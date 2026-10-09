"""Unit tests for the 04-03 gate comparator compare.py (BENCH-01).

The comparator's exit codes are the CI gate contract, so every test drives
compare.main() the way the workflow does and asserts the exit code:

  0 — every shared arm within BOTH thresholds on both axes (boundary probes:
      a delta exactly equal to a threshold passes; only strictly-greater
      deltas breach; one-ulp-above breaches),
  1 — any breach, with the wall and RSS axes checked INDEPENDENTLY,
  2 — invalid input: missing file, unparseable JSON, schema violation,
      platform mismatch, one-sided arm.

Also probed: the same-file self-comparison (every delta exactly 0), the
single-rep median fallback (reps=1 CI results carry no arm-level median
fields), and that a fallback median is a MEDIAN, not a mean. Stdlib
unittest only — no pytest, no conftest.
"""

import contextlib
import io
import json
import math
import os
import statistics
import tempfile
import unittest

from scripts.bench import compare


def make_arm(name="count-A", tool="rustkmer", walls=(10.0,),
             rss=(100_000_000,), with_medians=True):
    """One schema-valid arm; with_medians=False mimics the reps=1 CI path
    (bench.py emits arm-level median fields only for multi-rep runs)."""
    arm = {
        "name": name,
        "tool": tool,
        "reps": [{"wall_s": w, "peak_rss_bytes": r}
                 for w, r in zip(walls, rss)],
        "distinct_kmers": 2400,
        "total_kmers": 2400,
    }
    if with_medians:
        arm["median_wall_s"] = statistics.median(walls)
        arm["median_peak_rss_bytes"] = statistics.median(rss)
    return arm


def make_doc(platform="darwin", arms=None):
    """A schema-valid results/baseline document. platform is the flavor
    string a committed baseline carries; live results instead carry the
    bench.py platform report dict — tests exercise both shapes."""
    return {
        "schema_version": 1,
        "mode": "synthetic",
        "platform": platform,
        "created": "2026-10-09T00:00:00+00:00",
        "input_fingerprint": [],
        "params": {"k": 31, "canonical": True, "threads": 4},
        "arms": arms if arms is not None else [make_arm()],
    }


class CompareHarness(unittest.TestCase):
    """Shared driver: write docs to a tempdir, run compare.main, capture."""

    def run_compare_docs(self, baseline_doc, current_doc, extra=()):
        with tempfile.TemporaryDirectory() as tmp:
            base_path = os.path.join(tmp, "baseline.json")
            cur_path = os.path.join(tmp, "current.json")
            for path, doc in ((base_path, baseline_doc),
                              (cur_path, current_doc)):
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(doc, fh)
            return self.run_compare_paths(base_path, cur_path, extra)

    def run_compare_paths(self, base_path, cur_path, extra=()):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as ctx:
                compare.main(["--baseline", str(base_path),
                              "--current", str(cur_path), *extra])
        return ctx.exception.code, out.getvalue(), err.getvalue()


