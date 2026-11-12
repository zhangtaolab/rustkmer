---
phase: 06-parallelism-correctness-hot-path
plan: 01
subsystem: measurement/threading
tags: [rayon, thread-pool, cli, benchmark-gate, provenance, thread-scaling]

requires:
  - phase: 05-measurement-regression-harness
    provides: "verify_threads.py pool observer, thread_scaling.py gate, RED pool-size/scaling baselines, pinned slice parity"
provides:
  - "--threads N sizes the rayon global pool (N workers + main), observed in a fresh CLI subprocess"
  - "always-run, green pool-size gate plus a characterization of the fixed one-worker pool"
  - "provenance-bearing GREEN synthetic scaling document with a true single-thread baseline"
  - "real 4M-read slice true t1 baseline (142.54 s) for plan 06-04"
affects: [06-02, 06-03, 06-04, 07, 09]

actuals:
  tokens: 6273
  tasks: 3
  commits: 3
  plan_head_before: 914f8a0417f17dd68820a08d269eab43014f8adb
  plan_head_after: f85003500b827fb58c0d87c8e7639238e02582b0

tech-stack:
  added: []
  patterns:
    - "Lazy fallback: std::thread::available_parallelism, never a rayon pool query before build_global"
    - "Unique-thread-id counting for macOS `sample` call graphs (summary header + section header share a tid)"

key-files:
  created:
    - ".planning/phases/06-parallelism-correctness-hot-path/thread_scaling_par01_green.json"
    - ".planning/phases/06-parallelism-correctness-hot-path/thread_scaling_par01_slice.json"
  modified:
    - "src/cli/commands/count.rs"
    - "tests/thread_pool_size_tests.rs"
    - "scripts/bench/README.md"
    - ".planning/research/profiling/verify_threads.py"
    - "scripts/bench/tests/test_verify_threads.py"

key-decisions:
  - "All-cores fallback computed lazily with available_parallelism; no rayon query can run before build_global"
  - "The pool-size standing gate is un-ignored and the bug-pinning characterization replaced by a fixed-behavior characterization"
  - "The observer counts unique thread ids so `sample` summary+section lines for one thread count once"
  - "Both baselines are measure-only/synthetic artifacts with provenance; the Phase 5 RED baseline is untouched"

patterns-established:
  - "Thread-gate repair flow: fix resolver, re-observe in fresh subprocesses, then flip standing gates and evidence"
  - "Any new thread-count observation goes through verify_threads.py's unique-id parsing, not line counting"

requirements-completed: [PAR-01]

coverage:
  - id: D1
    description: "--threads N sizes the actual rayon pool (observed equals requested plus one worker/main thread)"
    requirement: PAR-01
    verification:
      - kind: integration
        ref: "cargo test --locked --test thread_pool_size_tests#pool_size_matches_requested_threads"
        status: pass
      - kind: integration
        ref: "python3 .planning/research/profiling/verify_threads.py --threads 1 4 16 (observed 2/5/17, exit 0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The Phase 5 pool-size pair is one always-run standing gate plus a fixed-behavior characterization; no ignore attribute remains"
    requirement: PAR-01
    verification:
      - kind: integration
        ref: "cargo test --locked --test thread_pool_size_tests (2 passed, 0 ignored)"
        status: pass
      - kind: other
        ref: "grep -Eqi 'expected RED|intentionally red|red is .*intentional' scripts/bench/README.md (no match)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The thread-scaling gate is GREEN on 500k synthetic reads with speedup_t4 and speedup_t16 both at least 1.3"
    requirement: PAR-01
    verification:
      - kind: integration
        ref: "python3 scripts/bench/thread_scaling.py --mode synthetic --reads 500000 --reps 3 (exit 0, GREEN 1.8118/1.4372)"
        status: pass
    human_judgment: false
  - id: D4
    description: "True t1 baselines recorded with provenance: synthetic 18.77 s and real 4M-read slice 142.54 s"
    requirement: PAR-01
    verification:
      - kind: integration
        ref: "python3 scripts/bench/thread_scaling.py --mode slice --slice-reads 4000000 --reps 1 --measure-only (exit 0)"
        status: pass
      - kind: other
        ref: "bench.validate_schema + validate_provenance over both JSON documents"
        status: pass
    human_judgment: false

duration: 31 min
completed: 2026-11-12
status: complete
---

