---
last_mapped_commit: 511b99e5b23614e60426e04a74bcf91a3c5d1a32
last_mapped_at: 2026-10-07
---
# Coding Conventions

**Analysis Date:** 2026-10-07

## Project Shape

Rust 2021 workspace (single crate at repo root, `Cargo.toml`) plus a separate PyO3 crate under `pyo3/` (`rustkmer-pyo3`, cdylib `pyrustkmer`). Library code lives in `src/`, the CLI entry point in `src/main.rs`, and Python bindings in `pyo3/src/`. CI gates: `cargo fmt --all --check`, `cargo clippy --all-targets -- -D warnings` (both crates), `cargo test` (`.github/workflows/ci.yml`).

## Naming Patterns

**Files:**
- Rust modules: `snake_case`, one concern per file — `src/hash/table.rs`, `src/database/prefix_cache_merge.rs`, `src/cli/commands/count.rs`.
- Domain directories use `mod.rs` as the module root — `src/kmer/mod.rs`, `src/cli/commands/mod.rs`, `pyo3/tests/` uses Python conventions.
- Test files: `<topic>_tests.rs` or `<topic>.rs` — `tests/round_trip_tests.rs`, `tests/golden_tests.rs`, `tests/parallel_count_tests.rs`, `tests/consistency/generators.rs`.
- Python: `test_<topic>.py`, helper `utils.py`, fixtures `conftest.py` — `pyo3/tests/test_counter.py`.

**Functions/Methods:**
- `snake_case`, verb-first, descriptive — `encode_kmer_bytes`, `canonical_kmer_u128`, `resolve_thread_count`, `execute_count`, `query_kmer`, `add_count`.
- Conversion pairs follow `_u64`/`_u128` suffixing to disambiguate width — `encode_kmer`, `encode_kmer_u128` (`src/kmer/encoding.rs`).
- CLI handlers are uniformly `execute_<command>(&Args) -> ProcessingResult<()>` — `src/cli/commands/{count,query,stats,dump,fuzzy,merge,prefix}.rs`.
- Private helpers omit `pub`; only public API items are exported.
- Python functions/attributes: `snake_case` — `query_kmer`, `get_stats`, `fuzzy_query`, `total_matches` (`pyo3/src/*.rs`, `pyo3/tests/*.py`).

**Types:**
- Structs/enums/traits: `PascalCase` — `KmerCounter`, `RKDatabase`, `DatabaseQuery`, `FuzzyQueryEngine`, `PositionMutationConfig`, `LoadMode`.
- Error types always end in `Error` — `KmerError`, `ProcessingError`, `RustKmerError` (`src/error.rs`), `FuzzyError` (`src/fuzzy/mod.rs`), `MergeError` (`src/database/merge_error.rs`), `TempFileError` (`tests/common/temp_files.rs`).
- Result aliases: `*Result<T>` — `ProcessingResult<T>`, `FuzzyResult<T>`, `FuzzyQueryResult<T>`, `TestResult<T>`, `TempFileResult<T>`.
- PyO3 wrapper classes are prefixed `Py` on the Rust side and exported under the same name — `#[pyclass(name = "PyCounter")] pub struct PyCounter` (`pyo3/src/counter.rs`).
- Generic parameters: single uppercase letters (`W: Write`, `P: AsRef<Path>`, `T`).
- Type aliases for tuple shapes get a named alias — `pub type Hit = (PathBuf, usize, String);` (`tests/cjk_check.rs`).

**Variables/Constants:**
- Locals `snake_case`; booleans read as predicates — `is_recursive`, `memory_loaded`, `canonical_mode`, `should_sort`.
- Constants `SCREAMING_SNAKE_CASE` — `MAX_KMER_SIZE_IN_U64`, `MAX_KMER_SIZE_IN_U128` (`src/kmer/encoding.rs`), `CHUNK_SIZE` (`src/cli/commands/count.rs`), `DATABASE_MAGIC`, `DATABASE_VERSION` (`src/database/format.rs`), `LEGACY_PATH` (`tests/legacy_readback_tests.rs`).
- Numeric literals use `_` separators when long — `0x1234_5678_9ABC_DEF0u128`, `1_000_000`, `1GB = 1024 * 1024 * 1024`.
- Enum variants `PascalCase`, often struct-shaped with named fields — `KmerError::InvalidCharacter { pos, char }`, `KmerError::SequenceTooShort { length, min_required, kmer_size }`.

