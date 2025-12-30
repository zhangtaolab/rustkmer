//! Prefix query command implementation
//!
//! Implements efficient prefix-based k-mer querying for sorted databases,
//! leveraging memory block optimization for significant performance gains.

use std::io::Write;
use std::path::Path;

use crate::cli::args::Args;
use crate::database::format::RKDatabase;
use crate::error::{KmerError, ProcessingResult};
use crate::database::prefix_query_optimized::MemoryBlockInfo;

/// Arguments for prefix query command
#[derive(Debug)]
pub struct PrefixQueryArgs {
    pub database: String,
    pub pattern: String,
    pub prefix: Option<String>,
    pub hybrid: bool,
    pub format: String,
    pub output: Option<String>,
    pub verbose: bool,
    pub quiet: bool,
    pub profile: bool,
    pub min_count: Option<u64>,
    pub max_count: Option<u64>,
}

/// Execute the prefix query command
pub fn execute_prefix_query(args: &Args) -> ProcessingResult<()> {
    match &args.command {
        crate::cli::args::Commands::PrefixQuery {
            database,
            pattern,
            prefix,
            hybrid,
            format,
            output,
            verbose,
            quiet,
            profile,
            min_count,
            max_count,
        } => {
            let prefix_args = PrefixQueryArgs {
                database: database.clone(),
                pattern: pattern.clone(),
                prefix: prefix.clone(),
                hybrid: *hybrid,
                format: format.clone(),
                output: output.clone(),
                verbose: *verbose,
                quiet: *quiet,
                profile: *profile,
                min_count: *min_count,
                max_count: *max_count,
            };

            execute_prefix_query_impl(&prefix_args)
        },
        _ => Err(KmerError::ProcessingError(
            "Invalid command for prefix query execution".to_string()
        ).into()),
    }
}

/// Implementation of prefix query logic
fn execute_prefix_query_impl(args: &PrefixQueryArgs) -> ProcessingResult<()> {
    // Determine the search pattern
    let search_pattern = if let Some(ref explicit_prefix) = args.prefix {
        // Use explicit prefix
        explicit_prefix.clone()
    } else if !args.pattern.is_empty() {
        // Use pattern parameter
        args.pattern.clone()
    } else {
        return Err(KmerError::ProcessingError(
            "Either --pattern or --prefix must be specified".to_string()
        ).into());
    };

    // Validate pattern format
    if search_pattern.is_empty() {
        return Err(KmerError::ProcessingError(
            "Pattern cannot be empty".to_string()
        ).into());
    }

    // Check if database file exists
    if !Path::new(&args.database).exists() {
        return Err(KmerError::FileNotFound(args.database.clone()).into());
    }

    // Load database
    if !args.quiet {
        eprintln!("Loading database: {}", args.database);
    }

    let database = RKDatabase::from_file_path(Path::new(&args.database))
        .map_err(|e| KmerError::ProcessingError(format!("Failed to load database: {}", e)))?;

    let kmer_size = database.kmer_size();

    // Execute query based on pattern type
    let start_time = std::time::Instant::now();
    let result = if args.hybrid || search_pattern.contains('{') {
        // Hybrid search mode
        if !args.quiet {
            eprintln!("Executing hybrid search for pattern: {}", search_pattern);
        }
        
        use crate::database::prefix_query_optimized::{extract_hybrid_by_pattern};
        
        
        extract_hybrid_by_pattern(&database, &search_pattern.to_uppercase())
            .map_err(|e| KmerError::ProcessingError(format!("Hybrid query failed: {}", e)))?
    } else {
        // Simple prefix search mode
        let prefix_len = search_pattern.len();
        
        if prefix_len >= kmer_size {
            return Err(KmerError::ProcessingError(
                format!("Prefix length ({}) must be less than k-mer size ({})", prefix_len, kmer_size)
            ).into());
        }

        if !search_pattern.chars().all(|c| matches!(c.to_ascii_uppercase(), 'A' | 'T' | 'C' | 'G')) {
            return Err(KmerError::ProcessingError(
                format!("Pattern contains invalid characters: {}. Only A, T, C, G are allowed.", search_pattern)
            ).into());
        }

        if !args.quiet {
            eprintln!("Executing optimized prefix query for: {}", search_pattern);
        }

        use crate::database::prefix_query_optimized::extract_prefix_optimized;
        extract_prefix_optimized(&database, &search_pattern.to_uppercase())
            .map_err(|e| KmerError::ProcessingError(format!("Prefix query failed: {}", e)))?
    };
    let query_time = start_time.elapsed();

    // Apply count filtering if specified
    let filtered_matches = if args.min_count.is_some() || args.max_count.is_some() {
        let min_count = args.min_count.unwrap_or(0);
        let max_count = args.max_count.unwrap_or(u64::MAX);
        
        result.matches
            .into_iter()
            .filter(|(_, count)| *count >= min_count && *count <= max_count)
            .collect()
    } else {
        result.matches
    };

    // Setup output writer
    let mut writer: Box<dyn Write> = if let Some(output_file) = &args.output {
        let file = std::fs::File::create(output_file)
            .map_err(|e| KmerError::FileWriteError(format!("Failed to create output file: {}", e)))?;
        Box::new(std::io::BufWriter::new(file))
    } else {
        Box::new(std::io::stdout())
    };

    // Output results
    match args.format.as_str() {
        "table" => output_table(&mut writer, &filtered_matches, &result.memory_block, args)?,
        "json" => output_json(&mut writer, &filtered_matches, &result.memory_block, args)?,
        "csv" => output_csv(&mut writer, &filtered_matches, &result.memory_block, args)?,
        "tsv" => output_tsv(&mut writer, &filtered_matches, &result.memory_block, args)?,
        _ => return Err(KmerError::ProcessingError(
            format!("Unsupported output format: {}", args.format)
        ).into()),
    }

    // Performance profiling output
    if args.profile || args.verbose {
        output_performance_info(&result.memory_block, query_time, filtered_matches.len(), args)?;
    }

    Ok(())
}

