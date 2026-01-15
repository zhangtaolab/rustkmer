//! Query command implementation
//!
//! Implements k-mer querying functionality with support for individual k-mers,
//! multiple k-mers, sequence files, and interactive mode.

use std::io::{self, BufRead, Write};
use std::path::Path;

use crate::cli::args::Args;
use crate::database::{format::DatabaseHeader, DatabaseQuery};
use crate::error::{KmerError, ProcessingResult};
use crate::io::fasta::{validate_fasta_file, FastaProcessor};

/// Execute the query command
pub fn execute_query(args: &Args) -> ProcessingResult<()> {
    match &args.command {
        crate::cli::args::Commands::Query {
            database,
            kmers,
            sequence,
            batch,
            output,
            interactive,
            load,
            no_load,
        } => {
            // Validate input parameters
            if kmers.is_empty() && sequence.is_none() && batch.is_none() && !interactive {
                return Err(KmerError::ProcessingError(
                    "Must specify k-mers, sequence file, batch file, or interactive mode"
                        .to_string(),
                )
                .into());
            }

            // Determine preload strategy
            let preload =
                *load || (!*no_load && (*interactive || sequence.is_some() || batch.is_some()));

            // Open database
            let mut db_query = DatabaseQuery::open(database, preload).map_err(|e| {
                KmerError::ProcessingError(format!("Failed to open database: {}", e))
            })?;

            // Output setup
            let mut writer: Box<dyn Write> = if let Some(output_file) = output {
                let file = std::fs::File::create(output_file).map_err(|e| {
                    KmerError::FileWriteError(format!("Failed to create output file: {}", e))
                })?;
                Box::new(std::io::BufWriter::new(file))
            } else {
                Box::new(std::io::stdout())
            };

            // Handle different query modes
            if *interactive {
                let db_info = db_query.get_info().clone();
                handle_interactive_mode(&mut db_query, &mut writer, &db_info)?;
            } else if let Some(sequence_file) = sequence {
                let db_info = db_query.get_info().clone();
                handle_sequence_query(&mut db_query, &mut writer, sequence_file, &db_info)?;
            } else if let Some(batch_file) = batch {
                let db_info = db_query.get_info().clone();
                handle_batch_query(&mut db_query, &mut writer, batch_file, &db_info)?;
            } else if !kmers.is_empty() {
                let db_info = db_query.get_info().clone();
                handle_kmer_queries(&mut db_query, &mut writer, kmers, &db_info)?;
            }

            Ok(())
        }
        _ => {
            Err(KmerError::ProcessingError("Invalid command for execute_query".to_string()).into())
        }
    }
}

/// Handle individual k-mer queries
fn handle_kmer_queries(
    db_query: &mut DatabaseQuery,
    writer: &mut Box<dyn Write>,
    kmers: &[String],
    db_info: &DatabaseHeader,
) -> ProcessingResult<()> {
    eprintln!(
        "Querying {} k-mers from database (k={})...",
        kmers.len(),
        db_info.kmer_size
    );

    let results = db_query.query_multiple(kmers)?;

    for (kmer, count) in results {
        if count > 0 {
            writeln!(writer, "{}\t{}", kmer, count)
                .map_err(|e| KmerError::FileWriteError(format!("Failed to write result: {}", e)))?;
        } else {
            // Show invalid k-mer error instead of 0 count
            if kmer.len() != db_info.kmer_size as usize {
                writeln!(writer, "Invalid mer '{}'", kmer).map_err(|e| {
                    KmerError::FileWriteError(format!("Failed to write error: {}", e))
                })?;
            }
        }
    }

    eprintln!("Query completed successfully");
    Ok(())
}

