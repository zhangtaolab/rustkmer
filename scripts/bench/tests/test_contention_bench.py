"""Unit tests for the 05-05 contention controller contention_bench.py (PROF-03).

The controller's exit codes are the evidence contract, so the suite pins:

  0 — valid evidence written (real capture; not exercised here),
  1 — a conservation failure in ANY raw record invalidates the whole run,
  2 — invalid inputs: missing (variant, threads) cells, malformed microbench
      JSON, lockfile mismatch/absence, bad arguments.

Attribution-v1 arithmetic is tested with hand-built medians (exact float
assertions), including the honesty contract: negative or near-zero shares
are recorded as measured with an inconclusive note, never clamped to look
decisive. rotation_schedule is tested for per-round coverage, rotation, and
wrap. Stdlib unittest only — no cargo, no PyO3, no human dataset.

The module import is guarded so the RED phase fails on planned assertions
(self.assertIsNotNone) rather than a collection/import error.
"""

import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

try:
    from scripts.bench import contention_bench
except ImportError:  # RED phase: module does not exist yet
    contention_bench = None

VARIANTS = ("shared-counter", "shared-dashmap", "atomic-only", "thread-local")
THREADS = (1, 4, 16)


def make_record(variant, threads, ns_per_window, rep=0, **overrides):
    """One schema-complete raw microbench record (conservation-passing)."""
    rec = {
        "variant": variant,
        "threads": threads,
        "k": 21,
        "reads": 200000,
        "windows": 26000000,
        "distinct": 16000000,
        "elapsed_ns": int(ns_per_window * 26000000),
        "ns_per_window": float(ns_per_window),
        "total_count": 26000000,
        "unique_count": 16000000,
        "conservation_ok": True,
        "rep": rep,
    }
    rec.update(overrides)
    return rec


def make_records(ns_by_variant_threads, reps=1):
    """Full 4x3 grid of records from {(variant, threads): ns} (constant reps)."""
    records = []
    for (variant, threads), ns in ns_by_variant_threads.items():
        for rep in range(reps):
            records.append(make_record(variant, threads, ns, rep=rep))
    return records


def decisive_grid():
    """Hand-built decisive split at t16: sc=900, sd=500, ao=400, tl=100.

    global-atomics share = 900-500 = 400; bandwidth share = 500-100 = 400;
    total gap = 800 -> 50%/50%. Multiplier = sc(t16)/sc(t1) = 900/100 = 9.
    """
    return {
        ("shared-counter", 1): 100.0,
        ("shared-counter", 4): 300.0,
        ("shared-counter", 16): 900.0,
        ("shared-dashmap", 1): 80.0,
        ("shared-dashmap", 4): 200.0,
        ("shared-dashmap", 16): 500.0,
        ("atomic-only", 1): 10.0,
        ("atomic-only", 4): 100.0,
        ("atomic-only", 16): 400.0,
        ("thread-local", 1): 60.0,
        ("thread-local", 4): 80.0,
        ("thread-local", 16): 100.0,
    }


class ContentionTestCase(unittest.TestCase):
    """Shared guard + quiet main() driver."""

    def setUp(self):
        self.assertIsNotNone(
            contention_bench, "contention_bench not implemented yet (05-05)")

    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as ctx:
                contention_bench.main(argv)
        return ctx.exception.code, out.getvalue(), err.getvalue()


