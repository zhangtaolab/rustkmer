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
use std::io::{BufRead, BufReader};
use std::path::Path;
use memmap2::{Mmap, MmapOptions};

// Include the core database functionality directly
use crate::database::query::DatabaseQuery;
use crate::database::format::{DatabaseHeader, KmerEntry};
use crate::kmer::{encode_kmer, canonical_kmer};

/// Threshold for using memory mapping (100MB)
const MMAP_THRESHOLD: u64 = 100 * 1024 * 1024; // 100MB in bytes

/// Memory mapping wrapper for large database files
#[derive(Debug)]
struct MemoryMappedDatabase {
    /// Memory-mapped file (wrapped in Arc for thread safety)
    mmap: Arc<Mmap>,
    /// Database header
    header: DatabaseHeader,
    /// File path for reference
    file_path: String,
}

// Implement Send + Sync for thread safety
unsafe impl Send for MemoryMappedDatabase {}
unsafe impl Sync for MemoryMappedDatabase {}

impl MemoryMappedDatabase {
    /// Create a new memory-mapped database
    fn new(file_path: &str) -> Result<Self, pyo3::PyErr> {
        let file = File::open(file_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to open file: {}", e)))?;

        // Use memmap2 for memory mapping
        let mmap = unsafe {
            MmapOptions::new()
                .map(&file)
                .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to memory map file: {}", e)))?
        };

        // Read header from the memory-mapped data
        let header = Self::read_header_from_mmap(&mmap)?;

        Ok(Self {
            mmap: Arc::new(mmap),
            header,
            file_path: file_path.to_string(),
        })
    }

    /// Read database header from memory-mapped data
    fn read_header_from_mmap(mmap: &Mmap) -> Result<DatabaseHeader, pyo3::PyErr> {
        if mmap.len() < 42 {
            return Err(pyo3::exceptions::PyIOError::new_err("File too small for database header"));
        }

        let mut cursor = std::io::Cursor::new(&mmap[..42]); // Only read header portion
        DatabaseHeader::read_from(&mut cursor)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to read database header: {}", e)))
    }

    /// Query a k-mer using binary search on memory-mapped data
    fn query_kmer(&self, kmer_seq: &str) -> Result<Option<u32>, pyo3::PyErr> {
        // Validate k-mer size
        if kmer_seq.len() != self.header.kmer_size as usize {
            return Err(pyo3::exceptions::PyValueError::new_err(
                format!("K-mer size mismatch: expected {}, got {}",
                    self.header.kmer_size, kmer_seq.len())
            ));
        }

        if !self.header.sorted {
            return Err(pyo3::exceptions::PyNotImplementedError::new_err(
                "Memory mapping only supports sorted databases"
            ));
        }

        // Encode k-mer
        let mut encoded_kmer = encode_kmer(kmer_seq)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Failed to encode k-mer: {}", e)))?;

        // Apply canonical transformation if needed
        if self.header.canonical {
            encoded_kmer = canonical_kmer(encoded_kmer, self.header.kmer_size as usize)
                .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Failed to get canonical k-mer: {}", e)))?;
        }

        // Fix for incorrect data_offset in header
        let actual_data_offset = if self.header.data_offset < 40 {
            42
        } else if self.header.data_offset > 1000 {
            42
        } else {
            self.header.data_offset
        };

        // Binary search in memory-mapped data
        let mut left = 0u64;
        let mut right = self.header.total_kmers.saturating_sub(1);

        while left <= right {
            let mid = (left + right) / 2;
            let entry_offset = actual_data_offset + (mid * 12); // 8 + 4 bytes per entry

            if entry_offset as usize + 12 > self.mmap.len() {
                return Err(pyo3::exceptions::PyIOError::new_err("Invalid entry offset in database"));
            }

            // Read k-mer entry from memory-mapped data
            let kmer_bytes = &self.mmap[entry_offset as usize..entry_offset as usize + 8];
            let count_bytes = &self.mmap[entry_offset as usize + 8..entry_offset as usize + 12];

            let entry_kmer = u64::from_le_bytes(kmer_bytes.try_into().unwrap());
            let count = u32::from_le_bytes(count_bytes.try_into().unwrap());

            match encoded_kmer.cmp(&entry_kmer) {
                std::cmp::Ordering::Equal => return Ok(Some(count)),
                std::cmp::Ordering::Less => {
                    if mid == 0 { break; }
                    right = mid - 1;
                },
                std::cmp::Ordering::Greater => left = mid + 1,
            }
        }

        Ok(None)
    }

    /// Get database information
    fn get_info(&self) -> &DatabaseHeader {
        &self.header
    }

    /// Check if file is large enough for memory mapping
    fn should_use_mmap(file_path: &str) -> Result<bool, pyo3::PyErr> {
        let metadata = std::fs::metadata(file_path)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to get file metadata: {}", e)))?;

        Ok(metadata.len() > MMAP_THRESHOLD)
    }
}

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

