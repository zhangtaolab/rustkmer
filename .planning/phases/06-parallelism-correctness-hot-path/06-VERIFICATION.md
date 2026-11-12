---
phase: 06-parallelism-correctness-hot-path
verified: 2026-11-12T13:50:05Z
status: passed
score: 20/20 must-haves verified
covered_files: [".github/workflows/benchmark.yml", ".planning/phases/06-parallelism-correctness-hot-path/06-01-PLAN.md", ".planning/phases/06-parallelism-correctness-hot-path/06-01-SUMMARY.md", ".planning/phases/06-parallelism-correctness-hot-path/06-02-PLAN.md", ".planning/phases/06-parallelism-correctness-hot-path/06-02-SUMMARY.md", ".planning/phases/06-parallelism-correctness-hot-path/06-03-PLAN.md", ".planning/phases/06-parallelism-correctness-hot-path/06-03-SUMMARY.md", ".planning/phases/06-parallelism-correctness-hot-path/06-04-PLAN.md", ".planning/phases/06-parallelism-correctness-hot-path/06-04-SUMMARY.md", ".planning/phases/06-parallelism-correctness-hot-path/06-05-PLAN.md", ".planning/phases/06-parallelism-correctness-hot-path/06-05-SUMMARY.md", ".planning/phases/06-parallelism-correctness-hot-path/phase6_exactness_evidence.json", ".planning/phases/06-parallelism-correctness-hot-path/phase6_gates_evidence.json", ".planning/phases/06-parallelism-correctness-hot-path/phase6_measurement.json", ".planning/phases/06-parallelism-correctness-hot-path/phase6_scaling_green.json", ".planning/phases/06-parallelism-correctness-hot-path/phase6_slice_green.json", ".planning/phases/06-parallelism-correctness-hot-path/thread_scaling_par01_green.json", ".planning/phases/06-parallelism-correctness-hot-path/thread_scaling_par01_slice.json", ".planning/research/profiling/verify_threads.py", "pyo3/src/counter.rs", "pyo3/tests/test_counter.py", "scripts/bench/README.md", "scripts/bench/tests/test_verify_threads.py", "scripts/bench/thread_scaling.py", "src/cli/commands/count.rs", "src/hash/local.rs", "src/hash/mod.rs", "src/hash/table.rs", "src/kmer/canonical.rs", "src/kmer/encoding.rs", "tests/kmer_rolling_differential_tests.rs", "tests/thread_local_count_tests.rs", "tests/thread_pool_size_tests.rs"]
covered_digest: "v4:sha256:6dfab9798e65b18bd632b02fe2b822cd89aa7b8b231fe76070ef3c728d311793"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 19/20
  gaps_closed:
    - "total_kmers, unique_kmers, and filtering statistics keep their existing semantics, including the rule that a failed increment does not advance the total"
  gaps_remaining: []
  regressions: []
---

# Phase 6: Parallelism Correctness & Hot Path Verification Report

**Phase Goal:** Thread control actually works and the single-thread hot path is measurably faster while counts stay exactly equal — establishing the true t1 baseline and contention-free accumulation before the engine restructure.
**Verified:** 2026-11-12T13:50:05Z
**Status:** passed
**Re-verification:** Yes — after gap closure (06-05)

## Gap Closure Verification (06-05)

**Prior Gap 1 — aggregate `total_kmers` lost updates under the 06-04 parallel reduction — is RESOLVED.** Every claim below was re-executed against the codebase in this round; SUMMARY.md was not treated as evidence.