class TestAttributionArithmetic(ContentionTestCase):
    """attribution-v1: exact subtraction formulas on hand-built medians."""

    def test_exact_arithmetic_on_hand_built_medians(self):
        """sc=900 sd=500 tl=100 at t16 -> 400/400 ns shares, 50/50 pct."""
        result = contention_bench.attribute(make_records(decisive_grid()))
        self.assertEqual(result["shared_counter_ns"], 900.0)
        self.assertEqual(
            result["shared_dashmap_without_global_atomics_ns"], 500.0)
        self.assertEqual(result["atomic_only_ns"], 400.0)
        self.assertEqual(result["thread_local_ns"], 100.0)
        self.assertEqual(result["global_atomics_attribution_ns"], 400.0)
        self.assertEqual(result["memory_bandwidth_attribution_ns"], 400.0)
        self.assertEqual(result["global_atomics_attribution_pct"], 50.0)
        self.assertEqual(result["memory_bandwidth_attribution_pct"], 50.0)
        self.assertEqual(result["notes"], [])

    def test_contention_multiplier_is_t16_over_t1(self):
        """916/97.3 — the research in-vivo shape — computed exactly."""
        grid = decisive_grid()
        grid[("shared-counter", 1)] = 97.3
        grid[("shared-counter", 16)] = 916.0
        result = contention_bench.attribute(make_records(grid))
        self.assertEqual(result["contention_multiplier"], 916.0 / 97.3)

    def test_medians_across_rounds_not_mean(self):
        """A single slow round must not drag the headline (median, not mean)."""
        grid = decisive_grid()
        records = make_records(grid)
        # Replace the three shared-counter t16 reps with [800, 900, 10000].
        records = [r for r in records
                   if not (r["variant"] == "shared-counter"
                           and r["threads"] == 16)]
        for rep, ns in enumerate((800.0, 900.0, 10000.0)):
            records.append(make_record("shared-counter", 16, ns, rep=rep))
        result = contention_bench.attribute(records)
        self.assertEqual(result["shared_counter_ns"], 900.0)
        self.assertEqual(result["global_atomics_attribution_ns"], 400.0)

    def test_per_cell_medians_cover_every_cell(self):
        result = contention_bench.attribute(make_records(decisive_grid()))
        cells = result["per_cell_medians"]
        self.assertEqual(len(cells), 12)
        self.assertEqual(cells["shared-counter-t1"], 100.0)
        self.assertEqual(cells["thread-local-t16"], 100.0)
        self.assertEqual(cells["atomic-only-t4"], 100.0)


class TestHonestyContract(ContentionTestCase):
    """Negative / near-zero shares are recorded honestly, never clamped."""

    def test_negative_share_recorded_with_inconclusive_note(self):
        """sc < sd at t16 -> negative global-atomics share, kept as measured."""
        grid = decisive_grid()
        grid[("shared-counter", 16)] = 300.0  # below shared-dashmap's 500
        result = contention_bench.attribute(make_records(grid))
        self.assertEqual(result["global_atomics_attribution_ns"], -200.0)
        self.assertEqual(result["memory_bandwidth_attribution_ns"], 400.0)
        self.assertTrue(result["notes"], "expected an inconclusive note")
        joined = " ".join(result["notes"]).lower()
        self.assertIn("inconclusive", joined)

    def test_near_zero_share_recorded_with_inconclusive_note(self):
        """A share below 1% of the total gap is flagged, not celebrated."""
        grid = decisive_grid()
        grid[("shared-dashmap", 16)] = 895.0  # global share 5 of gap 800
        result = contention_bench.attribute(make_records(grid))
        self.assertEqual(result["global_atomics_attribution_ns"], 5.0)
        self.assertTrue(result["notes"])
        self.assertIn("inconclusive", " ".join(result["notes"]).lower())

    def test_nonpositive_total_gap_yields_null_pcts_and_note(self):
        """sc == tl at t16: percentages are undefined -> None, never 0/100."""
        grid = decisive_grid()
        grid[("shared-counter", 16)] = 100.0
        grid[("shared-dashmap", 16)] = 100.0
        result = contention_bench.attribute(make_records(grid))
        self.assertIsNone(result["global_atomics_attribution_pct"])
        self.assertIsNone(result["memory_bandwidth_attribution_pct"])
        self.assertTrue(result["notes"])


