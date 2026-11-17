#!/usr/bin/env python3
"""Unit suite for the Phase-13 producer-attribution driver (phase13.py).

Wave-0 behaviors, one class per function under test, stdlib unittest only,
binary-light: no cargo build, no dataset, no network. The live rehearsal is
the driver's own `--rehearsal` verify; this module proves the pure functions
and the schema guards the full-scale stages ride on.

The load-bearing rules encoded here:
  * the D-03/D-10 fingerprint gate BRANCHES (match -> cite, mismatch ->
    re-measure) and always carries both hashes;
  * the evidence doc is its own kind, never a fork of the bench results
    schema, and upsert keys on the FULL record identity
    (arm, k, rep, part, input_type);
  * the probe-nanos reduction is input-type scoped: one arm's records are
    filtered to the NAMED input type, the two pinned-pair parts are summed
    per rep, then the median over reps is taken;
  * /usr/bin/time parsing is fail-loud, never best-effort.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.bench import phase13


# --- fixture helpers ---------------------------------------------------------


def provenance_block(sha="8f38d20c2e3dc77dfc0ef80c9a2475613da1aa7ad131bd240"
                         "d5ec74fc87c3d23"):
    """A well-formed bench.binary_provenance-shaped block for fixtures."""
    return {
        "binary": {"path": "/tmp/fixture-rustkmer", "size_bytes": 1234,
                   "sha256": sha},
        "git_commit": "0" * 40,
        "git_dirty": False,
        "build_profile": "release",
        "rust_toolchain": "rustc 1.82.0 (fixture)",
        "platform": "darwin-arm64",
        "created": "2026-11-17T00:00:00+00:00",
    }


def run_record(arm, k, rep, *, part=None, input_type="gzip",
               wall=1.0, scale="full", **extra):
    """A minimal complete run record (wall_s + peak_rss_bytes present)."""
    record = {
        "arm": arm,
        "k": k,
        "rep": rep,
        "scale": scale,
        "input_type": input_type,
        "part": part,
        "wall_s": wall,
        "peak_rss_bytes": 1024,
        "peak_bytes": 1024,
        "peak_footprint_bytes": 1024,
        "cache_state": "unavailable",
        "command_line": ["fixture", "--argv"],
        "binary_sha256": "a" * 64,
        "input_sha256s": ["b" * 64],
        "thermal": "unavailable",
        "created": "2026-11-17T00:00:00+00:00",
    }
    record.update(extra)
    return record


def probe_record(part, input_type, k, rep, *, wall_nanos,
                 producer_nanos=1_000_000, busy_nanos=None, scale="full"):
    """An arm-C-shaped probe record with a stored probe JSON document."""
    workers = [{"batches": 1, "busy_nanos": busy_nanos if busy_nanos is not None
                else 2_000_000}]
    document = {
        "input": f"/tmp/{part}.fq",
        "threads": 16,
        "wall_nanos": wall_nanos,
        "producer_nanos": producer_nanos,
        "workers": workers,
    }
    # The committed k=21 probe emits NO k field; the materialized k=31 probe
    # must assert it (the per-instrument contract).
    if k != 21:
        document["k"] = k
    return run_record(
        "C", k, rep, part=part, input_type=input_type, scale=scale,
        probe_output_json=document,
        aggregate_worker_busy_nanos=sum(w["busy_nanos"] for w in workers))


class TestRotationSchedule(unittest.TestCase):
    """rotation_schedule gives a counterbalanced 3-round schedule over 5 arms."""

    def test_three_rounds_each_visit_every_gate_arm_once(self):
        """3 reps x 5 arms: every round holds every arm exactly once."""
        schedule = phase13.rotation_schedule(phase13.GATE_ARMS, 3)
        self.assertEqual(len(schedule), 3)
        for round_arms in schedule:
            self.assertEqual(sorted(round_arms),
                             sorted(phase13.GATE_ARMS))

    def test_each_round_starts_at_the_next_arm(self):
        """Round r starts at arm index r mod 5 — order bias rotates."""
        schedule = phase13.rotation_schedule(phase13.GATE_ARMS, 3)
        self.assertEqual(schedule[0][0], "A")
        self.assertEqual(schedule[1][0], "B")
        self.assertEqual(schedule[2][0], "C")

    def test_gate_arms_are_the_five_pinned_names(self):
        """The arm set is pinned: A, B, C, D, control."""
        self.assertEqual(phase13.GATE_ARMS, ("A", "B", "C", "D", "control"))


class TestEvidenceDocIO(unittest.TestCase):
    """new_doc / load_doc / upsert_run / write_doc lifecycle."""

    def test_new_doc_pins_kind_and_top_level_blocks(self):
        """new_doc carries its own kind, schema 1, and the pinned blocks."""
        doc = phase13.new_doc()
        self.assertEqual(doc["kind"], phase13.KIND)
        self.assertEqual(doc["kind"], "phase13-producer-attribution")
        self.assertEqual(doc["schema_version"], phase13.SCHEMA_VERSION)
        for key in ("runs", "prep", "fingerprint_gate", "attribution",
                    "predicted_win", "scratch_cleaned", "created"):
            self.assertIn(key, doc)

    def test_load_doc_returns_none_when_absent(self):
        """A missing evidence file loads as None (fresh session)."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(phase13.load_doc(Path(tmp) / "missing.json"))

    def test_load_doc_refuses_a_foreign_kind(self):
        """A document of another kind raises — never merge across kinds."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "foreign.json"
            path.write_text(json.dumps({
                "schema_version": 1, "kind": "merge-characterization-ladder"}),
                encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "refusing to merge"):
                phase13.load_doc(path)

    def test_load_doc_refuses_a_schema_mismatch(self):
        """A wrong schema_version raises with both values named."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doc.json"
            path.write_text(json.dumps({
                "schema_version": 99, "kind": phase13.KIND}),
                encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "schema_version"):
                phase13.load_doc(path)

    def test_write_doc_round_trips_sorted_indented(self):
        """write_doc emits indent=2, sorted keys, and a trailing newline."""
        doc = phase13.new_doc()
        doc["fingerprint_gate"] = phase13.fingerprint_gate(provenance_block())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "evidence.json"
            phase13.write_doc(path, doc)
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.endswith("\n"))
            self.assertEqual(json.loads(text)["kind"], phase13.KIND)
            self.assertEqual(phase13.load_doc(path)["kind"], phase13.KIND)

    def test_upsert_keeps_part_and_input_type_distinct(self):
        """Arm C holds 4 and arm D 2 records for one rep (full identity)."""
        doc = phase13.new_doc()
        for part in phase13.PINNED_PAIR:
            for input_type in ("gzip", "plain"):
                phase13.upsert_run(
                    doc, run_record("C", 21, 1, part=part,
                                    input_type=input_type))
        for part in phase13.PINNED_PAIR:
            phase13.upsert_run(
                doc, run_record("D", 21, 1, part=part, input_type="plain"))
        self.assertEqual(len(doc["runs"]), 6)
        self.assertEqual(
            len([r for r in doc["runs"] if r["arm"] == "C"]), 4)
        self.assertEqual(
            len([r for r in doc["runs"] if r["arm"] == "D"]), 2)

    def test_upsert_replaces_a_same_identity_record(self):
        """A same-identity rewrite replaces; the list does not grow."""
        doc = phase13.new_doc()
        phase13.upsert_run(
            doc, run_record("A", 21, 1, wall=1.0))
        phase13.upsert_run(
            doc, run_record("A", 21, 1, wall=9.0))
        self.assertEqual(len(doc["runs"]), 1)
        self.assertEqual(doc["runs"][0]["wall_s"], 9.0)


