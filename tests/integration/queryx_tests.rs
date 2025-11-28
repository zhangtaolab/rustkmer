//! Integration tests for queryx parallel query processing
//!
//! Comprehensive test suite covering all aspects of parallel query functionality
//! including performance analysis, thread safety, and error handling.

use std::path::PathBuf;
use std::time::Duration;
use tempfile::TempDir;
use anyhow::Result;

use rustkmer::cli::commands::queryx::{execute_queryx, QueryXConfig};
use rustkmer::cli::args::Commands;
use rustkmer::database::parallel_query::{ThreadSafeDatabaseQuery, QueryXProcessor};
use rustkmer::database::format::RKDatabase;

mod common;

use common::*;

/// Test successful parallel query execution with small batch
#[test]
fn test_queryx_small_batch_success() -> Result<()> {
    let temp_dir = TempDir::new()?;
    let db_path = create_test_database(&temp_dir, 21, 100)?;
    let output_path = temp_dir.path().join("output.txt");

    let command = Commands::QueryX {
        database: db_path.to_str().unwrap().to_string(),
        kmers: Some(vec![
            "ATGCGATGCTAGCGCTAGCTA".to_string(),
            "GCTAGCTAGCTAGCTAGCTAG".to_string(),
            "TTAGGCCAATGCGATGCTAGC".to_string(),
        ]),
        file: None,
        threads: 2,
        batch_size: 10,
        preload: true,
        verbose: false,
        quiet: true,
        profile: true,
        progress: false,
        memory_limit_mb: None,
        output: Some(output_path.to_str().unwrap().to_string()),
    };

    let result = execute_queryx(&command);

    assert!(result.is_ok(), "QueryX execution should succeed");

    // Check that output file was created
    assert!(output_path.exists(), "Output file should be created");

    Ok(())
}

/// Test query execution with file input
#[test]
fn test_queryx_file_input() -> Result<()> {
    let temp_dir = TempDir::new()?;
    let db_path = create_test_database(&temp_dir, 21, 100)?;
    let kmer_file_path = temp_dir.path().join("kmers.txt");
    let output_path = temp_dir.path().join("output.txt");

    // Create test k-mer file
    create_test_kmer_file(&kmer_file_path, vec![
        "ATGCGATGCTAGCGCTAGCTA",
        "GCTAGCTAGCTAGCTAGCTAG",
        "TTAGGCCAATGCGATGCTAGC",
    ])?;

    let command = Commands::QueryX {
        database: db_path.to_str().unwrap().to_string(),
        kmers: None,
        file: Some(kmer_file_path.to_str().unwrap().to_string()),
        threads: 2,
        batch_size: 10,
        preload: false,
        verbose: false,
        quiet: true,
        profile: false,
        progress: false,
        memory_limit_mb: None,
        output: Some(output_path.to_str().unwrap().to_string()),
    };

    let result = execute_queryx(&command);

    assert!(result.is_ok(), "QueryX file input execution should succeed");

    Ok(())
}

/// Test error handling for invalid k-mers
#[test]
fn test_queryx_invalid_kmers() -> Result<()> {
    let temp_dir = TempDir::new()?;
    let db_path = create_test_database(&temp_dir, 21, 100)?;

    let command = Commands::QueryX {
        database: db_path.to_str().unwrap().to_string(),
        kmers: Some(vec![
            "ATGCGATGCTAGCGCTAGCTA".to_string(),
            "INVALIDKMER".to_string(),  // Contains invalid characters
            "TTAGGCCAATGCGATGCTAGC".to_string(),
        ]),
        file: None,
        threads: 2,
        batch_size: 10,
        preload: true,
        verbose: false,
        quiet: true,
        profile: false,
        progress: false,
        memory_limit_mb: None,
        output: None,
    };

    let result = execute_queryx(&command);

    assert!(result.is_err(), "QueryX should fail with invalid k-mers");

    Ok(())
}

/// Test error handling for non-existent database
#[test]
fn test_queryx_nonexistent_database() -> Result<()> {
    let command = Commands::QueryX {
        database: "/nonexistent/database.rkdb".to_string(),
        kmers: Some(vec!["ATGCGATGCTAGCGCTAGCTA".to_string()]),
        file: None,
        threads: 2,
        batch_size: 10,
        preload: true,
        verbose: false,
        quiet: true,
        profile: false,
        progress: false,
        memory_limit_mb: None,
        output: None,
    };

    let result = execute_queryx(&command);

    assert!(result.is_err(), "QueryX should fail with non-existent database");

    Ok(())
}

