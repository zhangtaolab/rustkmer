"""Unit tests for the OUT-01 output-stage gate (08-01 Task 1).

The harness's exit codes are the gate contract, so every verdict test drives
the pure `stage_verdict`/`identity_verdict` helpers exactly the way
`capture`/`compare` do and asserts the classification:

  0 — GREEN: sha256 identity, strictly-below sorted wall, delta at most half
      the baseline delta (inclusive boundary), and RSS not regressed;
  1 — RED: a MEASURED failure (any one of the four conditions alone, a sha256
      mismatch included — a byte change is RED, never invalid);
  2 — INVALID: malformed/missing provenance, missing arms, or a baseline whose
      params / input fingerprint identify a different measurement.

Also pinned: the list-form argv construction (the unsorted arm is the sorted
argv plus one flag), the RAW (never clamped) sort delta, the counterbalanced
round-robin schedule, and the per-rep record shape (`cache_state` from an
injected purge function, `round`, `arm_order`) — with no real `sudo` call and
no sleeps. Stdlib unittest only — no pytest, no conftest.
"""

import contextlib
import io
import math
import os
import tempfile
import unittest

from scripts.bench import bench, output_stage

BASE_SHA = "0976f29c" + "0" * 56
OTHER_SHA = "f" * 64
BASE_FP_SHA = "71c6264b" + "0" * 56
OTHER_FP_SHA = "deadbeef" + "0" * 56

BASE_WALL = 17.5
BASE_UNSORTED_WALL = 9.8
BASE_RSS = 17_967_218_688
BASE_UNSORTED_RSS = 14_291_222_528


def make_provenance():
    """A complete, well-formed provenance block (hand-built constants)."""
    return {
        "binary": {
            "path": "/repo/target/release/rustkmer",
            "size_bytes": 2_965_056,
            "sha256": "a" * 64,
        },
        "git_commit": "b" * 40,
        "git_dirty": False,
        "build_profile": "release",
        "rust_toolchain": "rustc 1.82.0 (f6e511eec 2024-10-15)",
        "platform": "darwin-arm64",
        "created": "2026-11-13T00:00:00+00:00",
    }


def make_arm(name, wall, rss=1_000_000_000, sha=None,
             unique=229_694_874, total=519_271_168):
    """One schema-valid output-stage arm with nested medians."""
    arm = {
        "name": name,
        "tool": "rustkmer",
        "threads": 4,
        "reps": [{
            "wall_s": wall,
            "peak_rss_bytes": rss,
            "cache_state": "unavailable",
            "round": 0,
            "arm_order": 0 if name == "sorted" else 1,
        }],
        "medians": {
            "wall_s": wall,
            "peak_rss_bytes": rss,
            "cv_wall_pct": None,
            "cv_warning": False,
        },
        "unique_kmers": unique,
        "total_kmers": total,
    }
    if sha is not None:
        arm["sorted_rkdb_sha256"] = sha
    return arm


def make_params(**overrides):
    """The measured-scope params both capture and compare persist."""
    params = {
        "k": 21,
        "canonical": True,
        "threads": 4,
        "reps": 3,
        "cooldown_s": 5,
        "slice_reads": 4_000_000,
        "input": "/data/CRR1936095_r1.part_001.fq.gz",
        "rustkmer": "target/release/rustkmer",
        "arms": ["sorted", "unsorted"],
    }
    params.update(overrides)
    return params


