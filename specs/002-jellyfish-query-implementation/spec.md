# Feature Specification: Jellyfish Query Implementation

**Feature Branch**: `002-jellyfish-query-implementation`
**Created**: 2025-11-28
**Status**: Completed
**Input**: User description: "实现jellyfish query的功能，该功能能查询kmer的数量，你可以根据 jellyfish 的源代码实现，也可以用rustkmer count sort 以后的结果，然后编写一个二进制文件的index，提高查询效率，可以先做个研究。"

## User Scenarios & Testing

### User Story 1 - Individual K-mer Query (Priority: P1)

As a bioinformatics researcher, I need to query specific k-mer sequences to get their count from a processed genomic dataset, so I can quickly check the abundance of particular sequences in my sample.

**Why this priority**: This is the most fundamental query operation and provides immediate value to users who need to check specific k-mer counts.

**Independent Test**: Can be fully tested by creating a small database with known k-mer counts and verifying that individual queries return the expected values.

**Acceptance Scenarios**:

1. **Given** a valid k-mer database file, **When** I query a k-mer that exists in the database, **Then** the system returns the exact count with tab-separated output format
2. **Given** a valid k-mer database file, **When** I query a k-mer that doesn't exist in the database, **Then** the system returns "Invalid mer" message or a zero count
3. **Given** a database with k-mer size 21, **When** I query a k-mer with different length, **Then** the system returns an appropriate error message

---

### User Story 2 - Batch K-mer Query (Priority: P1)

As a researcher working with multiple sequences of interest, I need to query multiple k-mers in a single command to efficiently retrieve counts for a set of target sequences.

**Why this priority**: Batch querying is a common workflow in genomic analysis and provides significant efficiency improvements over individual queries.

**Independent Test**: Can be fully tested by providing multiple k-mers as input and verifying that all results are returned with correct formatting and counts.

**Acceptance Scenarios**:

1. **Given** a valid k-mer database, **When** I query multiple k-mers in one command, **Then** the system returns results for all k-mers with proper tab-separated formatting
2. **Given** a mixture of valid and invalid k-mers, **When** I query them together, **Then** the system returns appropriate results for valid k-mers and error messages for invalid ones

---

### User Story 3 - Sequence File Query (Priority: P2)

As a researcher with a set of sequences in FASTA format, I need to query all k-mers from these sequences against my database to find which sequences are present in my reference dataset.

**Why this priority**: This enables researchers to quickly check the presence/absence of entire sequence files against reference databases.

**Independent Test**: Can be fully tested by creating a test FASTA file with known sequences and verifying that all constituent k-mers are queried correctly.

**Acceptance Scenarios**:

1. **Given** a valid k-mer database and FASTA file, **When** I use sequence file query mode, **Then** the system extracts all k-mers from the file and returns their counts
2. **Given** a sequence file with sequences shorter than the database k-mer size, **When** I query it, **Then** the system gracefully skips these sequences

---

### User Story 4 - Interactive Query Mode (Priority: P3)

As a researcher exploring k-mer frequencies, I need an interactive mode to quickly query multiple k-mers in succession without re-running the command each time.

**Why this priority**: Interactive mode provides flexibility for exploratory analysis and improves user experience for iterative workflows.

**Independent Test**: Can be fully tested by entering interactive mode and querying multiple k-mers through stdin input.

**Acceptance Scenarios**:

1. **Given** a valid k-mer database, **When** I enter interactive mode, **Then** I can input k-mers one by one and receive immediate results
2. **Given** interactive mode, **When** I input multiple k-mers on one line, **Then** the system processes all of them and returns results for each

---

### Edge Cases

- **FR-014**: When database file is corrupted or has invalid format, system MUST detect corruption and return specific error message: "Invalid database format: file corrupted or unsupported version"
- **FR-015**: When k-mers contain invalid characters (non-ATCG), system MUST reject with error message: "Invalid k-mer: contains non-ATCG characters" and continue processing remaining valid k-mers
- **FR-016**: When memory is insufficient for pre-loading large databases, system MUST automatically fall back to disk-based query mode with message: "Insufficient memory for pre-load: using disk-based queries"
- **FR-017**: For concurrent access to the same database file, system MUST allow multiple read operations simultaneously and return "Database busy: retry in 1 second" if write operations interfere
- **FR-018**: When database file permissions are read-only or inaccessible, system MUST return specific error: "Permission denied: cannot read database file" with exit code 1

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide a `query` subcommand that accepts a database file and one or more k-mer sequences
- **FR-002**: System MUST support individual k-mer queries with output in "k-mer\tcount" format
- **FR-003**: System MUST support batch k-mer queries where multiple k-mers can be provided in a single command
- **FR-004**: System MUST support sequence file queries using the `-s` flag to process FASTA files
- **FR-005**: System MUST provide interactive mode using the `-i` flag for querying via stdin
- **FR-006**: System MUST validate k-mer sequences and only process valid ATCG characters
- **FR-007**: System MUST validate that k-mer length matches the database's k-mer size
- **FR-008**: System MUST provide memory management options with `-l` (load) and `-L` (no-load) flags
- **FR-009**: System MUST support output redirection using the `-o` flag
- **FR-010**: System MUST implement efficient binary search on sorted k-mer databases
- **FR-011**: System MUST handle missing database files with clear error messages
- **FR-012**: System MUST validate database file format using magic number verification
- **FR-013**: System MUST provide jellyfish-compatible error messages for invalid k-mers

### Key Entities

- **K-mer Database**: Binary file containing sorted k-mer sequences with associated counts, including metadata header for format validation and efficient access
- **Database Header**: Metadata structure containing magic number, version, k-mer size, total k-mers, and data offset information for file validation and navigation
- **K-mer Entry**: Individual record containing encoded k-mer sequence (64-bit) and associated count (32-bit) for storage and retrieval
- **Query Result**: Tab-separated output containing k-mer sequence and its count, or appropriate error message for invalid queries

## Success Criteria

### Measurable Outcomes

- **SC-001**: Individual k-mer queries return results in under 1 millisecond for databases containing up to 1 million k-mers
- **SC-002**: Batch queries complete in under 10 milliseconds for up to 100 k-mers against databases containing up to 10 million k-mers
- **SC-003**: System uses no more than 2x the database size in memory when using pre-load option
- **SC-004**: Database files can be created and queried for datasets containing up to 100 million k-mers without performance degradation
- **SC-005**: Error messages are clear and actionable, allowing users to identify and correct input issues in under 30 seconds. Measured by user task completion studies where 90% of users can correct common input errors (invalid k-mer, wrong database, permission issues) within 30 seconds without external documentation
- **SC-006**: Command interface is fully compatible with jellyfish query syntax, allowing users familiar with jellyfish to use the system without additional training. Measured by syntax compatibility test covering all jellyfish query flags and argument patterns with 100% compatibility
- **SC-007**: System maintains 99.9% accuracy in k-mer count retrieval across all query modes and database sizes. Measured by comparing query results against reference jellyfish outputs on test datasets with error tolerance of ±0.1% for count values

### Performance Targets

- **Query Latency**: <1ms for individual queries, <10ms for batch queries (100 k-mers)
- **Memory Usage**: <2x database size when pre-loaded, <100MB when disk-based
- **Throughput**: >1000 queries per second for batch operations
- **Scalability**: Support databases up to 1GB in size without performance degradation