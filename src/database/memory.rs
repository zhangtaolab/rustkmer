//! Memory usage monitoring utilities

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

/// Format bytes in human readable format
pub fn format_bytes(bytes: usize) -> String {
    const UNITS: &[(&str, u64)] = &[
        ("B", 1),
        ("KB", 1024),
        ("MB", 1_048_576),
        ("GB", 1_073_741_824),
    ];

    for (i, &(unit, size)) in UNITS.iter().enumerate() {
        if bytes < (size * 1024) as usize || i == UNITS.len() - 1 {
            if i == 0 {
                return format!("{} {}", bytes, unit);
            } else {
                return format!("{:.2} {}", bytes as f64 / size as f64, unit);
            }
        } else {
            continue;
        }
    }
    unreachable!()
}
