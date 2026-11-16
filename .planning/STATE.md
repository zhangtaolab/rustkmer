---
gsd_state_version: "1.0"
milestone: v2.1
milestone_name: Merge Verdict & Producer Research
current_phase: 11
current_phase_name: Merge Characterization & Harness Prep
status: executing
stopped_at: Completed 11-04-PLAN.md
last_updated: "2026-11-16T14:13:02.025Z"
last_activity: 2026-11-16
last_activity_desc: Phase 11 execution started
state_head: b29dff9c5da81c09932326b1ac0b0b2ff62e6af7
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 8
  completed_plans: 4
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-11-16)

**Core value:** Count, query, and merge k-mers at genome scale within practical memory — fast and lean enough to compete with best-in-class tools (KMC / Jellyfish class), from both the CLI and Python.
**Current focus:** Phase 11 — Merge Characterization & Harness Prep

## Current Position

Phase: 11 (Merge Characterization & Harness Prep) — EXECUTING
Plan: 6 of 8
Status: Ready to execute
Last activity: 2026-11-16 — Phase 11 execution started

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
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 11 P01 | 18min | 3 tasks | 5 files |
| Phase 11 P02 | 17min | 2 tasks | 2 files |
| Phase 11 P03 | 6min | 2 tasks | 5 files |
| Phase 11 P08 | 10min | 2 tasks | 6 files |
| Phase 11 P04 | 15 min | 3 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table. Recent decisions affecting current work:

- [v2.1 scope, 2026-11-16]: merge verdict + producer research + hygiene; memory bar is "below jellyfish" (already met at both k); MINIM-01..03 permanently descoped; KMC3 dropped; jellyfish is the sole comparator
- [v2.1 roadmap, 2026-11-16]: Phases 11-14 continue v2.0 numbering (v2.0's Phase 11 never created); only two hard dependencies — 13→14 (D3 gate) and 12→14 (provenance stability); 13 is independent and may overlap 11-12 (measurement-only); hygiene is woven into Phase 11 with HYG-01 pulled forward before the merge verdict
- [D3 pattern reused]: Phase 14 executes ONLY if Phase 13's predicted-win memo says GO; PEXT-03/PEXT-04 are conditional requirements
- [v2.0 D3, 2026-11-14]: the prior Phase 11 (MINIM) did NOT execute — Stage A hit parity and memory was below jellyfish; MINIM descoped outright on 2026-11-16
- [Phase 11]: 11-01 renderer scope: merge row gains jellyfish-merge deltas via _arm_row merge_base param; merge-t1/jellyfish-merge table rows deferred to Phase 12 renderer work
- [Phase 11]: 11-01: --skip-merge excludes all three merge arms symmetrically; jellyfish-count-B from cfg_b with byte-identical -m/-s/-C per D-01
- [Phase 11]: prepare_inputs reconcile_anchors(totals_by_k, anchors=None, ks=None) is the single anchor enforcement point: build calls ks=(k,) per k mid-build (abort before next k / -s derivation); default full-set shape raises on missing k
- [Phase 11]: prepare_inputs DEFAULT_RUSTKMER is REPO_ROOT-resolved absolute (stage runs from any cwd); jf stage re-verifies recorded .rkdb identity + source fingerprints before building .jf inputs (the -s plan depends on those Distinct values)
- [Phase 11]: hash_size_plan carries slots/occupancy computed by the stage (jellyfish 2.3.1 info reports only command/where/when/canonical, probed 2026-11-16); empty .rkdb stats exit-1 normalized into the zero-count abort (MBENCH-01/empty)
- [Phase 11]: [11-03]: benchmark-report.md SUPERSEDED banner is the single acknowledged generated-file exception (re-render from v1.0 JSONs drops it); renderer-narrative debt (bench.py halt note :1981-1990, CRR2044018 block :2040-2045 post-11-01 anchors) owned by the post-Phase-12 rewrite — protects old-JSON re-render byte-identity per research Open Question 4; recorded in 11-HYGIENE-RECORD.md
- [Phase 11]: [11-03]: dataset description corrected to six single-member gzip parts (~2.79 GB each, ~16.7 GB total), pinned pair part_001+part_006 unchanged; HYG-04: WARNING-2 assigned to the 11-07 same-touch, backlog 999.1-999.3 not triggered (tracked, non-gate-blocking) — D-05/D-06 factual fixes only; HYG-04 opportunistic rule
- [Phase 11]: [11-08]: Phase 7 draft VALIDATION.md confirmed in place via the workflow's State A audit (draft -> validated, Wave 0 verified delivered) rather than re-issued; 05/06/08 reconstructed grounding on the archived 2026-11-14 re-verification reports; security records keep plan-time dispositions (09 T-9-07 accepted low / IN-03 info-only; 10 T-10-SC reserved) — 8 Info findings NOT re-opened
- [Phase 11]: 11-04: merge parity gate wired as pre-gate (assert_merge_parity) + deep verdict gate (dump_vs_dump_equal), both before results acceptance, guarded on the jellyfish-merge arm
- [Phase 11]: 11-04: comparator sorts in-process with Python str ordering (byte-identical to LC_ALL=C over the ASCII dump alphabet) instead of shelling out to sort; dumps go via workdir files (rustkmer dump -o / jellyfish dump -c stdout)
- [Phase 11]: 11-04: live slice proof head-provisions 200k reads from the first sorted parts (functional gate proof only); the pinned part_001+part_006 pair and union anchors bind full-scale runs through the prepare manifest
- [Phase 11]: 11-04: MBENCH-02 left unmarked in REQUIREMENTS.md — shared with 11-07 which has no SUMMARY yet (shared-ID gate)

### Pending Todos

None yet.

### Blockers/Concerns

- [Environment, OPEN] `scripts/bench/tests/test_verify_threads.py::TestNegativeControls::test_pre_engine_n_plus_one_stub_is_measured_red` is a pre-existing ~50% macOS `sample`-race flake. A shared `target/` across git worktrees can bake a deleted `CARGO_MANIFEST_DIR` into test binaries — purge stale artifacts before trusting a red result.
- [Carried, OPEN] IN-06/07/09 (Phase-04 review findings) deferred per triage 261111-spz; backlog 999.1-999.3 opportunistic — now HYG-04 in Phase 11.
- [Phase 9, OPEN] 8 Info findings in `09-REVIEW.md` (info only); SECURITY.md for Phases 9/10 is now HYG-03 (Phase 11).
- [Carried W1, OPEN] push dev so local commits get remote CI validation.
- [v2.1 planning note] MBENCH-02's gate is built in Phase 11 (written spec + slice-scale deep gate); its full-scale execution (per-k-mer deep validation) runs inside Phase 12's protocol — parity before timing binds both phases.
- [v2.1 research gap] jellyfish merge runtime/memory at 20-90 GiB is extrapolated until Phase 11's intermediate-scale characterization; disk pre-flight 150-400 GiB is an estimate — re-derive from v2.0 measured DB sizes and expect to raise `--disk-floor-gb`.
- Pre-existing (not 11-01): test_phase10_verdict.py reads archived .planning/phases/10-benchmark-verdict/ paths moved to .planning/milestones/v2.0-phases/ by 97c497c — 3 full-suite tests red; path retarget needed (see 11-01 deferred-items.md)

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

Last session: 2026-11-16T14:12:48.065Z
Stopped at: Completed 11-04-PLAN.md
Resume file: None
