---
gsd_state_version: "1.0"
milestone: v2.0
milestone_name: k=21 Counting Parity
status: planning
last_updated: "2026-11-11T16:32:49.000Z"
last_activity: 2026-11-12
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-11-11)

**Core value:** Count, query, and merge k-mers at genome scale within practical memory — fast and lean enough to compete with best-in-class tools (KMC / Jellyfish class), from both the CLI and Python.
**Current focus:** v2.0 k=21 Counting Parity — Phase 5 (Measurement & Regression Harness), ready to plan

## Current Position

Phase: 5 of 11 (Measurement & Regression Harness) — v2.0 spans Phases 5-11; Phase 11 conditional on D3
Plan: — (not yet planned)
Status: Ready to plan
Last activity: 2026-11-12 — v2.0 roadmap created: 7 phases, 21/21 requirements mapped (18 committed + 3 conditional MINIM)

Progress: [░░░░░░░░░░] 0% (v2.0)

## Performance Metrics

**Velocity (v2.0):**

- Total plans completed: 0
- Average duration: - min
- Total execution time: 0.0 hours
- v1.0 history: 31 plans / 4 phases (per-plan metrics archived in milestones/v1.0-phases/)
- Post-v1.0 hygiene wave (2026-10-21 → 2026-11-11): 10 quick tasks (memmap2 security floor, Cargo.lock + --locked CI, MSRV normalization, clippy fixes, review triage, WINDOWS #15) — records in .planning/quick/

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Foundation & Quality (v1.0) | 4/4 | - | - |
| 2. Parallel Counting (v1.0) | 5/5 | - | - |
| 3. Memory Safety (v1.0) | 17/17 | - | - |
| 4. Benchmark & Validation (v1.0) | 5/5 | - | - |
| 5. Measurement & Regression Harness | 0/TBD | - | - |
| 6. Parallelism Correctness & Hot Path | 0/TBD | - | - |
| 7. Shared Counting Engine | 0/TBD | - | - |
| 8. Output Pipeline & .rkdb v2 Parity | 0/TBD | - | - |
| 9. Python Parity | 0/TBD | - | - |
| 10. Benchmark Verdict | 0/TBD | - | - |
| 11. Minimizer & Memory Ceiling (conditional) | 0/TBD | - | - |

**Recent Trend:**

- Last 5 plans: - (v2.0 not started)
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table (v1.0 execution decision log archived with the milestone).
Recent decisions affecting current work:

- [v2.0 scope, 2026-11-11]: k=21 counting parity first; merge untouched this round; acceptance = match or beat Jellyfish2 on both surfaces
- [v2.0 D1, ratified 2026-11-12]: parallelism-first Stage A is the spine — measured root cause is ~3.5x parallel-scaling inefficiency × ~1.4x single-thread cost, NOT data structures; `--threads` is a silent no-op; minimizer/disk-backed demoted to conditional Stage B
- [v2.0 D2, ratified 2026-11-12]: unify N-read semantics on CLI skip-N; Python output changes on N-containing reads (user-accepted, never silent — WR-04 precedent)
- [v2.0 D3, ratified 2026-11-12]: BENCH-V2-01 (KMC3 comparison) stays in v2.0; Phase 11 (MINIM-01..03) executes only if Stage A misses parity OR a memory ceiling Stage A cannot meet; otherwise descope/defer
- [v2.0 roadmap, 2026-11-12]: Phases 5-11 continue v1.0 numbering; research flags on Phases 7/10/(11 if triggered); Phases 6+7 may merge at planning, 8/9 may overlap; never run Phase 10 before 8/9; goldens captured in Phase 5 before any hot-path refactor

### Pending Todos

None yet.

### Blockers/Concerns

- [Carried W1, OPEN] Unpushed local dev commits lack remote CI validation (memmap2 floor, Cargo.lock tracking, --locked CI, MSRV declaration, clippy fixes). Push dev to resolve.
- [v2.0 research] Rust 1.80 toolchain not installed locally — install in Phase 5 so MSRV-aware clippy gates both crates from the start; dev-host stable clippy is not MSRV evidence.
- [v2.0 research] Stage-A-achieves-parity is a MEDIUM-confidence extrapolation — the slice gates after Phases 6-8 must validate it; a miss feeds the D3 trigger decision (Phase 11).
- [Carried] Phase-04 review findings IN-06/07/09 deferred (triage 261111-spz: 11 fixed / 4 already-fixed / 3 deferred); backlog 999.1-999.3 opportunistic only if touched by the perf work.

## Deferred Items

Items acknowledged and carried forward, most recent first:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Review findings | IN-06/07/09 (Phase-04 harness/test code) | Deferred (triaged 261111-spz) | 2026-11-11 |
| Backlog | 999.1 pyo3 build.rs link args; 999.2 stale site-packages shadowing; 999.3 deferred-items stale sweep claim | Opportunistic in v2.0 if touched | 2026-10-09 |

## Session Continuity

Last session: 2026-11-12 (roadmapper)
Stopped at: v2.0 ROADMAP.md + STATE.md written; REQUIREMENTS.md traceability populated (21/21); awaiting orchestrator presentation + user approval
Resume file: None

## Operator Next Steps

- Review and approve the v2.0 roadmap, then run /gsd-plan-phase 5