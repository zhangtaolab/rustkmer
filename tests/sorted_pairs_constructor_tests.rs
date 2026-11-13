//! Phase 9 (PY-01) — byte contract for `RKDatabase::from_sorted_kmer_pairs`.
//!
//! The new constructor trusts the caller's ascending order and marks the
//! header `sorted: true` without sorting. It exists only to remove the second
//! sort from the PyO3 `save_database` path, so its ONLY acceptable behavior is
//! emitting exactly the bytes the frozen four-argument constructor emits for
//! the same already-sorted pairs.
//!
//! What this binary observes:
//!
//! | Test | Contract |
//! |---|---|
//! | `sorted_constructor_matches_from_kmer_pairs_sorted` | in-memory bytes and `TempDir` files are identical to `from_kmer_pairs(.., sorted: true)` |
//! | `sorted_constructor_empty_input` | empty input yields a 42-byte header-only file, `sorted == true`, record count 0 |
//! | `sorted_constructor_single_entry` | one entry round-trips through disk with record count 1 |
//! | `sorted_constructor_reproduces_the_k21_canonical_golden` | the k21/canonical golden input hashes to `a5da813e…` and matches the committed fixture |
//! | `sorted_constructor_debug_asserts_unsorted_input` | debug builds panic on descending input (release builds are caller-contract only) |
//!
//! What it does NOT observe: it never writes to `tests/fixtures/`, never
//! regenerates a fixture, and never edits the frozen header/entry writers.
//!
//! `tests/*.rs` files are separate test binaries, so the small helpers are
//! deliberately duplicated from `tests/output_pipeline_tests.rs` (same pattern
//! as `tests/golden_sha256_tests.rs`).

use std::collections::BTreeMap;
use std::fs;
use std::path::PathBuf;

use rustkmer::database::format::RKDatabase;
use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::kmer::encoding::encode_kmer_bytes_u128;
use sha2::{Digest, Sha256};
use tempfile::TempDir;

/// The fixed golden input — MUST match `tests/golden_generate.rs::GOLDEN_INPUT`
/// and `tests/output_pipeline_tests.rs`, otherwise the compared k-mer sets
/// differ and the byte-identity claim is meaningless.
const GOLDEN_INPUT: &[&str] = &[
    "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTAC",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "ACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACAC",
    "GTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGT",
    "AAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAA",
    "GATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATT",
];

/// `tests/fixtures/golden_k21_canon_sorted.rkdb` (pre-refactor baseline).
const GOLDEN_K21_CANON_SORTED_SHA256: &str =
    "a5da813e2977157afc4b8c395dc6fbc721516024c52cb257208490e29b796af7";

/// Committed fixture path — read only, never written.
fn golden_fixture_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("fixtures")
        .join("golden_k21_canon_sorted.rkdb")
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

/// A deterministic, intentionally shuffled pair vector with unique keys.
fn deterministic_pairs() -> Vec<(u128, u32)> {
    let mut pairs: Vec<(u128, u32)> = (0..40u128)
        .map(|i| {
            // Spread keys across the u128 space; unique by construction.
            let key = (i * 7919 + 13) << 64 | (i * 104_729 + 3);
            let count = (i as u32) % 7 + 1;
            (key, count)
        })
        .collect();
    pairs.reverse(); // deliberately unsorted before the caller sorts
    pairs
}

/// Count the golden input exactly as the CLI does: slide k-wide windows,
/// encode, canonicalize, accumulate.
fn golden_pairs(k: usize, canonical: bool) -> Vec<(u128, u32)> {
    let mut acc: BTreeMap<u128, u32> = BTreeMap::new();
    for seq in GOLDEN_INPUT {
        let bytes = seq.as_bytes();
        if bytes.len() < k {
            continue;
        }
        for window in bytes.windows(k) {
            let kmer = encode_kmer_bytes_u128(window).expect("encode golden window");
            let kmer = if canonical {
                canonical_kmer_u128(kmer, k).expect("canonicalize golden window")
            } else {
                kmer
            };
            *acc.entry(kmer).or_insert(0) += 1;
        }
    }
    acc.into_iter().collect()
}

