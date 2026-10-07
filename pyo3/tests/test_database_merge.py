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

import re

import pytest

try:
    import pyrustkmer
except ImportError:
    pytest.skip("pyrustkmer module not installed", allow_module_level=True)

# k used by the fixtures. Small enough that a fixture is cheap to build, large
# enough that the shared/unique split below produces 110 distinct k-mers.
K = 21

# Modelled per-k-mer cost used by the merge admission control.
# `INMEMORY_BYTES_PER_KMER` in src/database/format.rs is the source of this
# number. 24 was WR-01's under-model: it described roughly a quarter of the
# peak the in-memory route actually reaches, so a merge the gate admitted could
# still exhaust memory, and the in-memory route was the one the gate admitted.
# The core now charges 96.
#
# THIS IS THE ONLY CROSS-LANGUAGE COPY of the constant. It is restated here
# because a test can only predict the routing decision the core will make if it
# carries its own model instead of asking the implementation — but two comments
# can drift apart silently, so `test_python_budget_model_tracks_the_core` below
# pairs the two copies BEHAVIOURALLY: it reads the byte figure the core echoes
# in its own D-02 rejection and asserts it equals
# `total_kmers * BYTES_PER_KMER_ESTIMATE`. If the core's constant changes and
# this one does not, that test fails instead of the whole file quietly testing
# the wrong route.
BYTES_PER_KMER_ESTIMATE = 96

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


def test_merge_rejects_bad_merge_mode(two_dbs, tmp_path):
    """An unknown merge_mode is rejected at the Python boundary (T-03-15)."""
    with pytest.raises(ValueError, match="merge_mode"):
        pyrustkmer.PyDatabase.merge(
            two_dbs, str(tmp_path / "merged.rkdb"), merge_mode="bogus"
        )


def test_merge_rejects_bad_max_memory(two_dbs, tmp_path):
    """A malformed max_memory string is rejected at the boundary (T-03-16)."""
    with pytest.raises(ValueError, match="max_memory"):
        pyrustkmer.PyDatabase.merge(
            two_dbs, str(tmp_path / "merged.rkdb"), max_memory="not-a-size"
        )


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


def test_python_budget_model_tracks_the_core(two_dbs, tmp_path):
    """The Python copy of the admission model is pinned to the CORE's figure.

    W1: ``BYTES_PER_KMER_ESTIMATE`` is the only cross-language copy of
    ``INMEMORY_BYTES_PER_KMER``. Two copies of a number held together by a
    comment drift silently, and the consequence here is a routing test that
    quietly exercises the wrong path — the failure mode plan 03-04 shipped and
    this phase has now hit twice.

    So the pairing is BEHAVIOURAL rather than editorial. The core echoes the
    figures it computed in its D-02 rejection message; this test drives that
    rejection and parses both of them out, asserting that

    * the core's byte figure equals ``total_kmers * BYTES_PER_KMER_ESTIMATE``,
      and
    * the core's k-mer figure equals the sum of ``db.get_stats().total_kmers``
      read here in Python.

    The second assertion matters as much as the first: it pins the *record
    count* reading of ``total_kmers`` (IN-03) across the language boundary. If
    the core ever switches to the sum of counts — the other meaning of the same
    name, live in ``KmerCounter::total_kmers`` — this fails instead of every
    budget in this file being scaled by the average count.

    CAVEAT, and it is not a small one: ``pyrustkmer.so`` in the project venv is
    a PREBUILT artifact, not a build of the Rust on disk. This assertion is
    correct once the extension is rebuilt from source, and until then the whole
    of ``pyo3/tests/`` is developer-run only. Two things make that worse, both
    recorded in deferred-items.md: ``pyo3/pyproject.toml``'s ``python-source``
    misconfiguration means ``maturin build``/``maturin develop`` refuse to run
    at all, and ``addopts`` hard-codes ``--cov-fail-under=80`` against a
    compiled extension, so every pytest run exits 1 even when green.
    ``.github/workflows/ci.yml`` has no pytest job either, so nothing in CI
    runs this file. The Rust-side evidence for the model change is
    ``model_change_routes_a_budget_the_old_model_admitted_to_streaming`` in
    ``tests/merge_routing_tests.rs``; this is the Python half, kept
    correct-by-construction for the next rebuild.
    """
    budget = _over_budget(two_dbs)

    with pytest.raises(RuntimeError) as excinfo:
        pyrustkmer.PyDatabase.merge(
            two_dbs,
            str(tmp_path / "merged.rkdb"),
            max_memory=budget,
            merge_mode="memory",
        )

    message = str(excinfo.value)
    match = re.search(
        r"estimated memory \((\d+) bytes for (\d+) k-mers\)", message
    )
    assert match, (
        "the D-02 rejection must echo the figures the core computed, in the form "
        f"'estimated memory (N bytes for M k-mers)'; got: {message}"
    )
    core_bytes = int(match.group(1))
    core_kmers = int(match.group(2))

    total_kmers = 0
    for db_path in two_dbs:
        db = pyrustkmer.PyDatabase(db_path, pyrustkmer.LoadMode.Preload)
        total_kmers += db.get_stats().total_kmers

    assert core_kmers == total_kmers, (
        "the core's k-mer figure must be the sum of the inputs' record counts, "
        f"as Python reads them: core {core_kmers} vs Python {total_kmers}"
    )
    assert core_bytes == total_kmers * BYTES_PER_KMER_ESTIMATE, (
        f"the core's admission model ({core_bytes} bytes) disagrees with this "
        f"file's copy of it ({total_kmers} * {BYTES_PER_KMER_ESTIMATE} = "
        f"{total_kmers * BYTES_PER_KMER_ESTIMATE}). One of the two copies of "
        "INMEMORY_BYTES_PER_KMER is stale."
    )


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


