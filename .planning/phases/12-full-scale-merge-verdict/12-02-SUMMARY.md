---
phase: 12-full-scale-merge-verdict
plan: 02
subsystem: benchmarking
tags: [bench-harness, full-scale-session, merge-verdict, parity-gate, counterbalanced-protocol, exit-code-contract, mechanical-renderer, no-invest]

# Dependency graph
requires:
  - phase: 12-full-scale-merge-verdict (plan 12-01 + 12-04)
    provides: scripts/bench/phase11.py five stages (revalidate/parity/timed/verdict/render), doc layouts the gates read, 0/1/2 exit-code contract
  - phase: 11-merge-characterization-harness-prep
    provides: 8 parity-validated input artifacts + manifest, union anchors, ladder predictions + caveat, disk floor + budget constants, binary sha256 tripwires
provides:
  - 12-REVALIDATE.json — round-0 gate record (anchors exact both k, binary identities, 282 GiB budget vs df sample)
  - 12-PARITY-K21.json / 12-PARITY-K31.json — three-way parity evidence, all legs green incl. the full-scale streaming deep legs
  - 12-RESULTS-FULL-K21.json / 12-RESULTS-FULL-K31.json — schema-v1 timed results, 3 arms x 3 counterbalanced reps, honest cache_state/route
  - 12-VERDICT.json — overall YES / decision NO-INVEST / exit_code 0, rule verbatim
  - 12-MERGE-REPORT.md — mechanically rendered MBENCH-04 report (byte-stable)
  - 12-RENDER-PROOF.json — byte-identical re-render proof (in-process + live CLI)
  - THE MILESTONE HEADLINE: rustkmer merge beats jellyfish merge at both k — measured median walls 63.34s vs 88.44s (k=21) and 82.86s vs 114.70s (k=31); verdict exit 0 (NO-INVEST)
