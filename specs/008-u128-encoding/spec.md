# Feature Specification: u128-encoding-upgrade

**Feature Branch**: `[008-u128-encoding]`
**Created**: 2025-12-08
**Status**: Draft
**Input**: User description: " 目前 u64编码只能支持  kmer<=32, 现在需要支持kmer<=64,需要将 u64编码替换为u128编码，请认真研究升级方案,将目前rustkmer的所有程序升级支持 kmer<=64, 如果有问题可以用中文回答。 创建 008- 分支进行"

## Clarifications

### Session 2025-12-08

- Q: 对于 k=64 的操作，除了不超过 k=32 内存使用量的 2 倍外，是否需要设定一个绝对的内存上限？ → A: 让用户通过命令行参数自定义内存限制
- Q: 系统应该支持多少个并发查询操作？ → A: 不设具体限制，但提供并发控制机制
- Q: 对于包含多个模糊碱基（N）的大 k-mer（k>32），应该如何处理？ → A: 跳过包含模糊碱基的 k-mer，记录统计信息
- Q: 新版本是否需要考虑与 u64 数据的兼容性？ → A: 不需要考虑 u64 数据兼容，只支持 u128 格式
- Q: u128 版本的统计结果是否需要与 u64 版本保持一致？ → A: 是的，统计结果必须保持一致
- Q: 是否需要限制内存增长？ → A: 先不限制内存增长，由用户通过命令行参数手动限制
- Q: 是否需要考虑数据迁移工具？ → A: 不需要，新版本仅支持 u128 格式
- Q: u128 的 2 位编码实现规范？ → A: 使用标准 2 位/碱基编码：A=00, C=01, G=10, T=11
- Q: 从 u64 到 u128 的性能损失指标？ → A: 编码/解码 ≤10% 慢，查询 ≤5% 慢，数据库大小增加 33%

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Large K-mer Database Creation (Priority: P1)

Genomics researchers working with long DNA sequences need to create k-mer databases with k-mer sizes between 33 and 64 to accurately analyze large genomic regions, viral genomes, and complex genetic variations that cannot be captured with smaller k-mers.

**Why this priority**: This is the core requirement that enables support for larger k-mers, which is essential for modern genomics applications dealing with longer sequences and improved specificity.

**Independent Test**: Can be fully tested by creating databases with k=33, k=48, and k=64 using test FASTA files and verifying that all k-mers are correctly stored and retrievable.

**Acceptance Scenarios**:

1. **Given** a FASTA file with sequences longer than 64 bases, **When** running rustkmer count with k=33, **Then** the database is successfully created without errors
2. **Given** a FASTA file with sequences of various lengths, **When** running rustkmer count with k=64, **Then** all valid k-mers are processed and stored
3. **Given** sequences containing ambiguous bases (N), **When** counting k-mers with k>32, **Then** ambiguous k-mers are properly handled according to existing rules

---

### User Story 2 - Large K-mer Database Querying (Priority: P1)

Researchers need to query existing large k-mer databases (k=33 to k=64) to find specific long sequences, check for the presence of genomic markers, and perform comparative analyses across different organisms or samples.

**Why this priority**: Database querying is the primary operation for k-mer analysis; without efficient querying, the databases are useless for practical applications.

**Independent Test**: Can be fully tested by creating test databases with known k-mers (k=33, k=48, k=64) and verifying that exact matches return correct counts while non-existent k-mers return zero.

**Acceptance Scenarios**:

1. **Given** a database with k=48, **When** querying for known k-mers, **Then** correct counts are returned
2. **Given** a database with k=64, **When** querying for k-mers not in the database, **Then** zero or appropriate "not found" response is returned
3. **Given** multiple databases with different k-sizes, **When** performing batch queries, **Then** each database returns correct results independently

---

### User Story 3 - Statistical Consistency (Priority: P1)

Researchers require that k-mer statistics (counts, distributions, totals) produced by the new u128 implementation must exactly match those produced by the current u64 implementation for comparable datasets, ensuring data analysis consistency and research reproducibility.

**Why this priority**: Essential for scientific validity - researchers must trust that results are consistent regardless of the underlying encoding implementation.

**Independent Test**: Can be fully tested by processing identical datasets with both u64 and u128 implementations and comparing all statistical outputs.

**Acceptance Scenarios**:

