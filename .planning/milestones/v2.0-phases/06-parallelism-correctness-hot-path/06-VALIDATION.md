---
phase: "06"
slug: "parallelism-correctness-hot-path"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-16"
validated: "2026-11-16"
---

# Phase 06 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> **Reconstructed post-execution** (validate-phase State B, 2026-11-16): the phase executed 2026-11-12 without a seeded VALIDATION.md; this record was audited from the archived artifacts (5 PLANs, 5 SUMMARYs, `06-VERIFICATION.md` re-run 2026-11-14 at 20/20 passed) and the test files on disk. It closes the v2.0 milestone-audit Nyquist coverage gap (HYG-02).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Rust `cargo test` (integration + `proptest` 1.5) + Python stdlib `unittest` (`scripts/bench/tests/`) + pytest (`pyo3/tests/`) |
| **Config file** | `Cargo.toml` (root), `pyo3/pyproject.toml` |
| **Quick run command** | `cargo test --locked --test thread_pool_size_tests --test thread_local_count_tests --test kmer_rolling_differential_tests` |
| **Full suite command** | `cargo test --locked` + `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` (both crates) + `python3 -m unittest discover -s scripts/bench/tests -t .` |
| **Harness gates** | `scripts/bench/thread_scaling.py` (PROF-02 standing gate, `--current` re-verdict); `scripts/bench/tests/test_verify_threads.py` (exact engine thread model; the `test_pre_engine_n_plus_one_stub_is_measured_red` negative control is a documented ~50% macOS `sample`-race flake — purge stale `target/` before trusting a red) |
| **Estimated runtime** | quick Rust suites ~60 s; full suite ~5-8 min |

---

## Sampling Rate

- **After every task commit:** `cargo test --locked --lib` plus the suite touched by the task (engine, differential, pool-size)
- **After every plan wave:** full locked suite + clippy both crates + harness unittest discovery
- **Before `/gsd-verify-work`:** full suite green; pool-size standing gate green; scaling verdict GREEN on a fresh measurement
- **Max feedback latency:** ~8 minutes

---

## Per-Task Verification Map

Reconstructed 2026-11-16 from plan frontmatter declarations and `06-VERIFICATION.md` (re-verified 2026-11-14 against the post-Phase-10 tree, 20/20 truths, digest `86d98ed3…`; supersessions by Phases 7/9 recorded there).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-* | 01 | 1 | PAR-02 | — | `--threads N` sizes the actual rayon pool (fresh children observe exactly N workers; resolver precedence preserved) | integration | `cargo test --locked --test thread_pool_size_tests` | ✅ | ✅ green (truths 1-3; exact 2/9/33 formula post-Phase-7) |
| 06-02-* | 02 | 1 | PAR-01, PAR-02, PAR-03 | — | Thread-scaling gate GREEN (speedup_t4/t16 ≥ 1.3, identical nonzero counts); true t1 baseline recorded with provenance | e2e/benchmark | `python3 scripts/bench/thread_scaling.py --mode synthetic --reads 500000 --reps 3` | ✅ `tests/test_thread_scaling.py` | ✅ green (truths 4-5, 17: fresh t1 5.570 s vs pre 18.77 s) |
| 06-03-* | 03 | 1 | PAR-03 | — | Thread-local accumulation: per-worker tables, once-per-file reduction, no shared per-window increment in the hot loop; checked overflow fail-loud | unit/integration | `cargo test --locked --test thread_local_count_tests` | ✅ | ✅ green (truths 6-7, 10; aggregate-overflow regression `concurrent_local_reduction_never_loses_aggregate_total` passes) |
| 06-04-* | 04 | 1 | PAR-01 | — | Local-path maps equal pre-change and 1-vs-N maps across k {21,32,64}×canonical; multi-file CLI output equals elementwise sum | differential | `cargo test --locked --test thread_local_count_tests --test kmer_rolling_differential_tests` | ✅ | ✅ green (truths 8, 11-15: full edge matrix, masked rolling encoder, k 33..64 u128 path, bit-parallel revcomp) |
| 06-05-* | 05 | 1 | PAR-02 | — | Gap closure: aggregate `total_kmers` never lost under parallel reduction (`AtomicU64::fetch_update` checked add, verbatim overflow message) | regression | `cargo test --locked --test thread_local_count_tests concurrent_local_reduction_never_loses_aggregate_total` | ✅ (`tests/thread_local_count_tests.rs:707-802`) | ✅ green (16 threads × 2000 barrier rounds pass; pre-fix RED reproduction remains historical evidence the test is not vacuous) |
| — | — | — | PAR-01..03 (standing) | — | Release-only rolling-encoder timing gate (measured, not guessed); CI/README present PROF-02 gates as standing, no softener | benchmark + gate | `cargo test --locked --release --features profiling` (ignored timing gate); grep workflows for `continue-on-error` | ✅ | ✅ green (truths 16, 19, 20: per-window 3.204 µs vs rolling 0.876 µs; zero workflow silencing; Phase 5 RED baseline untouched) |
| — | — | — | PAR-02 (PyO3) | — | PyCounter public API unchanged; file methods accumulate through the same local core (`py.detach`, owned Send captures) | e2e (pytest) | `pytest pyo3/tests/test_counter.py -q` after `maturin develop --release` | ✅ | ✅ green (truths 9, 15, 19: 158 passed / 63 skipped on rebuilt module) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Known-flake note (STATE.md): `scripts/bench/tests/test_verify_threads.py::TestNegativeControls::test_pre_engine_n_plus_one_stub_is_measured_red` is a pre-existing ~50% macOS `sample`-race flake — treat a red as suspected-flake first; purge stale `target/` artifacts before trusting it. Phase 6-relevant modules were green on the 2026-11-16 suite run.

