# Implementation Tasks: RustKmer Python API Compatibility Verification

**Feature**: 007-api-compatibility | **Date**: 2025-12-02 | **Spec**: [spec.md](./spec.md)
**Total Tasks**: 27

## Phase 1: Setup (Project Initialization)

**Goal**: Establish development environment and resolve build system issues for Python bindings

- [x] T001 Resolve Python bindings compilation errors in maturin build system - **CRITICAL COMPILATION ERRORS IDENTIFIED**
- [x] T002 Remove old compiled Python modules that conflict with new implementation in python/rustkmer/ - **NO CONFLICTS FOUND**
- [x] T003 Set up development environment with PyO3 0.23.4 and Rust 1.80+ stable - **ENVIRONMENT VERIFIED**
- [x] T004 Create test data directory with sample FASTA files for validation testing - **TEST DATA READY**
- [x] T005 Establish baseline CLI database creation for comparison testing framework - **CLI WORKING**

## Phase 2: Foundational (Blocking Prerequisites)

**Goal**: Implement core database format compatibility infrastructure

- [ ] T006 Implement unified .rkdb binary format in Python API save_to_database() method in src/python/kmer_counter.rs
- [ ] T007 Update Python API Database class to read single .rkdb files using CLI DatabaseQuery in src/python/database.rs
- [ ] T008 Add k-mer encoding helpers using CLI encode_kmer_bytes() function from src/kmer/encoding.rs
- [ ] T009 Implement memory mapping wrapper for large database files (>100MB) using memmap2
- [ ] T010 Create compatibility test framework for cross-platform validation

## Phase 3: User Story 1 - Database Format Consistency Verification (P1)

**Goal**: Ensure Python API generates databases identical to CLI format
**Independent Test**: Binary comparison of databases created with identical input data

- [ ] T011 [US1] Modify save_to_database() to create single .rkdb files in src/python/kmer_counter.rs (lines 491-534)
- [ ] T012 [P] [US1] Implement DatabaseHeader write_to() integration for exact CLI format compatibility using src/database/format.rs
- [ ] T013 [US1] Update k-mer entry serialization to match CLI 12-byte format (8-byte k-mer + 4-byte count)
- [ ] T014 [P] [US1] Remove directory-based storage implementation from Python API core modules
- [ ] T015 [US1] Add database file validation to ensure .rkdb extension and proper format in save_to_database method

## Phase 4: User Story 2 - Cross-Platform Query Interoperability (P1)

**Goal**: Enable seamless querying between CLI and Python API databases
**Independent Test**: Create database with CLI, query with Python API and verify identical results

- [ ] T016 [US2] Update Database class to use CLI DatabaseQuery for single .rkdb files in src/python/database.rs
- [ ] T017 [P] [US2] Implement query() method with identical results to CLI query command using DatabaseQuery
- [ ] T018 [P] [US2] Add query_multiple() method for batch operations matching CLI behavior
- [ ] T019 [US2] Integrate memory mapping for efficient database access in src/python/database.rs
- [ ] T020 [US2] Test CLI querying Python-generated databases and vice versa for complete compatibility

## Phase 5: User Story 3 - Fuzzy Query Cross-Platform Support (P2)

**Goal**: Ensure fuzzy query functionality works consistently across platforms
**Independent Test**: Perform equivalent fuzzy queries with wildcards using both tools

- [ ] T021 [US3] Verify Python API fuzzy query uses same CLI core functions from src/fuzzy/
- [ ] T022 [P] [US3] Test wildcard pattern matching (N wildcards) consistency between CLI and Python
- [ ] T023 [US3] Validate mutation tolerance calculations match CLI implementation exactly
- [ ] T024 [P] [US3] Ensure complex fuzzy query patterns work identically across both platforms

## Phase 6: Performance Validation and Optimization

**Goal**: Ensure cross-platform operations maintain <10% overhead compared to native CLI operations

