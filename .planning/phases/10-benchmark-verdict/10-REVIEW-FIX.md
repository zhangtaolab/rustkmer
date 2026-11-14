---
phase: 10-benchmark-verdict
fixed_at: 2026-11-14T03:57:09Z
review_path: .planning/phases/10-benchmark-verdict/10-REVIEW.md
iteration: 3
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 10: Code Review Fix Report

**Fixed at:** 2026-11-14T03:57:09Z
**Source review:** `.planning/phases/10-benchmark-verdict/10-REVIEW.md`
**Iteration:** 3 (final `--auto` pass)

**Summary:**
- Findings in scope: 5 (WR-05, WR-06, WR-07 from the review; IN-02 and IN-03 added to scope by the orchestrator's iteration-3 dispatch)
- Fixed: 5
- Skipped: 0

All six earlier fixes were left untouched — the re-review confirmed them genuine, and this
pass reverts or "re-fixes" none of them. **No measured number, median, count, fingerprint,
or verdict changed.** Work was performed in the isolated worktree
`.claude/worktrees/rf-10-33276-1794628150` (branch `gsd-reviewfix/10-33276`); every commit
below is on that branch and was fast-forwarded to `dev` by the cleanup tail.

## Fixed Issues

### WR-05: The rendered report stated the CLI warmup order and rotation as report-wide methodology

**Files modified:** `scripts/bench/phase10.py`, `scripts/bench/tests/test_phase10_verdict.py`
**Commit:** `6ccfd2e`
**Applied fix:** Added `_session_schedules(docs)`, which groups the validated documents by
`session`, orders them CLI then Python (independent of `--docs` order), and rejects
documents of one session that disagree on `policy`, `warmup_order`, or `rounds`.
`_methodology_lines` now emits one "schedule policy / warmup order" bullet and one
"recorded rotation" bullet per session instead of reading `docs[0]` report-wide. The rendered
report now states, from each session's own document:

```
- CLI session schedule policy: round-robin-rotation; warmup order: rustkmer, jellyfish.
- CLI session recorded rotation: round 0: rk-t16 then rk-t1 then jf-t16; ...
- Python session schedule policy: round-robin-rotation; warmup order: jellyfish, pyrustkmer.
- Python session recorded rotation: round 0: jf-t16 then py-t16; round 1: py-t16 then jf-t16; round 2: jf-t16 then py-t16.
```

Tests added: `test_each_session_schedule_is_rendered_from_its_own_document` (asserts the
Python order and the exact 2-arm rotation, and that the CLI 3-arm rotation is never rendered
as the Python session's) and `test_session_documents_disagreeing_on_schedule_are_rejected`.
Output remains byte-deterministic (verified by a scratch re-render).

### WR-06: Python session documents pinned CLI-document bytes that no longer existed in the tree

**Files modified:** `.planning/phases/10-benchmark-verdict/evidence/historical_cli_k21.json` (new),
`.planning/phases/10-benchmark-verdict/evidence/historical_cli_k31.json` (new),
`.planning/phases/10-benchmark-verdict/10-results-python-k21.json`,
`.planning/phases/10-benchmark-verdict/10-results-python-k31.json`,
`.planning/phases/10-benchmark-verdict/10-python-preflight.json`,
`scripts/bench/tests/test_phase10_verdict.py`
**Commit:** `4313c71`
**Applied fix:** Extracted the historical CLI documents verbatim from commit `225303a`
(`git show 225303a:<path>`) into `evidence/historical_cli_k21.json` and
`historical_cli_k31.json`. Their sha256 values equal the historical pins exactly:
`757c923a7278c06b663ab8720d22cf32abdc10b35a81d65a85765a50be900d6f` (k=21) and
`90804c50822dfeb2cbad1d37e413fd07a0fb3471cd776ce40ceff4347b96b5d2` (k=31). Added a
path-only `committed_copy` beside each historical pin in both `memory_preflight` and
`cross_session`; the historical sha fields were not changed. Added an explicit
`supersession_note` to each block (and extended `model_revision.note` in
`10-python-preflight.json`) stating that the corrected CLI documents
(`f76cb1c6…` / `1ebf2b8c…`) are the current render inputs and the historical bytes are
preserved for pin verification. Mirrors the WR-04 `pre_gate.committed_copy` pattern.
New regression test `TestCommittedHistoricalCliEvidence` re-hashes each committed copy and
asserts it equals both historical pins, that the named CLI document is the differing
corrected document, and that the supersession notes are present.

### WR-07: The Plan-10-04 summary still reported the superseded 86 B preflight values

**Files modified:** `.planning/phases/10-benchmark-verdict/10-04-SUMMARY.md`
**Commit:** `b4749cd`
**Applied fix:** Updated the `provides`, `key-decisions`, `coverage` (D1 description and
quoted verification output), `Accomplishments`, and `Verification` text to the delivered
86.5 B values: **77,613,559,257 B (k=21) / 99,159,586,400 B (k=31)**, headroom
40,498,041,383 B / 18,952,014,240 B, both PROCEED vs 118,111,600,640 B. The original
run-time 86 B values (77,164,925,966 / 98,586,409,600 B) remain visible beside each updated
number, explicitly marked superseded, and the pre-WR-09/86 B model is annotated in the
`requires` block. Added a dated revision note at the top of the body. History is annotated,
not rewritten; no measurement was re-run and the PROCEED decision is unchanged.

### IN-02: "Last commit touching this renderer" actually named bench.py's last commit

**Files modified:** `scripts/bench/phase10.py`, `scripts/bench/tests/test_phase10_verdict.py`
**Commit:** `afbe964`
**Applied fix:** Added a local `renderer_source_commit()` in `phase10.py` that runs
`git log -1 -- phase10.py` (deterministic; `unknown` outside a git checkout) and used it for
the provenance line. Removed the now-unused `harness_source_commit` import (bench.py keeps
its own function for its own report). The rendered value now equals the last commit that
touched `phase10.py` (`afbe964e729e6035819ff0fb24fcbc7164717bb4` at render time), not
`bench.py`'s `d6a5857c…`. Tests added: one asserts the helper queries a path ending in
`phase10.py`; one asserts the rendered value equals a live `git log -1 -- phase10.py`.

### IN-03: README exit contract said exit 2 writes no artifact, but a BLOCKED preflight writes one

**Files modified:** `scripts/bench/README.md`
**Commit:** `0736c41`
**Applied fix:** Amended the Phase-10 exit-contract paragraph to state the single documented
exception: `preflight-python` always writes its PROCEED/BLOCKED decision record, so a BLOCKED
projection writes the record and then exits **2**; the decision is evidence, and the record
carries no measurement. Every other stage's exit 2 still writes no artifact. This reconciles
the paragraph with the stage table and
`test_blocked_projection_still_writes_the_record_and_returns_2`.

### Deliverable re-render (supports WR-05, WR-06, IN-02)

**Files modified:** `.planning/phases/10-benchmark-verdict/10-verdict.json`,
`.planning/phases/10-benchmark-verdict/10-BENCHMARK-REPORT.md`
**Commit:** `8fcb85e`
**Applied fix:** Ran the documented render over the four final committed documents after all
code/doc edits. The verdict diff vs the pre-fix artifact shows only `created` and the two
Python-document input fingerprints; the `verdicts` array is byte-for-byte deep-equal. The
report diff shows only the per-session methodology bullets and the corrected provenance
commit line. A second render is byte-identical for the report.

## Verification

**Where the gates ran:** the per-fix and render checks ran in the isolated worktree
`.claude/worktrees/rf-10-33276-1794628150`; the final full suite, the final re-render, and
the input-sha check were also repeated in the main checkout after `dev` was fast-forwarded
to `8fcb85e` and the worktree was removed. The worktree has no Rust build; the two
`test_schema` cases that execute a real binary need a release binary, so in the worktree
`target/release/rustkmer` was symlinked from the main checkout
(sha256 `f6ace9f7…`, 2,966,832 B — **the phase's measured binary `8f38d20c…` was not
re-run**; those tests only exercise a small synthetic count for provenance self-consistency).

- `python3 -m unittest discover -s scripts/bench/tests -t .` → **Ran 571 tests, OK
  (skipped=1)** in the isolated worktree (clean full run on the final tree) **and again in
  the main checkout** after the fast-forward (real `target/release/rustkmer`; `Ran 571
  tests in 10.223s, OK (skipped=1)`). The documented `test_engine_n_plus_one` flake failed
  in two later worktree full runs with `observed=0` and **passed isolated**
  (`Ran 1 test, OK`), as permitted.
- Re-render over the four final committed docs exits 0 and is **byte-identical** to the
  committed `10-BENCHMARK-REPORT.md` (verified in the worktree before and after the render
  commit, and again in the main checkout after cleanup).
- `10-verdict.json`: overall **YES**; `verdicts` deep-equal to the pre-fix verdict.
- Verdict `inputs` match the final four documents:
  k21 CLI `f76cb1c6002c234b34291ab6ec676e0d8417daa5d4ecbf03281286c69e0d19b6`,
  k31 CLI `1ebf2b8c0d07c15a00519e52d99c5ab2bd52d50757e74bc921c8fc91194df819`,
  k21 Python `0582bbc01f5f763d845dbc9e1ce90a63247e1bacbc08e5eebf9ba0f3bf490871`,
  k31 Python `1f737095c6ed54dd649f87bc4bf2728affded4c478da2dcbf79e9809cb85409f`.
- No measurement was re-run; no Rust test/build was run.
- `.planning/STATE.md`, `.planning/ROADMAP.md`, and `.planning/state.json` were not edited.

**Proof no measured number or verdict changed** (all against pre-fix commit `dce3e8b`):

| Check | Result |
|---|---|
| verdict `verdicts` array (every median) | deep-equal |
| verdict `overall` / `descoped` / flags / provenance | equal (overall `YES`) |
| k=21 medians (rk / jf-cli / py / jf-py) | 144.69 / 194.85 / 165.05 / 197.95 s |
| k=31 medians (rk / jf-cli / py / jf-py) | 147.08 / 1380.92 / 178.22 / 187.14 s |
| CLI k=21 / k=31 documents | byte-identical to `dce3e8b` |
| Python documents after removing exactly the 4 added metadata fields | deep-equal |
| preflight records / provenance (only `model_revision.note` changed) | equal; decisions `PROCEED`, `PROCEED` |
| report diff | only per-session schedule lines and the provenance commit line |

**Final artifact shas:**

- `10-BENCHMARK-REPORT.md`: `572d036bf923a3a78f4f5d36a3316e9358f3bd974d116a583ba7b0197ff403dc`
- `10-verdict.json`: `d37eba8424bdbd25987b50e30744adc4dbb1ccd835c8fe685aecd397f82c6c5f`
- `10-python-preflight.json`: `b4cf80247ff78468c43fbab659c9519e4342a0bcdd15ca5beaa7a93698f19acd`
- `evidence/historical_cli_k21.json`: `757c923a7278c06b663ab8720d22cf32abdc10b35a81d65a85765a50be900d6f`
- `evidence/historical_cli_k31.json`: `90804c50822dfeb2cbad1d37e413fd07a0fb3471cd776ce40ceff4347b96b5d2`

**Residual, deliberately preserved (not errors):**

- The Python session documents' `memory_preflight` blocks still record the run-time 86 B
  projections (77,164,925,966 / 98,586,409,600 B). They are historical run-time evidence;
  WR-02's constraint was not to rewrite them. The delivered artifact and this summary carry
  the current 86.5 B values, and the historical CLI pins are now verifiable from the
  committed copies.
- The pre-gate `path` entries still name `/tmp/rustkmer-phase10/scratch/...`; the committed
  `evidence/pre_gate_k*.json` copies from the prior iteration remain the verifiable bytes.

---

_Fixed: 2026-11-14T03:57:09Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 3_
