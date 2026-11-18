#!/usr/bin/env python3
"""PROF-05 CLI-vs-Python N-read differential (05-06) — D2 evidence.

Phase 9 landed the ratified D2 skip-N unification: BOTH surfaces now skip
every k-mer window containing a non-ACGT byte, so the pre-Phase-9 Python
strip-and-join behavior (which created chimeric k-mers) survives only as
history. Nine deterministic four-line FASTQ cases at k=21 are counted
through BOTH surfaces on the SAME bytes (canonical=True, threads=1): the
CLI map is decoded from its .rkdb via
pyrustkmer.PyDatabase(path, LoadMode.Preload).export_all_kmers() — no second
binary decoder, no prose parsing — and the Python map comes from
PyCounter.add_from_fastq + get_all_counts().

--expect-unified is the Phase 9 re-run mode. With --previous PATH the
committed pre-D2 artifact is validated first (k, canonical, exact case-name
set, per-case record shape) and embedded as a `before` block while the
top-level `cases` remain the after state — one self-contained artifact
carries both records.

Verdict semantics (evaluate):
  - The no-N control MUST be exactly equal across surfaces; a mismatch is
    exit 1 (harness bug or unexpected semantics change).
  - --expect-divergence: at least one N-case must show Python-only
    chimeric keys, else exit 1 (the fixture failed to exercise the
    historical divergence).
  - --expect-unified (Phase 9 re-run): ALL cases must be equal, else exit 1.

Exit codes: 0 verdict satisfied; 1 measured verdict failure; 2 invalid
(empty records, missing control, failed child process, missing/stale
extension, incompatible --previous artifact) — never an empty PASS. The
evidence doc is written only on verdict paths (0/1), never on exit-2 paths.

Stdlib controller; pyrustkmer is imported lazily so the unit suite runs
without it.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import sysconfig
import tempfile
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    # Direct script execution: insert the repo root BEFORE importing so the
    # harness package resolves to this checkout in one shot (compare.py's
    # fixup, replicated).
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.bench.bench import (
    DEFAULT_RUSTKMER,
    BenchmarkConfig,
    binary_provenance,
    fingerprint,
    rustkmer_count_cmd,
    validate_provenance,
)
from scripts.bench.python_bench import NATIVE_SUFFIXES, _native_module_file

EXIT_PASS = 0
EXIT_VERDICT_FAIL = 1
EXIT_INVALID = 2

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "scratch" / "n_read_differential.json"
K = 21
BASE_30 = "ACGTACGTACGTACGTACGTACGTACGTAC"  # 30 bp, no N
CONTROL_NAME = "control_no_n"
EXPECTED_SEMANTICS = {"cli": "skip-N-windows",
                      "python": "skip-N-windows"}
EXAMPLE_CAP = 5


def invalid(message):
    """Print an input/infra problem and exit 2 — never an empty PASS."""
    print(f"n_read_differential.py: {message}", file=sys.stderr)
    sys.exit(EXIT_INVALID)


# --- pure helpers (unit-tested without PyO3) --------------------------------

def with_n(seq, positions, char="N"):
    """Replace the given positions of seq with char (fixture helper)."""
    chars = list(seq)
    for pos in positions:
        chars[pos] = char
    return "".join(chars)


def build_cases():
    """The nine deterministic cases at k=21 (plan 05-06 Task 2).

    N positions are chosen against the FIRST k-window (bases 0..20):
    window_end puts N on its last base (kills every CLI window),
    window_start on the base just past it (kills all but the first).
    record_boundary predates D2 — its terminal Ns sit in the boundary
    windows, so under skip-N it only covers the pre-D2 strip-and-join form
    (joining the N-free flanks) and does NOT prove the absence of
    cross-record joins. The N-free two-read probe in the unit suite
    (`TestCrossRecordJoinProbe`) is the shape that would expose a
    join-based implementation; it stays out of this fixture because adding
    a live case would break `--previous`'s exact case-name check against
    the immutable pre-D2 artifact and require regenerating the committed
    evidence. short_read (15 bp < k) yields zero windows on both surfaces.
    """
    return [
        {"name": CONTROL_NAME, "reads": [BASE_30]},
        {"name": "n_at_first", "reads": [with_n(BASE_30, [0])]},
        {"name": "n_at_window_end", "reads": [with_n(BASE_30, [K - 1])]},
        {"name": "n_at_window_start", "reads": [with_n(BASE_30, [K])]},
        {"name": "n_at_last",
         "reads": [with_n(BASE_30, [len(BASE_30) - 1])]},
        {"name": "multiple_n", "reads": [with_n(BASE_30, [5, 15, 25])]},
        {"name": "lowercase_n", "reads": [with_n(BASE_30, [10], "n")]},
        {"name": "record_boundary",
         "reads": [with_n(BASE_30[:25], [24]), with_n(BASE_30[:25], [0])]},
        {"name": "short_read", "reads": [BASE_30[:15]]},
    ]


def fastq_bytes(case):
    """Deterministic four-line FASTQ bytes; quality 'I' x sequence length."""
    lines = []
    for i, seq in enumerate(case["reads"]):
        lines += [f"@read{i}", seq, "+", "I" * len(seq)]
    return ("\n".join(lines) + "\n").encode()


def _validated_surface_counts(record, surface, name, path):
    """Validate one case's `cli`/`python` {distinct, total} block."""
    block = record.get(surface)
    if not isinstance(block, dict):
        raise ValueError(
            f"prior case {name!r} has no {surface} counts block: {path}")
    counts = {}
    for field in ("distinct", "total"):
        value = block.get(field)
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(
                f"prior case {name!r} {surface}.{field}={value!r} is not an "
                f"integer: {path}")
        counts[field] = value
    return counts


