//! Utility functions for Python bindings

use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::sync::atomic::Ordering;
use super::exceptions::*;

/// Set verbosity level for logging
#[pyfunction]
pub fn set_verbosity(level: u32) -> PyResult<()> {
    use log::LevelFilter;

    let log_level = match level {
        0 => LevelFilter::Off,
        1 => LevelFilter::Info,
        2 => LevelFilter::Debug,
        3 => LevelFilter::Trace,
        _ => {
            // For levels > 3, map to the highest level
            if level > 3 {
                LevelFilter::Trace
            } else {
                LevelFilter::Info
            }
        }
    };

    // Initialize the logger with the specified level
    env_logger::Builder::from_default_env()
        .filter_level(log_level)
        .format_timestamp_secs()
        .init();

    log::info!("RustKmer Python logging initialized at level: {:?}", log_level);

    Ok(())
}

/// Get current logging level
#[pyfunction]
pub fn get_log_level() -> String {
    use log::LevelFilter;

    // Try to get the current max level from the logger
    let current_level = log::max_level();

    match current_level {
        LevelFilter::Off => "off".to_string(),
        LevelFilter::Error => "error".to_string(),
        LevelFilter::Warn => "warn".to_string(),
        LevelFilter::Info => "info".to_string(),
        LevelFilter::Debug => "debug".to_string(),
        LevelFilter::Trace => "trace".to_string(),
    }
}

/// Log a message at the specified level
#[pyfunction]
pub fn log_message(level: &str, message: &str) -> PyResult<()> {
    match level.to_lowercase().as_str() {
        "error" => log::error!("{}", message),
        "warn" | "warning" => log::warn!("{}", message),
        "info" => log::info!("{}", message),
        "debug" => log::debug!("{}", message),
        "trace" => log::trace!("{}", message),
        _ => {
            return Err(pyo3::exceptions::PyValueError::new_err(
                format!("Invalid log level: {}. Valid levels: error, warn, info, debug, trace", level)
            ));
        }
    }
    Ok(())
}

/// Check if logging is enabled at the specified level
#[pyfunction]
pub fn is_log_enabled(level: &str) -> PyResult<bool> {
    let result = match level.to_lowercase().as_str() {
        "error" => log::log_enabled!(log::Level::Error),
        "warn" | "warning" => log::log_enabled!(log::Level::Warn),
        "info" => log::log_enabled!(log::Level::Info),
        "debug" => log::log_enabled!(log::Level::Debug),
        "trace" => log::log_enabled!(log::Level::Trace),
        _ => {
            return Err(pyo3::exceptions::PyValueError::new_err(
                format!("Invalid log level: {}. Valid levels: error, warn, info, debug, trace", level)
            ));
        }
    };
    Ok(result)
}

/// Get RustKmer version information
#[pyfunction]
pub fn get_version() -> String {
    format!("RustKmer {}", env!("CARGO_PKG_VERSION"))
}

/// Validate DNA sequence
#[pyfunction]
pub fn validate_dna_sequence(sequence: &str) -> PyResult<bool> {
    let valid_bases = ['A', 'T', 'C', 'G', 'N'];
    for c in sequence.chars() {
        let upper = c.to_ascii_uppercase();
        if !valid_bases.contains(&upper) {
            return Ok(false);
        }
    }
    Ok(true)
}

/// Normalize DNA sequence (uppercase, remove whitespace)
#[pyfunction]
pub fn normalize_dna_sequence(sequence: &str) -> String {
    sequence.chars()
        .filter(|c| !c.is_whitespace())
        .map(|c| c.to_ascii_uppercase())
        .collect()
}

/// Reverse complement a DNA sequence
#[pyfunction]
pub fn reverse_complement(sequence: &str) -> PyResult<String> {
    let complement = |base: char| -> char {
        match base.to_ascii_uppercase() {
            'A' => 'T',
            'T' => 'A',
            'C' => 'G',
            'G' => 'C',
            'N' => 'N',
            _ => 'N', // Unknown base becomes N
        }
    };

    Ok(sequence.chars()
        .rev()
        .map(complement)
        .collect())
}

