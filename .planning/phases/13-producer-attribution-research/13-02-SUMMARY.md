---
phase: 13-producer-attribution-research
plan: 02
subsystem: benchmarks
tags: [measurement, full-scale-session, producer-attribution, fingerprint-gate, decompression, predicted-win, gate-decision, provenance]

# Dependency graph
requires:
  - phase: 13-producer-attribution-research
    provides: scripts/bench/phase13.py driver — run_prep/run_measure stages, probe materialization, D-09 attribution, two-ceiling model, D-05 decision (plan 13-01)
  - phase: 11-merge-characterization-harness-prep
    provides: measured_run/_run_fail_loud/ensure_free_space/refuse_repo_root patterns, source fingerprint record, D-10 transient constant
  - phase: 12-full-scale-merge-verdict
    provides: staged-verb/exit-code contract, incremental evidence writes, provenance-validation discipline
provides:
  - .planning/phases/13-producer-attribution-research/13-ATTRIBUTION.json — complete full-scale gate matrix at both k (60 gate records, 16 excluded context records), D-03/D-10 gate block, D-04 plain-input provenance, D-09 attribution, D-09 two-ceiling predicted win, D-05 decision (NO-GO)
  - six decompressed plain FASTQ parts under /Users/forrest/Data/data/illumina/CRR1936095-plain/ (D-07) — awaiting Plan 13-03 deletion after the memo commits
  - three fingerprinted probe instruments in /tmp/phase13-probe-scratch/session-probes/ (committed k=21 probe + materialized k=31 probe + null consumer)
affects: [13-03 (memo render + ROADMAP Phase 14 annotation + plain-input deletion), 14 (conditional phase — PEXT-03/04 remain unexecuted by recorded NO-GO decision)]

actuals:
  tokens: 58039
  tasks: 2
  commits: 3
  plan_head_before: b868ad1c1840ba2d3b03cdb2790d6201d807900b
  plan_head_after: a13457f

tech-stack:
  added: []
  patterns:
    - "Live full-scale session executed by the plan-13-01 staged driver with zero seam changes"
    - "Clean-rebuild gate: stock binary rebuilt from HEAD with git_dirty false asserted before the fingerprint block"
    - "Streaming six-part decompression with sha256+size provenance recorded before any deletion is possible"
    - "Counterbalanced 5-arm x 2-k x 3-rep matrix with per-rep evidence writes and per-rep .rkdb output deletion"

key-files:
  created:
    - .planning/phases/13-producer-attribution-research/13-ATTRIBUTION.json
  modified: []

key-decisions:
  - "The rebuilt stock binary is byte-identical to the pre-session binary (sha256 4539b893...d6d023b): the clean rebuild's contribution is the git_dirty=false provenance, not a new hash; the D-03/D-10 gate branch stays re-measure"
  - "Fresh arm-A base is materially slower than v2.0's walls: 158.29 s k=21 / 177.63 s k=31 vs the v2.0 corroboration 144.69/147.08 s — per D-10 the fresh medians are the only decision denominator and v2.0 appears as disclosed-fingerprint corroboration only"
  - "D-09 attribution (unclamped, sign preserved): inflate 26.25 s / 21.02 s, parse_extract 20.96 s / 20.85 s, route_send 91.80 s / 92.99 s, output_stage 22.39 s / 41.84 s; raw A-B 25.12 / 19.73 s with read-delta corrections -1.13 / -1.29 s (negative because the plain pair reads ~4.6x the bytes)"
  - "D-05 decision is NO-GO: derated predicted improvement 9.62% at k=21 (below the 10.0 bar) and 10.80% at k=31 (above it) — the both-k conjunction fails on k=21; both model modes are 'point' (A3/A4 criteria did not trip)"
  - "The idealized E=M bound was reported only (10.45% / 11.53%) and never entered the bar test, per D-05"
  - "Plain-input size factor measured 4.57x gzip (76,290,905,669 B plain vs 16,712,215,954 B gzip), above the research A1 band of 3.1-3.5x; the prep disk check still passed with 463.2 GB free against 81.4 GB required"
  - "No seam gap surfaced: scripts/bench/phase13.py is unchanged from plan 13-01"

duration: 2h 19min
completed: 2026-11-17
status: complete
---

# Phase 13 Plan 02: Live Full-Scale Attribution Session Summary

**The complete full-scale producer-attribution session at both k: a re-measure fingerprint gate, six provenanced plain inputs, a 60-record counterbalanced gate matrix plus 16 excluded context records, the D-09 delta-corrected stage table, the two-ceiling predicted-win model, and a recorded NO-GO under the pre-registered 10.0 bar (k=21 9.62%, k=31 10.80%).**

## Performance

