//! Merge CLI command
//!
//! This module implements the command-line interface for merging multiple RKDB databases.

use crate::database::format::RKDatabase;
use crate::error::ProcessingResult;
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
    #[arg(
        short = 'o',
        long,
        help = "Output merged database file"
    )]
    pub output: PathBuf,

    /// Temporary directory for merge operations
    #[arg(
        long,
        help = "Temporary directory for merge operations (default: system temp)"
    )]
    pub temp_dir: Option<PathBuf>,

    /// Number of threads for merging
    #[arg(
        short = 't',
        long,
        default_value = "0",
        help = "Number of threads for merging (0 = auto-detect)"
    )]
    pub threads: usize,

    /// Enable verbose output
    #[arg(
        short = 'v',
        long,
        help = "Enable verbose output"
    )]
    pub verbose: bool,

    /// Suppress non-error output
    #[arg(
        short = 'q',
        long,
        help = "Suppress non-error output"
    )]
    pub quiet: bool,

    /// Force merge even if databases have incompatible settings
    #[arg(
        long,
        help = "Force merge even if databases have incompatible settings (not recommended)"
    )]
    pub force: bool,

    /// Keep intermediate files (for debugging)
    #[arg(
        long,
        help = "Keep intermediate files (for debugging)"
    )]
    pub keep_intermediate: bool,
}

/// Execute merge command
pub fn execute_merge(args: &MergeArgs) -> Result<()> {
    let start_time = Instant::now();

    // Validate input
    if args.input.len() < 2 {
        return Err(anyhow::anyhow!("At least 2 input databases are required for merging"));
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

    // Validate all databases have compatible settings
    if !args.force {
        if args.verbose {
            eprintln!("Validating database compatibility...");
        }

        let ref_kmer_size = reference_db.kmer_size();
        let ref_canonical = reference_db.is_canonical();

        for (i, db_path) in args.input.iter().enumerate().skip(1) {
            let db = match RKDatabase::from_file_path(db_path) {
                Ok(db) => db,
                Err(e) => {
                    return Err(anyhow::anyhow!("Failed to load database '{}': {}",
                                           db_path.display(), e));
                }
            };

            if db.kmer_size() != ref_kmer_size {
                return Err(anyhow::anyhow!(
                    "Database '{}' has k-mer size {}, expected {}",
                    db_path.display(),
                    db.kmer_size(),
                    ref_kmer_size
                ));
            }

            if db.is_canonical() != ref_canonical {
                return Err(anyhow::anyhow!(
                    "Database '{}' has canonical mode {}, expected {}",
                    db_path.display(),
                    db.is_canonical(),
                    ref_canonical
                ));
            }

            if args.verbose {
                eprintln!("  ✓ Database '{}' is compatible", db_path.display());
            }
        }
    }

    // Perform merge
    if args.verbose {
        eprintln!("Starting merge operation...");
    }

    let merged_db = merge_databases(&args.input, args)?;

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

/// Merge multiple RKDB databases
///
/// This function handles the actual merging logic for RKDB databases,
/// supporting both u64 and u128 encoding formats.
fn merge_databases(
    input_paths: &[PathBuf],
    args: &MergeArgs,
) -> Result<RKDatabase> {
    use std::collections::HashMap;

    // Load all databases and merge their k-mer counts
    let mut all_kmers: HashMap<u128, u32> = HashMap::new();
    let mut total_kmers = 0u64;
    let mut kmer_size = None;
    let mut canonical = None;
    let mut sorted = true;

    for (db_index, db_path) in input_paths.iter().enumerate() {
        if args.verbose {
            eprintln!("Loading database {}/{}: {}",
                     db_index + 1, input_paths.len(), db_path.display());
        }

        let db = RKDatabase::from_file_path(db_path)?;

        // Set metadata from first database
        if db_index == 0 {
            kmer_size = Some(db.kmer_size());
            canonical = Some(db.is_canonical());
        }

        // Get all k-mers from this database
        let db_kmers = db.all_kmers()?;

        if args.verbose {
            eprintln!("  Merging {} k-mers...", db_kmers.len());
        }

        // Merge k-mers into the combined map
        for (kmer, count) in db_kmers {
            *all_kmers.entry(kmer).or_insert(0) += count;
            total_kmers += count as u64;
        }

        // Keep track of whether all databases are sorted
        sorted = sorted && db.header().sorted;
    }

    if args.verbose {
        eprintln!("Total unique k-mers after merge: {}", all_kmers.len());
        eprintln!("Total k-mer counts after merge: {}", total_kmers);
    }

    // Create merged database
    let kmer_size = kmer_size.ok_or_else(|| anyhow::anyhow!("No databases provided"))?;
    let canonical = canonical.unwrap_or(false);

    // Convert to sorted vector for RKDatabase
    let mut sorted_kmers: Vec<(u128, u32)> = all_kmers.into_iter().collect();
    sorted_kmers.sort_by_key(|(kmer, _)| *kmer);

    // Create RKDatabase with merged data
    Ok(RKDatabase::from_kmer_pairs(sorted_kmers, kmer_size.try_into()?, canonical, sorted)?)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::tempdir;

    #[test]
    fn test_merge_validation() {
        let temp_dir = tempdir().unwrap();
        let db1_path = temp_dir.path().join("db1.rkdb");
        let db2_path = temp_dir.path().join("db2.rkdb");
        let output_path = temp_dir.path().join("merged.rkdb");

        // Create test databases
        let db1 = RKDatabase::from_kmer_pairs(
            vec![(0x1234, 10), (0x5678, 20)],
            31,
            false,
            true
        ).unwrap();
        db1.to_file_path(&db1_path).unwrap();

        let db2 = RKDatabase::from_kmer_pairs(
            vec![(0x1234, 5), (0x9ABC, 15)],
            31,
            false,
            true
        ).unwrap();
        db2.to_file_path(&db2_path).unwrap();

        let args = MergeArgs {
            input: vec![db1_path, db2_path],
            output: output_path.clone(),
            temp_dir: None,
            threads: 0,
            verbose: false,
            quiet: true,
            force: false,
            keep_intermediate: false,
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
}