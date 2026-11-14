#!/usr/bin/env python3
"""Unit suite for python_bench.py (05-06, PROF-04).

Controller logic is tested WITHOUT importing PyO3: fake measure results and
worker stats files drive main(argv) through the real provisioning / filter /
parity / reduction / validation paths. One opt-in integration test runs only
when RUSTKMER_PYBENCH_VENV points at the freshly built venv. Stdlib only —
no PyO3, NumPy, pytest, or human dataset needed.
"""

import contextlib
import gzip
import io
import json
import os
import platform
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from scripts.bench import python_bench as pb
from scripts.bench.bench import validate_provenance, validate_schema


def fake_provenance(executable, build_profile):
    """A structurally valid provenance block (validate_provenance-clean)."""
    return {
        "binary": {"path": str(executable), "size_bytes": 1234,
                   "sha256": "a" * 64},
        "git_commit": "b" * 40,
        "git_dirty": False,
        "build_profile": build_profile,
        "rust_toolchain": "rustc 1.101.0-nightly (fake)",
        "platform": "darwin-arm64",
        "created": "2026-11-12T00:00:00+00:00",
    }


def make_fake_measure(module_path, total=100, unique=90, vary=False,
                      write_stats=True, threads_resolved=None):
    """Fake bench.measure: writes the worker stats file the controller reads
    and returns deterministic wall/RSS (wall = 1.0 + call index).

    By default the fake models a binding that HONORS its thread
    configuration: ``threads_resolved`` follows the worker's ``--threads``
    argument (``default`` -> 16). Pass ``threads_resolved`` to model a
    binding that ignores the request.
    """
    calls = {"n": 0}

    def fake_measure(argv):
        i = calls["n"]
        calls["n"] += 1
        stats_out = Path(argv[argv.index("--stats-out") + 1])
        requested = (argv[argv.index("--threads") + 1]
                     if "--threads" in argv else "1")
        if threads_resolved is not None:
            resolved = threads_resolved
        elif requested == "default":
            resolved = 16
        else:
            resolved = int(requested)
        payload = {
            "total_kmers": total + (i if vary else 0),
            "unique_kmers": unique + (i if vary else 0),
            "threads_resolved": resolved,
            "rayon_num_threads_env": (None if requested == "default"
                                      else str(int(requested))),
            "module_path": str(module_path),
            "module_mtime": 1794477430.0,
            "python_version": "3.13.11",
        }
        if write_stats:
            stats_out.write_text(json.dumps(payload), encoding="utf-8")
        return {"wall_s": 1.0 + i, "peak_rss_bytes": 1_000_000 + i}

    return fake_measure


def fastq_record(name, seq):
    return f"@{name}\n{seq}\n+\n{'I' * len(seq)}\n".encode()


def build_gz_fixture(path, n_records=30):
    """Deterministic gz FASTQ: every 5th record carries N, every 7th n."""
    with gzip.open(path, "wb") as fh:
        for i in range(n_records):
            seq = list("ACGT" * 8)  # 32 bp
            if i % 5 == 0:
                seq[3] = "N"
            if i % 7 == 0:
                seq[10] = "n"
            fh.write(fastq_record(f"read{i}", "".join(seq)))
    return path


def make_rep(total=100, unique=90, module="/x/pyrustkmer.so", wall=1.0,
             threads_resolved=1, module_sha256=None, module_mtime=None):
    return {"wall_s": wall, "peak_rss_bytes": 1000, "total_kmers": total,
            "unique_kmers": unique, "module_path": module,
            "module_sha256": module_sha256, "module_mtime": module_mtime,
            "threads_resolved": threads_resolved,
            "cache_state": "unavailable", "rep": 0}


def make_arm(name="py21-real-n-t1", reps=None):
    reps = reps if reps is not None else [make_rep()]
    return {"name": name, "tool": "pyrustkmer", "threads": 1, "reps": reps,
            "medians": {"wall_s": 1.0, "peak_rss_bytes": 1000,
                        "cv_wall_pct": None, "cv_warning": False},
            "unique_kmers": 90, "total_kmers": 100,
            "evidence_class": pb.REAL_N_EVIDENCE_CLASS}


def make_doc(mode="slice"):
    return {
        "schema_version": 1,
        "mode": mode,
        "params": {"k": 21},
        "platform": {"system": "Darwin", "release": "25.6.0",
                     "machine": "arm64", "python": "3.13.11"},
        "created": "2026-11-12T00:00:00+00:00",
        "input_fingerprint": [{"path": "slice.fq", "size_bytes": 10,
                               "sha256": "c" * 64}],
        "arms": [make_arm()],
        "provenance": fake_provenance("/x/python", "release"),
    }


def make_control(reps=None):
    return {
        "input_fingerprint": {"path": "control.fq", "size_bytes": 10,
                              "sha256": "d" * 64},
        "source_selection_manifest": {"seed": 7, "selected_reads": 20},
        "kept_reads": 15,
        "dropped_reads": 5,
        "filter": pb.N_FREE_FILTER,
        "parity_control": {
            "reference": "rustkmer-cli-same-bytes",
            "cli": {"distinct": 90, "total": 100},
            "python": {"unique_kmers": 90, "total_kmers": 100},
            "equal": True,
        },
        "exact_counts": {"total_kmers": 100, "unique_kmers": 90},
        "arms": [make_arm("py21-n-free-control-t1", reps)],
        "cli_provenance": fake_provenance("/x/rustkmer", "release"),
    }


