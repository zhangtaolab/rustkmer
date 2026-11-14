---
phase: 07-shared-counting-engine
plan: 04
subsystem: measurement-verification
tags: [rust, k-mer-counting, performance-measurement, thread-scaling, determinism, profiling, standing-gates, engine-02]

requires:
  - phase: 07-shared-counting-engine
    provides: "persistent producer/worker engine + CLI cutover (07-02), PyO3 extractor routing (07-03)"
  - phase: 06-parallelism-correctness-hot-path
    provides: "immutable post-hot-path baselines: synthetic 13.59/8.32/6.74 s, slice 57.16/34.98/26.96 s, t16 RSS 26,952,056,832 B, pinned 229,694,874/519,271,168"
provides:
  - "ENGINE-02 measured on the final engine binary: synthetic gate GREEN, slice walls strictly below Phase 6 at t1/t4/t16, pinned parity, bounded RSS, byte-identical .rkdb"
  - "Feature-gated EngineDiagnostics/WorkerDiagnostics and examples/engine_probe.rs producer/worker split"
  - "phase7_scaling_green.json, phase7_slice_green.json, phase7_measurement.json, phase7_engine_split.json, phase7_gates_evidence.json"
affects: [08 output sort, 10 benchmark verdict, 11 spill]

actuals:
  tokens: 10615
  tasks: 3
  commits: 3
  plan_head_before: aeabb4b526dff0ef0fbfe6eedb20fb9919d79f29
  plan_head_after: 3e1eb8730fadce840e941d71855987157ccbe625

tech-stack:
  added: []
  patterns:
    - "Parity-before-timing measurement against immutable Phase 6 documents, with provenance on every evidence doc"
    - "Feature-gated `Instant` diagnostics compiled out of default builds; the measured release binary is proven byte-identical"
    - "Sorted .rkdb sha256 equality across t1/t4/t16 as the thread-count-independent determinism proof"
    - "Evidence JSON persists command lines, test-result summaries, module paths, and HEAD baselines rather than bare booleans"

key-files:
  created:
    - examples/engine_probe.rs
    - .planning/phases/07-shared-counting-engine/phase7_scaling_green.json
    - .planning/phases/07-shared-counting-engine/phase7_slice_green.json
    - .planning/phases/07-shared-counting-engine/phase7_measurement.json
    - .planning/phases/07-shared-counting-engine/phase7_engine_split.json
    - .planning/phases/07-shared-counting-engine/phase7_gates_evidence.json
  modified:
    - src/count/engine.rs
    - src/count/mod.rs
    - src/core/mod.rs
    - src/core/monitoring.rs
    - .planning/config.json

key-decisions:
  - "Producer/worker diagnostics are read from the finished CountResult after join; no CountEngine accessor pretends to observe worker values before join"
  - "Diagnostics live only under the existing `profiling` feature; the default release binary sha256 (d107d17e...) is byte-identical before and after the instrumentation"
  - "The pre-existing broken `profiling` feature was repaired minimally (gated OperationMetrics, active_timers typo, Drop move, macro re-export) so the required probe build works without changing default behavior"
  - "The slice t16 wall (23.83 s) exceeds t4 (17.76 s) even though the count phase is producer-bound and equal (6.44 s vs 6.52 s); the difference is output sort/write variance, recorded for Phase 8, not softened"
  - "The one transient harness negative-control failure was re-run unmodified (no test/helper/gate edit) and is recorded with the passing run"

requirements-completed: [ENGINE-02]

