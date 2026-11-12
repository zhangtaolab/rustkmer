---
phase: 05-measurement-regression-harness
verified: 2026-11-12T10:25:32Z
status: passed
score: 12/12 must-haves verified
covered_files: [".github/workflows/benchmark.yml", ".github/workflows/ci.yml", ".planning/phases/05-measurement-regression-harness/05-01-PLAN.md", ".planning/phases/05-measurement-regression-harness/05-01-SUMMARY.md", ".planning/phases/05-measurement-regression-harness/05-02-PLAN.md", ".planning/phases/05-measurement-regression-harness/05-02-SUMMARY.md", ".planning/phases/05-measurement-regression-harness/05-03-PLAN.md", ".planning/phases/05-measurement-regression-harness/05-03-SUMMARY.md", ".planning/phases/05-measurement-regression-harness/05-04-PLAN.md", ".planning/phases/05-measurement-regression-harness/05-04-SUMMARY.md", ".planning/phases/05-measurement-regression-harness/05-05-PLAN.md", ".planning/phases/05-measurement-regression-harness/05-05-SUMMARY.md", ".planning/phases/05-measurement-regression-harness/05-06-PLAN.md", ".planning/phases/05-measurement-regression-harness/05-06-SUMMARY.md", ".planning/phases/05-measurement-regression-harness/05-07-PLAN.md", ".planning/phases/05-measurement-regression-harness/05-07-SUMMARY.md", ".planning/phases/05-measurement-regression-harness/contention_evidence.json", ".planning/phases/05-measurement-regression-harness/golden_capture.json", ".planning/phases/05-measurement-regression-harness/n_read_differential.json", ".planning/phases/05-measurement-regression-harness/slice_parity_evidence.json", ".planning/phases/05-measurement-regression-harness/thread_reality_evidence.json", ".planning/phases/05-measurement-regression-harness/thread_scaling_baseline.json", ".planning/research/profiling/microbench_Cargo.lock", ".planning/research/profiling/microbench_Cargo.toml", ".planning/research/profiling/microbench_main.rs", ".planning/research/profiling/verify_threads.py", "Cargo.toml", "pyo3/Cargo.toml", "scripts/bench/README.md", "scripts/bench/baselines/python_bench_baseline.darwin.json", "scripts/bench/baselines/slice_parity.crr1936095.json", "scripts/bench/bench.py", "scripts/bench/capture_goldens.py", "scripts/bench/contention_bench.py", "scripts/bench/n_read_differential.py", "scripts/bench/python_bench.py", "scripts/bench/random_slice.py", "scripts/bench/tests/test_contention_bench.py", "scripts/bench/tests/test_degradation.py", "scripts/bench/tests/test_n_read_differential.py", "scripts/bench/tests/test_python_bench.py", "scripts/bench/tests/test_schema.py", "scripts/bench/tests/test_thread_scaling.py", "scripts/bench/tests/test_verify_threads.py", "scripts/bench/thread_scaling.py", "src/database/prefix_cache_merge.rs", "tests/thread_pool_size_tests.rs"]
covered_digest: "v4:sha256:098ad659aa44c64f61274a17d60701e5dad87ce4955ea7ceebfddf9a78183c7c"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 5: Measurement & Regression Harness Verification Report

**Phase Goal:** Every downstream performance claim is measured against standing, reproducible gates — parity checked before timing, provenance on every artifact — and the known measurement gaps (thread reality, contention attribution, Python baseline, N-read divergence) are closed with recorded evidence.
**Verified:** 2026-11-12T10:25:32Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

Verification was performed goal-backward against the actual codebase and committed artifacts — not SUMMARY.md prose. Commands were re-run where the claim is mechanically checkable: the 302-test harness suite, the thread-scaling verdict, the pinned-parity smoke, the golden-sha test, the ignored pool-size standing gate, and both MSRV clippy gates at 1.82.

