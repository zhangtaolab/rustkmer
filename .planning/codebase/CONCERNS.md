# Codebase Concerns

**Analysis Date:** 2026-06-30

## Tech Debt

**Committed backup/staging files in source tree:**
- Issue: Four `.stage1_fix_backup` / `_backup.rs` files are checked into git alongside active source. These are dead artifacts from an in-progress refactor that were never cleaned up.
- Files: `pyo3/src/database.rs.stage1_fix_backup` (76 KB), `pyo3/src/formatter.rs.stage1_fix_backup` (24 KB), `pyo3/src/fuzzy_query.rs.stage1_fix_backup` (19 KB), `pyo3/src/database_backup.rs` (40 KB)
- Impact: Bloats the repo, confuses readers and tooling (IDE indexing, grep), and risks drift where someone edits the backup instead of the live file. `.gitignore` ignores `*.backup` and `*.bak` but not the `.stage1_fix_backup` suffix.
- Fix approach: `git rm` all four files; extend `.gitignore` with `*.stage1_fix_backup` and `*_backup.rs`. Verify `database.rs` matches the staged version before deletion.

**Dead/duplicate PyO3 modules never wired into the module tree:**
- Issue: `pyo3/src/database_backup.rs` (1127 lines) and `pyo3/src/database_new_approaches.rs` (707 lines) have the exact same module header and `LoadMode`/`PyQueryResult` definitions as the live `pyo3/src/database.rs` (2053 lines), but neither appears in `pyo3/src/lib.rs`'s `mod` declarations. They are unreachable experimental code.
- Files: `pyo3/src/database_backup.rs`, `pyo3/src/database_new_approaches.rs`, `pyo3/src/lib.rs:18-24`
- Impact: ~1800 lines of dead code that compile only if someone re-adds the `mod` line, in which case they would silently shadow the live module. Confusing duplication.
- Fix approach: Delete both files. Any salvageable logic should be cherry-picked into `database.rs` via a deliberate PR.

**Orphaned test file with broken `super::*` path:**
- Issue: `src/database/merge_tests.rs` uses `use super::super::memory::*` and `use super::*`, implying it expects to be declared as `mod merge_tests;` somewhere, but `grep` finds zero references to `merge_tests` anywhere in `src/`. It is never compiled, even under `#[cfg(test)]`.
- Files: `src/database/merge_tests.rs`, `src/database/mod.rs` (no `mod merge_tests;`), `src/database/format.rs:1040-1135` (live duplicate of the same merge-memory tests)
- Impact: Tests give false confidence — they look like coverage but never run. The same scenarios are duplicated in `format.rs`'s inline `#[cfg(test)]` block.
- Fix approach: Either wire it into `src/database/mod.rs` as `#[cfg(test)] mod merge_tests;` (fixing imports) or delete it. Prefer deletion since `format.rs` already covers the cases.

