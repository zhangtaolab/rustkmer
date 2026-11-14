---
phase: 10-benchmark-verdict
reviewed: 2026-11-14T02:53:55Z
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
  critical: 4
  warning: 12
  info: 10
  total: 26
  necessity: 0
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-11-14T02:53:55Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

The Phase-10 controller is thoughtfully staged: one measured arm per tool over
both split parts, explicit per-rep cache/round metadata, provenance-bearing
artifacts, strict Python worker validation, and a mechanical renderer. I ran
the complete `scripts/bench` unittest suite (`python3 -m unittest discover -s
scripts/bench/tests -t .`: 510 tests, OK) and independent probes against the
verdict/preflight paths. The committed result documents are internally
consistent (recorded medians equal the raw-rep medians, counts agree across
arms and sessions, fingerprints match, and the submitted YES arithmetic
recomputes).

The suite passes, but it does not exercise the failure modes below. Four
measurement-integrity blockers let the verdict layer accept malformed or
partial evidence and emit YES: a render over a subset of the pinned k values,
non-finite medians, recorded medians never cross-checked against the raw reps
they accompany, and a Python preflight gate whose decision is re-derived from
the record's own budget rather than the pinned budget. Twelve warnings cover
provenance and methodology gaps, including a 7.4x cross-session jellyfish
timing divergence in the committed k=31 evidence that the cross-session
assertion cannot see, and a recorded warmup order that describes warmups that
never ran.

No necessity findings: every guard I examined sits at a real trust boundary
(committed JSON evidence, measured subprocess output, worker payloads) or is a
documented test seam. I read
`$HOME/.claude/gsd-core/references/necessity-review.md` before classifying.
No project skills are present under `.claude/skills/` or `.agents/skills/`.

## Narrative Findings (AI reviewer)

### Critical Issues

#### CR-01: Render publishes an overall verdict over a subset of the pinned k values

**File:** `scripts/bench/phase10.py:808-844, 1281-1285, 973-993` (test at `scripts/bench/tests/test_phase10_verdict.py:587-588, 744-757`)
**Severity:** BLOCKER

**Issue:** `_render_groups` pairs whatever k values appear in `--docs`, and
`run_render` computes `overall` only from those pairs. Nothing requires the
pinned set `SLICE_GATE_K_VALUES = (21, 31)` (line 140) or that both sessions
are present for every k. Passing only the k=21 CLI/Python documents publishes
`"overall": "YES"` (verified: exit 0, `verdicts` contains only k=21), while
`_verdict_lines` still states "k=21 is the primary acceptance question; k=31
re-verifies the v1.0 matched-hash comparison" (973-993). A NO at k=31 can
therefore be silently omitted by simply not passing its documents — the exact
"turn a NO into a YES" failure this phase exists to prevent. The existing
stage test enshrines the single-k path by using `full_docs(k=21)` only.

**Fix:** in `run_render` (and the milestone path of `render_report_text`),
require `set(pairs) == set(SLICE_GATE_K_VALUES)` and exactly one cli + one
python document per k; reject any subset with exit 2 and no artifact. Add a
test asserting a k=21-only document set is invalid.

#### CR-02: Non-finite recorded medians are accepted and Infinity yields YES

**File:** `scripts/bench/phase10.py:565-570, 573-602 (validation at 596-601), 855-880 (869-874), 549-560`
**Severity:** BLOCKER

