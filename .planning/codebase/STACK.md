---
last_mapped_at: 2026-10-18
last_mapped_commit: 51629b5ea7ed323cfb60ef0be9cab2f30f6a2ed6
---
# Technology Stack

**Analysis Date:** 2026-10-18

*Scope note: refreshed from a scoped remap of `.github/`, `.gitignore`, `pyo3/`, `src/`, `tests/` (prior full map: 2026-10-17).*

## Languages

**Primary:**
- Rust (edition 2021, toolchain 1.80+ stable, via `dtolnay/rust-toolchain@stable` in CI) — core library + `rustkmer` CLI binary in `src/`; Python bindings crate in `pyo3/src/`
- Python 3.11+ (`requires-python = ">=3.11"` in `pyo3/pyproject.toml`) — PyO3 test suite in `pyo3/tests/`, cross-validation tests in `tests/` (`tests/007-api-compatibility/`, `tests/converted/`)

**Secondary:**
- Shell — `pyo3/build_with_python.sh`; benchmark harness scripts in `scripts/bench/` (Python stdlib; outside this map's scope, referenced as context)

## Runtime

**Environment:**
- Rust stable channel; no `rust-toolchain.toml` pin
- Python 3.11 (CI `actions/setup-python@v5` pins `'3.11'`); classifiers list 3.11/3.12
- Platforms: macOS, Linux, and Windows — all three CI matrices (`ci.yml` clippy/test/pyo3-build) now include `windows-latest`; benchmark gate runs linux + darwin only

**Package Manager:**
- Cargo — lockfiles `Cargo.lock` and `pyo3/Cargo.lock` committed
- pip + maturin (PEP 517, `build-backend = "maturin"`) for the `pyrustkmer` wheel

## Frameworks

**Core:**
- clap 4.5.53 (derive) — CLI argument parsing (`src/cli/args.rs`, `src/main.rs`)
- PyO3 0.27.2 — Python bindings, `cdylib` crate `rustkmer-pyo3` producing module `pyrustkmer` (`pyo3/src/lib.rs`)
- rayon 1.8 — parallel processing; global pool configured from `--threads` (CLI) and `PyCounter::new` (bindings); thread precedence `--threads > RUSTKMER_THREADS > RAYON_NUM_THREADS > num_cpus` (`src/cli/commands/count.rs:789-869`)
- bio 2.0 — FASTA/FASTQ parsing (`src/io/fasta.rs`, `src/io/fastq.rs`)

**Testing:**
- `cargo test` + proptest 1.5 — Rust unit/integration/property tests in `src/` and `tests/` (coordinated via `tests/mod.rs`)
- criterion 0.5 (html_reports) — declared in `[dev-dependencies]`; the `python_cli_comparison` `[[bench]]` is commented out in `Cargo.toml`; the active benchmark gate is the Python harness at `scripts/bench/` driven by `.github/workflows/benchmark.yml`
- pytest >=7.0 + pytest-cov >=4.0 (`--cov-fail-under=80`) + pytest-benchmark >=4.0 — `pyo3/tests/` (`pyo3/pyproject.toml [tool.pytest.ini_options]`)

**Build/Dev:**
- maturin >=1.0,<2.0 — wheel build (`pyo3/build.rs` + pyo3-build-config 0.22)
- rustfmt + clippy `--all-targets -D warnings` enforced in CI on all three OSes (`.github/workflows/ci.yml`)
- mkdocs + mkdocs-material — docs site (`docs/`, outside scope)

## Key Dependencies

**Critical (root `Cargo.toml`, `rustkmer` 0.5.0):**
- bio 2.0 — FASTA/FASTQ parsing
- memmap2 0.9 — memory-mapped RKDB database files
- serde 1.0.228 + serde_json 1.0.145 + toml 0.8 + bincode 1.3 — serialization (hybrid JSON + binary `.rkdb` persistence)
- byteorder 1.5 — binary I/O (42-byte RKDB header, 20-byte entries)
- thiserror 2.0.17 / anyhow 1.0 — error handling (`src/error.rs`)
- dashmap 6.2.1 — concurrent sharded hash map (pinned to reuse hashbrown 0.14.5)
- hashbrown 0.14 + ahash 0.8 + smallvec 1.13 — high-performance collections
- flate2 1.0 (zlib features only) / bzip2 0.4 / xz2 0.1 — gzip/bzip2/xz input compression (zstd/niffler deliberately disabled; `disable-zstd` feature)
- tempfile 3.12 — PRODUCTION dependency for merge temp dirs (`src/database/temp_lifecycle.rs`, RAII `rustkmer-merge-*` cleanup)
- parking_lot 0.12 — thread-safe locks (`src/config/manager.rs`, counters)

**Critical (`pyo3/Cargo.toml`, `rustkmer-pyo3` 0.5.0):**
- pyo3 0.27.2 (+ pyo3-build-config 0.22 build-dep)
- rustkmer (path dep `..`), plus serde/bincode/byteorder/memmap2/rayon/parking_lot/hashbrown/flate2/bzip2/xz2/log mirrored for binding parity (bzip2/xz2 added for CLI-vs-Python compressed-input parity)

**Infrastructure (root):**
- indicatif 0.17 — progress bars; inquire 0.7 — interactive file selection
- walkdir 2.4 — input discovery (`src/io/discovery.rs`); csv 1.3 — CSV output
- chrono 0.4 (serde) + sha2 0.10 — DB metadata/checksums
- tdigest 0.2 — streaming quantiles; itertools 0.14
- log 0.4 + env_logger 0.11 — logging (`RUST_LOG` gated)
- sys-info 0.9 — system memory detection
- numpy >=1.21 — sole Python runtime dependency

**Dev-only (root):** criterion, proptest, rand 0.8, rand_chacha 0.3, syn 2.0 + proc-macro2 (CJK string-literal lint, `tests/cjk_check.rs`)

## Configuration

**Environment:**
- `RUSTKMER_DEFAULT_K`, `RUSTKMER_THREADS`, `RUSTKMER_VERBOSE` — read in `src/cli/commands/count.rs` / `merge.rs`
- `RAYON_NUM_THREADS` — parallelism fallback (`src/cli/commands/merge.rs:228`, count thread resolution)
- `RUST_LOG` — env_logger level; PyO3 `build_global` warnings surface at `warn`
- `CARGO_TERM_COLOR: always` — set in CI env
- No `.env` files present

**Build:**
- `Cargo.toml` — lib (`rlib`, `src/lib.rs`) + bin `rustkmer` (`src/main.rs`); features: `profiling`, `disable-zstd`; release profile `lto = true`, `codegen-units = 1`, `panic = "abort"`
- `pyo3/Cargo.toml` — `cdylib` `pyrustkmer`; feature `extension-module`; own release profile (opt-level 3, lto, 1 codegen unit, panic=abort)
- `pyo3/pyproject.toml` — maturin backend; `[tool.maturin]` sets `module-name = "pyrustkmer"` and deliberately does NOT set `python-source` (pure-Rust extension; setting it breaks the wheel build)
- `.cargo/config` — cross-platform Python extension link flags (macOS aarch64/x86_64, Linux)

## Platform Requirements

**Development:**
- Rust 1.80+ stable with rustfmt + clippy; `cargo test` is the canonical test command (plus `cargo clippy`, per `CLAUDE.md`)
- Python 3.11+ with maturin for the bindings; numpy >=1.21

**Production:**
- Distributed as the `rustkmer` CLI binary and the `pyrustkmer` wheel (sdist + wheel built per-OS in CI, uploaded as `wheel-${{ matrix.os }}` artifacts)
- CI gate matrix covers ubuntu / macos / windows; benchmark regression gate covers linux + darwin
- Docs deployed to GitHub Pages from `main` (`.github/workflows/docs.yml`, outside scope)

---

*Stack analysis: 2026-10-18*
