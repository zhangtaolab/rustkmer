---

description: "Task list for rustkmer query bug fixes"
---

# Tasks: RustKmer Query Bug Fixes

**Feature**: RustKmer Query Bug Fixes
**Branch**: `002-jellyfish-query-implementation`
**Date**: 2025-11-28
**Status**: Bug Analysis Complete - Ready for Implementation

**Input**: Comprehensive bug analysis from `/tmp/rustkmer_vs_jellyfish_test_report.md`
**MVP Scope**: Fix critical canonical mode and data reading bugs to restore query functionality.

## Phase 1: Critical Bug Analysis & Setup

**Purpose**: Prepare environment and validate bug reproduction

- [ ] T001 Create test database with known k-mer counts for bug validation
- [ ] T002 [P] Set up bug reproduction test with failing query cases from test report
- [ ] T003 [P] Validate test environment matches conditions from bug report

---

## Phase 2: Canonical K-mer Encoding Fix (Critical)

**Purpose**: Fix canonical mode mismatch between database creation and querying

**⚠️ CRITICAL**: This fixes the primary root cause of query failures

### Tests for Canonical Encoding Fix (TDD - Write First)

- [ ] T004 [P] Test canonical k-mer encoding consistency in tests/unit/database/query_canonical_tests.rs
- [ ] T005 [P] Test query with database created in canonical mode in tests/integration/canonical_query_test.rs

### Implementation for Canonical Encoding Fix (After Tests Fail)

- [ ] T006 [P] Fix query_kmer() to check database canonical mode in src/database/query.rs
- [ ] T007 Add canonical k-mer transformation to query encoding in src/database/query.rs (depends on T006)
- [ ] T008 [P] Add validation for k-mer encoding consistency in src/database/query.rs
- [ ] T009 Add canonical mode error handling and user feedback in src/database/query.rs

**Checkpoint**: Canonical mode queries should now work correctly

---

## Phase 3: Data Reading Validation Fix (Critical)

**Purpose**: Fix file offset calculation and data reading issues

### Tests for Data Reading Fix

- [ ] T010 [P] Test file offset calculation accuracy in tests/unit/database/query_offset_tests.rs
- [ ] T011 [P] Test binary search data consistency with dump output in tests/integration/query_consistency_test.rs

### Implementation for Data Reading Fix

- [ ] T012 Verify and fix file offset calculation in read_entry_at() in src/database/query.rs
- [ ] T013 [P] Add bounds checking for binary search indices in src/database/query.rs
- [ ] T014 [P] Add data validation consistency with dump function in src/database/query.rs
- [ ] T015 Fix binary search data reading to match dump function format in src/database/query.rs

**Checkpoint**: File reading should be consistent and accurate

---

## Phase 4: Query Algorithm Improvements (High)

**Purpose**: Add robustness and better user experience

### Tests for Algorithm Improvements

- [ ] T016 [P] Test query debug mode and error reporting in tests/unit/database/query_debug_tests.rs
- [ ] T017 [P] Test end-to-end count → dump → query workflow in tests/integration/full_workflow_test.rs

### Implementation for Algorithm Improvements

- [ ] T018 [P] Add debug mode for tracing query execution in src/database/query.rs
- [ ] T019 [P] Improve error messages for mismatched encodings in src/database/query.rs
- [ ] T020 Add query validation and user feedback improvements in src/database/query.rs
- [ ] T021 [P] Optimize performance for large database queries in src/database/query.rs

**Checkpoint**: Query should be robust and user-friendly

---

## Phase 5: User Story 1 - Individual K-mer Query Bug Fixes (Priority: P1) 🎯 MVP

**Goal**: Fix individual k-mer queries to return correct counts matching dump and jellyfish results

**Independent Test**: Query individual k-mers from test database and verify exact match with dump output

### Tests for Individual Query Fixes

- [ ] T022 [P] [US1] Test individual query correctness vs dump output in tests/integration/individual_query_test.rs
- [ ] T023 [P] [US1] Test query error handling for invalid inputs in tests/unit/database/query_error_tests.rs

### Implementation for Individual Query Fixes

- [ ] T024 [US1] Fix query_kmer() to return correct counts in src/database/query.rs
- [ ] T025 [US1] Ensure query output format matches jellyfish compatibility in src/cli/commands/query.rs
- [ ] T026 [US1] Add comprehensive validation for individual queries in src/cli/commands/query.rs

### Implementation for Edge Case Handling

