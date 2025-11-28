# Feature Specification: Parallel Query Processing

**Feature Branch**: `003-parallel-query`
**Created**: 2025-11-28
**Status**: Draft
**Input**: User description: "能不能为query 设计一个多线程版本，就是一次可以 query 多条 kmer？多线程和单线程比如果性能没有明显提升也请明确的告诉我。请新建一个003分支来处理这个问题。"

## User Scenarios & Testing

### User Story 1 - Batch K-mer Query with Performance Analysis (Priority: P1)

Researchers and bioinformaticians need to query large numbers of k-mers from genomic databases efficiently. They currently can query multiple k-mers sequentially but want to know if multi-threading provides significant performance benefits for their batch query workflows.

**Why this priority**: This directly addresses the user's explicit question about multi-threading performance and is the core requirement that needs validation.

**Independent Test**: Can be fully tested by implementing multi-threaded batch queries and measuring performance against single-threaded baseline, providing clear performance analysis results.

**Acceptance Scenarios**:

1. **Given** a rustkmer database with multiple k-mers to query, **When** user executes a batch query with 1000+ k-mers using multi-threading, **Then** system processes all queries and provides clear performance metrics comparing multi-thread vs single-thread execution
2. **Given** performance analysis results, **When** multi-threading provides less than 20% performance improvement, **Then** system clearly reports that multi-threading offers minimal benefits for the query batch size
3. **Given** performance analysis results, **When** multi-threading provides significant (>20%) performance improvement, **Then** system reports the exact performance gain and recommendations for optimal usage

---

### User Story 2 - Scalable Query Performance for Different Batch Sizes (Priority: P2)

Users need to understand at what batch sizes multi-threading becomes beneficial, as small batches may have more overhead than benefit from parallelization.

**Why this priority**: Helps users make informed decisions about when to use multi-threading based on their specific query patterns and batch sizes.

**Independent Test**: Can be tested by running performance benchmarks across different batch sizes (10, 100, 1000, 10000 k-mers) and identifying the crossover point where multi-threading becomes beneficial.

**Acceptance Scenarios**:

1. **Given** batch queries of different sizes, **When** performance testing is conducted, **Then** system provides performance data showing optimal batch sizes for multi-threading
2. **Given** small batch queries (<100 k-mers), **When** multi-threading overhead exceeds benefits, **Then** system recommends single-threaded processing for these batch sizes
3. **Given** large batch queries (>1000 k-mers), **When** multi-threading provides clear benefits, **Then** system recommends optimal thread count based on available CPU cores

---

### User Story 3 - Thread Safety and Resource Management (Priority: P3)

Users need assurance that multi-threaded queries maintain data integrity and don't cause resource contention or corruption, especially when multiple query processes run simultaneously.

**Why this priority**: Ensures the multi-threaded implementation is robust and safe for production use in high-throughput environments.

**Independent Test**: Can be tested by running concurrent multi-threaded query processes and verifying data consistency and proper resource cleanup.

**Acceptance Scenarios**:

1. **Given** multiple concurrent multi-threaded query processes, **When** accessing the same database, **Then** all processes complete successfully without data corruption or race conditions
2. **Given** a multi-threaded query process, **When** interrupted or terminated, **Then** system cleans up all threads and resources properly without leaving zombie processes
3. **Given** system resource limits, **When** multi-threaded queries would exceed available memory or CPU, **Then** system gracefully handles resource constraints and provides clear error messages

---

### Edge Cases

- What happens when the number of k-mers in a batch is smaller than the number of available threads?
- How does system handle query failures in individual threads without affecting the entire batch?
- What occurs when memory is insufficient for the requested number of threads?
- How does system handle database corruption or I/O errors during multi-threaded processing?
- What happens when users request more threads than the system can support?

## Clarifications

### Session 2025-11-28

- Q: 多线程查询的具体实现方式 → A: 基于Rayon的并行批处理，将k-mer列表分块给不同线程处理，每个线程独立访问数据库文件进行二进制搜索
- Q: 性能分析的输出格式和详细程度 → A: 可配置的详细程度：用户可通过--verbose/--quiet参数控制输出详细程度，默认显示中等详细程度的信息
- Q: 线程数量的自动确定策略 → A: 基于CPU核心数和批次大小的智能算法：小批次(<100)使用单线程，中等批次(100-1000)使用CPU核心数的一半，大批次(>1000)使用所有CPU核心
- Q: 批处理查询的输入格式 → A: 混合格式：优先从标准输入读取，也支持命令行参数，同时提供--file选项指定输入文件
- Q: 错误处理和结果输出的行为 → A: 部分成功模式：有效k-mer返回结果，无效k-mer输出错误信息但继续处理其他k-mer，最后统计成功和失败的数量
- Q: 新的多线程查询命令名称 → A: queryx - 简洁的名称，字母"x"代表并行/扩展，现代且易于记忆

