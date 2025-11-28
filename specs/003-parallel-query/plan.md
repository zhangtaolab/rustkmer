# Implementation Plan: 21-mer Performance Testing

**Branch**: `003-parallel-query` | **Date**: 2025-11-28 | **Spec**: `/specs/003-parallel-query/spec.md`
**Input**: User request: "用真实数据/Users/forrest/Temp/demodata/fasta/osa1_r7.asm.fa 使用jellyfish 和rustkmer生成21mer数据库文件，然后随机生成 10000 条不同的21mer，进行 query 结果比较，jellyfish用单线程，rustkmer用单线程query和多线程queryx都进行测试。中间数据和临时文件保存在/Users/forrest/Temp/demodata/下，jellyfish用单线程，rustkmer用单线程query和多线程queryx用同一套10000 的数据，要比较结果。"

## Summary

Generate 21-mer databases using real genomic data (OSA1 r7 assembly) and conduct comprehensive performance comparison between jellyfish (single-threaded) and rustkmer (single-threaded query vs multi-threaded queryx) to determine if multi-threading provides significant performance benefits for larger k-mer sizes.

## Technical Context

**Language/Version**: Rust 1.80+ stable channel
**Primary Dependencies**: clap v4.0+ (CLI), serde (serialization), rayon (parallel processing), bio (FASTA parsing), memmap2 (memory-mapped files)
**Storage**: Binary database files (Jellyfish .jf format, RustKmer .rkdb format)
**Testing**: cargo test + criterion for benchmarks
**Target Platform**: Linux/macOS command-line environment
**Project Type**: Single project with CLI tool
**Performance Goals**: Compare single vs multi-threaded query performance for 21-mers
**Constraints**: Use existing OSA1 r7 assembly (381MB FASTA), store results in /Users/forrest/Temp/demodata/
**Scale/Scope**: 10,000 deterministic 21-mer queries for statistical significance

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Code Quality Gates
- [x] Performance benchmarks established for all computationally intensive operations (13-mer testing completed)
- [x] Memory efficiency requirements defined for target data sizes (381MB FASTA handled successfully)
- [x] Error handling strategy designed with Result/Option patterns (existing rustkmer implementation)
- [x] Code organization follows Rust best practices and module boundaries (existing codebase structure)

### Testing Standards Gates
- [x] Unit test coverage plan defined (target: 90%+ for critical paths)
- [x] Integration test scenarios identified for module interactions (database query operations)
- [x] Property-based test requirements specified for complex algorithms (proptest for 21-mer operations)
- [x] Performance regression test criteria established (existing 13-mer baseline)

### User Experience Consistency Gates
- [x] CLI interface follows standardized argument patterns (queryx command established)
- [x] Output formats support both human-readable and machine-parseable options (--verbose/--quiet flags)
- [x] Error message format and actionability requirements defined (existing error handling)
- [x] Documentation plan includes comprehensive examples (performance testing methodology)

### Performance Requirements Gates
- [x] Performance benchmarks defined with realistic genomic datasets (OSA1 r7 assembly)
- [x] Parallel processing opportunities identified and planned (single vs multi-threaded queryx)
- [x] Streaming processing strategy for large files (existing rustkmer file handling)
- [x] Resource limits and monitoring requirements specified (system monitoring implemented)

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

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
