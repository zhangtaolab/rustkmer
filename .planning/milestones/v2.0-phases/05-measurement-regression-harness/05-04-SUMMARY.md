---
phase: 05-measurement-regression-harness
plan: 04
subsystem: infra
tags: [prof-01, parity-gate, reservoir-sampling, provenance, thread-scaling, regression-gate, jellyfish, stdlib-python]

requires:
  - phase: 05-measurement-regression-harness
    plan: 01
    provides: "Shared bench.binary_provenance/validate_provenance + fingerprint helpers; thread_scaling.py gate (exit 0/1/2, counterbalanced rounds, SCALING VERDICT line); freshness-bound expected-RED discipline"
  - phase: 05-measurement-regression-harness
    plan: 02
    provides: "random_slice.reservoir_slice (seeded Algorithm R, deterministic FASTQ + selection manifest with source fingerprint/seed/indices/output_sha256)"
provides:
  - "bench.py random-record subslicing (--slice-selection random / --slice-seed) with sidecar selection manifests; head selection byte-compatible"
  - "Fingerprint-bound parity-reference gate: load_parity_reference / gate_parity_reference / capture_parity_reference / selection_identity_from; PARITY_PINNED_HEAD4M single-source constant; --hash-size threaded into run_parity; --parity-only --out parity-record emission"
  - "Committed slice_parity.crr1936095.json: head-4M pinned record (229694874/519271168) + 1M random-record (seed 20261112, live-derived 73578421/129801125) bound to seed + selection_manifest_sha256 + output_sha256"
  - "slice_parity_evidence.json: both provenance-bearing parity passes (head + random gate-proof re-runs, exit 0)"
  - "thread_scaling_baseline.json: real-slice t1/t4/t16 RED baseline (speedup_t4 1.0318 / speedup_t16 1.0505) — the standing number Phase 6 must beat"
affects: [05-05, 05-06, 05-07, 06-parallelism, 07-engine, 10-verdict]

actuals:
  tokens: 10354895
  tasks: 2
  commits: 3
plan_head_before: 65b4856fd6aaccb431fb8f136bbe92ca40807f53
plan_head_after: 319b80782a1a60dc84475b14f68129b6ce1d650e

tech-stack:
  added: []
  patterns:
    - "Parity reference bound to the FULL random recipe: source_sha256 + slice_kind + reads + k + canonical PLUS seed + selection_manifest_sha256 + live-recomputed output_sha256; wrong seed/manifest/output, missing identity, or duplicate full-key all exit 2"
    - "Pinned head-4M constants live in one module constant (PARITY_PINNED_HEAD4M) copied from evidence.json; capture asserts them before writing — a changed dataset is exit 1, never a re-pin"
    - "Gate-time selection identity recomputes the slice output hash LIVE and cross-checks the sidecar manifest before matching"
    - "Real-data parity gates use --hash-size 2G (the 1G smoke default silently penalizes the 229M-distinct slice)"
    - "Expected-RED scaling capture is freshness-bound + process-outcome-bound + traceback-rejecting + cross-log exact-float (repr round-trip)"

key-files:
  created:
    - scripts/bench/baselines/slice_parity.crr1936095.json
    - .planning/phases/05-measurement-regression-harness/slice_parity_evidence.json
    - .planning/phases/05-measurement-regression-harness/thread_scaling_baseline.json
  modified:
    - scripts/bench/bench.py
    - scripts/bench/tests/test_degradation.py

key-decisions:
  - "slice_kind_for returns None for head selections other than the pinned 4M recipe (rather than the plan's literal 'otherwise random-record'); the gate/capture flow rejects them loudly so a head prefix is never mislabeled a random sample"
  - "capture_parity_reference rejects an already-referenced EXACT recipe (exit 2) instead of appending a duplicate full-key record that would brick the gate; re-capture requires explicit deletion"
  - "--parity-reference / --capture-parity-reference require --parity-only, are mutually exclusive, and are slice-mode-only — an explicit CLI contract, never a silent ignore"
  - "load_parity_reference validates provenance on EVERY reference record (T-05-02: an unattributable reference must never gate) and requires random records to carry a selection_manifest consistent with their identity fields"
  - "Scaling scratch (slice-0.fq + three 4.59 GB .rkdb) is written under the phase dir by thread_scaling's --out parent; removed after verification — only the JSON baseline is committed (.rkdb is gitignored, the slice is reproducible runtime output)"

