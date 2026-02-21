//! PyFuzzyQuery - Python wrapper for RustKmer fuzzy query functionality
//!
//! This module provides a Python class that wraps the Rust fuzzy query
//! capabilities for pattern matching with wildcards and mutations.

// Allow deprecated methods for backward compatibility
#![allow(deprecated)]

use crate::database::PyDatabase;
use pyo3::prelude::*;
use rustkmer::database::format::RKDatabase;
use rustkmer::fuzzy::query::PositionMutationConfig;
use rustkmer::fuzzy::{FuzzyQuery, FuzzyQueryEngine, MatchType};
use std::path::Path;
use std::time::Instant;

/// Individual fuzzy match result
#[pyclass]
#[derive(Clone, Debug)]
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

    // Formatter methods
    fn to_json(&self) -> PyResult<String> {
        // Build JSON for exact_match if present
        let exact_match_json = match &self.exact_match {
            Some(exact) => {
                let positions_json = format!("[{}]", 
                    exact.mutation_positions.iter()
                        .map(|p| p.to_string())
                        .collect::<Vec<_>>()
                        .join(", ")
                );
                format!(
                    r#"{{"kmer": "{}", "count": {}, "distance": {}, "match_type": "{}", "mutation_positions": {}}}"#,
                    exact.kmer,
                    exact.count,
                    exact.distance.map_or("null".to_string(), |d| d.to_string()),
                    exact.match_type,
                    positions_json
                )
            },
            None => "null".to_string(),
        };

        // Build JSON array for matches
        let matches_json: Vec<String> = self.matches.iter().map(|m| {
            let positions_json = format!("[{}]", 
                m.mutation_positions.iter()
                    .map(|p| p.to_string())
                    .collect::<Vec<_>>()
                    .join(", ")
            );
            format!(
                r#"{{"kmer": "{}", "count": {}, "distance": {}, "match_type": "{}", "mutation_positions": {}}}"#,
                m.kmer,
                m.count,
                m.distance.map_or("null".to_string(), |d| d.to_string()),
                m.match_type,
                positions_json
            )
        }).collect();

        Ok(format!(
            r#"{{"query_kmer": "{}", "exact_match": {}, "matches": [{}], "total_matches": {}, "mutation_tolerance": {}, "query_time_ms": {}, "has_position_mutations": {}}}"#,
            self.query_kmer,
            exact_match_json,
            matches_json.join(", "),
            self.total_matches,
            self.mutation_tolerance,
            self.query_time_ms,
            self.has_position_mutations
        ))
    }



    fn to_csv(&self) -> PyResult<String> {
        let mut csv = String::new();
        csv.push_str("kmer,count,distance,match_type,mutation_positions\n");

        if let Some(ref exact) = self.exact_match {
            csv.push_str(&format!(
                "{},{},{},{},\"{:?}\"\n",
                exact.kmer,
                exact.count,
                exact.distance.unwrap_or(0),
                exact.match_type,
                exact.mutation_positions
            ));
        }

        for match_item in &self.matches {
            if match_item.match_type == "exact" {
                if let Some(ref exact) = self.exact_match {
                    if match_item.kmer == exact.kmer {
                        continue;
                    }
                }
            }

            csv.push_str(&format!(
                "{},{},{},{},\"{:?}\"\n",
                match_item.kmer,
                match_item.count,
                match_item.distance.unwrap_or(0),
                match_item.match_type,
                match_item.mutation_positions
            ));
        }

        csv.push_str(&format!("# query_kmer={}\n", self.query_kmer));
        csv.push_str(&format!("# total_matches={}\n", self.total_matches));
        csv.push_str(&format!(
            "# mutation_tolerance={}\n",
            self.mutation_tolerance
        ));
        csv.push_str(&format!("# query_time_ms={}\n", self.query_time_ms));
        csv.push_str(&format!(
            "# has_position_mutations={}\n",
            self.has_position_mutations
        ));

        Ok(csv)
    }

    fn to_tsv(&self) -> PyResult<String> {
        let mut tsv = String::new();
        tsv.push_str("kmer\tcount\tdistance\tmatch_type\tmutation_positions\n");

        if let Some(ref exact) = self.exact_match {
            tsv.push_str(&format!(
                "{}\t{}\t{}\t{}\t{:?}\n",
                exact.kmer,
                exact.count,
                exact.distance.unwrap_or(0),
                exact.match_type,
                exact.mutation_positions
            ));
        }

        for match_item in &self.matches {
            if match_item.match_type == "exact" {
                if let Some(ref exact) = self.exact_match {
                    if match_item.kmer == exact.kmer {
                        continue;
                    }
                }
            }

            tsv.push_str(&format!(
                "{}\t{}\t{}\t{}\t{:?}\n",
                match_item.kmer,
                match_item.count,
                match_item.distance.unwrap_or(0),
                match_item.match_type,
                match_item.mutation_positions
            ));
        }

        tsv.push_str(&format!("# query_kmer={}\n", self.query_kmer));
        tsv.push_str(&format!("# total_matches={}\n", self.total_matches));
        tsv.push_str(&format!(
            "# mutation_tolerance={}\n",
            self.mutation_tolerance
        ));
        tsv.push_str(&format!("# query_time_ms={}\n", self.query_time_ms));
        tsv.push_str(&format!(
            "# has_position_mutations={}\n",
            self.has_position_mutations
        ));

        Ok(tsv)
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

#[allow(deprecated)]
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
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Failed to load database for fuzzy queries: {}",
                    e
                )));
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
    #[allow(deprecated)]
    #[deprecated(since = "2.0.0", note = "Use `query_fuzzy()` instead")]
    #[pyo3(signature = (pattern, max_mutations, max_results=None))]
    fn fuzzy_query(
        &self,
        pattern: &Bound<'_, pyo3::types::PyString>,
        max_mutations: u32,
        max_results: Option<usize>,
    ) -> PyResult<PyFuzzyResult> {
        self.fuzzy_query_with_position_mutations_impl(
            &pattern.to_string_lossy(),
            max_mutations,
            "",
            max_results,
        )
    }

    /// Internal implementation for fuzzy query with position-specific mutations
    fn fuzzy_query_with_position_mutations_impl(
        &self,
        pattern: &str,
        max_mutations: u32,
        position_mutations: &str,
        max_results: Option<usize>,
    ) -> PyResult<PyFuzzyResult> {
        // Parse position mutations configuration if provided
        let parsed_config = if !position_mutations.is_empty() {
            Some(
                PositionMutationConfig::parse(position_mutations).map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                        "Invalid position mutation configuration: {}",
                        e
                    ))
                })?,
            )
        } else {
            None
        };

        let pattern_str = pattern.to_uppercase();

        // Validate pattern length
        if pattern_str.len() != self.kmer_size {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Pattern length {} does not match database k-mer size {}",
                pattern_str.len(),
                self.kmer_size
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

        // Create fuzzy query configuration
        let query = if let Some(ref config) = parsed_config {
            FuzzyQuery::with_position_mutations(
                &pattern_str,
                self.kmer_size,
                max_mutations as usize,
                max_results,
                false, // Sequential processing
                1000,  // Default batch size
                Some(config.clone()),
            )
        } else {
            FuzzyQuery::with_params(
                &pattern_str,
                self.kmer_size,
                max_mutations as usize,
                max_results,
                false, // Sequential processing
                1000,  // Default batch size
            )
        };

        // Create fuzzy query engine and execute the query
        let start_time = Instant::now();

        // Load database for fuzzy query execution
        let database = RKDatabase::from_file_path(Path::new(&self.database_path)).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                "Failed to load database for fuzzy query: {}",
                e
            ))
        })?;

        let engine = FuzzyQueryEngine::new(database);

        // Execute the fuzzy query
        let result = engine.execute_query(&query).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                "Fuzzy query execution failed: {}",
                e
            ))
        })?;

        let query_time_ms = start_time.elapsed().as_millis() as u64;

        // Convert Rust results to Python results
        let py_matches: Vec<PyFuzzyMatch> = result
            .individual_matches
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
        let exact_match = py_matches.iter().find(|m| m.match_type == "exact").cloned();

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

    /// Perform fuzzy query with position-specific mutations
    #[allow(deprecated)]
    #[deprecated(since = "2.0.0", note = "Use `query_fuzzy_position()` instead")]
    #[pyo3(signature = (pattern, max_mutations, position_mutations, max_results=None))]
    fn fuzzy_query_with_position_mutations(
        &self,
        pattern: &Bound<'_, pyo3::types::PyString>,
        max_mutations: u32,
        position_mutations: &str,
        max_results: Option<usize>,
    ) -> PyResult<PyFuzzyResult> {
        self.fuzzy_query_with_position_mutations_impl(
            &pattern.to_string_lossy(),
            max_mutations,
            position_mutations,
            max_results,
        )
    }

    // ===== 统一API命名方法 =====

    /// 模糊查询 - 统一命名版本
    #[pyo3(signature = (pattern, max_mutations, max_results=None))]
    fn query_fuzzy(
        &self,
        pattern: &Bound<'_, pyo3::types::PyString>,
        max_mutations: u32,
        max_results: Option<usize>,
    ) -> PyResult<PyFuzzyResult> {
        self.fuzzy_query_with_position_mutations_impl(
            &pattern.to_string_lossy(),
            max_mutations,
            "",
            max_results,
        )
    }

    /// 位置特异性模糊查询 - 统一命名版本
    #[pyo3(signature = (pattern, max_mutations, position_mutations, max_results=None))]
    fn query_fuzzy_position(
        &self,
        pattern: &Bound<'_, pyo3::types::PyString>,
        max_mutations: u32,
        position_mutations: &str,
        max_results: Option<usize>,
    ) -> PyResult<PyFuzzyResult> {
        self.fuzzy_query_with_position_mutations_impl(
            &pattern.to_string_lossy(),
            max_mutations,
            position_mutations,
            max_results,
        )
    }

    /// Get database k-mer size
    #[getter]
    fn kmer_size(&self) -> usize {
        self.kmer_size
    }
}
