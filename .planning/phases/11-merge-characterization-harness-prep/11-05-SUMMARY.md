---
phase: 11-merge-characterization-harness-prep
plan: 05
subsystem: measurement-infrastructure
tags: [benchmark-harness, prepare-inputs, jellyfish, rkdb, full-scale-artifacts, manifest-revalidation, d01, d04, parity-pregate, mbench-01]

# Dependency graph
requires:
  - phase: 11-02
    provides: scripts/bench/prepare_inputs.py stage (build --stage rkdb|jf, derive_hash_size, reconcile_anchors, refuse_repo_root, manifest/revalidate verbs)
  - phase: 10-benchmark-verdict (v2.0 milestone)
    provides: committed union anchors (8,967,099,203 k=21 / 8,275,694,030 k=31 sum-of-counts) and source fingerprints the build reconciles against
provides:
  - /Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/ — all 8 full-scale merge input artifacts (part_001/part_006 × .rkdb/.jf × k=21/31) + manifest.json (schema_version 1, stage: complete), built by the Plan 11-02 stage with automatic sha256+Total+command-line provenance (D-01/D-03/D-04)
  - First-ever per-part Distinct measurements (664.6–832.1M) and the first live green of the parity pre-gate union-anchor reconciliation at both k
  - Derived and human-approved jellyfish -s per k-pair (1G @ k=21, 2G @ k=31) with measured occupancy — research assumption A4 closed, research Open Question 1 closed
  - .planning/phases/11-merge-characterization-harness-prep/11-PREPARE-RECORD.md — the recorded derivation evidence that is the inputs term of Plan 11-07's disk-floor derivation (D-10)
affects: [Plan 11-06 (ladder), Plan 11-07 (floor derivation + dress rehearsal), Phase 12 (round-0 manifest revalidation)]

# Actuals (#2632) — pairs with the plan's estimate (35000) to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 3050    # chars/4 over git diff gsd-plan-head-before-11-05..HEAD (record-only repo diff; the ~87 GiB artifact builds live outside the repo by D-03)
  tasks: 3
  commits: 3      # MEASURED: git rev-list --count gsd-plan-head-before-11-05..HEAD
plan_head_before: 811e1825592939ee7f55bedd4f86eb19acd65db6
plan_head_after: 7029c7de1c2310747592d4c89cf920a97e61039c

# Tech tracking
tech-stack:
  added: []       # zero installs — existing pinned binaries only (rustkmer 0.5.0 release, jellyfish 2.3.1); T-11-SC N/A
  patterns:
    - "Checkpoint-before-irreversible-spend: derived -s + measured budget presented at the decision gate before any .jf build; auto-mode auto_select honored with premise verified against disk reality"
    - "Estimate superseded by measurement at the gate: D-01's ~70 GiB replaced by the measured 86.74 GiB with the projection band recorded before the spend"
    - "Post-write disk sampling: df re-read after APFS settles — a transient post-write accounting dip is not exhaustion (recorded in the evidence doc)"

key-files:
  created:
    - .planning/phases/11-merge-characterization-harness-prep/11-PREPARE-RECORD.md
  modified: []
  # outside the repo (D-03, intentionally not listed as repo files):
  # /Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/{manifest.json, part_001.k21.rkdb, part_006.k21.rkdb, part_001.k31.rkdb, part_006.k31.rkdb, part_001.k21.jf, part_006.k21.jf, part_001.k31.jf, part_006.k31.jf}

key-decisions:
  - "Task 2 auto-selected option-a per plan auto_select (gate=blocking, AUTO_CFG=true): derived -s approved as computed — 1G for the k=21 pair (occupancy 0.6191), 2G for the k=31 pair (occupancy 0.3875); option-b (one rung up / -s 10G everywhere) rejected as the research anti-pattern (Pitfall 3)"
  - "Budget approved on measured reality, not the estimate: 86.74 GiB actual vs D-01's ~70 GiB (estimate predates per-part Distinct; projection band 85.8-109.8 GiB was recorded before the spend; 359-372 GiB free throughout)"
  - "A4 closed: per-part -s is derived, not 10G-everywhere; fairness carried by the k-pair hash-size equality precondition (identical -m/-s/-C) plus recorded occupancy, not oversized hashes"
  - "Merge-output occupancy pre-computed for Phase 12/11-07 from the union anchors riding input-0 capacity: k=21 merged 0.836 (above the count-time 0.75 target — the plan's option-a con; PARITY-GATE legs own it at merge time), k=31 merged 0.534"

patterns-established:
  - "Evidence-record pattern (11-PREPARE-RECORD.md): measured tables + arithmetic, not prose — the inputs term of the 11-07 floor formula reads straight from it"
  - "Post-write df re-sampling before any budget decision (APFS transient dip observed and documented)"

requirements-completed: [MBENCH-01]

