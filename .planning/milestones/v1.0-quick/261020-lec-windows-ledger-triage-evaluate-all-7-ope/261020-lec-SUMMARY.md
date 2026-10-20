---
phase: quick-261020-lec
plan: 01
subsystem: planning
tags: [windows-ledger, triage, docs-only]
status: complete
duration: 8 min
completed: 2026-10-20
key-files:
  modified:
    - .planning/WINDOWS.md
decisions:
  - "Rows 4/5/11 discharged fixed, rows 12/13/14 waived, row 15 stays open — every disposition anchored to live evidence re-observed on the execution tree"
  - "Documented deviation: the plan's expected census (4 open / 6 waived / 11 fixed / 18 total) is arithmetically impossible (sums to 21 against an 18-row ledger); the true post-triage census produced by the plan's own mandated dispositions is 1 open / 6 waived / 11 fixed / 18 total, with row 15 the only remaining open row"
  - "windows waive requires the reason as a second positional argument (the plan's one-arg form errored); supplying it made the tool write the reason into both surfaces directly, so no hand edits were needed for rows 12-14"
actuals:
  tokens: 5364   # chars/4 over the realized .planning/WINDOWS.md diff (21458 chars)
  tasks: 3
  commits: 1
---

# Quick Task 261020-lec: WINDOWS Ledger Triage Summary

**One-liner:** Triaged all 7 open Broken Windows rows against live evidence — discharged 4/5/11 as fixed and 12/13/14 as waived, left row 15 open with its missing test precisely recorded; ledger at the honest census 1 open / 6 waived / 11 fixed / 18 total.

## What Was Done

Every one of the 7 open rows was evaluated against live evidence observed on the execution tree (HEAD = 55d01a9, branch dev), not against the plan's claims. Baseline validated read: `ok: true` at 7 open / 3 waived / 8 fixed / 18 total. Six rows were then discharged one at a time via the tool-managed path (`windows fixed` / `windows waive`), each followed by a validated `windows status` read. Row 15 was left byte-untouched.

## Per-Row Triage Record

| Row | Disposition | Live evidence observed (2026-10-20) |
|-----|-------------|--------------------------------------|
| 4 | fixed | Commit `dbb13ef` exists (`git cat-file -e`); `grep -c '^python-source' pyo3/pyproject.toml` reads 0 active keys (only comment lines 76/78 deliberately mention it); 03-VERIFICATION.md:135 records `maturin develop, exit 0` and :194 the full suite 125 passed / 0 failed / 63 skipped; `pyo3-pytest:` job present at ci.yml:133. Same evidence family as row 16. |
| 5 | fixed | pyproject.toml:103 `addopts = ["-v"]` with the comment block at 99-102 pointing at the CI gate; zero `--cov` in the addopts block; the 80 percent gate lives at ci.yml:183 (`--cov-fail-under=80` in the pyo3-pytest job); commits `b6ea0ee` and `31071ab` exist. |
| 11 | fixed | pyo3/tests/test_database_merge.py exists (19 KB) with `def test_python_budget_model_tracks_the_core` present; 03-VERIFICATION.md:123/:193 record test_database_merge.py 12/12 first-ever run on the freshly built extension and :194 the full suite 125/0; CI runs the suite continuously. |
| 12 | waived | `grep -c db_refs src/database/format.rs` reads exactly 3: one historical comment at :1747 (inside `merge_databases_prefix_cache_to_path`, describing the OLD pre-fix code) plus two test locals at :2249-2250 inside the `#[cfg(test)] mod tests` module (opens :1931) serving `RKDatabase::validate_compatibility`. Zero `db_refs` code occurrences in the production function — the discriminating gate (no live `Vec<RKDatabase>`/`from_file_path` inside the fn) holds. The literal grep was the wrong instrument. |
| 13 | waived | `grep -c 'saturating_add(total)'` reads 0; the fold exists as the closure at :1115 (`|total, count| total.saturating_add(count)`), which cannot contain the grepped substring; the unit test `summing_two_near_max_headers_saturates_instead_of_panicking` still exists in the file. The gate form was unsatisfiable by construction. |
| 14 | waived | `resolve_merge_route` still has the `WR-02, DEFERRED BY DESIGN` doc comment (lines ~1123-1133), the `log::warn` at :1137 (`use_prefix_cache is set: merge_mode=...`), and the arm returning `Ok(MergeStrategy::PrefixCache)` at :1151 above the `over_budget` D-02 check at :1154; 03-10-SUMMARY.md:49/:233 records the deferral as deliberate; a sweep of `.planning/phases` and `.planning/quick` found no later plan that changed this behaviour. |
| 15 | STAYS OPEN | See stay-open record below. |

## Row 15 Stay-Open Record (the precisely-named missing test)

Live evidence: the only hit for `Failed to save merged database` in pyo3/src/database.rs is the explanatory comment at :1452 documenting that every failure now surfaces under the single `Merge operation failed:` prefix (the `map_err` to `PyRuntimeError` at :1457-1462). Grep across ALL of pyo3/tests for `Merge operation failed` reads 0 hits and for `Failed to save` reads 0 hits.

