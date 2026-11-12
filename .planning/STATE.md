---
gsd_state_version: "1.0"
milestone: v2.0
milestone_name: k=21 Counting Parity
current_phase: 05
current_phase_name: Measurement & Regression Harness
status: executing
stopped_at: Completed 05-06-PLAN.md
last_updated: "2026-11-12T10:15:38.094Z"
last_activity: 2026-11-12
last_activity_desc: "Completed quick task 261112-jwl: Raise Rust MSRV 1.80 to 1.82"
state_head: 6c43145963f238cafccadef281b11a69ddbde235
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 7
  completed_plans: 6
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-11-11)

**Core value:** Count, query, and merge k-mers at genome scale within practical memory — fast and lean enough to compete with best-in-class tools (KMC / Jellyfish class), from both the CLI and Python.
**Current focus:** Phase 05 — Measurement & Regression Harness

## Current Position

Phase: 05 (Measurement & Regression Harness) — EXECUTING
Plan: 7 of 7
Status: Ready to execute
Last activity: 2026-11-12 - Completed quick task 261112-jwl: Raise Rust MSRV 1.80 to 1.82

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
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 05 P01 | 37 min | 2 tasks | 4 files |
| Phase 05 P02 | 18 min | 2 tasks | 3 files |
| Phase 05 P03 | 17 min | 2 tasks | 6 files |
| Phase 05 P04 | 45 min | 2 tasks | 5 files |
| Phase 05 P05 | 31 min | 2 tasks | 6 files |
| Phase 05 P06 | 21 min | 2 tasks | 6 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table (v1.0 execution decision log archived with the milestone).
Recent decisions affecting current work:

- [v2.0 scope, 2026-11-11]: k=21 counting parity first; merge untouched this round; acceptance = match or beat Jellyfish2 on both surfaces
- [v2.0 D1, ratified 2026-11-12]: parallelism-first Stage A is the spine — measured root cause is ~3.5x parallel-scaling inefficiency × ~1.4x single-thread cost, NOT data structures; `--threads` is a silent no-op; minimizer/disk-backed demoted to conditional Stage B
- [v2.0 D2, ratified 2026-11-12]: unify N-read semantics on CLI skip-N; Python output changes on N-containing reads (user-accepted, never silent — WR-04 precedent)
- [v2.0 D3, ratified 2026-11-12]: BENCH-V2-01 (KMC3 comparison) stays in v2.0; Phase 11 (MINIM-01..03) executes only if Stage A misses parity OR a memory ceiling Stage A cannot meet; otherwise descope/defer
- [v2.0 roadmap, 2026-11-12]: Phases 5-11 continue v1.0 numbering; research flags on Phases 7/10/(11 if triggered); Phases 6+7 may merge at planning, 8/9 may overlap; never run Phase 10 before 8/9; goldens captured in Phase 5 before any hot-path refactor
- [Phase 05]: [05-01] PROF-02 scaling gate reserves exit 1 for the measured RED verdict; infra failures exit 2 (__main__ guard), so an uncaught exception can never masquerade as expected-RED
- [Phase 05]: [05-01] Shared binary_provenance/validate_provenance in bench.py: actual-bytes sha256 + git HEAD + dirty + profile; SCHEMA_VERSION stays 1, validate_schema untouched (v1 baselines load)
- [Phase 05]: [05-01] Expected-RED verified twice freshness-bound: speedup_t4 1.005/0.977, speedup_t16 1.056/1.055 (<1.3), t1~t4~t16~13s on 500k synthetic reads; gate stays RED until Phase 6 PAR-01
- [Phase 05]: [05-02] Preserve locked-dependency MSRV failures as blockers; no dependency bumps, lockfile edits, --ignore-rust-version, or warning suppression
- [Quick 261112-jwl, user-approved 2026-11-12]: Raise Rust MSRV 1.80 to 1.82 for the existing locked graph; no dependency pin/update. Policy commit `69a82cf`; approved behavior-preserving clippy fix `23967d5`; all three 1.82.0 gates exited 0.
- [Phase 05]: [05-02] Random slicer uses single-pass Algorithm R with O(N) memory, source-index-sorted records, and deterministic fingerprint/seed/index/output-sha256 manifests
- [Phase 05]: [05-03] verify_threads.py hardened: exit-2 paths write no JSON and no verdict line; exceptions exit 2 without traceback; --build-profile flag keeps Rust-test debug provenance honest (dev-host capture stays release)
- [Phase 05]: [05-03] PROF-02 pool-size pair landed: characterization GREEN-now self-destructs when Phase 6 fixes --threads; standing gate ignored RED-now (observed 18/17/17 at requested 1/4/16, release sha256 8f64d442); WINDOWS skipped-test tracks the Phase-6 handoff
- [Phase 05]: [05-03] Golden capture is read-only rehash + manifest equality (12 fixtures, golden test rc 0, manifest sha256 f010e42a); generator never run, fixtures byte-identical; Phase 8 OUT-02 still needs a real write-path differential
- [Phase 05]: [05-04] Parity reference bound to the FULL random recipe (source_sha256 + seed + selection_manifest_sha256 + live-recomputed output_sha256); unbound/missing-identity/ambiguous/duplicate all exit 2; pinned head-4M constants (229694874/519271168) asserted on capture, never re-pinned; --hash-size 2G for real runs
- [Phase 05]: [05-04] Real-data gates proven on CRR1936095 part_001 (source dae91042): head-4M 229694874/519271168 + 1M random seed 20261112 73578421/129801125, both gate-proof re-runs exit 0; random distinct/instance 1.76 vs head 2.26 confirms head repeat-rich
- [Phase 05]: [05-04] Real-slice RED scaling baseline committed (t1/t4/t16 72.27/70.05/68.80s, speedup_t4 1.0318 / speedup_t16 1.0505, both <1.3) — standing Phase 6 PAR-01 target; freshness-bound capture, honest warm cache, no hot-path change
- [Phase 05]: [05-05] Microbench manifest declares rust-version 1.82 (plan literal 1.80 superseded by user-approved MSRV raise 69a82cf); standalone crate builds --locked from committed audited microbench_Cargo.lock whose measured-mechanism closure (dashmap 6.2.1/hashbrown 0.14.5/ahash 0.8.12 + padding/lock/zerocopy/libc deps) is aligned to the production lock; sha256 eabd946a recorded in evidence
- [Phase 05]: [05-05] Attribution-v1 at t16 on real 200k subslice (18M distinct): global-atomics share 120.22 ns/window = 115.2% of shared-vs-local gap; bandwidth share -15.82 ns recorded with inconclusive note (never clamped); t16/t1 multiplier 1.877 vs research 9.4x in-vivo (DRAM-regime + rayon spin-wait absent here) — Phase 7 reads atomics-dominant, bandwidth unproven at 18M distinct
- [Phase 05]: [05-05] Conservation recomputed from raw counts (flag never trusted): any failure exits 1 and the microbench aborts without JSON (mutation-proven); child exit 1 maps to controller exit 1, other child failures exit 2; negative/near-zero (<1% of gap) shares get honest inconclusive notes
- [Phase 05]: [Phase 05]: [05-06] N-free control is the committed Python comparison basis: deterministic drop-records-with-N filter of the 1M random subslice (seed 20261112), live CLI-vs-Python parity on the same bytes BEFORE timing, exact counts pinned across reps — invariant under Phase 9's D2 skip-N change; real-N arm labeled timing-only-real-N-pre-D2
- [Phase 05]: [Phase 05]: [05-06] Fresh-worker Python measurement + module provenance: every rep is a new interpreter process under /usr/bin/time (never an in-process clock); worker resolves maturin 1.11's editable-shim inner native .so so the fingerprint (c7701806) covers the measured bytes; stale/shadowed/zero-count/rep-disagreement runs exit 2, never skip
- [Phase 05]: [Phase 05]: [05-06] N-read differential recorded D2 evidence only: control exactly equal; 33 Python-only chimeric k-mers in n_at_window_end/n_at_window_start/multiple_n/lowercase_n; 0 CLI-only; --expect-unified reserved for Phase 9; neither surface's semantics changed