# Coverage metadata (#1602) — one entry per shipped deliverable.
coverage:
  - id: D1
    description: "All 8 full-scale merge input artifacts exist at the D-03 root, built by the prepare stage (not manually), with automatic provenance"
    requirement: MBENCH-01
    verification:
      - kind: integration
        ref: "command: python3 scripts/bench/prepare_inputs.py revalidate (green, 4 artifacts + 4 jellyfish inputs) + manifest stage=complete + test -f manifest.json (outside repo)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Per-part Totals reconcile exactly with the committed Phase-10 union anchors at both k — first live pre-gate green"
    requirement: MBENCH-01
    verification:
      - kind: integration
        ref: "command: plan verify asserted sums=={21: 8967099203, 31: 8275694030} from manifest.json; reconcile_anchors also enforced mid-build per k"
        status: pass
    human_judgment: false
  - id: D3
    description: "Derived -s per k-pair passed the decision gate before any .jf build; executed -s equals approved -s; occupancy <= 0.75 on all four .jf"
    requirement: MBENCH-01
    verification:
      - kind: integration
        ref: "command: plan Task 3 verify asserted approved-vs-executed -s ({21:'1G',31:'2G'}), hash-size equality per k-pair, occupancy numeric and <=0.75 (max 0.6191)"
        status: pass
      - kind: other
        ref: "gate: checkpoint:decision auto-selected option-a per plan auto_select (gate=blocking, AUTO_CFG=true); premise verified against 359 GiB free before selection; outcome recorded in 11-PREPARE-RECORD.md §7 before Task 3 started"
        status: pass
    human_judgment: true   # the -s + budget approval is the checkpoint's human-equivalent judgment, recorded in the evidence doc
  - id: D4
    description: "Nothing built in this plan landed inside the repo tree; retention (D-02) recorded; zero manual transcription (D-04)"
    requirement: MBENCH-01
    verification:
      - kind: other
        ref: "command: git status --porcelain scripts/bench/ docs/ shows no .rkdb/.jf; every fingerprint/size/total in 11-PREPARE-RECORD.md quoted from stage-written manifest.json or command output"
        status: pass
    human_judgment: false

# Metrics
duration: 63min
completed: 2026-11-16
status: complete
---

# Phase 11 Plan 05: Full-Scale Artifact Builds Summary

**All 8 full-scale merge input artifacts (86.74 GiB) pre-built outside the repo through the Plan 11-02 stage with automatic provenance, per-part Totals reconciling exactly to the committed Phase-10 union anchors at both k (first live pre-gate green), derived-and-approved jellyfish -s per k-pair (1G/2G, occupancy ≤ 0.62), manifest complete and revalidation-green from records alone (D-01/D-02/D-03/D-04)**

## Performance

- **Duration:** 63 min (rkdb stage ~16 min, jf stage ~25 min incl. pre-build identity re-verification, remainder verification + records)
- **Started:** 2026-11-16T14:17:36Z
- **Completed:** 2026-11-16T15:20:53Z
- **Tasks:** 3
- **Files modified:** 1 in-repo (11-PREPARE-RECORD.md, new); 9 files outside the repo (8 artifacts + manifest, D-03)