def make_doc(sorted_wall=BASE_WALL, unsorted_wall=BASE_UNSORTED_WALL,
             sorted_rss=BASE_RSS, unsorted_rss=BASE_UNSORTED_RSS,
             sha=BASE_SHA, delta=None, params=None, fp_sha=BASE_FP_SHA):
    """A schema-valid, provenance-bearing output-stage document."""
    if delta is None:
        delta = sorted_wall - unsorted_wall
    return {
        "schema_version": 1,
        "mode": "output_stage",
        "params": params if params is not None else make_params(),
        "platform": {"system": "Darwin", "release": "25.0",
                     "machine": "arm64", "python": "3.13.0"},
        "created": "2026-11-13T00:00:00+00:00",
        "input_fingerprint": [{
            "path": "pre/slice-0.fq",
            "size_bytes": 1_472_481_891,
            "sha256": fp_sha,
        }],
        "arms": [
            make_arm("sorted", sorted_wall, sorted_rss, sha=sha),
            make_arm("unsorted", unsorted_wall, unsorted_rss),
        ],
        "schedule": {
            "policy": "round-robin-rotation",
            "warmup_order": ["sorted", "unsorted"],
            "rounds": [["sorted", "unsorted"],
                       ["unsorted", "sorted"],
                       ["sorted", "unsorted"]],
        },
        "sort_delta_s": delta,
        "provenance": make_provenance(),
    }


class TestArmCommand(unittest.TestCase):
    """List-form argv construction — no shell, only the sort flag differs."""

    def test_sorted_arm_is_the_default_argv(self):
        cfg = bench.BenchmarkConfig(k=21, canonical=True, threads=4,
                                    inputs=["slice-0.fq"])
        argv = output_stage.arm_cmd(cfg, "out.rkdb",
                                    "target/release/rustkmer", "sorted")
        self.assertIsInstance(argv, list)
        self.assertEqual(argv[:2], ["target/release/rustkmer", "count"])
        self.assertNotIn("--no-sort", argv)
        self.assertIn("--threads", argv)
        self.assertEqual(argv[argv.index("--threads") + 1], "4")
        self.assertIn("-C", argv)
        self.assertEqual(argv[argv.index("-i") + 1], "slice-0.fq")

    def test_unsorted_arm_appends_the_no_sort_flag(self):
        cfg = bench.BenchmarkConfig(k=21, canonical=True, threads=4,
                                    inputs=["slice-0.fq"])
        sorted_argv = output_stage.arm_cmd(
            cfg, "out.rkdb", "target/release/rustkmer", "sorted")
        unsorted_argv = output_stage.arm_cmd(
            cfg, "out.rkdb", "target/release/rustkmer", "unsorted")
        self.assertEqual(unsorted_argv[-1], "--no-sort")
        self.assertEqual(unsorted_argv[:-1], sorted_argv)
        self.assertEqual(len(unsorted_argv), len(sorted_argv) + 1)

    def test_unknown_arm_is_rejected(self):
        cfg = bench.BenchmarkConfig(k=21, canonical=True, threads=4,
                                    inputs=["slice-0.fq"])
        with self.assertRaises(ValueError):
            output_stage.arm_cmd(cfg, "out.rkdb",
                                 "target/release/rustkmer", "sideways")


class TestSortDelta(unittest.TestCase):
    """The delta is the RAW sorted-minus-unsorted median difference."""

    def test_positive_delta(self):
        self.assertAlmostEqual(output_stage.sort_delta_s(17.54, 9.83), 7.71)

    def test_negative_delta_is_recorded_unclamped(self):
        # A sorted run that ended up FASTER is an honest observation; clamping
        # it to zero would corrupt the 0.5x post-change gate.
        self.assertEqual(output_stage.sort_delta_s(8.0, 10.5), -2.5)

    def test_exact_zero(self):
        self.assertEqual(output_stage.sort_delta_s(5.0, 5.0), 0.0)


