---

description: "Task list for Python fuzzy query API implementation"
---

# Tasks: Python Fuzzy Query API

**Input**: Design documents from `/specs/001-python-fuzzy-query/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are included as requested in the feature specification for ensuring reliability.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Python bindings**: `python/rustkmer/` for package, `python/tests/` for tests
- **Rust implementation**: `src/` for source, `tests/` for Rust tests
- **Examples**: `python/examples/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create Python fuzzy query module structure in python/rustkmer/
- [ ] T002 [P] Verify existing rustkmer CLI fuzzy-query command is functional

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Add fuzzy query parsing functions to python/rustkmer/utils.py
- [ ] T004 [P] Update python/rustkmer/__init__.py to expose fuzzy query classes
- [ ] T005 Add fuzzy query exception classes to python/rustkmer/exceptions.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Basic Fuzzy Query Search (Priority: P1) 🎯 MVP

**Goal**: Allow researchers to find k-mers similar to their query with configurable mutation tolerance

**Independent Test**: Query a known k-mer with 1 mutation tolerance and verify all variants at distance 0 and 1 are returned with correct counts and mutation information

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T006 [P] [US1] Create unit tests for FuzzyMatchResult class in python/tests/test_fuzzy_query.py
- [ ] T007 [P] [US1] Create unit tests for FuzzyQueryResult class in python/tests/test_fuzzy_query.py
- [ ] T008 [P] [US1] Create integration test for single fuzzy query in python/tests/test_fuzzy_query.py
- [ ] T009 [P] [US1] Create test for mutation tolerance validation in python/tests/test_fuzzy_query.py

### Implementation for User Story 1

- [ ] T010 [US1] Create FuzzyMatchResult dataclass in python/rustkmer/fuzzy_query.py
- [ ] T011 [US1] Create FuzzyQueryResult class with analysis methods in python/rustkmer/fuzzy_query.py
- [ ] T012 [US1] Implement fuzzy_query method in Database class in python/rustkmer/database.py
- [ ] T013 [US1] Add CLI argument building for fuzzy-query command in python/rustkmer/database.py
- [ ] T014 [US1] Add output parsing for fuzzy query results in python/rustkmer/utils.py
- [ ] T015 [US1] Add error handling for fuzzy query validation in python/rustkmer/database.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Batch Fuzzy Query Processing (Priority: P2)

**Goal**: Enable researchers to query hundreds of k-mers in parallel for efficient large-scale analyses

**Independent Test**: Query a batch of 10 k-mers with fuzzy matching and verify all results are returned correctly with proper association between input queries and their respective matches

### Tests for User Story 2

- [ ] T016 [P] [US2] Create unit tests for FuzzyBatchResult class in python/tests/test_fuzzy_query.py
- [ ] T017 [P] [US2] Create integration test for batch fuzzy query in python/tests/test_fuzzy_query.py
- [ ] T018 [US2] Create test for batch error handling with invalid k-mers in python/tests/test_fuzzy_query.py

### Implementation for User Story 2

- [ ] T019 [US2] Create FuzzyBatchResult class with summary methods in python/rustkmer/fuzzy_query.py
- [ ] T020 [US2] Implement fuzzy_query_batch method in Database class in python/rustkmer/database.py
- [ ] T021 [US2] Add parallel execution logic using ThreadPoolExecutor in python/rustkmer/database.py
- [ ] T022 [US2] Add batch validation for multiple k-mers in python/rustkmer/database.py
- [ ] T023 [US2] Add batch output parsing in python/rustkmer/utils.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Result Analysis and Export (Priority: P3)

**Goal**: Provide researchers with tools to analyze mutation patterns and export data in different formats

**Independent Test**: Perform a fuzzy query and export results in JSON, table, and TSV formats to verify correct formatting and data preservation

### Tests for User Story 3

- [ ] T024 [P] [US3] Create test for JSON export format in python/tests/test_fuzzy_query.py
- [ ] T025 [P] [US3] Create test for table export format in python/tests/test_fuzzy_query.py
- [ ] T026 [P] [US3] Create test for TSV export format in python/tests/test_fuzzy_query.py
- [ ] T027 [P] [US3] Create test for mutation pattern analysis methods in python/tests/test_fuzzy_query.py

### Implementation for User Story 3

- [ ] T028 [US3] Implement to_json() method in FuzzyQueryResult class in python/rustkmer/fuzzy_query.py
- [ ] T029 [US3] Implement to_table() method with row limiting in FuzzyQueryResult class in python/rustkmer/fuzzy_query.py
- [ ] T030 [US3] Implement get_matches_by_distance() analysis method in FuzzyQueryResult class in python/rustkmer/fuzzy_query.py
- [ ] T031 [US3] Implement get_top_matches() analysis method in FuzzyQueryResult class in python/rustkmer/fuzzy_query.py
- [ ] T032 [US3] Implement batch summary table in FuzzyBatchResult class in python/rustkmer/fuzzy_query.py
- [ ] T033 [US3] Add output format support (json, table, tsv) to CLI arguments in python/rustkmer/database.py

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T034 [P] Create fuzzy query demonstration script in python/examples/fuzzy_query_demo.py
- [ ] T035 [P] Add performance benchmarks for batch vs individual queries
- [ ] T036 [P] Update rustkmer Python package documentation to include fuzzy query examples
- [ ] T037 Run quickstart.md validation with actual implementation
- [ ] T038 [P] Add comprehensive docstrings to all fuzzy query classes and methods

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Reuses classes from US1 but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Extends classes from US1/US2 but independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Core classes before Database methods
- Single query before batch query (US2 depends on US1 classes)
- Basic functionality before analysis features (US3 depends on US1/US2 classes)

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Analysis methods in US3 marked [P] can run in parallel
- Documentation and example tasks in Polish phase can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Create unit tests for FuzzyMatchResult class in python/tests/test_fuzzy_query.py"
Task: "Create unit tests for FuzzyQueryResult class in python/tests/test_fuzzy_query.py"
Task: "Create integration test for single fuzzy query in python/tests/test_fuzzy_query.py"
Task: "Create test for mutation tolerance validation in python/tests/test_fuzzy_query.py"

# Launch core class creation together:
Task: "Create FuzzyMatchResult dataclass in python/rustkmer/fuzzy_query.py"
Task: "Create FuzzyQueryResult class with analysis methods in python/rustkmer/fuzzy_query.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2 (after US1 classes are available)
   - Developer C: User Story 3 (after US1/US2 classes are available)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Total tasks: 38
- Tasks per user story: US1 (10 tasks), US2 (8 tasks), US3 (10 tasks)
- Parallel opportunities identified at multiple levels
- MVP scope: Complete Phase 1-3 for basic fuzzy query functionality