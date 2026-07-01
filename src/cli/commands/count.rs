//! Count command implementation
//!
//! Implements the k-mer counting functionality.

use std::path::Path;
use std::sync::Arc;
use std::time::Instant;

use crate::cli::args::Args;
use crate::database::format::{DatabaseHeader, KmerEntry, DATABASE_MAGIC, DATABASE_VERSION};
use crate::error::{KmerError, ProcessingResult};
use crate::hash::table::KmerCounter;
use crate::io::discovery::{DiscoveryConfig, FileDiscovery};
use crate::io::fasta::{validate_fasta_file, FastaProcessor};
use crate::io::fastq::{validate_fastq_file, FastqProcessor};
use crate::kmer::canonical::canonical_kmer_u128;
use crate::kmer::encoding::encode_kmer_bytes_u128;

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
            threads,
            min_count: _,
            max_count: _,
            show_warnings,
        } => {
            // Validate k-mer size (u128 supports k up to 64)
            if *k < 1 || *k > 64 {
                return Err(KmerError::InvalidKmerSize(*k as u32).into());
            }

            // Determine if we should sort the output
            let should_sort = if *no_sort { false } else { *sort };

            // Validate filtering parameters
            if let Err(errors) = args.command.validate_filtering() {
                for error in errors {
                    eprintln!("Error: {}", error);
                }
                return Err(
                    KmerError::ProcessingError("Invalid filtering parameters".to_string()).into(),
                );
            }

            // Validate input parameters (includes --threads >= 1 check, D-07)
            if let Err(errors) = args.command.validate_input() {
                for error in errors {
                    eprintln!("Error: {}", error);
                }
                return Err(
                    KmerError::ProcessingError("Invalid input parameters".to_string()).into(),
                );
            }

            // Resolve thread count via the D-07 precedence chain and
            // initialize the global rayon pool ONCE, before the file loop.
            // build_global returns Err on a second call (Pitfall 3: tests,
            // embedded use, or a count→merge pipeline may already have
            // initialized the pool) — the `let _ =` deliberately discards
            // the Result. Do NOT unwrap/expect or propagate via ? here.
            let resolved_threads = resolve_thread_count(*threads);
            let _ = rayon::ThreadPoolBuilder::new()
                .num_threads(resolved_threads)
                .build_global();

            // Determine recursive mode
            let is_recursive = if *no_recursive { false } else { *recursive };

            // Handle directory mode vs file list mode
            let files_to_process = if let Some(dir_path) = directory {
                // Directory mode: discover files
                let config = DiscoveryConfig {
                    recursive: is_recursive,
                    ..Default::default()
                };
                let discovery = FileDiscovery::new(config);

                let dir_path_obj = Path::new(dir_path);
                let discovered_files = discovery.discover(dir_path_obj).map_err(|e| {
                    KmerError::ProcessingError(format!(
                        "Failed to discover files in directory: {}",
                        e
                    ))
                })?;

                // For now, use all discovered files (default behavior)
                discovered_files
                    .iter()
                    .map(|file_info| file_info.path.clone())
                    .collect::<Vec<_>>()
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
                eprintln!("Threads: {}", resolved_threads);

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

            // Create k-mer counter. The 4th param is a stats/reporting slot
            // (table.rs `_num_threads`); the real pool config is the
            // build_global call above (per PATTERNS.md note on table.rs:44).
            let counter = Arc::new(KmerCounter::new(
                *k,
                *canonical,
                *size,
                resolved_threads,
            )?);

            let start_time = Instant::now();

            // Process each file
            for (file_idx, file_path_obj) in files_to_process.iter().enumerate() {
                if !*quiet {
                    eprintln!(
                        "Processing file {}/{}: {}",
                        file_idx + 1,
                        files_to_process.len(),
                        file_path_obj.display()
                    );
                }

                // Determine file format and process
                // Helper function to get file extension with support for compressed files
                let get_file_type = |path: &Path| -> Option<&'static str> {
                    let file_str = path.to_string_lossy().to_ascii_lowercase();

                    // Check for compressed files first
                    if file_str.ends_with(".fa.gz")
                        || file_str.ends_with(".fasta.gz")
                        || file_str.ends_with(".fna.gz")
                        || file_str.ends_with(".ffn.gz")
                    {
                        return Some("fasta");
                    }
                    if file_str.ends_with(".fq.gz") || file_str.ends_with(".fastq.gz") {
                        return Some("fastq");
                    }

                    // Check for uncompressed files
                    let extension = path
                        .extension()
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
                        process_fasta_file(
                            &processor,
                            &counter,
                            *k,
                            *canonical,
                            *quiet,
                            *verbose,
                            *show_warnings,
                        )
                    }
                    Some("fastq") => {
                        // Validate FASTQ file
                        validate_fastq_file(file_path_obj)?;

                        // Process FASTQ file
                        let processor = FastqProcessor::new(file_path_obj);
                        if *verbose {
                            eprintln!(
                                "  FASTQ file detected (compression: {})",
                                processor.compression_type().name()
                            );
                        }
                        process_fastq_file(
                            &processor,
                            &counter,
                            *k,
                            *canonical,
                            *quiet,
                            *verbose,
                            *show_warnings,
                        )
                    }
                    _ => {
                        // Try to auto-detect format
                        let file_path_str = file_path_obj.to_string_lossy();
                        if file_path_str.to_ascii_lowercase().contains("fastq")
                            || file_path_str.to_ascii_lowercase().contains("fq")
                        {
                            let processor = FastqProcessor::new(file_path_obj);
                            process_fastq_file(
                                &processor,
                                &counter,
                                *k,
                                *canonical,
                                *quiet,
                                *verbose,
                                *show_warnings,
                            )
                        } else {
                            // Default to FASTA
                            let processor = FastaProcessor::new(file_path_obj);
                            process_fasta_file(
                                &processor,
                                &counter,
                                *k,
                                *canonical,
                                *quiet,
                                *verbose,
                                *show_warnings,
                            )
                        }
                    }
                };

                if let Err(e) = result {
                    return Err(KmerError::ProcessingError(format!(
                        "Failed to process file {}: {}",
                        file_path_obj.display(),
                        e
                    ))
                    .into());
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
                    }
                    _ => {
                        output_binary_format(&counter, output_path, *quiet, should_sort, &filter)?;
                    }
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
                if filter
                    .as_ref()
                    .is_some_and(|f| f.min_count.is_some() || f.max_count.is_some())
                {
                    eprintln!(
                        "K-mers kept after filtering: {}",
                        filtering_stats.kept_after
                    );
                    eprintln!("K-mers filtered out: {}", filtering_stats.filtered_out);
                    if filtering_stats.unique_before > 0 {
                        eprintln!(
                            "Filtering retention: {:.1}%",
                            filtering_stats.kept_percentage()
                        );
                    }
                }

                eprintln!("Total time: {:.2} seconds", total_time.as_secs_f64());

                if let Some(output_file) = output {
                    eprintln!("Results saved to: {}", output_file);
                }
            }

            Ok(())
        }
        _ => {
            Err(KmerError::ProcessingError("Invalid command for execute_count".to_string()).into())
        }
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
        writeln!(writer, "{}\t{}", sequence, count).map_err(|e| {
            KmerError::FileWriteError(format!("Failed to write k-mer {}: {}", idx, e))
        })?;

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
        kmers.sort_by_key(|(a, _)| *a);
    }

    let file = std::fs::File::create(output_path)
        .map_err(|e| KmerError::FileWriteError(format!("Failed to create output file: {}", e)))?;
    let mut writer = std::io::BufWriter::new(file);

    // Write RKDB database header with correct data offset
    // Header size = 4 (magic) + 2 (version) + 1 (kmer_size) + 3 (padding) + 8 (total_kmers) + 1 (flags) + 7 (padding) + 8 (data_offset) + 8 (index_offset) = 42 bytes
    //
    // `file_size` is left at 0 to match the canonical `RKDatabase::from_kmer_pairs`
    // header literal (format.rs:~467). The field is in-memory only and is NOT
    // serialized by `DatabaseHeader::write_to` (RESEARCH.md §4 verified: only
    // magic/version/kmer_size/total_kmers/flags/data_offset/index_offset cross
    // the wire). The golden sha256 (plan 01-03 Task 1) proves byte-identity
    // between this delegated path and the canonical path.
    let header = DatabaseHeader {
        magic: *DATABASE_MAGIC,
        version: DATABASE_VERSION,
        kmer_size: counter.get_kmer_length() as u8,
        total_kmers: kmer_count as u64,
        sorted: sort,
        data_offset: 42, // Fixed header size for RKDB format
        index_offset: 0,
        canonical: counter.canonical_mode(),
        unique_kmers: kmer_count as u64, // Same as total_kmers for now
        file_size: 0, // In-memory only; not serialized (matches canonical writer)
    };

    if !quiet {
        eprintln!(
            "DEBUG: Writing header with data_offset: {}",
            header.data_offset
        );
    }

    // Write header — delegates to the canonical DatabaseHeader::write_to
    // (format.rs:81), the single source of truth for the .rkdb header layout.
    header.write_to(&mut writer).map_err(|e| {
        KmerError::FileWriteError(format!("Failed to write database header: {}", e))
    })?;

    // Write k-mer entries — delegates to the canonical KmerEntry::write_to
    // (format.rs:201: u128 LE kmer + u32 LE count). This replaces the previous
    // inline raw-byte entry loop so there is exactly one .rkdb entry writer in
    // the codebase. Byte-identity is verified by tests/golden_tests.rs (P3).
    for (kmer, count) in kmers {
        KmerEntry::new(kmer, count).write_to(&mut writer)?;
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

/// Pure precedence resolver for the D-07 thread-count chain.
///
/// Implements the precedence `--threads > RUSTKMER_THREADS > RAYON_NUM_THREADS
/// > num_cpus` without touching the process environment, so it is unit-testable
/// without env-var races. The env-reading wrapper [`resolve_thread_count`]
/// supplies the `Option`/`usize` slots from `std::env::var` and `num_cpus::get`.
///
/// # Arguments
/// * `args_threads` - value of the `--threads` CLI flag (`None` if unset).
/// * `rustkmer_threads` - parsed value of `RUSTKMER_THREADS`, if present and `>= 1`.
/// * `rayon_num_threads` - parsed value of `RAYON_NUM_THREADS`, if present and `>= 1`.
/// * `num_cpus` - the all-cores fallback (`num_cpus::get()` / `rayon::current_num_threads()`).
///
/// # Returns
/// The resolved thread count (`>= 1`).
fn resolve_thread_count_from(
    args_threads: Option<usize>,
    rustkmer_threads: Option<usize>,
    rayon_num_threads: Option<usize>,
    num_cpus: usize,
) -> usize {
    if let Some(t) = args_threads.filter(|&n| n >= 1) {
        return t;
    }
    if let Some(t) = rustkmer_threads.filter(|&n| n >= 1) {
        return t;
    }
    if let Some(t) = rayon_num_threads.filter(|&n| n >= 1) {
        return t;
    }
    // Guard against `num_cpus::get()` returning 0 on unsupported platforms
    // (documented edge case in the num_cpus docs); fall back to 1 so the
    // pool always has at least one worker.
    num_cpus.max(1)
}

/// Resolve the rayon pool thread count from the D-07 precedence chain,
/// reading the environment for the `RUSTKMER_THREADS` and `RAYON_NUM_THREADS`
/// tiers. Thin wrapper over [`resolve_thread_count_from`].
///
/// Precedence (highest wins): `--threads` > `RUSTKMER_THREADS` >
/// `RAYON_NUM_THREADS` > all cores. Malformed env values parse to `None`
/// (the `filter` inside the pure resolver drops `< 1`) and fall through to
/// the next tier rather than panicking — this is the T-02-01 mitigation.
///
/// NOTE: `num_cpus` is a transitive dep via rayon (RESEARCH Assumption A1).
/// We use `rayon::current_num_threads()` for the fallback because it is
/// always reachable without a direct `num_cpus` dep and stays consistent
/// with whatever pool rayon actually built.
fn resolve_thread_count(args_threads: Option<usize>) -> usize {
    resolve_thread_count_from(
        args_threads,
        std::env::var("RUSTKMER_THREADS")
            .ok()
            .and_then(|v| v.parse::<usize>().ok()),
        std::env::var("RAYON_NUM_THREADS")
            .ok()
            .and_then(|v| v.parse::<usize>().ok()),
        rayon::current_num_threads(),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    /// `--threads` wins over everything (D-07 precedence).
    #[test]
    fn test_args_threads_wins() {
        assert_eq!(
            resolve_thread_count_from(Some(4), Some(8), Some(6), 12),
            4,
            "--threads must take precedence over env vars and num_cpus"
        );
    }

    /// `RUSTKMER_THREADS` wins when `--threads` is unset.
    #[test]
    fn test_rustkmer_threads_wins_when_args_unset() {
        assert_eq!(
            resolve_thread_count_from(None, Some(8), Some(6), 12),
            8,
            "RUSTKMER_THREADS must win over RAYON_NUM_THREADS and num_cpus"
        );
    }

    /// `RAYON_NUM_THREADS` is the lowest-precedence env tier (merge users unaffected).
    #[test]
    fn test_rayon_num_threads_fallback() {
        assert_eq!(
            resolve_thread_count_from(None, None, Some(6), 12),
            6,
            "RAYON_NUM_THREADS must be honored when both higher tiers are unset"
        );
    }

    /// All-cores fallback (D-06) when nothing is set.
    #[test]
    fn test_num_cpus_fallback() {
        assert_eq!(
            resolve_thread_count_from(None, None, None, 12),
            12,
            "default must be num_cpus when no flag/env is set"
        );
    }

    /// A `--threads 0` (invalid) must NOT short-circuit precedence — it falls
    /// through to the next tier. Validation rejects `--threads < 1` upstream,
    /// but the resolver is defensive: it filters via `n >= 1`.
    #[test]
    fn test_args_threads_zero_falls_through() {
        assert_eq!(
            resolve_thread_count_from(Some(0), Some(8), None, 12),
            8,
            "--threads 0 must fall through to the next precedence tier, not panic"
        );
    }

    /// Malformed env tiers (represented as `None` after parse failure upstream)
    /// fall through cleanly to num_cpus.
    #[test]
    fn test_all_envs_none_uses_num_cpus() {
        assert_eq!(resolve_thread_count_from(None, None, None, 16), 16);
    }

    /// `num_cpus::get()` can return 0 on unsupported platforms — the resolver
    /// must clamp to 1 so rayon always spawns at least one worker.
    #[test]
    fn test_num_cpus_zero_clamped_to_one() {
        assert_eq!(
            resolve_thread_count_from(None, None, None, 0),
            1,
            "num_cpus=0 (unsupported platform) must clamp to 1"
        );
    }
}
