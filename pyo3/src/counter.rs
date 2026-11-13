//! PyCounter - Python wrapper for RustKmer PyCounter
//!
//! This module provides a Python class that wraps Rust PyCounter
//! to provide high-performance k-mer counting functionality.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use rustkmer::count::{CountEngine, EngineConfig, SequenceKind};
use rustkmer::hash::KmerCounter as RustPyCounter;
use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::kmer::encoding::encode_kmer_bytes_u128;
use rustkmer::kmer::extract::{for_each_window, WindowError};
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
    /// Resolved rayon worker count the counter was constructed with.
    ///
    /// Phase 9 (WR-02) diagnostics: the benchmark harness uses this to prove
    /// the requested `threads` configuration was actually applied instead of
    /// trusting the controller's requested string. Read-only observation —
    /// it is a statistic of the counter, not a `PyCounter` member.
    pub threads: usize,
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

    #[getter]
    fn threads(&self) -> usize {
        self.threads
    }

    fn __repr__(&self) -> String {
        format!(
            "PyCounterStats(total_kmers={}, unique_kmers={}, kmer_length={}, canonical_mode={}, memory_usage={}, threads={})",
            self.total_kmers, self.unique_kmers, self.kmer_length, self.canonical_mode, self.memory_usage, self.threads
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
    /// `py.detach(..)` closures used by the heavy counting methods
    /// (`add_from_fastq` / `add_from_fasta`). `RustPyCounter` (a re-export of
    /// `rustkmer::hash::KmerCounter`) uses `dashmap::DashMap` for storage, which
    /// gives interior mutability — so incrementing counts through `&self` is
    /// sound under rayon's parallel workers (Phase 2, PCOUNT-03 / D-08).
    counter: Arc<RustPyCounter>,
    /// Phase 9 (PY-01): resolved thread count. `KmerCounter::new` discards its
    /// `_num_threads` argument (`src/hash/table.rs`), so the binding must
    /// remember the value it resolved in `new` to size each per-call engine
    /// config. Reported read-only through `get_stats().threads` (Phase 9
    /// WR-02) so the benchmark can verify the configuration actually applied;
    /// `PyCounter`'s own public surface stays unchanged.
    threads: usize,
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

        let counter = RustPyCounter::new(
            kmer_length_usize,
            canonical,
            initial_capacity,
            resolved_threads,
        )
        .map_err(|e| PyErr::new::<PyValueError, _>(format!("Failed to create counter: {}", e)))?;

        Ok(Self {
            counter: Arc::new(counter),
            threads: resolved_threads,
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
    // increment); the `py.detach` release/reacquire overhead would
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
    /// * `sequence` - DNA sequence string
    ///
    /// # Notes
    /// - Any length-k window containing a byte outside A/C/G/T
    ///   (case-insensitive) — including `N`, `n`, whitespace, or any other
    ///   byte — is skipped and never counted, matching the CLI skip-N
    ///   semantics (Phase 9 D2)
    /// - `get_stats().total_kmers` is therefore smaller on N-containing input
    ///   by design: skipped windows never advance the total
    ///
    /// # Example
    /// ```python
    /// counter.add_sequence("ATGCGATGCATGCGATGCATGCGATGCAT")
    /// ```
    // GIL not released: short-sequence workload (a single string's k-mers);
    // sub-millisecond for typical inputs. The `py.detach` release/reacquire
    // overhead would exceed the benefit for anything but very long sequences,
    // which should be loaded from a file via `add_from_fasta` /
    // `add_from_fastq` instead (those DO release the GIL).
    // Documented per RESEARCH Open Question 1.
    fn add_sequence(&self, sequence: &Bound<'_, pyo3::types::PyString>) -> PyResult<()> {
        let seq_str = sequence.to_str()?;
        let k = self.counter.kmer_length();

        // Phase 9 (PY-02 / D2): feed the RAW bytes to the ONE shared
        // extractor. It owns the non-ACGT rule — any length-k window
        // containing a byte outside A/C/G/T is skipped and counted, never
        // emitted — so the strip-and-join pre-filter that used to join the
        // flanks around an `N` (or a whitespace byte) is gone. The resulting
        // `total_kmers` drop on N-containing input is the ratified D2 change.
        //
        // ENGINE-03: window extraction goes through the ONE core extractor
        // (rolling for k <= 32, per-window u128 for 33..=64) instead of a
        // second local loop. The sink keeps the existing fail-loud overflow
        // contract: the first `u32::MAX` key aborts the pass and the error is
        // surfaced verbatim as a PyValueError.
        for_each_window(
            seq_str.as_bytes(),
            k,
            self.counter.canonical_mode(),
            |value| {
                self.counter.increment(value).map_err(|e| {
                    PyErr::new::<PyValueError, _>(format!("Failed to increment k-mer count: {}", e))
                })
            },
        )
        .map_err(|error| match error {
            // Unreachable: `PyCounter::new` validates k to 1..=64 before the
            // counter exists. Map it to the same invalid-k message rather than
            // panicking inside a pymethod.
            WindowError::InvalidK(invalid) => PyErr::new::<PyValueError, _>(format!(
                "Invalid k-mer size: {}. Must be between 1 and 64",
                invalid
            )),
            WindowError::Emit(error) => error,
        })?;

        Ok(())
    }

    /// Read and process k-mers from a FASTA file
    ///
    /// # Arguments
    /// * `file_path` - Path to FASTA file (supports .gz/.bz2/.xz compression)
    ///
    /// # Notes
    /// - Counts through the shared `CountEngine`, the same engine and strict
    ///   `bio` parser the CLI uses
    /// - Any length-k window containing a byte outside A/C/G/T is skipped and
    ///   never counted (Phase 9 D2 skip-N semantics)
    /// - Malformed FASTA raises `ValueError` carrying the parse context
    /// - Headers are ignored
    ///
    /// # Raises
    /// ValueError if the file cannot be read or parsed
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
        // owned, `Send` Rust types BEFORE entering the detach closure. The
        // closure cannot capture `&PyString` / `Bound<T>` / `PyObject` —
        // rayon workers are OS threads without GIL access. `to_str()?.to_owned()`
        // yields an owned `String` (Send); the `Arc<RustPyCounter>` clone is
        // likewise Send; the resolved thread count is a plain `usize`. The
        // closure moves all of them.
        let path_str = file_path.to_str()?.to_owned();
        let counter = self.counter.clone();
        let threads = self.threads;
        // Phase 9 (PY-01): bind the record kind to a local FIRST. Inlining
        // the variant literal in the call pushes the line past rustfmt's
        // 100-column width, which rewrites it into a block closure; the
        // local-binding form is format-stable.
        let kind = SequenceKind::Fasta;

        // Release the GIL for the duration of the file read + counting so
        // rayon workers actually run in parallel (D-08, PCOUNT-03). Without
        // this release the GIL would serialize the workers and the parallel
        // speedup would not materialize.
        //
        // API NOTE: pyo3 0.27.2 provides `Python::detach` as the canonical,
        // non-deprecated GIL-release API and enforces the `Ungil`
        // (= effectively `Send`) bound on the closure, so a capture that is
        // not `Send` is a compile error rather than a runtime hazard. The
        // deprecated predecessor is deliberately not used: it would fail the
        // `-D warnings` FOUND-01 clippy gate.
        py.detach(move || count_file_into_counter(&counter, &path_str, kind, threads))
            .map_err(|e: rustkmer::ProcessingError| {
                PyErr::new::<PyValueError, _>(format!("Failed to process FASTA: {}", e))
            })
    }

    /// Read and process k-mers from a FASTQ file
    ///
    /// # Arguments
    /// * `file_path` - Path to FASTQ file (supports .gz/.bz2/.xz compression)
    ///
    /// # Notes
    /// - Counts through the shared `CountEngine`, the same engine and strict
    ///   `bio` parser the CLI uses
    /// - Any length-k window containing a byte outside A/C/G/T is skipped and
    ///   never counted (Phase 9 D2 skip-N semantics)
    /// - Malformed FASTQ raises `ValueError` carrying the parse context
    /// - Headers and quality strings are ignored
    ///
    /// # Raises
    /// ValueError if the file cannot be read or parsed
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
        // owned, `Send` Rust types BEFORE entering the detach closure. The
        // closure cannot capture `&PyString` / `Bound<T>` / `PyObject` —
        // rayon workers are OS threads without GIL access. `to_str()?.to_owned()`
        // yields an owned `String` (Send); the `Arc<RustPyCounter>` clone is
        // likewise Send; the resolved thread count is a plain `usize`. The
        // closure moves all of them.
        let path_str = file_path.to_str()?.to_owned();
        let counter = self.counter.clone();
        let threads = self.threads;
        // Phase 9 (PY-01): bind the record kind to a local FIRST; see
        // `add_from_fasta` for the rustfmt format-stability rationale.
        let kind = SequenceKind::Fastq;

        // Release the GIL for the duration of the file read + counting so
        // rayon workers actually run in parallel (D-08, PCOUNT-03). Without
        // this release the GIL would serialize the workers and the parallel
        // speedup would not materialize.
        //
        // API NOTE: see `add_from_fasta` for the `py.detach` (not the
        // deprecated predecessor) rationale — pyo3 0.27.2.
        py.detach(move || count_file_into_counter(&counter, &path_str, kind, threads))
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
    /// - Sorts the k-mer snapshot exactly once with an in-place parallel
    ///   unstable sort, then writes through the single frozen `.rkdb` v2
    ///   header/entry writer — no second sort
    /// - The whole sort + write runs with the GIL released, so other Python
    ///   threads keep running during a large save (Phase 9, PY-01)
    /// - The emitted bytes are identical to the CLI `count` output for the
    ///   same input and thread-count independent
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
    fn save_database(
        &self,
        py: Python<'_>,
        file_path: &Bound<'_, pyo3::types::PyString>,
    ) -> PyResult<()> {
        // CRITICAL (T-02-11 / Pitfall 4): extract ALL Python arguments into
        // owned, `Send` Rust types BEFORE entering the detach closure. The
        // closure cannot capture `&PyString` / `Bound<T>` / `PyObject` —
        // rayon workers are OS threads without GIL access. The owned `String`
        // path and the cloned `Arc<RustPyCounter>` are both `Send`.
        let path_str = file_path.to_str()?.to_owned();
        let counter = self.counter.clone();

        // Release the GIL for the duration of the sort + write: sorting and
        // writing hundreds of millions of entries while holding the GIL would
        // block every Python thread for the whole save (PY-01). `PyErr` cannot
        // be built without the GIL, so the closure returns the private `Send`
        // error enum and it is mapped to `PyValueError` afterwards, keeping
        // the four user-visible messages verbatim.
        py.detach(move || save_database_on_counter(&counter, &path_str))
            .map_err(|e: SaveDatabaseError| PyErr::new::<PyValueError, _>(e.to_string()))
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
    /// - threads: Resolved rayon worker count (requested `threads` applied)
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
            threads: self.threads,
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

/// Count one FASTA/FASTQ file into `counter` through the shared engine.
///
/// Phase 9 (PY-01): every `add_from_*` call builds a fresh per-call engine
/// with `initial_capacity = 0` (the persistent counter already holds the
/// capacity), counts the file with the same strict `bio` parser and skip-N
/// extractor as the CLI, then folds the exact partition tables into the
/// shared counter through the checked merge bridge. Open/parse errors return
/// before the merge, so a failed call leaves the shared counter unchanged.
///
/// Designed to run inside a `py.detach(..)` closure: it takes only `Send`
/// types (the `Arc<RustPyCounter>`, an owned path `&str`, the record kind,
/// and the resolved thread count).
fn count_file_into_counter(
    counter: &Arc<RustPyCounter>,
    path: &str,
    kind: SequenceKind,
    threads: usize,
) -> Result<(), rustkmer::ProcessingError> {
    let config = EngineConfig::new(counter.kmer_length(), counter.canonical_mode(), threads, 0);
    let mut engine = CountEngine::new(config)?;
    engine.count_file(Path::new(path), kind)?;
    engine.finish()?.merge_into(counter)?;
    Ok(())
}

/// Failure modes of the detached `save_database` body.
///
/// The closure passed to `py.detach` runs without the GIL, so it cannot build
/// a `PyErr`; it returns this private enum instead and the Python-facing
/// method maps each variant to the exact `ValueError` message that existing
/// callers already match on. Every payload is a `String`, so the enum is
/// `Send` and legal as a detach return value.
#[derive(Debug)]
enum SaveDatabaseError {
    /// The counter holds no k-mers, so there is nothing to write.
    Empty,
    /// Building the `RKDatabase` from the sorted snapshot failed.
    Database(String),
    /// Creating the output file failed.
    CreateFile(String),
    /// Writing (or flushing) the database failed.
    Write(String),
}

impl std::fmt::Display for SaveDatabaseError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Empty => f.write_str("Cannot save empty database. Add k-mers first."),
            Self::Database(e) => write!(f, "Failed to create database: {}", e),
            Self::CreateFile(e) => write!(f, "Failed to create file: {}", e),
            Self::Write(e) => write!(f, "Failed to write database: {}", e),
        }
    }
}

/// Save `counter`'s snapshot to `path` as a sorted `.rkdb` v2 database.
///
/// Phase 9 (PY-01): designed to run inside a `py.detach(..)` closure, so it
/// takes only `Send` types. It snapshots the counter, returns `Empty` when
/// there is nothing to write, sorts the pairs exactly once in place with
/// rayon's parallel unstable sort, hands the caller-proven ascending order to
/// the single frozen `format.rs` sorted-input constructor (which never sorts
/// again), and writes through the frozen header/entry writers with an explicit
/// final flush. Counter keys are unique, so the resulting order is a strict
/// total order and the emitted bytes are thread-count independent.
fn save_database_on_counter(
    counter: &Arc<RustPyCounter>,
    path: &str,
) -> Result<(), SaveDatabaseError> {
    use rayon::prelude::*;
    use rustkmer::database::format::RKDatabase;
    use std::fs::File;
    use std::io::{BufWriter, Write};

    // Snapshot order is whatever the sharded map iterates. The sort below is
    // the ONLY sort performed anywhere on the save path.
    let mut pairs = counter.get_all_counts();
    if pairs.is_empty() {
        return Err(SaveDatabaseError::Empty);
    }

    // Phase 9 (PY-01): one in-place parallel unstable sort — the Phase 8
    // unstable/parallel mandate. No stable re-sort, no second sort downstream.
    pairs.par_sort_unstable_by_key(|&(kmer, _)| kmer);

    let db = RKDatabase::from_sorted_kmer_pairs(
        pairs,
        counter.kmer_length() as u8,
        counter.canonical_mode(),
    )
    .map_err(|e| SaveDatabaseError::Database(e.to_string()))?;

    let file =
        File::create(Path::new(path)).map_err(|e| SaveDatabaseError::CreateFile(e.to_string()))?;
    let mut writer = BufWriter::new(file);

    db.write_to(&mut writer)
        .map_err(|e| SaveDatabaseError::Write(e.to_string()))?;

    // A failed final write must never be silent (T-08-04).
    writer
        .flush()
        .map_err(|e| SaveDatabaseError::Write(e.to_string()))?;

    Ok(())
}
