"""Unit tests for the PROF-02 thread-scaling gate (05-01).

Drives thread_scaling.main(argv) with --current synthetic docs the way CI
does (the CompareHarness pattern from test_compare.py): capture SystemExit,
stdout, and stderr. No sleeps — every timing doc is hand-built constants,
and the suite runs without jellyfish, PyO3, or the human dataset.

Pinned contracts:
  * verdict matrix — material scaling exits 0; identical/insufficient
    medians exit 1; missing arm, count mismatch, zero counts, malformed
    provenance, unsupported platform exit 2;
  * boundary — a speedup exactly equal to --min-speedup is GREEN
    (compare.py's inclusive convention); one ulp below is RED;
  * mutation proof (v1.0 lesson: a GREEN gate that cannot fail reports
    nothing) — changing ONLY count maps cannot pass a no-op timing matrix,
    and changing ONLY timings cannot hide a parity failure;
  * the machine-greppable SCALING VERDICT stdout line — result matches the
    exit semantics, numbers round-trip via repr(), and NO verdict line is
    printed on any exit-2 path;
  * rotation_schedule — pure counterbalancing: per-round arm coverage,
    rotation across rounds, wrap when reps > len(arms).

Stdlib unittest only — no pytest, no conftest.
"""

import contextlib
import io
import json
import math
import os
import tempfile
import unittest

from scripts.bench import thread_scaling


def make_provenance():
    """A complete, well-formed provenance block (hand-built constants)."""
    return {
        "binary": {
            "path": "/repo/target/release/rustkmer",
            "size_bytes": 3_166_136,
            "sha256": "a" * 64,
        },
        "git_commit": "b" * 40,
        "git_dirty": False,
        "build_profile": "release",
        "rust_toolchain": "rustc 1.80.0 (051478957 2024-07-21)",
        "platform": "darwin-arm64",
        "created": "2026-11-12T00:00:00+00:00",
    }


def make_arm(threads, wall, unique=24000, total=24000, k=21):
    """One schema-valid scaling arm with nested medians (the gate's shape)."""
    return {
        "name": f"rk{k}-t{threads}",
        "tool": "rustkmer",
        "threads": threads,
        "reps": [{"wall_s": wall, "peak_rss_bytes": 100_000_000,
                  "cache_state": "unavailable", "round": 0, "arm_order": 0}],
        "medians": {"wall_s": wall, "peak_rss_bytes": 100_000_000,
                    "cv_wall_pct": None, "cv_warning": False},
        "unique_kmers": unique,
        "total_kmers": total,
    }


def make_doc(walls=(100.0, 30.0, 20.0), unique=24000, total=24000,
             system="Darwin"):
    """A schema-valid, provenance-bearing scaling doc (no verdict block —
    scaling_verdict computes it; --current never trusts a stored verdict)."""
    arms = [make_arm(t, w, unique=unique, total=total)
            for t, w in zip((1, 4, 16), walls)]
    names = [a["name"] for a in arms]
    return {
        "schema_version": 1,
        "mode": "synthetic",
        "params": {"k": 21, "canonical": True, "thread_counts": [1, 4, 16],
                   "reps": 1, "cooldown_s": 0, "min_speedup": 1.3,
                   "rustkmer": "target/release/rustkmer", "reads": 5000},
        "platform": {"system": system, "release": "25.0",
                     "machine": "arm64", "python": "3.13.0"},
        "created": "2026-11-12T00:00:00+00:00",
        "input_fingerprint": [],
        "arms": arms,
        "schedule": {"policy": "round-robin-rotation",
                     "warmup_order": names, "rounds": [names]},
        "provenance": make_provenance(),
    }


class ScalingHarness(unittest.TestCase):
    """Shared driver: write a doc to a tempdir, run thread_scaling.main
    with --current, capture exit code / stdout / stderr (CompareHarness)."""

    def run_current_doc(self, doc, extra=()):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "current.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(doc, fh)
            return self.run_current_path(path, extra)

    def run_current_path(self, path, extra=()):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as ctx:
                thread_scaling.main(["--current", str(path), *extra])
        return ctx.exception.code, out.getvalue(), err.getvalue()

    def assert_verdict_line(self, out, result, speedup_t4=None,
                            speedup_t16=None, min_speedup=1.3):
        """Exactly one SCALING VERDICT line; result matches exit semantics;
        the repr()-emitted numbers round-trip exactly to the stored floats."""
        lines = [l for l in out.splitlines()
                 if l.startswith("SCALING VERDICT ")]
        self.assertEqual(len(lines), 1, out)
        fields = dict(tok.split("=", 1) for tok in lines[0].split()[2:])
        self.assertEqual(fields["result"], result)
        self.assertEqual(float(fields["min_speedup"]), min_speedup)
        if speedup_t4 is not None:
            self.assertEqual(float(fields["speedup_t4"]), speedup_t4)
        if speedup_t16 is not None:
            self.assertEqual(float(fields["speedup_t16"]), speedup_t16)

    def assert_no_verdict_line(self, out):
        self.assertNotIn("SCALING VERDICT", out)


