---
phase: 04-benchmark-validation
plan: 04
subsystem: testing
tags: [benchmark, milestone-run, mechanical-report, evidence, BENCH-02, BENCH-03, python-stdlib]

requires:
  - phase: 04-benchmark-validation
    provides: bench.py measurement core + parity gate + interleaved counterbalanced protocol (04-01/04-02), compare.py CI gate (04-03), Task 1 pilot calibration + --merge-input/--skip-merge (3831d8b)
provides:
  - scripts/bench/bench.py --render-report — the only writer of docs/benchmark-report.md numbers; deterministic, zero measurement literals, byte-identical re-render (T-04-07)
  - committed milestone evidence — 04-results-full-k31.json / 04-results-full-k21.json / 04-results-slice.json (3 counterbalanced reps per arm, per-rep cache_state, wall+RSS medians, input fingerprints)
  - docs/benchmark-report.md — the BENCH-02/BENCH-03 milestone report with the verdict computed from recorded medians
affects: [milestone close (BENCH-02 verdict NO at k=21 must be triaged by the user at /gsd-complete-milestone), future re-run of the identical protocol on CRR1936095 via --input]

actuals:
  tokens: 14684   # chars/4 over the realized diff 8102985..8d63b91 (58,738 chars) — plan estimated 30,000
  tasks: 3
  commits: 12     # MEASURED: git rev-list --count 41e7d00..8d63b91 (docs commit follows).
                  # Ledger base predates Task 1 and spans the pre-benchmark interlude: 5 phase-03 CI-fix
                  # commits (ba7f451..437cec6) + the checkpoint pause (e1c7a4f) + the parity fix (8102985).
                  # Plan-04-04-scoped commits: 3831d8b (Task 1), e1c7a4f/8102985 (Task 2 story), f31d0b5/7eb510d/8d63b91 (Task 3).

plan_head_before: 41e7d0042196113abf0c486a16e7a4fb4fe2b1cc
plan_head_after: 8d63b918167303b7255c5d100a6bbc42ee5f171c

tech-stack:
  added: []   # stdlib-only constraint maintained (T-04-SC)
  patterns:
    - "Report as pure function of committed evidence: renderer carries no measurement literals and no clock — byte-identical re-render is the hand-edit detector (T-04-07)"
    - "Harness provenance via `git log -1 -- bench.py` instead of HEAD: the value does not move when unrelated commits land, preserving byte-identity across future re-renders"
    - "Verdict computed conservatively from recorded medians: EVERY rustkmer count arm must beat-or-match jellyfish, in EVERY full-scale table — a single slower arm is an honest NO"

key-files:
  created:
    - scripts/bench/tests/test_render_report.py
    - .planning/phases/04-benchmark-validation/04-results-full-k31.json
    - .planning/phases/04-benchmark-validation/04-results-full-k21.json
    - .planning/phases/04-benchmark-validation/04-results-slice.json
    - docs/benchmark-report.md
  modified:
    - scripts/bench/bench.py

key-decisions:
  - "BENCH-02 verdict rule is conservative and stated in the report itself: rustkmer matches-or-beats iff EVERY rustkmer count-arm median wall <= jellyfish median wall in EVERY full-scale table — k=31 passes (494.19/485.89 s vs 843.02 s), k=21 fails (505.77/494.14 s vs 97.26 s), so the overall verdict is NO and BENCH-02 is left unchecked in REQUIREMENTS.md (a NO is a valid measured outcome per the plan's flagged assumption; never tuned away)"
  - "Parity evidence pairs only same-input arms: the harness gate asserts jellyfish-count-A vs count-A; a merge-input slice run's count-B measures the r2 slice no jellyfish arm saw, so the renderer states 'not a parity claim' instead of mislabeling it MISMATCH (first draft did — caught in review of the rendered output, fixed in 7eb510d)"
  - "Harness provenance line uses the last commit that touched bench.py, not HEAD — HEAD would change on every unrelated commit and break the byte-identical re-render contract"
  - "Merge arm renders n/a in vs-jellyfish delta columns — jellyfish has no merge counterpart in this protocol; a merge-vs-count delta would be semantically void (RSS and wall are still reported beside every arm for BENCH-03)"
  - "Option (b) no-sudo execution recorded honestly: every rep of every arm carries cache_state 'unavailable'; the report states plainly that the cold-cache criterion is PARTIALLY SATISFIED (user-approved 2026-10-10; plan lines 101/111/146 pre-authorize)"
  - "Task 2's attempt-1 parity halt is part of the committed methodology record: the gate caught the single-member GzDecoder truncation before any timing was trusted; fix 8102985 (MultiGzDecoder) is cited in the report's methodology block"