/// Test error handling for conflicting input options
#[test]
fn test_queryx_conflicting_inputs() -> Result<()> {
    let temp_dir = TempDir::new()?;
    let db_path = create_test_database(&temp_dir, 21, 100)?;
    let kmer_file_path = temp_dir.path().join("kmers.txt");

    // Create test k-mer file
    create_test_kmer_file(&kmer_file_path, vec!["ATGCGATGCTAGCGCTAGCTA"])?;

    let command = Commands::QueryX {
        database: db_path.to_str().unwrap().to_string(),
        kmers: Some(vec!["ATGCGATGCTAGCGCTAGCTA".to_string()]),
        file: Some(kmer_file_path.to_str().unwrap().to_string()),  // Conflict with kmers
        threads: 2,
        batch_size: 10,
        preload: true,
        verbose: false,
        quiet: true,
        profile: false,
        progress: false,
        memory_limit_mb: None,
        output: None,
    };

    let result = execute_queryx(&command);

    assert!(result.is_err(), "QueryX should fail with conflicting inputs");

    Ok(())
}

/// Test error handling for no input provided
#[test]
fn test_queryx_no_input() -> Result<()> {
    let temp_dir = TempDir::new()?;
    let db_path = create_test_database(&temp_dir, 21, 100)?;

    let command = Commands::QueryX {
        database: db_path.to_str().unwrap().to_string(),
        kmers: None,  // No input
        file: None,   // No input
        threads: 2,
        batch_size: 10,
        preload: true,
        verbose: false,
        quiet: true,
        profile: false,
        progress: false,
        memory_limit_mb: None,
        output: None,
    };

    let result = execute_queryx(&command);

    assert!(result.is_err(), "QueryX should fail with no input");

    Ok(())
}

/// Test thread-safe database access
#[test]
fn test_thread_safe_database_access() -> Result<()> {
    let temp_dir = TempDir::new()?;
    let db_path = create_test_database(&temp_dir, 21, 100)?;
    let database = RKDatabase::from_file_path(&db_path)?;
    let thread_safe_db = ThreadSafeDatabaseQuery::new(database);

    // Test concurrent database access
    let kmer = "ATGCGATGCTAGCGCTAGCTA";

    // Multiple threads should be able to query simultaneously
    let handles: Vec<_> = (0..10)
        .map(|_| {
            let ts_db = &thread_safe_db;
            let kmer = kmer.to_string();
            std::thread::spawn(move || {
                ts_db.query_kmer(&kmer)
            })
        })
        .collect();

    // Wait for all threads to complete
    for handle in handles {
        let result = handle.join().unwrap();
        assert!(result.is_ok(), "Thread-safe database query should succeed");
    }

    // Test database stats access
    let stats = thread_safe_db.get_stats()?;
    assert_eq!(stats.kmer_size, 21);

    Ok(())
}

/// Test QueryXProcessor with different batch sizes
#[test]
fn test_queryx_processor_batch_sizes() -> Result<()> {
    let temp_dir = TempDir::new()?;
    let db_path = create_test_database(&temp_dir, 21, 1000)?;

    let config = QueryXConfig {
        database_path: db_path,
        threads: 2,
        batch_size: 100,
        preload: true,
        verbose: false,
        quiet: true,
        profile: false,
        progress: false,
        memory_limit_mb: None,
        output_path: None,
    };

    let mut processor = QueryXProcessor::new(config)?;

    // Test with different batch sizes
    for batch_size in [10, 50, 100, 500] {
        let test_kmers: Vec<String> = (0..batch_size)
            .map(|i| format!("{:021}", i % 4).replace("0", "A").replace("1", "C").replace("2", "G").replace("3", "T"))
            .collect();

        let results = processor.process_queries(test_kmers.clone())?;

        assert_eq!(results.query_results.len(), batch_size);
        assert!(results.performance.queries_processed > 0);
        assert!(results.performance.total_time_ms > 0.0);
    }

    Ok(())
}

