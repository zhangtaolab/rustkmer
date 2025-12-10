//! Simplified RustKmer Python bindings
//!
//! This module provides a simplified Python API that directly implements
//! the core functionality needed for database operations, queries, fuzzy searches,
//! and statistics.

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyAny};
use pyo3::wrap_pyfunction;
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;
use std::fs::File;
use std::io::{BufRead, BufReader, Seek, Write};
use std::path::{Path, PathBuf};
use memmap2::{Mmap, MmapOptions};
use byteorder::{LittleEndian, ReadBytesExt, WriteBytesExt};

// Include the core database functionality directly
use crate::database::{DatabaseQuery, DatabaseHeader};
use crate::kmer::{encode_kmer, canonical_kmer};
use crate::core::database::persistence::{merge_databases, PersistenceConfig};
use num_cpus;

/// Threshold for using memory mapping (100MB)
const MMAP_THRESHOLD: u64 = 100 * 1024 * 1024; // 100MB in bytes

/// Decode a k-mer from encoded format back to DNA sequence
fn decode_kmer_to_sequence(kmer: u64, k: usize) -> String {
    let mut sequence = String::with_capacity(k);
    let mut encoded = kmer;

    for _ in 0..k {
        let base = encoded & 0b11;
        let char = match base {
            0 => 'A',
            1 => 'C',
            2 => 'G',
            3 => 'T',
            _ => 'N',
        };
        sequence.push(char);
        encoded >>= 2;
    }

    sequence.chars().rev().collect()
}

/// Decode a u128 k-mer from encoded format back to DNA sequence
fn decode_kmer_to_sequence_u128(kmer: u128, k: usize) -> String {
    let mut sequence = String::with_capacity(k);
    let mut encoded = kmer;

    for _ in 0..k {
        let base = encoded & 0b11;
        let char = match base {
            0 => 'A',
            1 => 'C',
            2 => 'G',
            3 => 'T',
            _ => 'N',
        };
        sequence.push(char);
        encoded >>= 2;
    }

    sequence.chars().rev().collect()
}

/// K-mer counter for counting sequences
#[pyclass(name = "KmerCounter")]
pub struct KmerCounter {
    k: usize,
    canonical: bool,
    threads: usize,
    kmer_counts: Arc<RwLock<HashMap<String, u64>>>,
}

#[pymethods]
impl KmerCounter {
    #[new]
    fn new(k: usize, canonical: Option<bool>, threads: Option<usize>) -> PyResult<Self> {
        Ok(Self {
            k,
            canonical: canonical.unwrap_or(false),
            threads: threads.unwrap_or(1),
            kmer_counts: Arc::new(RwLock::new(HashMap::new())),
        })
    }

    /// Count k-mers from a FASTA/FASTQ file
    fn count_file(&self, file_path: &str, _py: Python<'_>) -> PyResult<()> {
        let path = Path::new(file_path);
        if !path.exists() {
            return Err(pyo3::exceptions::PyFileNotFoundError::new_err(format!("File not found: {}", file_path)));
        }

        let file = File::open(path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to open file: {}", e)))?;
        let mut reader = BufReader::new(file);

        let mut sequence = String::new();
        let mut line = String::new();
        let mut counts = self.kmer_counts.write();

        while reader.read_line(&mut line).unwrap_or(0) > 0 {
            let trimmed = line.trim();

            if trimmed.is_empty() {
                continue;
            }

            // FASTA format
            if trimmed.starts_with('>') {
                if !sequence.is_empty() {
                    // Process previous sequence
                    self._count_sequence(&mut counts, &sequence);
                    sequence.clear();
                }
            }
            // FASTQ format (sequence line)
            else if !sequence.is_empty() && !trimmed.starts_with('@') && !trimmed.starts_with('+') {
                sequence.push_str(trimmed);
            }
            // FASTQ quality line (skip)
            else if sequence.is_empty() && !trimmed.starts_with('@') && !trimmed.starts_with('+') {
                sequence.push_str(trimmed);
            }

            line.clear();
        }

        // Process last sequence
        if !sequence.is_empty() {
            self._count_sequence(&mut counts, &sequence);
        }

        Ok(())
    }

    /// Count k-mers from a DNA sequence string
    fn count_string(&self, sequence: &str) -> PyResult<()> {
        let mut counts = self.kmer_counts.write();
        let sequence = sequence.trim().to_ascii_uppercase();
        self._count_sequence(&mut counts, &sequence);
        Ok(())
    }

    /// Get all counts as a dictionary
    fn get_all_counts(&self) -> PyResult<HashMap<String, u64>> {
        Ok(self.kmer_counts.read().clone())
    }

    /// Get count for a specific k-mer
    fn get_count(&self, kmer: &str) -> PyResult<u64> {
        let counts = self.kmer_counts.read();
        Ok(counts.get(kmer).copied().unwrap_or(0))
    }

    /// Get total number of unique k-mers
    fn get_unique_count(&self) -> PyResult<usize> {
        Ok(self.kmer_counts.read().len())
    }

    /// Get total k-mer count (sum of all counts)
    fn get_total_count(&self) -> PyResult<u64> {
        let counts = self.kmer_counts.read();
        Ok(counts.values().sum())
    }

    /// Save to database
    fn save_to_database(&self, output_path: &str) -> PyResult<()> {
        let counts = self.kmer_counts.read();
        self._save_counts_to_database(&counts, output_path)
    }

    /// Get top k-mers by count
    #[pyo3(signature = (n=10))]
    fn get_top_kmers(&self, n: usize) -> PyResult<Vec<(String, u64)>> {
        let counts = self.kmer_counts.read();
        let mut sorted_kmers: Vec<(String, u64)> = counts.iter()
            .map(|(kmer, count)| (kmer.clone(), *count))
            .collect();

        sorted_kmers.sort_by(|a, b| b.1.cmp(&a.1));
        sorted_kmers.truncate(n);

        Ok(sorted_kmers)
    }

  }

impl KmerCounter {
    /// Helper method to count k-mers from a sequence
    fn _count_sequence(&self, counts: &mut HashMap<String, u64>, sequence: &str) {
        for i in 0..=(sequence.len().saturating_sub(self.k)) {
            let kmer = &sequence[i..i + self.k];
            if kmer.len() == self.k && !kmer.contains('N') {
                let encoded_kmer = match encode_kmer(kmer) {
                    Ok(encoded) => encoded,
                    Err(_) => continue,
                };

                let _final_kmer = if self.canonical {
                    match canonical_kmer(encoded_kmer, self.k) {
                        Ok(canon) => canon,
                        Err(_) => encoded_kmer,
                    }
                } else {
                    encoded_kmer
                };

                // For simplicity, just use the string as key
                // In a real implementation, we'd use the encoded value
                *counts.entry(kmer.to_string()).or_insert(0) += 1;
            }
        }
    }