patterns-established:
  - "Re-render determinism requires banning not just measurement literals but also render-time clocks and HEAD-derived provenance — any environment-derived value that can move between renders corrupts the tamper-evidence property it exists to provide"
  - "A mechanical renderer must mirror the measurement harness's own assertion pairing (parity is per-input, not per-arm-name) or it fabricates findings the harness never tripped"

requirements-completed: [BENCH-03]
# BENCH-02 deliberately NOT completed: overall verdict NO (k=21 arm fails by 4-5x), measured on the
# user-approved substitute dataset with cold-cache only partially satisfied. Escalated to the user
# at milestone close; the evidence (report + JSONs) is committed either way.

coverage:
  - id: D1
    description: "Mechanical renderer: --render-report --results <jsons> --out <md> produces the milestone report from committed results JSONs with zero measurement literals; byte-identical on re-render; loud ValueError on missing file / schema violation / one-sided arms / no full-mode file"
    requirement: BENCH-03
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_render_report.py — 19 tests: byte-identity, JSON-edit sensitivity (cherry-pick visibility), verdict truth table incl. equality-matches and cross-k conjunction, substitute/cold-cache/BENCH-03 statements, parity pairing incl. merge-input non-claim, merge conservation, error classes"
        status: pass
      - kind: integration
        ref: "plan Task 3 verify chain, verbatim, twice (after f31d0b5 and after 7eb510d): render -> copy -> re-render -> diff -q clean -> grep -c CRR2044018 = 5 -> grep -qi substitute hit -> RENDER-VERIFIED"
        status: pass
    human_judgment: false
  - id: D2
    description: "Committed evidence: the three milestone results JSONs under .planning/phases/04-benchmark-validation/ (plan-specified names), each validate_schema-clean, 3 reps per arm, per-rep cache_state, medians on wall AND peak RSS, input fingerprint blocks"
    requirement: BENCH-02
    verification:
      - kind: other
        ref: "validate_schema over all three committed copies + spot dump (3 reps/arm, medians both axes, cache_state unavailable x3); sha256 of /Users/forrest/Downloads/CRR2044018/CRR2044018_r1.fq.gz re-verified against the recorded fingerprint 131ca561... (2637234342 bytes) on 2026-10-10 (T-04-08)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The milestone measurement itself (Task 2, option b): k=31 primary and k=21 secondary full-scale counting + slice-scale merge, interleaved counterbalanced 3-rep protocol, parity asserted on every measured input; BENCH-02 verdict computed from recorded medians with peak RSS beside wall for every arm"
    requirement: BENCH-02
    verification:
      - kind: e2e
        ref: "scripts/bench/scratch/full_run.log (exit 0, 22:39-01:53): k=31 rustkmer 494.19/485.89 s @ 55.2/55.3 GiB vs jellyfish 843.02 s @ 84.0 GiB (CV 14.8% cv_warning); k=21 rustkmer 505.77/494.14 s @ 49.3/49.7 GiB vs jellyfish 97.26 s @ 46.8 GiB; slice merge 7.55 s @ 16.94 GiB; parity EQUAL on every same-input pairing"
        status: pass
      - kind: other
        ref: "docs/benchmark-report.md sections: headline k=31 (verdict YES), secondary k=21 (verdict NO), overall BENCH-02 verdict NO, parity evidence, slice+merge with conservation EQUAL, methodology (cache census, CV flags, -s 10G, decompression asymmetry, fingerprints, harness commit, attempt-1 finding 8102985), substitute provenance sentence"
        status: pass
    human_judgment: true
    # human_judgment: the milestone criterion's acceptance (NO verdict on substitute data, cold-cache
    # partial) is the user's call at milestone close — the measurement and its recording are done.

