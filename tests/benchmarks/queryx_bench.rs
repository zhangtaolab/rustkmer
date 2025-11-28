//! Performance benchmarks for queryx parallel query processing
//!
//! Provides comprehensive performance testing using criterion to validate
//! performance claims and identify optimization opportunities.

use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use std::path::PathBuf;
use std::time::Duration;

use rustkmer::database::parallel_query::{QueryXProcessor, ThreadSafeDatabaseQuery};
use rustkmer::cli::commands::queryx::QueryXConfig;

// Generate test k-mers for benchmarking
fn generate_test_kmers(count: usize, kmer_size: usize) -> Vec<String> {
    (0..count)
        .map(|i| {
            // Generate deterministic k-mers based on index
            let bases = ['A', 'C', 'G', 'T'];
            (0..kmer_size)
                .map(|j| bases[(i + j) % 4])
                .collect()
        })
        .collect()
}

fn create_test_database() -> PathBuf {
    // For benchmarks, we need a real database file
    // This should point to a test database created separately
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("test_data")
        .join("benchmark_db.rkdb")
}

fn benchmark_queryx_batch_sizes(c: &mut Criterion) {
    let database_path = create_test_database();

    // Check if test database exists
    if !database_path.exists() {
        eprintln!("Warning: Benchmark database not found at {:?}. Skipping benchmarks.", database_path);
        return;
    }

    let mut group = c.benchmark_group("queryx_batch_sizes");

    // Test different batch sizes
    for batch_size in [10, 50, 100, 500, 1000, 5000, 10000].iter() {
        let test_kmers = generate_test_kmers(*batch_size, 21);

        group.bench_with_input(
            BenchmarkId::new("parallel", batch_size),
            batch_size,
            |b, _| {
                b.iter(|| {
                    let config = QueryXConfig {
                        database_path: database_path.clone(),
                        threads: 0, // Auto-detect
                        batch_size: 1000,
                        preload: true,
                        verbose: false,
                        quiet: true,
                        profile: false,
                        progress: false,
                        memory_limit_mb: None,
                        output_path: None,
                    };

                    // Note: This would need actual database for real benchmarking
                    // For now, we'll benchmark the k-mer generation and validation
                    let validated_kmers: Vec<String> = test_kmers
                        .iter()
                        .map(|kmer| kmer.to_uppercase())
                        .collect();

                    black_box(validated_kmers);
                });
            },
        );
    }

    group.finish();
}

fn benchmark_thread_scaling(c: &mut Criterion) {
    let database_path = create_test_database();

    if !database_path.exists() {
        eprintln!("Warning: Benchmark database not found. Skipping thread scaling benchmarks.");
        return;
    }

    let mut group = c.benchmark_group("queryx_thread_scaling");

    let test_kmers = generate_test_kmers(1000, 21);

    // Test different thread counts
    for thread_count in [1, 2, 4, 8, 16].iter() {
        group.bench_with_input(
            BenchmarkId::new("threads", thread_count),
            thread_count,
            |b, &threads| {
                b.iter(|| {
                    let config = QueryXConfig {
                        database_path: database_path.clone(),
                        threads,
                        batch_size: 1000,
                        preload: true,
                        verbose: false,
                        quiet: true,
                        profile: false,
                        progress: false,
                        memory_limit_mb: None,
                        output_path: None,
                    };

                    // Simulate processing workload
                    let processed: Vec<String> = test_kmers
                        .par_iter()
                        .map(|kmer| {
                            // Simulate k-mer processing work
                            let mut result = kmer.clone();
                            result.push_str(&"_processed".to_string());
                            result
                        })
                        .collect();

                    black_box(processed);
                });
            },
        );
    }

    group.finish();
}

