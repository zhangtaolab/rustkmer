---
phase: quick
plan: 261116-mjo
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/STATE.md
autonomous: true
requirements: []
estimate:
  tokens: 9000
  raw_tokens: 9000
  tasks: 2
  confidence: low
must_haves:
  truths:
    - "docs/getting-started/first-steps.md:56 keeps its working expression {counter.canonical} — the live PyCounter property exposed by the #[getter] fn canonical() at pyo3/src/counter.rs:549-551 — and the file ends the task byte-identical to HEAD (porcelain-clean, expression count unchanged at 1)."
    - "The flagged premise is proven inverted at execution time: PyCounter exposes canonical (bool) and NOT canonical_mode (hasattr False; direct access raises 'builtins.PyCounter' object has no attribute 'canonical_mode'), while PyCounterStats exposes canonical_mode via its own getter at pyo3/src/counter.rs:55-58."
    - "The entire first-steps.md Python sample (lines 50-69) runs end-to-end exit 0 against the doc's own sample.fa with exact counts: kmer_length 21, canonical True, total_kmers 106, unique_kmers 24."
    - "STATE.md records quick task 261116-mjo as completed with the false-positive resolution and a refreshed Last activity line."
    - "No repo source, doc, or test file is modified by the executor; the only working-tree outputs are .planning/ artifacts (SUMMARY + STATE.md), left uncommitted for the orchestrator."
  artifacts:
    - "261116-mjo-SUMMARY.md recording every probe command and output, the HEAD hash, the counter.rs citations (PyCounter getter 549-551, PyCounterStats getter 55-58, canonical_mode field 26), and the CI test citations that pin counter.canonical"
    - "Updated .planning/STATE.md with the 261116-mjo Quick Tasks Completed row (Commit cell is a literal em dash — no code commit exists) and the refreshed Last activity line"
  key_links:
    - "pyo3/src/counter.rs:549-551 #[getter] fn canonical <-> docs/getting-started/first-steps.md:56: the doc expression binds to this getter; renaming either side breaks CI-pinned tests (pyo3/tests/test_counter.py:51,58,65,951-952; pyo3/tests/test_public_api.py:48)."
    - "PyCounterStats #[getter] fn canonical_mode (pyo3/src/counter.rs:55-58) <-> the docs-update flag: the stats-object property is the likely origin of the inverted premise (get_stats() objects DO carry canonical_mode); the SUMMARY must cite both getters so the confusion cannot recur."
---

<!-- planner-discipline-allow: 261116-mjo -->

<objective>
Resolve the 2026-11-16 docs-update flag on docs/getting-started/first-steps.md:56 ("code sample calls counter.canonical but PyCounter exposes canonical_mode") as a FALSE POSITIVE. Planning-time verification at HEAD c55482d proves the premise inverted: PyCounter exposes `canonical` via `#[getter] fn canonical()` (pyo3/src/counter.rs:549-551), `counter.canonical_mode` raises AttributeError on PyCounter, and `canonical_mode` belongs to PyCounterStats (pyo3/src/counter.rs:55-58). Applying the requested rename would inject the exact AttributeError the flag fears into a correct, CI-pinned doc line.

Purpose: close the recurring flag with durable runtime and source evidence instead of corrupting a correct doc; leave a permanent two-getter map (PyCounter.canonical vs PyCounterStats.canonical_mode) so future docs passes cannot repeat the confusion.
Output: 261116-mjo-SUMMARY.md (probe evidence + resolution narrative), updated .planning/STATE.md quick-task row. NO repo source/doc/test edit and NO commit by the executor — the orchestrator owns the docs commit.

Source audit: GOAL ("verify the actual attribute name against pyo3/src/counter.rs before fixing; fix the doc line") resolves via verification: the verification is performed (Task 1) and its result voids the fix action — the doc line is already correct and end-to-end proven, so the only honest deliverable is recorded proof (Task 2). No RESEARCH.md applies; no deferred ideas are implemented by this quick item.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md

