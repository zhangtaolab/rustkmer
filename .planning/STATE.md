---
gsd_state_version: "1.0"
milestone: v2.1
status: Awaiting next milestone
stopped_at: "v2.1 milestone closed and archived 2026-11-18; next: /gsd-new-milestone"
last_updated: "2026-11-18T00:33:16.809Z"
last_activity: 2026-11-18
last_activity_desc: Milestone v2.1 completed and archived
state_head: 2bcfc9bbfe50df1e2d0276c0bb10b5495c87f090
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 15
  completed_plans: 15
  percent: 75
milestone_name: Merge Verdict & Producer Research
current_phase: 14
current_phase_name: Parallel Extraction
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-11-18)

**Core value:** Count, query, and merge k-mers at genome scale within practical memory — fast and lean enough to compete with best-in-class tools (KMC / Jellyfish class), from both the CLI and Python.
**Current focus:** Planning the next milestone — v2.1 shipped 2026-11-18 (merge verdict NO-INVEST; producer attribution D3 NO-GO; Phase 14 NOT EXECUTED)

## Current Position

Phase: Milestone v2.1 complete
Plan: —
Status: Awaiting next milestone
Last activity: 2026-11-18 - Completed quick task 261118-bhr: Apply verify-work audit fixes (verify_threads zero-thread race, coverage schemas, deferred items, WINDOWS 26/27)

## Performance Metrics

**Velocity (v2.0):** 29 plans / 6 phases over 2026-11-12 → 2026-11-14; v1.0: 31 plans / 4 phases (per-plan metrics archived in `milestones/v1.0-phases/`). Post-v1.0 hygiene wave: 10 quick tasks (records in `.planning/quick/`).

**By Phase (v2.1):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 11. Merge Characterization & Harness Prep | 8/8 | 8 | ~29 min |
| 12. Full-Scale Merge Verdict | 4/4 | 4 | ~1h 51min |
| 13. Producer Attribution Research | 3/3 | 3 | ~52 min |
| 14. Parallel Extraction (conditional — D3) | NOT EXECUTED | — | — |

**Recent Trend:**
- v2.1 executable scope complete at Phase 13; v2.0 baseline ~31 min/plan (see `milestones/v2.0-ROADMAP.md`)

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 11 P01 | 18min | 3 tasks | 5 files |
| Phase 11 P02 | 17min | 2 tasks | 2 files |
| Phase 11 P03 | 6min | 2 tasks | 5 files |
| Phase 11 P08 | 10min | 2 tasks | 6 files |
| Phase 11 P04 | 15 min | 3 tasks | 3 files |
| Phase 11 P05 | 63min | 3 tasks | 1 files |
| Phase 11 P06 | 80min | 3 tasks | 2 files |
| Phase 11 P07 | 24min | 3 tasks | 5 files |
| Phase 12 P01 | 22 min | 1 tasks | 2 files |
| Phase 12 P04 | 45 min | 2 tasks | 2 files |
| Phase 12 P02 | 6h 47min | 3 tasks | 10 files |
| Phase 12 P03 | 12min | 2 tasks | 2 files |
| Phase 13 P01 | 14 min | 3 tasks | 4 files |
| Phase 13 P02 | 2h 19min | 2 tasks | 1 files |
| Phase 13 P03 | 4min | 2 tasks | 7 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table. Recent decisions affecting current work:

- [v2.1 shipped 2026-11-18]: merge verdict NO-INVEST (rustkmer merge beats jellyfish merge at both k: 63.34/82.86 s vs 88.44/114.70 s); producer attribution D3 NO-GO → Phase 14 NOT EXECUTED (PEXT-03/04 unexecuted by recorded decision); hygiene debt closed; no performance change landed (MEM guardrail holds by status quo)
- [v2.1 reusable patterns]: pre-registered decision bar → measure → record NO honestly; parity-before-timing; staged controllers with injectable seams; mechanical byte-identical rendering; evidence before multi-GiB input deletion — full detail in PROJECT.md Key Decisions and `milestones/v2.1-phases/`
- [v2.0 D3, 2026-11-14]: Phase 11 (Minimizer Partitioning) did not execute — Stage A hit parity and memory was below jellyfish; MINIM-01..03 permanently descoped 2026-11-16
- [Next milestone]: requirements defined fresh via /gsd-new-milestone; v2.2+ candidates tracked in ROADMAP.md Backlog (MBF-01 only on INVEST — not triggered; MBF-02; PEXT-05)

