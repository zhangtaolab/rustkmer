# Implementation Plan: K-mer Count Filtering Enhancement

**Branch**: `001-jellyfish-rust-port` | **Date**: 2025-11-28 | **Spec**: [spec.md](./spec.md)
**Input**: User request for "选项 B: 快速完善 添加 -L/-U 参数支持"

**Note**: This plan implements the missing FR-008 requirement for k-mer count filtering based on minimum and maximum count thresholds.

## Summary

This plan implements k-mer count filtering functionality to complete the final unaddressed functional requirement (FR-008). The enhancement will add `-L/--min-count` and `-U/--max-count` parameters to the rustkmer count command, allowing users to filter k-mers based on their occurrence frequency. This is commonly used in bioinformatics to remove rare sequencing errors (low count) or filter out overly repetitive sequences (high count).

## Technical Context

**Language/Version**: Rust 1.80+ stable channel
**Primary Dependencies**: clap v4.0+, serde, thiserror, anyhow, rayon, bio, memmap2
**Storage**: Files (text and binary k-mer output formats)
**Testing**: cargo test + criterion for performance benchmarks
**Target Platform**: Linux, macOS, Windows (cross-platform bioinformatics tool)
**Project Type**: Single CLI application with library architecture
**Performance Goals**: Maintain current processing rates while adding efficient filtering
**Constraints**: Must handle files >100GB, maintain memory efficiency <2x hash table size
**Scale/Scope**: Support individual files up to terabytes with filtering applied during output generation

### Current Architecture Analysis
- **Existing CLI**: Well-structured clap-based argument system
- **Hash Table**: Thread-safe KmerCounter with get_all_counts() method
- **Output Generation**: Separate text and binary format modules
- **Core Engine**: Functionally complete, needs output-layer filtering enhancement
- **Performance**: Optimized k-mer counting with minimal overhead expected for filtering

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Code Quality Gates
- [x] Performance benchmarks established for existing k-mer processing
- [x] Memory efficiency requirements defined (current <2x hash table size)
- [x] Error handling strategy designed with Result/Option patterns (existing thiserror integration)
- [x] Code organization follows Rust best practices and module boundaries

### Testing Standards Gates
- [x] Unit test coverage plan defined for filtering logic (target: 90%+ for critical paths)
- [x] Integration test scenarios identified for parameter validation
- [x] Property-based test requirements specified for edge cases
- [x] Performance regression test criteria established (vs baseline without filtering)

### User Experience Consistency Gates
- [x] CLI interface follows standardized argument patterns (existing clap integration)
- [x] Output formats support both human-readable and machine-parseable options (text/binary)
- [x] Error message format and actionability requirements defined (thiserror patterns)
- [x] Parameter validation consistency plan following existing patterns