    /// Count k-mers from a FASTA/FASTQ file (supports gzip compression)
    fn count_file(&self, file_path: &str) -> PyResult<HashMap<String, u64>> {
        if !Path::new(file_path).exists() {
            return Err(pyo3::exceptions::PyFileNotFoundError::new_err(format!("File not found: {}", file_path)));
        }

        // Check if file is gzipped and handle accordingly
        let reader: Box<dyn std::io::BufRead> = if file_path.ends_with(".gz") {
            let file = File::open(file_path)
                .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to open file: {}", e)))?;
            let gz_reader = flate2::read::GzDecoder::new(file);
            Box::new(BufReader::new(gz_reader))
        } else {
            let file = File::open(file_path)
                .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to open file: {}", e)))?;
            Box::new(BufReader::new(file))
        };
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

                    let _final_kmer = if self.canonical {
                        match canonical_kmer(encoded_kmer, self.k) {
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

                let _final_kmer = if self.canonical {
                    match canonical_kmer(encoded_kmer, self.k) {
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
        // Validate database file path
        if !database_path.ends_with(".rkdb") {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "Database path must end with .rkdb extension"
            ));
        }

        // Check if parent directory exists
        let path = Path::new(database_path);
        if let Some(parent) = path.parent() {
            if !parent.exists() {
                return Err(pyo3::exceptions::PyFileNotFoundError::new_err(format!(
                    "Parent directory does not exist: {}",
                    parent.display()
                )));
            }
        }

        let counts = self.kmer_counts.read();
        let total_kmers = counts.len() as u64;

        // Validate that we have k-mers to save
        if total_kmers == 0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "No k-mers to save - count file first"
            ));
        }

        // Create database header
        let header = DatabaseHeader {
            magic: *crate::database::format::DATABASE_MAGIC,
            version: crate::database::format::DATABASE_VERSION,
            kmer_size: self.k as u8,
            total_kmers,
            sorted: true, // Always sort for binary search compatibility
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
            .filter_map(|(kmer, count)| {
                match encode_kmer(kmer) {
                    Ok(encoded) => Some(KmerEntry::new(encoded.into(), *count as u32)),
                    Err(_) => None, // Skip invalid k-mers
                }
            })
            .collect();

        entries.sort_by_key(|entry| entry.kmer);

        for entry in entries {
            // Use the KmerEntry's write_to method for consistent format
            entry.write_to(&mut file)
                .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to write k-mer entry: {}", e)))?;
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
    mmap_db: Option<Arc<MemoryMappedDatabase>>,
    kmer_size: usize,
    total_kmers: u64,
    unique_kmers: u64,
    canonical: bool,
    sorted: bool,
    file_path: String,
    uses_mmap: bool,
}

#[pymethods]
impl SimpleDatabase {
    #[new]
    fn new() -> PyResult<Self> {
        Ok(Self {
            query: None,
            mmap_db: None,
            kmer_size: 0,
            total_kmers: 0,
            unique_kmers: 0,
            canonical: false,
            sorted: false,
            file_path: String::new(),
            uses_mmap: false,
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

        // Check if we should use memory mapping
        let use_mmap = MemoryMappedDatabase::should_use_mmap(file_path)?;

        if use_mmap {
            // Use memory mapping for large files
            let mmap_db = Arc::new(MemoryMappedDatabase::new(file_path)?);
            let info = mmap_db.get_info();

            self.kmer_size = info.kmer_size as usize;
            self.total_kmers = info.total_kmers;
            self.unique_kmers = info.unique_kmers;
            self.canonical = info.canonical;
            self.sorted = info.sorted;
            self.file_path = file_path.to_string();
            self.uses_mmap = true;
            self.mmap_db = Some(mmap_db);
            self.query = None;
        } else {
            // Use regular DatabaseQuery for smaller files
            let query = DatabaseQuery::open(&path, false)
                .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to open database: {}", e)))?;

            // Extract info before moving query
            let info = query.get_info();
            self.kmer_size = info.kmer_size as usize;
            self.total_kmers = info.total_kmers;
            self.unique_kmers = info.unique_kmers;
            self.canonical = info.canonical;
            self.sorted = info.sorted;
            self.file_path = file_path.to_string();
            self.uses_mmap = false;
            self.query = Some(query);
            self.mmap_db = None;
        }

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
            uses_memory_mapping: self.uses_mmap,
        })
    }

    /// Query a single k-mer
    fn query(&self, kmer: &str) -> PyResult<QueryResult> {
        let count = if self.uses_mmap {
            // Use memory mapping for queries
            let mmap_db = self.mmap_db.as_ref().ok_or_else(|| {
                pyo3::exceptions::PyRuntimeError::new_err("Memory mapped database not available")
            })?;
            mmap_db.query_kmer(kmer)?
        } else {
            // Since DatabaseQuery::query_kmer needs &mut self, we can't use the cached query
            // Instead, we need to open the database each time for querying
            let path = Path::new(&self.file_path);
            let mut query = DatabaseQuery::open(&path, false)
                .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to open database for query: {}", e)))?;

            query.query_kmer(kmer)
                .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("Query failed: {}", e)))?
        };

        Ok(QueryResult {
            kmer: kmer.to_string(),
            count: count.unwrap_or(0),
            found: count.is_some(),
        })
    }

