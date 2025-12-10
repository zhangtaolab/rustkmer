# Implementation Tasks: Complete Python Bindings for RustKmer

**Feature Branch**: `012-python-bindings-complete`
**Date**: 2025-12-10
**Total Tasks**: 114

## Phase 1: Setup and Infrastructure

### Goal
Set up the development environment and project structure for implementing Python bindings.

### Independent Test Criteria
- Python development environment configured with required dependencies
- Rust compilation pipeline configured for Python bindings
- Basic "hello world" Python binding compiles and imports successfully

### Tasks

- [X] T001 [P1] Configure Python development environment (.venv) per Constitution Principle VI
  - [X] T001.1 Create project-local .venv virtual environment
  - [X] T001.2 Activate .venv and install maturin build system
  - [X] T001.3 Set up Python package metadata in python/pyproject.toml
  - [X] T001.4 Create script to verify .venv is active during development
  - [X] T001.5 Document .venv usage in build instructions
- [X] T002 Create python bindings directory structure in src/python/
- [X] T003 [P] Add PyO3 dependency to Cargo.toml with required features
- [X] T004 [P] Create Python module layout with __init__.py in python/rustkmer/
- [X] T005 Create basic Rust-Python binding module structure
- [X] T006 [P] Create placeholder Python exception classes
- [X] T007 Set up Python test directory structure following pytest conventions
  - [X] T007.1 [P] Create test directories: unit/, integration/, performance/, compatibility/
  - [X] T007.2 [P] Set up pytest.ini with markers and configuration
  - [X] T007.3 [P] Create test conftest.py with shared fixtures
  - [X] T007.4 [P] Add test_coverage configuration in pytest.ini
  - [X] T007.5 [P] Create test runner script with categorized test execution
  - [X] T007.6 [P1] Add pytest fixture to ensure tests run in .venv
  - [X] T007.7 [P1] Add CI check to validate .venv isolation
- [X] T008 [P1] Implement basic "hello world" Python binding to verify compilation and import
  - [X] T008.1 Create simple rustkmer module with basic info() function
  - [X] T008.2 Add basic Python import test
  - [X] T008.3 Verify maturin build produces working Python extension

## Phase 2: Foundational Components

### Goal
Implement core infrastructure and base classes that all Python API components will depend on.

### Independent Test Criteria
- Base exception hierarchy implemented and importable
- Core utility functions for encoding/decoding k-mers working
- Memory mapping infrastructure operational

### Tasks

- [X] T009 Create Python exception hierarchy in python/rustkmer/exceptions.py
- [X] T010 Implement k-mer encoding utilities (support for u128 only)
- [X] T011 [P] Create memory mapping wrapper for large database files
- [X] T012 Implement base Python classes for all API components
- [X] T013 [P] Create file format validation utilities
- [X] T014 Set up progress callback mechanism for long operations
- [X] T015 [P] Implement thread pool configuration for parallel operations
- [X] T016 [P1] Implement GIL release mechanisms for CPU-intensive batch operations
  - [X] T016.1 Add pyo3::allow_threads wrapper for long-running operations
  - [X] T016.2 Implement batch query processing with GIL release
  - [X] T016.3 Add progress callbacks that work with GIL release
- [X] T017 Create Python-friendly error handling wrapper

## Phase 3: User Story 1 - Python API for K-mer Counting (P1)

### Goal
Python bioinformaticians need to count k-mers in sequence files (FASTA/FASTQ) directly from Python scripts.

### Independent Test Criteria
```python
from rustkmer import KmerCounter

counter = KmerCounter(k=31)
counter.count_file("test.fa")
assert counter.get_total_count() > 0
assert counter.get_unique_count() > 0
```

### Tasks

