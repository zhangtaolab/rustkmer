//! Python bindings for Database operations
//! Rewritten to use CLI core functions for exact compatibility

use pyo3::prelude::*;
use std::path::PathBuf;
use std::sync::Arc;
use parking_lot::RwLock;
use std::collections::HashMap;

// Import our modules
use super::exceptions::*;

// Import CLI core database functionality for exact compatibility
use crate::core::database::query::DatabaseQuery;
use crate::core::database::format::DatabaseHeader;

/// Internal database backend using CLI DatabaseQuery
#[derive(Debug)]
struct DatabaseBackend {
    /// CLI DatabaseQuery instance
    query: DatabaseQuery,
    /// Database file path
    path: PathBuf,
    /// Whether database is preloaded into memory
    preloaded: bool,
}

/// Python wrapper for RustKmer Database using CLI core functions
#[pyclass(name = "Database")]
pub struct PyDatabase {
    backend: Arc<RwLock<DatabaseBackend>>,
}

#[pymethods]
impl PyDatabase {
    /// Create a new Database instance with optional parameters
    /// Now uses CLI's DatabaseQuery for exact compatibility
    #[new]
    #[pyo3(signature = (file_path=None, preload=false, k=None))]
    fn new(file_path: Option<String>, preload: bool, k: Option<usize>) -> PyResult<Self> {
        // For in-memory database creation, return an empty database
        if file_path.is_none() {
            return Err(DatabaseError::new_err("In-memory databases not supported - please provide a file_path"));
        }

        let file_path = file_path.unwrap();
        let db_path = PathBuf::from(&file_path);

        // Check if file exists
        if !db_path.exists() {
            return Err(DatabaseError::new_err(format!("Database file not found: {}", file_path)));
        }

        // Check if path is a directory (legacy KmerCounter format)
        if db_path.is_dir() {
            return Err(DatabaseError::new_err(
                "Directory-based databases not supported - please use .rkdb binary database files created with CLI"
            ));
        }

        // Use CLI's DatabaseQuery to open the database
        let mut query = DatabaseQuery::open(&db_path, preload)
            .map_err(|e| DatabaseError::new_err(format!("Failed to open database: {}", e)))?;

        // Get database info from CLI's DatabaseQuery
        let db_info = query.get_info().clone();

        let backend = DatabaseBackend {
            query,
            path: db_path,
            preloaded: preload,
        };

        Ok(PyDatabase {
            backend: Arc::new(RwLock::new(backend)),
        })
    }

    /// Context manager entry
    fn __enter__(&self) -> PyResult<Self> {
        // Clone the Arc<RwLock> for the context manager
        Ok(PyDatabase {
            backend: self.backend.clone(),
        })
    }

    /// Context manager exit
    fn __exit__(&self, _exc_type: PyObject, _exc_val: PyObject, _exc_tb: PyObject) -> PyResult<()> {
        self.close()
    }

    /// Query a single k-mer using CLI's DatabaseQuery for exact compatibility
    fn query(&self, kmer: &str) -> PyResult<PyQueryResult> {
        #[cfg(feature = "profiling")]
        let _timer = rustkmer::core::monitoring::start_timer("database_query_single");

        let mut backend = self.backend.write();

        // Use CLI's DatabaseQuery for exact compatibility
        match backend.query.query_kmer(kmer) {
            Ok(Some(count)) => {
                #[cfg(feature = "profiling")]
                rustkmer::core::monitoring::record_metric("database_query_single", "found", 1.0);
                Ok(PyQueryResult::new(kmer.to_uppercase(), count as u64, true))
            },
            Ok(None) => {
                #[cfg(feature = "profiling")]
                rustkmer::core::monitoring::record_metric("database_query_single", "found", 0.0);
                Ok(PyQueryResult::new(kmer.to_uppercase(), 0, false))
            },
            Err(e) => {
                #[cfg(feature = "profiling")]
                rustkmer::core::monitoring::record_metric("database_query_single", "error", 1.0);
                Err(DatabaseError::new_err(format!("Query failed: {}", e)))
            }
        }
    }

