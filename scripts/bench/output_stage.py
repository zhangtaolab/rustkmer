#!/usr/bin/env python3
"""OUT-01 standing output-stage gate (Phase 8 tracer, 08-01).

Measures the CLI's counting-OUTPUT stage in isolation: the same input and
binary run twice per round — the default sorted `.rkdb` write (`sorted`) and
the same argv plus `--no-sort` (`unsorted`). The difference between their
median walls is the sort-attributed delta the phase must collapse.

STANDING GATE: `capture` records the immutable PRE-change baseline
(`pre/phase8_output_stage_pre.json`, measured on the untouched tree);
`compare` re-measures the same two arms after the refactor and issues a
GREEN verdict only when ALL of:

  * the post sorted `.rkdb` sha256 equals the baseline sha256 (slice-scale
    byte identity — the refactor changed bytes, not just the clock);
  * the post sorted median wall is STRICTLY below the baseline sorted median
    wall (a real stage drop, not noise);
  * the raw `sort_delta_s` is at most 0.5 x the baseline delta (inclusive
    boundary, compare.py's convention);
  * the post sorted median peak RSS is at most the baseline median peak RSS
    (the consuming collection releases each partition table as it drains, so
    memory must not grow).

Exit codes are a contract (compare.py semantics):
  0 — GREEN: every condition above holds.
  1 — RED: a measured failure (non-deterministic sorted output during
      capture, or any failed post-change condition).
  2 — invalid: missing/mismatched arms, cross-arm count mismatch, zero
      counts, malformed/missing provenance, unsupported platform,
      provisioning or measurement failure, or a baseline whose params or
      input fingerprint identify a different measurement. No verdict line is
      printed on any exit-2 path.

`capture` prints no verdict line; it writes the validated pre-change document
and requires `sort_delta_s > --min-pre-sort-delta-s` (default 3.0 s) so an
instrument that is not actually attributing the stable sort stops the plan
instead of recording a meaningless baseline.

`compare` prints exactly one machine-greppable line on stdout, AFTER the
validated post document is on disk:

  OUTPUT STAGE VERDICT result=GREEN|RED sorted_wall_s=<repr>
    sort_delta_s=<repr> sha256_match=<True|False> score=<reason>

Methodology (CONTEXT guardrails): parity BEFORE timing (identical nonzero
unique/total across both arms), ONE provisioned slice (never a second source
and never the full input list), one discarded warmup per arm, then --reps
counterbalanced rounds driven by a pure round-robin rotation — every round
visits every arm exactly once, so thermal/order bias rotates across arms
instead of accumulating inside one arm's block. The schedule is persisted in
BOTH capture and compare documents; every raw rep carries its round index,
its arm order, and the honest cache_state of its own purge attempt.

Python 3.11+ stdlib only — no jellyfish, no PyO3, no shell strings.
"""

import argparse
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    # Executed as a script (python3 scripts/bench/output_stage.py): the repo
    # root is not on sys.path yet. Insert it BEFORE importing so the harness
    # package resolves to this checkout in one shot — some environments carry
    # an unrelated `scripts` namespace package in site-packages that would
    # otherwise win the first import (thread_scaling.py's fixup, replicated).
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
    reduce_arm,
    rustkmer_count_cmd,
    stats,
    validate_provenance,
    validate_schema,
)

EXIT_GREEN = 0
EXIT_RED = 1
EXIT_INVALID = 2

ARM_NAMES = ("sorted", "unsorted")
SORTED_ARM = "sorted"
UNSORTED_ARM = "unsorted"
SUPPORTED_SYSTEMS = ("Darwin", "Linux")

# The Phase 7 slice scope: 4,000,000 head reads of the CRR1936095 r1 part.
DEFAULT_INPUT = (
    "/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/"
    "CRR1936095_r1.part_001.fq.gz"
)
DEFAULT_SLICE_READS = 4_000_000

# The pre-change stable sort must dominate the stage or the instrument is not
# measuring the sort (plan 08-01 Task 1). This is a CAPTURE-only precondition:
# it pins the baseline's meaning, it is never a post-change threshold.
MIN_PRE_SORT_DELTA_S = 3.0


def invalid(message):
    """Print an input/infra problem and exit 2 — never a verdict (compare.py
    stance: a gate with broken inputs is not a gate)."""
    print(f"output_stage.py: {message}", file=sys.stderr)
    sys.exit(EXIT_INVALID)