/// Handle batch query from file
fn handle_batch_query(
    db_query: &mut DatabaseQuery,
    writer: &mut Box<dyn Write>,
    batch_file: &str,
    _db_info: &DatabaseHeader,
) -> ProcessingResult<()> {
    eprintln!("Querying k-mers from batch file: {}", batch_file);

    // Validate batch file
    let path = Path::new(batch_file);
    if !path.exists() {
        return Err(KmerError::FileNotFound(batch_file.to_string()).into());
    }

    // Read k-mers from file
    let file = std::fs::File::open(path).map_err(|e| KmerError::FileFormatError {
        file: batch_file.to_string(),
        reason: format!("Failed to open batch file: {}", e),
    })?;
    let reader = std::io::BufReader::new(file);

    let mut kmer_list = Vec::new();
    let mut line_num = 0;

    for line in reader.lines() {
        line_num += 1;
        let line = line.map_err(|e| KmerError::FileFormatError {
            file: batch_file.to_string(),
            reason: format!("Error reading line {}: {}", line_num, e),
        })?;
        let trimmed = line.trim();

        // Skip empty lines and comments
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }

        // Validate k-mer format
        if !trimmed.chars().all(|c| matches!(c, 'A' | 'T' | 'C' | 'G')) {
            eprintln!(
                "Warning: Invalid k-mer '{}' at line {}, skipping",
                trimmed, line_num
            );
            continue;
        }

        kmer_list.push(trimmed.to_string());
    }

    if kmer_list.is_empty() {
        eprintln!("Warning: No valid k-mers found in batch file");
        return Ok(());
    }

    eprintln!("Loaded {} k-mers from batch file", kmer_list.len());

    // Query k-mers in batches for better performance
    let batch_size = 1000; // Process 1000 k-mers at a time
    let mut total_queries = 0;
    let mut found_kmers = 0;

    for chunk in kmer_list.chunks(batch_size) {
        let results = db_query.query_multiple(chunk)?;

        for (kmer, count) in results {
            total_queries += 1;

            // Always output the k-mer with its count (0 if not found)
            writeln!(writer, "{}\t{}", kmer, count)
                .map_err(|e| KmerError::FileWriteError(format!("Failed to write result: {}", e)))?;

            if count > 0 {
                found_kmers += 1;
            }
        }
    }

    eprintln!(
        "Processed {} k-mers, found {} with non-zero counts",
        total_queries, found_kmers
    );
    Ok(())
}

/// Handle sequence file queries
fn handle_sequence_query(
    db_query: &mut DatabaseQuery,
    writer: &mut Box<dyn Write>,
    sequence_file: &str,
    db_info: &DatabaseHeader,
) -> ProcessingResult<()> {
    eprintln!("Querying k-mers from sequence file: {}", sequence_file);

    // Validate sequence file
    let path = Path::new(sequence_file);
    if !path.exists() {
        return Err(KmerError::FileNotFound(sequence_file.to_string()).into());
    }

    validate_fasta_file(path)?;

    // Process sequence file
    let processor = FastaProcessor::new(path);
    let mut total_queries = 0;
    let mut found_kmers = 0;

    processor.process_file(|record| {
        let sequence = record.seq();

        // Skip sequences shorter than k
        if sequence.len() < db_info.kmer_size as usize {
            return Ok(());
        }

        // Extract all k-mers from sequence
        for i in 0..=(sequence.len() - db_info.kmer_size as usize) {
            let kmer_seq = std::str::from_utf8(&sequence[i..i + db_info.kmer_size as usize])
                .unwrap_or("INVALID");

            total_queries += 1;

            if let Ok(Some(count)) = db_query.query_kmer(kmer_seq) {
                writeln!(writer, "{}\t{}", kmer_seq, count)?;
                if count > 0 {
                    found_kmers += 1;
                }
            } else {
                // Show k-mer with 0 count
                writeln!(writer, "{}\t0", kmer_seq)?;
            }
        }

        Ok(())
    })?;

    eprintln!(
        "Processed {} k-mers, found {} with non-zero counts",
        total_queries, found_kmers
    );
    Ok(())
}

