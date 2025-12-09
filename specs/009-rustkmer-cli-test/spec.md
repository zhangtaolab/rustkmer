# Feature Specification: Comprehensive RustKmer CLI Testing with Real Data

**Feature Branch**: `009-rustkmer-cli-test`
**Created**: 2025-01-08
**Status**: Draft
**Input**: User description: "用真实数据 /Users/forrest/Temp/demodata 测试 rustkmer CLI 的全部功能，包括count , dump, query, fuzzy-query, stats, merge, help, 针对每个测试项目生成详细的测试报告，测试报告包括如何测试的，结果是怎样的。测试的中间数据可以保存在 /Users/forrest/Temp/demodata 下，并可以新建子目录。"

## Clarifications

### Session 2025-01-08

- Q: 测试数据的来源和类型 → A: 仅使用 /Users/forrest/Temp/demodata 中现有的数据

## User Scenarios & Testing *(mandatory)*

### User Story 1 - CLI Count Function Testing (Priority: P1)

As a bioinformatics developer, I want to thoroughly test the rustkmer count functionality with real genomic data so that I can verify its accuracy, performance, and reliability for k-mer counting tasks.

**Why this priority**: The count function is the core functionality of rustkmer and must be accurate and performant for downstream analysis.

**Independent Test**: Can be fully tested by running count commands on various real datasets and verifying outputs against expected results and performance benchmarks.

**Acceptance Scenarios**:

1. **Given** a real FASTA/FASTQ file in /Users/forrest/Temp/demodata, **When** running rustkmer count with different k-mer sizes (k=21, 31, 63), **Then** the tool should successfully create .rkdb database files and report processing statistics
2. **Given** multiple input files, **When** running rustkmer count with parallel processing enabled, **Then** the tool should process all files and aggregate results correctly
3. **Given** large genomic files (>1GB), **When** running rustkmer count, **Then** the tool should complete processing within reasonable time (<10 minutes for 1GB file) and report memory usage

---

### User Story 2 - CLI Query Function Testing (Priority: P1)

As a researcher, I want to test the query functionality to search for specific k-mers in the database so that I can retrieve accurate count information and verify the tool's correctness.

**Why this priority**: Query functionality is essential for downstream analysis and must return accurate results quickly.

**Independent Test**: Can be fully tested by querying known k-mers from test databases and verifying count accuracy and response times.

**Acceptance Scenarios**:

1. **Given** a created .rkdb database, **When** querying for known k-mers present in the source data, **Then** the tool should return exact counts matching the original data
2. **Given** a database, **When** querying for k-mers not present in the data, **Then** the tool should return zero or appropriate "not found" response
3. **Given** multiple k-mer queries in batch mode, **When** running rustkmer query with multiple sequences, **Then** the tool should return all results accurately and efficiently

---

### User Story 3 - CLI Dump Function Testing (Priority: P2)

As a developer, I want to test the dump functionality to extract k-mer information from databases so that I can verify data integrity and export results for further analysis.

**Why this priority**: Dump function is crucial for data export and integration with other bioinformatics tools.

**Independent Test**: Can be fully tested by dumping database contents and verifying the output format and completeness.

**Acceptance Scenarios**:

1. **Given** a populated .rkdb database, **When** running rustkmer dump, **Then** the tool should output all k-mers and their counts in the specified format
2. **Given** dump with format options (text, JSON), **When** specifying different output formats, **Then** the tool should produce correctly formatted outputs in each case
3. **Given** a large database, **When** dumping contents to file, **Then** the tool should handle memory efficiently and not crash

---

### User Story 4 - CLI Fuzzy Query Function Testing (Priority: P2)

As a researcher, I want to test the fuzzy query functionality to find k-mers within a specified Hamming distance so that I can identify similar sequences and handle sequencing errors.

**Why this priority**: Fuzzy query is important for real-world applications with sequencing errors and variations.

**Independent Test**: Can be fully tested by querying with known distance thresholds and verifying returned k-mers meet the distance criteria.

**Acceptance Scenarios**:

1. **Given** a database and a query k-mer, **When** running fuzzy-query with distance=1, **Then** the tool should return all k-mers with exactly 1 nucleotide difference
2. **Given** fuzzy queries with different distance thresholds (1, 2, 3), **When** comparing results, **Then** the tool should return progressively more results as distance increases
3. **Given** a k-mer not in the database, **When** running fuzzy-query, **Then** the tool should find similar k-mers if any exist within the distance threshold

---

### User Story 5 - CLI Stats Function Testing (Priority: P2)

As a system administrator, I want to test the stats functionality to get database statistics so that I can monitor database properties and verify database integrity.

**Why this priority**: Stats provide essential information about database contents and are used for quality control.

**Independent Test**: Can be fully tested by running stats on various databases and verifying reported metrics match expectations.

