---
last_mapped_commit: 511b99e5b23614e60426e04a74bcf91a3c5d1a32
last_mapped_at: 2026-10-07
---
# Codebase Concerns

**Analysis Date:** 2026-10-07

Scope: full repo at `511b99e` (branch `dev`). Phases 01 (Foundation & Quality) and 02 (Parallel Counting) landed; Phase 03 (Memory Safety) is planned but not started. All findings below were re-verified against the live source on 2026-10-07.

Severity key: **[S1]** data corruption / silent wrong results / OOM on valid input · **[S2]** crashes, aborts, disk exhaustion, silent partial success · **[S3]** performance, fragility, maintainability · **[S4]** hygiene.

---

## Tech Debt

### Merge is not actually bounded in ANY of its three paths (Phase 03 blocker)

- Issue: All three merge strategies materialize the entire result set in RAM before it is written. `merge_databases_streaming` (`src/database/format.rs:710`) drains the k-way heap iterator into `let mut sorted_kmers: Vec<(u128, u32)> = Vec::new()` (`format.rs:742-749`), then hands it to `from_kmer_pairs` (`format.rs:459-468`), which allocates a *second* full-size `Vec<KmerEntry>`. `(u128, u32)` is 32 B/entry (16-byte alignment), `KmerEntry` is 24 B/entry → **peak ≈ 56 B per distinct k-mer**, plus the returned `RKDatabase` is held in RAM by the caller while being written out.
- Files: `src/database/format.rs:710-764` (`merge_databases_streaming`), `:766-901` (`merge_databases_inmemory`), `:459-468` (`from_kmer_pairs`).
- Impact: ROADMAP Phase 3 success criterion 1 ("Merge defaults to the streaming path — human-scale merges no longer OOM") **cannot be met by flipping the routing flag alone**. The streaming body must write the output incrementally instead of accumulating `sorted_kmers`.
- Fix approach: stream header-then-entries directly to the output path (`.rkdb` is already sequential), or feed the heap iterator straight into `DatabaseHeader::write_to` + `KmerEntry::write_to`. Phase 3 plan 03-01 (D-01/D-02) must be widened to cover the streaming body.

### Every input `.rkdb` is fully deserialized 3–5× per merge

- Issue: `RKDatabase::from_file_path` (`src/database/format.rs:287-350`) eagerly loads **all** entries into `Vec<KmerEntry>` — it is a header read plus a full materialization, not a metadata peek.
  - `execute_merge` (`src/cli/commands/merge.rs:167-241`) validates inputs in one loop, then a second unconditional loop re-validates the same databases (the `if !args.use_prefix_cache` guard at `:167` and the bare loop at `:241` are duplicates).
  - `RKDatabase::merge_databases` (`format.rs:644-652`) loads every input again just to sum `total_kmers`.
  - `should_use_streaming` (`format.rs:692-708`) loads every input **again**.
  - `merge_databases_inmemory` (`format.rs:813-817`) loads every input **again** and holds them all simultaneously, then calls `db.all_kmers()` (`format.rs:832`) per DB → yet another full copy.
  - Prefix-cache path is worse: `merge_databases_prefix_cache` (`format.rs:920-924`) loads **all** inputs into `db_refs` at once, and `ExternalSortMerger::new` (`src/database/prefix_cache_merge.rs:39-51`) loads input[0] **and** every input again the same call.
- Impact: peak RSS ≈ 3–5× the size of the input set before the merge itself allocates. The "memory-efficient prefix cache" is the least memory-efficient path. Phase 3 D-01 flags only `should_use_streaming`; the duplication in `execute_merge` and `prefix_cache_merge` is not covered.
- Fix approach: add a header-only reader (`read_header(path) -> DatabaseHeader`) and use it for every sizing/validation call site. Delete the duplicate validation loop in `merge.rs`.

### Memory estimator is wrong by ~2× and uses a hardcoded constant

- Issue: `estimated_memory = total_kmers as usize * 24` (`format.rs:654`, `format.rs:705`). A materialized `(u128, u32)` entry is 32 B with padding and `DashMap`/`hashbrown` add control-byte + load-factor overhead. Under-estimating by ~2× means `should_use_streaming` routes *in-memory* for datasets that are far over budget.
- Compounding: `get_default_memory_limit()` (`src/database/merge_config.rs:142-181`) returns **50% of total system RAM** and falls back to a hardcoded **32 GB**. On a shared/oversubscribed machine this authorises allocations the process may never get; there is no `MemAvailable` check.
- Files: `src/database/format.rs:654`, `:705`; `src/database/merge_config.rs:142`.
- Fix approach: one named constant with a documented per-entry size measured against the real structures; use available (not total) memory.

### `KmerCounter` has three mutually inconsistent memory estimates

- Issue: `KmerCounter::memory_usage()` returns `len() * 44` (`src/hash/table.rs:283-286`); merge uses `* 24`; `DatabaseIndex::memory_usage_bytes()` uses `* 36` (`src/database/index.rs`). All three are guesses, none is measured, and none is cross-checked.
- Fix approach: delete the estimates or derive them from one shared constant.

### ~3,600 lines of dead/unreferenced library code

- Issue: Modules that read as live infrastructure but are never called from any production path:
  - `src/memory/efficiency.rs` (509 lines) — `MemoryManager`, `MemoryConfig`, `PageIterator`. Only re-exported by `src/memory/mod.rs:9`; zero call sites.
  - `src/hash/overflow.rs` (301 lines) — `DiskOverflow`, a disk-backed overflow store, self-documented as the answer to unbounded counting memory. **Zero references anywhere.** It also stores k-mers as `u64` (`overflow.rs:54`) while the counter is `u128`, so it is silently incompatible with k > 32.
  - `src/hash/matrix.rs` (125 lines) — `MatrixHashFunction`, self-documented as "a placeholder implementation". Zero references.
  - `src/database/index.rs` (262 lines) — `DatabaseIndex`. Only re-exported by `src/database/mod.rs:20`.
  - `src/database/suffix_query.rs` (477 lines) — `SuffixQuery` / `decide_query_strategy`. Only declared in `src/database/mod.rs:17`; no caller.
  - `src/database/merge_error.rs` (256 lines) — `MergeError` recovery machinery. Only declared in `src/database/mod.rs:10`; zero references.
  - `src/database/prefix_query.rs` (225 lines) — `extract_kmers_by_prefix`, now used only by the dead `suffix_query.rs`.
  - `src/output/binary.rs` + `text.rs` (428 lines) — a third serialization format that nothing writes or reads; `grep "crate::output"` returns nothing outside the module.
  - `src/core/database/persistence.rs` (583 lines) — a **third** persistence layer (bincode + `HashMap<String, u64>`), re-exported as `rustkmer::core::merge_databases` (`src/core/mod.rs:22`). A library user calling that name gets an entirely different, unbounded implementation than `RKDatabase::merge_databases`. Never called by CLI or pyo3.
  - `src/core/monitoring.rs` (474 lines) — ~95% gated behind `#[cfg(feature = "profiling")]`, which CI never enables; it cannot have rotted visibly, it will simply fail to build the first time the feature is turned on.
  - `src/database/prefix_cache_merge.rs:30` carries `#[allow(dead_code)]` on the entire `impl ExternalSortMerger` block.
- Fix approach: delete, or wire up. `DiskOverflow` is the honest answer to "what happens when the DashMap outgrows RAM" and there is currently no answer at all.

### pyo3 crate carries committed backup files and unreferenced modules

