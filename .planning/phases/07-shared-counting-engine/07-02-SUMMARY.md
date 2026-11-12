---
phase: 07-shared-counting-engine
plan: 02
subsystem: counting-engine
tags: [rust, k-mer-counting, persistent-workers, bounded-queues, flush-ack, thread-gate, multi-member-gzip, exactness]

requires:
  - phase: 07-shared-counting-engine
    provides: for_each_window extractor, PartitionLayout routing, sequential CountEngine, CountResult exactness
  - phase: 06-parallelism-correctness-hot-path
    provides: LocalKmerCounts tables, checked reduction, golden/thread-local gates, PROF-02 observer
provides:
  - Persistent producer/worker pipeline — N named `rustkmer-count-{i}` OS workers, contiguous partition ownership, bounded sync_channel queues, file-boundary flush/ack
  - CLI fully cut over to CountEngine at every thread count; the legacy per-chunk path is deleted from src/cli/commands/count.rs
  - Exact PROF-02 formula (2 at N=1, 2N+1 otherwise), polling to the expected total, and an end-to-end RED negative control
  - Engine-level determinism (t1/t4/t16 .rkdb sha256), multi-member gzip, trailing-garbage, and partition-conservation proofs
affects: [07-03 PyO3 extractor routing, 07-04 engine measurement, 08 output sort, 09 Python D2/merge, 11 spill]

actuals:
  tokens: 32936
  tasks: 3
  commits: 4
  plan_head_before: 80d672444f8b794dab4295c37f1ab89654047475
  plan_head_after: 18fe504b64412d1c80ac6a6fa54ff73ba5980f62

tech-stack:
  added: []
  patterns:
    - "One producer on the caller thread + N persistent OS workers; no blocking receive on rayon, no per-chunk fork-join barrier"
    - "Partition-tagged owned key batches over per-worker bounded sync_channel queues (backpressure, never unbounded)"
    - "File-boundary Flush{token} -> per-worker ack -> checked cumulative stats; stale tokens rejected"
    - "Every send/recv/worker failure drops senders and joins all workers, preferring the worker's own verbatim error"
    - "Thread gate is an exact hard equality (2 / 2N+1), polls through the intermediate rayon-only state, and has a true RED negative control"

key-files:
  created:
    - src/count/batch.rs
  modified:
    - src/count/engine.rs
    - src/count/mod.rs
    - src/cli/commands/count.rs
    - tests/count_engine_tests.rs
    - tests/thread_pool_size_tests.rs
    - .planning/research/profiling/verify_threads.py
    - scripts/bench/tests/test_verify_threads.py

key-decisions:
  - "threads == 1 keeps the true sequential path byte-for-byte (no queue, no worker); threads > 1 spawns exactly N named workers owning contiguous partition ranges"
  - "Workers own their tables outright; the producer routes through the ONE for_each_window sink into per-partition Vec buffers and moves them into CountBatch values (no clones, no shared writes)"
  - "Flush acks are per worker (sync_channel(1)); acks carry cumulative totals because tables persist across files"
  - "On any channel or worker failure the engine joins first and returns the worker-returned error when present, so a seeded overflow surfaces verbatim instead of as a disconnect symptom"
  - "The CLI consumes CountResult directly; CountOutput and every legacy per-chunk helper were deleted rather than left dormant"
  - "The thread gate asserts exact equality and reserves exit 2 only for never-observed / alive-timeout / infrastructure; the RED control proves the pre-engine N+1 model is still rejected"

requirements-completed: [ENGINE-01, ENGINE-02]

