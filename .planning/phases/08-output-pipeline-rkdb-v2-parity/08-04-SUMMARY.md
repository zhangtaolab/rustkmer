---
phase: 08-output-pipeline-rkdb-v2-parity
plan: 04
subsystem: output-pipeline
tags: [rust, output-stage-measurement, byte-identity, thread-scaling, frozen-contract, msrv-clippy, anti-softening, out-01, out-02, out-03]

requires:
  - phase: 08-output-pipeline-rkdb-v2-parity
    provides: "08-01 unstable/parallel sort + streaming write and the immutable pre-change baseline (sorted 18.73 s, sort delta 8.91 s, sorted .rkdb sha256 0976f29c, sorted RSS 17.97 GB)"
  - phase: 07-shared-counting-engine
    provides: "Phase 7 slice scope (k 21, canonical, threads 1/4/16, 4M reads) with per-arm medians 36.92/17.76/23.83 s, RSS 17.96/17.97/17.97 GB, pinned counts 229,694,874/519,271,168, fingerprint 71c6264b"
  - phase: 08-output-pipeline-rkdb-v2-parity
    provides: "08-02 four-arm byte differential and both-consumer sortedness; 08-03 12-cell differential matrix and mutation-RED evidence (VERDICT GREEN)"

provides:
  - "post/phase8_output_stage_post.json — GREEN output-stage verdict persisted with sorted 10.41 s, sort delta 1.70 s, sha256 match, sorted RSS 12.04 GB, full baseline schedule and per-rep cache_state/round/arm_order protocol"
  - "post/phase8_slice_green.json — t1/t4/t16 slice arms at 31.82/10.15/9.31 s and 12.04/12.04/12.05 GB, pinned counts in every arm, input fingerprint 71c6264b"
  - "Three slice .rkdb files sharing the single pre-refactor sha256 0976f29c — byte identity and thread-count independence at 229M-key scale"
  - "phase8_gates_evidence.json — MSRV clippy, full suite, golden tests, harness unittests, rebuilt PyO3 pytest, frozen blob hashes, golden manifest and anti-softening counts"

affects: [09-python-parity, 10-benchmark-verdict]

actuals:
  tokens: 3337
  tasks: 2
  commits: 2
  plan_head_before: 89aff206e358c0811217bc854140b08db5dd8f2b
  plan_head_after: a8cf51d6ee89a385174129ba16269b8047fca1db

tech-stack:
  added: []
  patterns:
    - "The post verdict is exercised through output_stage.py compare itself: the persisted verdict block is the evidence, and a RED verdict would be a defect to fix, never a threshold to move"
    - "Slice-scale byte identity is asserted from the three measured arm databases, not from a re-encode — the files the writer produced are hashed after the timing runs"
    - "The frozen contract is proven from git blobs and greps (format.rs eb0d5bf2, single struct definitions, single header.write_to call, no direct LE serialization) rather than prose"
    - "Anti-softening counts the silencing constructs on the current tree AND against git show HEAD:<file>, requiring current==HEAD==the Phase 7 recorded baseline"

key-files:
  created:
    - .planning/phases/08-output-pipeline-rkdb-v2-parity/post/phase8_output_stage_post.json
    - .planning/phases/08-output-pipeline-rkdb-v2-parity/post/phase8_slice_green.json
    - .planning/phases/08-output-pipeline-rkdb-v2-parity/phase8_gates_evidence.json
  modified: []