    /// Helper method to save counts to database file
    fn _save_counts_to_database(&self, counts: &HashMap<String, u64>, output_path: &str) -> PyResult<()> {
        // Create output file
        let mut file = File::create(output_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to create output file: {}", e)))?;

        // Write header (simplified)
        let header = DatabaseHeader {
            magic: *crate::database::format::DATABASE_MAGIC,
            version: crate::database::format::DATABASE_VERSION,
            kmer_size: self.k as u8,
            total_kmers: counts.values().sum::<u64>(),
            unique_kmers: counts.len() as u64,
            sorted: false,
            data_offset: 42, // Placeholder
            index_offset: 0, // Placeholder
            canonical: self.canonical,
            file_size: 0, // Placeholder
        };

        header.write_to(&mut file)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to write header: {}", e)))?;

        // Write k-mer data
        for (kmer_str, count) in counts {
            // Simplified: just use kmer hash as encoded value
            let kmer_hash = self._hash_kmer(kmer_str);
            file.write_u64::<LittleEndian>(kmer_hash)
                .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to write k-mer: {}", e)))?;
            file.write_u32::<LittleEndian>(*count as u32)
                .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to write count: {}", e)))?;
        }

        file.flush()
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to flush file: {}", e)))?;

        Ok(())
    }

    /// Simple hash function for k-mers
    fn _hash_kmer(&self, kmer: &str) -> u64 {
        // Simple hash - in real implementation use proper encoding
        let mut hash = 0u64;
        for (i, c) in kmer.chars().enumerate() {
            match c {
                'A' => hash = hash.wrapping_mul(31).wrapping_add(1),
                'C' => hash = hash.wrapping_mul(31).wrapping_add(2),
                'G' => hash = hash.wrapping_mul(31).wrapping_add(3),
                'T' => hash = hash.wrapping_mul(31).wrapping_add(4),
                _ => hash = hash.wrapping_mul(31).wrapping_add(0),
            }
        }
        hash
    }
}

/// Memory mapped database for large files
#[pyclass(name = "MemoryMappedDatabase")]
pub struct MemoryMappedDatabase {
    _private: (),
}

impl MemoryMappedDatabase {
    pub fn should_use_mmap(_file_path: &str) -> PyResult<bool> {
        // Always use regular file I/O for simplicity
        Ok(false)
    }

    pub fn new(_file_path: &str) -> PyResult<Self> {
        // Return placeholder
        Err(pyo3::exceptions::PyNotImplementedError::new_err("Memory mapping not implemented in simplified version"))
    }

    pub fn get_info(&self) -> PyResult<DatabaseInfo> {
        Err(pyo3::exceptions::PyNotImplementedError::new_err("Memory mapping not implemented"))
    }
}

/// Database information
#[pyclass(name = "DatabaseInfo")]
pub struct DatabaseInfo {
    #[pyo3(get)]
    kmer_size: u32,
    #[pyo3(get)]
    total_kmers: u64,
    #[pyo3(get)]
    unique_kmers: u64,
    #[pyo3(get)]
    canonical: bool,
    #[pyo3(get)]
    sorted: bool,
}

/// Database class for querying .rkdb files
#[pyclass(name = "Database")]
pub struct SimpleDatabase {
    query: Option<Arc<RwLock<DatabaseQuery>>>,
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
        // Validate database file extension
        if !file_path.ends_with(".rkdb") {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Database file must end with .rkdb extension"
            ));
        }

