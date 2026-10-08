---
last_mapped_commit: 0f442541636e002a322db9d1ba091ff046e62284
last_mapped_at: 2026-10-08
---
# External Integrations

**Analysis Date:** 2026-10-08

## APIs & External Services

**None.** rustkmer is a fully local/offline tool. No HTTP clients, cloud SDKs, or third-party web APIs are referenced in `src/` or `pyo3/src/`.

**Local process integration:**
- PyO3 ABI between Python and Rust: `pyo3/src/lib.rs` exposes the `pyrustkmer` module (PyO3 0.27.2, cdylib) wrapping the path dependency `rustkmer`
- The Python package can also be exercised via CLI subprocess patterns in tests (`tests/`, `pyo3/tests/`)

## Data Storage

**Databases:**
- None (no SQL/NoSQL). Custom binary k-mer database format `.rkdb` (RKDB):
  - 42-byte binary header read directly on merge paths (`src/database/`)
  - Hybrid JSON + binary persistence via serde/bincode; memory-mapped access via memmap2 0.9
  - `src/database/temp_lifecycle.rs` manages `rustkmer-merge-*` temp dirs with RAII cleanup (tempfile)

**File Storage:**
- Local filesystem only — FASTA/FASTQ inputs (plain, `.gz`, `.bz2`, `.xz` via flate2/bzip2/xz2), `.rkdb` databases, CSV/text outputs (`src/io/`, `src/output/`)

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
- GitHub repository (`rustkmer/rustkmer`); docs on GitHub Pages (`https://rustkmer.github.io`, deployed by `.github/workflows/docs.yml` on `main`/tags)

**CI Pipeline:** GitHub Actions, three workflows:
- `.github/workflows/ci.yml` — merge gate: rustfmt, clippy `--all-targets -D warnings`, `cargo test`, and pyo3 clippy + `maturin build` (sdist + wheel); matrix ubuntu/macos; PRs target `dev`/`main`; least-privilege `contents: read`; per-job cargo cache keys
- `.github/workflows/docs.yml` — mkdocs-material build + Pages deploy (`pages: write`, `id-token: write`)
- `.github/workflows/performance-regression.yml` — baseline benchmarks on push/schedule (daily 2 AM UTC cron), posts PR comments/issues

## Environment Configuration

**Required env vars:**
- None required. Optional: `RUSTKMER_DEFAULT_K`, `RUSTKMER_THREADS`, `RUSTKMER_VERBOSE` (`src/cli/commands/count.rs`, `src/cli/commands/merge.rs`), `RUST_LOG`

**Secrets location:**
- None — no secrets used anywhere; CI relies on GitHub OIDC (`id-token`) for Pages rather than stored tokens

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

---

*Integration audit: 2026-10-08*
