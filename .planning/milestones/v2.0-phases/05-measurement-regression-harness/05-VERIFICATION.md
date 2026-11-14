---
phase: 05-measurement-regression-harness
verified: 2026-11-14T04:19:48Z
status: passed
score: 12/12 must-haves verified
covered_files: [".github/workflows/benchmark.yml", ".github/workflows/ci.yml", ".planning/phases/05-measurement-regression-harness/05-01-PLAN.md", ".planning/phases/05-measurement-regression-harness/05-01-SUMMARY.md", ".planning/phases/05-measurement-regression-harness/05-02-PLAN.md", ".planning/phases/05-measurement-regression-harness/05-02-SUMMARY.md", ".planning/phases/05-measurement-regression-harness/05-03-PLAN.md", ".planning/phases/05-measurement-regression-harness/05-03-SUMMARY.md", ".planning/phases/05-measurement-regression-harness/05-04-PLAN.md", ".planning/phases/05-measurement-regression-harness/05-04-SUMMARY.md", ".planning/phases/05-measurement-regression-harness/05-05-PLAN.md", ".planning/phases/05-measurement-regression-harness/05-05-SUMMARY.md", ".planning/phases/05-measurement-regression-harness/05-06-PLAN.md", ".planning/phases/05-measurement-regression-harness/05-06-SUMMARY.md", ".planning/phases/05-measurement-regression-harness/05-07-PLAN.md", ".planning/phases/05-measurement-regression-harness/05-07-SUMMARY.md", ".planning/phases/05-measurement-regression-harness/contention_evidence.json", ".planning/phases/05-measurement-regression-harness/golden_capture.json", ".planning/phases/05-measurement-regression-harness/n_read_differential.json", ".planning/phases/05-measurement-regression-harness/slice_parity_evidence.json", ".planning/phases/05-measurement-regression-harness/thread_reality_evidence.json", ".planning/phases/05-measurement-regression-harness/thread_scaling_baseline.json", ".planning/research/profiling/microbench_Cargo.lock", ".planning/research/profiling/microbench_Cargo.toml", ".planning/research/profiling/microbench_main.rs", ".planning/research/profiling/verify_threads.py", "Cargo.toml", "pyo3/Cargo.toml", "scripts/bench/README.md", "scripts/bench/baselines/python_bench_baseline.darwin.json", "scripts/bench/baselines/slice_parity.crr1936095.json", "scripts/bench/bench.py", "scripts/bench/capture_goldens.py", "scripts/bench/contention_bench.py", "scripts/bench/n_read_differential.py", "scripts/bench/python_bench.py", "scripts/bench/random_slice.py", "scripts/bench/tests/test_contention_bench.py", "scripts/bench/tests/test_degradation.py", "scripts/bench/tests/test_n_read_differential.py", "scripts/bench/tests/test_python_bench.py", "scripts/bench/tests/test_schema.py", "scripts/bench/tests/test_thread_scaling.py", "scripts/bench/tests/test_verify_threads.py", "scripts/bench/thread_scaling.py", "src/database/prefix_cache_merge.rs", "tests/thread_pool_size_tests.rs"]
covered_digest: "v4:sha256:ee504391dfdebf15fdb48f780049b6d15b9f9ecac130b533df61a25d9cc99adc"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 12/12
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 5: Measurement & Regression Harness Verification Report

**Phase Goal:** Every downstream performance claim is measured against standing, reproducible gates — parity checked before timing, provenance on every artifact — and the known measurement gaps (thread reality, contention attribution, Python baseline, N-read divergence) are closed with recorded evidence.
**Verified:** 2026-11-14T04:19:48Z
**Status:** passed
**Re-verification:** Yes — stale-digest re-run against the current tree after Phases 6-10 (previous report: 2026-11-12, 12/12 passed)

## Goal Achievement

