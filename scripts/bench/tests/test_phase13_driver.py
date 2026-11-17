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

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
                 producer_nanos=1_000_000, busy_nanos=None, scale="full",
                 arm="C", context=False):
    """A probe-shaped run record with a stored probe JSON document."""
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
        arm, k, rep, part=part, input_type=input_type, scale=scale,
        probe_output_json=document, context=context,
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


def _rep_dict(wall):
    """A minimal bench.parse_time_output-shaped rep dict."""
    return {"wall_s": wall, "peak_rss_bytes": 2048,
            "peak_footprint_bytes": 2048, "peak_bytes": 2048}


def _make_dataset(directory):
    """Six dataset-shaped gzip part NAMES (the stubs never read them)."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for index in range(1, 7):
        (directory / f"CRR1936095_r1.part_{index:03d}.fq.gz").write_text(
            f"gz{index}", encoding="utf-8")
    return directory


def _fixture_probes():
    """Materialize-seam return shape: two scratch probe crates."""
    return {
        "engine_probe_k31": {
            "binary": Path("/tmp/fixture-phase13-probe-k31"),
            "provenance": provenance_block("c" * 64)},
        "null_consumer": {
            "binary": Path("/tmp/fixture-phase13-null-consumer"),
            "provenance": provenance_block("d" * 64)},
    }


def _prep_args(tmp):
    """A run_prep args namespace over temp dataset/plain directories."""
    tmp = Path(tmp)
    return argparse.Namespace(
        results=str(tmp / "evidence.json"),
        rustkmer="/tmp/fixture-rustkmer",
        data_dir=str(_make_dataset(tmp / "data")),
        plain_dir=str(tmp / "plain"))


def _prep_seams(decompress_calls, *, dirty=False, free=10 ** 12, ensure=None):
    """run_prep seams: no cargo, no real decompression, no probe builds."""
    def decompress(gz_path, target_path):
        decompress_calls.append((str(gz_path), str(target_path)))
        Path(target_path).write_text(f"plain-{Path(gz_path).name}",
                                     encoding="utf-8")
        return ["gunzip", "-c", str(gz_path)]

    prov = provenance_block()
    if dirty:
        prov = dict(prov)
        prov["git_dirty"] = True

    def ensure_free(path, min_free_gb):
        if ensure is not None:
            ensure(path, min_free_gb)

    return {
        "provenance": lambda executable, profile: prov,
        "build": lambda argv, cwd=None, env=None: None,
        "free_bytes": lambda path: free,
        "ensure_free_space": ensure_free,
        "decompress": decompress,
        "materialize_probes": lambda scratch, repo_root: _fixture_probes(),
    }


def _measure_args(tmp):
    """A run_measure args namespace (only --results is consulted)."""
    return argparse.Namespace(results=str(Path(tmp) / "evidence.json"))


def _measure_ctx(tmp, *, cooldown=False, delete_calls=None, sleep_calls=None):
    """A full-scale measure context with every measurement seam stubbed.

    The stub numbers encode the pinned arithmetic fixture: median_A=150,
    median_B=120, reads 6/18 -> inflate 42; arm-C gzip wall pair-sum 130,
    producer-plain pair-sum 50, busy pair-sum 120; arm-D pair-sum 42 ->
    route_send 8, output_stage 20, predicted wall 75.25 -> 49.83% GO.
    """
    tmp = Path(tmp)
    delete_calls = delete_calls if delete_calls is not None else []
    sleep_calls = sleep_calls if sleep_calls is not None else []
    inputs = {}
    fingerprints = {}
    for part in phase13.EXPECTED_PARTS:
        inputs[part] = {
            "gzip": Path(f"/tmp/{part}.fq.gz"),
            "plain": Path(f"/tmp/{part}.fq"),
        }
        fingerprints[part] = {
            "gzip": {"path": str(inputs[part]["gzip"]), "size_bytes": 10,
                     "sha256": "e" * 64},
            "plain": {"path": str(inputs[part]["plain"]), "size_bytes": 20,
                      "sha256": "f" * 64},
        }

    def stats_stub(path, binary):
        Path(path).write_bytes(b"x" * 16)
        return {"unique_kmers": 100, "total_kmers": 1000}

    def run_measured(argv):
        is_gz = any(str(arg).endswith(".gz") for arg in argv)
        return _rep_dict(150.0 if is_gz else 120.0), ""

    def run_devnull(argv):
        is_gz = any(str(arg).endswith(".gz") for arg in argv)
        return _rep_dict(6.0 if is_gz else 18.0)

    def run_with_stdout(argv):
        name = Path(str(argv[0])).name
        is_gz = str(argv[1]).endswith(".gz")
        if name == "phase13-null-consumer":
            document = {"input": str(argv[1]), "k": int(argv[2]),
                        "records": 200, "windows": 10,
                        "wall_nanos": 21_000_000_000}
        elif name == "phase13-probe-k31":
            document = {
                "input": str(argv[1]), "k": int(argv[4]),
                "threads": int(argv[3]),
                "wall_nanos": (65 if is_gz else 60) * 10 ** 9,
                "producer_nanos": (30 if is_gz else 25) * 10 ** 9,
                "workers": [{"batches": 1,
                             "busy_nanos": (60 if is_gz else 50) * 10 ** 9}],
            }
        else:  # the committed k=21 probe: NO k field by design
            document = {
                "input": str(argv[1]), "threads": int(argv[3]),
                "wall_nanos": (65 if is_gz else 60) * 10 ** 9,
                "producer_nanos": (30 if is_gz else 25) * 10 ** 9,
                "workers": [{"batches": 1,
                             "busy_nanos": (60 if is_gz else 50) * 10 ** 9}],
            }
        return _rep_dict(0.5), json.dumps(document)

    ctx = phase13._build_ctx(
        scale="full", parts=phase13.PINNED_PAIR, inputs=inputs,
        input_fingerprints=fingerprints,
        stock_binary="/tmp/fixture-rustkmer",
        stock_provenance=provenance_block(),
        probe_binaries={
            "engine_probe_k21": Path("/tmp/engine_probe"),
            "engine_probe_k31": Path("/tmp/phase13-probe-k31"),
            "null_consumer": Path("/tmp/phase13-null-consumer"),
        },
        probe_provenance={
            "engine_probe_k21": provenance_block("1" * 64),
            "engine_probe_k31": provenance_block("2" * 64),
            "null_consumer": provenance_block("3" * 64),
        },
        out_dir=tmp / "out",
        context_parts=("part_002", "part_003", "part_004", "part_005"),
        cooldown=cooldown, run_measured=run_measured,
        run_devnull=run_devnull, run_with_stdout=run_with_stdout,
        stats_fn=stats_stub,
        cache_state=lambda: "unavailable", thermal=lambda: "unavailable",
        delete=lambda path: (delete_calls.append(str(path)),
                             phase13._unlink_quiet(path)),
        now=lambda: "2026-11-17T00:00:00+00:00",
        sleep=lambda seconds: sleep_calls.append(seconds))
    ctx["cat_sha256"] = "9" * 64
    return ctx


def _prepared_doc(tmp):
    """A doc carrying a valid provenance block and a truthy prep block."""
    doc = phase13.new_doc()
    doc["provenance"] = provenance_block()
    doc["fingerprint_gate"] = phase13.fingerprint_gate(doc["provenance"])
    doc["prep"] = {
        "disk_check_passed": True,
        "plain_inputs": [
            {"part": part, "path": f"/tmp/{part}.fq", "size_bytes": 1,
             "sha256": "a" * 64} for part in phase13.EXPECTED_PARTS],
    }
    path = Path(tmp) / "evidence.json"
    phase13.write_doc(path, doc)
    return path, doc


class TestRunPrepSeams(unittest.TestCase):
    """run_prep: clean-tree assertion, disk guard, streaming decompression."""

    def test_happy_path_records_the_pinned_prep_keys(self):
        """Prep stores disk_check_passed, probe_scratch_root, six plain
        inputs with sha256+size_bytes, and passes validate_provenance."""
        from scripts.bench.bench import validate_provenance
        with tempfile.TemporaryDirectory() as tmp:
            args = _prep_args(tmp)
            calls = []
            phase13.run_prep(args, seams=_prep_seams(calls))
            doc = phase13.load_doc(args.results)
            prep = doc["prep"]
            self.assertTrue(prep["disk_check_passed"])
            self.assertEqual(prep["probe_scratch_root"],
                             str(phase13.PROBE_SCRATCH_ROOT))
            self.assertEqual(len(prep["plain_inputs"]), 6)
            for entry in prep["plain_inputs"]:
                self.assertEqual(len(entry["sha256"]), 64)
                self.assertGreater(entry["size_bytes"], 0)
            self.assertEqual(len(prep["decompression_commands"]), 6)
            self.assertEqual(len(prep["gzip_inputs"]), 6)
            self.assertEqual(len(prep["probes"]), 3)
            self.assertIn("engine_probe_k31", prep["probes"])
            validate_provenance(doc)
            self.assertEqual(doc["fingerprint_gate"]["branch"], "cite")

    def test_dirty_tree_raises_naming_git_dirty(self):
        """A git_dirty=true provenance block aborts before the gate block."""
        with tempfile.TemporaryDirectory() as tmp:
            args = _prep_args(tmp)
            with self.assertRaisesRegex(RuntimeError, "git_dirty"):
                phase13.run_prep(
                    args, seams=_prep_seams([], dirty=True))

    def test_insufficient_disk_raises_before_decompression(self):
        """The disk guard fires before any decompression seam runs."""
        def ensure(path, min_free_gb):
            raise RuntimeError("disk guard: not enough free space")

        with tempfile.TemporaryDirectory() as tmp:
            args = _prep_args(tmp)
            calls = []
            with self.assertRaisesRegex(RuntimeError, "disk guard"):
                phase13.run_prep(
                    args, seams=_prep_seams(calls, ensure=ensure))
            self.assertEqual(calls, [])

    def test_idempotent_reentry_skips_matching_parts(self):
        """A pre-existing part with matching recorded size+sha is skipped."""
        with tempfile.TemporaryDirectory() as tmp:
            args = _prep_args(tmp)
            first_calls = []
            phase13.run_prep(args, seams=_prep_seams(first_calls))
            self.assertEqual(len(first_calls), 6)
            second_calls = []
            phase13.run_prep(args, seams=_prep_seams(second_calls))
            self.assertEqual(second_calls, [])

    def test_mismatched_plain_file_redecompresses_only_that_part(self):
        """A changed plain file is re-decompressed; the others are skipped."""
        with tempfile.TemporaryDirectory() as tmp:
            args = _prep_args(tmp)
            phase13.run_prep(args, seams=_prep_seams([]))
            target = phase13.plain_part_path("part_003", args.plain_dir)
            target.write_text("tampered", encoding="utf-8")
            second_calls = []
            phase13.run_prep(args, seams=_prep_seams(second_calls))
            self.assertEqual([Path(call[1]).resolve() for call in second_calls],
                             [Path(target).resolve()])

    def test_plain_part_path_follows_the_pinned_rule(self):
        """part_001 -> PLAIN_INPUTS_DIR/part_001.fq (D-07 filename rule)."""
        self.assertEqual(
            phase13.plain_part_path("part_001"),
            phase13.PLAIN_INPUTS_DIR / "part_001.fq")
        self.assertEqual(
            phase13.plain_part_path("part_004", "/tmp/plain"),
            Path("/tmp/plain/part_004.fq"))

    def test_decompression_uses_the_stdout_path_helper(self):
        """`_decompress_part` streams to a path, never through a capture."""
        recorded = {}

        def fake_run_fail_loud(argv, stdout_path=None, env=None,
                               side_label=""):
            recorded["argv"] = argv
            recorded["stdout_path"] = stdout_path
            Path(stdout_path).write_text("plain", encoding="utf-8")

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "part_001.fq"
            with mock.patch.object(phase13, "_run_fail_loud",
                                   fake_run_fail_loud):
                argv = phase13._decompress_part("/tmp/part_001.fq.gz", target)
            self.assertEqual(recorded["stdout_path"], str(target))
            self.assertEqual(argv[:2], ["gunzip", "-c"])
            self.assertEqual(argv[2], "/tmp/part_001.fq.gz")

    def test_doc_without_provenance_block_fails_validation(self):
        """new_doc + a real provenance fixture passes; removing it raises."""
        from scripts.bench.bench import validate_provenance
        doc = phase13.new_doc()
        doc["provenance"] = provenance_block()
        validate_provenance(doc)
        del doc["provenance"]
        with self.assertRaisesRegex(ValueError, "missing provenance block"):
            validate_provenance(doc)


class TestLockFixtures(unittest.TestCase):
    """The committed-lock gate and the profiling-feature manifest pin."""

    def test_mismatched_scratch_lock_raises(self):
        """A scratch lock differing from its fixture is a loud abort."""
        with tempfile.TemporaryDirectory() as tmp:
            crate = Path(tmp) / "crate"
            crate.mkdir()
            (crate / "Cargo.lock").write_text("scratch-bytes", encoding="utf-8")
            fixture = Path(tmp) / "fixture.Cargo.lock"
            fixture.write_text("committed-bytes", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "sha256"):
                phase13.verify_scratch_lockfile(crate, fixture)

    def test_missing_fixture_aborts_before_any_build_seam(self):
        """No fixture -> no build: `--locked` can never create a lock."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            fixtures = Path(tmp) / "fixtures"
            fixtures.mkdir()
            scratch = Path(tmp) / "scratch"
            scratch.mkdir()
            target = Path(tmp) / "target"
            build_calls = []
            with self.assertRaisesRegex(RuntimeError, "lock fixture missing"):
                phase13.materialize_probe_binaries(
                    scratch, repo_root=repo, fixtures_dir=fixtures,
                    build_fn=lambda crate: build_calls.append(crate),
                    target_dir=target)
            self.assertEqual(build_calls, [])

    def test_materialized_manifests_pin_the_profiling_feature(self):
        """The k=31 manifest enables profiling; the null consumer stays bare."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            fixtures = Path(tmp) / "fixtures"
            fixtures.mkdir()
            for spec in phase13.PROBE_CRATES.values():
                (fixtures / spec["lock_fixture"]).write_text(
                    "lock-" + spec["package"], encoding="utf-8")
            scratch = Path(tmp) / "scratch"
            scratch.mkdir()
            target = Path(tmp) / "target"
            build_calls = []

            def build_fn(crate_dir):
                build_calls.append(Path(crate_dir))
                package = Path(crate_dir).name
                spec = next(spec for spec in phase13.PROBE_CRATES.values()
                            if spec["package"] == package)
                (target / "release").mkdir(parents=True, exist_ok=True)
                (target / "release" / spec["binary"]).write_text(
                    "binary", encoding="utf-8")

            built = phase13.materialize_probe_binaries(
                scratch, repo_root=repo, fixtures_dir=fixtures,
                build_fn=build_fn, target_dir=target)
            self.assertEqual(len(built), 2)
            self.assertEqual(len(build_calls), 2)
            k31_manifest = (scratch / "phase13-probe-k31"
                            / "Cargo.toml").read_text(encoding="utf-8")
            self.assertIn('features = ["profiling"]', k31_manifest)
            null_manifest = (scratch / "phase13-null-consumer"
                             / "Cargo.toml").read_text(encoding="utf-8")
            self.assertNotIn("profiling", null_manifest)


class TestRunMeasureSeams(unittest.TestCase):
    """run_measure: record multiplicity, deletion seam, writes, exclusion."""

    def test_full_scale_record_counts_and_incremental_writes(self):
        """60 gate records + 16 context records; one write per record + final."""
        with tempfile.TemporaryDirectory() as tmp:
            results_path, _doc = _prepared_doc(tmp)
            ctx = _measure_ctx(tmp)
            writes = []
            real_write = phase13.write_doc

            def counting_write(path, document):
                writes.append(path)
                return real_write(path, document)

            with mock.patch.object(phase13, "write_doc", counting_write):
                rc = phase13.run_measure(
                    _measure_args(tmp), ctx_factory=lambda a, d: ctx)
            self.assertEqual(rc, phase13.EXIT_OK)
            doc = phase13.load_doc(results_path)
            gate = [r for r in doc["runs"] if not r.get("excluded")]
            context = [r for r in doc["runs"] if r.get("excluded")]
            self.assertEqual(len(gate), 60)
            self.assertEqual(len(context), 16)
            self.assertEqual(len(writes), 76 + 1)
            for k in phase13.GATE_KS:
                self.assertEqual(len([
                    r for r in gate if r["arm"] == "D" and r["k"] == k]), 6)
                self.assertEqual(len([
                    r for r in gate if r["arm"] == "C" and r["k"] == k]), 12)
                self.assertEqual(len([
                    r for r in context if r["k"] == k]), 8)
            self.assertEqual(doc["predicted_win"]["decision"], "GO")

    def test_delete_seam_fires_once_per_ab_rep(self):
        """D-08: every arm-A/B rep deletes its scratch output immediately."""
        with tempfile.TemporaryDirectory() as tmp:
            _prepared_doc(tmp)
            delete_calls = []
            ctx = _measure_ctx(tmp, delete_calls=delete_calls)
            phase13.run_measure(
                _measure_args(tmp), ctx_factory=lambda a, d: ctx)
            self.assertEqual(len(delete_calls), 12)
            self.assertTrue(all(path.endswith(".rkdb")
                                for path in delete_calls))

    def test_cooldown_sleep_seam_fires_per_arm_execution(self):
        """The cooldown seam is the injectable sleep, default
        time.sleep(DEFAULT_COOLDOWN_S) — 5 arms x 2 k x 3 reps."""
        with tempfile.TemporaryDirectory() as tmp:
            _prepared_doc(tmp)
            sleep_calls = []
            ctx = _measure_ctx(tmp, cooldown=True, sleep_calls=sleep_calls)
            phase13.run_measure(
                _measure_args(tmp), ctx_factory=lambda a, d: ctx)
            self.assertEqual(len(sleep_calls), 30)
            self.assertEqual(set(sleep_calls),
                             {phase13.DEFAULT_COOLDOWN_S})

    def test_context_records_are_excluded_and_gate_math_refuses_them(self):
        """Context records carry excluded=true and build_attribution raises."""
        with tempfile.TemporaryDirectory() as tmp:
            results_path, _doc = _prepared_doc(tmp)
            ctx = _measure_ctx(tmp)
            phase13.run_measure(
                _measure_args(tmp), ctx_factory=lambda a, d: ctx)
            doc = phase13.load_doc(results_path)
            context = [r for r in doc["runs"] if r.get("excluded")]
            self.assertTrue(context)
            self.assertTrue(all(r.get("context") for r in context))
            with self.assertRaisesRegex(ValueError, "context"):
                phase13.build_attribution(doc["runs"], 21)

    def test_driver_record_passes_reduce_arm(self):
        """A driver-built record reduces through bench.reduce_arm unchanged."""
        from scripts.bench.bench import reduce_arm
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _measure_ctx(tmp)
            record = phase13._pair_arm_records("A", 21, 1, ctx)[0]
            reduced = reduce_arm([record, dict(record, wall_s=160.0)])
            self.assertEqual(reduced["median_wall_s"], 155.0)
            self.assertEqual(reduced["median_peak_rss_bytes"], 2048)

    def test_fixture_scale_arm_d_has_two_records_per_k(self):
        """One rep over the pinned pair -> 2 arm-D records (6 at full scale)."""
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _measure_ctx(tmp)
            records = phase13._arm_d_records(21, 1, ctx)
            self.assertEqual(len(records), 2)
            self.assertEqual({r["part"] for r in records},
                             set(phase13.PINNED_PAIR))

    def test_measure_refuses_a_doc_without_provenance(self):
        """A doc failing validate_provenance never has math kept from it."""
        with tempfile.TemporaryDirectory() as tmp:
            path, doc = _prepared_doc(tmp)
            del doc["provenance"]
            phase13.write_doc(path, doc)
            with self.assertRaisesRegex(ValueError, "missing provenance block"):
                phase13.run_measure(
                    _measure_args(tmp), ctx_factory=lambda a, d: None)


class TestProbeParsing(unittest.TestCase):
    """Per-instrument probe parsing: k contract + zeroed-nanos guards."""

    COMMITTED_K21_JSON = json.dumps({
        "input": "/tmp/part_001.fq", "threads": 16, "wall_nanos": 1000,
        "producer_nanos": 900, "workers": [{"batches": 1, "busy_nanos": 50}]})

    MATERIALIZED_K31_JSON = json.dumps({
        "input": "/tmp/part_001.fq", "k": 31, "threads": 16,
        "wall_nanos": 1000, "producer_nanos": 900,
        "workers": [{"batches": 1, "busy_nanos": 50}]})

    NULL_CONSUMER_JSON = json.dumps({
        "input": "/tmp/part_001.fq", "k": 31, "records": 200,
        "windows": 10, "wall_nanos": 1000})

    def test_committed_k21_probe_parses_without_a_k_field(self):
        """The committed probe's JSON has no k field; identity supplies it."""
        document = phase13.parse_probe_output(
            self.COMMITTED_K21_JSON, 21, "engine_probe_k21")
        self.assertNotIn("k", document)

    def test_materialized_k31_probe_requires_its_k_field(self):
        """A materialized probe JSON missing k is a loud abort."""
        without_k = json.dumps({
            "input": "/tmp/part_001.fq", "threads": 16,
            "wall_nanos": 1000, "producer_nanos": 900,
            "workers": [{"batches": 1, "busy_nanos": 50}]})
        with self.assertRaisesRegex(ValueError, "no k field"):
            phase13.parse_probe_output(without_k, 31, "engine_probe_k31")
        self.assertEqual(
            phase13.parse_probe_output(
                self.MATERIALIZED_K31_JSON, 31, "engine_probe_k31")["k"], 31)

    def test_k_mismatch_aborts(self):
        """A k that differs from the arm k never attributes across k."""
        with self.assertRaisesRegex(ValueError, "refusing to attribute"):
            phase13.parse_probe_output(
                self.MATERIALIZED_K31_JSON, 21, "engine_probe_k31")
        with self.assertRaisesRegex(ValueError, "registry-declared"):
            phase13.parse_probe_output(
                self.COMMITTED_K21_JSON, 31, "engine_probe_k21")

    def test_zeroed_nanos_abort_every_instrument(self):
        """A zeroed wall/producer/busy total aborts (guard-zero class)."""
        zero_wall = json.dumps({
            "input": "/tmp/part_001.fq", "threads": 16, "wall_nanos": 0,
            "producer_nanos": 900,
            "workers": [{"batches": 1, "busy_nanos": 50}]})
        with self.assertRaisesRegex(ValueError, "wall_nanos"):
            phase13.parse_probe_output(zero_wall, 21, "engine_probe_k21")
        zero_busy = json.dumps({
            "input": "/tmp/part_001.fq", "k": 31, "threads": 16,
            "wall_nanos": 1000, "producer_nanos": 900,
            "workers": [{"batches": 1, "busy_nanos": 0}]})
        with self.assertRaisesRegex(ValueError, "busy_nanos"):
            phase13.parse_probe_output(zero_busy, 31, "engine_probe_k31")
        zero_records = json.dumps({
            "input": "/tmp/part_001.fq", "k": 21, "records": 0,
            "windows": 0, "wall_nanos": 1000})
        with self.assertRaisesRegex(ValueError, "records"):
            phase13.parse_probe_output(
                zero_records, 21, "null_consumer")

    def test_null_consumer_requires_its_k_field(self):
        """The null consumer is materialized: its JSON must carry k."""
        without_k = json.dumps({
            "input": "/tmp/part_001.fq", "records": 200, "windows": 10,
            "wall_nanos": 1000})
        with self.assertRaisesRegex(ValueError, "no k field"):
            phase13.parse_probe_output(without_k, 31, "null_consumer")
        self.assertEqual(
            phase13.parse_probe_output(
                self.NULL_CONSUMER_JSON, 31, "null_consumer")["k"], 31)


