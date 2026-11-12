#!/usr/bin/env python3
"""PROF-03 contention controller + attribution-v1 evidence (Phase 5, 05-05).

Materializes the standalone rk-microbench crate from the committed template
(@REPO_ROOT@ substitution, committed audited Cargo.lock verified by sha256,
build --locked), provisions a representative random-record subslice of the
real CRR1936095 input (reservoir_slice; --synthetic is smoke-only — synthetic
all-unique keys have the wrong duplication structure for evidence), and runs
four mechanism arms x thread counts in counterbalanced rotated rounds:

  shared-counter  — production KmerCounter (DashMap + BOTH global atomics)
  shared-dashmap  — raw shared DashMap, identical table work, NO global atomics
  atomic-only     — the same global-atomic traffic without any table
  thread-local    — private tables + end reduction (locality/bandwidth control)

Attribution-v1 (persisted as formula strings alongside the numbers):

  global_atomics_attribution_ns    = shared_counter_ns(t16)
                                     - shared_dashmap_without_global_atomics_ns(t16)
  memory_bandwidth_attribution_ns  = shared_dashmap_without_global_atomics_ns(t16)
                                     - thread_local_ns(t16)
  *_pct                            = 100 * share / (shared_counter_ns(t16)
                                     - thread_local_ns(t16))
  contention_multiplier            = shared_counter_ns(t16) / shared_counter_ns(t1)

Negative or near-zero shares are recorded honestly with an inconclusive note,
never clamped to look decisive.

Exit codes are a contract (compare.py semantics):
  0 — valid evidence written.
  1 — a conservation failure in ANY raw record (or a microbench conservation
      abort) invalidates the whole run.
  2 — invalid: missing (variant, threads) cells, malformed microbench JSON,
      lockfile mismatch/absence, bad arguments, build/provisioning failure.
      No evidence file is written on any exit-1/2 path.

Methodology (CONTEXT guardrails): one discarded warmup per (variant, threads)
cell, then --reps measured rounds where each round runs all cells exactly once
in rotated order (pure rotation_schedule; round r starts at cell index
(r-1) mod n). The schedule is persisted with the raw records; every rep carries
its round index and honest cache_state. Medians across rounds, never
sequential per-cell blocks. Provenance via the shared bench.binary_provenance
(actual rk-microbench executable bytes + git HEAD + dirty flag + release).

Python 3.11+ stdlib only. Unit suite runs without cargo/PyO3/the dataset.
"""

import argparse
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    # Executed as a script: insert the checkout root BEFORE importing so the
    # harness package resolves to this checkout in one shot (compare.py's
    # fixup, replicated — an unrelated `scripts` namespace package in
    # site-packages must not win the first import).
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.bench.bench import (
    DEFAULT_COOLDOWN_S,
    attempt_cache_purge,
    binary_provenance,
    fingerprint,
    generate_synthetic_input,
    validate_provenance,
)
from scripts.bench.random_slice import reservoir_slice

EXIT_OK = 0
EXIT_CONSERVATION = 1
EXIT_INVALID = 2

VARIANTS = ("shared-counter", "shared-dashmap", "atomic-only", "thread-local")
DEFAULT_THREADS = (1, 4, 16)
NEAR_ZERO_PCT = 1.0  # a share below 1% of the total gap is flagged inconclusive

# T-05-09: the repo root is resolved from THIS file's location, never from
# user strings — the template substitution cannot be pointed at another tree.
REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILING_DIR = REPO_ROOT / ".planning" / "research" / "profiling"
MICROBENCH_MAIN = PROFILING_DIR / "microbench_main.rs"
MICROBENCH_TOML = PROFILING_DIR / "microbench_Cargo.toml"
MICROBENCH_LOCK = PROFILING_DIR / "microbench_Cargo.lock"
LOCK_REPO_PATH = ".planning/research/profiling/microbench_Cargo.lock"
SCRATCH = REPO_ROOT / "scripts" / "bench" / "scratch"
CRATE_DIR = SCRATCH / "microbench"

REQUIRED_RECORD_KEYS = (
    "variant", "threads", "k", "reads", "windows", "distinct", "elapsed_ns",
    "ns_per_window", "total_count", "unique_count", "conservation_ok", "rep",
)