- **Atomic publication confirmed.** `src/hash/table.rs:483-487` publishes the shared total with `AtomicU64::fetch_update(Relaxed, Relaxed, |current| current.checked_add(merged_total))` — a compare-exchange loop. The old non-atomic load + `checked_add` + `store` is gone; the fix diff (`f61534b`) replaces exactly that block plus docs and one unit test.
- **Fail-loud overflow preserved.** On `Err` (checked sum would exceed `u64::MAX`) the total is left untouched — no wrap, no saturation — `unique_kmers` is still published to match the poisoned partial table, and the verbatim `Total k-mer count overflow during local reduction` error is returned (`src/hash/table.rs:488-499`). Mid-loop poison publications remain `fetch_add`; per-key sums remain `checked_add`.
- **Parallelism preserved.** `reduce_local_counts` still merges drained locals via `locals.par_iter().try_for_each` (`src/hash/table.rs:542-549`). No mutex, no serialization, no public signature change. The only new shared operation is one CAS per local merge.
- **Deterministic regression exists and passes.** `concurrent_local_reduction_never_loses_aggregate_total` (`tests/thread_local_count_tests.rs:708`) runs 16 threads x 2000 barrier-synchronized rounds, one distinct key per thread per round, and asserts `total_kmers == 16` and `unique_kmers == 16` every round plus a final table of 16 entries of count 1. The targeted suite is 10/10 green.
- **The regression is not vacuous — independently proven RED pre-fix.** An isolated build of the test-only commit `bdb21e6` (pre-fix load + checked_add + store publication, confirmed at `src/hash/table.rs:470`/`:481` in that tree) fails with `lost rounds=229/2000 (first failing round Some(1), observed Some((15, 16)), expected total 16)`, exit 101. The test exercises the public concurrent `merge_local_counts` path, so it genuinely guards the race.
- **Overflow unit test green.** `local_reduction_total_overflow_is_fail_loud_and_never_wraps` seeds `u64::MAX - 1`, merges a delta of 2, and passes: verbatim error, total remains `u64::MAX - 1`, merged key count 2, stored sum 2, `unique_kmers == 1`.

## Goal Achievement

Verification was performed goal-backward against the codebase and committed artifacts, and the claims were re-executed rather than trusted from SUMMARY.md. This re-verification focused on the one prior blocker and regression-checked the other 19 truths: the targeted concurrency suite, the pre-fix RED reproduction, the full locked suite, MSRV 1.82 clippy on both crates (forced rebuilds), the pool-size standing gate, a fresh thread-scaling gate on a rebuilt release binary, the pinned parity smoke, the rebuilt PyO3 module's Python suite, scope guards, and the standing-gate/baseline immutability checks. All 20 truths are now evidenced.