class TestRotationSchedule(unittest.TestCase):
    """Pure counterbalanced rotation (thread_scaling.py's semantics)."""

    NAMES = ("sorted", "unsorted")

    def test_two_arms_three_reps(self):
        self.assertEqual(
            output_stage.rotation_schedule(self.NAMES, 3),
            [["sorted", "unsorted"],
             ["unsorted", "sorted"],
             ["sorted", "unsorted"]])

    def test_every_arm_exactly_once_per_round(self):
        for round_order in output_stage.rotation_schedule(self.NAMES, 3):
            self.assertEqual(sorted(round_order), sorted(self.NAMES))
            self.assertEqual(len(round_order), len(self.NAMES))

    def test_rotation_wraps_when_reps_exceed_arms(self):
        rounds = output_stage.rotation_schedule(self.NAMES, 7)
        self.assertEqual(len(rounds), 7)
        self.assertEqual(rounds[0], ["sorted", "unsorted"])
        self.assertEqual(rounds[1], ["unsorted", "sorted"])
        self.assertEqual(rounds[2], ["sorted", "unsorted"])
        for round_order in rounds:
            self.assertEqual(sorted(round_order), sorted(self.NAMES))

    def test_empty_or_zero_reps_is_rejected(self):
        with self.assertRaises(ValueError):
            output_stage.rotation_schedule([], 3)
        with self.assertRaises(ValueError):
            output_stage.rotation_schedule(self.NAMES, 0)


class TestMeasuredRounds(unittest.TestCase):
    """Per-rep record shape, injected purge, no sudo and no sleeps."""

    def test_records_cache_state_round_and_arm_order(self):
        sleeps = []
        measured = []

        def fake_measure(argv):
            measured.append(list(argv))
            return {"wall_s": 1.0, "peak_rss_bytes": 10}

        def fake_purge():
            return "runner-fresh"

        reps = output_stage.run_measured_rounds(
            output_stage.rotation_schedule(("sorted", "unsorted"), 3),
            {"sorted": ["s"], "unsorted": ["u"]},
            5,
            measure_fn=fake_measure,
            purge_fn=fake_purge,
            sleep_fn=sleeps.append,
        )

        self.assertEqual(sleeps, [5, 5, 5, 5, 5])  # 6 runs -> 5 gaps
        self.assertEqual(len(measured), 6)
        self.assertEqual(
            sorted((r["round"], r["arm_order"]) for r in reps["sorted"]),
            [(0, 0), (1, 1), (2, 0)])
        self.assertEqual(
            sorted((r["round"], r["arm_order"]) for r in reps["unsorted"]),
            [(0, 1), (1, 0), (2, 1)])
        for name in ("sorted", "unsorted"):
            for rep in reps[name]:
                self.assertEqual(rep["cache_state"], "runner-fresh")
                self.assertIn(rep["round"], (0, 1, 2))
                self.assertIn(rep["arm_order"], (0, 1))

    def test_on_rep_hook_observes_every_rep(self):
        seen = []
        reps = output_stage.run_measured_rounds(
            output_stage.rotation_schedule(("sorted", "unsorted"), 1),
            {"sorted": ["s"], "unsorted": ["u"]},
            0,
            measure_fn=lambda argv: {"wall_s": 1.0, "peak_rss_bytes": 1},
            purge_fn=lambda: "unavailable",
            sleep_fn=lambda _s: None,
            on_rep=lambda name, rep, rnd, pos: seen.append(
                (name, rnd, pos)),
        )
        self.assertEqual(seen, [("sorted", 0, 0), ("unsorted", 0, 1)])
        self.assertEqual(len(reps["sorted"]), 1)