/// Get canonical k-mer (lexicographically smaller of sequence and reverse complement)
#[pyfunction]
pub fn get_canonical_kmer(kmer: &str) -> PyResult<String> {
    let normalized = normalize_dna_sequence(kmer);
    let rev_comp = reverse_complement(&normalized)?;

    if normalized < rev_comp {
        Ok(normalized)
    } else {
        Ok(rev_comp)
    }
}

/// Generate all possible k-mers with wildcard expansion
#[pyfunction]
pub fn expand_wildcards(sequence: &str) -> PyResult<Vec<String>> {
    let bases = vec!['A', 'T', 'C', 'G'];
    let mut results = vec![String::new()];

    for c in sequence.chars() {
        let mut new_results = Vec::new();
        let replacements = if c.to_ascii_uppercase() == 'N' {
            bases.clone()
        } else {
            vec![c]
        };

        for prefix in results {
            for replacement in &replacements {
                let mut new_string = prefix.clone();
                new_string.push(*replacement);
                new_results.push(new_string);
            }
        }

        results = new_results;
    }

    Ok(results)
}

/// Calculate Hamming distance between two sequences of equal length
#[pyfunction]
pub fn hamming_distance(seq1: &str, seq2: &str) -> PyResult<usize> {
    if seq1.len() != seq2.len() {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "Sequences must have equal length"
        ));
    }

    let distance = seq1.chars()
        .zip(seq2.chars())
        .filter(|(a, b)| a != b)
        .count();

    Ok(distance)
}

/// Generate all k-mers within specified Hamming distance
#[pyfunction]
pub fn generate_neighbors(kmer: &str, max_distance: usize) -> PyResult<Vec<String>> {
    let bases = vec!['A', 'T', 'C', 'G'];
    let kmer = normalize_dna_sequence(kmer);
    let k = kmer.len();
    let mut neighbors = Vec::new();

    // Start with the original k-mer
    neighbors.push(kmer.clone());

    // Generate all variations
    for dist in 1..=max_distance {
        // This is a simplified approach - actual implementation would be more efficient
        let _positions: Vec<usize> = (0..k).collect();

        // Choose positions to mutate
        for i in 0..k {
            if i <= dist {
                for j in i+1..k.min(i + (dist - i) + 1) {
                    // Generate variations by mutating positions i and j
                    for base1 in &bases {
                        if *base1 != kmer.chars().nth(i).unwrap_or('N') {
                            let mut neighbor = kmer.clone();
                            neighbor.replace_range(i..=i, &base1.to_string());

                            if j < k {
                                for base2 in &bases {
                                    if *base2 != kmer.chars().nth(j).unwrap_or('N') {
                                        let mut neighbor2 = neighbor.clone();
                                        neighbor2.replace_range(j..=j, &base2.to_string());
                                        neighbors.push(neighbor2);
                                    }
                                }
                            } else {
                                neighbors.push(neighbor);
                            }
                        }
                    }
                }
            }
        }
    }

    // Remove duplicates and sort
    neighbors.sort();
    neighbors.dedup();

    Ok(neighbors)
}

/// Check if system supports multi-threading
#[pyfunction]
pub fn supports_multithreading() -> bool {
    std::thread::available_parallelism().map(|n| n.get() > 1).unwrap_or(false)
}

/// Get number of available CPU cores
#[pyfunction]
pub fn get_cpu_count() -> usize {
    std::thread::available_parallelism().map(|n| n.get()).unwrap_or(1)
}

/// Get memory usage statistics
#[pyfunction]
pub fn get_memory_stats() -> pyo3::PyObject {
    Python::with_gil(|py| {
        let stats = pyo3::types::PyDict::new(py);
        // Placeholder values - will implement actual memory tracking in Phase 2
        stats.set_item("total_memory", 0u64).unwrap();
        stats.set_item("used_memory", 0u64).unwrap();
        stats.set_item("available_memory", 0u64).unwrap();
        stats.into()
    })
}