Grounding observed live at planning time, HEAD c55482d on dev, working tree clean:
- The flagged line is docs/getting-started/first-steps.md:56 — `print(f"   Canonical mode: {counter.canonical}")` — inside the sample whose line 54 constructs `PyCounter(21, canonical=True)`, i.e. `counter` is a PyCounter.
- Source truth in pyo3/src/counter.rs: `#[getter] fn canonical(&self) -> bool` at lines 549-551 exposes PyCounter.canonical; `#[getter] fn canonical_mode(&self)` at lines 55-58 exposes canonical_mode ONLY on PyCounterStats (the object returned by get_stats()); the `canonical_mode: bool` field at line 26 belongs to PyCounterStats and is not a PyCounter attribute.
- Live runtime probes on .venv313 (module resolved at .venv313/lib/python3.13/site-packages/pyrustkmer/__init__.py): `c.canonical is True`; `hasattr(c, "canonical_mode")` is False; `c.canonical_mode` raises 'builtins.PyCounter' object has no attribute 'canonical_mode'; `c.get_stats().canonical_mode is True`.
- CI pins the doc's expression: pyo3/tests/test_counter.py:51,58,65,951-952 and pyo3/tests/test_counter_simple.py:20,25,91-92 assert `counter.canonical`; pyo3/tests/test_public_api.py:48 asserts `PyCounter(21, canonical=True).canonical is True`.
- The full doc sample (lines 50-69) ran end-to-end exit 0 against the doc's own sample.fa (lines 37-44): kmer_length 21, canonical True, total_kmers 106, unique_kmers 24.
- Count-gate baselines at HEAD: grep -c 'counter\.canonical}' docs/getting-started/first-steps.md = 1; grep -c 'fn canonical(&self)' pyo3/src/counter.rs = 1; grep -c 'fn canonical_mode(&self)' pyo3/src/counter.rs = 1; grep -c '261116-mjo' .planning/STATE.md = 0; git status --porcelain on docs/getting-started/first-steps.md = empty.
- .venv313/bin/python imports pyrustkmer without env fiddling (verified live). Only if that import ever fails: rebuild via the documented maturin flow with .venv313 and CONDA_PREFIX unset (project memory), then re-run the battery — do NOT treat an import failure as license to edit anything.
- Execution/commit contract: NO task commits anything and NO task edits any repo source/doc/test file; the executor leaves 261116-mjo-SUMMARY.md and .planning/STATE.md UNCOMMITTED — the orchestrator owns the docs commit (lhq precedent). All commands assume cwd at the checkout root; every path is repo-root-relative.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Execution-time verification battery — prove the flagged line correct and the premise inverted</name>
  <files>none — read-only verification; no file is created or modified</files>
  <action>
From the checkout root run this battery and capture every output for the SUMMARY; require every check green before proceeding to Task 2.
(1) Attribute truth probe: run .venv313/bin/python -I with an inline script that imports pyrustkmer, constructs PyCounter(21, canonical=True), asserts canonical is True, asserts not hasattr(c, "canonical_mode"), asserts get_stats().canonical_mode is True, and prints the marker MJO-ATTR-TRUTH-OK. Planning-time proof: this exact probe printed the marker at HEAD c55482d.
(2) End-to-end doc-sample probe: capture ROOT=$(pwd) at the checkout root, create a mktemp -d scratch dir, write the doc's exact sample.fa content from lines 37-44 (two records: sample_sequence_1 with two ATCG-runs, sample_sequence_2 with two GCTA-runs), cd into the scratch dir, and run "$ROOT/.venv313/bin/python" -I with an inline script reproducing the doc's lines 54-69 behavior (construct PyCounter(21, canonical=True); read counter.kmer_length and counter.canonical; add_from_fasta("sample.fa"); read get_stats().total_kmers and get_stats().unique_kmers) with exact assertions kmer_length==21, canonical is True, total_kmers==106, unique_kmers==24, printing the marker MJO-SNIPPET-GREEN; then cd back to ROOT and remove the scratch dir. Planning-time proof: exit 0 with the marker.
(3) Static count gates, each compared against its recorded HEAD baseline: the flagged expression count in the doc is 1; the PyCounter getter count in pyo3/src/counter.rs is 1; the PyCounterStats getter count in pyo3/src/counter.rs is 1; git status --porcelain over docs/getting-started/first-steps.md, pyo3/src/counter.rs, and pyo3/tests is empty.
HARD PROHIBITION: do NOT edit docs/getting-started/first-steps.md, pyo3/src/counter.rs, or any test file. The flagged premise is inverted — renaming the doc expression to the stats-only attribute name would raise AttributeError at runtime and break CI-pinned tests (pyo3/tests/test_counter.py:51,58,65,951-952; pyo3/tests/test_public_api.py:48). If any battery check fails, HALT and record the failure in the SUMMARY instead of "fixing" anything.
  </action>
  <verify>
    <automated>test "$(grep -c 'counter\.canonical}' docs/getting-started/first-steps.md)" = "1" && test "$(grep -c 'fn canonical(&self)' pyo3/src/counter.rs)" = "1" && test "$(grep -c 'fn canonical_mode(&self)' pyo3/src/counter.rs)" = "1" && test -z "$(git status --porcelain docs/getting-started/first-steps.md pyo3/src/counter.rs pyo3/tests)" && .venv313/bin/python -I -c "
