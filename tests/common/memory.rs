//! Memory usage tracking utilities for testing
//!
//! Shared test helper — see `tests/common/mod.rs` for the `dead_code` rationale.

#![allow(dead_code)]

use std::time::{Duration, Instant};

/// Memory usage statistics
#[derive(Debug, Clone)]
pub struct MemoryStats {
    pub peak_usage: usize,
    pub current_usage: usize,
    pub timestamp: Instant,
}

/// Memory monitor for tracking usage during operations
pub struct MemoryMonitor {
    initial_usage: usize,
    peak_usage: usize,
    start_time: Instant,
}

impl Default for MemoryMonitor {
    fn default() -> Self {
        Self::new()
    }
}

impl MemoryMonitor {
    /// Create a new memory monitor
    pub fn new() -> Self {
        Self {
            initial_usage: get_current_memory_usage(),
            peak_usage: get_current_memory_usage(),
            start_time: Instant::now(),
        }
    }

    /// Get current memory statistics
    pub fn current_stats(&self) -> MemoryStats {
        let current = get_current_memory_usage();
        MemoryStats {
            peak_usage: self.peak_usage.max(current),
            current_usage: current,
            timestamp: Instant::now(),
        }
    }

    /// Record a memory reading (updates peak if necessary)
    pub fn record_reading(&mut self) {
        let current = get_current_memory_usage();
        self.peak_usage = self.peak_usage.max(current);
    }

    /// Get initial memory usage
    pub fn initial_usage(&self) -> usize {
        self.initial_usage
    }

    /// Get peak memory usage
    pub fn peak_usage(&self) -> usize {
        self.peak_usage
    }

    /// Get elapsed time since creation
    pub fn elapsed(&self) -> Duration {
        self.start_time.elapsed()
    }

    /// Get memory increase since start
    pub fn increase(&self) -> isize {
        let current = get_current_memory_usage();
        (current as isize) - (self.initial_usage as isize)
    }
}

/// Get current process memory usage in bytes
pub fn get_current_memory_usage() -> usize {
    #[cfg(unix)]
    {
        use std::fs;

        // Try to read from /proc/self/status
        if let Ok(status) = fs::read_to_string("/proc/self/status") {
            for line in status.lines() {
                if line.starts_with("VmRSS:") {
                    let parts: Vec<&str> = line.split_whitespace().collect();
                    if parts.len() >= 2 {
                        if let Ok(kb) = parts[1].parse::<usize>() {
                            return kb * 1024; // Convert KB to bytes
                        }
                    }
                }
            }
        }

        // Fallback: use a simple estimate based on heap size
        estimate_heap_size()
    }

    #[cfg(not(unix))]
    {
        // For non-Unix systems, use a simple estimate
        estimate_heap_size()
    }
}

/// Estimate heap size (fallback method)
fn estimate_heap_size() -> usize {
    // This is a rough estimate - in practice, you might want more sophisticated tracking
    // For testing purposes, we'll assume a baseline usage
    10 * 1024 * 1024 // 10 MB baseline
}

/// Memory usage constraint for testing
#[derive(Debug)]
pub struct MemoryConstraint {
    pub max_usage: usize,
    pub relative_to_input: f64,
    pub warning_threshold: f64,
}

impl MemoryConstraint {
    /// Create a memory constraint
    pub fn new(max_usage: usize, relative_to_input: f64, warning_threshold: f64) -> Self {
        Self {
            max_usage,
            relative_to_input,
            warning_threshold,
        }
    }

    /// Check if the current usage exceeds the constraint
    pub fn is_exceeded(&self, current_usage: usize, input_size: usize) -> bool {
        let allowed = self
            .max_usage
            .max((input_size as f64 * self.relative_to_input) as usize);
        current_usage > allowed
    }

    /// Check if the current usage is near the warning threshold
    pub fn is_near_warning(&self, current_usage: usize, input_size: usize) -> bool {
        let allowed = self
            .max_usage
            .max((input_size as f64 * self.relative_to_input) as usize);
        current_usage > (allowed as f64 * self.warning_threshold) as usize
    }

    /// Get the maximum allowed usage for a given input size
    pub fn max_allowed(&self, input_size: usize) -> usize {
        self.max_usage
            .max((input_size as f64 * self.relative_to_input) as usize)
    }
}

/// Common memory constraints for testing
pub mod constraints {
    use super::*;