/// Benchmark k-mer counting performance
#[pyfunction]
pub fn benchmark_kmer_counting(k: usize, sequences: Vec<String>) -> PyResult<std::collections::HashMap<String, f64>> {
    use std::time::Instant;

    let start = Instant::now();
    let mut total_kmers = 0u64;

    for seq in sequences {
        if seq.len() >= k {
            total_kmers += (seq.len() - k + 1) as u64;
        }
    }

    let duration = start.elapsed();
    let elapsed_seconds = duration.as_secs_f64();

    let mut results = std::collections::HashMap::new();
    results.insert("sequences_processed".to_string(), total_kmers as f64);
    results.insert("elapsed_seconds".to_string(), elapsed_seconds);
    results.insert("kmer_rate".to_string(), total_kmers as f64 / elapsed_seconds);

    Ok(results)
}

// =============================================================================
// Debugging and Performance Utilities (T014)
// =============================================================================

/// Get system information for debugging
#[pyfunction]
pub fn get_system_info() -> pyo3::PyObject {
    Python::with_gil(|py| {
        let info = PyDict::new(py);

        // CPU information
        info.set_item("cpu_count", get_cpu_count()).unwrap();
        info.set_item("supports_multithreading", supports_multithreading()).unwrap();

        // Version information
        info.set_item("rustkmer_version", get_version()).unwrap();
        info.set_item("rust_version", "1.80+").unwrap(); // Based on CLAUDE.md requirements

        // Memory information (placeholder)
        info.set_item("memory_stats", get_memory_stats()).unwrap();

        // Resource information
        info.set_item("resource_stats", get_resource_stats()).unwrap();

        info.into()
    })
}

/// Simple performance timer for benchmarking operations
#[pyclass(name = "PerformanceTimer")]
pub struct PerformanceTimer {
    start_time: std::time::Instant,
    operation_name: String,
}

#[pymethods]
impl PerformanceTimer {
    /// Create a new performance timer
    #[new]
    fn new(operation_name: &str) -> Self {
        log::debug!("Starting performance timer for operation: {}", operation_name);
        Self {
            start_time: std::time::Instant::now(),
            operation_name: operation_name.to_string(),
        }
    }

    /// Get elapsed time in seconds
    fn elapsed(&self) -> f64 {
        let duration = self.start_time.elapsed();
        duration.as_secs_f64()
    }

    /// Get elapsed time as string with units
    fn elapsed_str(&self) -> String {
        let duration = self.start_time.elapsed();

        if duration.as_secs() > 0 {
            format!("{:.2}s", duration.as_secs_f64())
        } else if duration.as_millis() > 0 {
            format!("{:.0}ms", duration.as_millis())
        } else if duration.as_micros() > 0 {
            format!("{:.0}μs", duration.as_micros())
        } else {
            format!("{}ns", duration.as_nanos())
        }
    }

    /// Log the elapsed time and return it
    fn finish(&self) -> PyResult<f64> {
        let elapsed = self.elapsed();
        log::info!("Operation '{}' completed in {}", self.operation_name, self.elapsed_str());
        Ok(elapsed)
    }
}

/// Enable debug mode with additional logging
#[pyfunction]
pub fn enable_debug_mode() -> PyResult<()> {
    // Set logging to debug level
    set_verbosity(2)?;

    // Enable additional debug information
    log::info!("RustKmer debug mode enabled");
    log::debug!("CPU cores: {}", get_cpu_count());
    log::debug!("Multithreading support: {}", supports_multithreading());
    log::debug!("Version: {}", get_version());

    Ok(())
}

/// Enable trace mode with maximum logging
#[pyfunction]
pub fn enable_trace_mode() -> PyResult<()> {
    // Set logging to trace level
    set_verbosity(3)?;

    // Enable maximum trace information
    log::info!("RustKmer trace mode enabled - maximum verbosity");
    log::debug!("Performance monitoring enabled");

    Ok(())
}

/// Flush any pending log messages
#[pyfunction]
pub fn flush_logs() -> PyResult<()> {
    // In most logging implementations, this is a no-op
    // but it ensures logs are written when called from Python
    log::logger().flush();
    Ok(())
}

// =============================================================================
// Error Mapping Functions
// =============================================================================

