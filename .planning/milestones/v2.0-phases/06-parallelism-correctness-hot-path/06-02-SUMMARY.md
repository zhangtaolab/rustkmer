---
phase: 06-parallelism-correctness-hot-path
plan: 02
subsystem: counting/hot-path
tags: [thread-local, reduction, rayon, overflow, pyo3, par-02, differential]

requires:
  - phase: 06-parallelism-correctness-hot-path
    plan: 01
    provides: "working --threads (2/5/17 observed at 1/4/16), true t1 baselines (synthetic 18.77 s / real slice 142.54 s)"
  - phase: 05-measurement-regression-harness
    provides: "contention_evidence.json: 120.22 ns/window attributed to per-window total_kmers/unique_kmers atomics"
provides:
  - "LocalKmerCounts: per-worker dense u64 / wide u128 accumulator with verbatim u32 overflow semantics"
  - "KmerCounter thread-local handle registry with generation-based drain (fresh locals after every reduction)"
  - "KmerCounter::new_local_counts / local_handle / local_skipped / merge_local_counts / reduce_local_counts"
  - "CLI hot loop accumulates in locals and reduces checked once per file; count.rs has no shared increment call"
  - "PyCounter file methods accumulate in one local per call and merge once under py.detach"
  - "Differential suite: 1-vs-N, old-vs-new, multi-file CLI sum, overflow, unique, conservation"
affects: [06-03, 06-04, 07, 09]

actuals:
  tokens: 20022
  tasks: 3
  commits: 5
  plan_head_before: 6897df7dd79dd85050eefe643534120549aaf060
  plan_head_after: 532133a4f1fafe8317927117f7dcf724d7e4bf5c

tech-stack:
  added: []
  patterns:
    - "Per-worker thread-local accumulator with a lock-free TLS fast path keyed by a unique counter id + generation"
    - "End-of-file reduction as an explicit checked summation site (checked_add per key and for the shared u64 total)"
    - "par_chunks + try_for_each_init: one local lock per record sub-slice, never per k-mer window"
    - "Generation bump on drain makes a reused drained local impossible (multi-file exactness)"

key-files:
  created:
    - "src/hash/local.rs"
    - "tests/thread_local_count_tests.rs"
    - ".planning/phases/06-parallelism-correctness-hot-path/deferred-items.md"
  modified:
    - "src/hash/mod.rs"
    - "src/hash/table.rs"
    - "src/cli/commands/count.rs"
    - "pyo3/src/counter.rs"
    - "pyo3/tests/test_counter.py"

key-decisions:
  - "LocalTable uses hashbrown (AHash) dense u64 / wide u128 maps: cache-resident per worker and materially cheaper to hash than std SipHash"
  - "The handle registry is keyed by a unique counter id (never the address, which can be reused) and stores a generation; drain bumps the generation so stale TLS entries can never be reused or double-counted"
  - "reduce_local_counts replaces each drained local with an empty table (release) so per-file memory is returned before the next file"
  - "merge_local_counts publishes atomics from the merged deltas (not local.total) so a mid-loop overflow leaves a poison-consistent counter, matching merge's WR-02 contract"
  - "seed_count keeps the local total/unique coherent so ceiling-seeded tests exercise the real reduction invariants"

patterns-established:
  - "Hot-path accumulation pattern: per-worker local + explicit checked end-of-file reduction, with the command/FFI layer never touching shared per-window state"
  - "Generation-guarded TLS registry pattern: fast lock-free lookup, generation bump on drain, fresh local on the next handle request"
  - "Proving removal: grep the shared call out of the command layer + differential maps + overflow tests (the shared increment's atomics live only in table.rs)"

requirements-completed: [PAR-02]

