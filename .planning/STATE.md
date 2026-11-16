---
gsd_state_version: "1.0"
milestone: v2.1
milestone_name: Merge Verdict & Producer Research
current_phase: 11
current_phase_name: Merge Characterization & Harness Prep
status: planning
stopped_at: Phase 11 context gathered
last_updated: "2026-11-16T10:45:43.383Z"
last_activity: 2026-11-16
last_activity_desc: v2.1 roadmap created (Phases 11-14; research complete; 14/14 requirements mapped)
state_head: 54a716cd3de09b293e84abb85f179db1e80b22a2
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-11-16)

**Core value:** Count, query, and merge k-mers at genome scale within practical memory — fast and lean enough to compete with best-in-class tools (KMC / Jellyfish class), from both the CLI and Python.
**Current focus:** Phase 11 — Merge Characterization & Harness Prep

## Current Position

Phase: 11 of 14 (Merge Characterization & Harness Prep)
Plan: — (phase not yet planned)
Status: Ready to plan
Last activity: 2026-11-16 — v2.1 roadmap created (Phases 11-14; research complete; 14/14 requirements mapped)

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity (v2.0):** 29 plans / 6 phases over 2026-11-12 → 2026-11-14; v1.0: 31 plans / 4 phases (per-plan metrics archived in `milestones/v1.0-phases/`). Post-v1.0 hygiene wave: 10 quick tasks (records in `.planning/quick/`).

**By Phase (v2.1 — not started):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 11. Merge Characterization & Harness Prep | 0/TBD | - | - |
| 12. Full-Scale Merge Verdict | 0/TBD | - | - |
| 13. Producer Attribution Research | 0/TBD | - | - |
| 14. Parallel Extraction (conditional — D3) | 0/TBD | - | - |

**Recent Trend:**
- v2.1 not started; v2.0 baseline ~31 min/plan (see `milestones/v2.0-ROADMAP.md`)

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table. Recent decisions affecting current work:

- [v2.1 scope, 2026-11-16]: merge verdict + producer research + hygiene; memory bar is "below jellyfish" (already met at both k); MINIM-01..03 permanently descoped; KMC3 dropped; jellyfish is the sole comparator
- [v2.1 roadmap, 2026-11-16]: Phases 11-14 continue v2.0 numbering (v2.0's Phase 11 never created); only two hard dependencies — 13→14 (D3 gate) and 12→14 (provenance stability); 13 is independent and may overlap 11-12 (measurement-only); hygiene is woven into Phase 11 with HYG-01 pulled forward before the merge verdict
- [D3 pattern reused]: Phase 14 executes ONLY if Phase 13's predicted-win memo says GO; PEXT-03/PEXT-04 are conditional requirements
- [v2.0 D3, 2026-11-14]: the prior Phase 11 (MINIM) did NOT execute — Stage A hit parity and memory was below jellyfish; MINIM descoped outright on 2026-11-16

### Pending Todos

None yet.

### Blockers/Concerns

- [Environment, OPEN] `scripts/bench/tests/test_verify_threads.py::TestNegativeControls::test_pre_engine_n_plus_one_stub_is_measured_red` is a pre-existing ~50% macOS `sample`-race flake. A shared `target/` across git worktrees can bake a deleted `CARGO_MANIFEST_DIR` into test binaries — purge stale artifacts before trusting a red result.
- [Carried, OPEN] IN-06/07/09 (Phase-04 review findings) deferred per triage 261111-spz; backlog 999.1-999.3 opportunistic — now HYG-04 in Phase 11.
- [Phase 9, OPEN] 8 Info findings in `09-REVIEW.md` (info only); SECURITY.md for Phases 9/10 is now HYG-03 (Phase 11).
- [Carried W1, OPEN] push dev so local commits get remote CI validation.
- [v2.1 planning note] MBENCH-02's gate is built in Phase 11 (written spec + slice-scale deep gate); its full-scale execution (per-k-mer deep validation) runs inside Phase 12's protocol — parity before timing binds both phases.
- [v2.1 research gap] jellyfish merge runtime/memory at 20-90 GiB is extrapolated until Phase 11's intermediate-scale characterization; disk pre-flight 150-400 GiB is an estimate — re-derive from v2.0 measured DB sizes and expect to raise `--disk-floor-gb`.

## Deferred Items

Items acknowledged and carried forward, most recent first:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Review findings | IN-06/07/09 (Phase-04 harness/test code) | Deferred (triaged 261111-spz) | 2026-11-11 |
| Backlog | 999.1 pyo3 build.rs link args; 999.2 stale site-packages shadowing; 999.3 stale sweep claim | Opportunistic in v2.1 (HYG-04, Phase 11) | 2026-10-09 |
| Review findings | 8 Info findings in `09-REVIEW.md` (Phase 9) | Info-only, tracked | 2026-11-14 |
| Descoped | MINIM-01..03; KMC3 comparison (BENCH-V2-01) | Permanently descoped (user decision) | 2026-11-16 |
| Deferred to v2.2+ | MBF-01 (merge flag sweep, post-INVEST); MBF-02 (N-way/r1+r2); PEXT-05 (extractor refinements) | Post-verdict follow-ons | 2026-11-16 |

## Session Continuity

Last session: 2026-11-16T10:45:43.369Z
Stopped at: Phase 11 context gathered
Resume file: .planning/phases/11-merge-characterization-harness-prep/11-CONTEXT.md