duration: Task 3 ~12 min (2026-10-10T18:00Z-18:12Z); plan wall-clock incl. blocking checkpoint + 3.2 h benchmark run: 2026-10-09 -> 2026-10-11
completed: 2026-10-11
status: complete
---

# Phase 04 Plan 04: Milestone Validation + Report Summary

**Full-scale rustkmer-vs-Jellyfish2 milestone run on CRR2044018 (3 counterbalanced reps, parity-gated, honestly cache-labeled) with its evidence committed and a mechanically rendered report whose BENCH-02 verdict is computed from the recorded medians: NO overall — k=31 YES (41-42% faster, 34% less memory), k=21 NO (jellyfish 5x faster).**

## BENCH-02 Verdict (the headline the milestone must confront)

| table | rustkmer median wall | jellyfish median wall | wall delta | rustkmer RSS | jellyfish RSS | RSS delta | verdict |
|-------|----------------------|-----------------------|------------|--------------|---------------|-----------|---------|
| k=31 (primary) | 494.19 / 485.89 s | 843.02 s (CV 14.8%, cv_warning) | -41.4% / -42.4% | 55.22 / 55.29 GiB | 84.00 GiB | -34.3% / -34.2% | **YES** |
| k=21 (secondary) | 505.77 / 494.14 s | 97.26 s | +420.0% / +408.1% | 49.27 / 49.73 GiB | 46.84 GiB | +5.2% / +6.2% | **NO** |

**Overall: NO** (rule: every rustkmer count-arm median wall <= jellyfish in every full-scale table).
Merge at slice scale: 7.55 s / 16.94 GiB peak RSS, count conservation EQUAL.
This is reported as measured, never tuned away, and is escalated to the user at milestone close
together with the two methodology caveats the report states plainly: dataset is the user-approved
CRR2044018 substitute for CRR1936095, and cold-cache is PARTIALLY SATISFIED (option b, no sudo).

## Performance

- **Task 3 duration:** ~12 min (2026-10-10T18:00:47Z → 18:12Z)
- **Plan wall-clock:** 2026-10-09 (Task 1 pilot) → blocking checkpoint → 2026-10-10 22:39 → 2026-10-11 01:53 benchmark (attempt 2, 3.2 h) → Task 3
- **Tasks:** 3/3 (tracer, blocking-human checkpoint resolved as option b, auto)
- **Files:** 6 (1 modified, 5 created; 1,350 insertions in the Task 3 diff)

## Accomplishments

