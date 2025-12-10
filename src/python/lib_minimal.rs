//! Minimal RustKmer Python bindings for testing
//! This is a simplified version to get basic PyO3 functionality working

use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

/// Simple test function to verify Python bindings are working
#[pyfunction]
fn hello_world(name: Option<String>) -> PyResult<String> {
    let name = name.unwrap_or_else(|| "World".to_string());
    Ok(format!("Hello, {}! RustKmer Python bindings are working!", name))
}

/// Get information about the RustKmer library
#[pyfunction]
fn get_info() -> PyResult<String> {
    Ok(format!("RustKmer v{} - High-performance k-mer counting in Rust with Python bindings",
               env!("CARGO_PKG_VERSION")))
}

/// Python module for RustKmer (minimal version)
#[pymodule]
fn _rustkmer(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Version information
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;

    // Functions
    m.add_function(wrap_pyfunction!(hello_world, m)?)?;
    m.add_function(wrap_pyfunction!(get_info, m)?)?;

    Ok(())
}