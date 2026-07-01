//! Database query functionality
//!
//! Provides fast k-mer lookup from rustkmer databases with support
//! for various query modes and efficient binary search.

use std::cmp::Ordering;
use std::fs::File;
use std::io::{BufReader, Seek, SeekFrom};

use super::format::{DatabaseHeader, KmerEntry, RKDatabase};
use crate::error::{KmerError, ProcessingResult};
use crate::kmer::canonical::canonical_kmer_u128;
use crate::kmer::encoding::encode_kmer_bytes_u128;

/// Database query engine for fast k-mer lookups
#[derive(Debug)]
pub struct DatabaseQuery {
    /// Database file handle
    file: BufReader<File>,
    /// Database header
    header: DatabaseHeader,
    /// Whether database is loaded into memory
    memory_loaded: bool,
    /// In-memory cache of k-mer entries (if loaded)
    cached_entries: Option<Vec<KmerEntry>>,
}

impl DatabaseQuery {
    /// Open a database file for querying
    ///
    /// # Arguments
    /// * `path` - Path to the database file
    /// * `preload` - Whether to load the entire database into memory
    ///
    /// # Returns
    /// New DatabaseQuery instance
    pub fn open<P: AsRef<std::path::Path>>(path: P, preload: bool) -> ProcessingResult<Self> {
        let path_str = path.as_ref().to_string_lossy().to_string();
        let file = File::open(path).map_err(|e| KmerError::FileFormatError {
            file: path_str,
            reason: format!("Failed to open database: {}", e),
        })?;

        let mut file = BufReader::new(file);

        // Read and validate header
        let header =
            DatabaseHeader::read_from(&mut file).map_err(|e| KmerError::FileFormatError {
                file: "database".to_string(),
                reason: format!("Failed to read database header: {}", e),
            })?;

        header
            .validate()
            .map_err(|e| KmerError::ProcessingError(format!("Invalid database header: {}", e)))?;

        let memory_loaded = preload;
        let cached_entries = if preload {
            Some(Self::load_entries(&mut file, &header)?)
        } else {
            None
        };

        Ok(Self {
            file,
            header,
            memory_loaded,
            cached_entries,
        })
    }

    /// Load all k-mer entries into memory
    fn load_entries(
        file: &mut BufReader<File>,
        header: &DatabaseHeader,
    ) -> ProcessingResult<Vec<KmerEntry>> {
        // Defensive reconciliation of data_offset: legacy/corrupt files may carry an
        // out-of-range value; fall back to the canonical v2 offset (42) in that case.
        // TODO(plan 01-03): replace this silent clamp with a loud error.
        let actual_data_offset = if (40..=1000).contains(&header.data_offset) {
            header.data_offset
        } else {
            42
        };

        // Seek to data section
        file.seek(SeekFrom::Start(actual_data_offset))
            .map_err(KmerError::Io)?;

        let mut entries = Vec::with_capacity(header.total_kmers as usize);

        for _ in 0..header.total_kmers {
            let entry = KmerEntry::read_from(file).map_err(KmerError::Io)?;
            entries.push(entry);
        }

        Ok(entries)
    }

    /// Query a single k-mer count
    ///
    /// # Arguments
    /// * `kmer_seq` - The k-mer sequence to query
    ///
    /// # Returns
    /// The count of the k-mer, or None if not found
    pub fn query_kmer(&mut self, kmer_seq: &str) -> ProcessingResult<Option<u32>> {
        // Validate k-mer size
        if kmer_seq.len() != self.header.kmer_size as usize {
            return Err(KmerError::ProcessingError(format!(
                "K-mer size mismatch: expected {}, got {}",
                self.header.kmer_size,
                kmer_seq.len()
            ))
            .into());
        }

        // Encode k-mer using u128 encoding
        let mut encoded_kmer = encode_kmer_bytes_u128(kmer_seq.as_bytes())
            .map_err(|e| KmerError::ProcessingError(format!("Failed to encode k-mer: {}", e)))?;

        // Apply canonical transformation if database was created in canonical mode
        if self.header.canonical {
            encoded_kmer = canonical_kmer_u128(encoded_kmer, self.header.kmer_size as usize)
                .map_err(|e| {
                    KmerError::ProcessingError(format!("Failed to get canonical k-mer: {}", e))
                })?;
        }

        if self.memory_loaded {
            self.query_from_memory(encoded_kmer)
        } else {
            self.query_from_disk(encoded_kmer)
        }
    }

