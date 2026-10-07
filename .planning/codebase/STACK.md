---
last_mapped_commit: 511b99e5b23614e60426e04a74bcf91a3c5d1a32
last_mapped_at: 2026-10-07
---
# Technology Stack

**Analysis Date:** 2026-10-07

## Languages

**Primary:**
- Rust (edition 2021, stable toolchain) - Core CLI + library in `src/` and Python extension crate in `pyo3/src/`. Minimum Rust 1.80.0 per `INSTALL.md`; no `rust-toolchain.toml` and no `rust-version` key in `Cargo.toml`.

**Secondary:**
- Python 3.11+ - PyO3 bindings compiled to native module `pyrustkmer` from `pyo3/src/lib.rs`; Python tests in `pyo3/tests/`, examples in `examples/python/`, data generators in `test_data/`, ad-hoc scripts `fresh_test.py`, `precise_analysis.py`.
- Bash - helper scripts in `scripts/` (`sync_versions.sh`, `test_pyo3_version.sh`, `test_all_envs.sh`) and `pyo3/build_with_python.sh`.

## Runtime

**Environment:**
- Native CLI binary `rustkmer` from `src/main.rs` (declared as `[[bin]]` in `Cargo.toml`).
- Native Python extension `pyrustkmer` (`cdylib`) from `pyo3/src/lib.rs` via PyO3 0.27.2; package built with maturin.
- No async runtime (no tokio/async-std). Parallelism is Rayon thread pools only.

**Package Manager:**
- Cargo - multiple standalone packages, no workspace: root (`Cargo.toml`, lib `rlib` + bin), `pyo3/Cargo.toml` (path-depends on root), `tools/Cargo.toml` (standalone debug utilities, zero dependencies).
- pip/maturin for the Python wheel (`pyo3/pyproject.toml`, build-backend `maturin`).
- Lockfile: **missing/not committed** - `Cargo.lock` is ignored in `.gitignore`; no lockfiles found in repo.

**Versioning:** CLI `0.5.0` and PyO3 `0.5.0`, kept in sync via `scripts/sync_versions.sh` (see `VERSION.md`).

## Frameworks

**Core:**
- clap 4.5.53 (`derive` feature) - CLI argument parsing in `src/cli/args.rs`
- thiserror 2.0.17 + anyhow 1.0 - error types in `src/error.rs` and top-level error handling in `src/main.rs`
- bio 2.0 - FASTA/FASTQ parsing in `src/io/fasta.rs`, `src/io/fastq.rs`, `src/cli/commands/count.rs`
- PyO3 0.27.2 - Python bindings in `pyo3/src/*.rs` (maturin `extension-module` feature)

**Testing:**
- Rust built-in test harness (`cargo test`), suites under `tests/` (unit, integration, contract, property, consistency, golden)
- criterion 0.5 (`html_reports`) - dev-dependency; the `[[bench]]` section is commented out in `Cargo.toml` and no `benches/` directory exists despite `performance-regression.yml` calling `cargo bench`
- proptest 1.5 and tempfile 3.12 - Rust property-based/unit test support
- syn 2.0 + proc-macro2 1.0 - dev-only source-tree introspection for the CJK string-literal lint (used by `tests/cjk_check.rs`)
- pytest >=7, pytest-cov >=4, pytest-benchmark >=4 - Python tests configured in `pyo3/pyproject.toml` with coverage `--cov-fail-under=80`
- hypothesis is installed ad hoc in `.github/workflows/performance-regression.yml` but is not declared in any manifest

**Build/Dev:**
- maturin >=1.0,<2.0 - Python wheel builds (`pyo3/pyproject.toml`, CI job `pyo3-build`)
- pre-commit - hooks in `.pre-commit-config.yaml` (trailing whitespace, yaml/json/toml checks, black 24.1.1, isort 5.13.2, pydocstyle 6.3.0, docformatter 1.7.5)
- MkDocs Material - docs config in `mkdocs.yml` and `docs/mkdocs.yml`

## Key Dependencies

**Critical:**
- rayon 1.8 - parallel k-mer counting and merge paths (`src/cli/commands/count.rs`, `src/cli/commands/merge.rs`, `src/hash/table.rs`, `src/database/prefix_cache_merge.rs`)
- dashmap 6.2.1 - concurrent sharded hash map, pinned to reuse hashbrown 0.14.5 (`src/hash/table.rs`)
- hashbrown 0.14.5 + ahash 0.8 - hash table backing (`src/database/format.rs`)
- memmap2 0.9 - memory-mapped database IO (`src/io/mmap.rs`, `src/memory/efficiency.rs`)
- flate2 1.0 (zlib feature) + bzip2 0.4 + xz2 0.1 - `.gz`/`.bz2`/`.xz` input decoding (`src/io/fastq.rs:68-76`; zstd deliberately disabled, `niffler` commented out)
- serde 1.0.228 + serde_json 1.0.145 + toml 0.8 + bincode 1.3 - config, metadata, and database persistence (`src/config/manager.rs`, `src/core/database/persistence.rs`, `src/core/metadata.rs`)
- sha2 0.10 - database checksums (`src/core/database/persistence.rs`, `src/core/metadata.rs`, `src/cli/commands/count.rs`)
- tdigest 0.2 - streaming quantile estimation (`src/database/stats.rs`)
- sys-info 0.9 - host memory detection for adaptive cache decisions (`src/database/prefix_cache_merge.rs`)

