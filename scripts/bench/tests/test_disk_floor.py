"""Unit tests for the derived disk floor mechanics (D-10/D-11/D-12).

Covers the three primitives Plan 11-07 lands in bench.py: `derive_disk_floor`
(pure D-10 arithmetic over recorded measurements), the breach contract of
`check_disk_floor` (exit-3 hard block with the stated shortfall — D-11 — and
its explicit `--disk-floor-override` deliberate-run escape), and
`ensure_disk_headroom` called from `run_comparison_protocol` before each
measured rep (the D-12 lightweight per-rep re-check). One class per behavior
under test, stdlib unittest only, following test_merge_input.py conventions;
os.statvfs is patched everywhere so no test touches a real volume.
"""

import io
import contextlib
import types
import unittest
from unittest import mock

from scripts.bench import bench
from scripts.bench.bench import (
    DEFAULT_DISK_FLOOR_GB,
    DISK_FLOOR_EXIT,
    MEASURED_INPUT_ARTIFACTS_BYTES,
    LARGEST_SINGLE_ARM_TRANSIENT_BYTES,
    SAFETY_MARGIN,
    check_disk_floor,
    derive_disk_floor,
    run_comparison_protocol,
)

GIB = 1 << 30


def statvfs_ns(free_bytes, frsize=512):
    """A minimal os.statvfs result with f_bavail sized to free_bytes."""
    return types.SimpleNamespace(f_bavail=free_bytes // frsize,
                                 f_frsize=frsize)


