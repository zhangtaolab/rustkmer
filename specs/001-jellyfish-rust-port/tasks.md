---

description: "Task list for rustkmer count implementation"
---

# Tasks: RustKmer Count Implementation

**Input**: Design documents from `/specs/001-jellyfish-rust-port/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks for comprehensive validation based on jellyfish golden standard comparison.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, etc.)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Paths below assume the project structure defined in plan.md**

<!--
  ============================================================================
  IMPORTANT: The tasks below are generated based on:
  - User stories from spec.md (US1: Basic Counting, US2: Performance, US3: Canonical, US4: Output Formats)
  - Data model from data-model.md (Kmer, KmerCounter, SequenceProcessor)
  - CLI contract from contracts/cli-api.md
  - Technical stack from research.md and plan.md
  - Validation requirements: jellyfish comparison, k=13/21 progression
  - File storage: /Users/forrest/Temp/demodata/ for test outputs
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize Rust project with required dependencies
- [ ] T003 [P] Configure linting and formatting tools (rustfmt, clippy)
- [ ] T004 Create test data symlinks to /Users/forrest/Temp/demodata/
- [ ] T005 Set up Cargo.toml with all dependencies (clap, rayon, bio, memmap2, thiserror, anyhow, criterion)
- [ ] T006 Create basic module structure files (mod.rs files)
- [ ] T007 Set up benchmarks directory structure
- [ ] T008 Create validation test script for jellyfish comparison

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T009 [P] Implement core k-mer encoding functions in src/kmer/encoding.rs
- [ ] T010 [P] Implement DNA base encoding (2 bits per base) in src/kmer/encoding.rs
- [ ] T011 [P] Create k-mer decoding functions in src/kmer/encoding.rs
- [ ] T012 [P] Implement sequence validation and filtering in src/kmer/operations.rs
- [ ] T013 [P] Create basic error type definitions in src/error.rs
- [ ] T014 [P] Set up concurrent hash table structure in src/hash/table.rs
- [ ] T015 [P] Implement basic hash table operations (insert, get) in src/hash/table.rs
- [ ] T016 [P] Create memory-mapped file operations in src/io/mmap.rs
- [ ] T017 [P] Set up FASTA file parsing using bio crate in src/io/fasta.rs
- [ ] T018 [P] Set up FASTQ file parsing using bio crate in src/io/fastq.rs

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Basic K-mer Counting (Priority: P1) 🎯 MVP

**Goal**: Implement core k-mer counting functionality for FASTA/FASTQ files

**Independent Test**: Can be fully tested by running rustkmer count -k 13 on test data and comparing results with jellyfish -k 13

### Implementation for User Story 1

- [ ] T019 [P] [US1] Implement CLI argument structure in src/cli/commands/args.rs
- [ ] T020 [P] [US1] Create main count command logic in src/cli/commands/count.rs
- [ ] T021 [P] [US1] Implement k-mer extraction from sequences in src/kmer/operations.rs
- [ ] T022 [P] [US1] Build sliding window k-mer generator in src/kmer/operations.rs
- [ ] T023 [P] [US1] Implement sequence processing pipeline in src/io/fasta.rs
- [ ] T024 [P] [US1] Create KmerCounter with thread-safe operations in src/hash/table.rs
- [ ] T025 [P] [US1] Implement binary output format in src/output/binary.rs
- [ ] T026 [P] [US1] Create main CLI application entry point in src/main.rs
- [ ] T027 [P] [US1] Set up library interface in src/lib.rs
- [ ] T028 [US1] Add input file validation and error handling

### Tests for User Story 1

- [ ] T029 [P] [US1] Unit test k-mer encoding in tests/unit/kmer_tests.rs
- [ ] T030 [P] [US1] Unit test hash table operations in tests/unit/hash_tests.rs
- [ ] T031 [P] [US1] Unit test FASTA parsing in tests/unit/io_tests.rs
- [ ] T032 [P] [US1] Integration test basic counting workflow in tests/integration/count_tests.rs
- [ ] T033 [P] [US1] Validation test against jellyfish k=13 output in tests/integration/validation.rs
- [ ] T034 [P] [US1] Test edge cases (short sequences, invalid characters) in tests/integration/count_tests.rs

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Performance Optimization (Priority: P1)

**Goal**: Add multi-threading and performance optimization for large datasets

**Independent Test**: Can be fully tested by comparing performance with different thread counts and measuring scaling efficiency

### Implementation for User Story 2

- [ ] T035 [P] [US2] Implement parallel k-mer processing with Rayon in src/parallel/processor.rs
- [ ] T036 [P] [US2] Create thread pool management in src/parallel/pool.rs
- [ ] T037 [P] [US2] Add memory-efficient k-mer streaming for large files in src/parallel/processor.rs
- [ ] T038 [P] [US2] Implement progress reporting and statistics in src/parallel/processor.rs
- [ ] T039 [P] [US2] Add thread count configuration to CLI arguments in src/cli/commands/args.rs
- [ ] T040 [P] [US2] Implement configurable hash table sizing in src/hash/table.rs
- [ ] T041 [P] [US2] Add memory usage monitoring and reporting

### Tests for User Story 2

- [ ] T042 [P] [US2] Performance benchmark against jellyfish in benches/performance.rs
- [ ] T043 [P] [US2] Test multi-threading correctness and scaling in tests/integration/count_tests.rs
- [ ] T044 [P] [US2] Memory usage validation tests in tests/integration/count_tests.rs
- [ ] T045 [P] [US2] Large file processing test with k=13 data in tests/integration/validation.rs

---

## Phase 5: User Story 3 - Canonical K-mer Counting (Priority: P2)

**Goal**: Implement canonical k-mer counting (strand-agnostic)

**Independent Test**: Can be fully tested by running rustkmer count -C and comparing with jellyfish -C

### Implementation for User Story 3

- [ ] T046 [P] [US3] Implement reverse complement calculation in src/kmer/canonical.rs
- [ ] T047 [P] [US3] Create canonical k-mer selection logic in src/kmer/canonical.rs
- [ ] T048 [P] [US3] Add canonical mode flag to CLI arguments in src/cli/commands/args.rs
- [ ] T049 [P] [US3] Integrate canonical processing into counting pipeline in src/cli/commands/count.rs
- [ ] T050 [P] [US3] Update output format to indicate canonical mode in src/output/binary.rs

### Tests for User Story 3

- [ ] T051 [P] [US3] Unit test reverse complement calculation in tests/unit/kmer_tests.rs
- [ ] T052 [P] [US3] Unit test canonical k-mer selection in tests/unit/kmer_tests.rs
- [ ] T053 [P] [US3] Integration test canonical counting workflow in tests/integration/count_tests.rs
- [ ] T054 [P] [US3] Validation test against jellyfish -C with k=13 in tests/integration/validation.rs
- [ ] T055 [P] [US3] Test canonical correctness on reverse complement pairs in tests/integration/count_tests.rs

---

## Phase 6: User Story 4 - Output Format Compatibility (Priority: P2)

**Goal**: Support multiple output formats (binary and text)

**Independent Test**: Can be fully tested by generating both formats and verifying compatibility

### Implementation for User Story 4

- [ ] T056 [P] [US4] Implement text output format in src/output/text.rs
- [ ] T057 [P] [US4] Add text output flag to CLI arguments in src/cli/commands/args.rs
- [ ] T058 [P] [US4] Create output format selection logic in src/cli/commands/count.rs
- Note: Comprehensive filtering implementation (-L/-U parameters) moved to dedicated Phase 7 (FR-008 Enhancement)
- [ ] T074 [P] [US4] Add output file validation and extension handling
- [ ] T075 [P] [US4] Create output format metadata headers in both formats

### Tests for User Story 4

- [ ] T076 [P] [US4] Unit test text format generation in tests/unit/io_tests.rs
- [ ] T077 [P] [US4] Unit test binary format generation in tests/unit/io_tests.rs
- [ ] T078 [P] [US4] Integration test both output formats in tests/integration/count_tests.rs
- [ ] T079 [P] [US4] Test output format compatibility with standard tools in tests/integration/count_tests.rs
- [ ] T080 [P] [US4] Validate filtering thresholds work correctly in tests/integration/count_tests.rs

---

## Phase 7: K-mer Count Filtering Enhancement (FR-008)

**Purpose**: Implement jellyfish-compatible -L/-U filtering parameters as specified in the enhancement plan

**Independent Test**: rustkmer count -L 10 -U 1000 produces identical results to jellyfish count -L 10 -U 1000

### Filtering Data Structure Implementation

- [ ] T059a [P] [FR-008] Create CountFilter struct in src/hash/filtering.rs
- [ ] T059b [P] [FR-008] Create CountFilterConfig in src/hash/filtering.rs
- [ ] T059c [P] [FR-008] Create FilteringResult in src/hash/filtering.rs
- [ ] T059d [FR-008] Implement filter validation logic in src/hash/filtering.rs
- [ ] T059e [FR-008] Add filtering module to src/hash/mod.rs

### Hash Table Filtering Integration

- [ ] T059f [FR-008] Add get_filtered_kmers method to KmerCounter in src/hash/table.rs
- [ ] T059g [FR-008] Add get_filtering_stats method to KmerCounter in src/hash/table.rs

### CLI Parameter Enhancement

- [ ] T059h [FR-008] Add min_count and max_count fields to CountCommand in src/cli/args.rs
- [ ] T059i [FR-008] Add filtering parameter validation to CLI args in src/cli/args.rs
- [ ] T059j [FR-008] Add create_filter method to CountCommand in src/cli/args.rs

### Command Logic Integration

- [ ] T059k [FR-008] Add filtering parameter handling to count command in src/cli/commands/count.rs
- [ ] T059l [FR-008] Integrate filtering statistics into progress reporting in src/cli/commands/count.rs

### Output Format Filtering Support

- [ ] T059m [FR-008] Add filtering support to text output module in src/output/text.rs
- [ ] T059n [FR-008] Add filtering support to binary output module in src/output/binary.rs
- [ ] T059o [FR-008] Add filtering statistics to output headers in both formats

### Filtering Tests and Validation

- [ ] T059p [P] [FR-008] Unit tests for filtering data structures in tests/unit/hash/test_filtering.rs
- [ ] T059q [P] [FR-008] Unit tests for CLI parameter parsing in tests/unit/cli/test_filtering_args.rs
- [ ] T059r [P] [FR-008] Integration tests for filtering workflow in tests/integration/test_filtering.rs
- [ ] T059s [P] [FR-008] Performance tests for filtering overhead in tests/benchmarks/filtering_bench.rs
- [ ] T059t [P] [FR-008] Jellyfish compatibility tests for filtering in tests/integration/test_jellyfish_filtering.rs

**Checkpoint**: FR-008 filtering enhancement fully implemented and validated

---

## Phase 8: Disk Overflow and Advanced Features

**Purpose**: Handle memory constraints and implement overflow storage

- [ ] T081 [P] Implement disk-based overflow storage in src/hash/overflow.rs
- [ ] T082 [P] Add hash table overflow detection and handling in src/hash/table.rs
- [ ] T083 [P] Create temporary file management for overflow storage
- [ ] T084 [P] Implement overflow data retrieval and merging
- [ ] T085 [P] Add memory usage warnings and error handling

### Tests for Overflow Features

- [ ] T086 [P] Test hash table overflow handling in tests/integration/count_tests.rs
- [ ] T087 [P] Validate disk overflow storage correctness in tests/integration/count_tests.rs
- [ ] T088 [P] Test memory limit enforcement in tests/integration/count_tests.rs

---

## Phase 8: Full Validation and Testing

**Purpose**: Comprehensive testing against jellyfish golden standard

- [ ] T089 Create jellyfish comparison script for k=13 validation
- [ ] T090 [P] Run full validation test suite on osa1_r7.asm.fa with k=13
- [ ] T091 [P] Test both canonical (-C) and non-canonical modes against jellyfish
- [ ] T092 [P] Validate output format compatibility and statistical accuracy
- [ ] T093 [P] Performance comparison with jellyfish on test data
- [ ] T094 [P] Advanced test with k=21 on smaller test datasets
- [ ] T095 [P] Test multi-file input processing
- [ ] T096 [P] Edge case validation (empty files, invalid data, etc.)

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements that affect multiple user stories

- [ ] T097 [P] Add comprehensive error messages and user guidance
- [ ] T098 [P] Implement timing and performance statistics reporting
- [ ] T099 [P] Add progress bar for long-running operations
- [ ] T100 [P] Code cleanup and refactoring for maintainability
- [ ] T101 [P] Performance optimization and profiling
- [ ] T102 [P] Add memory usage optimization
- [ ] T103 [P] Documentation updates in source code
- [ ] T104 [P] Create user documentation and examples
- [ ] T105 [P] Final code review and quality checks
- [ ] T106 [P] Run full test suite with coverage analysis

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (US1 → US2 → US3 → US4)
- **Filtering Enhancement (Phase 7)**: Depends on User Stories 1,2,4 (counting, performance, output formats)
- **Overflow (Phase 8)**: Depends on User Stories 1-2 (hash table and performance)
- **Validation (Phase 9)**: Depends on all user stories and filtering enhancement being complete
- **Polish (Final Phase)**: Depends on all desired user stories and enhancements being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Builds on US1 but independent testable
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Extends US1-3 with output options

### Within Each User Story

- Tests can run in parallel with implementation for rapid feedback
- Core k-mer operations before file I/O
- Hash table before parallel processing
- CLI interface integration after core functionality

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, multiple user stories can start in parallel
- Unit tests for a story can run in parallel with integration tests of previous stories
- Different user stories can be worked on in parallel by different developers

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test k-mer encoding in tests/unit/kmer_tests.rs"
Task: "Unit test hash table operations in tests/unit/hash_tests.rs"
Task: "Unit test FASTA parsing in tests/unit/io_tests.rs"

# Launch all core implementation tasks for User Story 1 together:
Task: "Implement k-mer extraction from sequences in src/kmer/operations.rs"
Task: "Implement sequence processing pipeline in src/io/fasta.rs"
Task: "Create KmerCounter with thread-safe operations in src/hash/table.rs"
Task: "Implement binary output format in src/output/binary.rs"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently with k=13 against jellyfish
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Validate with k=13
3. Add User Story 2 → Test performance scaling → Deploy (P1 features complete)
4. Add User Story 3 → Test canonical mode → Deploy
5. Add User Story 4 → Test output formats → Deploy
6. Add Filtering Enhancement (Phase 7) → Test jellyfish compatibility → Deploy (FR-008 complete)
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 + validation tests
   - Developer B: User Story 2 + performance tests
   - Developer C: User Story 3 + canonical tests
   - Developer D: User Story 4 + output format tests
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Validation tasks specifically compare against jellyfish golden standard
- k=13 testing first, then k=21 for validation progression
- Use osa1_r7.asm.fa for full validation testing
- Test outputs stored in /Users/forrest/Temp/demodata/ to avoid git tracking
- Verify results match jellyfish exactly for both -C and non-C modes
- For filtering enhancement (FR-008): Ensure exact jellyfish -L/-U parameter compatibility
- For filtering enhancement: Performance overhead must remain <5% during output generation
- For filtering enhancement: Must maintain memory efficiency (filter during output, not counting)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence