---
phase: 07-shared-counting-engine
verified: 2026-11-12T16:17:11Z
status: passed
score: 12/12 must-haves verified
covered_files:
  - .planning/phases/07-shared-counting-engine/07-01-PLAN.md
  - .planning/phases/07-shared-counting-engine/07-01-SUMMARY.md
  - .planning/phases/07-shared-counting-engine/07-02-PLAN.md
  - .planning/phases/07-shared-counting-engine/07-02-SUMMARY.md
  - .planning/phases/07-shared-counting-engine/07-03-PLAN.md
  - .planning/phases/07-shared-counting-engine/07-03-SUMMARY.md
  - .planning/phases/07-shared-counting-engine/07-04-PLAN.md
  - .planning/phases/07-shared-counting-engine/07-04-SUMMARY.md
  - .planning/phases/07-shared-counting-engine/phase7_engine_split.json
  - .planning/phases/07-shared-counting-engine/phase7_gates_evidence.json
  - .planning/phases/07-shared-counting-engine/phase7_measurement.json
  - .planning/phases/07-shared-counting-engine/phase7_pyo3_evidence.json
  - .planning/phases/07-shared-counting-engine/phase7_scaling_green.json
  - .planning/phases/07-shared-counting-engine/phase7_slice_green.json
  - .planning/research/profiling/verify_threads.py
  - examples/engine_probe.rs
  - pyo3/src/counter.rs
  - pyo3/tests/test_counter.py
  - scripts/bench/tests/test_verify_threads.py
  - src/cli/commands/count.rs
  - src/core/mod.rs
  - src/core/monitoring.rs
  - src/count/batch.rs
  - src/count/engine.rs
  - src/count/mod.rs
  - src/count/partition.rs
  - src/hash/local.rs
  - src/kmer/extract.rs
  - src/kmer/mod.rs
  - src/lib.rs
  - tests/count_engine_tests.rs
  - tests/thread_pool_size_tests.rs
  - tests/window_extract_differential_tests.rs
covered_digest: "v4:sha256:3310a1d32af23ca77037023f5f5f2758a71426543c05e15a7c5fb127239155c0"
behavior_unverified: 0
overrides_applied: 0
deferred:
  - truth: "PyCounter::add_from_* counts through the shared engine (ENGINE-01 dual-surface half)"
    addressed_in: "Phase 9"
    evidence: "ROADMAP Phase 7 Note: the ENGINE-01/ENGINE-03 dual-surface contract completes in Phase 9; CONTEXT dual-surface decision leaves the PyCounter wiring to Phase 9"
  - truth: "Python D2 skip-N semantic change (PY-02)"
    addressed_in: "Phase 9"
    evidence: "ROADMAP Phase 9 success criterion 3; CONTEXT D2: Python keeps its N pre-filter in Phase 7"
  - truth: "Unstable/parallel output sort and Phase-5-golden .rkdb byte-identity proof (OUT-01/OUT-02)"
    addressed_in: "Phase 8"
    evidence: "ROADMAP Phase 8 success criteria 1-2; the slice output-stage variance is explicitly recorded for Phase 8"
---

# Phase 7: Shared Counting Engine Verification Report