**Test names:**
- Dominant pattern is `test_` prefix + condition: `test_streaming_stats_processor_basic`, `test_create_test_database`, `test_query_kmer` (Rust), `test_create_counter_default_params` (Python).
- Newer plan-era regression tests use outcome-describing names without the prefix: `golden_k21_canon_sorted_matches_manifest`, `legacy_offset42_known_kmer_present`, `differential_threads_1_vs_n`, `deterministic_sorted_output` (`tests/golden_tests.rs`, `tests/parallel_count_tests.rs`).
- Python test classes: `Test<PascalCaseTopic>` — `TestPyCounterBasicCreation`, `TestPyDatabase` (`pyo3/tests/test_counter.py`, `pyo3/tests/test_core.py`).

## Code Style

**Formatting:**
- `rustfmt` with default settings — no `rustfmt.toml` exists; CI enforces `cargo fmt --all --check`. Do not introduce custom formatting.
- 4-space indentation, trailing commas kept, rustfmt wrapping at 100 columns.
- Edition 2021 (`Cargo.toml`, `pyo3/Cargo.toml`).
- Release profile is deliberately tuned: `lto = true`, `codegen-units = 1`, `panic = "abort"` (`Cargo.toml`).

**Linting:**
- CI runs clippy with `-D warnings` for the root crate and `pyo3/` (`.github/workflows/ci.yml`). All new code must be clippy-clean.
- `src/lib.rs:1` and `pyo3/src/lib.rs:1` both enforce `#![deny(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]`.
- The only place that lifts the print denial is `src/cli/mod.rs:1`: `#![allow(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]` — CLI output via `print!`/`eprintln!` is allowed **only** in `src/cli/**`; library code must use `log` instead.
- Localized `#[allow(...)]` is used sparingly with a reason in the adjacent comment — `src/fuzzy/wildcard.rs:239` (`clippy::only_used_in_recursion`), `src/database/prefix_cache_merge.rs:30` (`dead_code`).
- Pre-commit hooks (`.pre-commit-config.yaml`): trailing-whitespace (excluding `.md`), EOF-fixer, check-yaml/json/toml, check-merge-conflict, check-added-large-files; Python hooks (black, isort `--profile black`, pydocstyle Google convention via `.pydocstylerc`, docformatter) are scoped to `^python/.*\.py$`.

**CJK string-literal ban (non-obvious, must follow):**
- Every runtime string literal in `src/` (excluding `src/cli/`) and `pyo3/src/` (excluding dead `*_backup*` / `*new_approaches*` / `*stage1_fix_backup*` files) must be English. Emoji are allowed; Han/Hiragana/Katakana/Hangul literals are rejected by the `tests/cjk_check.rs` source-scanning gate. Doc comments (translated to `#[doc]` attrs) are exempt, but error/log message literals are not. When you find a CJK literal, translate it — do not delete it.

## Import Organization

**Order (observed consistently):**
1. `std` imports (`use std::path::Path;`, `use std::sync::Arc;`) — often multi-line, one per statement.
2. External crates, single group (`use clap::Parser;`, `use rayon::prelude::*;`, `use serde::{Deserialize, Serialize};`, `use thiserror::Error;`).
3. Crate-local (`use crate::error::KmerError;`, `use crate::database::format::RKDatabase;`, `use super::filtering::{CountFilter, FilteringResult};`).

Groups are separated by blank lines; within a group, separate `use` lines (rustfmt does not merge them). Example: `src/cli/commands/count.rs:5-19`.

**Path style:**
- Prefer `use crate::...` over `super::...` for cross-module references; `super::` is used for parent-module items inside a submodule (`src/hash/table.rs:8`, test modules use `use super::*;`).
- Re-exports: short external paths are re-exported at module roots so downstream code imports stable names — `src/lib.rs:34` (`pub use error::{KmerError, ProcessingError, ProcessingResult};`), `src/database/mod.rs:19-26`, `src/fuzzy/mod.rs:33-38`, `pyo3/src/lib.rs:26-31`.
- Deep imports still allowed when explicit — `use rustkmer::database::format::RKDatabase;` in tests.

**No path aliases** beyond the crate name; relative `crate::`/`super::` only.

