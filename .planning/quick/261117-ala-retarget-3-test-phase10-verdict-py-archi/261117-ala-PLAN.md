---
phase: quick
plan: 261117-ala
type: execute
wave: 1
depends_on: []
files_modified:
  - scripts/bench/tests/test_phase10_verdict.py
  - scripts/bench/README.md
  - .planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-python-k21.json
  - .planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-python-k31.json
autonomous: true
must_haves:
  truths:
    - "The three previously red tests in scripts/bench/tests/test_phase10_verdict.py pass by resolving their artifacts under .planning/milestones/v2.0-phases/10-benchmark-verdict/: test_each_historical_pin_matches_its_committed_copy (k=21 and k=31 subTests) and test_committed_preflight_revalidates_for_both_k."
    - "python3 -m unittest discover -s scripts/bench/tests -t . reports 0 failures 0 errors (the known macOS sample-race flake in test_verify_threads, if it fires, clears on one rerun and is noted)."
    - "Zero test-logic change in test_phase10_verdict.py: the diff is exactly the two path-constant retargets (insert milestones/v2.0-phases into two existing Path chains)."
    - "The two archived python result JSONs keep every sha256/number byte-for-byte; only 5 path-string VALUES per file change their directory prefix."
    - "scripts/bench/README.md rehearsal Stage A/B commands are copy-pasteable and flag-for-flag identical to the four command_line strings recorded in .planning/phases/11-merge-characterization-harness-prep/11-REHEARSAL-RESULTS.json (--input present, one explicit k per invocation via loop, --disk-floor-gb 2 present)."
  artifacts:
    - "scripts/bench/tests/test_phase10_verdict.py — two retargeted Path constructions (TestCommittedPreflightArtifact and TestCommittedHistoricalCliEvidence.PHASE_DIR)."
    - ".planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-python-k21.json and -k31.json — 5 retargeted path values each."
    - "scripts/bench/README.md — rehearsal section (### dress rehearsal) carries the real recorded commands."
  key_links:
    - "test_phase10_verdict.py path constructions <-> archived dir .planning/milestones/v2.0-phases/10-benchmark-verdict/ (10-python-preflight.json, 10-results-python-k{21,31}.json, evidence/)."
    - "JSON fields memory_preflight.committed_copy / memory_preflight.source / cross_session.committed_copy / cross_session.cli_doc <-> repo-root-relative files that must exist under the archived dir for the sha re-check to pass."
    - "README Stage A/B commands <-> .planning/phases/11-merge-characterization-harness-prep/11-REHEARSAL-RESULTS.json runs[].command_line (flag-for-flag authority)."
---

<objective>
Fix the 3 red tests in scripts/bench/tests/test_phase10_verdict.py (2 ERROR +
1 FAIL) caused by commit 97c497c archiving .planning/phases/10-benchmark-verdict/
to .planning/milestones/v2.0-phases/10-benchmark-verdict/, and fix the WR-04
rehearsal Stage A/B command block in scripts/bench/README.md so it matches the
real recorded commands.

Purpose: restore the full bench suite to green (0 failures 0 errors) and make
the README rehearsal instructions actually runnable (they currently exit 1 for
missing --input, silently collapse the k list to k=31, and can trip the
136 GiB derived disk floor on smaller hosts).
Output: retargeted test constants + retargeted path values inside the two
archived JSONs + corrected README command block, landed as 2 atomic commits.

Planning shape note: test-path retarget + doc edit only — no runtime layers are
modified and the architecture is already proven, so a tracer slice would add no
information (horizontal task shape, the --no-tracer condition). No external
API integration, no ORM schema files, no assumption-delta signals — those
checkpoints are skipped.

Commit contract (quick executor): work on the primary checkout and land EACH
task as ONE atomic commit staging exactly that task's file set by explicit path
(git add -- <paths>; never git add -A). The orchestrator commits the
PLAN/SUMMARY/STATE artifacts afterwards. Do NOT touch STATE.md, ROADMAP.md,
or BATCH.json.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md
@scripts/bench/tests/test_phase10_verdict.py
@scripts/bench/README.md
@.planning/phases/11-merge-characterization-harness-prep/11-REHEARSAL-RESULTS.json

## Planning-time live observations (2026-11-17, HEAD 875e73f)