coverage:
  - id: D1
    description: "Persistent producer/worker pipeline with bounded per-worker queues and checked file-boundary flush acks is exact at t1/t4/t16 and deadlock-free on error/Drop"
    requirement: ENGINE-01
    verification:
      - kind: integration
        ref: "tests/count_engine_tests.rs#engine_worker_pipeline_is_exact_at_t1_t4_and_t16"
        status: pass
      - kind: integration
        ref: "tests/count_engine_tests.rs#engine_worker_count_matches_requested_threads"
        status: pass
      - kind: integration
        ref: "tests/count_engine_tests.rs#engine_layout_handles_non_divisible_worker_counts"
        status: pass
      - kind: integration
        ref: "tests/count_engine_tests.rs#engine_multi_file_cumulative_is_exact_with_workers"
        status: pass
      - kind: unit
        ref: "cargo test --locked --lib count::engine"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every CLI thread count counts through the engine; the legacy per-chunk helpers, CHUNK_SIZE, par_chunks/try_for_each_init, and CountOutput are gone"
    requirement: ENGINE-01
    verification:
      - kind: other
        ref: "grep -n 'par_chunks|try_for_each_init|CHUNK_SIZE|SUBSLICE_RECORDS|CountOutput|KmerCounter' src/cli/commands/count.rs (no match)"
        status: pass
      - kind: integration
        ref: "cargo test --locked (full suite: 26 integration binaries + 259 lib tests + doctests, 0 failed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "PROF-02 observes exactly 2 OS threads at N=1 and 2N+1 at N=4/16, polling through the intermediate state; the pre-engine N+1 model is measured RED end-to-end"
    requirement: ENGINE-02
    verification:
      - kind: integration
        ref: "tests/thread_pool_size_tests.rs#pool_size_matches_requested_threads (3 consecutive runs)"
        status: pass
      - kind: integration
        ref: "tests/thread_pool_size_tests.rs#pool_size_characterization_records_requested_pool"
        status: pass
      - kind: unit
        ref: "python3 -m unittest scripts.bench.tests.test_verify_threads (18 tests)"
        status: pass
      - kind: e2e
        ref: "verify_threads.py against target/debug/rustkmer: requested=1 observed=2; requested=4 observed=9; requested=16 observed=33; GREEN"
        status: pass
    human_judgment: false
  - id: D4
    description: "Sorted .rkdb bytes are identical at t1/t4/t16; multi-member gzip counts every member; trailing garbage fails with the path; partition tables conserve totals/uniques (reference + proptest)"
    requirement: ENGINE-01
    verification:
      - kind: integration
        ref: "tests/count_engine_tests.rs#t1_t4_t16_maps_and_rkdb_sha256_are_identical"
        status: pass
      - kind: integration
        ref: "tests/count_engine_tests.rs#multi_member_gzip_counts_every_member_at_t1_and_t4"
        status: pass
      - kind: integration
        ref: "tests/count_engine_tests.rs#trailing_garbage_fails_loudly_with_file_context"
        status: pass
      - kind: integration
        ref: "tests/count_engine_tests.rs#partition_disjointness_and_conservation_hold"
        status: pass
      - kind: integration
        ref: "tests/count_engine_tests.rs#proptest_partition_disjointness_and_conservation"
        status: pass
    human_judgment: false
  - id: D5
    description: "No new dependencies and MSRV 1.82 stays clean on both crates; seeded u32::MAX overflow and u64 aggregate overflow fail loud without hanging"
    requirement: ENGINE-01
    verification:
      - kind: other
        ref: "cargo +1.82.0 clippy --locked --all-targets -- -D warnings (root and pyo3)"
        status: pass
      - kind: unit
        ref: "src/count/engine.rs#worker_overflow_returns_verbatim_error_without_hanging"
        status: pass
      - kind: unit
        ref: "src/count/engine.rs#reduce_worker_stats_fails_loud_on_aggregate_overflow"
        status: pass
      - kind: unit
        ref: "src/count/engine.rs#engine_drop_joins_workers"
        status: pass
      - kind: other
        ref: "Cargo.toml / Cargo.lock unchanged"
        status: pass
    human_judgment: false

duration: 13min
completed: 2026-11-12
status: complete
---

# Phase 7 Plan 02: Shared Counting Engine (Persistent Worker Pipeline) Summary

**One producer over the shared extractor, N persistent OS workers with disjoint partition tables and bounded queues, a full CLI cutover, and an exact 2N+1 thread gate that still turns RED on the pre-engine defect.**

## Performance

- **Duration:** 13 min (785 s)
- **Started:** 2026-11-12T15:10:06Z
- **Completed:** 2026-11-12T15:23:11Z
- **Tasks:** 3
- **Files modified:** 8 (1 created, 7 modified)

## Accomplishments

