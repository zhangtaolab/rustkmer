---
last_mapped_commit: 511b99e5b23614e60426e04a74bcf91a3c5d1a32
last_mapped_at: 2026-10-07
---
# Codebase Structure

**Analysis Date:** 2026-10-07

## Directory Layout

```text
rustkmer/
├── Cargo.toml               # Root package: lib `rustkmer` + bin `rustkmer`
├── src/                     # Core Rust library + CLI binary
│   ├── main.rs              # CLI entry point (clap dispatch, env_logger)
│   ├── lib.rs               # Library root: 10 pub modules, re-exports
│   ├── error.rs             # KmerError / ProcessingError / ProcessingResult
│   ├── cli/                 # Command-line surface
│   │   ├── args.rs          # clap structs/enums for all 8 subcommands
│   │   ├── mod.rs
│   │   └── commands/        # One module per subcommand (execute_*)
│   │       ├── args.rs      # re-export shim
│   │       ├── count.rs     # parallel counting pipeline
│   │       ├── query.rs     # exact lookup modes
│   │       ├── dump.rs      # DB inspection/conversion
│   │       ├── fuzzy.rs     # fuzzy-query + fuzzy-query-batch
│   │       ├── merge.rs     # multi-db merge orchestration
│   │       ├── prefix.rs    # prefix/hybrid query
│   │       ├── stats.rs     # statistics command
│   │       ├── benchmark.rs # ORPHANED — not declared in mod.rs
│   │       └── mod.rs
│   ├── config/              # ConfigManager (file/env/operation layers)
│   │   ├── manager.rs
│   │   └── mod.rs
│   ├── core/                # Cross-cutting infrastructure
│   │   ├── database/        # persistence.rs (JSON metadata + checksummed data)
│   │   ├── metadata.rs      # DatabaseMetadata schema + checksums
│   │   ├── monitoring.rs    # metrics collector, timers
│   │   └── mod.rs
│   ├── database/            # RKDB format, query engines, merge strategies
│   │   ├── format.rs        # DatabaseHeader/KmerEntry/RKDatabase + merge dispatch
│   │   ├── index.rs         # in-memory hash index
│   │   ├── memory.rs        # memory monitor
│   │   ├── merge_config.rs  # MergeConfig/MergeStrategy/MergeStats
│   │   ├── merge_error.rs   # typed merge errors + recovery suggestions
│   │   ├── merge_tests.rs   # ORPHANED — not declared in mod.rs
│   │   ├── prefix_cache_merge.rs   # ExternalSortMerger
│   │   ├── prefix_query.rs         # legacy prefix extraction
│   │   ├── prefix_query_optimized.rs # optimized + hybrid pattern
│   │   ├── query.rs         # DatabaseQuery (disk/cache lookup)
│   │   ├── stats.rs         # streaming stats + output formats
│   │   ├── streaming_merge.rs # ExternalMerger + temp file mgmt
│   │   ├── suffix_query.rs  # suffix extraction (unused by CLI)
│   │   └── mod.rs           # re-exports public types
│   ├── fuzzy/               # Fuzzy query engine
│   │   ├── query.rs         # FuzzyQuery, FuzzyQueryEngine, position mutations
│   │   ├── wildcard.rs      # N-wildcard expansion
│   │   ├── normalization.rs # length normalization (pad/truncate)
│   │   ├── mutation.rs      # Hamming-distance variant generation
│   │   ├── expansion.rs     # expansion orchestration types
│   │   ├── performance.rs   # metrics/optimizer
│   │   └── mod.rs           # FuzzyError, FuzzyResult, constants
│   ├── hash/                # Counting
│   │   ├── table.rs         # KmerCounter (DashMap<u128,u32>) + CounterStats
│   │   ├── filtering.rs     # CountFilter (min/max)
│   │   ├── overflow.rs      # DiskOverflow (unused by main path)
│   │   ├── matrix.rs        # MatrixHashFunction (placeholder, test-only)
│   │   └── mod.rs
│   ├── io/                  # Sequence input
│   │   ├── fasta.rs         # FastaProcessor (bio crate)
│   │   ├── fastq.rs         # FastqProcessor + compressed readers (gz/bz2/xz)
│   │   ├── discovery.rs     # FileDiscovery (walkdir)
│   │   ├── mmap.rs          # MemoryMappedFile
│   │   └── mod.rs
│   ├── kmer/                # K-mer representation
│   │   ├── encoding.rs      # u64 + u128 encode/decode, revcomp
│   │   ├── canonical.rs     # canonicalization (min fwd/revcomp)
│   │   ├── operations.rs    # extract/window/quality helpers
│   │   ├── validation.rs    # u128 encoding validation suite
│   │   └── mod.rs           # Kmer enum (u128 + k_size)
│   ├── memory/              # Memory management
│   │   ├── efficiency.rs    # MemoryManager, PageIterator, reports
│   │   └── mod.rs
│   └── output/              # Legacy writers (public API, unused by CLI)
│       ├── binary.rs        # RSK1 binary format
│       ├── text.rs          # u64-based text format
│       └── mod.rs
├── pyo3/                    # Independent crate `rustkmer-pyo3` → module `pyrustkmer`
│   ├── Cargo.toml           # pyo3 0.27.2; rustkmer path = ".."
│   ├── pyproject.toml       # maturin build backend
│   ├── build.rs / build_with_python.sh
│   ├── src/
│   │   ├── lib.rs           # pymodule `pyrustkmer`; class registration
│   │   ├── counter.rs       # PyCounter, PyCounterStats
│   │   ├── database.rs      # PyDatabase (LoadMode), result types
│   │   ├── fuzzy_query.rs   # PyFuzzyQuery, PyFuzzyResult, PyFuzzyMatch
│   │   ├── prefix_query.rs  # PyPrefixQuery, PyExtendedPrefixQuery, metrics
│   │   ├── formatter.rs     # PyFormatter
│   │   ├── errors.rs        # RustKmerError
│   │   ├── utils.rs
│   │   ├── database_backup.rs          # orphaned backup
│   │   ├── database_new_approaches.rs  # orphaned experiment
│   │   └── *.stage1_fix_backup         # orphaned backup files
│   └── tests/               # pytest suites + conftest
│       ├── conftest.py
│       ├── test_core.py / test_counter.py / test_export.py / test_import.py ...
│       └── utils.py
├── tests/                   # Rust test targets
│   ├── mod.rs               # aggregates unit/integration/property
│   ├── common/              # shared helpers (memory, performance, temp_files)
│   ├── consistency/         # u64/u128 consistency generators
│   ├── contract/            # query contract tests
│   ├── converted/           # pytest assets (pytest.ini)
│   ├── fixtures/            # golden .rkdb files + sha256 manifest
│   ├── integration/         # multi-component tests
│   ├── performance/         # Python perf tests
│   ├── property/            # proptest suites
│   ├── unit/database/       # canonical/query unit tests
│   ├── golden_tests.rs      # byte-identity gate vs fixtures
│   ├── golden_generate.rs   # regenerates golden fixtures
│   ├── round_trip_tests.rs / parallel_count_tests.rs / legacy_readback_tests.rs
│   ├── consistency_tests.rs / cjk_check.rs
│   └── 007-api-compatibility/ # Python API compatibility suite artifacts
├── test_data/               # sample sequences/kmers + generation scripts
├── tools/                   # Independent debug-tools package (3 bins, no deps)
├── examples/                # python/ application/ utils/ bash/ examples
├── docs/                    # mkdocs site (105 markdown files, 16 dirs)
├── scripts/                 # version sync + env test + benchmark scripts
├── .github/workflows/       # ci.yml, docs.yml, performance-regression.yml
├── .cargo/config.toml       # Python linking notes for pyo3 builds
├── .opencode/               # GSD agent tooling (not app code)
├── .planning/               # GSD planning artifacts (this directory)
├── mkdocs.yml               # docs site config
├── .pre-commit-config.yaml  # repo hygiene + Python formatting hooks
└── *.md, *.py               # README, USER_GUIDE, INSTALL, VERSION; stray scripts
```

