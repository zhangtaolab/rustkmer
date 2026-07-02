//! CLI argument definitions for rustkmer
//!
//! Provides command-line argument parsing using clap.

use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "rustkmer")]
#[command(about = "A fast k-mer counting tool for genomic data")]
#[command(version = env!("CARGO_PKG_VERSION"))]
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
        #[arg(
            long,
            help = "Display warnings when skipping k-mers with invalid characters"
        )]
        show_warnings: bool,

        /// Retained no-op alias: sorting is enabled by default (decision D-09).
        /// Has no effect; pass --no-sort to disable sorted output.
        #[arg(long, default_value = "true")]
        sort: bool,

        /// Disable sorting of output k-mers (creates unsorted database for faster counting)
        #[arg(long, conflicts_with = "sort")]
        no_sort: bool,

        /// Number of threads for parallel counting (default: all cores).
        ///
        /// Precedence (highest wins): `--threads` beats `RUSTKMER_THREADS`
        /// which beats `RAYON_NUM_THREADS` which beats all available CPU
        /// cores (`num_cpus`). Values < 1 are rejected at validation time.
        #[arg(long)]
        threads: Option<usize>,

        /// Minimum k-mer count threshold
        #[arg(short = 'L', long = "min-count")]
        #[arg(alias = "lower-count")]
        #[arg(alias = "low-count")]
        #[arg(help = "Filter out k-mers with count below this threshold")]
        min_count: Option<u64>,

        /// Maximum k-mer count threshold
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
        #[arg(short = 's', long, conflicts_with_all = ["kmers", "batch"])]
        sequence: Option<String>,

        /// Query k-mers from text file (one per line)
        #[arg(short = 'b', long, conflicts_with_all = ["kmers", "sequence"])]
        batch: Option<String>,

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

        /// Position-specific mutations (e.g., "3,4,5:2" or "3,4,5:2;6,7:1")
        #[arg(long = "position-mutations")]
        position_mutations: Option<String>,
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

    /// Merge multiple RKDB databases
    Merge {
        /// Input database files to merge
        #[arg(short = 'i', long, num_args = 2.., help = "Input database files to merge (at least 2 required)")]
        input: Vec<std::path::PathBuf>,

        /// Output database file
        #[arg(short = 'o', long, help = "Output merged database file")]
        output: std::path::PathBuf,

        /// Temporary directory for merge operations
        #[arg(
            long,
            help = "Temporary directory for merge operations (default: system temp)"
        )]
        temp_dir: Option<std::path::PathBuf>,

        /// Enable verbose output
        #[arg(short = 'v', long, help = "Enable verbose output")]
        verbose: bool,

        /// Suppress non-error output
        #[arg(short = 'q', long, help = "Suppress non-error output")]
        quiet: bool,

        /// Keep intermediate files (for debugging)
        #[arg(long, help = "Keep intermediate files (for debugging)")]
        keep_intermediate: bool,

        /// Check compatibility of databases without merging
        #[arg(
            long,
            help = "Check compatibility of databases without performing the merge"
        )]
        check_compatibility: bool,

        /// Maximum memory usage for merge operations (e.g., "32GB", "1TB")
        #[arg(
            long,
            help = "Maximum memory usage for merge operations (e.g., '32GB', '1TB'). Defaults to 50% of system memory."
        )]
        max_memory: Option<String>,

        /// Use prefix cache merge (memory-efficient with error isolation)
        #[arg(
            long,
            help = "Use prefix cache merge strategy for memory-efficient processing with error isolation"
        )]
        use_prefix_cache: bool,

        /// Batch size for prefix cache merge (number of k-mers per buffer flush)
        #[arg(
            long,
            default_value = "100000",
            help = "Batch size for prefix cache merge. Higher values use more memory but are faster. (default: 100000)"
        )]
        batch_size: usize,

        /// Number of threads for parallel processing (0 = all cores)
        #[arg(
            long,
            default_value = "0",
            help = "Number of threads for parallel processing (0 = use all cores)."
        )]
        num_threads: usize,

        /// Merge strategy for prefix cache mode
        #[arg(long, value_parser = ["auto", "memory", "streaming"], default_value = "auto", help = "Merge strategy for prefix cache mode: auto (use memory if <100MB), memory (force in-memory), streaming (always stream).")]
        merge_mode: String,
    },

    /// Calculate statistics for a k-mer database
    Stats {
        /// Database file
        database: String,

        /// Output format (text, json, csv, tsv)
        #[arg(short = 'f', long, default_value = "text", value_parser = ["text", "json", "csv", "tsv"])]
        format: String,

        /// Output file (stdout if not specified)
        #[arg(short, long)]
        output: Option<String>,

        /// Include detailed frequency distribution
        #[arg(long)]
        detailed: bool,

        /// Maximum bins for frequency distribution
        #[arg(long, default_value = "1000")]
        max_bins: usize,

        /// Use approximate median (faster, less memory)
        #[arg(long)]
        approximate: bool,

        /// Enable progress reporting for large databases
        #[arg(short, long)]
        progress: bool,

        /// Split output to separate files (basic stats and frequency distribution)
        #[arg(long)]
        split_output: bool,

        /// Output file for frequency distribution (required when --split-output is used)
        #[arg(long, required_if_eq("split_output", "true"))]
        freq_output: Option<String>,
    },

    /// Efficient prefix-based k-mer query for sorted databases
    PrefixQuery {
        /// Database file
        database: String,

        /// Sequence pattern to match (prefix or hybrid format like ATAC{N5}ACAC)
        #[arg(short = 'p', long, default_value = "")]
        pattern: String,

        /// Explicit prefix sequence (alternative to pattern)
        #[arg(short = 'x', long, conflicts_with = "pattern")]
        prefix: Option<String>,

        /// Enable hybrid search mode for patterns with internal wildcards
        #[arg(long, requires = "pattern")]
        hybrid: bool,

        /// Output format (table, json, csv, tsv)
        #[arg(short = 'f', long, default_value = "table", value_parser = ["table", "json", "csv", "tsv"])]
        format: String,

        /// Output file (stdout if not specified)
        #[arg(short = 'o', long)]
        output: Option<String>,

        /// Enable verbose output
        #[arg(short = 'v', long)]
        verbose: bool,

        /// Suppress non-error output
        #[arg(short = 'q', long)]
        quiet: bool,

        /// Show performance profiling
        #[arg(long = "profile")]
        profile: bool,

        /// Minimum count threshold
        #[arg(short = 'L', long = "min-count")]
        min_count: Option<u64>,

        /// Maximum count threshold
        #[arg(short = 'U', long = "max-count")]
        max_count: Option<u64>,
    },
}