- `src/count/batch.rs` lands `CountBatch::{Dense, Wide, Flush}` and `WorkerStat::Flush`; `sync_channel::send` moves the batch, so the producer never retains a sent `Vec`, and the single FIFO channel per worker makes `Flush` a true barrier after every preceding batch.
- `CountEngine` now has two shapes. `threads == 1` keeps the 07-01 sequential path untouched (no queue, no worker thread, `worker_count() == 0`). `threads > 1` spawns exactly N named `rustkmer-count-{i}` OS threads, each moving into its own contiguous `PartitionLayout::worker_range` and its own bounded batch/ack pair. No worker calls rayon, prints, or unwraps.
- The producer keeps the ONE `for_each_window` extractor: it routes each key with `partition_of` into a per-partition `Vec<u64>`/`Vec<u128>` and blocks on a full queue (bounded backpressure). There is no per-chunk fork-join barrier and no shared write during counting.
- File boundaries flush buffers, send one `Flush { token }` per worker, and reduce the acks with `checked_add`. Error paths are deadlock-safe: a send/recv failure drops every sender, joins every worker, and returns the worker's own error when one exists (so a seeded `u32::MAX` surfaces the verbatim overflow rather than a disconnect). `Drop` joins survivors; `finish` concatenates tables in layout order.
- `execute_count` counts every file through one engine at every resolved thread count. `CountOutput`, `process_fasta_file`, `process_fastq_file`, `count_chunk_into_locals`, `count_record_into`, `CHUNK_SIZE`, and `SUBSLICE_RECORDS` are deleted; the frozen writers consume `&CountResult` directly.
- The PROF-02 gate now asserts the engine's exact model: 2 OS threads at `--threads 1` and 9/33 at 4/16. `observe()` polls through the intermediate rayon-only state, accepts an over-count as measured RED, and records a below-expected child exit after a successful sample as measured RED (exit 1), reserving exit 2 for never-observed/timeout/infra. The end-to-end negative control proves the gate still rejects the pre-engine N+1 model.
- Exactness and robustness are pinned: t1/t4/t16 text maps and sorted `.rkdb` bytes are identical; two-member gzip counts the concatenation; trailing garbage fails with the file path; partition tables conserve totals/uniques against the reference and a proptest over k 1..=64 × canonical.

## Measured Evidence

**Live thread observations (helper against `target/debug/rustkmer`, 100k-read fixture):**

```
requested=1 observed=2
requested=4 observed=9
requested=16 observed=33
THREAD REALITY verdict=GREEN
```

The standing Rust gate passed three consecutive runs (3.60 s / 3.59 s / 3.58 s).

**RED negative control (pre-engine N+1 stub):** exit 1, `requested=4 observed=5`, `THREAD REALITY verdict=RED`, JSON `observed == 5`, `requested == 4`, `child_returncode == 0`. Complementary never-observed stub: exit 2, no verdict line, no JSON.

**Determinism (5,000 reads, k = 21 canonical, debug binary):**

| Threads | `.rkdb` sha256 | Text map |
|---|---|---|
| 1 | `26561c3ede49a007c68ef1520db2232923590062084266ccdf5b9c0a675e4dcf` | identical |
| 4 | `26561c3ede49a007c68ef1520db2232923590062084266ccdf5b9c0a675e4dcf` | identical |
| 16 | `26561c3ede49a007c68ef1520db2232923590062084266ccdf5b9c0a675e4dcf` | identical |

649,998 distinct k-mers in the fixture output.

**Suites:** `count_engine_tests` 20 passed; `thread_pool_size_tests` 2 passed × 3 runs; `golden_sha256_tests` 5; `golden_tests` 34; `thread_local_count_tests` 10; `dense_differential_tests` 6; `parallel_count_tests` 4; `window_extract_differential_tests` 9; lib 259; full `cargo test --locked` green. `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` clean on both `rustkmer` and `rustkmer-pyo3`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Persistent worker pipeline with bounded per-worker queues and flush protocol** - `d46a2f2` (feat)
2. **Task 2: CLI cutover to the engine plus the exact 2N+1 PROF-02 gate and polling fix** - `5ed4c75` (feat)
3. **Task 3: Parallel exactness, multi-member gzip, and failure-path hardening** - `aead9e3` (test)
4. **MSRV lint fix** - `18fe504` (fix)

Plan metadata: the final docs commit with this SUMMARY, STATE.md, ROADMAP.md, and REQUIREMENTS.md.

## Files Created/Modified

