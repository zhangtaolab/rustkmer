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
                log::error!("Error: {}", error);
            }
            std::process::exit(1);
        }
    }

    // Execute the appropriate command
    match args.command {
        rustkmer::cli::args::Commands::Count { .. } => {
            rustkmer::cli::commands::count::execute_count(&args)?;
        }
        rustkmer::cli::args::Commands::Query {
            database: _,
            kmers: _,
            sequence: _,
            batch: _,
            output: _,
            interactive: _,
            load: _,
            no_load: _,
        } => {
            rustkmer::cli::commands::query::execute_query(&args)?;
        }
        rustkmer::cli::args::Commands::Stats { .. } => {
            rustkmer::cli::commands::stats::execute_stats(&args)?;
        }
        rustkmer::cli::args::Commands::Dump { .. } => {
            rustkmer::cli::commands::dump::execute_dump(&args)?;
        }
        rustkmer::cli::args::Commands::FuzzyQuery {
            database,
            query,
            mutations,
            max_variants,
            batch_size,
            format,
            output,
            verbose,
            quiet,
            profile,
            position_mutations,
        } => {
            let args = rustkmer::cli::commands::fuzzy::FuzzyQueryArgs {
                database: database.into(),
                query,
                mutations,
                max_variants,
                batch_size,
                format,
                output: output.map(|o| o.into()),
                verbose,
                quiet,
                profile,
                position_mutations,
            };
            rustkmer::cli::commands::fuzzy::execute_fuzzy_query(&args)?;
        }
        rustkmer::cli::args::Commands::FuzzyQueryBatch {
            database,
            sequence,
            default_mutations,
            default_max_variants,
            batch_size,
            format,
            output,
            verbose,
            quiet,
            progress,
            fail_fast,
            include_headers,
        } => {
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
        rustkmer::cli::args::Commands::Merge {
            input,
            output,
            temp_dir,
            verbose,
            quiet,
            keep_intermediate,
            check_compatibility,
            max_memory,
            use_prefix_cache,
            batch_size,
            num_threads,
            merge_mode,
        } => {
            let args = rustkmer::cli::commands::merge::MergeArgs {
                input,
                output,
                temp_dir,
                verbose,
                quiet,
                keep_intermediate,
                check_compatibility,
                max_memory,
                use_prefix_cache,
                batch_size,
                num_threads,
                merge_mode,
            };
            rustkmer::cli::commands::merge::execute_merge(&args)?;
        }
        rustkmer::cli::args::Commands::PrefixQuery { .. } => {
            rustkmer::cli::commands::prefix::execute_prefix_query(&args)?;
        }
    }

    Ok(())
}
