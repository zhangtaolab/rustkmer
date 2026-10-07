---
phase: 03-memory-safety
plan: 01
subsystem: database
tags: [rust, rkdb, merge, memory-budget, admission-control, streaming, estimator]

requires:
  - phase: 01-foundation-quality
    provides: "log:: facade + clippy -D warnings gate (FOUND-01/02); committed golden .rkdb fixtures that must not break"
  - phase: 02-parallel-counting
    provides: "unaffected — counting path untouched; shared-core discipline (core wins flow to CLI + pyrustkmer)"
provides:
  - "RKDatabase::estimate_total_kmers — header-only total_kmers reader (the D-01 OOM-on-estimate fix)"
  - "MERGE-02 hard admission control: over-budget 'auto' merges hard-route to streaming; over-budget 'memory' merges are rejected with an actionable Err"
  - "D-02 reject path — explicit --merge-mode memory can no longer silently OOM"
  - "tests/merge_routing_tests.rs — 5 tests (1 smoke + 4 routing/reject) proving MERGE-01 + MERGE-02 at toy scale"
  - "Two latent data-loss fixes in the streaming merge (heap-refill strand + temp-file name collision)"
affects: [03-02, 03-03, 03-04, 03-05, phase-04-benchmark]

actuals:
  tokens: 11857
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Header-only estimator: read persisted counts from a fixed-size file header instead of materializing the dataset"
    - "Side-effect path-selection probe: point a path's only side-effecting dependency at a nonexistent path to make branch selection observable without changing the public API"

key-files:
  created:
    - tests/merge_routing_tests.rs
    - .planning/phases/03-memory-safety/deferred-items.md
  modified:
    - src/database/format.rs
    - src/database/streaming_merge.rs
    - src/io/fasta.rs
    - src/io/fastq.rs

key-decisions:
  - "estimate_total_kmers is a pub associated fn on RKDatabase (not a free fn) so the integration test can assert the D-01 property directly from an external test crate; mirrors the 02-05 precedent of making resolve_thread_count_from pub for the same reason"
  - "A corrupt/unreadable header falls back to the file-size estimate instead of erroring: the merge still routes conservatively to streaming, which does its own per-chunk validation and surfaces the real corruption"
  - "Path selection in tests is observed via a nonexistent temp_dir probe (the streaming path writes chunk files there, the in-memory path does not) rather than adding a public strategy-returning API or capturing logs"
  - "estimated_memory uses saturating_mul instead of the original `as usize * 24` — the old form could overflow into a panic in debug builds on a large header value"
  - "Two pre-existing streaming-merge data-loss bugs were fixed in this plan because MERGE-01 promotes that exact path to default; shipping the hard route on top of a truncating merge would have been a regression introduced by this plan"

patterns-established:
  - "Bounding proof over scale proof: routing logic is size-independent, so it is proven at toy scale with an absurd budget rather than needing human-genome data in CI"
  - "D-01 test pattern: a .rkdb whose header declares a huge total_kmers over a truncated body — a materializing reader dies (or aborts the process), a header-only reader returns the declared value"

requirements-completed: [MERGE-01, MERGE-02]