class TestFingerprintGate(unittest.TestCase):
    """The D-03/D-10 gate branches on exact sha256 equality."""

    def test_matching_sha_branches_cite(self):
        """Exactly v2.0's fingerprint -> cite, both hashes carried."""
        block = phase13.fingerprint_gate(provenance_block())
        self.assertEqual(block["branch"], "cite")
        self.assertEqual(block["current_sha256"],
                         phase13.V2_0_RUSTKMER_SHA256)
        self.assertEqual(block["v2_0_sha256"],
                         phase13.V2_0_RUSTKMER_SHA256)

    def test_differing_sha_branches_re_measure(self):
        """Any other sha -> re-measure, both hashes carried."""
        live = "4539b893e8ece53bf2faa417f94a4a64d3e3d6c89f1ff94db38c21fafd6d023b"
        block = phase13.fingerprint_gate(provenance_block(live))
        self.assertEqual(block["branch"], "re-measure")
        self.assertEqual(block["current_sha256"], live)
        self.assertEqual(block["v2_0_sha256"],
                         phase13.V2_0_RUSTKMER_SHA256)

    def test_missing_binary_block_raises(self):
        """A provenance block without binary sha256 cannot branch."""
        with self.assertRaisesRegex(ValueError, "binary"):
            phase13.fingerprint_gate({})
        with self.assertRaisesRegex(ValueError, "binary"):
            phase13.fingerprint_gate({"binary": {}})


