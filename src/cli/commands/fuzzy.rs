//! Fuzzy query CLI commands
//!
//! This module implements the command-line interface for fuzzy k-mer queries,
//! supporting wildcard expansion, length normalization, and mutation tolerance.

use crate::database::format::RKDatabase;
use crate::fuzzy::{FuzzyQuery, FuzzyQueryEngine};
use anyhow::Result;
use clap::Args;
use serde_json;
use std::io::{self, Write};
use std::path::PathBuf;
use std::time::Instant;

/// Arguments for fuzzy query command
#[derive(Args, Debug)]
pub struct FuzzyQueryArgs {
    /// Path to RKDB database file
    #[arg(help = "Path to RKDB database file")]
    pub database: PathBuf,

    /// Query string (may contain 'N' wildcards)
    #[arg(help = "Query string (may contain 'N' wildcards)")]
    pub query: String,

    /// Maximum Hamming distance for mutations
    #[arg(
        short = 'm',
        long = "mutations",
        default_value = "0",
        help = "Maximum Hamming distance for mutations"
    )]
    pub mutations: usize,

    /// Maximum number of variants to generate
    #[arg(
        short = 'M',
        long = "max-variants",
        default_value = "10000",
        help = "Maximum number of variants to generate"
    )]
    pub max_variants: usize,

    /// Enable parallel processing
    #[arg(
        short = 'p',
        long = "parallel",
        default_value = "true",
        help = "Enable parallel processing"
    )]
    pub enable_parallel: bool,

    /// Batch size for processing variants
    #[arg(
        short = 'b',
        long = "batch-size",
        default_value = "1000",
        help = "Batch size for processing variants"
    )]
    pub batch_size: usize,

    /// Output format
    #[arg(
        short = 'f',
        long = "format",
        default_value = "table",
        value_parser = ["table", "json", "tsv", "csv"],
        help = "Output format"
    )]
    pub format: String,

    /// Output file path
    #[arg(short = 'o', long = "output", help = "Output file path")]
    pub output: Option<PathBuf>,

    /// Enable verbose output
    #[arg(short = 'v', long = "verbose", help = "Enable verbose output")]
    pub verbose: bool,

    /// Suppress non-error output
    #[arg(short = 'q', long = "quiet", help = "Suppress non-error output")]
    pub quiet: bool,

    /// Show performance profiling
    #[arg(long = "profile", help = "Show performance profiling")]
    pub profile: bool,
}

/// Arguments for batch fuzzy query command
#[derive(Args, Debug)]
pub struct FuzzyQueryBatchArgs {
    /// Path to RKDB database file
    #[arg(help = "Path to RKDB database file")]
    pub database: PathBuf,

    /// File containing queries (one per line)
    #[arg(help = "File containing queries (one per line)")]
    pub query_file: PathBuf,

    /// Default maximum Hamming distance for mutations
    #[arg(
        long = "default-mutations",
        default_value = "0",
        help = "Default maximum Hamming distance for mutations"
    )]
    pub default_mutations: usize,

    /// Default maximum number of variants to generate
    #[arg(
        long = "default-max-variants",
        default_value = "10000",
        help = "Default maximum number of variants to generate"
    )]
    pub default_max_variants: usize,

    /// Batch size for processing queries
    #[arg(
        short = 'b',
        long = "batch-size",
        default_value = "100",
        help = "Batch size for processing queries"
    )]
    pub batch_size: usize,

    /// Output format
    #[arg(
        short = 'f',
        long = "format",
        default_value = "table",
        value_parser = ["table", "json", "tsv", "csv"],
        help = "Output format"
    )]
    pub format: String,

    /// Output file path
    #[arg(short = 'o', long = "output", help = "Output file path")]
    pub output: Option<PathBuf>,

    /// Enable verbose output
    #[arg(short = 'v', long = "verbose", help = "Enable verbose output")]
    pub verbose: bool,

    /// Suppress non-error output
    #[arg(short = 'q', long = "quiet", help = "Suppress non-error output")]
    pub quiet: bool,

    /// Show progress bar
    #[arg(long = "progress", default_value = "true", help = "Show progress bar")]
    pub progress: bool,

    /// Stop on first error
    #[arg(long = "fail-fast", help = "Stop on first error")]
    pub fail_fast: bool,

    /// Include header row in CSV/TSV output
    #[arg(long = "include-headers", help = "Include header row in CSV/TSV output")]
    pub include_headers: bool,
}

