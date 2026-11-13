---
phase: 10-benchmark-verdict
plan: 02
subsystem: testing
tags:
  - benchmark-harness
  - python-stdlib
  - pyo3
  - slice-gate
  - mechanical-report
  - atomic-publish

requires:
  - phase: 10-benchmark-verdict
    provides: "10-01: phase10.py controller spine, ARM_ORDER, run_rounds, verdict_block, memory model, repeatable --inputs worker"
  - phase: 09-python-parity
    provides: "validate_worker_stats / check_rep_identity / build_provenance fresh-worker discipline"
  - phase: 08-output-pipeline-rkdb-v2-parity
    provides: "rotation_schedule and the validate-before-write controller shape"
provides:
  - "scripts/bench/phase10.py: production py-t16 arm (two ordered parts, per-rep module/threads/inputs validation), finalize_python_arm, session and cross-session parity guards"
  - "scripts/bench/phase10.py: full Phase-10 renderer with the five mandatory literals, pinned arm order, recorded-median rendering, atomic verdict+report publish"
  - "scripts/bench/phase10.py: --stage slice-gate with reference sha256 pinned before consumption and k=31 labelled live-parity-only"
  - "scripts/bench/tests/test_python_full_arm.py: 28 tests over the full-arm and stage-document contract"
  - "scripts/bench/tests/test_phase10_verdict.py: TestReport (19) and TestSliceGateRecord (8)"
  - "scripts/bench/README.md: Phase-10 stages, 0/1/2 exit contract, dev-host-only baseline class"
affects:
  - 10-03
  - 10-04

actuals:
  tokens: 29286
  tasks: 3
  commits: 3
  plan_head_before: 377fd7b91648a94af20c7b52758474156626d36b
  plan_head_after: 8c25e42980614ffacfb5e519c735fa4624e5fb33

tech-stack:
  added: []
  patterns:
    - "Fresh-worker full arm: one interpreter per rep, two --inputs in argv order, per-rep module sha256 + threads_resolved == 16"
    - "Session parity as a hard failure: exact counts equal across arms and across sessions, input fingerprints equal across sessions"
    - "Mechanical renderer: documents in, text out; five mandatory literals validated in memory; no clock in the report"
    - "Atomic publish: sibling temp files + os.replace; any failure unlinks both temps and BOTH destinations"
    - "Pin-before-consume: committed reference sha256 and pre-gate sha256 recorded before use"

key-files:
  created:
    - scripts/bench/tests/test_python_full_arm.py
  modified:
    - scripts/bench/phase10.py
    - scripts/bench/tests/test_phase10_verdict.py
    - scripts/bench/README.md

key-decisions:
  - "The py arm validates payload.inputs against the spec's two-part list IN ORDER; a reordered or dropped part is exit 2, never a number."
  - "finalize_python_arm is the single strict py reduction; build_arms routes the py tool through it so a rep-count/module/thread disagreement is a hard failure."
  - "The renderer always emits the cold-cache 'partially satisfied' statement plus a computed per-rep cache_state census; the statement is literal text, not conditional prose."
  - "The render stage treats --out as the rendered report and --verdict-out as the verdict document, per the plan's atomic-publish contract; other stages keep --report-out."
  - "The python stage re-derives the preflight decision via memory_gate and refuses a BLOCKED record (user stop, never a silent skip)."
  - "Slice-gate part tokens are matched on the compression-stripped stem (.fq.gz/.fastq.gz removed first); k=31 is explicitly live-parity-only."

requirements-completed: [BENCH-V2-02]

