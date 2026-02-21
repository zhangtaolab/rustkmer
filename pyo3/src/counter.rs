//! PyCounter - Python wrapper for RustKmer PyCounter
//!
//! This module provides a Python class that wraps Rust PyCounter
//! to provide high-performance k-mer counting functionality.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use rustkmer::hash::KmerCounter as RustPyCounter;
use rustkmer::io::fasta::FastaProcessor;
use rustkmer::io::fastq::FastqProcessor;
use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::kmer::encoding::encode_kmer_bytes_u128;
use std::path::Path;

/// Statistics for Counter operations
#[pyclass]
pub struct PyCounterStats {
    /// Total k-mers processed
    pub total_kmers: u64,
    /// Number of unique k-mers
    pub unique_kmers: u64,
    /// K-mer length
    pub kmer_length: usize,
    /// Whether canonical mode is enabled
    pub canonical_mode: bool,
    /// Estimated memory usage in bytes
    pub memory_usage: usize,
}

#[pymethods]
impl PyCounterStats {
    #[getter]
    fn total_kmers(&self) -> u64 {
        self.total_kmers
    }

    #[getter]
    fn unique_kmers(&self) -> u64 {
        self.unique_kmers
    }

    #[getter]
    fn kmer_length(&self) -> usize {
        self.kmer_length
    }

    #[getter]
    fn canonical_mode(&self) -> bool {
        self.canonical_mode
    }

    #[getter]
    fn memory_usage(&self) -> usize {
        self.memory_usage
    }

    fn __repr__(&self) -> String {
        format!(
            "PyCounterStats(total_kmers={}, unique_kmers={}, kmer_length={}, canonical_mode={}, memory_usage={})",
            self.total_kmers, self.unique_kmers, self.kmer_length, self.canonical_mode, self.memory_usage
        )
    }
}

/// High-performance k-mer counter for Python
///
/// This class provides a Python interface to RustKmer's high-performance
/// k-mer counting functionality, supporting:
///
/// - Adding individual k-mers
/// - Processing sequences from strings
/// - Reading FASTA and FASTQ files (with compression support)
/// - Saving results to RKDB database format
/// - Canonical k-mer counting
///
/// # Examples
///
/// ```python
/// from pyrustkmer import PyCounter
///
/// # Create a counter for k=21 with canonical mode
/// counter = PyCounter(21, canonical=True)
///
/// # Add a single k-mer
/// counter.add_kmer("ATGCGATGCATGCGATGCAT")
///
/// # Add a sequence
/// counter.add_sequence("ATGCGATGCATGCGATGCATGCGATGCAT")
///
/// # Process a FASTA file
/// counter.add_from_fasta("sequences.fasta")
///
/// # Process a FASTQ file (supports .gz compression)
/// counter.add_from_fastq("reads.fastq.gz")
///
/// # Save to database
/// counter.save_database("output.rkdb")
///
/// # Get statistics
/// stats = counter.get_stats()
/// print(f"Total k-mers: {stats.total_kmers}")
/// print(f"Unique k-mers: {stats.unique_kmers}")
/// ```
#[pyclass(name = "PyCounter")]
pub struct PyCounter {
    /// Internal Rust PyCounter
    counter: RustPyCounter,
}

#[pymethods]
impl PyCounter {
    /// Create a new k-mer counter
    ///
    /// # Arguments
    /// * `kmer_length` - Length of k-mers to count (1-64)
    /// * `canonical` - Whether to count canonical k-mers (forward and reverse complement merged)
    /// * `initial_capacity` - Initial hash table capacity (default: 1000)
    ///
    /// # Returns
    /// New PyPyCounter instance
    ///
    /// # Raises
    /// ValueError if kmer_length is not between 1 and 64
    #[new]
    #[pyo3(signature = (kmer_length, canonical=false, initial_capacity=1000))]
    fn new(kmer_length: i64, canonical: bool, initial_capacity: usize) -> PyResult<Self> {
        // Validate that kmer_length is in the valid range (1-64)
        // Using i64 allows us to catch negative values before they overflow
        if !(1..=64).contains(&kmer_length) {
            return Err(PyErr::new::<PyValueError, _>(format!(
                "Invalid k-mer size: {}. Must be between 1 and 64",
                kmer_length
            )));
        }

        // Convert to usize after validation (safe because we've already checked the range)
        let kmer_length_usize = kmer_length as usize;

        // Use a single thread for Python bindings (threading handled differently in Python)
        let counter = RustPyCounter::new(kmer_length_usize, canonical, initial_capacity, 1)
            .map_err(|e| {
                PyErr::new::<PyValueError, _>(format!("Failed to create counter: {}", e))
            })?;

        Ok(Self { counter })
    }

