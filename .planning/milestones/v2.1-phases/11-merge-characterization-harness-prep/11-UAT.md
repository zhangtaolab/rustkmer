---
status: complete
phase: 11-merge-characterization-harness-prep
source: [11-05-SUMMARY.md coverage D3, deferred-items.md]
started: 2026-11-17T23:24:34Z
updated: 2026-11-17T23:37:22.448Z
---

## Current Test

[testing complete]

## Tests

### 1. D3 — derived -s per k-pair and occupancy gate
expected: Approved -s per k-pair (21→1G, 31→2G) equals executed -s; .jf hash sizes equal within each k-pair; occupancy numeric and <= 0.75 on all four .jf (max 0.6191); decision recorded in 11-PREPARE-RECORD.md §7 before any .jf build.
result: pass
reported: "Agent audit performed at user's request (2026-11-18); D3 evidence independently reproduced from the retained manifest."
notes: |
  Independent verification from /Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/manifest.json
  (retained after the Phase-12 artifact cleanup):
  - hash_size_plan: k=21 hash_size=1G, slots=1,073,741,824, occupancy=0.6190726; k=31
    hash_size=2G, slots=2,147,483,648, occupancy=0.3874931. jellyfish_inputs: both k=21
    records hash_size=1G, both k=31 records hash_size=2G — k-pair equality holds.
  - Executed -s equals the §7 approved values; per-artifact occupancy recomputed from
    distinct/slots: 0.6190 / 0.6191 (k=21), 0.3875 / 0.3875 (k=31); max 0.6191 <= 0.75.
  - Sequencing independently verified: decision commit 5c0c274 (2026-11-16 22:49:14 +0800)
    precedes the first jellyfish count (`when` 23:00:46 local) by ~11.5 minutes; the rkdb
    stage manifest was created at 14:34:12Z. The checkpoint record predates every .jf build.

  Findings (non-blocking, modification suggestions):
  1. 11-PREPARE-RECORD.md §11 records "Free space after the full build: 372.50 GiB", which
     is unreconcilable with §6 (415 GiB before; 359.42 GiB after the 55.75 GiB rkdb build)
     minus §10's 30.98 GiB of .jf output (~328.4 GiB expected); 11-05-SUMMARY.md:165
     propagates 372.50. It is not an input to the 136 GiB D-10 floor (that formula uses
     measured artifact bytes), so there is no downstream effect — but the record should be
     corrected or the measurement context annotated (e.g. APFS purgeable-space reclamation).
  2. "No jellyfish auto-grow occurred" is inferred from occupancy < target, not measured:
     the captured `jellyfish info` records carry only command/when/where/canonical, not the
     final hash size. Future prepare runs should capture the info size fields, or the claim
     should be softened.
  3. Data quality: the 11-05-SUMMARY D3 coverage block fails classification twice — the
     inline `#` comment after `human_judgment: true` hides the boolean from the parser, and
     `rationale` is required when human_judgment is true but absent. Suggest removing the
     inline comment and adding a rationale so the block classifies cleanly.

### 2. Debt — macOS sampling flake disposition
expected: The pre-existing ~50% macOS `sample`-race flake in scripts/bench/tests/test_verify_threads.py::TestNegativeControls::test_pre_engine_n_plus_one_stub_is_measured_red is confirmed environmental and unrelated to the Phase 11 diff; a disposition is chosen (keep acknowledged, or open a fix follow-up).
result: pass
reported: "Agent audit performed at user's request (2026-11-18); flake reproduced 1/18 runs."
notes: |
  Ran the negative-control test 18 times: 17 pass, 1 fail with `requested=4 observed=0`.
  This confirms the documented macOS `sample` race (the helper returns the last observation
  when the child exits below expectation) and is unrelated to Phase 11 — the stub path never
  touches the Phase 11 code.

  Recommended disposition: fix rather than keep acknowledged. Root cause is _thread_count()
  in .planning/research/profiling/verify_threads.py: a successful `sample` whose report
  contains no thread lines parses to 0 and is recorded as last_observed; when the 6 s stub
  exits, observe() returns that 0. A live process always has >= 1 thread, so a parsed 0 is a
  transient artifact — return None (retry) instead, and add a unit test for the empty-report
  case. This removes the race without weakening the negative control (0 was never evidence of
  a real thread count).

### 3. Debt — .claude/CLAUDE.md dataset-line drift
expected: .claude/CLAUDE.md:17 still mirrors the pre-correction "~5.2 GB gzipped r1 across split parts" line while authoritative .planning/PROJECT.md states "~16.7 GB ... six single-member split parts"; a disposition is chosen (regenerate the auto-generated file, or accept the drift as recorded).
result: pass
reported: "Agent audit performed at user's request (2026-11-18); drift confirmed, disposition recommended."
notes: |
  .claude/CLAUDE.md:17 says "~5.2 GB gzipped r1 across split parts"; authoritative
  .planning/PROJECT.md (dataset paragraph and Constraints bullet) says "~16.7 GB ...
  six single-member split parts". The other generated copies (root CLAUDE.md, AGENTS.md,
  docs/dev-guide/claude.md, docs/dev-guide/agents.md) do not carry the stale line.

  The file is gitignored (.gitignore:146 `.claude/`) and untracked, so this is local agent
  context only — no repo/CI impact. No in-repo generator exists for this file (its header
  says "Auto-generated from all feature plans"); precedent quick task 261018-swu edited it
  directly in place. Recommended disposition: scoped manual edit of line 17 to match
  PROJECT.md, and amend the deferred-items entry's "fix = regeneration, not a manual edit"
  wording to record that no generator is available in-repo.

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
