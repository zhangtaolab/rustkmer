---
phase: 10-benchmark-verdict
plan: 03
subsystem: benchmark-harness
tags:
  - benchmark-verdict
  - full-scale-measurement
  - jellyfish
  - counterbalanced-rounds
  - slice-gate
  - memory-accounting
  - checkpoint

requires:
  - phase: 10-benchmark-verdict
    provides: "10-01: phase10.py controller spine, run_rounds, nested medians, memory model; 10-02: slice-gate stage, py-t16 arm, mechanical renderer"
  - phase: 08-output-pipeline-rkdb-v2-parity
    provides: "rotation_schedule and the validate-before-write controller shape"
provides:
  - "10-slice-gate.json: k=21 pinned-reference gate + k=31 live-parity gate, both split parts fingerprinted"
  - "10-results-full-k21.json: CLI session (`rk-t16`, `rk-t1`, `jf-t16`), 3 counterbalanced reps, exact three-way parity"
  - "10-results-full-k31.json: the same shape at k=31"
  - "Checkpoint-1 report: measured CLI medians, peak memory, parity counts, cache census, Python projection"
affects:
  - 10-04
  - 11

actuals:
  tokens: 3918
  tasks: 3
  commits: 3
  plan_head_before: c80ffd2e95d64ae3867b4904c86ab88832b37fd5
  plan_head_after: d0dcc59b851b1e69a13885751608ac6e5cf173e4

tech-stack:
  added: []
  patterns:
    - "Both split parts are ONE arm: rustkmer gets one `-i p1 p2`, jellyfish one `gzcat p1 p2 | jellyfish` pipeline; every arm records its two-part `inputs` list"
    - "Pre-run artifact written only after every post-arm stats read, the `.rkdb` identity assertion and the scratch deletion succeed; a failed session exits 2 with no destination file"
    - "Per-rep peak memory is `max(rss, phys_footprint)`; `peak_rss_bytes` keeps its raw meaning"

key-files:
  created:
    - .planning/phases/10-benchmark-verdict/10-slice-gate.json
    - .planning/phases/10-benchmark-verdict/10-results-full-k21.json
    - .planning/phases/10-benchmark-verdict/10-results-full-k31.json
  modified: []

key-decisions:
  - "The measured union distinct counts (k=21: 897,266,581; k=31: 1,146,353,600) supersede the research estimate; the Python projection is computed from them and both fit the 110 GiB budget (71.87 GiB / 91.82 GiB)."
  - "The v1.0 k=31 jellyfish slowdown DID reproduce at full scale (median 1380.92 s/rep) although the 5M-read probe showed none; the three reps were kept as measured and no run was re-rolled."
  - "The k=21 preflight stays the research-upper-estimate (1.2 B distinct, PROCEED); it is a projection input, never a measurement, and is labelled as such in the artifact."
  - "Checkpoint 1 states the CLI t16 comparison as a measured YES at both k and the Python surface as PENDING — no Python YES/NO is stated, projected, or implied."

requirements-completed: []

coverage:
  - id: D1
    description: "The slice gate is green on the real dataset: k=21 pinned reference at 229,694,874 / 519,271,168 bound to part_001 dae91042..., k=31 live-parity-only, baseline byte-unchanged"
    requirement: BENCH-V2-02
    verification:
      - kind: other
        ref: "python3 -c artifact assertions on 10-slice-gate.json (plan 10-03 task 1 <automated>) -> 'slice gate OK'"
        status: pass
    human_judgment: false
  - id: D2
    description: "CLI full-scale k=21 over both split parts: three arms, three counterbalanced reps, exact three-way parity, honest per-rep memory, equal .rkdb shas"
    requirement: BENCH-V2-02
    verification:
      - kind: other
        ref: "python3 -c artifact assertions on 10-results-full-k21.json (plan 10-03 task 2 <automated>) -> 'CLI k21 OK distinct=897266581 total=8967099203'"
        status: pass
    human_judgment: false
  - id: D3
    description: "CLI full-scale k=31 over both split parts: same arm/rep/parity discipline, pre-gate re-run green immediately before the stage"
    requirement: BENCH-V2-02
    verification:
      - kind: other
        ref: "python3 -c artifact assertions on 10-results-full-k31.json (plan 10-03 task 3 <automated>) -> 'CLI k31 OK distinct=1146353600 total=8275694030'"
        status: pass
    human_judgment: false
  - id: D4
    description: "Checkpoint 1: the user reviews the measured CLI evidence and selects proceed or hold before the Python arm runs"
    requirement: BENCH-V2-02
    verification: []
    human_judgment: true
    rationale: "A blocking-human decision checkpoint; the selection authorizes or stops the Python full-scale arm (Plan 10-04) and cannot be automated."