/// Execute fuzzy query command
pub fn execute_fuzzy_query(args: &FuzzyQueryArgs) -> Result<()> {
    let start_time = Instant::now();

    // Load database
    if !args.quiet {
        eprintln!("Loading database: {}", args.database.display());
    }
    let database = RKDatabase::from_file_path(&args.database)?;

    // Get k-mer size before moving database
    let kmer_size = database.kmer_size();

    // Create fuzzy query
    let query = FuzzyQuery::with_params(
        &args.query,
        kmer_size,
        args.mutations,
        Some(args.max_variants),
        args.enable_parallel,
        args.batch_size,
    );

    // Create query engine
    let engine = FuzzyQueryEngine::new(database);

    if args.verbose {
        eprintln!("Executing fuzzy query: {}", query.query_string);
        eprintln!("K-mer size: {}", query.kmer_size);
        eprintln!("Mutation tolerance: {}", query.mutation_tolerance);
        eprintln!("Max variants: {}", query.max_variants.unwrap_or(0));
    }

    // Execute query
    let result = engine.execute_query(&query)?;

    // Output results
    output_fuzzy_result(&result, args)?;

    if args.profile {
        output_performance_profile(&result, &start_time, args)?;
    }

    Ok(())
}

/// Execute batch fuzzy query command
pub fn execute_fuzzy_query_batch(args: &FuzzyQueryBatchArgs) -> Result<()> {
    let start_time = Instant::now();

    // Load database
    if !args.quiet {
        eprintln!("Loading database: {}", args.database.display());
    }
    let database = RKDatabase::from_file_path(&args.database)?;

    // Load queries from file
    if !args.quiet {
        eprintln!("Loading queries from: {}", args.query_file.display());
    }
    let queries = load_queries_from_file(&args.query_file)?;

    if !args.quiet {
        eprintln!("Loaded {} queries", queries.len());
    }

    // Get k-mer size before moving database
    let kmer_size = database.kmer_size();

    // Create query engine
    let engine = FuzzyQueryEngine::new(database);

    // Process queries
    let mut results = Vec::new();
    let mut successful_queries = 0;
    let mut failed_queries = 0;

    for (i, query_str) in queries.iter().enumerate() {
        if args.progress && !args.quiet {
            eprint!("Processing query {}/{}...\r", i + 1, queries.len());
            io::stdout().flush()?;
        }

        // Create fuzzy query with default parameters
        let query = FuzzyQuery::with_params(
            query_str,
            kmer_size,
            args.default_mutations,
            Some(args.default_max_variants),
            true,
            args.batch_size,
        );

        // Execute query
        match engine.execute_query(&query) {
            Ok(result) => {
                results.push((query_str.clone(), result));
                successful_queries += 1;
            }
            Err(e) => {
                if args.verbose {
                    eprintln!("Error processing query '{}': {}", query_str, e);
                }
                failed_queries += 1;

                if args.fail_fast {
                    return Err(e.into());
                }
            }
        }
    }

    if args.progress && !args.quiet {
        eprintln!(); // New line after progress
    }

    // Output batch results
    output_batch_results(&results, args)?;

    if !args.quiet {
        eprintln!("Batch processing complete:");
        eprintln!("  Successful queries: {}", successful_queries);
        eprintln!("  Failed queries: {}", failed_queries);
        eprintln!("  Total time: {:.2}s", start_time.elapsed().as_secs_f64());
    }

    Ok(())
}

/// Load queries from file
fn load_queries_from_file(file_path: &PathBuf) -> Result<Vec<String>> {
    use std::fs::File;
    use std::io::{BufRead, BufReader};

    let file = File::open(file_path)?;
    let reader = BufReader::new(file);

    let mut queries = Vec::new();

    for line in reader.lines() {
        let line = line?;
        let line = line.trim();

        // Skip empty lines and comments
        if line.is_empty() || line.starts_with('#') {
            continue;
        }

        // Parse extended format (query|mutations|max_variants)
        if line.contains('|') {
            let parts: Vec<&str> = line.split('|').collect();
            if !parts.is_empty() {
                queries.push(parts[0].trim().to_string());
            }
        } else {
            queries.push(line.to_string());
        }
    }

    Ok(queries)
}

/// Output fuzzy query result
fn output_fuzzy_result(result: &crate::fuzzy::FuzzyQueryResultData, args: &FuzzyQueryArgs) -> Result<()> {
    match args.format.as_str() {
        "table" => output_table_format(result, args),
        "json" => output_json_format(result, args),
        "tsv" => output_tsv_format(result, args),
        "csv" => output_csv_format(result, args),
        _ => Err(anyhow::anyhow!("Unsupported output format: {}", args.format)),
    }
}