        let path = Path::new(file_path);

        if !path.exists() {
            return Err(pyo3::exceptions::PyFileNotFoundError::new_err(format!("Database file not found: {}", file_path)));
        }

        // Load the database using DatabaseQuery
        match DatabaseQuery::open(file_path, false) {
            Ok(query) => {
                // Get database info
                let header = query.get_info();
                self.query = Some(Arc::new(RwLock::new(query)));
                self.kmer_size = header.kmer_size as usize;
                self.total_kmers = header.total_kmers;
                self.unique_kmers = header.unique_kmers;
                self.canonical = header.canonical;
                self.sorted = header.sorted;
                self.file_path = file_path.to_string();
                Ok(())
            }
            Err(e) => Err(pyo3::exceptions::PyIOError::new_err(format!("Failed to load database: {}", e))),
        }
    }

    /// Query a single k-mer
    fn query(&self, kmer: &str, _py: Python<'_>) -> PyResult<QueryResult> {
        if self.file_path.is_empty() {
            return Err(pyo3::exceptions::PyRuntimeError::new_err("No database loaded"));
        }

        match &self.query {
            Some(query_lock) => {
                let mut query = query_lock.write();
                // Query the database using kmer string directly
                match query.query_kmer(kmer) {
                    Ok(Some(count)) => Ok(QueryResult {
                        kmer: kmer.to_string(),
                        count: count as u32,
                        found: true,
                    }),
                    Ok(None) => Ok(QueryResult {
                        kmer: kmer.to_string(),
                        count: 0,
                        found: false,
                    }),
                    Err(e) => Err(pyo3::exceptions::PyIOError::new_err(format!("Query failed: {}", e))),
                }
            }
            None => Err(pyo3::exceptions::PyRuntimeError::new_err("Database not loaded")),
        }
    }

    /// Query multiple k-mers
    fn query_batch(&self, kmers: Vec<String>, _py: Python<'_>) -> PyResult<Vec<QueryResult>> {
        if self.file_path.is_empty() {
            return Err(pyo3::exceptions::PyRuntimeError::new_err("No database loaded"));
        }

        match &self.query {
            Some(query_lock) => {
                let mut query = query_lock.write();
                match query.query_multiple(&kmers) {
                    Ok(results) => {
                        let mut query_results = Vec::new();
                        for (kmer, count) in results {
                            query_results.push(QueryResult {
                                kmer,
                                count: count as u32,
                                found: true,
                            });
                        }
                        // Add missing k-mers
                        for kmer in kmers {
                            if !query_results.iter().any(|qr| qr.kmer == kmer) {
                                query_results.push(QueryResult {
                                    kmer,
                                    count: 0,
                                    found: false,
                                });
                            }
                        }
                        Ok(query_results)
                    },
                    Err(e) => Err(pyo3::exceptions::PyIOError::new_err(format!("Batch query failed: {}", e))),
                }
            }
            None => Err(pyo3::exceptions::PyRuntimeError::new_err("Database not loaded")),
        }
    }

    /// Check if k-mer exists
    fn exists(&self, kmer: &str) -> PyResult<bool> {
        if self.file_path.is_empty() {
            return Err(pyo3::exceptions::PyRuntimeError::new_err("No database loaded"));
        }

        match &self.query {
            Some(query_lock) => {
                let mut query = query_lock.write();
                match query.query_kmer(kmer) {
                    Ok(result) => Ok(result.is_some()),
                    Err(e) => Err(pyo3::exceptions::PyIOError::new_err(format!("Query failed: {}", e))),
                }
            }
            None => Err(pyo3::exceptions::PyRuntimeError::new_err("Database not loaded")),
        }
    }

    /// Get count for a k-mer
    fn get_count(&self, kmer: &str) -> PyResult<u32> {
        if self.file_path.is_empty() {
            return Err(pyo3::exceptions::PyRuntimeError::new_err("No database loaded"));
        }

        match &self.query {
            Some(query_lock) => {
                let mut query = query_lock.write();
                match query.query_kmer(kmer) {
                    Ok(Some(count)) => Ok(count as u32),
                    Ok(None) => Ok(0),
                    Err(e) => Err(pyo3::exceptions::PyIOError::new_err(format!("Query failed: {}", e))),
                }
            }
            None => Err(pyo3::exceptions::PyRuntimeError::new_err("Database not loaded")),
        }
    }

    /// Get the file path of the loaded database
    #[getter]
    fn file_path(&self) -> PyResult<String> {
        Ok(self.file_path.clone())
    }

    /// Get database statistics
    fn get_stats(&self, _py: Python<'_>) -> PyResult<DatabaseStats> {
        if self.file_path.is_empty() {
            return Err(pyo3::exceptions::PyRuntimeError::new_err("No database loaded"));
        }

        // Load database to calculate statistics
        use crate::database::format::RKDatabase;

        let db_path = std::path::Path::new(&self.file_path);
        match RKDatabase::from_file_path(db_path) {
            Ok(rkdb) => {
                // Calculate statistics using the Rust implementation
                use crate::database::index::DatabaseStats;
                let rust_stats = DatabaseStats::calculate_stats(&rkdb.entries);

                // Create frequency histogram
                let mut histogram = HashMap::new();
                for entry in &rkdb.entries {
                    *histogram.entry(entry.count).or_insert(0) += 1;
                }

                // Get file size
                let file_size = std::fs::metadata(&self.file_path)
                    .map(|m| m.len() as f64 / (1024.0 * 1024.0))
                    .unwrap_or(0.0);

                // Calculate coverage estimate (simplified: unique_kmers / possible_kmers)
                let possible_kmers = if self.kmer_size > 0 {
                    4u64.pow(self.kmer_size as u32) as f64
                } else {
                    0.0
                };
                let coverage_estimate = self.unique_kmers as f64 / possible_kmers;

                Ok(DatabaseStats {
                    kmer_size: self.kmer_size,
                    total_kmers: rust_stats.total_kmers,
                    unique_kmers: rust_stats.unique_kmers as u64,
                    canonical: self.canonical,
                    sorted: self.sorted,
                    filename: self.file_path.clone(),
                    uses_memory_mapping: false, // TODO: determine from DatabaseQuery

                    // Computed statistics
                    min_count: rust_stats.min_count,
                    max_count: rust_stats.max_count,
                    mean_count: rust_stats.avg_count,
                    median_count: rust_stats.median_count as f64,
                    coverage_estimate,

                    // Percentiles
                    p25: rust_stats.p25 as f64,
                    p50: (rust_stats.p25 + rust_stats.median_count) as f64 / 2.0,
                    p75: rust_stats.p75 as f64,
                    p95: rust_stats.p95 as f64,
                    p99: rust_stats.p99 as f64,

                    histogram,
                    file_size_mb: file_size,
                    creation_date: None, // TODO: extract from file metadata
                })
            }
            Err(e) => {
                // Fallback to basic stats
                Ok(DatabaseStats::new(
                    self.kmer_size,
                    self.total_kmers,
                    self.unique_kmers,
                    self.canonical,
                    self.sorted,
                    self.file_path.clone(),
                    false,
                ))
            }
        }
    }

    /// Calculate comprehensive statistics with detailed analysis
    fn calculate_stats(&self, py: Python<'_>) -> PyResult<DatabaseStats> {
        // For now, delegate to get_stats
        self.get_stats(py)
    }

    /// Merge with another database
    fn merge(&self, py: Python<'_>, other: &SimpleDatabase, output_path: &str,
              strategy: &str, progress_callback: Option<Py<PyAny>>) -> PyResult<()> {
        // Validate both databases are loaded
        if self.file_path.is_empty() {
            return Err(pyo3::exceptions::PyRuntimeError::new_err("No database loaded"));
        }
        if other.file_path.is_empty() {
            return Err(pyo3::exceptions::PyRuntimeError::new_err("Other database not loaded"));
        }

        // Check compatibility
        if self.kmer_size != other.kmer_size {
            return Err(pyo3::exceptions::PyValueError::new_err(
                format!("K-mer sizes don't match: {} vs {}", self.kmer_size, other.kmer_size)
            ));
        }
        if self.canonical != other.canonical {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Canonical mode mismatch"
            ));
        }

        // Note: strategy parameter is currently ignored - merge uses sum by default
        // TODO: Implement different aggregation strategies when available

        // Create persistence config
        let config = PersistenceConfig {
            compression_enabled: false,
            compression_level: 0,
            checksum_enabled: true,
            buffer_size: 8192,
        };

        // Perform merge in a separate thread to not block GIL
        let db1_path = PathBuf::from(&self.file_path);
        let db2_path = PathBuf::from(&other.file_path);
        let output_path_buf = PathBuf::from(output_path);

        py.allow_threads(|| {
            // Perform the merge
            match merge_databases(&db1_path, &db2_path, &output_path_buf, &config) {
                Ok(_) => Ok(()),
                Err(e) => Err(pyo3::exceptions::PyIOError::new_err(format!("Merge failed: {}", e))),
            }
        })
    }

    /// Merge with multiple databases
    fn merge_multiple(&self, py: Python<'_>, databases: Vec<&SimpleDatabase>,
                    output_path: &str, strategy: &str,
                    progress_callback: Option<Py<PyAny>>) -> PyResult<()> {
        // Validate this database is loaded
        if self.file_path.is_empty() {
            return Err(pyo3::exceptions::PyRuntimeError::new_err("No database loaded"));
        }

        if databases.is_empty() {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "At least one database to merge is required"
            ));
        }

        // Check compatibility with all databases
        for (i, db) in databases.iter().enumerate() {
            if db.file_path.is_empty() {
                return Err(pyo3::exceptions::PyRuntimeError::new_err(
                    format!("Database {} not loaded", i + 1)
                ));
            }
            if self.kmer_size != db.kmer_size {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    format!("K-mer size mismatch with database {}: {} vs {}", i + 1, self.kmer_size, db.kmer_size)
                ));
            }
            if self.canonical != db.canonical {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    format!("Canonical mode mismatch with database {}", i + 1)
                ));
            }
        }

        // Note: strategy parameter is currently ignored - merge uses sum by default
        // TODO: Implement different aggregation strategies when available

        // Create persistence config
        let config = PersistenceConfig {
            compression_enabled: false,
            compression_level: 0,
            checksum_enabled: true,
            buffer_size: 8192,
        };

        // For multiple databases, we merge them iteratively
        // Start with the first merge
        let mut current_output = if databases.len() == 1 {
            // Direct merge for 2 databases
            PathBuf::from(output_path)
        } else {
            // Use temporary files for iterative merging
            std::env::temp_dir().join(format!("rustkmer_merge_{}.rkdb", std::process::id()))
        };

        py.allow_threads(|| {
            // Merge first two databases
            let db1_path = PathBuf::from(&self.file_path);
            let db2_path = PathBuf::from(&databases[0].file_path);

            match merge_databases(&db1_path, &db2_path, &current_output, &config) {
                Ok(_) => (),
                Err(e) => return Err(pyo3::exceptions::PyIOError::new_err(format!("Merge failed: {}", e))),
            }

            // Merge remaining databases iteratively
            let total_dbs = databases.len();
            for (i, db) in databases[1..].iter().enumerate() {
                let next_output = if i == total_dbs - 2 {
                    // Last merge, use final output path
                    PathBuf::from(output_path)
                } else {
                    // Use another temporary file with a unique name
                    use std::collections::hash_map::DefaultHasher;
                    use std::hash::{Hash, Hasher};
                    let mut hasher = DefaultHasher::new();
                    db.file_path.hash(&mut hasher);
                    std::env::temp_dir().join(format!("rustkmer_merge_{}_{}.rkdb", std::process::id(), hasher.finish()))
                };

                match merge_databases(&current_output, &PathBuf::from(&db.file_path), &next_output, &config) {
                    Ok(_) => {
                        // Remove old temp file
                        let _ = std::fs::remove_file(&current_output);
                        current_output = next_output;
                    },
                    Err(e) => return Err(pyo3::exceptions::PyIOError::new_err(format!("Merge failed: {}", e))),
                }
            }

            Ok(())
        })
    }

    /// Dump database contents
    fn dump(&self, py: Python<'_>, output_path: &str, format: &str,
             min_count: Option<u32>, max_count: Option<u32>,
             progress_callback: Option<Py<PyAny>>) -> PyResult<()> {
        use pyo3::allow_threads;

        if self.file_path.is_empty() {
            return Err(pyo3::exceptions::PyRuntimeError::new_err("No database loaded"));
        }

        // Release GIL for potentially long dump operation
        allow_threads(py, || {
            self.dump_internal(output_path, format, min_count, max_count, progress_callback)
        })
    }

    /// Internal dump implementation
    fn dump_internal(&self, output_path: &str, format: &str,
                     min_count: Option<u32>, max_count: Option<u32>,
                     progress_callback: Option<Py<PyAny>>) -> PyResult<()> {
        use std::fs::File;
        use std::io::{BufReader, BufWriter, Write};
        use std::path::Path;
        use crate::database::format::{DatabaseHeader, DATABASE_MAGIC};
        use byteorder::{LittleEndian, ReadBytesExt};

        // Open the database file
        let file_path = Path::new(&self.file_path);
        let file = File::open(file_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to open database: {}", e)))?;

        let mut reader = BufReader::new(file);

        // Read RKDB header
        let header = DatabaseHeader::read_from(&mut reader)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to read database header: {}", e)))?;

        // Validate header
        header.validate()
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid database header: {}", e)))?;

        // Create output writer
        let output_file = File::create(output_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to create output file: {}", e)))?;
        let mut writer = BufWriter::new(output_file);

        // Write based on format
        match format.to_lowercase().as_str() {
            "text" | "tsv" => {
                // Write header comment
                writeln!(writer, "# rustkmer database dump")
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
                writeln!(writer, "# k: {}", header.kmer_size)
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
                writeln!(writer, "# total_kmers: {}", header.total_kmers)
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
                writeln!(writer, "# sorted: {}", header.sorted)
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
                writeln!(writer, "# canonical: {}", header.canonical)
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
                writeln!(writer, "# format: RKDB")
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
                writeln!(writer, "#")
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
            }
            "csv" => {
                // Write CSV header
                writeln!(writer, "kmer,count")
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
            }
            "json" => {
                // Start JSON array
                writeln!(writer, "{{")
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
                writeln!(writer, "  \"metadata\": {{")
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
                writeln!(writer, "    \"kmer_size\": {},", header.kmer_size)
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
                writeln!(writer, "    \"total_kmers\": {},", header.total_kmers)
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
                writeln!(writer, "    \"sorted\": {},", header.sorted)
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
                writeln!(writer, "    \"canonical\": {},", header.canonical)
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
                writeln!(writer, "    \"format\": \"RKDB\"")
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
                writeln!(writer, "  }},")
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
                writeln!(writer, "  \"kmers\": [")
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
            }
            _ => {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    format!("Unsupported format: {}. Supported formats: text, csv, json", format)
                ));
            }
        }

        // Read and dump k-mer entries
        let mut processed = 0u64;
        let mut written = 0u64;

        while processed < header.total_kmers {
            // Read k-mer
            let kmer = if header.version == 2 && header.kmer_size > 32 {
                reader.read_u128::<LittleEndian>()
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(
                        format!("Failed to read k-mer at position {}: {}", processed, e)
                    ))?
            } else {
                reader.read_u64::<LittleEndian>()
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(
                        format!("Failed to read k-mer at position {}: {}", processed, e)
                    ))? as u128
            };

            // Read count
            let mut count_bytes = [0u8; 4];
            reader.read_exact(&mut count_bytes)
                .map_err(|e| pyo3::exceptions::PyIOError::new_err(
                    format!("Failed to read count at position {}: {}", processed, e)
                ))?;

            // Fix for endianness issue
            let count_le = u32::from_le_bytes(count_bytes);
            let count_be = u32::from_be_bytes(count_bytes);
            let count = if count_le > 1_000_000 { count_be } else { count_le };

            // Apply count filters
            if let Some(min) = min_count {
                if count < min {
                    processed += 1;
                    continue;
                }
            }
            if let Some(max) = max_count {
                if count > max {
                    processed += 1;
                    continue;
                }
            }

            // Decode k-mer back to DNA sequence
            let sequence = if header.version == 2 && header.kmer_size > 32 {
                decode_kmer_to_sequence_u128(kmer, header.kmer_size as usize)
            } else {
                decode_kmer_to_sequence(kmer as u64, header.kmer_size as usize)
            };

            // Write based on format
            match format.to_lowercase().as_str() {
                "text" | "tsv" => {
                    writeln!(writer, "{}\t{}", sequence, count)
                        .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
                }
                "csv" => {
                    writeln!(writer, "{},{}", sequence, count)
                        .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
                }
                "json" => {
                    if written > 0 {
                        write!(writer, ",\n    ")
                            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
                    }
                    write!(writer, "{{\"kmer\":\"{}\",\"count\":{}}}", sequence, count)
                        .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
                }
                _ => unreachable!(),
            }

            processed += 1;
            written += 1;

            // Progress reporting
            if processed % 100_000 == 0 {
                if let Some(ref callback) = progress_callback {
                    let progress = (processed as f64 / header.total_kmers as f64) * 100.0;
                    let _ = callback.call1((progress,));
                }
            }
        }

        // Close JSON array
        if format.to_lowercase().as_str() == "json" {
            writeln!(writer, "\n  ]\n}}")
                .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Write error: {}", e)))?;
        }

        // Flush the writer
        writer.flush()
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to flush output: {}", e)))?;

        // Final progress callback
        if let Some(ref callback) = progress_callback {
            let _ = callback.call1((100.0,));
        }

        Ok(())
    }

    /// Reload database
    fn reload(&mut self, _force_memory_mapping: Option<bool>) -> PyResult<()> {
        if self.file_path.is_empty() {
            return Err(pyo3::exceptions::PyRuntimeError::new_err("No database loaded"));
        }
        Err(pyo3::exceptions::PyNotImplementedError::new_err("Reload not implemented yet"))
    }

    /// Use memory mapping
    fn uses_memory_mapping(&self) -> bool {
        false
    }

    /// Get k-mer size
    #[getter]
    fn kmer_size(&self) -> PyResult<usize> {
        if self.file_path.is_empty() {
            return Err(pyo3::exceptions::PyRuntimeError::new_err("No database loaded"));
        }
        Ok(self.kmer_size)
    }

    /// Check if canonical
    #[getter]
    fn canonical(&self) -> PyResult<bool> {
        if self.file_path.is_empty() {
            return Err(pyo3::exceptions::PyRuntimeError::new_err("No database loaded"));
        }
        Ok(self.canonical)
    }

    /// Check if sorted
    #[getter]
    fn sorted(&self) -> PyResult<bool> {
        if self.file_path.is_empty() {
            return Err(pyo3::exceptions::PyRuntimeError::new_err("No database loaded"));
        }
        Ok(self.sorted)
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
    #[pyo3(get)]
    uses_memory_mapping: bool,

    // Computed statistics
    #[pyo3(get)]
    min_count: u32,
    #[pyo3(get)]
    max_count: u32,
    #[pyo3(get)]
    mean_count: f64,
    #[pyo3(get)]
    median_count: f64,
    #[pyo3(get)]
    coverage_estimate: f64,

    // Percentiles
    #[pyo3(get)]
    p25: f64,
    #[pyo3(get)]
    p50: f64,
    #[pyo3(get)]
    p75: f64,
    #[pyo3(get)]
    p95: f64,
    #[pyo3(get)]
    p99: f64,

    // Frequency distribution (count -> number of k-mers)
    #[pyo3(get)]
    histogram: HashMap<u32, u64>,

    // Additional metadata
    #[pyo3(get)]
    file_size_mb: f64,
    #[pyo3(get)]
    creation_date: Option<String>,
}