def load_previous(path):
    """Load and validate a prior differential artifact for a `before` block.

    Validate-before-embed (compare.py's load_results habit): a prior must
    itself record the pre-D2 divergence (`expectation == "divergence"` and a
    positive integer `totals.python_only_total`) in addition to matching k,
    canonical, the exact case-name set, and the per-case count shape — a
    structurally valid post-D2 record is not a before state, never an empty
    pass. An unreadable file raises OSError and unparseable JSON raises
    json.JSONDecodeError; main() maps both to exit 2.
    """
    prior_path = Path(path)
    raw = prior_path.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"prior artifact is not a JSON object: {path}")
    if data.get("k") != K:
        raise ValueError(
            f"prior artifact k={data.get('k')!r} does not match K={K}: {path}")
    if data.get("canonical") is not True:
        raise ValueError(
            f"prior artifact canonical={data.get('canonical')!r} is not "
            f"true: {path}")
    # Prior-state guard (IN-04): only a record that itself observed the
    # pre-D2 divergence can serve as the `before` state. A post-D2 or
    # arbitrary differential with the right case set is not history.
    expectation = data.get("expectation")
    if expectation != "divergence":
        raise ValueError(
            f"prior artifact expectation={expectation!r} is not 'divergence': "
            f"only a pre-D2 divergence record can be a before state: {path}")
    totals = data.get("totals")
    if not isinstance(totals, dict):
        raise ValueError(
            f"prior artifact has no totals block (got {totals!r}): {path}")
    python_only_total = totals.get("python_only_total")
    if (not isinstance(python_only_total, int)
            or isinstance(python_only_total, bool)
            or python_only_total <= 0):
        raise ValueError(
            f"prior artifact totals.python_only_total={python_only_total!r} "
            f"is not a positive integer: a prior with no recorded divergence "
            f"cannot be a before state: {path}")
    records = data.get("cases")
    if not isinstance(records, list):
        raise ValueError(f"prior artifact has no cases list: {path}")
    expected_names = {case["name"] for case in build_cases()}
    cases = {}
    for record in records:
        if not isinstance(record, dict) or "name" not in record:
            raise ValueError(
                f"prior artifact has a malformed case record: {path}")
        name = record["name"]
        if name in cases:
            raise ValueError(
                f"prior artifact repeats case {name!r}: {path}")
        cases[name] = {
            surface: _validated_surface_counts(record, surface, name, path)
            for surface in ("cli", "python")
        }
    if set(cases) != expected_names:
        missing = sorted(expected_names - set(cases))
        extra = sorted(set(cases) - expected_names)
        raise ValueError(
            f"prior artifact case names do not match the fixture "
            f"(missing={missing}, extra={extra}): {path}")
    return {
        "path": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "expectation": expectation,
        "totals": totals,
        "cases": cases,
    }


