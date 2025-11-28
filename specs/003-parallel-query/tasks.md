# Tasks: 21-mer Performance Testing Implementation

**Input**: User request for 21-mer performance testing using OSA1 r7 assembly data
**Branch**: 003-parallel-query
**Prerequisites**: plan.md, spec.md, data-model.md, quickstart.md

**Tests**: Performance comparison validation tasks included for result accuracy verification

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [STATUS] [P?] [Story?] Description`

- **[STATUS]**: Current completion status ([COMPLETED], [IN-PROGRESS], [PENDING])
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- **Include exact file paths in descriptions**

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Data storage**: `/Users/forrest/Temp/demodata/` for all intermediate and test data
- **21-mer specific**: `/Users/forrest/Temp/demodata/test_runs/osa1_21mer_performance_test/`

---

## Phase 1: Setup and Environment Preparation

**Purpose**: Environment setup for 21-mer performance testing with data organization

- [x] T001 Create 21-mer specific test directory structure in /Users/forrest/Temp/demodata/test_runs/osa1_21mer_performance_test/
- [x] T002 Verify OSA1 r7 assembly file accessibility at /Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa (381MB)
- [x] T003 Create performance logging directory structure for comprehensive metric collection in /Users/forrest/Temp/demodata/test_runs/osa1_21mer_performance_test/logs/
- [x] T004 [P] Set up deterministic environment variables and configuration for reproducible testing
- [x] T005 Validate sufficient available disk space for 21-mer databases (expected 600-800MB each) - 757GB available
- [x] T006 [P] Create result validation framework in /Users/forrest/Temp/demodata/scripts/validate_21mer_results.py

---

## Phase 2: Foundational - 21-mer Database Generation (Foundation)

**Purpose**: Generate 21-mer databases using established methodology for fair comparison

**⚠️ CRITICAL**: No 21-mer performance testing can begin until databases are generated

- [x] T007 Generate jellyfish 21-mer database using canonical counting with single-threaded execution (84.79s, 2.5GB)
- [x] T008 Generate rustkmer 21-mer database with sorted optimization for query performance (64.59s, 3.0GB, 272M unique k-mers)
- [ ] T009 [P] Validate 21-mer database integrity and k-mer count consistency between tools
- [ ] T010 [P] Store 21-mer database metadata (creation time, file size, k-mer count) for performance analysis
- [ ] T011 [P] Compare 21-mer database characteristics with 13-mer results (size, unique k-mers, creation time)
- [x] T012 Create deterministic 10,000 21-mer query set with fixed seed (42) for reproducible testing

**Checkpoint**: 21-mer databases and query set ready - performance testing can now begin

---

## Phase 3: User Story 1 - 21-mer Multi-threading Performance Analysis (Priority: P1) 🎯 MVP

**Goal**: Execute comprehensive 21-mer performance comparison to determine multi-threading benefits

**Independent Test**: Run identical 10,000 21-mer queries on both single-threaded and multi-threaded rustkmer execution modes and compare with jellyfish baseline

### Performance Validation Tests

- [ ] T013 [P] [US1] Create 21-mer performance test execution framework in /Users/forrest/Temp/demodata/scripts/run_21mer_performance_comparison.sh
- [ ] T014 [P] [US1] Create 21-mer result validation script in /Users/forrest/Temp/demodata/scripts/validate_21mer_accuracy.py
- [ ] T015 [P] [US1] Create 21-mer memory usage analysis script for multi-threading impact assessment

### 21-mer Performance Testing Implementation

- [x] T016 [US1] Execute jellyfish single-threaded 21-mer query benchmark with comprehensive system monitoring
- [x] T017 [US1] Execute rustkmer single-threaded 21-mer query benchmark with comprehensive system monitoring
- [x] T018 [US1] Execute rustkmer multi-threaded 21-mer queryx benchmark with built-in profiling and system monitoring
- [ ] T019 [US1] [P] Collect and process 21-mer performance logs from both single and multi-threaded test executions
- [ ] T020 [US1] [P] Generate comprehensive 21-mer performance comparison report with multi-threading analysis
- [ ] T021 [US1] Create 21-mer vs 13-mer performance scaling analysis document comparing memory usage and throughput
- [ ] T022 [US1] Document memory usage patterns and resource efficiency for 21-mer queries with larger k-mer sizes
- [x] T023 [US1] Provide definitive answer on multi-threading benefits for 21-mer queries based on empirical evidence

**Checkpoint**: 21-mer multi-threading performance analysis complete with clear recommendations

---

## Phase 4: User Story 2 - Scalability Analysis for Different K-mer Sizes (Priority: P2)

**Goal**: Analyze performance characteristics across different k-mer sizes to identify optimization patterns

**Independent Test**: Compare 13-mer vs 21-mer performance across different batch sizes and threading configurations

### K-mer Size Scalability Testing Implementation

- [ ] T024 [P] [US2] Create k-mer size comparison testing framework for 13-mer vs 21-mer analysis
- [ ] T025 [P] [US2] Execute scalability benchmarks across different batch sizes (10, 100, 1000, 10000) for both k-mer sizes
- [ ] T026 [P] [US2] Generate k-mer size scaling analysis report with crossover point identification
- [ ] T027 [US2] [P] Analyze memory usage patterns and cache efficiency differences between 13-mer and 21-mer
- [ ] T028 [US2] Generate k-mer size optimization recommendations based on performance characteristics

**Checkpoint**: K-mer size scalability characteristics documented with clear usage recommendations

---

## Phase 5: User Story 3 - Thread Safety and Resource Management (Priority: P3)

**Goal**: Validate 21-mer performance with thread safety and proper resource management

**Independent Test**: Multi-run statistical analysis for confidence intervals and variance measurement

### 21-mer Advanced Performance Analysis

- [ ] T029 [P] [US3] Implement multi-run testing framework for 21-mer statistical significance
- [ ] T030 [P] [US3] Execute multiple 21-mer performance runs with different thread configurations
- [ ] T031 [US3] [P] Generate statistical 21-mer performance analysis with confidence intervals
- [ ] T032 [US3] Create comprehensive 21-mer database query optimization recommendations
- [ ] T033 [US3] Document memory usage patterns and thread safety validation for 21-mer
- [ ] T034 [US3] Validate resource efficiency and thread pool management for larger k-mer sizes

**Checkpoint**: Advanced 21-mer performance insights ready with statistical validation

---

## Phase 6: Comprehensive Analysis and Documentation

**Purpose**: Complete 21-mer analysis with final recommendations and comparison summary

- [ ] T035 [P] Create comprehensive 21-mer performance comparison documentation in /Users/forrest/GitHub/rustkmer/specs/003-parallel-query/21MER_PERFORMANCE_ANALYSIS.md
- [ ] T036 [P] Generate definitive answer document: "Does 21-mer benefit from multi-threading?" with clear evidence
- [ ] T037 [P] Create 13-mer vs 21-mer performance comparison visualization and summary tables
- [ ] T038 [P] Archive all 21-mer performance data and results with proper metadata
- [ ] T039 [P] Update project documentation with 21-mer performance findings and k-mer size recommendations
- [ ] T040 [P] Create final performance testing methodology documentation for future k-mer size comparisons

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

### Within Each User Story

- Tests (validation tasks) MUST be created before execution
- Data generation before execution
- Execution before analysis
- Analysis before reporting

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- Database generation tasks marked [P] can run in parallel (within Phase 2)
- Multiple performance analysis tasks can run in parallel
- Documentation and archiving tasks can run in parallel

---

## Parallel Example: 21-mer Performance Testing Execution

```bash
# Launch all data preparation in parallel:
Task: "Create 21-mer deterministic query set with fixed seed (42) for reproducible testing"
Task: "Store 21-mer database metadata (creation time, file size, k-mer count) for performance analysis"

