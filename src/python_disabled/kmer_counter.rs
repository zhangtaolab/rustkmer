//! Python bindings for KmerCounter

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;
use rayon::prelude::*;
use std::fs::File;
use std::io::{BufRead, BufReader, Write, BufWriter};
use flate2::read::GzDecoder;
use byteorder::{LittleEndian, WriteBytesExt};

// Import our modules
use super::exceptions::*;

// Import CLI database format modules for compatibility
use crate::core::database::format::{DatabaseHeader, DATABASE_MAGIC, DATABASE_VERSION};

// Import CLI k-mer operations for complete compatibility
use crate::core::kmer::{encode_kmer as cli_encode_kmer, decode_kmer, canonical_kmer};

/// Wrapper function to convert CLI KmerError to String for Python API
fn encode_kmer(kmer: &str) -> Result<u64, String> {
    cli_encode_kmer(kmer).map_err(|e| format!("Encoding error: {}", e))
}

/// Internal k-mer counter backend
#[derive(Debug, Clone)]
struct KmerCounterBackend {
    counts: HashMap<u64, u64>,  // Packed k-mer -> count
    k: usize,
    canonical: bool,
    total_sequences: u64,
}

impl KmerCounterBackend {
    fn new(k: usize, canonical: bool) -> Self {
        Self {
            counts: HashMap::new(),
            k,
            canonical,
            total_sequences: 0,
        }
    }

    fn count_sequence(&mut self, sequence: &str) -> Result<(), String> {
        // Normalize sequence to uppercase
        let normalized = sequence.to_ascii_uppercase();

        // Extract k-mers using CLI's extract_kmers function for consistency
        let encoded_kmers = match crate::core::kmer::operations::extract_kmers(&normalized, self.k) {
            Ok(kmers) => kmers,
            Err(e) => return Err(format!("Failed to extract k-mers: {}", e)),
        };

        // Apply canonical transformation if needed using CLI's function
        let final_kmers = if self.canonical {
            encoded_kmers.into_iter()
                .map(|encoded| {
                    canonical_kmer(encoded, self.k)
                        .map_err(|e| format!("Canonical transformation error: {}", e))
                })
                .collect::<Result<Vec<_>, _>>()?
        } else {
            encoded_kmers
        };

        // Count the k-mers
        for encoded in final_kmers {
            *self.counts.entry(encoded).or_insert(0) += 1;
        }

        self.total_sequences += 1;
        Ok(())
    }

    fn get_count(&self, kmer_str: &str) -> Result<u64, String> {
        if kmer_str.len() != self.k {
            return Err(format!("K-mer length mismatch: expected {}, got {}", self.k, kmer_str.len()));
        }

        // Encode k-mer using CLI's function
        let encoded = encode_kmer(kmer_str)
            .map_err(|e| format!("Invalid k-mer: {}", e))?;

        // Apply canonical transformation if needed using CLI's function
        let final_encoded = if self.canonical {
            canonical_kmer(encoded, self.k)
                .map_err(|e| format!("Canonical transformation error: {}", e))?
        } else {
            encoded
        };

        Ok(self.counts.get(&final_encoded).copied().unwrap_or(0))
    }

    fn get_all_counts(&self) -> HashMap<String, u64> {
        self.counts
            .iter()
            .map(|(&kmer, &count)| {
                let kmer_str = decode_kmer(kmer, self.k);
                (kmer_str, count)
            })
            .collect()
    }

    fn get_top_kmers(&self, n: usize) -> Vec<(String, u64)> {
        let mut sorted: Vec<_> = self.counts
            .iter()
            .map(|(&kmer, &count)| {
                let kmer_str = decode_kmer(kmer, self.k);
                (kmer_str, count)
            })
            .collect();

        // Sort by count descending, then by k-mer lexicographically for ties
        sorted.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));
        sorted.truncate(n);
        sorted
    }

    fn filter_by_count(&self, min_count: u64, max_count: Option<u64>) -> HashMap<String, u64> {
        self.counts
            .iter()
            .filter(|(_, &count)| {
                count >= min_count && max_count.map_or(true, |max| count <= max)
            })
            .map(|(&kmer, &count)| {
                let kmer_str = decode_kmer(kmer, self.k);
                (kmer_str, count)
            })
            .collect()
    }

    fn get_stats(&self) -> CounterStats {
        let total_kmers = self.counts.len();
        let total_count: u64 = self.counts.values().sum();

        let mut counts: Vec<u64> = self.counts.values().copied().collect();
        counts.sort_unstable();

        let average_count = if total_kmers > 0 {
            total_count as f64 / total_kmers as f64
        } else {
            0.0
        };

        let median_count = if !counts.is_empty() {
            if counts.len() % 2 == 1 {
                counts[counts.len() / 2] as f64
            } else {
                (counts[counts.len() / 2 - 1] + counts[counts.len() / 2]) as f64 / 2.0
            }
        } else {
            0.0
        };

        let max_count = counts.last().copied().unwrap_or(0);

        CounterStats {
            total_kmers,
            total_count,
            average_count,
            median_count,
            max_count,
        }
    }

    fn merge(&mut self, other: &KmerCounterBackend) -> Result<(), String> {
        if self.k != other.k {
            return Err(format!("Cannot merge counters with different k-mer sizes: {} vs {}", self.k, other.k));
        }
        if self.canonical != other.canonical {
            return Err(format!("Cannot merge counters with different canonical modes: {} vs {}", self.canonical, other.canonical));
        }

        for (&kmer, &count) in &other.counts {
            *self.counts.entry(kmer).or_insert(0) += count;
        }
        self.total_sequences += other.total_sequences;
        Ok(())
    }
}

