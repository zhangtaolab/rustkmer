#!/usr/bin/env python3
"""Threshold comparator for the rustkmer benchmark regression gate (BENCH-01).

Turns two schema-valid results JSONs — a committed per-platform baseline and
a fresh run — into a gate verdict. Gate semantics live HERE and only here:
the CI workflow invokes this script and trusts its exit code; no workflow
step is allowed to soften, skip, or re-derive the decision.

Exit codes are a contract (documented for CI and the tests alike):
  0 — within: every shared arm's current medians sit within BOTH thresholds
      on BOTH axes (a delta exactly equal to a threshold passes; only a
      strictly greater delta breaches; negative deltas are improvements).
  1 — regression: at least one arm breached a threshold. Every breach line
      names arm, tool, metric, baseline median, current median, delta
      percent, and threshold.
  2 — invalid input: missing file, unparseable JSON, schema violation,
      platform mismatch, or an arm present on only one side. A gate with
      broken inputs is not a gate — it fails loudly, never best-effort.

Both files are validated through validate_schema imported from
scripts.bench.bench — the single source of truth for the results contract
(shared with the harness self-check and the 04-04 report; three validators
would drift). The baseline adds one field on top of the results schema: a
platform flavor string ("darwin"/"linux"); a live results.json instead
carries the platform report dict, whose 'system' value normalizes to the
same vocabulary. Absolute numbers are never comparable across platforms,
which is exactly why baselines are per-platform files: any mismatch exits 2.

Medians come from the arm-level fields (median_wall_s /
median_peak_rss_bytes, emitted by the 04-02 multi-rep protocol) or, when a
file carries none (the single-rep CI path), from the median of its reps —
the same reduction bench.reduce_arm performs. Python 3.10+ stdlib only.
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

if __package__ in (None, ""):
    # Executed as a script (python3 scripts/bench/compare.py): the repo root
    # is not on sys.path yet. Insert it BEFORE importing so the harness
    # package resolves to this checkout in one shot — some environments
    # carry an unrelated `scripts` namespace package in site-packages that
    # would otherwise win the first import and poison sys.modules against
    # any retry. Package mode (python3 -m, unittest) needs no fixup.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.bench.bench import validate_schema

EXIT_WITHIN = 0
EXIT_REGRESSION = 1
EXIT_INVALID = 2

# Each gate axis: (arm-level median field, rep-level field). Wall and RSS are
# checked INDEPENDENTLY — an RSS breach fails the gate even when wall is
# comfortably within, and vice versa (BENCH-03: memory regressions surface on
# their own, not hidden behind a passing speed axis).
AXES = (
    ("median_wall_s", "wall_s"),
    ("median_peak_rss_bytes", "peak_rss_bytes"),
)

DEFAULT_WALL_THRESHOLD = 0.25  # shared-runner wall variance is 2-3x (Pitfall 6)
DEFAULT_RSS_THRESHOLD = 0.15   # RSS is far more stable -> tighter leash


def invalid(message):
    """Print an input problem and exit 2 — the comparator never best-effort
    parses its inputs (a verdict on malformed data would be a fabricated
    verdict)."""
    print(f"compare.py: {message}", file=sys.stderr)
    sys.exit(EXIT_INVALID)


def load_results(path, source):
    """Load and schema-validate one results/baseline JSON file.

    Missing file, unreadable file, unparseable JSON, and schema violations
    each exit 2 with a message naming the file and the problem.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except FileNotFoundError:
        invalid(f"{source} file not found: {path}")
    except OSError as exc:
        invalid(f"{source} file unreadable: {path} ({exc})")
    except json.JSONDecodeError as exc:
        invalid(f"{source} file is not parseable JSON: {path} ({exc})")
    try:
        validate_schema(doc)
    except ValueError as exc:
        invalid(f"{source} file fails schema validation: {path} ({exc})")
    return doc


def platform_flavor(doc, source):
    """Normalize a document's platform field to a comparable flavor string.

    Committed baselines carry the flavor string itself ("darwin"/"linux");
    a live results.json from bench.py carries the platform report dict whose
    'system' value ("Darwin"/"Linux") lowercases into the same vocabulary.
    A missing or unusable platform field exits 2 — an unattributable file
    must never reach the comparison.
    """
    value = doc.get("platform")
    if isinstance(value, dict):
        value = value.get("system")
    if not isinstance(value, str) or not value.strip():
        invalid(f"{source} file has no usable platform field (expected the "
                f"baseline flavor string, e.g. \"darwin\", or a results "
                f"platform report dict with a 'system' key)")
    return value.strip().lower()


def arm_key(arm):
    """Arms match across the two files by name AND tool."""
    return (str(arm.get("name", "")), str(arm.get("tool", "")))