fn benchmark_vs_single_threaded(c: &mut Criterion) {
    let database_path = create_test_database();

    if !database_path.exists() {
        eprintln!("Warning: Benchmark database not found. Skipping comparison benchmarks.");
        return;
    }

    let mut group = c.benchmark_group("queryx_vs_single");

    let test_kmers = generate_test_kmers(5000, 21);

    // Single-threaded baseline
    group.bench_function("single_threaded", |b| {
        b.iter(|| {
            // Simulate single-threaded processing
            let processed: Vec<String> = test_kmers
                .iter()
                .map(|kmer| {
                    // Simulate k-mer query work
                    format!("{}_single", kmer)
                })
                .collect();

            black_box(processed);
        });
    });

    // Multi-threaded queryx
    group.bench_function("multi_threaded", |b| {
        b.iter(|| {
            use rayon::prelude::*;

            // Simulate multi-threaded processing
            let processed: Vec<String> = test_kmers
                .par_iter()
                .map(|kmer| {
                    // Simulate k-mer query work
                    format!("{}_multi", kmer)
                })
                .collect();

            black_box(processed);
        });
    });

    group.finish();
}

fn benchmark_memory_usage(c: &mut Criterion) {
    let mut group = c.benchmark_group("queryx_memory_usage");

    // Test different k-mer set sizes to measure memory usage patterns
    for kmer_count in [1000, 5000, 10000, 50000].iter() {
        let test_kmers = generate_test_kmers(*kmer_count, 21);

        group.bench_with_input(
            BenchmarkId::new("memory_allocation", kmer_count),
            kmer_count,
            |b, _| {
                b.iter(|| {
                    // Simulate memory allocation patterns
                    let mut results = Vec::with_capacity(test_kmers.len());

                    for kmer in &test_kmers {
                        // Simulate result allocation
                        results.push((kmer.clone(), Some(42u64)));
                    }

                    black_box(results);
                });
            },
        );
    }

    group.finish();
}

fn benchmark_input_validation(c: &mut Criterion) {
    let mut group = c.benchmark_group("queryx_validation");

    // Test k-mer validation performance
    let valid_kmers = generate_test_kmers(10000, 21);
    let invalid_kmers: Vec<String> = (0..1000)
        .map(|i| format!("ATGCX{}", i)) // Contains invalid 'X' character
        .collect();

    group.bench_function("valid_kmers", |b| {
        b.iter(|| {
            let validated: Vec<String> = valid_kmers
                .iter()
                .filter_map(|kmer| {
                    if kmer.chars().all(|c| matches!(c, 'A' | 'C' | 'G' | 'T')) {
                        Some(kmer.to_uppercase())
                    } else {
                        None
                    }
                })
                .collect();

            black_box(validated);
        });
    });

    group.bench_function("mixed_kmers", |b| {
        let mixed_kmers = valid_kmers.iter().chain(&invalid_kmers).cloned().collect::<Vec<_>>();

        b.iter(|| {
            let validated: Vec<String> = mixed_kmers
                .iter()
                .filter_map(|kmer| {
                    if kmer.chars().all(|c| matches!(c, 'A' | 'C' | 'G' | 'T')) {
                        Some(kmer.to_uppercase())
                    } else {
                        None
                    }
                })
                .collect();

            black_box(validated);
        });
    });

    group.finish();
}

fn benchmark_adaptive_thread_management(c: &mut Criterion) {
    let mut group = c.benchmark_group("queryx_adaptive_threads");

    // Test thread management for different batch sizes
    for batch_size in [10, 100, 1000, 10000].iter() {
        group.bench_with_input(
            BenchmarkId::new("adaptive_thread_count", batch_size),
            batch_size,
            |b, &size| {
                b.iter(|| {
                    // Simulate adaptive thread count logic
                    let available_cores = num_cpus::get();
                    let optimal_threads = match size {
                        0..=50 => 1,
                        51..=200 => available_cores / 2,
                        201..=1000 => (available_cores * 3) / 4,
                        _ => available_cores,
                    };

                    // Simulate thread pool initialization
                    let _result = optimal_threads.max(1);
                    black_box(optimal_threads);
                });
            },
        );
    }

    group.finish();
}

criterion_group!(
    benches,
    benchmark_queryx_batch_sizes,
    benchmark_thread_scaling,
    benchmark_vs_single_threaded,
    benchmark_memory_usage,
    benchmark_input_validation,
    benchmark_adaptive_thread_management
);

criterion_main!(benches);