- [ ] T026a [US1] Implement corrupted database detection with specific error message in src/database/query.rs
- [ ] T026b [US1] Add invalid k-mer character validation with continue-on-error logic in src/cli/commands/query.rs
- [ ] T026c [US1] Implement memory-insufficient fallback to disk-based queries in src/database/query.rs
- [ ] T026d [US1] Add concurrent access handling with retry logic in src/database/query.rs
- [ ] T026e [US1] Implement file permission checking with specific error messages in src/cli/commands/query.rs

**Checkpoint**: Individual queries should work exactly like jellyfish with robust edge case handling

---

## Phase 6: User Story 2 - Batch K-mer Query Bug Fixes (Priority: P1)

**Goal**: Fix batch k-mer queries to return correct counts for all input k-mers

**Independent Test**: Query multiple k-mers and verify all results match dump output

### Tests for Batch Query Fixes

- [ ] T032 [P] [US2] Test batch query correctness vs dump output in tests/integration/batch_query_test.rs
- [ ] T033 [P] [US2] Test batch query with mixed valid/invalid k-mers in tests/unit/database/batch_query_tests.rs

### Implementation for Batch Query Fixes

- [ ] T034 [US2] Fix query_multiple() to handle all k-mers correctly in src/database/query.rs
- [ ] T035 [US2] Ensure batch query output format matches jellyfish in src/cli/commands/query.rs
- [ ] T036 [US2] Add error handling for mixed valid/invalid batch queries in src/cli/commands/query.rs

**Checkpoint**: Batch queries should work correctly for all inputs

---

## Phase 7: User Story 3 - Sequence File Query Bug Fixes (Priority: P2)

**Goal**: Fix sequence file queries to process FASTA files correctly

**Independent Test**: Query sequences from FASTA file and verify all constituent k-mers are processed

### Tests for Sequence File Query Fixes

- [ ] T037 [P] [US3] Test FASTA file query processing in tests/integration/fasta_query_test.rs
- [ ] T038 [P] [US3] Test sequence file handling of edge cases in tests/unit/database/fasta_query_tests.rs

### Implementation for Sequence File Query Fixes

- [ ] T039 [US3] Fix FASTA file k-mer extraction and querying in src/cli/commands/query.rs
- [ ] T040 [US3] Add graceful handling of short sequences in FASTA files in src/cli/commands/query.rs
- [ ] T041 [US3] Ensure sequence file query output format matches expectations in src/cli/commands/query.rs

**Checkpoint**: Sequence file queries should process all valid k-mers correctly

---

## Phase 8: User Story 4 - Interactive Query Mode Bug Fixes (Priority: P3)

**Goal**: Fix interactive query mode to handle stdin input correctly

**Independent Test**: Enter interactive mode and query multiple k-mers via stdin

### Tests for Interactive Query Fixes

- [ ] T042 [P] [US4] Test interactive mode stdin processing in tests/integration/interactive_query_test.rs
- [ ] T043 [P] [US4] Test interactive mode error handling in tests/unit/database/interactive_query_tests.rs

### Implementation for Interactive Query Fixes

- [ ] T044 [US4] Fix interactive mode stdin k-mer processing in src/cli/commands/query.rs
- [ ] T045 [US4] Add proper handling of multiple k-mers per line in interactive mode in src/cli/commands/query.rs
- [ ] T046 [US4] Ensure interactive mode output formatting is consistent in src/cli/commands/query.rs

**Checkpoint**: Interactive mode should work seamlessly for exploratory analysis

---

## Phase 9: Comprehensive Testing & Validation (High)

**Purpose**: Ensure all fixes work together and maintain compatibility

### Integration Tests

- [ ] T047 [P] Create comprehensive test suite with real data from bug report in tests/integration/real_data_test.rs
- [ ] T048 [P] Add property-based tests for query correctness in tests/unit/database/property_tests.rs
- [ ] T049 [P] Performance benchmarking against jellyfish in tests/benchmarks/query_benchmarks.rs

### Regression Tests

- [ ] T050 [P] Add regression tests for specific bugs from test report in tests/regression/bug_report_tests.rs
- [ ] T051 [P] Validate end-to-end workflow with count → dump → query in tests/integration/full_workflow_test.rs

**Checkpoint**: All query functionality should be robust and correct

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements and documentation

- [ ] T052 [P] Update CLI documentation with query bug fix notes in docs/query.md
- [ ] T053 [P] Code cleanup and refactoring of query module in src/database/query.rs
- [ ] T054 Performance optimization across all query modes in src/database/query.rs
- [ ] T055 [P] Additional unit tests for edge cases in tests/unit/database/query_edge_case_tests.rs
- [ ] T056 Run comprehensive validation with test report scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