coverage:
  - id: D1
    description: "The merge estimator reads only the 42-byte .rkdb header and never materializes entries (D-01 OOM-on-estimate fix)"
    requirement: MERGE-01
    verification:
      - kind: unit
        ref: "src/database/format.rs::tests::merge_admission_control::estimate_total_kmers_reads_header_only"
        status: pass
      - kind: unit
        ref: "src/database/format.rs::tests::merge_admission_control::estimate_total_kmers_falls_back_to_file_size"
        status: pass
      - kind: unit
        ref: "src/database/format.rs::tests::merge_admission_control::estimate_total_kmers_tolerates_corrupt_header"
        status: pass
      - kind: integration
        ref: "tests/merge_routing_tests.rs#estimator_reads_header_only_no_materialization"
        status: pass
    human_judgment: false
  - id: D2
    description: "Admission control is a hard route: an over-budget 'auto' merge goes unconditionally to streaming, with no warn-and-continue in-memory fallback (MERGE-02)"
    requirement: MERGE-02
    verification:
      - kind: unit
        ref: "src/database/format.rs::tests::merge_admission_control::should_use_streaming"
        status: pass
      - kind: integration
        ref: "tests/merge_routing_tests.rs#merge_over_budget_hard_routes_to_streaming"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-02 reject: an explicit --merge-mode memory merge whose estimate exceeds the budget returns Err naming both the memory mode and the streaming alternative, instead of silently OOMing"
    requirement: MERGE-01
    verification:
      - kind: unit
        ref: "src/database/format.rs::tests::merge_admission_control::memory_mode_over_budget_is_rejected"
        status: pass
      - kind: integration
        ref: "tests/merge_routing_tests.rs#merge_explicit_memory_mode_over_budget_rejects"
        status: pass
    human_judgment: false
  - id: D4
    description: "merge_mode 'streaming' always selects the streaming path regardless of the estimate"
    requirement: MERGE-01
    verification:
      - kind: integration
        ref: "tests/merge_routing_tests.rs#merge_explicit_streaming_mode_always_streams"
        status: pass
    human_judgment: false
  - id: D5
    description: "The in-memory fast path is retained for small inputs (D-02): a within-budget 'auto' or 'memory' merge still takes the in-memory path and produces the correct union"
    requirement: MERGE-01
    verification:
      - kind: integration
        ref: "tests/merge_routing_tests.rs#merge_default_routes_small_inputs_to_inmemory_or_streaming"
        status: pass
      - kind: integration
        ref: "src/database/format.rs::tests::test_merge_memory_basic"
        status: pass
    human_judgment: false
  - id: D6
    description: "The streaming path MERGE-01 promotes to default no longer silently drops k-mers (two latent data-loss bugs fixed)"
    requirement: MERGE-01
    verification:
      - kind: integration
        ref: "tests/merge_routing_tests.rs#merge_over_budget_hard_routes_to_streaming (asserts the exact 200-k-mer union through the streaming path)"
        status: pass
      - kind: integration
        ref: "tests/merge_routing_tests.rs#merge_explicit_streaming_mode_always_streams (asserts the exact 200-k-mer union)"
        status: pass
    human_judgment: false
  - id: D7
    description: "Absolute human-genome-scale merge memory bound (no OOM at real scale)"
    requirement: MERGE-01
    verification: []
    human_judgment: true
    rationale: "CI and this machine have no human-scale dataset, so only the size-independent routing LOGIC is proven here. The plan's own RESEARCH section defers actual human-scale validation to Phase 4's benchmark against CRR1936095. A human must confirm the end-to-end bound on real data."

commits: 4
plan_head_before: ec52a6325c15a2a8c9b7ffaa16f3da06ebdce0e5
plan_head_after: 26a66974755c01ce8d0f183e1c36d9ccd15abcd4

duration: 42min
completed: 2026-10-07
status: complete
---

# Phase 3 Plan 1: Header-Only Merge Estimator + Hard Admission Control Summary

**The OOM-on-estimate bug that made every merge unsafe is gone: the merge planner now reads 42-byte headers instead of loading every k-mer into RAM to count them, and the budget check became a hard route rather than a suggestion.**

## Performance

- **Duration:** 42 min
- **Started:** 2026-10-07T02:16:13Z
- **Completed:** 2026-10-07T02:58:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- **`RKDatabase::estimate_total_kmers`** — new header-only estimator. Reads the persisted `total_kmers` from the 42-byte `.rkdb` header through `DatabaseHeader::read_from` (which validates magic + version before any field is trusted), falling back to `(file_size - 42) / 20` when the header is unreadable or reports `0`. Replaced **both** OOM-on-estimate call sites: `merge_databases`' estimator loop and `should_use_streaming`.
- **MERGE-02 admission control is now a hard route.** Over budget under `merge_mode: "auto"` routes unconditionally to `merge_databases_streaming` — no warn-and-continue in-memory path.
- **D-02 reject landed.** An explicit `--merge-mode memory` merge whose estimate exceeds the budget returns `Err` naming both the memory mode and the streaming alternative, instead of silently OOMing. The in-memory path itself is retained for small/test merges.
- **`merge_mode: "streaming"` always streams**, regardless of the estimate.
- **Found and fixed two latent data-loss bugs in the streaming merge** (see Deviations) — this mattered because MERGE-01 promotes exactly that path to default. A 200-k-mer merge had been returning 5 k-mers.
- 5 routing tests + 5 new lib unit tests, all GREEN; 0 `#[ignore]`d.

## Task Commits

1. **Task 1: Wave-0 scaffold `tests/merge_routing_tests.rs`** — `db90529` (test)
2. **Task 2: Header-only estimator + hard-route + D-02 reject** — `fc8da65` (feat)
3. **Plan metadata:** `3aa2d2f` (docs: SUMMARY.md)
4. **Plan close-out:** `26a6697` (docs: STATE.md, ROADMAP.md, REQUIREMENTS.md)

## Files Created/Modified

