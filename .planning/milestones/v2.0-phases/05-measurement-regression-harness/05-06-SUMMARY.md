---
phase: 05-measurement-regression-harness
plan: 06
subsystem: infra
tags: [prof-04, prof-05, python-benchmark, pyo3, fresh-worker, n-free-control, d2, n-read-differential, provenance, stdlib-python, rkdb]

requires:
  - phase: 05-measurement-regression-harness
    plan: 01
    provides: "bench.measure (OS rusage), reduce_arm/cache_state_from, fingerprint, binary_provenance/validate_provenance, validate_schema"
  - phase: 05-measurement-regression-harness
    plan: 02
    provides: "random_slice.reservoir_slice (seeded Algorithm R FASTQ slicer + selection manifest)"
  - phase: 05-measurement-regression-harness
    plan: 04
    provides: "Real-input provenance (CRR1936095 part_001, sha256 dae91042…), CLI parity-reference discipline, release binary 8f64d442…"
provides:
  - "scripts/bench/python_bench.py — controller + --worker; every rep is a FRESH worker under /usr/bin/time (no in-process clock); per-rep exact counts with strict cross-rep identity; module provenance = actual .so sha256 (resolves maturin 1.11 editable-shim inner native module); exit 0 valid / 2 invalid"
  - "scripts/bench/baselines/python_bench_baseline.darwin.json — committed dev-host baseline (baseline_scope dev-host-local-comparison, comparison_basis n-free-control): parity-validated N-free control (CLI == Python 73,476,107/129,579,577; 998,117 kept / 1,883 dropped; exact counts identical across 3 reps) as the D2-invariant primary comparison basis, plus timing-only real-N arm (1M random subslice, seed 20261112, median 30.42 s)"
  - "scripts/bench/n_read_differential.py — 9-case CLI-vs-Python differential with control gate; --expect-divergence (default) / --expect-unified (Phase 9); exit 0/1 measured verdict, 2 invalid"
  - ".planning/phases/05-measurement-regression-harness/n_read_differential.json — D2 evidence: control exactly equal; 33 Python-only chimeric k-mers in n_at_window_end/n_at_window_start/multiple_n/lowercase_n; 0 CLI-only; both surfaces' provenance"
  - "Rebuilt .venv313 pyrustkmer extension (current source, sha256 c7701806…), fingerprinted in every artifact"
affects: [05-07, 09-python-parity, 10-verdict]

actuals:
  tokens: 4693463
  tasks: 2
  commits: 4
  plan_head_before: 463f36337819efbd9d4d92a4f089530af10de1c9
  plan_head_after: 6c43145963f238cafccadef281b11a69ddbde235

tech-stack:
  added: []
  patterns:
    - "Fresh-worker OS-rusage protocol for a Python-surface pipeline: every rep is a new interpreter process measured by bench.measure; the worker writes exact counts + native module path/mtime to a stats file the controller validates before accepting the rep"
    - "Parity-validated N-free control as a D2-invariant comparison basis: deterministic drop-records-with-N filter of the random subslice, live CLI-vs-Python parity on the same bytes BEFORE timing, exact counts pinned across every rep — identical semantics before and after Phase 9's skip-N unification"
    - "Real-N timing separately labeled evidence_class timing-only-real-N-pre-D2 with a semantics note: a pre-D2 record, never a post-D2 parity gate"
    - "Module provenance resolves the actual native .so bytes: maturin 1.11's editable develop wraps the .so in a generated shim package, so a .py __file__ is resolved through the native submodule; shim-with-no-native and out-of-site-packages modules exit 2"
    - "Record-only differential: the D2 divergence is quantified with a control gate; --expect-unified is the Phase 9 re-run contract, never a silent semantics change"

key-files:
  created:
    - scripts/bench/python_bench.py
    - scripts/bench/tests/test_python_bench.py
    - scripts/bench/baselines/python_bench_baseline.darwin.json
    - scripts/bench/n_read_differential.py
    - scripts/bench/tests/test_n_read_differential.py
    - .planning/phases/05-measurement-regression-harness/n_read_differential.json
  modified: []

