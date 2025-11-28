# Feature Specification: RustKmer Count Implementation

**Feature Branch**: `001-jellyfish-rust-port`
**Created**: 2025-11-28
**Status**: Draft
**Input**: User description: "需要重构 jellyfish 的 rust 版本，重构的软件叫做rustkmer，首先需要实现的是 jellyfish count的 rust 版本 rustkmer count,请认真从 @reference/ 审阅jellyfish count源代码， 提取关键算法，然后编写rust版本的rustkmer count. 这只是第一部分的需求，后面还需要编写 dump query stats等，要预留接口等."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic K-mer Counting (Priority: P1)

As a bioinformatics researcher, I want to count k-mers in genomic sequence files so that I can analyze sequence composition and identify patterns in DNA data.

**Why this priority**: This is the core functionality of rustkmer and provides immediate value to users who need to perform basic k-mer counting operations on genomic data.

**Independent Test**: Can be fully tested by running rustkmer count on a small FASTA/FASTQ file and verifying the output contains correct k-mer counts compared to a known reference implementation.

**Acceptance Scenarios**:

1. **Given** a valid FASTA file with DNA sequences, **When** I run `rustkmer count -k 31 input.fa`, **Then** the system produces a binary count file with all 31-mers counted
2. **Given** multiple input sequence files, **When** I run `rustkmer count -k 21 file1.fa file2.fq`, **Then** the system combines k-mers from all files into a single count output
3. **Given** a file containing invalid DNA characters, **When** I run rustkmer count, **Then** the system skips invalid sequences and processes valid ones normally

---

### User Story 2 - Performance Optimization (Priority: P1)

As a researcher working with large genomic datasets, I want rustkmer to process files efficiently with configurable memory usage and multi-threading so that I can handle whole-genome analysis in reasonable time.

**Why this priority**: Performance is critical for bioinformatics tools where datasets can be terabytes in size. Users need tools that can leverage modern hardware effectively.

**Independent Test**: Can be fully tested by running rustkmer count on large files with different thread counts and memory settings, measuring throughput and memory usage against defined benchmarks.

**Acceptance Scenarios**:

1. **Given** a large genomic file and a multi-core system, **When** I run `rustkmer count -t 8 -s 10G input.fa`, **Then** the system utilizes 8 threads and completes processing significantly faster than single-threaded execution
2. **Given** memory constraints, **When** I specify hash table size with `-s`, **Then** the system respects the memory limit and provides clear feedback if insufficient memory is available
3. **Given** very large datasets, **When** processing completes, **Then** the system provides timing and throughput statistics for performance monitoring

---

### User Story 3 - Canonical K-mer Counting (Priority: P2)

As a genomics researcher, I want to count canonical k-mers (representing both strands equally) so that I can analyze sequences without double-counting complementary strands.

**Why this priority**: Canonical k-mer counting is standard practice in genomic analysis to avoid strand bias and reduce memory usage by storing each k-mer only once.

**Independent Test**: Can be fully tested by running rustkmer count with canonical mode on sequences containing reverse complements and verifying that both strands map to the same k-mer key.

**Acceptance Scenarios**:

1. **Given** DNA sequences containing reverse complement pairs, **When** I run `rustkmer count -C input.fa`, **Then** the system stores each k-mer only once using its canonical representation
2. **Given** a sequence "ATGC" and its reverse complement "GCAT", **When** counting with k=4 in canonical mode, **Then** both map to the same k-mer entry in the hash table
3. **Given** canonical mode enabled, **When** I check the output format, **Then** the system can optionally output canonical k-mer sequences or their original forms

---

### User Story 4 - Output Format Compatibility (Priority: P2)

As a researcher integrating tools into existing pipelines, I want rustkmer to support multiple output formats so that I can work with downstream analysis tools that expect specific formats.

**Why this priority**: Compatibility with existing bioinformatics pipelines is essential for tool adoption. Users need both binary and text output options.

**Independent Test**: Can be fully tested by generating output in different formats and verifying compatibility with standard tools and parsing libraries.

**Acceptance Scenarios**:

1. **Given** completed k-mer counting, **When** I run with `--text` flag, **Then** the system outputs human-readable k-mer sequences and counts in tab-separated format
2. **Given** default binary output, **When** I specify output file with `-o`, **Then** the system writes a compact binary format that can be read by other rustkmer commands
3. **Given** output requirements, **When** I compare file sizes, **Then** binary output is significantly smaller than text format while maintaining full precision

---

### Edge Cases

- What happens when k-mer length exceeds the shortest sequence in the input? **Skip any sequences shorter than k-mer length**
- How does system handle files with mixed FASTA and FASTQ formats?
- What occurs when hash table becomes full during processing? **System switches to disk-based overflow storage with performance warning**
- How are sequences with ambiguous bases (N) handled during k-mer extraction? **Skip any k-mers containing ambiguous bases (N)**

## Clarifications

### Session 2025-11-28

- Q: How should the system behave when hash table resizing is not possible due to memory constraints? → A: Switch to disk-based overflow storage with performance warning
- Q: 在k-mer提取过程中遇到含有模糊碱基(N)的序列时，应该采用什么处理策略？ → A: Skip any k-mers containing ambiguous bases (N)
- Q: 对于长时间运行的大型数据集处理，应该提供什么程度的进度反馈？ → A: Periodic progress updates (files processed, k-mers counted, runtime)
- Q: 当指定的k-mer长度大于输入序列中的某些序列时，应该如何处理这些短序列？ → A: Skip any sequences shorter than k-mer length
- Q: jellyfish和rustkmer的数据格式关系要求是什么？ → A: Data formats may differ, but statistical results must match jellyfish exactly (gold standard)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST count k-mers from DNA sequences in FASTA and FASTQ formats
- **FR-002**: System MUST support configurable k-mer lengths from 1 to at least 127 bases
- **FR-003**: System MUST implement canonical k-mer counting when specified (store lexicographically smaller of k-mer and reverse complement)
- **FR-004**: System MUST support multi-threaded processing with configurable thread count
- **FR-005**: System MUST provide configurable hash table size with automatic resizing when needed
- **FR-006**: System MUST support both binary and text output formats
- **FR-007**: System MUST implement efficient DNA base encoding using minimal memory storage
- **FR-008**: System MUST handle sequence filtering based on minimum and maximum count thresholds
- **FR-009**: System MUST provide progress reporting and performance statistics **with periodic updates showing files processed, k-mers counted, and runtime**
- **FR-010**: System MUST implement extensible architecture for future commands (dump, query, stats)

### Performance Requirements

- **PR-001**: System MUST process genomic data at rates comparable to jellyfish (measured in bases per second)
- **PR-002**: System MUST maintain memory efficiency with bit-packed k-mer storage
- **PR-003**: System MUST support streaming processing for files larger than available memory
- **PR-004**: System MUST implement lock-free or minimally-contentious concurrent hash table operations
- **PR-005**: System MUST provide predictable performance scaling with thread count up to CPU core limits

### Key Entities

- **K-mer**: Fixed-length DNA sequence fragment stored as packed bit array
- **Hash Counter**: Concurrent hash table storing k-mer keys and count values
- **Sequence Parser**: File reader supporting FASTA/FASTQ formats with sliding window extraction
- **Matrix Hash Function**: Binary matrix multiplication for efficient k-mer hashing
- **Output Formatter**: Support for binary and text output serialization
- **Configuration**: Command-line arguments and system settings controlling behavior

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: rustkmer count processes a 1GB genomic file within 10% of jellyfish's processing time on identical hardware
- **SC-002**: Memory usage remains under 2× the configured hash table size even during peak processing
- **SC-003**: Multi-threaded scaling achieves at least 70% efficiency when doubling thread count (up to physical core limits)
- **SC-004**: Output format compatibility enables 100% interoperability with existing bioinformatics pipelines
- **SC-005**: The system handles files up to 100GB without running out of memory when appropriate hash sizes are specified
- **SC-006**: K-mer counting accuracy matches reference implementations with 100% precision on test datasets
- **SC-007**: Statistical results exactly match jellyfish output when processed on identical input (jellyfish as gold standard)

### Extensibility Metrics

- **SC-008**: Core k-mer processing engine is designed as a library usable by future rustkmer commands
- **SC-009**: Plugin architecture allows easy addition of new output formats and counting strategies
- **SC-010**: Command-line interface framework supports consistent argument parsing across all future subcommands