- `src/count/batch.rs` - `CountBatch`, `WorkerStat`, ownership/ordering docs, Send assertion
- `src/count/engine.rs` - parallel `CountEngine`, `spawn_parallel`, worker loop, routing buffers, flush/ack reduction, checked stats, join/Drop, seeded-overflow and Drop unit tests
- `src/count/mod.rs` - declares `pub mod batch` and re-exports the messages
- `src/cli/commands/count.rs` - engine at every thread count, deleted legacy path, `&CountResult` writers, engine-aware `--verbose`
- `tests/count_engine_tests.rs` - worker exactness/counts/layout/multi-file, determinism sha256, elementwise sum, conservation + proptest, multi-member gzip, trailing garbage
- `tests/thread_pool_size_tests.rs` - exact 2 / 2N+1 standing gate, no single-core skip
- `.planning/research/profiling/verify_threads.py` - `expected_total`, polling semantics, `verdict_for_records`, updated docstrings
- `scripts/bench/tests/test_verify_threads.py` - formula/verdict/polling/terminal unit tests and end-to-end RED/exit-2 negative controls

## Decisions Made

- **Sequential path preserved exactly at t1:** the engine still counts on the caller thread with zero workers, so the t1 baseline and the 2-thread observation stay honest.
- **Static ownership, no stealing:** each worker owns its contiguous partition range and no shared table exists; the measured producer-bound budget is the documented lever if scaling disappoints (07-04 measurement).
- **Join-then-prefer-worker-error:** every channel failure path joins the workers and returns the worker's own `ProcessingResult` error, which is what makes the seeded overflow test see the verbatim message instead of the disconnect.
- **Exactness over convenience:** acks carry cumulative totals because tables persist across files; stale tokens are rejected; all aggregate sums use named checked messages.
- **Gate strictness preserved:** no `>=`, no override flag, no self-reported pool size; exit 2 is only for unobservable/infra outcomes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Reflowed gate doc comment for MSRV 1.82 clippy**
- **Found during:** Post-task MSRV verification
- **Issue:** A doc-comment line beginning with `+` was parsed as a markdown list item, tripping `clippy::doc_lazy_continuation` under `-D warnings` on Rust 1.82.
- **Fix:** Reworded the same content without a leading `+`; no behavioral change.
- **Files modified:** `tests/thread_pool_size_tests.rs`
- **Verification:** `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` passes on root and pyo3.
- **Committed in:** `18fe504`

### Sequencing note (no behavioral or scope change)

The seeded `u32::MAX` overflow test, the aggregate-ack overflow test, and `engine_drop_joins_workers` landed in the Task 1 commit with the engine machinery they exercise; Task 3's action listed them under the engine module as well, and the Task 3 commit carries the remaining exactness/gzip/conservation matrix. No test or deliverable was dropped.

**Total deviations:** 1 auto-fixed (1 blocking lint)
**Impact on plan:** Minimal; the lint fix is documentation-only and the test placement is a commit-boundary adjustment.

## Issues Encountered

- The first RED negative-control stub let its sleeping threads wake 0.5 s before the process exited, so the last `sample` observed the teardown state (1 thread) and the measured count was 1. Holding the daemon threads past the main thread plus `os._exit(0)` removed the teardown window and the control now records the honest `observed=5`.
- The complementary exit-2 stub needs a genuinely instantaneous child: a shell script could still be sampled during its startup. The test copies the real `false` binary instead, so the first observation always fails and the helper exits 2 with no verdict/JSON. (`shutil.copy2` failed on macOS `chflags`; `copyfile` + chmod is used.)
- The 100k-read debug fixture remained observable at the expected totals on all three consecutive gate runs, so the R9 larger-fixture/readiness-marker remedy was not needed.

## Known Stubs

None. No placeholders, skipped tests, or unrun verifications were introduced. The gate's exit-2 controls are deliberate unobservable-child tests, not stubs of production behavior.

## Threat Flags

None beyond the plan's threat model. New surface is limited to in-process OS threads and bounded channels; no new network, auth, file, or dependency surface. `Cargo.toml` / `Cargo.lock` are unchanged.

## Next Phase Readiness

- 07-03 can route the PyO3 window loop through `for_each_window` without touching the engine; the engine is CLI-complete.
- 07-04 can measure producer/worker split, t1/t4/t16 wall, and peak RSS on the real slice; the pipeline is producer-bound by design and the worker queues/batches are configurable.
- Phase 8 can consume `CountResult` directly; Phase 9 has the `merge_into` bridge and the now-tested error/Drop contracts.
- No blockers. The standing gate is exact and green on this host.

## Self-Check: PASSED

- Created files verified present: `src/count/batch.rs`; modified files present.
- Task commits verified as ancestors of HEAD: `d46a2f2`, `5ed4c75`, `aead9e3`, `18fe504`.
- `Cargo.toml` / `Cargo.lock` unchanged.

---
*Phase: 07-shared-counting-engine*
*Completed: 2026-11-12*
