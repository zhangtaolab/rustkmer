---
phase: 05-measurement-regression-harness
plan: 05
subsystem: infra
tags: [prof-03, contention, microbench, dashmap, atomics, attribution, provenance, stdlib-python, rkdb]

requires:
  - phase: 05-measurement-regression-harness
    plan: 01
    provides: "Shared bench.binary_provenance/validate_provenance + fingerprint helpers; counterbalanced rotation_schedule pattern; exit 0/1/2 gate discipline (infra failures never masquerade as the measured verdict)"
  - phase: 05-measurement-regression-harness
    plan: 02
    provides: "random_slice.reservoir_slice (seeded Algorithm R, deterministic FASTQ + selection manifest) for the representative real-read subslice"
provides:
  - "Four mechanism-isolating contention arms in the standalone microbench (shared-counter / shared-dashmap / atomic-only / thread-local) with per-rep conservation checks and JSON records; legacy positional mode preserved"
  - "Relocatable @REPO_ROOT@ manifest template + committed audited microbench_Cargo.lock (measured-mechanism closure aligned to the production lock; builds --locked; sha256 recorded in evidence)"
  - "scripts/bench/contention_bench.py controller: materialize/verify/build/provision/counterbalanced-measure/attribute/persist, exit 0 valid / 1 conservation / 2 invalid"
  - "contention_evidence.json (attribution-v1, Phase 7 design input): at t16 on real reads the global-atomics share is 120.22 ns/window (115.2% of the shared-vs-local gap); the bandwidth share is -15.82 ns, recorded with an honest inconclusive note; t16/t1 contention multiplier 1.877 on the 18M-distinct subslice"
affects: [05-07, 07-engine]

actuals:
  tokens: 868904
  tasks: 2
  commits: 4
plan_head_before: 125a91cda54145c35c60e6d9cbc43f83b76f21a3
plan_head_after: 1045f619d6170a28020cb33dc1b3f738ef53ab3b

tech-stack:
  added: []
  patterns:
    - "Mechanism isolation by subtraction: shared-counter (table + both global atomics) - shared-dashmap (table only) = global-atomics share; shared-dashmap - thread-local = bandwidth/locality share; atomic-only corroborates without entering the subtraction"
    - "Standalone measurement crate reproducibility: @REPO_ROOT@ template + committed audited Cargo.lock copied beside the materialized manifest, sha256-verified before every build, built --locked; path deps record no absolute paths so the lock is relocatable"
    - "Conservation recomputed from raw counts (the conservation_ok flag is never trusted); any failure invalidates the whole run (exit 1) and the microbench aborts without writing JSON — mutation-proven fail-capable"
    - "Honest attribution: negative/near-zero (<1% of gap) shares recorded as measured with inconclusive notes, never clamped; nonpositive total gap yields null percentages"

key-files:
  created:
    - scripts/bench/contention_bench.py
    - scripts/bench/tests/test_contention_bench.py
    - .planning/research/profiling/microbench_Cargo.lock
    - .planning/phases/05-measurement-regression-harness/contention_evidence.json
  modified:
    - .planning/research/profiling/microbench_main.rs
    - .planning/research/profiling/microbench_Cargo.toml

key-decisions:
  - "rust-version = 1.82 in the microbench manifest (plan literal said 1.80): the user-approved MSRV raise (quick 261112-jwl, commit 69a82cf) postdates planning; the rustkmer path dependency and locked graph require 1.82, so a 1.80 declaration would be false — documented deviation, corrected acceptance check"
  - "Lockfile alignment extended from the plan-named trio (dashmap/hashbrown/ahash) to the FULL runtime closure of the measured increment mechanism (crossbeam-utils, cfg-if, zerocopy+derive, libc, smallvec, wasip2, serde_json; tempfile/rustix/fastrand/linux-raw-sys aligned to unblock libc) — the resolver had drifted dashmap's padding/lock deps and ahash's zerocopy, which ARE the measured path; remaining drift (clap, bio nalgebra/statrs, indexmap's hashbrown 0.15/0.17, serde 1.0.229, rayon 1.12) is outside the measured region"
  - "Attribution shares computed at t16 (max measured thread count) where in-vivo contention manifests; formulas persisted as strings naming the actual thread counts; per-cell medians for all 12 cells persisted alongside the four headline fields"
  - "Thread-local arm times workers + end reduction together and presizes each private HashMap to its slice (steady-state local traffic, not growth rehash); the reduction cost is part of the control's definition — the negative bandwidth share is recorded honestly, not engineered away"
  - "Microbench conservation abort (child exit 1) maps to controller ConservationError (exit 1); any other child failure is infra (exit 2) — the run-level exit contract survives the subprocess boundary"

