"""Unit tests for the BENCH-04 degradation ladder and the slice tool (BENCH-04).

The resolver is a pure function over (explicit mode, input spec, env): it
reads existence/size only, never mutates the filesystem, and never guesses
silently. Stdlib unittest only — no pytest, no conftest. The tiny .gz fixture
is built with the system `gzip` CLI (gzip is not a Python import).
"""

import argparse
import contextlib
import gzip
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.bench import bench
from scripts.bench.bench import gather_inputs, resolve_mode
from scripts.bench.tests.test_schema import make_provenance

REPO_ROOT = Path(__file__).resolve().parents[3]
MAKE_SLICE = REPO_ROOT / "scripts" / "bench" / "make_slice.sh"
RANDOM_SLICE = REPO_ROOT / "scripts" / "bench" / "random_slice.py"
BENCH = REPO_ROOT / "scripts" / "bench" / "bench.py"

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


# --- 05-04: fingerprint-bound parity-reference gate + random provisioning ----
# Fixture-based only: no real dataset, no jellyfish, no rustkmer binary. The
# reference gate is exercised through the importable helpers; exit codes are
# asserted via SystemExit (the helpers own the 0/1/2 contract directly).

PINNED = {"distinct": 229694874, "total": 519271168}


def make_head_record(**overrides):
    """A complete, well-formed head-4M pinned reference record."""
    rec = {
        "slice_kind": "head-4M-profiling-reference",
        "source_sha256": "c" * 64,
        "reads": 4000000,
        "k": 21,
        "canonical": True,
        "reference_tool": "jellyfish 2.3.1",
        "expected": dict(PINNED),
        "provenance": make_provenance(),
    }
    rec.update(overrides)
    return rec


def make_random_record(seed=20261112, output_sha256="d" * 64,
                       selection_manifest_sha256="e" * 64, **overrides):
    """A complete random-record reference bound to its exact selection."""
    rec = {
        "slice_kind": "random-record",
        "source_sha256": "c" * 64,
        "reads": 1000000,
        "k": 21,
        "canonical": True,
        "reference_tool": "jellyfish 2.3.1",
        "expected": {"distinct": 12345678, "total": 23456789},
        "provenance": make_provenance(),
        "seed": seed,
        "selection_manifest": {
            "seed": seed,
            "output_sha256": output_sha256,
            "requested_reads": 1000000,
            "selected_reads": 1000000,
            "selected_indices": [0, 3, 7],
            "record_lines": 4,
        },
        "selection_manifest_sha256": selection_manifest_sha256,
        "output_sha256": output_sha256,
    }
    rec.update(overrides)
    return rec


def selection_for(rec):
    """The gate-time selection identity matching a random record."""
    return {
        "seed": rec["seed"],
        "selection_manifest_sha256": rec["selection_manifest_sha256"],
        "output_sha256": rec["output_sha256"],
    }


class ReferenceGateTestCase(unittest.TestCase):
    """Shared tmpdir + require-guard + exit-2 assertion helpers."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def require(self, name):
        """Fetch a 05-04 helper, failing on a planned assertion when absent.

        RED evidence must be an executed assertion (not an import/collection
        error), so every new behavior test resolves its helper through here.
        """
        fn = getattr(bench, name, None)
        self.assertIsNotNone(fn, f"bench.{name} not implemented yet (05-04)")
        return fn

    def write_reference(self, records, name="reference.json"):
        path = self.root / name
        path.write_text(json.dumps({"schema_version": 1, "records": records}))
        return path

    def assert_exit(self, code, fn, *args, **kwargs):
        """Run fn, require SystemExit(code), return captured stderr."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                fn(*args, **kwargs)
        self.assertEqual(ctx.exception.code, code, err.getvalue())
        return err.getvalue()