class TestStageVerdict(unittest.TestCase):
    """The four-condition GREEN matrix, each failure isolated, plus exit 2."""

    def setUp(self):
        self.baseline = make_doc()

    def assert_verdict(self, post, result, score_substring=None):
        code, lines, verdict = output_stage.stage_verdict(self.baseline, post)
        self.assertIsNotNone(verdict, lines)
        self.assertEqual(verdict["result"], result)
        if result == "GREEN":
            self.assertEqual(code, 0)
        else:
            self.assertEqual(code, 1)
        if score_substring is not None:
            self.assertIn(score_substring, verdict["score"])
        line = output_stage.verdict_line(verdict)
        self.assertTrue(line.startswith("OUTPUT STAGE VERDICT result="))
        return verdict

    def test_all_conditions_pass_is_green(self):
        post = make_doc(sorted_wall=8.0, unsorted_wall=7.2,
                        sorted_rss=16_000_000_000,
                        unsorted_rss=15_000_000_000, sha=BASE_SHA)
        verdict = self.assert_verdict(post, "GREEN")
        self.assertTrue(verdict["sha256_match"])
        self.assertEqual(verdict["score"], "ok")
        self.assertAlmostEqual(verdict["sort_delta_s"], 0.8)

    def test_sha256_mismatch_alone_is_red_not_invalid(self):
        post = make_doc(sorted_wall=8.0, unsorted_wall=7.2,
                        sorted_rss=16_000_000_000, sha=OTHER_SHA)
        verdict = self.assert_verdict(post, "RED", "sha256_mismatch")
        self.assertFalse(verdict["sha256_match"])

    def test_wall_not_strictly_below_alone_is_red(self):
        # Same sorted median wall as the baseline; delta kept small so only
        # the strict-wall condition fails.
        post = make_doc(sorted_wall=BASE_WALL, unsorted_wall=16.5,
                        sorted_rss=16_000_000_000, delta=1.0)
        self.assert_verdict(post, "RED", "wall_not_below_baseline")

    def test_delta_above_half_alone_is_red(self):
        post = make_doc(sorted_wall=8.0, unsorted_wall=3.0,
                        sorted_rss=16_000_000_000, delta=4.5)
        self.assert_verdict(post, "RED", "sort_delta_not_halved")

    def test_rss_regression_alone_is_red(self):
        post = make_doc(sorted_wall=8.0, unsorted_wall=7.2,
                        sorted_rss=BASE_RSS + 1)
        self.assert_verdict(post, "RED", "rss_regressed")

    def test_exact_half_delta_boundary_passes(self):
        # Binary-exact values: baseline delta = 17.5 - 9.5 = 8.0; half = 4.0.
        # Equality passes (compare.py's inclusive convention).
        baseline = make_doc(unsorted_wall=9.5)
        post = make_doc(sorted_wall=8.0, unsorted_wall=4.0,
                        sorted_rss=16_000_000_000, delta=4.0)
        code, _lines, verdict = output_stage.stage_verdict(baseline, post)
        self.assertEqual(verdict["result"], "GREEN", verdict)
        self.assertEqual(code, 0)

    def test_one_ulp_above_half_delta_fails(self):
        baseline = make_doc(unsorted_wall=9.5)
        post = make_doc(sorted_wall=8.0, unsorted_wall=4.0,
                        sorted_rss=16_000_000_000,
                        delta=math.nextafter(4.0, math.inf))
        code, _lines, verdict = output_stage.stage_verdict(baseline, post)
        self.assertEqual(verdict["result"], "RED", verdict)
        self.assertEqual(code, 1)
        self.assertIn("sort_delta_not_halved", verdict["score"])

    def test_missing_arm_is_invalid_with_no_verdict(self):
        broken = make_doc()
        broken["arms"] = [broken["arms"][1]]
        code, lines, verdict = output_stage.stage_verdict(self.baseline, broken)
        self.assertEqual(code, 2)
        self.assertIsNone(verdict)
        self.assertTrue(any("sorted arm" in line for line in lines))

    def test_bad_provenance_is_invalid_with_no_verdict(self):
        broken = make_doc()
        del broken["provenance"]["binary"]["sha256"]
        code, _lines, verdict = output_stage.stage_verdict(self.baseline, broken)
        self.assertEqual(code, 2)
        self.assertIsNone(verdict)

    def test_negative_baseline_delta_is_kept_raw(self):
        # A baseline delta of -1.0 must not be clamped to 0: its half is
        # -0.5, so a post delta of 0.0 fails the half-delta condition.
        baseline = make_doc(delta=-1.0)
        post = make_doc(sorted_wall=8.0, unsorted_wall=8.0,
                        sorted_rss=16_000_000_000, delta=0.0)
        code, _lines, verdict = output_stage.stage_verdict(baseline, post)
        self.assertEqual(code, 1)
        self.assertEqual(verdict["result"], "RED")
        self.assertIn("sort_delta_not_halved", verdict["score"])
        # The raw stored value is what the verdict reports.
        self.assertEqual(verdict["sort_delta_s"], 0.0)


