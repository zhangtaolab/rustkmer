---
phase: 03-memory-safety
plan: 02
subsystem: database
tags: [rust, tempfile, raii, temp-files, disk-exhaustion, cleanup, prefix-cache-merge]

requires:
  - phase: 03-memory-safety
    plan: 01
    provides: "RKDatabase::merge_databases as the single admission-control + dispatch point (header-only estimator, hard route to streaming); TempFileManager RAII in streaming_merge.rs as the pattern to mirror"
  - phase: 01-foundation-quality
    provides: "log:: facade + clippy -D warnings gate (FOUND-01/02); committed golden .rkdb fixtures"
provides:
  - "tempfile::TempDir RAII for every merge: all prefix-cache shards live under a process-unique rustkmer-merge-<rand>/ subdir removed on any unwind"
  - "temp_lifecycle::sweep_stale_merge_dirs — the real defense against panic=abort / SIGKILL / power loss, where Drop never runs (D-06)"
  - "sweep wired once at the top of RKDatabase::merge_databases, covering all three merge strategies"
  - "RECORD_SIZE const + read_record_at helper in prefix_cache_merge.rs — 16 bare try_into().unwrap() sites collapse to one point of truth"
  - "tests/merge_cleanup_tests.rs — 6 GREEN MERGE-03 tests, 0 ignored"
affects: [03-03, 03-04, 03-05, phase-04-benchmark]

actuals:
  tokens: 10845
  tasks: 2
  commits: 2

tech-stack:
  added:
    - "tempfile 3.12 (PROMOTED dev-dependency -> [dependencies]; no new crate, same vetted version)"
  patterns:
    - "RAII-plus-sweep: Drop covers the unwind cases, an age-TTL sweep covers the cases where Drop never runs — neither alone closes MERGE-03"
    - "Process-unique subdir via tempfile::Builder::prefix().rand_bytes(8), not PID: random bytes also survive PID reuse after a reboot"

key-files:
  created:
    - src/database/temp_lifecycle.rs
    - tests/merge_cleanup_tests.rs
  modified:
    - src/database/prefix_cache_merge.rs
    - src/database/format.rs
    - src/database/mod.rs
    - Cargo.toml
    - .planning/phases/03-memory-safety/deferred-items.md

key-decisions:
  - "The per-bucket best-effort delete was KEPT but de-gated from `result.is_ok() &&` rather than deleted outright. It is a peak-disk optimization, not the cleanup guarantee; removing it entirely would have made a long merge retain every bucket's shards until the end, a disk-usage regression the original code avoided. Drop is the guarantee; this is the belt-and-suspenders. The plan's acceptance criterion (`if result.is_ok() && !self.keep_intermediate` is gone) still holds."
  - "The sweep's single call site is the top of RKDatabase::merge_databases (format.rs), not ExternalSortMerger::new — the plan's key_links asked for exactly one site in the shared dispatch, and this placement also covers the streaming and in-memory strategies"
  - "The sweep refuses to recurse into symlinks carrying our prefix (entry.file_type(), not entry.metadata()) — a symlink in a shared temp_dir could otherwise redirect remove_dir_all at an arbitrary tree (T-03-07 made worse, not better)"
  - "The prefix literal is hoisted to `pub const MERGE_TEMP_PREFIX` and the sweep compares against the const rather than re-spelling \"rustkmer-merge-\". The two sites must agree or orphan cleanup silently stops working, so the const is the single source of truth."
  - "No signal handler and no resumable merge (D-06 defers both to v2): a failed merge is a clean restart"
  - "Two out-of-scope pre-existing bugs on the prefix-cache path were logged to deferred-items.md rather than fixed, per the scope boundary: the un-deleted external_sort_merge_output.tmp, and merge_prefix_buckets returning Ok(()) after bucket failures (silent partial merge)"

patterns-established:
  - "RED discipline across plans: plan 03-02 Task 1 commits the ignored stubs against the pre-change API; Task 2 captures RED twice (an assertion failure for the stubbed sweep, then a compile error for the missing RAII API) before writing the implementation"
  - "Age a directory in a test with std::fs::File::set_times (stable since Rust 1.75) rather than adding a filetime dev-dependency or reaching for the still-unstable std::fs::set_modified"
  - "Two-layer cleanup with distinct jobs: an explicit tracked-path remove_file loop (precise, reports nothing) plus a TempDir close() (catches anything never tracked, and close() surfaces the error that Drop would swallow)"

