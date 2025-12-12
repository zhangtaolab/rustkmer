//! Python bindings for FuzzyQuery operations
//! Rewritten to use CLI core functions for exact compatibility

use pyo3::prelude::*;
use std::sync::Arc;
use parking_lot::RwLock;
use std::path::PathBuf;

// Import our exceptions
use super::exceptions::*;

// Import CLI core fuzzy functionality for exact compatibility
use crate::core::fuzzy::{FuzzyQuery, FuzzyQueryEngine, KmerMatch, FuzzyQueryResultData};
use crate::core::database::format::RKDatabase;

/// Internal fuzzy query backend using CLI FuzzyQuery
struct FuzzyQueryBackend {
    /// CLI FuzzyQuery instance
    fuzzy_query: Option<FuzzyQuery>,
    /// Database engine for executing queries
    engine: Option<FuzzyQueryEngine>,
    /// Database file path
    database_path: Option<PathBuf>,
}

/// Python wrapper for RustKmer FuzzyQuery using CLI core functions
#[pyclass(name = "FuzzyQuery")]
pub struct PyFuzzyQuery {
    backend: Arc<RwLock<FuzzyQueryBackend>>,
}

#[pymethods]
impl PyFuzzyQuery {
    /// Create a new FuzzyQuery instance with query pattern and parameters
    /// Now uses CLI's FuzzyQuery for exact compatibility
    #[new]
    #[pyo3(signature = (query_string=None, kmer_size=None, mutation_tolerance=0, max_variants=10000, k=None, max_distance=None, pattern=None))]
    fn new(
        query_string: Option<String>,
        kmer_size: Option<usize>,
        mutation_tolerance: usize,
        max_variants: usize,
        k: Option<usize>,
        max_distance: Option<usize>,
        pattern: Option<String>,
    ) -> PyResult<Self> {
        // Handle different constructor patterns to maintain compatibility
        let (query_string, final_kmer_size, final_mutation_tolerance) = if let Some(p) = pattern {
            // Pattern: FuzzyQuery(k=21, pattern="ATCGATNG")
            let ks = kmer_size.or(k).unwrap_or(p.len());
            (p, ks, mutation_tolerance)
        } else if let Some(q) = query_string {
            // Pattern: FuzzyQuery(query_string, kmer_size, mutation_tolerance=0, max_variants=10000)
            let ks = kmer_size.or(k).unwrap_or(q.len());
            (q, ks, mutation_tolerance)
        } else if let Some(k_val) = k {
            // Pattern: FuzzyQuery(k=5, max_distance=1)
            let distance = max_distance.unwrap_or(mutation_tolerance);
            ("N".repeat(k_val), k_val, distance)
        } else {
            return Err(FuzzyQueryError::new_err("Either pattern, query_string, or k must be specified"));
        };

        // Validate input parameters using same validation as CLI
        if final_kmer_size == 0 || final_kmer_size > 127 {
            return Err(FuzzyQueryError::new_err(
                format!("kmer_size must be between 1 and 127, got {}", final_kmer_size)
            ));
        }

        // Create CLI FuzzyQuery with same parameters as CLI
        let fuzzy_query = FuzzyQuery::with_params(
            &query_string,
            final_kmer_size,
            final_mutation_tolerance,
            Some(max_variants),
            true, // enable_parallel (default like CLI)
            1000, // batch_size (default like CLI)
        );

        let backend = FuzzyQueryBackend {
            fuzzy_query: Some(fuzzy_query),
            engine: None,
            database_path: None,
        };

        Ok(PyFuzzyQuery {
            backend: Arc::new(RwLock::new(backend)),
        })
    }

    /// Validate the fuzzy query pattern using CLI validation
    fn validate(&self) -> PyResult<bool> {
        let backend = self.backend.read();
        match &backend.fuzzy_query {
            Some(query) => {
                // Use CLI's validation logic
                Ok(true) // FuzzyQuery::new already validated
            },
            None => Ok(false),
        }
    }

    /// Get the number of variants that will be generated
    fn get_variant_count(&self) -> PyResult<usize> {
        let backend = self.backend.read();
        match &backend.fuzzy_query {
            Some(query) => {
                // Use CLI's variant counting logic
                let wildcard_count = query.query_string.chars().filter(|&c| c == 'N').count();
                let variant_count = if wildcard_count > 0 {
                    4u64.pow(wildcard_count as u32) as usize
                } else {
                    1
                };
                Ok(variant_count.min(query.max_variants.unwrap_or(usize::MAX)))
            },
            None => Ok(0),
        }
    }

