//! Legacy read-back tests for `.rkdb` files with `data_offset = 42`.
//!
//! Plan 01-03, Task 2 (decision D-12, SPEC R3 edge coverage: boundary).
//!
//! `tests/fixtures/legacy_v2_offset42.rkdb` was captured in Task 1 by the
//! CURRENT pre-refactor code (4 k-mers, header `data_offset = 42`). Task 3
//! replaces the silent `data_offset` reconciliation clamp with a loud error.
//! Because this fixture's `data_offset` is the canonical 42, the loud error
//! must NOT fire on it — the legacy sample must still read cleanly.
//!
//! Additionally, this test pins a specific known k-mer/count pair into the
//! fixture so that any future header-layout drift is caught here, not just by
//! the golden sha256.

use rustkmer::database::format::RKDatabase;
use rustkmer::kmer::encoding::encode_kmer_bytes_u128;

const LEGACY_PATH: &str = "tests/fixtures/legacy_v2_offset42.rkdb";

/// The legacy fixture loads via the post-refactor reader and reports nonzero
/// k-mers.
#[test]
fn legacy_offset42_loads_post_refactor() -> anyhow::Result<()> {
    let db = RKDatabase::from_file_path(std::path::Path::new(LEGACY_PATH))
        .map_err(|e| anyhow::anyhow!("legacy fixture failed to load post-refactor: {}", e))?;

    let kmers = db.all_kmers()?;
    assert!(
        !kmers.is_empty(),
        "legacy fixture must contain nonzero k-mers"
    );
    assert_eq!(
        kmers.len(),
        4,
        "legacy fixture was generated with exactly 4 k-mers"
    );
    assert_eq!(
        db.header().data_offset,
        42,
        "legacy fixture data_offset must be 42"
    );
    Ok(())
}

/// A specific known k-mer from the Task 1 generator input is present with its
/// expected count. This guards against the fixture being silently regenerated
/// with different input.
#[test]
fn legacy_offset42_known_kmer_present() -> anyhow::Result<()> {
    let db = RKDatabase::from_file_path(std::path::Path::new(LEGACY_PATH))?;
    let kmers = db.all_kmers()?;

    // One of the 4 k-mers hardcoded in tests/golden_generate.rs's legacy
    // sample: b"ACGTACGTACGTACGTACGTA" with count 7.
    let expected_kmer = encode_kmer_bytes_u128(b"ACGTACGTACGTACGTACGTA")?;
    let found = kmers
        .iter()
        .find(|(k, _)| *k == expected_kmer)
        .ok_or_else(|| {
            anyhow::anyhow!("expected k-mer ACGTACGTACGTACGTACGTA not in legacy fixture")
        })?;

    assert_eq!(
        found.1, 7,
        "expected count 7 for ACGTACGTACGTACGTACGTA in legacy fixture"
    );
    Ok(())
}

/// The legacy fixture also reads correctly through `DatabaseQuery::open`
/// (the streaming reader — the second data_offset site Task 3 changes).
/// Verified via the public `query_kmer` API: a known k-mer must resolve to
/// its expected count.
#[test]
fn legacy_offset42_reads_via_database_query() -> anyhow::Result<()> {
    use rustkmer::database::query::DatabaseQuery;
    let mut dq = DatabaseQuery::open(LEGACY_PATH, true)?;
    // Query the same k-mer pinned by legacy_offset42_known_kmer_present.
    let count = dq.query_kmer("ACGTACGTACGTACGTACGTA")?;
    assert_eq!(
        count,
        Some(7),
        "DatabaseQuery must resolve the legacy ACGT...ACGTA k-mer to count 7"
    );
    Ok(())
}
