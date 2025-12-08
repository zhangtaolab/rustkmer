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
        rustkmer::cli::args::Commands::FuzzyQuery { database, query, mutations, max_variants, parallel, batch_size, format, output, verbose, quiet, profile } => {
            let args = rustkmer::cli::commands::fuzzy::FuzzyQueryArgs {
                database: database.into(),
                query,
                mutations,
                max_variants,
                enable_parallel: parallel,
                batch_size,
                format,
                output: output.map(|o| o.into()),
                verbose,
                quiet,
                profile,
            };
            rustkmer::cli::commands::fuzzy::execute_fuzzy_query(&args)?;
        }
        rustkmer::cli::args::Commands::FuzzyQueryBatch { database, sequence, default_mutations, default_max_variants, batch_size, format, output, verbose, quiet, progress, fail_fast, include_headers } => {
            let args = rustkmer::cli::commands::fuzzy::FuzzyQueryBatchArgs {
                database: database.into(),
                query_file: sequence.into(),
                default_mutations,
                default_max_variants,
                batch_size,
                format,
                output: output.map(|o| o.into()),
                verbose,
                quiet,
                progress,
                fail_fast,
                include_headers,
            };
            rustkmer::cli::commands::fuzzy::execute_fuzzy_query_batch(&args)?;
        }
        rustkmer::cli::args::Commands::Benchmark { .. } => {
            rustkmer::cli::commands::benchmark::execute_benchmark(&args.command)?;
        }
        rustkmer::cli::args::Commands::Compare { databases, queries, query_count, output_dir, format, fuzzy, profile } => {
            eprintln!("Compare command not yet implemented");
            eprintln!("Databases: {:?}", databases);
            eprintln!("Queries: {}", queries);
            eprintln!("Query count: {}", query_count);
            eprintln!("Output dir: {}", output_dir);
            eprintln!("Format: {}", format);
            eprintln!("Fuzzy: {}", fuzzy);
            eprintln!("Profile: {}", profile);
            std::process::exit(1);
        }
        rustkmer::cli::args::Commands::Merge { input, output, temp_dir, threads, verbose, quiet, force, keep_intermediate } => {
            let args = rustkmer::cli::commands::merge::MergeArgs {
                input,
                output,
                temp_dir,
                threads,
                verbose,
                quiet,
                force,
                keep_intermediate,
            };
            rustkmer::cli::commands::merge::execute_merge(&args)?;
        }
        rustkmer::cli::args::Commands::Profile { command, args, output, depth, memory, cpu, duration } => {
            eprintln!("Profile command not yet implemented");
            eprintln!("Command: {}", command);
            eprintln!("Args: {:?}", args);
            eprintln!("Output: {:?}", output);
            eprintln!("Depth: {}", depth);
            eprintln!("Memory: {}", memory);
            eprintln!("CPU: {}", cpu);
            eprintln!("Duration: {}", duration);
            std::process::exit(1);
        }
    }

    Ok(())
}