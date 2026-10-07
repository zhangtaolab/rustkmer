"""MERGE-04 contract tests for ``pyrustkmer.PyDatabase.merge``.

MERGE-04 requires the PyO3 binding to expose the same bounded merge core the
CLI uses: ``--max-memory`` / ``--merge-mode`` reach Python as the keyword-only
``max_memory`` / ``merge_mode`` arguments, they are validated at the Python
boundary (PyValueError, the ``PyCounter(threads=...)`` precedent from 02-03),
and a merge failure inside the core surfaces as a Python exception instead of
being swallowed.

Two habits from earlier plans in this phase are load-bearing here:

* **The route is proved, not assumed.** Plan 03-04 shipped routing tests whose
  hard-coded ``max_memory_usage: 1024`` never fired, because the fixture only
  estimated 960 bytes — so every "streaming" assertion silently exercised the
  in-memory path. Budgets here are DERIVED from the core's own estimator and
  the selected route is OBSERVED through its side effect on the temp dir, the
  same nonexistent-``temp_dir`` probe 03-01 and 03-04 use.
* **Counts, never "non-empty".** 03-01's two streaming data-loss bugs survived
  because the existing streaming test asserted only non-emptiness (200 k-mers
  in, 5 out). Every merge assertion below pins the exact decoded count map and
  the header accounting.
"""

import pytest

try:
    import pyrustkmer
except ImportError:
    pytest.skip("pyrustkmer module not installed", allow_module_level=True)

# k used by the fixtures. Small enough that a fixture is cheap to build, large
# enough that the shared/unique split below produces 110 distinct k-mers.
K = 21

# Modelled per-k-mer cost used by the merge admission control
# (`RKDatabase::merge_databases`: `total_kmers.saturating_mul(24)` in
# src/database/format.rs). Restated here on purpose: a test can only predict
# the routing decision the core will make if it carries its own copy of the
# model instead of asking the implementation.
BYTES_PER_KMER_ESTIMATE = 24

# `parse_memory_size` refuses anything below 1KB ("Memory size too small
# (minimum 1KB)"), so 1024 is the smallest budget a Python caller can request.
SMALLEST_ACCEPTED_BUDGET = "1024"

# `parse_memory_size` also refuses anything above 1TB.
LARGEST_ACCEPTED_BUDGET = 1024 * 1024 * 1024 * 1024

_BASES = "ACGT"

# db1 owns indices [0, 60), db2 owns [50, 110): indices 50..59 occur in both,
# so a correct merge must SUM their counts. Index 0..9 are triple-counted in
# db1 and 50..59 double-counted in db2, so a merge that keeps only the first
# input, only the last, or the maximum instead of the sum is detectable.
DB1_COUNTS = {i: (3 if i < 10 else 1) for i in range(60)}
DB2_COUNTS = {i: (2 if i < 60 else 1) for i in range(50, 110)}


def _kmer(index, k=K):
    """Return a deterministic, collision-free k-mer for ``index``.

    Base-4 digits of ``index``, least significant first, mapped onto ACGT.
    Unique for every ``index`` below 4**k.
    """
    return "".join(_BASES[(index >> (2 * pos)) & 0x3] for pos in range(k))


def _expected_merged_counts():
    """The exact (kmer -> count) map a correct merge of both inputs produces."""
    merged = {}
    for counts in (DB1_COUNTS, DB2_COUNTS):
        for index, count in counts.items():
            key = _kmer(index)
            merged[key] = merged.get(key, 0) + count
    return merged


EXPECTED_COUNTS = _expected_merged_counts()
EXPECTED_UNIQUE = len(EXPECTED_COUNTS)
# `.rkdb` v2 header accounting: `RKDatabase::from_kmer_pairs` writes
# `total_kmers = entries.len()` and `unique_kmers = entries.len()`, i.e. the
# header counts RECORDS, not the sum of the count fields. Count conservation
# is therefore asserted on the exported map, not on the header.
EXPECTED_SUM_OF_COUNTS = sum(EXPECTED_COUNTS.values())


