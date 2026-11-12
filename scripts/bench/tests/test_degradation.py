"""Unit tests for the BENCH-04 degradation ladder and the slice tool (BENCH-04).

The resolver is a pure function over (explicit mode, input spec, env): it
reads existence/size only, never mutates the filesystem, and never guesses
silently. Stdlib unittest only — no pytest, no conftest. The tiny .gz fixture
is built with the system `gzip` CLI (gzip is not a Python import).
"""

import gzip
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.bench.bench import gather_inputs, resolve_mode

REPO_ROOT = Path(__file__).resolve().parents[3]
MAKE_SLICE = REPO_ROOT / "scripts" / "bench" / "make_slice.sh"
RANDOM_SLICE = REPO_ROOT / "scripts" / "bench" / "random_slice.py"

EMPTY_ENV = {}


def snapshot_tree(root):
    """(name, size, mtime_ns) for every path under root — mutation detector."""
    return sorted(
        (str(p.relative_to(root)), p.stat().st_size, p.stat().st_mtime_ns)
        for p in root.rglob("*")
    )


def build_gz_fixture(directory, n_reads=100):
    """Write a deterministic .fq.gz fixture; return (gz_path, plain_bytes)."""
    lines = []
    for i in range(1, n_reads + 1):
        lines.append(f"@R{i:07d}\n")
        lines.append("ACGT" * 5 + "\n")
        lines.append("+\n")
        lines.append("I" * 20 + "\n")
    plain = directory / "fixture.fq"
    plain.write_text("".join(lines), newline="\n")
    subprocess.run(["gzip", "-k", "-f", str(plain)], check=True)
    return directory / "fixture.fq.gz", plain.read_bytes()