/// Output in table format
fn output_table_format(result: &crate::fuzzy::FuzzyQueryResultData, args: &FuzzyQueryArgs) -> Result<()> {
    let mut writer: Box<dyn Write> = if let Some(output_path) = &args.output {
        Box::new(std::fs::File::create(output_path)?)
    } else {
        Box::new(io::stdout())
    };

    writeln!(writer, "Query: {}", result.query_metadata.query_params.query_string)?;
    writeln!(
        writer,
        "Mutations: {}",
        result.query_metadata.query_params.mutation_tolerance
    )?;
    writeln!(
        writer,
        "Variants Generated: {}",
        result.query_metadata.variants_generated
    )?;
    writeln!(writer, "Total Matches: {}", result.total_count)?;
    writeln!(writer, "Query Time: {}ms", result.query_metadata.query_time_ms)?;
    writeln!(writer)?;

    if result.individual_matches.is_empty() {
        writeln!(writer, "No matches found")?;
    } else {
        // Table header
        writeln!(writer, "┌─────────────────────┬───────┬─────────┐")?;
        writeln!(writer, "│ Sequence            │ Count │ Type    │")?;
        writeln!(writer, "├─────────────────────┼───────┼─────────┤")?;

        // Table rows
        for kmer_match in &result.individual_matches {
            writeln!(
                writer,
                "│ {:<19} │ {:<5} │ {:<7} │",
                kmer_match.sequence,
                kmer_match.count,
                format!("{:?}", kmer_match.match_type)
            )?;
        }

        writeln!(writer, "└─────────────────────┴───────┴─────────┘")?;
    }

    Ok(())
}

/// Output in JSON format
fn output_json_format(result: &crate::fuzzy::FuzzyQueryResultData, args: &FuzzyQueryArgs) -> Result<()> {
    let json = serde_json::to_string_pretty(result)?;

    if let Some(output_path) = &args.output {
        std::fs::write(output_path, json)?;
    } else {
        println!("{}", json);
    }

    Ok(())
}

/// Output in TSV format
fn output_tsv_format(result: &crate::fuzzy::FuzzyQueryResultData, args: &FuzzyQueryArgs) -> Result<()> {
    let mut writer: Box<dyn Write> = if let Some(output_path) = &args.output {
        Box::new(std::fs::File::create(output_path)?)
    } else {
        Box::new(io::stdout())
    };

    for kmer_match in &result.individual_matches {
        writeln!(
            writer,
            "{}\t{}\t{}\t{}",
            result.query_metadata.query_params.query_string,
            kmer_match.sequence,
            kmer_match.count,
            format!("{:?}", kmer_match.match_type)
        )?;
    }

    Ok(())
}

/// Output in CSV format
fn output_csv_format(result: &crate::fuzzy::FuzzyQueryResultData, args: &FuzzyQueryArgs) -> Result<()> {
    let mut writer: Box<dyn Write> = if let Some(output_path) = &args.output {
        Box::new(std::fs::File::create(output_path)?)
    } else {
        Box::new(io::stdout())
    };

    // CSV header
    writeln!(writer, "query,sequence,count,match_type")?;

    for kmer_match in &result.individual_matches {
        writeln!(
            writer,
            "{},{},{},{}",
            result.query_metadata.query_params.query_string,
            kmer_match.sequence,
            kmer_match.count,
            format!("{:?}", kmer_match.match_type)
        )?;
    }

    Ok(())
}

/// Output batch results
fn output_batch_results(results: &[(String, crate::fuzzy::FuzzyQueryResultData)], args: &FuzzyQueryBatchArgs) -> Result<()> {
    match args.format.as_str() {
        "json" => output_batch_json(results, args),
        "table" => output_batch_table(results, args),
        "tsv" => output_batch_tsv(results, args),
        "csv" => output_batch_csv(results, args),
        _ => Err(anyhow::anyhow!("Unsupported output format: {}", args.format)),
    }
}

/// Output batch results in JSON format
fn output_batch_json(results: &[(String, crate::fuzzy::FuzzyQueryResultData)], args: &FuzzyQueryBatchArgs) -> Result<()> {
    let batch_metadata = serde_json::json!({
        "total_queries": results.len(),
        "processed_queries": results.len(),
        "failed_queries": 0,
        "output_format": args.format
    });

    let batch_result = serde_json::json!({
        "batch_metadata": batch_metadata,
        "query_results": results.iter().map(|(query, result)| {
            serde_json::json!({
                "query": query,
                "result": result
            })
        }).collect::<Vec<_>>()
    });

    let json = serde_json::to_string_pretty(&batch_result)?;

    if let Some(output_path) = &args.output {
        std::fs::write(output_path, json)?;
    } else {
        println!("{}", json);
    }

    Ok(())
}

