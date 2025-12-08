# Feature Specification: Support k-mers up to 64 bases with u128 encoding

**Feature Branch**: `001-u128-encoding`
**Created**: 2025-12-08
**Status**: Draft

## Clarifications

### Session 2025-12-08

- Q: 数据库格式兼容性策略 → A: 破坏兼容性 - 强制用户重新创建所有数据库使用新格式
**Input**: User description: " 目前 u64编码只能支持  kmer<=32, 现在需要支持kmer<=64,需要将 u64编码替换为u128编码，请认真研究升级方案,将目前rustkmer的所有程序升级支持 kmer<=64, 如果有问题可以用中文回答。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Process long DNA sequences (Priority: P1)

Genomics researchers need to analyze DNA sequences containing k-mers longer than 32 bases, which are common in genome assembly, metagenomics, and structural variant detection applications.

**Why this priority**: This is the core requirement - users cannot work with sequences longer than 32 bases with the current implementation, limiting the tool's applicability to modern genomics workflows.

**Independent Test**: Can be fully tested by creating a database from a synthetic DNA sequence with 40-base k-mers and verifying that all k-mers are correctly counted and can be queried.

**Acceptance Scenarios**:

1. **Given** a DNA FASTA file with sequences containing 40-base k-mers, **When** running `rustkmer count -k 40`, **Then** the command completes successfully and creates a valid database
2. **Given** a database created with 40-base k-mers, **When** querying any of those k-mers, **Then** the correct count is returned
3. **Given** a k-mer size of 50, **When** encoding the k-mer, **Then** it fits within the u128 encoding scheme without overflow

---

### User Story 2 - Database format migration (Priority: P1)

Users with existing databases created with u64 encoding must migrate to the new u128 format, requiring a clear migration path and tools.

**Why this priority**: Users need guidance and tools to transition their existing databases to the new format to continue using rustkmer.

**Independent Test**: Can be tested by attempting to open an old database and receiving a clear error message with migration instructions.

**Acceptance Scenarios**:

1. **Given** a database created with the current u64 format, **When** opening it with the new version, **Then** it fails with a clear error message indicating incompatible format
2. **Given** an error about incompatible format, **When** user checks documentation, **Then** migration instructions are clearly provided
3. **Given** the new version, **When** creating databases, **Then** all databases use the new u128 format regardless of k-mer size

---

### User Story 3 - Support mixed k-mer size workflows (Priority: P2)

Researchers work with multiple k-mer sizes in the same project and need seamless switching between different sizes without performance degradation.

**Why this priority**: Many genomic analyses require comparing results across different k-mer sizes to understand sequence composition and detect features of various lengths.

**Independent Test**: Can be tested by creating databases with different k-mer sizes (20, 35, 50, 64) and verifying consistent performance and accuracy across all sizes.

**Acceptance Scenarios**:

1. **Given** databases created with k=20 and k=50, **When** querying both, **Then** performance is proportional to database size, not k-mer length
2. **Given** a k-mer size of 64, **When** performing reverse complement operations, **Then** the operation completes correctly and efficiently
3. **Given** any k-mer size between 1 and 64, **When** encoding to u128, **Then** the encoding is correct and reversible

---

### Edge Cases

- What happens when attempting to create a database with k>64?
- How does system handle memory limits when working with maximum k-mer size?
- What is the behavior when querying a database with the wrong k-mer size?
- How are invalid DNA characters handled in longer sequences?
- What happens during database corruption or partial reads with larger entries?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support k-mer sizes from 1 to 64 bases using u128 encoding
- **FR-002**: System MUST maintain 2-bit per base encoding scheme (A=00, C=01, G=10, T=11)
- **FR-003**: System MUST provide correct encoding/decoding for all k-mer sizes up to 64 bases
- **FR-004**: System MUST compute reverse complements correctly for k-mers up to 64 bases
- **FR-005**: System MUST determine canonical k-mers (lexicographically smaller of forward/reverse) for all sizes
- **FR-006**: System MUST store k-mers in database using 16-byte u128 format
- **FR-007**: System MUST NOT maintain backward compatibility with existing u64 databases; users must recreate databases with new format
- **FR-008**: System MUST provide clear error messages when k>64 is requested
- **FR-009**: System MUST support all existing CLI commands with extended k-mer sizes
- **FR-010**: System MUST update Python bindings to handle u128 k-mer values
- **FR-011**: System MUST maintain thread safety for all k-mer operations
- **FR-012**: System MUST preserve query accuracy and performance characteristics

### Key Entities *(include if feature involves data)*

- **K-mer**: DNA sequence fragment of length k, encoded as 128-bit integer using 2 bits per base
- **Database Entry**: Struct containing a 16-byte u128 k-mer and 4-byte count (total 20 bytes)
- **KmerCounter**: Thread-safe hash table storing HashMap<u128, u32> for k-mer counting
- **Canonical K-mer**: Representative k-mer that is lexicographically smaller of forward/reverse pair
- **Database Format**: Binary .rkdb format with updated entry size for u128 support

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can successfully create databases with k-mer sizes up to 64 bases
- **SC-002**: Database creation time scales linearly with input size, not k-mer length
- **SC-003**: Query response time remains under 10ms for any k-mer size up to 64 bases
- **SC-004**: Memory usage increases by no more than 120% compared to u64 implementation
- **SC-005**: Clear error messages provided when attempting to open old database format
- **SC-006**: All 128 possible k-mer sizes (1-64) pass correctness validation
- **SC-007**: No regression in performance for k≤32 compared to current implementation