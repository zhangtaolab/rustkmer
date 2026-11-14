---
phase: 10-benchmark-verdict
reviewed: 2026-11-14T03:29:21Z
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
  critical: 1
  warning: 4
  info: 1
  total: 6
  necessity: 0
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-11-14T03:29:21Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

This is an `--auto` re-review of the fix pass over the Phase-10 benchmark-verdict
harness. I re-read the eight submitted files, ran the full harness suite
(`python3 -m unittest discover -s scripts/bench/tests -t .`: **Ran 557 tests,
OK, 1 skipped**), and re-ran the stage entry points against the committed
evidence.

The sixteen claimed fixes are genuinely in the code: the render stage requires
exactly the pinned `{21, 31}` document set with one cli + one python document
per k (`phase10.py:1007-1012`); non-finite values are rejected on every
rep/median path (`validate_rep_memory`, `validate_arm_medians`,
`surface_result`); recorded medians are recomputed from the raw reps and must
match exactly (`phase10.py:694-745`); the preflight gate is re-derived with
`MEMORY_BUDGET_BYTES` and cross-checked against the consumed CLI document
(`phase10.py:2187-2281`); the cross-session divergence is rendered
(`phase10.py:1155-1172`); and `publish_atomic` backs up and restores
pre-existing destinations on failure (`phase10.py:1477-1559`). A fresh
`--stage render` over the four committed result documents exits 0 and is
byte-identical across two runs; no measured number and no verdict changed.

What did **not** happen is the publication step: the committed
`10-BENCHMARK-REPORT.md` and `10-verdict.json` are still the pre-fix renderer's
output, so the delivered report does not contain the mandate WR-01 disclosure
and still carries a now-false methodology sentence and pre-WR-04 provenance.
The committed CLI/Python result documents also still carry the pre-WR-02 false
warmup order, and the committed preflight artifact still uses the pre-WR-09
86 B model, which the current `python` stage now rejects. Separately, the
WR-07 module-identity guard is inert on `python_bench.py`'s own controller path
because that caller never records the fields the guard compares.

No necessity findings: I read
`$HOME/.claude/gsd-core/references/necessity-review.md`; every guard examined
sits at a real trust boundary (committed JSON evidence, subprocess output,
worker payloads) or is a documented test seam. No project skills are present
under `.claude/skills/` or `.agents/skills/`.

One correction to the fix report's WR-09 note: the fresh 86.5 B projections for
the measured distinct counts are **77,613,559,257 B (k=21)** and
**99,159,586,400 B (k=31)** — not the quoted 90.83/103.80 GB (those use the
test-fixture/estimate distinct counts). Both remain under the
118,111,600,640 B budget, so the PROCEED decision is unchanged.

## Narrative Findings (AI reviewer)

### Critical Issues

#### CR-01: The published report and verdict are the pre-fix render; the required WR-01 disclosure is absent

**File:** `.planning/phases/10-benchmark-verdict/10-BENCHMARK-REPORT.md:49-58` (verdict section), `.planning/phases/10-benchmark-verdict/10-verdict.json:70-82` (provenance); the disclosure code is `scripts/bench/phase10.py:1155-1172`
**Severity:** BLOCKER

**Issue:** WR-01's acceptance condition is that the *report* mechanically
discloses the cross-session jellyfish divergence. The fix landed in code, but
the committed artifacts were never regenerated. Verified by re-rendering the
four committed documents and diffing:

- the published report has no `cross-session jellyfish reference` line at all;
  a fresh render adds `k=21 … ratio 1.02x … within the documented 2.0x` and
  `k=31 … ratio 7.38x … no cross-session timing claim is made`;
- the published report still says "`rustkmer stats` is a single post-arm read
  per arm … it is not a per-rep cost" (line 79), which contradicts the WR-06
  fix (counts are now read after *every* measured CLI/jellyfish rep);
- the published report lacks the WR-03 "Python session CLI parity reference"
  provenance line (absent after line 87);
- `10-verdict.json` still attributes the render-time worktree binary
  (`agent-a5eb35be1e40e77fd`, git `10f0591`) instead of the MEASURED CLI
  provenance carried by the source documents (`agent-a24abbc9a0da37b75`, git
  `97b3f01`, per the k=21 CLI document) — i.e. the pre-WR-04 behavior.