requirements-completed: [MERGE-03]

coverage:
  - id: D1
    description: "The prefix-cache merge removes its temp shards on any non-aborting exit (normal return, early ? return, panic=unwind) — not only on the success branch"
    requirement: MERGE-03
    verification:
      - kind: integration
        ref: "tests/merge_cleanup_tests.rs#cleanup_runs_on_panic_unwind"
        status: pass
      - kind: integration
        ref: "tests/merge_cleanup_tests.rs#successful_merge_leaves_no_shards"
        status: pass
    human_judgment: false
  - id: D2
    description: "All temp shards for a merge live under a process-unique subdir created via tempfile::Builder::new().prefix(\"rustkmer-merge-\").rand_bytes(8).tempdir_in(&config.temp_dir)"
    requirement: MERGE-03
    verification:
      - kind: integration
        ref: "tests/merge_cleanup_tests.rs#subdir_is_process_unique"
        status: pass
      - kind: integration
        ref: "tests/merge_cleanup_tests.rs#two_concurrent_merges_do_not_collide"
        status: pass
    human_judgment: false
  - id: D3
    description: "sweep_stale_merge_dirs removes orphaned rustkmer-merge-* dirs older than the TTL, logs each removal, and swallows its own errors so it can never abort a merge; a live (in-flight) subdir is left untouched"
    requirement: MERGE-03
    verification:
      - kind: integration
        ref: "tests/merge_cleanup_tests.rs#orphan_subdir_swept_on_next_start"
        status: pass
    human_judgment: false
  - id: D4
    description: "The sweep is actually reached from the shared merge dispatch, not merely implemented"
    requirement: MERGE-03
    verification:
      - kind: integration
        ref: "tests/merge_cleanup_tests.rs#merge_databases_sweeps_stale_orphans"
        status: pass
    human_judgment: false
  - id: D5
    description: "tempfile is in [dependencies] so production code in src/database/ can use tempfile::TempDir (03-RESEARCH.md Pitfall 6)"
    requirement: MERGE-03
    verification:
      - kind: other
        ref: "cargo build --release"
        status: pass
      - kind: other
        ref: "cargo clippy --all-targets -- -D warnings"
        status: pass
    human_judgment: false
  - id: D6
    description: "const RECORD_SIZE: usize = 20 is hoisted and the byte-slice conversion sites route through one read_record_at helper instead of eight bare try_into().unwrap() assumptions (CONCERNS fragile-area fix)"
    requirement: MERGE-03
    verification:
      - kind: other
        ref: "grep -cE 'try_into\\(\\).unwrap\\(\\)' src/database/prefix_cache_merge.rs (16 -> 2, both inside read_record_at)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Cleanup under panic=\"abort\" / SIGKILL / power loss, where Drop does not run at all"
    requirement: MERGE-03
    verification: []
    human_judgment: true
    rationale: "Not testable from cargo test: the test harness requires panic=unwind, and a process that aborts cannot assert anything afterward. The release profile's panic=\"abort\" is exactly why sweep_stale_merge_dirs exists, and it is covered by proxy (orphan_subdir_swept_on_next_start + merge_databases_sweeps_stale_orphans assert that whatever an abort left behind is reclaimed on the next merge). A human must confirm the end-to-end behavior by SIGKILLing a real large merge and watching the next run reclaim the directory."
  - id: D8
    description: "No regression to the existing merge paths, the golden .rkdb fixtures, or the 03-01 routing work"
    requirement: MERGE-03
    verification:
      - kind: other
        ref: "cargo test (217 lib + 26 merge_cleanup + 25 merge_routing + 34 golden + 23 round_trip + 20 mod + 8 property, 0 failures)"
        status: pass
      - kind: other
        ref: "cargo test --lib"
        status: pass
    human_judgment: false

commits: 4
plan_head_before: b4ebc88f135dfcc0e3178a105ec9e89d8f7b36d0
plan_head_after: d493bfb4a0e2ff5e0d9d5aa9b48cf0dc8e2d9a3d

duration: 38min
completed: 2026-10-07
status: complete
---

