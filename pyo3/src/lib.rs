//! Enhanced PyO3 binding for RustKmer with complete query functionality
use pyo3::prelude::*;

// Module declarations
mod database;

// Re-export types for convenience
pub use database::{PyDatabase, PyDatabaseStats, PyQueryResult};

/// Python module
#[pymodule]
fn rustkmer_pyo3(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyDatabase>()?;
    m.add_class::<PyDatabaseStats>()?;
    m.add_class::<PyQueryResult>()?;
    Ok(())
}