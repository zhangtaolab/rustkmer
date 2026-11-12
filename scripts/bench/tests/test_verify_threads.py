"""Unit tests for the hardened PROF-02 thread observer (05-03).

Pins the fail-loud exit contract of
`.planning/research/profiling/verify_threads.py` WITHOUT needing a live
rustkmer binary or an OS sampler:

  * invalid inputs (nonexistent --binary/--input, zero --threads,
    nonpositive --timeout-s) must exit 2 and print NO `THREAD REALITY`
    verdict line — an invalid run is never a verdict, and an uncaught
    exception must never masquerade as the expected-RED observation
    (the 05-01 exit-code discipline: 0 = measured GREEN, 1 = measured
    RED, 2 = invalid/infra);
  * the platform backend selection is explicit: macOS `sample`, Linux
    `proc-task`, anything else `unsupported` (exit 2, never a false PASS).

The live observation path (exit 0/1 + structured records + per-N
`requested=<N> observed=<M>` stdout lines) is covered by
`tests/thread_pool_size_tests.rs` and the freshness-bound evidence
capture in 05-03-PLAN.md — not re-tested here.

Stdlib unittest only — no pytest, no conftest, no sleeps.
"""

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HELPER = REPO_ROOT / ".planning" / "research" / "profiling" / "verify_threads.py"


def load_helper_module():
    """Import the helper by path (it lives outside the scripts package)."""
    spec = importlib.util.spec_from_file_location("verify_threads_under_test", HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestExitContract(unittest.TestCase):
    """Invalid inputs exit 2 with no verdict line — never a false PASS."""

    def run_helper(self, *args):
        """Run the helper as a real subprocess (list form, no shell)."""
        return subprocess.run(
            [sys.executable, str(HELPER), *args],
            capture_output=True,
            text=True,
            timeout=180,
        )

    def assert_invalid(self, proc):
        """The shared exit-2 contract: code 2 and no verdict line anywhere."""
        self.assertEqual(
            proc.returncode,
            2,
            f"invalid input must exit 2, got {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}",
        )
        self.assertNotIn(
            "THREAD REALITY",
            proc.stdout,
            "exit-2 paths must print no verdict line",
        )

    def test_invalid_binary_exits_2_without_verdict(self):
        """A nonexistent --binary is invalid input: exit 2, no verdict."""
        with tempfile.TemporaryDirectory() as td:
            proc = self.run_helper(
                "--binary", str(Path(td) / "no-such-binary"),
                "--input", str(Path(td) / "no-such.fq"),
                "--threads", "1",
                "--json", str(Path(td) / "records.json"),
            )
            self.assert_invalid(proc)

    def test_zero_threads_exits_2(self):
        """--threads 0 is not a pool size: exit 2 before any observation."""
        with tempfile.TemporaryDirectory() as td:
            proc = self.run_helper(
                "--binary", str(Path(td) / "no-such-binary"),
                "--input", str(Path(td) / "no-such.fq"),
                "--threads", "0",
                "--json", str(Path(td) / "records.json"),
            )
            self.assert_invalid(proc)

    def test_nonpositive_timeout_exits_2(self):
        """--timeout-s 0 cannot bound an observation: exit 2."""
        with tempfile.TemporaryDirectory() as td:
            proc = self.run_helper(
                "--binary", str(Path(td) / "no-such-binary"),
                "--input", str(Path(td) / "no-such.fq"),
                "--threads", "1",
                "--timeout-s", "0",
                "--json", str(Path(td) / "records.json"),
            )
            self.assert_invalid(proc)


class TestSamplerSelection(unittest.TestCase):
    """Backend selection is a pure, explicit platform decision."""

    def test_backends_are_explicit(self):
        mod = load_helper_module()
        self.assertEqual(mod.sampler_for("Darwin"), "sample")
        self.assertEqual(mod.sampler_for("Linux"), "proc-task")
        self.assertEqual(mod.sampler_for("Windows"), "unsupported")


if __name__ == "__main__":
    unittest.main()