## Error Handling

**Strategy:** `thiserror` domain enums inside the library; `anyhow` at the application/CLI/test boundary; a bridge `ProcessingError` type carries context across domains.

**Patterns:**
- New error domains get their own `thiserror` enum: `KmerError` (`src/error.rs:8`), `FuzzyError` (`src/fuzzy/mod.rs`), `MergeError` (`src/database/merge_error.rs`), `RustKmerError` (`src/error.rs:118`). Variants have structured fields and `#[error("...")]` messages that include the offending values.
- Fallible public API returns `ProcessingResult<T>` (alias in `src/error.rs:63`) or the domain alias; never return raw `thiserror` enum without a reason.
- Convert with `?` + `From` impls: `impl From<KmerError> for ProcessingError` (`src/error.rs:104`), `KmerError::Io(#[from] std::io::Error)` (`src/error.rs:35`).
- Add context at the call site with `.map_err(...)`: `File::open(path).map_err(|e| KmerError::FileFormatError { file: path_str, reason: format!("Failed to open database: {}", e) })?` (`src/database/query.rs:39-42`), or `ProcessingError::with_context("Failed to write header", e)` (`src/output/text.rs:31`).
- Validate inputs at the top of functions and return early: `if !(1..=64).contains(&kmer_length) { return Err(KmerError::InvalidKmerSize(...).into()); }` (`src/hash/table.rs:55-57`).
- CLI boundary: `fn main() -> anyhow::Result<()>` (`src/main.rs:8`); command handlers return `ProcessingResult<()>` and `?`-propagate; argument validation loops print with `log::error!`/`eprintln!` then `std::process::exit(1)` (`src/main.rs:16-23`).
- `unwrap()`/`expect()` are acceptable only in tests and in cases with a proven invariant, and `expect` gets an explanatory message — `h.join().expect("worker thread panicked in count_input_with_workers")` (`tests/parallel_count_tests.rs`).
- No `todo!()`/`unimplemented!()` anywhere in `src/` or `pyo3/src/`.
- PyO3 layer maps Rust errors to Python exceptions: `PyValueError` for argument validation (`pyo3/src/counter.rs:6`), custom `RustKmerError` pyclass for richer errors (`pyo3/src/errors.rs`).

## Logging

**Framework:** `log` crate (facade) + `env_logger` (CLI init).

**Patterns:**
- Library code logs via `log::info!` / `log::warn!` / `log::error!` / `log::debug!` — 138 call sites, e.g. `src/database/prefix_cache_merge.rs:90-149`. `println!` inside the library is a clippy error by crate-level deny.
- `main.rs` initializes `env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();` (`src/main.rs:13`).
- User-facing CLI progress/verbose output uses `eprintln!` gated behind `--verbose`/`--quiet` flags inside `src/cli/commands/*` (`src/cli/commands/count.rs:135-158`).
- Emoji are common in progress logs (`🚀`, `📊`, `📦` in `src/database/prefix_cache_merge.rs`); keep log output English (CJK gate).

## Comments

**When to Comment:**
- Comment the *why*, not the *what*. This codebase carries unusually detailed rationale comments that cite the originating decision/plan identifiers (e.g. `D-01`, `D-07`, `PCOUNT-04`, `WR-03`, `RESEARCH Pattern 1`) and explicitly warn future editors off unsafe refactors — `src/hash/table.rs:77-92` ("Do NOT split this into `get()` + `insert()`"), `src/cli/commands/count.rs:94-99`, `tests/parallel_count_tests.rs` baseline notes.
- Behavior-preserving constraints are documented inline ("preserved VERBATIM", "byte-identical") — follow this style when touching `.rkdb` format code.
- Comment on non-obvious binary/bit math — `src/kmer/encoding.rs:32-35`.

**Rustdoc:**
- Every module has an `//!` header with a one-line summary plus feature/usage prose — `src/lib.rs`, `src/fuzzy/mod.rs`, `src/database/query.rs`.
- Public items get `///` doc comments using rustdoc sections `# Arguments`, `# Returns`, `# Examples` — `src/kmer/encoding.rs:19-36`, `src/hash/table.rs:37-48`, `src/output/text.rs:10-21`.
- Examples include runnable assertions; non-compiling sketches are marked ` ```rust,ignore ` (`src/lib.rs:11`).
- PyO3 methods document `# Raises` for Python exceptions (`pyo3/src/counter.rs:129-130`).

