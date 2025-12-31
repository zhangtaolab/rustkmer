# Implementation Plan: PyO3 Fuzzy Query Implementation

**Branch**: `013-pyo3-fuzzy-query` | **Date**: 2025-12-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/013-pyo3-fuzzy-query/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implementation of PyO3 fuzzy query functionality for rustkmer, enabling N-wildcard pattern matching (like "GANNNGA") with direct Rust integration. The feature extends existing PyDatabase functionality to support fuzzy queries through the same database instance, eliminating the need for separate database loading. Key capabilities include N-wildcard expansion, mutation tolerance, position-specific constraints, and significant performance improvements over subprocess-based approaches.

## Technical Context

**Language/Version**: Rust 1.80+ stable channel + Python 3.10+ via PyO3 0.22.6  
**Primary Dependencies**: 
- Rust: clap, serde, thiserror, anyhow, rayon, bio, memmap2 (existing)
- Python: pytest, pyo3-build-config
- PyO3: Python binding generation and FFI integration  
**Storage**: Binary RKDB files with memory-mapped access (existing format)  
**Testing**: Rust cargo test + Python pytest 8.4+  
**Target Platform**: Linux, macOS, Windows  
**Project Type**: Single project with Rust core and Python bindings  
**Performance Goals**: 
- Single fuzzy query: <2 seconds for N-wildcard patterns
- Performance improvement: 5x faster than subprocess approach
- Memory usage: <1GB for large wildcard expansions  
**Constraints**: 
- Must resolve Python library linking issues in release mode
- Memory-efficient wildcard expansion (combinatorial explosion protection)
- API compatibility with existing PyDatabase patterns
- Must maintain feature parity with CLI implementation  
**Scale/Scope**: 
- Handle genomic k-mer databases with millions of entries
- Support complex wildcard patterns (up to 10 N's safely)
- Enable researcher workflows with batch processing

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Code Quality Gates
- [x] Performance benchmarks established for fuzzy query operations vs subprocess approach
- [x] Memory efficiency requirements defined for wildcard expansion scenarios
- [x] Error handling strategy designed with PyO3 Result/Option patterns
- [x] Code organization follows PyO3 and Rust best practices with clear module boundaries

### Testing Standards Gates  
- [x] Unit test coverage plan defined (target: 90%+ for fuzzy query logic)
- [x] Integration test scenarios identified for PyO3 integration and database sharing
- [x] Property-based test requirements specified for wildcard expansion algorithms
- [x] Performance regression test criteria established (5x speedup target)

### User Experience Consistency Gates
- [x] PyO3 API interface follows standardized patterns matching existing PyDatabase
- [x] Output formats support both human-readable and machine-parseable options
- [x] Error message format and actionability requirements defined for Python exceptions
- [x] Documentation plan includes comprehensive examples and performance comparisons

### Performance Requirements Gates
- [x] Performance benchmarks defined with realistic genomic datasets and wildcard patterns
- [x] Parallel processing opportunities identified and planned for batch operations
- [x] Streaming processing strategy for large result sets (pagination support)
- [x] Resource limits and monitoring requirements specified for memory management

## Constitution Check (Post-Design Re-evaluation)

*GATE: Must pass after Phase 1 design completion.*

### Code Quality Gates (Re-evaluated)
- [x] Performance benchmarks established: Target 5x speedup over subprocess, <2s for N-wildcard patterns
- [x] Memory efficiency requirements: <1GB for large expansions, combinatorial explosion protection
- [x] Error handling strategy: Comprehensive PyO3 exception conversion with clear Python patterns
- [x] Code organization: Clean module separation with PyFuzzyQuery, PyFuzzyResult, PyFuzzyMatch classes

### Testing Standards Gates (Re-evaluated)  
- [x] Unit test coverage: Target 90%+ for PyO3 wrapper logic, wildcards, mutations
- [x] Integration tests: Database sharing validation, API consistency with PyDatabase
- [x] Property-based tests: Wildcard expansion algorithms, mutation generation logic
- [x] Performance regression: Automated benchmarking against subprocess approach

### User Experience Consistency Gates (Re-evaluated)
- [x] PyO3 API patterns: Consistent with PyDatabase constructor, method naming, error handling
- [x] Output formats: JSON-serializable results, readable match information, filtering methods
- [x] Error messages: Python exceptions with actionable messages, clear validation feedback
- [x] Documentation: Quickstart guide, API contracts, demo scripts with practical examples

### Performance Requirements Gates (Re-evaluated)
- [x] Performance benchmarks: Defined with realistic genomic datasets and N-wildcard patterns
- [x] Parallel processing: Batch query support with concurrent execution opportunities
- [x] Streaming strategy: Result filtering, pagination support, memory-efficient processing
- [x] Resource monitoring: Memory usage tracking, combinatorial explosion limits, database sharing

**CONSTITUTION COMPLIANCE**: ✅ **PASS** - All gates satisfied with no violations requiring justification.

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

## Project Structure

### Documentation (this feature)

```text
specs/013-pyo3-fuzzy-query/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
# PyO3 bindings extension
pyo3/
├── src/
│   ├── fuzzy_query.rs   # NEW: PyO3 fuzzy query implementation
│   ├── database.rs      # Updated: PyDatabase with fuzzy query integration
│   ├── lib.rs          # Updated: Module exports
│   ├── errors.rs       # Updated: Error types
│   └── utils.rs        # Utilities
├── Cargo.toml          # Updated: PyO3 configuration
└── target/             # Build artifacts

# Python package
python/rustkmer/
├── __init__.py         # Updated: PyO3 module imports
├── database.py         # Updated: Database class with fuzzy query methods
├── fuzzy_query.py      # Updated: Fuzzy query result classes
└── tests/
    └── test_fuzzy_query.py  # NEW: PyO3 fuzzy query tests

# Rust implementation (existing)
src/
├── cli/commands/
│   ├── fuzzy.rs        # Reference: CLI fuzzy command implementation
│   └── query.rs        # Reference: CLI query command
├── fuzzy/
│   ├── mod.rs          # Existing: Fuzzy query core modules
│   ├── query.rs        # Reference: FuzzyQuery engine
│   ├── wildcard.rs     # Reference: N-wildcard expansion
│   └── expansion.rs    # Reference: Query expansion logic
└── database/
    └── format.rs       # Reference: RKDatabase format

# Demo and testing
demo_pyo3_fuzzy_query.py  # NEW: Comprehensive demo script
PYO3_FUZZY_QUERY_IMPLEMENTATION_REPORT.md  # NEW: Technical documentation
```

**Structure Decision**: Single project with Rust core and PyO3 bindings. Following existing rustkmer patterns with Python package in `python/` directory and Rust implementation in `pyo3/src/`. The implementation leverages existing Rust fuzzy query modules and creates a clean PyO3 interface that integrates seamlessly with the existing PyDatabase functionality.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No Constitution violations identified. The implementation follows established patterns and maintains simplicity while achieving the required functionality.