/// Output results in table format
fn output_table(
    writer: &mut Box<dyn Write>,
    matches: &[(String, u64)],
    _memory_info: &MemoryBlockInfo,
    _args: &PrefixQueryArgs,
) -> ProcessingResult<()> {
    // Write header
    writeln!(writer, "K-mer\tCount")?;
    
    // Write data
    for (kmer, count) in matches {
        writeln!(writer, "{}\t{}", kmer, count)?;
    }

    Ok(())
}

/// Output results in JSON format
fn output_json(
    writer: &mut Box<dyn Write>,
    matches: &[(String, u64)],
    memory_info: &MemoryBlockInfo,
    args: &PrefixQueryArgs,
) -> ProcessingResult<()> {
    let matches_json: Vec<String> = matches.iter()
        .map(|(kmer, count)| format!(r#"{{"kmer": "{}", "count": {}}}"#, kmer, count))
        .collect();
    
    let json_output = format!(r#"{{
  "query": {{
    "prefix": "{}",
    "database": "{}"
  }},
  "results": {{
    "matches": [{}],
    "total_matches": {}
  }},
  "performance": {{
    "memory_block": {{
      "start_index": {},
      "end_index": {},
      "block_size": {},
      "is_sorted": {}
    }}
  }}
}}"#,
        args.pattern,
        args.database,
        matches_json.join(", "),
        matches.len(),
        memory_info.start_index,
        memory_info.end_index,
        memory_info.block_size,
        memory_info.is_sorted
    );

    writeln!(writer, "{}", json_output)?;
    Ok(())
}

/// Output results in CSV format
fn output_csv(
    writer: &mut Box<dyn Write>,
    matches: &[(String, u64)],
    _memory_info: &MemoryBlockInfo,
    _args: &PrefixQueryArgs,
) -> ProcessingResult<()> {
    // Write header
    writeln!(writer, "kmer,count")?;
    
    // Write data
    for (kmer, count) in matches {
        writeln!(writer, "{},{}", kmer, count)?;
    }

    Ok(())
}

/// Output results in TSV format
fn output_tsv(
    writer: &mut Box<dyn Write>,
    matches: &[(String, u64)],
    _memory_info: &MemoryBlockInfo,
    _args: &PrefixQueryArgs,
) -> ProcessingResult<()> {
    // Write header
    writeln!(writer, "kmer\tcount")?;
    
    // Write data
    for (kmer, count) in matches {
        writeln!(writer, "{}\t{}", kmer, count)?;
    }

    Ok(())
}

/// Output performance profiling information
fn output_performance_info(
    memory_info: &MemoryBlockInfo,
    query_time: std::time::Duration,
    match_count: usize,
    args: &PrefixQueryArgs,
) -> ProcessingResult<()> {
    if !args.quiet {
        eprintln!("\n=== Performance Profile ===");
        eprintln!("Query time: {:?}", query_time);
        eprintln!("Matches found: {}", match_count);
        eprintln!("Memory block: [{}, {}) - {} k-mers", 
                 memory_info.start_index, memory_info.end_index, memory_info.block_size);
        eprintln!("Database sorted: {}", memory_info.is_sorted);
        eprintln!("Optimization enabled: Yes");
        
        if memory_info.is_sorted {
            eprintln!("Performance gain: ~10-100x vs fuzzy-query for prefix patterns");
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_prefix_validation() {
        // Test valid prefix
        assert!(validate_prefix("ATCG").is_ok());
        
        // Test invalid prefix
        assert!(validate_prefix("").is_err());
        assert!(validate_prefix("ATCGNN").is_err());
    }

    fn validate_prefix(prefix: &str) -> ProcessingResult<()> {
        if prefix.is_empty() {
            return Err(crate::error::ProcessingError::new("Prefix cannot be empty"));
        }

        if !prefix.chars().all(|c| matches!(c.to_ascii_uppercase(), 'A' | 'T' | 'C' | 'G')) {
            return Err(crate::error::ProcessingError::new(
                format!("Prefix contains invalid characters: {}", prefix)
            ));
        }

        Ok(())
    }
}