    /// Small test memory constraint (100MB or 10x input)
    pub const SMALL: MemoryConstraint = MemoryConstraint {
        max_usage: 100 * 1024 * 1024, // 100 MB
        relative_to_input: 10.0,      // 10x input size
        warning_threshold: 0.8,       // 80% of limit
    };

    /// Medium test memory constraint (500MB or 5x input)
    pub const MEDIUM: MemoryConstraint = MemoryConstraint {
        max_usage: 500 * 1024 * 1024, // 500 MB
        relative_to_input: 5.0,       // 5x input size
        warning_threshold: 0.8,       // 80% of limit
    };

    /// Large test memory constraint (2GB or 3x input)
    pub const LARGE: MemoryConstraint = MemoryConstraint {
        max_usage: 2 * 1024 * 1024 * 1024, // 2 GB
        relative_to_input: 3.0,            // 3x input size
        warning_threshold: 0.9,            // 90% of limit
    };
}

/// Validate memory usage against constraints
pub fn validate_memory_usage(
    current_usage: usize,
    input_size: usize,
    constraint: &MemoryConstraint,
) -> (bool, String) {
    let max_allowed = constraint.max_allowed(input_size);

    if current_usage > max_allowed {
        (
            false,
            format!(
                "Memory usage {} exceeds limit {} (input: {})",
                format_bytes(current_usage),
                format_bytes(max_allowed),
                format_bytes(input_size)
            ),
        )
    } else if constraint.is_near_warning(current_usage, input_size) {
        (
            true,
            format!(
                "Warning: Memory usage {} is near limit {} (input: {})",
                format_bytes(current_usage),
                format_bytes(max_allowed),
                format_bytes(input_size)
            ),
        )
    } else {
        (
            true,
            format!(
                "Memory usage {} is within limits (max: {}, input: {})",
                format_bytes(current_usage),
                format_bytes(max_allowed),
                format_bytes(input_size)
            ),
        )
    }
}

/// Format bytes in human readable format
pub fn format_bytes(bytes: usize) -> String {
    const UNITS: &[(&str, u64)] = &[
        ("B", 1),
        ("KB", 1024),
        ("MB", 1_048_576),
        ("GB", 1_073_741_824),
    ];

    let bytes = bytes as u64;

    for (i, &(unit, size)) in UNITS.iter().enumerate() {
        if bytes < size * 1024 || i == UNITS.len() - 1 {
            return if i == 0 {
                format!("{} {}", bytes, unit)
            } else {
                format!("{:.2} {}", bytes as f64 / size as f64, unit)
            };
        }
    }

    // Default case (should never reach here)
    format!("{} GB", bytes as f64 / UNITS.last().unwrap().1 as f64)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_memory_monitor() {
        let mut monitor = MemoryMonitor::new();

        // Initial stats
        let initial = monitor.current_stats();
        assert!(initial.current_usage > 0);

        // Recording should update peak if necessary
        monitor.record_reading();
        let after = monitor.current_stats();
        assert!(after.timestamp >= initial.timestamp);
    }

    #[test]
    fn test_memory_constraints() {
        let constraint = constraints::SMALL;

        // Test within limits (9MB is well below 80MB threshold, so should NOT be near warning)
        assert!(!constraint.is_near_warning(9 * 1024 * 1024, 10 * 1024 * 1024));

        // Test near warning threshold (81MB > 80MB threshold)
        assert!(constraint.is_near_warning(81 * 1024 * 1024, 10 * 1024 * 1024));

        // Test exceeding limit
        assert!(constraint.is_exceeded(200 * 1024 * 1024, 10 * 1024 * 1024));

        // Test max allowed calculation
        assert_eq!(constraint.max_allowed(10 * 1024 * 1024), 100 * 1024 * 1024);
        assert_eq!(constraint.max_allowed(50 * 1024 * 1024), 500 * 1024 * 1024);
        // 10x
    }

    #[test]
    fn test_format_bytes() {
        assert_eq!(format_bytes(1024), "1.00 KB");
        assert_eq!(format_bytes(1536), "1.50 KB");
        assert_eq!(format_bytes(1024 * 1024), "1.00 MB");
        assert_eq!(format_bytes(1536 * 1024), "1.50 MB");
        assert_eq!(format_bytes(1024 * 1024 * 1024), "1.00 GB");
    }
}