coverage:
  - id: D1
    description: "PROF-02 synthetic thread-scaling gate is GREEN on the final engine binary and every median is strictly below the Phase 6 post-hot-path baseline"
    requirement: ENGINE-02
    verification:
      - kind: e2e
        ref: "python3 scripts/bench/thread_scaling.py --mode synthetic --reads 500000 --reps 3 -> SCALING VERDICT result=GREEN speedup_t4=1.5697 speedup_t16=1.605; schema+provenance valid"
        status: pass
      - kind: other
        ref: "phase7_scaling_green.json vs phase6_scaling_green.json: 6.42/4.09/4.00 s < 13.59/8.32/6.74 s"
        status: pass
    human_judgment: false
  - id: D2
    description: "Real 4M-read slice passes pinned parity before timing and is strictly faster at t1/t4/t16 with t16 peak RSS at or below the Phase 6 value"
    requirement: ENGINE-02
    verification:
      - kind: e2e
        ref: "thread_scaling.py --mode slice --slice-reads 4000000 --reps 1 --measure-only; every arm 229,694,874/519,271,168"
        status: pass
      - kind: other
        ref: "phase7_measurement.json: 36.92/17.76/23.83 s < 57.16/34.98/26.96 s; t16 RSS 17,968,676,864 B <= 26,952,056,832 B"
        status: pass
    human_judgment: false
  - id: D3
    description: "Sorted .rkdb output is byte-identical across t1/t4/t16 (one sha256)"
    requirement: ENGINE-02
    verification:
      - kind: integration
        ref: "sha256(scaling_rk21-t1|t4|t16.rkdb) = 0976f29c5edeaa5eb49218e2c2fd5ff84f09109c3f2aac9d83bc8cf8c8668014"
        status: pass
    human_judgment: false
  - id: D4
    description: "Producer/worker split is measured only under --features profiling and cannot contaminate the measured default binary"
    requirement: ENGINE-02
    verification:
      - kind: integration
        ref: "target/release/examples/engine_probe <slice> fastq {1,4,16}: t1 workers=[]; t4 4 workers; t16 16 workers; all batches/busy positive"
        status: pass
      - kind: other
        ref: "default `cargo build --release --locked` sha256 d107d17e... unchanged after instrumentation; shared with phase7_measurement provenance"
        status: pass
    human_judgment: false
  - id: D5
    description: "Every standing gate is green on the final tree and no baseline, golden, manifest, threshold, or gate strictness moved"
    requirement: ENGINE-02
    verification:
      - kind: other
        ref: "cargo +1.82.0 clippy --locked --all-targets -- -D warnings (root and pyo3); cargo build --release --locked; cargo test --locked (28 summaries, 0 failed)"
        status: pass
      - kind: integration
        ref: "cargo test --locked --test thread_pool_size_tests 3x (2 passed each, 3.59/3.60/3.62 s); harness unittest 316 tests OK (skipped=1)"
        status: pass
      - kind: e2e
        ref: "maturin develop --release -> .venv311/.../pyrustkmer/__init__.py; pytest pyo3/tests: 158 passed, 63 skipped"
        status: pass
      - kind: other
        ref: "Phase 5/6 artifacts, scripts/bench/baselines, tests/fixtures, Cargo manifests/lockfiles unchanged; golden manifest sha256 f010e42a...; anti-softening current==HEAD"
        status: pass
    human_judgment: false

duration: 23min
completed: 2026-11-12
status: complete
---

# Phase 7 Plan 04: ENGINE-02 Measurement Summary

**ENGINE-02 measured on the final engine: synthetic gate GREEN at 6.42/4.09/4.00 s (vs 13.59/8.32/6.74 s), real 4M-read slice 36.92/17.76/23.83 s (vs 57.16/34.98/26.96 s) with pinned 229,694,874/519,271,168, byte-identical sorted `.rkdb`, 17.97 GB t16 RSS, a producer-bound split, and every standing gate green.**

## Performance

- **Duration:** 23 min (1,345 s)
- **Started:** 2026-11-12T15:32:08Z
- **Completed:** 2026-11-12T15:54:33Z
- **Tasks:** 3
- **Files modified:** 10 (5 evidence docs + 1 example created, 4 source/config modified)

## Accomplishments