class TestParityReferenceGate(ReferenceGateTestCase):
    """load_parity_reference / gate_parity_reference: exact-match or exit."""

    def load(self, path, **overrides):
        load = self.require("load_parity_reference")
        kw = dict(source_sha256="c" * 64,
                  slice_kind="head-4M-profiling-reference",
                  reads=4000000, k=21, canonical=True)
        kw.update(overrides)
        with contextlib.redirect_stderr(io.StringIO()), \
                contextlib.redirect_stdout(io.StringIO()):
            return load(path, **kw)

    def test_exact_recipe_matches(self):
        """The exact full recipe returns the matching record."""
        path = self.write_reference([make_head_record()])
        rec = self.load(path)
        self.assertEqual(rec["expected"], PINNED)

    def test_fingerprint_mismatch_exits_2(self):
        """A different source fingerprint never matches (exit 2)."""
        path = self.write_reference([make_head_record()])
        self.assert_exit(2, self.load, path, source_sha256="f" * 64)

    def test_unbound_record_exits_2(self):
        """A record missing source_sha256 is invalid, never a fallback."""
        rec = make_head_record()
        del rec["source_sha256"]
        path = self.write_reference([rec])
        self.assert_exit(2, self.load, path)

    def test_no_matching_record_exits_2(self):
        """No record for the fingerprint/recipe is invalid (exit 2)."""
        path = self.write_reference([make_head_record()])
        self.assert_exit(2, self.load, path, reads=1000000)

    def test_wrong_k_exits_2(self):
        """k is part of the match key."""
        path = self.write_reference([make_head_record()])
        self.assert_exit(2, self.load, path, k=31)

    def test_wrong_canonical_exits_2(self):
        """canonical is part of the match key."""
        path = self.write_reference([make_head_record()])
        self.assert_exit(2, self.load, path, canonical=False)

    def test_ambiguous_full_key_exits_2(self):
        """Two records matching the FULL key are ambiguous, not first-wins."""
        path = self.write_reference([make_head_record(), make_head_record()])
        self.assert_exit(2, self.load, path)

    def test_missing_file_exits_2(self):
        """A missing reference file is invalid input."""
        self.assert_exit(2, self.load, self.root / "absent.json")

    def test_malformed_json_exits_2(self):
        """An unparseable reference file is invalid input."""
        path = self.root / "bad.json"
        path.write_text("{not json")
        self.assert_exit(2, self.load, path)

    def test_count_mismatch_exits_1(self):
        """Reference counts != live counts is a methodology finding (exit 1)
        printing both sides."""
        gate = self.require("gate_parity_reference")
        path = self.write_reference([make_head_record()])
        live = {"distinct": PINNED["distinct"] - 1, "total": PINNED["total"]}
        err = self.assert_exit(
            1, gate, live, path, "c" * 64,
            "head-4M-profiling-reference", 4000000, 21, True)
        self.assertIn(str(PINNED["distinct"]), err)
        self.assertIn(str(live["distinct"]), err)

    def test_count_match_gates_ok(self):
        """Equal counts gate successfully and return the record."""
        gate = self.require("gate_parity_reference")
        path = self.write_reference([make_head_record()])
        with contextlib.redirect_stderr(io.StringIO()), \
                contextlib.redirect_stdout(io.StringIO()):
            rec = gate(dict(PINNED), path, "c" * 64,
                       "head-4M-profiling-reference", 4000000, 21, True)
        self.assertEqual(rec["expected"], PINNED)


