"""Unit tests for the results.json schema contract (BENCH-03).

Every rep must carry BOTH wall_s and peak_rss_bytes — this is the contract
04-03's compare.py and 04-04's report consume via the same validate_schema.
Stdlib unittest only — no pytest, no conftest.

05-01 extension: provenance-specific fixtures and tests for the PROF-01
strict validator (validate_provenance) — the original minimal v1 fixture
below is UNCHANGED, proving committed baselines still load under
validate_schema (SCHEMA_VERSION stays 1).
"""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.bench.bench import (
    SCHEMA_VERSION,
    validate_provenance,
    validate_schema,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCH = REPO_ROOT / "scripts" / "bench" / "bench.py"
RUSTKMER = REPO_ROOT / "target" / "release" / "rustkmer"


class TestRealSelfCheckOutput(unittest.TestCase):
    """The real self-check's emitted results.json satisfies the schema."""

    def test_real_self_check_results_pass_validation(self):
        """A small real self-check run passes validate_schema untouched."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "results.json"
            proc = subprocess.run(
                [sys.executable, str(BENCH), "--mode", "synthetic",
                 "--reads", "5000", "--self-check", "--out", str(out),
                 "--rustkmer", str(RUSTKMER)],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            results = json.loads(out.read_text())
            validate_schema(results)  # must not raise
            # And every rep of every arm carries BOTH metric fields.
            for arm in results["arms"]:
                for rep in arm["reps"]:
                    self.assertIn("wall_s", rep)
                    self.assertIn("peak_rss_bytes", rep)


class TestValidateSchemaRejections(unittest.TestCase):
    """Malformed results dicts must raise, never pass silently."""

    def _minimal_results(self):
        return {
            "schema_version": 1,
            "arms": [{
                "name": "count-A",
                "tool": "rustkmer",
                "reps": [{"wall_s": 1.0, "peak_rss_bytes": 123}],
                "distinct_kmers": 1,
                "total_kmers": 1,
            }],
        }

    def test_minimal_valid_results_pass(self):
        """A minimal well-formed results dict validates without raising."""
        validate_schema(self._minimal_results())

    def test_missing_schema_version_raises(self):
        """Omitting schema_version raises."""
        d = self._minimal_results()
        del d["schema_version"]
        with self.assertRaises(ValueError):
            validate_schema(d)

    def test_rep_missing_peak_rss_raises(self):
        """A rep missing peak_rss_bytes raises (BENCH-03 contract)."""
        d = self._minimal_results()
        d["arms"][0]["reps"][0] = {"wall_s": 1.0}
        with self.assertRaises(ValueError):
            validate_schema(d)

    def test_rep_missing_wall_s_raises(self):
        """A rep missing wall_s raises."""
        d = self._minimal_results()
        d["arms"][0]["reps"][0] = {"peak_rss_bytes": 123}
        with self.assertRaises(ValueError):
            validate_schema(d)

    def test_empty_arms_raises(self):
        """An empty arms list raises (a zero-rep results file is a failure)."""
        d = self._minimal_results()
        d["arms"] = []
        with self.assertRaises(ValueError):
            validate_schema(d)


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


class TestProvenanceValidation(unittest.TestCase):
    """PROF-01 strict provenance gate: one mutated field per rejection test
    (the existing validate_schema rejection style), each naming the field."""

    def _doc(self):
        return {"provenance": make_provenance()}

    def test_full_provenance_passes(self):
        """A doc with a complete binary_provenance block validates."""
        validate_provenance(self._doc())  # must not raise

    def test_missing_provenance_raises(self):
        """A doc with no provenance block raises naming 'provenance'."""
        d = self._doc()
        del d["provenance"]
        with self.assertRaisesRegex(ValueError, "provenance"):
            validate_provenance(d)

    def test_empty_sha256_raises(self):
        """An empty binary.sha256 raises naming 'sha256' (path-only is not
        provenance — T-05-02)."""
        d = self._doc()
        d["provenance"]["binary"]["sha256"] = ""
        with self.assertRaisesRegex(ValueError, "sha256"):
            validate_provenance(d)

    def test_non_hex_sha256_raises(self):
        """A non-hex binary.sha256 raises naming 'sha256'."""
        d = self._doc()
        d["provenance"]["binary"]["sha256"] = "z" * 64
        with self.assertRaisesRegex(ValueError, "sha256"):
            validate_provenance(d)

    def test_wrong_typed_git_dirty_raises(self):
        """A string git_dirty raises naming 'git_dirty' (must be a bool)."""
        d = self._doc()
        d["provenance"]["git_dirty"] = "false"
        with self.assertRaisesRegex(ValueError, "git_dirty"):
            validate_provenance(d)

    def test_missing_build_profile_raises(self):
        """A missing build_profile raises naming 'build_profile'."""
        d = self._doc()
        del d["provenance"]["build_profile"]
        with self.assertRaisesRegex(ValueError, "build_profile"):
            validate_provenance(d)


class TestLegacyBaselineCompatibility(unittest.TestCase):
    """SCHEMA_VERSION stays 1: committed v1 baselines (no provenance block)
    still load under the UNCHANGED validate_schema."""

    def test_committed_darwin_baseline_still_loads(self):
        """The committed per-platform baseline passes validate_schema."""
        baseline = (REPO_ROOT / "scripts" / "bench" / "baselines"
                    / "bench_baseline.darwin.json")
        validate_schema(json.loads(baseline.read_text()))  # must not raise


class TestRealRunProvenance(unittest.TestCase):
    """The emitted provenance identifies the ACTUAL binary bytes — not the
    string supplied on the command line (analogous to the real self-check
    assertion above)."""

    def test_real_run_provenance_hashes_actual_binary(self):
        """A small real synthetic run emits provenance whose sha256 equals
        a freshly computed hashlib.sha256 of target/release/rustkmer."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "results.json"
            proc = subprocess.run(
                [sys.executable, str(BENCH), "--mode", "synthetic",
                 "--reads", "5000", "--self-check", "--out", str(out),
                 "--rustkmer", str(RUSTKMER)],
                capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            results = json.loads(out.read_text())
            validate_provenance(results)  # must not raise
            expected = hashlib.sha256(RUSTKMER.read_bytes()).hexdigest()
            self.assertEqual(results["provenance"]["binary"]["sha256"],
                             expected)


class TestSevenArmSchemaTolerance(unittest.TestCase):
    """MBENCH-01: the seven-arm comparison shape rides schema v1 unchanged.

    The new merge arm names (merge-t1, jellyfish-count-B, jellyfish-merge)
    are entries in the existing arms list — validate_schema is name-tolerant,
    so no second results schema exists (SCHEMA_VERSION stays 1).
    """

    ARM_NAMES = ("count-A", "count-B", "merge", "merge-t1",
                 "jellyfish-count-A", "jellyfish-count-B", "jellyfish-merge")

    def _seven_arm_results(self):
        """A well-formed results dict carrying all seven arm names."""
        arms = []
        for name in self.ARM_NAMES:
            tool = "jellyfish" if name.startswith("jellyfish") else "rustkmer"
            arms.append({
                "name": name,
                "tool": tool,
                "reps": [{"wall_s": 1.0, "peak_rss_bytes": 123}],
                "distinct_kmers": 1,
                "total_kmers": 1,
            })
        return {"schema_version": SCHEMA_VERSION, "arms": arms}

    def test_seven_arm_results_validate_unchanged(self):
        """All seven arm names pass validate_schema with no schema fork."""
        validate_schema(self._seven_arm_results())  # must not raise

    def test_schema_version_stays_1(self):
        """SCHEMA_VERSION is still 1 — no second results schema (MBENCH-05)."""
        self.assertEqual(SCHEMA_VERSION, 1)


if __name__ == "__main__":
    unittest.main()
