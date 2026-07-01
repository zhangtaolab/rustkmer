//! Performance monitoring infrastructure with conditional compilation
//!
//! This module provides low-overhead performance monitoring that can be
//! enabled/disabled at compile time using the "profiling" feature flag.

#[cfg(feature = "profiling")]
use serde::{Deserialize, Serialize};
#[cfg(feature = "profiling")]
use std::sync::{Arc, Mutex};
#[cfg(feature = "profiling")]
use std::time::{Duration, Instant};

/// Performance monitoring configuration
#[cfg(feature = "profiling")]
#[derive(Debug, Clone)]
pub struct MonitoringConfig {
    pub enabled: bool,
    pub track_memory: bool,
    pub track_timing: bool,
    pub track_operations: bool,
    pub max_samples: usize,
}

#[cfg(feature = "profiling")]
impl Default for MonitoringConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            track_memory: true,
            track_timing: true,
            track_operations: true,
            max_samples: 10_000,
        }
    }
}

/// Performance monitoring configuration (non-profiling stub)
#[cfg(not(feature = "profiling"))]
#[derive(Debug, Clone, Default)]
pub struct MonitoringConfig {
    pub enabled: bool,
}

#[cfg(not(feature = "profiling"))]

/// Core performance metrics structure
#[cfg(feature = "profiling")]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OperationMetrics {
    /// Operation name (e.g., "kmer_counting", "database_query")
    pub operation_name: String,
    /// Total duration of the operation
    pub duration: Duration,
    /// Memory usage statistics (in bytes)
    pub memory_stats: MemoryUsage,
    /// Number of items processed (k-mers, sequences, etc.)
    pub items_processed: u64,
    /// Number of successful operations
    pub successful_operations: u64,
    /// Number of failed operations
    pub failed_operations: u64,
    /// Additional custom metrics
    pub custom_metrics: std::collections::HashMap<String, f64>,
}

#[cfg(feature = "profiling")]
impl OperationMetrics {
    pub fn new(operation_name: String) -> Self {
        Self {
            operation_name,
            duration: Duration::default(),
            memory_stats: MemoryUsage::default(),
            items_processed: 0,
            successful_operations: 0,
            failed_operations: 0,
            custom_metrics: std::collections::HashMap::new(),
        }
    }

    pub fn add_custom_metric(&mut self, key: String, value: f64) {
        self.custom_metrics.insert(key, value);
    }

    pub fn success_rate(&self) -> f64 {
        let total = self.successful_operations + self.failed_operations;
        if total == 0 {
            0.0
        } else {
            self.successful_operations as f64 / total as f64
        }
    }

    pub fn items_per_second(&self) -> f64 {
        if self.duration.as_secs_f64() > 0.0 {
            self.items_processed as f64 / self.duration.as_secs_f64()
        } else {
            0.0
        }
    }
}

/// Memory usage tracking structure
#[cfg(feature = "profiling")]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryUsage {
    /// Peak memory usage in bytes
    pub peak_bytes: u64,
    /// Current memory usage in bytes
    pub current_bytes: u64,
    /// Total allocations in bytes
    pub total_allocated: u64,
    /// Total deallocations in bytes
    pub total_deallocated: u64,
}

#[cfg(feature = "profiling")]
impl Default for MemoryUsage {
    fn default() -> Self {
        Self {
            peak_bytes: 0,
            current_bytes: 0,
            total_allocated: 0,
            total_deallocated: 0,
        }
    }
}

#[cfg(feature = "profiling")]
impl MemoryUsage {
    pub fn update_allocation(&mut self, size: u64) {
        self.current_bytes += size;
        self.total_allocated += size;
        if self.current_bytes > self.peak_bytes {
            self.peak_bytes = self.current_bytes;
        }
    }

    pub fn update_deallocation(&mut self, size: u64) {
        self.current_bytes = self.current_bytes.saturating_sub(size);
        self.total_deallocated += size;
    }
}

/// Performance timer for measuring operation durations
#[cfg(feature = "profiling")]
pub struct PerformanceTimer {
    start_time: Instant,
    operation_name: String,
    metrics_collector: Option<Arc<Mutex<MetricsCollector>>>,
}