1. **Given** identical FASTA files, **When** processing with both u64 and u128 implementations, **Then** total k-mer counts are identical
2. **Given** test datasets with known k-mer distributions, **When** comparing statistics, **Then** all metrics match exactly
3. **Given** sequences with ambiguous bases, **When** processing with both implementations, **Then** the same k-mers are skipped with identical statistics

---

### User Story 4 - Performance Maintenance (Priority: P2)

The performance of k-mer operations for all supported k-mer sizes (1-64) must be optimized for the u128 encoding, ensuring efficient processing for both small and large k-mers.

**Why this priority**: Performance is crucial for genomics applications where researchers process millions of k-mers; efficient implementation enables larger scale analyses.

**Independent Test**: Can be tested by benchmarking the u128 implementation using representative datasets and measuring operation times.

**Acceptance Scenarios**:

1. **Given** test datasets with various k-sizes, **When** measuring performance, **Then** operations complete within acceptable time limits
2. **Given** large datasets with k=64, **When** performing database operations, **Then** memory usage remains within configured limits
3. **Given** concurrent operations, **When** multiple processes access databases, **Then** system remains stable and responsive

---

### Edge Cases

- System validates k-mer length and returns clear error for invalid values (<1 or >64)
- Memory limits are enforced via user-configurable parameters (FR-011)
- K-mers with ambiguous bases (N) are skipped with statistics reporting (FR-013)
- Database format ensures consistency and prevents data corruption
- Statistical outputs match u64 implementation exactly for comparable inputs

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support k-mer sizes from 1 to 64
- **FR-003**: System MUST handle u128 encoding for all k-mer operations (count, query, dump, stats)
- **FR-004**: System MUST preserve existing CLI command interfaces and options
- **FR-005**: System MUST maintain canonical k-mer representation (lexicographically smaller of reverse complement)
- **FR-006**: Python API MUST support u128 k-mers with consistent interface
- **FR-014**: Database format MUST support u128 k-mers efficiently
- **FR-008**: System MUST handle memory efficiently when processing large k-mers
- **FR-011**: System MUST allow users to configure memory limits via command-line parameters
- **FR-012**: System MUST provide concurrency control mechanisms for database access
- **FR-013**: System MUST skip k-mers with ambiguous bases and report statistics
- **FR-015**: System MUST produce statistics identical to u64 implementation for comparable inputs
- **FR-016**: System MUST use standard 2-bit encoding: A=00, C=01, G=10, T=11 for u128 k-mers
- **FR-017**: Encoding/decoding operations MUST be ≤10% slower than u64 implementation
- **FR-018**: Query operations MUST be ≤5% slower than u64 implementation
- **FR-019**: Database size MUST increase by exactly 33% (from 12 to 16 bytes per entry)
- **FR-009**: Error messages MUST be clear and informative for invalid k-mer sizes
- **FR-010**: Performance MUST remain acceptable for all k-mer sizes (1-64)

### Key Entities *(include if feature involves data)*

- **K-mer**: A DNA sequence of fixed length (1-64) encoded in u128 format
- **Database**: Binary storage system optimized for u128 k-mers and their counts (16 bytes per entry)
- **Encoding**: Process of converting DNA sequences to u128 using 2-bit scheme (A=00, C=01, G=10, T=11)
- **Canonical Representation**: Lexicographically smaller of forward and reverse complement
- **Query Operation**: Process of searching for specific k-mers in u128 databases using binary search
- **Statistics**: K-mer count distributions and totals that must match u64 implementation exactly
- **Memory Layout**: 16 bytes per database entry (u128 kmer + u32 count), no memory growth limits imposed

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: K-mer databases can be successfully created with k-sizes up to 64 without errors
- **SC-002**: Query operations on k=64 databases return correct results in under 105ms per query (≤5% slower than u64)
- **SC-004**: Memory usage is controlled by user-configurable limits only
- **SC-008**: System reports statistics for skipped k-mers with ambiguous bases
- **SC-009**: Statistical outputs exactly match u64 implementation for comparable datasets
- **SC-010**: CLI and Python API maintain consistent interfaces with existing functionality
- **SC-012**: Encoding/decoding operations complete within ≤110% of u64 implementation time
- **SC-013**: Database files are exactly 133% the size of equivalent u64 databases (16/12 bytes)
- **SC-007**: System can process datasets with 10M+ k-mers of size 64 without crashing
- **SC-011**: All supported k-mer sizes (1-64) achieve performance within specified limits