coverage:
  - id: D1
    description: "CLI counting accumulates in per-worker thread-local tables and reduces once per file; the hot loop contains no shared per-window increment"
    requirement: PAR-02
    verification:
      - kind: integration
        ref: "cargo test --locked --test thread_local_count_tests (9 passed)"
        status: pass
      - kind: other
        ref: "! grep -q 'counter.increment(' src/cli/commands/count.rs (absent)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The end reduction uses checked u32 arithmetic and returns the verbatim fail-loud overflow message; failed increments do not advance totals"
    requirement: PAR-02
    verification:
      - kind: unit
        ref: "cargo test --locked --lib hash::table (17 passed, incl. failed_local_merge_reports_error_and_keeps_partial_atomics_consistent)"
        status: pass
      - kind: integration
        ref: "tests/thread_local_count_tests.rs#local_increment_at_u32_ceiling_is_verbatim_and_does_not_advance_total; #merge_overflow_is_verbatim_and_never_wraps_or_saturates"
        status: pass
    human_judgment: false
  - id: D3
    description: "Local-path maps equal the old per-window maps and the 1-vs-N maps across k in {21,32,64} x canonical on/off; a combined multi-file CLI run equals the elementwise sum of per-file runs"
    requirement: PAR-02
    verification:
      - kind: integration
        ref: "tests/thread_local_count_tests.rs#old_vs_new_maps_are_identical_across_the_matrix; #one_vs_n_local_maps_are_identical_across_the_matrix"
        status: pass
      - kind: e2e
        ref: "tests/thread_local_count_tests.rs#multi_file_local_reduction_matches_per_file_sum (real CARGO_BIN_EXE_rustkmer, two FASTQ inputs)"
        status: pass
      - kind: other
        ref: "python3 scripts/bench/bench.py --mode synthetic --reads 20000 --parity-only (PARITY OK distinct=2400000 total=2400000; validate_provenance OK)"
        status: pass
    human_judgment: false
  - id: D4
    description: "PyCounter file methods accumulate through the same local core with py.detach and owned Send captures, public API unchanged"
    requirement: PAR-02
    verification:
      - kind: integration
        ref: "maturin develop --release + assert PyCounter importable + python -m pytest pyo3/tests/test_counter.py -q (93 passed)"
        status: pass
    human_judgment: false

duration: 10 min
completed: 2026-11-12
status: complete
---

# Phase 06 Plan 02: Thread-Local Counters & Checked End Reduction Summary

**The CLI hot loop now accumulates into per-worker `LocalKmerCounts` tables and reduces them once per file with checked `u32` sums: `count.rs` contains no shared increment, k×canonical count maps are identical to the pre-change path in both 1-vs-N and multi-file runs, overflow fails loud with the verbatim message, and PyCounter inherits the change through the same core.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-11-12T12:12:46Z
- **Completed:** 2026-11-12T12:22:57Z
- **Tasks:** 3
- **Files modified:** 7 (4 source/test + 3 task-created, including the deferred-items note)

## Accomplishments

- **PAR-02 core.** Added `LocalKmerCounts` (`src/hash/local.rs`): dense `hashbrown::HashMap<u64,u32>` for k ≤ 32, wide `u128` map for 33..=64, reproducing the shared counter's per-key semantics exactly (verbatim `K-mer count overflow reached maximum value 4294967295`, successful-increment totals per WR-03, fresh-key unique accounting, local skipped-window counter).
- **Thread-local handle registry.** Each `KmerCounter` owns a registry keyed by a globally unique counter id; each rayon worker's TLS cache resolves in one lock-free lookup (counter id + generation). `drain()` bumps the generation, so a drained local can never be reused — the contract the multi-file test pins.
- **Checked reduction.** `merge_local_counts` uses `checked_add` for the per-key `u32` sum and for the shared `u64` total; on overflow it publishes the partial atomics (WR-02 poison consistency) and returns the verbatim error. `reduce_local_counts` drains, merges, and releases every local's memory before the next file.
- **CLI rewiring.** `count.rs` now uses `par_chunks(64) + try_for_each_init`: the init returns the worker's handle, the op locks once per record sub-slice and counts every record in it. Per-chunk skip warnings are derived from the summed local skip-counter delta, preserving the exact wording and one-warning-per-chunk behavior. Each file's locals are reduced before its statistics print.
- **Dual surface.** `PyCounter::add_from_fasta` / `add_from_fastq` create one local per call, accumulate through `process_sequence_into_local`, and merge once at the end under the existing `py.detach` + owned `Send` captures. `add_kmer` / `add_sequence` stay on the shared increment path; public signatures and error messages are unchanged.
- **Proof suite.** 9 integration tests: end-to-end local-vs-reference parity, width selection, fresh-local-after-reduce, the multi-file CLI elementwise-sum differential, full 1-vs-N and old-vs-new matrices (k ∈ {21,32,64} × canonical), verbatim overflow on both widths (local increment and reduction), unique/conservation, and a table.rs poison-consistency unit test.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end per-worker local accumulation + checked per-file reduction** — `0824ec3` (feat)
2. **Task 2: Prove exactness, no shared increment, and fail-loud overflow** — `bc9c89d` (test)
3. **Task 3: PyCounter file methods through the local core** — `69fa33f` (feat)

