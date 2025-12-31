# Research Summary: Python Fuzzy Query API

**Date**: 2025-12-14
**Feature**: Python fuzzy query API implementation

## Technical Decisions

### Python Binding Architecture
**Decision**: Use subprocess-based approach calling existing CLI fuzzy-query command
**Rationale**:
- Maintains consistency with existing Python query API pattern
- Avoids PyO3 complexity for this feature
- Leverages existing, tested Rust implementation
- Allows for independent evolution of CLI and Python APIs

**Alternatives considered**:
- Direct PyO3 bindings to Rust fuzzy query engine: More complex, would require significant Rust code changes
- REST API wrapper: Overkill for local database operations

### Data Structure Design
**Decision**: Create dedicated fuzzy query result classes (FuzzyQueryResult, FuzzyMatchResult, FuzzyBatchResult)
**Rationale**:
- Clear separation from exact query results
- Supports rich metadata (distance, mutations)
- Enables future extensions (mutation analysis, pattern detection)
- Follows object-oriented design patterns

**Alternatives considered**:
- Extend existing QueryResult class: Would complicate the exact query API
- Use generic dictionaries: Less type-safe, poor developer experience

### Batch Processing Strategy
**Decision**: Python-level parallelism using ThreadPoolExecutor with user-configurable maximum workers
**Rationale**:
- Simpler implementation than Rust-level parallelism
- Leverages existing CLI process isolation
- Python's GIL not an issue for I/O-bound subprocess calls
- Consistent with existing batch query implementation
- Allows user control over resource usage

**Alternatives considered**:
- Rust-level parallel processing: Would require CLI changes, more complex
- Sequential processing: Would not meet performance requirements

### Output Format Support
**Decision**: Support JSON, table, and TSV formats
**Rationale**:
- JSON for programmatic access and web integration
- Table for human-readable output and analysis
- TSV for spreadsheet import and pipeline integration
- Matches existing query API format support

### Performance and Memory Management
**Decision**: Implement result pagination and memory limits
**Rationale**:
- Default limit of 10,000 matches prevents memory overflow
- Offset/limit pagination allows accessing additional results as needed
- Memory usage target: <1GB for 1000 k-mers with 2 mutations
- Linear scaling with batch size

### Error Handling Strategy
**Decision**: Partial failure tolerance for batch queries
**Rationale**:
- Large batches commonly contain occasional invalid entries
- Continue processing valid k-mers maximizes efficiency
- Return comprehensive results with error list for invalid inputs
- Matches user story requirement to "process valid k-mers"

## Implementation Considerations

### Performance Optimizations
- Lazy loading of mutation details to minimize memory usage
- Result pagination for large result sets
- Configurable batch sizes to balance memory and speed
- Adaptive parallelism based on system capabilities

### Error Handling Strategy
- Validate k-mers before subprocess calls
- Clear error messages for invalid inputs
- Graceful handling of CLI command failures
- Timeout management for long-running queries

### Testing Strategy
- Unit tests for all Python classes
- Integration tests with real databases
- Performance benchmarks for batch processing
- Property-based tests for mutation calculation correctness

### Integration with Existing Codebase
- Follow existing query API patterns in python/rustkmer/database.py
- Extend existing error handling in python/rustkmer/exceptions.py
- Reuse CLI argument patterns from existing implementation
- Maintain consistency with utils.py output parsing patterns