#!/usr/bin/env python3
"""Unit suite for the Phase-10 verdict controller (scripts/bench/phase10.py).

Hand-built constants, no filesystem beyond tempdir, no binaries invoked: the
controller's measured-round seams (`measure_fn`, `purge_fn`, `sleep_fn`) and
the interpreter query are injected, so this suite proves the arm/rotation/
verdict/document contract without a real `/usr/bin/time` run.

The load-bearing rules encoded here:
  * every arm carries BOTH split parts (one measured arm, never two);
  * every round visits every arm once with a rotated start;
  * the verdict filters `threads == 16`, equality is match-or-beat, and the
    `t1` arm never enters a YES/NO computation;
  * missing/ambiguous/zero-rep/non-positive-median arms are invalid, and an
    invalid document never reaches disk.

Stdlib unittest only — no pytest.
"""

import contextlib
import copy
import hashlib
import inspect
import io
import json
import shutil
import statistics
import tempfile
import unittest
from pathlib import Path
from unittest import mock

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.bench import phase10 as p10
from scripts.bench import python_bench as pb
from scripts.bench.bench import validate_provenance

PART_1 = "/data/part_001.fq.gz"
PART_2 = "/data/part_006.fq.gz"


def fake_provenance():
    """A structurally valid provenance block (validate_provenance-clean)."""
    return {
        "binary": {"path": "/repo/target/release/rustkmer", "size_bytes": 1234,
                   "sha256": "a" * 64},
        "git_commit": "b" * 40,
        "git_dirty": False,
        "build_profile": "release",
        "rust_toolchain": "rustc 1.82.0 (fake)",
        "platform": "darwin-arm64",
        "created": "2026-11-13T00:00:00+00:00",
    }


def make_rep(wall=1.0, peak_rss=1000, peak_bytes=None, cache_state="unavailable",
             round_index=0, arm_order=0):
    rep = {"wall_s": wall, "peak_rss_bytes": peak_rss,
           "cache_state": cache_state, "round": round_index,
           "arm_order": arm_order}
    if peak_bytes is not None:
        rep["peak_bytes"] = peak_bytes
    return rep


def make_arm(name, tool, threads, wall, peak=1000, reps=None, unique=100,
             total=200):
    reps = reps if reps is not None else [make_rep(wall=wall,
                                                   peak_rss=peak)]
    return {
        "name": name,
        "tool": tool,
        "threads": threads,
        "inputs": [PART_1, PART_2],
        "reps": reps,
        "medians": {"wall_s": wall, "peak_rss_bytes": peak,
                    "peak_bytes": peak, "cv_wall_pct": None,
                    "cv_warning": False},
        "unique_kmers": unique,
        "total_kmers": total,
        "db_sha256": None,
    }


def make_doc(arms, k=21, session="cli", mode="full"):
    doc = {
        "schema_version": p10.SCHEMA_VERSION,
        "mode": mode,
        "phase": 10,
        "session": session,
        "params": {"k": k, "canonical": True, "threads": 16, "reps": 3,
                   "cooldown_s": 5, "hash_size": "10G",
                   "arm_order": list(p10.ARM_ORDER)},
        "platform": {"system": "Darwin", "release": "25.6.0",
                     "machine": "arm64", "python": "3.13.11"},
        "created": "2026-11-13T00:00:00+00:00",
        "input_fingerprint": [
            {"path": PART_1, "size_bytes": 10, "sha256": "c" * 64},
            {"path": PART_2, "size_bytes": 11, "sha256": "d" * 64},
        ],
        "arms": arms,
        "schedule": {"policy": "round-robin-rotation",
                     "warmup_order": list(p10.TOOL_WARMUP_ORDER),
                     "rounds": []},
        "provenance": fake_provenance(),
    }
    if session == "python":
        doc["provenance"]["module"] = {
            "path": "/venv/lib/python3.13/site-packages/pyrustkmer.so",
            "size_bytes": 1234,
            "sha256": "f" * 64,
        }
        doc["provenance"]["python_executable"] = "/venv/bin/python"
        doc["provenance"]["python_version"] = "3.13.11"
        doc["provenance"]["maturin_version"] = "maturin 1.11.5"
    return doc


def cli_doc(rk_wall=100.0, jf_wall=100.0, t1_wall=5000.0, k=21):
    return make_doc([
        make_arm(p10.ARM_RK_T16, "rustkmer", 16, rk_wall),
        make_arm(p10.ARM_RK_T1, "rustkmer", 1, t1_wall),
        make_arm(p10.ARM_JF_T16, "jellyfish", 16, jf_wall),
    ], k=k, session="cli")


def python_doc(py_wall=100.0, jf_wall=100.0, k=21):
    return make_doc([
        make_arm(p10.ARM_JF_T16, "jellyfish", 16, jf_wall),
        make_arm(p10.ARM_PY_T16, "pyrustkmer", 16, py_wall),
    ], k=k, session="python")


