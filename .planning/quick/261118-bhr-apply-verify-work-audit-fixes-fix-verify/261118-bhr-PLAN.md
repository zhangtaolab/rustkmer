---
phase: quick
plan: 261118-bhr
type: execute
wave: 1
depends_on: []
files_modified:
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
autonomous: true
must_haves:
  truths:
    - "The macOS thread observer never records a parsed zero-thread sample as an observation: a successful sample report with no Thread_ lines yields None (retry), so a child that exits after such a sample is exit 2 (never observed) instead of a spurious measured RED; a report with real thread lines still returns the true count."
    - "The verify_threads unit file is green with the two new regression tests (full file OK, 20 tests), and the pre-engine negative control still measures requested=4 observed=5 RED."
    - "Both SUMMARY coverage blocks classify cleanly: 11-05 D3 is present with reason human_judgment and a non-empty rationale; 06-03 D6 uses kind integration; classify-coverage reports errors: [] for both."
    - "The 372.50 GiB free-space figure is annotated in place as recorded-but-inconsistent in 11-PREPARE-RECORD.md §11 and in its 11-05 propagations, with no invented replacement value and the 136 GiB D-10 floor derivation untouched."
    - "11-UAT test-3 notes carry a dated correction naming gsd-tools generate-claude-md as the in-repo generator and recording the regenerated ~16.7 GB line; every result: row is unchanged."
    - "All four archived deferred items are resolved in place with evidence; audit-uat reports archived items 0 and windows status reports open_count 0 with entries 26 and 27 fixed."
  artifacts:
    - ".planning/research/profiling/verify_threads.py — zero-count guard in the macOS branch of _thread_count (returns None, retry)."
    - "scripts/bench/tests/test_verify_threads.py — TestThreadCountTransient with the empty-report retry test and the nonzero-report regression test."
    - ".planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/11-05-SUMMARY.md — D3 rationale field, no inline human_judgment comment, two free-space annotations."
    - ".planning/milestones/v2.0-phases/06-parallelism-correctness-hot-path/06-03-SUMMARY.md — D6 kind corrected to integration."
    - ".planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/11-PREPARE-RECORD.md — §11 in-place recorded-but-inconsistent annotation."
    - ".planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/11-UAT.md — dated test-3 notes correction."
    - "deferred-items.md in phases 06, 08, 11 — every entry carrying an explicit resolved status with evidence."
    - ".planning/WINDOWS.md — ledger entries 26 and 27 fixed (open_count 0)."
  key_links:
    - "_thread_count zero guard <-> observe() last_observed/exit-2 contract: a zero can never become the returned observation."
    - "D3 rationale field <-> coverage.cjs MISSING_RATIONALE validation (human_judgment true requires a non-empty rationale)."
    - "deferred-items status: resolved lines <-> audit-uat parseDeferredItemsWithStatus (resolved entries are filtered from the audit)."
    - "windows fixed 26/27 <-> WINDOWS.md ledger frontmatter counts and JSON mirror (CLI rewrite only)."
---

<objective>
Apply the verify-work audit fixes established on 2026-11-18: make the macOS
thread observer immune to a parsed zero-thread sample (plus a deterministic
unit test), correct two SUMMARY coverage schemas, annotate the
recorded-but-inconsistent free-space figure without inventing a replacement,
correct the stale CLAUDE.md-generator record, close the four archived deferred
items with evidence, and close WINDOWS ledger entries 26 and 27.

Purpose: remove the reproducible macOS sample-race flake at its root
(requested=4 observed=0), restore clean coverage classification for 11-05 and
06-03, keep the 11-PREPARE-RECORD evidence internally honest, and drive the
cross-phase archived debt and the broken-windows ledger to zero.
Output: 3 atomic commits (code fix + tests; record/coverage corrections; debt
closure + ledger), with every verification gate carrying its recorded HEAD
baseline.

