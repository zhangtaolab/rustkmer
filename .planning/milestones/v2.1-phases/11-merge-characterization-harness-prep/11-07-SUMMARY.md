---
phase: 11-merge-characterization-harness-prep
plan: 07
subsystem: testing
tags: [benchmark-harness, disk-floor, parity-gate, jellyfish, dress-rehearsal, rustkmer]

# Dependency graph
requires:
  - phase: 11-04
    provides: PARITY-GATE.md written spec + assert_merge_parity/dump_vs_dump_equal wired pre-results-acceptance
  - phase: 11-05
    provides: measured 8-artifact inventory + manifest (the D-10 inputs term; 11-PREPARE-RECORD.md)
  - phase: 11-06
    provides: ladder slopes + fitted per-entry rates (the D-10 transient term; 11-LADDER-RESULTS.json)
provides:
  - derive_disk_floor + DEFAULT_DISK_FLOOR_GB=136 derived from recorded evidence, import-time tripwire-pinned (D-10)
  - --disk-floor-override deliberate-run escape with stated shortfall; exit-3 hard block without it (D-11)
  - ensure_disk_headroom per-rep re-check inside run_comparison_protocol (D-12)
  - 11-FLOOR-DERIVATION.md recorded derivation (formula, inputs + sources, arithmetic, 150-vs-136 comparison)
  - green full-protocol slice-scale dress rehearsal evidence (11-REHEARSAL-RESULTS.json: all seven arms x both k, counterbalanced, gates green before medians accepted)
  - README stage docs (prepare-inputs / ladder / disk pre-flight / rehearsal) + WARNING-2 closure (HYG-04)
affects: [12-full-scale-merge-verdict, phase10-controller, MBENCH-04]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
actuals:
  tokens: 16400   # chars/4 over the realized diff (5 files, +1781/-20)
  tasks: 3
  commits: 3       # MEASURED: git rev-list --count f94289a..HEAD

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "import-time derivation tripwire: a derived default literal is pinned to the pure function on the recorded inputs at module import — hand-edits past the derivation fail the import"
    - "derived-floor-as-evidence: floor = measured inputs + ladder-extrapolated largest single-arm transient + documented 1.25 margin, recorded in a phase-dir derivation doc"
    - "gates-before-trust rehearsal: two staged slice runs per k (A = gate-pipeline proof at small scale, B = full protocol), green exit IS the gate proof"

key-files:
  created:
    - scripts/bench/tests/test_disk_floor.py
    - .planning/phases/11-merge-characterization-harness-prep/11-FLOOR-DERIVATION.md
    - .planning/phases/11-merge-characterization-harness-prep/11-REHEARSAL-RESULTS.json
  modified:
    - scripts/bench/bench.py
    - scripts/bench/README.md

key-decisions:
  - "Derived floor is 136 GiB, LOWER than the stale 150 — expected: the old default priced the count-era -s 10G regime; the derived floor prices the measured per-part -s 1G/2G regime (recorded in 11-FLOOR-DERIVATION.md §5)"
  - "Largest single-arm transient = merged .rkdb at k=31 union scale (1,146,353,600 x 20.0 B/entry = 22,927,072,000 B); no temp term invented — no disk-spill observed at either ladder rung, residual variance covered by the 1.25 margin"
  - "DEFAULT_DISK_FLOOR_GB stays an int literal (plan verify regex) but is tripwire-pinned at import to derive_disk_floor(recorded inputs)"
  - "Per-rep D-12 check uses the configured --disk-floor-gb whatever the mode; slice/rehearsal runs pass their scaled budget explicitly (this rehearsal: --disk-floor-gb 2)"
  - "Rehearsal stage A at 50k reads/reps 2 (cheaper gate proof), stage B at the plan's literal command (200k/reps 3); run sequentially to keep the no-concurrent-tools research rule"

patterns-established:
  - "Derived-floor tripwire: DEFAULT == derive(recorded inputs) enforced at import (D-10 drift guard)"
  - "Shortfall-stated breach messages on every under-floor path; override prints and continues, never silent (D-11)"
  - "Rehearsal evidence wraps raw run JSONs with per-stage purpose, gates, t1 semantics (A6), and the RSS-as-context guardrail note"

