---
phase: quick
plan: 261117-ala
subsystem: testing
tags: [bench-harness, pytest-less-unittest, archived-artifacts, README, path-retarget]

# Dependency graph
requires:
  - phase: 10-benchmark-verdict (archived)
    provides: the archived evidence dir .planning/milestones/v2.0-phases/10-benchmark-verdict/ and its JSON artifacts
  - phase: 11-merge-characterization-harness-prep
    provides: 11-REHEARSAL-RESULTS.json recorded command_line strings (flag authority for the README block)
provides:
  - Green bench suite: the 3 red tests in scripts/bench/tests/test_phase10_verdict.py pass against the archived Phase-10 directory
  - README WR-04 rehearsal Stage A/B commands copy-pasteable and flag-for-flag identical to the four recorded runs
affects: [phase-12-full-scale-merge-verdict, bench-harness-users]

# Actuals (#2632)
actuals:
  tokens: 2314    # chars/4 over the realized diff (9258 chars across the 4 changed files)
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Path-constant retarget only: archived-artifact repointing done without touching test logic"
    - "Byte-preserving JSON edits: string substitution of path VALUES only, never re-serialization"

key-files:
  created: []
  modified:
    - scripts/bench/tests/test_phase10_verdict.py
    - scripts/bench/README.md
    - .planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-python-k21.json
    - .planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-python-k31.json

key-decisions:
  - "Kept the plan's verbatim Stage A/B command block (both loops carry --disk-floor-gb 2) over the gate's '= 2' line-count expectation — flag-for-flag identity with recorded runs outranks the miscounted gate arithmetic (see Deviations)"

patterns-established:
  - "Archived JSON path retargets: substitute the directory prefix inside the path-string values only; every sha256/number byte stays untouched and the suite re-derives all content hashes on every run"

requirements-completed: []

coverage:
  - id: D1
    description: "The 3 previously red tests in test_phase10_verdict.py pass against the archived dir (preflight revalidate + historical pin at k=21/31)"
    verification:
      - kind: unit
        ref: "python3 -m unittest discover -s scripts/bench/tests -t . -p test_phase10_verdict.py (Ran 99 tests, OK)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Full bench suite green (0 failures 0 errors)"
    verification:
      - kind: unit
        ref: "python3 -m unittest discover -s scripts/bench/tests -t . (Ran 644 tests, OK, skipped=1 pre-existing)"
        status: pass
    human_judgment: false
  - id: D3
    description: "README rehearsal commands flag-for-flag identical to the four recorded command_line strings in 11-REHEARSAL-RESULTS.json"
    verification:
      - kind: other
        ref: "token-expansion comparison script (all four: IDENTICAL) + plan gate greps (brace-k=0, section --input=2, slice-reads 50000/200000 each 1)"
        status: pass
    human_judgment: false

# Metrics
duration: 5min
completed: 2026-11-17
status: complete
---

# Quick Task 261117-ala: Retarget Phase-10 Verdict Tests + Fix README Rehearsal Commands — Summary

**3 red phase10 verdict tests repointed to .planning/milestones/v2.0-phases/ and README WR-04 rehearsal block replaced with the real recorded Stage A/B commands; full bench suite green (644 tests OK)**

## Performance

- **Duration:** 5 min
- **Started:** 2026-11-16T23:46:23Z
- **Completed:** 2026-11-16T23:51:29Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Retargeted the two stale Path constructions in `scripts/bench/tests/test_phase10_verdict.py` (preflight artifact path + `TestCommittedHistoricalCliEvidence.PHASE_DIR`) by inserting `"milestones" / "v2.0-phases"` after `".planning"` — zero test-logic change (8-line diff, both constants only)
- Substituted exactly the 5 directory-prefix path-string VALUES per archived JSON (`10-results-python-k21.json`, `-k31.json`); every sha256/number byte untouched (diff confirms: 5 path lines changed per file, nothing else)
- Replaced the two defective README Shape cells (Stage A missing `--input` — exit 1; Stage B brace-expanded `--k {21,31}` collapsing to k=31 only) with true per-k stage shapes, and added the real recorded Stage A/B command block, flag-for-flag identical to the four `command_line` strings in `11-REHEARSAL-RESULTS.json` (mechanically verified: all four token sequences IDENTICAL)
- Suite restored to green: per-file run OK (Ran 99 tests); full discover OK (Ran 644 tests, skipped=1 pre-existing) — the known `test_verify_threads` macOS flake did not fire, no rerun needed