**Phase Goal:** CLI counting runs through one shared engine — persistent workers, disjoint partitioned tables, overlapped producer/consumer I/O — recovering the measured ~3.5x parallel-scaling deficit, with Python inheritance structural rather than accidental.
**Verified:** 2026-11-12T16:17:11Z (UTC; local 2026-11-13)
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ONE counting entry point `src/count/engine.rs` exists and CLI counting runs through it | ✓ VERIFIED | `src/count/engine.rs:518` (`pub struct CountEngine`); `src/cli/commands/count.rs:190-191` builds one `CountEngine` for every resolved thread count and `:245` counts every file through `engine.count_file`; `grep -n "par_chunks\|try_for_each_init\|CHUNK_SIZE\|SUBSLICE_RECORDS\|CountOutput" src/cli/commands/count.rs` → no match (exit 1) |
| 2 | Fixed rayon pool built before any rayon query; producer streams records into bounded per-worker queues; N persistent workers count into disjoint hash-range-partitioned thread-local tables; decompression overlaps counting; no per-chunk fork-join barrier; `--threads 1` is true sequential | ✓ VERIFIED | `count.rs:150-153` `build_global` before `CountEngine::new`; no rayon in the counting path (`engine.rs` uses rayon only in `merge_into`); `engine.rs:658-662` spawns exactly N named `rustkmer-count-{i}` threads with `sync_channel(queue_batches=8)`; `partition.rs:111-118,152-157` disjoint contiguous ranges; `engine.rs:565-583` sequential path has no queue/worker. Live observer: requested=1→2, 4→9, 16→33 OS threads, GREEN. Probe: t4 wall 6.518 s with 4 workers busy 4.72-4.75 s each *inside* the producer's 6.518 s (overlap proven arithmetically); t16 wall 6.439 s, 16 workers 1.20-1.25 s |
| 3 | PROF-02 thread-scaling gate GREEN after the engine: speedups ≥ 1.3, identical nonzero counts across arms, synthetic walls strictly below the Phase 6 baseline | ✓ VERIFIED | Recorded: `phase7_scaling_green.json` verdict GREEN speedup_t4=1.5697 speedup_t16=1.605; counts 64,999,000/65,000,000 in every arm; medians 6.42/4.09/4.00 s vs Phase 6 13.59/8.32/6.74 s. Independent re-run on the identical deterministic input (sha256 `bd64b2c1…`): 6.320/3.940/3.810 s, verdict GREEN speedup_t4=1.6041 speedup_t16=1.6588, same counts, exit 0 |
| 4 | Real 4M-read slice: pinned Distinct 229,694,874 / Total 519,271,168 in every arm before any timing; t1/t4/t16 medians strictly below Phase 6 (57.16/34.98/26.96 s); t16 peak RSS ≤ 26,952,056,832 B; provenance on the artifact | ✓ VERIFIED | `phase7_slice_green.json`: every arm 229,694,874/519,271,168; 36.92/17.76/23.83 s; RSS 17,958,944,768 / 17,966,088,192 / 17,968,676,864 B; provenance binary sha256 `d107d17e…` + commit `aeabb4b…`. Independent re-run (same input path, same `slice_reads=4,000,000`, re-provisioned slice fingerprint `71c6264b…` identical): 37.95/17.63/17.64 s, same pinned counts, RSS 17.96 GB, below the Phase 6 t16 bound |
| 5 | Sorted `.rkdb` outputs are byte-identical at t1/t4/t16 (one sha256) | ✓ VERIFIED | Recorded slice sha256 `0976f29c5edeaa5eb49218e2c2fd5ff84f09109c3f2aac9d83bc8cf8c8668014` at t1/t4/t16. Independent slice re-run produced the same three files: all `0976f29c…` (byte-for-byte equal to the recorded evidence). Fixture re-run (100k reads): t1/t4/t16 `.rkdb` all `065c815e…`, text all `debee64c…`. `t1_t4_t16_maps_and_rkdb_sha256_are_identical` green |
| 6 | Producer/worker split measured under the `profiling` feature without changing default builds or the measured release binary | ✓ VERIFIED | `EngineDiagnostics`/`WorkerDiagnostics` are `#[cfg(feature = "profiling")]` only (`engine.rs:173-221,350-353`); probe `target/release/examples/engine_probe` sha256 `1038a224…` matches the evidence and was re-run: t1 `workers=[]` wall=producer=469,173,292 ns; t4 4 workers × 800 batches; t16 16 workers × 200 batches; producer ≈ wall. Rebuilt default release binary `d107d17e7bc60846dbf886727ed656500d189ec32102fa7704f283068a3e35cf` — byte-identical to the measured artifact, so the timers are compiled out |
| 7 | ONE core window extractor (`for_each_window`) implements the D2 skip-N semantics and both surfaces route through it; no duplicate extraction logic remains | ✓ VERIFIED | `src/kmer/extract.rs:90-148`; call sites `src/count/engine.rs:958,975` and `pyo3/src/counter.rs:309,677`; `grep -rn "RollingEncoder::" src/cli/commands/count.rs src/count/engine.rs pyo3/src/counter.rs` → no match; `grep -rn "for i in 0..=(" …` → no match; differential suite 9/9 passed (k 1..=64, canonical on/off, lowercase, N at every position, runs, boundaries, empty/short, sink error) |
| 8 | MultiGzDecoder multi-member gzip regression (v1.0 8102985) stays green; engine gzip behavior is complete and loud on trailing garbage | ✓ VERIFIED | `src/io/fastq.rs:639` `test_read_all_sequences_concatenated_gzip_members` (two members, 5 records) green in the full suite; `multi_member_gzip_counts_every_member_at_t1_and_t4` and `trailing_garbage_fails_loudly_with_file_context` green; `DefaultCompressedFileReader` still uses `flate2::read::MultiGzDecoder` (`fastq.rs:78`) |
| 9 | Exact counts survive partitioning: disjointness + conservation property tests green, and the slice parity gate passes the pinned counts | ✓ VERIFIED | `count_engine_tests` 20/20 green including `partition_disjointness_and_conservation_hold` and `proptest_partition_disjointness_and_conservation` (k 1..=64 × canonical, worker pipeline); slice parity pinned in every recorded and re-run arm |
| 10 | Every new summation site fails loud with checked arithmetic, and the per-key u32 overflow keeps the verbatim contract message | ✓ VERIFIED | `checked_sum_fails_loud_on_total_overflow`, `checked_sum_fails_loud_on_exact_max_plus_one`, `reduce_worker_stats_fails_loud_on_aggregate_overflow`, `merge_into_preserves_verbatim_per_key_overflow`, `worker_overflow_returns_verbatim_error_without_hanging` all passed; messages `Total/Unique k-mer count overflow during local reduction` and `K-mer count overflow reached maximum value 4294967295` verbatim |
| 11 | CLI behavior at the engine/legacy boundary is preserved: N-read skip semantics, multi-file cumulative stats, one warning per 4096-record batch with pinned wording, text/binary ordering, `-L/-U` filters, `--no-sort` contents | ✓ VERIFIED | `n_containing_reads_match_skip_n_reference`, `multi_file_stats_and_warnings_are_preserved`, `text_and_binary_output_order_is_unchanged`, `count_filters_are_unchanged`, `no_sort_still_writes_the_same_set` all green; warning wording at `count.rs:258`; text maps equal t1/t4/t16 on the 100k fixture |
| 12 | Standing gates green on the final tree with scope guards intact: MSRV 1.82 clippy both crates, full locked suite, harness unit suite, rebuilt PyO3 pytest; no new deps; public CLI/Python APIs, frozen `.rkdb` writer, hasher, and scope boundaries unchanged; both Rule-3 deviations legitimate | ✓ VERIFIED | `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` exit 0 on root and `--manifest-path pyo3/Cargo.toml`; `cargo test --locked` exit 0; `python3 -m unittest discover -s scripts/bench/tests -t .` → Ran 316, OK (skipped=1); `maturin develop --release` + pytest → 158 passed, 63 skipped. Manifests/lockfiles unchanged; `src/database/format.rs`, `src/hash/table.rs`, `src/kmer/encoding.rs`, `src/kmer/canonical.rs`, `src/cli/args.rs` untouched by the phase; profiling repair is confined to `#[cfg(feature = "profiling")]` and the default binary is byte-identical; `git.allow_default_branch_commits: true` present and documented |

