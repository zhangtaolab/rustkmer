---
last_mapped_commit: 51629b5ea7ed323cfb60ef0be9cab2f30f6a2ed6
last_mapped_at: 2026-10-18
---
# Codebase Structure

**Analysis Date:** 2026-10-18

## Directory Layout

```
rustkmer/                     # Workspace root (main crate `rustkmer` v0.5.0)
├── src/                      # Core Rust library + CLI binary
│   ├── cli/                  # clap args and command handlers
│   │   └── commands/         # One file per subcommand (benchmark.rs removed)
│   ├── core/                 # Metadata, monitoring, database persistence
│   ├── config/               # Config manager
│   ├── database/             # RKDB format, index, query, merge engine, temp lifecycle
│   ├── fuzzy/                # Fuzzy/mutation query engine
│   ├── hash/                 # KmerCounter (dense/wide DashMap) and counting support
│   ├── io/                   # FASTA/FASTQ (MultiGzDecoder), mmap, discovery
│   ├── kmer/                 # Encoding, canonicalization, validation
│   ├── memory/               # Memory efficiency helpers
│   ├── output/               # Binary/text writers
│   ├── lib.rs                # Library root (rlib), module decls + re-exports
│   ├── main.rs               # CLI binary entry point
│   └── error.rs              # KmerError/ProcessingError
├── pyo3/                     # Separate crate: Python bindings (`pyrustkmer` cdylib)
│   ├── src/                  # PyO3 wrappers (PyDatabase with merge kwargs, PyCounter, ...)
│   └── tests/                # pytest suite for the Python API
├── tests/                    # Rust integration tests (root crate)
│   ├── unit/  integration/  contract/  property/  consistency/
│   ├── performance/  converted/  fixtures/  common/
│   └── *.rs                  # Top-level test binaries (golden, merge, dense, ...)
├── tools/                    # `rustkmer-debug-tools` crate (3 standalone bins)
├── examples/                 # python/, bash/, utils/, application/ examples
├── docs/                     # MkDocs documentation (mkdocs.yml at root)
├── scripts/                  # Shell helpers + scripts/bench/ (benchmark gate)
├── test_data/                # kmers/ and sequences/ fixtures
├── .github/workflows/        # ci.yml (clippy/test on ubuntu/macos/windows), benchmark.yml, docs.yml
├── .planning/                # GSD planning artifacts (codebase/, phases/, research/)
└── Cargo.toml                # Single main crate + [[bin]] rustkmer (no workspace)
```

## Directory Purposes

**`src/`:**
- Purpose: all core logic; both rlib and CLI binary
- Contains: 10 module directories plus `lib.rs`, `main.rs`, `error.rs`
- Key files: `src/hash/table.rs` (KmerCounter), `src/database/format.rs` (RKDB format), `src/cli/args.rs` (Commands enum)

**`src/cli/commands/`:**
- Purpose: subcommand implementations
- Contains: `count.rs`, `query.rs`, `stats.rs`, `dump.rs`, `fuzzy.rs`, `merge.rs`, `prefix.rs`, `args.rs` (`benchmark.rs` deleted)
- Pattern: each exposes `execute_<command>(&Args)` (plus `FuzzyQueryArgs` struct in `fuzzy.rs`)

**`src/database/`:**
- Purpose: RKDB persistence and merge engine — the largest module cluster
- Key files: `format.rs` (header/format, dense KmerKey storage), `prefix_cache_merge.rs` (external sort), `streaming_merge.rs`, `merge_config.rs` (routing/admission/MergeStats), `temp_lifecycle.rs` (RAII temp subdirs + stale-shard sweep), `merge_tests.rs` (inline `#[cfg(test)]` module)
- Query paths: `query.rs`, `prefix_query.rs`, `prefix_query_optimized.rs`, `suffix_query.rs`, `index.rs`

**`src/hash/`:**
- Purpose: counting engine
- Key files: `table.rs` (`KmerCounter` with `CounterTable::{Dense(u64), Wide(u128)}` DashMap arms), `filtering.rs`, `overflow.rs`, `matrix.rs`

