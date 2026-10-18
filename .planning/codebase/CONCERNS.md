---
last_mapped_commit: 51629b5ea7ed323cfb60ef0be9cab2f30f6a2ed6
last_mapped_at: 2026-10-18
---
# Codebase Concerns

**Analysis Date:** 2026-10-18

Scope note: refreshed against `.github/`, `.gitignore`, `pyo3/`, `src/`, `tests/` only (incremental remap; prior full map dated 2026-10-17). Phase-03 memory-safety work (streaming merge routing, RAII temp lifecycle in `src/database/temp_lifecycle.rs`, dense KmerKey storage) and phase-04 closure (Windows `cfg` gating in `tests/merge_bounded_memory_tests.rs`) have landed and are reflected below. `.planning/` notes an open IN-09 diagnostic-posture item in `scripts/bench` — outside this scope, referenced only.

## Tech Debt

**Committed dead/backup source files in `pyo3/src/`:**
- Issue: `database_backup.rs`, `database_new_approaches.rs`, `database.rs.stage1_fix_backup`, `formatter.rs.stage1_fix_backup`, `fuzzy_query.rs.stage1_fix_backup` are git-tracked but NOT compiled — `pyo3/src/lib.rs` declares only `counter; database; errors; formatter; fuzzy_query; prefix_query; utils`. Stale snapshots from an abandoned "stage1 fix" and a "new approaches" experiment.
- Files: `pyo3/src/database_backup.rs` (1127 lines), `pyo3/src/database_new_approaches.rs` (707 lines), `pyo3/src/*.stage1_fix_backup`
- Impact: ~2000 lines of dead code confuse navigation and grep; `database_backup.rs` contains its own `PyDatabase` that diverges from the live `pyo3/src/database.rs` (2121 lines).
- Fix approach: `git rm` all five files; rely on git history for recovery.

**Tracked coverage artifacts and root scripts:**
- Issue: `pyo3/.coverage` and `pyo3/tests/.coverage` are git-tracked; `pyo3/tests/coverage.xml` and `pyo3/tests/htmlcov/` exist on disk. Ad-hoc scripts `fresh_test.py` and `precise_analysis.py` remain tracked at repo root.
- Files: `fresh_test.py`, `precise_analysis.py`, `pyo3/.coverage`, `pyo3/tests/.coverage`
- Impact: noisy diffs (`.coverage` shows as modified in git status), repo bloat, risk of embedding sensitive paths in ad-hoc scripts.
- Fix approach: `git rm --cached` the coverage files; add `**/.coverage`, `htmlcov/`, `__pycache__/`, `coverage.xml` ignore rules covering the `pyo3/` subtree (current `.gitignore` rules only cover `python/`-prefixed paths); delete or relocate the root scripts.

**Duplicated/parallel persistence layers:**
- Issue: Legacy JSON+gzip+SHA256 path in `src/core/database/persistence.rs` (583 lines, `PersistenceError`, flate2/sha2) coexists with the canonical binary RKDB path in `src/database/`. No `src/` consumer of `core::database::persistence` remains.
- Files: `src/core/database/persistence.rs`, `src/core/database/mod.rs`
- Impact: Dead module plus unused `flate2`/`sha2` dependency weight; two "sources of truth" invites writing to the wrong one.
- Fix approach: Delete `src/core/database/`, migrate any needed metadata helpers into `src/core/metadata.rs`, then audit `flate2`/`sha2` usage before dropping from `Cargo.toml`.

**Two args modules for the CLI:**
- Issue: `src/cli/args.rs` and `src/cli/commands/args.rs` both define CLI argument structures; command modules re-map fields between them.
- Files: `src/cli/args.rs`, `src/cli/commands/args.rs`
- Impact: Adding a flag requires edits in two places; drift causes silent option loss.
- Fix approach: Consolidate into a single clap derive model in `src/cli/args.rs` consumed by all command handlers.