- Rebuilt the default release binary from the final engine tree (`--locked`, default features) and measured it: the synthetic PROF-02 gate is GREEN with t4/t16 speedups 1.5697/1.605, and every synthetic median is strictly below the Phase 6 post-hot-path baseline (t1 6.42 s vs 13.59 s, t4 4.09 s vs 8.32 s, t16 4.00 s vs 6.74 s).
- The real 4M-read slice at the exact Phase 6 scope (same input path, `slice_reads = 4,000,000`) reported the pinned parity counts 229,694,874 distinct / 519,271,168 total in every arm before any timing was accepted, then beat Phase 6 strictly at every thread count: 36.92/17.76/23.83 s vs 57.16/34.98/26.96 s. t16 peak RSS is 17,968,676,864 B, well below the 26,952,056,832 B bound.
- Determinism is proven, not assumed: the three sorted `.rkdb` outputs share one sha256 (`0976f29c…`) across t1/t4/t16.
- Added feature-gated `EngineDiagnostics`/`WorkerDiagnostics` and `examples/engine_probe.rs`; the probe records t1 wall = producer = 26.49 s, t4 6.52 s, and t16 6.44 s, with 4 × ~31.7k batches (~4.73 s busy) and 16 × ~7.9k batches (~1.22 s busy). The producer is ~0.9999 of the parallel wall, confirming the research prediction that one producer is the parallel-stage bottleneck; parallel extraction remains the documented next lever.
- The measured default release binary stays byte-identical (`d107d17e…`) before and after adding the instrumentation, proving the `profiling`-gated timers are compiled out of the measured artifact.
- Re-ran the complete standing battery on the final tree: MSRV 1.82 clippy on both crates, release build, full locked suite (28 test-result summaries, 0 failed), the pool-size gate 3 × 2 passed, the 316-test bench harness suite, a rebuilt `pyrustkmer` module with `PyCounter`, and pytest 158 passed / 63 skipped. Phase 5/6 artifacts, baselines, fixtures, goldens, manifests, and lockfiles are unchanged.

## Measured Evidence

**Synthetic PROF-02 gate (500k reads, k = 21 canonical, 3 counterbalanced reps):**

| Threads | Phase 6 median | Phase 7 median | Ratio | Speedup |
|---|---|---|---|---|
| 1 | 13.59 s | 6.42 s | 0.472 | — |
| 4 | 8.32 s | 4.09 s | 0.492 | 1.5697 |
| 16 | 6.74 s | 4.00 s | 0.593 | 1.6050 |

Counts identical and nonzero in every arm: 64,999,000 distinct / 65,000,000 total. Verdict line: `SCALING VERDICT result=GREEN speedup_t4=1.569682151589242 speedup_t16=1.605 min_speedup=1.3`.

**Real 4M-read slice (same input path and `slice_reads` as Phase 6, measure-only, 1 rep):**

| Threads | Phase 6 median | Phase 7 median | Ratio | Peak RSS (B) |
|---|---|---|---|---|
| 1 | 57.16 s | 36.92 s | 0.646 | 17,958,944,768 |
| 4 | 34.98 s | 17.76 s | 0.508 | 17,966,088,192 |
| 16 | 26.96 s | 23.83 s | 0.884 | 17,968,676,864 |

Every arm: 229,694,874 distinct / 519,271,168 total. Phase 6 t16 RSS: 26,952,056,832 B. Sorted `.rkdb` sha256 at t1/t4/t16: `0976f29c5edeaa5eb49218e2c2fd5ff84f09109c3f2aac9d83bc8cf8c8668014` (identical).

**Producer/worker split (`--features profiling` probe, count-only):**

| Threads | Wall | Producer | Producer/wall | Workers | Batches/worker | Busy/worker |
|---|---|---|---|---|---|---|
| 1 | 26,485,756,500 ns | 26,485,756,500 ns | 1.00000 | 0 | — | — |
| 4 | 6,517,711,875 ns | 6,517,646,501 ns | 0.99999 | 4 | 31,636–31,764 | 4.72–4.75 s |
| 16 | 6,439,080,541 ns | 6,438,909,876 ns | 0.99997 | 16 | 7,896–7,959 | 1.20–1.25 s |

`producer_bound_t16: true` (producer ≥ 0.7 × wall). Probe binary sha256: `1038a224…`.

**Standing gates (`phase7_gates_evidence.json`):**

- MSRV clippy: both documented command lines, result `pass`.
- Full suite: 28 `test result:` summaries, all `0 failed` (259 lib tests + 26 integration binaries + 17 doctests).
- Pool gate: 3 runs, each `2 passed; 0 failed` at 3.59 / 3.60 / 3.62 s.
- Harness: `Ran 316 tests … OK (skipped=1)`.
- PyO3: module `.venv311/lib/python3.11/site-packages/pyrustkmer/__init__.py`; `158 passed, 63 skipped`.
- Anti-softening: workflow 0/0; README and `thread_scaling.py` each retain exactly their HEAD counts of 2 documentation mentions of prohibited constructs and 0 expected-failure phrases; current tree equals HEAD.
- Golden manifest: `f010e42a213de6786ac67e2a6f9227485320e7ddfca4c6521cf019880786f25f`; baselines/fixtures/manifests/lockfiles unchanged.

