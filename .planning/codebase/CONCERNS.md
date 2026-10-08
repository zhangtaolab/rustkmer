---
last_mapped_commit: 0f442541636e002a322db9d1ba091ff046e62284
last_mapped_at: 2026-10-08
---
# Codebase Concerns

**Analysis Date:** 2026-10-08

## Tech Debt

**Committed dead/backup source files in `pyo3/src/`:**
- Issue: `database_backup.rs`, `database_new_approaches.rs`, `database.rs.stage1_fix_backup`, `formatter.rs.stage1_fix_backup`, `fuzzy_query.rs.stage1_fix_backup` are git-tracked but NOT compiled — `pyo3/src/lib.rs` declares only `mod counter; database; errors; formatter; fuzzy_query; prefix_query; utils;`. These are stale snapshots from an abandoned "stage1 fix" and a "new approaches" experiment.
- Files: `pyo3/src/database_backup.rs` (1127 lines), `pyo3/src/database_new_approaches.rs` (707 lines), `pyo3/src/*.stage1_fix_backup`
- Impact: ~2000 lines of dead code confuse navigation and grep; `database_backup.rs` contains its own `PyDatabase` that diverges from the live `pyo3/src/database.rs` (2116 lines).
- Fix approach: `git rm` all five files; rely on git history for recovery.

**Committed build/test artifacts and stray scripts at repo root:**
- Issue: `pyo3/.coverage`, `pyo3/tests/.coverage`, `pyo3/coverage.xml`, `pyo3/htmlcov/`, `pyo3/target/`, `pyo3/tests/__pycache__/` exist on disk; `pyo3/.coverage` and `pyo3/tests/.coverage` are git-tracked. Ad-hoc scripts `fresh_test.py` and `precise_analysis.py` sit at repo root and are tracked.
- Files: `fresh_test.py`, `precise_analysis.py`, `pyo3/.coverage`, `pyo3/tests/.coverage`
- Impact: repo bloat, noisy diffs (`.coverage` shows as modified in git status), risk of committing coverage data or secrets embedded in ad-hoc scripts.
- Fix approach: `git rm --cached` the coverage files, add `**/.coverage`, `htmlcov/`, `__pycache__/`, `coverage.xml` to `.gitignore`; move or delete the root scripts.

**Duplicated/parallel persistence layers:**
- Issue: Two database persistence implementations coexist: the current binary RKDB path in `src/database/format.rs` (2033 lines) / `src/database/`, and a legacy JSON+gzip+SHA256 path in `src/core/database/persistence.rs` (583 lines, `PersistenceError`, flate2/sha2 deps). Nothing under `src/` imports `core::database::persistence` anymore (only `core::metadata` is still used, from `src/database/prefix_cache_merge.rs:960`).
- Files: `src/core/database/persistence.rs`, `src/core/database/mod.rs`
- Impact: Dead module plus unused `flate2`/`sha2` dependency weight; two "sources of truth" for database formats invites writing to the wrong one.
- Fix approach: Delete `src/core/database/`, migrate any needed metadata helpers into `src/core/metadata.rs`, drop flate2/sha2 from `Cargo.toml` if otherwise unused.

**Two args modules for the CLI:**
- Issue: `src/cli/args.rs` and `src/cli/commands/args.rs` both define CLI argument structures (568+ lines each area); command modules then re-map fields.
- Files: `src/cli/args.rs`, `src/cli/commands/args.rs`
- Impact: Adding a flag requires edits in two places; drift between them causes silent option loss.
- Fix approach: Consolidate into a single clap derive model in `src/cli/args.rs` consumed by all command handlers.

**Placeholder metrics (TODOs) in user-facing output:**
- Issue: Reported statistics are stubbed: `memory_peak_bytes: 0` ("TODO: Track actual memory usage"), `memory_usage_mb: None`, fuzzy cache/aggregation timings printed as hardcoded `0`/`N/A`, `wildcard_count = 0` ("TODO: Calculate from query"), benchmark visualization unimplemented.
- Files: `src/database/stats.rs:266`, `src/fuzzy/query.rs:444,466`, `src/fuzzy/expansion.rs:176`, `src/fuzzy/performance.rs:463`, `src/cli/commands/benchmark.rs:312,633`, `src/cli/commands/fuzzy.rs:679-680`, `src/cli/commands/stats.rs:56`, `src/cli/commands/dump.rs:306`
- Impact: CLI/Python API reports misleading performance numbers (0 ms, 0 MB) to users who may trust them for benchmarking.
- Fix approach: Wire real measurement (rayon thread-local peak tracking, `Instant` timers) or remove the fields until implemented.

