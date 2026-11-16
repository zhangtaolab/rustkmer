"""Unit tests for the prepare-inputs stage (D-01/D-03/D-04).

Covers the -s derivation with its 0.75 occupancy boundary, the part-pair /
repo-root / union-anchor guards in both directions, the manifest build ->
revalidate round-trip at synthetic scale, the tamper-negative case, the
zero-count abort, and jellyfish info recording where jellyfish exists.
Stdlib unittest only — the tiny .gz fixtures are built with the system
`gzip` CLI (same pattern as test_merge_input.py / test_degradation.py).
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.bench.bench import BenchmarkConfig, rustkmer_count_cmd, stats
from scripts.bench.prepare_inputs import (
    DEFAULT_RUSTKMER,
    JELLYFISH_BIN,
    OCCUPANCY_TARGET,
    UNION_ANCHORS,
    build_stage,
    derive_hash_size,
    hash_size_slots,
    load_manifest,
    reconcile_anchors,
    refuse_repo_root,
    revalidate_stage,
    resolve_part_pair,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RELEASE_BINARY = Path(DEFAULT_RUSTKMER)
HAS_RELEASE = RELEASE_BINARY.is_file()
HAS_JELLYFISH = shutil.which(JELLYFISH_BIN) is not None


def build_gz_fixture(directory, name, seq, n_reads=100):
    """Write a deterministic .fq.gz fixture with per-call name and content.

    `seq` must be long enough for k=21 k-mers unless a zero-count fixture
    is wanted on purpose (TestZeroTotalGuard).
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


class PrepareStageTestCase(unittest.TestCase):
    """Shared tmpdir + pinned part-pair fixtures + honest anchor helper."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self.parts = [
            build_gz_fixture(self.data, "CRR1936095_r1.part_001",
                             "ACGT" * 6, n_reads=100),
            build_gz_fixture(self.data, "CRR1936095_r1.part_006",
                             "TTTG" * 6, n_reads=100),
        ]
        # Outside the repo tree by construction (macOS tmpdir), which the
        # stage itself re-asserts via refuse_repo_root.
        self.artifacts = self.root / "artifacts"

    def measure_union_total(self, k=21, threads=2):
        """Honest per-k union Total for the synthetic fixtures.

        The real stage counts and reconciles against the committed
        Phase-10 anchors; at synthetic scale the test computes the same
        sum-of-counts the two parts genuinely produce and passes it as
        the anchor (phase10's injectable-seam pattern — the guard still
        runs, against the value the fixtures truly have).
        """
        total = 0
        for index, part in enumerate(self.parts):
            out = self.root / f"probe{index}.k{k}.rkdb"
            cfg = BenchmarkConfig(k=k, canonical=True, threads=threads,
                                  inputs=[part])
            subprocess.run(rustkmer_count_cmd(cfg, out, RELEASE_BINARY),
                           check=True, capture_output=True)
            total += stats(out, RELEASE_BINARY)["total_kmers"]
        return total

    def run_rkdb_stage(self, threads=2):
        """Build the rkdb stage at k=21 with the honest synthetic anchor."""
        anchors = {21: self.measure_union_total(threads=threads)}
        return build_stage(self.data, self.artifacts, "rkdb",
                           rustkmer=RELEASE_BINARY, threads=threads,
                           ks=(21,), anchors=anchors)


class TestDeriveHashSize(unittest.TestCase):
    """derive_hash_size: smallest standard -s with 0.75 occupancy headroom."""

    def test_known_values_map_to_expected_strings(self):
        """Small counts pick the smallest rung; bigger counts walk it."""
        self.assertEqual(derive_hash_size(1), "1M")
        self.assertEqual(derive_hash_size(1000), "1M")
        self.assertEqual(derive_hash_size(int(0.75 * (2 << 20))), "2M")
        self.assertEqual(derive_hash_size(int(0.75 * (1 << 30))), "1G")
        self.assertEqual(derive_hash_size(int(0.75 * (10 << 30))), "10G")

    def test_boundary_exact_threshold_stays_on_size(self):
        """A Distinct exactly at 0.75*slots keeps the size (<= assertion)."""
        slots = hash_size_slots("1M")
        self.assertEqual(int(OCCUPANCY_TARGET * slots), 786432)
        at_threshold = int(OCCUPANCY_TARGET * slots)
        self.assertEqual(derive_hash_size(at_threshold), "1M")

    def test_one_step_over_threshold_grows_a_rung(self):
        """Distinct just over 0.75*slots forces the NEXT size up — the
        boundary probe; auto-grow territory is unreachable, not corrected
        silently (probe MBENCH-01/boundary, D-04)."""
        slots = hash_size_slots("1M")
        over = int(OCCUPANCY_TARGET * slots) + 1
        self.assertEqual(derive_hash_size(over), "2M")

    def test_non_positive_distinct_rejected(self):
        """Zero/negative/non-int Distinct values are invalid input."""
        for bad in (0, -1, 1.5, "1M", True):
            with self.assertRaises(ValueError):
                derive_hash_size(bad)

    def test_oversized_distinct_raises(self):
        """Nothing in the ladder fits an absurd Distinct — loud failure."""
        with self.assertRaises(RuntimeError):
            derive_hash_size(1 << 45)


class TestPartPairGuard(unittest.TestCase):
    """resolve_part_pair: exactly part_001 then part_006 — never part_002."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.part_001 = self.root / "CRR1936095_r1.part_001.fq.gz"
        self.part_002 = self.root / "CRR1936095_r1.part_002.fq.gz"
        self.part_006 = self.root / "CRR1936095_r1.part_006.fq.gz"
        for path in (self.part_001, self.part_002, self.part_006):
            path.write_bytes(b"x")

    def test_pinned_pair_in_order_accepted(self):
        """part_001 followed by part_006 resolves unchanged."""
        self.assertEqual(
            resolve_part_pair([self.part_001, self.part_006]),
            [self.part_001, self.part_006])

    def test_part_002_rejected(self):
        """The sorted-six-parts + first-two selection can never pass."""
        with self.assertRaises(ValueError):
            resolve_part_pair([self.part_001, self.part_002])

    def test_reversed_order_rejected(self):
        """part_006 before part_001 is the wrong order and fails loud."""
        with self.assertRaises(ValueError):
            resolve_part_pair([self.part_006, self.part_001])

    def test_one_path_rejected(self):
        """A single path is not a pair."""
        with self.assertRaises(ValueError):
            resolve_part_pair([self.part_001])

    def test_three_paths_rejected(self):
        """Three paths are not a pair either."""
        with self.assertRaises(ValueError):
            resolve_part_pair(
                [self.part_001, self.part_002, self.part_006])

    def test_missing_compression_suffix_rejected(self):
        """The token is matched on the compression-stripped stem only."""
        bare = self.root / "CRR1936095_r1.part_001.txt"
        bare.write_bytes(b"x")
        with self.assertRaises(ValueError):
            resolve_part_pair([bare, self.part_006])


