---
last_mapped_commit: 0f442541636e002a322db9d1ba091ff046e62284
last_mapped_at: 2026-10-08
---
# Technology Stack

**Analysis Date:** 2026-10-08

## Languages

**Primary:**
- Rust (edition 2021, toolchain 1.80+ stable; local rustc 1.99.0) - core library + CLI binary, all of `src/`
- Python 3.11+ (requires-python >=3.11) - PyO3 bindings package `pyo3/`, docs tooling, test scripts (`fresh_test.py`, `precise_analysis.py`)

**Secondary:**
- Shell - `pyo3/build_with_python.sh`, `scripts/` helpers

## Runtime

**Environment:**
- Rust stable channel via `dtolnay/rust-toolchain@stable` in CI
- Python 3.11/3.12 for the `pyrustkmer` extension module (classifiers list 3.11 and 3.12)

**Package Manager:**
- Cargo (lockfiles: `Cargo.lock`, `pyo3/Cargo.lock` — both present)
- pip + maturin for the Python wheel (`pyo3/pyproject.toml`, build-backend = maturin)

## Frameworks

**Core:**
- clap 4.5.53 (derive) - CLI argument parsing (`src/cli/`)
- PyO3 0.27.2 - Python bindings (`pyo3/src/lib.rs`, module `pyrustkmer`, cdylib crate)
- rayon 1.8 - parallel processing; global pool configured from `--threads` / PyCounter::new

**Testing:**
- cargo test + proptest 1.5, criterion 0.5 (html_reports) - Rust side
- pytest >=7.0, pytest-cov, pytest-benchmark - Python side (`pyo3/tests/`, root `tests/`)

**Build/Dev:**
- maturin >=1.0 <2.0 - builds the PyO3 wheel (`pyo3/build.rs` + `pyo3-build-config 0.22`)
- mkdocs + mkdocs-material - docs site (`mkdocs.yml`, `docs/`)
- rustfmt + clippy enforced in CI (`.github/workflows/ci.yml`)

## Key Dependencies

**Critical (root `Cargo.toml`, rustkmer 0.5.0):**
- bio 2.0 - FASTA/FASTQ parsing
- memmap2 0.9 - memory-mapped RKDB database files
- serde 1.0 + serde_json 1.0 + toml 0.8 + bincode 1.3 - serialization (hybrid JSON + binary `.rkdb` persistence)
- byteorder 1.5 - binary I/O (42-byte RKDB headers)
- thiserror 2.0.17 / anyhow 1.0 - error handling
- dashmap 6.2.1 - concurrent sharded hash map (pinned to reuse hashbrown 0.14.5)
- hashbrown 0.14, ahash 0.8, smallvec 1.13 - high-performance collections
- flate2 1.0 (zlib only) / bzip2 0.4 / xz2 0.1 - gzip/bzip2/xz input compression (zstd/niffler deliberately disabled)
- tempfile 3.12 - PRODUCTION dependency for merge temp dirs (`src/database/temp_lifecycle.rs`)

**Critical (pyo3 sub-crate `pyo3/Cargo.toml`, rustkmer-pyo3 0.5.0):**
- pyo3 0.27.2 + pyo3-build-config 0.22 (build-dep)
- rustkmer (path dep `..`), plus serde/bincode/byteorder/memmap2/rayon/parking_lot/hashbrown/bzip2/xz2 mirrored for binding parity

**Infrastructure:**
- indicatif 0.17 - progress bars; inquire 0.7 - interactive file selection
- walkdir 2.4 - directory traversal; csv 1.3 - CSV output
- chrono 0.4 (serde) + sha2 0.10 - DB metadata/checksums
- tdigest 0.2 - streaming quantile estimation
- log 0.4 + env_logger 0.11 - logging (RUST_LOG gated)
- sys-info 0.9 - system memory detection
- numpy >=1.21 - Python-side array support

**Dev-only (root):** criterion, proptest, rand 0.8, rand_chacha 0.3, syn 2.0 + proc-macro2 (source-tree lint tooling)

## Configuration

**Environment:**
- `RUSTKMER_DEFAULT_K`, `RUSTKMER_THREADS`, `RUSTKMER_VERBOSE` — read in `src/cli/commands/count.rs` and `src/cli/commands/merge.rs`
- `RUST_LOG` — env_logger level (PyO3 `build_global` warnings surface at `warn`)
- `CARGO_TERM_COLOR` — set in CI
- No `.env` files present

**Build:**
- `Cargo.toml` — root lib (`rlib`, `src/lib.rs`) + bin `rustkmer` (`src/main.rs`); features: `profiling`, `disable-zstd`
- `pyo3/Cargo.toml` — cdylib `pyrustkmer`; features: `extension-module`; `[package.metadata.maturin]` module-name `pyrustkmer`
- Release profiles: `lto = true`, `codegen-units = 1`, `panic = "abort"` (both crates)

## Platform Requirements

**Development:**
- Rust stable toolchain (1.80+), cargo fmt/clippy
- Python 3.11+ with maturin for the bindings; numpy >=1.21
- macOS- and Linux-supported (CI matrix: ubuntu-latest, macos-latest)

**Production:**
- Distributed as the `rustkmer` CLI binary and the `pyrustkmer` wheel (sdist + wheel via `maturin build` in CI)
- Docs deployed to GitHub Pages from `main` (`.github/workflows/docs.yml`)

---

*Stack analysis: 2026-10-08*
