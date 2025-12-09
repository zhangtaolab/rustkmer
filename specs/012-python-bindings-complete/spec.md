# Feature Specification: Complete Python Bindings for RustKmer

**Feature Branch**: `012-python-bindings-complete`
**Created**: 2025-01-09
**Status**: Draft
**Input**: User description: "现在需要完善rustkmer所有包的 python binding，需要以现有的 u128为基础，不需要支持u64, 需要全面覆盖CLI版本的命令。记住是python binding不是重新写python 支持。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Python API for K-mer Counting (Priority: P1)

Python bioinformaticians need to count k-mers in sequence files (FASTA/FASTQ) directly from Python scripts, enabling integration with existing Python-based genomics workflows and pipelines.

**Why this priority**: K-mer counting is the foundational operation for RustKmer and the most frequently used functionality in bioinformatics pipelines.

**Independent Test**: Can be fully tested by creating a KmerCounter instance in Python, counting k-mers in a test FASTA file, and verifying the resulting database contains expected k-mer counts.

**Acceptance Scenarios**:

1. **Given** a Python environment with rustkmer installed, **When** creating a KmerCounter with k=31 and input FASTA file, **Then** the system creates a valid RKDB database file
2. **Given** a KmerCounter instance, **When** calling count() method on a FASTQ file, **Then** returns a Database object containing all counted k-mers
3. **Given** invalid sequence input, **When** attempting to count k-mers, **Then** raises appropriate SequenceError with descriptive message

---

### User Story 2 - Database Query Operations from Python (Priority: P1)

Researchers need to query k-mer counts and existence checks from existing RKDB databases through Python, enabling fast lookups in genomics analysis scripts.

**Why this priority**: Database querying is essential for downstream analysis and is the second most common operation after counting.

**Independent Test**: Can be fully tested by loading an existing RKDB database file and performing various query operations (exact match, batch queries, existence checks) with known k-mers.

**Acceptance Scenarios**:

1. **Given** an existing RKDB database file, **When** loading it in Python using Database class, **Then** successfully loads with correct metadata (k-mer size, total k-mers)
2. **Given** a loaded Database, **When** querying for known k-mers, **Then** returns accurate count values matching CLI results
3. **Given** a Database instance, **When** performing batch queries for multiple k-mers, **Then** returns results for all k-mers efficiently

---

### User Story 3 - Fuzzy Query and Mutation Analysis (Priority: P2)

Genomics researchers need to perform fuzzy queries with wildcards and mutation tolerance from Python to find similar k-mers and analyze sequence variations.

**Why this priority**: Fuzzy queries are critical for variant analysis and mutation studies, enabling researchers to find k-mers within specified edit distances.

**Independent Test**: Can be fully tested by creating a FuzzyQuery instance and performing wildcard searches and mutation-tolerant queries against a test database.

**Acceptance Scenarios**:

1. **Given** a Database instance, **When** creating a FuzzyQuery object, **Then** successfully initializes with specified parameters
2. **Given** a FuzzyQuery instance, **When** searching with wildcard pattern "A*TG*C", **Then** returns all matching k-mers within specified mutation tolerance
3. **Given** a FuzzyQuery with tolerance=1, **When** querying k-mer "AAAAA", **Then** returns all k-mers that differ by at most 1 mutation

---

### User Story 4 - Database Statistics and Analysis (Priority: P2)

Bioinformaticians need to calculate and retrieve comprehensive statistics about k-mer databases from Python, including frequency distributions, coverage estimates, and database metadata.

**Why this priority**: Statistics provide essential insights into database composition and are frequently required for quality control and analysis reporting.

**Independent Test**: Can be fully tested by loading a database and calculating statistics, then comparing results with CLI stats command output.

**Acceptance Scenarios**:

1. **Given** a loaded Database, **When** calling calculate_stats() method, **Then** returns DatabaseStats with frequency distribution and metadata
2. **Given** a DatabaseStats object, **When** accessing properties like total_kmers, unique_kmers, coverage, **Then** returns accurate numerical values
3. **Given** stats calculation request, **When** requesting histogram data, **Then** returns frequency distribution with configurable bin counts

---

### User Story 5 - Database Merge Operations (Priority: P3)

Pipeline developers need to merge multiple RKDB databases from Python to combine k-mer counts from different samples or sequencing runs into unified databases.

**Why this priority**: Database merging is important for large-scale projects where samples are processed separately and later combined.

**Independent Test**: Can be fully tested by creating two small databases and merging them, then verifying the merged database contains the union of k-mers with correct count aggregation.

**Acceptance Scenarios**:

1. **Given** multiple Database objects, **When** calling merge() method, **Then** creates a new database containing all unique k-mers from input databases
2. **Given** databases with overlapping k-mers, **When** merging, **Then** correctly aggregates counts using sum strategy (adding counts for identical k-mers)
3. **Given** incompatible databases (different k-mer sizes), **When** attempting to merge, **Then** raises DatabaseError with clear explanation

---

### User Story 6 - Database Dump and Export (Priority: P3)

Users need to export k-mer data from RKDB databases to text formats from Python for downstream analysis, visualization, or compatibility with other tools.

**Why this priority**: Data export enables interoperability with external tools and custom analysis pipelines that require text-based k-mer data.

**Independent Test**: Can be fully tested by dumping a database to text format and verifying the output format and content.

**Acceptance Scenarios**:

1. **Given** a Database instance, **When** calling dump() with format="text", **Then** exports all k-mers and counts to specified file in readable format
2. **Given** a Database instance, **When** calling dump() with format="csv", **Then** exports data in CSV format with headers
3. **Given** large database, **When** calling dump() with threshold parameter, **Then** only exports k-mers with counts above threshold

---

### Edge Cases

- What happens when attempting to load databases with incompatible formats or versions?
- How does system handle memory constraints when querying extremely large databases?
- What happens when invalid k-mer sequences (containing N or non-ACGT characters) are provided?
- How does system handle concurrent access to the same database file from multiple Python processes?
- What happens when system runs out of memory during k-mer counting operations?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Python bindings MUST provide KmerCounter class for counting k-mers in FASTA/FASTQ files with configurable k-mer sizes
- **FR-002**: Python bindings MUST provide Database class for loading and querying existing RKDB database files
- **FR-003**: Python bindings MUST provide FuzzyQuery class for wildcard searches and mutation-tolerant queries
- **FR-004**: Python bindings MUST support all CLI operations: count, query, dump, fuzzy-query, fuzzy-query-batch, merge, and stats
- **FR-005**: Python bindings MUST be built on existing u128 encoding implementation without u64 support
- **FR-006**: System MUST provide comprehensive error handling with Python-specific exception types
- **FR-007**: Python bindings MUST support both single-threaded and multi-threaded operations
- **FR-008**: System MUST provide memory-efficient database access using memory mapping for large files with automatic pagination for memory-constrained queries
- **FR-009**: Python bindings MUST maintain API compatibility with existing CLI command behaviors and outputs
- **FR-010**: System MUST provide progress reporting via Python callback functions for long-running operations (counting, merging, stats calculation)
- **FR-011**: Python bindings MUST support batch operations with automatic concurrent processing for efficient handling of multiple queries
- **FR-012**: System MUST provide configuration options for verbosity levels and debugging output

### Key Entities

- **KmerCounter**: Python class representing k-mer counting functionality with configurable parameters
- **Database**: Python class providing access to RKDB database files with query and metadata operations
- **FuzzyQuery**: Python class for performing wildcard and mutation-tolerant searches
- **DatabaseStats**: Python class containing statistical information about k-mer databases
- **QueryResult**: Python class containing results from k-mer query operations
- **FuzzyQueryResult**: Python class containing results from fuzzy query operations with match details
- **PerformanceTimer**: Python utility class for measuring operation execution times
- **ResourceStats**: Python class providing memory and system resource usage information

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Python API performance within 10% of CLI performance for all operations (count, query, fuzzy-query, merge, stats)
- **SC-002**: All 7 CLI commands have complete Python API coverage with 100% functional parity
- **SC-003**: Python package can be installed via pip with automatic compilation of Rust extensions on major platforms (Linux, macOS, Windows) for Python >= 3.10
- **SC-004**: Memory usage for database operations remains within 5% of CLI baseline when accessing identical databases
- **SC-005**: Query accuracy matches CLI results exactly for 100% of test cases across different database sizes and k-mer lengths
- **SC-006**: Comprehensive test suite achieves 95% code coverage for Python bindings
- **SC-007**: Documentation includes complete API reference with examples for all classes and methods
- **SC-008**: Error messages are informative and actionable, enabling users to diagnose and fix issues without external help

## Clarifications

### Session 2025-01-09

- Q: 数据库合并策略（merge strategy）应该如何定义？ → A: 使用求和策略（将相同k-mer的计数值相加）
- Q: 支持的Python版本范围是什么？ → A: Python >= 3.10
- Q: 批量操作是否应该并发处理？ → A: 自动并发处理
- Q: 进度报告应该如何实现？ → A: 使用Python回调函数机制
- Q: 大型数据库查询的内存管理策略是什么？ → A: 自动分页查询，内部管理内存限制

### Session 2025-12-09

- Q: 是否有进行rustkmer cli和python api的对比测试？ → A: 是的，已有完整的兼容性测试框架，包括cli_comparator.py、test_count_compatibility.py等测试文件，验证Python API与CLI命令的功能一致性