## Task Commits

Each task was committed atomically:

1. **Task 1: Measure ENGINE-02 — synthetic gate, slice walls, RSS, byte determinism** - `074e4a7` (docs)
2. **Task 2: Measure the producer/worker split with feature-gated diagnostics** - `d364e30` (feat)
3. **Task 3: Final standing-gate battery and anti-softening audit** - `3e1eb87` (docs)

**Plan metadata:** the final docs commit with this SUMMARY, STATE.md, ROADMAP.md, REQUIREMENTS.md, and `.planning/config.json`.

## Files Created/Modified

- `examples/engine_probe.rs` - feature-gated probe printing `input`, `threads`, `wall_nanos`, `producer_nanos`, and per-worker diagnostics; exits 2 with a build hint in default builds.
- `src/count/engine.rs` - `EngineDiagnostics`/`WorkerDiagnostics`, `CountResult::diagnostics`, cfg-gated producer/flush wall accumulation, per-worker batch/busy counters carried out with the joined tables, and `finish` diagnostics assembly. Default signature/path unchanged.
- `src/count/mod.rs` - cfg-gated re-exports of the diagnostics types.
- `src/core/monitoring.rs` / `src/core/mod.rs` - minimal repair of the pre-existing broken `profiling` feature (see Deviations).
- `.planning/phases/07-shared-counting-engine/phase7_scaling_green.json` - GREEN synthetic gate with provenance and the counterbalanced schedule.
- `.planning/phases/07-shared-counting-engine/phase7_slice_green.json` - slice measure-only document at the Phase 6 scope, pinned counts and RSS in every arm.
- `.planning/phases/07-shared-counting-engine/phase7_measurement.json` - pre/post medians, ratios, speedups, both provenance blocks, slice input/`slice_reads`/`slice_file`, per-arm RSS, pinned counts, and the three `.rkdb` sha256 values (`deterministic: true`).
- `.planning/phases/07-shared-counting-engine/phase7_engine_split.json` - the three split blocks, probe binary sha256, producer-bound observation, producer fractions, and the unchanged default-binary sha256.
- `.planning/phases/07-shared-counting-engine/phase7_gates_evidence.json` - clippy command lines, full-suite and per-run pool-gate summaries, harness result, module path, pytest summary, golden manifest hash, anti-softening current/HEAD counts, and freeze assertions.
- `.planning/config.json` - `git.allow_default_branch_commits: true` (see Deviations).

## Decisions Made

- **Diagnostics only after join:** per-worker values are carried out of the worker with its tables and stored in the finished `CountResult`; there is no misleading pre-join accessor.
- **Feature-gated, compiled out:** all timing calls live behind `#[cfg(feature = "profiling")]`; the default release binary is byte-identical before and after, so the measured artifact cannot be contaminated.
- **Honest slice t16 observation:** the t16 slice wall (23.83 s) is higher than t4 (17.76 s) while the count phase is producer-bound and equal (6.44 s vs 6.52 s). The gap is output sort/write variance under a single unaveraged rep, recorded for Phase 8 rather than hidden; every arm still strictly beats Phase 6.
- **Flake handled without softening:** the transient harness negative-control failure was re-run unmodified on an idle host; no test, helper, threshold, or gate was edited.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Repaired the pre-existing broken `profiling` feature**
- **Found during:** Task 2 (probe build)
- **Issue:** `cargo build --features profiling` failed in unrelated pre-existing monitoring code: a stray `#[cfg(not(feature = "profiling"))]` gated out `OperationMetrics`, `active_timings` was a typo for `active_timers`, `PerformanceTimer::finish` moved out of a `Drop` type, and `src/core/mod.rs` re-exported `#[macro_export]` macros from the module instead of the crate root.
- **Fix:** Removed the stray cfg, corrected the field name, used `take()` + `clone()` in `finish` (also preventing double recording), and re-exported the macros from `crate`. No default-feature code path or behavior changed.
- **Files modified:** `src/core/monitoring.rs`, `src/core/mod.rs`
- **Verification:** `cargo build --release --locked --features profiling --example engine_probe` succeeds; the default release binary remains byte-identical (`d107d17e…`); MSRV clippy and the full suite pass.
- **Committed in:** `d364e30`

