---
phase: 06-parallelism-correctness-hot-path
verified: 2026-11-14T04:23:21Z
status: passed
score: 20/20 must-haves verified
covered_files: [".github/workflows/benchmark.yml", ".planning/phases/06-parallelism-correctness-hot-path/06-01-PLAN.md", ".planning/phases/06-parallelism-correctness-hot-path/06-01-SUMMARY.md", ".planning/phases/06-parallelism-correctness-hot-path/06-02-PLAN.md", ".planning/phases/06-parallelism-correctness-hot-path/06-02-SUMMARY.md", ".planning/phases/06-parallelism-correctness-hot-path/06-03-PLAN.md", ".planning/phases/06-parallelism-correctness-hot-path/06-03-SUMMARY.md", ".planning/phases/06-parallelism-correctness-hot-path/06-04-PLAN.md", ".planning/phases/06-parallelism-correctness-hot-path/06-04-SUMMARY.md", ".planning/phases/06-parallelism-correctness-hot-path/06-05-PLAN.md", ".planning/phases/06-parallelism-correctness-hot-path/06-05-SUMMARY.md", ".planning/phases/06-parallelism-correctness-hot-path/phase6_exactness_evidence.json", ".planning/phases/06-parallelism-correctness-hot-path/phase6_gates_evidence.json", ".planning/phases/06-parallelism-correctness-hot-path/phase6_measurement.json", ".planning/phases/06-parallelism-correctness-hot-path/phase6_scaling_green.json", ".planning/phases/06-parallelism-correctness-hot-path/phase6_slice_green.json", ".planning/phases/06-parallelism-correctness-hot-path/thread_scaling_par01_green.json", ".planning/phases/06-parallelism-correctness-hot-path/thread_scaling_par01_slice.json", ".planning/research/profiling/verify_threads.py", "pyo3/src/counter.rs", "pyo3/tests/test_counter.py", "scripts/bench/README.md", "scripts/bench/tests/test_verify_threads.py", "scripts/bench/thread_scaling.py", "src/cli/commands/count.rs", "src/hash/local.rs", "src/hash/mod.rs", "src/hash/table.rs", "src/kmer/canonical.rs", "src/kmer/encoding.rs", "tests/kmer_rolling_differential_tests.rs", "tests/thread_local_count_tests.rs", "tests/thread_pool_size_tests.rs"]
covered_digest: "v4:sha256:86d98ed3b4b341824b0df31ede5f64386a568c98b2996b781f783715ec62d6b7"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 20/20
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 6: Parallelism Correctness & Hot Path Verification Report

**Phase Goal:** Thread control actually works and the single-thread hot path is measurably faster while counts stay exactly equal — establishing the true t1 baseline and contention-free accumulation before the engine restructure.
**Verified:** 2026-11-14T04:23:21Z
**Status:** passed
**Re-verification:** Yes — current-tree re-run after Phases 7-10 restructured the counting path (previous report: 2026-11-12, 20/20 passed)

## Re-verification Context (current tree)

The 2026-11-12 report verified the Phase 6 tree. Later phases then changed the code that realizes several Phase 6 truths: Phase 7 moved CLI counting into `src/count/engine.rs` and unified window extraction in `src/kmer/extract.rs`; Phase 9 routed PyO3 counting through the same engine; Phases 9/10 extended the shared harness and test files. The previous `covered_digest` therefore no longer matched the tree. This round re-derived every truth from the current code and re-ran the gates rather than carrying the old evidence forward.

**No new gaps were found.** The phase goal holds on the current tree, and the current implementation is a strict successor of the Phase 6 design. The changes are recorded as supersessions below so the evidence is not misread as "unchanged since Phase 6".

### Supersessions by Later Phases