- Issue: `pyo3/src/database_backup.rs` (1,127 lines), `pyo3/src/database_new_approaches.rs` (707 lines), `pyo3/src/database.rs.stage1_fix_backup` (76 KB), `formatter.rs.stage1_fix_backup`, `fuzzy_query.rs.stage1_fix_backup` are all **git-tracked but not declared as modules** in `pyo3/src/lib.rs:17-23`. They are excluded from the CJK gate by name (`tests/cjk_check.rs`) but remain in the repo and in every grep/IDE index.
- Impact: ~3,000 lines of stale code; a future `mod` addition could accidentally resurrect a shadow module.
- Fix approach: delete; the `.stage1_fix_backup` suffix is not covered by `.gitignore` (`*.backup`/`*.bak` only), so extend the ignore list if any remain.

### Orphaned test file never compiled

- Issue: `src/database/merge_tests.rs` (75 lines, not 2,575 bytes of tests) uses `use super::*` and expects `mod merge_tests;`, but `grep -rn "merge_tests" src/` finds zero references and `src/database/mod.rs` does not declare it. It is never compiled, even under `#[cfg(test)]`.
- Impact: false coverage signal; the same scenarios are duplicated in `format.rs`'s inline `#[cfg(test)]` block.
- Fix approach: delete it (prefer) or wire it in and fix imports.

### Dead configuration, no-op flags, and superseded metadata

- Issue:
  - `MergeConfig::use_streaming` (`src/database/merge_config.rs:16`, `:35`) is **never read** by `merge_databases` — routing is decided solely by `should_use_streaming`. `format.rs` `test_merge_streaming_basic` sets it `true`, which therefore exercises the *in-memory* path despite its name; the streaming merge has no effective test coverage.
  - `MergeArgs::batch_size` (`src/cli/commands/merge.rs:117-124`, default 50000) is never plumbed into `MergeConfig` — there is no `batch_size` field. The flag is accepted and silently discarded.
  - `--merge-mode` is only consulted inside the prefix-cache path, which requires `--use-prefix-cache`; without it the flag does nothing.
  - `ExternalSortMerger.num_threads` is stored and never used; both phases call `rayon::current_num_threads()` (`prefix_cache_merge.rs:127`, `:278`).
  - `pyo3/pyproject.toml` defines both `[tool.maturin]` and `[tool.maturin.build]` with duplicate `features = ["pyo3/extension-module"]`; the two sections can diverge per maturin version.
  - `pyo3/pyproject.toml:103-106` globally ignores `DeprecationWarning` / `PendingDeprecationWarning` for pytest, hiding PyO3/numpy migrations.
- Fix approach: honor the fields or remove them from the CLI surface; consolidate maturin config; remove the global warning filter.

### Unused direct dependencies

- Root `Cargo.toml`: `smallvec = "1.13"` (`:40`), `ahash = "0.8"` (`:44`), `inquire = "0.7"` (`:67`), `chrono = "0.4"` (`:82`) — zero `use`/grep references in `src/`. `niffler` is commented out (`:73`) and the `disable-zstd` feature (`Cargo.toml:131`) now controls nothing.
- `pyo3/Cargo.toml`: `bincode`, `byteorder`, `parking_lot`, `hashbrown`, `anyhow`, `thiserror`, `flate2`, `xz2` have zero references in `pyo3/src/` (only the uncompiled backup files use some of them). `bzip2`/`xz2` appear only in doc comments. Compression is handled through `rustkmer::io::fastq::DefaultCompressedFileReader`.
- Impact: slower builds, larger audit surface, misleading dependency graph.
- Fix approach: remove after a `cargo machete` confirmation; drop the `niffler` comment and `disable-zstd` feature.

### CI / workflow debt

- `.github/workflows/docs.yml` is **broken in three ways**: it runs `pip install -r docs/requirements.txt` (file does not exist), runs `pydocstyle python/rustkmer/` (directory does not exist — the bindings live in `pyo3/`), and calls `python ../scripts/check_broken_links.py` (script does not exist). It also `cd docs` then runs `mkdocs build --strict`, but `mkdocs.yml` is at the repo root. Trigger paths include `python/**`, which does not exist.
- `.github/workflows/performance-regression.yml` is effectively a no-op: it probes for `cargo bench --bench python_cli_comparison`, but the `[[bench]]` target is commented out in `Cargo.toml:123-125`; `scripts/check_performance_regression.py` does not exist (soft-skipped by design); it triggers on branches `develop` and `012-python-bindings-complete`, neither of which exists (the repo uses `dev`/`main`). The PR-comment step reads `report.regressions`, which the placeholder JSON never contains.
- CI cache keys hash `Cargo.lock` / `pyo3/Cargo.lock` (`ci.yml:60`, `:88`, `:118`), but **no lockfile is committed or present anywhere** (see Dependencies at Risk).
- `.pre-commit-config.yaml` hooks all target `files: ^python/.*\.py$` and `python/rustkmer/` — a directory that no longer exists; the hooks never match any file.
- Fix approach: repair or delete the docs/perf workflows; reconcile branch names; add `Cargo.lock` (see below); point pre-commit at `pyo3/**`.

### Committed artifacts and local-path pollution

- Issue: `.coverage` databases are git-tracked at `pyo3/.coverage` and `pyo3/tests/.coverage` (52 KB each) even though `.gitignore` lists `python/.coverage` (wrong path). Generated test reports are tracked at `tests/007-api-compatibility/test_reports/*.json`. Root scratch scripts `fresh_test.py` and `precise_analysis.py` are committed; `fresh_test.py` contains a hardcoded `/Users/forrest/GitHub/rustkmer/pyo3/target/debug` path (note the wrong case) and `precise_analysis.py` is a one-off Chinese-language N-region analysis script. `scripts/test_all_envs.sh`, `test_current.sh`, `test_pyo3_version.sh` hardcode `/Users/forrest/miniconda3` and `/Users/forrest/GitHub/...`.
- Impact: repo noise, non-portable scripts, and a stale-path bug that will confuse any future contributor.
- Fix approach: `git rm --cached` the artifacts, extend `.gitignore` (`pyo3/.coverage`, `*.stage1_fix_backup`, `test_reports/`), delete or move the scratch scripts, and fix the shell scripts to use `$HOME`/repo-relative paths.

### Stale auto-generated project metadata

- Issue: `CLAUDE.md` and `AGENTS.md` are auto-generated and stale: they list PyO3 0.22.6 / 0.23.4 and "Python 3.8+", while the live bindings are PyO3 0.27.2 / Python ≥3.11; all dependencies between them differ. `AGENTS.md` still says `cd src` + `pytest` for a Rust repo.
- Impact: agents and contributors following these files get incorrect guidance (the AGENTS.md instructions are injected into every session).
- Fix approach: regenerate from the current `Cargo.toml`/`pyo3/Cargo.toml`, or trim to pointers at the real manifests.

---

## Known Bugs

### [S1] `KmerEntry::read_from` silently corrupts any k-mer count above 1,000,000

- Symptoms: A count of `1_000_001` written and read back becomes `1_092_158_208`. Any `.rkdb` with counts above 1M is read wrong by `merge`, `stats`, `query`, `dump`, `prefix-query`, and `PyDatabase`.
- Cause: `src/database/format.rs:219-237`:
  ```rust
  let count_le = u32::from_le_bytes(count_bytes);
  let count_be = u32::from_be_bytes(count_bytes);
  // If little-endian gives an unreasonable count (> 1M), use big-endian
  let count = if count_le > 1_000_000 { count_be } else { count_le };
  ```
  The writer (`format.rs:210-213`, `write_u32::<LittleEndian>`) **always** writes LE, so the BE branch is unreachable for anything this crate produced — it exists only to misfire on legitimate large counts.