def rotation_schedule(arm_names, reps):
    """Pure counterbalanced round-robin schedule (unit-testable, no I/O).

    Round r (0-based) starts at arm index r mod len(arm_names); every round
    contains every arm exactly once. With [sorted, unsorted] and reps=3:
    [sorted, unsorted], [unsorted, sorted], [sorted, unsorted] — order bias
    rotates across arms instead of accumulating inside one arm's sequential
    block. reps > len(arm_names) wraps the rotation (thread_scaling.py's
    exact semantics).
    """
    names = list(arm_names)
    if not names:
        raise ValueError("rotation_schedule needs at least one arm name")
    if reps < 1:
        raise ValueError(f"rotation_schedule needs reps >= 1, got {reps}")
    n = len(names)
    return [[names[(r + i) % n] for i in range(n)] for r in range(reps)]


def arm_cmd(cfg, out, rustkmer, arm_name):
    """List-form argv for one output-stage arm (no shell, ever).

    The `unsorted` arm is byte-for-byte the `sorted` argv plus the `--no-sort`
    flag, so the two arms differ in exactly the sort decision: same binary,
    same input, same k/canonical/threads, same output path shape.
    """
    if arm_name not in ARM_NAMES:
        raise ValueError(f"unknown output-stage arm: {arm_name!r}")
    argv = rustkmer_count_cmd(cfg, out, rustkmer)
    if arm_name == UNSORTED_ARM:
        argv.append("--no-sort")
    return argv


