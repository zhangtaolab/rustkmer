---
phase: 11-merge-characterization-harness-prep
plan: 06
subsystem: measurement-infrastructure
tags: [benchmark-harness, characterization-ladder, jellyfish-merge, rustkmer-merge, reservoir-slice, slope-linearity, rkdb, jf, d07, d08, d09, mbench-01, mbench-04]

# Dependency graph
requires:
  - phase: 11-01
    provides: merge arms + bench.py measure/stats/cmd builders (build_merge_cmd, jellyfish_merge_cmd) and assert_merge_parity reuse surface
  - phase: 11-02
    provides: prepare-stage functions the ladder chain exercises (derive_hash_size, hash_size_slots, refuse_repo_root, discover_part_pair, run_command)
  - phase: 11-04
    provides: PARITY-GATE.md written spec + assert_merge_parity (the rung gates execute per it before rung medians are recorded)
  - phase: 11-05
    provides: full-scale artifact economics (10.000/12.000 B/entry .jf anchors) and the D-03 outside-repo discipline precedent
provides:
  - scripts/bench/merge_characterize.py — the pinned two-rung x both-k ladder runner (reservoir_slice provisioning, complete prepare->count->merge chain, /usr/bin/time measurement, slope fit, evidence-JSON writer) and the streaming PARITY-GATE.md §4 deep-gate form for ladder-scale dumps
  - .planning/phases/11-merge-characterization-harness-prep/11-LADDER-RESULTS.json — committed evidence: 4 rung records (2 scales x 2 k), per-run wall/output-size/entry counts/cache_state/route/provenance, gates green, fitted slopes + linearity verdicts + full-scale extrapolations with the MBENCH-04 backstop caveat
  - Phase 12 scheduling input: per tool-k wall-per-entry slopes (jellyfish 8.97e-8/1.008e-7 s/entry at k=21/31; rustkmer 6.67e-8/7.41e-8) — all four linear (ratios 1.06-1.37, under the 2x flag)
  - D-10 transient input for Plan 11-07: measured merge-output sizes (e.g. 40% k=31: .rkdb 15.24 GB / .jf 9.14 GB at 762,068,515 entries) + extrapolated full-scale merge walls (rustkmer 53.8/73.4 s, jellyfish 77.3/105.5 s)
affects: [Plan 11-07 (floor derivation + dress rehearsal consumes the slopes and the D-10 transient term), Phase 12 (round scheduling + MBENCH-04 predicted-vs-measured backstop)]

# Actuals (#2632) — pairs with the plan's estimate (50000) to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 20200    # chars/4 over git diff gsd-plan-head-before-11-06..2e1a16e (merge_characterize.py ~975 lines + 11-LADDER-RESULTS.json 1041 lines)
  tasks: 3
  commits: 4      # MEASURED: git rev-list --count gsd-plan-head-before-11-06..2e1a16e (last task commit; the metadata commit follows)
plan_head_before: d91c6be6eceaad11a4531fce671ba3013e73abb5
plan_head_after: 2e1a16eee0fbb3985a761c22b9524feb05c7e5a2

# Tech tracking
tech-stack:
  added: []       # stdlib-only contract preserved (bench.py:25-26); zero installs (T-11-SC N/A)
  patterns:
    - "Two-point ladder discipline: one measured rep per merge per rung point — the slope comes from BETWEEN rungs (D-07), not from within-rung CV"
    - "Gate-as-spec-at-scale: when the in-process comparator cannot run at measured scale, the WRITTEN spec's original streaming form (fail-loud normalize, LC_ALL=C external sort, exact identity) executes the same legs within practical memory"
    - "Slice-scale -s derivation per rung-k (derive_hash_size from measured per-part Distinct) — the D-04 occupancy logic exercised live at two scales (500M at 10%, 1G at 40%)"

key-files:
  created:
    - scripts/bench/merge_characterize.py
    - .planning/phases/11-merge-characterization-harness-prep/11-LADDER-RESULTS.json
  modified: []

