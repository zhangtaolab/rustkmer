//! Formatting utilities for PyO3 result types
//!
//! This module provides formatted output methods for converting PyO3 result types
//! into various formats (JSON, CSV, TSV, and table formats).

use pyo3::prelude::*;

// ============================================================================
// PyFormatter class for backward compatibility
// ============================================================================

/// Formatter for k-mer data and query results (legacy, for backward compatibility)
///
/// Note: Result types now have built-in formatting methods (to_json, to_csv, to_tsv, to_dict, to_table)
#[pyclass]
pub struct PyFormatter {
    /// Whether to use canonical representation
    canonical: bool,
    /// Output format style (e.g., "compact", "verbose", "json")
    format_style: String,
}

#[pymethods]
impl PyFormatter {
    #[new]
    fn new(canonical: bool, format_style: String) -> Self {
        Self {
            canonical,
            format_style,
        }
    }

    /// Format a k-mer string
    #[pyo3(signature = (kmer))]
    fn format_kmer(&self, kmer: &str) -> String {
        if self.canonical {
            // Return canonical form (lowercase)
            kmer.to_uppercase()
        } else {
            kmer.to_string()
        }
    }

    /// Format a k-mer count result
    #[pyo3(signature = (count))]
    fn format_count(&self, count: u64) -> String {
        match self.format_style.as_str() {
            "json" => format!(r#"{{"count": {}}}"#, count),
            "verbose" => format!("K-mer count: {}", count),
            _ => count.to_string(), // compact
        }
    }

    /// Get canonical mode
    #[getter]
    fn canonical(&self) -> bool {
        self.canonical
    }

    /// Set canonical mode
    #[setter]
    fn set_canonical(&mut self, value: bool) {
        self.canonical = value;
    }

    /// Get format style
    #[getter]
    fn format_style(&self) -> String {
        self.format_style.clone()
    }

    /// Set format style
    #[setter]
    fn set_format_style(&mut self, value: String) {
        self.format_style = value;
    }
}
