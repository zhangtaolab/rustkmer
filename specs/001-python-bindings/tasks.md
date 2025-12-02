# Implementation Tasks: Python Bindings for RustKmer

**Branch**: `001-python-bindings` | **Date**: 2025-12-01
**Spec**: [spec.md](./spec.md)
**Total Tasks**: 47

## Phase 1: Setup (Project Initialization)

**Goal**: Initialize project structure and build system for Python package with Rust extension.

**Independent Test Criteria**:
- Build system configured and can compile basic Rust extension
- Python package structure created with empty modules
- CI/CD pipeline can build and test basic functionality

### Tasks

- [X] T001 Create Python package structure according to implementation plan
- [X] T002 Initialize pyproject.toml with maturin build system configuration
- [X] T003 Update Cargo.toml with PyO3 dependencies and python module configuration
- [X] T004 [P] Create Python package modules with empty class definitions (python/rustkmer/__init__.py, core.py, fuzzy.py, sequence.py, stats.py, exceptions.py)
- [X] T005 Create Rust Python module structure (src/python/lib.rs, kmer_counter.rs, database.rs, fuzzy_query.rs, utils.rs)
- [X] T006 Setup GitHub Actions CI/CD workflow for cross-platform wheel building
- [X] T007 Create basic project documentation (README.md, LICENSE)

## Phase 2: Foundational (Blocking Prerequisites)

**Goal**: Implement core infrastructure that all user stories depend on.

**Independent Test Criteria**:
- Basic PyO3 module can be imported in Python
- Error handling system works across Python-Rust boundary
- Memory management and resource cleanup functions correctly

### Tasks

- [X] T008 Implement basic PyO3 module initialization and Python class structure in src/python/lib.rs
- [X] T009 [P] Create custom exception classes in python/rustkmer/exceptions.py
- [X] T010 [P] Implement Rust error to Python exception mapping in src/python/utils.rs
- [X] T011 Create basic memory management and resource cleanup utilities
- [X] T012 Setup basic Python test framework (pytest configuration)
- [X] T013 [P] Create integration test infrastructure for Rust-Python interface
- [X] T014 Implement basic logging and debugging utilities

## Phase 3: User Story 1 - Basic k-mer Counting from Python (P1)

**Goal**: Enable Python developers to perform k-mer counting on genomic data directly from Python scripts.

**Independent Test Criteria**:
- Can count k-mers from a simple DNA sequence and get correct results
- Can count k-mers from a FASTA file and get correct results
- Invalid DNA sequence input raises appropriate error with clear message

### Tasks

- [X] T015 [US1] Create KmerCounter Rust struct wrapper in src/python/kmer_counter.rs
- [X] T016 [US1] [P] Implement KmerCounter.__init__ method with kmer_length, canonical_mode, thread_count parameters
- [X] T017 [US1] [P] Implement KmerCounter.count_sequence method for string sequence input
- [X] T018 [US1] [P] Implement KmerCounter.count_file method with FASTA/FASTQ file support
- [X] T019 [US1] Implement KmerCounter.get_kmer_count method for individual k-mer queries
- [X] T020 [US1] [P] Implement KmerCounter.get_all_counts method
- [X] T021 [US1] Implement KmerCounter.get_top_kmers method
- [X] T022 [US1] [P] Implement KmerCounter.filter_by_count method
- [X] T023 [US1] Implement KmerCounter.get_stats method returning CounterStats
- [X] T024 [US1] Implement KmerCounter.merge method for combining counters
- [ ] T025 [US1] [P] Create CounterStats dataclass in python/rustkmer/stats.py
- [ ] T026 [US1] Add KmerCounter to python/rustkmer/core.py
- [ ] T027 [US1] Add KmerCounter to main package exports in python/rustkmer/__init__.py
- [ ] T028 [US1] Create Python unit tests for KmerCounter functionality
- [ ] T029 [US1] Create integration tests comparing Python results with command-line tool

## Phase 4: User Story 2 - Database Query Operations (P1)