**`#[allow(dead_code)]` shims accumulating:**
- Issue: Multiple modules carry dead-code suppressions rather than deletions.
- Files: `src/database/prefix_cache_merge.rs:64`, `src/database/index.rs:18`, `src/database/format.rs:1371` (explicit "no remaining caller" shim), `src/fuzzy/performance.rs:105,107`, `src/cli/commands/dump.rs:61`
- Impact: Compiler can no longer flag genuinely dead paths; code grows monotonically.
- Fix approach: Delete dead items; keep allow-list to zero in non-test code.

## Known Bugs

**Hardcoded `XXXX` bytes-per-k-mer constant in header writing:**
- Issue: `src/database/format.rs:1848` writes a test marker `f.write_all(b"XXXX").unwrap()` inside non-test-position code path per grep (verify whether test-gated before merging upstream).
- Files: `src/database/format.rs:1848`
- Trigger: Executing that write path.
- Workaround: None; confirm and gate behind `#[cfg(test)]` or remove.

**Recently fixed but hot memory-accounting area:**
- Issue: Merge routing memory model was corrected twice in the latest commits (24 -> 96 B/k-mer, 1 GB floor overriding `--max-memory`, prefix-cache intermediate leak). The surrounding code remains the most churn-prone area.
- Files: `src/database/prefix_cache_merge.rs` (1126 lines), `src/database/streaming_merge.rs` (712 lines), `src/database/merge_config.rs`
- Workaround: Regression tests exist (`tests/merge_route_parity_tests.rs`, `tests/merge_routing_tests.rs`, `tests/merge_cleanup_tests.rs`); keep them in any change to merge paths.

## Security Considerations

**Unsanitized `env::set_var` via config manager (unsafe in Rust 2021, UB-adjacent in multi-threaded use):**
- Risk: `src/config/manager.rs:492,498,606-623` calls `unsafe { env::set_var(...) }` / `remove_var` at runtime. If rayon worker threads are active, mutating the environment is undefined behavior (documented std caveat); edition 2024 makes these unsafe precisely for this reason.
- Files: `src/config/manager.rs`
- Current mitigation: None observed beyond the `unsafe` blocks themselves.
- Recommendations: Set env vars only before thread pools spawn, or replace with an in-process config struct passed explicitly.

**Memory-mapped I/O on untrusted input:**
- Risk: `unsafe { MmapOptions::new().map(&file) }` in `src/io/mmap.rs:28`, `src/memory/efficiency.rs:182,228`, plus manual header parsing in `src/database/format.rs`. Malformed/truncated `.rkdb` files rely on length validation before slice indexing; 42-byte header reads were only recently hardened (commit 8cbaa11).
- Files: `src/io/mmap.rs`, `src/memory/efficiency.rs`, `src/database/format.rs`
- Current mitigation: Header validation and error typing (`src/error.rs`, `thiserror`).
- Recommendations: Fuzz `from_file`/header parse paths (cargo-fuzz) before accepting databases from third parties.

**No secrets handling needed:** CLI-only tool, no network calls, no credentials in codebase. `.env` files not present.

## Performance Bottlenecks

**Giant files concentrating logic:**
- Problem: `pyo3/src/database.rs` (2116 lines) and `src/database/format.rs` (2033 lines) each mix parsing, iteration, and mutation; compile times and review cost suffer.
- Files: `pyo3/src/database.rs`, `src/database/format.rs`, `src/hash/table.rs` (1388 lines)
- Cause: Incremental feature addition without module splits.
- Improvement path: Split format.rs into header/reader/writer submodules; split pyo3 database.rs by query vs mutation `#[pymethods]` blocks.

**Legacy JSON persistence path uses gzip + SHA256 over full payload:**
- Problem: If ever invoked, `src/core/database/persistence.rs` re-hashes and compresses entire databases single-threaded.
- Files: `src/core/database/persistence.rs`
- Improvement path: Delete it (see Tech Debt) rather than optimize.

## Fragile Areas

**Fuzzy query engine:**
- Files: `src/fuzzy/query.rs`, `src/fuzzy/mutation.rs` (843 lines), `src/fuzzy/expansion.rs`, `src/fuzzy/wildcard.rs`, `src/fuzzy/normalization.rs`
- Why fragile: Multiple interacting expansion/mutation/wildcard strategies with stubbed metrics and TODO comments; behavior matrix (k size x wildcard count x distance) is large.
- Safe modification: Add cases to `tests/` (property tests exist: `tests/dense_proptest_tests.rs`) before touching expansion logic.
- Test coverage: Python-side tests in `pyo3/tests/test_core.py`; Rust-side fuzzy unit coverage is thinner than the merge paths.