def make_synthetic_baseline(control_wall=12.0, exact=None,
                            control_sha="e" * 64, platform_flavor=None,
                            provenance_platform=None, k=21, canonical=True):
    """A minimal committed-baseline envelope for the comparison guards.

    Shape mirrors scripts/bench/baselines/python_bench_baseline.darwin.json;
    the absolute numbers are synthetic (the real guard must not hard-code
    the committed file's values).
    """
    flavor = (platform_flavor if platform_flavor is not None
              else pb.baseline_filename(platform.system())[1])
    host_platform = (provenance_platform if provenance_platform is not None
                     else f"{sys.platform}-{platform.machine()}")
    return {
        "schema_version": 1,
        "platform": flavor,
        "created": "2026-11-12T00:00:00+00:00",
        "host_class": "dev-host Apple M4 Max (16 cores, 128 GiB)",
        "comparison_basis": "n-free-control",
        "params": {"k": k, "canonical": canonical, "threads": 1,
                   "slice_reads": 20, "slice_seed": 7},
        "n_free_control": {
            "input_fingerprint": {"path": "control.fq", "size_bytes": 10,
                                  "sha256": control_sha},
            "exact_counts": (exact if exact is not None
                             else {"total_kmers": 100, "unique_kmers": 90}),
            "arms": [{"name": f"py{k}-n-free-control-t1", "threads": 1,
                      "medians": {"wall_s": control_wall}}],
        },
        "provenance": {"platform": host_platform},
    }


def make_new_control_doc(t1_wall, default_wall):
    """The two measured control arms a comparison run produces."""
    return {"n_free_control": {"arms": [
        {"name": "py21-n-free-control-t1",
         "medians": {"wall_s": t1_wall}},
        {"name": "py21-n-free-control-tdefault",
         "medians": {"wall_s": default_wall}},
    ]}}


class TestNFreeFilter(unittest.TestCase):
    """Deterministic drop-records-with-N filter, 4-line record integrity."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_drops_n_records_and_preserves_order(self):
        src = self.root / "in.fq"
        records = [
            fastq_record("r0", "ACGTACGT"),
            fastq_record("r1", "ACNTACGT"),      # N -> dropped
            fastq_record("r2", "TTTTACGT"),
            fastq_record("r3", "ACnTACGT"),      # lowercase n -> dropped
            fastq_record("r4", "GGGGACGT"),
        ]
        src.write_bytes(b"".join(records))
        dst = self.root / "out.fq"
        counts = pb.filter_n_free(src, dst)
        self.assertEqual(counts, {"kept_reads": 3, "dropped_reads": 2})
        self.assertEqual(dst.read_bytes(),
                         records[0] + records[2] + records[4])

    def test_filter_is_byte_deterministic(self):
        src = self.root / "in.fq"
        src.write_bytes(fastq_record("r0", "ACGT") +
                        fastq_record("r1", "NCGT") +
                        fastq_record("r2", "TGCA"))
        a, b = self.root / "a.fq", self.root / "b.fq"
        ca = pb.filter_n_free(src, a)
        cb = pb.filter_n_free(src, b)
        self.assertEqual(ca, cb)
        self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_kept_records_are_complete_four_line_records(self):
        src = self.root / "in.fq"
        src.write_bytes(fastq_record("r0", "ACGTAC") +
                        fastq_record("r1", "NCGTAC"))
        dst = self.root / "out.fq"
        pb.filter_n_free(src, dst)
        lines = dst.read_bytes().splitlines()
        self.assertEqual(len(lines) % 4, 0)
        self.assertTrue(lines[0].startswith(b"@"))
        self.assertTrue(lines[2].startswith(b"+"))
        self.assertEqual(len(lines[1]), len(lines[3]))

    def test_malformed_record_raises(self):
        src = self.root / "in.fq"
        src.write_bytes(b"@r0\nACGT\n+\n")  # truncated quality line
        with self.assertRaises(ValueError):
            pb.filter_n_free(src, self.root / "out.fq")

    def test_all_n_input_raises(self):
        src = self.root / "in.fq"
        src.write_bytes(fastq_record("r0", "NNNN"))
        with self.assertRaises(ValueError):
            pb.filter_n_free(src, self.root / "out.fq")


class TestWorkerStatsValidation(unittest.TestCase):
    """Zero counts and stale/shadowed modules are invalid, never a skip."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.site = Path(self.tmp.name) / "site-packages"
        self.site.mkdir()
        self.module = self.site / "pyrustkmer.cpython-313-darwin.so"
        self.module.write_bytes(b"native")

    def payload(self, **over):
        base = {"total_kmers": 100, "unique_kmers": 90,
                "threads_resolved": 1,
                "rayon_num_threads_env": None,
                "module_path": str(self.module), "module_mtime": 1.0,
                "python_version": "3.13.11"}
        base.update(over)
        return base

    def test_valid_stats_return_exact_counts(self):
        counts = pb.validate_worker_stats(self.payload(), self.site)
        self.assertEqual(counts, {"total_kmers": 100, "unique_kmers": 90})

    def test_zero_total_raises(self):
        with self.assertRaises(ValueError):
            pb.validate_worker_stats(self.payload(total_kmers=0), self.site)

    def test_zero_unique_raises(self):
        with self.assertRaises(ValueError):
            pb.validate_worker_stats(self.payload(unique_kmers=0), self.site)

    def test_missing_field_raises(self):
        payload = self.payload()
        del payload["module_mtime"]
        with self.assertRaises(ValueError):
            pb.validate_worker_stats(payload, self.site)

    def test_module_outside_site_packages_raises(self):
        outside = Path(self.tmp.name) / "elsewhere" / "pyrustkmer.so"
        with self.assertRaises(ValueError):
            pb.validate_worker_stats(
                self.payload(module_path=str(outside)), self.site)

    def test_python_shim_module_raises(self):
        shim = self.site / "pyrustkmer" / "__init__.py"
        shim.parent.mkdir()
        shim.write_text("from .pyrustkmer import *\n")
        with self.assertRaises(ValueError):
            pb.validate_worker_stats(
                self.payload(module_path=str(shim)), self.site)

    def test_resolved_threads_mismatch_raises(self):
        """A binding that ignores --threads reports the wrong resolved count."""
        with self.assertRaises(ValueError):
            pb.validate_worker_stats(
                self.payload(threads_resolved=16), self.site,
                expected_threads=1)

    def test_resolved_threads_match_passes(self):
        counts = pb.validate_worker_stats(
            self.payload(threads_resolved=1, rayon_num_threads_env="1"),
            self.site, expected_threads=1)
        self.assertEqual(counts, {"total_kmers": 100, "unique_kmers": 90})

    def test_env_pin_mismatch_raises(self):
        """The pinned default pool must match the arm's requested size."""
        with self.assertRaises(ValueError):
            pb.validate_worker_stats(
                self.payload(threads_resolved=16,
                             rayon_num_threads_env="8"),
                self.site, expected_threads=16)

    def test_missing_env_pin_raises(self):
        payload = self.payload()
        del payload["rayon_num_threads_env"]
        with self.assertRaises(ValueError):
            pb.validate_worker_stats(payload, self.site)

    def test_missing_resolved_threads_raises(self):
        payload = self.payload()
        del payload["threads_resolved"]
        with self.assertRaises(ValueError):
            pb.validate_worker_stats(payload, self.site)

    def test_zero_resolved_threads_raises(self):
        with self.assertRaises(ValueError):
            pb.validate_worker_stats(
                self.payload(threads_resolved=0), self.site)

    def test_default_expected_accepts_any_positive_resolution(self):
        counts = pb.validate_worker_stats(
            self.payload(threads_resolved=16), self.site,
            expected_threads=None)
        self.assertEqual(counts["unique_kmers"], 90)