    /// Query multiple k-mers
    fn query_multiple(&self, kmers: Vec<String>) -> PyResult<Vec<QueryResult>> {
        let mut results = Vec::with_capacity(kmers.len());

        if self.uses_mmap {
            // Use memory mapping for batch queries
            let mmap_db = self.mmap_db.as_ref().ok_or_else(|| {
                pyo3::exceptions::PyRuntimeError::new_err("Memory mapped database not available")
            })?;

            for kmer in kmers {
                let count = mmap_db.query_kmer(&kmer).unwrap_or(None);
                results.push(QueryResult {
                    kmer: kmer.clone(),
                    count: count.unwrap_or(0),
                    found: count.is_some(),
                });
            }
        } else {
            // Use regular DatabaseQuery for batch queries
            let path = Path::new(&self.file_path);
            let mut query = DatabaseQuery::open(&path, false)
                .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to open database for query: {}", e)))?;

            for kmer in kmers {
                let count = query.query_kmer(&kmer).unwrap_or(None);
                results.push(QueryResult {
                    kmer: kmer.clone(),
                    count: count.unwrap_or(0),
                    found: count.is_some(),
                });
            }
        }

        Ok(results)
    }

    /// Check if database is using memory mapping
    fn uses_memory_mapping(&self) -> PyResult<bool> {
        Ok(self.uses_mmap)
    }

    /// Force reload database with or without memory mapping
    #[pyo3(signature = (force_mmap=None))]
    fn reload(&mut self, force_mmap: Option<bool>) -> PyResult<()> {
        if self.file_path.is_empty() {
            return Err(pyo3::exceptions::PyRuntimeError::new_err("No database file loaded"));
        }

        let file_path = self.file_path.clone();

        if let Some(force) = force_mmap {
            if force && !self.uses_mmap {
                // Force enable memory mapping
                let mmap_db = Arc::new(MemoryMappedDatabase::new(&file_path)?);
                let info = mmap_db.get_info();

                self.kmer_size = info.kmer_size as usize;
                self.total_kmers = info.total_kmers;
                self.unique_kmers = info.unique_kmers;
                self.canonical = info.canonical;
                self.sorted = info.sorted;
                self.uses_mmap = true;
                self.mmap_db = Some(mmap_db);
                self.query = None;
            } else if !force && self.uses_mmap {
                // Force disable memory mapping
                let path = Path::new(&file_path);
                let query = DatabaseQuery::open(&path, false)
                    .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to open database: {}", e)))?;

                let info = query.get_info();
                self.kmer_size = info.kmer_size as usize;
                self.total_kmers = info.total_kmers;
                self.unique_kmers = info.unique_kmers;
                self.canonical = info.canonical;
                self.sorted = info.sorted;
                self.uses_mmap = false;
                self.query = Some(query);
                self.mmap_db = None;
            }
        } else {
            // Reload with automatic detection
            self.load(&file_path)?;
        }

        Ok(())
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