    /// Add a single k-mer to the counter
    ///
    /// # Arguments
    /// * `kmer` - K-mer string (must contain only A, C, G, T)
    ///
    /// # Raises
    /// ValueError if k-mer contains invalid characters or has wrong length
    ///
    /// # Example
    /// ```python
    /// counter.add_kmer("ATGCGATGCATGCGATGCAT")
    /// ```
    fn add_kmer(&mut self, kmer: &Bound<'_, pyo3::types::PyString>) -> PyResult<()> {
        let kmer_str = kmer.to_str()?;
        let kmer_bytes = kmer_str.as_bytes();

        // Validate k-mer length
        if kmer_bytes.len() != self.counter.kmer_length() {
            return Err(PyErr::new::<PyValueError, _>(format!(
                "K-mer length mismatch: expected {}, got {}",
                self.counter.kmer_length(),
                kmer_bytes.len()
            )));
        }

        // Encode k-mer
        let encoded = encode_kmer_bytes_u128(kmer_bytes)
            .map_err(|e| PyErr::new::<PyValueError, _>(format!("Failed to encode k-mer: {}", e)))?;

        // Apply canonical transformation if needed
        let encoded_to_add = if self.counter.canonical_mode() {
            canonical_kmer_u128(encoded, self.counter.kmer_length()).map_err(|e| {
                PyErr::new::<PyValueError, _>(format!("Failed to compute canonical k-mer: {}", e))
            })?
        } else {
            encoded
        };

        // Increment count
        self.counter.increment(encoded_to_add).map_err(|e| {
            PyErr::new::<PyValueError, _>(format!("Failed to increment k-mer count: {}", e))
        })?;

        Ok(())
    }

    /// Extract and add k-mers from a sequence string
    ///
    /// # Arguments
    /// * `sequence` - DNA sequence string (may contain whitespace)
    ///
    /// # Notes
    /// - Invalid characters (N, etc.) are skipped
    /// - K-mers spanning invalid characters are not counted
    ///
    /// # Example
    /// ```python
    /// counter.add_sequence("ATGCGATGCATGCGATGCATGCGATGCAT")
    /// ```
    fn add_sequence(&mut self, sequence: &Bound<'_, pyo3::types::PyString>) -> PyResult<()> {
        let seq_str = sequence.to_str()?;
        let k = self.counter.kmer_length();

        // Clean sequence: remove whitespace and keep only valid bases
        let cleaned: Vec<u8> = seq_str
            .bytes()
            .filter(|&b| matches!(b.to_ascii_uppercase(), b'A' | b'C' | b'G' | b'T'))
            .collect();

        if cleaned.len() < k {
            // Sequence too short for any k-mers
            return Ok(());
        }

        // Extract k-mers
        for i in 0..=(cleaned.len() - k) {
            let kmer = &cleaned[i..i + k];

            // Encode k-mer
            if let Ok(encoded) = encode_kmer_bytes_u128(kmer) {
                // Apply canonical transformation if needed
                let encoded_to_add = if self.counter.canonical_mode() {
                    match canonical_kmer_u128(encoded, k) {
                        Ok(canonical) => canonical,
                        Err(_) => continue, // Skip on canonical computation error
                    }
                } else {
                    encoded
                };

                // Increment count
                if let Err(e) = self.counter.increment(encoded_to_add) {
                    return Err(PyErr::new::<PyValueError, _>(format!(
                        "Failed to increment k-mer count: {}",
                        e
                    )));
                }
            }
            // If encoding fails, skip this k-mer (e.g., invalid characters)
        }

        Ok(())
    }