**Merge routing / temp-file lifecycle:**
- Files: `src/database/temp_lifecycle.rs`, `src/database/merge_error.rs`, `src/database/streaming_merge.rs`, `src/database/prefix_cache_merge.rs`
- Why fragile: External-sort compatibility error strings are contract-pinned by tests (commit dc1c25a asserts exact text); changing messages breaks `tests/007-api-compatibility`.
- Safe modification: Run `cargo test merge` and the API-compatibility suite after any edit; never reword errors casually.
- Test coverage: Good (`tests/merge_*`, `tests/consistency*`).

**Hardcoded `unwrap()` in production paths:**
- Files: `src/hash/table.rs` (52 sites), `src/database/streaming_merge.rs` (28), `src/fuzzy/mutation.rs` (25), `src/io/fasta.rs` (23), `src/io/fastq.rs` (19)
- Why fragile: Any malformed input hitting one of these panics the CLI instead of returning `RustKmerError`.
- Safe modification: Replace with `?`/`.context(...)` when touching these files; prioritize I/O parsers (`src/io/`) since they face user files first.
- Test coverage: Panic-on-corrupt-input is not systematically tested.

## Scaling Limits

**k-mer width fixed to u128 encoding:**
- Current capacity: k <= 64 via 2-bit packing in `src/kmer/encoding.rs` (`encode_kmer_u128`).
- Limit: k > 64 unsupported; API surface (including Python bindings) exposes u128-based encoding/decoding assumptions.
- Scaling path: Wider encodings would require format-versioned storage; RKDB header carries k size, so plan a format v2 before attempting.

**Single-machine only:**
- Current capacity: Rayon thread parallelism (`src/cli/commands/count.rs`), memory-mapped single-file databases, external-sort merge for memory-constrained merges (`src/database/streaming_merge.rs`).
- Limit: No distributed sharding; merge is pairwise/streaming.
- Scaling path: More merge-routing work (already header-only per recent commits) or a partitioned RKDB scheme.

## Dependencies at Risk

**PyO3 pinned at 0.27.2:**
- Risk: PyO3 minor versions break API frequently; both root `pyo3/Cargo.toml` and CLAUDE.md documentation hardcode the version. CLAUDE.md also lists contradictory historic versions (0.23.4, 0.27.2) in duplicated "Active Technologies" bullets.
- Impact: Upgrade requires coordinated edits to all `#[pyclass]`/`#[pymethods]` in `pyo3/src/` plus doc updates.
- Migration plan: Upgrade deliberately in one phase; regenerate `pyo3/tests/` against the same Python version.

**`bincode 1.3` (unmaintained major version):**
- Risk: bincode 1.x is legacy; used only in `pyo3/Cargo.toml`.
- Impact: Low (small usage surface) but blocks edition-2024 migration cleanly.
- Migration plan: Move to bincode 2 or serde_json/byteorder-only serialization.

## Missing Critical Features

**No CI pipeline detected:**
- Problem: No `.github/workflows/`, no CI config in repo root.
- Blocks: Automated `cargo test`/`cargo clippy` gates (CLAUDE.md mandates both as project commands), cross-platform (Linux/Windows) validation of the mmap-heavy code, and Python binding test runs.

**Test-suite organization debt:**
- Problem: `tests/` mixes 26 top-level entries including a compiled-in `src/database/merge_tests.rs` (unit tests inside `src/`, non-idiomatic) and many ad-hoc suites (`cjk_check.rs`, `fresh_test.py`-style naming).
- Blocks: Fast, selective test runs; new contributors cannot tell which suites are canonical.

## Test Coverage Gaps

**Fuzzy query memory/performance claims:**
- What's not tested: The metrics the module claims to report (memory usage, cache hits, aggregation time) — they are hardcoded stubs (see Tech Debt), so tests would fail if run against the stubs.
- Files: `src/fuzzy/performance.rs`, `src/fuzzy/query.rs`
- Risk: Performance regressions invisible.
- Priority: Medium.

**Corrupt-input panic paths:**
- What's not tested: Truncated/malformed FASTA/FASTQ/RKDB inputs against the ~300 non-test `unwrap()` sites.
- Files: `src/io/fasta.rs`, `src/io/fastq.rs`, `src/io/mmap.rs`, `src/hash/table.rs`
- Risk: CLI panics on user data instead of clean errors.
- Priority: High.

**Python binding coverage for merge routes:**
- What's not tested: `pyo3/tests/` covers core/counter/merge basics, but the recently changed merge memory-model (96 B/k-mer admission) is only validated from Rust tests.
- Files: `pyo3/tests/test_database_merge.py`, `src/database/merge_config.rs`
- Risk: Python users could hit OOM conditions Rust tests don't reproduce.
- Priority: Medium.

---

*Concerns audit: 2026-10-08*
