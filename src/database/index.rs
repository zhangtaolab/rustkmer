//! Database indexing utilities
//!
//! Provides functionality for creating and managing indexes for
//! fast k-mer lookup in rustkmer databases.

use std::io::Write;
use std::collections::HashMap;

use crate::error::ProcessingResult;
use super::format::KmerEntry;

/// Index for fast k-mer lookup
#[derive(Debug)]
pub struct DatabaseIndex {
    /// Hash table for O(1) lookup
    hash_table: HashMap<u128, u32>,
    /// Whether index is loaded in memory
    #[allow(dead_code)]
    memory_loaded: bool,
}

impl Default for DatabaseIndex {
    fn default() -> Self {
        Self::new()
    }
}

impl DatabaseIndex {
    /// Create a new empty index
    pub fn new() -> Self {
        Self {
            hash_table: HashMap::new(),
            memory_loaded: false,
        }
    }

    /// Build index from k-mer entries
    pub fn build_from_entries(entries: &[KmerEntry]) -> ProcessingResult<Self> {
        let mut hash_table = HashMap::with_capacity(entries.len());

        for entry in entries {
            hash_table.insert(entry.kmer, entry.count);
        }

        Ok(Self {
            hash_table,
            memory_loaded: true,
        })
    }

    /// Query k-mer count from index
    pub fn query(&self, kmer: u128) -> Option<u32> {
        self.hash_table.get(&kmer).copied()
    }

    /// Get number of entries in index
    pub fn len(&self) -> usize {
        self.hash_table.len()
    }

    /// Check if index is empty
    pub fn is_empty(&self) -> bool {
        self.hash_table.is_empty()
    }

    /// Estimate memory usage in bytes
    pub fn memory_usage_bytes(&self) -> usize {
        // Rough estimate: each entry uses ~24 bytes (HashMap overhead) + 12 bytes for key+value
        self.hash_table.len() * 36
    }
}

/// Utility for sorting k-mer entries
pub struct KmerSorter;

impl KmerSorter {
    /// Sort k-mer entries by packed k-mer value
    pub fn sort_entries(entries: &mut [KmerEntry]) {
        entries.sort_by_key(|entry| entry.kmer);
    }

    /// Check if entries are sorted
    pub fn is_sorted(entries: &[KmerEntry]) -> bool {
        entries.windows(2).all(|w| w[0].kmer <= w[1].kmer)
    }
}

/// Utility for database statistics
pub struct DatabaseStats;

impl DatabaseStats {
    /// Calculate statistics for k-mer entries
    pub fn calculate_stats(entries: &[KmerEntry]) -> DatabaseStatistics {
        if entries.is_empty() {
            return DatabaseStatistics::default();
        }

        let total_kmers: u64 = entries.iter().map(|e| e.count as u64).sum();
        let min_count = entries.iter().map(|e| e.count).min().unwrap();
        let max_count = entries.iter().map(|e| e.count).max().unwrap();
        let avg_count = total_kmers as f64 / entries.len() as f64;

        // Calculate median
        let mut counts: Vec<u32> = entries.iter().map(|e| e.count).collect();
        counts.sort();
        let median_count = if counts.len().is_multiple_of(2) {
            (counts[counts.len() / 2 - 1] + counts[counts.len() / 2]) / 2
        } else {
            counts[counts.len() / 2]
        };

        // Calculate distribution (percentiles)
        let p25 = counts[counts.len() / 4];
        let p75 = counts[counts.len() * 3 / 4];
        let p90 = counts[counts.len() * 9 / 10];
        let p95 = counts[counts.len() * 95 / 100];
        let p99 = counts[counts.len() * 99 / 100];

        DatabaseStatistics {
            unique_kmers: entries.len(),
            total_kmers,
            min_count,
            max_count,
            avg_count,
            median_count,
            p25,
            p75,
            p90,
            p95,
            p99,
        }
    }
}

