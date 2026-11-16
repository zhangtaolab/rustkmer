---
phase: 11-merge-characterization-harness-prep
plan: 04
subsystem: testing
tags: [python, benchmark-harness, parity-gate, merge, jellyfish, dump-comparator, mbench-02, stdlib-only, unittest]

# Dependency graph
requires:
  - phase: 10-benchmark-verdict (v2.0 milestone)
    provides: committed union anchors (k=21 Total 8,967,099,203 / k=31 Total 8,275,694,030, sum-of-counts), parity-before-timing precedent, stats-JSON reader contract
  - phase: 11-01 (sibling wave 1)
    provides: seven-arm comparison protocol, arm dicts carrying stats-JSON distinct/total, assert_arm_ordering, jellyfish_merge_cmd
provides:
  - .planning/phases/11-merge-characterization-harness-prep/PARITY-GATE.md — the three-way merge parity gate defined in writing BEFORE any timed round trusts it (MBENCH-02)
  - assert_merge_parity in bench.py — aggregate pre-gate (merge Total == jellyfish-merge Total == sum of input Totals; Distinct equality; Distinct >= max input, boundary exact-at-max passes), sum-of-counts definition only
  - dump_vs_dump_equal + normalize_dump_lines in bench.py — the per-k-mer verdict gate: rustkmer dump vs jellyfish dump -c, fail-loud parsing, LC_ALL=C-ordered byte comparison, exact identity required
  - GREEN/RED unit proof of every gate invariant including the exact-boundary pass / one-count-short raise
  - live slice-scale gate proof on real data: gates execute before the results JSON is accepted
affects: [Phase 12 Full-Scale Merge Verdict (gate stage before round 0), Plan 11-06 (ladder rides the same gate), 11-07 (shares MBENCH-02)]

# Actuals (#2632) — pairs with the plan's estimate (55000) to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 7904    # chars/4 over git diff 38706b0..HEAD at SUMMARY time
  tasks: 3
  commits: 3      # MEASURED: git rev-list --count gsd-plan-head-before-11-04..HEAD
plan_head_before: 38706b09a69ebccd35c1691a880da43b18ad2892
plan_head_after: b29dff9c5da81c09932326b1ac0b0b2ff62e6af7

# Tech tracking
tech-stack:
  added: []       # stdlib-only contract preserved (bench.py:25-26); no package installs (T-11-SC N/A)
  patterns:
    - "Gate-as-written-spec: the phase-dir doc is the definition of record; code implements it check-for-check (check names its total_kmers definition per the IN-03 collision)"
    - "Injectable-seam subprocess comparator: dump helpers default at CALL time to module runners, so unit fixtures drive the real normalize/sort/compare logic binary-light"
    - "Fail-loud parsing as tamper defense (T-11-09): malformed or empty dump lines raise naming the offending content — never a vacuous pass"

key-files:
  created:
    - .planning/phases/11-merge-characterization-harness-prep/PARITY-GATE.md
  modified:
    - scripts/bench/bench.py
    - scripts/bench/tests/test_merge_arms.py

key-decisions:
  - "Gate wiring order in run_bench: count-parity block -> assert_merge_parity -> dump_vs_dump_equal -> results doc write/accept; all guarded on the jellyfish-merge arm (comparison runs, not --skip-merge)"
  - "Comparator sorts in-process with Python str ordering (byte-identical to LC_ALL=C over the pure-ASCII dump alphabet) instead of shelling out to sort; dump output goes via workdir files (rustkmer dump -o / jellyfish dump -c stdout redirect) and is unlinked after reading"
  - "Live slice proof head-provisions 200k reads from the first sorted parts — functional gate proof only; the pinned part_001+part_006 pair and union anchors bind full-scale runs through the prepare manifest (plan-stated)"
  - "MBENCH-02 left unmarked in REQUIREMENTS.md: shared with 11-07 (no SUMMARY yet), blocked by the shared-ID ready gate (#2388) — 11-07 finishing will re-evaluate"
  - "normalize_dump_lines preserves the count text verbatim (no int reformatting) so byte comparison stays honest to both tools' decimal output"

patterns-established:
  - "Boundary-exact gate semantics unit-pinned: merged Distinct exactly at max input Distinct passes; one count short raises (GREEN/RED pair)"
  - "Repr-aware test assertions: dump lines in gate errors are repr-escaped, so regexes match the literal backslash-t (r'...\\\\t...'), not a tab"