class ConservationError(Exception):
    """A raw record failed conservation — the whole run is invalid (exit 1)."""


class InvalidRecords(Exception):
    """Missing cells / malformed JSON / inconsistent inputs (exit 2)."""


def invalid(message):
    """Print an input/infra problem and exit 2 — never evidence."""
    print(f"contention_bench.py: {message}", file=sys.stderr)
    sys.exit(EXIT_INVALID)


def rotation_schedule(cell_names, reps):
    """Pure counterbalanced round-robin schedule (unit-testable, no I/O).

    Round r (1-based) starts at cell index (r-1) mod len(cell_names); every
    round contains every cell exactly once. Thermal/order bias rotates across
    the compared cells instead of accumulating inside one cell's block.
    reps > len(cell_names) wraps the rotation.
    """
    names = list(cell_names)
    if not names:
        raise ValueError("rotation_schedule needs at least one cell name")
    if reps < 1:
        raise ValueError(f"rotation_schedule needs reps >= 1, got {reps}")
    n = len(names)
    return [[names[(r + i) % n] for i in range(n)] for r in range(reps)]


def cell_names_for(threads):
    """Variant-major cell names: shared-counter-t1 ... thread-local-t16."""
    return [f"{v}-t{t}" for v in VARIANTS for t in threads]


def split_cell(cell):
    """'shared-counter-t16' -> ('shared-counter', 16)."""
    variant, t = cell.rsplit("-t", 1)
    return variant, int(t)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_scratch_lockfile(crate_dir, committed_lock):
    """The build never runs unlocked: the scratch lock's bytes must equal the
    committed audited lock (T-05-SC). Missing either file, or any mismatch,
    is invalid (exit 2)."""
    crate_dir = Path(crate_dir)
    committed_lock = Path(committed_lock)
    scratch_lock = crate_dir / "Cargo.lock"
    if not committed_lock.is_file():
        invalid(f"committed microbench lockfile missing: {committed_lock}")
    if not scratch_lock.is_file():
        invalid(f"scratch lockfile missing: {scratch_lock} — refusing to "
                f"build unlocked")
    committed_sha = _sha256(committed_lock)
    scratch_sha = _sha256(scratch_lock)
    if scratch_sha != committed_sha:
        invalid(f"scratch lockfile sha256 {scratch_sha} != committed "
                f"{committed_sha} — the measured dependency graph would "
                f"drift; refusing to build")
    return committed_sha


def materialize_crate(repo_root=REPO_ROOT, crate_dir=CRATE_DIR):
    """Copy the committed template into scratch (T-05-09).

    main.rs -> src/main.rs; Cargo.toml with @REPO_ROOT@ replaced by the repo
    root (resolved from the controller's own __file__ in the default flow);
    committed Cargo.lock -> Cargo.lock, then sha256-verified. No build here.
    """
    repo_root = Path(repo_root)
    crate_dir = Path(crate_dir)
    prof = repo_root / ".planning" / "research" / "profiling"
    main_src = prof / "microbench_main.rs"
    toml_src = prof / "microbench_Cargo.toml"
    lock_src = prof / "microbench_Cargo.lock"
    for src in (main_src, toml_src, lock_src):
        if not src.is_file():
            invalid(f"microbench template file missing: {src}")
    (crate_dir / "src").mkdir(parents=True, exist_ok=True)
    (crate_dir / "src" / "main.rs").write_bytes(main_src.read_bytes())
    template = toml_src.read_text(encoding="utf-8")
    if "@REPO_ROOT@" not in template:
        invalid(f"manifest template has no @REPO_ROOT@ placeholder: {toml_src}")
    (crate_dir / "Cargo.toml").write_text(
        template.replace("@REPO_ROOT@", str(repo_root)), encoding="utf-8")
    (crate_dir / "Cargo.lock").write_bytes(lock_src.read_bytes())
    return verify_scratch_lockfile(crate_dir, lock_src)


