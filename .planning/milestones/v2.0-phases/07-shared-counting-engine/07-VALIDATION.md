---
phase: "07"
slug: "shared-counting-engine"
status: draft
nyquist_compliant: true
wave_0_complete: false
created: "2026-11-12"
---

# Phase 07 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Rust built-in `cargo test` + `proptest` 1.5; Python `pytest` >= 7 in `pyo3/tests/` (Phase 9 / optional bridge) |
| **Config file** | `Cargo.toml`, `pyo3/pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `cargo test --locked --lib --test thread_local_count_tests --test kmer_rolling_differential_tests` |
| **Full suite command** | `cargo test --locked` (26 suites, 432 passed / 0 failed / 4 ignored at Phase 6 close) |
| **Harness gates** | `python3 scripts/bench/thread_scaling.py --mode synthetic --reads 500000 --reps 3`; slice `--mode slice --input "$SLICE" --slice-reads 4000000`; `python3 scripts/bench/bench.py --mode synthetic --parity-only`; `python3 -m unittest discover -s scripts/bench/tests -t .` |
| **Estimated runtime** | quick ~60 s; full suite ~5-8 min; slice scaling arms minutes |

---

## Sampling Rate

- **After every task commit:** `cargo test --locked --lib` plus the suite touched by the task (engine tests, extraction differential, golden).
- **After every plan wave:** `cargo test --locked` full suite; `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` on both crates; `python3 -m unittest discover -s scripts/bench/tests -t .`.
- **Before `/gsd-verify-work`:** Full suite green; engine parity + determinism gates green.
- **Max feedback latency:** ~8 minutes (full suite).

---

## Per-Task Verification Map

| Req ID | Behavior | Test Type | Automated Command | File Exists |
|--------|----------|-----------|-------------------|-------------|
| ENGINE-01 | `execute_count` counts through `CountEngine`; no per-chunk `par_chunks` hot loop; engine CLI output equals the reference map at t1/t4/t16 | integration | `cargo test --locked --test count_engine_tests` | ❌ Wave 0 |
| ENGINE-01 | Disjointness + conservation: every key exactly one partition; sum totals/uniques = reference; union = reference map | property/integration | `cargo test --locked --test count_engine_tests disjointness_conservation` | ❌ Wave 0 |
| ENGINE-01 | Multi-file cumulative counts = elementwise sum of per-file runs | e2e | `cargo test --locked --test count_engine_tests multi_file` | ❌ Wave 0 |
| ENGINE-01 | `--threads N` sizes both rayon pool and engine workers; observer formula updated to 2N+1 / 2 | integration | `cargo test --locked --test thread_pool_size_tests`; `python3 -m unittest scripts.bench.tests.test_verify_threads` | ✅ update needed |
| ENGINE-02 | Thread-scaling gate GREEN; slice wall drops vs Phase 6 baseline; counts identical | e2e/benchmark | `python3 scripts/bench/thread_scaling.py --mode synthetic --reads 500000 --reps 3`; slice run with provenance | ✅ gate exists; new evidence |
| ENGINE-02 | Peak RSS at t1/t4/t16 on slice; no regression vs Phase 6 (target ~12 GB) | benchmark | `/usr/bin/time -l` around slice arms; record max RSS | ✅ harness supports RSS |
| ENGINE-02 | Pinned parity (229,694,874 / 519,271,168) BEFORE timing | e2e | `python3 scripts/bench/bench.py --mode ... --parity-only`; slice parity report | ✅ exists |
| ENGINE-03 | `for_each_window` equals reference for k 1..=64: N at every position, lowercase, record boundaries, empty/short, canonical on/off | differential | `cargo test --locked --test window_extract_differential_tests` | ❌ Wave 0 |
| ENGINE-03 | Multi-member gzip counts all members; trailing garbage fails loudly; same counts at t1/t4 | integration | `cargo test --locked --test count_engine_tests multi_member_gzip` | ❌ Wave 0 |
| ENGINE-03 | Python output unchanged in Phase 7 (pre-filter retained); D2 proven in Phase 9 | e2e | `pytest pyo3/tests/test_counter.py -q` after `maturin develop --release` | ✅ exists |
| Exactness | Golden `.rkdb` v2 sha256 unchanged at t1/t4/t16; sortedness via both consumers | differential | `cargo test --locked --test golden_sha256_tests`; slice sha256 comparison | ✅ exists |
| Exactness | Per-key u32 overflow verbatim; aggregate summation fail-loud (seeded `u64::MAX`, helper tested directly) | unit/integration | `cargo test --locked --test thread_local_count_tests`; engine overflow tests | ✅ + ❌ Wave 0 |
| Exactness | Old-vs-new and 1-vs-N differential matrix (k × canonical), partitioned tables | differential | `cargo test --locked --test dense_differential_tests --test parallel_count_tests`; engine matrix | ✅ + ❌ Wave 0 |
| MSRV/CI | 1.82 clippy both crates; PyO3 wheel builds; full suite green | gate | `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` (root + pyo3); `maturin build`/`develop` | ✅ exists |

---

## Wave 0 Requirements

- [ ] `tests/count_engine_tests.rs` — engine vs reference map, disjointness/conservation, t1/t4/t16, multi-file, overflow seeding, multi-member gzip, error propagation.
- [ ] `tests/window_extract_differential_tests.rs` (or extend `tests/kmer_rolling_differential_tests.rs`) — full k/N/boundary matrix for `for_each_window`.
- [ ] `tests/thread_pool_size_tests.rs` + `.planning/research/profiling/verify_threads.py` + `scripts/bench/tests/test_verify_threads.py` — exact 2N+1 / 2 formula with an end-to-end RED negative control (below-expected observed ⇒ exit 1 with requested/observed; exit 2 only for unobservable child/infra failures).
- [ ] A test-only aggregate-overflow seeding path for `CountResult` stats / checked-sum helper mirroring `LocalKmerCounts::seed_count`.
- [ ] A producer-vs-worker timing probe (feature-gated counters or standalone) so R1/R2 are measured, not guessed.
- [ ] No framework install needed: `cargo test`, `proptest`, `pytest`, `maturin` are present.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 8 min
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
