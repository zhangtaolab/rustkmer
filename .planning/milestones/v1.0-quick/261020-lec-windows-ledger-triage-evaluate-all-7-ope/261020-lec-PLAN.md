---
phase: quick-261020-lec
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/WINDOWS.md
autonomous: true
requirements: ["WINDOWS-LEDGER-TRIAGE"]
estimate:
  tokens: 14000
  raw_tokens: 14000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "node /Users/forrest/.claude/gsd-core/bin/gsd-tools.cjs windows status (cwd repo root) reports ok true with open_count 4, waived_count 6, fixed_count 11, total_count 18 — the tool's validated read proves frontmatter counters, markdown table, and fenced JSON all agree at the honest post-triage census (a documented evidence-driven deviation may change one row's disposition; then the counters must equal that documented census instead — never a silent mismatch, never a forced flip)"
    - "Ledger rows 4, 5, 11 read status fixed with non-empty resolved_at stamps; rows 12, 13, 14 read status waived; each of the six carries its evidence-citing reason appearing EXACTLY twice in .planning/WINDOWS.md — once in the table cell, once in the JSON string, character-identical, ASCII only, containing no pipe, backtick, double-quote, or backslash characters"
    - "Row 15 still reads open in BOTH the table and the JSON with its original description and empty reason — byte-untouched by this task; its stay-open rationale (the precisely-named missing save-failure test) is recorded in the task SUMMARY, and no test code is written in this task"
    - "Every planning-time evidence anchor re-runs green on the execution tree before and after the flips: commit dbb13ef exists; the active pyo3/pyproject.toml sets no python-source key and its addopts block carries no --cov flag; .github/workflows/ci.yml still defines the pyo3-pytest job; grep -c db_refs on src/database/format.rs reads 3 with all three occurrences a doc comment or cfg-test locals; grep -c of the literal saturating_add(total) reads 0 while the closure fold total.saturating_add(count) is present; the use_prefix_cache arm of resolve_merge_route still warns and documents the deferral"
    - "The single task commit contains ONLY .planning/WINDOWS.md; .planning/STATE.md is not modified by the executor (orchestrator closeout owns it); the SUMMARY file is created but left out of the task commit"
  artifacts:
    - ".planning/WINDOWS.md — six rows discharged (4/5/11 fixed, 12/13/14 waived) with dual-surface evidence-citing reasons; row 15 open and untouched; counters at the honest census (expected 4/6/11/18) with last_updated bumped (tool-managed)"
    - ".planning/quick/261020-lec-windows-ledger-triage-evaluate-all-7-ope/261020-lec-SUMMARY.md — per-row triage record including the row-15 stay-open rationale and any evidence-driven deviations from the expected dispositions"
  key_links:
    - "WINDOWS.md frontmatter counters <-> markdown table row census <-> fenced JSON entries: all three must agree; gsd-tools windows status runs the counter-vs-entries check and the table-vs-JSON drift guard on every read, so a validated read after the hand edits is the proof"
    - "reason text in each discharged table row <-> reason field in the same row's JSON entry: character-identical in both surfaces, achieved by using no pipe / backtick / double-quote / backslash characters in the reason text"
---

<objective>
Triage ALL 7 open rows of the Broken Windows ledger (4, 5, 11, 12, 13, 14, 15) against live evidence: discharge only what the current tree and history support (rows 4/5/11 fixed; rows 12/13/14 waived as accepted deviations), leave row 15 open with a precise record of the missing test, and commit only the ledger.

