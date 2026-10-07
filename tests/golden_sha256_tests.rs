//! DENSE-02 — `.rkdb` v2 byte-identity guard for the dense-storage width
//! narrowing: for k <= 32 the counter stores its keys as `u64` while the
//! on-disk record stays 16 + 4 bytes.
//!
//! **D-03 locks dense storage to RAM only.** For k <= 32 the counter stores its
//! keys as `u64`, but a `KmerEntry` on disk remains a 16-byte little-endian
//! `u128` + 4-byte little-endian `u32` (v2, 20 B/record), and the write path
//! widens `u64 -> u128` by zero-extension. If that widening ever drifts, every
//! `.rkdb` a k <= 32 run produces changes bytes and existing readers silently
//! see different data — which is exactly the "dense storage must be
//! transparent to existing readers" obligation DENSE-02 states.
//!
//! ## What each test here does — and what it does not
//!
//! | Test | What it observes | What it does **not** observe |
//! |---|---|---|
//! | `golden_rkdb_sha256_unchanged_post_dense` | the 12 committed Phase 1/2 fixture **files** still hash to a committed Phase 1/2 **manifest** — it catches a hand-edited or truncated committed fixture | anything about the Phase-3 write path: neither the fixtures nor the manifest is produced by Phase-3 code at test time, so this test is green whatever the write path does |
//! | `dense_write_path_bytes_match_a_hand_built_reference` | the bytes the production write path actually emits, against a reference this test builds itself | the encoder (both arms call it — see that test's own docstring) |
//! | `dense_k32_high_bytes_are_zero_on_disk` | the 16 k-mer bytes of a dense key at the tight `2^(2k) <= 2^64` bound, read back out of the file | — |
//! | `write_read_write_is_byte_idempotent` | that a write depends only on the data, not on insertion order or uninitialised header fields | — |
//!
//! An earlier version of this docstring claimed that the fixture re-hash was
//! GREEN before the dense narrowing landed and that the pre-narrowing pass was
//! what made the post-narrowing pass meaningful as a differential. That claim
//! was false: the test never invoked the swapped code, so its before and after
//! passes were green for the same reason. It is removed rather than reworded,
//! and the write-path differential above is what actually guards DENSE-02.
//!
//! Phase 1 D-10 carry-forward: the golden baselines are **ground truth, not
//! regenerated**. If the fixture re-hash ever fails, the fix is to revert the
//! drift — never to re-capture.
//!
//! Note on coverage vs `tests/golden_tests.rs`: `golden_tests.rs` reads the same
//! manifest and therefore shares the static-fixture property, one test per
//! fixture. This binary exists because D-02's guarantee is *the write path*, and
//! a plan-scoped artifact named for the requirement makes that coupling legible:
//! it is the test a reviewer points at when asking "did the dense narrowing
//! change the file format?". Both binaries must agree on the fixture hashes;
//! only this one drives the write path.

use anyhow::Result;
use rustkmer::database::format::RKDatabase;
use rustkmer::hash::table::KmerCounter;
use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::kmer::encoding::{encode_kmer_bytes_u128, reverse_complement_u128};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::path::Path;
use tempfile::TempDir;

/// The 12 golden fixture basenames, i.e. the D-13 coverage matrix
/// `k ∈ {21, 32, 64} × canonical × sorted` (`golden_tests.rs` writes the same
/// list as 12 individual tests; this binary iterates it so a format drift
/// reports as ONE failure naming every affected cell).
const GOLDEN_FIXTURES: &[&str] = &[
    "golden_k21_canon_sorted.rkdb",
    "golden_k21_canon_unsorted.rkdb",
    "golden_k21_noncanon_sorted.rkdb",
    "golden_k21_noncanon_unsorted.rkdb",
    "golden_k32_canon_sorted.rkdb",
    "golden_k32_canon_unsorted.rkdb",
    "golden_k32_noncanon_sorted.rkdb",
    "golden_k32_noncanon_unsorted.rkdb",
    "golden_k64_canon_sorted.rkdb",
    "golden_k64_canon_unsorted.rkdb",
    "golden_k64_noncanon_sorted.rkdb",
    "golden_k64_noncanon_unsorted.rkdb",
];