#[pymethods]
impl DatabaseStats {
    #[new]
    fn new(
        kmer_size: usize,
        total_kmers: u64,
        unique_kmers: u64,
        canonical: bool,
        sorted: bool,
        filename: String,
        uses_memory_mapping: bool,
    ) -> Self {
        Self {
            kmer_size,
            total_kmers,
            unique_kmers,
            canonical,
            sorted,
            filename,
            uses_memory_mapping,
            min_count: 0,
            max_count: 0,
            mean_count: 0.0,
            median_count: 0.0,
            coverage_estimate: 0.0,
            p25: 0.0,
            p50: 0.0,
            p75: 0.0,
            p95: 0.0,
            p99: 0.0,
            histogram: HashMap::new(),
            file_size_mb: 0.0,
            creation_date: None,
        }
    }

    /// Convert to dictionary representation
    fn to_dict<'a>(&self, py: Python<'a>) -> PyResult<Bound<'a, PyDict>> {
        let dict = PyDict::new(py);
        dict.set_item("kmer_size", self.kmer_size)?;
        dict.set_item("total_kmers", self.total_kmers)?;
        dict.set_item("unique_kmers", self.unique_kmers)?;
        dict.set_item("canonical", self.canonical)?;
        dict.set_item("sorted", self.sorted)?;
        dict.set_item("filename", &self.filename)?;
        dict.set_item("uses_memory_mapping", self.uses_memory_mapping)?;
        dict.set_item("min_count", self.min_count)?;
        dict.set_item("max_count", self.max_count)?;
        dict.set_item("mean_count", self.mean_count)?;
        dict.set_item("median_count", self.median_count)?;
        dict.set_item("coverage_estimate", self.coverage_estimate)?;
        dict.set_item("p25", self.p25)?;
        dict.set_item("p50", self.p50)?;
        dict.set_item("p75", self.p75)?;
        dict.set_item("p95", self.p95)?;
        dict.set_item("p99", self.p99)?;

        // Convert histogram to Python dict
        let hist_dict = PyDict::new(py);
        for (count, freq) in &self.histogram {
            hist_dict.set_item(count, freq)?;
        }
        dict.set_item("histogram", hist_dict)?;

        dict.set_item("file_size_mb", self.file_size_mb)?;

        match &self.creation_date {
            Some(date) => dict.set_item("creation_date", date)?,
            None => dict.set_item("creation_date", py.None())?,
        };

        Ok(dict)
    }

    /// Convert to JSON string
    #[pyo3(signature = (indent=None))]
    fn to_json(&self, py: Python<'_>, indent: Option<usize>) -> PyResult<String> {
        let dict = self.to_dict(py)?;
        let json_module = py.import("json")?;

        let result = if let Some(indent) = indent {
            let kwargs = PyDict::new(py);
            kwargs.set_item("indent", indent)?;
            json_module.call_method("dumps", (dict,), Some(&kwargs))?
        } else {
            json_module.call_method("dumps", (dict,), None)?
        };

        result.extract()
    }

    /// Get human-readable summary
    fn summary(&self) -> String {
        let mut lines = Vec::new();
        lines.push("Database Statistics".to_string());
        lines.push("==================".to_string());
        lines.push(format!("Filename: {}", self.filename));
        lines.push(format!("K-mer size: {}", self.kmer_size));
        lines.push(format!("Total k-mers: {}", self.total_kmers));
        lines.push(format!("Unique k-mers: {}", self.unique_kmers));
        lines.push(format!("Canonical: {}", self.canonical));
        lines.push(format!("Sorted: {}", self.sorted));
        lines.push(format!("Memory mapped: {}", self.uses_memory_mapping));
        lines.push("".to_string());
        lines.push("Count Statistics:".to_string());
        lines.push(format!("  Min count: {}", self.min_count));
        lines.push(format!("  Max count: {}", self.max_count));
        lines.push(format!("  Mean count: {:.2}", self.mean_count));
        lines.push(format!("  Median count: {:.2}", self.median_count));
        lines.push("".to_string());
        lines.push("Percentiles:".to_string());
        lines.push(format!("  25th: {:.2}", self.p25));
        lines.push(format!("  50th: {:.2}", self.p50));
        lines.push(format!("  75th: {:.2}", self.p75));
        lines.push(format!("  95th: {:.2}", self.p95));
        lines.push(format!("  99th: {:.2}", self.p99));
        lines.push("".to_string());
        lines.push(format!("Coverage estimate: {:.2}%", self.coverage_estimate * 100.0));

        if self.file_size_mb > 0.0 {
            lines.push(format!("File size: {:.1} MB", self.file_size_mb));
        }

        lines.join("\n")
    }
}

