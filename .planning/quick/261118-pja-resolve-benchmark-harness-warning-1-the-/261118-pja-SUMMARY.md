---
phase: quick
plan: 261118-pja
subsystem: testing
tags: [benchmark-harness, phase10, slice-gate, controller, unittest, roadmap]
requires: []
provides:
  - "cli stage requires --pre-gate and validates it before any measured work"
  - "pre_gate {path, sha256} block recorded in the CLI session document"
  - "four CLI-stage enforcement tests in scripts/bench/tests/test_python_full_arm.py"
  - "ROADMAP v2.0 carry-forward WARNING-1 resolved; WARNING-2 resolved at commit 7e837f1"
affects: [benchmark-harness, phase-10-verdict-artifacts]
actuals:
  tokens: 4263
  tasks: 2
  commits: 2
plan_head_before: a121a61ec28f9d42d7ceef5d18c4d8e065fbb2e7
plan_head_after: 7dd2a8fce1a077b4f82666aa4b4984e174f6544a
tech-stack:
  added: []
  patterns:
    - "consume-then-pin: validate an external artifact, digest it before measurement, record path+sha256"
key-files:
  created: []
  modified:
    - scripts/bench/phase10.py
    - scripts/bench/tests/test_python_full_arm.py
    - scripts/bench/README.md
    - .planning/ROADMAP.md
key-decisions:
  - "Require --pre-gate rather than add a render-time ordering assertion: the two committed CLI documents have no pre_gate block, so the requirement subsumes ordering while keeping historical evidence readable"
  - "Reuse _load_slice_gate_doc unchanged so the cli and python stages share one definition of a valid gate"
  - "Digest the gate immediately after validation and before the disk floor/preflight/rounds, so a mid-run edit cannot repin the document"
patterns-established:
  - "CLI stage gate-before-measurement order: loader validation -> input-fingerprint equality -> slice-source sha equality -> digest -> disk floor/preflight/rounds"
requirements-completed: []
duration: 3min
completed: 2026-11-18
status: complete
---

# Quick 261118-pja: Resolve benchmark-harness WARNING-1 Summary

**The full-scale CLI stage now structurally consumes the slice-gate artifact: `--pre-gate` is required, validated by the python stage's own loader plus same-input and slice-source checks before any measured work, and pinned as `pre_gate` {path, sha256} in the CLI document.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-11-18T10:32:06Z
- **Completed:** 2026-11-18T10:35:17Z
- **Tasks:** 2
- **Files modified:** 4 (3 product + 1 roadmap record)

## Accomplishments

- `run_cli_session` refuses to run without `--pre-gate` (exit 2, stderr names the requirement, no artifact).
- A CLI session whose gate fails provenance, session-k, same-input, or slice-source validation exits 2 BEFORE `check_disk_floor`, `_cli_preflight`, `build_arm_specs`, and `run_rounds`; the input-fingerprint test proves `run_rounds` is never called.
- A valid CLI session records `pre_gate` with the gate path and the sha256 of the bytes validated before any measured work.
- Four new unittest cases pin the enforcement; the shared fixture gate now carries part_001's real sha256, and the 42 pre-existing tests stay green (module now 46).
- ROADMAP's v2.0 carry-forward block marks WARNING-1 RESOLVED with the mechanism and evidence, and WARNING-2 RESOLVED at `7e837f1`.

## Enforcement order in `run_cli_session`

1. Outside the `try`: `if not args.pre_gate: invalid("the cli stage requires --pre-gate <10-slice-gate.json>")` — SystemExit(2) is never swallowed.
2. Inside the `try`, immediately after `_resolve_two_parts`:
   a. `_load_slice_gate_doc(args.pre_gate, args.k)` — the python stage's validator, unchanged: provenance, kind, duplicate/per-k gates, positive counts, k=21 pinned counts/reference, k=31 same-slice source.
   b. `current_fingerprints = [fingerprint(path) for path in inputs]`; reject when `gate_doc.get("input_fingerprint")` differs, naming `--pre-gate`, "was measured on different input bytes", and both fingerprint values.
   c. Select the gate whose `k == args.k`; reject when its `slice_recipe["source_sha256"]` differs from `current_fingerprints[0]["sha256"]` (part_001), naming `--pre-gate`, the k value, both sha256 values, and the sentence "the gate must have been measured on the pinned slice source".
   d. `pre_gate_sha256 = file_sha256(args.pre_gate)` — computed before the disk floor, preflight, specs, or rounds.
3. Only then: `check_disk_floor` -> `_cli_preflight` -> `build_arm_specs` -> `run_rounds`.