**Placeholder metrics (TODOs) in user-facing output:**
- Issue: Reported statistics remain stubbed: `memory_peak_bytes: 0` (`src/database/stats.rs:275`), `memory_usage_mb: None` (`src/fuzzy/query.rs:420,444`), fuzzy perf TODOs (`src/fuzzy/query.rs:466`, `src/fuzzy/performance.rs:463`), `wildcard_count = 0` (`src/fuzzy/expansion.rs:176`), hardcoded `0 ms` / `N/A` cache lines printed by the fuzzy command (`src/cli/commands/fuzzy.rs:679-680`).
- Files: `src/database/stats.rs`, `src/fuzzy/query.rs`, `src/fuzzy/performance.rs`, `src/fuzzy/expansion.rs`, `src/cli/commands/fuzzy.rs`
- Impact: CLI/Python API reports misleading performance numbers (0 ms, 0 MB) that users may trust for benchmarking.
- Fix approach: Wire real measurement (peak-RSS sampling, `Instant` timers) or remove the fields until implemented.

**`#[allow(dead_code)]` shims accumulating:**
- Issue: Production modules carry dead-code suppressions rather than deletions; test-support modules (`tests/common/`, `tests/consistency/`) are wholesale-allowed instead of selectively wired via the `tests/mod.rs` coordinator.
- Files: `src/database/prefix_cache_merge.rs:106`, `src/database/index.rs:18`, `src/database/format.rs:1857`, `src/fuzzy/performance.rs:105,107`, `src/cli/commands/dump.rs:61`; tests: `tests/consistency/generators.rs:6,17,44`, `tests/consistency/utils.rs`, `tests/common/temp_files.rs:5`, `tests/common/mod.rs:17`, `tests/common/performance.rs:5`
- Impact: Compiler can no longer flag genuinely dead paths; fixture generators referenced only from some test configs silently rot.
- Fix approach: In `src/`, delete dead items (target zero allows). In `tests/`, keep the documented fixture-generator pattern (`tests/consistency/generators.rs`) but reference each generator from at least one suite so the allow can be dropped.

**`.gitignore` ignores `Cargo.lock`:**
- Issue: `.gitignore` lists `Cargo.lock` (twice), yet `Cargo.lock` is committed at root and in `pyo3/` — the ignore rules are dead but signal an old policy; if ever honored, CI builds (`.github/workflows/ci.yml` runs `cargo test`/`cargo clippy` without lock enforcement) would resolve fresh, unpinned dependency versions.
- Files: `.gitignore` ("Rust build artifacts" block)
- Impact: Reproducibility risk for the release binary and for CI gate results (release profile uses `lto=true`, `panic="abort"` — sensitive to dependency drift).
- Fix approach: Remove the `Cargo.lock` ignore lines and keep the lockfiles committed (correct policy for a binary crate + cdylib).

## Known Bugs

**None currently open in the scoped paths.** Previously flagged items resolved:
- The `XXXX` header-corruption write (`src/database/format.rs:2334`) is now inside the `estimate_total_kmers_tolerates_corrupt_header` test (threat register T-03-01) — test-gated, intentional.
- Merge memory-model churn (routing bytes-per-k-mer, `--max-memory` floor, prefix-cache intermediate leak) was stabilized by phase-03; regression suites exist (`tests/merge_routing_tests.rs`, `tests/merge_route_parity_tests.rs`, `tests/merge_cleanup_tests.rs`, `tests/merge_bounded_memory_tests.rs` with platform-gated `#[cfg(...)]` cases for linux/windows/other).

## Security Considerations

**Runtime `env::set_var`/`remove_var` in the config manager:**
- Risk: `src/config/manager.rs:492,498` call `unsafe { env::set_var/remove_var }` at runtime. Mutating the environment while rayon worker threads are live is a documented std hazard (UB-adjacent; edition 2024 makes it unsafe for this reason).
- Files: `src/config/manager.rs`
- Current mitigation: `unsafe` blocks are isolated; no observed post-spawn invocation from the count/merge paths, but nothing enforces ordering.
- Recommendations: Set env vars only before thread pools spawn, or replace with an in-process config struct passed explicitly.

**Memory-mapped I/O on untrusted input:**
- Risk: `unsafe { MmapOptions::new().map(&file) }` in `src/io/mmap.rs` and `src/memory/efficiency.rs`, plus manual binary header parsing across `src/database/`. Malformed/truncated `.rkdb` files rely on length validation before slice indexing.
- Files: `src/io/mmap.rs`, `src/memory/efficiency.rs`, `src/database/format.rs`, `src/database/query.rs`
- Current mitigation: Header validation with defensive `data_offset` clamping (`src/database/query.rs`, `src/database/format.rs`); error typing via `thiserror` (`src/error.rs`); corrupt-header tolerance is now unit-tested (`src/database/format.rs` estimate tests).
- Recommendations: Fuzz the `from_file`/header-parse paths (cargo-fuzz) before accepting third-party databases.

