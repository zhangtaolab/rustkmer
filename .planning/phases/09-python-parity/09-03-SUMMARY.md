---
phase: 09-python-parity
plan: "03"
subsystem: benchmark-harness
tags: [python-benchmark, pyo3, baseline-comparison, exit-contract, threshold-gate, d2]
requires:
  - phase: 09-python-parity
    plan: "01"
    provides: "shared counting engine on PyCounter file methods + resolved threads field"
  - phase: 05-measurement-regression-harness
    provides: "fresh-worker Python benchmark, N-free control, committed dev-host baseline"
provides:
  - "--compare-baseline dual fresh-process arms (threads=1 and default) on the N-free control"
  - "Locked verdict math (speedup_t1 >= 1.0, speedup_default >= 1.2, inclusive, no noise band)"
  - "0/1/2 exit contract: exit-1 artifact retention, artifact-free exit 2"
  - "Verdict/guard/controller unit suite (65 python_bench tests pass, 1 opt-in skip)"
  - "Post-D2 real-N labels and the updated bench README operator contract"
affects:
  - scripts/bench/python_bench.py
  - scripts/bench/tests/test_python_bench.py
  - scripts/bench/README.md
  - "09-05 (measured comparison run and evidence artifact)"
tech-stack:
  added: []
  patterns:
    - "Fresh worker process per (arm, thread configuration) — the global rayon pool is first-call-wins"
    - "Pre-timing identity gate: CLI-vs-Python parity AND baseline exact counts AND control sha256"
    - "Pure verdict function with inclusive thresholds; artifact written on PASS and genuine FAIL"
key-files:
  created: []
  modified:
    - scripts/bench/python_bench.py
    - scripts/bench/tests/test_python_bench.py
    - scripts/bench/README.md
decisions:
  - "Compare mode measures only the two N-free-control arms; the real-N arm is never a comparison basis"
  - "Threads are recorded as an int for N and the string \"default\" for all-cores — never null"
  - "The comparison artifact uses mode \"compare-baseline\" while params.threads stays 1 (the baseline-comparable arm)"
  - "--emit-baseline and --compare-baseline are mutually exclusive; a comparison never re-pins a baseline"
  - "Non-compare arms also honor --threads so every arm record reports the actual configuration"
patterns-established:
  - "Pre-timing guards: parity_counts, baseline exact-count equality, regenerated-control fingerprint equality"
  - "Exit contract: 0 PASS / 1 valid FAIL with artifact / 2 invalid with no artifact"
requirements-completed: [PY-02]
coverage:
  - id: D1
    description: "--compare-baseline measures threads=1 and default arms as fresh workers and writes a schema+provenance-valid artifact on PASS and genuine FAIL"
    requirement: PY-02
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_python_bench.py#TestCompareController"
        status: pass
    human_judgment: false
  - id: D2
    description: "Locked verdict math and every exit-2 guard are unit-proven with synthetic baselines"
    requirement: PY-02
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_python_bench.py#TestCompareToBaseline, #TestBaselineIdentityGuards, #TestParseThreads"
        status: pass
    human_judgment: false
  - id: D3
    description: "Bench README documents the compare invocation, both arms, locked thresholds, exit contract, .venv313 commands, and post-D2 labels"
    requirement: PY-02
    verification:
      - kind: other
        ref: "Task 3 grep gates over scripts/bench/README.md"
        status: pass
    human_judgment: false
metrics:
  duration: "4m 16s"
  completed: "2026-11-13"
status: complete
actuals:
  tokens: 13289
  tasks: 3
  commits: 3
  plan_head_before: 57ba6d959e9d5dd14a328e51de944365ff1b09cb
  plan_head_after: 95c36202c792c941eb4bfbda58c980a2723a850e
---

# Phase 9 Plan 03: Baseline Comparison Harness Summary

`--compare-baseline` now measures threads=1 and default-threads arms as fresh workers on the N-free control, with parity/exact-count/fingerprint guards before timing, locked inclusive 1.0x/1.2x thresholds, and the 0/1/2 exit contract proven by 65 unit tests.

## Performance

- **Duration:** 4m 16s
- **Started:** 2026-11-13T01:50:47Z
- **Completed:** 2026-11-13T01:55:03Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- `python_bench.py` gained `parse_threads` (`default` -> None, N >= 1), a `--threads`
  worker/controller flag, and per-arm threading so the threads=1 isolation arm and the
  all-cores default arm always run in separate fresh processes.
- `validate_baseline_identity` rejects platform-flavor, provenance-platform, k/canonical,
  fingerprint-shape, and exact-count-shape mismatches before provisioning; compare mode
  additionally requires CLI-vs-Python parity, baseline exact-count equality, and
  regenerated-control fingerprint equality before any timing.
- `compare_to_baseline` implements the locked math (`speedup_t1 = baseline_t1 / new_t1`,
  `speedup_default = baseline_t1 / new_default`) with inclusive 1.0/1.2 boundaries and no
  noise band; the artifact is written on PASS and on a genuine FAIL, never on exit 2.
- Exit 1 is wired to a valid FAIL with its artifact retained; the module docstring, constant
  comment, and argparse description no longer describe it as reserved-and-never-emitted.