#[cfg(feature = "profiling")]
impl PerformanceTimer {
    /// Create a new performance timer
    pub fn new(operation_name: String) -> Self {
        log::debug!("Starting performance timer for: {}", operation_name);
        Self {
            start_time: Instant::now(),
            operation_name,
            metrics_collector: None,
        }
    }

    /// Create a new performance timer with metrics collector
    pub fn with_collector(operation_name: String, collector: Arc<Mutex<MetricsCollector>>) -> Self {
        log::debug!(
            "Starting performance timer for: {} (with collection)",
            operation_name
        );
        Self {
            start_time: Instant::now(),
            operation_name,
            metrics_collector: Some(collector),
        }
    }

    /// Finish timing and record the duration
    pub fn finish(self) -> Duration {
        let duration = self.start_time.elapsed();
        log::debug!(
            "Operation '{}' completed in {:?}",
            self.operation_name,
            duration
        );

        if let Some(collector) = self.metrics_collector {
            let mut collector = collector.lock().unwrap();
            collector.record_timing(self.operation_name, duration);
        }

        duration
    }

    /// Get elapsed time without finishing
    pub fn elapsed(&self) -> Duration {
        self.start_time.elapsed()
    }
}

#[cfg(feature = "profiling")]
impl Drop for PerformanceTimer {
    fn drop(&mut self) {
        let elapsed = self.elapsed();
        log::debug!(
            "Performance timer for '{}' dropped after {:?}",
            self.operation_name,
            elapsed
        );

        if let Some(collector) = &self.metrics_collector {
            let mut collector = collector.lock().unwrap();
            collector.record_timing(self.operation_name.clone(), elapsed);
        }
    }
}

/// Global metrics collector for aggregating performance data
#[cfg(feature = "profiling")]
#[derive(Debug)]
pub struct MetricsCollector {
    config: MonitoringConfig,
    operations: Vec<OperationMetrics>,
    active_timers: std::collections::HashMap<String, Vec<Duration>>,
    total_samples: usize,
}

#[cfg(feature = "profiling")]
impl MetricsCollector {
    pub fn new(config: MonitoringConfig) -> Self {
        Self {
            config,
            operations: Vec::new(),
            active_timers: std::collections::HashMap::new(),
            total_samples: 0,
        }
    }

    pub fn record_timing(&mut self, operation: String, duration: Duration) {
        if !self.config.enabled {
            return;
        }

        let timings = self
            .active_timers
            .entry(operation.clone())
            .or_insert_with(Vec::new);
        timings.push(duration);

        // Maintain maximum sample limit
        if timings.len() > self.config.max_samples {
            timings.remove(0);
        }

        self.total_samples += 1;

        // Log periodic statistics
        if self.total_samples % 1000 == 0 {
            self.log_summary();
        }
    }

    pub fn record_operation(&mut self, metrics: OperationMetrics) {
        if !self.config.enabled {
            return;
        }

        self.operations.push(metrics);

        // Maintain maximum operation limit
        if self.operations.len() > self.config.max_samples {
            self.operations.remove(0);
        }
    }

    pub fn get_average_timing(&self, operation: &str) -> Option<Duration> {
        if let Some(timings) = self.active_timers.get(operation) {
            if timings.is_empty() {
                return None;
            }
            let total: Duration = timings.iter().sum();
            Some(total / timings.len() as u32)
        } else {
            None
        }
    }

    pub fn get_operation_stats(&self, operation: &str) -> Option<OperationStats> {
        if let Some(timings) = self.active_timers.get(operation) {
            if timings.is_empty() {
                return None;
            }

            let total: Duration = timings.iter().sum();
            let average = total / timings.len() as u32;
            let min = *timings.iter().min().unwrap();
            let max = *timings.iter().max().unwrap();

            Some(OperationStats {
                operation: operation.to_string(),
                count: timings.len(),
                total,
                average,
                min,
                max,
            })
        } else {
            None
        }
    }

    pub fn log_summary(&self) {
        log::info!(
            "Performance Summary - {} samples recorded",
            self.total_samples
        );

        for (operation, timings) in &self.active_timings {
            if let Some(stats) = self.get_operation_stats(operation) {
                log::info!(
                    "  {}: {} ops, avg {:?}, min {:?}, max {:?}",
                    operation,
                    stats.count,
                    stats.average,
                    stats.min,
                    stats.max
                );
            }
        }
    }

