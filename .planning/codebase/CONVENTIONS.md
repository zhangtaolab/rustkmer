# Coding Conventions

**Analysis Date:** 2026-06-30

This is a **hybrid Rust + Python codebase**. The Rust crate `rustkmer` (CLI + library, `src/`) is the core; the `pyo3/` crate (`pyrustkmer`) wraps it as a Python extension module via PyO3 + maturin. Conventions differ per language and are documented separately below.

## Languages

- **Rust 1.80+ stable** — primary crate `rustkmer` (`src/`) and PyO3 wrapper crate `rustkmer-pyo3` (`pyo3/src/`).
- **Python 3.11+** — `pyrustkmer` consumers, test suites (`pyo3/tests/`, `tests/` Python dirs), examples, and tooling scripts.

## Project Layout (language split)

| Concern | Location | Language |
|---------|----------|----------|
| Core library | `src/lib.rs` + `src/<module>/` | Rust |
| CLI binary | `src/main.rs`, `src/cli/` | Rust |
| Python bindings | `pyo3/src/` (crate `pyrustkmer`) | Rust + PyO3 |
| Rust integration/property tests | `tests/` (coordinated via `tests/mod.rs`) | Rust |
| Python tests for bindings | `pyo3/tests/` | Python |
| Cross-validation Python tests | `tests/007-api-compatibility/`, `tests/converted/` | Python |
| Examples | `examples/python/`, `examples/application/`, `examples/bash/` | Python / Bash |

## Naming Patterns

### Rust

**Files:** `snake_case.rs`. Module aggregations live in `mod.rs` per directory (e.g. `src/cli/mod.rs`, `src/database/mod.rs`).
- Examples: `src/kmer/encoding.rs`, `src/database/prefix_query_optimized.rs`, `src/cli/commands/count.rs`.

**Types (structs/enums):** `UpperCamelCase`.
- Examples: `KmerCounter` (`src/hash/table.rs:14`), `RKDatabase` (`src/database/format.rs`), `DatabaseHeader`, `KmerError` (`src/error.rs:9`), `ProcessingError` (`src/error.rs:67`), `Commands` (`src/cli/args.rs:17`).

**Functions/methods:** `snake_case`. Public command entry points follow `execute_<command>` naming: `execute_count`, `execute_query`, `execute_stats`, `execute_dump`, `execute_merge`, `execute_fuzzy_query`, `execute_prefix_query` (see `src/cli/commands/*.rs`).

**Constants:** `SCREAMING_SNAKE_CASE`.
- Examples: `DATABASE_MAGIC`, `DATABASE_VERSION` (`src/database/format.rs`), `MAX_KMER_SIZE_IN_U64`, `MAX_KMER_SIZE_IN_U128` (`src/kmer/encoding.rs:14-17`), single-base codes `A`, `C`, `G`, `T` (`src/kmer/encoding.rs:8-11`).

**Module-private type aliases:** short `Result<T>` style with module-local error type, e.g. `pub type ProcessingResult<T> = Result<T, ProcessingError>;` (`src/error.rs:63`).

**PyO3 wrapper types:** prefixed `Py` — `PyCounter`, `PyDatabase`, `PyFuzzyQuery`, `PyPrefixQuery`, `PyFormatter` (`pyo3/src/lib.rs:25-30`). Stats/result companions are suffixed `Stats`/`Result`: `PyCounterStats`, `PyQueryResult`, `PyFuzzyResult`.

### Python

**Files:** `snake_case.py` for modules, `test_*.py` for tests (`pyo3/tests/test_counter.py`, `test_export.py`, `test_import.py`).

**Classes:** `UpperCamelCase`, grouped into `Test*` suites per behavior (e.g. `TestPyCounterBasicCreation`, `TestPyCounterAddKmer` in `pyo3/tests/test_counter.py`).

**Functions/methods:** `snake_case`; test functions prefixed `test_`.

**Docstrings:** **Google convention** enforced via `pydocstyle` (`.pydocstylerc` → `convention = google`). Helper modules use Args/Returns/Raises sections (see `pyo3/tests/utils.py:7-16`, `pyrustkmer/` runtime modules).

## Code Style

### Rust formatting & linting