key-decisions:
  - "Deep dump-vs-dump leg runs the PARITY-GATE.md §4 streaming form at ladder scale (in merge_characterize.py; bench.py untouched): measured 10%-rung dumps are 318.5M/373.0M lines per side and bench.dump_vs_dump_equal's in-process normalize+sort would need ~120-150 GB heap — impossible on this host; the written spec's original pipeline (fail-loud awk normalization, LC_ALL=C external sort, exact per-k-mer identity) executes the same legs streaming, byte-order identical over the pure-ASCII dump alphabet"
  - "One measured rep per merge per rung (8 measured merges total): the D-07 two-point design takes its slope between rungs; within-rung CV is not the ladder's deliverable, keeping the session inside its 30-60+ min budget"
  - "Route attribution recorded honestly as not-reported at every merge: the rustkmer merge default route prints no route line and jellyfish merge is single-strategy — stderr captured and scanned per rep (T-11-15: no invention), no Rust changes"
  - "measured_run() keeps stderr while delegating parsing to bench.parse_time_output (same /usr/bin/time -l invocation, same units-pinned parser): bench.measure() discards stderr, which the plan's route-attribution requirement needs — the only way to satisfy both constraints without touching bench.py"

patterns-established:
  - "Evidence-JSON of its own kind (schema_version 1, kind merge-characterization-ladder): rungs flat-list of exactly 4 records, never a fork of the bench results schema (MBENCH-05 boundary)"
  - "Ladder scratch outside the repo (default /tmp/rustkmer-phase11/ladder) with refuse_repo_root enforcement, per-rung free-space guard (>= 20 GiB), deterministic slice reuse verified by sha256, and post-evidence cleanup recorded in the evidence document"

requirements-completed: [MBENCH-01]

# Coverage metadata (#1602) — one entry per shipped deliverable.
coverage:
  - id: D1
    description: "merge_characterize.py exposes the pinned two-rung x both-k ladder with the full prepare->count->merge chain, measure-based timing, slope fit, and evidence-JSON output"
    requirement: MBENCH-01
    verification:
      - kind: other
        ref: "command: python3 -c \"import ast; ... assert {'run_rung','fit_slope'} <= names; assert 'reservoir_slice' in src and '3500000' in src and '14000000' in src\" + python3 scripts/bench/merge_characterize.py --help (exit 0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Ladder executed end-to-end on real data: 4 rung records (2 scales x 2 k), both tools merged on the same slice pairs, gates green before record acceptance, scratch cleaned and recorded"
    requirement: MBENCH-01
    verification:
      - kind: integration
        ref: "command: python3 scripts/bench/merge_characterize.py --run (exit 0, ~58 min) + plan Task 2 verify (4 rungs, scales {3500000,14000000}, ks {21,31}, tools {jellyfish,rustkmer}, scratch_cleaned true)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Summary block finalized: >=4 tool-k fitted slopes, measured bytes-per-entry (.rkdb ~20 B/entry vs .jf exactly 10.000/12.000), linearity verdicts (all linear, ratios 1.06-1.37), extrapolated full-scale walls with the MBENCH-04 backstop caveat (D-07)"
    requirement: MBENCH-01
    verification:
      - kind: other
        ref: "command: python3 scripts/bench/merge_characterize.py --summarize (idempotent) + plan Task 3 verify (>=4 slopes, linearity present, extrapolated_full_scale present) + python3 -m json.tool (parses)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Harness regression net intact: full bench suite green modulo the documented pre-existing reds (test_phase10_verdict.py archived-path family + the STATE.md-documented ~50% macOS sample-race flake)"
    requirement: MBENCH-01
    verification:
      - kind: unit
        ref: "command: python3 -m unittest discover -s scripts/bench/tests -t . — Ran 630 tests, failures=2 errors=2 skipped=1; all 4 reds in the two documented pre-existing families (2+1 archived-path, 1 flake), zero related to this plan's files"
        status: pass
    human_judgment: false

# Metrics
duration: 80min
completed: 2026-11-16
status: complete
---

# Phase 11 Plan 06: Characterization Ladder Summary

