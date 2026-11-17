---
phase: 11-merge-characterization-harness-prep
plan: 03
subsystem: docs
tags: [documentation, benchmark-report, evidence-hygiene, superseded-banner, drift-sweep, dataset-description, jellyfish]

# Dependency graph
requires:
  - phase: 10-benchmark-verdict (v2.0 milestone)
    provides: the authoritative verdict evidence the banner points to (k=21 CLI 144.69 s vs jellyfish 194.85 s; k=31 CLI 147.08 s; union Distinct 897,266,581 / Total 8,967,099,203) at .planning/milestones/v2.0-phases/10-benchmark-verdict/
provides:
  - docs/benchmark-report.md carrying a superseded banner before any stale content, pointing to the v2.0 Phase-10 verdicts (the single acknowledged exception to the generated-file contract)
  - corrected benchmark dataset description in .planning/PROJECT.md (six single-member gzip parts ~2.79 GB each / ~16.7 GB total; pinned arrangement still part_001 + part_006)
  - 11-HYGIENE-RECORD.md: banner exception + renderer-narrative debt (bench.py halt note / CRR2044018 block, pre- and post-11-01 anchors) + per-file D-06 sweep results + HYG-04 determination
  - HYG-04 determination: WARNING-2 assigned to the Plan 11-07 same-touch; backlog 999.1/999.2/999.3 recorded as not triggered (tracked, non-gate-blocking)
  - zero-drift gate: no unlabeled stale v1.0 verdict cite remains anywhere in the D-06 breadth outside the banner-marked report
affects: [Plan 11-07 (owns the WARNING-2 same-touch fix in scripts/bench/README.md), Plan 11-08 (HYG-02/03 records; HYG-04 flips complete when 11-07 lands), Phase 12 Full-Scale Merge Verdict (stale-v1.0-free context), post-Phase-12 benchmark-report rewrite (renderer-narrative update owner)]

# Actuals (#2632) — pairs with the plan's estimate (25000) to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 5588     # chars/4 over git diff 54a55d8..HEAD at SUMMARY time (22,351 chars)
  tasks: 2
  commits: 2       # MEASURED: git rev-list --count gsd-plan-head-before-11-03..HEAD
plan_head_before: 54a55d800589c90bcc0289777edd4c75602293c7
plan_head_after: 1a9e78b10c956ea6f892fdfb00783f8b8e053203

# Tech tracking
tech-stack:
  added: []       # docs-only plan; no packages, no code (T-11-SC: no installs — N/A confirmed)
  patterns:
    - "Supersede-banner pattern for generated files: hand-added marker precedes all stale content, explicitly acknowledges the generator contract, and records the exception beside the artifact (11-HYGIENE-RECORD.md)"
    - "Drift-sweep gate: grep sweep with a zero-unlabeled-cite acceptance command (matched lines must carry a 'superseded' label or live inside the banner-marked report)"

key-files:
  created:
    - .planning/phases/11-merge-characterization-harness-prep/11-HYGIENE-RECORD.md
  modified:
    - docs/benchmark-report.md
    - .planning/PROJECT.md
    - README.md
    - .planning/phases/11-merge-characterization-harness-prep/deferred-items.md

key-decisions:
  - "Banner carries the corrected dataset description inline (six single-member gzip parts ~2.79 GB each / ~16.7 GB total) so the file's current description block is accurate without touching any rendered v1.0 content below (D-05/truth-1)"
  - "The report's CRR2044018 provenance block needed no correction: it describes the v1.0 run's substitute dataset (historical statement), not the current CRR1936095 split directory — six-part correction belongs to PROJECT.md per D-05"
  - "Renderer narrative (bench.py halt note + CRR2044018 block) deliberately left emitting v1.0 text to protect old-JSON re-render byte-identity; debt recorded with both pre-11-01 anchors (1883-1892/1942-1947) and current post-11-01 anchors (1981-1990/2040-2045); the post-Phase-12 rewrite owns the update (research Open Question 4)"
  - "HYG-04: WARNING-2 assigned to Plan 11-07's same-touch of scripts/bench/README.md; 999.1-999.3 not triggered (no pyo3/build.rs change, no venv work, no edit reaches v1.0-phases/03-memory-safety/deferred-items.md) — stay tracked, not gate-blocking"

patterns-established:
  - "Generated-file exception recording: every hand edit of a generated file names the generator contract, the drop-on-re-render consequence, and the record file — no silent hand edits"
  - "Stale-cite labeling rule: any kept historical verdict mention outside the banner-marked report carries an in-place 'superseded' label citing the superseding evidence"

requirements-completed: [HYG-01, HYG-04]  # HYG-04 shared with Plan 11-07 — REQUIREMENTS.md flips it when 11-07's SUMMARY lands (shared-ID gate)

