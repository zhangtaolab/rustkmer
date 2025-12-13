//! Count command implementation
//!
//! Implements the k-mer counting functionality.

use std::path::Path;
use std::sync::Arc;
use std::time::Instant;

use crate::cli::args::Args;
use crate::error::{KmerError, ProcessingResult};
use crate::hash::table::KmerCounter;
use crate::io::fasta::{FastaProcessor, validate_fasta_file};
use crate::io::fastq::{FastqProcessor, validate_fastq_file};
use crate::io::discovery::{FileDiscovery, DiscoveryConfig};
use crate::kmer::encoding::{encode_kmer_bytes_u128};
use crate::kmer::canonical::canonical_kmer_u128;
use crate::database::format::{DatabaseHeader, DATABASE_MAGIC, DATABASE_VERSION};

/// Execute the count command
pub fn execute_count(args: &Args) -> ProcessingResult<()> {
    match &args.command {
        crate::cli::args::Commands::Count {
            k,
            input,
            directory,
            select,
            recursive,
            no_recursive,
            output,
            canonical,
            size,
            format,
            quiet,
            verbose,
            sort,
            no_sort,
            min_count: _,
            max_count: _,
            show_warnings,
        } => {
            // Validate k-mer size (u128 supports k up to 64)
            if *k < 1 || *k > 64 {
                return Err(KmerError::InvalidKmerSize(*k as u32).into());
            }

            // Determine if we should sort the output
            let should_sort = if *no_sort {
                false
            } else {
                *sort
            };

            // Validate filtering parameters
            if let Err(errors) = args.command.validate_filtering() {
                for error in errors {
                    eprintln!("Error: {}", error);
                }
                return Err(KmerError::ProcessingError("Invalid filtering parameters".to_string()).into());
            }

            // Validate input parameters
            if let Err(errors) = args.command.validate_input() {
                for error in errors {
                    eprintln!("Error: {}", error);
                }
                return Err(KmerError::ProcessingError("Invalid input parameters".to_string()).into());
            }

            // Determine recursive mode
            let is_recursive = if *no_recursive {
                false
            } else {
                *recursive
            };

            // Handle directory mode vs file list mode
            let files_to_process = if let Some(dir_path) = directory {
                // Directory mode: discover files
                let config = DiscoveryConfig {
                    recursive: is_recursive,
                    ..Default::default()
                };
                let discovery = FileDiscovery::new(config);

                let dir_path_obj = Path::new(dir_path);
                let discovered_files = discovery.discover(dir_path_obj)
                    .map_err(|e| KmerError::ProcessingError(format!("Failed to discover files in directory: {}", e)))?;

                // For now, use all discovered files (default behavior)
                discovered_files.iter().map(|file_info| file_info.path.clone()).collect::<Vec<_>>()
            } else {
                // File list mode: use provided input files
                input.iter().map(|s| Path::new(s).to_path_buf()).collect()
            };

            if *verbose {
                eprintln!("rustkmer count starting...");
                eprintln!("K-mer size: {}", k);
                eprintln!("Canonical mode: {}", canonical);
                eprintln!("Processing mode: sequential");
                eprintln!("Hash table size: {}", size);

                if directory.is_some() {
                    eprintln!("Directory: {:?}", directory);
                    eprintln!("Recursive: {}", is_recursive);
                    eprintln!("Interactive selection: {}", select);
                    eprintln!("Files discovered: {}", files_to_process.len());
                } else {
                    eprintln!("Input files: {:?}", input);
                }

                if let Some(out) = output {
                    eprintln!("Output file: {}", out);
                }
            }

            // Create k-mer counter
            let counter = Arc::new(KmerCounter::new(
                *k,
                *canonical,
                *size,
                1, // num_threads: fixed to 1 for sequential processing
            )?);

            let start_time = Instant::now();

            // Process each file
            for (file_idx, file_path_obj) in files_to_process.iter().enumerate() {
                if !*quiet {
                    eprintln!("Processing file {}/{}: {}", file_idx + 1, files_to_process.len(), file_path_obj.display());
                }

                // Determine file format and process
                // Helper function to get file extension with support for compressed files
                let get_file_type = |path: &Path| -> Option<&'static str> {
                    let file_str = path.to_string_lossy().to_ascii_lowercase();

                    // Check for compressed files first
                    if file_str.ends_with(".fa.gz") || file_str.ends_with(".fasta.gz") ||
                       file_str.ends_with(".fna.gz") || file_str.ends_with(".ffn.gz") {
                        return Some("fasta");
                    }
                    if file_str.ends_with(".fq.gz") || file_str.ends_with(".fastq.gz") {
                        return Some("fastq");
                    }

                    // Check for uncompressed files
                    let extension = path.extension()
                        .and_then(|ext| ext.to_str())
                        .map(|s| s.to_ascii_lowercase());

                    match extension.as_deref() {
                        Some("fa") | Some("fasta") | Some("fna") | Some("ffn") => Some("fasta"),
                        Some("fq") | Some("fastq") => Some("fastq"),
                        _ => None,
                    }
                };

                let result = match get_file_type(file_path_obj) {
                    Some("fasta") => {
                        // Validate FASTA file
                        validate_fasta_file(file_path_obj)?;

                        // Process FASTA file
                        let processor = FastaProcessor::new(file_path_obj);
                        process_fasta_file(&processor, &counter, *k, *canonical, *quiet, *verbose, *show_warnings)
                    },
                    Some("fastq") => {
                        // Validate FASTQ file
                        validate_fastq_file(file_path_obj)?;

                        // Process FASTQ file
                        let processor = FastqProcessor::new(file_path_obj);
                        if *verbose {
                            eprintln!("  FASTQ file detected (compression: {})", processor.compression_type().name());
                        }
                        process_fastq_file(&processor, &counter, *k, *canonical, *quiet, *verbose, *show_warnings)
                    },
                    _ => {
                        // Try to auto-detect format
                        let file_path_str = file_path_obj.to_string_lossy();
                        if file_path_str.to_ascii_lowercase().contains("fastq") ||
                           file_path_str.to_ascii_lowercase().contains("fq") {
                            let processor = FastqProcessor::new(file_path_obj);
                            process_fastq_file(&processor, &counter, *k, *canonical, *quiet, *verbose, *show_warnings)
                        } else {
                            // Default to FASTA
                            let processor = FastaProcessor::new(file_path_obj);
                            process_fasta_file(&processor, &counter, *k, *canonical, *quiet, *verbose, *show_warnings)
                        }
                    }
                };

                if let Err(e) = result {
                    return Err(KmerError::ProcessingError(format!(
                        "Failed to process file {}: {}", file_path_obj.display(), e
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

            // Create filter if filtering parameters are specified
            let filter = args.command.create_count_filter();

            // Generate output
            if let Some(output_file) = output {
                let output_path = Path::new(output_file);

                match format.as_str() {
                    "text" => {
                        output_text_format(&counter, output_path, *quiet, should_sort, &filter)?;
                    },
                    "binary" | _ => {
                        output_binary_format(&counter, output_path, *quiet, should_sort, &filter)?;
                    },
                }
            }

            let total_time = start_time.elapsed();
            let final_stats = counter.get_stats();
            let filtering_stats = counter.get_filtering_stats(&filter);

            if !*quiet {
                eprintln!("Counting completed successfully!");
                eprintln!("Total k-mers: {}", final_stats.total_kmers);
                eprintln!("Unique k-mers: {}", final_stats.unique_kmers);

                // Report filtering statistics if filtering was applied
                if filter.as_ref().is_some_and(|f| f.min_count.is_some() || f.max_count.is_some()) {
                    eprintln!("K-mers kept after filtering: {}", filtering_stats.kept_after);
                    eprintln!("K-mers filtered out: {}", filtering_stats.filtered_out);
                    if filtering_stats.unique_before > 0 {
                        eprintln!("Filtering retention: {:.1}%", filtering_stats.kept_percentage());
                    }
                }

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
    _quiet: bool,
    _verbose: bool,
    show_warnings: bool,
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

            match encode_kmer_bytes_u128(kmer_seq) {
                Ok(encoded_kmer) => {
                    let final_kmer = if canonical {
                        match canonical_kmer_u128(encoded_kmer, k) {
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
                    if show_warnings {
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
    _quiet: bool,
    _verbose: bool,
    show_warnings: bool,
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

            match encode_kmer_bytes_u128(kmer_seq) {
                Ok(encoded_kmer) => {
                    let final_kmer = if canonical {
                        match canonical_kmer_u128(encoded_kmer, k) {
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
                    if show_warnings {
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
    filter: &Option<crate::hash::CountFilter>,
) -> ProcessingResult<()> {
    use std::io::Write;

    let file = std::fs::File::create(output_path)
        .map_err(|e| KmerError::FileWriteError(format!("Failed to create output file: {}", e)))?;
    let mut writer = std::io::BufWriter::new(file);

    if !quiet {
        eprintln!("Writing results in text format...");
    }

    // Get k-mers from the counter (filtered if applicable)
    let mut kmers = counter.get_filtered_kmers(filter);
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

/// Output results in RKDB format
fn output_binary_format(
    counter: &Arc<KmerCounter>,
    output_path: &Path,
    quiet: bool,
    sort: bool,
    filter: &Option<crate::hash::CountFilter>,
) -> ProcessingResult<()> {
    use byteorder::{LittleEndian, WriteBytesExt};

    if !quiet {
        eprintln!("Writing results in RKDB database format...");
    }

    let mut kmers = counter.get_filtered_kmers(filter);
    let kmer_count = kmers.len();

    // Sort k-mers if requested (required for binary search)
    if sort {
        if !quiet {
            eprintln!("Sorting {} k-mers...", kmer_count);
        }
        kmers.sort_by(|(a, _), (b, _)| a.cmp(b));
    }

    let file = std::fs::File::create(output_path)
        .map_err(|e| KmerError::FileWriteError(format!("Failed to create output file: {}", e)))?;
    let mut writer = std::io::BufWriter::new(file);

    // Write RKDB database header with correct data offset
    // Header size = 4 (magic) + 2 (version) + 1 (kmer_size) + 3 (padding) + 8 (total_kmers) + 1 (flags) + 7 (padding) + 8 (data_offset) + 8 (index_offset) = 42 bytes
    let header = DatabaseHeader {
        magic: *DATABASE_MAGIC,
        version: DATABASE_VERSION,
        kmer_size: counter.get_kmer_length() as u8,
        total_kmers: kmer_count as u64,
        sorted: sort,
        data_offset: 42, // Fixed header size for RKDB format
        index_offset: 0,
        canonical: counter.canonical_mode(),
        unique_kmers: kmer_count as u64,  // Same as total_kmers for now
        file_size: 42 + (kmer_count as u64 * 12),  // Header + k-mer entries (8+4 bytes each)
    };

    if !quiet {
        eprintln!("DEBUG: Writing header with data_offset: {}", header.data_offset);
    }

    // Write header
    header.write_to(&mut writer)
        .map_err(|e| KmerError::FileWriteError(format!("Failed to write database header: {}", e)))?;

    // Write k-mer entries
    for (kmer, count) in kmers {
        writer.write_u128::<LittleEndian>(kmer)?;
        writer.write_u32::<LittleEndian>(count)?;
    }

    if !quiet {
        eprintln!("Completed writing {} k-mers in RKDB format", kmer_count);
    }

    Ok(())
}

/// Decode a k-mer from encoded format back to DNA sequence
fn decode_kmer(kmer: u128, k: usize) -> String {
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