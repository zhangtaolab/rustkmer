---
phase: 10-benchmark-verdict
plan: 01
subsystem: testing
tags:
  - benchmark-harness
  - python-stdlib
  - jellyfish
  - pyo3
  - memory-projection
  - counterbalanced-protocol

requires:
  - phase: 09-python-parity
    provides: "the fresh-process pyrustkmer worker, module-sha provenance and worker-stats validation"
  - phase: 08-output-pipeline-rkdb-v2-parity
    provides: "output_stage.rotation_schedule and the validate-before-write controller shape"
provides:
  - "scripts/bench/phase10.py: four-arm controller over BOTH split parts, per-tool warmups, rotation rounds, nested medians, t16-only verdict with t1 excluded, mechanical report renderer, memory projection and preflight stage"
  - "parse_time_output: peak_footprint_bytes and peak_bytes = max(rss, footprint), raw peak_rss_bytes preserved"
  - "python_bench --inputs: repeatable worker inputs counted in argv order in one fresh process"
  - "Wave-0 tests: arm construction, rotation, verdict truth table, document write, memory model, preflight stage, worker argument gate"
affects:
  - 10-02
  - 10-03
  - 10-04
  - 11

actuals:
  tokens: 19847
  tasks: 3
  commits: 4
  plan_head_before: 130cf5d190abbdaf6e5aa9a2101a275d4965c1de
  plan_head_after: b613a0152ac164bc586d59038672003b7a5723c2

tech-stack:
  added: []
  patterns:
    - "Both-parts single arm: one BenchmarkConfig over the full two-part list; rustkmer one -i, jellyfish one gzcat pipeline, Python two --inputs flags"
    - "Acceptance verdict filters recorded threads == 16, treats equality as match-or-beat, reports t1 only as scaling"
    - "Honest peak memory: max(rss, phys_footprint) while peak_rss_bytes keeps its raw-byte schema meaning"
    - "Mechanical renderer: no measurement literal, no clock, only harness_source_commit()"
    - "Memory projection from a MEASURED distinct count with a derived PROCEED/BLOCKED decision"

key-files:
  created:
    - scripts/bench/phase10.py
    - scripts/bench/tests/test_phase10_verdict.py
  modified:
    - scripts/bench/bench.py
    - scripts/bench/python_bench.py
    - scripts/bench/tests/test_python_bench.py
    - scripts/bench/tests/test_time_parser.py

key-decisions:
  - "The Phase-10 controller is a standalone scripts/bench/phase10.py that imports bench, python_bench and output_stage; bench.py never imports python_bench (no cycle), and the v1.0 renderer stays byte-identical."
  - "A synthetic document is mode='synthetic' with session='synthetic'; the renderer pairs cli/python documents by k for full-mode runs and uses the single combined document for the synthetic spine."
  - "One interpreter_info call at arm-build time supplies the py arm's site_prefix to run_rounds; run_rounds takes no info argument."
  - "per-rep peak_bytes is normalized inside run_rounds (forward-compatible with the pre-extension parser) and preserve peak_footprint_bytes=None when unavailable."
  - "preflight-python requires exactly the two full-mode CLI documents, pins each consumed document's sha256, and writes its decision record on both PROCEED and BLOCKED paths."

requirements-completed: [BENCH-V2-02]

coverage:
  - id: D1
    description: "Four arms (rk-t16, rk-t1, jf-t16, py-t16) over BOTH synthetic split parts, counterbalanced rounds with per-rep cache_state/round/arm_order, schema-valid document and mechanical report"
    requirement: BENCH-V2-02
    verification:
      - kind: integration
        ref: "python3 scripts/bench/phase10.py --stage synthetic --out /tmp/rustkmer-phase10/tracer2/phase10_synthetic.json --report-out /tmp/rustkmer-phase10/tracer2/phase10_synthetic.md"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_phase10_verdict.py#TestArmConstruction"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_phase10_verdict.py#TestRunRounds"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_phase10_verdict.py#TestVerdictBlock"
        status: pass
    human_judgment: false
  - id: D2
    description: "parse_time_output records peak_footprint_bytes and peak_bytes = max(rss, footprint) with darwin fail-loud and unchanged raw RSS semantics"
    requirement: BENCH-V2-02
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_time_parser.py#TestPeakFootprint"
        status: pass
    human_judgment: false
  - id: D3
    description: "CLI capacity-cliff projection validated at three measured points, 86 B/distinct Python projection, inclusive 110 GiB gate, and a preflight stage that derives PROCEED/BLOCKED"
    requirement: BENCH-V2-02
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_phase10_verdict.py#TestMemoryModel"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_phase10_verdict.py#TestPreflightStage"
        status: pass
    human_judgment: false
  - id: D4
    description: "The worker gate accepts the exact Phase-10 argv --worker --inputs p1 --inputs p2 --stats-out S (inputs reach run_worker unflattened) and still rejects a worker with no input source"
    requirement: BENCH-V2-02
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_python_bench.py#TestWorkerArgumentGate"
        status: pass
    human_judgment: false

