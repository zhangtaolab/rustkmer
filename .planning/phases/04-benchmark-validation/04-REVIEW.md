---
phase: 04-benchmark-validation
reviewed: 2026-10-17T15:36:48Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - .github/workflows/benchmark.yml
  - .github/workflows/ci.yml
  - docs/benchmark-report.md
  - scripts/bench/README.md
  - scripts/bench/baselines/bench_baseline.darwin.json
  - scripts/bench/bench.py
  - scripts/bench/compare.py
  - scripts/bench/tests/test_compare.py
  - src/database/prefix_cache_merge.rs
  - tests/merge_bounded_memory_tests.rs
  - tests/merge_cleanup_tests.rs
findings:
  critical: 1
  warning: 1
  info: 1
  total: 3
status: issues_found
---

# Phase 04: Code Review Report (incremental re-review)

**Reviewed:** 2026-10-17T15:36:48Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Incremental re-review of the 11 files changed since the 2026-10-11 review (base
76076e6): bb5ccb0 (CR-01 renderer fix), 6cffc30 (darwin baseline regen),
375fac5 (`--wall-advisory` CI gate change), 8f23225 (Windows test fixes),
b514331/0c90f4d (windows-latest CI matrices). The prior review's findings are
not carried forward here; they remain tracked in
`04-REVIEW-DISPOSITION.md` (CR-01 fixed; WR-01..WR-07, IN-01..IN-07 open).

What was verified in this pass:

- The `--wall-advisory` implementation in `compare.py` is correct: wall
  breaches under the flag keep their full bookkeeping (table line, breach
  line, threshold) and are demoted to a non-gating `advisory_breaches` list;
  RSS breaches still gate; the FAIL summary correctly names only the RSS axis
  in advisory mode. All 31 comparator tests pass locally (including the 4 new
  `TestWallAdvisory` cases). The change matches the pre-locked README
  contingency ("demote wall to advisory and keep RSS hard — do not widen
  RSS"); the RSS threshold did not move and the baseline was not shaved.
- The regenerated darwin baseline (6cffc30) is schema-valid, carries the
  rustkmer-arms-only shape the gate requires, and its provenance note
  documents the runner-class variance honestly.
- The CR-01 fix (bb5ccb0) removes the `220,028 k-mers` literal from the
  renderer; the figure now derives from the fingerprinted input size, and the
  committed `docs/benchmark-report.md` matches (2,637,234,342 bytes, equal to
  the headline full-run fingerprint).
- The Windows test gating (8f23225) itself works: `test (root)
  (windows-latest)` and `pyo3 clippy + wheel (windows-latest)` passed on the
  real runner (run 39018676504), including the share-lock failure-injection
  variant of `failed_bucket_aborts_the_merge_with_err`.

One BLOCKER stands: commit 8f23225 gated the RSS measurement test off on
Windows but left its helper constants/functions un-gated, and commit b514331
then added windows-latest to the clippy matrix — where `-D warnings` turns
the resulting dead_code lint into errors. **The dev-branch CI merge gate is
red at HEAD right now** (CI run 39018676504, job `clippy (root)
(windows-latest)`: "could not compile `rustkmer` (test
"merge_bounded_memory_tests") due to 7 previous errors"). This is proven,
not hypothesized — see CR-02.

Note for the fixer: the factual basis of prior open finding WR-05 was
re-verified (both `Cargo.lock` and `pyo3/Cargo.lock` remain untracked;
`.gitignore:6,117`), so the degenerate `hashFiles('Cargo.lock')` cache keys in
ci.yml/benchmark.yml still stand as recorded in the disposition; it is not
re-listed as a finding of this pass.

## Structural Findings (fallow)

None provided — no structural pre-pass was supplied for this review.

## Narrative Findings (AI reviewer)

### Critical Issues

### CR-02: Windows clippy gate is red at HEAD — un-gated measurement helpers are dead code under the Windows test gating (CI merge gate failing)

**File:** `tests/merge_bounded_memory_tests.rs:102-136, 161-167, 177-190, 199-219` (gated consumer at `:363-365`); enabled by `.github/workflows/ci.yml:46` (clippy matrix gained `windows-latest`)
**Issue:** Commit 8f23225 added `#[cfg(not(target_os = "windows"))]` to
`streaming_merge_peak_memory_is_bounded_by_chunk_not_dataset` (line 363) but
did not gate the items only that test uses: `CHUNK_ENTRIES` (102),
`KMER_ENTRY_BYTES` (107), `CHUNK_BYTES` (110), `RSS_BOUND_BYTES` (125),
`MEASUREMENT_ENTRIES` (136), `current_rss_kb` (177, the non-Linux variant),
and `run_tracking_peak_rss` (199). On Windows their sole caller is compiled
out, so `cargo clippy --all-targets -- -D warnings` (the clippy-root job,
which b514331/0c90f4d extended to windows-latest) fails with seven
`dead_code` errors. Verified against the actual runner log (run 39018676504,
job `clippy (root) (windows-latest)`):

```text
error: constant `CHUNK_ENTRIES` is never used
error: constant `KMER_ENTRY_BYTES` is never used
error: constant `CHUNK_BYTES` is never used
error: constant `RSS_BOUND_BYTES` is never used
error: constant `MEASUREMENT_ENTRIES` is never used
error: function `current_rss_kb` is never used
error: function `run_tracking_peak_rss` is never used
error: could not compile `rustkmer` (test "merge_bounded_memory_tests") due to 7 previous errors
```

`cargo test` on Windows passes (dead_code is only a warning there), which is
why 8f23225's own CI run looked green — the breakage surfaced only when the
clippy matrix gained the Windows leg. Per ci.yml's own header rule ("any gate
job failing fails the PR"), every subsequent push/PR to dev fails CI until
this is fixed. `cargo clippy` is a mandated command in CLAUDE.md.
**Fix:** Gate the measurement machinery to match its consumer. Minimal,
robust one-liner at the top of `tests/merge_bounded_memory_tests.rs`:

```rust
// Windows has no stdlib RSS source (see the gated test below), so the
// measurement helpers compile dead there.
#![cfg_attr(target_os = "windows", allow(dead_code))]
```

or, more precisely, add `#[cfg(not(target_os = "windows"))]` to the five
constants, the non-Linux `current_rss_kb`, and `run_tracking_peak_rss` (the
Linux `current_rss_kb` is already Linux-gated; if the non-Linux variant is
gated to not-Windows instead, also gate or inline the
`std::sync::atomic`/`Arc` imports that only `run_tracking_peak_rss` uses).
Then confirm by cross-compiling the test target before push:
`cargo clippy --all-targets --target x86_64-pc-windows-msvc` (or push and
watch the windows clippy leg go green).

## Warnings

### WR-08: CR-01's replacement figure indexes `input_fingerprint[0]` unguarded — and can silently take the number from the wrong results file

**File:** `scripts/bench/bench.py:1275` (new in this delta, from bb5ccb0)
**Issue:** Two defects in the fix for the prior CR-01:

1. `fp0 = first["input_fingerprint"][0]` assumes the first results file
   carries at least one fingerprint. `validate_schema` (bench.py:279-309)
   never checks `input_fingerprint` — it may be `[]` or absent on a file that
   passes schema validation and the mode=full/slice check in `render_report`
   (bench.py:1319-1327). Such a file now crashes the renderer with a bare
   `IndexError`/`KeyError` that the `__main__` catch-all reports as
   `bench.py: list index out of range` — failing loudly, but violating the
   file's own diagnostic standard (every other failure names the file and the
   problem, e.g. "render needs at least one mode=full results file"), and
   contradicting the module's "fails loudly, never best-effort" posture with
   an unattributable message. (The pre-existing `first['platform']` /
   `first['params']['rustkmer']` accesses at :1274/:1297 share the gap but
   predate this delta; `fp0` is new.)
