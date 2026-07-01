---
phase: 02-parallel-counting
plan: 05
subsystem: testing
tags: [rust, python, testing, differential, correctness, concurrency, pcoount-04]
requires:
  - "src/hash/table.rs (POST-02-02 DashMap-backed KmerCounter — the code under test)"
  - "src/cli/commands/count.rs (resolve_thread_count_from — the pure D-07 precedence resolver exercised by test_thread_resolution)"
  - "pyo3/src/counter.rs (POST-02-03 PyCounter with threads kwarg + py.detach GIL release — the code under test)"
  - "tests/fixtures/parallel_count_baseline/*.json (the 6 committed pre-refactor baselines captured by 02-04 — the D-10 ground truth baseline_matches_current asserts against)"
  - "tests/parallel_count_tests.rs (the 02-04 scaffold: BASELINE_INPUT, all_cells D-13 matrix, count_input_to_map helper, #[ignore]d capture generator + 3 #[ignore]d differential stubs)"
provides:
  - "tests/parallel_count_tests.rs (PCOUNT-04 gate GREEN: 4 UN-ignored asserting tests — differential_threads_1_vs_n, baseline_matches_current, deterministic_sorted_output, test_thread_resolution)"
  - "pyo3/tests/test_counter.py extended with TestPyCounterThreads + TestPyCounterParallel (PCOUNT-03 gate GREEN at the Python layer)"
affects:
  - "Phase 02 acceptance — this plan is the correctness gate proving parallel counting == sequential counting"
tech-stack:
  added: []
  patterns:
    - "1-vs-N commutativity differential via std::thread::scope + Arc<KmerCounter> (bypasses build_global's one-call-per-process limit; exercises the exact DashMap atomicity path the CLI's rayon workers rely on)"
    - "D-10 baseline-vs-current: deserialize committed JSON as BTreeMap<String,u32>, parse stringified u128 keys back to u128, assert equality with current single-threaded count map"
    - "D-09 determinism: count twice with separate KmerCounter instances, apply default-sort, assert byte-identical sorted Vec — guards against sharded DashMap iteration non-determinism leaking into output"
    - "PCOUNT-01 precedence: test the pure resolve_thread_count_from helper with Option params (no env::set_var — CONCERNS.md unsafe soundness mitigation)"
    - "PCOUNT-03 Python differential: PyCounter.get_all_counts() returns dict[str,int] (order-independent), compare threads=1 vs threads=N count maps"
key-files:
  created:
    - .planning/phases/02-parallel-counting/02-05-SUMMARY.md
  modified:
    - tests/parallel_count_tests.rs
    - pyo3/tests/test_counter.py
    - src/cli/commands/count.rs
decisions:
  - "Make resolve_thread_count_from pub in src/cli/commands/count.rs (was private fn) so the integration test binary can call it directly. One-line visibility change authorized by plan 02-05 Task 1 action (d). The env-reading wrapper resolve_thread_count stays private. This is a minimal scope expansion beyond files_modified (the plan's action explicitly sanctions it)."
  - "Drive the 1-vs-N differential via std::thread::scope against a shared Arc<KmerCounter> rather than via CLI subprocess with different --threads values. build_global is one-call-per-process (rayon returns Err on a second ThreadPoolBuilder::build_global), so a single test process cannot drive two different pool configs through execute_count. The thread::scope approach exercises the exact same DashMap sharded entry().and_modify().or_insert_with() atomicity path the CLI's rayon workers rely on, making it a real commutativity differential rather than a subprocess approximation."
  - "Use PyCounter.get_all_counts() (dict[str,int]) for the Python parallel differential rather than a save_database + PyDatabase read-back round trip. get_all_counts returns a native dict which is order-independent by construction, and avoids the PyDatabase.get_all_kmers() API which returns Vec<HashMap<String,String>> with hex-encoded kmers (awkward to canonicalize). get_all_counts decodes kmers to strings and is the natural comparison type."
