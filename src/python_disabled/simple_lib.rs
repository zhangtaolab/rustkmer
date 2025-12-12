//! Simplified RustKmer Python bindings
//!
//! This module provides a simplified Python API that directly implements
//! the core functionality needed for the 007-api-compatibility feature.
//! It focuses on database format consistency and query interoperability
//! without the complex module dependencies that were causing compilation issues.

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;
use std::fs::File;
use std::io::{BufRead, BufReader, Read, Write};
use std::path::Path;

// Include the core database functionality directly
use crate::database::query::DatabaseQuery;
use crate::database::format::{DatabaseHeader, DatabaseEntry, KmerEntry};
use crate::kmer::{encode_kmer, decode_kmer, canonical_kmer};

/// Simple Kmer counter for Python API
#[pyclass(name = "KmerCounter")]
pub struct SimpleKmerCounter {
    k: usize,
    canonical: bool,
    threads: usize,
    kmer_counts: Arc<RwLock<HashMap<String, u64>>>,
}

#[pymethods]
impl SimpleKmerCounter {
    #[new]
    #[pyo3(signature = (k, canonical=false, threads=1))]
    fn new(k: usize, canonical: bool, threads: usize) -> PyResult<Self> {
        if k == 0 || k > 31 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "K-mer size must be between 1 and 31"
            ));
        }

        Ok(Self {
            k,
            canonical,
            threads: threads.max(1),
            kmer_counts: Arc::new(RwLock::new(HashMap::new())),
        })
    }

    /// Get the k-mer size
    #[getter]
    fn get_k(&self) -> usize {
        self.k
    }

    /// Get canonical setting
    #[getter]
    fn get_canonical(&self) -> bool {
        self.canonical
    }

    /// Get thread count
    #[getter]
    fn get_threads(&self) -> usize {
        self.threads
    }

    /// Count k-mers from a FASTA file
    fn count_file(&self, file_path: &str) -> PyResult<HashMap<String, u64>> {
        if !Path::new(file_path).exists() {
            return Err(pyo3::exceptions::PyFileNotFoundError::new_err(format!("File not found: {}", file_path)));
        }

        let file = File::open(file_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to open file: {}", e)))?;

        let reader = BufReader::new(file);
        let mut counts = self.kmer_counts.write();

        counts.clear();

        for line in reader.lines() {
            let line = match line {
                Ok(l) => l,
                Err(_) => continue,
            };

            if line.starts_with('>') {
                continue; // Skip header lines
            }

            let sequence = line.trim().to_ascii_uppercase();

            if sequence.is_empty() || !sequence.chars().all(|c| c.is_ascii_uppercase() || c == 'N') {
                continue;
            }

            // Extract k-mers from the sequence
            for i in 0..=(sequence.len().saturating_sub(self.k)) {
                let kmer = &sequence[i..i + self.k];
                if kmer.len() == self.k && !kmer.contains('N') {
                    let encoded_kmer = match encode_kmer(kmer) {
                        Ok(encoded) => encoded,
                        Err(_) => continue,
                    };

                    let canonical_kmer = if self.canonical {
                        match canonical_kmer(kmer, self.k) {
                            Ok(canon) => canon,
                            Err(_) => encoded_kmer,
                        }
                    } else {
                        encoded_kmer
                    };

                    *counts.entry(kmer.to_string()).or_insert(0) += 1;
                }
            }
        }

        Ok(counts.clone())
    }

    /// Count k-mers from a string sequence
    fn count_string(&self, sequence: &str) -> PyResult<HashMap<String, u64>> {
        let sequence = sequence.trim().to_ascii_uppercase();
        let mut counts = self.kmer_counts.write();

        counts.clear();

        // Extract k-mers from the sequence
        for i in 0..=(sequence.len().saturating_sub(self.k)) {
            let kmer = &sequence[i..i + self.k];
            if kmer.len() == self.k && !kmer.contains('N') {
                let encoded_kmer = match encode_kmer(kmer) {
                    Ok(encoded) => encoded,
                    Err(_) => continue,
                };

                let canonical_kmer = if self.canonical {
                    match canonical_kmer(kmer, self.k) {
                        Ok(canon) => canon,
                        Err(_) => encoded_kmer,
                    }
                } else {
                    encoded_kmer
                };

                *counts.entry(kmer.to_string()).or_insert(0) += 1;
            }
        }

        Ok(counts.clone())
    }

    /// Save k-mer counts to database in unified .rkdb format
    fn save_to_database(&self, database_path: &str, _compression: bool) -> PyResult<()> {
        let counts = self.kmer_counts.read();
        let total_kmers = counts.len() as u64;

        // Create database header
        let header = DatabaseHeader {
            magic: *crate::database::format::DATABASE_MAGIC,
            version: crate::database::format::DATABASE_VERSION,
            kmer_size: self.k as u8,
            total_kmers,
            flags: if self.canonical { 0x02 } else { 0x00 }, // Canonical flag
            data_offset: 42, // Always 42 bytes for our format
            index_offset: 0,
            canonical: self.canonical,
            unique_kmers: total_kmers,
            file_size: 0, // Will be calculated
        };

        // Create database file
        let mut file = File::create(database_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to create database file: {}", e)))?;

        // Write header
        header.write_to(&mut file)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to write database header: {}", e)))?;

        // Write k-mer entries sorted by k-mer for binary search compatibility
        let mut entries: Vec<KmerEntry> = counts.iter()
            .map(|(kmer, count)| {
                let encoded = match encode_kmer(kmer) {
                    Ok(enc) => enc,
                    Err(_) => 0, // Skip invalid k-mers
                };
                (encoded, *count)
            })
            .collect();

        entries.sort_by_key(|entry| entry.kmer);

        for entry in entries {
            // Write k-mer (8 bytes, little-endian)
            file.write_all(&entry.kmer.to_le_bytes())
                .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to write k-mer: {}", e)))?;

            // Write count (4 bytes, little-endian)
            file.write_all(&entry.count.to_le_bytes())
                .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to write count: {}", e)))?;
        }

        Ok(())
    }

    /// Get all k-mer counts
    fn get_all_counts(&self) -> PyResult<HashMap<String, u64>> {
        Ok(self.kmer_counts.read().clone())
    }

    /// Get count for a specific k-mer
    fn get_count(&self, kmer: &str) -> PyResult<u64> {
        let counts = self.kmer_counts.read();
        Ok(counts.get(kmer).copied().unwrap_or(0))
    }

    /// Get total unique k-mers
    fn get_unique_count(&self) -> PyResult<usize> {
        Ok(self.kmer_counts.read().len())
    }

    /// Get total k-mer count (sum of all counts)
    fn get_total_count(&self) -> PyResult<u64> {
        let counts = self.kmer_counts.read();
        Ok(counts.values().sum())
    }
}

/// Database class for querying .rkdb files
#[pyclass(name = "Database")]
pub struct SimpleDatabase {
    query: Option<DatabaseQuery>,
    kmer_size: usize,
    total_kmers: u64,
    unique_kmers: u64,
    canonical: bool,
    sorted: bool,
    file_path: String,
}

#[pymethods]
impl SimpleDatabase {
    #[new]
    fn new() -> PyResult<Self> {
        Ok(Self {
            query: None,
            kmer_size: 0,
            total_kmers: 0,
            unique_kmers: 0,
            canonical: false,
            sorted: false,
            file_path: String::new(),
        })
    }

    /// Load database from file
    fn load(&mut self, file_path: &str) -> PyResult<()> {
        let path = Path::new(file_path);

        if !path.exists() {
            return Err(pyo3::exceptions::PyFileNotFoundError::new_err(format!("Database file not found: {}", file_path)));
        }

        let mut query = DatabaseQuery::open(&path, false)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to open database: {}", e)))?;

        let info = query.get_info();

        self.query = Some(query);
        self.kmer_size = info.kmer_size as usize;
        self.total_kmers = info.total_kmers;
        self.unique_kmers = info.unique_kmers;
        self.canonical = info.canonical;
        self.sorted = info.sorted;
        self.file_path = file_path.to_string();

        Ok(())
    }

    /// Get database statistics
    fn get_stats(&self) -> PyResult<DatabaseStats> {
        Ok(DatabaseStats {
            kmer_size: self.kmer_size,
            total_kmers: self.total_kmers,
            unique_kmers: self.unique_kmers,
            canonical: self.canonical,
            sorted: self.sorted,
            filename: self.file_path.clone(),
        })
    }

    /// Query a single k-mer
    fn query(&self, kmer: &str) -> PyResult<QueryResult> {
        let query = self.query.as_ref()
            .ok_or_else(|| Err(pyo3::exceptions::PyRuntimeError::new_err("Database not loaded")))?;

        let count = query.query_kmer(kmer)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Query failed: {}", e)))?;

        Ok(QueryResult {
            kmer: kmer.to_string(),
            count: count,
            found: count > 0,
        })
    }

    /// Query multiple k-mers
    fn query_multiple(&self, kmers: Vec<String>) -> PyResult<Vec<QueryResult>> {
        let query = self.query.as_ref()
            .ok_or_else(|| Err(pyo3::exceptions::PyRuntimeError::new_err("Database not loaded")))?;

        let mut results = Vec::new();

        for kmer in kmers {
            let count = query.query_kmer(&kmer)
                .unwrap_or(0);

            results.push(QueryResult {
                kmer: kmer.clone(),
                count,
                found: count > 0,
            });
        }

        Ok(results)
    }
}

/// Query result from database query
#[pyclass(name = "QueryResult")]
pub struct QueryResult {
    #[pyo3(get)]
    kmer: String,
    #[pyo3(get)]
    count: u32,
    #[pyo3(get)]
    found: bool,
}

/// Database statistics
#[pyclass(name = "DatabaseStats")]
#[derive(Clone)]
pub struct DatabaseStats {
    #[pyo3(get)]
    kmer_size: usize,
    #[pyo3(get)]
    total_kmers: u64,
    #[pyo3(get)]
    unique_kmers: u64,
    #[pyo3(get)]
    canonical: bool,
    #[pyo3(get)]
    sorted: bool,
    #[pyo3(get)]
    filename: String,
}

/// Counter statistics
#[pyclass(name = "CounterStats")]
pub struct CounterStats {
    #[pyo3(get)]
    kmer_size: usize,
    #[pyo3(get)]
    total_kmers: u64,
    #[pyo3(get)]
    unique_kmers: u64,
    #[pyo3(get)]
    canonical: bool,
    #[pyo3(get)]
    threads: usize,
}

/// Python module for RustKmer
#[pymodule]
fn _rustkmer(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Version information
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    // Core classes
    m.add_class::<SimpleKmerCounter>()?;
    m.add_class::<SimpleDatabase>()?;
    m.add_class::<QueryResult>()?;
    m.add_class::<DatabaseStats>()?;
    m.add_class::<CounterStats>()?;

    Ok(())
}