# Research Findings: u128 Encoding Upgrade

**Date**: 2025-12-08
**Feature**: 008-u128-encoding
**Phase**: 0 - Outline & Research

## Executive Summary

The u128 encoding upgrade requires changes across multiple layers of the rustkmer codebase:
- Core encoding functions need u128 support for k-mers up to length 64
- Database format changes with 16-byte entries (up from 12)
- Python API updates for 128-bit integer support
- Maintaining statistical consistency with u64 implementation

## Technical Decisions

### 1. u128 Encoding Strategy

**Decision**: Implement native u128 encoding using 2 bits per base
- **Rationale**: Direct mapping from current u64 approach, minimal code changes
- **Implementation**:
  - A=00, C=01, G=10, T=11 encoding
  - Maximum k-mer size: 64 (128 bits / 2 bits per base)
  - Use Rust's native u128 type (fully supported in stable Rust 1.80+)
- **Alternative considered**: Custom packed encoding - rejected for complexity

### 2. Database Format Evolution

**Decision**: Increment database format version with new entry size
- **Current format**: 12-byte entries (8-byte kmer + 4-byte count)
- **New format**: 16-byte entries (16-byte kmer + 4-byte count)
- **Backward handling**: Version detection in header, graceful fallback for old format
- **Rationale**: Simple, efficient, maintains binary search properties
- **Trade-off**: 33% larger database size

### 3. Python Integration

**Decision**: Use PyO3's native u128 support
- **Implementation**: Python int can hold 128-bit values natively
- **Compatibility**: Python 3.8+ fully supports large integers
- **Performance**: Minimal overhead with PyO3's efficient conversions
- **Alternative considered**: String-based representation - rejected for performance

### 4. Memory Management

**Decision**: No system-level memory limits - user-controlled only
- **Implementation**: Memory-mapped files with 16-byte stride for binary search
- **Streaming support**: Unchanged, already processes data sequentially
- **Memory limits**: User-configurable via command-line parameters only
- **Database size**: Exactly 33% larger (16 bytes vs 12 bytes per entry)

### 5. Statistical Consistency

**Decision**: Implement reference comparison tests
- **Approach**: Process same datasets with both u64 and u128 implementations
- **Validation**: Automated tests to ensure identical statistical outputs
- **Coverage**: All edge cases including ambiguous base handling

## Implementation Strategy

### Phase 1: Core Infrastructure
1. Update encoding functions in `src/kmer/encoding.rs`
2. Modify database format in `src/database/format.rs`
3. Implement version detection for backward compatibility

### Phase 2: CLI Integration
1. Update all command validation for k≤64
2. Adjust binary search operations
3. Update help text and error messages

### Phase 3: Python API
1. Update Python bindings for u128 support
2. Maintain API compatibility
3. Add test cases for large k-mers

### Phase 4: Testing & Validation
1. Comprehensive test suite with k>32 examples
2. Statistical consistency validation
3. Performance benchmarking

## Risk Assessment

### Low Risk
- Core u128 operations (native Rust support)
- Python integration (PyO3 handles large integers)
- Memory mapping (minimal changes required)

### Medium Risk
- Database migration compatibility
- Performance impact of larger entries
- Binary search offset calculations

### Mitigations
- Comprehensive version detection
- Automated regression tests
- Performance monitoring

## Dependencies

### Required
- Rust 1.80+ (already required)
- PyO3 0.23.4 (already in use)
- No new dependencies needed

### Optional (for benchmarks)
- Criterion (already available)
- Custom test data generators for k=33-64

## Performance Considerations

### Expected Impact
- **Memory**: Exactly 33% increase in database size (16/12 bytes per entry)
- **CPU**: ≤10% slower for encoding/decoding, ≤5% slower for queries
- **I/O**: 33% larger file transfers
- **Query time**: O(log n) unchanged, ≤5% slower per comparison

### Performance Targets
- **Encoding/Decoding**: Must complete within 110% of u64 implementation time
- **Query Operations**: Must complete within 105ms per query (≤5% slower)
- **Database Creation**: Scalable to 10M+ k-mers with k=64
- **Memory Usage**: No system limits - user-controlled only

### Optimization Opportunities
- SIMD instructions for 128-bit comparisons
- Batch processing for large k-mers
- Lazy loading strategies for very large databases

## Testing Strategy

### Unit Tests
- All encoding/decoding functions with k=1..64
- Edge cases: k=32, k=33, k=64
- Error handling for invalid inputs

### Integration Tests
- Database creation and query workflows
- CLI command end-to-end tests
- Python API integration

### Consistency Tests
- u64 vs u128 statistical comparison
- Canonical representation validation
- Ambiguous base handling verification

### Performance Tests
- Benchmark suite with various k-sizes
- Memory usage profiling
- Large dataset processing (10M+ k-mers)

## Conclusion

The u128 encoding upgrade is technically straightforward with:
- Clear implementation path
- No breaking changes to user-facing APIs
- Manageable performance impact
- Comprehensive testing strategy

Main challenge is ensuring statistical consistency between u64 and u128 implementations for comparable inputs.