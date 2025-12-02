//! Python bindings for Database operations

use pyo3::prelude::*;
use std::path::PathBuf;
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;

// Import our modules
use super::exceptions::*;


// TODO: Import RustKmer database functionality when module structure is ready
// use crate::database::query::DatabaseQuery;
// use crate::database::format::DatabaseHeader;

/// Internal database backend for Python bindings
#[derive(Debug, Clone)]
struct DatabaseBackend {
    /// Database file path
    path: Option<PathBuf>,
    /// K-mer size (when known)
    kmer_size: Option<usize>,
    /// Total k-mers (when known)
    total_kmers: Option<u64>,
    /// Whether database is currently open
    is_open: bool,
    /// Whether database is preloaded into memory
    preloaded: bool,
    /// Whether database is canonical
    canonical: bool,
    /// Whether database is sorted
    sorted: bool,
    /// In-memory k-mer storage for testing
    memory_store: Option<HashMap<u64, u32>>,
}

/// Python wrapper for RustKmer Database
#[pyclass(name = "Database")]
pub struct PyDatabase {
    backend: Arc<RwLock<DatabaseBackend>>,
}

#[pymethods]
impl PyDatabase {
    /// Simple k-mer encoding for testing purposes
    /// TODO: Replace with real k-mer encoding when database module is integrated
    fn simple_encode_kmer(&self, kmer: &str) -> u64 {
        let mut encoded = 0u64;
        // Limit k-mer size to prevent overflow (max 32 bases for 64-bit encoding)
        let max_kmer_size = 32;
        let kmer_chars: Vec<char> = kmer.chars().take(max_kmer_size).collect();

        for (i, c) in kmer_chars.iter().enumerate() {
            let bits = match c.to_ascii_uppercase() {
                'A' | 'a' => 0b00,
                'C' | 'c' => 0b01,
                'G' | 'g' => 0b10,
                'T' | 't' => 0b11,
                _ => 0b00, // Treat N and other characters as A
            };
            encoded |= (bits as u64) << (i * 2);
        }
        encoded
    }

