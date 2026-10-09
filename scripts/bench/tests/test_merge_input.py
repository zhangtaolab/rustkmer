"""Unit tests for the 04-04 milestone knobs: --merge-input and --skip-merge.

--merge-input changes slice provisioning only (slice A from --input, slice B
from --merge-input, same --slice-reads); every other mode must reject it
loudly, never silently ignore it. Stdlib unittest only — the tiny .gz
fixtures are built with the system `gzip` CLI (same pattern as
test_degradation.py).
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.bench.bench import merge_input_for, provision_slice


def build_gz_fixture(directory, name, seq, n_reads=100):
    """Write a deterministic .fq.gz fixture with per-call sequence content.

    Distinct `seq` values make two fixtures distinguishable by their slice
    bytes, which is exactly what the r1/r2 arrangement must preserve.
    """
    lines = []
    for i in range(1, n_reads + 1):
        lines.append(f"@{name}{i:07d}\n")
        lines.append(seq + "\n")
        lines.append("+\n")
        lines.append("I" * len(seq) + "\n")
    plain = directory / f"{name}.fq"
    plain.write_text("".join(lines), newline="\n")
    subprocess.run(["gzip", "-k", "-f", str(plain)], check=True)
    return directory / f"{name}.fq.gz"


class TestMergeInputFor(unittest.TestCase):
    """merge_input_for: slice-mode validation, loud rejection elsewhere."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.gz = build_gz_fixture(self.root, "r1", "ACGT" * 5)

    def test_none_returns_none(self):
        """No --merge-input is the ordinary path: None in, None out."""
        self.assertIsNone(merge_input_for("slice", None))
        self.assertIsNone(merge_input_for("full", None))

    def test_slice_mode_returns_path(self):
        """A slice-mode --merge-input that exists validates to its Path."""
        self.assertEqual(merge_input_for("slice", self.gz), self.gz)

    def test_full_mode_rejected(self):
        """--merge-input on a full run fails loudly, never silently."""
        with self.assertRaises(ValueError):
            merge_input_for("full", self.gz)

    def test_synthetic_mode_rejected(self):
        """--merge-input on a synthetic run fails loudly too."""
        with self.assertRaises(ValueError):
            merge_input_for("synthetic", self.gz)

    def test_missing_file_rejected(self):
        """A nonexistent --merge-input fails before any extraction."""
        with self.assertRaises(ValueError):
            merge_input_for("slice", self.root / "nope.fq.gz")


class TestProvisionSliceMergeInput(unittest.TestCase):
    """provision_slice with merge_input: slice B comes from the r2 input."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.r1 = build_gz_fixture(self.root, "r1", "ACGT" * 5)
        self.r2 = build_gz_fixture(self.root, "r2", "TTTG" * 5)
        self.scratch = self.root / "scratch"

    def test_second_slice_from_merge_input(self):
        """Slice A = first N reads of r1; slice B = first N reads of r2."""
        slices = provision_slice([self.r1], 10, self.scratch,
                                 merge_input=self.r2)
        self.assertEqual(len(slices), 2)
        slice_a, slice_b = slices
        a_lines = slice_a.read_text().splitlines()
        b_lines = slice_b.read_text().splitlines()
        # Slice A carries r1's reads; slice B carries r2's (its sequence
        # line differs and its headers name the r2 fixture).
        self.assertTrue(a_lines[0].startswith("@r1"))
        self.assertEqual(a_lines[1], "ACGT" * 5)
        self.assertTrue(b_lines[0].startswith("@r2"))
        self.assertEqual(b_lines[1], "TTTG" * 5)
        # Both slices honor the same --slice-reads (4 lines per read).
        self.assertEqual(len(a_lines), 40)
        self.assertEqual(len(b_lines), 40)

    def test_merge_input_wins_over_second_resolved_input(self):
        """An explicit --merge-input beats a second resolved --input."""
        slices = provision_slice([self.r1, self.r2], 10, self.scratch,
                                 merge_input=self.r2)
        slice_b = slices[1]
        self.assertTrue(slice_b.read_text().splitlines()[0].startswith("@r2"))

    def test_without_merge_input_single_source_reused(self):
        """Legacy behavior: one resolved input is extracted once, measured
        twice (slice B is the same file as slice A)."""
        slices = provision_slice([self.r1], 10, self.scratch)
        self.assertEqual(slices[0], slices[1])


if __name__ == "__main__":
    unittest.main()
