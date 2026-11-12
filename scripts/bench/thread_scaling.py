#!/usr/bin/env python3
"""PROF-02 standing thread-scaling gate (Phase 5 tracer, 05-01).

Measures `rustkmer count` at --threads 1 / 4 / 16 on ONE provisioned input
and gates on material scaling: speedup_t4 = median_wall(t1)/median_wall(t4)
and speedup_t16 likewise must BOTH reach --min-speedup (default 1.3).
t4-vs-t16 is deliberately unconstrained — CI runners have 2-4 cores and t16
oversubscription must not keep the gate red after Phase 6 fixes --threads.

EXPECTED RED on the current tree: --threads is a silent no-op (17 OS threads
at --threads 1, profiling evidence 2026-11-12), so t1 ~ t4 ~ t16 and both
speedups sit near 1.0. The harness task is DONE when this gate correctly
OBSERVES that bug — Phase 6 (PAR-01) turns it green. Never soften the exit
code, never `|| true`, never continue-on-error.

Exit codes are a contract (compare.py semantics):
  0 — GREEN: both speedups >= --min-speedup (inclusive boundary).
  1 — RED: a measured no-op/regression — at least one speedup below the
      threshold. ONLY the verdict path exits 1; infrastructure failures
      exit 2, so an exit code alone is never the RED evidence.
  2 — invalid: missing arm, cross-arm count mismatch, zero counts,
      malformed/missing provenance, unsupported platform, provisioning or
      measurement failure. No verdict line is printed on any exit-2 path.

Whenever a verdict is produced (run mode and --current), exactly one
machine-greppable line is printed on stdout AFTER the validated doc has been
written (run mode) or loaded (--current):

  SCALING VERDICT result=RED speedup_t4=<v> speedup_t16=<v> min_speedup=<v>

The three numbers are emitted with repr() so they round-trip exactly to the
stored floats. --measure-only writes the doc without a verdict (exit 0 when
schema+provenance valid) so CI can upload the artifact before the verdict
step; it never prints a verdict line.

Methodology (CONTEXT guardrails): parity BEFORE timing (identical nonzero
unique/total across all three arms), one discarded warmup per arm, then
--reps counterbalanced rounds — round r runs ALL arms exactly once in
round-robin rotated order so thermal/order bias rotates across arms instead
of accumulating inside one arm's sequential block. The schedule is persisted
in the doc; every raw rep carries its round index and honest cache_state.
Medians via bench.reduce_arm across rounds. Provenance via the shared
bench.binary_provenance (actual executable bytes + git HEAD + dirty flag).

Python 3.11+ stdlib only — no jellyfish, no PyO3, no human dataset needed.
"""

import argparse
import dataclasses
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    # Executed as a script (python3 scripts/bench/thread_scaling.py): the repo
    # root is not on sys.path yet. Insert it BEFORE importing so the harness
    # package resolves to this checkout in one shot — some environments carry
    # an unrelated `scripts` namespace package in site-packages that would
    # otherwise win the first import (compare.py's fixup, replicated).
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.bench.bench import (
    DEFAULT_COOLDOWN_S,
    DEFAULT_RUSTKMER,
    SCHEMA_VERSION,
    BenchmarkConfig,
    attempt_cache_purge,
    binary_provenance,
    fingerprint,
    gather_inputs,
    measure,
    provision_slice,
    provision_synthetic,
    reduce_arm,
    rustkmer_count_cmd,
    stats,
    validate_provenance,
    validate_schema,
)

EXIT_GREEN = 0
EXIT_RED = 1
EXIT_INVALID = 2

THREAD_COUNTS = (1, 4, 16)
DEFAULT_MIN_SPEEDUP = 1.3
SUPPORTED_SYSTEMS = ("Darwin", "Linux")
DEFAULT_OUT = Path(__file__).resolve().parent / "scratch" / "scaling.json"