requirements-completed: []  # MBENCH-02 declared but blocked by the shared-ID gate until 11-07 completes

# Coverage metadata (#1602) — one entry per shipped deliverable.
coverage:
  - id: D1
    description: "PARITY-GATE.md exists in the phase dir before any timed round uses the gate: scope, three legs, per-check total_kmers definition naming, committed union anchors, canonicality assertion, saturating-add scope note, Phase 12 execution-order requirement"
    requirement: MBENCH-02
    verification:
      - kind: other
        ref: "command: Task 1 content gates (sum-of-counts x2, anchors 8967099203/8275694030, LC_ALL=C, record count) — all green; committed a2ff0ed"
        status: pass
    human_judgment: false
  - id: D2
    description: "assert_merge_parity raises before any median is trusted on each violated invariant; at the exact boundary (merged Distinct == max input Distinct) it passes and one count short it raises"
    requirement: MBENCH-02
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_merge_arms.py#TestAssertMergeParity (GREEN conserved + GREEN boundary, RED rustkmer-total / jellyfish-total / distinct-inequality / below-max)"
        status: pass
    human_judgment: false
  - id: D3
    description: "dump-vs-dump comparator demands exact per-k-mer equality after LC_ALL=C-ordered normalization; empty, missing, and malformed dump inputs all fail loud (never a vacuous pass)"
    requirement: MBENCH-02
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_merge_arms.py#TestNormalizeDumpLines + #TestDumpVsDumpEqual (equal pair passes; altered count fails naming the pair; length mismatch fails; empty side fails loudly)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every conservation Total flows from the stats-JSON sum-of-counts reader on the arm dicts — the header record-count field is never read by any gate check"
    requirement: MBENCH-02
    verification:
      - kind: other
        ref: "code review: assert_merge_parity reads only arm-dict total_kmers/distinct_kmers populated by stats()/jellyfish_stats() in run_comparison_protocol (bench.py); grep confirms no header-field read in gate code"
        status: pass
    human_judgment: false
  - id: D5
    description: "Live slice-scale proof on real data: three-way aggregate parity green (Total 51,936,393 == 25,967,840 + 25,968,553; Distinct 29,730,885 equal across tools), dump-vs-dump deep gate green, all executed before /tmp/p11-parity-proof.json was accepted"
    requirement: MBENCH-02
    verification:
      - kind: integration
        ref: "command: python3 scripts/bench/bench.py --mode slice --input /Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split --slice-reads 200000 --k 21 --reps 2 --self-check --out /tmp/p11-parity-proof.json (exit 0; merge, jellyfish-merge, merge-t1 arms present)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Full harness suite green on every module this plan touched; only the documented pre-existing test_phase10_verdict.py archived-path reds + 1 opt-in skip remain"
    requirement: MBENCH-02
    verification:
      - kind: unit
        ref: "command: python3 -m unittest discover -s scripts/bench/tests -t . (630 tests; failures=1, errors=2, skipped=1 — all pre-existing, identical to the 11-01/11-02 records)"
        status: pass
    human_judgment: false

# Metrics
duration: 15 min
completed: 2026-11-16
status: complete
---

# Phase 11 Plan 04: Three-Way Merge Parity Gate Summary

**Three-way merge parity gate defined in writing (PARITY-GATE.md), implemented in bench.py as an aggregate pre-gate plus a per-k-mer dump-vs-dump verdict gate, GREEN/RED-proven by unit tests, and proven live at slice scale on real data before any median was trusted (MBENCH-02)**

## Performance

- **Duration:** 15 min
- **Started:** 2026-11-16T13:57:00Z
- **Completed:** 2026-11-16T14:12:00Z
- **Tasks:** 3
- **Files modified:** 3 (1 new doc, 2 code/test)

## Accomplishments
- PARITY-GATE.md written in the phase dir BEFORE implementation: scope, the three legs (fast pre-gate anchored on the committed Phase-10 union Totals 8,967,099,203 k=21 / 8,275,694,030 k=31 as sum-of-counts; independent-recount ground truth; cross-tool dump-vs-dump verdict), per-check total_kmers definition naming (IN-03 collision), canonicality assertion, saturating-add scope note, and the Phase 12 execution-order requirement (gate stage before round 0)
- `assert_merge_parity` + `normalize_dump_lines` + `dump_vs_dump_equal` implemented in bench.py per the written spec; wired into run_bench after the count-parity block and before any results doc is accepted; merge-t1 self-check extended to the same conservation invariants as merge
- All gate invariants GREEN/RED unit-proven (14 new tests): each violated aggregate invariant raises with the sum-of-counts definition named; the exact-boundary case (merged Distinct == max input Distinct) passes and one count short raises; malformed, empty, and length-mismatched dump inputs all fail loud
- Live proof on real data at slice scale (200k reads, k=21, reps=2): three-way aggregate parity green (merge == jellyfish-merge Total 51,936,393 == count-A 25,967,840 + count-B 25,968,553; Distinct 29,730,885 equal), dump-vs-dump deep gate green, all executed before the results JSON was written

