---
gsd_state_version: "1.0"
milestone: v2.1
status: Awaiting next milestone
stopped_at: context exhaustion at 97% (2026-11-18)
last_updated: "2026-11-18T10:13:12.093Z"
last_activity: 2026-11-18
last_activity_desc: Milestone v2.1 completed and archived
state_head: 71c8c3fcdda66c92d764f60f545210fbd2e0d057
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
Last activity: 2026-11-18 - Completed quick task 261118-oy5: milestone-prep consistency check (20 findings; three stale texts repaired)

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

- [Environment, RESOLVED 2026-11-18] The macOS `scripts/bench/tests/test_verify_threads.py::TestNegativeControls::test_pre_engine_n_plus_one_stub_is_measured_red` flake is closed by quick 261118-n53: `observe()` records the peak nonzero observation, so a truncated exit-window `sample` report can never overwrite a correct earlier count (the zero-report retry landed in 261118-bhr), and the pre-engine negative control passed 10/10 stress runs. A shared `target/` across git worktrees can still bake a deleted `CARGO_MANIFEST_DIR` into test binaries — purge stale artifacts before trusting a red result.
- [Carried, RESOLVED 2026-11-18] IN-06/07/09 (Phase-04 review findings) closed by quick 261118-f80; backlog 999.1-999.3 also resolved (c2r/d69/csg) — no gate-blocking backlog remains.
- [Phase 9, RESOLVED 2026-11-18] 8 Info findings in `09-REVIEW.md` closed by quick 261118-fsk (7 Fixed, 1 Accepted as a no-code-change preservation-gate rationale).
- [Carried W1, RESOLVED 2026-11-18] pushed dev (through f4e2dc9) and tag v2.1 to origin — remote CI now sees every local commit.
- [v2.1 close, acknowledged] Deferred-item acknowledgments recorded in the Deferred Items table below — no live carry-forward remains: the macOS flake was closed by quick 261118-n53, and the `.claude/CLAUDE.md` dataset-line drift was verified already corrected (line 17 reads ~16.7 GB / six single-member split parts) and its record is closed.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 261118-bhr | Apply verify-work audit fixes: fix verify_threads zero-thread race and add unit test; correct 11-05 and 06-03 SUMMARY coverage schemas; sync .claude/CLAUDE.md dataset line; correct 11-PREPARE-RECORD free-space figure; mark 06/08 deferred items resolved; close WINDOWS ledger entries 26 and 27 | 2026-11-18 | 2bcfc9b | [261118-bhr-apply-verify-work-audit-fixes-fix-verify](./quick/261118-bhr-apply-verify-work-audit-fixes-fix-verify/) |
| 261118-c2r | Backlog 999.1: make pyo3/build.rs call pyo3_build_config::add_extension_module_link_args() and re-add pyo3-build-config as a build-dependency so the documented manual-build workaround links as-is under pyo3 0.27 | 2026-11-18 | 78b8542 | [261118-c2r-backlog-999-1-make-pyo3-build-rs-call-py](./quick/261118-c2r-backlog-999-1-make-pyo3-build-rs-call-py/) |
| 261118-csg | Backlog 999.3: correct the stale Phase 03 deferred-items record claiming loose *.chunk files are never swept — CHUNK_FILE_PREFIXES now sweeps them (plan 03-11, commit 83a6ac2, test sweep_reclaims_stale_loose_chunk_files); mark the sweep-coverage entry resolved and close ROADMAP backlog 999.3 | 2026-11-18 | 1d9aaee | [261118-csg-backlog-999-3-correct-the-stale-phase-03](./quick/261118-csg-backlog-999-3-correct-the-stale-phase-03/) |
| 261118-d69 | Backlog 999.2: resolve the dev-venv site-packages shadowing pitfall by documenting it in pyo3/README.md and adding a structural shadowing guard to pyo3/tests/test_version.py, then close ROADMAP backlog 999.2 | 2026-11-18 | e324f55 | [261118-d69-backlog-999-2-resolve-the-dev-venv-site-](./quick/261118-d69-backlog-999-2-resolve-the-dev-venv-site-/) |
| 261118-epn | Refresh .planning/.continue-here.md so the paused-handoff snapshot reflects the resolution of backlog 999.2 (quick 261118-d69): add the d69 row to the session summary, update Current State, remove 999.2 from Remaining Backlog since 999.1-999.3 are all resolved, and update the Resume section | 2026-11-18 | b0b893f | [261118-epn-refresh-planning-continue-here-md-so-the](./quick/261118-epn-refresh-planning-continue-here-md-so-the/) |
| 261118-f80 | Resolve Phase-04 deferred review findings IN-06/IN-07/IN-09: interpolate {route:?} in the two merge_bounded_memory_tests expect_err messages; reject leading-hyphen paths in scripts/bench/bench.py validate_path; emit explicit no-input_fingerprint notes in the bench.py render listing; pin each with targeted Rust/Python tests and mark the 04-REVIEW-DISPOSITION records fixed | 2026-11-18 | 1b91b5e | [261118-f80-resolve-phase-04-deferred-review-finding](./quick/261118-f80-resolve-phase-04-deferred-review-finding/) |
| 261118-fsk | Resolve the 8 Phase-09 info-only review findings: IN-01 accepted (no code change); IN-02/IN-03/IN-07 PyO3 docstring and defensive-arm documentation; IN-04 guard --previous against non-divergence/empty prior state; IN-05 scope record_boundary plus a test-local N-free cross-record-join probe; IN-06 make the missing-extension test deterministic under -S; IN-08 require reps>=3 and CV-clean arms in compare mode; update 09-REVIEW.md to 7 Fixed / 1 Accepted | 2026-11-18 | fcbe3d2 | [261118-fsk-resolve-the-8-phase-09-info-only-review-](./quick/261118-fsk-resolve-the-8-phase-09-info-only-review-/) |
| 261118-jp1 | Close the stale carry-forward records for the already-resolved .claude/CLAUDE.md dataset-line drift: verified the generated line reads ~16.7 GB / six single-member split parts; updated .continue-here.md Remaining Backlog/Resume to drop the resolved Phase-04 IN-06/07/09, Phase-09 8 Info findings, and the dataset drift; closed the matching STATE.md rows | 2026-11-18 | cc641d8 | [261118-jp1-close-the-stale-carry-forward-records-fo](./quick/261118-jp1-close-the-stale-carry-forward-records-fo/) |
| 261118-n53 | Close the macOS test_verify_threads ~50% sample-race flake: harden observe() to record the peak nonzero thread observation (a truncated exit-window sample can no longer clobber a correct earlier count), pin it with deterministic TestObservePeakGuard unit tests (both observed RED pre-fix at 3 and 2, GREEN at 5 and 5 post-fix), stress-verify the pre-engine negative control 10/10, and close the stale records in STATE.md, .continue-here.md, and 11/deferred-items.md | 2026-11-18 | 2da9988 | [261118-n53-make-the-macos-test-verify-threads-pre-e](./quick/261118-n53-make-the-macos-test-verify-threads-pre-e/) |
| 261118-nss | Run the GSD planning-directory health diagnostic and record a dated report in the quick task directory: live validate.health is degraded with 0 errors / 1 warning (W019) / 0 repairable; W019 (.continue-here.md not in the artifact registry) is accepted as a live pause/resume handoff rather than repaired; sentinel-free isolation inspection resolves harness-worktree and W025 does not fire; no repairs applied; one atomic product commit contains only the report | 2026-11-18 | 1180d9c | [261118-nss-diagnose-planning-directory-health-run-t](./quick/261118-nss-diagnose-planning-directory-health-run-t/) |
| 261118-o67 | Record the W019 health-scanner registry gap as a known GSD tooling bug in .planning/.continue-here.md: entry 3 in Known Tooling Bugs names the false positive, cites CANONICAL_EXACT in bin/lib/artifacts.cjs (line 18 declaration, line 50 membership test), notes the pause/resume provenance and the resume-breaking move/delete fix, and states the upstream fix; the snapshot last_updated was refreshed to 2026-11-18T09:32:41Z; all other sections byte-identical | 2026-11-18 | 3cd0e0f | [261118-o67-record-the-w019-health-scanner-registry-](./quick/261118-o67-record-the-w019-health-scanner-registry-/) |
| 261118-op9 | Refresh .planning/.continue-here.md so the paused-handoff snapshot reflects the eight quick tasks landed this session: Session Summary extended from four to eight rows (jp1/cc641d8, n53/68b3995, nss/1180d9c, o67/3cd0e0f), Current State updated with the execution-time HEAD, the n53 macOS flake closure (peak guard, 22-test file, stress 10/10), the o67 W019 known-tooling-bug record, and fresh audit-uat/windows counter values; frontmatter last_updated refreshed to 2026-11-18T09:53:20Z | 2026-11-18 | acb8ac8 | [261118-op9-refresh-planning-continue-here-md-so-the](./quick/261118-op9-refresh-planning-continue-here-md-so-the/) |
| 261118-oy5 | Milestone-prep consistency check across PROJECT.md, ROADMAP.md, STATE.md, MILESTONES.md, and .continue-here.md: 20 findings recorded (12 CONSISTENT, 7 STALE, 1 UNRECONCILED — WARNING-1 has no recorded resolution); three proven stale texts repaired (ROADMAP 09-REVIEW info-only claim, ROADMAP 999.x opportunistic note, two PROJECT.md — Pending v2.0 outcome cells); everything else recorded as recommendations (STATE current_phase 14 on a closed milestone, remote-CI/push wording, etc.) | 2026-11-18 | 71c8c3f | [261118-oy5-run-a-milestone-prep-consistency-check-a](./quick/261118-oy5-run-a-milestone-prep-consistency-check-a/) |