key-decisions:
  - "N-free control is the committed primary comparison basis (comparison_basis n-free-control): Phase 9's D2 change alters Python counts only on N-containing reads, so a real-N-only baseline could never prove a like-for-like win; the control's exact counts are a parity invariant Phase 9 must preserve"
  - "Parity BEFORE timing, enforced live: the control's discarded warmup supplies the Python counts, the CLI counts the SAME bytes (--threads 1, same k/canonical), and any mismatch exits 2 before a single measured rep"
  - "Every rep's exact {total_kmers, unique_kmers} is persisted and must be identical across reps; disagreement is a nondeterministic pipeline (exit 2), never averaged away"
  - "The stale mixed-layout pyrustkmer install was uninstalled before rebuilding (removal only — no new packages, T-05-SC); after maturin develop the worker fingerprints the inner native .so (sha256 c7701806…) because maturin 1.11's editable shim makes pyrustkmer.__file__ a 123-byte __init__.py"
  - "--emit-baseline is slice-mode only and its filename must match the platform flavor (python_bench_baseline.darwin.json on this host); a synthetic or mislabeled baseline exits 2"
  - "The differential records D2 evidence only: CLI skip-N vs Python strip-and-join remain untouched; --expect-unified is reserved for Phase 9"
  - "Execution context: branching_strategy none — per execute-phase/steps/protected-branch.md the workflow warns and continues on the current branch (dev); sequential executor on the main working tree, normal git hooks, no --no-verify (05-01..05 precedent)"

patterns-established:
  - "A Python-surface benchmark is measured the same way as the CLI: fresh process per rep, OS rusage, warmup discarded, honest cache_state, medians and CV — never an in-process clock"
  - "Comparison bases for a semantics-changing phase are chosen to be invariant across the change (N-free control), with the changing arm recorded under an explicit evidence_class label"
  - "Worker stats are a validated artifact: nonzero exact counts, native extension under the interpreter's site-packages, identical across reps — a stale/shadowed module invalidates the run instead of producing a plausible number"

requirements-completed: [PROF-04, PROF-05]

coverage:
  - id: D1
    description: "Fresh-worker Python counting benchmark + committed dev-host darwin baseline whose primary comparison basis is a parity-validated N-free control; the real-N arm is timing-only pre-D2 evidence"
    requirement: "PROF-04"
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_python_bench.py (39 tests; 1 env-gated integration test passes with RUSTKMER_PYBENCH_VENV=.venv313)"
        status: pass
      - kind: integration
        ref: "python3 scripts/bench/python_bench.py --python .venv313/bin/python --mode slice --input CRR1936095_r1.part_001.fq.gz --slice-reads 1000000 --slice-seed 20261112 --reps 3 --emit-baseline scripts/bench/baselines/python_bench_baseline.darwin.json (exit 0; control parity OK distinct=73476107 total=129579577)"
        status: pass
      - kind: integration
        ref: "verify chain: validate_schema + validate_provenance + dev-host scope + n-free-control basis + module sha256 + cross-rep exact counts + timing-only real-N label (python baseline OK)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Nine-case CLI-vs-Python N-read differential executed on both surfaces and recorded as D2 evidence: control exactly equal, 33 Python-only chimeric k-mers quantified with examples, both surfaces' provenance"
    requirement: "PROF-05"
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_n_read_differential.py (22 tests; RED_EVIDENCE_OK at 46815d4)"
        status: pass
      - kind: integration
        ref: ".venv313/bin/python scripts/bench/n_read_differential.py --rustkmer target/release/rustkmer --out .planning/phases/05-measurement-regression-harness/n_read_differential.json (exit 0; N-READ DIFFERENTIAL result=PASS expect=divergence cases=9 divergent=4)"
        status: pass
      - kind: integration
        ref: "verify chain: control python_only/cli_only/count_deltas all empty, at least one N-case python_only, exactly 9 cases (N-read differential OK)"
        status: pass
    human_judgment: false

duration: 21min
completed: 2026-11-12
status: complete
---

# Phase 5 Plan 06: Python Counting Baseline and N-Read Differential Summary

**Fresh-worker Python counting benchmark with a parity-validated N-free control baseline (CLI == Python at 73,476,107 distinct / 129,579,577 total; control median 32.14 s over 3 reps) plus a 9-case CLI-vs-Python N-read differential recording 33 Python-only chimeric k-mers across 4 N cases — the D2 evidence Phase 9 resolves, with the measured win basis made invariant to the D2 semantics change.**

## Performance

- **Duration:** 21 min
- **Started:** 2026-11-12T09:51:59Z
- **Completed:** 2026-11-12T10:13:53Z
- **Tasks:** 2
- **Files modified:** 6 created (0 modified; `git diff --stat src/ pyo3/src/` empty)

## Accomplishments