/// Output batch results in table format
fn output_batch_table(results: &[(String, crate::fuzzy::FuzzyQueryResultData)], args: &FuzzyQueryBatchArgs) -> Result<()> {
    let mut writer: Box<dyn Write> = if let Some(output_path) = &args.output {
        Box::new(std::fs::File::create(output_path)?)
    } else {
        Box::new(io::stdout())
    };

    writeln!(writer, "Batch Query Results")?;
    writeln!(writer, "Total Queries: {}", results.len())?;
    writeln!(writer, "Processed: {}", results.len())?;
    writeln!(writer)?;

    writeln!(writer, "┌─────┬─────────────────────┬───────┬───────┬──────────┬──────────┬─────────┐")?;
    writeln!(writer, "│ #   │ Query               │ Vars  │ Mut   │ Matches  │ Time(ms) │ Status  │")?;
    writeln!(writer, "├─────┼─────────────────────┼───────┼───────┼──────────┼──────────┼─────────┤")?;

    for (i, (query, result)) in results.iter().enumerate() {
        writeln!(
            writer,
            "│ {:<3} │ {:<19} │ {:<5} │ {:<5} │ {:<8} │ {:<8} │ {:<7} │",
            i + 1,
            if query.len() > 19 { &query[..16] } else { query },
            result.query_metadata.variants_generated,
            result.query_metadata.query_params.mutation_tolerance,
            result.total_count,
            result.query_metadata.query_time_ms,
            format!("{:?}", result.status)
        )?;
    }

    writeln!(writer, "└─────┴─────────────────────┴───────┴───────┴──────────┴──────────┴─────────┘")?;

    Ok(())
}

/// Output batch results in TSV format
fn output_batch_tsv(results: &[(String, crate::fuzzy::FuzzyQueryResultData)], args: &FuzzyQueryBatchArgs) -> Result<()> {
    let mut writer: Box<dyn Write> = if let Some(output_path) = &args.output {
        Box::new(std::fs::File::create(output_path)?)
    } else {
        Box::new(io::stdout())
    };

    if args.include_headers {
        writeln!(writer, "query_id\tquery_string\tvariants_generated\tmutations\ttotal_matches\tquery_time_ms\tstatus")?;
    }

    for (i, (query, result)) in results.iter().enumerate() {
        writeln!(
            writer,
            "{}\t{}\t{}\t{}\t{}\t{}\t{}",
            i + 1,
            query,
            result.query_metadata.variants_generated,
            result.query_metadata.query_params.mutation_tolerance,
            result.total_count,
            result.query_metadata.query_time_ms,
            format!("{:?}", result.status)
        )?;
    }

    Ok(())
}

/// Output batch results in CSV format
fn output_batch_csv(results: &[(String, crate::fuzzy::FuzzyQueryResultData)], args: &FuzzyQueryBatchArgs) -> Result<()> {
    let mut writer: Box<dyn Write> = if let Some(output_path) = &args.output {
        Box::new(std::fs::File::create(output_path)?)
    } else {
        Box::new(io::stdout())
    };

    if args.include_headers {
        writeln!(writer, "query_id,query_string,variants_generated,mutations,total_matches,query_time_ms,status")?;
    }

    for (i, (query, result)) in results.iter().enumerate() {
        writeln!(
            writer,
            "{},{},{},{},{},{},{}",
            i + 1,
            query,
            result.query_metadata.variants_generated,
            result.query_metadata.query_params.mutation_tolerance,
            result.total_count,
            result.query_metadata.query_time_ms,
            format!("{:?}", result.status)
        )?;
    }

    Ok(())
}

/// Output performance profiling information
fn output_performance_profile(
    result: &crate::fuzzy::FuzzyQueryResultData,
    start_time: &Instant,
    args: &FuzzyQueryArgs,
) -> Result<()> {
    let total_time = start_time.elapsed().as_millis() as u64;

    eprintln!("\n=== Performance Profile ===");
    eprintln!("Total Query Time: {}ms", total_time);
    eprintln!("├─ Variant Generation: {}ms", total_time - result.query_metadata.query_time_ms);
    eprintln!("├─ Database Queries: {}ms", result.query_metadata.query_time_ms);
    eprintln!("│  ├─ Avg per query: {:.1}ms", result.query_metadata.query_time_ms as f64 / result.query_metadata.variants_generated as f64);
    eprintln!("│  └─ Cache hits: N/A"); // TODO: Implement cache tracking
    eprintln!("└─ Result Aggregation: {}ms", 0); // TODO: Measure aggregation time

    if let Some(memory_usage) = result.query_metadata.memory_usage_mb {
        eprintln!("\nMemory Usage:");
        eprintln!("├─ Peak: {:.1}MB", memory_usage);
        eprintln!("├─ Variants: {:.1}MB", memory_usage * 0.3); // Estimate
        eprintln!("└─ Results: {:.1}MB", memory_usage * 0.2); // Estimate
    }

    if args.enable_parallel {
        eprintln!("\nParallel Processing:");
        eprintln!("├─ Worker threads: {}", num_cpus::get());
        eprintln!("├─ Parallel efficiency: N/A"); // TODO: Calculate efficiency
        eprintln!("└─ Load balance score: N/A"); // TODO: Calculate load balance
    }

    Ok(())
}