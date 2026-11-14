---
phase: 05-measurement-regression-harness
plan: 03
subsystem: infra
tags: [prof-02, rayon, thread-pool, regression-gate, golden-baseline, sha256, stdlib-python]

requires:
  - phase: 05-measurement-regression-harness
    plan: 01
    provides: "Shared bench.binary_provenance/fingerprint helpers and the freshness-bound expected-RED gate discipline (exit 1 = measured verdict, exit 2 = infra)"
provides:
  - "Hardened cross-platform verify_threads.py (macOS sample + Linux proc-task, structured --json records, requested=/observed= stdout lines, THREAD REALITY verdict line, exit 0/1/2)"
  - "PROF-02 pool-size test pair: characterization GREEN-now (pins the --threads no-op) + #[ignore]d standing gate RED-now (Phase 6 turns it green)"
  - "Freshness-bound RED thread-reality evidence (thread_reality_evidence.json): observed 18/17/17 at requested 1/4/16 with release-binary provenance"
  - "Immutable pre-refactor golden capture (capture_goldens.py + golden_capture.json): 12 fixture hashes + manifest sha256 + provenance, OUT-02 Phase 8 input"
affects: [05-04, 05-07, 06-parallelism, 07-engine, 08-output-parity]

actuals:
  tokens: 10078
  tasks: 2
  commits: 3
plan_head_before: 817531b95b2cb55aba1fcd3fab4d6345f8788cac
plan_head_after: 1efb5c7dab185361c3be252090edf09438a26610

tech-stack:
  added: []
  patterns:
    - "live-subprocess pool-size observation: one independent CLI child per requested N (rayon global init is once-per-process), polled until workers spawn, try/finally terminate+reap"
    - "characterization + standing-gate test pair: the baseline test is DESIGNED to fail once Phase 6 fixes the bug, forcing a conscious inversion; the gate's #[ignore] reason names PROF-02 and Phase 6"
    - "every pool-size assertion embeds requested=<N> observed=<M> so expected-RED is mechanically distinguishable from build/infra failure"
    - "golden capture is read-only: rehash + manifest equality, generator never invoked, fixtures never written"

key-files:
  created:
    - tests/thread_pool_size_tests.rs
    - scripts/bench/tests/test_verify_threads.py
    - scripts/bench/capture_goldens.py
    - .planning/phases/05-measurement-regression-harness/thread_reality_evidence.json
    - .planning/phases/05-measurement-regression-harness/golden_capture.json
  modified:
    - .planning/research/profiling/verify_threads.py

key-decisions:
  - "Helper --build-profile flag (default release) added so the Rust tests record honest debug provenance for CARGO_BIN_EXE_rustkmer; the dev-host evidence capture uses the release default"
  - "Helper exit-2 paths write NO JSON and print NO verdict line; unexpected exceptions are converted to exit 2 without a traceback (05-01 discipline) — a crashed run can never pass the freshness-bound RED check"
  - "Added scripts/bench/tests/test_verify_threads.py exit-contract suite: the TDD RED evidence classifier has no Rust libtest adapter, and every harness gate owns a stdlib unit suite; it supplied the machine-verified RED_EVIDENCE_OK"
  - "The intentional Phase-6 ignored gate is recorded in .planning/WINDOWS.md (skipped-test) so the ship gate sees the outstanding --threads fix"

patterns-established:
  - "Expected-RED capture is freshness-bound + process-outcome-bound + traceback-rejecting: delete prior JSON+log, require exit 1 AND fresh JSON AND this run's THREAD REALITY verdict=RED + requested=/observed= lines AND no Traceback"
  - "Golden immutability: capture rehashes committed fixtures and exits 1 naming any tampered fixture; manifest is never updated to make a diff green (D-10 / DENSE-02)"

requirements-completed: [PROF-02]