patterns-established:
  - "Measurement-critical dependency alignment: when a standalone crate measures a production mechanism, align the mechanism's full transitive runtime closure to the production lock via cargo update --precise, and record the boundary (what is aligned vs what is merely locked) in the SUMMARY"
  - "A measured share that contradicts the hypothesis (negative bandwidth share) is evidence, not a bug: persist it with the versioned formula and an inconclusive note so Phase 7 can weigh it instead of inheriting a clamped number"

requirements-completed: [PROF-03]

coverage:
  - id: D1
    description: "Four mechanism-isolating multi-thread arms with conservation checks, flag CLI + per-rep JSON, relocatable @REPO_ROOT@ template, committed audited lockfile; production crates untouched"
    requirement: "PROF-03"
    verification:
      - kind: integration
        ref: "planned verify chain: materialize + cargo build --release --locked + gen_synthetic 20000/150/42 + shared-counter t4 smoke + JSON field assertion (microbench smoke OK)"
        status: pass
      - kind: integration
        ref: "all four variants at --threads 4 on the smoke input: conservation-passing JSON records (ALL FOUR VARIANTS OK)"
        status: pass
      - kind: other
        ref: "mutation smoke: forced conservation mismatch -> exit 1 + CONSERVATION FAILURE + no JSON written (MUTATION RED OK); pristine source restored and rebuilt"
        status: pass
      - kind: other
        ref: "legacy positional 'rk-microbench 21 20000 C': key-identity check PASS, arm C runs (post_matrix.sh reproduction preserved)"
        status: pass
      - kind: other
        ref: "acceptance greps: @REPO_ROOT@=1, /Users/forrest=0, dashmap pin=1, lock dashmap=1 @6.2.1, git diff --stat Cargo.toml pyo3/Cargo.toml src/ empty"
        status: pass
    human_judgment: false
  - id: D2
    description: "contention_bench.py controller with pure attribution-v1 reduction, counterbalanced rotation, lockfile sha256 gate, exit 0/1/2 contract; 30-test unit suite runnable without cargo/PyO3/dataset"
    requirement: "PROF-03"
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_contention_bench.py (30 tests: exact arithmetic, honesty notes, conservation exit 1, missing-cell/malformed-JSON/lockfile-mismatch exit 2, rotation coverage/rotation/wrap)"
        status: pass
      - kind: integration
        ref: "python3 -m unittest discover -s scripts/bench/tests (241 tests OK)"
        status: pass
      - kind: integration
        ref: "synthetic controller smoke (--synthetic --reads 20000 --threads 1 4 --reps 1): exit 0, 8 records, negative bandwidth share honestly noted"
        status: pass
    human_judgment: false
  - id: D3
    description: "Real-read attribution-v1 evidence captured and committed: 200k random-record subslice (seed 20261112), 4 variants x t1/t4/t16 x 3 counterbalanced rounds, 36/36 conservation passes, lockfile sha256 + release provenance"
    requirement: "PROF-03"
    verification:
      - kind: integration
        ref: "python3 scripts/bench/contention_bench.py --input $RUSTKMER_REAL_INPUT --reads 200000 --seed 20261112 --threads 1 4 16 --reps 3 --out contention_evidence.json (exit 0, freshness-bound)"
        status: pass
      - kind: other
        ref: "planned structured check: method attribution-v1, all named fields, 3-round schedule, lockfile sha256 == committed lock, all records conservation_ok (contention evidence OK)"
        status: pass
      - kind: other
        ref: "schedule coverage (each round = all 12 cells exactly once, rotated starts), per-rep round/cache_state tags, source fingerprint dae91042 == 05-04 measured source"
        status: pass
    human_judgment: false

duration: 31min
completed: 2026-11-12
status: complete
---

# Phase 5 Plan 05: Contention Microbench and Attribution Evidence Summary