## Deferred Items

Items acknowledged and carried forward, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| quick_tasks | 261116-lhq (AtomicU64::fetch_update deprecation suppressed at src/hash/table.rs; work committed 3655086, all gates green) | Acknowledged (scanner status unknown; work complete) | 2026-11-18 | v2.1 |
| deferred_items | 11/deferred-items.md: Pre-existing flake — test_verify_threads.py TestNegativeControls pre_engine_n_plus_one stub (~50% macOS sample-race) | Resolved (quick 261118-n53, 2026-11-18; peak-observation guard in `observe()`) | 2026-11-18 | v2.1 |
| deferred_items | 11/deferred-items.md: Docs drift — .claude/CLAUDE.md:17 pre-correction two-parts dataset line | Resolved (quick 261118-bhr; verified 2026-11-18 in quick 261118-jp1: line reads ~16.7 GB / six single-member split parts) | 2026-11-18 | v2.1 |
| Review findings | IN-06/07/09 (Phase-04 harness/test code) | Resolved (quick 261118-f80, 2026-11-18) | 2026-11-11 | — |
| Backlog | 999.1 pyo3 build.rs link args; 999.2 stale site-packages shadowing; 999.3 stale sweep claim | Resolved 2026-11-18 (999.1 c2r; 999.2 d69; 999.3 csg) | 2026-10-09 | — |
| Review findings | 8 Info findings in `09-REVIEW.md` (Phase 9) | Resolved (quick 261118-fsk, 2026-11-18; 7 fixed, 1 accepted) | 2026-11-14 | — |
| Descoped | MINIM-01..03; KMC3 comparison (BENCH-V2-01) | Permanently descoped (user decision) | 2026-11-16 | — |
| Deferred to v2.2+ | MBF-01 (merge flag sweep, post-INVEST); MBF-02 (N-way/r1+r2); PEXT-05 (extractor refinements) | Post-verdict follow-ons | 2026-11-16 | — |

## Session Continuity

Last session: 2026-11-18T01:19:19.410Z
Stopped at: context exhaustion at 97% (2026-11-18)
Resume file: None

## Operator Next Steps

- Start the next milestone with /gsd-new-milestone
