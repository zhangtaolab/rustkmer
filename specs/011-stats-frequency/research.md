# Research Findings: Stats Command Implementation

**Date**: December 9, 2025
**Feature**: Stats Command with K-mer Count Frequency Distribution

## Executive Summary

This research document outlines the technical approach for implementing a high-performance statistics command for the rustkmer CLI tool. The implementation will focus on memory-efficient processing of large RKDB databases with billions of k-mers while providing comprehensive statistics and flexible output formats.

## Key Technical Decisions

### 1. Streaming Algorithm Architecture

**Decision**: Use a streaming approach with optional TDigest for approximate median calculation.

**Rationale**:
- Loading billions of k-mer counts into memory is infeasible (>8GB for 1B items)
- TDigest provides O(1) memory usage with configurable accuracy
- Streaming allows processing databases larger than available RAM

**Implementation Strategy**:
- Single-pass algorithm for basic statistics (min, max, mean, total)
- TDigest integration for median and percentile calculations
- Optional two-pass approach for complete frequency distribution when requested

### 2. Memory Management Strategy

**Decision**: Implement memory-bounded frequency distribution with configurable bin limits.

**Rationale**:
- Complete frequency distribution for high counts (millions) would consume excessive memory
- Users often need summarized statistics more than granular frequency data
- Configurable limits provide flexibility based on available resources

**Implementation Strategy**:
- Default limit of 1000 bins for frequency distribution
- User-configurable via `--max-bins` parameter
- Automatic bin width calculation based on count range

### 3. Output Format Support

**Decision**: Support multiple formats using a unified data structure with serde serialization.

**Rationale**:
- Consistency with existing rustkmer commands
- Machine-readable formats essential for pipeline integration
- serde provides zero-cost serialization with compile-time guarantees

**Implementation Strategy**:
- Text format for human readability (default)
- JSON for API integration
- CSV/TSV for spreadsheet and data analysis tools
- All formats derive from the same `DatabaseStatistics` struct

### 4. Performance Optimizations

**Decision**: Leverage existing dependencies and add minimal new ones.

**Rationale**:
- Codebase already uses rayon for parallelization
- memmap2 is available for efficient file access
- indicatif provides progress reporting

**Implementation Strategy**:
- Parallel processing using rayon's `par_iter()`
- Memory-mapped file access to avoid loading entire database
- Progress bars for long-running operations (>1 second)

### 5. Error Handling Approach

**Decision**: Extend existing thiserror-based error handling with statistics-specific errors.

**Rationale**:
- Consistency with rustkmer's error handling patterns
- thiserror provides excellent error messages with minimal boilerplate
- Proper error types improve debugging and user experience

## Dependencies Analysis

### Existing Dependencies to Leverage:
- `clap v4.5` - CLI argument parsing
- `rayon 1.10` - Parallel processing
- `memmap2 0.9` - Memory-mapped file I/O
- `serde 1.0` - Serialization for output formats
- `thiserror 2.0` - Error handling
- `indicatif` - Progress bars

### Recommended New Dependencies:
- `tdigest` v0.2 - Streaming quantile estimation
  - Lightweight, pure Rust implementation
  - Configurable compression parameter for accuracy/memory tradeoff
  - Battle-tested in production systems

## Algorithm Specifications

### Streaming Statistics Algorithm

```
Input: RKDB database with N k-mers
Output: DatabaseStatistics

Initialize:
- total_kmers = 0
- unique_kmers = 0
- min_count = ∞
- max_count = 0
- sum_counts = 0
- tdigest = TDigest.new(compression=100)
- frequency_map = HashMap<u32, u64> (with size limit)

For each k-mer entry:
1. total_kmers += count
2. unique_kmers += 1
3. min_count = min(min_count, count)
4. max_count = max(max_count, count)
5. sum_counts += count
6. tdigest.insert(count)
7. if count <= threshold OR map_size < limit:
       frequency_map[count] += 1

Calculate:
- mean_count = sum_counts / unique_kmers
- median_count = tdigest.quantile(0.5)
- frequency_distribution = expand_to_full_range(frequency_map, min_count, max_count)

Return DatabaseStatistics with all fields
```

### Memory Usage Estimates

- **Base statistics**: <1KB regardless of database size
- **TDigest**: ~10KB with compression=100
- **Frequency map**: Variable, bounded by max-bins parameter
  - Default 1000 bins: ~16KB
  - Maximum 10000 bins: ~160KB
- **Total worst-case**: <200KB memory usage

## Performance Benchmarks

### Target Performance (based on requirements):
- **Databases up to 1B unique k-mers**: Process without memory issues
- **Statistics calculation**: <5 seconds for typical databases
- **Memory usage**: <200MB regardless of database size

### Expected Performance Characteristics:
- **I/O bound**: Memory-mapped file access at ~500MB/s
- **CPU bound**: Parallel processing scales with core count
- **Memory bound**: Constant memory usage (O(1) relative to database size)

## Integration Considerations

### CLI Integration Points:
1. **args.rs**: Extend Commands enum with Stats variant
2. **commands/stats.rs**: New module for stats implementation
3. **database/mod.rs**: Reuse existing database reading logic
4. **main.rs**: Add stats command routing

### Testing Strategy:
- Unit tests for statistical calculations
- Integration tests with sample databases
- Property-based tests for algorithm correctness
- Performance benchmarks for regression testing

## Alternatives Considered

### Complete Frequency Distribution in Memory
- **Rejected**: Would require O(max_count) memory
- **Issue**: Max count could be millions, leading to GB of memory usage

### External Sorting for Median
- **Rejected**: Requires multiple passes over data
- **Issue**: Doubles I/O requirements, slower execution

### Custom Quantile Algorithm
- **Rejected**: TDigest is well-tested and optimized
- **Issue**: Reinventing well-solved problem increases risk

## Implementation Risks and Mitigations

### Risk 1: TDigest accuracy
- **Mitigation**: Use conservative compression (100) for 1% accuracy
- **Fallback**: Exact median calculation for small datasets

### Risk 2: Frequency distribution memory
- **Mitigation**: Enforce hard limits with clear error messages
- **Fallback**: Two-pass algorithm with binning for large ranges

### Risk 3: Performance regression
- **Mitigation**: Comprehensive benchmark suite
- **Fallback**: Exact calculations with warning for large datasets

## Success Metrics

1. **Correctness**: All statistics accurate within 0.1% for test datasets
2. **Performance**: <5 seconds for 100M k-mer database
3. **Memory**: <200MB peak usage regardless of database size
4. **Usability**: Clear error messages and helpful CLI output

## Next Steps

1. Implement basic stats command structure
2. Add streaming statistics algorithm
3. Integrate output format support
4. Add comprehensive tests
5. Performance tuning and optimization