key-decisions:
  - "The compare run was executed from the final tree (binary sha fea904e6…, HEAD 89aff20) with the untouched pre baseline: GREEN with sorted 10.41 s vs 18.73 s, delta 1.6999999999999993 s (0.191x the 8.91 s baseline delta), sha256 match and sorted RSS 12.04 GB vs 17.97 GB"
  - "The slice arms record 31.82/10.15/9.31 s, strictly below Phase 7's 36.92/17.76/23.83 s; t16 now beats t4 because the parallel unstable sort removed the single-threaded output tail, and every arm's RSS is ~12.04 GB vs ~17.96 GB (each partition table is released as it drains)"
  - "All three slice databases hash to 0976f29c5edeaa5eb49218e2c2fd5ff84f09109c3f2aac9d83bc8cf8c8668014 — the same value as Phase 7, the pre baseline and the committed goldens' pipeline, so t1/t4/t16 are byte-identical at 229M keys"
  - "Generated scratch (slice-0.fq, slice-1.fq and all five .rkdb files) was deleted after the assertion pass; only the two measurement documents remain in post/"
  - "Task 2 required no source edits: MSRV 1.82 clippy is clean on both crates. The only release-build warning is the nightly-only deprecation of Atomic::fetch_update (renamed try_update), pre-existing Phase 6 code that MSRV 1.82 does not deprecate"
  - "bench_harness_unittests.summary records the meaningful 'Ran 361 tests in 10.763s; OK (skipped=1)' pair; the plan's literal unit[-1] slice would capture a per-test 'report written to …' path line, not a summary"

requirements-completed: [OUT-01, OUT-02, OUT-03]

coverage:
  - id: D1
    description: "Post-change output stage measured against the immutable pre-change baseline with the GREEN verdict (identical sorted .rkdb sha256, lower sorted wall, sort delta at most half the baseline, no RSS regression) persisted in the validated document"
    requirement: OUT-01
    verification:
      - kind: e2e
        ref: "python3 scripts/bench/output_stage.py compare --baseline .planning/phases/08-output-pipeline-rkdb-v2-parity/pre/phase8_output_stage_pre.json --threads 4 --reps 3 --input /Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split --slice-reads 4000000 --rustkmer target/release/rustkmer --out …/post/phase8_output_stage_post.json (exit 0)"
        status: pass
      - kind: other
        ref: "post/phase8_output_stage_post.json#verdict result=GREEN sorted_wall_s=10.41 sort_delta_s=1.6999999999999993 sha256_match=True score=ok"
        status: pass
    human_judgment: false
  - id: D2
    description: "Real 4M-read slice measured at the Phase 7 scope with pinned counts in every arm, walls strictly below the Phase 7 per-arm medians, RSS non-increasing, and one shared .rkdb sha256 across t1/t4/t16"
    requirement: OUT-02
    verification:
      - kind: e2e
        ref: "python3 scripts/bench/thread_scaling.py --mode slice --input /Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split --slice-reads 4000000 --reps 1 --measure-only --out …/post/phase8_slice_green.json (exit 0)"
        status: pass
      - kind: other
        ref: "assertion pass: params k=21/canonical/[1,4,16]/4000000/reps=1, fingerprint 71c6264b, counts 229,694,874/519,271,168 in all arms, walls 31.82/10.15/9.31 < 36.92/17.76/23.83, RSS 12.04/12.04/12.05 GB <= Phase 7, all three .rkdb sha256 == 0976f29c"
        status: pass
    human_judgment: false
  - id: D3
    description: "Final standing-gate battery green with the frozen writer, goldens, fixtures, manifests, lockfiles and gate strictness proven intact by pinned blob/manifest hashes and current==HEAD anti-softening counts"
    requirement: OUT-03
    verification:
      - kind: integration
        ref: "cargo +1.82.0 clippy --locked --all-targets -- -D warnings (root and pyo3) — both pass; cargo test --locked — 31 summaries, 0 failed; golden_sha256_tests + golden_tests — 5 + 34 passed, 0 failed"
        status: pass
      - kind: integration
        ref: "python3 -m unittest discover -s scripts/bench/tests -t . — Ran 361 tests, OK (skipped=1); maturin develop --release + import assert + pytest pyo3/tests — 158 passed, 63 skipped"
        status: pass
      - kind: other
        ref: "phase8_gates_evidence.json#frozen_contract blobs format.rs eb0d5bf2, Cargo.toml fb5c8395, Cargo.lock 7f24f3f3, pyo3/Cargo.toml 5b01979c, pyo3/Cargo.lock 6da3805f; golden manifest f010e42a; anti_softening current==HEAD==(0,2,2), expected-failure wording 0"
        status: pass
    human_judgment: false

duration: 19min
completed: 2026-11-13
status: complete
---

# Phase 8 Plan 04: Post-Measurement and Final Gates Summary

