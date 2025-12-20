//! PyFuzzyQuery - Python wrapper for RustKmer fuzzy query functionality
//!
//! This module provides a Python class that wraps the Rust fuzzy query
//! capabilities for pattern matching with wildcards and mutations.

use pyo3::prelude::*;
use crate::database::PyDatabase;
use rustkmer::database::format::RKDatabase;
use rustkmer::fuzzy::{FuzzyQuery, FuzzyQueryEngine, MatchType};
use rustkmer::fuzzy::query::PositionMutationConfig;
use std::path::Path;
use std::time::Instant;

/// Individual fuzzy match result
#[pyclass]
#[derive(Clone)]
pub struct PyFuzzyMatch {
    /// The matched k-mer sequence
    pub kmer: String,
    /// Count in database
    pub count: u64,
    /// Distance from query pattern (if applicable)
    pub distance: Option<usize>,
    /// Match type information
    pub match_type: String,
    /// Positions involved in mutations (if applicable)
    pub mutation_positions: Vec<usize>,
}

#[pymethods]
impl PyFuzzyMatch {
    #[getter]
    fn kmer(&self) -> &str {
        &self.kmer
    }
    
    #[getter]
    fn count(&self) -> u64 {
        self.count
    }
    
    #[getter]
    fn distance(&self) -> Option<usize> {
        self.distance
    }
    
    #[getter]
    fn mutation_positions(&self) -> Vec<usize> {
        self.mutation_positions.clone()
    }
    
    #[getter]
    fn match_type(&self) -> &str {
        &self.match_type
    }
    
    fn __repr__(&self) -> String {
        format!(
            "PyFuzzyMatch(kmer='{}', count={}, distance={:?}, mutation_positions={:?}, match_type='{}')",
            self.kmer, self.count, self.distance, self.mutation_positions, self.match_type
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
    /// Query execution time in milliseconds
    pub query_time_ms: u64,
    /// Whether position-specific mutations were used
    pub has_position_mutations: bool,
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
    
    #[getter]
    fn query_time_ms(&self) -> u64 {
        self.query_time_ms
    }
    
    #[getter]
    fn has_position_mutations(&self) -> bool {
        self.has_position_mutations
    }
    
    /// Get matches filtered by specific Hamming distance
    fn get_matches_by_distance(&self, distance: u32) -> Vec<PyFuzzyMatch> {
        self.matches
            .iter()
            .filter(|m| m.distance == Some(distance as usize))
            .cloned()
            .collect()
    }
    
    /// Get top matches by count (most frequent k-mers)
    fn get_top_matches(&self, limit: usize) -> Vec<PyFuzzyMatch> {
        let mut matches = self.matches.clone();
        matches.sort_by(|a, b| b.count.cmp(&a.count));
        matches.into_iter().take(limit).collect()
    }
    
    fn __repr__(&self) -> String {
        format!(
            "PyFuzzyResult(query='{}', total_matches={}, mutation_tolerance={}, query_time_ms={})",
            self.query_kmer, self.total_matches, self.mutation_tolerance, self.query_time_ms
        )
    }
}

/// High-performance fuzzy k-mer query for Python
#[pyclass]
pub struct PyFuzzyQuery {
    /// Database file path (stored separately for fuzzy query execution)
    database_path: String,
    /// K-mer size from database
    kmer_size: usize,
}

#[pymethods]
impl PyFuzzyQuery {
    /// Create a new fuzzy query engine
    #[new]
    fn new(database: &PyDatabase) -> PyResult<Self> {
        let database_path = database.path.clone();
        
        // Load the actual Rust database to get k-mer size
        let database = match RKDatabase::from_file_path(Path::new(&database_path)) {
            Ok(db) => db,
            Err(e) => {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Failed to load database for fuzzy queries: {}", e)
                ));
            }
        };
        
        // Get k-mer size from the loaded database
        let kmer_size = database.kmer_size();
        
        Ok(Self {
            database_path,
            kmer_size,
        })
    }
    /// Perform fuzzy query with wildcard and mutation support
    #[pyo3(signature = (pattern, max_mutations, max_results=None))]
    fn fuzzy_query(
        &self,
        pattern: &Bound<'_, pyo3::types::PyString>,
        max_mutations: u32,
        max_results: Option<usize>
    ) -> PyResult<PyFuzzyResult> {
        // For now, just call with empty position mutations
        self.fuzzy_query_with_position_mutations(pattern, max_mutations, "", max_results)
    }
    