def build_crate(crate_dir=CRATE_DIR):
    """cargo build --release --locked (list form) — the audited committed
    graph is exactly what gets measured."""
    crate_dir = Path(crate_dir)
    proc = subprocess.run(
        ["cargo", "build", "--release", "--locked",
         "--manifest-path", str(crate_dir / "Cargo.toml")],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"microbench build failed rc={proc.returncode}\n"
            f"trailing stderr:\n{proc.stderr[-800:]}")
    exe = crate_dir / "target" / "release" / "rk-microbench"
    if not exe.is_file():
        raise RuntimeError(f"built microbench executable missing: {exe}")
    return exe


def load_microbench_json(path):
    """Parse one microbench --json output; malformed/missing fields are
    InvalidRecords (exit 2), never silently skipped."""
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidRecords(f"microbench JSON unreadable: {path} ({exc})")
    if not isinstance(doc, dict) or not isinstance(doc.get("records"), list):
        raise InvalidRecords(
            f"microbench JSON has no records array: {path}")
    records = doc["records"]
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            raise InvalidRecords(f"record {i} is not an object: {path}")
        for key in REQUIRED_RECORD_KEYS:
            if key not in rec:
                raise InvalidRecords(
                    f"record {i} missing field {key!r}: {path}")
    return records


def _is_pos_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _is_pos_num(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and value > 0)


def validate_records(records, required_cells):
    """Conservation first (exit 1), then validity/coverage (exit 2).

    Conservation is RECOMPUTED from the raw counts — the conservation_ok
    flag alone is never trusted (defense in depth). All records must describe
    the same input (k/reads/windows/distinct) and cover every required
    (variant, threads) cell.
    """
    if not records:
        raise InvalidRecords("no raw records — nothing measured")
    for i, rec in enumerate(records):
        if rec.get("conservation_ok") is not True:
            raise ConservationError(
                f"record {i} ({rec.get('variant')}-t{rec.get('threads')}): "
                f"conservation_ok is not True")
        if (rec.get("total_count") != rec.get("windows")
                or rec.get("unique_count") != rec.get("distinct")):
            raise ConservationError(
                f"record {i} ({rec.get('variant')}-t{rec.get('threads')}): "
                f"counts do not reconcile (total={rec.get('total_count')} "
                f"windows={rec.get('windows')} unique={rec.get('unique_count')} "
                f"distinct={rec.get('distinct')})")
    identities = set()
    seen = set()
    for i, rec in enumerate(records):
        variant, threads = rec.get("variant"), rec.get("threads")
        if variant not in VARIANTS:
            raise InvalidRecords(f"record {i}: unknown variant {variant!r}")
        if not _is_pos_int(threads):
            raise InvalidRecords(f"record {i}: invalid threads {threads!r}")
        if not _is_pos_int(rec.get("windows")) or not _is_pos_int(rec.get("distinct")):
            raise InvalidRecords(
                f"record {i}: windows/distinct must be positive integers")
        if not _is_pos_num(rec.get("ns_per_window")):
            raise InvalidRecords(
                f"record {i}: ns_per_window must be positive, "
                f"got {rec.get('ns_per_window')!r}")
        identities.add((rec.get("k"), rec.get("reads"),
                        rec.get("windows"), rec.get("distinct")))
        seen.add((variant, threads))
    if len(identities) != 1:
        raise InvalidRecords(
            f"records describe different inputs (k/reads/windows/distinct): "
            f"{sorted(identities)} — a timing comparison would be meaningless")
    missing = set(required_cells) - seen
    if missing:
        raise InvalidRecords(
            f"missing cells: {sorted(f'{v}-t{t}' for v, t in missing)}")