**Goal**: Enable researchers to query existing k-mer databases from Python to retrieve specific k-mer counts.

**Independent Test Criteria**:
- Can query a valid database file and get accurate k-mer counts
- Query for non-existent k-mers returns zero counts
- Invalid database file path raises clear error about file access

### Tasks

- [X] T030 [US2] Create Database Rust struct wrapper in src/python/database.rs
- [X] T031 [US2] [P] Implement Database.__init__ method with file_path and preload parameters
- [X] T032 [US2] Implement Database.__enter__ and __exit__ methods for context manager support
- [X] T033 [US2] [P] Implement Database.query method returning QueryResult
- [X] T034 [US2] Implement Database.query_multiple method for batch queries
- [X] T035 [US2] Implement Database.get_kmer_size method
- [X] T036 [US2] [P] Implement Database.get_stats method returning DatabaseStats
- [X] T037 [US2] Implement Database.load and Database.close methods
- [ ] T038 [US2] [P] Create QueryResult dataclass in python/rustkmer/stats.py
- [ ] T039 [US2] Create DatabaseStats dataclass in python/rustkmer/stats.py
- [ ] T040 [US2] Add Database to python/rustkmer/core.py
- [ ] T041 [US2] Add Database to main package exports in python/rustkmer/__init__.py
- [ ] T042 [US2] Create Python unit tests for Database functionality
- [ ] T043 [US2] Create integration tests with existing .rkdb database files

## Phase 5: User Story 3 - Fuzzy Query with Wildcards (P2)

**Goal**: Enable bioinformaticians to perform fuzzy queries with wildcards to find similar k-mers.

**Independent Test Criteria**:
- Can query with wildcard patterns and get all matching k-mers with counts
- Fuzzy query with too many potential matches applies limits or raises warning

### Tasks

- [X] T044 [US3] Create FuzzyQuery Rust struct wrapper in src/python/fuzzy_query.rs
- [X] T045 [US3] [P] Implement FuzzyQuery.__init__ method with query_string, kmer_size, mutation_tolerance, max_variants
- [X] T046 [US3] Implement FuzzyQuery.validate method
- [X] T047 [US3] [P] Implement FuzzyQuery.expand_wildcards method
- [X] T048 [US3] Implement FuzzyQuery.generate_mutations method
- [X] T049 [US3] Implement FuzzyQuery.execute method for database queries
- [X] T050 [US3] Create FuzzyQueryResult dataclass in python/rustkmer/stats.py
- [X] T051 [US3] Add FuzzyQuery to python/rustkmer/fuzzy.py
- [X] T052 [US3] Add FuzzyQuery to main package exports in python/rustkmer/__init__.py
- [X] T053 [US3] Create Python unit tests for FuzzyQuery functionality
- [X] T054 [US3] Create integration tests with wildcard and mutation queries

## Phase 6: User Story 4 - Batch Processing and Performance (P2)

**Goal**: Enable data scientists to process multiple sequences or large datasets efficiently.

**Independent Test Criteria**:
- Can process multiple sequences in batch efficiently
- Large genomic files process with reasonable memory usage and time

### Tasks

- [ ] T055 [US4] [P] Implement convenience function rustkmer.count_kmers for simple use cases
- [ ] T056 [US4] [P] Implement rustkmer.create_database function for database creation
- [ ] T057 [US4] Implement batch processing optimizations in KmerCounter
- [ ] T058 [US4] Add memory-mapped file access for large databases
- [ ] T059 [US4] Implement parallel processing optimizations using Rayon
- [ ] T060 [US4] Create performance benchmarks and regression tests
- [ ] T061 [US4] Create Sequence utility class in python/rustkmer/sequence.py
- [ ] T062 [US4] Add Sequence to main package exports in python/rustkmer/__init__.py
- [ ] T063 [US4] Create Python tests for batch processing performance

## Phase 7: Polish & Cross-Cutting Concerns

