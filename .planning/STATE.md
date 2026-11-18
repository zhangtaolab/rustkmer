---
gsd_state_version: "1.0"
milestone: v2.1
status: Awaiting next milestone
stopped_at: context exhaustion at 97% (2026-11-18)
last_updated: "2026-11-18T02:45:20.566Z"
last_activity: 2026-11-18
last_activity_desc: Milestone v2.1 completed and archived
state_head: b0b893f52af036bcc885f277a9f7a1d5edc297e6
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 15
  completed_plans: 15
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
Last activity: 2026-11-18 - Completed quick task 261118-epn: refresh the paused-handoff snapshot after backlog 999.2 resolution

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
| 261118-c2r | Backlog 999.1: make pyo3/build.rs call pyo3_build_config::add_extension_module_link_args() and re-add pyo3-build-config as a build-dependency so the documented manual-build workaround links as-is under pyo3 0.27 | 2026-11-18 | 78b8542 | [261118-c2r-backlog-999-1-make-pyo3-build-rs-call-py](./quick/261118-c2r-backlog-999-1-make-pyo3-build-rs-call-py/) |
| 261118-csg | Backlog 999.3: correct the stale Phase 03 deferred-items record claiming loose *.chunk files are never swept — CHUNK_FILE_PREFIXES now sweeps them (plan 03-11, commit 83a6ac2, test sweep_reclaims_stale_loose_chunk_files); mark the sweep-coverage entry resolved and close ROADMAP backlog 999.3 | 2026-11-18 | 1d9aaee | [261118-csg-backlog-999-3-correct-the-stale-phase-03](./quick/261118-csg-backlog-999-3-correct-the-stale-phase-03/) |
| 261118-d69 | Backlog 999.2: resolve the dev-venv site-packages shadowing pitfall by documenting it in pyo3/README.md and adding a structural shadowing guard to pyo3/tests/test_version.py, then close ROADMAP backlog 999.2 | 2026-11-18 | e324f55 | [261118-d69-backlog-999-2-resolve-the-dev-venv-site-](./quick/261118-d69-backlog-999-2-resolve-the-dev-venv-site-/) |
| 261118-epn | Refresh .planning/.continue-here.md so the paused-handoff snapshot reflects the resolution of backlog 999.2 (quick 261118-d69): add the d69 row to the session summary, update Current State, remove 999.2 from Remaining Backlog since 999.1-999.3 are all resolved, and update the Resume section | 2026-11-18 | b0b893f | [261118-epn-refresh-planning-continue-here-md-so-the](./quick/261118-epn-refresh-planning-continue-here-md-so-the/) |

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

Last session: 2026-11-18T01:19:19.410Z
Stopped at: context exhaustion at 97% (2026-11-18)
Resume file: None

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