Planning shape note: one small code fix plus record-only edits. No new runtime
layer, external service, or dependency is introduced; the behaviour is pinned
by a deterministic unit test, so a tracer slice would add no information (the
--no-tracer condition).

Commit contract (quick executor): work on the primary checkout and land EACH
task as ONE atomic commit staging exactly that task's file set by explicit path
(git add -- <paths>; never git add -A). The orchestrator commits the
PLAN/SUMMARY/STATE artifacts afterwards. Do NOT touch STATE.md, ROADMAP.md, or
BATCH.json. NEVER stage .claude/CLAUDE.md (gitignored per .gitignore:149) and
never use git add -f.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md
@.planning/research/profiling/verify_threads.py
@scripts/bench/tests/test_verify_threads.py
@.planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/11-05-SUMMARY.md
@.planning/milestones/v2.0-phases/06-parallelism-correctness-hot-path/06-03-SUMMARY.md
@.planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/11-PREPARE-RECORD.md
@.planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/11-UAT.md
@.planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/deferred-items.md
@.planning/milestones/v2.0-phases/06-parallelism-correctness-hot-path/deferred-items.md
@.planning/milestones/v2.0-phases/08-output-pipeline-rkdb-v2-parity/deferred-items.md

## Planning-time live observations (2026-11-18, HEAD c155170, clean tree)

- Test baseline: `python3 -m unittest scripts.bench.tests.test_verify_threads -v`
  → 18 tests OK in ~7.5 s. TestThreadCountTransient does not exist yet.
- Coverage baselines: 11-05 classify-coverage → errors
  [invalid_human_judgment on D3] (the inline # comment hides the boolean and
  rationale is required); 06-03 → errors [invalid_kind on D6
  (kind: benchmark)]. Dry-run on repo-local temp copies confirmed the planned
  edits produce errors: [] and D3 present with reason human_judgment.
- Debt baseline: `gsd_run audit-uat --pick summary.archived.items` → 4
  (11 flake, 11 docs drift, 06 fmt, 08 fmt); `--pick summary.total_files` → 3;
  `--pick summary.parse_gap_files` → 0; `--pick acknowledged_files` → 0.
- WINDOWS baseline: `gsd_run windows status --pick ledger.open_count` → 2
  (entries 26, 27); `--pick ledger.fixed_count` → 18.
- fmt evidence (for the debt closures): `cargo fmt --all --check` exits 0 and
  `cargo fmt --all --check --manifest-path pyo3/Cargo.toml` exits 0 at HEAD
  (both verified 2026-11-18); quick 261116-ks7 is commit ee742dc.
- WINDOWS #26 evidence: scripts/bench/tests/test_phase10_verdict.py resolves
  `.planning/milestones/v2.0-phases/10-benchmark-verdict` (lines 742-743 and
  762-763); retargeted by quick 261117-ala (commit 20caf42).
- `.claude/CLAUDE.md:17` ALREADY reads "~16.7 GB gzipped r1 across six
  single-member split parts" (regenerated); `.gitignore:149` ignores `.claude/`.
  This task records the regeneration, it does not edit the file.
- Tooling note: the audit finding snippets name
  `node .claude/gsd-core/bin/gsd-tools.cjs`, which does NOT exist in this
  checkout. Use `gsd_run` (on PATH; absolute ~/.claude/gsd-core/bin/gsd_run),
  which resolves the same gsd-tools CLI.
