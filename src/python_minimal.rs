//! Minimal RustKmer Python bindings for testing

use pyo3::prelude::*;
use pyo3::exceptions::{PyRuntimeError, PyValueError, PyIOError, PyFileNotFoundError, PyMemoryError, PyAssertionError};
use std::sync::{Arc, atomic::{AtomicUsize, Ordering}};
use parking_lot::RwLock;
use std::thread;
use std::time::Duration;

/// Minimal Kmer counter for testing
use std::collections::HashMap;

/// Python wrapper for k-mer counting
#[pyclass(name = "KmerCounter")]
#[derive(Clone)]
pub struct KmerCounter {
    k: usize,
    canonical: bool,
    threads: usize,
    counts: HashMap<String, u64>,
}

#[pymethods]
impl KmerCounter {
    /// Create a new KmerCounter
    #[new]
    #[pyo3(signature = (k, canonical=false, threads=1))]
    fn new(k: usize, canonical: bool, threads: usize) -> PyResult<Self> {
        if k == 0 || k > 128 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "K-mer size must be between 1 and 128"
            ));
        }

        let threads = if threads == 0 { 1 } else { threads };
        if threads > 512 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Thread count cannot exceed 512"
            ));
        }

        Ok(Self {
            k,
            canonical,
            threads,
            counts: HashMap::new(),
        })
    }

    /// Get the k-mer size
    #[getter]
    fn get_k(&self) -> usize {
        self.k
    }

    /// Get canonical mode flag
    #[getter]
    fn get_canonical(&self) -> bool {
        self.canonical
    }

    /// Get thread count
    #[getter]
    fn get_threads(&self) -> usize {
        self.threads
    }

    /// Count k-mers in a string and return a dictionary of counts
    fn count_string(&mut self, sequence: &str) -> PyResult<HashMap<String, u64>> {
        // Clean sequence: remove whitespace and convert to uppercase
        let clean_seq: String = sequence.chars()
            .filter(|c| !c.is_whitespace())
            .map(|c| c.to_ascii_uppercase())
            .collect();

        if clean_seq.len() < self.k {
            self.counts.clear();
            return Ok(self.counts.clone());
        }

        self.counts.clear();

        for i in 0..=clean_seq.len() - self.k {
            let kmer = &clean_seq[i..i + self.k];

            // Skip if contains N
            if kmer.contains('N') {
                continue;
            }

            let final_kmer = if self.canonical {
                // Get reverse complement
                let rev_comp: String = kmer.chars()
                    .map(|c| match c {
                        'A' => 'T',
                        'T' => 'A',
                        'C' => 'G',
                        'G' => 'C',
                        _ => c,
                    })
                    .rev()
                    .collect();

                // Use lexicographically smaller
                if kmer.to_string() < rev_comp { kmer.to_string() } else { rev_comp }
            } else {
                kmer.to_string()
            };

            *self.counts.entry(final_kmer).or_insert(0) += 1;
        }

        Ok(self.counts.clone())
    }

    /// Get count for a specific k-mer
    fn get_count(&self, kmer: &str) -> u64 {
        self.counts.get(kmer).copied().unwrap_or(0)
    }

    /// Get total k-mer count
    fn get_total_count(&self) -> u64 {
        self.counts.values().sum()
    }

    /// Get number of unique k-mers
    fn get_unique_count(&self) -> usize {
        self.counts.len()
    }

    /// Get all k-mer counts
    fn get_all_counts(&self) -> HashMap<String, u64> {
        self.counts.clone()
    }

    /// Get top k-mers by count
    fn get_top_kmers(&self, n: usize) -> Vec<(String, u64)> {
        let mut items: Vec<(String, u64)> = self.counts.iter()
            .map(|(k, v)| (k.clone(), *v))
            .collect();
        items.sort_by(|a, b| b.1.cmp(&a.1));
        items.into_iter().take(n).collect()
    }

    /// Count k-mers from multiple sequences
    fn count_stream(&mut self, sequences: Vec<String>) -> PyResult<HashMap<String, u64>> {
        let mut all_counts = HashMap::new();

        for seq in sequences {
            // Temporarily store current counts
            let old_counts = std::mem::take(&mut self.counts);

            // Count this sequence
            let seq_counts = self.count_string(&seq)?;

            // Merge with previous counts
            for (kmer, count) in seq_counts {
                *all_counts.entry(kmer).or_insert(0) += count;
            }

            // Restore counts
            self.counts = old_counts;
        }

        // Update final counts
        self.counts = all_counts.clone();
        Ok(all_counts)
    }

    /// Count k-mers from a file with format validation
    fn count_file(&mut self, file_path: &str) -> PyResult<HashMap<String, u64>> {
        use std::path::Path;

        // Validate file path exists
        let path = Path::new(file_path);
        if !path.exists() {
            return Err(PyFileNotFoundError::new_err(format!(
                "File not found: {}", file_path
            )));
        }

        // Validate file format by extension
        let extension = path.extension()
            .and_then(|ext| ext.to_str())
            .unwrap_or("");

        match extension.to_lowercase().as_str() {
            "fa" | "fasta" | "fq" | "fastq" | "fna" | "ffn" | "faa" | "frn" => {
                // Supported formats
            }
            "gz" | "gzip" => {
                // Check if it's a compressed FASTA/FASTQ
                let stem = path.file_stem()
                    .and_then(|s| s.to_str())
                    .unwrap_or("");

                if !stem.ends_with(".fa") && !stem.ends_with(".fasta") &&
                   !stem.ends_with(".fq") && !stem.ends_with(".fastq") {
                    return Err(PyValueError::new_err(format!(
                        "Compressed file must be FASTA or FASTQ: {}", file_path
                    )));
                }
            }
            "bz2" => {
                // Similar check for bzip2
                let stem = path.file_stem()
                    .and_then(|s| s.to_str())
                    .unwrap_or("");

                if !stem.ends_with(".fa") && !stem.ends_with(".fasta") &&
                   !stem.ends_with(".fq") && !stem.ends_with(".fastq") {
                    return Err(PyValueError::new_err(format!(
                        "Compressed file must be FASTA or FASTQ: {}", file_path
                    )));
                }
            }
            _ => {
                return Err(PyValueError::new_err(format!(
                    "Unsupported file format: {}. Supported formats: FASTA (.fa, .fasta, .fna), FASTQ (.fq, .fastq), and their compressed versions",
                    file_path
                )));
            }
        }

        // For now, just read the file as text and process
        // In a full implementation, this would use the bio crate for proper FASTA/FASTQ parsing
        match std::fs::read_to_string(file_path) {
            Ok(content) => {
                // Simple validation: check if it looks like FASTA/FASTQ
                if content.is_empty() {
                    return Ok(HashMap::new());
                }

                // Basic format validation
                let lines: Vec<&str> = content.lines().collect();
                if lines.is_empty() {
                    return Ok(HashMap::new());
                }

                // Check if first line indicates FASTA or FASTQ
                let first_line = lines[0];
                if !first_line.starts_with('>') && !first_line.starts_with('@') {
                    return Err(PyValueError::new_err(format!(
                        "Invalid file format. Expected FASTA (starts with >) or FASTQ (starts with @): {}",
                        file_path
                    )));
                }

                // Count k-mers from the file content
                // For simplicity, just concatenate all sequence lines
                let mut sequence = String::new();
                let in_header = first_line.starts_with('@'); // FASTQ

                for (i, line) in lines.iter().enumerate() {
                    if line.starts_with('>') || (line.starts_with('@') && (i % 4 == 0)) {
                        // Header line, skip
                        continue;
                    } else if line.starts_with('+') || (in_header && i % 4 == 2) {
                        // FASTQ quality line or separator, skip
                        continue;
                    } else {
                        // Sequence line
                        sequence.push_str(line);
                    }
                }

                self.count_string(&sequence)
            }
            Err(e) => {
                Err(PyIOError::new_err(format!(
                    "Failed to read file '{}': {}", file_path, e
                )))
            }
        }
    }
}

