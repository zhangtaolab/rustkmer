---
phase: 10
fixed_at: 2026-11-14T03:39:45Z
review_path: .planning/phases/10-benchmark-verdict/10-REVIEW.md
iteration: 2
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 10: Code Review Fix Report

**Fixed at:** 2026-11-14T03:39:45Z
**Source review:** `.planning/phases/10-benchmark-verdict/10-REVIEW.md`
**Iteration:** 2

**Summary:**
- Findings in scope: 6 (CR-01, WR-01, WR-02, WR-03, WR-04, IN-01)
- Fixed: 6
- Skipped: 0

## Verification

All gates ran in the isolated review-fix worktree
`/Users/forrest/GitHub/rustkmer/.claude/worktrees/rf-10-20726-1794627228`
(branch `gsd-reviewfix/10-20726`), with `target/release/rustkmer` symlinked to
the main checkout's existing release binary so the two real-run tests in
`test_schema.py` could execute. The harness gates themselves are independent of
worktree state.

- `python3 -m unittest discover -s scripts/bench/tests -t .` — **Ran 566 tests,
  OK, skipped=1** (exit 0) on the final tree. This is 557 pre-existing tests plus
  9 regression tests added by this pass (2 WR-01 render, 2 WR-03 module
  identity, 4 IN-01 gate/k identity, 1 WR-02 committed-preflight).
- After the cleanup fast-forward, the same suite was re-run in the main
  checkout (`dev@dce3e8b`): **Ran 566 tests, OK, skipped=1** (exit 0).
- One earlier full-suite run hit the known `test_engine_n_plus_one` sampling
  race (`requested=4 observed=0`); it passed on the second isolated rerun and
  the final full suite passed cleanly, as the pass instructions allow.
- `python3 -m py_compile` after every Python edit (Tier 2 syntax gate), plus
  targeted module runs per finding.
- No Rust file was touched; no `cargo` command was run. `.planning/STATE.md`,
  `ROADMAP.md`, and `state.json` were not edited.
- Each finding is its own commit; the worktree is clean apart from the
  gitignored `target/release/rustkmer` test symlink.

## Measured-value and verdict proof

- The regenerated `10-verdict.json` has `overall: "YES"` and both
  `verdicts[].result == "YES"`. Its `verdicts` array (every result and every
  median value) is deep-equal to the pre-fix verdict.
- k=21: rustkmer median 144.69 s, python median 165.05 s, CLI-session
  jellyfish 194.85 s, Python-session jellyfish 197.95 s.
- k=31: rustkmer median 147.08 s, python median 178.22 s, CLI-session
  jellyfish 1380.92 s, Python-session jellyfish 187.14 s.
- A field-by-field script compared each of the four result documents against
  the pre-fix commit `225303a`, excluding exactly the declared metadata
  additions (`schedule.warmup_order`, `schedule_correction`,
  `pre_gate.committed_copy`): **no rep, median, count, fingerprint, or
  provenance field changed**.
- A second render to scratch paths is byte-identical for the report; the
  verdict differs only in `created`, which `run_render` documents as its only
  varying field. A final post-merge re-render from the main checkout is also
  report-byte-identical, with the verdict identical ignoring `created`.
- Final artifact sha256:
  - `10-BENCHMARK-REPORT.md` — `16fb283dfb0d4c25775906bc84e7dff2a8cea8ab3b5aaafa197e3853e495f7f1`
  - `10-verdict.json` — `54ec12114d92975985c4fac8be7c0aac7dc41113b179b1db9564926560911e61`
  - `10-python-preflight.json` — `40b262162e6da17afbfc65657c82af57be1d85d8f39eea002af0d83bb1145e8a`
- The verdict `inputs` shas equal the four final result documents
  (`f76cb1c6…`, `1ebf2b8c…`, `0f019bed…`, `26f7ecb4…`).

## Fixed Issues

### CR-01: The published report and verdict are the pre-fix render; the required WR-01 disclosure is absent

