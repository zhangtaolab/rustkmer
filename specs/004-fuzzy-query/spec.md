# Feature Specification: Fuzzy Query with Wildcard Support

**Feature Branch**: `004-fuzzy-query`
**Created**: 2025-11-28
**Status**: Draft
**Input**: User description: "构建一个新的 query 程序，不要用之前的，新建一个。主要功能是模糊搜索，例如，如果数据库是5mer的，query AACTN , N 为 ATCG 中的任意一个，实际上是把 N 进行替换然后 query AACTA， AACTT, AACTC, AACTG；另外个例子 ，如果query ATNNT, 实际上 需要N都替换为 ATCG 的组合进行 query。如果数据库是5mer的，query 是 4mer 的，需要补齐 5mer 再 query， 补齐的方式为 4mer 前加一个 N和后面加一个 N，凑齐 5mer; 更高级的的，如果 kmer 数据库是 5mer，query ATACG 可以有1 个突变，需要 query NTACG, ANACG, ... ATACN。需要新建一个004分支进行。请认真研究制定计划，给出具体示例，然后用上面的方案测试13mer的模糊搜索。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Wildcard Query Processing (Priority: P1)

User needs to perform fuzzy k-mer queries with wildcard support where 'N' represents any nucleotide (A, T, C, G). Given a database with k-mers of size K, the system should handle queries containing 'N' characters by expanding them to all possible combinations and querying each variant.

**Why this priority**: This is the core functionality that enables flexible sequence searching when parts of the sequence are unknown or variable, which is essential for real biological applications where sequencing errors or variations are common.

**Independent Test**: Can be fully tested by creating a 5-mer database, querying with patterns like "AACTN" and verifying that all 4 variants (AACTA, AACTT, AACTC, AACTG) are correctly queried and results are properly aggregated.

**Acceptance Scenarios**:

1. **Given** a 5-mer database with entries for AACTA, AACTT, AACTC, AACTG, **When** user queries "AACTN", **Then** the system returns the sum of counts for all 4 variants
2. **Given** a 13-mer database, **When** user queries "ATGCGATGCTAGCN", **Then** the system expands the single 'N' into 4 variants and queries each
3. **Given** a query with multiple 'N's like "ATNNT", **When** processed, **Then** the system generates all 4^N = 16 combinations (ATAAT, ATACT, etc.) and queries each

---

### User Story 2 - Length Normalization (Priority: P1)

User needs to query the database with sequences that don't match the database's k-mer size. The system should automatically normalize query lengths by padding with 'N' characters to match the database k-mer size.

**Why this priority**: Users often have sequences of different lengths and need the system to handle the normalization automatically rather than requiring manual padding.

**Independent Test**: Can be fully tested by creating a 5-mer database and querying with a 4-mer sequence, verifying both front and back padding are tried.

**Acceptance Scenarios**:

1. **Given** a 5-mer database, **When** user queries a 4-mer "ATAC", **Then** the system queries both "NATAC" and "ATACN"
2. **Given** a 13-mer database, **When** user queries an 11-mer, **Then** the system generates queries with 'N' padding at both ends
3. **Given** a query longer than the database k-mer size, **When** processed, **Then** the system extracts all possible k-mers from the query and searches each

---

### User Story 3 - Mutation Tolerance (Priority: P2)

User needs to find k-mers with a small number of mutations (substitutions) compared to their query. The system should support finding variants within a specified Hamming distance.

**Why this priority**: This enables finding related sequences despite sequencing errors or biological mutations, which is crucial for practical applications in genomics research.

**Independent Test**: Can be fully tested by creating a 5-mer database with known entries, querying with a sequence that has 1 substitution, and verifying that nearby variants are found.

**Acceptance Scenarios**:

1. **Given** a 5-mer database containing "ATACG", **When** user queries "ATACG" with 1 mutation tolerance, **Then** the system finds all k-mers with Hamming distance ≤ 1 (NTACG, ANACG, ATNCG, ATANG, ATACN)
2. **Given** a 13-mer database, **When** user queries with 2 mutation tolerance, **Then** the system returns all k-mers with ≤ 2 substitutions
3. **Given** no exact matches or mutation variants, **When** querying, **Then** the system returns count 0 without error

---

### User Story 4 - Performance Optimization for Large-scale Queries (Priority: P2)

User needs to perform fuzzy queries efficiently on large databases (millions of k-mers) without prohibitive computational overhead.

**Why this priority**: Wildcard expansion can lead to combinatorial explosion (4^N combinations), so optimization is essential for practical utility.

