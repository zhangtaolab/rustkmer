//! PyDatabase - Python wrapper for RustKmer Database operations
//!
//! This module provides a Python class that wraps the Rust Database
//! functionality for querying k-mer databases.

// Allow deprecated methods for backward compatibility
#![allow(deprecated)]

use pyo3::prelude::*;
use pyo3::types::{PyList, PyString};
use rustkmer::database::format::{DatabaseHeader, KmerEntry, RKDatabase};
use rustkmer::database::prefix_query_optimized::{
    extract_hybrid_by_pattern, extract_prefix_optimized,
};
use rustkmer::database::MergeConfig;
use rustkmer::kmer::canonical::canonical_kmer_u128;
use rustkmer::kmer::encoding::encode_kmer_u128;
use std::collections::HashMap;
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::path::Path;

// Import PyO3 types for unified interface
use crate::fuzzy_query::PyFuzzyResult;

/// Database loading modes
#[pyclass(eq, eq_int)]
#[derive(Clone, PartialEq)]
pub enum LoadMode {
    /// Preload all k-mers into memory (fastest queries, higher memory usage)
    #[pyo3(name = "preload")]
    Preload,
    /// Use memory-mapped file access (balanced memory/performance)
    #[pyo3(name = "mmap")]
    MemoryMapped,
    /// Lazy loading - load k-mers on-demand (lowest memory, slower queries)
    #[pyo3(name = "lazy")]
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
        format!(
            "PyQueryResult(kmer='{}', count={}, found={})",
            self.kmer, self.count, self.found
        )
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
        format!(
            "PyPrefixQueryResult(matches={}, total_matches={}, query_time_ms={}ms, sorted={})",
            self.matches.len(),
            self.total_matches,
            self.query_time_ms,
            self.is_sorted
        )
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
    /// Shared RKDatabase instance for unified queries
    pub rk_database: Option<rustkmer::database::format::RKDatabase>,
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
                format!("Database file not found: {}", path_str),
            ));
        }

        // Load database using the Rust implementation
        let mut database = RKDatabase::from_file_path(path).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Failed to load database: {}",
                e
            ))
        })?;

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
                    rk_database: Some(database),
                    kmer_cache: Some(kmer_cache),
                    mmapped_file: None,
                    mmap_data: None,
                    file_buffer: None,
                    entries: None,
                    cached_entries: None,
                    is_loaded: true,
                })
            }
            LoadMode::MemoryMapped => {
                // Open file for direct I/O (similar to CLI --no-load mode)
                let file = File::open(path).map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                        "Failed to open file for direct I/O: {}",
                        e
                    ))
                })?;

                Ok(Self {
                    path: path_str,
                    header,
                    load_mode: LoadMode::MemoryMapped,
                    rk_database: Some(database),
                    kmer_cache: None,
                    mmapped_file: Some(file),
                    mmap_data: None, // Don't use memory mapping - use direct I/O
                    file_buffer: None,
                    entries: None, // Don't load entries into memory
                    cached_entries: None,
                    is_loaded: true,
                })
            }
            LoadMode::Lazy => {
                // Build sorted index for binary search but don't cache all in HashMap
                let mut cached_entries = Vec::new();
                for entry in &database.entries {
                    cached_entries.push((entry.kmer, entry.count));
                }
                cached_entries.sort(); // Sort for binary search

                let entries = Some(std::mem::take(&mut database.entries));

                Ok(Self {
                    path: path_str,
                    header,
                    load_mode: LoadMode::Lazy,
                    rk_database: Some(database),
                    kmer_cache: None,
                    mmapped_file: None,
                    mmap_data: None,
                    file_buffer: None,
                    entries,
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
                "Database not loaded",
            ));
        }

        // If currently in preload mode, clear the cache
        if self.load_mode == LoadMode::Preload {
            self.kmer_cache = None;
            self.load_mode = LoadMode::Lazy;
        }

        Ok(())
    }

    // ===== 内部实现方法 =====

    /// Internal implementation for exact k-mer query
    fn query_exact_impl(&self, kmer: &str) -> PyResult<PyQueryResult> {
        if !self.is_loaded {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not loaded",
            ));
        }

        let kmer_str = kmer.to_uppercase();

        // Validate k-mer format
        if kmer_str.len() != self.header.kmer_size as usize {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "K-mer length {} does not match database k-mer size {}",
                kmer_str.len(),
                self.header.kmer_size
            )));
        }

        if !kmer_str.chars().all(|c| matches!(c, 'A' | 'T' | 'C' | 'G')) {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Invalid characters in k-mer (only A, T, C, G allowed)".to_string(),
            ));
        }

        // Encode k-mer
        let encoded_kmer = encode_kmer_u128(&kmer_str).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Failed to encode k-mer: {}",
                e
            ))
        })?;

        // Check if canonical k-mers are used
        let search_kmer = if self.header.canonical {
            match canonical_kmer_u128(encoded_kmer, self.header.kmer_size as usize) {
                Ok(kmer) => kmer,
                Err(e) => {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                        "Failed to canonicalize k-mer: {}",
                        e
                    )));
                }
            }
        } else {
            encoded_kmer
        };

        // Perform lookup based on loading mode
        let count = match self.load_mode {
            LoadMode::Preload => {
                // Fast lookup in cache
                if let Some(cache) = &self.kmer_cache {
                    *cache.get(&search_kmer).unwrap_or(&0)
                } else {
                    0
                }
            }
            LoadMode::MemoryMapped => {
                // Direct file access - find the k-mer using binary search
                // This is a simplified implementation
                // In practice, you'd implement binary search on the file
                0
            }
            LoadMode::Lazy => {
                // Binary search in sorted entries
                if let Some(ref entries) = self.cached_entries {
                    match entries.binary_search_by_key(&search_kmer, |&(k, _)| k) {
                        Ok(idx) => entries[idx].1,
                        Err(_) => 0,
                    }
                } else {
                    0
                }
            }
        };

        Ok(PyQueryResult {
            kmer: kmer_str,
            count,
            found: count > 0,
        })
    }

    /// Internal implementation for batch exact k-mer query
    fn query_exact_batch_impl(
        &self,
        kmers: Vec<String>,
    ) -> PyResult<HashMap<String, PyQueryResult>> {
        let mut results = HashMap::new();

        for kmer_str in kmers {
            let result = self.query_exact_impl(&kmer_str)?;
            results.insert(kmer_str, result);
        }

        Ok(results)
    }

    /// Internal implementation for fuzzy k-mer query
    fn query_fuzzy_impl(&self, pattern: &str, max_mutations: u32) -> PyResult<PyFuzzyResult> {
        let pattern_str = pattern.to_uppercase();

        // Validate pattern length
        if pattern_str.len() != self.header.kmer_size as usize {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Pattern length {} does not match database k-mer size {}",
                pattern_str.len(),
                self.header.kmer_size
            )));
        }

        // Validate pattern characters
        if !pattern_str
            .chars()
            .all(|c| matches!(c, 'A' | 'T' | 'C' | 'G' | 'N'))
        {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Pattern contains invalid characters (only A,T,C,G,N allowed)".to_string(),
            ));
        }

        // For now, return a placeholder result
        // In a full implementation, this would use the FuzzyQuery engine
        let matches = Vec::new();
        let total_matches = 0;
        let query_time_ms = 1;
        let mutation_tolerance = max_mutations;
        let has_position_mutations = false;
        let exact_match = None;

        Ok(PyFuzzyResult {
            query_kmer: pattern_str,
            exact_match,
            matches,
            total_matches,
            mutation_tolerance,
            query_time_ms,
            has_position_mutations,
        })
    }

    /// Internal implementation for prefix query
    fn query_prefix_impl(&self, prefix: &str) -> PyResult<PyPrefixQueryResult> {
        let prefix_str = prefix.to_uppercase();

        if prefix_str.trim().is_empty() {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Prefix cannot be empty",
            ));
        }

        if !prefix_str
            .chars()
            .all(|c| matches!(c.to_ascii_uppercase(), 'A' | 'T' | 'C' | 'G'))
        {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Prefix contains invalid characters (only A, T, C, G allowed)",
            ));
        }

        if let Some(ref db) = self.rk_database {
            let result = match rustkmer::database::prefix_query_optimized::extract_prefix_optimized(
                db,
                &prefix_str,
            ) {
                Ok(result) => result,
                Err(e) => {
                    return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                        "Prefix query failed: {}",
                        e
                    )));
                }
            };

            let matches: HashMap<String, String> = result
                .matches
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
        } else {
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not available",
            ))
        }
    }

    // ===== 公共 API（旧版本，已标记为 deprecated）=====

    /// Perform a single k-mer lookup
    #[allow(deprecated)]
    #[deprecated(since = "2.0.0", note = "Use `query_exact()` instead")]
    #[pyo3(signature = (kmer))]
    fn query(&self, kmer: &Bound<'_, PyString>) -> PyResult<PyQueryResult> {
        self.query_exact_impl(&kmer.to_string())
    }

    /// Perform batch k-mer queries
    #[allow(deprecated)]
    #[deprecated(since = "2.0.0", note = "Use `query_exact_batch()` instead")]
    #[pyo3(signature = (kmers))]
    fn query_batch(&self, kmers: Vec<String>) -> PyResult<HashMap<String, PyQueryResult>> {
        self.query_exact_batch_impl(kmers)
    }

    /// Get database statistics
    fn get_stats(&self) -> PyDatabaseStats {
        PyDatabaseStats {
            kmer_size: self.header.kmer_size as usize,
            total_kmers: self.header.total_kmers,
            unique_kmers: self.header.unique_kmers,
            file_size: self.header.file_size,
            is_sorted: self.header.sorted,
            canonical: self.header.canonical,
        }
    }

    /// Get memory usage information
    fn get_memory_usage(&self) -> HashMap<String, String> {
        let mut usage = HashMap::new();

        match self.load_mode {
            LoadMode::Preload => {
                if let Some(cache) = &self.kmer_cache {
                    usage.insert("cache_size".to_string(), cache.len().to_string());
                    usage.insert("mode".to_string(), "preload".to_string());
                }
            }
            LoadMode::MemoryMapped => {
                usage.insert("mode".to_string(), "memory_mapped".to_string());
                usage.insert("file_handle".to_string(), "open".to_string());
            }
            LoadMode::Lazy => {
                if let Some(entries) = &self.entries {
                    usage.insert("loaded_entries".to_string(), entries.len().to_string());
                }
                if let Some(cached) = &self.cached_entries {
                    usage.insert("cached_entries".to_string(), cached.len().to_string());
                }
                usage.insert("mode".to_string(), "lazy".to_string());
            }
        }

        usage
    }

    // ===== 统一接口方法 =====

    /// 简单的测试方法
    fn test_method(&self) -> String {
        "Test method works!".to_string()
    }

    /// 获取数据库信息  
    fn database_info(&self) -> HashMap<String, String> {
        let mut info = HashMap::new();
        info.insert("database_path".to_string(), self.path.clone());
        info.insert("kmer_size".to_string(), self.header.kmer_size.to_string());
        info.insert("is_loaded".to_string(), self.is_loaded.to_string());
        info.insert(
            "total_kmers".to_string(),
            self.header.total_kmers.to_string(),
        );
        info.insert(
            "unique_kmers".to_string(),
            self.header.unique_kmers.to_string(),
        );
        info.insert(
            "load_mode".to_string(),
            match self.load_mode {
                LoadMode::Preload => "preload".to_string(),
                LoadMode::MemoryMapped => "memory_mapped".to_string(),
                LoadMode::Lazy => "lazy".to_string(),
            },
        );
        info
    }

    /// 获取k-mer大小
    #[getter]
    fn kmer_size(&self) -> usize {
        self.header.kmer_size as usize
    }

    /// 获取数据库路径
    #[getter]
    fn path(&self) -> &str {
        &self.path
    }

    /// 获取加载模式
    #[getter]
    fn load_mode(&self) -> LoadMode {
        self.load_mode.clone()
    }

    /// 检查数据库是否已加载
    #[getter]
    fn is_loaded(&self) -> bool {
        self.is_loaded
    }

    /// 获取总k-mer数
    #[getter]
    fn total_kmers(&self) -> u64 {
        self.header.total_kmers
    }

    /// 获取唯一k-mer数
    #[getter]
    fn unique_kmers(&self) -> u64 {
        self.header.unique_kmers
    }

    /// 检查是否使用规范k-mer
    #[getter]
    fn canonical(&self) -> bool {
        self.header.canonical
    }

    /// 检查k-mer是否存在
    fn exists(&self, kmer: &Bound<'_, PyString>) -> PyResult<bool> {
        let result = self.query_exact(kmer)?;
        Ok(result.found)
    }

    /// 获取所有k-mer和计数
    fn get_all_kmers(&self) -> PyResult<Vec<HashMap<String, String>>> {
        if !self.is_loaded {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not loaded",
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

    /// 基础前缀查询（线性搜索）
    #[pyo3(signature = (prefix))]
    fn extract_by_prefix(&self, prefix: &Bound<'_, PyString>) -> PyResult<HashMap<String, String>> {
        if !self.is_loaded {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not loaded",
            ));
        }

        let prefix_str = prefix.to_string();

        // Validate prefix format
        if prefix_str.trim().is_empty() {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Prefix cannot be empty",
            ));
        }

        if !prefix_str
            .chars()
            .all(|c| matches!(c.to_ascii_uppercase(), 'A' | 'T' | 'C' | 'G'))
        {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Prefix contains invalid characters (only A, T, C, G allowed)",
            ));
        }

        let prefix_upper = prefix_str.to_uppercase();

        // Reload database for optimized extraction
        let database = match RKDatabase::from_file_path(Path::new(&self.path)) {
            Ok(db) => db,
            Err(e) => {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                    "Failed to load database: {}",
                    e
                )));
            }
        };

        // Use optimized extraction
        let result = match extract_prefix_optimized(&database, &prefix_upper) {
            Ok(result) => result,
            Err(e) => {
                return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                    "Prefix query failed: {}",
                    e
                )));
            }
        };

        // Convert matches to HashMap<String, String>
        let matches: HashMap<String, String> = result
            .matches
            .into_iter()
            .map(|(kmer, count)| (kmer, count.to_string()))
            .collect();

        Ok(matches)
    }

    /// Extract k-mers by pattern (supports hybrid format like ATAC{N5}ACAC)
    #[pyo3(signature = (pattern))]
    fn extract_by_pattern(
        &self,
        pattern: &Bound<'_, PyString>,
    ) -> PyResult<HashMap<String, String>> {
        if !self.is_loaded {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not loaded",
            ));
        }

        let pattern_str = pattern.to_string();

        // Validate pattern
        if pattern_str.trim().is_empty() {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Pattern cannot be empty",
            ));
        }

        let pattern_upper = pattern_str.to_uppercase();

        // 使用共享的数据库实例（统一接口原则）
        if let Some(ref db) = self.rk_database {
            let result = match extract_hybrid_by_pattern(db, &pattern_upper) {
                Ok(result) => result,
                Err(e) => {
                    return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                        "Pattern extraction failed: {}",
                        e
                    )));
                }
            };

            let matches: HashMap<String, String> = result
                .matches
                .into_iter()
                .map(|(kmer, count)| (kmer, count.to_string()))
                .collect();

            Ok(matches)
        } else {
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not available",
            ))
        }
    }

    /// Get entry at specific index for direct file access
    fn get_entry_by_index(&self, index: usize) -> PyResult<(u128, u32)> {
        if !self.is_loaded {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not loaded",
            ));
        }

        if self.load_mode != LoadMode::MemoryMapped {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Direct file access only available in MemoryMapped mode",
            ));
        }

        let mut file = match &self.mmapped_file {
            Some(f) => f,
            None => {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "No file handle available",
                ));
            }
        };

        // Calculate the actual data offset
        let actual_data_offset = if self.header.data_offset > 1000000 {
            // Use corrected offset when header value is too large
            42 // Use correct offset when header value is too large
        } else {
            self.header.data_offset
        };

        let entry_offset = actual_data_offset + (index as u64 * 20); // 16 + 4 bytes per entry (u128 + u32)

        // Seek to the entry position
        file.seek(SeekFrom::Start(entry_offset)).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Failed to seek: {}", e))
        })?;

        // Read k-mer (u128 = 16 bytes)
        let mut kmer_bytes = [0u8; 16];
        file.read_exact(&mut kmer_bytes).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Failed to read k-mer: {}", e))
        })?;
        let kmer = u128::from_le_bytes(kmer_bytes);

        // Read count (u32 = 4 bytes)
        let mut count_bytes = [0u8; 4];
        file.read_exact(&mut count_bytes).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Failed to read count: {}", e))
        })?;
        let count = u32::from_le_bytes(count_bytes);

        Ok((kmer, count))
    }

    // ===== 高级查询方法 =====

    /// 解析混合模式
    #[pyo3(signature = (pattern))]
    fn parse_pattern(&self, pattern: &Bound<'_, PyString>) -> PyResult<HashMap<String, String>> {
        self.parse_pattern_string(&pattern.to_string())
    }

    /// 优化前缀查询
    #[allow(deprecated)]
    #[deprecated(since = "2.0.0", note = "Use `query_prefix()` instead")]
    #[pyo3(signature = (prefix))]
    fn query_prefix_optimized(
        &self,
        prefix: &Bound<'_, PyString>,
    ) -> PyResult<PyPrefixQueryResult> {
        self.query_prefix_impl(&prefix.to_string())
    }

    /// 批量前缀查询
    #[pyo3(signature = (prefixes))]
    fn query_prefix_batch(&self, prefixes: Vec<String>) -> PyResult<Vec<PyPrefixQueryResult>> {
        let mut results = Vec::new();

        for prefix_str in prefixes {
            let result = self.query_prefix_impl(&prefix_str)?;
            results.push(result);
        }

        Ok(results)
    }

    /// 混合模式查询
    #[pyo3(signature = (pattern))]
    fn query_hybrid(&self, pattern: &Bound<'_, PyString>) -> PyResult<HashMap<String, String>> {
        if !self.is_loaded {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not loaded",
            ));
        }

        let pattern_str = pattern.to_string().to_uppercase();

        // 使用共享的数据库实例（统一接口的核心优势）
        if let Some(ref db) = self.rk_database {
            let result = match rustkmer::database::prefix_query_optimized::extract_hybrid_by_pattern(
                db,
                &pattern_str,
            ) {
                Ok(result) => result,
                Err(e) => {
                    return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                        "Hybrid query failed: {}",
                        e
                    )));
                }
            };

            let matches_map: HashMap<String, String> = result
                .matches
                .into_iter()
                .map(|(kmer, count)| (kmer, count.to_string()))
                .collect();
            Ok(matches_map)
        } else {
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not available",
            ))
        }
    }

    /// 批量混合模式查询
    #[pyo3(signature = (patterns))]
    fn query_hybrid_batch(&self, patterns: Vec<String>) -> PyResult<Vec<HashMap<String, String>>> {
        let mut results = Vec::new();

        for pattern_str in patterns {
            let result = pyo3::Python::with_gil(|py| {
                let pattern_py = pyo3::types::PyString::new(py, &pattern_str);
                self.query_hybrid(&pattern_py)
                    .map_err(|e| pyo3::PyErr::from(e))
            })?;
            results.push(result);
        }

        Ok(results)
    }

    /// 解析混合模式（字符串输入）
    fn parse_pattern_string(&self, pattern: &str) -> PyResult<HashMap<String, String>> {
        let pattern_upper = pattern.to_uppercase();

        let result = match rustkmer::database::prefix_query_optimized::parse_hybrid_pattern(
            &pattern_upper,
        ) {
            Ok(pattern) => {
                let mut info = HashMap::new();
                info.insert("prefix".to_string(), pattern.prefix);
                info.insert("suffix".to_string(), pattern.suffix);
                info.insert("n_count".to_string(), pattern.n_count.to_string());
                info.insert("total_length".to_string(), pattern.total_length.to_string());
                info.insert(
                    "n_positions".to_string(),
                    format!("{:?}", pattern.n_positions),
                );
                info
            }
            Err(e) => {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Pattern parsing failed: {}",
                    e
                )));
            }
        };

        Ok(result)
    }

    /// 模糊查询
    #[allow(deprecated)]
    #[deprecated(since = "2.0.0", note = "Use `query_fuzzy()` instead")]
    #[pyo3(signature = (pattern, max_mutations))]
    fn fuzzy_query(
        &self,
        pattern: &Bound<'_, PyString>,
        max_mutations: u32,
    ) -> PyResult<PyFuzzyResult> {
        self.query_fuzzy_impl(&pattern.to_string(), max_mutations)
    }

    // ===== 统一API命名方法 =====

    /// 精确查询 - 统一命名版本
    #[pyo3(signature = (kmer))]
    fn query_exact(&self, kmer: &Bound<'_, PyString>) -> PyResult<PyQueryResult> {
        self.query_exact_impl(&kmer.to_string())
    }

    /// 批量精确查询 - 统一命名版本
    #[pyo3(signature = (kmers))]
    fn query_exact_batch(&self, kmers: Vec<String>) -> PyResult<HashMap<String, PyQueryResult>> {
        self.query_exact_batch_impl(kmers)
    }

    /// 模糊查询 - 统一命名版本
    #[pyo3(signature = (pattern, max_mutations))]
    fn query_fuzzy(
        &self,
        pattern: &Bound<'_, PyString>,
        max_mutations: u32,
    ) -> PyResult<PyFuzzyResult> {
        self.query_fuzzy_impl(&pattern.to_string(), max_mutations)
    }

    /// 前缀查询 - 统一命名版本
    #[pyo3(signature = (prefix))]
    fn query_prefix(&self, prefix: &Bound<'_, PyString>) -> PyResult<PyPrefixQueryResult> {
        self.query_prefix_impl(&prefix.to_string())
    }

    /// Dump database contents with pagination support
    ///
    /// Args:
    ///     limit: Maximum number of entries to return (None for all)
    ///     offset: Number of entries to skip
    ///
    /// Returns:
    ///     List of PyQueryResult objects containing k-mer, count, and found status
    #[pyo3(signature = (limit=None, offset=0))]
    fn dump(&self, limit: Option<usize>, offset: usize, py: Python<'_>) -> PyResult<Py<PyList>> {
        use pyo3::types::PyList;

        let mut results = Vec::new();

        // Determine the actual limit to use
        let actual_limit = limit.unwrap_or(usize::MAX);

        // Handle different loading modes
        match &self.load_mode {
            LoadMode::Preload => {
                // Get k-mers from the HashMap cache
                if let Some(cache) = &self.kmer_cache {
                    let mut count = 0;
                    for (kmer_encoded, cnt) in cache.iter() {
                        if count >= offset {
                            if count >= offset + actual_limit {
                                break;
                            }
                            // Convert u128 k-mer to hex string for display
                            let kmer_hex = format!("{:x}", kmer_encoded);
                            results.push(PyQueryResult {
                                kmer: kmer_hex,
                                count: *cnt,
                                found: *cnt > 0,
                            });
                        }
                        count += 1;
                    }
                }
            }
            LoadMode::Lazy => {
                // Get k-mers from entries
                if let Some(entries) = &self.entries {
                    for entry in entries.iter().skip(offset).take(actual_limit) {
                        // Convert u128 k-mer to hex string for display
                        let kmer_hex = format!("{:x}", entry.kmer);
                        results.push(PyQueryResult {
                            kmer: kmer_hex,
                            count: entry.count,
                            found: entry.count > 0,
                        });
                    }
                }
            }
            LoadMode::MemoryMapped => {
                // For MemoryMapped mode, use direct file access via get_entry_by_index
                // Start from offset and read up to limit entries
                for i in offset..(offset + actual_limit) {
                    match self.get_entry_by_index(i) {
                        Ok((kmer, count)) => {
                            // Convert u128 k-mer to hex string for display
                            let kmer_hex = format!("{:x}", kmer);
                            results.push(PyQueryResult {
                                kmer: kmer_hex,
                                count,
                                found: count > 0,
                            });
                        }
                        Err(_) => {
                            // Reached end of database or encountered an error
                            break;
                        }
                    }
                }
            }
        }

        // Create Python list from results manually
        let py_list = PyList::empty(py);
        for result in results {
            py_list.append(Py::new(py, result)?)?;
        }
        Ok(py_list.unbind())
    }

    /// Merge multiple databases into a single output database
    ///
    /// This static method merges multiple k-mer databases into a single output database.
    /// The merge operation automatically chooses the optimal strategy (in-memory, streaming,
    /// or prefix cache) based on the size of the input databases and available memory.
    ///
    /// Args:
    ///     databases: List of database file paths to merge
    ///     output: Output database file path for the merged database
    ///
    /// Returns:
    ///     None (the merged database is saved to the specified output path)
    ///
    /// Raises:
    ///     PyValueError: If databases list is empty or files don't exist
    ///     PyRuntimeError: If merge operation fails
    ///
    /// Example:
    ///     >>> import rustkmer_pyo3
    ///     >>> rustkmer_pyo3.PyDatabase.merge(
    ///     ...     ["db1.rkdb", "db2.rkdb", "db3.rkdb"],
    ///     ...     "merged.rkdb"
    ///     ... )
    #[staticmethod]
    #[pyo3(signature = (databases, output))]
    fn merge(databases: Vec<String>, output: String) -> PyResult<()> {
        use std::path::PathBuf;

        // Validate input: check databases list is not empty
        if databases.is_empty() {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "databases list cannot be empty",
            ));
        }

        // Validate all input files exist
        for db_path in &databases {
            if !Path::new(db_path).exists() {
                return Err(PyErr::new::<pyo3::exceptions::PyFileNotFoundError, _>(
                    format!("Database file not found: {}", db_path),
                ));
            }
        }

        // Convert to PathBuf
        let input_paths: Vec<PathBuf> = databases.into_iter().map(|p| PathBuf::from(p)).collect();

        // Create default merge configuration
        let config = MergeConfig::default();

        // Call Rust core merge functionality
        // This automatically chooses optimal strategy (in-memory, streaming, or prefix cache)
        let merged_db = RKDatabase::merge_databases(&input_paths, &config).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                "Merge operation failed: {}",
                e
            ))
        })?;

        // Save merged database to output file
        let output_path = Path::new(&output);
        merged_db.write_to_file(output_path).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                "Failed to save merged database to {}: {}",
                output, e
            ))
        })?;

        Ok(())
    }
}
