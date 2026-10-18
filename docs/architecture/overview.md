---
title: Architecture Overview
---

<!-- generated-by: gsd-doc-writer -->

# Architecture Overview

## System Overview

rustkmer is a high-performance toolkit for counting, querying, and merging DNA k-mers at genome scale. It is built as a single layered Rust library with two independent front ends that share it: a CLI binary (`rustkmer`, built from `src/main.rs` and `src/cli/` with clap) and a Python extension module (`pyrustkmer`, built from the separate PyO3 crate in `pyo3/`). All k-mer state is persisted in a custom fixed-layout binary format (`.rkdb`, magic `RKDB`, version 2), so both surfaces read and write the same databases. The architecture is a classic layered design — front ends over a domain core — with no server, daemon, or long-running state: every invocation is a pipeline step (count reads into a database, query/merge databases into results), and parallelism comes from in-process rayon thread pools.

## Component Diagram

```mermaid
graph TD
    subgraph FE["Entry points"]
        CLI["rustkmer CLI - clap - src/main.rs, src/cli/"]
        PY["pyrustkmer - PyO3 cdylib - pyo3/src/lib.rs"]
    end

    subgraph CORE["Shared core library - crate rustkmer - src/"]
        IO["io/ - FASTA and FASTQ readers,<br/>gzip/bzip2/xz, mmap, file discovery"]
        KMER["kmer/ - 2-bit u128 encoding,<br/>canonical form"]
        HASH["hash/ - KmerCounter<br/>DashMap, dense or wide table"]
        DB["database/ - .rkdb format,<br/>query engine, merge routing"]
        FUZZY["fuzzy/ - wildcard expansion,<br/>Hamming mutations"]
        CFG["config/ - .rustkmerrc + RUSTKMER_ env layering"]
    end

    CLI --> IO
    CLI --> HASH
    CLI --> DB
    CLI --> FUZZY
    CLI --> CFG
    PY --> HASH
    PY --> DB
    PY --> FUZZY
    IO --> KMER
    KMER --> HASH
    HASH --> DB
    FUZZY --> DB
```

The dependency direction is strictly downward: `src/cli/` and `pyo3/src/` depend on the core modules in `src/`, never on each other, and the core modules never depend on a front end. This is what lets a change to counting or merge logic benefit both surfaces at once.

## Entry Points

| Entry point | Location | Reached by |
|---|---|---|
| CLI binary | `src/main.rs` | Running `rustkmer <subcommand>` |
| Rust library | `src/lib.rs` | `use rustkmer::...` from the CLI binary, the PyO3 crate, and integration tests |
| Python module | `pyo3/src/lib.rs` | `import pyrustkmer` from Python |

- **CLI**: `src/main.rs` parses arguments (clap `Args::parse`), initializes `env_logger`, validates query arguments, and dispatches to one `execute_*` function per subcommand in `src/cli/commands/`. Subcommands (defined in `src/cli/args.rs`): `count`, `query`, `stats`, `dump`, `merge`, `fuzzy-query`, `fuzzy-query-batch`, `prefix-query`.
- **Library**: `src/lib.rs` re-exports the public modules and the convenience types `KmerCounter`, `KmerError`, and `ProcessingResult`.
- **Python**: `pyo3/src/lib.rs` declares the `#[pymodule] fn pyrustkmer` and registers the `#[pyclass]` surface: `PyDatabase`, `PyCounter`, `PyFuzzyQuery`, `PyPrefixQuery`, `PyExtendedPrefixQuery`, `PyFormatter`, and the `RustKmerError` exception type, plus their stats/result helper classes. The bindings live in a separate crate (`rustkmer-pyo3`, `pyo3/Cargo.toml`, built as a `cdylib`) that depends on the root `rustkmer` crate by path and is packaged as a wheel with maturin.

## Data Flow

### Count: FASTA/FASTQ to sorted `.rkdb`

The `count` command (`execute_count` in `src/cli/commands/count.rs`) turns sequence files into a `.rkdb` database in one pass:

1. **Boundary validation** — `k` must satisfy `1 <= k <= 64` (two bits per base packed into a `u128`); filtering parameters and input presence are checked, and `--threads < 1` is rejected.
2. **Thread resolution** — the worker count is resolved once, before the file loop, from the precedence chain `--threads` > `RUSTKMER_THREADS` > `RAYON_NUM_THREADS` > all cores (`resolve_thread_count_from` in `src/cli/commands/count.rs`), and the global rayon pool is built with it.
3. **Input discovery** — either the explicit `-i` file list or directory discovery via `FileDiscovery` (`src/io/discovery.rs`).
4. **Format and compression routing** — each file's type is detected from its extension (including compressed suffixes such as `.fa.gz` / `.fastq.gz`) and opened through the compression-aware reader in `src/io/fastq.rs`, which transparently handles gzip (multi-member, via `MultiGzDecoder`), bzip2, and xz.
5. **Chunked parallel counting** — a single-threaded producer reads and decompresses records sequentially into bounded chunks of `CHUNK_SIZE = 4096` records, then hands each chunk to rayon workers via `par_iter()`. Each worker runs `process_one_record`: `encode_kmer_bytes_u128` (`src/kmer/encoding.rs`) packs the window into an integer, `canonical_kmer_u128` (`src/kmer/canonical.rs`) optionally reduces it to `min(kmer, reverse_complement)`, and `KmerCounter::increment` bumps its count. Windows containing invalid characters (for example `N`) are skipped and reported once per chunk.
6. **Counting table** — `KmerCounter` (`src/hash/table.rs`) stores counts in a sharded `dashmap::DashMap`. The table width is chosen at construction: a dense `DashMap<u64, u32>` for `k <= 32` and a wide `DashMap<u128, u32>` for `33..=64`, while the public API remains `u128`-typed end to end. Each increment uses the `entry().and_modify().or_insert_with()` chain, which holds exactly one shard lock, making the overflow-checked count update atomic per key.
7. **Emit** — after all files, an optional `--min-count`/`--max-count` filter is applied. Sorting is on by default (`--no-sort` is the opt-out): sharded-map iteration order is run-to-run non-deterministic, so sorting restores reproducible output and enables binary-search queries. Binary output writes the canonical 42-byte `DatabaseHeader::write_to` followed by `KmerEntry::write_to` records (a 16-byte little-endian `u128` k-mer plus a 4-byte little-endian `u32` count), both from `src/database/format.rs`. Text output writes `sequence<TAB>count` lines sorted by decoded sequence.

### Query

`DatabaseQuery::open(path, preload)` (`src/database/query.rs`) reads a `.rkdb` either by streaming entries through a `BufReader<File>` (binary search on sorted databases) or by preloading everything into a `Vec<KmerEntry>` cache (the CLI `--load` / `--no-load` flags). The fuzzy engine (`FuzzyQueryEngine`, `src/fuzzy/query.rs`) expands `N` wildcards and enumerates Hamming-distance mutation variants (`src/fuzzy/expansion.rs`, `src/fuzzy/mutation.rs`, `src/fuzzy/normalization.rs`), then batches exact lookups against the same query machinery.

### Merge: header-only size estimation and route selection