- **Critical Bug Analysis (Phase 1)**: No dependencies - can start immediately
- **Canonical Encoding Fix (Phase 2)**: Depends on Phase 1 completion - BLOCKS all other phases
- **Data Reading Fix (Phase 3)**: Depends on Phase 2 completion - BLOCKS user story fixes
- **User Stories (Phase 5-8)**: All depend on Phases 2-4 completion
- **Testing & Validation (Phase 9)**: Depends on all user story fixes
- **Polish (Final Phase)**: Depends on all previous phases

### Within Each Phase

- Tests MUST be written and validated before implementation fixes
- Critical fixes (canonical, data reading) before user story improvements
- Core implementation before integration and polish
- Each phase should be complete and testable before proceeding

### Parallel Opportunities

- All Analysis tasks marked [P] can run in parallel
- All Canonical Encoding tasks marked [P] can run in parallel (within Phase 2)
- All Data Reading tasks marked [P] can run in parallel (within Phase 3)
- User Story phases can proceed in parallel after core fixes (Phase 4)
- All tests for a phase marked [P] can run in parallel
- Different user story fixes can be worked on in parallel by different team members

---

## Parallel Example: Critical Bug Fixes

```bash
# Launch all canonical encoding tests together:
Task: "Test canonical k-mer encoding consistency in tests/unit/database/query_canonical_tests.rs"
Task: "Test query with database created in canonical mode in tests/integration/canonical_query_test.rs"

# Launch all canonical encoding fixes together:
Task: "Fix query_kmer() to check database canonical mode in src/database/query.rs"
Task: "Add validation for k-mer encoding consistency in src/database/query.rs"
```

---

## Implementation Strategy

### Critical Fixes First (Phases 2-3)

1. Complete Phase 1: Bug Analysis and Setup
2. Complete Phase 2: Canonical Encoding Fix (CRITICAL)
3. Complete Phase 3: Data Reading Validation (CRITICAL)
4. **STOP and VALIDATE**: Test critical fixes with reproduction cases
5. Verify query now works with test report examples

### Incremental User Story Delivery

1. Fix Core Issues (Phases 1-3) → Basic queries work
2. Add User Story 1 fixes → Individual queries work robustly
3. Add User Story 2 fixes → Batch queries work robustly
4. Add User Stories 3-4 fixes → Advanced query modes work
5. Each phase adds functionality without breaking previous fixes

### Parallel Team Strategy

With multiple developers:

1. Team completes Critical Bug Analysis (Phase 1) together
2. Once Critical Analysis is done:
   - Developer A: Canonical Encoding Fix (Phase 2)
   - Developer B: Data Reading Validation (Phase 3)
   - Developer C: Test Infrastructure (Phase 1 tests)
3. After critical fixes:
   - Developer A: User Stories 1-2 (Individual/Batch)
   - Developer B: User Stories 3-4 (Sequence/Interactive)
   - Developer C: Testing & Validation (Phase 9)

---

## Success Criteria

1. **Query Correctness**: All query modes return exactly the same results as dump and jellyfish
2. **Bug Resolution**: All specific issues from test report are resolved
3. **Performance**: Query time meets original specifications (<1ms individual, <10ms batch)
4. **Robustness**: Proper error handling and validation for all edge cases
5. **Compatibility**: Full jellyfish compatibility maintained
6. **Coverage**: Comprehensive test coverage for all query functionality

## Notes

- **Critical Priority**: Phases 2-3 (canonical encoding and data reading) must be completed first
- **Test-Driven**: All test tasks should be written and validated before implementation
- **Incremental**: Each phase should be independently testable before proceeding
- **Bug Report Focus**: All fixes should address specific issues identified in the test report
- **Validation**: Use exact same test data and scenarios from the bug reproduction report

**Total Tasks**: 56
**Critical Fix Tasks**: 15 (Phases 2-3)
**User Story Fix Tasks**: 23 (Phases 5-8 including edge cases)
**Testing & Validation Tasks**: 9 (Phase 9)
**Polish Tasks**: 9 (Phase 10)

**Parallel Opportunities**: 43 tasks (77%) can be developed in parallel, enabling efficient bug fix timeline.

## Current Implementation Status: 🐛 BUGS IDENTIFIED - READY FOR FIXES

All query functionality is implemented but contains critical bugs identified in comprehensive testing:

- ❌ **Canonical Mode Mismatch**: Query doesn't apply canonical transformation when database was created with canonical mode
- ❌ **File Offset Calculation Error**: Binary search offset calculation may be incorrect, returning wrong counts
- ❌ **Missing Query Validation**: No validation that query input matches database encoding parameters

**Ready for Bug Fixing** - The implementation has a complete foundation but requires the 51 tasks above to resolve identified issues and restore full functionality.