2. `first = files_data[0]` is the first file *as given on the command line*,
   which may be a mode=slice file (`--results slice.json full.json` is a
   legal invocation — the renderer's own doc says full files render "in the
   order given"). The halt note narrates the attempt-1 **full** run, but its
   byte figure would then be the slice run's input size — a sourced-looking
   number attached to the wrong run. The committed report happens to list the
   full file first, so the committed output is correct; the ordering
   sensitivity is latent.

**Fix:** Derive the figure from the first **full-mode** file and guard the
access with a named error:

```python
full0 = next(d for d in files_data if d["mode"] == "full")
fps = full0.get("input_fingerprint") or []
if not fps:
    raise ValueError(
        f"render needs a non-empty input_fingerprint on the mode=full results "
        f"file (created {full0.get('created')}) to source the methodology "
        f"note's input-size figure")
fp0 = fps[0]
```

and use `full0` for the halt note (the provenance lines may keep
`files_data[0]`).

## Info

### IN-08: The advisory-mode PASS summary line is not pinned by any test

**File:** `scripts/bench/tests/test_compare.py:190-236` (`TestWallAdvisory`)
**Issue:** `compare.py:271-274` prints a distinct advisory summary —
`GATE: PASS — within RSS thresholds (15%); N wall breach(es) advisory, not
gating` — but `test_wall_breach_above_threshold_exits_0_and_is_flagged`
asserts only the prefix `GATE: PASS`, which the plain all-axes PASS line
(:276) also matches. A regression that swapped the advisory summary for the
plain line (falsely claiming "every arm within thresholds on both axes" while
wall breaches exist) would not be caught.
**Fix:** Add `self.assertIn("wall breach(es) advisory, not gating", out)` to
the exit-0 advisory test.

---

_No structural findings block was provided by the orchestrator; no external
reviewer evidence was supplied._

_Reviewed: 2026-10-17T15:36:48Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