class TestRepoRootGuard(unittest.TestCase):
    """refuse_repo_root: artifacts can never land inside the repo (D-03)."""

    def test_path_inside_repo_rejected(self):
        """bench.py's in-repo scratch default is exactly what this refuses."""
        inside = REPO_ROOT / "scripts" / "bench" / "scratch"
        with self.assertRaises(ValueError):
            refuse_repo_root(inside)

    def test_repo_root_itself_rejected(self):
        """The repo root as artifacts root is rejected too."""
        with self.assertRaises(ValueError):
            refuse_repo_root(REPO_ROOT)

    def test_path_outside_repo_accepted(self):
        """An out-of-repo path resolves and is returned."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        outside = Path(tmp.name)
        self.assertEqual(refuse_repo_root(outside), outside.resolve())


class TestAnchorReconciliation(unittest.TestCase):
    """reconcile_anchors: per-k sums must equal the committed union anchors."""

    def test_matching_anchors_pass(self):
        """The exact committed anchor values pass both k checks."""
        totals = {21: UNION_ANCHORS[21], 31: UNION_ANCHORS[31]}
        self.assertIsNone(reconcile_anchors(totals))

    def test_k21_one_short_raises_naming_k_and_anchor(self):
        """A sum one count short names k=21, the measured sum, the anchor."""
        totals = {21: UNION_ANCHORS[21] - 1, 31: UNION_ANCHORS[31]}
        with self.assertRaises(RuntimeError) as ctx:
            reconcile_anchors(totals)
        message = str(ctx.exception)
        self.assertIn("k=21", message)
        self.assertIn(str(UNION_ANCHORS[21] - 1), message)
        self.assertIn(str(UNION_ANCHORS[21]), message)

    def test_k31_one_long_raises_naming_k(self):
        """A sum one count long fails the same way for k=31."""
        totals = {21: UNION_ANCHORS[21], 31: UNION_ANCHORS[31] + 1}
        with self.assertRaises(RuntimeError) as ctx:
            reconcile_anchors(totals)
        self.assertIn("k=31", str(ctx.exception))

    def test_missing_k_raises(self):
        """A k with no recorded total is a loud error, never vacuous."""
        with self.assertRaises(RuntimeError):
            reconcile_anchors({31: UNION_ANCHORS[31]})

    def test_unknown_k_raises(self):
        """A total for a k with no committed anchor is rejected."""
        totals = {21: UNION_ANCHORS[21], 31: UNION_ANCHORS[31], 25: 1}
        with self.assertRaises(RuntimeError):
            reconcile_anchors(totals)

    def test_per_k_mid_build_call_enforces_single_k(self):
        """The build's ks=(k,) shape enforces just that k mid-stage."""
        self.assertIsNone(reconcile_anchors({21: UNION_ANCHORS[21]}, ks=(21,)))
        with self.assertRaises(RuntimeError):
            reconcile_anchors({21: UNION_ANCHORS[21] - 1}, ks=(21,))