    /// Read and process k-mers from a FASTA file
    ///
    /// # Arguments
    /// * `file_path` - Path to FASTA file (supports .gz compression)
    ///
    /// # Notes
    /// - Automatically detects and handles gzip compression (.gz)
    /// - Invalid characters in sequences are skipped
    /// - Headers are ignored
    ///
    /// # Raises
    /// ValueError if file cannot be read
    ///
    /// # Example
    /// ```python
    /// counter.add_from_fasta("sequences.fasta")
    /// counter.add_from_fasta("compressed.fasta.gz")
    /// ```
    fn add_from_fasta(&mut self, file_path: &Bound<'_, pyo3::types::PyString>) -> PyResult<()> {
        let path_str = file_path.to_str()?;
        let path = Path::new(path_str);

        // Check file extension for compression
        let is_compressed = path
            .extension()
            .and_then(|ext| ext.to_str())
            .map(|ext| ext == "gz")
            .unwrap_or(false);

        let k = self.counter.kmer_length();

        if is_compressed {
            // Handle compressed FASTA using flate2
            use flate2::read::GzDecoder;
            use std::io::{BufRead, BufReader};

            let file = std::fs::File::open(path).map_err(|e| {
                PyErr::new::<PyValueError, _>(format!("Failed to open file: {}", e))
            })?;

            let decoder = GzDecoder::new(file);
            let reader = BufReader::new(decoder);

            let mut current_seq = Vec::new();

            for line_result in reader.lines() {
                let line = line_result.map_err(|e| {
                    PyErr::new::<PyValueError, _>(format!("Failed to read line: {}", e))
                })?;

                let trimmed = line.trim();

                if trimmed.starts_with('>') {
                    // Process previous sequence
                    if !current_seq.is_empty() && current_seq.len() >= k {
                        self.process_sequence_bytes(&current_seq).map_err(|e| {
                            PyErr::new::<PyValueError, _>(format!(
                                "Failed to process sequence: {}",
                                e
                            ))
                        })?;
                    }
                    current_seq.clear();
                } else {
                    // Collect sequence bases
                    current_seq.extend(
                        trimmed.bytes().filter(|&b| {
                            matches!(b.to_ascii_uppercase(), b'A' | b'C' | b'G' | b'T')
                        }),
                    );
                }
            }

            // Process last sequence
            if !current_seq.is_empty() && current_seq.len() >= k {
                self.process_sequence_bytes(&current_seq).map_err(|e| {
                    PyErr::new::<PyValueError, _>(format!("Failed to process sequence: {}", e))
                })?;
            }
        } else {
            // Use FastaProcessor for uncompressed files
            let processor = FastaProcessor::new(path);

            processor
                .process_file(|record| {
                    let seq_bytes = record.seq();
                    if seq_bytes.len() >= k {
                        self.process_sequence_bytes(seq_bytes)
                    } else {
                        Ok(())
                    }
                })
                .map_err(|e| {
                    PyErr::new::<PyValueError, _>(format!("Failed to process FASTA: {}", e))
                })?;
        }

        Ok(())
    }

    /// Read and process k-mers from a FASTQ file
    ///
    /// # Arguments
    /// * `file_path` - Path to FASTQ file (supports .gz compression)
    ///
    /// # Notes
    /// - Automatically detects and handles gzip compression (.gz)
    /// - Invalid characters in sequences are skipped
    /// - Headers and quality strings are ignored
    ///
    /// # Raises
    /// ValueError if file cannot be read
    ///
    /// # Example
    /// ```python
    /// counter.add_from_fastq("reads.fastq")
    /// counter.add_from_fastq("compressed_reads.fastq.gz")
    /// ```
    fn add_from_fastq(&mut self, file_path: &Bound<'_, pyo3::types::PyString>) -> PyResult<()> {
        let path_str = file_path.to_str()?;
        let path = Path::new(path_str);

        // Check file extension for compression
        let is_compressed = path
            .extension()
            .and_then(|ext| ext.to_str())
            .map(|ext| ext == "gz")
            .unwrap_or(false);

        let k = self.counter.kmer_length();

        if is_compressed {
            // Handle compressed FASTQ
            use flate2::read::GzDecoder;
            use std::io::{BufRead, BufReader};

            let file = std::fs::File::open(path).map_err(|e| {
                PyErr::new::<PyValueError, _>(format!("Failed to open file: {}", e))
            })?;

            let decoder = GzDecoder::new(file);
            let reader = BufReader::new(decoder);

            let mut line_num = 0;

            for line_result in reader.lines() {
                let line = line_result.map_err(|e| {
                    PyErr::new::<PyValueError, _>(format!("Failed to read line: {}", e))
                })?;

                line_num += 1;
                let line_mod = line_num % 4;

                // FASTQ format: line 1 = header (@...), line 2 = sequence, line 3 = +, line 4 = quality
                if line_mod == 2 {
                    let trimmed = line.trim();

                    // Process sequence
                    let seq_bytes: Vec<u8> = trimmed
                        .bytes()
                        .filter(|&b| matches!(b.to_ascii_uppercase(), b'A' | b'C' | b'G' | b'T'))
                        .collect();

                    if seq_bytes.len() >= k {
                        self.process_sequence_bytes(&seq_bytes).map_err(|e| {
                            PyErr::new::<PyValueError, _>(format!(
                                "Failed to process FASTQ sequence: {}",
                                e
                            ))
                        })?;
                    }
                }
            }
        } else {
            // Use FastqProcessor for uncompressed files
            let processor = FastqProcessor::new(path);

            processor
                .process_file(|record| {
                    let seq_bytes = record.seq();
                    if seq_bytes.len() >= k {
                        self.process_sequence_bytes(seq_bytes)
                    } else {
                        Ok(())
                    }
                })
                .map_err(|e| {
                    PyErr::new::<PyValueError, _>(format!("Failed to process FASTQ: {}", e))
                })?;
        }

        Ok(())
    }