// ============================================================================
// Thread Pool Configuration
// ============================================================================

/// Thread pool configuration for parallel operations
#[pyclass(name = "ThreadPoolConfig")]
#[derive(Clone, Debug)]
pub struct ThreadPoolConfig {
    /// Number of threads to use (0 for auto-detect)
    #[pyo3(get)]
    num_threads: usize,
    /// Thread stack size in bytes
    #[pyo3(get)]
    stack_size: Option<usize>,
    /// Thread timeout in seconds
    #[pyo3(get)]
    timeout_secs: Option<u64>,
    /// Whether threads should be daemon threads
    #[pyo3(get)]
    daemon_threads: bool,
    /// Thread affinity settings (CPU cores)
    #[pyo3(get)]
    cpu_affinity: Option<Vec<usize>>,
}

#[pymethods]
impl ThreadPoolConfig {
    /// Create a new thread pool configuration
    #[new]
    #[pyo3(signature = (num_threads=0, stack_size=None, timeout_secs=None, daemon_threads=true, cpu_affinity=None))]
    fn new(
        num_threads: usize,
        stack_size: Option<usize>,
        timeout_secs: Option<u64>,
        daemon_threads: bool,
        cpu_affinity: Option<Vec<usize>>,
    ) -> PyResult<Self> {
        if num_threads > 512 {
            return Err(PyValueError::new_err(
                "Number of threads cannot exceed 512"
            ));
        }

        if let Some(ref affinity) = cpu_affinity {
            if affinity.is_empty() {
                return Err(PyValueError::new_err(
                    "CPU affinity list cannot be empty"
                ));
            }
            for &core in affinity {
                if core >= num_cpus::get() {
                    return Err(PyValueError::new_err(format!(
                        "CPU core {} exceeds available cores ({})",
                        core, num_cpus::get()
                    )));
                }
            }
        }

        Ok(Self {
            num_threads: if num_threads == 0 {
                // Auto-detect based on CPU cores
                std::cmp::max(1, num_cpus::get())
            } else {
                num_threads
            },
            stack_size,
            timeout_secs,
            daemon_threads,
            cpu_affinity,
        })
    }

    /// Create a configuration for single-threaded operations
    #[staticmethod]
    fn single_threaded() -> Self {
        Self {
            num_threads: 1,
            stack_size: None,
            timeout_secs: None,
            daemon_threads: true,
            cpu_affinity: None,
        }
    }

    /// Create a configuration for maximum parallelism
    #[staticmethod]
    fn max_parallelism() -> Self {
        let num_threads = num_cpus::get();
        Self {
            num_threads,
            stack_size: Some(8 * 1024 * 1024), // 8MB stack
            timeout_secs: Some(300), // 5 minutes
            daemon_threads: false,
            cpu_affinity: Some((0..num_threads).collect()),
        }
    }

    /// Create a configuration for I/O-bound operations
    #[staticmethod]
    fn io_bound() -> Self {
        Self {
            num_threads: std::cmp::max(4, num_cpus::get() * 2),
            stack_size: Some(2 * 1024 * 1024), // 2MB stack
            timeout_secs: Some(600), // 10 minutes
            daemon_threads: true,
            cpu_affinity: None,
        }
    }

    /// Create a configuration for CPU-bound operations
    #[staticmethod]
    fn cpu_bound() -> Self {
        Self {
            num_threads: num_cpus::get(),
            stack_size: Some(16 * 1024 * 1024), // 16MB stack
            timeout_secs: Some(120), // 2 minutes
            daemon_threads: false,
            cpu_affinity: Some((0..num_cpus::get()).collect()),
        }
    }

    /// Get the recommended number of threads based on workload type
    #[staticmethod]
    fn recommended_threads(workload_type: &str) -> PyResult<usize> {
        match workload_type.to_lowercase().as_str() {
            "single" => Ok(1),
            "io" | "iobound" => Ok(std::cmp::max(4, num_cpus::get() * 2)),
            "cpu" | "cpubound" => Ok(num_cpus::get()),
            "mixed" => Ok(std::cmp::max(2, num_cpus::get())),
            _ => Err(PyValueError::new_err(format!(
                "Unknown workload type: {}. Use 'single', 'io', 'cpu', or 'mixed'",
                workload_type
            ))),
        }
    }

    /// Validate the configuration
    fn validate(&self) -> PyResult<()> {
        if self.num_threads == 0 {
            return Err(PyValueError::new_err(
                "Number of threads cannot be 0"
            ));
        }

        if self.num_threads > 512 {
            return Err(PyValueError::new_err(
                "Number of threads cannot exceed 512 for stability"
            ));
        }

        if let Some(timeout) = self.timeout_secs {
            if timeout == 0 {
                return Err(PyValueError::new_err(
                    "Timeout cannot be 0 seconds"
                ));
            }
            if timeout > 3600 {
                return Err(PyValueError::new_err(
                    "Timeout cannot exceed 1 hour (3600 seconds)"
                ));
            }
        }

        if let Some(stack_size) = self.stack_size {
            if stack_size < 1024 * 1024 {
                return Err(PyValueError::new_err(
                    "Stack size must be at least 1MB"
                ));
            }
            if stack_size > 100 * 1024 * 1024 {
                return Err(PyValueError::new_err(
                    "Stack size cannot exceed 100MB"
                ));
            }
        }

        Ok(())
    }

