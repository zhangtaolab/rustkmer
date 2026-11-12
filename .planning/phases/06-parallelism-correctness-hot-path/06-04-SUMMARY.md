---
phase: 06-parallelism-correctness-hot-path
plan: 04
subsystem: measurement/verification
tags: [thread-scaling, par-01, par-02, par-03, green-gate, exactness, golden, msrv, pyo3, standing-gate]

requires:
  - phase: 06-parallelism-correctness-hot-path
    plan: 01
    provides: "working --threads and the pre-hot-path true t1 baselines (synthetic 18.77 s, 4M slice 142.54 s)"
  - phase: 06-parallelism-correctness-hot-path
    plan: 02
    provides: "per-worker LocalKmerCounts + checked end-of-file reduction"
  - phase: 06-parallelism-correctness-hot-path
    plan: 03
    provides: "rolling 2-bit encoder + bit-parallel reverse complement on the counting path"
  - phase: 05-measurement-regression-harness
    provides: "thread_scaling.py gate, provenance validators, pinned slice parity, MSRV 1.82 clippy jobs"
provides:
  - "Post-hot-path GREEN scaling document: speedup_t4=1.633, speedup_t16=2.016 at 500k synthetic reads, identical counts"
  - "Strict t1 improvements vs the 06-01 baselines: synthetic 18.77 -> 13.59 s (0.724x), 4M slice 142.54 -> 57.16 s (0.401x), same input and slice_reads"
  - "Parallel per-file local reduction: the serial reduction tail from 06-02 was the scaling ceiling and is now merged concurrently with identical checked semantics"
  - "Exactness evidence: six differential/golden suites + lib green, pinned parity 2,400,000/2,400,000 with provenance"
  - "Gate evidence: MSRV 1.82 clippy on both crates, full locked suite 430 passed, pool-size gate, rebuilt PyO3 pytest 146 passed"
  - "CI and harness docs describe PROF-02 as a standing gate; no expected-failure wording or softening construct remains"
affects: [07, 08, 09, 10]

actuals:
  tokens: 6228
  tasks: 3
  commits: 4
  plan_head_before: e4657536a9bec8a07aebd9639d4c70e7e57dcbf7
  plan_head_after: d7f7751c6028af9963e2958fee0e03f4b6d87cda

tech-stack:
  added: []
  patterns:
    - "Local reduction is parallel over the drained locals: per-key DashMap shard locks keep checked sums exact, so scaling no longer pays a fixed serial merge tail"
    - "The single-local (t1) path stays sequential so the single-thread measurement is unchanged by the parallel-reduction fix"
    - "Standing-gate evidence is measured on the final binary and compared against immutable pre-change baselines; no baseline is ever recaptured"

key-files:
  created:
    - ".planning/phases/06-parallelism-correctness-hot-path/phase6_scaling_green.json"
    - ".planning/phases/06-parallelism-correctness-hot-path/phase6_slice_green.json"
    - ".planning/phases/06-parallelism-correctness-hot-path/phase6_measurement.json"
    - ".planning/phases/06-parallelism-correctness-hot-path/phase6_exactness_evidence.json"
    - ".planning/phases/06-parallelism-correctness-hot-path/phase6_gates_evidence.json"
  modified:
    - "src/hash/table.rs"
    - ".github/workflows/benchmark.yml"
    - "scripts/bench/thread_scaling.py"

key-decisions:
  - "The first post-change scaling run was RED (1.197/1.253, CV ~1.2%) and was treated as a real regression, not noise; no threshold, input, or baseline change was made"
  - "Decomposing with --no-sort showed user time ~ wall time at t4, isolating the serial per-file local reduction as the fixed tail; the reduction was parallelized while preserving checked u32/u64 sums, unique/total accounting, and the verbatim overflow error"
  - "The README already presented both PROF-02 gates as standing after 06-01, so no further README edit was needed; the stale expected-RED docstring/help in thread_scaling.py was brought in line as part of the same wording cleanup"
  - "Peak RSS is recorded in both scaling documents for T-06-05: multi-thread locals raise slice t4/t16 RSS (24/25 GiB vs 17/16 GiB pre-change); the long-run partitioned memory design remains owned by Phase 7"

requirements-completed: [PAR-01, PAR-02, PAR-03]