    /// Save k-mer counts to an RKDB database file
    ///
    /// # Arguments
    /// * `file_path` - Path to output database file (.rkdb)
    ///
    /// # Notes
    /// - Creates a sorted RKDB database for fast querying
    /// - Uses canonical k-mer encoding if enabled
    /// - Database can be loaded using rustkmer.Database
    ///
    /// # Raises
    /// ValueError if file cannot be written
    ///
    /// # Example
    /// ```python
    /// counter.save_database("output.rkdb")
    ///
    /// # Load database for querying
    /// from pyrustkmer import PyDatabase, LoadMode
    /// db = PyDatabase("output.rkdb", LoadMode.Preload)
    /// ```
    fn save_database(&self, file_path: &Bound<'_, pyo3::types::PyString>) -> PyResult<()> {
        use rustkmer::database::format::{DatabaseHeader, RKDatabase};
        use std::fs::File;
        use std::io::BufWriter;

        let path_str = file_path.to_str()?;
        let path = Path::new(path_str);

        // Get all k-mer counts
        let kmer_counts = self.counter.get_all_counts();

        if kmer_counts.is_empty() {
            return Err(PyErr::new::<PyValueError, _>(
                "Cannot save empty database. Add k-mers first.",
            ));
        }

        // Sort k-mers for binary search
        let mut sorted_kmers: Vec<(u128, u32)> = kmer_counts;
        sorted_kmers.sort_by_key(|&(k, _)| k);

        // Create database
        let kmer_size = self.counter.kmer_length() as u8;
        let canonical = self.counter.canonical_mode();
        let total_kmers = sorted_kmers.len() as u64;

        let _header = DatabaseHeader::new(kmer_size, total_kmers, canonical);

        let db =
            RKDatabase::from_kmer_pairs(sorted_kmers, kmer_size, canonical, true).map_err(|e| {
                PyErr::new::<PyValueError, _>(format!("Failed to create database: {}", e))
            })?;

        // Write to file
        let file = File::create(path)
            .map_err(|e| PyErr::new::<PyValueError, _>(format!("Failed to create file: {}", e)))?;

        let mut writer = BufWriter::new(file);

        db.write_to(&mut writer).map_err(|e| {
            PyErr::new::<PyValueError, _>(format!("Failed to write database: {}", e))
        })?;

        Ok(())
    }

    /// Get statistics for the counter
    ///
    /// # Returns
    /// PyCounterStats object containing:
    /// - total_kmers: Total number of k-mers processed
    /// - unique_kmers: Number of unique k-mers found
    /// - kmer_length: K-mer length
    /// - canonical_mode: Whether canonical mode is enabled
    /// - memory_usage: Estimated memory usage in bytes
    ///
    /// # Example
    /// ```python
    /// stats = counter.get_stats()
    /// print(f"Total: {stats.total_kmers}, Unique: {stats.unique_kmers}")
    /// ```
    fn get_stats(&self) -> PyCounterStats {
        let total_kmers = self.counter.total_kmers();
        let unique_kmers = self.counter.unique_kmers();
        let kmer_length = self.counter.kmer_length();
        let canonical_mode = self.counter.canonical_mode();
        let memory_usage = self.counter.memory_usage();

        PyCounterStats {
            total_kmers,
            unique_kmers,
            kmer_length,
            canonical_mode,
            memory_usage,
        }
    }

    /// Get k-mer length
    #[getter]
    fn kmer_length(&self) -> usize {
        self.counter.kmer_length()
    }

    /// Get whether canonical mode is enabled
    #[getter]
    fn canonical(&self) -> bool {
        self.counter.canonical_mode()
    }

