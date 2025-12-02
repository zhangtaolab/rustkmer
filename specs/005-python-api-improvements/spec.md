# Feature Specification: Python API Improvements

**Feature Branch**: `005-python-api-improvements`
**Created**: 2025-12-01
**Status**: Draft
**Input**: User description: "@/Users/forrest/Temp/demodata/python_api_system_test/reports/comprehensive_test_report.md 根据测试的结果进行 python 支持的修订和完善。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - FuzzyQuery API Enhancement (Priority: P1)

Bioinformaticians need to perform advanced fuzzy queries with configurable variant limits to prevent computational explosion when working with complex wildcard patterns in large genomic databases.

**Why this priority**: Critical for production use - current API limitations prevent users from controlling variant generation which can lead to performance issues or query failures.

**Independent Test**: Can be tested by creating FuzzyQuery objects with different variant limits and verifying the max_variants property is accessible and functional.

**Acceptance Scenarios**:

1. **Given** a FuzzyQuery object with multiple wildcards, **When** accessing the max_variants property, **Then** the property should be readable and writable
2. **Given** a FuzzyQuery that would generate > 100,000 variants, **When** setting max_variants to 10,000, **Then** the query should execute without computational explosion
3. **Given** a FuzzyQuery with high variant count, **When** attempting execution without limit, **Then** the system should provide clear error guidance

---

### User Story 2 - Enhanced KmerCounter Database Persistence (Priority: P2)

Researchers need to save k-mer counting results as databases for later querying, enabling workflow separation between counting and analysis phases.

**Why this priority**: Important for scalable bioinformatics workflows where counting and analysis are performed at different times or by different team members.

**Independent Test**: Can be tested by creating a KmerCounter, counting k-mers from a file, saving the results to a database file, and later loading that database for queries.

**Acceptance Scenarios**:

1. **Given** a KmerCounter with processed k-mer counts, **When** calling save_to_database method, **Then** a valid .rkdb file should be created
2. **Given** a newly created database file, **When** loading it with Database class, **Then** all k-mer counts should be accessible
3. **Given** a KmerCounter with existing counts, **When** merging with another counter, **Then** combined results should be accurate

---

### User Story 3 - Advanced Performance Monitoring (Priority: P3)

System administrators need to monitor Python API performance characteristics including memory usage, processing time, and resource utilization for large-scale genomic analysis jobs.

**Why this priority**: Important for production deployment and capacity planning in high-throughput bioinformatics environments.

**Independent Test**: Can be tested by enabling performance monitoring during k-mer counting operations and verifying that detailed metrics are captured and accessible.

**Acceptance Scenarios**:

1. **Given** performance monitoring enabled, **When** processing large genomic files, **Then** detailed timing and memory metrics should be captured
2. **Given** concurrent database operations, **When** monitoring is active, **Then** thread-specific performance data should be available
3. **Given** completed analysis operations, **When** querying performance history, **Then** trend data should be accessible

---

### Edge Cases

- What happens when FuzzyQuery variant generation exceeds available memory?
- How does system handle database file corruption during loading?
- What occurs when k-mer counting exceeds system memory limits?
- How does API behave with extremely long input sequences (>1MB)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: FuzzyQuery class MUST expose max_variants property as both readable and writable
- **FR-002**: FuzzyQuery MUST enforce max_variants limit to prevent computational explosion
- **FR-003**: FuzzyQuery MUST provide clear error messages when variant limits are exceeded
- **FR-004**: KmerCounter class MUST provide save_to_database method for persistence
- **FR-005**: KmerCounter.save_to_database MUST create valid .rkdb files compatible with Database class
- **FR-006**: Database class MUST support loading databases created by KmerCounter
- **FR-007**: System MUST provide performance monitoring capabilities for tracking resource usage
- **FR-008**: Performance monitoring MUST track memory usage, processing time, and query performance
- **FR-009**: System MUST handle large-scale k-mer counting operations (>10GB input) gracefully
- **FR-010**: API MUST provide progress feedback for long-running operations

### Key Entities *(include if feature involves data)*

- **FuzzyQuery**: Advanced k-mer pattern matching with configurable variant limits and wildcard support
- **KmerCounter**: K-mer counting engine with database persistence and merge capabilities
- **Database**: K-mer database storage with enhanced loading and performance monitoring
- **PerformanceMetrics**: Resource utilization tracking including memory, CPU, and timing data

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: FuzzyQuery performance tests achieve 100% success rate (currently working, API limitations resolved)
- **SC-002**: KmerCounter database persistence operations complete in under 5 seconds for typical datasets (1MB-100MB files)
- **SC-003**: Large-scale k-mer counting operations (11GB RNA-seq data) complete without memory errors (streaming processing validated)
- **SC-004**: Performance monitoring provides metrics with <1% overhead on processing operations (measured via conditional compilation benchmarks)
- **SC-005**: Overall Python API test success rate improves from current 80.6% (25/31 tests) to >95% (>29/31 tests passing)

### Success Criteria Measurement Methodology

- **Test Suite Definition**: Python API tests = `tests/python/` comprehensive test suite (31 total tests)
- **Typical Datasets**: 1MB-100MB genomic files for standard performance testing
- **Large-Scale Testing**: >10GB input data with streaming processing and memory mapping
- **Performance Overhead**: Measured by comparing execution with/without `profiling` feature flag
- **Database Operations**: Timed using Rust's `std::time::Instant` for precise measurement

### Assumptions

- RustKmer Python API is already 91.8% functional with excellent core performance
- Existing database format (.rkdb) supports the required persistence operations
- Performance monitoring can be implemented without significant API breaking changes
- FuzzyQuery variant generation can be controlled through existing architecture

## Dependencies & Constraints

### Dependencies
- Existing RustKmer core library and database format
- PyO3 Python binding framework
- Current 83 passing unit tests provide foundation for enhancements

### Constraints
- API changes must maintain backward compatibility with existing code
- Performance improvements should not impact current excellent query speeds
- New features must work with existing .rkdb database files
- Memory usage should remain within reasonable limits for genomic applications