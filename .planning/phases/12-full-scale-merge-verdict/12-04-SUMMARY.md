---
phase: 12-full-scale-merge-verdict
plan: 04
subsystem: benchmarking
tags: [bench-harness, python-stdlib, merge-verdict, staged-controller, round0-gate, parity-gate, counterbalanced-protocol, tdd]

# Dependency graph
requires:
  - phase: 12-full-scale-merge-verdict (plan 12-01)
    provides: phase11.py five-stage skeleton (0/1/2 exit contract, verdict/render stages), _validate_parity_document/_validate_results_document contracts, merge_arm_argv, publish_atomic/write_doc/write_evidence_doc
  - phase: 11-merge-characterization-harness-prep
    provides: revalidate_stage + manifest schema, streaming dump pipeline (_normalized_sorted_dump / dump_vs_dump_equal_streaming), measured_run/route_from_stderr, UNION_DISTINCT_ANCHORS, assert_merge_parity, disk guards, rotation_schedule
provides:
  - scripts/bench/phase11.py — ALL five stages implemented: run_revalidate (round-0 gate: manifest digest, anchors keyed '21'/'31' with {sum, expected, exact}, binary identities, D-12 session budget, df sample, source-fingerprint cross-check), run_parity (three legs incl. the NEW Leg-2 recount_vs_merged_equal streaming diff, warmup-marked merges per A5, deletion sequencing), run_timed (3-arm counterbalanced per-rep loop, cross-rep conservation, schema-v1 results docs PHASE=12)
  - recount_vs_merged_equal() — the Leg-2 independent-recount diff through the streaming pipeline (WR-01 structural fix; no in-process form anywhere in this file)
  - session_budget/session_budget_gb — the deterministic D-12 session-budget arithmetic with terms citing their constants
  - assert_anchor_equality — EXACT union-anchor equality emitting the round-0 anchors layout Plan 12-02's gates read
  - check_source_fingerprints — source-swap defense over the pinned part pair
  - scripts/bench/tests/test_phase11_verdict.py — 72-test suite (36 Wave-0 + 36 new), binary-free
affects: [12-02 full-scale live session (drives revalidate/parity/timed end-to-end; its gates hardcode the doc layouts pinned here), 12-03 wrap-up]

# Actuals (#2632) — same estimateTokens scale (chars/4 over the realized diff).
actuals:
  tokens: 22855        # 91,423 chars over the realized diff / 4
  tasks: 2
  commits: 4           # MEASURED: git rev-list --count 9d3fcd0..HEAD

commits: 4
plan_head_before: 9d3fcd017e174f4b0f28099da4ca9c168ee79982
plan_head_after: a8886783e9d2b54da8e92ab08f206af5f7380086

# Tech tracking
tech-stack:
  added: []           # stdlib-only harness contract held — zero new packages (T-12-SC: no installs)
  patterns: [staged-controller stage fill (phase10 precedent), injectable-seams-defaulting-at-call-time, validate-then-write evidence docs, streaming-only deep legs (WR-01), GREEN/RED unit proofs for every new gate]

key-files:
  created: []
  modified:
    - scripts/bench/phase11.py
    - scripts/bench/tests/test_phase11_verdict.py

key-decisions:
  - "run_revalidate/run_timed take artifacts_dir/scratch/source_paths as injectable params DEFAULTING to the pinned constants (DEFAULT_ARTIFACTS_DIR / DEFAULT_SCRATCH / PART_PATHS) — production behavior identical, unit tests hermetic (a fixture revalidate_fn that honored the hardcoded real dir hashed the 86.74 GiB of real artifacts per test; the fix also gives 12-02 resume flexibility)"
  - "Doc-level provenance stays ONE validate_provenance-clean block (the rustkmer release provenance); the plan's two-tool mapping lands as a separate comparator_provenance key {rustkmer, jellyfish} — validate_provenance would reject a raw {rustkmer: ..., jellyfish: ...} provenance mapping, so the literal reading could never have passed write_doc"
  - "Session-budget entries come from merge_characterize.UNION_DISTINCT_ANCHORS — the constant that wrote 11-LADDER-RESULTS.json summary.extrapolated_full_scale.full_scale_entries — instead of loading the ladder JSON at runtime; same recorded values, single source, no new file dependency"
  - "Leg 2 asserts the recount Total EXACT against the union anchor BEFORE the per-k-mer diff (a cheap conservation pre-check consistent with the gate family; the diff remains the verdict)"
  - "Timed arms carry output_sha256 from each arm's FINAL rep's actual output bytes; per-rep records keep the plan's exact field list (determinism visible via cross-rep conservation of distinct/total/output_bytes, not per-rep hashes)"
  - "The 12-01 'not implemented yet' placeholder test became a total-dispatch pin (every pinned stage has a callable runner) — the natural consequence of filling the last three stages"