**What is missing:** no Python test drives a final merged-output write failure — for example `PyDatabase.merge` to a path inside a nonexistent directory — asserting a `RuntimeError` carrying the `Merge operation failed` prefix; and no pyo3 test pins that the old `Failed to save merged database` text is gone.

**Why the gap is narrow but real:** the green suite does exercise the error bridge through real merge failures — `test_streaming_route_is_proven_by_its_chunk_files` drives a streaming-route chunk-creation failure via a bogus TMPDIR (a temp-dir failure, not an output-write failure), and `test_over_budget_memory_mode_is_rejected` drives the D-02 rejection — but neither makes the FINAL merged-output write fail.

Writing the missing test is deliberately out of scope for this task (no test code was written); it is a candidate follow-up quick task. Row 15's table line and JSON entry are byte-identical to their pre-task state (verified by diff against HEAD).

## Deviations from Plan

### 1. [Evidence-driven] The plan's expected census is arithmetically impossible

- **Found during:** Task 2 (final validated read after the sixth discharge)
- **Issue:** The plan's must_haves truth #1, Task 2/3 verify gates, and objective all state the expected post-triage census as 4 open / 6 waived / 11 fixed / 18 total. That census sums to 21 and cannot describe an 18-row ledger. The baseline was 7 open / 3 waived / 8 fixed; the plan's own mandated dispositions (rows 4/5/11 open→fixed, rows 12/13/14 open→waived, row 15 untouched) mathematically produce **1 open / 6 waived / 11 fixed / 18 total** (1+6+11=18). The "4 remaining rows" narrative in the objective appears to be leftover arithmetic from an earlier draft (waive-only triage: 7-3=4 open).
- **Resolution:** No row disposition changed — all six dispositions matched the live evidence exactly. The tool-validated ledger reads `ok: true` at 1/6/11/18 with only row 15 open, and that is the truthful census this task records. Per the plan's own rule ("never a silent mismatch, never a forced flip"), the counters were left at the tool-computed truth rather than massaged toward the impossible expectation. The specific verify sub-check `grep -q '"open_count": 4'` is unsatisfiable by construction; every other sub-check in the Task 2 and Task 3 gates passes.
- **Consequence:** `/gsd-ship` remains blocked on exactly ONE open row (15), not four.

### 2. [Rule 3 - blocking fix] `windows waive` requires the reason as a second positional argument

- **Found during:** Task 2 (row 12 flip)
- **Issue:** The plan instructed `windows waive ID` (one argument). The tool refused: `Error: Expected 2 positional argument(s); got 1.` — the ledger header itself documents `windows waive <id> "<reason>"`.
- **Fix:** Re-ran each waive with the plan's verbatim reason text as the second argument. The tool then wrote the reason into BOTH surfaces directly (table cell and JSON string, character-identical) — the 2026-10-19 "reason stays empty" observation did not reproduce — so no post-flip hand edits were needed for rows 12/13/14. Rows 4/5/11 (`windows fixed`, which takes only the id) did leave the reason empty as anticipated; their reasons were added via scoped Edits anchored on each row's unique resolved_at stamp, per the plan.

### 3. [Truthfulness] Commit message census parenthetical corrected

- **Found during:** Task 3
- **Issue:** The plan's mandated commit message ends `(4/6/11/18)`, embedding the impossible census into permanent history.
- **Fix:** Committed with `(1/6/11/18)` — the actual validated census. A commit message asserting counters that contradict the very ledger file it commits would violate the task's core mandate (a truthful ledger, never a silent mismatch).

## Verify Gate Results

- Task 1 `EVIDENCE-SWEEP-OK`: PASSED (all anchors green on the pre-mutation tree).
- Task 2 `DISCHARGE-OK`: every sub-check PASSED except `grep -q '"open_count": 4'` (unsatisfiable — see Deviation 1). The gate as written cannot exit 0; the honest substitution `"open_count": 1` passes alongside all other sub-checks.
- Task 3 `FINAL-GATES-OK`: same single exception as Task 2; all other sub-checks green (census 6/11/18 counts, all six reasons appear exactly twice, row 15 open and byte-untouched, anchors re-run green post-edit, SUMMARY exists, HEAD commit contains only .planning/WINDOWS.md, STATE.md untouched).

## Commits

- Single task commit `b78b1d5` containing ONLY `.planning/WINDOWS.md` — SUMMARY intentionally left out for the orchestrator closeout, per the 261018-wrx / 261019-ese pattern. STATE.md not touched by the executor.

## Self-Check: PASSED

- Commit b78b1d5 exists on HEAD and contains exactly one file: .planning/WINDOWS.md (`git show --name-only` verified; no deletions).
- Validated `windows status` post-commit: ok true, 1 open / 6 waived / 11 fixed / 18 total; all six discharged reasons appear exactly twice; row 15 open and byte-identical to pre-task state in both surfaces.
- Evidence anchors re-run green on the post-edit tree; `git diff --quiet HEAD` clean (only pre-existing untracked files remain).
