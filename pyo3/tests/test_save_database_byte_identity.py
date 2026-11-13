"""Cross-surface byte identity for ``PyCounter.save_database`` (Phase 9, PY-01).

The rewritten save path snapshots the counter, sorts the pairs exactly once
(``rayon::par_sort_unstable_by_key``), writes them through the frozen ``.rkdb``
v2 header/entry writers, and does all of it with the GIL released. Its only
acceptable output is the bytes the CLI ``count`` path writes for the same input
and thread count, and the committed golden fixture. This module proves that on
the six-sequence golden input:

* the Python arms (``threads=1``, ``threads=None`` = default) hash to
  ``a5da813e2977157afc4b8c395dc6fbc721516024c52cb257208490e29b796af7``;
* the CLI arms (``--threads 1``, ``--threads 4``, default) hash to the same
  value;
* every arm also equals ``tests/fixtures/golden_k21_canon_sorted.rkdb``;
* the 1-vs-N invariant holds: all arms agree, so the saved bytes are
  thread-count independent.

Each Python arm runs in a FRESH interpreter (``sys.executable -c``) because the
rayon thread pool is process-global and first-call-wins — a ``threads=4``
counter built after a ``threads=1`` counter in the same process would silently
run on the first pool. A fresh process makes the arm's thread count real.

Skips are build-infrastructure only and are split by arm (WR-03): the
fixture-only Python arm needs just the committed fixture, so it runs in the
CI pyo3 job (which never builds the root CLI); the CLI and 1-vs-N arms also
need the release ``rustkmer`` binary and skip gracefully when it is absent.
A count/save failure or a sha256 mismatch never skips.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

try:
    import pyrustkmer
except ImportError:
    pytest.skip("pyrustkmer module not installed", allow_module_level=True)

# MUST match tests/output_pipeline_tests.rs and tests/golden_generate.rs.
GOLDEN_INPUT = [
    "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTAC",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "ACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACAC",
    "GTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGT",
    "AAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAA",
    "GATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATT",
]

GOLDEN_SHA = "a5da813e2977157afc4b8c395dc6fbc721516024c52cb257208490e29b796af7"

REPO_ROOT = Path(__file__).resolve().parents[2]
RUSTKMER = REPO_ROOT / "target" / "release" / "rustkmer"
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "golden_k21_canon_sorted.rkdb"

# Fresh-process Python arm. argv: fasta, output db, "1" | "4" | "default".
# Prints one JSON line naming the native module so a stale .so is diagnosable.
PYTHON_ARM_SCRIPT = """
import json
import sys

import pyrustkmer

fasta, out, threads_arg = sys.argv[1], sys.argv[2], sys.argv[3]
threads = None if threads_arg == "default" else int(threads_arg)
counter = pyrustkmer.PyCounter(21, canonical=True, threads=threads)
counter.add_from_fasta(fasta)
counter.save_database(out)
print(json.dumps({"module": pyrustkmer.__file__, "threads_arg": threads_arg}))
"""


def _sha256(path):
    """Return the lowercase hex sha256 of a file's bytes."""
    digest = hashlib.sha256()
    digest.update(Path(path).read_bytes())
    return digest.hexdigest()


def _write_golden_fasta(directory):
    """Write the six golden sequences to a temp FASTA and return its path."""
    fasta = Path(directory) / "golden_input.fa"
    fasta.write_text(
        "".join(f">seq{idx}\n{sequence}\n" for idx, sequence in enumerate(GOLDEN_INPUT))
    )
    return fasta


def _require_fixture():
    """Skip only when the committed golden fixture is absent (build infra)."""
    if not FIXTURE.exists():
        pytest.skip(f"committed golden fixture absent (build infra): {FIXTURE}")


def _require_cli():
    """Skip only when the release CLI binary is absent (build infra)."""
    if not RUSTKMER.exists():
        pytest.skip(f"release CLI binary absent (build infra): {RUSTKMER}")


def _run_python_arm(fasta, out, threads_arg):
    """Run one save arm in a fresh interpreter and return its JSON report."""
    result = subprocess.run(
        [sys.executable, "-c", PYTHON_ARM_SCRIPT, str(fasta), str(out), threads_arg],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"fresh Python arm threads={threads_arg} failed: {result.stderr}"
    )
    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert report["threads_arg"] == threads_arg
    assert Path(report["module"]).exists(), f"native module vanished: {report['module']}"
    return report


