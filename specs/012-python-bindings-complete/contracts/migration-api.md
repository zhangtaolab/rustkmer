# API Contract: PyO3 Migration Interface

**Version**: 0.27.2
**Date**: 2025-12-09

## Migration API Endpoints

### 1. Type Conversion API

#### Convert to Python Object
```rust
// Old API (deprecated)
fn convert_to_python<T: IntoPy<PyObject>>(value: T, py: Python) -> PyObject

// New API (PyO3 0.27.2)
fn convert_to_python<T: IntoPyObject>(value: T, py: Python<'_>) -> PyResult<Bound<'_, PyAny>>
```

**Parameters**:
- `value: T` - Rust value to convert
- `py: Python<'_>` - Python GIL token

**Returns**:
- Old: `PyObject` - Direct Python object
- New: `PyResult<Bound<'_, PyAny>>` - Result-wrapped bound object

**Error Handling**:
- Old: Panic on conversion error
- New: Returns Err on conversion failure

### 2. Dictionary Creation API

#### Create Python Dictionary
```rust
// Old API
fn create_dict(items: Vec<(String, PyObject)>, py: Python) -> PyObject

// New API
fn create_dict(items: Vec<(String, Bound<'_, PyAny>>) -> PyResult<Bound<'_, PyDict>>
```

**Alternative using set_item**:
```rust
// New pattern (recommended)
fn create_dict(py: Python<'_>) -> PyResult<Bound<'_, PyDict>> {
    let dict = pyo3::types::PyDict::new(py);
    dict.set_item("key", value)?;
    Ok(dict)
}
```

### 3. Module Registration API

#### Register PyO3 Module
```rust
// Old API
#[pymodule]
fn rustkmer(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<MyClass>()?;
    Ok(())
}

// New API
#[pymodule]
fn rustkmer(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<MyClass>()?;
    Ok(())
}
```

### 4. Class Definition API

#### Define Python Class with Thread Safety
```rust
// Requirement for PyO3 0.25+
#[pyclass]
#[derive(Clone)] // Must be Send + Sync
struct MyClass {
    data: Arc<RwLock<Data>>,
}

// Alternative for non-thread-safe classes
#[pyclass(unsendable)]
struct NotThreadSafe {
    data: RefCell<Data>,
}
```

## Migration Patterns

### Pattern 1: Simple Type Conversion
```rust
// Before
fn get_string() -> PyObject {
    Python::with_gil(|py| "hello".into_py(py))
}

// After
fn get_string() -> PyResult<Bound<'_, PyAny>> {
    Python::with_gil(|py| "hello".into_pyobject(py))
}
```

### Pattern 2: Dictionary Conversion
```rust
// Before
fn get_metadata(&self) -> HashMap<String, PyObject> {
    let mut dict = HashMap::new();
    dict.insert("key".to_string(), value.into_py(py));
    dict
}

// After
fn get_metadata(&self, py: Python<'_>) -> PyResult<HashMap<String, Bound<'_, PyAny>>> {
    let dict = pyo3::types::PyDict::new(py);
    dict.set_item("key", value)?;
    // Convert to HashMap if needed
    Ok(dict.into())
}
```

### Pattern 3: List Conversion
```rust
// Before
fn get_list(items: Vec<String>) -> PyObject {
    Python::with_gil(|py| {
        items.into_py(py)
    })
}

// After
fn get_list(items: Vec<String>) -> PyResult<Bound<'_, PyList>> {
    Python::with_gil(|py| {
        let list = pyo3::types::PyList::new(py, items);
        Ok(list)
    })
}
```

## Error Handling Contracts

### Conversion Error Types
```rust
// New error handling required
enum ConversionError {
    InvalidType(String),
    OutOfRange(String),
    Custom(String),
}

impl From<ConversionError> for PyErr {
    fn from(err: ConversionError) -> PyErr {
        PyValueError::new_err(err.to_string())
    }
}
```

### Error Propagation
```rust
// Required for all conversions
fn safe_convert(value: Value) -> PyResult<Bound<'_, PyAny>> {
    value.into_pyobject(py).map_err(|e| {
        PyValueError::new_err(format!("Conversion failed: {}", e))
    })
}
```

## Performance Requirements

### Conversion Performance
- Must not exceed 5% performance overhead
- Memory allocation must be minimized
- GIL hold time must be minimized

### Batch Operations
```rust
// Recommended for multiple conversions
fn batch_convert(items: Vec<Value>) -> PyResult<Vec<Bound<'_, PyAny>>> {
    Python::with_gil(|py| {
        items.into_iter()
            .map(|item| item.into_pyobject(py))
            .collect()
    })
}
```

## Validation Rules

### Pre-migration Validation
1. Audit all `IntoPy` usage
2. Identify all `PyObject` return types
3. Check thread safety of all `#[pyclass]` types
4. Verify error handling patterns

### Post-migration Validation
1. All tests must pass
2. Performance benchmarks must meet requirements
3. Memory usage must remain stable
4. Python API compatibility must be maintained

## Backward Compatibility

### Compatibility Guarantees
1. Python API surface remains unchanged
2. Method signatures maintain compatibility
3. Error messages remain informative
4. Performance characteristics preserved

### Migration Support
- Provide fallback implementations where possible
- Document all breaking changes
- Offer migration guide with examples
- Support both versions during transition period