**Score:** 12/12 truths verified (0 present, behavior-unverified)

### Deferred Items

Items not part of Phase 7's contract but explicitly addressed in later milestone phases.

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | `PyCounter::add_from_*` counts through the shared engine (ENGINE-01 dual-surface half) | Phase 9 | ROADMAP Phase 7 Note; CONTEXT "Dual surface" decision |
| 2 | Python D2 skip-N semantics change (PY-02) | Phase 9 | ROADMAP Phase 9 SC3; CONTEXT D2 (Python pre-filter retained here) |
| 3 | Unstable/parallel output sort and Phase-5-golden `.rkdb` byte-identity proof (OUT-01/OUT-02) | Phase 8 | ROADMAP Phase 8; the slice output-stage variance is recorded for Phase 8 |

### Honest Measurement Assessment (recorded, non-blocking)

The recorded ENGINE-02 numbers are internally consistent, match the immutable Phase 6 baselines, and replicate independently on this host:

| Claim | Phase 6 | Phase 7 recorded | Phase 7 independent re-run |
|---|---|---|---|
| Synthetic t1 / t4 / t16 wall | 13.59 / 8.32 / 6.74 s | 6.42 / 4.09 / 4.00 s | 6.32 / 3.94 / 3.81 s |
| Synthetic speedup t4 / t16 | 1.633 / 2.016 | 1.570 / 1.605 (GREEN) | 1.604 / 1.659 (GREEN) |
| Slice t1 / t4 / t16 wall | 57.16 / 34.98 / 26.96 s | 36.92 / 17.76 / 23.83 s | 37.95 / 17.63 / 17.64 s |
| Slice peak RSS t16 | 26,952,056,832 B | 17,968,676,864 B | 17,975,721,984 B |
| Slice counts (every arm) | 229,694,874 / 519,271,168 | same | same |
| Slice `.rkdb` sha256 | — | `0976f29c…` ×3 | `0976f29c…` ×3 |