/// `.rkdb` v2 header length in bytes: 4 magic + 2 version + 1 kmer_size +
/// 1 pad + 2 pad + 8 total_kmers + 1 flags + 7 pad + 8 data_offset +
/// 8 index_offset. Pinned by a whole-file length assertion in every test that
/// reads a data section, so a header that gains a field moves the data section
/// loudly instead of silently shifting the bytes these tests inspect.
const RKDB_V2_HEADER_BYTES: usize = 42;

/// Parse `tests/fixtures/golden_manifest.sha256` into a name -> hex map.
///
/// Manifest format (one entry per line): `<filename> <sha256-hex>`.
/// Identical to `golden_tests.rs::load_golden_manifest` — deliberately
/// duplicated rather than shared, because `tests/*.rs` are separate binaries
/// and `tests/common/` is only for helper *modules*.
fn load_golden_manifest() -> Result<HashMap<String, String>> {
    let text = std::fs::read_to_string("tests/fixtures/golden_manifest.sha256")
        .map_err(|e| anyhow::anyhow!("failed to read golden_manifest.sha256: {}", e))?;
    let mut map = HashMap::new();
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let mut parts = line.split_whitespace();
        let name = parts
            .next()
            .ok_or_else(|| anyhow::anyhow!("manifest line missing name: {:?}", line))?
            .to_string();
        let hex = parts
            .next()
            .ok_or_else(|| anyhow::anyhow!("manifest line missing sha256: {:?}", line))?
            .to_string();
        map.insert(name, hex);
    }
    Ok(map)
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

/// Assert a single golden fixture's on-disk bytes hash to the manifest entry.
fn assert_golden_matches_manifest(name: &str) -> Result<()> {
    let manifest = load_golden_manifest()?;
    let expected = manifest.get(name).ok_or_else(|| {
        anyhow::anyhow!(
            "golden fixture {:?} not present in golden_manifest.sha256",
            name
        )
    })?;
    let path = format!("tests/fixtures/{}", name);
    let bytes = std::fs::read(&path).map_err(|e| anyhow::anyhow!("read {}: {}", path, e))?;
    let actual = sha256_hex(&bytes);
    assert_eq!(
        actual, *expected,
        "golden sha256 mismatch for {}: committed bytes drifted from baseline",
        name
    );
    Ok(())
}

/// Read the bytes of `path` that follow the `.rkdb` v2 header.
fn read_data_section(path: &Path) -> Result<Vec<u8>> {
    let bytes =
        std::fs::read(path).map_err(|e| anyhow::anyhow!("read {}: {}", path.display(), e))?;
    anyhow::ensure!(
        bytes.len() > RKDB_V2_HEADER_BYTES,
        "{} is {} bytes — too short to hold a {}-byte header plus a record",
        path.display(),
        bytes.len(),
        RKDB_V2_HEADER_BYTES
    );
    Ok(bytes[RKDB_V2_HEADER_BYTES..].to_vec())
}

/// Describe where two blobs first differ, for an assertion message that has to
/// be actionable on its own. A silent byte drift IS the DENSE-02 failure, and
/// a bare `assert_eq!` on two multi-hundred-byte arms would print a wall of
/// hex without saying which arm moved.
fn describe_difference(produced: &[u8], reference: &[u8]) -> String {
    let shared = produced.len().min(reference.len());
    for (offset, (a, b)) in produced[..shared]
        .iter()
        .zip(reference[..shared].iter())
        .enumerate()
    {
        if a != b {
            return format!(
                "first difference at data-section byte {offset}: production arm 0x{a:02x}, \
                 test-built reference 0x{b:02x} (production arm {} bytes, reference {} bytes)",
                produced.len(),
                reference.len()
            );
        }
    }
    format!(
        "the shared {shared}-byte prefix is identical but the arms have different lengths: \
         production arm {} bytes, test-built reference {} bytes",
        produced.len(),
        reference.len()
    )
}