class TestRandomReferenceBinding(ReferenceGateTestCase):
    """Random records are bound to seed + manifest hash + output hash."""

    def load(self, path, selection, **overrides):
        load = self.require("load_parity_reference")
        kw = dict(source_sha256="c" * 64, slice_kind="random-record",
                  reads=1000000, k=21, canonical=True, selection=selection)
        kw.update(overrides)
        with contextlib.redirect_stderr(io.StringIO()), \
                contextlib.redirect_stdout(io.StringIO()):
            return load(path, **kw)

    def test_exact_full_recipe_matches(self):
        """The exact full recipe + selection identity returns the record."""
        rec = make_random_record()
        path = self.write_reference([rec])
        got = self.load(path, selection_for(rec))
        self.assertEqual(got["expected"], rec["expected"])

    def test_wrong_seed_exits_2(self):
        """Same source + same reads but a different seed never matches."""
        rec = make_random_record(seed=20261112)
        path = self.write_reference([rec])
        other = make_random_record(seed=999, output_sha256="a" * 64,
                                   selection_manifest_sha256="b" * 64)
        self.assert_exit(2, self.load, path, selection_for(other))

    def test_wrong_manifest_hash_exits_2(self):
        """A different selection-manifest hash never matches."""
        rec = make_random_record()
        path = self.write_reference([rec])
        sel = selection_for(rec)
        sel["selection_manifest_sha256"] = "9" * 64
        self.assert_exit(2, self.load, path, sel)

    def test_wrong_output_hash_exits_2(self):
        """Tampered slice bytes (different live output hash) never match."""
        rec = make_random_record()
        path = self.write_reference([rec])
        sel = selection_for(rec)
        sel["output_sha256"] = "8" * 64
        self.assert_exit(2, self.load, path, sel)

    def test_missing_selection_argument_exits_2(self):
        """A random-record gate without a selection identity is invalid."""
        rec = make_random_record()
        path = self.write_reference([rec])
        self.assert_exit(2, self.load, path, None)

    def test_record_missing_seed_exits_2(self):
        """A random record missing seed lacks required identity."""
        rec = make_random_record()
        del rec["seed"]
        path = self.write_reference([rec])
        self.assert_exit(2, self.load, path, selection_for(make_random_record()))

    def test_record_missing_manifest_hash_exits_2(self):
        """A random record missing selection_manifest_sha256 is invalid."""
        rec = make_random_record()
        del rec["selection_manifest_sha256"]
        path = self.write_reference([rec])
        self.assert_exit(2, self.load, path, selection_for(make_random_record()))

    def test_record_missing_output_hash_exits_2(self):
        """A random record missing output_sha256 is invalid."""
        rec = make_random_record()
        del rec["output_sha256"]
        path = self.write_reference([rec])
        self.assert_exit(2, self.load, path, selection_for(make_random_record()))

    def test_duplicate_full_key_exits_2(self):
        """Duplicate full-key random records are ambiguous, never first-wins."""
        rec = make_random_record()
        path = self.write_reference([rec, make_random_record()])
        self.assert_exit(2, self.load, path, selection_for(rec))

    def test_two_samples_never_cross_match(self):
        """Two samples sharing source+reads but differing in seed and selected
        bytes can never match each other's reference."""
        rec_a = make_random_record(seed=1, output_sha256="1" * 64,
                                   selection_manifest_sha256="2" * 64)
        rec_b = make_random_record(seed=2, output_sha256="3" * 64,
                                   selection_manifest_sha256="4" * 64)
        path = self.write_reference([rec_a])
        self.assert_exit(2, self.load, path, selection_for(rec_b))


class TestSelectionIdentity(ReferenceGateTestCase):
    """Gate-time identity: live slice hash cross-checked against the sidecar."""

    def write_slice_and_manifest(self, seed=20261112):
        slice_path = self.root / "slice.fq"
        slice_path.write_bytes(b"@R1\nACGT\n+\nIIII\n")
        out_sha = hashlib.sha256(slice_path.read_bytes()).hexdigest()
        manifest = {"seed": seed, "output_sha256": out_sha,
                    "requested_reads": 1, "selected_reads": 1,
                    "selected_indices": [0], "record_lines": 4}
        manifest_path = self.root / "slice.manifest.json"
        manifest_path.write_text(json.dumps(manifest, sort_keys=True))
        return slice_path, manifest_path, out_sha

    def test_identity_from_live_slice(self):
        """Identity carries the LIVE output hash, the manifest-file hash, and
        the seed."""
        identity_from = self.require("selection_identity_from")
        slice_path, manifest_path, out_sha = self.write_slice_and_manifest()
        with contextlib.redirect_stderr(io.StringIO()):
            sel = identity_from(slice_path, manifest_path, 20261112)
        self.assertEqual(sel["seed"], 20261112)
        self.assertEqual(sel["output_sha256"], out_sha)
        self.assertEqual(
            sel["selection_manifest_sha256"],
            hashlib.sha256(manifest_path.read_bytes()).hexdigest())

    def test_tampered_slice_exits_2(self):
        """Slice bytes whose live hash differs from the sidecar manifest are
        rejected (exit 2)."""
        identity_from = self.require("selection_identity_from")
        slice_path, manifest_path, _ = self.write_slice_and_manifest()
        slice_path.write_bytes(b"@R1\nTTTT\n+\nIIII\n")
        self.assert_exit(2, identity_from, slice_path, manifest_path, 20261112)

    def test_manifest_seed_mismatch_exits_2(self):
        """A sidecar manifest whose seed differs from the requested seed is
        rejected (exit 2)."""
        identity_from = self.require("selection_identity_from")
        slice_path, manifest_path, _ = self.write_slice_and_manifest(seed=7)
        self.assert_exit(2, identity_from, slice_path, manifest_path, 20261112)