coverage:
  - id: D1
    description: "Post-hot-path thread-scaling gate is GREEN with speedup_t4 and speedup_t16 at least 1.3, identical nonzero counts, and a strictly lower true t1 than the pre-hot-path baseline"
    requirement: PAR-01
    verification:
      - kind: e2e
        ref: "python3 scripts/bench/thread_scaling.py --mode synthetic --reads 500000 --reps 3 -> SCALING VERDICT result=GREEN speedup_t4=1.6334 speedup_t16=2.0163"
        status: pass
      - kind: e2e
        ref: "phase6_measurement.json: synthetic t1 18.77 -> 13.59 s (ratio 0.7240); slice t1 142.54 -> 57.16 s (ratio 0.4010)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Exact counts, golden compatibility, and pinned slice parity re-proven on the final tree without regenerating fixtures or relaxing assertions"
    requirement: PAR-02
    verification:
      - kind: integration
        ref: "cargo test --locked --test parallel_count_tests; --test dense_differential_tests; --test golden_tests; --test golden_sha256_tests; --test thread_local_count_tests; --test kmer_rolling_differential_tests; --lib"
        status: pass
      - kind: e2e
        ref: "python3 scripts/bench/bench.py --mode synthetic --reads 20000 --parity-only -> PARITY OK distinct=2400000 total=2400000"
        status: pass
    human_judgment: false
  - id: D3
    description: "MSRV 1.82 clippy on both crates, locked release build, full locked test suite, pool-size gate, and the rebuilt PyO3 module's Python suite all pass"
    requirement: PAR-03
    verification:
      - kind: integration
        ref: "cargo +1.82.0 clippy --locked --all-targets -- -D warnings (root and pyo3/Cargo.toml)"
        status: pass
      - kind: integration
        ref: "cargo test --locked -> 26 suites, 430 passed, 0 failed, 4 ignored; thread_pool_size_tests 2 passed/0 ignored"
        status: pass
      - kind: integration
        ref: "maturin develop --release + import PyCounter + pytest pyo3/tests -q -> 146 passed, 63 skipped"
        status: pass
    human_judgment: false
  - id: D4
    description: "CI and harness documentation present the PROF-02 gates as standing, with no expected-failure wording and no softener"
    requirement: PAR-01
    verification:
      - kind: other
        ref: "grep -Eqi 'INTENTIONALLY RED|expected RED|intentional RED|expected to fail|expected failure' .github/workflows/benchmark.yml scripts/bench/README.md scripts/bench/thread_scaling.py -> no match; grep -E 'continue-on-error|\\|\\| true' benchmark.yml -> no match"
        status: pass
      - kind: integration
        ref: "python3 -m unittest scripts.bench.tests.test_thread_scaling -q -> 20 tests OK"
        status: pass
    human_judgment: false

duration: 27 min
completed: 2026-11-12
status: complete
---

# Phase 06 Plan 04: Measurement, Exactness & Standing-Gate Verification Summary

**The post-hot-path binary is measured GREEN at 1.633x (t4) and 2.016x (t16) scaling with identical counts, true t1 is 26% faster synthetically (18.77 -> 13.59 s) and 2.5x faster on the 4M-read real slice (142.54 -> 57.16 s), every exactness/golden/parity gate is green, MSRV clippy and the rebuilt PyO3 suite pass, and the CI/docs no longer call the PROF-02 gates expected failures — after fixing the serial reduction tail that broke scaling.**

## Performance

- **Duration:** 27 min
- **Started:** 2026-11-12T12:38:08Z
- **Completed:** 2026-11-12T13:05:20Z
- **Tasks:** 3
- **Files modified:** 8 (5 evidence artifacts created; 3 files modified)

## Accomplishments

