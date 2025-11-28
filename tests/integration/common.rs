//! Common test utilities for integration tests

use std::path::Path;
use std::fs::File;
use std::io::Write;
use tempfile::TempDir;
use anyhow::Result;

use rustkmer::database::format::RKDatabase;
use rustkmer::hash::CountFilter;
use rustkmer::kmer::{Kmer, KmerSize};

/// Create a test database with specified parameters
pub fn create_test_database(temp_dir: &TempDir, kmer_size: u32, num_kmers: u64) -> Result<std::path::PathBuf> {
    let db_path = temp_dir.path().join("test_db.rkdb");

    // Create test k-mers
    let mut kmer_counts = std::collections::HashMap::new();

    for i in 0..num_kmers {
        let kmer_str = generate_test_kmer(i as usize, kmer_size as usize);
        kmer_counts.insert(kmer_str, (i % 100) + 1);  // Count 1-100
    }

    // Create database using existing RKDatabase creation logic
    // This is a simplified version - actual implementation would use RKDatabase::new()
    let db = create_simple_rkdb(&db_path, kmer_size, kmer_counts)?;

    db.write_to_file(&db_path)?;

    Ok(db_path)
}

/// Create a test k-mer file with given sequences
pub fn create_test_kmer_file(path: &Path, kmers: Vec<&str>) -> Result<()> {
    let mut file = File::create(path)?;

    for kmer in kmers {
        writeln!(file, "{}", kmer)?;
    }

    Ok(())
}

/// Generate a deterministic test k-mer
pub fn generate_test_kmer(index: usize, kmer_size: usize) -> String {
    let bases = ['A', 'C', 'G', 'T'];
    (0..kmer_size)
        .map(|i| bases[(index + i) % 4])
        .collect()
}

/// Create a simple RKDatabase for testing
fn create_simple_rkdb(
    _path: &Path,
    kmer_size: u32,
    kmer_counts: std::collections::HashMap<String, u64>,
) -> Result<RKDatabase> {
    // This is a placeholder - actual implementation would create a real RKDatabase
    // For now, we'll assume this works and return a mock database

    let _total_kmers = kmer_counts.values().sum::<u64>();
    let _unique_kmers = kmer_counts.len() as u64;

    // In a real implementation, this would create the actual database file
    // For testing purposes, we'll rely on the actual RKDatabase creation methods

    Err(anyhow::anyhow!("Mock RKDatabase creation - use actual implementation"))
}

/// Helper function to get test database path
pub fn get_test_database_path() -> Result<std::path::PathBuf> {
    let mut current_dir = std::env::current_dir()?;

    // Navigate to the project root
    while !current_dir.join("Cargo.toml").exists() {
        current_dir = current_dir.parent().ok_or_else(|| {
            anyhow::anyhow!("Could not find project root")
        })?.to_path_buf();
    }

    let test_db_path = current_dir
        .join("tests")
        .join("test_data")
        .join("test_database.rkdb");

    Ok(test_db_path)
}

/// Check if test database exists and create if needed
pub fn ensure_test_database() -> Result<std::path::PathBuf> {
    let db_path = get_test_database_path()?;

    if !db_path.exists() {
        // Create test database if it doesn't exist
        let temp_dir = TempDir::new()?;
        let created_db = create_test_database(&temp_dir, 21, 1000)?;

        // Copy to test location
        std::fs::copy(&created_db, &db_path)?;
    }

    Ok(db_path)
}