class TestConservationInvalidates(ContentionTestCase):
    """A conservation failure in ANY raw record invalidates the whole run."""

    def test_conservation_flag_false_raises(self):
        records = make_records(decisive_grid())
        records[5]["conservation_ok"] = False
        with self.assertRaises(contention_bench.ConservationError):
            contention_bench.attribute(records)

    def test_counts_disagreeing_with_windows_raises_even_if_flag_true(self):
        """Defense in depth: recompute conservation, don't trust the flag."""
        records = make_records(decisive_grid())
        records[3]["total_count"] = records[3]["windows"] + 1
        with self.assertRaises(contention_bench.ConservationError):
            contention_bench.attribute(records)

    def test_unique_disagreeing_with_distinct_raises(self):
        records = make_records(decisive_grid())
        records[7]["unique_count"] = records[7]["distinct"] - 1
        with self.assertRaises(contention_bench.ConservationError):
            contention_bench.attribute(records)

    def test_main_maps_conservation_failure_to_exit_1(self):
        with mock.patch.object(contention_bench, "run",
                               side_effect=contention_bench.ConservationError(
                                   "record 5 failed conservation")):
            code, _, err = self.run_main(
                ["--synthetic", "--out", "unused.json"])
        self.assertEqual(code, 1)
        self.assertIn("conservation", err.lower())


class TestInvalidInputs(ContentionTestCase):
    """Missing cells / malformed JSON / bad values are exit-2 invalid."""

    def test_missing_cell_raises_invalid(self):
        records = make_records(decisive_grid())
        records = [r for r in records
                   if not (r["variant"] == "thread-local"
                           and r["threads"] == 16)]
        with self.assertRaises(contention_bench.InvalidRecords):
            contention_bench.attribute(records)

    def test_missing_thread_count_raises_invalid(self):
        records = make_records(decisive_grid())
        records = [r for r in records if r["threads"] != 4]
        with self.assertRaises(contention_bench.InvalidRecords):
            contention_bench.attribute(records)

    def test_zero_ns_per_window_raises_invalid(self):
        records = make_records(decisive_grid())
        records[0]["ns_per_window"] = 0.0
        with self.assertRaises(contention_bench.InvalidRecords):
            contention_bench.attribute(records)

    def test_inconsistent_windows_across_records_raises_invalid(self):
        records = make_records(decisive_grid())
        records[2]["windows"] = 12345
        records[2]["total_count"] = 12345
        with self.assertRaises(contention_bench.InvalidRecords):
            contention_bench.attribute(records)

    def test_malformed_microbench_json_raises_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.json")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("{not json")
            with self.assertRaises(contention_bench.InvalidRecords):
                contention_bench.load_microbench_json(path)

    def test_microbench_json_missing_records_key_raises_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "norecords.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"data": []}, fh)
            with self.assertRaises(contention_bench.InvalidRecords):
                contention_bench.load_microbench_json(path)

    def test_microbench_json_record_missing_field_raises_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "short.json")
            rec = make_record("shared-counter", 1, 100.0)
            del rec["ns_per_window"]
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"records": [rec]}, fh)
            with self.assertRaises(contention_bench.InvalidRecords):
                contention_bench.load_microbench_json(path)

    def test_main_maps_invalid_records_to_exit_2(self):
        with mock.patch.object(contention_bench, "run",
                               side_effect=contention_bench.InvalidRecords(
                                   "missing cell thread-local-t16")):
            code, _, err = self.run_main(
                ["--synthetic", "--out", "unused.json"])
        self.assertEqual(code, 2)
        self.assertIn("missing cell", err)

    def test_main_maps_unexpected_failure_to_exit_2(self):
        with mock.patch.object(contention_bench, "run",
                               side_effect=RuntimeError("cargo exploded")):
            code, _, _ = self.run_main(["--synthetic", "--out", "unused.json"])
        self.assertEqual(code, 2)

    def test_missing_real_input_exits_2_before_any_build(self):
        code, _, err = self.run_main(
            ["--input", "/nonexistent/reads.fq.gz", "--out", "unused.json"])
        self.assertEqual(code, 2)
        self.assertIn("input", err.lower())