patterns-established:
  - "Random subslice representativeness is measured, not assumed: the 1M random sample's distinct/instance ratio is 1.76 vs the head-4M's 2.26, confirming the head is repeat-rich (CONTEXT) without invalidating the pinned historical reference"
  - "A parity reference is a gate input, not a convenience: every record is fingerprint-bound, provenance-validated, and exact-match (ambiguity is invalid, never first-match-wins)"

requirements-completed: [PROF-01]

coverage:
  - id: D1
    description: "bench.py random-selection + fingerprint-bound parity-reference gate (load/gate/capture/identity helpers, PARITY_PINNED_HEAD4M, --hash-size threading, parity-record emission), proven by fixture tests without the dataset or jellyfish"
    requirement: "PROF-01"
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_degradation.py (38 new tests: TestParityReferenceGate, TestRandomReferenceBinding, TestSelectionIdentity, TestParityCapture, TestRandomProvisioning, TestHeadBackwardCompat, TestPinnedConstants, TestHashSizeThreading)"
        status: pass
      - kind: unit
        ref: "python3 -m unittest scripts.bench.tests.test_degradation scripts.bench.tests.test_schema -v (82 tests OK)"
        status: pass
      - kind: integration
        ref: "python3 -m unittest discover -s scripts/bench/tests (211 tests OK)"
        status: pass
      - kind: integration
        ref: "bench.py --mode synthetic --reads 20000 --parity-only --out parity_smoke.json + validate_provenance (PARITY OK distinct=2400000; parity record OK)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Real-data parity gates proven on the measured CRR1936095 input: head-4M pinned parity + gate-proof, 1M random subslice parity + gate-proof, committed reference + evidence with provenance"
    requirement: "PROF-01"
    verification:
      - kind: integration
        ref: "head-4M capture: PARITY OK distinct=229694874 total=519271168 (pinned assertion passed), exit 0"
        status: pass
      - kind: integration
        ref: "head gate-proof --parity-reference: PARITY REFERENCE OK, exit 0"
        status: pass
      - kind: integration
        ref: "random 1M (seed 20261112) capture: PARITY OK distinct=73578421 total=129801125, exit 0; gate-proof --parity-reference: PARITY REFERENCE OK, exit 0"
        status: pass
      - kind: other
        ref: "baseline structure verify (parity baseline OK) + slice_parity_evidence.json provenance check (binary sha256 + git HEAD + dirty + profile on both records)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Real-slice t1/t4/t16 RED scaling baseline captured freshness-bound with honest cache-state and provenance — the standing Phase 6 target"
    requirement: "PROF-01"
    verification:
      - kind: integration
        ref: "thread_scaling.py --mode slice --slice-reads 4000000 --reps 2 (freshness-bound: prior baseline+logs deleted; exit 1 + fresh doc + SCALING VERDICT result=RED + no traceback)"
        status: pass
      - kind: integration
        ref: "thread_scaling.py --current baseline (exit 1 + SCALING VERDICT result=RED + no traceback)"
        status: pass
      - kind: other
        ref: "structured RED check (validate_schema + validate_provenance; verdict RED; speedups in (0,1.3); identical nonzero cross-arm counts; positive medians; 2-round schedule; both logs' speedups exactly equal the doc's stored floats): RED baseline verdict OK"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-11-12
status: complete
---

# Phase 5 Plan 04: Random-Selection Parity Gate and Real-Data RED Baseline Summary

**Random-record subslicing and a fingerprint-bound parity-reference gate wired into bench.py (additive, SCHEMA_VERSION 1), then proven on the measured CRR1936095 input: head-4M pinned parity 229,694,874 / 519,271,168 vs jellyfish 2.3.1, a 1M random subslice with its own live-derived reference (73,578,421 / 129,801,125, seed 20261112), and the real-slice t1/t4/t16 scaling baseline recorded RED (speedup_t4 1.0318 / speedup_t16 1.0505) — the standing number Phase 6 must beat.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-11-12T08:19:48Z
- **Completed:** 2026-11-12T09:05:26Z
- **Tasks:** 2
- **Files modified:** 5 (2 code/test, 3 data artifacts)

## Accomplishments