class TestDeriveDiskFloor(unittest.TestCase):
    """derive_disk_floor: pure arithmetic, margin applied, zero inputs raise."""

    def test_recorded_inputs_yield_the_derived_default(self):
        """The recorded 11-FLOOR-DERIVATION.md inputs produce the shipped
        default (136 GiB): (93,135,484,166 + 22,927,072,000) x 1.25 = 135.11
        GiB -> ceil = 136."""
        self.assertEqual(
            derive_disk_floor(MEASURED_INPUT_ARTIFACTS_BYTES,
                              LARGEST_SINGLE_ARM_TRANSIENT_BYTES),
            136)
        self.assertEqual(DEFAULT_DISK_FLOOR_GB, 136)

    def test_default_is_not_the_stale_150(self):
        """D-10: the stale count-era 150 GiB literal is replaced by the
        derived value."""
        self.assertNotEqual(DEFAULT_DISK_FLOOR_GB, 150)

    def test_margin_is_applied_to_the_sum(self):
        """The safety margin multiplies inputs + transient before the ceil."""
        self.assertEqual(derive_disk_floor(GIB, 0, margin=1.0), 1)
        self.assertEqual(derive_disk_floor(GIB, 0), 2)          # ceil(1.25)
        self.assertEqual(derive_disk_floor(GIB, 0, margin=2.0), 2)
        self.assertEqual(derive_disk_floor(GIB, GIB // 4), 2)   # ceil(1.25)

    def test_ceil_semantics(self):
        """Any fractional GiB rounds up — a floor of 0.0000001x GiB is 1."""
        self.assertEqual(derive_disk_floor(1, 0), 1)
        self.assertEqual(derive_disk_floor(1, 1), 1)

    def test_zero_inputs_raise(self):
        """A floor derived from nothing guards nothing — the D-10 inputs term
        is required."""
        with self.assertRaises(ValueError):
            derive_disk_floor(0, 100)
        with self.assertRaises(ValueError):
            derive_disk_floor(-1, 100)

    def test_negative_transient_raises(self):
        """Negative measurements are recording bugs, not floors."""
        with self.assertRaises(ValueError):
            derive_disk_floor(GIB, -1)

    def test_safety_margin_constant(self):
        """The documented D-10 constant is 1.25."""
        self.assertEqual(SAFETY_MARGIN, 1.25)


class TestDiskFloorBlock(unittest.TestCase):
    """check_disk_floor: under-floor exits 3 with the shortfall stated."""

    def test_under_floor_exits_3_with_shortfall(self):
        """RED-provable D-11 block: free space below the floor is a loud
        exit 3 naming the shortfall in GiB."""
        floor_gb = 1
        free = 256 * (1 << 20)  # 0.25 GiB free
        expected_shortfall = floor_gb - free / GIB
        with mock.patch("scripts.bench.bench.os.statvfs",
                        return_value=statvfs_ns(free)):
            with contextlib.redirect_stderr(io.StringIO()) as err:
                with self.assertRaises(SystemExit) as cm:
                    check_disk_floor("/tmp/scratch", floor_gb)
        self.assertEqual(cm.exception.code, DISK_FLOOR_EXIT)
        self.assertIn("shortfall", err.getvalue())
        self.assertIn(f"{expected_shortfall:.2f} GiB", err.getvalue())
        self.assertIn("exit 3", err.getvalue())

    def test_above_floor_returns_free_bytes(self):
        """A passing guard returns the free bytes (the pre-flight contract)."""
        free = 400 * GIB
        with mock.patch("scripts.bench.bench.os.statvfs",
                        return_value=statvfs_ns(free)):
            self.assertEqual(check_disk_floor("/tmp/scratch", 136), free)


class TestDiskFloorOverride(unittest.TestCase):
    """--disk-floor-override: shortfall printed + continue; no silent paths."""

    def test_override_prints_shortfall_and_continues(self):
        """D-11 deliberate-run escape: the breach is printed with its
        shortfall and the call returns (never exits)."""
        floor_gb = 1
        free = 256 * (1 << 20)
        with mock.patch("scripts.bench.bench.os.statvfs",
                        return_value=statvfs_ns(free)):
            with contextlib.redirect_stderr(io.StringIO()) as err:
                returned = check_disk_floor("/tmp/scratch", floor_gb,
                                            override=True)
        self.assertEqual(returned, free)
        self.assertIn("shortfall", err.getvalue())
        self.assertIn("--disk-floor-override", err.getvalue())

    def test_no_override_still_exits_3(self):
        """The override flag changes nothing when absent: under-floor without
        it is the exit-3 hard block — there is no silent continue."""
        with mock.patch("scripts.bench.bench.os.statvfs",
                        return_value=statvfs_ns(256 * (1 << 20))):
            with contextlib.redirect_stderr(io.StringIO()) as err:
                with self.assertRaises(SystemExit) as cm:
                    check_disk_floor("/tmp/scratch", 1, override=False)
        self.assertEqual(cm.exception.code, DISK_FLOOR_EXIT)
        self.assertNotIn("override", err.getvalue())


class TestEnsureDiskHeadroom(unittest.TestCase):
    """ensure_disk_headroom: the D-12 per-rep wrapper over the same guard."""

    def test_reuses_check_disk_floor_contract(self):
        """Breach exits 3 with the phase label in the message; pass returns
        the free bytes."""
        with mock.patch("scripts.bench.bench.os.statvfs",
                        return_value=statvfs_ns(256 * (1 << 20))):
            with contextlib.redirect_stderr(io.StringIO()) as err:
                with self.assertRaises(SystemExit) as cm:
                    bench.ensure_disk_headroom("/tmp/scratch", 1,
                                               phase="rep round 1")
        self.assertEqual(cm.exception.code, DISK_FLOOR_EXIT)
        self.assertIn("rep round 1", err.getvalue())

        free = 2 * GIB
        with mock.patch("scripts.bench.bench.os.statvfs",
                        return_value=statvfs_ns(free)):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(
                    bench.ensure_disk_headroom("/tmp/scratch", 1), free)


class TestPerRepRecheck(unittest.TestCase):
    """D-12 in the protocol: a mid-protocol disk fill aborts before the next
    measured rep, not after the run."""

    def _protocol(self, statvfs_side_effect):
        """Run a 1-arm, 2-rep comparison protocol with the disk guard active
        and everything else patched; returns (SystemExit | None, stderr,
        measure call count)."""
        spec = {"name": "count-A", "tool": "rustkmer", "out": "/tmp/a.rkdb",
                "cmd": ["rustkmer", "count"]}
        measure_calls = []

        def fake_measure(cmd):
            measure_calls.append(cmd)
            return {"wall_s": 0.1, "peak_rss_bytes": 1}

        with mock.patch("scripts.bench.bench.os.statvfs",
                        side_effect=statvfs_side_effect), \
             mock.patch("scripts.bench.bench.measure",
                        side_effect=fake_measure), \
             mock.patch("scripts.bench.bench.attempt_cache_purge",
                        return_value={"purged": False, "ci": False}), \
             mock.patch("scripts.bench.bench.stats",
                        return_value={"unique_kmers": 1, "total_kmers": 1}):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                try:
                    run_comparison_protocol(
                        [spec], reps=2, cooldown_s=0, rustkmer="rustkmer",
                        disk_floor_gb=1, disk_dir="/tmp/scratch",
                        disk_override=False)
                    exc = None
                except SystemExit as system_exit:
                    exc = system_exit
        return exc, err.getvalue(), len(measure_calls)

    def test_rep_passes_then_disk_fills_next_rep_breaches(self):
        """Rep 1's guard passes on 2 GiB free; the disk fills; rep 2's
        pre-rep re-check exits 3 MID-protocol (after exactly one measured
        rep plus the discarded warmup)."""
        # Sequence: warmup measure (no guard) -> rep round 0 guard (2 GiB,
        # passes) -> rep round 1 guard (0.25 GiB, breaches).
        sequence = [statvfs_ns(2 * GIB), statvfs_ns(256 * (1 << 20))]
        exc, err, measure_calls = self._protocol(sequence)
        self.assertIsNotNone(exc, "expected the mid-protocol exit-3 breach")
        self.assertEqual(exc.code, DISK_FLOOR_EXIT)
        self.assertIn("shortfall", err)
        self.assertIn("rep round 1", err)
        # One discarded warmup + exactly one measured rep before the breach.
        self.assertEqual(measure_calls, 2)

    def test_steady_disk_runs_to_completion(self):
        """Every pre-rep re-check passing means the protocol completes
        normally (the guard never fires on a healthy volume)."""
        sequence = [statvfs_ns(2 * GIB)] * 2
        exc, err, _ = self._protocol(sequence)
        self.assertIsNone(exc, err)