- Aggravating inconsistency: `prefix_cache_merge.rs` (`:475-477`, `:664-665`, `:698-699`) reads raw 20-byte records with `u128::from_le_bytes` / `u32::from_le_bytes` directly and **skips the heuristic**. The same file can therefore yield different counts depending on which reader loads it.
- Trigger: any dataset where a k-mer genuinely occurs >1M times — realistic for small k on metagenomes/high-coverage data, `--no-canonical` repeats, and merged multi-sample databases. Round-tripping `count = 1_000_001` reproduces it deterministically.
- Coverage gap: no test or fixture anywhere uses `count > 1_000_000` (`grep` finds only unrelated CLI defaults and `format.rs:1155`, which uses exactly 1,000,000), so the bug is invisible.
- Fix approach: remove the heuristic; read `u32` little-endian unconditionally, matching the writer. If legacy BE files must be supported, gate on an explicit header/version flag, never a magnitude guess. Add a >1M round-trip test and route the prefix-cache readers through the same decoder.

### [S1] `pyrustkmer` strips non-ACGT bases instead of skipping affected k-mers

- Symptoms: `PyCounter.add_sequence("ACGTNNNACGT")` counts k-mers that span the N run as if the bases were contiguous. Python counts diverge from the CLI for the same input.
- Cause: `pyo3/src/counter.rs:284`, `:740`, `:800` all do:
  ```rust
  .filter(|&b| matches!(b.to_ascii_uppercase(), b'A' | b'C' | b'G' | b'T'))
  ```
  This **deletes** non-ACGT characters, gluing the flanking bases together. The CLI (`src/cli/commands/count.rs`) instead calls `encode_kmer_bytes_u128`, gets `Err` on the invalid base, and skips only the affected window.
- Aggravating: the docstring at `pyo3/src/counter.rs:264-265` states the *opposite* of what the code does: "Invalid characters (N, etc.) are skipped" / "K-mers spanning invalid characters are not counted". The documented contract is violated silently.
- Impact: silent scientific miscounting on any real FASTQ (N runs are ubiquitous). Violates PCOUNT-04 ("results identical") and the dual-surface constraint in PROJECT.md.
- Fix approach: preserve invalid bases as a sentinel that the encoder rejects (matching the CLI), and add a CLI-vs-Python differential test on an N-containing fixture.

### [S2] Prefix-cache merge reports success after partial failure

- Issue: `merge_prefix_buckets` (`src/database/prefix_cache_merge.rs:379-403`) counts per-bucket errors into `error_count`, logs `"Merge complete: {} prefix buckets, {} errors"`, then **returns `Ok(())` unconditionally**. `concatenate_final_output` then concatenates whatever buckets exist and writes a syntactically valid `.rkdb` with silently missing k-mers.
- Impact: data loss with a success exit code and a valid-looking output file — the worst failure mode in the codebase.
- Fix approach: return `Err` when `error_count > 0`; never write an output database from a partially-merged bucket set.

### [S2] Prefix-cache streaming merge can silently drop the tail of a bucket file

- Issue: In `merge_single_prefix_streaming` (`src/database/prefix_cache_merge.rs:622-637`), when a file's batch is exhausted mid-run and the newly-read batch's first entry equals `current_kmer`, the code adds that entry's count but **neither removes it from the batch nor pushes it onto the heap**:
  ```rust
  if current_kmer == Some(first_entry.kmer) {
      current_count += first_entry.count;   // accounted
  } else {
      heap.push(HeapEntry { ... });          // NOT pushed in the equal branch
  }
  ```
  Since that file then has no heap entry, it is never popped again, so `file_states[idx].2.remove(0)` never runs for it and the remainder of the new batch (and every later batch for that file) is silently discarded when the heap drains.
- Trigger: any bucket file where a duplicate k-mer straddles a 4 MB batch boundary — reachable whenever duplicates span inputs (they always land in the same bucket) and the bucket is large enough to batch.
- Fix approach: always push, and let the normal `kmer == current_kmer` accumulation path handle equality; or use a `VecDeque` cursor design.

### [S2] Append-mode, predictable, non-unique temp file names corrupt concurrent and stale merges

- Issue: Bucket shards are named `ext_sort_{AAAA}_file_{000..}.tmp` (`prefix_cache_merge.rs:143`, `:256`) inside `MergeConfig::temp_dir` (default `std::env::temp_dir()`, a world-writable shared location) and written with `OpenOptions::new().create(true).append(true)` (`prefix_cache_merge.rs:232-236`) — **never truncated**. The prefix-cache output is a fixed `external_sort_merge_output.tmp` (`format.rs:944`).
  - There is **no PID or randomness** in any of these names (contrast `TempFileManager` in `streaming_merge.rs:118`, which includes `std::process::id()`).
  - A crashed run's shard files are **appended to**, mixing two merges' k-mers into one bucket → wrong counts.
  - Two concurrent `rustkmer merge --use-prefix-cache` runs corrupt each other, and race on the fixed final output name.
- Partial mitigation: Phase 3 D-06 specifies a process-unique subdir + startup sweep; this bug is the strongest justification for it.
- Fix: `tempfile::TempDir` (currently dev-dependency only) or `rustkmer-merge-<pid>-<rand>/` subdir with `create(true).truncate(true)` and `O_EXCL`.

### [S2] `ExternalMerger` leaks temp chunk files when a later input fails

- Issue: `ExternalMerger` has **no `Drop` impl**. `sort_database` (`src/database/streaming_merge.rs:236-282`) uses a local `TempFileManager` (which cleans up on unwind) but then calls `take_files()` (`streaming_merge.rs:166`), moving ownership into `self.temp_files` with no cleanup owner. If a later input fails, or `merge_sorted_chunks` is never reached, every earlier chunk is orphaned.
- Aggravating: `[profile.release] panic = "abort"` (`Cargo.toml:112`) means `Drop` does not run on panic at all, so `TempFileManager::drop` (`streaming_merge.rs:170-176`) is also ineffective in release builds.
- Impact: silent disk exhaustion in a shared `/tmp` after repeated failed merges (see also MERGE-03).
- Fix approach: give `ExternalMerger` a `Drop`/RAII shard guard; rely on the subdir + startup sweep for the abort/kill case.

### [S2] Prefix-cache merge leaves a full-size copy of the output in the temp dir

- Issue: `merge_databases_prefix_cache` writes `external_sort_merge_output.tmp` (`format.rs:944`), reads it back with `from_file_path` (`format.rs:950`) and **never deletes it**. `concatenate_final_output` additionally writes a sibling `.json` metadata file (`prefix_cache_merge.rs:868-880`) that is never removed.
- Impact: every prefix-cache merge permanently retains one full `.rkdb`-sized temp file plus JSON in the system temp dir — tens of GB per genome-scale run, with world-readable default permissions.
- Fix approach: write into the run's private subdir and remove on completion; do not emit sidecar JSON into the temp dir.

### [S2] Batch reader swallows I/O errors as clean EOF