## Directory Purposes

**`src/cli/`:**
- Purpose: the entire command-line surface
- Contains: clap definitions and one module per subcommand
- Key files: `src/cli/args.rs` (568 lines; enum `Commands` at `:17`), `src/cli/commands/count.rs` (the hot path), `src/cli/commands/mod.rs` (module registry)

**`src/database/`:**
- Purpose: `.rkdb` storage format, read/write/query, and all merge strategies
- Contains: format serialization, query engines, prefix/suffix extraction, stats, merge machinery
- Key files: `src/database/format.rs` (1321 lines — header/entry/RKDatabase/merge dispatch), `src/database/query.rs`, `src/database/streaming_merge.rs`, `src/database/prefix_cache_merge.rs`

**`src/fuzzy/`:**
- Purpose: approximate query engine
- Contains: wildcard, normalization, mutation, expansion, performance modules
- Key files: `src/fuzzy/query.rs`, `src/fuzzy/mutation.rs` (843 lines)

**`src/hash/`:**
- Purpose: concurrency-safe counting and filtering
- Key files: `src/hash/table.rs` (KmerCounter, 840 lines), `src/hash/filtering.rs`

**`src/io/`:**
- Purpose: sequence file input
- Key files: `src/io/fastq.rs` (fastq + all compression readers), `src/io/fasta.rs`, `src/io/discovery.rs`, `src/io/mmap.rs`

