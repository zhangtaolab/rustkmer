# External Integrations

**Analysis Date:** 2026-06-30

## APIs & External Services

**None.** rustkmer is a fully offline, local-first bioinformatics toolkit. There are no HTTP clients, no remote API SDKs, and no network calls in the core codebase.

- Verified: no `reqwest`, `hyper`, `isahc`, `ureq`, `tonic`, or `tokio` networking crates in `Cargo.toml` or `pyo3/Cargo.toml`.
- No `import requests` / `import httpx` patterns in Python sources.
- The only "external" dependency is the local Python interpreter, accessed via PyO3 FFI (not a network service).

## Data Storage

**Databases:**
- Custom binary format only - no SQL/NoSQL/embedded database (no SQLite, Postgres, Redis, etc.).
- Primary format: `.rkdb` files (RKDB format), magic bytes `b"RKDB"`, format version 2. Defined in `src/database/format.rs` (`DATABASE_MAGIC`, `DATABASE_VERSION`, `DatabaseHeader`).
  - Header fields: `magic`, `version`, `kmer_size` (u8), `total_kmers` (u64), `sorted` (bool), `data_offset` (u64), `index_offset` (u64), `canonical` (bool), `unique_kmers`, `file_size`. Standard header is 42 bytes.
  - Supporting modules: `src/database/index.rs` (indexing), `src/database/query.rs`, `src/database/prefix_query.rs`, `src/database/prefix_query_optimized.rs`, `src/database/suffix_query.rs`, `src/database/stats.rs`, `src/database/memory.rs`, `src/database/streaming_merge.rs`, `src/database/prefix_cache_merge.rs`.
- Secondary binary output format: `RSK1` (Rust K-mer format v1) via `src/output/binary.rs` (`BinaryHeader`, magic `b"RSK1"`).
- Legacy/interchange: `.rkd` files (e.g. `merged_test.rkd`, `simple_db1.rkd` in repo root) and text exports (`.txt`).
- Connection: filesystem path only; no connection string or env var. Opened via memory mapping (see File Storage).

**Connection env vars:** None. Database paths are passed as CLI args (`--database <path>`) or Python API arguments (`PyDatabase`).

**Client:** Direct `std::fs` file I/O + `memmap2` memory mapping. No ORM/database client library.

**File Storage:**
- Local filesystem only. No cloud object storage (no S3, GCS, Azure Blob SDKs).
- Memory-mapped file access via `memmap2` (`Mmap`, `MmapOptions`) in `src/io/mmap.rs` (`MemoryMappedFile` struct) for large RKDB files and large FASTA/FASTQ inputs.
- Input discovery (recursive directory walks) via `walkdir` in `src/io/discovery.rs`.
- Compression support (local only): `flate2` (gzip/zlib), `bzip2`, `xz2`. Note: `niffler` is commented out in `Cargo.toml` to avoid zstd compilation issues.

**Caching:**
- Local prefix-cache files for merge operations (`src/database/prefix_cache_merge.rs`). Examples in repo root: `merged_prefix_cache.rkdb`, `merged_prefix_cache_debug.rkdb`, `merged_prefix_cache_fixed.rkdb`.
- No distributed/remote cache (no Redis, memcached).

## Authentication & Identity

**None.** No authentication, authorization, or identity provider integration.

- No auth code paths in `src/` or `pyo3/src/`.
- No JWT/OAuth/SSO libraries in dependencies.
- No `api_key`, `token`, `password`, or `login` references in source (verified via grep).

## Monitoring & Observability

**Error Tracking:**
- None. No Sentry, Bugsnag, or remote error reporting.

**Logs:**
- Local logging only via the `log` crate + `env_logger`. Initialized in `src/main.rs` with `env_logger::Builder::from_env(Env::default().default_filter_or("info"))`.
- Log level controlled by `RUSTKMER_LOG_LEVEL` / `RUSTKMER_LOG_FILE` env vars (read in `src/config/manager.rs`).
- Runtime monitoring (system info) via `sys-info` in `src/core/monitoring.rs`.
- Performance benchmarking (local): criterion reports uploaded as CI artifacts only; not shipped to any external metrics service.

## CI/CD & Deployment

**Hosting:**
- Source: GitHub (`https://github.com/rustkmer/rustkmer`).
- Documentation: GitHub Pages (`https://rustkmer.github.io`), deployed by `mkdocs gh-deploy` from `.github/workflows/docs.yml`.
- Python package: intended for PyPI distribution as `pyrustkmer` (maturin-built wheel; no publish workflow file detected in `.github/workflows/`).

**CI Pipeline:**
- GitHub Actions, two workflows in `.github/workflows/`:
  - `docs.yml` - Documentation Build and Deploy. Triggers: push to `main`, tags `v*`, PRs touching `docs/**`, `python/**`, `mkdocs.yml`, `.pydocstylerc`. Builds MkDocs strictly, runs `scripts/check_broken_links.py` and `scripts/check_doc_coverage.py`, deploys to GitHub Pages on `main`/tags using `secrets.GITHUB_TOKEN`.
  - `performance-regression.yml` - Performance Regression Tests. Triggers: push to `main`/`develop`/`012-python-bindings-complete`, PRs to `main`/`develop`, daily cron (`0 2 * * *`). Jobs: `baseline-benchmarks` (criterion `--save-baseline baseline`), `performance-comparison` (10% threshold via `scripts/check_performance_regression.py`, PR comment via `actions/github-script@v6`), `memory-profiling` (valgrind + `scripts/memory_profiling_test.py`), `performance-trend-analysis` (pandas/matplotlib via `scripts/analyze_performance_trends.py`, `scripts/generate_performance_report.py`), `notify-performance-regression` (auto-opens a `performance`/`regression`/`bug` issue on failure).
- CI uses: `actions/checkout@v4`, `actions/setup-python@v4` (3.10), `dtolnay/rust-toolchain@stable`, `actions/cache@v4`, `actions/upload-artifact@v4`, `actions/download-artifact@v4`, `actions/github-script@v6`.
- Secrets used: `secrets.GITHUB_TOKEN` only (for Pages deploy and PR comments). No third-party API tokens.
- Local hooks: `.pre-commit-config.yaml` (pre-commit-hooks v4.5.0, black 24.1.1, isort 5.13.2, pydocstyle 6.3.0, docformatter 1.7.5) targeting `python/`.

## Environment Configuration

**Required env vars:**
- None required to run. All behavior has defaults. Optional tuning vars use the `RUSTKMER_` prefix (see STACK.md "Configuration").
- `RAYON_NUM_THREADS` - optional, overrides parallelism.
- Build-time: `PYO3_BUILD_CONFIG` (rerun trigger in `pyo3/build.rs`), `PYTHON_LIB_DIR` (optional, `.cargo/config`).

**Secrets location:**
- No secrets required. `.env*` files do not exist (verified). No credentials/keys/`.pem`/`.npmrc` present.
- Only CI secret: built-in `GITHUB_TOKEN` injected by GitHub Actions.

## Webhooks & Callbacks

**Incoming:**
- None. No HTTP server, no webhook listener, no inbound endpoints.

**Outgoing:**
- None network-based. The only "callback" pattern is in-process: `src/io/fastq.rs` accepts an optional `progress_callback: Option<G>` invoked locally during FASTQ processing (not a remote callback).

---

*Integration audit: 2026-06-30*