class TestRotationSchedule(ContentionTestCase):
    """Counterbalanced rounds: coverage, rotation, wrap, invalid inputs."""

    def test_every_round_contains_every_cell_exactly_once(self):
        cells = [f"{v}-t{t}" for v in VARIANTS for t in THREADS]
        schedule = contention_bench.rotation_schedule(cells, 3)
        self.assertEqual(len(schedule), 3)
        for rnd in schedule:
            self.assertEqual(sorted(rnd), sorted(cells))

    def test_round_r_starts_at_index_r_minus_1(self):
        cells = [f"c{i}" for i in range(12)]
        schedule = contention_bench.rotation_schedule(cells, 3)
        for r in range(1, 4):
            self.assertEqual(schedule[r - 1][0], cells[(r - 1) % 12])
        self.assertEqual(schedule[0], cells)
        self.assertEqual(schedule[1], cells[1:] + cells[:1])
        self.assertEqual(schedule[2], cells[2:] + cells[:2])

    def test_rotation_wraps_when_reps_exceed_cells(self):
        cells = ["a", "b", "c"]
        schedule = contention_bench.rotation_schedule(cells, 5)
        self.assertEqual(schedule[3], cells)  # wrap: round 4 == round 1
        self.assertEqual(schedule[4], cells[1:] + cells[:1])

    def test_empty_cells_raises(self):
        with self.assertRaises(ValueError):
            contention_bench.rotation_schedule([], 3)

    def test_zero_reps_raises(self):
        with self.assertRaises(ValueError):
            contention_bench.rotation_schedule(["a"], 0)


class TestLockfileIntegrity(ContentionTestCase):
    """The build never runs unlocked: scratch lock must equal committed lock."""

    def _fixture_repo(self, tmp):
        prof = os.path.join(tmp, "repo", ".planning", "research", "profiling")
        os.makedirs(prof)
        with open(os.path.join(prof, "microbench_main.rs"), "w") as fh:
            fh.write("fn main() {}\n")
        with open(os.path.join(prof, "microbench_Cargo.toml"), "w") as fh:
            fh.write('[dependencies]\nrustkmer = { path = "@REPO_ROOT@" }\n')
        with open(os.path.join(prof, "microbench_Cargo.lock"), "w") as fh:
            fh.write('# committed lock\nname = "dashmap"\n')
        return prof

    def test_materialize_substitutes_repo_root_and_copies_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            prof = self._fixture_repo(tmp)
            repo_root = os.path.join(tmp, "repo")
            crate_dir = os.path.join(tmp, "scratch", "microbench")
            contention_bench.materialize_crate(repo_root, crate_dir)
            with open(os.path.join(crate_dir, "Cargo.toml")) as fh:
                manifest = fh.read()
            self.assertNotIn("@REPO_ROOT@", manifest)
            self.assertIn(repo_root, manifest)
            with open(os.path.join(crate_dir, "src", "main.rs")) as fh:
                self.assertEqual(fh.read(), "fn main() {}\n")
            committed = os.path.join(prof, "microbench_Cargo.lock")
            scratch = os.path.join(crate_dir, "Cargo.lock")
            with open(committed, "rb") as fh:
                committed_bytes = fh.read()
            with open(scratch, "rb") as fh:
                self.assertEqual(fh.read(), committed_bytes)

    def test_lockfile_mismatch_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            prof = self._fixture_repo(tmp)
            crate_dir = os.path.join(tmp, "scratch", "microbench")
            os.makedirs(crate_dir)
            with open(os.path.join(crate_dir, "Cargo.lock"), "w") as fh:
                fh.write("# TAMPERED lock\n")
            committed = os.path.join(prof, "microbench_Cargo.lock")
            with self.assertRaises(SystemExit) as ctx:
                contention_bench.verify_scratch_lockfile(crate_dir, committed)
            self.assertEqual(ctx.exception.code, 2)

    def test_missing_scratch_lockfile_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            prof = self._fixture_repo(tmp)
            crate_dir = os.path.join(tmp, "scratch", "microbench")
            os.makedirs(crate_dir)
            committed = os.path.join(prof, "microbench_Cargo.lock")
            with self.assertRaises(SystemExit) as ctx:
                contention_bench.verify_scratch_lockfile(crate_dir, committed)
            self.assertEqual(ctx.exception.code, 2)

    def test_missing_committed_lockfile_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            crate_dir = os.path.join(tmp, "scratch", "microbench")
            os.makedirs(crate_dir)
            with open(os.path.join(crate_dir, "Cargo.lock"), "w") as fh:
                fh.write("# lock\n")
            with self.assertRaises(SystemExit) as ctx:
                contention_bench.verify_scratch_lockfile(
                    crate_dir, os.path.join(tmp, "absent.lock"))
            self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
