# Feature Specification: Python Fuzzy Query API

**Feature Branch**: `001-python-fuzzy-query`
**Created**: 2025-12-14
**Status**: Draft
**Input**: User description: "用类似的python api query 的思路，实现 fuzzy-query"

## Clarifications

### Session 2025-12-14

- Q: How does system handle extremely large numbers of matches? → A: Default limit of 10,000 matches with offset/limit pagination parameters
- Q: Batch query error handling when invalid k-mers present? → A: Continue processing valid k-mers, return results and error list for invalid ones
- Q: Parallel processing configuration and limits? → A: Default adaptive parallelism with user-configurable maximum worker threads

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic Fuzzy Query Search (Priority: P1)

A bioinformatics researcher wants to find k-mers in a database that are similar to their query sequence, allowing for a small number of mutations. They need a simple way to search for variants of their sequence that may exist in the database with 1-2 base differences.

**Why this priority**: This is the core functionality that enables researchers to find sequence variants, which is fundamental for mutation analysis, strain typing, and evolutionary studies.

**Independent Test**: Can be fully tested by querying a known k-mer with 1 mutation tolerance and verifying that all variants at distance 0 and 1 are returned with correct counts and mutation information.

**Acceptance Scenarios**:

1. **Given** a researcher has a valid k-mer sequence, **When** they perform a fuzzy query with 1 mutation tolerance, **Then** the system returns all exact matches (distance 0) and all single-base mutations (distance 1) with their occurrence counts
2. **Given** a researcher queries with 2 mutation tolerance, **Then** the system returns matches at distances 0, 1, and 2, each with proper mutation descriptions
3. **Given** the query k-mer has no variants in the database, **When** performing fuzzy query, **Then** the system returns an empty result set with proper indication of no matches

---

### User Story 2 - Batch Fuzzy Query Processing (Priority: P2)

A researcher needs to query hundreds of k-mers against a database to find variants for each sequence. They want to process these queries efficiently in parallel rather than one at a time.

**Why this priority**: Batch processing is essential for large-scale analyses where researchers need to find variants across many sequences, significantly improving productivity for genome-wide studies.

**Independent Test**: Can be tested by querying a batch of 10 k-mers with fuzzy matching and verifying that all results are returned correctly with proper association between input queries and their respective matches.

**Acceptance Scenarios**:

1. **Given** a researcher provides a list of 100 k-mers, **When** they perform a batch fuzzy query, **Then** the system returns results for all k-mers with their respective variant matches
2. **Given** batch processing is requested, **When** executing, **Then** the system processes queries in parallel and completes faster than sequential processing
3. **Given** some k-mers in the batch are invalid, **When** performing batch query, **Then** the system continues processing valid k-mers and returns both results and error list for invalid ones

---

### User Story 3 - Result Analysis and Export (Priority: P3)

After performing fuzzy queries, a researcher needs to analyze the results, understand mutation patterns, and export data in different formats for further analysis or publication.

**Why this priority**: Analysis and export capabilities enable researchers to derive insights from their data and integrate results into their workflows and publications.

**Independent Test**: Can be tested by performing a fuzzy query and exporting results in each supported format (JSON, table, TSV) to verify correct formatting and data preservation.

**Acceptance Scenarios**:

1. **Given** fuzzy query results are returned, **When** the researcher requests JSON format, **Then** the system provides a complete JSON representation of all matches and metadata
2. **Given** results contain multiple matches, **When** the researcher requests a table view, **Then** the system formats results in a readable table showing k-mer, count, distance, and mutations
3. **Given** the researcher wants to analyze mutation patterns, **When** they query results, **Then** they can group matches by distance and identify the most common mutations

---

### Edge Cases

- What happens when the mutation tolerance is set to 0? (Should behave like exact query)
- How does system handle queries with invalid DNA characters? (Should validate and reject)
- What happens when the query k-mer length doesn't match the database k-mer size? (Should validate and reject)
- How does system handle extremely large numbers of matches? (Default limit of 10,000 matches with offset/limit pagination parameters)
- What happens when the database file is corrupted or unreadable? (Should provide clear error message)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to perform fuzzy k-mer queries with configurable mutation tolerance (0-5 mutations)
- **FR-002**: System MUST return all k-mers within the specified mutation distance from the query
- **FR-003**: For each match, system MUST provide the k-mer sequence, occurrence count, Hamming distance, and specific mutations
- **FR-004**: System MUST support batch fuzzy queries for multiple k-mers with parallel processing
- **FR-009**: System MUST allow users to configure maximum parallel worker threads for batch processing
- **FR-005**: System MUST validate query k-mers for correct DNA characters and proper length
- **FR-006**: System MUST support multiple output formats including JSON, table, and TSV
- **FR-007**: System MUST identify and highlight exact matches separately from fuzzy matches
- **FR-008**: System MUST provide clear error messages for invalid inputs or database issues

### Key Entities *(include if feature involves data)*

- **Fuzzy Query**: A request to find k-mers similar to a query sequence within a specified mutation tolerance
- **Fuzzy Match**: A k-mer from the database that matches the query within the tolerance, characterized by its sequence, count, distance, and mutation list
- **Mutation**: A specific base change from the query to a match, indicating position and nucleotide change
- **Batch Query**: A collection of multiple fuzzy queries processed together
- **Query Result**: Complete response containing the original query, all matches, and metadata

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Researchers can find all sequence variants within 1-2 mutations in under 2 seconds per query
- **SC-002**: Batch queries process 100 k-mers at least 5x faster than individual queries
- **SC-003**: System correctly identifies and reports 100% of exact matches when present in the database
- **SC-004**: Researchers can export query results in their preferred format without data loss
- **SC-005**: System handles invalid inputs gracefully with clear error messages 100% of the time
- **SC-006**: Memory usage scales linearly with batch size, allowing processing of 1000+ k-mers without system failure