- **No `rustfmt.toml` or `clippy.toml` present** — default `cargo fmt` / `cargo clippy` settings apply. Run both locally; `cargo clippy` is listed in `CLAUDE.md` Commands.
- Standard 4-space indent, trailing commas on multi-line constructs.
- **Edition 2021** (`Cargo.toml:4`, `pyo3/Cargo.toml:4`).
- **Release profile** is tuned for the production binary (`Cargo.toml:101-104`): `lto = true`, `codegen-units = 1`, `panic = "abort"`. Preserve these when touching `[profile.release]`.
- `#[allow(dead_code)]` is applied to fixture generators that are referenced only from some test configs (e.g. `tests/consistency/generators.rs:6,17,44`) — do not remove without verifying no test references them.

### Python formatting & linting

- **`black`** — line length **88** (`pyo3/pyproject.toml:108-110`, `.pre-commit-config.yaml` `black` rev 24.1.1). Target version `py311`.
- **`isort`** with `--profile black` (`.pre-commit-config.yaml`).
- **`mypy`** strict mode (`pyo3/pyproject.toml:127-140`): `disallow_untyped_defs`, `disallow_incomplete_defs`, `no_implicit_optional`, `warn_unreachable`, etc. New Python in `pyo3/` should be fully typed.
- **`pydocstyle` (Google)** + **`docformatter --black`** via pre-commit (`.pre-commit-config.yaml`).
- **`ruff`** is also installed (`.ruff_cache/` present; referenced in `AGENTS.md` as `ruff check .`).
- pre-commit hooks are configured in `.pre-commit-config.yaml` (trailing-whitespace, end-of-file-fixer, check-yaml/json/toml, large-file guard).

## Import Organization

### Rust

Order observed across `src/`:
1. External crates (`use anyhow::...`, `use byteorder::...`, `use parking_lot::RwLock as ParkingLotRwLock;`, `use pyo3::prelude::*;`).
2. `std::*` (`use std::path::Path;`, `use std::sync::Arc;`).
3. `crate::*` (`use crate::error::{KmerError, ProcessingResult};`, `use crate::database::format::...`).
4. `super::*` inside submodules (`use super::filtering::{CountFilter, FilteringResult};`).

Type renames for disambiguation use `as`: `use parking_lot::RwLock as ParkingLotRwLock;` (`src/hash/table.rs:6`), `use rustkmer::hash::KmerCounter as RustPyCounter;` (`pyo3/src/counter.rs:8`).

### Python

- `isort` (black profile) groups: stdlib → third-party → local.
- `from __future__` imports not used (Python 3.11+ baseline).
- PyO3 tests guard the native import: `try: import pyrustkmer / except ImportError: pytest.skip(...)` (`pyo3/tests/test_counter.py:10-13`).

**Path aliases:** none. Python imports the compiled module by name `pyrustkmer` (set via `[tool.maturin] module-name` in `pyo3/pyproject.toml:77`).

## Error Handling

### Rust — layered strategy

The crate distinguishes **typed library errors** from **contextual application errors** (`src/error.rs`):

1. **`KmerError`** (`src/error.rs:9-60`) — `#[derive(Debug, thiserror::Error)]` enum. Use for type-safe, domain-specific failure modes (`InvalidKmerSize`, `InvalidCharacter`, `SequenceTooShort`, `FileFormatError`, `HashTableOverflow`, `TooManyVariants`, …). `#[error("...")]` attributes carry human-readable messages; `#[from]` is used for `std::io::Error` and `FromUtf8Error`.
2. **`RustKmerError`** (`src/error.rs:117-148`) — second thiserror enum for query/database path errors.
3. **`ProcessingError`** (`src/error.rs:67-108`) — application-level struct wrapping `anyhow::Error` with a message + optional source chain. Built via `ProcessingError::new(...)` or `ProcessingError::with_context(msg, err)`. Convenience constructors: `io_error`, `database_error`, `query_error`.
4. **`ProcessingResult<T>`** = `Result<T, ProcessingError>` (`src/error.rs:63`) — preferred return type for library functions that may fail (e.g. `KmerCounter::new`, `increment` in `src/hash/table.rs`).
5. **`anyhow::Result<T>`** — used in CLI command modules and config (`src/cli/commands/fuzzy.rs:8`, `src/cli/commands/merge.rs:53`, `src/config/manager.rs:6`). `anyhow::Context` is `.with_context(...)`-ed at boundaries.