### Pending Todos

None yet.

### Blockers/Concerns

- [Environment, OPEN] `scripts/bench/tests/test_verify_threads.py::TestNegativeControls::test_pre_engine_n_plus_one_stub_is_measured_red` is a pre-existing ~50% macOS `sample`-race flake. A shared `target/` across git worktrees can bake a deleted `CARGO_MANIFEST_DIR` into test binaries — purge stale artifacts before trusting a red result.
- [Carried, OPEN] IN-06/07/09 (Phase-04 review findings) deferred per triage 261111-spz; backlog 999.1-999.3 remain tracked in ROADMAP.md Backlog (opportunistic, not gate-blocking).
- [Phase 9, OPEN] 8 Info findings in `09-REVIEW.md` (info only).
- [Carried W1, RESOLVED 2026-11-18] pushed dev (through f4e2dc9) and tag v2.1 to origin — remote CI now sees every local commit.
- [v2.1 close, acknowledged] Deferred-item acknowledgments recorded in the Deferred Items table below — the macOS flake and the auto-generated `.claude/CLAUDE.md` dataset-line drift remain the two live carry-forwards.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 261118-bhr | Apply verify-work audit fixes: fix verify_threads zero-thread race and add unit test; correct 11-05 and 06-03 SUMMARY coverage schemas; sync .claude/CLAUDE.md dataset line; correct 11-PREPARE-RECORD free-space figure; mark 06/08 deferred items resolved; close WINDOWS ledger entries 26 and 27 | 2026-11-18 | 2bcfc9b | [261118-bhr-apply-verify-work-audit-fixes-fix-verify](./quick/261118-bhr-apply-verify-work-audit-fixes-fix-verify/) |

## Deferred Items

Items acknowledged and carried forward, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| quick_tasks | 261116-lhq (AtomicU64::fetch_update deprecation suppressed at src/hash/table.rs; work committed 3655086, all gates green) | Acknowledged (scanner status unknown; work complete) | 2026-11-18 | v2.1 |
| deferred_items | 11/deferred-items.md: Pre-existing flake — test_verify_threads.py TestNegativeControls pre_engine_n_plus_one stub (~50% macOS sample-race) | acknowledged | 2026-11-18 | v2.1 |
| deferred_items | 11/deferred-items.md: Docs drift — .claude/CLAUDE.md:17 mirrors pre-correction "~5.2 GB" dataset line (auto-generated; fix = regeneration) | acknowledged | 2026-11-18 | v2.1 |
| Review findings | IN-06/07/09 (Phase-04 harness/test code) | Deferred (triaged 261111-spz) | 2026-11-11 | — |
| Backlog | 999.1 pyo3 build.rs link args; 999.2 stale site-packages shadowing; 999.3 stale sweep claim | Opportunistic in v2.1 (HYG-04, Phase 11) | 2026-10-09 | — |
| Review findings | 8 Info findings in `09-REVIEW.md` (Phase 9) | Info-only, tracked | 2026-11-14 | — |
| Descoped | MINIM-01..03; KMC3 comparison (BENCH-V2-01) | Permanently descoped (user decision) | 2026-11-16 | — |
| Deferred to v2.2+ | MBF-01 (merge flag sweep, post-INVEST); MBF-02 (N-way/r1+r2); PEXT-05 (extractor refinements) | Post-verdict follow-ons | 2026-11-16 | — |

## Session Continuity

Last session: 2026-11-18
Stopped at: v2.1 milestone closed and archived 2026-11-18
Resume file: None

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