class TestBoundaryBehavior(CompareHarness):
    """Delta exactly equal to a threshold passes; strictly greater breaches."""

    def test_wall_delta_exactly_at_threshold_passes(self):
        """(125-100)/100 == 0.25 exactly -> exit 0 (boundary is green)."""
        base = make_doc(arms=[make_arm(walls=(100.0,))])
        cur = make_doc(arms=[make_arm(walls=(125.0,))])
        code, out, _ = self.run_compare_docs(
            base, cur, ["--wall-threshold", "0.25"])
        self.assertEqual(code, 0)
        self.assertIn("GATE: PASS", out)

    def test_wall_delta_strictly_above_threshold_breaches(self):
        """(126-100)/100 == 0.26 > 0.25 -> exit 1."""
        base = make_doc(arms=[make_arm(walls=(100.0,))])
        cur = make_doc(arms=[make_arm(walls=(126.0,))])
        code, out, _ = self.run_compare_docs(
            base, cur, ["--wall-threshold", "0.25"])
        self.assertEqual(code, 1)
        self.assertIn("GATE: FAIL", out)

    def test_wall_one_ulp_above_threshold_breaches(self):
        """One float ulp above the boundary value still breaches — the
        comparison is strictly-greater, not approximately-equal."""
        base = make_doc(arms=[make_arm(walls=(100.0,))])
        cur = make_doc(arms=[make_arm(
            walls=(math.nextafter(125.0, math.inf),))])
        code, _, _ = self.run_compare_docs(
            base, cur, ["--wall-threshold", "0.25"])
        self.assertEqual(code, 1)

    def test_rss_delta_exactly_at_threshold_passes(self):
        """(1_150_000-1_000_000)/1_000_000 == 0.15 exactly -> exit 0."""
        base = make_doc(arms=[make_arm(rss=(1_000_000,))])
        cur = make_doc(arms=[make_arm(rss=(1_150_000,))])
        code, out, _ = self.run_compare_docs(
            base, cur, ["--rss-threshold", "0.15"])
        self.assertEqual(code, 0)
        self.assertIn("GATE: PASS", out)

    def test_rss_delta_strictly_above_threshold_breaches(self):
        """(1_160_000-1_000_000)/1_000_000 == 0.16 > 0.15 -> exit 1."""
        base = make_doc(arms=[make_arm(rss=(1_000_000,))])
        cur = make_doc(arms=[make_arm(rss=(1_160_000,))])
        code, _, _ = self.run_compare_docs(
            base, cur, ["--rss-threshold", "0.15"])
        self.assertEqual(code, 1)

    def test_rss_one_ulp_above_threshold_breaches(self):
        """One float ulp above the RSS boundary value breaches."""
        base = make_doc(arms=[make_arm(rss=(1_000_000,))])
        cur = make_doc(arms=[make_arm(
            rss=(math.nextafter(1_150_000.0, math.inf),))])
        code, _, _ = self.run_compare_docs(
            base, cur, ["--rss-threshold", "0.15"])
        self.assertEqual(code, 1)

    def test_improvements_pass_on_both_axes(self):
        """Negative deltas (current faster AND leaner) are passes, not 0."""
        base = make_doc(arms=[make_arm(walls=(100.0,), rss=(1_000_000,))])
        cur = make_doc(arms=[make_arm(walls=(50.0,), rss=(500_000,))])
        code, out, _ = self.run_compare_docs(base, cur)
        self.assertEqual(code, 0)
        self.assertIn("GATE: PASS", out)

    def test_default_thresholds_are_25_wall_15_rss(self):
        """No flags: 24% wall / 14% rss pass; 26% wall would not (covered
        above with an explicit flag — this pins the DEFAULTS)."""
        base = make_doc(arms=[make_arm(walls=(100.0,), rss=(1_000_000,))])
        cur = make_doc(arms=[make_arm(walls=(124.0,), rss=(1_140_000,))])
        code, out, _ = self.run_compare_docs(base, cur)
        self.assertEqual(code, 0)
        self.assertIn("threshold 25.00%", out)
        self.assertIn("threshold 15.00%", out)


class TestIndependentAxes(CompareHarness):
    """Wall and RSS are gated independently — either axis alone fails."""

    def test_rss_breach_with_wall_within_exits_1(self):
        base = make_doc(arms=[make_arm(walls=(10.0,), rss=(1_000_000,))])
        cur = make_doc(arms=[make_arm(walls=(10.0,), rss=(1_160_000,))])
        code, out, _ = self.run_compare_docs(base, cur)
        self.assertEqual(code, 1)
        self.assertIn("metric=median_peak_rss_bytes", out)
        # The wall axis is still reported, and as ok — the axes are judged
        # independently, so a wall table line must exist and stay green.
        self.assertIn("median_wall_s: baseline 10 -> current 10", out)

    def test_wall_breach_with_rss_within_exits_1(self):
        base = make_doc(arms=[make_arm(walls=(10.0,), rss=(1_000_000,))])
        cur = make_doc(arms=[make_arm(walls=(13.0,), rss=(1_000_000,))])
        code, out, _ = self.run_compare_docs(base, cur)
        self.assertEqual(code, 1)
        self.assertIn("metric=median_wall_s", out)


