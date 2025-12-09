---

description: "Task list for implementing stats command with k-mer count frequency distribution"
---

# Tasks: Stats Command Implementation

**Input**: Feature specification and design documents for implementing `rustkmer stats` command
**Goal**: Implement a high-performance statistics command that calculates comprehensive statistics for RKDB databases using streaming algorithms

## Format: `[ID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3 from spec.md)

## Phase 1: Setup Tasks

**Purpose**: Initialize project and add dependencies

- [ ] T001 Add tdigest dependency to Cargo.toml for streaming quantile estimation
- [ ] T002 [P] Create stats module structure in src/database/stats.rs
- [ ] T003 [P] Create command module placeholder in src/cli/commands/stats.rs

---

## Phase 2: Foundational Tasks

**Purpose**: Implement core data structures and error handling that all user stories depend on

- [ ] T004 Implement DatabaseStatistics struct with serde serialization in src/database/stats.rs
- [ ] T005 Implement StatsConfiguration struct for command options in src/database/stats.rs
- [ ] T006 [P] Implement StreamingStatsProcessor for memory-efficient calculation in src/database/stats.rs
- [ ] T007 [P] Define StatsError enum with thiserror in src/database/stats.rs
- [ ] T008 [P] Implement OutputFormat enum and formatters in src/database/stats.rs

---

## Phase 3: User Story 1 - Database Statistics Overview (P1)

**Goal**: Calculate and display basic database statistics (total/unique k-mers, min/max/mean/median counts)

**Independent Test**: Can be tested by running stats on a database with known counts and verifying all statistics are correct

### Implementation Tasks

- [ ] T009 Add Stats command variant to CLI Commands enum in src/cli/args.rs
- [ ] T010 Implement stats argument parsing with clap in src/cli/args.rs
- [ ] T011 [P] Implement basic statistics calculation (total, unique, min, max, mean) in StreamingStatsProcessor
- [ ] T012 [P] Implement TDigest integration for approximate median calculation
- [ ] T013 [P] Implement memory-mapped database reading for stats in src/database/stats.rs
- [ ] T014 [P] Implement text output formatter for human-readable statistics
- [ ] T015 Implement stats command handler in src/cli/commands/stats.rs
- [ ] T016 Wire stats command into main.rs command routing

### Tests for User Story 1

- [ ] T017 [P] Create unit test for statistics calculation accuracy in tests/unit/stats_tests.rs
- [ ] T018 [P] Create integration test for basic stats command in tests/integration/stats_integration.rs
- [ ] T019 Create property-based test for statistical invariants in tests/property/stats_properties.rs

---

## Phase 4: User Story 2 - Frequency Distribution Analysis (P2)

**Goal**: Display complete frequency distribution from count 1 to max count with zero-filling

**Independent Test**: Can be tested by creating a database with specific count patterns and verifying frequency distribution

### Implementation Tasks

- [ ] T020 [P] Implement frequency histogram with configurable bin limits in StreamingStatsProcessor
- [ ] T021 [P] Implement zero-filling for complete frequency distribution range
- [ ] T022 [P] Add --detailed flag to CLI arguments for frequency distribution
- [ ] T023 [P] Implement --max-bins parameter for configurable histogram limits
- [ ] T024 [P] Extend output formatters to include frequency distribution
- [ ] T025 [P] Optimize frequency distribution memory usage for large ranges

### Tests for User Story 2

- [ ] T026 [P] Create unit test for frequency distribution accuracy in tests/unit/stats_tests.rs
- [ ] T027 [P] Create integration test for detailed frequency distribution in tests/integration/stats_integration.rs
- [ ] T028 [P] Create test for zero-filling frequency gaps in tests/property/stats_properties.rs

---

## Phase 5: User Story 3 - Error Handling for Invalid Inputs (P3)

**Goal**: Provide clear error messages for invalid or incompatible database files

**Independent Test**: Can be tested by running stats on non-existent, corrupted, or incompatible files

