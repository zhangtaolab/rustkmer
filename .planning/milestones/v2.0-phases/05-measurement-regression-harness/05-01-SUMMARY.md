---
phase: 05-measurement-regression-harness
plan: 01
subsystem: infra
tags: [benchmark, provenance, thread-scaling, regression-gate, stdlib-python, rkdb]

requires:
  - phase: 04-benchmark-validation
    provides: "v1.0 stdlib harness (bench.py measure/reduce_arm/BenchmarkConfig, compare.py exit contract, schema-v1 results, committed per-platform baselines)"
provides:
  - "binary_provenance()/validate_provenance() shared builders in scripts/bench/bench.py for every later Phase 5 artifact"
  - "PROF-02 standing thread-scaling gate (scripts/bench/thread_scaling.py) with exit 0/1/2 contract, counterbalanced rotation_schedule, structured SCALING VERDICT stdout line"
  - "Freshness-bound expected-RED observation of the --threads no-op bug (tracer artifact scripts/bench/scratch/scaling_tracer.json, gitignored)"
  - "Mutation-proof verdict + provenance unit suites (34 tests) runnable without jellyfish/PyO3/human dataset"
affects: [05-02, 05-03, 05-04, 05-05, 05-06, 05-07, 06-parallelism, 07-engine, 09-python-parity, 10-verdict]

actuals:
  tokens: 11530
  tasks: 2
  commits: 2
plan_head_before: c357915e291b17e6e76ac21e4bb996ee4f34b688
plan_head_after: 7b537effe0592a8786abe48c79aba2eb5a0e9af4

tech-stack:
  added: []
  patterns:
    - "shared binary provenance on every results artifact (actual-bytes sha256 + git HEAD + dirty + profile + toolchain + platform)"
    - "strict separate provenance validator; SCHEMA_VERSION stays 1, validate_schema untouched"
    - "counterbalanced round-robin rotation_schedule persisted with raw reps"
    - "structured machine-greppable verdict line (repr round-trippable floats) printed only after validated doc write/load"
    - "exit 1 reserved for the measured verdict; infrastructure failures exit 2"

key-files:
  created:
    - scripts/bench/thread_scaling.py
    - scripts/bench/tests/test_thread_scaling.py
  modified:
    - scripts/bench/bench.py
    - scripts/bench/tests/test_schema.py

key-decisions:
  - "Infrastructure failures exit 2, never 1: the __main__ guard converts unexpected exceptions to EXIT_INVALID so an uncaught exception can never masquerade as the expected-RED observation"
  - "Warmup runs double as parity-gate outputs: parity asserted on warmup .rkdb files BEFORE any measured round; recorded per-arm counts re-read from the final measured outputs"
  - "Provenance git/rustc queries fail loud (raise with trailing stderr) instead of recording 'unknown'; binary path recorded resolved-absolute; git queries run from REPO_ROOT"
  - "Verdict arm lookup by -t1/-t4/-t16 name suffix with exactly-one-match rule (ambiguous duplicates are invalid, not first-match)"

patterns-established:
  - "Expected-RED verification is freshness-bound + process-outcome-bound + traceback-rejecting: delete prior doc+log, require exit 1 AND fresh doc AND 'SCALING VERDICT result=RED' in this run's captured output AND no Traceback"
  - "Gate unit tests drive main(argv) with --current hand-built docs (CompareHarness pattern); mutation tests change exactly one dimension and assert exit 2, never 0"

requirements-completed: [PROF-01, PROF-02]

coverage:
  - id: D1
    description: "Shared binary_provenance builder + strict validate_provenance wired into bench.py emission; v1 baselines stay loadable (SCHEMA_VERSION 1, validate_schema unchanged)"
    requirement: "PROF-01"
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_schema.py#TestProvenanceValidation (6 tests)"
        status: pass
      - kind: integration
        ref: "scripts/bench/tests/test_schema.py#TestRealRunProvenance.test_real_run_provenance_hashes_actual_binary"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_schema.py#TestLegacyBaselineCompatibility.test_committed_darwin_baseline_still_loads"
        status: pass
      - kind: other
        ref: "shasum -a 256 target/release/rustkmer == provenance.binary.sha256 (a6a9f2c6...7a8b99)"
        status: pass
    human_judgment: false
  - id: D2
    description: "PROF-02 standing thread-scaling gate: t1/t4/t16 counterbalanced rounds, parity-before-timing, provenance-bearing schema-v1 doc, exit 0/1/2 + structured verdict line; observably RED on the current --threads no-op tree"
    requirement: "PROF-02"
    verification:
      - kind: integration
        ref: "python3 scripts/bench/thread_scaling.py --mode synthetic --reads 500000 --reps 3 --out scripts/bench/scratch/scaling_tracer.json (freshness-bound, run twice: exit 1 + RED verdict + no traceback)"
        status: pass
      - kind: unit
        ref: "scripts/bench/tests/test_thread_scaling.py#TestVerdictMatrix (12 tests) + TestRotationSchedule (6 tests)"
        status: pass
      - kind: integration
        ref: "--measure-only exit 0 no-verdict smoke + --current verdict-only on both tracer and measure-only docs"
        status: pass
    human_judgment: false
  - id: D3
    description: "Mutation-proof verdict suites: count-only and timing-only mutations cannot fool the gate; SCALING VERDICT stdout contract pinned on every verdict path"
    requirement: "PROF-02"
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_thread_scaling.py#TestMutationProof (2 tests, exit 2 never 0)"
        status: pass
    human_judgment: false

