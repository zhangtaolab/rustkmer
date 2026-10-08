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

    // WR-05 (gap-closure 03-14): compatibility validation is the extracted,
    // integration-testable unit below — see `validate_merge_compatibility`.
    validate_merge_compatibility(&args.input, args.use_prefix_cache, args.verbose, args.quiet)?;

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

    // Configure thread pool from command line argument.
    //
    // The global-pool constructor returns Err on a second call (Pitfall 3:
    // an earlier command in the same process — e.g. `rustkmer count ... &&
    // rustkmer merge ...`, tests, or pyrustkmer users calling both — may
    // already have initialized the global pool). The Err is benign: the
    // existing pool stays in effect. We tolerate it and log under --verbose
    // instead of panicking. The `config.num_threads` assignment stays in
    // both branches so downstream stats reporting reflects the user's intent.
    if args.num_threads > 0 {
        config.num_threads = args.num_threads;
        if args.verbose {
            eprintln!("Using {} threads from command line", args.num_threads);
        }
        if let Err(e) = rayon::ThreadPoolBuilder::new()
            .num_threads(args.num_threads)
            .build_global()
        {
            if args.verbose {
                eprintln!(
                    "Note: global thread pool already initialized ({}); using existing pool",
                    e
                );
            }
        }
    } else if let Ok(num_threads_str) = std::env::var("RAYON_NUM_THREADS") {
        if let Ok(num_threads) = num_threads_str.parse::<usize>() {
            if num_threads > 0 {
                config.num_threads = num_threads;
                if args.verbose {
                    eprintln!("Using {} threads from RAYON_NUM_THREADS", num_threads);
                }
                if let Err(e) = rayon::ThreadPoolBuilder::new()
                    .num_threads(num_threads)
                    .build_global()
                {
                    if args.verbose {
                        eprintln!(
                            "Note: global thread pool already initialized ({}); using existing pool",
                            e
                        );
                    }
                }
            }
        }
    }

    // Check compatibility only if requested
    if args.check_compatibility {
        if !args.quiet {
            eprintln!("Checking database compatibility only...");
        }

        // WR-05 (plan 03-14): headers only. The pre-plan block called
        // `from_file_path` per input — fully materializing every database
        // just to compare header fields. `RKDatabase::new(header)` carries
        // the header (everything `validate_compatibility_verbose` reads:
        // `kmer_size()`, `is_canonical()`, `header().total_kmers`) with an
        // empty entry list, so the enhanced validation and its message text
        // run UNCHANGED on 42 bytes per input.
        let mut databases = Vec::new();
        let mut total_kmers_across_inputs: u64 = 0;
        for db_path in &args.input {
            let header = match RKDatabase::read_header_of(db_path) {
                Ok(header) => header,
                Err(e) => {
                    return Err(anyhow::anyhow!(
                        "Failed to load database '{}': {}",
                        db_path.display(),
                        e
                    ));
                }
            };
            total_kmers_across_inputs += header.total_kmers;
            databases.push(RKDatabase::new(header));
        }

        // Use the enhanced compatibility validation
        match RKDatabase::validate_compatibility_verbose(
            &databases.iter().collect::<Vec<_>>(),
            args.verbose,
        ) {
            Ok(_) => {
                if !args.quiet {
                    eprintln!("✓ All {} databases are compatible!", args.input.len());
                    // Pre-plan this line printed the validation tuple's first
                    // element — which is the reference k-mer SIZE
                    // (`validate_compatibility_verbose` returns
                    // `(kmer_size, canonical)`), so `--check-compatibility`
                    // reported "Total k-mers: 31" on any k=31 set. The real
                    // sum of the headers' record counts is computed above.
                    eprintln!(
                        "Total k-mers across all databases: {}",
                        total_kmers_across_inputs
                    );

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

    // The destination is announced BEFORE the merge starts so the user sees
    // it ahead of a long-running merge. The line's text is user-facing
    // behaviour and stays byte-identical to the pre-03-10 output even though
    // the save is now part of the merge itself rather than a separate step
    // afterwards (plan 03-10: the merge writes straight to the destination).
    if !args.quiet {
        eprintln!("Saving merged database to: {}", args.output.display());
    }

    // Plan 03-10 / G2b: the merge writes its output DIRECTLY to the
    // destination. The pre-plan shape — `merge_databases` into RAM, then
    // `to_file_path` — meant even the "streaming" route materialized the
    // whole merged dataset before writing it (CR-02's substantive half).
    let summary = RKDatabase::merge_databases_to_path(&args.input, &config, &args.output)?;

    // Report results
    let elapsed = start_time.elapsed();
    if !args.quiet {
        eprintln!("Merge completed successfully!");
        eprintln!("  Total input databases: {}", args.input.len());
        eprintln!("  Output database: {}", args.output.display());
        eprintln!("  K-mer size: {}", summary.kmer_size);
        eprintln!("  Total k-mers: {}", summary.total_kmers);
        eprintln!("  Time elapsed: {:.2}s", elapsed.as_secs_f64());

        eprintln!("  Canonical mode: {}", summary.canonical);
        eprintln!("  Sorted: {}", summary.sorted);
    }

    Ok(())
}

/// Validate that all merge inputs are compatible BEFORE the core merge runs —
/// reading each input's 42-byte header only, never its body.
///
/// WR-05 (03-REVIEW.md; closed by this plan): the pre-plan front-end fully
/// materialized every input here — `from_file_path(input[0])` held for the
/// whole function plus two serial loops each loading every remaining input,
/// one at a time — including on `--use-prefix-cache`, the memory-bounded
/// route it exists to protect. The compatibility facts being checked (k-mer
/// size, canonical mode) live in the 42-byte header, so this pass reads
/// exactly that: one [`RKDatabase::read_header_of`] per input, the same
/// header-only door the bounded core's own prologue (plan 03-12) validates
/// through — neither layer performs a body load, so they cannot disagree on
/// one. The core's prologue remains the authoritative cross-route gate; this
/// front-end pass exists for the CLI's recovery-guidance UX only.
///
/// `pub` on the cli module path following the `parse_memory_size` /
/// `resolve_thread_count_from` precedents so an integration test (an external
/// crate) can assert the header-only property directly.
///
/// # Deliberate message deltas vs the pre-plan loops
///
/// The two serial loops collapsed into this single pass had diverging error
/// texts; loop 1 (`!use_prefix_cache`) always ran first, so its texts are the
/// ones preserved verbatim. The two resulting deltas:
///
/// 1. On the `--use-prefix-cache` path the k-mismatch error now carries the
///    third recovery bullet (`rustkmer count --k <size>`) that loop 2's
///    two-bullet message lacked — one more suggestion, same headline.
/// 2. The canonical error uses loop 1's boolean formatting (`true`/`false`)
///    rather than loop 2's `enabled`/`disabled` wording. Loop 2's canonical
///    arm was unreachable on the non-prefix-cache path (loop 1 fires first
///    on the same predicate) and skipped on the prefix-cache path, so no
///    user-visible rejection outcome changes.
pub fn validate_merge_compatibility(
    input_paths: &[PathBuf],
    use_prefix_cache: bool,
    verbose: bool,
    quiet: bool,
) -> Result<()> {
    // Reference header: the only input-shape read before the core merge.
    let first_db_path = &input_paths[0];
    if !quiet {
        eprintln!(
            "Reading reference database header: {}",
            first_db_path.display()
        );
    }
    let ref_header = RKDatabase::read_header_of(first_db_path).map_err(|e| {
        anyhow::anyhow!(
            "Failed to load database '{}': {}",
            first_db_path.display(),
            e
        )
    })?;

    if !use_prefix_cache {
        if verbose {
            eprintln!("Validating database compatibility...");
        }
    } else if verbose {
        // k-mer size is still checked below; only the canonical comparison
        // is the prefix-cache route's to skip (it converts mixed-canonical
        // inputs — its advertised capability).
        eprintln!("Skipping canonical-mode validation (k-mer size still checked; using prefix cache merge)");
    }

    let ref_kmer_size = ref_header.kmer_size as usize;
    let ref_canonical = ref_header.canonical;

    for (_i, db_path) in input_paths.iter().enumerate().skip(1) {
        let header = RKDatabase::read_header_of(db_path).map_err(|e| {
            anyhow::anyhow!("Failed to load database '{}': {}", db_path.display(), e)
        })?;

        if header.kmer_size as usize != ref_kmer_size {
            let mut error_msg = format!(
                "Database '{}' has k-mer size {}, expected {}",
                db_path.display(),
                header.kmer_size,
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
            error_msg
                .push_str("\n  • Use 'rustkmer count --k <size>' to create compatible databases");

            return Err(anyhow::anyhow!("{}", error_msg));
        }

        // Only check canonical mode if not using prefix cache.
        if !use_prefix_cache && header.canonical != ref_canonical {
            let mut error_msg = format!(
                "Database '{}' has canonical mode {}, expected {}",
                db_path.display(),
                header.canonical,
                ref_canonical
            );

            // Add recovery suggestions
            error_msg.push_str("\n\nRecovery suggestions:");
            error_msg.push_str(&format!(
                "\n  • Create a new database with canonical mode {}",
                ref_canonical
            ));
            error_msg.push_str(
                "\n  • Use 'rustkmer count --canonical' or 'rustkmer count --no-canonical' as needed",
            );
            error_msg
                .push_str("\n  • Verify all databases use the same canonical mode before merging");

            return Err(anyhow::anyhow!("{}", error_msg));
        }

        if verbose {
            eprintln!("  ✓ Database '{}' is compatible", db_path.display());
        }
    }

    Ok(())
}

/// Parse memory size string like "32GB", "1TB", "512MB" into bytes
///
/// Public so the PyO3 binding can reuse it: MERGE-04 requires Python's
/// `max_memory=` kwarg and the CLI's `--max-memory` flag to accept exactly the
/// same grammar and the same bounds. A second copy of this parser in the
/// binding would be free to drift, and the drift would be invisible until a
/// user's budget silently parsed differently on one surface than the other.
pub fn parse_memory_size(size_str: &str) -> Result<usize, String> {
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

    // WR-05: every unit multiplier is `checked_mul`. The pre-fix chains
    // (`number * 1024`, `number * 1024 * 1024`, ...) panicked on arithmetic
    // overflow in a debug build BEFORE the bound checks below could run, and
    // the PyO3 binding calls this exact function for `max_memory=`, so a
    // Python caller could abort the host interpreter with an over-large
    // budget string (e.g. "18446744073709551615KB"). Any overflow is mapped
    // onto the SAME `Err` the existing 1TB ceiling returns, so the only
    // observable change is "ValueError instead of a crash".
    let bytes = match unit {
        "B" => number,
        "KB" => number
            .checked_mul(1024)
            .ok_or_else(|| "Memory size too large (maximum 1TB)".to_string())?,
        "MB" => number
            .checked_mul(1024)
            .and_then(|bytes| bytes.checked_mul(1024))
            .ok_or_else(|| "Memory size too large (maximum 1TB)".to_string())?,
        "GB" => number
            .checked_mul(1024)
            .and_then(|bytes| bytes.checked_mul(1024))
            .and_then(|bytes| bytes.checked_mul(1024))
            .ok_or_else(|| "Memory size too large (maximum 1TB)".to_string())?,
        "TB" => number
            .checked_mul(1024)
            .and_then(|bytes| bytes.checked_mul(1024))
            .and_then(|bytes| bytes.checked_mul(1024))
            .and_then(|bytes| bytes.checked_mul(1024))
            .ok_or_else(|| "Memory size too large (maximum 1TB)".to_string())?,
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

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    /// WR-05: `parse_memory_size` must never panic on an overflowing size —
    /// it must return the ordinary `too large` `Err` instead.
    ///
    /// The four cases below are derived from the REAL overflow boundary of
    /// each unit multiplier (`2^64 / 1024^k`, the smallest numeric part whose
    /// k-fold `* 1024` product reaches `usize::MAX + 1`), so each one
    /// genuinely reaches the multiplication it targets rather than failing
    /// earlier in the parser:
    ///
    /// | unit | multiply that overflows | numeric part        | why                    |
    /// |------|--------------------------|---------------------|------------------------|
    /// | KB   | 1st (`* 1024`)           | 18446744073709551615| equals `usize::MAX` exactly |
    /// | MB   | 2nd                      | 17592186044416      | 1st fits, 2nd reaches 2^64 |
    /// | GB   | 3rd                      | 17179869184         | first two fit, 3rd reaches 2^64 |
    /// | TB   | 4th                      | 16777216            | first three fit, 4th reaches 2^64 |
    ///
    /// All four were RED against the pre-fix source (each panicked with
    /// "attempt to multiply with overflow" in a debug build, aborting the
    /// test before any assertion ran) and pass with `checked_mul`. The
    /// `pyo3` binding calls this parser for `max_memory=`, so a Python caller
    /// now gets a `ValueError` where it previously could crash the host
    /// interpreter.
    #[test]
    fn parse_memory_size_rejects_an_overflowing_size_without_panicking() {
        for size in [
            "18446744073709551615KB",
            "17592186044416MB",
            "17179869184GB",
            "16777216TB",
        ] {
            match parse_memory_size(size) {
                Ok(bytes) => panic!(
                    "an overflowing size must be rejected, but {} parsed as {} bytes",
                    size, bytes
                ),
                Err(e) => assert!(
                    e.contains("too large"),
                    "{} must be rejected with the ordinary 'too large' error (WR-05: same \
                     observable behaviour as the 1TB ceiling, no panic); got: {}",
                    size,
                    e
                ),
            }
        }

        // The DIFFERENT case, recorded so the file documents the boundary of
        // the fix: a numeric part ABOVE `usize::MAX` (20 digits, one more
        // than `usize::MAX`) never reaches the multiplication — it fails
        // earlier, at `.parse::<usize>()`, and returns the parser's own
        // `Invalid number` message. That path was always safe (no panic) and
        // is unchanged by this fix.
        let oversized = parse_memory_size("99999999999999999999TB")
            .expect_err("a numeric part above usize::MAX must fail at the parser");
        assert!(
            oversized.contains("Invalid number"),
            "an over-usize numeric part is rejected by the PARSER with a different, \
             always-safe message; got: {}",
            oversized
        );

        // The fix did not narrow the accepted range: the smallest and a
        // mid-range size still parse exactly as before.
        assert_eq!(parse_memory_size("1KB").expect("1KB is the floor"), 1024);
        assert_eq!(
            parse_memory_size("512MB").expect("512MB is well within range"),
            512 * 1024 * 1024
        );
    }

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

        // Verify output. WR-05 (plan 03-14): verified header-only here so
        // this file keeps its zero-materializing-loader discipline; the deep
        // merged-COUNTS assertions live in
        // tests/merge_frontend_validation_tests.rs's end-to-end smoke.
        assert!(output_path.exists());
        let header = RKDatabase::read_header_of(&output_path).unwrap();
        assert_eq!(header.kmer_size, 31);
        assert_eq!(
            header.total_kmers, 3,
            "2 unique k-mers in db1 + 1 additional unique k-mer in db2"
        );
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

        // Verify output. WR-05 (plan 03-14): the merged COUNTS are asserted
        // on the in-memory result; the written file is round-trip checked
        // via its header only (no materializing load in this file).
        assert!(output_path.exists());
        let header = RKDatabase::read_header_of(&output_path).unwrap();
        assert_eq!(header.total_kmers, 3);

        // Check that k-mers were properly merged
        let all_kmers = merged_db.all_kmers().unwrap();
        let kmer_map: std::collections::HashMap<_, _> = all_kmers.into_iter().collect();

        assert_eq!(kmer_map.get(&0x1234), Some(&15)); // 10 + 5
        assert_eq!(kmer_map.get(&0x5678), Some(&20));
        assert_eq!(kmer_map.get(&0x9ABC), Some(&15));
    }
}