    /// Get the effective timeout as a Duration
    fn get_timeout_duration(&self) -> Option<Duration> {
        self.timeout_secs.map(Duration::from_secs)
    }

    /// Check if this configuration uses daemon threads
    fn is_daemon(&self) -> bool {
        self.daemon_threads
    }

    /// Check if CPU affinity is configured
    fn has_cpu_affinity(&self) -> bool {
        self.cpu_affinity.is_some()
    }

    /// String representation
    fn __repr__(&self) -> String {
        format!(
            "ThreadPoolConfig(num_threads={}, stack_size={:?}, timeout_secs={:?}, daemon_threads={}, cpu_affinity={:?})",
            self.num_threads, self.stack_size, self.timeout_secs, self.daemon_threads, self.cpu_affinity
        )
    }

    /// String representation
    fn __str__(&self) -> String {
        format!(
            "ThreadPool: {} threads{}{}{}",
            self.num_threads,
            if let Some(timeout) = self.timeout_secs {
                format!(", {}s timeout", timeout)
            } else {
                String::new()
            },
            if self.daemon_threads {
                String::from(", daemon")
            } else {
                String::new()
            },
            if self.cpu_affinity.is_some() {
                String::from(", CPU affinity")
            } else {
                String::new()
            }
        )
    }
}

/// Global thread pool manager
static GLOBAL_THREAD_CONFIG: parking_lot::RwLock<Option<ThreadPoolConfig>> = parking_lot::RwLock::new(None);

/// Set the global thread pool configuration
#[pyfunction]
fn set_global_thread_config(config: &ThreadPoolConfig) -> PyResult<()> {
    config.validate()?;
    let mut global_config = GLOBAL_THREAD_CONFIG.write();
    *global_config = Some(config.clone());
    Ok(())
}

/// Get the current global thread pool configuration
#[pyfunction]
fn get_global_thread_config() -> Option<ThreadPoolConfig> {
    let global_config = GLOBAL_THREAD_CONFIG.read();
    global_config.clone()
}

/// Reset the global thread pool configuration to default
#[pyfunction]
fn reset_global_thread_config() {
    let mut global_config = GLOBAL_THREAD_CONFIG.write();
    *global_config = None;
}

/// Apply thread pool configuration to the current thread
#[pyfunction]
fn apply_thread_config(config: &ThreadPoolConfig) -> PyResult<()> {
    // This would be used to configure the current thread based on the config
    // In a real implementation, this might set thread priority, affinity, etc.

    if let Some(ref affinity) = config.cpu_affinity {
        // Note: Setting CPU affinity is platform-specific
        // This is a placeholder for the actual implementation
        #[cfg(target_os = "linux")]
        {
            use libc::{cpu_set_t, sched_setaffinity, sched_getpid};
            use std::mem;

            let mut cpuset: cpu_set_t = unsafe { mem::zeroed() };
            for &core in affinity {
                if core < 1024 { // CPU_SET typically supports up to 1024 cores
                    unsafe {
                        libc::CPU_SET(core, &mut cpuset);
                    }
                }
            }

            let pid = unsafe { sched_getpid() };
            let result = unsafe {
                sched_setaffinity(pid, mem::size_of::<cpu_set_t>(), &cpuset)
            };

            if result != 0 {
                return Err(PyIOError::new_err(format!(
                    "Failed to set CPU affinity: {}", std::io::Error::last_os_error()
                )));
            }
        }
    }

    Ok(())
}

/// Get information about the current system's threading capabilities
#[pyfunction]
fn get_system_thread_info() -> std::collections::HashMap<String, pyo3::Py<pyo3::PyAny>> {
    Python::with_gil(|py| {
        let mut info = std::collections::HashMap::new();

        // Number of logical CPU cores
        info.insert("logical_cores".to_string(), num_cpus::get().into_py(py));

        // Physical cores (approximation - this varies by system)
        info.insert("physical_cores".to_string(), (num_cpus::get() / 2).into_py(py));

        // Recommended threads for different workloads
        info.insert("recommended_cpu_threads".to_string(), num_cpus::get().into_py(py));
        info.insert("recommended_io_threads".to_string(),
                   std::cmp::max(4, num_cpus::get() * 2).into_py(py));
        info.insert("recommended_mixed_threads".to_string(),
                   std::cmp::max(2, num_cpus::get()).into_py(py));

        // System limits
        info.insert("max_safe_threads".to_string(), 512.into_py(py));
        info.insert("default_stack_size".to_string(), (8 * 1024 * 1024).into_py(py));

        info
    })
}

// ============================================================================
// Thread-Safe Database Operations
// ============================================================================

use std::path::PathBuf;

/// Thread-safe database manager for concurrent access
#[pyclass(name = "ThreadSafeDatabaseManager")]
#[derive(Clone)]
pub struct ThreadSafeDatabaseManager {
    /// Internal database registry
    databases: Arc<parking_lot::RwLock<HashMap<String, ThreadSafeDatabase>>>,
    /// Default configuration for new databases
    default_config: Option<ThreadPoolConfig>,
}

/// Thread-safe database wrapper
#[pyclass(name = "ThreadSafeDatabase")]
#[derive(Clone)]
pub struct ThreadSafeDatabase {
    /// Database path
    #[pyo3(get)]
    path: String,
    /// Database is loaded flag
    loaded: Arc<AtomicUsize>,
    /// Query count
    query_count: Arc<AtomicUsize>,
    /// Last access time (timestamp)
    last_access: Arc<AtomicUsize>,
    /// Database metadata
    metadata: Arc<parking_lot::RwLock<HashMap<String, String>>>,
}

#[pymethods]
impl ThreadSafeDatabaseManager {
    /// Create a new thread-safe database manager
    #[new]
    #[pyo3(signature = (default_config=None))]
    fn new(default_config: Option<ThreadPoolConfig>) -> Self {
        Self {
            databases: Arc::new(parking_lot::RwLock::new(HashMap::new())),
            default_config,
        }
    }

    /// Register a database for thread-safe access
    #[pyo3(signature = (path, name=None))]
    fn register_database(&self, path: String, name: Option<String>) -> PyResult<String> {
        let db_name = name.unwrap_or_else(|| {
            // Generate a unique name based on path
            format!("db_{}", path.replace('/', "_").replace('\\', "_"))
        });

        let db = ThreadSafeDatabase {
            path: path.clone(),
            loaded: Arc::new(AtomicUsize::new(0)),
            query_count: Arc::new(AtomicUsize::new(0)),
            last_access: Arc::new(AtomicUsize::new(
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_secs() as usize
            )),
            metadata: Arc::new(parking_lot::RwLock::new(HashMap::new())),
        };

        let mut databases = self.databases.write();
        databases.insert(db_name.clone(), db);
        Ok(db_name)
    }

