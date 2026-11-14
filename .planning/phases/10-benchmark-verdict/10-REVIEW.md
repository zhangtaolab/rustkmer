---
phase: 10-benchmark-verdict
reviewed: 2026-11-14T03:52:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - scripts/bench/README.md
  - scripts/bench/bench.py
  - scripts/bench/phase10.py
  - scripts/bench/python_bench.py
  - scripts/bench/tests/test_phase10_verdict.py
  - scripts/bench/tests/test_python_bench.py
  - scripts/bench/tests/test_python_full_arm.py
  - scripts/bench/tests/test_time_parser.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
  necessity: 0
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-11-14T03:52:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Final `--auto` re-review (iteration 3 of 3) of the Phase-10 benchmark-verdict
harness. I re-read all eight submitted files and verified each of the six
claimed fixes against the committed evidence and the current code, not the fix
report.

**All six claimed fixes verify:**

1. **CR-01** — A fresh `--stage render` over the four committed result
   documents to scratch exits 0 and is **byte-identical** to the committed
   `10-BENCHMARK-REPORT.md` (`diff` empty). The regenerated verdict is
   identical except `created`; the `verdicts` array (every result and median)
   is deep-equal to the pre-fix verdict, `overall` is still `YES`, and the
   verdict's four `inputs` sha256 values equal the current documents
   (`f76cb1c6…`, `1ebf2b8c…`, `0f019bed…`, `26f7ecb4…`).
2. **WR-01** — All four result documents now record the warmup order their
   session actually ran (CLI `["rustkmer","jellyfish"]`, Python
   `["jellyfish","pyrustkmer"]`), each with a self-describing
   `schedule_correction` block. Scrubbing exactly `schedule.warmup_order`,
   `schedule_correction` and `pre_gate.committed_copy` from the current
   documents makes them deep-equal to commit `225303a`: no rep, median, count,
   fingerprint or provenance field changed. `_validate_warmup_order` rejects a
   order naming an unmeasured tool (verified directly against the committed
   CLI document).
3. **WR-02** — `10-python-preflight.json` re-validates under
   `_load_python_preflight` for both k under the 86.5 B model
   (77,613,559,257 B and 99,159,586,400 B, both PROCEED). The Python session
   documents' historical `memory_preflight` blocks are untouched and the
   preflight artifact's `model_revision.note` documents the supersession.
4. **WR-03** — `python_bench.measure_arm.one_run` now records
   `module_mtime` from the worker payload and `module_sha256` from
   `fingerprint(payload["module_path"])` on every measured rep, so
   `check_rep_identity`'s `(path, sha256, mtime)` tuple is live on the
   `python_bench` controller; the same-path rebuild test raises
   "module identity disagreement".
5. **WR-04** — `evidence/pre_gate_k21.json` (sha `4f958c19…`) and
   `evidence/pre_gate_k31.json` (sha `b9f3d850…`) match the documents' pins
   exactly and are referenced by `pre_gate.committed_copy`; both pass
   `_load_slice_gate_doc` for k=21 and k=31.
6. **IN-01** — `preflight_records` requires exactly the pinned `{21,31}` pair,
   and `_load_slice_gate_doc(path, k)` validates the session's own k gate
   (plus the shared slice source sha for k=31).

The full harness suite passes in the main checkout:
`python3 -m unittest discover -s scripts/bench/tests -t .` → **Ran 566 tests,
OK, skipped=1**.

The residual issues below are consequences of the fixes themselves (the
WR-01 metadata correction changed the CLI documents after the Python sessions
recorded pins to them; the WR-02 preflight regeneration was not propagated to
the planning summaries) plus two accuracy defects in the rendered
methodology/provenance text.

No necessity findings: I read
`$HOME/.claude/gsd-core/references/necessity-review.md`; every guard examined
sits at a real trust boundary (committed JSON evidence, subprocess output,
worker payloads) or is a documented test seam. No project skills are present
under `.claude/skills/` or `.agents/skills/`.

## Narrative Findings (AI reviewer)

### Warnings

#### WR-05: The rendered report states the CLI warmup order (and CLI rotation) as the report-wide methodology

**File:** `.planning/phases/10-benchmark-verdict/10-BENCHMARK-REPORT.md:76-77`; source `scripts/bench/phase10.py:1307-1329` (`_methodology_lines`, `schedule = docs[0].get("schedule")` at line 1310)
**Severity:** WARNING

**Issue:** `_methodology_lines` reads the schedule from `docs[0]` only and emits
one "warmup order" and one "recorded rotation" line for the whole report.
`docs[0]` is always the CLI k=21 document (the documented render command's
order), whose schedule is `["rustkmer","jellyfish"]` with a 3-arm rotation.
Both Python-session documents record `warmup_order: ["jellyfish","pyrustkmer"]`
and a 2-arm rotation (`10-results-python-k21.json:226-240`,
`10-results-python-k31.json:226-240`). The report therefore claims a
`rustkmer` warmup — and a `rk-t16`/`rk-t1` rotation — for sessions that never
ran either. This is the same false warmup claim the WR-01 fix removed from the
documents, reintroduced at report scope because the schedule is session-local
while the methodology section is not. The regression test only asserts the CLI
string is present (`test_rendered_warmup_order_is_the_recorded_session_order`);
it never checks that the Python session's order is rendered.