/// Statistics for k-mer counting operations
#[pyclass(name = "CounterStats")]
#[derive(Debug, Clone)]
pub struct CounterStats {
    #[pyo3(get)]
    total_kmers: usize,
    #[pyo3(get)]
    total_count: u64,
    #[pyo3(get)]
    average_count: f64,
    #[pyo3(get)]
    median_count: f64,
    #[pyo3(get)]
    max_count: u64,
}

/// Python wrapper for RustKmer KmerCounter
#[pyclass(name = "KmerCounter")]
pub struct PyKmerCounter {
    backend: Arc<RwLock<KmerCounterBackend>>,
}

#[pymethods]
impl PyKmerCounter {
    /// Create a new KmerCounter with specified parameters
    #[new]
    #[pyo3(signature = (k, canonical=false, threads=None))]
    fn new(k: usize, canonical: bool, threads: Option<usize>) -> PyResult<Self> {
        // Validate k-mer size
        if k == 0 || k > 127 {
            return Err(KmerError::new_err(
                format!("K-mer size must be between 1 and 127, got {}", k)
            ));
        }

        // Validate thread count
        if let Some(t) = threads {
            if t == 0 {
                return Err(KmerError::new_err("Thread count must be at least 1"));
            }
            // In this implementation, we don't actually use threads yet,
            // but we validate the parameter for future compatibility
        }

        let backend = KmerCounterBackend::new(k, canonical);
        Ok(PyKmerCounter {
            backend: Arc::new(RwLock::new(backend)),
        })
    }

    /// Get the k-mer size
    fn get_k(&self) -> usize {
        self.backend.read().k
    }

    /// Check if counting canonical k-mers
    fn is_canonical(&self) -> bool {
        self.backend.read().canonical
    }

    /// Count k-mers in a DNA sequence string
    #[pyo3(signature = (sequence,))]
    fn count_sequence(&self, sequence: &str) -> PyResult<HashMap<String, u64>> {
        // Validate sequence
        if sequence.is_empty() {
            return Ok(HashMap::new());
        }

        let mut backend = self.backend.write();

        // Create a copy of current counts to avoid modifying during counting
        let initial_counts = backend.counts.clone();

        if let Err(e) = backend.count_sequence(sequence) {
            // Restore original counts on error
            backend.counts = initial_counts;
            return Err(SequenceError::new_err(format!("Failed to count sequence: {}", e)));
        }

        // Return only the newly added k-mers and their counts
        let new_counts: HashMap<String, u64> = backend.counts
            .iter()
            .filter(|(&kmer, _)| !initial_counts.contains_key(&kmer))
            .map(|(&kmer, &count)| {
                let kmer_str = decode_kmer(kmer, backend.k);
                (kmer_str, count)
            })
            .collect();

        Ok(new_counts)
    }