/// DENSE-02 — the dense-storage narrowing is RAM-only, so all 12 committed
/// `.rkdb` fixtures must still hash to their Phase 1/2 manifest values.
///
/// Threat T-03-10 (Tampering / on-disk format drift) — the failure mode the
/// binary as a whole guards is a write path that stops zero-extending
/// `u64 -> u128`, that changes `KmerEntry`'s 16 + 4 byte v2 layout, or that
/// alters the header literal.
///
/// **What THIS test can detect:** a hand-edited or truncated committed fixture.
/// **What it cannot:** any of the three drift modes above. The fixtures were
/// last written in Phase 1 and neither they nor the manifest is touched by any
/// Phase-3 code at test time, so their hashes are unaffected by the write path
/// — which is precisely why the write-path differential below exists.
#[test]
fn golden_rkdb_sha256_unchanged_post_dense() -> Result<()> {
    for name in GOLDEN_FIXTURES {
        assert_golden_matches_manifest(name)?;
    }
    Ok(())
}

/// The manifest must cover exactly the 12 fixtures this binary iterates — if a
/// fixture is added to disk without a manifest entry, the loop above would
/// silently stop covering it.
#[test]
fn golden_manifest_covers_every_fixture_this_binary_checks() -> Result<()> {
    let manifest = load_golden_manifest()?;
    assert_eq!(
        manifest.len(),
        GOLDEN_FIXTURES.len(),
        "manifest entry count must match the fixture list this binary iterates"
    );
    for name in GOLDEN_FIXTURES {
        assert!(
            manifest.contains_key(*name),
            "manifest is missing an entry for {}",
            name
        );
        let path = format!("tests/fixtures/{}", name);
        assert!(
            std::path::Path::new(&path).exists(),
            "fixture {} is listed but not present on disk",
            path
        );
    }
    Ok(())
}

/// A fixed, literal, already-canonical k=21 k-mer table, with the occurrence
/// count each k-mer is incremented with. `KMER_TABLE.len()` is the number of
/// DISTINCT k-mers the counter must end up holding; several entries are
/// incremented more than once so the counts are not all 1.
///
/// Canonicality matters because it is what makes "the k-mer set in this file"
/// and "the k-mer set the counter holds" the same set: a canonical-mode run
/// canonicalizes each window before incrementing, so a non-canonical table
/// would be rewritten by production into a smaller, different set. Asserted
/// rather than assumed — see `table_is_already_canonical`.
///
/// The table is a literal in this file, not a fixture, so the input the
/// comparison is built from is visible in the comparison's own source.
const KMER_TABLE: &[(&str, u32)] = &[
    ("AAAAAAAAAAAAAAAAAAAAA", 1),
    ("CACACACACACACACACACAC", 1),
    ("CCCCCCCCCCCCCCCCCCCCC", 5),
    ("AACCGGTTAACCGGTTAACCG", 1),
    ("CCGGAATTCCGGAATTCCGGA", 1),
    ("ATATATATATATATATATATA", 1),
    ("GGGGATATATATATATATATA", 1),
    ("ACGTACGTACGTACGTACGTA", 3),
];

/// k of [`KMER_TABLE`]; also the `kmer_size` written into the `.rkdb` header.
const TABLE_K: u8 = 21;