**Infrastructure:**
- parking_lot 0.12 - locking (`src/config/manager.rs`, `src/memory/efficiency.rs`)
- byteorder 1.5 + csv 1.3 + walkdir 2.4 + itertools 0.14 + smallvec 1.13 - binary IO, CSV output, input discovery, iterator utilities
- indicatif 0.17 - progress reporting (`src/database/format.rs`)
- log 0.4 + env_logger 0.11 - logging (`src/main.rs:13`)
- Discrepancies: `inquire 0.7` and `chrono 0.4` are declared in `Cargo.toml` but have no usage in `src/` (grep found zero references); `numpy>=1.21` is a declared Python dependency in `pyo3/pyproject.toml` but no numpy usage exists in `pyo3/src/`

**Python binding crate (`pyo3/Cargo.toml`):**
- pyo3 0.27.2 (note: `build-dependencies` pins `pyo3-build-config = "0.22"`, a version mismatch)
- Path dependency on root crate; also serde/serde_json/bincode, byteorder, memmap2, anyhow, thiserror, parking_lot, hashbrown, rayon, flate2, bzip2, xz2, log

## Configuration

**Environment:**
- Runtime config file `.rustkmerrc` (TOML), searched in: current directory -> `$HOME/.rustkmerrc` -> `$XDG_CONFIG_HOME/rustkmer/.rustkmerrc` (`src/config/manager.rs:14-18, 211-237`)
- Environment overrides with `RUSTKMER_` prefix (21 variables): `RUSTKMER_MEMORY_LIMIT`, `RUSTKMER_MMAP_THRESHOLD`, `RUSTKMER_PAGE_SIZE`, `RUSTKMER_ADAPTIVE`, `RUSTKMER_FORCE_MMAP`, `RUSTKMER_DEFAULT_K`, `RUSTKMER_CANONICAL`, `RUSTKMER_THREADS`, `RUSTKMER_HASH_SIZE`, `RUSTKMER_SORT_OUTPUT`, `RUSTKMER_MIN_COUNT`, `RUSTKMER_MAX_COUNT`, `RUSTKMER_PROGRESS`, `RUSTKMER_FORMAT`, `RUSTKMER_TIMESTAMPS`, `RUSTKMER_STATISTICS`, `RUSTKMER_VERBOSE`, `RUSTKMER_QUIET`, `RUSTKMER_LOG_LEVEL`, `RUSTKMER_LOG_FILE`, `RUSTKMER_STRUCTURED` (`src/config/manager.rs:296-395`)
- Threading: `RUSTKMER_THREADS`, falling back to `RAYON_NUM_THREADS` (`src/cli/commands/count.rs:841-844`, `src/cli/commands/merge.rs:365`)
- Logging: `RUST_LOG` via env_logger, default filter `info` (`src/main.rs:13`)
- No `.env` files tracked; `.env`, `.env.*` are gitignored

**Build:**
- `Cargo.toml` - release profile: `lto = true`, `codegen-units = 1`, `panic = "abort"`; features `default = []`, `profiling`, `disable-zstd`
- `.cargo/config.toml` - per-target rustflags stubs for cross-platform Python extension linking (macOS targets, Linux commented examples)
- `pyo3/build.rs` - emits `cargo:rerun-if-env-changed=PYO3_BUILD_CONFIG`
- `pyo3/pyproject.toml` - maturin + `[tool.pytest.ini_options]` (coverage threshold 80), black (line-length 88, py311), mypy strict, coverage config
- `.pydocstylerc` - Google convention docstring linting
- `.pre-commit-config.yaml` - Python hook file filters point at `^python/.*\.py$`; a `python/` directory does not exist in the repo (stale filter)

## Platform Requirements

**Development:**
- Rust 1.80.0+ stable with cargo/rustc (`INSTALL.md`)
- Python 3.11+ for bindings (`pyo3/pyproject.toml` `requires-python = ">=3.11"`); README/INSTALL state 3.10-3.12 tested, with README also mentioning Python 3.8+ in one place
- maturin >=1.0,<2.0 for extension builds; conda/uv installation paths documented in `README.md`
- Optional: pre-commit, MkDocs Material (+ `docs/requirements.txt`, which is referenced by `.github/workflows/docs.yml` but does not exist)

**Production:**
- Self-contained native binary compiled to `target/release/rustkmer`; README claims Linux, macOS, Windows support
- Python wheel (`pyrustkmer`) installable via pip; distribution channels documented: crates.io (`cargo install rustkmer`), PyPI/conda-forge/uv in `README.md` and `docs/getting-started/installation.md`
- CI runs on `ubuntu-latest` and `macos-latest` (`.github/workflows/ci.yml`); no Windows CI

---

*Stack analysis: 2026-10-07*
