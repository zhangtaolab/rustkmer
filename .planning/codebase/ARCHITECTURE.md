<!-- refreshed: 2026-06-30 -->
# Architecture

**Analysis Date:** 2026-06-30

## System Overview

rustkmer is a high-performance k-mer counting and querying toolkit written in Rust. It is delivered through two independent entry points that share a single core library (`rustkmer` crate): a CLI binary (`rustkmer`) and a Python extension module (`pyrustkmer` via PyO3). Both surfaces persist and read the same custom binary `.rkdb` format.

```text
┌────────────────────────────────────────────────────────────────────────────┐
│                              Entry Surfaces                                 │
├──────────────────────────────────┬─────────────────────────────────────────┤
│   CLI binary (`src/main.rs`)     │   Python binding (`pyo3/src/lib.rs`)    │
│   clap Commands enum             │   #[pymodule] pyrustkmer                │
│   `src/cli/args.rs`              │   Py* wrapper classes                   │
│   `src/cli/commands/*.rs`        │   `pyo3/src/*.rs`                       │
└──────────────┬───────────────────┴──────────────────┬──────────────────────┘
               │                                      │
               ▼                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                    Core library crate `rustkmer` (`src/lib.rs`)            │
│  pub mod: cli · config · core · database · error · fuzzy · hash · io ·     │
│           kmer · memory · output                                            │
└──────────────┬─────────────────────────────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  RKDB binary format (`.rkdb`) — flat-file k-mer database                    │
│  `src/database/format.rs`: DatabaseHeader (42B) + KmerEntry[] (20B each)    │
│  Loaded via `RKDatabase`, `DatabaseQuery`, or memory-mapped (`io/mmap.rs`)  │
└────────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| `main.rs` | CLI entry: parse args, init logging, dispatch to command handler | `src/main.rs` |
| `Args` / `Commands` | clap-derived CLI definition and per-command validation helpers | `src/cli/args.rs` |
| Command handlers | One `execute_*` function per subcommand (count, query, stats, dump, merge, fuzzy, prefix) | `src/cli/commands/*.rs` |
| `KmerCounter` | Thread-safe in-memory counter (`HashMap<u128, u32>` behind `parking_lot::RwLock`) | `src/hash/table.rs` |
| `RKDatabase` | Full in-memory database representation + load/save | `src/database/format.rs` |
| `DatabaseQuery` | Streaming/random-access query engine over a `.rkdb` file | `src/database/query.rs` |
| `KmerEntry` / `DatabaseHeader` | Binary on-disk records | `src/database/format.rs` |
| Streaming merge | External-sort merge of multiple `.rkdb` files (memory-bounded) | `src/database/streaming_merge.rs` |
| Prefix query | Sorted-prefix / hybrid-pattern lookup over sorted databases | `src/database/prefix_query_optimized.rs` |
| Fuzzy engine | Wildcard expansion + Hamming-distance mutation matching | `src/fuzzy/query.rs`, `src/fuzzy/expansion.rs`, `src/fuzzy/mutation.rs` |
| PyO3 wrappers | `PyDatabase`, `PyCounter`, `PyFuzzyQuery`, `PyPrefixQuery`, `PyFormatter` | `pyo3/src/{database,counter,fuzzy_query,prefix_query,formatter}.rs` |

## Pattern Overview

**Overall:** Layered library-with-frontend pattern. A single Rust crate exposes a library API; the CLI binary and the PyO3 cdylib are thin frontends that translate their input formats (clap args / Python objects) into library calls.

**Key Characteristics:**
- K-mers are encoded as `u128` (supports k up to 64) and decoded on demand. See `src/kmer/encoding.rs`, `src/kmer/canonical.rs`.
- The `.rkdb` format is a fixed-layout binary file (magic `RKDB`, version 2, 42-byte header + 20-byte entries). No relational DB, no server.
- Counting produces an in-memory `HashMap`, optionally sorts entries, and writes them as a flat `.rkdb` (or text) file.
- Queries read the file back either by streaming entries (`DatabaseQuery`) or by loading all entries (`RKDatabase` / preload mode).
- PyO3 binding is a separate crate (`pyo3/Cargo.toml`, `crate-type = ["cdylib"]`) that depends on the core `rustkmer` crate by path.

## Layers

**CLI presentation layer:**
- Purpose: Parse user input, validate, format output.
- Location: `src/cli/` (`args.rs`, `commands/*.rs`)
- Contains: clap structs, `execute_*` free functions, output formatting for stdout/files (table/json/csv/tsv).
- Depends on: `hash`, `database`, `fuzzy`, `io`, `kmer`, `output`.
- Used by: `src/main.rs` dispatch only.

**Python binding layer:**
- Purpose: Expose Rust functionality as Python classes.
- Location: `pyo3/src/`
- Contains: `#[pyclass]` wrappers (`PyDatabase`, `PyCounter`, `PyFuzzyQuery`, `PyPrefixQuery`, `PyExtendedPrefixQuery`, `PyFormatter`, `RustKmerError`).
- Depends on: `rustkmer` core crate (path dependency), `pyo3`.
- Used by: Python import `pyrustkmer`.

**Core library layer:**
- Purpose: All domain logic — counting, encoding, querying, merging, fuzzy matching.
- Location: `src/lib.rs` and submodules (`hash/`, `database/`, `fuzzy/`, `kmer/`, `io/`, `output/`, `memory/`, `core/`, `config/`).
- Contains: Domain types, algorithms, file I/O.
- Depends on: external crates (`rayon`, `memmap2`, `bio`, `byteorder`, `hashbrown`, `ahash`, `parking_lot`, `flate2`/`bzip2`/`xz2`).
- Used by: CLI layer, PyO3 layer, integration tests.

**Persistence layer:**
- Purpose: Custom binary format read/write.
- Location: `src/database/format.rs` (the canonical implementation), with I/O also inlined in `src/cli/commands/count.rs` (write) and `src/database/query.rs` (read).
- Contains: `DatabaseHeader`, `KmerEntry`, `RKDatabase`, magic/version constants.
- Used by: count (write), query/stats/dump/merge (read), PyO3 `PyDatabase`.

## Data Flow

### Primary Request Path — Count

1. CLI parse: `Args::parse()` → `Commands::Count` (`src/main.rs:10`, `src/cli/args.rs:17`)
2. Validate k, filters, inputs via `Commands` helper methods (`src/cli/args.rs:394`–`552`)
3. Discover input files (file list or directory walk via `FileDiscovery`) (`src/cli/commands/count.rs:73`–`97`, `src/io/discovery.rs`)
4. Construct `KmerCounter` (capacity, canonical flag) (`src/cli/commands/count.rs:121`, `src/hash/table.rs:40`)
5. For each file: detect format (fasta/fastq, compressed), process via `FastaProcessor`/`FastqProcessor`, encode each k-mer (`encode_kmer_bytes_u128`), optionally canonicalize (`canonical_kmer_u128`), and `counter.increment(u128)` (`src/cli/commands/count.rs:128`–`265`)
6. Optionally sort entries by encoded k-mer (`src/cli/commands/count.rs:494`)
7. Write output: text (`output_text_format`) or binary `.rkdb` (`output_binary_format` writes 42-byte header + 20-byte entries) (`src/cli/commands/count.rs:266`–`270`, `:423`–`535`)

### Primary Request Path — Query

1. CLI parse → `Commands::Query` (`src/main.rs:30`); `validate_query_args` runs first (`src/cli/commands/query.rs`)
2. Open database: `DatabaseQuery::open(path, preload)` reads + validates header, optionally loads all `KmerEntry` into memory (`src/database/query.rs:37`–`70`)
3. For each queried k-mer: encode, binary-search the sorted entries (or scan cached entries), return count (`src/database/query.rs`)
4. Format output to stdout/file.

### Merge Flow

1. CLI parse → `Commands::Merge`; handler builds `MergeArgs` (`src/main.rs:106`–`135`, `src/cli/commands/merge.rs`)
2. Selects strategy based on flags: in-memory `MergeConfig`, `ExternalSortMerger` (prefix cache), or `ExternalMerger`/`StreamingMergeIterator` for bounded-memory streaming (`src/database/prefix_cache_merge.rs`, `src/database/streaming_merge.rs`)
3. Reads each input `.rkdb` via `DatabaseStreamIterator`, k-way merges, sums counts for duplicates, writes merged `.rkdb`.

### Python API Flow

1. `import pyrustkmer` → `#[pymodule] pyrustkmer` registers classes (`pyo3/src/lib.rs:37`)
2. `PyCounter` wraps `rustkmer::hash::KmerCounter` and reuses `FastaProcessor`/`FastqProcessor` (`pyo3/src/counter.rs:8`–`13`)
3. `PyDatabase` wraps direct `.rkdb` reads via `rustkmer::database::format::{RKDatabase, KmerEntry}` and supports three `LoadMode`s (Preload / MemoryMapped / Lazy) (`pyo3/src/database.rs:11`–`39`)
4. Results returned as `#[pyclass]` objects (`PyQueryResult`, `PyFuzzyResult`, etc.)

**State Management:**
- No long-running state, no daemon. All state is per-invocation.
- `KmerCounter` holds the only shared mutable state (a `parking_lot::RwLock<HashMap<u128, u32>>` + atomics for totals).
- `DatabaseQuery` optionally caches all entries in a `Vec<KmerEntry>` when preload is requested.
- Rayon thread pool is used for parallel processing within a process.

## Key Abstractions

**K-mer encoding (`u128`):**
- Purpose: Pack a k-mer (k ≤ 64) into a single integer for fast comparison/hashing.
- Examples: `src/kmer/encoding.rs` (`encode_kmer_u128`, `decode_kmer_u128`), `src/kmer/canonical.rs` (`canonical_kmer_u128`).
- Pattern: 2 bits per nucleotide, little-endian bit packing; canonical form is min(kmer, reverse_complement).

**KmerCounter:**
- Purpose: Accumulate counts during counting.
- Examples: `src/hash/table.rs:14`; wrapped by `pyo3/src/counter.rs`.
- Pattern: thread-safe wrapper around `HashMap<u128, u32>` with atomic totals and overflow protection.

**RKDatabase / DatabaseHeader / KmerEntry:**
- Purpose: In-memory and on-disk database representation.
- Examples: `src/database/format.rs:18` (header), `:187` (entry), `:256` (database).
- Pattern: Plain structs with `read_from`/`write_to` using `byteorder::LittleEndian`; 42-byte header, 20-byte entries (16-byte kmer + 4-byte count).

**DatabaseQuery:**
- Purpose: Read-only query engine with optional in-memory preload.
- Examples: `src/database/query.rs:17`.
- Pattern: Owns a `BufReader<File>` and optional `Vec<KmerEntry>` cache; uses binary search on sorted databases.

**FuzzyQueryEngine:**
- Purpose: Expand wildcards (`N`) and enumerate mutation variants within a Hamming distance, then query each.
- Examples: `src/fuzzy/query.rs`, `src/fuzzy/expansion.rs`, `src/fuzzy/mutation.rs`, `src/fuzzy/wildcard.rs`.
- Pattern: Builder-style `FuzzyQuery` config + engine that generates variant set and batches queries.

## Entry Points

**CLI binary:**
- Location: `src/main.rs`
- Triggers: `rustkmer count|query|stats|dump|merge|fuzzy-query|fuzzy-query-batch|prefix-query ...`
- Responsibilities: Arg parsing, logging init (`env_logger`), query-arg validation, dispatch to `cli::commands::*::execute_*`.

**Library crate root:**
- Location: `src/lib.rs`
- Triggers: Imported by the CLI binary, the PyO3 crate, and integration tests.
- Responsibilities: Re-exports public modules and convenience types (`KmerCounter`, `KmerError`, `ProcessingResult`).

**Python module:**
- Location: `pyo3/src/lib.rs` (`#[pymodule] fn pyrustkmer`)
- Triggers: `import pyrustkmer` from Python.
- Responsibilities: Register all `#[pyclass]` types so they are accessible as `pyrustkmer.PyDatabase`, etc.

## Architectural Constraints

- **Threading:** Single-process; parallelism via Rayon thread pool. `KmerCounter` uses `parking_lot::RwLock` for thread-safe increments, but the count command currently passes `num_threads = 1` (sequential per-file processing) (`src/cli/commands/count.rs:121`–`123`).
- **Global state:** None at module scope. All shared state is instance-scoped on `KmerCounter` / `DatabaseQuery`.
- **K-mer width:** Hard upper bound of k ≤ 64 (u128 encoding) enforced in `KmerCounter::new` and the count command (`src/hash/table.rs:46`, `src/cli/commands/count.rs:42`). The `Kmer` struct notes legacy u64 paths exist for backward compatibility (`src/kmer/mod.rs:21`).
- **Circular imports:** None observed; module DAG is acyclic and follows `cli → {hash, database, fuzzy, io, kmer, output}`.
- **Database format versioning:** `.rkdb` is version 2 (`DATABASE_VERSION`, `src/database/format.rs:14`). Readers contain defensive offsets: if `header.data_offset < 40 || > 1000`, it is forced to 42 (`src/database/query.rs:79`, `src/database/format.rs:290`–`296`).
- **No cross-process coordination:** No server, IPC, or file locking. Concurrent writers to the same `.rkdb` path will corrupt it.

## Anti-Patterns

### Header data_offset reconciliation in every reader

**What happens:** `DatabaseQuery::load_entries` and `RKDatabase::from_file_path` both override the persisted `header.data_offset` when it falls outside `[40, 1000]`, hard-coding `42`.
**Why it's wrong:** The on-disk header field is effectively untrusted; correctness depends on a magic constant replicated in multiple places, so any future header-size change silently breaks readers.
**Do this instead:** Centralize offset computation in one function on `DatabaseHeader` (e.g., `DatabaseHeader::validated_data_offset()`) and call it from all readers. Track and validate the format version rather than patching offset heuristically.

### Counting writes the `.rkdb` format inline in the command handler

**What happens:** `output_binary_format` in `src/cli/commands/count.rs:477`–`535` writes the header and entries directly with `byteorder` calls, duplicating the layout defined in `src/database/format.rs` (`KmerEntry::write_to`, `DatabaseHeader::write_to`).
**Why it's wrong:** Two implementations of the same binary layout; a change to one will desync from the other.
**Do this instead:** Build an `RKDatabase` (or reuse `KmerEntry::write_to` / `DatabaseHeader::write_to`) from the command handler so persistence has a single source of truth.

## Error Handling

**Strategy:** Two-tier. `thiserror::Error` enum `KmerError` for typed library errors; `ProcessingError` (wrapping `anyhow::Error`) for context-rich application errors. `ProcessingResult<T> = Result<T, ProcessingError>` is the canonical return type across the library.

**Patterns:**
- Library functions return `ProcessingResult<T>` (`src/error.rs:63`).
- `KmerError → ProcessingError` via `From` (`src/error.rs:104`).
- CLI uses `anyhow::Result` at `main` and converts errors to user messages with `eprintln!` before `process::exit(1)`.
- `FuzzyError` is a separate `thiserror` enum for fuzzy-query-specific failures (`src/fuzzy/mod.rs:43`).
- PyO3 layer converts errors to Python exceptions via `RustKmerError` (`pyo3/src/errors.rs`).

## Cross-Cutting Concerns

**Logging:** `log` + `env_logger`, initialized in `src/main.rs:13` with default filter `info`. Library code uses the `log` facade; verbose/quiet flags are checked in command handlers and routed to `eprintln!`.

**Validation:** Centralized in `impl Commands` helper methods on `src/cli/args.rs:394`–`552` (`validate_input`, `validate_filtering`, `has_filtering`, `is_directory_mode`). Query-specific validation lives in `src/cli/commands/query.rs::validate_query_args`.

**Authentication:** Not applicable — local CLI/library with no networked auth.

**Memory management:** `memmap2` for memory-mapped reads (`src/io/mmap.rs`); streaming merge (`src/database/streaming_merge.rs`) and prefix-cache merge (`src/database/prefix_cache_merge.rs`) exist specifically to bound memory when merging large databases; `max_memory` CLI flag controls the budget.

---

*Architecture analysis: 2026-06-30*