# Phase 06 Plan 01: Working --threads & True t1 Baseline Summary

**`--threads` now sizes the rayon pool through a lazy `available_parallelism` fallback: fresh children observe exactly 2/5/17 threads at `--threads 1/4/16`, the Phase 5 pool-size and scaling gates are green, and true single-thread baselines are recorded (synthetic 18.77 s; 4M-read real slice 142.54 s).**

## Performance

- **Duration:** 31 min
- **Started:** 2026-11-12T11:35:02Z
- **Completed:** 2026-11-12T12:06:42Z
- **Tasks:** 3
- **Files modified:** 7 (5 modified, 2 created)

## Accomplishments

- `resolve_thread_count` no longer calls `rayon::current_num_threads()`: the all-cores fallback is `std::thread::available_parallelism()`, so the default pool is not eagerly initialized before `build_global(num_threads(resolved))` runs. The precedence chain and all 7 unit tests are unchanged.
- The PROF-02 pool-size standing gate runs in the default suite (0 ignored) and observes exactly requested + 1 threads for N in {1, 4, 16}; the old bug-pinning characterization is replaced by a fixed-behavior characterization at `--threads 1`.
- The thread-scaling gate is GREEN: `speedup_t4 = 1.8118`, `speedup_t16 = 1.4372` (threshold 1.3), identical nonzero counts 64,999,000 unique / 65,000,000 total across t1/t4/t16.
- The true single-thread baselines plan 06-04 consumes are recorded with provenance: synthetic 500k-read t1 = 18.77 s, and the real 4M-read head slice t1 = 142.54 s (t4 59.61 s, t16 69.40 s; counts 229,694,874 / 519,271,168, slice sha256 `71c6264b…` — the same slice as Phase 5).
- The Phase 5 RED baseline `thread_scaling_baseline.json` is byte-for-byte unchanged (sha256 `5d7c4466…` verified before and after).
- Full verification stayed green: `cargo test --locked` exit 0, MSRV 1.82 clippy exit 0 on both crates, benchmark harness suite 304 tests OK (skipped=1).

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end --threads sizes the rayon pool** - `3d23941` (fix) — includes the Rule 1 observer-parser fix and its tests
2. **Task 2: Flip the pool-size standing gate and characterization** - `61edf8b` (test)
3. **Task 3: GREEN scaling gate + true t1 baselines** - `f850035` (feat)

**Plan metadata:** (docs commit created after this summary)

## Files Created/Modified

- `src/cli/commands/count.rs` — lazy `available_parallelism` fallback; resolver doc comment rewritten; `build_global` still runs before any rayon parallel work.
- `tests/thread_pool_size_tests.rs` — ignore removed; standing gate active; characterization inverted to `observed == requested + 1` at `--threads 1`; module doc rewritten as standing-gate documentation.
- `scripts/bench/README.md` — "Expected RED gates" section replaced by "Standing thread gates"; current-tense intentional-red wording removed; error-softening prohibition retained.
- `.planning/research/profiling/verify_threads.py` — counts unique thread ids in `sample` output (Rule 1 fix; see deviations).
- `scripts/bench/tests/test_verify_threads.py` — two parser unit tests for duplicate/distinct thread ids.
- `.planning/phases/06-parallelism-correctness-hot-path/thread_scaling_par01_green.json` — schema-valid, provenance-bearing GREEN scaling document (synthetic, 3 reps) with the true t1 baseline.
- `.planning/phases/06-parallelism-correctness-hot-path/thread_scaling_par01_slice.json` — measure-only real-slice baseline at the same 4M-read scope as Phase 5.

## Verify Evidence