## Implementation Architecture

### Multi-threading Strategy
- **Command Name**: `queryx` - A new dedicated command for parallel batch querying
- **Implementation Approach**: Non-destructive development - create separate command without modifying existing `query` functionality
- **Implementation**: Rayon-based parallel batch processing with k-mer list chunking
- **Database Access**: Each thread independently accesses database file for binary search
- **Thread Safety**: Database files support concurrent read operations without additional synchronization
- **Future Integration**: After thorough testing and validation, consider merging with existing query command

### Performance Analysis Framework
- **Output Modes**: Configurable verbosity via --verbose/--quiet flags
- **Metrics Collection**: Total query time, single-threaded comparison time, speedup ratio, batch-specific usage recommendations
- **Default Behavior**: Medium detail output with actionable insights

### Thread Optimization Algorithm
- **Small batches (<100 k-mers)**: Single-threaded execution to avoid overhead
- **Medium batches (100-1000 k-mers)**: Use 50% of available CPU cores
- **Large batches (>1000 k-mers)**: Use all available CPU cores
- **Smart detection**: Automatic crossover point identification around 50-200 k-mers

### Input Processing
- **Primary input**: Standard input (one k-mer per line) for pipeline compatibility
- **Secondary input**: Command line arguments for small batch queries
- **File input**: --file option for direct file specification
- **Compatibility**: Maintains compatibility with existing jellyfish query workflows

### Error Management
- **Partial success processing**: Continue batch execution on individual k-mer failures
- **Error reporting**: Output error messages for invalid k-mers while processing valid ones
- **Final statistics**: Summary of successful vs failed query counts
- **Graceful degradation**: System recommendations when multi-threading provides minimal benefits

## Requirements

### Functional Requirements

- **FR-001**: System MUST support multi-threaded batch k-mer queries that can process multiple k-mers simultaneously
- **FR-002**: System MUST provide clear performance comparisons between multi-threaded and single-threaded query execution
- **FR-003**: System MUST automatically determine optimal thread count based on available CPU cores and query batch size
- **FR-004**: System MUST maintain data integrity and consistency across all concurrent query operations
- **FR-005**: System MUST provide performance metrics including throughput, latency, and resource utilization for each query batch
- **FR-006**: Users MUST be able to specify maximum thread count or let system auto-determine optimal settings
- **FR-007**: System MUST handle thread pool management efficiently, avoiding thread creation overhead for small batches
- **FR-008**: System MUST report when multi-threading provides minimal or no performance benefit
- **FR-009**: System MUST gracefully degrade to single-threaded processing when multi-threading conditions are not favorable
- **FR-010**: System MUST ensure thread-safe access to database files and shared resources

### Key Entities

- **Query Batch**: A collection of k-mers to be processed together in a single operation
- **Thread Pool**: Managed collection of worker threads for parallel query processing
- **Performance Metrics**: Data collected during query execution including timing, throughput, and resource usage
- **Database Access Handler**: Thread-safe interface for concurrent database operations

## Success Criteria

### Measurable Outcomes

- **SC-001**: Multi-threaded queries demonstrate measurable performance improvement over single-threaded queries for batch sizes >100 k-mers
- **SC-002**: System provides clear performance analysis showing exact speedup ratios (e.g., "3.2x faster with 8 threads for 1000 k-mers")
- **SC-003**: System accurately identifies and reports when multi-threading provides <10% performance benefit
- **SC-004**: Thread pool management overhead is <5% of total query time for optimal batch sizes
- **SC-005**: System maintains 100% data consistency and accuracy across all multi-threaded query operations
- **SC-006**: Memory usage scales linearly with thread count, no memory leaks detected in prolonged multi-threaded operations
- **SC-007**: System automatically selects optimal thread count within 90% of theoretical maximum performance
- **SC-008**: Users can complete batch queries of 10,000 k-mers in under 30 seconds with appropriate thread configuration
- **SC-009**: System provides actionable performance recommendations based on query batch size and system resources
- **SC-010**: Multi-threaded implementation maintains compatibility with existing single-threaded query functionality

### Performance Benchmarks

- **PB-001**: Achieve >2x speedup for batches >1000 k-mers on systems with 8+ CPU cores
- **PB-002**: Maintain <1ms per k-mer query overhead in multi-threaded mode for large batches
- **PB-003**: Demonstrate linear scalability up to CPU core count for batch sizes >10,000 k-mers
- **PB-004**: Show clear performance crossover point where multi-threading becomes beneficial (typically 50-200 k-mers)

### User Experience

- **UX-001**: Users receive clear, actionable performance analysis for their specific query patterns
- **UX-002**: System provides automatic optimization recommendations without requiring deep technical knowledge
- **UX-003**: Performance analysis results are presented in an easy-to-understand format with specific recommendations
