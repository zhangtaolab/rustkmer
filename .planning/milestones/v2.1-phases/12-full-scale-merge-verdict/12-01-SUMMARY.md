---
phase: 12-full-scale-merge-verdict
plan: 01
subsystem: benchmarking
tags: [bench-harness, python-stdlib, merge-verdict, staged-controller, renderer, exit-code-contract, unittest]

# Dependency graph
requires:
  - phase: 11-merge-characterization-harness-prep
    provides: prepared parity-validated artifacts + manifest, streaming dump comparator (WR-01 route), FULL_SCALE_CAVEAT, derived 136 GiB floor, ladder slopes + full-scale predictions, binary sha256 tripwires, union Total anchors
  - phase: 10-benchmark-verdict (v2.0)
    provides: phase10.py staged-controller precedent (0/1/2 exit-code contract, publish_atomic, write_doc/write_evidence_doc), bench.py schema v1 + provenance gates + merge command builders
provides:
  - scripts/bench/phase11.py — five-stage controller skeleton (revalidate/parity/timed/verdict/render) with the 0/1/2 exit-code contract and total dispatch (unimplemented stages exit 2 naming themselves)
  - Verdict stage: pure match-or-beat comparison of recorded medians per k, t1 excluded under "scaling", overall YES iff both k, verdict doc (kind phase11-merge-verdict) carrying overall/decision/exit_code/rule + per-k blocks
  - Render stage: mechanical MBENCH-04 renderer (no measurement literals, no clock) with byte-identical re-render proof recorded in a phase12-render-proof doc and atomic dual-artifact publish
  - merge_arm_argv: defaults-only argv resolved from revalidated manifest records (Plan 12-04's timed stage consumes this)
  - Document validators (_validate_results_document/_validate_parity_document/_validate_verdict_document) that pin what Plan 12-04's stage docs must satisfy
  - scripts/bench/tests/test_phase11_verdict.py — 36-test Wave-0 contract suite
affects: [12-02 full-scale session (reads verdict doc layout + render stage), 12-04 session-stage expansion (fills revalidate/parity/timed against these validators), 12-03 wrap-up (docs rewrite sources the rendered report)]

# Actuals (#2632) — same estimateTokens scale (chars/4 over the realized diff).
actuals:
  tokens: 19805       # 79,219 chars over the two created files / 4
  tasks: 1
  commits: 2          # MEASURED: git rev-list --count 005af06..HEAD

# Tech tracking
tech-stack:
  added: []           # stdlib-only harness contract held — zero new packages
  patterns: [staged-controller (phase10 precedent), mechanical-renderer T-04-07 contract, publish_atomic validate-then-write evidence docs, tripwire constants with provenance comments]

key-files:
  created:
    - scripts/bench/phase11.py
    - scripts/bench/tests/test_phase11_verdict.py
  modified: []

key-decisions:
  - "Verdict stage publishes exactly one carrier artifact (12-VERDICT.json per the pinned artifact table); the plan's 'both artifacts still written' on a measured NO is satisfied by both per-k blocks publishing inside that doc — a measured NO is a valid recorded result, never an abort"
  - "Results-doc arm contract pins per-arm provenance + unique_kmers/total_kmers/output_bytes so entry-rate/byte-rate render mechanically; Plan 12-04's timed docs must write arms to this shape (schema v1 tolerates the extra keys, A6)"
  - "Renderer reads the ladder caveat from the recorded doc and refuses any ladder whose caveat != merge_characterize.FULL_SCALE_CAVEAT — a document not written by this harness cannot be rendered"
  - "TDD task executed as test-commit-before-feat-commit; RED evidenced on a clean worktree at HEAD (suite fails at collection: ImportError on the absent controller), machine tdd-red-evidence gate not active for type:execute plans"

patterns-established:
  - "Staged controller dispatch: STAGES tuple + choices + a total dispatch where a stage whose function a later plan owns exits 2 naming the missing stage — never silence"
  - "Verdict docs carry the rule string verbatim at top level AND in every per-k block; exit_code field must equal the process exit code (Plan 12-02's gates read this layout)"
  - "Mechanical renderer hygiene gates as unit tests: zero 'normalize_dump_lines' refs, zero bare in-process comparator refs (only the streaming form), zero shell=True, zero fixture measurement literals"

requirements-completed: [MBENCH-03, MBENCH-04]  # copied from plan frontmatter; mark-complete deferred — both IDs are shared with 12-02/12-03/12-04 whose SUMMARYs do not exist yet (shared-ID gate #2388)

coverage:
  - id: D1
    description: "Five-stage controller skeleton: STAGES == (revalidate, parity, timed, verdict, render), EXIT_OK/EXIT_NO/EXIT_INVALID == 0/1/2, unknown --stage exits 2, unimplemented session stages exit 2 naming the stage, infra failure maps to exit 2 with no artifact, --help exits 0 via the script-path fixup"
    requirement: MBENCH-03
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestStageContract"
        status: pass
      - kind: unit
        ref: "command: python3 scripts/bench/phase11.py --help (exit 0, stderr clean)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Verdict stage: match-or-beat median comparison per k (equality wins, no tolerance), t1 excluded under 'scaling', overall YES iff both k, exit 0/NO-INVEST vs 1/INVEST with the verdict doc publishing in both cases, pinned doc key layout (overall/decision/exit_code/rule + per-k k/result/rustkmer_wall_s/jellyfish_wall_s), greppable 'PHASE11 VERDICT k=...' stdout lines"
    requirement: MBENCH-03
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestVerdictRule"
        status: pass
    human_judgment: false
  - id: D3
    description: "merge_arm_argv: defaults-only argv resolved from manifest records — no --num-threads on merge, exactly [--num-threads, 1] on merge-t1, exact 5-token jellyfish argv, drifted manifests and unknown arms raise"
    requirement: MBENCH-03
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestMergeArmArgv"
        status: pass
    human_judgment: false
  - id: D4
    description: "Document validators: results docs gate on schema v1 + phase/session + merge-arm names + per-arm provenance; parity docs gate on kind/legs (all three)/anchors.exact/merges; verdict docs gate on the pinned layout and decision/exit-code consistency"
    requirement: MBENCH-04
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestValidateDocs"
        status: pass
    human_judgment: false
  - id: D5
    description: "Mechanical renderer: asymmetry sentence and ladder caveat verbatim, per-arm methodology rows (threads/flags/route/sha256), entry-rate/byte-rate/B-per-entry rows computed only from recorded values, predicted-vs-measured table read from summary.slopes/extrapolated_full_scale, parity evidence lines, RSS-is-context framing, t1 2-OS-thread pool-contract label"
    requirement: MBENCH-04
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestRenderSections"
        status: pass
    human_judgment: false
  - id: D6
    description: "Byte-identical re-render proof + hygiene: render twice is byte-identical with no clock fields, changing a median changes its row, render stage publishes report + phase12-render-proof via publish_atomic, source carries zero in-process-normalizer refs / zero bare in-process comparator refs / zero shell=True / zero fixture literals"
    requirement: MBENCH-04
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestRenderDeterminism"
        status: pass
      - kind: unit
        ref: "command: grep -c normalize_dump_lines / grep -cE 'dump_vs_dump_equal\\b' / grep -c shell=True on scripts/bench/phase11.py (all 0)"
        status: pass
    human_judgment: false

# Metrics
duration: 22 min
completed: 2026-11-17
status: complete
---

# Phase 12 Plan 01: Controller Skeleton + Verdict + Render Stages Summary

**Staged `phase11.py` controller (five-stage dispatch, 0/1/2 exit-code contract) with a pure match-or-beat merge-verdict stage, a byte-identical mechanical MBENCH-04 renderer, defaults-only `merge_arm_argv`, and a 36-test Wave-0 contract suite — all green, no binaries invoked**

## Performance

- **Duration:** 22 min
- **Started:** 2026-11-17T00:58:08Z
- **Completed:** 2026-11-17T01:19:44Z
- **Tasks:** 1 (TDD: RED + GREEN commits)
- **Files modified:** 2 created

## Accomplishments

- `scripts/bench/phase11.py` (1071 lines): five-stage `--stage` dispatch pinning revalidate → parity → timed → verdict → render by construction (the WR-01 structural fix), phase10-modeled 0/1/2 exit-code contract with exit 3 preserved for the disk-floor block, and a total dispatch where the session stages Plan 12-04 owns exit 2 naming themselves
- Verdict stage: pure comparison of recorded merge vs jellyfish-merge medians per k — match-or-beat `<=` with exact equality winning, merge-t1 recorded under `scaling` and excluded from YES/NO, overall YES iff both k; writes the `phase11-merge-verdict` doc (overall/decision/exit_code/rule verbatim + per-k blocks) via `write_evidence_doc` and prints `PHASE11 VERDICT k=... result=...` lines; a measured NO publishes with exit 1
- Render stage: mechanical renderer carrying all MBENCH-04 sections — per-arm methodology rows (threads/argv/route/output+binary sha256), the pre-agreed asymmetry sentence, entry-rate/byte-rate/B-per-entry rows, predicted-vs-measured table from the ladder doc with `FULL_SCALE_CAVEAT` verbatim, parity evidence lines, RSS-is-context framing, the t1 2-OS-thread pool-contract label — byte-identical on re-render with the proof recorded in a `phase12-render-proof` doc and atomic dual-artifact publish
- `merge_arm_argv` builds defaults-only argv for all three arms from revalidated manifest records (inputs cannot drift from the parity-validated artifacts), ready for Plan 12-04's timed stage
- Binary-identity tripwires (`assert_binary_identity`) pin rustkmer `4539b893…d023b` and jellyfish `e99c676b…91ee` against the ladder provenance; `invalid()`, pinned constants with provenance comments (STAGES, UNION_TOTALS anchors, PART_PATHS, DUMP_BYTES_PER_LINE, ASYMMETRY_SENTENCE), and the top-level exception mapping complete the phase10-modeled skeleton
- `scripts/bench/tests/test_phase11_verdict.py`: 36 stdlib-unittest tests covering stage dispatch/exit codes, the verdict rule + doc layout, defaults-only argv, validator GREEN/RED gates, renderer sections, byte-identity, and source-hygiene gates — zero measurement binaries invoked

## Task Commits

Each task was committed atomically (TDD commit scope):

1. **Task 1 RED: Wave-0 verdict-contract suite** - `647ed17` (test)
2. **Task 1 GREEN: controller skeleton + verdict + render stages** - `18c966e` (feat)

_Note: no REFACTOR commit — no post-green cleanup was needed._

## Files Created/Modified

- `scripts/bench/phase11.py` - the Phase-12 staged controller (D-01 name locked verbatim; evidence kinds carry the phase-12 prefix, controller/verdict-line carry phase11)
- `scripts/bench/tests/test_phase11_verdict.py` - Wave-0 contract suite (session-stage tests belong to Plan 12-04 per the plan)

## TDD Cycle (RED → GREEN)

- **RED:** `647ed17` commits the 36-test suite before the implementation exists. Why it failed: the suite imports `scripts.bench.phase11`, which no commit at HEAD contained — demonstrated on a clean throwaway worktree at HEAD: `.venv313/bin/python -m pytest scripts/bench/tests/test_phase11_verdict.py -q` → `ImportError: cannot import name 'phase11' from 'scripts.bench'`, collection interrupted. **Semantic assessment:** this is load-level RED (the whole module is the deliverable), not assertion-level RED — the machine `tdd-red-evidence` classifier would grade a `ModuleNotFoundError`/`_FailedTest` as a load failure; that gate binds `type: tdd` plans and this plan is `type: execute`, so the commit-scope contract (test before feat) is the binding rule here. Assertion-level proof of every planned behavior is supplied by the 36 GREEN tests, each targeting one behavior from the plan's `<behavior>` list.
- **GREEN:** `18c966e` implements the controller; the new suite passes 36/36 and the combined quick command passes 61/61 (with `test_merge_arms.py`).

## Verification (all run at HEAD `18c966e`)

- `.venv313/bin/python -m pytest scripts/bench/tests/test_phase11_verdict.py -q` → **36 passed** (grep gate: 36 ≥ 15 [HEAD=0 EXPECT>=15])
- `.venv313/bin/python -m pytest scripts/bench/tests/test_phase11_verdict.py scripts/bench/tests/test_merge_arms.py -q` → **61 passed**
- `python3 scripts/bench/phase11.py --help` → exit 0, stderr clean (no ImportError/ModuleNotFoundError/Traceback)
- Full harness suite: `python3 -m unittest discover -s scripts/bench/tests -t .` → **Ran 680 tests ... OK (skipped=1)**, exit 0 (the skip is the pre-existing flake-guard skip; zero new failures)
- WR-01/T-12-03 grep gates: `normalize_dump_lines` = 0, bare in-process comparator (`dump_vs_dump_equal\b`) = 0 (only `dump_vs_dump_equal_streaming` appears), `shell=True` = 0
- Success-criterion boundary check: `bench.py`, `merge_characterize.py`, `prepare_inputs.py`, `output_stage.py` untouched; no Rust code changed (WR-02's same-touch trigger does NOT fire)

## Decisions Made

- **Single verdict carrier artifact:** `run_verdict` writes exactly one doc (`12-VERDICT.json` per the pinned artifact table); the plan behavior's "both artifacts still written (a measured NO publishes)" is tested as both per-k blocks publishing inside that doc on exit 1. Adding a second artifact would have forked the pinned evidence set.
- **Arm record contract for Plan 12-04:** results-doc arms carry `provenance`, `unique_kmers`, `total_kmers`, `output_bytes`, `output_sha256`, `command_line`, and `route` — the exact fields the renderer consumes. Schema v1 tolerates the extra keys (A6); `_validate_results_document` enforces them so a malformed doc is rejected before verdict/render.
- **Ladder caveat pinned to the harness constant:** the renderer renders the caveat recorded in the ladder doc but refuses any doc whose caveat differs from `merge_characterize.FULL_SCALE_CAVEAT` — a ladder document not written by this harness cannot be rendered into the public report.
- **Exact-vs-strict equality:** the verdict rule uses `<=` on recorded floats (JSON round-trip is exact in Python), so `merge wall == jellyfish wall` is match-or-beat YES — unit-proven.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The plan's infra-failure behavior test initially hit the arity guard instead of the validator because argparse consumed only one `--results` value; fixed in the test by passing two malformed docs. Test-side only; no controller change needed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for 12-02 (full-scale session): the verdict stage consumes the two schema-v1 results docs 12-02/12-04 produce and writes the pinned verdict layout; the render stage consumes results + parity + verdict + ladder docs and publishes `12-MERGE-REPORT.md` + `12-RENDER-PROOF.json`.
- Plan 12-04 must implement `run_revalidate`/`run_parity`/`run_timed` (currently exiting 2 by design, named by the dispatch), plus the Leg-2 recount diff and the parity/round-0 doc builders — the validator and argv contracts they must satisfy are pinned and unit-proven here.
- MBENCH-03/MBENCH-04 intentionally remain open in REQUIREMENTS.md: both IDs are shared with 12-02/12-03/12-04 (shared-ID gate), and the full-scale measurement itself belongs to 12-02.
- Known flake reminder for 12-02's long session: `test_verify_threads.py` ~50% macOS `sample`-race flake — purge stale `target/` before trusting a red.

---
*Phase: 12-full-scale-merge-verdict*
*Completed: 2026-11-17*