class TestParityCapture(ReferenceGateTestCase):
    """capture_parity_reference writes only verified, pinned-safe records."""

    def test_capture_head4M_pinned_counts_written(self):
        """A head-4M capture with the pinned live counts writes the record."""
        capture = self.require("capture_parity_reference")
        path = self.root / "baseline.json"
        with contextlib.redirect_stdout(io.StringIO()):
            capture(path, make_head_record())
        doc = json.loads(path.read_text())
        self.assertEqual(doc["schema_version"], 1)
        self.assertEqual(len(doc["records"]), 1)
        self.assertEqual(doc["records"][0]["expected"], PINNED)

    def test_capture_head4M_wrong_counts_exits_1(self):
        """A head-4M capture whose live counts differ from the pinned
        constants is a loud methodology finding (exit 1), never a re-pin."""
        capture = self.require("capture_parity_reference")
        path = self.root / "baseline.json"
        bad = make_head_record(
            expected={"distinct": PINNED["distinct"] + 1,
                      "total": PINNED["total"]})
        self.assert_exit(1, capture, path, bad)
        self.assertFalse(path.exists(), "a rejected capture must not write")

    def test_capture_random_record_written(self):
        """A random capture carries its own live-derived counts + identity."""
        capture = self.require("capture_parity_reference")
        path = self.root / "baseline.json"
        rec = make_random_record()
        with contextlib.redirect_stdout(io.StringIO()):
            capture(path, rec)
        doc = json.loads(path.read_text())
        stored = doc["records"][0]
        self.assertEqual(stored["expected"], rec["expected"])
        self.assertNotEqual(stored["expected"]["distinct"], PINNED["distinct"])
        self.assertEqual(stored["seed"], 20261112)
        self.assertEqual(stored["output_sha256"], rec["output_sha256"])
        self.assertEqual(stored["selection_manifest_sha256"],
                         rec["selection_manifest_sha256"])

    def test_capture_appends_second_recipe(self):
        """Head + random records coexist as separate records."""
        capture = self.require("capture_parity_reference")
        path = self.root / "baseline.json"
        with contextlib.redirect_stdout(io.StringIO()):
            capture(path, make_head_record())
            capture(path, make_random_record())
        doc = json.loads(path.read_text())
        kinds = [r["slice_kind"] for r in doc["records"]]
        self.assertEqual(kinds, ["head-4M-profiling-reference", "random-record"])

    def test_capture_duplicate_full_key_exits_2(self):
        """Capturing an already-referenced exact recipe is rejected (exit 2),
        never a silent duplicate that would brick the gate."""
        capture = self.require("capture_parity_reference")
        path = self.root / "baseline.json"
        with contextlib.redirect_stdout(io.StringIO()):
            capture(path, make_head_record())
        self.assert_exit(2, capture, path, make_head_record())

    def test_capture_malformed_record_exits_2(self):
        """A record missing source_sha256 cannot be captured."""
        capture = self.require("capture_parity_reference")
        rec = make_head_record()
        del rec["source_sha256"]
        self.assert_exit(2, capture, self.root / "baseline.json", rec)