### Observable Truths

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | Reproducible slice bench gates on pinned parity (Distinct 229,694,874 / Total 519,271,168 vs jellyfish) with provenance on every artifact and random-record (not head) subslices | ✓ VERIFIED | `scripts/bench/bench.py:653` `PARITY_PINNED_HEAD4M = {"distinct": 229694874, "total": 519271168}`; `scripts/bench/baselines/slice_parity.crr1936095.json` holds the pinned head-4M record + a 1M random record (seed 20261112, selection_manifest_sha256, output_sha256); `slice_parity_evidence.json` records both passes with binary sha256 `8f64d442…` + git commit + profile; live smoke `bench.py --mode synthetic --reads 20000 --parity-only` exited 0 with `PARITY OK distinct=2400000 total=2400000` and provenance |
| 2 | `--threads` correctness test asserts the ACTUAL rayon pool size and is observably RED on the current tree | ✓ VERIFIED | `tests/thread_pool_size_tests.rs:198` `#[ignore]` standing gate + `:134` active characterization; independently re-run: `cargo test --test thread_pool_size_tests -- --ignored` → `requested=1 observed=18`, FAILED, exit 101; default suite → `1 passed; 1 ignored`. Root cause confirmed in `src/cli/commands/count.rs:836-845` (`rayon::current_num_threads()` eagerly initializes the pool as a fallback argument before `build_global` returns Err, so the flag is a no-op) |
| 3 | Thread-scaling gate records t1/t4/t16 wall-clock and is RED while the flag is a no-op | ✓ VERIFIED | `scripts/bench/thread_scaling.py` counterbalanced rotation + `scaling_verdict`; committed `thread_scaling_baseline.json` verdict RED (speedup_t4 1.0318, speedup_t16 1.0505 < 1.3), medians 72.270/70.045/68.795 s, identical 229,694,874/519,271,168 counts, provenance; re-ran `--current` → exit 1 with the same `SCALING VERDICT result=RED` line |
| 4 | Multi-thread contention microbench produces a recorded global-atomics vs memory-bandwidth split as Phase 7 evidence | ✓ VERIFIED | `contention_evidence.json`: 4 variants (`shared-counter`, `shared-dashmap`, `atomic-only`, `thread-local`) × t1/t4/t16 × 3 counterbalanced rounds = 36 records, 36/36 `conservation_ok`; attribution-v1 persisted with formulas: global-atomics 120.21998 ns (115.16%), bandwidth -15.82389 ns (-15.16%, honest "inconclusive" note, not clamped), multiplier 1.87686; committed audited lock `microbench_Cargo.lock` sha256 `eabd946a…` matches the evidence and the file |
| 5 | Python-surface counting benchmark runs and a sequential-pipeline baseline is committed | ✓ VERIFIED | `scripts/bench/python_bench.py` uses a fresh `--worker` process per rep under `bench.measure` (no in-process clock); committed `scripts/bench/baselines/python_bench_baseline.darwin.json` (baseline_scope `dev-host-local-comparison`, comparison_basis `n-free-control`): control arm median 32.14 s over 3 reps, CLI==Python 73,476,107/129,579,577 (`parity_control.equal=true`), exact counts identical across reps; actual native `.so` sha256 `c7701806…` recorded |
| 6 | CLI-vs-Python N-read differential is executed and recorded, quantifying chimeric-k-mer divergence | ✓ VERIFIED | `.planning/phases/05-measurement-regression-harness/n_read_differential.json`: 9 cases, verdict PASS expect=divergence, control exactly equal, 4 divergent N cases, 33 Python-only chimeras, 0 CLI-only, 0 count deltas; both surfaces' provenance recorded (binary `8f64d442…`, module `c7701806…`) |
| 7 | The gates are standing and wired into CI without softening | ✓ VERIFIED | `.github/workflows/benchmark.yml` runs harness unittest suite (`:90`), Python benchmark (`:121`), thread-scaling measure→upload→`--current` verdict (`:136`,`:150`); `grep -E 'continue-on-error\|\|\| true'` → NONE; all three uploads carry `if: always()` + `if-no-files-found: warn`; intentional PROF-02 red documented at the step |
| 8 | Pre-refactor golden `.rkdb` capture exists, is non-regenerating, and fixtures are unchanged | ✓ VERIFIED | `golden_capture.json` manifest_sha256 `f010e42a…` equals `shasum -a 256 tests/fixtures/golden_manifest.sha256`; all 12 fixture hashes match; `git diff --stat c357915..HEAD -- tests/fixtures/` empty; `capture_goldens.py` only rehashes + runs the golden test (never the generator); `cargo test --test golden_sha256_tests` → 5 passed |
| 9 | MSRV is 1.82 with MSRV-aware clippy green on BOTH crates; no 1.80 guardrail residue | ✓ VERIFIED | `Cargo.toml:5`, `pyo3/Cargo.toml:5`, `microbench_Cargo.toml:8` all `rust-version = "1.82"`; `ci.yml` pins `toolchain: 1.82.0` in both clippy jobs with isolated `msrv182` caches; `PROJECT.md:92` guardrail says 1.82; independently re-ran `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` → exit 0 (root and pyo3); WINDOWS 19/20 `fixed` |
| 10 | No counting hot-path / `.rkdb` format / public API changes | ✓ VERIFIED | Phase-window diff over `src/`, `pyo3/src/`, `tests/fixtures/`, both Cargo.locks: only `src/database/prefix_cache_merge.rs` (approved MSRV clippy `needless_range_loop` fix, commit `23967d5`) and the two `rust-version` manifest lines; no `format.rs`, no `pyo3/src`, no lockfile changes; no plan declared `src/` files_modified |
| 11 | Schema-v1 committed baselines remain loadable | ✓ VERIFIED | `bench.validate_schema` accepts `bench_baseline.darwin.json`, `bench_baseline.linux.json`, `thread_scaling_baseline.json` (schema_version 1); `SCHEMA_VERSION` and `validate_schema` untouched |
| 12 | All phase requirements PROF-01..05 are covered | ✓ VERIFIED | Plans declare PROF-01 (01/02/04/07), PROF-02 (01/03/07), PROF-03 (05), PROF-04 (06/07), PROF-05 (06); artifacts/evidence verified per rows 1-6 |

