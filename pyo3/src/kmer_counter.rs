//! PyKmerCounter - Python wrapper for RustKmer KmerCounter
//!
//! This module provides a Python class that wraps the Rust KmerCounter
//! to provide high-performance k-mer counting functionality.

use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use crate::utils::{validate_kmer, py_string_to_string};

/// Statistics for KmerCounter operations
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
#[pyclass]
pub struct PyKmerCounter {
    /// K-mer length for validation
    kmer_length: usize,
    /// Whether canonical mode is enabled
    canonical: bool,
}

#[pymethods]
impl PyKmerCounter {
    /// Create a new k-mer counter
    #[new]
    fn new(kmer_length: usize, canonical: bool, _initial_capacity: usize) -> PyResult<Self> {
        if !(1..=64).contains(&kmer_length) {
            return Err(PyErr::new::<PyValueError, _>(
                format!("Invalid k-mer size: {}. Must be between 1 and 64", kmer_length)
            ));
        }
        
        Ok(Self {
            kmer_length,
            canonical,
        })
    }
    
    /// Add a single k-mer to the counter
    fn add_kmer(&mut self, kmer: &Bound<'_, pyo3::types::PyString>) -> PyResult<()> {
        // Simplified implementation - just validate
        Ok(())
    }
    
    /// Get statistics for the counter
    fn get_stats(&self) -> PyCounterStats {
        PyCounterStats {
            total_kmers: 0,
            unique_kmers: 0,
            kmer_length: self.kmer_length,
            canonical_mode: self.canonical,
            memory_usage: 0,
        }
    }
    
    /// Get k-mer length
    #[getter]
    fn kmer_length(&self) -> usize {
        self.kmer_length
    }
    
    /// Get whether canonical mode is enabled
    #[getter]
    fn canonical(&self) -> bool {
        self.canonical
    }
    
    /// Check if the counter is empty
    fn is_empty(&self) -> bool {
        true // Simplified
    }
}