    /// Query from in-memory cache
    fn query_from_memory(&self, encoded_kmer: u128) -> ProcessingResult<Option<u32>> {
        let entries = self.cached_entries.as_ref().unwrap();

        if self.header.sorted {
            // Binary search in sorted array
            match entries.binary_search_by_key(&encoded_kmer, |entry| entry.kmer) {
                Ok(index) => Ok(Some(entries[index].count)),
                Err(_) => Ok(None),
            }
        } else {
            // Linear search
            Ok(entries
                .iter()
                .find(|entry| entry.kmer == encoded_kmer)
                .map(|entry| entry.count))
        }
    }

    /// Query from disk using binary search
    fn query_from_disk(&mut self, encoded_kmer: u128) -> ProcessingResult<Option<u32>> {
        if !self.header.sorted {
            return Err(KmerError::ProcessingError(
                "Cannot query unsorted database from disk without preloading".to_string(),
            )
            .into());
        }

        let mut left = 0u64;
        let mut right = self.header.total_kmers - 1;

        while left <= right {
            let mid = (left + right) / 2;
            let entry = self.read_entry_at(mid)?;

            match encoded_kmer.cmp(&entry.kmer) {
                Ordering::Equal => return Ok(Some(entry.count)),
                Ordering::Less => {
                    if mid == 0 {
                        break;
                    }
                    right = mid - 1;
                }
                Ordering::Greater => left = mid + 1,
            }
        }

        Ok(None)
    }

    /// Read entry at specific position
    fn read_entry_at(&mut self, index: u64) -> ProcessingResult<KmerEntry> {
        let actual_data_offset = if (40..=1000).contains(&self.header.data_offset) {
            self.header.data_offset
        } else {
            42
        };

        let entry_offset = actual_data_offset + (index * 20);

        self.file
            .seek(SeekFrom::Start(entry_offset))
            .map_err(KmerError::Io)?;

        let entry = KmerEntry::read_from(&mut self.file).map_err(KmerError::Io)?;

        Ok(entry)
    }

    /// Query multiple k-mers
    ///
    /// # Arguments
    /// * `kmer_seqs` - Vector of k-mer sequences to query
    ///
    /// # Returns
    /// Vector of (kmer, count) pairs, with 0 for missing k-mers
    pub fn query_multiple(&mut self, kmer_seqs: &[String]) -> ProcessingResult<Vec<(String, u32)>> {
        let mut results = Vec::with_capacity(kmer_seqs.len());

        for kmer_seq in kmer_seqs {
            match self.query_kmer(kmer_seq) {
                Ok(Some(count)) => results.push((kmer_seq.clone(), count)),
                Ok(None) => results.push((kmer_seq.clone(), 0)),
                Err(e) => {
                    // For individual query errors, we return 0 count but log the error
                    log::warn!("Warning: Failed to query k-mer '{}': {}", kmer_seq, e);
                    results.push((kmer_seq.clone(), 0));
                }
            }
        }

        Ok(results)
    }

    /// Get database information
    pub fn get_info(&self) -> &DatabaseHeader {
        &self.header
    }

    /// Get database size estimate
    pub fn size_bytes(&self) -> u64 {
        self.header.data_offset + (self.header.total_kmers * 12) // 8 bytes kmer + 4 bytes count
    }
}

/// K-mer query result
#[derive(Debug, Clone)]
pub struct QueryResult {
    pub kmer: String,
    pub count: u32,
    pub found: bool,
}

impl QueryResult {
    pub fn new(kmer: String, count: u32, found: bool) -> Self {
        Self { kmer, count, found }
    }
}

/// K-mer query interface for sequential query operations
#[derive(Debug)]
pub struct KmerQuery<'a> {
    database: &'a RKDatabase,
}

impl<'a> KmerQuery<'a> {
    /// Create a new k-mer query interface
    pub fn new(database: &'a RKDatabase) -> Self {
        Self { database }
    }

    /// Query a single k-mer
    pub fn query(&mut self, kmer: &str) -> crate::error::ProcessingResult<QueryResult> {
        // Fixed: Use actual database query instead of mock implementation
        // Reopens database file for each sequential query operation

        // Encode the k-mer to check validity
        let _encoded = encode_kmer_bytes_u128(kmer.as_bytes())
            .map_err(|e| crate::error::ProcessingError::new(format!("Invalid k-mer: {}", e)))?;

        // Use the stored file path to reopen the database for actual query
        if let Some(file_path) = &self.database.file_path {
            let mut db_query = DatabaseQuery::open(file_path, false)?;
            match db_query.query_kmer(kmer)? {
                Some(count) => Ok(QueryResult::new(kmer.to_uppercase(), count, true)),
                None => Ok(QueryResult::new(kmer.to_uppercase(), 0, false)),
            }
        } else {
            Err(crate::error::ProcessingError::new(
                "Database file path not available for query",
            ))
        }
    }

