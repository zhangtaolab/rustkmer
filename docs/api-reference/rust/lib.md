<!-- generated-by: gsd-doc-writer -->
# Lib

**Module**: `pyrustkmer` (crate root of `rustkmer-pyo3`)

## Overview

Enhanced PyO3 binding for RustKmer with complete query functionality.

This crate root provides the `pyrustkmer` Python extension module. It
declares the binding submodules, re-exports all wrapper types for
convenience, and registers them on the Python module so they are accessible
as `pyrustkmer.PyDatabase`, `pyrustkmer.PyCounter`, etc. It includes
functionality for:

- K-mer counting with `PyCounter`
- Database operations with `PyDatabase`
- Fuzzy querying with `PyFuzzyQuery`
- Prefix querying with `PyPrefixQuery` and `PyExtendedPrefixQuery`
- Formatting utilities with `PyFormatter`

The bindings are a separate crate from the `rustkmer` core library: the
`rustkmer-pyo3` crate (`pyo3/Cargo.toml`, `crate-type = ["cdylib"]`, lib
name `pyrustkmer`) depends on `rustkmer` by path and is built into a
Python wheel with maturin.

## API Reference

### Module Layout

```rust
mod counter;       // PyCounter, PyCounterStats
mod database;      // PyDatabase, LoadMode, PyQueryResult, PyPrefixQueryResult, PyDatabaseStats
mod errors;        // RustKmerError
mod formatter;     // PyFormatter
mod fuzzy_query;   // PyFuzzyQuery, PyFuzzyResult, PyFuzzyMatch
mod prefix_query;  // PyPrefixQuery, PyExtendedPrefixQuery, PyPrefixQueryMetrics
mod utils;
```

### Re-exports

```rust
pub use counter::{PyCounter, PyCounterStats};
pub use database::{LoadMode, PyDatabase, PyDatabaseStats, PyPrefixQueryResult, PyQueryResult};
pub use errors::RustKmerError;
pub use formatter::PyFormatter;
pub use fuzzy_query::{PyFuzzyMatch, PyFuzzyQuery, PyFuzzyResult};
pub use prefix_query::{PyExtendedPrefixQuery, PyPrefixQuery, PyPrefixQueryMetrics};
```

All wrapper types are re-exported at the crate root so Python users can
import everything directly from `pyrustkmer`.

### Fns

#### pyrustkmer

```rust
#[pymodule]
fn pyrustkmer(m: &Bound<'_, PyModule>) -> PyResult<()> {
```

Python module entry point for the `pyrustkmer` package. Registers all
`#[pyclass]` types on the module:

| Class | Defined in |
|-------|------------|
| `PyDatabase`, `PyDatabaseStats`, `PyQueryResult`, `PyPrefixQueryResult`, `LoadMode` | `database` |
| `PyCounter`, `PyCounterStats` | `counter` |
| `PyFuzzyQuery`, `PyFuzzyResult`, `PyFuzzyMatch` | `fuzzy_query` |
| `PyPrefixQuery`, `PyExtendedPrefixQuery`, `PyPrefixQueryMetrics` | `prefix_query` |
| `PyFormatter` | `formatter` |
| `RustKmerError` | `errors` |

```python
import pyrustkmer

db = pyrustkmer.PyDatabase("output.rkdb", pyrustkmer.LoadMode.Preload)
counter = pyrustkmer.PyCounter(21, canonical=True)
```

---

*Source: [`lib.rs`](../../../pyo3/src/lib.rs)*