    /// Get a database by name
    fn get_database(&self, name: &str) -> Option<ThreadSafeDatabase> {
        let databases = self.databases.read();
        databases.get(name).cloned()
    }

    /// Unregister a database
    fn unregister_database(&self, name: &str) -> PyResult<bool> {
        let mut databases = self.databases.write();
        Ok(databases.remove(name).is_some())
    }

    /// List all registered databases
    fn list_databases(&self) -> Vec<String> {
        let databases = self.databases.read();
        databases.keys().cloned().collect()
    }

    /// Get database statistics for all databases
    fn get_all_stats(&self) -> PyResult<std::collections::HashMap<String, pyo3::Py<pyo3::PyAny>>> {
        Python::with_gil(|py| {
            let databases = self.databases.read();
            let mut stats = std::collections::HashMap::new();

            for (name, db) in databases.iter() {
                let mut db_stats = std::collections::HashMap::new();
                db_stats.insert("path".to_string(), db.path.clone().into_py(py));
                db_stats.insert("loaded".to_string(), (db.loaded.load(Ordering::Relaxed) > 0).into_py(py));
                db_stats.insert("query_count".to_string(), db.query_count.load(Ordering::Relaxed).into_py(py));
                db_stats.insert("last_access".to_string(), db.last_access.load(Ordering::Relaxed).into_py(py));
                stats.insert(name.clone(), db_stats.into_py(py));
            }

            Ok(stats)
        })
    }

    /// Clear all registered databases
    fn clear(&self) {
        let mut databases = self.databases.write();
        databases.clear();
    }
}

#[pymethods]
impl ThreadSafeDatabase {
    /// Load the database (thread-safe)
    fn load(&self) -> PyResult<()> {
        // Simulate loading - in real implementation, this would load the RKDB file
        self.loaded.store(1, Ordering::Relaxed);
        self.update_last_access();

        // Store metadata
        let mut metadata = self.metadata.write();
        metadata.insert("loaded_at".to_string(),
                      std::time::SystemTime::now()
                          .duration_since(std::time::UNIX_EPOCH)
                          .unwrap_or_default()
                          .as_secs()
                          .to_string());

        Ok(())
    }

    /// Unload the database (thread-safe)
    fn unload(&self) {
        self.loaded.store(0, Ordering::Relaxed);
        let mut metadata = self.metadata.write();
        metadata.clear();
    }

    /// Check if database is loaded
    fn is_loaded(&self) -> bool {
        self.loaded.load(Ordering::Relaxed) > 0
    }

    /// Query a k-mer in the database (thread-safe)
    fn query(&self, kmer: &str) -> PyResult<u32> {
        if !self.is_loaded() {
            return Err(PyRuntimeError::new_err("Database not loaded"));
        }

        // Simulate query - in real implementation, this would query the RKDB
        self.increment_query_count();

        // Simple hash-based simulation for testing
        let hash = kmer.chars().map(|c| c as u32).sum::<u32>();
        Ok(hash % 1000) // Return a count between 0-999
    }

    /// Query multiple k-mers (thread-safe batch operation)
    fn query_batch(&self, kmers: Vec<String>) -> PyResult<std::collections::HashMap<String, u32>> {
        if !self.is_loaded() {
            return Err(PyRuntimeError::new_err("Database not loaded"));
        }

        let mut results = std::collections::HashMap::new();
        for kmer in kmers {
            let count = self.query(&kmer)?;
            results.insert(kmer, count);
        }
        Ok(results)
    }

    /// Check if a k-mer exists in the database
    fn exists(&self, kmer: &str) -> bool {
        if !self.is_loaded() {
            return false;
        }

        self.increment_query_count();

        // Simple existence check based on k-mer properties
        kmer.len() >= 3 && kmer.chars().all(|c| matches!(c, 'A' | 'C' | 'G' | 'T'))
    }

    /// Get database metadata
    fn get_metadata(&self) -> PyResult<std::collections::HashMap<String, String>> {
        let metadata = self.metadata.read();
        Ok(metadata.clone())
    }

    /// Update metadata (thread-safe)
    fn set_metadata(&self, key: String, value: String) -> PyResult<()> {
        let mut metadata = self.metadata.write();
        metadata.insert(key, value);
        Ok(())
    }

    /// Get query statistics
    fn get_query_stats(&self) -> PyResult<std::collections::HashMap<String, pyo3::Py<pyo3::PyAny>>> {
        Python::with_gil(|py| {
            let mut stats = std::collections::HashMap::new();
            stats.insert("query_count".to_string(), self.query_count.load(Ordering::Relaxed).into_py(py));
            stats.insert("last_access".to_string(), self.last_access.load(Ordering::Relaxed).into_py(py));
            stats.insert("loaded".to_string(), self.is_loaded().into_py(py));
            Ok(stats)
        })
    }

    /// Reset query statistics
    fn reset_stats(&self) {
        self.query_count.store(0, Ordering::Relaxed);
        self.last_access.store(
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs() as usize,
            Ordering::Relaxed
        );
    }

    /// String representation
    fn __repr__(&self) -> String {
        format!(
            "ThreadSafeDatabase(path='{}', loaded={}, queries={})",
            self.path,
            self.is_loaded(),
            self.query_count.load(Ordering::Relaxed)
        )
    }

    /// String representation
    fn __str__(&self) -> String {
        if self.is_loaded() {
            format!("Database: {} (loaded, {} queries)",
                   PathBuf::from(&self.path).file_name()
                       .and_then(|n| n.to_str())
                       .unwrap_or(&self.path),
                   self.query_count.load(Ordering::Relaxed))
        } else {
            format!("Database: {} (not loaded)",
                   PathBuf::from(&self.path).file_name()
                       .and_then(|n| n.to_str())
                       .unwrap_or(&self.path))
        }
    }
}

impl ThreadSafeDatabase {
    /// Update the last access time
    fn update_last_access(&self) {
        self.last_access.store(
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs() as usize,
            Ordering::Relaxed
        );
    }

    /// Increment the query count
    fn increment_query_count(&self) {
        self.query_count.fetch_add(1, Ordering::Relaxed);
        self.update_last_access();
    }
}