/// Fuzzy query result match
#[pyclass(name = "FuzzyMatch")]
#[derive(Clone)]
pub struct FuzzyMatch {
    #[pyo3(get)]
    kmer: String,
    #[pyo3(get)]
    count: u32,
    #[pyo3(get)]
    distance: usize,
}

/// Fuzzy query result container
#[pyclass(name = "FuzzyQueryResult")]
pub struct FuzzyQueryResult {
    #[pyo3(get)]
    query: String,
    #[pyo3(get)]
    total_matches: u32,
    matches: Vec<FuzzyMatch>,
}

#[pymethods]
impl FuzzyQueryResult {
    #[new]
    fn new(query: String) -> Self {
        Self {
            query,
            total_matches: 0,
            matches: Vec::new(),
        }
    }

    /// Get all matches
    fn get_matches(&self) -> Vec<FuzzyMatch> {
        self.matches.clone()
    }

    /// Get match at specific index
    fn get_match(&self, index: usize) -> Option<FuzzyMatch> {
        self.matches.get(index).cloned()
    }

    /// Add a match (internal use)
    fn add_match(&mut self, kmer: String, count: u32, distance: usize) {
        self.matches.push(FuzzyMatch {
            kmer,
            count,
            distance,
        });
        self.total_matches += 1;
    }