- **bench.py extended additively** (no hot-path file touched; `SCHEMA_VERSION` stays 1, `validate_schema` untouched): `--slice-selection {head,random}` / `--slice-seed` (default 20261112) with `provision_random_slice` wrapping Plan 02's `reservoir_slice` and writing sidecar manifests; head selection byte-compatible (`extract_slice` unchanged). `PARITY_PINNED_HEAD4M = {distinct: 229694874, total: 519271168}` is the single-source pinned constant copied from `evidence.json`. `--hash-size` is threaded through `run_parity_cli` into `run_parity` (real runs use 2G; the 1G smoke default silently penalizes the 229M-distinct slice).
- **Fingerprint-bound parity-reference gate:** `load_parity_reference` matches the exact key (source_sha256, slice_kind, reads, k, canonical) PLUS the full random selection identity (seed + selection_manifest_sha256 + output_sha256); unbound/missing-identity/ambiguous records exit 2, never a silent fallback or first-match-wins. `selection_identity_from` recomputes the slice output hash LIVE and cross-checks the sidecar manifest. `gate_parity_reference` exits 1 on a count mismatch (printing both sides). `capture_parity_reference` writes only after a live parity pass, asserts the pinned head-4M counts first (exit 1 on a changed dataset), and rejects duplicate full-key captures. `--parity-only --out` emits a provenance-bearing parity record.
- **Real-data gates proven on the measured input** (source `CRR1936095_r1.part_001.fq.gz`, 2,785,381,389 bytes, sha256 `dae91042…`): head-4M pinned parity captured and gate-proven (exit 0); a representative 1M random subslice (seed 20261112) captured with its own live-derived jellyfish reference and gate-proven (exit 0). Both gate-proof re-runs loaded the committed reference and matched. The random sample's distinct/instance ratio is **1.76** vs the head-4M's **2.26** — measured confirmation that the head is repeat-rich, without invalidating the pinned historical reference.
- **Real-slice RED scaling baseline committed:** t1/t4/t16 medians 72.27 / 70.05 / 68.80 s (research matrix expected ~65-75 s per arm), speedup_t4 1.0318 and speedup_t16 1.0505 (both < 1.3), identical nonzero counts 229,694,874 / 519,271,168 across arms, honest warm-cache `cache_state=unavailable` (no sudo), counterbalanced 2-round rotation, full provenance. Freshness-bound capture (prior baseline + both logs deleted first), exit 1 with the `SCALING VERDICT result=RED` line in both the capture and `--current` logs, no traceback, and both logs' speedups exactly equal the doc's stored floats.
- **38 new fixture tests** (no real dataset, no jellyfish, no binary) cover every rejection case; full harness suite **211 tests OK**. TDD RED machine-verified (`RED_EVIDENCE_OK`) before GREEN.

## Real-Data Evidence (actual recorded output)

Independent release-build prerequisite: `cargo build --release --locked` exit 0 (0.22 s no-op; src unchanged), binary sha256 `8f64d442636871ee27173a4cc1c670a7e0d345ba6122a7582c08c13acf26c14f`. Precondition verified read-only: `RUSTKMER_REAL_INPUT` file present; `/opt/homebrew/bin/jellyfish --version` = 2.3.1.

**Head-4M pinned parity capture** (`--slice-selection head --slice-reads 4000000 --k 21 --hash-size 2G --parity-only --capture-parity-reference`), exit 0:

```
PARITY OK distinct=229694874 total=519271168
parity reference captured: kind=head-4M-profiling-reference reads=4000000 distinct=229694874 total=519271168
```

**Head gate-proof** (`--parity-reference`, no capture), exit 0:

```
PARITY OK distinct=229694874 total=519271168
PARITY REFERENCE OK distinct=229694874 total=519271168 (bound to source dae91042e42c… kind=head-4M-profiling-reference)
```

**Random 1M subslice capture** (`--slice-selection random --slice-seed 20261112 --slice-reads 1000000 --hash-size 2G`), exit 0:

```
PARITY OK distinct=73578421 total=129801125
parity reference captured: kind=random-record reads=1000000 distinct=73578421 total=129801125
```

**Random gate-proof** (same recipe, `--parity-reference`), exit 0:

```
PARITY OK distinct=73578421 total=129801125
PARITY REFERENCE OK distinct=73578421 total=129801125 (bound to source dae91042e42c… kind=random-record)
```

Random selection identity: seed 20261112, selection_manifest_sha256 `b6dd426f1ff69a07a3a84f73c4f3789048a4e446a3278c2f5b2ab8190d9b14cb`, output_sha256 `712cdf86007825bc3fc138ffaaa030a794f797be28619cd10d14235544ae82b7`; manifest indices span 24 … 34,541,287 (uniform over the full 2.78 GB source, not a head prefix). The 4M constants never appear in the random record.

**RED scaling capture** (`thread_scaling.py --mode slice --slice-reads 4000000 --reps 2`), freshness-bound, exit 1:

```
rk21-t1: median wall 72.270s unique=229694874 total=519271168
rk21-t4: median wall 70.045s unique=229694874 total=519271168
rk21-t16: median wall 68.795s unique=229694874 total=519271168
SCALING VERDICT result=RED speedup_t4=1.031765293739739 speedup_t16=1.0505123918889456 min_speedup=1.3
```