### Observable Truths

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | `--threads N` sizes the ACTUAL rayon pool: fresh CLI children at N in {1,4,16} observe exactly N workers plus main | ✓ VERIFIED | `cargo test --locked --test thread_pool_size_tests` re-run → 2 passed, 0 ignored; independent release-binary observation `.planning/research/profiling/verify_threads.py` → requested/observed `(1,2) (4,5) (16,17)`, GREEN, exit 0 (prior executed evidence; `count.rs` unchanged by the gap fix) |
| 2 | Precedence `--threads > RUSTKMER_THREADS > RAYON_NUM_THREADS > all cores` unchanged; Python `threads=` / IN-04 warn semantics preserved | ✓ VERIFIED | `resolve_thread_count_from` + its 7 unit tests pass in the full suite; `pyo3/src` diff since `4b61fb9` is empty (no signature or warn change) |
| 3 | No rayon pool-size query or parallel operation before `build_global(resolved)`; the all-cores fallback is lazy | ✓ VERIFIED | `src/cli/commands/count.rs` unchanged by the gap fix; resolver at 875-888 uses `std::thread::available_parallelism`; `build_global` at 101-104 before counting; no `current_num_threads` in the file |
| 4 | Thread-scaling gate GREEN with `speedup_t4` and `speedup_t16` >= 1.3 and identical nonzero counts | ✓ VERIFIED | Fresh run on the rebuilt fixed release binary: t1/t4/t16 medians 12.900 / 8.130 / 6.490 s, `speedup_t4=1.5867158671586714`, `speedup_t16=1.987673343605547`, every arm `unique=64999000 total=65000000`; verdict `GREEN`; exit 0 |
| 5 | A true single-thread baseline is recorded with provenance; the slice arm runs whenever the documented input resolves | ✓ VERIFIED | Recorded `thread_scaling_par01_green.json` (synthetic t1) and `thread_scaling_par01_slice.json` (4M slice t1) are unchanged since 06-04 and schema/provenance valid; the fresh gate reproduced synthetic t1 at 12.900 s median |
| 6 | CLI file counting accumulates in per-worker thread-local tables and reduces once per file; the hot loop has no shared per-window increment or atomic fetch-add | ✓ VERIFIED | `count.rs` unchanged; worker locals via `try_for_each_init` + `local_handle()`, per-file `reduce_local_counts()`; no `counter.increment(` and no `fetch_add` in `count.rs`; full suite green |
| 7 | The end reduction adds per-key u32 counts with checked arithmetic and returns the verbatim fail-loud overflow message; never wraps or saturates | ✓ VERIFIED | Per-key `checked_add` retained in both dense/wide branches (`table.rs:403-442`); `merge_overflow_is_verbatim_and_never_wraps_or_saturates` and `local_increment_at_u32_ceiling_...` pass; new aggregate-total overflow unit test passes with the verbatim message |
| 8 | Local-path maps equal the pre-change maps and the 1-vs-N maps across k in {21,32,64} x canonical on/off; multi-file CLI output equals the elementwise per-file sum | ✓ VERIFIED | `cargo test --locked --test thread_local_count_tests` re-run → 10 passed, including `one_vs_n_local_maps_are_identical_across_the_matrix`, `old_vs_new_maps_are_identical_across_the_matrix`, and the real-binary `multi_file_local_reduction_matches_per_file_sum` |
| 9 | PyCounter's public API is unchanged and its file methods accumulate through the same local core with `py.detach` and owned Send captures | ✓ VERIFIED | `pyo3/src` diff since `4b61fb9` is empty; extension rebuilt from the fixed tree and installed; `pytest pyo3/tests` → 146 passed, 63 skipped, exit 0 |
| 10 | `total_kmers`, `unique_kmers`, and filtering statistics keep their existing semantics, including the rule that a failed increment does not advance the total | ✓ VERIFIED | Former Gap 1 closed: atomic `fetch_update` + `checked_add` publication (`table.rs:483-487`), no load+store; 16x2000 concurrent regression passes deterministically; independent pre-fix RED `229/2000` reproduced; failed-increment/unique/filtering tests pass. See Gap Closure Verification |
| 11 | For k 1..32 the rolling encoder emits exactly the reference values, order, and skipped counts on the full edge matrix (N at every position, consecutive Ns, lowercase, mixed case, empty/short, record boundaries) | ✓ VERIFIED | `cargo test --locked --test kmer_rolling_differential_tests` → 9 passed; differential compares against the unchanged `encode_kmer_bytes_u128` + `canonical_kmer_u128` |
| 12 | The emitted value is masked to 2k bits, with k=32 using the all-ones mask and no overflowing shift | ✓ VERIFIED | `RollingEncoder::new` mask branch (`encoding.rs:486-491`); `rolling_encoder_rejects_out_of_range_k` asserts `mask() == u64::MAX` at k=32; full k 1..=64 matrix passes |
| 13 | For k 33..64 the existing u128 per-window path is retained and produces the same counts as before | ✓ VERIFIED | Constructor rejects k>32; `count_record_into`/`process_sequence_into_local` route k 33..64 to the unchanged u128 path; k 33/48/64 differentials and real-CLI checks pass |
| 14 | The bit-parallel u64 reverse-complement equals the scalar u128 reverse-complement narrowed to u64 for every k 1..32, including the all-zero/all-ones extremes | ✓ VERIFIED | `bit_parallel_reverse_complement_matches_scalar_u128` passes over every window and every k; out-of-range lengths return 0 without a 64+ shift |
| 15 | CLI and PyO3 counts equal the reference maps on ACGT input and on the N edge matrix, and skipped-window counts match; Python's existing N filtering is unchanged | ✓ VERIFIED | Rust differentials + real-CLI map checks pass; rebuilt-module pytest parity classes pass; pinned parity smoke → `PARITY OK distinct=2400000 total=2400000` |
| 16 | The rolling path is measurably faster than the per-window path on a fixed in-memory corpus in a release build | ✓ VERIFIED | Initial verification executed the release-only ignored timing gate: `windows=260000 ... ratio=0.462` against the 0.75 threshold (recorded 0.452), equal checksums; `src/kmer/encoding.rs` is unchanged by the gap fix |
| 17 | The post-change t1 is strictly lower than the pre-hot-path baseline on the same input and configuration (synthetic and 4M slice) | ✓ VERIFIED | Recorded measurement JSONs unchanged (synthetic 18.77→13.59 s ratio 0.7240; slice 142.54→57.16 s ratio 0.4010, same slice sha); fresh synthetic t1 12.900 s vs pre-change 18.77 s (ratio ~0.687) |
| 18 | All 1-vs-N, old-vs-new, dense-width, golden, local-accumulation, and rolling suites pass on the final tree; pinned parity reports matching nonzero counts with provenance | ✓ VERIFIED | Fresh `cargo test --locked` → 26 suites, 432 passed, 0 failed, 4 ignored, exit 0 (golden 34, golden sha256 5, round-trip 23, dense differential 6, thread-local 10); parity smoke `PARITY OK distinct=2400000 total=2400000` |
| 19 | Both crates pass MSRV 1.82 clippy with warnings denied; the full locked suite and the rebuilt PyO3 module's Python suite pass | ✓ VERIFIED | Forced-rebuild `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` → exit 0 for root (`Checking rustkmer`) and pyo3 (`Compiling rustkmer-pyo3`); full suite above; rebuilt module `pytest pyo3/tests` → 146 passed / 63 skipped |
| 20 | CI and README present the PROF-02 gates as standing, introduce no softener, and the Phase 5 RED baseline is not recaptured or edited | ✓ VERIFIED | No `continue-on-error` / `|| true` in `.github/workflows/benchmark.yml`, `scripts/bench/README.md`, `scripts/bench/thread_scaling.py` (only prose forbidding them); `thread_scaling_baseline.json` sha256 `5d7c4466...` with a single commit; Phase 6 evidence JSONs untouched since 06-04 |

