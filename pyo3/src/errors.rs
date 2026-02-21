//! Error handling for RustKmer PyO3 bindings
//!
//! This module provides custom Python exceptions and error conversion
//! between Rust error types and Python exceptions.

use pyo3::prelude::*;

/// Custom exception base class for all RustKmer errors
#[pyclass]
pub struct RustKmerError {
    pub message: String,
    pub error_type: String,
}

#[pymethods]
impl RustKmerError {
    #[new]
    fn new(message: String, error_type: String) -> Self {
        Self {
            message,
            error_type,
        }
    }

    fn __str__(&self) -> String {
        format!("{}: {}", self.error_type, self.message)
    }

    fn __repr__(&self) -> String {
        format!("RustKmerError('{}', '{}')", self.error_type, self.message)
    }

    #[getter]
    fn message(&self) -> &str {
        &self.message
    }

    #[getter]
    fn error_type(&self) -> &str {
        &self.error_type
    }
}