**Fix:** render the schedule per session, e.g. group the validated documents by
`session` in `_methodology_lines` and emit one "warmup order / recorded
rotation" bullet per session (the per-session arm tables already establish the
grouping), or scope the existing line to "CLI session: …" and add the Python
line. Add a test asserting `warmup order: jellyfish, pyrustkmer` appears for
the Python session. Re-render the report (measured numbers unchanged).

#### WR-06: Python session documents pin CLI-document bytes that no longer exist in the tree

**File:** `.planning/phases/10-benchmark-verdict/10-results-python-k21.json:218,222`, `.planning/phases/10-benchmark-verdict/10-results-python-k31.json:218,222`
**Severity:** WARNING

**Issue:** Both Python documents pin the consumed CLI document to
`757c923a…` (k=21) and `90804c50…` (k=31) in `memory_preflight.source_sha256`
and `cross_session.cli_doc_sha256`. The committed CLI documents are now
`f76cb1c6…` and `1ebf2b8c…` because the WR-01 metadata correction changed
their bytes. The pinned bytes are recoverable only from git history (verified:
`git show 225303a:<path>` hashes to exactly those two values); they are not in
the working tree, so the pin at the named path cannot be verified from a clean
checkout and now contradicts the file it names. The preflight artifact's
`model_revision.note` says the `memory_preflight` blocks are historical but
does not mention the sha mismatch, and the `cross_session` pin has no
supersession note at all. This is the same unverifiable-pin class as the
resolved WR-04 and is a side effect of the WR-01 fix, which the fix report
acknowledges as a residual limitation but leaves unfixed.

**Fix:** commit the historical CLI documents (recoverable from `225303a`)
beside the pre-gate copies under `evidence/` and add a `committed_copy` field to
both blocks, mirroring the WR-04 remediation; or add an explicit supersession
note recording the current sha256 for each pin. Either way, re-render the
verdict and report afterwards so `10-verdict.json`'s `inputs` shas match the
modified documents.

#### WR-07: The Plan-10-04 summary still reports the superseded 86 B preflight values

**File:** `.planning/phases/10-benchmark-verdict/10-04-SUMMARY.md:17,19,53,55,64,68,111`
**Severity:** WARNING

**Issue:** The completion summary states that `10-python-preflight.json`
contains the 86 B projections 77,164,925,966 B (k=21) and 98,586,409,600 B
(k=31) with 38.13 / 18.18 GiB headroom, and its coverage-D1 verification
quotes `'preflight OK {21: (897266581, 77164925966, …), 31: (1146353600,
98586409600, …)}'`. The committed artifact now carries the 86.5 B model:
77,613,559,257 B / 99,159,586,400 B, headroom 40,498,041,383 B / 18,952,014,240
B (about 37.72 / 17.65 GiB). The PROCEED decision is unchanged, but the
summary's description of the delivered artifact and its recorded verification
evidence no longer match what is committed. `10-01-SUMMARY.md:91,132` and
`10-03-SUMMARY.md:169-174` also describe the then-current 86 B model; if those
are immutable checkpoint records they can stand, but `10-04-SUMMARY.md` is the
final Plan-10-04 completion record and is stale (the WR-02 fix did not update
it).

**Fix:** update the `provides`, `key-decisions`, `coverage` and `Accomplishments`
numbers (and the quoted verification output) to the committed 86.5 B values, or
explicitly label the 86 B block as the pre-WR-09 historical projection and cite
the current artifact for the delivered numbers.

### Info

#### IN-02: "Last commit touching this renderer" actually names bench.py's last commit

**File:** `.planning/phases/10-benchmark-verdict/10-BENCHMARK-REPORT.md:91`; source `scripts/bench/phase10.py:1435-1437`, `scripts/bench/bench.py:1569-1585`
**Severity:** INFO

**Issue:** `_provenance_lines` calls `harness_source_commit()`, imported from
`bench.py`, where the function hashes `Path(__file__)` — i.e. `bench.py`, not
`phase10.py`. The report labels the result "last commit touching this renderer"
and prints `d6a5857c…`, which is the last commit touching `bench.py`; the last
commit touching `phase10.py` is `9eb73b45…` (IN-01). A reader checking out
`d6a5857` gets an older `phase10.py` that lacks the warmup guard and the k-pair
checks. Byte-identity is unaffected (the value is deterministic), but the
provenance statement is wrong.

**Fix:** compute the commit for the actual file (a local helper running
`git log -1 -- <phase10.py>`) or reword the line to "harness (bench.py) last
commit"; re-render.

#### IN-03: README exit contract says exit 2 writes no artifact, but `preflight-python` writes a BLOCKED record on exit 2

**File:** `scripts/bench/README.md:350,358-360`; `scripts/bench/phase10.py:1901-1927`
**Severity:** INFO

**Issue:** The Phase-10 exit contract says **"2 — invalid or inapplicable (no
artifact written)"**, but `run_preflight_python` writes
`10-python-preflight.json` and then returns `EXIT_INVALID` when the projection
is BLOCKED. The stage table at README:350 and the regression test
`test_blocked_projection_still_writes_the_record_and_returns_2` both require the
record, so the two README statements contradict each other.
**Fix:** state the preflight exception in the exit-contract paragraph (a
BLOCKED projection writes its decision record and exits 2), or give a BLOCKED
decision a distinct exit code.

---

_Reviewed: 2026-11-14T03:52:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