**`pyo3/`:**
- Purpose: PyO3 Python bindings crate (`pyrustkmer`), versioned in lockstep (0.5.0)
- Contains: `src/lib.rs` (pymodule), `database.rs` (incl. `PyDatabase.merge` kwargs), `counter.rs`, `fuzzy_query.rs`, `prefix_query.rs`, `formatter.rs`, `errors.rs`, `utils.rs`; `build.rs`, `pyproject.toml`, `build_with_python.sh`
- Note: contains `*.stage1_fix_backup` / `database_backup.rs` / `database_new_approaches.rs` dead copies — do not treat backups as source

**`tests/`:**
- Purpose: Rust integration test binaries run by `cargo test`
- Contains: category subdirs (`unit/`, `integration/`, `contract/`, `property/`, `consistency/`, `performance/`, `converted/`) plus root-level test files: golden (`golden_tests.rs`, `golden_sha256_tests.rs`, `golden_generate.rs`), merge suites (`merge_routing_tests.rs`, `merge_route_parity_tests.rs`, `merge_cleanup_tests.rs`, `merge_bounded_memory_tests.rs`, `merge_frontend_validation_tests.rs`, `prefix_cache_conservation_tests.rs`, `prefix_cache_output_order_tests.rs`), dense suites (`dense_differential_tests.rs`, `dense_memory_tests.rs`, `dense_merge_integration_tests.rs`, `dense_proptest_tests.rs`), `parallel_count_tests.rs`, `round_trip_tests.rs`, `legacy_readback_tests.rs`, `cjk_check.rs`, and `common/`, `fixtures/`, `mod.rs`

**`.github/workflows/`:**
- Purpose: CI/CD pipelines
- Contains: `ci.yml` (fmt, clippy `-D warnings`, and tests on ubuntu/macos/windows-latest; pyo3 clippy + wheel job), `benchmark.yml` (BENCH-01 RSS regression gate via `scripts/bench/compare.py`; wall axis advisory), `docs.yml` (MkDocs deploy)

**`tools/`:**
- Purpose: standalone debug binaries (crate `rustkmer-debug-tools`, no deps)
- Contains: `debug_canonical_trace.rs`, `analyze_database.rs`, `verify_canonical.rs`

**`docs/`:**
- Purpose: MkDocs site (user guide, API reference, tutorials, dev guide, performance)
- Config: `mkdocs.yml` at repo root

**`examples/`:**
- Purpose: runnable Python/Bash examples (`examples/python/demo_pyo3_binding.py`, etc.)

**`scripts/`:**
- Purpose: shell utilities — `sync_versions.sh`, `test_all_envs.sh`, `benchmark_prefix_vs_fuzzy.sh`; `scripts/bench/compare.py` is the benchmark gate's single source of truth for exit codes

## Key File Locations

**Entry Points:**
- `src/main.rs`: CLI binary (clap Parser, command dispatch)
- `src/lib.rs`: library root; module declarations and re-exports (`pub use hash::KmerCounter`, `pub use error::{KmerError, ProcessingError, ProcessingResult}`)
- `pyo3/src/lib.rs`: Python module registration (`#[pymodule]`)

**Configuration:**
- `Cargo.toml`: main crate deps, release profile (lto, codegen-units=1, panic=abort), features (`profiling`)
- `pyo3/Cargo.toml` + `pyo3/pyproject.toml` + `pyo3/build.rs`: Python extension build
- `tools/Cargo.toml`: debug tools crate
- `.github/workflows/*.yml`: CI, benchmark gate, docs deploy
- `mkdocs.yml`: docs site config

**Core Logic:**
- `src/hash/table.rs`: `KmerCounter` (counting engine, dense/wide storage)
- `src/kmer/encoding.rs`, `src/kmer/canonical.rs`: 2-bit encoding and canonical k-mers
- `src/database/format.rs`: RKDB binary format (42-byte header)
- `src/database/temp_lifecycle.rs`: merge temp RAII + orphan sweep
- `src/fuzzy/query.rs`: fuzzy query engine