    /// Process a FASTA/FASTQ file for k-mer counting
    #[pyo3(signature = (file_path, file_format="auto"))]
    fn count_file(&self, file_path: &str, file_format: &str) -> PyResult<HashMap<String, u64>> {
        #[cfg(feature = "profiling")]
        let _timer = rustkmer::core::monitoring::start_timer("kmer_counting_file");

        use std::fs::File;
        use std::io::{BufRead, BufReader};
        use std::path::Path;

        // Validate file exists
        if !Path::new(file_path).exists() {
            return Err(SequenceError::new_err(format!("File not found: {}", file_path)));
        }

        // Determine file format
        let format = if file_format == "auto" {
            let file_path_lower = file_path.to_lowercase();
            if file_path_lower.ends_with(".fa") || file_path_lower.ends_with(".fasta") || file_path_lower.ends_with(".fna") ||
               file_path_lower.ends_with(".fa.gz") || file_path_lower.ends_with(".fasta.gz") || file_path_lower.ends_with(".fna.gz") {
                "fasta"
            } else if file_path_lower.ends_with(".fq") || file_path_lower.ends_with(".fastq") ||
                      file_path_lower.ends_with(".fq.gz") || file_path_lower.ends_with(".fastq.gz") {
                "fastq"
            } else {
                return Err(SequenceError::new_err(format!("Cannot determine file format for: {}", file_path)));
            }
        } else {
            file_format
        };

        let file = File::open(file_path)
            .map_err(|e| SequenceError::new_err(format!("Failed to open file '{}': {}", file_path, e)))?;

        // Check if file is compressed and create appropriate reader
        let is_compressed = file_path.to_lowercase().ends_with(".gz");
        let reader: Box<dyn BufRead> = if is_compressed {
            let decoder = GzDecoder::new(file);
            Box::new(BufReader::new(decoder))
        } else {
            Box::new(BufReader::new(file))
        };
        let mut backend = self.backend.write();
        let mut sequences_processed = 0;
        let mut kmers_processed = 0u64;

        match format {
            "fasta" => {
                let mut current_sequence = String::new();
                let mut in_sequence = false;

                for line in reader.lines() {
                    let line = line.map_err(|e| SequenceError::new_err(format!("Failed to read line: {}", e)))?;

                    if line.starts_with('>') {
                        // Process previous sequence if exists
                        if in_sequence && !current_sequence.is_empty() {
                            let seq_len = current_sequence.len();
                            if let Err(e) = backend.count_sequence(&current_sequence) {
                                return Err(SequenceError::new_err(format!("Failed to count sequence: {}", e)));
                            }
                            sequences_processed += 1;
                            if seq_len >= backend.k {
                                kmers_processed += (seq_len - backend.k + 1) as u64;
                            }
                        }
                        current_sequence.clear();
                        in_sequence = true;
                    } else if in_sequence {
                        current_sequence.push_str(&line.trim());
                    }
                }

                // Process last sequence
                if in_sequence && !current_sequence.is_empty() {
                    let seq_len = current_sequence.len();
                    if let Err(e) = backend.count_sequence(&current_sequence) {
                        return Err(SequenceError::new_err(format!("Failed to count sequence: {}", e)));
                    }
                    sequences_processed += 1;
                    if seq_len >= backend.k {
                        kmers_processed += (seq_len - backend.k + 1) as u64;
                    }
                }
            }
            "fastq" => {
                let mut lines = reader.lines();
                while let (Some(header_result), Some(sequence_result), Some(plus_result), Some(quality_result)) = (
                    lines.next(),
                    lines.next(),
                    lines.next(),
                    lines.next()
                ) {
                    let header_line = header_result.map_err(|e| SequenceError::new_err(format!("Failed to read FASTQ header: {}", e)))?;
                    let sequence_line = sequence_result.map_err(|e| SequenceError::new_err(format!("Failed to read FASTQ sequence: {}", e)))?;
                    let _plus_line = plus_result.map_err(|e| SequenceError::new_err(format!("Failed to read FASTQ plus line: {}", e)))?;
                    let _quality_line = quality_result.map_err(|e| SequenceError::new_err(format!("Failed to read FASTQ quality line: {}", e)))?;

                    if !header_line.starts_with('@') {
                        return Err(SequenceError::new_err("Invalid FASTQ format: expected header starting with '@'"));
                    }
                    if !_plus_line.starts_with('+') {
                        return Err(SequenceError::new_err("Invalid FASTQ format: expected plus line starting with '+'"));
                    }

                    // Count the sequence
                    let seq_len = sequence_line.trim().len();
                    if let Err(e) = backend.count_sequence(&sequence_line.trim()) {
                        return Err(SequenceError::new_err(format!("Failed to count sequence: {}", e)));
                    }
                    sequences_processed += 1;
                    if seq_len >= backend.k {
                        kmers_processed += (seq_len - backend.k + 1) as u64;
                    }

                    // Verify sequence and quality length match
                    if sequence_line.len() != _quality_line.len() {
                        return Err(SequenceError::new_err("Invalid FASTQ format: sequence and quality line lengths don't match"));
                    }
                }
            }
            _ => {
                return Err(SequenceError::new_err(format!("Unsupported file format: {}", format)));
            }
        }

        // Record custom metrics
        #[cfg(feature = "profiling")]
        {
            rustkmer::core::monitoring::record_metric("kmer_counting_file", "sequences_processed", sequences_processed as f64);
            rustkmer::core::monitoring::record_metric("kmer_counting_file", "kmers_processed", kmers_processed as f64);
            rustkmer::core::monitoring::record_metric("kmer_counting_file", "unique_kmers", backend.counts.len() as f64);
        }

        // Return all counts from the file
        Ok(backend.get_all_counts())
    }

