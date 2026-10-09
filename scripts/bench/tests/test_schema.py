"""Unit tests for the results.json schema contract (BENCH-03).

Every rep must carry BOTH wall_s and peak_rss_bytes — this is the contract
04-03's compare.py and 04-04's report consume via the same validate_schema.
Stdlib unittest only — no pytest, no conftest.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.bench.bench import validate_schema

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


if __name__ == "__main__":
    unittest.main()