Two honest observations, neither a phase-contract failure:

1. **The gain is absolute wall-clock, not an improved speedup ratio.** The Phase 7 speedup ratios (t1/tN) are lower than Phase 6's (synthetic t16 2.016 → 1.605 recorded / 1.659 re-run; slice t16 2.120 → 1.549 recorded / 2.152 re-run) because t1 itself became ~2.1x faster. The plan's measurable ENGINE-02 contract (gate GREEN at `min_speedup=1.3`, every synthetic and slice median strictly below Phase 6, parity before timing, provenance) is met and re-verified, but the ROADMAP prose "parallel-scaling efficiency materially improves toward jellyfish's measured 8.9x-on-16-cores profile" is **not** demonstrated as a ratio improvement. The milestone-level judgment belongs to Phase 10.
2. **The engine is producer-bound, as the research predicted.** The split probe measures the count phase as one producer on the caller thread: producer/wall = 1.00000 (t1), 0.99999 (t4), 0.99997 (t16); 4 workers busy 4.72-4.75 s and 16 workers busy 1.20-1.25 s inside a ~6.44 s producer wall. A single producer is the parallel-stage bottleneck; parallel extraction / file-level producers is the documented, unbuilt next lever (07-RESEARCH fallback trigger, not triggered). The recorded slice t16 > t4 wall (23.83 vs 17.76 s) was **not** reproduced (re-run: 17.64 vs 17.63 s) and remains attributed to the single-rep output stage, which Phase 8 owns.

### Required Artifacts