def diff_maps(cli_map, python_map):
    """Pure symmetric-difference reduction with stable (sorted) ordering.

    Returns python_only keys (chimeric), cli_only keys (skip-N losses),
    shared-key count deltas, both surfaces' distinct/sum-of-counts, and up
    to EXAMPLE_CAP example chimeric k-mers.
    """
    cli_keys = set(cli_map)
    py_keys = set(python_map)
    python_only = sorted(py_keys - cli_keys)
    cli_only = sorted(cli_keys - py_keys)
    count_deltas = [
        {"kmer": kmer, "cli": cli_map[kmer], "python": python_map[kmer]}
        for kmer in sorted(cli_keys & py_keys)
        if cli_map[kmer] != python_map[kmer]
    ]
    return {
        "python_only": python_only,
        "cli_only": cli_only,
        "count_deltas": count_deltas,
        "cli": {"distinct": len(cli_map), "total": sum(cli_map.values())},
        "python": {"distinct": len(python_map),
                   "total": sum(python_map.values())},
        "example_chimeras": python_only[:EXAMPLE_CAP],
    }


def _has_diff(record):
    return bool(record["python_only"] or record["cli_only"]
                or record["count_deltas"])


def evaluate(cases, expect):
    """Verdict from per-case diff records. Returns (exit_code, lines).

    Raises ValueError on invalid shapes (empty records, missing/ambiguous
    control) — the caller maps that to exit 2, never an empty PASS.
    """
    if not cases:
        raise ValueError("no case records — an empty differential is invalid")
    controls = [c for c in cases if c["name"] == CONTROL_NAME]
    if len(controls) != 1:
        raise ValueError(
            f"expected exactly one {CONTROL_NAME} case, found {len(controls)}")
    lines = []
    control = controls[0]
    if _has_diff(control):
        lines.append(
            f"{CONTROL_NAME} MISMATCH: python_only={control['python_only']} "
            f"cli_only={control['cli_only']} "
            f"count_deltas={control['count_deltas']} — harness bug or "
            f"unexpected semantics change")
        return EXIT_VERDICT_FAIL, lines
    lines.append(f"{CONTROL_NAME} equal across surfaces")
    if expect == "unified":
        divergent = [c["name"] for c in cases if _has_diff(c)]
        if divergent:
            lines.append(
                f"expect-unified FAILED: divergence remains in {divergent}")
            return EXIT_VERDICT_FAIL, lines
        lines.append("all cases equal — D2 unification verified")
        return EXIT_PASS, lines
    divergent = [c["name"] for c in cases
                 if c["name"] != CONTROL_NAME and c["python_only"]]
    if not divergent:
        lines.append(
            "expect-divergence FAILED: no N-case shows Python-only chimeric "
            "keys — the fixture failed to exercise the known pre-Phase-9 "
            "divergence")
        return EXIT_VERDICT_FAIL, lines
    lines.append(f"chimeric divergence recorded in {divergent}")
    return EXIT_PASS, lines


# --- controller (real CLI + PyO3 execution) ---------------------------------

def count_case(case, tmp, rustkmer, pyrustkmer):
    """Count one case's SAME bytes through both surfaces; return the record."""
    fq = tmp / f"{case['name']}.fq"
    data = fastq_bytes(case)
    fq.write_bytes(data)
    db = tmp / f"{case['name']}.rkdb"
    cfg = BenchmarkConfig(k=K, canonical=True, threads=1, inputs=[fq])
    cmd = rustkmer_count_cmd(cfg, db, rustkmer)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"CLI count failed for {case['name']} rc={proc.returncode}: "
            f"{cmd}\ntrailing stderr:\n{proc.stderr[-500:]}")
    cli_db = pyrustkmer.PyDatabase(str(db), pyrustkmer.LoadMode.Preload)
    cli_map = {r.kmer: int(r.count) for r in cli_db.export_all_kmers()}
    counter = pyrustkmer.PyCounter(K, canonical=True, threads=1)
    counter.add_from_fastq(str(fq))
    py_map = counter.get_all_counts()
    record = {"name": case["name"],
              "reads": list(case["reads"]),
              "input_sha256": hashlib.sha256(data).hexdigest()}
    record.update(diff_maps(cli_map, py_map))
    return record