Verification was performed goal-backward against the actual codebase and committed artifacts — not SUMMARY.md prose. Every must-have was re-checked on the current tree, and the mechanically checkable claims were re-run: `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` on both crates, `cargo test --locked`, the current 571-test harness suite, the real pinned head-4M parity gate-proof, the committed RED scaling baseline re-verdict, a fresh current-tree scaling measurement, the golden capture, the Python benchmark worker path, and the N-read differential in its current post-D2 mode.

### Re-verification Notes (what changed vs the 2026-11-12 report)

- Phases 6/7 did what Phase 5 specified: the `--threads` no-op is fixed, so the phase's deliberately-RED instruments are now GREEN (the committed Phase 5 RED evidence is unchanged and remains the pre-fix record). This is the intended trajectory, not a regression.
- Phases 9/10 modified shared harness files covered by the digest: `bench.py` (memory parser), `python_bench.py` (post-D2 comparison/both-parts arms), `n_read_differential.py` (post-D2 modes), `thread_scaling.py` (comments), `verify_threads.py` (exact engine thread model), `tests/thread_pool_size_tests.rs` (active exact-formula gate), `benchmark.yml`/`README.md` (post-fix doctrine). The Phase 5 evidence JSONs and committed baselines are untouched since Phase 5.
- The covered-file set is identical to the previous report (47 files); the digest was recomputed over current bytes: `098ad659…` → `ee504391…`.
- Harness suite grew from 302 to 571 tests (Phase 5-relevant modules now total 276); all Phase 5-relevant tests pass.