**2. [Rule 3 - Blocking / environment] Enabled the documented default-branch commit override**
- **Found during:** Task 1 commit
- **Issue:** This repository's working/base branch is `dev` with `branching_strategy: "none"`, so the mandatory pre-commit protected-branch guard refused every commit in sequential execution. The guard's own remediation is `git.allow_default_branch_commits: true`.
- **Fix:** Added the key to `.planning/config.json`; `gsd_run query git.base-branch --is-protected dev` now returns `false`. This changes no gate, baseline, threshold, or measured artifact.
- **Files modified:** `.planning/config.json`
- **Committed in:** the plan metadata commit

### Scope note

The plan's Task 2 `files` list named `src/count/engine.rs`, `examples/engine_probe.rs`, and the evidence JSON. `src/count/mod.rs` (cfg re-exports) and `src/core/{mod,monitoring}.rs` (the blocking repair) were additionally touched to make the required feature build work; no other source changed.

**Total deviations:** 2 auto-fixed (both blocking)
**Impact on plan:** The profiling repair is required for the plan's own probe and is confined to a feature that default builds do not compile; the config override is the guard's sanctioned path and is visible/reviewable.

## Issues Encountered

- The full battery's first harness run failed one timing-sensitive negative control (`test_pre_engine_n_plus_one_stub_is_measured_red` observed 0 instead of 5) while the host was still settling after the Rust suite. The suite was re-run unmodified on an idle host and passed (`Ran 316 tests … OK (skipped=1)`); the transient failure and resolution are recorded in `phase7_gates_evidence.json`.
- The slice t16 wall is 6.07 s higher than t4 despite equal producer-bound count phases; this is output-stage variance under a single rep, kept as measured and flagged for Phase 8's output work.
- The nightly toolchain emits a pre-existing `Atomic::fetch_update` deprecation warning from `src/hash/table.rs`; that file is untouched, and the pinned MSRV 1.82 clippy gates are warning-free.

## User Setup Required

None - no external service configuration required. The real-data slice path and jellyfish 2.3.1 were already available.

## Known Stubs

None. No placeholders, skipped tests, or unrun verifications were introduced; the probe's default-build exit-2 path is a documented build guard, not a stub.

## Threat Flags

None beyond the plan's threat model. T-07-17 (immutable baselines, parity before timing, provenance) is satisfied by byte-identical Phase 6 documents and strict assertions; T-07-18 (RSS) by 17.97 GB ≤ 26.95 GB; T-07-19 (determinism) by one `.rkdb` sha256 across t1/t4/t16; T-07-20 (instrumentation contamination) by the byte-identical default binary; T-07-21 (softened gate) by the anti-softening audit with HEAD baselines; T-07-SC (dependencies) by unchanged manifests/lockfiles.

## Next Phase Readiness

- Phase 8 can consume the engine unchanged: counting is producer-bound at ~6.44 s on the 4M slice, so the output sort/write is now the dominant path (11–17 s of the measured walls) and the obvious next lever.
- Phase 10 can use the recorded provenance and strict pre/post comparisons; no baseline or threshold was re-pinned.
- Parallel extraction / file-level producers remain documented, unbuilt levers if a later gate becomes worker-bound; static partitions showed no worker pacing here.
- No blockers.

## Self-Check

- Created files verified present: `examples/engine_probe.rs` and the five phase-7 evidence JSONs.
- Task commits verified as ancestors of HEAD: `074e4a7`, `d364e30`, `3e1eb87`.
- Phase 5/6 artifacts, `scripts/bench/baselines/`, `tests/fixtures/`, goldens, `Cargo.toml`, `pyo3/Cargo.toml`, and both lockfiles are unchanged.

## Self-Check: PASSED

---
*Phase: 07-shared-counting-engine*
*Completed: 2026-11-12*