**Four mechanism arms isolate the in-vivo increment multiplier on real reads: at t16 the global-atomics share is 120.22 ns/window (115.2% of the shared-vs-local gap) while the bandwidth share is -15.82 ns — recorded with an honest inconclusive note, never clamped — and the t16/t1 multiplier on the 18M-distinct subslice is 1.877; the evidence is persisted as attribution-v1 with a committed audited lockfile (sha256 eabd946a…) for Phase 7's engine design.**

## Performance

- **Duration:** 31 min
- **Started:** 2026-11-12T09:15:30Z
- **Completed:** 2026-11-12T09:46:06Z
- **Tasks:** 2
- **Files modified:** 6 (4 created, 2 modified; 4 commits)

## Accomplishments

- **Microbench extended with four mechanism arms** (`shared-counter`, `shared-dashmap`, `atomic-only`, `thread-local`) over the same pre-encoded canonical key vector split into disjoint per-worker ranges (`std::thread::scope`, every handle joined, every Result propagated). The shared-counter arm calls the production `KmerCounter::increment` unchanged — both global atomics included; the private counter table was never made public and no production file was edited. Per-rep conservation (sum of counts == windows AND unique == precomputed distinct) aborts exit 1 with a loud error and NO JSON on failure — proven fail-capable by a mutation smoke. Flag CLI (`--k --reads --threads --reps --variant --input --json`) with per-rep JSON records; the legacy positional mode (`rk-microbench 21 200000 ABCDE`) still parses and passes the key-identity check.
- **Reproducible standalone crate:** the manifest is now a relocatable `@REPO_ROOT@` template (zero absolute checkout pins) with direct `dashmap = "=6.2.1"` + `serde_json = "1.0"` (both already in production lockfiles — no new external packages). The committed audited `microbench_Cargo.lock` was generated via `cargo generate-lockfile`, its measured-mechanism closure aligned to the production root lock via `cargo update --precise`, sha256-verified before every build, and built `--locked`. Path deps record no absolute paths, so the lock is relocatable across checkouts.
- **Controller + TDD unit suite:** `contention_bench.py` materializes the template (repo root resolved from its own `__file__`, T-05-09), verifies the scratch lock's sha256 against the committed lock (mismatch/missing → exit 2, never an unlocked build), provisions a real random-record subslice via `reservoir_slice`, runs one discarded warmup per cell then counterbalanced rotated rounds (pure `rotation_schedule`, persisted schedule + per-rep round index + honest `cache_state`), reduces medians across rounds, and computes the attribution-v1 split via the pure, unit-tested `attribute(records)`. Conservation is RECOMPUTED from raw counts — the flag alone is never trusted. 30 new unit tests (exact hand-built arithmetic, negative/near-zero honesty notes, exit-code contract, rotation coverage/wrap, lockfile integrity); full harness suite **241 tests OK**.
- **Real-read evidence captured and committed** (`contention_evidence.json`, Phase 7 input): 200,000 randomly selected records from CRR1936095 part_001 (seed 20261112, source indices 531 … 34,540,762 — uniform over the full 2.78 GB source, not a head prefix), 25,959,989 windows / 18,026,712 distinct (ratio 1.44), 4 variants × t1/t4/t16 × 3 rounds = 36 raw reps, **36/36 conservation passes**, release-binary provenance (git 4ca7848, clean) and lockfile sha256 matching the committed audited lock.

## Measured Attribution (actual recorded numbers)

Per-cell medians, ns/window (real reads, warm cache, no sudo — per-rep `cache_state=unavailable`):

| variant | t1 | t4 | t16 |
|---|---|---|---|
| shared-counter (production path) | 76.16 | 65.74 | 142.95 |
| shared-dashmap (no global atomics) | 66.54 | 33.11 | 22.73 |
| atomic-only (no table) | 2.72 | 7.07 | 56.84 |
| thread-local (+ end reduction) | 89.76 | 43.39 | 38.55 |

Attribution-v1 at t16 (formulas persisted as strings in the evidence `method` block):

- `global_atomics_attribution_ns` = 142.95 − 22.73 = **120.21998225808184** (**115.15754614691627%** of the 104.40 ns shared-vs-local gap)
- `memory_bandwidth_attribution_ns` = 22.73 − 38.55 = **-15.82388640457436** (**-15.157546146916289%**) — recorded as measured with the note: *"inconclusive: memory-bandwidth share is -15.82 ns/window <= 0 — the subtraction does not isolate this mechanism on this host; recorded as measured, not clamped"*
- `contention_multiplier` = shared_counter(t16)/shared_counter(t1) = **1.8768642164029798**
- Corroboration: atomic-only traffic alone costs 56.84 ns/window at t16 (vs 2.72 at t1); removing the global atomics lets the raw shared table scale 66.54 → 22.73 ns/window (2.9x) from t1 to t16.

