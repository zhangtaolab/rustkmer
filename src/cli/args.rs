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
        /// K-mer size (1-64)
        #[arg(short, long)]
        k: usize,

        /// Input sequence files
        #[arg(short = 'i', long, num_args = 1.., conflicts_with = "directory")]
        input: Vec<String>,

        /// Process all files in directory
        #[arg(long = "directory", short = 'd', conflicts_with = "input")]
        directory: Option<String>,

        /// Select specific files from directory (interactive)
        #[arg(short = 's', long, requires = "directory")]
        select: bool,

        /// Recursive directory search
        #[arg(long, default_value_t = true)]
        recursive: bool,

        /// Disable recursive directory search
        #[arg(long = "no-recursive", conflicts_with = "recursive")]
        no_recursive: bool,

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
    },

    /// Run comprehensive performance benchmarks
    Benchmark {
        /// Test data directory (default: /Users/forrest/Temp/demodata)
        #[arg(long, default_value = "/Users/forrest/Temp/demodata")]
        data_dir: String,

        /// Output directory for results
        #[arg(short = 'o', long, default_value = "/Users/forrest/Temp/demodata/performance_comparison")]
        output_dir: String,

        /// K-mer sizes to test (comma-separated)
        #[arg(long, default_value = "13,21,31")]
        kmer_sizes: String,

        /// Include compression performance tests
        #[arg(long)]
        compression: bool,

        /// Include memory profiling
        #[arg(long)]
        memory: bool,

        /// Number of iterations for each test
        #[arg(long, default_value = "3")]
        iterations: usize,

        /// Output format
        #[arg(short = 'f', long, default_value = "json", value_parser = ["json", "csv", "table"])]
        format: String,

        /// Generate visualizations
        #[arg(long)]
        visualize: bool,

        /// Compare against Jellyfish
        #[arg(long)]
        compare_jellyfish: bool,
    },

    /// Direct performance comparison with Jellyfish
    Compare {
        /// Database files to compare (space-separated)
        #[arg(short = 'd', long, num_args = 1..)]
        databases: Vec<String>,

        /// Query file for testing
        #[arg(short = 'q', long)]
        queries: String,

        /// Number of queries to test
        #[arg(long, default_value = "1000")]
        query_count: usize,

        /// Output directory for results
        #[arg(short = 'o', long, default_value = "/Users/forrest/Temp/demodata/performance_comparison")]
        output_dir: String,

        /// Output format
        #[arg(short = 'f', long, default_value = "json", value_parser = ["json", "csv", "table"])]
        format: String,

        /// Include fuzzy queries in comparison
        #[arg(long)]
        fuzzy: bool,

        /// Enable detailed profiling
        #[arg(long)]
        profile: bool,
    },

    /// Performance profiling and analysis
    Profile {
        /// Command to profile (query, fuzzy-query, count)
        #[arg(long)]
        command: String,

        /// Arguments for the command being profiled
        #[arg(short = 'a', long, num_args = 1..)]
        args: Vec<String>,

        /// Output file for profiling results
        #[arg(short = 'o', long)]
        output: Option<String>,

        /// Profile depth (basic, detailed, full)
        #[arg(long, default_value = "detailed", value_parser = ["basic", "detailed", "full"])]
        depth: String,

        /// Include memory profiling
        #[arg(long)]
        memory: bool,

        /// Include CPU profiling
        #[arg(long)]
        cpu: bool,

        /// Duration of profiling (seconds)
        #[arg(long, default_value = "60")]
        duration: u64,
    },

    /// Merge multiple RKDB databases
    Merge {
        /// Input database files to merge
        #[arg(short = 'i', long, num_args = 2.., help = "Input database files to merge (at least 2 required)")]
        input: Vec<std::path::PathBuf>,

        /// Output database file
        #[arg(short = 'o', long, help = "Output merged database file")]
        output: std::path::PathBuf,

        /// Temporary directory for merge operations
        #[arg(long, help = "Temporary directory for merge operations (default: system temp)")]
        temp_dir: Option<std::path::PathBuf>,

        /// Number of threads for merging
        #[arg(short = 't', long, default_value = "0", help = "Number of threads for merging (0 = auto-detect)")]
        threads: usize,

        /// Enable verbose output
        #[arg(short = 'v', long, help = "Enable verbose output")]
        verbose: bool,

        /// Suppress non-error output
        #[arg(short = 'q', long, help = "Suppress non-error output")]
        quiet: bool,

        /// Force merge even if databases have incompatible settings
        #[arg(long, help = "Force merge even if databases have incompatible settings (not recommended)")]
        force: bool,

        /// Keep intermediate files (for debugging)
        #[arg(long, help = "Keep intermediate files (for debugging)")]
        keep_intermediate: bool,
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

    /// Validate input parameters for the Count command
    ///
    /// # Returns
    /// Result<(), Vec<String>> with validation errors if any
    pub fn validate_input(&self) -> Result<(), Vec<String>> {
        match self {
            Commands::Count {
                input,
                directory,
                k,
                ..
            } => {
                let mut errors = Vec::new();

                // Check if either input files or directory is provided
                if input.is_empty() && directory.is_none() {
                    errors.push("Either input files (-i) or directory (-d) must be specified".to_string());
                }

                // Validate k-mer size
                if *k == 0 || *k > 127 {
                    errors.push("K-mer size must be between 1 and 127".to_string());
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

    /// Check if directory processing is enabled
    ///
    /// # Returns
    /// true if directory parameter is specified
    pub fn is_directory_mode(&self) -> bool {
        match self {
            Commands::Count { directory, .. } => directory.is_some(),
            _ => false,
        }
    }

    /// Get directory path if directory mode is enabled
    ///
    /// # Returns
    /// Option<&str> with the directory path
    pub fn get_directory(&self) -> Option<&str> {
        match self {
            Commands::Count { directory, .. } => directory.as_deref(),
            _ => None,
        }
    }

    /// Check if interactive file selection is enabled
    ///
    /// # Returns
    /// true if select parameter is specified
    pub fn is_select_mode(&self) -> bool {
        match self {
            Commands::Count { select, .. } => *select,
            _ => false,
        }
    }

    /// Check if recursive directory search is enabled
    ///
    /// # Returns
    /// true if recursive parameter is specified
    pub fn is_recursive(&self) -> bool {
        match self {
            Commands::Count { recursive, .. } => *recursive,
            _ => false,
        }
    }
}