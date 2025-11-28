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

    // Validate query arguments first
    if let rustkmer::cli::args::Commands::Query { .. } = &args.command {
        if let Err(errors) = rustkmer::cli::commands::query::validate_query_args(&args) {
            for error in errors {
                eprintln!("Error: {}", error);
            }
            std::process::exit(1);
        }
    }

    // Execute the appropriate command
    match args.command {
        rustkmer::cli::args::Commands::Count { .. } => {
            rustkmer::cli::commands::count::execute_count(&args)?;
        }
        rustkmer::cli::args::Commands::Query { .. } => {
            rustkmer::cli::commands::query::execute_query(&args)?;
        }
        rustkmer::cli::args::Commands::Stats { database } => {
            eprintln!("Stats command not yet implemented");
            eprintln!("Database: {}", database);
            std::process::exit(1);
        }
        rustkmer::cli::args::Commands::Dump { .. } => {
            rustkmer::cli::commands::dump::execute_dump(&args)?;
        }
    }

    Ok(())
}