**Comparison to the research's ~9.4x in-vivo multiplier (context, not a recomputation):** the measured t16/t1 multiplier here is 1.88x, far below the in-vivo 916/97.3 ≈ 9.4x. Two regime differences explain the gap: (1) working set — this subslice's 18M-distinct table (~0.3 GB) is far more cache-resident than the in-vivo 4M-read slice's 229M-distinct multi-GB DRAM regime that produced 916 ns/window; (2) the microbench isolates pure increment traffic (pre-encoded keys, static disjoint ranges) and strips the rayon chunking/spin-wait overhead that was 59% of the in-vivo profile. The DIRECTION is consistent and is the Phase 7 takeaway: global atomics are the dominant isolable cost (115% of the gap at t16 — the shared table without them scales cleanly), while the bandwidth/locality share is NOT demonstrable at this working set (negative → inconclusive). Phase 7 should read the split as "atomics dominant; bandwidth unproven at 18M distinct" and re-measure at DRAM scale if the bandwidth share becomes decision-critical. The thread-local control's timed region includes its end reduction (per the plan's arm definition), which is part of why it does not beat the raw shared table here.

## Task Commits

Each task was committed atomically (Task 2 TDD = RED + GREEN + evidence capture):

1. **Task 1: multi-thread mechanism arms + template + audited lockfile** — `a030e26` (feat)
2. **Task 2 RED: failing attribution/exit-contract tests** — `088750f` (test)
3. **Task 2 GREEN: contention controller** — `4ca7848` (feat)
4. **Task 2 evidence: real-read attribution capture** — `1045f61` (feat)

REFACTOR: not needed — the GREEN implementation remained clear and all tests passed.

## TDD Gate Compliance

- **RED: PASS** — `088750f`. Machine verdict `RED_EVIDENCE_OK` (`gsd_run check tdd-red-evidence`, unittest format): 30 tests discovered, 30 FAIL headers, 0 ERROR headers; target `TestAttributionArithmetic.test_exact_arithmetic_on_hand_built_medians` executed and failed its planned assertion (`contention_bench not implemented yet (05-05)` — guarded import, so a genuine planned-behavior failure, not a collection/import fault). Evidence retained at `scripts/bench/scratch/05-05-task2-red-evidence.json` (gitignored).
- **GREEN: PASS** — `4ca7848` descends from `088750f`; 30/30 contention tests pass, full harness 241 OK.
- **REFACTOR:** not needed.
- Violations: none.

## Files Created/Modified

- `.planning/research/profiling/microbench_main.rs` (modified, 203 → 562 lines) — four contention arms, flag CLI, per-rep JSON, conservation gates; legacy A–E mode and key-identity check preserved
- `.planning/research/profiling/microbench_Cargo.toml` (modified) — `@REPO_ROOT@` template, `dashmap = "=6.2.1"`, `serde_json = "1.0"`, `rust-version = "1.82"`, isolated `[workspace]` + release profile verbatim
- `.planning/research/profiling/microbench_Cargo.lock` (new, 204 packages) — committed audited graph; measured-mechanism closure aligned to production; sha256 `eabd946ad93b9a52ff7f60c0993d15aa10eb2bb83540c9d5a8704289717503c0`
- `scripts/bench/contention_bench.py` (new, 621 lines) — controller; `attribute(records)`, `rotation_schedule(cell_names, reps)`, `materialize_crate`, `verify_scratch_lockfile`, `load_microbench_json`, `validate_records`; exit 0/1/2
- `scripts/bench/tests/test_contention_bench.py` (new, 397 lines) — 30 stdlib tests, no cargo/PyO3/dataset
- `.planning/phases/05-measurement-regression-harness/contention_evidence.json` (new) — 36 raw reps + schedule + attribution-v1 + provenance + lockfile sha256 + selection manifest (the 200k-index manifest is the bulk of the file)
- Runtime scratch (materialized crate, smoke inputs/JSONs, capture log, RED evidence) lives under gitignored `scripts/bench/scratch/`

## Decisions Made

- **MSRV 1.82 in the manifest** (plan literal: 1.80) — see Deviations; the orchestrator's dispatch notes confirm "MSRV now 1.82".
- **Lockfile alignment boundary:** the plan named dashmap/hashbrown/ahash; the resolver had also drifted dashmap's padding/lock deps (crossbeam-utils, cfg-if) and ahash's zerocopy, which are ON the measured increment path, so the full mechanism closure was aligned (plus serde_json, the named direct dep; tempfile/rustix/fastrand/linux-raw-sys aligned to unblock libc). Remaining drift is outside the measured region and recorded here: clap 4.6.7, bio's nalgebra/statrs, indexmap's hashbrown 0.15.5/0.17.1, serde 1.0.229, rayon 1.12.0 (rayon is compiled but unused by the arms — std threads).
- **Attribution at t16** with formulas naming the actual thread counts; all 12 per-cell medians persisted alongside the four headline fields.
- **Thread-local control** times workers + end reduction and presizes private tables to their slices — the plan's arm definition, kept faithful even though it makes the bandwidth share negative here; honesty note instead of engineering the number.
- **Child exit-code mapping:** microbench conservation abort (exit 1) → controller exit 1; any other child failure → exit 2.
- Execution context: `branching_strategy: none` — per `execute-phase/steps/protected-branch.md` the workflow warns and continues on `dev`; sequential executor on the main working tree, normal git hooks, no `--no-verify` (05-01..04 precedent).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking policy conflict] rust-version 1.82 instead of the plan's literal 1.80**
- **Found during:** Task 1 (manifest edit)
- **Issue:** The plan (and its acceptance grep) hardcodes `rust-version = "1.80"`, but the user-approved MSRV raise to 1.82 (quick 261112-jwl, commit `69a82cf`) landed AFTER planning: the rustkmer path dependency declares 1.82 and the locked graph (indexmap/proptest) requires it. A 1.80 declaration would be false — a 1.80 toolchain cannot build this crate regardless of its own declaration.
- **Fix:** `rust-version = "1.82"` with an explanatory manifest comment; the acceptance check is corrected to `grep -c 'rust-version = "1.82"' == 1` (passes). The orchestrator's dispatch notes explicitly flag "MSRV now 1.82, Rust 1.82.0 installed".
- **Files modified:** `.planning/research/profiling/microbench_Cargo.toml`
- **Verification:** `--locked` release build exit 0 on the default nightly toolchain (rustc 1.101.0-nightly, matching the research evidence provenance); 1.82.0 toolchain installed locally
- **Committed in:** `a030e26`