def _write_db(path, counts):
    """Count ``counts`` (index -> multiplicity) and save it as a .rkdb file."""
    counter = pyrustkmer.PyCounter(K)
    for index, count in counts.items():
        for _ in range(count):
            counter.add_kmer(_kmer(index))
    counter.save_database(str(path))
    return str(path)


def _read_count_map(db_path, tmp_path, name="merged.txt"):
    """Return (decoded kmer -> count map, PyDatabaseStats) for ``db_path``.

    Reads the whole database through the public export API rather than spot
    checking a few k-mers, so a merge that drops, duplicates or invents entries
    cannot pass.
    """
    db = pyrustkmer.PyDatabase(db_path, pyrustkmer.LoadMode.Preload)
    export_path = tmp_path / name
    db.export_to_file(str(export_path))
    counts = {}
    for line in export_path.read_text().splitlines():
        kmer, _, count = line.partition("\t")
        counts[kmer] = int(count)
    return counts, db.get_stats()


def _estimated_bytes(db_paths):
    """Reproduce the core's admission-control estimate for ``db_paths``.

    Same model as `RKDatabase::merge_databases`: every input's persisted
    header `total_kmers` (what `RKDatabase::estimate_total_kmers` reads out of
    the 42-byte header — the record count, not the sum of counts) summed, then
    multiplied by the modelled per-k-mer cost.
    """
    total_kmers = 0
    for db_path in db_paths:
        db = pyrustkmer.PyDatabase(db_path, pyrustkmer.LoadMode.Preload)
        total_kmers += db.get_stats().total_kmers
    return total_kmers * BYTES_PER_KMER_ESTIMATE


def _over_budget(db_paths):
    """Return a budget string that is provably BELOW the real estimate.

    The smallest budget `parse_memory_size` accepts is 1KB, so an over-budget
    budget is only constructible when the fixture estimates more than that.
    The assertion is the important part: 03-04's routing gate went vacuous
    because a "tiny" budget was larger than the fixture's estimate, and a
    vacuous routing assertion is worse than no assertion. If the fixtures ever
    shrink below the 1KB parser floor, this fails loudly instead.
    """
    estimate = _estimated_bytes(db_paths)
    smallest = int(SMALLEST_ACCEPTED_BUDGET)
    assert estimate > smallest, (
        f"fixture too small to exceed the smallest accepted budget: "
        f"estimate {estimate} <= {smallest}"
    )
    return SMALLEST_ACCEPTED_BUDGET


def _within_budget(db_paths):
    """Return a budget string that is provably ABOVE the real estimate."""
    estimate = _estimated_bytes(db_paths)
    budget = estimate * 2
    assert budget <= LARGEST_ACCEPTED_BUDGET
    return str(budget)


@pytest.fixture
def two_dbs(tmp_path):
    """Two small .rkdb inputs with a 50..59 overlap that must sum."""
    db1 = _write_db(tmp_path / "db1.rkdb", DB1_COUNTS)
    db2 = _write_db(tmp_path / "db2.rkdb", DB2_COUNTS)
    return [db1, db2]


def test_merge_default_no_kwargs_works(two_dbs, tmp_path):
    """Backward compatibility: the pre-MERGE-04 call still merges correctly.

    No keyword arguments at all, so this exercises the `MergeConfig::default()`
    path a 0.4.x caller relied on. It now inherits the 03-01 bounded dispatch,
    which is exactly the MERGE-04 point: the shared core, not a parallel
    implementation.
    """
    out = tmp_path / "merged.rkdb"
    pyrustkmer.PyDatabase.merge(two_dbs, str(out))

    assert out.exists()
    counts, stats = _read_count_map(str(out), tmp_path)
    assert counts == EXPECTED_COUNTS
    # Header accounting + count conservation: the two whole-database invariants
    # a merge can break without changing the k-mer set (asserted on both routes
    # in tests/merge_routing_tests.rs after plan 03-04).
    assert stats.unique_kmers == EXPECTED_UNIQUE
    assert stats.total_kmers == EXPECTED_UNIQUE
    assert sum(counts.values()) == EXPECTED_SUM_OF_COUNTS