- `tests/merge_routing_tests.rs` (new) — 5 tests: 1 smoke + 4 MERGE-01/MERGE-02 routing/reject tests
- `src/database/format.rs` — `estimate_total_kmers` added; `merge_databases` estimator loop and `should_use_streaming` switched to it; D-02 reject + explicit-streaming branches added; new `merge_admission_control` unit-test module
- `src/database/streaming_merge.rs` — two data-loss fixes (heap-refill strand, temp-file name collision)
- `src/io/fasta.rs`, `src/io/fastq.rs` — 4 pre-existing clippy lint fixes (unblocked the `-D warnings` gate)
- `.planning/phases/03-memory-safety/deferred-items.md` (new)

## Decisions Made

- **`estimate_total_kmers` is a `pub` associated fn on `RKDatabase`**, not a free fn, so the integration test can assert the D-01 property directly from an external test crate. Mirrors the 02-05 precedent (`resolve_thread_count_from` was made `pub` for the same reason).
- **A corrupt header falls back rather than erroring.** Returning `Err` would make a corrupt input fail before the merge strategy is chosen, which is a worse failure mode than over-estimating and letting the streaming path surface the real corruption during its own per-chunk validation. The fallback only ever *over*-estimates, so it routes conservatively (threat T-03-01).
- **Path selection is observed behaviorally, not via a new API.** `merge_databases` returns an `RKDatabase`, not a strategy tag, so the tests point `config.temp_dir` at a nonexistent directory: the streaming path must create a chunk file there (`Err`), the in-memory path never touches it (`Ok`). This avoids adding a public strategy-returning API or depending on log-capture.
- **`estimated_memory` now uses `saturating_mul`.** The original `total_kmers as usize * 24` could overflow into a panic in debug builds given a large header value.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `StreamingMergeIterator::next()` stranded the heap successor, truncating every streaming merge**
- **Found during:** Task 2 — `merge_over_budget_hard_routes_to_streaming` failed with 9 of 200 k-mers
- **Issue:** The k-mer-boundary branch `return Some(...)` fired *before* the refill code that read the next entry from the run's file reader. The popped item was consumed for the emit and its successor was never queued, so the rest of that run was dropped. Measured: 10 k-mers in → 2 out; 200 in → 5 out. Pre-existing, in a file this plan did not otherwise modify, and covered by no test (the existing `test_merge_streaming_basic` only asserts the result is non-empty).
- **Why in scope:** MERGE-01 makes this exact path the hard-route default. Shipping the hard route on top of a silently-truncating merge would have converted a latent bug into a guaranteed data-corruption path for every over-budget merge.
- **Fix:** Moved the reader advance + heap re-queue ahead of the emit decision, preserving the popped item's k-mer/count in locals first.
- **Files modified:** `src/database/streaming_merge.rs`
- **Verification:** `merge_over_budget_hard_routes_to_streaming` and `merge_explicit_streaming_mode_always_streams` now assert the exact 200-k-mer union with summed counts; 10/10 k-mers recovered in a direct `merge_sorted_chunks` probe.
- **Committed in:** `fc8da65`

**2. [Rule 1 - Bug] `TempFileManager` chunk-file names collided and overwrote sibling sorted runs**
- **Found during:** Task 2 — same failing test, while diagnosing #1
- **Issue:** Chunk files were named `rustkmer_{op}_{pid}_{micros}.chunk` from `SystemTime::now().as_micros()`, which is not unique at microsecond granularity. Several `create_temp_file` calls in a tight loop land on the same microsecond, and `File::create` truncates — so one chunk silently overwrote another. 8 chunks collapsed to 2 files at `chunk_size: 64`.
- **Fix:** Added a monotonic per-manager `next_file_id` counter to the filename; kept the timestamp for readability.
- **Files modified:** `src/database/streaming_merge.rs`
- **Verification:** chunk files now observed as `rustkmer_sort_<pid>_<micros>_0.chunk`, one per chunk; `prefix_cache_merge.rs` was checked and already uses explicit `{:03}` indices, so it is unaffected.
- **Committed in:** `fc8da65`

**3. [Rule 3 - Blocking] Fixed 4 pre-existing clippy errors that made the plan's `-D warnings` gate unpassable**
- **Found during:** Task 2 acceptance-criteria gate
- **Issue:** `cargo clippy --all-targets -- -D warnings` failed on 4 `useless_borrows_in_formatting` errors in `src/io/fasta.rs` and `src/io/fastq.rs` — toolchain drift (local rustc 1.99.0; the Phase 1 sweep ran on an older toolchain where this lint did not fire). Not caused by this plan, but the plan lists this exact command as a blocking acceptance criterion, so the gate could not pass. Logged to `deferred-items.md` before fixing.
- **Fix:** Removed the 4 redundant `&` in `format!` arguments.
- **Files modified:** `src/io/fasta.rs`, `src/io/fastq.rs`
- **Verification:** `cargo clippy --all-targets -- -D warnings` exits 0.
- **Committed in:** `fc8da65`

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** Deviations 1 and 2 are correctness fixes on the exact code path this plan promotes to default — without them, MERGE-01's "no longer OOM" would have been met by silently returning wrong data. Deviation 3 was required to reach the plan's own quality gate. No scope creep beyond what correctness and the stated gates demanded.

