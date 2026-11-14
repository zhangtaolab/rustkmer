#!/usr/bin/env python3
"""Unit suite for the full-scale `py-t16` arm and the two session stages.

Hand-built fixtures, tempdir only, no binary invoked: `bench.measure`,
`bench.stats`, `bench.jellyfish_stats`, the interpreter query and the disk
floor are injected, so this suite proves the Phase-9-derived discipline at
full-input scale without a real run.

The load-bearing rules encoded here:
  * one fresh interpreter per rep receives BOTH split parts through two
    `--inputs` flags in argv order (never one part, never reversed);
  * every rep is validated: positive exact counts, a native module inside the
    interpreter's site-packages, and `threads_resolved == 16`;
  * zero counts, a missing stats file, a non-native/outside module, a thread
    mismatch, or a rep-count disagreement is exit 2 with NO artifact;
  * every session's arms must agree on the exact counts, and the two
    sessions' jellyfish arms must agree on counts AND input fingerprints;
  * the stage documents expose the pinned downstream schema by key.

Stdlib unittest only — no pytest, no PyO3, no real dataset.
"""

import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.bench import phase10 as p10
from scripts.bench.bench import validate_provenance, validate_schema

PART_1_NAME = "CRR1936095_r1.part_001.fq.gz"
PART_2_NAME = "CRR1936095_r1.part_006.fq.gz"


def fake_provenance(executable="/repo/target/release/rustkmer",
                    build_profile="release"):
    """A structurally valid provenance block (validate_provenance-clean)."""
    return {
        "binary": {"path": str(executable), "size_bytes": 1234,
                   "sha256": "a" * 64},
        "git_commit": "b" * 40,
        "git_dirty": False,
        "build_profile": build_profile,
        "rust_toolchain": "rustc 1.82.0 (fake)",
        "platform": "darwin-arm64",
        "created": "2026-11-13T00:00:00+00:00",
    }


def make_fake_measure(module_path, total=200, unique=100,
                      threads_resolved=None, write_stats=True,
                      inputs_override=None, vary=False):
    """A fake bench.measure that writes the worker payload the controller reads.

    By default it echoes the arm's own `--inputs` order and honors
    `--threads`; pass `inputs_override` to model a worker that reordered or
    dropped a part, `threads_resolved` to model a binding that ignored the
    thread configuration, and `write_stats=False` to model a worker that
    produced no payload.
    """
    calls = {"n": 0}

    def fake_measure(argv):
        i = calls["n"]
        calls["n"] += 1
        if "--stats-out" in argv:
            stats_path = Path(argv[argv.index("--stats-out") + 1])
            requested = int(argv[argv.index("--threads") + 1])
            if inputs_override is not None:
                reported_inputs = [str(part) for part in inputs_override]
            else:
                reported_inputs = [argv[j + 1]
                                   for j, token in enumerate(argv)
                                   if token == "--inputs"]
            payload = {
                "total_kmers": total + (i if vary else 0),
                "unique_kmers": unique + (i if vary else 0),
                "threads_resolved": (requested if threads_resolved is None
                                     else threads_resolved),
                "rayon_num_threads_env": str(requested),
                "module_path": str(module_path),
                "module_mtime": 1.0,
                "python_version": "3.13.11",
                "inputs": reported_inputs,
            }
            if write_stats:
                stats_path.write_text(json.dumps(payload), encoding="utf-8")
        return {"wall_s": 1.0 + i, "peak_rss_bytes": 1000 + i}

    return fake_measure


def make_py_rep(total=200, unique=100, module="/site/pyrustkmer.so",
                threads=16, inputs=None, wall=1.0):
    return {"wall_s": wall, "peak_rss_bytes": 1000, "peak_bytes": 1000,
            "total_kmers": total, "unique_kmers": unique,
            "module_path": module, "threads_resolved": threads,
            "inputs": list(inputs or ["/data/part_001.fq.gz",
                                      "/data/part_006.fq.gz"])}