- `.planning/tmp/` was used only for the planning dry-runs above and is
  cleaned up; it is not part of this task's file set.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Retry zero-thread macOS sample reports in verify_threads (test first)</name>
  <files>.planning/research/profiling/verify_threads.py, scripts/bench/tests/test_verify_threads.py</files>
  <action>
    1. In scripts/bench/tests/test_verify_threads.py, add a class
       TestThreadCountTransient immediately after TestThreadCountParsing with
       exactly two tests (the file already imports subprocess and
       unittest.mock; load the helper with the existing load_helper_module):
       - test_zero_thread_report_is_retried: patch the loaded module's
         subprocess.run to return a completed process with returncode 0 whose
         stdout is a sample call-graph header only (no per-thread section
         lines); assert mod._thread_count(4242, "sample") is None.
       - test_nonzero_thread_report_is_returned: same mocked run with two
         distinct Thread_<tid> section lines; assert the return is 2.
       Run only the new class FIRST and observe
       test_zero_thread_report_is_retried fail against the current code (it
       returns 0) — that red is the regression proof; record it in the SUMMARY.
    2. In .planning/research/profiling/verify_threads.py, change the macOS
       branch of _thread_count so that, after the "written to file" redirect is
       resolved and txt holds the report, the unique-thread count is computed
       once; if that count is 0, return None (the poll loop retries) instead of
       returning 0. A live process always has at least one OS thread, so a
       successful sample with no thread lines is a transient sampling artifact
       (sample straddling the child's exit), never evidence. Return the parsed
       count unchanged when it is at least 1. Place the zero check AFTER the
       redirect handling so a redirected empty report is also retried. Do not
       alter the proc-task branch, observe(), the module exit contract, or any
       other function.
    3. Do not weaken the negative-control semantics: observe() still returns
       the last successfully observed count when the child exits below the
       expectation, but a zero can no longer become last_observed; a run whose
       only samples were empty reports ends as exit 2 (never observed), exactly
       as the module docstring's exit contract requires.
    4. Commit exactly these two files as one atomic commit with message
       "fix(quick-261118-bhr): retry zero-thread macOS sample reports in
       verify_threads".
  </action>
  <verify>
    <automated>python3 -m unittest scripts.bench.tests.test_verify_threads.TestThreadCountTransient 2>&1 | grep -qx 'OK' && python3 -m unittest scripts.bench.tests.test_verify_threads 2>&1 | grep -qx 'OK'</automated>
    Baselines recorded beside the gates: TestThreadCountTransient presence [HEAD=absent EXPECT==present]; full-file test count [HEAD=18 EXPECT==20].
  </verify>
  <done>TestThreadCountTransient exists with the two named tests; the zero-report test was observed failing pre-fix and passes now; the full file reports OK (20 tests = 18 pre-existing + 2 new), including TestNegativeControls' pre-engine stub measured RED (requested=4 observed=5) and the instant-exit exit-2 control.</done>
</task>

<task type="auto">
  <name>Task 2: Correct both coverage schemas, annotate the inconsistent free-space record, correct the CLAUDE.md-generator note</name>
  <files>.planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/11-05-SUMMARY.md, .planning/milestones/v2.0-phases/06-parallelism-correctness-hot-path/06-03-SUMMARY.md, .planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/11-PREPARE-RECORD.md, .planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/11-UAT.md</files>
  <action>
    1. In 11-05-SUMMARY.md, coverage entry D3: remove the trailing inline
       comment from the human_judgment: true line and add a sibling
       rationale: key at the same indentation as human_judgment, value: "The
       -s + budget approval is the checkpoint's human-equivalent judgment,
       recorded in 11-PREPARE-RECORD.md section 7 before any .jf build." Change
       nothing else in the coverage block (descriptions, verification refs,
       statuses, requirement stay byte-identical).
    2. In 06-03-SUMMARY.md, coverage entry D6: change the verification kind
       from benchmark to integration. Leave the ref (the release timing-gate
       cargo test) and everything else untouched.
    3. In 11-PREPARE-RECORD.md section 11, the "Free space after the full
       build" bullet: keep the recorded 372.50 GiB verbatim and append in
       place a bold dated note "Recorded-but-inconsistent (2026-11-18
       audit):" stating that the figure is unreconcilable with section 6
       (415 GiB before; 359.42 GiB after the 55.75 GiB .rkdb build) minus
       section 10's 30.98 GiB of .jf output (~328.4 GiB expected); the likely
       explanation is APFS purgeable-space reclamation between samples; the
       value is retained as recorded, is NOT an input to the D-10 floor
       derivation (which uses measured artifact bytes, not free space), and
       must not be used as a capacity baseline without re-measuring. Do NOT
       invent a replacement measurement and do NOT touch the 136 GiB floor
       derivation.
    4. In 11-05-SUMMARY.md, append the same one-line parenthetical pointer
       "(recorded-but-inconsistent free-space figure - see
       11-PREPARE-RECORD.md section 11; not a D-10 derivation input)"
       immediately after the 372.50 GiB phrase in the Next Phase Readiness
       bullet (line ~165) and after the "359-372 GiB free throughout" phrase
       in the key-decisions budget bullet (line ~46) - same figure, same
       annotation, so the file carries no silent stale mention.
    5. In 11-UAT.md, test 3 notes ONLY (never a result: row): append a dated
       correction paragraph at the end of the notes block: "Correction
       (2026-11-18, quick 261118-bhr): an in-repo generator does exist -
       gsd-tools generate-claude-md, invoked through the gsd_run launcher;
       the file was regenerated and line 17 now reads the corrected ~16.7 GB
       gzipped r1 across six single-member split parts line. The earlier
       no-in-repo-generator claim is superseded." Keep the original audit
       findings text above it intact.
    6. Do NOT edit or stage .claude/CLAUDE.md. Verify line 17 already carries
       the corrected ~16.7 GB / six single-member split parts text; if it does
       not, stop and report rather than hand-editing (finding: the
       regeneration already landed; this task records it).
    7. Commit exactly these four files as one atomic commit with message
       "docs(quick-261118-bhr): correct coverage schemas and annotate
       inconsistent free-space record".
  </action>
  <verify>
    <automated>gsd_run query uat.classify-coverage --summary .planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/11-05-SUMMARY.md --raw | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['errors']==[], d['errors']; assert any(e.get('id')=='D3' and e.get('reason')=='human_judgment' and e.get('rationale') for e in d['present']), d['present']"</automated>
    <automated>gsd_run query uat.classify-coverage --summary .planning/milestones/v2.0-phases/06-parallelism-correctness-hot-path/06-03-SUMMARY.md --raw | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['errors']==[], d['errors']; assert d['present']==[], d['present']"</automated>
    <automated>! grep -qE 'human_judgment: true[[:space:]]*#' .planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/11-05-SUMMARY.md && test "$(grep -c 'recorded-but-inconsistent' .planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/11-PREPARE-RECORD.md)" -ge 1 && test "$(grep -c 'recorded-but-inconsistent' .planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/11-05-SUMMARY.md)" -ge 2 && test "$(grep -c 'generate-claude-md' .planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/11-UAT.md)" -ge 1 && test "$(grep -c '16.7 GB' .claude/CLAUDE.md)" -ge 1</automated>
    Baselines recorded beside the gates: 11-05 errors [HEAD=1 EXPECT==0]; D3 present with reason human_judgment [HEAD=0 EXPECT>=1]; 06-03 errors [HEAD=1 EXPECT==0]; recorded-but-inconsistent in 11-PREPARE-RECORD [HEAD=0 EXPECT>=1]; in 11-05-SUMMARY [HEAD=0 EXPECT>=2]; generate-claude-md in 11-UAT [HEAD=0 EXPECT>=1]. The 16.7 GB grep is a read-only precondition already true at HEAD (never staged), not a change measurement.
  </verify>
  <done>classify-coverage returns errors: [] for both summaries; D3 appears in present with reason human_judgment and a non-empty rationale; 06-03 present is []; 11-PREPARE-RECORD section 11 and both 11-05 propagations carry the recorded-but-inconsistent annotation (2 matching lines in the summary); 11-UAT test 3 notes carry the dated generate-claude-md correction and every result: row is unchanged; the 136 GiB D-10 derivation is untouched.</done>
</task>

<task type="auto">
  <name>Task 3: Resolve the four archived deferred items with evidence and close WINDOWS 26/27 via the ledger CLI</name>
  <files>.planning/milestones/v2.0-phases/06-parallelism-correctness-hot-path/deferred-items.md, .planning/milestones/v2.0-phases/08-output-pipeline-rkdb-v2-parity/deferred-items.md, .planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/deferred-items.md, .planning/WINDOWS.md</files>
  <action>
    Run only after Task 1 is committed (the flake evidence) and Task 2 is
    committed (the docs-drift record).
    1. In .planning/milestones/v2.0-phases/06-parallelism-correctness-hot-path/deferred-items.md,
       section 06-02: set BOTH bullets' status lines to status: resolved (the
       audit parser takes the FIRST status field in the entry, so both must
       agree). On the prefix_cache_merge.rs:1382 bullet add: "Resolved
       2026-11-18: cargo fmt --all --check exits 0 at HEAD (verified
       2026-11-18); the drift was cleared by quick task 261116-ks7 (commit
       ee742dc)." Keep the existing pyo3 counter.rs narrative (Resolved in
       06-03) and set its trailing status to resolved.
    2. In .planning/milestones/v2.0-phases/08-output-pipeline-rkdb-v2-parity/deferred-items.md,
       section 08-02: change the trailing status: acknowledged to status:
       resolved and append: "Resolved 2026-11-18: cargo fmt --all --check
       exits 0 at HEAD (verified 2026-11-18); all seven named files are
       covered by the workspace check; the drift was cleared by quick task
       261116-ks7 (commit ee742dc)."
    3. In .planning/milestones/v2.1-phases/11-merge-characterization-harness-prep/deferred-items.md,
       flake entry: change its Status field from acknowledged to resolved and
       append: "Resolved in quick 261118-bhr (2026-11-18): _thread_count now
       returns None for a zero-thread macOS sample report (retry), with unit
       tests pinning the empty-report case; the negative controls and the full
       test_verify_threads suite are green."
    4. In the same file, docs-drift entry: change its Status field from
       acknowledged to resolved and append: "Resolved in quick 261118-bhr
       (2026-11-18): regenerated with gsd-tools generate-claude-md; line 17
       now reads the corrected ~16.7 GB / six single-member split parts text
       (verified)."
    5. Close the WINDOWS ledger entries with the CLI, never by hand-editing
       .planning/WINDOWS.md: run gsd_run windows fixed 26, then gsd_run
       windows fixed 27. The CLI sets status fixed and resolved_at and
       recomputes the frontmatter counts and JSON mirror; it records no reason
       text (fixed-row precedent carries an empty reason cell), so the
       evidence narrative belongs in the SUMMARY. Entry 26 evidence:
       scripts/bench/tests/test_phase10_verdict.py now resolves the archived
       Phase-10 dir under .planning/milestones/v2.0-phases (lines 742-743 and
       762-763), retargeted by quick 261117-ala (commit 20caf42). Entry 27
       evidence: the verification-only Rule 3 deviation recorded in
       11-05-SUMMARY.md.
    6. Do not edit STATE.md, ROADMAP.md, BATCH.json, or .claude/CLAUDE.md;
       the orchestrator owns the quick-task STATE.md bookkeeping.
    7. Commit exactly these four files (the three deferred-items files plus
       the CLI-rewritten .planning/WINDOWS.md) as one atomic commit with
       message "docs(quick-261118-bhr): resolve archived deferred items and
       close WINDOWS 26/27".
  </action>
  <verify>
    <automated>test "$(gsd_run audit-uat --pick summary.total_files)" = "3" && test "$(gsd_run audit-uat --pick summary.parse_gap_files)" = "0" && test "$(gsd_run audit-uat --pick summary.archived.items)" = "0" && test "$(gsd_run audit-uat --pick acknowledged_files)" = "0" && test "$(gsd_run windows status --pick ledger.open_count)" = "0" && test "$(gsd_run windows status --pick ledger.fixed_count)" = "20"</automated>
    Baselines recorded beside the gates: archived items [HEAD=4 EXPECT==0]; open_count [HEAD=2 EXPECT==0]; fixed_count [HEAD=18 EXPECT==20]. total_files == 3 and parse_gap_files == 0 are anti-false-pass guards (already true at HEAD, asserted by the command so a deleted/degraded entry cannot pass as zero debt).
  </verify>
  <done>audit-uat reports 3 files scanned, 0 parse gaps, 0 archived items, 0 acknowledged files; windows status reports open_count 0 and fixed_count 20 (entries 26 and 27 fixed with resolved_at set, added to the 18 previously fixed).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| (none new) | No new runtime surface. The only integrity-sensitive surface is the evidence record itself (SUMMARY coverage blocks, UAT notes, deferred-items, WINDOWS ledger), edited record-only. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-quick-bhr-01 | Tampering | Coverage blocks, UAT notes, deferred-items, WINDOWS ledger | medium | mitigate | Minimal in-place edits; classify-coverage and audit-uat gates re-derive the classification from the files; UAT result rows and the D-10 floor derivation are explicitly out of scope; the WINDOWS ledger is mutated only through its CLI, which recomputes counts. |