# Phase 3 Plan 2: Merge Temp-File Lifecycle (RAII + Orphan Sweep) Summary

**A merge that dies no longer takes its temporary shards with it: every merge now owns a process-unique `rustkmer-merge-<rand>/` subdir cleaned up by RAII, and whatever an aborted process could not clean up is reclaimed by a 7-day-TTL sweep on the next merge — closing the disk-exhaustion vector MERGE-03 was written about.**

## Performance

- **Duration:** 38 min
- **Started:** 2026-10-07T03:05:00Z
- **Completed:** 2026-10-07T03:43:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- **The gap is closed.** `prefix_cache_merge.rs` removed its shards only on the `result.is_ok()` branch, so an early `?` return, a logic-error panic, or any interruption leaked all 256 bucket shards per input file. `ExternalSortMerger` now implements `Drop` (mirroring `streaming_merge.rs::TempFileManager::Drop`), so cleanup happens on *every* unwind path.
- **Every merge owns a process-unique subdir.** All shard writes resolve through `shard_dir()` → the `tempfile::TempDir` created by `create_merge_temp_subdir`. Concurrency safety comes from `rand_bytes(8)`, not from the PID — so a restarted process reusing a PID cannot resurrect a name.
- **The startup sweep is implemented and actually wired.** `sweep_stale_merge_dirs` is called once at the top of `RKDatabase::merge_databases`, so all three merge strategies are covered by a single call site. It refuses symlinks, tolerates a missing `temp_dir`, and cannot itself fail a merge.
- **`RECORD_SIZE` hoisted.** 16 bare `try_into().unwrap()` byte-slice conversions collapsed to one `read_record_at` helper — the `.planning/codebase/CONCERNS.md` "Fragile Area" on this file is closed.
- **6 MERGE-03 integration tests, 0 ignored** (up from 4 `#[ignore]`d RED stubs), including two the plan did not ask for: `successful_merge_leaves_no_shards` and `merge_databases_sweeps_stale_orphans` (which proves the sweep is *reached*, not merely implemented).

## Task Commits

1. **Task 1: promote tempfile to [dependencies] + scaffold temp_lifecycle.rs + RED test stubs** — `e61c87a` (chore)
2. **Task 2: RAII mirror on prefix-cache + sweep body + RECORD_SIZE const (GREEN)** — `d493bfb` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified

- `src/database/temp_lifecycle.rs` (new) — `MERGE_TEMP_PREFIX`, `DEFAULT_MERGE_TEMP_TTL` (7 days), `create_merge_temp_subdir`, `sweep_stale_merge_dirs`
- `src/database/prefix_cache_merge.rs` — `TempDir` field + `shard_paths` + `merge_temp_subdir_path()` accessor + `shard_dir()`; `Drop` impl; success-only cleanup gate removed; `RECORD_SIZE` + `read_record_at`
- `src/database/format.rs` — one `sweep_stale_merge_dirs` call at the top of `merge_databases`
- `src/database/mod.rs` — `pub mod temp_lifecycle;`
- `Cargo.toml` — `tempfile = "3.12"` promoted to `[dependencies]`; `[profile.release]` untouched
- `tests/merge_cleanup_tests.rs` (new) — 6 MERGE-03 tests
- `.planning/phases/03-memory-safety/deferred-items.md` — 2 new out-of-scope findings

## Decisions Made

