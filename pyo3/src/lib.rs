//! Enhanced PyO3 binding for RustKmer with complete query functionality
use pyo3::prelude::*;

// Module declarations
mod database;
mod errors;
mod fuzzy_query;
mod kmer_counter;
mod prefix_query;
mod utils;

// Re-export types for convenience
pub use database::{LoadMode, PyDatabase, PyDatabaseStats, PyPrefixQueryResult, PyQueryResult};
pub use errors::RustKmerError;
pub use fuzzy_query::{PyFuzzyMatch, PyFuzzyQuery, PyFuzzyResult};
pub use kmer_counter::{PyCounterStats, PyKmerCounter};
pub use prefix_query::{PyExtendedPrefixQuery, PyPrefixQuery, PyPrefixQueryMetrics};

/// Python module
#[pymodule]
fn pyrustkmer(m: &Bound<'_, PyModule>) -> PyResult<()> {
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