def attribute(records, thread_counts=DEFAULT_THREADS):
    """Pure attribution-v1 reduction (unit-tested with hand-built numbers).

    Medians per (variant, threads) cell across rounds; the headline shares
    are computed at the MAXIMUM measured thread count (t16 by default), where
    the in-vivo contention manifests. Negative/near-zero shares are recorded
    as measured with an inconclusive note — never clamped.
    """
    threads = tuple(sorted(thread_counts))
    required = {(v, t) for v in VARIANTS for t in threads}
    validate_records(records, required)

    groups = defaultdict(list)
    for rec in records:
        groups[(rec["variant"], rec["threads"])].append(rec["ns_per_window"])
    medians = {f"{v}-t{t}": statistics.median(groups[(v, t)])
               for v in VARIANTS for t in threads}

    t_max, t_min = threads[-1], threads[0]
    sc = medians[f"shared-counter-t{t_max}"]
    sd = medians[f"shared-dashmap-t{t_max}"]
    ao = medians[f"atomic-only-t{t_max}"]
    tl = medians[f"thread-local-t{t_max}"]

    global_share = sc - sd
    bandwidth_share = sd - tl
    gap = sc - tl
    notes = []
    if gap > 0:
        global_pct = 100.0 * global_share / gap
        bandwidth_pct = 100.0 * bandwidth_share / gap
    else:
        global_pct = None
        bandwidth_pct = None
        notes.append(
            f"inconclusive: total gap (shared_counter - thread_local at "
            f"t{t_max}) is {gap} ns/window <= 0 — percentage shares undefined")
    for label, share, pct in (
            ("global-atomics", global_share, global_pct),
            ("memory-bandwidth", bandwidth_share, bandwidth_pct)):
        if share <= 0:
            notes.append(
                f"inconclusive: {label} share is {share} ns/window <= 0 — the "
                f"subtraction does not isolate this mechanism on this host; "
                f"recorded as measured, not clamped")
        elif pct is not None and pct < NEAR_ZERO_PCT:
            notes.append(
                f"inconclusive: {label} share is {pct:.3f}% of the total gap "
                f"(< {NEAR_ZERO_PCT}%) — near-zero, do not read as decisive")
    multiplier = sc / medians[f"shared-counter-t{t_min}"]
    if t_max == t_min:
        notes.append(
            "inconclusive: only one thread count measured — contention "
            "multiplier is trivially 1.0")

    return {
        "per_cell_medians": medians,
        "shared_counter_ns": sc,
        "shared_dashmap_without_global_atomics_ns": sd,
        "atomic_only_ns": ao,
        "thread_local_ns": tl,
        "global_atomics_attribution_ns": global_share,
        "global_atomics_attribution_pct": global_pct,
        "memory_bandwidth_attribution_ns": bandwidth_share,
        "memory_bandwidth_attribution_pct": bandwidth_pct,
        "contention_multiplier": multiplier,
        "attribution_threads": t_max,
        "multiplier_threads": [t_min, t_max],
        "notes": notes,
    }


def run_cell(exe, variant, threads, args, input_path, json_path):
    """One microbench invocation (--reps 1), list-form argv (T-05-09).

    The microbench's own conservation abort (exit 1) maps to
    ConservationError so the run-level exit code stays 1; any other non-zero
    exit is an infrastructure failure (exit 2 upstream).
    """
    proc = subprocess.run(
        [str(exe), "--k", str(args.k), "--reads", str(args.reads),
         "--threads", str(threads), "--reps", "1", "--variant", variant,
         "--input", str(input_path), "--json", str(json_path)],
        capture_output=True, text=True)
    if proc.returncode == 1:
        raise ConservationError(
            f"microbench conservation abort for {variant}-t{threads}\n"
            f"trailing stderr:\n{proc.stderr[-500:]}")
    if proc.returncode != 0:
        raise RuntimeError(
            f"microbench failed rc={proc.returncode} for {variant}-t{threads}\n"
            f"trailing stderr:\n{proc.stderr[-500:]}")
    return load_microbench_json(json_path)


def provision_input(args, scratch):
    """Real random-record subslice (evidence) or synthetic smoke input."""
    if args.synthetic:
        input_path = scratch / "contention_smoke.fq"
        generate_synthetic_input(args.reads, 150, args.seed, input_path)
        return input_path, None
    input_path = scratch / "contention_slice.fq"
    manifest_path = scratch / "contention_slice.manifest.json"
    manifest = reservoir_slice(args.input, args.reads, args.seed,
                               input_path, manifest_path)
    return input_path, manifest


