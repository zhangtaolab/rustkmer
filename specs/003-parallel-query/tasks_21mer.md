# Tasks: 21-mer Performance Comparison Testing - Multi-threading Analysis

**Input**: User request "如果是 21mer 呢？ 多线程和单线程比如果性能没有明显提升也请明确的告诉我"
**Prerequisites**: plan.md, spec.md, research.md, data-model.md from `/specs/003-parallel-query/`

**Goal**: Determine if 21-mer k-mer queries benefit from multi-threading compared to single-threaded execution using the same methodology as 13-mer testing

**Focus**: Multi-threading performance analysis for larger k-mer size (21-mers) with higher memory and computational requirements

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- **Focus**: 21-mer specific analysis and comparison with 13-mer results

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Data storage**: `/Users/forrest/Temp/demodata/` for all intermediate and test data
- **21-mer specific**: `/Users/forrest/Temp/demodata/test_runs/osa1_21mer_performance_test/`

---

## Phase 1: 21-mer Setup and Preparation

**Purpose**: Environment setup for 21-mer performance testing with comparison baseline

- [ ] T001 Create 21-mer specific test directory structure in /Users/forrest/Temp/demodata/test_runs/osa1_21mer_performance_test/
- [ ] T002 Verify 21-mer compatibility with existing rustkmer implementation and database format
- [ ] T003 [P] Create 21-mer deterministic query generator with 10,000 queries (same seed=42 for reproducibility)
- [ ] T004 [P] Validate 21-mer query sequences for DNA compliance and proper length validation
- [ ] T005 [P] Set up 21-mer specific logging and performance monitoring infrastructure
- [ ] T006 [P] Create performance comparison framework between 13-mer and 21-mer results

---

## Phase 2: 21-mer Database Generation (Foundation)

**Purpose**: Generate 21-mer databases using established methodology for fair comparison

**⚠️ CRITICAL**: No 21-mer performance testing can begin until databases are generated

- [ ] T007 Generate jellyfish 21-mer database using canonical counting with single-threaded execution
- [ ] T008 Generate rustkmer 21-mer database with sorted optimization for query performance
- [ ] T009 [P] Validate 21-mer database integrity and k-mer count consistency between tools
- [ ] T010 [P] Store 21-mer database metadata (creation time, file size, k-mer count) for performance analysis
- [ ] T011 [P] Compare 21-mer database characteristics with 13-mer results (size, unique k-mers, creation time)
- [ ] T012 [P] Create deterministic 10,000 21-mer query set with fixed seed (42) for reproducible testing

**Checkpoint**: 21-mer databases and query set ready - performance testing can now begin

---

## Phase 3: User Story 1 - 21-mer Multi-threading Performance Analysis (Priority: P1) 🎯 MVP

**Goal**: Execute comprehensive 21-mer performance comparison to determine multi-threading benefits

**Independent Test**: Run identical 10,000 21-mer queries on both single-threaded and multi-threaded rustkmer execution modes

### 21-mer Performance Validation Tests

- [ ] T013 [P] [US1] Create 21-mer performance test execution framework in /Users/forrest/Temp/demodata/scripts/run_21mer_performance_comparison.sh
- [ ] T014 [P] [US1] Create 21-mer vs 13-mer comparison script in /Users/forrest/Temp/demodata/scripts/compare_kmer_sizes.py
- [ ] T015 [P] [US1] Create 21-mer memory usage analysis script for multi-threading impact assessment

### 21-mer Performance Testing Implementation

- [ ] T016 [US1] Execute rustkmer single-threaded 21-mer query benchmark with comprehensive system monitoring
- [ ] T017 [US1] Execute rustkmer multi-threaded 21-mer queryx benchmark with built-in profiling and system monitoring
- [ ] T018 [US1] [P] Collect and process 21-mer performance logs from both single and multi-threaded test executions
- [ ] T019 [US1] [P] Generate comprehensive 21-mer performance comparison report with multi-threading analysis
- [ ] T020 [US1] Create 21-mer vs 13-mer performance scaling analysis document
- [ ] T021 [US1] Document memory usage patterns and resource efficiency for 21-mer queries
- [ ] T022 [US1] Provide definitive answer on multi-threading benefits for 21-mer queries

**Checkpoint**: 21-mer multi-threading performance analysis complete with clear recommendations

---

## Phase 4: User Story 2 - Scalability Analysis for Different K-mer Sizes (Priority: P2)

**Goal**: Analyze performance characteristics across different k-mer sizes to identify optimization patterns

**Independent Test**: Compare 13-mer vs 21-mer performance across different batch sizes and threading configurations

### K-mer Size Scalability Testing Implementation

- [ ] T023 [P] [US2] Create k-mer size comparison testing framework for 13-mer vs 21-mer analysis
- [ ] T024 [P] [US2] Execute scalability benchmarks across different batch sizes (10, 100, 1000, 10000) for both k-mer sizes
- [ ] T025 [P] [US2] Generate k-mer size scaling analysis report with crossover point identification
- [ ] T026 [US2] [P] Analyze memory usage patterns and cache efficiency differences between 13-mer and 21-mer
- [ ] T027 [US2] Generate k-mer size optimization recommendations based on performance characteristics

