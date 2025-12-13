# Feature Specification: Remove Rayon Library and Parallel Processing Support

**Feature Branch**: `020-remove-rayon`
**Created**: 2025-12-13
**Status**: Draft
**Input**: User description: "由于 rustkmer count， query 和 fuzzy-query 只是引用了 Rayon 库，却没有真正的实现并行，现在需要取消并行的支持，除去Rayon库的引用"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Remove Rayon Library Dependency (Priority: P1)

Project maintainers need to simplify the codebase by removing unused dependencies to reduce build complexity, binary size, and potential security vulnerabilities.

**Why this priority**: This is the foundational change that enables all other simplifications and directly addresses the user's request to remove the Rayon library reference.

**Independent Test**: Can be fully tested by checking Cargo.toml for Rayon absence and verifying the project builds successfully without the dependency.

**Acceptance Scenarios**:

1. **Given** the rustkmer project, **When** examining Cargo.toml, **Then** no Rayon dependency is present
2. **Given** the project without Rayon, **When** running cargo build, **Then** the build completes successfully without errors
3. **Given** the compiled binary, **When** checking for Rayon symbols, **Then** no Rayon-related symbols are found in the binary

---

### User Story 2 - Simplify Count Command Implementation (Priority: P1)

Users need the count command to function correctly using sequential processing instead of unused parallel processing, maintaining all existing functionality while simplifying the code.

**Why this priority**: The count command is one of the core CLI commands and must continue to work correctly for k-mer counting operations.

**Independent Test**: Can be fully tested by running rustkmer count on sample FASTA/FASTQ files and verifying the output matches expected k-mer counts.

**Acceptance Scenarios**:

1. **Given** a FASTA file with sequences, **When** running rustkmer count with k=31, **Then** the command processes the file sequentially and produces a valid RKDB database
2. **Given** multiple input files, **When** running rustkmer count with --canonical flag, **Then** all files are processed sequentially and counts are correctly aggregated
3. **Given** the count command, **When** examining the implementation, **Then** no parallel iterators (par_iter, par_chunks, etc.) are used

---

### User Story 3 - Simplify Query Command Implementation (Priority: P1)

Users need the query command to function correctly using sequential processing, maintaining fast k-mer lookups from RKDB databases.

**Why this priority**: The query command is essential for retrieving k-mer counts from existing databases and is frequently used in analysis workflows.

**Independent Test**: Can be fully tested by loading an RKDB database and querying known k-mers, verifying the results match expected counts.

**Acceptance Scenarios**:

1. **Given** a loaded RKDB database, **When** running rustkmer query with a k-mer sequence, **Then** the command returns the correct count from the database
2. **Given** multiple k-mers to query, **When** running rustkmer query with batch input, **Then** all queries are processed sequentially and results are accurate
3. **Given** the query command, **When** examining the implementation, **Then** no parallel processing is used in the query logic

---

### User Story 4 - Simplify Fuzzy-Query Command Implementation (Priority: P1)

Users need the fuzzy-query command to function correctly using sequential processing, maintaining the ability to find similar k-mers with wildcards and mutation tolerance.

**Why this priority**: The fuzzy-query command is used for advanced sequence analysis and must maintain its core functionality during the simplification.

**Independent Test**: Can be fully tested by performing fuzzy searches with wildcard patterns and verifying the results match expected matches.

**Acceptance Scenarios**:

1. **Given** a database with k-mers, **When** running rustkmer fuzzy-query with a wildcard pattern, **Then** the command finds all matching k-mers using sequential processing
2. **Given** a pattern with maximum mismatches, **When** running fuzzy-query, **Then** only k-mers within the specified distance are returned
3. **Given** the fuzzy-query command, **When** examining the implementation, **Then** no parallel iterators are used in the fuzzy matching logic

---

### User Story 5 - Verify Build and Test Suite (Priority: P1)

Project maintainers need to ensure the simplified codebase passes all existing tests and builds successfully across different platforms.

**Why this priority**: This validates that the removal of parallel processing doesn't break any existing functionality and the codebase remains stable.

**Independent Test**: Can be fully tested by running the complete test suite and verifying all tests pass without modification.

**Acceptance Scenarios**:

1. **Given** the test suite, **When** running cargo test, **Then** all tests pass successfully
2. **Given** the documentation, **When** checking for Rayon references, **Then** no documentation mentions Rayon or parallel processing
3. **Given** the build process, **When** building on different platforms, **Then** builds complete successfully on all supported platforms

---

### Edge Cases

- What happens when users have existing build scripts or CI/CD pipelines that expect Rayon to be present?
- How does the removal affect any benchmarks or performance comparisons?
- Are there any hidden dependencies on Rayon that might cause compilation errors?
- What if some tests were specifically testing parallel functionality (these should be updated or removed)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST remove all Rayon dependency references from Cargo.toml and related configuration files
- **FR-002**: System MUST remove all parallel iterator usage (par_iter, par_chunks, par_extend, etc.) from the count command implementation
- **FR-003**: System MUST remove all parallel iterator usage from the query command implementation
- **FR-004**: System MUST remove all parallel iterator usage from the fuzzy-query command implementation
- **FR-005**: System MUST ensure all existing tests continue to pass without modification to test logic
- **FR-006**: System MUST verify the compiled binary size is reduced or remains unchanged after removing Rayon
- **FR-007**: System MUST ensure no compilation errors occur when building without Rayon
- **FR-008**: System MUST maintain backward compatibility for all CLI commands and their outputs

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Rayon library is completely removed from Cargo.toml dependencies (verified by grep returning no matches)
- **SC-002**: count command processes FASTA/FASTQ files sequentially and produces correct RKDB output (verified by comparing output with expected results)
- **SC-003**: query command retrieves k-mer counts accurately from databases (verified by testing against known k-mer counts)
- **SC-004**: fuzzy-query command finds matching k-mers correctly using sequential processing (verified by pattern matching tests)
- **SC-005**: All existing unit and integration tests pass without modification (100% pass rate)
- **SC-006**: Project builds successfully on Linux, macOS, and Windows without errors (cross-platform compatibility)
- **SC-007**: Binary size is reduced by at least 5% or remains within 1% of original size (size optimization)