- Suite baseline for the target file: `Ran 99 tests ... FAILED (failures=1,
  errors=2)` in 0.44 s — exactly the 3 named reds, nothing else.
  - ERROR x2: `TestCommittedHistoricalCliEvidence.test_each_historical_pin_matches_its_committed_copy`
    (k=21 and k=31 subTests) — FileNotFoundError reading
    `.planning/phases/10-benchmark-verdict/10-results-python-k{21,31}.json`.
  - FAIL x1: `TestCommittedPreflightArtifact.test_committed_preflight_revalidates_for_both_k`
    — `missing committed artifact .planning/phases/10-benchmark-verdict/10-python-preflight.json`.
- The archived dir exists with all needed files:
  `.planning/milestones/v2.0-phases/10-benchmark-verdict/` contains
  `10-python-preflight.json`, `10-results-python-k21.json`,
  `10-results-python-k31.json`, `10-results-full-k{21,31}.json`, and
  `evidence/historical_cli_k{21,31}.json` (+ `evidence/pre_gate_k{21,31}.json`).
  The old path `.planning/phases/10-benchmark-verdict` does NOT exist.
- The two path constants in the test file are the ONLY stale references in it:
  lines 742-743 (preflight artifact path) and lines 762-763
  (`TestCommittedHistoricalCliEvidence.PHASE_DIR`). Both build
  `Path(__file__).resolve().parents[3] / ".planning" / "phases" / "10-benchmark-verdict"`.
- CRITICAL: retargeting the constants alone does NOT turn the historical-pin
  test green. The test resolves `preflight["committed_copy"]` and
  `preflight["source"]` against `p10.REPO_ROOT`, and those JSON fields still
  carry the old prefix — 5 occurrences per file (verified by grep, all
  double-quoted string values):
  - k21 file: 2x `.planning/phases/10-benchmark-verdict/evidence/historical_cli_k21.json`
    (`memory_preflight.committed_copy` + `cross_session.committed_copy`),
    2x `.planning/phases/10-benchmark-verdict/10-results-full-k21.json`
    (`memory_preflight.source` + `cross_session.cli_doc`),
    1x `.planning/phases/10-benchmark-verdict/evidence/pre_gate_k21.json`.
  - k31 file: same shape with k31 names.
- Safety of editing those JSON fields (verified):
  - Every sha256 the suite checks hashes file BYTES (`copy_path.read_bytes()`),
    never the path strings; `supersession_note` carries the CLI doc's content
    sha, also path-independent.
  - The renderer embeds none of these fields: zero hits for
    committed_copy/evidence paths in the committed
    `.planning/milestones/v2.0-phases/10-benchmark-verdict/10-BENCHMARK-REPORT.md`
    and no rendering reference in `scripts/bench/phase10.py` — re-render
    byte-identity is unaffected.
  - `_load_python_preflight` (scripts/bench/phase10.py:2341) is purely
    content-based (kind/records/budget/model/decision checks) — the preflight
    test needs only the constant retarget.
- Out of scope (verified non-contributing, leave untouched):
  - `.planning/milestones/v2.0-phases/10-benchmark-verdict/10-python-preflight.json`
    carries 2 stale path references, but no test resolves them (loader is
    content-only) — archived evidence stays unedited beyond what the tests
    resolve.
  - `scripts/bench/phase10.py` `PHASE_DIR` constant (line 135) and the usage
    text at lines 1565-1568 still name the old location, but no currently
    running test consumes them (only the 3 named reds fail); they serve the
    Phase-12 full-scale stage defaults — out of scope here.
- README WR-04 (lines 463-464, the two Shape cells of the
  `### dress rehearsal (gates before trust)` table): the Stage A cell omits
  `--input` (the run exits 1), the Stage B cell carries a brace-expanded k
  value list that argparse collapses to k=31 only, and both omit the explicit
  small `--disk-floor-gb 2` that slice/rehearsal runs must pass (D-12's
  per-rep re-check makes the 136 GiB derived default trip on smaller hosts —
  the prose at lines 452-454 already says exactly this; the commands below it
  contradict it). The authoritative flags are the four `command_line` strings
  in 11-REHEARSAL-RESULTS.json, e.g. Stage A k21:
  `python3 scripts/bench/bench.py --mode slice --input /Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split --slice-reads 50000 --k 21 --reps 2 --self-check --disk-floor-gb 2 --out /private/tmp/rustkmer-phase11/rehearsal/A-k21/results.json`
  (Stage B differs only in `--slice-reads 200000 --reps 3` and the `B-k21`
  out path; k31 mirrors both).