**2. [Rule 2 - Measurement fidelity] Lockfile alignment extended to the measured mechanism's full runtime closure**
- **Found during:** Task 1 (lockfile audit)
- **Issue:** Fresh resolution drifted not just the plan-named trio but dashmap's hot-path-adjacent deps (crossbeam-utils 0.8.23 vs 0.8.21, cfg-if 1.0.5 vs 1.0.4) and ahash's zerocopy (0.8.63 vs 0.8.31), plus libc/smallvec — all compiled into the measured increment path.
- **Fix:** `cargo update --precise` alignment of the full mechanism closure to the production lock (dashmap 6.2.1, hashbrown 0.14.5, ahash 0.8.12, crossbeam-utils 0.8.21, cfg-if 1.0.4, zerocopy+derive 0.8.31, libc 0.2.178, smallvec 1.15.1, wasip2 1.0.2, serde_json 1.0.145; tempfile 3.24.0/rustix 1.1.3/fastrand 2.3.0/linux-raw-sys 0.11.0 to unblock libc). Verified every closure crate's micro version exists in the production lock; out-of-closure drift documented (Decisions).
- **Files modified:** `.planning/research/profiling/microbench_Cargo.lock`
- **Verification:** closure-comparison script (all OK); `--locked` build exit 0; evidence lockfile sha256 equals the committed lock
- **Committed in:** `a030e26`

---

