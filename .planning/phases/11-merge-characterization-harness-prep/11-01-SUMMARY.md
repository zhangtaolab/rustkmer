---
phase: 11-merge-characterization-harness-prep
plan: 01
subsystem: testing
tags: [python, benchmark-harness, jellyfish, merge, unittest, stdlib-only, counterbalanced-protocol]

# Dependency graph
requires:
  - phase: 10-benchmark-verdict (v2.0 milestone)
    provides: counterbalanced comparison protocol, results schema v1, count-parity gate, render-report renderer, BenchmarkConfig fairness matrix
provides:
  - jellyfish_merge_cmd command builder (list-form argv, validate_path everywhere, no flag copying between jellyfish subcommands)
  - build_merge_cmd num_threads parameter (merge-t1 like-for-like single-thread arm)
  - assert_arm_ordering count-before-merge invariant guard (fail-loud RuntimeError protecting warmup-runs-first-spec semantics)
  - seven-arm comparison spec set: count-A, count-B, merge, merge-t1, jellyfish-count-A, jellyfish-count-B, jellyfish-merge
  - renderer merge-vs-jellyfish-merge delta rows with byte-compat n/a branch for pre-Phase-11 files
  - MBENCH-05 CI degradation rung pinned by unit tests (single-rep path: count-A, count-B, merge; no jellyfish dependency)
affects: [Phase 12 Full-Scale Merge Verdict, 11-02 and later Phase 11 plans (parity gate spec, characterization ladder, prepare-inputs), MBENCH-04 cost-model check]

# Actuals (#2632) — pairs with the plan's estimate (65000) to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 5733    # chars/4 over git diff 03373b5..HEAD at SUMMARY time
  tasks: 3
  commits: 3      # MEASURED: git rev-list --count gsd-plan-head-before-11-01..HEAD
plan_head_before: 03373b5c3611ceda41dea4616701b12ae5e47a21
plan_head_after: 8aa44dd75f75c8e84a4ee46425daac9dda2ce359

# Tech tracking
tech-stack:
  added: []       # stdlib-only contract preserved (bench.py:25-26); no package installs (T-11-SC)
  patterns:
    - "Count-before-merge arm ordering as an executable invariant (assert_arm_ordering) rather than a convention"
    - "Renderer conditional extension via an optional param (merge_base) — legacy n/a branch untouched for old files"
    - "Flag-collision hygiene: jellyfish subcommand builders each carry only their own literal flag set (merge's -m is MIN mode)"

key-files:
  created:
    - scripts/bench/tests/test_merge_arms.py
  modified:
    - scripts/bench/bench.py
    - scripts/bench/tests/test_schema.py
    - scripts/bench/tests/test_render_report.py
    - scripts/bench/tests/test_degradation.py

key-decisions:
  - "Renderer extension kept minimal per plan scope: _arm_row gains an optional merge_base param and only the 'merge' row's delta source changes; merge-t1 / jellyfish-merge are not yet table rows (Phase 12 renderer work can extend the tables)"
  - "--skip-merge now excludes all three merge arms (merge, merge-t1, jellyfish-merge) symmetrically, preserving the flag's counting-only semantics"
  - "jellyfish-count-B derives from cfg_b (dataclasses.replace(cfg_a, inputs=[inputs[1]])) so the merge hash-size equality precondition holds by construction (D-01)"

patterns-established:
  - "Ordering assertion pattern: generic name-based invariant (any arm list), not pinned to the current seven names"
  - "Byte-compat renderer pattern: new behavior activates only when the new arm exists in the same results file"

requirements-completed: [MBENCH-01, MBENCH-05]

# Coverage metadata (#1602) — one entry per shipped deliverable.
coverage:
  - id: D1
    description: "Seven-arm comparison runs end-to-end at synthetic scale under the counterbalanced protocol with parity + conservation gates green (tracer)"
    requirement: MBENCH-01
    verification:
      - kind: integration
        ref: "command: python3 scripts/bench/bench.py --mode synthetic --reads 20000 --k 21 --reps 2 --self-check --out /tmp/p11-tracer-results.json (ran twice: pre-commit and post-commit tracer gate; all seven arms present, distinct>0, rustkmer merge == jellyfish-merge on counts: 5,199,995 distinct / 5,200,000 total)"
        status: pass
    human_judgment: false
  - id: D2
    description: "assert_arm_ordering fails loud (RuntimeError) on any count-after-merge ordering within a tool and stays green on the shipped seven-arm order"
    requirement: MBENCH-01
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_merge_arms.py#TestAssertArmOrdering"
        status: pass
    human_judgment: false
  - id: D3
    description: "jellyfish_merge_cmd exact argv shape + validate_path rejection + no -t/-s/-m flag copying; build_merge_cmd num_threads exact-shape cases"
    requirement: MBENCH-01
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_merge_arms.py#TestJellyfishMergeCmd"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_merge_arms.py#TestBuildMergeCmdThreads"
        status: pass
    human_judgment: false
  - id: D4
    description: "Results with all seven arm names validate unchanged under schema v1; SCHEMA_VERSION stays 1 (no second schema)"
    requirement: MBENCH-05
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_schema.py#TestSevenArmSchemaTolerance"
        status: pass
    human_judgment: false
  - id: D5
    description: "Renderer renders merge-vs-jellyfish-merge deltas when a jellyfish-merge arm exists; legacy n/a branch preserved byte-compat without it"
    requirement: MBENCH-01
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_render_report.py#TestJellyfishMergeDelta"
        status: pass
    human_judgment: false
  - id: D6
    description: "CI degradation rung: single-rep synthetic path produces a schema-v1-valid file with count-A, count-B, merge and no jellyfish arms; rung cannot pass vacuously"
    requirement: MBENCH-05
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_degradation.py#TestCIIntegrationRung"
        status: pass
      - kind: integration
        ref: "command: python3 scripts/bench/bench.py --mode synthetic --reads 20000 --out /tmp/p11-ci-rung.json (asserted names == [count-A, count-B, merge])"
        status: pass
    human_judgment: false