**Score:** 20/20 truths verified (0 present, behavior-unverified)

### Deferred Items

None. The measured peak-RSS increase from per-worker locals (slice t4/t16 25.0/25.1 GiB vs 15.9/15.1 GiB pre-change; synthetic t1 10.15 GiB vs ~8.0 GiB) is recorded in the scaling documents and explicitly assigned to Phase 7's partitioned-memory design — it is not hidden and not a Phase 6 gap.

### Advisory (New Scope, Unevidenced)

None. Re-verification produced no new-scope findings; the single prior blocker is closed with deterministic evidence.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/cli/commands/count.rs` | Lazy resolver, pool built before rayon work, local accumulation, rolling hot loop | ✓ VERIFIED | Resolver at 875-888, `build_global` at 101-104, `count_record_into` rolling/u128 split 387-443, per-file reduce 296; unchanged by gap fix |
| `src/hash/local.rs` | `LocalKmerCounts` + per-thread handle registry | ✓ VERIFIED | Dense/wide maps, verbatim overflow, generation-guarded TLS registry; no stubs |
| `src/hash/table.rs` | Additive local API + checked reduction + atomic aggregate publication | ✓ VERIFIED | `merge_local_counts` now publishes `total_kmers` with `fetch_update` + `checked_add` (483-487), fail-loud overflow preserved (488-499), per-key merges still parallel (542-549); aggregate defect resolved |
| `src/kmer/encoding.rs` | Rolling encoder + bit-parallel u64 revcomp | ✓ VERIFIED | Mask/reset contracts documented and differentially tested; u128 functions untouched |
| `src/kmer/canonical.rs` | Rolling integration / re-export | ✓ VERIFIED | Re-exports `RollingEncoder`; canonical u128 path unchanged |
| `pyo3/src/counter.rs` | File methods through local core, API frozen | ✓ VERIFIED | Empty diff since 06-04; one local per file call, one checked merge; `PyCounterStats.total_kmers` reads the same `KmerCounter` atomic and inherits the fix |
| `tests/thread_pool_size_tests.rs` | Always-run pool-size standing gate | ✓ VERIFIED | 2 passed, asserts observed == requested+1 |
| `tests/thread_local_count_tests.rs` | Local-path exactness proofs + deterministic concurrency regression | ✓ VERIFIED | 10 tests: end-to-end, width, fresh-local, multi-file CLI, 1-vs-N, old-vs-new, overflow, unique/conservation, and `concurrent_local_reduction_never_loses_aggregate_total` (16x2000; independently proven RED pre-fix) |
| `tests/kmer_rolling_differential_tests.rs` | Edge matrix + release timing gate | ✓ VERIFIED | 9 active tests + 1 ignored timing gate (executed and passed at 0.462 in initial verification) |
| `phase6_scaling_green.json`, `phase6_slice_green.json`, `phase6_measurement.json` | Post-change measurement evidence | ✓ VERIFIED | Schema/provenance valid; unchanged since 06-04; fresh gate reproduced GREEN 1.5867/1.9877 with identical counts |
| `phase6_exactness_evidence.json` | Differential/golden/parity results | ✓ VERIFIED | Per-suite counts match the re-run; golden manifest sha matches |
| `phase6_gates_evidence.json` | MSRV/full-suite/dual-surface results | ✓ VERIFIED | Re-run values match (432 passed, 146 pytest passed, clippy 0) |
| `scripts/bench/thread_scaling.py`, `scripts/bench/README.md`, `.github/workflows/benchmark.yml` | Standing-gate procedure and wording | ✓ VERIFIED | No expected-failure wording, no softener; verdict step unconditional |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `resolve_thread_count` | `std::thread::available_parallelism` | lazy fallback | ✓ WIRED | `count.rs:875-888`; no rayon query |
| `execute_count` | `ThreadPoolBuilder::build_global` | before any `par_iter` | ✓ WIRED | `count.rs:101-104`; counting starts later |
| count hot loop | `RollingEncoder` -> `LocalKmerCounts` | k <= 32 branch | ✓ WIRED | `count.rs:398-413` |
| count hot loop | per-window u128 encoder | k 33..64 branch | ✓ WIRED | `count.rs:416-440` |
| worker tasks | per-worker local handle | `try_for_each_init` + TLS registry | ✓ WIRED | `count.rs:462-473`, `local.rs:390-427` |
| per-file reduce | per-key checked `DashMap` sums | `merge_local_counts` | ✓ WIRED | Per-key sums exact; aggregate total published with atomic CAS (no lost updates) |
| `reduce_local_counts` | `merge_local_counts` | `locals.par_iter().try_for_each` | ✓ WIRED | `table.rs:542-549`; parallel reduction preserved by the fix |
| `merge_local_counts` | `KmerCounter.total_kmers` (`AtomicU64`) | `fetch_update` + `checked_add` | ✓ WIRED | `table.rs:483-487`; concurrent deltas compose; overflow returns Err without wrapping |
| concurrent-reduction regression | public `KmerCounter::merge_local_counts` | barrier-synchronized 16 threads x 2000 rounds | ✓ WIRED | `tests/thread_local_count_tests.rs:708`; RED pre-fix (`229/2000`), GREEN post-fix |
| PyCounter file loop | `LocalKmerCounts` -> one merge | `process_sequence_into_local` | ✓ WIRED | `pyo3/src/counter.rs:667-724`, file helpers 758/790 |
| `thread_scaling.py` | `phase6_scaling_green.json` -> t1 comparison | counterbalanced measurement | ✓ WIRED | Fresh gate exits 0 GREEN; counts identical across arms |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| CLI counting | encoded k-mer keys/counts | real FASTQ/FASTA records via rolling/u128 encoders | Yes | ✓ FLOWING (differentials + real-CLI map tests) |
| CLI/`.rkdb` output | count map | shared `DashMap` populated by local reduction | Yes | ✓ FLOWING (parity 2.4M/2.4M; fresh scaling arms 64,999,000/65,000,000) |
| Skip warnings | skipped-window counters | local skip deltas per chunk | Yes | ✓ FLOWING (wording preserved; `Warning: Skipped` present) |
| Scaling verdict | arm medians/counts | `/usr/bin/time` rusage + `.rkdb` stats on real runs | Yes | ✓ FLOWING (fresh re-run GREEN) |
| CLI/PyCounter stats | `total_kmers` | shared atomic published by `merge_local_counts` via `fetch_update` CAS | Yes | ✓ FLOWING (concurrent regression exact every round; overflow fail-loud) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Concurrent reduction regression | `cargo test --locked --test thread_local_count_tests` | 10 passed, 0 failed (includes `concurrent_local_reduction_never_loses_aggregate_total`) | ✓ PASS |
| Regression is non-vacuous (pre-fix RED) | isolated build of `bdb21e6` (pre-fix source) + `cargo test --locked --test thread_local_count_tests concurrent_local_reduction_never_loses_aggregate_total` | `lost rounds=229/2000`, observed `(15, 16)` vs expected 16, exit 101 | ✓ PASS (proves the test fails on the unfixed code) |
| Aggregate overflow contract | `cargo test --locked --lib hash::table` | 18 passed, including `local_reduction_total_overflow_is_fail_loud_and_never_wraps` | ✓ PASS |
| Pool-size standing gate | `cargo test --locked --test thread_pool_size_tests` | 2 passed, 0 ignored | ✓ PASS |
| Full locked suite | `cargo test --locked` | exit 0; 26 suites, 432 passed, 0 failed, 4 ignored | ✓ PASS |
| Thread-scaling gate (fresh) | `python3 scripts/bench/thread_scaling.py --mode synthetic --reads 500000 --reps 3` on rebuilt fixed release binary | `GREEN speedup_t4=1.5867 speedup_t16=1.9877`; all arms 64,999,000 / 65,000,000 | ✓ PASS |
| Pinned parity smoke | `python3 scripts/bench/bench.py --mode synthetic --reads 20000 --parity-only` | `PARITY OK distinct=2400000 total=2400000` | ✓ PASS |
| MSRV clippy root (forced rebuild) | `cargo +1.82.0 clean -p rustkmer` then `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` | `Checking rustkmer`; exit 0 | ✓ PASS |
| MSRV clippy PyO3 (forced rebuild) | `cargo +1.82.0 clean --manifest-path pyo3/Cargo.toml -p rustkmer-pyo3` then clippy with `-D warnings` | `Compiling rustkmer-pyo3`; exit 0 | ✓ PASS |
| Python suite (rebuilt module) | `maturin develop --release` then `.venv311/bin/python -m pytest pyo3/tests -q` | 146 passed, 63 skipped, exit 0 | ✓ PASS |
| Formatting | `rustfmt --check --edition 2021 src/hash/table.rs tests/thread_local_count_tests.rs` | exit 0 | ✓ PASS |
| Concurrent reduction totals (prior harness) | barrier harness calling `merge_local_counts` on 16 threads x 2000 rounds | Prior `lost_rounds=149`; now the in-tree regression passes 2000/2000 | ✓ PASS (defect fixed) |

### Probe Execution

N/A — no `scripts/*/tests/probe-*.sh` exists and no probe was declared in the phase plans/summaries.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| PAR-01 | 06-01, 06-04 | Working `--threads`: pool sized, precedence chain, Python parity | ✓ SATISFIED | Truths 1-5; release observation, standing gate, fresh GREEN scaling, t1 baselines |
| PAR-02 | 06-02, 06-04, 06-05 | Thread-local counters + end reduction; hot-path atomics removed; checked per-key overflow; exact aggregate statistics | ✓ SATISFIED | Truths 6-8 and 10; checked per-key reduction plus atomic CAS aggregate publication; deterministic concurrency regression green with independently reproduced pre-fix RED; overflow fail-loud proven |
| PAR-03 | 06-03, 06-04 | Rolling encoder + bit-parallel revcomp, N/boundary reset, u128 retained | ✓ SATISFIED | Truths 11-16; differential edge matrix and release timing gate |

No orphaned requirements: REQUIREMENTS.md maps exactly PAR-01..03 to Phase 6 and all three appear in plan frontmatter.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX`, no `TODO`/`HACK`/`PLACEHOLDER`, no stub returns, no hardcoded-empty rendering values in any phase-modified file (re-scanned after the gap fix) | — | None |
| `src/hash/local.rs` | 214-216 | Diagnostic skip counter uses `saturating_add` (and `count.rs` uses `saturating_sub` for the per-chunk delta) | ℹ️ Info | Not part of the exact u32 count contract (skipped-window diagnostics only); the CHECKED requirement applies to per-key/u64 count sums, which use `checked_add` |
| `src/hash/table.rs` | 483 | `AtomicU64::fetch_update` is deprecated as of the host nightly 1.101 in favor of `try_update` | ℹ️ Info | Warning-only on newer toolchains; `try_update` does not exist on the CI-pinned MSRV 1.82 clippy toolchain, where `fetch_update` is stable and both clippy gates exit 0. No suppression added; MSRV compatibility requires `fetch_update` |
| `.planning/phases/06-parallelism-correctness-hot-path/deferred-items.md` | 8 | Pre-existing `cargo fmt` drift in `src/database/prefix_cache_merge.rs` (untouched by this phase) | ℹ️ Info | Out of phase scope; both gap-fix files are rustfmt-clean |

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `tests/thread_pool_size_tests.rs` | PAR-01 | 2 | 0 | No | Value (`requested=/observed=`) via external subprocess observer | ✓ PASS |
| `tests/thread_local_count_tests.rs` | PAR-02 | 10 | 0 | No | Value/Behavioral (decoded maps, real-CLI multi-file sum, exact per-round concurrent totals) | ✓ PASS — the prior warning (no deterministic >1 concurrent local merge) is resolved: the new barrier-synchronized regression was independently proven RED pre-fix and GREEN post-fix |
| `tests/kmer_rolling_differential_tests.rs` | PAR-03 | 9 | 1 ignored timing gate (executed and passed at 0.462) | No | Value/Behavioral (ordered emission + skip counts vs unchanged encoder) | ✓ PASS |
| `pyo3/tests/test_counter.py` | PAR-02/PAR-03 | 146 | 63 environment/fixture skips (none requirement-disabling) | No | Value (pure-Python sliding-window reference) | ✓ PASS |

**Disabled tests on requirements:** none (the two Rust ignores are intentional instruments: a run-once D-10 baseline capture and the release-only timing gate, both exercised/documented).
**Circular patterns detected:** none — expected values come from the unchanged u128 reference encoder, a pure-Python reference, the pre-fix RED reproduction, and the real CLI differential.
**Insufficient assertions:** none remaining — the concurrency regression asserts the exact aggregate total and unique count in every one of 2000 rounds, plus the final table contents.

### Decision Coverage

Not evaluated — the decision-coverage gate could not parse the CONTEXT.md decisions block (`reason: could-not-parse`; it uses prose sub-sections rather than `D-NN` entries). Non-blocking; the research-locked decisions were checked manually: lazy fallback + `build_global` ordering, thread-local + checked per-key reduction, atomic aggregate publication, rolling encoder with N/boundary reset and u128 retention, dual-surface inheritance, and the Phase 7/8/9 scope boundary are all honored.

### Human Verification Required

N/A — infrastructure/foundation phase with no user-facing UI. All acceptance criteria are programmatically verifiable and were re-executed; `behavior_unverified` is 0, so no human-UAT item is emitted. The former concurrency defect now has deterministic behavioral evidence (RED pre-fix, GREEN post-fix), so it needs no human judgment.

### Gaps Summary

None. The prior report's single blocker is closed and no regression was introduced.

**Gap 1 (closed) — aggregate `total_kmers` lost under the 06-04 parallel reduction.** `merge_local_counts` now publishes the shared `u64` total with `AtomicU64::fetch_update(Relaxed, Relaxed, checked_add)` instead of a non-atomic load + store. Concurrent merges therefore compose their deltas: the 16-thread x 2000-round regression reports the exact total every round, and an isolated build of the pre-fix tree reports `lost rounds=229/2000` with `(15, 16)` observed, proving the test guards the race. The fail-loud overflow contract is preserved verbatim (no wrap, `unique_kmers` still consistent with the poisoned partial table), per-key u32 sums remain `checked_add`, and `reduce_local_counts` still merges locals in parallel. No emitted counts or `.rkdb` bytes changed: the fresh full suite (432 passed), golden/sha256 tests, parity smoke, and scaling gate (identical 64,999,000 / 65,000,000 counts across arms) confirm it.

Scope guards verified: the gap-fix diff touches exactly `src/hash/table.rs` and `tests/thread_local_count_tests.rs` (plus planning docs); no Phase 7 engine (`src/count/` absent), no Phase 8 output-sort/`.rkdb`-writer change (`format.rs`/`query.rs` untouched), no D2 skip-N change, no counter hasher swap, no dependency/manifest change, public CLI/Python APIs frozen, `.rkdb` v2 counts unchanged. The known peak-RSS increase from per-worker locals remains recorded and assigned to Phase 7.

---

_Verified: 2026-11-12T13:50:05Z_
_Verifier: Claude (gsd-verifier)_