- Issue: `read_batch_from_file_sync` (`src/database/prefix_cache_merge.rs:682-710`) ends its read loop with `Err(_) => break`. Any mid-read I/O error is treated as end-of-file; the truncated batch is returned as if complete and the merge proceeds.
- Impact: silent partial results on disk errors (EIO, ENOSPC-adjacent failures) with no warning; compounds the `Ok(())`-on-partial-failure bug above.
- Fix approach: propagate the error (`Err(e) => return Err(...)`); only `Ok(0)` means EOF.

### [S3] `.expect()` inside a rayon worker aborts the process

- Issue: `prefix_cache_merge.rs:299` calls `.expect("Prefix not found in map")` inside the `into_par_iter().map(...)` closure. Combined with `panic = "abort"` in the release profile, any panic here kills the process rather than surfacing an error.
- Fix approach: propagate via the closure's existing `Result<(), String>` return instead of `expect`.

### [S3] `dump` computes the wrong entry size for k ≤ 32

- Issue: `.rkdb` v2 entries are **always** 20 bytes (`u128` + `u32`), but `dump` uses `entry_size = if version == 2 && kmer_size > 32 { 20 } else { 12 }` (`src/cli/commands/dump.rs:138-144`). For any k ≤ 32 database this **over-reports the entry count by ~1.67×** and prints a wrong "Calculated database entries".
- Mitigation: the read loop breaks on EOF, so emitted records are complete; but `num_entries` is derived from file size rather than `header.total_kmers`, so a truncated `.rkdb` dumps its truncated contents and exits 0 with no warning.
- Fix approach: use the constant 20 (Phase 3 already calls for centralizing `RECORD_SIZE`); iterate `header.total_kmers` and error if the file is short.

### [S3] `DatabaseQuery::query_from_disk` mis-handles an empty database

- Issue: `let mut right = self.header.total_kmers - 1;` (`src/database/query.rs:173`) underflows for `total_kmers == 0`. Debug builds panic; release wraps to `u64::MAX` and the binary search seeks far past EOF, returning a confusing I/O error instead of `None`.
- Fix approach: early-return `Ok(None)` when `total_kmers == 0`.

### [S3] Wildcard expansion overflows `usize` at ≥32 wildcards

- Issue: `4_usize.pow(wildcard_positions.len() as u32)` at `src/fuzzy/wildcard.rs:45`, `:113`, `:149` and `src/fuzzy/expansion.rs:198`. On 64-bit, `4^32 = 2^64` overflows: debug panics, release **wraps to 0**. A wrapped `0` passes the `combination_count > limit` guard, so the recursion at `wildcard.rs:65-84` proceeds toward `4^64` strings.
- Related: `src/fuzzy/mutation.rs:270-273`, `:505-508` use `sequence_length.pow(i) / i.pow(i)` and `3_usize.pow(i)` — same overflow exposure. `validate_expansion_params` (`expansion.rs:176`) hardcodes `let wildcard_count = 0; // TODO: Calculate from query`, so the combinatorial-explosion guard never accounts for wildcards at all.
- Impact: `rustkmer fuzzy-query` with a long `N`-containing pattern is a hang/OOM DoS; in release builds no error is raised.
- Fix approach: use `checked_pow`, reject `wildcard_count > 16`, and fill in the `TODO`.

### [S3] Public APIs that panic instead of returning errors

- `hamming_distance` (`src/fuzzy/mutation.rs:128-133`) panics on length mismatch; it is public and reachable from `fuzzy-query`.
- `format_bytes` (`src/database/memory.rs:176-195`) ends in `unreachable!()`; currently unreachable only because of the exact `UNITS` table.
- `memory_usage_mb`/`format_bytes`-style helpers aside, the library's `#![deny(clippy::print_stdout, ...)]` shields stdout but not panics.
- Fix approach: return `Result`/`Option`; replace `unreachable!()` with a fallback unit.

### [S4] Remaining inconsistency and hygiene bugs

- Two divergent `decode_kmer` implementations: `src/kmer/encoding.rs:99` decodes MSB-first, while `src/cli/commands/count.rs` carries an LSB-first-then-reverse copy; text and binary output of the same command use different decoders, and only the MSB-first one is unit-tested.
- k validation messages disagree: `src/cli/args.rs:505-507` rejects `k > 127` ("between 1 and 127") while `execute_count` (`count.rs:56-59`) rejects `k > 64`. 127 is unreachable (`u128` supports k ≤ 64).
- Merge overflow policy is inconsistent: `KmerCounter::merge` errors (`table.rs:407`); `merge_databases_inmemory` uses `saturating_add` (`format.rs:837`); `StreamingMergeIterator::next` uses `saturating_add` (`streaming_merge.rs:372`); `merge_single_prefix_hashmap` uses plain `+=` (`prefix_cache_merge.rs:478`) which **wraps silently in release** (no `overflow-checks` override) and panics in debug. Same input, different results per path.
- `count.rs:742-746` prints `"DEBUG: Writing header with data_offset: {}"` to stderr in normal (non-quiet) operation — debug noise on the user-facing path.
- `KmerCounterBuilder::max_count` (`src/hash/table.rs:467-470`) is stored but `build()` (`table.rs:476-480`) ignores it; `KmerCounter::new` always sets `max_count: u32::MAX`. A caller setting a lower cap gets default behaviour.
- One Chinese comment remains: `// 检查内存使用` at `prefix_cache_merge.rs:449` (comments are exempt from the CJK gate by design). Merge logs also use emoji (`🚀`, `📦`, `✅`, `❌`, `📊`), which render inconsistently and complicate log grepping.

---

## Security Considerations

### [S2] Unvalidated `total_kmers` in headers drives unbounded allocation

- Risk: `RKDatabase::from_file_path` (`format.rs:326`), `DatabaseQuery::load_entries` (`query.rs:97`), and `DatabaseStreamIterator` (`streaming_merge.rs:88`) all do `Vec::with_capacity(header.total_kmers as usize)` from an **attacker-controlled 8-byte field**, with no cross-check against actual file length. A 42-byte file declaring `total_kmers = 2^60` forces a ~100 EB `with_capacity` attempt.
- Current mitigation: `DatabaseHeader::validate()` checks magic/version/kmer_size/data_offset (`format.rs:166-191`) — but **not** `total_kmers` vs file size, and `from_file_path` never calls `validate()` (it only checks `data_offset != 42` inline).
- Recommendations: validate `(file_len - 42) / 20 >= total_kmers` before allocating; use `try_reserve` and map failure to a clean error.

### [S2] Predictable temp filenames in a shared, world-writable directory

- Risk: see the append/exposure bug above. Two distinct angles:
  - **Symlink attack (CWE-59/CWE-377):** `File::create`/`OpenOptions::append` follow symlinks. On a multi-user host, another local user can pre-create `ext_sort_ACGT_file_000.tmp` as a symlink and cause the merge to append attacker-chosen content or truncate an arbitrary writable file.
  - **Data exposure:** merged k-mer databases (potentially whole genomes) are written into `/tmp` with default permissions and retained (see leaked-output bug).
- Recommendations: `tempfile::TempDir` or `O_EXCL` creation inside a `0700` process-unique subdir.

### [S3] Unvalidated `String` mutation via `as_bytes_mut()` in the benchmark command

- Risk: `src/cli/commands/benchmark.rs:512-517`:
  ```rust
  unsafe {
      let bytes = query.as_bytes_mut();
      bytes[pos] = b'N';
  }
  ```
  `String::as_bytes_mut` is unsound if the written bytes break the UTF-8 invariant; here `'N'` is ASCII so it is safe today, but there is **no `SAFETY` comment** and the pattern breaks if the replacement byte ever changes.
