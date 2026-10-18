---
last_mapped_at: 2026-10-18
last_mapped_commit: 51629b5ea7ed323cfb60ef0be9cab2f30f6a2ed6
---
# External Integrations

**Analysis Date:** 2026-10-18

*Scope note: refreshed from a scoped remap of `.github/`, `.gitignore`, `pyo3/`, `src/`, `tests/` (prior full map: 2026-10-17).*

## APIs & External Services

**None.** rustkmer is fully local/offline. No HTTP clients, cloud SDKs, or third-party web APIs are referenced in `src/` or `pyo3/src/`.

**Local process integration:**
- PyO3 ABI between Python and Rust: `pyo3/src/lib.rs` exposes the `pyrustkmer` module (PyO3 0.27.2, cdylib) wrapping the path dependency `rustkmer`
- Python tests also exercise the CLI via subprocess patterns (`tests/`, `pyo3/tests/`)

## Data Storage

**Databases:**
- None (no SQL/NoSQL). Custom binary k-mer database format `.rkdb` (magic `RKDB`, version 2):
  - 42-byte header + 20-byte entries, little-endian via byteorder (`src/database/format.rs`)
  - Hybrid JSON + binary persistence via serde/bincode; memory-mapped access via memmap2 0.9
  - `src/database/temp_lifecycle.rs` manages `rustkmer-merge-*` temp dirs with RAII cleanup (tempfile)
  - Merge pipeline: streaming external-sort merge (`src/database/streaming_merge.rs`), prefix-cache merge (`src/database/prefix_cache_merge.rs`), bounded-memory routing (exercised by `tests/merge_routing_tests.rs`, `tests/merge_bounded_memory_tests.rs`, `tests/merge_cleanup_tests.rs`)

**File Storage:**
- Local filesystem only — FASTA/FASTQ inputs (plain, `.gz`, `.bz2`, `.xz` via flate2/bzip2/xz2; `src/io/fastq.rs`, `src/io/fasta.rs`), `.rkdb` databases, CSV/text outputs (`src/output/`)

**Caching:**
- None (in-memory hash maps only: dashmap/hashbrown/ahash)

## Authentication & Identity

**Auth Provider:**
- Not applicable — no auth, no user identity, no network surface

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry etc.)

**Logs:**
- `log` 0.4 + `env_logger` 0.11, gated by `RUST_LOG`; indicatif 0.17 progress bars for CLI feedback

## CI/CD & Deployment

**Hosting:**
- GitHub repository; docs on GitHub Pages (deployed by `.github/workflows/docs.yml`, outside scope)

**CI Pipeline:** GitHub Actions, three workflows in `.github/workflows/`:
- `ci.yml` — merge gate (PRs/pushes to `dev`/`main`): rustfmt; clippy `--all-targets -D warnings`, `cargo test`, and pyo3 clippy + `maturin build` (sdist + wheel, uploaded as artifacts) — all matrices now `ubuntu-latest, macos-latest, windows-latest`. Least-privilege `contents: read`; standard `pull_request` trigger (not `_target`); per-job cargo cache namespaces; concurrency cancellation on ref
- `benchmark.yml` — CI performance regression gate (replaces the deleted `performance-regression.yml`): builds the release binary, runs the synthetic benchmark via `python3 scripts/bench/bench.py` (Python stdlib harness, outside scope), uploads `bench-results-<OS>` artifacts BEFORE gating, then gates with `scripts/bench/compare.py` against committed per-platform baselines (`scripts/bench/baselines/bench_baseline.{linux,darwin}.json`; thresholds: wall 0.25 advisory, RSS 0.15 hard). Gate semantics live only in compare.py exit codes (0 pass / 1 regression / 2 invalid); no error-swallowing or conditional skips. Matrix: linux + darwin
- `docs.yml` — mkdocs-material build + Pages deploy (outside scope)

**Removed:** `src/cli/commands/benchmark.rs` CLI subcommand and `.github/workflows/performance-regression.yml` no longer exist — benchmarking is now exclusively the `scripts/bench/` harness + `benchmark.yml` gate.

## Environment Configuration

**Required env vars:**
- None required. Optional: `RUSTKMER_DEFAULT_K`, `RUSTKMER_THREADS`, `RUSTKMER_VERBOSE` (`src/cli/commands/count.rs`, `merge.rs`), `RAYON_NUM_THREADS` (fallback), `RUST_LOG`

**Secrets location:**
- None — no secrets used anywhere; CI relies on GitHub OIDC (`id-token`) for Pages rather than stored tokens

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

---

*Integration audit: 2026-10-18*