</context>

<tasks>

<task type="auto">
  <name>Task 1: Retarget the 3 red tests to the archived Phase-10 directory</name>
  <files>scripts/bench/tests/test_phase10_verdict.py, .planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-python-k21.json, .planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-python-k31.json</files>
  <action>
    1. In scripts/bench/tests/test_phase10_verdict.py, retarget EXACTLY two
       path constructions — insert ` / "milestones" / "v2.0-phases"` after
       `".planning"` so each chain reads `.planning / milestones / v2.0-phases
       / 10-benchmark-verdict`:
       - `TestCommittedPreflightArtifact.test_committed_preflight_revalidates_for_both_k`
         (planning-time lines 742-743): the chain must resolve to
         `.planning/milestones/v2.0-phases/10-benchmark-verdict/10-python-preflight.json`.
       - `TestCommittedHistoricalCliEvidence.PHASE_DIR` (planning-time lines
         762-763): must resolve to
         `.planning/milestones/v2.0-phases/10-benchmark-verdict`.
       Do NOT touch any other line of the test file — no test logic, docstring,
       or assertion changes.
    2. In each of the two archived JSONs, replace the directory prefix of the
       5 path-string VALUES from `.planning/phases/10-benchmark-verdict/` to
       `.planning/milestones/v2.0-phases/10-benchmark-verdict/` (grep confirms
       exactly 5 occurrences per file, all double-quoted values; edit as plain
       string substitution preserving key order, indentation, and every other
       byte — do NOT re-serialize the JSON):
       - `memory_preflight.committed_copy` and `cross_session.committed_copy`
         (both -> the evidence/historical_cli_k{k}.json path under the new
         prefix),
       - `memory_preflight.source` and `cross_session.cli_doc` (both -> the
         10-results-full-k{k}.json path under the new prefix),
       - the single `pre_gate_k{k}.json` reference.
       Never modify any sha256, count, or numeric field.
    3. Leave `.planning/milestones/v2.0-phases/10-benchmark-verdict/10-python-preflight.json`
       and `scripts/bench/phase10.py` untouched (out of scope per the context
       section's verified-out list).
  </action>
  <verify>
    <automated>grep -c 'v2.0-phases' scripts/bench/tests/test_phase10_verdict.py | grep -qx '2' && test "$(grep -c 'planning/phases/10-benchmark-verdict' .planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-python-k21.json .planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-python-k31.json | grep -vc ':0$')" = "0" && python3 -m unittest discover -s scripts/bench/tests -t . -p "test_phase10_verdict.py" 2>&1 | grep -q '^OK$'</automated>
  </verify>
  <done>python3 -m unittest discover -s scripts/bench/tests -t . -p "test_phase10_verdict.py" reports OK (Ran 99 tests): test_each_historical_pin_matches_its_committed_copy passes at both k and test_committed_preflight_revalidates_for_both_k passes. Gate baselines at HEAD: 'v2.0-phases' in the test file = 0 (EXPECT 2); 'planning/phases/10-benchmark-verdict' per JSON = 5 (EXPECT 0); suite result = FAILED (failures=1, errors=2) (EXPECT OK).</done>
</task>

<task type="auto">
  <name>Task 2: Fix README WR-04 — rehearsal Stage A/B commands match the recorded runs</name>
  <files>scripts/bench/README.md</files>
  <action>
    In scripts/bench/README.md, section `### dress rehearsal (gates before
    trust)` (planning-time lines 456-471):
    1. Keep the table's Stage and "What it proves" columns and all surrounding
       prose unchanged (lines 452-454 already document the explicit small
       disk floor — the commands must now agree with it).
    2. Replace the two Shape cells (planning-time lines 463-464) so they no
       longer present a runnable-looking but defective invocation: describe
       each stage's true shape per k (Stage A: slice mode, 50000 reads, 2 reps;
       Stage B: slice mode, 200000 reads, 3 reps) and point to the command
       block added in step 3.
    3. Immediately after the table, add a fenced bash block with the REAL
       recorded commands, copy-pasteable via a k loop with every flag
       explicit — flag-for-flag identical to the four `command_line` strings
       in .planning/phases/11-merge-characterization-harness-prep/11-REHEARSAL-RESULTS.json,
       same flag order, same reps/slice-reads/out values:

       DATA=/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split
       # Stage A (gate proof): 50k reads, 2 reps, both k
       for k in 21 31; do
         python3 scripts/bench/bench.py --mode slice --input "$DATA" --slice-reads 50000 --k "$k" --reps 2 \
           --self-check --disk-floor-gb 2 --out "/private/tmp/rustkmer-phase11/rehearsal/A-k$k/results.json"
       done
       # Stage B (full protocol): 200k reads, 3 reps, both k
       for k in 21 31; do
         python3 scripts/bench/bench.py --mode slice --input "$DATA" --slice-reads 200000 --k "$k" --reps 3 \
           --self-check --disk-floor-gb 2 --out "/private/tmp/rustkmer-phase11/rehearsal/B-k$k/results.json"
       done

       (`$DATA` is the pinned input-parts dir; identical to phase10.py's
       DEFAULT_DATA_DIR. The /private/tmp out root matches the recorded runs.)
    4. Do NOT alter any other README section, and do not add or remove flags
       relative to the recorded JSON.
  </action>
  <verify>
    <automated>test "$(grep -c -- '--k {21,31}' scripts/bench/README.md)" = "0" && test "$(grep -c -- '--disk-floor-gb 2' scripts/bench/README.md)" = "2" && test "$(sed -n '/### dress rehearsal/,/## Provenance fields/p' scripts/bench/README.md | grep -c -- '--input')" = "2" && test "$(sed -n '/### dress rehearsal/,/## Provenance fields/p' scripts/bench/README.md | grep -c -- '--slice-reads 50000')" = "1" && test "$(sed -n '/### dress rehearsal/,/## Provenance fields/p' scripts/bench/README.md | grep -c -- '--slice-reads 200000')" = "1"</automated>
  </verify>
  <done>The defective brace-expanded k list reads 0 occurrences in README.md (HEAD baseline: 1); '--disk-floor-gb 2' reads exactly 2 (HEAD baseline: 1, prose only); the dress-rehearsal section carries --input twice and each --slice-reads value once, all inside the stage loops. Commands are flag-for-flag identical to 11-REHEARSAL-RESULTS.json runs[].command_line.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| (none new) | Doc + test-path edits only; no new trust surface is introduced — the archived JSONs stay a consumed trust boundary whose integrity the suite itself re-checks |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-quick-ala-01 | Tampering | .planning/milestones/v2.0-phases/10-benchmark-verdict/10-results-python-k{21,31}.json | low | mitigate | Edits restricted to 5 path-string VALUES per file; every sha256/number byte untouched, and the suite re-derives all content hashes on every run (same guard that rejects tampered projections in _load_python_preflight) |
