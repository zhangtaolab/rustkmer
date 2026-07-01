//! Write→read round-trip tests for the `.rkdb` format.
//!
//! Plan 01-03, Task 2 (decision D-09, SPEC R3 acceptance).
//!
//! Asserts that a database written via `RKDatabase::write_to_file` reads back
//! via `RKDatabase::from_file_path` with byte-identical k-mer counts. Reuses
//! the shared factories in `tests/common/mod.rs`. This guards against any
//! Task 3 refactor introducing a read/write asymmetry that the golden sha256
//! check (which only exercises the write side) might miss.

mod common;

use common::*;
use rustkmer::database::format::RKDatabase;

/// Adapter: the shared factories return `TestResult<T>` = `Result<T, Box<dyn
/// Error>>`, whose error is not `Send + Sync + 'static` and so cannot flow
/// into `anyhow::Result` via `?`. Box-to-anyhow conversion is the standard
/// bridge; centralised here to keep test bodies readable.
trait TestResultExt<T> {
    fn a(self) -> anyhow::Result<T>;
}

impl<T> TestResultExt<T> for Result<T, Box<dyn std::error::Error>> {
    fn a(self) -> anyhow::Result<T> {
        self.map_err(|e| anyhow::anyhow!("{}", e))
    }
}

/// Write a small database, read it back, assert identical k-mer counts.
#[test]
fn round_trip_preserves_kmer_counts() -> anyhow::Result<()> {
    let kmers = vec![
        (0x1234_5678_9ABC_DEF0_1234_5678_9ABC_DEF0u128, 7u32),
        (0x0000_0000_0000_0000_0000_0000_0000_0001u128, 3u32),
        (0xFFFF_FFFF_FFFF_FFFF_FFFF_FFFF_FFFF_FFFEu128, 11u32),
        (0xDEAD_BEEF_DEAD_BEEF_DEAD_BEEF_DEAD_BEEFu128, 1u32),
    ];
    let original = create_database_from_kmers(kmers.clone(), 21, true, true).a()?;

    let tmp = tempfile::NamedTempFile::new()?;
    original.write_to_file(tmp.path())?;

    let reloaded = RKDatabase::from_file_path(tmp.path())?;

    assert!(
        databases_have_same_kmers(&original, &reloaded).a()?,
        "round-trip: reloaded database k-mers differ from original"
    );
    Ok(())
}

/// Round-trip across the D-13 coverage matrix — every (k, canonical, sorted)
/// combination must survive a write→read cycle.
#[test]
fn round_trip_full_matrix() -> anyhow::Result<()> {
    for &k in &[21usize, 32, 64] {
        for &canonical in &[true, false] {
            for &sorted in &[true, false] {
                let original = create_test_database(50, k as u8, canonical, sorted).a()?;
                let tmp = tempfile::NamedTempFile::new()?;
                original.write_to_file(tmp.path())?;
                let reloaded = RKDatabase::from_file_path(tmp.path())?;

                assert!(
                    databases_have_same_kmers(&original, &reloaded).a()?,
                    "round-trip failed for k={}, canonical={}, sorted={}",
                    k,
                    canonical,
                    sorted
                );
                assert_eq!(
                    original.total_kmers(),
                    reloaded.total_kmers(),
                    "total_kmers header mismatch for k={}, canonical={}, sorted={}",
                    k,
                    canonical,
                    sorted
                );
            }
        }
    }
    Ok(())
}

/// Round-trip must preserve the canonical flag in the header (the query path
/// branches on it, so a lost flag would silently break canonical lookups).
#[test]
fn round_trip_preserves_canonical_flag() -> anyhow::Result<()> {
    let kmers = vec![(42u128, 5u32), (99u128, 9u32)];
    for canonical in &[true, false] {
        let db = create_database_from_kmers(kmers.clone(), 21, *canonical, true).a()?;
        let tmp = tempfile::NamedTempFile::new()?;
        db.write_to_file(tmp.path())?;
        let reloaded = RKDatabase::from_file_path(tmp.path())?;
        assert_eq!(
            db.is_canonical(),
            reloaded.is_canonical(),
            "canonical flag not preserved on round-trip (expected {})",
            *canonical
        );
    }
    Ok(())
}