- Recommendation: rebuild safely (`let mut bytes = query.into_bytes(); bytes[pos] = b'N'; String::from_utf8(bytes)?`). Enable `clippy::undocumented_unsafe_blocks`.

### [S3] Unsound-by-contract env var mutation from a library

- Risk: `ConfigManager::set_env_var` / `remove_env_var` (`src/config/manager.rs:491-499`) call `unsafe { env::set_var(...) }`. Mutating the process environment is unsafe under Rust 2024 rules because it races with any concurrent `env::var` read; this is reachable from library consumers of `rustkmer::config`.
- Compounding: `resolve_thread_count` (`src/cli/commands/count.rs`) reads `RUSTKMER_THREADS` via `env::var` in the same process where `ConfigManager` may write it.
- Recommendation: pass configuration explicitly; if env must be used, funnel all access through one lock and document single-threaded setup.

### [S3] Memory-mapped I/O without safety justification

- Risk: `unsafe { MmapOptions::new().map(&file)? }` at `src/io/mmap.rs:28` and `src/memory/efficiency.rs:182`, and `map_mut` at `src/memory/efficiency.rs:228`, map files that another process could modify concurrently (UB for the borrowed slice). No `// SAFETY:` comments.
- Recommendation: document the read-only/no-external-mutation invariant or advisory-lock; for `map_mut`, document the exclusive-write requirement.

### [S4] CJK gate exempts `src/cli/**` and all comments

- Issue: `tests/cjk_check.rs` exempts `src/cli/**` ("CLI output is out of FOUND-04 scope") and skips comments; every string a user actually sees comes from `eprintln!` in `src/cli/commands/*.rs`. One Chinese comment slipped through by design.
- Recommendation: extend the gate to CLI string literals, or record the exemption as an explicit, permanent policy.

### [S4] CI never executes the Python test suite

- Issue: `.github/workflows/ci.yml` runs `rustfmt`, `cargo clippy --all-targets -D warnings`, `cargo test`, `maturin build`, and uploads wheels — but **no `pytest` step**. The six `pyo3/tests/test_*.py` modules (~168 test functions) are never run, `--cov-fail-under=80` in `pyo3/pyproject.toml:100` is never enforced, and the `PyCounter` N-stripping divergence above is exactly what they would catch.
- Recommendation: add a `maturin develop` (or `maturin build` + `pip install`) + `pytest` job to `ci.yml`.

### [S4] Performance-regression workflow never fires on the development branch

- Issue: `performance-regression.yml` triggers on `[main, develop, 012-python-bindings-complete]`; `ci.yml` uses `[dev, main]`. `develop` does not exist. Combined with the no-op benchmark probing (see Tech Debt), no performance gate is actually running.

---

## Performance Bottlenecks

### [S1] `stats` performs a full TDigest merge per k-mer — O(n × compression)

- Problem: `StreamingStatsProcessor::add_count` (`src/database/stats.rs:195`):
  ```rust
  self.tdigest = self.tdigest.merge_unsorted(vec![count as f64]);
  ```
  One `Vec` allocation **and one whole-digest merge** per k-mer read. `TDigest::merge_unsorted` re-ingests and re-compresses the entire digest, so cost is O(compression) per input value, not O(1).
- Impact: at ~1,000 centroids this is ~10³ operations per k-mer. For a 10M-k-mer `.rkdb` that is ~10¹⁰ operations — minutes-to-hours for a seconds-long scan; at human scale it is not finishable. `rustkmer stats` is effectively unusable on real databases.
- Files: `src/database/stats.rs:195`
- Fix approach: batch inserts (accumulate 8–64k counts, one `merge_unsorted` per batch) or use the exact histogram median that is already computed (`stats.rs:198-201`).

### [S2] O(n²) `Vec::remove(0)` in the prefix-cache streaming merge

- Problem: `prefix_cache_merge.rs:615` — `file_states[top.file_idx].2.remove(0)` shifts the whole batch for every popped entry. With `BATCH_BYTES = 4_000_000` (~200k entries) per batch, that is ~4 MB of memmove per pop.
- Fix approach: `VecDeque` + `pop_front`, or a cursor index.

### [S2] Merge re-reads and re-deserializes every input 3–5×

- Problem: see "Every input `.rkdb` is fully deserialized 3–5× per merge" above. Merge wall-clock is dominated by redundant I/O, not the merge itself.
- Fix approach: header-only reads for sizing/validation.

### [S2] Text-format count output decodes every k-mer on every sort comparison

- Problem: `output_text_format` (`src/cli/commands/count.rs:660-668`) sorts with `sort_by` and calls `decode_kmer` for **both** operands inside the comparator — O(n log n) string allocations. The binary output path correctly uses `sort_by_key(|(a, _)| *a)` on the packed integer (`count.rs:711`). Since `--sort` is now default-on (Phase 2 D-09), every text `count` pays this.
- Impact: for 100M unique k-mers this is tens of GB of allocator churn and multi-minute sorts.
- Fix approach: sort by the packed encoding (same ordering does not hold for sequences vs integers across width changes — decode once into a `Vec<(String, u32)>` or an index permutation), or make the text path sort by integer encoding and decode only at write time.

### [S3] Chunked record buffering holds full `Record` objects

- Issue: `count.rs` buffers up to `CHUNK_SIZE = 4096` owned `bio::io::fastq::Record` / `fasta::Record` values, each owning `Vec<u8>` id/desc/seq/qual (~4 KB/record for 150 bp FASTQ). Bounded but churny; the code comment itself defers the sweep to Phase 4.
- Related: the pyo3 FASTA path accumulates an entire record into `current_seq` (`pyo3/src/counter.rs:740`), so a chromosome-scale FASTA record becomes one 250 MB `Vec<u8>`; the pyo3 FASTQ path allocates a fresh `Vec<u8>` per read (`counter.rs:797-801`).
- Fix approach: sweep `CHUNK_SIZE` in Phase 4; reuse buffers in the pyo3 paths.

### [S3] `prefix-query` copies the whole database before searching

- Issue: `extract_hybrid_by_pattern` (`src/database/prefix_query_optimized.rs:258-263`) copies `database.entries` into a `Vec<(u128, u32)>` (32 B/entry) before doing anything, while the caller has already loaded the full database via `from_file_path`. Peak ≈ 2× database size for a range scan.
- Fix approach: binary-search `&[KmerEntry]` directly or mmap/search in place.

### [S3] Single-threaded decompression is the counting bottleneck (D-02)

- Status: deliberate per D-02, but measurable. The producer loop in `process_fasta_file` / `process_fastq_file` reads/decompresses serially into a bounded chunk, then hands off to rayon; on gzip input all other cores idle during the read half of each cycle.
- Additional gap: the pyo3 paths (`pyo3/src/counter.rs:690-710`, `:753-790`) release the GIL (`py.detach`) but have **no rayon chunking at all** — they run entirely on one thread, so ROADMAP Phase 2 criterion 3 ("PyCounter delivers the same parallel speedup as the CLI") is only partially met.
- Fix approach (v2): parallel inflate or an I/O/CPU ring buffer. Phase 4 must measure decompression separately or the Jellyfish2 comparison is unfair in rustkmer's favour.

### [S4] `KmerCounterBuilder::max_count` is silently ignored

- Issue: see hygiene bugs above (`src/hash/table.rs:467-480`). Callers setting a lower cap get `u32::MAX` behaviour.
- Fix approach: thread the value through `new`, or delete the builder method.

