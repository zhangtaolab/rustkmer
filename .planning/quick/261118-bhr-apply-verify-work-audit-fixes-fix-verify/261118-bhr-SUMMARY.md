---
phase: quick
plan: 261118-bhr
subsystem: measurement-infrastructure
tags: [verify-threads, flake-fix, coverage-schema, deferred-items, broken-windows, audit-hygiene]
requires:
  - 11-05 (PREPARE-RECORD evidence record + coverage D3)
  - 06-03 / 08-02 (deferred fmt drift, cleared by quick 261116-ks7 / ee742dc)
provides:
  - Zero-thread macOS sample reports retried (None) with two deterministic unit tests
  - Clean coverage classification for 11-05 D3 (human_judgment + rationale) and 06-03 D6 (integration)
  - Recorded-but-inconsistent free-space annotation (11-PREPARE-RECORD section 11 + two 11-05 propagations)
  - Dated generate-claude-md correction in 11-UAT test-3 notes
  - Four archived deferred items resolved with evidence; WINDOWS entries 26/27 fixed
affects: [audit-uat, /gsd-ship, WINDOWS ledger, next-milestone hygiene]
key-files:
  created: []
  modified:
    - .planning/research/profiling/verify_threads.py
    - scripts/bench/tests/test_verify_threads.py
    - .planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/11-05-SUMMARY.md
    - .planning/milestones/v2.0-phases/06-parallelism-correctness-hot-path/06-03-SUMMARY.md
    - .planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/11-PREPARE-RECORD.md
    - .planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/11-UAT.md
    - .planning/milestones/v2.0-phases/06-parallelism-correctness-hot-path/deferred-items.md
    - .planning/milestones/v2.0-phases/08-output-pipeline-rkdb-v2-parity/deferred-items.md
    - .planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/deferred-items.md
    - .planning/WINDOWS.md
decisions:
  - "A parsed zero-thread macOS sample report is a transient artifact: _thread_count returns None so the poll loop retries and a zero can never become last_observed"
  - "The 372.50 GiB free-space figure is annotated as recorded-but-inconsistent in place, never replaced with an invented measurement; the D-10 136 GiB derivation is untouched"
  - "Resolved deferred entries are filtered by audit-uat, so total_files legitimately drops to 0 when all debt is resolved (see deviation 2)"
metrics:
  duration: 6min
  completed: 2026-11-18
status: complete
actuals:
  tokens: 5167      # chars/4 over the realized diff (git diff c155170..HEAD = 20,669 chars)
  tasks: 3
  commits: 3        # MEASURED: git rev-list --count plan_head_before..HEAD
plan_head_before: c155170f915dbf9402199d7f40cbf517ba83ad71
plan_head_after: 2bcfc9bbfe50df1e2d0276c0bb10b5495c87f090
---

# Quick Task 261118-bhr: Apply Verify-Work Audit Fixes Summary

**The macOS thread observer now retries a parsed zero-thread sample report instead of recording it (regression pinned by two new unit tests), both coverage blocks classify cleanly, the inconsistent free-space figure is annotated in place, the stale CLAUDE.md-generator record is corrected, and the four archived deferred items plus WINDOWS entries 26/27 are closed — 3 atomic commits over exactly the 10 planned files.**

## Performance

- **Duration:** 6 min (2026-11-18T00:25:44Z → 00:32:00Z)
- **Tasks:** 3/3
- **Files modified:** 10 (2 code/test, 8 record/ledger)
- **Commits:** 3 (one per task, explicit-path staging)

## Task Commits

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Retry zero-thread macOS sample reports (test first) | `2a79420` (fix) | verify_threads.py, test_verify_threads.py |
| 2 | Correct coverage schemas, annotate free-space record, CLAUDE.md-generator note | `106768a` (docs) | 11-05-SUMMARY.md, 06-03-SUMMARY.md, 11-PREPARE-RECORD.md, 11-UAT.md |
| 3 | Resolve archived deferred items, close WINDOWS 26/27 | `2bcfc9b` (docs) | 06/08/11 deferred-items.md, WINDOWS.md |