class TestPinRayonNumThreads(unittest.TestCase):
    """The worker pins rayon's default pool before the binding can use it."""

    def test_explicit_threads_set_the_env_pin(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(pb.pin_rayon_num_threads(16), "16")
            self.assertEqual(os.environ["RAYON_NUM_THREADS"], "16")

    def test_default_threads_remove_an_inherited_pin(self):
        with mock.patch.dict(os.environ, {"RAYON_NUM_THREADS": "4"}):
            self.assertIsNone(pb.pin_rayon_num_threads(None))
            self.assertNotIn("RAYON_NUM_THREADS", os.environ)


class TestRepIdentity(unittest.TestCase):
    """Cross-rep exact-count identity; disagreement is never averaged away."""

    def test_identical_reps_reduce_to_exact_counts(self):
        reps = [make_rep(), make_rep(wall=2.0), make_rep(wall=3.0)]
        exact = pb.check_rep_identity(reps)
        self.assertEqual(exact, {"total_kmers": 100, "unique_kmers": 90})

    def test_count_disagreement_raises(self):
        reps = [make_rep(), make_rep(total=101)]
        with self.assertRaises(ValueError):
            pb.check_rep_identity(reps)

    def test_expected_pin_mismatch_raises(self):
        reps = [make_rep()]
        with self.assertRaises(ValueError):
            pb.check_rep_identity(
                reps, expected={"total_kmers": 100, "unique_kmers": 91})

    def test_module_disagreement_raises(self):
        reps = [make_rep(), make_rep(module="/other/pyrustkmer.so")]
        with self.assertRaises(ValueError):
            pb.check_rep_identity(reps)

    def test_module_sha_disagreement_raises(self):
        """A rebuild replacing the .so at the same path is a different module."""
        reps = [make_rep(module_sha256="a" * 64),
                make_rep(module_sha256="b" * 64)]
        with self.assertRaises(ValueError):
            pb.check_rep_identity(reps)

    def test_module_mtime_disagreement_raises(self):
        reps = [make_rep(module_mtime=1.0), make_rep(module_mtime=2.0)]
        with self.assertRaises(ValueError):
            pb.check_rep_identity(reps)

    def test_thread_resolution_disagreement_raises(self):
        reps = [make_rep(), make_rep(threads_resolved=16)]
        with self.assertRaises(ValueError):
            pb.check_rep_identity(reps)


class TestParityCounts(unittest.TestCase):
    """CLI-vs-Python parity on the same bytes, before any timing."""

    def test_equal_counts_produce_parity_block(self):
        block = pb.parity_counts({"unique_kmers": 90, "total_kmers": 100},
                                 {"unique_kmers": 90, "total_kmers": 100})
        self.assertIs(block["equal"], True)
        self.assertEqual(block["reference"], "rustkmer-cli-same-bytes")
        self.assertEqual(block["cli"], {"distinct": 90, "total": 100})

    def test_distinct_mismatch_raises(self):
        with self.assertRaises(ValueError):
            pb.parity_counts({"unique_kmers": 91, "total_kmers": 100},
                             {"unique_kmers": 90, "total_kmers": 100})

    def test_total_mismatch_raises(self):
        with self.assertRaises(ValueError):
            pb.parity_counts({"unique_kmers": 90, "total_kmers": 101},
                             {"unique_kmers": 90, "total_kmers": 100})

    def test_zero_cli_counts_raise(self):
        with self.assertRaises(ValueError):
            pb.parity_counts({"unique_kmers": 0, "total_kmers": 0},
                             {"unique_kmers": 0, "total_kmers": 0})


class TestBaselineNaming(unittest.TestCase):
    """Per-platform baseline naming; unsupported platforms are invalid."""

    def test_darwin_name(self):
        name, flavor = pb.baseline_filename("Darwin")
        self.assertEqual(name, "python_bench_baseline.darwin.json")
        self.assertEqual(flavor, "darwin")

    def test_linux_name(self):
        name, flavor = pb.baseline_filename("Linux")
        self.assertEqual(name, "python_bench_baseline.linux.json")
        self.assertEqual(flavor, "linux")

    def test_unsupported_platform_raises(self):
        with self.assertRaises(ValueError):
            pb.baseline_filename("Windows")


class TestParseThreads(unittest.TestCase):
    """--threads accepts 'default' or an integer >= 1, nothing else."""

    def test_default_maps_to_none(self):
        self.assertIsNone(pb.parse_threads("default"))

    def test_integer_values(self):
        self.assertEqual(pb.parse_threads("1"), 1)
        self.assertEqual(pb.parse_threads("4"), 4)

    def test_invalid_values_raise(self):
        for bad in ("0", "-1", "1.5", "DEFault", ""):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    pb.parse_threads(bad)


class TestCompareToBaseline(unittest.TestCase):
    """Locked speedup math: inclusive 1.0x / 1.2x, no noise band."""

    def setUp(self):
        self.baseline = make_synthetic_baseline(control_wall=12.0)

    def result(self, t1_wall, default_wall):
        return pb.compare_to_baseline(
            self.baseline, make_new_control_doc(t1_wall, default_wall))

    def test_threshold_equality_passes(self):
        result = self.result(12.0, 10.0)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["speedup_t1"], 1.0)
        self.assertEqual(result["speedup_default"], 1.2)
        self.assertEqual(result["baseline_wall_s"], 12.0)
        self.assertEqual(result["new_t1_wall_s"], 12.0)
        self.assertEqual(result["new_default_wall_s"], 10.0)
        self.assertEqual(result["min_speedup_t1"], 1.0)
        self.assertEqual(result["min_speedup_default"], 1.2)

    def test_one_ulp_below_t1_threshold_fails(self):
        self.assertEqual(
            self.result(12.000000000000002, 10.0)["result"], "FAIL")

    def test_one_ulp_below_default_threshold_fails(self):
        self.assertEqual(
            self.result(12.0, 10.000000000000002)["result"], "FAIL")

    def test_t1_regression_fails(self):
        self.assertEqual(self.result(13.0, 10.0)["result"], "FAIL")

    def test_default_below_threshold_fails(self):
        self.assertEqual(self.result(12.0, 10.5)["result"], "FAIL")

    def test_missing_arm_raises(self):
        doc = make_new_control_doc(12.0, 10.0)
        del doc["n_free_control"]["arms"][1]
        with self.assertRaises(ValueError):
            pb.compare_to_baseline(self.baseline, doc)

    def test_non_positive_median_raises(self):
        doc = make_new_control_doc(0.0, 10.0)
        with self.assertRaises(ValueError):
            pb.compare_to_baseline(self.baseline, doc)

    def test_baseline_arm_selected_by_identity_not_position(self):
        """A default-threads arm at index 0 must never become baseline_t1."""
        baseline = make_synthetic_baseline(control_wall=1.0)
        baseline["n_free_control"]["arms"] = [
            {"name": "py21-n-free-control-tdefault", "threads": "default",
             "medians": {"wall_s": 1.0}},
            {"name": "py21-n-free-control-t1", "threads": 1,
             "medians": {"wall_s": 12.0}},
        ]
        result = pb.compare_to_baseline(
            baseline, make_new_control_doc(12.0, 10.0))
        self.assertEqual(result["baseline_wall_s"], 12.0)
        self.assertEqual(result["result"], "PASS")

    def test_t1_named_arm_measured_at_default_threads_raises(self):
        """A '-t1' name with threads="default" is not a t1 comparison basis."""
        self.baseline["n_free_control"]["arms"][0]["threads"] = "default"
        with self.assertRaises(ValueError):
            self.result(12.0, 10.0)

    def test_t1_arm_without_threads_field_raises(self):
        del self.baseline["n_free_control"]["arms"][0]["threads"]
        with self.assertRaises(ValueError):
            self.result(12.0, 10.0)

    def test_two_t1_arms_are_ambiguous(self):
        arms = self.baseline["n_free_control"]["arms"]
        arms.append(dict(arms[0]))
        with self.assertRaises(ValueError):
            self.result(12.0, 10.0)


