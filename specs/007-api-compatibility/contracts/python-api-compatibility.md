# Python API Compatibility Contract

**Version**: 1.0
**Date**: 2025-12-02
**Standard**: Rust CLI (Authoritative Reference)

## Contract Overview

This contract defines the compatibility requirements between Python API and Rust CLI implementations. All Python API behaviors must exactly match the Rust CLI reference implementation.

## Core Requirements

### 1. Database Format Contract

**Requirement**: Python API must create databases that are bit-for-bit identical to Rust CLI databases for identical inputs.

**Validation**:
```python
# Test: Identical database creation
rust_db = create_with_rust_cli(input_files, k=21, canonical=True)
python_db = create_with_python_api(input_files, k=21, canonical=True)
assert files_are_identical(rust_db, python_db)  # Must pass
```

**Header Structure**: Must exactly match `DatabaseHeader` from CLI implementation
- Magic: `[82, 75, 68, 66]` ("RKDB")
- Version: `1`
- Byte order: LittleEndian
- All fields must match CLI values

### 2. Query Results Contract

**Requirement**: Query results must be 100% identical between Python API and CLI for the same database.

**Validation**:
```python
# Test: Query result consistency
for kmer in test_kmers:
    cli_result = rust_cli_query(database, kmer)
    py_result = python_api_query(database, kmer)
    assert cli_result == py_result  # Must pass exactly
```

**Response Format**:
```python
{
    "found": bool,           # Must match CLI
    "count": u32,           # Must match CLI
    "metadata": u32,        # Must match CLI
    "query_time_ms": f64    # Within 10% of CLI time
}
```

### 3. Fuzzy Query Contract

**Requirement**: Fuzzy query results must be identical across implementations for the same patterns.

**Parameters**:
- `pattern`: String with N wildcards (must match CLI behavior)
- `max_mutations`: 1-2 (must match CLI `--mutations` parameter)
- `max_results`: Must match CLI default behavior

**Validation**:
```python
# Test: Fuzzy query consistency
patterns = ["ACGTN", "AANN", "ACGNNT"]
for pattern in patterns:
    cli_results = rust_cli_fuzzy_query(database, pattern, max_mutations=1)
    py_results = python_fuzzy_query(database, pattern, max_mutations=1)
    assert cli_results == py_results  # Must pass exactly
```

### 4. Error Handling Contract

**Requirement**: Error messages and error codes must be consistent across implementations.

**Error Categories**:
- Invalid k-mer size
- File not found
- Corrupted database
- Permission denied

**Validation**:
```python
# Test: Error consistency
for invalid_input in invalid_inputs:
    try:
        rust_cli_query(database, invalid_input)
    except Exception as e_cli:
        cli_error = str(e_cli)

    try:
        python_api_query(database, invalid_input)
    except Exception as e_py:
        py_error = str(e_py)

    assert normalize_error_message(cli_error) == normalize_error_message(py_error)
```

## Performance Contracts

### 1. Query Performance Contract

**Requirement**: Python API query performance must be within 10% of CLI performance.

**Benchmarks**:
```python
# Performance validation test
import time

def benchmark_query(database, test_kmers):
    start_time = time.time()
    for kmer in test_kmers:
        python_api_query(database, kmer)
    py_time = time.time() - start_time

    start_time = time.time()
    for kmer in test_kmers:
        rust_cli_query(database, kmer)
    cli_time = time.time() - start_time

    overhead = (py_time - cli_time) / cli_time
    assert overhead < 0.10  # Must be < 10%
```

### 2. Memory Usage Contract

**Requirement**: Memory usage patterns must be predictable and efficient.

**Memory Limits**:
- Small databases (<100MB): Full loading acceptable
- Medium databases (100MB-10GB): Memory-mapped access required
- Large databases (>10GB): Streaming with caching

## Feature Parity Contract

### Required CLI Features in Python API

1. **Counting Features**:
   - Min/max count thresholds (`-L`, `-U` CLI flags)
   - Canonical k-mer processing
   - Directory processing
   - Recursive file search

2. **Query Features**:
   - Individual k-mer queries
   - Batch k-mer queries
   - Sequence file queries
   - Interactive mode equivalent

3. **Fuzzy Query Features**:
   - Wildcard pattern matching (N = any base)
   - Mutation tolerance (1-2 mutations)
   - Result limiting and sorting

4. **Output Features**:
   - Human-readable output format
   - Machine-readable format (JSON)
   - Progress reporting for long operations

## Testing Contracts

### 1. Unit Test Contract

Each Python API function must have corresponding unit tests that validate:
- Correct behavior for valid inputs
- Proper error handling for invalid inputs
- Performance characteristics
- Memory usage patterns

### 2. Integration Test Contract

End-to-end tests must validate:
- Database creation consistency
- Cross-platform query compatibility
- File format interoperability
- Error message consistency

### 3. Regression Test Contract

All fixes must include regression tests that prevent:
- Performance regressions
- Format compatibility issues
- Behavioral deviations from CLI standard

## Compliance Validation

### Automated Checks

1. **Format Validation**: Binary comparison of generated databases
2. **Behavior Validation**: Result comparison across implementations
3. **Performance Validation**: Benchmark comparison within 10% threshold
4. **Feature Validation**: Feature parity checklist completion

### Manual Validation

1. **User Experience Testing**: Real-world workflow validation
2. **Documentation Validation**: Example and tutorial accuracy
3. **Edge Case Testing**: Boundary condition and error scenario validation

## Enforcement

### Contract Violations

Any violation of this contract must be addressed before feature completion:
- **Critical Violations**: Block feature completion
- **Major Violations**: Require immediate fix
- **Minor Violations**: Document and schedule resolution

### Change Management

Changes to this contract require:
- Impact analysis on existing implementations
- Update to validation tests
- Documentation updates
- Stakeholder approval

**Sign-off**: This contract represents the binding agreement between Python API implementation and Rust CLI standard compliance.