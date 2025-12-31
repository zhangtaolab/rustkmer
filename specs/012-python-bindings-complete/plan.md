# Implementation Plan: Complete Python Bindings for RustKmer

**Branch**: `012-python-bindings-complete` | **Date**: 2025-12-10 | **Spec**: `/specs/012-python-bindings-complete/spec.md`
**Input**: Feature specification from `/specs/012-python-bindings-complete/spec.md`

## Summary

This plan implements comprehensive Python bindings for the RustKmer library, providing complete API coverage for all CLI commands including k-mer counting, database queries, fuzzy searches, statistics calculation, database merging, and data export. The implementation is built on the existing u128 encoding architecture and focuses on high-performance, memory-efficient operations with seamless Rust-Python integration via PyO3.

## Technical Context

**Language/Version**: Rust 1.80+ stable, Python 3.10+ via PyO3 0.27.2
**Primary Dependencies**: PyO3 0.27.2+, serde 1.0+, thiserror 2.0+, rayon 1.10+, memmap2 0.9+, pytest 8.4+
**Storage**: Binary RKDB files with memory-mapped access
**Testing**: pytest 8.4+ with pytest-cov, pytest-benchmark, hypothesis
**Target Platform**: Linux, macOS, Windows with Python >= 3.10
**Project Type**: Python library with Rust extension module
**Performance Goals**: Within 110% of CLI performance, <5% additional memory overhead
**Constraints**: Must support u128 encoding only (1-64 bases), maintain CLI parity, 95%+ test coverage
**Scale/Scope**: Genomic datasets up to billions of k-mers, databases >100GB

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Code Quality Gates
- [x] Performance benchmarks established for all computationally intensive operations
- [x] Memory efficiency requirements defined for target data sizes
- [x] Error handling strategy designed with Result/Option patterns
- [x] Code organization follows Rust best practices and module boundaries

### Testing Standards Gates
- [x] Unit test coverage plan defined (target: 95%+ for critical paths)
- [x] Integration test scenarios identified for module interactions
- [x] Property-based test requirements specified for complex algorithms
- [x] Performance regression test criteria established

### User Experience Consistency Gates
- [x] CLI interface follows standardized argument patterns
- [x] Output formats support both human-readable and machine-parseable options
- [x] Error message format and actionability requirements defined
- [x] Documentation plan includes comprehensive examples

### Performance Requirements Gates
- [x] Performance benchmarks defined with realistic genomic datasets
- [x] Parallel processing opportunities identified and planned
- [x] Streaming processing strategy for large files
- [x] Resource limits and monitoring requirements specified

## Project Structure

### Documentation (this feature)

```text
specs/012-python-bindings-complete/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── lib.rs              # PyO3 module exports and Python class definitions
├── kmer_counter.rs     # KmerCounter Python bindings
├── database.rs         # Database query Python bindings
├── fuzzy_query.rs      # Fuzzy query Python bindings
├── stats.rs           # Statistics calculation Python bindings
├── merge.rs           # Database merge Python bindings
├── export.rs          # Data export Python bindings
├── error.rs           # Python error type conversions
└── utils.rs           # Python utility functions

python/
├── rustkmer/
│   ├── __init__.py     # Main module exports
│   ├── core.py         # Python wrapper classes
│   ├── database.py     # Database wrapper
│   ├── fuzzy.py        # Fuzzy query wrapper
│   ├── stats.py        # Statistics wrapper
│   ├── merge.py        # Merge operations wrapper
│   ├── export.py       # Export functionality wrapper
│   ├── exceptions.py   # Python exception hierarchy
│   ├── utils.py        # Utility functions
│   └── stubs.py        # Stub implementations for missing features
├── Cargo.toml          # Rust extension build configuration
├── pyproject.toml      # Python package configuration
└── README.md           # Package documentation

tests/
├── python/
│   ├── unit/           # Unit tests for Python API
│   ├── integration/    # CLI parity tests
│   ├── performance/    # Performance benchmarks
│   ├── property/       # Property-based tests
│   ├── memory/         # Memory usage tests
│   ├── errors/         # Error handling tests
│   ├── e2e/           # End-to-end workflow tests
│   └── fixtures/       # Test data and utilities
└── rust/              # Rust extension tests
```

**Structure Decision**: Hybrid Rust-Python architecture with core functionality in Rust and Pythonic wrapper classes for usability.

## Complexity Tracking