---

## Wave 0 Requirements

- [x] `tests/thread_pool_size_tests.rs` — exact rayon/engine thread formula (2 at N=1, 2N+1 at N>1) with end-to-end RED negative control
- [x] `tests/thread_local_count_tests.rs` — local accumulation, checked overflow, aggregate-total regression, conservation
- [x] `tests/kmer_rolling_differential_tests.rs` — rolling-encoder reference differential (full edge matrix, k 1..=32) + k 33..64 u128 path parity
- [x] `scripts/bench/tests/test_verify_threads.py` + `.planning/research/profiling/verify_threads.py` — observed-thread model probe
- [x] Evidence JSONs beside archived artifacts: `phase6_gates_evidence.json`, `phase6_exactness_evidence.json`, `phase6_measurement.json`, `phase6_scaling_green.json`, `phase6_slice_green.json`, `thread_scaling_par01_green.json`, `thread_scaling_par01_slice.json`
- [x] No framework install needed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions | Outcome |
|----------|-------------|------------|-------------------|---------|
| 4M real-slice t1 measurement with provenance (`phase6_slice_green.json`) | PAR-01/02 | Requires the local CRR1936095 dataset; CI carries none | `bench.py --mode slice ... --reps 3 --threads 1` on part data | **DONE** — recorded: slice t1 57.16 s vs pre 142.54 s, pinned counts 229,694,874 / 519,271,168 (truth 5/17; not re-measured in the 2026-11-14 round — recorded artifact valid, fresh synthetic t1 lower still) |
| Live thread observation of a fresh CLI child | PAR-02 | Requires process inspection on a real run (`sample`-based probe; platform-sensitive) | `python3 -m unittest scripts.bench.tests.test_verify_threads` (env-gated) | **DONE 2026-11-14** — verification re-ran a live thread observation matching the exact formula (truth 1); known flake handling per STATE.md |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none remained at phase close)
- [x] No watch-mode flags (release-profile timing gates are feature/ignored-gated, not watch-mode)
- [x] Feedback latency < 8 min
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-11-16 — reconstructed from archived artifacts; grounding: `06-VERIFICATION.md` re-verification 2026-11-14 (20/20 truths, 0 behavior-unverified, digest `86d98ed3…`, supersessions by Phases 7/9 explicitly recorded), Rust/harness suites green at the 2026-11-16 run, per-plan requirement frontmatter greps consistent with the report.

## Validation Audit 2026-11-16

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