def invalid(message):
    """Print an input/infra problem and exit 2 — never a verdict (compare.py
    stance: a gate with broken inputs is not a gate)."""
    print(f"thread_scaling.py: {message}", file=sys.stderr)
    sys.exit(EXIT_INVALID)


def rotation_schedule(arm_names, reps):
    """Pure counterbalanced round-robin schedule (unit-testable, no I/O).

    Round r (1-based) starts at arm index (r-1) mod len(arm_names); every
    round contains every arm exactly once. With [t1, t4, t16] and reps=3:
    [t1,t4,t16], [t4,t16,t1], [t16,t1,t4] — thermal/order bias rotates
    across arms instead of accumulating inside one arm's sequential block.
    reps > len(arm_names) wraps the rotation.
    """
    names = list(arm_names)
    if not names:
        raise ValueError("rotation_schedule needs at least one arm name")
    if reps < 1:
        raise ValueError(f"rotation_schedule needs reps >= 1, got {reps}")
    n = len(names)
    return [[names[(r + i) % n] for i in range(n)] for r in range(reps)]


def _arm_for_threads(doc, threads):
    """The single arm whose name ends in -t{threads}, or None."""
    suffix = f"-t{threads}"
    matches = [a for a in doc.get("arms", [])
               if isinstance(a, dict) and str(a.get("name", "")).endswith(suffix)]
    return matches[0] if len(matches) == 1 else None


def scaling_verdict(doc, min_speedup):
    """Compute the gate verdict from a results doc.

    Returns (exit_code, report_lines, verdict_block). verdict_block is None
    on every exit-2 path (no verdict may be printed or persisted then).
    Exit 0 only when BOTH speedup_t4 and speedup_t16 >= min_speedup
    (inclusive boundary, compare.py convention); exit 1 when either is
    below (measured no-op/regression); exit 2 for invalid inputs.
    """
    try:
        validate_schema(doc)
    except ValueError as exc:
        return EXIT_INVALID, [f"schema invalid: {exc}"], None
    try:
        validate_provenance(doc)
    except ValueError as exc:
        return EXIT_INVALID, [f"provenance invalid: {exc}"], None

    plat = doc.get("platform")
    system = plat.get("system") if isinstance(plat, dict) else None
    if system not in SUPPORTED_SYSTEMS:
        return EXIT_INVALID, [
            f"unsupported platform {system!r} (expected one of "
            f"{SUPPORTED_SYSTEMS}) — never a false PASS"], None

    arms = {}
    for t in THREAD_COUNTS:
        arm = _arm_for_threads(doc, t)
        if arm is None:
            return EXIT_INVALID, [
                f"missing or ambiguous t{t} arm (expected exactly one arm "
                f"named *-t{t})"], None
        arms[t] = arm

    counts = set()
    for t, arm in arms.items():
        unique, total = arm.get("unique_kmers"), arm.get("total_kmers")
        for label, value in (("unique_kmers", unique), ("total_kmers", total)):
            if (not isinstance(value, int) or isinstance(value, bool)
                    or value <= 0):
                return EXIT_INVALID, [
                    f"arm {arm['name']!r}: {label} must be a positive "
                    f"integer, got {value!r} — zero/absent counts are a "
                    f"silent input failure, never a verdict"], None
        counts.add((unique, total))
    if len(counts) != 1:
        return EXIT_INVALID, [
            f"cross-arm count mismatch: {sorted(counts)} — arms counted "
            f"DIFFERENT things; a timing comparison would be meaningless "
            f"(parity before timing)"], None

    medians = {}
    for t, arm in arms.items():
        med = arm.get("medians")
        wall = med.get("wall_s") if isinstance(med, dict) else None
        if (not isinstance(wall, (int, float)) or isinstance(wall, bool)
                or wall <= 0):
            return EXIT_INVALID, [
                f"arm {arm['name']!r}: medians.wall_s must be a positive "
                f"number, got {wall!r} — no real timing observation"], None
        medians[t] = float(wall)

    speedup_t4 = medians[1] / medians[4]
    speedup_t16 = medians[1] / medians[16]
    passed = speedup_t4 >= min_speedup and speedup_t16 >= min_speedup
    verdict = {
        "result": "GREEN" if passed else "RED",
        "speedup_t4": speedup_t4,
        "speedup_t16": speedup_t16,
        "min_speedup": float(min_speedup),
    }
    unique, total = next(iter(counts))
    lines = [f"scaling gate: min_speedup={min_speedup!r} "
             f"(both ratios must reach it; t4-vs-t16 unconstrained)"]
    for t in THREAD_COUNTS:
        lines.append(f"  {arms[t]['name']}: median wall {medians[t]:.3f}s "
                     f"unique={unique} total={total}")
    for label, value in (("speedup_t4", speedup_t4),
                         ("speedup_t16", speedup_t16)):
        lines.append(f"  {label} = {value!r} "
                     f"{'>= ' if value >= min_speedup else '< '}"
                     f"{min_speedup!r}")
    return (EXIT_GREEN if passed else EXIT_RED), lines, verdict