class TestArmConstruction(unittest.TestCase):
    """One spec per requested arm; every command carries BOTH parts."""

    def _specs(self, include=p10.ARM_ORDER):
        self.info = mock.patch.object(
            p10.python_bench, "interpreter_info",
            return_value={
                "site_prefix": "/venv/lib/python3.13/site-packages",
                "executable": "/venv/bin/python",
                "version": "3.13.11"})
        self.info_mock = self.info.start()
        self.addCleanup(self.info.stop)
        return p10.build_arm_specs(
            [PART_1, PART_2], 21, "target/release/rustkmer",
            "/venv/bin/python", "/tmp/p10scratch", include)

    def test_one_spec_per_requested_arm(self):
        """The four pinned arms appear once each with their thread config."""
        specs = self._specs()
        self.assertEqual([s["name"] for s in specs], list(p10.ARM_ORDER))
        by_name = {s["name"]: s for s in specs}
        self.assertEqual(by_name[p10.ARM_RK_T16]["threads"], 16)
        self.assertEqual(by_name[p10.ARM_RK_T1]["threads"], 1)
        self.assertEqual(by_name[p10.ARM_JF_T16]["threads"], 16)
        self.assertEqual(by_name[p10.ARM_PY_T16]["threads"], 16)
        for spec in specs:
            self.assertEqual(spec["inputs"], [PART_1, PART_2])
            self.assertTrue(str(spec["out"]).startswith("/tmp/p10scratch"))
            self.assertIsInstance(spec["cmd"], list)

    def test_every_command_carries_both_parts(self):
        """rustkmer gets one -i with both files; jellyfish one pipeline; py two
        --inputs flags — the both-parts seam on every tool."""
        by_name = {s["name"]: s for s in self._specs()}

        for name in (p10.ARM_RK_T16, p10.ARM_RK_T1):
            cmd = by_name[name]["cmd"]
            self.assertEqual(cmd[cmd.index("-i") + 1:], [PART_1, PART_2],
                             f"{name} must pass both parts through one -i")

        jf_cmd = by_name[p10.ARM_JF_T16]["cmd"]
        self.assertEqual(jf_cmd[:2], ["sh", "-c"])
        self.assertIn(PART_1, jf_cmd[2])
        self.assertIn(PART_2, jf_cmd[2])

        py_cmd = by_name[p10.ARM_PY_T16]["cmd"]
        self.assertEqual(py_cmd.count("--inputs"), 2)
        first = py_cmd.index("--inputs")
        self.assertEqual(py_cmd[first + 1], PART_1)
        second = py_cmd.index("--inputs", first + 1)
        self.assertEqual(py_cmd[second + 1], PART_2)
        self.assertEqual(py_cmd[py_cmd.index("--stats-out") + 1],
                         by_name[p10.ARM_PY_T16]["stats_path"])

    def test_py_spec_carries_site_prefix_from_one_interpreter_query(self):
        """The py spec carries the interpreter's site_prefix; queried once."""
        by_name = {s["name"]: s for s in self._specs()}
        self.assertTrue(by_name[p10.ARM_PY_T16]["site_prefix"])
        self.info_mock.assert_called_once_with("/venv/bin/python")

    def test_unknown_arm_rejected(self):
        with self.assertRaises(ValueError):
            self._specs(include=("rk-t16", "nope"))

    def test_exactly_two_parts_required(self):
        with self.assertRaises(ValueError):
            p10.build_arm_specs([PART_1], 21, "rustkmer", "/venv/bin/python",
                                "/tmp/p10scratch", (p10.ARM_RK_T16,))