requirements-completed: [MBENCH-01, MBENCH-02, HYG-04]

coverage:
  - id: D1
    description: "Disk-floor mechanics: derive_disk_floor (pure D-10 arithmetic, 136 GiB derived default tripwire-pinned, stale 150 replaced), exit-3 hard block with stated shortfall + --disk-floor-override deliberate-run escape (D-11), ensure_disk_headroom per-rep re-check in the comparison protocol (D-12)"
    requirement: MBENCH-01
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_disk_floor.py (14 tests: TestDeriveDiskFloor/TestDiskFloorBlock/TestDiskFloorOverride/TestEnsureDiskHeadroom/TestPerRepRecheck) — python3 -m unittest discover -s scripts/bench/tests -t . -k test_disk_floor"
        status: pass
    human_judgment: false
  - id: D2
    description: "Recorded floor derivation: formula, every input value with its source file, full arithmetic, and the 150-vs-136 comparison — 11-FLOOR-DERIVATION.md as D-10 evidence"
    requirement: MBENCH-01
    verification:
      - kind: unit
        ref: "test_disk_floor.py::TestDeriveDiskFloor::test_recorded_inputs_yield_the_derived_default + bench.py import-time tripwire; committed as 722def6"
        status: pass
    human_judgment: false
  - id: D3
    description: "Full-protocol slice-scale dress rehearsal green: all seven arms at both k (21, 31), counterbalanced reps=3 rounds, honest per-rep cache_state, medians + CV, three-way parity + dump-vs-dump gates green before medians accepted; evidence committed as 11-REHEARSAL-RESULTS.json with t1 semantics (A6) and RSS-as-context guardrail"
    requirement: MBENCH-02
    verification:
      - kind: integration
        ref: "plan verify: python3 -c ... 11-REHEARSAL-RESULTS.json (both k, seven arms, gates green) — plus the four staged bench.py runs (stage A 50000x2, stage B 200000x3 per k) all exit 0"
        status: pass
    human_judgment: false
  - id: D4
    description: "README documents the three new stages (prepare-inputs, characterization ladder, disk pre-flight) + the dress-rehearsal stages; WARNING-2 closed in the same touch — stale 'requested + 1' pool-size formula replaced by the 2-at-N=1 / 2N+1-at-N>1 contract with its test citation (HYG-04)"
    requirement: HYG-04
    verification:
      - kind: unit
        ref: "grep gates: 'requested + 1' count == 0; 2N+1 present; prepare_inputs.py / merge_characterize.py / disk-floor-override all documented"
        status: pass
    human_judgment: false

# Metrics
duration: 24min
completed: 2026-11-16
status: complete
---

# Phase 11 Plan 07: Disk-Floor Derivation + Dress Rehearsal Summary

**Derived 136 GiB disk floor landed with block/override/per-rep mechanics (D-10/D-11/D-12), full seven-arm slice-scale dress rehearsal green at both k with parity + dump gates before trust, README stage docs with the WARNING-2 same-touch fix**

## Performance

- **Duration:** 24 min (rehearsal wall 15.4 min inside; floor derivation + mechanics + docs concurrent)
- **Started:** 2026-11-16T16:55:36Z
- **Completed:** 2026-11-16T17:19:05Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Disk floor is now recorded evidence: `derive_disk_floor` + tripwire-pinned `DEFAULT_DISK_FLOOR_GB = 136` (replaces stale 150), derivation + every input source committed as 11-FLOOR-DERIVATION.md
- D-11/D-12 live: every under-floor path states the shortfall (exit 3, or `--disk-floor-override` prints-and-continues), and each measured rep of a comparison protocol re-checks the disk just before its run
- Full-protocol dress rehearsal green: 4 staged runs (A/B × k=21/31), all seven arms × both k, counterbalanced reps=3, honest cache_state, medians + CV, three-way parity + dump-vs-dump green before medians accepted; B-k21 counts exactly reproduce 11-04's proof (29,730,885 / 51,936,393)
- README: prepare-inputs / ladder / disk pre-flight / rehearsal stage docs; WARNING-2's stale pool-size formula replaced with the 2 / 2N+1 contract (HYG-04)