def build_evidence(args, input_path, selection_manifest, records, cells,
                   schedule, attribution, exe, lock_sha256):
    """Assemble the provenance-bearing attribution-v1 evidence doc."""
    threads = tuple(sorted(set(args.threads)))
    t_max, t_min = threads[-1], threads[0]
    method = {
        "version": "attribution-v1",
        "attribution_threads": t_max,
        "near_zero_threshold_pct": NEAR_ZERO_PCT,
        "formulas": {
            "global_atomics_attribution_ns":
                f"shared_counter_ns(t{t_max}) - "
                f"shared_dashmap_without_global_atomics_ns(t{t_max})",
            "memory_bandwidth_attribution_ns":
                f"shared_dashmap_without_global_atomics_ns(t{t_max}) - "
                f"thread_local_ns(t{t_max})",
            "global_atomics_attribution_pct":
                f"100 * global_atomics_attribution_ns / "
                f"(shared_counter_ns(t{t_max}) - thread_local_ns(t{t_max}))",
            "memory_bandwidth_attribution_pct":
                f"100 * memory_bandwidth_attribution_ns / "
                f"(shared_counter_ns(t{t_max}) - thread_local_ns(t{t_max}))",
            "contention_multiplier":
                f"shared_counter_ns(t{t_max}) / shared_counter_ns(t{t_min})",
            "per_cell_medians":
                "median of ns_per_window across counterbalanced rounds for "
                "each (variant, threads) cell",
        },
        "notes": attribution["notes"],
    }
    return {
        "schema_version": 1,
        "method": method,
        "schedule": {
            "policy": "round-robin-rotation",
            "cell_order": list(cells),
            "warmup_order": list(cells),
            "rounds": schedule,
        },
        "microbench_lockfile": {"path": LOCK_REPO_PATH, "sha256": lock_sha256},
        "records": records,
        "per_cell_medians": attribution["per_cell_medians"],
        "shared_counter_ns": attribution["shared_counter_ns"],
        "shared_dashmap_without_global_atomics_ns":
            attribution["shared_dashmap_without_global_atomics_ns"],
        "atomic_only_ns": attribution["atomic_only_ns"],
        "thread_local_ns": attribution["thread_local_ns"],
        "global_atomics_attribution_ns":
            attribution["global_atomics_attribution_ns"],
        "global_atomics_attribution_pct":
            attribution["global_atomics_attribution_pct"],
        "memory_bandwidth_attribution_ns":
            attribution["memory_bandwidth_attribution_ns"],
        "memory_bandwidth_attribution_pct":
            attribution["memory_bandwidth_attribution_pct"],
        "contention_multiplier": attribution["contention_multiplier"],
        "params": {
            "k": args.k,
            "reads": args.reads,
            "seed": args.seed,
            "thread_counts": list(threads),
            "reps": args.reps,
            "cooldown_s": args.cooldown_s,
            "synthetic": bool(args.synthetic),
            "input": str(args.input) if args.input else None,
        },
        "input_fingerprint": fingerprint(input_path),
        "selection_manifest": selection_manifest,
        "cache_state": (
            "warm page cache on the dev host; no sudo cold-cache purge "
            "available — per-rep cache_state labels are the honest record "
            "(attempt_cache_purge)"),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "created": datetime.now(timezone.utc).isoformat(),
        "provenance": binary_provenance(exe, "release"),
    }


