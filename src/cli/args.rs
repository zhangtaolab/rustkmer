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

        /// Sort output by k-mer sequence (default: unsorted for performance)
        #[arg(long)]
        sort: bool,
    },

    /// Query k-mer counts from a database
    Query {
        /// Database file
        database: String,

        /// K-mer to query
        kmer: String,

        /// K-mer size
        #[arg(short, long)]
        k: usize,
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
}