/// The reference arm: a data-section byte string this test builds itself, with
/// no production call between the literal table and the bytes.
///
/// Each record is `encode_kmer_bytes_u128(dna).to_le_bytes()` followed by
/// `count.to_le_bytes()`, sorted ascending by the encoded k-mer because the
/// production writer sorts when it is asked for a sorted database. Nothing here
/// touches the counter, the pair collector, the record codec, or the file
/// writer — that independence is the entire reason this arm is a reference and
/// not a second call of the function under test.
fn hand_built_reference() -> Result<Vec<u8>> {
    let mut records: Vec<(u128, [u8; 4])> = Vec::with_capacity(KMER_TABLE.len());
    for (dna, count) in KMER_TABLE {
        let encoded = encode_kmer_bytes_u128(dna.as_bytes())
            .map_err(|e| anyhow::anyhow!("encode {}: {}", dna, e))?;
        records.push((encoded, count.to_le_bytes()));
    }
    records.sort_by_key(|(encoded, _)| *encoded);

    let mut out = Vec::with_capacity(records.len() * 20);
    for (encoded, count_bytes) in records {
        out.extend_from_slice(&encoded.to_le_bytes());
        out.extend_from_slice(&count_bytes);
    }
    Ok(out)
}

/// Drive the production DENSE write path: counter -> pair collector -> sorted
/// entries -> `.rkdb` on disk, then return the bytes it actually wrote.
///
/// This arm traverses `KmerCounter::new` (which selects the dense `u64` table
/// for k <= 32), `increment`'s narrow-on-store, `get_all_counts`'s `u64 -> u128`
/// widening, `RKDatabase::from_kmer_pairs` and the record codec. The returned
/// bytes are read back off the filesystem, not from an in-memory buffer.
fn production_write_path(
    dir: &Path,
    k: u8,
    pairs: Vec<(u128, u32)>,
    canonical: bool,
) -> Result<Vec<u8>> {
    let db = RKDatabase::from_kmer_pairs(pairs, k, canonical, true)?;
    let path = dir.join(format!("dense_k{k}.rkdb"));
    db.to_file_path(&path)?;
    read_data_section(&path)
}

/// The literal table must already be canonical, or a canonical-mode run would
/// rewrite it into a different k-mer set and the differential would compare the
/// wrong two things. This makes the "already canonical" claim an observation
/// rather than a comment.
fn table_is_already_canonical() -> Result<()> {
    for (dna, _) in KMER_TABLE {
        let encoded = encode_kmer_bytes_u128(dna.as_bytes())
            .map_err(|e| anyhow::anyhow!("encode {}: {}", dna, e))?;
        let canonical =
            canonical_kmer_u128(encoded, TABLE_K as usize).map_err(|e| anyhow::anyhow!("{e}"))?;
        anyhow::ensure!(
            canonical == encoded,
            "KMER_TABLE entry {} is not already canonical (its canonical form encodes to 0x{:x}, \
             not 0x{:x}); the two arms would then be counting different k-mer sets",
            dna,
            canonical,
            encoded
        );
    }
    Ok(())
}

