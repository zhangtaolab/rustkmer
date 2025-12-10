# Research Findings: Python Bindings Implementation

## PyO3 Best Practices for Bioinformatics Applications

### Decision: Use PyO3 0.27.2+ with Python 3.10+ Support
**Rationale**:
- Latest PyO3 version provides mature async support and better performance
- Python 3.10+ required for type hints and performance improvements
- Well-tested in production bioinformatics applications
- Good integration with maturin build system

**Alternatives considered**:
- PyO3 0.26.x: Lacks some performance optimizations
- cffi: More verbose, less type-safe
- ctypes: No compile-time safety

## Performance Optimization Strategies

### 1. Minimize Cross-Language Boundary Calls
- Implement bulk operations in Rust
- Batch database queries
- Process k-mers in Rust before returning to Python

### 2. Parallel Processing with Rayon
- Release GIL for CPU-intensive operations using `py.allow_threads()`
- Parallel k-mer counting and database operations
- Thread-safe memory-mapped database access

### 3. Memory-Mapped File Access
- Use memmap2 for large database files
- 100MB threshold for memory mapping decisions
- Adaptive caching based on access patterns

## Memory Management Patterns

### Efficient Data Structures
- u128 encoding for k-mers (up to 64 bases)
- Zero-copy operations where possible
- Buffer protocols for numpy integration

### Memory Safety
- Arc<RwLock<>> for thread-safe shared state
- Proper Send/Sync traits for concurrent access
- Memory pools for frequent allocations

## Error Handling

### Structured Error Definitions
```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum RustKmerError {
    #[error("Invalid k-mer sequence: {sequence}")]
    InvalidKmer { sequence: String },

    #[error("Database file corrupted: {file}")]
    DatabaseCorrupted { file: String },

    #[error("Memory mapping failed: {reason}")]
    MemoryMappingError { reason: String },
}
```

### Python Exception Mapping
- RustKmerError → PyValueError
- DatabaseError → PyIOError
- MemoryError → PyMemoryError

## Testing Strategy

### Multi-Layer Approach
1. Rust unit tests for core algorithms
2. Python integration tests for PyO3 bindings
3. End-to-end tests for complete workflows
4. Performance benchmarks with criterion

### Property-Based Testing
- Use proptest for Rust
- Use hypothesis for Python
- Test k-mer encoding roundtrip properties
- Validate database consistency properties

## Build and Distribution

### Maturin Configuration
```toml
[build-system]
requires = ["maturin>=1.0,<2.0"]
build-backend = "maturin"

[tool.maturin]
python-source = "python"
module-name = "rustkmer._rustkmer"
features = ["python"]
```

### CI/CD Pipeline
- Multi-platform builds (Linux, macOS, Windows)
- Python 3.11, 3.12, 3.13 support
- Automated performance regression testing
- Wheel distribution for major platforms

## Technical Stack Decisions

### Core Dependencies
- **Rust**: 1.80+ stable channel
- **Python**: 3.10+ (minimum), 3.13+ (recommended)
- **PyO3**: 0.27.2+ for bindings
- **rayon**: 1.10+ for parallel processing
- **serde**: 1.0+ for serialization
- **memmap2**: 0.9+ for memory mapping
- **thiserror**: 2.0+ for error handling

### Testing Dependencies
- **pytest**: 8.4+ for Python testing
- **criterion**: 0.5+ for Rust benchmarks
- **proptest**: Rust property-based testing
- **hypothesis**: Python property-based testing

### Build Dependencies
- **maturin**: 1.0+ for building Rust-Python extensions
- **cargo**: Rust package manager
- **pip**: Python package installer

## Performance Targets

Based on research and analysis:

- **API Performance**: ≤ 110% of CLI baseline
- **Memory Usage**: ≤ 105% of CLI baseline
- **Initialization**: < 100ms for database loading
- **Query Latency**: < 1ms for single k-mer lookup
- **Batch Throughput**: > 100k k-mers/second

## Key Implementation Considerations

### 1. Thread Safety
- Database queries must be thread-safe
- Multiple Python threads can access same database
- Proper synchronization for shared state

### 2. Memory Efficiency
- Memory mapping for databases > 100MB
- Streaming processing for large FASTA/FASTQ files
- Garbage collection integration with Python

### 3. Error Handling
- Structured error types with thiserror
- Python exception mapping
- Graceful degradation for non-critical errors

### 4. API Design
- Pythonic interface following PEP 8
- Type hints for better IDE support
- Context managers for resource management

## Risk Mitigation

### Performance Risks
- Automated benchmarking in CI/CD
- Performance regression testing
- Optimized release builds with LTO

### Compatibility Risks
- Comprehensive test matrix across platforms
- Version pinning for critical dependencies
- Backward compatibility testing

### Maintenance Risks
- Comprehensive documentation
- Example code and tutorials
- Clear contribution guidelines