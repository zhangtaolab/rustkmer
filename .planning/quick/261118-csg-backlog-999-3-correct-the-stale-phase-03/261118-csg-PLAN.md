---
phase: quick
plan: 261118-csg
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md
  - .planning/ROADMAP.md
autonomous: true
must_haves:
  truths:
    - "The Phase 03 deferred-items entry for the streaming-merge chunk sweep records its sweep-coverage gap in past tense and carries a dated Resolved paragraph; it no longer makes the claim as a current, present-tense assertion."
    - "The Resolved paragraph names plan 03-11, commit 83a6ac2, CHUNK_FILE_PREFIXES and CHUNK_FILE_SUFFIX, the sweep behaviour (prefix+suffix selection, TTL mtime cutoff, symlink refusal via entry.file_type()), and the passing test tests/merge_cleanup_tests.rs::sweep_reclaims_stale_loose_chunk_files."
    - "The entry keeps its status: closed line, its first-half normal-path text (Verified, NOT a new defect ... cleans up correctly), and its How-to-reproduce line; the other three status: closed entries in the file are unchanged (count stays 4)."
    - "ROADMAP backlog Phase 999.3 reads (RESOLVED 2026-11-18), its Test 21 checkbox is ticked, and a Resolution paragraph cites the corrected deferred-items entry, commit 83a6ac2, and the passing test; Phase 999.1, Phase 999.2, and the italic 999.1-999.3 footnote are byte-identical to HEAD."
    - "cargo test --test merge_cleanup_tests sweep_reclaims_stale_loose_chunk_files passes on the current tree (HEAD: 1 passed, 0 failed, 8 filtered out)."
    - "The three historical artifacts 03-11-PLAN.md, 03-04-SUMMARY.md and 03-05-SUMMARY.md and the 03-UAT.md result rows are unmodified; STATE.md is untouched."
  artifacts:
    - ".planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md — same entry, past-tense gap record plus an appended **Resolved (2026-11-18):** paragraph; no other entry changed."
    - ".planning/ROADMAP.md — Phase 999.3 heading and checkbox resolved, one Resolution paragraph added; nothing else changed."
  key_links:
    - "deferred-items.md Resolved paragraph <-> src/database/temp_lifecycle.rs: the record must name the exact mechanism that supersedes it — CHUNK_FILE_PREFIXES (`rustkmer_sort_`, `rustkmer_merge_`) + CHUNK_FILE_SUFFIX (`.chunk`) selection, the DEFAULT_MERGE_TEMP_TTL cutoff, and the entry.file_type() symlink refusal in sweep_stale_merge_dirs."
    - "deferred-items.md Resolved paragraph <-> tests/merge_cleanup_tests.rs::sweep_reclaims_stale_loose_chunk_files: the resolution's evidence is the test that pins stale-reclaim, fresh-survives-TTL, and symlink-refused-with-target-intact."
    - "ROADMAP Phase 999.3 <-> deferred-items.md: the backlog closure is only true because the live tracking record was corrected; both name commit 83a6ac2 (plan 03-11, landed 2026-10-08)."
---

<objective>
Correct the stale Phase 03 deferred-items record and close ROADMAP backlog 999.3.

Purpose: the live tracking record still asserts, in the present tense, that
loose `*.chunk` files left by a SIGKILLed / `panic = "abort"`ed streaming merge
are outside the sweep. That is false: plan 03-11 (commit `83a6ac2`,
2026-10-08) added the loose-chunk branch to `sweep_stale_merge_dirs` with the
same TTL and symlink refusal as the directory branch, pinned by
`tests/merge_cleanup_tests.rs::sweep_reclaims_stale_loose_chunk_files`. The
record was written by an earlier plan in the same phase and never updated.
Output: 1 atomic commit touching exactly two files — the corrected
`deferred-items.md` entry and the resolved ROADMAP 999.3 entry.