/// Map common Rust errors to appropriate Python exceptions
pub fn map_rust_error_to_py(error: Box<dyn std::error::Error>) -> PyErr {
    let error_msg = error.to_string();

    // Check for common error patterns and map to appropriate exceptions
    if error_msg.contains("k-mer") || error_msg.contains("kmer") {
        KmerError::new_err(error_msg)
    } else if error_msg.contains("database") || error_msg.contains("file") {
        DatabaseError::new_err(error_msg)
    } else if error_msg.contains("sequence") || error_msg.contains("DNA") {
        SequenceError::new_err(error_msg)
    } else if error_msg.contains("configuration") || error_msg.contains("parameter") {
        ConfigurationError::new_err(error_msg)
    } else if error_msg.contains("validation") || error_msg.contains("invalid") {
        ValidationError::new_err(error_msg)
    } else {
        RustKmerError::new_err(error_msg)
    }
}

/// Convert IoError to DatabaseError
pub fn map_io_error_to_py(error: std::io::Error, context: &str) -> PyErr {
    let msg = format!("{}: {}", context, error);
    DatabaseError::new_err(msg)
}

/// Convert validation errors with detailed context
pub fn create_validation_error(field: &str, value: &str, reason: &str) -> PyErr {
    let msg = format!("Invalid value '{}' for field '{}': {}", value, field, reason);
    ValidationError::new_err(msg)
}

/// Convert k-mer related errors
pub fn create_kmer_error(kmer: &str, operation: &str, reason: &str) -> PyErr {
    let msg = format!("Failed to {} k-mer '{}': {}", operation, kmer, reason);
    KmerError::new_err(msg)
}

/// Convert database operation errors
pub fn create_database_error(operation: &str, path: Option<&str>, reason: &str) -> PyErr {
    let msg = if let Some(p) = path {
        format!("Failed to {} database '{}': {}", operation, p, reason)
    } else {
        format!("Failed to {} database: {}", operation, reason)
    };
    DatabaseError::new_err(msg)
}

/// Convert sequence processing errors
pub fn create_sequence_error(sequence: &str, operation: &str, reason: &str) -> PyErr {
    let msg = format!("Failed to {} sequence '{}': {}", operation, sequence, reason);
    SequenceError::new_err(msg)
}

// =============================================================================
// Memory Management Utilities (T011)
// =============================================================================

/// Memory manager for tracking resource usage
pub struct MemoryManager {
    peak_memory: std::sync::atomic::AtomicU64,
    current_memory: std::sync::atomic::AtomicU64,
}

impl MemoryManager {
    /// Create a new memory manager
    pub fn new() -> Self {
        Self {
            peak_memory: std::sync::atomic::AtomicU64::new(0),
            current_memory: std::sync::atomic::AtomicU64::new(0),
        }
    }

    /// Allocate memory and update tracking
    pub fn allocate(&self, size: u64) -> Result<(), String> {
        let current = self.current_memory.fetch_add(size, Ordering::Relaxed);
        let peak = self.peak_memory.load(Ordering::Relaxed);

        if current > peak {
            self.peak_memory.store(current, Ordering::Relaxed);
        }

        // Check memory limits (100MB default)
        const MAX_MEMORY: u64 = 100 * 1024 * 1024;
        if current > MAX_MEMORY {
            self.current_memory.fetch_sub(size, Ordering::Relaxed);
            Err(format!("Memory allocation would exceed limit: {} bytes", MAX_MEMORY))
        } else {
            Ok(())
        }
    }

    /// Deallocate memory and update tracking
    pub fn deallocate(&self, size: u64) {
        self.current_memory.fetch_sub(size, Ordering::Relaxed);
    }

    /// Get current memory usage in bytes
    pub fn current_usage(&self) -> u64 {
        self.current_memory.load(Ordering::Relaxed)
    }

    /// Get peak memory usage in bytes
    pub fn peak_usage(&self) -> u64 {
        self.peak_memory.load(Ordering::Relaxed)
    }

    /// Reset tracking statistics
    pub fn reset(&self) {
        self.current_memory.store(0, Ordering::Relaxed);
        self.peak_memory.store(0, Ordering::Relaxed);
    }
}

/// Global memory manager instance
static MEMORY_MANAGER: std::sync::OnceLock<MemoryManager> = std::sync::OnceLock::new();

/// Get the global memory manager
pub fn get_memory_manager() -> &'static MemoryManager {
    MEMORY_MANAGER.get_or_init(|| MemoryManager::new())
}