The plan frontmatter declares must-have artifacts in string form; `query verify.artifacts` parses zero structured entries for all four plans (`total: 0`), so every artifact was verified manually at existence, substance, and wiring levels.

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/count/engine.rs` | Engine entry point | ✓ VERIFIED | 1,599 lines; `CountEngine`, `CountResult`, `EngineConfig`, worker pipeline, flush/ack, checked sums, Drop join; wired by CLI; no prints/unwraps in production code |
| `src/count/batch.rs` | Partition-tagged batches + worker stats | ✓ VERIFIED | 74 lines; `CountBatch::{Dense,Wide,Flush}`, `WorkerStat::Flush`, `Send` assertion test, ownership/ordering docs |
| `src/count/partition.rs` | splitmix64 routing + layout | ✓ VERIFIED | 311 lines; `mix64`, `partition_of`, `PartitionLayout` `P=min(256,max(64,threads))`; 7 unit tests green |
| `src/count/mod.rs` | Module root and re-exports | ✓ VERIFIED | 22 lines; exports engine/batch/partition (diagnostics cfg-gated) |
| `src/kmer/extract.rs` | ONE `for_each_window` extractor | ✓ VERIFIED | 190 lines; rolling k≤32, u128 k 33..=64, skip-N, fallible sink, doctest; used by engine + PyO3 |
| `src/cli/commands/count.rs` | CLI cutover | ✓ VERIFIED | 634 lines; engine at every thread count, frozen writers adapted to `&CountResult`, `build_global` ordering preserved, legacy helpers deleted |
| `pyo3/src/counter.rs` | PyO3 extractor routing | ✓ VERIFIED | 828 lines; `add_sequence` and `process_sequence_into_local` call `for_each_window`; pre-filter and `py.detach` captures retained |
| `src/hash/local.rs` | Additive `get_count` | ✓ VERIFIED | Width-correct lookup only; no behavior change to increment/reduction |
| `tests/count_engine_tests.rs` | Engine exactness/CLI-boundary suite | ✓ VERIFIED | 1,406 lines; 20 tests, all green |
| `tests/window_extract_differential_tests.rs` | Extractor differential | ✓ VERIFIED | 253 lines; 9 tests, all green |
| `tests/thread_pool_size_tests.rs` | Exact 2N+1 standing gate | ✓ VERIFIED | 237 lines; exact equality, no `>=`, live subprocess observation |
| `tests/thread_pool_size_tests.rs` helpers | `verify_threads.py` + unit suite | ✓ VERIFIED | 315-line helper with polling/exit contract; 388-line unit suite (18 tests) green |
| `examples/engine_probe.rs` | Feature-gated split probe | ✓ VERIFIED | 97 lines; reads diagnostics after `finish`; default build exits 2 with a hint |
| `phase7_*.json` (6 evidence docs) | Measured evidence | ✓ VERIFIED | Schema + provenance valid; numbers match the immutable Phase 6 baselines; reproduced above |
| `src/core/mod.rs`, `src/core/monitoring.rs` | Profiling-feature repair | ✓ VERIFIED | Stray cfg, `active_timers` typo, `Drop` move, macro re-export; changes confined to the profiling feature; default release binary byte-identical |

**Artifacts:** 15/15 verified.

### Key Link Verification

Plan key-links are also declared in string form and `query verify.key-links` parses zero entries (`total: 0`); verified manually.

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `execute_count` | `CountEngine::count_file` | direct construction, every file | ✓ WIRED | `count.rs:190-191,245` |
| `CountEngine` | `for_each_window` | `count_sequence` sink | ✓ WIRED | `engine.rs:958` (sequential), `engine.rs:975` (parallel) |
| `for_each_window` | `partition_of` → `LocalKmerCounts::increment` | routing sink | ✓ WIRED | `engine.rs:959-968`, `engine.rs:1092-1127` |
| Producer | per-worker `sync_channel` | `CountBatch` batch send | ✓ WIRED | `engine.rs:658,1139-1158`; batch ownership moved |
| File boundary | `Flush{token}` → per-worker ack | checked cumulative stats | ✓ WIRED | `engine.rs:1206-1249`, workers `1300-1322` |
| `CountResult` | frozen text/`.rkdb` writers | `filtered_pairs` | ✓ WIRED | `count.rs:283-293,341-471`; writer/format untouched |
| `CountResult::merge_into` | `KmerCounter::merge_local_counts` | rayon `try_for_each` | ✓ WIRED | `engine.rs:464-469`; verbatim overflow test green |
| `CountEngine::new` | named engine workers | `rustkmer-count-{i}` threads | ✓ WIRED | `engine.rs:660-662`; live observer 2/9/33 |
| `PyCounter::add_from_*` | `py.detach` → `process_*_file_on_counter` → `process_sequence_into_local` → `for_each_window` | owned Send captures | ✓ WIRED | `counter.rs:346-420,671-694,707-763,776-828` |
| `PyCounter::add_sequence` | pre-filter → `for_each_window` → `increment` | retained Python contract | ✓ WIRED | `counter.rs:294-323` |
| `maturin develop --release` | import/`PyCounter` assert → pytest | rebuilt module | ✓ WIRED | Re-ran: module path `.venv311/.../pyrustkmer/__init__.py`; 158 passed |
| Release binary | synthetic/slice gate + probe | `d107d17e…` | ✓ WIRED | Rebuilt default binary matches the measured provenance sha256 |

**Wiring:** 12/12 connections verified.

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `CountResult.tables` | per-partition `LocalKmerCounts` | producer's `for_each_window` windows, routed by `partition_of`; workers increment owned tables | Yes — counts equal the independent reference map and the pinned slice counts | ✓ FLOWING |
| CLI text/`.rkdb` writers | `filtered_pairs` | `CountResult` tables | Yes — output maps/sha equal the reference path; no static fallback | ✓ FLOWING |
| PyO3 `add_sequence` / file helpers | `KmerCounter` / `LocalKmerCounts` | shared extractor over (pre-filtered) record bytes | Yes — N-read parity matches the pure-Python pre-filter oracle | ✓ FLOWING |
| `engine_probe` diagnostics | `EngineDiagnostics` | timers around the real producer/worker loops | Yes — positive wall/producer/worker values; producer-bound observation | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Extractor differential | `cargo test --locked --test window_extract_differential_tests` | 9 passed; 0 failed | ✓ PASS |
| Engine exactness + CLI boundary | `cargo test --locked --test count_engine_tests` | 20 passed; 0 failed | ✓ PASS |
| Exact 2N+1 pool gate (3 consecutive) | `cargo test --locked --test thread_pool_size_tests` ×3 | 2 passed each (3.61 s / 3.58 s / 3.55 s) | ✓ PASS |
| Live thread observation | `python3 .planning/research/profiling/verify_threads.py --binary target/release/rustkmer --input <100k fixture> --build-profile release --threads 1 4 16` | `requested=1 observed=2`; `4→9`; `16→33`; `verdict=GREEN`; exit 0 | ✓ PASS |
| Determinism (fixture) | CLI count at `--threads 1/4/16`, binary + text | `.rkdb` all `065c815e…`; text all `debee64c…`; 12,999,981 lines | ✓ PASS |
| Synthetic scaling gate | `python3 scripts/bench/thread_scaling.py --mode synthetic --reads 500000 --reps 3` (independent re-run) | GREEN; 6.320/3.940/3.810 s; speedups 1.604/1.659; counts 64,999,000/65,000,000; exit 0 | ✓ PASS |
| Real-slice replication | `thread_scaling.py --mode slice --input <CRR1936095 part_001> --slice-reads 4000000 --reps 1 --measure-only` (independent re-run) | 37.95/17.63/17.64 s; pinned 229,694,874/519,271,168 every arm; RSS 17.96 GB; three `.rkdb` sha256 `0976f29c…` | ✓ PASS |
| Producer/worker split | `target/release/examples/engine_probe <fixture> fastq 1|4|16` | t1 workers=[]; t4 4 workers × 800 batches; t16 16 workers × 200 batches; producer ≈ wall | ✓ PASS |
| Golden / exactness suites | `cargo test --locked --test golden_sha256_tests --test golden_tests --test thread_local_count_tests --test dense_differential_tests` | 5 / 34 / 10 / 6 passed; 0 failed | ✓ PASS |
| Full Rust suite | `cargo test --locked` | exit 0; no failed test | ✓ PASS |
| Harness unit suite | `python3 -m unittest discover -s scripts/bench/tests -t .` | Ran 316; OK (skipped=1) on idle re-run | ✓ PASS (one transient stub-timing failure reproduced and cleared; see Anti-Patterns) |
| MSRV clippy | `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` (root and pyo3) | exit 0 both | ✓ PASS |
| PyO3 rebuild + pytest | `maturin develop --release` then `pytest pyo3/tests -q` | module path recorded; 158 passed, 63 skipped | ✓ PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` probes are declared or present for this phase. The phase's declared probe-like helper is the live thread observer:

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| `.planning/research/profiling/verify_threads.py` | `python3 .planning/research/profiling/verify_threads.py --binary target/release/rustkmer --input <fixture> --json /tmp/... --build-profile release --threads 1 4 16` | exit 0; `requested=1 observed=2`, `requested=4 observed=9`, `requested=16 observed=33`, `THREAD REALITY verdict=GREEN`; JSON records carry binary sha256 `d107d17e…` | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ENGINE-01 | 07-01, 07-02, 07-03(shared extractor) | ONE counting entry point consumed by CLI and structurally by Python: fixed pool, producer → bounded queue, N persistent workers on disjoint partitioned tables, overlapped decompression, no fork-join | ✓ SATISFIED | Engine wired into every CLI thread count; live 2N+1 observation; producer/worker split measured. `PyCounter::add_from_*` engine consumption is the Phase 9 half per the ROADMAP Note; the shared extractor and `merge_into` bridge exist now |
| ENGINE-02 | 07-04 | PROF-02 gate green after the engine; scaling efficiency materially improves toward jellyfish's; slice wall-clock drops measurably | ✓ SATISFIED (plan contract) | Gate GREEN with speedups ≥ 1.3; every recorded synthetic and slice median strictly below Phase 6; independent re-runs replicate. Honest caveat: the gain is absolute wall-clock, not an improved speedup ratio; the engine is producer-bound (see Honest Measurement Assessment) |
| ENGINE-03 | 07-01, 07-02, 07-03 | ONE core window extractor implements D2 skip-N for both surfaces; MultiGz multi-member regression stays green | ✓ SATISFIED | `for_each_window` used by engine and PyO3; no second loop; 9-test differential; multi-member gzip + trailing-garbage tests green; Python pre-filter retained (D2 stays Phase 9) |