## Issues Encountered

- The plan's `<verify>` commands use `/Users/forrest/GitHub/rustkmer` (a macOS path); this executor runs on Linux at `/home/forrest/Github/rustkmer`. All verification commands were run with the path adapted. No behavioral difference.
- `cargo test --test merge_routing_tests -- --exact` (as literally written in the plan) selects zero tests, because `--exact` filters on a name that was not supplied. Ran the meaningful equivalents instead (`cargo test --test merge_routing_tests` and `cargo test --lib should_use_streaming`) — both are the plan's own `<verification>` entries and both pass.
- While building the D-01 test, calling `from_file_path` on a file whose header declares 5 billion k-mers **aborted the test process** with `memory allocation of 160000000000 bytes failed`. That is the OOM-on-estimate bug reproducing live, and it is the sharpest possible evidence for the fix. The test premise now uses a small declared count (1,000) so the materializing path returns `Err` instead of aborting, while the 5-billion value is only ever handed to the header-only estimator.

## Known Stubs

None. No `#[ignore]`d test, placeholder, or unwired data source remains in this plan's files. `tests/golden_generate.rs` (1 ignored) and `tests/parallel_count_tests.rs` (1 ignored) are pre-existing run-once baseline capture generators from Phases 1–2, untouched here.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **MERGE-01 / MERGE-02 routing logic is complete and proven at toy scale.** The human-scale memory bound itself still needs Phase 4's benchmark against CRR1936095 — that is the one deliverable a human must sign off on.
- **MERGE-03 (03-02) is unblocked and now safer to build.** Plan 03-02 adds RAII temp guards + a process-unique subdir + a startup sweep. Note that `streaming_merge.rs` already has RAII, and plan 03-01 just hardened its chunk-file naming — build 03-02 on the current file, not the pre-03-01 state.
- **MERGE-04 (03-05) is unaffected** — `PyDatabase::merge` still uses `MergeConfig::default()`, which now inherits the corrected bounded dispatch.
- **For downstream planners:** `merge_databases` is now the single admission-control point. Anything that constructs a `MergeConfig` with an explicit `merge_mode` gets the D-02 reject behavior for free, so callers must be ready to handle a new `Err` where previously the merge would have been attempted.

## Deferred Items

See `.planning/phases/03-memory-safety/deferred-items.md`:
- `cargo fmt --check` still reports pre-existing drift in `src/cli/commands/count.rs`, `src/hash/table.rs`, and `tests/parallel_count_tests.rs`. Files touched by this plan are rustfmt-clean; the three above were left alone as out-of-scope. **Note:** `cargo fmt --check` is a Phase 1 CI gate (`.github/workflows/ci.yml`), so this pre-existing drift will fail that gate independently of Phase 3 — worth a separate quick plan.
- `mod common;` compiles the shared test-helper modules (and their 20 unit tests) into the `merge_routing_tests` binary. Harmless, matches existing convention, but noisy.

---

## Self-Check: PASSED

- Commits verified present in history: `db90529`, `fc8da65` ✓
- Files verified on disk: `tests/merge_routing_tests.rs`, `src/database/format.rs`, `src/database/streaming_merge.rs`, `.planning/phases/03-memory-safety/deferred-items.md` ✓
- `commits: 4` is MEASURED via `git rev-list --count ec52a63..HEAD` (ledger written to `.git/gsd-plan-head-before-03-01` before the first commit) — 2 task commits + the SUMMARY commit + the STATE/ROADMAP/REQUIREMENTS commit ✓
- All Task 1 and Task 2 acceptance criteria re-run and passing ✓
- Full `cargo test` green: 217 lib + 25 merge_routing + 34 golden + 23 round_trip + 20 mod + 8 property, 0 failures ✓
- `cargo clippy --all-targets -- -D warnings` exits 0 ✓
- `golden_tests.rs` 34/34 pass — `.rkdb` v2 on-disk format is byte-identical (D-10 / DENSE-02 preserved) ✓

---
*Phase: 03-memory-safety*
*Completed: 2026-10-07*