class TestVerdictMatrix(ScalingHarness):
    """Exit 0/1/2 across the timing/count/provenance/platform matrix."""

    def test_material_scaling_green(self):
        """100/30/20 s medians -> both speedups >= 1.3 -> exit 0, GREEN."""
        code, out, _ = self.run_current_doc(make_doc(walls=(100.0, 30.0, 20.0)))
        self.assertEqual(code, 0)
        self.assert_verdict_line(out, "GREEN",
                                 speedup_t4=100.0 / 30.0,
                                 speedup_t16=100.0 / 20.0)

    def test_identical_medians_red(self):
        """The no-op signature t1 == t4 == t16 -> exit 1, RED."""
        code, out, _ = self.run_current_doc(
            make_doc(walls=(100.0, 100.0, 100.0)))
        self.assertEqual(code, 1)
        self.assert_verdict_line(out, "RED", speedup_t4=1.0, speedup_t16=1.0)

    def test_insufficient_scaling_red(self):
        """100/90/85 s -> speedups 1.11/1.18 below 1.3 -> exit 1, RED."""
        code, out, _ = self.run_current_doc(make_doc(walls=(100.0, 90.0, 85.0)))
        self.assertEqual(code, 1)
        self.assert_verdict_line(out, "RED",
                                 speedup_t4=100.0 / 90.0,
                                 speedup_t16=100.0 / 85.0)

    def test_threshold_equality_green(self):
        """130/100/100 -> both ratios exactly 1.3 -> exit 0 (the boundary
        belongs to green, compare.py's inclusive convention)."""
        code, out, _ = self.run_current_doc(
            make_doc(walls=(130.0, 100.0, 100.0)))
        self.assertEqual(code, 0)
        self.assert_verdict_line(out, "GREEN", speedup_t4=1.3, speedup_t16=1.3)

    def test_one_ulp_below_threshold_red(self):
        """One float ulp below the boundary ratio -> exit 1 (>= is exact,
        not approximately-equal)."""
        below = math.nextafter(130.0, 0.0)
        code, out, _ = self.run_current_doc(
            make_doc(walls=(below, 100.0, 100.0)))
        self.assertEqual(code, 1)
        self.assert_verdict_line(out, "RED", speedup_t4=below / 100.0)

    def test_missing_t4_arm_invalid(self):
        """No t4 arm -> exit 2, no verdict line."""
        doc = make_doc()
        doc["arms"] = [a for a in doc["arms"] if a["threads"] != 4]
        code, out, _ = self.run_current_doc(doc)
        self.assertEqual(code, 2)
        self.assert_no_verdict_line(out)

    def test_missing_t16_arm_invalid(self):
        """No t16 arm -> exit 2, no verdict line."""
        doc = make_doc()
        doc["arms"] = [a for a in doc["arms"] if a["threads"] != 16]
        code, out, _ = self.run_current_doc(doc)
        self.assertEqual(code, 2)
        self.assert_no_verdict_line(out)

    def test_count_mismatch_invalid(self):
        """One arm counted different k-mers -> exit 2, no verdict line."""
        doc = make_doc()
        doc["arms"][1]["unique_kmers"] += 1
        code, out, _ = self.run_current_doc(doc)
        self.assertEqual(code, 2)
        self.assert_no_verdict_line(out)

    def test_zero_unique_kmers_invalid(self):
        """Zero unique counts (silent input failure) -> exit 2, no verdict."""
        code, out, _ = self.run_current_doc(make_doc(unique=0))
        self.assertEqual(code, 2)
        self.assert_no_verdict_line(out)

    def test_malformed_provenance_invalid(self):
        """A non-hex binary sha256 -> exit 2, no verdict line (T-05-02:
        an unattributable artifact cannot gate)."""
        doc = make_doc()
        doc["provenance"]["binary"]["sha256"] = "not-a-hash"
        code, out, _ = self.run_current_doc(doc)
        self.assertEqual(code, 2)
        self.assert_no_verdict_line(out)

    def test_unsupported_platform_invalid(self):
        """platform.system outside Darwin/Linux -> exit 2, never a false
        PASS."""
        code, out, _ = self.run_current_doc(make_doc(system="Windows"))
        self.assertEqual(code, 2)
        self.assert_no_verdict_line(out)

    def test_missing_doc_file_invalid(self):
        """--current pointing at a nonexistent file -> exit 2, no verdict."""
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = self.run_current_path(
                os.path.join(tmp, "absent.json"))
        self.assertEqual(code, 2)
        self.assert_no_verdict_line(out)