Planning shape note: record-only correction plus a live test re-run. No new
runtime layer, API, or persisted format is involved; a tracer slice would add
no information (the --no-tracer condition). Historical artifacts
(`03-11-PLAN.md`, `03-04-SUMMARY.md`, `03-05-SUMMARY.md`, `03-UAT.md`) were
accurate when written and MUST NOT be rewritten.

History-preservation note: the entry's first half (normal-path RAII cleanup is
fine) stays verbatim and `status: closed` stays. Only the second half's
present-tense clauses become past tense — the gap was real when recorded — and
the appended Resolved paragraph supersedes it. This keeps the history legible
while removing the false current claim, which is why the negative gate can hold
file-wide.

Commit contract (quick executor): work on the primary checkout and land the
whole task as ONE atomic commit staging exactly the two files by explicit path
(`git add -- <paths>`; never `git add -A`). The orchestrator records the
STATE.md quick-task row and commits the PLAN/SUMMARY/STATE artifacts
afterwards. Do NOT touch STATE.md, BATCH.json, any other deferred-items file,
or any historical phase artifact. NEVER stage `.claude/CLAUDE.md` (gitignored
per .gitignore) and never use `git add -f`.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md
@.planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md
@.planning/ROADMAP.md
@src/database/temp_lifecycle.rs
@tests/merge_cleanup_tests.rs

## Planning-time live observations (2026-11-18, HEAD 62e3d04, clean tree)

- The stale entry is the block at `.planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md`
  lines 211-224, beginning `- Verified, NOT a new defect: the streaming merge`.
  It carries `status: closed` at line 215; its `**What:**` paragraph ends with
  the present-tense claim that a killed merge leaves chunks the sweep cannot
  reclaim.
- Mechanism (live, HEAD): `src/database/temp_lifecycle.rs:62` declares
  `pub const CHUNK_FILE_PREFIXES: [&str; 2] = ["rustkmer_sort_", "rustkmer_merge_"];`
  and `:68` declares `pub const CHUNK_FILE_SUFFIX: &str = ".chunk";`. The
  loose-chunk branch at lines 164-221 selects on suffix + any prefix, applies
  the same `DEFAULT_MERGE_TEMP_TTL` mtime cutoff as the directory branch, and
  refuses symlinks via `entry.file_type()`.
- Fix provenance (live): `83a6ac2 2026-10-08 feat(03-11): block-copy
  concatenation and orphan sweep for loose chunks` touches
  `src/database/prefix_cache_merge.rs` and `src/database/temp_lifecycle.rs`.
- Test provenance (live): `tests/merge_cleanup_tests.rs:520`
  `fn sweep_reclaims_stale_loose_chunk_files()`; run on 2026-11-18 gives
  `1 passed; 0 failed; 0 ignored; 8 filtered out` in ~0.1 s (prebuilt).
- Gate baselines measured at HEAD (all zero unless noted), deferred-items.md:
  `Resolved (2026-11-18)` = 0; `83a6ac2` = 0; `plan 03-11` = 0;
  `CHUNK_FILE_PREFIXES` = 0; `CHUNK_FILE_SUFFIX` = 0; `sweep_stale_merge_dirs`
  = 1; `DEFAULT_MERGE_TEMP_TTL` = 0; `entry.file_type()` = 0;
  `sweep_reclaims_stale_loose_chunk_files` = 0; `Verified, NOT a new defect` =
  1; `cleans up correctly` = 1; `status: closed` = 4;
  `How to reproduce:** the earlier plan 03-02 item stands` = 1; the two
  stale present-tense phrase literals = 1 each.
- Gate baselines measured at HEAD, `.planning/ROADMAP.md`:
  `### Phase 999.3: ... Test 21 (BACKLOG)` = 1; `Test 21 (RESOLVED 2026-11-18)`
  = 0; `- [x] Test 21:` = 0; `- [ ] Test 21:` = 1; `Resolution (2026-11-18,
  quick 261118-csg` = 0; `83a6ac2` = 0;
  `sweep_reclaims_stale_loose_chunk_files` = 0; `- [ ] Test 22:` = 1 (the
  999.2 entry); `- [x] Test 22:` = 1 (the resolved 999.1 entry); the italic
  `*999.1-999.3 are handled opportunistically...*` footnote = 1.
