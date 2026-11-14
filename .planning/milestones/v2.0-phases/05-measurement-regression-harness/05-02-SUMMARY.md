---
phase: 05-measurement-regression-harness
plan: 02
subsystem: infra
tags: [msrv, rust-1.80, clippy, ci, reservoir-sampling, fastq, stdlib-python]

requires:
  - phase: 05-measurement-regression-harness
    plan: 01
    provides: "Shared bench.fingerprint/validate_path helpers and fail-loud harness conventions"
provides:
  - "Local Rust 1.80.0 toolchain with clippy and two MSRV-pinned CI clippy jobs using isolated msrv180 cache namespaces"
  - "Seeded single-pass Algorithm R random-record FASTQ slicer with deterministic FASTQ bytes and selection manifest"
  - "Thirty-test degradation suite covering determinism, source-order whole records, non-head selection, and exit-2 failures"
  - "Reproduced locked-dependency MSRV blockers for root and PyO3 crates, recorded as open WINDOWS entries 19 and 20"
affects: [05-03, 05-04, 05-07, 06-parallelism, 07-engine, 09-python-parity]

actuals:
  tokens: 4599
  tasks: 2
  commits: 3
plan_head_before: 1aa9470d36f1ec76cfa338908a18171b2e168526
plan_head_after: 176debcaa24e404964113818c2fa426b2900db65

tech-stack:
  added:
    - "Rust 1.80.0 toolchain + clippy component installed through rustup (local toolchain, no repo dependency changes)"
  patterns:
    - "MSRV-only clippy toolchains and writable/restore cache namespaces separated from stable test jobs"
    - "Single-pass reservoir sampling with O(requested-records) memory and ascending-source-index output"
    - "Deterministic manifest keyed by source fingerprint + seed + sorted selected indices + output sha256"
    - "TDD RED evidence machine-validated before GREEN; historical first-N slicer left byte-identical"

key-files:
  created:
    - scripts/bench/random_slice.py
  modified:
    - .github/workflows/ci.yml
    - scripts/bench/tests/test_degradation.py
    - .planning/WINDOWS.md

key-decisions:
  - "Do not bump dependencies, edit either Cargo.lock, add --ignore-rust-version, or soften -D warnings: the locked dependency MSRV failures are surfaced as blocking findings exactly as the plan requires"
  - "The random slicer buffers only the reservoir and writes output only after full-stream validation, so malformed/oversized inputs cannot silently produce a partial slice"
  - "Manifest JSON excludes output/manifest paths and timestamps, making identical source + seed + reads byte-deterministic across invocation names"
  - "No refactor commit was needed after GREEN; the minimal implementation remained clear and all tests passed"

patterns-established:
  - "Random-record selection uses random.Random(seed) before Algorithm R selection, then sorts selected records by source index for deterministic output independent of reservoir eviction order"
  - "CLI invalid input exits 2 while the importable reservoir_slice function raises ValueError/RuntimeError/OSError for Plan 04 integration"
  - "CI cache comments and restore prefixes explicitly distinguish msrv180 artifacts from stable artifacts"

requirements-completed: [PROF-01]

coverage:
  - id: D1
    description: "Rust 1.80.0 installed and both CI clippy jobs pinned with isolated msrv180 caches; local clippy execution exposes locked dependency MSRV violations rather than being softened"
    requirement: "PROF-01"
    verification:
      - kind: other
        ref: "cargo +1.80.0 --version && cargo +1.80.0 clippy --version"
        status: pass
      - kind: other
        ref: "ci.yml exactly two toolchain: 1.80.0 pins, two msrv180 cache namespaces, stable test jobs, YAML parse"
        status: pass
      - kind: other
        ref: "cargo +1.80.0 clippy --locked --all-targets -- -D warnings (root: exit 101; half/indexmap/proptest MSRV)"
        status: fail
      - kind: other
        ref: "cargo +1.80.0 clippy --locked --all-targets --manifest-path pyo3/Cargo.toml -- -D warnings (exit 101; indexmap MSRV)"
        status: fail
    human_judgment: true
    rationale: "The CI structure is verified, but clean MSRV clippy is blocked by locked dependencies. Resolving their versions is explicitly prohibited by this plan and needs a separately planned dependency decision."
  - id: D2
    description: "Seeded uniform random-record slicer emits complete source-ordered records and deterministic selection manifests with loud invalid-input handling"
    requirement: "PROF-01"
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_degradation.py#TestRandomSlice (11 tests); full module 30 tests OK"
        status: pass
      - kind: unit
        ref: "python3 -m unittest discover -s scripts/bench/tests -v (169 tests OK)"
        status: pass
      - kind: other
        ref: "from scripts.bench.random_slice import reservoir_slice; callable import smoke"
        status: pass
    human_judgment: false
  - id: D3
    description: "Historical first-N make_slice.sh behavior and all scope-guarded counting hot-path files remain unchanged"
    requirement: "PROF-01"
    verification:
      - kind: unit
        ref: "TestMakeSliceDeterminism (4 existing tests) remains green; git diff --stat scripts/bench/make_slice.sh is empty"
        status: pass
      - kind: other
        ref: "git diff --name-only plan-base..HEAD over count.rs/table.rs/pyo3 counter.rs/format.rs returns zero files"
        status: pass
    human_judgment: false