Both front ends — the CLI's `execute_merge` (`src/cli/commands/merge.rs`) and PyO3's `PyDatabase::merge` — funnel into `RKDatabase::merge_databases_to_path` (`src/database/format.rs`). It runs a prologue (empty-input guard, cross-input compatibility validation that reads only each input's 42-byte header, and a startup sweep of stale merge temp directories from `src/database/temp_lifecycle.rs`) and then resolves the merge route in `RKDatabase::resolve_merge_route`:

```mermaid
flowchart TD
    EST["Estimate total k-mers:<br/>read each input's 42-byte header only<br/>(fallback: (file_size - 42) / 20, an over-estimate)"]
    MEM["estimated_memory =<br/>total_kmers x 96 bytes/k-mer<br/>(in-memory admission model)"]
    Q{estimated_memory ><br/>max_memory_usage?}
    PC{"use_prefix_cache set?"}
    REJ["hard reject with actionable error<br/>(merge_mode='memory' over budget)"]
    ST["Streaming route"]
    IM["In-memory route"]

    EST --> MEM --> Q
    PC -->|yes| PCCR["PrefixCache route<br/>(merge_mode selects the per-bucket<br/>strategy inside ExternalSortMerger)"]
    PC -->|no| MODE{"merge_mode?"}
    MODE -->|memory + over budget| REJ
    MODE -->|streaming| ST
    MODE -->|auto, over budget| ST
    MODE -->|auto, within budget| IM
    Q -.feeds.-> MODE
```

Key properties of the routing decision:

- **The estimator never loads data.** `RKDatabase::estimate_total_kmers` (`src/database/format.rs`) reads only the 42-byte header of each input via `read_header_of`. If the header is unreadable or reports `total_kmers == 0`, it falls back to a coarse over-estimate from the file size, `(file_size - 42) / 20` — over-estimating is the safe direction because it routes toward streaming rather than admitting an in-memory merge that could OOM. Per-input counts are summed with saturating addition.
- **The admission model is per-route.** `RKDatabase::estimated_bytes_for_route` charges the in-memory route 96 bytes per k-mer (`INMEMORY_BYTES_PER_KMER`, derived from the three 32-byte-per-element structures that route holds at peak). The streaming and prefix-cache figures (32 B/k-mer) are diagnostic only — those routes are bounded by chunk/bucket size, not by total k-mer count.
- **The budget defaults to half the machine.** `MergeConfig::max_memory_usage` (`src/database/merge_config.rs`) defaults to 50% of `MemTotal` (with a 32 GB fallback when that is unavailable) and is overridden by `--max-memory`.
- **Decision order is load-bearing.** `use_prefix_cache` returns early (its `merge_mode` selects the per-bucket strategy inside the external sorter, not the route); an explicit `merge_mode='memory'` that cannot fit the budget is rejected with an actionable error instead of being attempted; an explicit `merge_mode='streaming'` always streams; under `auto` (the default), over budget routes unconditionally to streaming and within budget takes the in-memory fast path.

The three routes (`MergeStrategy` in `src/database/merge_config.rs`):

| Route | Implementation | Behavior |
|---|---|---|
| `InMemory` | `src/database/format.rs` | Loads all inputs, accumulates counts in a `HashMap<u128, u32>`, writes the result once. The only route that ever holds the whole merged dataset. |
| `Streaming` | `ExternalMerger`, `DatabaseStreamIterator`, `TempFileManager` in `src/database/streaming_merge.rs` | External sort: inputs stream in chunks, sorted runs spill to temp files, and a `BinaryHeap` k-way merge emits `.rkdb` bytes directly to the destination as they are produced. |
| `PrefixCache` | `ExternalSortMerger` in `src/database/prefix_cache_merge.rs` | Shards k-mers into 256 prefix buckets and merges one bucket at a time, bounded by the per-bucket buffer, with per-bucket error isolation (a failed bucket keeps its shard files as the recovery path). |

All routes write their output directly to the destination path (the streaming route emits `.rkdb` bytes as the merge yields them; the prefix-cache route renames its finished file into place). Temporary files live in process-unique `rustkmer-merge-*` subdirectories whose lifecycle is RAII `TempDir` cleanup plus a startup sweep of stale directories (`src/database/temp_lifecycle.rs`) — the sweep is the real defense for `panic = "abort"` / SIGKILL terminations where `Drop` never runs.

## Key Abstractions

| Abstraction | Location | Role |
|---|---|---|
| `KmerCounter` / `CounterTable` | `src/hash/table.rs` | Thread-safe counting table over a sharded `DashMap`; dense `u64` keys for `k <= 32`, wide `u128` keys for `33..=64`, `u128`-typed public surface, atomic per-key overflow-checked increments. |
| `encode_kmer_bytes_u128` / `canonical_kmer_u128` | `src/kmer/encoding.rs`, `src/kmer/canonical.rs` | Bit-packing (2 bits per base, `A=00 C=01 G=10 T=11`) and strand normalization to `min(kmer, reverse_complement)`; k is capped at `MAX_KMER_SIZE_IN_U128` = 64. |
| `DatabaseHeader` / `KmerEntry` / `RKDatabase` | `src/database/format.rs` | The `.rkdb` v2 on-disk format: magic `RKDB`, version 2, fixed 42-byte header (with `data_offset` pinned to 42), 20-byte little-endian entries; `RKDatabase` is the full in-memory representation and owns the merge routing. |
| `DatabaseQuery` | `src/database/query.rs` | Read-only query engine: streaming reads with binary search on sorted databases, or optional full preload into a `Vec<KmerEntry>` cache. |
| `MergeConfig` / `MergeStrategy` | `src/database/merge_config.rs` | Merge budget (`max_memory_usage`), temp dir, and route selector (`InMemory`, `Streaming`, `PrefixCache`, `Hybrid`). |
| `ExternalMerger` | `src/database/streaming_merge.rs` | External-sort merge for inputs too large for memory: chunked streaming, sorted run spill, heap-based k-way merge writing straight to the output path. |
| `ExternalSortMerger` | `src/database/prefix_cache_merge.rs` | Prefix-bucketed merge with bounded per-bucket memory and per-bucket error isolation. |
| `FuzzyQuery` / `FuzzyQueryEngine` | `src/fuzzy/query.rs` | Builder-style fuzzy query config plus the engine that expands wildcard/mutation variants and batches exact lookups. |
| `KmerError` / `ProcessingError` / `ProcessingResult` | `src/error.rs` | Layered error taxonomy: library code returns `Result<T, KmerError>` / `ProcessingResult<T>`, the CLI converts via `anyhow`, and PyO3 bridges to Python exceptions. |
| `ConfigManager` | `src/config/manager.rs` | Layered configuration — `.rustkmerrc` file, `RUSTKMER_*` environment variables, CLI overrides — behind a `parking_lot::RwLock`. |
| PyO3 wrappers | `pyo3/src/database.rs`, `pyo3/src/counter.rs`, `pyo3/src/fuzzy_query.rs`, `pyo3/src/prefix_query.rs`, `pyo3/src/formatter.rs`, `pyo3/src/errors.rs` | Thin `#[pyclass]` adapters over the core types; errors surface as `RustKmerError` or `PyValueError`. |

## Directory Structure

```text
src/
├── main.rs          # CLI entry point (binary crate)
├── lib.rs           # Library root; re-exports public modules and key types
├── error.rs         # Error taxonomy (KmerError, ProcessingError, ProcessingResult)
├── cli/             # clap argument tree (args.rs) + one execute_* per subcommand (commands/)
├── kmer/            # encoding, canonical form, validation, sequence operations
├── hash/            # KmerCounter, count filtering, overflow protection
├── io/              # FASTA/FASTQ parsing, compression, memory mapping, file discovery
├── database/        # .rkdb format, query engine, merge subsystem (streaming, prefix cache)
├── fuzzy/           # wildcard expansion, mutation enumeration, normalization
├── config/          # layered configuration (file + environment + CLI)
├── core/            # metadata persistence, performance monitoring
├── memory/          # memory-efficiency helpers
└── output/          # output formatting (binary, text)

pyo3/
├── Cargo.toml       # crate rustkmer-pyo3 (cdylib), path dependency on the root crate
├── pyproject.toml   # maturin build backend, pytest/tooling configuration
├── src/             # PyO3 wrappers exposing the pyrustkmer module
└── tests/           # Python tests for the bindings
```

The split is intentional: everything under `src/` (minus `src/cli/`) is front-end-agnostic domain logic; `src/cli/` holds only argument parsing, validation, and output formatting for the terminal; `pyo3/` holds only the Python binding shim. The database subsystem is the largest module because persistence, query, and three merge strategies all live beside the format definition they share.

## Architectural Constraints and Invariants

- **K-mer width**: `k` is hard-bounded to `1..=64` (two bits per base in a `u128`), enforced at the count boundary in `src/cli/commands/count.rs` and in `KmerCounter::new`. The dense/wide table choice is purely an in-RAM optimization — `.rkdb` files always store 16-byte `u128` k-mers regardless of `k`.
- **Single-process, no coordination**: there is no server, IPC, or file locking. All shared state is instance-scoped (`KmerCounter`'s sharded map, `DatabaseQuery`'s optional cache); concurrent writers to the same `.rkdb` path will corrupt it.
- **Format discipline**: `.rkdb` is version 2 with a fixed 42-byte header and 20-byte entries; readers reject any `data_offset` other than 42 rather than silently clamping it. The header's `total_kmers` is a record count, not a sum of counts.
- **Parallelism**: rayon global thread pools only. Decompression stays single-threaded by design; only the encode/canonicalize/increment work per record is parallelized, in bounded record chunks.
- **Memory safety on merge**: the merge admission model exists so that an over-budget merge routes to a bounded route or fails with an actionable error — never attempts an in-memory merge that would OOM — and the estimator itself reads only headers so it can never be the OOM.

## Related Documentation

- [API Reference Overview](../api-reference/overview.md) — the `pyrustkmer` class surface
- [Core Concepts](../user-guide/concepts.md) — k-mers, canonical form, and database basics
- [Prefix Query Guide](../guides/prefix-query-guide.md) — hybrid prefix patterns
- [PyO3 Binding Guide](../guides/pyo3-binding-guide.md) — building and extending the Python module