    /// Check if the counter is empty
    ///
    /// # Returns
    /// True if no k-mers have been counted, False otherwise
    ///
    /// # Example
    /// ```python
    /// if not counter.is_empty():
    ///     print(f"Counted {counter.get_stats().total_kmers} k-mers")
    /// ```
    fn is_empty(&self) -> bool {
        self.counter.total_kmers() == 0
    }

    /// Get the count for a specific k-mer
    ///
    /// # Arguments
    /// * `kmer` - K-mer string to query
    ///
    /// # Returns
    /// Count of the k-mer (0 if not found)
    ///
    /// # Raises
    /// ValueError if k-mer contains invalid characters or has wrong length
    ///
    /// # Example
    /// ```python
    /// count = counter.get_count("ATGCGATGCATGCGATGCAT")
    /// print(f"K-mer appears {count} times")
    /// ```
    fn get_count(&self, kmer: &Bound<'_, pyo3::types::PyString>) -> PyResult<u32> {
        let kmer_str = kmer.to_str()?;
        let kmer_bytes = kmer_str.as_bytes();

        // Validate k-mer length
        if kmer_bytes.len() != self.counter.kmer_length() {
            return Err(PyErr::new::<PyValueError, _>(format!(
                "K-mer length mismatch: expected {}, got {}",
                self.counter.kmer_length(),
                kmer_bytes.len()
            )));
        }

        // Encode k-mer
        let encoded = encode_kmer_bytes_u128(kmer_bytes)
            .map_err(|e| PyErr::new::<PyValueError, _>(format!("Failed to encode k-mer: {}", e)))?;

        // Apply canonical transformation if needed
        let encoded_to_query = if self.counter.canonical_mode() {
            canonical_kmer_u128(encoded, self.counter.kmer_length()).map_err(|e| {
                PyErr::new::<PyValueError, _>(format!("Failed to compute canonical k-mer: {}", e))
            })?
        } else {
            encoded
        };

        // Get count
        Ok(self.counter.get_count(encoded_to_query).unwrap_or(0))
    }

    /// Reset the counter, clearing all counted k-mers
    ///
    /// # Example
    /// ```python
    /// counter.reset()
    /// # Counter is now empty
    /// ```
    fn reset(&mut self) {
        self.counter.reset();
    }

    /// Get all k-mer counts as a dictionary
    ///
    /// # Returns
    /// Dictionary mapping k-mer strings to their counts
    ///
    /// # Notes
    /// - For canonical mode, returns canonical k-mers
    /// - May use significant memory for large counters
    ///
    /// # Example
    /// ```python
    /// counts = counter.get_all_counts()
    /// for kmer, count in counts.items():
    ///     print(f"{kmer}: {count}")
    /// ```
    fn get_all_counts(&self) -> PyResult<std::collections::HashMap<String, u32>> {
        use rustkmer::kmer::encoding::decode_kmer_u128;

        let mut result = std::collections::HashMap::new();
        let kmer_counts = self.counter.get_all_counts();
        let k = self.counter.kmer_length();

        for (encoded, count) in kmer_counts {
            let kmer_str = decode_kmer_u128(encoded, k);
            result.insert(kmer_str, count);
        }

        Ok(result)
    }

    fn __repr__(&self) -> String {
        let stats = self.get_stats();
        format!(
            "PyCounter(kmer_length={}, canonical={}, total_kmers={}, unique_kmers={})",
            stats.kmer_length, stats.canonical_mode, stats.total_kmers, stats.unique_kmers
        )
    }
}

impl PyCounter {
    /// Helper function to process sequence bytes and count k-mers
    fn process_sequence_bytes(
        &mut self,
        seq_bytes: &[u8],
    ) -> Result<(), rustkmer::ProcessingError> {
        let k = self.counter.kmer_length();

        // Extract k-mers from sequence
        for i in 0..=(seq_bytes.len() - k) {
            let kmer = &seq_bytes[i..i + k];

            // Encode k-mer
            if let Ok(encoded) = encode_kmer_bytes_u128(kmer) {
                // Apply canonical transformation if needed
                let encoded_to_add = if self.counter.canonical_mode() {
                    match canonical_kmer_u128(encoded, k) {
                        Ok(canonical) => canonical,
                        Err(_) => continue,
                    }
                } else {
                    encoded
                };

                // Increment count
                if let Err(e) = self.counter.increment(encoded_to_add) {
                    return Err(rustkmer::ProcessingError::with_context(
                        "Failed to increment k-mer count",
                        Box::new(e),
                    ));
                }
            }
        }

        Ok(())
    }
}