**`src/kmer/`:**
- Purpose: 2-bit encoding, canonicalization, validation
- Key files: `src/kmer/encoding.rs`, `src/kmer/canonical.rs`, `src/kmer/validation.rs`

**`src/core/`:**
- Purpose: infrastructure that supports the rest (metadata, persistence, monitoring)
- Key files: `src/core/metadata.rs`, `src/core/database/persistence.rs`, `src/core/monitoring.rs`

**`src/config/`:**
- Purpose: layered configuration management
- Key files: `src/config/manager.rs` (722 lines)

**`src/memory/`:**
- Purpose: mmap lifecycle and paging helpers
- Key files: `src/memory/efficiency.rs`

**`src/output/`:**
- Purpose: legacy public writers (RSK1 binary, u64 text) — not used by the CLI
- Key files: `src/output/binary.rs`, `src/output/text.rs`

**`pyo3/`:**
- Purpose: Python extension crate (cdylib `pyrustkmer`)
- Contains: PyO3 wrapper classes, pytest suites, maturin build config
- Key files: `pyo3/src/lib.rs` (registration), `pyo3/src/database.rs` (2048 lines — `PyDatabase`), `pyo3/src/counter.rs`

**`tests/`:**
- Purpose: all Rust test targets (integration, property, golden, consistency)
- Key files: `tests/golden_tests.rs` (byte-identity gate), `tests/fixtures/golden_manifest.sha256`, `tests/parallel_count_tests.rs`, `tests/consistency_tests.rs`

**`test_data/`:**
- Purpose: sample sequences and k-mer JSON fixtures with generators
- Key files: `test_data/generate_test_data.py`, `test_data/sequences/`, `test_data/kmers/`

**`tools/`:**
- Purpose: standalone debug binaries in an independent Cargo package
- Key files: `tools/Cargo.toml`, `tools/debug_canonical_trace.rs`, `tools/analyze_database.rs`, `tools/verify_canonical.rs`

**`examples/`:**
- Purpose: runnable examples for both surfaces
- Contains: `examples/python/` (PyO3 demos), `examples/application/` (gap-filling FASTA workflows), `examples/bash/`, `examples/utils/`

