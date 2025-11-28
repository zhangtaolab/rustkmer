//! Count command implementation
//!
//! Implements the k-mer counting functionality.

use clap::Parser;
use std::path::Path;
use std::sync::Arc;
use std::time::Instant;

use crate::cli::args::Args;
use crate::error::{KmerError, ProcessingResult};
use crate::hash::table::KmerCounter;
use crate::io::fasta::{FastaProcessor, validate_fasta_file};
use crate::io::fastq::{FastqProcessor, validate_fastq_file};
use crate::kmer::encoding::encode_kmer_bytes;
use crate::kmer::operations::{canonical_kmer, reverse_complement};

/// Execute the count command
pub fn execute_count(args: &Args) -> ProcessingResult<()> {
    match &args.command {
        crate::cli::args::Commands::Count {
            k,
            input,
            output,
            canonical,
            size,
            threads,
            format,
            quiet,
            verbose,
            sort,
        } => {
            // Validate k-mer size
            if *k < 1 || *k > 127 {
                return Err(KmerError::InvalidKmerSize(*k as u32).into());
            }

            // Validate thread count
            let num_threads = if *threads == 0 {
                std::thread::available_parallelism()
                    .map_err(|e| KmerError::ProcessingError(format!(
                        "Failed to get available parallelism: {}", e
                    )))?
                    .get()
            } else {
                *threads
            };

            if *verbose {
                eprintln!("rustkmer count starting...");
                eprintln!("K-mer size: {}", k);
                eprintln!("Canonical mode: {}", canonical);
                eprintln!("Thread count: {}", num_threads);
                eprintln!("Hash table size: {}", size);
                eprintln!("Input files: {:?}", input);
                if let Some(out) = output {
                    eprintln!("Output file: {}", out);
                }
            }

            // Create k-mer counter
            let counter = Arc::new(KmerCounter::new(
                *k,
                *canonical,
                *size,
                *threads,
            )?);

            let start_time = Instant::now();

            // Process each input file
            for (file_idx, file_path) in input.iter().enumerate() {
                let path = Path::new(file_path);

                if !path.exists() {
                    return Err(KmerError::FileNotFound(file_path.clone()).into());
                }

                if !*quiet {
                    eprintln!("Processing file {}/{}: {}", file_idx + 1, input.len(), file_path);
                }

                // Determine file format and process
                let file_extension = path.extension()
                    .and_then(|ext| ext.to_str())
                    .map(|s| s.to_ascii_lowercase());

                let result = match file_extension.as_deref() {
                    Some("fa") | Some("fasta") | Some("fna") | Some("ffn") => {
                        // Validate FASTA file
                        validate_fasta_file(path)?;

                        // Process FASTA file
                        let processor = FastaProcessor::new(path);
                        process_fasta_file(&processor, &counter, *k, *canonical, *quiet, *verbose)
                    },
                    Some("fq") | Some("fastq") => {
                        // Validate FASTQ file
                        validate_fastq_file(path)?;

                        // Process FASTQ file
                        let processor = FastqProcessor::new(path);
                        process_fastq_file(&processor, &counter, *k, *canonical, *quiet, *verbose)
                    },
                    _ => {
                        // Try to auto-detect format
                        if file_path.to_ascii_lowercase().contains("fastq") ||
                           file_path.to_ascii_lowercase().contains("fq") {
                            let processor = FastqProcessor::new(path);
                            process_fastq_file(&processor, &counter, *k, *canonical, *quiet, *verbose)
                        } else {
                            // Default to FASTA
                            let processor = FastaProcessor::new(path);
                            process_fasta_file(&processor, &counter, *k, *canonical, *quiet, *verbose)
                        }
                    }
                };

                if let Err(e) = result {
                    return Err(KmerError::ProcessingError(format!(
                        "Failed to process file {}: {}", file_path, e
                    )).into());
                }

                if !*quiet {
                    let elapsed = start_time.elapsed().as_secs_f64();
                    let stats = counter.get_stats();
                    eprintln!("  Total k-mers processed: {}", stats.total_kmers);
                    eprintln!("  Unique k-mers found: {}", stats.unique_kmers);
                    eprintln!("  Elapsed time: {:.2} seconds", elapsed);
                }
            }

            // Generate output
            if let Some(output_file) = output {
                let output_path = Path::new(output_file);

                match format.as_str() {
                    "text" => {
                        output_text_format(&counter, output_path, *quiet, *sort)?;
                    },
                    "binary" | _ => {
                        output_binary_format(&counter, output_path, *quiet, *sort)?;
                    },
                }
            }

            let total_time = start_time.elapsed();
            let final_stats = counter.get_stats();

            if !*quiet {
                eprintln!("Counting completed successfully!");
                eprintln!("Total k-mers: {}", final_stats.total_kmers);
                eprintln!("Unique k-mers: {}", final_stats.unique_kmers);
                eprintln!("Total time: {:.2} seconds", total_time.as_secs_f64());

                if let Some(output_file) = output {
                    eprintln!("Results saved to: {}", output_file);
                }
            }

            Ok(())
        },
        _ => Err(KmerError::ProcessingError("Invalid command for execute_count".to_string()).into()),
    }
}

