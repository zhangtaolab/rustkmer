---
last_mapped_commit: 0f442541636e002a322db9d1ba091ff046e62284
last_mapped_at: 2026-10-08
---
# Coding Conventions

**Analysis Date:** 2026-10-08

## Languages

**Primary:** Rust 2021 edition (crate `rustkmer` v0.5.0, `Cargo.toml`)
**Secondary:** Python 3.11+ (PyO3 bindings package `pyo3/`, maturin-built as `pyrustkmer`)

## Naming Patterns

**Files:**
- Rust modules: `snake_case.rs` (e.g., `src/kmer/encoding.rs`, `src/database/prefix_query.rs`)
- Module directories with `mod.rs` re-export pattern (e.g., `src/database/mod.rs`)
- CLI subcommands live one file per command: `src/cli/commands/{query,prefix,merge,fuzzy,benchmark}.rs`
- Python tests: `test_*.py` in `pyo3/tests/`
- Test binaries in `tests/`: `*_tests.rs` suffix (e.g., `round_trip_tests.rs`, `dense_proptest_tests.rs`); meta-lints use bare nouns (`cjk_check.rs`, `golden_generate.rs`)

**Functions:**
- `snake_case`; test functions prefixed `test_` (e.g., `test_create_test_database`, `test_query_kmer`)
- Constructors follow `from_*` / `new` convention (`RKDatabase::from_kmer_pairs`, `KmerCounter::new`)
- Test-factory names are verb-first: `create_test_database`, `create_overlapping_database`, `encode_test_kmer`, `generate_kmer_sequence` (`tests/common/mod.rs`)

**Types:**
- `PascalCase` structs/enums: `KmerError`, `RKDatabase`, `KmerCounter`, `ProcessingError`
- PyO3 wrapper types prefixed `Py`: `PyDatabase` (`pyo3/src/`)
- Constants: `SCREAMING_SNAKE_CASE` (e.g., `DENSE_K: &[usize]` in `tests/dense_proptest_tests.rs`)

**Variables:**
- `snake_case`; hex-literal test k-mers use underscore-digit separators: `0x1234_5678_9ABC_DEF0_...u128`

## Code Style

**Formatting:**
- Standard `rustfmt` defaults; no custom `rustfmt.toml` detected
- Numeric literals with type suffixes in tests (`7u32`, `...u128`)

**Linting:**
- `cargo clippy` (per CLAUDE.md commands)
- Crate-level lint gate in `src/lib.rs:1`: `#![deny(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]` — library code must NOT use `println!`/`eprintln!`/`dbg!`; use `log::*!` macros instead
- Localized `#![allow(...)]` where justified with a comment (e.g., `#![allow(dead_code)]` in `tests/common/mod.rs:10`, `#![allow(clippy::needless_borrow)]` in `tests/cjk_check.rs`)
- Python: `ruff check .` (per AGENTS.md)

## Import Organization

**Order (Rust):**
1. `//!` module doc comment block first, every file
2. `use std::...`
3. `use` external crates (`use clap::...`, `use proptest::prelude::*;`)
4. `use rustkmer::...` / `use common::*;`

**Path Aliases:**
- None; absolute crate paths (`rustkmer::database::format::RKDatabase`)

## Documentation

**Module docs:**
- Every file starts with `//!` doc comment stating purpose, often referencing plan/decision IDs (`//! Plan 01-03, Task 2 (decision D-09, SPEC R3 acceptance).` in `tests/round_trip_tests.rs`)
- This plan-reference convention (e.g., "D-13", "FOUND-04, D-07", "plan 03-06") is pervasive — cite the originating decision when touching guarded code

**Item docs:**
- `///` doc comments on public items and non-obvious test helpers, frequently multi-paragraph explaining *why* (see `tests/cjk_check.rs`, `tests/dense_proptest_tests.rs` headers)

## Error Handling

**Patterns (two-tier, defined in `src/error.rs`):**
- Library code: `KmerError` enum via `thiserror` with `#[error("...")]` display strings and `#[from]` for `io::Error`/`FromUtf8Error`
- Application/pipeline layer: `ProcessingError` struct (manual `Display` + `source` chaining over `anyhow::Error`), with `ProcessingResult<T>` alias and `From<KmerError>` / `From<io::Error>` conversions
- A second thiserror enum `RustKmerError` covers queryx/database paths
- CLI commands use `anyhow::Result` + `.context(...)` (e.g., `src/cli/commands/stats.rs`, `src/config/manager.rs`)
- Rule of thumb: `thiserror` enums in library modules; `anyhow` with context at CLI/ orchestration boundaries
- Error display strings are contract: external-sort compatibility error text is asserted verbatim in tests (commit dc1c25a) — do not reword error messages without checking `tests/`

**In tests:**
- Prefer returning `anyhow::Result<()>` from `#[test]` fns over `.unwrap()` chains for I/O-heavy tests; use `.unwrap()`/`.expect("reason")` for setup
- Bridge shared-helper `Box<dyn Error>` results into `anyhow` via a local adapter trait (see `TestResultExt` in `tests/round_trip_tests.rs`)

## Logging

**Framework:** `log` crate macros + `env_logger` (initialized in CLI entry)

**Patterns:**
- Use `log::info!`/`log::error!`/etc. — never `println!` in `src/` (denied by lint)
- Heaviest logging: `src/database/prefix_cache_merge.rs`, `src/database/format.rs`
- Note: string literals passed to log macros are scanned by the CJK lint gate (below)

## Language / String Literals

- **No CJK characters in string literals** in `src/` (excluding `src/cli/`) or `pyo3/src/` (excluding dead `*backup*` files) — enforced by the syn-based scanner test `tests/cjk_check.rs` (decision FOUND-04/D-07). Write all user-facing and log strings in English.

## Comments

**When to Comment:**
- Explain *why* (design decision, plan reference, pitfall), not *what*
- Reference plan IDs and decisions: `(03-RESEARCH.md Pitfall 6)`, `Phase 2; PCOUNT-02`, `decision D-09` — used throughout `Cargo.toml` comments, `src/lib.rs`, and test headers
- Cargo.toml dependency comments document promotion rationale (see `tempfile` entry in `Cargo.toml`)

## Function Design

**Parameters:** Builder-style options via clap derive attributes (`#[arg(short, long, default_value_t = true)]` in `src/cli/args.rs`); conflicts expressed declaratively (`conflicts_with`, `requires`)

**Return Values:** `Result<T, KmerError>` / `ProcessingResult<T>` in library; `anyhow::Result<T>` in CLI layer

## Module Design

**Exports:**
- `mod.rs` per directory declares submodules and re-exports public API
- `src/lib.rs` re-exports key types (`pub use error::{KmerError, ProcessingError, ProcessingResult}; pub use hash::KmerCounter;`) with historical notes when types are removed
- Note: `src/core/database/` exists alongside `src/database/` — check both before adding database code

**Barrel Files:** `mod.rs` acts as the module's barrel; deep paths like `rustkmer::database::format::RKDatabase` are used explicitly in tests

## Testing Conventions

See TESTING.md for the full testing pattern reference.

---

*Convention analysis: 2026-10-08*
