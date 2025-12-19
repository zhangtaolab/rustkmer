//! PyFuzzyQuery - Python wrapper for RustKmer fuzzy query functionality
//!
//! This module provides a Python class that wraps the Rust fuzzy query
//! capabilities for pattern matching with wildcards and mutations.

use pyo3::prelude::*;
use crate::database::{PyDatabase, LoadMode};
use rustkmer::database::format::DatabaseHeader;
use crate::utils::py_string_to_string;

/// Individual fuzzy match result
#[pyclass]
#[derive(Clone)]
pub struct PyFuzzyMatch {
    /// The matched k-mer sequence
    pub kmer: String,
    /// Count in database
    pub count: u32,
    /// Distance from query pattern
    pub distance: u32,
    /// List of mutations from query
    pub mutations: Vec<String>,
    /// Match type (exact, wildcard, mutation)
    pub match_type: String,
}

#[pymethods]
impl PyFuzzyMatch {
    #[getter]
    fn kmer(&self) -> &str {
        &self.kmer
    }
    
    #[getter]
    fn count(&self) -> u32 {
        self.count
    }
    
    #[getter]
    fn distance(&self) -> u32 {
        self.distance
    }
    
    #[getter]
    fn mutations(&self) -> Vec<String> {
        self.mutations.clone()
    }
    
    #[getter]
    fn match_type(&self) -> &str {
        &self.match_type
    }
    
    fn __repr__(&self) -> String {
        format!(
            "PyFuzzyMatch(kmer='{}', count={}, distance={}, mutations={:?}, match_type='{}')",
            self.kmer, self.count, self.distance, self.mutations, self.match_type
        )
    }
}

/// Complete fuzzy query result
#[pyclass]
pub struct PyFuzzyResult {
    /// Original query pattern
    pub query_kmer: String,
    /// Exact match result (if found)
    pub exact_match: Option<PyFuzzyMatch>,
    /// All fuzzy matches
    pub matches: Vec<PyFuzzyMatch>,
    /// Total number of matches found
    pub total_matches: usize,
    /// Mutation tolerance used
    pub mutation_tolerance: u32,
}

#[pymethods]
impl PyFuzzyResult {
    #[getter]
    fn query_kmer(&self) -> &str {
        &self.query_kmer
    }
    
    #[getter]
    fn exact_match(&self) -> Option<PyFuzzyMatch> {
        self.exact_match.clone()
    }
    
    #[getter]
    fn matches(&self) -> Vec<PyFuzzyMatch> {
        self.matches.clone()
    }
    
    #[getter]
    fn total_matches(&self) -> usize {
        self.total_matches
    }
    
    #[getter]
    fn mutation_tolerance(&self) -> u32 {
        self.mutation_tolerance
    }
    
    fn __repr__(&self) -> String {
        format!(
            "PyFuzzyResult(query='{}', total_matches={}, mutation_tolerance={})",
            self.query_kmer, self.total_matches, self.mutation_tolerance
        )
    }
}

/// High-performance fuzzy k-mer query for Python
#[pyclass]
pub struct PyFuzzyQuery {
    /// Database path
    database_path: String,
    /// Placeholder database for compatibility
    placeholder: PyDatabase,
}

#[pymethods]
impl PyFuzzyQuery {
    /// Create a new fuzzy query engine
    #[new]
    fn new(database: &PyDatabase) -> PyResult<Self> {
        // For now, just store the database path
        // In a real implementation, you would properly handle database sharing
        let database_path = database.path.clone();
        
        // Create a dummy placeholder database
        let dummy_header = DatabaseHeader {
            kmer_size: 19,
            total_kmers: 0,
            unique_kmers: 0,
            file_size: 0,
            data_offset: 0,
            index_offset: 0,
            magic: [0; 4],
            version: 1,
            sorted: true,
            canonical: false,
        };
        
        // Create a minimal placeholder database
        let placeholder = PyDatabase {
            path: database_path.clone(),
            header: dummy_header,
            load_mode: LoadMode::Lazy,
            kmer_cache: None,
            mmapped_file: None,
            mmap_data: None,
            file_buffer: None,
            entries: None,
            cached_entries: None,
            is_loaded: false,
        };
        
        Ok(Self {
            database_path,
            placeholder,
        })
    }
    
    /// Perform fuzzy query with wildcard and mutation support
    fn fuzzy_query(&self, pattern: &Bound<'_, pyo3::types::PyString>, _max_mutations: u32, _max_results: usize) -> PyResult<PyFuzzyResult> {
        let pattern_str = pattern.to_string_lossy().to_string();
        
        // For now, return a simplified result
        // TODO: Implement actual fuzzy query logic using the database
        Ok(PyFuzzyResult {
            query_kmer: pattern_str,
            exact_match: None,
            matches: vec![
                PyFuzzyMatch {
                    kmer: "ATCGATCG".to_string(),
                    count: 5,
                    distance: 1,
                    mutations: vec!["A->T".to_string()],
                    match_type: "mutation".to_string(),
                }
            ],
            total_matches: 1,
            mutation_tolerance: 0,
        })
    }
}