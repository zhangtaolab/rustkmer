#![deny(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]
//! Enhanced PyO3 binding for RustKmer with complete query functionality
//!
//! This module provides Python bindings for RustKmer, a high-performance
//! k-mer counting and querying library. It includes functionality for:
//! - K-mer counting with PyCounter
//! - Database operations with PyDatabase
//! - Fuzzy querying with PyFuzzyQuery
//! - Prefix querying with PyPrefixQuery and PyExtendedPrefixQuery
//! - Formatting utilities with PyFormatter
//!
//! All types are exported at the module level for convenience.

use pyo3::prelude::*;

// Module declarations
mod counter;
mod database;
mod errors;
mod formatter;
mod fuzzy_query;
mod prefix_query;
mod utils;

// Re-export types for convenience
pub use counter::{PyCounter, PyCounterStats};
pub use database::{LoadMode, PyDatabase, PyDatabaseStats, PyPrefixQueryResult, PyQueryResult};
pub use errors::RustKmerError;
pub use formatter::PyFormatter;
pub use fuzzy_query::{PyFuzzyMatch, PyFuzzyQuery, PyFuzzyResult};
pub use prefix_query::{PyExtendedPrefixQuery, PyPrefixQuery, PyPrefixQueryMetrics};

/// Python module for RustKmer
///
/// This module is the entry point for the pyrustkmer Python package.
/// It exposes all high-performance Rust functionality to Python.
#[pymodule]
fn pyrustkmer(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyDatabase>()?;
    m.add_class::<PyDatabaseStats>()?;
    m.add_class::<PyQueryResult>()?;
    m.add_class::<PyPrefixQueryResult>()?;
    m.add_class::<LoadMode>()?;
    m.add_class::<PyCounter>()?;
    m.add_class::<PyCounterStats>()?;
    m.add_class::<PyFuzzyQuery>()?;
    m.add_class::<PyFuzzyResult>()?;
    m.add_class::<PyFuzzyMatch>()?;
    m.add_class::<PyPrefixQuery>()?;
    m.add_class::<PyExtendedPrefixQuery>()?;
    m.add_class::<PyPrefixQueryMetrics>()?;
    m.add_class::<PyFormatter>()?;
    m.add_class::<RustKmerError>()?;
    Ok(())
}