patterns-established:
  - "Session-stage seams (revalidate_fn/provenance_fn/measure_fn/purge_fn/sleep_fn/guard_fn/counts_fn/fingerprint_fn/disk_fn/df_fn) default to the module primitives at CALL time — tests inject fixtures and still drive the real stage entry points (phase10.run_rounds precedent)"
  - "Round-0 anchors layout pinned by test: 12-REVALIDATE.json anchors is keyed by the string k values ('21'/'31'), each entry exactly {sum, expected, exact}"
  - "Parity docs are warmup carriers: merges records marked warmup=True with argv; run_timed cites them as params.warmup_provenance and runs no additional warmup (A5/D-02)"

requirements-completed: [MBENCH-03, MBENCH-04]  # copied from plan frontmatter; mark-complete DEFERRED — both IDs are shared with 12-02/12-03 whose SUMMARYs do not exist yet (shared-ID gate #2388; requirements.ready-ids returned blocked for both)

coverage:
  - id: D1
    description: "Round-0 revalidate stage: revalidate_stage invocation, EXACT anchor equality vs UNION_TOTALS for both k, source-fingerprint cross-check, explicit D-12 session budget through check_disk_floor (exit-3 semantics preserved), round-0 doc with anchors keyed '21'/'31' carrying {sum, expected, exact} + manifest digest + binary identities + df sample"
    requirement: MBENCH-03
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestAnchorEquality"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestSessionBudget"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestSourceFingerprintCrossCheck"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestRunRevalidateStage"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestRound0DocBuilder"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestBinaryIdentityTripwire"
        status: pass
    human_judgment: false
  - id: D2
    description: "Parity stage with the NEW Leg-2 recount diff: one warmup-marked merge per tool (A5), Leg 1 assert_merge_parity (sum-of-counts), Leg 2 recount_vs_merged_equal through the streaming pipeline (via_stdout=False sides, first-difference naming, empty/malformed/length loud errors), Leg 3 dump_vs_dump_equal_streaming, deletion sequencing recorded, parity docs passing _validate_parity_document"
    requirement: MBENCH-03
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestRecountVsMergedEqual"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestParityDocBuilder"
        status: pass
      - kind: unit
        ref: "command: grep -c 'leg2-recount-vs-merged' scripts/bench/phase11.py (1 >= 1); grep -c 'normalize_dump_lines' (0)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Timed stage: 3 arms x 3 counterbalanced reps per k via rotation_schedule, per-rep honest cache_state + disk guard + route attribution from kept stderr + own-output counts + rep-output deletion, cross-rep conservation enforced before any doc, medians via reduce_arm, schema-v1 results docs (PHASE=12, session merge) written validate-then-write, structural --parity-doc requirement"
    requirement: MBENCH-03
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestRotationSchedule"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestTimedRounds"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestCrossRepConservation"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestResultsDocBuilder"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestTimedStageGuards"
        status: pass
      - kind: unit
        ref: "command: grep -c 'rotation_schedule' scripts/bench/phase11.py (4 >= 2); grep -c 'shell=True' (0)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Cross-plan data contracts Plan 12-02's gates hardcode pinned by unit tests: 12-REVALIDATE.json anchors['21'/'31'].exact, 12-PARITY-K*.json legs_executed/anchors.exact, 12-RESULTS-FULL-K*.json phase/session/arms/reps (via _validate_results_document)"
    requirement: MBENCH-04
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestRound0DocBuilder"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestParityDocBuilder"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_phase11_verdict.py#TestResultsDocBuilder::test_doc_passes_schema_and_validators"
        status: pass
    human_judgment: false
  - id: D5
    description: "Boundary held: no Rust code changed; bench.py, merge_characterize.py, prepare_inputs.py, output_stage.py untouched; no measurement happened (the full-scale live session is Plan 12-02); stdlib-only imports"
    requirement: MBENCH-03
    verification:
      - kind: command
        ref: "git diff --stat 9d3fcd0..HEAD -- bench.py merge_characterize.py prepare_inputs.py output_stage.py src/ pyo3/ (empty)"
        status: pass
      - kind: command
        ref: "python3 scripts/bench/phase11.py --help (exit 0, stderr clean)"
        status: pass
    human_judgment: false

