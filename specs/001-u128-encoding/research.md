# Research Document: u128 Encoding Upgrade

**Date**: 2025-12-08
**Feature**: Support k-mers up to 64 bases with u128 encoding

## Encoding Scheme Decision

**Decision**: Use 2-bit per base encoding with u128 storage
**Rationale**: Maintains compatibility with existing encoding logic while extending capacity to 64 bases
**Alternatives considered**:
- 3-bit encoding (supports more nucleotides but wastes space)
- Variable-length encoding (complex implementation)

## Database Format Migration Strategy

**Decision**: Backward incompatible migration (version 2 format)
**Rationale**: Simplifies implementation and avoids dual-format complexity
**Key points**:
- Update database header to indicate version
- Provide clear error messages for old format
- Document migration path for users

## Performance Considerations

- **Memory impact**: u128 uses 16 bytes vs 8 bytes for u64 (2x increase)
- **CPU impact**: u128 operations compile to multiple 64-bit instructions on 64-bit systems
- **Cache efficiency**: Larger entries may reduce cache performance for large datasets
- **Benchmarking needed**: Establish baseline for regression testing

## Testing Strategy

### Property-Based Testing
Use proptest for comprehensive validation:
- Round-trip encoding/decoding consistency
- Reverse complement correctness
- Lexicographic ordering preservation
- Edge cases (k=1, k=64, invalid characters)

### Integration Testing
- Test all CLI commands (count, dump, query, fuzzy-query, merge)
- Validate output consistency with u64 implementation
- Performance regression testing

### Cross-Platform Validation
- Ensure consistent results across architectures
- Validate byte order (endian) handling

## Implementation Guidelines

1. **Gradual Migration**:
   - Start with core encoding module
   - Update data structures
   - Modify database I/O
   - Update CLI commands
   - Update Python bindings

2. **Validation Points**:
   - After encoding module changes
   - After database format changes
   - After each CLI command update
   - Final integration testing

3. **Error Handling**:
   - Clear messages for k>64 attempts
   - Helpful guidance for database format errors
   - Graceful handling of invalid DNA characters