class TestBaselineIdentityGuards(unittest.TestCase):
    """Every cross-host/config mismatch is a ValueError (exit 2 upstream)."""

    def setUp(self):
        self.flavor = pb.baseline_filename(platform.system())[1]
        self.host = f"{sys.platform}-{platform.machine()}"

    def fresh(self):
        return make_synthetic_baseline(platform_flavor=self.flavor,
                                       provenance_platform=self.host)

    def check(self, baseline):
        return pb.validate_baseline_identity(
            baseline, self.flavor, self.host, 21, True)

    def test_valid_baseline_passes(self):
        self.check(self.fresh())

    def test_platform_flavor_mismatch_raises(self):
        baseline = self.fresh()
        baseline["platform"] = ("linux" if self.flavor == "darwin"
                                else "darwin")
        with self.assertRaises(ValueError):
            self.check(baseline)

    def test_provenance_platform_mismatch_raises(self):
        baseline = self.fresh()
        baseline["provenance"]["platform"] = "linux-x86_64"
        with self.assertRaises(ValueError):
            self.check(baseline)

    def test_k_mismatch_raises(self):
        baseline = self.fresh()
        baseline["params"]["k"] = 31
        with self.assertRaises(ValueError):
            self.check(baseline)

    def test_canonical_mismatch_raises(self):
        baseline = self.fresh()
        baseline["params"]["canonical"] = False
        with self.assertRaises(ValueError):
            self.check(baseline)

    def test_missing_fingerprint_sha_raises(self):
        baseline = self.fresh()
        baseline["n_free_control"]["input_fingerprint"]["sha256"] = ""
        with self.assertRaises(ValueError):
            self.check(baseline)

    def test_zero_exact_count_raises(self):
        baseline = self.fresh()
        baseline["n_free_control"]["exact_counts"]["total_kmers"] = 0
        with self.assertRaises(ValueError):
            self.check(baseline)

    def test_control_arm_measured_at_default_threads_raises(self):
        baseline = self.fresh()
        baseline["n_free_control"]["arms"][0]["threads"] = "default"
        with self.assertRaises(ValueError):
            self.check(baseline)

    def test_control_arm_missing_threads_field_raises(self):
        baseline = self.fresh()
        del baseline["n_free_control"]["arms"][0]["threads"]
        with self.assertRaises(ValueError):
            self.check(baseline)