**Acceptance Scenarios**:

1. **Given** any .rkdb database file, **When** running rustkmer stats, **Then** the tool should report total k-mers, unique k-mers, k-mer size, and file size information
2. **Given** databases created with different k-mer sizes, **When** running stats, **Then** the tool should correctly report the k-mer size for each database
3. **Given** empty or corrupted databases, **When** running stats, **Then** the tool should handle errors gracefully and provide meaningful error messages

---

### User Story 6 - CLI Merge Function Testing (Priority: P3)

As a bioinformatics analyst, I want to test the merge functionality to combine multiple databases so that I can aggregate k-mer counts from different samples or experiments.

**Why this priority**: Merge functionality is essential for large-scale analyses where data is processed in batches.

**Independent Test**: Can be fully tested by merging known databases and verifying the combined counts are correct.

**Acceptance Scenarios**:

1. **Given** two or more .rkdb databases with non-overlapping k-mers, **When** running rustkmer merge, **Then** the merged database should contain all k-mers from input databases with correct counts
2. **Given** databases with overlapping k-mers, **When** merging, **Then** overlapping k-mers should have their counts summed correctly
3. **Given** databases created with different parameters, **When** attempting to merge incompatible databases, **Then** the tool should provide clear error messages about incompatibilities

---

### User Story 7 - CLI Help and Documentation Testing (Priority: P3)

As a new user, I want to access comprehensive help documentation so that I can understand how to use all rustkmer CLI commands effectively.

**Why this priority**: Good documentation is essential for tool adoption and user experience.

**Independent Test**: Can be fully tested by accessing help for each command and verifying completeness and clarity.

**Acceptance Scenarios**:

1. **Given** rustkmer CLI installed, **When** running `rustkmer --help`, **Then** the tool should display all available commands and general usage information
2. **Given** specific commands (count, query, etc.), **When** running `rustkmer <command> --help`, **Then** the tool should display detailed usage information, options, and examples for that command
3. **Given** invalid command usage, **When** running commands incorrectly, **Then** the tool should provide helpful error messages suggesting correct usage

---

### Edge Cases

- What happens when the input data directory (/Users/forrest/Temp/demodata) doesn't exist or is empty?
- How does the system handle corrupted or invalid FASTA/FASTQ files during count operations?
- What happens when running out of disk space during database creation or merging?
- How does the system handle extremely large k-mer sizes (k>63) with u128 encoding?
- What happens with concurrent access to the same database file?
- How does the system handle non-ASCII characters in file paths or sequence data?
- What happens when memory is insufficient for large dataset operations?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST test all rustkmer CLI commands (count, dump, query, fuzzy-query, stats, merge, help) with real genomic data
- **FR-002**: System MUST generate detailed test reports for each command including test methodology, inputs, outputs, and results
- **FR-003**: System MUST save test intermediate data and reports in /Users/forrest/Temp/demodata with organized subdirectory structure
- **FR-004**: System MUST validate count accuracy by comparing results against known inputs and expected outputs
- **FR-005**: System MUST measure and report performance metrics (execution time, memory usage, CPU utilization) for all operations
- **FR-006**: System MUST test error handling for invalid inputs, corrupted files, and edge cases
- **FR-007**: System MUST verify database integrity by cross-validating query results against original count data
- **FR-008**: System MUST test parallel processing capabilities and performance scalability
- **FR-009**: System MUST test u128 encoding functionality with k-mers up to length 64
- **FR-010**: System MUST document all test procedures, results, and findings in a comprehensive final report

### Key Entities *(include if feature involves data)*

- **Test Dataset**: Existing genomic data files (FASTA/FASTQ) already present in /Users/forrest/Temp/demodata
- **Test Report**: Detailed documentation of test procedures, inputs, outputs, and results for each CLI command
- **Performance Metrics**: Measured data including execution time, memory usage, CPU utilization, and throughput
- **Database Files**: .rkdb files created during testing with various k-mer sizes and parameters
- **Validation Results**: Comparison of actual vs expected results to verify accuracy

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 7 rustkmer CLI commands tested with at least 3 different real datasets each
- **SC-002**: Test reports generated for all commands with documented methodology, results, and performance metrics
- **SC-003**: Performance benchmarks established showing rustkmer can process 1GB of genomic data in under 10 minutes for count operations
- **SC-004**: Accuracy validation showing 100% correctness for query operations on known k-mers
- **SC-005**: Error handling verified for all major error conditions with appropriate error messages
- **SC-006**: Memory usage documented and verified to be within acceptable limits (<8GB for typical operations)
- **SC-007**: Parallel processing tested showing scalability improvements with multiple CPU cores
- **SC-008**: Comprehensive final report delivered summarizing all findings, recommendations, and any discovered issues