class RoundsFixture(unittest.TestCase):
    """Shared fake-measure fixture for the run_rounds contract."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        site = self.tmp / "site"
        site.mkdir()
        self.module = site / "pyrustkmer.cpython-313-darwin.so"
        self.module.write_bytes(b"\x7fELF-phase10-fake")
        self.site_prefix = str(site)
        patcher = mock.patch.object(
            p10.python_bench, "interpreter_info",
            return_value={"site_prefix": self.site_prefix,
                          "executable": str(self.tmp / "python"),
                          "version": "3.13.11"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.specs = p10.build_arm_specs(
            [PART_1, PART_2], 21, "target/release/rustkmer",
            str(self.tmp / "python"), self.tmp, p10.ARM_ORDER)
        self.by_name = {s["name"]: s for s in self.specs}
        self.calls = []

    def fake_measure(self, argv):
        self.calls.append([str(part) for part in argv])
        if "--stats-out" in argv:
            stats_path = Path(argv[argv.index("--stats-out") + 1])
            requested = int(argv[argv.index("--threads") + 1])
            payload = {
                "total_kmers": 200,
                "unique_kmers": 100,
                "threads_resolved": requested,
                "module_path": str(self.module),
                "module_mtime": 1.0,
                "python_version": "3.13.11",
                "inputs": [PART_1, PART_2],
            }
            stats_path.write_text(json.dumps(payload), encoding="utf-8")
        index = len(self.calls)
        return {"wall_s": float(index), "peak_rss_bytes": 1000 + index}

    def run_with_fakes(self, reps=3, measure_fn=None):
        sleeps = []
        reps_by_arm = p10.run_rounds(
            self.specs, reps, 5,
            measure_fn=measure_fn or self.fake_measure,
            purge_fn=lambda: "unavailable",
            sleep_fn=sleeps.append)
        return reps_by_arm, sleeps


class TestRunRounds(RoundsFixture):
    """Warmups, rotation, per-rep honest fields, and the py stats seam."""

    def test_one_warmup_per_tool_before_round_zero(self):
        """Exactly one discarded warmup per tool, in tool order."""
        reps_by_arm, _ = self.run_with_fakes()
        self.assertEqual(len(self.calls), 3 + 3 * 4)
        self.assertEqual(self.calls[0], self.by_name[p10.ARM_RK_T16]["cmd"])
        self.assertEqual(self.calls[1], self.by_name[p10.ARM_JF_T16]["cmd"])
        self.assertEqual(self.calls[2], self.by_name[p10.ARM_PY_T16]["cmd"])
        for reps in reps_by_arm.values():
            self.assertEqual(len(reps), 3)

    def test_each_round_visits_every_arm_once_with_rotated_start(self):
        """Round r starts at index r mod 4 and covers every arm once."""
        reps_by_arm, _ = self.run_with_fakes()
        expected_rounds = p10.rotation_schedule(list(p10.ARM_ORDER), 3)
        for rnd, expected in enumerate(expected_rounds):
            start = 3 + rnd * len(self.specs)
            observed = self.calls[start:start + len(self.specs)]
            self.assertEqual(
                observed, [self.by_name[name]["cmd"] for name in expected])
            for position, name in enumerate(expected):
                rep = reps_by_arm[name][rnd]
                self.assertEqual(rep["round"], rnd)
                self.assertEqual(rep["arm_order"], position)
                self.assertEqual(rep["cache_state"], "unavailable")

    def test_reps_record_normalized_peak_and_cooldown(self):
        """peak_bytes derives from RSS when the parser had no peak_bytes."""
        reps_by_arm, sleeps = self.run_with_fakes()
        for name, reps in reps_by_arm.items():
            for rep in reps:
                self.assertEqual(rep["peak_bytes"], rep["peak_rss_bytes"],
                                 f"{name} fallback peak")
                self.assertIsNone(rep["peak_footprint_bytes"])
        # 15 measured invocations -> 14 cooldown gaps of 5 s.
        self.assertEqual(sleeps, [5] * 14)

    def test_py_reps_carry_validated_identity(self):
        """The py reps carry exact counts and the measured module sha."""
        reps_by_arm, _ = self.run_with_fakes()
        expected_sha = hashlib.sha256(self.module.read_bytes()).hexdigest()
        for rep in reps_by_arm[p10.ARM_PY_T16]:
            self.assertEqual(rep["total_kmers"], 200)
            self.assertEqual(rep["unique_kmers"], 100)
            self.assertEqual(rep["module_path"], str(self.module))
            self.assertEqual(rep["module_sha256"], expected_sha)
            self.assertEqual(rep["threads_resolved"], 16)

    def test_py_branch_validates_with_the_spec_site_prefix(self):
        """validate_worker_stats receives the spec's site_prefix, not 'info'."""
        original = p10.python_bench.validate_worker_stats
        with mock.patch.object(p10.python_bench, "validate_worker_stats",
                               wraps=original) as validator:
            self.run_with_fakes()
        self.assertEqual(validator.call_count, 4)  # 1 warmup + 3 reps
        for call in validator.call_args_list:
            self.assertEqual(call.args[1], self.site_prefix)

    def test_missing_py_stats_file_is_invalid(self):
        """A py run leaving no stats file raises — counts are never made up."""

        def losing_measure(argv):
            self.calls.append([str(part) for part in argv])
            index = len(self.calls)
            return {"wall_s": float(index), "peak_rss_bytes": 1000 + index}

        with self.assertRaises(ValueError):
            self.run_with_fakes(measure_fn=losing_measure)

    def test_zero_reps_rejected(self):
        with self.assertRaises(ValueError):
            self.run_with_fakes(reps=0)


class TestSurfaceResult(unittest.TestCase):
    """The acceptance rule is `<=`; equality is a match with no tolerance."""

    def test_truth_table(self):
        cases = [
            (10.0, 20.0, "YES"),
            (20.0, 10.0, "NO"),
            (10.0, 10.0, "YES"),      # equality is match-or-beat
            (0.5, 0.5, "YES"),
            (100.0, 99.999, "NO"),    # any excess is a NO, no noise band
        ]
        for tool, jellyfish, expected in cases:
            self.assertEqual(p10.surface_result(tool, jellyfish), expected,
                             f"{tool} vs {jellyfish}")


