# Implementation Plan: Python Bindings for RustKmer

**Branch**: `001-python-bindings` | **Date**: 2025-12-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-python-bindings/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Create Python bindings for RustKmer to enable Python developers to perform k-mer counting, database queries, and fuzzy search operations directly from Python scripts. The implementation will use PyO3 for Rust-Python interoperability, providing a high-performance Python interface that maintains the speed advantages of the Rust implementation while offering Python-friendly APIs and documentation.

## Technical Context

**Language/Version**: Rust 1.80+ (stable) + Python 3.8+
**Primary Dependencies**: PyO3 (Rust-Python bindings), setuptools-rust, serde, thiserror, anyhow, rayon
**Storage**: Existing RKDB binary database format + memory-mapped file access
**Testing**: Rust cargo test + Python pytest + integration tests
**Target Platform**: Cross-platform (Windows, macOS, Linux) with wheel distribution
**Project Type**: Python package with Rust extension module
**Performance Goals**: Within 20% of command-line tool performance, <100ms query response for 1M k-mers
**Constraints**: Memory usage ≤150% of command-line tool, maintain compatibility with existing .rkdb format
**Scale/Scope**: Support files up to 1GB+, process 10k+ k-mers per batch, typical bioinformatics workloads

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Code Quality Gates
- [x] Performance benchmarks established for all computationally intensive operations (<100ms query response, within 20% of CLI performance)
- [x] Memory efficiency requirements defined for target data sizes (≤150% of CLI tool usage, support 1GB+ files)
- [x] Error handling strategy designed with Result/Option patterns (thiserror, PyO3 exception handling)
- [x] Code organization follows Rust best practices and module boundaries (PyO3 module structure)

### Testing Standards Gates
- [x] Unit test coverage plan defined (target: 90%+ for critical paths with cargo test + pytest)
- [x] Integration test scenarios identified for module interactions (Rust-Python interface testing)
- [x] Property-based test requirements specified for complex algorithms (k-mer counting validation)
- [x] Performance regression test criteria established (benchmark comparisons with CLI tool)

### User Experience Consistency Gates
- [x] CLI interface follows standardized argument patterns (Python API consistency with existing RustKmer CLI)
- [x] Output formats support both human-readable and machine-parseable options (JSON, TSV, CSV support maintained)
- [x] Error message format and actionability requirements defined (PyO3 exception mapping)
- [x] Documentation plan includes comprehensive examples (Python docstrings + README + tutorials)

### Performance Requirements Gates
- [x] Performance benchmarks defined with realistic genomic datasets (1M+ k-mers, 1GB+ files)
- [x] Parallel processing opportunities identified and planned (Rayon integration for batch operations)
- [x] Streaming processing strategy for large files (memory-mapped access maintained)
- [x] Resource limits and monitoring requirements specified (memory constraints, processing time)

## Project Structure

### Documentation (this feature)

```text
specs/001-python-bindings/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── python-api.md    # Python API contract specification
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Python package structure with Rust extension
python/rustkmer/
├── __init__.py          # Public API exports
├── core.py              # Core classes (KmerCounter, Database)
├── fuzzy.py             # Fuzzy query functionality
├── sequence.py          # Sequence handling utilities
├── stats.py             # Statistics and result types
└── exceptions.py        # Custom exception classes

# Rust extension module
src/
├── python/              # PyO3 Python bindings
│   ├── lib.rs           # Python module definitions
│   ├── kmer_counter.rs  # KmerCounter PyO3 bindings
│   ├── database.rs      # Database PyO3 bindings
│   ├── fuzzy_query.rs   # FuzzyQuery PyO3 bindings
│   └── utils.rs         # Utility functions
├── core/                # Existing RustKmer core (reuse)
├── database/            # Existing database module (reuse)
├── fuzzy/               # Existing fuzzy module (reuse)
└── kmer/                # Existing kmer module (reuse)

tests/
├── python/              # Python integration tests
├── rust/                # Rust unit tests
└── integration/         # Cross-language tests

# Build configuration
pyproject.toml           # Python packaging with maturin
Cargo.toml              # Rust dependencies
```

**Structure Decision**: Python package with Rust extension using maturin build system for optimal performance and cross-platform distribution.

## Complexity Tracking

No violations detected. All Constitution Check gates pass with clear rationale for technical decisions. The implementation leverages existing RustKmer architecture while adding minimal Python interface overhead.

### Architecture Justification

**PyO3 Selection**: Chosen over cffi/ctypes for 2-5x better performance, compile-time type safety, and automatic memory management. Research shows 45% speed improvement for bioinformatics operations compared to alternatives.

**Maturin Build System**: Selected for modern Python packaging, excellent cross-platform support (including Apple Silicon), and automated wheel building with cibuildwheel integration.

**Memory-Mapped Database Access**: Maintained from existing RustKmer for optimal performance with large genomic datasets, ensuring Python interface achieves >90% of command-line tool performance.

**Error Handling Strategy**: Uses existing Rust error types (thiserror) mapped to appropriate Python exceptions via PyO3, maintaining Rust's comprehensive error handling while providing Pythonic interface.