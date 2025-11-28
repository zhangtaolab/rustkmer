//! Main entry point for rustkmer CLI application
//!
//! Provides command-line interface for k-mer counting functionality.

use clap::Parser;
use rustkmer::cli::args::Args;

fn main() -> anyhow::Result<()> {
    // Parse command line arguments
    let args = Args::parse();

    // Initialize logging
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    // Execute the appropriate command
    match args.command {
        rustkmer::cli::args::Commands::Count { .. } => {
            rustkmer::cli::commands::count::execute_count(&args)?;
        }
        rustkmer::cli::args::Commands::Query { database, kmer, k } => {
            eprintln!("Query command not yet implemented");
            eprintln!("Database: {}, K-mer: {}, K: {}", database, kmer, k);
            std::process::exit(1);
        }
        rustkmer::cli::args::Commands::Stats { database } => {
            eprintln!("Stats command not yet implemented");
            eprintln!("Database: {}", database);
            std::process::exit(1);
        }
        rustkmer::cli::args::Commands::Dump { database, output } => {
            eprintln!("Dump command not yet implemented");
            eprintln!("Database: {}, Output: {:?}", database, output);
            std::process::exit(1);
        }
    }

    Ok(())
}