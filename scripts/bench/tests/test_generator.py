"""Unit tests for the deterministic synthetic FASTQ generator (BENCH-04).

The determinism contract: identical arguments produce byte-identical output
(same sha256), because the RNG is seeded before any sequence generation.
Stdlib unittest only — no pytest, no conftest.
"""

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
GEN = REPO_ROOT / "scripts" / "bench" / "gen_synthetic.py"


def sha256_of(path):
    """sha256 hex digest of a file's bytes."""
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


class TestDeterminism(unittest.TestCase):
    """Identical arguments must produce byte-identical output."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_gen(self, name, reads=500, length=150, seed=42):
        """Invoke the generator CLI; assert success; return the output path."""
        out = Path(self.tmp.name) / name
        proc = subprocess.run(
            [sys.executable, str(GEN), "--reads", str(reads),
             "--length", str(length), "--seed", str(seed),
             "--out", str(out)],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return out

    def test_same_seed_same_sha256(self):
        """Two runs with identical arguments give equal sha256."""
        a = self.run_gen("a.fq")
        b = self.run_gen("b.fq")
        self.assertEqual(sha256_of(a), sha256_of(b))

    def test_different_seed_differs(self):
        """Different seeds must produce different bytes."""
        a = self.run_gen("a.fq", seed=42)
        b = self.run_gen("b.fq", seed=1337)
        self.assertNotEqual(sha256_of(a), sha256_of(b))


class TestRecordShape(unittest.TestCase):
    """500 reads x 150 bp: 2000 lines, unique '@R' headers, 'I' qualities."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / "in.fq"
        proc = subprocess.run(
            [sys.executable, str(GEN), "--reads", "500",
             "--length", "150", "--seed", "42", "--out", str(self.out)],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.lines = self.out.read_text().splitlines()

    def test_line_count_is_exactly_4_per_read(self):
        """500 reads produce exactly 2000 lines (4 per record)."""
        self.assertEqual(len(self.lines), 500 * 4)

    def test_headers_unique_and_sequential(self):
        """Header lines are unique, start with '@R', and are sequential."""
        headers = self.lines[0::4]
        self.assertEqual(len(headers), 500)
        self.assertEqual(len(set(headers)), 500)
        self.assertTrue(headers[0].startswith("@R"))
        self.assertEqual(headers, [f"@R{i:07d}" for i in range(1, 501)])

    def test_plus_lines_are_bare(self):
        """Plus-lines (record line index 2) are a single '+' character."""
        self.assertEqual(set(self.lines[2::4]), {"+"})

    def test_quality_lines_all_i_of_read_length(self):
        """Every quality line is exactly read-length repeated 'I'."""
        qualities = self.lines[3::4]
        self.assertEqual(len(qualities), 500)
        self.assertEqual(set(qualities), {"I" * 150})

    def test_sequences_are_acgt_only(self):
        """Sequences contain only uppercase ACGT of the read length."""
        for seq in self.lines[1::4]:
            self.assertEqual(len(seq), 150)
            self.assertTrue(set(seq) <= {"A", "C", "G", "T"},
                            f"non-ACGT sequence: {seq}")


class TestRejection(unittest.TestCase):
    """Invalid arguments must exit non-zero."""

    def test_zero_reads_exits_nonzero(self):
        """--reads 0 is rejected with a usage error (non-zero exit)."""
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [sys.executable, str(GEN), "--reads", "0",
                 "--out", str(Path(tmp) / "x.fq")],
                capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