def test_over_budget_auto_hard_route_completes(two_dbs, tmp_path, monkeypatch):
    """MERGE-02's hard route, reached from Python.

    `auto` with an over-budget budget must still complete — routed to
    streaming, never to an in-memory merge that could exhaust RAM. That the
    streaming branch was the one entered is proved by the sibling
    bogus-`TMPDIR` test, not by this test; this one asserts the data.
    """
    work = tmp_path / "temp"
    work.mkdir()
    monkeypatch.setenv("TMPDIR", str(work))

    out = tmp_path / "merged.rkdb"
    pyrustkmer.PyDatabase.merge(
        two_dbs,
        str(out),
        max_memory=_over_budget(two_dbs),
        merge_mode="auto",
    )

    counts, stats = _read_count_map(str(out), tmp_path)
    assert counts == EXPECTED_COUNTS
    assert stats.unique_kmers == EXPECTED_UNIQUE
    assert stats.total_kmers == EXPECTED_UNIQUE
    assert sum(counts.values()) == EXPECTED_SUM_OF_COUNTS


def _bogus_temp_dir(tmp_path, monkeypatch):
    """Point the merge's temp dir at a directory that does not exist.

    `MergeConfig::temp_dir` defaults to `std::env::temp_dir()`, which on unix
    reads `TMPDIR` on every call (it is not cached), so the environment
    variable is enough to redirect it. This is 03-01's nonexistent-`temp_dir`
    probe lifted to Python: it needs no new API and no log capture.
    """
    bogus = tmp_path / "no_such_temp_dir"
    monkeypatch.setenv("TMPDIR", str(bogus))
    assert not bogus.exists()
    return bogus


@pytest.mark.parametrize("merge_mode", ["streaming", "auto"])
def test_streaming_route_is_proven_by_its_chunk_files(
    two_dbs, tmp_path, monkeypatch, merge_mode
):
    """The streaming route is OBSERVED, never assumed.

    `TempFileManager::create_temp_file` does
    `File::create(temp_dir.join("rustkmer_sort_..."))`, so with `TMPDIR`
    pointing at a nonexistent directory the streaming path fails on its first
    chunk file and the error names that file. `merge_databases_inmemory` never
    touches `temp_dir` at all, which is what makes the sibling control test
    meaningful: same fixture, same bogus temp dir, succeeds.

    A test that merely passed a small budget and called the result "streaming"
    would prove nothing — plan 03-04 shipped exactly that mistake.
    """
    bogus = _bogus_temp_dir(tmp_path, monkeypatch)

    kwargs = {"merge_mode": merge_mode}
    if merge_mode == "auto":
        # Derived (not hard-coded) so the MERGE-02 hard route actually fires.
        kwargs["max_memory"] = _over_budget(two_dbs)

    with pytest.raises(RuntimeError) as excinfo:
        pyrustkmer.PyDatabase.merge(two_dbs, str(tmp_path / "merged.rkdb"), **kwargs)

    message = str(excinfo.value)
    assert "Failed to create temp file" in message, message
    assert bogus.name in message, message


@pytest.mark.parametrize("merge_mode", ["auto", "memory"])
def test_inmemory_route_never_touches_temp_dir(
    two_dbs, tmp_path, monkeypatch, merge_mode
):
    """Control arm for the route proof, and the 'memory is not always rejected'
    control: within budget, the bogus temp dir is irrelevant and the merge
    succeeds with the exact union.
    """
    _bogus_temp_dir(tmp_path, monkeypatch)

    out = tmp_path / "merged.rkdb"
    pyrustkmer.PyDatabase.merge(
        two_dbs,
        str(out),
        max_memory=_within_budget(two_dbs),
        merge_mode=merge_mode,
    )

    counts, stats = _read_count_map(str(out), tmp_path)
    assert counts == EXPECTED_COUNTS
    assert stats.unique_kmers == EXPECTED_UNIQUE


def test_merge_signature_exposes_the_cli_kwargs():
    """`max_memory` and `merge_mode` are part of the public signature.

    Scripts the plan's manual `help(pyrustkmer.PyDatabase.merge)` check so the
    kwargs cannot silently drop out of the binding.
    """
    doc = pyrustkmer.PyDatabase.merge.__doc__ or ""
    assert "max_memory" in doc
    assert "merge_mode" in doc
    assert "streaming" in doc