- The other three files containing `Test 21` are archived milestone roadmaps
  (`.planning/milestones/v1.0-ROADMAP.md`, `v2.0-ROADMAP.md`,
  `v2.1-ROADMAP.md`); they are out of scope and must not be edited.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Correct the deferred-entry second half, close ROADMAP 999.3, re-run the sweep test, commit</name>
  <files>.planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md, .planning/ROADMAP.md</files>
  <action>
    1. Edit `.planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md`.
       Locate the entry by the literal `Verified, NOT a new defect` (currently
       the block at lines 211-224). Keep these parts byte-identical: the entry's
       first two sentences (through `Drop` cleans up correctly.), the
       `status: closed` line, the `**What:**` paragraph's opening sentence about
       closing the normal-path half of plan 03-02's item, and the closing
       `**How to reproduce:** the earlier plan 03-02 item stands; this note
       only narrows its scope so nobody re-investigates the RAII path.` line.
       In the `**What:**` paragraph, convert only the second half from
       present tense to past tense, so the sweep-coverage gap is recorded as
       history rather than as a current claim. Replace the whole run that
       begins at `Normal cleanup is fine` and continues to the end of that
       paragraph (the period immediately before `**How to reproduce:**`) with:
       "Normal cleanup is fine. When this record was written, the only gap
       still open was the sweep-coverage one: a merge SIGKILLed or
       `panic = \"abort\"`ed (this project's release profile) left chunks in
       `temp_dir` that the then-current sweep did not reach, because it removed
       `rustkmer-merge-*` *directories* only. That gap is closed below."
       Then, after the `**How to reproduce:**` line and as the final paragraph
       of this entry, append:
       "**Resolved (2026-11-18):** plan 03-11 (commit `83a6ac2`, 2026-10-08)
       closed this gap — `sweep_stale_merge_dirs`
       (`src/database/temp_lifecycle.rs`) selects loose chunk files by
       `CHUNK_FILE_PREFIXES` (`rustkmer_sort_`, `rustkmer_merge_`) AND
       `CHUNK_FILE_SUFFIX` (`.chunk`), applies the same
       `DEFAULT_MERGE_TEMP_TTL` mtime cutoff as the directory branch, and
       refuses symlinks via `entry.file_type()`. Pinned by
       `tests/merge_cleanup_tests.rs::sweep_reclaims_stale_loose_chunk_files`
       (stale reclaimed, fresh survives the TTL, symlink refused with its
       target intact); re-run green 2026-11-18 (1 passed, 0 failed). Both
       halves of this entry are now closed; the entry's status line is
       unchanged."
       Wrap both inserted runs to the file's existing prose width (about 78
       columns) with the bullet's two-space continuation indent; do not leave
       them as one long line. Do not add a second `status:` line, do not
       renumber or touch any other entry, and do not edit the three historical
       artifacts named in the objective or the 03-UAT.md result rows.
    2. Edit `.planning/ROADMAP.md`, Phase 999.3 block only (currently lines
       96-102). Change the heading's trailing `(BACKLOG)` to
       `(RESOLVED 2026-11-18)`; change the single leading `- [ ] Test 21:`
       marker to `- [x] Test 21:` leaving the rest of that line byte-identical;
       then insert a blank line and one bold paragraph immediately after the
       Test 21 line and before the italic footnote:
       "**Resolution (2026-11-18, quick 261118-csg):** the Phase 03
       deferred-items entry no longer makes the stale claim; it records the
       gap in past tense and carries a dated Resolved paragraph. The
       sweep-coverage gap was closed by plan 03-11 (commit `83a6ac2`,
       2026-10-08): `sweep_stale_merge_dirs` selects loose chunk files via
       `CHUNK_FILE_PREFIXES` + `CHUNK_FILE_SUFFIX` under the same TTL and
       symlink refusal as the directory branch, pinned by
       `tests/merge_cleanup_tests.rs::sweep_reclaims_stale_loose_chunk_files`
       (re-run 2026-11-18: 1 passed, 0 failed)."
       Do not touch Phase 999.1, Phase 999.2, the italic footnote line, or the
       Goal / Source phase / Deferred at lines of Phase 999.3.
    3. Run the gates and the test in the Verify block. The test is cheap and
       already built (about 0.1 s); do not run the full suite.
    4. Confirm `git status --porcelain` lists exactly the two edited files plus
       nothing else (STATE.md must not appear). Commit exactly the two files as
       one atomic commit with message:
       "docs(quick-261118-csg): correct stale Phase 03 loose-chunk sweep record
       and close backlog 999.3".
  </action>
  <verify>
    <automated>test "$(grep -cF 'Resolved (2026-11-18)' .planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md)" -eq 1 # [HEAD=0 EXPECT==1]</automated>
    <automated>test "$(grep -cF '83a6ac2' .planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'plan 03-11' .planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'CHUNK_FILE_PREFIXES' .planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'CHUNK_FILE_SUFFIX' .planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'DEFAULT_MERGE_TEMP_TTL' .planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'entry.file_type()' .planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'sweep_reclaims_stale_loose_chunk_files' .planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md)" -eq 1 # [HEAD=0 EXPECT==1]</automated>
    <automated>test -z "$(grep -F 'will never reclaim' .planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md)" # [HEAD=1 EXPECT==0]</automated>
    <automated>test -z "$(grep -F 'never looks at loose' .planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md)" # [HEAD=1 EXPECT==0]</automated>
    <automated>test "$(grep -cF 'Verified, NOT a new defect' .planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md)" -ge 1 # [HEAD=1 EXPECT>=1 GUARD MUTATION: removing the entry's first-half sentence drops this to 0]</automated>
    <automated>test "$(grep -cF 'cleans up correctly' .planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md)" -ge 1 # [HEAD=1 EXPECT>=1 GUARD MUTATION: rewording the preserved normal-path sentence drops this to 0]</automated>
    <automated>test "$(grep -cF 'How to reproduce:** the earlier plan 03-02 item stands' .planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md)" -ge 1 # [HEAD=1 EXPECT>=1 GUARD MUTATION: dropping the entry's How-to-reproduce line drops this to 0]</automated>
    <automated>test "$(grep -cF 'status: closed' .planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md)" -ge 4 # [HEAD=4 EXPECT>=4 GUARD MUTATION: deleting or reclassifying any of the four closed entries drops the count below 4]</automated>
    <automated>test "$(grep -cF '### Phase 999.3: Follow-up — Phase 03 deferred UAT follow-up: Test 21 (RESOLVED 2026-11-18)' .planning/ROADMAP.md)" -eq 1 && test -z "$(grep -F 'Test 21 (BACKLOG)' .planning/ROADMAP.md)" # [HEAD=0 EXPECT==1]</automated>
    <automated>test "$(grep -cF -- '- [x] Test 21:' .planning/ROADMAP.md)" -eq 1 && test -z "$(grep -F -- '- [ ] Test 21:' .planning/ROADMAP.md)" # [HEAD=0 EXPECT==1]</automated>
    <automated>test "$(grep -cF 'Resolution (2026-11-18, quick 261118-csg' .planning/ROADMAP.md)" -eq 1 # [HEAD=0 EXPECT==1]</automated>
    <automated>test "$(grep -cF '83a6ac2' .planning/ROADMAP.md)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF 'sweep_reclaims_stale_loose_chunk_files' .planning/ROADMAP.md)" -ge 1 # [HEAD=0 EXPECT>=1]</automated>
    <automated>test "$(grep -cF -- '- [ ] Test 22:' .planning/ROADMAP.md)" -eq 1 # [HEAD=1 EXPECT==1 GUARD MUTATION: editing or removing the 999.2 follow-up line drops this to 0]</automated>
    <automated>test "$(grep -cF -- '- [x] Test 22:' .planning/ROADMAP.md)" -eq 1 # [HEAD=1 EXPECT==1 GUARD MUTATION: editing or removing the resolved 999.1 follow-up line drops this to 0]</automated>
    <automated>test "$(grep -cF '*999.1-999.3 are handled opportunistically' .planning/ROADMAP.md)" -eq 1 # [HEAD=1 EXPECT==1 GUARD MUTATION: editing the italic footnote line drops this to 0]</automated>
    <automated>cargo test --test merge_cleanup_tests sweep_reclaims_stale_loose_chunk_files # [HEAD=present EXPECT==present GUARD MUTATION: re-verification of a test already green at HEAD; the change is record-only]</automated>
    <automated>test -z "$(git status --porcelain -- .planning/milestones/v1.0-phases/03-memory-safety/03-11-PLAN.md .planning/milestones/v1.0-phases/03-memory-safety/03-04-SUMMARY.md .planning/milestones/v1.0-phases/03-memory-safety/03-05-SUMMARY.md .planning/milestones/v1.0-phases/03-memory-safety/03-UAT.md .planning/STATE.md)" # [HEAD=0 EXPECT==0 GUARD MUTATION: any modification to a historical artifact or STATE.md changes this from 0]</automated>
    <automated>FILES=$(git show --pretty=format: --name-only HEAD) && printf '%s\n' "$FILES" | grep -qxF '.planning/ROADMAP.md' && printf '%s\n' "$FILES" | grep -qxF '.planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md' && test -z "$(printf '%s\n' "$FILES" | grep -vF -e '.planning/ROADMAP.md' -e '.planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md')" # [HEAD=absent EXPECT==present]</automated>
    HEAD baselines are recorded beside each gate above. Prose summary in the same order: the deferred-file resolved marker, commit hash, plan id, the four mechanism literals and the test name are all 0 at HEAD; the two stale present-tense literals are 1 each at HEAD; the preserved first-half, cleanup and How-to-reproduce literals are 1 each at HEAD; status: closed is 4 at HEAD; the ROADMAP resolved heading, ticked checkbox and Resolution marker are 0 at HEAD while the BACKLOG heading and unticked checkbox are 1; the ROADMAP commit-hash and test-name mentions are 0; the two neighbor entries and the footnote are 1 each at HEAD; the named test is already green at HEAD; the historical artifacts and STATE.md are clean at HEAD; the commit-shape criterion does not exist before the commit. The commit-shape gate runs after the commit; all other gates run before it.
  </verify>
  <done>The deferred-items entry records the sweep-coverage gap in past tense and ends with a dated Resolved paragraph naming plan 03-11, commit 83a6ac2, CHUNK_FILE_PREFIXES/CHUNK_FILE_SUFFIX, the TTL cutoff, the symlink refusal, and the passing test, while keeping status: closed, its first-half normal-path text, and its How-to-reproduce line; the file contains no present-tense assertion that the sweep ignores loose chunk files; ROADMAP Phase 999.3 reads (RESOLVED 2026-11-18), its Test 21 checkbox is ticked, and a Resolution paragraph cites the record, 83a6ac2, and the test, with 999.1, 999.2 and the footnote untouched; the named test passes; exactly the two files are one atomic commit and STATE.md, the historical artifacts, and 03-UAT.md are unchanged.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| planning record -> future planner/executor | A live deferred-items entry and a ROADMAP backlog entry are authoritative evidence about what is still open; a false claim here causes duplicated or skipped work. |
