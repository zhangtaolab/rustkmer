//! PyDatabase - Python wrapper for RustKmer Database operations
//!
//! This module provides a Python class that wraps the Rust Database
//! functionality for querying k-mer databases.

use pyo3::prelude::*;
use pyo3::types::PyString;
use std::path::Path;
use std::collections::HashMap;
use rustkmer::database::format::{RKDatabase, DatabaseHeader, KmerEntry};
use rustkmer::kmer::encoding::encode_kmer_u128;
use rustkmer::kmer::canonical::canonical_kmer_u128;

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
    path: String,
    /// Database header
    header: DatabaseHeader,
    /// In-memory cache of k-mers for fast querying
    kmer_cache: HashMap<u128, u32>,
    /// Whether database is loaded
    is_loaded: bool,
}

#[pymethods]
impl PyDatabase {
    /// Load a k-mer database from file
    #[new]
    fn new(path: &Bound<'_, PyString>, memory_mapped: bool) -> PyResult<Self> {
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
        
        // Build k-mer cache for fast querying
        let mut kmer_cache = HashMap::new();
        for entry in &database.entries {
            // Store both the original and canonical form if needed
            kmer_cache.insert(entry.kmer, entry.count);
        }
        
        Ok(Self {
            path: path_str,
            header,
            kmer_cache,
            is_loaded: true,
        })
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
        
        // Look up in cache
        let count = self.kmer_cache.get(&search_kmer).copied().unwrap_or(0);
        
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
    fn get_all_kmers(&self) -> PyResult<Vec<HashMap<String, u32>>> {
        if !self.is_loaded {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Database not loaded"
            ));
        }
        
        let mut results = Vec::new();
        for (encoded_kmer, count) in &self.kmer_cache {
            // For now, we'll store as hex string since we can't easily decode u128 back to string
            // In a real implementation, you might want to store the original string representation
            let kmer_hex = format!("{:x}", encoded_kmer);
            let mut result = HashMap::new();
            result.insert("kmer".to_string(), *count);
            result.insert("encoded".to_string(), 0); // Placeholder for encoded form
            results.push(result);
        }
        
        Ok(results)
    }
    
    /// Check if a k-mer exists in the database
    fn exists(&self, kmer: &Bound<'_, PyString>) -> PyResult<bool> {
        let result = self.query(kmer)?;
        Ok(result.found)
    }
}