duration: 18min
completed: 2026-11-12
status: complete
---

# Phase 5 Plan 02: MSRV CI Pins and Random-Record Slicer Summary

**Rust 1.80 CI clippy pins plus a deterministic Algorithm R FASTQ slicer with manifest-backed selection; both locked-crate MSRV dependency failures are explicitly preserved as blocking findings.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-11-12T02:15:05Z
- **Completed:** 2026-11-12T02:33:08Z
- **Tasks:** 2 executed
- **Files modified:** 3 production/config/test files (plus `.planning/WINDOWS.md` defect ledger)

## Accomplishments

- Installed official `1.80.0-aarch64-apple-darwin` with clippy via `rustup toolchain install 1.80.0 --component clippy`; `cargo 1.80.0 (376290515 2024-07-16)` and `clippy 0.1.80` are available locally without changing the default nightly toolchain or adding `rust-toolchain.toml`.
- Pinned only `clippy-root` and `pyo3-build` to `dtolnay/rust-toolchain@master` + `toolchain: 1.80.0`. Both clippy commands remain verbatim `cargo clippy --locked --all-targets -- -D warnings`; PyO3 working directories are unchanged. `test-root` and `pyo3-pytest` remain on stable.
- Added `cargo-clippy-msrv180` and `cargo-pyo3-msrv180` key/restore namespaces so stable and 1.80 artifacts cannot share writable or restore slots. Workflow YAML parses and contains exactly two 1.80.0 pins.
- Added `reservoir_slice(gz_path, n_reads, seed, out_path, manifest_path)` and CLI `--input --reads --seed --out --manifest`. It streams list-form `gunzip -c`, uses seeded single-pass Algorithm R with O(N) memory, rejects partial four-line records, emits selected records in ascending source-index order, and writes deterministic JSON containing source fingerprint, seed, counts, sorted indices, output sha256, and `record_lines: 4`.
- Extended the degradation suite with 11 random-slice tests. Same-seed FASTQ/manifest sha256 equality, different-seed divergence, exact whole-record reconstruction, sorted/in-range indices, non-head selection, oversized requests, empty/malformed/missing inputs, and zero/nonnumeric counts are covered. All 30 module tests and all 169 harness tests pass.
- Preserved `make_slice.sh`, the historical 4M-read first-N reference path, and every scope-guarded hot-path file. The pinned parity constants remain untouched for Plan 04: Distinct `229,694,874`, Total `519,271,168`.

## Task Commits

1. **Task 1: CI MSRV toolchain pins and cache isolation** — `ea13c16` (chore). Local 1.80 installation and both clippy commands were executed; their locked-dependency failures are documented below, not hidden.
2. **Task 2 RED: random-record behavior and failure tests** — `cbdb15e` (test). RED classifier returned `RED_EVIDENCE_OK`: 30 tests ran, 23 passed, 7 failed; target `TestRandomSlice.test_same_seed_is_byte_deterministic` failed its planned successful-invocation assertion (`2 != 0`) because the implementation did not yet exist. This was an executed unittest assertion, not a collection/load failure.
3. **Task 2 GREEN: seeded reservoir implementation** — `176debc` (feat). The full degradation module passed 30/30; no refactor commit was necessary.

RED evidence is retained at `scripts/bench/scratch/05-02-task2-red-evidence.json` (gitignored runtime evidence). Git ancestry confirms RED `cbdb15e` is an ancestor of GREEN `176debc`.

## Verification Evidence

### Random slicer — PASS

`NO_COLOR=1 python3 -m unittest scripts.bench.tests.test_degradation -v`:

```text
Ran 30 tests in 0.578s
OK
```

`NO_COLOR=1 python3 -m unittest discover -s scripts/bench/tests -v`:

```text
Ran 169 tests in 3.138s
OK
```

Acceptance checks also passed: `random_slice.py` exists; six `reservoir` markers; importable `reservoir_slice`; empty `git diff --stat scripts/bench/make_slice.sh`; zero changed hot-path files.

### CI structure — PASS

```text
PASS toolchain pins=2
PASS YAML parse
PASS clippy cache markers=2
PASS pyo3 cache markers=2
PASS no root rust-toolchain.toml
PASS test-root remains on stable
PASS pyo3-pytest remains on stable
PASS both clippy commands unchanged
```

