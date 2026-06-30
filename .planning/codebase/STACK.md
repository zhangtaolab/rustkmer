# Technology Stack

**Analysis Date:** 2026-06-30

## Languages

**Primary:**
- Rust (edition 2021, stable channel 1.80+) - Core library, CLI, and PyO3 native extension. Located in `src/` (CLI + library) and `pyo3/src/` (Python bindings).

**Secondary:**
- Python 3.10+ (Python bindings target `>=3.11` per `pyo3/pyproject.toml`) - PyO3 consumer package `pyrustkmer`, test suites, docs tooling, CI helper scripts. Python tests live in `pyo3/tests/` and `tests/`.
- Bash - Shell scripts in `scripts/` (build helpers, version sync, multi-env test runners, benchmarks).
- Markdown - Documentation in `docs/`, `README.md`, `USER_GUIDE.md`, `INSTALL.md`, `PROJECT_SUMMARY.md`.

## Runtime

**Environment:**
- Rust 1.80+ stable toolchain (no `rust-toolchain.toml` pinned; CI installs via `dtolnay/rust-toolchain@stable`).
- Python 3.10+ required for bindings/dev tooling; `pyo3/pyproject.toml` `requires-python = ">=3.11"` (local venvs `.venv`, `.venv311`, `.venv312`, `.venv313`, `.venvtest` present).
- Native binaries: `rustkmer` (CLI), `pyrustkmer` (Python native extension, `cdylib`).
- Runs on macOS (aarch64/x86_64) and Linux (x86_64-unknown-linux-gnu); CI uses `ubuntu-latest`.

**Package Manager:**
- Cargo (Rust) - lockfiles: `Cargo.lock` (root), `pyo3/Cargo.lock`.
- pip + maturin (Python) - `pyo3/pyproject.toml` declares `maturin>=1.0,<2.0` as build backend.
- Lockfiles: present (Cargo.lock files committed); no `requirements.txt` or `poetry.lock` at root (`docs/requirements.txt` referenced by CI but currently empty).

## Frameworks

**Core:**
- `clap` 4.5.53 (derive feature) - CLI argument parsing. `src/cli/args.rs`, `src/main.rs`.
- `pyo3` 0.27.2 - Rust<->Python FFI bindings. `pyo3/src/lib.rs` declares the `pyrustkmer` module.
- `maturin` >=1.0,<2.0 - Build/distribution backend for the `pyrustkmer` Python wheel (PEP 517). Configured in `pyo3/pyproject.toml` `[tool.maturin]`.
- `bio` 2.0 (RustBio) - FASTA/FASTQ genomics I/O. `src/io/fasta.rs`, `src/io/fastq.rs`.

**Testing:**
- `cargo test` (built-in) + `proptest` 1.5 (property-based testing) - Rust unit/integration tests in `src/` modules and `tests/`.
- `criterion` 0.5 (html_reports) - Rust benchmarks; referenced by `.github/workflows/performance-regression.yml` (`python_cli_comparison` bench, currently commented out in `Cargo.toml`).
- `pytest` >=7.0 + `pytest-cov` >=4.0 + `pytest-benchmark` >=4.0 - Python tests in `pyo3/tests/`. Config in `pyo3/pyproject.toml` `[tool.pytest.ini_options]` (coverage gate `--cov-fail-under=80`).
- `hypothesis` - installed in CI for property-based Python tests.

**Build/Dev:**
- `cargo` (release profile: `lto=true`, `codegen-units=1`, `panic="abort"`) - `Cargo.toml` `[profile.release]`.
- `maturin develop` / `maturin build` - builds and installs the `pyrustkmer` extension. Helper: `pyo3/build_with_python.sh`.
- `mkdocs` + `mkdocs-material` theme - documentation site. Config: `mkdocs.yml` (root) and `docs/mkdocs.yml`; deployed to GitHub Pages.
- `pre-commit` - hooks config in `.pre-commit-config.yaml` (black, isort, pydocstyle, docformatter targeting `python/`).

## Key Dependencies

**Critical (Rust - `Cargo.toml`):**
- `bio` 2.0 - FASTA/FASTQ parsing (`bio::io::fasta::Reader`, `bio::io::fastq::Reader`).
- `memmap2` 0.9 - Memory-mapped file I/O for large databases. `src/io/mmap.rs` (`MemoryMappedFile`).
- `rayon` 1.8 - Data parallelism (parallel merge, thread pools). `src/database/prefix_cache_merge.rs`, `src/cli/commands/merge.rs`.
- `clap` 4.5.53 - CLI derive framework.
- `serde` 1.0.228 (+ `serde_json` 1.0.145, `bincode` 1.3, `toml` 0.8) - Serialization for the RKDB format, config, metadata.
- `byteorder` 1.5 - Little-endian binary I/O for RKDB files. `src/database/format.rs`.
- `hashbrown` 0.14 + `ahash` 0.8 - High-performance hash map for k-mer counting table. `src/hash/`.
- `smallvec` 1.13 - Small-vector optimization for k-mer buffers.
- `flate2` 1.0 (zlib), `bzip2` 0.4, `xz2` 0.1 - Compression (note: `niffler` commented out to avoid zstd issues).

**Critical (PyO3 - `pyo3/Cargo.toml`):**
- `pyo3` 0.27.2 - Python bindings (`#[pymodule]`, `#[pyclass]`, `#[pymethods]`).
- `rustkmer` (path `..`) - Path dependency on the root crate; the bindings wrap `rustkmer::hash::KmerCounter`, `rustkmer::io::*`, `rustkmer::kmer::*`.
- `pyo3-build-config` 0.22 - Build-time PyO3 config (`pyo3/build.rs`).