/// Thread pool statistics (thread-safe implementation)
#[pyclass(name = "ThreadPoolStats")]
#[derive(Clone, Debug, Default)]
pub struct ThreadPoolStats {
    // Atomic counters stored internally
    stats: Arc<ThreadStatsInner>,
}

/// Internal structure for thread-safe statistics
#[derive(Debug, Default)]
struct ThreadStatsInner {
    active_threads: AtomicUsize,
    completed_tasks: AtomicUsize,
    failed_tasks: AtomicUsize,
    total_runtime_ms: AtomicUsize,
}

#[pymethods]
impl ThreadPoolStats {
    /// Create new thread pool statistics
    #[new]
    fn new() -> Self {
        Self {
            stats: Arc::new(ThreadStatsInner::default()),
        }
    }

    /// Get the number of active threads
    fn get_active_threads(&self) -> usize {
        self.stats.active_threads.load(Ordering::Relaxed)
    }

    /// Get the number of completed tasks
    fn get_completed_tasks(&self) -> usize {
        self.stats.completed_tasks.load(Ordering::Relaxed)
    }

    /// Get the number of failed tasks
    fn get_failed_tasks(&self) -> usize {
        self.stats.failed_tasks.load(Ordering::Relaxed)
    }

    /// Get the total runtime in milliseconds
    fn get_total_runtime_ms(&self) -> usize {
        self.stats.total_runtime_ms.load(Ordering::Relaxed)
    }

    /// Increment active threads
    fn increment_active_threads(&self) {
        self.stats.active_threads.fetch_add(1, Ordering::Relaxed);
    }

    /// Decrement active threads
    fn decrement_active_threads(&self) {
        self.stats.active_threads.fetch_sub(1, Ordering::Relaxed);
    }

    /// Increment completed tasks
    fn increment_completed_tasks(&self) {
        self.stats.completed_tasks.fetch_add(1, Ordering::Relaxed);
    }

    /// Increment failed tasks
    fn increment_failed_tasks(&self) {
        self.stats.failed_tasks.fetch_add(1, Ordering::Relaxed);
    }

    /// Add runtime
    fn add_runtime_ms(&self, runtime_ms: usize) {
        self.stats.total_runtime_ms.fetch_add(runtime_ms, Ordering::Relaxed);
    }

    /// Reset all statistics
    fn reset(&self) {
        self.stats.active_threads.store(0, Ordering::Relaxed);
        self.stats.completed_tasks.store(0, Ordering::Relaxed);
        self.stats.failed_tasks.store(0, Ordering::Relaxed);
        self.stats.total_runtime_ms.store(0, Ordering::Relaxed);
    }

    /// Get statistics as a dictionary
    fn to_dict(&self) -> PyResult<std::collections::HashMap<String, pyo3::Py<pyo3::PyAny>>> {
        Python::with_gil(|py| {
            let mut dict = std::collections::HashMap::new();
            dict.insert("active_threads".to_string(), self.get_active_threads().into_py(py));
            dict.insert("completed_tasks".to_string(), self.get_completed_tasks().into_py(py));
            dict.insert("failed_tasks".to_string(), self.get_failed_tasks().into_py(py));
            dict.insert("total_runtime_ms".to_string(), self.get_total_runtime_ms().into_py(py));
            Ok(dict)
        })
    }

    /// String representation
    fn __repr__(&self) -> String {
        format!(
            "ThreadPoolStats(active_threads={}, completed_tasks={}, failed_tasks={}, total_runtime_ms={})",
            self.get_active_threads(),
            self.get_completed_tasks(),
            self.get_failed_tasks(),
            self.get_total_runtime_ms()
        )
    }
}

// ============================================================================
// Database Class for User Story 2
// ============================================================================

/// Database class for querying k-mer databases
#[pyclass(name = "Database")]
#[derive(Clone)]
pub struct Database {
    /// Database file path
    #[pyo3(get)]
    path: String,
    /// Whether the database is loaded
    loaded: bool,
    /// K-mer size used in the database
    #[pyo3(get)]
    kmer_size: Option<usize>,
    /// Total k-mers in the database
    #[pyo3(get)]
    total_kmers: Option<u64>,
    /// Unique k-mers in the database
    #[pyo3(get)]
    unique_kmers: Option<u64>,
    /// Database metadata
    metadata: std::collections::HashMap<String, String>,
}

#[pymethods]
impl Database {
    /// Create a new Database instance
    #[new]
    #[pyo3(signature = (path, preload=true))]
    fn new(path: String, preload: bool) -> PyResult<Self> {
        let mut db = Self {
            path,
            loaded: false,
            kmer_size: None,
            total_kmers: None,
            unique_kmers: None,
            metadata: std::collections::HashMap::new(),
        };

        // Validate path exists
        if !std::path::Path::new(&db.path).exists() {
            return Err(PyFileNotFoundError::new_err(format!(
                "Database file not found: {}", db.path
            )));
        }

        // Auto-load if requested
        if preload {
            db.load()?;
        }

        Ok(db)
    }

    /// Load the database from file
    fn load(&mut self) -> PyResult<()> {
        if self.loaded {
            return Ok(());
        }

        // For now, simulate loading - in real implementation this would load RKDB format
        // Check file extension
        let path = std::path::Path::new(&self.path);
        if !path.extension().and_then(|s| s.to_str()).unwrap_or("").ends_with("rkdb") {
            return Err(PyValueError::new_err(format!(
                "Invalid database format. Expected .rkdb file: {}", self.path
            )));
        }

        // Simulate database metadata
        self.kmer_size = Some(31); // Default k-mer size
        self.total_kmers = Some(1000000); // Simulated total
        self.unique_kmers = Some(500000); // Simulated unique
        self.metadata.insert("format".to_string(), "RKDB".to_string());
        self.metadata.insert("version".to_string(), "2.0".to_string());
        self.metadata.insert("created_at".to_string(), "2024-01-01".to_string());

        self.loaded = true;
        Ok(())
    }

    /// Query a single k-mer in the database
    fn query(&self, kmer: &str) -> PyResult<QueryResult> {
        if !self.loaded {
            return Err(PyRuntimeError::new_err("Database not loaded"));
        }

        // Validate k-mer
        if kmer.is_empty() {
            return Err(PyValueError::new_err("Empty k-mer sequence"));
        }

        if let Some(k) = self.kmer_size {
            if kmer.len() != k {
                return Err(PyValueError::new_err(format!(
                    "Invalid k-mer length: expected {}, got {}", k, kmer.len()
                )));
            }
        }

        // Check for invalid characters
        if !kmer.chars().all(|c| matches!(c, 'A' | 'T' | 'C' | 'G' | 'N')) {
            return Err(PyValueError::new_err("Invalid characters in k-mer"));
        }

        // Simulate query - return deterministic result based on k-mer hash
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut hasher = DefaultHasher::new();
        kmer.hash(&mut hasher);
        let hash = hasher.finish();

        let count = (hash % 1000) as u32; // Simulated count 0-999
        let exists = count > 0 && !kmer.contains('N');

        Ok(QueryResult::new(
            kmer.to_string(),
            count,
            exists,
            Some(format!("queried_at_{}", std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_secs()))
        ))
    }

