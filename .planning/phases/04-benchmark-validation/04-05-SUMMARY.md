---
phase: 04-benchmark-validation
plan: 05
subsystem: testing
tags: [ci, clippy, cfg-gating, windows, benchmark-harness, provenance, byte-identity, tdd]

requires:
  - phase: 04-benchmark-validation (plans 01-04)
    provides: the benchmark harness (bench.py/compare.py), committed 04-results-*.json evidence, docs/benchmark-report.md, and the ci.yml matrix whose windows-latest clippy leg this plan repairs
provides:
  - Green dev-branch CI merge gate on every platform including clippy (root) (windows-latest) — CR-02 closed
  - Byte-identical tamper-evident docs/benchmark-report.md (provenance line names the bench.py commit; fresh render diffs empty) — gap 2 closed
  - Hardened render_report: named ValueError on empty/absent input_fingerprint, methodology figure sourced from the first mode=full file regardless of --results order (WR-08)
  - Test-pinned advisory-mode PASS summary in compare.py output (IN-08)
affects: [milestone-close (gsd-complete-milestone), any future bench.py change (re-render + separate-commit discipline), phase verification re-run]

actuals:
  tokens: 2628      # chars/4 over the realized diff (10,513 chars)
  tasks: 3
  commits: 4        # MEASURED: git rev-list --count 1c41c40..HEAD
plan_head_before: 1c41c408191cf9d812b062c16db7112a18f74874
plan_head_after: 764f53f2589a7f30414c4f53bfffb3b0b88e6672

tech-stack:
  added: []
  patterns:
    - "Helper-and-consumer platform gating: cfg-test-exclusive measurement helpers carry the same #[cfg] as their only consumer, so dead_code is impossible by construction rather than silenced"
    - "Provenance commit discipline: a bench.py change and its re-rendered report NEVER ride in one commit; the report commit is docs/benchmark-report.md and nothing else"

key-files:
  created: []
  modified:
    - tests/merge_bounded_memory_tests.rs
    - scripts/bench/bench.py
    - scripts/bench/tests/test_render_report.py
    - scripts/bench/tests/test_compare.py
    - docs/benchmark-report.md

key-decisions:
  - "Per-item cfg gating (not the file-top cfg_attr allow): 04-REVIEW sanctioned both; per-item keeps -D warnings meaningful for future Windows dead code in this file and matches its existing per-platform style"
  - "Task 2 executed as TDD RED commit then GREEN commit (test 4eeb9d4 -> feat 78e5eec) per the binding tdd.md contract for tdd=true tasks, superseding the plan prose's 'ONE commit' sentence; the invariant that sentence protects (report never bundled with bench.py) is honored strictly — bench.py rode completely alone"
  - "The fingerprint listing loop reads results.get(\"input_fingerprint\") or [] so an ABSENT key reaches the named ValueError instead of a bare KeyError at the listing — the must-have truth names 'empty or absent' and both had to produce the named error"
  - "BENCH-02's measured NO verdict was not touched, re-derived, or re-litigated (prohibition 4) — it stays escalated to /gsd-complete-milestone"

patterns-established:
  - "Same-platform-set gating: exclusive helpers carry their consumer's cfg verbatim (10 not-windows gates + 1 any(linux,windows) gate + untouched linux/windows pair in the file)"
  - "Named-error renderer diagnostics: guarded access raising ValueError that names the field, the mode, and the file's created timestamp"

requirements-completed: [BENCH-01, BENCH-02, BENCH-03]