import pyrustkmer
c = pyrustkmer.PyCounter(21, canonical=True)
assert c.canonical is True and not hasattr(c, 'canonical_mode')
assert c.get_stats().canonical_mode is True
print('MJO-ATTR-TRUTH-OK')
" | grep -q MJO-ATTR-TRUTH-OK && ROOT=$(pwd) && SAMPLE_DIR=$(mktemp -d) && printf '%s\n' '>sample_sequence_1' 'ATCGATCGATCGATCGATCGATCGATCGATCGATCG' 'ATCGATCGATCGATCGATCGATCGATCGATCGATCG' '>sample_sequence_2' 'GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG' 'GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG' > "$SAMPLE_DIR/sample.fa" && cd "$SAMPLE_DIR" && "$ROOT/.venv313/bin/python" -I -c "
from pyrustkmer import PyCounter
counter = PyCounter(21, canonical=True)
assert counter.kmer_length == 21
assert counter.canonical is True
counter.add_from_fasta('sample.fa')
total_kmers = counter.get_stats().total_kmers
unique_kmers = counter.get_stats().unique_kmers
assert total_kmers == 106 and unique_kmers == 24
print('MJO-SNIPPET-GREEN')
" | grep -q MJO-SNIPPET-GREEN && cd "$ROOT" && rm -rf "$SAMPLE_DIR" && echo MJO-T1-VERIFIED</automated>
  </verify>
  <done>All static count gates equal their HEAD baselines (1 / 1 / 1, doc + source + tests porcelain-clean), the attribute-truth probe prints MJO-ATTR-TRUTH-OK, and the end-to-end doc-sample probe prints MJO-SNIPPET-GREEN — the flagged line is proven correct and untouched.</done>
  <reversibility rating="reversible">Pure read-only verification; no artifact is created or mutated, so there is nothing to revert.</reversibility>
</task>

<task type="auto">
  <name>Task 2: Record the false-positive resolution — SUMMARY and STATE.md row</name>
  <files>.planning/STATE.md</files>
  <action>
