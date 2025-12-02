//! RustKmer Python bindings
//!
//! This module provides Python bindings for the RustKmer library using PyO3.
//! It exposes the core functionality of k-mer counting, database operations,
//! and fuzzy querying to Python users.

use pyo3::prelude::*;

// Import our modules
mod kmer_counter;
mod database;
mod fuzzy_query;
mod utils;
mod exceptions;

// Re-export Python classes
use kmer_counter::{PyKmerCounter, CounterStats};
use database::{PyDatabase, PyQueryResult, PyDatabaseStats};
use fuzzy_query::{PyFuzzyQuery, PyFuzzyQueryResult};
use utils::{
    set_verbosity, get_version, get_log_level, log_message, is_log_enabled,
    get_system_info, enable_debug_mode, enable_trace_mode, flush_logs,
    get_resource_stats, cleanup_resources, PerformanceTimer
};

/// Initialize performance monitoring system
#[pyfunction]
#[pyo3(signature = (enabled, track_memory, track_timing, track_operations, max_samples=None))]
fn initialize_monitoring(enabled: bool, track_memory: bool, track_timing: bool, track_operations: bool, max_samples: Option<usize>) -> PyResult<()> {
    #[cfg(feature = "profiling")]
    {
        use rustkmer::core::monitoring::MonitoringConfig;
        let config = MonitoringConfig {
            enabled,
            track_memory,
            track_timing,
            track_operations,
            max_samples: max_samples.unwrap_or(10_000),
        };
        rustkmer::core::monitoring::initialize_monitoring(config);
        Ok(())
    }
    #[cfg(not(feature = "profiling"))]
    {
        // No-op when profiling is disabled
        Ok(())
    }
}

/// Get comprehensive performance statistics
#[pyfunction]
fn get_performance_stats() -> PyResult<std::collections::HashMap<String, String>> {
    #[cfg(feature = "profiling")]
    {
        use rustkmer::core::monitoring::get_global_collector;
        let collector = get_global_collector();
        let collector = collector.lock().unwrap();

        let mut stats = std::collections::HashMap::new();
        stats.insert("total_samples".to_string(), collector.total_samples.to_string());
        stats.insert("enabled".to_string(), collector.config.enabled.to_string());
        stats.insert("track_memory".to_string(), collector.config.track_memory.to_string());
        stats.insert("track_timing".to_string(), collector.config.track_timing.to_string());
        stats.insert("track_operations".to_string(), collector.config.track_operations.to_string());

        // Add operation-specific stats
        for (operation, _) in &collector.active_timers {
            if let Some(op_stats) = collector.get_operation_stats(operation) {
                let key_prefix = format!("{}_", operation);
                stats.insert(format!("{}count", key_prefix), op_stats.count.to_string());
                stats.insert(format!("{}avg_ms", key_prefix), format!("{:.2}", op_stats.average.as_millis()));
                stats.insert(format!("{}min_ms", key_prefix), format!("{:.2}", op_stats.min.as_millis()));
                stats.insert(format!("{}max_ms", key_prefix), format!("{:.2}", op_stats.max.as_millis()));
                stats.insert(format!("{}total_ms", key_prefix), format!("{:.2}", op_stats.total.as_millis()));
            }
        }

        Ok(stats)
    }
    #[cfg(not(feature = "profiling"))]
    {
        Ok(std::collections::HashMap::new())
    }
}

/// Export detailed performance metrics to JSON
#[pyfunction]
fn export_metrics() -> PyResult<String> {
    #[cfg(feature = "profiling")]
    {
        use rustkmer::core::monitoring::get_global_collector;
        let collector = get_global_collector();
        let collector = collector.lock().unwrap();
        let json_bytes = collector.export_metrics();
        Ok(String::from_utf8_lossy(&json_bytes).to_string())
    }
    #[cfg(not(feature = "profiling"))]
    {
        Ok("{}".to_string()) // Empty JSON object when profiling is disabled
    }
}

/// Record a custom performance metric
#[pyfunction]
fn record_custom_metric(operation: String, metric_name: String, value: f64) -> PyResult<()> {
    #[cfg(feature = "profiling")]
    {
        rustkmer::core::monitoring::record_metric(&operation, &metric_name, value);
        Ok(())
    }
    #[cfg(not(feature = "profiling"))]
    {
        Ok(())
    }
}

/// Check if performance monitoring is available
#[pyfunction]
fn is_monitoring_available() -> bool {
    cfg!(feature = "profiling")
}

/// Python module for RustKmer
#[pymodule]
fn _rustkmer(m: &Bound<'_, PyModule>) -> PyResult<()> {
    let py = m.py();
    // Version information
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    // Core classes
    m.add_class::<PyKmerCounter>()?;
    m.add_class::<CounterStats>()?;
    m.add_class::<PyDatabase>()?;
    m.add_class::<PyQueryResult>()?;
    m.add_class::<PyDatabaseStats>()?;
    m.add_class::<PyFuzzyQuery>()?;
    m.add_class::<PyFuzzyQueryResult>()?;

    // Debugging and utility classes
    m.add_class::<PerformanceTimer>()?;

    // Performance monitoring functions
    m.add_function(wrap_pyfunction!(initialize_monitoring, m)?)?;
    m.add_function(wrap_pyfunction!(get_performance_stats, m)?)?;
    m.add_function(wrap_pyfunction!(export_metrics, m)?)?;
    m.add_function(wrap_pyfunction!(record_custom_metric, m)?)?;
    m.add_function(wrap_pyfunction!(is_monitoring_available, m)?)?;

    // Logging and debugging functions
    m.add_function(wrap_pyfunction!(set_verbosity, m)?)?;
    m.add_function(wrap_pyfunction!(get_version, m)?)?;
    m.add_function(wrap_pyfunction!(get_log_level, m)?)?;
    m.add_function(wrap_pyfunction!(log_message, m)?)?;
    m.add_function(wrap_pyfunction!(is_log_enabled, m)?)?;
    m.add_function(wrap_pyfunction!(get_system_info, m)?)?;
    m.add_function(wrap_pyfunction!(enable_debug_mode, m)?)?;
    m.add_function(wrap_pyfunction!(enable_trace_mode, m)?)?;
    m.add_function(wrap_pyfunction!(flush_logs, m)?)?;

    // Resource management functions
    m.add_function(wrap_pyfunction!(get_resource_stats, m)?)?;
    m.add_function(wrap_pyfunction!(cleanup_resources, m)?)?;

    // Register custom exceptions
    exceptions::register_exceptions(m)?;

    Ok(())
}