| historical artifact -> corrected record | History is being superseded in place; a careless rewrite can erase why the gap was originally logged. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-quick-csg-01 | Tampering | .planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md | medium | mitigate | Rewrite only the second half from present to past tense and append the Resolved paragraph; gates assert the first-half literal, the cleanup literal, the How-to-reproduce line, and the status: closed count (4) are preserved, and the diff-shape gate limits the commit to exactly the two intended files. |
| T-quick-csg-02 | Repudiation | .planning/ROADMAP.md Phase 999.3 | low | mitigate | The checkbox is ticked and a dated Resolution paragraph cites the corrected record, commit 83a6ac2, and the named test; neighbor entries (999.1, 999.2) and the italic footnote are gated byte-identical at their HEAD counts. |
| T-quick-csg-03 | Repudiation | Resolved paragraph's factual claims | low | mitigate | Every claim is live-verified at HEAD before planning (constants at temp_lifecycle.rs:62/68, branch at :164-221, commit 83a6ac2 dated 2026-10-08, test at merge_cleanup_tests.rs:520) and the test is re-run as a gate. |
| T-quick-csg-SC | Tampering | npm/pip/cargo installs | high | mitigate | No package or dependency is added or installed; the only cargo command is an existing offline test binary run. |
</threat_model>