coverage:
  - id: D1
    description: "Hardened cross-platform thread observer: CLI args, macOS sample + Linux proc-task backends, polling, structured records, exit 0/1/2, machine-greppable verdict line"
    requirement: "PROF-02"
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_verify_threads.py (4 tests: exit-2/no-verdict contract + explicit sampler backends)"
        status: pass
      - kind: integration
        ref: "python3 .planning/research/profiling/verify_threads.py --binary target/release/rustkmer --threads 1 4 16 (freshness-bound, exit 1 + verdict=RED + no traceback)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Pool-size test pair with the expected GREEN/RED split: characterization pins the no-op in the default suite; standing gate is ignored with a Phase-6 reason and provably RED when run"
    requirement: "PROF-02"
    verification:
      - kind: integration
        ref: "cargo test --locked --test thread_pool_size_tests (1 passed; 0 failed; 1 ignored)"
        status: pass
      - kind: integration
        ref: "cargo test --locked --test thread_pool_size_tests -- --ignored (exit 101 + pool_size_matches_requested_threads FAILED + requested=1 observed=18)"
        status: pass
      - kind: other
        ref: "cargo test --locked --test thread_pool_size_tests --no-run (independent build prerequisite, exit 0)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Recorded RED thread-reality evidence with provenance: three records (1/4/16), top-level verdict RED, requested=1 observed > 2, release-binary sha256"
    requirement: "PROF-02"
    verification:
      - kind: other
        ref: "structured JSON check (verdict RED, requested [1,4,16], observed 18/17/17, 64-char sha256 == shasum of target/release/rustkmer, sampler sample)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Immutable pre-refactor golden capture: 12 fixture hashes equal to the committed manifest, golden test rc 0, fixtures byte-identical to HEAD, generator never invoked"
    requirement: "PROF-02"
    verification:
      - kind: integration
        ref: "python3 scripts/bench/capture_goldens.py --out golden_capture.json (exit 0) + structured check (12 fixtures, rc 0, 64-char manifest hash)"
        status: pass
      - kind: other
        ref: "git diff --stat tests/fixtures/ empty; manifest order+hash equality; grep golden_generate == 0"
        status: pass
    human_judgment: false

duration: 17min
completed: 2026-11-12
status: complete
---

# Phase 5 Plan 03: Thread-Reality Pool-Size Gates and Golden Capture Summary

**Live-subprocess PROF-02 test pair records the `--threads` no-op as a freshness-bound RED (observed 18/17/17 OS threads at requested 1/4/16 on the 16-core dev host) and captures the 12 pre-refactor golden `.rkdb` hashes with full provenance — no hot-path file touched, no fixture regenerated.**

## Performance

- **Duration:** 17 min
- **Started:** 2026-11-12T07:55:24Z
- **Completed:** 2026-11-12T08:12:42Z
- **Tasks:** 2
- **Files modified:** 6 (5 created, 1 rewritten; 910 insertions, 32 deletions across 3 commits)

## Accomplishments

- **`verify_threads.py` hardened in place** (was: hardcoded `/tmp` paths, fixed 4-second sleep, macOS-only prose): required `--binary/--input/--json` CLI, `--threads` (default 1 4 16), `--timeout-s` (default 30), macOS `sample` + Linux `/proc/<pid>/task` backends, polling until workers spawn, loud exit 2 if the child exits before observation, try/finally terminate+reap, process-unique tempdir outputs, structured per-N records with shared `binary_provenance`, top-level verdict, `requested=<N> observed=<M>` stdout lines + final `THREAD REALITY verdict=RED|GREEN` line (never on exit-2 paths). Infra failures exit 2 without a traceback.
- **`tests/thread_pool_size_tests.rs` test pair** driving the real CLI (`CARGO_BIN_EXE_rustkmer`) through the helper, one independent child per N (rayon global init is once-per-process): `pool_size_baseline_records_default_pool` (characterization, GREEN now, designed to FAIL once Phase 6 fixes the flag) and `pool_size_matches_requested_threads` (standing gate, `#[ignore]`d with the PROF-02/Phase-6 reason, RED now). Deterministic 100k-read LCG FASTQ fixture in `tempfile::tempdir()`; Windows returns early with an explicit platform-skip. Phase-6 handoff documented in the module doc.
- **RED evidence captured freshness-bound on the release binary** and committed: `thread_reality_evidence.json` — verdict RED, requested 1/4/16 → observed 18/17/17, provenance sha256 `8f64d442636871ee27173a4cc1c670a7e0d345ba6122a7582c08c13acf26c14f` equals `shasum -a 256 target/release/rustkmer`.
- **`capture_goldens.py` + `golden_capture.json`**: rehashed all 12 committed fixtures (k ∈ {21,32,64} × canonical × sorted), proved equality with `golden_manifest.sha256` in manifest order, ran `cargo test --locked --test golden_sha256_tests` (rc 0), recorded manifest sha256 `f010e42a…` + release provenance + the static-rehash limitation note for Phase 8 OUT-02. Generator never invoked; `git diff --stat tests/fixtures/` empty.
- Full harness suite **173 tests OK** (169 existing + 4 new); `rustfmt --check` and `cargo +1.82.0 clippy --locked --test thread_pool_size_tests -- -D warnings` clean; no orphan count processes after any run.