- **Extension rebuilt from current source** (the installed `.so` was prebuilt): `env -u CONDA_PREFIX VIRTUAL_ENV=$PWD/.venv313 PATH=$PWD/.venv313/bin:$PATH .venv313/bin/maturin develop --release -m pyo3/Cargo.toml` → fresh release build, installed module under `.venv313`, native `.so` sha256 `c7701806…`. The stale mixed-layout install was uninstalled first (removal only; no new packages).
- **`python_bench.py`** measures the sequential PyO3 file-counting pipeline (`PyCounter(k, canonical=True, threads=1).add_from_fastq`) with a FRESH interpreter per rep under `/usr/bin/time` — OS wall/RSS, one discarded warmup per arm, honest per-rep `cache_state`, medians/CV via `reduce_arm`. Every rep's stats file is validated (nonzero exact counts, native module under the interpreter's site-packages) and its exact counts persisted; any cross-rep disagreement, zero count, stale/shadowed module, or malformed stats exits 2. Zero `time.time()` occurrences.
- **Committed dev-host baseline** (`baseline_scope: dev-host-local-comparison`, `comparison_basis: n-free-control`): the 1M random subslice (seed 20261112 — the same recipe as Plan 04's parity record) is deterministically filtered into an N-free control (998,117 kept / 1,883 dropped, whole 4-line records). The CLI and Python counts on the control's exact bytes were proven equal **before timing**, and all 3 control reps reproduced the parity counts exactly. The real-N arm is separately labeled `evidence_class: timing-only-real-N-pre-D2` with a semantics note (its counts are a pre-D2 strip-and-join record and will change when D2 lands).
- **`n_read_differential.py`** records the D2 divergence: 9 deterministic k=21 FASTQ cases counted on both surfaces from the same bytes (CLI via `PyDatabase(..., LoadMode.Preload).export_all_kmers()` — no second binary decoder; Python via `add_from_fastq` + `get_all_counts`). The no-N control is exactly equal; 4 N cases show Python-only chimeric k-mers (33 total), with example k-mers; `record_boundary` and terminal-N cases are equal, proving no cross-record joins. `--expect-unified` is reserved for Phase 9's re-run.
- **No semantics changed**: this plan records evidence only; bindings and core are untouched (verified by `git diff --stat src/ pyo3/src/`).

## Real Measured Evidence (actual recorded output)

**N-free control parity** (slice mode, 1M random subslice seed 20261112, k=21, canonical, threads=1):

```
control parity OK distinct=73476107 total=129579577 (kept=998117 dropped=1883)
```

**Baseline** (`scripts/bench/baselines/python_bench_baseline.darwin.json`): control reps 31.77 / 32.51 / 32.14 s → median **32.14 s**, peak RSS ~3.98 GB, CV 1.15%; real-N reps 31.27 / 30.42 / 29.18 s → median **30.42 s**, CV 3.47% (no warning); per-rep `cache_state=unavailable` (warm cache, no sudo). Module sha256 `c7701806…` (the rebuilt `.so`), python 3.13.11, maturin 1.11.5, git HEAD `463f363` (dirty while the capture's artifacts were still uncommitted). Control exact counts: unique 73,476,107 / total 129,579,577 (identical in every rep); real-N pre-D2 exact counts: unique 73,598,016 / total 129,822,128.

**N-read differential** (`n_read_differential.json`, verdict PASS expect=divergence cases=9 divergent=4):

| case | CLI distinct/total | Python distinct/total | Python-only chimeras |
|------|-------------------|----------------------|----------------------|
| control_no_n | 2/10 | 2/10 | 0 |
| n_at_first | 2/9 | 2/9 | 0 |
| n_at_window_end | 0/0 | 9/9 | 9 |
| n_at_window_start | 1/1 | 9/9 | 8 |
| n_at_last | 2/9 | 2/9 | 0 |
| multiple_n | 0/0 | 7/7 | 7 |
| lowercase_n | 0/0 | 9/9 | 9 |
| record_boundary | 2/8 | 2/8 | 0 |
| short_read (15 bp < k) | 0/0 | 0/0 | 0 |

Totals: 33 Python-only chimeric k-mers, 0 CLI-only, 0 shared-key count deltas. Provenance: CLI binary sha256 `8f64d442…` (the Plan 04 release binary), native module sha256 `c7701806…`, git `0ab8c83` clean, python 3.13.11. The real-N arm's Python counts exceeding Plan 04's CLI random-1M counts (73,598,016 vs 73,578,421 unique) are the same chimeric effect manifesting at scale.

## Task Commits

Each task was committed atomically (Task 2 TDD = RED + GREEN + evidence):

1. **Task 1: Python benchmark, fresh-worker protocol, N-free control baseline** — `e642601` (feat)
2. **Task 2 RED: failing map-diff/fixture/verdict tests** — `46815d4` (test)
3. **Task 2 GREEN: N-read differential implementation** — `0ab8c83` (feat)
4. **Task 2 evidence: real differential capture** — `6c43145` (feat)

REFACTOR: not needed — the GREEN implementation remained clear and all tests passed.

## TDD Gate Compliance

- **RED: PASS** — `46815d4`. Machine verdict `RED_EVIDENCE_OK` (`gsd_run check tdd-red-evidence`, unittest format): 22 tests discovered, 22 FAIL headers, 0 ERROR headers; target `TestMapDiff.test_equal_maps_produce_zero_diffs` executed and failed its planned assertion (`n_read_differential not implemented yet (05-06)` — guarded import, 05-05 precedent). Evidence re-derived after fixing a test-fixture bug (see Deviations) with the implementation set aside, so the committed RED test genuinely fails at its commit.
- **GREEN: PASS** — `0ab8c83` descends from `46815d4`; 22/22 tests pass.
- **REFACTOR:** not needed.
- Violations: none.

## Files Created/Modified

- `scripts/bench/python_bench.py` (new, 726 lines) — controller + `--worker`; fresh-process measurement, N-free filter, parity gate, baseline envelope, module provenance
- `scripts/bench/tests/test_python_bench.py` (new, 571 lines) — 39 stdlib tests (filter, stats, rep identity, parity, naming, baseline, controller exit-2 matrix) + env-gated integration test
- `scripts/bench/baselines/python_bench_baseline.darwin.json` (new, ~17 MB) — committed dev-host baseline; bulk is the 1M-index selection manifest (identity binding, 05-04 precedent)
- `scripts/bench/n_read_differential.py` (new, 321 lines) — 9-case differential, pure reduction/verdict, record-only
- `scripts/bench/tests/test_n_read_differential.py` (new, 267 lines) — 22 stdlib tests
- `.planning/phases/05-measurement-regression-harness/n_read_differential.json` (new) — D2 evidence with both surfaces' provenance
- Runtime scratch (slice FASTQs, control `.rkdb`, stats files, logs) under gitignored `scripts/bench/scratch/`; large artifacts removed after verification (only the run doc and logs remain)

## Decisions Made

- **N-free control is the committed comparison basis.** D2 changes Python's counts only on N-containing reads; the control contains none, so its exact counts and timing are like-for-like before and after Phase 9. A real-N-only baseline could never prove the win.
- **Parity before timing, live.** The control's warmup supplies the Python counts; the CLI counts the same bytes with the same k/canonical; a mismatch exits 2 before any measured rep.
- **Fresh-worker stats are a validated artifact.** Exact counts must be nonzero, identical across reps, and produced by a native module under the `--python` interpreter's site-packages; a shim-only or shadowed module invalidates the run.
- **`--emit-baseline` is slice-mode only** and must carry the platform's filename; synthetic/mislabeled baselines are invalid.
- **Record-only differential.** `--expect-unified` is Phase 9's contract; control equality is a hard gate in both modes; exit 1 is a measured verdict, exit 2 invalid.
- Execution context: `branching_strategy: none` — per `execute-phase/steps/protected-branch.md` the workflow warns and continues on the current branch (`dev`); sequential executor on the main working tree, normal git hooks, no `--no-verify` (05-01..05 precedent).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking, measurement fidelity] maturin 1.11 editable shim hides the measured `.so`**
- **Found during:** Task 1 (rebuild)
- **Issue:** The plan rebuilds with `maturin develop --release` and fingerprints `pyrustkmer.__file__`. maturin 1.11.5 installs an editable shim package (`pyrustkmer/__init__.py: from .pyrustkmer import *` + inner `pyrustkmer.cpython-313-darwin.so`), so `__file__` is a 123-byte `.py` — hashing it would violate the plan's own must_have ("its actual .so bytes are sha256-fingerprinted"). The pre-existing install was an older build of the same layout.
- **Fix:** Uninstalled the stale local package (removal only, no new packages), rebuilt from source, and had the worker resolve the native extension file through the shim (`_native_module_file`) before fingerprinting. Validation now also rejects non-native/shim-only and out-of-site-packages modules (exit 2).
- **Files modified:** `scripts/bench/python_bench.py`, `scripts/bench/tests/test_python_bench.py`
- **Verification:** module sha256 `c7701806…` equals `shasum` of the installed fresh `.so`; integration test asserts module path under the venv and sha match; shim-path unit test exits 2
- **Committed in:** `e642601`

**2. [Rule 1 - Bug] Example-cap test fixture had only 4 distinct keys**
- **Found during:** Task 2 GREEN
- **Issue:** `test_stable_ordering_and_example_cap` used `{c * 21: 1 for c in "TGCACTG"}` — only four distinct bases, so the dict had 4 keys while the assertion required 5. The fixture bug was masked in RED (all tests failed on the implementation guard).
- **Fix:** Built six distinct 21-mers explicitly; re-derived the RED evidence with the implementation temporarily set aside so the committed RED test genuinely fails at HEAD.
- **Files modified:** `scripts/bench/tests/test_n_read_differential.py`
- **Verification:** RED evidence re-classified `RED_EVIDENCE_OK` (22/22 planned failures); GREEN 22/22 pass
- **Committed in:** `46815d4` (test) / `0ab8c83` (implementation)

---

**Total deviations:** 2 auto-fixed (1 Rule 3, 1 Rule 1).
**Impact on plan:** Both strengthen measurement fidelity/provenance; no scope creep. `git diff --stat src/ pyo3/src/` is empty across the plan range — neither surface's semantics changed. Threat mitigations satisfied: T-05-11 (rebuild before capture, module path/mtime reported, site-packages + native-suffix + sha256 checks, exit 2), T-05-12 (`CONDA_PREFIX` unset for the rebuild via `env -u`; interpreter recorded), T-05-SC (no new packages — maturin already present, stale local build removed, CLI parity uses the locked release binary).

## Issues Encountered

- `RUSTKMER_REAL_INPUT` is not exported in the shell profile; the dataset exists at the documented path (2,785,381,389 bytes). The capture exported it inline before `test -f` — same fulfillment as 05-04/05-05.
- The ~10-minute baseline capture (reservoir pass over the 2.78 GB source + 9 fresh-worker runs + CLI parity + cooldowns) ran as a single background job with freshness binding (prior baseline/run doc deleted and absence asserted first); it completed exit 0 on the first attempt.
- The filtered control drops 1,883 of 1,000,000 records (0.19% N-containing), so the control is representative of the same selection — both sets are recorded with their own fingerprints.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required (the rebuild used the existing `.venv313` maturin; no package installs).

## Next Phase Readiness

- **Phase 9 (PY-02) win basis ready:** re-run the identical command from Plan 05-06 (`--slice-reads 1000000 --slice-seed 20261112 --reps 3`) and compare against the committed N-free control (exact counts 73,476,107/129,579,577 must be preserved; control median 32.14 s). The real-N arm is supplementary timing-only evidence, never a parity gate.
- **D2 proof ready:** re-run `n_read_differential.py --expect-unified`; all 9 cases must be equal, including the four currently divergent N cases.
- **05-07 / CI:** both unit suites run without PyO3/NumPy/pytest/dataset (302-test harness discover suite green); the real captures stay dev-host/real-data operations, not CI fabrication.
- **Requirement marking:** PROF-05 is declared only by this plan (marked complete). PROF-04 is shared with 05-07, so the shared-ID gate defers `Complete` until 05-07 finishes.

## Self-Check: PASSED

- FOUND: scripts/bench/python_bench.py, scripts/bench/tests/test_python_bench.py, scripts/bench/baselines/python_bench_baseline.darwin.json, scripts/bench/n_read_differential.py, scripts/bench/tests/test_n_read_differential.py, .planning/phases/05-measurement-regression-harness/n_read_differential.json
- FOUND commits: e642601, 46815d4, 0ab8c83, 6c43145 (all ancestors of HEAD; measured ledger count 4 == commits recorded)
- Task 1 + Task 2 verify chains re-run and passed; full harness suite 302 tests OK (1 env-gated skip, integration test passes when enabled)
- Stub scan: no TODO/FIXME/placeholder stubs. No Known Stubs; no WINDOWS entries warranted (no skipped tests, no unrun verifies — the real-N arm's label is a deliberate evidence class, not a defect)

---

*Phase: 05-measurement-regression-harness*
*Completed: 2026-11-12*