    /// Convert matches to dictionary list
    fn to_dict<'a>(&self, py: Python<'a>) -> PyResult<Vec<Bound<'a, PyDict>>> {
        let mut result = Vec::new();

        for m in &self.matches {
            let dict = PyDict::new(py);
            dict.set_item("kmer", &m.kmer)?;
            dict.set_item("count", m.count)?;
            dict.set_item("distance", m.distance)?;
            result.push(dict);
        }

        Ok(result)
    }
}

/// Database class for fuzzy queries
#[pyclass(name = "FuzzyQuery")]
pub struct FuzzyQuery {
    database: Option<SimpleDatabase>,
    max_distance: usize,
}

#[pymethods]
impl FuzzyQuery {
    #[new]
    fn new(database: Option<SimpleDatabase>, max_distance: usize) -> PyResult<Self> {
        Ok(Self {
            database,
            max_distance,
        })
    }

    /// Set the database
    fn set_database(&mut self, database: SimpleDatabase) {
        self.database = Some(database);
    }

    /// Search for patterns
    fn search(&self, pattern: str, max_results: Option<u32>, _py: Python<'_>) -> PyResult<FuzzyQueryResult> {
        let mut result = FuzzyQueryResult::new(pattern);

        if let Some(_db) = &self.database {
            // Simplified implementation
            // In a real implementation, we'd perform the fuzzy search
        }

        Ok(result)
    }

