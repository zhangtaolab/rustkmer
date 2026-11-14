---
phase: 05-measurement-regression-harness
plan: 07
subsystem: infra
tags: [ci, benchmark, regression-gate, thread-scaling, expected-red, provenance, python-benchmark, documentation]

requires:
  - phase: 05-measurement-regression-harness
    plan: 01
    provides: "scripts/bench/thread_scaling.py (--measure-only / --current exit contract), shared binary_provenance"
  - phase: 05-measurement-regression-harness
    plan: 02
    provides: "scripts/bench/random_slice.py; Rust 1.82 MSRV"
  - phase: 05-measurement-regression-harness
    plan: 03
    provides: "hardened verify_threads.py + pool-size Rust test pair (characterization + ignored standing gate)"
  - phase: 05-measurement-regression-harness
    plan: 04
    provides: "slice_parity.crr1936095.json + bench.py parity-reference flags"
  - phase: 05-measurement-regression-harness
    plan: 05
    provides: "contention_bench.py"
  - phase: 05-measurement-regression-harness
    plan: 06
    provides: "python_bench.py + dev-host baseline + n_read_differential.py"
  - phase: 04-benchmark-validation
    provides: "v1.0 benchmark.yml release-build -> upload -> compare gate sequence"

provides:
  - "Standing CI gates in .github/workflows/benchmark.yml: harness unittest suite, Python-surface benchmark, and the PROF-02 thread-scaling measure -> upload -> verdict chain"
  - "Evidence-retention rule: all three artifact uploads carry if: always() + if-no-files-found: warn; measurement/gate steps carry no conditions"
  - "Intentionally-red PROF-02 verdict surfaced as a real job failure until Phase 6 (PAR-01), documented in the workflow itself"
  - "Maintainer README: commands for all seven new tools, Expected RED gates (PROF-02) doctrine + Phase 6 handoff checklist, provenance field reference, dev-host vs CI-class baseline bootstrap, updated Layout"
affects: [06-parallelism, 09-python-parity, 10-verdict]

actuals:
  tokens: 5646
  tasks: 2
  commits: 2
plan_head_before: 732af4009b5ddaf795a348fa97c06ae9518f1fb4
plan_head_after: 1800263e2046fac7f67fdcc15c4159c35d0d3080

tech-stack:
  added: []
  patterns:
    - "standing CI gate order: build -> unit suite -> measure -> upload -> gate, trusting script exit codes directly"
    - "evidence-retention exception: artifact uploads run always() and never affect the job verdict; measurement/gate steps remain unconditional"
    - "intentional-RED documented at the controlling comment block and at the red step, naming Phase 6 / PAR-01"

key-files:
  created: []
  modified:
    - .github/workflows/benchmark.yml
    - scripts/bench/README.md

key-decisions:
  - "No Python compare gate in CI: no CI-class Python baseline exists, and comparing CI numbers to the committed dev-host baseline would violate the per-runner-class rule (Phase 10 owns CI baselines)"
  - "Scaling gate is a two-step measure-only -> upload -> --current verdict chain so the evidence artifact survives the intentional RED; the verdict step is the last step and fails the job by design until Phase 6"
  - "All three upload steps (existing bench-results, python-bench-results, thread-scaling) carry if: always() + if-no-files-found: warn; no measurement or gate step carries a condition and no error-softening construct was introduced"
  - "README names the prohibited silencing constructs (continue-on-error, || true / ; true, conditional gates, baseline recapture) explicitly while the workflow comments deliberately avoid the literal tokens so the negative grep gate stays meaningful"

patterns-established:
  - "An always() artifact upload is evidence retention, not error softening: it runs no gate and cannot change the job verdict; the failed measurement/gate step still fails the job"
  - "Expected-RED doctrine names the exact tests to flip (un-ignore standing gate; invert/remove characterization test) so Phase 6 has an unambiguous green-target checklist"

requirements-completed: [PROF-01, PROF-02, PROF-04]

coverage:
  - id: D1
    description: "benchmark.yml runs the harness unit suite, the Python-surface benchmark with artifact upload, and the PROF-02 measure -> upload -> verdict chain, with all three uploads carrying if: always() + if-no-files-found: warn and no error-softening constructs"
    requirement: "PROF-02"
    verification:
      - kind: other
        ref: "ruby -ryaml YAML.load_file + grep counts: thread_scaling.py=3, python_bench.py=1, unittest discover=1, if: always()=3, if-no-files-found: warn=3, measure-only=3, --current thread_scaling.json=1; grep -E 'continue-on-error|\\|\\| true' finds none"
        status: pass
    human_judgment: false
  - id: D2
    description: "README documents all seven new tools with real CLI flags, the Expected RED gates (PROF-02) section with the Phase 6 handoff checklist, provenance fields, dev-host vs CI-class baseline bootstrap, CI evidence-retention rule, and the updated Layout"
    requirement: "PROF-01"
    verification:
      - kind: other
        ref: "grep gates: thread_scaling.py=7, expected RED=2, random_slice.py=3, expect-unified=2, capture_goldens.py=3, continue-on-error=1; flags spot-checked against every script's --help"
        status: pass
    human_judgment: false

duration: 4min
completed: 2026-11-12
status: complete
---

# Phase 5 Plan 7: Standing CI Gates & Harness Documentation Summary