class TestExitTwoInputs(CompareHarness):
    """Every invalid-input class exits 2 — never a traceback, never a 0/1."""

    def test_missing_baseline_file_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            cur_path = os.path.join(tmp, "current.json")
            with open(cur_path, "w", encoding="utf-8") as fh:
                json.dump(make_doc(), fh)
            code, _, err = self.run_compare_paths(
                os.path.join(tmp, "absent.json"), cur_path)
        self.assertEqual(code, 2)
        self.assertIn("not found", err)

    def test_missing_current_file_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_path = os.path.join(tmp, "baseline.json")
            with open(base_path, "w", encoding="utf-8") as fh:
                json.dump(make_doc(), fh)
            code, _, err = self.run_compare_paths(
                base_path, os.path.join(tmp, "absent.json"))
        self.assertEqual(code, 2)
        self.assertIn("not found", err)

    def test_unparseable_baseline_json_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_path = os.path.join(tmp, "baseline.json")
            cur_path = os.path.join(tmp, "current.json")
            with open(base_path, "w", encoding="utf-8") as fh:
                fh.write("not json {")
            with open(cur_path, "w", encoding="utf-8") as fh:
                json.dump(make_doc(), fh)
            code, _, err = self.run_compare_paths(base_path, cur_path)
        self.assertEqual(code, 2)
        self.assertIn("not parseable JSON", err)

    def test_schema_violation_missing_schema_version_exits_2(self):
        doc = make_doc()
        del doc["schema_version"]
        code, _, err = self.run_compare_docs(doc, make_doc())
        self.assertEqual(code, 2)
        self.assertIn("schema validation", err)

    def test_schema_violation_rep_missing_rss_exits_2(self):
        """A rep without peak_rss_bytes is caught by the SHARED validator —
        compare.py must not have a second, driftier one."""
        bad = make_doc(arms=[make_arm()])
        del bad["arms"][0]["reps"][0]["peak_rss_bytes"]
        code, _, err = self.run_compare_docs(bad, make_doc())
        self.assertEqual(code, 2)
        self.assertIn("peak_rss_bytes", err)

    def test_platform_mismatch_string_vs_string_exits_2(self):
        """darwin baseline vs linux current — never silently compared."""
        code, _, err = self.run_compare_docs(
            make_doc(platform="darwin"), make_doc(platform="linux"))
        self.assertEqual(code, 2)
        self.assertIn("platform mismatch", err)
        self.assertIn("darwin", err)
        self.assertIn("linux", err)

    def test_platform_mismatch_string_vs_results_dict_exits_2(self):
        """Baseline flavor string vs a live results platform report dict."""
        cur = make_doc(platform={"system": "Linux", "release": "6.8",
                                 "machine": "x86_64", "python": "3.11"})
        code, _, err = self.run_compare_docs(make_doc(platform="darwin"), cur)
        self.assertEqual(code, 2)
        self.assertIn("platform mismatch", err)

    def test_missing_platform_field_on_baseline_exits_2(self):
        doc = make_doc()
        del doc["platform"]
        code, _, err = self.run_compare_docs(doc, make_doc())
        self.assertEqual(code, 2)
        self.assertIn("platform", err)

    def test_arm_in_baseline_only_exits_2(self):
        base = make_doc(arms=[make_arm("count-A"),
                              make_arm("count-B"),
                              make_arm("jellyfish-count-A", tool="jellyfish")])
        cur = make_doc(arms=[make_arm("count-A"), make_arm("count-B")])
        code, _, err = self.run_compare_docs(base, cur)
        self.assertEqual(code, 2)
        self.assertIn("in baseline only", err)
        self.assertIn("jellyfish-count-A", err)

    def test_arm_in_current_only_exits_2(self):
        base = make_doc(arms=[make_arm("count-A")])
        cur = make_doc(arms=[make_arm("count-A"), make_arm("merge")])
        code, _, err = self.run_compare_docs(base, cur)
        self.assertEqual(code, 2)
        self.assertIn("in current only", err)
        self.assertIn("merge", err)

    def test_same_name_different_tool_is_one_sided(self):
        """Arms match by name AND tool: count-A/rustkmer vs count-A/jellyfish
        is a mismatch, not a match."""
        base = make_doc(arms=[make_arm("count-A", tool="rustkmer")])
        cur = make_doc(arms=[make_arm("count-A", tool="jellyfish")])
        code, _, err = self.run_compare_docs(base, cur)
        self.assertEqual(code, 2)
        self.assertIn("arm sets differ", err)