**Files modified:** `.planning/phases/10-benchmark-verdict/10-BENCHMARK-REPORT.md`, `.planning/phases/10-benchmark-verdict/10-verdict.json`
**Commit:** `300c626`
**Status:** fixed
**Applied fix:** re-ran the documented mechanical render over the four final
result documents, after WR-01/WR-02/WR-04. The report now contains the
cross-session jellyfish disclosure (k=21 ratio 1.02x within the 2.0x factor;
k=31 ratio 7.38x with the explicit "no cross-session timing claim is made"
caveat), the corrected per-rep stats methodology sentence ("exact counts are
re-read from every measured run's OWN output" — the old "single post-arm read
per arm" sentence is gone), and the Python-session CLI parity reference
provenance line. The verdict attributes the MEASURED CLI binary carried by the
source documents (`agent-a24abbc9a0da37b75`, git `97b3f01`) instead of the
render-time worktree binary. No measured number and no verdict changed.

### WR-01: Committed result documents record a warmup order their sessions never ran

**Files modified:** `.planning/phases/10-benchmark-verdict/10-results-full-k21.json`, `10-results-full-k31.json`, `10-results-python-k21.json`, `10-results-python-k31.json`, `scripts/bench/phase10.py`, `scripts/bench/tests/test_phase10_verdict.py`
**Commit:** `683eb36`
**Status:** fixed
**Applied fix:** corrected only `schedule.warmup_order` — CLI sessions
`["rustkmer", "jellyfish"]`, Python sessions `["jellyfish", "pyrustkmer"]` —
and added a self-describing `schedule_correction` block to each document with
`corrected_at: "2026-11-14"`, the prior array, the corrected array, the reason
("pre-fix harness wrote a constant warmup_order; the recorded arms show the
warmups actually run"), `measured_values_changed: false`, and a note that no
rep/median/count/fingerprint/provenance field changed. Added a render-time
`_validate_warmup_order` guard that rejects any document whose recorded order
names a tool it never measured or omits a measured tool, with regression tests.
The rendered methodology line now states `warmup order: rustkmer, jellyfish`
(CLI session); the three-tool false claim no longer appears.

### WR-02: Committed preflight records use the superseded 86 B model

**Files modified:** `.planning/phases/10-benchmark-verdict/10-python-preflight.json`, `scripts/bench/tests/test_phase10_verdict.py`
**Commits:** `177b7eb` (record), `dce3e8b` (regression test)
**Status:** fixed
**Applied fix:** re-ran `--stage preflight-python` from the committed CLI
documents. The record now carries the 86.5 B model projections:
77,613,559,257 B (k=21) and 99,159,586,400 B (k=31), both PROCEED under the
118,111,600,640 B budget. Added a top-level `model_revision` note recording the
2026-11-14 re-derivation under `ceil(86.5 * distinct)`, the superseded 86 B
model, that the decision is unchanged, and that the Python session documents
retain their historical `memory_preflight` blocks. Added a regression test that
the committed artifact re-validates under `_load_python_preflight` for both k.
The two Python session documents' `memory_preflight` blocks were deliberately
left untouched: they record what the gate computed at run time, including the
historical 86 B `projected_bytes`.

### WR-03: The module-identity guard is inert on `python_bench.py`'s controller path

**Files modified:** `scripts/bench/python_bench.py`, `scripts/bench/tests/test_python_bench.py`
**Commit:** `b6c3461`
**Status:** fixed: requires human verification
**Applied fix:** `measure_arm.one_run` now records `module_mtime` from the
worker payload and `module_sha256` from `fingerprint(payload["module_path"])`
on every measured rep, so `check_rep_identity` actually compares the
`(path, sha256, mtime)` tuple on the Phase-9/python_bench controller too.
Regression tests assert the fields are present with the measured sha, and a
fake worker that replaces the `.so` bytes at the same path between reps causes
`check_rep_identity` to raise "rep module identity disagreement".

### WR-04: Committed Python documents pin pre-gate artifacts that are not in the repository

**Files modified:** `.planning/phases/10-benchmark-verdict/10-results-python-k21.json`, `10-results-python-k31.json`, `.planning/phases/10-benchmark-verdict/evidence/pre_gate_k21.json` (new), `.planning/phases/10-benchmark-verdict/evidence/pre_gate_k31.json` (new)
**Commit:** `e9e02e5`
**Status:** fixed
**Applied fix:** copied the consumed artifacts byte-for-byte into the phase
directory and verified their sha256 against the pins already recorded in the
documents:
- `/tmp/rustkmer-phase10/scratch/pre_gate_k21.json` → `evidence/pre_gate_k21.json`, sha256 `4f958c19053dc1297f4998f7dfe1258b35f5d4610a0859234c71c65e4d5e8ea3`
- `/tmp/rustkmer-phase10/scratch/pre_gate_k31.json` → `evidence/pre_gate_k31.json`, sha256 `b9f3d85061085ab7fe3712938a01afa15ec9df1e7347b7bd0ae54864b77082b2`

Each Python document's `pre_gate` block gained a path-only `committed_copy`
field pointing at its copy; the historical `path` and `sha256` fields were not
changed. Both committed copies also pass `_load_slice_gate_doc` for k=21 and
k=31.

### IN-01: Consumed-evidence stages do not pin the k identity of what they consume

**Files modified:** `scripts/bench/phase10.py`, `scripts/bench/tests/test_phase10_verdict.py`, `scripts/bench/tests/test_python_full_arm.py`
**Commit:** `9eb73b4`
**Status:** fixed: requires human verification
**Applied fix:** `preflight_records` now requires
`set(seen_k) == set(SLICE_GATE_K_VALUES)` (exactly the pinned `{21, 31}` pair).
`_load_slice_gate_doc(path, k)` validates the gate matching the session's k,
not only k=21: the requested k's gate must exist exactly once, carry positive
integer `distinct`/`total`, and carry a `slice_recipe.source_sha256` equal to
the k=21 gate's (proving both gates describe the same provisioned slice). The
pinned head-4M counts and reference-sha checks are retained for k=21.
`run_python_session` now passes `args.k`. Regression tests cover a k=31
session with only a k=21 gate, a valid k=31 gate, and a k=31 gate from a
different slice.

## WR-09 correction

The iteration-1 report quoted 90.83 GB (k=21) and 103.80 GB (k=31) as the
post-fix projections. Those numbers use the test-fixture/estimate distinct
counts. For the MEASURED distinct counts the corrected 86.5 B projections are:

- k=21: `ceil(86.5 * 897,266,581)` = **77,613,559,257 B** (about 72.28 GiB)
- k=31: `ceil(86.5 * 1,146,353,600)` = **99,159,586,400 B** (about 92.35 GiB)

Both are under the 118,111,600,640 B budget, so the PROCEED decision is
unchanged. These are the values now committed in `10-python-preflight.json`.

## Evidence-history and residual limitations

- The Python session documents' historical `memory_preflight` blocks (and their
  `cross_session` blocks) still pin the pre-WR-01 CLI-document bytes
  (`757c923a…` for k=21 and `90804c50…` for k=31). Those exact historical bytes
  are not committed anywhere; only the current corrected CLI documents
  (`f76cb1c6…`, `1ebf2b8c…`) are. The blocks are deliberate run-time records;
  the regenerated preflight's `model_revision.note` documents the supersession,
  and the historical values are not used by any stage after this pass.
- The evidence copies are now repository-verifiable. The scratch directory
  `/tmp/rustkmer-phase10/scratch/` itself remains ephemeral, but the two
  consumed pre-gate artifacts were copied byte-for-byte and their sha256 pins
  re-verified, so the WR-04 chain no longer depends on `/tmp`.
- No other residual unverifiable evidence was found: the render stage consumes
  only the committed result documents, and the verdict `inputs` shas match
  those documents.

## Skipped Issues

None — all in-scope findings were fixed.

---

_Fixed: 2026-11-14T03:39:45Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