## Accomplishments
- **D-01 complete:** 4 per-part `.rkdb` (55.75 GiB) + 4 per-part `.jf` (30.98 GiB) built via `prepare_inputs.py build --stage rkdb` then `--stage jf`; manifest `stage: complete`; `revalidate` green re-hashing/re-stat-ing all 8 artifacts
- **Union-anchor reconciliation EXACT at both k** — the parity pre-gate's first live green: part_001+part_006 Total = 8,967,099,203 (k=21) and 8,275,694,030 (k=31), enforced mid-build by `reconcile_anchors` and re-proven post-build from the manifest
- **First-ever per-part Distinct measurements:** 664,641,739 / 664,724,158 (k=21), 832,067,970 / 832,135,175 (k=31)
- **-s decision gate executed before any .jf build** (research Open Question 1 + assumption A4 closed): derived 1G @ k=21 (occ 0.6191) / 2G @ k=31 (occ 0.3875), auto-selected option-a under auto mode with the premise verified against disk reality; executed -s asserted equal to approved -s
- **Budget arithmetic recorded before the spend:** projection band 85.8–109.8 GiB written into 11-PREPARE-RECORD.md §5 before the .jf builds; actual 86.74 GiB (low end of band, +24% over D-01's ~70 GiB estimate — estimate superseded by measurement, as the checkpoint design anticipated)
- **Measured .jf byte economics for the 11-07 floor formula:** exactly 10.000 B/entry at k=21 and 12.000 B/entry at k=31 (6.19 / 4.65 B/slot); merge-output occupancy pre-computed (k=21 merged 0.836, k=31 merged 0.534)
- **D-02/D-03/D-04 satisfied:** retention note recorded (keep until Phase 12 verdict, then cleanup), zero artifacts in the repo tree (git-verified), zero manual fingerprint transcription (every value stage-computed or quoted from the manifest)

## Task Commits

Each task was committed atomically:

1. **Task 1: Build the 4 per-part .rkdb, reconcile union anchors, derive -s + provisional budget** - `812f165` (docs — build executed + record created)
2. **Task 2: DECISION — approve derived -s and disk budget before the .jf builds** - `5c0c274` (docs — checkpoint outcome recorded)
3. **Task 3: Build the 4 per-part .jf with approved -s, record jellyfish info, complete manifest, prove revalidation** - `7029c7d` (docs — jf build executed + record completed)

## Files Created/Modified
- `.planning/phases/11-merge-characterization-harness-prep/11-PREPARE-RECORD.md` - NEW: the recorded derivation evidence (fingerprints, per-artifact tables, anchor reconciliation, -s derivation, budget arithmetic, checkpoint outcome §7, .jf build + final inventory §10–11, retention §9/§12)
- Outside the repo (D-03): `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/` — manifest.json + 8 artifacts (86.74 GiB total)

## Decisions Made
- Task 2 auto-selected **option-a** (plan `auto_select`, `gate="blocking"`, AUTO_CFG=true): approve the derived -s as computed. Premise verified before selection: 359.42 GiB free vs 54.0 GiB high-end projection. Option-b rejected as the research anti-pattern (four per-part `-s 10G` artifacts ≈ hundreds of GiB; merge requires hash-size equality, not any particular size)
- Budget approved on **measured** numbers: D-01's ~70 GiB estimate was superseded by the recorded projection band and then by the actual 86.74 GiB — never overridden, always documented
- Merge-output occupancy treated as a measured 11-07 floor input rather than a surprise: k=21 merged 0.836 rides input-0 capacity above the count-time 0.75 target (the plan's stated option-a con; PARITY-GATE.md Leg-1 + the Phase 12 deep dump-vs-dump leg are the structural checks at merge time)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 3 verify snippet expected `occupancy` inside per-.jf `jellyfish_info` records**
- **Found during:** Task 3 verification
- **Issue:** the plan's verify read `a['jellyfish_info'].get('occupancy')`, but the Plan 11-02 stage deliberately stores occupancy only in `hash_size_plan` — jellyfish 2.3.1 `info` reports only command/where/when/canonical (probed verbatim at 11-02; the stage computes occupancy itself), so the snippet as written would assert `None` and fail on a green build
- **Fix:** corrected the verify to compute per-.jf occupancy from the manifest's own records (`hash_size_plan[k].distinct_per_part[token] / hash_size_plan[k].slots`) with identical fails_when semantics (non-numeric or > 0.75 fails); also asserted approved-vs-executed -s and the fail-loud info keys. No stage, manifest, or artifact change
- **Files modified:** none (verify-command correction only)
- **Verification:** Task 3 verify ran green with the corrected computation (occupancies 0.6190/0.6191/0.3875/0.3875, max 0.6191 ≤ 0.75)
- **Committed in:** n/a (verification-only; the deviation is documented in 11-PREPARE-RECORD.md §11 and here)

---

**Total deviations:** 1 auto-fixed (blocking verify-command mismatch, no code/data change)
**Impact on plan:** none — verification intent (occupancy ≤ 0.75 per .jf) fully enforced.

## Issues Encountered
- **Transient post-write df dip (T-11-11 adjacent):** an intermediate df sample moments after the rkdb build exited read 0.35 GiB free; it recovered to 359.42 GiB within ~2 minutes — no APFS snapshots (`tmutil listlocalsnapshots` empty), no swap growth, no other writer identified. Classified as APFS accounting lag during post-write reclamation. Lesson recorded in 11-PREPARE-RECORD.md §6: re-sample df after writes settle before any budget decision. No data or process was harmed; the .jf builds were launched only after free space was re-confirmed.
- Wall times: rkdb stage ~16 min (4 full-scale counts, 16 threads), jf stage ~25 min including the stage's pre-build .rkdb identity re-verification (re-hash of 55.75 GiB before building on the recorded Distinct values).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Ready for 11-06 (characterization ladder): the stage has now run at full scale; the ladder exercises it on real slices (D-08)
- Ready for 11-07 (floor derivation + dress rehearsal): 11-PREPARE-RECORD.md §5/§10/§11 carry the measured inputs term — .rkdb 55.75 GiB, .jf 30.98 GiB (10.000/12.000 B/entry, 6.19/4.65 B/slot), merged-occupancy projections 0.836/0.534, total 86.74 GiB vs 372.50 GiB free
- Ready for Phase 12 round 0: manifest revalidates from records alone (`revalidate` green post-completion); D-02 retention binds cleanup to the verdict landing
- MBENCH-01: this plan's full-scale build portion is complete on top of 11-01 (arms) + 11-02 (stage) — requirement already marked; no new requirement IDs to mark

---

*Phase: 11-merge-characterization-harness-prep*
*Completed: 2026-11-16*

## Self-Check: PASSED

All created files exist on disk (11-PREPARE-RECORD.md, 11-05-SUMMARY.md, manifest.json outside the repo per D-03); all task commits (812f165, 5c0c274, 7029c7d) are ancestors of HEAD; commits measured 3 from the persisted plan ledger (gsd-plan-head-before-11-05); plan_head_after (7029c7d) matches HEAD at self-check time; stub scan over the plan's touched repo files found no placeholder patterns.
