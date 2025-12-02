//! Exception classes for RustKmer Python bindings
//!
//! This module defines custom exception classes that provide better error handling
//! and more specific error information for Python users.

use pyo3::create_exception;
use pyo3::exceptions::PyException;
use pyo3::prelude::*;

// Create custom exception classes
create_exception!(rustkmer_python, RustKmerError, PyException);
create_exception!(rustkmer_python, KmerError, RustKmerError);
create_exception!(rustkmer_python, DatabaseError, RustKmerError);
create_exception!(rustkmer_python, FuzzyQueryError, RustKmerError);
create_exception!(rustkmer_python, SequenceError, RustKmerError);
create_exception!(rustkmer_python, ConfigurationError, RustKmerError);
create_exception!(rustkmer_python, ValidationError, RustKmerError);

/// Register all exception classes with the Python module
pub fn register_exceptions(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("RustKmerError", m.py().get_type::<RustKmerError>())?;
    m.add("KmerError", m.py().get_type::<KmerError>())?;
    m.add("DatabaseError", m.py().get_type::<DatabaseError>())?;
    m.add("FuzzyQueryError", m.py().get_type::<FuzzyQueryError>())?;
    m.add("SequenceError", m.py().get_type::<SequenceError>())?;
    m.add("ConfigurationError", m.py().get_type::<ConfigurationError>())?;
    m.add("ValidationError", m.py().get_type::<ValidationError>())?;

    Ok(())
}