### Pending Todos

None yet.

### Blockers/Concerns

- [Carried W1, OPEN] Unpushed local dev commits lack remote CI validation (memmap2 floor, Cargo.lock tracking, --locked CI, MSRV declaration, clippy fixes). Push dev to resolve.
- [Resolved 05-02] Rust 1.80.0 + clippy installed locally; remaining MSRV blocker is locked dependency compatibility, recorded below.
- [v2.0 research] Stage-A-achieves-parity is a MEDIUM-confidence extrapolation — the slice gates after Phases 6-8 must validate it; a miss feeds the D3 trigger decision (Phase 11).
- [Carried] Phase-04 review findings IN-06/07/09 deferred (triage 261111-spz: 11 fixed / 4 already-fixed / 3 deferred); backlog 999.1-999.3 opportunistic only if touched by the perf work.
- [Resolved quick 261112-jwl] User approved raising MSRV to 1.82 for the unchanged locked graph; `69a82cf` carries the policy and `23967d5` the sole behavior-preserving clippy fix. Rust 1.82.0 root build/root clippy/PyO3 clippy all exited 0; WINDOWS 19/20 are fixed.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 261112-jwl | Raise Rust MSRV 1.80 to 1.82 | 2026-11-12 | 69a82cf | [261112-jwl-raise-rust-msrv-1-80-1-82-user-approved-](./quick/261112-jwl-raise-rust-msrv-1-80-1-82-user-approved-/) |

## Deferred Items

Items acknowledged and carried forward, most recent first:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Review findings | IN-06/07/09 (Phase-04 harness/test code) | Deferred (triaged 261111-spz) | 2026-11-11 |
| Backlog | 999.1 pyo3 build.rs link args; 999.2 stale site-packages shadowing; 999.3 deferred-items stale sweep claim | Opportunistic in v2.0 if touched | 2026-10-09 |

## Session Continuity

Last session: 2026-11-12T10:15:38.078Z
Stopped at: Completed 05-06-PLAN.md
Resume file: None

## Operator Next Steps

- Review and approve the v2.0 roadmap, then run /gsd-plan-phase 5
