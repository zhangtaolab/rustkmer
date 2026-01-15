//! Merge CLI command
//!
//! This module implements the command-line interface for merging multiple RKDB databases.
//!
//! # Usage
//!
//! ```bash
//! rustkmer merge -i <db1.rkdb> <db2.rkdb> ... -o <output.rkdb>
//! ```
//!
//! # Description
//!
//! The merge command combines multiple RKDB (Rust k-mer database) files into a single
//! database. When k-mers appear in multiple input databases, their counts are summed
//! in the output. Unique k-mers from each database are preserved in the result.
//!
//! # Examples
//!
//! ## Basic merge
//! ```bash
//! rustkmer merge -i sample1.rkdb sample2.rkdb -o merged.rkdb
//! ```
//!
//! ## Merge with verbose output
//! ```bash
//! rustkmer merge -i *.rkdb -o all_merged.rkdb --verbose
//! ```
//!
//!
//! # Compatibility Requirements
//!
//! All input databases must have:
//! - The same k-mer size
//! - The same canonical mode setting
//! - Compatible format versions
//!
//! Use `rustkmer stats <database>` to check database parameters before merging.
//!
//! # Performance Considerations
//!
//! - Memory usage is proportional to the number of unique k-mers in the output
//! - Parallel processing is automatically used when beneficial
//!
//! # Error Recovery
//!
//! If merge fails with compatibility errors:
//! 1. Check that all databases have the same k-mer size
//! 2. Verify canonical mode consistency across all inputs
//! 3. Use enhanced error messages for specific guidance

use crate::database::format::RKDatabase;
use crate::database::MergeConfig;
use anyhow::Result;
use clap::Args;
use std::path::PathBuf;
use std::time::Instant;

/// Arguments for merge command
#[derive(Args, Debug)]
pub struct MergeArgs {
    /// Input database files to merge
    #[arg(
        short = 'i',
        long,
        num_args = 2..,
        help = "Input database files to merge (at least 2 required)"
    )]
    pub input: Vec<PathBuf>,

    /// Output database file
    #[arg(short = 'o', long, help = "Output merged database file")]
    pub output: PathBuf,

    /// Temporary directory for merge operations
    #[arg(
        long,
        help = "Temporary directory for merge operations (default: system temp)"
    )]
    pub temp_dir: Option<PathBuf>,

    /// Enable verbose output
    #[arg(short = 'v', long, help = "Enable verbose output")]
    pub verbose: bool,

    /// Suppress non-error output
    #[arg(short = 'q', long, help = "Suppress non-error output")]
    pub quiet: bool,

    /// Keep intermediate files (for debugging)
    #[arg(long, help = "Keep intermediate files (for debugging)")]
    pub keep_intermediate: bool,

    /// Check compatibility of databases without merging
    #[arg(
        long,
        help = "Check compatibility of databases without performing the merge"
    )]
    pub check_compatibility: bool,

    /// Maximum memory usage for merge operations (e.g., "32GB", "1TB")
    #[arg(
        long,
        help = "Maximum memory usage for merge operations (e.g., '32GB', '1TB'). Defaults to 50% of system memory."
    )]
    pub max_memory: Option<String>,

    /// Use prefix cache merge (memory-efficient with error isolation)
    #[arg(
        long,
        help = "Use prefix cache merge strategy for memory-efficient processing with error isolation"
    )]
    pub use_prefix_cache: bool,

    /// Batch size for prefix cache merge (number of k-mers per buffer flush)
    #[arg(
        long,
        default_value = "50000",
        help = "Batch size for prefix cache merge (k-mers per buffer flush). Lower values use less memory but are slower. (default: 50000)"
    )]
    pub batch_size: usize,

    /// Number of threads for parallel processing (0 = all cores)
    #[arg(
        long,
        default_value = "0",
        help = "Number of threads for parallel processing (0 = use all cores). Can also be set via RAYON_NUM_THREADS environment variable."
    )]
    pub num_threads: usize,

    /// Merge strategy for prefix cache mode
    #[arg(
        long,
        value_parser = ["auto", "memory", "streaming"],
        default_value = "auto",
        help = "Merge strategy for prefix cache mode: auto (use memory if <100MB), memory (force in-memory), streaming (always stream). (default: auto)"
    )]
    pub merge_mode: String,
}

