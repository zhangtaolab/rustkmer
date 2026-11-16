---
phase: 11-merge-characterization-harness-prep
plan: 02
subsystem: testing
tags: [python, benchmark-harness, prepare-inputs, manifest, sha256, jellyfish, rkdb, stdlib-only, unittest]

# Dependency graph
requires:
  - phase: 10-benchmark-verdict (v2.0 milestone)
    provides: committed union anchors (k=21: 8,967,099,203 / k=31: 8,275,694,030 sum-of-counts), fingerprint/stats/binary_provenance/PROVENANCE_KEYS shapes, rustkmer_count_cmd/jellyfish_count_cmd builders in bench.py
  - phase: 11-01 (sibling wave 1)
    provides: seven-arm bench.py extension this stage's artifacts feed (read surface unchanged)
provides:
  - scripts/bench/prepare_inputs.py — build/revalidate/manifest stage that constructs the 8 full-scale merge input artifacts with automatic sha256 + Total + command-line provenance recording (D-01/D-04)
  - merge-input-manifest record shape (schema_version 1) in RESEARCH Pattern 1 form — Phase 12 round-0 revalidation consumes records, not memory
  - derive_hash_size: smallest standard jellyfish -s satisfying the 0.75 occupancy assertion; one step over forces the next rung (auto-grow unreachable)
  - reconcile_anchors: mid-build per-k union-anchor enforcement point (Plan 11-05's post-build verify re-proves it from the manifest)
  - guards: pinned part_001+part_006 pair resolution, refuse_repo_root (D-03), zero-count abort, unrecorded-artifact revalidation error, fail-loud jellyfish info parser
affects: [Plan 11-05 (full-scale artifact builds + -s checkpoint), Plan 11-06 (ladder exercises the stage on real slices), Phase 12 (round-0 manifest revalidation), Plan 11-04 (parity gate consumes manifest Totals)]

# Actuals (#2632) — pairs with the plan's estimate (60000) to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 12747    # chars/4 over git diff 8c8362f..HEAD at SUMMARY time
  tasks: 2
  commits: 2       # MEASURED: git rev-list --count gsd-plan-head-before-11-02..HEAD
plan_head_before: 8c8362f8bb4be0ed6d9feeb0fc730c2241cb200d
plan_head_after: 1c65d5d8b4c583bebf01e05978132050b8e3d920

# Tech tracking
tech-stack:
  added: []       # stdlib-only contract preserved; no package installs (T-11-SC N/A)
  patterns:
    - "Manifest-bound artifact stage: build once, record sha256+stats+cmdline, revalidate from records alone (random_slice.py manifest pattern at artifact scale)"
    - "Fixed-order build with mid-build gate enforcement (anchor reconciliation between k steps, not only post-build)"
    - "Injectable-seam testing of a real subprocess stage: honest anchors computed from the fixtures, guard still runs, never bypassed (phase10 run_rounds pattern)"

key-files:
  created:
    - scripts/bench/prepare_inputs.py
    - scripts/bench/tests/test_prepare_inputs.py
  modified: []

key-decisions:
  - "reconcile_anchors(totals_by_k, anchors=None, ks=None) is the single enforcement point: the build calls ks=(k,) immediately after both parts of that k (mid-build abort), while the default full-set shape (missing k raises) serves tests and manifest-time checks"
  - "DEFAULT_RUSTKMER is REPO_ROOT-resolved absolute (bench.py's relative default assumes repo-root cwd) so the stage runs from any cwd, including Plan 11-05's controller invocations"
  - "The jf stage re-verifies the recorded .rkdb identity AND source fingerprints before building .jf inputs — the derived -s depends on those Distinct values, so drift between stages must be loud"
  - "hash_size_plan carries slots/occupancy/occupancy_target: jellyfish 2.3.1 `info` reports only command/where/when/canonical (probed verbatim 2026-11-16), so occupancy is computed by the stage, not parsed"
  - "Unreadable stats on a freshly counted artifact is normalized into the zero-count abort (empty .rkdb makes `rustkmer stats` exit 1 — probed), keeping the MBENCH-01/empty message contract"
  - "Tests drive the real stage with honest anchors pre-counted from the fixtures — the anchor guard executes on every synthetic run instead of being patched out"

patterns-established:
  - "Occupancy-boundary -s derivation: max_per_part_distinct <= 0.75 * slots over a fixed standard-size ladder; boundary exact-at-threshold keeps the size, +1 grows a rung"
  - "Manifest identity contract: every recorded artifact revalidates from size_bytes+sha256(+stats) against the manifest only; stray unrecorded .rkdb/.jf in the artifacts dir is a loud error"

requirements-completed: [MBENCH-01]

# Coverage metadata (#1602) — one entry per shipped deliverable.
coverage:
  - id: D1
    description: "Build verb runs the fixed D-04 order (per-part .rkdb counts -> per-k anchor reconciliation -> shared -s derivation -> per-part .jf with identical -m/-s/-C -> jellyfish info recording) and both stages produce/recomplete the manifest"
    requirement: MBENCH-01
    verification:
      - kind: integration
        ref: "scripts/bench/tests/test_prepare_inputs.py#TestManifestRoundTrip.test_round_trip_manifest_shape_and_revalidate"
        status: pass
      - kind: integration
        ref: "scripts/bench/tests/test_prepare_inputs.py#TestJfBuildAndInfo.test_jf_stage_records_hash_size_and_info"
        status: pass
    human_judgment: false
  - id: D2
    description: "derive_hash_size picks the smallest standard -s with the 0.75 occupancy assertion; exact-threshold keeps the size, one step over grows a rung, oversized raises RuntimeError"
    requirement: MBENCH-01
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_prepare_inputs.py#TestDeriveHashSize"
        status: pass
    human_judgment: false
  - id: D3
    description: "Guards proven both directions: pinned part_001+part_006 pair (part_002/reversed/1/3 paths rejected), refuse_repo_root (D-03), union-anchor reconciliation (missing/mismatching/unknown k raise, per-k mid-build shape), zero-count abort before any downstream build"
    requirement: MBENCH-01
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_prepare_inputs.py#TestPartPairGuard"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_prepare_inputs.py#TestRepoRootGuard"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_prepare_inputs.py#TestAnchorReconciliation"
        status: pass
      - kind: integration
        ref: "scripts/bench/tests/test_prepare_inputs.py#TestZeroTotalGuard.test_zero_total_aborts_stage"
        status: pass
    human_judgment: false
  - id: D4
    description: "Manifest round-trip integrity: revalidate re-hashes (+ re-stats .rkdb) every recorded record and passes; a single flipped byte, a rebuild-replace, or a stray unrecorded .rkdb makes revalidate raise naming the artifact (D-04, threat T-11-03)"
    requirement: MBENCH-01
    verification:
      - kind: integration
        ref: "scripts/bench/tests/test_prepare_inputs.py#TestManifestRoundTrip.test_tampered_byte_fails_revalidate"
        status: pass
      - kind: integration
        ref: "scripts/bench/tests/test_prepare_inputs.py#TestManifestRoundTrip.test_unrecorded_artifact_fails_revalidate"
        status: pass
      - kind: integration
        ref: "scripts/bench/tests/test_prepare_inputs.py#TestManifestRoundTrip.test_changed_counts_fail_revalidate"
        status: pass
    human_judgment: false
  - id: D5
    description: "Manifest shape matches RESEARCH Pattern 1 field-for-field (schema_version 1, kind merge-input-manifest, artifacts[] with sha256/command_line/k/canonical/distinct/total, jellyfish_inputs[] with hash_size + fail-loud-parsed info, source_fingerprints, binary_provenance verbatim, retention D-02); provenance reuses fingerprint/PROVENANCE_KEYS shapes so Phase 12 tooling reads one format"
    requirement: MBENCH-01
    verification:
      - kind: integration
        ref: "scripts/bench/tests/test_prepare_inputs.py#TestManifestRoundTrip.test_round_trip_manifest_shape_and_revalidate"
        status: pass
    human_judgment: false
  - id: D6
    description: "CLI surface: build --stage rkdb|jf / revalidate / manifest verbs work via direct script execution and module import; invalid input exits 2 loud (random_slice exit contract)"
    requirement: MBENCH-01
    verification:
      - kind: other
        ref: "command: python3 scripts/bench/prepare_inputs.py --help (rc 0); revalidate on empty dir -> exit 2 with loud message; AST check for derive_hash_size/resolve_part_pair/refuse_repo_root/reconcile_anchors + add_subparsers passed"
        status: pass
    human_judgment: false

# Metrics
duration: 17min
completed: 2026-11-16
status: complete
---

# Phase 11 Plan 02: Prepare-Inputs Stage Summary

**Harness built-in prepare-inputs stage (build/revalidate/manifest) that constructs the 8 merge input artifacts with automatic sha256 + Total + command-line provenance, derives the per-k-pair jellyfish -s under a 0.75 occupancy assertion, reconciles Phase-10 union anchors mid-build, and revalidates from manifest records alone — proven end-to-end at synthetic scale including the tamper-negative case (MBENCH-01/D-01/D-04)**

## Performance

- **Duration:** 17 min
- **Started:** 2026-11-16T13:06:55Z
- **Completed:** 2026-11-16T13:24:48Z
- **Tasks:** 2
- **Files modified:** 2 (both new)

## Accomplishments
- `scripts/bench/prepare_inputs.py`: three-verb stage (build --stage rkdb|jf / revalidate / manifest) in the random_slice.py template — import-fixup for direct execution, stdlib-only, fail-loud subprocess stance, list-form argv only
- Fixed D-04 build order enforced in code: per-part `.rkdb` counts first (first-ever per-part Distinct), per-k union-anchor reconciliation immediately after both parts of that k, shared `-s` derivation per k-pair with the occupancy assertion, per-part `.jf` with identical `-m/-s/-C`, `jellyfish info` recorded via a fail-loud parser
- Manifest in RESEARCH Pattern 1 shape (schema_version 1, kind `merge-input-manifest`) reusing bench.py's `fingerprint`/`stats`/`binary_provenance`/command builders verbatim — Phase 12 round-0 revalidation consumes records, not memory (D-04)
- Guards proven in both directions by 28 green tests: part pair (never part_002), repo-exit (D-03), union anchors (missing/mismatch/unknown k), zero-count abort, occupancy boundary (exact-at-threshold keeps, +1 grows a rung), tamper-negative revalidate, unrecorded-artifact error, drifted-source jf refusal
- Full-scale readiness: the stage defaults to `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs` (created on first build, outside the repo per D-03); Plan 11-05 drives the real ~70 GiB builds through it

## Task Commits

Each task was committed atomically:

1. **Task 1: prepare_inputs.py — build / revalidate / manifest stage with -s derivation and repo-exit guards** - `0452935` (feat)
2. **Task 2: test_prepare_inputs.py — manifest round-trip, tamper-negative, -s bounds, guards** - `1c65d5d` (test)

**Plan metadata:** _pending final docs commit_ (hash recorded in the completion report)

## Files Created/Modified
- `scripts/bench/prepare_inputs.py` - NEW: the prepare-inputs stage (build/revalidate/manifest, derive_hash_size, reconcile_anchors, resolve_part_pair, refuse_repo_root, parse_jellyfish_info, verify_recorded_artifacts)
- `scripts/bench/tests/test_prepare_inputs.py` - NEW: 28 tests across 6 classes (derivation boundary, guards, round-trip, tamper, zero-count, jf info)

## Decisions Made
- `reconcile_anchors(totals_by_k, anchors=None, ks=None)` is the single enforcement point: the build passes `ks=(k,)` immediately after both parts of that k (mid-build abort before the next k's counts and before any -s derivation), while the default full-set shape — where a missing k raises — serves tests and manifest-time checks
- `DEFAULT_RUSTKMER` is REPO_ROOT-resolved absolute so the stage works from any cwd (bench.py's relative default assumes repo-root cwd)
- The jf stage re-verifies the recorded `.rkdb` identity and source fingerprints before building on them (the -s plan was derived from those Distinct values)
- `hash_size_plan` carries `slots`/`occupancy`/`occupancy_target`: jellyfish 2.3.1 `info` reports only command/where/when/canonical (probed verbatim this session), so occupancy is computed by the stage
- Unreadable stats on a fresh artifact is normalized into the zero-count abort (empty `.rkdb` makes `rustkmer stats` exit 1 — probed), preserving the MBENCH-01/empty message contract
- Tests drive the real stage with honest anchors pre-counted from the fixtures (phase10 injectable-seam pattern) — the anchor guard executes on every synthetic run instead of being patched out

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 1's verify unittest leg cannot be green before Task 2 exists**
- **Found during:** Task 1 verification
- **Issue:** the verify command `python3 -m unittest discover -s scripts/bench/tests -t . -k test_prepare_inputs` matches zero tests until Task 2 creates `test_prepare_inputs.py`; on Python 3.13 zero-match discovery exits 5 ("NO TESTS RAN"), a non-zero exit by the verify's own fails_when rule
- **Fix:** no code change — Task 1's gate ran the load-bearing halves (AST surface check naming all four required functions + add_subparsers, importability, occupancy constant, plan greps — all green) and the exact unittest command re-ran green immediately after Task 2's module landed (28 tests, rc 0, zero skips)
- **Files modified:** none (sequencing artifact of the plan, not a code defect)
- **Verification:** `python3 -m unittest discover -s scripts/bench/tests -t . -k test_prepare_inputs` -> rc 0 at plan close
- **Committed in:** n/a

**2. [Rule 2 - Missing Critical] Zero-count abort normalized for empty databases**
- **Found during:** Task 1 implementation (empirical probe)
- **Issue:** an empty `.rkdb` (zero k-mers counted) makes `rustkmer stats -f json` itself exit 1 ("Database empty: no k-mers found") — the stats read raises before the plan's `total == 0` check could run, so the zero-total guard would surface as a generic stats failure instead of the intended loud empty-count abort
- **Fix:** `build_stage` wraps the post-count stats read: an unreadable stats on a freshly counted artifact raises the zero-count RuntimeError naming the artifact and probe (MBENCH-01/empty) with the original error chained; the explicit `total == 0` check remains as defense in depth
- **Files modified:** scripts/bench/prepare_inputs.py
- **Verification:** TestZeroTotalGuard.test_zero_total_aborts_stage (12 bp reads at k=21) asserts the MBENCH-01/empty abort and that no manifest is written
- **Committed in:** 0452935 (part of Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking verify-sequencing, 1 missing critical)
**Impact on plan:** both necessary for a green, honest verification loop; no scope creep.

## Issues Encountered
- Full harness suite: 616 tests, `FAILED (failures=1, errors=2, skipped=1)` — the 1 failure + 2 errors are exactly the pre-existing `test_phase10_verdict.py` archived-path reds documented in 11-01 (`.planning/phases/10-benchmark-verdict/` moved to `.planning/milestones/v2.0-phases/` by `97c497c`; already logged in deferred-items.md and STATE.md), and the 1 skip is the pre-existing opt-in `RUSTKMER_PYBENCH_VENV` skip in `test_python_bench.py`. Zero new failures; every module this plan created or touched is green.
- jellyfish aborts (SIGABRT) on `.gz` path arguments as known — the jf stage correctly rides `jellyfish_count_cmd`'s existing decompressor pipe (verified in TestJfBuildAndInfo through the real `sh -c` pipeline).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Ready for 11-03 (next plan in the phase) — no coupling: 11-03 is the parity-gate spec doc
- Ready for 11-05's full-scale builds: the stage creates `/Users/forrest/Data/data/illumina/CRR1936095-merge-inputs/` on first build; Plan 11-05's blocking checkpoint approves the derived `-s` + disk budget before any `.jf` build (closing research A4); its post-build verify re-proves the union-anchor reconciliation from the manifest — the mid-build enforcement point built here aborts first if anything drifts
- Ready for 11-06: the characterization ladder deliberately exercises this same stage on real slices (D-08)
- Known carried flakes unchanged: `test_verify_threads.py` macOS `sample`-race (purge stale `target/` before trusting a red); `test_phase10_verdict.py` archived-path reds (path retarget pending)

---
*Phase: 11-merge-characterization-harness-prep*
*Completed: 2026-11-16*

## Self-Check: PASSED

All created files exist on disk (`scripts/bench/prepare_inputs.py`, `scripts/bench/tests/test_prepare_inputs.py`); both task commits (`0452935`, `1c65d5d`) are ancestors of HEAD; plan_head_after (1c65d5d) matches HEAD at self-check time; commits measured 2 from the persisted plan ledger (gsd-plan-head-before-11-02).