    /// Perform fuzzy query with position-specific mutations
    #[pyo3(signature = (pattern, max_mutations, position_mutations, max_results=None))]
    fn fuzzy_query_with_position_mutations(
        &self,
        pattern: &Bound<'_, pyo3::types::PyString>,
        max_mutations: u32,
        position_mutations: &str,
        max_results: Option<usize>
    ) -> PyResult<PyFuzzyResult> {
        // Parse position mutations configuration if provided
        let parsed_config = if !position_mutations.is_empty() {
            Some(PositionMutationConfig::parse(position_mutations).map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Invalid position mutation configuration: {}", e)
                )
            })?)
        } else {
            None
        };

        let pattern_str = pattern.to_string_lossy().to_string();
        
        // Validate pattern length
        if pattern_str.len() != self.kmer_size {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Pattern length {} does not match database k-mer size {}", 
                        pattern_str.len(), self.kmer_size)
            ));
        }
        
        // Validate pattern characters
        if !pattern_str.chars().all(|c| matches!(c, 'A' | 'T' | 'C' | 'G' | 'N')) {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Pattern contains invalid characters (only A,T,C,G,N allowed)".to_string()
            ));
        }
        
        // Create fuzzy query configuration
        let query = if let Some(ref config) = parsed_config {
            FuzzyQuery::with_position_mutations(
                &pattern_str,
                self.kmer_size,
                max_mutations as usize,
                max_results,
                false, // Sequential processing
                1000, // Default batch size
                Some(config.clone()),
            )
        } else {
            FuzzyQuery::with_params(
                &pattern_str,
                self.kmer_size,
                max_mutations as usize,
                max_results,
                false, // Sequential processing  
                1000, // Default batch size
            )
        };
        let pattern_str = pattern.to_string_lossy().to_string();
        
        // Validate pattern length
        if pattern_str.len() != self.kmer_size {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Pattern length {} does not match database k-mer size {}", 
                        pattern_str.len(), self.kmer_size)
            ));
        }
        
        // Validate pattern characters
        if !pattern_str.chars().all(|c| matches!(c, 'A' | 'T' | 'C' | 'G' | 'N')) {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Pattern contains invalid characters (only A,T,C,G,N allowed)".to_string()
            ));
        }
        
        // Parse position mutations configuration if provided
        let position_config = if !position_mutations.is_empty() {
            Some(PositionMutationConfig::parse(position_mutations).map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Invalid position mutation configuration: {}", e)
                )
            })?)
        } else {
            None
        };

        // Create fuzzy query configuration
        let query = if let Some(ref config) = position_config {
            FuzzyQuery::with_position_mutations(
                &pattern_str,
                self.kmer_size,
                max_mutations as usize,
                max_results,
                false, // Sequential processing
                1000, // Default batch size
                Some(config.clone()),
            )
        } else {
            FuzzyQuery::with_params(
                &pattern_str,
                self.kmer_size,
                max_mutations as usize,
                max_results,
                false, // Sequential processing  
                1000, // Default batch size
            )
        };
        
        // Create fuzzy query engine and execute the query
        let start_time = Instant::now();
        
        // Load database for fuzzy query execution
        let database = RKDatabase::from_file_path(Path::new(&self.database_path))
            .map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to load database for fuzzy query: {}", e)
                )
            })?;
        
        let engine = FuzzyQueryEngine::new(database);
        
        // Execute the fuzzy query
        let result = engine.execute_query(&query)
            .map_err(|e| {
                PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Fuzzy query execution failed: {}", e)
                )
            })?;
        
        let query_time_ms = start_time.elapsed().as_millis() as u64;
        
        // Convert Rust results to Python results
        let py_matches: Vec<PyFuzzyMatch> = result.individual_matches
            .into_iter()
            .map(|kmer_match| {
                let match_type_str = match &kmer_match.match_type {
                    MatchType::Exact => "exact".to_string(),
                    MatchType::WildcardExpansion { wildcard_positions } => {
                        format!("wildcard_expansion[{:?}]", wildcard_positions)
                    }
                    MatchType::MutationTolerance { mutation_positions } => {
                        format!("mutation_tolerance[{:?}]", mutation_positions)
                    }
                    MatchType::LengthNormalization => "length_normalization".to_string(),
                };
                
                PyFuzzyMatch {
                    kmer: kmer_match.sequence,
                    count: kmer_match.count,
                    distance: kmer_match.hamming_distance,
                    match_type: match_type_str,
                    mutation_positions: match kmer_match.match_type {
                        MatchType::WildcardExpansion { wildcard_positions } => wildcard_positions,
                        MatchType::MutationTolerance { mutation_positions } => mutation_positions,
                        _ => vec![],
                    },
                }
            })
            .collect();
        
        // Find exact match if it exists
        let exact_match = py_matches.iter()
            .find(|m| m.match_type == "exact")
            .cloned();
        
        Ok(PyFuzzyResult {
            query_kmer: pattern_str,
            exact_match,
            matches: py_matches,
            total_matches: result.total_count as usize,
            mutation_tolerance: max_mutations,
            query_time_ms,
            has_position_mutations: !position_mutations.is_empty(),
        })
    }
    
    /// Get database k-mer size
    #[getter]
    fn kmer_size(&self) -> usize {
        self.kmer_size
    }
}