/// Test adaptive thread count optimization
#[test]
fn test_adaptive_thread_optimization() -> Result<()> {
    let temp_dir = TempDir::new()?;
    let db_path = create_test_database(&temp_dir, 21, 100)?;

    // Test with different batch sizes to verify adaptive thread behavior
    let test_cases = vec![
        (10, 1),    // Small batch: should use 1 thread
        (100, 2),   // Medium batch: should use partial threads
        (1000, 4),  // Large batch: should use more threads
    ];

    for (batch_size, expected_min_threads) in test_cases {
        let config = QueryXConfig {
            database_path: db_path.clone(),
            threads: 0,  // Auto-detect
            batch_size: 1000,
            preload: true,
            verbose: false,
            quiet: true,
            profile: false,
            progress: false,
            memory_limit_mb: None,
            output_path: None,
        };

        let mut processor = QueryXProcessor::new(config)?;

        let test_kmers: Vec<String> = (0..batch_size)
            .map(|i| format!("{:021}", i % 4).replace("0", "A").replace("1", "C").replace("2", "G").replace("3", "T"))
            .collect();

        let results = processor.process_queries(test_kmers)?;

        // Verify that thread count is reasonable for batch size
        assert!(results.performance.threads_used >= expected_min_threads);
    }

    Ok(())
}

/// Test performance analysis reporting
#[test]
fn test_performance_analysis() -> Result<()> {
    let temp_dir = TempDir::new()?;
    let db_path = create_test_database(&temp_dir, 21, 500)?;

    let config = QueryXConfig {
        database_path: db_path,
        threads: 2,
        batch_size: 100,
        preload: true,
        verbose: false,
        quiet: true,
        profile: true,  // Enable profiling
        progress: false,
        memory_limit_mb: None,
        output_path: None,
    };

    let mut processor = QueryXProcessor::new(config)?;

    let test_kmers: Vec<String> = (0..200)
        .map(|i| format!("{:021}", i % 4).replace("0", "A").replace("1", "C").replace("2", "G").replace("3", "T"))
        .collect();

    let results = processor.process_queries(test_kmers)?;

    // Verify performance metrics are populated
    assert!(results.performance.total_time_ms > 0.0);
    assert_eq!(results.performance.queries_processed, 200);
    assert!(results.performance.queries_per_second > 0.0);
    assert!(results.performance.threads_used > 0);

    // Check that recommendations are provided
    assert!(!results.performance.recommendations.is_empty());

    // For batch size 200 with 2 threads, should have reasonable performance
    assert!(results.performance.queries_per_second > 10.0);  // At least 10 queries/sec

    Ok(())
}

/// Test memory limit enforcement
#[test]
fn test_memory_limit_enforcement() -> Result<()> {
    let temp_dir = TempDir::new()?;
    let db_path = create_test_database(&temp_dir, 21, 100)?;

    let config = QueryXConfig {
        database_path: db_path,
        threads: 2,
        batch_size: 10,
        preload: true,
        verbose: false,
        quiet: true,
        profile: false,
        progress: false,
        memory_limit_mb: Some(1),  // Very low memory limit
        output_path: None,
    };

    // Should succeed even with low memory limit (just smaller batches)
    let mut processor = QueryXProcessor::new(config)?;

    let test_kmers: Vec<String> = (0..20)
        .map(|i| format!("{:021}", i % 4).replace("0", "A").replace("1", "C").replace("2", "G").replace("3", "T"))
        .collect();

    let results = processor.process_queries(test_kmers)?;

    assert_eq!(results.query_results.len(), 20);

    Ok(())
}

/// Test large batch query performance
#[test]
fn test_large_batch_performance() -> Result<()> {
    let temp_dir = TempDir::new()?;
    let db_path = create_test_database(&temp_dir, 21, 10000)?;

    let config = QueryXConfig {
        database_path: db_path,
        threads: 0,  // Auto-detect
        batch_size: 1000,
        preload: true,
        verbose: false,
        quiet: true,
        profile: true,
        progress: false,
        memory_limit_mb: None,
        output_path: None,
    };

    let mut processor = QueryXProcessor::new(config)?;

    let test_kmers: Vec<String> = (0..1000)
        .map(|i| format!("{:021}", i % 4).replace("0", "A").replace("1", "C").replace("2", "G").replace("3", "T"))
        .collect();

    let start_time = std::time::Instant::now();
    let results = processor.process_queries(test_kmers)?;
    let elapsed = start_time.elapsed();

    // Should complete reasonably quickly even for 1000 queries
    assert!(elapsed < Duration::from_secs(10));
    assert_eq!(results.query_results.len(), 1000);

    // Should show good parallel performance
    if let Some(speedup) = results.performance.speedup_factor {
        assert!(speedup > 1.0, "Should show some speedup from parallelization");
    }

    Ok(())
}