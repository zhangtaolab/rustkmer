---
last_mapped_commit: 511b99e5b23614e60426e04a74bcf91a3c5d1a32
last_mapped_at: 2026-10-07
---
# External Integrations

**Analysis Date:** 2026-10-07

## APIs & External Services

**None.** RustKmer is an offline, local-first bioinformatics tool. No network clients or cloud SDKs exist in the dependency graph or source:

- No HTTP stacks in `Cargo.toml` / `pyo3/Cargo.toml` (no reqwest, hyper, tokio, curl, ureq)
- No TCP/UDP usage in `src/` or `pyo3/src/` (grep for `std::net`, `TcpStream`, `UdpSocket` returns nothing)
- No SDKs for AWS/GCP/Azure, sequencing platforms, or telemetry vendors

**Data interchange happens via files and process exit codes only** (CLI stdout/stderr, files on disk).

## Data Storage

**Databases:**
- Custom binary `.rkdb` v2 format, entirely application-managed - no external database engine
  - Format definition and magic-number validation: `src/database/format.rs` (magic header, fixed 42-byte v2 offset, `.rkdb`/`.rkdbz` extensions)
  - Persistence and checksums: `src/core/database/persistence.rs`, `src/core/metadata.rs`
  - Query engines: `src/database/query.rs`, `src/database/prefix_query.rs`, `src/database/suffix_query.rs`
  - Python access via `PyDatabase` with `LoadMode.Preload` / `MemoryMapped` / `Lazy` (`pyo3/src/database.rs`)
- No connection strings or env vars for external data stores

**File Storage:**
- Local filesystem only. Memory-mapped file reads via `memmap2` (`src/io/mmap.rs`, `src/memory/efficiency.rs`)
- Golden binary fixtures committed under `tests/fixtures/*.rkdb` with sha256 manifest (`tests/fixtures/golden_manifest.sha256`)

**Caching:**
- In-process prefix cache only (`src/database/prefix_cache_merge.rs`); no Redis/Memcached or other external cache

## Authentication & Identity

**Auth Provider:**
- None. No accounts, sessions, tokens, or credentials; no auth code in `src/` or `pyo3/src/`.

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, DataDog, OpenTelemetry, etc.)

**Logs:**
- `log` 0.4 facade + `env_logger` 0.11 to stderr; level controlled by `RUST_LOG`, default `info` (`src/main.rs:13`)
- Config-file/env log settings: `RUSTKMER_LOG_LEVEL`, `RUSTKMER_LOG_FILE`, `RUSTKMER_STRUCTURED` (`src/config/manager.rs:387-395`)
- Local memory-pressure introspection via `sys_info::mem_info()` (`src/database/prefix_cache_merge.rs`)
- Stats/benchmark output formats: text, JSON, CSV, TSV (`src/cli/commands/stats.rs:29-31`, `src/cli/commands/benchmark.rs`)

## CI/CD & Deployment

**Hosting:**
- No server deployment. Artifacts are end-user binaries and Python wheels.
- Documentation published to GitHub Pages via `mkdocs gh-deploy` (`.github/workflows/docs.yml`)

**CI Pipeline:**
- `.github/workflows/ci.yml` - merge gate on PRs/pushes to `dev`/`main`: `cargo fmt --check`; `cargo clippy --all-targets -- -D warnings` and `cargo test` on ubuntu + macos; pyo3 `cargo clippy` plus `maturin build` with wheel artifacts uploaded
- `.github/workflows/docs.yml` - MkDocs `build --strict`, pydocstyle check, `mkdocs gh-deploy` to GitHub Pages on `main`/tags, artifact upload/download
- `.github/workflows/performance-regression.yml` - criterion baseline vs PR comparison, memory profiling, PR comment via `actions/github-script@v6`, daily cron at 02:00 UTC
- Third-party actions used: `actions/checkout@v4`, `actions/cache@v4`, `actions/setup-python@v4`/`@v5`, `actions/upload-artifact@v4`, `actions/download-artifact@v4`, `actions/github-script@v6`, `dtolnay/rust-toolchain@stable`
- Only secret consumed is the automatic `GITHUB_TOKEN`; no repository secrets referenced. No self-hosted runners.

**Publishing (documented, not automated):**
- crates.io: `cargo install rustkmer` instructions in `README.md`, `INSTALL.md`, `docs/getting-started/installation.md`
- PyPI / conda-forge / uv: `pip install rustkmer`, `conda install -c conda-forge rustkmer`, `uv add rustkmer` in `README.md` (package metadata name is `pyrustkmer` in `pyo3/pyproject.toml` - naming inconsistency)
- No release/publish workflow exists in `.github/workflows/` (only ci, docs, performance-regression)

## Environment Configuration

**Required env vars:**
- None required for runtime operation

**Optional env vars:**
- `RUSTKMER_*` runtime overrides (21 settings: memory, k-mer, output, logging) - `src/config/manager.rs:296-395`
- `RUSTKMER_THREADS`, `RAYON_NUM_THREADS` - thread pool sizing (`src/cli/commands/count.rs:841`, `src/cli/commands/merge.rs:365`)
- `RUST_LOG` - log filtering
- `HOME`, `XDG_CONFIG_HOME` - config file discovery (`src/config/manager.rs:221-232`)
- `PYO3_BUILD_CONFIG` - PyO3 build-time configuration (`pyo3/build.rs`)

**Secrets location:**
- None in repo. `.env`, `.env.*` are gitignored. CI relies solely on the built-in `GITHUB_TOKEN`.

## Webhooks & Callbacks

**Incoming:**
- None - the tool opens no network listeners or HTTP endpoints

**Outgoing:**
- None from the product itself
- CI only: `actions/github-script@v6` posts benchmark results as PR comments (`.github/workflows/performance-regression.yml`)

## File-Format Integrations (primary external surface)

- **Inputs:** FASTA/FASTQ plain text and compressed `.gz` (flate2/zlib), `.bz2` (bzip2), `.xz` (xz2) - `src/io/fasta.rs`, `src/io/fastq.rs`; directory discovery via walkdir (`src/io/discovery.rs`)
- **Outputs:** k-mer count text/binary (`src/output/text.rs`, `src/output/binary.rs`), JSON/CSV/TSV stats reports, `.rkdb` databases
- `.fxi` index files appear in `examples/application/` (e.g., `Chr10_demo.fa.fxi`) but are not generated by rustkmer source - they are produced by an external tool (pyfastx-style index) used in example workflows

**Stale integration references (files referenced but absent):**
- `.github/workflows/docs.yml` calls `pip install -r docs/requirements.txt`, `python ../scripts/check_broken_links.py`, and `python ../scripts/check_doc_coverage.py` - none exist in the repo
- `.github/workflows/performance-regression.yml` guards on `scripts/check_performance_regression.py`, which does not exist
- `pyo3/build_with_python.sh` and `scripts/test_all_envs.sh` hard-code macOS paths (`/Users/forrest/...`) and reference module name `rustkmer_pyo3` instead of the built `pyrustkmer`

---

*Integration audit: 2026-10-07*