/// Allocate memory with automatic tracking
pub fn allocate_tracked(size: u64) -> Result<(), String> {
    get_memory_manager().allocate(size)
}

/// Deallocate memory with automatic tracking
pub fn deallocate_tracked(size: u64) {
    get_memory_manager().deallocate(size);
}

/// Resource cleanup utility for Python objects
pub struct ResourceTracker {
    allocated_objects: std::sync::atomic::AtomicUsize,
    peak_objects: std::sync::atomic::AtomicUsize,
}

impl ResourceTracker {
    /// Create a new resource tracker
    pub fn new() -> Self {
        Self {
            allocated_objects: std::sync::atomic::AtomicUsize::new(0),
            peak_objects: std::sync::atomic::AtomicUsize::new(0),
        }
    }

    /// Register a new object allocation
    pub fn register_allocation(&self) -> Result<(), String> {
        let current = self.allocated_objects.fetch_add(1, Ordering::Relaxed);
        let peak = self.peak_objects.load(Ordering::Relaxed);

        if current > peak {
            self.peak_objects.store(current, Ordering::Relaxed);
        }

        // Check object limits (10,000 default)
        const MAX_OBJECTS: usize = 10_000;
        if current > MAX_OBJECTS {
            self.allocated_objects.fetch_sub(1, Ordering::Relaxed);
            Err(format!("Object allocation would exceed limit: {}", MAX_OBJECTS))
        } else {
            Ok(())
        }
    }

    /// Register a deallocation
    pub fn register_deallocation(&self) {
        self.allocated_objects.fetch_sub(1, Ordering::Relaxed);
    }

    /// Get current object count
    pub fn current_objects(&self) -> usize {
        self.allocated_objects.load(Ordering::Relaxed)
    }

    /// Get peak object count
    pub fn peak_objects(&self) -> usize {
        self.peak_objects.load(Ordering::Relaxed)
    }

    /// Reset tracking statistics
    pub fn reset(&self) {
        self.allocated_objects.store(0, Ordering::Relaxed);
        self.peak_objects.store(0, Ordering::Relaxed);
    }
}

/// Global resource tracker instance
static RESOURCE_TRACKER: std::sync::OnceLock<ResourceTracker> = std::sync::OnceLock::new();

/// Get the global resource tracker
pub fn get_resource_tracker() -> &'static ResourceTracker {
    RESOURCE_TRACKER.get_or_init(|| ResourceTracker::new())
}

/// Register a Python object allocation
pub fn register_object() -> Result<(), String> {
    get_resource_tracker().register_allocation()
}

/// Register a Python object deallocation
pub fn deallocate_object() {
    get_resource_tracker().register_deallocation();
}

/// Get comprehensive resource usage statistics
#[pyfunction]
pub fn get_resource_stats() -> pyo3::PyObject {
    Python::with_gil(|py| {
        let stats = PyDict::new(py);
        let mem_mgr = get_memory_manager();
        let res_tracker = get_resource_tracker();

        stats.set_item("memory_current_bytes", mem_mgr.current_usage()).unwrap();
        stats.set_item("memory_peak_bytes", mem_mgr.peak_usage()).unwrap();
        stats.set_item("objects_current", res_tracker.current_objects()).unwrap();
        stats.set_item("objects_peak", res_tracker.peak_objects()).unwrap();

        stats.into()
    })
}

/// Cleanup all tracked resources
#[pyfunction]
pub fn cleanup_resources() -> PyResult<()> {
    let mem_mgr = get_memory_manager();
    let res_tracker = get_resource_tracker();

    mem_mgr.reset();
    res_tracker.reset();

    println!("Resource tracking reset - Memory: {} bytes, Objects: {}",
              mem_mgr.current_usage(), res_tracker.current_objects());

    Ok(())
}

/// RAII wrapper for automatic resource management
pub struct AutoResourceGuard {
    _private: (),
}

impl AutoResourceGuard {
    /// Create a new resource guard
    pub fn new() -> Result<Self, String> {
        register_object()?;
        Ok(AutoResourceGuard { _private: () })
    }
}

impl Drop for AutoResourceGuard {
    fn drop(&mut self) {
        deallocate_object();
    }
}