def verdict_line(verdict):
    """The one machine-greppable stdout line; repr() round-trips the floats."""
    return (f"SCALING VERDICT result={verdict['result']} "
            f"speedup_t4={verdict['speedup_t4']!r} "
            f"speedup_t16={verdict['speedup_t16']!r} "
            f"min_speedup={verdict['min_speedup']!r}")


def provision_input(args, scratch):
    """Provision the ONE measured input via the requested mode."""
    if args.mode == "synthetic":
        inputs = provision_synthetic(args.reads, scratch)
        return inputs[0]
    if not args.input:
        invalid("slice mode requires --input (gz file, glob, or directory)")
    resolved = gather_inputs(args.input)
    if not resolved:
        invalid(f"slice mode: no inputs resolved from {args.input!r}")
    slices = provision_slice(resolved, args.slice_reads, scratch)
    return slices[0]


def measure_scaling(args, input_path, scratch):
    """Warmup + parity-before-timing + counterbalanced measured rounds.

    Returns (arms, schedule_dict). Each arm's command derives from ONE
    BenchmarkConfig (only threads and the output path vary), list-form argv
    throughout — no shell strings (T-05-01).
    """
    base_cfg = BenchmarkConfig(k=args.k, canonical=True, threads=1,
                               inputs=[input_path])
    arm_names = [f"rk{args.k}-t{t}" for t in THREAD_COUNTS]
    cmds, dbs = {}, {}
    for t, name in zip(THREAD_COUNTS, arm_names):
        cfg = dataclasses.replace(base_cfg, threads=t)
        db = scratch / f"scaling_{name}.rkdb"
        dbs[name] = db
        cmds[name] = rustkmer_count_cmd(cfg, db, args.rustkmer)

    schedule = rotation_schedule(arm_names, args.reps)
    total_runs = len(arm_names) + args.reps * len(arm_names)
    done_runs = 0

    def cooldown_gap():
        nonlocal done_runs
        done_runs += 1
        if done_runs < total_runs:
            time.sleep(args.cooldown_s)

    # One discarded warmup per arm (t1, t4, t16 order) — also produces the
    # .rkdb files the pre-timing parity gate reads.
    for name in arm_names:
        measure(cmds[name])
        cooldown_gap()

    # Parity BEFORE any timing is accepted: identical nonzero counts across
    # all three arms, or exit 2 (a mismatch is invalid input, not a verdict).
    warmup_counts = {}
    for name in arm_names:
        st = stats(dbs[name], args.rustkmer)
        warmup_counts[name] = (st["unique_kmers"], st["total_kmers"])
    if len(set(warmup_counts.values())) != 1:
        invalid(f"parity before timing failed: {warmup_counts} — arms "
                f"counted different things on the same input")
    unique, total = warmup_counts[arm_names[0]]
    if unique <= 0 or total <= 0:
        invalid(f"parity before timing: zero counts ({warmup_counts}) — "
                f"silent input failure, never a measurement")

    reps_by_arm = {name: [] for name in arm_names}
    for rnd, round_order in enumerate(schedule):
        for position, name in enumerate(round_order):
            cache_state = attempt_cache_purge()
            rep = measure(cmds[name])
            rep["cache_state"] = cache_state
            rep["round"] = rnd
            rep["arm_order"] = position
            reps_by_arm[name].append(rep)
            cooldown_gap()

    arms = []
    for t, name in zip(THREAD_COUNTS, arm_names):
        st = stats(dbs[name], args.rustkmer)
        reduced = reduce_arm(reps_by_arm[name])
        arms.append({
            "name": name,
            "tool": "rustkmer",
            "threads": t,
            "reps": reps_by_arm[name],
            "medians": {
                "wall_s": reduced["median_wall_s"],
                "peak_rss_bytes": reduced["median_peak_rss_bytes"],
                "cv_wall_pct": reduced["cv_wall_pct"],
                "cv_warning": reduced["cv_warning"],
            },
            "unique_kmers": st["unique_kmers"],
            "total_kmers": st["total_kmers"],
        })
    return arms, {"policy": "round-robin-rotation",
                  "warmup_order": list(arm_names),
                  "rounds": schedule}