A fresh render reproduces every measured number and the overall YES exactly
(verified: identical verdicts apart from `created`/provenance, two renders
byte-identical). The defect is that the deliverable a reader/next phase
consumes does not contain the mandated disclosure and misstates the current
methodology.

**Fix:** re-run the documented mechanical render and commit both outputs (no
measurement, no number changes):

```bash
python3 scripts/bench/phase10.py --stage render \
  --docs .planning/phases/10-benchmark-verdict/10-results-full-k21.json \
         .planning/phases/10-benchmark-verdict/10-results-full-k31.json \
         .planning/phases/10-benchmark-verdict/10-results-python-k21.json \
         .planning/phases/10-benchmark-verdict/10-results-python-k31.json \
  --verdict-out .planning/phases/10-benchmark-verdict/10-verdict.json \
  --out .planning/phases/10-benchmark-verdict/10-BENCHMARK-REPORT.md
```

If the committed artifacts must stay frozen, add an explicit note to
`10-04-SUMMARY.md`/the report stating that the publishable report must be
re-rendered with the fixed renderer and why — but leaving the report without
the WR-01 caveat is not acceptable.

### Warnings

#### WR-01: Committed CLI/Python result documents still record a warmup order their sessions never ran

**File:** `.planning/phases/10-benchmark-verdict/10-results-full-k21.json:208-214`, `.planning/phases/10-benchmark-verdict/10-results-full-k31.json:208-214`, `.planning/phases/10-benchmark-verdict/10-results-python-k21.json:223-229`, `.planning/phases/10-benchmark-verdict/10-results-python-k31.json:223-229`; rendered at `10-BENCHMARK-REPORT.md:74`; code `scripts/bench/phase10.py:301-312, 2070-2075`
**Severity:** WARNING

**Issue:** All four committed documents record
`warmup_order: ["rustkmer", "jellyfish", "pyrustkmer"]`. The CLI session's
arms are `rk-t16`/`rk-t1`/`jf-t16`, so no `pyrustkmer` warmup ever ran; the
Python session's arms are `jf-t16`/`py-t16`, so no `rustkmer` warmup ran. The
fixed `tool_warmup_order` would record `["rustkmer","jellyfish"]` and
`["jellyfish","pyrustkmer"]` respectively. The report line still prints the
three-tool claim, so WR-02's finding — a session claiming warmups it never
performed — remains present in the delivered evidence even though the code is
fixed. (The fix report explicitly states no committed artifact was modified.)

**Fix:** either re-run the two sessions with the fixed harness, or correct only
the `schedule.warmup_order` metadata in the four documents with a revision note
(discarded warmups carry no measured number), then re-render. Add a render-time
check that derives the expected warmup order from the document's arms and
rejects a document whose recorded order names a tool not present.

#### WR-02: The committed preflight records use the superseded 86 B model and are rejected by the current `python` stage

**File:** `.planning/phases/10-benchmark-verdict/10-python-preflight.json:12,16,24,28`, `.planning/phases/10-benchmark-verdict/10-results-python-k21.json:209-217`, `.planning/phases/10-benchmark-verdict/10-results-python-k31.json:209-217`; code `scripts/bench/phase10.py:2227-2232`
**Severity:** WARNING

**Issue:** WR-09's fix changed `python_projection_bytes` to the true 86.5 B
upper bound, but the committed records still carry the 86 B projections
(77,164,925,966 / 98,586,409,600, model string
`python-86B-per-distinct-conservative-two-call-upper-bound`). Verified against
the current loader:

```
k=21: FAIL: projected_bytes=77164925966 != the model's 77613559257
k=31: FAIL: projected_bytes=98586409600 != the model's 99159586400
```

so a re-run of the documented `python` stage from committed evidence exits 2
before any measurement, and the two Python session documents embed the same
stale derived values. Regenerating the record from the *committed* CLI
documents is mechanical and succeeds (`PROCEED` at both k, verified), so the
decision is unaffected — but the evidence chain as committed is not
self-consistent, and the fix report's acknowledged limitation is a regression
introduced by the WR-09 fix.