---

## Fragile Areas

### `merge_databases_prefix_cache` / `ExternalSortMerger` — highest fragility

- Files: `src/database/format.rs:904-953`, `src/database/prefix_cache_merge.rs` (983 lines)
- Why fragile: five compounding issues in one path — unbounded input loads, append-mode non-unique temp files, error-swallowing (`Ok(())` on `error_count > 0`), the heap-refill data-loss branch, and `.expect()` inside a rayon worker. Test coverage is limited to `ExternalSortMerger::new` returning `Err` and a temp-dir existence assertion — no test drives `external_sort_merge` end to end.
- Safe modification: Phase 3 plan 03-02 touches this module; fix append/truncate, return `Err` on errors, and add an end-to-end ≥2-input forced-multi-chunk test. Centralize `RECORD_SIZE = 20` (currently open-coded at `:475-477`, `:664-665`, `:698-699`, `:940-941`, plus sizing math).

### `merge_databases_inmemory`

- Files: `src/database/format.rs:766-901`
- Why fragile: `#[allow(unused_assignments)]` at `format.rs:788-791` declares `kmer_size`/`canonical` as `None` then overwrites them; `format.rs:856-857` unwraps them. An early return added later compiles cleanly and panics at runtime. `sorted_kmers` is built while `all_kmers` is still live (`format.rs:875-887`) → ~2× peak.
- Safe modification: Phase 3 D-02 keeps this path behind `--merge-mode memory` with over-budget rejection; refactor the Option dance into a direct `let (kmer_size, canonical) = validate(...)?`.
- Test coverage: reasonable for small fixtures (`test_merge_with_config`, `test_merge_memory_basic`).

### `merge_databases_streaming`

- Files: `src/database/format.rs:710-764`, `src/database/streaming_merge.rs`
- Why fragile: it looks like the safe path (chunks + external sort + heap) but materializes the full output anyway (see Tech Debt). Anyone reading `streaming_merge.rs` in isolation concludes the merge is bounded.
- Test coverage: effectively **zero** — `test_merge_streaming_basic` sets `use_streaming: true`, which `merge_databases` ignores, and `should_use_streaming` returns `false` for its tiny fixture, so it exercises the in-memory path. Fix and test before Phase 3 flips defaults.

### `KmerCounter::merge` — documented unsafety under concurrency

- Files: `src/hash/table.rs:319-410`
- Why fragile: `merge` takes `&self`, so the compiler permits concurrent calls, but the doc comment states it **must not** run concurrently with `increment` or another `merge` (WR-04). The atomics are published incrementally, so a concurrent `increment` transiently under-reports `total_kmers`; overflow mid-loop leaves the counter poisoned/partially mutated (WR-02). None of this is enforced by types.
- Safe modification: wrap in an external mutex before merging into a live counter; consider `&mut self` or a `MergeGuard`.
- Test coverage: the WR-02 poisoning invariant is tested (`test_merge_overflow_poisons_consistently`); WR-04 concurrency is documented but untested.

### `config` module — global env mutation and order-dependent tests

- Files: `src/config/manager.rs` (722 lines)
- Why fragile: 6 `unsafe { env::set_var / remove_var }` call sites (plus test call sites), a global collector in `src/core/monitoring.rs:367` (`let _ = GLOBAL_COLLECTOR.set(...)`), and tests that mutate process env (`manager.rs:606-623`) — config tests are order-dependent and race with any parallel test reading `RUSTKMER_*`.
- Test coverage: `test_env_overrides` mutates global state and can flake under higher `--test-threads`.

### `.rkdb` header validation is triplicated

- Files: `src/database/format.rs:298-310` (`from_file_path`), `src/database/query.rs:77-85` (`load_entries`), `src/database/streaming_merge.rs:50-60` (`DatabaseStreamIterator::new`)
- Why fragile: three hand-rolled copies of the same `data_offset != 42` check with three separately-worded errors; `from_file_path` never calls `DatabaseHeader::validate()`; a fourth writer (`count.rs::output_binary_format`) hardcodes `data_offset: 42` inline.
- Safe modification: route every reader through `header.validate()`; keep one message string.

### Legacy/backup artifacts still in the tree

- Files: `pyo3/src/*.stage1_fix_backup` (3 files), `pyo3/src/database_backup.rs`, `pyo3/src/database_new_approaches.rs`, `src/database/merge_tests.rs` (orphaned), `tests/007-api-compatibility/` (stale README/pytest.ini/reports referencing a `compatibility_framework/` that does not exist), `tests/converted/` (README + pytest.ini only, referencing a `python/` dir that does not exist), `fresh_test.py`, `precise_analysis.py` at repo root.
- Why fragile: git-tracked, so they appear in every grep, inflate apparent codebase size by ~20%, and `tests/cjk_check.rs` already needs a hardcoded exclusion list for them.

---

## Scaling Limits

### Distinct k-mers in `DashMap<u128, u32>` (count)

- Current capacity: effectively unbounded — nothing checks before inserting.
- Limit: per-entry cost. `DashMap<u128, u32>` shards into `(len * 4).next_power_of_two()` shards, each a `hashbrown::HashMap` with 20 B payload + control byte + ≤ 7/8 load factor → roughly **28–40 B per distinct k-mer amortized**, plus table slack. A human genome (~3 G distinct k-mers) needs **~90–120 GB** (PROJECT.md already cites "~100 GB+").
- Scaling path: Phase 3 D-03 (`u64` keys for k ≤ 32) halves it to ~45–60 GB. Beyond that nothing scales: no partitioning, no spill (the unwired `DiskOverflow` is `u64`-only), no minimizer scheme. KMC-class tools partition by minimizer precisely to avoid this.
- Note: `--size` defaults to `1_000_000` (`src/cli/args.rs:53`), preallocating a 1M-entry DashMap (~30 MB) even for a toy input.

### Merge peak RSS

- Current capacity: ~56 B per **distinct output** k-mer on the streaming path (32 B `Vec<(u128,u32)>` + 24 B `Vec<KmerEntry>` coexisting), similar on the in-memory path, plus 3–5× the input set from redundant loads.
- Limit: a 3 G-distinct-k-mer merge needs ~170 GB on the "streaming" path — the bounded path is currently the *worst* of the three.
- Scaling path: (a) incremental streaming write → O(chunk); (b) header-only reads → removes the 3–5× multiplier; (c) D-03 `u64` → halves what remains; (d) a genuinely bounded external-sort pipeline writing straight to the output `.rkdb` is the real answer.

### `u32` k-mer counts saturate/wrap at 4,294,967,295

- Current capacity: `KmerEntry.count` and `KmerCounter` values are `u32`. Counting saturates at `u32::MAX` with an error/warning in `KmerCounter::increment` (Phase 2 semantics), but `merge_databases_inmemory` silently saturates and `merge_single_prefix_hashmap` silently wraps in release.
- Limit: any k-mer appearing >4.29 B times loses precision or corrupts depending on the path.
- Scaling path: promote counts to `u64`, or emit one loud warning per run on saturation (SAT-01/SAT-02, deferred to v2).

### Text-sort memory on `count`

- Current capacity: `get_filtered_kmers` materializes all unique k-mers, then `output_text_format` sorts them with per-comparison decodes. For >100M k-mers this is multiple GB plus severe allocator churn.
- Scaling path: sort by packed integer, decode at write time; or stream a merge-sorted output as Phase 3 does for merge.