**Goal**: Complete the implementation with documentation, performance optimization, and release preparation.

**Independent Test Criteria**:
- Documentation examples work correctly for all major use cases
- Installation and setup process works in under 5 minutes
- Performance meets success criteria (within 20% of CLI, <100ms queries)

### Tasks

- [ ] T064 [P] Create comprehensive API documentation with docstrings
- [ ] T065 [P] Create user guide and tutorial documentation
- [ ] T066 [P] Add performance benchmarks to CI/CD pipeline
- [ ] T067 [P] Optimize memory usage and performance bottlenecks
- [ ] T068 Create example scripts and notebooks for common use cases
- [ ] T069 [P] Setup automated wheel building and PyPI publishing
- [ ] T070 Create integration tests with popular bioinformatics libraries (Biopython, pandas)
- [ ] T071 Add type hints and improve IDE support
- [ ] T072 Final performance validation against success criteria
- [ ] T073 Create release notes and version management

## Dependencies

### User Story Dependencies

```
US1 (Basic Counting) ← US2 (Database Queries) ← US3 (Fuzzy Queries) ← US4 (Batch Processing)
```

- **US1**: No dependencies (can be implemented independently)
- **US2**: Depends on US1 for basic infrastructure
- **US3**: Depends on US2 for database query functionality
- **US4**: Depends on US1-3 for performance optimization

### Critical Path

1. **Phase 1** → **Phase 2** → **US1** → **US2** → **US3** → **US4** → **Phase 7**

## Parallel Execution Opportunities

### Within User Stories

**Phase 1 (Setup)**:
- T004, T006, T007 can be executed in parallel

**Phase 2 (Foundational)**:
- T009, T010, T012, T013 can be executed in parallel

**US1 (Basic Counting)**:
- T016, T017, T020, T022, T025 can be executed in parallel
- T026, T027, T028 can be executed in parallel after core methods

**US2 (Database Queries)**:
- T031, T033, T036, T038, T039 can be executed in parallel
- T040, T041, T042 can be executed in parallel after core methods

**US3 (Fuzzy Queries)**:
- T045, T047, T048, T050 can be executed in parallel
- T051, T052, T053 can be executed in parallel after core methods

**US4 (Batch Processing)**:
- T055, T056, T057, T058, T061 can be executed in parallel
- T062, T063 can be executed in parallel after core methods

**Phase 7 (Polish)**:
- T064, T065, T068, T071 can be executed in parallel
- T066, T067, T069 can be executed in parallel

## Implementation Strategy

### MVP Scope (First Release)

**Minimum Viable Product**: US1 + US2 + Basic Documentation
- Tasks T001-T043 (Phases 1-4)
- Basic k-mer counting and database query functionality
- Essential documentation and basic tests

**Timeline Estimate**: 3-4 weeks

### Full Release Scope

**Complete Implementation**: All User Stories + Polish
- All tasks T001-T073
- Full feature set with performance optimization
- Comprehensive documentation and examples

**Timeline Estimate**: 7-11 weeks

### Incremental Delivery Strategy

1. **Week 1-2**: Phase 1-2 (Setup + Infrastructure)
2. **Week 3-4**: US1 (Basic Counting) - MVP Ready
3. **Week 5-6**: US2 (Database Queries) - Beta Release
4. **Week 7-8**: US3 (Fuzzy Queries) - Feature Complete
5. **Week 9-10**: US4 (Performance) - Performance Optimized
6. **Week 11**: Phase 7 (Polish) - Production Ready

## Testing Strategy

### Unit Tests
- Each Python module tested independently
- Rust extension module tested with Python test framework
- Error handling and edge case validation

### Integration Tests
- End-to-end workflows for each user story
- Cross-language interface testing
- Performance benchmark validation

### Compatibility Tests
- Existing .rkdb database compatibility
- Cross-platform wheel testing
- Python version compatibility (3.8+)

### Performance Tests
- Benchmark against command-line tool
- Memory usage validation
- Large dataset performance testing