class TestMutationProof(ScalingHarness):
    """v1.0 lesson: a GREEN gate that cannot fail reports nothing. Each
    mutation changes exactly ONE dimension of a hand-built doc."""

    def test_mutation_counts_only_cannot_pass_noop_matrix(self):
        """A no-op timing matrix with equal counts is RED (exit 1);
        changing ONLY the count maps must yield exit 2 — never 0."""
        doc = make_doc(walls=(100.0, 100.0, 100.0))
        code, out, _ = self.run_current_doc(doc)
        self.assertEqual(code, 1)
        self.assert_verdict_line(out, "RED")
        # Mutation: counts only — timings untouched.
        doc["arms"][1]["unique_kmers"] += 1
        code, out, _ = self.run_current_doc(doc)
        self.assertEqual(code, 2)
        self.assertNotEqual(code, 0)
        self.assert_no_verdict_line(out)

    def test_mutation_timings_only_cannot_hide_parity_failure(self):
        """A count-mismatched doc is invalid (exit 2); changing ONLY the
        timings to scale beautifully must stay exit 2 — never 0."""
        doc = make_doc(walls=(100.0, 100.0, 100.0))
        doc["arms"][1]["unique_kmers"] += 1
        code, out, _ = self.run_current_doc(doc)
        self.assertEqual(code, 2)
        self.assert_no_verdict_line(out)
        # Mutation: timings only — the count mismatch untouched.
        for arm, wall in zip(doc["arms"], (100.0, 25.0, 10.0)):
            arm["medians"]["wall_s"] = wall
            arm["reps"][0]["wall_s"] = wall
        code, out, _ = self.run_current_doc(doc)
        self.assertEqual(code, 2)
        self.assertNotEqual(code, 0)
        self.assert_no_verdict_line(out)


class TestRotationSchedule(unittest.TestCase):
    """The pure counterbalancing helper — no subprocesses, no I/O."""

    NAMES = ["rk21-t1", "rk21-t4", "rk21-t16"]

    def test_each_round_contains_every_arm_exactly_once(self):
        """Per-round coverage: every arm appears exactly once per round."""
        rounds = thread_scaling.rotation_schedule(self.NAMES, 3)
        self.assertEqual(len(rounds), 3)
        for rnd in rounds:
            self.assertEqual(sorted(rnd), sorted(self.NAMES))

    def test_consecutive_rounds_start_at_different_arms(self):
        """Rotation across rounds: no two consecutive rounds share a first
        arm (thermal/order bias rotates instead of accumulating)."""
        rounds = thread_scaling.rotation_schedule(self.NAMES, 3)
        for prev, nxt in zip(rounds, rounds[1:]):
            self.assertNotEqual(prev[0], nxt[0])

    def test_first_round_preserves_input_order(self):
        """Round 1 is the input order [t1, t4, t16]."""
        rounds = thread_scaling.rotation_schedule(self.NAMES, 3)
        self.assertEqual(rounds[0], self.NAMES)

    def test_rotation_wraps_when_reps_exceed_arms(self):
        """reps > len(arms): round r starts at arm index r mod len(arms)."""
        rounds = thread_scaling.rotation_schedule(self.NAMES, 7)
        self.assertEqual(len(rounds), 7)
        for r, rnd in enumerate(rounds):
            self.assertEqual(rnd[0], self.NAMES[r % len(self.NAMES)])
            self.assertEqual(sorted(rnd), sorted(self.NAMES))

    def test_empty_arm_names_raises(self):
        """No arms is a programming error, not an empty schedule."""
        with self.assertRaises(ValueError):
            thread_scaling.rotation_schedule([], 3)

    def test_zero_reps_raises(self):
        """reps < 1 is a programming error."""
        with self.assertRaises(ValueError):
            thread_scaling.rotation_schedule(self.NAMES, 0)


if __name__ == "__main__":
    unittest.main()