def make_arm(name, tool, threads, unique=100, total=200, wall=10.0,
             db_sha256=None):
    rep = {"wall_s": wall, "peak_rss_bytes": 1000, "peak_bytes": 1000,
           "cache_state": "unavailable", "round": 0, "arm_order": 0}
    return {
        "name": name,
        "tool": tool,
        "threads": threads,
        "inputs": ["/data/part_001.fq.gz", "/data/part_006.fq.gz"],
        "reps": [rep],
        "medians": {"wall_s": wall, "peak_rss_bytes": 1000,
                    "peak_bytes": 1000, "cv_wall_pct": None,
                    "cv_warning": False},
        "unique_kmers": unique,
        "total_kmers": total,
        "db_sha256": db_sha256,
    }


class FullArmFixture(unittest.TestCase):
    """Shared filesystem + fake interpreter/module fixture."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.data = self.tmp / "data"
        self.data.mkdir()
        self.part1 = self.data / PART_1_NAME
        self.part2 = self.data / PART_2_NAME
        self.part1.write_bytes(b"part-001-bytes")
        self.part2.write_bytes(b"part-006-bytes")
        # The full-scale stages pin part_001's sha256; point the pin at this
        # fixture's bytes so the real resolver is exercised end to end.
        self.pinned_source_sha256 = hashlib.sha256(
            self.part1.read_bytes()).hexdigest()
        pin_patch = mock.patch.object(
            p10, "PINNED_SOURCE_SHA256", self.pinned_source_sha256)
        pin_patch.start()
        self.addCleanup(pin_patch.stop)
        self.site = self.tmp / "site-packages"
        self.site.mkdir()
        self.module = self.site / "pyrustkmer.cpython-313-darwin.so"
        self.module.write_bytes(b"fake native extension bytes")
        self.scratch = self.tmp / "scratch"
        self.scratch.mkdir()
        self.out = self.tmp / "session.json"
        self.rustkmer = "/repo/target/release/rustkmer"
        self.info = {"site_prefix": str(self.site),
                     "executable": sys.executable,
                     "version": "3.13.11"}

    def build_specs(self, include=(p10.ARM_JF_T16, p10.ARM_PY_T16)):
        with mock.patch.object(p10.python_bench, "interpreter_info",
                               return_value=self.info):
            return p10.build_arm_specs(
                [self.part1, self.part2], 21, self.rustkmer,
                sys.executable, self.scratch, include)

    def run_py_rounds(self, measure, reps=2):
        specs = [spec for spec in self.build_specs()
                 if spec["name"] == p10.ARM_PY_T16]
        return p10.run_rounds(
            specs, reps, 0, measure_fn=measure,
            purge_fn=lambda: "unavailable", sleep_fn=lambda _s: None)

    def run_main(self, argv, patches):
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
        return code, out.getvalue(), err.getvalue()


class TestResolveTwoParts(FullArmFixture):
    """The full-scale stages refuse anything but the pinned split parts."""

    def test_pinned_parts_are_accepted(self):
        self.assertEqual(p10._resolve_two_parts(self.data),
                         [self.part1, self.part2])

    def test_wrong_part_name_is_rejected(self):
        self.part1.rename(self.data / "CRR1936095_r1.part_002.fq.gz")
        with self.assertRaises(ValueError):
            p10._resolve_two_parts(self.data)

    def test_different_part_001_bytes_are_rejected(self):
        with mock.patch.object(p10, "PINNED_SOURCE_SHA256", "0" * 64):
            with self.assertRaises(ValueError):
                p10._resolve_two_parts(self.data)


class TestWorkerArgv(FullArmFixture):
    """The py arm's argv carries BOTH parts, in order, in one process."""

    def test_two_inputs_flags_in_part_order(self):
        specs = {spec["name"]: spec for spec in self.build_specs()}
        argv = specs[p10.ARM_PY_T16]["cmd"]
        self.assertEqual(argv.count("--inputs"), 2)
        first = argv.index("--inputs")
        second = argv.index("--inputs", first + 1)
        self.assertEqual(argv[first + 1], str(self.part1))
        self.assertEqual(argv[second + 1], str(self.part2))

    def test_py_spec_carries_the_interpreter_site_prefix(self):
        specs = {spec["name"]: spec for spec in self.build_specs()}
        self.assertEqual(specs[p10.ARM_PY_T16]["site_prefix"], str(self.site))

    def test_one_process_one_thread_configuration(self):
        """The worker argv has no --input flag: only the two-part seam."""
        specs = {spec["name"]: spec for spec in self.build_specs()}
        argv = specs[p10.ARM_PY_T16]["cmd"]
        self.assertNotIn("--input", argv)
        self.assertEqual(argv[argv.index("--worker")], "--worker")
        self.assertEqual(argv[argv.index("--threads") + 1], "16")