### Performance Requirements Gates
- [x] Performance benchmarks defined with existing genomic datasets
- [x] Streaming processing strategy maintained (filtering during output generation)
- [x] Real-time progress monitoring continues to work (existing system)
- [x] Memory efficiency preserved (filtering doesn't increase memory footprint)

## Project Structure

### Documentation (this feature)

```text
specs/[001-jellyfish-rust-port]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command) - NEW
├── data-model.md        # Phase 1 output (/speckit.plan command) - UPDATED
├── quickstart.md        # Phase 1 output (/speckit.plan command) - UPDATED
├── contracts/           # Phase 1 output (/speckit.plan command) - UPDATED
└── tasks.md             # Phase 2 output (/speckit.tasks command) - NEEDS UPDATE
```

### Source Code (repository root)

```text
# Current Project Structure (Enhancement Areas)
src/
├── cli/
│   ├── args.rs                    # MODIFIED: Add -L/-U parameters
│   └── commands/
│       └── count.rs               # MODIFIED: Add filtering logic
├── hash/
│   └── table.rs                   # MODIFIED: Add filtered output methods
├── output/
│   ├── text.rs                    # MODIFIED: Apply filtering during output
│   └── binary.rs                  # MODIFIED: Apply filtering during output
└── tests/
    ├── unit/                      # NEW: Filtering unit tests
    └── integration/               # NEW: Filtering integration tests
```

**Structure Decision**: Leverage existing modular architecture. The filtering enhancement will focus on:
1. `cli/args.rs` - Add CLI parameters for filtering
2. `cli/commands/count.rs` - Add filtering parameter handling
3. `hash/table.rs` - Add filtered output methods
4. `output/text.rs` & `output/binary.rs` - Apply filtering during output generation
5. `tests/` - Add comprehensive filtering test coverage

## Phase 0: Research - COMPLETED ✅

Research completed in `research_filtering.md`. Key findings:

1. **Parameter Naming**: Use jellyfish standard exactly: `-L/--min-count` and `-U/--max-count`
2. **Default Behavior**: Include all k-mers when no filtering specified (jellyfish compatible)
3. **Validation Rules**: Min count ≥ 0, Max count > 0, Min ≤ Max with clear error messages
4. **Output Statistics**: Report pre-filtering counts and post-filtering results

## Next Steps for Implementation

### Phase 1: Design & Contracts - COMPLETED ✅

### ✅ **Research Completed**
Research completed in `research_filtering.md`. Key findings:

1. **Parameter Naming**: Use jellyfish standard exactly: `-L/--min-count` and `-U/--max-count`
2. **Default Behavior**: Include all k-mers when no filtering specified (jellyfish compatible)
3. **Validation Rules**: Min count ≥ 0, Max count > 0, Min ≤ Max with clear error messages
4. **Output Statistics**: Report pre-filtering counts and post-filtering results

### ✅ **Data Model Completed**
Data structures defined in `data-model.md`:

1. **CountFilter**: Filtering criteria with min/max thresholds
2. **CountFilterConfig**: Configuration with validation state
3. **FilteringResult**: Statistics for pre/post filtering comparison
4. **Enhanced KmerCounter**: Filtered k-mer retrieval methods
5. **CLI Integration**: Enhanced CountCommand with filtering parameters

### ✅ **Contracts Generated**
API contracts defined for:
- **CLI Parameter**: Jellyfish-compatible filtering arguments
- **Filter Validation**: Comprehensive parameter validation rules
- **Output Processing**: Filtered k-mer iteration with statistics

### ✅ **Agent Context Updated**
New filtering technology stack documented for future development

## Phase 2: Task Generation

Run `/speckit.tasks` to generate detailed implementation tasks based on this plan:
- CLI parameter implementation tasks
- Hash table filtering method tasks
- Output format filtering tasks
- Testing and validation tasks
- Documentation and integration tasks

### Immediate Implementation Priority (After Research)
1. Add -L/-U parameters to CLI args.rs
2. Implement filtering methods in KmerCounter
3. Update output format modules to apply filtering
4. Add comprehensive test coverage
5. Update documentation

## Success Criteria

### Functional Requirements
- [ ] Process k-mers with minimum count threshold filtering (-L)
- [ ] Process k-mers with maximum count threshold filtering (-U)
- [ ] Support combined minimum and maximum filtering (-L -U)
- [ ] Maintain existing API compatibility when no filtering specified
- [ ] Handle invalid filter ranges gracefully with informative messages

### Performance Requirements
- [ ] <5% performance overhead for filtering operations
- [ ] No additional memory usage during filtering (filter during output)
- [ ] Maintain existing progress reporting with filtered counts
- [ ] Preserve current memory efficiency for large files

### User Experience Requirements
- [ ] Clear help documentation for filtering parameters
- [ ] Consistent error messages with existing patterns
- [ ] Backward compatibility with existing scripts
- [ ] Informative output about filtered k-mer counts

## Complexity Tracking

No constitution violations identified. All enhancements extend existing functionality without architectural changes or breaking compatibility.

---

**Implementation Approach**: Filter during output generation rather than during counting to maintain memory efficiency and preserve the existing optimized counting pipeline.