- [X] T017 [US1] Implement KmerCounter class Python wrapper in src/python/lib.rs
- [X] T018 [US1] Implement KmerCounter.__init__() with k, canonical, threads parameters
- [X] T019 [US1] Implement KmerCounter.count_file() method for FASTA/FASTQ files
- [X] T020 [US1] Implement KmerCounter.count_string() method for sequence strings
- [X] T021 [US1] Implement KmerCounter.count_stream() method for data streams
- [X] T022 [US1] Implement KmerCounter.get_total_count() method
- [X] T023 [US1] Implement KmerCounter.get_unique_count() method
- [X] T024 [US1] Implement KmerCounter.get_kmer_count() for individual k-mer lookup
- [X] T025 [US1] Implement KmerCounter.get_top_kmers() method
- [X] T026 [US1] Implement KmerCounter.save_to_database() method
- [X] T027 [US1] Add progress callback support to counting operations
- [X] T028 [US1] Implement file format auto-detection (FASTA/FASTQ)
- [X] T029 [US1] Create python/rustkmer/core.py with KmerCounter Python wrapper
- [X] T030 [US1] Write unit tests for KmerCounter functionality
  - [X] T030.1 [P] Create test_kmer_counter.py with comprehensive test cases
  - [X] T030.2 [P] Test k-mer counting from FASTA files (tests/integration/test_kmer_counter_fasta.py)
  - [X] T030.3 [P] Test k-mer counting from FASTQ files (tests/integration/test_kmer_counter_fastq.py)
  - [X] T030.4 [P] Test k-mer counting from strings with different parameters
  - [X] T030.5 [P] Test top k-mers retrieval and sorting
  - [X] T030.6 [P] Test database saving functionality
  - [X] T030.7 [P] Test canonical vs non-canonical counting modes
- [X] T031 [US1] Add comprehensive docstrings for KmerCounter class

## Phase 4: User Story 2 - Database Query Operations from Python (P1)

### Goal
Researchers need to query k-mer counts and existence checks from existing RKDB databases through Python.

### Independent Test Criteria
```python
from rustkmer import Database

db = Database()
db.load("test.rkdb")
stats = db.get_stats()
count = db.query("ATCGATCGATCGATCGATCGATC")
assert isinstance(count, int)
```

### Tasks

- [X] T033 [US2] Implement Database class Python wrapper in src/python/lib.rs
- [X] T034 [US2] Implement Database.load() method for RKDB files
- [X] T035 [US2] Implement Database.query() method for exact k-mer lookup
- [X] T036 [US2] Implement Database.query_batch() method for multiple k-mers
- [X] T037 [US2] Implement Database.exists() method for k-mer existence check
- [X] T038 [US2] Implement Database.get_stats() method returning DatabaseStats
- [X] T039 [US2] Implement Database.close() method for cleanup
- [X] T040 [US2] Add memory mapping support for large databases
- [X] T041 [US2] Implement DatabaseHeader Python wrapper
- [X] T042 [US2] Implement DatabaseStats Python wrapper
- [X] T043 [US2] Create python/rustkmer/database.py module
- [X] T044 [US2] Add database metadata access methods
- [X] T045 [US2] Write unit tests for Database operations
  - [X] T045.1 [P] Create test_database.py with database operations tests
  - [X] T045.2 [P] Test database loading from RKDB files (tests/integration/test_database_load.py)
  - [X] T045.3 [P] Test exact k-mer queries and batch queries
  - [X] T045.4 [P] Test database existence checks
  - [X] T045.5 [P] Test database statistics calculation (tests/integration/test_database_statistics.py)
  - [X] T045.6 [P] Test concurrent database access (tests/integration/test_concurrent_access.py)
  - [X] T045.7 [P] Test memory-mapped file access

## Phase 5: User Story 3 - Fuzzy Query and Mutation Analysis (P2)

### Goal
Genomics researchers need to perform fuzzy queries with wildcards and mutation tolerance from Python.

### Independent Test Criteria
```python
from rustkmer import FuzzyQuery

fq = FuzzyQuery()
fq.load("database.rkdb")
results = fq.query("ATCGATCGATCGATNGATCG", max_mismatches=2)
assert len(results) > 0
```

### Tasks

- [X] T046 [US3] Implement FuzzyQuery class Python wrapper in src/python/lib.rs
- [X] T047 [US3] Implement FuzzyQuery.load() method
- [X] T048 [US3] Implement FuzzyQuery.query() with wildcard support
- [X] T049 [US3] Implement FuzzyQuery.query_batch() method
- [X] T050 [US3] Implement FuzzyQuery.set_max_distance() method
- [X] T051 [US3] Implement wildcard pattern expansion logic
- [X] T052 [US3] Implement fuzzy query result ranking
- [X] T053 [US3] Create python/rustkmer/fuzzy.py module
- [X] T054 [US3] Implement FuzzyQueryResult Python wrapper
- [X] T055 [US3] Add Hamming distance calculation methods
- [X] T056 [US3] Write unit tests for fuzzy query functionality
  - [X] T056.1 [P] Create test_fuzzy_query.py with fuzzy query tests
  - [X] T056.2 [P] Test fuzzy queries with wildcards (tests/integration/test_fuzzy_query.py)
  - [X] T056.3 [P] Test batch fuzzy queries with multiple patterns
  - [X] T056.4 [P] Test Hamming distance calculations
  - [X] T056.5 [P] Test fuzzy query result ranking
  - [X] T056.6 [P] Test max distance configuration