#[test]
fn sorted_constructor_matches_from_kmer_pairs_sorted() {
    let mut pairs = deterministic_pairs();
    // The caller owns the ordering proof: sort exactly once, then hand the
    // result to the sorted-input constructor.
    pairs.sort_by_key(|&(kmer, _)| kmer);

    // In-memory byte comparison through the frozen `write_to`.
    let mut new_bytes: Vec<u8> = Vec::new();
    RKDatabase::from_sorted_kmer_pairs(pairs.clone(), 21, true)
        .expect("from_sorted_kmer_pairs")
        .write_to(&mut new_bytes)
        .expect("write_to (new constructor)");

    let mut frozen_bytes: Vec<u8> = Vec::new();
    RKDatabase::from_kmer_pairs(pairs.clone(), 21, true, true)
        .expect("from_kmer_pairs(sorted=true)")
        .write_to(&mut frozen_bytes)
        .expect("write_to (frozen constructor)");

    assert_eq!(
        new_bytes, frozen_bytes,
        "the sorted-input constructor must emit exactly the frozen writer's bytes"
    );

    // The same comparison through real files on disk.
    let dir = TempDir::new().expect("tempdir for byte comparison");
    let new_path = dir.path().join("new.rkdb");
    let frozen_path = dir.path().join("frozen.rkdb");

    RKDatabase::from_sorted_kmer_pairs(pairs.clone(), 21, true)
        .expect("from_sorted_kmer_pairs (file arm)")
        .write_to_file(&new_path)
        .expect("write_to_file (new constructor)");
    RKDatabase::from_kmer_pairs(pairs, 21, true, true)
        .expect("from_kmer_pairs (file arm)")
        .write_to_file(&frozen_path)
        .expect("write_to_file (frozen constructor)");

    let new_file_bytes = fs::read(&new_path).expect("read new file arm");
    let frozen_file_bytes = fs::read(&frozen_path).expect("read frozen file arm");
    assert_eq!(
        new_file_bytes, frozen_file_bytes,
        "file-written bytes must be identical to the frozen constructor's"
    );
    assert_eq!(new_file_bytes, new_bytes, "file and in-memory arms agree");
}

#[test]
fn sorted_constructor_empty_input() {
    let dir = TempDir::new().expect("tempdir for empty input");
    let out = dir.path().join("empty.rkdb");

    let db = RKDatabase::from_sorted_kmer_pairs(Vec::new(), 21, true)
        .expect("from_sorted_kmer_pairs(empty)");
    assert!(db.header.sorted, "empty database still claims sorted");
    assert_eq!(db.header.total_kmers, 0, "IN-03 record count is zero");
    assert_eq!(db.header.unique_kmers, 0);
    assert!(db.entries.is_empty());

    db.write_to_file(&out).expect("write empty database");
    let bytes = fs::read(&out).expect("read empty database");
    assert_eq!(bytes.len(), 42, "header-only file is exactly 42 bytes");
}

#[test]
fn sorted_constructor_single_entry() {
    let dir = TempDir::new().expect("tempdir for single entry");
    let out = dir.path().join("single.rkdb");

    let key: u128 = 0x0123_4567_89ab_cdef_0123_4567_89ab_cdefu128;
    let db = RKDatabase::from_sorted_kmer_pairs(vec![(key, 42u32)], 21, false)
        .expect("from_sorted_kmer_pairs(single)");
    assert!(db.header.sorted);
    assert_eq!(db.header.total_kmers, 1, "IN-03 record count is one");
    assert_eq!(db.header.unique_kmers, 1);

    db.write_to_file(&out).expect("write single-entry database");

    let loaded = RKDatabase::from_file_path(&out).expect("read single-entry database");
    assert_eq!(loaded.entries.len(), 1);
    assert_eq!(loaded.entries[0].kmer, key, "the encoded key round-trips");
    assert_eq!(loaded.entries[0].count, 42, "the count round-trips");
    assert!(loaded.header.sorted, "sorted flag round-trips");
    assert_eq!(loaded.header.total_kmers, 1);
}

#[test]
fn sorted_constructor_reproduces_the_k21_canonical_golden() {
    let k = 21usize;
    let pairs = golden_pairs(k, true);
    assert!(!pairs.is_empty(), "the golden input must produce records");

    let dir = TempDir::new().expect("tempdir for golden reproduction");
    let out = dir.path().join("golden-k21-canon-sorted.rkdb");

    let db = RKDatabase::from_sorted_kmer_pairs(pairs.clone(), k as u8, true)
        .expect("from_sorted_kmer_pairs(golden)");
    assert!(db.header.sorted, "golden header must be sorted");
    assert_eq!(
        db.header.total_kmers as usize,
        db.entries.len(),
        "IN-03: header record count equals the number of entries"
    );
    assert_eq!(db.header.total_kmers as usize, pairs.len());

    db.write_to_file(&out).expect("write golden database");

    let produced = fs::read(&out).expect("read produced golden");
    let produced_sha = sha256_hex(&produced);
    assert_eq!(
        produced_sha, GOLDEN_K21_CANON_SORTED_SHA256,
        "the sorted-input constructor must reproduce the committed golden bytes"
    );

    let fixture = fs::read(golden_fixture_path()).expect("read committed golden fixture");
    assert_eq!(
        sha256_hex(&fixture),
        GOLDEN_K21_CANON_SORTED_SHA256,
        "the committed fixture must still hash to the pinned golden value"
    );
    assert_eq!(
        produced, fixture,
        "produced bytes must equal the committed fixture byte-for-byte"
    );
}

#[cfg(debug_assertions)]
#[test]
fn sorted_constructor_debug_asserts_unsorted_input() {
    // Descending keys violate the caller contract. In debug builds (the
    // default `cargo test` profile) the constructor must panic rather than
    // silently emit a file whose header claims `sorted: true`.
    let descending: Vec<(u128, u32)> = vec![(9, 1), (5, 2), (1, 3)];

    let result = std::panic::catch_unwind(|| {
        // The return value is irrelevant; the call must panic.
        let _ = RKDatabase::from_sorted_kmer_pairs(descending, 21, true);
    });

    assert!(
        result.is_err(),
        "from_sorted_kmer_pairs must panic on descending input in debug builds"
    );
}