| Phase 6 truth clause | Superseded by | Current-tree evidence |
| -------------------- | ------------- | --------------------- |
| Truth 1: "observed equals requested plus one" | Phase 7 engine adds N persistent counting workers, so the standing gate is now `2` at N=1 and `2N+1` at N>1 (N rayon workers + N engine workers + main) | `tests/thread_pool_size_tests.rs` asserts 2/9/33 and passes; the rayon pool itself is still built with exactly N (`count.rs:152-155`) |
| Truth 6: "reduces them once per file into the shared counter" | Phase 7's disjoint-partition engine retains per-worker tables and reduces at end-of-run (the ROADMAP SC2 wording); file boundaries reduce checked worker statistics | `engine.rs:884-904` checked ack sums; `engine.rs:935-989` end-of-run `checked_stats_for`; no shared per-window increment or atomic in the hot loop |
| Truth 9: "accumulate through the same local core" | Phase 9 routes `add_from_fasta`/`add_from_fastq` through `CountEngine` and folds tables back with the checked `merge_into` bridge | `pyo3/src/counter.rs:676-687`; public method signatures match the Phase 6 baseline (one additive `PyCounterStats.threads` reader from Phase 9 WR-02) |
| Truth 15: "Python's existing N filtering is unchanged" | Phase 9's D2 decision intentionally replaced Python's strip-and-join pre-filter with the CLI's skip-N semantics | Python parity tests now compare against a pure-Python skip-N reference and pass; the parity intent is preserved and strengthened |
| Truth 17: slice t1 measurement | Not re-measured this round; the recorded 4M-slice artifact is unchanged and valid, and the fresh synthetic t1 is lower still | `phase6_slice_green.json` t1 57.16 s vs pre 142.54 s; fresh synthetic t1 5.57 s vs pre 18.77 s |

## Gap Closure Verification (06-05)

The single prior blocker — aggregate `total_kmers` lost updates under the parallel local reduction — remains fixed on the current tree. `merge_local_counts` publishes the shared total with `AtomicU64::fetch_update(Relaxed, Relaxed, |current| current.checked_add(merged_total))` (`src/hash/table.rs:483-487`); on overflow it returns the verbatim `Total k-mer count overflow during local reduction` error without wrapping and publishes `unique_kmers` to match the poisoned partial table (`:488-499`). Per-key sums remain `checked_add` (`:403-442`), and `reduce_local_counts` still merges drained locals with `locals.par_iter().try_for_each` (`:526-559`). The deterministic regression `concurrent_local_reduction_never_loses_aggregate_total` (16 threads x 2000 barrier-synchronized rounds) is present (`tests/thread_local_count_tests.rs:707-802`) and passes on this tree. The pre-fix RED reproduction (`lost rounds=229/2000` in the prior round) was not re-executed; it remains historical evidence that the test is not vacuous.

## Goal Achievement

Verification was performed goal-backward against the current codebase, and the mechanically checkable claims were re-executed: the MSRV 1.82 clippy gates on both crates (forced rebuilds), the full locked Rust suite, the 571-test Python harness suite, the rebuilt PyO3 module's pytest suite, the pool-size standing gate and a live thread observation, the synthetic thread-scaling gate on a freshly built release binary, the release-only rolling-encoder timing gate, and the pinned parity smoke. SUMMARY.md claims were not used as evidence.

### Observable Truths

| # | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | `--threads N` sizes the ACTUAL rayon pool: fresh CLI children at N in {1,4,16} observe exactly N workers plus main | ✓ VERIFIED | `build_global(resolved_threads)` at `src/cli/commands/count.rs:152-155`; `tests/thread_pool_size_tests.rs` → 2 passed; live `verify_threads.py` → `(1,2) (4,9) (16,33)`, `THREAD REALITY verdict=GREEN`, exit 0. Phase 7 adds N persistent engine workers, so the standing gate's total is 2N+1 while the rayon pool remains exactly N |
| 2 | Precedence `--threads > RUSTKMER_THREADS > RAYON_NUM_THREADS > all cores` unchanged; Python `threads=` / IN-04 warn semantics preserved | ✓ VERIFIED | Pure resolver `resolve_thread_count_from` + env wrapper at `count.rs:551-600`; its 7 unit tests pass in the full suite; PyO3 `new` rejects `threads < 1` and logs `build_global` failures at warn (`pyo3/src/counter.rs:169-218`); public signature unchanged |
| 3 | No rayon pool-size query or parallel operation before `build_global(resolved)`; the all-cores fallback is lazy | ✓ VERIFIED | `count.rs:152-155` runs before `CountEngine::new` (`:192`) and before the file loop; the fallback uses `std::thread::available_parallelism()` (`:596`), never a rayon query; no `current_num_threads` in the count path or engine |
| 4 | Thread-scaling gate GREEN with `speedup_t4` and `speedup_t16` >= 1.3 and identical nonzero counts | ✓ VERIFIED | Fresh run on the rebuilt current release binary: t1/t4/t16 medians 5.570 / 2.080 / 1.780 s; `speedup_t4=2.6778846153846154`, `speedup_t16=3.1292134831460676`; every arm `unique=64999000 total=65000000`; verdict `GREEN`; exit 0; provenance binary sha `f6ace9f70644…`, commit `698522d415a4…` |
| 5 | A true single-thread baseline is recorded with provenance; the slice arm runs whenever the documented input resolves | ✓ VERIFIED | `thread_scaling_par01_green.json` (synthetic t1 18.77 s) and `thread_scaling_par01_slice.json` (4M-slice t1 142.54 s, pinned counts 229,694,874 / 519,271,168) are schema/provenance valid and unchanged since 06-04; the named real input resolves on this host; the fresh gate reproduced synthetic t1 5.570 s |
| 6 | CLI file counting accumulates in per-worker thread-local tables and reduces once per file; the hot loop has no shared per-window increment or atomic fetch-add | ✓ VERIFIED | `CountEngine` gives each worker a disjoint contiguous range of `LocalKmerCounts` (`engine.rs:650-700`, `partition.rs`); the producer only routes keys into per-partition buffers; workers call `LocalKmerCounts::increment` (`engine.rs:1298-1330`); no `fetch_add` or shared `counter.increment` in the engine hot loop; file boundaries flush and reduce checked worker statistics (`engine.rs:884-904`). Phase 7 superseded the literal per-file shared-counter merge with end-of-run tables, preserving the no-shared-per-window-atomic contract |
| 7 | The end reduction adds per-key u32 counts with checked arithmetic and returns the verbatim fail-loud overflow message; never wraps or saturates | ✓ VERIFIED | Per-key `checked_add` retained in both dense/wide branches (`table.rs:403-442`); `LocalKmerCounts::increment` checks total, unique, and `u32::MAX` before mutating (`local.rs:152-207`); engine aggregate sums use `checked_sum` (`engine.rs:108-165`); `merge_overflow_is_verbatim_and_never_wraps_or_saturates`, `local_increment_at_u32_ceiling_…`, and `local_reduction_total_overflow_…` all pass |
| 8 | Local-path maps equal the pre-change maps and the 1-vs-N maps across k in {21,32,64} x canonical on/off; multi-file CLI output equals the elementwise per-file sum | ✓ VERIFIED | `cargo test --test thread_local_count_tests` → 10 passed, including `one_vs_n_local_maps_are_identical_across_the_matrix`, `old_vs_new_maps_are_identical_across_the_matrix`, and the real-CLI `multi_file_local_reduction_matches_per_file_sum` (which now runs through the engine) |
| 9 | PyCounter's public API is unchanged and its file methods accumulate through the same local core with `py.detach` and owned Send captures | ✓ VERIFIED | Method signatures diffed against the Phase 6 baseline `4b61fb9`: identical except an additive `PyCounterStats.threads` reader (Phase 9 WR-02); `add_from_fasta`/`add_from_fastq` call `count_file_into_counter` inside `py.detach` with owned `Arc`/`String`/kind/threads captures (`pyo3/src/counter.rs:367-452, 676-687`), which counts through `CountEngine`'s `LocalKmerCounts` and folds back with checked `merge_into`; rebuilt module pytest → 179 passed, 63 skipped, exit 0 |
| 10 | `total_kmers`, `unique_kmers`, and filtering statistics keep their existing semantics, including the rule that a failed increment does not advance the total | ✓ VERIFIED | `LocalKmerCounts::increment` computes the new total before mutating and advances it only on success (`local.rs:152-207`); CLI stats come from `checked_stats_for` over the partition tables (`engine.rs:130-141, 935-989`); filtering uses the WR-01 denominator (`engine.rs:462-486`); the aggregate CAS publication and the 16x2000 concurrent regression pass; failed-increment/unique/filtering tests pass |
| 11 | For k 1..32 the rolling encoder emits exactly the reference values, order, and skipped counts on the full edge matrix (N at every position, consecutive Ns, lowercase, mixed case, empty/short, record boundaries) | ✓ VERIFIED | `cargo test --test kmer_rolling_differential_tests` → 9 passed; the differential compares against the unchanged `encode_kmer_bytes_u128` + `canonical_kmer_u128`; `full_edge_matrix_matches_reference_for_k_1_through_64` covers N at every position, consecutive runs, lowercase/mixed case, empty/short, and record-boundary pairs |
| 12 | The emitted value is masked to 2k bits, with k=32 using the all-ones mask and no overflowing shift | ✓ VERIFIED | `RollingEncoder::new` mask branch (`encoding.rs:486-491`); `rolling_encoder_rejects_out_of_range_k` asserts `mask() == u64::MAX` at k=32; the full k 1..=64 matrix passes |
| 13 | For k 33..64 the existing u128 per-window path is retained and produces the same counts as before | ✓ VERIFIED | `RollingEncoder::new` rejects k>32; `for_each_window` routes k 33..=64 to `encode_kmer_bytes_u128` + `canonical_kmer_u128` (`extract.rs:117-147`); k 33/48/64 differentials and real-CLI checks pass |
| 14 | The bit-parallel u64 reverse-complement equals the scalar u128 reverse-complement narrowed to u64 for every k 1..32, including the all-zero/all-ones extremes | ✓ VERIFIED | `reverse_complement_u64` (`encoding.rs:388-398`); `bit_parallel_reverse_complement_matches_scalar_u128` passes over every window and every k, plus both extremes; out-of-range lengths return 0 without a 64+ shift. The rolling hot path maintains the reverse value incrementally and is differentially proven against the same reference |
| 15 | CLI and PyO3 counts equal the reference maps on ACGT input and on the N edge matrix, and skipped-window counts match; Python's existing N filtering is unchanged | ✓ VERIFIED | Rust edge-matrix/local-accumulator/window-extractor differentials pass; Python parity classes compare file and sequence paths against a pure-Python skip-N reference (`pyo3/tests/test_counter.py:1116-1445`) and pass; pinned parity smoke → `PARITY OK distinct=2400000 total=2400000`. The "Python's existing N filtering is unchanged" clause was intentionally superseded by Phase 9's D2 skip-N unification (Python now matches the CLI); the parity intent holds |
| 16 | The rolling path is measurably faster than the per-window path on a fixed in-memory corpus in a release build | ✓ VERIFIED | Fresh release-only ignored gate: `windows=260000 per_window=3.203833ms rolling=1.73125ms ratio=0.540` against the 0.75 threshold; checksums equal; exit 0. `src/kmer/encoding.rs` is unchanged since Phase 6 |
| 17 | The post-change t1 is strictly lower than the pre-hot-path baseline on the same input and configuration (synthetic and 4M slice) | ✓ VERIFIED | Fresh synthetic t1 5.570 s vs the recorded pre baseline 18.77 s (ratio ≈ 0.297); the recorded 4M-slice artifact is unchanged and shows 57.16 s vs 142.54 s (ratio 0.401, same slice sha). The slice arm was not re-measured this round; the synthetic arm is fresh and the current engine is strictly faster |
| 18 | All 1-vs-N, old-vs-new, dense-width, golden, local-accumulation, and rolling suites pass on the final tree; pinned parity reports matching nonzero counts with provenance | ✓ VERIFIED | Fresh `cargo test --locked` → 32 suites, 508 passed, 0 failed, 4 ignored, exit 0 (golden 34, golden sha256 5, round-trip 23, dense differential 6, thread-local 10, rolling 9, engine 20, output matrix 3); Python harness → 571 tests, `OK (skipped=1)`; parity smoke `PARITY OK distinct=2400000 total=2400000` |
| 19 | Both crates pass MSRV 1.82 clippy with warnings denied; the full locked suite and the rebuilt PyO3 module's Python suite pass | ✓ VERIFIED | Forced-rebuild `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` → exit 0 for root (`Checking rustkmer`) and pyo3 (`Compiling rustkmer-pyo3`); full suite above; `.venv313` `maturin develop --release` rebuilt against CPython 3.13, then pytest → 179 passed, 63 skipped |
| 20 | CI and README present the PROF-02 gates as standing, introduce no softener, and the Phase 5 RED baseline is not recaptured or edited | ✓ VERIFIED | No `continue-on-error` / `|| true` in `.github/workflows/benchmark.yml`, `scripts/bench/README.md`, `scripts/bench/thread_scaling.py` (only prose forbidding them); `thread_scaling_baseline.json` sha256 `5d7c4466…` with a single commit; Phase 6 evidence JSONs unchanged since 06-04 |