## Expected-RED Evidence (actual recorded output)

Prerequisites succeeded independently: `cargo test --no-run` exit 0; `cargo build --release --locked` exit 0 (18.4 s); synthetic 200k×150 seed-42 input generated; prior evidence JSON + helper log deleted and absence asserted before the capture.

**Standing gate (debug test binary):** `GATE_RC=101`, `EXPECTED-RED GATE VERIFY OK`

```text
test pool_size_matches_requested_threads ... FAILED
assertion `left == right` failed: PROF-02 pool-size mismatch: requested=1 observed=18
test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 1 filtered out
```

**Default suite:** `test result: ok. 1 passed; 0 failed; 1 ignored` — the ignored reason names PROF-02 and Phase 6.

**Release capture:** `HELPER_RC=1`, `EXPECTED-RED CAPTURE VERIFY OK`, `RED observation records OK`

```text
requested=1 observed=18
requested=4 observed=17
requested=16 observed=17
THREAD REALITY verdict=RED
```

No `Traceback` in the captured output; the JSON was freshly written by this run (deleted immediately before). Note: the plan's prose anticipated 17 at N=1; the live release binary shows 17–18 OS threads depending on transient auxiliary threads at sample time (18 at N=1 in both the gate run and the capture). The acceptance contract is `observed > 2` at requested=1 — satisfied; the no-op observation is unambiguous (16 workers + main regardless of the flag).

**Golden capture:** `CAPTURE_RC=0`, `golden capture OK`, `manifest order+hash equality OK` — 12 fixtures, golden test rc 0, fixtures byte-identical to HEAD, `grep golden_generate` == 0.

## Task Commits

Each task was committed atomically (TDD task 1 = RED + GREEN):

1. **Task 1 RED: pool-size observation tests + helper exit-contract suite** — `dcb3679` (test)
2. **Task 1 GREEN: hardened observer + RED thread-reality evidence** — `e34b56d` (feat)
3. **Task 2: immutable golden capture** — `1efb5c7` (feat)

REFACTOR: not needed — fmt/clippy clean after GREEN, no cleanup changes.

## TDD Gate Compliance

- **RED: PASS** — `dcb3679`. Machine verdict `RED_EVIDENCE_OK` (`gsd_run check tdd-red-evidence`, unittest format): target `test_invalid_binary_exits_2_without_verdict` executed and failed its planned assertion (`0 != 2` — the old helper ignores the new CLI and exits 0). Semantic assessment: genuine planned-behavior failure, not a load/build fault. The Rust pair was also run pre-implementation: `pool_size_baseline_records_default_pool` FAILED on its planned "helper must write JSON records" assertion (cargo exit 101, log retained in gitignored scratch) — libtest has no classifier adapter, so the unittest report is the machine-verified evidence.
- **GREEN: PASS** — `e34b56d` descends from `dcb3679`; default suite 1 passed/1 ignored, contract suite 4/4, full harness 173 OK.
- **REFACTOR:** not needed.
- Violations: none.

## Files Created/Modified

- `.planning/research/profiling/verify_threads.py` (rewritten, 49 → 254 lines) — hardened cross-platform observer; exit 0/1/2; structured records + verdict line
- `tests/thread_pool_size_tests.rs` (new, 232 lines) — characterization + standing gate; `requested=/observed=` assertion pattern; Phase-6 handoff doc
- `scripts/bench/tests/test_verify_threads.py` (new, 120 lines) — helper exit-2/no-verdict contract + sampler selection (4 stdlib tests)
- `scripts/bench/capture_goldens.py` (new, 178 lines) — read-only golden capture, fail-loud manifest equality
- `.planning/phases/05-measurement-regression-harness/thread_reality_evidence.json` (new) — RED evidence, 3 records + provenance
- `.planning/phases/05-measurement-regression-harness/golden_capture.json` (new) — 12 hashes + manifest sha256 + provenance + OUT-02 note
- `.planning/WINDOWS.md` — one `skipped-test` entry for the intentional Phase-6 ignored gate (ship-gate visibility)

## Decisions Made