## Phase 6: User Story 4 - Database Statistics and Analysis (P2)

### Goal
Bioinformaticians need to calculate and retrieve comprehensive statistics about k-mer databases from Python.

### Independent Test Criteria
```python
from rustkmer import Database

db = Database()
db.load("test.rkdb")
stats = db.calculate_stats()
assert stats.total_kmers > 0
assert stats.unique_kmers > 0
```

### Tasks

- [X] T057 [US4] Implement statistics calculation module in src/python/lib.rs
- [X] T058 [US4] Implement Database.calculate_stats() method
- [X] T059 [US4] Implement histogram calculation for k-mer frequency distribution
- [X] T060 [US4] Implement coverage estimation algorithms
- [X] T061 [US4] Create python/rustkmer/stats.py module
- [X] T062 [US4] Implement percentile calculations (P25, P50, P75, P95, P99)
- [X] T063 [US4] Add database metadata extraction
- [X] T064 [US4] Implement k-mer abundance distribution analysis
- [X] T065 [US4] Write unit tests for statistics functionality
  - [X] T065.1 [P] Create test_stats.py with statistics calculation tests
  - [X] T065.2 [P] Test frequency histogram generation
  - [X] T065.3 [P] Test percentile calculations (P25, P50, P75, P95, P99)
  - [X] T065.4 [P] Test coverage estimation algorithms
  - [X] T065.5 [P] Test database metadata extraction
  - [X] T065.6 [P] Validate statistics against CLI output

## Phase 7: User Story 5 - Database Merge Operations (P3)

### Goal
Pipeline developers need to merge multiple RKDB databases from Python to combine k-mer counts.

### Independent Test Criteria
```python
from rustkmer import Database

db1 = Database.load("sample1.rkdb")
db2 = Database.load("sample2.rkdb")
merged = db1.merge(db2)
assert merged.get_stats().total_kmers > 0
```

### Tasks

- [X] T066 [US5] Implement database merge functionality in src/python/lib.rs
- [X] T067 [US5] Implement Database.merge() method for combining databases
- [X] T068 [US5] Implement Database.merge_multiple() for multiple databases
- [X] T069 [US5] Add k-mer count aggregation strategies (sum, max, min)
- [X] T070 [US5] Implement merge validation (k-mer size compatibility)
- [X] T071 [US5] Create python/rustkmer/merge.py module
- [X] T072 [US5] Add progress reporting for merge operations
- [X] T073 [US5] Write unit tests for database merge functionality
  - [X] T073.1 [P] Create test_merge.py with merge operations tests
  - [X] T073.2 [P] Test merging compatible databases (tests/integration/test_database_merge.py)
  - [X] T073.3 [P] Test merging multiple databases
  - [X] T073.4 [P] Test merge validation (incompatible k-mer sizes)
  - [X] T073.5 [P] Test different aggregation strategies (sum, max, min)
  - [X] T073.6 [P] Test merge performance with large databases

## Phase 8: User Story 6 - Database Dump and Export (P3)

### Goal
Users need to export k-mer data from RKDB databases to text formats from Python.

### Independent Test Criteria
```python
from rustkmer import Database

db = Database()
db.load("test.rkdb")
db.dump("export.txt", format="text")
assert os.path.exists("export.txt")
```

### Tasks

