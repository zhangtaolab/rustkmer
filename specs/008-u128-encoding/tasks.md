---

description: "Task list for u128 encoding upgrade implementation"
---

# Tasks: u128-encoding-upgrade

**Input**: Design documents from `/specs/008-u128-encoding/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: All programs require comprehensive testing as specified by user

**Organization**: Tasks are grouped by user story and program to enable independent implementation and testing

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create test data fixtures for k=33-64 in tests/fixtures/
- [ ] T002 Setup benchmark infrastructure for u128 performance testing
- [ ] T003 [P] Create consistency test framework to compare u64 vs u128 outputs

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Update Kmer struct to support u128 in src/kmer/mod.rs
- [ ] T005 [P] Implement u128 encoding functions in src/kmer/encoding.rs
- [ ] T006 [P] Implement u128 decoding functions in src/kmer/encoding.rs
- [ ] T007 [P] Update canonical k-mer operations for u128 in src/kmer/operations.rs
- [ ] T008 [P] Update reverse complement for u128 in src/kmer/operations.rs
- [ ] T009 Update database header to version 2 with u128 support in src/database/format.rs
- [ ] T010 [P] Update KmerEntry struct for u128 in src/database/format.rs
- [ ] T011 [P] Update database I/O operations for 16-byte entries in src/database/format.rs
- [ ] T012 Update binary search for 16-byte stride in src/database/query.rs
- [ ] T013 [P] Update memory mapping offsets for new format in src/database/mmap.rs
- [ ] T014 Add new error types for u128 validation in src/error.rs
- [ ] T015 [P] Update Python bindings for u128 support in src/python/lib.rs
- [ ] T016 Update Cargo.toml with any new dependencies if needed

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Large K-mer Database Creation (Priority: P1) 🎯 MVP

**Goal**: Enable creation of k-mer databases with k-sizes 33-64

**Independent Test**: Create databases with k=33, k=48, k=64 and verify all k-mers are correctly stored

### Tests for Count Command

- [ ] T017 [P] [US1] Create unit tests for count command with k>32 in tests/unit/cli/test_count.rs
- [ ] T018 [P] [US1] Create integration tests for count with large k-mers in tests/integration/test_count_large.rs
- [ ] T019 [US1] Create property-based tests for count correctness in tests/property/test_count.rs

### Implementation for Count Command

- [ ] T020 [P] [US1] Update count command validation for k up to 64 in src/cli/commands/count.rs
- [ ] T021 [US1] Update count command to use u128 encoding in src/cli/commands/count.rs (depends on T005)
- [ ] T022 [US1] Add memory limit configuration to count command in src/cli/commands/count.rs
- [ ] T023 [US1] Add verbose output for large k-mer processing statistics in src/cli/commands/count.rs
- [ ] T024 [US1] Update count command error messages for k>32 scenarios in src/cli/commands/count.rs

---

## Phase 4: User Story 2 - Large K-mer Database Querying (Priority: P1) 🎯 MVP

**Goal**: Enable efficient querying of k-mer databases with k-sizes 33-64

**Independent Test**: Query known k-mers in k=48 and k=64 databases, verify correct counts

### Tests for Query Command

- [ ] T025 [P] [US2] Create unit tests for query command with k>32 in tests/unit/cli/test_query.rs
- [ ] T026 [P] [US2] Create integration tests for query with large k-mers in tests/integration/test_query_large.rs
- [ ] T027 [P] [US2] Create batch query tests for performance in tests/integration/test_query_batch.rs

### Implementation for Query Command

- [ ] T028 [P] [US2] Update query command to handle u128 k-mers in src/cli/commands/query.rs (depends on T006)
- [ ] T029 [US2] Update query command batch processing for u128 in src/cli/commands/query.rs
- [ ] T030 [US2] Add concurrent query controls in src/cli/commands/query.rs
- [ ] T031 [US2] Update query JSON/TSV output formatting for large k-mers in src/cli/commands/query.rs

---

## Phase 5: Additional Programs Implementation (Priority: P1)

### Dump Command

#### Tests for Dump Command

- [ ] T032 [P] Create unit tests for dump with u128 entries in tests/unit/cli/test_dump.rs
- [ ] T033 [P] Create integration tests for dump output formats in tests/integration/test_dump.rs

#### Implementation for Dump Command

- [ ] T034 [P] Update dump command for 16-byte entries in src/cli/commands/dump.rs
- [ ] T035 [P] Update dump command formatting for large k-mers in src/cli/commands/dump.rs

### Fuzzy Query Command

#### Tests for Fuzzy Query

- [ ] T036 [P] Create unit tests for fuzzy query with u128 in tests/unit/cli/test_fuzzy.rs
- [ ] T037 [P] Create integration tests for fuzzy query accuracy in tests/integration/test_fuzzy.rs

#### Implementation for Fuzzy Query

- [ ] T038 [P] Update fuzzy query for u128 k-mers in src/cli/commands/fuzzy.rs
- [ ] T039 [P] Update fuzzy query distance calculations for larger k-mers in src/cli/commands/fuzzy.rs

### Fuzzy Query Batch Command

#### Tests for Fuzzy Query Batch

- [ ] T040 [P] Create unit tests for fuzzy query batch in tests/unit/cli/test_fuzzy_batch.rs
- [ ] T041 [P] Create performance tests for fuzzy batch operations in tests/benchmarks/test_fuzzy_batch.rs

#### Implementation for Fuzzy Query Batch

- [ ] T042 [P] Implement fuzzy query batch command in src/cli/commands/fuzzy_batch.rs
- [ ] T043 [P] Optimize batch processing for u128 in src/cli/commands/fuzzy_batch.rs

### Merge Command

#### Tests for Merge Command

- [ ] T044 [P] Create unit tests for merge with u128 databases in tests/unit/cli/test_merge.rs
- [ ] T045 [P] Create integration tests for merge consistency in tests/integration/test_merge.rs

#### Implementation for Merge Command

- [ ] T046 [P] Update merge command for u128 database compatibility in src/cli/commands/merge.rs
- [ ] T047 [P] Add merge validation for k-size consistency in src/cli/commands/merge.rs

---

## Phase 6: User Story 3 - Statistical Consistency (Priority: P1)

**Goal**: Ensure u128 implementation produces identical statistics to u64 for comparable inputs

**Independent Test**: Process identical datasets with both implementations and compare all outputs

### Consistency Tests

- [ ] T048 [P] [US3] Create consistency test suite framework in tests/consistency/mod.rs
- [ ] T049 [P] [US3] Create test for k≤32 statistical comparison in tests/consistency/test_small_k.rs
- [ ] T050 [P] [US3] Create test for ambiguous base handling consistency in tests/consistency/test_ambiguous.rs
- [ ] T051 [P] [US3] Create test for canonical representation consistency in tests/consistency/test_canonical.rs
- [ ] T052 [US3] Create end-to-end consistency validation in tests/consistency/test_full_pipeline.rs

### Implementation for Consistency Validation

- [ ] T053 [US3] Implement statistics comparison utilities in tests/consistency/utils.rs
- [ ] T054 [US3] Add consistency test data generation in tests/consistency/generators.rs

---

## Phase 7: User Story 4 - Performance Maintenance (Priority: P2)

**Goal**: Ensure u128 implementation maintains acceptable performance

**Independent Test**: Benchmark with various k-sizes and measure operation times

### Performance Benchmarks

- [ ] T055 [P] [US4] Create encoding benchmarks for k=1-64 in tests/benchmarks/encoding_bench.rs
- [ ] T056 [P] [US4] Create query benchmarks for k=64 in tests/benchmarks/query_bench.rs
- [ ] T057 [P] [US4] Create memory usage benchmarks for large databases in tests/benchmarks/memory_bench.rs
- [ ] T058 [P] [US4] Create concurrent access benchmarks in tests/benchmarks/concurrent_bench.rs

### Performance Optimizations

- [ ] T059 [US4] Optimize u128 encoding for common k-sizes in src/kmer/encoding.rs
- [ ] T060 [US4] Optimize binary search for 128-bit comparisons in src/database/query.rs
- [ ] T061 [US4] Implement SIMD optimizations if beneficial in src/kmer/simd_ops.rs

---

## Phase 8: Python API Updates

**Purpose**: Ensure Python API fully supports u128 k-mers

### Python API Tests

- [ ] T062 [P] Create Python tests for u128 k-mer creation in tests/python/test_u128_creation.py
- [ ] T063 [P] Create Python tests for large k-mer queries in tests/python/test_large_queries.py
- [ ] T064 [P] Create Python tests for batch operations with u128 in tests/python/test_batch_u128.py

### Python API Implementation

- [ ] T065 [P] Update SimpleKmerCounter for k>32 in src/python/lib.rs
- [ ] T066 [P] Update SimpleDatabase for u128 queries in src/python/lib.rs
- [ ] T067 [P] Add u128-specific example scripts in examples/python/u128_examples.py

---

## Phase 9: Documentation & Polish

**Purpose**: Complete documentation and final refinements

- [ ] T068 Update README.md with u128 support information
- [ ] T069 Update man pages for all commands with k>32 information
- [ ] T070 [P] Add u128 examples to documentation in docs/examples/
- [ ] T071 [P] Create migration guide from u64 to u128 in docs/migration.md
- [ ] T072 Update CHANGELOG.md with u128 upgrade notes
- [ ] T073 [P] Run full test suite and fix any failures
- [ ] T074 [P] Run benchmarks and verify performance targets met
- [ ] T075 Final code review and cleanup

**Checkpoint**: All features complete, tested, and documented

---

## Dependencies

### Story Completion Order

1. **Phase 1** - Setup (T001-T003)
2. **Phase 2** - Foundational (T004-T016) - *Must complete before any stories*
3. **Phase 3** - User Story 1: Database Creation (T017-T024)
4. **Phase 4** - User Story 2: Database Querying (T025-T031)
5. **Phase 5** - Additional Programs (T032-T047) - *Can run in parallel with US3*
6. **Phase 6** - User Story 3: Statistical Consistency (T048-T054) - *Depends on US1 & US2*
7. **Phase 7** - User Story 4: Performance (T055-T061) - *Depends on US1 & US2*
8. **Phase 8** - Python API (T062-T067) - *Can run in parallel with US3 & US4*
9. **Phase 9** - Documentation (T068-T075)

### Parallel Execution Opportunities

Within each phase, tasks marked `[P]` can be executed in parallel as they work on different files and have no dependencies on incomplete tasks.

### MVP Scope

For Minimum Viable Product, complete:
- Phase 1 (Setup)
- Phase 2 (Foundational)
- Phase 3 (User Story 1: Count command)
- Phase 4 (User Story 2: Query command)
- Basic tests from these phases

This delivers the core functionality of creating and querying large k-mer databases.

### Implementation Strategy

1. **Start with Phase 1 & 2** to establish the foundation
2. **Implement User Stories 1 & 2** for the core MVP functionality
3. **Add remaining programs** (dump, fuzzy-query, merge) to complete feature set
4. **Validate consistency** to ensure scientific correctness
5. **Optimize performance** to meet requirements
6. **Update Python API** for complete coverage
7. **Polish and document** for release readiness

Each phase should result in a testable increment that delivers value to users.