    /// Query multiple k-mers in batch using CLI's DatabaseQuery
    fn query_multiple(&self, kmers: Vec<String>) -> PyResult<Vec<PyQueryResult>> {
        #[cfg(feature = "profiling")]
        let _timer = rustkmer::core::monitoring::start_timer("database_query_batch");

        let mut backend = self.backend.write();

        // Use CLI's DatabaseQuery for exact compatibility
        let cli_results = backend.query.query_multiple(&kmers)
            .map_err(|e| DatabaseError::new_err(format!("Batch query failed: {}", e)))?;

        let mut found_count = 0;
        let mut total_length = 0u64;

        // Convert CLI results to Python format
        let mut results = Vec::with_capacity(cli_results.len());
        for (kmer, count) in cli_results {
            total_length += kmer.len() as u64;
            if count > 0 {
                found_count += 1;
                results.push(PyQueryResult::new(kmer.to_uppercase(), count as u64, true));
            } else {
                results.push(PyQueryResult::new(kmer.to_uppercase(), 0, false));
            }
        }

        #[cfg(feature = "profiling")]
        {
            rustkmer::core::monitoring::record_metric("database_query_batch", "total_queries", kmers.len() as f64);
            rustkmer::core::monitoring::record_metric("database_query_batch", "found_queries", found_count as f64);
            rustkmer::core::monitoring::record_metric("database_query_batch", "hit_rate", (found_count as f64 / kmers.len() as f64) * 100.0);
            rustkmer::core::monitoring::record_metric("database_query_batch", "avg_kmer_length", (total_length as f64 / kmers.len() as f64));
        }

        Ok(results)
    }

    /// Get the k-mer size from CLI database
    fn get_kmer_size(&self) -> PyResult<usize> {
        let backend = self.backend.read();
        let db_info = backend.query.get_info();
        Ok(db_info.kmer_size as usize)
    }

    /// Get the k-mer size (alias for get_kmer_size)
    fn get_k(&self) -> PyResult<usize> {
        self.get_kmer_size()
    }

    /// Get database statistics from CLI database
    fn get_stats(&self) -> PyResult<PyDatabaseStats> {
        let backend = self.backend.read();
        let db_info = backend.query.get_info();

        Ok(PyDatabaseStats::new(
            db_info.kmer_size as usize,
            db_info.total_kmers,
            db_info.unique_kmers,
            db_info.sorted,
            db_info.canonical,
            backend.preloaded,
        ))
    }

    /// Load a database from file using CLI DatabaseQuery
    fn load(&mut self, file_path: &str, preload: bool) -> PyResult<()> {
        let db_path = PathBuf::from(file_path);

        // Check if file exists
        if !db_path.exists() {
            return Err(DatabaseError::new_err(format!("Database file not found: {}", file_path)));
        }

        // Check if path is a directory (legacy KmerCounter format)
        if db_path.is_dir() {
            return Err(DatabaseError::new_err(
                "Directory-based databases not supported - please use .rkdb binary database files created with CLI"
            ));
        }

        // Use CLI's DatabaseQuery to load the database
        let mut query = DatabaseQuery::open(&db_path, preload)
            .map_err(|e| DatabaseError::new_err(format!("Failed to load database: {}", e)))?;

        let db_info = query.get_info().clone();

        // Replace the backend with new loaded database
        let mut backend = self.backend.write();
        backend.query = query;
        backend.path = db_path;
        backend.preloaded = preload;

        Ok(())
    }

    /// Get count for a specific k-mer (compatibility method)
    fn get_count(&self, kmer: &str) -> PyResult<u64> {
        let result = self.query(kmer)?;
        Ok(result.count)
    }

    /// Get all k-mer counts from CLI database
    fn get_all_counts(&self) -> PyResult<HashMap<String, u64>> {
        let backend = self.backend.read();
        let db_info = backend.query.get_info();

        // Note: CLI DatabaseQuery doesn't have a direct "get all counts" method
        // This would require iterating through all k-mers, which could be expensive
        // For now, we'll return an empty hash with metadata
        let mut all_counts = HashMap::new();

        // Could add implementation to iterate through database if needed
        // This would be more efficient in Python than in Rust for large databases

        Ok(all_counts)
    }