**`docs/`:**
- Purpose: mkdocs documentation site
- Contains: getting-started, user-guide, api-reference (python/rust), guides, tutorials, performance, implementation, troubleshooting
- Key files: `mkdocs.yml` at repo root, `docs/index.md`

**`scripts/`:**
- Purpose: developer/release automation
- Key files: `scripts/sync_versions.sh`, `scripts/test_all_envs.sh`, `scripts/benchmark_prefix_vs_fuzzy.sh`

**`.github/workflows/`:**
- Purpose: CI gates
- Key files: `.github/workflows/ci.yml` (fmt, clippy, test on ubuntu+macos, pyo3 wheel), `.github/workflows/docs.yml`, `.github/workflows/performance-regression.yml`

## Key File Locations

**Entry Points:**
- `src/main.rs`: CLI binary entry — parse, logging, dispatch
- `src/lib.rs`: library root — module declarations and re-exports
- `pyo3/src/lib.rs`: Python module `pyrustkmer` registration
- `tools/`: three standalone debug binaries

**Configuration:**
- `Cargo.toml`: root crate deps/features/release profile (no workspace)
- `pyo3/Cargo.toml`: binding crate deps (`pyo3 = "0.27.2"`)
- `pyo3/pyproject.toml`: maturin packaging (`module-name = "pyrustkmer"`)
- `.cargo/config.toml`: platform linking notes for Python builds
- `mkdocs.yml`: documentation site
- `.pre-commit-config.yaml`: repo hygiene hooks

**Core Logic:**
- `src/hash/table.rs`: counting (KmerCounter)
- `src/database/format.rs`: `.rkdb` format + RKDatabase + merge dispatch
- `src/kmer/encoding.rs`: encode/decode (u64 and u128)
- `src/cli/commands/count.rs`: counting pipeline (producer/rayon workers)
- `src/database/query.rs`: exact query
- `src/fuzzy/query.rs`: fuzzy engine
- `src/database/streaming_merge.rs`, `src/database/prefix_cache_merge.rs`: merge strategies

**Testing:**
- `tests/`: Rust integration/property/golden targets
- `tests/fixtures/`: golden `.rkdb` files (do not hand-edit)
- `pyo3/tests/`: pytest suites for the Python API
- `scripts/test_all_envs.sh`: environment matrix runner

## Naming Conventions

**Files:**
- Rust modules/directories: `snake_case` (e.g., `prefix_query_optimized.rs`, `streaming_merge.rs`)
- Multi-file modules use a directory + `mod.rs` (e.g., `src/cli/commands/mod.rs`)
- Test files: `*_tests.rs` (e.g., `round_trip_tests.rs`), helper suites as directories (`tests/integration/`)
- Golden fixtures: `golden_k{N}_{canon|noncanon}_{sorted|unsorted}.rkdb`

**Functions:**
- CLI command entry points: `execute_<command>` (e.g., `execute_count`, `execute_fuzzy_query_batch`)
- Validation helpers: `validate_<subject>`, `is_<predicate>`
- Constructors: `new`, `from_<source>` (e.g., `from_file_path`, `from_kmer_pairs`, `from_entries`)
- Conversions/parsers: `parse_<thing>`, `to_<thing>`, `as_<thing>`

**Variables:**
- `snake_case`; encoded k-mers are `encoded`/`encoded_kmer`/`kmer_encoded`; counts are `count`/`u32`; totals use `total_kmers`/`unique_kmers`

**Types:**
- `PascalCase` structs/enums; PyO3 classes prefixed `Py` (`PyDatabase`, `PyCounter`, `PyFuzzyQuery`, `PyPrefixQuery`, `PyFormatter`)
- Error types suffixed `Error` (`KmerError`, `MergeError`, `FuzzyError`, `PersistenceError`)
- Config types often suffixed `Config` (`MergeConfig`, `DiscoveryConfig`, `MemoryConfig`, `PersistenceConfig`); stats suffixed `Stats`/`Statistics`
- Constants: `UPPER_SNAKE_CASE` (`DATABASE_MAGIC`, `DATABASE_VERSION`, `CHUNK_SIZE`, `MAX_KMER_SIZE`)