metrics:
  duration: ~25min
  completed: 2026-07-01
  tasks: 2
  files: 3
status: complete
---

# Phase 02 Plan 05: PCOUNT-04 Correctness Gate Summary

Filled in the differential correctness tests scaffolded by 02-04 and extended pyo3/tests/test_counter.py for the PyCounter threads kwarg — the PCOUNT-04 gate proving parallel counting produces results identical to sequential (commutativity differential), post-refactor counts match the committed pre-refactor baselines (D-10), output is deterministic run-to-run (D-09), the thread-resolution precedence chain works (PCOUNT-01), and PyCounter inherits the parallel speedup with identical counts (PCOUNT-03).

## What Was Built

### `tests/parallel_count_tests.rs` — 4 UN-ignored asserting tests (PCOUNT-04 gate GREEN)

- **`differential_threads_1_vs_n`** (PCOUNT-04): iterates the D-13 matrix (k in {21,32,64} x canonical {true,false}). For each cell, counts the fixed deterministic `BASELINE_INPUT` with 1 worker and with N=num_cpus workers via `count_input_with_workers`, and asserts the two `BTreeMap<u128,u32>` are equal. Any divergence fails with a cell-specific message. The 1-vs-N parallelism is driven at the unit level via `std::thread::scope` against one shared `Arc<KmerCounter>` (DashMap gives interior mutability) — `build_global` is one-call-per-process so a single test process cannot drive two pool configs through `execute_count`. The thread::scope approach exercises the exact same `entry().and_modify().or_insert_with()` atomicity path the CLI's rayon workers rely on.

- **`baseline_matches_current`** (D-10): for each D-13 cell, deserializes the committed pre-refactor JSON from `tests/fixtures/parallel_count_baseline/k{k}_{canon|noncanon}.json` via `serde_json::from_str::<BTreeMap<String,u32>>()`, parses the stringified u128 keys back to u128, and asserts equality with the current single-threaded count map. Catches any count drift introduced by the DashMap swap.

- **`deterministic_sorted_output`** (D-09): counts the fixed input twice with two independent `KmerCounter` instances (two independent sharded-iteration orderings), applies the default-sort path (sort by kmer key, mirroring `count.rs::output_binary_format`), and asserts the two sorted `Vec<(u128,u32)>` are byte-identical. Guards against sharded DashMap iteration non-determinism leaking into output.

- **`test_thread_resolution`** (PCOUNT-01): exercises the pure `resolve_thread_count_from` helper across the full D-07 precedence chain (`--threads > RUSTKMER_THREADS > RAYON_NUM_THREADS > num_cpus`) without env mutation (CONCERNS.md unsafe soundness mitigation). Asserts each tier wins when higher tiers are unset, that `--threads 0` falls through (does not panic), and that `num_cpus=0` clamps to 1.

The `capture_parallel_count_baseline` generator STAYS `#[ignore]`d (run-once; the committed baselines are read-only ground truth per T-02-04).

### `src/cli/commands/count.rs` — one-line visibility change

`resolve_thread_count_from` changed from `fn` (private) to `pub fn` so the integration test binary (`tests/parallel_count_tests.rs` is a separate crate) can call it directly. The env-reading wrapper `resolve_thread_count` stays private. Authorized by plan 02-05 Task 1 action (d); the 7 existing unit tests inside `count.rs` continue to pass unchanged.

### `pyo3/tests/test_counter.py` — TestPyCounterThreads + TestPyCounterParallel (PCOUNT-03 GREEN)

- **`TestPyCounterThreads`**:
  - `test_create_counter_with_threads`: `PyCounter(21, canonical=True, threads=4)` constructs; `.kmer_length == 21`.
  - `test_threads_none_uses_all_cores`: `threads=None` (default) constructs without error.
  - `test_threads_zero_rejected`: `threads=0` raises `ValueError` matching `"Invalid thread count"` (T-02-13 validation).

