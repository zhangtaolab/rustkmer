//! Performance optimization and metrics for fuzzy queries
//!
//! This module provides performance monitoring, optimization strategies, and
//! resource management for fuzzy query operations.

use crate::fuzzy::{constants, FuzzyError, FuzzyResult};
use serde::{Deserialize, Serialize};
use std::time::{Duration, Instant};

/// Comprehensive performance metrics for fuzzy query operations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PerformanceMetrics {
    /// Variant generation metrics
    pub variant_generation: VariantGenerationMetrics,

    /// Database query metrics
    pub database_queries: DatabaseQueryMetrics,

    /// Memory usage metrics
    pub memory_usage: MemoryUsageMetrics,

    /// Parallel processing metrics
    pub parallel_processing: ParallelProcessingMetrics,
}

/// Metrics for variant generation process
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VariantGenerationMetrics {
    /// Time to generate all variants
    pub total_generation_time_ms: u64,

    /// Number of variants generated
    pub variants_generated: usize,

    /// Generation rate (variants per second)
    pub generation_rate: f64,

    /// Peak memory usage during generation
    pub peak_memory_mb: f64,

    /// Wildcard expansion time
    pub wildcard_expansion_time_ms: u64,

    /// Mutation generation time
    pub mutation_generation_time_ms: u64,

    /// Length normalization time
    pub normalization_time_ms: u64,
}

/// Metrics for database query operations
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseQueryMetrics {
    /// Total number of database queries executed
    pub total_queries: usize,

    /// Average query time per k-mer lookup
    pub avg_query_time_ms: f64,

    /// Number of queries that returned results
    pub successful_queries: usize,

    /// Database hit rate
    pub hit_rate: f64,

    /// Total query time
    pub total_query_time_ms: u64,

    /// Fastest query time
    pub fastest_query_ms: u64,

    /// Slowest query time
    pub slowest_query_ms: u64,
}

/// Memory usage statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryUsageMetrics {
    /// Peak memory usage during entire operation
    pub peak_memory_mb: f64,

    /// Memory used for storing variants
    pub variants_memory_mb: f64,

    /// Memory used for result storage
    pub results_memory_mb: f64,

    /// Memory efficiency score (results / memory)
    pub memory_efficiency: f64,

    /// Memory growth rate
    pub memory_growth_rate_mb_per_sec: f64,
}

/// Parallel processing metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParallelProcessingMetrics {
    /// Number of worker threads used
    pub worker_threads: usize,

    /// Parallel efficiency (speedup vs sequential)
    pub parallel_efficiency: f64,

    /// Load balancing score (0-1, higher is better)
    pub load_balance_score: f64,

    /// Thread contention metrics
    pub thread_contention_ms: u64,

    /// Sequential time estimate
    pub sequential_time_estimate_ms: u64,

    /// Actual parallel time
    pub parallel_time_ms: u64,
}

/// Performance monitor for tracking operations
pub struct PerformanceMonitor {
    start_time: Instant,
    checkpoints: Vec<PerformanceCheckpoint>,
    memory_tracker: MemoryTracker,
    query_tracker: QueryTracker,
}

/// Checkpoint for measuring performance at different stages
#[derive(Debug, Clone)]
struct PerformanceCheckpoint {
    name: String,
    timestamp: Instant,
    #[allow(dead_code)]
    memory_mb: f64,
    #[allow(dead_code)]
    operation_count: usize,
}

/// Memory usage tracker
#[derive(Debug)]
struct MemoryTracker {
    peak_memory_mb: f64,
    current_memory_mb: f64,
    start_memory_mb: f64,
}

/// Database query tracker
#[derive(Debug)]
struct QueryTracker {
    total_queries: usize,
    successful_queries: usize,
    total_time_ms: u64,
    fastest_query_ms: u64,
    slowest_query_ms: u64,
    query_times: Vec<u64>,
}

impl Default for PerformanceMonitor {
    fn default() -> Self {
        Self::new()
    }
}

impl PerformanceMonitor {
    /// Create a new performance monitor
    pub fn new() -> Self {
        Self {
            start_time: Instant::now(),
            checkpoints: Vec::new(),
            memory_tracker: MemoryTracker {
                peak_memory_mb: 0.0,
                current_memory_mb: get_memory_usage_mb(),
                start_memory_mb: get_memory_usage_mb(),
            },
            query_tracker: QueryTracker {
                total_queries: 0,
                successful_queries: 0,
                total_time_ms: 0,
                fastest_query_ms: u64::MAX,
                slowest_query_ms: 0,
                query_times: Vec::new(),
            },
        }
    }

