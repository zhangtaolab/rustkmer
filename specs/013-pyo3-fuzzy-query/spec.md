# Feature Specification: PyO3 Fuzzy Query Implementation

**Feature Branch**: `013-pyo3-fuzzy-query`
**Created**: 2025-12-20
**Status**: In Progress
**Input**: 实现 PyO3 fuzzy query 功能，集成 N-wildcard 支持如 GANNNGA 模式，完成与现有 query 功能的整合，实现一次加载数据库即可进行 query 和 fuzzy-query 操作，参考 CLI 版本实现完整的 PyO3 绑定，包括编译、安装和测试，最后编写 demo 和完善文档

## User Scenarios & Testing

### User Story 1 - N-Wildcard Fuzzy Query (Priority: P1)

A bioinformatics researcher wants to find k-mers in a database that match patterns with ambiguous positions, using N wildcards to represent any nucleotide (A, T, C, G). They need to search for variants like "GANNNGA" which should match all combinations where N positions can be any nucleotide.

**Why this priority**: This is the core functionality that enables researchers to find sequence variants with ambiguous positions, which is fundamental for handling incomplete or low-quality genomic data.

**Independent Test**: Can be fully tested by querying a known pattern with N wildcards and verifying that all possible nucleotide combinations are correctly expanded and searched.

**Acceptance Scenarios**:
1. **Given** a researcher provides a pattern like "GANNNGA", **When** they perform a fuzzy query, **Then** the system expands all N positions to A,T,C,G combinations (64 total for 3 N's) and searches for matches
2. **Given** the pattern contains multiple N wildcards, **When** querying, **Then** the system generates all possible combinations without exceeding memory limits
3. **Given** a pattern has no N wildcards, **When** performing fuzzy query, **Then** the system treats it as a regular query with mutation tolerance

---

### User Story 2 - Shared Database Usage (Priority: P1)

A researcher wants to load a database once and use it for both regular queries and fuzzy queries without reloading, improving performance and resource efficiency.

**Why this priority**: This is essential for workflow efficiency, allowing researchers to perform multiple types of queries on the same database without the overhead of repeated loading.

**Independent Test**: Can be tested by loading a database once and performing both regular query and fuzzy query operations, measuring performance improvement.

**Acceptance Scenarios**:
1. **Given** a database is loaded, **When** the researcher performs both query and fuzzy_query operations, **Then** the database is used efficiently without reloading
2. **Given** multiple fuzzy queries are performed, **When** executing, **Then** subsequent queries reuse the same database instance
3. **Given** database operations are complete, **When** closing the database, **Then** all resources are properly released

---

### User Story 3 - Integration with Existing API (Priority: P2)

A developer familiar with the existing rustkmer Python API wants to use fuzzy query functionality through the same interface patterns, ensuring consistency and ease of use.

**Why this priority**: API consistency reduces learning curve and makes the feature adoption easier for existing users.

**Independent Test**: Can be tested by comparing the fuzzy query API with the existing query API to ensure consistent patterns and behavior.

**Acceptance Scenarios**:
1. **Given** a user familiar with `db.query(kmer)`, **When** they use `db.fuzzy_query(pattern, mutations=n)`, **Then** the API feels natural and consistent
2. **Given** error handling patterns, **When** fuzzy query encounters invalid input, **Then** appropriate exceptions are raised with clear messages
3. **Given** result objects, **When** fuzzy query returns results, **Then** they follow the same patterns as regular query results

---

### User Story 4 - Performance and Testing (Priority: P2)

A performance-conscious researcher wants fuzzy queries to be significantly faster than subprocess-based approaches, with comprehensive testing to ensure reliability.

**Why this priority**: Performance improvements justify the PyO3 implementation effort and ensure practical usability.

**Independent Test**: Can be tested by measuring query performance against subprocess implementation and running comprehensive test suites.

**Acceptance Scenarios**:
1. **Given** PyO3 and subprocess implementations, **When** performing identical fuzzy queries, **Then** PyO3 version is significantly faster (target: 5x speedup)
2. **Given** test coverage requirements, **When** running test suite, **Then** all critical paths have adequate test coverage
3. **Given** memory usage constraints, **When** processing large queries, **Then** memory usage remains within acceptable limits

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST support N-wildcard patterns (e.g., "GANNNGA") that expand to all nucleotide combinations
- **FR-002**: System MUST integrate with existing PyDatabase to enable shared database usage
- **FR-003**: System MUST provide consistent Python API that matches existing rustkmer patterns
- **FR-004**: System MUST support mutation tolerance alongside wildcard expansion
- **FR-005**: System MUST handle position-specific mutation constraints
- **FR-006**: System MUST provide comprehensive error handling and validation
- **FR-007**: System MUST support batch processing for multiple queries
- **FR-008**: System MUST maintain feature parity with CLI fuzzy query implementation

### Key Entities

- **PyFuzzyQuery**: Main class for executing fuzzy queries against databases
- **PyFuzzyResult**: Result container with matches, metadata, and statistics
- **PyFuzzyMatch**: Individual match result with k-mer, count, distance, and mutations
- **FuzzyQueryEngine**: Core Rust engine for executing fuzzy queries
- **PositionMutationConfig**: Configuration for position-specific mutation constraints

### Success Criteria

- **SC-001**: Researchers can perform N-wildcard queries (like "GANNNGA") with results matching CLI implementation
- **SC-002**: Database loading is shared between regular query and fuzzy query operations
- **SC-003**: PyO3 fuzzy queries are at least 5x faster than subprocess-based approach
- **SC-004**: All existing test cases pass, and new test coverage exceeds 90%
- **SC-005**: API follows consistent patterns with existing rustkmer Python bindings
- **SC-006**: Documentation and demo scripts enable users to quickly adopt the feature

## Technical Constraints

- Must compile and link properly with Python development libraries
- Must maintain compatibility with existing PyDatabase and query functionality
- Must handle memory efficiently for large wildcard expansions
- Must provide clear error messages for invalid inputs and edge cases
- Must support both development and release build configurations