**Score:** 12/12 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `scripts/bench/bench.py` | provenance builder/validator + parity-reference gate + random selection | ✓ VERIFIED | `binary_provenance` :309, `validate_provenance` :342, `PARITY_PINNED_HEAD4M` :653, `load/gate/capture_parity_reference` :883/929/992, `selection_identity_from` :954, `provision_random_slice` :579 |
| `scripts/bench/thread_scaling.py` | PROF-02 standing gate | ✓ VERIFIED | `rotation_schedule` :101, `scaling_verdict` :127, exit 0/1/2, structured verdict line |
| `scripts/bench/random_slice.py` | seeded reservoir slicer | ✓ VERIFIED | importable `reservoir_slice`, used by `bench.py:601`; 11+ tests |
| `scripts/bench/contention_bench.py` | contention controller + attribution | ✓ VERIFIED | 621-line controller, tested by 30 tests |
| `scripts/bench/python_bench.py` | fresh-worker Python bench | ✓ VERIFIED | `--worker`, `bench.measure` around a new process; no `time.time()` |
| `scripts/bench/n_read_differential.py` | 9-case D2 differential | ✓ VERIFIED | `PyDatabase(... LoadMode.Preload).export_all_kmers()`; `--expect-unified` reserved for Phase 9 |
| `tests/thread_pool_size_tests.rs` | pool-size observation pair | ✓ VERIFIED | characterization active, standing gate ignored + RED |
| `.planning/research/profiling/verify_threads.py` | hardened thread observer | ✓ VERIFIED | exit 0/1/2, `requested=/observed=`, `THREAD REALITY verdict=` |
| `.planning/research/profiling/microbench_main.rs` | 4 mechanism arms | ✓ VERIFIED | arms + conservation at :243-246, :569-571 |
| `.planning/research/profiling/microbench_Cargo.toml/.lock` | relocatable, audited | ✓ VERIFIED | one `@REPO_ROOT@`, zero `/Users/forrest`; lock sha matches evidence |
| `.github/workflows/benchmark.yml` | standing gates | ✓ VERIFIED | see truth 7 |
| `scripts/bench/baselines/slice_parity.crr1936095.json` | pinned + random parity records | ✓ VERIFIED | both records with provenance/identity |
| `scripts/bench/baselines/python_bench_baseline.darwin.json` | committed Python baseline | ✓ VERIFIED | dev-host scope + n-free control basis |
| Evidence JSONs (thread_reality, golden_capture, slice_parity, thread_scaling, contention, n_read) | recorded, provenance-bearing | ✓ VERIFIED | all present, tracked, schema/provenance valid |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `bench.py` | `random_slice.py` | `--slice-selection random` → `reservoir_slice` + manifest | ✓ WIRED | `bench.py:601,622` |
| `bench.py` parity gate | `slice_parity.crr1936095.json` | exact key + seed + manifest + output hash | ✓ WIRED | `load_parity_reference` :883; fixture tests pass |
| `thread_scaling.py` | `bench.py` | imports measure/reduce_arm/binary_provenance/validate_* | ✓ WIRED | live `--current` executed |
| `thread_scaling.py` | `target/release/rustkmer` | list-form subprocess per arm | ✓ WIRED | live RED run |
| `tests/thread_pool_size_tests.rs` | `verify_threads.py` | subprocess + `--json` records | ✓ WIRED | ignored gate ran and observed 18 |
| `contention_bench.py` | `microbench_Cargo.toml` | `@REPO_ROOT@` substitution + lockfile sha gate | ✓ WIRED | lock sha matches |
| `python_bench.py` | `bench.py` | `measure([python, __file__, --worker, ...])` | ✓ WIRED | code + baseline |
| `n_read_differential.py` | `pyo3` `PyDatabase.export_all_kmers` | CLI map decode | ✓ WIRED | code :215-216 |
| `benchmark.yml` | `thread_scaling.py` | measure-only → upload → `--current` verdict | ✓ WIRED | workflow :136/:150 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `slice_parity.crr1936095.json` | expected distinct/total | jellyfish 2.3.1 external reference, bound to source sha256 `dae91042…` | Yes | ✓ FLOWING |
| `thread_scaling_baseline.json` | arm medians | `/usr/bin/time` OS rusage over real 4M-read slice | Yes | ✓ FLOWING |
| `contention_evidence.json` | ns_per_window | standalone microbench on real random-record subslice (200k, seed 20261112) | Yes | ✓ FLOWING |
| `python_bench_baseline.darwin.json` | control counts/timings | fresh PyO3 worker on filtered real subslice + CLI parity | Yes | ✓ FLOWING |
| `n_read_differential.json` | per-case maps | CLI `.rkdb` + Python `add_from_fastq` on same FASTQ bytes | Yes | ✓ FLOWING |
| `thread_reality_evidence.json` | observed OS threads | macOS `sample` on live CLI child | Yes | ✓ FLOWING |
| `golden_capture.json` | fixture sha256 | read-only rehash of committed fixtures | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full harness suite passes | `python3 -m unittest discover -s scripts/bench/tests -t .` | `Ran 302 tests ... OK (skipped=1)` | ✓ PASS |
| Thread-scaling gate is RED on the committed baseline | `python3 scripts/bench/thread_scaling.py --current thread_scaling_baseline.json` | exit 1; `SCALING VERDICT result=RED speedup_t4=1.0318 speedup_t16=1.0505` | ✓ PASS |
| Pool-size standing gate is RED | `cargo test --locked --test thread_pool_size_tests -- --ignored` | `requested=1 observed=18` FAILED; exit 101 | ✓ PASS |
| Pool-size characterization pins the bug | `cargo test --locked --test thread_pool_size_tests` | `1 passed; 1 ignored` | ✓ PASS |
| Golden manifest integrity | `cargo test --locked --test golden_sha256_tests` | `5 passed` | ✓ PASS |
| Pinned-parity gate runs and records provenance | `python3 scripts/bench/bench.py --mode synthetic --reads 20000 --parity-only --out /tmp/parity_smoke.json` | exit 0; `PARITY OK distinct=2400000 total=2400000`; provenance present | ✓ PASS |
| MSRV 1.82 clippy (root) | `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` | exit 0 | ✓ PASS |
| MSRV 1.82 clippy (pyo3) | `cargo +1.82.0 clippy --locked --all-targets --manifest-path pyo3/Cargo.toml -- -D warnings` | exit 0 | ✓ PASS |