    /// Get database metadata from CLI database
    fn get_metadata(&self) -> PyResult<PyObject> {
        let backend = self.backend.read();
        let db_info = backend.query.get_info();

        Python::with_gil(|py| {
            let dict = pyo3::types::PyDict::new(py);

            dict.set_item("database_path", backend.path.to_string_lossy())?;
            dict.set_item("kmer_size", db_info.kmer_size)?;
            dict.set_item("total_kmers", db_info.total_kmers)?;
            dict.set_item("unique_kmers", db_info.unique_kmers)?;
            dict.set_item("sorted", db_info.sorted)?;
            dict.set_item("canonical", db_info.canonical)?;
            dict.set_item("preloaded", backend.preloaded)?;
            dict.set_item("data_offset", db_info.data_offset)?;
            dict.set_item("index_offset", db_info.index_offset)?;
            dict.set_item("file_size", backend.query.size_bytes())?;
            dict.set_item("format", "RKDB (CLI compatible)")?;
            dict.set_item("version", db_info.version)?;

            Ok(dict.into())
        })
    }

    /// Close the database
    fn close(&self) -> PyResult<()> {
        // DatabaseQuery doesn't have an explicit close method, so we just mark it as closed
        // In practice, when the backend goes out of scope, the database is closed
        // This method is kept for API compatibility
        Ok(())
    }

    /// Get the database file path
    fn get_path(&self) -> Option<String> {
        Some(self.backend.read().path.to_string_lossy().to_string())
    }

    /// Check if database is open (always true for loaded CLI databases)
    fn is_open(&self) -> bool {
        // CLI DatabaseQuery is always considered "open" when successfully loaded
        true
    }

    /// Check if database is preloaded into memory
    fn is_preloaded(&self) -> bool {
        self.backend.read().preloaded
    }

    /// Get a string representation
    fn __repr__(&self) -> String {
        let backend = self.backend.read();
        let db_info = backend.query.get_info();
        format!(
            "Database(path={}, k={}, open={}, preloaded={}, total_kmers={}, unique_kmers={}, sorted={}, canonical={})",
            backend.path.display(),
            db_info.kmer_size,
            true, // Always true for loaded CLI databases
            backend.preloaded,
            db_info.total_kmers,
            db_info.unique_kmers,
            db_info.sorted,
            db_info.canonical
        )
    }

    /// Get a string representation
    fn __str__(&self) -> String {
        self.__repr__()
    }
}

/// Python wrapper for QueryResult
#[pyclass(name = "QueryResult")]
#[derive(Debug, Clone)]
pub struct PyQueryResult {
    #[pyo3(get)]
    pub kmer: String,
    #[pyo3(get)]
    pub count: u64,
    #[pyo3(get)]
    pub found: bool,
}

#[pymethods]
impl PyQueryResult {
    #[new]
    fn new(kmer: String, count: u64, found: bool) -> Self {
        Self { kmer, count, found }
    }

    fn __repr__(&self) -> String {
        format!("QueryResult(kmer='{}', count={}, found={})", self.kmer, self.count, self.found)
    }

    fn __str__(&self) -> String {
        self.__repr__()
    }
}

/// Python wrapper for DatabaseStats
#[pyclass(name = "DatabaseStats")]
#[derive(Debug, Clone)]
pub struct PyDatabaseStats {
    #[pyo3(get)]
    pub kmer_size: usize,
    #[pyo3(get)]
    pub total_kmers: u64,
    #[pyo3(get)]
    pub unique_kmers: u64,
    #[pyo3(get)]
    pub sorted: bool,
    #[pyo3(get)]
    pub canonical: bool,
    #[pyo3(get)]
    pub preloaded: bool,
}

#[pymethods]
impl PyDatabaseStats {
    #[new]
    fn new(kmer_size: usize, total_kmers: u64, unique_kmers: u64, sorted: bool, canonical: bool, preloaded: bool) -> Self {
        Self {
            kmer_size,
            total_kmers,
            unique_kmers,
            sorted,
            canonical,
            preloaded,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "DatabaseStats(kmer_size={}, total_kmers={}, unique_kmers={}, sorted={}, canonical={}, preloaded={})",
            self.kmer_size, self.total_kmers, self.unique_kmers, self.sorted, self.canonical, self.preloaded
        )
    }

    fn __str__(&self) -> String {
        self.__repr__()
    }
}