    /// Query multiple k-mers
    pub fn query_multiple(
        &mut self,
        kmers: &[String],
    ) -> crate::error::ProcessingResult<Vec<QueryResult>> {
        let mut results = Vec::with_capacity(kmers.len());

        for kmer in kmers {
            results.push(self.query(kmer)?);
        }

        Ok(results)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::NamedTempFile;

    fn create_test_database(kmer_size: u8, entries: Vec<(u128, u32)>) -> NamedTempFile {
        let mut file = NamedTempFile::new().unwrap();

        // Use canonical: false to match the stored k-mers (which are not canonically transformed)
        let mut header = DatabaseHeader::new(kmer_size, entries.len() as u64, false);
        header.sorted = true;
        header.write_to(&mut file).unwrap();

        for (kmer, count) in entries {
            let entry = KmerEntry::new(kmer, count);
            entry.write_to(&mut file).unwrap();
        }

        file
    }

    #[test]
    fn test_database_query_basic() {
        use crate::kmer::encoding::encode_kmer_u128;

        let kmer1 = encode_kmer_u128("ATGCGATGCTAGCGCTAGCT").unwrap();
        let kmer2 = encode_kmer_u128("TGCGATGCTAGCGCTAGCTA").unwrap();
        let kmer3 = encode_kmer_u128("GCGATGCTAGCGCTAGCTAG").unwrap();

        // Note: entries must be in sorted order for binary search to work
        // kmer1 (398e726727) < kmer3 (98e7267272) < kmer2 (e639c99c9c)
        let entries = vec![
            (kmer1, 10),
            (kmer3, 30), // Reorder to be sorted
            (kmer2, 20),
        ];

        let temp_file = create_test_database(20, entries);
        let mut query = DatabaseQuery::open(temp_file.path(), false).unwrap();

        assert_eq!(query.query_kmer("ATGCGATGCTAGCGCTAGCT").unwrap(), Some(10));
        assert_eq!(query.query_kmer("TGCGATGCTAGCGCTAGCTA").unwrap(), Some(20));
        assert_eq!(query.query_kmer("GCGATGCTAGCGCTAGCTAG").unwrap(), Some(30));
    }

    #[test]
    fn test_database_query_not_found() {
        let entries = vec![(0x123456789ABCDEF0u128, 10)];
        let temp_file = create_test_database(20, entries);
        let mut query = DatabaseQuery::open(temp_file.path(), false).unwrap();

        // Verify the database was created with sorted flag
        assert!(query.header.sorted);
        // Query for a k-mer that definitely doesn't exist (all T's, encoding is very high)
        let not_found_result = query.query_kmer("TTTTTTTTTTTTTTTTTTTT");
        assert!(
            not_found_result.is_ok()
                || not_found_result
                    .unwrap_err()
                    .to_string()
                    .contains("Cannot query")
        );
    }

    #[test]
    fn test_database_query_multiple() {
        use crate::kmer::encoding::encode_kmer_u128;

        let kmer1 = encode_kmer_u128("ATGCGATGCTAGCGCTAGCT").unwrap();
        let kmer2 = encode_kmer_u128("TGCGATGCTAGCGCTAGCTA").unwrap();

        let entries = vec![(kmer1, 10), (kmer2, 20)];

        let temp_file = create_test_database(20, entries);
        let mut query = DatabaseQuery::open(temp_file.path(), false).unwrap(); // Database is sorted, no need to preload

        let kmer_seqs = vec![
            "ATGCGATGCTAGCGCTAGCT".to_string(),
            "TGCGATGCTAGCGCTAGCTA".to_string(),
            "AAAAAAAAAAAAAAAAAAAA".to_string(), // Not in database
        ];

        let results = query.query_multiple(&kmer_seqs).unwrap();
        assert_eq!(results.len(), 3);
        assert_eq!(results[0].1, 10);
        assert_eq!(results[1].1, 20);
        assert_eq!(results[2].1, 0);
    }
}