- **The milestone measurement (BENCH-02 measurement leg, Task 2):** all three runs completed exit 0 on the M4 Max dev host post-fix-8102985, exactly as calibrated in Task 1 (no ad-hoc invocations). Every arm: 3 measured reps (warmup discarded), counterbalanced interleaved rounds, per-rep `cache_state: "unavailable"` (honest option-b recording), medians on both axes. The harness asserted count parity on every measured input — 787,508,352 distinct / 4,448,351,631 total at k=31; 663,276,710 / 4,826,823,600 at k=21; both tools identical.
- **Committed evidence (T-04-08):** the three JSONs copied verbatim from `scripts/bench/scratch/` into the phase directory under the plan's exact names; the recorded r1 fingerprint (sha256 `131ca561…59ce9`, 2,637,234,342 bytes) re-verified against the file on disk at close-out.
- **The mechanical renderer (T-04-07):** `bench.py --render-report --results <jsons> --out docs/benchmark-report.md`. Zero measurement literals, no clock, harness provenance via git-log-of-bench.py so re-renders stay byte-identical. 19 unit tests pin byte-identity, JSON-edit sensitivity (a changed median MUST change the report), the verdict truth table (equality = match; one slower arm = NO; cross-k conjunction), the mandatory substitute/cold-cache/BENCH-03 statements, parity pairing semantics, and loud error classes.
- **The report:** headline k=31 and secondary k=21 tables (median wall + peak RSS + deltas + raw per-rep values beside the medians so cherry-picks are visible), overall BENCH-02 verdict, parity evidence lines paired the way the harness asserts them, slice+merge section with conservation checks, full methodology block (reps/schedule, per-arm cache census, CV values + the k=31 jellyfish cv_warning at 14.8%, jellyfish `-s 10G`, decompression arrangement with the residual pipe asymmetry stated, fingerprints, harness commit, the attempt-1 parity-halt finding naming fix 8102985), and the mandated provenance sentence: CRR2044018 is the user-approved substitute for CRR1936095 (approved 2026-10-09), re-runnable via `--input`.
- **Plan verification green:** render verify chain RENDER-VERIFIED (twice), 124 bench unit tests OK, `cargo clippy --all-targets -- -D warnings` clean, `cargo test` green (237 + integration suites) — no Rust source changed this plan.

## Task Commits

1. **Task 1 (tracer, prior session): pilot parity PASS + --merge-input/--skip-merge + calibration** — `3831d8b` (feat)
2. **Task 2 (checkpoint → option b): benchmark runs** — pause `e1c7a4f` (wip), attempt-1 parity fix `8102985` (fix, MultiGzDecoder); runs themselves produce no commits (evidence committed in Task 3)
3. **Task 3 (auto): renderer** — `f31d0b5` (feat)
4. **Task 3 (auto): renderer precision fix** — `7eb510d` (fix, same-input parity pairing + merge delta n/a)
5. **Task 3 (auto): report + evidence** — `8d63b91` (docs)

**Plan metadata:** committed after this SUMMARY (docs).

## Files Created/Modified

- `scripts/bench/bench.py` — +`--render-report`/`--results`; renderer section (render_report + helpers); module docstring names the renderer surface; measurement paths untouched
- `scripts/bench/tests/test_render_report.py` — 19 stdlib unittests (124 total suite-wide)
- `.planning/phases/04-benchmark-validation/04-results-full-k31.json` / `04-results-full-k21.json` / `04-results-slice.json` — committed evidence (verbatim copies of the validated scratch outputs)
- `docs/benchmark-report.md` — the mechanically rendered milestone report

## Decisions Made

See key-decisions in frontmatter. The load-bearing ones: the conservative verdict rule that makes k=21 an unambiguous NO; parity evidence paired per-input (not per-arm-name) so a merge-input run cannot fabricate a finding; harness provenance from git-log-of-bench.py (not HEAD) to preserve byte-identity; and leaving BENCH-02 unchecked in REQUIREMENTS.md — the honest state for a mixed verdict on substitute data.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Renderer's first draft fabricated a parity MISMATCH for the merge-input run**
- **Found during:** Task 3, review of the rendered report (before the evidence commit)
- **Issue:** `_parity_lines` compared jellyfish-count-A against every rustkmer count arm. In the slice+merge run, count-B measures the r2 slice — different data no jellyfish arm saw — so the report printed `-> MISMATCH`, reading as a methodology finding the run never tripped (the harness gate asserts jellyfish vs count-A only). The merge row also carried vs-jellyfish deltas, comparing merging two DBs against counting one slice.
- **Fix:** parity pairing now mirrors the harness's own assertion; same-input repeats label `EQUAL (same input measured twice)`; differing fingerprints (r1/r2) state plainly "not a parity claim"; merge arm renders n/a in delta columns. +1 unit test pinning both.
- **Files modified:** scripts/bench/bench.py, scripts/bench/tests/test_render_report.py
- **Verification:** 124/124 tests; RENDER-VERIFIED chain re-run on the corrected report
- **Committed in:** 7eb510d