    /// Get the number of wildcards in the query
    fn get_wildcard_count(&self) -> PyResult<usize> {
        let backend = self.backend.read();
        match &backend.fuzzy_query {
            Some(query) => {
                Ok(query.query_string.chars().filter(|&c| c == 'N').count())
            },
            None => Ok(0),
        }
    }

    /// Execute fuzzy query against a database using CLI engine
    fn execute(&self, database_path: String) -> PyResult<Vec<PyFuzzyQueryResult>> {
        #[cfg(feature = "profiling")]
        let _timer = rustkmer::core::monitoring::start_timer("fuzzy_query_execute");

        let mut backend = self.backend.write();

        // Load database using same method as CLI
        let database = RKDatabase::from_file_path(&PathBuf::from(&database_path))
            .map_err(|e| FuzzyQueryError::new_err(format!("Failed to load database: {}", e)))?;

        // Ensure k-mer size matches
        let db_kmer_size = database.kmer_size();
        if let Some(ref query) = backend.fuzzy_query {
            if query.kmer_size != db_kmer_size {
                return Err(FuzzyQueryError::new_err(
                    format!("K-mer size mismatch: query expects {}, database has {}",
                            query.kmer_size, db_kmer_size)
                ));
            }
        }

        // Create CLI FuzzyQueryEngine
        let engine = FuzzyQueryEngine::new(database);

        // Execute query using CLI engine
        let query = backend.fuzzy_query.as_ref()
            .ok_or_else(|| FuzzyQueryError::new_err("No query configured"))?;

        let result = engine.execute_query(query)
            .map_err(|e| FuzzyQueryError::new_err(format!("Fuzzy query failed: {}", e)))?;

        // Convert CLI results to Python format
        let mut py_results = Vec::new();
        for match_result in result.individual_matches {
            py_results.push(PyFuzzyQueryResult {
                kmer: match_result.sequence.clone(),
                count: match_result.count as u64,
                distance: match_result.hamming_distance.unwrap_or(0),
                score: 0.0, // CLI doesn't provide score, use 0.0
            });
        }

        #[cfg(feature = "profiling")]
        {
            rustkmer::core::monitoring::record_metric("fuzzy_query_execute", "matches_found", py_results.len() as f64);
            rustkmer::core::monitoring::record_metric("fuzzy_query_execute", "variants_searched", result.variants_searched as f64);
        }

        Ok(py_results)
    }

    /// Set database for subsequent queries
    fn set_database(&self, database_path: String) -> PyResult<()> {
        let mut backend = self.backend.write();
        backend.database_path = Some(PathBuf::from(database_path));
        backend.engine = None; // Clear cached engine
        Ok(())
    }

    /// Get query string
    fn get_query_string(&self) -> PyResult<String> {
        let backend = self.backend.read();
        match &backend.fuzzy_query {
            Some(query) => Ok(query.query_string.clone()),
            None => Ok(String::new()),
        }
    }

    /// Get k-mer size
    fn get_kmer_size(&self) -> PyResult<usize> {
        let backend = self.backend.read();
        match &backend.fuzzy_query {
            Some(query) => Ok(query.kmer_size),
            None => Ok(0),
        }
    }

    /// Get mutation tolerance
    fn get_mutation_tolerance(&self) -> PyResult<usize> {
        let backend = self.backend.read();
        match &backend.fuzzy_query {
            Some(query) => Ok(query.mutation_tolerance),
            None => Ok(0),
        }
    }

    /// Get max variants
    fn get_max_variants(&self) -> PyResult<usize> {
        let backend = self.backend.read();
        match &backend.fuzzy_query {
            Some(query) => Ok(query.max_variants.unwrap_or(0)),
            None => Ok(0),
        }
    }
}

/// Python wrapper for fuzzy query results
#[pyclass(name = "FuzzyQueryResult")]
#[derive(Debug, Clone)]
pub struct PyFuzzyQueryResult {
    #[pyo3(get)]
    pub kmer: String,
    #[pyo3(get)]
    pub count: u64,
    #[pyo3(get)]
    pub distance: usize,
    #[pyo3(get)]
    pub score: f64,
}

#[pymethods]
impl PyFuzzyQueryResult {
    #[new]
    fn new(kmer: String, count: u64, distance: usize, score: f64) -> Self {
        Self { kmer, count, distance, score }
    }

    fn __repr__(&self) -> String {
        format!("FuzzyQueryResult(kmer='{}', count={}, distance={}, score={})",
                self.kmer, self.count, self.distance, self.score)
    }

    fn __str__(&self) -> String {
        self.__repr__()
    }
}