def file_sha256(path):
    """sha256 hex of one file, streamed in 1 MiB chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sort_delta_s(sorted_wall_s, unsorted_wall_s):
    """RAW sorted-minus-unsorted median wall delta — never clamped.

    A negative value is an honest observation (the sorted run happened to end
    up faster); `max(0, ...)` would hide it and corrupt both the pre-change
    baseline and the post-change 0.5x verdict, which are computed from this
    number.
    """
    return float(sorted_wall_s) - float(unsorted_wall_s)


def run_measured_rounds(schedule, arm_cmds, cooldown_s, measure_fn=measure,
                        purge_fn=attempt_cache_purge, sleep_fn=time.sleep,
                        on_rep=None):
    """Run the counterbalanced measured rounds; return {arm: [rep dicts]}.

    Each rep records the honest `cache_state` returned by the purge attempt,
    its `round` index, and its `arm_order` position in that round — the same
    per-rep protocol as thread_scaling.py / bench.run_comparison_protocol.
    The dependency functions are injectable so unit tests can record the rep
    shape without a real `sudo purge` and without sleeping.
    """
    arm_names = list(arm_cmds)
    total_runs = sum(len(order) for order in schedule)
    done_runs = 0

    def cooldown_gap():
        nonlocal done_runs
        done_runs += 1
        if done_runs < total_runs:
            sleep_fn(cooldown_s)

    reps_by_arm = {name: [] for name in arm_names}
    for rnd, round_order in enumerate(schedule):
        for position, name in enumerate(round_order):
            cache_state = purge_fn()
            rep = measure_fn(arm_cmds[name])
            rep["cache_state"] = cache_state
            rep["round"] = rnd
            rep["arm_order"] = position
            if on_rep is not None:
                on_rep(name, rep, rnd, position)
            reps_by_arm[name].append(rep)
            cooldown_gap()
    return reps_by_arm


def measure_output_stage(args, input_path, scratch):
    """Warmups, parity-before-timing, determinism, then measured rounds.

    Returns (arms, schedule, sort_delta_s). Both arms derive from ONE
    BenchmarkConfig (only the output path and the --no-sort flag vary), and
    the measured slice is provisioned by the caller.
    """
    cfg = BenchmarkConfig(k=args.k, canonical=True, threads=args.threads,
                          inputs=[input_path])
    dbs = {name: scratch / f"output_stage_{name}.rkdb" for name in ARM_NAMES}
    cmds = {name: arm_cmd(cfg, dbs[name], args.rustkmer, name)
            for name in ARM_NAMES}
    schedule = rotation_schedule(ARM_NAMES, args.reps)
    total_runs = len(ARM_NAMES) + args.reps * len(ARM_NAMES)
    done_runs = 0

    def cooldown_gap():
        nonlocal done_runs
        done_runs += 1
        if done_runs < total_runs:
            time.sleep(args.cooldown_s)

    # One discarded warmup per arm in fixed sorted/unsorted order — also
    # produces the databases the pre-timing parity gate reads.
    for name in ARM_NAMES:
        measure(cmds[name])
        cooldown_gap()

    # Parity BEFORE any timing is accepted: identical nonzero counts across
    # both arms, or exit 2 (a mismatch is invalid input, not a verdict).
    warmup_counts = {}
    for name in ARM_NAMES:
        st = stats(dbs[name], args.rustkmer)
        warmup_counts[name] = (st["unique_kmers"], st["total_kmers"])
    if len(set(warmup_counts.values())) != 1:
        invalid(f"parity before timing failed: {warmup_counts} — the two arms "
                f"counted different things on the same input")
    unique, total = warmup_counts[ARM_NAMES[0]]
    if unique <= 0 or total <= 0:
        invalid(f"parity before timing: zero counts ({warmup_counts}) — "
                f"silent input failure, never a measurement")

    # Determinism starts with the warmup artifact: the sorted database must
    # be byte-identical after the warmup and after every measured sorted rep.
    sorted_hashes = [file_sha256(dbs[SORTED_ARM])]

    def record_sorted_sha(name, rep, _rnd, _position):
        if name == SORTED_ARM:
            rep["sha256"] = file_sha256(dbs[name])
            sorted_hashes.append(rep["sha256"])

    reps_by_arm = run_measured_rounds(
        schedule, cmds, args.cooldown_s, on_rep=record_sorted_sha)

    if len(set(sorted_hashes)) != 1:
        print(f"output_stage.py: sorted .rkdb sha256 is not deterministic "
              f"across reps: {sorted_hashes}", file=sys.stderr)
        sys.exit(EXIT_RED)
    sorted_sha = sorted_hashes[0]

    arms = []
    for name in ARM_NAMES:
        st = stats(dbs[name], args.rustkmer)
        reduced = reduce_arm(reps_by_arm[name])
        arm = {
            "name": name,
            "tool": "rustkmer",
            "threads": args.threads,
            "reps": reps_by_arm[name],
            "medians": {
                "wall_s": reduced["median_wall_s"],
                "peak_rss_bytes": reduced["median_peak_rss_bytes"],
                "cv_wall_pct": reduced["cv_wall_pct"],
                "cv_warning": reduced["cv_warning"],
            },
            "unique_kmers": st["unique_kmers"],
            "total_kmers": st["total_kmers"],
        }
        if name == SORTED_ARM:
            arm["sorted_rkdb_sha256"] = sorted_sha
        arms.append(arm)

    sort_delta = sort_delta_s(
        arms[0]["medians"]["wall_s"], arms[1]["medians"]["wall_s"])
    return arms, schedule, sort_delta


def run_params(args):
    """The measured-scope params persisted in BOTH capture and compare docs."""
    return {
        "k": args.k,
        "canonical": True,
        "threads": args.threads,
        "reps": args.reps,
        "cooldown_s": args.cooldown_s,
        "slice_reads": args.slice_reads,
        "input": str(args.input),
        "rustkmer": str(args.rustkmer),
        "arms": list(ARM_NAMES),
    }


def assemble_doc(params, input_fingerprint, arms, schedule, sort_delta,
                 provenance, platform_block):
    """Assemble the schema-v1 provenance-bearing output-stage document.

    Pure (no I/O, no clock beyond `created`) so unit tests can build a
    document and push it through bench.validate_schema/validate_provenance.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "output_stage",
        "params": params,
        "platform": platform_block,
        "created": datetime.now(timezone.utc).isoformat(),
        "input_fingerprint": input_fingerprint,
        "arms": arms,
        "schedule": schedule,
        "sort_delta_s": sort_delta,
        "provenance": provenance,
    }


def build_doc(args, input_path, arms, schedule, sort_delta):
    """Runtime document assembly: fingerprint, platform, provenance, params."""
    params = run_params(args)
    platform_block = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
    }
    return assemble_doc(
        params=params,
        input_fingerprint=[fingerprint(input_path)],
        arms=arms,
        schedule={
            "policy": "round-robin-rotation",
            "warmup_order": list(ARM_NAMES),
            "rounds": schedule,
        },
        sort_delta=sort_delta,
        provenance=binary_provenance(args.rustkmer, "release"),
        platform_block=platform_block,
    )


def write_doc(doc, out_path):
    """Validate schema AND provenance, then write — an invalid artifact never
    reaches disk (compare mode and CI consume it as a gate input)."""
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