**Conversion flow:** `KmerError` → `ProcessingError` via `impl From<KmerError>` (`src/error.rs:104-108`); `io::Error` likewise (`src/error.rs:110-114`). Library code returns `Err(KmerError::...).into()` so callers see a `ProcessingError`.

**Anti-pattern guidance (prescriptive):**
- DO return `ProcessingResult<T>` / `Result<T, KmerError>` from library code; convert with `.into()` or `?`.
- DO NOT use `.unwrap()` in library code paths reachable from Python (`pyo3/`) — convert errors to `PyErr` (see below). Production `unwrap()` count in `src/database/format.rs` is non-zero; new code should use `?` instead.
- DO validate at boundaries: e.g. `execute_count` re-checks `*k < 1 || *k > 64` and returns `KmerError::InvalidKmerSize` even though clap parses the value (`src/cli/commands/count.rs:42-44`).
- DO collect multiple validation errors before failing (`args.command.validate_filtering()` / `validate_input()` in `src/cli/commands/count.rs:50-67`), echoing each to stderr.

### PyO3 → Python error bridging

- PyO3 wrappers convert Rust errors to Python exceptions via `PyErr`/`PyResult<T>` (`pyo3/src/counter.rs:6,126`).
- Invalid input raises `PyValueError` with a `match=`-able message, e.g. `"Invalid k-mer size"` (`pyo3/src/counter.rs:129-130`, matched in `pyo3/tests/test_counter.py:49-60`).
- A custom exception `RustKmerError` is exported as a `#[pyclass]` with `message` and `error_type` fields (`pyo3/src/errors.rs:9-42`, registered in `pyo3/src/lib.rs:52`).

### Python

- Tests assert failures with `pytest.raises(ValueError, match="...")` (`pyo3/tests/test_counter.py:48-60`).
- Helper utilities swallow broad `Exception` only when probing optional behaviour (`pyo3/tests/utils.py:37-39, 154`); prefer specific exception types in production code.

## Logging

**Rust:** the `log` facade + `env_logger` (`Cargo.toml:82-84`). Initialized in `src/main.rs:13` with default filter `info`. Emit via fully-qualified `log::debug!`, `log::info!`, etc. (pattern in `src/core/monitoring.rs:161,317,373`). Do NOT use the bare `debug!`/`info!` macros (they are not imported).

**User-facing progress/reporting** is handled by `indicatif` (progress bars) and `inquire` (interactive prompts), not by `log`. CLI `--quiet` / `--verbose` flags toggle these (see `src/cli/args.rs`).

**Warning fallbacks:** some hot paths still use `eprintln!("Warning: ...")` (e.g. `src/kmer/operations.rs:54`). Prefer the `log` facade for new code; reserve `eprintln!` for CLI-only diagnostics.

**Python:** pytest logs are configured per-suite (`tests/converted/pytest.ini` → `log_cli = true`, level INFO, timestamped format).

## Comments & Documentation

### Rust doc comments

- **Module-level:** every `.rs` starts with `//!` block describing purpose, often with a one-line summary followed by detail and `# Examples`. See `src/lib.rs:1-18`, `src/hash/table.rs:1-5`, `src/kmer/encoding.rs:1-4`.
- **Item docs:** `///` on every public item. Follow the **# Arguments / # Returns / # Errors / # Raises / # Examples** section convention (see `KmerCounter::increment`, `src/hash/table.rs:60-91`, and PyO3 `PyCounter::new` at `pyo3/src/counter.rs:112-126`).
- **Doc examples:** use ` ```rust ` (or ` ```rust,ignore ` for things requiring files) and keep them runnable for doctests — `encode_kmer` (`src/kmer/encoding.rs:28-36`) and `extract_kmers` (`src/kmer/operations.rs:19-25`) are good templates. PyO3 wrappers show ` ```python ` blocks (e.g. `pyo3/src/counter.rs:77-103`).
- Field docs use `///` on struct fields (`src/hash/table.rs:15-26`, `pyo3/src/counter.rs:18-27`).

