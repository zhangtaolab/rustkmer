# Exceptions

**Module**: `rustkmer::python::exceptions`

## Overview

Exception classes for RustKmer Python bindings
This module defines custom exception classes that provide better error handling
and more specific error information for Python users.

## API Reference

### Fns

#### register_exceptions

```rust
pub fn register_exceptions(m: &Bound<'_, PyModule>) -> PyResult<()> {
```

Register all exception classes with the Python module

---

*Source: [`exceptions.rs`](../../../python/exceptions.rs)*