# Codebase Structure

**Analysis Date:** 2026-06-30

## Directory Layout

```
rustkmer/
├── src/                    # Core Rust library + CLI binary (the `rustkmer` crate)
│   ├── lib.rs              # Crate root: declares public modules, re-exports KmerCounter/errors
│   ├── main.rs             # CLI binary entry point (clap dispatch)
│   ├── error.rs            # KmerError (thiserror) + ProcessingError (anyhow)
│   ├── cli/                # CLI surface: arg definitions + command handlers
│   ├── config/             # Configuration management
│   ├── core/               # Metadata, monitoring/metrics, persistence facade
│   ├── database/           # RKDB binary format, query engines, merge strategies
│   ├── fuzzy/              # Fuzzy/wildcard/mutation query engine
│   ├── hash/               # KmerCounter + count filtering
│   ├── io/                 # FASTA/FASTQ parsing, memory mapping, file discovery
│   ├── kmer/               # 2-bit encoding, canonicalization, validation
│   ├── memory/             # Memory-efficiency utilities
│   └── output/             # Binary + text output writers
├── pyo3/                   # Separate crate (`rustkmer-pyo3`) producing the `pyrustkmer` cdylib
│   ├── Cargo.toml          # crate-type = ["cdylib"], depends on `rustkmer` by path
│   ├── build.rs            # PyO3 build config
│   ├── pyproject.toml      # Maturin/setuptools-rust build config
│   ├── src/                # #[pyclass] wrappers over the core crate
│   └── tests/              # Python pytest suite for the binding
├── tests/                  # Rust integration/unit/property/contract tests
├── examples/               # Bash, Python, and application usage examples + sample data
├── docs/                   # MkDocs documentation source
├── scripts/                # Test runner + benchmark + version-sync shell scripts
├── tools/                  # Auxiliary tooling
├── test_data/              # Shared sample databases/kmers/sequences
├── specs/                  # Spec notes (sparse)
├── Cargo.toml              # Workspace-less root crate manifest
└── Cargo.lock
```

## Directory Purposes

**`src/cli/`:**
- Purpose: All CLI presentation logic.
- Contains: `args.rs` (clap `Args`/`Commands` enum + validation helpers), `commands/` (one module per subcommand: `count`, `query`, `stats`, `dump`, `merge`, `fuzzy`, `prefix`, `benchmark`).
- Key files: `src/cli/args.rs`, `src/cli/commands/mod.rs`, `src/cli/commands/count.rs`.

**`src/database/`:**
- Purpose: RKDB format and all read/query/merge strategies.
- Contains: format definition, in-memory + streaming query, prefix/hybrid/suffix query, merge (in-memory, streaming, prefix-cache).
- Key files: `src/database/format.rs` (canonical format), `src/database/query.rs` (query engine), `src/database/streaming_merge.rs`, `src/database/prefix_query_optimized.rs`, `src/database/prefix_cache_merge.rs`.

**`src/hash/`:**
- Purpose: Counting data structures.
- Contains: `KmerCounter` (thread-safe), count filtering, overflow handling, hash matrix.
- Key files: `src/hash/table.rs`, `src/hash/filtering.rs`.

**`src/kmer/`:**
- Purpose: Nucleotide encoding/decoding and canonicalization.
- Contains: `encoding.rs` (u64 + u128 encoders/decoders), `canonical.rs` (reverse-complement canonical form), `operations.rs`, `validation.rs`, `mod.rs` (`Kmer` struct).
- Key files: `src/kmer/encoding.rs`, `src/kmer/canonical.rs`.

**`src/io/`:**
- Purpose: File input (parsing, discovery, memory mapping) for FASTA/FASTQ (incl. compressed).
- Contains: `fasta.rs`, `fastq.rs`, `discovery.rs`, `mmap.rs`.
- Key files: `src/io/fasta.rs` (`FastaProcessor`, `validate_fasta_file`), `src/io/discovery.rs` (`FileDiscovery`, `DiscoveryConfig`).

**`src/fuzzy/`:**
- Purpose: Fuzzy query — wildcard expansion, length normalization, Hamming mutation variants.
- Contains: `query.rs` (engine), `expansion.rs`, `mutation.rs`, `normalization.rs`, `wildcard.rs`, `performance.rs` (metrics).
- Key files: `src/fuzzy/query.rs`, `src/fuzzy/expansion.rs`.