`--current` re-verdict reproduced the identical RED line (exit 1). Structured check: `RED baseline verdict OK` (schema + provenance valid; verdict RED; speedups in (0, 1.3); identical nonzero cross-arm counts; positive medians; 2-round schedule; both logs' speedups exactly equal the doc's stored floats via repr round-trip). Neither log contains a Traceback. Per-rep `cache_state=unavailable` (warm cache, no sudo — honest per README). Provenance: binary `8f64d442…`, git HEAD `227cffd571aa` (dirty True at capture — artifacts not yet committed), build profile release, rustc 1.101.0-nightly.

## Task Commits

Each task was committed atomically (Task 1 TDD = RED + GREEN):

1. **Task 1 RED: failing parity-reference + random-provisioning tests** — `9ca448f` (test)
2. **Task 1 GREEN: random-selection + fingerprint-bound parity gate** — `227cffd` (feat)
3. **Task 2: real-data parity gates + RED scaling baseline** — `319b807` (feat)

REFACTOR: not needed — the GREEN implementation remained clear and all tests passed.

## TDD Gate Compliance

- **RED: PASS** — `9ca448f`. Machine verdict `RED_EVIDENCE_OK` (`gsd_run check tdd-red-evidence`, unittest format): 68 tests discovered, 37 FAIL headers, 0 ERROR headers; target `TestParityReferenceGate.test_exact_recipe_matches` executed and failed its planned assertion (`bench.load_parity_reference not implemented yet (05-04)`). Semantic assessment: genuine planned-behavior failures (the new helpers do not exist at HEAD), not a load/collection fault. Evidence retained at `scripts/bench/scratch/05-04-task1-red-evidence.json` (gitignored).
- **GREEN: PASS** — `227cffd` descends from `9ca448f`; 82 degradation+schema tests pass, full harness 211 OK.
- **REFACTOR:** not needed.
- Violations: none.

## Files Created/Modified

- `scripts/bench/bench.py` (+490/-9) — random provisioning, parity-reference gate helpers, pinned constant, hash-size threading, parity-record emission, new CLI flags; `SCHEMA_VERSION`/`validate_schema` unchanged
- `scripts/bench/tests/test_degradation.py` (+487) — 38 fixture-based gate/provisioning tests; existing resolver + first-N + random-slice classes unchanged
- `scripts/bench/baselines/slice_parity.crr1936095.json` (new) — head-4M pinned + 1M random reference records (the random record's 1M-index selection manifest is the bulk of the file)
- `.planning/phases/05-measurement-regression-harness/slice_parity_evidence.json` (new) — both provenance-bearing parity passes
- `.planning/phases/05-measurement-regression-harness/thread_scaling_baseline.json` (new) — real-slice t1/t4/t16 RED baseline
- Generated runtime scratch (slice-0.fq + three 4.59 GB scaling `.rkdb`) removed from the phase dir after verification; smoke/capture logs live under gitignored `scripts/bench/scratch/`

## Decisions Made

- `slice_kind_for` returns `None` for head selections other than the pinned 4M recipe; the gate/capture flow rejects them loudly rather than mislabeling a head prefix as `random-record` (see Deviations).
- Capture rejects duplicate full-key recipes (exit 2) to protect the gate from ambiguity; re-capture requires explicit deletion.
- The reference flags require `--parity-only`, are mutually exclusive, and are slice-mode-only — explicit CLI contract.
- Every reference record is provenance-validated at load (T-05-02); random records must carry a `selection_manifest` consistent with their identity fields.
- Execution context: `branching_strategy: none` — per `execute-phase/steps/protected-branch.md` the workflow warns and continues on `dev`; sequential executor on the main working tree, normal git hooks, no `--no-verify` (05-01/05-03 precedent).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Correctness] Head non-4M selections have no reference recipe (slice_kind None)**
- **Found during:** Task 1 (gate design)
- **Issue:** The plan's literal "slice_kind … 'random-record' otherwise" would label a head-1M prefix as a random sample, then reject it for missing selection identity — a confusing path that could mislabel a head prefix.
- **Fix:** `slice_kind_for` returns `None` for head selections other than head+4000000; the gate/capture flow rejects them with an explicit "no parity reference recipe … use --slice-selection random" message (exit 2). The two supported recipes (head-4M pinned, random-record) behave exactly as specified.
- **Files modified:** `scripts/bench/bench.py`
- **Verification:** head backward-compat tests green; random binding tests green; real head-4M + random gates passed
- **Committed in:** `227cffd`