class TestVerdictBlock(unittest.TestCase):
    """t16 filtering, t1 exclusion, and every invalid-input path."""

    def test_equality_is_match_or_beat(self):
        block = p10.verdict_block(21, cli_doc(100.0, 100.0),
                                  python_doc(100.0, 100.0))
        self.assertEqual(block["result"], "YES")
        self.assertEqual(block["rustkmer_result"], "YES")
        self.assertEqual(block["python_result"], "YES")

    def test_python_only_loss_is_overall_no(self):
        block = p10.verdict_block(21, cli_doc(90.0, 100.0),
                                  python_doc(120.0, 100.0))
        self.assertEqual(block["rustkmer_result"], "YES")
        self.assertEqual(block["python_result"], "NO")
        self.assertEqual(block["result"], "NO")

    def test_t1_arm_never_enters_the_verdict(self):
        """A slow t1 arm is scaling evidence only — it cannot manufacture NO."""
        block = p10.verdict_block(21, cli_doc(100.0, 100.0, t1_wall=9999.0),
                                  python_doc(100.0, 100.0))
        self.assertEqual(block["result"], "YES")
        self.assertEqual(block["scaling"]["arm"], p10.ARM_RK_T1)
        self.assertEqual(block["scaling"]["wall_s"], 9999.0)

    def test_missing_arm_is_invalid(self):
        cli = cli_doc()
        cli["arms"] = [a for a in cli["arms"] if a["name"] != p10.ARM_JF_T16]
        with self.assertRaises(ValueError):
            p10.verdict_block(21, cli, python_doc())

    def test_zero_rep_arm_is_invalid(self):
        cli = cli_doc()
        for arm in cli["arms"]:
            if arm["name"] == p10.ARM_RK_T16:
                arm["reps"] = []
        with self.assertRaises(ValueError):
            p10.verdict_block(21, cli, python_doc())

    def test_non_positive_median_is_invalid(self):
        cli = cli_doc()
        for arm in cli["arms"]:
            if arm["name"] == p10.ARM_RK_T16:
                arm["medians"]["wall_s"] = 0.0
        with self.assertRaises(ValueError):
            p10.verdict_block(21, cli, python_doc())

    def test_ambiguous_arm_is_invalid(self):
        cli = cli_doc()
        cli["arms"].append(make_arm(p10.ARM_RK_T16, "rustkmer", 16, 50.0))
        with self.assertRaises(ValueError):
            p10.verdict_block(21, cli, python_doc())

    def test_mismatched_k_is_invalid(self):
        with self.assertRaises(ValueError):
            p10.verdict_block(31, cli_doc(k=21), python_doc(k=21))


class TestRepPeakBytes(unittest.TestCase):
    """peak_bytes prefers the recorded value, else max(rss, footprint-or-0)."""

    def test_recorded_peak_bytes_wins(self):
        self.assertEqual(
            p10.rep_peak_bytes({"peak_bytes": 42, "peak_rss_bytes": 10,
                                "peak_footprint_bytes": 5}), 42)

    def test_footprint_can_exceed_rss(self):
        self.assertEqual(
            p10.rep_peak_bytes({"peak_rss_bytes": 10,
                                "peak_footprint_bytes": 20}), 20)

    def test_absent_footprint_falls_back_to_rss(self):
        self.assertEqual(p10.rep_peak_bytes({"peak_rss_bytes": 10}), 10)
        self.assertEqual(
            p10.rep_peak_bytes({"peak_rss_bytes": 10,
                                "peak_footprint_bytes": None}), 10)


class TestWriteDoc(unittest.TestCase):
    """An invalid document must never reach disk."""

    def test_invalid_document_is_refused(self):
        doc = make_doc([make_arm(p10.ARM_RK_T16, "rustkmer", 16, 1.0)])
        doc["arms"] = []  # validate_schema requires a non-empty arms list
        out = Path(tempfile.mkdtemp()) / "out.json"
        self.addCleanup(shutil.rmtree, str(out.parent), True)
        with self.assertRaises(ValueError):
            p10.write_doc(doc, out)
        self.assertFalse(out.exists())

    def test_missing_provenance_is_refused(self):
        doc = make_doc([make_arm(p10.ARM_RK_T16, "rustkmer", 16, 1.0)])
        del doc["provenance"]
        out = Path(tempfile.mkdtemp()) / "out.json"
        self.addCleanup(shutil.rmtree, str(out.parent), True)
        with self.assertRaises(ValueError):
            p10.write_doc(doc, out)
        self.assertFalse(out.exists())

    def test_valid_document_round_trips(self):
        doc = make_doc([make_arm(p10.ARM_RK_T16, "rustkmer", 16, 1.0)])
        out = Path(tempfile.mkdtemp()) / "out.json"
        self.addCleanup(shutil.rmtree, str(out.parent), True)
        p10.write_doc(doc, out)
        self.assertEqual(json.loads(out.read_text(encoding="utf-8")), doc)


