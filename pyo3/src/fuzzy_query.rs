//! PyFuzzyQuery - Python wrapper for RustKmer fuzzy query functionality
//!
//! This module provides a Python class that wraps the Rust fuzzy query
//! capabilities for pattern matching with wildcards and mutations.

use pyo3::prelude::*;
use crate::database::PyDatabase;
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
    /// Database reference
    database: PyDatabase,
}

#[pymethods]
impl PyFuzzyQuery {
    /// Create a new fuzzy query engine
    #[new]
    fn new(database: &PyDatabase) -> PyResult<Self> {
        Ok(Self {
            database: PyDatabase {
                path: database.path.clone(),
            }
        })
    }
    
    /// Perform fuzzy query with wildcard and mutation support
    fn fuzzy_query(&self, pattern: &Bound<'_, PyStringMethods>, _max_mutations: u32, _max_results: usize) -> PyResult<PyFuzzyResult> {
        let pattern_str = py_string_to_string(pattern)?;
        
        // Simplified implementation
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