**CI least-privilege posture (positive note):** `.github/workflows/ci.yml` uses `pull_request` (not `pull_request_target`), read-only `contents: read` permissions, no `continue-on-error` on gates, and concurrency cancellation — threat-model hardening is in place.

**No secrets surface:** CLI-only tool, no network calls, no credentials in the scoped paths; `.gitignore` covers `.env*`.

## Performance Bottlenecks

**Giant files concentrating logic:**
- Problem: `pyo3/src/database.rs` (2121 lines), `src/database/format.rs` (2519 lines), `src/database/prefix_cache_merge.rs` (2119 lines), `src/hash/table.rs` (~1400 lines) each mix parsing, iteration, and mutation; compile times and review cost suffer.
- Files: listed above
- Cause: Incremental feature addition without module splits (phase-03 added routing logic into `prefix_cache_merge.rs`).
- Improvement path: Split `format.rs` into header/reader/writer submodules; split `pyo3/src/database.rs` by query vs mutation `#[pymethods]` blocks; extract routing/admission from `prefix_cache_merge.rs` into `merge_config.rs` consumers.

**Counting still single-threaded per file:**
- Problem: The count command passes `num_threads = 1` (`src/cli/commands/count.rs`), so rayon parallelism is unused for the primary count path even though `KmerCounter` is thread-safe.
- Files: `src/cli/commands/count.rs`, `src/hash/table.rs`
- Improvement path: Enable per-file parallel counting (chunked record batching into the RwLock map) — the core value proposition ("compete with KMC/Jellyfish") depends on it.

## Fragile Areas

**Merge routing / temp-file lifecycle:**
- Files: `src/database/temp_lifecycle.rs`, `src/database/merge_config.rs`, `src/database/merge_error.rs`, `src/database/streaming_merge.rs`, `src/database/prefix_cache_merge.rs`
- Why fragile: External-sort compatibility error strings are contract-pinned (exact-text assertions in `tests/007-api-compatibility/`); routing admission (bytes-per-k-mer model, memory floor) was corrected repeatedly before phase-03 stabilization.
- Safe modification: Run `cargo test merge` and the API-compatibility suite after any edit; never reword errors casually. `tests/merge_bounded_memory_tests.rs` now gates per-OS (`linux` / `not windows` / `not linux+windows` branches) — add platform-specific cases under the matching `#[cfg]`.
- Test coverage: Good (`tests/merge_*`, `tests/consistency*`, golden fixtures under `tests/fixtures/` with `tests/golden_sha256_tests.rs` tamper detection).

**Fuzzy query engine:**
- Files: `src/fuzzy/query.rs`, `src/fuzzy/mutation.rs` (~840 lines), `src/fuzzy/expansion.rs`, `src/fuzzy/wildcard.rs`, `src/fuzzy/normalization.rs`
- Why fragile: Multiple interacting expansion/mutation/wildcard strategies with stubbed metrics and TODO comments; behavior matrix (k size x wildcard count x distance) is large.
- Safe modification: Add property cases (`tests/dense_proptest_tests.rs`) before touching expansion logic.
- Test coverage: Python-side in `pyo3/tests/test_core.py`; Rust-side fuzzy unit coverage thinner than merge paths.

**Hardcoded `unwrap()` in production paths:**
- Files: `src/hash/table.rs` (52 sites), `src/database/streaming_merge.rs` (28), `src/fuzzy/mutation.rs` (25), `src/io/fastq.rs` (24), `src/io/fasta.rs` (23)
- Why fragile: Any malformed input hitting one of these panics the CLI instead of returning `RustKmerError` — `panic = "abort"` in the release profile means no unwind, no cleanup of RAII temp dirs.
- Safe modification: Replace with `?`/`.context(...)` when touching these files; prioritize the I/O parsers (`src/io/`) since they face user files first.
- Test coverage: Panic-on-corrupt-input not systematically tested.

## Scaling Limits

**k-mer width fixed to u128 encoding:**
- Current capacity: k <= 64 via 2-bit packing (`src/kmer/encoding.rs`, `MAX_KMER_SIZE_IN_U128`).
- Limit: k > 64 unsupported across CLI and Python API.
- Scaling path: Wider encodings require a format-version bump; the RKDB header carries k size, so plan a `.rkdb` v3 before attempting.