### Observable Truths

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | Reproducible slice bench gates on pinned parity (Distinct 229,694,874 / Total 519,271,168 vs jellyfish) with provenance on every artifact and random-record (not head) subslices | ✓ VERIFIED | `scripts/bench/bench.py:689` `PARITY_PINNED_HEAD4M = {"distinct": 229694874, "total": 519271168}`; `scripts/bench/baselines/slice_parity.crr1936095.json` unchanged since Phase 5 holds the pinned head-4M record + a 1M random record (seed 20261112, selection manifest, output_sha256); `slice_parity_evidence.json` records both provenance-bearing passes (binary sha256 `8f64d442…`). Re-ran the real gate on the CURRENT tree: `bench.py --mode slice --input CRR1936095_r1.part_001.fq.gz --slice-selection head --slice-reads 4000000 --k 21 --hash-size 2G --parity-only --parity-reference …` → exit 0, `PARITY OK distinct=229694874 total=519271168`, `PARITY REFERENCE OK`, current release binary sha256 `f6ace9f7…`; synthetic smoke → exit 0 `PARITY OK distinct=2400000 total=2400000` with provenance |
| 2 | A `--threads` correctness test asserts the ACTUAL rayon pool size (phase-time RED on the 2026-11-12 tree; GREEN now that Phase 6 fixed the flag) | ✓ VERIFIED | `tests/thread_pool_size_tests.rs:198` `pool_size_matches_requested_threads` now runs in the default suite; `:143` characterization; `:48` `expected_total` pins 2 at N=1 and 2N+1 at N=4/16. The Phase 5 RED observation is committed in `thread_reality_evidence.json` (requested 1/4/16 → observed 18/17/17, verdict RED, per-record provenance sha256 `8f64d442…`). Current tree: `cargo test --locked` → both pool-size tests `ok` (2 passed; exact 2/9/33 formula), the intended Phase 6/7 green |
| 3 | Thread-scaling gate records t1/t4/t16 wall-clock and is RED while the flag is a no-op (committed Phase 5 baseline; fresh current-tree measurement is GREEN after Phase 6) | ✓ VERIFIED | `scripts/bench/thread_scaling.py:100` `rotation_schedule`, `:126` `scaling_verdict`. Committed `thread_scaling_baseline.json` (unchanged): medians 72.270/70.045/68.795 s, speedup_t4 1.031765… / speedup_t16 1.050512… < 1.3, identical counts 229,694,874/519,271,168, provenance. Re-ran `--current` on that baseline → exit 1, `SCALING VERDICT result=RED speedup_t4=1.031765293739739 speedup_t16=1.0505123918889456 min_speedup=1.3`. Fresh current-tree measurement (`--mode synthetic --reads 200000 --reps 2`) → exit 0, `SCALING VERDICT result=GREEN speedup_t4=2.487012987012987 speedup_t16=2.9689922480620154`, identical non-zero counts 25,999,819/26,000,000, schema+provenance valid |
| 4 | Multi-thread contention microbench produces a recorded global-atomics vs memory-bandwidth split as Phase 7 evidence | ✓ VERIFIED | `contention_evidence.json` unchanged: 4 variants (`shared-counter`, `shared-dashmap`, `atomic-only`, `thread-local`) × t1/t4/t16 × 3 counterbalanced rounds = 36 records, 36/36 `conservation_ok`; attribution-v1 persisted with formulas: global-atomics 120.21998225808184 ns (115.1575%), bandwidth -15.82388640457436 ns (-15.1575%, honest "inconclusive" note, not clamped), multiplier 1.8768642164029798; committed `microbench_Cargo.lock` sha256 `eabd946a…` matches the evidence and the file. Arms at `microbench_main.rs:243-246`, conservation at `:585-589`; manifest `@REPO_ROOT@` at `microbench_Cargo.toml:14`, zero `/Users/forrest` pins |
| 5 | Python-surface counting benchmark runs and a sequential-pipeline baseline is committed | ✓ VERIFIED | `scripts/bench/baselines/python_bench_baseline.darwin.json` unchanged since Phase 5: `baseline_scope dev-host-local-comparison`, `comparison_basis n-free-control`; nested control arm `py21-n-free-control-t1` median 32.14 s over 3 reps, `parity_control.equal=true` with CLI==Python 73,476,107/129,579,577, exact counts identical across reps; native `.so` sha256 `c7701806…` recorded. Current tooling still accepts it: `validate_baseline_identity(...) → OK`; the env-gated real-worker test passes with `RUSTKMER_PYBENCH_VENV=.venv313` (`took 0.281 s, ok`) |
| 6 | CLI-vs-Python N-read differential is executed and recorded, quantifying chimeric-k-mer divergence | ✓ VERIFIED | `n_read_differential.json` unchanged: 9 cases, verdict PASS `expect=divergence`, control exactly equal, 4 divergent N cases, 33 Python-only chimeras, 0 CLI-only, 0 count deltas; both surfaces' provenance (binary `8f64d442…`, module `c7701806…`). Current tree: the differential still runs end-to-end; post-D2 `--expect-unified` → exit 0 `N-READ DIFFERENTIAL result=PASS expect=unified cases=9 divergent=0`, confirming the Phase 5 record is the pre-D2 baseline Phase 9 superseded by design |
| 7 | The gates are standing and wired into CI without softening | ✓ VERIFIED | `.github/workflows/benchmark.yml:90` harness unittest suite, `:121` Python benchmark, `:136` scaling measure-only, `:150` `--current` verdict; all three uploads (`:97`, `:124`, `:139`) carry `if: always()` + `if-no-files-found: warn`; `grep -E 'continue-on-error\|\|\| true'` → NONE; measurement/gate steps are unconditional. Phase 6 updated the comments from "intentionally RED" to "standing gate must stay GREEN"; the gate chain itself is unchanged. Live: the suite command passes (571 tests), the committed baseline re-verdict is RED (exit 1), and a fresh measurement is GREEN (exit 0) |
| 8 | Pre-refactor golden `.rkdb` capture exists, is non-regenerating, and fixtures are unchanged | ✓ VERIFIED | `golden_capture.json` manifest_sha256 `f010e42a…` equals `shasum -a 256 tests/fixtures/golden_manifest.sha256`; 12/12 fixture hashes match on disk; `git diff c357915..HEAD -- tests/fixtures/` empty; `capture_goldens.py` re-run on the current tree → exit 0, 12 fixtures, golden test rc 0; `cargo test --locked` → `golden_sha256_tests` 5 passed. The script only rehashes + runs the golden test and never invokes the generator |
| 9 | MSRV is 1.82 with MSRV-aware clippy green on BOTH crates; no 1.80 guardrail residue | ✓ VERIFIED | `Cargo.toml:5`, `pyo3/Cargo.toml:5`, `microbench_Cargo.toml:8` all `rust-version = "1.82"`; `ci.yml:51,108` pin `toolchain: 1.82.0` in both clippy jobs with isolated `msrv182` caches; re-ran `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` → exit 0 (root and pyo3). WINDOWS 19/20 remain `fixed` |
| 10 | No counting hot-path / `.rkdb` format / public API changes in the Phase 5 window | ✓ VERIFIED | Phase-window diff `c357915..1800263` over `src/`, `pyo3/src/`, `tests/fixtures/`, both Cargo.locks: only `src/database/prefix_cache_merge.rs` (approved MSRV clippy `needless_range_loop` fix, commit `23967d5`) plus the two `rust-version` manifest lines; no `format.rs`, no `pyo3/src`, no lockfile changes. Later Phases 6-9 changed the hot path intentionally, outside this phase's window — not a Phase 5 regression |
| 11 | Schema-v1 committed baselines remain loadable | ✓ VERIFIED | Current `bench.validate_schema` (`SCHEMA_VERSION = 1` at `bench.py:44`) accepts `bench_baseline.darwin.json`, `bench_baseline.linux.json`, `thread_scaling_baseline.json`; `validate_schema` body is unchanged. (`slice_parity.crr1936095.json` is a parity-reference document, not a results doc; it is validated by `_load_reference_doc`/`_validate_reference_record` and by the live gate-proof in truth 1.) |
| 12 | All phase requirements PROF-01..05 are covered | ✓ VERIFIED | Plans declare PROF-01 (01/02/04/07), PROF-02 (01/03/07), PROF-03 (05), PROF-04 (06/07), PROF-05 (06); `.planning/REQUIREMENTS.md` maps all five to Phase 5 `Complete`; artifacts/evidence verified per rows 1-6. No orphaned requirements |