No constitution violations identified. The implementation follows standard patterns for PyO3-based Python extensions with clear separation between Rust core logic and Python API layer.

## Implementation Details

### Phase 0: Foundation Architecture (Research Complete)

#### u128 Encoding Integration
- **Decision**: Use existing u128 encoding supporting all k-mer lengths from 1 to 64 bases
- **Rationale**: u128 can encode up to 64 bases (2 bits per base) with room for flags
- Implementation: Direct mapping from Rust u128 to Python strings
- Validation: Comprehensive testing for all supported lengths

#### Memory Efficiency Strategy
- **Decision**: Use memory-mapped file access with automatic pagination
- **Rationale**: RKDB databases can exceed 100GB, requiring efficient memory usage
- Target: <10% memory overhead over CLI baseline
- Implementation: memmap2 crate with configurable pagination

#### Python API Design Philosophy
- **Decision**: Prioritize Pythonic usability while maintaining Rust integration clarity
- **Rationale**: Simplified names (DatabaseQuery → Database) improve Python developer experience
- Implementation: Python wrapper classes with snake_case methods mapping to Rust implementations

### Phase 1: Core Python API Implementation

#### KmerCounter Class (rustkmer.KmerCounter)
```python
class KmerCounter:
    def __init__(self, k: int, canonical: bool = True, threads: int = 1)
    def count_file(self, input_path: str, output_path: str) -> Database
    def count_string(self, sequence: str) -> Dict[str, int]
    def count_files(self, input_paths: List[str], output_path: str) -> Database
    def count_directory(self, path: str, recursive: bool = True) -> Database
```

#### Database Class (rustkmer.Database)
```python
class Database:
    def __init__(self, path: str, preload: bool = True)
    def load(self, path: str, preload: bool = True) -> None
    def query(self, kmer: str) -> int
    def query_batch(self, kmers: List[str]) -> Dict[str, int]
    def exists(self, kmer: str) -> bool
    def get_kmers(self) -> Iterator[str]
    def get_counts(self) -> Iterator[int]
    def iter_kmers(self) -> Iterator[Tuple[str, int]]
    def get_statistics(self) -> DatabaseStats
    def dump(self, output_path: str, format: str = "text", threshold: int = 0) -> None
    def merge(self, other_databases: List[Database], output_path: str) -> Database
```

#### FuzzyQuery Class (rustkmer.FuzzyQuery)
```python
class FuzzyQuery:
    def __init__(self, database: Database, max_mutations: int = 1)
    def query(self, pattern: str, max_results: int = None) -> FuzzyQueryResult
    def query_batch(self, patterns: List[str]) -> List[FuzzyQueryResult]
    def set_max_distance(self, distance: int) -> None
    def set_format(self, format: str) -> None
```

### Phase 2: Advanced Features

#### Statistics and Analysis
```python
class DatabaseStats:
    def calculate_histogram(self, max_bins: int = 1000) -> Dict[int, int]
    def get_percentiles(self) -> Dict[str, float]
    def get_coverage_estimate(self, genome_size: int) -> float
    def export_frequency_distribution(self, output_path: str) -> None
```

#### Database Merging
```python
class DatabaseMerger:
    def __init__(self, output_file: str, threads: int = 0, temp_dir: str = "/tmp")
    def merge(self, input_databases: List[str]) -> Database
    def check_compatibility(self, input_databases: List[str]) -> bool
    def merge_databases(self, databases: List[Database]) -> Database
```

#### Export and Formats
```python
class DatabaseExporter:
    def __init__(self, database: Database)
    def export_text(self, output_path: str, threshold: int = 0) -> None
    def export_csv(self, output_path: str, threshold: int = 0) -> None
    def export_json(self, output_path: str, threshold: int = 0) -> None
    def export_tsv(self, output_path: str, threshold: int = 0) -> None
```

### Phase 3: Performance and Optimization

#### Memory-Mapped Database Access
- **Implementation**: MmapDatabase wrapper for large files
- **Detection**: Automatic threshold-based activation (files > 100MB)
- **Configuration**: Configurable memory limits and fallback strategies
- **Thread Safety**: Arc<RwLock<>> for shared read-only access

#### Parallel Processing Integration
- **CPU Operations**: Rayon for k-mer counting and fuzzy queries
- **I/O Operations**: Async file reading with progress callbacks
- **Batch Operations**: Configurable chunk sizes for optimal throughput
- **Monitoring**: Resource usage tracking and alerting