**Single-machine only:**
- Current capacity: Rayon thread parallelism, memory-mapped single-file databases, external-sort streaming merge for memory-constrained merges.
- Limit: No distributed sharding; merge is pairwise/streaming.
- Scaling path: Partitioned RKDB scheme or merge-routing work on header-only admission (already the post-phase-03 model).

## Dependencies at Risk

**PyO3 pinned at 0.27.2:**
- Risk: PyO3 minor versions break API frequently; `pyo3/Cargo.toml` hardcodes the version. Upstream `CLAUDE.md` additionally lists contradictory historic versions (0.23.4 alongside 0.27.2) in duplicated "Active Technologies" bullets.
- Impact: Upgrade requires coordinated edits to all `#[pyclass]`/`#[pymethods]` in `pyo3/src/` plus doc updates.
- Migration plan: Upgrade deliberately in one phase; rerun `pyo3/tests/` against the same Python matrix used by CI.

**`bincode 1.3` (unmaintained major version):**
- Risk: bincode 1.x is legacy; declared in `pyo3/Cargo.toml`.
- Impact: Low usage surface, but blocks a clean edition-2024 migration.
- Migration plan: Move to bincode 2 or serde_json/byteorder-only serialization.

**MSRV / Python-version policy inconsistency:**
- Risk: Docs say Python 3.10+, `pyo3/pyproject.toml` says `requires-python = ">=3.11"`; no enforced Rust MSRV (CI installs `dtolnay/rust-toolchain@stable`, so gate results float with the toolchain).
- Impact: Contributors on older toolchains/Pythons get unpredictable failures.
- Migration plan: Pin MSRV via `rust-version` in both `Cargo.toml` files and align the Python floor as part of hardening.

## Missing Critical Features

**None blocking in the scoped paths.** CI now exists and is a gate: `.github/workflows/ci.yml` (rustfmt, clippy root + pyo3 with `-D warnings`, `cargo test`, maturin wheel matrix), plus `benchmark.yml` and `docs.yml`. Remaining gaps:

- **rustfmt job is ubuntu-only:** every substantive `ci.yml` gate (`clippy (root)`, `test (root)`, `pyo3 clippy + wheel`) runs the full `[ubuntu-latest, macos-latest, windows-latest]` matrix, so the platform-gated branches of `tests/merge_bounded_memory_tests.rs` (`#[cfg(not(target_os = "windows"))]` items, `not(any(linux, windows))` portable RSS helper) compile and execute on their respective CI runners. Only the `rustfmt` job is ubuntu-only — negligible, since rustfmt output is platform-independent.
- **Test-suite organization debt:** `tests/` mixes ~20 top-level Rust suites plus Python trees (`007-api-compatibility/`, `converted/`, `consistency/`, `contract/`, `property/`, `unit/`, `performance/`, `integration/`) coordinated through `tests/mod.rs`; ad-hoc names (`tests/cjk_check.rs`) survive. Contributors cannot tell which suites are canonical.

## Test Coverage Gaps

**Fuzzy query memory/performance claims:**
- What's not tested: The metrics the module claims to report (memory usage, cache hits, aggregation time) — they are hardcoded stubs, so meaningful tests cannot exist yet.
- Files: `src/fuzzy/performance.rs`, `src/fuzzy/query.rs`
- Risk: Performance regressions invisible.
- Priority: Medium.

**Corrupt-input panic paths:**
- What's not tested: Truncated/malformed FASTA/FASTQ/RKDB inputs against the ~150 non-test `unwrap()` sites in the parsers and streaming merge.
- Files: `src/io/fasta.rs`, `src/io/fastq.rs`, `src/io/mmap.rs`, `src/database/streaming_merge.rs`
- Risk: CLI panics (abort, no temp cleanup) on user data instead of clean errors.
- Priority: High.

**Python binding coverage for merge routes:**
- What's not tested: `pyo3/tests/` covers core/counter/merge basics, but the phase-03 merge memory-model (routing admission, temp lifecycle) is only validated from Rust tests.
- Files: `pyo3/tests/test_database_merge.py`, `src/database/merge_config.rs`
- Risk: Python users could hit OOM conditions Rust tests don't reproduce.
- Priority: Medium.

---

*Concerns audit: 2026-10-18*