**Infrastructure (Rust):**
- `thiserror` 2.0.17 + `anyhow` 1.0 - Error handling. `src/error.rs`.
- `parking_lot` 0.12 - Thread-safe `RwLock` for `ConfigManager`. `src/config/manager.rs`.
- `indicatif` 0.17 - Progress bars.
- `inquire` 0.7 - Interactive file selection.
- `walkdir` 2.4 - Directory traversal for input discovery. `src/io/discovery.rs`.
- `csv` 1.3 - CSV output support.
- `tdigest` 0.2 - Streaming quantile estimation.
- `itertools` 0.14 - Iterator utilities.
- `sha2` 0.10 - Hashing for database persistence.
- `chrono` 0.4 (serde) - Timestamps in metadata.
- `log` 0.4 + `env_logger` 0.11 - Logging (initialized in `src/main.rs`).
- `sys-info` 0.9 - System info for monitoring. `src/core/monitoring.rs`.

**Infrastructure (Python - `pyo3/pyproject.toml`):**
- `numpy>=1.21` - Runtime dependency of `pyrustkmer`.
- Dev extras: `black>=23.0`, `flake8>=6.0`, `mypy>=1.0`, `pytest>=7.0`, `pytest-cov>=4.0`, `pytest-benchmark>=4.0`.
- Performance extras: `memory-profiler>=0.60`, `psutil>=5.9`.
- Docs extras: `sphinx>=5.0`, `sphinx-rtd-theme>=1.2`, `sphinx-autoapi>=2.0` (note: actual docs site uses MkDocs, not Sphinx).
- Jupyter extras: `jupyter>=1.0`, `ipywidgets>=8.0`.

## Configuration

**Environment:**
- Configuration is layered: file (`.rustkmerrc`) + environment variables + CLI flags. Managed by thread-safe `ConfigManager` in `src/config/manager.rs`.
- Env var prefix: `RUSTKMER_` (constant `ENV_PREFIX = "RUSTKMER"`). Examples read in `src/config/manager.rs`:
  - `RUSTKMER_MEMORY_LIMIT`, `RUSTKMER_MMAP_THRESHOLD`, `RUSTKMER_PAGE_SIZE`, `RUSTKMER_ADAPTIVE`, `RUSTKMER_FORCE_MMAP`
  - `RUSTKMER_DEFAULT_K`, `RUSTKMER_CANONICAL`, `RUSTKMER_THREADS`, `RUSTKMER_HASH_SIZE`
  - `RUSTKMER_SORT_OUTPUT`, `RUSTKMER_MIN_COUNT`, `RUSTKMER_MAX_COUNT`
  - `RUSTKMER_PROGRESS`, `RUSTKMER_FORMAT`, `RUSTKMER_TIMESTAMPS`, `RUSTKMER_STATISTICS`
  - `RUSTKMER_VERBOSE`, `RUSTKMER_QUIET`, `RUSTKMER_LOG_LEVEL`, `RUSTKMER_LOG_FILE`, `RUSTKMER_STRUCTURED`
- `RAYON_NUM_THREADS` - controls parallelism (`src/cli/commands/merge.rs`).
- `HOME`, `XDG_CONFIG_HOME` - config file discovery.
- `PYTHON_LIB_DIR` - optional Python linking path (`.cargo/config`).
- `env_logger` initialized from env in `src/main.rs` (`RUST_LOG` style via `Env::default().default_filter_or("info")`).
- No `.env` files present (verified: no secrets files exist).

**Build:**
- `Cargo.toml` (root) - main crate `rustkmer` 0.5.0; lib `rlib` + bin `rustkmer`.
- `pyo3/Cargo.toml` - `rustkmer-pyo3` 0.5.0; lib `pyrustkmer` as `cdylib`.
- `pyo3/pyproject.toml` - maturin PEP 517 backend, `[tool.maturin]` with `features = ["pyo3/extension-module"]`, `module-name = "pyrustkmer"`.
- `.cargo/config` - cross-platform Python extension linking flags for macOS (aarch64/x86_64) and Linux.
- `pyo3/build.rs` - PyO3 build config rerun trigger.
- Features: `default = []`, `profiling = []`, `disable-zstd = []` (root); `extension-module` (pyo3).
- Python tooling config: `[tool.black]` (line-length 88, py311), `[tool.mypy]` (strict), `[tool.coverage.*]`, `[tool.pytest.ini_options]`.

## Platform Requirements

**Development:**
- Rust 1.80+ stable, Cargo.
- Python 3.11+ (3.10+ acceptable for CI/docs) with pip + venv.
- maturin for building the Python extension (`maturin develop --release`).
- Optional: valgrind + massif-visualizer (Linux) for memory profiling in CI.
- Pre-commit hooks (`.pre-commit-config.yaml`) require `pre-commit` install.

**Production:**
- Distributes as: native `rustkmer` CLI binary, and `pyrustkmer` Python wheel (manylinux/macOS wheels via maturin).
- Documentation hosted on GitHub Pages (`https://rustkmer.github.io`) via MkDocs Material.
- Custom binary database format `.rkdb` (magic `RKDB`, version 2) and legacy `.rkd` files for storage.

---

*Stack analysis: 2026-06-30*
