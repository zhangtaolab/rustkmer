# Implementation Plan: Support k-mers up to 64 bases with u128 encoding

**Branch**: `001-u128-encoding` | **Date**: 2025-12-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-u128-encoding/spec.md`

## Summary

Upgrade rustkmer from u64 to u128 encoding to support k-mers up to 64 bases. This involves updating the core encoding module, database format (breaking change to version 2), and all CLI commands to maintain result consistency. The upgrade will increase memory usage by ~2x but enable analysis of longer DNA sequences crucial for modern genomics applications.

## Technical Context

**Language/Version**: Rust 1.80+ stable
**Primary Dependencies**: clap 4.5 (CLI), serde 1.0 (serialization), thiserror 2.0 (error handling), rayon 1.10 (parallel processing), memmap2 0.9 (memory mapping), bio 2.0 (genomics)
**Storage**: Binary .rkdb files (version 2 format)
**Testing**: cargo test + proptest for property-based testing
**Target Platform**: Linux/macOS/Windows (64-bit)
**Project Type**: Single binary CLI application
**Performance Goals**:
- Query response time <10ms for any k-mer size
- Database creation time linear with input size
- No regression in performance for k≤32
- Memory usage increase ≤120%
**Constraints**:
- k-mer size: 1 ≤ k ≤ 64
- Database entries: 20 bytes each (16-byte k-mer + 4-byte count)
- No backward compatibility with version 1 databases
**Scale/Scope**: Support genomic datasets up to terabytes with streaming processing

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Code Quality Gates
- [X] Performance benchmarks established for all computationally intensive operations
- [X] Memory efficiency requirements defined for target data sizes
- [X] Error handling strategy designed with Result/Option patterns
- [X] Code organization follows Rust best practices and module boundaries

### Testing Standards Gates
- [X] Unit test coverage plan defined (target: 90%+ for critical paths)
- [X] Integration test scenarios identified for module interactions
- [X] Property-based test requirements specified for complex algorithms
- [X] Performance regression test criteria established

### User Experience Consistency Gates
- [X] CLI interface follows standardized argument patterns
- [X] Output formats support both human-readable and machine-parseable options
- [X] Error message format and actionability requirements defined
- [X] Documentation plan includes comprehensive examples

### Performance Requirements Gates
- [X] Performance benchmarks defined with realistic genomic datasets
- [X] Parallel processing opportunities identified and planned
- [X] Streaming processing strategy for large files
- [X] Resource limits and monitoring requirements specified

## Project Structure

### Documentation (this feature)

```text
specs/001-u128-encoding/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── cli-openapi.yaml # CLI API specification
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── kmer/
│   ├── encoding.rs      # Updated to use u128
│   ├── canonical.rs     # Updated for u128 operations
│   └── operations.rs    # Updated bit manipulation
├── database/
│   ├── format.rs        # Updated for version 2 format
│   ├── query.rs         # Updated for u128 entries
│   └── merge.rs         # Updated for new entry size
├── cli/
│   └── commands/
│       ├── count.rs     # Updated for u128 support
│       ├── query.rs     # Updated for u128 support
│       ├── dump.rs      # Updated for u128 support
│       └── merge.rs     # Updated for u128 support
├── hash/
│   └── table.rs         # Updated HashMap<u128, u32>
└── python/              # Updated Python bindings

tests/
├── unit/                # Unit tests for each module
├── integration/         # Integration tests for CLI commands
├── property/            # Property-based tests with proptest
└── regression/          # Performance regression tests
```

**Structure Decision**: Single project structure with updated source modules to support u128 encoding throughout the codebase

## Implementation Phases

### Phase 0: Research (Complete)
- [X] Research u128 encoding patterns and performance implications
- [X] Define database migration strategy (breaking change to v2)
- [X] Establish testing approach with property-based testing
- [X] Document performance expectations and constraints

### Phase 1: Design (Complete)
- [X] Define updated data model with u128 entries
- [X] Specify CLI API contracts
- [X] Create user documentation and quickstart guide
- [X] Update agent context with new technology details

### Phase 2: Implementation (Next)
1. Update core encoding module to use u128
2. Update database format to version 2
3. Modify all CLI commands for u128 support
4. Update Python bindings
5. Comprehensive testing at each step

## Critical Success Factors

1. **Encoding Consistency**: Must maintain identical results between u64 and u128 for k≤32
2. **Performance**: Ensure acceptable performance despite larger data structures
3. **Testing**: Comprehensive property-based testing to catch encoding errors
4. **Documentation**: Clear migration guide for users

## Risk Mitigation

- **Performance Risk**: Implement benchmarks to catch regressions early
- **Compatibility Risk**: Clear error messages for old database format
- **Complexity Risk**: Gradual implementation with testing at each step
- **Data Integrity Risk**: Extensive validation including round-trip tests