**Issue:** The positivity checks use `value <= 0`, which is False for both
`NaN` and `+inf`, so `_acceptance_arm` accepts a non-finite `medians.wall_s`.
Python's `json.load` accepts `Infinity`/`NaN` literals from a committed
document. Verified: setting the jellyfish arms' `medians.wall_s =
float("inf")` passes `_acceptance_arm`, and `verdict_block(...)["result"]`
returns `YES` because `tool <= inf`. A NaN tool median also passes the
validation (it then yields NO, but it is still accepted as a measurement).
The same `<= 0` pattern is in `_report_arm_row` and `validate_rep_memory`.

**Fix:** require `math.isfinite(value)` wherever a measured number is
validated (rep `wall_s`, `peak_*`, and arm medians); reject non-finite JSON
values with exit 2. Add tests that load documents containing `Infinity` and
`NaN`.

#### CR-03: Verdict trusts recorded medians without checking them against the raw reps

**File:** `scripts/bench/phase10.py:592-602, 605-657, 390-399`
**Severity:** BLOCKER

**Issue:** `_acceptance_arm` requires `reps` to be non-empty ("no median may
exist") but then uses `medians.wall_s` verbatim; it never recomputes
`statistics.median([r["wall_s"] for r in reps])` or compares the two. A
stale, partially regenerated, or edited medians block therefore silently
drives the verdict while the document still carries the raw reps that
contradict it. Verified: three reps of 5000.0 with `medians.wall_s = 50.0`
yields `rustkmer_result = YES`. The report renders both columns, so a human
can notice, but the automated verdict cannot.

**Fix:** recompute the median from the reps and require exact equality with
the recorded `medians.wall_s` (or use the recomputed value and require the
recorded one to match); cross-check `peak_bytes`/`peak_rss_bytes` the same
way. Add a tamper test with inconsistent reps/medians.

#### CR-04: Python preflight gate can be converted from BLOCKED to PROCEED

**File:** `scripts/bench/phase10.py:1817-1862 (budget at 1834, gate at 1847-1852), 1865-1946 (loads at 1888-1893)`
**Severity:** BLOCKER

**Issue:** `_load_python_preflight` re-derives the decision using the
record's own `budget_bytes`, which it only checks is positive — not
`MEMORY_BUDGET_BYTES` (114). Verified: an honest BLOCKED record (distinct
2,000,000,000, projected 172,000,000,000) edited to `budget_bytes =
200,000,000,000` and `decision = "PROCEED"` passes `_load_python_preflight`
unchanged. Additionally, `distinct` and `distinct_source_sha256` are never
compared with the CLI document actually consumed by `run_python_session`, so
a preflight computed from a different (smaller) CLI document authorizes a run
whose measured distinct is higher. The stage docstring claims the projection
is re-derived and "a blocked projection cannot be recorded as PROCEED"; in
practice only self-consistency with the record's own fields is checked.

**Fix:** re-derive with the module constant (`memory_gate(projected,
MEMORY_BUDGET_BYTES)`) and reject a record whose `budget_bytes` differs;
cross-check `preflight["distinct"]` against the consumed CLI document's
`rk-t16.unique_kmers` and `preflight["distinct_source_sha256"]` against
`file_sha256(args.cli_doc)` before measuring. Add tests for both tampers.

### Warnings

#### WR-01: Cross-session jellyfish assertion ignores a 7.4x timing divergence

**File:** `scripts/bench/phase10.py:477-501`; evidence: `.planning/phases/10-benchmark-verdict/10-results-full-k31.json` vs `10-results-python-k31.json`
**Severity:** WARNING

**Issue:** `assert_cross_session_jellyfish` proves count and fingerprint
identity, not timing comparability. In the committed evidence the identical
`jf-t16` command over the identical two-part input records median 1380.92 s
in the CLI session and 187.14 s in the Python session at k=31 (7.4x) with
identical counts and ~94.5 GB peaks. The CLI k=31 surface is therefore
evaluated against an outlier reference; the mechanical report's verdict line
("rustkmer YES ... vs jellyfish 1380.92 s") presents it without a caveat.
`10-04-SUMMARY.md` discloses the divergence, but the report does not. The
overall verdict is still YES via the Python session's fair reference, so this
is a measurement-integrity/visibility gap rather than a flipped verdict.

**Fix:** add a cross-session jellyfish median sanity check (e.g., invalid or
explicitly warn when the same command's two session medians differ beyond a
documented factor), or render both reference medians side by side with a note
in `_methodology_lines`.

#### WR-02: Recorded warmup order names tools that never ran in the session

**File:** `scripts/bench/phase10.py:110, 1705-1710, 1406-1440`; committed `schedule` blocks; `10-BENCHMARK-REPORT.md:74`
**Severity:** WARNING

**Issue:** `_stage_schedule` always records `warmup_order = ["rustkmer",
"jellyfish", "pyrustkmer"]`, while the actual warmup loop in `run_rounds`
(317-373) uses only the tools present in the specs. The committed CLI
document (arms `rk-t16`, `rk-t1`, `jf-t16`) therefore claims a `pyrustkmer`
warmup that never ran, and the Python document claims a `rustkmer` warmup.
The rendered report prints the false order. This contradicts the phase's
otherwise honest per-rep metadata (`cache_state`, `round`, `arm_order`).

**Fix:** derive `warmup_order` from the unique `spec["tool"]` sequence (the
same derivation `run_rounds` uses) and record that list; add a test comparing
the document's `warmup_order` to the specs.

#### WR-03: Report provenance is positional; a Python-first document list mislabels the interpreter as the CLI binary

**File:** `scripts/bench/phase10.py:1111-1144 (1113, 1120-1121), 1280, 1305`
**Severity:** WARNING

**Issue:** `_provenance_lines` reads `docs[0]` positionally and labels its
`binary` as "CLI binary". `--docs` order is unrestricted and the report
footer documents one order only. Verified: with the Python document first,
the report prints `CLI binary: /venv/bin/python` with the interpreter's
sha256. (The unused `_SESSION_ORDER` at line 159 suggests session-ordered
selection was intended.)

**Fix:** select the cli-session document by `session == "cli"` from the
validated pairs and use its provenance for the CLI lines; render the Python
session's provenance (including its `cli_binary` field) from the python
document.

#### WR-04: Render and preflight stages require a local release binary and toolchain

**File:** `scripts/bench/phase10.py:1302, 1514`; `scripts/bench/bench.py:345-375`
**Severity:** WARNING

**Issue:** Both `run_render` and `run_preflight_python` call
`binary_provenance(args.rustkmer, "release")`. That function raises unless
the binary exists (bench.py:357-361) and `git`/`rustc` queries succeed, so a
clean checkout without `cargo build --release` cannot mechanically re-render
the committed verdict or regenerate the preflight, even though both stages
otherwise consume only JSON documents. The README's regeneration procedure
does not mention building. The verdict document's `provenance` also
attributes the render-time binary rather than either measured binary (the
measured provenance lives in the source documents).

**Fix:** give these stages a source/renderer provenance (phase10.py commit +
schema, or reuse the source documents' `provenance`), or make the binary
provenance optional; add a test that render succeeds with a nonexistent
`--rustkmer`.

#### WR-05: Python artifact does not pin the preflight sha, and consumed evidence docs are not validated

**File:** `scripts/bench/phase10.py:1910-1924, 1787-1814, 1817-1862`; `scripts/bench/README.md:344`; test fixtures `scripts/bench/tests/test_python_full_arm.py:450-485`
**Severity:** WARNING

**Issue:** The README says the `python` stage consumes the slice-gate
artifact, the Python preflight record, and the CLI document "pinning each
one's sha256". The artifact pins `pre_gate.path/sha256` and
`cross_session.cli_doc_sha256`, but records no preflight path or sha at all
(grep of both committed Python documents finds none); it only copies the
record's fields. Unlike `load_cli_document`, `_load_slice_gate_doc` and
`_load_python_preflight` never call `validate_provenance`, and the slice gate
is never compared with the session's current input fingerprints. The
committed Python documents pin `/tmp/rustkmer-phase10/scratch/pre_gate_k21.json`
(sha `4f958c…`), not the committed `10-slice-gate.json` (sha `5f1119…`;
content identical apart from `created`/`provenance`), so the committed chain
cannot be re-verified from the repository alone. The tests use
provenance-less gate/preflight fixtures, so none of this is exercised.

**Fix:** record `{"path": str(args.preflight), "sha256":
file_sha256(args.preflight)}` in the Python document (and verify it), call
`validate_provenance` on both consumed artifacts, compare the gate's
`input_fingerprint` to the current inputs, and require/normalize a committed
gate path. Add provenance to the test fixtures.

#### WR-06: Only the Python arm validates per-rep counts; a silent zero-count CLI/jellyfish rep can enter the medians

**File:** `scripts/bench/phase10.py:330-364, 504-546 (counts read at 527-529)`
**Severity:** WARNING

**Issue:** For the CLI and jellyfish arms, `one_measured_run` only calls
`measure_fn`; counts are read once per arm from the final output after all
reps. A single rep that exits 0 but silently counts nothing (the Pitfall 1
trap this harness exists to catch) is appended as a valid timing observation;
the next rep overwrites the artifact, so `build_arms` and
`assert_session_parity` see only positive final counts. This violates the
phase's "parity before timing — counts are exact and nonzero before any
median is trusted" claim for the arms competing with the Python surface.

**Fix:** after each measured rep, read `stats`/`jellyfish_stats` on that
rep's output (distinct output paths, or read before the next overwrite) and
require positive, identical counts; invalidate the arm otherwise.

#### WR-07: Rep module identity is compared by path only, not by measured bytes

**File:** `scripts/bench/python_bench.py:289-322 (303-313)`; `scripts/bench/phase10.py:358-359`
**Severity:** WARNING

**Issue:** `check_rep_identity` compares `module_path` strings and
`threads_resolved` across reps, but not the per-rep `module_sha256` that
Phase-10 attaches. A rebuild that replaces the `.so` at the same path
mid-session passes this check; the arm then records one final
`module_sha256`/provenance fingerprint that may not describe every measured
rep. The docstring's "the measured extension changed mid-run" is only true
for path changes.

**Fix:** include `r.get("module_sha256")` (and mtime where present) in the
identity set and fail on any disagreement.

#### WR-08: `threads_resolved` is the requested value, not an observed pool size

**File:** `scripts/bench/python_bench.py:262-272`; `pyo3/src/counter.rs:190-230, 525-539`; `scripts/bench/README.md:219-222`
**Severity:** WARNING

**Issue:** `validate_worker_stats` treats `threads_resolved` as the
binding's observed pool size, but `PyCounter::new` assigns `self.threads =
resolved_threads` (the requested value) before calling `build_global`, and
deliberately swallows a `build_global` error (log-only). If the global pool
was already initialized to another size, or pool construction fails, the
worker still reports 16 and the Phase-10 acceptance check passes while the
measured process ran with a different pool. The README's "a PyCounter that
ignores its threads argument can never produce a PASS" overstates the
guarantee.

**Fix:** report an independent observation (e.g.,
`rayon::current_num_threads()` after the pool is used) as `threads_resolved`,
or fail the worker when `build_global` returns Err and the current pool size
differs; update the validation docstring/README accordingly.

#### WR-09: Python memory projection is not the "conservative upper bound" it claims to be

**File:** `scripts/bench/phase10.py:114-115, 1350-1363`; `scripts/bench/tests/test_phase10_verdict.py:482-485`
**Severity:** WARNING

**Issue:** The docstring derives `33*D_part + 53.5*D_union <= 86.5*D_union`
and then returns `86 * D_union`. Since 86 < 86.5, the projection is not an
upper bound; it under-projects by 0.5 B/distinct (~0.5 GB at 1B distinct),
and the model string calls it "python-86B-per-distinct-conservative-two-call-upper-bound".
The test pins the 86 value. The committed projections have enough headroom
that the decision does not flip, but the stated safety property is false.

**Fix:** return `math.ceil(86.5 * d_union)` (or model the split explicitly),
update the model string and the test; keep the budget and gate semantics
unchanged.

#### WR-10: Full-scale stages do not pin the split-part identity

**File:** `scripts/bench/phase10.py:1681-1689, 1549-1569, 131-132, 945-946`
**Severity:** WARNING

**Issue:** The full-scale CLI/Python stages resolve inputs with
`_resolve_two_parts`, which only requires two `.fq.gz` files; only the slice
gate calls `require_split_parts` (part_001/part_006). `PINNED_SOURCE_SHA256`
is defined but never used, and the parity lines claim "on the same two-part
input" without checking the arms' recorded `inputs`. A `--data-dir` with two
differently named or unrelated files produces a full-scale verdict that the
report still describes as "Both split parts of the CRR1936095 read-1 set".

**Fix:** reuse `require_split_parts` in `_resolve_two_parts`, verify the
part_001 sha against `PINNED_SOURCE_SHA256` (and pin part_006), and/or assert
each arm's `inputs` in `_parity_lines`.

#### WR-11: Atomic publish deletes pre-existing artifacts and its cleanup can mask the real failure

**File:** `scripts/bench/phase10.py:1221-1225, 1228-1254, 1305-1309`
**Severity:** WARNING

**Issue:** `publish_atomic` removes BOTH destinations on any failure
(1250-1253), so a failed re-render deletes a previously published
verdict/report. Verified: an existing `artifact1.md` was deleted when the
second destination failed. `_unlink_quiet` only swallows
`FileNotFoundError`; a destination that is a directory (or an unlink
permission error) raises from the cleanup block and masks the original
exception (verified: the real failure was replaced by a `PermissionError`).
Passing the same path for `--out` and `--verdict-out` also silently leaves
only the second artifact.

**Fix:** record which destinations existed before publishing and preserve
pre-existing content (or back it up); catch `OSError` in `_unlink_quiet`
while preserving the original exception; reject identical destination paths
up front.

#### WR-12: `load_cli_document` accepts a non-CLI session document

**File:** `scripts/bench/phase10.py:1455-1465, 1889-1893, 477-501`
**Severity:** WARNING

**Issue:** `load_cli_document` validates schema, provenance, and
`mode == "full"`, but not `session == "cli"`. A Python-session results
document (which also carries `jf-t16`) can be passed as `--cli-doc`; the
`_doc_k` check passes and `assert_cross_session_jellyfish` compares that
document's jellyfish arm with the new session's, so the "cross-session"
assertion no longer compares a CLI session at all, and the artifact's
`cross_session.cli_doc` names the wrong session.

**Fix:** require `doc.get("session") == "cli"` in `load_cli_document` (or in
`run_python_session`), and have `assert_cross_session_jellyfish` assert the
two documents' sessions are `cli` vs `python`.

### Info

#### IN-01: Dead constants

**File:** `scripts/bench/phase10.py:127-132, 159`
**Severity:** INFO

**Issue:** `PHASE_DIR`, `PINNED_SOURCE_SHA256`, and `_SESSION_ORDER` are
defined but never referenced anywhere in the file.

**Fix:** remove them, or use them (`PINNED_SOURCE_SHA256` in the full-stage
input check per WR-10; `_SESSION_ORDER` in provenance ordering per WR-03).

#### IN-02: Report renders "maturin maturin 1.11.5"

**File:** `scripts/bench/phase10.py:1135-1138`; `scripts/bench/python_bench.py:577-595`; `10-BENCHMARK-REPORT.md:87`
**Severity:** INFO

**Issue:** `_provenance_lines` prefixes `"maturin "` to
`maturin_version()`, which already returns `"maturin 1.11.5"`; the committed
report shows the doubled label.

**Fix:** render `maturin_version()` verbatim (or strip the prefix).

#### IN-03: README exit-2 contract omits the preflight record exception

**File:** `scripts/bench/README.md:348-352`; `scripts/bench/phase10.py:1517-1526`
**Severity:** INFO

**Issue:** The README says exit 2 means "no artifact written", but
`run_preflight_python` intentionally writes the BLOCKED
`10-python-preflight.json` and returns 2. `10-04-PLAN.md:130` documents this
as the single deliberate exception; the README does not mention it.

**Fix:** state the exception in the Phase-10 exit contract.

#### IN-04: Methodology section renders only the first document's rotation

**File:** `scripts/bench/phase10.py:1068-1108`
**Severity:** INFO

**Issue:** `_methodology_lines` reads `docs[0]["schedule"]`; the CLI and
Python sessions have different round orders and arm counts, but only one
session's rotation is printed, without a session label.

**Fix:** render each session's `schedule.rounds` under its k/session heading,
or label the one that is shown.

#### IN-05: TOCTOU between parsing and hashing consumed evidence

**File:** `scripts/bench/phase10.py:1887-1888, 1910-1913, 1925-1928, 1298`
**Severity:** INFO

**Issue:** The gate/CLI documents are parsed first and then hashed by
re-reading the path (`file_sha256`), and `run_render` fingerprints
`args.docs` after loading them. A file modified between parse and hash yields
a pinned sha256 that does not describe the content actually consumed.

**Fix:** read bytes once, hash them, then `json.loads` the same bytes.

#### IN-06: "Last commit touching this renderer" is actually bench.py's last commit

**File:** `scripts/bench/phase10.py:1140-1141`; `scripts/bench/bench.py:1569-1585`
**Severity:** INFO

**Issue:** `_provenance_lines` calls `bench.harness_source_commit()`, which
is bound to `bench.py` via `Path(__file__)`, and labels it as the last commit
touching "this renderer". The committed report shows `d6a5857` (a bench.py
commit) even though `phase10.py` was last touched at `8c25e42`.

**Fix:** add a phase10-local source-commit helper (or change the label to
say "bench.py").

#### IN-07: Assertion evidence blocks are discarded

**File:** `scripts/bench/phase10.py:1771, 1931-1932`
**Severity:** INFO

**Issue:** `assert_session_parity` and `assert_cross_session_jellyfish` return
structured evidence blocks (`{"equal": True, ...}`), but both stage callers
discard them; the artifacts carry the arms, not the assertion result.

**Fix:** persist the returned blocks under the session document (e.g.,
`session_parity`, `cross_session.verification`) so the audit trail records
what was asserted, not only the data it was asserted over.

#### IN-08: Fingerprint sha256 is length-checked but not hex-checked

**File:** `scripts/bench/phase10.py:785-786`
**Severity:** INFO

**Issue:** `_validate_fingerprint` accepts any 64-character string as a
sha256; `validate_provenance` uses the stricter `SHA256_HEX_RE`. A
non-hex value would pass the render path and be printed as a hash.

**Fix:** reuse `SHA256_HEX_RE` from `bench.py`.

#### IN-09: Leading-hyphen paths can be interpreted as options in the one shell arm

**File:** `scripts/bench/bench.py:193, 222-234, 276-279`
**Severity:** INFO

**Issue:** `SAFE_PATH_RE` permits a path beginning with `-`; the gz
pipeline is the only shell string, and a filename such as `-f.fq.gz` in a
scanned data directory is passed to `gzcat` as an option token. The filename
must exist and malformed options fail loudly, but rejecting a leading `-`
(or prefixing `./`) closes the option-injection class.

**Fix:** reject a leading `-` in `validate_path`, or normalize shell-bound
paths with a `./` prefix.

#### IN-10: Synthetic stage writes its document before rendering and lacks an explicit parity assertion

**File:** `scripts/bench/phase10.py:1406-1450`
**Severity:** INFO

**Issue:** `run_synthetic` never calls `assert_session_parity`; a count
mismatch is caught only by `_parity_lines` during `render_report`, after
`write_doc` has already put the results document on disk. The stage then
exits 2 with an artifact, which conflicts with the broad exit-2/no-artifact
contract and reports the failure as a render error rather than a parity
failure.

**Fix:** call `assert_session_parity(doc, *ARM_ORDER)` before `write_doc`
(synthetic arms all count the same two parts), and render before writing or
remove the document on render failure.

---

_Reviewed: 2026-11-14T02:53:55Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