**Coverage:** 3/3 Phase 7 requirements satisfied; no orphaned requirements (REQUIREMENTS.md maps only ENGINE-01..03 to this phase, all declared in plans).

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `tests/count_engine_tests.rs` | ENGINE-01/02/03 | 20 | 0 | No — reference maps come from `encode_kmer_bytes_u128` + `canonical_kmer_u128` over naive windows and the real CLI, not from the engine | Value/Behavioral | PASS |
| `tests/window_extract_differential_tests.rs` | ENGINE-03 | 9 | 0 | No — naive per-window reference with order + conservation checks | Value | PASS |
| `tests/thread_pool_size_tests.rs` | ENGINE-01/02 (PROF-02) | 2 | 0 on macOS/Linux (Windows platform guard) | No — live subprocess observation | Behavioral | PASS |
| `pyo3/tests/test_counter.py` (`TestPyCounterNReadPreFilterParity`) | ENGINE-03 | 12 | 0 (module-import guard not triggered) | No — pure-Python pre-filter oracle | Value | PASS |
| `scripts/bench/tests/test_verify_threads.py` | ENGINE-02 (PROF-02) | 18 | 0 on Darwin/Linux (`skipUnless` platform guard) | No — real child-thread observation + RED negative control | Behavioral | PASS |