    /// Get count for a specific k-mer
    fn get_kmer_count(&self, kmer: &str) -> PyResult<u64> {
        let backend = self.backend.read();

        match backend.get_count(kmer) {
            Ok(count) => Ok(count),
            Err(e) => Err(KmerError::new_err(e)),
        }
    }

    /// Get count for a specific k-mer (alias for get_kmer_count)
    fn get_count(&self, kmer: &str) -> PyResult<u64> {
        self.get_kmer_count(kmer)
    }

    /// Get all k-mer counts as a dictionary
    fn get_all_counts(&self) -> PyResult<HashMap<String, u64>> {
        Ok(self.backend.read().get_all_counts())
    }

    /// Get top N most frequent k-mers
    #[pyo3(signature = (n,))]
    fn get_top_kmers(&self, n: usize) -> PyResult<Vec<(String, u64)>> {
        if n == 0 {
            return Err(KmerError::new_err("n must be at least 1"));
        }

        Ok(self.backend.read().get_top_kmers(n))
    }

    /// Filter k-mers by count range
    #[pyo3(signature = (min_count, max_count=None))]
    fn filter_by_count(&self, min_count: u64, max_count: Option<u64>) -> PyResult<HashMap<String, u64>> {
        if min_count < 0 {
            return Err(KmerError::new_err("min_count must be non-negative"));
        }

        Ok(self.backend.read().filter_by_count(min_count, max_count))
    }

    /// Merge another KmerCounter into this one
    fn merge(&self, other_counter: &PyKmerCounter) -> PyResult<()> {
        let mut self_backend = self.backend.write();
        let other_backend = other_counter.backend.read();

        match self_backend.merge(&other_backend) {
            Ok(()) => Ok(()),
            Err(e) => Err(KmerError::new_err(e)),
        }
    }

    /// Get statistics for this counter
    fn get_stats(&self) -> PyResult<CounterStats> {
        Ok(self.backend.read().get_stats())
    }

    /// Reset the counter (clear all counts)
    fn reset(&self) -> PyResult<()> {
        let mut backend = self.backend.write();
        let k = backend.k;
        let canonical = backend.canonical;
        *backend = KmerCounterBackend::new(k, canonical);
        Ok(())
    }

    /// Get the number of unique k-mers
    fn get_unique_count(&self) -> usize {
        self.backend.read().counts.len()
    }

    /// Get the total count of all k-mers
    fn get_total_count(&self) -> u64 {
        self.backend.read().counts.values().sum()
    }

    /// Save k-mer counts to a database file using CLI RKDB format
    #[pyo3(signature = (database_path, compression=true))]
    fn save_to_database(&self, database_path: String, compression: bool) -> PyResult<()> {
        // Use CLI's RKDB binary format for complete compatibility
        let backend = self.backend.read();
        let counts = &backend.counts; // Access the HashMap<u64, u64> directly
        let kmer_count = counts.len() as u64;

        // Create output file
        let file = File::create(&database_path)
            .map_err(|e| DatabaseError::new_err(format!("Failed to create database file: {}", e)))?;
        let mut writer = BufWriter::new(file);

        // Create RKDB database header using CLI's DatabaseHeader struct
        let header = DatabaseHeader {
            magic: *DATABASE_MAGIC,
            version: DATABASE_VERSION,
            kmer_size: backend.k as u8,
            total_kmers: kmer_count,
            sorted: false,  // TODO: Add sorting option if needed
            data_offset: 42, // Fixed header size for RKDB format (matches CLI)
            index_offset: 0,
            canonical: backend.canonical,
            unique_kmers: kmer_count,  // Same as total_kmers for now
            file_size: 42 + (kmer_count * 12),  // Header + k-mer entries (8+4 bytes each)
        };

        // Write header using CLI's exact format
        header.write_to(&mut writer)
            .map_err(|e| DatabaseError::new_err(format!("Failed to write database header: {}", e)))?;

        // Write k-mer entries in CLI format (8-byte k-mer + 4-byte count)
        for (&kmer, &count) in counts {
            writer.write_u64::<LittleEndian>(kmer)
                .map_err(|e| DatabaseError::new_err(format!("Failed to write k-mer: {}", e)))?;
            writer.write_u32::<LittleEndian>(count as u32)
                .map_err(|e| DatabaseError::new_err(format!("Failed to write count: {}", e)))?;
        }

        // Flush to ensure data is written
        writer.flush()
            .map_err(|e| DatabaseError::new_err(format!("Failed to flush database: {}", e)))?;

        Ok(())
    }

    /// Get a string representation
    fn __repr__(&self) -> String {
        let backend = self.backend.read();
        format!("KmerCounter(k={}, canonical={}, unique_kmers={})",
                backend.k, backend.canonical, backend.counts.len())
    }

    /// Get a string representation
    fn __str__(&self) -> String {
        self.__repr__()
    }
}