### Single-threaded decompression throughput

- Current capacity: one core's inflate rate (~100–250 MB/s gzip output). The CRR1936095 target (~5.2 GB gzipped → ~25 GB uncompressed) has the read half of the producer cycle on the critical path while N-1 cores idle; pyo3 paths are fully single-threaded.
- Scaling path: parallel inflate contexts over byte-range boundaries (deferred; Phase 4 must measure it).

### Wildcard / mutation query expansion

- Current capacity: `DEFAULT_MAX_VARIANTS = 10_000` (`src/fuzzy/mod.rs:76`), with a guard bypassed by `usize` overflow at ≥32 wildcards and by the `TODO` at `expansion.rs:176`.
- Limit: `expand_wildcards` recursion (`wildcard.rs:65-84`) rebuilds full `String`s per level — O(4ⁿ · n) allocations; `generate_mutation_combinations` (`mutation.rs:75-113`) is similarly exponential with a `HashSet<String>` accumulator.
- Scaling path: `checked_pow` + hard wildcard cap; iterative in-place generation; byte-vector representation.

---

## Dependencies at Risk

### No committed `Cargo.lock` (binary crate) — non-reproducible builds

- Risk: `.gitignore` excludes `Cargo.lock` and `pyo3/Cargo.lock`; no lockfile exists on disk. This is a **binary/CLI** crate (`[[bin]] name = "rustkmer"`), where the lockfile should be committed for reproducible builds and supply-chain audits. CI cache keys (`hashFiles('Cargo.lock')`, `hashFiles('pyo3/Cargo.lock')`) hash a missing file, collapsing all cache namespaces.
- Impact: every build resolves newest semver-compatible deps; a broken upstream release silently breaks the build; the "verified in RESEARCH" dependency claims (e.g. tempfile 3.24.0) cannot be reproduced.
- Mitigation: remove `Cargo.lock` from `.gitignore`, commit both lockfiles, and let CI cache on them.

### No Rust MSRV, Python version drift

- Risk: `Cargo.toml` has no `rust-version` key (CI uses `dtolnay/rust-toolchain@stable`, i.e. whatever is newest). `CLAUDE.md`/`AGENTS.md` say Python 3.8+/3.10+, `pyo3/pyproject.toml` requires `>=3.11`, classifiers list 3.11/3.12 only, `[tool.mypy].python_version = "3.11"`. Nothing enforces any of it.
- Impact: a rustc bump can silently break the build; a consumer on 3.10 gets a resolver failure with no in-repo signal.

### `bio` 2.0 — `Record` ownership forces duplicated reader code

- Risk: `process_fasta_file`/`process_fastq_file` (`count.rs`) bypass `FastaProcessor::process_file`/`FastqProcessor::process_file` because those take `FnMut(&Record)` with a borrow tied to the reader iterator — the doc comment calls this "a known integration issue". The bypasses duplicate reader setup, compression detection, and error strings already owned by `src/io/fasta.rs` / `src/io/fastq.rs`; they have already drifted once (the fixed `.fa.gz` WR-01 bug).
- Mitigation: move the chunk-buffered reader into `src/io/` as the canonical API and make the processors thin wrappers.

### `flate2` / `bzip2` / `xz2` — hand-rolled compression detection

- Risk: `niffler` is commented out (`Cargo.toml:73`) over "zstd issues", so `.zst` input is unsupported and compression detection is by extension only (`CompressionType::from_path`, `src/io/fastq.rs:24-37`). A `.fastq.zst` file falls through to raw-byte parsing and produces **silently garbage k-mers** — the same failure class as the already-fixed `.fa.gz` bug.
- Mitigation: sniff magic bytes (not extensions) at open time and error loudly on an unrecognized compressed stream.

### `tdigest` 0.2 — no incremental single-value path

- Risk: `tdigest` 0.2 has no `add(f64)`; the only insertion path is a whole-digest merge, which forces the O(n × compression) behavior at `stats.rs:195`. Any future use of `tdigest` will hit the same trap.
- Mitigation: batch inserts; or use the exact histogram already maintained.

### `hashbrown` 0.14 / `dashmap` 6.2.1 — deliberate version pin

- Risk: low. `dashmap 6.2.1` pins `hashbrown ^0.14.5`, matching the project's `hashbrown 0.14` so there is no duplicate-version bloat (documented at `Cargo.toml:58-61`). Phase 3 D-03 must preserve this when swapping the key type to `u64`.

### `pyo3` 0.27.2 — deprecated-API shims and a stale ROADMAP note

- Risk: `pyo3/src/database.rs:7`, `fuzzy_query.rs:7`, and `prefix_query.rs:7` each carry module-wide `#![allow(deprecated)]`, hiding every deprecation warning in those files (10 deprecated `#[pymethods]` remain). `.planning/ROADMAP.md:76` still says "wrap in `pyo3::allow_threads` (0.27.2 API, NOT `detach`)" while the shipped code correctly uses `Python::detach` — a future agent could "fix" working code back to the deprecated API.
- Mitigation: scope the `allow(deprecated)` to the specific methods and reconcile the ROADMAP text.

### `sys-info` 0.9 — advisory-only memory checks

- Risk: used only in `prefix_cache_merge.rs` for warning-level logging (`:427`, `:451`, `:499`, `:720`, `:764`); it does not gate any allocation. A failure to read system memory silently skips the warnings. The crate is old and unmaintained; `get_default_memory_limit()` reads `/proc/meminfo` directly on Linux with a 32 GB fallback elsewhere.
- Mitigation: if memory admission control becomes real in Phase 3, use a maintained source and treat the read as a hard input to routing.

---

## Missing Critical Features

### No bounded-memory *counting* path

- Problem: counting is the flagship benchmarked path and has the largest absolute memory. There is no spill, no partition, and no minimizer scheme — the `DashMap` grows without limit. `DiskOverflow` exists but is unwired **and** `u64`-only, so it could not even attach to the current `u128` counter.
- Blocks: the milestone's core-value claim ("within practical memory") for `count` at human scale. Phase 3 D-03 halves memory but does not bound it.

### No memory admission control on `count`

- Problem: `count` takes `--size` (initial capacity) but nothing estimates final memory or warns/refuses as it approaches a budget. A user gets an OOM kill with no diagnostic.
- Blocks: MERGE-02's equivalent for counting; makes Phase 4 memory measurements hard to interpret.

### No disk-space preflight for merge

- Problem: streaming and prefix-cache paths write one or more full-size copies of the input to `temp_dir` with no available-space check. A merge needing 60 GB of scratch on a 2 GB `/tmp` fails partway through with raw ENOSPC after doing all the work — and the orphaned shards then make the next attempt worse.
- Blocks: MERGE-03's "prevents silent disk exhaustion".

### No resumable or interruptible merge

- Problem: explicitly deferred to v2 in 03-CONTEXT. Noted because `panic = "abort"` means even a correct RAII guard does not run on abort/`SIGKILL`; the subdir + startup sweep only prevents accumulation across runs, not mid-run loss.

### `PyDatabase.merge` exposes neither `max_memory` nor `merge_mode`, and holds the GIL

- Problem: `pyo3/src/database.rs:1348` is `fn merge(databases: Vec<String>, output: String)` with `#[pyo3(signature = (databases, output))]` and hardcoded `MergeConfig::default()`. It also **does not release the GIL**, so a long merge freezes the entire Python interpreter, including other threads.
- Blocks: ROADMAP Phase 3 success criterion 6 / MERGE-04. Plan 03-05 covers kwargs; the GIL release is not mentioned and should be added.