def _gate_fixture_doc():
    """A complete 3-rep full-scale GO fixture doc with all six part rows."""
    doc = phase13.new_doc()
    doc["provenance"] = provenance_block()
    doc["fingerprint_gate"] = phase13.fingerprint_gate(doc["provenance"])
    for k in phase13.GATE_KS:
        for rep in (1, 2, 3):
            phase13.upsert_run(doc, run_record("A", k, rep, wall=150.0))
            phase13.upsert_run(doc, run_record("B", k, rep, wall=120.0))
            phase13.upsert_run(doc, run_record(
                "control", k, rep, input_type="gzip", wall=6.0))
            phase13.upsert_run(doc, run_record(
                "control", k, rep, input_type="plain", wall=18.0))
            for part in phase13.PINNED_PAIR:
                phase13.upsert_run(doc, probe_record(
                    part, "gzip", k, rep, wall_nanos=65 * 10 ** 9,
                    producer_nanos=30 * 10 ** 9, busy_nanos=60 * 10 ** 9))
                phase13.upsert_run(doc, probe_record(
                    part, "plain", k, rep, wall_nanos=60 * 10 ** 9,
                    producer_nanos=25 * 10 ** 9, busy_nanos=50 * 10 ** 9))
                phase13.upsert_run(doc, probe_record(
                    part, "plain", k, rep, wall_nanos=21 * 10 ** 9, arm="D"))
    for part in ("part_002", "part_003", "part_004", "part_005"):
        for input_type in ("gzip", "plain"):
            phase13.upsert_run(doc, probe_record(
                part, input_type, 21, 1, wall_nanos=60 * 10 ** 9,
                context=True))
    phase13.compute_gate_blocks(doc)
    return doc


