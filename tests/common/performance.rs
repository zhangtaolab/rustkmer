//! Performance monitoring utilities for testing

use std::time::{Duration, Instant};
use std::collections::HashMap;

/// Performance metrics for operations
#[derive(Debug, Clone)]
pub struct PerformanceMetrics {
    pub operation_name: String,
    pub start_time: Instant,
    pub end_time: Option<Instant>,
    pub duration: Option<Duration>,
    pub items_processed: usize,
    pub memory_peak: usize,
    pub custom_metrics: HashMap<String, f64>,
}

impl PerformanceMetrics {
    /// Create new performance metrics
    pub fn new(operation_name: &str) -> Self {
        Self {
            operation_name: operation_name.to_string(),
            start_time: Instant::now(),
            end_time: None,
            duration: None,
            items_processed: 0,
            memory_peak: 0,
            custom_metrics: HashMap::new(),
        }
    }

    /// Mark the operation as completed
    pub fn complete(&mut self, items_processed: usize, memory_peak: usize) {
        self.end_time = Some(Instant::now());
        self.duration = Some(self.start_time.elapsed());
        self.items_processed = items_processed;
        self.memory_peak = memory_peak;
    }

    /// Get the duration of the operation
    pub fn duration(&self) -> Option<Duration> {
        self.duration.or_else(|| self.end_time.map(|end| end.duration_since(self.start_time)))
    }

    /// Get operations per second
    pub fn ops_per_second(&self) -> Option<f64> {
        self.duration().map(|d| {
            let secs = d.as_secs_f64();
            if secs > 0.0 {
                self.items_processed as f64 / secs
            } else {
                f64::INFINITY
            }
        })
    }

    /// Get operations per minute
    pub fn ops_per_minute(&self) -> Option<f64> {
        self.ops_per_second().map(|ops| ops * 60.0)
    }

    /// Get throughput in MB/s
    pub fn throughput_mb_per_sec(&self, bytes_processed: usize) -> Option<f64> {
        self.duration().map(|d| {
            let secs = d.as_secs_f64();
            if secs > 0.0 {
                (bytes_processed as f64) / (1024.0 * 1024.0 * secs)
            } else {
                f64::INFINITY
            }
        })
    }

    /// Add a custom metric
    pub fn add_custom_metric(&mut self, name: &str, value: f64) {
        self.custom_metrics.insert(name.to_string(), value);
    }

    /// Get a custom metric value
    pub fn get_custom_metric(&self, name: &str) -> Option<f64> {
        self.custom_metrics.get(name).copied()
    }

    /// Format duration in human readable form
    pub fn format_duration(&self) -> String {
        match self.duration() {
            Some(d) => {
                let total_ms = d.as_millis();
                if total_ms < 1000 {
                    format!("{}ms", total_ms)
                } else if total_ms < 60_000 {
                    format!("{:.2}s", total_ms as f64 / 1000.0)
                } else if total_ms < 3_600_000 {
                    format!("{:.2}m", total_ms as f64 / 60_000.0)
                } else {
                    format!("{:.2}h", total_ms as f64 / 3_600_000.0)
                }
            }
            None => "N/A".to_string(),
        }
    }

    /// Format operations per second
    pub fn format_ops_per_sec(&self) -> String {
        match self.ops_per_second() {
            Some(ops) if ops.is_finite() => format!("{:.0} ops/sec", ops),
            Some(_) => "∞ ops/sec".to_string(),
            None => "N/A".to_string(),
        }
    }

    /// Generate a summary string
    pub fn summary(&self) -> String {
        format!(
            "{}: {} items in {}, Memory: {}MB, Rate: {}",
            self.operation_name,
            self.items_processed,
            self.format_duration(),
            self.memory_peak / (1024 * 1024),
            self.format_ops_per_sec()
        )
    }
}

/// Performance timer for measuring operation duration
pub struct PerformanceTimer {
    start_time: Instant,
}

impl PerformanceTimer {
    /// Start a new timer
    pub fn start() -> Self {
        Self {
            start_time: Instant::now(),
        }
    }

    /// Get elapsed time
    pub fn elapsed(&self) -> Duration {
        self.start_time.elapsed()
    }

    /// Create performance metrics
    pub fn create_metrics(&self, operation_name: &str, items_processed: usize) -> PerformanceMetrics {
        let mut metrics = PerformanceMetrics::new(operation_name);
        metrics.complete(items_processed, 0);
        metrics
    }
}

/// Performance benchmarking utilities
pub struct BenchmarkSuite {
    name: String,
    results: Vec<PerformanceMetrics>,
}

