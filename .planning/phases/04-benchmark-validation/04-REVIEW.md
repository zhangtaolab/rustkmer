---
phase: 04-benchmark-validation
reviewed: 2026-10-18T07:50:53Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - docs/benchmark-report.md
  - scripts/bench/bench.py
  - scripts/bench/tests/test_compare.py
  - scripts/bench/tests/test_render_report.py
  - tests/merge_bounded_memory_tests.rs
findings:
  critical: 0
  warning: 0
  info: 1
  total: 1
status: issues_found
---

# Phase 04: Code Review Report (incremental re-review, gap-closure round)

**Reviewed:** 2026-10-18T07:50:53Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Incremental re-review of the five files changed since the prior round (base
7d26a2e): 444f660 (CR-02 cfg-gating), 4eeb9d4 (WR-08/IN-08 pinning tests),
78e5eec (WR-08 renderer fix), 764f53f (re-rendered provenance line), and
63f2835 (docs only, no scoped-file change). The prior round's findings are not
carried forward; their triage lives in `04-REVIEW-DISPOSITION.md`.

Every closure claim in this delta was verified against runtime evidence, not
just read:

- **CR-02 (closed, proven on the runner):** the seven Windows-dead measurement
  helpers in `tests/merge_bounded_memory_tests.rs` are now gated
  `#[cfg(not(target_os = "windows"))]` — the `std::sync::atomic`/`Arc` imports
  (:92-95), `CHUNK_ENTRIES` (:106), `KMER_ENTRY_BYTES` (:112), `CHUNK_BYTES`
  (:116), `RSS_BOUND_BYTES` (:132), `MEASUREMENT_ENTRIES` (:144), and
  `run_tracking_peak_rss` (:208); the portable `current_rss_kb` became
  `not(any(linux, windows))` (:186). Exhaustive grep of the file confirms every
  consumer of a gated symbol sits inside the gated measurement test (:373) or
  `run_tracking_peak_rss` itself, and `use std::time::Duration` (:96) is
  correctly left ungated (consumed by ungated tests and both `backdate`
  variants). Proof: CI run 39018676504 (the base) failed exactly on
  `clippy (root) (windows-latest)` — the CR-02 red — while run 39108077664
  (the gap-closure batch push) is green on all six clippy jobs including
  `clippy (root) (windows-latest)`. The scoped files are byte-identical between
  that CI-verified commit (764f53f) and HEAD.
- **WR-08 (closed):** `bench.py:1279-1290` now sources the halt-note figure
  from the first mode=full file via
  `next(d for d in files_data if d["mode"] == "full")` with a guarded
  `fps` list and a named `ValueError` — exactly the prior round's prescribed
  fix. The `next()` without default cannot raise `StopIteration` through the
  public path: `render_report` raises `ValueError` at bench.py:1337-1339 when
  no full file exists, and `_methodology_lines` is called only from there
  (bench.py:1390). The two new pinning tests
  (`test_methodology_figure_empty_fingerprint_raises_named_error`,
  `test_methodology_figure_sourced_from_full_mode_file_not_order`) exercise
  both failure modes — empty and absent fingerprints, and slice-first CLI
  ordering — and the order test's `assertNotIn` is precise enough not to trip
  on the legitimate "(359,504,511 bytes)" fingerprint listing.
- **IN-08 (closed):** the added assertion
  `self.assertIn("wall breach(es) advisory, not gating", out)`
  (test_compare.py:200) matches compare.py:271-274's actual advisory PASS
  summary, closing the gap where the plain all-axes PASS line satisfied the
  bare `GATE: PASS` prefix.
- **Gap 2 (closed, byte-identity proven):** re-rendering from the three
  committed evidence JSONs (`.planning/phases/04-benchmark-validation/
  04-results-full-k31.json`, `-full-k21.json`, `-slice.json`) reproduces
  `docs/benchmark-report.md` byte-for-byte (`diff` clean), and the new
  provenance hash `78e5eec4...` equals
  `git log -1 --format=%H -- scripts/bench/bench.py`. The report's own
  reproducibility claim (T-04-07) therefore holds end-to-end at HEAD,
  including through the WR-08-modified code path.
- Full bench suite: 130 tests, all passing (the 5 in-scope test additions
  included).

No new Critical or Warning defects were found in the delta. One Info-level
observation on the renderer's diagnostic posture is recorded below. The prior
round's open items (WR-01..WR-07, IN-01..IN-07 in the disposition) were not
re-litigated; the factual basis of WR-05 (untracked `Cargo.lock` files) was
not re-checked this round.

## Structural Findings (fallow)

None provided — no structural pre-pass was supplied for this review.

## Narrative Findings (AI reviewer)

## Info

### IN-09: Fingerprint-less results files now pass through the fingerprints section silently

**File:** `scripts/bench/bench.py:1267-1268`
**Issue:** The WR-08 hardening changed the listing loop from
`results["input_fingerprint"]` to `results.get("input_fingerprint") or []`.
Before the delta, a results file with the key absent crashed the renderer with
a (loud) `KeyError`; now it renders cleanly with no fingerprint lines and no
note. The halt-note figure sourcing errors loudly on the same condition — but
only for mode=full files (bench.py:1280-1286). A mode=slice file with an
absent or empty `input_fingerprint` therefore contributes zero fingerprint
evidence to the "Input fingerprints (size + sha256 per file, as recorded)"
section with no diagnostic anywhere, which sits oddly beside the module's
"fails loudly, never best-effort" posture. No wrong number can be emitted (the
section simply lists nothing), and the adjacent `_inputs_differ` behavior is
pre-existing and unchanged, so this is a diagnostic-consistency gap, not a
correctness defect.
**Fix:** Either render an explicit line for fingerprint-less files (e.g.
`- {label}: no input_fingerprint recorded in this results file`) or extend
`validate_schema` to require a non-empty `input_fingerprint` list, so the
loud/silent split between the figure sourcing and the listing disappears.

---

_No structural findings block was provided by the orchestrator; no external
reviewer evidence was supplied._

_Reviewed: 2026-10-18T07:50:53Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