class TestResolverLadder(unittest.TestCase):
    """Mode resolution: explicit beats env beats size ladder."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_missing_path_resolves_synthetic(self):
        """A missing input path resolves to synthetic with no inputs."""
        mode, inputs = resolve_mode(
            None, str(self.root / "nope.fq.gz"), EMPTY_ENV)
        self.assertEqual(mode, "synthetic")
        self.assertEqual(inputs, [])

    def test_existing_small_file_resolves_slice(self):
        """An existing input below the default threshold resolves to slice."""
        f = self.root / "small.fq.gz"
        f.write_bytes(b"x" * 100)
        mode, inputs = resolve_mode(None, str(f), EMPTY_ENV)
        self.assertEqual(mode, "slice")
        self.assertEqual(inputs, [f])

    def test_file_at_injected_threshold_resolves_full(self):
        """A file at or above an injected tiny threshold resolves to full."""
        f = self.root / "big.fq.gz"
        f.write_bytes(b"x" * 1000)
        mode, inputs = resolve_mode(None, str(f), EMPTY_ENV,
                                    size_threshold_bytes=1000)
        self.assertEqual(mode, "full")
        self.assertEqual(inputs, [f])

    def test_file_below_injected_threshold_resolves_slice(self):
        """A file just under the injected threshold stays slice."""
        f = self.root / "edge.fq.gz"
        f.write_bytes(b"x" * 999)
        mode, _ = resolve_mode(None, str(f), EMPTY_ENV,
                               size_threshold_bytes=1000)
        self.assertEqual(mode, "slice")

    def test_explicit_mode_wins_over_ladder(self):
        """An explicit --mode wins even when the ladder would disagree."""
        f = self.root / "small.fq.gz"
        f.write_bytes(b"x" * 100)
        mode, inputs = resolve_mode("full", str(f), EMPTY_ENV)
        self.assertEqual(mode, "full")
        self.assertEqual(inputs, [f])

    def test_env_mode_overrides_ladder(self):
        """RUSTKMER_BENCH_MODE beats the size ladder."""
        f = self.root / "small.fq.gz"
        f.write_bytes(b"x" * 100)
        mode, _ = resolve_mode(None, str(f),
                               {"RUSTKMER_BENCH_MODE": "synthetic"})
        self.assertEqual(mode, "synthetic")

    def test_cli_mode_beats_env_mode(self):
        """An explicit --mode beats RUSTKMER_BENCH_MODE when both are set."""
        mode, _ = resolve_mode("slice", None,
                               {"RUSTKMER_BENCH_MODE": "full"})
        self.assertEqual(mode, "slice")

    def test_env_input_used_when_no_cli_input(self):
        """RUSTKMER_BENCH_INPUT resolves when --input is absent."""
        f = self.root / "env_input.fq.gz"
        f.write_bytes(b"x" * 100)
        mode, inputs = resolve_mode(
            None, None, {"RUSTKMER_BENCH_INPUT": str(f)})
        self.assertEqual(mode, "slice")
        self.assertEqual(inputs, [f])

    def test_cli_input_beats_env_input(self):
        """--input beats RUSTKMER_BENCH_INPUT when both are set."""
        f = self.root / "cli.fq.gz"
        f.write_bytes(b"x" * 100)
        mode, inputs = resolve_mode(
            None, str(f),
            {"RUSTKMER_BENCH_INPUT": str(self.root / "missing.fq.gz")})
        self.assertEqual(mode, "slice")
        self.assertEqual(inputs, [f])

    def test_directory_scans_gz_sorted(self):
        """A directory scan returns only .fq.gz/.fastq.gz files, sorted."""
        for name in ("c.fq.gz", "a.fq.gz", "b.fastq.gz", "ignored.txt",
                     "notes.md"):
            (self.root / name).write_bytes(b"x" * 10)
        mode, inputs = resolve_mode(None, str(self.root), EMPTY_ENV)
        self.assertEqual(mode, "slice")
        self.assertEqual(
            inputs,
            [self.root / "a.fq.gz", self.root / "b.fastq.gz",
             self.root / "c.fq.gz"])

    def test_empty_directory_resolves_synthetic(self):
        """A directory with no gz files resolves to synthetic."""
        mode, inputs = resolve_mode(None, str(self.root), EMPTY_ENV)
        self.assertEqual(mode, "synthetic")
        self.assertEqual(inputs, [])

    def test_glob_expands_sorted(self):
        """A glob spec expands to the matching files, sorted."""
        for name in ("x2.fq.gz", "x1.fq.gz"):
            (self.root / name).write_bytes(b"x" * 10)
        mode, inputs = resolve_mode(
            None, str(self.root / "x*.fq.gz"), EMPTY_ENV)
        self.assertEqual(mode, "slice")
        self.assertEqual(inputs,
                         [self.root / "x1.fq.gz", self.root / "x2.fq.gz"])

    def test_gather_inputs_glob_direct(self):
        """gather_inputs expands a glob without going through the ladder."""
        for name in ("y1.fq.gz", "y2.fq.gz"):
            (self.root / name).write_bytes(b"x" * 10)
        self.assertEqual(
            gather_inputs(str(self.root / "y?.fq.gz")),
            [self.root / "y1.fq.gz", self.root / "y2.fq.gz"])

    def test_invalid_env_mode_raises(self):
        """A bogus mode from the environment fails loudly (V5 boundary)."""
        f = self.root / "small.fq.gz"
        f.write_bytes(b"x" * 100)
        with self.assertRaises(ValueError):
            resolve_mode(None, str(f), {"RUSTKMER_BENCH_MODE": "banana"})

    def test_resolution_mutates_nothing(self):
        """Resolution performs no filesystem writes."""
        f = self.root / "small.fq.gz"
        f.write_bytes(b"x" * 100)
        (self.root / "subdir").mkdir()
        before = snapshot_tree(self.root)
        resolve_mode(None, str(self.root), EMPTY_ENV)
        resolve_mode("full", str(f), EMPTY_ENV)
        resolve_mode(None, str(self.root / "nope"), EMPTY_ENV)
        self.assertEqual(snapshot_tree(self.root), before)


class TestMakeSliceDeterminism(unittest.TestCase):
    """make_slice.sh: byte-identical slices for the same input and N."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.gz_path, self.plain_bytes = build_gz_fixture(self.root, 100)

    def run_slice(self, output_name, n_reads=10):
        """Invoke make_slice.sh; assert success; return the slice path."""
        out = self.root / output_name
        proc = subprocess.run(
            ["bash", str(MAKE_SLICE), str(self.gz_path),
             str(n_reads), str(out)],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return out

    def test_identical_bytes_across_invocations(self):
        """Two invocations with the same input and N produce equal bytes."""
        a = self.run_slice("slice_a.fq")
        b = self.run_slice("slice_b.fq")
        self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_slice_is_exactly_first_n_reads(self):
        """The slice equals the first 4*N lines of the plain content."""
        out = self.run_slice("slice.fq", n_reads=10)
        expected_lines = self.plain_bytes.splitlines(keepends=True)[:40]
        self.assertEqual(out.read_bytes(), b"".join(expected_lines))

    def test_rejects_non_numeric_reads(self):
        """A non-numeric N_READS exits non-zero."""
        proc = subprocess.run(
            ["bash", str(MAKE_SLICE), str(self.gz_path),
             "ten", str(self.root / "bad.fq")],
            capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)

    def test_rejects_missing_input(self):
        """A missing INPUT exits non-zero."""
        proc = subprocess.run(
            ["bash", str(MAKE_SLICE), str(self.root / "nope.fq.gz"),
             "10", str(self.root / "bad.fq")],
            capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)


class TestRandomSlice(unittest.TestCase):
    """Seeded reservoir slices select whole records, never a head prefix."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.gz_path, self.plain_bytes = build_gz_fixture(self.root, 64)

    def run_random(self, output_name="slice.fq", reads=10, seed=42,
                   input_path=None, manifest_name=None):
        """Invoke the random-slice CLI without asserting its exit status."""
        out = self.root / output_name
        manifest = self.root / (manifest_name or output_name + ".json")
        proc = subprocess.run(
            [sys.executable, str(RANDOM_SLICE),
             "--input", str(input_path or self.gz_path),
             "--reads", str(reads), "--seed", str(seed),
             "--out", str(out), "--manifest", str(manifest)],
            capture_output=True, text=True)
        return proc, out, manifest

    def assert_invalid(self, proc, out, manifest):
        """Invalid input fails loudly with the CLI's invalid-exit contract."""
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertTrue(proc.stderr.strip(), "failure must be loud")
        self.assertFalse(out.exists(), "invalid input must not emit a slice")
        self.assertFalse(manifest.exists(),
                         "invalid input must not emit a manifest")

    def test_same_seed_is_byte_deterministic(self):
        """Identical inputs and seeds produce identical bytes and manifests."""
        proc_a, out_a, manifest_a = self.run_random(
            "a.fq", manifest_name="a.json")
        proc_b, out_b, manifest_b = self.run_random(
            "b.fq", manifest_name="b.json")
        self.assertEqual(proc_a.returncode, 0, proc_a.stderr)
        self.assertEqual(proc_b.returncode, 0, proc_b.stderr)
        self.assertEqual(hashlib.sha256(out_a.read_bytes()).hexdigest(),
                         hashlib.sha256(out_b.read_bytes()).hexdigest())
        self.assertEqual(
            hashlib.sha256(manifest_a.read_bytes()).hexdigest(),
            hashlib.sha256(manifest_b.read_bytes()).hexdigest())

    def test_different_seeds_select_different_records(self):
        """Changing only the seed changes selected source indices."""
        proc_a, out_a, manifest_a = self.run_random("a.fq", seed=42)
        proc_b, out_b, manifest_b = self.run_random("b.fq", seed=1337)
        self.assertEqual(proc_a.returncode, 0, proc_a.stderr)
        self.assertEqual(proc_b.returncode, 0, proc_b.stderr)
        doc_a = json.loads(manifest_a.read_text())
        doc_b = json.loads(manifest_b.read_text())
        self.assertNotEqual(doc_a["selected_indices"],
                            doc_b["selected_indices"])
        self.assertNotEqual(out_a.read_bytes(), out_b.read_bytes())

    def test_output_is_complete_records_in_source_order(self):
        """Every emitted record is the original four lines at its index."""
        proc, out, manifest = self.run_random(reads=12)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = out.read_bytes().splitlines(keepends=True)
        self.assertEqual(len(lines), 12 * 4)
        source_records = [self.plain_bytes.splitlines(keepends=True)[i:i + 4]
                          for i in range(0, 64 * 4, 4)]
        doc = json.loads(manifest.read_text())
        expected = b"".join(b"".join(source_records[i])
                            for i in doc["selected_indices"])
        self.assertEqual(out.read_bytes(), expected)
        self.assertEqual(doc["selected_reads"], 12)
        self.assertEqual(doc["record_lines"], 4)
        self.assertEqual(doc["output_sha256"],
                         hashlib.sha256(out.read_bytes()).hexdigest())

    def test_selected_indices_are_sorted_and_in_range(self):
        """Manifest indices are unique, ascending, and source-bounded."""
        proc, _, manifest = self.run_random(reads=16)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        doc = json.loads(manifest.read_text())
        indices = doc["selected_indices"]
        self.assertEqual(indices, sorted(set(indices)))
        self.assertEqual(len(indices), doc["requested_reads"])
        self.assertTrue(all(0 <= index < 64 for index in indices))
        self.assertEqual(doc["source"]["path"], str(self.gz_path))
        self.assertEqual(doc["source"]["size_bytes"], self.gz_path.stat().st_size)
        self.assertEqual(len(doc["source"]["sha256"]), 64)
        self.assertEqual(doc["seed"], 42)

    def test_selection_is_not_head_of_file(self):
        """A seeded sample over more than N records is not range(N)."""
        proc, _, manifest = self.run_random(reads=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        indices = json.loads(manifest.read_text())["selected_indices"]
        self.assertNotEqual(indices, list(range(10)))

    def test_request_larger_than_source_exits_2(self):
        """Oversized requests fail rather than silently truncating."""
        proc, out, manifest = self.run_random("too-large.fq", reads=65)
        self.assert_invalid(proc, out, manifest)
        self.assertIn("64", proc.stderr)

    def test_empty_input_exits_2(self):
        """A valid gzip containing zero records is invalid benchmark input."""
        empty = self.root / "empty.fq.gz"
        with gzip.open(empty, "wb"):
            pass
        proc, out, manifest = self.run_random(
            "empty.fq", input_path=empty)
        self.assert_invalid(proc, out, manifest)

    def test_malformed_fastq_exits_2(self):
        """A partial fifth line group is rejected as malformed FASTQ."""
        malformed = self.root / "malformed.fq.gz"
        with gzip.open(malformed, "wb") as fh:
            fh.write(b"@R1\nACGT\n+\nIIII\n@R2\nACGT\n+\n")
        proc, out, manifest = self.run_random(
            "malformed.fq", input_path=malformed)
        self.assert_invalid(proc, out, manifest)
        self.assertIn("multiple of 4", proc.stderr)

    def test_zero_reads_exits_2(self):
        """Zero requested reads is an argparse usage error."""
        proc, out, manifest = self.run_random("zero.fq", reads=0)
        self.assert_invalid(proc, out, manifest)

    def test_nonnumeric_reads_exits_2(self):
        """Nonnumeric requested reads is an argparse usage error."""
        proc, out, manifest = self.run_random("nonnumeric.fq", reads="ten")
        self.assert_invalid(proc, out, manifest)

    def test_missing_input_exits_2(self):
        """A missing source file is invalid, never an empty successful slice."""
        proc, out, manifest = self.run_random(
            "missing.fq", input_path=self.root / "missing.fq.gz")
        self.assert_invalid(proc, out, manifest)


if __name__ == "__main__":
    unittest.main()