**`src/output/`:**
- Purpose: Serialize counts to disk. `binary.rs` and `text.rs` writers. Note the count command also writes the `.rkdb` layout inline (see ARCHITECTURE.md anti-patterns).

**`src/core/`:**
- Purpose: Cross-cutting persistence/metadata/monitoring facade. `database/` (persistence config), `metadata.rs` (DatabaseMetadata, schema), `monitoring.rs` (metrics, profiling-gated).

**`src/config/`:** Configuration manager.

**`src/memory/`:** Memory-efficiency helpers.

**`pyo3/src/`:**
- Purpose: Python bindings; each file is a `#[pyclass]` wrapper.
- Key files: `lib.rs` (module registration), `database.rs` (`PyDatabase`, `LoadMode`, `PyQueryResult`), `counter.rs` (`PyCounter`), `fuzzy_query.rs`, `prefix_query.rs`, `formatter.rs`, `errors.rs` (`RustKmerError`).
- Note: `database_backup.rs` and `database_new_approaches.rs` are exploratory/legacy files in this directory.

**`tests/`:**
- Purpose: Rust test suites organized by kind.
- Contains: `unit/`, `integration/`, `contract/`, `property/`, `consistency/`, `performance/` (Python), `common/` (shared helpers), `fixtures/` (test FASTA + JSON k-mer fixtures), `007-api-compatibility/` and `converted/` (Python pytest suites under `tests/`).

**`examples/`:**
- Purpose: Demonstrations. `bash/` (CLI usage scripts), `python/` (PyO3 API demos), `application/` (real-world FASTA gap-filling scripts + sample data), `utils/` (data prep), `data/` (sample genome).

**`docs/`:** MkDocs Material site source (`mkdocs.yml` at repo root). Subdirs: `getting-started/`, `user-guide/`, `api-reference/`, `guides/`, `examples/`, `tutorials/`, `troubleshooting/`, `dev-guide/`, `implementation/`, `performance/`.

**`scripts/`:** Shell helpers: `test_current.sh`, `test_all_envs.sh`, `test_pyo3_version.sh`, `benchmark_prefix_vs_fuzzy.sh`, `sync_versions.sh`.

## Key File Locations

**Entry Points:**
- `src/main.rs`: CLI binary entry.
- `src/lib.rs`: Library crate root (public modules + re-exports).
- `pyo3/src/lib.rs`: Python module entry (`#[pymodule] pyrustkmer`).

**Configuration:**
- `Cargo.toml`: Root crate manifest (library `rlib` + binary `rustkmer`).
- `pyo3/Cargo.toml`: PyO3 cdylib manifest.
- `pyo3/pyproject.toml`: Python build config (maturin).
- `pyo3/build.rs`: PyO3 build script.
- `mkdocs.yml`: Documentation site config.
- `.cargo/`, `.pre-commit-config.yaml`, `.pydocstylerc`: Tooling config.

**Core Logic:**
- `src/database/format.rs`: RKDB binary format (header/entry/database).
- `src/hash/table.rs`: `KmerCounter`.
- `src/database/query.rs`: `DatabaseQuery`.
- `src/database/streaming_merge.rs`: External-sort merge.
- `src/kmer/encoding.rs`, `src/kmer/canonical.rs`: encoding/canonicalization.
- `src/fuzzy/query.rs`: fuzzy query engine.

**Testing:**
- `tests/`: Rust test suites (see above).
- `pyo3/tests/`: Python pytest suite for the binding (`conftest.py`, `test_core.py`, `test_counter.py`, `test_export.py`, `test_import.py`, etc.).
- `tests/fixtures/`: Shared test FASTA + JSON k-mer fixtures.
- `tests/common/`: Shared Rust test helpers (`memory.rs`, `performance.rs`, `temp_files.rs`).

## Naming Conventions

**Files (Rust):**
- `snake_case.rs` for modules and files: `prefix_query_optimized.rs`, `streaming_merge.rs`.
- `mod.rs` for directory module roots: `src/database/mod.rs`, `src/cli/commands/mod.rs`.
- Command handler files match the subcommand verb: `count.rs`, `query.rs`, `merge.rs`, `fuzzy.rs`, `prefix.rs`, `stats.rs`, `dump.rs`.

