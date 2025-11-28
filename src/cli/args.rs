//! CLI argument definitions for rustkmer
//!
//! Provides command-line argument parsing using clap.

use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "rustkmer")]
#[command(about = "A fast k-mer counting tool for genomic data")]
#[command(version = "0.1.0")]
pub struct Args {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Count k-mers in sequence files
    Count {
        /// K-mer size (1-127)
        #[arg(short, long)]
        k: usize,

        /// Input sequence files
        #[arg(short, long, num_args = 1..)]
        input: Vec<String>,

        /// Output file
        #[arg(short, long)]
        output: Option<String>,

        /// Use canonical k-mers (forward/reverse complement)
        #[arg(short = 'C', long)]
        canonical: bool,

        /// Hash table size
        #[arg(long, default_value = "1000000")]
        size: usize,

        /// Number of threads
        #[arg(short, long, default_value = "0")]
        threads: usize,

        /// Output format (binary or text)
        #[arg(long, default_value = "binary")]
        format: String,

        /// Quiet mode (suppress progress output)
        #[arg(short, long)]
        quiet: bool,

        /// Verbose mode
        #[arg(short, long)]
        verbose: bool,

        /// Show warnings for invalid k-mer characters (default: false)
        #[arg(long, help = "Display warnings when skipping k-mers with invalid characters")]
        show_warnings: bool,

        /// Sort output by k-mer sequence (default: sorted for optimal query performance)
        #[arg(long, default_value = "true")]
        sort: bool,

        /// Disable sorting of output k-mers (creates unsorted database for faster counting)
        #[arg(long, conflicts_with = "sort")]
        no_sort: bool,

        /// Minimum k-mer count threshold (jellyfish compatible)
        #[arg(short = 'L', long = "min-count")]
        #[arg(alias = "lower-count")]
        #[arg(alias = "low-count")]
        #[arg(help = "Filter out k-mers with count below this threshold")]
        min_count: Option<u64>,

        /// Maximum k-mer count threshold (jellyfish compatible)
        #[arg(short = 'U', long = "max-count")]
        #[arg(alias = "upper-count")]
        #[arg(alias = "high-count")]
        #[arg(help = "Filter out k-mers with count above this threshold")]
        max_count: Option<u64>,
    },

    /// Query k-mer counts from a database
    Query {
        /// Database file
        database: String,

        /// K-mers to query (multiple values supported)
        #[arg(num_args = 0..)]
        kmers: Vec<String>,

        /// Query k-mers from sequence file
        #[arg(short = 's', long, conflicts_with_all = ["kmers"])]
        sequence: Option<String>,

        /// Output file (stdout if not specified)
        #[arg(short, long)]
        output: Option<String>,

        /// Interactive mode (queries from stdin)
        #[arg(short, long)]
        interactive: bool,

        /// Force pre-loading of database file into memory
        #[arg(short, long)]
        load: bool,

        /// Disable pre-loading of database file into memory
        #[arg(short = 'L', long, conflicts_with = "load")]
        no_load: bool,
    },

    /// Generate statistics about k-mer database
    Stats {
        /// Database file
        database: String,
    },

    /// Dump k-mer database to text format
    Dump {
        /// Database file
        database: String,

        /// Output file
        #[arg(short, long)]
        output: Option<String>,
    },

    /// Fuzzy query with wildcard support and mutation tolerance
    FuzzyQuery {
        /// Database file
        database: String,

        /// Query string (may contain 'N' wildcards)
        query: String,

        /// Maximum Hamming distance for mutations
        #[arg(short = 'm', long, default_value = "0")]
        mutations: usize,

        /// Maximum number of variants to generate
        #[arg(short = 'M', long, default_value = "10000")]
        max_variants: usize,

        /// Enable parallel processing
        #[arg(short = 'p', long, default_value = "true")]
        parallel: bool,

        /// Batch size for processing variants
        #[arg(short = 'b', long, default_value = "1000")]
        batch_size: usize,

        /// Output format
        #[arg(short = 'f', long, default_value = "table", value_parser = ["table", "json", "tsv", "csv"])]
        format: String,

        /// Output file
        #[arg(short, long)]
        output: Option<String>,

        /// Enable verbose output
        #[arg(short = 'v', long)]
        verbose: bool,

        /// Suppress non-error output
        #[arg(short = 'q', long)]
        quiet: bool,

        /// Show performance profiling
        #[arg(long)]
        profile: bool,
    },

    /// Batch fuzzy queries from file
    FuzzyQueryBatch {
        /// Database file
        database: String,

        /// File containing queries (one per line)
        #[arg(short = 's', long)]
        sequence: String,

        /// Default maximum Hamming distance for mutations
        #[arg(long, default_value = "0")]
        default_mutations: usize,

        /// Default maximum number of variants to generate
        #[arg(long, default_value = "10000")]
        default_max_variants: usize,

        /// Batch size for processing queries
        #[arg(short = 'b', long, default_value = "100")]
        batch_size: usize,

        /// Output format
        #[arg(short = 'f', long, default_value = "table", value_parser = ["table", "json", "tsv", "csv"])]
        format: String,

        /// Output file
        #[arg(short, long)]
        output: Option<String>,

        /// Enable verbose output
        #[arg(short = 'v', long)]
        verbose: bool,

        /// Suppress non-error output
        #[arg(short = 'q', long)]
        quiet: bool,

        /// Show progress bar
        #[arg(long, default_value = "true")]
        progress: bool,

        /// Stop on first error
        #[arg(long)]
        fail_fast: bool,

        /// Include header row in CSV/TSV output
        #[arg(long)]
        include_headers: bool,
    }
}

// Filtering helper functions for the Count command
impl Commands {
    /// Create a count filter from the command parameters
    ///
    /// # Returns
    /// Option<CountFilter> for the filtering parameters
    pub fn create_count_filter(&self) -> Option<crate::hash::CountFilter> {
        match self {
            Commands::Count { min_count, max_count, .. } => {
                if min_count.is_some() || max_count.is_some() {
                    Some(crate::hash::CountFilter::new(*min_count, *max_count))
                } else {
                    None
                }
            }
            _ => None,
        }
    }

    /// Validate filtering parameters for the Count command
    ///
    /// # Returns
    /// Result<(), Vec<String>> with validation errors if any
    pub fn validate_filtering(&self) -> Result<(), Vec<String>> {
        match self {
            Commands::Count { min_count, max_count, .. } => {
                let mut errors = Vec::new();

                if let Some(min) = min_count {
                    if *min == 0 {
                        // Allow min_count = 0 for jellyfish compatibility
                        // but warn that it includes all k-mers
                    }
                }

                if let Some(max) = max_count {
                    if *max == 0 {
                        errors.push("Maximum count must be positive".to_string());
                    }
                }

                if let (Some(min), Some(max)) = (min_count, max_count) {
                    if min > max {
                        errors.push("Minimum count cannot exceed maximum count".to_string());
                    }
                }

                if errors.is_empty() {
                    Ok(())
                } else {
                    Err(errors)
                }
            }
            _ => Ok(()),
        }
    }

    /// Check if filtering is enabled for this command
    ///
    /// # Returns
    /// true if filtering parameters are specified
    pub fn has_filtering(&self) -> bool {
        match self {
            Commands::Count { min_count, max_count, .. } => {
                min_count.is_some() || max_count.is_some()
            }
            _ => false,
        }
    }
}