**Fix:** re-run `--stage preflight-python` from the committed CLI documents and
commit the regenerated `10-python-preflight.json` (derived evidence, no
measurement); either update the two Python documents' derived
`memory_preflight` block with a revision note or state in the report that the
embedded projection is the historical 86 B model. Add a test that the committed
preflight artifact re-validates under `_load_python_preflight`.

#### WR-03: WR-07's module-identity guard is inert on `python_bench.py`'s own controller path

**File:** `scripts/bench/python_bench.py:758-773` (`one_run`), `:786` (`check_rep_identity` call), `:329-367` (`check_rep_identity`); contrast `scripts/bench/phase10.py:418-422`
**Severity:** WARNING

**Issue:** `check_rep_identity` now compares
`(module_path, module_sha256, module_mtime)` across reps. But
`python_bench.measure_arm.one_run` only records `module_path` and
`threads_resolved`; it never sets `module_sha256` or `module_mtime`. Every rep
therefore contributes `(path, None, None)` to the identity set, and a rebuild
that replaces the `.so` at the same path mid-session still passes — the exact
case WR-07 claims to close. Only `phase10.run_rounds` populates those fields, so
the guard protects the Phase-10 arm but not the Phase-9/python_bench controller
the earlier finding named.

**Fix:** in `one_run`, after validation, add

```python
rep["module_mtime"] = payload["module_mtime"]
rep["module_sha256"] = fingerprint(payload["module_path"])["sha256"]
```

and add a regression test where the fake worker swaps the module bytes at the
same path between reps and `check_rep_identity` raises.

#### WR-04: The committed Python documents pin pre-gate artifacts that are not in the repository

**File:** `.planning/phases/10-benchmark-verdict/10-results-python-k21.json:205-208`, `.planning/phases/10-benchmark-verdict/10-results-python-k31.json:205-208`
**Severity:** WARNING

**Issue:** The consumed slice-gate artifact is pinned to
`/tmp/rustkmer-phase10/scratch/pre_gate_k21.json` (sha `4f958c…`) and
`pre_gate_k31.json` (sha `b9f3d8…`). Neither file is committed, and neither sha
matches the committed `10-slice-gate.json` (`5f1119…`). The WR-05 fix added the
pin and the provenance/fingerprint validation in the code, but the recorded
"consumed artifact sha256" still cannot be verified from a clean checkout;
`10-04-SUMMARY.md:232` documents the same limitation. The current code itself
is sound (I verified the committed `10-slice-gate.json` passes
`_load_slice_gate_doc` and its fingerprints match the measured inputs), so this
is an evidence-history defect, not a live-code defect.

**Fix:** commit the per-k pre-gate records if still recoverable; otherwise
record in the report/summary that the historical pre-gate pins are ephemeral
and that a re-run must pass the committed `10-slice-gate.json` (which the stage
accepts). Optionally have `run_python_session` refuse a `--pre-gate` path
outside the repository so the pinned sha is always verifiable.

### Info

#### IN-01: Consumed-evidence stages do not pin the k identity of what they consume

**File:** `scripts/bench/phase10.py:1817-1853` (`preflight_records`), `:2152-2184` (`_load_slice_gate_doc`), `:2284-2380` (`run_python_session`)
**Severity:** INFO

**Issue:** `preflight_records` requires exactly two CLI documents and rejects a
duplicate k, but it does not require the pinned `{21, 31}` pair; `(k=21, k=7)`
is accepted. `_load_slice_gate_doc` always validates only the k=21 gate, so a
k=31 Python session's pre-gate record is never checked against its own k. Both
gaps fail loudly downstream (the render stage now rejects any k set other than
`(21, 31)`), so they cannot flip a verdict, but the trust boundary should carry
the same identity rule the render stage now enforces.

**Fix:** in `preflight_records`, require `set(seen_k) == set(SLICE_GATE_K_VALUES)`;
in `_load_slice_gate_doc`, accept the session's k and require that k's gate to
exist (for k=31: present, positive counts, and the same `slice_recipe`
source sha), rather than silently validating only k=21.

---

_Reviewed: 2026-11-14T03:29:21Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
