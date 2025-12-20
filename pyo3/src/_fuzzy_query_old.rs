//! PyFuzzyQuery - Python wrapper for RustKmer fuzzy query functionality
//!
//! This module provides a Python class that wraps the Rust fuzzy query
//! capabilities for pattern matching with wildcards and mutations.

use pyo3::prelude::*;
use crate::database::{PyDatabase, LoadMode};
use rustkmer::database::format::{DatabaseHeader, RKDatabase};
use rustkmer::fuzzy::{FuzzyQuery, FuzzyQueryEngine, FuzzyQueryResultData};
use rustkmer::fuzzy::query::PositionMutationConfig;
use crate::utils::py_string_to_string;
use std::path::Path;

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
    /// The actual Rust database for fuzzy queries
    database: Option<RKDatabase>,
    /// K-mer size from database
    kmer_size: Option<usize>,
    /// Position mutation configuration (optional)
    position_mutations: Option<PositionMutationConfig>,
}

#[pymethods]
impl PyFuzzyQuery {
    /// Create a new fuzzy query engine
    #[new]
    fn new(database: &PyDatabase) -> PyResult<Self> {
        let database_path = database.path.clone();
        
        // Load the actual Rust database for fuzzy queries
        let database = match RKDatabase::from_file_path(Path::new(&database_path)) {
            Ok(db) => Some(db),
            Err(e) => {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Failed to load database for fuzzy queries: {}", e)
                ));
            }
        };
        
        // Get k-mer size from the loaded database
        let kmer_size = database.as_ref().map(|db| db.kmer_size());
        
        Ok(Self {
            database_path,
            database,
            kmer_size,
            position_mutations: None,
        })
    }
    
    /// Configure position-specific mutations
    #[pyo3(signature = (position_config=None))]
    fn set_position_mutations(&mut self, position_config: Option<&str>) -> PyResult<()> {
        self.position_mutations = if let Some(config_str) = position_config {
            match PositionMutationConfig::parse(config_str) {
                Ok(config) => Some(config),
                Err(e) => {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        format!("Invalid position mutation configuration: {}", e)
                    ));
                }
            }
        } else {
            None
        };
        Ok(())
    }
    
    /// Perform fuzzy query with wildcard and mutation support
    #[pyo3(signature = (pattern, max_mutations, max_results=None))]
    fn fuzzy_query(
        &mut self,
        pattern: &Bound<'_, pyo3::types::PyString>,
        max_mutations: u32,
        max_results: Option<usize>
    ) -> PyResult<PyFuzzyResult> {
        let pattern_str = pattern.to_string_lossy().to_string();
        
        // Take ownership of database for the query
        let database = match self.database.take() {
            Some(db) => db,
            None => {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Database not available"
                ));
            }
        };
            
        let kmer_size = self.kmer_size
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "K-mer size not available"
            ))?;
        
        // Create fuzzy query configuration
        let query = if let Some(ref position_config) = self.position_mutations {
            FuzzyQuery::with_position_mutations(
                &pattern_str,
                kmer_size,
                max_mutations as usize,
                max_results,
                false, // Sequential processing
                1000, // Default batch size
                Some(position_config.clone()),
            )
        } else {
            FuzzyQuery::with_params(
                &pattern_str,
                kmer_size,
                max_mutations as usize,
                max_results,
                false, // Sequential processing  
                1000, // Default batch size
            )
        };
        
        // Create query engine and execute
        let engine = FuzzyQueryEngine::new(database);
        let result = engine.execute_query(&query)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Fuzzy query failed: {}", e)
            ))?;
        
        // Convert to Python result
        convert_fuzzy_result(result, &pattern_str, max_mutations)
    }
    
/// Convert Rust fuzzy query result to Python result
fn convert_fuzzy_result(
    result: FuzzyQueryResultData,
    query_pattern: &str,
    mutation_tolerance: u32
) -> PyResult<PyFuzzyResult> {
    let mut matches = Vec::new();
    let mut exact_match = None;
    
    for kmer_match in result.individual_matches {
        let match_type = match kmer_match.match_type {
            rustkmer::fuzzy::query::MatchType::Exact => "exact".to_string(),
            rustkmer::fuzzy::query::MatchType::WildcardExpansion { .. } => "wildcard".to_string(),
            rustkmer::fuzzy::query::MatchType::MutationTolerance { .. } => "mutation".to_string(),
            rustkmer::fuzzy::query::MatchType::LengthNormalization => "length_norm".to_string(),
        };
        
        let distance = kmer_match.hamming_distance.unwrap_or(0) as u32;
        
        let py_match = PyFuzzyMatch {
            kmer: kmer_match.sequence,
            count: kmer_match.count as u32,
            distance,
            mutations: vec![], // TODO: Extract mutation information
            match_type,
        };
        
        if distance == 0 {
            exact_match = Some(py_match.clone());
        }
        matches.push(py_match);
    }
    
    Ok(PyFuzzyResult {
        query_kmer: query_pattern.to_string(),
        exact_match,
        matches: matches.clone(),
        total_matches: matches.len(),
        mutation_tolerance,
    })
}
}