## Where to Add New Code

**New CLI subcommand:**
1. Add a variant to `Commands` in `src/cli/args.rs` (with clap attrs + a `validate_*` helper if needed)
2. Create `src/cli/commands/<name>.rs` exposing `pub fn execute_<name>(args: &Args) -> ProcessingResult<()>` (mirror `src/cli/commands/prefix.rs`)
3. Register `pub mod <name>;` in `src/cli/commands/mod.rs`
4. Add the dispatch arm in `src/main.rs`

**New core algorithm (database/kmer/io):**
- Put it in the closest existing domain directory (`src/database/`, `src/kmer/`, `src/io/`, `src/hash/`, `src/fuzzy/`), add the `pub mod` line and re-export in that directory's `mod.rs`
- Only add a new top-level module in `src/lib.rs` when the concern is genuinely orthogonal

**New `.rkdb` format capability:**
- Extend `DatabaseHeader`/`KmerEntry` in `src/database/format.rs` (the single source of truth); writing paths must go through `write_to`/`read_from` — never inline bytes
- Update both readers (`RKDatabase::from_file_path`, `DatabaseQuery::open`) and regenerate golden fixtures via `tests/golden_generate.rs`

**New merge strategy:**
- Add a `MergeStrategy` variant in `src/database/merge_config.rs`, implement in `src/database/` (new file or existing `streaming_merge.rs`/`prefix_cache_merge.rs`), wire the selection in `RKDatabase::merge_databases` (`src/database/format.rs:640`), and expose the flag in `MergeArgs` + `src/cli/commands/merge.rs`

**New Python binding:**
- Create `pyo3/src/<name>.rs` with `#[pyclass]`/`#[pymethods]`; declare `mod <name>;` and register `m.add_class::<...>()` in `pyo3/src/lib.rs`; add pytest coverage in `pyo3/tests/test_<name>.py`

**Utilities:**
- Shared CLI helpers: inside `src/cli/` (do not create a `utils` module in the root crate unless reused by `pyo3` too)
- Shared test helpers: `tests/common/` (Rust) or `pyo3/tests/utils.py` (Python)

**Tests:**
- Rust unit-ish tests for a module: `tests/unit/` or `tests/unit/database/`
- Integration across components: `tests/integration/` + top-level `tests/*_tests.rs`
- Property tests: `tests/property/` (proptest)
- Golden/byte-layout: add fixtures to `tests/fixtures/` and assertions to `tests/golden_tests.rs`
- Python: `pyo3/tests/`

## Special Directories

**`.planning/`:**
- Purpose: GSD workflow artifacts (project, roadmap, phases, this codebase map)
- Generated: partially
- Committed: yes

**`.opencode/`:**
- Purpose: GSD agent tooling (agents, commands, skills, hooks)
- Generated: installed by GSD
- Committed: yes

**`tests/fixtures/`:**
- Purpose: committed golden `.rkdb` databases + sha256 manifest + FASTA inputs
- Generated: by `tests/golden_generate.rs` (then never edited by hand)
- Committed: yes

**`pyo3/`:**
- Purpose: separate crate producing the `pyrustkmer` extension; consumes the root crate via path dependency
- Generated: no
- Committed: yes

**`tools/`:**
- Purpose: independent, dependency-free debug binaries
- Generated: no
- Committed: yes

**`test_data/`:**
- Purpose: small sample sequences and k-mer JSON fixtures used by tests/examples
- Generated: partially (`test_data/generate_test_data.py`)
- Committed: yes

**Root-level stray scripts (`fresh_test.py`, `precise_analysis.py`):**
- Purpose: ad-hoc analysis scripts; not wired into any build or CI
- Generated: no
- Committed: yes

---

*Structure analysis: 2026-10-07*
