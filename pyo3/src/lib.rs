//! Enhanced PyO3 binding for RustKmer with complete query functionality
use pyo3::prelude::*;

// Module declarations
mod database;
mod errors;
mod fuzzy_query;
mod kmer_counter;
mod utils;
mod prefix_query;

// Re-export types for convenience
pub use database::{PyDatabase, PyDatabaseStats, PyQueryResult, PyPrefixQueryResult, LoadMode};
pub use errors::RustKmerError;
pub use fuzzy_query::{PyFuzzyQuery, PyFuzzyResult, PyFuzzyMatch};
pub use kmer_counter::{PyKmerCounter, PyCounterStats};
pub use prefix_query::{PyPrefixQuery, PyExtendedPrefixQuery, PyPrefixQueryMetrics};

/// Python module
#[pymodule]
fn rustkmer_pyo3(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyDatabase>()?;
    m.add_class::<PyDatabaseStats>()?;
    m.add_class::<PyQueryResult>()?;
    m.add_class::<PyPrefixQueryResult>()?;
    m.add_class::<LoadMode>()?;
    m.add_class::<PyKmerCounter>()?;
    m.add_class::<PyCounterStats>()?;
    m.add_class::<PyFuzzyQuery>()?;
    m.add_class::<PyFuzzyResult>()?;
    m.add_class::<PyFuzzyMatch>()?;
    m.add_class::<PyPrefixQuery>()?;
    m.add_class::<PyExtendedPrefixQuery>()?;
    m.add_class::<PyPrefixQueryMetrics>()?;
    m.add_class::<RustKmerError>()?;
    Ok(())
}