def arm_median(arm, arm_field, rep_field):
    """One arm's median for an axis: the arm-level field when present, else
    the median of the reps (single-rep CI runs carry no precomputed medians;
    median-of-one is that rep). Any gap exits 2."""
    value = arm.get(arm_field)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    reps = arm.get("reps") or []
    try:
        return float(statistics.median(rep[rep_field] for rep in reps))
    except (KeyError, TypeError, ValueError, statistics.StatisticsError):
        invalid(f"arm {arm.get('name')!r}: no {arm_field} field and no "
                f"parsable reps.{rep_field} values to derive the median from")


def compare_results(baseline, current, wall_threshold, rss_threshold):
    """Compare every shared arm on both axes; return (breaches, table_lines).

    Relative delta = (current - baseline) / baseline per axis. A breach is
    STRICTLY delta > threshold: equality passes (the boundary belongs to
    green), and negative deltas (improvements) always pass.
    """
    thresholds = {"median_wall_s": wall_threshold,
                  "median_peak_rss_bytes": rss_threshold}
    base_arms = {arm_key(a): a for a in baseline["arms"]}
    cur_arms = {arm_key(a): a for a in current["arms"]}
    only_baseline = sorted(set(base_arms) - set(cur_arms))
    only_current = sorted(set(cur_arms) - set(base_arms))
    if only_baseline or only_current:
        parts = []
        if only_baseline:
            parts.append("in baseline only: " + ", ".join(
                f"{name}/{tool}" for name, tool in only_baseline))
        if only_current:
            parts.append("in current only: " + ", ".join(
                f"{name}/{tool}" for name, tool in only_current))
        invalid("arm sets differ across the files — " + "; ".join(parts)
                + " (arms match by name AND tool; a gate over different "
                "measurement sets is invalid input, not a verdict)")

    breaches = []
    lines = []
    for key in sorted(base_arms):
        name, tool = key
        for arm_field, rep_field in AXES:
            base_v = arm_median(base_arms[key], arm_field, rep_field)
            cur_v = arm_median(cur_arms[key], arm_field, rep_field)
            if base_v <= 0:
                invalid(f"arm {name!r}: baseline {arm_field} is {base_v} — "
                        f"relative delta is undefined against a non-positive "
                        f"baseline")
            delta = (cur_v - base_v) / base_v
            threshold = thresholds[arm_field]
            breached = delta > threshold
            lines.append(
                f"  {name} [{tool}] {arm_field}: baseline {base_v:.6g} -> "
                f"current {cur_v:.6g}  delta {delta * 100:+.2f}%  threshold "
                f"{threshold * 100:.2f}%  {'BREACH' if breached else 'ok'}")
            if breached:
                breaches.append(
                    f"REGRESSION arm={name} tool={tool} metric={arm_field} "
                    f"baseline={base_v:.6g} current={cur_v:.6g} "
                    f"delta={delta * 100:+.2f}% "
                    f"threshold={threshold * 100:.2f}%")
    return breaches, lines


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Compare benchmark results against a committed baseline "
                    "and emit a gate verdict (exit 0 within, 1 regression, "
                    "2 invalid input).")
    parser.add_argument("--baseline", required=True,
                        help="committed per-platform baseline JSON "
                             "(results schema + platform flavor string)")
    parser.add_argument("--current", required=True,
                        help="fresh results.json from bench.py")
    parser.add_argument("--wall-threshold", type=float,
                        default=DEFAULT_WALL_THRESHOLD,
                        help="relative wall-clock breach threshold "
                             "(default 0.25 — shared-runner variance)")
    parser.add_argument("--rss-threshold", type=float,
                        default=DEFAULT_RSS_THRESHOLD,
                        help="relative peak-RSS breach threshold "
                             "(default 0.15 — RSS is stable; memory "
                             "regressions surface earlier)")
    args = parser.parse_args(argv)
    if args.wall_threshold < 0 or args.rss_threshold < 0:
        parser.error("thresholds must be >= 0")

    baseline = load_results(args.baseline, "baseline")
    current = load_results(args.current, "current")

    base_flavor = platform_flavor(baseline, "baseline")
    cur_flavor = platform_flavor(current, "current")
    if base_flavor != cur_flavor:
        invalid(f"platform mismatch: baseline is {base_flavor!r} but current "
                f"results are {cur_flavor!r} — absolute wall/RSS numbers are "
                f"not comparable across platforms; use this platform's "
                f"baseline file bench_baseline.{cur_flavor}.json")

    breaches, lines = compare_results(baseline, current,
                                      args.wall_threshold,
                                      args.rss_threshold)
    print(f"benchmark gate: baseline {args.baseline} ({base_flavor}) vs "
          f"current {args.current} ({cur_flavor})")
    for line in lines:
        print(line)
    if breaches:
        for breach in breaches:
            print(breach)
        print(f"GATE: FAIL — {len(breaches)} regression(s) beyond thresholds "
              f"(wall {args.wall_threshold * 100:g}%, "
              f"rss {args.rss_threshold * 100:g}%)")
        sys.exit(EXIT_REGRESSION)
    print("GATE: PASS — every arm within thresholds on both axes")
    sys.exit(EXIT_WITHIN)


if __name__ == "__main__":
    main()