def build_doc(args, input_path, arms, schedule):
    """Assemble the schema-v1 provenance-bearing results doc (no verdict)."""
    params = {
        "k": args.k,
        "canonical": True,
        "thread_counts": list(THREAD_COUNTS),
        "reps": args.reps,
        "cooldown_s": args.cooldown_s,
        "min_speedup": args.min_speedup,
        "rustkmer": str(args.rustkmer),
    }
    if args.mode == "synthetic":
        params["reads"] = args.reads
    else:
        params["slice_reads"] = args.slice_reads
        params["input"] = str(args.input)
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": args.mode,
        "params": params,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "created": datetime.now(timezone.utc).isoformat(),
        "input_fingerprint": [fingerprint(input_path)],
        "arms": arms,
        "schedule": schedule,
        "provenance": binary_provenance(args.rustkmer, "release"),
    }


def write_doc(doc, out_path):
    """Validate schema AND provenance, then write — an invalid artifact
    never reaches disk (compare.py/CI consume it as a gate input)."""
    try:
        validate_schema(doc)
        validate_provenance(doc)
    except ValueError as exc:
        invalid(f"results doc failed validation: {exc}")
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")


def run_current(args):
    """--current DOC: verdict-only from an existing doc (unit tests drive
    this path; CI runs it after uploading the --measure-only artifact)."""
    try:
        with open(args.current, encoding="utf-8") as fh:
            doc = json.load(fh)
    except FileNotFoundError:
        invalid(f"current doc not found: {args.current}")
    except OSError as exc:
        invalid(f"current doc unreadable: {args.current} ({exc})")
    except json.JSONDecodeError as exc:
        invalid(f"current doc is not parseable JSON: {args.current} ({exc})")
    code, lines, verdict = scaling_verdict(doc, args.min_speedup)
    stream = sys.stderr if code == EXIT_INVALID else sys.stdout
    for line in lines:
        print(line, file=stream)
    if verdict is not None:
        print(verdict_line(verdict))
    sys.exit(code)


