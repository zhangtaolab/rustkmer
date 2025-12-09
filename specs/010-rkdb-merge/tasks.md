---

description: "Task list for comparing split-count-merge vs direct-count approaches"
---

# Tasks: Compare Counting Approaches

**Input**: Test data in `/Users/forrest/Temp/demodata/fastq/split/` containing 10 FASTQ files
**Approaches to Compare**:
1. **Split-Count-Merge**: Count each file individually, then merge all databases
2. **Direct-Count**: Count all files in a single operation

**Goal**: Verify both approaches produce identical results and compare performance metrics

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which approach this task belongs to (SPLIT for split-count-merge, DIRECT for direct-count)

## Phase 1: Environment Setup

**Purpose**: Prepare test environment and verify tools

- [X] T001 Verify rustkmer binary is built and available
- [ ] T002 [P] Verify test data integrity in /Users/forrest/Temp/demodata/fastq/split/
- [ ] T003 Create test directory for outputs
- [ ] T004 Check available disk space for test outputs

---

## Phase 2: Baseline Measurements

**Purpose**: Establish baseline system metrics

- [ ] T005 Measure available system memory before tests
- [ ] T006 Measure available disk space before tests
- [ ] T007 Record system load baseline

---

## Phase 3: Split-Count-Merge Approach (SPLIT)

**Goal**: Count each file individually and merge results

### Setup for Split Approach

- [ ] T008 [P] [SPLIT] Create output directories for individual databases
- [ ] T009 [SPLIT] Set up logging for split approach timing

### Individual File Counting

- [X] T010 [P] [SPLIT] Count mrna_miR5794_rep1_pair1.part_001.fq.gz to individual.rkdb
- [X] T011 [P] [SPLIT] Count mrna_miR5794_rep1_pair1.part_002.fq.gz to individual.rkdb
- [X] T012 [P] [SPLIT] Count mrna_miR5794_rep1_pair1.part_003.fq.gz to individual.rkdb
- [X] T013 [P] [SPLIT] Count mrna_miR5794_rep1_pair1.part_004.fq.gz to individual.rkdb
- [X] T014 [P] [SPLIT] Count mrna_miR5794_rep1_pair1.part_005.fq.gz to individual.rkdb
- [X] T015 [P] [SPLIT] Count mrna_miR5794_rep1_pair1.part_006.fq.gz to individual.rkdb
- [X] T016 [P] [SPLIT] Count mrna_miR5794_rep1_pair1.part_007.fq.gz to individual.rkdb
- [X] T017 [P] [SPLIT] Count mrna_miR5794_rep1_pair1.part_008.fq.gz to individual.rkdb
- [X] T018 [P] [SPLIT] Count mrna_miR5794_rep1_pair1.part_009.fq.gz to individual.rkdb
- [X] T019 [P] [SPLIT] Count mrna_miR5794_rep1_pair1.part_010.fq.gz to individual.rkdb

### Merge Individual Databases

- [X] T020 [SPLIT] Verify all individual databases created successfully
- [X] T021 [SPLIT] Check compatibility of all individual databases
- [X] T022 [SPLIT] Merge all 10 individual databases into split_merged.rkdb
- [X] T023 [SPLIT] Record merge operation statistics

### Results Collection

- [X] T024 [SPLIT] Get statistics from split_merged.rkdb
- [X] T025 [SPLIT] Calculate total time for split-count-merge approach
- [X] T026 [SPLIT] Measure peak memory usage during split approach
- [X] T027 [SPLIT] Record disk usage for all intermediate files

---

## Phase 4: Direct-Count Approach (DIRECT)

**Goal**: Count all files in a single operation

### Setup for Direct Approach

- [X] T028 [DIRECT] Create output directory for direct approach
- [X] T029 [DIRECT] Set up logging for direct approach timing

### Single Operation Counting

- [X] T030 [DIRECT] Count all 10 FASTQ files directly to direct_counted.rkdb

### Results Collection

- [X] T031 [DIRECT] Get statistics from direct_counted.rkdb
- [X] T032 [DIRECT] Calculate total time for direct-count approach
- [X] T033 [DIRECT] Measure peak memory usage during direct approach
- [X] T034 [DIRECT] Record disk usage for output file

---

## Phase 5: Comparison and Analysis

**Purpose**: Compare results and performance between approaches

### Data Verification

- [X] T035 Compare total k-mer counts between approaches
- [X] T036 Compare unique k-mer counts between approaches
- [X] T037 Verify database compatibility between merged and direct databases
- [X] T038 Extract sample k-mers from both databases for comparison
- [X] T039 Perform diff check on k-mer sets between approaches

### Performance Analysis

- [X] T040 Calculate time difference between approaches
- [X] T041 Compare peak memory usage between approaches
- [X] T042 Compare total disk I/O between approaches
- [X] T043 Analyze scaling efficiency (time per file vs total time)

### Edge Case Testing

- [ ] T044 Test with k-mer size 21 instead of default
- [ ] T045 Test with canonical mode enabled
- [ ] T046 Test with different thread counts (1, 2, 4, 8)
- [ ] T047 Test with large k-mer (k=33) if supported

---

## Phase 6: Report Generation

**Purpose**: Document findings and recommendations

- [ ] T048 Generate performance comparison report
- [ ] T049 Create summary table with all metrics
- [ ] T050 Document recommendations for optimal approach
- [ ] T051 Identify scenarios where each approach excels

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Must run before any other phases
- **Baseline (Phase 2)**: Must run before testing phases
- **Split Approach (Phase 3)**: Independent - can run before or after Direct
- **Direct Approach (Phase 4)**: Independent - can run before or after Split
- **Comparison (Phase 5)**: Requires both Split and Direct phases to complete
- **Report (Phase 6)**: Requires all previous phases to complete

### Parallel Opportunities

- All tasks marked [P] in Split Approach (T010-T019) can run in parallel
- Baseline measurements (T005-T007) can run in parallel
- Results collection tasks within each phase can run in parallel

### Critical Success Factors

1. **Accuracy**: Both approaches must produce identical results
2. **Performance**: Measure comprehensive metrics for fair comparison
3. **Reproducibility**: Tests must be repeatable with consistent results
4. **Scalability**: Analysis should inform optimal approach for different data sizes

---

## Implementation Strategy

### Test Parameters

- **K-mer size**: Default (31) and optional tests with 21, 33
- **Canonical mode**: Default (false) and optional test with true
- **Threads**: Test with 1, 2, 4, 8 threads
- **Memory monitoring**: Continuous during operations
- **Timing**: Wall-clock time and CPU time

### Expected Outcomes

1. **Result Verification**: Both approaches should produce 100% identical k-mer databases
2. **Performance Insights**:
   - Direct counting expected to be faster for small numbers of files
   - Split-merge may be more memory-efficient for very large files
3. **Resource Usage**:
   - Split approach uses more disk space (intermediate databases)
   - Direct approach may use more memory during single operation
4. **Recommendations**: Clear guidance on when to use each approach

### Test Data Characteristics

- **Files**: 10 compressed FASTQ files (~225MB each)
- **Total size**: ~2.2GB of compressed data
- **Estimated uncompressed size**: ~10-15GB
- **Expected k-mer count**: Millions to tens of millions
- **Test duration**: Estimate 30-60 minutes for complete test suite