/// Handle interactive query mode
fn handle_interactive_mode(
    db_query: &mut DatabaseQuery,
    writer: &mut Box<dyn Write>,
    db_info: &DatabaseHeader,
) -> ProcessingResult<()> {
    eprintln!("Interactive query mode (k={})", db_info.kmer_size);
    eprintln!("Enter k-mers to query (Ctrl+D to exit):");

    let stdin = io::stdin();
    let lines = stdin.lock().lines();

    for line in lines {
        let line =
            line.map_err(|e| KmerError::ProcessingError(format!("Failed to read input: {}", e)))?;

        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }

        // Handle multiple k-mers in one line
        let kmer_strings: Vec<&str> = trimmed.split_whitespace().collect();

        for kmer_str in kmer_strings {
            match db_query.query_kmer(kmer_str) {
                Ok(Some(count)) => {
                    writeln!(writer, "{}\t{}", kmer_str, count)?;
                }
                Ok(None) => {
                    if kmer_str.len() != db_info.kmer_size as usize {
                        writeln!(writer, "Invalid mer '{}'", kmer_str)?;
                    } else {
                        writeln!(writer, "{}\t0", kmer_str)?;
                    }
                }
                Err(e) => {
                    writeln!(writer, "Error querying '{}': {}", kmer_str, e)?;
                }
            }
        }
    }

    eprintln!("Interactive mode ended");
    Ok(())
}

/// Validate query parameters
pub fn validate_query_args(args: &Args) -> Result<(), Vec<String>> {
    match &args.command {
        crate::cli::args::Commands::Query {
            database,
            kmers,
            sequence,
            interactive,
            load,
            no_load,
            ..
        } => {
            let mut errors = Vec::new();

            // Check if database file exists
            if !Path::new(database).exists() {
                errors.push(format!("Database file not found: {}", database));
            }

            // Check for contradictory options
            if *load && *no_load {
                errors.push("Cannot specify both --load and --no-load".to_string());
            }

            // Check for conflicting input modes
            if !kmers.is_empty() && sequence.is_some() {
                errors.push("Cannot specify both k-mers and sequence file".to_string());
            }
            if !kmers.is_empty() && *interactive {
                errors.push("Cannot specify both k-mers and interactive mode".to_string());
            }
            if sequence.is_some() && *interactive {
                errors.push("Cannot specify both sequence file and interactive mode".to_string());
            }

            // Validate k-mer sequences if provided
            for (i, kmer) in kmers.iter().enumerate() {
                if kmer.is_empty() {
                    errors.push(format!("Empty k-mer at position {}", i + 1));
                } else if !kmer
                    .chars()
                    .all(|c| matches!(c, 'A' | 'T' | 'G' | 'C' | 'a' | 't' | 'g' | 'c'))
                {
                    errors.push(format!("Invalid characters in k-mer '{}'", kmer));
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cli::args::{Args, Commands};
    use std::io::Write;

    // Helper function to create a temporary database file
    fn create_temp_db() -> tempfile::NamedTempFile {
        let temp_file = tempfile::NamedTempFile::new().unwrap();
        // Write minimal valid content
        let mut file = temp_file.as_file();
        // Write a minimal header (magic + version)
        file.write_all(b"RKDB").unwrap();
        file.write_all(&[1u8; 8]).unwrap(); // placeholder for version and other fields
        temp_file
    }

    #[test]
    fn test_validate_query_args_valid() {
        let temp_db = create_temp_db();
        let args = Args {
            command: Commands::Query {
                database: temp_db.path().to_str().unwrap().to_string(),
                kmers: vec!["ATGCG".to_string()],
                sequence: None,
                output: None,
                interactive: false,
                load: false,
                no_load: false,
                batch: None,
            },
        };

        assert!(validate_query_args(&args).is_ok());
    }

    #[test]
    fn test_validate_query_args_conflicting_options() {
        let temp_db = create_temp_db();
        let args = Args {
            command: Commands::Query {
                database: temp_db.path().to_str().unwrap().to_string(),
                kmers: vec!["ATGCG".to_string()],
                sequence: Some("test.fa".to_string()),
                output: None,
                interactive: false,
                load: false,
                no_load: false,
                batch: None,
            },
        };

        assert!(validate_query_args(&args).is_err());
    }

    #[test]
    fn test_validate_query_args_invalid_kmer() {
        let temp_db = create_temp_db();
        let args = Args {
            command: Commands::Query {
                database: temp_db.path().to_str().unwrap().to_string(),
                kmers: vec!["ATXCG".to_string()], // Invalid character
                sequence: None,
                output: None,
                interactive: false,
                load: false,
                no_load: false,
                batch: None,
            },
        };

        assert!(validate_query_args(&args).is_err());
    }
}
