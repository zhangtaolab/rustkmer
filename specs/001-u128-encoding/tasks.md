---

description: "Task list for implementing u128 encoding support in rustkmer"
---

# Tasks: Support k-mers up to 64 bases with u128 encoding

**Input**: Design documents from `/specs/001-u128-encoding/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Include comprehensive tests to ensure encoding consistency between u64 and u128 implementations

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and testing framework setup

- [ ] T001 Add proptest dependency to Cargo.toml for property-based testing
- [ ] T002 [P] Create test data directory structure in tests/data/
- [ ] T003 [P] Create benchmark framework in benches/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Update encoding constants in src/kmer/encoding.rs to support up to k=64
- [ ] T005 [P] Create property-based tests for encoding consistency in tests/property/test_encoding.rs
- [ ] T006 Update KmerEntry struct to use u128 in src/database/format.rs
- [ ] T007 Update DatabaseHeader to version 2 format in src/database/format.rs
- [ ] T008 Update KmerCounter to use HashMap<u128, u32> in src/hash/table.rs

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Process long DNA sequences (Priority: P1) 🎯 MVP

**Goal**: Enable counting and querying k-mers up to 64 bases

**Independent Test**: Create a synthetic FASTA file with 40-base k-mers, count them with `rustkmer count -k 40`, and verify all k-mers are correctly counted and queryable

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T009 [P] [US1] Property test for u128 encoding round-trip in tests/property/test_u128_encoding.rs
- [ ] T010 [P] [US1] Integration test for count command with k=40 in tests/integration/test_count_long_kmers.rs
- [ ] T011 [P] [US1] Integration test for query command with u128 in tests/integration/test_query_u128.rs
- [ ] T012 [P] [US1] Benchmark test for encoding performance in benches/bench_encoding.rs

### Implementation for User Story 1

- [ ] T013 [US1] Update encode_kmer function to return u128 in src/kmer/encoding.rs
- [ ] T014 [US1] Update decode_kmer function to accept u128 in src/kmer/encoding.rs
- [ ] T015 [US1] Update reverse_complement to handle u128 in src/kmer/canonical.rs
- [ ] T016 [US1] Update database I/O to read/write 16-byte k-mers in src/database/format.rs
- [ ] T017 [US1] Update count command to handle u128 in src/cli/commands/count.rs
- [ ] T018 [US1] Update query command to handle u128 lookups in src/database/query.rs
- [ ] T019 [US1] Add validation for k≤64 in src/cli/commands/count.rs

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Database format migration (Priority: P1)

**Goal**: Provide clear error messages for old database format and guide users to recreate databases

**Independent Test**: Attempt to open an old v1 database and verify a clear error message with migration instructions is shown

### Tests for User Story 2

- [ ] T020 [P] [US2] Unit test for version detection in tests/unit/test_database_format.rs
- [ ] T021 [P] [US2] Integration test for error message on old format in tests/integration/test_migration_errors.rs

### Implementation for User Story 2

- [ ] T022 [US2] Add version check on database open in src/database/format.rs
- [ ] T023 [US2] Create clear error message for v1 format in src/database/format.rs
- [ ] T024 [US2] Update all database open paths to check version in src/database/mod.rs
- [ ] T025 [US2] Add documentation references in error messages

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Support mixed k-mer size workflows (Priority: P2)

**Goal**: Ensure consistent performance and accuracy across all k-mer sizes (1-64)

**Independent Test**: Create databases with k=20, 35, 50, 64 and verify performance scales with database size, not k-mer length

### Tests for User Story 3

- [ ] T026 [P] [US3] Performance regression test across k-mer sizes in tests/regression/test_k_size_scaling.rs
- [ ] T027 [P] [US3] Integration test for all k-mer sizes in tests/integration/test_all_k_sizes.rs

### Implementation for User Story 3

- [ ] T028 [US3] Update dump command for u128 entries in src/cli/commands/dump.rs
- [ ] T029 [US3] Update merge command for u128 entries in src/database/merge.rs
- [ ] T030 [US3] Update fuzzy query for u128 in src/fuzzy/mod.rs
- [ ] T031 [US3] Optimize memory layout for u128 in src/database/query.rs
- [ ] T032 [US3] Add performance metrics collection in src/cli/commands/count.rs

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Update Python bindings and ensure overall system integrity

- [ ] T033 [P] Update Python bindings for u128 support in src/python/lib.rs
- [ ] T034 [P] Add unit tests for canonical k-mer with u128 in tests/unit/test_canonical.rs
- [ ] T035 Update documentation in README.md for new k-mer limits
- [ ] T036 Update CHANGELOG.md with breaking changes
- [ ] T037 Run comprehensive performance benchmarks
- [ ] T038 Validate quickstart examples against implementation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (US1 → US2 → US3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - Core encoding functionality
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Error handling for format
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Depends on US1 core functionality

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Core encoding before database format
- Database format before CLI commands
- CLI commands before Python bindings
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Tests for each story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Property test for u128 encoding round-trip in tests/property/test_u128_encoding.rs"
Task: "Integration test for count command with k=40 in tests/integration/test_count_long_kmers.rs"
Task: "Integration test for query command with u128 in tests/integration/test_query_u128.rs"
Task: "Benchmark test for encoding performance in benches/bench_encoding.rs"

# Launch core encoding updates together:
Task: "Update encode_kmer function to return u128 in src/kmer/encoding.rs"
Task: "Update decode_kmer function to accept u128 in src/kmer/encoding.rs"
Task: "Update reverse_complement to handle u128 in src/kmer/canonical.rs"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test with 40-base k-mers, verify count and query work
5. Deploy/demo MVP supporting k>32

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Complete Phase 6 → Final release

### Critical Path Testing

At each step, verify:
- Encoding consistency: u64 and u128 produce same results for k≤32
- Performance: no significant regression for k≤32
- Accuracy: all k-mers up to 64 bases encode/decode correctly
- Database integrity: version 2 format reads/writes correctly

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD approach)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- CRITICAL: Maintain encoding consistency between old and new implementations