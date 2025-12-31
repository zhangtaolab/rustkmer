//! Configuration and statistics for database merge operations

use std::path::PathBuf;
use std::time::Duration;

/// Merge operation configuration
#[derive(Debug, Clone)]
pub struct MergeConfig {
    /// Maximum memory usage in bytes
    pub max_memory_usage: usize,
    /// Processing chunk size for streaming mode
    pub chunk_size: usize,
    /// Temporary directory for operations
    pub temp_dir: PathBuf,
    /// Force streaming mode
    pub use_streaming: bool,
    /// Use prefix cache merge (memory-efficient with error isolation)
    pub use_prefix_cache: bool,
    /// Number of threads for parallel processing (0 = use all cores)
    pub num_threads: usize,
    /// Merge mode for prefix cache: "auto", "memory", "streaming"
    pub merge_mode: String,
    /// Keep intermediate files for debugging
    pub keep_intermediate: bool,
    /// Enable detailed logging
    pub verbose: bool,
}

impl Default for MergeConfig {
    fn default() -> Self {
        Self {
            max_memory_usage: get_default_memory_limit(),
            chunk_size: 50_000_000, // 50M k-mers to drastically reduce temp files
            temp_dir: std::env::temp_dir(),
            use_streaming: false,
            use_prefix_cache: false,
            num_threads: 0,
            merge_mode: "auto".to_string(),
            keep_intermediate: false,
            verbose: false,
        }
    }
}

/// Merge strategy used
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MergeStrategy {
    /// In-memory merge for small datasets
    InMemory,
    /// Streaming merge for large datasets
    Streaming,
    /// Prefix cache merge (memory-efficient with error isolation)
    PrefixCache,
    /// Hybrid approach (start in-memory, fallback to streaming)
    Hybrid,
}

/// Runtime statistics for merge operations
#[derive(Debug, Clone)]
pub struct MergeStats {
    /// Input database paths
    pub input_databases: Vec<String>,
    /// Number of k-mers in each input database
    pub input_kmers: Vec<u64>,
    /// Total k-mers in output database
    pub output_kmers: u64,
    /// Number of unique k-mers in output
    pub unique_kmers: u64,
    /// Time taken for merge operation
    pub merge_time: Duration,
    /// Peak memory usage during merge
    pub peak_memory: usize,
    /// Strategy used for merging
    pub strategy_used: MergeStrategy,
}

impl MergeStats {
    /// Create new merge statistics
    pub fn new() -> Self {
        Self {
            input_databases: Vec::new(),
            input_kmers: Vec::new(),
            output_kmers: 0,
            unique_kmers: 0,
            merge_time: Duration::default(),
            peak_memory: 0,
            strategy_used: MergeStrategy::InMemory,
        }
    }

    /// Add input database info
    pub fn add_input_database(&mut self, path: &str, kmer_count: u64) {
        self.input_databases.push(path.to_string());
        self.input_kmers.push(kmer_count);
    }

    /// Set output statistics
    pub fn set_output_stats(&mut self, total_kmers: u64, unique_kmers: u64) {
        self.output_kmers = total_kmers;
        self.unique_kmers = unique_kmers;
    }

    /// Complete the merge with timing information
    pub fn complete(&mut self, merge_time: Duration, peak_memory: usize, strategy: MergeStrategy) {
        self.merge_time = merge_time;
        self.peak_memory = peak_memory;
        self.strategy_used = strategy;
    }

    /// Get total input k-mers
    pub fn total_input_kmers(&self) -> u64 {
        self.input_kmers.iter().sum()
    }

    /// Get compression ratio (unique / total)
    pub fn compression_ratio(&self) -> f64 {
        if self.output_kmers > 0 {
            self.unique_kmers as f64 / self.output_kmers as f64
        } else {
            1.0
        }
    }

    /// Get throughput in k-mers per second
    pub fn throughput(&self) -> f64 {
        let secs = self.merge_time.as_secs_f64();
        if secs > 0.0 {
            self.total_input_kmers() as f64 / secs
        } else {
            0.0
        }
    }
}

/// Get default memory limit (50% of available memory)
fn get_default_memory_limit() -> usize {
    // Try to get total system memory
    #[cfg(unix)]
    {
        if let Ok(meminfo) = std::fs::read_to_string("/proc/meminfo") {
            for line in meminfo.lines() {
                if line.starts_with("MemTotal:") {
                    if let Some(kb_str) = line.split_whitespace().nth(1) {
                        if let Ok(kb) = kb_str.parse::<usize>() {
                            // Use 50% of total system memory
                            let total_bytes = kb * 1024;
                            return total_bytes / 2;
                        }
                    }
                }
            }
        }
    }

    // Fallback: assume 64GB total, use 32GB for merge (instead of 2GB)
    32 * 1024 * 1024 * 1024 // 32GB default
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_merge_config_default() {
        let config = MergeConfig::default();
        assert!(config.max_memory_usage > 0);
        assert_eq!(config.chunk_size, 50_000_000);
        assert!(!config.use_streaming);
        assert!(!config.use_prefix_cache);
        assert!(!config.verbose);
    }

    #[test]
    fn test_merge_stats() {
        let mut stats = MergeStats::new();

        stats.add_input_database("test1.rkdb", 1000);
        stats.add_input_database("test2.rkdb", 2000);

        assert_eq!(stats.input_databases.len(), 2);
        assert_eq!(stats.total_input_kmers(), 3000);

        stats.set_output_stats(2500, 1500);
        assert_eq!(stats.output_kmers, 2500);
        assert_eq!(stats.unique_kmers, 1500);
        assert_eq!(stats.compression_ratio(), 0.6);

        stats.complete(
            Duration::from_secs(10),
            1024 * 1024 * 100, // 100MB
            MergeStrategy::InMemory
        );

        assert_eq!(stats.merge_time.as_secs(), 10);
        assert_eq!(stats.peak_memory, 1024 * 1024 * 100);
        assert_eq!(stats.throughput(), 300.0);
    }

    #[test]
    fn test_merge_strategy() {
        assert_eq!(MergeStrategy::InMemory, MergeStrategy::InMemory);
        assert_ne!(MergeStrategy::InMemory, MergeStrategy::Streaming);
        assert_ne!(MergeStrategy::Streaming, MergeStrategy::PrefixCache);
        assert_ne!(MergeStrategy::PrefixCache, MergeStrategy::Hybrid);
    }
}