# Coverage metadata (#1602) — one entry per shipped deliverable.
coverage:
  - id: D1
    description: "docs/benchmark-report.md opens with a SUPERSEDED banner (v1.0/CRR2044018 snapshot) pointing to .planning/milestones/v2.0-phases/10-benchmark-verdict/ with the v2.0 verdict numbers (144.69/147.08 s), acknowledges the generated-file contract, and states all numbers below are historical; rendered tables/footer untouched"
    requirement: HYG-01
    verification:
      - kind: other
        ref: "command: grep -c -i 'superseded' docs/benchmark-report.md (=2); head confirms banner precedes the title and all stale content"
        status: pass
    human_judgment: false
  - id: D2
    description: "Dataset description corrected in .planning/PROJECT.md at the benchmark-dataset paragraph and the Constraints bullet (six single-member gzip parts ~2.79 GB each / ~16.7 GB total; pinned arrangement part_001 + part_006) — zero '5.2 GB' / 'two split parts' remains"
    requirement: HYG-01
    verification:
      - kind: other
        ref: "command: grep -c '5\\.2 GB' .planning/PROJECT.md (=0) && grep -c 'two split parts' .planning/PROJECT.md (=0)"
        status: pass
    human_judgment: false
  - id: D3
    description: "README.md stale '+420.0%' k=21 row superseded-labeled in place (citing v2.0 144.69 s, no table restructure) and the v1.0 conclusion sentence labeled with the v2.0 pointer"
    requirement: HYG-01
    verification:
      - kind: other
        ref: "command: grep -c -i 'superseded' README.md (=2); +420 line carries the superseded label"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-06 sweep leaves zero unlabeled stale cites outside the banner-marked report; per-file results (USER_GUIDE.md and PROJECT_SUMMARY.md clean) recorded in 11-HYGIENE-RECORD.md"
    requirement: HYG-01
    verification:
      - kind: other
        ref: "command: grep -rn -- '+420' docs/ README.md USER_GUIDE.md PROJECT_SUMMARY.md .planning/PROJECT.md | grep -v 'docs/benchmark-report.md' | grep -vi superseded | wc -l (=0)"
        status: pass
    human_judgment: false
  - id: D5
    description: "11-HYGIENE-RECORD.md records the banner as the single acknowledged generated-file exception (re-render drops it), the renderer-narrative debt with current anchors, and the HYG-04 determination (WARNING-2 -> 11-07 same-touch; 999.1-999.3 not triggered, tracked, non-gate-blocking)"
    requirement: HYG-04
    verification:
      - kind: other
        ref: "command: test -f 11-HYGIENE-RECORD.md && grep -q 'not triggered' 11-HYGIENE-RECORD.md; bench.py anchors verified: halt_note literal at :1981-1990, CRR2044018 block at :2040-2045 (grep -n)"
        status: pass
    human_judgment: false

# Metrics
duration: 6min
completed: 2026-11-16
status: complete
---

# Phase 11 Plan 03: Evidence-Hygiene Docs Closure Summary

**Superseded banner + six-part (~16.7 GB) dataset correction on the stale v1.0 benchmark report, a zero-unlabeled-cite D-06 sweep across README/PROJECT.md/docs, and the HYG-04 determination (WARNING-2 to 11-07; 999.1–999.3 not triggered) recorded in 11-HYGIENE-RECORD.md (HYG-01)**

## Performance

- **Duration:** 6 min
- **Started:** 2026-11-16T13:29:53Z
- **Completed:** 2026-11-16T13:36:44Z
- **Tasks:** 2
- **Files modified:** 5 (1 created, 4 modified)