Run only after Task 1 is fully green (precondition below). From the checkout root:
1. Write 261116-mjo-SUMMARY.md in this task's quick directory (.planning/quick/261116-mjo-fix-docs-getting-started-first-steps-md-/) per the summary template, recording: the resolution verdict — flagged issue resolved as FALSE POSITIVE, premise inverted, no repo change required; each Task 1 probe command with its exact output (including both MJO markers) and the HEAD hash it ran at; the source-truth citations — PyCounter #[getter] fn canonical at pyo3/src/counter.rs:549-551, PyCounterStats #[getter] fn canonical_mode at pyo3/src/counter.rs:55-58 (the likely origin of the confusion, since get_stats() objects DO carry that name), and the canonical_mode bool field at line 26 belonging to PyCounterStats; the CI citations pinning counter.canonical (pyo3/tests/test_counter.py:51,58,65,951-952; pyo3/tests/test_counter_simple.py:20,25,91-92; pyo3/tests/test_public_api.py:48); and the exact end-to-end counts (total 106, unique 24). Add an explicit warning paragraph for future docs passes: the stats-only attribute name raises AttributeError on PyCounter — a doc line printing the flag off a PyCounter must use .canonical or .get_stats().canonical_mode.
2. In .planning/STATE.md make exactly two edits: (a) replace the Last activity: line under Current Position with: Last activity: 2026-11-16 - Completed quick task 261116-mjo: docs/getting-started/first-steps.md:56 flag resolved as false positive (PyCounter.canonical is correct; the stats-only name exists only on PyCounterStats) - no repo change; (b) append to the Quick Tasks Completed table the row: | 261116-mjo | Resolve first-steps.md:56 flag as false positive (PyCounter.canonical correct; no doc change) | 2026-11-16 | — | [261116-mjo-fix-docs-getting-started-first-steps-md-](./quick/261116-mjo-fix-docs-getting-started-first-steps-md-/) | — the Commit cell is a literal em dash because a verification-only resolution produces no code commit. Touch nothing else in STATE.md.
3. Leave 261116-mjo-SUMMARY.md, 261116-mjo-PLAN.md, and .planning/STATE.md UNCOMMITTED — the orchestrator owns the docs commit.
  </action>
  <verify>
    <automated>test -f .planning/quick/261116-mjo-fix-docs-getting-started-first-steps-md-/261116-mjo-SUMMARY.md && test "$(grep -ciE 'false[- ]positive' .planning/quick/261116-mjo-fix-docs-getting-started-first-steps-md-/261116-mjo-SUMMARY.md)" -ge "1" && test "$(grep -c '261116-mjo' .planning/STATE.md)" -ge "2" && test "$(grep -c 'counter\.canonical}' docs/getting-started/first-steps.md)" = "1" && test -z "$(git status --porcelain docs/getting-started/first-steps.md)" && echo MJO-T2-RECORDED</automated>
  </verify>
  <done>SUMMARY exists carrying the false-positive verdict with probe outputs, both counter.rs getter citations, and the CI test citations; STATE.md carries the quick-task row and refreshed Last activity; the doc file is still untouched (porcelain-clean, expression count 1); all .planning/ artifacts remain uncommitted for the orchestrator.</done>
  <precondition>Every Task 1 check is green: both probe markers printed, all three count gates equal their HEAD baselines of 1, and docs/getting-started/first-steps.md, pyo3/src/counter.rs, pyo3/tests are porcelain-clean. Halt without touching STATE.md or writing the SUMMARY otherwise.</precondition>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| docs-update recheck findings -> executor action | A flag produced by an automated docs pass arrives as a premise; an executor that trusts it verbatim would tamper a correct, CI-pinned doc line |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261116-mjo-01 | Tampering | docs/getting-started/first-steps.md:56 and pyo3/src/counter.rs:549-551 | medium | mitigate | Task 1 hard-prohibits the flagged rename and re-proves runtime truth (MJO-ATTR-TRUTH-OK) plus the end-to-end sample (MJO-SNIPPET-GREEN) before anything is recorded; positive count gates [HEAD=1 EXPECT=1] on the doc expression and both source getters plus porcelain-clean gates in both tasks' verify detect any unauthorized edit |
</threat_model>

<verification>
- Attribute-truth probe prints MJO-ATTR-TRUTH-OK: PyCounter.canonical is True, the stats-only name is absent on PyCounter (AttributeError), PyCounterStats.canonical_mode is present.
- End-to-end doc-sample probe prints MJO-SNIPPET-GREEN with exact counts total 106 / unique 24.
- Count gates at recorded baselines: doc expression 1 [HEAD=1], PyCounter getter 1 [HEAD=1], PyCounterStats getter 1 [HEAD=1].
- docs/getting-started/first-steps.md, pyo3/src/counter.rs, and pyo3/tests are porcelain-clean throughout; the executor makes no commit.
- 261116-mjo-SUMMARY.md and the .planning/STATE.md updates exist and stay uncommitted for the orchestrator.
</verification>

<success_criteria>
The 2026-11-16 flag is closed with recorded proof that the doc line was already correct and the premise inverted — the stats-only attribute name raises AttributeError on PyCounter while .canonical is the CI-pinned property. No repo file changed. The SUMMARY gives any future docs pass the two-getter map so the confusion cannot recur. STATE.md records the quick task; the orchestrator owns the single docs commit.
</success_criteria>

<output>
Create `.planning/quick/261116-mjo-fix-docs-getting-started-first-steps-md-/261116-mjo-SUMMARY.md` when done
</output>