    pub fn export_metrics(&self) -> Vec<u8> {
        serde_json::to_vec_pretty(&self.operations).unwrap_or_default()
    }
}

#[cfg(feature = "profiling")]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OperationStats {
    pub operation: String,
    pub count: usize,
    pub total: Duration,
    pub average: Duration,
    pub min: Duration,
    pub max: Duration,
}

/// Global metrics collector instance
#[cfg(feature = "profiling")]
static GLOBAL_COLLECTOR: std::sync::OnceLock<Arc<Mutex<MetricsCollector>>> =
    std::sync::OnceLock::new();

/// Get the global metrics collector
#[cfg(feature = "profiling")]
pub fn get_global_collector() -> Arc<Mutex<MetricsCollector>> {
    GLOBAL_COLLECTOR
        .get_or_init(|| {
            let config = MonitoringConfig::default();
            Arc::new(Mutex::new(MetricsCollector::new(config)))
        })
        .clone()
}

/// Initialize global performance monitoring
#[cfg(feature = "profiling")]
pub fn initialize_monitoring(config: MonitoringConfig) {
    let collector = MetricsCollector::new(config);
    let _ = GLOBAL_COLLECTOR.set(Arc::new(Mutex::new(collector)));
    log::info!("Performance monitoring initialized");
}

/// Start a performance timer for an operation
#[cfg(feature = "profiling")]
pub fn start_timer(operation: &str) -> PerformanceTimer {
    let collector = get_global_collector();
    PerformanceTimer::with_collector(operation.to_string(), collector)
}

/// Record a custom metric
#[cfg(feature = "profiling")]
pub fn record_metric(operation: &str, metric_name: &str, value: f64) {
    let collector = get_global_collector();
    let mut collector = collector.lock().unwrap();

    // Find existing operation metrics or create new one
    if let Some(op_metrics) = collector
        .operations
        .iter_mut()
        .find(|op| op.operation_name == operation)
    {
        op_metrics.add_custom_metric(format!("{}.{}", operation, metric_name), value);
    } else {
        let mut new_metrics = OperationMetrics::new(operation.to_string());
        new_metrics.add_custom_metric(format!("{}.{}", operation, metric_name), value);
        collector.record_operation(new_metrics);
    }
}

// =============================================================================
// Stub implementations when profiling feature is disabled
// =============================================================================

#[cfg(not(feature = "profiling"))]
#[derive(Debug, Clone)]
pub struct OperationMetrics {
    pub operation_name: String,
}

#[cfg(not(feature = "profiling"))]
impl OperationMetrics {
    pub fn new(operation_name: String) -> Self {
        Self { operation_name }
    }
}

#[cfg(not(feature = "profiling"))]
pub struct PerformanceTimer {
    _private: (),
}

#[cfg(not(feature = "profiling"))]
impl PerformanceTimer {
    pub fn new(operation_name: String) -> Self {
        let _ = operation_name; // Suppress unused warning
        Self { _private: () }
    }

    pub fn finish(self) -> std::time::Duration {
        std::time::Duration::default()
    }

    pub fn elapsed(&self) -> std::time::Duration {
        std::time::Duration::default()
    }
}

#[cfg(not(feature = "profiling"))]
pub fn start_timer(_operation: &str) -> PerformanceTimer {
    PerformanceTimer::new(String::new())
}

#[cfg(not(feature = "profiling"))]
pub fn initialize_monitoring(_config: MonitoringConfig) {
    // No-op when profiling is disabled
}

#[cfg(not(feature = "profiling"))]
pub fn record_metric(_operation: &str, _metric_name: &str, _value: f64) {
    // No-op when profiling is disabled
}

/// Convenience macro for timing operations
#[macro_export]
macro_rules! time_operation {
    ($operation:expr, $block:block) => {{
        #[cfg(feature = "profiling")]
        {
            let _timer = $crate::core::monitoring::start_timer($operation);
            $block
        }
        #[cfg(not(feature = "profiling"))]
        {
            $block
        }
    }};
}

/// Convenience macro for conditional monitoring code
#[macro_export]
macro_rules! if_profiling {
    ($block:block) => {{
        #[cfg(feature = "profiling")]
        $block
    }};
}