class TestPlatformFlavors(CompareHarness):
    """Baseline flavor string matches the live results platform dict."""

    def test_darwin_string_matches_darwin_system_dict(self):
        """"darwin" baseline vs {"system": "Darwin"} current -> exit 0."""
        cur = make_doc(platform={"system": "Darwin", "release": "24.0",
                                 "machine": "arm64", "python": "3.12"})
        code, out, _ = self.run_compare_docs(make_doc(platform="darwin"), cur)
        self.assertEqual(code, 0)
        self.assertIn("(darwin)", out)


class TestSelfComparison(CompareHarness):
    """A file compared against itself is the delta-0 sanity anchor."""

    def test_same_file_self_comparison_exits_0(self):
        """All deltas exactly 0 across three arms -> exit 0."""
        doc = make_doc(arms=[make_arm("count-A", walls=(10.0, 10.5, 9.8),
                                       rss=(100, 102, 99)),
                             make_arm("count-B", walls=(11.0,),
                                      rss=(101_000_000,)),
                             make_arm("merge", walls=(2.0,),
                                      rss=(200_000_000,))])
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "results.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(doc, fh)
            code, out, _ = self.run_compare_paths(path, path)
        self.assertEqual(code, 0)
        self.assertEqual(out.count("delta +0.00%"), 6)  # 3 arms x 2 axes
        self.assertIn("GATE: PASS", out)


class TestMedianFallback(CompareHarness):
    """reps=1 CI results carry no arm-level median fields — the comparator
    derives the median from the reps, exactly as bench.reduce_arm would."""

    def test_single_rep_without_median_fields_gates_on_rep_values(self):
        """26% wall regression visible through the fallback path -> exit 1."""
        base = make_doc(arms=[make_arm(walls=(100.0,), with_medians=True)])
        cur = make_doc(arms=[make_arm(walls=(126.0,), with_medians=False)])
        code, out, _ = self.run_compare_docs(base, cur)
        self.assertEqual(code, 1)
        self.assertIn("delta=+26.00%", out)

    def test_fallback_derives_median_not_mean(self):
        """reps (10, 10, 25): median 10 (+0%, PASS) — mean 15 would breach."""
        base = make_doc(arms=[make_arm(walls=(10.0,), with_medians=True)])
        cur = make_doc(arms=[make_arm(walls=(10.0, 10.0, 25.0),
                                      with_medians=False)])
        code, out, _ = self.run_compare_docs(base, cur)
        self.assertEqual(code, 0)
        self.assertIn("delta +0.00%", out)


class TestBreachMessage(CompareHarness):
    """A breach line names everything a human needs to act on."""

    def test_breach_message_names_all_seven_fields(self):
        base = make_doc(arms=[make_arm(walls=(100.0,), rss=(1_000_000,))])
        cur = make_doc(arms=[make_arm(walls=(126.0,), rss=(1_000_000,))])
        code, out, _ = self.run_compare_docs(base, cur)
        self.assertEqual(code, 1)
        self.assertIn("arm=count-A", out)
        self.assertIn("tool=rustkmer", out)
        self.assertIn("metric=median_wall_s", out)
        self.assertIn("baseline=100", out)
        self.assertIn("current=126", out)
        self.assertIn("delta=+26.00%", out)
        self.assertIn("threshold=25.00%", out)

    def test_multiple_breaches_all_named(self):
        """Two arms breaching -> both named, count reported as 4 regressions
        when both axes breach on both arms."""
        base = make_doc(arms=[
            make_arm("count-A", walls=(100.0,), rss=(1_000_000,)),
            make_arm("count-B", walls=(100.0,), rss=(1_000_000,))])
        cur = make_doc(arms=[
            make_arm("count-A", walls=(200.0,), rss=(2_000_000,)),
            make_arm("count-B", walls=(200.0,), rss=(2_000_000,))])
        code, out, _ = self.run_compare_docs(base, cur)
        self.assertEqual(code, 1)
        self.assertIn("arm=count-A", out)
        self.assertIn("arm=count-B", out)
        self.assertIn("4 regression(s)", out)


if __name__ == "__main__":
    unittest.main()