duration: 37min
completed: 2026-11-12
status: complete
---

# Phase 5 Plan 01: Measurement Harness Tracer Summary

**Shared binary-provenance builder + PROF-02 thread-scaling gate wired end-to-end and proven to observe the `--threads` no-op bug as a structured, freshness-bound RED (speedup_t4 ~1.0, speedup_t16 ~1.05, both < 1.3) — the pattern every later Phase 5 gate replicates.**

## Performance

- **Duration:** 37 min
- **Started:** 2026-11-12T01:31:48Z
- **Completed:** 2026-11-12T02:09:10Z
- **Tasks:** 2
- **Files modified:** 4 (1015 insertions, 1 deletion)

## Accomplishments

- `binary_provenance()` / `validate_provenance()` in bench.py: actual-executable-bytes sha256 + git HEAD + dirty flag + build profile + rust toolchain + platform + UTC timestamp; strict separate validator; wired into `run_bench` emission. `SCHEMA_VERSION` stays 1 and `validate_schema` is untouched — committed v1 baselines still load.
- `thread_scaling.py`: standing PROF-02 gate with three modes (run+gate, `--measure-only`, `--current DOC`), parity-before-timing, one discarded warmup per arm, counterbalanced round-robin rounds (pure `rotation_schedule`, persisted schedule + per-rep round index + honest cache_state), medians via `reduce_arm`, provenance-bearing schema-v1 doc validated before write, and exactly one repr-round-trippable `SCALING VERDICT` stdout line per verdict (never on `--measure-only` or exit-2 paths).
- **Expected RED observed twice, end-to-end, on the current tree** (the milestone's smoking gun: `--threads` is a no-op). The gate is DONE because it correctly observes the bug; Phase 6 (PAR-01) turns it green. No hot-path file was touched.
- Mutation-proof unit suites (34 tests across the two files; full harness suite 158 tests OK): verdict matrix incl. inclusive 1.3 boundary + one-ulp probe, count-only/timing-only mutation proofs (exit 2, never 0), provenance positive/negative fixtures, real-run sha256-of-actual-bytes assertion, legacy-baseline compatibility, pure rotation coverage/rotation/wrap tests. No sleeps; stdlib only; no jellyfish/PyO3/human dataset needed.

## Expected-RED Evidence (actual recorded output)

Prerequisite `cargo build --release --locked` succeeded independently both times (41.6 s first, 0.06 s no-op re-run). Freshness precondition deleted prior doc+log and asserted absence before each gate run.

**Run 1 (Task 1 verify):** `GATE_RC=1`, `EXPECTED-RED VERIFY OK`, `tracer RED verdict OK`

```
rk21-t1: median wall 13.710s unique=64999000 total=65000000
rk21-t4: median wall 13.640s unique=64999000 total=65000000
rk21-t16: median wall 12.980s unique=64999000 total=65000000
SCALING VERDICT result=RED speedup_t4=1.0051319648093842 speedup_t16=1.0562403697996918 min_speedup=1.3
```

**Run 2 (tracer feedback gate, auto mode re-verify):** `GATE_RC=1`, `EXPECTED-RED VERIFY OK`, `tracer RED verdict OK`, `TRACER RE-VERIFY PASSED`

```
rk21-t1: median wall 13.490s reps=[13.65, 13.09, 13.49]
rk21-t4: median wall 13.810s reps=[13.0, 13.89, 13.81]
rk21-t16: median wall 12.790s reps=[13.38, 12.79, 12.42]
SCALING VERDICT result=RED speedup_t4=0.9768283852280956 speedup_t16=1.0547302580140736 min_speedup=1.3
```

Both runs: no `Traceback` in captured output; doc freshly written by that run; structured assertions passed (3 arms, RED verdict, speedups in (0, 1.3), identical nonzero counts 64,999,000 / 65,000,000 across arms, positive medians, 3-round rotation schedule covering each arm exactly once per round, every rep carrying its round index). Provenance sha256 `a6a9f2c6207bece2b4804672efb1f596296731adcf98fb4ba40d89c0657a8b99` equals `shasum -a 256 target/release/rustkmer`. Legacy `bench_baseline.darwin.json` loads under unchanged `validate_schema`.

Auxiliary-mode smoke: `--measure-only` exits 0 with a schema+provenance-valid doc, no verdict block and no verdict line; `--current` on both the tracer doc and the measure-only doc reproduces the RED verdict (exit 1) — the CI upload-then-verdict two-step works.

## Task Commits

Each task was committed atomically:

1. **Task 1: Provenance builder + thread-scaling gate, end-to-end RED** - `5b75891` (feat)
2. **Task 2: Schema/provenance and scaling-verdict unit suites (mutation-proof)** - `7b537ef` (test)

Tracer feedback gate (auto mode): full `<verify>` chain re-run end-to-end after Task 1's commit and before Task 2 — passed (`TRACER RE-VERIFY PASSED`).

## Files Created/Modified

- `scripts/bench/thread_scaling.py` (new, 492 lines) — PROF-02 standing gate; `rotation_schedule`, `scaling_verdict`, `verdict_line`, three modes; exit 1 reserved for the measured verdict, infra failures exit 2
- `scripts/bench/bench.py` (+109) — `binary_provenance`, `validate_provenance`, `_provenance_tool_output`; `"provenance"` key + `validate_provenance` call at the `run_bench` emission site
- `scripts/bench/tests/test_thread_scaling.py` (new, 308 lines) — verdict matrix + mutation + rotation suites (20 tests)
- `scripts/bench/tests/test_schema.py` (+107/-1) — provenance fixtures/tests, real-run binary-hash assertion, legacy-baseline test (8 new tests; original minimal v1 fixture and tests unchanged — the single deleted line is the import extended with `validate_provenance`)
- `scripts/bench/scratch/scaling_tracer.json` + `.log` — gitignored smoke artifacts (RED observation), intentionally not committed

## Decisions Made

- Infrastructure failures exit 2, never 1 (`__main__` guard converts unexpected exceptions to `EXIT_INVALID`) — an uncaught exception exiting 1 can never masquerade as the expected-RED observation. This strengthens the plan's freshness/traceback contract at the source.
- Warmup runs double as the parity gate's outputs: parity is asserted on the warmup `.rkdb` files before any measured round; recorded per-arm counts are re-read from the final measured outputs (defense in depth — `scaling_verdict` re-checks count equality).
- Provenance git/rustc queries fail loud (raise with trailing stderr, `measure()` style) rather than recording "unknown" — an unattributable artifact must never gate (T-05-02). Git queries run from `REPO_ROOT`; the binary path is recorded resolved-absolute.
- Verdict arm lookup matches `-t1`/`-t4`/`-t16` name suffixes with an exactly-one-match rule; ambiguous duplicates are invalid input, not first-match.
- Execution context: `branching_strategy: none` — per `execute-phase/steps/protected-branch.md` the workflow warns and continues on the current branch (`dev`); commits landed there as the project config directs. Sequential executor on the main working tree; normal git hooks, no `--no-verify`.

## Deviations from Plan

None - plan executed exactly as written. (Threat mitigations T-05-01 list-form argv and T-05-02 provenance validation are implemented as planned; no package installs — T-05-SC trivially satisfied.)

## Issues Encountered

- The first tracer re-verify launch used `set -e`, which is incompatible with the gate's expected exit 1; the job was stopped and relaunched with explicit per-step guards. The killed intermediate run left no doc and correctly FAILED the structured check — an unplanned live demonstration that the freshness binding rejects crashed/killed runs.
- One auxiliary-mode smoke command initially omitted the `--measure-only` flag and therefore ran the default gate (correctly RED); re-run with the flag confirmed the measure-only contract. No code change was needed for either issue.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for 05-02 (slice bench + parity gate): the shared `binary_provenance`/`validate_provenance` helpers and the gate pattern (freshness-bound structured verdict, counterbalanced rounds, exit 0/1/2) are in place to replicate.
- The PROF-02 gate is EXPECTED RED until Phase 6 (PAR-01) fixes `--threads`; CI wiring (05-07) must surface that intentional red without `continue-on-error`/`|| true`.
- Requirement marking: PROF-01/PROF-02 are shared with sibling plans (05-02/03/04/07); the shared-ID gate defers `Complete` until every declaring plan finishes.
- Note: local toolchain is nightly (rustc 1.101.0-nightly); provenance records it honestly. The Rust 1.80 MSRV toolchain install is a later Phase 5 plan (05-07 scope), not this tracer.

## Self-Check: PASSED

- FOUND: scripts/bench/bench.py, scripts/bench/thread_scaling.py, scripts/bench/tests/test_schema.py, scripts/bench/tests/test_thread_scaling.py
- FOUND commits: 5b75891, 7b537ef (both ancestors of HEAD; measured count 2 == ledger)
- All Task 1 + Task 2 acceptance criteria re-run and passed; full harness suite 158 tests OK

---
*Phase: 05-measurement-regression-harness*
*Completed: 2026-11-12*