**Post-change output stage GREEN at 10.41 s (from 18.73 s) with byte-identical `.rkdb`, slice walls cut to 31.82/10.15/9.31 s at 229M keys, and every standing gate green on a frozen writer**

## Performance

- **Duration:** 19 min
- **Started:** 2026-11-12T17:43:47Z
- **Completed:** 2026-11-12T18:02:44Z
- **Tasks:** 2
- **Files modified:** 3 created, 0 source files modified

## Accomplishments

- **Output-stage gate GREEN, persisted.** `output_stage.py compare` re-measured the final tree against the immutable pre baseline: sorted median wall 10.41 s vs 18.73 s, raw sort delta 1.6999999999999993 s vs 8.91 s (0.191x, inside the inclusive 0.5x boundary), sorted `.rkdb` sha256 unchanged (0976f29c), sorted peak RSS 12,041,912,320 B vs 17,967,087,616 B. The verdict block is written into the validated post document; the document also carries the baseline's `schedule` (round-robin-rotation, 3 identical rounds) and every rep's `cache_state`/`round`/`arm_order`.
- **Slice measurement at the exact Phase 7 scope.** t1/t4/t16 medians 31.82/10.15/9.31 s vs Phase 7's 36.92/17.76/23.83 s; peak RSS 12,036,734,976 / 12,043,878,400 / 12,051,611,648 B vs 17,958,944,768 / 17,966,088,192 / 17,968,676,864 B. Every arm reports exactly 229,694,874 unique / 519,271,168 total; params are k 21, canonical true, thread_counts [1, 4, 16], slice_reads 4,000,000, reps 1; input fingerprint 71c6264b.
- **Slice-scale byte identity.** The three measured arm databases hash to the single value 0976f29c5edeaa5eb49218e2c2fd5ff84f09109c3f2aac9d83bc8cf8c8668014 — identical to Phase 7, the pre baseline, and the golden pipeline, and independent of thread count.
- **Frozen contract proven untouched.** `src/database/format.rs` is git blob eb0d5bf2; `DatabaseHeader`/`KmerEntry` are defined only there; `count.rs` calls `KmerEntry::new` and `header.write_to` exactly once and contains no direct `write_u128` serialization; root and pyo3 manifests/lockfiles hash to their phase-base blobs; golden manifest f010e42a with an empty `git status` on fixtures, baselines and Phase 5/6/7/8-pre artifacts.
- **Every standing gate green.** MSRV 1.82 clippy on both crates, release build, full locked suite (31 summaries, 0 failed; 260 tests in the lib target), explicit golden tests (5 + 34), harness unittest discovery (361 tests, OK with 1 skip), rebuilt PyO3 module at the same module path and pytest 158 passed / 63 skipped.
- **No gate softened.** Workflow silencing constructs 0; README.md and thread_scaling.py each 2 on the current tree AND at `git show HEAD:<file>`, equal to the Phase 7 recorded baseline; expected-failure wording 0 in all three files. None of the three files was edited.

## Task Commits

Each task was committed atomically:

1. **Task 1: Post-change output-stage verdict and real-slice measurement** — `66d6e40` (feat)
2. **Task 2: Final standing-gate battery and frozen-contract audit** — `a8cf51d` (feat)

**Plan metadata:** the final docs commit with this SUMMARY, STATE.md, ROADMAP.md, and REQUIREMENTS.md.

## Files Created/Modified

- `.planning/phases/08-output-pipeline-rkdb-v2-parity/post/phase8_output_stage_post.json` — schema/provenance-valid post measurement with the persisted GREEN verdict block and baseline-equivalent schedule/rep protocol.
- `.planning/phases/08-output-pipeline-rkdb-v2-parity/post/phase8_slice_green.json` — t1/t4/t16 slice arms with pinned counts, walls, RSS, fingerprint and the pinned params.
- `.planning/phases/08-output-pipeline-rkdb-v2-parity/phase8_gates_evidence.json` — command lines, test summaries, module path, pytest summary, frozen blob hashes, golden manifest hash, anti-softening current/HEAD counts and both verdicts.
- Deleted after the assertion pass: `post/slice-0.fq`, `post/slice-1.fq`, `post/output_stage_sorted.rkdb`, `post/output_stage_unsorted.rkdb`, `post/scaling_rk21-t{1,4,16}.rkdb` and the transient `.gates_*.log` files.