### Probe Execution

N/A — not a migration/CLI-probe phase; no `scripts/*/tests/probe-*.sh` declared or found.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| PROF-01 | 05-01/02/04/07 | slice bench + parity + provenance + random subslices | ✓ SATISFIED | truths 1, 8; live parity smoke |
| PROF-02 | 05-01/03/07 | pool-size test + thread-scaling gate | ✓ SATISFIED | truths 2, 3; live RED runs |
| PROF-03 | 05-05 | contention microbench split | ✓ SATISFIED | truth 4; 36/36 conservation |
| PROF-04 | 05-06/07 | Python benchmark + committed baseline | ✓ SATISFIED | truth 5 |
| PROF-05 | 05-06 | CLI-vs-Python N-read differential | ✓ SATISFIED | truth 6 |

No orphaned requirements mapped to Phase 5 in REQUIREMENTS.md.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX`, no `TODO`/`HACK`/`PLACEHOLDER`, no stub returns in phase-modified files | — | None |
| `.planning/PROJECT.md` | 69 | Historical narrative sentence still says "MSRV 1.80 enforced in both manifests" (describes the pre-raise v1.0 hygiene wave) | ℹ️ Info | Not a guardrail: the binding v2.0 guardrail at `PROJECT.md:92` and both manifests/CI say 1.82 |
| `.planning/ROADMAP.md` | 60 | Plan label still reads "Rust 1.80 MSRV toolchain" for 05-02 | ℹ️ Info | Historical plan title; actual implementation raised to 1.82 mid-phase by user decision |

### Test Quality Audit

| Test Area | Linked Req | Active | Skipped/Ignored | Circular | Assertion Level | Verdict |
| --------- | ---------- | ------ | --------------- | -------- | --------------- | ------- |
| `test_thread_scaling.py` (20) | PROF-02 | 20 | 0 | No | Value (exact speedups/exit codes) | ✓ PASS |
| `test_schema.py` | PROF-01 | all | 0 | No | Value (sha256/provenance fixtures) | ✓ PASS |
| `test_degradation.py` | PROF-01 | all | 0 | No | Value/Behavioral (gate rejection matrix) | ✓ PASS |
| `test_verify_threads.py` (4) | PROF-02 | 4 | 0 | No | Value (exit/verdict contract) | ✓ PASS |
| `test_contention_bench.py` (30) | PROF-03 | 30 | 0 | No | Value (hand-built arithmetic) | ✓ PASS |
| `test_python_bench.py` (39) | PROF-04 | 39 | 1 env-gated | No | Value (parity/cross-rep identity) | ✓ PASS |
| `test_n_read_differential.py` (22) | PROF-05 | 22 | 0 | No | Value (map diff counts) | ✓ PASS |
| `thread_pool_size_tests.rs` | PROF-02 | 1 char. | 1 intentional standing gate | No | Value (`requested=`/`observed=`) | ✓ PASS — the ignored gate is the intentional RED instrument, ledgered in WINDOWS #21 and duplicated by the active CI `thread_scaling.py` gate |

- **Disabled tests on requirements:** only the deliberate PROF-02 standing gate; PROF-02 is additionally proven by the actively-run CI gate and committed RED evidence — not a disabled-only requirement.
- **Circular patterns:** none. Parity expected values derive from an external oracle (jellyfish 2.3.1); fixture tests use hand-built data.
- **Expected-value provenance:** VALID for parity (external tool); the golden manifest is a tamper check against pre-existing fixtures, explicitly noted as not a write-path proof (Phase 8 OUT-02).

### Decision Coverage

Not evaluated — the decision-coverage gate could not parse the CONTEXT.md decisions block (`reason: could-not-parse`; the phase uses prose headings rather than `D-NN` entries). No counts reported; non-blocking.

### Human Verification Required

N/A — infrastructure/foundation phase with no user-facing elements. All acceptance criteria are verifiable programmatically and were re-run above. No ⚠️ PRESENT_BEHAVIOR_UNVERIFIED or ⚠️ `insufficient_spec` truth exists (the gates that assert runtime behavior — pool size, thread scaling, parity, conservation, golden integrity — were executed, not merely inspected).

### Gaps Summary

None. Every Phase 5 roadmap success criterion is achieved in the codebase with executed evidence:

- Pinned slice parity (229,694,874 / 519,271,168), provenance on every artifact, random-record sub-slicing — verified live.
- `--threads` is demonstrably a no-op (observed 18 OS threads at `--threads 1`; root cause in the eager `rayon::current_num_threads()` fallback), with a RED pool-size gate and a RED t1/t4/t16 scaling baseline.
- Contention split recorded (atomics 120.22 ns / 115%; bandwidth -15.82 ns recorded honest-inconclusive; multiplier 1.88) with an audited lockfile.
- Python baseline committed with a D2-invariant N-free control (CLI == Python 73,476,107/129,579,577).
- N-read divergence quantified (33 Python-only chimeras across 4 cases).
- Gates are standing in CI with `always()` evidence uploads and no error-softening constructs.
- MSRV raised to 1.82 (user-approved) with both clippy gates green; WINDOWS 19/20 closed.
- No counting hot-path, `.rkdb` format, or public API change.

The intentional PROF-02 red is the phase's deliverable (the standing gate observing the real bug), not a regression; Phase 6 (PAR-01) owns turning it green.

---

_Verified: 2026-11-12T10:25:32Z_
_Verifier: Claude (gsd-verifier)_