/// Execute merge command
pub fn execute_merge(args: &MergeArgs) -> Result<()> {
    let start_time = Instant::now();

    // Validate input
    if args.input.len() < 2 {
        return Err(anyhow::anyhow!(
            "At least 2 input databases are required for merging"
        ));
    }

    if !args.quiet {
        eprintln!("Merging {} databases...", args.input.len());
        if args.verbose {
            for (i, db_path) in args.input.iter().enumerate() {
                eprintln!("  {}: {}", i + 1, db_path.display());
            }
        }
    }

    // Load first database to get reference metadata
    let first_db_path = &args.input[0];
    if !args.quiet {
        eprintln!("Loading reference database: {}", first_db_path.display());
    }
    let reference_db = RKDatabase::from_file_path(first_db_path)?;

    // Validate all databases have compatible settings (skip if using prefix cache)
    if !args.use_prefix_cache {
        if args.verbose {
            eprintln!("Validating database compatibility...");
        }

        let ref_kmer_size = reference_db.kmer_size();
        let ref_canonical = reference_db.is_canonical();

        for (_i, db_path) in args.input.iter().enumerate().skip(1) {
            let db = match RKDatabase::from_file_path(db_path) {
                Ok(db) => db,
                Err(e) => {
                    return Err(anyhow::anyhow!(
                        "Failed to load database '{}': {}",
                        db_path.display(),
                        e
                    ));
                }
            };

            if db.kmer_size() != ref_kmer_size {
                let mut error_msg = format!(
                    "Database '{}' has k-mer size {}, expected {}",
                    db_path.display(),
                    db.kmer_size(),
                    ref_kmer_size
                );

                // Add recovery suggestions
                error_msg.push_str("\n\nRecovery suggestions:");
                error_msg.push_str(&format!(
                    "\n  • Create a new database with k-mer size {}",
                    ref_kmer_size
                ));
                error_msg.push_str(
                    "\n  • Use 'rustkmer stats' to verify database parameters before merging",
                );
                error_msg.push_str(
                    "\n  • Use 'rustkmer count --k <size>' to create compatible databases",
                );

                return Err(anyhow::anyhow!("{}", error_msg));
            }

            if db.is_canonical() != ref_canonical {
                let mut error_msg = format!(
                    "Database '{}' has canonical mode {}, expected {}",
                    db_path.display(),
                    db.is_canonical(),
                    ref_canonical
                );

                // Add recovery suggestions
                error_msg.push_str("\n\nRecovery suggestions:");
                error_msg.push_str(&format!(
                    "\n  • Create a new database with canonical mode {}",
                    ref_canonical
                ));
                error_msg.push_str("\n  • Use 'rustkmer count --canonical' or 'rustkmer count --no-canonical' as needed");
                error_msg.push_str(
                    "\n  • Verify all databases use the same canonical mode before merging",
                );

                return Err(anyhow::anyhow!("{}", error_msg));
            }
        }
    } else if args.verbose {
        eprintln!("Skipping compatibility validation (using prefix cache merge)");
    }

    let ref_kmer_size = reference_db.kmer_size();
    let ref_canonical = reference_db.is_canonical();

    for (_i, db_path) in args.input.iter().enumerate().skip(1) {
        let db = match RKDatabase::from_file_path(db_path) {
            Ok(db) => db,
            Err(e) => {
                return Err(anyhow::anyhow!(
                    "Failed to load database '{}': {}",
                    db_path.display(),
                    e
                ));
            }
        };

        if db.kmer_size() != ref_kmer_size {
            let mut error_msg = format!(
                "Database '{}' has k-mer size {}, expected {}",
                db_path.display(),
                db.kmer_size(),
                ref_kmer_size
            );

            // Add recovery suggestions
            error_msg.push_str("\n\nRecovery suggestions:");
            error_msg.push_str(&format!(
                "\n  • Create a new database with k-mer size {}",
                ref_kmer_size
            ));
            error_msg.push_str(
                "\n  • Use 'rustkmer stats' to verify database parameters before merging",
            );

            return Err(anyhow::anyhow!(error_msg));
        }

        // Only check canonical mode if not using prefix cache
        if !args.use_prefix_cache && db.is_canonical() != ref_canonical {
            let mut error_msg = format!(
                "Database '{}' has canonical mode {}, expected {}",
                db_path.display(),
                db.is_canonical(),
                ref_canonical
            );

            // Add recovery suggestions
            error_msg.push_str("\n\nRecovery suggestions:");
            error_msg.push_str(&format!(
                "\n  • Create a new database with canonical mode {}",
                if ref_canonical { "enabled" } else { "disabled" }
            ));
            error_msg.push_str("\n  • Use 'rustkmer count --canonical' or 'rustkmer count --no-canonical' as needed");
            error_msg
                .push_str("\n  • Verify all databases use the same canonical mode before merging");

            return Err(anyhow::anyhow!("{}", error_msg));
        }

        if args.verbose {
            eprintln!("  ✓ Database '{}' is compatible", db_path.display());
        }
    }

    // Configure merge options
    let mut config = MergeConfig::default();
    if let Some(temp_dir) = &args.temp_dir {
        config.temp_dir = temp_dir.clone();
    }

    // Parse and set max memory if provided
    if let Some(max_memory_str) = &args.max_memory {
        match parse_memory_size(max_memory_str) {
            Ok(memory_bytes) => {
                config.max_memory_usage = memory_bytes;
                if args.verbose {
                    eprintln!(
                        "Using custom memory limit: {} bytes ({:.2} GB)",
                        memory_bytes,
                        memory_bytes as f64 / 1_000_000_000.0
                    );
                }
            }
            Err(e) => {
                return Err(anyhow::anyhow!(
                    "Invalid memory limit '{}': {}",
                    max_memory_str,
                    e
                ));
            }
        }
    } else if args.verbose {
        eprintln!(
            "Using default memory limit: {:.2} GB",
            config.max_memory_usage as f64 / 1_000_000_000.0
        );
    }

    config.verbose = args.verbose;
    config.use_prefix_cache = args.use_prefix_cache;
    config.merge_mode = args.merge_mode.clone();
    config.keep_intermediate = args.keep_intermediate;

    // Configure thread pool from command line argument
    if args.num_threads > 0 {
        config.num_threads = args.num_threads;
        if args.verbose {
            eprintln!("Using {} threads from command line", args.num_threads);
        }
        rayon::ThreadPoolBuilder::new()
            .num_threads(args.num_threads)
            .build_global()
            .expect("Failed to set rayon thread pool");
    } else if let Ok(num_threads_str) = std::env::var("RAYON_NUM_THREADS") {
        if let Ok(num_threads) = num_threads_str.parse::<usize>() {
            if num_threads > 0 {
                config.num_threads = num_threads;
                if args.verbose {
                    eprintln!("Using {} threads from RAYON_NUM_THREADS", num_threads);
                }
                rayon::ThreadPoolBuilder::new()
                    .num_threads(num_threads)
                    .build_global()
                    .expect("Failed to set rayon thread pool");
            }
        }
    }

    // Check compatibility only if requested
    if args.check_compatibility {
        if !args.quiet {
            eprintln!("Checking database compatibility only...");
        }

        // Load all databases for compatibility checking
        let mut databases = Vec::new();
        for db_path in &args.input {
            let db = match RKDatabase::from_file_path(db_path) {
                Ok(db) => db,
                Err(e) => {
                    return Err(anyhow::anyhow!(
                        "Failed to load database '{}': {}",
                        db_path.display(),
                        e
                    ));
                }
            };
            databases.push(db);
        }

        // Use the enhanced compatibility validation
        match RKDatabase::validate_compatibility_verbose(
            &databases.iter().collect::<Vec<_>>(),
            args.verbose,
        ) {
            Ok((total_kmers, _)) => {
                if !args.quiet {
                    eprintln!("✓ All {} databases are compatible!", args.input.len());
                    eprintln!("Total k-mers across all databases: {}", total_kmers);

                    // Show individual database stats
                    if args.verbose {
                        for (i, db) in databases.iter().enumerate() {
                            let info = db.header();
                            eprintln!(
                                "  Database {}: k={}, canonical={}, sorted={}, kmers={}",
                                i + 1,
                                info.kmer_size,
                                info.canonical,
                                info.sorted,
                                db.total_kmers()
                            );
                        }
                    }
                }
                return Ok(());
            }
            Err(e) => {
                return Err(anyhow::anyhow!("Database compatibility check failed: {}\n\nUse --verbose for more details about the incompatibilities.", e));
            }
        }
    }

    // Perform merge
    if args.verbose {
        eprintln!("Starting merge operation...");
    }

    let merged_db = RKDatabase::merge_databases(&args.input, &config)?;

    // Save merged database
    if !args.quiet {
        eprintln!("Saving merged database to: {}", args.output.display());
    }

    merged_db.to_file_path(&args.output)?;

    // Report results
    let elapsed = start_time.elapsed();
    if !args.quiet {
        eprintln!("Merge completed successfully!");
        eprintln!("  Total input databases: {}", args.input.len());
        eprintln!("  Output database: {}", args.output.display());
        eprintln!("  K-mer size: {}", merged_db.kmer_size());
        eprintln!("  Total k-mers: {}", merged_db.total_kmers());
        eprintln!("  Time elapsed: {:.2}s", elapsed.as_secs_f64());

        let info = merged_db.header();
        eprintln!("  Canonical mode: {}", info.canonical);
        eprintln!("  Sorted: {}", info.sorted);
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_merge_validation() {
        let temp_dir = tempdir().unwrap();
        let db1_path = temp_dir.path().join("db1.rkdb");
        let db2_path = temp_dir.path().join("db2.rkdb");
        let output_path = temp_dir.path().join("merged.rkdb");

        // Create test databases
        let db1 =
            RKDatabase::from_kmer_pairs(vec![(0x1234, 10), (0x5678, 20)], 31, false, true).unwrap();
        db1.to_file_path(&db1_path).unwrap();

        let db2 =
            RKDatabase::from_kmer_pairs(vec![(0x1234, 5), (0x9ABC, 15)], 31, false, true).unwrap();
        db2.to_file_path(&db2_path).unwrap();

        let args = MergeArgs {
            input: vec![db1_path, db2_path],
            output: output_path.clone(),
            temp_dir: None,
            verbose: true,
            quiet: false,
            keep_intermediate: false,
            check_compatibility: false,
            max_memory: None,
            use_prefix_cache: false,
            batch_size: 50000,
            num_threads: 0,
            merge_mode: "auto".to_string(),
        };

        // Execute merge
        execute_merge(&args).unwrap();

        // Verify output
        assert!(output_path.exists());
        let merged_db = RKDatabase::from_file_path(&output_path).unwrap();

        // Check that k-mers were properly merged
        let all_kmers = merged_db.all_kmers().unwrap();
        let kmer_map: std::collections::HashMap<_, _> = all_kmers.into_iter().collect();

        assert_eq!(kmer_map.get(&0x1234), Some(&15)); // 10 + 5
        assert_eq!(kmer_map.get(&0x5678), Some(&20));
        assert_eq!(kmer_map.get(&0x9ABC), Some(&15));
    }

    #[test]
    fn test_merge_with_config() {
        let temp_dir = tempdir().unwrap();
        let db1_path = temp_dir.path().join("db1.rkdb");
        let db2_path = temp_dir.path().join("db2.rkdb");
        let output_path = temp_dir.path().join("merged.rkdb");

        // Create test databases
        let db1 =
            RKDatabase::from_kmer_pairs(vec![(0x1234, 10), (0x5678, 20)], 31, false, true).unwrap();
        db1.to_file_path(&db1_path).unwrap();

        let db2 =
            RKDatabase::from_kmer_pairs(vec![(0x1234, 5), (0x9ABC, 15)], 31, false, true).unwrap();
        db2.to_file_path(&db2_path).unwrap();

        // Test merge with custom config
        let config = MergeConfig {
            max_memory_usage: 1024 * 1024, // 1MB
            chunk_size: 1000,
            temp_dir: temp_dir.path().to_path_buf(),
            use_streaming: false,
            use_prefix_cache: false,
            num_threads: 0,
            merge_mode: "auto".to_string(),
            keep_intermediate: false,
            verbose: false,
        };

        let merged_db = RKDatabase::merge_databases(&[db1_path, db2_path], &config).unwrap();
        merged_db.to_file_path(&output_path).unwrap();

        // Verify output
        assert!(output_path.exists());
        let loaded_db = RKDatabase::from_file_path(&output_path).unwrap();

        // Check that k-mers were properly merged
        let all_kmers = loaded_db.all_kmers().unwrap();
        let kmer_map: std::collections::HashMap<_, _> = all_kmers.into_iter().collect();

        assert_eq!(kmer_map.get(&0x1234), Some(&15)); // 10 + 5
        assert_eq!(kmer_map.get(&0x5678), Some(&20));
        assert_eq!(kmer_map.get(&0x9ABC), Some(&15));
    }
}

/// Parse memory size string like "32GB", "1TB", "512MB" into bytes
fn parse_memory_size(size_str: &str) -> Result<usize, String> {
    let size_str = size_str.trim().to_uppercase();

    // Parse number and unit - handle multi-character units properly
    let (number_str, unit) = if size_str.ends_with("B") {
        if size_str.ends_with("KB") {
            (&size_str[..size_str.len() - 2], "KB")
        } else if size_str.ends_with("MB") {
            (&size_str[..size_str.len() - 2], "MB")
        } else if size_str.ends_with("GB") {
            (&size_str[..size_str.len() - 2], "GB")
        } else if size_str.ends_with("TB") {
            (&size_str[..size_str.len() - 2], "TB")
        } else if size_str.len() > 1 {
            (&size_str[..size_str.len() - 1], "B")
        } else {
            return Err(format!("Invalid memory size format: {}", size_str));
        }
    } else {
        (size_str.as_str(), "")
    };

    let number: usize = number_str
        .parse()
        .map_err(|_| format!("Invalid number: {}", number_str))?;

    let bytes = match unit {
        "B" => number,
        "KB" => number * 1024,
        "MB" => number * 1024 * 1024,
        "GB" => number * 1024 * 1024 * 1024,
        "TB" => number * 1024 * 1024 * 1024 * 1024,
        "" => number, // Default to bytes
        _ => return Err(format!("Unknown unit: {}", unit)),
    };

    // Validate reasonable bounds
    if bytes < 1024 {
        return Err("Memory size too small (minimum 1KB)".to_string());
    }

    if bytes > 1024 * 1024 * 1024 * 1024 {
        // 1TB
        return Err("Memory size too large (maximum 1TB)".to_string());
    }

    Ok(bytes)
}
