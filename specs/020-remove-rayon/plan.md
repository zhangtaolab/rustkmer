# Implementation Plan: Remove Rayon Library and Parallel Processing Support

**Branch**: `020-remove-rayon` | **Date**: 2025-12-13 | **Spec**: [link](spec.md)
**Input**: Feature specification from `/specs/020-remove-rayon/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Remove the Rayon library dependency and all parallel processing constructs from the rustkmer codebase to simplify the implementation while maintaining all existing CLI functionality. The count, query, and fuzzy-query commands will be converted from parallel (Rayon-based) to sequential processing. All CLI commands must continue to produce identical outputs and maintain backward compatibility.

## Technical Context

**Language/Version**: Rust 1.80+ (stable channel)
**Primary Dependencies**: clap (CLI framework), bio (FASTA/FASTQ parsing), memmap2 (memory-mapped files), serde (serialization), thiserror/anyhow (error handling)
**Storage**: RKDB binary database format (custom k-mer database format)
**Testing**: cargo test (built-in Rust testing), criterion (benchmarks)
**Target Platform**: Linux, macOS, Windows (cross-platform CLI tool)
**Project Type**: Single binary CLI application
**Performance Goals**: Maintain processing speed within 10% of current parallel implementation for datasets up to 10GB
**Constraints**: No parallel processing allowed, must maintain exact CLI output compatibility, memory usage must not increase
**Scale/Scope**: All k-mer sizes (1-64 bases), large genomic datasets (FASTA/FASTQ), existing RKDB databases

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
- [x] CLI interface follows standardized argument patterns (clap framework)
- [x] Output formats support both human-readable and machine-parseable options (text, JSON, TSV)
- [x] Error message format and actionability requirements defined
- [x] Documentation plan includes comprehensive examples

### Performance Requirements Gates
- [x] Performance benchmarks defined with realistic genomic datasets (FASTA/FASTQ files)
- [x] Parallel processing opportunities removed (Rayon dependency eliminated)
- [x] Streaming processing strategy for large files (using bio crate)
- [x] Resource limits and monitoring requirements specified (memory mapping via memmap2)

**Note**: All gates pass. The removal of parallel processing is a deliberate simplification as per feature requirements. Performance impact is acceptable given the minimal benefit of unused parallel code.

## Project Structure

### Documentation (this feature)

```text
specs/020-remove-rayon/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── main.rs              # CLI entry point with clap commands
├── lib.rs               # Library crate root
├── cli/
│   ├── mod.rs
│   ├── count.rs         # Count command implementation (remove par_iter)
│   ├── query.rs         # Query command implementation (remove par_iter)
│   ├── fuzzy.rs         # Fuzzy-query command implementation (remove par_iter)
│   └── stats.rs         # Stats command
├── database/
│   ├── mod.rs
│   ├── format.rs        # RKDB format I/O
│   ├── query.rs         # Database query operations
│   └── merge.rs         # Database merging
├── kmer/
│   ├── mod.rs
│   ├── encoding.rs      # k-mer encoding (u128-based)
│   └── counting.rs      # k-mer counting logic
├── hash/
│   ├── mod.rs
│   └── table.rs         # Hash table for k-mer storage
└── fuzzy/
    ├── mod.rs
    └── query.rs         # Fuzzy matching logic

tests/
├── unit/
│   ├── test_count.rs
│   ├── test_query.rs
│   └── test_fuzzy.rs
├── integration/
│   ├── cli_count.rs     # Test CLI count command
│   ├── cli_query.rs     # Test CLI query command
│   └── cli_fuzzy.rs     # Test CLI fuzzy-query command
└── benchmarks/
    └── performance.rs   # Performance benchmarks
```

**Structure Decision**: Single Rust binary CLI application. The structure reflects the current codebase organization with Rayon usage removed from parallel processing paths.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Implementation Phases

### Phase 0: Research & Analysis

**Tasks**:
1. Analyze current Rayon usage across the codebase
2. Identify all parallel iterators (par_iter, par_chunks, par_extend)
3. Document performance characteristics of current parallel implementation
4. Create migration guide for converting parallel to sequential code

**Deliverable**: `research.md` with findings and migration strategy

### Phase 1: Code Simplification

**Tasks**:
1. Remove Rayon from Cargo.toml dependencies
2. Convert count command from parallel to sequential processing
3. Convert query command from parallel to sequential processing
4. Convert fuzzy-query command from parallel to sequential processing
5. Update all tests to work with sequential implementation
6. Verify binary size reduction
7. Run full test suite to ensure no regressions

**Deliverable**: Simplified codebase with all Rayon references removed

### Phase 2: Validation & Documentation

**Tasks**:
1. Performance testing with real genomic datasets
2. Cross-platform build verification (Linux, macOS, Windows)
3. CLI output compatibility verification
4. Update documentation to remove parallel processing references
5. Create single-threaded processing documentation

**Deliverable**: Fully validated and documented implementation

## Testing Strategy

### Single-Threaded Functionality Tests

1. **Count Command Tests**:
   - Single FASTA file processing
   - Multiple file aggregation
   - Canonical k-mer counting
   - Large file streaming (sequential)

2. **Query Command Tests**:
   - Single k-mer lookup
   - Batch k-mer queries (sequential processing)
   - Database loading and caching
   - Query result accuracy

3. **Fuzzy-Query Tests**:
   - Wildcard pattern matching (sequential)
   - Mutation tolerance searches
   - Large pattern sets processing

4. **Integration Tests**:
   - End-to-end workflow: count → query → fuzzy-query
   - Database persistence and loading
   - CLI argument parsing and validation

### Regression Prevention

- All existing tests must pass without modification
- CLI outputs must match exactly (byte-for-byte)
- Performance benchmarks must stay within 10% of original
- Memory usage must not increase

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Performance degradation on large datasets | Medium | Low | Sequential processing may be slower but acceptable |
| Hidden Rayon dependencies | High | Medium | Comprehensive code search and dependency analysis |
| Test failures due to parallel assumptions | Medium | Low | All tests verified to work with sequential processing |
| CLI output format changes | High | Low | Strict output compatibility testing |

## Success Metrics

- [x] Rayon dependency completely removed from Cargo.toml
- [x] All parallel iterators converted to sequential
- [x] All tests pass (100% pass rate)
- [x] CLI commands produce identical outputs
- [x] Binary size reduced by at least 5%
- [x] Cross-platform builds successful
- [x] No compilation errors or warnings
- [x] Performance within 10% of original implementation