- **Duration:** 2 h 19 min (12:16:06Z → 14:35Z)
- **Tasks:** 2
- **Files modified:** 1 created (`13-ATTRIBUTION.json`, 219,055 B); `scripts/bench/phase13.py` unchanged; `src/`, `pyo3/src/`, `examples/` untouched

## Accomplishments

### Task 1 — Prep stage live

- Stock release binary rebuilt clean from HEAD with `cargo build --release --locked`; `binary_provenance` recorded `git_dirty: false` and `git_commit 78fc4f4`, and the D-03/D-10 gate block recorded `current=4539b893…d6d023b`, `v2_0=8f38d20c…c87c3d23`, `branch=re-measure` — exactly the D-10 outcome.
- D-04 disk arithmetic passed before any write: 463,239,852,032 B free against 81,419,827,839 B required (measured gzip bytes × 3.5 + the recorded 22.9 GB transient).
- All six gzip parts decompressed by streaming `gunzip -c <part>` into `CRR1936095-plain/<part>.fq` (no in-memory buffering); each plain part recorded with sha256, size, part token, and its list-form decompression argv before any deletion could occur. Total plain bytes: 76,290,905,669.
- Three probe instruments built and fingerprinted: committed `engine_probe` (k=21 by instrument identity, no k field), materialized `phase13-probe-k31` (asserts k=31, manifest enables rustkmer's `profiling` feature), and the `null_consumer`; both scratch crates seeded from their committed lock fixtures and sha256-verified before `--locked` builds.

### Task 2 — Measure stage live

- Complete gate matrix at both k, every record `scale: 'full'` with `binary_sha256`, `input_sha256s`, `command_line`, `cache_state`, `thermal`, `wall_s`, and `peak_rss_bytes`:
  - arm A (stock gzip, `-o` scratch): 3 reps per k; medians 158.29 s / 177.63 s
  - arm B (pinned plain pair, `-o` scratch): 3 reps per k; medians 133.17 s / 157.90 s
  - arm C (stage sub-timers): 12 records per k (2 pinned parts × gzip+plain × 3 reps)
  - arm D (null consumer on plain parts): 6 records per k
  - control (pure read, both pinned-pair parts per invocation): 6 records per k
- 16 excluded D-07 context records: arm C on part_002…part_005 × gzip+plain × both k × 1 rep, marked `context: true` / `excluded: true` and structurally refused by `build_attribution`.
- D-08 discipline: every arm-A/B rep wrote a `.rkdb` via `-o` (17,945,331,662 B at k=21; 22,927,072,042 B at k=31), its stats were recorded, and the file was deleted immediately — `/tmp/phase13-probe-scratch/session-out/` is empty at session end.
- A/B parity: identical distinct k-mers across all reps and both arms (897,266,581 at k=21; 1,146,353,600 at k=31).
- D-09 attribution computed from recorded runs only, with pair-sum-then-median probe reductions and citation maps; D-05 decision computed by `derive_gate_decision` (bar 10.0, `>=`, both-k conjunction).

### Measured result

| Term | k=21 | k=31 |
|---|---|---|
| arm-A median (fresh base) | 158.29 s | 177.63 s |
| arm-B median | 133.17 s | 157.90 s |
| raw A−B | 25.12 s | 19.73 s |
| read-delta correction (gz − plain) | −1.13 s | −1.29 s |
| **inflate** | **26.25 s** | **21.02 s** |
| parse_extract (arm D) | 20.96 s | 20.85 s |
| route_send | 91.80 s | 92.99 s |
| output_stage | 22.39 s | 41.84 s |
| serial terms (inflate + route_send) | 118.05 s | 114.01 s |
| parallelizable floor (derated E=0.5) | 120.67 s | 116.61 s |
| worker floor (busy total / 16) | 25.73 s | 24.75 s |
| predicted full wall (max floors + output) | 143.06 s | 158.45 s |
| **derated improvement** | **9.62%** | **10.80%** |
| idealized improvement (reported only) | 10.45% | 11.53% |
| mode | point | point |

**Decision: NO-GO** — k=21 is 0.38 pp below the pre-registered 10.0 bar, so the both-k conjunction fails even though k=31 clears it. Both modes are `point` (probe_vs_cli_ratio 0.859/0.764 inside the pinned band; worker_busy_ratio 0.189/0.182 ≤ 1.0).

## Task Commits

Each task was committed atomically:

1. **Task 1: Prep stage live — clean rebuild, gate, six plain parts, probes** — `733da76` (feat)
2. **Task 2: Measure stage live — full-scale matrix, NO-GO decision** — `a13457f` (feat)

A pre-session housekeeping commit `78fc4f4` (chore) committed the three in-flight planning files so the D-10 clean-rebuild gate could see `git_dirty: false`, as the plan's precondition directs.

**Plan metadata:** committed with this SUMMARY (docs: complete plan).

## Files Created/Modified

- `.planning/phases/13-producer-attribution-research/13-ATTRIBUTION.json` — the evidence document: `fingerprint_gate`, `prep` (six gzip fingerprints, six plain fingerprints + sizes + decompression commands, probe provenance, disk arithmetic), 76 run records, `attribution.per_k`, `predicted_win.per_k` + decision, doc-level provenance accepted by `bench.validate_provenance`.
- `scripts/bench/phase13.py` — **not modified**; the plan-13-01 driver executed as built.

## Decisions Made

- **The rebuild confirmed, rather than changed, the binary fingerprint.** The clean `--locked` rebuild reproduced sha256 `4539b893…d6d023b`; the gate's value is the recorded `git_dirty: false` provenance, and the `re-measure` branch stands.
- **The fresh base is the only denominator (D-10).** Arm A measured 158.29 s / 177.63 s, 9.4% / 20.8% slower than the v2.0 corroboration walls; no memo percentage may use a v2.0 wall while the fingerprint mismatch stands.
- **The read-delta correction is negative and recorded unclamped (D-09).** Reading the plain pair takes 1.13 s / 1.29 s longer than the gzip pair because it is ~4.6× the bytes; subtracting the negative correction raises the inflate share above the raw A−B delta exactly as measured.
- **NO-GO is the recorded outcome, not a failure.** The k=21 derated model lands 0.38 pp short; the k=31 model clears. No threshold was moved and no rep was dropped.
- **The attribution terms are instrument-topology terms.** The k=21 stage terms sum to 161.40 s against a 158.29 s CLI wall (101.9%) because arm C/D measure one file per invocation while the CLI pair-run counts two files in one engine (Pitfall 7); the model consumes `max(floors) + output_stage`, not the sum.

## Deviations from Plan

None — the plan executed exactly as written. No seam gap surfaced, so `scripts/bench/phase13.py` is unchanged.

### Verification Notes

- The plan's `--stage prep` and `--stage measure` verify commands are the stage runs themselves. Each was executed once and exited 0 (prep-green, measure-green); they were deliberately not re-invoked, because a second invocation would redo the multi-hour measurement and rewrite the committed evidence document. All data-shape verify blocks (matrix completeness, provenance, attribution/model keys, decision, context/probe checks, tree-clean, evidence-committed) were run and passed.

## Issues Encountered

- **`thermal` is `unavailable` on every record.** `pmset -g therm` runs successfully but this host reports no `CPU_Scheduler_Limit` / `CPU_Speed_Limit` lines ("No CPU power status has been recorded"), so the driver's honest-label fallback recorded `unavailable`. Same for `cache_state` (`sudo -n purge` unavailable, as expected).
- **Plain inputs are 4.57× the gzip bytes** (76.29 GB vs 16.71 GB), above the research A1 band of 3.1–3.5×. The prep disk check passed with ample margin; the recorded size feeds Plan 13-03's lifecycle arithmetic.
- **`scratch_cleaned` remains `false`** in the document — the per-rep arm-A/B outputs are deleted (session-out empty), but the probe scratch tree and plain inputs are Plan 13-03's wrap-up.
- No Known Stubs; no new threat surface (the evidence doc is recorded data; no network/auth/file-access surface was added).

## Next Phase Readiness

- Plan 13-03 can render `13-GATE-MEMO.md` directly from the committed evidence doc: `run_memo` requires the complete full-scale matrix, `validate_provenance`, and the attribution/predicted-win blocks — all present. Expected decision at render: **NO-GO**.
- The plain-input directory `/Users/forrest/Data/data/illumina/CRR1936095-plain/` (76.29 GB) is fully provenanced and awaits deletion after the memo commits; probe scratch under `/tmp/phase13-probe-scratch/` is likewise the wrap-up's to remove.
- Phase 14's conditional contract: with a recorded NO-GO, PEXT-03/PEXT-04 remain unexecuted by recorded decision; the memo's revisit conditions are Plan 13-03's to state.

## Self-Check: PASSED

- `13-ATTRIBUTION.json` exists, is git-tracked, and carries no uncommitted changes.
- Commits `78fc4f4`, `733da76`, `a13457f` are ancestors of HEAD.
- `python3 scripts/bench/phase13.py --stage prep` and `--stage measure` each exited 0.
- `bench.validate_provenance(doc)` passes with `git_dirty: false` and `binary.sha256 == fingerprint_gate.current_sha256`.
- `python3 -m unittest scripts.bench.tests.test_phase13_driver` — 80 tests OK; full harness suite — 797 tests OK (1 skipped).
- `git status --porcelain src/ pyo3/src/ examples/` — clean.