affects: [12-03 wrap-up (D-03 artifact cleanup + D-04 benchmark-report rewrite — both consume this plan's committed evidence)]

# Actuals (#2632) — same estimateTokens scale (chars/4 over the realized diff).
actuals:
  tokens: 14146        # 56,584 chars over the realized diff (session code fix + 8 evidence docs) / 4
  tasks: 3
  commits: 4           # MEASURED: git rev-list --count d5ed61c..HEAD

commits: 4
plan_head_before: d5ed61c1460895c41d5a8816ba98c7ea151e6350
plan_head_after: 10c12cfb888e0fa1d21554af021efd71ad83dda4

# Tech tracking
tech-stack:
  added: []           # stdlib-only contract held; no packages, no binary rebuilds (T-12-SC)
  patterns: [live staged session through a pre-registered controller, parity-before-timing held structurally, measured verdict via exit-code contract (no retry on 0/1), findings-recorded-never-smoothed]

key-files:
  created:
    - .planning/phases/12-full-scale-merge-verdict/12-REVALIDATE.json
    - .planning/phases/12-full-scale-merge-verdict/12-PARITY-K21.json
    - .planning/phases/12-full-scale-merge-verdict/12-PARITY-K31.json
    - .planning/phases/12-full-scale-merge-verdict/12-RESULTS-FULL-K21.json
    - .planning/phases/12-full-scale-merge-verdict/12-RESULTS-FULL-K31.json
    - .planning/phases/12-full-scale-merge-verdict/12-VERDICT.json
    - .planning/phases/12-full-scale-merge-verdict/12-MERGE-REPORT.md
    - .planning/phases/12-full-scale-merge-verdict/12-RENDER-PROOF.json
  modified:
    - scripts/bench/phase11.py            # Rule 1: source-fingerprint token matching
    - scripts/bench/tests/test_phase11_verdict.py  # regression test (73 total)

key-decisions:
  - "Verdict recorded from the FIRST observed exit code: 0 = NO-INVEST (overall YES) — never retried, never remapped (Pitfall 10); rustkmer merge median <= jellyfish-merge median at BOTH k"
  - "The Rule 1 fingerprint-lookup fix landed as its own atomic commit BEFORE the session ran — a failed revalidate stage wrote no doc (fail-loud gate behaved as designed), and no partial evidence ever landed"
  - "Parity k=21 ran strictly before k=31 (deletion sequencing halves the deep-gate transient peak); timed k=21 before k=31; every stage committed before the next started"
  - "cv_warning on the k=31 merge arm (rep-0 101.51s vs 82.49-82.86s rounds 1-2, CV 12.2% > 10%) recorded as a finding — the median is robust and even the outlier rep beats the jellyfish median; no re-run"
  - "Predicted-vs-measured deltas (~+9-11s absolute on all four rows, +8.7% to +17.6% relative) recorded as findings reconciled against the ladder linearity caveat — scheduling inputs, not a re-run reason; notably the parity warmup walls landed much closer to predictions (-6.4% to +3.1%)"

requirements-completed: [MBENCH-03, MBENCH-04]  # copied from plan frontmatter; shared with 12-03 whose SUMMARY does not exist yet — mark-complete via the shared-ID gate (requirements.ready-ids)

coverage:
  - id: D1
    description: "Round-0 gate: re-hashed all 8 artifacts + 2 source fingerprints, binary identity tripwires green (4539b893.../e99c676b...), anchors EXACT at both k (8967099203 / 8275694030), computed session budget 282 GiB vs 363.53 GiB free, df sample recorded"
    requirement: MBENCH-03
    verification:
      - kind: command
        ref: "anchors gate: python -c '...12-REVALIDATE.json...' prints True (anchors['21'].exact and anchors['31'].exact)"
        status: pass
      - kind: command
        ref: "stage stdout: PHASE11 ROUND0 anchors=exact budget_gb=282 artifacts=4, exit 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "Full-scale three-way parity at BOTH k before any timed rep: warmup-marked merges per tool, leg1-aggregate-conservation, leg2-recount-vs-merged (independent recount over part_001+part_006 as ONE input list, EXACT anchor pre-check, streaming per-k-mer diff), leg3-dump-vs-dump (streaming) — all green, transients deleted in sequence"
    requirement: MBENCH-03
    verification:
      - kind: command
        ref: "parity gate: legs_executed == [leg1-aggregate-conservation, leg2-recount-vs-merged, leg3-dump-vs-dump] and anchors.exact and all warmup merges — prints parity-ok"
        status: pass
      - kind: command
        ref: "stage stdout: PHASE11 PARITY k=21 legs=3/3 anchors_exact=true recount=identical (and k=31), exit 0 both"
        status: pass
    human_judgment: false
  - id: D3
    description: "Timed stage at both k: 3 arms (merge/merge-t1/jellyfish-merge) x exactly 3 counterbalanced reps (rotation schedule round r starts at arm r mod 3), per-rep cache purge + disk re-check + /usr/bin/time wall + route attribution; cross-rep conservation enforced; medians via reduce_arm; schema-v1 docs pass validate_schema"
    requirement: MBENCH-03
    verification:
      - kind: command
        ref: "results gate: validate_schema + phase==12 + arms==[merge,merge-t1,jellyfish-merge] + reps==3 + route/cache_state per rep — prints results-ok exit_code=0 decision=NO-INVEST"
        status: pass
      - kind: command
        ref: "schedule check (SUMMARY extraction): rounds rotated [[merge,merge-t1,jellyfish-merge],[merge-t1,jellyfish-merge,merge],[jellyfish-merge,merge,merge-t1]] at both k"
        status: pass
    human_judgment: false
  - id: D4
    description: "Verdict via the 0/1/2 exit-code contract: pure comparison of recorded medians; observed exit code 0 == recorded exit_code 0; overall YES -> decision NO-INVEST; rule verbatim in doc + every per-k block; t1 excluded (scaling only)"
    requirement: MBENCH-03
    verification:
      - kind: command
        ref: "observed verdict-stage exit: VERDICT_EXIT=0 with stdout PHASE11 VERDICT k=21 result=YES rustkmer_wall_s=63.34 jellyfish_wall_s=88.44 / k=31 result=YES 82.86 114.7 / overall=YES decision=NO-INVEST exit_code=0"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py (73 passed) — controller contract suite green after the session"
        status: pass
    human_judgment: false
  - id: D5
    description: "Mechanical MBENCH-04 report + byte-identical re-render proof: all sections present (methodology rows incl. merge-t1 pool contract, asymmetry sentence verbatim, entry-rate/byte-rate rows, predicted-vs-measured with the ladder caveat verbatim, parity evidence, RSS-is-context framing); in-process proof byte_identical=true with matching digests; LIVE CLI re-render byte-identical"
    requirement: MBENCH-04
    verification:
      - kind: command
        ref: "live re-render gate: H1==H2 across two independent CLI render invocations — prints re-render-identical (sha256 9adcc892...)"
        status: pass
      - kind: command
        ref: "report gate: 12-RENDER-PROOF.json byte_identical true + digests equal + asymmetry sentence + predicted/caveat + all three arms + entry-rate/byte-rate sections — prints report-ok"
        status: pass
      - kind: command
        ref: "commit gate: both files tracked and clean — prints report-committed"
        status: pass
    human_judgment: false

# Metrics
duration: 6h 47min
completed: 2026-11-17
status: complete
---

# Phase 12 Plan 02: Full-Scale Merge-Verdict Session Summary

**The milestone headline session executed live: round-0 gate green (anchors exact both k), three-way parity green at k=21 and k=31 (all three legs incl. the full-scale streaming per-k-mer deep legs), 3 arms x 3 counterbalanced reps timed at each k, and the verdict recorded as exit 0 / NO-INVEST — rustkmer merge median walls 63.34s (k=21) and 82.86s (k=31) beat jellyfish merge's 88.44s and 114.70s — with the mechanically rendered report byte-identical across independent re-renders**

## Performance

- **Duration:** 6h 47min (02:19:08Z → 09:06:20Z; dominated by the streaming deep legs at ~1.5-1.8 h per k, inside the flagged research A4 uncertainty band; the loud disk guards made the overrun safe)
- **Started:** 2026-11-17T02:19:08Z
- **Completed:** 2026-11-17T09:06:20Z
- **Tasks:** 3 (all `type="auto"`)
- **Files:** 8 evidence docs created, 2 session-code files modified (Rule 1 fix + regression test)

## The Verdict (MBENCH-03 headline)

| k | rustkmer merge median | merge-t1 median (scaling) | jellyfish-merge median | result |
|---|---|---|---|---|
| 21 | **63.34 s** | 62.15 s | 88.44 s | YES |
| 31 | **82.86 s** | 83.39 s | 114.70 s | YES |

**Overall YES → decision NO-INVEST, exit code 0** (observed process exit == recorded `exit_code`; never retried). Ladder predictions (53.8/73.4 s rustkmer, 77.3/105.5 s jellyfish) stay scheduling inputs: all four measured medians ran +8.7% to +17.6% above prediction — recorded as findings, reconciled against the linearity caveat, never smoothed or re-run (Pitfall 9).

## Accomplishments

- **Round-0 gate (12-REVALIDATE.json):** re-hashed all 8 artifacts (~86.74 GiB) + re-fingerprinted the pinned source pair; binary identity tripwires green (rustkmer `4539b893…d023b`, jellyfish `e99c676b…91ee` — ladder attribution held); anchors EXACT at both k (8,967,099,203 / 8,275,694,030); D-12 session budget computed 282 GiB (inputs 87 + parity {k21: 76, k31: 97} + timed 22) vs 363.53 GiB free — floor check passed without override
- **Parity k=21 (12-PARITY-K21.json):** warmup-marked merges (rustkmer 50.42 s, jellyfish 77.30 s, honest `cache_state: unavailable`), Leg 1 aggregate conservation green (distinct 897,266,581 conserved across merge/recount/jellyfish), Leg 2 independent recount over part_001+part_006 as ONE input list — Total exact vs anchor, then per-k-mer streaming diff vs the merged db identical, Leg 3 cross-tool streaming dump-vs-dump identical; transients deleted in sequence (5 recorded deletions)
- **Parity k=31 (12-PARITY-K31.json):** same contract green at k=31 (distinct 1,146,353,600 conserved; warmups 70.37 s / 108.78 s); k=21 strictly before k=31 per the deletion-sequencing plan
- **Timed k=21 (12-RESULTS-FULL-K21.json):** 3 arms x exactly 3 reps under `rotation_schedule` (rounds start at arms 0/1/2), per-rep cache purge + disk re-check + `/usr/bin/time`, route honestly `not-reported` on every rep (matches ladder expectation), cross-rep conservation green, CVs 0.5-2.5% (no warnings)
- **Timed k=31 (12-RESULTS-FULL-K31.json):** same protocol; merge-arm `cv_warning: true` (rep-0 101.51 s vs 82.49-82.86 s in rounds 1-2, CV 12.23% > 10%) — recorded as a finding, never smoothed; even that outlier rep (101.51 s) beats the jellyfish median (114.70 s), so the verdict is robust to it; merge and merge-t1 outputs hash identically per k (`75ddd231…` / `c2b974d9…`) — cross-arm determinism visible in the methodology rows
- **Verdict (12-VERDICT.json):** per-k blocks with the rule verbatim, overall YES, decision NO-INVEST, exit_code 0 == the observed process exit code; merge-t1 recorded under `scaling`, never in the YES/NO computation
- **Render (12-MERGE-REPORT.md + 12-RENDER-PROOF.json):** all MBENCH-04 sections rendered mechanically — per-arm methodology rows (threads/argv/route/output+binary sha256, the t1 pool-contract label), the pre-agreed asymmetry sentence verbatim, entry-rate/byte-rate rows making the 20 vs 10/12 B/entry format asymmetry visible, predicted-vs-measured table with the ladder caveat verbatim, parity evidence lines, RSS-is-context framing; in-process proof `byte_identical: true` with matching digests, and the LIVE CLI re-render check (hash → re-run → hash) proved byte identity `9adcc892…60cc7` at the process level

## Session Findings (recorded, not smoothed)

1. **Predicted-vs-measured deviations (all four rows positive, +9.18 to +11.18 s absolute / +8.7% to +17.6% relative).** The parity warmups landed much closer to predictions (rustkmer −6.4%/−4.1%, jellyfish +0.05%/+3.1%), so the timed-stage shift is consistent with a uniform host-state factor during the timed window rather than a tool-specific effect; the deltas are near-uniform in absolute terms across both tools and both k. Per the ladder caveat (rendered verbatim in the report), the predictions are scheduling inputs and the measured medians are the deliverable — no rep was re-run.
2. **k=31 merge-arm cv_warning (CV 12.23%).** Rep-0 ran 101.51 s vs 82.49/82.86 s in rounds 1-2 (first-round write-back/thermal effect at merge scale). The median is robust; the finding is recorded in the results doc and rendered report; the verdict holds even against the outlier.
3. **`cache_state: unavailable` on all 18 reps and `route: not-reported` on all 18 reps** — the honesty mechanisms operated exactly as designed (sudo purge unavailable; no tool-stated route marker at full scale, matching the ladder's recorded routes).

## Task Commits

Each task was committed atomically:

1. **Rule 1 fix (pre-Task-1 blocker):** `68e2f3e` — source-fingerprint lookup tokenizes the dotted file name (`fix`)
2. **Task 1:** `e9df71a` — round-0 gate + full-scale three-way parity green at both k (`feat`)
3. **Task 2:** `727eba5` — timed stage both k + verdict, observed exit 0 / NO-INVEST (`feat`)
4. **Task 3:** `10c12cf` — mechanical merge-verdict report + byte-identical re-render proof (`docs`)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Source-fingerprint lookup failed on the real recorded path shape**
- **Found during:** Task 1, stage 1 (the round-0 revalidate stage exited 2 on the live manifest)
- **Issue:** `check_source_fingerprints.record_for` matched records via `file_name`/`stem` equality and suffix checks only; the manifest's real paths (`CRR1936095_r1.part_001.fq.gz`) have `Path.stem == "CRR1936095_r1.part_001.fq"` (stem strips only the final `.gz`), so no check matched and the gate raised "manifest predates the pinned part-pair contract". The docstring promised "token-based" matching that was never implemented; unit fixtures used `part_001.fq.gz` names whose stems happen to match — a test-blind-spot, not a data problem (the manifest's source_fingerprints records were correct)
- **Fix:** added `name in file_name.split(".")` to the match conjunction (the dotted-token check), plus regression test `test_real_recorded_path_shape_matches` using the real `CRR1936095_r1.part_NNN.fq.gz` shape
- **Files modified:** scripts/bench/phase11.py, scripts/bench/tests/test_phase11_verdict.py
- **Verification:** suite 73 passed; re-run of the revalidate stage exited 0 with the doc written
- **Commit:** 68e2f3e

**Total deviations:** 1 auto-fixed (Rule 1, in Plan 12-04's session-stage code, blocking this plan's Task 1). **Impact:** none on the evidence — the gate failed loud before any doc was written, the fix is test-pinned, and every session number in the committed docs comes from post-fix stage runs.

## Issues Encountered

- The revalidate stage's first run failed exit 2 (the Rule 1 bug above) — no doc written, no partial state; resolved within Task 1 by the atomic fix commit.
- None otherwise: the parity and timed stages ran clean end-to-end at full scale (the disk guards, parity gates, and conservation checks all held; scratch fully reclaimed — 349 GiB free post-session).

## Known Stubs

None — every committed evidence document carries real measured data from the live session; no placeholder text, no unwired paths.

## Authentication Gates

None — local, offline session over pinned binaries.

## User Setup Required

None.

## Verification (all run at HEAD `10c12cf`)

- Anchors gate: `12-REVALIDATE.json` anchors exact both k → `True`
- Parity gate (both k): `parity-ok` — legs == [leg1-aggregate-conservation, leg2-recount-vs-merged, leg3-dump-vs-dump], anchors.exact, warmup-marked merges
- Commit gates: `parity-committed`, `report-committed`
- Results gate: `results-ok exit_code=0 decision=NO-INVEST` — validate_schema + phase 12 + 3 arms + reps 3 + route/cache_state per rep; verdict doc consistent (exit_code == 0 == observed exit)
- Contract suite: `.venv313/bin/python -m pytest scripts/bench/tests/test_phase11_verdict.py -q` → **73 passed**
- Full harness suite: `python3 -m unittest discover -s scripts/bench/tests -t .` → **Ran 717 tests … OK (skipped=1)** — zero new failures (the +1 vs pre-session is this plan's regression test; the skip is the pre-existing flake-guard)
- Live re-render gate: `re-render-identical` (two independent CLI invocations, sha256 `9adcc892…`)
- Report gate: `report-ok` (proof byte_identical + all MBENCH-04 sections present)

## Decisions Made

See `key-decisions` — headline: the verdict was recorded from the first observed exit code (0/NO-INVEST, no retry); the Rule 1 fix landed before the session so every committed number is post-fix; findings (prediction deltas, cv_warning, honest labels) are recorded in evidence, never smoothed.

## Next Phase Readiness

- Ready for 12-03 (wrap-up): its preconditions are met — verdict evidence (report + results JSONs + exit-code record) is committed, so D-03 artifact deletion (~86.74 GiB under `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/`) and D-04's one-time rewrite of `docs/benchmark-report.md` (transcribed from the rendered report, banner removed) can proceed. The scratch dir `/Users/forrest/Data/data/illumina/CRR1936095-phase12-scratch/` is already empty.
- MBENCH-03/MBENCH-04 remain formally open until 12-03's SUMMARY lands (shared-ID gate — both IDs are declared by 12-03 as well).
- The NO-INVEST verdict means MBF-01 (flag sweep) stays deferred per the ROADMAP Note.

---
*Phase: 12-full-scale-merge-verdict*
*Completed: 2026-11-17*

## Self-Check: PASSED

- All 8 evidence documents + SUMMARY verified on disk and git-tracked (12-REVALIDATE.json, 12-PARITY-K21/K31.json, 12-RESULTS-FULL-K21/K31.json, 12-VERDICT.json, 12-MERGE-REPORT.md, 12-RENDER-PROOF.json)
- All 5 commits verified ancestors of HEAD: 68e2f3e (Rule 1 fix), e9df71a (Task 1), 727eba5 (Task 2), 10c12cf (Task 3), fbd6323 (this SUMMARY)
- Measured commits d5ed61c..HEAD at SUMMARY-write: 4 (fix + 3 task commits), +1 SUMMARY docs commit
- Plan-level verification re-run at HEAD: anchors True, parity-ok, results-ok exit_code=0 decision=NO-INVEST, re-render-identical, report-ok, contract suite 73 passed, full suite 717 OK (skipped=1)