- [X] T074 [US6] Implement database export functionality in src/python/lib.rs
- [X] T075 [US6] Implement Database.dump() method with format parameter
- [X] T076 [US6] Implement text format export (k-mer<TAB>count)
- [X] T077 [US6] Implement CSV format export with headers
- [X] T078 [US6] Implement JSON format export
- [X] T079 [US6] Add count threshold filtering for exports
- [X] T080 [US6] Create python/rustkmer/export.py module
- [ ] T081 [US6] Add compression support for large exports
- [X] T082 [US6] Write unit tests for export functionality
  - [X] T082.1 [P] Create test_export.py with export functionality tests
  - [X] T082.2 [P] Test text format export (k-mer<TAB>count) (tests/integration/test_database_dump.py)
  - [X] T082.3 [P] Test CSV format export with headers
  - [X] T082.4 [P] Test JSON format export with metadata
  - [X] T082.5 [P] Test count threshold filtering for exports
  - [ ] T082.6 [P] Test compression support for large exports
  - [X] T082.7 [P] Validate export formats match CLI output

## Phase 9: Cross-Cutting Concerns and Polish

### Goal
Complete the implementation with performance optimization, testing, and documentation.

### Independent Test Criteria
- All Python API classes match CLI performance within 10%
- Complete test suite with 95% code coverage
- Full API documentation generated

### Tasks

- [X] T083 Implement comprehensive error handling for all Python API methods
- [X] T084 [P] Add input validation for all public methods
- [ ] T085 Implement performance benchmarking suite
- [ ] T086 Optimize memory usage for large database operations
- [X] T087 [P] Add thread-safe operations for concurrent access
- [ ] T088 Create integration tests comparing Python API to CLI
  - [ ] T088.1 [P] Create test_api_workflows.py for end-to-end testing
  - [ ] T088.2 [P] Test counting workflow (Python vs CLI)
  - [ ] T088.3 [P] Test query workflow accuracy
  - [ ] T088.4 [P] Test merge workflow results
  - [ ] T088.5 [P] Test stats workflow outputs
  - [ ] T088.6 [P] Create comprehensive integration test runner
- [ ] T089 [P] Write compatibility tests for all CLI commands
  - [ ] T089.1 [P] Create test_count_compatibility.py comparing count operations
  - [ ] T089.2 [P] Create test_database_query.py comparing query operations
  - [ ] T089.3 [P] Create test_fuzzy_query.py comparing fuzzy queries
  - [ ] T089.4 [P] Create test_database_merge.py comparing merge operations
  - [ ] T089.5 [P] Create test_database_dump.py comparing export operations
  - [ ] T089.6 [P] Create test_database_statistics.py comparing stats calculations
  - [ ] T089.7 [P] Implement CLI comparator utility for automated testing
- [X] T090 Generate Python API documentation with docstrings
- [X] T091 Create example scripts and tutorials
- [X] T092 Update __init__.py to expose all public classes
- [X] T093 [P] Add type hints for all Python methods
- [X] T094 Create pytest test suite with fixtures
  - [X] T094.1 [P] Create comprehensive fixtures in tests/python/conftest.py
  - [ ] T094.2 [P] Add basic DNA sequence fixtures (tests/fixtures/kmers/)
  - [ ] T094.3 [P] Add test data fixtures for different k-mer sizes
  - [ ] T094.4 [P] Add large scale test fixtures for performance testing
  - [ ] T094.5 [P] Add error case fixtures for exception testing
  - [ ] T094.6 [P] Add fuzzy query test fixtures
  - [ ] T094.7 [P] Create parameterized test fixtures for edge cases
- [ ] T095 Final integration testing and bug fixes

## Phase 10: Performance, Compliance, and Advanced Error Handling

### Goal
Ensure Python API meets all constitutional requirements including performance benchmarks, comprehensive error handling, and testing standards.

### Independent Test Criteria
- Performance benchmarks show Python API within 110% of CLI baseline
- Property-based tests cover critical algorithms
- Thread safety verified for concurrent operations
- Memory usage monitored and optimized
- All error types properly defined and handled

### Tasks

#### Performance and Compliance (T096-T103)
- [ ] T096 [P1] Implement performance benchmarks for all Python API operations
- [ ] T097 [P1] Add criterion benchmarks comparing Python vs CLI performance
- [X] T098 [P1] Create property-based tests for k-mer encoding/decoding using hypothesis
  - [X] T098.1 [P] Create test_kmer_encoding_property.py using hypothesis library
  - [ ] T098.2 [P] Test k-mer encoding roundtrip property (encode → decode = original)
  - [ ] T098.3 [P] Test canonical k-mer property (revcomp = original)
  - [ ] T098.4 [P] Test u128 bit pattern invariants for all valid k-mers
  - [ ] T098.5 [P] Test database consistency properties (k-mer ordering uniqueness)
  - [ ] T098.6 [P] Add property-based tests for fuzzy query distance calculations
