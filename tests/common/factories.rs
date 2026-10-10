//! Self-test-free factory core of the shared test-helper library.
//!
//! Integration-test binaries that need only the database factories include
//! this file directly (`#[path = "common/factories.rs"] mod common;`) instead
//! of the full `common` module: pulling full `common` compiles the shared
//! helpers' OWN `#[cfg(test)]` self-tests into the binary — about 20 extra
//! `common::*::tests::*` cases per target, including timing-sensitive ones
//! (`test_performance_timer`'s wall-clock assertion flaked a CI run exactly
//! this way; see deferred-items.md's `mod common` entry and CI run
//! 37952454763).
//!
//! `tests/common/mod.rs` re-exports everything here (`pub use factories::*`)
//! so full-`common` binaries keep their unchanged `common::*` call sites —
//! there is exactly one definition of each factory, never a fork.

#![allow(dead_code)]

use rustkmer::database::format::RKDatabase;

/// Result type for test operations
pub type TestResult<T> = Result<T, Box<dyn std::error::Error>>;

/// Create a test database with specified number of k-mers
pub fn create_test_database(
    num_kmers: usize,
    kmer_size: u8,
    canonical: bool,
    sorted: bool,
) -> TestResult<RKDatabase> {
    let mut kmers = Vec::with_capacity(num_kmers);

    for i in 0..num_kmers {
        let kmer = encode_test_kmer(i as u64, kmer_size);
        kmers.push((kmer, (i % 1000 + 1) as u32));
    }

    if sorted {
        kmers.sort_by_key(|(kmer, _)| *kmer);
    }

    RKDatabase::from_kmer_pairs(kmers, kmer_size, canonical, sorted).map_err(|e| e.into())
}

/// Create a test database with overlapping k-mers
pub fn create_overlapping_database(
    num_kmers: usize,
    kmer_size: u8,
    canonical: bool,
    sorted: bool,
    overlap_ratio: f64, // 0.0 to 1.0
) -> TestResult<(RKDatabase, Vec<(u128, u32)>)> {
    let mut kmers = Vec::with_capacity(num_kmers);
    let overlapping_kmers = (num_kmers as f64 * overlap_ratio) as usize;

    // Create overlapping k-mers (first N k-mers)
    for i in 0..overlapping_kmers {
        let kmer = encode_test_kmer(i as u64, kmer_size);
        kmers.push((kmer, (i % 100 + 1) as u32));
    }

    // Create unique k-mers (remaining)
    for i in overlapping_kmers..num_kmers {
        let kmer = encode_test_kmer((i + 1000000) as u64, kmer_size); // Offset to avoid overlap
        kmers.push((kmer, (i % 500 + 1) as u32));
    }

    let overlapping_snapshot = kmers[..overlapping_kmers].to_vec();

    if sorted {
        kmers.sort_by_key(|(kmer, _)| *kmer);
    }

    let db = RKDatabase::from_kmer_pairs(kmers, kmer_size, canonical, sorted)
        .map_err(|e| format!("Failed to create database: {}", e))?;

    Ok((db, overlapping_snapshot))
}

/// Create a test database from existing k-mer pairs
pub fn create_database_from_kmers(
    kmers: Vec<(u128, u32)>,
    kmer_size: u8,
    canonical: bool,
    sorted: bool,
) -> TestResult<RKDatabase> {
    let mut sorted_kmers = kmers;
    if sorted {
        sorted_kmers.sort_by_key(|(kmer, _)| *kmer);
    }

    RKDatabase::from_kmer_pairs(sorted_kmers, kmer_size, canonical, sorted).map_err(|e| e.into())
}

/// Generate a simple test k-mer encoding
pub fn encode_test_kmer(value: u64, kmer_size: u8) -> u128 {
    let mut kmer = 0u128;

    // Encode value as base-4 (A=0, C=1, G=2, T=3)
    let mut v = value;
    for i in 0..kmer_size {
        let base = (v % 4) as u128;
        kmer |= base << (2 * i);
        v /= 4;
    }

    kmer
}

/// Generate a sequence of k-mers for testing
pub fn generate_kmer_sequence(start: u64, count: usize, kmer_size: u8) -> Vec<u128> {
    (0..count)
        .map(|i| encode_test_kmer(start + i as u64, kmer_size))
        .collect()
}

/// Validate that two databases have the same k-mers (order-independent)
pub fn databases_have_same_kmers(db1: &RKDatabase, db2: &RKDatabase) -> TestResult<bool> {
    let kmers1: Vec<(u128, u32)> = db1
        .all_kmers()
        .map_err(|e| format!("Database error: {}", e))?;
    let kmers2: Vec<(u128, u32)> = db2
        .all_kmers()
        .map_err(|e| format!("Database error: {}", e))?;

    if kmers1.len() != kmers2.len() {
        return Ok(false);
    }

    let map1: std::collections::HashMap<u128, u32> = kmers1.into_iter().collect();
    let map2: std::collections::HashMap<u128, u32> = kmers2.into_iter().collect();

    Ok(map1 == map2)
}

/// Count total k-mer occurrences in a database
pub fn count_total_kmers(db: &RKDatabase) -> TestResult<u64> {
    db.all_kmers()
        .map_err(|e| e.into())
        .map(|kmers| kmers.iter().map(|(_, count)| *count as u64).sum())
}

/// Get unique k-mer count in a database
pub fn count_unique_kmers(db: &RKDatabase) -> TestResult<usize> {
    db.all_kmers()
        .map_err(|e| e.into())
        .map(|kmers| kmers.len())
}
