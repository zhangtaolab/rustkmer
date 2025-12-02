# Feature Specification: Python Bindings for RustKmer

**Feature Branch**: `001-python-bindings`
**Created**: 2025-12-01
**Status**: Draft
**Input**: User description: "撰写python接口，方便 python 调用现有的 rustkmer ,并给出文档。新建 004 分支进行"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic k-mer Counting from Python (Priority: P1)

Python developers need to perform k-mer counting on genomic data directly from Python scripts without using command-line tools. This enables integration into bioinformatics pipelines and data analysis workflows.

**Why this priority**: This is the core functionality of RustKmer and the most common use case for Python integration in bioinformatics workflows.

**Independent Test**: Can be tested by counting k-mers from a simple DNA sequence and verifying the results match the command-line version.

**Acceptance Scenarios**:

1. **Given** a Python script with RustKmer bindings imported, **When** the user calls the count function with a DNA sequence and k-mer size, **Then** the system returns a dictionary with k-mer counts
2. **Given** a FASTA file path, **When** the user calls the count function with file input, **Then** the system processes the entire file and returns k-mer counts
3. **Given** invalid DNA sequence input, **When** the user calls the count function, **Then** the system raises an appropriate error with clear message

---

### User Story 2 - Database Query Operations (Priority: P1)

Researchers need to query existing k-mer databases from Python to retrieve specific k-mer counts for analysis and validation purposes.

**Why this priority**: Query operations are essential for comparing k-mer frequencies across different datasets and validating experimental results.

**Independent Test**: Can be tested by creating a small database, then querying specific k-mers and verifying returned counts.

**Acceptance Scenarios**:

1. **Given** a valid database file, **When** the user queries for specific k-mers, **Then** the system returns accurate counts for each k-mer
2. **Given** a database and non-existent k-mers, **When** the user queries, **Then** the system returns zero counts for those k-mers
3. **Given** an invalid database file path, **When** the user attempts to query, **Then** the system raises a clear error about file access

---

### User Story 3 - Fuzzy Query with Wildcards (Priority: P2)

Bioinformaticians need to perform fuzzy queries with wildcards to find similar k-mers that may contain sequencing errors or biological variations.

**Why this priority**: Fuzzy queries are important for error tolerance in sequencing data and finding biologically related sequences.

**Independent Test**: Can be tested by querying with wildcard patterns and verifying the system returns all matching k-mers with their counts.

**Acceptance Scenarios**:

1. **Given** a database and a query pattern with wildcards, **When** the user performs a fuzzy query, **Then** the system returns all k-mers matching the pattern with their counts
2. **Given** a fuzzy query with too many potential matches, **When** the user runs the query, **Then** the system either applies reasonable limits or raises a warning about result size

---

### User Story 4 - Batch Processing and Performance (Priority: P2)

Data scientists need to process multiple sequences or large datasets efficiently through Python interfaces for high-throughput analysis.

**Why this priority**: Performance is critical for processing large genomic datasets in research environments.

**Independent Test**: Can be tested by processing multiple sequences in batch and measuring throughput and memory usage.

**Acceptance Scenarios**:

1. **Given** multiple input sequences, **When** the user performs batch counting, **Then** the system processes all sequences efficiently and returns combined results
2. **Given** large genomic files, **When** the user processes them through Python, **Then** the system maintains reasonable memory usage and processing time

---

### Edge Cases

- What happens when the input sequence contains characters other than A, T, G, C?
- How does the system handle extremely large k-mer sizes (>127)?
- What happens when the database file is corrupted or incompatible?
- How does the system handle concurrent access to the same database from multiple Python processes?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Python package MUST provide k-mer counting functionality with configurable k-mer size
- **FR-002**: Python package MUST support both string sequences and file input for counting operations
- **FR-003**: Users MUST be able to query k-mer databases and retrieve exact counts
- **FR-004**: Python package MUST support fuzzy queries with wildcard patterns (N for any nucleotide)
- **FR-005**: System MUST provide clear error messages for invalid inputs or file access issues
- **FR-006**: Python package MUST support batch processing of multiple sequences efficiently
- **FR-007**: System MUST handle both compressed and uncompressed FASTA/FASTQ files
- **FR-008**: Python package MUST provide database creation and management functionality
- **FR-009**: System MUST support both canonical and non-canonical k-mer counting modes
- **FR-010**: Python package MUST include comprehensive documentation and usage examples

### Key Entities

- **KmerCounter**: Main class for counting k-mers from sequences and files
- **Database**: Object representing k-mer database with query capabilities
- **QueryResult**: Object containing k-mer query results with metadata
- **FuzzyQuery**: Object for wildcard and mutation-tolerant queries
- **Sequence**: Entity representing DNA/RNA sequences with validation

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Python developers can perform basic k-mer counting with less than 5 lines of code
- **SC-002**: System processes standard genomic files (up to 1GB) within 30 seconds on typical hardware
- **SC-003**: Memory usage for Python interface does not exceed 150% of command-line tool usage
- **SC-004**: Query operations return results in under 100ms for databases with up to 1 million k-mers
- **SC-005**: 95% of common bioinformatics workflows can be reproduced using Python interface
- **SC-006**: Installation and setup process takes less than 5 minutes for Python developers
- **SC-007**: Documentation examples work correctly for all major use cases without modification

## Optional Sections

### Assumptions

- Users have Python 3.8+ installed on their systems
- Target users are familiar with basic bioinformatics concepts (k-mers, FASTA/FASTQ formats)
- Users have access to genomic data in standard formats
- System has sufficient memory for processing typical genomic datasets

### Constraints

- Python interface must maintain compatibility with existing RustKmer database formats
- Performance should not be significantly worse than command-line tool (within 20%)
- Interface must be cross-platform (Windows, macOS, Linux)
- Memory usage should be reasonable for typical bioinformatics workstations