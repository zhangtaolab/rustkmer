---
phase: 13-producer-attribution-research
plan: 01
subsystem: benchmarks
tags: [harness, measurement, attribution, provenance, pre-registration, rustkmer, python-stdlib]

# Dependency graph
requires:
  - phase: 11-merge-characterization-harness-prep
    provides: measured_run/_run_fail_loud/ensure_free_space/_guard_zero patterns, committed lock-fixture precedent, microbench manifest template
  - phase: 12-full-scale-merge-verdict
    provides: staged-verb/exit-code contract, publish_atomic + byte-identical render proof, provenance-validation discipline
provides:
  - scripts/bench/phase13.py — the D-01 measurement driver (probe materialization, A/B/C/D + control arms, evidence doc, D-09 attribution, two-ceiling predicted win, D-05 gate, deterministic memo render)
  - scripts/bench/tests/test_phase13_driver.py — 80 Wave-0 unit tests (gate branches, attribution arithmetic, model bounds, memo branches)
  - committed probe lock fixtures for the materialized k=31 probe and null consumer
  - `--rehearsal` fixture-scale chain proof (materialize -> measure -> evidence -> math -> decision -> memo text)
affects: [13-02 (live session), 13-03 (memo/ROADMAP/lifecycle), 14 (conditional GO target)]

actuals:
  tokens: 66352
  tasks: 3
  commits: 3
  plan_head_before: 078556c5a5b89e57a3a10ec90997c1f258908753
  plan_head_after: d992f6fce6df6f00076f4ea6a9cc99d4c799bef8

tech-stack:
  added: []
  patterns:
    - "Probe materialization outside the repo: embedded Rust templates + committed Cargo.lock fixtures, seeded and sha256-verified before every cargo build --locked"
    - "Per-instrument probe k contract: committed k=21 probe keyed by instrument identity (no k field), materialized probes must assert k in JSON"
    - "Input-type-scoped pair-sum-then-median reduction for probe nanos (never bench.reduce_arm on probe JSON)"
    - "Doc-level provenance block validated by every stage; full-scale-only memo derivation with three distinct refusal classes"

key-files:
  created:
    - scripts/bench/phase13.py
    - scripts/bench/tests/test_phase13_driver.py
    - scripts/bench/fixtures/phase13_probe_k31.Cargo.lock
    - scripts/bench/fixtures/phase13_null_consumer.Cargo.lock
  modified: []

key-decisions:
  - "D-09 arithmetic is implemented exactly as researched: inflate = (median_A - median_B) - (read_gz - read_plain), sign preserved unclamped; route_send = producer_plain - parse_extract; output_stage = median_A - count_phase_wall"
  - "Probe nanos reduce through one input-type-scoped _pair_sum_median (arm-C gzip for count-phase and busy total, arm-C plain for producer, arm-D plain for parse+extract), never through bench.reduce_arm"
  - "The two scratch probe crates share one CARGO_TARGET_DIR under the pinned PROBE_SCRATCH_ROOT so dependency builds are reused; the repo target dir is never touched"
  - "A3/A4 anomaly criteria are module constants; when tripped the model returns mode='bounds' with the conservative (derated) end as the decision input"
  - "Lock fixtures are regenerated through a documented offline maintenance verb rather than hand-edited"

requirements-completed: [PEXT-01, PEXT-02]