def provision_one_slice(args, scratch):
    """Provision EXACTLY ONE measured slice via the existing provisioning.

    The input directory resolves two gzip parts; `resolved[:1]` keeps only the
    first, so `provision_slice` extracts one `slice-0.fq` and never writes an
    unused `slice-1.fq` into the scratch directory.
    """
    resolved = gather_inputs(args.input)
    if not resolved:
        invalid(f"slice mode: no inputs resolved from {args.input!r}")
    slices = provision_slice(resolved[:1], args.slice_reads, scratch)
    return slices[0]


def prepare_run(args):
    """Provision, measure and assemble one validated-ready document."""
    out_path = Path(args.out)
    scratch = out_path.parent
    scratch.mkdir(parents=True, exist_ok=True)
    input_path = provision_one_slice(args, scratch)
    arms, schedule, sort_delta = measure_output_stage(args, input_path, scratch)
    return build_doc(args, input_path, arms, schedule, sort_delta)


def find_arm(doc, name):
    """The single arm named `name`, or None when missing/ambiguous."""
    matches = [a for a in doc.get("arms", [])
               if isinstance(a, dict) and a.get("name") == name]
    return matches[0] if len(matches) == 1 else None


def stage_verdict(baseline, post):
    """Compute the post-change gate verdict.

    Returns (exit_code, report_lines, verdict_block). verdict_block is None on
    every exit-2 path (no verdict may be printed or persisted then). The four
    conditions are checked independently; exit 0 only when ALL hold and the
    raw post delta is at most half the raw baseline delta (inclusive).
    """
    for label, doc in (("baseline", baseline), ("post", post)):
        try:
            validate_schema(doc)
            validate_provenance(doc)
        except ValueError as exc:
            return EXIT_INVALID, [f"{label} document invalid: {exc}"], None

    base_sorted = find_arm(baseline, SORTED_ARM)
    post_sorted = find_arm(post, SORTED_ARM)
    if base_sorted is None or post_sorted is None:
        return EXIT_INVALID, [
            f"missing or ambiguous sorted arm (baseline={base_sorted is not None}, "
            f"post={post_sorted is not None})"], None

    observations = {}
    for label, arm in (("baseline", base_sorted), ("post", post_sorted)):
        medians = arm.get("medians")
        if not isinstance(medians, dict):
            return EXIT_INVALID, [f"{label} sorted arm has no medians block"], None
        wall = medians.get("wall_s")
        rss = medians.get("peak_rss_bytes")
        for field, value in (("medians.wall_s", wall),
                             ("medians.peak_rss_bytes", rss)):
            if (not isinstance(value, (int, float)) or isinstance(value, bool)
                    or value <= 0):
                return EXIT_INVALID, [
                    f"{label} sorted arm {field} must be a positive number, "
                    f"got {value!r}"], None
        sha = arm.get("sorted_rkdb_sha256")
        if not isinstance(sha, str) or len(sha) != 64:
            return EXIT_INVALID, [
                f"{label} sorted arm sorted_rkdb_sha256 missing or malformed: "
                f"{sha!r}"], None
        observations[label] = {
            "wall_s": float(wall),
            "peak_rss_bytes": float(rss),
            "sha256": sha,
        }

    base_delta = baseline.get("sort_delta_s")
    post_delta = post.get("sort_delta_s")
    for label, value in (("baseline", base_delta), ("post", post_delta)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return EXIT_INVALID, [
                f"{label} sort_delta_s must be a number, got {value!r}"], None

    base = observations["baseline"]
    post_obs = observations["post"]
    checks = [
        ("sha256_mismatch", post_obs["sha256"] == base["sha256"]),
        ("wall_not_below_baseline", post_obs["wall_s"] < base["wall_s"]),
        ("sort_delta_not_halved", post_delta <= 0.5 * base_delta),
        ("rss_regressed", post_obs["peak_rss_bytes"] <= base["peak_rss_bytes"]),
    ]
    failed = [name for name, ok in checks if not ok]
    passed = not failed
    verdict = {
        "result": "GREEN" if passed else "RED",
        "sorted_wall_s": post_obs["wall_s"],
        "sort_delta_s": float(post_delta),
        "sha256_match": post_obs["sha256"] == base["sha256"],
        "score": "ok" if passed else ",".join(failed),
    }
    lines = [
        f"output-stage gate: baseline sorted {base['wall_s']:.3f}s "
        f"delta {base_delta!r}s; post sorted {post_obs['wall_s']:.3f}s "
        f"delta {post_delta!r}s",
        f"  sha256_match={verdict['sha256_match']} "
        f"(one .rkdb byte identity at slice scale)",
        f"  sorted wall strictly below baseline: "
        f"{post_obs['wall_s']:.3f}s < {base['wall_s']:.3f}s",
        f"  sort delta at most half baseline: {post_delta!r} <= "
        f"0.5 * {base_delta!r}",
        f"  peak RSS not regressed: {post_obs['peak_rss_bytes']:.0f} <= "
        f"{base['peak_rss_bytes']:.0f}",
    ]
    return (EXIT_GREEN if passed else EXIT_RED), lines, verdict


def verdict_line(verdict):
    """The one machine-greppable stdout line; repr() round-trips the floats."""
    return (f"OUTPUT STAGE VERDICT result={verdict['result']} "
            f"sorted_wall_s={verdict['sorted_wall_s']!r} "
            f"sort_delta_s={verdict['sort_delta_s']!r} "
            f"sha256_match={verdict['sha256_match']} "
            f"score={verdict['score']}")


def compare_identity_problem(baseline, params, input_fingerprint):
    """Return a reason string when this run is NOT the baseline measurement.

    `input_fingerprint` may be None for the pre-provisioning params-only
    check. Any returned reason is exit-2 material: comparing arms measured on
    different params or a different slice would make the verdict meaningless
    (the milestone's parity-before-timing guardrail).
    """
    base_params = baseline.get("params")
    if not isinstance(base_params, dict):
        return "baseline carries no params block"
    for key in ("threads", "k", "slice_reads", "canonical"):
        if base_params.get(key) != params.get(key):
            return (f"baseline {key}={base_params.get(key)!r} != post "
                    f"{params.get(key)!r} — only the same measurement may be "
                    f"compared")
    if input_fingerprint is None:
        return None
    base_fp = baseline.get("input_fingerprint")
    if (not isinstance(base_fp, list) or not base_fp
            or not isinstance(base_fp[0], dict)):
        return "baseline carries no input fingerprint"
    base_sha = base_fp[0].get("sha256")
    post_sha = None
    if isinstance(input_fingerprint, list) and input_fingerprint:
        if isinstance(input_fingerprint[0], dict):
            post_sha = input_fingerprint[0].get("sha256")
    if not isinstance(base_sha, str) or base_sha != post_sha:
        return (f"input fingerprint mismatch: baseline {base_sha!r} != post "
                f"{post_sha!r} — the slice is not the baseline's slice")
    return None


def identity_verdict(baseline, params, input_fingerprint):
    """(exit_code, reason): 0 when identical, 2 when not the same measurement."""
    problem = compare_identity_problem(baseline, params, input_fingerprint)
    if problem is not None:
        return EXIT_INVALID, problem
    return EXIT_GREEN, ""


def load_baseline(path):
    """Load and validate a pre-change baseline; exit 2 on any defect."""
    try:
        with open(path, encoding="utf-8") as fh:
            baseline = json.load(fh)
    except FileNotFoundError:
        invalid(f"baseline not found: {path}")
    except OSError as exc:
        invalid(f"baseline unreadable: {path} ({exc})")
    except json.JSONDecodeError as exc:
        invalid(f"baseline is not parseable JSON: {path} ({exc})")
    try:
        validate_schema(baseline)
        validate_provenance(baseline)
    except ValueError as exc:
        invalid(f"baseline failed validation: {exc}")
    if baseline.get("mode") != "output_stage":
        invalid(f"baseline mode {baseline.get('mode')!r} != 'output_stage'")
    return baseline


def check_environment(args):
    """Platform + binary preconditions shared by capture and compare."""
    if platform.system() not in SUPPORTED_SYSTEMS:
        invalid(f"unsupported platform {platform.system()!r} (expected one "
                f"of {SUPPORTED_SYSTEMS})")
    if not Path(args.rustkmer).is_file():
        invalid(f"rustkmer binary not found: {args.rustkmer} — build it "
                f"first (cargo build --release --locked)")


def run_capture(args):
    """Record the immutable pre-change baseline (never a verdict)."""
    check_environment(args)
    doc = prepare_run(args)
    if doc["sort_delta_s"] <= MIN_PRE_SORT_DELTA_S:
        invalid(f"sort_delta_s={doc['sort_delta_s']!r} is not > "
                f"{MIN_PRE_SORT_DELTA_S}: the instrument is not attributing "
                f"the stable sort — investigate provisioning/binary before "
                f"recording a baseline")
    write_doc(doc, args.out)
    arms = {arm["name"]: arm for arm in doc["arms"]}
    print(f"output-stage baseline written to {args.out}")
    print(f"  sorted   median wall {arms['sorted']['medians']['wall_s']:.3f}s "
          f"RSS {arms['sorted']['medians']['peak_rss_bytes']:.0f} B")
    print(f"  unsorted median wall "
          f"{arms['unsorted']['medians']['wall_s']:.3f}s")
    print(f"  sort_delta_s {doc['sort_delta_s']!r} "
          f"(raw sorted - unsorted)")
    print(f"  sorted_rkdb_sha256 "
          f"{arms['sorted']['sorted_rkdb_sha256']}")
    sys.exit(EXIT_GREEN)


def run_compare(args):
    """Re-measure post-change arms and issue the GREEN/RED verdict."""
    check_environment(args)
    baseline = load_baseline(args.baseline)

    # Cheap params-only identity check BEFORE the expensive provisioning.
    post_params = run_params(args)
    code, reason = identity_verdict(baseline, post_params, None)
    if code != EXIT_GREEN:
        invalid(reason)

    doc = prepare_run(args)
    code, reason = identity_verdict(
        baseline, doc["params"], doc["input_fingerprint"])
    if code != EXIT_GREEN:
        invalid(reason)

    code, lines, verdict = stage_verdict(baseline, doc)
    if code == EXIT_INVALID:
        for line in lines:
            print(f"output_stage.py: {line}", file=sys.stderr)
        sys.exit(code)
    doc["verdict"] = verdict
    write_doc(doc, args.out)
    for line in lines:
        print(line)
    print(f"results written to {args.out}")
    # The verdict line is printed only AFTER the validated doc is on disk.
    print(verdict_line(verdict))
    sys.exit(code)


def build_parser():
    """CLI: `capture --out DOC` and `compare --baseline DOC --out DOC`."""
    parser = argparse.ArgumentParser(
        description="OUT-01 output-stage gate: sorted vs --no-sort counting "
                    "output on one provisioned slice. capture records the "
                    "pre-change baseline; compare issues the post-change "
                    "GREEN/RED verdict (exit 0/1/2).")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p):
        p.add_argument("--threads", type=int, default=4,
                       help="count threads for both arms (default 4)")
        p.add_argument("--reps", type=int, default=3,
                       help="measured counterbalanced rounds (default 3)")
        p.add_argument("--k", type=int, default=21, help="k-mer size")
        p.add_argument("--slice-reads", type=int, default=DEFAULT_SLICE_READS,
                       help="reads in the ONE provisioned slice "
                            f"(default {DEFAULT_SLICE_READS})")
        p.add_argument("--input", default=DEFAULT_INPUT,
                       help="gz input file, glob, or directory (the first "
                            "resolved source is sliced; default the Phase 7 "
                            "CRR1936095 part_001 gz)")
        p.add_argument("--rustkmer", default=DEFAULT_RUSTKMER,
                       help="path to the rustkmer RELEASE binary")
        p.add_argument("--cooldown-s", type=int, default=DEFAULT_COOLDOWN_S,
                       help="cooldown seconds between runs (thermal/order "
                            "bias defense)")
        p.add_argument("--out", required=True,
                       help="results doc output path (scratch directory is "
                            "its parent)")

    capture = sub.add_parser(
        "capture", help="record the immutable pre-change baseline")
    add_common(capture)
    compare = sub.add_parser(
        "compare", help="re-measure and issue the post-change verdict")
    add_common(compare)
    compare.add_argument("--baseline", required=True,
                         help="validated capture-mode baseline document")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.k < 1 or args.k > 64:
        parser.error("--k must be in 1..64")
    if args.reps < 1:
        parser.error("--reps must be >= 1")
    if args.slice_reads < 1:
        parser.error("--slice-reads must be >= 1")
    if args.threads < 1:
        parser.error("--threads must be >= 1")
    if args.cooldown_s < 0:
        parser.error("--cooldown-s must be >= 0")
    if args.command == "capture":
        run_capture(args)
    else:
        run_compare(args)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — fail loudly, no traceback noise
        # Infrastructure failures are INVALID (exit 2), never exit 1: the
        # RED exit code is reserved for the measured verdict, so an uncaught
        # exception can never masquerade as a measured RED observation.
        print(f"output_stage.py: {exc}", file=sys.stderr)
        sys.exit(EXIT_INVALID)