class TestMemoryModel(unittest.TestCase):
    """The capacity-cliff CLI model and the conservative Python projection.

    The CLI model is validated against three measured RSS points; the Python
    projection is the measured 86 B/distinct single-call coefficient quoted
    as the conservative two-call upper bound; the budget gate is inclusive at
    equality and blocks one byte over.
    """

    MEASURED_POINTS = (
        (229_694_874, 12.04e9),   # Phase 8 head-4M
        (256_606_202, 17.52e9),   # 5M random slice
        (537_770_176, 35.71e9),   # 20M random probe
    )

    def test_cli_model_reproduces_measured_points_within_five_percent(self):
        for distinct, measured in self.MEASURED_POINTS:
            projected = p10.cli_peak_bytes(distinct)
            deviation = abs(projected - measured) / measured
            self.assertLess(
                deviation, 0.05,
                f"distinct={distinct}: projected {projected} vs measured "
                f"{measured} ({deviation:.2%})")

    def test_python_projection_is_exactly_the_measured_coefficient(self):
        self.assertEqual(p10.python_projection_bytes(1_050_000_000),
                         86 * 1_050_000_000)
        self.assertEqual(p10.PYTHON_BYTES_PER_DISTINCT, 86)

    def test_memory_gate_equality_passes_and_one_byte_over_blocks(self):
        budget = 110 * (1 << 30)
        ok, detail = p10.memory_gate(budget, budget)
        self.assertTrue(ok, "equality must pass")
        self.assertIn("headroom", detail)
        ok, detail = p10.memory_gate(budget + 1, budget)
        self.assertFalse(ok, "one byte over must be blocked")
        self.assertIn("deficit", detail)

    def test_preflight_record_derives_the_decision(self):
        """No caller can supply the projection or the decision."""
        params = inspect.signature(p10.preflight_record).parameters
        self.assertNotIn("projected_bytes", params)
        self.assertNotIn("decision", params)

        allowed = p10.preflight_record(21, 1_050_000_000, "cli-k21.json",
                                       "e" * 64)
        self.assertEqual(allowed["decision"], "PROCEED")
        self.assertEqual(allowed["projected_bytes"],
                         p10.python_projection_bytes(1_050_000_000))
        self.assertEqual(allowed["budget_bytes"], p10.MEMORY_BUDGET_BYTES)
        self.assertGreaterEqual(allowed["headroom_bytes"], 0)

        blocked = p10.preflight_record(21, 2_000_000_000, "cli-k21.json",
                                       "e" * 64)
        self.assertEqual(blocked["decision"], "BLOCKED")
        self.assertLess(blocked["headroom_bytes"], 0)


