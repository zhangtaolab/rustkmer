"""Unit tests for --render-report (04-04 Task 3, threat T-04-07).

The renderer's contract is that the report is a pure function of the
committed results JSONs: no measurement literals, no clock. These tests pin
the three observable consequences — byte-identical re-render, sensitivity
to JSON edits (a hand-edited number cannot hide), and verdict/cold-cache/
provenance statements computed mechanically from the recorded data.
Stdlib unittest only, in-memory fixtures written to temp files.
"""

import json
import statistics
import tempfile
import unittest
from pathlib import Path

from scripts.bench.bench import (
    _delta_pct,
    render_report,
)


def build_arm(name, tool, walls, rss, cache="unavailable",
              distinct=1000, total=2000, cv_warning=False):
    reps = [{"wall_s": w, "peak_rss_bytes": r, "cache_state": cache,
             "round": i, "arm_order": i}
            for i, (w, r) in enumerate(zip(walls, rss))]
    return {"name": name, "tool": tool, "reps": reps,
            "distinct_kmers": distinct, "total_kmers": total,
            "median_wall_s": statistics.median(walls),
            "median_peak_rss_bytes": statistics.median(rss),
            "cv_wall_pct": 1.0, "cv_warning": cv_warning}


def build_results(mode="full", k=31, arms=None, fingerprints=None):
    if fingerprints is None:
        fingerprints = [{"path": "input.fq.gz", "size_bytes": 12345,
                         "sha256": "ab" * 32}]
    return {
        "schema_version": 1,
        "mode": mode,
        "resolved_inputs": ["input.fq.gz"],
        "input_fingerprint": fingerprints,
        "platform": {"system": "Darwin", "release": "25.6.0",
                     "machine": "arm64", "python": "3.12.8"},
        "created": "2026-10-10T16:36:28Z",
        "params": {"k": k, "canonical": True, "threads": 16,
                   "rustkmer": "target/release/rustkmer",
                   "hash_size": "10G", "decompressor": "gzcat", "reps": 3,
                   "cooldown_s": 5,
                   "round_schedule": {"0": ["rustkmer", "jellyfish"],
                                      "1": ["jellyfish", "rustkmer"],
                                      "2": ["rustkmer", "jellyfish"]}},
        "arms": arms if arms is not None else [],
    }


def typical_full_results(k=31):
    """A full-mode comparison shape: two rustkmer count arms + jellyfish."""
    return build_results(mode="full", k=k, arms=[
        build_arm("count-A", "rustkmer", (494.19, 494.18, 499.98),
                  (11 * (1 << 30), 10 * (1 << 30), 12 * (1 << 30))),
        build_arm("count-B", "rustkmer", (485.89, 492.59, 485.89),
                  (11 * (1 << 30),) * 3),
        build_arm("jellyfish-count-A", "jellyfish", (843.02, 657.82, 875.18),
                  (80 * (1 << 30),) * 3),
    ])