/// Process a FASTA file and count k-mers
fn process_fasta_file(
    processor: &FastaProcessor,
    counter: &Arc<KmerCounter>,
    k: usize,
    canonical: bool,
    quiet: bool,
    verbose: bool,
) -> ProcessingResult<()> {
    processor.process_file(|record| {
        let sequence = record.seq();

        // Skip sequences shorter than k
        if sequence.len() < k {
            return Ok(());
        }

        // Extract and count k-mers
        for i in 0..=(sequence.len() - k) {
            let kmer_seq = &sequence[i..i + k];

            match encode_kmer_bytes(kmer_seq) {
                Ok(encoded_kmer) => {
                    let final_kmer = if canonical {
                        match canonical_kmer(encoded_kmer, k) {
                            Ok(canonical) => canonical,
                            Err(_) => continue, // Skip invalid k-mers
                        }
                    } else {
                        encoded_kmer
                    };

                    counter.increment(final_kmer).map_err(|e| {
                        KmerError::ProcessingError(format!("Failed to increment k-mer count: {}", e))
                    })?;
                },
                Err(_) => {
                    // Skip k-mers with invalid characters (N, etc.)
                    if verbose {
                        eprintln!("Warning: Skipping k-mer with invalid characters at position {} in sequence {}",
                                i, record.id());
                    }
                }
            }
        }

        Ok(())
    })
}

/// Process a FASTQ file and count k-mers
fn process_fastq_file(
    processor: &FastqProcessor,
    counter: &Arc<KmerCounter>,
    k: usize,
    canonical: bool,
    quiet: bool,
    verbose: bool,
) -> ProcessingResult<()> {
    processor.process_file(|record| {
        let sequence = record.seq();

        // Skip sequences shorter than k
        if sequence.len() < k {
            return Ok(());
        }

        // Extract and count k-mers
        for i in 0..=(sequence.len() - k) {
            let kmer_seq = &sequence[i..i + k];

            match encode_kmer_bytes(kmer_seq) {
                Ok(encoded_kmer) => {
                    let final_kmer = if canonical {
                        match canonical_kmer(encoded_kmer, k) {
                            Ok(canonical) => canonical,
                            Err(_) => continue, // Skip invalid k-mers
                        }
                    } else {
                        encoded_kmer
                    };

                    counter.increment(final_kmer).map_err(|e| {
                        KmerError::ProcessingError(format!("Failed to increment k-mer count: {}", e))
                    })?;
                },
                Err(_) => {
                    // Skip k-mers with invalid characters (N, etc.)
                    if verbose {
                        eprintln!("Warning: Skipping k-mer with invalid characters at position {} in sequence {}",
                                i, record.id());
                    }
                }
            }
        }

        Ok(())
    })
}

/// Output results in text format
fn output_text_format(
    counter: &Arc<KmerCounter>,
    output_path: &Path,
    quiet: bool,
    sort: bool,
) -> ProcessingResult<()> {
    use std::io::Write;

    let file = std::fs::File::create(output_path)
        .map_err(|e| KmerError::FileWriteError(format!("Failed to create output file: {}", e)))?;
    let mut writer = std::io::BufWriter::new(file);

    if !quiet {
        eprintln!("Writing results in text format...");
    }

    // Get all k-mers from the counter
    let mut kmers = counter.get_all_kmers();
    let total = kmers.len();

    // Sort k-mers if requested
    if sort {
        if !quiet {
            eprintln!("Sorting {} k-mers...", total);
        }
        kmers.sort_by(|(a, _), (b, _)| {
            // Decode both k-mers and compare sequences
            let seq_a = decode_kmer(*a, counter.get_kmer_length());
            let seq_b = decode_kmer(*b, counter.get_kmer_length());
            seq_a.cmp(&seq_b)
        });
    }

    for (idx, (kmer, count)) in kmers.into_iter().enumerate() {
        // Decode k-mer back to sequence
        let sequence = decode_kmer(kmer, counter.get_kmer_length());
        writeln!(writer, "{}\t{}", sequence, count)
            .map_err(|e| KmerError::FileWriteError(format!("Failed to write k-mer {}: {}", idx, e)))?;

        if !quiet && (idx + 1) % 100000 == 0 {
            eprintln!("Written {}/{} k-mers", idx + 1, total);
        }
    }

    if !quiet {
        eprintln!("Completed writing {} k-mers", total);
    }

    Ok(())
}

/// Output results in binary format
fn output_binary_format(
    counter: &Arc<KmerCounter>,
    output_path: &Path,
    quiet: bool,
    sort: bool,
) -> ProcessingResult<()> {
    use bincode;

    if !quiet {
        eprintln!("Writing results in binary format...");
    }

    let mut kmers = counter.get_all_kmers();
    let kmer_count = kmers.len();

    // Sort k-mers if requested
    if sort {
        if !quiet {
            eprintln!("Sorting {} k-mers...", kmer_count);
        }
        kmers.sort_by(|(a, _), (b, _)| {
            // Decode both k-mers and compare sequences
            let seq_a = decode_kmer(*a, counter.get_kmer_length());
            let seq_b = decode_kmer(*b, counter.get_kmer_length());
            seq_a.cmp(&seq_b)
        });
    }

    let file = std::fs::File::create(output_path)
        .map_err(|e| KmerError::FileWriteError(format!("Failed to create output file: {}", e)))?;

    // Serialize using bincode
    bincode::serialize_into(file, &(counter.get_kmer_length(), kmers))
        .map_err(|e| KmerError::FileWriteError(format!("Failed to serialize k-mers: {}", e)))?;

    if !quiet {
        eprintln!("Completed writing {} k-mers in binary format", kmer_count);
    }

    Ok(())
}

/// Decode a k-mer from encoded format back to DNA sequence
fn decode_kmer(kmer: u64, k: usize) -> String {
    let mut sequence = String::with_capacity(k);
    let mut encoded = kmer;

    for _ in 0..k {
        let base = encoded & 0b11;
        let char = match base {
            0 => 'A',
            1 => 'C',
            2 => 'G',
            3 => 'T',
            _ => 'N',
        };
        sequence.push(char);
        encoded >>= 2;
    }

    sequence.chars().rev().collect()
}