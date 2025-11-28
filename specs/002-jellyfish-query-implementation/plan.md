# Implementation Plan: RustKmer Query Bug Fixes

**Branch**: `002-jellyfish-query-implementation` | **Date**: 2025-11-28 | **Spec**: `/specs/002-jellyfish-query-implementation/spec.md`
**Input**: Comprehensive bug analysis from `/tmp/rustkmer_vs_jellyfish_test_report.md`

## Summary

Fix critical bugs in rustkmer query functionality identified during real data testing. While count and dump functions work correctly and are fully compatible with jellyfish, the query function returns incorrect counts (e.g., 620756992 instead of 37) or no output for existing k-mers. The root causes include:

1. **Canonical Mode Mismatch**: Query doesn't handle canonical k-mer encoding correctly when database was created with canonical mode
2. **File Offset Calculation Error**: Binary search calculation in `read_entry_at()` may be incorrect
3. **Missing Validation**: No validation that query k-mers use same encoding mode as database

## Technical Context

**Language/Version**: Rust 1.80+ stable channel
**Primary Dependencies**: clap v4.0+, serde, thiserror, anyhow, rayon, criterion, bio, memmap2
**Storage**: RKDB binary format with little-endian encoding
**Testing**: cargo test, property-based testing for query algorithms
**Target Platform**: Linux/macOS/WASM
**Project Type**: Single bioinformatics CLI tool
**Performance Goals**: O(log n) query lookups for sorted databases, <10ms per query
**Constraints**: Memory efficient for databases >10M k-mers, offline-capable
**Scale/Scope**: Support databases up to 100M k-mers, handle queries in batch mode

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Code Quality Gates
- [x] Performance benchmarks established for all computationally intensive operations
- [x] Memory efficiency requirements defined for target data sizes
- [x] Error handling strategy designed with Result/Option patterns
- [x] Code organization follows Rust best practices and module boundaries

### Testing Standards Gates
- [x] Unit test coverage plan defined (target: 90%+ for critical paths)
- [x] Integration test scenarios identified for module interactions
- [x] Property-based test requirements specified for complex algorithms
- [x] Performance regression test criteria established

### User Experience Consistency Gates
- [x] CLI interface follows standardized argument patterns
- [x] Output formats support both human-readable and machine-parseable options
- [x] Error message format and actionability requirements defined
- [x] Documentation plan includes comprehensive examples

### Performance Requirements Gates
- [x] Performance benchmarks defined with realistic genomic datasets
- [x] Parallel processing opportunities identified and planned
- [x] Streaming processing strategy for large files
- [x] Resource limits and monitoring requirements specified

## Root Cause Analysis

Based on comprehensive testing comparing rustkmer query vs jellyfish query on real data, the following critical issues were identified:

### 1. Canonical Mode Encoding Mismatch (Critical)
**Issue**: Query doesn't apply canonical transformation when database was created with canonical mode
**Evidence**: Test database shows `canonical: false` in header but jellyfish was run with `-C` flag
**Impact**: Query k-mers encoded differently than stored k-mers, causing lookup failures
**Location**: `src/database/query.rs:105` - `encode_kmer_bytes()` doesn't check database canonical mode

### 2. File Offset Calculation Error (Critical)
**Issue**: Binary search offset calculation assumes fixed 12-byte entries but may be incorrect
**Evidence**: Query returns completely wrong count values (620756992 vs expected 37)
**Impact**: Binary search reads wrong memory locations, returns garbage data
**Location**: `src/database/query.rs:164` - `entry_offset = data_offset + (index * 12)`

### 3. Missing Query Validation (High)
**Issue**: No validation that query input matches database encoding parameters
**Evidence**: No error messages when querying with mismatched k-mer encoding
**Impact**: Silent failures make debugging difficult for users
**Location**: Throughout `src/database/query.rs`

## Detailed Bug Analysis

### Canonical K-mer Processing
The issue stems from how canonical k-mers are handled during counting vs querying:

1. **Count Mode** (working correctly):
   ```rust
   let final_kmer = if canonical {
       match canonical_kmer(encoded_kmer, k) {  // Transform to canonical
           Ok(canonical) => canonical,
           // ...
       }
   } else {
       encoded_kmer  // Use original encoding
   };
   ```

2. **Query Mode** (buggy):
   ```rust
   let encoded_kmer = encode_kmer_bytes(kmer_seq.as_bytes())?;  // Always uses original
   // Missing canonical transformation!
   ```