impl BenchmarkSuite {
    /// Create a new benchmark suite
    pub fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            results: Vec::new(),
        }
    }

    /// Add a benchmark result
    pub fn add_result(&mut self, metrics: PerformanceMetrics) {
        self.results.push(metrics);
    }

    /// Get the fastest benchmark
    pub fn fastest(&self) -> Option<&PerformanceMetrics> {
        self.results.iter().min_by_key(|m| m.duration().unwrap_or_default())
    }

    /// Get the slowest benchmark
    pub fn slowest(&self) -> Option<&PerformanceMetrics> {
        self.results.iter().max_by_key(|m| m.duration().unwrap_or_default())
    }

    /// Get the average duration
    pub fn average_duration(&self) -> Option<Duration> {
        if self.results.is_empty() {
            None
        } else {
            let total_ms: u128 = self.results
                .iter()
                .map(|m| m.duration().unwrap_or_default().as_millis())
                .sum();
            Some(Duration::from_millis((total_ms / self.results.len() as u128) as u64))
        }
    }

    /// Get total time
    pub fn total_time(&self) -> Option<Duration> {
        if self.results.is_empty() {
            None
        } else {
            let total_ms: u128 = self.results
                .iter()
                .map(|m| m.duration().unwrap_or_default().as_millis())
                .sum();
            Some(Duration::from_millis(total_ms as u64))
        }
    }

    /// Generate a benchmark report
    pub fn generate_report(&self) -> String {
        let mut report = format!("Benchmark Suite: {}\n", self.name);
        report.push_str(&"=".repeat(60));

        if self.results.is_empty() {
            report.push_str("\nNo benchmarks run.\n");
        } else {
            report.push_str(&format!("\nTotal benchmarks: {}\n", self.results.len()));

            if let Some(avg) = self.average_duration() {
                report.push_str(&format!("Average duration: {:.2}s\n", avg.as_secs_f64()));
            }

            if let Some(total) = self.total_time() {
                report.push_str(&format!("Total time: {:.2}s\n", total.as_secs_f64()));
            }

            report.push_str("\nBenchmark Results:\n");
            report.push_str(&"-".repeat(80));

            for (i, metrics) in self.results.iter().enumerate() {
                report.push_str(&format!(
                    "\n{}: {} ({})",
                    i + 1,
                    metrics.operation_name,
                    metrics.summary()
                ));
            }
        }

        report
    }

    /// Export results as CSV
    pub fn export_csv(&self) -> String {
        let mut csv = "Operation,Duration(ms),Items,Ops/Sec,Memory(MB)\n".to_string();

        for metrics in &self.results {
            let duration_ms = metrics.duration().unwrap_or_default().as_millis();
            let ops_per_sec = metrics.ops_per_second().unwrap_or(0.0);
            let memory_mb = metrics.memory_peak / (1024 * 1024);

            csv.push_str(&format!(
                "{},{},{},{:.2},{}\n",
                metrics.operation_name,
                duration_ms,
                metrics.items_processed,
                ops_per_sec,
                memory_mb
            ));
        }

        csv
    }
}

/// Macro for timing operations
#[macro_export]
macro_rules! time_operation {
    ($op:expr) => {{
        let timer = $crate::tests::common::performance::PerformanceTimer::start();
        let result = $op;
        let elapsed = timer.elapsed();
        (result, elapsed)
    }};
}

/// Macro for timing operations with item count
#[macro_export]
macro_rules! time_operation_with_items {
    ($op:expr, $items:expr) => {{
        let timer = $crate::tests::common::performance::PerformanceTimer::start();
        let result = $op;
        let elapsed = timer.elapsed();
        (result, elapsed, $items)
    }};
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_performance_metrics() {
        let mut metrics = PerformanceMetrics::new("test_operation");

        // Test initial state
        assert!(metrics.start_time <= Instant::now());
        assert!(metrics.end_time.is_none());
        assert_eq!(metrics.items_processed, 0);

        // Test completion
        metrics.complete(1000, 50 * 1024 * 1024);

        assert!(metrics.end_time.is_some());
        assert!(metrics.duration().is_some());
        assert_eq!(metrics.items_processed, 1000);
        assert_eq!(metrics.memory_peak, 50 * 1024 * 1024);
    }

    #[test]
    fn test_performance_timer() {
        let timer = PerformanceTimer::start();
        std::thread::sleep(std::time::Duration::from_millis(100));
        let elapsed = timer.elapsed();

        assert!(elapsed.as_millis() >= 100);
        assert!(elapsed.as_millis() < 150);
    }

    #[test]
    fn test_benchmark_suite() {
        let mut suite = BenchmarkSuite::new("Test Suite");

        // Add some test results
        let mut metrics1 = PerformanceMetrics::new("Operation 1");
        metrics1.complete(1000, 10 * 1024 * 1024);

        let mut metrics2 = PerformanceMetrics::new("Operation 2");
        std::thread::sleep(std::time::Duration::from_millis(50));
        metrics2.complete(2000, 20 * 1024 * 1024);

        suite.add_result(metrics1);
        suite.add_result(metrics2);

        assert_eq!(suite.results.len(), 2);

        let report = suite.generate_report();
        assert!(report.contains("Test Suite"));
        assert!(report.contains("Operation 1"));
        assert!(report.contains("Operation 2"));
    }

    #[test]
    fn test_format_bytes() {
        let mut metrics = PerformanceMetrics::new("test");
        metrics.complete(1000, 100 * 1024 * 1024);

        assert_eq!(metrics.format_ops_per_sec().parse::<f64>().unwrap() > 0.0, true);
        assert_eq!(metrics.summary(), "test: 1000 items in N/A, Memory: 100MB, Rate: N/A");
    }
}