Supporting commits:

4. `d531863` (fix) — 1.82 clippy gates: TLS map type alias (`type_complexity`) and `if let` in the reference path (`single_match`)
5. `532133a` (style) — `cargo fmt` over the files this plan touched

**Plan metadata:** (docs commit created after this summary)

## Files Created/Modified

- `src/hash/local.rs` (new) — `LocalKmerCounts` + `LocalHandleRegistry` + TLS handle cache.
- `src/hash/mod.rs` — declares `local`, re-exports `LocalKmerCounts`.
- `src/hash/table.rs` — registry field, `new_local_counts` / `local_handle` / `local_skipped` / `merge_local_counts` / `reduce_local_counts`, plus the failed-merge unit test.
- `src/cli/commands/count.rs` — `count_record_into` / `count_chunk_into_locals`, `SUBSLICE_RECORDS = 64`, per-file `reduce_local_counts`, skip-delta warning accounting.
- `pyo3/src/counter.rs` — file helpers use one `LocalKmerCounts` per call + one merge; `process_sequence_into_local`.
- `pyo3/tests/test_counter.py` — 8 new parametrized parity cases against a pure-Python reference (k 21/64 × canonical, file + sequence paths, totals/unique).
- `tests/thread_local_count_tests.rs` (new) — the 9-test PAR-02 proof suite.
- `.planning/phases/06-parallelism-correctness-hot-path/deferred-items.md` — pre-existing rustfmt drift recorded (out of scope).

## Verify Evidence

- `cargo test --locked --test thread_local_count_tests` → **9 passed**, including `multi_file_local_reduction_matches_per_file_sum` (real `CARGO_BIN_EXE_rustkmer`, two FASTQ inputs, combined map == elementwise per-file sum, combined total == sum of per-file totals).
- `cargo test --locked --lib hash::table` → **17 passed** (16 pre-existing + the failed-merge poison-consistency test).
- `! grep -q 'counter.increment(' src/cli/commands/count.rs` → **absent** (the only atomics remain inside `KmerCounter::increment` in table.rs).
- `grep -q 'Warning: Skipped' src/cli/commands/count.rs` → **present** (warning wording preserved).
- `cargo build --release --locked` → OK. `python3 scripts/bench/bench.py --mode synthetic --reads 20000 --parity-only --out scripts/bench/scratch/par02_parity.json` → `PARITY OK distinct=2400000 total=2400000`; `validate_provenance` → `PAR-02 CLI parity OK`.
- `maturin develop --release --manifest-path pyo3/Cargo.toml` → rebuilt; `assert hasattr(pyrustkmer, "PyCounter")` → importable; `pytest pyo3/tests/test_counter.py -q` → **93 passed**.
- Full suite `cargo test --locked` → all groups `ok` (242 lib unit tests, 9 thread-local, 34 golden, 6 dense differential, 4 parallel count, 2 pool-size, doc-tests 8 passed / 1 ignored); exit 0.
- `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` → exit 0 for the root crate; same for `pyo3/Cargo.toml` → exit 0.
- 1-vs-N / old-vs-new matrix evidence: decoded maps equal for k ∈ {21,32,64} × canonical ∈ {true,false}; reduced shared totals/unique equal the reference.

## Decisions Made

