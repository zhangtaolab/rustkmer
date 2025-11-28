//! Tests for canonical k-mer encoding consistency in query functionality

use rustkmer::database::query::DatabaseQuery;
use rustkmer::database::format::{DatabaseHeader, DATABASE_MAGIC, DATABASE_VERSION};
use std::fs::File;
use std::io::{BufWriter, Write};

#[test]
fn test_query_kmer_with_canonical_database_should_work() {
    // Create a test database with canonical k-mers
    let test_db_path = "test_canonical_db.rkdb";

    // Database header for canonical k-mers
    let header = DatabaseHeader {
        magic: *DATABASE_MAGIC,
        version: DATABASE_VERSION,
        kmer_size: 21,
        total_kmers: 3,
        sorted: true,
        data_offset: 40, // sizeof(DatabaseHeader)
        index_offset: 0,
        canonical: true,
    };

    // Create test database file
    {
        let mut file = File::create(test_db_path).expect("Failed to create test database file");
        let mut writer = BufWriter::new(&mut file);

        // Write header
        header.write_to(&mut writer).expect("Failed to write header");

        // Write test k-mer entries (kmer, count) - using encoded values that would result from canonical encoding
        // These are example values - actual encoding would need proper implementation
        let test_entries = vec![
            (0x0000000000000000u64, 1u32), // AAAAAAAAAAAAAAAAAAAAA - canonical encoding
            (0x123456789ABCDEF0u64, 1u32), // ATGCGATGCTAGCGCTAGCTA - canonical encoding
            (0x56789ABCDEF01234u64, 1u32), // CGATCGATCGATCGATCGATC - canonical encoding
        ];

        for (kmer, count) in test_entries {
            writer.write_all(&kmer.to_le_bytes()).expect("Failed to write kmer");
            writer.write_all(&count.to_le_bytes()).expect("Failed to write count");
        }
    }

    // Test querying the database
    {
        let mut query = DatabaseQuery::open(test_db_path, false)
            .expect("Failed to open database for querying");

        // Test querying k-mers that should be found
        let test_kmers = vec![
            "AAAAAAAAAAAAAAAAAAAAA",
            "ATGCGATGCTAGCGCTAGCTA",
            "CGATCGATCGATCGATCGATC"
        ];

        for kmer_seq in test_kmers {
            let result = query.query_kmer(kmer_seq)
                .expect("Query should not fail");

            // The k-mer should be found since it exists in our canonical database
            assert!(result.is_some(),
                "K-mer '{}' should be found in canonical database", kmer_seq);

            let count = result.unwrap();
            assert_eq!(count, 1,
                "K-mer '{}' should have count 1, got {}", kmer_seq, count);
        }
    }

    // Cleanup
    std::fs::remove_file(test_db_path).ok();
}

#[test]
fn test_query_kmer_canonical_encoding_mismatch_should_fail() {
    // This test demonstrates the bug: when database was created with canonical mode
    // but query doesn't apply canonical transformation, the lookup fails

    // Create a database with canonical k-mers (already done in setup)
    let canonical_db_path = "test_database.rkdb";

    // Query with original k-mer that should have canonical transformation applied
    let original_kmer = "TTATATATATATATATATATA"; // Reverse complement of AAAAA...
    let canonical_kmer = "ATATATATATATATATATA";  // Should be the canonical form

    // Test that current implementation fails (this test will initially fail)
    let mut query = DatabaseQuery::open(canonical_db_path, false)
        .expect("Failed to open database for querying");

    // This should fail because current query doesn't apply canonical transformation
    let result = query.query_kmer(original_kmer)
        .expect("Query should not fail");

    // Current buggy behavior: returns None or wrong count
    // Expected behavior after fix: should return Some(1)
    assert!(result.is_some(),
        "Canonical k-mer transformation should make query succeed");
    assert_eq!(result.unwrap(), 1,
        "Should return correct count for canonical k-mer");
}

#[test]
fn test_database_canonical_flag_consistency() {
    // Test that database header correctly reflects canonical mode
    let canonical_db_path = "test_database.rkdb";

    let mut query = DatabaseQuery::open(canonical_db_path, false)
        .expect("Failed to open database");

    let header = query.get_info();
    assert!(header.canonical, "Database should be marked as canonical");
    assert_eq!(header.kmer_size, 21, "Database should have k-mer size 21");
    assert_eq!(header.total_kmers, 3, "Database should have 3 k-mers");
}