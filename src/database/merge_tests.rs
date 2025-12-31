//! Memory usage tests for merge operations

#[cfg(test)]
mod tests {
    use super::super::memory::MemoryMonitor;
    use super::super::memory::constraints;
    use super::*;
    use std::path::PathBuf;
    use tempfile::tempdir;

    /// Test that merge doesn't use excessive memory
    #[test]
    fn test_merge_memory_basic() {
        // Create test databases
        let db1 = RKDatabase::from_kmer_pairs(
            vec![(0x1234, 10), (0x5678, 20), (0x9ABC, 30)],
            31,
            false,
            true
        ).unwrap();

        let db2 = RKDatabase::from_kmer_pairs(
            vec![(0x1234, 5), (0xDEF0, 15), (0x9ABC, 25)],
            31,
            false,
            true
        ).unwrap();

        // Create temporary files
        let temp_dir = tempdir().unwrap();
        let db1_path = temp_dir.path().join("db1.rkdb");
        let db2_path = temp_dir.path().join("db2.rkdb");

        // Save databases
        db1.to_file_path(&db1_path).unwrap();
        db2.to_file_path(&db2_path).unwrap();

        // Monitor memory usage
        let mut monitor = MemoryMonitor::new();

        // Configure merge with memory constraints
        let config = MergeConfig {
            max_memory_usage: constraints::SMALL.max_usage,
            chunk_size: 100,
            temp_dir: temp_dir.path().to_path_buf(),
            use_streaming: false,
            use_prefix_cache: false,
            verbose: false,
        };

        // Perform merge
        let merged_db = RKDatabase::merge_databases(&[db1_path, db2_path], &config)
            .expect("Merge should succeed");

        // Record final memory usage
        monitor.record_reading();

        // Validate merge results
        let all_kmers = merged_db.all_kmers().expect("Failed to get merged k-mers");
        assert!(!all_kmers.is_empty(), "Merged database should have k-mers");

        // Check specific k-mers were merged correctly
        let kmer_map: std::collections::HashMap<_, _> = all_kmers.into_iter().collect();
        assert_eq!(kmer_map.get(&0x1234), Some(&15)); // 10 + 5
        assert_eq!(kmer_map.get(&0x5678), Some(&20));
        assert_eq!(kmer_map.get(&0x9ABC), Some(&55)); // 30 + 25
        assert_eq!(kmer_map.get(&0xDEF0), Some(&15));

        println!("Memory usage: {} bytes", monitor.peak_usage());
        println!("Memory increase: {} bytes", monitor.increase());

        // Basic memory sanity check
        assert!(monitor.peak_usage() < constraints::SMALL.max_usage,
               "Memory usage should be within small constraint");
    }
}