- **`TestPyCounterParallel::test_parallel_counts_match_sequential`**: writes a small deterministic FASTQ fixture (4 reads of ACGT, k=21), counts it with `threads=1` and `threads=4`, and compares the resulting count maps via `PyCounter.get_all_counts()` (returns `dict[str,int]` — order-independent, so sharded DashMap iteration order cannot flake it). Any divergence is, by construction, a concurrency bug.

All new tests use the existing module-level `try: import pyrustkmer / except ImportError: pytest.skip(...)` guard (no duplicate guard added). Google-style docstrings, line length <= 88 (black-compliant per `pyproject.toml`).

## How to Run

```bash
# The PCOUNT-04 gate (4 differential tests; capture generator ignored):
cargo test --test parallel_count_tests

# FOUND-01 clippy gates:
cargo clippy --tests -- -D warnings            # root
(cd pyo3 && cargo clippy -- -D warnings)       # pyo3

# PCOUNT-03 gate (Python layer):
maturin develop --release -m pyo3/Cargo.toml
python -m pytest pyo3/tests/test_counter.py -v

# Full root regression:
cargo test
```

## Verification Results

- `cargo test --test parallel_count_tests` — **4 passed, 0 failed, 1 ignored** (capture generator). THE PCOUNT-04 GATE GOING GREEN.
- `baseline_matches_current` passes against all 6 committed JSON baselines (D-10 honored — post-refactor DashMap counts == pre-refactor ground truth).
- `differential_threads_1_vs_n` passes across the full D-13 matrix (1-worker count map == N-worker count map for k in {21,32,64} x canonical {true,false}).
- `cargo clippy --tests -- -D warnings` (root) — green.
- `(cd pyo3 && cargo clippy -- -D warnings)` — green.
- `cargo test` (full root) — **307 passed, 0 failed, 3 ignored** (no regressions).
- `maturin develop --release -m pyo3/Cargo.toml` — extension builds with 02-03 changes.
- `python -m pytest pyo3/tests/test_counter.py` — **81 passed** (including the 4 new PCOUNT-03 tests). Coverage 100%, above the 80% gate.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] BASELINE_INPUT T-run off-by-one introduced during file rewrite**
- **Found during:** Task 1 (first test run)
- **Issue:** When rewriting `tests/parallel_count_tests.rs` with `Write`, the T-run line (line 2 of the `BASELINE_INPUT` literal) was transcribed with 67 `T` characters instead of the 68 in the 02-04 committed version. This caused `baseline_matches_current` to fail spuriously: the all-T kmer window count dropped from 48 (68-21+1) to 47 (67-21+1), making kmer `0` (canonical form of all-T) mismatch the committed baseline.
- **Fix:** Restored the exact 02-04 T-line (68 `T`s). The fix was verified by re-running `baseline_matches_current` (passed) and by regenerating the baseline into a scratch dir and diffing (byte-identical to committed).
- **Files modified:** tests/parallel_count_tests.rs (BASELINE_INPUT literal)
- **Commit:** d608939