class TestPreflightStage(unittest.TestCase):
    """The preflight-python stage reads CLI docs and writes its decision."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp), True)

    def _cli_docs(self, distinct_by_k):
        paths = []
        for k, distinct in distinct_by_k.items():
            doc = make_doc([make_arm(p10.ARM_RK_T16, "rustkmer", 16, 100.0,
                                     unique=distinct, total=distinct * 2)],
                           k=k, session="cli", mode="full")
            path = self.tmp / f"cli-k{k}.json"
            path.write_text(json.dumps(doc), encoding="utf-8")
            paths.append(str(path))
        return paths

    def _run(self, docs, out):
        with mock.patch.object(p10, "binary_provenance",
                               return_value=fake_provenance()):
            return p10.main(["--stage", "preflight-python",
                             "--cli-docs", *docs, "--out", str(out)])

    def test_proceed_writes_both_k_records_and_returns_zero(self):
        docs = self._cli_docs({21: 1_050_000_000, 31: 1_200_000_000})
        out = self.tmp / "preflight.json"
        self.assertEqual(self._run(docs, out), p10.EXIT_OK)
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(doc["kind"], "phase10-python-preflight")
        self.assertEqual(doc["overall"], "PROCEED")
        self.assertEqual({r["k"] for r in doc["records"]}, {21, 31})
        for record in doc["records"]:
            self.assertEqual(len(record["distinct_source_sha256"]), 64)
            self.assertEqual(record["decision"], "PROCEED")

    def test_blocked_projection_still_writes_the_record_and_returns_2(self):
        docs = self._cli_docs({21: 2_000_000_000, 31: 2_000_000_000})
        out = self.tmp / "preflight.json"
        self.assertEqual(self._run(docs, out), p10.EXIT_INVALID)
        doc = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(doc["overall"], "BLOCKED")
        self.assertEqual({r["k"] for r in doc["records"]}, {21, 31})
        for record in doc["records"]:
            self.assertEqual(record["decision"], "BLOCKED")


class TestReport(unittest.TestCase):
    """The Phase-10 renderer: deterministic, literal-bearing, order-pinned.

    The report is a pure function of the result documents (the only
    environment read is the harness source commit), every mandatory statement
    is literal text asserted here, and invalid input raises instead of
    rendering an empty table.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp), True)

    def render(self, docs, name="report.md"):
        out = self.tmp / name
        p10.render_report([copy.deepcopy(doc) for doc in docs], out)
        return out.read_text(encoding="utf-8")

    def section(self, text, header):
        start = text.index(header)
        rest = text[start + len(header):]
        end = rest.index("\n## ") if "\n## " in rest else len(rest)
        return rest[:end]

    def full_docs(self, k=21):
        return [cli_doc(k=k), python_doc(k=k)]

    def full_k_docs(self):
        """One cli + one python document for EACH pinned k value."""
        return [cli_doc(k=21), cli_doc(k=31),
                python_doc(k=21), python_doc(k=31)]

    def test_re_render_is_byte_identical(self):
        docs = self.full_docs()
        first = self.render(docs, "a.md")
        second = self.render(docs, "b.md")
        self.assertEqual(first, second)

    def test_editing_one_recorded_median_changes_that_number(self):
        docs = copy.deepcopy(self.full_docs())
        before = self.render(docs, "a.md")
        for arm in docs[0]["arms"]:
            if arm["name"] == p10.ARM_RK_T16:
                arm["medians"]["wall_s"] = 123.456
        after = self.render(docs, "b.md")
        self.assertNotEqual(before, after)
        self.assertIn("123.456", after)
        self.assertNotIn("123.456", before)

    def test_five_pinned_literals_are_present(self):
        report = self.render(self.full_docs())
        for literal in ("BENCH-V2-01", "partially satisfied",
                        "Dev-host evidence only", "scaling evidence"):
            self.assertIn(literal, report)
        self.assertIn("equality", report.lower())

    def test_arm_order_is_pinned_independent_of_json_order(self):
        docs = self.full_docs()
        docs[0]["arms"].reverse()
        docs[1]["arms"].reverse()
        report = self.render(docs)
        cli_table = self.section(report, "### CLI session")
        positions = [cli_table.index(f"| {name} |")
                     for name in (p10.ARM_RK_T16, p10.ARM_RK_T1,
                                  p10.ARM_JF_T16)]
        self.assertEqual(positions, sorted(positions))

    def test_even_rep_median_is_the_mean_of_the_two_middle_values(self):
        self.assertEqual(
            p10.arm_medians([{"wall_s": 10.0, "peak_rss_bytes": 1000},
                             {"wall_s": 20.0, "peak_rss_bytes": 1000}])
            ["wall_s"], 15.0)
        docs = self.full_docs()
        for arm in docs[0]["arms"]:
            if arm["name"] == p10.ARM_RK_T16:
                arm["reps"] = [
                    make_rep(wall=10.0, round_index=0),
                    make_rep(wall=20.0, round_index=1),
                ]
                arm["medians"]["wall_s"] = statistics.median([10.0, 20.0])
        report = self.render(docs)
        row = next(line for line in report.splitlines()
                   if line.startswith(f"| {p10.ARM_RK_T16} |"))
        self.assertIn("| 15.0 |", row)
        self.assertIn("10.0 / 20.0", row)

    def test_each_arm_row_carries_rep_walls_and_large_counts(self):
        docs = self.full_docs()
        for arm in docs[0]["arms"]:
            if arm["name"] == p10.ARM_RK_T16:
                arm["medians"]["peak_bytes"] = 1 << 30
        report = self.render(docs)
        cli_table = self.section(report, "### CLI session")
        row = next(line for line in cli_table.splitlines()
                   if line.startswith(f"| {p10.ARM_RK_T16} |"))
        self.assertIn("100", row)
        self.assertIn("200", row)
        self.assertIn("| 1.00 |", row)  # one GiB peak rendered in GiB

    def test_scaling_evidence_line_excludes_t1(self):
        report = self.render(self.full_docs())
        cli_table = self.section(report, "### CLI session")
        self.assertIn("Scaling evidence (excluded from the verdict)", cli_table)

    def test_cv_warning_marker_is_rendered(self):
        docs = self.full_docs()
        docs[0]["arms"][0]["medians"]["cv_warning"] = True
        report = self.render(docs)
        self.assertIn("[cv_warning]", report)

    def test_report_names_both_binary_sha256_values(self):
        report = self.render(self.full_docs())
        self.assertIn("a" * 64, report)   # CLI binary sha256
        self.assertIn("f" * 64, report)   # Python module sha256

    def test_missing_arm_raises(self):
        docs = self.full_docs()
        docs[0]["arms"] = [arm for arm in docs[0]["arms"]
                           if arm["name"] != p10.ARM_RK_T16]
        with self.assertRaises(ValueError):
            self.render(docs)

    def test_missing_document_raises(self):
        with self.assertRaises(ValueError):
            self.render([cli_doc()])

    def test_zero_rep_arm_raises(self):
        docs = self.full_docs()
        docs[0]["arms"][0]["reps"] = []
        with self.assertRaises(ValueError):
            self.render(docs)

    def test_unsupported_document_kind_raises(self):
        docs = self.full_docs()
        docs[0]["kind"] = "phase10-python-preflight"
        with self.assertRaises(ValueError):
            self.render(docs)

    def test_missing_provenance_raises(self):
        docs = self.full_docs()
        del docs[0]["provenance"]
        with self.assertRaises(ValueError):
            self.render(docs)

    def test_parity_mismatch_raises(self):
        docs = self.full_docs()
        for arm in docs[1]["arms"]:
            if arm["name"] == p10.ARM_PY_T16:
                arm["unique_kmers"] = 101
        with self.assertRaises(ValueError):
            self.render(docs)

    # --- the render stage: atomic publish and exit codes --------------------

    def write_docs(self, docs):
        paths = []
        for index, doc in enumerate(docs):
            path = self.tmp / f"doc{index}.json"
            path.write_text(json.dumps(doc), encoding="utf-8")
            paths.append(str(path))
        return paths

    def run_render(self, docs, extra_patches=None):
        paths = self.write_docs(docs)
        verdict_out = self.tmp / "10-verdict.json"
        report_out = self.tmp / "10-BENCHMARK-REPORT.md"
        argv = ["--stage", "render", "--docs", *paths,
                "--verdict-out", str(verdict_out),
                "--out", str(report_out),
                "--rustkmer", "/repo/target/release/rustkmer"]
        patches = [mock.patch.object(
            p10, "binary_provenance",
            side_effect=lambda *_args, **_kwargs: fake_provenance())]
        patches += list(extra_patches or [])
        out, err = io.StringIO(), io.StringIO()
        with contextlib.ExitStack() as stack:
            for patch in patches:
                stack.enter_context(patch)
            stack.enter_context(contextlib.redirect_stdout(out))
            stack.enter_context(contextlib.redirect_stderr(err))
            try:
                code = p10.main(argv)
            except SystemExit as exc:
                code = exc.code
        return code, verdict_out, report_out, out.getvalue(), err.getvalue()

    def test_render_stage_publishes_both_artifacts_on_yes(self):
        code, verdict_out, report_out, _out, err = self.run_render(
            self.full_k_docs())
        self.assertEqual(code, p10.EXIT_OK, err)
        verdict = json.loads(verdict_out.read_text(encoding="utf-8"))
        self.assertEqual(verdict["kind"], "phase10-verdict")
        self.assertEqual(verdict["overall"], "YES")
        self.assertEqual(verdict["descoped"]["requirement"], "BENCH-V2-01")
        self.assertFalse(verdict["kmc3_executed"])
        self.assertFalse(verdict["ci_baseline_written"])
        self.assertTrue(verdict["dev_host_only"])
        self.assertEqual(len(verdict["inputs"]), 4)
        self.assertEqual({block["k"] for block in verdict["verdicts"]},
                         {21, 31})
        report = report_out.read_text(encoding="utf-8")
        self.assertIn("BENCH-V2-01", report)

    def test_render_rejects_a_subset_of_the_pinned_k_values(self):
        """A k=21-only document set can never publish an overall verdict."""
        code, verdict_out, report_out, _out, err = self.run_render(
            self.full_docs(k=21))
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertIn("pinned k values", err)
        self.assertFalse(verdict_out.exists())
        self.assertFalse(report_out.exists())

    def test_render_stage_keeps_artifacts_on_no(self):
        docs = self.full_k_docs()
        for doc in docs:
            if doc["session"] != "python":
                continue
            for arm in doc["arms"]:
                if arm["name"] == p10.ARM_PY_T16:
                    for rep in arm["reps"]:
                        rep["wall_s"] = 999.0
                    arm["medians"]["wall_s"] = 999.0
        code, verdict_out, report_out, _out, err = self.run_render(docs)
        self.assertEqual(code, p10.EXIT_NO, err)
        self.assertTrue(verdict_out.exists())
        self.assertTrue(report_out.exists())
        verdict = json.loads(verdict_out.read_text(encoding="utf-8"))
        self.assertEqual(verdict["overall"], "NO")

    def test_injected_render_failure_leaves_neither_destination(self):
        def boom(_docs):
            raise ValueError("injected render failure")

        code, verdict_out, report_out, _out, err = self.run_render(
            self.full_k_docs(), [mock.patch.object(p10, "render_report_text",
                                                   side_effect=boom)])
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertIn("injected render failure", err)
        self.assertFalse(verdict_out.exists())
        self.assertFalse(report_out.exists())

    def test_invalid_document_leaves_neither_destination(self):
        docs = self.full_k_docs()
        del docs[0]["provenance"]
        code, verdict_out, report_out, _out, _err = self.run_render(docs)
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertFalse(verdict_out.exists())
        self.assertFalse(report_out.exists())