duration: 3h20m
completed: 2026-11-13
checkpoint_1_decision: proceed
checkpoint_1_decided: 2026-11-14
status: complete
---

# Phase 10 Plan 03: Slice gate + CLI full-scale sessions at k=21 and k=31

**Both split parts measured as one arm per tool: rustkmer beats jellyfish at the matched 16 threads by 25.7% at k=21 (144.69 s vs 194.85 s) and 9.39x at k=31 (147.08 s vs 1380.92 s), at lower peak memory; the Python surface is measured only by projection and stops at Checkpoint 1 as PENDING.**

## Performance

- **Duration:** ~3 h 20 min of host time (started ~10:00Z, last artifact 13:14Z)
- **Started:** 2026-11-13T10:00:00Z (slice-gate start)
- **Completed:** 2026-11-13T13:14:28Z (k=31 artifact write)
- **Tasks:** 3 of 4 executed (task 4 is the blocking-human checkpoint, awaiting selection)
- **Files created:** 3 (all evidence artifacts; no source/harness/baseline file changed)

## Accomplishments

- The slice gate ran green on the real split directory: k=21 `PARITY OK distinct=229694874 total=519271168` plus `PARITY REFERENCE OK` bound to part_001 `dae91042…` with reference sha256 `9826bd59…`; k=31 a live-parity-only gate at 261,863,892 / 479,271,168. `scripts/bench/baselines/` is byte-unchanged.
- CLI k=21 over the complete r1 set (both split parts in one invocation per arm): `rk-t16` 144.69 s, `rk-t1` 493.86 s, `jf-t16` 194.85 s; exact three-way parity at 897,266,581 distinct / 8,967,099,203 total; rustkmer `.rkdb` sha `75ddd231…` identical at t16 and t1.
- CLI k=31: `rk-t16` 147.08 s, `rk-t1` 474.31 s, `jf-t16` 1380.92 s; exact three-way parity at 1,146,353,600 distinct / 8,275,694,030 total; `.rkdb` sha `c2b974d9…` identical at t16 and t1; the slice gate was re-run green immediately before the stage.
- Every rep records `max(rss, phys_footprint)`; the jellyfish pipeline's footprint line is the ~1 MB shell value while its RSS carries the tool peak, so the max resolves to RSS for those arms.
- Cache state is honest: 18 of 18 measured reps recorded `unavailable` (no sudo purge on this host).
- Scratch databases were deleted after their stats and sha256 were recorded; the data volume is back to 240 GiB free (150 GiB floor).

## Task Commits

Each task was committed atomically:

1. **Task 1: Slice gate (k=21 pinned reference + k=31 live parity)** — `97b3f01` (feat)
2. **Task 2: CLI full-scale session k=21** — `e47f6ca` (feat)
3. **Task 3: CLI full-scale session k=31** — `d0dcc59` (feat)

_Note: Task 4 was the blocking-human checkpoint; the user selected **proceed** on 2026-11-14 and the outcome is recorded below._

## Files Created