    /// Add a performance checkpoint
    pub fn checkpoint(&mut self, name: &str) {
        let memory_mb = get_memory_usage_mb();
        self.memory_tracker.current_memory_mb = memory_mb;
        self.memory_tracker.peak_memory_mb = self.memory_tracker.peak_memory_mb.max(memory_mb);

        self.checkpoints.push(PerformanceCheckpoint {
            name: name.to_string(),
            timestamp: Instant::now(),
            memory_mb,
            operation_count: 0,
        });
    }

    /// Record a database query
    pub fn record_query(&mut self, query_time_ms: u64, success: bool) {
        self.query_tracker.total_queries += 1;
        self.query_tracker.total_time_ms += query_time_ms;
        self.query_tracker.query_times.push(query_time_ms);

        if success {
            self.query_tracker.successful_queries += 1;
        }

        self.query_tracker.fastest_query_ms = self.query_tracker.fastest_query_ms.min(query_time_ms);
        self.query_tracker.slowest_query_ms = self.query_tracker.slowest_query_ms.max(query_time_ms);
    }

    /// Generate comprehensive performance metrics
    pub fn generate_metrics(&self, variant_count: usize, result_count: usize) -> PerformanceMetrics {
        let total_elapsed = self.start_time.elapsed().as_millis() as u64;

        // Calculate variant generation metrics
        let (wildcard_time, mutation_time, normalization_time) = self.extract_timing_breakdown();
        let generation_rate = if total_elapsed > 0 {
            variant_count as f64 * 1000.0 / total_elapsed as f64
        } else {
            0.0
        };

        let variant_generation = VariantGenerationMetrics {
            total_generation_time_ms: total_elapsed,
            variants_generated: variant_count,
            generation_rate,
            peak_memory_mb: self.memory_tracker.peak_memory_mb,
            wildcard_expansion_time_ms: wildcard_time,
            mutation_generation_time_ms: mutation_time,
            normalization_time_ms: normalization_time,
        };

        // Calculate database query metrics
        let avg_query_time = if self.query_tracker.total_queries > 0 {
            self.query_tracker.total_time_ms as f64 / self.query_tracker.total_queries as f64
        } else {
            0.0
        };

        let hit_rate = if self.query_tracker.total_queries > 0 {
            self.query_tracker.successful_queries as f64 / self.query_tracker.total_queries as f64
        } else {
            0.0
        };

        let database_queries = DatabaseQueryMetrics {
            total_queries: self.query_tracker.total_queries,
            avg_query_time_ms: avg_query_time,
            successful_queries: self.query_tracker.successful_queries,
            hit_rate,
            total_query_time_ms: self.query_tracker.total_time_ms,
            fastest_query_ms: if self.query_tracker.fastest_query_ms == u64::MAX {
                0
            } else {
                self.query_tracker.fastest_query_ms
            },
            slowest_query_ms: self.query_tracker.slowest_query_ms,
        };

        // Calculate memory metrics
        let memory_growth_rate = if total_elapsed > 0 {
            (self.memory_tracker.peak_memory_mb - self.memory_tracker.start_memory_mb) * 1000.0
                / total_elapsed as f64
        } else {
            0.0
        };

        let memory_usage = MemoryUsageMetrics {
            peak_memory_mb: self.memory_tracker.peak_memory_mb,
            variants_memory_mb: (variant_count as f64 * 13.0) / 1024.0 / 1024.0, // Rough estimate
            results_memory_mb: (result_count as f64 * 32.0) / 1024.0 / 1024.0, // Rough estimate
            memory_efficiency: if self.memory_tracker.peak_memory_mb > 0.0 {
                result_count as f64 / self.memory_tracker.peak_memory_mb
            } else {
                0.0
            },
            memory_growth_rate_mb_per_sec: memory_growth_rate,
        };

        // Calculate parallel processing metrics
        let thread_count = num_cpus::get();
        let parallel_efficiency = 1.0; // TODO: Calculate actual efficiency
        let load_balance_score = 0.9; // TODO: Calculate actual load balance

        let parallel_processing = ParallelProcessingMetrics {
            worker_threads: thread_count,
            parallel_efficiency,
            load_balance_score,
            thread_contention_ms: 0, // TODO: Measure thread contention
            sequential_time_estimate_ms: total_elapsed, // TODO: Calculate sequential estimate
            parallel_time_ms: total_elapsed,
        };

        PerformanceMetrics {
            variant_generation,
            database_queries,
            memory_usage,
            parallel_processing,
        }
    }

    /// Extract timing breakdown from checkpoints
    fn extract_timing_breakdown(&self) -> (u64, u64, u64) {
        let mut wildcard_time = 0u64;
        let mut mutation_time = 0u64;
        let mut normalization_time = 0u64;

        let mut prev_time = self.start_time;

        for checkpoint in &self.checkpoints {
            let elapsed = checkpoint.timestamp.duration_since(prev_time).as_millis() as u64;

            match checkpoint.name.as_str() {
                name if name.contains("wildcard") => wildcard_time += elapsed,
                name if name.contains("mutation") => mutation_time += elapsed,
                name if name.contains("normalization") => normalization_time += elapsed,
                _ => {}
            }

            prev_time = checkpoint.timestamp;
        }

        (wildcard_time, mutation_time, normalization_time)
    }
}