**2. [Rule 3 - Blocking issue] Made resolve_thread_count_from pub in src/cli/commands/count.rs**
- **Found during:** Task 1 (test_thread_resolution implementation)
- **Issue:** `resolve_thread_count_from` is a free function in `src/cli/commands/count.rs` but was declared `fn` (private). Integration test binaries (`tests/*.rs`) are separate crates, so a private/free function is unreachable from `tests/parallel_count_tests.rs`. The plan's Task 1 action (d) explicitly anticipated this: "make it `pub(crate)`/`pub` if needed for the test." (`pub(crate)` is insufficient because integration tests are external crates — `pub` is required.)
- **Fix:** Changed `fn resolve_thread_count_from` to `pub fn resolve_thread_count_from`. One-line visibility change. The env-reading wrapper `resolve_thread_count` stays private. The 7 existing unit tests inside `count.rs` continue to pass unchanged.
- **Files modified:** src/cli/commands/count.rs (one-line visibility change; outside the nominal files_modified scope but explicitly authorized by the plan's action)
- **Commit:** d608939

### Decisions Made

**Drive the 1-vs-N differential via std::thread::scope, not CLI subprocess**
The plan's phase-critical-reminders section specifies this approach: `build_global` is one-call-per-process, so driving two different `--threads` values through `execute_count` in a single test process is impossible (the second `build_global` returns `Err`). Instead, `count_input_with_workers` spawns N `std::thread::scope` threads each running the encode/canonicalize/increment loop over a disjoint slice of the input windows, sharing one `Arc<KmerCounter>`. DashMap's sharded `entry().and_modify().or_insert_with()` is the exact atomicity path the CLI's rayon workers rely on, so this is a real commutativity differential, not a subprocess approximation. The N=1 case spawns a single thread (or runs sequentially when `total_windows < workers`).

**Use PyCounter.get_all_counts() for the Python parallel differential**
`PyCounter.get_all_counts()` returns `dict[str, int]` mapping decoded kmer strings to counts — order-independent by construction (Python dict equality ignores insertion order in the equality sense). This is the natural comparison type and avoids the `PyDatabase.get_all_kmers()` round trip (which returns `Vec<HashMap<String, String>>` with hex-encoded kmers and stringified counts, awkward to canonicalize for an order-independent comparison). Using the counter's own accessor also tests the real code path users hit.

## TDD Gate Compliance

This plan's tasks are marked `tdd="true"` in the frontmatter, but the work is test-only (no production feature implemented — the DashMap core landed in 02-02 and PyCounter in 02-03). The tests ARE the artifact; the "GREEN" gate (implementation passing the tests) is satisfied by the already-landed 02-02/02-03 production code, which these tests now prove correct.

Git log gate sequence for this plan:
1. `test(02-05): fill in PCOUNT-04 differential gate + D-10/D-09/PCOUNT-01 tests` (d608939) — the four Rust differential tests un-ignored and asserting; PCOUNT-04 gate GREEN.
2. `test(02-05): add PyCounter threads-kwarg + parallel differential tests` (cfd354c) — the four Python tests + TestPyCounterParallel; PCOUNT-03 gate GREEN at the Python layer.

No separate `feat(02-05)` commit because no production feature was implemented in this plan — the deliverable is the proving test suite. The "GREEN" gate is the already-landed 02-02/02-03 code passing these new tests.

## Threat Flags

None. The files modified are test files (read committed JSON baselines as ground truth, write no new trust boundaries) plus a one-line visibility change to an existing helper (`resolve_thread_count_from: fn -> pub fn`). No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries were introduced. The plan's threat register (T-02-14 differential strength, T-02-15 env::set_var avoidance, T-02-16 deterministic input) is fully mitigated: the differential uses exact `BTreeMap` equality with cell-specific failure messages; `test_thread_resolution` tests the pure helper without env mutation; the input is a compile-time `&str`.

## Known Stubs

None. All four Rust differential tests and all four Python tests make real assertions and PASS. The `capture_parallel_count_baseline` generator is intentionally `#[ignore]`d (run-once; the committed baselines are read-only ground truth per T-02-04) — this is the designed lifecycle, not a stub.

## Self-Check: PASSED

- `tests/parallel_count_tests.rs` — FOUND (4 un-ignored asserting test fns + 1 ignored capture generator).
- `pyo3/tests/test_counter.py` — FOUND (4 new test fns + TestPyCounterThreads + TestPyCounterParallel classes).
- `src/cli/commands/count.rs` — FOUND (`resolve_thread_count_from` now `pub fn`).
- Commit `d608939` — FOUND in git log.
- Commit `cfd354c` — FOUND in git log.
- `.planning/phases/02-parallel-counting/02-05-SUMMARY.md` — created by this write.