- **GREEN thread-scaling gate on the final binary.** 500,000 synthetic reads, 3 counterbalanced reps, 5 s cooldown: t1 13.59 s, t4 8.32 s, t16 6.74 s; `speedup_t4=1.6334`, `speedup_t16=2.0163` (threshold 1.3); all three arms report 64,999,000 unique / 65,000,000 total; schema and provenance valid.
- **Strict single-thread improvement against immutable baselines.** Synthetic t1 18.77 -> 13.59 s (ratio 0.7240) and the real 4M-read slice t1 142.54 -> 57.16 s (ratio 0.4010), with `params.input` and `params.slice_reads` identical to `thread_scaling_par01_slice.json`. Both 06-01 baselines and the Phase 5 RED baseline were verified byte-for-byte unchanged before and after.
- **Regression found and fixed, not papered over.** The first post-change run was RED (1.197/1.253, CV ~1.2%). Decomposition with `--no-sort` showed user time ~ wall time at t4, isolating the 06-02 serial reduction of per-worker locals as a fixed N-way tail. `reduce_local_counts` now merges drained locals concurrently via rayon; the shared DashMap's per-key shard lock keeps every checked sum atomic, so counts, unique/total accounting, and the verbatim overflow error are unchanged. The single-local (t1) path stays sequential.
- **Exactness re-proven.** `parallel_count_tests` 4 passed/1 ignored (run-once D-10 capture), `dense_differential_tests` 6, `golden_tests` 34, `golden_sha256_tests` 5, `thread_local_count_tests` 9, `kmer_rolling_differential_tests` 9 passed/1 ignored (release timing gate), lib 242 passed. Pinned parity smoke: `PARITY OK distinct=2400000 total=2400000` with valid provenance. Golden manifest sha256 `f010e42a...`; no fixture, expected count, or assertion changed.
- **Standing-gate green battery.** Root and PyO3 MSRV 1.82 clippy with `-D warnings` exit 0; locked release build OK; full locked suite 26 test-result groups, 430 passed / 0 failed / 4 ignored; pool-size gate 2 passed / 0 ignored; rebuilt `pyrustkmer` exposes `PyCounter`; full Python suite 146 passed / 63 skipped.
- **Wording de-REDed without softening.** `benchmark.yml` header, mid-file comment, step comment and step name now describe the thread-scaling verdict as a standing gate that must stay green; the measure -> upload -> verdict order and unconditional step are unchanged. No `continue-on-error` or `|| true` exists. README already presented both gates as standing after 06-01; the obsolete expected-RED wording in `thread_scaling.py`'s docstring/help was removed (comments/help only; exit-code contract untouched).
- **WINDOWS ledger.** Entry 22 records the serial-reduction scaling regression and is marked fixed; `open_count` is back to 0.

## Task Commits

Each task was committed atomically:

1. **Task 1: Measure post-change scaling and true single-thread improvement**
   - `149379b` (fix) — parallelize the per-file local reduction (deviation Rule 1)
   - `329cfb2` (feat) — GREEN scaling, slice, and pre/post t1 evidence documents
2. **Task 2: Re-prove exact counts, golden compatibility, and pinned slice parity** — `cdfa320` (test)
3. **Task 3: MSRV/full-suite/dual-surface gates and standing-gate wording cleanup** — `d7f7751` (chore)

**Plan metadata:** (docs commit created after this summary)

## Files Created/Modified

- `src/hash/table.rs` — `reduce_local_counts` merges drained locals concurrently for >1 local via `rayon::prelude::*`; single-local path unchanged; failed parallel reductions still release every local table.
- `.planning/phases/06-parallelism-correctness-hot-path/phase6_scaling_green.json` — GREEN synthetic scaling document with provenance and per-arm RSS.
- `.planning/phases/06-parallelism-correctness-hot-path/phase6_slice_green.json` — measure-only real 4M-read slice document at the 06-01 scope.
- `.planning/phases/06-parallelism-correctness-hot-path/phase6_measurement.json` — pre/post t1 medians and ratios, both speedups, both provenance blocks, and the slice comparison.
- `.planning/phases/06-parallelism-correctness-hot-path/phase6_exactness_evidence.json` — per-suite markers, golden manifest sha256, parity counts/provenance.
- `.planning/phases/06-parallelism-correctness-hot-path/phase6_gates_evidence.json` — per-gate pass markers, clippy command lines, Python module path, full-suite and pytest summaries.
- `.github/workflows/benchmark.yml` — standing-gate wording; gate structure and evidence-retention behavior unchanged.
- `scripts/bench/thread_scaling.py` — obsolete expected-RED docstring/help/comment text removed.

## Verify Evidence

