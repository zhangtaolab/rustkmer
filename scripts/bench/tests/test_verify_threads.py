"""Unit and negative-control tests for the PROF-02 thread observer (05-03/07-02).

Pins the fail-loud exit contract of
`.planning/research/profiling/verify_threads.py` WITHOUT needing a live
rustkmer binary or an OS sampler for the unit-level cases:

  * `expected_total(n)` is the exact engine formula: 2 at N=1, 2N+1 for N>1;
  * `verdict_for_records` turns RED on the pre-engine `observed = requested+1`
    model and GREEN on the exact 2N+1 records;
  * `observe` polls THROUGH the rayon-only N+1 intermediate state to the
    expected total, returns an over-count immediately (measured RED), returns
    the last observation when the child exits below the expectation (measured
    RED, not exit 2), and raises `ObservationError` only when the child was
    never observed or the window expires with the child alive;
  * invalid inputs (nonexistent --binary/--input, zero --threads,
    nonpositive --timeout-s) must exit 2 and print NO `THREAD REALITY`
    verdict line — an invalid run is never a verdict;
  * the platform backend selection is explicit: macOS `sample`, Linux
    `proc-task`, anything else `unsupported` (exit 2, never a false PASS);
  * end-to-end negative controls run the real helper against small stub
    binaries: a stub that holds N+1 OS threads must produce a measured RED
    (exit 1, observed=5, requested=4, child_returncode=0), and a stub that
    exits immediately before any sample must produce exit 2 with no verdict
    and no JSON.

Stdlib unittest only — no pytest, no conftest.
"""

import importlib.util
import json
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
HELPER = REPO_ROOT / ".planning" / "research" / "profiling" / "verify_threads.py"