class TestBuildBaseline(unittest.TestCase):
    """A slice-mode baseline without a parity-passing control is invalid."""

    def test_valid_baseline_carries_scope_basis_and_labels(self):
        doc = make_doc()
        baseline = pb.build_baseline(doc, make_control(), "darwin")
        validate_schema(baseline)
        validate_provenance(baseline)
        self.assertEqual(baseline["baseline_scope"],
                         "dev-host-local-comparison")
        self.assertEqual(baseline["comparison_basis"], "n-free-control")
        self.assertIn("M4 Max", baseline["host_class"])
        self.assertEqual(baseline["platform"], "darwin")
        self.assertEqual(baseline["arms"][0]["evidence_class"],
                         "timing-only-real-N-post-D2")
        self.assertIs(baseline["n_free_control"]["parity_control"]["equal"],
                      True)

    def test_missing_control_raises(self):
        with self.assertRaises(ValueError):
            pb.build_baseline(make_doc(), None, "darwin")

    def test_parity_not_equal_raises(self):
        control = make_control()
        control["parity_control"]["equal"] = False
        with self.assertRaises(ValueError):
            pb.build_baseline(make_doc(), control, "darwin")

    def test_zero_exact_counts_raise(self):
        control = make_control()
        control["exact_counts"] = {"total_kmers": 0, "unique_kmers": 0}
        with self.assertRaises(ValueError):
            pb.build_baseline(make_doc(), control, "darwin")

    def test_control_rep_identity_violation_raises(self):
        control = make_control(reps=[make_rep(total=101)])
        with self.assertRaises(ValueError):
            pb.build_baseline(make_doc(), control, "darwin")

    def test_control_arm_measured_at_default_threads_raises(self):
        """A baseline can never be emitted from a non-t1 control arm."""
        control = make_control()
        control["arms"][0]["threads"] = "default"
        with self.assertRaises(ValueError):
            pb.build_baseline(make_doc(), control, "darwin")

    def test_synthetic_mode_baseline_raises(self):
        with self.assertRaises(ValueError):
            pb.build_baseline(make_doc(mode="synthetic"), make_control(),
                              "darwin")