Recorded block shape (inside `assemble_doc`'s `extra`, key order preflight, pre_gate, schedule):

```json
"pre_gate": {"path": "<--pre-gate value>", "sha256": "<digest of the validated bytes>"}
```

## New tests and results

All four passed individually and as part of the module:

- `TestCliStageDocument.test_missing_pre_gate_exits_2_with_no_artifact` — EXIT_INVALID, stderr contains "the cli stage requires --pre-gate", no artifact.
- `TestCliStageDocument.test_gate_for_different_inputs_exits_2_before_any_measurement` — mutated `input_fingerprint[0]["sha256"]` to zeros; EXIT_INVALID, stderr "different input bytes", no artifact, `run_rounds.call_count == 0` (explicit `new=` Mock observable after the ExitStack unwinds).
- `TestCliStageDocument.test_gate_from_a_different_slice_exits_2` — only the k=21 `slice_recipe.source_sha256` mutated (input fingerprints intact, proving this is a distinct check); EXIT_INVALID, stderr "pinned slice source", no artifact.
- `TestCliStageDocument.test_gate_missing_the_session_k_exits_2` — `cli_argv(k=31)` against the k=21-only fixture gate; EXIT_INVALID, stderr "no gate for the session's k=31", no artifact.

## Verification results

| Gate | Result |
|---|---|
| `python3 -m unittest scripts.bench.tests.test_python_full_arm` | 46 tests, OK (baseline 42) |
| Four new CLI-stage tests (explicit selection) | 4 tests, OK |
| `python3 -m unittest scripts.bench.tests.test_phase10_verdict scripts.bench.tests.test_render_report` | 127 tests, OK |
| `ruff check ... --ignore F541` | All checks passed |
| F541 count | 4 (unchanged pre-existing baseline) |
| `--stage render` over the four committed v2.0 documents | exit 0 (verdict k=21 YES, k=31 YES) |
| `--stage preflight-python` over the two committed CLI documents | exit 0 (both PROCEED) |

The two committed CLI documents predate the `pre_gate` block and remain readable; neither render nor preflight-python reads the gate path.

## Task Commits

Each task was committed atomically, staged by explicit path:

1. **Task 1: Require and validate `--pre-gate` for the cli stage, record it, and pin it with tests** — `f1805f3` (fix), staging exactly `scripts/bench/phase10.py`, `scripts/bench/tests/test_python_full_arm.py`, `scripts/bench/README.md`.
2. **Task 2: Close the ROADMAP v2.0 carry-forward WARNING-1 record** — `7dd2a8f` (docs), staging exactly `.planning/ROADMAP.md`.

**Plan metadata:** the orchestrator commits PLAN/SUMMARY/STATE afterwards (this executor does not commit docs artifacts).

## Files Created/Modified

- `scripts/bench/phase10.py` — `run_cli_session` requires/validates `--pre-gate`, records `pre_gate`, docstring updated; `--pre-gate` help now reads "cli and python stages".
- `scripts/bench/tests/test_python_full_arm.py` — `write_pre_gate` moved to `FullArmFixture` (k=21 gate source sha now part_001's real fingerprint), `_add_k31_gate(source_sha=None)` defaults to the k=21 gate's source sha, `cli_argv(k=21, include_pre_gate=True)`, recorded-block assertions, four new tests.
- `scripts/bench/README.md` — `cli` stage row states that it consumes the slice-gate artifact and pins path+sha256.
- `.planning/ROADMAP.md` — v2.0 carry-forward WARNING-1/WARNING-2 bullets resolved; heading "status updated 2026-11-18".

## Decisions Made

- Require `--pre-gate` instead of a render-time ordering assertion (historical documents have no `pre_gate`; a render-time read could depend on a `/tmp` gate path and make evidence unreadable).
- Reuse `_load_slice_gate_doc` unchanged so both stages share one gate definition.
- Digest the gate after validation but before the disk floor/preflight/rounds, so the recorded digest describes the validated bytes.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. All pre-commit verify gates passed on the first run after the message-wrapping adjustment that keeps the required slice-source sentence contiguous in one literal.

## Historical evidence protection

No milestone archive, STATE.md, `.claude/CLAUDE.md`, or source outside the authorized three files was edited. The render/preflight-python compatibility runs wrote only into fresh temp dirs removed in the same command, and `git status --porcelain` was clean after each commit.

## Next Phase Readiness

- WARNING-1 is closed structurally: a future CLI document cannot exist without the gate it consumed.
- WARNING-2's stale half is now marked resolved at `7e837f1` for the orchestrator's STATE.md quick-task row and docs commit.

---
*Quick task: 261118-pja*
*Completed: 2026-11-18*

## Self-Check: PASSED

- `scripts/bench/phase10.py`, `scripts/bench/tests/test_python_full_arm.py`, `scripts/bench/README.md`, `.planning/ROADMAP.md`, and this SUMMARY all exist.
- Commits `f1805f3` (Task 1) and `7dd2a8f` (Task 2) are ancestors of HEAD.
- No stub patterns in the realized product diff; all verify gates ran green.