def run_differential(args):
    """Execute the nine cases and persist the D2 evidence doc."""
    rustkmer = Path(args.rustkmer)
    if not rustkmer.is_file():
        invalid(f"rustkmer binary not found: {rustkmer} — build it first "
                f"(cargo build --release --locked)")
    try:
        import pyrustkmer
    except Exception as exc:
        invalid(
            f"cannot import pyrustkmer: {exc} — rebuild the extension from "
            f"source (env -u CONDA_PREFIX ... maturin develop --release -m "
            f"pyo3/Cargo.toml) and run under that venv's python")
    module_path = _native_module_file(pyrustkmer)
    site_prefix = Path(sysconfig.get_paths()["purelib"]).resolve()
    if (not module_path.is_relative_to(site_prefix)
            or module_path.suffix not in NATIVE_SUFFIXES):
        invalid(f"pyrustkmer native module {module_path} is outside this "
                f"interpreter's site-packages {site_prefix} — stale/shadowed "
                f"extension")

    expect = "unified" if args.expect_unified else "divergence"
    records = []
    with tempfile.TemporaryDirectory(prefix="n-read-diff-") as tmp_name:
        tmp = Path(tmp_name)
        for case in build_cases():
            records.append(count_case(case, tmp, rustkmer, pyrustkmer))

    code, lines = evaluate(records, expect)
    previous = load_previous(args.previous) if args.previous else None
    divergent = [r["name"] for r in records if _has_diff(r)]
    doc = {
        "schema_version": 1,
        "k": K,
        "canonical": True,
        "expected_semantics": dict(EXPECTED_SEMANTICS),
        "expectation": expect,
        "created": datetime.now(timezone.utc).isoformat(),
        "cases": records,
        "totals": {
            "cases": len(records),
            "divergent_cases": divergent,
            "python_only_total": sum(len(r["python_only"]) for r in records),
            "cli_only_total": sum(len(r["cli_only"]) for r in records),
            "count_delta_total": sum(len(r["count_deltas"]) for r in records),
        },
        "verdict": {"result": "PASS" if code == EXIT_PASS else "FAIL",
                    "expect": expect, "exit_code": code},
        "provenance": None,
    }
    if previous is not None:
        doc["before"] = previous
    prov = binary_provenance(rustkmer, "release")
    prov["module"] = fingerprint(module_path)
    prov["python_executable"] = sys.executable
    prov["python_version"] = sys.version.split()[0]
    doc["provenance"] = prov
    validate_provenance(doc)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")
    for line in lines:
        print(line, file=sys.stdout if code == EXIT_PASS else sys.stderr)
    print(f"evidence written to {out}")
    print(f"N-READ DIFFERENTIAL result={doc['verdict']['result']} "
          f"expect={expect} cases={len(records)} divergent={len(divergent)}")
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="PROF-05 CLI-vs-Python N-read differential (D2 evidence). "
                    "Phase 9 landed the skip-N unification: both surfaces "
                    "skip windows containing non-ACGT bytes. --expect-unified "
                    "is the Phase 9 re-run mode; --previous embeds the "
                    "committed pre-D2 artifact as a before block.")
    parser.add_argument("--rustkmer", default=DEFAULT_RUSTKMER)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--previous", metavar="PATH",
                        help="prior differential artifact to validate and "
                             "embed as a before block; the top-level cases "
                             "remain the after state")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--expect-divergence", action="store_true",
                       help="default: N-cases must show chimeric divergence")
    group.add_argument("--expect-unified", action="store_true",
                       help="Phase 9 re-run: all cases must be equal")
    args = parser.parse_args(argv)
    try:
        return run_differential(args)
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        invalid(str(exc))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # infra failures exit 2, never a traceback
        print(f"n_read_differential.py: {exc}", file=sys.stderr)
        sys.exit(EXIT_INVALID)