## Accomplishments
- HYG-01 resolved before the Phase 12 verdict exists (roadmap constraint met): `docs/benchmark-report.md` now opens with a SUPERSEDED banner — v1.0 snapshot rendered from the deleted CRR2044018 substitute dataset, superseded by the v2.0 Phase-10 verdicts at `.planning/milestones/v2.0-phases/10-benchmark-verdict/` (k=21 CLI 144.69 s vs jellyfish 194.85 s; k=31 CLI 147.08 s; overall YES) — with the generated-file contract explicitly acknowledged; the banner also carries the corrected dataset description, and no rendered table, verdict line, or footer was touched
- Dataset description corrected in `.planning/PROJECT.md`: the benchmark-dataset paragraph and the Constraints bullet now state six single-member gzip parts (~2.79 GB each, ~16.7 GB total; valid standard gzip) with the pinned benchmark arrangement still part_001 + part_006; zero "5.2 GB" / "two split parts" phrasing remains
- README.md: the stale "+420.0%" k=21 row and the v1.0 conclusion sentence are superseded-labeled in place citing the v2.0 re-measurement — no table restructure
- D-06 sweep clean: zero unlabeled `+420` / stale-dataset cites anywhere in the breadth (`docs/`, README.md, USER_GUIDE.md, PROJECT_SUMMARY.md, `.planning/PROJECT.md`) outside the banner-marked report; USER_GUIDE.md and PROJECT_SUMMARY.md verified clean; historical CRR2044018 mentions in PROJECT.md (:33/:72/:109) checked and left — all explicitly era-labeled v1.0 records
- 11-HYGIENE-RECORD.md created: banner exception (re-render drops it), renderer-narrative debt with pre-11-01 AND current post-11-01 bench.py anchors, per-file sweep results, HYG-04 determination (WARNING-2 assigned to Plan 11-07's same-touch; 999.1/999.2/999.3 not triggered — stay tracked in the ROADMAP backlog, non-gate-blocking)

## Task Commits

Each task was committed atomically:

1. **Task 1: HYG-01 — superseded banner, dataset correction, README superseded label** - `3d7d175` (docs)
2. **Task 2: D-06 drift sweep + 11-HYGIENE-RECORD.md** - `1a9e78b` (docs)

**Plan metadata:** _hash recorded in the completion report (docs commit with SUMMARY + STATE + ROADMAP + REQUIREMENTS)_

## Files Created/Modified
- `docs/benchmark-report.md` - SUPERSEDED banner prepended (the single acknowledged generated-file exception); rendered content untouched
- `.planning/PROJECT.md` - dataset description corrected (benchmark paragraph + Constraints bullet); HYG target bullet and v2.0 paragraph drift fixed in the sweep
- `README.md` - stale k=21 row + v1.0 conclusion sentence superseded-labeled with v2.0 pointers
- `.planning/phases/11-merge-characterization-harness-prep/11-HYGIENE-RECORD.md` - NEW: exception record, renderer-narrative debt, sweep results, HYG-04 determination
- `.planning/phases/11-merge-characterization-harness-prep/deferred-items.md` - appended the out-of-breadth CLAUDE.md discovery

## Decisions Made
- Banner carries the corrected dataset description inline so the file's current description block is accurate without editing any rendered v1.0 content (satisfies the must-have "the file's dataset description is corrected" reading directly)
- The report's CRR2044018 provenance block left verbatim — it makes a historically accurate statement about the v1.0 run's substitute dataset, not about the current CRR1936095 split directory; per Task 1 action, the six-part correction belongs to PROJECT.md
- Renderer narrative deliberately not fixed (research Open Question 4 resolution): byte-identity of old-JSON re-renders outranks the small narrative fix; the debt is recorded with both anchor sets so the post-Phase-12 rewrite finds the strings regardless of further bench.py drift
- PROJECT.md:18 (HYG bullet) and :74 ("both split parts") plus README.md:356 (v1.0 conclusion sentence) were fixed as Task 2 sweep findings — same-class drift, factual fixes only, inside the locked D-06 breadth

## Deviations from Plan

None - plan executed exactly as written. (All sweep fixes beyond the two named PROJECT.md lines are the Task 2 action's own "fix factual drift only where found" operating as designed; every acceptance gate passed.)

## Issues Encountered
- Out-of-scope discovery (logged to `deferred-items.md`, not fixed): `.claude/CLAUDE.md:17` — the auto-generated CLAUDE.md still mirrors the pre-correction constraint line ("~5.2 GB gzipped r1 across split parts"). D-06's locked sweep breadth excludes CLAUDE.md, and the file is generator-produced, so the fix is regeneration rather than a hand edit; the authoritative PROJECT.md line is corrected.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Ready for 11-04 (parity-gate spec doc) — no coupling with this plan's files
- Plan 11-07 must fix WARNING-2 (`scripts/bench/README.md:318-321` stale "requested + 1" pool-size formula) in its same-touch of `scripts/bench/README.md` — assignment recorded in 11-HYGIENE-RECORD.md §4
- HYG-04 requirement stays open in REQUIREMENTS.md until 11-07 lands (shared-ID gate: declared by both 11-03 and 11-07); HYG-01 is marked complete
- Plan 11-08 owns the HYG-02/HYG-03 milestone-archive records (same wave, disjoint files)
- Post-Phase-12 rewrite owns the renderer-narrative update (bench.py halt note + CRR2044018 block) alongside the full v2.0-based report rewrite (D-05 deferred idea)

---
*Phase: 11-merge-characterization-harness-prep*
*Completed: 2026-11-16*

## Self-Check: PASSED

All created files exist on disk (`11-HYGIENE-RECORD.md`, `11-03-SUMMARY.md`); all task commits (`3d7d175`, `1a9e78b`) and the metadata commit (`16be40c`) are ancestors of HEAD; plan_head_after (1a9e78b) matches the last task commit at SUMMARY time; commits measured 2 from the persisted plan ledger (gsd-plan-head-before-11-03). Full plan verification set re-run green at close: banner present (report=2, README=2), zero "5.2 GB"/"two split parts" in PROJECT.md, zero unlabeled "+420" cites outside the banner-marked report, HYGIENE-RECORD.md present with the "not triggered" HYG-04 determination.