### Local MSRV clippy — BLOCKED, not passed

Final verification reproduced both failures with the exact planned commands. Neither dependency versions nor the gate were changed.

Root command exited **101**:

```text
error: rustc 1.80.0 is not supported by the following packages:
  half@2.7.1 requires rustc 1.81
  indexmap@2.13.0 requires rustc 1.82
  proptest@1.9.0 requires rustc 1.82
```

PyO3 command exited **101**:

```text
error: rustc 1.80.0 is not supported by the following package:
  indexmap@2.13.0 requires rustc 1.82
```

Consequently, the plan's two clean-clippy acceptance criteria and the downstream claim that later phases can run clean MSRV-aware clippy are **not met**. CI will enforce the requested 1.80.0 gate and expose these same violations until a separately planned lockfile/MSRV remediation lands. No `--ignore-rust-version`, dependency bump, lockfile edit, or warning suppression was used.

## Files Created/Modified

- `.github/workflows/ci.yml` — two 1.80.0 clippy pins, isolated cache keys/restore prefixes, updated cache comments; stable jobs retained.
- `scripts/bench/random_slice.py` — new stdlib-only streaming reservoir slicer and importable API.
- `scripts/bench/tests/test_degradation.py` — new `TestRandomSlice` class; existing resolver and first-N test classes unchanged.
- `.planning/WINDOWS.md` — open `unmet-truth` entries 19 (root lockfile) and 20 (PyO3 lockfile) make the MSRV defects visible to ship gates.

## Decisions Made

- Surface the locked dependency MSRV conflict as a blocker instead of changing dependencies or weakening the check, following the plan's explicit failure-handling instruction.
- Buffer only selected reservoir entries and delay output/manifest writes until the entire source has been validated, preventing silent partial artifacts on malformed or oversized input.
- Exclude timestamps and destination paths from manifest content so same-source/same-seed invocations are byte-identical even when output filenames differ.
- Keep the historical first-N tool separate and unchanged; the new tool owns representative random-record selection for Plan 04.

## Deviations from Plan

None — the implementation and failure handling followed the plan. The dependency failure was an explicitly anticipated blocking-finding path, not permission to alter lockfiles or the gate. Threat mitigations T-05-03 (path screening, list-form argv, malformed-input rejection), T-05-04 (bounded reservoir), and T-05-SC (official rustup channel only) are implemented.

## Issues Encountered

- **Blocking:** root and PyO3 locked dependencies declare Rust requirements above 1.80, detailed under Verification Evidence. The requested CI pins are in place, but clean local/CI MSRV clippy requires follow-up dependency remediation outside this plan's permitted edits.
- The initial ad-hoc per-job stable-toolchain assertion used an overly broad job-boundary regex and failed despite the workflow being correct; a corrected job-boundary check passed. No source change was required.

## TDD Gate Compliance

- RED: PASS — `cbdb15e`, machine verdict `RED_EVIDENCE_OK`, semantic inspection confirmed the target executed and failed the planned assertion.
- GREEN: PASS — `176debc` descends from RED and all 30 degradation tests pass.
- REFACTOR: not needed; no cleanup changes followed GREEN.
- Violations: none.

## Authentication Gates

None.

## User Setup Required

None — rustup installation was completed automatically through the official existing rustup binary.

## Next Phase Readiness

- Plan 04 can import `reservoir_slice` to provision representative random subslices and persist their selection manifests. It must derive fresh Jellyfish references for each random input fingerprint, never reuse the historical 4M first-N parity constants.
- **MSRV handoff is blocked:** before claiming clean 1.80 clippy, a follow-up plan must resolve `half`, `indexmap`, and `proptest` lockfile versions (or explicitly revise MSRV policy through a surfaced decision). The current plan prohibits that remediation.
- The open WINDOWS entries and STATE blocker preserve this finding for later phases and ship gates.

## Self-Check: PASSED (artifacts, commits, and executable slicer/CI checks)

- FOUND: `.github/workflows/ci.yml`, `scripts/bench/random_slice.py`, `scripts/bench/tests/test_degradation.py`.
- FOUND commits: `ea13c16`, `cbdb15e`, `176debc`; measured production commit count 3 equals the ledger range.
- All Task 2 acceptance criteria and all structural Task 1 CI criteria passed; 169-test harness suite green.
- The two Task 1 clean-clippy criteria were rerun and remain **BLOCKED**, explicitly reported above rather than omitted or misreported as passing.
- Stub scan found no TODO/FIXME/placeholder markers. No Known Stubs.

---
*Phase: 05-measurement-regression-harness*
*Completed: 2026-11-12*