- **Kept the per-bucket delete, de-gated it instead of deleting it.** The plan said to remove the block outright. Removing it would have meant a long merge retains every bucket's shards until the very end — a real peak-disk regression the original code was avoiding. The block's `result.is_ok() &&` gate (the actual gap) is gone; what remains is an unconditional best-effort delete documented as a peak-disk optimization, with `Drop` carrying the guarantee. The plan's grep-based acceptance criterion still holds.
- **One sweep call site, in `merge_databases`.** The plan's `key_links` asked for exactly one, in the shared dispatch. Putting it there rather than in `ExternalSortMerger::new` also means the in-memory and streaming strategies get orphan reclamation for free.
- **`MERGE_TEMP_PREFIX` as a const.** Creation and sweeping must agree on the string or cleanup silently stops working; two hard-coded literals would be a future silent-breakage site.
- **The sweep refuses symlinks.** `entry.file_type()` rather than `entry.metadata()` — the latter follows symlinks, so a `rustkmer-merge-*` symlink planted in a shared temp dir could redirect `remove_dir_all` at an arbitrary tree. Threat T-03-07 ("another tool using our prefix gets swept") was accepted; making it able to delete an arbitrary *target* tree was not.
- **Aging a directory in tests uses `File::set_times`** (stable since Rust 1.75) rather than adding a `filetime` dev-dependency — one fewer dependency for one assertion.
- **No signal handler, no resumable merge** — D-06 defers both to v2. A failed merge is a clean restart.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] My own `two_concurrent_merges_do_not_collide` stub asserted against already-dropped `TempDir`s**
- **Found during:** Task 2 RED run (`cargo test --test merge_cleanup_tests`)
- **Issue:** The Task 1 stub created a subdir inside each spawned thread and returned only its path, so both `TempDir`s were dropped at the end of their closures. The post-join assertion `merge_subdirs(parent).len() == 2` saw 0. The test was structurally incapable of passing regardless of the implementation.
- **Fix:** Threads now return the `ExternalSortMerger` itself alongside its path, keeping the subdirs alive across the assertions; cleanup is then asserted explicitly after `drop`.
- **Files modified:** `tests/merge_cleanup_tests.rs`
- **Verification:** `two_concurrent_merges_do_not_collide` GREEN — distinct subdirs, both shards intact, both cleaned on drop.
- **Committed in:** `d493bfb`

**2. [Rule 1 - Bug] `orphan_subdir_swept_on_next_start` used a 1 ns TTL, which swept the "live" subdir it was asserting should survive**
- **Found during:** Task 2 GREEN run
- **Issue:** The stub paired a fresh subdir with a 1 ns TTL to avoid mtime manipulation. Once the sweep was implemented, that TTL correctly swept both the orphan *and* the fresh subdir — the test's own premise contradicted its assertion.
- **Fix:** Introduced a `backdate` helper (`File::set_times`) and switched to the production `DEFAULT_MERGE_TEMP_TTL`, so the test exercises the real production constant: orphan aged 7 days + 60 s → swept; freshly created subdir → survives.
- **Files modified:** `tests/merge_cleanup_tests.rs`
- **Verification:** GREEN against the real 7-day TTL, not a synthetic one.
- **Committed in:** `d493bfb`

---

**Total deviations:** 2 auto-fixed (both Rule 1, both in tests written by this plan)
**Impact on plan:** No production-code deviation. Both fixes were bugs in the plan's own RED stubs, surfaced by actually running them — which is the point of the TDD gate. The one *intentional* departure from the plan text (keeping the de-gated per-bucket delete) is documented above.

## Issues Encountered

- The plan's `<verify>` commands use `/Users/forrest/GitHub/rustkmer`; this executor runs on Linux at `/home/forrest/Github/rustkmer`. All commands were run with the path adapted — no behavioral difference (same as 03-01).
- `cargo` is not on the default `PATH` in this environment; `export PATH="$HOME/.cargo/bin:$PATH"` was needed for every invocation.
- A first attempt at a multi-typed-parameter closure in the concurrency test hit a rustc parse error; rewritten as a named `start_merger` fn, which is clearer regardless.
- Two out-of-scope pre-existing bugs were found while working in this file and logged to `deferred-items.md` rather than fixed (scope boundary):
  1. `external_sort_merge_output.tmp` is written to the *shared* `temp_dir`, outside the new subdir, and is never deleted — dataset-sized leak plus a fixed-name collision between concurrent merges (T-03-05 / T-03-06).
  2. `merge_prefix_buckets` returns `Ok(())` after logging bucket failures, so a partial merge is written out as a valid `.rkdb` — silent k-mer loss. 03-01 fixed two comparable bugs on the streaming path because it promotes that path to default; the prefix-cache path is not the default, so the urgency differs.
- `cargo fmt --check` still reports pre-existing drift in `src/cli/commands/count.rs`, `src/hash/table.rs`, and `tests/parallel_count_tests.rs` (carried from 03-01). All seven files this plan touched are rustfmt-clean.

## Known Stubs