- The real-N evidence class moved to post-D2 wording (exactly one literal occurrence in the
  code, the constant assignment) with a semantics note stating the counts are post-D2 skip-N
  values not comparable to the pre-D2 committed baseline; the committed baseline is untouched.
- The bench README now carries the exact compare invocation, both arms, both thresholds, the
  anchored exit-contract line, `.venv313/bin/python` differential commands, scratch-only
  pre-D2 recording, the immutable Phase 5 artifact, and the dev-host-only/CI boundary.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add per-arm thread configuration and --compare-baseline with its exit contract** - `fb441dd` (feat)
2. **Task 2: Extend the harness unit suite for verdict, guards, and exit paths** - `fb419cc` (test)
3. **Task 3: Update the bench README** - `95c3620` (docs)

## Files Created/Modified

- `scripts/bench/python_bench.py` - `parse_threads`, baseline identity/verdict helpers, dual control arms, compare mode, 0/1/2 exit contract, post-D2 labels
- `scripts/bench/tests/test_python_bench.py` - parse/verdict/guard/controller matrices and the two updated label assertions
- `scripts/bench/README.md` - compare-mode operator contract, `.venv313` commands, post-D2 labels, exit contract

## Decisions Made

- Compare mode measures only the two N-free-control arms; the real-N arm is excluded because
  its post-D2 counts are not comparable to the pre-D2 committed baseline.
- An arm's `threads` field is an int for a concrete N and the string `"default"` for all
  cores — never null, so the artifact records the actual configuration.
- The comparison document reports `mode: "compare-baseline"` while `params.threads` stays 1:
  that is the arm compared against the committed sequential baseline.
- `--emit-baseline` + `--compare-baseline` is rejected up front instead of writing a
  comparison artifact and then failing on baseline construction.
- Non-compare arms honor `--threads` too, so a controller run never silently ignores the flag
  (the default `"1"` keeps the committed capture semantics unchanged).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree base was stale**
- **Found during:** pre-execution worktree verification
- **Issue:** the worktree HEAD was `2fc58cb`, an ancestor of the plan's expected base
  `57ba6d9`; the phase-9 plan, the 09-01 wave-1 work, and the pyo3 engine cutover were absent.
  Executing 09-03 from that tree would have measured and extended the wrong codebase.
- **Fix:** verified the branch had zero own commits and a clean tree, then fast-forwarded the
  agent branch to the expected base with `git merge --ff-only 57ba6d9`.
- **Files modified:** none
- **Verification:** HEAD == `57ba6d9`, branch `worktree-agent-a0d56b8f9ec09ee61`, clean tree
- **Committed in:** N/A (no commit)

**2. [Rule 2 - Missing Critical] Reject contradictory compare/baseline modes early**
- **Found during:** Task 1
- **Issue:** `--compare-baseline` and `--emit-baseline` both allow slice mode; without a guard
  the run would write the comparison artifact and then exit 2 while trying to build a
  baseline from a non-slice-mode document — an artifact left on an exit-2 path.
- **Fix:** added an up-front mutual-exclusion guard and validated the controller's `--threads`
  via `parse_threads` before provisioning.
- **Files modified:** `scripts/bench/python_bench.py`
- **Verification:** `test_compare_and_emit_baseline_are_mutually_exclusive` asserts exit 2 with
  no artifact; `TestParseThreads` covers invalid controller values.
- **Committed in:** `fb441dd` (Task 1 commit)

---

**Total deviations:** 2 (1 blocking setup fix, 1 missing-critical guard)
**Impact on plan:** The worktree fix was required to execute at all; the guard keeps exit-2
paths artifact-free as the plan's exit contract requires. No scope creep.

## Issues Encountered

- The full `python3 -m unittest discover -s scripts/bench/tests -t .` run in this worktree
  reports 2 failures in `test_schema` because `target/release/rustkmer` is an untracked build
  artifact absent from fresh worktrees; those tests spawn that binary. The targeted suite
  (`-p test_python_bench.py`) is green (65 tests, 1 opt-in skip), and the failure is
  environmental, not caused by this plan. A maintainer running the full discovery from a
  built checkout sees it green.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required. The measured comparison itself is 09-05's
job and needs the rebuilt `.venv313` extension plus the local dataset.

## Next Phase Readiness

- 09-05 can run the exact command documented in `scripts/bench/README.md` to produce
  `evidence/python_bench_after_d2.json`; PASS returns 0 and a genuine FAIL returns 1 with the
  artifact retained.
- The committed baseline (`sha256 42bb480d…`) and its `32.14 s` / `129579577` / `73476107` /
  `5cc93333…` pins are unmodified and asserted at run time.
- No CI comparison gate was added; Phase 10 owns CI-class baselines.

---

## Self-Check: PASSED

- `scripts/bench/python_bench.py` exists and contains exactly one post-D2 label literal, zero
  pre-D2 literals, and the two required helpers.
- `scripts/bench/tests/test_python_bench.py` exists with >= 2 post-D2 label occurrences and zero
  pre-D2 literals; the targeted suite passes.
- `scripts/bench/README.md` exists and passes every Task 3 anchored grep gate.
- Commits `fb441dd`, `fb419cc`, `95c3620` are ancestors of HEAD.
- The committed baseline file is byte-identical (sha256 `42bb480d…`).

*Phase: 09-python-parity*
*Completed: 2026-11-13*