- `cargo build --release --locked` -> OK; binary sha256 `29507442...`, git HEAD `e465753`, `git_dirty: true` from generated measurement inputs (same honesty convention as 06-01).
- `python3 scripts/bench/thread_scaling.py --mode synthetic --reads 500000 --reps 3 --out phase6_scaling_green.json` -> `SCALING VERDICT result=GREEN speedup_t4=1.6334134615384615 speedup_t16=2.016320474777448 min_speedup=1.3`; schema/provenance validation pass; arm counts identical and nonzero.
- `python3 scripts/bench/thread_scaling.py --mode slice --input "$SLICE_IN" --slice-reads 4000000 --reps 1 --measure-only` -> exit 0; slice t1 57.16 s (pre 142.54 s), t4 34.98 s, t16 26.96 s; counts 229,694,874 / 519,271,168 in every arm.
- Baseline integrity: `thread_scaling_baseline.json` sha256 `5d7c4466...`, `thread_scaling_par01_green.json` `65d6d45c...`, `thread_scaling_par01_slice.json` `d81742c4...` — all unchanged.
- Exactness commands (Task 2) all exit 0 with the suite counts listed above; `golden_manifest.sha256` sha256 `f010e42a213de6786ac67e2a6f9227485320e7ddfca4c6521cf019880786f25f`.
- `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` -> exit 0 (root); same with `--manifest-path pyo3/Cargo.toml` -> exit 0.
- `cargo test --locked` -> exit 0: 26 suites, 430 passed, 0 failed, 4 ignored. `cargo test --locked --test thread_pool_size_tests` -> 2 passed, 0 ignored.
- `maturin develop --release` (CONDA_PREFIX unset) -> installed; `import pyrustkmer; assert hasattr(pyrustkmer,'PyCounter')` -> OK, module `/Users/forrest/GitHub/rustkmer/.venv311/lib/python3.11/site-packages/pyrustkmer/__init__.py`; `pytest pyo3/tests -q` -> **146 passed, 63 skipped**.
- Wording greps: forbidden expected-failure regexes have no match in `benchmark.yml`, `README.md`, or `thread_scaling.py`; `continue-on-error` / `|| true` have no match in the workflow.

## Decisions Made

- Treat the first RED scaling measurement as a real regression: CV was ~1.2% on every arm, so re-running to chase a pass would have been dishonest and the plan forbids threshold/input/baseline changes.
- Fix the scaling ceiling at its source (parallel per-local reduction) rather than touching the measurement protocol or the output pipeline: the Phase 8-owned stable sort (`~2.2 s`, measured via `--no-sort`) was left untouched.
- Preserve the 06-02 exactness contract exactly: per-key checked `u32` sums, checked `u64` total accumulation, unique counting only for keys vacant in the shared table, verbatim overflow error, and local release on failure.
- Record peak RSS rather than gate it: T-06-05's mitigation is reduce/release + capacity hints + measurement, and the long-run partitioned memory design belongs to Phase 7.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 06-02's serial per-file local reduction broke the standing scaling gate**
- **Found during:** Task 1 (first post-change scaling measurement)
- **Issue:** The measured gate was RED — `speedup_t4=1.1974`, `speedup_t16=1.2527` against the 1.3 threshold. CVs were 1.23%/1.22%/1.32%, so this was not noise. With `--no-sort`, t4 wall 8.85 s vs t1 10.84 s and user time ~ wall time, showing the drain-and-merge of all worker locals into the shared DashMap was a fixed serial tail; 06-03's hot-path win made t1 faster while t4/t16 stayed merge-bound.
- **Fix:** `KmerCounter::reduce_local_counts` now merges drained locals concurrently with rayon when there is more than one local. Each merge still goes through the same per-key DashMap shard-locked `checked_add`, so per-key sums, unique/total accounting, and the verbatim `K-mer count overflow reached maximum value <max>` error are unchanged. The single-local t1 path remains sequential, and a failed parallel reduction releases every drained local table.
- **Files modified:** `src/hash/table.rs`
- **Verification:** `thread_local_count_tests` 9/9 (including overlapping locals, 1-vs-N, old-vs-new, multi-file, and overflow); full exactness battery green; rebuilt gate **GREEN** at 1.6334/2.0163 with identical counts; slice t1 57.16 s.
- **Committed in:** `149379b` (Task 1 fix commit)
- **WINDOWS:** entry 22 (recorded + marked fixed)

**2. [In-scope wording completion] Stale expected-RED text inside `thread_scaling.py`**
- **Found during:** Task 3 (standing-gate wording cleanup)
- **Issue:** The plan named `benchmark.yml` and `scripts/bench/README.md`, but the gate script's own docstring, `--help` description, and an exception comment still described the gate as expected-RED/`--threads`-is-a-no-op. The README itself was already compliant (06-01 had made it standing, and the forbidden-wording grep found nothing).
- **Fix:** Rewrote those comments/help strings to describe the standing GREEN gate; no behavior, exit-code, or argument contract changed. `scripts/bench/tests/test_thread_scaling.py` -> 20 passed.
- **Files modified:** `scripts/bench/thread_scaling.py`
- **Committed in:** `d7f7751` (Task 3 commit)