## Verification Evidence

### Task 1 — verify_threads zero-report retry

- **RED proof observed before the fix:** `TestThreadCountTransient.test_zero_thread_report_is_retried` failed with `AssertionError: 0 is not None` (current code returned 0), confirming the regression the fix targets.
- **Post-fix:** `TestThreadCountTransient` → 2 tests OK; full file → **20 tests OK** (18 pre-existing + 2 new), including `TestNegativeControls::test_pre_engine_n_plus_one_stub_is_measured_red` (asserts `requested=4 observed=5`, `verdict=RED`, exit 1) and the instant-exit exit-2 control.
- Exact gate command returned rc=0: `...TestThreadCountTransient | grep -qx 'OK' && ...test_verify_threads | grep -qx 'OK'`.
- The fix sits after the "written to file" redirect handling, so a redirected empty report is retried too; `proc-task`, `observe()`, and the exit contract are untouched.

### Task 2 — coverage + record corrections

| Gate | Baseline (HEAD) | Measured after |
|------|-----------------|----------------|
| 11-05 classify-coverage errors | 1 (`invalid_human_judgment` on D3) | **0** |
| D3 present with reason `human_judgment` + rationale | 0 (reason `validation_failed`) | **>=1** (reason `human_judgment`, non-empty rationale) |
| 06-03 classify-coverage errors | 1 (`invalid_kind` on D6) | **0** |
| 06-03 `present` | 1 invalid | **[]** |
| `recorded-but-inconsistent` in 11-PREPARE-RECORD | 0 | **1** |
| `recorded-but-inconsistent` in 11-05-SUMMARY | 0 | **2** |
| `generate-claude-md` in 11-UAT | 0 | **1** |
| `16.7 GB` in `.claude/CLAUDE.md` (read-only precondition) | 1 | **1** (never staged) |

- All three Task-2 automated gates returned rc=0.
- 11-UAT `result:` rows unchanged (17, 49, 67 all `pass`); the original audit-findings text is intact and the correction is appended, not rewritten.
- The 136 GiB D-10 derivation was not touched (only referenced in the untouched UAT finding prose).

### Task 3 — deferred items + WINDOWS ledger

- Deferred items resolved: 06-02 (2 `status: resolved`, first-status-in-entry agreement), 08-02 (1 `status: resolved`), 11 flake + docs drift (`**Status:** resolved`, 3 total including the pre-existing resolved test_phase10 entry).
- WINDOWS 26/27 marked `fixed` with `resolved_at` set through the ledger CLI; the CLI rewrote frontmatter counts (open 2→0, fixed 18→20) and the JSON mirror — no hand edit.
- fmt evidence re-verified at HEAD: `cargo fmt --all --check` rc=0 and `cargo fmt --all --check --manifest-path pyo3/Cargo.toml` rc=0.
- **Gate as written:** rc=1. Measured values: `total_files=0`, `parse_gap_files=0`, `archived.items=0`, `acknowledged_files=0`, `open_count=0`, `fixed_count=20`. Every conjunct passes **except** `total_files == 3` — see Deviation 2 (unsatisfiable by construction).
- **Compensating anti-false-pass checks (same intent as the total_files guard):** all three deferred-items files are tracked (`git ls-files --error-unmatch` succeeds), carry 2/1/3 resolved status lines respectively, and no `status: acknowledged` marker remains.

### Plan-level verification

