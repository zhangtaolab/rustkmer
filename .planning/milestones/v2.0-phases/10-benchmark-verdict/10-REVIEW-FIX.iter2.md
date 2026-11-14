---
phase: 10
fixed_at: 2026-11-14T03:18:46Z
review_path: .planning/phases/10-benchmark-verdict/10-REVIEW.md
iteration: 1
findings_in_scope: 16
fixed: 16
skipped: 0
status: all_fixed
---

# Phase 10: Code Review Fix Report

**Fixed at:** 2026-11-14T03:18:46Z
**Source review:** `.planning/phases/10-benchmark-verdict/10-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 16 (CR-01..CR-04, WR-01..WR-12; Info findings excluded per the pass scope)
- Fixed: 16
- Skipped: 0

## Verification

All gates ran in the isolated review-fix worktree
`/Users/forrest/GitHub/rustkmer/.claude/worktrees/rf-10-87153-1794625091`
(branch `gsd-reviewfix/10-87153`), with `target/release/rustkmer` symlinked to
the main checkout's existing release binary so the two real-run tests in
`test_schema.py` could execute. The harness gates themselves are independent
of worktree state.

- `python3 -m unittest discover -s scripts/bench/tests -t .` — **557 tests, OK,
  1 skipped**. (Baseline before fixes: 510 tests, OK, 1 skipped, once the same
  binary symlink was in place.)
- One full-suite run hit the pre-existing `test_engine_n_plus_one` sampling
  race (`observed=0`); the affected test passed on three consecutive isolated
  reruns, as documented in the pass instructions.
- `python3 -c "import ast; ast.parse(...)"` after every edit (Tier 2 syntax
  gate), plus targeted module runs per finding.
- No Rust files were touched; `cargo test --locked` was therefore not run.
- Committed evidence re-render check: the render stage over the four committed
  result documents exits 0 and is byte-identical across two runs. Compared
  with the committed `10-BENCHMARK-REPORT.md`, the only differences are the
  three intended disclosures (WR-01 caveat lines, WR-06 methodology sentence,
  WR-03 Python parity-reference line); **no measured number and no verdict
  changed**. No committed result artifact was modified.
- `git status` in the worktree is clean after the fixes; each finding is its
  own commit.

## Fixed Issues

### CR-01: Render publishes an overall verdict over a subset of the pinned k values

**Files modified:** `scripts/bench/phase10.py`, `scripts/bench/tests/test_phase10_verdict.py`
**Commit:** `0f19282`
**Status:** fixed: requires human verification
**Applied fix:** `_render_groups(allow_synthetic=False)` now requires
`set(pairs) == set(SLICE_GATE_K_VALUES)` (exactly one cli + one python document
per k). `run_render` therefore exits 2 with no artifact for a subset. The
stage tests that enshrined the k=21-only path now pass all four pinned
documents, and a regression test asserts a k=21-only set is invalid.

### CR-02: Non-finite recorded medians are accepted and Infinity yields YES

**Files modified:** `scripts/bench/phase10.py`, `scripts/bench/tests/test_phase10_verdict.py`
**Commit:** `34c508b`
**Status:** fixed: requires human verification
**Applied fix:** `math.isfinite` is now required alongside the positivity
checks in `validate_rep_memory` (including `peak_footprint_bytes`),
`_acceptance_arm`/`validate_arm_medians`, `_report_arm_row`, the scaling arm,
and `surface_result`. Tests load documents containing `Infinity` and `NaN` and
assert exit 2 with no artifact, plus direct guards on the rep/verdict paths.

### CR-03: Verdict trusts recorded medians without checking them against the raw reps

**Files modified:** `scripts/bench/phase10.py`, `scripts/bench/tests/test_phase10_verdict.py`
**Commit:** `c0f0e82`
**Status:** fixed: requires human verification
**Applied fix:** new `validate_arm_medians()` recomputes `wall_s`,
`peak_rss_bytes` and `peak_bytes` from the raw reps with the same reducer that
produced them (`statistics.median` / `rep_peak_bytes`) and requires exact
agreement with the recorded medians. It is used by every acceptance arm, the
t1 scaling arm, and every rendered arm row. The committed documents' medians
all reproduce exactly. Tests cover a median contradicted by the reps, a peak
contradicted by the reps, and the committed-evidence render.

### CR-04: Python preflight gate can be converted from BLOCKED to PROCEED

**Files modified:** `scripts/bench/phase10.py`, `scripts/bench/tests/test_python_full_arm.py`
**Commit:** `d7172f2`
**Status:** fixed: requires human verification
**Applied fix:** `_load_python_preflight` rejects a record whose
`budget_bytes != MEMORY_BUDGET_BYTES` and re-derives the gate with the module
constant. `_check_preflight_matches_cli` cross-checks
`preflight["distinct"]` against the consumed CLI document's `rk-t16`
`unique_kmers` and `distinct_source_sha256` against `file_sha256(args.cli_doc)`.
Tests cover a substituted budget, a preflight from a different CLI document,
and a tampered source sha.

### WR-01: Cross-session jellyfish assertion ignores a 7.4x timing divergence

**Files modified:** `scripts/bench/phase10.py`, `scripts/bench/tests/test_phase10_verdict.py`
**Commit:** `c06df62`
**Status:** fixed: requires human verification
**Applied fix:** `_verdict_lines` now renders, per k, both reference medians
side by side with their ratio. When the ratio exceeds the documented
`CROSS_SESSION_JELLYFISH_MAX_RATIO = 2.0`, the report states the divergence and
declines any cross-session timing claim; otherwise it states the agreement.
The verdict rule is untouched. On committed evidence, k=21 renders 1.02x
(within factor) and k=31 renders 7.38x with the caveat.

### WR-02: Recorded warmup order names tools that never ran in the session

**Files modified:** `scripts/bench/phase10.py`, `scripts/bench/tests/test_phase10_verdict.py`, `scripts/bench/tests/test_python_full_arm.py`
**Commit:** `f992b48`
**Status:** fixed
**Applied fix:** new `tool_warmup_order(specs)` derives the unique tool
sequence from the specs; `run_rounds`, `_stage_schedule`, and `run_synthetic`
all use it. Tests assert the CLI session records `["rustkmer", "jellyfish"]`
and the Python session `["jellyfish", "pyrustkmer"]`.

### WR-03: Report provenance is positional; a Python-first document list mislabels the interpreter as the CLI binary

**Files modified:** `scripts/bench/phase10.py`, `scripts/bench/tests/test_phase10_verdict.py`
**Commit:** `6848dcb`
**Status:** fixed: requires human verification
**Applied fix:** `_provenance_lines` selects cli-session documents by
`session == "cli"` (deterministically ordered by k, requiring their measured
binary blocks to agree) and renders the Python session's module/interpreter
provenance plus its `cli_binary` parity reference from python-session
documents. The python test fixture now models the real artifact shape (primary
`binary` = interpreter), and tests pass Python documents first to prove the
labeling.

### WR-04: Render and preflight stages require a local release binary and toolchain

**Files modified:** `scripts/bench/phase10.py`, `scripts/bench/tests/test_phase10_verdict.py`, `scripts/bench/README.md`
**Commit:** `3e198a3`
**Status:** fixed
**Applied fix:** new `_measured_provenance(docs, label)` returns the measured
CLI provenance carried by the source documents (requiring their binary blocks
to agree). `run_render` uses it for the verdict document and
`preflight_records`/`run_preflight_python` return and record it, so neither
stage calls `binary_provenance` or needs `git`/`rustc`. Tests run both stages
with a nonexistent `--rustkmer`.

### WR-05: Python artifact does not pin the preflight sha, and consumed evidence docs are not validated

**Files modified:** `scripts/bench/phase10.py`, `scripts/bench/tests/test_python_full_arm.py`, `scripts/bench/README.md`
**Commit:** `3be742b`
**Status:** fixed: requires human verification
**Applied fix:** `_load_slice_gate_doc` and `_load_python_preflight` now call
`validate_provenance`. `_load_python_preflight` parses and hashes the bytes
once and returns `(record, sha256)`; the Python document records
`preflight: {path, sha256}`. `run_python_session` compares the gate's
`input_fingerprint` with the current inputs before measuring. Test fixtures
carry real provenance and fingerprints; new tests cover missing provenance on
either artifact and a gate measured on different inputs.

### WR-06: Only the Python arm validates per-rep counts

**Files modified:** `scripts/bench/phase10.py`, `scripts/bench/tests/test_phase10_verdict.py`
**Commit:** `ac8094d`
**Status:** fixed: requires human verification
**Applied fix:** `read_rep_counts(spec)` reads `stats`/`jellyfish_stats` from
that rep's own output immediately after each measured CLI/jellyfish run
(injectable via the new `counts_fn` seam; warmups skip it). `build_arms` now
rejects disagreeing per-rep counts and a final artifact whose counts differ
from the last measured rep. The methodology line states that these parity
reads are outside every measured wall.

### WR-07: Rep module identity is compared by path only, not by measured bytes

**Files modified:** `scripts/bench/python_bench.py`, `scripts/bench/tests/test_python_bench.py`
**Commit:** `a779760`
**Status:** fixed: requires human verification
**Applied fix:** `check_rep_identity` now compares the
`(module_path, module_sha256, module_mtime)` identity across reps; any
disagreement is a hard failure. Tests cover same-path/different-sha and
different-mtime rebuilds.

### WR-08: `threads_resolved` is the requested value, not an observed pool size

**Files modified:** `scripts/bench/python_bench.py`, `scripts/bench/tests/test_python_bench.py`, `scripts/bench/tests/test_python_full_arm.py`, `scripts/bench/tests/test_phase10_verdict.py`, `scripts/bench/README.md`
**Commit:** `3b518b1`
**Status:** fixed: requires human verification
**Applied fix (harness scope):** new `pin_rayon_num_threads(threads)` sets
`RAYON_NUM_THREADS` before the binding is imported (and removes an inherited
pin for the all-cores default); the worker records it as
`rayon_num_threads_env`, and `validate_worker_stats` requires it to equal the
arm's requested size. This closes the fallback path the finding describes: if
the binding's explicit `build_global` fails, rayon's lazy default pool now
uses the requested size instead of all cores. The docstrings and README now
state that `threads_resolved` is the binding's resolved CONFIGURATION, not an
independent OS-level observation.
**Remaining limitation:** the Rust-side independent observation
(`rayon::current_num_threads()` / failing on `build_global` Err in
`pyo3/src/counter.rs`) was not implemented because this pass is scoped to the
harness and its tests. A human should decide whether to add it in a follow-up.

### WR-09: Python memory projection is not the "conservative upper bound" it claims to be

**Files modified:** `scripts/bench/phase10.py`, `scripts/bench/tests/test_phase10_verdict.py`
**Commit:** `b17b6e8`
**Status:** fixed: requires human verification
**Applied fix:** `python_projection_bytes` now returns
`ceil(PYTHON_TWO_CALL_BYTES_PER_DISTINCT * d_union)` with the new constant
`86.5`, which is a true upper bound of the stated `33*D_part + 53.5*D_union`
model. `PYTHON_BYTES_PER_DISTINCT = 86` is retained as the measured
single-call coefficient; the preflight model string is updated to
`python-86.5B-per-distinct-conservative-two-call-upper-bound`. Budget and gate
semantics are unchanged.
**Operational note:** the committed `10-python-preflight.json` carries
86-B-model projections. A re-run of the `python` stage from that committed
record would now fail the stricter re-derivation (the harness model changed);
no committed artifact was modified. All committed decisions remain well under
the budget (k=21 90.83 GB and k=31 103.80 GB vs the 118.11 GB budget).

### WR-10: Full-scale stages do not pin the split-part identity

**Files modified:** `scripts/bench/phase10.py`, `scripts/bench/tests/test_python_full_arm.py`, `scripts/bench/tests/test_phase10_verdict.py`, `scripts/bench/README.md`
**Commit:** `4e993f9`
**Status:** fixed: requires human verification
**Applied fix:** `_resolve_two_parts` now reuses `require_split_parts`
(part_001 then part_006) and verifies part_001's sha256 against
`PINNED_SOURCE_SHA256` (previously dead, now used). `_parity_lines` also
asserts every arm's recorded `inputs` equal the document's input fingerprint
paths. Tests cover wrong part names, different part_001 bytes, and an arm
measured over different inputs. A part_006 sha pin was not added because no
pinned digest for it exists in the repository.

### WR-11: Atomic publish deletes pre-existing artifacts and its cleanup can mask the real failure

**Files modified:** `scripts/bench/phase10.py`, `scripts/bench/tests/test_phase10_verdict.py`, `scripts/bench/README.md`
**Commit:** `647c62a`
**Status:** fixed: requires human verification
**Applied fix:** `publish_atomic` rejects identical/non-regular-file
destinations up front, backs up pre-existing file bytes, restores them on any
failure (via temp + `os.replace`), and removes only destinations it created.
`_unlink_quiet` swallows `OSError`; restore errors never mask the original
exception. `run_render` no longer unlinks destinations on failure. Tests cover
pre-existing preservation on a failed re-render, publish-time restore,
new-destination cleanup, identical destinations, directory destinations, and
`_unlink_quiet` on a directory.

### WR-12: `load_cli_document` accepts a non-CLI session document

**Files modified:** `scripts/bench/phase10.py`, `scripts/bench/tests/test_python_full_arm.py`
**Commit:** `225303a`
**Status:** fixed: requires human verification
**Applied fix:** `load_cli_document` requires `session == "cli"` and
`assert_cross_session_jellyfish` asserts the CLI/Python document sessions are
`cli`/`python`. Tests cover a Python document passed as `--cli-doc` and a
cross-session call with the wrong session labels.

## Scope Notes

- Info findings IN-01..IN-10 were intentionally left untouched (out of scope
  for this pass).
- No locked verdict rule, measured number, committed result document, or CI
  baseline was changed. All fixes are in `scripts/bench/phase10.py`,
  `scripts/bench/python_bench.py`, the harness unit suites, and
  `scripts/bench/README.md`.

---

_Fixed: 2026-11-14T03:18:46Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
