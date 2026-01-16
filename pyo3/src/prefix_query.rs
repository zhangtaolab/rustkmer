//! High-performance prefix query engine for Python
//!
//! This module provides a dedicated prefix query engine that can be used
//! independently for high-performance k-mer prefix queries.

// Allow deprecated methods for backward compatibility
#![allow(deprecated)]

use pyo3::prelude::*;
use rustkmer::database::format::RKDatabase;
use rustkmer::database::prefix_query_optimized::{
    extract_hybrid_by_pattern, extract_prefix_optimized, parse_hybrid_pattern,
};
use std::collections::HashMap;
use std::path::Path;

/// High-performance prefix query engine
#[pyclass]
pub struct PyPrefixQuery {
    /// Database path
    database_path: String,
    /// Loaded database
    rk_database: Option<RKDatabase>,
    /// K-mer size
    kmer_size: usize,
}

#[pymethods]
impl PyPrefixQuery {
    /// Create a new prefix query engine
    #[new]
    fn new(database_path: &Bound<'_, pyo3::types::PyString>) -> PyResult<Self> {
        let db_path = database_path.to_string();

        // Load the database
        let database = match RKDatabase::from_file_path(Path::new(&db_path)) {
            Ok(db) => db,
            Err(e) => {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Failed to load database: {}",
                    e
                )));
            }
        };

        let kmer_size = database.kmer_size();

        Ok(Self {
            database_path: db_path,
            rk_database: Some(database),
            kmer_size,
        })
    }

    /// Perform optimized prefix query
    #[pyo3(signature = (prefix))]
    fn query_prefix(
        &self,
        prefix: &Bound<'_, pyo3::types::PyString>,
    ) -> PyResult<HashMap<String, String>> {
        self.query_prefix_string(&prefix.to_string())
    }

    /// Perform optimized prefix query with string input
    fn query_prefix_string(&self, prefix: &str) -> PyResult<HashMap<String, String>> {
        if let Some(ref db) = self.rk_database {
            // Validate prefix
            if prefix.trim().is_empty() {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Prefix cannot be empty",
                ));
            }

            if !prefix
                .chars()
                .all(|c| matches!(c.to_ascii_uppercase(), 'A' | 'T' | 'C' | 'G'))
            {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    "Prefix contains invalid characters (only A, T, C, G allowed)",
                ));
            }

            let prefix_upper = prefix.to_uppercase();

            // Execute optimized query
            let result = match extract_prefix_optimized(db, &prefix_upper) {
                Ok(result) => result,
                Err(e) => {
                    return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!(
                        "Prefix query failed: {}",
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
                "Database not loaded",
            ))
        }
    }

    /// Perform hybrid pattern query
    #[pyo3(signature = (pattern))]
    fn query_hybrid(
        &self,
        pattern: &Bound<'_, pyo3::types::PyString>,
    ) -> PyResult<HashMap<String, String>> {
        let pattern_str = pattern.to_string();

        // Validate pattern
        if pattern_str.trim().is_empty() {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Pattern cannot be empty",
            ));
        }

        let pattern_upper = pattern_str.to_uppercase();

        if let Some(ref db) = self.rk_database {
            // Execute hybrid query
            let result = match extract_hybrid_by_pattern(db, &pattern_upper) {
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
                "Database not loaded",
            ))
        }
    }

    /// Parse hybrid pattern without executing query
    #[pyo3(signature = (pattern))]
    fn parse_pattern(
        &self,
        pattern: &Bound<'_, pyo3::types::PyString>,
    ) -> PyResult<HashMap<String, String>> {
        let pattern_str = pattern.to_string();
        let pattern_upper = pattern_str.to_uppercase();

        let result = match parse_hybrid_pattern(&pattern_upper) {
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

    /// Get database information
    fn database_info(&self) -> HashMap<String, String> {
        let mut info = HashMap::new();
        info.insert("database_path".to_string(), self.database_path.clone());
        info.insert("kmer_size".to_string(), self.kmer_size.to_string());
        info.insert(
            "is_loaded".to_string(),
            self.rk_database.is_some().to_string(),
        );
        info
    }

    /// Check if database is loaded
    fn is_loaded(&self) -> bool {
        self.rk_database.is_some()
    }

    /// Get k-mer size
    fn kmer_size(&self) -> usize {
        self.kmer_size
    }

    fn __repr__(&self) -> String {
        format!(
            "PyPrefixQuery(database='{}', kmer_size={}, loaded={})",
            self.database_path,
            self.kmer_size,
            self.rk_database.is_some()
        )
    }
}

/// Query result with performance metrics
#[pyclass]
pub struct PyPrefixQueryMetrics {
    /// Query results
    pub results: HashMap<String, String>,
    /// Execution time in milliseconds
    pub execution_time_ms: u64,
    /// Memory block information
    pub start_index: usize,
    pub end_index: usize,
    pub block_size: usize,
    /// Total matches found
    pub total_matches: usize,
}

#[pymethods]
impl PyPrefixQueryMetrics {
    #[getter]
    fn results(&self) -> HashMap<String, String> {
        self.results.clone()
    }

    #[getter]
    fn execution_time_ms(&self) -> u64 {
        self.execution_time_ms
    }

    #[getter]
    fn total_matches(&self) -> usize {
        self.total_matches
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

    fn __repr__(&self) -> String {
        format!(
            "PyPrefixQueryMetrics(matches={}, time={}ms, block=[{},{})",
            self.total_matches, self.execution_time_ms, self.start_index, self.end_index
        )
    }
}

/// Extended prefix query with detailed metrics
#[pyclass]
pub struct PyExtendedPrefixQuery {
    /// Base query engine
    query_engine: PyPrefixQuery,
}

#[allow(deprecated)]
#[pymethods]
impl PyExtendedPrefixQuery {
    /// Create a new extended prefix query engine
    #[new]
    fn new(database_path: &Bound<'_, pyo3::types::PyString>) -> PyResult<Self> {
        let query_engine = PyPrefixQuery::new(database_path)?;
        Ok(Self { query_engine })
    }

    /// Query prefix with detailed metrics
    #[allow(deprecated)]
    #[deprecated(since = "2.0.0", note = "Use `query_prefix_metrics()` instead")]
    #[pyo3(signature = (prefix))]
    fn query_with_metrics(
        &self,
        prefix: &Bound<'_, pyo3::types::PyString>,
    ) -> PyResult<PyPrefixQueryMetrics> {
        use std::time::Instant;

        let start_time = Instant::now();

        // Perform query
        let results = self.query_engine.query_prefix(prefix)?;
        let execution_time = start_time.elapsed().as_millis() as u64;

        let start_index = 0;
        let end_index = results.len();
        let block_size = end_index - start_index;
        let total_matches = results.len();

        Ok(PyPrefixQueryMetrics {
            results,
            execution_time_ms: execution_time,
            start_index,
            end_index,
            block_size,
            total_matches,
        })
    }

    /// Query hybrid pattern with detailed metrics
    #[allow(deprecated)]
    #[deprecated(since = "2.0.0", note = "Use `query_hybrid_metrics()` instead")]
    #[pyo3(signature = (pattern))]
    fn query_hybrid_with_metrics(
        &self,
        pattern: &Bound<'_, pyo3::types::PyString>,
    ) -> PyResult<PyPrefixQueryMetrics> {
        use std::time::Instant;

        let start_time = Instant::now();

        // Perform query
        let results = self.query_engine.query_hybrid(pattern)?;
        let execution_time = start_time.elapsed().as_millis() as u64;

        let start_index = 0;
        let end_index = results.len();
        let block_size = end_index - start_index;
        let total_matches = results.len();

        Ok(PyPrefixQueryMetrics {
            results,
            execution_time_ms: execution_time,
            start_index,
            end_index,
            block_size,
            total_matches,
        })
    }

    /// Query prefix with metrics using string input
    #[allow(deprecated)]
    #[deprecated(since = "2.0.0", note = "Use `query_prefix_metrics_string()` instead")]
    #[pyo3(signature = (prefix))]
    fn query_with_metrics_string(&self, prefix: &str) -> PyResult<PyPrefixQueryMetrics> {
        use std::time::Instant;

        let start_time = Instant::now();

        // Perform query
        let results = self.query_engine.query_prefix_string(prefix)?;
        let execution_time = start_time.elapsed().as_millis() as u64;

        let start_index = 0;
        let end_index = results.len();
        let block_size = end_index - start_index;
        let total_matches = results.len();

        Ok(PyPrefixQueryMetrics {
            results,
            execution_time_ms: execution_time,
            start_index,
            end_index,
            block_size,
            total_matches,
        })
    }

    /// Batch query multiple prefixes
    #[allow(deprecated)]
    #[deprecated(since = "2.0.0", note = "Use `query_prefix_batch_metrics()` instead")]
    #[pyo3(signature = (prefixes))]
    fn batch_query(
        &self,
        prefixes: Vec<String>,
    ) -> PyResult<HashMap<String, PyPrefixQueryMetrics>> {
        let mut results = HashMap::new();

        for prefix in prefixes {
            let metrics = self.query_with_metrics_string(&prefix)?;
            results.insert(prefix, metrics);
        }

        Ok(results)
    }

    // ===== 统一API命名方法 =====

    /// 前缀查询带指标 - 统一命名版本
    #[pyo3(signature = (prefix))]
    fn query_prefix_metrics(
        &self,
        prefix: &Bound<'_, pyo3::types::PyString>,
    ) -> PyResult<PyPrefixQueryMetrics> {
        use std::time::Instant;

        let start_time = Instant::now();
        let prefix_str = prefix.to_string().to_uppercase();

        // Perform query - call base implementation directly
        let results = self.query_engine.query_prefix_string(&prefix_str)?;
        let execution_time = start_time.elapsed().as_millis() as u64;

        let start_index = 0;
        let end_index = results.len();
        let block_size = end_index - start_index;
        let total_matches = results.len();

        Ok(PyPrefixQueryMetrics {
            results,
            execution_time_ms: execution_time,
            start_index,
            end_index,
            block_size,
            total_matches,
        })
    }

    /// 混合模式查询带指标 - 统一命名版本
    #[pyo3(signature = (pattern))]
    fn query_hybrid_metrics(
        &self,
        pattern: &Bound<'_, pyo3::types::PyString>,
    ) -> PyResult<PyPrefixQueryMetrics> {
        use std::time::Instant;

        let start_time = Instant::now();

        // Perform query - call base implementation directly
        let results = self.query_engine.query_hybrid(pattern)?;
        let execution_time = start_time.elapsed().as_millis() as u64;

        let start_index = 0;
        let end_index = results.len();
        let block_size = end_index - start_index;
        let total_matches = results.len();

        Ok(PyPrefixQueryMetrics {
            results,
            execution_time_ms: execution_time,
            start_index,
            end_index,
            block_size,
            total_matches,
        })
    }

    /// 前缀查询带指标（字符串输入）- 统一命名版本
    #[pyo3(signature = (prefix))]
    fn query_prefix_metrics_string(&self, prefix: &str) -> PyResult<PyPrefixQueryMetrics> {
        use std::time::Instant;

        let start_time = Instant::now();

        // Perform query - call base implementation directly
        let results = self.query_engine.query_prefix_string(prefix)?;
        let execution_time = start_time.elapsed().as_millis() as u64;

        let start_index = 0;
        let end_index = results.len();
        let block_size = end_index - start_index;
        let total_matches = results.len();

        Ok(PyPrefixQueryMetrics {
            results,
            execution_time_ms: execution_time,
            start_index,
            end_index,
            block_size,
            total_matches,
        })
    }

    /// 批量前缀查询带指标 - 统一命名版本
    #[pyo3(signature = (prefixes))]
    fn query_prefix_batch_metrics(
        &self,
        prefixes: Vec<String>,
    ) -> PyResult<HashMap<String, PyPrefixQueryMetrics>> {
        let mut results = HashMap::new();

        for prefix in prefixes {
            let metrics = self.query_prefix_metrics_string(&prefix)?;
            results.insert(prefix, metrics);
        }

        Ok(results)
    }

    fn __repr__(&self) -> String {
        format!(
            "PyExtendedPrefixQuery(database='{}', kmer_size={})",
            self.query_engine.database_path, self.query_engine.kmer_size
        )
    }
}
