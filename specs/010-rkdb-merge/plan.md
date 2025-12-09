# Implementation Plan: RKDB Database Merge

**Branch**: `010-rkdb-merge` | **Date**: 2025-12-09 | **Spec**: [/specs/010-rkdb-merge/spec.md](/specs/010-rkdb-merge/spec.md)
**Input**: Feature specification from `/specs/010-rkdb-merge/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a robust RKDB database merge functionality that combines multiple k-mer databases by summing counts for identical k-mers while preserving unique entries. The solution will validate database compatibility (k-mer size and canonical mode), use u128 encoding exclusively, and provide comprehensive error handling and progress reporting.

## Technical Context

**Language/Version**: Rust 1.80+ stable channel
**Primary Dependencies**:
- clap v4.0+ (CLI argument parsing)
- serde (serialization)
- thiserror (error handling)
- anyhow (error handling)
- rayon (parallel processing)
- criterion (benchmarks)
- bio (FASTA/FASTQ parsing)
- memmap2 (memory-mapped files)
- hashbrown with AHasher (optimized hash maps)

**Storage**: Binary RKDB (.rkdb) files with custom database format
**Testing**: cargo test with comprehensive test suite (unit, integration, property-based, benchmarks)
**Target Platform**: Linux/macOS/Windows (CLI tool)
**Project Type**: Single binary with library components
**Performance Goals**: Merge 10M k-mers per database in under 5 minutes
**Constraints**: Memory usage ≤3x unique k-mers in output, u128 encoding only
**Scale/Scope**: Support databases with 100M+ k-mers

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Code Quality Gates
- [x] Performance benchmarks established for all computationally intensive operations (benches/merge_benchmarks.rs exists)
- [x] Memory efficiency requirements defined for target data sizes (≤3x unique k-mers)
- [x] Error handling strategy designed with Result/Option patterns (thiserror implemented)
- [x] Code organization follows Rust best practices and module boundaries (existing codebase structure)

### Testing Standards Gates
- [x] Unit test coverage plan defined (target: 90%+ for critical paths)
- [x] Integration test scenarios identified for module interactions (tests/integration/)
- [x] Property-based test requirements specified for complex algorithms (tests/property/)
- [x] Performance regression test criteria established (benchmarks with criteria)

### User Experience Consistency Gates
- [x] CLI interface follows standardized argument patterns (clap derive macros)
- [x] Output formats support both human-readable and machine-parseable options
- [x] Error message format and actionability requirements defined (enhanced error messages)
- [x] Documentation plan includes comprehensive examples (quickstart.md exists)

### Performance Requirements Gates
- [x] Performance benchmarks defined with realistic genomic datasets (5min for 10M k-mers)
- [x] Parallel processing opportunities identified and planned (rayon integration)
- [x] Streaming processing strategy for large files (merge configuration supports streaming)
- [x] Resource limits and monitoring requirements specified (memory constraints defined)

## Project Structure

### Documentation (this feature)

```text
specs/010-rkdb-merge/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Task breakdown
```

### Source Code (repository root)

```text
src/
├── cli/
│   ├── commands/
│   │   └── merge.rs      # Merge CLI command implementation
│   └── args.rs           # CLI argument definitions
├── database/
│   ├── format.rs         # RKDB format and merge implementation
│   ├── merge_config.rs   # Merge configuration
│   └── merge_error.rs    # Error handling for merge operations
└── kmer/
    ├── encoding.rs       # u128 k-mer encoding
    └── canonical.rs      # Canonical k-mer handling

tests/
├── integration/
│   └── merge_tests.rs    # Integration tests for merge
├── property/
│   ├── test_merge_associativity.rs
│   └── test_merge_commutativity.rs
└── fixtures/             # Test database files

benches/
└── merge_benchmarks.rs   # Performance benchmarks
```

**Structure Decision**: Single binary project with library components, following Rust conventions and integrating with existing rustkmer codebase structure.

## Phase Completion Status

### Phase 0: Research ✅ COMPLETE
- **research.md**: Created with comprehensive technical decisions
- **Key findings**: All technical decisions established, no unresolved clarifications
- **Dependencies**: All required dependencies already available in codebase

### Phase 1: Design & Contracts ✅ COMPLETE
- **data-model.md**: Exists with complete entity definitions
- **contracts/merge-api.md**: Complete API specification
- **quickstart.md**: Comprehensive user guide created
- **Agent context**: Updated with Rust 1.80+ and RKDB specifications

### Constitution Check: ✅ ALL GATES PASSING
- Code Quality Gates: All satisfied
- Testing Standards Gates: All satisfied
- User Experience Consistency Gates: All satisfied
- Performance Requirements Gates: All satisfied

## Implementation Readiness

All planning phases complete. Ready for implementation using existing task breakdown in tasks.md. Key technical decisions:

- **Encoding**: u128 exclusively (per user clarification)
- **Incompatibility Handling**: Strict rejection with errors (no --force)
- **Memory Strategy**: Hybrid in-memory/streaming approach
- **Performance**: Parallel processing with Rayon, hashbrown/AHasher
- **Testing**: Comprehensive 6-layer testing strategy