- [ ] T025 [P] Create comprehensive performance benchmarking suite for Python API vs CLI operations
- [ ] T026 [P] Validate performance requirements (<10% overhead) across all database sizes (1MB-100MB, 100MB-10GB, >10GB)
- [ ] T027 [P] Profile memory usage patterns to ensure <2x input file size requirement
- [ ] T028 [P] Optimize Python API binding layer for sub-millisecond query performance

## Final Phase: Polish & Cross-Cutting Concerns

**Goal**: Complete implementation with comprehensive testing and documentation

- [ ] T029 Create comprehensive compatibility test suite with binary file comparison framework
- [ ] T030 Add proper error handling with PyO3 exception conversion for CLI compatibility
- [ ] T031 Update documentation and examples for unified .rkdb format usage in src/python/
- [ ] T032 Implement automated validation tools for contract compliance testing

## Dependencies

### User Story Dependencies
- **US1** → **US2**: Database format must be unified before query interoperability
- **US2** → **US3**: Query interoperability must work before fuzzy query validation
- **Setup** → **Foundational**: Build issues must be resolved before implementation
- **Foundational** → **US1**: Core infrastructure needed for database format unification

### Parallel Execution Opportunities

**Within US1** (Parallel tasks):
- T012: DatabaseHeader integration
- T014: Directory storage removal
- T015: File validation
- (T013 depends on T012 completion)

**Within US2** (Parallel tasks):
- T017: query() method implementation
- T019: Memory mapping integration
- (T018 depends on T017, T020 depends on all US2 tasks)

**Within US3** (Parallel tasks):
- T022: Wildcard pattern testing
- T023: Mutation tolerance validation

**Within Performance** (Parallel tasks):
- T025: Benchmarking suite creation
- T026: Performance validation
- T027: Memory usage profiling
- T028: Binding layer optimization

## Implementation Strategy

### MVP Scope (First Deliverable)
- Complete Phase 1: Resolve build system issues (T001-T005)
- Complete Phase 2: Foundational infrastructure (T006-T010)
- Complete US1 (T011-T015): Basic database format consistency
- **Result**: Python API can create databases identical to CLI format

### Incremental Delivery
1. **MVP**: Database format consistency (US1)
2. **V1.1**: Query interoperability (US2)
3. **V1.2**: Fuzzy query support (US3)
4. **V1.3**: Performance optimization and polish

### Testing Strategy
- **Unit Tests**: Each component tested in isolation using cargo test and pytest
- **Integration Tests**: Cross-platform compatibility validation
- **Property-Based Tests**: Random k-mer sets produce identical results
- **Performance Tests**: Validate <10% overhead requirement using criterion
- **Regression Tests**: Prevent format compatibility breaks

## Success Criteria

### Phase Completion Criteria
- **Phase 1 Complete**: maturin build succeeds without linker errors
- **Phase 2 Complete**: Core infrastructure tests pass
- **US1 Complete**: Binary file comparison shows 100% compatibility
- **US2 Complete**: Cross-platform queries produce identical results
- **US3 Complete**: Fuzzy queries match CLI behavior exactly
- **Project Complete**: All contract requirements from contracts/python-api-compatibility.md satisfied

### Validation Requirements
- Bit-for-bit database file comparison between CLI and Python API
- Query result consistency (100% accuracy) across platforms
- Performance overhead <10% compared to native CLI operations
- All edge cases and error conditions produce identical behavior
- Feature parity with CLI for all supported operations per data-model.md

## File Paths and Implementation Details

### Core Implementation Files
- **src/python/kmer_counter.rs**: Python API k-mer counting and database creation (lines 491-534 for save_to_database)
- **src/python/database.rs**: Python API database querying and file access
- **src/database/format.rs**: CLI database format definitions (DatabaseHeader, KmerEntry)
- **src/kmer/encoding.rs**: CLI k-mer encoding functions (encode_kmer_bytes)
- **src/database/query.rs**: CLI database query functionality
- **src/fuzzy/**: CLI fuzzy query implementation

### Testing Files
- **test_database_compatibility.py**: Comprehensive cross-platform testing framework
- **tests/**: Rust unit tests for core functionality
- **specs/007-api-compatibility/contracts/**: Contract validation tests