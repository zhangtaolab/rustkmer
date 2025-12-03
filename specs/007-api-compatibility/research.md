# Research Report: RKDB Format and PyO3 Integration

**Generated**: 2025-12-02
**Purpose**: Foundation for implementing unified .rkdb database format in RustKmer Python API

## Decision: Use Identical RKDB Binary Format for Both CLI and Python API

**Rationale**:
- Ensures bit-for-bit compatibility and complete interoperability
- Eliminates format conversion overhead and complexity
- Maintains single source of truth for database specification
- Aligns with user requirement for "不能出现不兼容的情况"

**Alternatives Considered**:
- Directory format with conversion tools (rejected: adds complexity and conversion overhead)
- New unified format (rejected: breaks existing CLI compatibility)
- Dual format support (rejected: violates simplicity requirement)

---

## Research Findings

### 1. RKDB Binary Database Format Specification

**Source**: Analysis of RustKmer CLI source code in `/src/database/format.rs`

#### Header Format (42 bytes total)
```
Offset  Size    Field        Description
0      4       magic        "RKDB" magic number
4      2       version      Format version (1)
6      1       kmer_size    K-mer size (1-127)
7      1       padding      1 byte padding
8      2       padding      2 bytes padding
10     8       total_kmers  Total unique k-mers
18     1       flags        Bit flags (sorted=1, canonical=2)
19     7       padding      7 bytes padding
26     8       data_offset  Offset to data (always 42)
34     8       index_offset Offset to index (0 if none)
```

**Key Implementation Details**:
- Little-endian byte order throughout
- Fixed data_offset of 42 bytes
- Flags encode sorted (bit 0) and canonical (bit 1) properties
- Extensive padding for alignment requirements

#### K-mer Entry Format (12 bytes each)
```
Offset  Size    Field        Description
0      8       kmer         Packed 64-bit k-mer representation
8      4       count        32-bit count with endianness detection
```

**DNA Base Encoding** (2 bits per base):
- A = 00 (0)
- C = 01 (1)
- G = 10 (2)
- T = 11 (3)

### 2. Key Implementation Functions and Locations

**Core I/O Functions**:
- `DatabaseHeader::write_to()` in `/src/database/format.rs`
- `DatabaseHeader::read_from()` in `/src/database/format.rs`
- `KmerEntry::write_to()` in `/src/database/format.rs`
- `KmerEntry::read_from()` in `/src/database/format.rs`

**K-mer Processing**:
- `encode_kmer_bytes()` in `/src/kmer/encoding.rs`
- `canonical_kmer()` in `/src/kmer/operations.rs`
- `reverse_complement_bits()` in `/src/kmer/operations.rs`

**CLI Integration Points**:
- `output_binary_format()` in `/src/cli/commands/count.rs`
- `save_to_database()` in `/src/python/kmer_counter.rs`

### 3. PyO3 Integration Best Practices

**Error Handling Pattern**:
```rust
use thiserror::Error;
use pyo3::exceptions::{PyIOError, PyValueError};

#[derive(Error, Debug)]
pub enum DatabaseSerializationError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Invalid database format: {0}")]
    InvalidFormat(String),
}

impl From<DatabaseSerializationError> for PyErr {
    fn from(err: DatabaseSerializationError) -> PyErr {
        match err {
            DatabaseSerializationError::Io(e) => PyIOError::new_err(e.to_string()),
            DatabaseSerializationError::InvalidFormat(msg) => PyValueError::new_err(msg),
        }
    }
}
```

**GIL Release for Performance**:
```rust
use pyo3::prelude::*;

#[pyfunction]
fn save_database_rkdb(
    py: Python<'_>,
    kmer_counts: HashMap<String, u64>,
    file_path: &str,
    kmer_size: usize,
) -> PyResult<()> {
    // Release GIL for intensive computation
    py.allow_threads(|| {
        save_database_internal(kmer_counts, file_path, kmer_size)
    })?;
    Ok(())
}
```

**Memory Management for Large Files**:
```rust
use memmap2::MmapOptions;

#[pyclass]
pub struct PyRKDatabase {
    mmap: Option<Arc<MmapWrapper>>,
    header: DatabaseHeader,
}

// Use memory mapping for files >100MB
if file_size > 100_000_000 {
    self.mmap = Some(Arc::new(MmapWrapper::new(path)?));
}
```

### 4. Performance Considerations

**Critical Findings**:
- **Memory Mapping**: Essential for files >100MB to avoid loading entire database into memory
- **Batch Processing**: More efficient than individual k-mer operations
- **GIL Management**: Use `py.allow_threads()` for computationally intensive operations
- **Endianness Handling**: Little-endian primary format with automatic big-endian detection for count field

**Performance Targets**:
- Python API overhead <10% vs native CLI
- Sub-millisecond query performance for in-memory databases
- Memory usage <2x input file size

### 5. Implementation Strategy

#### Phase 1: Unify Database Format
1. **Modify Python API `save_to_database()`**:
   - Replace directory creation with single .rkdb file creation
   - Use CLI's `DatabaseHeader::write_to()` and `KmerEntry::write_to()`
   - Maintain identical encoding and byte order

2. **Update Python API `Database()` constructor**:
   - Read .rkdb files using CLI's `DatabaseHeader::read_from()`
   - Use memory mapping for large files
   - Maintain Python-idiomatic interface

#### Phase 2: Ensure Compatibility
1. **Binary Comparison Testing**:
   - Generate identical databases with both tools
   - Perform bit-for-bit file comparison
   - Validate query result consistency

2. **Performance Validation**:
   - Benchmark Python API vs CLI performance
   - Ensure <10% overhead requirement
   - Validate memory usage patterns

#### Phase 3: Integration and Testing
1. **Cross-Platform Query Testing**:
   - CLI queries Python-generated databases
   - Python queries CLI-generated databases
   - Validate identical results across all operations

2. **Fuzzy Query Compatibility**:
   - Ensure wildcard pattern matching works consistently
   - Validate mutation tolerance calculations
   - Test complex query scenarios

### 6. Code Changes Required

**Files to Modify**:
- `/src/python/kmer_counter.rs` - Update `save_to_database()` method
- `/src/python/database.rs` - Update `Database` implementation
- `/src/python/wrapper.rs` - Update PyO3 bindings if needed

**Key Changes**:
1. Replace directory-based storage with single .rkdb file creation
2. Use CLI serialization functions directly
3. Implement memory mapping for large database files
4. Add proper error handling with PyO3 exception conversion

### 7. Testing Strategy

**Unit Tests**:
- Database header serialization/deserialization
- K-mer encoding/decoding accuracy
- Error handling and edge cases

**Integration Tests**:
- CLI ↔ Python API compatibility
- Cross-platform query operations
- Large database performance

**Property-Based Tests**:
- Random k-mer sets produce identical databases
- Query results are consistent across platforms
- Format round-tripping maintains data integrity

## Next Steps

1. **Immediate**: Implement unified .rkdb format in Python API
2. **Validation**: Create comprehensive compatibility test suite
3. **Performance**: Optimize for <10% overhead requirement
4. **Documentation**: Update examples and usage guides

This research provides the complete technical foundation needed to implement unified database format compatibility between RustKmer CLI and Python API.