class ControllerHarness(unittest.TestCase):
    """Drive main(argv) with fake measure/stats — no PyO3, no sleeps."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.site = self.root / "site-packages"
        self.site.mkdir()
        self.module = self.site / "pyrustkmer.cpython-313-darwin.so"
        self.module.write_bytes(b"fake native bytes")
        self.info = {"executable": sys.executable, "version": "3.13.11",
                     "site_prefix": str(self.site)}
        self.out = self.root / "run.json"

    def run_main(self, argv, measure=None, cli=None, fingerprint_value=None,
                 filter_counts=None):
        patches = [
            mock.patch.object(pb, "interpreter_info", return_value=self.info),
            mock.patch.object(pb, "maturin_version",
                              return_value="maturin 1.11.5"),
            mock.patch.object(pb, "binary_provenance",
                              side_effect=fake_provenance),
            mock.patch.object(pb, "attempt_cache_purge",
                              return_value="unavailable"),
            mock.patch.object(pb, "measure",
                              side_effect=measure if measure is not None
                              else make_fake_measure(self.module)),
        ]
        if cli is not None:
            patches.append(mock.patch.object(pb, "cli_count_counts",
                                             return_value=cli))
        if fingerprint_value is not None:
            patches.append(mock.patch.object(
                pb, "fingerprint",
                return_value={"path": "mocked-input", "size_bytes": 10,
                              "sha256": fingerprint_value}))
        if filter_counts is not None:
            patches.append(mock.patch.object(pb, "filter_n_free",
                                             return_value=filter_counts))
        out, err = io.StringIO(), io.StringIO()
        with contextlib.ExitStack() as stack:
            for patch in patches:
                stack.enter_context(patch)
            stack.enter_context(contextlib.redirect_stdout(out))
            stack.enter_context(contextlib.redirect_stderr(err))
            try:
                code = pb.main(argv)
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def synthetic_argv(self, *extra):
        return ["--mode", "synthetic", "--reads", "50", "--reps", "3",
                "--cooldown-s", "0", "--python", sys.executable,
                "--out", str(self.out), *extra]

    def slice_argv(self, *extra):
        gz = build_gz_fixture(self.root / "source.fq.gz")
        return ["--mode", "slice", "--input", str(gz), "--slice-reads", "20",
                "--slice-seed", "7", "--reps", "3", "--cooldown-s", "0",
                "--python", sys.executable, "--rustkmer", sys.executable,
                "--out", str(self.out), *extra]


class TestSyntheticController(ControllerHarness):

    def test_valid_run_writes_schema_valid_doc_with_medians(self):
        code, out, err = self.run_main(self.synthetic_argv())
        self.assertEqual(code, 0, err)
        doc = json.loads(self.out.read_text())
        validate_schema(doc)
        validate_provenance(doc)
        arm = doc["arms"][0]
        # Fake walls: warmup 1.0, reps 2.0/3.0/4.0 -> median 3.0.
        self.assertEqual(arm["medians"]["wall_s"], 3.0)
        self.assertEqual(len(arm["reps"]), 3)
        for rep in arm["reps"]:
            self.assertEqual(rep["cache_state"], "unavailable")
            self.assertEqual(rep["total_kmers"], 100)
            self.assertEqual(rep["unique_kmers"], 90)
        self.assertEqual(len(doc["provenance"]["module"]["sha256"]), 64)
        self.assertEqual(doc["provenance"]["maturin_version"],
                         "maturin 1.11.5")

    def test_zero_count_worker_exits_2(self):
        code, _, err = self.run_main(
            self.synthetic_argv(),
            measure=make_fake_measure(self.module, total=0, unique=0))
        self.assertEqual(code, 2)
        self.assertIn("zero", err)
        self.assertFalse(self.out.exists())

    def test_shadowed_module_exits_2(self):
        outside = self.root / "elsewhere" / "pyrustkmer.so"
        code, _, err = self.run_main(
            self.synthetic_argv(), measure=make_fake_measure(outside))
        self.assertEqual(code, 2)
        self.assertIn("site-packages", err)

    def test_cross_rep_count_disagreement_exits_2(self):
        code, _, err = self.run_main(
            self.synthetic_argv(),
            measure=make_fake_measure(self.module, vary=True))
        self.assertEqual(code, 2)
        self.assertIn("disagreement", err)

    def test_missing_stats_file_exits_2(self):
        code, _, err = self.run_main(
            self.synthetic_argv(),
            measure=make_fake_measure(self.module, write_stats=False))
        self.assertEqual(code, 2)
        self.assertIn("stats", err)

    def test_synthetic_emit_baseline_exits_2(self):
        code, _, err = self.run_main(
            self.synthetic_argv("--emit-baseline",
                                str(self.root / "python_bench_baseline.darwin.json")))
        self.assertEqual(code, 2)
        self.assertIn("slice-mode", err)

    def test_binding_ignoring_threads_exits_2(self):
        """A PyCounter that ignores --threads is never a valid measurement."""
        code, _, err = self.run_main(
            self.synthetic_argv(),
            measure=make_fake_measure(self.module, threads_resolved=16))
        self.assertEqual(code, 2)
        self.assertIn("thread", err)
        self.assertFalse(self.out.exists())


class TestSliceController(ControllerHarness):

    def baseline_path(self):
        name, _ = pb.baseline_filename(platform.system())
        return self.root / name

    def test_slice_run_with_parity_and_baseline(self):
        baseline = self.baseline_path()
        code, out, err = self.run_main(
            self.slice_argv("--emit-baseline", str(baseline)),
            cli={"unique_kmers": 90, "total_kmers": 100})
        self.assertEqual(code, 0, err)
        self.assertIn("control parity OK", out)
        doc = json.loads(self.out.read_text())
        validate_schema(doc)
        validate_provenance(doc)
        control = doc["n_free_control"]
        self.assertIs(control["parity_control"]["equal"], True)
        self.assertEqual(control["kept_reads"] + control["dropped_reads"], 20)
        self.assertGreater(control["dropped_reads"], 0)
        self.assertEqual(doc["arms"][0]["evidence_class"],
                         "timing-only-real-N-post-D2")
        self.assertIn("semantics_note", doc["arms"][0])
        # The committed baseline envelope.
        base = json.loads(baseline.read_text())
        validate_schema(base)
        validate_provenance(base)
        self.assertEqual(base["baseline_scope"], "dev-host-local-comparison")
        self.assertEqual(base["comparison_basis"], "n-free-control")
        self.assertIn("M4 Max", base["host_class"])
        self.assertEqual(len(base["provenance"]["module"]["sha256"]), 64)
        exact = base["n_free_control"]["exact_counts"]
        for arm in base["n_free_control"]["arms"]:
            for rep in arm["reps"]:
                self.assertEqual(rep["total_kmers"], exact["total_kmers"])
                self.assertEqual(rep["unique_kmers"], exact["unique_kmers"])

    def test_control_parity_mismatch_exits_2_before_baseline(self):
        baseline = self.baseline_path()
        code, _, err = self.run_main(
            self.slice_argv("--emit-baseline", str(baseline)),
            cli={"unique_kmers": 91, "total_kmers": 100})
        self.assertEqual(code, 2)
        self.assertIn("parity mismatch", err)
        self.assertFalse(baseline.exists())
        self.assertFalse(self.out.exists())

    def test_wrong_platform_baseline_name_exits_2(self):
        name, _ = pb.baseline_filename(platform.system())
        other = ("python_bench_baseline.linux.json" if name.endswith(
            "darwin.json") else "python_bench_baseline.darwin.json")
        code, _, err = self.run_main(
            self.slice_argv("--emit-baseline", str(self.root / other)),
            cli={"unique_kmers": 90, "total_kmers": 100})
        self.assertEqual(code, 2)
        self.assertIn("filename", err)

    def test_slice_without_input_exits_2(self):
        code, _, err = self.run_main(
            ["--mode", "slice", "--python", sys.executable,
             "--out", str(self.out)])
        self.assertEqual(code, 2)
        self.assertIn("--input", err)

    def test_emit_baseline_requires_one_thread(self):
        """--emit-baseline must never label a non-t1 arm as the t1 basis."""
        for threads in ("default", "4"):
            with self.subTest(threads=threads):
                baseline = self.baseline_path()
                code, _, err = self.run_main(
                    self.slice_argv("--threads", threads,
                                    "--emit-baseline", str(baseline)),
                    cli={"unique_kmers": 90, "total_kmers": 100})
                self.assertEqual(code, 2)
                self.assertIn("--threads 1", err)
                self.assertFalse(baseline.exists())
                self.assertFalse(self.out.exists())

    def test_non_compare_arm_names_follow_actual_threads(self):
        """Arm names derive from the measured configuration, not a literal."""
        code, _, err = self.run_main(
            self.slice_argv("--threads", "4"),
            cli={"unique_kmers": 90, "total_kmers": 100})
        self.assertEqual(code, 0, err)
        doc = json.loads(self.out.read_text())
        control_arm = doc["n_free_control"]["arms"][0]
        self.assertTrue(control_arm["name"].endswith("-n-free-control-t4"))
        self.assertEqual(control_arm["threads"], 4)
        self.assertTrue(doc["arms"][0]["name"].endswith("-real-n-t4"))
        self.assertEqual(doc["arms"][0]["threads"], 4)


class TestCompareController(ControllerHarness):
    """--compare-baseline through main(): exit 0/1/2 and artifact policy.

    The fake measure's wall times are 1.0 + call index, so with --reps 3 the
    t1 arm's measured reps are 3/4/5 s (median 4.0) and the default arm's
    are 7/8/9 s (median 8.0). A baseline control median of 12.0 therefore
    yields speedups 3.0 / 1.5 (PASS); 8.0 yields 2.0 / 1.0 (default FAIL).
    """

    CONTROL_SHA = "e" * 64
    FILTER = {"kept_reads": 15, "dropped_reads": 5}

    def write_baseline(self, **over):
        kwargs = {"control_sha": self.CONTROL_SHA}
        kwargs.update(over)
        doc = make_synthetic_baseline(**kwargs)
        path = self.root / "baseline.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        return path

    def compare_argv(self, baseline_path, *extra):
        return self.slice_argv("--compare-baseline", str(baseline_path),
                               *extra)

    def run_compare(self, baseline_path, cli=None):
        return self.run_main(
            self.compare_argv(baseline_path),
            cli=(cli if cli is not None
                 else {"unique_kmers": 90, "total_kmers": 100}),
            fingerprint_value=self.CONTROL_SHA,
            filter_counts=dict(self.FILTER))

    def test_pass_writes_valid_doc_and_exits_0(self):
        baseline = self.write_baseline(control_wall=12.0)
        code, out, err = self.run_compare(baseline)
        self.assertEqual(code, 0, err)
        doc = json.loads(self.out.read_text())
        validate_schema(doc)
        validate_provenance(doc)
        self.assertEqual(doc["mode"], "compare-baseline")
        self.assertEqual([a["name"] for a in doc["arms"]],
                         ["py21-n-free-control-t1",
                          "py21-n-free-control-tdefault"])
        self.assertEqual([a["threads"] for a in doc["arms"]], [1, "default"])
        self.assertEqual(doc["comparison"]["result"], "PASS")
        self.assertEqual(doc["comparison"]["speedup_t1"], 3.0)
        self.assertEqual(doc["comparison"]["speedup_default"], 1.5)
        self.assertEqual(doc["verdict"], {"result": "PASS", "exit_code": 0})
        self.assertEqual(doc["baseline"]["control_wall_s"], 12.0)
        self.assertEqual(doc["baseline"]["sha256"], self.CONTROL_SHA)
        self.assertEqual(doc["params"]["compare_baseline"], str(baseline))
        self.assertEqual(doc["params"]["threads_default"], "default")
        control = doc["n_free_control"]
        self.assertEqual(control["kept_reads"], 15)
        self.assertEqual(control["dropped_reads"], 5)
        self.assertEqual(len(control["arms"]), 2)
        self.assertIs(control["parity_control"]["equal"], True)
        for arm in doc["arms"]:
            self.assertNotEqual(arm.get("evidence_class"),
                                pb.REAL_N_EVIDENCE_CLASS)
        self.assertIn("COMPARISON VERDICT result=PASS", out)

    def test_fail_exits_1_and_keeps_artifact(self):
        baseline = self.write_baseline(control_wall=8.0)
        code, out, err = self.run_compare(baseline)
        self.assertEqual(code, 1, err)
        self.assertTrue(self.out.is_file())
        doc = json.loads(self.out.read_text())
        validate_schema(doc)
        validate_provenance(doc)
        self.assertEqual(doc["comparison"]["result"], "FAIL")
        self.assertEqual(doc["comparison"]["speedup_t1"], 2.0)
        self.assertEqual(doc["comparison"]["speedup_default"], 1.0)
        self.assertEqual(doc["verdict"], {"result": "FAIL", "exit_code": 1})
        self.assertIn("COMPARISON VERDICT result=FAIL", out)

    def test_wrong_platform_baseline_exits_2_without_artifact(self):
        other = ("linux" if pb.baseline_filename(platform.system())[1]
                 == "darwin" else "darwin")
        baseline = self.write_baseline(platform_flavor=other)
        code, _, err = self.run_compare(baseline)
        self.assertEqual(code, 2)
        self.assertIn("platform", err)
        self.assertFalse(self.out.exists())

    def test_exact_count_mismatch_exits_2_without_artifact(self):
        baseline = self.write_baseline(
            exact={"total_kmers": 101, "unique_kmers": 90})
        code, _, err = self.run_compare(baseline)
        self.assertEqual(code, 2)
        self.assertIn("exact counts", err)
        self.assertFalse(self.out.exists())

    def test_control_fingerprint_mismatch_exits_2_without_artifact(self):
        baseline = self.write_baseline(control_sha="f" * 64)
        code, _, err = self.run_compare(baseline)
        self.assertEqual(code, 2)
        self.assertIn("fingerprint", err)
        self.assertFalse(self.out.exists())

    def test_missing_baseline_file_exits_2_without_artifact(self):
        code, _, err = self.run_compare(self.root / "absent-baseline.json")
        self.assertEqual(code, 2)
        self.assertIn("not found", err)
        self.assertFalse(self.out.exists())

    def test_unparseable_baseline_exits_2_without_artifact(self):
        baseline = self.root / "broken-baseline.json"
        baseline.write_text("{ not json", encoding="utf-8")
        code, _, err = self.run_compare(baseline)
        self.assertEqual(code, 2)
        self.assertFalse(self.out.exists())

    def test_compare_requires_slice_mode(self):
        baseline = self.write_baseline()
        code, _, err = self.run_main(
            self.synthetic_argv("--compare-baseline", str(baseline)),
            cli={"unique_kmers": 90, "total_kmers": 100},
            fingerprint_value=self.CONTROL_SHA,
            filter_counts=dict(self.FILTER))
        self.assertEqual(code, 2)
        self.assertIn("slice", err)
        self.assertFalse(self.out.exists())

    def test_compare_and_emit_baseline_are_mutually_exclusive(self):
        baseline = self.write_baseline()
        name, _ = pb.baseline_filename(platform.system())
        code, _, err = self.run_main(
            self.compare_argv(baseline, "--emit-baseline",
                              str(self.root / name)),
            cli={"unique_kmers": 90, "total_kmers": 100},
            fingerprint_value=self.CONTROL_SHA,
            filter_counts=dict(self.FILTER))
        self.assertEqual(code, 2)
        self.assertIn("mutually exclusive", err)
        self.assertFalse(self.out.exists())

    def test_compare_rejects_non_default_threads(self):
        """--threads must never be a silent no-op in compare mode (WR-02)."""
        baseline = self.write_baseline()
        code, _, err = self.run_main(
            self.compare_argv(baseline, "--threads", "4"),
            cli={"unique_kmers": 90, "total_kmers": 100},
            fingerprint_value=self.CONTROL_SHA,
            filter_counts=dict(self.FILTER))
        self.assertEqual(code, 2)
        self.assertIn("--threads", err)
        self.assertFalse(self.out.exists())


@unittest.skipUnless(
    os.environ.get("RUSTKMER_PYBENCH_VENV"),
    "opt-in: RUSTKMER_PYBENCH_VENV must point at the freshly built venv")
class TestRealWorkerIntegration(unittest.TestCase):
    """Real fresh-worker run against the rebuilt extension (env-gated)."""

    def test_module_sha_provenance_and_nonzero_counts(self):
        venv = Path(os.environ["RUSTKMER_PYBENCH_VENV"]).resolve()
        python = venv / "bin" / "python"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run.json"
            proc = subprocess.run(
                [sys.executable, str(pb.THIS_FILE), "--python", str(python),
                 "--mode", "synthetic", "--reads", "200", "--reps", "1",
                 "--cooldown-s", "0", "--out", str(out)],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            doc = json.loads(out.read_text())
            validate_schema(doc)
            validate_provenance(doc)
            module = doc["provenance"]["module"]
            self.assertEqual(len(module["sha256"]), 64)
            self.assertEqual(module["sha256"],
                             pb.fingerprint(module["path"])["sha256"])
            self.assertTrue(
                Path(module["path"]).resolve().is_relative_to(venv))
            arm = doc["arms"][0]
            self.assertGreater(arm["total_kmers"], 0)
            self.assertGreater(arm["unique_kmers"], 0)


class TestWorkerArgumentGate(unittest.TestCase):
    """The Phase-10 worker argv must reach run_worker unflattened.

    The pre-Phase-10 gate rejected every invocation without `--input`; the
    both-parts arm passes repeatable `--inputs` flags instead, so the gate
    must accept that shape while still rejecting a worker with no input
    source and no stats destination.
    """

    def test_repeatable_inputs_reach_run_worker(self):
        p1 = "/data/part_001.fq.gz"
        p2 = "/data/part_006.fq.gz"
        stats_out = "/tmp/phase10/worker.stats.json"
        with mock.patch.object(pb, "run_worker", return_value=0) as worker:
            rc = pb.main(["--worker", "--inputs", p1, "--inputs", p2,
                          "--k", "21", "--threads", "16",
                          "--stats-out", stats_out])
        self.assertEqual(rc, 0)
        args = worker.call_args[0][0]
        self.assertEqual(args.inputs, [p1, p2])
        self.assertIsNone(args.input)

    def test_worker_without_input_source_exits_2(self):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            with mock.patch.object(pb, "run_worker") as worker:
                with self.assertRaises(SystemExit) as caught:
                    pb.main(["--worker", "--k", "21",
                             "--stats-out", "/tmp/x.stats.json"])
        self.assertEqual(caught.exception.code, pb.EXIT_INVALID)
        self.assertIn("--inputs", err.getvalue())
        worker.assert_not_called()

    def test_worker_without_stats_out_exits_2(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with mock.patch.object(pb, "run_worker") as worker:
                with self.assertRaises(SystemExit) as caught:
                    pb.main(["--worker", "--inputs", "/data/part_001.fq.gz"])
        self.assertEqual(caught.exception.code, pb.EXIT_INVALID)
        worker.assert_not_called()


if __name__ == "__main__":
    unittest.main()