# Metrics
duration: 45 min
completed: 2026-11-17
status: complete
---

# Phase 12 Plan 04: Session Stages — Round-0 Revalidate + Parity + Timed Summary

**Completed the phase11.py controller's three session stages on the 12-01 skeleton — the round-0 gate (exact union anchors + D-12 session budget + source-swap defense), the three-leg parity stage with the NEW Leg-2 independent-recount diff through the streaming pipeline, and the 3-arm counterbalanced timed stage — all unit-proven GREEN/RED binary-free, with the doc layouts Plan 12-02's gates read pinned by tests**

## Performance

- **Duration:** 45 min
- **Started:** 2026-11-17T01:26:20Z
- **Completed:** 2026-11-17T02:11:30Z
- **Tasks:** 2 (both TDD: RED + GREEN commits each)
- **Files modified:** 2 (extended, never restructured)

## Accomplishments

- `run_revalidate` (round-0 gate): invokes `assert_binary_identity` + `revalidate_stage` (never reimplements hashing), asserts EXACT anchor equality for both k against UNION_TOTALS (raising naming computed vs expected), cross-checks the pinned part-pair source fingerprints against the manifest, computes the D-12 session budget explicitly (`inputs 87 + parity 173 + timed 22 = 282 GiB` on the recorded values, deterministic, terms citing DUMP_BYTES_PER_LINE=30 / 20 B-per-entry / the ladder source) and passes it to `check_disk_floor` (exit-3 block semantics untouched), samples df via `shutil.disk_usage`, and writes the `phase12-round0-revalidation` doc with anchors keyed '21'/'31' each carrying exactly `{sum, expected, exact}` — the layout Plan 12-02's first gate reads
- `run_parity` (three-way gate per k): requires a valid `--round0` doc (structural order), re-runs the revalidate + binary-identity tripwires at stage start, runs one warmup-marked merge per tool (A5 — argv + wall + honest cache_state recorded), executes all three legs — Leg 1 `assert_merge_parity` on sum-of-counts values, the NEW Leg 2 `recount_vs_merged_equal` (independent recount over both parts as ONE input list via `rustkmer_count_cmd`/`run_command` untimed, anchored EXACT against the union total, then per-k-mer diffed through two `via_stdout=False` streaming dump sides), Leg 3 `dump_vs_dump_equal_streaming` — sequences transient deletions (recount db after its sorted dump exists, merged outputs after Leg 3 green, leg workdirs removed; all recorded as `transients_deleted`), and writes the `phase12-merge-parity` doc passing Plan 12-01's `_validate_parity_document`
- `run_timed` (3-arm counterbalanced protocol per k): refuses to run without exactly one matching-k validated parity doc (`invalid()` — parity-before-timing is structural); re-runs the input-swap tripwires; cites the parity merges as `params.warmup_provenance` and runs no additional warmup; iterates `rotation_schedule(MERGE_ARMS, reps)` with per-rep honest cache_state, `ensure_disk_headroom` BEFORE every measured rep, `measured_run` (stderr kept) + `route_from_stderr`, counts from each rep's OWN output (WR-06, sum-of-counts readers, zero-distinct loud), rep-output deletion before the next rep, cooldown only between runs; enforces cross-rep conservation (distinct/total/output_bytes identical per arm) BEFORE any doc is written; reduces medians via `reduce_arm` (cv_warning recorded, never smoothed); writes schema-v1 results docs (PHASE=12, session merge, mode full) via `phase10.write_doc` validate-then-write
- `scripts/bench/tests/test_phase11_verdict.py`: 36 new tests (72 total, zero binaries invoked) — anchor equality GREEN/RED, budget determinism + constant citations, Leg-2 GREEN/RED streaming fixtures (identical/unordered pass; altered count names the sorted line and both sides; empty side, length mismatch, malformed line, and stdout-only builders all fail loudly), source-swap defense, run_revalidate drift/stray/hermetic happy path, binary-identity tripwire, parity-doc contract, rotation-schedule shape, per-rep loop seam recording (guard count == rep count, sleep count == rep count - 1), conservation RED, results-doc validator chain, timed-stage guards

