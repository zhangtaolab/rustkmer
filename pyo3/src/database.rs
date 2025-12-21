//! PyDatabase - Python wrapper for RustKmer Database operations
//!
//! This module provides a Python class that wraps the Rust Database
//! functionality for querying k-mer databases.

use pyo3::prelude::*;
use pyo3::types::{PyString, PyDict};
use std::path::Path;
use std::collections::HashMap;
use std::fs::File;
use std::io::{Seek, SeekFrom, Read};
// use memmap2::{Mmap, MmapOptions}; // No longer needed - using direct I/O
use rustkmer::database::format::{RKDatabase, DatabaseHeader, KmerEntry};
use rustkmer::kmer::encoding::{encode_kmer_u128, decode_kmer_u128};
use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::database::prefix_query_optimized::{extract_prefix_optimized, extract_hybrid_by_pattern, parse_hybrid_pattern, OptimizedPrefixResult};
use rustkmer::database::{PrefixQueryResult, extract_kmers_by_prefix, SuffixQueryResult, extract_kmers_by_suffix, SmartWildcardResult};

/// Database loading modes
#[pyclass(eq, eq_int)]
#[derive(Clone, PartialEq)]
pub enum LoadMode {
    /// Preload all k-mers into memory (fastest queries, higher memory usage)
    Preload,
    /// Use memory-mapped file access (balanced memory/performance)
    MemoryMapped,
    /// Lazy loading - load k-mers on-demand (lowest memory, slower queries)
    Lazy,
}

/// Query result for k-mer lookups
#[pyclass]
pub struct PyQueryResult {
    /// The k-mer sequence
    pub kmer: String,
    /// Count found in database
    pub count: u32,
    /// Whether the k-mer was found
    pub found: bool,
}

#[pymethods]
impl PyQueryResult {
    #[getter]
    fn kmer(&self) -> &str {
        &self.kmer
    }
    
    #[getter]
    fn count(&self) -> u32 {
        self.count
    }
    
    #[getter]
    fn found(&self) -> bool {
        self.found
    }
    
    fn __repr__(&self) -> String {
        format!("PyQueryResult(kmer='{}', count={}, found={})", self.kmer, self.count, self.found)
    }
}

/// Result of optimized prefix query for Python
#[pyclass]
pub struct PyPrefixQueryResult {
    /// List of matching k-mers with their counts
    pub matches: HashMap<String, String>,
    /// Memory block information for performance analysis
    pub start_index: usize,
    pub end_index: usize,
    pub block_size: usize,
    pub is_sorted: bool,
    /// Total number of matches found
    pub total_matches: usize,
    /// Query execution time in milliseconds
    pub query_time_ms: u64,
}

#[pymethods]
impl PyPrefixQueryResult {
    #[getter]
    fn matches(&self) -> HashMap<String, String> {
        self.matches.clone()
    }
    
    #[getter]
    fn total_matches(&self) -> usize {
        self.total_matches
    }
    
    #[getter]
    fn query_time_ms(&self) -> u64 {
        self.query_time_ms
    }
    
    #[getter]
    fn start_index(&self) -> usize {
        self.start_index
    }
    
    #[getter]
    fn end_index(&self) -> usize {
        self.end_index
    }
    
    #[getter]
    fn block_size(&self) -> usize {
        self.block_size
    }
    
    #[getter]
    fn is_sorted(&self) -> bool {
        self.is_sorted
    }
    
    fn __repr__(&self) -> String {
        format!("PyPrefixQueryResult(matches={}, total_matches={}, query_time_ms={}ms, sorted={})", 
            self.matches.len(), self.total_matches, self.query_time_ms, self.is_sorted)
    }
}

/// Database statistics
#[pyclass]
pub struct PyDatabaseStats {
    /// K-mer size in database
    pub kmer_size: usize,
    /// Total k-mers in database
    pub total_kmers: u64,
    /// Unique k-mers count
    pub unique_kmers: u64,
    /// Database file size in bytes
    pub file_size: u64,
    /// Whether database is sorted
    pub is_sorted: bool,
    /// Whether canonical k-mers are used
    pub canonical: bool,
}

#[pymethods]
impl PyDatabaseStats {
    #[getter]
    fn kmer_size(&self) -> usize {
        self.kmer_size
    }
    
