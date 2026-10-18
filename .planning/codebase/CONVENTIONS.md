---
last_mapped_at: 2026-10-18
last_mapped_commit: 51629b5ea7ed323cfb60ef0be9cab2f30f6a2ed6
---
# Coding Conventions

**Analysis Date:** 2026-10-18

*Scope: `.github/`, `pyo3/`, `src/`, `tests/` (incremental refresh of the 2026-10-17 full map).*

## Languages

**Primary:** Rust 2021 edition (crate `rustkmer` v0.5.0, `Cargo.toml`)
**Secondary:** Python 3.11+ (PyO3 bindings package `pyo3/`, maturin-built as `pyrustkmer`)

## Naming Patterns

**Files:**
- Rust modules: `snake_case.rs` (e.g., `src/kmer/encoding.rs`, `src/database/prefix_query.rs`)
- Module directories with `mod.rs` re-export pattern (e.g., `src/database/mod.rs`)
- CLI subcommands live one file per command: `src/cli/commands/{query,prefix,merge,fuzzy,benchmark}.rs`
- Python tests: `test_*.py` in `pyo3/tests/`
- Test binaries in `tests/`: `*_tests.rs` suffix (e.g., `round_trip_tests.rs`, `merge_bounded_memory_tests.rs`, `dense_merge_integration_tests.rs`); meta-lints use bare nouns (`cjk_check.rs`, `golden_generate.rs`)

**Functions:**
- `snake_case`; test functions prefixed `test_` (e.g., `test_create_test_database`)
- Constructors follow `from_*` / `new` convention (`RKDatabase::from_kmer_pairs`, `KmerCounter::new`)
- Test-factory and helper names are verb-first: `create_test_database`, `create_overlapping_database`, `encode_test_kmer`, `write_fixture_pair`, `backdate` (`tests/common/mod.rs`, `tests/merge_bounded_memory_tests.rs`)
- Platform-specific measurement helpers keep one name across cfg arms (`current_rss_kb`, `backdate` — each defined once per `#[cfg(target_os = ...)]`)

**Types:**
- `PascalCase` structs/enums: `KmerError`, `RKDatabase`, `KmerCounter`, `ProcessingError`, `PerformanceMetrics` (`tests/common/performance.rs`)
- PyO3 wrapper types prefixed `Py`: `PyDatabase` (`pyo3/src/`)
- Constants: `SCREAMING_SNAKE_CASE` (e.g., `GOLDEN_FIXTURES`, `DENSE_STORED_KEY_BYTES`, `RSS_BOUND_BYTES`, `CHUNK_ENTRIES` in the new merge/dense test binaries)

**Variables:**
- `snake_case`; hex-literal test k-mers use underscore-digit separators: `0x1234_5678_9ABC_DEF0_...u128`, `0x0000_0100` (Windows flag constants)

## Code Style

**Formatting:**
- Standard `rustfmt` defaults; enforced in CI via `cargo fmt --all --check` (`.github/workflows/ci.yml` job `fmt`)
- Numeric literals with type suffixes in tests (`7u32`, `...u128`)

**Linting:**
- `cargo clippy` per CLAUDE.md commands; CI gate runs `cargo clippy --all-targets -- -D warnings` on **ubuntu/macos/windows** matrices for BOTH the root crate (job `clippy-root`) and the pyo3 crate (job `pyo3-build`, working-directory `pyo3`) — new code must be warning-clean on all three OSes
- Crate-level lint gate in `src/lib.rs:1`: `#![deny(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]` — library code must NOT use `println!`/`eprintln!`/`dbg!`; use `log::*!` macros instead
- Localized `#![allow(...)]` / `#[allow(...)]` where justified with a comment (e.g., `#![allow(dead_code)]` in `tests/common/mod.rs:17` with the per-binary-usage rationale written out)
- Python: `ruff check .` (per AGENTS.md); pre-commit runs black (line 88) + isort

## Import Organization

**Order (Rust):**
1. `//!` module doc comment block first, every file
2. `use std::...`
3. `use` external crates (`use anyhow::Result;`, `use sha2::{Digest, Sha256};`, `use tempfile::TempDir;`)
4. `use rustkmer::...` / `use common::*;`

**Path Aliases:**
- None; absolute crate paths (`rustkmer::database::format::RKDatabase`)
- Exception: binaries needing only factories include them directly via `#[path = "common/factories.rs"] mod common;` (documented in `tests/common/mod.rs`) to avoid compiling shared-helper self-tests

## Documentation

**Module docs:**
- Every file starts with `//!` doc comment stating purpose. New test binaries carry extensive multi-paragraph headers explaining the gap/requirement they close: `tests/merge_bounded_memory_tests.rs` cites "Phase 3, plan 03-10, gap G2 (CR-02)" and derives the memory bound; `tests/dense_merge_integration_tests.rs` cites MERGE-01/MERGE-02/DENSE-02/DENSE-03 and decision IDs D-04/D-05; `tests/golden_sha256_tests.rs` cites DENSE-02/D-03/D-10
- The plan/decision-reference convention (e.g., "D-13", "FOUND-04, D-07", "plan 03-06", "T-03-13") is pervasive — cite the originating decision when touching guarded code
- Test headers include "what this test does NOT observe" tables (`tests/golden_sha256_tests.rs`) — keep the observation boundary explicit

**Item docs:**
- `///` doc comments on public items and non-obvious test helpers, frequently multi-paragraph explaining *why* (see `current_rss_kb` and `backdate` cfg arms in `tests/merge_bounded_memory_tests.rs`)

## Error Handling

**Patterns (two-tier, defined in `src/error.rs`):**
- Library code: `KmerError` enum via `thiserror` with `#[error("...")]` display strings and `#[from]` for `io::Error`/`FromUtf8Error`
- Application/pipeline layer: `ProcessingError` struct (manual `Display` + `source` chaining over `anyhow::Error`), with `ProcessingResult<T>` alias and `From<KmerError>` / `From<io::Error>` conversions
- CLI commands use `anyhow::Result` + `.context(...)`
- Rule of thumb: `thiserror` enums in library modules; `anyhow` with context at CLI/orchestration boundaries
- Error display strings are contract: exact error-message text is asserted verbatim in tests — do not reword error messages without running the full suite

**In tests:**
- Prefer returning `anyhow::Result<()>` from `#[test]` fns over `.unwrap()` chains for I/O-heavy tests; use `.unwrap()`/`.expect("reason")` for setup
- Bridge shared-helper `Box<dyn Error>` results into `anyhow` via a local adapter trait (see `TestResultExt` in `tests/round_trip_tests.rs`)
- Helper failure uses `unwrap_or_else(|e| panic!("context: {}", e))` for diagnosability (`backdate` in `tests/merge_bounded_memory_tests.rs`)

## Logging

**Framework:** `log` crate macros + `env_logger` (initialized in CLI entry)

**Patterns:**
- Use `log::info!`/`log::error!`/etc. — never `println!` in `src/` (denied by lint)
- String literals passed to log macros are scanned by the CJK lint gate (below)

## Language / String Literals

- **No CJK characters in string literals** in `src/` (excluding `src/cli/`) or `pyo3/src/` — enforced by the syn-based scanner test `tests/cjk_check.rs` (decision FOUND-04/D-07). Write all user-facing and log strings in English.

## Comments

**When to Comment:**
- Explain *why* (design decision, plan reference, pitfall), not *what*
- Reference plan IDs and decisions: `(03-RESEARCH.md Pitfall 6)`, `decision D-09`, `gap G2 (CR-02)` — used throughout `Cargo.toml` comments, `src/lib.rs`, and test headers
- Measurement-bound derivations must document the arithmetic AND the rejected alternative (see `RSS_BOUND_BYTES` in `tests/merge_bounded_memory_tests.rs`, which explains why 12x headroom, not 4x, and why the withdrawn N-relative bound is absent "by design")
- CI YAML carries decision references inline (`.github/workflows/ci.yml` cache-key comments citing CR-04, security notes citing T-01-SC, gate policy citing FOUND-01/D-04/SPEC P1)

## Function Design

**Parameters:** Builder-style options via clap derive attributes (`#[arg(short, long, default_value_t = true)]` in `src/cli/args.rs`); conflicts expressed declaratively (`conflicts_with`, `requires`)

**Return Values:** `Result<T, KmerError>` / `ProcessingResult<T>` in library; `anyhow::Result<T>` in CLI layer and integration tests

## Module Design

**Exports:**
- `mod.rs` per directory declares submodules and re-exports public API
- `src/lib.rs` re-exports key types (`pub use error::{KmerError, ProcessingError, ProcessingResult}; pub use hash::KmerCounter;`)
- `tests/common/` is a layered helper library: `mod.rs` (facade + self-tests), `factories.rs`, `memory.rs`, `performance.rs`, `temp_files.rs`
- Note: `src/core/database/` exists alongside `src/database/` — check both before adding database code

**Barrel Files:** `mod.rs` acts as the module's barrel; deep paths like `rustkmer::database::format::RKDatabase` are used explicitly in tests

## Platform-Conditional Code

- OS-specific test helpers are expressed as same-named functions under `#[cfg(target_os = "...")]` arms, with a portable fallback under `#[cfg(not(any(linux, windows)))]` (macOS) — pattern in `tests/merge_bounded_memory_tests.rs` (`current_rss_kb`: `/proc/self/status` on Linux, `ps -o rss=` elsewhere) and `backdate` (`FileTimes` on Unix, `OpenOptionsExt` + `FILE_FLAG_BACKUP_SEMANTICS` on Windows); also `tests/dense_memory_tests.rs` (`#[cfg(target_os = "linux")]` measurement tests) and `tests/merge_cleanup_tests.rs:172` (Windows arm)
- Rationale: a memory bound that never runs on the developer's machine proves nothing (RED discipline demands executable measurement wherever tests run)

## Testing Conventions

See TESTING.md for the full testing pattern reference.

---

*Convention analysis: 2026-10-18*