## Task Commits

Each task was committed atomically (TDD commit scope):

1. **Task 1 RED: round-0 + parity contracts** - `55ae5f5` (test)
2. **Task 1 GREEN: revalidate stage + parity stage with Leg-2 recount diff** - `ffdfc08` (feat)
3. **Task 2 RED: timed-stage contract suite** - `4b3bb93` (test)
4. **Task 2 GREEN: timed stage — 3-arm counterbalanced protocol** - `a888678` (feat)

_No REFACTOR commits — no post-green cleanup was needed._

## Verification (all run at HEAD `a888678`)

- `.venv313/bin/python -m pytest scripts/bench/tests/test_phase11_verdict.py scripts/bench/tests/test_prepare_inputs.py scripts/bench/tests/test_merge_arms.py scripts/bench/tests/test_disk_floor.py -q` → **139 passed**
- Full harness suite: `python3 -m unittest discover -s scripts/bench/tests -t .` → **Ran 716 tests ... OK (skipped=1)**, exit 0 (the skip is the pre-existing flake-guard skip; zero new failures)
- `python3 scripts/bench/phase11.py --help` → exit 0, stderr clean
- WR-01 gate: `grep -c "normalize_dump_lines" scripts/bench/phase11.py` → **0** (streaming form only)
- T-12-03 gate: `grep -c "shell=True"` → **0** (argv-clean)
- `grep -c "leg2-recount-vs-merged"` → 1 (>= 1); `grep -c "rotation_schedule"` → 4 (>= 2)
- Boundary: `bench.py`, `merge_characterize.py`, `prepare_inputs.py`, `output_stage.py`, `src/`, `pyo3/` untouched at `9d3fcd0..HEAD` (no Rust code changed — WR-02's same-touch trigger does not fire)
- Cross-plan doc layouts pinned by tests: round-0 anchors keyed '21'/'31' with `{sum, expected, exact}`; parity docs `legs_executed` == the three legs + `anchors.exact`; results docs pass `bench.validate_schema` AND `_validate_results_document` with phase 12 / session merge / 3 arms / reps 3

## TDD Cycles (RED → GREEN per task)

- **Task 1:** RED `55ae5f5` (25 tests failing: AttributeError on `assert_anchor_equality`/`session_budget_gb`/`recount_vs_merged_equal`/`run_revalidate`/`parity_doc`/`check_source_fingerprints`/`round0_doc` — load-level RED on the planned behaviors), GREEN `ffdfc08` (61/61 + combined 89 passed).
- **Task 2:** RED `4b3bb93` (8 tests failing: AttributeError on `_timed_rounds`/`_assert_cross_rep_conservation`/`_timed_arm`/`results_doc`/`run_timed`), GREEN `a888678` (72/72 + combined 111 passed).

## Decisions Made

- **Hermetic stage params:** `run_revalidate`/`run_timed` take `artifacts_dir`/`scratch`/`source_paths` as injectable params defaulting to the pinned constants. Production is byte-identical to the plan's literals; the alternative (hardcoding the real artifacts dir into the stage body) made a fixture-based revalidate function hash the real 86.74 GiB per test (~38 s each — discovered when the first happy-path run did exactly that).
- **Provenance shape:** the plan's `provenance = {rustkmer: ..., jellyfish: ...}` would fail `write_doc`'s `validate_provenance` (it requires a single block with `binary`/`git_commit`/...). The doc carries the rustkmer release block as `provenance` and the plan's two-tool mapping as `comparator_provenance` — both tools attributed, validator-clean.
- **Budget entries from the harness constant:** `session_budget` defaults its union entries to `merge_characterize.UNION_DISTINCT_ANCHORS` — the same recorded values the ladder doc carries at `summary.extrapolated_full_scale.full_scale_entries` — instead of loading the JSON at runtime.
- **Leg-2 anchor pre-check:** the recount's Total is asserted EXACT against the union anchor before the per-k-mer diff — a cheap conservation pre-gate consistent with the gate family; the diff remains the verdict.
- **Arm output hash:** one hash per arm from its final rep's actual output bytes; per-rep records keep the plan's exact field list (determinism is enforced via conservation of distinct/total/output_bytes).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Provenance-mapping contradiction resolved in favor of the 12-01 validator contract**
- **Found during:** Task 2 (results-doc builder)
- **Issue:** the plan's literal `provenance = {rustkmer: ..., jellyfish: ...}` conflicts with `phase10.write_doc`'s `validate_provenance` gate (single provenance block) — the doc would never land
- **Fix:** doc `provenance` = the rustkmer release block (validator-clean); the two-tool mapping recorded at `comparator_provenance` = `{rustkmer, jellyfish}` exactly as the plan's attribution intent requires
- **Files modified:** scripts/bench/phase11.py
- **Verification:** TestResultsDocBuilder asserts `validate_schema` + `_validate_results_document` + `write_doc` lands
- **Commit:** a888678

**2. [Rule 3 - Blocking] Hardcoded real artifacts dir made fixture tests hash 86.74 GiB**
- **Found during:** Task 1 (GREEN run)
- **Issue:** `run_revalidate` called the injected `revalidate_fn` with the hardcoded `DEFAULT_ARTIFACTS_DIR`, so the fixture revalidate function read the REAL manifest and fingerprinted the real 86.74 GiB artifacts (~38 s per test, suite appeared hung)
- **Fix:** `artifacts_dir`/`manifest_path` became injectable params defaulting to the pinned constants; the test passes its fixture dir
- **Files modified:** scripts/bench/phase11.py, scripts/bench/tests/test_phase11_verdict.py
- **Verification:** full suite runs in ~0.6 s, hermetic
- **Commit:** ffdfc08 (amended by the same commit's follow-up fix in the working tree at commit ffdfc08)

**Total deviations:** 2 auto-fixed (both Rule 3 blockers inside this plan's own code). **Impact:** none on the pinned contracts — production behavior matches the plan's literals; both fixes are visible as injectable-with-pinned-defaults seams.

## Issues Encountered

- None beyond the two deviations above. The known `test_verify_threads.py` macOS flake did not fire in the full-suite run (716 tests OK).

## Known Stubs

None — every stage is fully implemented; no placeholder text, no unwired data paths, no TODO/FIXME markers introduced.

## Authentication Gates

None — no external services involved.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Ready for 12-02 (the full-scale live session): every stage function exists with the 0/1/2 contract, resume-by-explicit-args shape, and the doc layouts its gates hardcode pinned by unit tests. The 12-02 driver should run stages in the pinned order (`--stage revalidate --out 12-REVALIDATE.json` → `--stage parity --k 21 --round0 ... --out 12-PARITY-K21.json` → k31 → `--stage timed --k N --parity-doc ... --out 12-RESULTS-FULL-KN.json`), then reuse 12-01's verdict/render stages.
- Runtime expectations for 12-02 (from this plan's structures): round-0 hashes the manifest + 8 artifacts (~40 s) and checks 282 GiB free on the data volume (the D-12 session budget — exit 3 with a stated shortfall if under; `--disk-floor-override` for deliberate runs); parity runs 2 merges + 1 recount + 2 streamed deep-leg diffs per k; timed runs 9 measured merges per k with per-rep disk re-checks.
- MBENCH-03/MBENCH-04 intentionally remain open in REQUIREMENTS.md: both IDs are shared with 12-02/12-03 (shared-ID gate returned blocked for both; they flip when the last declaring plan's SUMMARY lands).
- Known flake reminder for 12-02's long session: `test_verify_threads.py` ~50% macOS `sample`-race flake — purge stale `target/` before trusting a red.

---
*Phase: 12-full-scale-merge-verdict*
*Completed: 2026-11-17*
