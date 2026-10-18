<!-- generated-by: gsd-doc-writer -->
# Exceptions

**Module**: `pyrustkmer` (crate `rustkmer-pyo3`, `errors` module)

## Overview

Error handling for RustKmer PyO3 bindings.

This module provides the custom Python exception base class `RustKmerError`
and the error conversion between Rust error types and Python exceptions.
Wrapper methods across the crate raise standard Python exceptions
(`ValueError`, `FileNotFoundError`, `RuntimeError`, `PermissionError`) with
descriptive messages; `RustKmerError` carries a structured
`message` + `error_type` pair for programmatic handling.

The class is registered on the `pyrustkmer` module in `pyo3/src/lib.rs`
via `m.add_class::<RustKmerError>()`.

## API Reference

### Structs

#### RustKmerError

```rust
#[pyclass]
pub struct RustKmerError {
    pub message: String,
    pub error_type: String,
}
```

Custom exception base class for all RustKmer errors, exposed to Python as
`pyrustkmer.RustKmerError`.

### Fns

#### new

```rust
#[new]
fn new(message: String, error_type: String) -> Self {
```

Create a new error. Python constructor: `RustKmerError(message, error_type)`.

#### \_\_str\_\_

```rust
fn __str__(&self) -> String {
```

Returns `"{error_type}: {message}"`.

#### \_\_repr\_\_

```rust
fn __repr__(&self) -> String {
```

Returns `RustKmerError('{error_type}', '{message}')`.

#### message (property)

```rust
#[getter]
fn message(&self) -> &str {
```

The human-readable error message.

#### error_type (property)

```rust
#[getter]
fn error_type(&self) -> &str {
```

The error category string.

---

*Source: [`errors.rs`](../../../pyo3/src/errors.rs)*