**Python docstrings:** Google convention (`.pydocstylerc`: `convention = google`, max line 88), module docstring first line, `Args:`/`Returns:` sections in helpers — `pyo3/tests/utils.py`, `pyo3/tests/conftest.py`. pydocstyle rules D100/D105/D107 are ignored.

## Function Design

**Size:** Functions are small-to-medium with early returns; heavy numeric loops and parsing routines are the exception (`PositionMutationConfig::parse`, `src/fuzzy/query.rs`). Keep pure helpers private and named for what they compute (`encode_test_kmer`, `sha256_hex`).

**Parameters:** Prefer `&str` / `&[u8]` / `&Path` borrows over owned; generic readers/writers via `W: Write`, `P: AsRef<Path>` (`src/database/query.rs:37`). CLI args structs are passed by reference (`&Args`).

**Return Values:** `Result` for anything fallible; `Option` for lookups (`query_kmer -> ProcessingResult<Option<u32>>`); `Vec`/iterator otherwise. Test-body convention: `-> anyhow::Result<()>` with `?` and terminal `Ok(())` (see TESTING.md).

## Module Design

**Exports:**
- Each domain has a `mod.rs` that declares submodules in dependency order and re-exports the key types with `pub use` — `src/database/mod.rs:1-26`, `src/fuzzy/mod.rs:25-38`.
- Crate root re-exports the main entry points — `src/lib.rs:33-35` (`pub use error::{...}; pub use hash::KmerCounter;`).
- PyO3 crate keeps modules private (`mod counter;`) and re-exports at `lib.rs` (`pub use counter::{PyCounter, PyCounterStats};`), then registers every class in the `#[pymodule]` fn (`pyo3/src/lib.rs:37-55`).

**Barrel files:** `mod.rs` files are the barrels; no wildcard re-exports at the crate root.

**Shared abstractions:**
- Config structs derive `Default` and are built with struct-update syntax: `DiscoveryConfig { recursive: is_recursive, ..Default::default() }` (`src/cli/commands/count.rs:111-114`).
- Threading: `rayon` for data parallelism (`count.rs` chunked `par_iter`), `std::thread::scope` for explicit worker pools in tests, `parking_lot`/atomics internally; shared state passed as `Arc<T>` (`pyo3/src/counter.rs:111`).
- Stateful engines are structs (`KmerCounter`, `RKDatabase`, `StreamingStatsProcessor`, `DatabaseQuery`); stateless transforms are free functions.
- `#[derive(Debug)]` on public structs; `Clone`, `Serialize`/`Deserialize`, `PartialEq` added as needed (e.g. `#[derive(Debug, Clone, Serialize, Deserialize, Default)]` in `src/fuzzy/query.rs:15`).

**CLI conventions:**
- clap derive API only: `#[derive(Parser)] struct Args`, `#[derive(Subcommand)] enum Commands` (`src/cli/args.rs`). Field doc comments become `--help` text.
- Add flags in `src/cli/args.rs`; implement the command in `src/cli/commands/<name>.rs` with an `execute_<name>` entry point; wire dispatch in `src/main.rs`.
- Backward-compatible aliases are kept in clap (`#[arg(alias = "lower-count")]`) even when behavior changes; retained no-op fields are renamed `_field` to satisfy clippy (`sort: _sort`, `src/cli/commands/count.rs:53`).

## PyO3 Binding Conventions

- Structs exposed to Python carry `#[pyclass(name = "Py...")]`; fields are read via `#[getter]` methods, not `#[pyo3(get)]` (`pyo3/src/counter.rs:29-54`).
- Constructors use `#[new]` + `#[pyo3(signature = (...))]` with Python-side defaults (`pyo3/src/counter.rs:131-133`).
- Python-visible validation raises `PyValueError` with messages matching test expectations ("Invalid k-mer size") (`pyo3/tests/test_counter.py:47-60`).
- Long-running methods release the GIL via `py.allow_threads(...)` (`pyo3/src/counter.rs:105-110`).
- Python tests exercise the built module via `maturin develop`; imports are guarded with `pytest.skip` when the module is absent (`pyo3/tests/test_counter.py:9-12`).

---

*Convention analysis: 2026-10-07*