    /// Query multiple k-mers in batch
    fn query_batch(&self, kmers: Vec<String>) -> PyResult<std::collections::HashMap<String, QueryResult>> {
        if !self.loaded {
            return Err(PyRuntimeError::new_err("Database not loaded"));
        }

        let mut results = std::collections::HashMap::new();
        for kmer in kmers {
            let result = self.query(&kmer)?;
            results.insert(kmer, result);
        }
        Ok(results)
    }

    /// Check if a k-mer exists in the database
    fn exists(&self, kmer: &str) -> PyResult<bool> {
        if !self.loaded {
            return Err(PyRuntimeError::new_err("Database not loaded"));
        }

        // Quick existence check based on k-mer properties
        // In real implementation, this would be more efficient than query()
        if kmer.is_empty() || kmer.contains('N') {
            return Ok(false);
        }

        if let Some(k) = self.kmer_size {
            if kmer.len() != k {
                return Err(PyValueError::new_err(format!(
                    "Invalid k-mer length: expected {}, got {}", k, kmer.len()
                )));
            }
        }

        // Simulate existence check
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut hasher = DefaultHasher::new();
        kmer.hash(&mut hasher);
        let hash = hasher.finish();

        Ok((hash % 100) > 50) // 50% chance of existence
    }

    /// Get database metadata
    fn get_metadata(&self) -> PyResult<std::collections::HashMap<String, String>> {
        if !self.loaded {
            return Err(PyRuntimeError::new_err("Database not loaded"));
        }
        Ok(self.metadata.clone())
    }

    /// Check if database is loaded
    fn is_loaded(&self) -> bool {
        self.loaded
    }

    /// Get database statistics
    fn get_stats(&self) -> PyResult<std::collections::HashMap<String, pyo3::Py<pyo3::PyAny>>> {
        Python::with_gil(|py| {
            if !self.loaded {
                return Err(PyRuntimeError::new_err("Database not loaded"));
            }

            let mut stats = std::collections::HashMap::new();
            stats.insert("path".to_string(), self.path.clone().into_py(py));
            stats.insert("loaded".to_string(), self.loaded.into_py(py));
            if let Some(k) = self.kmer_size {
                stats.insert("kmer_size".to_string(), k.into_py(py));
            }
            if let Some(total) = self.total_kmers {
                stats.insert("total_kmers".to_string(), total.into_py(py));
            }
            if let Some(unique) = self.unique_kmers {
                stats.insert("unique_kmers".to_string(), unique.into_py(py));
            }

            Ok(stats)
        })
    }

    /// String representation
    fn __repr__(&self) -> String {
        format!(
            "Database(path='{}', loaded={}, kmer_size={:?})",
            self.path, self.loaded, self.kmer_size
        )
    }

    /// String representation
    fn __str__(&self) -> String {
        if self.loaded {
            format!(
                "Database: {} (k={}, {} kmers)",
                std::path::Path::new(&self.path)
                    .file_name()
                    .and_then(|n| n.to_str())
                    .unwrap_or(&self.path),
                self.kmer_size.unwrap_or(0),
                self.unique_kmers.unwrap_or(0)
            )
        } else {
            format!(
                "Database: {} (not loaded)",
                std::path::Path::new(&self.path)
                    .file_name()
                    .and_then(|n| n.to_str())
                    .unwrap_or(&self.path)
            )
        }
    }
}

/// Python module
#[pymodule]
fn rustkmer(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_class::<KmerCounter>()?;
    m.add_class::<QueryResult>()?;
    m.add_class::<Database>()?;
    m.add_class::<ThreadPoolConfig>()?;
    m.add_class::<ThreadPoolStats>()?;
    m.add_class::<ThreadSafeDatabaseManager>()?;
    m.add_class::<ThreadSafeDatabase>()?;

    // Add u128 validation functions
    #[cfg(feature = "python")]
    {
        m.add_function(pyo3::wrap_pyfunction!(validate_u128_encoding_all, m)?)?;
        m.add_function(pyo3::wrap_pyfunction!(validate_u128_encoding_length, m)?)?;

        // Add error conversion functions
        m.add_function(pyo3::wrap_pyfunction!(convert_error_for_python, m)?)?;
        m.add_function(pyo3::wrap_pyfunction!(create_python_exception, m)?)?;

        // Add thread pool functions
        m.add_function(pyo3::wrap_pyfunction!(set_global_thread_config, m)?)?;
        m.add_function(pyo3::wrap_pyfunction!(get_global_thread_config, m)?)?;
        m.add_function(pyo3::wrap_pyfunction!(reset_global_thread_config, m)?)?;
        m.add_function(pyo3::wrap_pyfunction!(apply_thread_config, m)?)?;
        m.add_function(pyo3::wrap_pyfunction!(get_system_thread_info, m)?)?;

        // Add utils functions
        // TODO: Implement get_resource_stats
        // m.add_function(pyo3::wrap_pyfunction!(get_resource_stats, m)?)?;
    }

    Ok(())
}

/// Validate u128 encoding for all supported k-mer lengths (1-64)
#[pyfunction]
fn validate_u128_encoding_all() -> PyResult<u128> {
    use crate::kmer::validation::ValidationReport;

    let report = ValidationReport::generate()
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Validation failed: {}", e)))?;

    if report.summary.all_passed {
        Ok(report.summary.total_sequences_tested as u128)
    } else {
        Err(pyo3::exceptions::PyAssertionError::new_err(format!(
            "Validation failed: {} errors across {} lengths",
            report.summary.total_failures,
            report.summary.failed_lengths
        )))
    }
}

/// Validate u128 encoding for a specific k-mer length
#[pyfunction]
fn validate_u128_encoding_length(k: usize) -> PyResult<bool> {
    use crate::kmer::validation::validate_kmer_length;

    match validate_kmer_length(k) {
        Ok(result) => Ok(result.all_passed),
        Err(e) => Err(pyo3::exceptions::PyValueError::new_err(format!(
            "Validation error for k={}: {}",
            k, e
        ))),
    }
}

// ============================================================================
// Error Conversion Layer
// ============================================================================

