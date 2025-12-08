# Implementation Plan: u128-encoding-upgrade

**Branch**: `008-u128-encoding` | **Date**: 2025-12-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-u128-encoding/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

The u128 encoding upgrade extends rustkmer's k-mer support from size 32 to 64 by replacing u64 encoding with u128. This involves:
- Core encoding functions upgraded to handle 128-bit k-mers using standard 2-bit encoding (A=00, C=01, G=10, T=11)
- Database format evolution to 16-byte entries (from 12-byte), exactly 33% larger
- Performance targets: ≤10% slower for encoding/decoding, ≤5% slower for queries
- No memory growth limits - controlled by user via command-line parameters
- Maintaining statistical consistency with current u64 implementation
- Supporting k-mer sizes from 1 to 64 without backward compatibility requirements

## Technical Context

**Language/Version**: Rust 1.80+ stable
**Primary Dependencies**: PyO3 0.23.4, clap, serde, byteorder, rayon, criterion
**Storage**: Binary RKDB files with memory-mapped access (version 2 format)
**Testing**: cargo test + criterion for benchmarks + proptest for property-based testing
**Target Platform**: Linux, macOS, Windows (cross-platform)
**Project Type**: Single Rust binary with Python bindings
**Performance Goals**: Query ≤105ms, encoding ≤110% of u64 time, process 10M+ k-mers
**Constraints**: User-configurable memory limits only, support concurrent access
**Scale/Scope**: Genomic datasets up to terabytes, k-mer sizes 1-64, databases 33% larger

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Code Quality Gates
- [x] Performance benchmarks established (encoding ≤110%, query ≤105ms, criterion)
- [x] Memory efficiency defined (user-configurable, 16-byte entries)
- [x] Error handling strategy designed (Result/Option patterns in existing codebase)
- [x] Code organization follows Rust best practices (established module structure)

### Testing Standards Gates
- [x] Unit test coverage plan defined (90%+ for critical paths, tasks.md)
- [x] Integration test scenarios identified (CLI commands, Python API, database I/O)
- [x] Property-based test requirements specified (proptest for encoding algorithms)
- [x] Performance regression test criteria established (≤10% encode, ≤5% query)

### User Experience Consistency Gates
- [x] CLI interface follows standardized patterns (clap framework, existing structure)
- [x] Output formats support human/machine parseable (JSON, TSV maintained)
- [x] Error message format defined (clear messages for invalid k-sizes)
- [x] Documentation plan includes examples (quickstart.md, k=33-64 use cases)

### Performance Requirements Gates
- [x] Performance benchmarks defined (specific targets in spec.md)
- [x] Parallel processing planned (rayon for k-mer processing)
- [x] Streaming processing strategy (memory-mapped files)
- [x] Resource limits specified (user-configurable via CLI)

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

└── benchmarks/
    ├── encoding_bench.rs  # Updated: u128 benchmarks
    └── query_bench.rs     # Updated: k=64 benchmarks
```

**Structure Decision**: Single Rust project with Python bindings, following existing rustkmer structure

## Complexity Tracking

> No constitution violations - all gates passed

## Phase 0 Complete: Research Findings

✅ **Research Document**: [research.md](research.md)
- Technical decisions made for u128 encoding
- Database format evolution strategy
- Performance implications identified
- Risk assessment completed

## Phase 1 Complete: Design & Contracts

✅ **Data Model**: [data-model.md](data-model.md)
- Core entities defined (Kmer, KmerEntry, DatabaseHeader)
- Validation rules established
- Error types specified

✅ **API Contracts**:
- [CLI API Contract](contracts/cli-api.md)
- [Python API Contract](contracts/python-api.md)

✅ **Quickstart Guide**: [quickstart.md](quickstart.md)
- User documentation for CLI and Python API
- Examples for k>32 use cases
- Performance tips and common pitfalls

✅ **Agent Context Updated**
- Claude context updated with u128 support information

## Updated with Latest Clarifications

✅ **Memory Management**: No system limits, user-controlled only
✅ **Performance Targets**: Specific metrics (≤10% encode, ≤5% query)
✅ **Encoding Specification**: Standard 2-bit encoding (A=00, C=01, G=10, T=11)
✅ **Database Size**: Exactly 33% increase (16/12 bytes)
✅ **No Migration Required**: u128 format only, no backward compatibility

## Next Steps

The implementation plan is now complete and aligned with all clarifications. To proceed with implementation:

1. Run `/speckit.implement` to begin task execution
2. Follow tasks.md for detailed implementation steps
3. Ensure all tests pass for k-mer sizes 33-64
4. Validate performance targets are met

## Key Implementation Updates

1. **Performance Testing**: Verify ≤10% encode, ≤5% query degradation
2. **Memory Configuration**: Implement user-configurable limits only
3. **Database Format**: 16-byte entries (exact 33% size increase)
4. **Encoding Algorithm**: Standard 2-bit encoding implementation