# Launch performance benchmarks in sequence (each depends on previous completion):
Task: "Execute jellyfish single-threaded 21-mer query benchmark with comprehensive system monitoring"
Task: "Execute rustkmer single-threaded 21-mer query benchmark with comprehensive system monitoring"
Task: "Execute rustkmer multi-threaded 21-mer queryx benchmark with built-in profiling and system monitoring"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (environment and directories)
2. Complete Phase 2: Database Generation (create 21-mer databases and query sets)
3. Complete Phase 3: Performance Testing (execute comparisons and analysis)
4. **STOP AND VALIDATE**: Verify 21-mer performance results and accuracy validation
5. Document findings and recommendations

### Incremental Delivery

1. Complete Setup + Database Generation → Foundation ready
2. Add Performance Testing → Core comparison complete (MVP!)
3. Add Scalability Analysis → Extended insights
4. Add Advanced Analysis → Statistical validation
5. Each phase adds value without breaking previous phases

### Quality Assurance Strategy

1. **Reproducibility**: Fixed random seeds, consistent environments, documented parameters
2. **Accuracy Validation**: 100% result consistency verification across all tools
3. **Statistical Significance**: Multiple runs with confidence intervals for advanced analysis
4. **Comprehensive Monitoring**: System resource, memory usage, I/O patterns tracking
5. **Fair Comparison**: Identical datasets, consistent parameters, transparent methodology

---

## Expected Outcomes

**21-mer Performance Deliverables**:
- **Definitive Answer**: Clear evidence on whether 21-mer queries benefit from multi-threading
- **Performance Comparison**: 13-mer vs 21-mer multi-threading performance analysis
- **Memory Usage Analysis**: Resource efficiency comparison between different k-mer sizes
- **Scaling Characteristics**: Performance patterns and optimization recommendations

**Technical Specifications**:
- **Dataset**: OSA1 r7 assembly (381MB FASTA)
- **K-mer Size**: 21-mers for comparison with existing 13-mer results
- **Query Volume**: 10,000 deterministic queries for statistical significance
- **Tools**: jellyfish (single-threaded) vs rustkmer (single-threaded query vs multi-threaded queryx)
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