<verification>
1. All Verify-block gates pass with the HEAD baselines recorded beside them;
   the stale present-tense literals are absent from the live record file-wide.
2. The named test is re-run, not merely cited: `cargo test --test
   merge_cleanup_tests sweep_reclaims_stale_loose_chunk_files` reports
   `1 passed; 0 failed`.
3. Commit hygiene: exactly one atomic commit, staging exactly
   `.planning/milestones/v1.0-phases/03-memory-safety/deferred-items.md` and
   `.planning/ROADMAP.md` by explicit path; `git status --porcelain` is clean
   afterwards; STATE.md and BATCH.json are untouched; the historical artifacts
   `03-11-PLAN.md`, `03-04-SUMMARY.md`, `03-05-SUMMARY.md` and `03-UAT.md` are
   untouched; `.claude/CLAUDE.md` is never staged and no `git add -f` is used.
4. No archived roadmap (`.planning/milestones/v1.0-ROADMAP.md`, `v2.0-ROADMAP.md`,
   `v2.1-ROADMAP.md`) is modified.
5. The SUMMARY records that backlog 999.3 (Phase 03 deferred UAT follow-up,
   Test 21) is resolved so the orchestrator can add the STATE.md quick-task row
   and commit the artifacts.
</verification>

<success_criteria>
- The Phase 03 deferred-items entry no longer asserts as current fact that the
  sweep ignores loose `*.chunk` files; the gap is recorded in past tense and
  superseded by a dated Resolved paragraph naming plan 03-11 (commit 83a6ac2),
  CHUNK_FILE_PREFIXES/CHUNK_FILE_SUFFIX, the TTL cutoff, the symlink refusal,
  and the passing test.
- The entry keeps `status: closed`, its normal-path first half, and its
  How-to-reproduce line; no other entry in the file changes.
- ROADMAP backlog Phase 999.3 reads `(RESOLVED 2026-11-18)`, its Test 21
  checkbox is `[x]`, and its Resolution paragraph cites the corrected record,
  commit 83a6ac2, and the test; 999.1, 999.2, and the italic footnote are
  untouched.
- `cargo test --test merge_cleanup_tests sweep_reclaims_stale_loose_chunk_files`
  passes on the current tree.
- One atomic commit touches exactly the two record files.
</success_criteria>

<output>
Create `.planning/quick/261118-csg-backlog-999-3-correct-the-stale-phase-03/261118-csg-SUMMARY.md` when done. Record in it: the exact deferred-entry change (past-tense second half plus the Resolved paragraph), the ROADMAP 999.3 closure (heading, checkbox, Resolution paragraph), the live test result (1 passed, 0 failed), the commit hash and the two staged paths, and that backlog 999.3 / Phase 03 UAT Test 21 is resolved so the orchestrator can add the STATE.md quick-task row and commit the artifacts.
</output>