## Task Commits

Each task was committed atomically:

1. **Task 1: PARITY-GATE.md — gate defined in writing before implementation** - `a2ff0ed` (docs)
2. **Task 2: assert_merge_parity + dump-vs-dump comparator + GREEN/RED tests** - `f4d0a07` (feat)
3. **Task 3: deep gate wired before results acceptance + live slice proof** - `b29dff9` (feat)

## Files Created/Modified
- `.planning/phases/11-merge-characterization-harness-prep/PARITY-GATE.md` - NEW: the gate's definition of record (three legs, definition naming, canonicality assertion, scope conditions, Phase 12 execution order)
- `scripts/bench/bench.py` - assert_merge_parity, normalize_dump_lines, dump_vs_dump_equal (+ injectable dump seams), run_bench wiring, merge-t1 self-check extension
- `scripts/bench/tests/test_merge_arms.py` - TestAssertMergeParity (6), TestNormalizeDumpLines (4), TestDumpVsDumpEqual (4)

## Decisions Made
- Comparator sorts in-process with Python str ordering — byte-identical to LC_ALL=C over the pure-ASCII k-mer/digit/tab alphabet — instead of shelling out to `sort`; documented in the function docstring and PARITY-GATE.md (satisfies the plan's LC_ALL=C verification alternative)
- Dump output goes through workdir files (rustkmer dump `-o`; jellyfish dump -c stdout redirect), unlinked after reading — avoids giant stdout pipes and leaves no scratch behind
- `normalize_dump_lines` preserves count text verbatim (no int reformatting) so byte comparison stays honest to both tools' decimal output
- MBENCH-02 not marked complete in REQUIREMENTS.md: it is shared with 11-07 (no SUMMARY yet) and the shared-ID ready gate blocks it (#2388) — correct, since MBENCH-02's full-scale execution also belongs to Phase 12
- Live proof uses head provisioning from the first sorted parts (plan-stated: functional gate proof only; the pinned pair and union anchors bind full-scale runs via the prepare manifest)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- In-task (never committed broken): the mismatch-report test regex initially matched a literal tab (`\t` interpreted by the regex engine) while the gate error repr-escapes dump lines to a literal backslash-t — fixed the pattern to `\\t` before the Task 2 commit; suite green after
- Full suite shows the same 3 pre-existing `test_phase10_verdict.py` archived-path reds (`.planning/phases/10-benchmark-verdict/` moved to `.planning/milestones/v2.0-phases/` by `97c497c`) + 1 opt-in venv skip documented in 11-01/11-02 and deferred-items.md — identical counts to before this plan (630 tests now, +14 new, all green); out of scope per the deviation rules' scope boundary
- Live proof run took ~4.5 min (16 protocol runs with 5 s cooldowns) and was executed as a background command; exit 0, no parity/dump RuntimeError text in stderr

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Ready for 11-05 (full-scale artifact builds): the gate spec now exists in writing and its implementation is proven live at slice scale, so the dress rehearsal (11-06/11-07) and Phase 12 inherit a check-for-check-verified gate
- Phase 12 requirement recorded in PARITY-GATE.md §7: the gate stage runs BEFORE round 0 of the full-scale session; at full scale the deep leg runs inside Phase 12's protocol (MBENCH-02/03 split)
- MBENCH-02 will be marked complete when 11-07 (its co-declarer) produces its SUMMARY

---
*Phase: 11-merge-characterization-harness-prep*
*Completed: 2026-11-16*

## Self-Check: PASSED

All created files exist on disk (PARITY-GATE.md, bench.py, test_merge_arms.py; live proof JSON at /tmp/p11-parity-proof.json); all task commits (a2ff0ed, f4d0a07, b29dff9) are ancestors of HEAD; commits measured 3 from the persisted plan ledger (gsd-plan-head-before-11-04); plan_head_after (b29dff9) matches HEAD at self-check time.