/// Convert RustKmerError to appropriate Python exception
fn convert_rustkmer_error(err: crate::error::RustKmerError) -> PyErr {
    use crate::error::RustKmerError;

    match err {
        RustKmerError::InvalidKmer(msg) => PyValueError::new_err(format!("Invalid k-mer: {}", msg)),
        RustKmerError::InvalidInput(msg) => PyValueError::new_err(format!("Invalid input: {}", msg)),
        RustKmerError::QueryError(msg) => PyRuntimeError::new_err(format!("Query error: {}", msg)),
        RustKmerError::DatabaseError(msg) => PyRuntimeError::new_err(format!("Database error: {}", msg)),
        RustKmerError::ThreadCreationError(msg) => PyRuntimeError::new_err(format!("Thread creation failed: {}", msg)),
        RustKmerError::ProcessingError(msg) => PyRuntimeError::new_err(format!("Processing error: {}", msg)),
        RustKmerError::IoError(msg) => PyIOError::new_err(format!("I/O error: {}", msg)),
        RustKmerError::InsufficientMemory(msg) => PyMemoryError::new_err(format!("Insufficient memory: {}", msg)),
        RustKmerError::DatabaseNotFound(msg) => PyFileNotFoundError::new_err(format!("Database not found: {}", msg)),
        RustKmerError::InvalidDatabaseFormat(msg) => PyValueError::new_err(format!("Invalid database format: {}", msg)),
    }
}

/// Convert KmerError to appropriate Python exception
fn convert_kmer_error(err: crate::error::KmerError) -> PyErr {
    use crate::error::KmerError;

    match err {
        KmerError::InvalidKmerSize(k) => PyValueError::new_err(format!("Invalid k-mer size: {}", k)),
        KmerError::InvalidCharacter { pos, char } => PyValueError::new_err(format!(
            "Invalid character '{}' at position {}", char, pos
        )),
        KmerError::SequenceTooShort { length, min_required, kmer_size } => PyValueError::new_err(format!(
            "Sequence too short: {} bases (minimum {} for k-mer size {})",
            length, min_required, kmer_size
        )),
        KmerError::FileFormatError { file, reason } => PyValueError::new_err(format!(
            "File format error in '{}': {}", file, reason
        )),
        KmerError::MemoryError(msg) => PyMemoryError::new_err(format!("Memory error: {}", msg)),
        KmerError::HashTableOverflow(msg) => PyRuntimeError::new_err(format!("Hash table overflow: {}", msg)),
        KmerError::Io(err) => PyIOError::new_err(err.to_string()),
        KmerError::Utf8Error(err) => PyRuntimeError::new_err(format!("UTF-8 error: {}", err)),
        KmerError::ParseError(msg) => PyValueError::new_err(format!("Parse error: {}", msg)),
        KmerError::ProcessingError(msg) => PyRuntimeError::new_err(format!("Processing error: {}", msg)),
        KmerError::FileNotFound(file) => PyFileNotFoundError::new_err(format!("File not found: {}", file)),
        KmerError::FileWriteError(msg) => PyIOError::new_err(format!("File write error: {}", msg)),
        KmerError::InvalidArgument(msg) => PyValueError::new_err(format!("Invalid argument: {}", msg)),
    }
}

/// Convert ProcessingError to appropriate Python exception
fn convert_processing_error(err: crate::error::ProcessingError) -> PyErr {
    PyRuntimeError::new_err(format!("Processing error: {}", err))
}

/// Convert StatsError to appropriate Python exception
fn convert_stats_error(err: crate::database::stats::StatsError) -> PyErr {
    use crate::database::stats::StatsError;

    match err {
        StatsError::DatabaseNotFound { path } => PyFileNotFoundError::new_err(format!("Database not found: {}", path.display())),
        StatsError::InvalidFormat { reason } => PyValueError::new_err(format!("Invalid database format: {}", reason)),
        StatsError::EmptyDatabase => PyRuntimeError::new_err("Database empty: no k-mers found"),
        StatsError::MemoryLimitExceeded { required, limit } => PyMemoryError::new_err(format!(
            "Memory limit exceeded: required {}MB, limit {}MB", required, limit
        )),
        StatsError::Io { source } => PyIOError::new_err(format!("I/O error: {}", source)),
        StatsError::Serialization { format, source } => PyRuntimeError::new_err(format!(
            "Serialization error: {} - {}", format, source
        )),
        StatsError::Csv(err) => PyValueError::new_err(format!("CSV error: {}", err)),
        StatsError::Json(err) => PyValueError::new_err(format!("JSON error: {}", err)),
    }
}

/// Convert FuzzyError to appropriate Python exception
fn convert_fuzzy_error(err: crate::fuzzy::FuzzyError) -> PyErr {
    use crate::fuzzy::FuzzyError;

    match err {
        FuzzyError::InvalidQuery(query) => PyValueError::new_err(format!("Invalid query: {}", query)),
        FuzzyError::TooManyVariants { actual, limit } => PyRuntimeError::new_err(format!(
            "Too many variants generated: {} (limit: {})", actual, limit
        )),
        FuzzyError::MemoryLimitExceeded { usage_mb, limit_mb } => PyMemoryError::new_err(format!(
            "Memory limit exceeded: {}MB (limit: {}MB)", usage_mb, limit_mb
        )),
        FuzzyError::DatabaseError(msg) => PyRuntimeError::new_err(format!("Database error: {}", msg)),
        FuzzyError::PerformanceConstraint(msg) => PyRuntimeError::new_err(format!("Performance constraint violation: {}", msg)),
        FuzzyError::InvalidParameters(msg) => PyValueError::new_err(format!("Invalid parameters: {}", msg)),
        FuzzyError::Cancelled => PyRuntimeError::new_err("Query cancelled by user"),
        FuzzyError::IoError(err) => PyIOError::new_err(format!("I/O error: {}", err)),
    }
}