class TestMeasuredRunFailLoud(unittest.TestCase):
    """measured_run is fail-loud: a non-zero child exit never measures."""

    def test_failing_child_raises_with_trailing_stderr(self):
        """A child exiting non-zero raises RuntimeError naming the argv."""
        with self.assertRaises(RuntimeError):
            phase13.measured_run(
                [sys.executable, "-c", "import sys; sys.exit(3)"])

    def test_successful_child_parses_wall_and_rss(self):
        """A successful child returns the units-pinned parse dict."""
        rep, _stderr = phase13.measured_run(["/bin/echo", "phase13"])
        self.assertIsInstance(rep["wall_s"], float)
        self.assertGreaterEqual(rep["wall_s"], 0.0)
        self.assertIsInstance(rep["peak_rss_bytes"], int)
        self.assertGreater(rep["peak_rss_bytes"], 0)


class TestPairSumMedian(unittest.TestCase):
    """_pair_sum_median: input-type subset, pair sum per rep, median over reps."""

    @staticmethod
    def arm_c_records():
        """Arm C both-type fixture: distinct gzip and plain wall values."""
        records = []
        gzip_values = {1: (10, 20), 2: (14, 26), 3: (12, 18)}
        plain_values = {1: (1, 2), 2: (3, 4), 3: (5, 6)}
        for rep, pair in gzip_values.items():
            for part, value in zip(phase13.PINNED_PAIR, pair):
                records.append(probe_record(
                    part, "gzip", 21, rep, wall_nanos=value * 1_000_000_000))
        for rep, pair in plain_values.items():
            for part, value in zip(phase13.PINNED_PAIR, pair):
                records.append(probe_record(
                    part, "plain", 21, rep, wall_nanos=value * 1_000_000_000,
                    producer_nanos=value * 2 * 1_000_000_000))
        return records

    def test_gzip_call_consumes_only_gzip_records(self):
        """The gzip subset sums per rep then medians: [30, 40, 30] -> 30."""
        result = phase13._pair_sum_median(
            self.arm_c_records(),
            lambda record: record["probe_output_json"]["wall_nanos"],
            21, "gzip")
        self.assertEqual(result["value_s"], 30.0)
        self.assertEqual(len(result["citations"]), 6)

    def test_plain_call_consumes_only_plain_records(self):
        """The plain subset is independent: sums [3, 7, 11] -> median 7."""
        result = phase13._pair_sum_median(
            self.arm_c_records(),
            lambda record: record["probe_output_json"]["wall_nanos"],
            21, "plain")
        self.assertEqual(result["value_s"], 7.0)

    def test_per_rep_values_are_pair_sums(self):
        """The reduction sums the two pinned parts BEFORE the median."""
        result = phase13._pair_sum_median(
            self.arm_c_records(),
            lambda record: record["probe_output_json"]["wall_nanos"],
            21, "gzip")
        self.assertEqual(result["per_rep_s"], {"1": 30.0, "2": 40.0,
                                               "3": 30.0})

    def test_missing_pinned_part_raises_naming_rep_and_input_type(self):
        """A rep missing a pinned part is a loud abort, never a thin sum."""
        records = [record for record in self.arm_c_records()
                   if not (record["rep"] == 2 and record["part"] == "part_006"
                           and record["input_type"] == "gzip")]
        with self.assertRaisesRegex(ValueError, r"rep 2.*gzip"):
            phase13._pair_sum_median(
                records,
                lambda record: record["probe_output_json"]["wall_nanos"],
                21, "gzip")

    def test_extra_part_in_subset_raises(self):
        """An extra part (a context-matrix part) cannot join the reduction."""
        records = self.arm_c_records() + [
            probe_record("part_002", "gzip", 21, 1, wall_nanos=5_000_000_000)]
        with self.assertRaisesRegex(ValueError, r"rep 1.*gzip"):
            phase13._pair_sum_median(
                records,
                lambda record: record["probe_output_json"]["wall_nanos"],
                21, "gzip")

    def test_empty_subset_raises(self):
        """No records for the named subset is a loud abort."""
        with self.assertRaisesRegex(ValueError, "no records"):
            phase13._pair_sum_median(
                self.arm_c_records(),
                lambda record: record["probe_output_json"]["wall_nanos"],
                31, "gzip")


if __name__ == "__main__":
    unittest.main()