def run(args):
    """Full controller flow: materialize, build, provision, measure, emit."""
    threads = tuple(sorted(set(args.threads)))
    if not args.synthetic:
        if not args.input:
            invalid("--input is required unless --synthetic (evidence must "
                    "use real reads)")
        if not Path(args.input).is_file():
            invalid(f"input not found: {args.input}")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    lock_sha256 = materialize_crate(REPO_ROOT, CRATE_DIR)
    exe = build_crate(CRATE_DIR)
    input_path, selection_manifest = provision_input(args, SCRATCH)

    cells = cell_names_for(threads)
    schedule = rotation_schedule(cells, args.reps)

    # One discarded warmup per cell — conservation still enforced (a broken
    # measurement must fail fast, not poison the measured rounds).
    for cell in cells:
        variant, t = split_cell(cell)
        warm = run_cell(exe, variant, t, args, input_path,
                        SCRATCH / f"contention_warmup_{cell}.json")
        validate_records(warm, {(variant, t)})
        print(f"warmup {cell}: discarded ({warm[0]['ns_per_window']:.1f} "
              f"ns/window)")
        time.sleep(args.cooldown_s)

    records = []
    for rnd, round_order in enumerate(schedule):
        for position, cell in enumerate(round_order):
            variant, t = split_cell(cell)
            cache_state = attempt_cache_purge()
            recs = run_cell(exe, variant, t, args, input_path,
                            SCRATCH / f"contention_{cell}_r{rnd}.json")
            if len(recs) != 1:
                raise InvalidRecords(
                    f"expected exactly 1 record for {cell} round {rnd}, "
                    f"got {len(recs)}")
            rec = recs[0]
            rec["cell"] = cell
            rec["round"] = rnd
            rec["arm_order"] = position
            rec["cache_state"] = cache_state
            records.append(rec)
            print(f"round {rnd} [{position:2d}] {cell}: "
                  f"{rec['ns_per_window']:.1f} ns/window "
                  f"(cache_state={cache_state})")
            time.sleep(args.cooldown_s)

    attribution = attribute(records, threads)
    doc = build_evidence(args, input_path, selection_manifest, records,
                         cells, schedule, attribution, exe, lock_sha256)
    try:
        validate_provenance(doc)
    except ValueError as exc:
        invalid(f"evidence doc failed provenance validation: {exc}")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")

    print(f"contention evidence written to {out_path}")
    print(f"shared_counter_ns(t{attribution['attribution_threads']}) = "
          f"{attribution['shared_counter_ns']!r}")
    print(f"global_atomics_attribution_ns = "
          f"{attribution['global_atomics_attribution_ns']!r} "
          f"({attribution['global_atomics_attribution_pct']!r} pct)")
    print(f"memory_bandwidth_attribution_ns = "
          f"{attribution['memory_bandwidth_attribution_ns']!r} "
          f"({attribution['memory_bandwidth_attribution_pct']!r} pct)")
    print(f"contention_multiplier = {attribution['contention_multiplier']!r}")
    for note in attribution["notes"]:
        print(f"NOTE: {note}")
    print(f"CONTENTION EVIDENCE OK records={len(records)} "
          f"cells={len(cells)} rounds={len(schedule)}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="PROF-03 contention microbench controller: four mechanism "
                    "arms in counterbalanced rounds, attribution-v1 evidence. "
                    "Exit 0 valid / 1 conservation failure / 2 invalid.")
    parser.add_argument("--input", default=None,
                        help="real source .fq.gz (random-record subslice; "
                             "required unless --synthetic)")
    parser.add_argument("--reads", type=int, default=200000,
                        help="reads in the measured subslice (default 200000)")
    parser.add_argument("--seed", type=int, default=20261112,
                        help="reservoir selection seed (default 20261112)")
    parser.add_argument("--threads", type=int, nargs="+",
                        default=list(DEFAULT_THREADS),
                        help="thread counts (default 1 4 16)")
    parser.add_argument("--reps", type=int, default=3,
                        help="measured counterbalanced rounds (default 3)")
    parser.add_argument("--k", type=int, default=21, help="k-mer size")
    parser.add_argument("--cooldown-s", type=int, default=DEFAULT_COOLDOWN_S,
                        help="cooldown seconds between runs")
    parser.add_argument("--synthetic", action="store_true",
                        help="smoke-only synthetic input (evidence must use "
                             "real reads — synthetic all-unique keys have the "
                             "wrong duplication structure)")
    parser.add_argument("--out", required=True, help="evidence JSON output path")
    args = parser.parse_args(argv)
    if args.reads < 1:
        parser.error("--reads must be >= 1")
    if args.reps < 1:
        parser.error("--reps must be >= 1")
    if args.k < 1 or args.k > 32:
        parser.error("--k must be in 1..32 (u64 pre-encoded keys)")
    if any(t < 1 for t in args.threads):
        parser.error("--threads values must be >= 1")
    if args.cooldown_s < 0:
        parser.error("--cooldown-s must be >= 0")

    try:
        run(args)
    except SystemExit:
        raise
    except ConservationError as exc:
        print(f"contention_bench.py: conservation failure: {exc}",
              file=sys.stderr)
        sys.exit(EXIT_CONSERVATION)
    except Exception as exc:  # noqa: BLE001 — infra failures are exit 2
        print(f"contention_bench.py: {exc}", file=sys.stderr)
        sys.exit(EXIT_INVALID)
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
