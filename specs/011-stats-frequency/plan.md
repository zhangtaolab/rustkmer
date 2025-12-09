# Implementation Plan: Stats Command with K-mer Count Frequency Distribution

**Branch**: `011-stats-frequency` | **Date**: December 9, 2025 | **Spec**: [link](spec.md)
**Input**: Feature specification from `/specs/011-stats-frequency/spec.md`

## Summary

Implement a high-performance `rustkmer stats` command that calculates comprehensive statistics for RKDB databases using u128 encoding. The implementation will use streaming algorithms to handle billions of k-mers efficiently while providing multiple output formats (text, JSON, CSV, TSV) and configurable memory usage.

## Technical Context

**Language/Version**: Rust 1.80+ stable channel
**Primary Dependencies**: clap v4.0+, serde, rayon, memmap2, tdigest (new)
**Storage**: Binary RKDB files with memory-mapped access
**Testing**: cargo test with property-based testing (proptest)
**Target Platform**: Linux/macOS/Windows (CLI tool)
**Project Type**: Single binary CLI application
**Performance Goals**: Process 1B k-mers in <5 seconds with <200MB memory
**Constraints**: Memory-bounded processing (O(1) relative to database size)
**Scale/Scope**: Handle databases up to billions of unique k-mers

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

## Project Structure

### Documentation (this feature)

```text
specs/011-stats-frequency/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── cli-api.md       # CLI API specification
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── cli/
│   ├── commands/
│   │   ├── mod.rs        # Command module exports
│   │   ├── stats.rs      # Stats command implementation (NEW)
│   │   ├── count.rs      # Existing count command
│   │   ├── query.rs      # Existing query command
│   │   ├── merge.rs      # Existing merge command
│   │   └── dump.rs       # Existing dump command
│   └── args.rs           # CLI arguments (MODIFY)

├── database/
│   ├── mod.rs            # Database module (MODIFY)
│   ├── reader.rs         # Database reading logic
│   ├── stats.rs          # Statistics calculation (NEW)
│   └── format.rs         # Format validation (MODIFY)

tests/
├── unit/
│   └── stats_tests.rs    # Unit tests for stats (NEW)
├── integration/
│   └── stats_integration.rs  # Integration tests (NEW)
└── property/
    └── stats_properties.rs   # Property-based tests (NEW)
```

## Implementation Phases

### Phase 0: Research (COMPLETED)
- [x] Analyzed streaming algorithms for large datasets
- [x] Evaluated TDigest for approximate median calculation
- [x] Designed memory-bounded frequency distribution strategy
- [x] Identified output format requirements and patterns
- [x] Documented performance optimization strategies

### Phase 1: Design (COMPLETED)
- [x] Created data model with StreamingStatsProcessor and DatabaseStatistics
- [x] Defined CLI API contract with all options and error codes
- [x] Specified output formats (text, JSON, CSV, TSV)
- [x] Created quick start guide with usage examples
- [x] Updated agent context with new dependencies

### Phase 2: Implementation (NEXT - to be done via /speckit.tasks)
Key implementation tasks will include:
1. Add tdigest dependency to Cargo.toml
2. Extend CLI arguments in args.rs
3. Implement stats.rs command handler
4. Create database/stats.rs module
5. Add comprehensive test suite
6. Update documentation

## Technical Architecture

### Core Components

1. **StreamingStatsProcessor**
   - Single-pass statistics calculation
   - TDigest for approximate quantiles
   - Bounded frequency histogram
   - Memory-mapped database access

2. **OutputFormatters**
   - Text formatter for human-readable output
   - JSON/CSV/TSV formatters via serde
   - Consistent error message formatting

3. **CLI Integration**
   - clap argument parsing with validation
   - Progress reporting via indicatif
   - Error handling with thiserror

### Memory Management Strategy
- **Fixed overhead**: ~10KB for base statistics
- **TDigest**: ~10KB with compression=100
- **Frequency histogram**: Configurable, default 1000 bins (~16KB)
- **Total typical usage**: <100KB regardless of database size

### Performance Optimizations
- **Parallel processing**: rayon for CPU-bound operations
- **Memory mapping**: memmap2 for efficient file access
- **Streaming**: Constant memory usage (O(1) relative to database)
- **Batching**: Process entries in batches for cache efficiency

## Dependencies

### Existing Dependencies (Leveraged)
- `clap v4.5` - CLI argument parsing
- `rayon 1.10` - Parallel processing
- `memmap2 0.9` - Memory-mapped file I/O
- `serde 1.0` - Serialization for output formats
- `thiserror 2.0` - Error handling
- `indicatif` - Progress bars
- `bio 2.0` - Genomics utilities

### New Dependencies
- `tdigest 0.2` - Streaming quantile estimation
  - Lightweight, pure Rust implementation
  - Configurable compression for accuracy/memory tradeoff

## Testing Strategy

### Unit Tests
- Statistics calculation correctness
- Output format validation
- Error handling scenarios
- Memory usage verification

### Integration Tests
- End-to-end command execution
- Real database file processing
- Output format validation
- Performance benchmarking

### Property-Based Tests
- Statistical invariants preservation
- Distribution properties
- Edge case handling

### Performance Tests
- Large database processing
- Memory usage monitoring
- Regression testing

## Risk Mitigation

### Technical Risks
1. **TDigest Accuracy**
   - Mitigation: Conservative compression (100) for 1% accuracy
   - Fallback: Exact calculation for small datasets

2. **Memory Limit Exceeded**
   - Mitigation: Configurable bin limits with clear errors
   - Fallback: Two-pass algorithm with binning

3. **Performance Regression**
   - Mitigation: Comprehensive benchmark suite
   - Monitoring: CI pipeline with performance tests

### User Experience Risks
1. **Confusing Error Messages**
   - Mitigation: Standardized error format with hints
   - Testing: User feedback integration

2. **Slow Large Dataset Processing**
   - Mitigation: Progress bars and approximate mode
   - Documentation: Clear performance expectations

## Success Criteria

### Functional
- All statistics accurate within 0.1% for test datasets
- Support for all specified output formats
- Correct error handling for all edge cases

### Performance
- <5 seconds for 100M k-mer database
- <200MB peak memory usage regardless of database size
- Linear scaling with dataset size

### Quality
- 90%+ test coverage for critical paths
- Zero clippy warnings
- Comprehensive documentation

## Next Steps

1. **Immediate**: Run `/speckit.tasks` to generate implementation task list
2. **Implementation**: Execute tasks in order of dependency
3. **Testing**: Run comprehensive test suite
4. **Documentation**: Update README and man pages
5. **Release**: Merge to main branch with version bump

## Relevant Files

- [Feature Specification](spec.md)
- [Research Findings](research.md)
- [Data Model](data-model.md)
- [CLI API Contract](contracts/cli-api.md)
- [Quick Start Guide](quickstart.md)
- [Implementation Tasks](tasks.md) - To be generated