    /// Simple k-mer decoding for testing purposes
    /// TODO: Replace with real k-mer decoding when database module is integrated
    fn simple_decode_kmer(&self, encoded: u64, length: usize) -> String {
        let mut kmer = String::with_capacity(length);
        for i in 0..length {
            let bits = ((encoded >> (i * 2)) & 0b11) as usize;
            let base = match bits {
                0b00 => 'A',
                0b01 => 'C',
                0b10 => 'G',
                0b11 => 'T',
                _ => 'A',
            };
            kmer.push(base);
        }
        kmer
    }
    /// Create a new Database instance with optional parameters
    #[new]
    #[pyo3(signature = (file_path=None, preload=false, k=None))]
    fn new(file_path: Option<String>, preload: bool, k: Option<usize>) -> PyResult<Self> {
        let backend = if let Some(path) = file_path {
            // Check if the path is a directory (KmerCounter-created database)
            let db_path = PathBuf::from(&path);

            if db_path.is_dir() {
                // Create placeholder backend first
                let backend = DatabaseBackend {
                    path: Some(db_path.clone()),
                    kmer_size: k.or(Some(21)), // Will be updated by load_kmercounter_database
                    total_kmers: Some(0), // Will be updated by load_kmercounter_database
                    is_open: true,
                    preloaded: preload,
                    canonical: false, // Will be updated by load_kmercounter_database
                    sorted: true,
                    memory_store: Some(HashMap::new()), // Will be populated by load_kmercounter_database
                };

                // Create the PyDatabase instance first
                let mut py_db = PyDatabase {
                    backend: Arc::new(RwLock::new(backend)),
                };

                // Now load the actual database data
                py_db.load_kmercounter_database(path, preload)?;

                // Return the loaded database
                return Ok(py_db);
            } else {
                // Legacy database file loading (placeholder for now)
                DatabaseBackend {
                    path: Some(PathBuf::from(path)),
                    kmer_size: k.or(Some(21)), // Use provided k or default to 21
                    total_kmers: Some(0), // Placeholder - will be read from actual database
                    is_open: true,
                    preloaded: preload,
                    canonical: false, // Placeholder - will be read from actual database
                    sorted: true,      // Placeholder - will be read from actual database
                    memory_store: Some(HashMap::new()), // For testing purposes
                }
            }
        } else {
            // Create in-memory database (no file)
            DatabaseBackend {
                path: None,
                kmer_size: k.or(Some(21)), // Use provided k or default to 21 for in-memory database
                total_kmers: None,
                is_open: false,
                preloaded: false,
                canonical: false,
                sorted: false,
                memory_store: Some(HashMap::new()),
            }
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

    /// Query a single k-mer and return a QueryResult
    fn query(&self, kmer: &str) -> PyResult<PyQueryResult> {
        #[cfg(feature = "profiling")]
        let _timer = rustkmer::core::monitoring::start_timer("database_query_single");

        let backend = self.backend.read();

        if !backend.is_open {
            return Err(DatabaseError::new_err("Database is not open"));
        }

        // TODO: Use real DatabaseQuery when available
        // For now, provide a simplified implementation
        let result = if let Some(ref memory_store) = backend.memory_store {
            // Simple k-mer encoding for testing
            let encoded_kmer = self.simple_encode_kmer(kmer);
            match memory_store.get(&encoded_kmer) {
                Some(&count) => {
                    #[cfg(feature = "profiling")]
                    rustkmer::core::monitoring::record_metric("database_query_single", "found", 1.0);
                    Ok(PyQueryResult::new(kmer.to_uppercase(), count as u64, true))
                },
                None => {
                    #[cfg(feature = "profiling")]
                    rustkmer::core::monitoring::record_metric("database_query_single", "found", 0.0);
                    Ok(PyQueryResult::new(kmer.to_uppercase(), 0, false))
                },
            }
        } else {
            // Return placeholder result when no database is loaded
            Ok(PyQueryResult::new(kmer.to_uppercase(), 0, false))
        };

        #[cfg(feature = "profiling")]
        rustkmer::core::monitoring::record_metric("database_query_single", "kmer_length", kmer.len() as f64);

        result
    }

    /// Query multiple k-mers in batch
    fn query_multiple(&self, kmers: Vec<String>) -> PyResult<Vec<PyQueryResult>> {
        #[cfg(feature = "profiling")]
        let _timer = rustkmer::core::monitoring::start_timer("database_query_batch");

        let backend = self.backend.read();

        if !backend.is_open {
            return Err(DatabaseError::new_err("Database is not open"));
        }

        let mut found_count = 0;
        let mut total_length = 0u64;

        // TODO: Use real DatabaseQuery when available
        let mut results = Vec::with_capacity(kmers.len());
        for kmer in &kmers {
            total_length += kmer.len() as u64;
            if let Some(ref memory_store) = backend.memory_store {
                let encoded_kmer = self.simple_encode_kmer(kmer);
                match memory_store.get(&encoded_kmer) {
                    Some(&count) => {
                        found_count += 1;
                        results.push(PyQueryResult::new(kmer.to_uppercase(), count as u64, true));
                    },
                    None => results.push(PyQueryResult::new(kmer.to_uppercase(), 0, false)),
                }
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

    /// Get the k-mer size from the database
    fn get_kmer_size(&self) -> PyResult<usize> {
        let backend = self.backend.read();

        if let Some(kmer_size) = backend.kmer_size {
            Ok(kmer_size)
        } else {
            Err(DatabaseError::new_err("No database loaded"))
        }
    }

    /// Get the k-mer size (alias for get_kmer_size)
    fn get_k(&self) -> PyResult<usize> {
        self.get_kmer_size()
    }

    /// Get database statistics
    fn get_stats(&self) -> PyResult<PyDatabaseStats> {
        let backend = self.backend.read();

        if !backend.is_open {
            return Err(DatabaseError::new_err("Database is not open"));
        }

        Ok(PyDatabaseStats::new(
            backend.kmer_size.unwrap_or(0),
            backend.total_kmers.unwrap_or(0),
            backend.total_kmers.unwrap_or(0), // unique_kmers same as total_kmers for now
            backend.sorted,
            backend.canonical,
            backend.preloaded,
        ))
    }

    /// Load a database from file
    fn load(&mut self, file_path: &str, preload: bool) -> PyResult<()> {
        // Try to load as KmerCounter-created database first
        let db_path = PathBuf::from(file_path);

        if db_path.is_dir() {
            // Load KmerCounter-created database (hybrid format)
            self.load_kmercounter_database(file_path.to_string(), preload)
        } else {
            // Legacy database file loading (placeholder for now)
            self.load_legacy_database(file_path, preload)
        }
    }

    /// Load KmerCounter-created database with hybrid format
    fn load_kmercounter_database(&mut self, database_path: String, preload: bool) -> PyResult<()> {
        let db_path = std::path::Path::new(&database_path);

        // Read metadata.json for proper kmer_size and other metadata
        let metadata_path = db_path.join("metadata.json");
        let metadata_content = std::fs::read_to_string(&metadata_path)
            .map_err(|e| DatabaseError::new_err(format!("Failed to read metadata file: {}", e)))?;

        let metadata: serde_json::Value = serde_json::from_str(&metadata_content)
            .map_err(|e| DatabaseError::new_err(format!("Failed to parse metadata: {}", e)))?;

        // Extract kmer_size from metadata
        let kmer_size = metadata["kmer_size"].as_u64()
            .ok_or_else(|| DatabaseError::new_err("Missing kmer_size in metadata"))? as usize;

        let canonical = metadata["canonical"].as_bool().unwrap_or(false);

        // Read k-mer counts from data.rkdb (JSON format for stub implementation)
        let data_path = db_path.join("data.rkdb");
        let data_content = std::fs::read_to_string(&data_path)
            .map_err(|e| DatabaseError::new_err(format!("Failed to read data file: {}", e)))?;

        let kmer_counts: HashMap<String, u64> = serde_json::from_str(&data_content)
            .map_err(|e| DatabaseError::new_err(format!("Failed to parse data file: {}", e)))?;

        // Convert k-mer counts to memory store format
        let mut memory_store = HashMap::new();
        let mut total_kmers = 0u64;

        for (kmer, count) in kmer_counts.iter() {
            let encoded_kmer = self.simple_encode_kmer(kmer);
            memory_store.insert(encoded_kmer, *count as u32);
            total_kmers += count;
        }

        // Update backend with correct metadata
        let mut backend = self.backend.write();
        backend.path = Some(PathBuf::from(database_path));
        backend.kmer_size = Some(kmer_size);
        backend.total_kmers = Some(total_kmers);
        backend.is_open = true;
        backend.preloaded = preload;
        backend.canonical = canonical;
        backend.sorted = true; // Assume sorted for stub implementation
        backend.memory_store = Some(memory_store);

        Ok(())
    }

    /// Load legacy database file (placeholder implementation)
    fn load_legacy_database(&mut self, file_path: &str, preload: bool) -> PyResult<()> {
        // TODO: Implement real database loading when DatabaseQuery is available
        let mut backend = self.backend.write();
        backend.path = Some(PathBuf::from(file_path));
        backend.kmer_size = Some(21); // Placeholder - will be read from actual database
        backend.total_kmers = Some(0); // Placeholder - will be read from actual database
        backend.is_open = true;
        backend.preloaded = preload;
        backend.memory_store = Some(HashMap::new());

        Ok(())
    }

    /// Get count for a specific k-mer (compatibility method)
    fn get_count(&self, kmer: &str) -> PyResult<u64> {
        let result = self.query(kmer)?;
        Ok(result.count)
    }

    /// Get all k-mer counts
    fn get_all_counts(&self) -> PyResult<HashMap<String, u64>> {
        let backend = self.backend.read();

        if !backend.is_open {
            return Err(DatabaseError::new_err("Database is not open"));
        }

        let mut all_counts = HashMap::new();

        if let Some(ref memory_store) = backend.memory_store {
            for (encoded_kmer, &count) in memory_store {
                // Use proper k-mer decoding
                let kmer = self.simple_decode_kmer(*encoded_kmer, backend.kmer_size.unwrap_or(21));
                all_counts.insert(kmer, count as u64);
            }
        }

        Ok(all_counts)
    }

    /// Get database metadata
    fn get_metadata(&self) -> PyResult<PyObject> {
        // TODO: Re-enable full persistence implementation when core module naming conflicts are resolved
        // For now, create a simple stub implementation that returns basic metadata

        let backend = self.backend.read();

        Python::with_gil(|py| {
            let dict = pyo3::types::PyDict::new(py);

            if let Some(ref path_str) = backend.path {
                dict.set_item("database_path", path_str)?;
                dict.set_item("kmer_size", backend.kmer_size.unwrap_or(0))?;
                dict.set_item("total_kmers", backend.total_kmers.unwrap_or(0))?;
                dict.set_item("is_open", backend.is_open)?;
                dict.set_item("preloaded", backend.preloaded)?;
                dict.set_item("canonical", backend.canonical)?;
                dict.set_item("sorted", backend.sorted)?;
                dict.set_item("format", "JSON (stub implementation)")?;
                dict.set_item("note", "Temporary stub implementation - full persistence pending core module resolution")?;
            } else {
                dict.set_item("error", "No database loaded")?;
            }

            Ok(dict.into())
        })
    }

    /// Close the database
    fn close(&self) -> PyResult<()> {
        let mut backend = self.backend.write();
        backend.is_open = false;
        backend.memory_store = None;
        Ok(())
    }

    /// Get the database file path
    fn get_path(&self) -> Option<String> {
        self.backend.read().path.as_ref().map(|p| p.to_string_lossy().to_string())
    }

    /// Check if database is open
    fn is_open(&self) -> bool {
        self.backend.read().is_open
    }

    /// Check if database is preloaded into memory
    fn is_preloaded(&self) -> bool {
        self.backend.read().preloaded
    }

    /// Get a string representation
    fn __repr__(&self) -> String {
        let backend = self.backend.read();
        match (&backend.path, backend.kmer_size) {
            (Some(path), Some(kmer_size)) => format!(
                "Database(path={}, k={}, open={}, preloaded={}, total_kmers={})",
                path.display(),
                kmer_size,
                backend.is_open,
                backend.preloaded,
                backend.total_kmers.unwrap_or(0)
            ),
            _ => format!("Database(closed={})", !backend.is_open),
        }
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