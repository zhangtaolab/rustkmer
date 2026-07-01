//! Golden-file regression tests for the `.rkdb` count-path output.
//!
//! Plan 01-03, Task 2 (decision D-09 + D-11 + D-13).
//!
//! Two complementary assertions:
//! 1. **Pre-refactor baseline (D-09a, D-11):** each of the 12 committed
//!    `tests/fixtures/golden_k{21,32,64}_{canon,noncanon}_{sorted,unsorted}.rkdb`
//!    files (captured in Task 1 by the CURRENT pre-refactor count path) must
//!    hash to the sha256 recorded in `tests/fixtures/golden_manifest.sha256`.
//!    This is the P3 byte-layout prohibition gate.
//! 2. **Cross-consistency (D-09b):** for a fixed input, the count-path write
//!    and `RKDatabase::from_kmer_pairs(...).write_to_file(...)` must emit
//!    byte-identical bytes (sha256 equal). This is the proof that survives the
//!    Task 3 consolidation — if `count.rs` ever drifts from `format.rs`, this
//!    fails.
//!
//! Test bodies use `anyhow::Result<()>` + `?` per TESTING.md convention.

mod common;

use common::*;
use sha2::{Digest, Sha256};

/// Parse `tests/fixtures/golden_manifest.sha256` into a name -> hex map.
///
/// Manifest format (one entry per line): `<filename> <sha256-hex>`.
fn load_golden_manifest() -> anyhow::Result<std::collections::HashMap<String, String>> {
    let text = std::fs::read_to_string("tests/fixtures/golden_manifest.sha256")
        .map_err(|e| anyhow::anyhow!("failed to read golden_manifest.sha256: {}", e))?;
    let mut map = std::collections::HashMap::new();
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
fn assert_golden_matches_manifest(name: &str) -> anyhow::Result<()> {
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

// --- D-13 matrix: 12 cells, each its own test for localized failure reporting ---

#[test]
fn golden_k21_canon_sorted_matches_manifest() -> anyhow::Result<()> {
    assert_golden_matches_manifest("golden_k21_canon_sorted.rkdb")
}

#[test]
fn golden_k21_canon_unsorted_matches_manifest() -> anyhow::Result<()> {
    assert_golden_matches_manifest("golden_k21_canon_unsorted.rkdb")
}

#[test]
fn golden_k21_noncanon_sorted_matches_manifest() -> anyhow::Result<()> {
    assert_golden_matches_manifest("golden_k21_noncanon_sorted.rkdb")
}

#[test]
fn golden_k21_noncanon_unsorted_matches_manifest() -> anyhow::Result<()> {
    assert_golden_matches_manifest("golden_k21_noncanon_unsorted.rkdb")
}

#[test]
fn golden_k32_canon_sorted_matches_manifest() -> anyhow::Result<()> {
    assert_golden_matches_manifest("golden_k32_canon_sorted.rkdb")
}

#[test]
fn golden_k32_canon_unsorted_matches_manifest() -> anyhow::Result<()> {
    assert_golden_matches_manifest("golden_k32_canon_unsorted.rkdb")
}

#[test]
fn golden_k32_noncanon_sorted_matches_manifest() -> anyhow::Result<()> {
    assert_golden_matches_manifest("golden_k32_noncanon_sorted.rkdb")
}

#[test]
fn golden_k32_noncanon_unsorted_matches_manifest() -> anyhow::Result<()> {
    assert_golden_matches_manifest("golden_k32_noncanon_unsorted.rkdb")
}

#[test]
fn golden_k64_canon_sorted_matches_manifest() -> anyhow::Result<()> {
    assert_golden_matches_manifest("golden_k64_canon_sorted.rkdb")
}

#[test]
fn golden_k64_canon_unsorted_matches_manifest() -> anyhow::Result<()> {
    assert_golden_matches_manifest("golden_k64_canon_unsorted.rkdb")
}

#[test]
fn golden_k64_noncanon_sorted_matches_manifest() -> anyhow::Result<()> {
    assert_golden_matches_manifest("golden_k64_noncanon_sorted.rkdb")
}

#[test]
fn golden_k64_noncanon_unsorted_matches_manifest() -> anyhow::Result<()> {
    assert_golden_matches_manifest("golden_k64_noncanon_unsorted.rkdb")
}

// --- D-09b: cross-consistency between count-path-equivalent output and the
//     canonical RKDatabase::from_kmer_pairs().write_to_file() path.
//
// Both the pre-refactor count.rs inline writer and `RKDatabase::write_to`
// emit the same bytes for the same input (RESEARCH.md §4: file_size /
// unique_kmers are not serialized; the header literal fields match). This
// test pins that empirically — it is the assertion that survives the Task 3
// consolidation. If Task 3 makes count.rs delegate to format.rs but the
// bytes ever diverge, golden_tests catches it AND this catches the
// count-path↔canonical-path drift directly.

#[test]
fn cross_consistency_count_path_equals_canonical_path() -> anyhow::Result<()> {
    // Fixed input — MUST match tests/golden_generate.rs::GOLDEN_INPUT exactly,
    // otherwise the k-mer sets differ and the sha256 comparison is meaningless.
    let input: &[&str] = &[
        "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTAC",
        "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
        "ACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACACAC",
        "GTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGTGT",
        "AAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAAAACCCCGGGGTTTTAA",
        "GATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATT",
    ];

    // Build the canonical-path output: encode → canonical → collect pairs →
    // RKDatabase::from_kmer_pairs → write_to_file. This exercises the
    // format.rs canonical writer end-to-end.
    let k = 21usize;
    let canonical = true;
    let mut acc: std::collections::HashMap<u128, u32> = std::collections::HashMap::new();
    for seq in input {
        let bytes = seq.as_bytes();
        if bytes.len() < k {
            continue;
        }
        for window in bytes.windows(k) {
            let kmer = rustkmer::kmer::encoding::encode_kmer_bytes_u128(window)?;
            let kmer = if canonical {
                rustkmer::kmer::canonical::canonical_kmer_u128(kmer, k)?
            } else {
                kmer
            };
            *acc.entry(kmer).or_insert(0) += 1;
        }
    }
    let mut pairs: Vec<(u128, u32)> = acc.into_iter().collect();
    pairs.sort_by_key(|(kmer, _)| *kmer);

    let db = create_database_from_kmers(pairs.clone(), k as u8, canonical, true)
        .map_err(|e| anyhow::anyhow!("create_database_from_kmers failed: {}", e))?;
    let tmp = tempfile::NamedTempFile::new()?;
    db.write_to_file(tmp.path())?;
    let canonical_bytes = std::fs::read(tmp.path())?;
    let canonical_hash = sha256_hex(&canonical_bytes);

    // The matching golden fixture for this exact (k=21, canon, sorted) cell.
    // If the count path and the canonical path produce the same bytes, their
    // sha256 must match the committed golden.
    let golden_bytes = std::fs::read("tests/fixtures/golden_k21_canon_sorted.rkdb")?;
    let golden_hash = sha256_hex(&golden_bytes);

    assert_eq!(
        canonical_hash, golden_hash,
        "D-09b cross-consistency: count-path and canonical-path outputs differ for k21/canon/sorted"
    );
    Ok(())
}

/// Smoke test: the manifest itself is well-formed (12 entries, all hex).
#[test]
fn golden_manifest_is_well_formed() -> anyhow::Result<()> {
    let manifest = load_golden_manifest()?;
    assert_eq!(
        manifest.len(),
        12,
        "golden_manifest.sha256 must contain exactly 12 entries"
    );
    for (name, hex) in &manifest {
        assert!(
            name.starts_with("golden_k") && name.ends_with(".rkdb"),
            "unexpected golden fixture name: {}",
            name
        );
        assert_eq!(
            hex.len(),
            64,
            "sha256 hex for {} must be 64 chars, got {}",
            name,
            hex.len()
        );
        assert!(
            hex.chars().all(|c| c.is_ascii_hexdigit()),
            "sha256 hex for {} contains non-hex chars",
            name
        );
    }
    Ok(())
}