**Checkpoint**: K-mer size scalability characteristics documented with clear usage recommendations

---

## Phase 5: User Story 3 - Thread Safety and Resource Management (Priority: P3)

**Goal**: Validate 21-mer performance with thread safety and proper resource management

**Independent Test**: Multi-run statistical analysis for confidence intervals and variance measurement

### 21-mer Advanced Performance Analysis

- [ ] T028 [P] [US3] Implement multi-run testing framework for 21-mer statistical significance
- [ ] T029 [P] [US3] Execute multiple 21-mer performance runs with different thread configurations
- [ ] T030 [US3] [P] Generate statistical 21-mer performance analysis with confidence intervals
- [ ] T031 [US3] Create comprehensive 21-mer database query optimization recommendations
- [ ] T032 [US3] Document memory usage patterns and thread safety validation for 21-mer
- [ ] T033 [US3] Validate resource efficiency and thread pool management for larger k-mer sizes

**Checkpoint**: Advanced 21-mer performance insights ready with statistical validation

---

## Phase 6: Comprehensive Analysis and Documentation

**Purpose**: Complete 21-mer analysis with final recommendations and comparison summary

- [ ] T034 [P] Create comprehensive 21-mer performance comparison documentation in /Users/forrest/GitHub/rustkmer/specs/003-parallel-query/21MER_PERFORMANCE_ANALYSIS.md
- [ ] T035 [P] Generate definitive answer document: "Does 21-mer benefit from multi-threading?" with clear evidence
- [ ] T036 [P] Create 13-mer vs 21-mer performance comparison visualization and summary tables
- [ ] T037 [P] Archive all 21-mer performance data and results with proper metadata
- [ ] T038 [P] Update project documentation with 21-mer performance findings and k-mer size recommendations

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Database Generation (Phase 2)**: Depends on Setup completion - BLOCKS all performance testing
- **21-mer Performance Testing (Phase 3)**: Depends on Database Generation completion - Primary deliverable
- **Scalability Analysis (Phase 4)**: Depends on Performance Testing completion - Extended analysis
- **Advanced Analysis (Phase 5)**: Depends on Performance Testing completion - Statistical insights
- **Documentation (Final Phase)**: Depends on all testing phases complete - Final reporting

### User Story Dependencies

- **User Story 1 (P1)**: Core 21-mer multi-threading performance question - provides baseline for all other analysis
- **User Story 2 (P2)**: Extends US1 with k-mer size scaling insights - depends on US1 completion
- **User Story 3 (P3)**: Builds on US1/US2 with advanced statistical validation - depends on US1 completion

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- Database generation tasks marked [P] can run in parallel (within Phase 2)
- Multiple performance analysis tasks can run in parallel
- Documentation and archiving tasks can run in parallel

---

## Expected Outcomes

**21-mer Performance Deliverables**:
- **Definitive Answer**: Clear evidence on whether 21-mer queries benefit from multi-threading
- **Performance Comparison**: 13-mer vs 21-mer multi-threading performance analysis
- **Memory Usage Analysis**: Resource efficiency comparison between different k-mer sizes
- **Scaling Characteristics**: Performance patterns and optimization recommendations

**Technical Specifications**:
- **Dataset**: OSA1 r7 assembly (~120MB FASTA)
- **K-mer Size**: 21-mers for comparison with existing 13-mer results
- **Query Volume**: 10,000 deterministic queries for statistical significance
- **Tools**: rustkmer (single-threaded query vs multi-threaded queryx)
- **Storage**: /Users/forrest/Temp/demodata/test_runs/osa1_21mer_performance_test/ for all intermediate and final results

**Success Criteria**:
- **Clear Answer**: Definitive statement on 21-mer multi-threading benefits with supporting evidence
- **Performance Metrics**: Comprehensive comparison between 13-mer and 21-mer performance
- **Resource Analysis**: Memory usage and efficiency patterns for larger k-mer sizes
- **Recommendations**: Actionable guidance on optimal k-mer size and threading configuration
- **Documentation**: Complete analysis ready for bioinformatics community review

---

## Research Questions to Answer

1. **Primary Question**: Does 21-mer query processing benefit significantly from multi-threading compared to single-threaded execution?

2. **Secondary Questions**:
   - How does 21-mer performance compare to 13-mer performance in both single and multi-threaded modes?
   - What are the memory usage implications of larger k-mer sizes with multi-threading?
   - At what point (if any) does multi-threading become beneficial for 21-mer queries?
   - How do cache efficiency and memory access patterns differ between 13-mer and 21-mer processing?

3. **Expected Findings**:
   - **If multi-threading helps**: Quantify the performance benefit and identify optimal conditions
   - **If multi-threading doesn't help**: Provide clear evidence and explain why (e.g., memory-bound, I/O-bound)
   - **Comparison insights**: How k-mer size affects the multi-threading crossover point

**Final Deliverable**: Clear, evidence-based answer to the user's question: "如果是 21mer 呢？ 多线程和单线程比如果性能没有明显提升也请明确的告诉我"