None. All 6 tests in `tests/merge_cleanup_tests.rs` are GREEN with 0 `#[ignore]`d, and no placeholder, `todo!()`, or unwired data source remains in the plan's files. The 3 `#[ignore]`d tests in the repo (`golden_generate`, `parallel_count_tests`, one property test) are pre-existing run-once baseline generators from Phases 1–2.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **MERGE-03 is met for every path that `Drop` can reach, and defended-by-sweep for the paths it cannot.** The remaining human-judgment item is D7: a real SIGKILL'd human-scale merge, confirming the next run reclaims the directory. Nothing in CI can substitute.
- **`streaming_merge.rs` was deliberately not modified.** Its `TempFileManager` was the reference pattern and already has RAII. Note that its chunk files still land loose in `temp_dir` (`rustkmer_sort_<pid>_<micros>_<id>.chunk`) and are therefore NOT covered by the sweep — if a 03-01-hard-routed streaming merge is SIGKILL'd, its chunks are not reclaimed by `sweep_stale_merge_dirs`. That is a known, documented limitation of this plan's scope, and a strong candidate for a follow-up.
- **For downstream planners:** `temp_lifecycle` is `pub`. `merge_databases` now performs filesystem I/O in `config.temp_dir` on entry — a merge into a nonexistent `temp_dir` logs at debug and continues (it fails later, as before), so no new failure mode was introduced. `ExternalSortMerger::new` now returns `Err` if the temp subdir cannot be created.
- **The `mod common;` noise** (20 extra shared-helper tests per binary) now applies to `merge_cleanup_tests.rs` too, as it already did to `merge_routing_tests.rs`.

## Deferred Items

See `.planning/phases/03-memory-safety/deferred-items.md`:
- `external_sort_merge_output.tmp` written outside the process-unique subdir and never removed (T-03-05 + T-03-06)
- `merge_prefix_buckets` returns `Ok(())` despite bucket failures → silent partial merge
- `mod common;` compiles the shared test helpers into each test binary (noisy counts, harmless)
- `cargo fmt --check` drift in `src/cli/commands/count.rs`, `src/hash/table.rs`, `tests/parallel_count_tests.rs` — still a Phase 1 CI gate failure independent of Phase 3

---

## Self-Check: PASSED

- Commits verified present in history: `e61c87a`, `d493bfb` ✓
- Files verified on disk: `src/database/temp_lifecycle.rs`, `tests/merge_cleanup_tests.rs`, `src/database/prefix_cache_merge.rs`, `src/database/format.rs`, `src/database/mod.rs`, `Cargo.toml` ✓
- `commits: 4` is MEASURED via `git rev-list --count b4ebc88..HEAD` (ledger at `.git/gsd-plan-head-before-03-02`) — 2 task commits + this SUMMARY commit + the STATE/ROADMAP commit ✓
- Task 1 acceptance criteria re-run: `tempfile = "3.12"` under `[dependencies]` ✓; `cargo build --release` exits 0 ✓; `temp_lifecycle.rs` exists and `mod.rs` declares it ✓; `cargo test --test merge_cleanup_tests --no-run` exits 0 ✓; 4 `#[ignore]`d stubs registered ✓; `[profile.release]` unchanged ✓; clippy exits 0 ✓
- Task 2 acceptance criteria re-run: `const RECORD_SIZE: usize = 20;` at `prefix_cache_merge.rs:24` ✓; `try_into().unwrap()` 16 → 2 (both in `read_record_at`) ✓; `if result.is_ok() && !` gate absent ✓; `impl Drop for ExternalSortMerger` present ✓; `TempDir`/`create_merge_temp_subdir` references present ✓; `sweep_stale_merge_dirs` body has `remove_dir_all` + prefix check + `log::info!`/`log::warn!` ✓; `cargo test --test merge_cleanup_tests` 26 passed / 0 ignored ✓; `cargo test --lib` 217 passed ✓; clippy `-D warnings` exits 0 ✓; `cargo build --release` exits 0 ✓
- Full `cargo test` green: 217 lib + 26 merge_cleanup + 25 merge_routing + 34 golden + 23 round_trip + 20 mod + 8 property + 5 cjk + 3 legacy + 2 consistency, 0 failures ✓
- `golden_tests.rs` 34/34 pass — `.rkdb` v2 on-disk format untouched (D-10 / DENSE-02 preserved) ✓

---
*Phase: 03-memory-safety*
*Completed: 2026-10-07*