- `.planning/phases/10-benchmark-verdict/10-slice-gate.json` — k=21 pinned-reference gate + k=31 live parity; both parts' `{path,size_bytes,sha256}`; binary provenance (commit `c80ffd2`, clean, release).
- `.planning/phases/10-benchmark-verdict/10-results-full-k21.json` — `mode=full`, `session=cli`, k=21, arms `rk-t16`/`rk-t1`/`jf-t16`, 3 reps each, schedule rounds, preflight, fingerprints, provenance.
- `.planning/phases/10-benchmark-verdict/10-results-full-k31.json` — the same shape at k=31.

## Decisions Made

- The measured distinct counts are authoritative; the research projection (0.94–1.2 B at k=21) under-estimated the drop-off — the measured k=21 union is 897.3 M, and k=31 rises to 1,146.4 M (higher k resolves repeats). The Python projection is computed from the measured k=31 count, not from the estimate.
- No rep was re-rolled, no parameter tuned, no gate edited. The k=31 jellyfish slowdown is reported as measured.
- Checkpoint 1 reports the CLI surface as a measured YES at both k, and the Python surface as PENDING.

## Checkpoint 1 — measured CLI evidence (from the committed artifacts)

### Slice gate (`10-slice-gate.json`, committed)

| k | gate | distinct | total | reference |
|---|------|----------|-------|-----------|
| 21 | pinned reference | 229,694,874 | 519,271,168 | sha256 `9826bd59c51e34be520c6fca008aea304fb69232f6887cc808b93c4f49ac8a96`, source part_001 `dae91042…` |
| 31 | live-parity-only | 261,863,892 | 479,271,168 | none (no invented expectation) |

Both parts fingerprinted: part_001 `2,785,381,389 B` sha256 `dae91042…`; part_006 `2,785,388,289 B` sha256 `b197f16c…`.

### CLI full-scale sessions

| k | arm | threads | median wall | per-rep wall (s) | median peak_bytes | CV | verdict input |
|---|-----|---------|-------------|------------------|-------------------|----|---------------|
| 21 | rk-t16 | 16 | **144.69 s** | 145.76 / 143.91 / 144.69 | 43.97 GiB (47,213,854,720 B) | 0.64% | YES |
| 21 | rk-t1 | 1 | 493.86 s | 496.75 / 493.86 / 468.38 | 43.96 GiB | 3.21% | scaling only |
| 21 | jf-t16 | 16 | **194.85 s** | 193.81 / 205.60 / 194.85 | 46.84 GiB (50,297,962,496 B) | 3.30% | YES |
| 31 | rk-t16 | 16 | **147.08 s** | 148.63 / 147.08 / 146.74 | 68.52 GiB (73,577,611,264 B) | 0.68% | YES |
| 31 | rk-t1 | 1 | 474.31 s | 472.57 / 476.29 / 474.31 | 68.51 GiB | 0.39% | scaling only |
| 31 | jf-t16 | 16 | **1380.92 s** | 1377.62 / 1380.92 / 1450.67 | 88.00 GiB (94,494,605,312 B) | 2.94% | YES |

- **Three-way parity:** k=21 — all three arms report distinct 897,266,581 / total 8,967,099,203; k=31 — all three report distinct 1,146,353,600 / total 8,275,694,030. Exact equality, no tolerance.
- **`.rkdb` identity across thread counts:** k=21 `75ddd231b674a6ec…`, k=31 `c2b974d905b98775…` — equal between `rk-t16` and `rk-t1` in both sessions.
- **Peak memory rule:** every rep satisfies `peak_bytes == max(peak_rss_bytes, peak_footprint_bytes)`.
- **CV warnings:** none (all arms below the 10% threshold).
- **Cache census:** 18/18 measured reps `unavailable` (no sudo purge available; the cold-cache criterion is only partially satisfied and the report must say so).
- **Disk:** 240 GiB free after the per-k scratch databases were deleted (150 GiB floor).
- **Host:** other user applications were running throughout (load average 7–17 on 16 cores: WindowServer, magpie, DingTalk, other sessions); no agent-run build, test, or process competed with a measured session. The counterbalanced rotation applies the same background load to every arm.

### Python projection (computed from the MEASURED distinct counts)