// Filtering helper functions for the Count command
impl Commands {
    /// Create a count filter from the command parameters
    ///
    /// # Returns
    /// Option<CountFilter> for the filtering parameters
    pub fn create_count_filter(&self) -> Option<crate::hash::CountFilter> {
        match self {
            Commands::Count {
                min_count,
                max_count,
                ..
            } => {
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
            Commands::Count {
                min_count,
                max_count,
                ..
            } => {
                let mut errors = Vec::new();

                if let Some(min) = min_count {
                    if *min == 0 {
                        // Allow min_count = 0, which includes all k-mers
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
            Commands::Count {
                min_count,
                max_count,
                ..
            } => min_count.is_some() || max_count.is_some(),
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
                threads,
                ..
            } => {
                let mut errors = Vec::new();

                // Check if either input files or directory is provided
                if input.is_empty() && directory.is_none() {
                    errors.push(
                        "Either input files (-i) or directory (-d) must be specified".to_string(),
                    );
                }

                // Validate k-mer size
                if *k == 0 || *k > 127 {
                    errors.push("K-mer size must be between 1 and 127".to_string());
                }

                // Validate thread count (D-07: reject --threads < 1; mirrors
                // InvalidKmerSize collect-then-fail style)
                if threads.is_some_and(|t| t < 1) {
                    errors.push("--threads must be >= 1".to_string());
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