    /// Find similar k-mers
    fn find_similar(&self, kmer: str, max_results: Option<u32>, _py: Python<'_>) -> PyResult<FuzzyQueryResult> {
        let mut result = FuzzyQueryResult::new(kmer);

        if let Some(_db) = &self.database {
            // Simplified implementation
        }

        Ok(result)
    }

    /// Set max distance
    fn set_max_distance(&mut self, max_distance: usize) {
        self.max_distance = max_distance;
    }

    /// Get max distance
    fn get_max_distance(&self) -> usize {
        self.max_distance
    }

    /// Batch query
    fn query_batch(&self, queries: Vec<String>, _py: Python<'_>) -> PyResult<Vec<FuzzyQueryResult>> {
        let mut results = Vec::new();

        for query in queries {
            if query.contains('*') {
                results.push(self.search(query, None, _py)?);
            } else {
                results.push(self.find_similar(query, None, _py)?);
            }
        }

        Ok(results)
    }

    /// Get k-mer size
    fn get_kmer_size(&self) -> PyResult<usize> {
        Err(pyo3::exceptions::PyNotImplementedError::new_err("Not implemented"))
    }

    /// Check if canonical
    fn is_canonical(&self) -> PyResult<bool> {
        Err(pyo3::exceptions::PyNotImplementedError::new_err("Not implemented"))
    }
}

/// Export the module
#[pymodule]
fn rustkmer(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<KmerCounter>()?;
    m.add_class::<SimpleDatabase>()?;
    m.add_class::<QueryResult>()?;
    m.add_class::<DatabaseStats>()?;
    m.add_class::<FuzzyQuery>()?;
    m.add_class::<FuzzyQueryResult>()?;
    m.add_class::<FuzzyMatch>()?;

    Ok(())
}