coverage:
  - id: D1
    description: "Fixture-scale rehearsal proves the whole chain end-to-end (probe materialization -> all arms + control -> evidence doc -> attribution -> predicted win -> decision -> memo text)"
    requirement: PEXT-01
    verification:
      - kind: integration
        ref: "python3 scripts/bench/phase13.py --rehearsal"
        status: pass
    human_judgment: false
  - id: D2
    description: "Wave-0 unit module: fingerprint gate, D-09 attribution arithmetic, model completeness, bounds mode, memo branches, probe parsing, constant pre-registration"
    requirement: PEXT-01
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_phase13_driver.py (80 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Full-scale prep/measure/memo stages behind injectable seams (clean-rebuild gate, disk guard, streaming decompression, per-rep deletion, crash-safe writes, memo refusals)"
    requirement: PEXT-02
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_phase13_driver.py#TestRunPrepSeams / TestRunMeasureSeams / TestRunMemoSeams"
        status: pass
      - kind: automated
        ref: "python3 -m unittest discover -s scripts/bench/tests -t . (797 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Committed lock fixtures + probe materialization with sha256 verification before every --locked build; k=31 manifest pins rustkmer's profiling feature"
    requirement: PEXT-01
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_phase13_driver.py#TestLockFixtures"
        status: pass
      - kind: integration
        ref: "rehearsal builds both materialized crates from the committed fixtures"
        status: pass
    human_judgment: false
  - id: D5
    description: "D-05 pre-registered bar (10.0, derated model, >= semantics, both-k conjunction) pinned as constants and consumed by derive_gate_decision"
    requirement: PEXT-02
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_phase13_driver.py#TestDeriveGateDecision / TestPreRegisteredConstants"
        status: pass
    human_judgment: false

duration: 14 min
completed: 2026-11-17
status: complete
---

# Phase 13 Plan 01: Producer Attribution Research — Driver & Wave-0 Harness Summary

**Stdlib-only Phase-13 measurement driver with materialized k=31/null probes, a fixture-scale rehearsal proving the whole attribution -> predicted-win -> D3-decision -> memo chain, and 80 Wave-0 unit tests — zero Rust changes.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-11-17T11:56:30Z
- **Completed:** 2026-11-17T12:10:55Z
- **Tasks:** 3
- **Files modified:** 4 created (0 modified; `src/`, `pyo3/src/`, `examples/` untouched)

## Accomplishments

- `scripts/bench/phase13.py` (kind `phase13-producer-attribution`) implements the full D-01 vehicle: `materialize_probe_binaries` (embedded Rust templates, pinned `/tmp/phase13-probe-scratch` root, committed-lock-fixture seeding + sha256 verification before every `cargo build --release --locked`, k=31 manifest enabling rustkmer's `profiling` feature), `fingerprint_gate` (D-03/D-10 branch: exact sha256 equality -> `cite`, else `re-measure`, both hashes recorded), `run_prep`/`run_measure`/`run_memo`, the pure functions `build_attribution`/`build_predicted_win`/`derive_gate_decision`/`render_memo_text`, and the `--rehearsal` chain proof.
- The rehearsal runs all five arms at both k over deterministic fixture inputs and emits a complete evidence document (20 records, every record carrying `scale='rehearsal'`, `binary_sha256`, `input_sha256s`, `command_line`, `cache_state`, `wall_s`, `peak_rss_bytes`, validated provenance block) plus a rendered memo whose D-06 context block carries 165.05/178.22, the module fingerprint, "context only", and "binary-fingerprint caveat".
- Probe parsing is per-instrument and fail-loud: the committed k=21 probe's JSON (no k field) parses by instrument identity; the materialized k=31 probe and null consumer require and cross-check their k; zeroed nanos abort every instrument.
- 80 Wave-0 unit tests cover the D-09 delta correction in both directions plus the unclamped negative share, the exact residual derivations and composition split, both predicted-win ceilings and the A3/A4 bounds branch, the D-05 `>=`/both-k conjunction fixtures, the three memo-derivation refusals, the lock-fixture gate, the profiling-feature manifest pin, and the pre-registered constant assertions.
- Full harness suite green: 797 tests (1 platform skip), +80 from this plan; `git status` over `src/`, `pyo3/src/`, `examples/` is clean.

## Task Commits

Each task was committed atomically:

1. **Task 1: Driver skeleton + rehearsal mode (tracer)** - `0726073` (feat)
2. **Task 2: Full-scale prep/measure/memo stages + seam tests** - `18f4a5b` (feat)
3. **Task 3: Wave-0 attribution/model/memo behaviors** - `d992f6f` (test)

**Plan metadata:** committed with this SUMMARY (docs: complete plan)

## Files Created/Modified

- `scripts/bench/phase13.py` — the staged driver: probe materialization + lock-fixture gate, measured-run wrappers (`measured_run` imported; DEVNULL and stdout-capture variants), per-instrument probe parsing, evidence doc I/O, D-09 attribution, two-ceiling predicted win (point/bounds), D-05 decision, deterministic memo render + byte-identical proof + atomic publish, rehearsal, prep, measure, memo.
- `scripts/bench/tests/test_phase13_driver.py` — 80 stdlib-unittest cases, binary-light, one class per function under test.
- `scripts/bench/fixtures/phase13_probe_k31.Cargo.lock` — committed lock for the materialized k=31 probe (202 packages, offline-generated).
- `scripts/bench/fixtures/phase13_null_consumer.Cargo.lock` — committed lock for the null consumer (same graph + bio).

## Decisions Made

- **Attribution arithmetic is the RESEARCH formula, not an approximation.** `inflate_s = (median_A - median_B) - (read_gz - read_plain)` with the sign preserved unclamped; `route_send_s = producer_plain_probe_s - parse_extract_s`; `output_stage_s = median_A - count_phase_wall_probe_s`. A negative corrected share is stored exactly as measured (D-09).
- **Probe nanos never go through `bench.reduce_arm`.** One `_pair_sum_median(records, value_fn, k, input_type)` filters an arm's records to the named input type, requires exactly the two pinned-pair parts per rep, sums per rep, and medians over reps, returning citations keyed arm/k/rep/part/input_type.
- **Bounds mode keeps the decision rule fixed.** A3/A4 anomaly criteria (`PROBE_VS_CLI_RATIO_BAND`, `WORKER_BUSY_RATIO_MAX`, non-positive busy total) switch `mode` to `bounds`; the point keys carry the conservative derated end so `derive_gate_decision` consumes the same input in both modes and the idealized E=M bound is reported only.
- **One shared scratch `CARGO_TARGET_DIR`** under the pinned probe root lets the two materialized crates reuse dependency builds; the repo's `target/` is never used for probe crates, keeping provenance clean.
- **Lock fixtures have a reproducible offline regeneration verb** (`--generate-lock-fixtures`) instead of a hand-edited file: `cargo generate-lockfile --offline` at fixture creation only; every measurement run seeds + sha256-verifies against the committed fixture.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Imported `stats` and `LARGEST_SINGLE_ARM_TRANSIENT_BYTES` beyond the plan's named bench import list**
- **Found during:** Task 1 (driver build)
- **Issue:** The plan's import block named only the primitives it listed, but the zero-entry guard needs `bench.stats` on every arm-A/B output and the D-04 disk arithmetic needs the recorded largest-transient constant.
- **Fix:** Added both to the `scripts.bench.bench` import block; both are existing tested primitives.
- **Files modified:** `scripts/bench/phase13.py`
- **Verification:** rehearsal zero-entry guards fire on every A/B run; prep records `required_free_bytes` from the constant.
- **Committed in:** `0726073`, `18f4a5b`

**2. [Rule 3 - Blocking] Shared `CARGO_TARGET_DIR` for the two scratch probe crates**
- **Found during:** Task 1 (probe materialization)
- **Issue:** Two separate `--manifest-path` builds without a shared target dir rebuild the whole rustkmer dependency graph (release + LTO) twice, turning the rehearsal into a multi-minute duplicate build.
- **Fix:** `materialize_probe_binaries` passes `CARGO_TARGET_DIR=<scratch>/target` in the build environment (still outside the repo, still `--locked`); `_cargo_build` gained an `env` parameter.
- **Files modified:** `scripts/bench/phase13.py`
- **Verification:** second crate builds in ~13 s after the first populates the shared target (vs a full duplicate graph build).
- **Committed in:** `0726073`, `18f4a5b`

**3. [Rule 2 - Missing Critical] Added `--generate-lock-fixtures` maintenance verb**
- **Found during:** Task 1 (lock fixtures)
- **Issue:** The plan mandated the two committed lock fixtures but gave no reproducible in-driver way to generate them; hand-running cargo would leave the fixture provenance undocumented.
- **Fix:** Added a maintenance-only verb that materializes each crate without a lock, runs `cargo generate-lockfile --offline`, and copies the result into `scripts/bench/fixtures/`.
- **Files modified:** `scripts/bench/phase13.py`
- **Verification:** both fixtures regenerated deterministically and committed.
- **Committed in:** `0726073`

**4. [Rule 1 - Bug] Citation sort key, pair-level `part=None`, and the D-06 token**
- **Found during:** Task 1 rehearsal green-up and Task 2 memo tests
- **Issue:** `_sorted_citations` sorted a mixed int/str key tuple (TypeError); the memo-derivation provenance guard treated pair-level `part=None` (arms A/B/control) as a missing field; the rendered D-06 sentence started "Binary-fingerprint caveat", so the required verbatim token `binary-fingerprint caveat` was absent.
- **Fix:** dedupe/sort on the already-comparable citation key; treat `part` as identity (required only for arms C/D); reword the D-06 sentence so the pinned lowercase token appears.
- **Files modified:** `scripts/bench/phase13.py`
- **Verification:** rehearsal green; `test_go_fixture_renders_and_exits_zero` asserts every D-06 token.
- **Committed in:** `0726073`, `18f4a5b`, `d992f6f`

---

**Total deviations:** 4 auto-fixed (1 bug, 2 missing critical, 1 blocking)
**Impact on plan:** All four are infrastructure/completeness fixes inside the plan's own driver; no scope expansion, no Rust changes, no new dependencies.

## Issues Encountered

- The rehearsal (fixture-scale, deliberately tiny) computes a NO-GO decision: the CLI's fixed startup/sort overhead dominates at 2000-record inputs, so the k=21 conservative improvement is negative and the k=21 model correctly falls into bounds mode. The chain proof is unaffected — the NO-GO memo branch was rendered and asserted. The GO per-part branch is unit-proven on a full-shape fixture doc (`TestMemoBranches.test_go_memo_lists_all_six_parts`) and will be exercised live by Plan 13-02/13-03. No number was fabricated to force a GO.

## User Setup Required

None — no external service configuration, no new packages, no Rust changes.

## Next Phase Readiness

- Plan 13-02 can run the live protocol as recorded code: `--stage prep` (clean rebuild + git_dirty assertion + disk arithmetic + six-part streaming decompression + probe materialization), `--stage measure` (3-rep counterbalanced gate matrix per k + excluded context matrix + attribution/predicted-win/decision), with crash-safe incremental evidence writes.
- The D-05 constants and the D-03/D-10 gate are pinned and unit-asserted; the live fingerprint outcome is already recorded as `re-measure` (current `4539b893…`, v2.0 `8f38d20c…`), so arm A's fresh medians are the only decision denominator.
- Watch items for 13-02: `run_prep` requires a clean tree (`git_dirty: false`) — the live session must start from a committed state; the six plain parts land in `/Users/forrest/Data/data/illumina/CRR1936095-plain` for Plan 13-03 to delete post-memo.

## Self-Check: PASSED

- Created files exist: `scripts/bench/phase13.py`, `scripts/bench/tests/test_phase13_driver.py`, `scripts/bench/fixtures/phase13_probe_k31.Cargo.lock`, `scripts/bench/fixtures/phase13_null_consumer.Cargo.lock`
- Commits are ancestors of HEAD: `0726073`, `18f4a5b`, `d992f6f`
- `python3 scripts/bench/phase13.py --rehearsal` exits 0
- `python3 -m unittest scripts.bench.tests.test_phase13_driver` — 80 tests OK
- `python3 -m unittest discover -s scripts/bench/tests -t .` — 797 tests OK (1 skipped)
- `git status` over `src/`, `pyo3/src/`, `examples/` — clean