- `--build-profile` flag (default `release`) so the Rust tests record honest `debug` provenance for the Cargo-built test binary; the dev-host capture keeps the plan's release default.
- Exit-2 paths write no JSON and print no verdict line; the `__main__` guard converts unexpected exceptions to exit 2 without a traceback — strengthening the plan's freshness/traceback contract at the source (05-01 precedent).
- The helper's provenance is computed once per run (same binary bytes for every N) and attached to each record; the input FASTQ is fingerprinted alongside.
- Execution context: `branching_strategy: none` — per `execute-phase/steps/protected-branch.md` the workflow warns and continues on `dev`; sequential executor on the main working tree, normal git hooks, no `--no-verify`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added helper exit-contract unit suite**
- **Found during:** Task 1 (TDD RED setup)
- **Issue:** The plan's `tdd="true"` task needs classifier-verifiable RED evidence, but the RED-evidence classifier has no Rust libtest adapter; additionally every other harness gate owns a stdlib exit-contract unit suite (05-PATTERNS) and the rewritten helper had none.
- **Fix:** Added `scripts/bench/tests/test_verify_threads.py` (4 stdlib tests: invalid binary / zero threads / nonpositive timeout → exit 2 with no verdict line; explicit sampler backends). It supplied the machine-verified `RED_EVIDENCE_OK` and runs in the default harness discover suite.
- **Files modified:** `scripts/bench/tests/test_verify_threads.py`
- **Verification:** RED `RED_EVIDENCE_OK` pre-implementation; 4/4 GREEN post; full suite 173 OK
- **Committed in:** `dcb3679` (RED), contract exercised by `e34b56d`

**2. [Rule 2 - Provenance correctness] Added `--build-profile` helper flag**
- **Found during:** Task 1 (helper design)
- **Issue:** The plan pins `build_profile "release"` for the dev-host capture, but the Rust tests drive the DEBUG `CARGO_BIN_EXE_rustkmer`; a hardcoded "release" would record dishonest provenance for those records.
- **Fix:** Optional `--build-profile` (default `release`); Rust tests pass `debug`. Dev-host capture unchanged.
- **Files modified:** `.planning/research/profiling/verify_threads.py`, `tests/thread_pool_size_tests.rs`
- **Verification:** evidence JSON records `build_profile: release` with sha256 equal to the actual release bytes
- **Committed in:** `e34b56d`

---

**Total deviations:** 2 auto-fixed (2 Rule 2).
**Impact on plan:** Both strengthen correctness (verifiable RED evidence, honest provenance). No scope creep; no hot-path, lockfile, or fixture changes (`git diff` over `src/`, `pyo3/src/`, both Cargo.locks, `tests/fixtures/` across the plan range: zero files).

## Issues Encountered

- The observed thread count at requested=1 is 18 (not the plan prose's 17): the release binary carries a transient auxiliary thread at sample time. Both the gate assertion (`!= requested+1`) and the evidence contract (`> 2`) are count-agnostic and satisfied; recorded honestly rather than massaged to 17.
- The old helper's RED runs printed "process already exited (too fast to sample)" for its hardcoded children — harmless for RED (the planned assertion is the missing JSON / wrong exit code, which failed exactly as intended).

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Phase 6 green-target ready:** un-ignore `pool_size_matches_requested_threads`, invert/remove `pool_size_baseline_records_default_pool`, and the 05-01 scaling gate goes green. The WINDOWS `skipped-test` entry tracks this handoff to ship time.
- **Phase 8 OUT-02 input ready:** `golden_capture.json` pins the 12 pre-refactor hashes + manifest sha256 + release provenance; the note records that a real old-vs-new write-path differential is still required.
- 05-04 can reuse the hardened helper and the `binary_provenance` pattern; its same-wave `bench.py` edits are additive and do not affect the helpers imported here.
- PROF-02 is shared with sibling plans (05-04/05-07); the shared-ID gate defers `Complete` until every declaring plan finishes.

## Self-Check: PASSED

- FOUND: all 6 artifact files (tests/thread_pool_size_tests.rs, scripts/bench/tests/test_verify_threads.py, .planning/research/profiling/verify_threads.py, scripts/bench/capture_goldens.py, thread_reality_evidence.json, golden_capture.json)
- FOUND commits: dcb3679, e34b56d, 1efb5c7 (all ancestors of HEAD; measured ledger count 3 == commits recorded)
- All Task 1 + Task 2 acceptance criteria re-run and passed; scope guard verified (zero hot-path/lockfile/fixture changes in the plan range)
- Stub scan: no TODO/FIXME/placeholder stubs; the single `#[ignore]` is the plan-mandated standing gate, ledgered in WINDOWS.md as a skipped-test with the Phase-6 resolution path

---
*Phase: 05-measurement-regression-harness*
*Completed: 2026-11-12*