## Decisions Made

- The compare was re-run from the final tree (`HEAD 89aff20`, binary sha fea904e68cd617c58d67982b39f833aeab391b1663d6a58735ae7fc400d00ada) rather than reusing 08-01's `/tmp` run; the result (10.41 s vs the earlier 10.43 s) reproduces within noise and the verdict is persisted in the plan's own document.
- The t16 arm now beats t4 (9.31 s vs 10.15 s) where Phase 7 had t16 worst (23.83 s); the parallel in-place sort removed the single-threaded output tail that dominated the t16 arm. Both remain strictly below their Phase 7 counterparts as required.
- Scratch slices/databases are removed after assertions; the two documents plus the evidence file are the only artifacts committed.
- No source edit was needed in Task 2: MSRV 1.82 clippy is clean on both crates, and the sole release-build warning is a nightly-only deprecation of `Atomic::fetch_update` (renamed `try_update`) in pre-existing Phase 6 code — never touched, and not a 1.82 warning.

## Deviations from Plan

### Recording adjustment (no gate change)

**1. Harness unittest summary field**
- **Found during:** Task 2 (final standing-gate battery)
- **Issue:** The plan's evidence script records `unit[-1]`, the last non-empty line of the unittest log. Seven harness tests print `report written to …md` lines after unittest's `OK`, so that slice captures a temp-file path instead of the summary.
- **Fix:** The evidence document records the meaningful `Ran 361 tests in 10.763s; OK (skipped=1)` pair. All assertions on the log (exit 0, `OK`, no failures) are unchanged; no test, helper, threshold, or gate was modified.
- **Files modified:** `.planning/phases/08-output-pipeline-rkdb-v2-parity/phase8_gates_evidence.json` only
- **Verification:** The log itself reported `Ran 361 tests in 10.763s` / `OK (skipped=1)` and the process exited 0.
- **Committed in:** `a8cf51d` (Task 2 commit)

---

**Total deviations:** 0 auto-fixed; 1 recording-format adjustment (no code, threshold, or gate semantics changed).
**Impact on plan:** None on the measured claims or gate strictness; the evidence field now carries the actual unittest summary.

## Issues Encountered

- The plan's `<verify>` chain bundles the two long measurements with the assertions. It was executed as the same commands in sequence (build → compare → slice measurement → assertion pass → cleanup); the measurement commands auto-backgrounded after 180 s and both completed with exit 0.
- `output_stage.py compare` provisions its own one-slice scratch in `post/`; `thread_scaling.py` provisions `slice-0.fq` and `slice-1.fq` because the input directory resolves two gzip parts. Both were removed after the assertion pass, leaving only the two JSON documents.
- `provision_slice` re-extracts the slice on every run (no caching), so the fingerprint equality is a fresh extraction, not a stale file.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 8 is complete: OUT-01/OUT-02/OUT-03 have measured, persisted evidence and every standing gate is green on the final output-pipeline tree.
- The frozen writer, goldens, fixtures, baselines, manifests and lockfiles are proven unchanged, so Phase 9 (Python parity) and Phase 10 (benchmark verdict) inherit a stable `.rkdb` v2 contract.
- The slice measurement (31.82/10.15/9.31 s, ~12.04 GB RSS) is the reference for the Phase 10 verdict at 229M-key scale.

---
*Phase: 08-output-pipeline-rkdb-v2-parity*
*Completed: 2026-11-13*

## Self-Check: PASSED

- FOUND: `.planning/phases/08-output-pipeline-rkdb-v2-parity/post/phase8_output_stage_post.json`
- FOUND: `.planning/phases/08-output-pipeline-rkdb-v2-parity/post/phase8_slice_green.json`
- FOUND: `.planning/phases/08-output-pipeline-rkdb-v2-parity/phase8_gates_evidence.json`
- FOUND: `66d6e40` (Task 1 commit)
- FOUND: `a8cf51d` (Task 2 commit)