### File Structure Analysis
Both RKDB and Jellyfish databases show similar binary structure with valid data:
- RKDB: Contains proper k-mer entries with 8-byte k-mer + 4-byte count
- Dump function reads correctly using `byteorder::LittleEndian`
- Query function should read the same way but has calculation errors

### Binary Search Algorithm Issues
The binary search implementation appears correct logically, but the offset calculation and/or data reading may have issues:
```rust
fn read_entry_at(&mut self, index: u64) -> ProcessingResult<KmerEntry> {
    let entry_offset = self.header.data_offset + (index * 12); // 8 + 4 bytes per entry
    // ... seek and read
}
```

## Fix Strategy

### Phase 1: Canonical K-mer Encoding Fix
1. Modify `DatabaseQuery::query_kmer()` to check database canonical mode
2. Apply canonical transformation to query k-mer when needed
3. Add validation for k-mer size and character validation

### Phase 2: Data Reading Validation
1. Verify file offset calculation in `read_entry_at()`
2. Add bounds checking for index values
3. Validate that reads are returning expected data ranges

### Phase 3: Query Algorithm Improvements
1. Add debug mode for tracing query execution
2. Improve error messages for mismatched encodings
3. Add integration tests for count → dump → query workflow

### Phase 4: Testing and Validation
1. Create comprehensive test suite with real data
2. Add property-based tests for query correctness
3. Performance benchmarking against jellyfish

## Project Structure

### Documentation (this feature)

```text
specs/002-jellyfish-query-implementation/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Root cause analysis (completed in this plan)
├── data-model.md        # Database format structure
├── quickstart.md        # Query usage examples
├── contracts/           # API contracts for query functionality
└── tasks.md             # Implementation tasks (created via /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── database/
│   ├── format.rs        # Database format definitions (RKDB)
│   ├── query.rs         # Query engine (PRIMARY FIX LOCATION)
│   ├── index.rs         # Index structures
│   └── mod.rs           # Database module exports
├── cli/
│   └── commands/
│       ├── query.rs     # Query command interface
│       ├── dump.rs      # Dump command (working correctly)
│       ├── count.rs     # Count command (working correctly)
│       └── mod.rs
├── kmer/
│   ├── encoding.rs      # K-mer encoding/decoding
│   ├── canonical.rs     # Canonical k-mer operations
│   └── mod.rs
└── main.rs

tests/
├── integration/
│   └── query_tests.rs   # End-to-end query tests
├── unit/
│   └── database/
│       └── query_tests.rs
└── fixtures/
    └── test_databases/   # Sample RKDB files for testing
```

**Structure Decision**: Single project with clear separation between database logic, CLI interface, and k-mer operations. The fix focuses on `src/database/query.rs` with supporting changes in related modules.

## Implementation Tasks

The implementation will be organized into the following phases (detailed tasks will be generated via `/speckit.tasks`):

### Phase 1: Canonical K-mer Encoding Fix (Critical)
- Fix `DatabaseQuery::query_kmer()` to respect database canonical mode
- Add canonical transformation when database was created with canonical mode
- Add validation for k-mer encoding consistency

### Phase 2: Data Reading Validation (Critical)
- Verify and fix file offset calculation in `read_entry_at()`
- Add bounds checking and error handling for binary search
- Ensure data consistency with dump function

### Phase 3: Query Algorithm Improvements (High)
- Add debug mode and improved error messages
- Enhance query validation and user feedback
- Optimize performance for large databases

### Phase 4: Testing and Validation (High)
- Create comprehensive test suite with real data
- Add property-based tests for query correctness
- Performance benchmarking against jellyfish

## Testing Strategy

### Unit Tests
- Query algorithm correctness with known k-mer sets
- Canonical encoding validation
- File offset calculation accuracy
- Error handling edge cases

### Integration Tests
- End-to-end count → dump → query workflow
- Cross-compatibility with jellyfish databases
- Performance regression testing
- Large database stress testing

### Property-Based Tests
- Query correctness for random k-mer sets
- Binary search invariant maintenance
- Database format serialization/deserialization

## Success Criteria

1. **Functional Correctness**: Query returns exactly the same results as dump and jellyfish
2. **Performance**: Query time <10ms for databases up to 10M k-mers
3. **Robustness**: Proper error handling for invalid inputs
4. **Compatibility**: Full compatibility with RKDB format databases

## Complexity Tracking

No violations detected. All fixes are within existing codebase structure and follow established patterns. The solution addresses critical bugs without introducing unnecessary complexity.