**Independent Test**: Can be fully tested by measuring query performance with different numbers of wildcards and mutation tolerances on a 13-mer database.

**Acceptance Scenarios**:

1. **Given** a 13-mer database with >1M entries, **When** querying with 2 wildcards (16 combinations), **Then** query completes within reasonable time (<10 seconds)
2. **Given** performance monitoring, **When** processing fuzzy queries, **Then** system reports number of combinations generated and query time
3. **Given** queries that would generate >1000 combinations, **When** processed, **Then** system either processes efficiently or warns user about complexity

---

## Edge Cases

- **Multiple consecutive wildcards**: Query "ATNNG" generates 16 combinations - system must handle efficiently without duplicates
- **All wildcards**: Query "NNNNN" generates 4^5 = 1024 combinations - need performance safeguards
- **Empty database**: Handle gracefully without crashes
- **Invalid characters**: Non-ATCGN characters should produce clear error messages
- **Too many mutations**: Requesting more than k/2 mutations should either warn or limit automatically
- **Very long queries**: Queries much longer than database k-mer size should be handled efficiently
- **Memory limits**: Large wildcard expansions should not cause memory exhaustion

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expand wildcard characters ('N') into all four nucleotides (A, T, C, G)
- **FR-002**: System MUST normalize query lengths by padding with 'N' characters to match database k-mer size
- **FR-003**: System MUST support mutation tolerance using Hamming distance for finding near-matches
- **FR-004**: System MUST aggregate results from all expanded queries and return combined counts
- **FR-005**: System MUST provide performance metrics for fuzzy query operations
- **FR-006**: System MUST handle edge cases like empty databases and invalid characters gracefully
- **FR-007**: System MUST support both single queries and batch query files with fuzzy operations
- **FR-008**: System MUST validate input parameters and provide clear error messages
- **FR-009**: System MUST implement performance safeguards for combinatorial explosion scenarios
- **FR-010**: System MUST maintain compatibility with existing RKDB database format

### Key Entities *(include if feature involves data)*

- **FuzzyQuery**: Represents a query with wildcards and mutation tolerance parameters
  - query_string: The input sequence (may contain 'N' wildcards)
  - kmer_size: Target k-mer size for the database
  - mutation_tolerance: Maximum allowed Hamming distance (default: 0)

- **QueryExpansion**: Generated set of concrete k-mers to be queried
  - concrete_kmers: List of specific sequences without wildcards
  - expansion_method: How the k-mers were generated (wildcard, mutation, padding)
  - combination_count: Number of total combinations generated

- **FuzzyResult**: Aggregated result from fuzzy query operations
  - total_count: Sum of counts from all matching k-mers
  - individual_matches: List of k-mers that matched with their counts
  - query_metadata: Information about expansion method and performance

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System can process queries with up to 3 wildcards (64 combinations) on a 13-mer database in under 5 seconds
- **SC-002**: System achieves 100% accuracy in wildcard expansion compared to manual enumeration
- **SC-003**: System correctly handles length normalization for queries within ±3 k-mers of database size
- **SC-004**: System maintains query performance within acceptable bounds for mutation tolerance ≤ 2
- **SC-005**: System processes batch queries with fuzzy patterns at 100+ queries/second on average
- **SC-006**: System provides clear error messages for invalid inputs in 100% of test cases
- **SC-007**: System demonstrates successful 13-mer fuzzy querying with real genomic data as specified by user

### Performance Benchmarks

- **Single wildcard query**: < 0.1 seconds for typical databases
- **Double wildcard query**: < 1 second for typical databases
- **Triple wildcard query**: < 5 seconds for typical databases
- **Mutation tolerance queries**: < 0.5 seconds per mutation tolerance level
- **Batch fuzzy queries**: > 50 queries/second throughput

### Testing Scenarios for 13-mer Validation

As specifically requested by user, the system will be tested with:

1. **Wildcard examples for 13-mers**:
   - "ATGCGATGCTAGCN" → expands to 4 variants
   - "ATGCGATGCTNGCN" → expands to 16 variants
   - "ATGCGATGCNNNGC" → expands to 64 variants

2. **Length normalization examples**:
   - 12-mer query → padded to 13-mers with 'N' at both ends
   - 14-mer query → extract all possible 13-mers

3. **Mutation tolerance examples**:
   - "ATGCGATGCTAGCG" with 1 mutation → all k-mers with ≤1 substitution
   - Real OSA1 genomic data testing with 13-mer database

This specification provides the foundation for implementing a comprehensive fuzzy query system that addresses all user requirements while maintaining performance and usability.