coverage:
  - id: D1
    description: "py-t16 runs one fresh interpreter per rep over both parts in order and records module path/sha256, threads_resolved, and inputs per rep; every invalid worker outcome is exit 2 with no artifact"
    requirement: BENCH-V2-02
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_python_full_arm.py#TestWorkerArgv"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_python_full_arm.py#TestPythonRepValidation"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_python_full_arm.py#TestPythonStageDocument"
        status: pass
    human_judgment: false
  - id: D2
    description: "The renderer is byte-deterministic, order-pinned, carries all five mandatory literals, and publishes verdict+report atomically (neither destination on exit 2)"
    requirement: BENCH-V2-02
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_phase10_verdict.py#TestReport"
        status: pass
      - kind: regression
        ref: "scripts/bench/tests/test_render_report.py (v1.0 renderer, byte-identical)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The slice-gate record pins the reference sha256 before consumption, labels k=31 live-parity-only, and resolves the real .fq.gz filenames by stripping the compression suffix first"
    requirement: BENCH-V2-02
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_phase10_verdict.py#TestSliceGateRecord"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-11-13
status: complete
---

# Phase 10 Plan 02: Production py-t16 arm, mechanical report, slice-gate record

**The Python surface is now as hard to fool as the Phase-9 slice path at full-input scale, the Phase-10 report is a pure function of the result documents with all five mandatory literals pinned, and the slice-gate evidence record makes the committed reference tamper-evident.**

## Performance