class RenderFixtureBase(unittest.TestCase):
    """Shared plumbing: write results dicts to temp JSON files, render."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write_results(self, results, name="results.json"):
        path = self.root / name
        path.write_text(json.dumps(results, indent=2), newline="\n")
        return path

    def render(self, paths, name="report.md"):
        out = self.root / name
        render_report([str(p) for p in paths], out)
        return out.read_text()


class TestDeterminism(RenderFixtureBase):
    """T-04-07: same JSONs in, byte-identical file out — twice."""

    def test_re_render_is_byte_identical(self):
        """Two renders of the same JSONs produce identical bytes."""
        full = self.write_results(typical_full_results(), "full.json")
        first = self.render([full], "a.md")
        second = self.render([full], "b.md")
        self.assertEqual(first, second)

    def test_editing_a_json_number_changes_the_report(self):
        """Cherry-pick visibility: a changed median MUST surface in the text."""
        results = typical_full_results()
        path = self.write_results(results, "full.json")
        before = self.render([path], "a.md")
        results["arms"][0]["median_wall_s"] = 400.0
        path2 = self.write_results(results, "full2.json")
        after = self.render([path2], "b.md")
        self.assertNotEqual(before, after)
        self.assertIn("400.00", after)
        self.assertNotIn("400.00", before)


class TestVerdicts(RenderFixtureBase):
    """The matches-or-beats verdict is computed from recorded medians."""

    def test_faster_rustkmer_arms_yield_yes(self):
        report = self.render([self.write_results(typical_full_results())])
        self.assertIn("counting speed — **YES**", report)

    def test_equal_medians_match(self):
        """'Matches or beats': equality is a match, not a loss."""
        results = build_results(arms=[
            build_arm("count-A", "rustkmer", (100.0, 100.0, 100.0),
                      (10 * (1 << 30),) * 3),
            build_arm("jellyfish-count-A", "jellyfish", (100.0, 100.0, 100.0),
                      (10 * (1 << 30),) * 3),
        ])
        report = self.render([self.write_results(results)])
        self.assertIn("counting speed — **YES**", report)

    def test_any_slower_rustkmer_arm_yields_no(self):
        """Conservative rule: one slower rustkmer arm fails the whole table."""
        results = build_results(arms=[
            build_arm("count-A", "rustkmer", (100.0, 100.0, 100.0),
                      (10 * (1 << 30),) * 3),
            build_arm("count-B", "rustkmer", (200.0, 200.0, 200.0),
                      (10 * (1 << 30),) * 3),
            build_arm("jellyfish-count-A", "jellyfish", (150.0, 150.0, 150.0),
                      (10 * (1 << 30),) * 3),
        ])
        report = self.render([self.write_results(results)])
        self.assertIn("counting speed — **NO**", report)

    def test_overall_verdict_is_conjunction_across_k_tables(self):
        """k=31 YES + k=21 NO -> overall NO, with the split stated."""
        fast = typical_full_results(k=31)
        slow = build_results(mode="full", k=21, arms=[
            build_arm("count-A", "rustkmer", (500.0, 500.0, 500.0),
                      (50 * (1 << 30),) * 3),
            build_arm("jellyfish-count-A", "jellyfish", (100.0, 100.0, 100.0),
                      (50 * (1 << 30),) * 3),
        ])
        report = self.render([self.write_results(fast, "k31.json"),
                              self.write_results(slow, "k21.json")])
        self.assertIn("**NO** — rustkmer matches-or-beats", report)
        self.assertIn("k=31: YES; k=21: NO", report)


class TestMandatoryStatements(RenderFixtureBase):
    """Substitute labeling, cold-cache honesty, memory-beside-wall, parity."""

    def test_substitute_provenance_sentence_present(self):
        report = self.render([self.write_results(typical_full_results())])
        self.assertIn("CRR2044018", report)
        self.assertIn("CRR1936095", report)
        self.assertIn("substitute", report)

    def test_cold_cache_partial_statement_when_unavailable(self):
        report = self.render([self.write_results(typical_full_results())])
        self.assertIn("PARTIALLY SATISFIED", report)

    def test_no_cold_cache_caveat_when_all_purged(self):
        results = build_results(arms=[
            build_arm("count-A", "rustkmer", (1.0, 1.0, 1.0),
                      (10 * (1 << 30),) * 3, cache="purged"),
            build_arm("jellyfish-count-A", "jellyfish", (2.0, 2.0, 2.0),
                      (10 * (1 << 30),) * 3, cache="purged"),
        ])
        report = self.render([self.write_results(results)])
        self.assertNotIn("PARTIALLY SATISFIED", report)

    def test_peak_rss_beside_wall_for_every_arm(self):
        """BENCH-03: the table header pairs wall and RSS columns."""
        report = self.render([self.write_results(typical_full_results())])
        self.assertIn("median wall (s)", report)
        self.assertIn("median peak RSS (GiB)", report)

    def test_parity_lines_from_recorded_equality(self):
        """Same-input run: jellyfish vs count-A EQUAL; count-B repeat EQUAL."""
        results = typical_full_results()
        report = self.render([self.write_results(results)])
        self.assertIn("vs count-A distinct=1,000 total=2,000 -> EQUAL",
                      report)
        self.assertIn("vs count-A -> EQUAL (same input measured twice)",
                      report)
        results["arms"][0]["distinct_kmers"] = 999
        report = self.render([self.write_results(results)])
        self.assertIn("-> MISMATCH", report)

    def test_merge_input_run_does_not_mislabel_count_b_as_mismatch(self):
        """r1/r2 fingerprints differ: count-B is not a parity claim at all.

        The harness's gate compares jellyfish-count-A vs count-A only; a
        renderer that printed 'MISMATCH' for the r2 arm would fabricate a
        methodology finding the run never tripped.
        """
        results = build_results(mode="slice", arms=[
            build_arm("count-A", "rustkmer", (16.0, 16.0, 16.0),
                      (5 * (1 << 30),) * 3, distinct=100, total=1000),
            build_arm("count-B", "rustkmer", (16.0, 16.0, 16.0),
                      (5 * (1 << 30),) * 3, distinct=120, total=1100),
            build_arm("jellyfish-count-A", "jellyfish", (22.0, 22.0, 22.0),
                      (80 * (1 << 30),) * 3, distinct=100, total=1000),
            build_arm("merge", "rustkmer", (7.5, 7.5, 7.5),
                      (16 * (1 << 30),) * 3, distinct=150, total=2100),
        ], fingerprints=[
            {"path": "slice-0.fq", "size_bytes": 1, "sha256": "aa" * 32},
            {"path": "slice-1.fq", "size_bytes": 1, "sha256": "bb" * 32},
        ])
        report = self.render([self.write_results(typical_full_results()),
                              self.write_results(results, "slice.json")])
        self.assertIn("no jellyfish arm measured it, so this is not a "
                      "parity claim", report)
        slice_block = report.split("mode=slice k=31:", 1)[1]
        self.assertNotIn("MISMATCH", slice_block.split("\n", 1)[0])

    def test_merge_arm_rendered_with_conservation(self):
        results = build_results(mode="slice", arms=[
            build_arm("count-A", "rustkmer", (16.0, 16.0, 16.0),
                      (5 * (1 << 30),) * 3, distinct=100, total=1000),
            build_arm("count-B", "rustkmer", (16.0, 16.0, 16.0),
                      (5 * (1 << 30),) * 3, distinct=120, total=1100),
            build_arm("jellyfish-count-A", "jellyfish", (22.0, 22.0, 22.0),
                      (80 * (1 << 30),) * 3, distinct=100, total=1000),
            build_arm("merge", "rustkmer", (7.5, 7.5, 7.5),
                      (16 * (1 << 30),) * 3, distinct=150, total=2100),
        ])
        report = self.render([self.write_results(typical_full_results()),
                              self.write_results(results, "slice.json")])
        # merge has no jellyfish counterpart: delta columns are n/a
        self.assertIn("| merge | rustkmer | 7.50 | 16.00 | n/a | n/a |",
                      report)
        self.assertIn("EQUAL (count conservation)", report)
        self.assertIn("OK (distinct union)", report)

    def test_cv_warning_surfaced(self):
        results = build_results(arms=[
            build_arm("count-A", "rustkmer", (10.0, 10.0, 10.0),
                      (10 * (1 << 30),) * 3),
            build_arm("jellyfish-count-A", "jellyfish", (10.0, 20.0, 30.0),
                      (10 * (1 << 30),) * 3, cv_warning=True),
        ])
        report = self.render([self.write_results(results)])
        self.assertIn("[cv_warning]", report)
        self.assertIn("cv_warning flags:", report)


class TestErrorClasses(RenderFixtureBase):
    """Loud failures, never silent skips."""

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            render_report([str(self.root / "nope.json")],
                          self.root / "out.md")

    def test_no_full_mode_file_raises(self):
        slice_only = self.write_results(build_results(
            mode="slice",
            arms=[build_arm("count-A", "rustkmer", (1.0,) * 3,
                            (10 * (1 << 30),) * 3)]), "slice.json")
        with self.assertRaises(ValueError):
            render_report([str(slice_only)], self.root / "out.md")

    def test_one_sided_arms_raise(self):
        """A rustkmer-only file (reps=1 CI shape) cannot render a verdict."""
        one_sided = self.write_results(build_results(
            arms=[build_arm("count-A", "rustkmer", (1.0,),
                            (10 * (1 << 30),))]), "one.json")
        with self.assertRaises(ValueError):
            render_report([str(one_sided)], self.root / "out.md")

    def test_schema_violation_raises(self):
        bad = build_results(arms=[])
        path = self.write_results(bad, "bad.json")
        with self.assertRaises(ValueError):
            render_report([str(path)], self.root / "out.md")


class TestDeltaPct(unittest.TestCase):

    def test_sign_and_value(self):
        self.assertAlmostEqual(_delta_pct(50.0, 100.0), -50.0)
        self.assertAlmostEqual(_delta_pct(150.0, 100.0), 50.0)
        self.assertAlmostEqual(_delta_pct(100.0, 100.0), 0.0)

    def test_nonpositive_base_rejected(self):
        with self.assertRaises(ValueError):
            _delta_pct(1.0, 0.0)


if __name__ == "__main__":
    unittest.main()