/// Convert MergeError to appropriate Python exception
fn convert_merge_error(err: crate::database::merge_error::MergeError) -> PyErr {
    use crate::database::merge_error::MergeError;

    match err {
        MergeError::EmptyInput => PyValueError::new_err("No input databases provided"),
        MergeError::IncompatibleDatabase { details, .. } => PyValueError::new_err(format!(
            "Incompatible database: {}", details
        )),
        MergeError::IOError { path, message, .. } => PyIOError::new_err(format!(
            "I/O error accessing '{}': {}", path, message
        )),
        MergeError::InsufficientMemory { required, available } => PyMemoryError::new_err(format!(
            "Insufficient memory for merge operation. Required: {}MB, Available: {}MB",
            required, available
        )),
        MergeError::CountOverflow { kmer, current, additional } => PyRuntimeError::new_err(format!(
            "K-mer count overflow for k-mer {:X}. Current count: {}, Additional: {}",
            kmer, current, additional
        )),
        MergeError::InvalidFormat { path, reason } => PyValueError::new_err(format!(
            "Invalid database format in '{}': {}", path, reason
        )),
        MergeError::Interrupted { reason } => PyRuntimeError::new_err(format!(
            "Merge operation interrupted: {}", reason
        )),
        MergeError::TempFileError { operation, path, error } => PyIOError::new_err(format!(
            "Temporary file operation failed: {} on '{}': {}", operation, path, error
        )),
        MergeError::ConcurrentModification { path } => PyRuntimeError::new_err(format!(
            "Concurrent modification detected on database '{}'", path
        )),
        MergeError::Configuration { details } => PyValueError::new_err(format!(
            "Invalid merge configuration: {}", details
        )),
    }
}

/// Error conversion utility that can handle any error type
#[pyfunction]
fn convert_error_for_python(error_type: &str, message: &str) -> PyErr {
    match error_type.to_lowercase().as_str() {
        "validation" => PyValueError::new_err(format!("ValidationError: {}", message)),
        "database" => PyRuntimeError::new_err(format!("DatabaseError: {}", message)),
        "stats" => PyRuntimeError::new_err(format!("StatsError: {}", message)),
        "utils" => PyRuntimeError::new_err(format!("UtilsError: {}", message)),
        "kmercounting" => PyRuntimeError::new_err(format!("KmerCountingError: {}", message)),
        "query" => PyRuntimeError::new_err(format!("QueryError: {}", message)),
        "fuzzy" => PyRuntimeError::new_err(format!("FuzzyQueryError: {}", message)),
        "merge" => PyRuntimeError::new_err(format!("MergeError: {}", message)),
        "export" => PyRuntimeError::new_err(format!("ExportError: {}", message)),
        "compression" => PyRuntimeError::new_err(format!("CompressionError: {}", message)),
        "progress" => PyRuntimeError::new_err(format!("ProgressCallbackError: {}", message)),
        "threadsafety" => PyRuntimeError::new_err(format!("ThreadSafetyError: {}", message)),
        "notimplemented" => PyRuntimeError::new_err(format!("NotImplementedError: {}", message)),
        "value" => PyValueError::new_err(format!("ValueError: {}", message)),
        "memory" => PyMemoryError::new_err(format!("MemoryError: {}", message)),
        "io" => PyIOError::new_err(format!("PermissionError: {}", message)),
        "file" => PyFileNotFoundError::new_err(format!("FileNotFoundError: {}", message)),
        _ => PyRuntimeError::new_err(format!("RustKmerError: {}", message)),
    }
}

/// Create a Python exception with custom attributes
#[pyfunction]
#[pyo3(signature = (exception_type, message, attributes=None))]
fn create_python_exception(exception_type: &str, message: String, attributes: Option<Vec<String>>) -> PyErr {
    let base_exception = match exception_type.to_lowercase().as_str() {
        "validation" => PyValueError::new_err(message),
        "database" => PyRuntimeError::new_err(message),
        "stats" => PyRuntimeError::new_err(message),
        _ => PyRuntimeError::new_err(message),
    };

    // Note: In a real implementation, we would add custom attributes here
    // For now, we just return the base exception
    base_exception
}

// ============================================================================
// QueryResult Class Structure
// ============================================================================

/// Query result containing k-mer query information
#[pyclass(name = "QueryResult")]
#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
pub struct QueryResult {
    /// The queried k-mer sequence
    #[pyo3(get)]
    kmer: String,
    /// The count of the k-mer in the database (0 if not found)
    #[pyo3(get)]
    count: u32,
    /// Whether the k-mer exists in the database
    #[pyo3(get)]
    exists: bool,
    /// Additional metadata about the query
    #[pyo3(get)]
    metadata: Option<String>,
}

#[pymethods]
impl QueryResult {
    /// Create a new QueryResult
    #[new]
    #[pyo3(signature = (kmer, count, exists, metadata=None))]
    fn new(kmer: String, count: u32, exists: bool, metadata: Option<String>) -> Self {
        Self { kmer, count, exists, metadata }
    }

    /// Create a QueryResult for a found k-mer
    #[staticmethod]
    #[pyo3(signature = (kmer, count, metadata=None))]
    fn found(kmer: String, count: u32, metadata: Option<String>) -> Self {
        Self {
            kmer,
            count,
            exists: true,
            metadata,
        }
    }

    /// Create a QueryResult for a missing k-mer
    #[staticmethod]
    fn not_found(kmer: String) -> Self {
        Self {
            kmer,
            count: 0,
            exists: false,
            metadata: None,
        }
    }

    /// Convert to a dictionary representation
    fn to_dict(&self) -> PyResult<std::collections::HashMap<String, pyo3::Py<pyo3::PyAny>>> {
        Python::with_gil(|py| {
            let mut dict = std::collections::HashMap::new();
            dict.insert("kmer".to_string(), self.kmer.clone().into_py(py));
            dict.insert("count".to_string(), self.count.into_py(py));
            dict.insert("exists".to_string(), self.exists.into_py(py));
            if let Some(ref metadata) = self.metadata {
                dict.insert("metadata".to_string(), metadata.clone().into_py(py));
            }
            Ok(dict)
        })
    }

    /// String representation of the QueryResult
    fn __repr__(&self) -> String {
        if self.exists {
            format!("QueryResult(kmer='{}', count={}, exists=True)", self.kmer, self.count)
        } else {
            format!("QueryResult(kmer='{}', count=0, exists=False)", self.kmer)
        }
    }

    /// String representation of the QueryResult
    fn __str__(&self) -> String {
        if self.exists {
            format!("{}: {} (found)", self.kmer, self.count)
        } else {
            format!("{}: not found", self.kmer)
        }
    }

    /// Compare two QueryResults for equality
    fn __eq__(&self, other: &Self) -> bool {
        self.kmer == other.kmer && self.count == other.count && self.exists == other.exists
    }

    /// Serialize to JSON string
    fn to_json(&self) -> PyResult<String> {
        serde_json::to_string(self)
            .map_err(|e| PyRuntimeError::new_err(format!("JSON serialization error: {}", e)))
    }

    /// Deserialize from JSON string
    #[staticmethod]
    fn from_json(json_str: String) -> PyResult<Self> {
        serde_json::from_str(&json_str)
            .map_err(|e| PyRuntimeError::new_err(format!("JSON deserialization error: {}", e)))
    }
}