| k | measured distinct | projection `86 × distinct` | 110 GiB budget | reading | headroom |
|---|-------------------|---------------------------|----------------|---------|----------|
| 21 | 897,266,581 | 77,164,925,966 B = **71.87 GiB** | 118,111,600,640 B | **PROCEED** | 38.13 GiB |
| 31 | 1,146,353,600 | 98,586,409,600 B = **91.82 GiB** | 118,111,600,640 B | **PROCEED** | 18.18 GiB |

### Surface status at Checkpoint 1

- **CLI surface (t16, the acceptance rule):** measured **YES** at k=21 (144.69 ≤ 194.85, 25.7% faster) and **YES** at k=31 (147.08 ≤ 1380.92, 9.39x faster). A NO would have stood; there is no tolerance band and the t1 arm does not enter the rule.
- **Python surface:** **PENDING.** Plan 10-04 has not run; no Python YES/NO is stated, projected, or implied. Only the projection and its PROCEED reading are reported.
- **KMC3:** BENCH-V2-01 was descoped on 2026-11-13 by user decision; no KMC3 binary was downloaded, installed, or executed. Its absence is intentional.

### Checkpoint 1 outcome — **PROCEED**

**Selection: `proceed`** (recorded 2026-11-14). The user reviewed the measured CLI evidence and authorized Plan 10-04: the Python memory preflight (re-derived from the measured distinct counts), the Python full-scale sessions at k=21 and k=31 (each after a slice-gate re-run), and the verdict + report render.

- Both Python projections are PROCEED from the measured counts (71.87 GiB / 91.82 GiB vs the 110 GiB budget), so the hard OOM gate does not trigger a stop at preflight.
- The Python surface remains **PENDING** until Plan 10-04's sessions produce measured medians; no Python YES/NO is stated here.
- Plan 10-04 may start.

## Deviations from Plan

### Environment

**1. [Worktree base] Fast-forwarded the stale worktree before any edit**
- **Found during:** start-up worktree branch check
- **Issue:** HEAD was `2fc58cb` — a strict ancestor of the expected base `c80ffd2`, clean tree, zero own commits; `.planning/phases/10-benchmark-verdict/` did not exist in the worktree.
- **Fix:** `git merge --ff-only c80ffd2e95d64ae3867b4904c86ab88832b37fd5` before any edit, as the dispatch instructions require. The merge itself changed no files.
- **Files modified:** none by the merge.

**2. [Runtime environment] Built `target/release/rustkmer` from THIS worktree**
- **Found during:** pre-execution environment probing (the worktree had no `target/`)
- **Issue:** the measured binary must come from this tree; symlinking the main checkout's stale `target` would make the provenance (commit/dirty/sha) describe a different tree.
- **Fix:** `cargo build --release --locked` in the worktree (host default toolchain `rustc 1.101.0-nightly`), 37 s, exit 0; binary sha256 `8f38d20c…c87c3d23`, 2,966,832 B, `rustkmer 0.5.0`; tree clean at `c80ffd2`. `target/` is gitignored and was never committed.
- **Files modified:** none (gitignored build output only).

**3. [Ledger location] Plan commit ledger recorded in `/tmp`**
- **Found during:** Task 1 commit
- **Issue:** the worktree sandbox refuses writes into the shared `.git/worktrees/...` directory (same as plan 10-02).
- **Fix:** base recorded at `/tmp/gsd-plan-head-before-10-03` (`c80ffd2`); `commits` measured with the same instrument (`git rev-list --count c80ffd2..HEAD` = 3).

### Measurement reality (no code changed)

**4. [Estimate vs reality] The v1.0 k=31 jellyfish slowdown reproduced at full scale**
- **Found during:** Task 3
- **Issue:** RESEARCH Pitfall 10 said the 5M-read probe showed no k=31 penalty; at full scale `jf-t16` took ~22–24 min/rep (median 1380.92 s = 23.0 min, peak 88.00 GiB) vs 194.85 s at k=21. The k=31 stage took ~2 h 14 min instead of the planned 60–80 min.
- **Fix:** none — the protocol forbids re-rolling or tuning; the numbers are recorded as measured. The CV (2.94%) stayed below the warning threshold.
- **Files modified:** none.