**2. [Rule 2 - Missing Critical] Duplicate-capture rejection + reference-flag CLI contract**
- **Found during:** Task 1 (capture/CLI design)
- **Issue:** The plan specifies duplicate full-key records are invalid at LOAD but is silent on duplicate CAPTURE; appending a duplicate would brick the gate. The reference flags also needed an explicit mode/parity-only contract to avoid silent ignores.
- **Fix:** `capture_parity_reference` exits 2 on an already-referenced exact recipe; `--parity-reference`/`--capture-parity-reference` require `--parity-only`, are mutually exclusive, and are slice-mode-only (loud exit 2 otherwise).
- **Files modified:** `scripts/bench/bench.py`
- **Verification:** `TestParityCapture.test_capture_duplicate_full_key_exits_2` + head/random real captures (distinct recipes coexist; gate-proof re-runs exit 0)
- **Committed in:** `227cffd`

---

**Total deviations:** 2 auto-fixed (2 Rule 2).
**Impact on plan:** Both strengthen gate correctness (no mislabeled recipes, no gate-bricking duplicates). No scope creep; no hot-path, lockfile, or fixture changes (`git diff --stat src/ pyo3/src/` empty across the plan range). Threat mitigations satisfied: T-05-07 (new invocations list-form; the existing screened jellyfish pipe reused), T-05-08 (slices under gitignored scratch / removed runtime artifacts; reservoir O(requested records)), T-05-SC (no package installs; jellyfish 2.3.1 pre-existing; locked cargo build).

## Issues Encountered

- The ~12-minute scaling capture (9 runs × ~70 s + cooldowns) exceeds the foreground command cap, so it was run as a background job (single authoritative execution, as the plan's verify block requires). Several redundant sentinel-wait jobs were spawned while awaiting it; they were harmless and all completed. The capture itself ran exactly once, freshness-bound.
- `evidence.json`'s `slice.gz_sha256` (`0c7626d8…`, 320 MB) describes the re-gzipped 4M head slice, not the source part; the reference is correctly bound to the LIVE source-part fingerprint `dae91042…` (2.78 GB), confirmed identical across capture and both gate-proof re-runs. The pinned counts matching exactly proves the same measured data.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Phase 6 (PAR-01) green-target ready:** `thread_scaling_baseline.json` is the standing RED number (speedup_t4 1.0318 / speedup_t16 1.0505); fixing `--threads` must push both speedups >= 1.3. The 05-03 ignored pool-size gate goes green alongside it.
- **Downstream gates ready:** 05-05/05-06 import only bench.py helpers stable after Wave 1 (measure, reduce_arm, cache_state_from, fingerprint, binary_provenance, …) — this plan's additive edits change none of their signatures (coupling_justified honored; full harness 211 OK). Phase 10 can re-run one command per gate (`--parity-reference`, `thread_scaling.py --current`) against the committed numbers.
- **Representativeness validated:** the random subslice gate proves the harness can derive a fresh fingerprint-bound reference for any seeded sample; the pinned head-4M reference remains the historical anchor.
- PROF-01 is shared with sibling plans (05-02/05-07); the shared-ID gate defers `Complete` until every declaring plan finishes.

## Self-Check: PASSED

- FOUND: scripts/bench/bench.py, scripts/bench/tests/test_degradation.py, scripts/bench/baselines/slice_parity.crr1936095.json, .planning/phases/05-measurement-regression-harness/slice_parity_evidence.json, .planning/phases/05-measurement-regression-harness/thread_scaling_baseline.json
- FOUND commits: 9ca448f, 227cffd, 319b807 (all ancestors of HEAD; measured ledger count 3 == commits recorded)
- All Task 1 + Task 2 acceptance criteria re-run and passed; full harness suite 211 tests OK; scope guard verified (zero hot-path changes)
- Stub scan: no TODO/FIXME/placeholder stubs. The RED scaling verdict is the plan-mandated expected-RED observation (a standing gate that actively runs, not a skipped test), so no WINDOWS defect entry is warranted.

### Actuals note

`actuals.tokens` (10,354,895) is the honest chars/4 measurement over the FULL realized diff (41,419,580 chars), dominated by the two machine-generated 1,000,000-index selection manifests (data artifacts, ~2M lines). The authored code+tests portion (`bench.py` + `test_degradation.py`) is 52,394 chars ≈ **13,098 tokens** — the meaningful work-cost figure for calibration against the 30,000-token estimate. Both are reported unrounded; the data volume is not flavored to look closer to the estimate.

---
*Phase: 05-measurement-regression-harness*
*Completed: 2026-11-12*