    #[getter]
    fn total_kmers(&self) -> u64 {
        self.total_kmers
    }
    
    #[getter]
    fn unique_kmers(&self) -> u64 {
        self.unique_kmers
    }
    
    #[getter]
    fn file_size(&self) -> u64 {
        self.file_size
    }
    
    #[getter]
    fn is_sorted(&self) -> bool {
        self.is_sorted
    }
    
    #[getter]
    fn canonical(&self) -> bool {
        self.canonical
    }
    
    fn __repr__(&self) -> String {
        format!(
            "PyDatabaseStats(kmer_size={}, total_kmers={}, unique_kmers={}, file_size={}, is_sorted={}, canonical={})",
            self.kmer_size, self.total_kmers, self.unique_kmers, self.file_size, self.is_sorted, self.canonical
        )
    }
}

/// High-performance k-mer database for Python
#[pyclass]
pub struct PyDatabase {
    /// Database file path
    pub path: String,
    /// Database header
    pub header: DatabaseHeader,
    /// Loading mode
    pub load_mode: LoadMode,
    /// In-memory cache of k-mers for fast querying (used in Preload mode)
    pub kmer_cache: Option<HashMap<u128, u32>>,
    /// Memory-mapped file reader (used in MemoryMapped mode)
    pub mmapped_file: Option<std::fs::File>,
    /// Memory-mapped data (used in MemoryMapped mode) - now using direct I/O
    pub mmap_data: Option<()>,
    /// File content buffer (used in Lazy mode)
    pub file_buffer: Option<Vec<u8>>,
    /// Database entries for lazy loading
    pub entries: Option<Vec<KmerEntry>>,
    /// Whether database is loaded
    pub is_loaded: bool,
    /// Index for binary search in lazy mode
    pub cached_entries: Option<Vec<(u128, u32)>>, // (encoded_kmer, count) sorted
}

#[pymethods]
impl PyDatabase {
    /// Load a k-mer database from file with specified loading mode
    #[new]
    fn new(path: &Bound<'_, PyString>, load_mode: LoadMode) -> PyResult<Self> {
        let path_str = path.to_string();
        let path = Path::new(&path_str);
        
        if !path.exists() {
            return Err(PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(
                format!("Database file not found: {}", path_str)
            ));
        }
        
        // Load database using the Rust implementation
        let database = RKDatabase::from_file_path(path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Failed to load database: {}", e)
            ))?;
        
        let header = database.header().clone();
        
        match load_mode {
            LoadMode::Preload => {
                // Build k-mer cache for fast querying
                let mut kmer_cache = HashMap::new();
                for entry in &database.entries {
                    kmer_cache.insert(entry.kmer, entry.count);
                }
                
                Ok(Self {
                    path: path_str,
                    header,
                    load_mode: LoadMode::Preload,
                    kmer_cache: Some(kmer_cache),
                    mmapped_file: None,
                    mmap_data: None,
                    file_buffer: None,
                    entries: None,
                    cached_entries: None,
                    is_loaded: true,
                })
            },
            LoadMode::MemoryMapped => {
                // Open file for direct I/O (similar to CLI --no-load mode)
                let file = File::open(path)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Failed to open file for direct I/O: {}", e)
                    ))?;
                