| T-quick-ala-SC | Tampering | npm/pip/cargo installs | high | mitigate | N/A for this task — no package-manager installs in scope; row kept reserved per quick-task convention |
</threat_model>

<verification>
1. Task 1 gates (HEAD baselines recorded above) all pass.
2. Task 2 gates (HEAD baselines recorded above) all pass.
3. Full-suite gate: `python3 -m unittest discover -s scripts/bench/tests -t .`
   reports 0 failures 0 errors. Known pre-existing flake
   (STATE.md Blockers): test_verify_threads.py's
   TestNegativeControls::test_pre_engine_n_plus_one_stub_is_measured_red is a
   ~50% macOS sample-race flake — if THAT test is the only red, rerun the
   discover command once; a cleared rerun is acceptable, note it in the
   summary. Any other red is a real regression — stop and fix.
4. Diff hygiene: `git diff --stat` for Task 1's commit shows exactly the 3
   files with the expected small line deltas; Task 2's commit touches only
   scripts/bench/README.md.
</verification>

<success_criteria>
- The 3 previously red tests pass against the archived directory; the full
  bench suite is green (0 failures 0 errors, flake clause as above).
- test_phase10_verdict.py changed only by the two path-constant retargets.
- Archived JSONs changed only in 5 path values each; hashes/numbers intact.
- README rehearsal commands are the real recorded commands, copy-pasteable
  with --input, explicit per-k invocations, and --disk-floor-gb 2.
- Each task landed as one atomic commit of exactly its own file set.
</success_criteria>

<output>
Create `.planning/quick/261117-ala-retarget-3-test-phase10-verdict-py-archi/261117-ala-SUMMARY.md` when done
</output>