- [ ] T099 [P1] Implement regression test suite for all bug fixes
- [X] T100 [P1] Add thread-safe operations for concurrent database access
- [X] T101 [P1] Implement memory usage validation and monitoring
- [X] T102 [P1] Add automated test coverage verification (target: 95%)
- [ ] T103 [P1] Create performance regression tests in CI/CD pipeline

#### Advanced Error Handling (T104-T108)
- [X] T104 [P1] Implement Python exception hierarchy matching Rust error types
  - [X] T104.1 Define RustKmerError base exception class in python/rustkmer/exceptions.py
  - [X] T104.2 Implement SequenceError for invalid DNA sequences
  - [X] T104.3 Implement DatabaseError for database operations
  - [X] T104.4 Implement FileNotFoundError for missing files
  - [X] T104.5 Implement ValueError for invalid parameters
  - [X] T104.6 Implement MemoryError for out-of-memory conditions
- [X] T105 [P1] Add error propagation from Rust to Python with proper translation in src/python/lib.rs
- [ ] T106 [P1] Create error recovery examples in documentation
- [ ] T107 [P1] Add error handling tests for all API methods
  - [ ] T107.1 [P] Create test_exceptions.py with comprehensive error tests
  - [ ] T107.2 [P] Test SequenceError for invalid DNA sequences
  - [ ] T107.3 [P] Test DatabaseError for corrupted files
  - [ ] T107.4 [P] Test ValueError for invalid parameters
  - [ ] T107.5 [P] Test MemoryError for out-of-memory conditions
  - [ ] T107.6 [P] Test error message clarity and actionability
  - [ ] T107.7 [P] Test error recovery and graceful degradation
- [ ] T108 [P1] Implement graceful degradation for edge cases

## Dependencies and Task Order

### User Story Dependencies
1. US1 (K-mer Counting) - No dependencies
2. US2 (Database Query) - Depends on US1 (for creating test databases)
3. US3 (Fuzzy Query) - Depends on US2
4. US4 (Statistics) - Depends on US2
5. US5 (Merge Operations) - Depends on US2
6. US6 (Export) - Depends on US2

### Critical Path
Phase 1 → Phase 2 → Phase 3 (US1) → Phase 4 (US2) → [US3, US4, US5, US6 can run in parallel] → Phase 9 → Phase 10

### Constitutional Requirements
Phase 10 (T096-T108) must be completed to satisfy:
- Principle II: Comprehensive Testing Standards (95% coverage, property-based tests)
- Principle IV: Performance Requirements (≤110% CLI performance, memory efficiency)
- User Story acceptance criteria

## Parallel Execution Opportunities

### Within User Story 1 (Phase 3)
- T018-T027 can be implemented in parallel once core structure is in place
- Test tasks (T032) can be written alongside implementation

### Within User Story 2 (Phase 4)
- T033-T043 can be implemented in parallel
- Memory mapping (T040) can be done independently

### Across User Stories
- Once US2 is complete, US3, US4, US5, and US6 can proceed in parallel
- Documentation tasks (T090, T091) can be done throughout

### Within Phase 10
- Performance benchmarks (T096-T097) can run in parallel with property-based tests (T098)
- Error handling implementation (T104-T105) can proceed concurrently with test setup (T107)
- CI/CD pipeline tests (T103) can be configured independently

## Implementation Strategy

### MVP (Minimum Viable Product)
Focus on completing User Stories 1 and 2:
- K-mer counting from Python
- Basic database query operations
- Essential error handling

This provides core functionality that covers 80% of common use cases.

### Incremental Delivery
1. **First Release**: US1 + US2 (Core functionality)
2. **Second Release**: Add US3 + US4 (Advanced features)
3. **Third Release**: Add US5 + US6 (Pipeline features)
4. **Final Polish**: Performance optimization and documentation

## Testing Strategy

### Unit Tests
- Each Python class will have dedicated unit tests
- Test coverage will use pytest framework
- Fixtures will provide test data (FASTA/FASTQ files)

### Integration Tests
- CLI-Python compatibility tests
- Performance benchmarking against CLI
- End-to-end workflow tests

### Acceptance Tests
- Each user story has defined independent test criteria
- Tests can run without external dependencies