@pytest.mark.skip(reason="TODO(03-05 Task 2): un-skip once kwargs land")
def test_merge_rejects_bad_merge_mode(two_dbs, tmp_path):
    """An unknown merge_mode is rejected at the Python boundary (T-03-15)."""
    with pytest.raises(ValueError, match="merge_mode"):
        pyrustkmer.PyDatabase.merge(
            two_dbs, str(tmp_path / "merged.rkdb"), merge_mode="bogus"
        )


@pytest.mark.skip(reason="TODO(03-05 Task 2): un-skip once kwargs land")
def test_merge_rejects_bad_max_memory(two_dbs, tmp_path):
    """A malformed max_memory string is rejected at the boundary (T-03-16)."""
    with pytest.raises(ValueError, match="max_memory"):
        pyrustkmer.PyDatabase.merge(
            two_dbs, str(tmp_path / "merged.rkdb"), max_memory="not-a-size"
        )


@pytest.mark.skip(reason="TODO(03-05 Task 2): un-skip once kwargs land")
def test_over_budget_memory_mode_is_rejected(two_dbs, tmp_path):
    """max_memory + merge_mode='memory' reach the D-02 reject (T-03-17).

    The budget is derived from the real estimate, so the merge really is over
    budget, and the message is checked for the numbers the core computed — a
    reject that quotes the wrong byte counts would mean the kwargs never
    reached MergeConfig.
    """
    budget = _over_budget(two_dbs)
    estimate = _estimated_bytes(two_dbs)

    with pytest.raises(RuntimeError) as excinfo:
        pyrustkmer.PyDatabase.merge(
            two_dbs,
            str(tmp_path / "merged.rkdb"),
            max_memory=budget,
            merge_mode="memory",
        )

    message = str(excinfo.value)
    assert "rejected" in message
    # The D-02 message must name the streaming alternative...
    assert "streaming" in message
    # ...and echo the numbers the core computed from the derived budget.
    assert f"{estimate} bytes" in message, message
    assert f"{int(budget)} bytes" in message, message


@pytest.mark.skip(reason="TODO(03-05 Task 2): un-skip once kwargs land")
def test_streaming_and_inmemory_routes_produce_identical_data(
    two_dbs, tmp_path, monkeypatch
):
    """Both routes selected from Python yield the same exact count map.

    Route selection is budget-dependent (03-01), so covering one route is half
    a claim. The temp dir is redirected at a real directory so the streaming
    route can actually write its chunk files.
    """
    work = tmp_path / "temp"
    work.mkdir()
    monkeypatch.setenv("TMPDIR", str(work))

    streaming_out = tmp_path / "streaming.rkdb"
    pyrustkmer.PyDatabase.merge(
        two_dbs, str(streaming_out), merge_mode="streaming"
    )
    streaming_counts, streaming_stats = _read_count_map(
        str(streaming_out), tmp_path, "streaming.txt"
    )

    inmemory_out = tmp_path / "inmemory.rkdb"
    pyrustkmer.PyDatabase.merge(
        two_dbs,
        str(inmemory_out),
        max_memory=_within_budget(two_dbs),
        merge_mode="memory",
    )
    inmemory_counts, inmemory_stats = _read_count_map(
        str(inmemory_out), tmp_path, "inmemory.txt"
    )

    assert streaming_counts == EXPECTED_COUNTS
    assert inmemory_counts == EXPECTED_COUNTS
    assert streaming_counts == inmemory_counts
    assert streaming_stats.total_kmers == EXPECTED_UNIQUE
    assert inmemory_stats.total_kmers == EXPECTED_UNIQUE
    assert streaming_stats.unique_kmers == EXPECTED_UNIQUE
    assert inmemory_stats.unique_kmers == EXPECTED_UNIQUE
    assert sum(streaming_counts.values()) == EXPECTED_SUM_OF_COUNTS
    assert sum(inmemory_counts.values()) == EXPECTED_SUM_OF_COUNTS