**Disabled tests on requirements:** 0. The only ignored tests in the phase's vicinity (one-shot baseline capture, release-only timing gate) predate this phase and are deliberate.
**Circular patterns detected:** 0.
**Insufficient assertions:** 0.
**Expected-value provenance:** VALID — pinned slice counts come from the Phase 5 jellyfish 2.3.1 reference bound to the input fingerprint; Python N-read expectations come from an independent pure-Python implementation.

### Decision Coverage

No trackable decisions in `07-CONTEXT.md` (`skipped: true`, `total: 0`, `honored: 0`) — the context's design decisions are prose bullets, so the gate had nothing to match.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/placeholder markers in any phase-created or phase-modified file | — | None |
| `src/count/engine.rs` | — | No `println!`/`eprintln!`, no `unwrap()`/`expect()` in production code | — | None |
| `src/hash/table.rs` | 483 | Pre-existing nightly-only `AtomicU64::fetch_update` deprecation warning (file untouched by this phase) | ℹ️ Info | MSRV 1.82 clippy gates are warning-free; recorded in the evidence notes |
| `scripts/bench/tests/test_verify_threads.py` | 341 | `test_pre_engine_n_plus_one_stub_is_measured_red` is timing-sensitive: under load the stub can be sampled before its threads exist (`observed=0`), failing `assertIn("requested=4 observed=5")` | ℹ️ Info | Reproduced once during this verification under load, then passed unmodified on an idle re-run (`Ran 316 tests … OK`); the evidence already records the same first-run failure. The gate stays strict (observed=0 is a failure, never a PASS); no test/threshold was softened |
| `src/cli/commands/count.rs` | 360 | Pair materialization before the existing stable sort (no Phase 8 streaming/unstable sort yet) | ℹ️ Info | Explicitly accepted for Phase 7 (T-07-05); Phase 8 owns OUT-01/OUT-02 |
| `src/count/engine.rs` | — | Single-producer pipeline is the parallel-stage bottleneck (producer ≈ 100% of the parallel count wall) | ℹ️ Info | Predicted by 07-RESEARCH (producer ~5.4 s budget); parallel extraction is the documented next lever, not built |