**Score:** 12/12 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `scripts/bench/bench.py` | provenance builder/validator + parity-reference gate + random selection | ✓ VERIFIED | `binary_provenance` :345, `validate_provenance` :378, `PARITY_PINNED_HEAD4M` :689, `load/gate/capture_parity_reference` :919/:965/:1028, `selection_identity_from` :990, `provision_random_slice` :615; live real gate-proof passed |
| `scripts/bench/thread_scaling.py` | PROF-02 standing gate | ✓ VERIFIED | `rotation_schedule` :100, `scaling_verdict` :126, exit 0/1/2, structured verdict line; live RED-baseline and GREEN-fresh runs |
| `scripts/bench/random_slice.py` | seeded reservoir slicer | ✓ VERIFIED | importable `reservoir_slice` :25, used by `bench.py:637,658`; tests pass |
| `scripts/bench/contention_bench.py` | contention controller + attribution | ✓ VERIFIED | 621-line controller; lockfile sha gate; 36/36 conservation evidence; 30-test suite passes |
| `scripts/bench/python_bench.py` | fresh-worker Python bench | ✓ VERIFIED | `--worker` :1133, `measure_arm` :739; no in-process clock; env-gated real-worker test passes |
| `scripts/bench/n_read_differential.py` | CLI-vs-Python differential | ✓ VERIFIED | `export_all_kmers` :287, `add_from_fastq` :289; Phase 5 evidence record + current post-D2 `--expect-unified` run exit 0 |
| `tests/thread_pool_size_tests.rs` | pool-size observation pair | ✓ VERIFIED | characterization :143 and standing gate :198 both active; `cargo test --locked` green (2 passed) |
| `.planning/research/profiling/verify_threads.py` | hardened thread observer | ✓ VERIFIED | `expected_total` :86, `verdict_for_records` :192, `THREAD REALITY` line :297, exit 0/1/2 |
| `.planning/research/profiling/microbench_main.rs` | 4 mechanism arms | ✓ VERIFIED | arms :243-246, conservation abort/write at :585-589 |
| `.planning/research/profiling/microbench_Cargo.toml/.lock` | relocatable, audited | ✓ VERIFIED | one `@REPO_ROOT@` (:14), zero `/Users/forrest`; lock sha matches evidence |
| `.github/workflows/benchmark.yml` | standing gates | ✓ VERIFIED | see truth 7 |
| `scripts/bench/baselines/slice_parity.crr1936095.json` | pinned + random parity records | ✓ VERIFIED | both records with provenance/identity, unchanged since Phase 5 |
| `scripts/bench/baselines/python_bench_baseline.darwin.json` | committed Python baseline | ✓ VERIFIED | dev-host scope + n-free control basis, unchanged since Phase 5 |
| Evidence JSONs (thread_reality, golden_capture, slice_parity, thread_scaling, contention, n_read) | recorded, provenance-bearing | ✓ VERIFIED | all present, tracked, `validate_provenance` passes on every artifact |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `bench.py` | `random_slice.py` | `--slice-selection random` → `reservoir_slice` + manifest | ✓ WIRED | `bench.py:637,658` |
| `bench.py` parity gate | `slice_parity.crr1936095.json` | exact key + seed + manifest + output hash | ✓ WIRED | `load_parity_reference` :919; live head gate-proof exit 0 |
| `thread_scaling.py` | `bench.py` | imports measure/reduce_arm/binary_provenance/validate_* | ✓ WIRED | live current-tree measurement executed |
| `thread_scaling.py` | `target/release/rustkmer` | list-form subprocess per arm | ✓ WIRED | live GREEN run exit 0 |
| `tests/thread_pool_size_tests.rs` | `verify_threads.py` | subprocess + `--json` records | ✓ WIRED | `cargo test --locked` both tests pass |
| `contention_bench.py` | `microbench_Cargo.toml` | `@REPO_ROOT@` substitution + lockfile sha gate | ✓ WIRED | lock sha matches evidence |
| `python_bench.py` | `bench.py` | `measure([python, __file__, --worker, ...])` | ✓ WIRED | code :752; env-gated real-worker test passes |
| `n_read_differential.py` | `pyo3` `PyDatabase.export_all_kmers` | CLI map decode | ✓ WIRED | code :287; post-D2 run exit 0 |
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
| Full harness suite passes | `python3 -m unittest discover -s scripts/bench/tests -t .` | `Ran 571 tests ... OK (skipped=1)` | ✓ PASS |
| Phase 5-relevant modules pass | `python3 -m unittest scripts.bench.tests.{test_contention_bench,test_degradation,test_n_read_differential,test_python_bench,test_schema,test_thread_scaling,test_verify_threads}` | `Ran 276 tests ... OK (skipped=1)` | ✓ PASS |
| MSRV 1.82 clippy (root) | `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` | exit 0 | ✓ PASS |
| MSRV 1.82 clippy (pyo3) | `cargo +1.82.0 clippy --locked --all-targets --manifest-path pyo3/Cargo.toml -- -D warnings` | exit 0 | ✓ PASS |
| Rust test suite | `cargo test --locked` | exit 0; all binaries ok; pool-size 2 passed; golden 5 passed | ✓ PASS |
| Real pinned head-4M parity gate | `bench.py --mode slice --input CRR1936095_r1.part_001.fq.gz --slice-selection head --slice-reads 4000000 --k 21 --hash-size 2G --parity-only --parity-reference scripts/bench/baselines/slice_parity.crr1936095.json` | exit 0; `PARITY OK distinct=229694874 total=519271168`; `PARITY REFERENCE OK`; current binary sha256 `f6ace9f7…` | ✓ PASS |
| Synthetic parity smoke | `bench.py --mode synthetic --reads 20000 --parity-only --out /tmp/parity_smoke.json` | exit 0; `PARITY OK distinct=2400000 total=2400000`; provenance present | ✓ PASS |
| Committed RED scaling baseline re-verdict | `python3 scripts/bench/thread_scaling.py --current thread_scaling_baseline.json` | exit 1; `SCALING VERDICT result=RED speedup_t4=1.0318 speedup_t16=1.0505` | ✓ PASS |
| Fresh current-tree scaling gate | `python3 scripts/bench/thread_scaling.py --mode synthetic --reads 200000 --reps 2` | exit 0; `SCALING VERDICT result=GREEN speedup_t4=2.4870 speedup_t16=2.9690` | ✓ PASS |
| Golden capture re-run | `python3 scripts/bench/capture_goldens.py --out /tmp/golden_capture.json` | exit 0; 12 fixtures; golden test rc 0 | ✓ PASS |
| Python bench real worker | `RUSTKMER_PYBENCH_VENV=.venv313 python3 -m unittest scripts.bench.tests.test_python_bench.TestRealWorkerIntegration...` | `Ran 1 test ... OK` | ✓ PASS |
| Post-D2 N-read re-run | `.venv313/bin/python scripts/bench/n_read_differential.py --rustkmer target/release/rustkmer --expect-unified` | exit 0; `result=PASS expect=unified cases=9 divergent=0` | ✓ PASS |