class TestSliceGateRecord(unittest.TestCase):
    """The slice-gate stage pins the reference and labels k=31 honestly."""

    REAL_PART_1 = "CRR1936095_r1.part_001.fq.gz"
    REAL_PART_2 = "CRR1936095_r1.part_006.fq.gz"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.out = self.tmp / "10-slice-gate.json"
        self.gate_calls = []

    def make_data(self, names=(None, None)):
        data = self.tmp / "data"
        data.mkdir()
        for name in names:
            if name:
                (data / name).write_bytes(b"part-bytes")
        return data

    def make_fingerprint(self, reference_sha=p10.REFERENCE_SHA256):
        def fake_fingerprint(path):
            resolved = Path(path)
            if resolved == p10.PARITY_REFERENCE:
                return {"path": str(resolved), "size_bytes": 123,
                        "sha256": reference_sha}
            return {
                "path": str(resolved),
                "size_bytes": resolved.stat().st_size,
                "sha256": hashlib.sha256(str(resolved).encode()).hexdigest(),
            }
        return fake_fingerprint

    def run_stage(self, data, reference_sha=p10.REFERENCE_SHA256,
                  parity_side_effect=None):
        def fake_provision(resolved_inputs, slice_reads, scratch):
            slice_path = Path(scratch) / "slice-0.fq"
            slice_path.write_bytes(b"slice-bytes")
            return [slice_path, slice_path]

        def fake_run_parity(slice_path, k, threads, rustkmer, scratch,
                            hash_size=None):
            if parity_side_effect is not None:
                return parity_side_effect(k)
            return {"distinct": 1000 + k, "total": 2000 + k}

        def fake_gate(counts, path, source_sha256, slice_kind, reads, k,
                      canonical, selection=None):
            self.gate_calls.append({"counts": counts, "path": path,
                                    "source_sha256": source_sha256,
                                    "slice_kind": slice_kind, "reads": reads,
                                    "k": k, "canonical": canonical})
            return {"expected": {"distinct": counts["distinct"],
                                 "total": counts["total"]}}

        patches = [
            mock.patch.object(p10, "provision_slice",
                              side_effect=fake_provision),
            mock.patch.object(p10, "run_parity",
                              side_effect=fake_run_parity),
            mock.patch.object(p10, "gate_parity_reference",
                              side_effect=fake_gate),
            mock.patch.object(p10, "fingerprint",
                              side_effect=self.make_fingerprint(reference_sha)),
            mock.patch.object(p10, "binary_provenance",
                              side_effect=lambda *_a, **_k: fake_provenance()),
        ]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.ExitStack() as stack:
            for patch in patches:
                stack.enter_context(patch)
            stack.enter_context(contextlib.redirect_stdout(out))
            stack.enter_context(contextlib.redirect_stderr(err))
            try:
                code = p10.main(["--stage", "slice-gate",
                                 "--data-dir", str(data),
                                 "--out", str(self.out),
                                 "--scratch", str(self.tmp / "scratch"),
                                 "--rustkmer",
                                 "/repo/target/release/rustkmer"])
            except SystemExit as exc:
                code = exc.code
        return code, err.getvalue()

    def test_record_carries_both_k_gates_and_pins_the_reference(self):
        data = self.make_data((self.REAL_PART_1, self.REAL_PART_2))
        code, err = self.run_stage(data)
        self.assertEqual(code, p10.EXIT_OK, err)
        doc = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertEqual(doc["kind"], "phase10-slice-gate")
        self.assertEqual(doc["phase"], 10)
        validate_provenance(doc)
        gates = {gate["k"]: gate for gate in doc["gates"]}
        self.assertEqual(set(gates), {21, 31})
        reference = gates[21]["parity_reference"]
        self.assertIsNotNone(reference)
        self.assertEqual(reference["path"],
                         "scripts/bench/baselines/slice_parity.crr1936095.json")
        self.assertEqual(reference["sha256"], p10.REFERENCE_SHA256)
        self.assertEqual(gates[21]["reference_gate"], p10.PINNED_REFERENCE_GATE)
        self.assertIsNone(gates[31]["parity_reference"])
        self.assertEqual(gates[31]["reference_gate"], p10.LIVE_PARITY_ONLY)
        for k, gate in gates.items():
            self.assertEqual(gate["slice_recipe"]["k"], k)
            self.assertEqual(gate["slice_recipe"]["slice_selection"], "head")
            self.assertEqual(gate["slice_recipe"]["slice_reads"],
                             p10.PINNED_SLICE_READS)
            self.assertEqual(gate["slice_recipe"]["hash_size"],
                             p10.PARITY_HASH_SIZE)
            self.assertEqual(gate["slice_recipe"]["source_sha256"],
                             doc["input_fingerprint"][0]["sha256"])
            self.assertEqual(gate["distinct"], 1000 + k)
            self.assertEqual(gate["total"], 2000 + k)
        self.assertEqual(len(doc["input_fingerprint"]), 2)
        # The k=21 gate is bound to the SOURCE part, not the slice.
        self.assertEqual(len(self.gate_calls), 1)
        call = self.gate_calls[0]
        self.assertEqual(call["k"], 21)
        self.assertEqual(call["reads"], p10.PINNED_SLICE_READS)
        self.assertEqual(call["slice_kind"],
                         p10.slice_kind_for("head", p10.PINNED_SLICE_READS))

    def test_compression_suffix_is_stripped_before_the_token_match(self):
        self.assertEqual(
            p10.strip_compression_suffix("CRR1936095_r1.part_001.fq.gz"),
            "CRR1936095_r1.part_001")
        self.assertEqual(
            p10.strip_compression_suffix("CRR1936095_r1.part_006.fastq.gz"),
            "CRR1936095_r1.part_006")
        self.assertIsNone(p10.strip_compression_suffix("part_001.fq"))

    def test_reference_sha_mismatch_exits_2_with_no_artifact(self):
        data = self.make_data((self.REAL_PART_1, self.REAL_PART_2))
        code, err = self.run_stage(data, reference_sha="0" * 64)
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertIn("refusing to consume a modified reference", err)
        self.assertFalse(self.out.exists())

    def test_one_part_directory_exits_2(self):
        data = self.make_data((self.REAL_PART_1, None))
        code, _err = self.run_stage(data)
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertFalse(self.out.exists())

    def test_three_part_directory_exits_2(self):
        data = self.make_data((self.REAL_PART_1, self.REAL_PART_2,
                               "CRR1936095_r1.part_007.fq.gz"))
        code, _err = self.run_stage(data)
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertFalse(self.out.exists())

    def test_wrong_part_name_exits_2(self):
        data = self.make_data(("CRR1936095_r1.part_002.fq.gz",
                               self.REAL_PART_2))
        code, _err = self.run_stage(data)
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertFalse(self.out.exists())

    def test_reversed_parts_are_rejected(self):
        """gather_inputs sorts a directory, so pin the ORDER check directly."""
        data = self.make_data((self.REAL_PART_1, self.REAL_PART_2))
        first, second = sorted(data.iterdir())
        with self.assertRaises(ValueError):
            p10.require_split_parts([second, first])

    def test_parity_mismatch_propagates_and_writes_nothing(self):
        data = self.make_data((self.REAL_PART_1, self.REAL_PART_2))

        def parity_failure(k):
            raise SystemExit(p10.EXIT_NO)

        code, _err = self.run_stage(data, parity_side_effect=parity_failure)
        self.assertEqual(code, p10.EXIT_NO)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
