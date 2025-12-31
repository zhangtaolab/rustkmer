//! Utility functions for RustKmer PyO3 bindings
//!
//! This module provides helper functions for common operations
//! like validation, conversion, and data manipulation.

use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;

/// Validate k-mer sequence for Python API
pub fn validate_kmer(kmer: &str, _k_size: Option<usize>) -> PyResult<String> {
    if kmer.is_empty() {
        return Err(PyErr::new::<PyValueError, _>("K-mer cannot be empty"));
    }
    
    Ok(kmer.to_uppercase())
}

/// Convert Python string to Rust String
pub fn py_string_to_string(py_str: &Bound<'_, pyo3::types::PyString>) -> PyResult<String> {
    Ok(py_str.to_string_lossy().to_string())
}

/// Convert Rust Vec to Python list
pub fn string_vec_to_py_list(strings: Vec<String>) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        let py_list = pyo3::types::PyList::new_bound(py, &[] as &[&str]);
        
        for s in strings {
            let py_string = pyo3::types::PyString::new_bound(py, &s);
            py_list.append(&py_string)?;
        }
        
        Ok(py_list.into())
    })
}