**The Phase 5 harness gates are now standing in CI (unit suite + Python benchmark + intentionally-red PROF-02 scaling), with evidence-preserving `always()` uploads, and the README gives maintainers the full tool/provenance/Phase-6-handoff playbook.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-11-12T10:15:56Z
- **Completed:** 2026-11-12T10:19:17Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `.github/workflows/benchmark.yml` now runs, in order: release build → harness unittest suite → synthetic BENCH-01 measure/upload/gate → maturin wheel build/install → `python_bench.py` + upload → thread-scaling `--measure-only` + upload → the PROF-02 `--current` verdict (last).
- All three evidence uploads (`bench-results-<OS>`, `python-bench-results-<OS>`, `thread-scaling-<OS>`) carry `if: always()` + `if-no-files-found: warn`, so a failed measurement step still leaves its artifact without altering the job verdict.
- The PROF-02 red is documented in the workflow's controlling comment block and at the verdict step as intentional until Phase 6 (PAR-01); no `continue-on-error`, `|| true`, conditional gate, or baseline recapture exists.
- `scripts/bench/README.md` documents all seven new tools with flags verified against each script's `--help`, the "Expected RED gates (PROF-02)" section, the Phase 6 handoff checklist, the provenance field reference, the dev-host vs CI-class Python baseline bootstrap, and the updated Layout tree.

## Task Commits

Each task was committed atomically:

1. **Task 1: Standing CI gates in benchmark.yml** - `93434f5` (feat)
2. **Task 2: README — tools, expected-RED doctrine, Phase 6 handoff** - `1800263` (docs)

**Plan metadata:** `PENDING` (docs: complete plan)

## Files Created/Modified

- `.github/workflows/benchmark.yml` — added harness unit tests, Python-surface benchmark + upload, scaling measure/upload/verdict; all three uploads gained `always()` + `if-no-files-found: warn`; controlling comment block extended with the evidence-retention rule and the intentional PROF-02 red.
- `scripts/bench/README.md` — Quick runs for every new tool, Expected RED gates + Phase 6 handoff, provenance fields, CI-class Python baseline bootstrap, CI evidence-retention rule, updated Layout.

## Decisions Made

- No Python compare gate in CI: there is no CI-class Python baseline yet, and comparing a CI run against the dev-host baseline would violate the per-runner-class rule. The artifact is the Phase 10 bootstrap input.
- The scaling gate is split measure-only → upload → `--current` verdict so the RED run leaves its evidence; only the final verdict step carries the failure.
- README names the prohibited silencing constructs (`continue-on-error`, `|| true`/`; true`, conditional gates, baseline recapture) explicitly, while the workflow comments avoid the literal tokens so the negative grep gate remains a meaningful check.

## Deviations from Plan

None - plan executed exactly as written.

## Verification

Commands run and their actual results:

```
ruby -ryaml YAML.load_file('.github/workflows/benchmark.yml')  -> OK
grep -c 'thread_scaling.py' benchmark.yml                      -> 3  (>=2)
grep -c 'python_bench.py' benchmark.yml                        -> 1  (>=1)
grep -c 'unittest discover' benchmark.yml                      -> 1  (>=1)
grep -Eq 'continue-on-error|\|\| true' benchmark.yml           -> no match
grep -c 'if: always()' benchmark.yml                           -> 3  (>=3)
grep -c 'if-no-files-found: warn' benchmark.yml                -> 3  (>=3)
grep -c 'measure-only' benchmark.yml                           -> 3  (>=1)
grep -c -- '--current thread_scaling.json' benchmark.yml       -> 1  (>=1)
grep -c 'thread_scaling.py' README.md                          -> 7  (>=1)
grep -c 'expected RED' README.md                               -> 2  (>=1)
grep -c 'random_slice.py' README.md                            -> 3  (>=1)
grep -c 'expect-unified' README.md                             -> 2  (>=1)
grep -c 'capture_goldens.py' README.md                         -> 3  (>=1)
grep -c 'continue-on-error' README.md                          -> 1  (>=1)
python3 -m unittest discover -s scripts/bench/tests -t .        -> Ran 302 tests, OK (skipped=1), exit 0
```

Step order extracted from the workflow: Build release binary (85) → Harness unit tests (89) → Run synthetic benchmark (91) → Upload results (96) → Gate against committed baseline (103) → Install maturin (114) → Build PyO3 extension wheel (116) → Install PyO3 extension wheel (118) → Run Python benchmark (120) → Upload Python benchmark results (123) → Measure thread scaling (135) → Upload thread-scaling results (138) → Thread-scaling verdict (149, last).

## Known Stubs

None. The intentional PROF-02 red is a measured gate observing a real bug, not a stub; it is tracked for Phase 6 and documented in both the workflow and README.

## Threat Flags

None — no new network endpoints, auth paths, file-access patterns, or schema changes at trust boundaries. `permissions: contents: read` is unchanged; the only new CI installs are maturin (existing `>=1.0,<2.0` pin from ci.yml) and numpy (existing runtime dependency).

## Issues Encountered

None.

## Next Phase Readiness

- Phase 6 (PAR-01) inherits an explicit green-target checklist: un-ignore `pool_size_matches_requested_threads`, invert/remove `pool_size_baseline_records_default_pool`, then the local and CI scaling verdicts go green.
- Real-data gates (CRR1936095 / jellyfish) remain dev-host procedures (Plan 04), not hidden CI skips; CI runs the synthetic degradation ladder only.
- Phase 10 owns CI-class Python baselines; the `python-bench-results-<OS>` artifact is the bootstrap input.

## Self-Check: PASSED

- FOUND: `.github/workflows/benchmark.yml`
- FOUND: `scripts/bench/README.md`
- FOUND: `.planning/phases/05-measurement-regression-harness/05-07-SUMMARY.md`
- FOUND: commit `93434f5`
- FOUND: commit `1800263`

---
*Phase: 05-measurement-regression-harness*
*Completed: 2026-11-12*
