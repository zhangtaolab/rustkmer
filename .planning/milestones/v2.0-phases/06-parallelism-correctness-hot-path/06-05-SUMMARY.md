---
phase: 06-parallelism-correctness-hot-path
plan: 05
subsystem: hash/counter-concurrency
tags: [par-02, concurrency, atomic, fetch-update, cas, thread-local, regression, gap-closure, overflow]

requires:
  - phase: 06-parallelism-correctness-hot-path
    plan: 02
    provides: "per-worker LocalKmerCounts and the checked merge_local_counts reduction"
  - phase: 06-parallelism-correctness-hot-path
    plan: 04
    provides: "parallel per-file local reduction (locals.par_iter().try_for_each), the concurrent-caller configuration that exposed the race"
  - phase: 06-parallelism-correctness-hot-path
    provides: "06-VERIFICATION.md Gap 1: aggregate total_kmers lost updates under the parallel local reduction"
provides:
  - "Atomic checked CAS publication of total_kmers: concurrent merge_local_counts calls compose deltas instead of overwriting each other"
  - "Deterministic regression concurrent_local_reduction_never_loses_aggregate_total (16 threads x 2000 rounds, exact total/unique every round), RED 266/2000 pre-fix and GREEN post-fix"
  - "local_reduction_total_overflow_is_fail_loud_and_never_wraps: u64::MAX - 1 seed proves the verbatim overflow error and no wrap"
  - "Corrected thread-safety and parallel-reduction docs: concurrent merges supported, concurrent counting still unsupported"
affects: [07, 08, 09]

actuals:
  tokens: 3160
  tasks: 2
  commits: 2
  plan_head_before: 4b61fb963ac8dd1eb30c349c27e178c386222f54
  plan_head_after: f61534b70d1767bd0e6a5a8f0e57b1f308f3f1c5

tech-stack:
  added: []
  patterns:
    - "Aggregate statistics are published with AtomicU64::fetch_update(Relaxed, Relaxed, checked_add) — a compare-exchange loop — never load + store; a bare fetch_add is rejected because it silently wraps on u64 overflow"
    - "Concurrency regressions are barrier-synchronized and assertion-free inside the round loop, so a pre-fix failure reports observations instead of deadlocking barrier-blocked workers"
    - "Concurrent merge_local_counts is a supported configuration; concurrent counting on the same counter remains unsupported"

key-files:
  created: []
  modified:
    - "src/hash/table.rs"
    - "tests/thread_local_count_tests.rs"

key-decisions:
  - "Used AtomicU64::fetch_update with checked_add rather than a bare fetch_add: the CAS loop composes concurrent deltas while preserving the fail-loud u64 overflow contract; fetch_add would wrap silently"
  - "Both fetch_update orderings are Relaxed, matching the existing fetch_add usage in increment/merge; for a monotone statistic atomicity (not ordering) is what prevents lost updates"
  - "The regression protocol records (total_kmers, unique_kmers) between barrier A (before merges) and barrier B (after merges) and asserts only after the scope joins, so the pre-fix RED is reproducible without deadlock"
  - "No dependency, manifest, CLI, PyO3, or database-format change: per-key u32 exactness, .rkdb v2 bytes, public APIs, and MSRV 1.82 are untouched"

requirements-completed: [PAR-02]

coverage:
  - id: D1
    description: "Concurrent merge_local_counts calls never lose an update to the shared aggregate total; every barrier-synchronized round publishes exactly 16 total and 16 unique"
    requirement: PAR-02
    verification:
      - kind: integration
        ref: "tests/thread_local_count_tests.rs#concurrent_local_reduction_never_loses_aggregate_total"
        status: pass
    human_judgment: false
  - id: D2
    description: "Aggregate u64 overflow remains fail-loud with the verbatim message, never wraps, and publishes unique_kmers to match the poisoned partial table"
    requirement: PAR-02
    verification:
      - kind: unit
        ref: "src/hash/table.rs#local_reduction_total_overflow_is_fail_loud_and_never_wraps"
        status: pass
    human_judgment: false
  - id: D3
    description: "Thread-safety and parallel-reduction documentation states the real concurrency contract instead of the unsound exact-delta claim"
    verification:
      - kind: other
        ref: "src/hash/table.rs merge_local_counts # Thread safety and reduce_local_counts parallel-reduction paragraph (#05 gap closure)"
        status: pass
    human_judgment: false

duration: 3 min
completed: 2026-11-12
status: complete
---

# Phase 06 Plan 05: Atomic Aggregate Total Publication Summary

**Atomic CAS publication of `total_kmers` under parallel local reduction, guarded by a deterministic 16-thread x 2000-round regression and a fail-loud u64 overflow proof**

## Performance