coverage:
  - id: D1
    description: "CR-02 closed: the seven Windows-dead measurement items in tests/merge_bounded_memory_tests.rs gated to compile on exactly their consumer's platform set"
    requirement: BENCH-01
    verification:
      - kind: command
        ref: "cargo clippy --all-targets -- -D warnings (exit 0) + awk attribute audit + not-any/old-form greps -> CR02-LOCAL-VERIFIED"
        status: pass
      - kind: command
        ref: "cargo test --test merge_bounded_memory_tests -- --test-threads=1 --nocapture -> 6 passed, rss_delta_bytes=1867776 line printed"
        status: pass
      - kind: other
        ref: "gh run view 39108077664 --json jobs -> clippy (root) (windows-latest): success"
        status: pass
    human_judgment: false
  - id: D2
    description: "WR-08 closed: render_report raises a named ValueError on empty/absent input_fingerprint of the first mode=full file, and sources the halt-note figure from that file regardless of --results order"
    requirement: BENCH-02
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_render_report.py#test_methodology_figure_empty_fingerprint_raises_named_error (observed RED: IndexError/KeyError pre-fix)"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_render_report.py#test_methodology_figure_sourced_from_full_mode_file_not_order (observed RED: slice figure attached pre-fix)"
        status: pass
    human_judgment: false
  - id: D3
    description: "IN-08 closed: compare.py's advisory-mode PASS summary ('wall breach(es) advisory, not gating') pinned by an assertIn in the exit-0 wall-breach test"
    requirement: BENCH-01
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_compare.py#test_wall_breach_above_threshold_exits_0_and_is_flagged"
        status: pass
    human_judgment: false
  - id: D4
    description: "Gap 2 closed: docs/benchmark-report.md re-rendered in a report-only commit; diff is exactly the provenance line; fresh render of the committed tree is byte-identical"
    requirement: BENCH-02
    verification:
      - kind: command
        ref: "git diff --numstat docs/benchmark-report.md == 1 1; removed line carries 7eb510d..., added carries 78e5eec... == git log -1 --format=%H -- scripts/bench/bench.py -> RENDER-DIFF-EXACTLY-ONE-LINE"
        status: pass
      - kind: command
        ref: "diff scripts/bench/scratch/report_identity_check.md docs/benchmark-report.md -> identical -> BYTE-IDENTICAL-ON-COMMITTED-TREE"
        status: pass
    human_judgment: false
  - id: D5
    description: "dev pushed (0c90f4d..764f53f) and the full CI matrix green at the pushed SHA — the merge gate no longer fails on Windows clippy"
    requirement: BENCH-01
    verification:
      - kind: other
        ref: "gh run watch 39108077664 --exit-status (rc 0); all 10 jobs success incl. clippy (root) (windows-latest) -> WINDOWS-CLIPPY-LEG-GREEN"
        status: pass
    human_judgment: false
  - id: D6
    description: "Evidence integrity: the three committed 04-results-*.json files byte-for-byte unmodified; no measurement, verdict, or fingerprint line moved"
    requirement: BENCH-02
    verification:
      - kind: command
        ref: "git diff --stat 1c41c40..HEAD -- .planning/phases/04-benchmark-validation/04-results-*.json (empty) + report numstat 1 1"
        status: pass
    human_judgment: false

duration: 16 min
completed: 2026-10-18
status: complete
---

# Phase 04 Plan 05: Verification Gap Closure Summary

**Windows-dead measurement helpers cfg-gated to their consumer (CR-02), benchmark report provenance re-rendered in a report-only commit restoring byte-identity, plus WR-08/IN-08 harness hardening riders — CI fully green at pushed HEAD including clippy (root) (windows-latest)**

## Performance

- **Duration:** 16 min (07:22:55Z – 07:38:43Z; excludes the CI observation window)
- **Started:** 2026-10-18T07:22:55Z
- **Completed:** 2026-10-18T07:47:00Z (incl. CI run 39108077664 watch)
- **Tasks:** 3/3
- **Files modified:** 5

## Accomplishments

