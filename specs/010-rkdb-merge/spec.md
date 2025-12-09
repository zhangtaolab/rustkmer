# Feature Specification: RKDB Database Merge

**Feature Branch**: `010-rkdb-merge`
**Created**: 2025-12-08
**Status**: Draft
**Input**: User description: "实现merge 功能，这个是将多个 rkdb进行合并 sort 后新生成一个 rkdb, merge 的意思是如果两个或多个db 中，含有相同的 kmer统计数量相加合并，如果一个 db 有其他 db 没有，则新建一个kmer。请认真理解意图。 think harder"

## Clarifications

### Session 2025-12-08

- Q: u128编码支持的具体实现方式是什么？ → A: 只支持u128编码格式，所有输入数据库必须使用u128编码
- Q: 系统性测试的具体范围和级别是什么？ → A: 全面测试：单元测试、集成测试、属性测试、性能基准、回归测试、模糊测试
- Q: 如何处理参数不兼容的数据库合并？ → A: 系统必须拒绝合并参数不兼容的数据库（k-mer长度或canonical模式不一致），并提供清晰的错误信息

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Merge Multiple Datasets (Priority: P1)

As a genomic researcher, I want to merge k-mer databases from different samples or experiments so that I can create a comprehensive k-mer catalog for downstream analysis.

**Why this priority**: Merging is fundamental for comparative genomics and meta-analysis across multiple samples or experiments

**Independent Test**: Can be fully tested by creating two test databases with overlapping and unique k-mers, then verifying the merged database correctly combines counts

**Acceptance Scenarios**:

1. **Given** two RKDB databases with k-mer size 31, **When** I merge them using the merge command, **Then** the output database contains all unique k-mers from both inputs with correct summed counts
2. **Given** databases with overlapping k-mers, **When** merged, **Then** overlapping k-mer counts are summed in the output
3. **Given** databases with unique k-mers, **When** merged, **Then** all unique k-mers are preserved in the output

---

### User Story 2 - Validate Database Compatibility (Priority: P2)

As a user, I want clear error messages when attempting to merge incompatible databases so that I can understand and fix the issues.

**Why this priority**: Prevents data corruption and helps users understand merge requirements

**Independent Test**: Can be tested by attempting to merge databases with different k-mer sizes or canonical modes

**Acceptance Scenarios**:

1. **Given** databases with different k-mer sizes, **When** I attempt to merge, **Then** the system fails with a clear error about k-mer size mismatch
2. **Given** databases with different canonical modes, **When** I attempt to merge, **Then** the system fails with a clear error about canonical mode mismatch
3. **Given** compatible databases, **When** I merge with --verbose flag, **Then** I see compatibility check progress

---

### User Story 3 - Handle Large Database Merges (Priority: P3)

As a researcher working with large genomic datasets, I want the merge operation to be memory-efficient and provide progress feedback so that I can merge large databases without running out of memory.

**Why this priority**: Essential for processing real-world genomic datasets which can be very large

**Independent Test**: Can be tested with larger databases to verify memory usage stays reasonable and progress is reported

**Acceptance Scenarios**:

1. **Given** large databases (>1M k-mers each), **When** merging, **Then** memory usage is proportional to unique k-mers, not total input size
2. **Given** a merge operation, **When** using --verbose flag, **Then** progress information is displayed during loading and merging
3. **Given** a merge operation, **When** completed, **Then** summary statistics are shown including total k-mers and time elapsed

---

### Edge Cases

- What happens when merging empty databases?
- How does system handle duplicate database files in input?
- What happens when output file path is one of the input files?
- How are very large k-mer counts handled (overflow prevention)?
- What happens when disk space is insufficient for output?

## Testing Strategy *(mandatory)*

The merge functionality MUST undergo comprehensive testing to ensure reliability and correctness:

### Testing Levels

1. **Unit Tests**: Test individual functions and methods (merge_databases, kmer aggregation, validation logic)
2. **Integration Tests**: Test complete merge workflows with various database combinations
3. **Property-Based Tests**: Verify mathematical properties (associativity, commutativity, identity)
4. **Performance Benchmarks**: Validate performance targets (5 minutes for 10M k-mers)
5. **Regression Tests**: Ensure fixes don't break existing functionality
6. **Fuzz Tests**: Test robustness with random and malformed inputs

### Critical Test Scenarios

- Merge associativity: (A+B)+C = A+(B+C)
- Merge commutativity: A+B = B+A
- Overflow protection for k-mer counts
- Memory usage bounds (≤3x unique k-mers)
- Large dataset handling (>100M k-mers)
- Error conditions and recovery

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST merge at least 2 RKDB databases into a single output database
- **FR-002**: System MUST sum counts for identical k-mers present in multiple input databases
- **FR-003**: System MUST preserve unique k-mers from all input databases in the output
- **FR-004**: System MUST sort the merged k-mers in the output database
- **FR-005**: System MUST validate that all input databases have the same k-mer size
- **FR-006**: System MUST validate that all input databases have the same canonical mode setting
- **FR-007**: System MUST reject merge operations for databases with incompatible settings with clear error messages
- **FR-008**: System MUST support u128 k-mer encoding format exclusively (all input databases must use u128)
- **FR-009**: System MUST provide progress reporting when verbose mode is enabled
- **FR-010**: System MUST handle merging databases of different sizes efficiently

### Key Entities

- **RKDB Database**: Binary k-mer database format containing k-mers and their counts
- **K-mer**: A fixed-length nucleotide sequence (k characters) with associated count
- **Canonical Mode**: Flag indicating whether k-mers are stored in canonical form (lexicographically smaller of k-mer and its reverse complement)
- **Merge Operation**: Process of combining multiple databases by summing counts for identical k-mers

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can merge 2+ databases with identical k-mer settings in under 5 minutes for databases with up to 10M k-mers each
- **SC-002**: System correctly merges overlapping k-mers with 100% count accuracy
- **SC-003**: System prevents merging incompatible databases with clear error messages 100% of the time
- **SC-004**: Memory usage during merge is optimized to not exceed 3x the size of unique k-mers in output
- **SC-005**: Users can successfully merge databases with 100M+ total k-mers without system crashes