- **Duration:** 3 min
- **Started:** 2026-11-12T13:34:52Z
- **Completed:** 2026-11-12T13:38:33Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Replaced the non-atomic `load` + `checked_add` + `store` publication of `total_kmers` in `merge_local_counts` with `AtomicU64::fetch_update(Relaxed, Relaxed, checked_add)`, so concurrent callers under `reduce_local_counts`' `locals.par_iter().try_for_each` compose their deltas instead of overwriting each other.
- Added the deterministic regression `concurrent_local_reduction_never_loses_aggregate_total`: 16 threads x 2000 rounds, one distinct key per local, barrier-synchronized so every round's 16 merges start together; asserts `total_kmers == 16` and `unique_kmers == 16` in every round plus the final table's 16 entries of count 1.
- Recorded the pre-fix RED: `lost rounds=266/2000`, first failing round 0, observed `(14, 16)` versus expected `16`; post-fix the test passes deterministically (five consecutive runs, 0 lost rounds).
- Added `local_reduction_total_overflow_is_fail_loud_and_never_wraps`, seeding `u64::MAX - 1` and merging a delta of 2: the verbatim `Total k-mer count overflow during local reduction` error is returned, the total stays at `u64::MAX - 1` (no wrap), and `unique_kmers` is published to match the poisoned partial table.
- Corrected the unsound docs: concurrent `merge_local_counts` is now stated as supported (per-key shard lock + atomic CAS total), while concurrent counting remains unsupported.
- Full locked suite green: 26 suites, 432 passed, 0 failed, 4 ignored. MSRV 1.82 clippy with `-D warnings` exits 0 for both the root and PyO3 crates; `rustfmt --check` is clean on both changed files.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the deterministic concurrent-reduction regression test and record its pre-fix RED result** - `bdb21e6` (test)
2. **Task 2: Publish total_kmers with an atomic checked read-modify-write and prove the regression and overflow contract green** - `f61534b` (fix)

**Plan metadata:** `docs(06-05): complete atomic aggregate total publication plan`

## Files Created/Modified

- `src/hash/table.rs` - `fetch_update` + `checked_add` publication; corrected `merge_local_counts` thread-safety and `reduce_local_counts` parallel-reduction docs; new aggregate-overflow unit test
- `tests/thread_local_count_tests.rs` - new barrier-synchronized concurrent-reduction regression (16 threads x 2000 rounds)

## Decisions Made

- `fetch_update` + `checked_add` over a bare `fetch_add`: the CAS loop composes concurrent deltas and preserves the fail-loud u64 overflow contract; `fetch_add` would silently wrap past `u64::MAX`.
- Both orderings are `Relaxed`, matching the existing `fetch_add` usage in `increment`/`merge`; the statistic is monotone, so atomicity — not ordering — is what prevents lost updates.
- The regression keeps all assertions outside the round loop so a pre-fix failure records observations rather than deadlocking barrier-blocked workers; the parent resets before barrier A and observes between A and B.
- No per-key serialization, mutex, dependency, manifest, CLI, PyO3, or database-format change: per-key checked u32 sums stay parallel and exact, `.rkdb` v2 bytes and public APIs are untouched, and `PyCounter.get_stats().total_kmers` inherits the fix through the same `KmerCounter` atomic.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The host's default toolchain is Rust 1.101.0-nightly, which deprecates `AtomicU64::fetch_update` in favor of `try_update`. `try_update` does not exist on the MSRV 1.82 toolchain that CI and the plan's clippy gate pin, and the plan mandates `fetch_update`; the deprecation is therefore a warning only on newer toolchains (test builds still pass) and is absent from the MSRV 1.82 clippy gate (exit 0). No suppression attribute was added, so the MSRV incompatibility of `try_update` stays visible.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 6 Gap 1 is closed: the aggregate `total_kmers` statistic is now safe under the parallel local reduction introduced by 06-04, with the pre-fix RED and post-fix GREEN both recorded.
- All Phase 6 truths should now verify (20/20); re-run `/gsd-verify-work 06` to confirm.
- No blockers carried forward; Phase 7 (shared engine) can build on a counter whose local reduction and aggregate publication both have explicit, correct concurrency contracts.

---
*Phase: 06-parallelism-correctness-hot-path*
*Completed: 2026-11-12*

## Self-Check: PASSED

- Files exist: `src/hash/table.rs`, `tests/thread_local_count_tests.rs`, `06-05-SUMMARY.md`
- Commits exist on HEAD: `bdb21e6` (test), `f61534b` (fix)
- Scope identity: base..HEAD changes exactly `src/hash/table.rs` and `tests/thread_local_count_tests.rs`
- Verification: `cargo test --locked` (26 suites, 432 passed, 0 failed, 4 ignored), `cargo test --locked --test thread_local_count_tests` (10 passed), `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` root and pyo3 (exit 0), `rustfmt --check` both files (clean)