duration: 10min
completed: 2026-11-13
status: complete
---

# Phase 10 Plan 01: Four-arm Phase-10 spine, honest peak memory, memory projection

**One measured arm per tool over both split parts — rk-t16/rk-t1/jf-t16/py-t16 in rotated rounds — plus `max(rss, footprint)` accounting and a measured-distinct memory preflight, proven end-to-end on synthetic data.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-11-13T09:29:01Z
- **Completed:** 2026-11-13T09:39:10Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- `scripts/bench/phase10.py` exists as a standalone controller with the 0/1/2 exit contract, injectable `measure_fn`/`purge_fn`/`sleep_fn` seams, and no `bench.py` ↔ `python_bench.py` cycle.
- The synthetic tracer ran all four arms over TWO 200,000-read parts and exited 0: every arm's recorded `inputs` list and executed command carries both parts (rustkmer one `-i`, jellyfish one `gzcat` pipeline, Python two `--inputs` flags in one fresh process).
- `parse_time_output` now records `peak_footprint_bytes` and `peak_bytes = max(rss, footprint)` while `peak_rss_bytes` keeps its raw-byte contract; a darwin text without the footprint line raises.
- The CLI projection reproduces the three measured RSS points within 5%; the Python projection is exactly 86 B/distinct; the 110 GiB gate passes equality and blocks one byte over; `preflight_record` derives its decision internally.
- The `--inputs`-only worker argv is accepted and proven to reach `run_worker` unflattened; single `--input` behaviour is unchanged.

## Tracer observed results (second run, final parser state)

`python3 scripts/bench/phase10.py --stage synthetic ...` — exit 0, mode `synthetic`.

| arm | median wall (s) | median peak bytes | reps |
|-----|-----------------|-------------------|------|
| rk-t16 | 1.40 | 2,917,941,248 | 3 |
| rk-t1 | 3.85 | 2,901,213,184 | 3 |
| jf-t16 | 9.91 | 50,317,479,504 | 3 |
| py-t16 | 1.82 | 2,959,523,840 | 3 |

`PHASE10 VERDICT k=21 result=YES rustkmer=YES python=YES` (synthetic inputs; not evidence of full-scale performance). The jellyfish pipeline rep recorded footprint 50,317,266,536 B > RSS 50,297,290,752 B — the `max()` rule is load-bearing even for the pipeline shape. Jellyfish ran at the mandated `-s 10G`, costing ~50 GB RSS per rep even on synthetic input; the whole tracer still finished in about 2.5 minutes.

## Task Commits

1. **Task 1: End-to-end four-arm Phase-10 run on a synthetic two-part input** — `b3d93d5` (feat)
2. **Task 2: Extend the time parser with peak footprint and max(rss, footprint)** — `a0e993c` (test, RED) → `d6a5857` (feat, GREEN)
3. **Task 3: Memory projection model and budget gate** — `b613a01` (test; see deviation 3)

## Files Created/Modified

- `scripts/bench/phase10.py` — controller: arm specs, rotation rounds, nested medians, verdict, document assembly/write, mechanical renderer, memory projection, preflight-python stage.
- `scripts/bench/bench.py` — `MAC_FOOTPRINT` regex and the four-key `parse_time_output`; `measure`, `reduce_arm`, `validate_schema`, the v1.0 renderer and every protocol function untouched.
- `scripts/bench/python_bench.py` — repeatable `--inputs` worker; widened `main` gate; `run_worker` counts each path in argv order and records `inputs`.
- `scripts/bench/tests/test_phase10_verdict.py` — arm construction, rotation/rounds, surface truth table, verdict invalid paths, rep peak fallback, document write, memory model, preflight stage.
- `scripts/bench/tests/test_python_bench.py` — `TestWorkerArgumentGate` appended; existing tests byte-unchanged.
- `scripts/bench/tests/test_time_parser.py` — `TestPeakFootprint` appended; existing tests byte-unchanged.

## Decisions Made

- Kept the v1.0 `render_report` and its byte-identity tests untouched; the Phase-10 renderer is its own function, ordered by `ARM_ORDER`, deriving the verdict text from `verdict_block`.
- The synthetic document is `mode="synthetic"`, `session="synthetic"`; the renderer pairs `cli`/`python` documents by k for full runs and uses a single combined document for the synthetic spine.
- `assemble_doc` refuses `extra` keys that collide with pinned keys; the schedule block arrives via `extra`.
- `preflight-python` requires exactly two full-mode CLI documents, records each consumed document's sha256 (pin-before-consume), and writes its record on both PROCEED and BLOCKED paths.

## Deviations from Plan

### Environment