**Two-point real-data merge ladder executed end-to-end (10%/40% part scale x k=21/31, seed 4242, pinned part_001+part_006 pairs): both tools ran the complete prepare->count->merge chain per side with exact cross-tool parity and green gates at every rung — rustkmer merge 15.2-44.9 s at 1.6-2.3 GB peak vs jellyfish merge 25.3-66.8 s at a constant 6.8 MB RSS, all four tool-k slopes linear, slopes + linearity + flagged full-scale extrapolations committed for Phase 12 scheduling and the D-10 floor term**

## Performance

- **Duration:** 80 min (ladder run itself ~58 min: 15:46:04Z -> 16:44:16Z; remainder = fixes, verification, records)
- **Started:** 2026-11-16T15:27:24Z
- **Completed:** 2026-11-16T16:52:09Z
- **Tasks:** 3
- **Files modified:** 2 (both new: scripts/bench/merge_characterize.py, 11-LADDER-RESULTS.json)

## Accomplishments

- **D-07/D-08/D-09 satisfied in one live session:** the pinned two-point ladder (N=3,500,000 and N=14,000,000 reads per slice, seed 4242) ran at both k with BOTH tools on the same slice pairs, each side through the complete prepare -> count -> merge chain — the first live exercise of the slice-provisioning + prepare-stage logic on real data (D-08)
- **Exact cross-tool count parity at every rung** (first evidence of its kind at ladder scale): 10% k=21 both tools 199,722,642/454,310,397 and 199,764,725/454,311,750; 10% k=31 both 227,322,410/419,281,928-class; 40% k=21 both 461,344,902/461,485,792-class; 40% k=31 both 557,446,677/557,610,429-class (identical distinct AND total per part per k)
- **Slice-scale -s derivation exercised live per D-04** (derive_hash_size from measured per-part Distinct): 500M at the 10% rung (both k), 1G at the 40% rung (both k), occupancy recorded per rung; no auto-grow anywhere
- **Merge measurements recorded (wall, peak, output bytes, merged Distinct, cache_state, route):** rustkmer 15.23 s/16.02 s -> 34.88 s/44.87 s (10%->40%; peak 1.60-2.33 GB; outputs 6.37-15.24 GB), jellyfish 25.34 s/27.59 s -> 51.76 s/66.80 s (peak 6.78-6.82 MB — the milestone-pinned ~6.8 MB streaming comparator, now measured live at two scales); merged Distinct identical across tools at every rung (318,506,459 / 372,965,505 / 612,991,988 / 762,068,515)
- **Gates executed before record acceptance per PARITY-GATE.md:** assert_merge_parity green at all 4 rungs (Totals conservation + Distinct union, sum-of-counts definition); the dump-vs-dump deep leg GREEN at both 10% rungs (per-k-mer exact identity on 318.5M and 373.0M entries — 637M/746M lines normalized+sorted+compared through the streaming form); zero-entry protection armed at every count/merge
- **Slope summary for Phase 12 + D-10 (Task 3):** wall-per-entry slopes — jellyfish 8.97e-8 (k=21) / 1.008e-7 (k=31) s/entry, rustkmer 6.67e-8 / 7.41e-8 — ALL FOUR LINEAR (40%/10% wall-per-entry ratios 1.061/1.185/1.190/1.371, far under the 2x flag); bytes-per-entry measured (.rkdb ~20.0 B/entry as the format constant predicts; .jf exactly 10.000 B/entry at k=21 and 12.000 at k=31, matching 11-05's full-scale anchors); extrapolated full-scale merge walls under the two-point linear model with the MBENCH-04 backstop caveat: rustkmer 53.8 s (k=21) / 73.4 s (k=31), jellyfish 77.3 s / 105.5 s
- **Disk hygiene (T-11-14):** GiB-scale scratch (peak ~60 GB at the 40% rung) lived at /tmp/rustkmer-phase11/ladder (outside the repo, refuse_repo_root enforced), was cleaned after evidence, and scratch_cleaned=true is recorded in the evidence document; zero artifacts landed in the repo tree

## Task Commits

Each task was committed atomically:

1. **Task 1: merge_characterize.py — rung provisioning, chain runner, slope fit** - `12908f2` (feat)
2. **[Rule 3 fix] free_bytes probes nearest existing ancestor** - `f9cbf9b` (fix)
3. **[Rule 3 fix] deep dump-vs-dump gate runs the PARITY-GATE.md §4 streaming form** - `aa3390f` (fix)
4. **Task 2: Execute the ladder on real data — evidence JSON committed** - `2e1a16e` (docs)
5. **Task 3: summary finalized + verified** - verification-only: --run had already written the complete summary block; `--summarize` recompute was byte-identical (no JSON diff to commit)

**Plan metadata:** committed with STATE.md/ROADMAP.md updates (docs: complete characterization ladder plan)

## Files Created/Modified

- `scripts/bench/merge_characterize.py` - NEW: the ladder runner (RUNGS/KS constants, provision_rung_slices via reservoir_slice with sha-verified reuse, run_rung full chain with gates, measured_run with stderr-retained /usr/bin/time parsing via bench.parse_time_output, route_from_stderr, fit_slope, build_summary, streaming dump_vs_dump_equal_streaming, evidence-JSON I/O with upsert + incremental writes, --run/--summarize CLI)
- `.planning/phases/11-merge-characterization-harness-prep/11-LADDER-RESULTS.json` - NEW: committed evidence document (kind merge-characterization-ladder, schema_version 1; 4 rung records with slices/counts/merges/gates + summary block; scratch_cleaned true)

## Decisions Made

- **Deep gate at ladder scale = the written spec's streaming form** (in merge_characterize.py, bench.py untouched): the 10% rung measured ~200M distinct per part (3.5M reads) -> 318.5M/373.0M merged lines per side; bench.dump_vs_dump_equal's in-process normalize+sort would need ~120-150 GB of Python heap (OOM risk on this 128 GB host with swap already 82% committed). PARITY-GATE.md §4's original pipeline — dump, strip '#', fail-loud normalize to "kmer<TAB>count", LC_ALL=C external sort (-T workdir), exact compare — runs the same legs streaming. Byte order is identical to the in-process variant (the 11-04 equivalence argument, realized literally). Positive/negative/empty semantics smoke-proven before the live run
- **One measured rep per merge per rung point** (8 measured merges): the D-07 two-point design takes its slope between rungs; within-rung CV is not this ladder's deliverable
- **Honest route + cache labels everywhere:** route not-reported at all 8 merges (default rustkmer route prints no route line; no Rust changes allowed), cache_state unavailable at all 8 (sudo -n purge unavailable — the established honest protocol), RSS recorded as context only, never as a decision axis (prohibition honored)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] free_bytes crashed on a fresh (nonexistent) scratch root**
- **Found during:** Task 2 (first --run attempt, aborted at startup)
- **Issue:** os.statvfs requires an existing path; ensure_free_space(scratch_root) ran before run_rung created the scratch dir, so the very first rung died with "[Errno 2] No such file or directory: '/private/tmp/rustkmer-phase11/ladder'"
- **Fix:** free_bytes probes the nearest existing ancestor (same volume, same answer)
- **Files modified:** scripts/bench/merge_characterize.py
- **Verification:** free_bytes/ensure_free_space on a nonexistent nested path OK; live run proceeded past the guard
- **Committed in:** f9cbf9b

