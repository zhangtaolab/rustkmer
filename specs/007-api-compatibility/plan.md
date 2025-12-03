# Implementation Plan: RustKmer Python API Compatibility Verification

**Branch**: `007-api-compatibility` | **Date**: 2025-12-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-api-compatibility/spec.md`

## Summary

This feature enforces strict database format consistency between RustKmer CLI and Python API by requiring the Python API to generate and read identical single .rkdb binary files instead of directory structures. The implementation focuses on modifying the Python API's save_to_database() and Database() methods to use the same underlying Rust database serialization as the CLI, ensuring bit-for-bit compatibility and complete interoperability.

## Technical Context

**Language/Version**: Rust 1.80+ stable + Python 3.8+ via PyO3 0.23.4
**Primary Dependencies**: PyO3 (Python bindings), serde (serialization), thiserror (error handling), rayon (parallel processing), clap (CLI), bio (genomics)
**Storage**: Single binary .rkdb files (RKDB format) - unified storage for both CLI and Python API
**Testing**: Rust cargo test + pytest for Python, criterion for benchmarks, property-based testing
**Target Platform**: Cross-platform (Linux, macOS, Windows) with focus on bioinformatics workflows
**Project Type**: Bioinformatics library with dual interfaces (CLI + Python bindings)
**Performance Goals**: <10% overhead for Python API vs native CLI, maintain sub-millisecond query performance
**Constraints**: Must maintain backward compatibility for existing CLI databases, memory usage <2x input size
**Scale/Scope**: Support databases from 1MB to >10GB, handle millions of k-mers efficiently

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