**Testing:**
- `tests/` (Rust integration), `src/database/merge_tests.rs` (inline), `pyo3/tests/` (pytest)
- Test fixtures: `tests/fixtures/`, `test_data/sequences/`, `test_data/kmers/`

## Naming Conventions

**Files:**
- Rust modules: `snake_case.rs`, one module per file with `mod.rs` as directory index (`src/database/mod.rs` declares and re-exports submodules)
- CLI command files named after the subcommand: `count.rs` → `Commands::Count`
- Test binaries: `*_tests.rs` for suites, `golden_*` for golden files, `<topic>_proptest_tests.rs` for proptest suites, `<topic>_bounded_memory_tests.rs` for budget-gated suites

**Directories:**
- `snake_case`, plural for collections (`commands/`, `examples/`, `fixtures/`)
- Test categories as directories under `tests/` (`unit/`, `integration/`, `contract/`, `property/`)

**Backups:**
- `*.stage1_fix_backup` suffix and `*_backup.rs` / `*_new_approaches.rs` files in `pyo3/src/` mark dead copies pending deletion — never edit or import from them

## Where to Add New Code

**New CLI subcommand:**
1. Add variant to `Commands` enum in `src/cli/args.rs`
2. Add dispatch arm in `src/main.rs`
3. Implement `execute_<command>(&Args)` in `src/cli/commands/<command>.rs`
4. Declare module in `src/cli/commands/mod.rs`

**New library module:**
- Create `src/<module>/mod.rs` + submodule files; add `pub mod <module>;` to `src/lib.rs`; re-export key types from `src/lib.rs`

**New database/query feature:**
- Query paths go in `src/database/`; keep the RKDB header (`src/database/format.rs`) and merge routing (`src/database/merge_config.rs`) in sync with any format change
- Any new merge temp usage must go through `src/database/temp_lifecycle.rs` (RAII subdir under the `rustkmer-merge-` prefix so the sweep catches it)

**New Python API surface:**
- Add `#[pyclass]`/`#[pyfunction]` in `pyo3/src/` (e.g. `pyo3/src/database.rs`), register in `pyo3/src/lib.rs` `#[pymodule]`, add pytest in `pyo3/tests/`
- Use `#[pyo3(signature = (...))]` for keyword-arg APIs (pattern: `PyDatabase::merge`, `pyo3/src/database.rs:1370`)

**New Rust integration test:**
- Root-level suite: `tests/<topic>_tests.rs` (or a category subdir); shared helpers in `tests/common/`
- Declare new category dirs in `tests/mod.rs` (`pub mod <category>;`)

**New debug tool:**
- Add `[[bin]]` entry in `tools/Cargo.toml` with `tools/<name>.rs` (keep zero deps)

**New CI gate / workflow change:**
- Add to `.github/workflows/`; clippy/test matrices cover ubuntu/macos/windows-latest — keep new code compiling on all three
- Never add error-swallowing flags or exit-code laundering to `benchmark.yml` (gate semantics live only in `scripts/bench/compare.py`)

**Utilities:**
- Shared helpers: `tests/common/`; Python-side: `pyo3/tests/utils.py`, `examples/utils/`

## Special Directories

**`target/`, `pyo3/target/`:** build artifacts — generated, not committed
**`pyo3/htmlcov/`, `pyo3/.pytest_cache/`, `pyo3/coverage.xml`:** generated coverage output — not committed
**`.venv/`:** local Python virtualenv for the pyo3 build — generated, not committed
**`.planning/`:** GSD planning artifacts (phases, research, this codebase map) — committed, updated by GSD commands
**`test_data/`, `tests/fixtures/`:** committed test inputs (sequences, kmers)
**`graphify-out/` (if present):** knowledge-graph output; regenerated by the graphify skill

---

*Structure analysis: 2026-10-18*
