# Implementation Plan: Fix Database Format Issues

**Branch**: `002-jellyfish-query-implementation` | **Date**: 2025-11-28
**Purpose**: Fix database format compatibility issues between count and query commands

## Problem Summary

Based on testing with real FASTA data, the following issues were identified:

### Issue 1: Format Mismatch ❌
- **Problem**: `rustkmer count` generates bincode-serialized format, while `rustkmer query` expects RKDB format with specific header structure
- **Impact**: Users cannot use count output directly with query command
- **Root Cause**: Different serialization approaches in count vs query commands

### Issue 2: Missing Dump Command ❌
- **Problem**: `rustkmer dump` command is not implemented ("Dump command not yet implemented")
- **Impact**: Users cannot inspect or convert database files
- **Root Cause**: Placeholder implementation in main.rs

### Issue 3: Format Incompatibility ❌
- **Problem**: No tools exist to convert between formats or validate database integrity
- **Impact**: Debugging and interoperability issues
- **Root Cause**: Incomplete toolchain implementation

## Technical Analysis

### Current Count Output Format
```rust
// Current (bincode format)
bincode::serialize_into(file, &(counter.get_kmer_length(), kmers))
```

### Expected Query Input Format
```rust
// Expected (RKDB format)
DatabaseHeader {
    magic: b"RKDB",
    version: 1,
    kmer_size: 21,
    total_kmers: count,
    sorted: bool,
    data_offset: 64,
    index_offset: 0,
    canonical: bool,
}
```

## Solution Strategy

### Phase 1: Fix Count Command Output Format
**Goal**: Make count command generate RKDB format compatible with query

#### Tasks:
1. **[T001]** Modify `output_binary_format()` to use RKDB format
2. **[T002]** Implement `write_rkdb_format()` function
3. **[T003]** Update DatabaseHeader serialization to match read format
4. **[T004]** Ensure proper alignment and byte ordering (little-endian)
5. **[T005]** Add RKDB format validation in count output

### Phase 2: Implement Dump Command
**Goal**: Add database inspection and conversion capabilities

#### Tasks:
1. **[T006]** Remove placeholder implementation from main.rs
2. **[T007]** Create `src/cli/commands/dump.rs` module
3. **[T008]** Implement `execute_dump()` function
4. **T009** Add dump command argument definitions
5. **[T010]** Support both RKDB and bincode format detection
6. **T011]** Add text output with human-readable k-mer sequences
7. **T012]** Add format validation and error reporting

### Phase 3: Add Format Conversion
**Goal**: Provide tools to convert between formats

#### Tasks:
1. **[T013]** Add format auto-detection to dump command
2. **[T014]** Implement bincode-to-RKDB conversion
3. **[T015]** Add `--convert` option to dump command
4. **T016]** Support bidirectional conversion
5. **T017]** Add progress reporting for large databases

### Phase 4: Testing & Validation
**Goal**: Ensure format compatibility works end-to-end

#### Tasks:
1. **[T018]** Test count → query workflow with new RKDB format
2. **[T019]** Verify dump command works with both formats
3. **T020]** Test format conversion accuracy
4. **[T021]** Add integration tests for complete workflow
5. **T022]** Performance testing for format conversion

## Implementation Details

### RKDB Format Structure (Fixed)
```rust
// Header (32 bytes total)
struct DatabaseHeader {
    magic: [u8; 4],        // "RKDB"
    version: u16,            // 1
    kmer_size: u8,           // 1-127
    padding: u8,             // 0
    padding2: u16,           // 0
    total_kmers: u64,        // count
    flags: u8,               // bit flags
    alignment: u64,          // padding
    data_offset: u64,        // 32 (header size)
    index_offset: u64,       // 0 (unused)
}
```

### K-mer Entry Structure
```rust
// Each entry (12 bytes)
struct KmerEntry {
    kmer: u64,    // encoded k-mer
    count: u32,   // occurrence count
}
```

## Risk Assessment

### Low Risk
- **Backward Compatibility**: New format is additive, old bincode files can still be converted
- **Performance**: RKDB format is designed for efficient random access
- **Complexity**: Changes are localized to I/O modules

### Mitigation Strategies
- **Testing**: Comprehensive test coverage before release
- **Fallback**: Maintain bincode support during transition
- **Documentation**: Clear migration guide for users

## Success Criteria

### Functional Requirements ✅
- [ ] Count command outputs RKDB format by default
- [ ] Query command successfully reads count output
- [ ] Dump command provides database inspection
- [ ] Format conversion tools work correctly

### Quality Requirements ✅
- [ ] All existing functionality preserved
- [ ] No performance regression
- [ ] Comprehensive error handling
- [ ] Clear user documentation

### Integration Requirements ✅
- [ ] End-to-end workflow works (count → query)
- [ ] Jellyfish compatibility maintained
- [ ] Toolchain integration complete

## Implementation Timeline

**Phase 1**: 2-3 hours (Count format fix)
**Phase 2**: 2-3 hours (Dump command)
**Phase 3**: 1-2 hours (Conversion tools)
**Phase 4**: 1-2 hours (Testing & validation)

**Total Estimated Time**: 6-10 hours

## Dependencies

### Internal Dependencies
- Database format definitions (src/database/format.rs) ✅
- Query engine (src/database/query.rs) ✅
- CLI framework (src/cli/args.rs) ✅

### External Dependencies
- byteorder (already in use) ✅
- serde (already in use) ✅
- clap (already in use) ✅

## Testing Strategy

### Unit Tests
- Database header serialization/deserialization
- Format detection logic
- Conversion accuracy

### Integration Tests
- End-to-end count → query workflow
- Dump command functionality
- Error handling scenarios

### Performance Tests
- Large database handling
- Format conversion overhead
- Memory usage validation

## Rollback Plan

If issues arise:
1. **Immediate**: Revert to bincode format in count command
2. **Short-term**: Add `--format=rkdb` flag option
3. **Long-term**: Implement compatibility layer

## Next Steps

1. **Immediate**: Start Phase 1 implementation
2. **Testing**: Validate each phase independently
3. **Integration**: Test complete workflow
4. **Documentation**: Update user guides and examples
5. **Release**: Deploy with migration guide

**Status**: Ready for implementation
**Priority**: High (Critical user workflow fix)