**Anti-patterns:** 0 blockers, 0 warnings, 5 informational.

### Human Verification Required

N/A — infrastructure/foundation phase with no user-facing elements. All acceptance criteria (engine shape, exactness, extractor semantics, gates, measurement) were verified programmatically and by re-execution; `behavior_unverified` is 0. Per the infrastructure-phase rule, no artificial manual steps are invented.

### Gaps Summary

**No gaps found.** The phase goal is achieved as scoped by the roadmap Note:

- CLI counting runs through ONE shared engine (`src/count/engine.rs`) at every thread count; the old per-chunk rayon hot loop is gone.
- The engine is one producer on the caller thread → N persistent named OS workers over disjoint splitmix64 hash-range partition tables with bounded per-worker queues and a file-boundary flush/ack barrier; `--threads 1` is a true sequential path with no extra thread.
- The producer/consumer overlap is measured (workers' busy time fits inside the producer wall) and the engine is honestly recorded as producer-bound — the research-documented next lever.
- One `for_each_window` extractor implements skip-N for the CLI and PyO3; Python's pre-filter is retained, so D2 remains Phase 9's change.
- Exactness is preserved: pinned slice parity, identical sorted `.rkdb` bytes across t1/t4/t16 (replicated byte-for-byte), disjointness/conservation property tests, and the verbatim overflow contract at every new summation site.
- The PROF-02 gate is GREEN and all recorded performance claims were independently replicated; the honest caveat is that the improvement is absolute wall-clock rather than an improved speedup ratio, and the remaining parallel-stage bottleneck is the single producer.

Deferred to later phases (not gaps): PyCounter engine routing + Python D2 (Phase 9), output sort/streaming + Phase-5-golden byte-identity proof (Phase 8).

### Verification Metadata

**Verification approach:** Goal-backward against ROADMAP Phase 7 success criteria merged with the four plans' frontmatter must-haves.
**Must-haves source:** ROADMAP.md success criteria + PLAN frontmatter (07-01..07-04).
**Automated checks:** full Rust suite (exit 0), 5 exactness/golden suites, 3 consecutive pool gates, extractor/engine suites, live thread observer, synthetic and slice measurement re-runs, harness unit suite, MSRV clippy both crates, rebuilt PyO3 pytest — all passed. One transient test-environment flake reproduced and cleared unmodified.
**Human checks required:** 0.
**Total verification time:** ~60 min (including independent synthetic and 4M-slice re-measurements).

---

*Verified: 2026-11-12T16:17:11Z*
*Verifier: Claude (gsd-verifier)*