**Duplicate test coverage between `merge_tests.rs` and `format.rs`:**
- Issue: `test_merge_memory_basic`, `test_streaming_merge_*`, and `test_header_*` are duplicated verbatim across `src/database/merge_tests.rs` and the inline `#[cfg(test)] mod tests` in `src/database/format.rs:1000-1306`.
- Files: `src/database/merge_tests.rs`, `src/database/format.rs`
- Impact: Maintenance burden; fixes must be applied in two places (and currently aren't, since one file is dead).
- Fix approach: Delete `merge_tests.rs`, keep the `format.rs` inline tests.

**`proptest` declared in both `[dependencies]` and `[dev-dependencies]`:**
- Issue: `proptest = "1.5"` appears at `Cargo.toml:53` (regular dep) and `Cargo.toml:95` (dev-dep). Production code never imports proptest — it is test-only.
- Files: `Cargo.toml:53`, `Cargo.toml:95`
- Impact: Ships a testing framework into the release binary's dependency graph; inflates compile time and binary surface for no benefit.
- Fix approach: Remove the line at `Cargo.toml:53`, keep the dev-dependency entry.

**Unused crate dependencies inflating build:**
- Issue: `inquire = "0.7"` (interactive prompts) and `chrono = "0.4"` (date/time) are declared in `Cargo.toml` but have zero `use`/`grep` references in `src/**/*.rs`. `niffler` is commented out with a TODO note ("Commented out to avoid zstd issues").
- Files: `Cargo.toml:65` (inquire), `Cargo.toml:80` (chrono), `Cargo.toml:71` (niffler comment), `Cargo.toml:123` (`disable-zstd` feature flag for the removed dep)
- Impact: Dead dependencies slow `cargo build` and expand the audit surface. The `disable-zstd` feature flag and the `niffler` comment are now meaningless.
- Fix approach: Remove `inquire` and `chrono` from `[dependencies]` after a final `cargo +nightly udeps` / `cargo machete` confirmation. Remove the `niffler` comment and the `disable-zstd` feature.

**Suppress-all `#![allow(deprecated)]` at module level:**
- Issue: `pyo3/src/database.rs:7` places `#![allow(deprecated)]` (inner attribute, module-wide) to keep deprecated PyO3 shims compiling. This silences every deprecation warning in the 2053-line module, including any future ones introduced by dependency upgrades.
- Files: `pyo3/src/database.rs:7`, deprecated methods at `pyo3/src/database.rs:756`, `:764`, `:1090`
- Impact: Deprecation ladders (the signal to migrate before a breaking release) are invisible inside this module. New deprecations from PyO3/serde upgrades will be swallowed.
- Fix approach: Replace with scoped `#[allow(deprecated)]` on the three specific deprecated `#[pymethods]`, or delete the deprecated shims if the 2.0.0 migration window has passed.

**Python `filterwarnings` ignores all `DeprecationWarning`:**
- Issue: `pyo3/pyproject.toml` sets `filterwarnings = ["ignore::DeprecationWarning", "ignore::PendingDeprecationWarning"]` globally for pytest.
- Files: `pyo3/pyproject.toml` (`[tool.pytest.ini_options]`)
- Impact: Deprecations from PyO3, numpy, or stdlib are hidden in tests, so breaking-version migrations arrive with no warning.
- Fix approach: Remove the global ignore; use per-test `pytest.warns()` / `filterwarnings` markers where a specific deprecation is expected.

**Library code performs direct console I/O (layering violation):**
- Issue: 129 `eprintln!`/`println!` calls live in non-CLI library modules (not under `src/cli/`). Library code should emit through the `log` crate (already a dependency — `log = "0.4"`, `env_logger = "0.11"`), not write to stdout/stderr directly. Only `src/core/monitoring.rs` uses `log::` today.
- Files: `src/database/format.rs` (~30 calls), `src/database/prefix_cache_merge.rs` (~15 calls), `src/core/database/persistence.rs`, `src/io/fastq.rs`, others
- Impact: Consumers embedding `rustkmer` as a library cannot redirect or silence output; stdout pollution corrupts machine-readable CLI output; violates separation of library vs. presentation.
- Fix approach: Replace all `eprintln!`/`println!` in `src/` (excluding `src/cli/` and `src/main.rs`) with `log::info!`/`log::debug!`/`log::warn!`. Gate the verbose merge progress behind `log::debug!`.

**Hardcoded Chinese (CJK) user-facing strings in production code:**
- Issue: `src/database/prefix_cache_merge.rs` emits progress/error messages in Chinese (e.g. `println!("\n🚀 开始外部排序合并")`, `处理完毕`, `处理失败`, `阶段1 (分桶)`). The rest of the CLI uses English.
- Files: `src/database/prefix_cache_merge.rs:90-112`, `:317-329`
- Impact: Inconsistent UX; non-English speakers (and log parsers) cannot interpret output; blocks any i18n strategy.
- Fix approach: Translate to English, or route through `log::` with English messages. Add a CI grep check for non-ASCII in source strings if a language policy is desired.

**`#[allow(unused_assignments)]` masking control-flow confusion:**
- Issue: `src/database/format.rs:769-770` annotates `kmer_size` and `canonical` with `#[allow(unused_assignments)]` because they are initialized to `None` then "assigned" later via `validate_compatibility_verbose`. The later `unwrap()` at `format.rs:841-842` then panics if validation is skipped.
- Files: `src/database/format.rs:769`, `:770`, `:841`, `:842`
- Impact: The suppression hides that the Option is only ever `Some` by convention. A future refactor that reorders the calls would compile cleanly but panic at runtime.
- Fix approach: Have `validate_compatibility_verbose` return `(u8, bool)` directly and bind it without the `Option` indirection; drop the `allow`.

**`#[allow(unused)]` / `#[allow(dead_code)]` not audited:**
- Issue: Scattered `allow` attributes suppress dead-code warnings without justification comments.
- Files: `src/database/format.rs:769`, `src/database/format.rs:770`, `pyo3/src/database.rs:755` (`#[allow(deprecated)]`)
- Impact: Dead code accumulates silently.
- Fix approach: Audit each `allow`; either remove the dead code or document why the suppression is required.

## Known Bugs

**Undefined-behavior `unsafe` mutation of `String` bytes in benchmark generator:**
- Symptoms: `as_bytes_mut()` writes `b'N'` into a `String` in place.
- Files: `src/cli/commands/benchmark.rs:514-517`
- Trigger: Calling `generate_fuzzy_queries` with any base query longer than 10 chars.
- Cause: Mutating a `String`'s buffer via `as_bytes_mut()` is only sound when the new bytes preserve valid UTF-8. Writing `b'N'` happens to be valid here, but the pattern is fragile and breaks if the replacement byte is ever changed to a non-ASCII value, and it is UB if the `String` is shared/aliased. There is no safety comment justifying the invariant.
- Workaround: None needed for current inputs, but the code is a latent soundness bug.
- Fix approach: Rewrite as safe code: build a new `String` (or `Vec<u8>`) with the byte replaced, e.g. `let bytes = query.into_bytes(); bytes[pos] = b'N'; String::from_utf8(bytes).unwrap()`. Add a `// SAFETY:` comment if any `unsafe` is retained.

**`unreachable!()` in `format_bytes` reachable on empty input:**
- Symptoms: Panics with `unreachable!()` if the loop exits without returning.
- Files: `src/database/memory.rs:193`
- Trigger: The loop guards `i == UNITS.len() - 1` on the last iteration, so it is currently unreachable — but only by virtue of the specific `UNITS` table. Refactoring the table (e.g. to `[]`) makes it reachable.
- Cause: Reliance on an implicit invariant rather than encoding it.
- Workaround: None.
- Fix approach: Replace `unreachable!()` with a final `format!("{} B", bytes)` fallback, or return `Result`.

## Security Considerations

**`unsafe` `env::set_var` / `env::remove_var` (Rust 2024 soundness):**
- Risk: Mutating the process environment is `unsafe` since Rust 1.80 because it can race with other threads reading `env::var`. The config manager calls these from `set_env_var`/`remove_env_var` and from tests.
- Files: `src/config/manager.rs:498`, `:504`, `:612`, `:627-629`
- Current mitigation: The calls are wrapped in `unsafe {}` (so they compile), but no synchronization guarantees that no other thread is reading the environment concurrently.
- Recommendations: Document a `// SAFETY:` comment stating these must only be called from single-threaded setup, or move env overrides to a pre-thread-spawn initialization phase. Consider replacing runtime env mutation with an in-memory `RwLock<Config>` override map.

**Memory-mapped file I/O lacks `// SAFETY:` justification:**
- Risk: `unsafe { MmapOptions::new().map(&file)? }` maps a file that could be modified by another process while mapped, yielding UB on the borrowed slice. Same for `map_mut`.
- Files: `src/memory/efficiency.rs:176`, `src/memory/efficiency.rs:222`, `src/io/mmap.rs:28`, `pyo3/src/database_backup.rs:440`
- Current mitigation: None documented.
- Recommendations: Add `// SAFETY:` blocks stating the file is opened read-only and not externally mutated, or advisory-lock the file. For `map_mut`, document the exclusive-write invariant.

**No Rust CI workflow (only docs + perf regression):**
- Risk: `.github/workflows/` contains `docs.yml` and `performance-regression.yml` but no workflow runs `cargo test`, `cargo clippy -- -D warnings`, or `cargo fmt --check`. PRs can merge with failing tests or new warnings.
- Files: `.github/workflows/` (no `ci.yml` / `rust.yml`)
- Current mitigation: Local `cargo test` / `cargo clippy` per `CLAUDE.md`, but not enforced.
- Recommendations: Add a matrix CI workflow (linux/macos, stable + 1.80 MSRV) running `fmt`, `clippy -D warnings`, `test`, and the maturin wheel build for the pyo3 crate.

**`.coverage` files committed to git:**
- Risk: `pyo3/.coverage` and `pyo3/tests/.coverage` (coverage databases) are tracked in git. They are build artifacts that change on every test run, creating noise and potential information leakage about local paths.
- Files: `pyo3/.coverage`, `pyo3/tests/.coverage`
- Current mitigation: `.gitignore` lists `python/.coverage` (wrong path) but not `pyo3/.coverage`.
- Recommendations: `git rm --cached pyo3/.coverage pyo3/tests/.coverage` and add `pyo3/.coverage` to `.gitignore`.

## Performance Bottlenecks

**`merge_databases_inmemory` loads every k-mer of every input into a single hashmap:**
- Problem: The in-memory merge path (`format.rs:752-842`) calls `db.all_kmers()?` per input database and accumulates into one `HashMapBrown<u128, u32>`, defeating the streaming/external-sort machinery that exists alongside it.
- Files: `src/database/format.rs:808-824` (`for (i, db) in databases.iter().enumerate() { let db_kmers = db.all_kmers()?; ... }`)
- Cause: The in-memory path was written before the streaming merge (`src/database/streaming_merge.rs`, `src/database/prefix_cache_merge.rs`) and was never routed through it.
- Improvement path: Default to the streaming/prefix-bucket merge for all sizes; gate the in-memory path behind an explicit `--merge-strategy memory` flag for small inputs only.

**`u128` k-mer encoding doubles memory vs. minimum bit width:**
- Problem: All k-mer storage uses `u128` (16 bytes) even for k ≤ 32 (which fits in `u64`, 8 bytes). For the common k=21 case this is ~2× wasted memory in hashmaps and on-disk.
- Files: `src/database/format.rs`, `src/kmer/encoding.rs` (`encode_kmer_u128`), `src/database/prefix_cache_merge.rs:461`, `:645`, `:679`
- Cause: Single-type simplification; no conditional packing.
- Improvement path: Introduce a `Kmer` enum/newtype that selects `u64` vs `u128` by `kmer_size` at database creation, or pack two k-mers per `u128` for small k.

**Pervasive `.clone()` on hot query paths:**
- Problem: Query result types (`PyQueryResult`, `PrefixQueryResult`) are cloned per result row, and `database.rs` (pyo3) shows heavy `.clone()` usage in result construction.
- Files: `pyo3/src/database.rs`, `src/database/query.rs:140` (`self.cached_entries.as_ref().unwrap()`)
- Cause: Owned `String` fields in result structs returned by value.
- Improvement path: Return `Cow<str>` or borrowed views; only materialize owned `String`s at the Python boundary.

## Fragile Areas

**`src/database/format.rs` (1306 lines, god module):**
- Files: `src/database/format.rs`
- Why fragile: Mixes `RKDatabase`, `DatabaseHeader`, `KmerEntry`, `from_file_path`, `to_file_path`, `merge_databases_inmemory`, `merge_databases_streaming`, `validate_compatibility_verbose`, progress-bar rendering, and a 300-line inline `#[cfg(test)]` block. Any change risks colliding concerns.
- Safe modification: Make targeted edits; prefer extracting a concern (e.g. header ser/de, merge orchestration) into its own file before adding features.
- Test coverage: Inline tests cover merge and header round-trip, but the streaming-merge error paths and the `validate_compatibility_verbose` mismatch branches are not asserted.

**`pyo3/src/database.rs` (2053 lines, single PyO3 class):**
- Files: `pyo3/src/database.rs`
- Why fragile: One `#[pyclass] PyDatabase` with dozens of `#[pymethods]` (query, batch query, prefix, fuzzy, stats, merge, backup, restore, deprecated shims). The module-wide `#![allow(deprecated)]` hides warnings.
- Safe modification: Split into sub-modules (`query`, `merge`, `stats`, `compat`) re-exported from `database.rs`; keep the `#[pyclass]` in one place but move method bodies.
- Test coverage: Python contract tests exist under `tests/contract/` but the deprecated method paths are not exercised.

**`src/database/prefix_cache_merge.rs` (961 lines) — external sort orchestrator:**
- Files: `src/database/prefix_cache_merge.rs`
- Why fragile: Parallel rayon merge with manual `Arc<AtomicUsize>` progress tracking, hardcoded memory thresholds via `sys_info::mem_info()`, and multiple `try_into().unwrap()` byte-slice conversions (lines 461, 463, 645, 646, 679, 680, 917, 918) that assume a specific on-disk record layout. A change to the record size silently breaks these.
- Safe modification: Centralize the `(u128, u32)` record layout (20 bytes) as a `const RECORD_SIZE` and a typed reader; never inline `try_into().unwrap()`.
- Test coverage: Round-trip merge is tested, but the memory-threshold branch selection and partial-failure cleanup are not.

## Scaling Limits

**Single-process, memory-bound merge:**
- Current capacity: Documented for ~100M k-mers in memory; beyond that the streaming path is used.
- Limit: The in-memory path (`merge_databases_inmemory`) has no upper bound check before allocating the hashmap; a large merge OOMs the process. The streaming path shards by 4-prefix (256 buckets), which caps bucket count but not bucket size.
- Scaling path: Add explicit memory-budget admission control; allow configurable prefix length (5- or 6-prefix) for very large inputs.

**`u32` k-mer count saturates at `u32::MAX`:**
- Current capacity: `KmerEntry.count` is `u32`; merge saturates at `u32::MAX` (`format.rs:816-822`).
- Limit: Datasets where a single k-mer appears > ~4.29 billion times lose precision silently (no warning).
- Scaling path: Promote count to `u64`, or emit a warning on saturation.

## Dependencies at Risk

**`hashbrown = "0.14"` (two major versions behind):**
- Risk: Current is 0.15+; 0.14 is unmaintained for new features.
- Impact: Misses API/perf improvements; eventual forced upgrade touches every `HashMap` site.
- Migration plan: Bump to latest `hashbrown`; `cargo update -p hashbrown` then fix `DefaultHashBuilder` import paths.

**`pyo3 = "0.27.2"` pinned in `pyo3/Cargo.toml`:**
- Risk: PyO3 releases breaking minors frequently; 0.27 may lag Python 3.13+ support.
- Impact: Newer Python versions may not build.
- Migration plan: Track upstream PyO3 release notes; test against Python 3.11/3.12/3.13 matrix in CI before bumping.

**`maturin` build config duplicated in `pyproject.toml`:**
- Risk: `[tool.maturin]` and `[tool.maturin.build]` both set `features = ["pyo3/extension-module"]`; the two sections can diverge and one silently overrides the other depending on maturin version.
- Impact: Build reproducibility depends on which section maturin reads.
- Migration plan: Keep only `[tool.maturin]`; remove the redundant `[tool.maturin.build]` block.

## Missing Critical Features

**No reproducible-build lockfile in git:**
- Problem: `Cargo.lock` is gitignored (`.gitignore: Cargo.lock`), but the crate ships a binary (`[[bin]] name = "rustkmer"`). Binaries should commit `Cargo.lock` for reproducible builds; libraries may omit it.
- Blocks: Reproducible CI builds, deterministic dependency resolution, supply-chain audits.

**No enforced MSRV check:**
- Problem: `CLAUDE.md` declares "Rust 1.80+ stable" but no `rust-version` field in `Cargo.toml` and no CI job verifying the MSRV.
- Blocks: Users on older toolchains hit cryptic compile errors instead of a clear MSRV message.

**Python version policy inconsistent across sources:**
- Problem: `CLAUDE.md` says "Python 3.10+", `pyo3/pyproject.toml` says `requires-python = ">=3.11"`, classifiers list 3.11/3.12 only, while `[tool.mypy].python_version = "3.11"`. Five `.venv*` directories (3.10/3.11/3.12/3.13 + generic) suggest local confusion about the target.
- Blocks: Downstream users cannot tell which Python versions are supported.

## Test Coverage Gaps

**Orphaned `merge_tests.rs` gives false coverage signal:**
- What's not tested: The file documents merge-memory tests but is never compiled into the test binary.
- Files: `src/database/merge_tests.rs`
- Risk: A reader believes merge memory behavior is covered when it is not (only the `format.rs` inline duplicates are).
- Priority: High (delete or wire in)

**Streaming-merge error paths untested:**
- What's not tested: Partial-failure cleanup (the `for temp_file in files_to_delete { let _ = std::fs::remove_file(...) }` branch at `prefix_cache_merge.rs:309-313`), memory-threshold branch selection, and the `sys_info::mem_info()` failure fallback.
- Files: `src/database/prefix_cache_merge.rs:296-330`, `:410-490`
- Risk: A failing prefix shard leaves temp files behind and reports success; silent disk exhaustion.
- Priority: High

**PyO3 deprecated method paths untested:**
- What's not tested: The three `#[deprecated]` `#[pymethods]` in `pyo3/src/database.rs:756,764,1090`.
- Files: `pyo3/src/database.rs`, `tests/contract/`
- Risk: Backward-compat shims can break without detection (and the module-wide `#![allow(deprecated)]` hides compiler warnings too).
- Priority: Medium

**`benchmark.rs` unsafe helper untested:**
- What's not tested: `generate_fuzzy_queries` (the `as_bytes_mut` site) has no unit test asserting UTF-8 validity of its outputs.
- Files: `src/cli/commands/benchmark.rs:505-523`
- Risk: A future edit to the replacement byte produces UB silently.
- Priority: Medium

**Count export format (current branch feature) lacks contract tests:**
- What's not tested: The `count` command's `format` option (`src/cli/commands/count.rs:32`, dispatch at `:264-269`) — text vs binary output round-trips are only partially covered.
- Files: `src/cli/commands/count.rs`, `src/cli/args.rs`
- Risk: Format regressions on the active `feature/pyrustkmer-v0.4.0-count-export-format` branch.
- Priority: High (active development area)

---

*Concerns audit: 2026-06-30*