Purpose: `.planning/WINDOWS.md` stands at 7 open / 3 waived / 8 fixed / 18 total and `/gsd-ship` blocks while open_count > 0 (workflow.windows_enforce). The goal is a TRUTHFUL ledger, not zero: planning-time live verification (2026-10-20, minutes before this plan) confirmed rows 4/5/11 are dischargeable with the same evidence family that closed row 16 (dbb13ef dropped the maturin python-source blocker; the 2026-10-17 phase-03 re-verification rebuilt the extension and ran the pyo3 suite 125 passed / 0 failed including test_database_merge.py 12/12; quick-261019-d1y added the 3-OS pyo3-pytest CI job), rows 12/13 are accepted deviations where the plan's literal grep gate was the wrong instrument (live: db_refs reads 3 — one doc comment plus two cfg-test locals; saturating_add(total) reads 0 because the fold is a closure that cannot contain that substring), row 14 is a recorded design deferral still standing in code (the use_prefix_cache arm of resolve_merge_route returns above the D-02 rejection with a log::warn and a load-bearing-ordering doc comment), and row 15 still lacks a Python-level assertion for the folded-save failure path (the suite exercises the error bridge via real merge failures, but no test drives a final merged-output write failure). The honest end state is 4 open / 6 waived / 11 fixed — /gsd-ship stays blocked on the 4 remaining rows and that is correct.

Output: WINDOWS.md with six evidence-citing discharges in both the table and the JSON; row 15 untouched and open; one task commit containing only .planning/WINDOWS.md; a SUMMARY recording the full triage including the row-15 stay-open rationale.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/WINDOWS.md
@.planning/STATE.md
@.planning/phases/03-memory-safety/03-VERIFICATION.md
@.planning/phases/03-memory-safety/03-10-SUMMARY.md

Docs-only task — no Rust or Python source is modified. The 2026-10-17 re-verification evidence lives in 03-VERIFICATION.md (rows citing maturin develop exit 0, test_database_merge.py 12/12 first-ever run, full pyo3 pytest  passed / 0 failed / 63 skipped). Row 14's deferral decision is the WR-02 section of 03-10-SUMMARY.md — CAUTION: the round-4 03-REVIEW.md also has a WR-02, which is a DIFFERENT finding (u32 saturating in prefix_cache_merge.rs); do not conflate them.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Live evidence sweep over all 7 open rows (read-only)</name>
  <files>(none — read-only investigation; no file modifications)</files>
  <action>
Run every check below from the repo root on the CURRENT tree and record a per-row verdict (expected disposition + the evidence lines observed) for carry into Task 2 and the SUMMARY. This sweep is the sole authority for each disposition (mutable-scope rule: history notes guide, live observation decides).

Baseline: run node /Users/forrest/.claude/gsd-core/bin/gsd-tools.cjs windows status and confirm ok true with open 7 / waived 3 / fixed 8 / total 18 before any mutation. Do NOT use --pick inside dollar-parenthesis command substitution (known tool bug: broken-windows.cjs writes via process.stdout.write on a pipe and the substitution fails with command output was not JSON); redirect status output to a temp file or grep the plain output instead.

Per-row checks and decision rules:

Row 4 (unrun-verify, maturin python-source blocker) — expected FIXED. Verify: git cat-file -e on commit dbb13ef succeeds; grep for lines starting with python-source in pyo3/pyproject.toml returns 0 active keys (two comment lines near lines 76-78 deliberately mention it — comments do not count); the 2026-10-17 re-verification record exists in .planning/phases/03-memory-safety/03-VERIFICATION.md (maturin develop exit 0, pyo3 suite 125 passed / 0 failed); the pyo3-pytest CI job exists in .github/workflows/ci.yml. If all hold, row 4 is dischargeable fixed with the same evidence family as row 16 (read row 16's reason in WINDOWS.md as the format precedent).

Row 5 (deviation, cov flags in addopts) — expected FIXED. Verify: the addopts block in pyo3/pyproject.toml reads only -v (or at minimum contains no --cov flag) with the explanatory comment pointing at the CI gate; the 80 percent gate lives in the CI pytest step in .github/workflows/ci.yml; quick-261019-d1y commits b6ea0ee and 31071ab exist in history (git cat-file -e on each). If all hold, fixed.

Row 11 (unrun-verify, pyo3 test_database_merge.py never executed) — expected FIXED. Verify: pyo3/tests/test_database_merge.py exists and still contains def test_python_budget_model_tracks_the_core; the 03-VERIFICATION.md record cites test_database_merge.py 12/12 and the full suite 125/0 on the freshly built extension; CI now runs the suite continuously. If all hold, fixed.

Row 12 (deviation, db_refs grep gate) — expected WAIVED as accepted deviation. Verify live: grep -n db_refs src/database/format.rs — expected exactly 3 hits: one doc comment near line 1747 and two lines near 2249-2250 declaring and using a db_refs test local; confirm those two lines sit INSIDE the cfg-test module (the module opens with the cfg-test attribute around line 1931) and serve RKDatabase::validate_compatibility, not merge_databases_prefix_cache. If the occurrences are gone, flip to fixed-by-time citing the commit that removed them instead; if still present and still test-local/doc-comment, waive — the literal grep was the wrong instrument and the 03-09 discriminating gate (no from_file_path and no Vec of RKDatabase inside merge_databases_prefix_cache) was the right one.

Row 13 (deviation, saturating_add(total) grep gate) — expected WAIVED as accepted deviation. Verify live: grep -c of the literal saturating_add(total) on src/database/format.rs reads 0; the fold exists as a closure near line 1115 in the shape fold over total and count returning total.saturating_add(count), which cannot contain the grepped substring; the unit test summing_two_near_max_headers_saturates_instead_of_panicking still exists in the file (grep its name). If the code shape changed such that the literal now matches, re-derive (fixed citing the change if the gate became satisfiable, waive otherwise); if unchanged, waive — the gate form was wrong, not the code.

Row 14 (deviation, WR-02 deferral) — expected WAIVED as accepted by design. Verify live: in src/database/format.rs the use_prefix_cache arm of resolve_merge_route still returns above the D-02 over-budget rejection (grep for the warn text use_prefix_cache is set: merge_mode and the doc comment recording that the arm ordering IS finding WR-02 and that re-ordering would change outcomes for every existing prefix-cache caller); the 03-10-SUMMARY.md WR-02 section records the deferral as deliberate. Also grep .planning for any LATER plan or quick task that changed this behaviour (search for use_prefix_cache arm and merge_mode=memory across .planning/phases and .planning/quick summaries newer than 03-10): if a later change made the rejection happen, flip to fixed citing that commit; if the deferral still stands (expected), waive as accepted-by-design. Do NOT cite the 03-REVIEW round-4 WR-02 — it is a different finding (u32 overflow in prefix_cache_merge.rs).

Row 15 (unrun-verify, MERGE-04 folded-save residual) — expected STAYS OPEN. Verify live: grep the production source pyo3/src/database.rs for the old message text Failed to save merged database — the only hit must be the explanatory comment (near line 1452) documenting that every failure now surfaces under the single Merge operation failed prefix (the map_err to PyRuntimeError near line 1459); grep ALL of pyo3/tests for Merge operation failed and for Failed to save — expected 0 hits, meaning no Python test asserts the new prefix and none pins the disappearance of the old save-failure message; confirm which failure paths the green suite DOES exercise (test_streaming_route_is_proven_by_its_chunk_files drives a real core failure through the error bridge via a bogus TMPDIR; test_over_budget_memory_mode_is_rejected drives the D-02 rejection; neither makes the FINAL merged-output write fail). Decision rule: if no test drives a final merged-output write failure (for example merging to a path inside a nonexistent directory) asserting the RuntimeError, a real assertion gap remains — leave row 15 OPEN, change nothing in the ledger for it, and record in the SUMMARY the precisely-named missing test. Only if live evidence shows such a test exists (contradicting planning time) may row 15 flip to fixed citing it. Do NOT write any test code in this task.

Deviation protocol: if any check contradicts the expected disposition, STOP on that row, re-derive from the live evidence, and record the divergence in the SUMMARY; never force a flip the evidence does not support, and never leave a row open that the evidence discharges.
  </action>
  <verify>
    <automated>set -e; [ "$(grep -c '^python-source' pyo3/pyproject.toml)" = "0" ]; [ "$(grep -A2 '^addopts' pyo3/pyproject.toml | grep -c -- '--cov')" = "0" ]; [ "$(grep -c 'pyo3-pytest:' .github/workflows/ci.yml)" -ge 1 ]; [ "$(grep -c 'def test_python_budget_model_tracks_the_core' pyo3/tests/test_database_merge.py)" = "1" ]; [ "$(grep -c db_refs src/database/format.rs)" = "3" ]; [ "$(grep -c 'saturating_add(total)' src/database/format.rs)" = "0" ]; grep -q 'total.saturating_add(count)' src/database/format.rs; grep -q 'summing_two_near_max_headers_saturates_instead_of_panicking' src/database/format.rs; grep -q 'use_prefix_cache is set: merge_mode' src/database/format.rs; grep -q 'test_streaming_route_is_proven_by_its_chunk_files' pyo3/tests/test_database_merge.py; test "$(grep -rc 'Merge operation failed' pyo3/tests --include='*.py' | grep -v ':0' | wc -l | tr -d ' ')" = "0"; git cat-file -e 'dbb13ef^{commit}'; git cat-file -e 'b6ea0ee^{commit}'; git cat-file -e '31071ab^{commit}'; echo EVIDENCE-SWEEP-OK</automated>
  </verify>
  <done>All seven rows have a recorded verdict anchored to live evidence observed on the execution tree (not to this plan's claims); any row whose live evidence contradicts the expected disposition is flagged with the divergence noted; the baseline windows status read was ok true at 7/3/8/18; no ledger mutation has occurred yet.</done>
</task>

<task type="auto">
  <name>Task 2: Discharge rows 4/5/11 (fixed) and 12/13/14 (waived) via gsd-tools, with dual-surface reasons</name>
  <files>.planning/WINDOWS.md</files>
  <action>
Process ONE row at a time, in this order: 4, 5, 11, 12, 13, 14. For each: run the flip from the repo root with node /Users/forrest/.claude/gsd-core/bin/gsd-tools.cjs windows fixed ID (for 4, 5, 11) or windows waive ID (for 12, 13, 14). The tool re-reads the ledger with full validation, stamps resolved_at, recomputes the frontmatter counters, and re-renders the table and fenced JSON atomically. If it refuses with a table-vs-JSON disagreement, align the TABLE cell to the fenced JSON (the declared source of truth) with a scoped Edit and retry the flip.

Both subcommands have been observed (2026-10-19, quick-261019-ese) to leave the reason field EMPTY regardless of CLI arguments. After each flip, check the row's reason in the rendered file; if empty, add the reason text (below) via scoped Edits in BOTH surfaces — the table cell and the JSON string — character-identical. Anchor each Edit on text unique to that row (the recorded_at timestamp or the id plus file fields) so the match cannot land on another row's empty reason. Reason texts are ASCII-only and contain no pipe, backtick, double-quote, or backslash characters — copy them verbatim, single line, no trailing period changes. Do not run the flips for row 15 under any circumstances short of Task 1 evidence showing its gap closed.

Reason for row 4 (copy verbatim):
Closed 2026-10-20: discharged by evidence, not new code. The python-source key named in the description was dropped in dbb13ef and pyo3/pyproject.toml now documents it as deliberately not set; the 2026-10-17 phase-03 re-verification rebuilt pyrustkmer via maturin develop and ran the full suite green (125 passed, 0 failed, 63 skipped for missing fixture data); quick-261019-d1y added the 3-OS pyo3-pytest CI job. Same evidence family as row 16.

Reason for row 5 (copy verbatim):
Closed 2026-10-20: the cov flags named in the description were moved out of addopts by quick-261019-d1y (commits b6ea0ee and 31071ab); the addopts block in pyo3/pyproject.toml now reads only -v with a comment pointing at the CI gate; local pyo3 pytest runs are plain and the 80 percent coverage gate runs in the 3-OS pyo3-pytest CI job.

Reason for row 11 (copy verbatim):
Closed 2026-10-20: both execution blockers named in the description are gone (dbb13ef dropped python-source; quick-261019-d1y moved the cov gate to CI); the 2026-10-17 re-verification rebuilt the extension from source and executed test_database_merge.py 12/12 green for the first time, including test_python_budget_model_tracks_the_core and the BYTES_PER_KMER_ESTIMATE repair it pins; the pyo3-pytest CI job now runs the suite continuously.

Reason for row 12 (copy verbatim):
Accepted deviation, waived 2026-10-20: the literal grep was the wrong instrument, not a code defect. Live re-run on HEAD reads 3 occurrences of db_refs (one doc comment near src/database/format.rs:1747 and two test locals at 2249-2250 inside the cfg-test module serving validate_compatibility); zero production occurrences inside merge_databases_prefix_cache, which the 03-09 discriminating gate (no from_file_path and no Vec of RKDatabase inside that fn) already proved. Renaming test locals to satisfy a literal grep would make the gate green without making the property truer.

Reason for row 13 (copy verbatim):
Accepted deviation, waived 2026-10-20: the gate form was unsatisfiable by construction; the fold is written as a closure (src/database/format.rs:1115, fold over total and count returning total.saturating_add(count)), so the literal substring the plan grepped for cannot occur. Live re-run reads 0, exactly as reported at 03-09 time. The real evidence is the RED-observed unit test summing_two_near_max_headers_saturates_instead_of_panicking, which pinned the saturation behaviour and still stands.

Reason for row 14 (copy verbatim):
Accepted by design, waived 2026-10-20: the 03-10 deferral is still the standing decision. Live code confirms resolve_merge_route returns from the use_prefix_cache arm above the D-02 rejection, with a log::warn naming the dual meaning of merge_mode and a load-bearing-ordering doc comment recording that re-ordering would change outcomes for every existing prefix-cache caller; rejecting merge_mode=memory under --use-prefix-cache remains a behaviour-change decision no later plan has made (03-10-SUMMARY WR-02 section; note the 03-REVIEW WR-02 is a different u32-overflow finding).

If Task 1 recorded a divergence that changed any disposition (for example row 12 flipping to fixed-by-time because the occurrences vanished, or row 15 flipping to fixed because a save-failure test now exists), adjust that row's flip and reason to cite the live evidence actually observed, keeping the same ASCII and character restrictions and the same evidence-citing style. After each row is complete, run windows status (temp-file redirect, no --pick in command substitution) and confirm ok true before moving to the next row, so any drift refusal is attributable to a single edit. Row 15's table line and JSON entry must remain byte-identical to their pre-task state.
  </action>
  <verify>
    <automated>set -e; node /Users/forrest/.claude/gsd-core/bin/gsd-tools.cjs windows status > /tmp/win-status-triage.json; grep -q '"ok": true' /tmp/win-status-triage.json; grep -q '"open_count": 4' /tmp/win-status-triage.json; grep -q '"waived_count": 6' /tmp/win-status-triage.json; grep -q '"fixed_count": 11' /tmp/win-status-triage.json; grep -q '"total_count": 18' /tmp/win-status-triage.json; [ "$(grep -c 'Same evidence family as row 16' .planning/WINDOWS.md)" = "2" ]; [ "$(grep -c 'moved out of addopts by quick-261019-d1y' .planning/WINDOWS.md)" = "2" ]; [ "$(grep -c '12/12 green for the first time' .planning/WINDOWS.md)" = "2" ]; [ "$(grep -c 'Renaming test locals to satisfy a literal grep' .planning/WINDOWS.md)" = "2" ]; [ "$(grep -c 'unsatisfiable by construction' .planning/WINDOWS.md)" = "2" ]; [ "$(grep -c 'Accepted by design, waived 2026-10-20' .planning/WINDOWS.md)" = "2" ]; grep '^| 15 |' .planning/WINDOWS.md | grep -q '| open |'; grep -A6 '"id": 15,' .planning/WINDOWS.md | grep -q '"status": "open"'; ! grep '^| 15 |' .planning/WINDOWS.md | grep -q 'Closed 2026-10-20'; ! LC_ALL=C grep -E 'Closed 2026-10-20|Accepted deviation, waived 2026-10-20|Accepted by design, waived 2026-10-20' .planning/WINDOWS.md | LC_ALL=C grep -q '[^ -~]'; ! LC_ALL=C grep -E 'Closed 2026-10-20|Accepted deviation, waived 2026-10-20|Accepted by design, waived 2026-10-20' .planning/WINDOWS.md | LC_ALL=C grep -q -e '[|]' -e '[`]' -e '["]' -e '[\\]'; echo DISCHARGE-OK</automated>
  </verify>
  <done>Six rows discharged: 4/5/11 fixed and 12/13/14 waived, each with non-empty resolved_at and its reason appearing exactly twice (table + JSON, character-identical); the validated windows status read reports the honest census (expected 4 open / 6 waived / 11 fixed / 18 total, or the documented deviation census); row 15 is open, reason-empty, and byte-untouched; frontmatter counters were recomputed by the tool, not by hand.</done>
</task>

<task type="auto">
  <name>Task 3: Final read-only gates, SUMMARY with row-15 record, single-file commit</name>
  <files>.planning/WINDOWS.md</files>
  <action>
Re-run every read-only gate from the task contract before committing. First, the counter census: windows status (temp-file redirect) must be ok true with open_count, waived_count, fixed_count each equal to its actual row census in BOTH the markdown table and the fenced JSON (expected 4/6/11/18; if Task 1 recorded a documented deviation, the counters must equal that census instead — a mismatch between counters and rows is a failure regardless of direction). Second, the reason-twice check: each discharged row's reason appears exactly twice in the file and nowhere else — verify with the six distinctive substrings (Same evidence family as row 16 / moved out of addopts by quick-261019-d1y / 12/12 green for the first time / Renaming test locals to satisfy a literal grep / unsatisfiable by construction / Accepted by design, waived 2026-10-20), each grep -c reading 2. Third, open-row integrity: the row 15 table line still reads open with its original description and empty reason, its JSON entry still reads status open, and nothing in the row was altered. Fourth, evidence re-run: the Task 1 anchor bundle re-runs green on the post-edit tree (the ledger edit must not have touched any source file — confirm with git status --porcelain showing ONLY .planning/WINDOWS.md modified plus untracked planning artifacts).

Then write .planning/quick/261020-lec-windows-ledger-triage-evaluate-all-7-ope/261020-lec-SUMMARY.md recording: the per-row verdicts with the evidence observed at execution time; the six dispositions and their reason texts; and the row-15 stay-open record, which must state precisely what is missing — no Python test drives a final merged-output write failure (for example PyDatabase.merge to a path inside a nonexistent directory) asserting a RuntimeError carrying the Merge operation failed prefix, and no pyo3 test pins that the old Failed to save merged database text is gone; the suite does exercise the error bridge through real merge failures (bogus-TMPDIR streaming test) and the D-02 rejection, which is why the gap is narrow but real; writing the missing test is deliberately out of scope for this task and is a candidate follow-up quick task. Also record any evidence-driven deviations from the expected dispositions.

Finally, commit with git add .planning/WINDOWS.md ONLY (never git add -A; the SUMMARY stays out of the task commit for the orchestrator closeout, mirroring the 261018-wrx / 261019-ese pattern) and message: docs(quick-261020-lec): windows ledger triage — 4/5/11 fixed, 12/13/14 waived, 15 stays open (4/6/11/18). Do NOT modify .planning/STATE.md in any way — that bookkeeping belongs to the orchestrator's closeout.
  </action>
  <verify>
    <automated>set -e; node /Users/forrest/.claude/gsd-core/bin/gsd-tools.cjs windows status > /tmp/win-status-final.json; grep -q '"ok": true' /tmp/win-status-final.json; grep -q '"open_count": 4' /tmp/win-status-final.json; grep -q '"waived_count": 6' /tmp/win-status-final.json; grep -q '"fixed_count": 11' /tmp/win-status-final.json; [ "$(grep -c 'Same evidence family as row 16' .planning/WINDOWS.md)" = "2" ]; [ "$(grep -c 'moved out of addopts by quick-261019-d1y' .planning/WINDOWS.md)" = "2" ]; [ "$(grep -c '12/12 green for the first time' .planning/WINDOWS.md)" = "2" ]; [ "$(grep -c 'Renaming test locals to satisfy a literal grep' .planning/WINDOWS.md)" = "2" ]; [ "$(grep -c 'unsatisfiable by construction' .planning/WINDOWS.md)" = "2" ]; [ "$(grep -c 'Accepted by design, waived 2026-10-20' .planning/WINDOWS.md)" = "2" ]; grep '^| 15 |' .planning/WINDOWS.md | grep -q '| open |'; git cat-file -e 'dbb13ef^{commit}'; [ "$(grep -c '^python-source' pyo3/pyproject.toml)" = "0" ]; [ "$(grep -c db_refs src/database/format.rs)" = "3" ]; [ "$(grep -c 'saturating_add(total)' src/database/format.rs)" = "0" ]; test -f .planning/quick/261020-lec-windows-ledger-triage-evaluate-all-7-ope/261020-lec-SUMMARY.md; git show --name-only --format= HEAD > /tmp/head-commit-files.txt; [ "$(cat /tmp/head-commit-files.txt)" = ".planning/WINDOWS.md" ]; git diff --quiet HEAD -- .planning/STATE.md; git diff --quiet HEAD; echo FINAL-GATES-OK</automated>
  </verify>
  <done>All read-only gates green: validated status counters equal the row census in both surfaces; every discharged reason appears exactly twice; row 15 open and untouched; evidence anchors green post-edit; SUMMARY exists with the row-15 stay-open record; HEAD commit contains only .planning/WINDOWS.md; STATE.md untouched by the executor.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| (none) | Docs-only task: edits .planning/WINDOWS.md via the local gsd-tools CLI; no external input, no network, no code execution paths touched |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261020lec-01 | Tampering | .planning/WINDOWS.md ledger | low | mitigate | All mutations go through gsd-tools windows fixed/waive, which validates table-vs-JSON agreement and recomputes counters atomically; hand edits are limited to dual-surface reason strings gated by the appears-exactly-twice check |
| T-261020lec-02 | Information disclosure | ledger reason texts | low | accept | Reasons cite only public repo facts (commit hashes, test counts, dates); no secrets, env values, or paths outside the repo |
</threat_model>

<verification>
- node /Users/forrest/.claude/gsd-core/bin/gsd-tools.cjs windows status validates clean at the honest post-triage census (expected open 4 / waived 6 / fixed 11 / total 18, or the documented deviation census) with counters matching the row count in both the markdown table and the fenced JSON.
- Each of the six discharged reasons appears exactly twice in .planning/WINDOWS.md (table cell + JSON string), character-identical, ASCII-only, free of pipe/backtick/double-quote/backslash.
- Row 15 reads open in both surfaces with its original description and empty reason; its stay-open rationale names the precise missing test in the SUMMARY.
- The planning-time evidence anchors re-run green on the execution tree (dbb13ef exists; python-source absent from active config; addopts cov-free; db_refs count 3, all doc-comment/test-local; saturating_add(total) count 0 with the closure fold present; use_prefix_cache warn + deferral doc present; pyo3-pytest CI job present).
- HEAD commit contains only .planning/WINDOWS.md; STATE.md is untouched by the executor.
</verification>

<success_criteria>
- All 7 open rows were individually evaluated against live evidence observed at execution time — no disposition rests on this plan's claims alone.
- Rows 4/5/11 fixed, rows 12/13/14 waived, each with an evidence-citing reason in both ledger surfaces; row 15 open with the missing test precisely documented in the SUMMARY.
- The ledger is truthful, not massaged: /gsd-ship remains blocked on the remaining open rows and the record explains exactly why each is open.
- One commit, one file: docs(quick-261020-lec) touching only .planning/WINDOWS.md.
</success_criteria>

<output>
Create .planning/quick/261020-lec-windows-ledger-triage-evaluate-all-7-ope/261020-lec-SUMMARY.md when done (left for the orchestrator's closeout commit; not included in the task commit)
</output>