- Local maps use `hashbrown`'s default AHash builder (already a project dependency) rather than `std`'s SipHash: this is the hot path and the per-worker table is cache-resident.
- The handle fast path is lock-free (TLS + atomic generation); only a miss takes the registry mutex. This keeps `try_for_each_init` cheap enough that the lock is taken once per record sub-slice, not per record.
- `merge_local_counts` accumulates shared atomics from successfully merged per-key deltas rather than `local.total_kmers()`, so a mid-loop overflow leaves a counter whose stats match its partial table (WR-02 parity with `merge`).
- `seed_count` advances the local total and unique so tests that seed at `u32::MAX` still exercise the same invariant the production path upholds.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 1.82 clippy gates failed on the new code**
- **Found during:** Overall verification (after Task 3 tests)
- **Issue:** `clippy::type_complexity` on the TLS map declared inline in `src/hash/local.rs`, and `clippy::single_match` on the reference-path `match` in `tests/thread_local_count_tests.rs`.
- **Fix:** Added `WorkerLocalHandle` / `WorkerLocalMap` type aliases and rewrote the reference match as `if let Ok(..)`. Behavior unchanged.
- **Files modified:** `src/hash/local.rs`, `tests/thread_local_count_tests.rs`
- **Commit:** `d531863`

**2. [Rule 1 - Style/CI] `cargo fmt --check` drift in plan-touched files**
- **Found during:** Overall verification
- **Issue:** The newly written code was not rustfmt-formatted.
- **Fix:** Ran `cargo fmt`; reverted the one unrelated pre-existing file it also touched (`src/database/prefix_cache_merge.rs`) and logged that drift plus the pre-existing `pyo3/src/counter.rs:197` drift to `deferred-items.md`.
- **Files modified (committed):** the four plan files
- **Commit:** `532133a`

### Environment accommodations

- The plan's Task 3 verify command sets `VIRTUAL_ENV` but the ambient shell also exports `CONDA_PREFIX`; maturin refuses to run with both set. The command was executed as `env -u CONDA_PREFIX VIRTUAL_ENV=... PATH=... maturin ...`. No code or API impact.

**Total deviations:** 2 auto-fixed (1 blocking lint, 1 formatting) + 1 environment accommodation. No plan-intent deviation.

## Issues Encountered

- **Peak-RSS recording for T-06-05** is not part of this plan's tasks/verify; the memory mitigation implemented here is reduce-and-release per file plus the 8192-entry per-worker capacity hint. Peak-RSS measurement lands with plan 06-04's performance measurement.
- `cargo fmt --check` is not clean at HEAD for two pre-existing, untouched files (`src/database/prefix_cache_merge.rs`, `pyo3/src/counter.rs`); recorded in `deferred-items.md` rather than fixed out of scope.

## User Setup Required

None - no external service configuration required. (The local `.venv311` + maturin toolchain already existed.)

## Known Stubs

None.

## Threat Flags

None. The plan's threat model is satisfied: T-06-03 (per-worker isolation + entry-API merge + 1-vs-N/old-vs-new differentials), T-06-04 (checked `u32`/`u64` arithmetic with the verbatim error; ceiling-seeded tests; no saturating/wrapping in the reduction), T-06-05 (per-file reduce + release; capacity hint), T-06-06 (`py.detach` + owned `Send` captures only; rebuild + import-capability assert), T-06-SC (no dependency changes; all builds `--locked`). No new network endpoints, auth paths, or schema changes.

## Next Phase Readiness

- Plan 06-03 (rolling encoder) can build on the local accumulator: `count_record_into` is the single per-record site to swap to the rolling encoder, and the differential suite already proves the surrounding accumulation/reduction is exact.
- Plan 06-04 can reuse `thread_local_count_tests` as the correctness gate while measuring the t1 win against the 06-01 baselines (18.77 s synthetic / 142.54 s slice). Peak RSS must be recorded there for T-06-05's full mitigation evidence.
- Phase 7 can lift `LocalKmerCounts` / the handle registry into the persistent-worker engine; the CLI/PyO3 wiring is intentionally thin so the engine swap is localized.

---

*Phase: 06-parallelism-correctness-hot-path*
*Completed: 2026-11-12*

## Self-Check: PASSED
