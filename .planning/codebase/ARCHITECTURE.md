---
last_mapped_commit: 51629b5ea7ed323cfb60ef0be9cab2f30f6a2ed6
last_mapped_at: 2026-10-18
---
<!-- refreshed: 2026-10-18 -->

# Architecture

**Analysis Date:** 2026-10-18

## System Overview

rustkmer is a high-performance k-mer counting toolkit delivered through three surfaces that share one core library: a Rust CLI binary (`rustkmer`), a Python native extension (`pyrustkmer` via PyO3), and a reusable Rust library crate (`rustkmer`).

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                              Interfaces                                   │
├───────────────────────────┬──────────────────────┬───────────────────────┤
│  CLI binary               │  Python extension    │  Debug tools           │
│  src/main.rs              │  pyo3/src/lib.rs     │  tools/*.rs            │
│  (clap Parser → commands) │  (#[pyfunction]/     │  (standalone bins)     │
│                           │   #[pyclass] wrappers)│                       │
└────────────┬──────────────┴──────────┬───────────┴───────────────────────┘
             │                         │
             ▼                         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       Core library crate (`rustkmer`)                     │
│  src/cli/commands/*  src/hash/  src/kmer/  src/io/  src/database/        │
│  src/fuzzy/  src/output/  src/memory/  src/config/  src/core/            │
└────────────┬─────────────────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Output: binary .rkdb database files (RKDB format, memory-mapped)        │
│  text/CSV dumps, TSV/JSON stats                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| CLI entry | Arg parsing (clap derive), logging init, command dispatch | `src/main.rs` |
| CLI args | `Commands` enum: Count, Query, Dump, FuzzyQuery, FuzzyQueryBatch, Merge, Stats, PrefixQuery | `src/cli/args.rs` |
| Command implementations | One `execute_*` function per subcommand (`benchmark.rs` removed; no Benchmark command) | `src/cli/commands/*.rs` |
| Counter engine | `KmerCounter` — concurrent counting via `CounterTable::{Dense(DashMap<u64,u32>), Wide(DashMap<u128,u32>)}` | `src/hash/table.rs` |
| Counter support | Count filtering, overflow handling, hash matrix | `src/hash/filtering.rs`, `src/hash/overflow.rs`, `src/hash/matrix.rs` |
| K-mer encoding | 2-bit encoding, canonicalization, validation, operations | `src/kmer/encoding.rs`, `src/kmer/canonical.rs`, `src/kmer/validation.rs`, `src/kmer/operations.rs` |
| Sequence I/O | FASTA/FASTQ parsing (MultiGzDecoder for concatenated gzip members), memory-mapped reads, file discovery, compression (flate2/bzip2/xz2) | `src/io/fasta.rs`, `src/io/fastq.rs`, `src/io/mmap.rs`, `src/io/discovery.rs` |
| RKDB format | Binary database header/format read/write (42-byte header); dense KmerKey storage on merge routes | `src/database/format.rs` |
| Database index & query | `DatabaseIndex`, `DatabaseQuery`, prefix/suffix query paths | `src/database/index.rs`, `src/database/query.rs`, `src/database/prefix_query.rs`, `src/database/prefix_query_optimized.rs`, `src/database/suffix_query.rs` |
| Merge engine | Streaming merge, external-sort prefix-cache merge, routing/admission, RAII temp lifecycle + orphan sweep | `src/database/streaming_merge.rs`, `src/database/prefix_cache_merge.rs`, `src/database/merge_config.rs`, `src/database/merge_error.rs`, `src/database/temp_lifecycle.rs` |
| Fuzzy query | Mutation expansion, wildcards, normalization, perf tuning | `src/fuzzy/query.rs`, `src/fuzzy/expansion.rs`, `src/fuzzy/mutation.rs`, `src/fuzzy/wildcard.rs`, `src/fuzzy/normalization.rs`, `src/fuzzy/performance.rs` |
| Output | Binary and text writers | `src/output/binary.rs`, `src/output/text.rs` |
| Memory management | Memory-efficiency helpers/budgets | `src/memory/efficiency.rs` |
| Config | Config manager (TOML/serde) | `src/config/manager.rs` |
| Core metadata/monitoring | Database metadata, metrics collector, profiling helpers | `src/core/metadata.rs`, `src/core/monitoring.rs`, `src/core/database/persistence.rs` |
| Errors | `KmerError`/`ProcessingError` (thiserror), `ProcessingResult` | `src/error.rs` |
| Python bindings | PyO3 classes: PyDatabase (with `merge` kwargs), PyCounter, PyFuzzyQuery, PyPrefixQuery, etc. | `pyo3/src/lib.rs`, `pyo3/src/database.rs`, `pyo3/src/counter.rs`, `pyo3/src/fuzzy_query.rs`, `pyo3/src/prefix_query.rs` |
| Debug tools | Standalone canonicalization/database analysis binaries | `tools/debug_canonical_trace.rs`, `tools/analyze_database.rs`, `tools/verify_canonical.rs` |

## Pattern Overview

**Overall:** Layered library-first architecture with thin interface adapters (CLI + PyO3) over a shared domain core.

**Key Characteristics:**
- Library crate (`src/lib.rs`, rlib) holds all logic; `src/main.rs` is only a clap dispatch shell.
- Parallelism via rayon throughout; concurrent counting via `DashMap` sharded by k-mer width — **dense** `DashMap<u64, u32>` for k ≤ 32 (`MAX_KMER_SIZE_IN_U64`), wide `DashMap<u128, u32>` above; width chosen at `KmerCounter::new()` and hidden behind a `u128`-typed public surface (`src/hash/table.rs:38-40`, `uses_dense_storage()` at `:199`).
- Binary `.rkdb` persistence with memory-mapped (`memmap2`) read paths and header-only merge routing with a 96 B/k-mer admission model (plan 03-09).
- Errors: `thiserror` in library (`src/error.rs`), `anyhow` at CLI boundary.
- PyO3 bindings live in a separate crate (`pyo3/`) that depends on the parent by path — no Python code in the Rust core.

## Layers

**Interface layer:**
- Purpose: parse input, dispatch to command handlers, format output
- Location: `src/main.rs`, `src/cli/`, `pyo3/src/`
- Contains: clap definitions, `execute_*` functions, PyO3 wrappers and formatters
- Depends on: all library modules
- Used by: end users (CLI/Python)

**Domain logic layer:**
- Purpose: counting, encoding, querying, merging, fuzzy matching
- Location: `src/hash/`, `src/kmer/`, `src/database/`, `src/fuzzy/`
- Depends on: `src/io/`, `src/error.rs`
- Used by: interface layer, tests, PyO3 crate

**I/O and persistence layer:**
- Purpose: sequence parsing, RKDB serialization, output writing
- Location: `src/io/`, `src/output/`, `src/core/database/persistence.rs`
- Depends on: `src/database/format.rs` (header layout)
- Used by: domain and interface layers

**Cross-cutting layer:**
- Purpose: errors, config, monitoring, memory budgets
- Location: `src/error.rs`, `src/config/`, `src/core/monitoring.rs`, `src/memory/`
- Used by: everything

## Data Flow

### Primary Request Path (count)

1. `rustkmer count ...` → clap parse → `Commands::Count` dispatch (`src/main.rs`)
2. `execute_count(&args)` (`src/cli/commands/count.rs`) discovers/reads input files via `src/io/discovery.rs`, `src/io/fasta.rs`/`fastq.rs`/`mmap.rs`
3. Sequences encoded to 2-bit k-mers, canonicalized (`src/kmer/encoding.rs`, `src/kmer/canonical.rs`)
4. `KmerCounter::increment` narrows to the dense `u64` width when active and inserts into the sharded DashMap in parallel (rayon) (`src/hash/table.rs:250-263`)
5. Results persisted as binary `.rkdb` via database format writers (`src/database/format.rs`, `src/core/database/persistence.rs`) or dumped as text (`src/output/`)

### Query Path

1. `rustkmer query` args validated first (`validate_query_args`, `src/cli/commands/query.rs`, invoked early in `src/main.rs`)
2. `execute_query` memory-maps the `.rkdb`, builds `DatabaseIndex` (`src/database/index.rs`)
3. Lookup via `DatabaseQuery` (`src/database/query.rs`); prefix queries route through `src/database/prefix_query.rs` / `prefix_query_optimized.rs`; suffix through `src/database/suffix_query.rs`
4. Results formatted by `src/output/text.rs`

### Merge Path

1. `rustkmer merge` → `execute_merge` (`src/cli/commands/merge.rs`)
2. Route chosen from the 42-byte header only (no full load) with a 96 B/k-mer admission model (`src/database/merge_config.rs`); `MergeMode` options `auto`/`memory`/`streaming` mirror the CLI `--merge-mode` flag
3. Either streaming merge (`src/database/streaming_merge.rs`) or external-sort prefix-cache merge (`src/database/prefix_cache_merge.rs`), running inside a process-unique RAII temp subdir (`src/database/temp_lifecycle.rs`)
4. Temp cleanup is two-layered (D-06): RAII `TempDir` for normal exits/unwinding tests, plus `sweep_stale_merge_dirs()` on the next merge for abort/SIGKILL/power-loss orphans (release profile is `panic = "abort"`, so `Drop` does not run) — the `rustkmer-merge-` prefix (`MERGE_TEMP_PREFIX`) is the sweep's load-bearing selector

### Python API Flow (merge)

1. `pyrustkmer.PyDatabase.merge(databases, output, *, max_memory=None, merge_mode="auto")` (`pyo3/src/database.rs:1370-1375`)
2. `merge_mode` validated at the Python boundary against `VALID_MERGE_MODES` (`auto`, `memory`, `streaming`); `max_memory` parsed via `rustkmer::cli::commands::merge::parse_memory_size` (`pyo3/src/database.rs:1395-1414`)
3. Delegates to the same bounded core the CLI uses (`RKDatabase::merge_databases_to_path`) — output written directly, never fully materialized in memory

**State Management:**
- Counting state is the `KmerCounter` DashMap (interior mutability, rayon-safe). Databases are immutable files once written; queries operate on memory maps. No global mutable singletons.

## Key Abstractions

**KmerCounter:**
- Purpose: thread-safe k-mer counter, the central domain object
- Examples: `src/hash/table.rs` (re-exported from `src/lib.rs` as `pub use hash::KmerCounter`)
- Pattern: `CounterTable` enum — `Dense(DashMap<u64, u32>)` for k ≤ 32, wide `DashMap<u128, u32>` otherwise; width internal, API typed `u128`; `narrow_to_dense` asserts the narrowing invariant (threat T-03-09 tamper checks in `tests/dense_proptest_tests.rs`)

**RKDB database format:**
- Purpose: on-disk k-mer storage shared by CLI and Python API
- Examples: `src/database/format.rs` (`DatabaseHeader`, `DatabaseFormat`), `src/database/index.rs` (`DatabaseIndex`)
- Pattern: fixed 42-byte header + indexed payload, read via mmap; merge routes use dense `KmerKey` storage

**Merge strategies:**
- Purpose: combine databases under memory budgets
- Examples: `src/database/streaming_merge.rs`, `src/database/prefix_cache_merge.rs` (`ExternalSortMerger`)
- Pattern: strategy selection via `MergeConfig`/`MergeStrategy`/`MergeStats` (`src/database/merge_config.rs`) with header-only routing

**Temp lifecycle (MERGE-03 / D-06):**
- Purpose: guarantee temp-shard cleanup for failed/interrupted merges
- Examples: `src/database/temp_lifecycle.rs` (`create_merge_temp_subdir`, `sweep_stale_merge_dirs`, `MERGE_TEMP_PREFIX`)
- Pattern: RAII + TTL-based startup sweep; verified by `tests/merge_cleanup_tests.rs`

**Fuzzy query engine:**
- Purpose: mutation/wildcard-tolerant k-mer lookup
- Examples: `src/fuzzy/query.rs` plus expansion/mutation/wildcard modules
- Pattern: query normalization → variant expansion → batched lookup

**PyO3 wrapper classes:**
- Purpose: expose library to Python
- Examples: `pyo3/src/lib.rs` (`#[pymodule]` registering `PyDatabase`, `PyCounter`, `PyFuzzyQuery`, `PyPrefixQuery`, `PyFormatter`, `RustKmerError`, etc.)
- Pattern: thin `#[pyclass]` wrappers delegating to `rustkmer` crate; keyword-arg signatures via `#[pyo3(signature = ...)]`

## Entry Points

**CLI binary `rustkmer`:**
- Location: `src/main.rs` (bin defined in `Cargo.toml` `[[bin]]`)
- Triggers: shell invocation; subcommands Count, Query, Dump, FuzzyQuery, FuzzyQueryBatch, Merge, Stats, PrefixQuery
- Responsibilities: parse, init env_logger, validate query args, dispatch

**Python module `pyrustkmer`:**
- Location: `pyo3/src/lib.rs` (cdylib, built via `pyo3/build.rs` + `pyproject.toml`)
- Triggers: `import pyrustkmer`
- Responsibilities: expose classes/functions listed above

**Debug binaries:**
- Location: `tools/debug_canonical_trace.rs`, `tools/analyze_database.rs`, `tools/verify_canonical.rs` (separate crate `rustkmer-debug-tools`, zero deps)
- Triggers: manual debugging sessions

**Library crate:**
- Location: `src/lib.rs` (rlib `rustkmer`)
- Triggers: `use rustkmer::...` from pyo3 crate, benches, integration tests

## Architectural Constraints

- **Threading:** rayon data parallelism; counting relies on DashMap interior mutability — new write paths must be rayon-safe. Release profile uses `panic = "abort"`, so never rely on `Drop`/`catch_unwind` for correctness in release; temp cleanup compensates via the startup sweep (`src/database/temp_lifecycle.rs`).
- **Global state:** none detected; monitoring/metrics are passed explicitly (`src/core/monitoring.rs` `MetricsCollector`).
- **Crate boundaries:** pyo3 crate depends on parent by path (`rustkmer = { path = ".." }`) — changes to public library API ripple into `pyo3/src/`.
- **Lint gate:** `#![deny(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]` at `src/lib.rs:1` — use `log::` macros, never println!/eprintln! in library code. Clippy `-D warnings` runs in CI on ubuntu/macos/**windows** (`.github/workflows/ci.yml`).
- **Feature flags:** `default = []`, optional `profiling` feature gates instrumentation.
- **File format coupling:** 42-byte RKDB header is read on merge routes; format changes must update `src/database/format.rs` and the routing model (`src/database/merge_config.rs`) together.
- **CI regression gate:** `.github/workflows/benchmark.yml` (BENCH-01) gates peak RSS (hard, locked 15%) against committed per-platform baselines via `scripts/bench/compare.py` exit codes; wall-time axis is advisory. The workflow must never soften/skip/launder exit codes.
- **Dense-width invariant:** `narrow_to_dense` (`src/hash/table.rs:223`) asserts u128→u64 narrowing — do not bypass it on new write paths.

## Anti-Patterns

### Printing from library code

**What happens:** Using `println!`/`eprintln!`/`dbg!` anywhere under `src/`.
**Why it's wrong:** Denied by the crate-level lint in `src/lib.rs:1`; breaks the logging convention.
**Do this instead:** Use `log::info!`/`log::warn!`/`log::error!` (env_logger initialized in `src/main.rs`).

### Loading whole databases to make routing decisions

**What happens:** Reading entire databases before choosing a merge strategy.
**Why it's wrong:** Defeats the memory-budget admission model (plan 03-09).
**Do this instead:** Read the 42-byte header only (`src/database/format.rs` `DatabaseHeader`) and route via `src/database/merge_config.rs`.

### Widening the public key type

**What happens:** A public `KmerKey` enum with a `u128` variant forced 16-byte alignment and bloated memory for k ≤ 32.
**Why it's wrong:** Made counting memory larger than the plain u128 counter (removed in plan 03-06).
**Do this instead:** Keep width internal to `CounterTable`; expose only the `u128`-typed surface of `KmerCounter` (`src/hash/table.rs`).

### Relying on Drop for temp cleanup in release builds

**What happens:** Assuming `TempDir::drop` cleans merge shards after a crash.
**Why it's wrong:** Release profile is `panic = "abort"` — no unwinding, no `Drop`; SIGKILL/power loss behave the same (`src/database/temp_lifecycle.rs` header comment).
**Do this instead:** Use `create_merge_temp_subdir` (RAII) for the common case and let `sweep_stale_merge_dirs` handle abort/killed runs; keep `MERGE_TEMP_PREFIX` unchanged.

## Error Handling

**Strategy:** thiserror-typed errors in the library; anyhow at the CLI/Python boundary.

**Patterns:**
- `KmerError` / `ProcessingError` with `ProcessingResult<T>` alias (`src/error.rs`, re-exported from `src/lib.rs`)
- CLI `main` returns `anyhow::Result<()>`; per-command `execute_*` functions propagate with context
- Merge-specific error taxonomy in `src/database/merge_error.rs` (exact error texts are test-asserted — see `tests/merge_route_parity_tests.rs`)
- PyO3 errors surfaced as `RustKmerError` (`pyo3/src/errors.rs`); `PyDatabase.merge` validates kwargs at the boundary and raises `PyValueError`/`PyRuntimeError` (`pyo3/src/database.rs:1395-1414`)

## Cross-Cutting Concerns

**Logging:** `log` + `env_logger` (default filter `info`, set in `src/main.rs`); profiling via `src/core/monitoring.rs` (`if_profiling`, `time_operation`, `MetricsCollector`)
**Validation:** k-mer validation in `src/kmer/validation.rs`; CLI query arg validation (`validate_query_args`) runs before dispatch; merge-mode/memory validation at both CLI (`src/cli/commands/merge.rs`) and Python (`pyo3/src/database.rs`) boundaries
**Authentication:** Not applicable (local CLI/library tool)

---

*Architecture analysis: 2026-10-18*