/// Database statistics
#[derive(Debug, Default)]
pub struct DatabaseStatistics {
    /// Number of unique k-mers
    pub unique_kmers: usize,
    /// Total k-mer count (sum of all counts)
    pub total_kmers: u64,
    /// Minimum k-mer count
    pub min_count: u32,
    /// Maximum k-mer count
    pub max_count: u32,
    /// Average k-mer count
    pub avg_count: f64,
    /// Median k-mer count
    pub median_count: u32,
    /// 25th percentile
    pub p25: u32,
    /// 75th percentile
    pub p75: u32,
    /// 90th percentile
    pub p90: u32,
    /// 95th percentile
    pub p95: u32,
    /// 99th percentile
    pub p99: u32,
}

impl DatabaseStatistics {
    /// Format statistics as a string
    pub fn format(&self) -> String {
        format!(
            "Database Statistics:\n\
             Unique k-mers: {}\n\
             Total k-mers: {}\n\
             Min count: {}\n\
             Max count: {}\n\
             Avg count: {:.2}\n\
             Median count: {}\n\
             25th percentile: {}\n\
             75th percentile: {}\n\
             90th percentile: {}\n\
             95th percentile: {}\n\
             99th percentile: {}",
            self.unique_kmers,
            self.total_kmers,
            self.min_count,
            self.max_count,
            self.avg_count,
            self.median_count,
            self.p25,
            self.p75,
            self.p90,
            self.p95,
            self.p99
        )
    }

    /// Write statistics to a file
    pub fn write_to_file<P: AsRef<std::path::Path>>(&self, path: P) -> ProcessingResult<()> {
        let mut file = std::fs::File::create(path)
            .map_err(|e| crate::error::KmerError::FileWriteError(format!("Failed to create stats file: {}", e)))?;

        file.write_all(self.format().as_bytes())
            .map_err(|e| crate::error::KmerError::FileWriteError(format!("Failed to write stats: {}", e)))?;

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_database_index_build() {
        let entries = vec![
            KmerEntry::new(0x123456789ABCDEF0, 10),
            KmerEntry::new(0x23456789ABCDEF01, 20),
            KmerEntry::new(0x3456789ABCDEF012, 30),
        ];

        let index = DatabaseIndex::build_from_entries(&entries).unwrap();

        assert_eq!(index.query(0x123456789ABCDEF0), Some(10));
        assert_eq!(index.query(0x23456789ABCDEF01), Some(20));
        assert_eq!(index.query(0x3456789ABCDEF012), Some(30));
        assert_eq!(index.query(0x456789ABCDEF0123), None);
    }

    #[test]
    fn test_kmer_sorter() {
        let mut entries = vec![
            KmerEntry::new(0x3000000000000000, 30),
            KmerEntry::new(0x1000000000000000, 10),
            KmerEntry::new(0x2000000000000000, 20),
        ];

        assert!(!KmerSorter::is_sorted(&entries));

        KmerSorter::sort_entries(&mut entries);

        assert!(KmerSorter::is_sorted(&entries));
        assert_eq!(entries[0].kmer, 0x1000000000000000);
        assert_eq!(entries[1].kmer, 0x2000000000000000);
        assert_eq!(entries[2].kmer, 0x3000000000000000);
    }

    #[test]
    fn test_database_stats() {
        let entries = vec![
            KmerEntry::new(0x1000000000000000, 10),
            KmerEntry::new(0x2000000000000000, 20),
            KmerEntry::new(0x3000000000000000, 30),
            KmerEntry::new(0x4000000000000000, 40),
        ];

        let stats = DatabaseStats::calculate_stats(&entries);

        assert_eq!(stats.unique_kmers, 4);
        assert_eq!(stats.total_kmers, 100);
        assert_eq!(stats.min_count, 10);
        assert_eq!(stats.max_count, 40);
        assert_eq!(stats.avg_count, 25.0);
        assert_eq!(stats.median_count, 25);
    }
}