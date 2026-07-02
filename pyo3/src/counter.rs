//! PyCounter - Python wrapper for RustKmer PyCounter
//!
//! This module provides a Python class that wraps Rust PyCounter
//! to provide high-performance k-mer counting functionality.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use rustkmer::hash::KmerCounter as RustPyCounter;
use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::kmer::encoding::encode_kmer_bytes_u128;
use std::path::Path;
use std::sync::Arc;

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
    /// Internal Rust PyCounter, wrapped in `Arc` so it can be cloned into the
    /// `py.allow_threads(..)` closures used by the heavy counting methods
    /// (`add_from_fastq` / `add_from_fasta`). `RustPyCounter` (a re-export of
    /// `rustkmer::hash::KmerCounter`) uses `dashmap::DashMap` for storage, which
    /// gives interior mutability — so incrementing counts through `&self` is
    /// sound under rayon's parallel workers (Phase 2, PCOUNT-03 / D-08).
    counter: Arc<RustPyCounter>,
}

#[pymethods]
impl PyCounter {
    /// Create a new k-mer counter
    ///
    /// # Arguments
    /// * `kmer_length` - Length of k-mers to count (1-64)
    /// * `canonical` - Whether to count canonical k-mers (forward and reverse complement merged)
    /// * `initial_capacity` - Initial hash table capacity (default: 1000)
    /// * `threads` - Number of rayon worker threads for parallel counting
    ///   (default `None` = all available cores). Values `< 1` are rejected.
    ///   This is parity with the CLI's `--threads` flag (D-08, PCOUNT-03).
    ///
    /// # Returns
    /// New PyCounter instance
    ///
    /// # Raises
    /// ValueError if kmer_length is not between 1 and 64, or if threads < 1
    #[new]
    #[pyo3(signature = (kmer_length, canonical=false, initial_capacity=1000, threads=None))]
    fn new(
        kmer_length: i64,
        canonical: bool,
        initial_capacity: usize,
        threads: Option<usize>,
    ) -> PyResult<Self> {
        // Validate that kmer_length is in the valid range (1-64)
        // Using i64 allows us to catch negative values before they overflow
        if !(1..=64).contains(&kmer_length) {
            return Err(PyErr::new::<PyValueError, _>(format!(
                "Invalid k-mer size: {}. Must be between 1 and 64",
                kmer_length
            )));
        }

        // Validate threads (T-02-13): mirror the InvalidKmerSize style. A value
        // of Some(0) (or any Some(n) where n < 1) is rejected; None means "use
        // all available cores" — parity with the CLI --threads default (D-08).
        if let Some(t) = threads {
            if t < 1 {
                return Err(PyErr::new::<PyValueError, _>(format!(
                    "Invalid thread count: {}. Must be >= 1",
                    t
                )));
            }
        }

        // Convert to usize after validation (safe because we've already checked the range)
        let kmer_length_usize = kmer_length as usize;

        // Resolve the thread count. `None` => all cores. We use
        // `std::thread::available_parallelism()` (stable since Rust 1.59; the
        // project targets 1.80+) rather than `num_cpus::get()` to avoid adding
        // a direct `num_cpus` dependency — it is semantically equivalent
        // (returns the number of logical CPUs the runtime considers usable)
        // and lives in `std`. Falls back to 1 on unsupported platforms.
        let resolved_threads = threads.unwrap_or_else(|| {
            std::thread::available_parallelism()
                .map(|v| v.get())
                .unwrap_or(1)
        });

        // Configure the global rayon pool ONCE. `build_global` returns `Err`
        // (not a panic) if the pool was already initialized — e.g. a user
        // constructs a second `PyCounter`, or a prior CLI command in the same
        // process already set it. We deliberately discard the `Result`
        // (T-02-12, Pitfall 3). This mirrors 02-01's `execute_count` idiom.
        //
        // IN-04: on the *first* construction the discard can silently swallow
        // a real pool-construction failure (e.g. restrictive cgroups/ulimits
        // rejecting the requested thread count). Surface it under
        // `RUST_LOG=warn` so the silent-success contract (no hard error) is
        // preserved while still giving users a diagnostic. The second-call
        // case is also logged — harmless, and indistinguishable from a
        // genuine failure without inspecting the message.
        if let Err(e) = rayon::ThreadPoolBuilder::new()
            .num_threads(resolved_threads)
            .build_global()
        {
            log::warn!(
                "could not configure global rayon pool (threads={}): {}",
                resolved_threads,
                e
            );
        }

        let counter = RustPyCounter::new(kmer_length_usize, canonical, initial_capacity, resolved_threads)
            .map_err(|e| {
                PyErr::new::<PyValueError, _>(format!("Failed to create counter: {}", e))
            })?;

        Ok(Self {
            counter: Arc::new(counter),
        })
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
    // GIL not released: sub-millisecond workload (single k-mer encode +
    // increment); the `py.allow_threads(..)` release/reacquire overhead would
    // exceed the benefit. Documented per RESEARCH Open Question 1.
    fn add_kmer(&self, kmer: &Bound<'_, pyo3::types::PyString>) -> PyResult<()> {
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
    // GIL not released: short-sequence workload (a single string's k-mers);
    // sub-millisecond for typical inputs. The `py.allow_threads(..)`
    // release/reacquire overhead would exceed the benefit for anything but
    // very long sequences, which should be loaded from a file via
    // `add_from_fasta` / `add_from_fastq` instead (those DO release the GIL).
    // Documented per RESEARCH Open Question 1.
    fn add_sequence(&self, sequence: &Bound<'_, pyo3::types::PyString>) -> PyResult<()> {
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
    fn add_from_fasta(
        &self,
        py: Python<'_>,
        file_path: &Bound<'_, pyo3::types::PyString>,
    ) -> PyResult<()> {
        // CRITICAL (T-02-11 / Pitfall 4): extract ALL Python arguments into
        // owned, `Send` Rust types BEFORE entering the `allow_threads` closure.
        // The closure cannot capture `&PyString` / `Bound<T>` / `PyObject` —
        // rayon workers are OS threads without GIL access. `to_str()?.to_owned()`
        // yields an owned `String` (Send); the `Arc<RustPyCounter>` clone is
        // likewise Send. The closure moves both.
        let path_str = file_path.to_str()?.to_owned();
        let counter = self.counter.clone();

        // Release the GIL for the duration of the file read + per-record
        // encode/canonicalize/increment work so rayon workers actually run in
        // parallel (D-08, PCOUNT-03). Without this release the GIL would
        // serialize the workers and the parallel speedup would not materialize.
        //
        // API NOTE: pyo3 0.27.2 provides `Python::detach` as the canonical,
        // non-deprecated GIL-release API. `Python::allow_threads` exists but is
        // `#[deprecated(since = "0.26.0", note = "use Python::detach instead")]`
        // in pyo3 0.27.2 (it delegates to `self.detach(f)`). The RESEARCH note
        // that claimed `detach` is "0.28+ only" was factually inverted —
        // `detach` is the recommended API in 0.27.2. Using `allow_threads`
        // would fail the `-D warnings` FOUND-01 clippy gate. Both enforce the
        // same `Ungil` (= effectively `Send`) bound on the closure.
        py.detach(move || process_fasta_file_on_counter(&counter, &path_str))
            .map_err(|e: rustkmer::ProcessingError| {
                PyErr::new::<PyValueError, _>(format!("Failed to process FASTA: {}", e))
            })
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
    fn add_from_fastq(
        &self,
        py: Python<'_>,
        file_path: &Bound<'_, pyo3::types::PyString>,
    ) -> PyResult<()> {
        // CRITICAL (T-02-11 / Pitfall 4): extract ALL Python arguments into
        // owned, `Send` Rust types BEFORE entering the `allow_threads` closure.
        // The closure cannot capture `&PyString` / `Bound<T>` / `PyObject` —
        // rayon workers are OS threads without GIL access. `to_str()?.to_owned()`
        // yields an owned `String` (Send); the `Arc<RustPyCounter>` clone is
        // likewise Send. The closure moves both.
        let path_str = file_path.to_str()?.to_owned();
        let counter = self.counter.clone();

        // Release the GIL for the duration of the file read + per-record
        // encode/canonicalize/increment work so rayon workers actually run in
        // parallel (D-08, PCOUNT-03). Without this release the GIL would
        // serialize the workers and the parallel speedup would not materialize.
        //
        // API NOTE: see `add_from_fasta` for the `py.detach` (not the
        // deprecated `allow_threads`) rationale — pyo3 0.27.2.
        py.detach(move || process_fastq_file_on_counter(&counter, &path_str))
            .map_err(|e: rustkmer::ProcessingError| {
                PyErr::new::<PyValueError, _>(format!("Failed to process FASTQ: {}", e))
            })
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
    fn reset(&self) {
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

/// Count all k-mers in `seq_bytes` against `counter`.
///
/// This is a free function (not a method on `PyCounter`) so it can be called
/// from inside a `py.allow_threads(move || { .. })` closure, which may only
/// capture `Send` types. The closure clones the `Arc<RustPyCounter>` and moves
/// it in, then passes a `&RustPyCounter` here. `RustPyCounter` uses
/// `dashmap::DashMap` for storage, so `increment` takes `&self` and is sound
/// under rayon's parallel workers (Phase 2, PCOUNT-03 / D-08).
///
/// Invalid bases (anything outside A/C/G/T after uppercasing) are skipped at
/// the k-mer extraction step via `encode_kmer_bytes_u128` returning `Err`;
/// canonical computation errors likewise `continue`. The overflow semantics
/// (error on `u32::MAX` per k-mer) are inherited verbatim from
/// `RustPyCounter::increment` (PCOUNT-04).
fn process_sequence_on_counter(
    counter: &RustPyCounter,
    seq_bytes: &[u8],
) -> Result<(), rustkmer::ProcessingError> {
    let k = counter.kmer_length();
    if seq_bytes.len() < k {
        return Ok(());
    }

    // Extract k-mers from sequence
    for i in 0..=(seq_bytes.len() - k) {
        let kmer = &seq_bytes[i..i + k];

        // Encode k-mer
        if let Ok(encoded) = encode_kmer_bytes_u128(kmer) {
            // Apply canonical transformation if needed
            let encoded_to_add = if counter.canonical_mode() {
                match canonical_kmer_u128(encoded, k) {
                    Ok(canonical) => canonical,
                    Err(_) => continue,
                }
            } else {
                encoded
            };

            // Increment count
            if let Err(e) = counter.increment(encoded_to_add) {
                return Err(rustkmer::ProcessingError::with_context(
                    "Failed to increment k-mer count",
                    Box::new(e),
                ));
            }
        }
    }

    Ok(())
}

/// Count all k-mers in a FASTA file (gzip/bzip2/xz/plain) against `counter`.
///
/// Designed to run inside a `py.allow_threads(..)` closure: takes only `Send`
/// types (an `&Arc<RustPyCounter>` and a `&str` path). Reads the file,
/// decompresses it transparently if the extension is `.gz` / `.bz2` / `.xz`
/// (WR-05: previously only `.gz` was detected; `.bz2` / `.xz` were silently
/// mis-parsed), and accumulates each record's sequence into the shared
/// counter. Errors are returned as `rustkmer::ProcessingError` so the caller
/// (which holds the GIL again after `allow_threads` returns) can map them to
/// `PyErr`.
fn process_fasta_file_on_counter(
    counter: &Arc<RustPyCounter>,
    path: &str,
) -> Result<(), rustkmer::ProcessingError> {
    use rustkmer::io::fastq::{CompressedFileReader, DefaultCompressedFileReader};
    use std::io::{BufRead, BufReader};

    let path = Path::new(path);

    // WR-05: route through the shared compression-aware opener (the same one
    // the CLI path uses) so `.bz2` / `.xz` inputs are decompressed correctly.
    // Previously this branch detected only `.gz` inline and silently fell
    // through to raw-byte parsing for the other two formats.
    let (file, _compression) =
        DefaultCompressedFileReader::open_compressed(path).map_err(|e| {
            rustkmer::ProcessingError::with_context("Failed to open FASTA file", Box::new(e))
        })?;
    let reader = BufReader::new(file);

    let k = counter.kmer_length();
    let mut current_seq = Vec::new();

    for line_result in reader.lines() {
        let line = line_result.map_err(|e| {
            rustkmer::ProcessingError::with_context("Failed to read FASTA line", Box::new(e))
        })?;

        let trimmed = line.trim();

        if trimmed.starts_with('>') {
            // Process previous sequence
            if !current_seq.is_empty() && current_seq.len() >= k {
                process_sequence_on_counter(counter, &current_seq)?;
            }
            current_seq.clear();
        } else {
            // Collect sequence bases
            current_seq.extend(
                trimmed
                    .bytes()
                    .filter(|&b| matches!(b.to_ascii_uppercase(), b'A' | b'C' | b'G' | b'T')),
            );
        }
    }

    // Process last sequence
    if !current_seq.is_empty() && current_seq.len() >= k {
        process_sequence_on_counter(counter, &current_seq)?;
    }

    Ok(())
}

/// Count all k-mers in a FASTQ file (gzip/bzip2/xz/plain) against `counter`.
///
/// Designed to run inside a `py.allow_threads(..)` closure: takes only `Send`
/// types (an `&Arc<RustPyCounter>` and a `&str` path). Reads the file,
/// decompresses it transparently if the extension is `.gz` / `.bz2` / `.xz`
/// (WR-05: previously only `.gz` was detected; `.bz2` / `.xz` were silently
/// mis-parsed), and accumulates each record's sequence into the shared
/// counter. Errors are returned as `rustkmer::ProcessingError` so the caller
/// (which holds the GIL again after `allow_threads` returns) can map them to
/// `PyErr`.
fn process_fastq_file_on_counter(
    counter: &Arc<RustPyCounter>,
    path: &str,
) -> Result<(), rustkmer::ProcessingError> {
    use rustkmer::io::fastq::{CompressedFileReader, DefaultCompressedFileReader};
    use std::io::{BufRead, BufReader};

    let path = Path::new(path);

    // WR-05: route through the shared compression-aware opener (the same one
    // the CLI path uses) so `.bz2` / `.xz` inputs are decompressed correctly.
    // Previously this branch detected only `.gz` inline and silently fell
    // through to raw-byte parsing for the other two formats.
    let (file, _compression) =
        DefaultCompressedFileReader::open_compressed(path).map_err(|e| {
            rustkmer::ProcessingError::with_context("Failed to open FASTQ file", Box::new(e))
        })?;
    let reader = BufReader::new(file);

    let k = counter.kmer_length();
    let mut line_num = 0;

    for line_result in reader.lines() {
        let line = line_result.map_err(|e| {
            rustkmer::ProcessingError::with_context("Failed to read FASTQ line", Box::new(e))
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
                process_sequence_on_counter(counter, &seq_bytes)?;
            }
        }
    }

    Ok(())
}