**2. [Rule 3 - Blocking] deep dump-vs-dump gate not runnable at measured ladder scale via bench's in-process comparator**
- **Found during:** Task 2 (second --run attempt — deliberately stopped BEFORE the gate could OOM the host)
- **Issue:** the 10% rung's measured slice counts (~200M distinct per part) imply ~318-373M lines per merged-dump side; bench.dump_vs_dump_equal normalizes both dumps in-process (Python lists of per-line strings + in-process sort) — ~120-150 GB heap at that scale, an OOM/swap-thrash risk the run was not allowed to reach
- **Fix:** implemented dump_vs_dump_equal_streaming in merge_characterize.py per PARITY-GATE.md §4's original pipeline (fail-loud awk normalization — malformed/non-integer/comments-only-empty all raise naming the line; LC_ALL=C external sort with -T workdir; streaming compare naming the first differing sorted line pair or the length mismatch); run_rung's deep leg calls it; bench.py untouched; semantics smoke-proven (positive equality, altered-count mismatch named, comments-only side loud) before relaunch
- **Files modified:** scripts/bench/merge_characterize.py
- **Verification:** smoke tests (awk branch checks + tiny rkdb/jf round-trip positive + tampered negative) all pass; live deep gate green at both 10% rungs on 318.5M/373.0M-entry dumps
- **Committed in:** aa3390f