**Score:** 20/20 truths verified (0 present, behavior-unverified)

### Deferred Items

None. The measured peak-RSS increase from per-worker locals recorded in Phase 6 was explicitly assigned to Phase 7's partitioned-memory design; it is not a Phase 6 gap.

### Advisory (New Scope, Unevidenced)

None. This re-verification produced no new-scope findings.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/cli/commands/count.rs` | Lazy resolver, pool built before rayon work, engine dispatch | ✓ VERIFIED | Resolver/`build_global` at 152-155 and 551-600; all counting now delegates to `CountEngine` (Phase 7), which preserves the ordering contract |
| `src/hash/local.rs` | `LocalKmerCounts` + per-thread handle registry | ✓ VERIFIED | Dense/wide maps, checked totals, verbatim overflow, generation-guarded TLS registry; the engine consumes the same type directly |
| `src/hash/table.rs` | Additive local API + checked reduction + atomic aggregate publication | ✓ VERIFIED | `merge_local_counts` uses per-key `checked_add` and `fetch_update` CAS publication (483-487); fail-loud overflow preserved; parallel reduction intact |
| `src/kmer/encoding.rs` | Rolling encoder + bit-parallel u64 revcomp | ✓ VERIFIED | Mask/reset contracts documented and differentially tested; u128 functions untouched |
| `src/kmer/canonical.rs` | Rolling integration / re-export | ✓ VERIFIED | Re-exports `RollingEncoder`; canonical u128 path unchanged |
| `pyo3/src/counter.rs` | File methods through the shared counting core, API frozen | ✓ VERIFIED | Uses `CountEngine` + `merge_into` inside `py.detach`; signatures match the Phase 6 baseline plus one additive stats reader |
| `tests/thread_pool_size_tests.rs` | Always-run pool-size standing gate | ✓ VERIFIED | 2 passed; asserts the Phase 7 `2N+1` engine formula on N=1/4/16 |
| `tests/thread_local_count_tests.rs` | Local-path exactness proofs + deterministic concurrency regression | ✓ VERIFIED | 10 passed, including 1-vs-N, old-vs-new, real-CLI multi-file, overflow, and `concurrent_local_reduction_never_loses_aggregate_total` |
| `tests/kmer_rolling_differential_tests.rs` | Edge matrix + release timing gate | ✓ VERIFIED | 9 active tests + 1 ignored timing gate, executed this round and passed at ratio 0.540 |
| Current-tree successors (Phase 7, realizing the same truths) | Shared engine + unified extractor | ✓ VERIFIED | `src/count/engine.rs`, `src/count/partition.rs`, `src/kmer/extract.rs`, `tests/count_engine_tests.rs` (20 passed), `tests/window_extract_differential_tests.rs` (9 passed); no debt markers or stubs |
| `phase6_scaling_green.json`, `phase6_slice_green.json`, `phase6_measurement.json` | Post-change measurement evidence | ✓ VERIFIED | Schema/provenance valid; unchanged since 06-04; a fresh current-tree gate reproduces GREEN 2.678/3.129 with identical counts |
| `phase6_exactness_evidence.json` | Differential/golden/parity results | ✓ VERIFIED | Per-suite evidence valid; the fresh full suite and parity smoke match the recorded pattern |
| `phase6_gates_evidence.json` | MSRV/full-suite/dual-surface results | ✓ VERIFIED | Fresh values are larger (508 Rust / 179 pytest) because Phases 7-10 added tests; the gate outcomes match |
| `scripts/bench/thread_scaling.py`, `scripts/bench/README.md`, `.github/workflows/benchmark.yml` | Standing-gate procedure and wording | ✓ VERIFIED | No expected-failure wording, no softener; verdict step unconditional |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `resolve_thread_count` | `std::thread::available_parallelism` | lazy fallback | ✓ WIRED | `count.rs:587-600`; never a rayon query |
| `execute_count` | `ThreadPoolBuilder::build_global` | before any rayon work | ✓ WIRED | `count.rs:152-155`; engine construction and counting start later |
| count hot loop | `for_each_window` -> `RollingEncoder` / u128 reference | one shared extractor | ✓ WIRED | `count.rs:247` -> `engine.rs:992-1031` -> `extract.rs:103-147` |
| worker tasks | per-worker disjoint partition tables | `PartitionLayout::worker_range` | ✓ WIRED | `engine.rs:650-700`; each key has exactly one partition |
| per-file flush | checked acknowledgement sums | `flush_pipeline` / `reduce_worker_stats` | ✓ WIRED | `engine.rs:884-904, 148-165`; `checked_add` fail-loud messages |
| end-of-run reduction | `checked_stats_for` over tables | `finish` | ✓ WIRED | `engine.rs:935-989`; totals/uniques are checked sums |
| `reduce_local_counts` | `merge_local_counts` | `locals.par_iter().try_for_each` | ✓ WIRED | `table.rs:526-559`; parallel per-key reduction preserved |
| `merge_local_counts` | `KmerCounter.total_kmers` (`AtomicU64`) | `fetch_update` + `checked_add` | ✓ WIRED | `table.rs:483-487`; concurrent deltas compose; overflow returns Err without wrapping |
| concurrent-reduction regression | public `KmerCounter::merge_local_counts` | barrier-synchronized 16 threads x 2000 rounds | ✓ WIRED | `tests/thread_local_count_tests.rs:707-802`; passes on this tree |
| PyCounter file loop | `CountEngine` -> checked `merge_into` | `count_file_into_counter` inside `py.detach` | ✓ WIRED | `pyo3/src/counter.rs:676-687`; owned Send captures |
| `thread_scaling.py` | current release binary -> GREEN verdict | counterbalanced measurement | ✓ WIRED | Fresh gate exits 0 GREEN; counts identical across arms |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| CLI counting | encoded k-mer keys/counts | real FASTQ/FASTA records via the shared extractor (`RollingEncoder` k<=32, u128 path k>32) | Yes | ✓ FLOWING (differentials + real-CLI map tests) |
| CLI/`.rkdb` output | count map | disjoint partition tables populated by the engine | Yes | ✓ FLOWING (parity 2.4M/2.4M; fresh scaling arms 64,999,000/65,000,000) |
| Skip warnings | skipped-window counters | per-record `WindowSummary` deltas | Yes | ✓ FLOWING (wording preserved; `Warning: Skipped` present) |
| Scaling verdict | arm medians/counts | `/usr/bin/time` rusage + `.rkdb` stats on real runs | Yes | ✓ FLOWING (fresh re-run GREEN) |
| CLI/PyCounter stats | `total_kmers` / `unique_kmers` | checked table sums (CLI) or the CAS-published `KmerCounter` atomics (PyO3 bridge) | Yes | ✓ FLOWING (concurrent regression exact every round; overflow fail-loud) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Pool-size standing gate | `cargo test --locked --test thread_pool_size_tests` (via full suite) | 2 passed, 0 ignored | ✓ PASS |
| Live thread reality | `python3 .planning/research/profiling/verify_threads.py --binary target/release/rustkmer --input scripts/bench/scratch/poolcheck.fq --build-profile release --threads 1 4 16` | `(1,2) (4,9) (16,33)`, `verdict=GREEN`, exit 0 | ✓ PASS |
| Local-path exactness + concurrency regression | `cargo test --locked --test thread_local_count_tests` | 10 passed, 0 failed | ✓ PASS |
| Rolling differential edge matrix | `cargo test --locked --test kmer_rolling_differential_tests` | 9 passed, 1 ignored (timing gate) | ✓ PASS |
| Rolling release timing gate | `cargo test --locked --release --test kmer_rolling_differential_tests rolling_path_is_at_most_three_quarters_of_per_window_time -- --ignored --exact --nocapture` | `windows=260000 … ratio=0.540`; checksums equal; 1 passed | ✓ PASS |
| Full locked suite | `cargo test --locked` | exit 0; 32 suites, 508 passed, 0 failed, 4 ignored | ✓ PASS |
| MSRV clippy root (forced rebuild) | `cargo +1.82.0 clean -p rustkmer` then `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` | `Checking rustkmer`; exit 0 | ✓ PASS |
| MSRV clippy PyO3 (forced rebuild) | `cargo +1.82.0 clean --manifest-path pyo3/Cargo.toml -p rustkmer-pyo3` then clippy with `-D warnings` | `Compiling rustkmer-pyo3`; exit 0 | ✓ PASS |
| Python harness suite | `python3 -m unittest discover -s scripts/bench/tests -t .` | `Ran 571 tests … OK (skipped=1)`, exit 0; one later verbose rerun hit the known macOS sampling flake, and the permitted isolated rerun passed (`1 test … OK`) | ✓ PASS |
| Python suite (rebuilt module) | `.venv313` `maturin develop --release` (CPython 3.13) then `.venv313/bin/python -m pytest pyo3/tests -q` | 179 passed, 63 skipped, exit 0 | ✓ PASS |
| Thread-scaling gate (fresh, current tree) | `python3 scripts/bench/thread_scaling.py --mode synthetic --reads 500000 --reps 3` on a rebuilt release binary | `GREEN speedup_t4=2.6779 speedup_t16=3.1292`; every arm 64,999,000 / 65,000,000; exit 0 | ✓ PASS |
| Pinned parity smoke | `python3 scripts/bench/bench.py --mode synthetic --reads 20000 --parity-only` | `PARITY OK distinct=2400000 total=2400000`, exit 0 | ✓ PASS |
| Release build | `cargo build --release --locked` | exit 0; one host-nightly deprecation warning (`fetch_update`), see Anti-Patterns | ✓ PASS |
| Formatting (Phase 6 files) | `rustfmt --check --edition 2021` on the covered Rust files | `src/cli/commands/count.rs` has 3 later-phase formatting diffs; the other Phase 6 files are clean | ℹ️ INFO (later-phase code, not a Phase 6 contract) |

### Probe Execution

N/A — no `scripts/*/tests/probe-*.sh` exists and no probe was declared in the phase plans/summaries.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| PAR-01 | 06-01, 06-04 | Working `--threads`: pool sized, precedence chain, Python parity | ✓ SATISFIED | Truths 1-5; live observation, standing gate, fresh GREEN scaling, recorded t1 baselines |
| PAR-02 | 06-02, 06-04, 06-05 | Thread-local counters + end reduction; hot-path atomics removed; checked per-key overflow; exact aggregate statistics | ✓ SATISFIED | Truths 6-8 and 10; disjoint partition locals, checked reduction, CAS aggregate publication, deterministic concurrency regression, overflow fail-loud |
| PAR-03 | 06-03, 06-04 | Rolling encoder + bit-parallel revcomp, N/boundary reset, u128 retained | ✓ SATISFIED | Truths 11-16; differential edge matrix, release timing gate, parity |

No orphaned requirements: REQUIREMENTS.md maps exactly PAR-01..03 to Phase 6 and all three appear in plan frontmatter.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX`, no `TODO`/`HACK`/`PLACEHOLDER`, no stub returns in any covered file or in the current-tree engine/extractor | — | None |
| `src/hash/local.rs` | 214-216 | Diagnostic skip counter uses `saturating_add` | ℹ️ Info | Not part of the exact u32 count contract (skipped-window diagnostics only); per-key/u64 count sums use `checked_add` |
| `src/hash/table.rs` | 483 | `AtomicU64::fetch_update` is deprecated as of the host nightly 1.101 (`try_update`) | ℹ️ Info | Warning-only on newer toolchains; `try_update` does not exist on the CI-pinned MSRV 1.82, where both clippy gates exit 0. No suppression added; MSRV compatibility requires `fetch_update` |
| `src/cli/commands/count.rs` | 289-… | `rustfmt --check` reports 3 formatting diffs introduced by the Phase 8 output pipeline | ℹ️ Info | Style-only; MSRV clippy on both crates is clean and no Phase 6 file is affected |

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `tests/thread_pool_size_tests.rs` | PAR-01 | 2 | 0 | No | Value (`requested=/observed=`) via external subprocess observer | ✓ PASS |
| `tests/thread_local_count_tests.rs` | PAR-02 | 10 | 0 | No | Value/Behavioral (decoded maps, real-CLI multi-file sum, exact per-round concurrent totals) | ✓ PASS — the prior warning (no deterministic >1 concurrent local merge) remains resolved by the barrier-synchronized regression |
| `tests/kmer_rolling_differential_tests.rs` | PAR-03 | 9 | 1 ignored timing gate (executed this round at ratio 0.540) | No | Value/Behavioral (ordered emission + skip counts vs the unchanged encoder) | ✓ PASS |
| `tests/window_extract_differential_tests.rs` | PAR-03/PAR-02 | 9 | 0 | No | Value (extractor vs reference for k 1..64, N runs, boundaries) | ✓ PASS |
| `pyo3/tests/test_counter.py` | PAR-02/PAR-03 | 179 | 63 environment/fixture skips (none requirement-disabling) | No | Value (pure-Python skip-N reference; anti-softening guards) | ✓ PASS |

**Disabled tests on requirements:** none (the two Rust ignores are intentional instruments: a run-once D-10 baseline capture and the release-only timing gate, both exercised/documented).
**Circular patterns detected:** none — expected values come from the unchanged u128 reference encoder, pure-Python reference maps, the pre-fix RED reproduction (historical), and the real CLI differential.
**Insufficient assertions:** none — the concurrency regression asserts the exact aggregate total and unique count in every one of 2000 rounds, plus the final table contents.

### Decision Coverage

Not evaluated — the decision-coverage gate could not parse the CONTEXT.md decisions block (`reason: could-not-parse`; it uses prose sub-sections rather than `D-NN` entries). Non-blocking; the research-locked decisions were checked manually: lazy `available_parallelism` fallback + `build_global` ordering, thread-local/disjoint accumulation with checked reduction, atomic aggregate publication, rolling encoder with N/boundary reset and u128 retention, dual-surface inheritance, and the Phase 7/8/9 scope boundary are all honored.

### Human Verification Required

N/A — infrastructure/foundation phase with no user-facing UI. All acceptance criteria are programmatically verifiable and were re-executed; `behavior_unverified` is 0, so no human-UAT item is emitted. The concurrency and timing invariants have deterministic behavioral evidence (the 16x2000 regression, the scaling gate, and the release timing gate).

### Gaps Summary

None. No must-have failed on the current tree and no regression was introduced by Phases 7-10. The prior gap (aggregate `total_kmers` lost under the parallel local reduction) remains fixed with an atomic CAS publication and a passing deterministic regression. The changes observed against the 2026-11-12 report are implementation supersessions (shared engine, unified extractor, PyO3 engine routing, D2 skip-N), not defects; each is listed in "Supersessions by Later Phases".

---

_Verified: 2026-11-14T04:23:21Z_
_Verifier: Claude (gsd-verifier)_