# Metrics
duration: 18min
completed: 2026-11-16
status: complete
---

# Phase 11 Plan 01: Merge Arm Harness Extension Summary

**Seven-arm merge comparison wired into bench.py — jellyfish merge + per-part count arms + single-thread rustkmer merge-t1 under the counterbalanced protocol, proven end-to-end at synthetic scale with the CI rung pinned in schema v1 (MBENCH-01/MBENCH-05)**

## Performance

- **Duration:** 18 min
- **Started:** 2026-11-16T12:44:30Z
- **Completed:** 2026-11-16T13:02:36Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- MBENCH-01 harness side complete: `jellyfish_merge_cmd`, `build_merge_cmd(num_threads=...)`, `assert_arm_ordering`, and the seven-arm spec set (count-A, count-B, merge, merge-t1, jellyfish-count-A, jellyfish-count-B, jellyfish-merge) run end-to-end under the existing counterbalanced protocol; at synthetic scale rustkmer merge and jellyfish-merge agree exactly (5,199,995 distinct / 5,200,000 total), count-parity and merge conservation green
- MBENCH-05 complete: CI degradation rung (reps=1: count-A, count-B, merge, no jellyfish) validated under schema v1, SCHEMA_VERSION unchanged, unit tests pin the shape and reject a vacuous pass (empty reps)
- Renderer byte-compat preserved: `_arm_row`'s legacy n/a branch intact for committed pre-Phase-11 files; merge row carries real deltas vs a jellyfish-merge arm when one exists
- Tracer feedback gate passed: the Task 1 verify re-ran green post-commit before any expansion task

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end seven-arm synthetic run** - `cf42c26` (feat)
2. **Task 2: Unit tests — command shapes, ordering, threads, schema, renderer** - `47899e6` (test)
3. **Task 3: MBENCH-05 CI degradation rung** - `8aa44dd` (test)

## Files Created/Modified
- `scripts/bench/bench.py` - jellyfish_merge_cmd builder, build_merge_cmd num_threads param, assert_arm_ordering, seven-arm spec wiring, renderer merge_base param
- `scripts/bench/tests/test_merge_arms.py` - NEW: builder shapes, ordering GREEN/RED, flag-collision guard (11 tests)
- `scripts/bench/tests/test_schema.py` - seven-arm schema tolerance + SCHEMA_VERSION pin (2 new tests)
- `scripts/bench/tests/test_render_report.py` - merge delta rows / n/a byte-compat (2 new tests)
- `scripts/bench/tests/test_degradation.py` - CI rung validation + vacuous-pass rejection (2 new tests)

## Decisions Made
- Renderer extension scoped exactly to the plan's `_arm_row` conditional: merge-t1 and jellyfish-merge are not yet rendered as table rows (left for Phase 12 renderer work)
- `--skip-merge` excludes all three merge arms symmetrically (counting-only semantics preserved)
- jellyfish-count-B built from `cfg_b` with byte-identical -m/-s/-C per D-01, making jellyfish merge's hash-size precondition hold by construction

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- **Full-suite CI-gate command exits non-zero due to 4 PRE-EXISTING failures unrelated to this plan** (verified: the 11-01 diff touches only the 5 plan files; causes predate the plan):
  - 3 tests in `test_phase10_verdict.py` read `.planning/phases/10-benchmark-verdict/*.json`, moved to `.planning/milestones/v2.0-phases/10-benchmark-verdict/` by commit `97c497c` (v2.0 milestone archive)
  - 1 documented macOS `sample`-race flake in `test_verify_threads.py` (STATE.md Blockers/Concerns), reproduced
  - Logged to `deferred-items.md` in the phase directory; every module this plan created or extended is green (11 + 19 + 24 + 70 tests), remaining ~464 tests unaffected
- In-task (never committed broken): an f-string syntax error in the new `_arm_row` branch was caught by the Task 2 verify and fixed before commit; the renderer tests initially omitted the required mode=full companion file and were corrected to the existing fixture pattern

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Ready for 11-02 (next plan in the phase): the seven-arm protocol, ordering guard, and schema-v1 CI rung this plan provides are the harness foundation for the parity-gate spec, prepare-inputs stage, and characterization ladder
- Note for 11-04 (three-way merge gate): the parity gate and self-check were deliberately left untouched here; the synthetic-scale three-way agreement observed in the tracer (rustkmer merge == jellyfish-merge on counts) is encouraging but was NOT gated — that is Plan 11-04's scope
- Known flake warning carried: trust `test_verify_threads.py` reds only after purging stale `target/` artifacts (STATE.md)

---
*Phase: 11-merge-characterization-harness-prep*
*Completed: 2026-11-16*

## Self-Check: PASSED

All created files exist on disk; all task commits (cf42c26, 47899e6, 8aa44dd) are ancestors of HEAD; plan_head_after (8aa44dd) matches HEAD at self-check time.