- **CR-02 closed by construction and by CI:** all seven Windows-dead measurement items (CHUNK_ENTRIES, KMER_ENTRY_BYTES, CHUNK_BYTES, RSS_BOUND_BYTES, MEASUREMENT_ENTRIES, portable current_rss_kb, run_tracking_peak_rss) plus the atomic/Arc imports they exclusively use now carry `#[cfg(not(target_os = "windows"))]` (portable current_rss_kb: `not(any(linux, windows))`) — helper and consumer compile on exactly the same platform set. File-wide cfg census after the change: 10 not-windows / 1 any-form / 0 old linux-not form. No test deleted, no bound loosened; the darwin measurement still executes (rss_delta_bytes=1867776 against the 19,200,000 bound at n=1,000,000).
- **Gap 2 closed under strict byte-identity:** docs/benchmark-report.md re-rendered from the three committed JSONs in the report's own fingerprint-listing order; `git diff --numstat` is exactly `1 1` (removed: provenance `7eb510dae…`, added: `78e5eec40…` = `git log -1 --format=%H -- scripts/bench/bench.py`); a fresh render of the committed tree is byte-identical (`diff` empty). The report commit (764f53f) contains docs/benchmark-report.md and nothing else.
- **WR-08 closed (both halves):** the methodology figure is sourced from the first mode=full entry with a guarded, named `ValueError` (names input_fingerprint, mode=full, and the file's created timestamp) instead of a bare IndexError; provenance/platform/rustkmer-binary lines keep `files_data[0]`, so zero rendered bytes moved for the committed inputs.
- **IN-08 closed:** `assertIn("wall breach(es) advisory, not gating", out)` added to the exit-0 advisory test — a regression swapping the advisory PASS summary for the plain all-axes line now fails the suite.
- **Authoritative CI proof:** dev pushed (`0c90f4d..764f53f`, 15 commits: 11 accumulated docs + this plan's 4); CI run **39108077664** completed with **all 10 jobs success**, including `clippy (root) (windows-latest)` (the red baseline was run 39018676504 at 0c90f4d). The dev merge gate is green again.

## Task Commits

Each task was committed atomically (Task 2 as a TDD RED→GREEN pair):

1. **Task 1: CR-02 cfg gating** - `444f660` (fix)
2. **Task 2 RED: failing render tests + comparator pin** - `4eeb9d4` (test)
3. **Task 2 GREEN: renderer fix, no report** - `78e5eec` (feat)
4. **Task 3: report re-render, report-only commit** - `764f53f` (docs)

**Plan metadata:** `<this commit>` (docs: complete plan)

## TDD Execution (Task 2, tdd="true")

- **RED** (`4eeb9d4`): both new tests observed failing against the unfixed renderer for the planned reasons — `test_methodology_figure_empty_fingerprint_raises_named_error` errored with `IndexError: list index out of range` at bench.py:1275 (`fp0 = first["input_fingerprint"][0]`; the absent-key variant would KeyError at the listing, :1268); `test_methodology_figure_sourced_from_full_mode_file_not_order` failed on `AssertionError: '2,637,234,342-byte input' not found` with the rendered fixture visibly carrying the slice figure (`359,504,511-byte input`) in the full-run halt note. Semantic assessment: both targets executed and failed on the planned assertions — not import/syntax/zero-test faults. Evidence saved at /tmp/red_evidence_0405.txt during execution.
- **GREEN** (`78e5eec`): minimal fix in `_methodology_lines` — `full0 = next(d for d in files_data if d["mode"] == "full")`, `fps = full0.get("input_fingerprint") or []`, guarded ValueError, `fp0 = fps[0]` for the halt note only. Module 22/22 OK; full harness suite `Ran 130 tests / OK` (128 + 2 new, exactly as planned).
- **REFACTOR:** none needed — the fix landed minimal; no refactor commit.

## Files Created/Modified

- `tests/merge_bounded_memory_tests.rs` - cfg gates on the five constants, run_tracking_peak_rss, the portable current_rss_kb, and the two atomic/Arc imports (11 insertions, 1 replacement)
- `scripts/bench/bench.py` - guarded full-mode fingerprint sourcing in `_methodology_lines` (+14/−2)
- `scripts/bench/tests/test_render_report.py` - new TestMethodologyFigure class with the two WR-08 tests (+78 with test_compare.py)
- `scripts/bench/tests/test_compare.py` - IN-08 assertIn pinning the advisory PASS summary
- `docs/benchmark-report.md` - exactly the provenance line (7eb510d → 78e5eec)

## Decisions Made

- Per-item cfg gating over the file-top `#![cfg_attr(target_os = "windows", allow(dead_code))]` one-liner (both sanctioned by 04-REVIEW CR-02): per-item keeps `-D warnings` meaningful for future Windows dead code and matches the file's existing style (backdate).
- Task 2 shipped as a TDD test→feat commit pair rather than the plan prose's single commit (see Deviations).
- The fingerprint-listing loop tolerates an absent `input_fingerprint` key so the named ValueError is the failure mode for both the empty and absent cases the must-have truth names.
- BENCH-02's measured NO verdict (k=31 YES / k=21 NO / overall NO) was not touched — it remains escalated to `/gsd-complete-milestone` exactly where 04-VERIFICATION placed it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Fingerprint listing loop tolerates an absent input_fingerprint key**
- **Found during:** Task 2 (GREEN implementation)
- **Issue:** The must-have truth requires a named ValueError for an "empty OR ABSENT" input_fingerprint, but the listing loop (`for fp in results["input_fingerprint"]:`) raised a bare KeyError before the planned guard could fire for the absent case.
- **Fix:** `results.get("input_fingerprint") or []` in the listing loop; the named ValueError at the guard is now reachable for both cases. No rendered-byte change for well-formed files (all committed JSONs carry the key).
- **Files modified:** scripts/bench/bench.py
- **Verification:** absent-key variant of test_methodology_figure_empty_fingerprint_raises_named_error passes with the ValueError regex
- **Committed in:** 78e5eec (Task 2 GREEN)

### Plan-prose deviations

**2. [Process - TDD contract] Task 2 split into RED/GREEN commits instead of the plan's "ONE commit"**
- **Found during:** Task 2 (commit boundary)
- **Issue:** The plan's action text says "commit scripts/bench/bench.py + both test files in ONE commit", but the task carries tdd="true" and the dispatch binds the canonical tdd.md commit-scope contract (`test(...)` → `feat(...)` with failing tests at RED) to Task 2.
- **Resolution:** Two commits — `test(04-05)` (both test files, suite intentionally red) then `feat(04-05)` (bench.py alone). The union of files touched is exactly the three files the plan's acceptance criterion names; the invariant the "ONE commit" sentence actually protects (prohibition 2: a bench.py change and its re-rendered report must never ride together) is honored more strictly, since bench.py now rides completely alone. Task 3's precondition explicitly tolerates "HEAD or in recent history".
- **Committed in:** 4eeb9d4 + 78e5eec

---

**Total deviations:** 2 (1 Rule 2 auto-fix, 1 documented process deviation)
**Impact on plan:** Both necessary; neither touched a measurement, verdict, or evidence file. No scope creep.

## Issues Encountered

None — push clean, CI run registration immediate, all gates green first try.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Verification Evidence (plan-level)

- cfg census in tests/merge_bounded_memory_tests.rs: 10 / 1 / 0 (not-windows / any-form / old-form)
- `cargo clippy --all-targets -- -D warnings` exit 0; full `cargo test` green (23 binaries, 0 failures)
- `python3 -m unittest discover -s scripts/bench/tests -t .` → `Ran 130 tests / OK`
- Report: numstat `1 1`, provenance 7eb510d→78e5eec, fresh-render diff empty
- CI run 39108077664 at pushed SHA 764f53f: conclusion **success**, all 10 jobs (incl. clippy (root) (windows-latest), test (root) (windows-latest), pyo3 clippy + wheel x3)
- Evidence JSONs: `git diff 1c41c40..HEAD -- .planning/phases/04-benchmark-validation/04-results-*.json` empty

## Next Phase Readiness

- Phase 04 is now 5/5 plans summarized — ready for phase verification re-run (both gaps the verifier named are closed with their authoritative evidence) and then `/gsd-complete-milestone`, where the BENCH-02 NO-verdict decision (ship v1.0 on k=31 with k=21 documented vs. plan a k=21 investigation) belongs.
- No blockers from this plan. The provenance is stable until bench.py next changes — and then the Task 2/Task 3 commit discipline applies (never bundle).

## Self-Check: PASSED

All 6 key files exist on disk; all 4 task commits (444f660, 4eeb9d4, 78e5eec, 764f53f) are ancestors of HEAD; measured commit count (4) matches `git rev-list --count 1c41c40..HEAD`.

---
*Phase: 04-benchmark-validation*
*Completed: 2026-10-18*