### Python docstrings

- **Google style** (enforced). Public helpers document Args/Returns/Raises (`pyo3/tests/utils.py`, `pyrustkmer/` runtime).
- Test methods carry one-line docstrings describing the behaviour under test (`pyo3/tests/test_counter.py:19,26,...`).

## Function Design

**Size:** No enforced limit; the largest source files are `src/database/format.rs` (1306 lines) and `src/database/prefix_cache_merge.rs` (961). CLI command dispatch (`src/main.rs`) is a flat `match` — when adding a subcommand, add a new match arm plus a dedicated `execute_<command>` in `src/cli/commands/`.

**Parameters:** prefer `impl Into<String>` for message construction (`ProcessingError::new`, `src/error.rs:73`). Use explicit borrows (`&str`, `&[u8]`, `&Path`) for inputs; return owned `String`/`Vec` for outputs.

**Return values:**
- Fallible library functions → `ProcessingResult<T>` or `Result<T, KmerError>`.
- PyO3 methods → `PyResult<T>`.
- CLI entry points → `anyhow::Result<()>` (`fn main`, `execute_*`).
- Lookups that may be absent → `Option<u32>` (e.g. `KmerCounter::get_count`, `src/hash/table.rs:100-103`).

**Validation:** perform at the constructor / boundary, not deep inside hot loops (see `KmerCounter::new` range check `src/hash/table.rs:46-48`).

## Module Design

**Exports:** each `mod.rs` re-exports key types. `src/lib.rs:32-34` re-exports `KmerError`, `ProcessingError`, `ProcessingResult`, `KmerCounter`. `pyo3/src/lib.rs:24-30` re-exports every `Py*` wrapper. Mirror this pattern when adding modules.

**Barrel files:** not used — Rust relies on `pub mod` + `pub use` re-exports rather than barrel-style aggregation.

**Module separation by concern** (see `src/`):
- `error.rs` — error taxonomy (single source of truth for `KmerError`/`ProcessingError`).
- `hash/` — concurrent counting primitives.
- `kmer/` — encoding/decoding/canonical/validation/operations.
- `io/` — FASTA/FASTQ parsing, file discovery, memory mapping.
- `database/` — RKDB binary format, queries, merge, index, stats.
- `fuzzy/` — fuzzy/wildcard query, mutation expansion.
- `cli/` — clap argument tree (`args.rs`) + command implementations (`commands/`).
- `core/` — metadata, monitoring, persistence helpers.
- `config/`, `memory/`, `output/` — configuration, memory-efficiency, output formatting.

**PyO3 mirror:** each Python-facing type has its own file under `pyo3/src/` (`counter.rs`, `database.rs`, `fuzzy_query.rs`, `prefix_query.rs`, `formatter.rs`, `errors.rs`, `utils.rs`) and is registered in the `#[pymodule] fn pyrustkmer` (`pyo3/src/lib.rs:36-54`). New Python-visible classes MUST be added both as `pub use` (line 25-30) and `m.add_class::<...>()?` (line 38-52).

## Versioning & Release Conventions

- Single source version per crate: `Cargo.toml` `version = "0.5.0"` (root) and `pyo3/Cargo.toml` `version = "0.5.0"`, mirrored in `pyo3/pyproject.toml`.
- Keep versions in sync via `scripts/sync_versions.sh` (referenced in `VERSION.md`). When bumping, update all three files together.
- CLI version is dynamic: `#[command(version = env!("CARGO_PKG_VERSION"))]` (`src/cli/args.rs:10`) — do not hard-code.

## Pre-commit & CI Hooks

`.pre-commit-config.yaml` runs: trailing-whitespace (excluding `.md`), end-of-file-fixer, check-yaml/json/toml, merge-conflict/case-conflict guards, large-file guard, then `black`, `isort`, `pydocstyle`, `docformatter` scoped to `python/.*\.py$`. The local `check-docstring-coverage` hook is warn-only.

CI workflows (`.github/workflows/`): `docs.yml`, `performance-regression.yml`. No CI matrix test workflow was detected — local `cargo test` + `pytest` are the source of truth.

---

*Convention analysis: 2026-06-30*