**5. [Estimate vs reality] k=21 measured distinct is below the research projection**
- **Found during:** Task 2
- **Issue:** the research projected 0.94–1.2 B distinct and 68–80 GB peak at k=21; the measured union is 897,266,581 with a 43.97 GiB peak. k=31 rises to 1,146,353,600 distinct.
- **Fix:** none — the preflight stays the labelled `research-upper-estimate` (1.2 B, PROCEED) as designed; the projection basis is never rewritten post hoc.

**6. [Host state] The host was not fully idle**
- **Found during:** every measured session
- **Issue:** five users logged in with CPU-active applications (WindowServer, magpie, DingTalk, other Claude sessions); load average 7–17.
- **Fix:** none possible without killing other users' work. No agent-initiated build, test, or measurement competed with a measured run; the counterbalanced rotation applies the same background noise to every arm. Recorded here and in the checkpoint report.

---

**Total deviations:** 6 documented (3 environment/process, 2 measurement reality, 1 host state). No production source, fixture, baseline, or manifest was modified; no gate was edited to turn green.

## Issues Encountered

- `jellyfish count -s 10G` at k=31 peaks at ~88–94.5 GB (vs ~47 GB at k=21): the 62-bit mer representation doubles per-slot memory and is ~7x slower per rep at full scale. Budget for the Python session in Plan 10-04 must account for a host that just returned from a 94 GB process; memory pressure was 82–94% free between stages.
- The full harness discovery suite was deliberately **not** run: the plan says it runs only after all measured sessions finish and never concurrently with a measurement, and Plan 10-04 still has measured sessions pending.

## Verification

- Task 1 automated verify — passed: `slice gate OK` plus `git status --porcelain scripts/bench/baselines/` empty.
- Task 2 automated verify — passed: `CLI k21 OK distinct=897266581 total=8967099203`.
- Task 3 automated verify — passed: `CLI k31 OK distinct=1146353600 total=8275694030`.
- Scope guardrail — the plan diff touches exactly the three declared artifacts; nothing under `scripts/bench/baselines/`, `src/`, `pyo3/src/`, `tests/fixtures/`, or any manifest/lockfile changed.
- The controller never emits `--size` to rustkmer; the executed rustkmer command carries only `-k/-C/--threads/-o/-i`.
- Every arm's `inputs` list and executed command contain both `part_001` and `part_006`.
- Exit codes were kept raw: slice gate 0, k=21 session 0, pre-gate 0, k=31 session 0.

## Known Stubs

None. No stubbed code was written by this plan.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 10-04 is blocked on Checkpoint 1. If the user selects **proceed**: run `--stage preflight-python --cli-docs <k21> <k31>`, then `--stage python --k 21` and `--k 31` (each after a slice-gate re-run), then `--stage render`. The Python projection is PROCEED at both k (71.87 GiB / 91.82 GiB vs the 110 GiB budget).
- If the user selects **hold**: the phase stops with CLI evidence only; no verdict or report is rendered (the renderer requires four result documents), and the Python surface stays unmeasured at full scale.
- `.venv313` was not needed or created by this plan; the Python surface belongs to Plan 10-04.

---
*Phase: 10-benchmark-verdict*
*Completed: 2026-11-13 (Checkpoint 1 approved 2026-11-14 — proceed)*

## Self-Check: PASSED

- FOUND: .planning/phases/10-benchmark-verdict/10-slice-gate.json
- FOUND: .planning/phases/10-benchmark-verdict/10-results-full-k21.json
- FOUND: .planning/phases/10-benchmark-verdict/10-results-full-k31.json
- FOUND: .planning/phases/10-benchmark-verdict/10-03-SUMMARY.md
- FOUND: 97b3f01 (task 1 slice gate)
- FOUND: e47f6ca (task 2 CLI k=21)
- FOUND: d0dcc59 (task 3 CLI k=31)