## Task Commits

Each task was committed atomically:

1. **Task 1: Disk-floor mechanics — derive, block, override, per-rep re-check** - `722def6` (feat)
2. **Task 2: Full-protocol slice-scale dress rehearsal** - `fab5e0c` (test)
3. **Task 3: README stage docs + WARNING-2 same-touch fix** - `7e837f1` (docs)

## Files Created/Modified
- `scripts/bench/bench.py` - derive_disk_floor + measured-input constants + import tripwire; check_disk_floor shortfall/override; ensure_disk_headroom; per-rep hook in run_comparison_protocol; --disk-floor-override flag
- `scripts/bench/tests/test_disk_floor.py` - 14 tests (derive arithmetic/margin/raises; block RED-provable; override prints-and-continues; per-rep mid-protocol breach)
- `.planning/phases/11-merge-characterization-harness-prep/11-FLOOR-DERIVATION.md` - D-10 recorded derivation (formula, inputs + sources, enumeration of all arm-output candidates, arithmetic, 150-vs-136)
- `.planning/phases/11-merge-characterization-harness-prep/11-REHEARSAL-RESULTS.json` - wrapping rehearsal evidence: 4 stage docs with command lines, gates, conservation checks, t1 semantics (A6), RSS-as-context guardrail, reproducibility vs 11-04
- `scripts/bench/README.md` - Phase-11 stage docs section + arms bullet update + WARNING-2 fix + layout tree

## Decisions Made
- Floor = 136 GiB (inputs 93,135,484,166 B + largest transient 22,927,072,000 B) × 1.25, ceil — lower than the stale 150 by derivation, not by weakening; old default priced the count-era `-s 10G` regime
- Largest single-arm transient is the k=31 merged `.rkdb` at union scale; no invented temp term (no disk-spill at either ladder rung; margin covers residual variance)
- DEFAULT_DISK_FLOOR_GB kept as an int literal for the plan's verify regex, pinned to the formula by an import-time tripwire (drift = import failure)
- Rehearsal runs sequential (no concurrent tools); stage A proves the gate pipeline at 50k×2, stage B is the plan's literal full-protocol command; slice runs pass `--disk-floor-gb 2` explicitly per the D-12 scaled-budget rule

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Full bench suite (644 tests) carries the two documented pre-existing red families (test_phase10_verdict archived-path errors/failure after 97c497c moved Phase-10 artifacts; the ~50% macOS `sample`-race flake in test_verify_threads — it passed on the final run). Zero reds touch this plan's files; tracked in deferred-items.md since 11-01. Out of scope per the scope-boundary rule.
- Stage-A k=31 / stage-B k=31 jellyfish count arms show high CV (up to ~39%/34%) with cv_warning=True — warnings by design at slice scale (sub-second walls, timer quantization); recorded honestly in the evidence, no gate impact.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 12 consumes everything it needs from this phase: extended seven-arm harness + written PARITY-GATE.md + prebuilt fingerprinted artifacts (11-05) + ladder characterization (11-06) + derived floor with block/override/per-rep (this plan) + green rehearsal evidence (this plan)
- Phase 12 controller should pass the session's computed full budget explicitly via `--disk-floor-gb` (the D-12 full-budget pre-flight) and a scaled budget for any slice-mode runs; re-derive the floor only if the input artifacts or ladder rates change (D-10)
- 397.5+ GiB free at plan close (floor 136 GiB green with wide margin); artifact retention unchanged (D-02: until the Phase 12 verdict lands)

---
*Phase: 11-merge-characterization-harness-prep*
*Completed: 2026-11-16*

## Self-Check: PASSED

All 6 created/modified files verified on disk; all 3 task commits verified as ancestors of HEAD (722def6, fab5e0c, 7e837f1).