### `--max-memory` is documented but not enforced against reality

- Problem: `parse_memory_size` (`merge.rs`) accepts up to 1 TB and feeds `config.max_memory_usage`, which is only ever compared to `total_kmers * 24`. There is no check against actual available memory, and the in-memory path has no hard cap (Phase 3 D-01/D-02 fixes the latter).

---

## Test Coverage Gaps

| Area | What's not tested | Files | Risk | Priority |
|---|---|---|---|---|
| Streaming merge | **Effectively zero.** `test_merge_streaming_basic` sets `use_streaming: true`, which `merge_databases` ignores; `should_use_streaming` returns false for its tiny fixture, so it runs the in-memory path. No test creates >1 chunk, so the k-way heap, temp-file lifecycle, and full-result accumulation are unexercised. | `src/database/format.rs:1105-1155`, `src/database/streaming_merge.rs:435-495` | Phase 3 makes this the default merge path with zero coverage | **High** |
| Prefix-cache merge | Only `ExternalSortMerger::new` error path and a temp-dir existence assertion. Nothing drives `external_sort_merge` end to end — the append/truncate bug, `error_count` swallow, tail-drop, and reader `Err(_) => break` are all invisible. | `src/database/prefix_cache_merge.rs:955-976` | Silent data loss + concurrency corruption | **High** |
| Large counts (>1M) | No fixture anywhere has `count > 1_000_000`; the endianness heuristic is invisible. | all fixtures under `tests/fixtures/` | S1 silent count corruption | **High** |
| CLI ↔ Python parity | No differential test between `rustkmer count` and `PyCounter` output on N-containing input. | `tests/parallel_count_tests.rs` (Rust-only), `pyo3/tests/` (never run in CI) | N-stripping divergence ships undetected | **High** |
| Python suite in CI | `pyo3/tests/*.py` (6 modules, ~168 tests) never executed by CI; `--cov-fail-under=80` unenforced. | `.github/workflows/ci.yml` | Entire Python surface unguarded | **High** |
| Orphaned `merge_tests.rs` | Never compiled (`mod` missing); false coverage signal. | `src/database/merge_tests.rs`, `src/database/mod.rs` | Reader believes merge memory behavior is covered | Medium |
| Merge temp-file cleanup | No test asserts shards/temp output are removed after success or failure. | `streaming_merge.rs`, `prefix_cache_merge.rs`, `format.rs:944` | Disk exhaustion | Medium |
| `stats` at scale | No test beyond a handful of k-mers; the O(n·compression) TDigest never shows. Also 0 unit tests in `src/database/stats.rs` and `src/cli/commands/stats.rs`. | `src/database/stats.rs`, `tests/unit/stats_tests.rs` | `stats` unusable on real data | Medium |
| `dump` entry count | No test asserts the reported entry count for k ≤ 32. | `src/cli/commands/dump.rs:138-145` | Wrong entry-size math | Medium |
| Malformed `.rkdb` headers | No test with a lying `total_kmers`, truncated file, or oversized `data_offset` beyond the `!= 42` checks. | `src/database/format.rs`, `src/database/query.rs` | Allocation DoS; silent truncation | Medium |
| Fuzzy expansion limits | No test with ≥32 wildcards or near the overflow boundary; `expansion.rs:176` TODO guard never accounts for wildcards. | `src/fuzzy/wildcard.rs`, `src/fuzzy/expansion.rs` | DoS | Medium |
| CLI command modules | `src/cli/commands/benchmark.rs` (705 lines), `stats.rs` (435), `fuzzy.rs` (692) have zero unit tests. | `src/cli/commands/` | Regressions in stats/benchmark paths | Medium |
| Dead-module tests | `src/output/text.rs` / `binary.rs` tests exercise code no command calls; they create a false sense of output-format coverage. | `src/output/` | Misleading signal | Low |
| `profiling` feature | Never compiled in CI (no `--features profiling`); cannot know if it builds. | `src/core/monitoring.rs` (474 lines) | Rot | Low |
| Memory bounds | `MemoryConstraint`/`MemoryMonitor` asserted only on tiny fixtures; no test asserts any RSS ceiling for count or merge. | `src/database/memory.rs`, `tests/common/memory.rs` | The milestone's central claim is unmeasured | Medium |

---

## Quick Wins (low risk, high value)

1. **Delete the endianness heuristic** at `src/database/format.rs:231`. One-line change; removes the only S1 silent-corruption bug. Add a round-trip test at `count = 1_000_001` and route `prefix_cache_merge.rs` readers through the same decoder.
2. **Preserve non-ACGT bytes in the pyo3 readers** (`pyo3/src/counter.rs:284`, `:740`, `:800`) so they match the CLI, and fix the contradicted docstring at `:264-265`.
3. **Add a header-only reader** and use it in `merge_databases`, `should_use_streaming`, and `execute_merge`; delete the duplicated validation loop at `src/cli/commands/merge.rs:241`.
4. **Return `Err` when `error_count > 0`** in `merge_prefix_buckets` (`prefix_cache_merge.rs:379-403`), and propagate `Err(_) => break` in `read_batch_from_file_sync`.
5. **Truncate (not append) bucket shards** and move them into a process-unique subdir (`prefix_cache_merge.rs:232-236`).
6. **Batch the TDigest insert** at `src/database/stats.rs:195` — or drop the TDigest and use the histogram's exact median.
7. **Add a pytest step** to `.github/workflows/ci.yml` and fix the docs.yml/perf-regression.yml dangling references.
8. **Commit `Cargo.lock`** (remove from `.gitignore`) so builds and CI caches are reproducible.
9. **Delete the dead modules/artifacts**: `src/output/`, `src/hash/overflow.rs`, `src/hash/matrix.rs`, `src/database/index.rs`, `src/database/suffix_query.rs`, `src/database/merge_error.rs`, `src/database/prefix_query.rs`, `src/core/database/persistence.rs`, `pyo3/src/*.stage1_fix_backup`, `pyo3/src/database_backup.rs`, `pyo3/src/database_new_approaches.rs`, `src/database/merge_tests.rs`, committed `.coverage` files, and the root scratch scripts. ~6,500 lines total.
10. **Replace `as_bytes_mut()`** at `src/cli/commands/benchmark.rs:514` with a safe reconstruction; reconcile the ROADMAP's stale `allow_threads`-vs-`detach` text; add `SAFETY` comments to the mmap/env `unsafe` sites.

---

## Related Planning Artifacts

- `.planning/phases/03-memory-safety/03-CONTEXT.md` — decisions D-01…D-06 already cover merge routing/estimator (D-01/D-02), `u64` dense keys (D-03/D-04/D-05), and RAII temp guards + process-unique subdir + startup sweep (D-06). **Not covered there:** the streaming path's full-result materialization, the 3–5× redundant input loads, the `error_count` swallow, the heap-refill data loss, the always-worse-than-in-memory prefix-cache profile, and `PyDatabase.merge`'s missing GIL release.
- `.planning/PROJECT.md` — "Out of Scope" names committed backup files, dead PyO3 modules, and the orphaned `merge_tests.rs` as tracked-but-deferred tech debt. This document confirms and quantifies them.
- `.planning/HANDOFF.json` — records the open human-verification item for Phase 2 WR-01 (`total_kmers` denominator semantics on saturating inputs, commit `a545a2d`).

---

*Concerns audit: 2026-10-07*