### Probe Execution

N/A — not a migration/CLI-probe phase; no `scripts/*/tests/probe-*.sh` declared or found.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| PROF-01 | 05-01/02/04/07 | slice bench + parity + provenance + random subslices | ✓ SATISFIED | truths 1, 8; live real gate-proof + synthetic smoke |
| PROF-02 | 05-01/03/07 | pool-size test + thread-scaling gate | ✓ SATISFIED | truths 2, 3; committed RED evidence + current GREEN gate |
| PROF-03 | 05-05 | contention microbench split | ✓ SATISFIED | truth 4; 36/36 conservation |
| PROF-04 | 05-06/07 | Python benchmark + committed baseline | ✓ SATISFIED | truth 5; baseline identity validated + real worker test |
| PROF-05 | 05-06 | CLI-vs-Python N-read differential | ✓ SATISFIED | truth 6; Phase 5 divergence record + post-D2 re-run |

No orphaned requirements mapped to Phase 5 in REQUIREMENTS.md.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX`, no `TODO`/`HACK`/`PLACEHOLDER`, no stub returns in phase-covered implementation/test files | — | None |
| `.planning/PROJECT.md` | 71 | Historical narrative sentence still says "MSRV 1.80 enforced in both manifests" (describes the pre-raise v1.0 hygiene wave) | ℹ️ Info | Not a guardrail: the binding v2.0 guardrail and both manifests/CI say 1.82 |
| `.planning/ROADMAP.md` | 60 | Plan label still reads "Rust 1.80 MSRV toolchain" for 05-02 | ℹ️ Info | Historical plan title; actual implementation raised to 1.82 mid-phase by user decision |
| `scripts/bench/README.md` | 321 | Says the pool-size gate expects "requested + 1 OS threads", but after Phase 7 the test/helper use 2 at N=1 and 2N+1 at N>1 | ℹ️ Info | Post-Phase-7 documentation drift in a Phase 5-covered file; code/test/helper agree (2/9/33) and the gate passes. The Phase 5 contract (requested+1) was accurate when written. Recommend updating the bullet; not status-affecting |

### Test Quality Audit

| Test Area | Linked Req | Active | Skipped/Ignored | Circular | Assertion Level | Verdict |
| --------- | ---------- | ------ | --------------- | -------- | --------------- | ------- |
| `test_thread_scaling.py` (20) | PROF-02 | 20 | 0 | No | Value (exact speedups/exit codes) | ✓ PASS |
| `test_schema.py` (14) | PROF-01 | 14 | 0 | No | Value (sha256/provenance fixtures) | ✓ PASS |
| `test_degradation.py` (68) | PROF-01 | 68 | 0 | No | Value/Behavioral (gate rejection matrix) | ✓ PASS |
| `test_verify_threads.py` (18) | PROF-02 | 18 on this platform | 0 (platform-gated class active on macOS) | No | Value (exit/verdict contract) | ✓ PASS |
| `test_contention_bench.py` (30) | PROF-03 | 30 | 0 | No | Value (hand-built arithmetic) | ✓ PASS |
| `test_python_bench.py` (93) | PROF-04 | 93 | 1 env-gated (passes with `RUSTKMER_PYBENCH_VENV`) | No | Value (parity/cross-rep identity) | ✓ PASS |
| `test_n_read_differential.py` (33) | PROF-05 | 33 | 0 | No | Value (map diff counts) | ✓ PASS |
| `thread_pool_size_tests.rs` | PROF-02 | 2 | 0 (standing gate now active) | No | Value (exact `requested=`/`observed=` formula) | ✓ PASS |

- **Disabled tests on requirements:** none blocking; the only skip is the opt-in Python real-worker integration test, which was explicitly run and passed with `RUSTKMER_PYBENCH_VENV=.venv313`. No requirement is covered only by a disabled test.
- **Circular patterns:** none. Parity expected values derive from an external oracle (jellyfish 2.3.1); fixture tests use hand-built data.
- **Expected-value provenance:** VALID for parity (external tool); the golden manifest is a tamper check against pre-existing fixtures, explicitly noted as not a write-path proof (Phase 8 OUT-02).

### Decision Coverage

Not evaluated — the decision-coverage gate could not parse the CONTEXT.md decisions block (`reason: could-not-parse`; the phase uses prose headings rather than `D-NN` entries). No counts reported; non-blocking.

### Advisory (New Scope, Unevidenced)

None. The only new-scope observation (README line 321) has deterministic grep evidence and is recorded as ℹ️ Info above; it is not a blocker.

### Human Verification Required

N/A — infrastructure/foundation phase with no user-facing elements. All acceptance criteria are verifiable programmatically and were re-run above. No ⚠️ PRESENT_BEHAVIOR_UNVERIFIED or ⚠️ `insufficient_spec` truth exists: the gates that assert runtime behavior — pool size, thread scaling, parity, conservation, golden integrity — were executed, not merely inspected.

### Gaps Summary

None. The 2026-11-14 re-verification against the current tree confirms all 12 truths remain achieved:

- The pinned head-4M parity gate was re-proven live on the current binary: 229,694,874 / 519,271,168 vs jellyfish 2.3.1, with the committed fingerprint-bound random-record baseline intact.
- The Phase 5 RED thread instruments did their job and Phase 6 turned them green: the committed RED evidence (`thread_reality_evidence.json`, `thread_scaling_baseline.json`) is unchanged, the committed baseline still re-verdicts RED, and a fresh current-tree measurement is GREEN (t4 2.49x, t16 2.97x) with the pool-size test green (2/9/33) in `cargo test`.
- Contention attribution, the Python baseline, the N-read differential, the golden capture, MSRV 1.82 clippy on both crates, CI gate wiring, and schema-v1 baseline compatibility all re-verified. Both required external gates pass: `cargo test --locked` (all suites) and the 571-test harness suite (276 in Phase 5 modules). The real full-scale data gates remain Phase 10's domain; the slice gate is green here before them.
- No gaps and no regressions. The only current-tree note is the stale README thread-count bullet recorded as ℹ️ Info.

---

_Verified: 2026-11-14T04:19:48Z_
_Verifier: Claude (gsd-verifier)_