- **Duration:** ~12 min
- **Tasks:** 3
- **Files modified:** 4 (all within the plan's declared scope)
- **Commits:** 3 task commits (measured `git rev-list --count 377fd7b..8c25e42`)

## Accomplishments

- `py-t16`: one fresh `.venv313` interpreter per rep over BOTH split parts via two ordered `--inputs` flags; every rep records the measured native module path, module sha256, `threads_resolved == 16`, and its input list. A zero count, a missing stats file, a non-native module, a module outside the interpreter's site-prefix, a thread mismatch, or a reordered/dropped part is a hard failure (exit 2, no artifact).
- `finalize_python_arm`, `assert_session_parity`, and `assert_cross_session_jellyfish`: exact counts are pinned across reps, across arms within a session, and across the CLI/Python jellyfish arms (counts plus input fingerprints).
- The CLI and Python session stages are wired with the pinned downstream schema: `params.{k,threads,reps}`, arm-level `db_sha256` (equal and non-null for the two rustkmer arms; null for py), CLI `preflight.{basis,distinct_assumed,projected_bytes,budget_bytes,decision,model}`, Python `pre_gate.{path,sha256}`, `memory_preflight.{decision,distinct,projected_bytes,budget_bytes,headroom_bytes,observed_peak_bytes,source,source_sha256}`, and `cross_session.{cli_doc,cli_doc_sha256}`.
- The renderer emits the ordered sections (contract, dataset provenance, per-k CLI + Python tables, verdict, parity, methodology, provenance, footer), renders arms in `ARM_ORDER` independent of JSON order, shows raw rep walls beside the recorded median and `peak_bytes` in GiB, marks `[cv_warning]`, and prints t1 under `Scaling evidence (excluded from the verdict)`.
- The five mandatory literals — `BENCH-V2-01`, `partially satisfied`, `Dev-host evidence only`, `scaling evidence`, `equality` — are validated in memory by the renderer and asserted verbatim by `TestReport`.
- `--stage render` builds the verdict document and the report in memory, validates both, and publishes through sibling temp files + `os.replace`; a failure (including an injected renderer failure) unlinks both temps and BOTH destinations, so neither exists on exit 2. On a measured NO both artifacts are kept and exit 1 is returned.
- `--stage slice-gate` strips `.fq.gz`/`.fastq.gz` before matching `.part_001`/`.part_006`, provisions the head-4M slice once from part_001, pins the reference sha256 before consuming it, records k=21 as `pinned-reference` and k=31 as `live-parity-only (no pinned k=31 slice reference)`.
- `scripts/bench/README.md` now documents the five Phase-10 stages, the 0/1/2 exit contract (disk floor keeps 3), and the dev-host-only baseline class; the false promise that Phase 10 produces a CI-class baseline is gone.

## Task Commits

1. **Task 1: Production py-t16 arm and session stages** — `e700f4b` (feat)
2. **Task 2: Mechanical Phase-10 renderer with atomic publish** — `64743c2` (feat)
3. **Task 3: Slice-gate record stage and README contract** — `8c25e42` (feat)

## Files Created/Modified

- `scripts/bench/phase10.py` — py-rep input validation, `finalize_python_arm`, session/cross-session parity, `cli`/`python` session stages, full renderer + `render_report_text`, atomic publish, `render` stage, slice-gate helpers + stage.
- `scripts/bench/tests/test_python_full_arm.py` (new) — worker argv, invalid worker outcomes, finalize/parity guards, and both stage-document schemas (28 tests).
- `scripts/bench/tests/test_phase10_verdict.py` — `TestReport` (19) and `TestSliceGateRecord` (8); the RoundsFixture worker payload gained the required `inputs` list.
- `scripts/bench/README.md` — Phase-10 stages section, exit contract, dev-host-only class, Layout entry.

## Decisions Made

- The Python arm's payload `inputs` must equal the spec's two-part list exactly (order included); the check lives in the controller, not the worker.
- `finalize_python_arm(name, reps, expected=None)` is the only strict py reduction and is used by `build_arms`; `threads` is taken from the validated `threads_resolved`, and `db_sha256` is null by construction.
- The cold-cache statement is always emitted (with the computed census); it is a methodology fact about this host, not a conditional on the recorded cache states.
- The report's only environment read is `bench.harness_source_commit()` (last commit touching `bench.py`), so re-renders are stable as the repo advances.
- `run_rounds` resolves its `measure_fn`/`purge_fn`/`sleep_fn` defaults at call time so the real stage entry points can be unit-driven with `p10.measure` patched; explicit injection still works unchanged.

## Deviations from Plan

### Environment

**1. [Worktree base] Fast-forwarded from the stale worktree base before any edit**
- **Found during:** start-up worktree branch check
- **Issue:** HEAD was `2fc58cb` (a strict ancestor of the expected base `377fd7b`) with a clean tree; `.planning/phases/10-benchmark-verdict/` did not exist in the worktree.
- **Fix:** `git merge --ff-only 377fd7b91648a94af20c7b52758474156626d36b` before any edit, as the dispatch instructions require. No files were changed by the fast-forward itself.
- **Files modified:** none by the merge.

**2. [Runtime environment] Symlinked untracked `target` from the main checkout**
- **Found during:** first discovery run (two `test_schema` failures, rc 127 on `target/release/rustkmer`)
- **Fix:** symlinked `target` (gitignored, untracked) from the main checkout so the two real self-check tests can run. Not committed. No `.venv313` symlink was needed for this plan.
- **Files modified:** none by the symlink.

### Plan deviations

**3. [Plan gap] The `python` stage takes an added `--preflight` argument**
- **Found during:** Task 1 implementation
- **Issue:** the plan's stage signature lists `--pre-gate G --cli-doc C`, but the pinned `memory_preflight` schema requires reading the projection from `10-python-preflight.json`.
- **Fix:** added a required `--preflight` flag for `--stage python`; the stage re-derives the decision through `memory_gate` and refuses a BLOCKED record before any measured run.
- **Files modified:** `scripts/bench/phase10.py`.

**4. [Testability] `run_rounds` seams default to call-time resolution**
- **Found during:** Task 1 stage-driver tests
- **Issue:** `measure_fn=measure` bound the primitive at definition time, so patching `phase10.measure` did not reach the stage entry points (they call `run_rounds` without injecting).
- **Fix:** defaults are now `None`, resolved to `measure` / `attempt_cache_purge` / `time.sleep` at call time. Explicit injection callers (all 10-01 tests) are unaffected.
- **Files modified:** `scripts/bench/phase10.py`.

**5. [Interpretation] Render-stage argument names follow the plan literally**
- **Found during:** Task 2
- **Issue:** the plan says "on exit 2 neither `--verdict-out` nor `--out` exists", while other stages use `--out` for the results document and `--report-out` for the report.
- **Fix:** for `--stage render`, `--out` is the rendered report and `--verdict-out` is the verdict document; `--docs` supplies the result documents. Documented in `scripts/bench/README.md`.
- **Files modified:** `scripts/bench/phase10.py`, `scripts/bench/README.md`.

**6. [Test method] Reversed-part rejection is asserted on `require_split_parts` directly**
- **Found during:** Task 3
- **Issue:** `bench.gather_inputs` sorts a directory, so a fixture containing the two parts in "reversed" creation order still resolves to `[part_001, part_006]`. A directory-level reversed test cannot fail.
- **Fix:** the order rule is pinned by calling `p10.require_split_parts([part_006, part_001])` directly and asserting `ValueError`; the directory-level tests cover one/three/wrong-part shapes.
- **Files modified:** `scripts/bench/tests/test_phase10_verdict.py`.

**7. [Ledger location] The plan commit ledger was recorded in `/tmp`**
- **Found during:** Task 1 commit
- **Issue:** the worktree sandbox refused writing into the shared `.git/worktrees/...` directory for the `gsd-plan-head-before-10-02` ledger.
- **Fix:** recorded the base in `/tmp/gsd-plan-head-before-10-02-a94e72d7` and measured `commits` with the same instrument (`git rev-list --count 377fd7b..HEAD`). The count and both head SHAs are recorded in `actuals`.
- **Files modified:** none in the repository.

---

**Total deviations:** 7 documented (2 environment/worktree, 5 plan/test method). No production source, fixture, baseline, or manifest was modified; no gate was edited to turn green.

## Issues Encountered

- The two real `test_schema` tests fail in a fresh worktree because `target/release/rustkmer` is untracked and absent; symlinking `target` from the main checkout resolves this. This is an environment condition, not a code regression.
- The known-flaky `test_verify_threads.TestNegativeControls.test_pre_engine_n_plus_one_stub_is_measured_red` did **not** fire in any of the discovery runs; the allowance was therefore not exercised.

## Verification

- `python3 -m unittest scripts.bench.tests.test_python_full_arm` — **28/28 OK**.
- `python3 -m unittest scripts.bench.tests.test_python_bench` — **85 OK (1 skip)**, unchanged.
- `python3 -m unittest scripts.bench.tests.test_phase10_verdict` — **60/60 OK** (33 from 10-01 + 19 `TestReport` + 8 `TestSliceGateRecord`).
- `python3 -m unittest scripts.bench.tests.test_render_report` — **22/22 OK** (v1.0 renderer byte-identical).
- `python3 -m unittest scripts.bench.tests.test_time_parser` — **14/14 OK**.
- `python3 -m unittest discover -s scripts/bench/tests -t .` — **510 tests, OK (1 skip)**; no failure was masked (full log inspected, zero `FAIL`/`ERROR` lines).
- README gate — `phase10.py` present, `dev-host` present, the old `CI runner artifacts only (Phase 10)` promise absent.
- Render smoke over four documents (k=21/31 × cli/python) — exit 0, all five literals present, sections in the mandated order.
- Scope guardrail — the plan diff touches exactly the four declared files; nothing under `scripts/bench/baselines/`, `src/`, `pyo3/src/`, `tests/fixtures/`, or any manifest/lockfile changed.

## Known Stubs

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 10-03 can execute `--stage slice-gate` against the real split directory (the stage is built and unit-tested with fakes), then `--stage cli --k 21|31`; the CLI stage records the research-upper-estimate preflight and refuses a blocked projection.
- Plan 10-04 can run `--stage preflight-python`, then `--stage python --k 21|31 --pre-gate ... --preflight ... --cli-doc ...`, then `--stage render --docs <four JSONs> --verdict-out ... --out ...`.
- No real-data measurement, slice provisioning, or evidence artifact was produced here (by design).

---

*Phase: 10-benchmark-verdict*
*Completed: 2026-11-13*

## Self-Check: PASSED

- FOUND: scripts/bench/phase10.py
- FOUND: scripts/bench/tests/test_python_full_arm.py
- FOUND: scripts/bench/tests/test_phase10_verdict.py
- FOUND: scripts/bench/README.md
- FOUND: e700f4b (task 1)
- FOUND: 64743c2 (task 2)
- FOUND: 8c25e42 (task 3)