- Full bench suite: `python3 -m unittest discover -s scripts/bench/tests -t .` → **799 tests, OK (skipped=1)**, exit 0. No macOS sample-race red appeared.
- `git diff HEAD~3 --stat` → exactly the 10 planned files (83 insertions, 19 deletions).
- `git status --porcelain` → only `?? .planning/quick/` (orchestrator-owned docs artifacts, intentionally uncommitted by the executor).
- `.claude/CLAUDE.md` never staged (`git status --porcelain .claude/CLAUDE.md` empty); no `git add -f`.
- No `VERIFICATION.md` / `SECURITY.md` touched; no UAT `result:` row changed.

## Deviations from Plan

### Auto-fixed / adapted Issues

**1. [Rule 3 - Blocking] `gsd_run windows status --pick` cannot capture output on a pipe**

- **Found during:** Task 3 gate execution.
- **Issue:** `test "$(gsd_run windows status --pick ledger.open_count)" = "0"` fails even when the value is correct. `broken-windows.cjs`'s `emit()` writes via `process.stdout.write`, but `--pick`'s capture helper (`captureStdoutSyncWrites`, io.cjs:146) only patches `fs.writeSync(fd=1)`. When stdout is a pipe (which `$( )` always creates), Node's stdout write bypasses the patch, nothing is captured, and `--pick` errors `command output was not JSON` while the full JSON still reaches stdout. Redirecting stdout to a regular file works because that path goes through the patched `fs.writeSync`.
- **Fix:** the asserted values were read by redirecting each pick's stdout to a temp file and reading it back (`pick_win()` in the gate run); no asserted value changed. `audit-uat --pick` is unaffected (it emits through `output()`/`writeAllSync`).
- **Files modified:** none (invocation-only workaround; record-only).
- **Verification:** both pick values measured correct (`open_count=0`, `fixed_count=20`).

**2. [Rule 1 - Plan gate defect] Task 3's `total_files == 3` conjunct is unsatisfiable once the debt is resolved**

- **Found during:** Task 3 gate execution.
- **Issue:** `audit-uat` computes `summary.total_files = results.length`, and a `deferred-items.md` file is added to `results` only when it still has **unresolved** entries (`parseDeferredItems` filters `status: resolved`, uat.cjs:2208-2214). At HEAD the count was 3 precisely because 4 items were unresolved; resolving them necessarily yields 0. The plan's expectation of 3 (and its `<done>` wording "3 files scanned") assumed resolved entries still counted.
- **Fix:** ran the gate exactly as written and report the measured `total_files=0`; did not weaken any substantive assertion. The gate's stated anti-false-pass intent ("a deleted/degraded entry cannot pass as zero debt") is covered by the compensating checks above: files still tracked, resolution evidence present, zero remaining `acknowledged` markers, `parse_gap_files=0`.
- **Files modified:** none (plan-gate form only).
- **Verification:** all substantive claims hold: archived items 0, acknowledged files 0, parse gaps 0, WINDOWS open 0 / fixed 20.

**Note (not a plan deviation):** Gate 2c initially read 0 for `recorded-but-inconsistent` in 11-PREPARE-RECORD because the mandated bold note capitalizes the phrase; the note now also states "recorded-but-inconsistent" in lowercase prose, satisfying both the required wording and the case-sensitive grep.

## Known Stubs

None. The change adds a retry guard and record annotations only; no placeholder or unwired data path was introduced.

## Threat Flags

None. No new runtime surface (no endpoints, auth paths, or schema changes). The only code change is a defensive retry in the macOS observation branch; the evidence-record edits are gated by `classify-coverage` / `audit-uat` re-derivation, and the WINDOWS ledger was mutated only through its own CLI.

---
*Quick task: 261118-bhr*
*Completed: 2026-11-18*

## Self-Check: PASSED

- All 10 planned files modified at HEAD are present on disk (plus this SUMMARY).
- All three task commits (`2a79420`, `106768a`, `2bcfc9b`) are ancestors of HEAD.
- Measured commits from the persisted ledger (`gsd-plan-head-before-quick-261118-bhr`, base `c155170`): **3**, matching `plan_head_after=2bcfc9b`.
- Stub scan over the touched files: none.