**2. [Rule 3 - Blocker] Orchestrator instruction vs plan action conflict on bench.py**
- **Found during:** Task 3 start
- **Issue:** The dispatch prompt said "Do NOT modify scripts/bench/ source", but the plan's Task 3 action mandates "Add --render-report to bench.py" and its verify chain invokes `bench.py --render-report` — the plan's specified mechanism cannot exist without the addition.
- **Fix:** Resolved in favor of the plan (the dispatch's own required_reading marks the plan "authoritative for exact commands/gates"): an additive-only renderer section; zero changes to measurement/parity/protocol code paths; the full pre-existing suite re-run green to prove no measurement-path regression; documented here.
- **Files modified:** scripts/bench/bench.py (additive only)
- **Committed in:** f31d0b5, 7eb510d

**3. [Recorded - prior tasks] Task 1 deviations (already documented in 04-pilot-calibration.md §9)** — calibration ran `--reps 2` (protocol engages both tools only at reps >= 2); `--skip-merge` added to the two full-run commands (the plan's must_haves place merge at slice scale; full-scale merge would add hundreds of GB I/O and hours); full-input size measured, not assumed. Task 2 ran option (b) (no sudo) per the user's checkpoint resolution — every rep records cache_state "unavailable" and the report states the cold-cache criterion is partially satisfied.

---

**Total deviations:** 2 auto-fixed in Task 3 (Rule 1, Rule 3) + 3 recorded from Tasks 1-2
**Impact on plan:** The renderer fix was caught before any evidence was committed; the bench.py conflict resolution kept the measurement surface byte-identical (all 104 pre-existing tests green).

## Issues Encountered

- **k=21 jellyfish speed anomaly (observation, not a defect):** jellyfish's k=21 median wall (97.26 s, CV 4.9%) is 8.7x faster than its own k=31 run (843.02 s, CV 14.8%, cv_warning) on near-identical input volume, while rustkmer's wall is k-independent (~486-506 s). The recorded data cannot explain the swing (plausible contributors: jellyfish's storage-matrix layout at k<=25 packing more k-mers per mem block, plus the k=31 run's high rep-to-rep variance). Recorded as-is with the CV disclosure; no re-run was attempted (the plan forbids tuning outcomes). Worth a targeted follow-up experiment if k=21 performance matters to the user.
- **k=31 jellyfish cv_warning (14.8%):** reps 843.02/657.82/875.18 s — flagged in the report's methodology block per protocol; the median is stated with the warning beside it.

## Authentication Gates

None — the sudo cold-cache gate was avoided entirely by the user's option-(b) resolution (checkpoint Task 2); its absence is recorded honestly in every rep's cache_state and in the report.

## User Setup Required

None. (Maintainers: re-render via the command in the report footer; re-run the whole protocol on CRR1936095 with `--input` when that dataset returns.)

## Next Phase Readiness

- Phase 04 execution complete pending verification; the plan's `<output>` (this SUMMARY) is the last wave-4 artifact.
- **BENCH-02 escalation for milestone close:** verdict NO (k=21), substitute dataset, cold-cache partial — the user decides at `/gsd-complete-milestone v1.0` whether v1.0 ships on the k=31 result with k=21 documented, or a k=21 performance investigation is planned first.
- BENCH-03 satisfied: peak RSS beside wall for every arm in every table.
- Harness, tests, CI gate, baselines all green at 8d63b91; scratch DB artifacts (~4.9 GB) remain under `scripts/bench/scratch/` (gitignored) for inspection.

## Self-Check: PASSED

All key-files exist on disk; all task commits (3831d8b, f31d0b5, 7eb510d, 8d63b91) are ancestors of HEAD; ledger-measured commit count 12 (base 41e7d00 -> 8d63b91, docs commit follows); RENDER-VERIFIED chain green post-fix (diff -q clean, grep -c CRR2044018 = 5, grep -qi substitute hit); 124/124 bench tests, clippy -D warnings clean, cargo test green; input fingerprint re-verified against disk.

---
*Phase: 04-benchmark-validation*
*Completed: 2026-10-11*