/// **The DENSE-02 write-path differential.** A mutation of the dense
/// `u64 -> u128` widening in `KmerCounter::get_all_counts` — the single link
/// between the dense table and the `.rkdb` record — turns this test red, where
/// no test in the phase could see it before (the committed-fixture re-hash
/// above is green under exactly that mutation).
///
/// **Why the reference is a byte string and not a second call.** An earlier
/// revision built the reference by handing the same `Vec<(u128, u32)>` to the
/// same `RKDatabase::from_kmer_pairs` / `to_file_path` pair. That is one pure
/// function compared with itself: under the widening mutation both arms wrote
/// the same corrupted high eight bytes and the comparison stayed GREEN. Here
/// the expected bytes are `to_le_bytes()` of values this test computed, so the
/// mutation moves the production arm and only the production arm.
///
/// **Scope limit, stated plainly.** Both arms call `encode_kmer_bytes_u128`, so
/// a change to the ENCODER moves both arms together and this test stays green.
/// That is deliberate: the encoder is not what this test guards (the
/// committed-fixture re-hash above still covers committed bytes, and
/// `tests/merge_route_parity_tests.rs` covers the record codec). This test
/// guards the one link nothing else covers — the dense counter's widening as
/// it reaches the file.
///
/// Note on `KmerCounter::increment`: it takes an ALREADY-ENCODED `u128`;
/// canonicalization happens in the CLI (`src/cli/commands/count.rs`), not in
/// the counter. Encoding the literal table here is therefore input
/// construction, the same step `process_one_record` performs, and not a shared
/// dependency with the code under test.
#[test]
fn dense_write_path_bytes_match_a_hand_built_reference() -> Result<()> {
    table_is_already_canonical()?;

    let k = TABLE_K as usize;
    let counter = KmerCounter::new(k, true, 16, 1)?;
    assert!(
        counter.uses_dense_storage(),
        "a k={k} counter must select the dense u64 storage width — this test's premise is \
         that the value crosses a u64 -> u128 boundary on its way to disk"
    );

    for (dna, times) in KMER_TABLE {
        let encoded = encode_kmer_bytes_u128(dna.as_bytes())
            .map_err(|e| anyhow::anyhow!("encode {}: {}", dna, e))?;
        for _ in 0..*times {
            counter.increment(encoded)?;
        }
    }

    let pairs = counter.get_all_counts();
    assert_eq!(
        pairs.len(),
        KMER_TABLE.len(),
        "the counter must hold exactly the {} distinct k-mers of the literal table",
        KMER_TABLE.len()
    );
    assert!(
        pairs.iter().any(|(_, count)| *count > 1),
        "the table must produce at least one count above 1, otherwise a widening that pins \
         every count to 1 would pass unnoticed"
    );

    let dir = TempDir::new()?;
    let production_arm = production_write_path(dir.path(), TABLE_K, pairs, true)?;
    let reference_arm = hand_built_reference()?;

    assert!(
        production_arm == reference_arm,
        "{}",
        describe_difference(&production_arm, &reference_arm)
    );
    Ok(())
}

