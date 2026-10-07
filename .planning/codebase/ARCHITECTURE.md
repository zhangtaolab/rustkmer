---
last_mapped_commit: 511b99e5b23614e60426e04a74bcf91a3c5d1a32
last_mapped_at: 2026-10-07
---
<!-- refreshed: 2026-10-07 -->

# Architecture

**Analysis Date:** 2026-10-07

## System Overview

```text
┌───────────────────────────────────┬─────────────────────────────────────────┐
│           CLI surface             │            Python surface               │
│  bin `rustkmer`  `src/main.rs`    │  cdylib `pyrustkmer`  `pyo3/src/lib.rs` │
│  clap args `src/cli/args.rs`      │  PyDatabase / PyCounter / PyFuzzyQuery  │
│  commands `src/cli/commands/*.rs` │  PyPrefixQuery / PyFormatter / LoadMode │
└─────────────────┬─────────────────┴────────────────────┬────────────────────┘
                  │                                      │
                  ▼                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Core library crate `rustkmer` (`src/lib.rs`)              │
│  Domain:  database/ (RKDB + merge)     hash/ (DashMap counter)               │
│           kmer/ (encode/canonical)     fuzzy/ (wildcard/mutation engine)     │
│  I/O:     io/ (FASTA/FASTQ/discovery/mmap)   output/ (legacy writers)        │
│  Support: error.rs   config/   memory/   core/ (metadata, persistence, mon.) │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Persistence: `.rkdb` v2 (magic `RKDB`, 42-byte header, 20-byte entries:      │
│ u128 LE k-mer + u32 LE count) │ text TSV │ JSON/CSV/TSV stats                │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| CLI binary | Parse args, init logging, dispatch to command modules | `src/main.rs` |
| CLI args | clap derive definitions for 8 subcommands + validation helpers | `src/cli/args.rs` |
| Count command | Parallel k-mer counting pipeline (FASTA/FASTQ, compressed) | `src/cli/commands/count.rs` |
| Query command | Exact lookup: literal k-mers, sequence file, batch, interactive | `src/cli/commands/query.rs` |
| Dump command | Database inspection/conversion (RKDB or bincode) | `src/cli/commands/dump.rs` |
| Fuzzy commands | Wildcard/mutation-tolerant queries (+ batch mode) | `src/cli/commands/fuzzy.rs` |
| Merge command | Multi-database merge orchestration + compatibility checks | `src/cli/commands/merge.rs` |
| Prefix command | Prefix and hybrid-pattern (`ATAC{N5}ACAC`) lookup | `src/cli/commands/prefix.rs` |
| Stats command | Frequency distribution/statistics with 4 output formats | `src/cli/commands/stats.rs` |
| K-mer counter | Thread-safe `DashMap<u128,u32>` counting, overflow protection | `src/hash/table.rs` |
| Count filtering | min/max (`-L`/`-U`) count threshold passes | `src/hash/filtering.rs` |
| K-mer encoding | u64 (legacy) + u128 packed 2-bit encode/decode, revcomp, canonicalization | `src/kmer/encoding.rs`, `src/kmer/canonical.rs`, `src/kmer/operations.rs`, `src/kmer/validation.rs` |
| FASTA/FASTQ I/O | Record parsing via `bio`, gzip/bzip2/xz compression | `src/io/fasta.rs`, `src/io/fastq.rs` |
| File discovery | Recursive directory scanning, file-type detection | `src/io/discovery.rs` |
| RKDB format | Header/entry serialization, `RKDatabase`, merge strategy selection | `src/database/format.rs` |
| Query engine | Binary search on disk / cache / hash lookup | `src/database/query.rs`, `src/database/index.rs` |
| Prefix/suffix extraction | Sorted-prefix + hybrid pattern + suffix lookup | `src/database/prefix_query.rs`, `src/database/prefix_query_optimized.rs`, `src/database/suffix_query.rs` |
| Streaming merge | External sort + k-way heap merge with temp files | `src/database/streaming_merge.rs` |
| Prefix-cache merge | Prefix-bucket cached merge with error isolation | `src/database/prefix_cache_merge.rs` |
| Merge config/errors | Strategy enum, memory limits, typed merge errors | `src/database/merge_config.rs`, `src/database/merge_error.rs` |
| Database stats | Streaming stats (tdigest quantiles), JSON/CSV/TSV output | `src/database/stats.rs` |
| Fuzzy engine | Wildcard expansion, length normalization, Hamming mutations | `src/fuzzy/query.rs`, `src/fuzzy/wildcard.rs`, `src/fuzzy/mutation.rs`, `src/fuzzy/normalization.rs`, `src/fuzzy/expansion.rs`, `src/fuzzy/performance.rs` |
| Metadata | Versioned JSON database metadata + checksums | `src/core/metadata.rs` |
| Persistence | Checksummed save/load of k-mer maps (JSON+binary) | `src/core/database/persistence.rs` |
| Monitoring | Global metrics collector, timers | `src/core/monitoring.rs` |
| Config | File/env/operation-layered configuration | `src/config/manager.rs` |
| Memory | mmap lifecycle, page iteration, memory reports | `src/memory/efficiency.rs` |
| Errors | `KmerError` (thiserror) + `ProcessingError` (anyhow-wrapped) | `src/error.rs` |
| PyO3 bindings | 12 Python classes wrapping the core crate | `pyo3/src/*.rs` |

## Pattern Overview

**Overall:** Layered library with two thin entry surfaces (CLI binary + PyO3 cdylib), command pattern for CLI subcommands, and strategy pattern for storage/merge.

**Key Characteristics:**
- One core crate (`rustkmer`) is shared by both surfaces; the PyO3 crate depends on it via `rustkmer = { path = ".." }` (`pyo3/Cargo.toml`).
- CLI dispatch is a clap enum match in `src/main.rs`; each subcommand is a module exposing a single `execute_<name>` function.
- `RKDatabase` is the storage facade; merge picks a strategy (in-memory / streaming external sort / prefix-cache) based on estimated memory vs budget (`src/database/format.rs:640`).
- Counting is single-producer/multi-worker: a sequential reader fills bounded record chunks that rayon `par_iter` workers count into a sharded `DashMap` (`src/cli/commands/count.rs:33-104`, `:376`).
- Single canonical `.rkdb` writer/reader: the count path delegates header/entry serialization to `DatabaseHeader::write_to` / `KmerEntry::write_to` (`src/database/format.rs:81`, `:210`), byte-verified by golden tests.
- u128 packed encoding everywhere in the hot path (k ≤ 64); legacy u64 helpers retained for backward compatibility (`src/kmer/mod.rs`).
- Two error regimes: `KmerError`/`ProcessingError` inside the library, `anyhow` at command boundaries.
- Python `PyDatabase` offers three storage strategies: `Preload` (BTreeMap cache), `MemoryMapped` (direct file I/O), `Lazy` (sorted Vec + binary search) (`pyo3/src/database.rs:29`).

## Layers

**CLI layer:**
- Purpose: user-facing commands, argument validation, progress output
- Location: `src/main.rs`, `src/cli/`
- Contains: clap definitions (`src/cli/args.rs`), command implementations (`src/cli/commands/*.rs`)
- Depends on: all core modules directly
- Used by: the `rustkmer` binary only
- Note: `src/cli/mod.rs:1` has `#![allow(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]` because the library root denies these macros

**Core domain layer:**
- Purpose: k-mer algorithms and database operations
- Location: `src/database/`, `src/hash/`, `src/kmer/`, `src/fuzzy/`
- Contains: counting, encoding, format I/O, query engines, merge strategies, fuzzy matching
- Depends on: `src/error.rs`, `src/io/`, `src/output/`
- Used by: CLI commands and PyO3 bindings

**Core I/O layer:**
- Purpose: reading sequence files and writing results
- Location: `src/io/`, `src/output/`
- Contains: FASTA/FASTQ processors, compressed readers, memory mapping, file discovery; legacy binary (`RSK1`) and text writers
- Depends on: `src/error.rs`
- Used by: CLI commands (FASTA/FASTQ/discovery are hot-path; `output/` is public API only)

**Core support layer:**
- Purpose: cross-cutting infrastructure
- Location: `src/error.rs`, `src/config/`, `src/memory/`, `src/core/`
- Contains: error types, layered config, mmap manager, metadata schema, persistence, monitoring
- Used by: commands and library consumers; `core::metadata` is also used by `src/database/prefix_cache_merge.rs`

**Python binding layer:**
- Purpose: expose the core library to Python
- Location: `pyo3/src/`
- Contains: 12 `#[pyclass]` types; module registration in `pyo3/src/lib.rs:38`
- Depends on: `rustkmer` path dependency, PyO3 0.27.2, maturin build (`pyo3/pyproject.toml`)
- Used by: the `pyrustkmer` Python package

**Persistence formats:**
- `.rkdb` binary: magic `RKDB`, version 2, 42-byte header, 20-byte entries (`src/database/format.rs:11-14`)
- Text TSV: `sequence\tcount` (`src/cli/commands/count.rs:638`)
- Stats: text/json/csv/tsv (`src/database/stats.rs:106`)
- Legacy `RSK1` binary + text writers in `src/output/` (public API, unused by the CLI)
- Hybrid JSON+binary persistence for `core::database::persistence` (`data.rkdb[.gz]` + metadata JSON)

## Data Flow

### Primary Request Path — Count

1. `main()` parses `Args` and initializes `env_logger` (`src/main.rs:10-13`).
2. `Commands::Count` dispatches to `execute_count` (`src/main.rs:27-28`).
3. `execute_count` validates k ∈ [1, 64], filtering params, and input params (`src/cli/commands/count.rs:60-95`; validators at `src/cli/args.rs:429`, `:486`).
4. Thread count resolved via precedence chain `--threads > RUSTKMER_THREADS > RAYON_NUM_THREADS > num_cpus` (`resolve_thread_count`, `src/cli/commands/count.rs:838`); rayon global pool built once (`build_global`, `count.rs:101-103`).
5. Input files: explicit `-i` list or directory discovery via `FileDiscovery` (`src/io/discovery.rs:142`).
6. Per file, format routing by extension (`.fa/.fasta/.fna/.ffn`, `.fq/.fastq` + `.gz` variants, `count.rs:181-230`); validation via `validate_fasta_file` / `validate_fastq_file`; processor constructed (`FastaProcessor`, `src/io/fasta.rs:14`; `FastqProcessor`, `src/io/fastq.rs:86`).
7. Producer reads records sequentially through the compression-aware opener `DefaultCompressedFileReader::open_compressed` (`src/io/fastq.rs:50-57`) into a bounded `CHUNK_SIZE = 4096` buffer (`count.rs:31`), then rayon workers process each chunk (`process_fasta_file` `count.rs:435`, `process_fastq_file` `count.rs:545`).
8. Per k-mer window: `encode_kmer_bytes_u128` → optional `canonical_kmer_u128` → `KmerCounter::increment` (`process_one_record`, `count.rs:376`; counter at `src/hash/table.rs:76`). DashMap `entry().and_modify().or_insert_with()` is atomic per key; invalid characters (N, etc.) are skipped and counted.
9. After all files: `CountFilter` applied; output written. Default binary = RKDB via `output_binary_format` (`count.rs:692`) delegating to `DatabaseHeader::write_to` + `KmerEntry::write_to`; `--format text` = TSV via `output_text_format` (`count.rs:638`). Output is sorted by default; `--no-sort` opts out.

### Query Path

1. `execute_query` (`src/cli/commands/query.rs:15`) decides preload strategy (`--load` / `--no-load`) and opens `DatabaseQuery::open` (`src/database/query.rs:37`).
2. Mode branch: interactive REPL / FASTA sequence file / batch text file / literal k-mer list.
3. Lookup: `query_kmer` canonicalizes (if db is canonical) then either binary-searches the in-memory cache (`query_from_memory`, `query.rs:143`) or binary-searches on disk with seeks (`query_from_disk`, `query.rs:161`). Unsorted DBs require preload.
4. Results written as TSV to file or stdout; missing literal k-mers print an "Invalid mer" note.

### Merge Path

1. `execute_merge` (`src/cli/commands/merge.rs:141`) requires ≥ 2 inputs; loads the reference database; validates k-mer size and canonical-mode compatibility (skipped under `--use-prefix-cache`).
2. `MergeConfig` built from CLI flags (memory budget, chunk size default 50M, `merge_mode`) (`src/database/merge_config.rs:12`).
3. `RKDatabase::merge_databases` (`src/database/format.rs:640`) estimates memory as `total_kmers × 24` bytes and selects:
   - prefix-cache: `ExternalSortMerger::external_sort_merge` (`src/database/prefix_cache_merge.rs:87`)
   - streaming: `ExternalMerger::sort_database` + `merge_sorted_chunks` heap merge (`src/database/streaming_merge.rs:236`, `:279`)
   - in-memory: load all entries, sum counts
4. Merged `.rkdb` written; timing/stats reported.

### Fuzzy Query Path

1. `execute_fuzzy_query` (`src/cli/commands/fuzzy.rs:162`) parses `FuzzyQueryArgs`, including optional position-mutation groups (`"3,4,5:2;6,7:1"` → `PositionMutationConfig::parse`, `src/fuzzy/query.rs:38`).
2. `RKDatabase::from_file_path`; `FuzzyQuery::new(query, k, mutations)` (`src/fuzzy/query.rs:190`).
3. `FuzzyQueryEngine::execute_query` (`src/fuzzy/query.rs:400`) expands wildcards (`src/fuzzy/wildcard.rs`), normalizes length (`src/fuzzy/normalization.rs`), generates mutation variants within limits (`src/fuzzy/mutation.rs`), matches against the database, dedupes; `execute_batch` (`:451`) streams a query file.
4. Results formatted table/json/csv/tsv (`src/cli/commands/fuzzy.rs`).

### Prefix Query Path

1. `execute_prefix_query` (`src/cli/commands/prefix.rs:31`) resolves pattern or explicit prefix; hybrid mode when `--hybrid` or pattern contains `{`.
2. Simple prefix uses `extract_prefix_optimized` (`src/database/prefix_query_optimized.rs:37`); hybrid uses `parse_hybrid_pattern` + `extract_hybrid_by_pattern` (`prefix_query_optimized.rs:385`, `:491`); a legacy `extract_kmers_by_prefix` remains in `src/database/prefix_query.rs:24`.
3. min/max count filters applied; output in table/json/csv/tsv.

### Python Path

1. Module init registers all classes (`pyrustkmer`, `pyo3/src/lib.rs:38-54`).
2. `PyDatabase::new(path, LoadMode)` (`pyo3/src/database.rs:434`) loads via `RKDatabase::from_file_path`; `Preload` builds a `BTreeMap<u128,u32>` cache, `MemoryMapped` keeps a direct `File` handle, `Lazy` keeps a sorted `Vec<(u128,u32)>` index.
3. `PyCounter` wraps the core `KmerCounter` and configures the global rayon pool; counting releases the GIL (`pyo3/src/counter.rs:104`).
4. `PyFuzzyQuery`, `PyPrefixQuery`, `PyExtendedPrefixQuery`, `PyFormatter` wrap their core counterparts; all result classes expose `to_json`/`to_csv`/`to_tsv`/`to_dict` (`pyo3/src/database.rs:43-105`).

**State Management:**
- Counting state lives in `KmerCounter.table: DashMap<u128, u32>` with atomic `AtomicU64` totals (`src/hash/table.rs:13-32`) — no external locking.
- Global rayon thread pool created once per process; second `build_global` errors are deliberately discarded (`count.rs:101-103`).
- Monitoring uses a process-global `MetricsCollector` singleton (`src/core/monitoring.rs:354`).
- `RKDatabase` owns its `header`, `entries: Vec<KmerEntry>`, and optional `file_path` (`src/database/format.rs:265`).
- Query engines (`DatabaseQuery`, `PyDatabase`) hold per-instance caches; no cross-instance sharing.

## Key Abstractions

**`KmerCounter`:**
- Purpose: thread-safe k-mer tallying with overflow protection
- Examples: `src/hash/table.rs:13` (uses `dashmap::DashMap`), builder at `:436`
- Pattern: sharded concurrent map + interior mutability; `get_filtered_kmers` (`:189`), `get_stats` (`:292`)

**`RKDatabase`:**
- Purpose: canonical in-memory representation of a `.rkdb` database and merge facade
- Examples: `src/database/format.rs:265`; `from_file_path` (`:287`), `from_kmer_pairs` (`:459`), `query_kmer` binary search (`:402`), `merge_databases` (`:640`)
- Pattern: facade + strategy selection

**`DatabaseHeader` / `KmerEntry`:**
- Purpose: single source of truth for the on-disk byte layout
- Examples: `src/database/format.rs:20` (42-byte header), `:199` (20-byte entry)
- Pattern: explicit little-endian `Write`/`Read` implementations (no serde on the wire)

**`DatabaseQuery`:**
- Purpose: read-side engine with optional in-memory cache
- Examples: `src/database/query.rs:17`; `open` (`:37`), `query_kmer` (`:111`), `query_multiple` (`:211`)
- Pattern: cache-or-seek strategy; loud rejection of non-canonical `data_offset` (`query.rs:100-107`)

**`FuzzyQuery` / `FuzzyQueryEngine`:**
- Purpose: approximate matching with wildcards/Hamming distance
- Examples: `src/fuzzy/query.rs:190`, `:393`; position-mutation config `:16`
- Pattern: variant generation pipeline (wildcard → normalize → mutate) bounded by `max_variants`

**Merge strategies:**
- Purpose: merge N databases under a memory budget
- Examples: `ExternalMerger` (`src/database/streaming_merge.rs:179`), `ExternalSortMerger` (`src/database/prefix_cache_merge.rs:15`), `MergeStrategy` enum (`src/database/merge_config.rs:47`)
- Pattern: external merge sort with k-way heap and temp-file management (`TempFileManager`, `streaming_merge.rs:113`)

**`FastaProcessor` / `FastqProcessor`:**
- Purpose: callback-based record iteration with compression autodetection
- Examples: `src/io/fasta.rs:14`, `src/io/fastq.rs:86`; `CompressedFileReader` trait `src/io/fastq.rs:50`
- Pattern: trait-object reader + `FnMut(&Record)` callback; the count hot path reads records directly to enable rayon chunking (`count.rs:435-470`)

**`MemoryManager`:**
- Purpose: threshold-driven mmap lifecycle, paging, efficiency reporting
- Examples: `src/memory/efficiency.rs:139`; `PageIterator` `:372`
- Pattern: config object + manager

**`ConfigManager`:**
- Purpose: layered configuration (global file + env overrides + operation overrides)
- Examples: `src/config/manager.rs:22`; `OperationConfig` `:119`, `ConfigReport` `:530`
- Pattern: builder/defaults + `apply_env_overrides_to_config` (`:421`)

**PyO3 facade classes:**
- Purpose: unified Python API surface
- Examples: `PyDatabase` (`pyo3/src/database.rs:407`), `LoadMode` (`:29`), `PyCounter` (`pyo3/src/counter.rs:104`), `PyFuzzyQuery` (`pyo3/src/fuzzy_query.rs`), `PyPrefixQuery` (`pyo3/src/prefix_query.rs`), `PyFormatter` (`pyo3/src/formatter.rs`)
- Pattern: wrapper structs holding core types/caches; all results derive formatter methods

## Entry Points

**CLI binary `rustkmer`:**
- Location: `src/main.rs` (declared as `[[bin]]` in `Cargo.toml:119-121`)
- Triggers: shell invocation
- Responsibilities: clap parse → logging init → special-case query validation (`main.rs:16-23`) → dispatch one of 8 subcommands: `count`, `query`, `dump`, `fuzzy-query`, `fuzzy-query-batch`, `merge`, `stats`, `prefix-query` (`src/cli/args.rs:17`)

**Library crate `rustkmer`:**
- Location: `src/lib.rs` (crate-type `rlib`, `Cargo.toml:114-117`)
- Triggers: `use rustkmer::...` from the PyO3 crate or external consumers
- Responsibilities: exposes 10 public modules; re-exports `KmerError`, `ProcessingError`, `ProcessingResult`, `KmerCounter` (`src/lib.rs:21-35`)

**Python extension `pyrustkmer`:**
- Location: `pyo3/src/lib.rs` (cdylib, `pyo3/Cargo.toml`)
- Triggers: `import pyrustkmer`
- Responsibilities: register `PyDatabase`, `PyDatabaseStats`, `PyQueryResult`, `PyPrefixQueryResult`, `LoadMode`, `PyCounter`, `PyCounterStats`, `PyFuzzyQuery`, `PyFuzzyResult`, `PyFuzzyMatch`, `PyPrefixQuery`, `PyExtendedPrefixQuery`, `PyPrefixQueryMetrics`, `PyFormatter`, `RustKmerError` (`pyo3/src/lib.rs:38-54`)

**Debug tools:**
- Location: `tools/Cargo.toml` (independent package, 3 binaries)
- Triggers: manual developer runs
- Responsibilities: `debug_canonical_trace.rs`, `analyze_database.rs`, `verify_canonical.rs` — standalone, no dependencies

## Architectural Constraints

- **Threading:** rayon global pool (initialized once in `execute_count` and `PyCounter::new`); `DashMap` sharded locks for counting; compressed streams are read by a single producer thread while record chunks are counted in parallel (design decision D-01/D-02).
- **Global state:** global rayon pool; monitoring singleton (`src/core/monitoring.rs:354`); `env_logger` initialized once in `src/main.rs:13`. No other process-wide mutable state in the library.
- **Encoding limit:** u128 2-bit packing caps k at 64 (`MAX_KMER_SIZE = 64`, `src/kmer/validation.rs:9`); `DatabaseHeader.kmer_size` is a `u8`. Legacy u64 API (`encode_kmer_u64`) is kept only for backward compatibility (`src/kmer/mod.rs:6-7`).
- **Format invariants:** `DATABASE_VERSION = 2` and `data_offset` must equal exactly 42; readers reject anything else loudly (`src/database/format.rs:14`, `:299-306`; `src/database/query.rs:100-107`).
- **Lint contract:** `src/lib.rs:1` denies `clippy::print_stdout`, `clippy::print_stderr`, `clippy::dbg_macro`; library code must use `log::*` for messages, and only the `cli` module (which re-allows them) prints to stderr.
- **Release profile:** `panic = "abort"`, LTO on, 1 codegen unit (`Cargo.toml:109-112`).
- **Alphabet:** 2-bit A/C/G/T only; non-ACGT windows are skipped (soft-skip for N), never percent-encoded.
- **No circular imports:** dependency direction is one-way (`cli` → domain → I/O/support; `pyo3` → `rustkmer`).
- **Crate graph:** three independent Cargo packages — root `rustkmer` (lib + bin), `pyo3/` (`rustkmer-pyo3` cdylib), `tools/` (debug bins). There is no workspace file; `pyo3` uses a path dependency back to the root.

## Anti-Patterns

### Orphaned source files not declared in `mod.rs`

**What happens:** `src/cli/commands/benchmark.rs` and `src/database/merge_tests.rs` exist but are not declared by `src/cli/commands/mod.rs` or `src/database/mod.rs` — they are never compiled. Likewise in PyO3: `pyo3/src/database_backup.rs`, `pyo3/src/database_new_approaches.rs`, and the `*.stage1_fix_backup` files are not declared in `pyo3/src/lib.rs`.
**Why it's wrong:** dead files drift out of date, confuse navigation, and bloat the repo; any future `mod` declaration would fail to compile.
**Do this instead:** delete them, or declare them properly and test them. Follow `src/cli/commands/mod.rs` — every real command has a `pub mod <name>;` line.

### Duplicated query readers

**What happens:** k-mer lookup logic exists twice — `DatabaseQuery` (`src/database/query.rs`) and `RKDatabase::query_kmer` (`src/database/format.rs:402`). Both re-implement binary search and both repeat the `data_offset != 42` rejection (intentionally per comment at `format.rs:299`).
**Why it's wrong:** any format or canonicalization change must be applied in both places or the two paths diverge silently.
**Do this instead:** route new read features through one engine (prefer `RKDatabase` for loaded databases, `DatabaseQuery` for streaming disk reads) and refactor duplicates when touching either file.

### Parallel output-format implementations

**What happens:** the count command writes RKDB directly using `format.rs` types (`src/cli/commands/count.rs:692`), while `src/output/binary.rs` defines a separate legacy `RSK1` format and `src/output/text.rs` writes a u64-based text format that the CLI never calls.
**Why it's wrong:** two formats with two sets of invariants; new output features added to the wrong one are invisible to the CLI.
**Do this instead:** use `DatabaseHeader`/`KmerEntry` from `src/database/format.rs` for all `.rkdb` output (the byte-identity contract is enforced by `tests/golden_tests.rs`).

### Test scaffolding referencing non-existent files

**What happens:** `tests/integration/mod.rs` and `tests/property/mod.rs` carry commented-out module declarations for missing files; `tests/unit/mod.rs` documents a deleted `test_merge_unit` module.
**Why it's wrong:** signals lost coverage; the referenced areas (merge compatibility, merge associativity/commutativity) have no executable tests through those paths.
**Do this instead:** either implement the modules or remove the stale comments; real coverage today lives in `tests/integration/queryx_tests.rs`, `tests/consistency/`, `tests/golden_tests.rs`, `tests/round_trip_tests.rs`, `tests/parallel_count_tests.rs`.

## Error Handling

**Strategy:** typed errors inside the library, anyhow at command boundaries; `main()` returns `anyhow::Result<()>` so failures exit non-zero.

**Patterns:**
- `KmerError` (thiserror enum) for domain failures: invalid k, bad chars, format errors, overflow, I/O (`src/error.rs:7`)
- `ProcessingError` wraps anyhow with `with_context` chaining; `ProcessingResult<T>` is the common library return alias (`src/error.rs:64-163`)
- CLI commands return `ProcessingResult<()>` or `anyhow::Result<()>` and add user-facing context before propagating
- Dedicated error enums: `MergeError` with recovery suggestions (`src/database/merge_error.rs:11`), `PersistenceError` (`src/core/database/persistence.rs:17`), `FuzzyError` (`src/fuzzy/mod.rs:47`), `StatsError` (`src/database/stats.rs:115`), `MetadataError` (`src/core/metadata.rs:11`), PyO3 `RustKmerError` (`pyo3/src/errors.rs`)
- Validation before I/O: `DatabaseHeader::validate` (`src/database/format.rs:174`), thread count ≥ 1, k range, prefix alphabet/order checks
- Query tolerates per-k-mer failures by logging a warning and returning count 0 for that k-mer (`src/database/query.rs:218-226`)

## Cross-Cutting Concerns

**Logging:** `log` macros throughout the library (`log::info!`, `log::warn!`, `log::error!`); `env_logger` initialized in the CLI (`src/main.rs:13`); user-facing progress via `eprintln!` in `src/cli/commands/*` gated on `--quiet`/`--verbose`; PyO3 counting logs the discarded rayon error under `RUST_LOG=warn`.

**Validation:** CLI-level validation helpers on `Commands` (`validate_filtering` `src/cli/args.rs:429`, `validate_input` `:486`, `create_count_filter` `:400`); core-level checks in `KmerCounter::new` (k range), `DatabaseHeader::validate`, `PositionMutationConfig::validate` (`src/fuzzy/query.rs:107`), prefix/suffix alphabet checks.

**Authentication:** Not applicable — local CLI/library with no network surface.

**Configuration:** `ConfigManager` layers defaults < config file < environment variables < per-operation overrides (`src/config/manager.rs`); runtime knobs are otherwise plain CLI flags. Thread env vars: `RUSTKMER_THREADS`, `RAYON_NUM_THREADS`.

---

*Architecture analysis: 2026-10-07*