/// Get current memory usage in MB
fn get_memory_usage_mb() -> f64 {
    // This is a simplified implementation
    // In a real scenario, you would use platform-specific APIs
    // or crates like `memory-stats` for accurate measurement
    0.0 // Placeholder
}

/// Performance configuration for optimization
#[derive(Debug, Clone)]
pub struct PerformanceConfig {
    /// Enable parallel processing
    pub enable_parallel: bool,

    /// Number of worker threads (None = auto-detect)
    pub worker_threads: Option<usize>,

    /// Batch size for processing
    pub batch_size: usize,

    /// Memory limit in MB
    pub memory_limit_mb: f64,

    /// Enable performance monitoring
    pub enable_monitoring: bool,

    /// Timeout in seconds
    pub timeout_seconds: u64,
}

impl Default for PerformanceConfig {
    fn default() -> Self {
        Self {
            enable_parallel: true,
            worker_threads: None,
            batch_size: constants::DEFAULT_BATCH_SIZE,
            memory_limit_mb: constants::DEFAULT_MEMORY_LIMIT_MB,
            enable_monitoring: true,
            timeout_seconds: constants::DEFAULT_TIMEOUT_SECONDS,
        }
    }
}

/// Performance optimizer for fuzzy queries
pub struct PerformanceOptimizer {
    config: PerformanceConfig,
    monitor: Option<PerformanceMonitor>,
}

impl PerformanceOptimizer {
    /// Create a new performance optimizer
    pub fn new(config: PerformanceConfig) -> Self {
        let monitor = if config.enable_monitoring {
            Some(PerformanceMonitor::new())
        } else {
            None
        };

        Self { config, monitor }
    }

    /// Get optimal batch size based on system characteristics
    pub fn optimal_batch_size(&self, variant_count: usize) -> usize {
        let base_size = self.config.batch_size;

        // Adjust based on variant count
        if variant_count < 100 {
            base_size.min(variant_count)
        } else if variant_count < 1000 {
            base_size
        } else if variant_count < 10000 {
            base_size * 2
        } else {
            base_size * 4
        }
    }

    /// Determine if parallel processing should be used
    pub fn should_use_parallel(&self, variant_count: usize) -> bool {
        if !self.config.enable_parallel {
            return false;
        }

        // Use parallel processing for larger variant sets
        variant_count >= constants::PARALLEL_THRESHOLD
    }

    /// Get optimal number of worker threads
    pub fn optimal_thread_count(&self, variant_count: usize) -> usize {
        if !self.config.enable_parallel {
            return 1;
        }

        match self.config.worker_threads {
            Some(threads) => threads,
            None => {
                // Auto-detect based on variant count and CPU cores
                let cpu_cores = num_cpus::get();

                if variant_count < 1000 {
                    1 // Sequential is better for small sets
                } else if variant_count < 10000 {
                    cpu_cores.min(4)
                } else {
                    cpu_cores
                }
            }
        }
    }

    /// Check memory constraints
    pub fn check_memory_constraints(&self, variant_count: usize) -> FuzzyResult<()> {
        let estimated_memory_mb = (variant_count as f64 * 64.0) / 1024.0 / 1024.0; // Rough estimate

        if estimated_memory_mb > self.config.memory_limit_mb {
            return Err(FuzzyError::MemoryLimitExceeded {
                usage_mb: estimated_memory_mb,
                limit_mb: self.config.memory_limit_mb,
            });
        }

        Ok(())
    }

    /// Validate performance configuration
    pub fn validate_config(&self) -> FuzzyResult<()> {
        if self.config.batch_size == 0 {
            return Err(FuzzyError::InvalidParameters(
                "Batch size must be greater than 0".to_string(),
            ));
        }

        if self.config.memory_limit_mb <= 0.0 {
            return Err(FuzzyError::InvalidParameters(
                "Memory limit must be greater than 0".to_string(),
            ));
        }

        if self.config.timeout_seconds == 0 {
            return Err(FuzzyError::InvalidParameters(
                "Timeout must be greater than 0".to_string(),
            ));
        }

        Ok(())
    }

    /// Get performance monitor reference
    pub fn monitor(&mut self) -> Option<&mut PerformanceMonitor> {
        self.monitor.as_mut()
    }

    /// Take the performance monitor (consumes it)
    pub fn take_monitor(&mut self) -> Option<PerformanceMonitor> {
        self.monitor.take()
    }
}