#### Caching and Optimization
- **LRU Cache**: Frequently accessed k-mers with TTL
- **Query Result Batching**: Pre-fetching for sequential access
- **Adaptive Algorithms**: Memory usage patterns based on database size

### Phase 4: Testing and Validation

#### Comprehensive Test Suite
- **Unit Tests**: All Python API methods with 95%+ coverage
- **Integration Tests**: CLI parity validation for all commands
- **Performance Tests**: Benchmarking against CLI baselines
- **Property Tests**: Hypothesis-based testing for edge cases
- **Memory Tests**: Usage validation for large datasets

#### CLI Parity Validation
- **Output Comparison**: Direct text comparison for all commands
- **Parameter Mapping**: Validation of all CLI options in Python API
- **Error Mapping**: CLI exit codes to Python exception mapping
- **Performance Regression**: Continuous monitoring against CLI

## Critical Implementation Areas

### 1. u128 Encoding Validation Tasks (6 tasks)
- Validate u128 encoding for all k-mer lengths up to 64 bases
- Test encoding/decoding consistency across Rust-Python boundary
- Implement efficient u128-to-string conversions for Python display
- Add comprehensive tests for edge cases (all A's, all T's, mixed patterns)
- Validate performance impact of u128 operations in Python context

### 2. Memory Efficiency Implementation Tasks (7 tasks)
- Implement memory-mapped database access with automatic fallback
- Add pagination support for large query results
- Create memory usage monitoring and reporting utilities
- Implement streaming interfaces for count operations
- Add configurable memory limits with graceful degradation
- Create memory efficiency benchmarks and validation

### 3. Configuration Management Tasks (7 tasks)
- Implement global configuration system with file support
- Add per-operation configuration override mechanisms
- Create environment variable integration for defaults
- Implement configuration validation and error reporting
- Add configuration persistence and loading utilities
- Create configuration schema documentation

## Performance Targets

### K-mer Counting Performance
- **Single-threaded**: ≥ 50,000 k-mers/second
- **Multi-threaded**: Linear scaling up to CPU cores
- **Memory Usage**: ≤ 200MB for 1M k-mers dataset

### Database Query Performance
- **Exact Query**: ≤ 1ms average response time
- **Batch Query**: ≤ 10ms for 1000 k-mers
- **Fuzzy Query**: ≤ 100ms for distance=1, k=31

### Memory Efficiency Targets
- **Database Loading**: ≤ 10% overhead over file size
- **Query Operations**: ≤ 50MB additional memory
- **Large File Processing**: Constant memory usage with streaming

## Quality Assurance

### Code Coverage Requirements
- **Rust Extension**: ≥ 90% line coverage
- **Python Wrapper**: ≥ 95% line coverage
- **Integration Tests**: 100% CLI command coverage
- **Property-Based Tests**: All critical algorithms

### Performance Regression Testing
- **Automated Benchmarks**: All operations on every commit
- **Performance Alerts**: >5% degradation triggers alert
- **Memory Usage Tracking**: Continuous monitoring in CI/CD
- **CLI Parity**: Validation on all operations

### Error Handling Validation
- **Comprehensive Exception Hierarchy**: All error types with structured messages
- **Actionable Messages**: Clear guidance for error resolution
- **Graceful Degradation**: Resource constraint handling
- **Proper Cleanup**: Resource management and cleanup

## Deliverables

1. **Complete Python Package**: Installable via pip with automatic Rust extension compilation
2. **Comprehensive Test Suite**: 95%+ coverage with CLI parity validation
3. **Performance Benchmarks**: Matching CLI within 10% performance targets
4. **Complete Documentation**: API reference with examples and tutorials
5. **CLI Parity Validation Suite**: Ensuring output consistency
6. **Migration Guide**: For existing users transitioning from CLI to Python API
7. **Performance Optimization Guide**: For large dataset handling

## Success Metrics

- **All 121 implementation tasks completed** (including 14 critical infrastructure tasks)
- **pytest suite passes with zero failures** in .venv environment
- **95%+ code coverage achieved** for both Rust and Python components
- **Python API performance within 110% of CLI** baseline
- **Memory usage within 105% of CLI baseline** for identical operations
- **Complete CLI command coverage verified** for all 7 commands
- **Documentation completeness verified** with examples and API reference
- **Package successfully builds** on all target platforms (Linux, macOS, Windows)