| T-quick-bhr-02 | Repudiation | 11-UAT test-3 notes | low | mitigate | The stale claim is superseded by an appended dated correction, not rewritten, so the audit history stays legible. |
| T-quick-bhr-SC | Tampering | npm/pip/cargo installs | high | mitigate | N/A for this task - no package-manager installs in scope; row kept reserved per quick-task convention. |
</threat_model>

<verification>
1. All three task gates pass with the HEAD baselines recorded in each <done>.
2. Commit hygiene: three atomic commits, each staging exactly its task's file
   set by explicit path (git add -- <paths>); `git status --porcelain` is
   clean afterwards; `.claude/CLAUDE.md` is never staged (git status
   --porcelain .claude/CLAUDE.md stays empty) and no git add -f is used; no
   diff touches .planning/milestones/**/VERIFICATION.md or SECURITY.md, and no
   result: row in any UAT file changes.
3. Full bench suite: `python3 -m unittest discover -s scripts/bench/tests -t .`
   reports OK (0 failures, 0 errors). The macOS sample-race flake this quick
   task fixes must not appear; any other red is a real regression - stop and
   report.
4. Diff review: `git diff HEAD~3 --stat` shows exactly the 10 files in the
   frontmatter files_modified list (the three commits land in order), with the
   small targeted line deltas described in each task.
</verification>

<success_criteria>
- verify_threads: a parsed zero-thread sample report is retried (None), never
  recorded; the two deterministic unit tests pin the regression; the full file
  suite is green (20 tests) and the pre-engine negative control still measures
  RED at requested=4 observed=5.
- 11-05 D3 and 06-03 D6 classify cleanly (errors: []), with D3 present by
  human_judgment plus rationale and D6 as kind integration.
- The 372.50 GiB figure is annotated as recorded-but-inconsistent in the
  evidence record and its 11-05 propagations; no replacement value is invented
  and the 136 GiB D-10 derivation is untouched.
- 11-UAT test-3 notes carry the dated generator correction; all result rows
  unchanged.
- The four archived deferred items are resolved with evidence; audit-uat shows
  archived items 0; WINDOWS entries 26 and 27 are fixed and open_count is 0.
- Three atomic commits, no staging of .claude/CLAUDE.md, STATE.md or ROADMAP.md
  untouched by the executor.
</success_criteria>

<output>
Create `.planning/quick/261118-bhr-apply-verify-work-audit-fixes-fix-verify/261118-bhr-SUMMARY.md` when done
</output>