@unittest.skipUnless(HAS_RELEASE,
                     "target/release/rustkmer not built — run "
                     "`cargo build --release` first")
class TestManifestRoundTrip(PrepareStageTestCase):
    """build rkdb -> manifest -> revalidate green; tamper -> loud failure."""

    def test_round_trip_manifest_shape_and_revalidate(self):
        """The manifest carries RESEARCH Pattern 1's shape and revalidates.

        Asserts schema_version 1, kind merge-input-manifest, 64-hex
        sha256, distinct/total > 0, the shared -s plan with its occupancy
        assertion satisfied, source fingerprints, retention — and that
        revalidate re-hashes + re-stats every record and passes.
        """
        manifest = self.run_rkdb_stage()
        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["kind"], "merge-input-manifest")
        self.assertEqual(len(manifest["artifacts"]), 2)
        repo_text = str(REPO_ROOT)
        for record in manifest["artifacts"]:
            self.assertRegex(record["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(record["distinct"], 0)
            self.assertGreater(record["total"], 0)
            self.assertEqual(record["k"], 21)
            self.assertTrue(record["canonical"])
            self.assertEqual(record["tool"], "rustkmer")
            self.assertIn("-C", record["command_line"])
            artifact_path = Path(record["path"])
            self.assertTrue(artifact_path.is_file())
            self.assertNotIn(repo_text, record["path"])  # D-03
        self.assertEqual(manifest["jellyfish_inputs"], [])
        plan = manifest["hash_size_plan"]["21"]
        self.assertEqual(plan["hash_size"], "1M")
        self.assertLessEqual(plan["max_per_part_distinct"],
                             OCCUPANCY_TARGET * plan["slots"])
        self.assertEqual(len(manifest["source_fingerprints"]), 2)
        for entry, part in zip(manifest["source_fingerprints"], self.parts):
            self.assertEqual(entry["path"], str(part))
            self.assertEqual(entry["size_bytes"], part.stat().st_size)
            self.assertEqual(len(entry["sha256"]), 64)
        self.assertEqual(manifest["retention"],
                         "keep until the Phase 12 merge verdict lands (D-02)")
        self.assertTrue((self.artifacts / "manifest.json").is_file())
        verified = revalidate_stage(self.artifacts, rustkmer=RELEASE_BINARY)
        self.assertEqual(len(verified["artifacts"]), 2)

    def test_tampered_byte_fails_revalidate(self):
        """A single flipped byte makes revalidate exit with a loud error
        naming the artifact — the tamper-negative case (D-04 integrity,
        threat T-11-03)."""
        self.run_rkdb_stage()
        target = self.artifacts / "part_001.k21.rkdb"
        data = bytearray(target.read_bytes())
        data[len(data) // 2] ^= 0xFF
        target.write_bytes(bytes(data))
        with self.assertRaises(RuntimeError) as ctx:
            revalidate_stage(self.artifacts, rustkmer=RELEASE_BINARY)
        self.assertIn("part_001.k21.rkdb", str(ctx.exception))

    def test_unrecorded_artifact_fails_revalidate(self):
        """A stray .rkdb with no manifest record is a loud error, never a
        silent rebuild (probe MBENCH-01/empty applied to identity)."""
        self.run_rkdb_stage()
        stray = self.artifacts / "part_009.k21.rkdb"
        stray.write_bytes(b"not really a database")
        with self.assertRaises(RuntimeError):
            revalidate_stage(self.artifacts, rustkmer=RELEASE_BINARY)

    def test_changed_counts_fail_revalidate(self):
        """Rebuild-then-replace (same size class, different bytes) is
        caught by the stats comparison, not just the hash."""
        manifest = self.run_rkdb_stage()
        target = Path(manifest["artifacts"][0]["path"])
        other = Path(manifest["artifacts"][1]["path"])
        target.write_bytes(other.read_bytes())
        with self.assertRaises(RuntimeError):
            revalidate_stage(self.artifacts, rustkmer=RELEASE_BINARY)


@unittest.skipUnless(HAS_RELEASE,
                     "target/release/rustkmer not built — run "
                     "`cargo build --release` first")
class TestZeroTotalGuard(PrepareStageTestCase):
    """An empty count aborts before the artifact becomes downstream input."""

    def test_zero_total_aborts_stage(self):
        """Reads shorter than k count zero k-mers; the stage fails loud
        instead of recording a zero-entry input (probe MBENCH-01/empty)."""
        build_gz_fixture(self.data, "CRR1936095_r1.part_001",
                         "ACGT" * 3, n_reads=10)
        build_gz_fixture(self.data, "CRR1936095_r1.part_006",
                         "TTTG" * 3, n_reads=10)
        with self.assertRaises(RuntimeError) as ctx:
            build_stage(self.data, self.artifacts, "rkdb",
                        rustkmer=RELEASE_BINARY, threads=2, ks=(21,),
                        anchors={21: 0})
        self.assertIn("MBENCH-01/empty", str(ctx.exception))
        self.assertFalse((self.artifacts / "manifest.json").is_file(),
                         "an aborted stage must not write a manifest")


@unittest.skipUnless(HAS_RELEASE and HAS_JELLYFISH,
                     "target/release/rustkmer AND jellyfish both required")
class TestJfBuildAndInfo(PrepareStageTestCase):
    """The jf stage completes the manifest with hash_size + jellyfish info."""

    def run_both_stages(self, threads=2):
        """rkdb stage then jf stage; return the completed manifest."""
        self.run_rkdb_stage(threads=threads)
        return build_stage(self.data, self.artifacts, "jf",
                           rustkmer=RELEASE_BINARY, threads=threads,
                           ks=(21,), jellyfish_bin=JELLYFISH_BIN)

    def test_jf_stage_records_hash_size_and_info(self):
        """Both .jf records carry the shared -s, 64-hex sha256, and the
        fail-loud-parsed jellyfish info; the completed manifest
        revalidates green end-to-end."""
        manifest = self.run_both_stages()
        self.assertEqual(manifest["stage"], "complete")
        records = manifest["jellyfish_inputs"]
        self.assertEqual(len(records), 2)
        hash_sizes = {record["hash_size"] for record in records}
        # One shared -s per k-pair — merge enforces hash-size equality.
        self.assertEqual(hash_sizes, {"1M"})
        for record in records:
            self.assertRegex(record["sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(record["k"], 21)
            self.assertTrue(Path(record["path"]).is_file())
            info = record["jellyfish_info"]
            for key in ("command", "where", "when", "canonical"):
                self.assertIn(key, info)
            self.assertIn("-m", info["command"].split())
            self.assertIn("-s", info["command"].split())
        verified = revalidate_stage(self.artifacts, rustkmer=RELEASE_BINARY)
        self.assertEqual(len(verified["artifacts"]), 2)
        self.assertEqual(len(verified["jellyfish_inputs"]), 2)

    def test_jf_stage_without_rkdb_manifest_raises(self):
        """No rkdb manifest -> the jf stage is invalid, never a rebuild."""
        with self.assertRaises(ValueError):
            build_stage(self.data, self.artifacts, "jf",
                        rustkmer=RELEASE_BINARY, threads=2, ks=(21,),
                        jellyfish_bin=JELLYFISH_BIN)

    def test_drifted_source_fails_jf_stage(self):
        """A source part changed since the rkdb stage -> loud refusal."""
        self.run_rkdb_stage()
        self.parts[1].write_bytes(b"replaced bytes, not a gzip file")
        with self.assertRaises(RuntimeError):
            build_stage(self.data, self.artifacts, "jf",
                        rustkmer=RELEASE_BINARY, threads=2, ks=(21,),
                        jellyfish_bin=JELLYFISH_BIN)


if __name__ == "__main__":
    unittest.main()
