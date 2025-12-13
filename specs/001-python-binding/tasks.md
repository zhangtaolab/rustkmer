---

description: "Task list for Python Binding API for rustkmer implementation"
---

# Tasks: Python Binding API for rustkmer

**Input**: Design documents from `/specs/001-python-binding/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Test tasks included as per specification requirements for CLI-API consistency validation

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Python package**: `python/` directory at repository root
- **Source code**: `python/rustkmer/`
- **Tests**: `python/tests/`
- **Examples**: `python/examples/`

## Phase 1: Setup (Shared Infrastructure) ✓ COMPLETE

**Purpose**: Project initialization and basic structure

- [x] T001 Create Python package directory structure per implementation plan
- [x] T002 Initialize Python package with pyproject.toml configuration
- [x] T003 [P] Create empty module files (__init__.py) for rustkmer package
- [x] T004 [P] Create test directory structure with conftest.py
- [x] T005 [P] Create examples directory structure
- [x] T006 Create README.md for Python package with installation instructions
- [x] T007 Create LICENSE file for Python package
- [x] T008 [P] Add .gitignore entries for Python build artifacts

---

## Phase 2: Foundational (Blocking Prerequisites) ✓ COMPLETE

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T009 Create exception hierarchy in python/rustkmer/exceptions.py
- [x] T010 Create utility functions in python/rustkmer/utils.py
- [x] T011 [P] Create CLI wrapper functions for subprocess calls in python/rustkmer/utils.py
- [x] T012 Create pytest configuration in python/tests/conftest.py
- [x] T013 Create test database fixtures directory python/tests/fixtures/
- [x] T014 [P] Create basic smoke test to verify CLI accessibility

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Python Query API (Priority: P1) 🎯 MVP

**Goal**: Enable Python developers to query k-mer databases programmatically without PyO3

**Independent Test**: Perform queries on real database file and compare with CLI output for 100% consistency

### Tests for User Story 1 ✓ COMPLETE

- [x] T015 [P] [US1] Create unit test for Database.__init__ in python/tests/test_database.py
- [x] T016 [P] [US1] Create unit test for Database.query in python/tests/test_database.py
- [x] T017 [P] [US1] Create unit test for Database.query_batch in python/tests/test_database.py
- [x] T018 [P] [US1] Create integration test for CLI-API consistency in python/tests/test_integration.py
- [x] T019 [P] [US1] Create performance test for 1000 entry dump in python/tests/test_performance.py
- [x] T020 [P] [US1] Create benchmark test for dump operation timing and memory usage in python/tests/test_benchmark.py

### Implementation for User Story 1 ✓ COMPLETE

- [x] T021 [US1] Create QueryResult dataclass in python/rustkmer/query.py
- [x] T022 [US1] Implement Database class basic structure in python/rustkmer/database.py
- [x] T023 [US1] Implement Database.query method in python/rustkmer/database.py (depends on T011, T021)
- [x] T024 [US1] Implement Database.query_batch method with ThreadPoolExecutor in python/rustkmer/database.py
- [x] T025 [US1] Implement Database.dump method for streaming k-mers in python/rustkmer/database.py
- [x] T026 [US1] Add Database context manager support (__enter__/__exit__) in python/rustkmer/database.py
- [x] T027 [US1] Update main module exports in python/rustkmer/__init__.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Database Information Access (Priority: P2) ✓ COMPLETE

**Goal**: Enable researchers to retrieve metadata about k-mer databases

**Independent Test**: Retrieve database stats and verify they match CLI stats output

### Tests for User Story 2

- [x] T028 [P] [US2] Create unit test for Database.stats in python/tests/test_stats.py
- [x] T029 [P] [US2] Create unit test for DatabaseStats dataclass in python/tests/test_stats.py
- [x] T030 [P] [US2] Create integration test for stats CLI consistency in python/tests/test_integration.py

### Implementation for User Story 2

- [x] T031 [P] [US2] Create DatabaseStats dataclass in python/rustkmer/stats.py
- [x] T032 [US2] Implement Database.stats method in python/rustkmer/database.py (depends on T031)
- [x] T033 [US2] Add Database properties (path, kmer_size, is_loaded) in python/rustkmer/database.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: Polish & Cross-Cutting Concerns ✓ COMPLETE

**Purpose**: Improvements that affect multiple user stories

- [x] T034 [P] Create basic usage example in python/examples/basic_usage.py
- [x] T035 [P] Create batch query example in python/examples/batch_query.py
- [x] T036 Create large dataset processing example in python/examples/large_dataset.py
- [x] T037 [P] Add docstrings and type hints to all public APIs
- [x] T038 Add CLI path validation and helpful error messages
- [x] T039 Optimize subprocess calls for performance
- [x] T040 Add memory-efficient processing for large dump operations (define threshold: >10,000 results)
- [x] T041 Run all tests and verify CLI-API consistency with real data
- [x] T042 Update documentation with final API reference
- [x] T043 Validate pip install -e . works correctly
- [x] T044 [P] Create pre-commit hooks for code quality (black, flake8)
- [x] T045 [P] Create directory for scripts in python/scripts/
- [x] T046 [P] Add test coverage verification script in python/scripts/check_coverage.py
- [x] T047 Configure pytest to generate coverage reports and enforce 90% threshold

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-4)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Integrates with US1 Database class

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models/Classes before services
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Terminal 1: Setup tests
pytest python/tests/test_database.py::test_database_init -v

# Terminal 2: Implement core classes (parallel)
# Working on QueryResult in python/rustkmer/query.py

# Terminal 3: Implement Database class (parallel)
# Working on Database structure in python/rustkmer/database.py

# Terminal 4: Integration tests
pytest python/tests/test_integration.py -v
```

---

## Implementation Strategy

### MVP Approach (Minimum Viable Product)

1. **Start with User Story 1 only** - Core query functionality
2. **Implement subprocess wrapper first** - Foundation for all features
3. **Add basic error handling** - Standard Python exceptions
4. **Verify with real database** - Use /Users/forrest/Data/data/kmer/K19/R1_001.rkdb
5. **Ensure pip install -e . works** - Development installation

### Incremental Delivery

1. **MVP**: Single k-mer queries (T020-T022, T026)
2. **Batch 1**: Batch queries and parallel processing (T023)
3. **Batch 2**: Dump functionality (T024)
4. **Batch 3**: Database stats (US2 - T030-T032)
5. **Batch 4**: Polish and optimization (Phase 5)

### Success Metrics

- Python API query results match CLI with 100% accuracy
- 1000 entry dump completes in <5 seconds
- Memory usage stays <500MB for large databases
- pip install -e . works without Rust compilation
- All tests pass with real database data