class TestIdentity(unittest.TestCase):
    """The baseline and the post run must be the same measurement."""

    def setUp(self):
        self.baseline = make_doc()
        self.fp = self.baseline["input_fingerprint"]

    def test_identical_params_and_fingerprint_is_ok(self):
        code, reason = output_stage.identity_verdict(
            self.baseline, make_params(), self.fp)
        self.assertEqual((code, reason), (0, ""))

    def test_threads_mismatch_is_exit_2(self):
        code, reason = output_stage.identity_verdict(
            self.baseline, make_params(threads=16), self.fp)
        self.assertEqual(code, 2)
        self.assertIn("threads", reason)

    def test_fingerprint_mismatch_is_exit_2(self):
        other = [{"path": "pre/slice-0.fq", "size_bytes": 1,
                  "sha256": OTHER_FP_SHA}]
        code, reason = output_stage.identity_verdict(
            self.baseline, make_params(), other)
        self.assertEqual(code, 2)
        self.assertIn("fingerprint", reason)

    def test_params_only_check_skips_fingerprint(self):
        code, reason = output_stage.identity_verdict(
            self.baseline, make_params(), None)
        self.assertEqual((code, reason), (0, ""))


class TestDocument(unittest.TestCase):
    """The assembled document must pass the shared validators unchanged."""

    def test_assembled_document_passes_schema_and_provenance(self):
        doc = output_stage.assemble_doc(
            params=make_params(),
            input_fingerprint=[{"path": "pre/slice-0.fq",
                                "size_bytes": 1,
                                "sha256": BASE_FP_SHA}],
            arms=[make_arm("sorted", BASE_WALL, BASE_RSS, sha=BASE_SHA),
                  make_arm("unsorted", BASE_UNSORTED_WALL,
                           BASE_UNSORTED_RSS)],
            schedule={"policy": "round-robin-rotation",
                      "warmup_order": ["sorted", "unsorted"],
                      "rounds": [["sorted", "unsorted"]]},
            sort_delta=BASE_WALL - BASE_UNSORTED_WALL,
            provenance=make_provenance(),
            platform_block={"system": "Darwin", "release": "25.0",
                            "machine": "arm64", "python": "3.13.0"},
        )
        bench.validate_schema(doc)
        bench.validate_provenance(doc)
        self.assertEqual(doc["mode"], "output_stage")
        self.assertEqual(doc["schedule"]["policy"], "round-robin-rotation")
        self.assertEqual(doc["params"]["threads"], 4)

    def test_missing_baseline_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = os.path.join(tmp, "rustkmer")
            with open(exe, "w", encoding="utf-8") as fh:
                fh.write("#!/bin/sh\nexit 0\n")
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), \
                    contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as ctx:
                    output_stage.main([
                        "compare",
                        "--baseline", os.path.join(tmp, "missing.json"),
                        "--out", os.path.join(tmp, "post.json"),
                        "--rustkmer", exe,
                    ])
            self.assertEqual(ctx.exception.code, 2)
            self.assertNotIn("OUTPUT STAGE VERDICT", out.getvalue())

    def test_invalid_baseline_json_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = os.path.join(tmp, "rustkmer")
            with open(exe, "w", encoding="utf-8") as fh:
                fh.write("#!/bin/sh\nexit 0\n")
            baseline = os.path.join(tmp, "baseline.json")
            with open(baseline, "w", encoding="utf-8") as fh:
                fh.write("{not json")
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), \
                    contextlib.redirect_stderr(err):
                with self.assertRaises(SystemExit) as ctx:
                    output_stage.main([
                        "compare", "--baseline", baseline,
                        "--out", os.path.join(tmp, "post.json"),
                        "--rustkmer", exe,
                    ])
            self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