## Task Commits

Each task was committed atomically:

1. **Task 1: Retarget the 3 red tests to the archived Phase-10 directory** - `20caf42` (fix) — 3 files, 14 insertions/14 deletions
2. **Task 2: Fix README WR-04 — rehearsal Stage A/B commands match the recorded runs** - `89b6776` (docs) — 1 file (scripts/bench/README.md only), 20 insertions/2 deletions

## Files Created/Modified

- `scripts/bench/tests/test_phase10_verdict.py` - two path-constant retargets (lines 742-743, 762-763) — no other line touched
- `.planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-python-k21.json` - 5 path values repointed (pre_gate.committed_copy, memory_preflight.source/committed_copy, cross_session.cli_doc/committed_copy)
- `.planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-python-k31.json` - same 5-field shape, k31 names
- `scripts/bench/README.md` - dress-rehearsal Shape cells describe true per-k shape; fenced bash block with the recorded Stage A/B commands (one explicit `--k` per invocation, `--input` present, `--disk-floor-gb 2` present)

## Decisions Made

- Out-of-scope items left untouched per the plan's verified-out list: `10-python-preflight.json` (2 stale paths, loader is content-only), `scripts/bench/phase10.py` `PHASE_DIR` constant + usage text (Phase-12 stage defaults, no currently-running test consumes them)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Task 2 verify gate's `--disk-floor-gb 2` expectation (= 2) is arithmetically unsatisfiable; corrected expectation is 3**
- **Found during:** Task 2 (README WR-04) verification
- **Issue:** The plan mandates (step 1) keeping the surrounding prose unchanged — line 453 already carries one `--disk-floor-gb 2` mention — and (step 3) adding the verbatim command block where BOTH stage loops carry `--disk-floor-gb 2` (required by the must-have truth "flag-for-flag identical ... --disk-floor-gb 2 present"). That is 1 prose line + 2 command lines = 3 matching lines; the gate's `test ... = "2"` can only pass by breaking a stronger requirement (dropping the flag from one stage's command, or editing the protected prose). Planner miscount in the gate arithmetic.
- **Fix:** Honored the stronger constraints (verbatim block, prose intact). Gate run with line provenance: matches at lines 453 (prose), 475 (Stage A), 480 (Stage B) = 3. All other Task 2 gate components pass as written: `--k {21,31}` = 0, section `--input` = 2, section `--slice-reads 50000` = 1, section `--slice-reads 200000` = 1.
- **Files modified:** none beyond the planned README edit
- **Verification:** flag-for-flag token comparison against all four recorded command_line strings: IDENTICAL ×4
- **Committed in:** 89b6776 (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — gate arithmetic, no content change)
**Impact on plan:** None on deliverables — the README content is exactly what the plan's action section specifies; only the gate's expected count was miscomputed. No scope creep.

## Issues Encountered

- None beyond the documented gate-arithmetic deviation. All HEAD baselines matched the plan's recorded planning-time observations exactly (suite FAILED failures=1 errors=2; `v2.0-phases` test-file count 0; stale-prefix JSON counts 5+5; README counts 1/1/0).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Full bench suite is green again; the STATE.md blocker entry "test_phase10_verdict.py reads archived .planning/phases/ paths — 3 full-suite tests red" can be closed
- Phase 12 (Full-Scale Merge Verdict) unaffected: `phase10.py` stage defaults remain as planned out-of-scope carry-forward
- Known pre-existing items intentionally not touched: `10-python-preflight.json` stale paths (no test resolves them), `phase10.py` PHASE_DIR constant/usage text (Phase-12 scope)

---
*Quick task: 261117-ala*
*Completed: 2026-11-17*

## Self-Check: PASSED

- All 4 modified files + SUMMARY verified present on disk
- Commits `20caf42` and `89b6776` verified in HEAD ancestry (branch `dev`, primary checkout, sequential mode)
- Working tree after execution: only the pre-existing `.planning/` edits (config.json, 11-VERIFICATION.md, state.json — dirty before task start) and the untracked SUMMARY directory; no stray code changes; no `.planning/` artifacts committed by the executor
