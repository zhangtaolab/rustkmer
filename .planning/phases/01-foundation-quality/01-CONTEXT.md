# Phase 1: Foundation & Quality - Context

**Gathered:** 2026-07-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish engineering infrastructure that unblocks Phases 2–4 and guards against regressions: a CI gate workflow (fmt/clippy/test/wheel-build on a matrix), library output routed through the `log` facade, a single source of truth for `.rkdb` write/read logic, and English-only user-facing library strings — across both the CLI and `pyrustkmer` surfaces. WHAT/verification/matrix/trigger are locked by `01-SPEC.md`; this document locks the HOW.

</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**4 requirements are locked.** See `01-SPEC.md` for full requirements, boundaries, acceptance criteria, edge coverage (9/9), and prohibitions (4 must-NOT).

Downstream agents MUST read `01-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
- A new Rust CI workflow (`.github/workflows/ci.yml`) gating fmt/clippy/test/wheel-build on PR + push to `dev`/`main`
- Fixing all existing root-crate clippy warnings so `-D warnings` is green
- Migrating console I/O in `src/` (excl. `src/cli/`), `src/main.rs` non-init writes, and `pyo3/src/` to the `log` facade
- clippy deny config for `print_stdout`/`print_stderr`/`dbg_macro` + a comment-aware CJK detection check, with allowlists
- Consolidating `count.rs` write path to delegate to `format.rs`, and removing the read-side `data_offset` reconciliation anti-pattern
- Translating CJK string literals in `src/` (excl. `src/cli/`) + `pyo3/src/` to English
- Regression tests: golden-file `sha256`, write→read round-trip, legacy-sample read-back

**Out of scope (from SPEC.md):**
- Multi-Python wheel matrix (3.11/3.12/3.13); macOS x86_64 cross-build; manylinux matrix — release-readiness is v2
- Translating CJK in code comments — string literals only
- God-module splits in `format.rs` / `pyo3/database.rs` not on the write/read-consolidation path
- `src/cli/` console output and `indicatif` progress bars — exempt from log migration
- CI security hardening (action SHA pinning, `pull_request_target`, secret handling, injection) — canon, owned by `/gsd-secure-phase`
- Parallel counting, bounded merge, dense storage, Jellyfish2 benchmarking — Phases 2/3/4

</spec_lock>

<decisions>
## Implementation Decisions

### CI Workflow Structure
- **D-01:** Single new file `.github/workflows/ci.yml` (alongside `docs.yml` and `performance-regression.yml`). Mirror the cargo registry/index/build caching pattern already used in `performance-regression.yml`.
- **D-02:** Independent jobs run in parallel on the matrix (fmt / clippy / test / wheel-build as separate jobs), not one multi-step job. Failures localize faster; tradeoff of repeated checkout/cache per job is accepted.
- **D-03:** The pyo3 subcrate clippy gate runs as its own job (`cd pyo3 && cargo clippy`), merged with the wheel-build job so pyo3-side failures are independently visible. Root crate runs fmt/clippy/test.
- **D-04:** Any matrix job failing fails the PR (branch protection requires all status checks green) — realizes prohibition P1 (no swallowed gate failures). No `continue-on-error` / `|| true` / if-guarded skips on gate steps.

### Lint Enforcement Mechanism
- **D-05:** clippy deny is enforced BOTH locally and in CI (defense in depth): crate-level `#![deny(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]` in `src/lib.rs` AND an explicit `cargo clippy -- -D ...` step in CI. Local `cargo build`/`cargo clippy` fails immediately on a violation.
- **D-06:** The `src/cli/` allowlist is a single module-level `#![allow(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]` at the top of `src/cli/mod.rs` — the whole cli subtree is exempt in one place. (`main.rs`'s `env_logger::Builder…init()` is logger setup, not a print macro, so it needs no allow.)
- **D-07:** The comment-aware CJK check is implemented as a Rust `#[test]` that uses `syn` to parse source files and scan ONLY string literals (not comments) for covered CJK code points (Han + Hiragana + Katakana + Hangul blocks). This adds `syn` as a dev-dependency.
- **D-08:** The CJK check lives in `tests/` as a normal `cargo test`, so it runs both locally and in CI (same place as the clippy gate philosophy). No separate CI-only script.

### golden-file Baseline
- **D-09:** Both baseline strategies apply: (a) pre-capture — generate golden `.rkdb` artifacts with the CURRENT (pre-refactor) code and commit them; (b) cross-consistency — assert the consolidated count-path output's `sha256` equals `RKDatabase::write_to_file`'s output for the same input.
- **D-10 (CRITICAL SEQUENCING):** The plan MUST capture the golden `.rkdb` + `sha256` artifacts in its FIRST task, BEFORE any refactor of `count.rs`. Refactoring first destroys the pre-refactor baseline the golden proof depends on.
- **D-11:** Golden artifacts are committed binary `.rkdb` files under `tests/fixtures/` (the test computes and compares `sha256`). Binary fixtures double as the legacy read-back sample. `tests/fixtures/` already has the `.fasta` / `.json` precedent; `sha2 0.10` is already a dependency.
- **D-12:** The legacy `data_offset = 42` read-back sample is generated by the current code and committed (not hand-written binary). The new reader must read it correctly after the read-side refactor.
- **D-13:** Coverage matrix for golden + round-trip: `k ∈ {21, 32, 64}` × `canonical {on, off}` × `sorted {on, off}` — guards against k-width- or canonical-related byte differences slipping through.

### Log Level / Progress Visibility
- **D-14:** The 51 merge-progress `println!` calls in `prefix_cache_merge.rs` migrate to `log::info!` — CLI users still see merge progress by default (default filter is `info`). Behavior change is minimized. (CONCERNS.md's suggestion to gate verbose progress behind `debug!` is partly adopted: fine-grained per-phase progress may be `debug!`, but the headline milestones stay `info!`.)
- **D-15:** Mapping convention: `println!` → `info!`; `eprintln!` → `warn!` or `error!` (by severity); `dbg!` → `debug!`. Message text and format args are preserved verbatim (SPEC acceptance — channel-only change).
- **D-16:** User log-level control reuses existing env vars (`RUSTKMER_VERBOSE` / `RUSTKMER_QUIET` / `RUSTKMER_LOG_LEVEL`) — NO new CLI flags. `env_logger` already reads `RUST_LOG`-style env (SPEC P2 locks default at `info`).
- **D-17 (Python embedding):** `env_logger` is initialized ONLY in the CLI binary (`src/main.rs:13`); the `pyo3` extension does NOT initialize a logger, so library log output is discarded by default when embedded in Python — zero stderr pollution into Python (the core FOUND-02 goal). A Python host that wants the logs can configure `env_logger` itself or via callback in a later phase.

### Claude's Discretion
- Exact per-job `timeout-minutes` values, `concurrency` cancel-in-progress settings, and cache key versioning in `ci.yml` — follow `performance-regression.yml` conventions; planner picks concrete values.
- Whether the CJK `syn` test scans `src/` + `pyo3/src/` via a path list hardcoded in the test or discovered via `walkdir` — planner's choice (`walkdir` is already a dependency).
- Whether the read-side `data_offset` removal keeps a one-line sanity assertion or removes the clamp entirely — planner decides as long as the legacy sample (D-12) still reads and golden `sha256` matches (D-09).
- Splitting the per-area clippy work across the 4 plans (`01-01`..`01-04`) — planner sequences; D-10 (capture golden first) is the only hard ordering constraint.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked requirements (MUST read first)
- `.planning/phases/01-foundation-quality/01-SPEC.md` — 4 locked requirements, boundaries, 16 acceptance criteria, 9/9 edge coverage, 4 must-NOT prohibitions. The authority on WHAT; this CONTEXT is the authority on HOW.

### Project / roadmap
- `.planning/ROADMAP.md` §"Phase 1: Foundation & Quality" — phase goal, success criteria, the 4 plans (`01-01`..`01-04`)
- `.planning/REQUIREMENTS.md` §"Foundation / Quality" — FOUND-01..FOUND-04 definitions; §"Out of Scope" table (scope-creep guardrail)
- `.planning/PROJECT.md` §Context, §Constraints — `.rkdb` v2 preservation, dual-surface, benchmark dataset path

### Codebase maps (grounding)
- `.planning/codebase/CONCERNS.md` — the 4 known issues this phase directly fixes: "No Rust CI workflow", "Library code performs direct console I/O", "Hardcoded Chinese (CJK) user-facing strings", and the `format.rs` fragile-god-module / duplicated write logic. Also enumerates adjacent tech debt that is explicitly OUT of scope (dead backup files, dead pyo3 modules, `merge_tests.rs`, unused deps, `#![allow(deprecated)]`, unsafe `env::set_var`, mmap SAFETY) — do NOT pull these in.
- `.planning/codebase/STACK.md` — Rust 1.80+ / PyO3 0.27.2 / maturin `[tool.maturin]` config; `log 0.4` + `env_logger 0.11` already deps; release profile (`lto`, `codegen-units=1`, `panic="abort"`) to preserve.
- `.planning/codebase/TESTING.md` — `tests/common/mod.rs` factories, `tests/common/temp_files.rs` RAII + `temp_file!`/`temp_fasta!` macros, `tests/fixtures/` convention, inline `#[cfg(test)]` pattern, `sha2` usage.

### Existing CI (pattern to mirror)
- `.github/workflows/performance-regression.yml` — cargo registry/index/build cache steps, `dtolnay/rust-toolchain@stable`, `maturin` install + venv pattern to reuse in `ci.yml`.
- `.github/workflows/docs.yml` — for trigger conventions.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `env_logger` already initialized in `src/main.rs:13` (`Env::default().default_filter_or("info")`) — log facade infrastructure exists; D-17 only needs to ensure pyo3 does NOT call it.
- `format.rs` canonical writers: `DatabaseHeader::write_to` (line 81), `KmerEntry::write_to` (line 201), `RKDatabase::write_to` (line 360), `RKDatabase::write_to_file` (line 348) — the single-source-of-truth target for `count.rs` delegation (FOUND-03).
- `sha2 0.10` already a dependency — golden-file `sha256` needs no new dep.
- `tests/common/mod.rs` factories (`create_test_database`, `create_database_from_kmers`, `databases_have_same_kmers`) and `tests/common/temp_files.rs` (`TempFileManager`, `temp_file!`/`temp_fasta!`) — reuse for golden/round-trip test scaffolding.
- `tests/fixtures/` (`.fasta`, `.json`) — the committed-binary-fixture precedent for `.rkdb` golden files (D-11).
- Inline `#[cfg(test)] mod tests` in `format.rs:1000-1306` — existing header round-trip + merge-memory tests to extend (not duplicate — note CONCERNS: `merge_tests.rs` is orphaned/dead).
- `walkdir 2.4` already a dependency — available for the CJK `syn` test to discover source files.

### Established Patterns
- Rust tests: inline `#[cfg(test)] mod tests` for unit; `tests/{unit,integration,property,contract,common,fixtures}` tree for integration; `anyhow::Result` + `?` in integration tests; `.unwrap()` as failure signal inside test bodies.
- Release profile tuned for production (`lto=true`, `codegen-units=1`, `panic="abort"`) — preserve when touching `Cargo.toml` (e.g., adding `syn` dev-dep).
- `proptest 1.5`, `tempfile 3.12`, `rand`/`rand_chacha` are dev-deps available for new tests.

### Integration Points
- `src/cli/commands/count.rs:497-531` — the inline header + `write_u128`/`write_u32` loop to replace with `format.rs` writer delegation (FOUND-03).
- `src/database/format.rs:290-296` and `src/database/query.rs:79` — the defensive `data_offset` clamp (`if < 40 || > 1000 { 42 }`) to remove on the read side (FOUND-03). Legacy sample (D-12) must still read after removal.
- `src/database/prefix_cache_merge.rs:90-112, 317-329` — the 51 Chinese progress `println!` calls (FOUND-02 + FOUND-04 overlap) → `log::info!` in English (D-14, D-15).
- `src/lib.rs` — site of the crate-level `#![deny(...)]` (D-05); `src/cli/mod.rs` — site of the `#![allow(...)]` (D-06).
- `pyo3/src/lib.rs` / `pyo3/src/*.rs` — the 3 console I/O + 66 CJK string literals to migrate; pyo3 must NOT initialize `env_logger` (D-17).
- `.github/workflows/ci.yml` (new) — the gate workflow (D-01..D-04); mirror `performance-regression.yml` caching.

</code_context>

<specifics>
## Specific Ideas

- The phase explicitly fixes four issues already documented in `CONCERNS.md`; the fixes should track back to those concern entries (CI section, console-I/O section, CJK section, format-god-module section) so verification can point at resolved concerns.
- The golden-capture-before-refactor ordering (D-10) is the one non-obvious sequencing constraint — it exists because the byte-identity proof is only meaningful against a pre-refactor baseline.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. Adjacent tech debt in `CONCERNS.md` (dead `.stage1_fix_backup` files, dead `pyo3/database_backup.rs` + `database_new_approaches.rs`, orphaned `merge_tests.rs`, `proptest` in both dep sections, unused `inquire`/`chrono` deps, `#![allow(deprecated)]`, unsafe `env::set_var`, mmap `// SAFETY:` gaps, `Cargo.lock` gitignored, no enforced MSRV, Python version-policy inconsistency) is explicitly out of scope per `PROJECT.md` ("cleaned opportunistically when the relevant code is touched, not pursued for its own sake this round") and is NOT pulled in even though FOUND-02/04 touch `prefix_cache_merge.rs` and `pyo3/src/`.

</deferred>

---

*Phase: 01-foundation-quality*
*Context gathered: 2026-07-01*