### Environment accommodations

- `maturin develop` ran with `CONDA_PREFIX` unset (the ambient shell exports it in addition to the plan's `VIRTUAL_ENV`); same accommodation as 06-02 and 06-03. No code or API impact.

**Total deviations:** 1 auto-fixed (Rule 1 scaling regression) + 1 in-scope wording completion + 1 environment accommodation.
**Impact on plan:** The Rule 1 fix was required to make Task 1's own acceptance criteria true and to keep the standing gate honest; it adds ~42 lines in one function and introduces no new dependency, API, format, or output change.

## Issues Encountered

- **First scaling run RED, then GREEN after the fix.** The diagnostic sequence was: inspect per-arm CVs (all ~1.2%, so not noise) -> rerun with `--no-sort` -> observe user time ~ wall time at t4 (serial work) -> inspect `reduce_local_counts` -> parallelize per-local merges -> exactness suite -> re-measure. No baseline was recaptured and no threshold changed.
- **Peak RSS is higher with per-worker locals (T-06-05 measurement).** Synthetic: t1 10.9 GiB (pre-change 8.6 GiB), t4 10.0 GiB, t16 9.0 GiB. Real 4M slice: t1 16 GiB, t4 24 GiB, t16 25 GiB (pre-change slice 16.4/17.1/16.2 GiB). This is the expected cost of holding one local table per worker until the per-file reduction; 06-02's threat model assigns the long-run partitioned memory design to Phase 7, and the measured values are recorded in both scaling documents rather than silently omitted.
- **Release sort remains a serial tail (Phase 8 owns it).** `--no-sort` vs sorted runs differ by ~2.2 s at both t1 and t4; this plan deliberately did not touch the output pipeline.

## User Setup Required

None - no external service configuration required. (`.venv311`, maturin, jellyfish 2.3.1, and Rust 1.82 were already present.)

## Known Stubs

None. The two ignored tests are pre-existing, documented run-once instruments: the D-10 pre-refactor baseline capture (`parallel_count_tests`) and the 06-03 release timing gate (`kmer_rolling_differential_tests`, exercised separately under `--ignored`).

## Threat Flags

None. Plan threat mitigations hold: **T-06-09** (new provenance-bearing artifacts; both speedup thresholds unchanged; Phase 5 and 06-01 baselines verified byte-identical; softening constructs rejected by grep), **T-06-10** (maturin release rebuild, `PyCounter` import assert, full Python suite, module path recorded), **T-06-SC** (no dependency or manifest changes; every build/clippy run used `--locked`). The reduction fix preserves T-06-04's checked-arithmetic and verbatim-overflow contracts. No new network endpoints, auth paths, schema changes, or `.rkdb`/output-sort changes.

## Next Phase Readiness

- Phase 7 inherits a GREEN PROF-02 gate (1.633x/2.016x) and an honest baseline: further scaling work must beat 13.59 s synthetic t1 / 57.16 s slice t1 and can move the gate rather than merely reach it.
- `reduce_local_counts` is now parallel over locals; the persistent-worker/partitioned design in Phase 7 can replace it without changing the checked sum or error contracts the differential suites pin.
- Phase 8 owns the remaining serial tails: the stable sort (~2.2 s at 200k-read scale) and `get_all_counts` materialization; the golden manifest and byte-identity gates are untouched.
- Peak-RSS evidence for human-scale engineering is recorded here and must be carried into Phase 10/11 memory decisions.

---

*Phase: 06-parallelism-correctness-hot-path*
*Completed: 2026-11-12*

## Self-Check: PASSED

- All five evidence artifacts and this SUMMARY — FOUND.
- Commits `149379b`, `329cfb2`, `cdfa320`, `d7f7751` — all ancestors of HEAD.
- Phase 5 RED baseline sha256 `5d7c4466...`, 06-01 synthetic baseline `65d6d45c...`, 06-01 slice baseline `d81742c4...` — unchanged.
- Gate result GREEN 1.6334/2.0163 with identical nonzero counts; synthetic t1 ratio 0.7240 and slice t1 ratio 0.4010 (strictly lower).
- Exactness suites and pinned parity green; MSRV clippy, full suite, pool-size gate, rebuilt PyO3 pytest green; forbidden wording/softening greps empty.