class TestRunMemoSeams(unittest.TestCase):
    """run_memo: refusals, deterministic render, both decisions exit 0."""

    def _write_doc(self, tmp, doc):
        path = Path(tmp) / "13-ATTRIBUTION.json"
        phase13.write_doc(path, doc)
        return path

    def _args(self, tmp, path):
        return argparse.Namespace(
            results=str(path),
            out=str(Path(tmp) / "13-GATE-MEMO.md"),
            proof_out=str(Path(tmp) / "13-RENDER-PROOF.json"))

    def test_go_fixture_renders_and_exits_zero(self):
        """A complete GO fixture publishes a memo + proof at exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            doc = _gate_fixture_doc()
            self.assertEqual(doc["predicted_win"]["decision"], "GO")
            path = self._write_doc(tmp, doc)
            args = self._args(tmp, path)
            self.assertEqual(phase13.run_memo(args), phase13.EXIT_OK)
            memo = Path(args.out).read_text(encoding="utf-8")
            proof = json.loads(Path(args.proof_out).read_text(encoding="utf-8"))
            self.assertTrue(proof["byte_identical"])
            self.assertEqual(proof["decision"], "GO")
            self.assertIn("DECISION: GO", memo)
            for token in ("Phase-14 sizing context", "probe-vs-CLI topology",
                          "part_001", "part_006", "165.05", "178.22",
                          phase13.V2_0_PYTHON_MODULE_SHA256, "context only",
                          "binary-fingerprint caveat"):
                self.assertIn(token, memo)

    def test_no_go_fixture_also_exits_zero(self):
        """A recorded NO-GO is a valid result: exit 0 + revisit conditions."""
        with tempfile.TemporaryDirectory() as tmp:
            doc = _gate_fixture_doc()
            doc["predicted_win"]["decision"] = "NO-GO"
            doc["predicted_win"]["per_k_improvement_pct"] = {
                "21": 9.0, "31": 9.0}
            path = self._write_doc(tmp, doc)
            args = self._args(tmp, path)
            self.assertEqual(phase13.run_memo(args), phase13.EXIT_OK)
            memo = Path(args.out).read_text(encoding="utf-8")
            self.assertIn("DECISION: NO-GO", memo)
            self.assertIn("Revisit conditions", memo)
            self.assertNotIn("Phase-14 sizing context", memo)

    def test_double_render_is_byte_identical(self):
        """Two invocations of the renderer return identical text."""
        doc = _gate_fixture_doc()
        self.assertEqual(phase13.render_memo_text(doc),
                         phase13.render_memo_text(doc))

    def test_missing_blocks_exit_two(self):
        """A doc without attribution/predicted_win never renders (exit 2)."""
        with tempfile.TemporaryDirectory() as tmp:
            doc = phase13.new_doc()
            doc["provenance"] = provenance_block()
            path = self._write_doc(tmp, doc)
            args = self._args(tmp, path)
            with self.assertRaises(SystemExit) as raised:
                phase13.main(["--stage", "memo", "--results", str(path),
                              "--out", args.out,
                              "--proof-out", args.proof_out])
            self.assertEqual(raised.exception.code, 2)

    def test_non_full_record_refused_naming_scale(self):
        """A rehearsal record cited by the memo is refused loudly."""
        with tempfile.TemporaryDirectory() as tmp:
            doc = _gate_fixture_doc()
            doc["runs"][0]["scale"] = "rehearsal"
            path = self._write_doc(tmp, doc)
            with self.assertRaisesRegex(ValueError, "rehearsal"):
                phase13.run_memo(self._args(tmp, path))

    def test_incomplete_matrix_refused_naming_arm_and_k(self):
        """A 2-rep arm-k is refused with the arm and k named."""
        with tempfile.TemporaryDirectory() as tmp:
            doc = _gate_fixture_doc()
            doc["runs"] = [record for record in doc["runs"]
                           if not (record["arm"] == "D" and record["k"] == 31
                                   and record["rep"] == 3)]
            path = self._write_doc(tmp, doc)
            with self.assertRaisesRegex(ValueError, r"arm D k=31"):
                phase13.run_memo(self._args(tmp, path))

    def test_missing_provenance_field_refused(self):
        """A gate record missing a required field is refused by name."""
        with tempfile.TemporaryDirectory() as tmp:
            doc = _gate_fixture_doc()
            doc["runs"][0].pop("cache_state")
            path = self._write_doc(tmp, doc)
            with self.assertRaisesRegex(ValueError, "cache_state"):
                phase13.run_memo(self._args(tmp, path))


def _attribution_runs(*, median_a=150.0, median_b=120.0, read_gz=6.0,
                      read_plain=18.0, arm_c_gzip=65.0,
                      arm_c_plain_producer=25.0, arm_c_busy=60.0,
                      arm_d=21.0, k=21, reps=(1, 2, 3)):
    """A complete per-k run set for the attribution/model fixtures.

    Each probe value is per PART; the pair sum doubles it. Defaults encode:
    inflate 42, count-phase 130, producer-plain 50, busy 120, arm-D 42,
    route_send 8, output_stage 20.
    """
    runs = []
    for rep in reps:
        runs.append(run_record("A", k, rep, wall=median_a))
        runs.append(run_record("B", k, rep, wall=median_b))
        runs.append(run_record("control", k, rep, input_type="gzip",
                               wall=read_gz))
        runs.append(run_record("control", k, rep, input_type="plain",
                               wall=read_plain))
        for part in phase13.PINNED_PAIR:
            runs.append(probe_record(
                part, "gzip", k, rep, wall_nanos=arm_c_gzip * 10 ** 9,
                producer_nanos=30 * 10 ** 9,
                busy_nanos=arm_c_busy * 10 ** 9))
            runs.append(probe_record(
                part, "plain", k, rep, wall_nanos=60 * 10 ** 9,
                producer_nanos=arm_c_plain_producer * 10 ** 9,
                busy_nanos=50 * 10 ** 9))
            runs.append(probe_record(
                part, "plain", k, rep, wall_nanos=arm_d * 10 ** 9, arm="D"))
    return runs


class TestBuildAttribution(unittest.TestCase):
    """D-09 arithmetic: delta correction, unclamped sign, residuals, split."""

    def test_delta_correction_adds_back_the_read_delta(self):
        """inflate = (A-B) - (read_gz - read_plain) = 30 + 12 = 42."""
        block = phase13.build_attribution(_attribution_runs(), 21)
        self.assertEqual(block["raw_a_minus_b_s"], 30.0)
        self.assertEqual(block["delta_correction_s"], -12.0)
        self.assertEqual(block["inflate_s"], 42.0)
        self.assertEqual(block["parse_extract_s"], 42.0)
        self.assertEqual(block["route_send_s"], 8.0)
        self.assertEqual(block["output_stage_s"], 20.0)
        self.assertEqual(block["count_phase_wall_probe_s"], 130.0)
        self.assertEqual(block["producer_plain_probe_s"], 50.0)
        self.assertEqual(block["worker_busy_total_s"], 120.0)

    def test_correction_works_in_the_other_direction(self):
        """Plain reads faster than gz -> the correction SUBTRACTS 12."""
        runs = _attribution_runs(read_gz=18.0, read_plain=6.0)
        block = phase13.build_attribution(runs, 21)
        self.assertEqual(block["delta_correction_s"], 12.0)
        self.assertEqual(block["inflate_s"], 18.0)

    def test_negative_corrected_share_is_unclamped(self):
        """A negative corrected share is recorded exactly as measured."""
        runs = _attribution_runs(read_gz=60.0, read_plain=0.0)
        block = phase13.build_attribution(runs, 21)
        self.assertEqual(block["delta_correction_s"], 60.0)
        self.assertEqual(block["inflate_s"], -30.0)
        self.assertEqual(block["raw_a_minus_b_s"], 30.0)

    def test_stage_residuals_and_composition_split_are_exact(self):
        """route_send = producer_plain - parse_extract; output = median_A -
        count_phase_wall; both through the input-type-scoped reduction."""
        runs = _attribution_runs(arm_c_plain_producer=33.0, arm_d=11.0,
                                 arm_c_gzip=61.5)
        block = phase13.build_attribution(runs, 21)
        self.assertEqual(block["producer_plain_probe_s"], 66.0)
        self.assertEqual(block["parse_extract_s"], 22.0)
        self.assertEqual(block["route_send_s"], 44.0)
        self.assertEqual(block["count_phase_wall_probe_s"], 123.0)
        self.assertEqual(block["output_stage_s"], 27.0)

    def test_missing_arm_d_records_raise_naming_the_arm(self):
        """No null-consumer runs -> a loud refusal naming the missing arm."""
        runs = [record for record in _attribution_runs() if record["arm"] != "D"]
        with self.assertRaisesRegex(ValueError, "arm-D"):
            phase13.build_attribution(runs, 21)

    def test_missing_control_plain_records_raise(self):
        """A missing control row would leave the correction uncited."""
        runs = [record for record in _attribution_runs()
                if not (record["arm"] == "control"
                        and record["input_type"] == "plain")]
        with self.assertRaisesRegex(ValueError, "control plain"):
            phase13.build_attribution(runs, 21)

    def test_every_value_carries_a_citation(self):
        """Each attribution value names its source records."""
        block = phase13.build_attribution(_attribution_runs(), 21)
        for key in ("inflate_s", "parse_extract_s", "route_send_s",
                    "output_stage_s", "raw_a_minus_b_s",
                    "delta_correction_s", "count_phase_wall_probe_s",
                    "producer_plain_probe_s", "worker_busy_total_s"):
            self.assertTrue(block["citations"][key], msg=key)


class TestBuildPredictedWin(unittest.TestCase):
    """PEXT-02 model completeness: both ceilings, composition, citations."""

    @staticmethod
    def block():
        runs = _attribution_runs()
        attribution = phase13.build_attribution(runs, 21)
        return phase13.build_predicted_win(attribution, 21, runs)

    def test_serial_terms_and_derived_floors(self):
        """serial=50; derated floor=55.25; idealized=52.625; worker=7.5."""
        block = self.block()
        self.assertEqual(block["serial_terms_s"], 50.0)
        self.assertAlmostEqual(block["parallelizable_floor_derated_s"], 55.25)
        self.assertAlmostEqual(
            block["parallelizable_floor_idealized_s"], 52.625)
        self.assertAlmostEqual(block["worker_floor_s"], 7.5)

    def test_composition_is_max_of_floors_plus_output_stage(self):
        """predicted_full_wall = max(floors) + output_stage = 75.25."""
        block = self.block()
        self.assertAlmostEqual(block["predicted_full_wall_s"], 75.25)
        self.assertAlmostEqual(block["predicted_improvement_pct"], 49.8333333,
                               places=5)
        self.assertEqual(block["worker_scaling_ceiling"], 16)
        self.assertEqual(block["extractor_count"], 16)
        self.assertEqual(block["mode"], "point")

    def test_anomaly_ratios_are_recorded(self):
        """probe_vs_cli and worker_busy ratios are model outputs."""
        block = self.block()
        self.assertAlmostEqual(block["probe_vs_cli_ratio"], 130.0 / 150.0)
        self.assertAlmostEqual(block["worker_busy_ratio"],
                               120.0 / (16 * 130.0))

    def test_every_floor_fields_citation_is_named(self):
        """Each model input carries its source record keys."""
        block = self.block()
        for key in ("parse_extract_s", "worker_busy_total_s", "route_send_s",
                    "output_stage_s", "arm_a_median_s"):
            self.assertTrue(block["citations"][key], msg=key)

    def test_missing_input_raises_naming_it(self):
        """An unresolved attribution input is a loud refusal, never a 0."""
        runs = _attribution_runs()
        attribution = phase13.build_attribution(runs, 21)
        attribution.pop("worker_busy_total_s")
        with self.assertRaisesRegex(ValueError, "worker_busy_total_s"):
            phase13.build_predicted_win(attribution, 21, runs)

    def test_missing_arm_a_median_raises(self):
        """Without arm-A records or a recorded median the model refuses."""
        runs = _attribution_runs()  # k=21 only
        attribution = phase13.build_attribution(runs, 21)
        attribution.pop("arm_a_median_s", None)
        with self.assertRaisesRegex(ValueError, "arm_a_median_s"):
            phase13.build_predicted_win(attribution, 31, runs)


class TestAnomalyBoundsMode(unittest.TestCase):
    """A3/A4: anomaly criteria drive mode='bounds' with a conservative end."""

    def test_probe_ratio_outside_band_bounds(self):
        """count-phase probe outside (0.25, 1.0] of median_A -> bounds."""
        runs = _attribution_runs(arm_c_gzip=100.0)  # pair sum 200 / 150
        attribution = phase13.build_attribution(runs, 21)
        block = phase13.build_predicted_win(attribution, 21, runs)
        self.assertEqual(block["mode"], "bounds")
        self.assertGreater(block["probe_vs_cli_ratio"], 1.0)

    def test_worker_busy_ratio_over_max_bounds(self):
        """Worker busy over the pinned max -> bounds."""
        runs = _attribution_runs(arm_c_busy=1300.0)  # pair sum 2600
        attribution = phase13.build_attribution(runs, 21)
        block = phase13.build_predicted_win(attribution, 21, runs)
        self.assertEqual(block["mode"], "bounds")
        self.assertGreater(block["worker_busy_ratio"], 1.0)

    def test_zero_busy_total_bounds_with_interval_and_assumptions(self):
        """A non-positive worker busy total -> bounds + assumptions list."""
        runs = _attribution_runs()
        attribution = phase13.build_attribution(runs, 21)
        attribution["worker_busy_total_s"] = 0.0
        block = phase13.build_predicted_win(attribution, 21, runs)
        self.assertEqual(block["mode"], "bounds")
        self.assertTrue(block["what_would_need_to_be_true"])
        walls = block["bounds"]["predicted_full_wall_s"]
        pcts = block["bounds"]["predicted_improvement_pct"]
        self.assertLessEqual(walls["upper_s"], walls["lower_s"])
        self.assertGreaterEqual(pcts["upper_pct"], pcts["lower_pct"])
        self.assertAlmostEqual(block["predicted_full_wall_s"],
                               walls["lower_s"])
        self.assertAlmostEqual(block["predicted_improvement_pct"],
                               pcts["lower_pct"])

    def test_bounds_conservative_end_drives_the_decision(self):
        """A bounds fixture at 9.99 conservative is NO-GO though its upper
        bound clears the bar."""
        by_k = {
            "21": {"predicted_improvement_pct": 9.99,
                   "bounds": {"predicted_improvement_pct": {
                       "lower_pct": 9.99, "upper_pct": 15.0}}},
            "31": {"predicted_improvement_pct": 12.0},
        }
        decision = phase13.derive_gate_decision(by_k)
        self.assertEqual(decision["decision"], "NO-GO")
        self.assertTrue(decision["conservative_bound_used"])


class TestDeriveGateDecision(unittest.TestCase):
    """D-05: >= bar, both-k conjunction, derated input only."""

    def test_exactly_the_bar_at_both_k_is_go(self):
        """>= semantics: 10.0 at both k is GO."""
        decision = phase13.derive_gate_decision({
            "21": {"predicted_improvement_pct": 10.0},
            "31": {"predicted_improvement_pct": 10.0}})
        self.assertEqual(decision["decision"], "GO")
        self.assertEqual(decision["bar_pct"], 10.0)
        self.assertTrue(decision["conservative_bound_used"])

    def test_either_k_below_the_bar_is_no_go(self):
        """Conjunction: 9.99 at one k is NO-GO even if the other clears."""
        decision = phase13.derive_gate_decision({
            "21": {"predicted_improvement_pct": 10.0},
            "31": {"predicted_improvement_pct": 9.99}})
        self.assertEqual(decision["decision"], "NO-GO")

    def test_idealized_only_clearance_is_no_go(self):
        """The idealized E=M bound never participates in the bar test."""
        decision = phase13.derive_gate_decision({
            "21": {"predicted_improvement_pct": 5.0,
                   "idealized_predicted_improvement_pct": 20.0},
            "31": {"predicted_improvement_pct": 5.0,
                   "idealized_predicted_improvement_pct": 20.0}})
        self.assertEqual(decision["decision"], "NO-GO")

    def test_missing_k_raises_not_silently_no_go(self):
        """The bar applies at both k: a missing k is a loud refusal."""
        with self.assertRaisesRegex(ValueError, "no predicted-win block"):
            phase13.derive_gate_decision({
                "21": {"predicted_improvement_pct": 20.0}})

    def test_python_context_never_feeds_the_decision(self):
        """D-06: the Python walls are context and never a bar input."""
        cleared = phase13.derive_gate_decision({
            "21": {"predicted_improvement_pct": 20.0,
                   "python_wall_s": phase13.V2_0_PYTHON_WALL_K21_S},
            "31": {"predicted_improvement_pct": 20.0,
                   "python_wall_s": phase13.V2_0_PYTHON_WALL_K31_S}})
        below = phase13.derive_gate_decision({
            "21": {"predicted_improvement_pct": 5.0,
                   "python_wall_s": phase13.V2_0_PYTHON_WALL_K21_S},
            "31": {"predicted_improvement_pct": 5.0,
                   "python_wall_s": phase13.V2_0_PYTHON_WALL_K31_S}})
        self.assertEqual(cleared["decision"], "GO")
        self.assertEqual(below["decision"], "NO-GO")


class TestControlArmArgv(unittest.TestCase):
    """The pure-read control reads BOTH pinned-pair parts per invocation."""

    def test_one_argv_per_input_type_with_both_parts(self):
        """Each control argv is list-form `cat` over the two pinned parts."""
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _measure_ctx(tmp)
            seen = []
            ctx["run_devnull"] = lambda argv: (
                seen.append(list(argv)), _rep_dict(6.0))[1]
            records = phase13._control_records(21, 1, ctx)
            self.assertEqual(len(seen), 2)
            self.assertEqual(len(records), 2)
            gzip_argv, plain_argv = seen
            self.assertEqual(gzip_argv[0], "cat")
            self.assertIn(str(ctx["inputs"]["part_001"]["gzip"]), gzip_argv)
            self.assertIn(str(ctx["inputs"]["part_006"]["gzip"]), gzip_argv)
            self.assertEqual(len(gzip_argv), 3)
            self.assertIn(str(ctx["inputs"]["part_001"]["plain"]), plain_argv)
            self.assertIn(str(ctx["inputs"]["part_006"]["plain"]), plain_argv)
            self.assertEqual({record["input_type"] for record in records},
                             {"gzip", "plain"})


class TestMemoBranches(unittest.TestCase):
    """render_memo_text: section contract, decision flip, bounds branch."""

    def test_render_carries_every_pinned_section(self):
        """Decision line, both ceilings, stage table, fresh base, gate
        provenance, bar statement, and the D-06 block are all present."""
        memo = phase13.render_memo_text(_gate_fixture_doc())
        for token in ("DECISION: GO", "Pre-registered D-05 bar",
                      "PARALLELIZABLE CEILING", "WORKER-SIDE CEILING",
                      "Stage attribution", "k=21", "k=31",
                      "Fresh base", "D-03/D-10 gate provenance",
                      "Python-surface context (D-06)", "165.05", "178.22",
                      phase13.V2_0_PYTHON_MODULE_SHA256, "context only",
                      "binary-fingerprint caveat", "Lifecycle / deletion"):
            self.assertIn(token, memo)

    def test_flipping_the_decision_changes_the_text(self):
        """GO and NO-GO renders differ on the decision line and branches."""
        go_doc = _gate_fixture_doc()
        no_go_doc = _gate_fixture_doc()
        no_go_doc["predicted_win"]["decision"] = "NO-GO"
        go_text = phase13.render_memo_text(go_doc)
        no_go_text = phase13.render_memo_text(no_go_doc)
        self.assertNotEqual(go_text, no_go_text)
        self.assertIn("DECISION: GO", go_text)
        self.assertIn("DECISION: NO-GO", no_go_text)

    def test_bounds_mode_renders_the_interval_and_assumptions(self):
        """A bounds model replaces point shares with the interval + list."""
        doc = _gate_fixture_doc()
        doc["predicted_win"]["decision"] = "NO-GO"
        block = doc["predicted_win"]["per_k"]["21"]
        block["mode"] = "bounds"
        block["bounds"] = {
            "predicted_full_wall_s": {"lower_s": 90.0, "upper_s": 70.0},
            "predicted_improvement_pct": {"lower_pct": 40.0,
                                          "upper_pct": 53.3333},
        }
        block["what_would_need_to_be_true"] = [
            "the probe topology must match the CLI pair-run"]
        memo = phase13.render_memo_text(doc)
        self.assertIn("BOUNDS MODE", memo)
        self.assertIn("What would need to be true", memo)
        self.assertIn("40.0000", memo)

    def test_go_memo_lists_all_six_parts(self):
        """The GO per-part block names every dataset part token."""
        memo = phase13.render_memo_text(_gate_fixture_doc())
        self.assertIn("Phase-14 sizing context", memo)
        self.assertIn("probe-vs-CLI topology", memo)
        for part in phase13.EXPECTED_PARTS:
            self.assertIn(part, memo)


class TestPreRegisteredConstants(unittest.TestCase):
    """D-05/A3/A4 constants are load-bearing and asserted, never drifted."""

    def test_bar_and_model_constants(self):
        """Bar 10.0, 16 extractors, E=0.5, ceiling == 16, band, busy max."""
        self.assertEqual(phase13.D3_BAR_FULL_WALL_IMPROVEMENT_PCT, 10.0)
        self.assertEqual(phase13.EXTRACTOR_COUNT, 16)
        self.assertEqual(phase13.EXTRACTOR_EFFICIENCY_DERATED, 0.5)
        self.assertEqual(phase13.WORKER_SCALING_CEILING,
                         phase13.EXTRACTOR_COUNT)
        self.assertEqual(phase13.PROBE_VS_CLI_RATIO_BAND, (0.25, 1.0))
        self.assertEqual(phase13.WORKER_BUSY_RATIO_MAX, 1.0)

    def test_gate_shape_constants(self):
        """Both k, 3 reps, the pinned pair, and the phase kind."""
        self.assertEqual(phase13.GATE_KS, (21, 31))
        self.assertEqual(phase13.GATE_REPS, 3)
        self.assertEqual(phase13.PINNED_PAIR, ("part_001", "part_006"))
        self.assertEqual(phase13.KIND, "phase13-producer-attribution")
        self.assertEqual(phase13.V2_0_RUSTKMER_SHA256,
                         "8f38d20c2e3dc77dfc0ef80c9a2475613da1aa7ad131bd240"
                         "d5ec74fc87c3d23")


if __name__ == "__main__":
    unittest.main()