/// **The tight end of the encoder's `2^(2k) <= 2^64` bound, asserted on disk.**
///
/// At k=32 a k-mer uses all 64 low bits, so `2^64` values are reachable and the
/// bound holds with equality. A 32-base T k-mer encodes to exactly
/// `u64::MAX as u128`: the 64 low bits are all set and the high 64 are zero. The
/// dense counter stores that as a `u64`, and `get_all_counts` widens it back.
///
/// The 16 bytes that reach the file must therefore be eight `0xFF` bytes
/// followed by eight `0x00` bytes. The `0x00` half is the zero-extension:
/// asserted here, on the disk, rather than stated in a comment about a code
/// path nothing observes. If a future change ever let a dense key carry bits
/// above bit 64, this is the test that catches it — and it is the assertion
/// that catches it independently of the differential above.
///
/// **Why this drives the counter with `canonical: false`.** The canonical form
/// of a 32-base T k-mer is 32 bases of A (its reverse complement encodes to 0),
/// so no CANONICAL k-mer encodes to `u64::MAX` — the bound value is only
/// reachable on the non-canonical path, which is exactly what `count
/// --no-canonical` produces. The header flag is irrelevant to the claim: what is
/// under test is how a dense `u64` key is widened, and that is independent of
/// whether the k-mer was canonicalized on the way in. `rc_differs_from_self`
/// pins that reasoning so it cannot silently rot.
#[test]
fn dense_k32_high_bytes_are_zero_on_disk() -> Result<()> {
    const K: usize = 32;
    const T32: &str = "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT";
    const COUNT: u32 = 7;

    let encoded = encode_kmer_bytes_u128(T32.as_bytes())
        .map_err(|e| anyhow::anyhow!("encode {T32}: {}", e))?;
    assert_eq!(
        encoded,
        u64::MAX as u128,
        "a 32-base T k-mer must be exactly u64::MAX as u128 — this test's premise is the tight \
         end of the 2^(2k) <= 2^64 bound, and the encoder no longer produces it"
    );
    assert_eq!(
        encoded as u64 as u128, encoded,
        "the low 64 bits must survive a round trip through the dense storage width unchanged"
    );
    assert_ne!(
        reverse_complement_u128(encoded, K),
        encoded,
        "this k-mer's reverse complement differs from itself, which is why it is only reachable \
         on the non-canonical path — if it ever became self-canonical, canonical: false below \
         would no longer match what a canonical-mode run would store"
    );

    let counter = KmerCounter::new(K, false, 1, 1)?;
    assert!(
        counter.uses_dense_storage(),
        "k=32 is the widest k that must still select the dense u64 storage width"
    );
    for _ in 0..COUNT {
        counter.increment(encoded)?;
    }

    let pairs = counter.get_all_counts();
    assert_eq!(
        pairs.len(),
        1,
        "exactly one k-mer is expected in the counter"
    );
    assert_eq!(pairs[0].1, COUNT, "the count must have accumulated");

    let dir = TempDir::new()?;
    let data = production_write_path(dir.path(), K as u8, pairs, false)?;

    assert_eq!(
        data.len(),
        20,
        "a one-entry .rkdb data section is exactly one 20-byte record; got {} bytes, which also \
         re-pins the {}-byte header offset the slice below relies on",
        data.len(),
        RKDB_V2_HEADER_BYTES
    );
    assert_eq!(
        &data[0..8],
        &u64::MAX.to_le_bytes(),
        "the low 8 bytes must be the k-mer's own little-endian u64"
    );
    assert_eq!(
        &data[8..16],
        &[0u8; 8],
        "the high 8 bytes must be all zero on disk — this is the u64 -> u128 zero-extension, \
         observed in the file rather than asserted about the code"
    );
    assert_eq!(
        &data[16..20],
        &COUNT.to_le_bytes(),
        "the trailing 4 bytes are the little-endian count"
    );
    Ok(())
}

/// A write must depend only on the data, not on the order it arrived in or on a
/// header field that was never initialized.
///
/// Write a database, read it back with the production reader, write it again,
/// and require the two files to be byte-identical. The manifest re-hash cannot
/// see this class of drift at all: its fixtures are never regenerated, so a
/// write path that grew order-dependence or left a header field uninitialized
/// would pass every other test in this binary.
#[test]
fn write_read_write_is_byte_idempotent() -> Result<()> {
    let k = TABLE_K as usize;
    let counter = KmerCounter::new(k, true, 16, 1)?;
    for (dna, times) in KMER_TABLE {
        let encoded = encode_kmer_bytes_u128(dna.as_bytes())
            .map_err(|e| anyhow::anyhow!("encode {}: {}", dna, e))?;
        for _ in 0..*times {
            counter.increment(encoded)?;
        }
    }

    let dir = TempDir::new()?;
    let first = dir.path().join("a.rkdb");
    let second = dir.path().join("b.rkdb");

    let db = RKDatabase::from_kmer_pairs(counter.get_all_counts(), TABLE_K, true, true)?;
    db.to_file_path(&first)?;

    let reread = RKDatabase::from_file_path(&first)?;
    assert_eq!(
        reread.entries.len(),
        db.entries.len(),
        "the reader must return every record the writer emitted"
    );
    reread.to_file_path(&second)?;

    let first_bytes =
        std::fs::read(&first).map_err(|e| anyhow::anyhow!("read {}: {}", first.display(), e))?;
    let second_bytes =
        std::fs::read(&second).map_err(|e| anyhow::anyhow!("read {}: {}", second.display(), e))?;

    assert!(
        first_bytes == second_bytes,
        "{}",
        describe_difference(&first_bytes, &second_bytes)
    );
    Ok(())
}