class TestPythonRepValidation(FullArmFixture):
    """Every invalid worker outcome is a hard failure, never a number."""

    def test_two_input_accumulation_yields_the_exact_sum(self):
        reps_by_arm = self.run_py_rounds(
            make_fake_measure(self.module, total=321, unique=123))
        arm = p10.finalize_python_arm(p10.ARM_PY_T16,
                                      reps_by_arm[p10.ARM_PY_T16])
        self.assertEqual(arm["unique_kmers"], 123)
        self.assertEqual(arm["total_kmers"], 321)
        self.assertEqual(arm["inputs"], [str(self.part1), str(self.part2)])
        self.assertEqual(arm["threads"], 16)
        self.assertIsNone(arm["db_sha256"])
        expected_sha = hashlib.sha256(self.module.read_bytes()).hexdigest()
        for rep in arm["reps"]:
            self.assertEqual(rep["module_sha256"], expected_sha)
            self.assertEqual(rep["threads_resolved"], 16)

    def test_zero_counts_are_invalid(self):
        with self.assertRaises(ValueError):
            self.run_py_rounds(make_fake_measure(self.module, total=0,
                                                 unique=0))

    def test_missing_stats_file_is_invalid(self):
        with self.assertRaises(ValueError):
            self.run_py_rounds(make_fake_measure(self.module,
                                                 write_stats=False))

    def test_non_native_module_is_invalid(self):
        shim = self.site / "pyrustkmer.py"
        shim.write_text("# python shim, no native bytes\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.run_py_rounds(make_fake_measure(shim))

    def test_module_outside_site_prefix_is_invalid(self):
        outside = self.tmp / "elsewhere"
        outside.mkdir()
        stale = outside / "pyrustkmer.cpython-313-darwin.so"
        stale.write_bytes(b"stale extension")
        with self.assertRaises(ValueError):
            self.run_py_rounds(make_fake_measure(stale))

    def test_thread_count_mismatch_is_invalid(self):
        with self.assertRaises(ValueError):
            self.run_py_rounds(make_fake_measure(self.module,
                                                 threads_resolved=8))

    def test_reordered_parts_are_invalid(self):
        with self.assertRaises(ValueError):
            self.run_py_rounds(make_fake_measure(
                self.module,
                inputs_override=[str(self.part2), str(self.part1)]))

    def test_dropped_part_is_invalid(self):
        with self.assertRaises(ValueError):
            self.run_py_rounds(make_fake_measure(
                self.module, inputs_override=[str(self.part1)]))


class TestFinalizePythonArm(unittest.TestCase):
    """`finalize_python_arm` rejects disagreement instead of averaging it."""

    def test_rep_count_disagreement_is_rejected(self):
        reps = [make_py_rep(total=200), make_py_rep(total=201)]
        with self.assertRaises(ValueError):
            p10.finalize_python_arm(p10.ARM_PY_T16, reps)

    def test_matching_reps_reduce_to_medians_and_exact_counts(self):
        reps = [make_py_rep(wall=10.0), make_py_rep(wall=20.0)]
        arm = p10.finalize_python_arm(p10.ARM_PY_T16, reps)
        self.assertEqual(arm["medians"]["wall_s"], 15.0)
        self.assertEqual(arm["unique_kmers"], 100)
        self.assertEqual(arm["total_kmers"], 200)


class TestSessionParity(unittest.TestCase):
    """Internal and cross-session parity are hard failures when they differ."""

    def _doc(self, arms, fingerprint=None, session="python"):
        return {
            "session": session,
            "input_fingerprint": fingerprint or [
                {"path": "/data/part_001.fq.gz", "size_bytes": 1,
                 "sha256": "c" * 64},
                {"path": "/data/part_006.fq.gz", "size_bytes": 2,
                 "sha256": "d" * 64},
            ],
            "arms": arms,
        }

    def test_session_parity_accepts_equal_arms(self):
        block = p10.assert_session_parity(
            self._doc([make_arm(p10.ARM_JF_T16, "jellyfish", 16),
                       make_arm(p10.ARM_PY_T16, "pyrustkmer", 16)]),
            p10.ARM_JF_T16, p10.ARM_PY_T16)
        self.assertTrue(block["equal"])
        self.assertEqual(block["unique_kmers"], 100)

    def test_session_parity_rejects_a_py_jf_mismatch(self):
        with self.assertRaises(ValueError):
            p10.assert_session_parity(
                self._doc([make_arm(p10.ARM_JF_T16, "jellyfish", 16),
                           make_arm(p10.ARM_PY_T16, "pyrustkmer", 16,
                                    unique=101)]),
                p10.ARM_JF_T16, p10.ARM_PY_T16)

    def test_session_parity_rejects_zero_counts(self):
        with self.assertRaises(ValueError):
            p10.assert_session_parity(
                self._doc([make_arm(p10.ARM_JF_T16, "jellyfish", 16),
                           make_arm(p10.ARM_PY_T16, "pyrustkmer", 16,
                                    unique=0)]),
                p10.ARM_JF_T16, p10.ARM_PY_T16)

    def test_cross_session_accepts_identical_counts_and_fingerprints(self):
        cli = self._doc([make_arm(p10.ARM_JF_T16, "jellyfish", 16)],
                        session="cli")
        py = self._doc([make_arm(p10.ARM_JF_T16, "jellyfish", 16)],
                       session="python")
        block = p10.assert_cross_session_jellyfish(cli, py)
        self.assertTrue(block["equal"])

    def test_cross_session_rejects_a_python_document_as_the_cli_side(self):
        cli = self._doc([make_arm(p10.ARM_JF_T16, "jellyfish", 16)],
                        session="python")
        py = self._doc([make_arm(p10.ARM_JF_T16, "jellyfish", 16)],
                       session="python")
        with self.assertRaises(ValueError):
            p10.assert_cross_session_jellyfish(cli, py)

    def test_cross_session_rejects_count_differences(self):
        cli = self._doc([make_arm(p10.ARM_JF_T16, "jellyfish", 16)],
                        session="cli")
        py = self._doc([make_arm(p10.ARM_JF_T16, "jellyfish", 16,
                                 total=201)], session="python")
        with self.assertRaises(ValueError):
            p10.assert_cross_session_jellyfish(cli, py)

    def test_cross_session_rejects_fingerprint_differences(self):
        cli = self._doc([make_arm(p10.ARM_JF_T16, "jellyfish", 16)],
                        session="cli")
        py = self._doc([make_arm(p10.ARM_JF_T16, "jellyfish", 16)],
                       fingerprint=[{"path": "/other.fq.gz",
                                     "size_bytes": 1, "sha256": "e" * 64}],
                       session="python")
        with self.assertRaises(ValueError):
            p10.assert_cross_session_jellyfish(cli, py)


class CliStageFixture(FullArmFixture):
    """Scratch artifacts a fake CLI measurement leaves behind."""

    def setUp(self):
        super().setUp()
        (self.scratch / "phase10-rk-t16.rkdb").write_bytes(b"identical-db")
        (self.scratch / "phase10-rk-t1.rkdb").write_bytes(b"identical-db")
        (self.scratch / "phase10-jf-t16.jf").write_bytes(b"jellyfish-db")

    def stage_patches(self, measure=None, stats_value=None, jf_value=None):
        return [
            mock.patch.object(p10, "binary_provenance",
                              side_effect=fake_provenance),
            mock.patch.object(p10, "attempt_cache_purge",
                              return_value="unavailable"),
            mock.patch.object(p10, "check_disk_floor",
                              return_value=10 ** 12),
            mock.patch.object(p10, "measure",
                              side_effect=measure if measure is not None
                              else make_fake_measure(self.module)),
            mock.patch.object(p10, "stats",
                              return_value=stats_value
                              if stats_value is not None
                              else {"unique_kmers": 100, "total_kmers": 200}),
            mock.patch.object(p10, "jellyfish_stats",
                              return_value=jf_value
                              if jf_value is not None
                              else {"distinct": 100, "total": 200}),
        ]

    def cli_argv(self):
        return ["--stage", "cli", "--k", "21", "--out", str(self.out),
                "--data-dir", str(self.data), "--scratch", str(self.scratch),
                "--rustkmer", self.rustkmer, "--python", sys.executable,
                "--reps", "2", "--cooldown-s", "0"]


class TestCliStageDocument(CliStageFixture):
    """The CLI stage document exposes the pinned downstream schema."""

    def test_stage_writes_the_pinned_sub_shapes(self):
        code, _out, err = self.run_main(self.cli_argv(),
                                        self.stage_patches())
        self.assertEqual(code, p10.EXIT_OK, err)
        doc = json.loads(self.out.read_text(encoding="utf-8"))
        validate_schema(doc)
        validate_provenance(doc)
        self.assertEqual(doc["mode"], "full")
        self.assertEqual(doc["session"], "cli")
        self.assertEqual(doc["params"]["k"], 21)
        self.assertEqual(doc["params"]["threads"], 16)
        self.assertEqual(doc["params"]["reps"], 2)
        by_name = {arm["name"]: arm for arm in doc["arms"]}
        self.assertEqual(by_name[p10.ARM_RK_T16]["db_sha256"],
                         by_name[p10.ARM_RK_T1]["db_sha256"])
        self.assertIsNotNone(by_name[p10.ARM_RK_T16]["db_sha256"])
        self.assertIsNotNone(by_name[p10.ARM_JF_T16]["db_sha256"])
        for arm in doc["arms"]:
            self.assertEqual(arm["inputs"],
                             [str(self.part1), str(self.part2)])
            self.assertIsInstance(arm["reps"], list)
            self.assertIsInstance(arm["medians"], dict)
        preflight = doc["preflight"]
        self.assertEqual(preflight["basis"], "research-upper-estimate")
        self.assertEqual(preflight["distinct_assumed"], 1_200_000_000)
        self.assertEqual(preflight["model"],
                         "cli-16B-slot-32B-pair-64-partitions")
        ok, _detail = p10.memory_gate(preflight["projected_bytes"],
                                      preflight["budget_bytes"])
        self.assertEqual(preflight["decision"],
                         "PROCEED" if ok else "BLOCKED")
        self.assertIn("schedule", doc)
        self.assertEqual(doc["schedule"]["policy"],
                         "round-robin-rotation")
        # The CLI session measured no pyrustkmer arm: it must not claim a
        # pyrustkmer warmup in the recorded order.
        self.assertEqual(doc["schedule"]["warmup_order"],
                         ["rustkmer", "jellyfish"])
        # Scratch databases are deleted after their sha256 is recorded.
        self.assertFalse((self.scratch / "phase10-rk-t16.rkdb").exists())
        self.assertFalse((self.scratch / "phase10-jf-t16.jf").exists())

    def test_unequal_rustkmer_db_shas_exit_2_with_no_artifact(self):
        (self.scratch / "phase10-rk-t1.rkdb").write_bytes(b"different-db")
        code, _out, _err = self.run_main(self.cli_argv(),
                                         self.stage_patches())
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertFalse(self.out.exists())

    def test_zero_counts_exit_2_with_no_artifact(self):
        code, _out, _err = self.run_main(
            self.cli_argv(),
            self.stage_patches(stats_value={"unique_kmers": 0,
                                            "total_kmers": 0}))
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertFalse(self.out.exists())


class PythonStageFixture(FullArmFixture):
    """Committed-evidence fixtures + a fake Python session."""

    def setUp(self):
        super().setUp()
        (self.scratch / "phase10-jf-t16.jf").write_bytes(b"jellyfish-db")
        self.distinct = 1_050_000_000
        self.pre_gate = self.tmp / "10-slice-gate.json"
        self.write_pre_gate()
        self.cli_doc = self.tmp / "10-results-full-k21.json"
        self.write_cli_doc()
        self.preflight = self.tmp / "10-python-preflight.json"
        self.write_preflight()

    def write_pre_gate(self, distinct=None, total=None, sha=None):
        doc = {
            "schema_version": p10.SCHEMA_VERSION,
            "kind": "phase10-slice-gate",
            "phase": 10,
            "input_fingerprint": [p10.fingerprint(self.part1),
                                  p10.fingerprint(self.part2)],
            "gates": [{
                "k": 21,
                "slice_recipe": {"mode": "slice", "k": 21,
                                 "canonical": True, "threads": 16,
                                 "hash_size": "2G",
                                 "slice_selection": "head",
                                 "slice_reads": 4_000_000,
                                 "source_sha256": "f" * 64},
                "distinct": (p10.PINNED_HEAD4M["distinct"]
                             if distinct is None else distinct),
                "total": (p10.PINNED_HEAD4M["total"]
                          if total is None else total),
                "parity_reference": {
                    "path": "scripts/bench/baselines/slice_parity.crr1936095.json",
                    "sha256": p10.REFERENCE_SHA256 if sha is None else sha,
                },
                "reference_gate": "pinned-reference",
            }],
            "provenance": fake_provenance(),
        }
        self.pre_gate.write_text(json.dumps(doc), encoding="utf-8")

    def write_cli_doc(self, distinct=None):
        distinct = self.distinct if distinct is None else distinct
        self.cli_doc.write_text(
            json.dumps(self.cli_document(distinct=distinct)),
            encoding="utf-8")

    def write_preflight(self, distinct=None):
        distinct = self.distinct if distinct is None else distinct
        record = p10.preflight_record(
            21, distinct, str(self.cli_doc), p10.file_sha256(self.cli_doc))
        doc = {
            "schema_version": p10.SCHEMA_VERSION,
            "kind": "phase10-python-preflight",
            "phase": 10,
            "records": [record],
            "overall": record["decision"],
            "provenance": fake_provenance(),
        }
        self.preflight.write_text(json.dumps(doc), encoding="utf-8")

    def cli_document(self, distinct=None):
        distinct = self.distinct if distinct is None else distinct
        return {
            "schema_version": p10.SCHEMA_VERSION,
            "mode": "full",
            "phase": 10,
            "session": "cli",
            "params": {"k": 21, "canonical": True, "threads": 16,
                       "reps": 2, "cooldown_s": 0, "hash_size": "10G",
                       "arm_order": list(p10.ARM_ORDER)},
            "platform": {"system": "Darwin", "release": "25.6.0",
                         "machine": "arm64", "python": "3.13.11"},
            "created": "2026-11-13T00:00:00+00:00",
            "input_fingerprint": [p10.fingerprint(self.part1),
                                  p10.fingerprint(self.part2)],
            "arms": [
                make_arm(p10.ARM_RK_T16, "rustkmer", 16, unique=distinct,
                         total=distinct * 2, wall=10.0, db_sha256="c" * 64),
                make_arm(p10.ARM_RK_T1, "rustkmer", 1, unique=distinct,
                         total=distinct * 2, wall=40.0, db_sha256="c" * 64),
                make_arm(p10.ARM_JF_T16, "jellyfish", 16, unique=distinct,
                         total=distinct * 2, wall=20.0,
                         db_sha256="d" * 64),
            ],
            "provenance": fake_provenance(),
        }

    def stage_patches(self, measure=None):
        return [
            mock.patch.object(p10.python_bench, "interpreter_info",
                              return_value=self.info),
            mock.patch.object(p10.python_bench, "binary_provenance",
                              side_effect=fake_provenance),
            mock.patch.object(p10, "binary_provenance",
                              side_effect=fake_provenance),
            mock.patch.object(p10.python_bench, "maturin_version",
                              return_value="maturin 1.11.5"),
            mock.patch.object(p10, "attempt_cache_purge",
                              return_value="unavailable"),
            mock.patch.object(p10, "check_disk_floor",
                              return_value=10 ** 12),
            mock.patch.object(p10, "measure",
                              side_effect=measure if measure is not None
                              else make_fake_measure(
                                  self.module, total=self.distinct * 2,
                                  unique=self.distinct)),
            mock.patch.object(p10, "jellyfish_stats",
                              return_value={"distinct": self.distinct,
                                            "total": self.distinct * 2}),
        ]

    def python_argv(self):
        return ["--stage", "python", "--k", "21", "--out", str(self.out),
                "--data-dir", str(self.data), "--scratch", str(self.scratch),
                "--rustkmer", self.rustkmer, "--python", sys.executable,
                "--reps", "2", "--cooldown-s", "0",
                "--pre-gate", str(self.pre_gate),
                "--preflight", str(self.preflight),
                "--cli-doc", str(self.cli_doc)]


class TestPythonStageDocument(PythonStageFixture):
    """The Python stage document exposes the pinned downstream schema."""

    def test_stage_writes_the_pinned_sub_shapes(self):
        code, _out, err = self.run_main(self.python_argv(),
                                        self.stage_patches())
        self.assertEqual(code, p10.EXIT_OK, err)
        doc = json.loads(self.out.read_text(encoding="utf-8"))
        validate_schema(doc)
        validate_provenance(doc)
        self.assertEqual(doc["mode"], "full")
        self.assertEqual(doc["session"], "python")
        self.assertEqual(doc["params"]["k"], 21)
        self.assertEqual(doc["params"]["threads"], 16)
        self.assertEqual(doc["params"]["reps"], 2)
        # The Python session measured no rustkmer arm: it must not claim a
        # rustkmer warmup in the recorded order.
        self.assertEqual(doc["schedule"]["warmup_order"],
                         ["jellyfish", "pyrustkmer"])
        by_name = {arm["name"]: arm for arm in doc["arms"]}
        self.assertIsNone(by_name[p10.ARM_PY_T16]["db_sha256"])
        self.assertIsNotNone(by_name[p10.ARM_JF_T16]["db_sha256"])
        self.assertEqual(doc["pre_gate"]["sha256"],
                         hashlib.sha256(
                             self.pre_gate.read_bytes()).hexdigest())
        self.assertEqual(doc["preflight"]["path"], str(self.preflight))
        self.assertEqual(
            doc["preflight"]["sha256"],
            hashlib.sha256(self.preflight.read_bytes()).hexdigest())
        memory = doc["memory_preflight"]
        self.assertEqual(memory["decision"], "PROCEED")
        self.assertEqual(memory["distinct"], 1_050_000_000)
        self.assertEqual(memory["budget_bytes"], p10.MEMORY_BUDGET_BYTES)
        self.assertGreaterEqual(memory["headroom_bytes"], 0)
        self.assertEqual(memory["source_sha256"],
                         hashlib.sha256(
                             self.cli_doc.read_bytes()).hexdigest())
        self.assertGreater(memory["observed_peak_bytes"], 0)
        self.assertEqual(doc["cross_session"]["cli_doc"], str(self.cli_doc))
        self.assertEqual(
            doc["cross_session"]["cli_doc_sha256"],
            hashlib.sha256(self.cli_doc.read_bytes()).hexdigest())
        self.assertIn("module",
                      doc["provenance"])
        self.assertIn("cli_binary", doc["provenance"])
        self.assertFalse((self.scratch / "phase10-jf-t16.jf").exists())

    def test_blocked_preflight_exits_2_with_no_artifact(self):
        self.write_cli_doc(distinct=2_000_000_000)
        self.write_preflight(distinct=2_000_000_000)
        code, _out, _err = self.run_main(self.python_argv(),
                                         self.stage_patches())
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertFalse(self.out.exists())

    def test_tampered_projection_exits_2_with_no_artifact(self):
        doc = json.loads(self.preflight.read_text(encoding="utf-8"))
        doc["records"][0]["projected_bytes"] += 1
        self.preflight.write_text(json.dumps(doc), encoding="utf-8")
        code, _out, _err = self.run_main(self.python_argv(),
                                         self.stage_patches())
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertFalse(self.out.exists())

    def test_preflight_with_a_substituted_budget_exits_2(self):
        """A record's own budget can never turn BLOCKED into PROCEED."""
        doc = json.loads(self.preflight.read_text(encoding="utf-8"))
        record = doc["records"][0]
        record["budget_bytes"] = 200_000_000_000
        record["headroom_bytes"] = (record["budget_bytes"]
                                    - record["projected_bytes"])
        record["decision"] = "PROCEED"
        self.preflight.write_text(json.dumps(doc), encoding="utf-8")
        code, _out, err = self.run_main(self.python_argv(),
                                        self.stage_patches())
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertIn("MEMORY_BUDGET_BYTES", err)
        self.assertFalse(self.out.exists())

    def test_preflight_from_a_different_cli_document_exits_2(self):
        """A smaller source document can never authorize this measured run."""
        self.write_cli_doc(distinct=100)
        code, _out, _err = self.run_main(self.python_argv(),
                                         self.stage_patches())
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertFalse(self.out.exists())

    def test_preflight_source_sha_tamper_exits_2(self):
        doc = json.loads(self.preflight.read_text(encoding="utf-8"))
        doc["records"][0]["distinct_source_sha256"] = "e" * 64
        self.preflight.write_text(json.dumps(doc), encoding="utf-8")
        code, _out, _err = self.run_main(self.python_argv(),
                                         self.stage_patches())
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertFalse(self.out.exists())

    def test_pre_gate_with_unpinned_counts_exits_2_with_no_artifact(self):
        self.write_pre_gate(distinct=p10.PINNED_HEAD4M["distinct"] + 1)
        code, _out, _err = self.run_main(self.python_argv(),
                                         self.stage_patches())
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertFalse(self.out.exists())

    def test_pre_gate_with_unpinned_reference_sha_exits_2(self):
        self.write_pre_gate(sha="0" * 64)
        code, _out, _err = self.run_main(self.python_argv(),
                                         self.stage_patches())
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertFalse(self.out.exists())

    def test_pre_gate_without_provenance_exits_2(self):
        doc = json.loads(self.pre_gate.read_text(encoding="utf-8"))
        del doc["provenance"]
        self.pre_gate.write_text(json.dumps(doc), encoding="utf-8")
        code, _out, _err = self.run_main(self.python_argv(),
                                         self.stage_patches())
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertFalse(self.out.exists())

    def test_pre_gate_for_different_inputs_exits_2(self):
        doc = json.loads(self.pre_gate.read_text(encoding="utf-8"))
        doc["input_fingerprint"][0]["sha256"] = "0" * 64
        self.pre_gate.write_text(json.dumps(doc), encoding="utf-8")
        code, _out, _err = self.run_main(self.python_argv(),
                                         self.stage_patches())
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertFalse(self.out.exists())

    def _add_k31_gate(self, source_sha="f" * 64):
        doc = json.loads(self.pre_gate.read_text(encoding="utf-8"))
        gate21 = doc["gates"][0]
        doc["gates"].append({
            "k": 31,
            "slice_recipe": dict(gate21["slice_recipe"], k=31,
                                 source_sha256=source_sha),
            "distinct": 261_863_892,
            "total": 479_271_168,
            "parity_reference": None,
            "reference_gate": p10.LIVE_PARITY_ONLY,
        })
        self.pre_gate.write_text(json.dumps(doc), encoding="utf-8")

    def test_pre_gate_missing_the_session_k_is_rejected(self):
        """A k=31 session must not be authorized by a k=21-only gate (IN-01)."""
        with self.assertRaises(ValueError) as ctx:
            p10._load_slice_gate_doc(self.pre_gate, 31)
        self.assertIn("no gate for the session's k=31", str(ctx.exception))

    def test_pre_gate_validates_the_k31_gate_for_a_k31_session(self):
        self._add_k31_gate()
        loaded = p10._load_slice_gate_doc(self.pre_gate, 31)
        self.assertEqual([gate["k"] for gate in loaded["gates"]], [21, 31])

    def test_pre_gate_k31_gate_from_another_slice_is_rejected(self):
        self._add_k31_gate(source_sha="0" * 64)
        with self.assertRaises(ValueError) as ctx:
            p10._load_slice_gate_doc(self.pre_gate, 31)
        self.assertIn("same provisioned slice", str(ctx.exception))

    def test_preflight_without_provenance_exits_2(self):
        doc = json.loads(self.preflight.read_text(encoding="utf-8"))
        del doc["provenance"]
        self.preflight.write_text(json.dumps(doc), encoding="utf-8")
        code, _out, _err = self.run_main(self.python_argv(),
                                         self.stage_patches())
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertFalse(self.out.exists())

    def test_python_session_document_as_cli_doc_exits_2(self):
        """--cli-doc must be a CLI-session document, never a Python one."""
        doc = self.cli_document()
        doc["session"] = "python"
        self.cli_doc.write_text(json.dumps(doc), encoding="utf-8")
        code, _out, err = self.run_main(self.python_argv(),
                                        self.stage_patches())
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertIn("session", err)
        self.assertFalse(self.out.exists())

    def test_invalid_worker_outcome_exits_2_with_no_artifact(self):
        code, _out, _err = self.run_main(
            self.python_argv(),
            self.stage_patches(measure=make_fake_measure(
                self.module, threads_resolved=8)))
        self.assertEqual(code, p10.EXIT_INVALID)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