---

**Total deviations:** 2 auto-fixed (both Rule 3 blocking; no scope creep beyond merge_characterize.py)
**Impact on plan:** both fixes were prerequisites for the ladder to run at all/at scale; the plan's gate semantics are fully preserved (executed per the written spec's own text).

## Issues Encountered

- **Attempt 1 (aborted at startup):** the statvfs crash above — no measurements taken, no evidence written.
- **Attempt 2 (deliberately stopped):** after rung-1 k=21 slice counts measured ~200M distinct per part (far above the ~90-100M planning estimate), the in-process deep gate's memory math became an OOM risk; the run was killed pre-gate (~15:44Z) and the streaming gate built before relaunch. No host instability occurred; partial scratch was removed.
- **Full-suite reds are the documented pre-existing families only:** `python3 -m unittest discover -s scripts/bench/tests -t .` -> Ran 630 tests, failures=2, errors=2, skipped=1. The 2 ERRORs + 1 FAIL are the test_phase10_verdict.py archived-path family (`.planning/phases/10-benchmark-verdict/` moved to `.planning/milestones/v2.0-phases/` by 97c497c; retarget documented since 11-01 in deferred-items.md and STATE.md); the second FAIL is `test_pre_engine_n_plus_one_stub_is_measured_red`, the STATE.md-documented ~50% macOS `sample`-race flake (suspected-flake-first per STATE.md line 74). Zero reds touch this plan's files. Out of scope per the deviation rules' scope boundary.
- **Wall-time note:** slice provisioning is python-bound (~5 min per 3.5M-read slice on the live run; the first attempt's ~1 min pace had a warm FS cache). Slices are reused across k within a scale point via sha256-verified reuse, so each scale point provisions once.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Ready for 11-07 (disk-floor derivation + dress rehearsal):** 11-LADDER-RESULTS.json's summary block carries exactly what the D-10 formula consumes — measured merge-output sizes at two scales (largest single-arm transients: .rkdb 15.24 GB / .jf 9.14 GB at the 40% rung), the fitted wall-per-entry slopes, the linearity verdicts (all linear), and the extrapolated full-scale merge walls with the MBENCH-04 backstop caveat named
- **Ready for Phase 12 scheduling:** expected full-scale merge wall per tool-k now exists (rustkmer 53.8/73.4 s, jellyfish 77.3/105.5 s under the two-point linear model, unflagged); MBENCH-04's predicted-vs-measured check at full scale remains the backstop (D-07)
- **rustkmer-side scaling behavior (D-09's second purpose):** no route lines reported at any scale, peaks stayed at 1.6-2.3 GB with outputs to 15.24 GB, wall-per-entry ratio 1.19-1.37 between rungs — no spill/route-switch signal at ladder scale
- MBENCH-01: this plan's ladder portion rides the requirement already marked complete by 11-05; no new requirement IDs introduced

---
*Phase: 11-merge-characterization-harness-prep*
*Completed: 2026-11-16*

## Self-Check: PASSED

All created files exist on disk (scripts/bench/merge_characterize.py, 11-LADDER-RESULTS.json, 11-06-SUMMARY.md); all task commits (12908f2, f9cbf9b, aa3390f, 2e1a16e) and the metadata commit (dbbb668) are ancestors of HEAD; commits measured 4 from the persisted plan ledger (gsd-plan-head-before-11-06) at SUMMARY-write time, plus the metadata commit; plan_head_after (2e1a16e) was HEAD at SUMMARY write; ladder scratch confirmed removed from disk; stub-pattern scan over both created files found zero matches.