**Files (Python):**
- `snake_case.py`: `test_counter.py`, `conftest.py`.
- PyO3 wrapper files are named by the Python class domain, lowercase: `database.rs`, `counter.rs`, `fuzzy_query.rs`, `prefix_query.rs`.

**Directories:**
- `snake_case` for Rust/Python source dirs: `commands/`, `fixtures/`, `unit/`, `integration/`.
- `kebab-case` for documentation dirs: `user-guide/`, `api-reference/`, `dev-guide/`.

**Types:**
- Rust structs/enums: `UpperCamelCase` — `KmerCounter`, `RKDatabase`, `DatabaseHeader`, `KmerEntry`, `DatabaseQuery`, `FuzzyQueryEngine`.
- PyO3 classes prefixed `Py`: `PyDatabase`, `PyCounter`, `PyQueryResult`, `PyFuzzyQuery`, `PyPrefixQuery`, `PyFormatter`.

**Functions/Methods:**
- `snake_case`: `execute_count`, `canonical_kmer_u128`, `encode_kmer_bytes_u128`, `from_file_path`.
- Command entry points follow `execute_<verb>`: `execute_count`, `execute_query`, `execute_merge`, `execute_fuzzy_query`, `execute_prefix_query`.

**Constants:**
- `SCREAMING_SNAKE_CASE`: `DATABASE_MAGIC`, `DATABASE_VERSION`, `DEFAULT_MAX_VIANTS`.

## Where to Add New Code

**New CLI subcommand:**
- Add a variant to `Commands` in `src/cli/args.rs`.
- Add a dispatch arm in `src/main.rs`.
- Create `src/cli/commands/<verb>.rs` with `pub fn execute_<verb>(args: &Args) -> ProcessingResult<()>` and register it in `src/cli/commands/mod.rs`.

**New library module:**
- Create `src/<module>/` with a `mod.rs`.
- Declare `pub mod <module>;` in `src/lib.rs`.
- Re-export key types from `src/lib.rs` if they should be part of the public API.

**New database query/read strategy:**
- Add a module under `src/database/` and declare it in `src/database/mod.rs`.
- Read via the shared `DatabaseHeader`/`KmerEntry` types in `src/database/format.rs` (do not re-implement the binary layout).

**New PyO3-exposed class:**
- Add a `#[pyclass]` wrapper file under `pyo3/src/` and `mod <name>;` in `pyo3/src/lib.rs`.
- Register it with `m.add_class::<<T>>()?` in the `#[pymodule] fn pyrustkmer` function (`pyo3/src/lib.rs:37`).

**New tests:**
- Rust integration tests: add a file under the appropriate `tests/<kind>/` dir (or a new `tests/<kind>/` dir).
- Shared Rust test helpers: `tests/common/`.
- Python binding tests: `pyo3/tests/test_*.py`.
- Test data: `tests/fixtures/` (small) or `test_data/` (larger shared assets).

**Utilities:**
- Shared shell helpers: `scripts/`.
- Auxiliary tools: `tools/`.

## Special Directories

**`target/`:**
- Purpose: Rust build output (cargo).
- Generated: Yes.
- Committed: No (in `.gitignore`).

**`pyo3/target/`:**
- Purpose: PyO3 cdylib build output.
- Generated: Yes.
- Committed: No.

**`.venv*` (`.venv`, `.venv311`, `.venv312`, `.venv313`, `.venvtest`):**
- Purpose: Python virtual environments for multi-version testing.
- Generated: Yes.
- Committed: No.

**`docs/`:**
- Purpose: MkDocs documentation source.
- Generated: No.
- Committed: Yes. Built site is not committed.

**`examples/application/`:**
- Purpose: Real-world application scripts and sample FASTA data (including `.fa.fxi` indexes).
- Generated: Partially (`.fa.fxi`, `__pycache__/`, `.pytest_cache/`, `htmlcov/` are byproducts).
- Committed: Yes for scripts/data; byproducts should be gitignored.

**`test_data/`:**
- Purpose: Shared sample databases (`.rkdb`), k-mer lists, and sequences used across tests and examples.
- Generated: No.
- Committed: Yes.

**`.planning/`:**
- Purpose: GSD workflow artifacts (plans, codebase maps).
- Generated: By tooling.
- Committed: As per project policy.

---

*Structure analysis: 2026-06-30*