- `verify_threads.py --threads 1 4 16` (release): `requested=1 observed=2`, `requested=4 observed=5`, `requested=16 observed=17`, `THREAD REALITY verdict=GREEN`, exit 0. `grep current_num_threads src/cli/commands/count.rs` → no match.
- `cargo test --locked --lib cli::commands::count::tests` → 7 passed.
- `cargo test --locked --test thread_pool_size_tests` → 2 passed, 0 failed, 0 ignored.
- Synthetic scaling doc: `validate_schema`/`validate_provenance` pass; arms `rk21-t1 18.77 s`, `rk21-t4 10.36 s`, `rk21-t16 13.06 s`; binary sha256 `953bf0e0…`; git commit `61edf8b…`; `git_dirty: true` (untracked generated inputs were present during the run; the source tree itself matched the commit).
- Slice doc: `validate_schema`/`validate_provenance` pass; `params.input` = `/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/CRR1936095_r1.part_001.fq.gz`; `params.slice_reads` = 4000000; t1 median 142.54 s > 0; no verdict block (measure-only).
- Phase 5 baseline integrity: `shasum -a 256 -c` → OK.
- Full suite: `cargo test --locked` exit 0 (24 test-result-ok groups; thread_pool_size_tests 2 passed); `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` exit 0 for root and pyo3; harness `python3 -m unittest discover -s scripts/bench/tests -t .` → Ran 304 tests, OK (skipped=1).

## Decisions Made

- The all-cores fallback must be computed without any rayon call: `available_parallelism` is the only correct source because a rayon query permanently initializes the default pool and makes `build_global` fail silently.
- The characterization test now pins the fixed contract rather than the bug, with a single-core-host skip because the fixed pool and the old default coincide there.
- Generated measurement inputs/slices/`.rkdb` files were deleted after capture; the JSON fingerprints and provenance are the durable evidence (same practice as Phase 5).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `verify_threads.py` double-counted the main thread**
- **Found during:** Task 1 (pool-size observation)
- **Issue:** A fresh rebuild made macOS `sample` emit both a `Thread_<tid>: Main Thread` call-graph summary header and the regular `Thread_<tid> …` section header for the same main thread. The helper counted matching lines, so `--threads 1` intermittently observed 3 threads (2 workers + main) and the gate failed right after `cargo build` (reproduced 4/4).
- **Fix:** Count unique thread ids via `THREAD_ID_RE = r"^\s*\d+\s+Thread_(\d+)"` and a pure `parse_thread_count()`; added two parser unit tests. The JSON contract, exit codes, and verdict line are unchanged.
- **Files modified:** `.planning/research/profiling/verify_threads.py`, `scripts/bench/tests/test_verify_threads.py`
- **Verification:** `THREAD REALITY verdict=GREEN` in repeated runs including immediately after a rebuild; helper unit suite 6/6; Task 1 verify chain exit 0.
- **Committed in:** `3d23941` (Task 1 commit)

**Total deviations:** 1 auto-fixed (1 bug).
**Impact on plan:** Required for the gate to be honest and non-flaky; no production counting/output behavior changed. The plan's `files_modified` list did not name the observer, so the extra two files are surfaced here.

## Issues Encountered

- The observer flakiness was diagnosed by sampling thread names live: the duplicate was the same tid under a summary header, not a second OS thread. Loading the owner with 2 workers should no longer reproduce.
- Both evidence documents honestly record `git_dirty: true` because generated measurement inputs existed in the phase directory during the runs; the source tree matched commit `61edf8b`, and the recorded binary sha256 `953bf0e0…` is the artifact that produced the numbers.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Threat Flags

None. The plan's threat model items are satisfied: T-06-01 (lazy fallback + build_global ordering + fresh-subprocess gate), T-06-SC (no dependency changes; all builds used `--locked`). No new network endpoints, auth paths, or schema changes.

## Next Phase Readiness

- Plan 06-02 (thread-local counters) and 06-03 (rolling encoder) can rely on working, observable thread control.
- Plan 06-04 consumes `thread_scaling_par01_green.json` (synthetic t1 = 18.77 s) and `thread_scaling_par01_slice.json` (slice t1 = 142.54 s, `params.input`/`slice_reads` recorded) for strict post-change t1 comparison; it must not recapture these baselines.
- The Phase 5 RED baseline remains the historical record and must stay untouched.

---

*Phase: 06-parallelism-correctness-hot-path*
*Completed: 2026-11-12*

## Self-Check: PASSED

- `thread_scaling_par01_green.json` — FOUND, schema/provenance valid, verdict GREEN.
- `thread_scaling_par01_slice.json` — FOUND, schema/provenance valid, t1 median 142.54 s.
- `06-01-SUMMARY.md` — FOUND.
- Commits `3d23941`, `61edf8b`, `f850035` — all ancestors of HEAD.
- Pool-size records `(1,2), (4,5), (16,17)` — observed = requested + 1.
- Phase 5 `thread_scaling_baseline.json` — sha256 verified unchanged.

