# Feature Specification: Stats Command with K-mer Count Frequency Distribution

**Feature Branch**: `011-stats-frequency`
**Created**: December 9, 2025
**Status**: Draft
**Input**: User description: "目前 stats 还没有实现，需要完成这个工作，只需要支持u128即可，另外需要添加统计 kmer count 的频率, 从 1 到count 最大值都需要统计，如果缺失用 0 表示。"

## Clarifications

### Session 2025-12-09

- Q: 频率分布的显示格式（当最大计数很大时） → A: 始终显示完整分布，从1到最大计数
- Q: 输出格式的详细程度 → A: 添加基本统计指标：最小计数、最大计数、平均计数、中位数
- Q: 性能优化策略（大型数据库） → A: 使用流式算法，单次遍历计算所有统计
- Q: 空数据库的处理 → A: 返回错误，提示数据库为空无法生成统计
- Q: 输出格式选项 → A: 支持多种格式：--text、--json、--csv、--tsv

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Database Statistics Overview (Priority: P1)

As a bioinformatics researcher, I want to view comprehensive statistics about my k-mer database, including total k-mers, unique k-mers, and count distribution, so that I can understand the characteristics of my genomic dataset.

**Why this priority**: This is the core functionality of the stats command and provides immediate value to users for dataset analysis.

**Independent Test**: Can be fully tested by running the stats command on a database with known k-mer counts and verifying all statistics are correctly calculated and displayed.

**Acceptance Scenarios**:

1. **Given** a valid RKDB database file, **When** I run `rustkmer stats database.rkdb`, **Then** the system displays total k-mers, unique k-mers, and complete count frequency distribution
2. **Given** a database with k-mers having various counts, **When** I run stats, **Then** the frequency distribution shows counts from 1 to the maximum count present (with 0 for missing frequencies)

---

### User Story 2 - Frequency Distribution Analysis (Priority: P2)

As a data analyst, I want to see the complete frequency distribution of k-mer counts, including zero-filled gaps, so that I can analyze the coverage patterns and identify potential sequencing biases.

**Why this priority**: Frequency distribution is crucial for understanding dataset quality and coverage depth.

**Independent Test**: Can be tested by creating a database with specific count patterns and verifying the frequency distribution accurately represents all counts from 1 to max with proper zero-filling.

**Acceptance Scenarios**:

1. **Given** a database where k-mers have counts of 1, 3, and 5, **When** I run stats, **Then** the frequency distribution shows count=1: [frequency], count=2: 0, count=3: [frequency], count=4: 0, count=5: [frequency]
2. **Given** a large database, **When** I run stats, **Then** the frequency distribution efficiently handles the range without performance issues

---

### User Story 3 - Error Handling for Invalid Inputs (Priority: P3)

As a user, I want clear error messages when trying to get stats from invalid or incompatible files, so that I can quickly identify and fix input issues.

**Why this priority**: Good error handling improves user experience and reduces support overhead.

**Independent Test**: Can be tested by running stats on non-existent files, corrupted files, and files with incompatible formats.

**Acceptance Scenarios**:

1. **Given** a non-existent file path, **When** I run stats, **Then** I receive a clear "file not found" error message
2. **Given** a file that's not a valid RKDB database, **When** I run stats, **Then** I receive an appropriate error about invalid file format

---

### User Story 4 - Split Output Files (Priority: P2)

As a bioinformatics analyst, I want to save basic statistics and frequency distribution to separate files, so that I can integrate the stats output into different parts of my analysis workflow more efficiently.

**Why this priority**: Split output enables better workflow integration, allowing users to pipe basic statistics to one process and frequency distribution to another, improving productivity.

**Independent Test**: Can be tested by running stats with split output options and verifying both files are created with correct content and format.

**Acceptance Scenarios**:

1. **Given** a database with frequency distribution, **When** I run `rustkmer stats --split-output --freq-output freq.tsv database.rkdb`, **Then** basic statistics are saved to one file and frequency distribution to another
2. **Given** I specify CSV format with split output, **When** I run stats, **Then** both files are in CSV format with appropriate headers
3. **Given** I only specify --split-output without --freq-output, **When** I run stats, **Then** the system provides an error asking for the frequency output path

---

### Edge Cases

- Empty database: System returns error message indicating database is empty and cannot generate statistics
- Extremely large count values: System handles u128 values without overflow using streaming algorithm
- Large frequency distributions: System always displays complete distribution from 1 to max count regardless of size
- Non-existent files: Clear error message indicating file not found
- Invalid file formats: Clear error message indicating incompatible or corrupted RKDB format
- Split output without freq-output path: System provides clear error message asking for the missing path

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support stats command for RKDB databases using u128 encoding
- **FR-002**: System MUST calculate and display total number of k-mers in the database
- **FR-003**: System MUST calculate and display number of unique k-mers
- **FR-004**: System MUST generate complete frequency distribution from count 1 to maximum count present (always display full range regardless of size)
- **FR-005**: System MUST fill missing count frequencies with 0 (e.g., if no k-mers have count=2, display count=2: 0)
- **FR-006**: System MUST display basic statistical metrics: minimum count, maximum count, average count, and median
- **FR-007**: System MUST support multiple output formats: --text (default), --json, --csv, --tsv
- **FR-008**: System MUST use streaming algorithm to calculate statistics in a single pass for memory efficiency
- **FR-009**: System MUST return error message for empty databases (no k-mers present)
- **FR-010**: System MUST validate database format and compatibility before processing
- **FR-011**: System MUST handle u128 count values without overflow or precision loss
- **FR-012**: System MUST support --split-output flag to enable splitting basic statistics and frequency distribution into separate files
- **FR-013**: System MUST support --freq-output argument to specify output path for frequency distribution when split-output is enabled
- **FR-014**: System MUST require --freq-output when --split-output is specified and provide clear error if missing
- **FR-015**: System MUST maintain the same output format (text, json, csv, tsv) for both split files as specified by --format
- **FR-016**: System MUST include appropriate headers in frequency distribution files when using CSV/TSV formats

### Key Entities *(include if feature involves data)*

- **RKDB Database**: Binary k-mer database file containing k-mers and their counts using u128 encoding
- **K-mer**: A sequence of length k with an associated count (u128)
- **Frequency Distribution**: A mapping from count values (1 to max) to the number of k-mers having that count

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can run `rustkmer stats` on any valid u128 RKDB database and receive complete statistics in under 5 seconds
- **SC-002**: Stats command accurately reports total k-mers, unique k-mers, and frequency distribution for test databases with 100% accuracy
- **SC-003**: Frequency distribution correctly displays all counts from 1 to maximum count with proper zero-filling
- **SC-004**: Command handles databases with up to 1 billion unique k-mers without memory issues
- **SC-005**: Error messages are clear and actionable for all invalid input scenarios
- **SC-006**: Users can successfully split output into separate files with --split-output and --freq-output flags
- **SC-007**: Split output maintains format consistency across both files (same format as specified by --format)
- **SC-008**: Frequency distribution files include proper headers and formatting for CSV/TSV outputs