                Ok(Self {
                    path: path_str,
                    header,
                    load_mode: LoadMode::MemoryMapped,
                    kmer_cache: None,
                    mmapped_file: Some(file),
                    mmap_data: None, // Don't use memory mapping - use direct I/O
                    file_buffer: None,
                    entries: None, // Don't load entries into memory
                    cached_entries: None,
                    is_loaded: true,
                })
            },
            LoadMode::Lazy => {
                // Build sorted index for binary search but don't cache all in HashMap
                let mut cached_entries = Vec::new();
                for entry in &database.entries {
                    cached_entries.push((entry.kmer, entry.count));
                }
                cached_entries.sort(); // Sort for binary search
                
                Ok(Self {
                    path: path_str,
                    header,
                    load_mode: LoadMode::Lazy,
                    kmer_cache: None,
                    mmapped_file: None,
                    mmap_data: None,
                    file_buffer: None,
                    entries: Some(database.entries),
                    cached_entries: Some(cached_entries),
                    is_loaded: true,
                })
            }
        }
    }
    
    /// Force lazy loading mode (similar to CLI's --no-load option)
    fn force_lazy_mode(&mut self) -> PyResult<()> {
        if !self.is_loaded {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not loaded"
            ));
        }
        
        // If currently in preload mode, clear the cache
        if self.load_mode == LoadMode::Preload {
            self.kmer_cache = None;
            self.load_mode = LoadMode::Lazy;
            
            // Rebuild sorted index for binary search
            if let Some(entries) = &self.entries {
                let mut cached_entries = Vec::new();
                for entry in entries {
                    cached_entries.push((entry.kmer, entry.count));
                }
                cached_entries.sort();
                self.cached_entries = Some(cached_entries);
            }
        }
        
        Ok(())
    }
    
    /// Query a single k-mer in the database
    fn query(&self, kmer: &Bound<'_, PyString>) -> PyResult<PyQueryResult> {
        if !self.is_loaded {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not loaded"
            ));
        }
        
        let kmer_str = kmer.to_string();
        
        // Validate k-mer size
        if kmer_str.len() != self.header.kmer_size as usize {
            return Ok(PyQueryResult {
                kmer: kmer_str,
                count: 0,
                found: false,
            });
        }
        
        // Encode k-mer
        let encoded_kmer = match encode_kmer_u128(&kmer_str) {
            Ok(encoded) => encoded,
            Err(_) => {
                return Ok(PyQueryResult {
                    kmer: kmer_str,
                    count: 0,
                    found: false,
                });
            }
        };
        
        // Apply canonical transformation if needed
        let search_kmer = if self.header.canonical {
            match canonical_kmer_u128(encoded_kmer, self.header.kmer_size as usize) {
                Ok(canonical) => canonical,
                Err(_) => encoded_kmer,
            }
        } else {
            encoded_kmer
        };
        
        // Query based on load mode
        let count = match &self.load_mode {
            LoadMode::Preload => {
                // Fast lookup in memory cache
                self.kmer_cache.as_ref().unwrap().get(&search_kmer).copied().unwrap_or(0)
            },
            LoadMode::MemoryMapped => {
                // Use binary search with direct file I/O (like CLI --no-load mode)
                if !self.header.sorted {
                    return Ok(PyQueryResult {
                        kmer: kmer_str,
                        count: 0,
                        found: false,
                    });
                }
                
                // Binary search using direct file reads
                let mut left = 0u64;
                let mut right = self.header.total_kmers - 1;
                
                while left <= right {
                    let mid = (left + right) / 2;
                    
                    // Read entry at position mid using direct file I/O
                    match self.read_entry_from_file(mid) {
                        Ok((kmer, count)) => {
                            match search_kmer.cmp(&kmer) {
                                std::cmp::Ordering::Equal => {
                                    return Ok(PyQueryResult {
                                        kmer: kmer_str,
                                        count,
                                        found: true,
                                    });
                                },
                                std::cmp::Ordering::Less => {
                                    if mid == 0 { break; }
                                    right = mid - 1;
                                },
                                std::cmp::Ordering::Greater => left = mid + 1,
                            }
                        },
                        Err(_) => break, // Error reading entry
                    }
                }
                0
            },
            LoadMode::Lazy => {
                // Binary search in sorted cache
                let cached_entries = self.cached_entries.as_ref().unwrap();
                match cached_entries.binary_search_by_key(&search_kmer, |(kmer, _)| *kmer) {
                    Ok(idx) => cached_entries[idx].1,
                    Err(_) => 0,
                }
            }
        };
        
        Ok(PyQueryResult {
            kmer: kmer_str,
            count,
            found: count > 0,
        })
    }
    
    /// Query multiple k-mers in batch
    fn query_batch(&self, kmers: Vec<String>) -> PyResult<Vec<PyQueryResult>> {
        let mut results = Vec::new();
        
        for kmer_str in kmers {
            // Create PyString and call the single query method
            unsafe {
                let py = Python::assume_gil_acquired();
                let py_string = PyString::new_bound(py, &kmer_str);
                let result = self.query(&py_string)?;
                results.push(result);
            }
        }
        
        Ok(results)
    }
    
    /// Get database statistics
    fn get_stats(&self) -> PyResult<PyDatabaseStats> {
        if !self.is_loaded {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not loaded"
            ));
        }
        
        Ok(PyDatabaseStats {
            kmer_size: self.header.kmer_size as usize,
            total_kmers: self.header.total_kmers,
            unique_kmers: self.header.unique_kmers,
            file_size: self.header.file_size,
            is_sorted: self.header.sorted,
            canonical: self.header.canonical,
        })
    }
    
    /// Get database file path
    #[getter]
    fn path(&self) -> String {
        self.path.clone()
    }
    
    /// Get k-mer size of database
    #[getter]
    fn kmer_size(&self) -> usize {
        self.header.kmer_size as usize
    }
    
    /// Check if database uses canonical k-mers
    #[getter]
    fn canonical(&self) -> bool {
        self.header.canonical
    }
    
    /// Get total number of k-mers in database
    #[getter]
    fn total_kmers(&self) -> u64 {
        self.header.total_kmers
    }
    
    /// Get number of unique k-mers
    #[getter]
    fn unique_kmers(&self) -> u64 {
        self.header.unique_kmers
    }
    
    /// Check if database is loaded
    #[getter]
    fn is_loaded(&self) -> bool {
        self.is_loaded
    }
    
    /// Get all k-mers and their counts
    fn get_all_kmers(&self) -> PyResult<Vec<HashMap<String, String>>> {
        if !self.is_loaded {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not loaded"
            ));
        }
        
        let mut results = Vec::new();
        if let Some(kmer_cache) = &self.kmer_cache {
            for (encoded_kmer, count) in kmer_cache {
                // For now, we'll store as hex string since we can't easily decode u128 back to string
                // In a real implementation, you might want to store the original string representation
                let kmer_hex = format!("{:x}", encoded_kmer);
                let mut result = HashMap::new();
                result.insert("kmer".to_string(), kmer_hex);
                result.insert("count".to_string(), count.to_string());
                results.push(result);
            }
        }
        
        Ok(results)
    }
    
    /// Check if a k-mer exists in the database
    fn exists(&self, kmer: &Bound<'_, PyString>) -> PyResult<bool> {
        let result = self.query(kmer)?;
        Ok(result.found)
    }
    
    /// Extract all k-mers that start with the given prefix (legacy linear search)
    fn extract_by_prefix(&self, prefix: &Bound<'_, PyString>) -> PyResult<HashMap<String, String>> {
        if !self.is_loaded {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not loaded"
            ));
        }
        
        let prefix_str = prefix.to_string();
        
        // Validate prefix format
        if prefix_str.trim().is_empty() {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Prefix cannot be empty"
            ));
        }
        
        if !prefix_str.chars().all(|c| matches!(c.to_ascii_uppercase(), 'A' | 'T' | 'C' | 'G')) {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Prefix contains invalid characters (only A, T, C, G allowed)"
            ));
        }
        
        let prefix_upper = prefix_str.to_uppercase();
        
        // Use linear search for now (legacy implementation)
        let mut matches = HashMap::new();
        
        if let Some(kmer_cache) = &self.kmer_cache {
            let kmer_size = self.header.kmer_size as usize;
            
            for (encoded_kmer, count) in kmer_cache {
                let decoded_kmer = decode_kmer_u128(*encoded_kmer, kmer_size);
                if decoded_kmer.starts_with(&prefix_upper) {
                    matches.insert(decoded_kmer, count.to_string());
                }
            }
        }
        
        Ok(matches)
    }
    
    /// Extract all k-mers that start with the given prefix using optimized algorithm
    #[pyo3(signature = (prefix))]
    fn extract_prefix_optimized(&self, prefix: &Bound<'_, PyString>) -> PyResult<PyPrefixQueryResult> {
        if !self.is_loaded {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not loaded"
            ));
        }
        
        let prefix_str = prefix.to_string();
        
        // Validate prefix format
        if prefix_str.trim().is_empty() {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Prefix cannot be empty"
            ));
        }
        
        if !prefix_str.chars().all(|c| matches!(c.to_ascii_uppercase(), 'A' | 'T' | 'C' | 'G')) {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Prefix contains invalid characters (only A, T, C, G allowed)"
            ));
        }
        
        let prefix_upper = prefix_str.to_uppercase();
        
        // Reload database for optimized extraction
        let database = match RKDatabase::from_file_path(Path::new(&self.path)) {
            Ok(db) => db,
            Err(e) => {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to load database: {}", e)
                ));
            }
        };
        
        // Use optimized extraction
        let result = match extract_prefix_optimized(&database, &prefix_upper) {
            Ok(result) => result,
            Err(e) => {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Prefix query failed: {}", e)
                ));
            }
        };
        
        // Convert matches to HashMap<String, String>
        let matches: HashMap<String, String> = result.matches
            .into_iter()
            .map(|(kmer, count)| (kmer, count.to_string()))
            .collect();
        
        Ok(PyPrefixQueryResult {
            matches,
            start_index: result.memory_block.start_index,
            end_index: result.memory_block.end_index,
            block_size: result.memory_block.block_size,
            is_sorted: result.memory_block.is_sorted,
            total_matches: result.total_matches,
            query_time_ms: result.query_time_ms,
        })
    }
    
    /// Extract k-mers by pattern (supports hybrid format like ATAC{N5}ACAC)
    #[pyo3(signature = (pattern))]
    fn extract_by_pattern(&self, pattern: &Bound<'_, PyString>) -> PyResult<HashMap<String, String>> {
        if !self.is_loaded {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not loaded"
            ));
        }
        
        let pattern_str = pattern.to_string();
        
        // Validate pattern format
        if pattern_str.trim().is_empty() {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Pattern cannot be empty"
            ));
        }
        
        let pattern_upper = pattern_str.to_uppercase();
        
        // Reload database for hybrid extraction
        let database = match RKDatabase::from_file_path(Path::new(&self.path)) {
            Ok(db) => db,
            Err(e) => {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to load database: {}", e)
                ));
            }
        };
        
        // Use hybrid extraction
        let result = match extract_hybrid_by_pattern(&database, &pattern_upper) {
            Ok(result) => result,
            Err(e) => {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Pattern query failed: {}", e)
                ));
            }
        };
        
        // Convert matches to HashMap<String, String>
        let matches: HashMap<String, String> = result.matches
            .into_iter()
            .map(|(kmer, count)| (kmer, count.to_string()))
            .collect();
        
        Ok(matches)
    }
    
    /// Parse hybrid pattern without executing query
    #[pyo3(signature = (pattern))]
    fn parse_hybrid_pattern(&self, pattern: &Bound<'_, PyString>) -> PyResult<HashMap<String, String>> {
        let pattern_str = pattern.to_string();
        let pattern_upper = pattern_str.to_uppercase();
        
        let result = match parse_hybrid_pattern(&pattern_upper) {
            Ok(pattern) => {
                let mut info = HashMap::new();
                info.insert("prefix".to_string(), pattern.prefix);
                info.insert("suffix".to_string(), pattern.suffix);
                info.insert("n_count".to_string(), pattern.n_count.to_string());
                info.insert("total_length".to_string(), pattern.total_length.to_string());
                info.insert("n_positions".to_string(), format!("{:?}", pattern.n_positions));
                info
            }
            Err(e) => {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Pattern parsing failed: {}", e)
                ));
            }
        };
        
        Ok(result)
    }
    
    /// Extract all k-mers that end with the given suffix
    fn extract_by_suffix(&self, suffix: &Bound<'_, PyString>) -> PyResult<HashMap<String, String>> {
        if !self.is_loaded {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not loaded"
            ));
        }
        
        let suffix_str = suffix.to_string();
        
        // Validate suffix format
        if suffix_str.trim().is_empty() {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Suffix cannot be empty"
            ));
        }
        
        if !suffix_str.chars().all(|c| matches!(c.to_ascii_uppercase(), 'A' | 'T' | 'C' | 'G' | 'N')) {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Suffix contains invalid characters (only A, T, C, G, N allowed)"
            ));
        }
        
        let suffix_upper = suffix_str.to_uppercase();
        
        // Use linear search for now
        let mut matches = HashMap::new();
        
        if let Some(kmer_cache) = &self.kmer_cache {
            use rustkmer::kmer::encoding::decode_kmer_u128;
            
            let kmer_size = self.header.kmer_size as usize;
            
            for (encoded_kmer, count) in kmer_cache {
                let decoded_kmer = decode_kmer_u128(*encoded_kmer, kmer_size);
                if decoded_kmer.ends_with(&suffix_upper) {
                    matches.insert(decoded_kmer, count.to_string());
                }
            }
        }
        
        Ok(matches)
    }
    
    /// Smart wildcard query that automatically chooses the best strategy (placeholder)
    fn smart_wildcard_query(&self, pattern: &Bound<'_, PyString>) -> PyResult<HashMap<String, String>> {
        if !self.is_loaded {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not loaded"
            ));
        }
        
        let pattern_str = pattern.to_string();
        let pattern_upper = pattern_str.to_uppercase();
        
        println!("🔍 Smart wildcard query: {} (placeholder implementation)", pattern_upper);
        println!("   This feature will be implemented in the next version");
        
        // Return empty results for now
        Ok(HashMap::new())
    }
    
    /// Get current loading mode
    #[getter]
    fn load_mode(&self) -> String {
        match self.load_mode {
            LoadMode::Preload => "preload".to_string(),
            LoadMode::MemoryMapped => "memory_mapped".to_string(),
            LoadMode::Lazy => "lazy".to_string(),
        }
    }
    
    /// Get memory usage information
    fn get_memory_usage(&self) -> PyResult<HashMap<String, usize>> {
        let mut usage = HashMap::new();
        
        match &self.load_mode {
            LoadMode::Preload => {
                if let Some(cache) = &self.kmer_cache {
                    usage.insert("cache_size".to_string(), cache.len());
                    usage.insert("memory_bytes".to_string(), cache.len() * std::mem::size_of::<(u128, u32)>());
                }
            },
            LoadMode::MemoryMapped => {
                if let Some(file) = &self.mmapped_file {
                    if let Ok(metadata) = file.metadata() {
                        usage.insert("file_size".to_string(), metadata.len() as usize);
                    }
                }
                usage.insert("implementation".to_string(), 1); // Mark as direct I/O implementation
            },
            LoadMode::Lazy => {
                if let Some(cached) = &self.cached_entries {
                    usage.insert("index_size".to_string(), cached.len());
                    usage.insert("memory_bytes".to_string(), cached.len() * std::mem::size_of::<(u128, u32)>());
                }
            }
        }
        
        Ok(usage)
    }
    
    /// Close database and release memory resources
    fn close(&mut self) -> PyResult<String> {
        // Debug: Print to stderr to see if method is called
        eprintln!("DEBUG: close() method called!");
        
        // Clear all cached data to free memory
        self.kmer_cache = None;
        self.file_buffer = None;
        self.entries = None;
        self.cached_entries = None;
        self.mmap_data = None;
        
        // Note: mmapped_file is left as-is since it's automatically managed by OS
        // when the file handle is dropped
        
        Ok("Database closed and memory released".to_string())
    }
    
    /// Read a k-mer entry from file using direct I/O (like CLI --no-load mode)
    fn read_entry_from_file(&self, index: u64) -> PyResult<(u128, u32)> {
        use std::io::{Seek, SeekFrom, Read};
        
        let mut file = self.mmapped_file.as_ref()
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("File not available"))?;
        
        // Fix for incorrect data_offset in header
        let actual_data_offset = if self.header.data_offset < 40 {
            42  // Use correct offset when header value is too small
        } else if self.header.data_offset > 1000 {
            42  // Use correct offset when header value is too large
        } else {
            self.header.data_offset
        };
        
        let entry_offset = actual_data_offset + (index * 20); // 16 + 4 bytes per entry (u128 + u32)
        
        // Seek to the entry position
        file.seek(SeekFrom::Start(entry_offset))
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Failed to seek: {}", e)))?;
        
        // Read k-mer (u128 = 16 bytes)
        let mut kmer_bytes = [0u8; 16];
        file.read_exact(&mut kmer_bytes)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Failed to read k-mer: {}", e)))?;
        let kmer = u128::from_le_bytes(kmer_bytes);
        
        // Read count (u32 = 4 bytes)
        let mut count_bytes = [0u8; 4];
        file.read_exact(&mut count_bytes)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Failed to read count: {}", e)))?;
        let count = u32::from_le_bytes(count_bytes);
        
        Ok((kmer, count))
    }
    
}