def load_helper_module():
    """Import the helper by path (it lives outside the scripts package)."""
    spec = importlib.util.spec_from_file_location("verify_threads_under_test", HELPER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeProc:
    """Minimal subprocess stand-in: `poll()` is None while alive."""

    def __init__(self, pid=4242, returncode=None):
        self.pid = pid
        self.returncode = returncode

    def poll(self):
        return self.returncode


class TestExpectedTotal(unittest.TestCase):
    """The engine's exact OS thread formula — hard equality, never a range."""

    def test_expected_total_is_exact(self):
        mod = load_helper_module()
        self.assertEqual(mod.expected_total(1), 2)
        self.assertEqual(mod.expected_total(4), 9)
        self.assertEqual(mod.expected_total(16), 33)

    def test_expected_total_rejects_zero(self):
        mod = load_helper_module()
        with self.assertRaises(ValueError):
            mod.expected_total(0)


class TestVerdict(unittest.TestCase):
    """GREEN only when every record matches the exact 2N+1 / 2 formula."""

    def test_exact_engine_records_are_green(self):
        mod = load_helper_module()
        records = [
            {"requested": 1, "observed": 2},
            {"requested": 4, "observed": 9},
            {"requested": 16, "observed": 33},
        ]
        self.assertEqual(mod.verdict_for_records(records), "GREEN")

    def test_pre_engine_n_plus_one_records_are_red(self):
        mod = load_helper_module()
        records = [{"requested": 4, "observed": 5}]
        self.assertEqual(mod.verdict_for_records(records), "RED")

    def test_any_mismatch_is_red(self):
        mod = load_helper_module()
        records = [
            {"requested": 1, "observed": 2},
            {"requested": 4, "observed": 8},
        ]
        self.assertEqual(mod.verdict_for_records(records), "RED")


class TestObservePolling(unittest.TestCase):
    """The sampler must poll through the intermediate N+1 state."""

    def test_intermediate_sample_is_never_accepted(self):
        mod = load_helper_module()
        proc = FakeProc()
        with mock.patch.object(mod, "_thread_count", side_effect=[5, 9]) as counter:
            observed = mod.observe(proc, 5.0, "proc-task", 9)
        self.assertEqual(observed, 9)
        self.assertEqual(counter.call_count, 2, "the 5-thread sample must not be returned")

    def test_over_count_is_returned_immediately_as_measured(self):
        mod = load_helper_module()
        proc = FakeProc()
        with mock.patch.object(mod, "_thread_count", return_value=10):
            observed = mod.observe(proc, 5.0, "proc-task", 9)
        self.assertEqual(observed, 10, "an over-count must become a measured mismatch")

    def test_below_expected_child_exit_returns_last_observation(self):
        mod = load_helper_module()
        proc = FakeProc(returncode=0)
        with mock.patch.object(mod, "_thread_count", return_value=5):
            observed = mod.observe(proc, 5.0, "proc-task", 9)
        self.assertEqual(
            observed,
            5,
            "a child that exits below the expectation after a sample is a measured RED, "
            "not an unobservable exit 2",
        )


class TestObserveTerminal(unittest.TestCase):
    """Exit-2 boundaries: never observed, or timeout with a live child."""

    def test_child_exiting_before_any_sample_is_observation_error(self):
        mod = load_helper_module()
        proc = FakeProc(returncode=0)
        with mock.patch.object(mod, "_thread_count", return_value=None):
            with self.assertRaises(mod.ObservationError):
                mod.observe(proc, 5.0, "proc-task", 9)

    def test_timeout_with_live_child_is_observation_error(self):
        mod = load_helper_module()
        proc = FakeProc(returncode=None)
        with mock.patch.object(mod, "_thread_count", return_value=5):
            with self.assertRaises(mod.ObservationError):
                mod.observe(proc, 0.2, "proc-task", 9)


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


class TestThreadCountParsing(unittest.TestCase):
    """`sample` output parsing counts OS threads, never text lines."""

    def test_duplicate_main_thread_header_is_counted_once(self):
        """A `Thread_<tid>: Main Thread` summary plus its section header is one thread."""
        mod = load_helper_module()
        text = (
            "Call graph:\n"
            "    136 Thread_18895681: Main Thread\n"
            "    + 133 _dyld_start  (in dyld) + 0\n"
            "    618 Thread_18895681   DispatchQueue_1: com.apple.main-thread  (serial)\n"
            "    + 618 start  (in dyld) + 6992\n"
            "    617 Thread_18895775\n"
        )
        self.assertEqual(mod.parse_thread_count(text), 2)

    def test_distinct_threads_are_counted(self):
        """One section header per thread yields the thread count."""
        mod = load_helper_module()
        text = (
            "Call graph:\n"
            "    618 Thread_100   DispatchQueue_1: com.apple.main-thread  (serial)\n"
            "    617 Thread_101\n"
            "    616 Thread_102\n"
            "    615 Thread_103\n"
        )
        self.assertEqual(mod.parse_thread_count(text), 4)


class TestThreadCountTransient(unittest.TestCase):
    """A zero-thread sample report is a transient artifact, never evidence."""

    def test_zero_thread_report_is_retried(self):
        """A header-only sample report parses to 0 and must be retried (None)."""
        mod = load_helper_module()
        report = subprocess.CompletedProcess(
            args=["sample", "4242", "1"],
            returncode=0,
            stdout=(
                "Analysis of sampling process 4242 every 1 millisecond\n"
                "Call graph:\n"
                "Total number in stack (recursive counted multiple, when >=5):\n"
            ),
        )
        with mock.patch.object(mod.subprocess, "run", return_value=report):
            self.assertIsNone(
                mod._thread_count(4242, "sample"),
                "a successful sample with no thread lines must be retried, "
                "never recorded as a zero-thread observation",
            )

    def test_nonzero_thread_report_is_returned(self):
        """A report with real thread sections still returns the true count."""
        mod = load_helper_module()
        report = subprocess.CompletedProcess(
            args=["sample", "4242", "1"],
            returncode=0,
            stdout=(
                "Call graph:\n"
                "    618 Thread_100   DispatchQueue_1: com.apple.main-thread  (serial)\n"
                "    617 Thread_101\n"
            ),
        )
        with mock.patch.object(mod.subprocess, "run", return_value=report):
            self.assertEqual(mod._thread_count(4242, "sample"), 2)


# --- End-to-end negative controls against real child processes --------------

# Holds the PRE-ENGINE thread model (main + N sleeping threads = N+1) and
# exits 0 on its own after a bounded interval well inside the helper timeout.
# `os._exit` terminates the process without Python's interpreter shutdown, so
# there is no teardown window in which daemon threads disappear while the main
# thread still runs — the last successful sample is the honest 5-thread state.
PRE_ENGINE_STUB = """#!/usr/bin/env python3
import os
import sys
import threading
import time


def requested(argv):
    for index, arg in enumerate(argv):
        if arg == "--threads" and index + 1 < len(argv):
            return int(argv[index + 1])
    return 1


count = requested(sys.argv)


def hold():
    # Outlive the main thread so the N+1 thread state is stable until the
    # abrupt `os._exit`; daemon threads die with the process.
    time.sleep(30)


for _ in range(count):
    threading.Thread(target=hold, daemon=True).start()

time.sleep(6.0)
os._exit(0)
"""


@unittest.skipUnless(
    platform.system() in ("Darwin", "Linux"),
    "thread observation needs macOS sample or Linux /proc",
)
class TestNegativeControls(unittest.TestCase):
    """The gate must still turn RED on the pre-engine thread model."""

    def run_helper(self, stub, dummy, json_path, threads):
        return subprocess.run(
            [
                sys.executable,
                str(HELPER),
                "--binary",
                str(stub),
                "--input",
                str(dummy),
                "--threads",
                str(threads),
                "--json",
                str(json_path),
                "--timeout-s",
                "30",
                "--build-profile",
                "debug",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

    def test_pre_engine_n_plus_one_stub_is_measured_red(self):
        """A real child holding N+1=5 threads must be a measured RED, exit 1."""
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            stub = td_path / "pre_engine_stub.py"
            stub.write_text(PRE_ENGINE_STUB)
            stub.chmod(0o755)
            dummy = td_path / "dummy.fastq"
            dummy.write_text("@r\nACGT\n+\nIIII\n")
            json_path = td_path / "records.json"

            proc = self.run_helper(stub, dummy, json_path, 4)

            self.assertEqual(
                proc.returncode,
                1,
                "the pre-engine 5-thread child against expected=9 must be a measured RED "
                f"(exit 1), got {proc.returncode}\n"
                f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}",
            )
            self.assertIn("requested=4 observed=5", proc.stdout)
            self.assertIn("THREAD REALITY verdict=RED", proc.stdout)
            doc = json.loads(json_path.read_text())
            self.assertEqual(doc["verdict"], "RED")
            record = doc["records"][0]
            self.assertEqual(record["requested"], 4)
            self.assertEqual(record["observed"], 5)
            self.assertEqual(
                record["child_returncode"],
                0,
                "the stub must exit on its own well inside the timeout",
            )

    def test_child_exiting_before_any_sample_is_exit_2(self):
        """A child that exits before the first sample is unobservable: exit 2."""
        false_binary = shutil.which("false")
        if false_binary is None:
            self.skipTest("no `false` binary available for the instant-exit stub")
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            # A real executable that exits instantly: by the time the observer
            # spawns `sample`, the pid is gone (or a zombie), so there is no
            # successful first observation and no verdict is emitted.
            stub = td_path / "instant_exit_stub"
            shutil.copyfile(false_binary, stub)
            stub.chmod(0o755)
            dummy = td_path / "dummy.fastq"
            dummy.write_text("@r\nACGT\n+\nIIII\n")
            json_path = td_path / "records.json"

            proc = self.run_helper(stub, dummy, json_path, 4)

            self.assertEqual(
                proc.returncode,
                2,
                "a child that exits before any successful observation must be exit 2 "
                f"(never a verdict), got {proc.returncode}\n"
                f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}",
            )
            self.assertNotIn("THREAD REALITY", proc.stdout)
            self.assertFalse(
                json_path.exists(),
                "exit-2 paths must not write a JSON verdict document",
            )


if __name__ == "__main__":
    unittest.main()