def run_gate(args):
    """Default run+gate (and --measure-only): provision, measure, emit."""
    if platform.system() not in SUPPORTED_SYSTEMS:
        invalid(f"unsupported platform {platform.system()!r} (expected one "
                f"of {SUPPORTED_SYSTEMS})")
    if not Path(args.rustkmer).is_file():
        invalid(f"rustkmer binary not found: {args.rustkmer} — build it "
                f"first (cargo build --release --locked)")
    out_path = Path(args.out)
    scratch = out_path.parent
    scratch.mkdir(parents=True, exist_ok=True)
    input_path = provision_input(args, scratch)
    arms, schedule = measure_scaling(args, input_path, scratch)
    doc = build_doc(args, input_path, arms, schedule)

    if args.measure_only:
        # No verdict block, no verdict line — CI uploads this artifact
        # before the verdict step (--current) consumes it.
        write_doc(doc, out_path)
        print(f"measure-only results written to {out_path}")
        sys.exit(EXIT_GREEN)

    code, lines, verdict = scaling_verdict(doc, args.min_speedup)
    if code == EXIT_INVALID:
        for line in lines:
            print(f"thread_scaling.py: {line}", file=sys.stderr)
        sys.exit(code)
    doc["verdict"] = verdict
    write_doc(doc, out_path)
    for line in lines:
        print(line)
    print(f"results written to {out_path}")
    # The verdict line is printed only AFTER the validated doc is on disk.
    print(verdict_line(verdict))
    sys.exit(code)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="PROF-02 thread-scaling gate: t1/t4/t16 count arms, "
                    "counterbalanced rounds, exit 0 GREEN / 1 RED / 2 "
                    "invalid. Expected RED while --threads is a no-op.")
    parser.add_argument("--mode", choices=["synthetic", "slice"],
                        default="synthetic",
                        help="input provisioning mode (default synthetic; "
                             "slice uses head selection for comparability "
                             "with the research matrix)")
    parser.add_argument("--input", default=None,
                        help="gz input file, glob, or directory (slice mode)")
    parser.add_argument("--reads", type=int, default=500000,
                        help="reads per synthetic input (default 500000)")
    parser.add_argument("--slice-reads", type=int, default=4000000,
                        help="reads per slice in slice mode (default "
                             "4000000, first-N extraction)")
    parser.add_argument("--k", type=int, default=21, help="k-mer size")
    parser.add_argument("--reps", type=int, default=3,
                        help="measured counterbalanced rounds (default 3)")
    parser.add_argument("--cooldown-s", type=int, default=DEFAULT_COOLDOWN_S,
                        help="cooldown seconds between runs (thermal/order "
                             "bias defense)")
    parser.add_argument("--min-speedup", type=float,
                        default=DEFAULT_MIN_SPEEDUP,
                        help="minimum t1/t4 AND t1/t16 median-wall speedup "
                             "for GREEN (inclusive; default 1.3)")
    parser.add_argument("--rustkmer", default=DEFAULT_RUSTKMER,
                        help="path to the rustkmer RELEASE binary")
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help="results doc output path")
    parser.add_argument("--measure-only", action="store_true",
                        help="measure and write the doc without a verdict "
                             "(exit 0 when schema+provenance valid); no "
                             "SCALING VERDICT line is printed")
    parser.add_argument("--current", default=None,
                        help="verdict-only from an existing results doc "
                             "(no measurement)")
    args = parser.parse_args(argv)
    if args.k < 1 or args.k > 64:
        parser.error("--k must be in 1..64")
    if args.reps < 1:
        parser.error("--reps must be >= 1")
    if args.reads < 1:
        parser.error("--reads must be >= 1")
    if args.slice_reads < 1:
        parser.error("--slice-reads must be >= 1")
    if args.cooldown_s < 0:
        parser.error("--cooldown-s must be >= 0")
    if args.min_speedup <= 0:
        parser.error("--min-speedup must be > 0")
    if args.measure_only and args.current:
        parser.error("--measure-only and --current are mutually exclusive")

    if args.current:
        run_current(args)
    else:
        run_gate(args)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — fail loudly, no traceback noise
        # Infrastructure failures are INVALID (exit 2), never exit 1: the
        # RED exit code is reserved for the measured verdict, so an uncaught
        # exception can never masquerade as the expected-RED observation.
        print(f"thread_scaling.py: {exc}", file=sys.stderr)
        sys.exit(EXIT_INVALID)