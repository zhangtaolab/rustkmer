# Implementation Plan: Python Binding API for rustkmer

**Branch**: `001-python-binding` | **Date**: 2025-01-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-python-binding/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature implements Python bindings for rustkmer k-mer database functionality, starting with query capabilities. The implementation will use subprocess calls to the rustkmer CLI rather than PyO3, providing an object-oriented Python API that matches CLI functionality with 100% consistency.

## Technical Context

**Language/Version**: Python 3.10+ (for the API), Rust 1.80+ (existing CLI)
**Primary Dependencies**: subprocess (Python standard library), pytest for testing
**Storage**: Binary .rkdb files (existing format)
**Testing**: pytest 8.4+ with fixtures and CLI consistency tests
**Target Platform**: Cross-platform (Linux, macOS, Windows)
**Project Type**: Python package wrapping CLI tool
**Performance Goals**: <5 seconds for dumping 1000 entries, <500MB memory usage
**Constraints**: No PyO3 usage, must support pip installation, CLI-API consistency
**Scale/Scope**: Support for large genomic databases (millions of k-mers)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design - ALL PASSES*

### Code Quality Gates
- [x] Performance benchmarks established for all computationally intensive operations (SC-002: <5s for 1000 entries)
- [x] Memory efficiency requirements defined for target data sizes (SC-003: <500MB memory usage)
- [x] Error handling strategy designed with Result/Option patterns (FR-004: Python standard exceptions)
- [x] Code organization follows Rust best practices and module boundaries (Note: Python code will follow Python PEP 8)

### Testing Standards Gates
- [x] Unit test coverage plan defined (target: 90%+ for critical paths)
- [x] Integration test scenarios identified for module interactions (CLI-API consistency tests)
- [x] Property-based test requirements specified for complex algorithms (for k-mer validation)
- [x] Performance regression test criteria established (SC-002 and SC-003)

### User Experience Consistency Gates
- [x] CLI interface follows standardized argument patterns (inherited from existing CLI)
- [x] Output formats support both human-readable and machine-parseable options (Python objects + JSON support)
- [x] Error message format and actionability requirements defined (FR-004)
- [x] Documentation plan includes comprehensive examples (quickstart.md to be generated)

### Performance Requirements Gates
- [x] Performance benchmarks defined with realistic genomic datasets (using R1_001.rkdb)
- [x] Parallel processing opportunities identified and planned (ThreadPoolExecutor for batch operations)
- [x] Streaming processing strategy for large files (via CLI dump with limits)
- [x] Resource limits and monitoring requirements specified (SC-002, SC-003)

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

```text
python/
├── rustkmer/
│   ├── __init__.py           # Main module exports
│   ├── database.py           # Database class implementation
│   ├── query.py              # QueryResult class
│   ├── stats.py              # DatabaseStats class
│   ├── exceptions.py         # Exception hierarchy
│   ├── utils.py              # Utility functions
│   └── bin/                  # Pre-compiled rustkmer binaries
│       ├── rustkmer-linux
│       ├── rustkmer-macos
│       └── rustkmer-windows.exe
├── scripts/                  # Utility and helper scripts
│   └── check_coverage.py     # Test coverage verification
├── tests/
│   ├── __init__.py
│   ├── test_database.py      # Database class tests
│   ├── test_query.py         # Query functionality tests
│   ├── test_stats.py         # Stats functionality tests
│   ├── test_batch.py         # Batch query tests
│   ├── fixtures/             # Test databases
│   │   └── test.rkdb
│   └── conftest.py           # Pytest configuration
├── examples/                 # Usage examples
│   ├── basic_usage.py
│   ├── batch_query.py
│   └── large_dataset.py
├── pyproject.toml            # Python package configuration
├── README.md                 # Package documentation
└── LICENSE                   # License file

# Rust CLI (existing)
src/
├── cli/                      # CLI implementation
├── database/                 # Database handling
└── ...                       # Other existing modules
```

**Structure Decision**: Python package wrapping existing CLI tool. The Python API is implemented as a pure Python package that uses subprocess calls to interact with the rustkmer binary. This approach avoids PyO3 dependency while maintaining full CLI compatibility.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