### Implementation Tasks

- [ ] T029 [P] Implement file existence validation in stats command handler
- [ ] T030 [P] Implement RKDB format validation before processing
- [ ] T031 [P] Implement empty database detection and error handling
- [ ] T032 [P] Implement memory limit checking with helpful error messages
- [ ] T033 [P] Add error context and suggestions to all error messages
- [ ] T034 Implement proper exit codes for different error types

### Tests for User Story 3

- [ ] T035 [P] Create unit test for error handling scenarios in tests/unit/stats_tests.rs
- [ ] T036 [P] Create integration test for error messages in tests/integration/stats_integration.rs

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Complete implementation with additional output formats and optimizations

### Output Format Support

- [ ] T037 [P] Implement JSON output formatter with serde serialization
- [ ] T038 [P] Implement CSV output formatter for spreadsheet analysis
- [ ] T039 [P] Implement TSV output formatter for tab-separated values
- [ ] T040 Add --format argument validation to CLI

### Performance & UX Features

- [ ] T041 [P] Implement progress bar with indicatif for large databases
- [ ] T042 [P] Add --progress flag to CLI arguments
- [ ] T043 [P] Add --approximate flag for faster median calculation
- [ ] T044 [P] Implement parallel processing with rayon for CPU-bound operations
- [ ] T045 [P] Add processing time and memory usage tracking

### Documentation & Integration

- [ ] T046 [P] Update CLI help text and man pages
- [ ] T047 [P] Add stats command examples to README.md
- [ ] T048 Update src/database/mod.rs to export stats module
- [ ] T049 Update src/cli/commands/mod.rs to export stats command

### Final Tests

- [ ] T050 Create performance benchmark test in tests/bench/stats_bench.rs
- [ ] T051 [P] Create end-to-end test with real genomic database
- [ ] T052 Run clippy with zero warnings policy
- [ ] T053 Verify test coverage meets 90%+ requirement for critical paths

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Must complete before any other phases
- **Foundational (Phase 2)**: Must complete before User Story phases
- **User Story 1 (Phase 3)**: Core statistics - prerequisite for other stories
- **User Story 2 (Phase 4)**: Depends on User Story 1 completion
- **User Story 3 (Phase 5)**: Can be developed in parallel with User Story 2
- **Polish (Phase 6)**: Depends on all User Stories completion

### Parallel Opportunities

- All tasks marked [P] can run in parallel within their phase
- Unit tests [P] can run in parallel with implementation
- Different output formatters [P] can be implemented in parallel
- Error handling tasks [P] can be developed alongside main features

### Critical Success Factors

1. **Memory Efficiency**: Must handle databases larger than available RAM
2. **Performance**: Must meet <5 second target for 100M k-mers
3. **Accuracy**: All statistics must be 100% accurate for test datasets
4. **User Experience**: Clear error messages and helpful output formats
5. **Code Quality**: Zero clippy warnings, comprehensive test coverage

### Implementation Strategy

#### MVP (Minimum Viable Product)
- Implement User Story 1 only (basic statistics)
- Text output format only
- Basic error handling
- This provides immediate value to users

#### Incremental Delivery
1. Release MVP with basic statistics
2. Add frequency distribution (User Story 2)
3. Add comprehensive error handling (User Story 3)
4. Add multiple output formats and performance optimizations

### Risk Mitigation

- **TDigest Accuracy**: Use conservative compression (100) with exact fallback for small datasets
- **Memory Limits**: Enforce configurable limits with clear error messages
- **Performance Regression**: Include benchmarks in CI pipeline
- **File Compatibility**: Validate database format before processing

### Expected Outcomes

1. **Functional**: Complete stats command meeting all requirements
2. **Performance**: <5 seconds for 100M k-mers, <200MB memory usage
3. **Quality**: 90%+ test coverage, zero warnings
4. **Documentation**: Comprehensive examples and API docs