def _run_cli_arm(fasta, out, threads_arg):
    """Run one CLI count arm; threads_arg is "1", "4", or "default"."""
    command = [str(RUSTKMER), "count", "-k", "21", "-C"]
    if threads_arg != "default":
        command += ["--threads", threads_arg]
    command += ["-i", str(fasta), "-o", str(out), "-q"]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, (
        f"CLI arm threads={threads_arg} failed: {result.stderr}"
    )


def test_fixture_only_arm_does_not_require_the_cli(monkeypatch):
    """WR-03: the golden Python arm must not gate on the CLI binary.

    The CI pyo3 job builds only the wheel; a fixture-only guard is what keeps
    ``test_python_save_database_matches_golden`` running there.
    """
    monkeypatch.setattr(sys.modules[__name__], "RUSTKMER",
                        Path("/nonexistent/target/release/rustkmer"))
    _require_fixture()  # must not skip


def test_cli_guard_skips_gracefully_when_the_binary_is_absent(monkeypatch):
    """WR-03: CLI arms skip (not fail) when the release binary is absent."""
    monkeypatch.setattr(sys.modules[__name__], "RUSTKMER",
                        Path("/nonexistent/target/release/rustkmer"))
    with pytest.raises(pytest.skip.Exception):
        _require_cli()


@pytest.mark.parametrize("threads_arg", ["1", "default"])
def test_python_save_database_matches_golden(threads_arg, tmp_path):
    """PyCounter.save_database emits the golden bytes at threads=1 and default."""
    _require_fixture()
    fasta = _write_golden_fasta(tmp_path)
    out = tmp_path / f"python-{threads_arg}.rkdb"

    _run_python_arm(fasta, out, threads_arg)

    produced = _sha256(out)
    assert produced == GOLDEN_SHA, (
        f"Python save_database (threads={threads_arg}) sha256 {produced} "
        f"!= golden {GOLDEN_SHA}"
    )
    assert produced == _sha256(FIXTURE), (
        "Python save_database bytes must equal the committed golden fixture"
    )


@pytest.mark.parametrize("threads_arg", ["1", "4", "default"])
def test_cli_count_matches_golden(threads_arg, tmp_path):
    """CLI count emits the golden bytes at threads=1, 4, and default."""
    _require_cli()
    _require_fixture()
    fasta = _write_golden_fasta(tmp_path)
    out = tmp_path / f"cli-{threads_arg}.rkdb"

    _run_cli_arm(fasta, out, threads_arg)

    produced = _sha256(out)
    assert produced == GOLDEN_SHA, (
        f"CLI count (threads={threads_arg}) sha256 {produced} != golden {GOLDEN_SHA}"
    )
    assert produced == _sha256(FIXTURE), (
        "CLI count bytes must equal the committed golden fixture"
    )


def test_python_and_cli_arms_agree_1_vs_n(tmp_path):
    """The 1-vs-N invariant: every Python and CLI arm emits identical bytes."""
    _require_cli()
    _require_fixture()
    fasta = _write_golden_fasta(tmp_path)

    shas = {}
    for threads_arg in ("1", "default"):
        out = tmp_path / f"py-{threads_arg}.rkdb"
        _run_python_arm(fasta, out, threads_arg)
        shas[f"python-{threads_arg}"] = _sha256(out)
    for threads_arg in ("1", "4", "default"):
        out = tmp_path / f"cli-{threads_arg}.rkdb"
        _run_cli_arm(fasta, out, threads_arg)
        shas[f"cli-{threads_arg}"] = _sha256(out)

    fixture_sha = _sha256(FIXTURE)
    assert set(shas.values()) == {GOLDEN_SHA}, (
        f"thread-count dependent bytes: per-arm sha256 map {shas}"
    )
    assert fixture_sha == GOLDEN_SHA, (
        f"committed fixture drifted: {fixture_sha} != {GOLDEN_SHA}"
    )


def test_empty_counter_still_raises_the_verbatim_value_error(tmp_path):
    """Empty-counter behavior is unchanged by the detach rewrite."""
    counter = pyrustkmer.PyCounter(7)
    with pytest.raises(ValueError, match="Cannot save empty database"):
        counter.save_database(str(tmp_path / "empty.rkdb"))


def test_directory_path_still_raises_the_file_error(tmp_path):
    """A directory target still surfaces the verbatim file-creation message."""
    counter = pyrustkmer.PyCounter(7)
    counter.add_kmer("AAAAAAA")
    with pytest.raises(ValueError, match="Failed to create file"):
        counter.save_database(str(tmp_path))