class TestRandomProvisioning(ReferenceGateTestCase):
    """bench.provision_random_slice: deterministic reservoir subslices."""

    def setUp(self):
        super().setUp()
        self.gz_path, self.plain_bytes = build_gz_fixture(self.root, 64)

    def provision(self, scratch_name, seed=42, reads=10):
        prov = self.require("provision_random_slice")
        scratch = self.root / scratch_name
        return prov([self.gz_path], reads, scratch, seed)

    def test_same_seed_byte_deterministic(self):
        """Two identical invocations produce identical slice + manifest bytes."""
        slices_a, sel_a = self.provision("a")
        slices_b, sel_b = self.provision("b")
        self.assertEqual(slices_a[0].read_bytes(), slices_b[0].read_bytes())
        self.assertEqual(
            Path(sel_a[0]["manifest_path"]).read_bytes(),
            Path(sel_b[0]["manifest_path"]).read_bytes())

    def test_selection_is_not_head_prefix(self):
        """The random slice differs from the first-N head bytes and indices."""
        slices, selections = self.provision("rnd")
        head = b"".join(self.plain_bytes.splitlines(keepends=True)[:40])
        self.assertNotEqual(slices[0].read_bytes(), head)
        manifest = selections[0]["manifest"]
        self.assertNotEqual(manifest["selected_indices"], list(range(10)))
        self.assertEqual(manifest["selected_reads"], 10)

    def test_manifest_written_beside_slice(self):
        """The sidecar manifest sits next to the slice and binds the source."""
        slices, selections = self.provision("side")
        manifest_path = Path(selections[0]["manifest_path"])
        self.assertTrue(manifest_path.is_file())
        self.assertEqual(manifest_path.parent, slices[0].parent)
        doc = json.loads(manifest_path.read_text())
        self.assertEqual(doc["source"]["sha256"],
                         hashlib.sha256(self.gz_path.read_bytes()).hexdigest())
        self.assertEqual(doc["output_sha256"],
                         hashlib.sha256(slices[0].read_bytes()).hexdigest())

    def test_single_source_measured_twice(self):
        """A single source is provisioned once and referenced twice (head
        arrangement parity)."""
        slices, selections = self.provision("dup")
        self.assertEqual(slices[0], slices[1])
        self.assertEqual(selections[0]["manifest_path"],
                         selections[1]["manifest_path"])


class TestHeadBackwardCompat(ReferenceGateTestCase):
    """Head selection stays byte-compatible with the historical extract."""

    def test_provision_slice_head_bytes_unchanged(self):
        """provision_slice still emits exactly the first 4*N lines."""
        gz_path, plain = build_gz_fixture(self.root, 64)
        scratch = self.root / "head"
        slices = bench.provision_slice([gz_path], 10, scratch)
        expected = b"".join(plain.splitlines(keepends=True)[:40])
        self.assertEqual(slices[0].read_bytes(), expected)

    def test_cli_exposes_new_flags(self):
        """--slice-selection / --slice-seed / --parity-reference /
        --capture-parity-reference are advertised by the CLI."""
        proc = subprocess.run([sys.executable, str(BENCH), "--help"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for flag in ("--slice-selection", "--slice-seed", "--parity-reference",
                     "--capture-parity-reference"):
            self.assertIn(flag, proc.stdout)


class TestPinnedConstants(unittest.TestCase):
    """The pinned head-4M constants live in exactly one module constant."""

    def test_pinned_constants_present(self):
        """PARITY_PINNED_HEAD4M carries the research-pinned counts."""
        self.assertTrue(hasattr(bench, "PARITY_PINNED_HEAD4M"),
                        "bench.PARITY_PINNED_HEAD4M not implemented yet (05-04)")
        self.assertEqual(bench.PARITY_PINNED_HEAD4M, PINNED)


class TestHashSizeThreading(ReferenceGateTestCase):
    """--hash-size reaches run_parity (real runs need 2G, not the 1G smoke)."""

    def test_parity_cli_threads_hash_size(self):
        """run_parity_cli forwards args.hash_size into run_parity."""
        args = argparse.Namespace(
            mode="synthetic", input=None, merge_input=None,
            out=str(self.root / "parity.json"), reads=10, k=21, threads=1,
            rustkmer="target/release/rustkmer", slice_reads=10,
            hash_size="2G", slice_selection="head", slice_seed=20261112,
            parity_reference=None, capture_parity_reference=None)
        with mock.patch.object(bench, "provision_synthetic",
                               return_value=[self.root / "in.fq"]), \
                mock.patch.object(bench, "run_parity",
                                  return_value={"distinct": 1, "total": 1}) as rp:
            bench.run_parity_cli(args)
        self.assertEqual(rp.call_args.kwargs.get("hash_size"), "2G")


if __name__ == "__main__":
    unittest.main()