/// Performance optimization utilities
pub mod utils {
    use super::*;

    /// Estimate query time based on database size and variant count
    pub fn estimate_query_time(
        database_size: u64,
        variant_count: usize,
        use_parallel: bool,
    ) -> Duration {
        let base_time_per_query_ms = if database_size < 1_000_000 {
            1.0 // Small database
        } else if database_size < 100_000_000 {
            5.0 // Medium database
        } else {
            20.0 // Large database
        };

        let total_time_ms = variant_count as f64 * base_time_per_query_ms;

        // Apply parallel speedup
        let adjusted_time_ms = if use_parallel {
            total_time_ms / num_cpus::get() as f64 * 0.8 // 80% efficiency
        } else {
            total_time_ms
        };

        Duration::from_millis(adjusted_time_ms as u64)
    }

    /// Determine if query should be aborted based on performance
    pub fn should_abort_query(
        elapsed_time: Duration,
        _variant_count: usize,
        timeout_seconds: u64,
    ) -> bool {
        elapsed_time.as_secs() > timeout_seconds
    }

    /// Optimize variant processing order for better cache performance
    pub fn optimize_variant_order(variants: &mut [String]) {
        // Sort by first character for better cache locality
        variants.sort();

        // TODO: Implement more sophisticated ordering based on database structure
    }

    /// Calculate optimal chunk size for parallel processing
    pub fn calculate_optimal_chunk_size(
        total_items: usize,
        num_threads: usize,
        min_chunk_size: usize,
    ) -> usize {
        let base_chunk_size = total_items / num_threads;
        base_chunk_size.max(min_chunk_size)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_performance_config_default() {
        let config = PerformanceConfig::default();
        assert!(config.enable_parallel);
        assert_eq!(config.batch_size, constants::DEFAULT_BATCH_SIZE);
        assert_eq!(config.memory_limit_mb, constants::DEFAULT_MEMORY_LIMIT_MB);
        assert!(config.enable_monitoring);
    }

    #[test]
    fn test_performance_optimizer() {
        let config = PerformanceConfig::default();
        let optimizer = PerformanceOptimizer::new(config);

        assert!(optimizer.validate_config().is_ok());

        // Test batch size optimization
        assert_eq!(optimizer.optimal_batch_size(50), 50);
        assert!(optimizer.optimal_batch_size(5000) >= constants::DEFAULT_BATCH_SIZE);

        // Test parallel processing decision
        assert!(!optimizer.should_use_parallel(50));
        assert!(optimizer.should_use_parallel(1000));

        // Test thread count optimization
        assert_eq!(optimizer.optimal_thread_count(50), 1);
        assert!(optimizer.optimal_thread_count(10000) >= 1);
    }

    #[test]
    fn test_performance_monitor() {
        let mut monitor = PerformanceMonitor::new();

        monitor.checkpoint("test_checkpoint");
        monitor.record_query(10, true);
        monitor.record_query(5, false);

        let metrics = monitor.generate_metrics(100, 50);
        assert_eq!(metrics.variant_generation.variants_generated, 100);
        assert_eq!(metrics.database_queries.total_queries, 2);
        assert_eq!(metrics.database_queries.successful_queries, 1);
    }

    #[test]
    fn test_utils_estimate_query_time() {
        let small_db_time = utils::estimate_query_time(100_000, 100, false);
        let large_db_time = utils::estimate_query_time(1_000_000_000, 100, false);

        assert!(large_db_time > small_db_time);

        let parallel_time = utils::estimate_query_time(1_000_000_000, 100, true);
        let sequential_time = utils::estimate_query_time(1_000_000_000, 100, false);

        assert!(parallel_time < sequential_time); // Parallel should be faster
    }

    #[test]
    fn test_utils_optimize_variant_order() {
        let mut variants = vec![
            "TTTT".to_string(),
            "AAAA".to_string(),
            "CCCC".to_string(),
            "GGGG".to_string(),
        ];

        utils::optimize_variant_order(&mut variants);

        // Should be sorted alphabetically
        assert_eq!(variants[0], "AAAA");
        assert_eq!(variants[1], "CCCC");
        assert_eq!(variants[2], "GGGG");
        assert_eq!(variants[3], "TTTT");
    }

    #[test]
    fn test_utils_calculate_optimal_chunk_size() {
        let chunk_size = utils::calculate_optimal_chunk_size(1000, 4, 10);
        assert!(chunk_size >= 10);
        assert!(chunk_size <= 1000);
    }

    #[test]
    fn test_should_abort_query() {
        let timeout = 5u64;
        let short_time = Duration::from_secs(1);
        let long_time = Duration::from_secs(10);

        assert!(!utils::should_abort_query(short_time, 100, timeout));
        assert!(utils::should_abort_query(long_time, 100, timeout));
    }
}