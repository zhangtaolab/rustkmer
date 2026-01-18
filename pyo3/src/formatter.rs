//! Formatting utilities for PyO3 result types
//!
//! This module provides formatted output methods for converting PyO3 result types
//! into various formats (JSON, CSV, TSV, and table formats).

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

/// Serde-compatible wrapper for PyQueryResult
#[derive(Debug, Clone, Serialize, Deserialize)]
struct QueryResultSerializable {
    kmer: String,
    count: u32,
    found: bool,
}

impl From<&crate::database::PyQueryResult> for QueryResultSerializable {
    fn from(result: &crate::database::PyQueryResult) -> Self {
        Self {
            kmer: result.kmer.clone(),
            count: result.count,
            found: result.found,
        }
    }
}

/// Serde-compatible wrapper for PyPrefixQueryResult
#[derive(Debug, Clone, Serialize, Deserialize)]
struct PrefixQueryResultSerializable {
    matches: Vec<(String, String)>,
    total_matches: usize,
    start_index: usize,
    end_index: usize,
    block_size: usize,
    is_sorted: bool,
    query_time_ms: u64,
}

impl From<&crate::database::PyPrefixQueryResult> for PrefixQueryResultSerializable {
    fn from(result: &crate::database::PyPrefixQueryResult) -> Self {
        let matches_vec: Vec<(String, String)> = result
            .matches
            .iter()
            .map(|(k, v)| (k.clone(), v.clone()))
            .collect();

        Self {
            matches: matches_vec,
            total_matches: result.total_matches,
            start_index: result.start_index,
            end_index: result.end_index,
            block_size: result.block_size,
            is_sorted: result.is_sorted,
            query_time_ms: result.query_time_ms,
        }
    }
}

/// Serde-compatible wrapper for PyFuzzyMatch
#[derive(Debug, Clone, Serialize, Deserialize)]
struct FuzzyMatchSerializable {
    kmer: String,
    count: u64,
    distance: Option<usize>,
    match_type: String,
    mutation_positions: Vec<usize>,
}

impl From<&crate::fuzzy_query::PyFuzzyMatch> for FuzzyMatchSerializable {
    fn from(match_item: &crate::fuzzy_query::PyFuzzyMatch) -> Self {
        Self {
            kmer: match_item.kmer.clone(),
            count: match_item.count,
            distance: match_item.distance,
            match_type: match_item.match_type.clone(),
            mutation_positions: match_item.mutation_positions.clone(),
        }
    }
}

/// Serde-compatible wrapper for PyFuzzyResult
#[derive(Debug, Clone, Serialize, Deserialize)]
struct FuzzyResultSerializable {
    query_kmer: String,
    exact_match: Option<FuzzyMatchSerializable>,
    matches: Vec<FuzzyMatchSerializable>,
    total_matches: usize,
    mutation_tolerance: u32,
    query_time_ms: u64,
    has_position_mutations: bool,
}

impl From<&crate::fuzzy_query::PyFuzzyResult> for FuzzyResultSerializable {
    fn from(result: &crate::fuzzy_query::PyFuzzyResult) -> Self {
        Self {
            query_kmer: result.query_kmer.clone(),
            exact_match: result
                .exact_match
                .as_ref()
                .map(FuzzyMatchSerializable::from),
            matches: result
                .matches
                .iter()
                .map(FuzzyMatchSerializable::from)
                .collect(),
            total_matches: result.total_matches,
            mutation_tolerance: result.mutation_tolerance,
            query_time_ms: result.query_time_ms,
            has_position_mutations: result.has_position_mutations,
        }
    }
}

/// Serde-compatible wrapper for PyDatabaseStats
#[derive(Debug, Clone, Serialize, Deserialize)]
struct DatabaseStatsSerializable {
    kmer_size: usize,
    total_kmers: u64,
    unique_kmers: u64,
    file_size: u64,
    is_sorted: bool,
    canonical: bool,
}

impl From<&crate::database::PyDatabaseStats> for DatabaseStatsSerializable {
    fn from(stats: &crate::database::PyDatabaseStats) -> Self {
        Self {
            kmer_size: stats.kmer_size,
            total_kmers: stats.total_kmers,
            unique_kmers: stats.unique_kmers,
            file_size: stats.file_size,
            is_sorted: stats.is_sorted,
            canonical: stats.canonical,
        }
    }
}

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
    /// Create a new formatter
    #[new]
    #[pyo3(signature = (canonical=false, format_style="compact".to_string()))]
    fn new(canonical: bool, format_style: String) -> Self {
        Self {
            canonical,
            format_style,
        }
    }

    /// Format a k-mer string
    fn format_kmer(&self, kmer: &Bound<'_, pyo3::types::PyString>) -> PyResult<String> {
        let kmer_str = kmer.to_string();
        Ok(if self.canonical {
            format_kmer_canonical(&kmer_str)
        } else {
            kmer_str
        })
    }

    /// Format a count result
    fn format_count(&self, kmer: &str, count: u64) -> PyResult<String> {
        match self.format_style.as_str() {
            "compact" => Ok(format!("{}:{}", kmer, count)),
            "verbose" => Ok(format!("k-mer: {}, count: {}", kmer, count)),
            "json" => Ok(format!(r#"{{"kmer": "{}", "count": {}}}"#, kmer, count)),
            _ => Ok(format!("{}:{}", kmer, count)),
        }
    }

    /// Get whether canonical mode is enabled
    #[getter]
    fn canonical(&self) -> bool {
        self.canonical
    }

    /// Get the current format style
    #[getter]
    fn format_style(&self) -> String {
        self.format_style.clone()
    }

    /// Set the format style
    #[setter]
    fn set_format_style(&mut self, style: String) {
        self.format_style = style;
    }
}

/// Format a k-mer in canonical representation (reverse complement if needed)
fn format_kmer_canonical(kmer: &str) -> String {
    let revcomp = reverse_complement(kmer);
    if kmer.to_string() < revcomp {
        kmer.to_string()
    } else {
        revcomp
    }
}

/// Compute the reverse complement of a DNA sequence
fn reverse_complement(seq: &str) -> String {
    seq.chars()
        .rev()
        .map(|c| match c {
            'A' | 'a' => 'T',
            'T' | 't' => 'A',
            'C' | 'c' => 'G',
            'G' | 'g' => 'C',
            _ => c,
        })
        .collect()
}