**1. [Worktree base] Fast-forwarded from the stale worktree base before any edit**
- **Found during:** start-up worktree branch check
- **Issue:** HEAD was `2fc58cb` (a strict ancestor of the expected base `130cf5d`) with a clean tree; `.planning/phases/10-benchmark-verdict/` did not exist yet in the worktree.
- **Fix:** `git merge --ff-only 130cf5d190abbdaf6e5aa9a2101a275d4965c1de` before any edit, as the dispatch instructions require.
- **Files modified:** none by the merge itself (fast-forward).

**2. [Runtime environment] Symlinked untracked `.venv313` and `target` from the main checkout**
- **Found during:** pre-execution environment probing (worktrees lack both untracked paths)
- **Fix:** symlinked for the tracer; `target` is gitignored and left in place, `.venv313` removed before returning. Nothing was committed.

### TDD sequencing / plan deviations

**3. [TDD anomaly] Task 3's implementation was written forward inside Task 1's controller**
- **Found during:** Task 3 RED
- **Issue:** `cli_peak_bytes`, `python_projection_bytes`, `memory_gate`, `preflight_record` and the preflight stage were authored while creating `phase10.py` in Task 1, so Task 3's target tests passed on first run (unexpected GREEN in RED; no RED evidence exists for this task).
- **Fix:** Investigated; the feature genuinely already existed. No production code changed in Task 3 — the task landed as the test commit `b613a01` only. The behavior is fully pinned by `TestMemoryModel` and `TestPreflightStage`.
- **Impact:** The plan's three tasks are all complete, but the per-task TDD commit split is not `test → feat` for Task 3. This is an execution-discipline miss (over-implementing during module creation), not a behavior gap.

**4. [Scope note] Jellyfish's pipeline footprint exceeded its RSS**
- **Found during:** the post-parser tracer rerun
- **Issue:** On this host the jellyfish pipeline's `peak memory footprint` (50,317,266,536 B) was ABOVE the pipeline RSS (50,297,290,752 B), whereas 10-RESEARCH Pitfall 5 described the footprint as the ~1 MB shell value.
- **Fix:** none needed — the mandated `max(rss, footprint)` rule records the larger value honestly and `peak_rss_bytes` preserves the raw RSS. Recorded here so later stages do not assume footprint < RSS for pipeline arms.

---

**Total deviations:** 4 documented (1 worktree base, 1 runtime environment, 1 TDD sequencing anomaly, 1 observed measurement nuance). No scope creep, no production behavior changed outside the plan's declared files.

## Issues Encountered

- The mandated `DEFAULT_HASH_SIZE = "10G"` makes each jellyfish rep reserve ~50 GB RSS even on synthetic input; the tracer still completed in ~2.5 minutes on a 128 GiB host. Full-scale stages must budget this per rep (plan 10-03).
- The known-flaky `test_verify_threads.TestNegativeControls.test_pre_engine_n_plus_one_stub_is_measured_red` did **not** fire in any run; the discovery gate was green each time, growing from the 415-test baseline to 455 tests (1 skip).

## Verification

- Tracer: exit 0, `mode=synthetic`, four arms, both parts per arm, 3 reps per arm, `peak_bytes >= peak_rss_bytes`, positive medians, t16 set exactly `{rk-t16, jf-t16, py-t16}`.
- `python3 -m unittest scripts.bench.tests.test_time_parser` — 14/14 OK.
- `python3 -m unittest scripts.bench.tests.test_phase10_verdict` — 33/33 OK.
- `python3 -m unittest scripts.bench.tests.test_python_bench` — 85 OK (1 skip).
- `python3 -m unittest discover -s scripts/bench/tests -t .` — **455 tests, OK (1 skip)**.
- Guardrail: the plan diff touches only the six declared files; nothing under `scripts/bench/baselines/`, `src/`, `pyo3/src/`, `tests/fixtures/`, or any manifest/lockfile changed.
- No `--size` flag is emitted; `bench.py` does not import `python_bench`; discovery was never masked through a tail pipe.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 10-02 can fill the `slice-gate`, `cli`, `python` and `render` stages, the full mandatory statement set, and `scripts/bench/README.md`, reusing the controller seams and `ARM_ORDER`.
- Plan 10-03 can budget jellyfish at ~50 GB RSS per rep at `-s 10G` and must leave rustkmer `--size` at its default.
- Plan 10-04 can call `--stage preflight-python --cli-docs <k21> <k31>`; a BLOCKED decision returns exit 2 with the decision record on disk.
- No full-scale measurement, slice provisioning, or phase evidence artifact was produced here (by design).

---
*Phase: 10-benchmark-verdict*
*Completed: 2026-11-13*

## Self-Check: PASSED

- FOUND: scripts/bench/phase10.py
- FOUND: scripts/bench/tests/test_phase10_verdict.py
- FOUND: .planning/phases/10-benchmark-verdict/10-01-SUMMARY.md
- FOUND: b3d93d5 (task 1)
- FOUND: a0e993c (task 2 RED)
- FOUND: d6a5857 (task 2 GREEN)
- FOUND: b613a01 (task 3)