**Total deviations:** 2 auto-fixed (1 Rule 3, 1 Rule 2).
**Impact on plan:** Both strengthen measurement honesty/reproducibility; no scope creep. `git diff --stat src/ pyo3/src/ Cargo.toml pyo3/Cargo.toml` empty across the plan range — production crates and the private counter table untouched. Threat mitigations satisfied: T-05-09 (repo root from controller `__file__`, list-form argv, gitignored scratch), T-05-10 (conservation recomputed from raw counts; mutation-proven abort), T-05-SC (no new external packages — dashmap/serde_json already in production locks; `--locked` from the committed audited lock with sha256 in evidence).

## Issues Encountered

- **Precondition env var not persisted:** `RUSTKMER_REAL_INPUT` is not exported in the shell profile; the dataset file exists at the exact path the plan documents (verified read-only, 2,785,381,389 bytes). The capture command exported the documented path inline before `test -f` — same fulfillment as 05-04. Precondition substance (real data present) met.
- **Negative bandwidth share:** the measured shared-dashmap − thread-local difference at t16 is negative on this working set. This is the plan's anticipated honesty path (behavior block: "Negative or near-zero shares are recorded honestly with an inconclusive note, never clamped"), not a defect — the evidence carries the note and the formula so Phase 7 can weigh it. The synthetic smoke showed the same shape (all-unique keys make the thread-local reduction dominate), confirming the mechanism before the real capture.
- **Pre-existing dead-code warning:** `rc_bits` was already unused in the original research microbench (rolling_canonical maintains its own rolling revcomp); kept verbatim — the warning predates this plan and the helper documents the bit-parallel approach.
- The ~13-minute real capture (reservoir pass over the 2.78 GB source + 48 microbench runs + cooldowns) exceeded the foreground command cap, so it ran as a single background job (05-04 precedent), freshness-bound: prior evidence deleted and absence asserted before the run.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Phase 7 engine design input ready:** `contention_evidence.json` records the atomics-vs-bandwidth split as numeric, versioned, provenance-bearing evidence. Read it as: global atomics are the dominant isolable cost at t16 (115% of the shared-vs-local gap; atomic-only traffic alone is 56.8 ns/window); the bandwidth share is inconclusive at 18M distinct — re-measure at DRAM scale (e.g. the 4M-read/229M-distinct regime) if it becomes decision-critical before choosing the partition/queue design.
- **Reproducibility:** the microbench rebuilds from the repo alone — template + committed audited lock, `--locked`, sha256 recorded; `contention_bench.py --input <gz> --reads 200000 --seed 20261112` reproduces the capture recipe.
- **05-07 (CI wiring):** the contention unit suite (30 tests) runs in the default harness discover suite without cargo/PyO3/dataset; the real capture stays a dev-host/real-data gate (synthetic is smoke-only by design).
- PROF-03 is declared only by this plan — marked complete immediately (no shared-ID deferral).

## Self-Check: PASSED

- FOUND: .planning/research/profiling/microbench_main.rs, .planning/research/profiling/microbench_Cargo.toml, .planning/research/profiling/microbench_Cargo.lock, scripts/bench/contention_bench.py, scripts/bench/tests/test_contention_bench.py, .planning/phases/05-measurement-regression-harness/contention_evidence.json
- FOUND commits: a030e26, 088750f, 4ca7848, 1045f61 (all ancestors of HEAD; measured ledger count 4 == commits recorded)
- All Task 1 + Task 2 acceptance criteria re-run and passed (rust-version check corrected per Deviation 1); full harness suite 241 tests OK; plan-level verification checklist satisfied (formulas persisted, 36/36 conservation, real reads + provenance + honest cache state, --locked + sha256, counterbalanced schedule, production untouched)
- Stub scan: no TODO/FIXME/placeholder stubs (the two "placeholder" grep hits are the wired @REPO_ROOT@ template mechanism). No Known Stubs; no WINDOWS entries warranted (no skipped tests, no unrun verifies — the inconclusive note is a measured result, not a defect).

### Actuals note

`actuals.tokens` (868,904) is the honest chars/4 measurement over the FULL realized diff (3,475,617 chars), dominated by the machine-generated evidence JSON (200,825 lines — mostly the 200k-index selection manifest) and the audited lockfile. The authored code+tests portion (microbench_main.rs + microbench_Cargo.toml + contention_bench.py + test_contention_bench.py) is 67,763 chars ≈ **16,941 tokens** — the meaningful work-cost figure for calibration against the 32,000-token estimate. Both reported unrounded.

---
*Phase: 05-measurement-regression-harness*
*Completed: 2026-11-12*
