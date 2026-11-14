---
phase: 07-shared-counting-engine
verified: 2026-11-14T04:20:47Z
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
covered_digest: "v4:sha256:bc1e058c9aeca2fb8135ba32ef7983b2f260aaa0fce1a4337c27e01fe92db2b1"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 12/12
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 7: Shared Counting Engine Verification Report

**Phase Goal:** CLI counting runs through one shared engine — persistent workers, disjoint partitioned tables, overlapped producer/consumer I/O — recovering the measured ~3.5x parallel-scaling deficit, with Python inheritance structural rather than accidental.
**Verified:** 2026-11-14T04:20:47Z (UTC; local 2026-11-14)
**Status:** passed
**Re-verification:** Yes — freshness re-run against the current tree (no prior gaps; Phases 8 and 9 changed covered files, moving the previous digest to `stale`)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ONE counting entry point (`src/count/engine.rs`) exists and is consumed by both CLI counting (`execute_count`) and `PyCounter::add_from_*` | ✓ VERIFIED | `src/count/engine.rs:559` (`pub struct CountEngine`); CLI `src/cli/commands/count.rs:193` builds one `CountEngine` for every resolved thread count and `:247` counts every file through `engine.count_file`; PyO3 `pyo3/src/counter.rs:676-687` (`count_file_into_counter`) builds `EngineConfig`/`CountEngine`, calls `count_file`, then `finish()?.merge_into(counter)` inside `py.detach` (`:399`, `:452`); `grep -n "par_chunks\|try_for_each_init\|CHUNK_SIZE\|SUBSLICE_RECORDS\|CountOutput" src/cli/commands/count.rs` → no match (exit 1). The Phase 7 deferred PyCounter half is now delivered (Phase 9), so the ENGINE-01 dual-surface contract holds on the current tree |
| 2 | Fixed rayon pool built before any rayon query; producer streams records into bounded per-worker queues; N persistent workers count into disjoint hash-range-partitioned thread-local tables; decompression overlaps counting; no per-chunk fork-join barrier; `--threads 1` is true sequential | ✓ VERIFIED | `count.rs:152-155` `build_global` before `CountEngine::new`; engine counting never calls rayon (`src/count/engine.rs` uses rayon only in `merge_into:505-510`); `engine.rs:598-630` sequential vs parallel selection; `:699-700` `sync_channel(queue_batches=8)` per worker; `:701-703` exactly N named `rustkmer-count-{i}` threads; `src/count/partition.rs:139-147` disjoint contiguous worker ranges over splitmix64 routing (`:72`); `engine.rs:1126-1199` route/send, `:1298-1374` worker loop, `:1247-1290` flush/ack. Live observer on the current release binary: requested 1→2, 4→9, 16→33 OS threads, `THREAD REALITY verdict=GREEN`; `thread_pool_size_tests` 2/2 green. Probe: t1 `workers=[]`; t4 four workers × 400 batches with worker busy time inside the producer wall |
| 3 | PROF-02 thread-scaling gate GREEN with both speedups ≥ 1.3, identical nonzero counts across arms, and synthetic walls strictly below the Phase 6 baseline | ✓ VERIFIED | Recorded `phase7_scaling_green.json`: GREEN, speedup_t4=1.5697, speedup_t16=1.605; counts 64,999,000/65,000,000 in every arm; medians 6.42/4.09/4.00 s vs Phase 6 13.59/8.32/6.74 s. Supplementary current-tree re-run on the same deterministic input (sha256 `bd64b2c1…`, 500k reads, reps 3): exit 0, GREEN, medians 5.57/2.22/1.78 s, speedups 2.509/3.129, identical 64,999,000/65,000,000 counts. Caveats recorded in Honest Measurement Assessment: the re-run artifact is `8b92cb2a…` (a release artifact of HEAD `698522d` whose exact feature set is not recorded — a concurrent build swapped the top-level link mid-run) and the host was shared with other harness runs; the ratios improved because Phase 8's output-stage optimization is inside the measured wall, not because the engine changed |
| 4 | Real 4M-read slice: pinned Distinct 229,694,874 / Total 519,271,168 in every arm before any timing; t1/t4/t16 medians strictly below Phase 6 (57.16/34.98/26.96 s); t16 peak RSS ≤ 26,952,056,832 B; provenance on the artifact | ✓ VERIFIED | `phase7_slice_green.json`: every arm 229,694,874/519,271,168; 36.92/17.76/23.83 s; RSS 17,958,944,768 / 17,966,088,192 / 17,968,676,864 B; provenance binary sha256 `d107d17e…` + commit `aeabb4b…`. Prior verification independently replicated it (37.95/17.63/17.64 s, same pinned counts, same three `0976f29c…` `.rkdb` files). Not re-executed this round: the counting path is byte-identical to the measured one (`git diff aeabb4b..HEAD -- src/count/engine.rs` contains only the additive Phase 8 pair collector; output stage is Phase 8's) and the shared host was saturated by concurrent harness processes |
| 5 | Sorted `.rkdb` outputs are byte-identical at t1/t4/t16 (one sha256) | ✓ VERIFIED | Recorded slice sha256 `0976f29c5edeaa5eb49218e2c2fd5ff84f09109c3f2aac9d83bc8cf8c8668014` at t1/t4/t16. Current-tree check (50k reads, k=21 canonical, N-containing reads): `.rkdb` sha256 `4fc1f07d2fd7f4fa3793211f93153a5af167f1a1280bb5a0c54b7db8a9a2ff67` at t1/t4/t16; text output sha256 `22b43448ec2731015f0f01a499fb92e5c8ca35ee7c808b013bd92d03b2dd0270` at t1/t4/t16; `sort_pairs_ascending_orders_numeric_keys_and_is_deterministic` green |
| 6 | Producer/worker split measured under the `profiling` feature without changing default builds | ✓ VERIFIED | Recorded `phase7_engine_split.json` (t1 workers=[], t4 4×~31.7k batches, t16 16×~7.9k batches, producer/wall ≈ 1.0). Current tree: diagnostics remain `#[cfg(feature = "profiling")]` (`engine.rs:59-60,573-577,1305-1338`); `cargo build --release --locked --example engine_probe` default build runs and exits 2 with the profiling hint and empty stdout; profiling build on the 50k fixture: t1 `{"producer_nanos":195462125,"wall_nanos":195462125,"workers":[]}`, t4 4 workers × 400 batches with `producer_nanos` 85,274,458 inside `wall_nanos` 85,371,209 |
| 7 | ONE core window extractor (`for_each_window`) implements the D2 skip-N semantics and both surfaces route through it; no duplicate extraction logic remains | ✓ VERIFIED | `src/kmer/extract.rs:90-148` (rolling for k≤32, per-window u128 for 33..=64, any non-ACGT window skipped); call sites `src/count/engine.rs:999,1016` and `pyo3/src/counter.rs:322` (add_sequence); `PyCounter::add_from_*` reaches the same extractor through `CountEngine::count_file` (`pyo3/src/counter.rs:682-685`); `grep -rn "RollingEncoder::" src/cli/commands/count.rs src/count/engine.rs pyo3/src/counter.rs` → no match; `grep -rn "for i in 0..=(" …` → no match; differential suite 9/9 green. Python's D2 semantics is now also delivered (Phase 9), so both surfaces share the skip-N behavior |
| 8 | MultiGzDecoder multi-member gzip regression (v1.0 8102985) stays green; engine gzip behavior is complete and loud on trailing garbage | ✓ VERIFIED | `src/io/fastq.rs:637` `test_read_all_sequences_concatenated_gzip_members` and `:782` `test_read_all_errors_on_trailing_garbage_after_gzip_member` green in the full suite; `DefaultCompressedFileReader` still uses `flate2::read::MultiGzDecoder` (`fastq.rs:78`); `count_engine_tests` 20/20 include `multi_member_gzip_counts_every_member_at_t1_and_t4` and `trailing_garbage_fails_loudly_with_file_context` |
| 9 | Exact counts survive partitioning: disjointness + conservation property tests green, and the slice parity gate passes the pinned counts | ✓ VERIFIED | `count_engine_tests` 20/20 green including `partition_disjointness_and_conservation_hold` and `proptest_partition_disjointness_and_conservation`; recorded slice parity pinned in every recorded and independent re-run arm; current-tree synthetic re-run reports identical 64,999,000/65,000,000 in all three arms; current-tree fixture stats 6,489,164 total / 6,489,152 unique at t4 |
| 10 | Every new summation site fails loud with checked arithmetic, and the per-key u32 overflow keeps the verbatim contract message | ✓ VERIFIED | `checked_sum_fails_loud_on_total_overflow`, `checked_sum_fails_loud_on_exact_max_plus_one`, `reduce_worker_stats_fails_loud_on_aggregate_overflow`, `merge_into_preserves_verbatim_per_key_overflow`, `worker_overflow_returns_verbatim_error_without_hanging` green; constants at `engine.rs:84-90` and assertions at `:1452,1468`; per-key path inherits `LocalKmerCounts::increment`'s verbatim `K-mer count overflow reached maximum value 4294967295` |
| 11 | CLI behavior at the engine/legacy boundary is preserved: N-read skip semantics, multi-file cumulative stats, one warning per 4096-record batch with pinned wording, text/binary ordering, `-L/-U` filters, `--no-sort` contents | ✓ VERIFIED | `n_containing_reads_match_skip_n_reference`, `multi_file_stats_and_warnings_are_preserved`, `text_and_binary_output_order_is_unchanged`, `count_filters_are_unchanged`, `no_sort_still_writes_the_same_set` all green; warning wording at `count.rs:258-264`; current-tree fixture text map identical at t1/t4/t16 |
| 12 | Standing gates green on the current tree with scope guards intact: MSRV 1.82 clippy both crates, full locked suite, harness unit suite, rebuilt PyO3 pytest; no new deps; public CLI/Python APIs, frozen `.rkdb` writer functions, hasher, and scope boundaries unchanged by Phase 7 | ✓ VERIFIED | `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` exit 0 on root and `--manifest-path pyo3/Cargo.toml`; `cargo test --locked` exit 0 (32 test-result blocks all ok; `count_engine_tests` 20, `window_extract_differential_tests` 9, `thread_pool_size_tests` 2); `python3 -m unittest discover -s scripts/bench/tests -t .` → Ran 571, OK (skipped=1); `pytest pyo3/tests -q` → 179 passed, 63 skipped; manifests/lockfiles unchanged since Phase 7; `src/database/format.rs` gained only an additive Phase 9 sorted-input constructor (header/entry writers unchanged); `src/hash/table.rs`, `src/kmer/encoding.rs`, `src/kmer/canonical.rs`, `src/cli/args.rs` untouched |

**Score:** 12/12 truths verified (0 present, behavior-unverified)

### Previously Deferred, Now Delivered (Phases 8-9)

The three items deferred by the original Phase 7 verification are now present on the current tree; none remains a deferral.

| # | Item | Delivered In | Evidence |
|---|------|-------------|----------|
| 1 | `PyCounter::add_from_*` counts through the shared engine (ENGINE-01 dual-surface half) | Phase 9 | `pyo3/src/counter.rs:676-687` builds `CountEngine`, counts the file, and merges via `CountResult::merge_into`; commit `d8befcf` |
| 2 | Python D2 skip-N semantics (PY-02) | Phase 9 | `pyo3/src/counter.rs:310-322` feeds raw bytes to `for_each_window`; `pyo3/tests/test_counter.py:1310` `TestPyCounterNReadSkipParity` |
| 3 | Unstable/parallel output sort + streaming write, and `.rkdb` v2 byte identity (OUT-01/OUT-02) | Phase 8 | `src/cli/commands/count.rs:349-359,389,444` consuming pair collection + in-place `par_sort_unstable`; `src/count/engine.rs:391-425`; `src/hash/local.rs:323`; `tests/output_pipeline_tests.rs` and `rkdb_v2_byte_identity_tests` green |

### Honest Measurement Assessment (recorded, non-blocking)

| Claim | Phase 6 | Phase 7 recorded | Prior independent re-run | Current-tree re-run (2026-11-14) |
|---|---|---|---|---|
| Synthetic t1 / t4 / t16 wall | 13.59 / 8.32 / 6.74 s | 6.42 / 4.09 / 4.00 s | 6.32 / 3.94 / 3.81 s | 5.57 / 2.22 / 1.78 s |
| Synthetic speedup t4 / t16 | 1.633 / 2.016 | 1.570 / 1.605 (GREEN) | 1.604 / 1.659 (GREEN) | 2.509 / 3.129 (GREEN) |
| Slice t1 / t4 / t16 wall | 57.16 / 34.98 / 26.96 s | 36.92 / 17.76 / 23.83 s | 37.95 / 17.63 / 17.64 s | not re-run (recorded evidence stands) |
| Slice peak RSS t16 | 26,952,056,832 B | 17,968,676,864 B | 17,975,721,984 B | not re-run |
| Slice counts (every arm) | 229,694,874 / 519,271,168 | same | same | not re-run |
| Slice `.rkdb` sha256 | — | `0976f29c…` ×3 | `0976f29c…` ×3 | fixture check: `4fc1f07d…` ×3 |

Four honest observations, none a phase-contract failure:

1. **The synthetic ratio improvement is now real but is partly Phase 8's.** The current-tree re-run's t16 speedup (3.129) exceeds Phase 6's (2.016) and Phase 7's recorded 1.605, because Phase 8 replaced the serial output stage inside the measured `count` wall. It is not evidence that the Phase 7 engine alone scales further: the recorded engine probe still shows producer/wall ≈ 1.0 and workers idle inside the producer wall for the 4M slice. The ROADMAP prose target ("toward jellyfish's measured 8.9x-on-16-cores") remains a milestone-level judgment, answered at full scale by Phase 10 (overall YES), not by this synthetic gate.
2. **The engine is producer-bound, as the research predicted.** Recorded split probe: producer/wall = 1.00000 (t1), 0.99999 (t4), 0.99997 (t16); a single producer is the parallel-stage bottleneck; parallel extraction / file-level producers is the documented, unbuilt next lever. The current-tree 50k-fixture probe reproduces the same shape (t4 producer 85.27 ms vs wall 85.37 ms; four workers busy ~31.6-33.5 ms each).
3. **The current-tree measurement ran on a shared, loaded host and with a swapped top-level binary link.** The re-run artifact records binary `8b92cb2a…` because a concurrent harness build from another session replaced `target/release/rustkmer` mid-run; the default release artifact `f6ace9f7…` was rebuilt from the same HEAD `698522d` and restored afterwards. The transient artifact's exact feature set is not recorded (its size differs from the default build by 160 bytes), so the recorded wall numbers are used only as a supplementary observation; the primary ENGINE-02 evidence remains the recorded artifact. Concurrent `bench.py --mode slice` and parity runs from other sessions also saturated the host. The gate still returned GREEN with wide margins and identical counts, but these numbers are supplementary; the primary ENGINE-02 evidence remains the recorded artifact.
4. **The slice was not re-executed this round.** The 4M-read counting path is unchanged since the recorded measurement (verified by diffing `aeabb4b..HEAD`), and a clean slice run was not obtainable on the contended host. The recorded artifact and the prior verification's independent replication remain the evidence of record.

### Required Artifacts

The plan frontmatter declares must-have artifacts in string form; `query verify.artifacts` parses zero structured entries for all four plans, so every artifact was verified manually at existence, substance, and wiring levels.

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/count/engine.rs` | Engine entry point | ✓ VERIFIED | 1,640 lines; `CountEngine` at `:559`, worker pipeline, flush/ack, checked sums, Drop join; `merge_into` at `:505`; Phase 8's additive `into_filtered_pairs` at `:413`; wired by CLI and PyO3; no prints/unwraps in production code |
| `src/count/batch.rs` | Partition-tagged batches + worker stats | ✓ VERIFIED | 74 lines; `CountBatch::{Dense,Wide,Flush}`, `WorkerStat::Flush`, `Send` assertion test |
| `src/count/partition.rs` | splitmix64 routing + layout | ✓ VERIFIED | 311 lines; `mix64`, `partition_of:72`, `PartitionLayout` `P=min(256,max(64,threads))`; 7 unit tests green |
| `src/count/mod.rs` | Module root and re-exports | ✓ VERIFIED | 22 lines; exports engine/batch/partition (diagnostics cfg-gated) |
| `src/kmer/extract.rs` | ONE `for_each_window` extractor | ✓ VERIFIED | 190 lines; rolling k≤32, u128 k 33..=64, skip-N, fallible sink, doctest; used by engine and PyO3 |
| `src/cli/commands/count.rs` | CLI cutover | ✓ VERIFIED | 700 lines; engine at every thread count (`:193,:247`), Phase 8 consuming output stage, `build_global` ordering preserved, legacy helpers absent |
| `pyo3/src/counter.rs` | PyO3 engine/extractor routing | ✓ VERIFIED | 769 lines; `add_sequence` uses `for_each_window` (`:322`); `add_from_*` use `CountEngine` (`:676-687`) inside `py.detach`; public API retained |
| `src/hash/local.rs` | Additive `get_count` / `into_pairs_into` | ✓ VERIFIED | 514 lines; width-correct lookup and consuming drain only; increment/reduction behavior unchanged |
| `tests/count_engine_tests.rs` | Engine exactness/CLI-boundary suite | ✓ VERIFIED | 1,406 lines; 20 tests, all green |
| `tests/window_extract_differential_tests.rs` | Extractor differential | ✓ VERIFIED | 253 lines; 9 tests, all green |
| `tests/thread_pool_size_tests.rs` | Exact 2N+1 standing gate | ✓ VERIFIED | 237 lines; exact equality, live subprocess observation; 2 tests green |
| `tests/thread_pool_size_tests.rs` helpers | `verify_threads.py` + unit suite | ✓ VERIFIED | 315-line helper with polling/exit contract; 388-line harness unit suite (18 tests) green within the 571-test run |
| `examples/engine_probe.rs` | Feature-gated split probe | ✓ VERIFIED | 97 lines; default build exits 2 with a hint; profiling build emits producer/worker JSON |
| `phase7_*.json` (6 evidence docs) | Measured evidence | ✓ VERIFIED | Schema + provenance valid; numbers match the immutable Phase 6 baselines; supplementary current-tree replication recorded above |
| `src/core/mod.rs`, `src/core/monitoring.rs` | Profiling-feature repair | ✓ VERIFIED | Changes confined to the profiling feature; default build still compiles (default probe exits with the expected hint) |

**Artifacts:** 15/15 verified.

### Key Link Verification

Plan key-links are declared in string form and `query verify.key-links` parses zero entries (`total: 0`); verified manually.

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `execute_count` | `CountEngine::count_file` | direct construction, every file | ✓ WIRED | `count.rs:193,247` |
| `CountEngine` | `for_each_window` | `count_sequence` sink | ✓ WIRED | `engine.rs:999` (sequential), `engine.rs:1016` (parallel) |
| `for_each_window` | `partition_of` → `LocalKmerCounts::increment` | routing sink | ✓ WIRED | `engine.rs:1000-1009`, `engine.rs:1132-1168` |
| Producer | per-worker `sync_channel` | `CountBatch` batch send | ✓ WIRED | `engine.rs:699,1180-1199`; bounded backpressure |
| File boundary | `Flush{token}` → per-worker ack | checked cumulative stats | ✓ WIRED | `engine.rs:1247-1290`, workers `:1340-1363` |
| `CountResult` | text/`.rkdb` writers | consuming `into_filtered_pairs` (Phase 8) | ✓ WIRED | `count.rs:389,444`; header/entry writer functions frozen |
| `CountResult::merge_into` | `KmerCounter::merge_local_counts` | rayon `try_for_each` | ✓ WIRED | `engine.rs:505-510`; verbatim overflow test green |
| `CountEngine::new` | named engine workers | `rustkmer-count-{i}` threads | ✓ WIRED | `engine.rs:701-703`; live observer 2/9/33 |
| `PyCounter::add_from_*` | `py.detach` → `count_file_into_counter` → `CountEngine::count_file` → engine extractor → `merge_into` | owned Send captures | ✓ WIRED | `counter.rs:367-456,676-687` |
| `PyCounter::add_sequence` | pre-filter-free raw bytes → `for_each_window` → `increment` | D2 skip-N contract | ✓ WIRED | `counter.rs:306-343` |
| Installed extension | pytest suite | `maturin`-built module | ✓ WIRED | 179 passed, 63 skipped; module version 0.5.0 |
| Release binary | synthetic gate + observer | `f6ace9f7…` (HEAD `698522d`) | ✓ WIRED | Observer GREEN 2/9/33; synthetic re-run GREEN |

**Wiring:** 12/12 connections verified.

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `CountResult.tables` | per-partition `LocalKmerCounts` | producer's `for_each_window` windows, routed by `partition_of`; workers increment owned tables | Yes — counts equal the independent reference map and the pinned slice counts | ✓ FLOWING |
| CLI text/`.rkdb` writers | `into_filtered_pairs` buffer | `CountResult` tables | Yes — output maps/sha equal across thread counts; no static fallback | ✓ FLOWING |
| PyO3 `add_sequence` / file helpers | `KmerCounter` / `LocalKmerCounts` | shared extractor over raw record bytes; engine tables merged through the checked bridge | Yes — Python D2 tests and Cargo/CLI parity suites green | ✓ FLOWING |
| `engine_probe` diagnostics | `EngineDiagnostics` | timers around the real producer/worker loops | Yes — positive wall/producer/worker values; producer-bound observation | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Extractor differential | `cargo test --locked --test window_extract_differential_tests` | 9 passed; 0 failed | ✓ PASS |
| Engine exactness + CLI boundary | `cargo test --locked --test count_engine_tests` | 20 passed; 0 failed | ✓ PASS |
| Exact 2N+1 pool gate | `cargo test --locked --test thread_pool_size_tests` | 2 passed; 0 failed | ✓ PASS |
| Live thread observation | `python3 .planning/research/profiling/verify_threads.py --binary target/release/rustkmer --input <500k fixture> --build-profile release --threads 1 4 16` | `requested=1 observed=2`; `4→9`; `16→33`; `verdict=GREEN` | ✓ PASS |
| Determinism (current tree) | CLI count at `--threads 1/4/16`, binary + text, 50k reads with Ns | `.rkdb` all `4fc1f07d…`; text all `22b43448…`; stats 6,489,164 / 6,489,152 | ✓ PASS |
| Synthetic scaling gate (recorded) | `python3 scripts/bench/thread_scaling.py --mode synthetic --reads 500000 --reps 3` | GREEN; 6.42/4.09/4.00 s; speedups 1.570/1.605; counts 64,999,000/65,000,000 | ✓ PASS |
| Synthetic scaling gate (current tree) | same command, isolated scratch, `--cooldown-s 5` | GREEN; 5.57/2.22/1.78 s; speedups 2.509/3.129; same counts; provenance `8b92cb2a…` (see caveat) | ✓ PASS (supplementary) |
| Producer/worker split (current tree) | `target/release/examples/engine_probe <50k fixture> fastq 1|4` | t1 `workers=[]`; t4 4 workers × 400 batches, producer≈wall | ✓ PASS |
| Default build has no diagnostics | `cargo build --release --locked --example engine_probe` then run | exit 2, hint on stderr, empty stdout | ✓ PASS |
| Full Rust suite | `cargo test --locked` | exit 0; 32 test-result blocks ok | ✓ PASS |
| Harness unit suite | `python3 -m unittest discover -s scripts/bench/tests -t .` | Ran 571; OK (skipped=1) | ✓ PASS |
| MSRV clippy | `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` (root and pyo3) | exit 0 both | ✓ PASS |
| PyO3 pytest | `.venv313/bin/python -m pytest pyo3/tests -q` | 179 passed, 63 skipped | ✓ PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` probes are declared or present for this phase. The phase's declared probe-like helper is the live thread observer:

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| `.planning/research/profiling/verify_threads.py` | `python3 .planning/research/profiling/verify_threads.py --binary target/release/rustkmer --input <500k fixture> --build-profile release --threads 1 4 16 --json /tmp/…` | exit GREEN; `requested=1 observed=2`, `requested=4 observed=9`, `requested=16 observed=33`, `THREAD REALITY verdict=GREEN`; JSON records binary provenance + pid + sampler | PASS |
| `verify_threads.py` through the standing gate | `cargo test --locked --test thread_pool_size_tests` | 2 passed (characterization + exact gate) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ENGINE-01 | 07-01, 07-02, 07-03 | ONE counting entry point consumed by CLI and PyO3: fixed pool, producer → bounded queue, N persistent workers on disjoint partitioned tables, overlapped decompression, no fork-join | ✓ SATISFIED | Engine wired into every CLI thread count; PyO3 `add_from_*` now build the same engine (Phase 9); live 2N+1 observation; producer/worker split measured |
| ENGINE-02 | 07-04 | PROF-02 gate green after the engine; scaling efficiency materially improves toward jellyfish's; slice wall-clock drops measurably | ✓ SATISFIED (plan contract) | Gate GREEN with speedups ≥ 1.3; every recorded synthetic and slice median strictly below Phase 6; current-tree synthetic replication GREEN. Honest caveat: the current-tree ratio gain includes Phase 8's output-stage work, and the engine remains producer-bound (see Honest Measurement Assessment) |
| ENGINE-03 | 07-01, 07-02, 07-03 | ONE core window extractor implements D2 skip-N for both surfaces; MultiGz multi-member regression stays green | ✓ SATISFIED | `for_each_window` used by engine and PyO3 (file paths through the engine, add_sequence directly); no second loop; 9-test differential; multi-member gzip + trailing-garbage tests green; Python D2 delivered in Phase 9 |

**Coverage:** 3/3 Phase 7 requirements satisfied; no orphaned requirements (REQUIREMENTS.md maps only ENGINE-01..03 to this phase, all declared in plans).

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `tests/count_engine_tests.rs` | ENGINE-01/02/03 | 20 | 0 | No — reference maps come from `encode_kmer_bytes_u128` + `canonical_kmer_u128` over naive windows and the real CLI, not from the engine | Value/Behavioral | PASS |
| `tests/window_extract_differential_tests.rs` | ENGINE-03 | 9 | 0 | No — naive per-window reference with order + conservation checks | Value | PASS |
| `tests/thread_pool_size_tests.rs` | ENGINE-01/02 (PROF-02) | 2 | 0 on macOS/Linux (Windows platform guard) | No — live subprocess observation | Behavioral | PASS |
| `pyo3/tests/test_counter.py` (`TestPyCounterNReadSkipParity`, `TestPyCounterRollingPathParity`) | ENGINE-03 | Active in the 179-passed run | Import guard not triggered; 63 directory-wide skips are pre-existing optional/feature guards, none Phase 7 requirements | No — D2 reference + rolling-path oracle | Value | PASS |
| `scripts/bench/tests/test_verify_threads.py` | ENGINE-02 (PROF-02) | 18 | 0 on Darwin/Linux (`skipUnless` platform guard) | No — real child-thread observation + RED negative control | Behavioral | PASS |

**Disabled tests on requirements:** 0. The only ignored tests in the phase's vicinity (one-shot baseline capture, release-only timing gate) predate this phase and are deliberate. The Phase 7 pre-filter parity class was intentionally superseded by Phase 9's `TestPyCounterNReadSkipParity` when Python adopted D2.
**Circular patterns detected:** 0.
**Insufficient assertions:** 0.
**Expected-value provenance:** VALID — pinned slice counts come from the Phase 5 jellyfish 2.3.1 reference bound to the input fingerprint; Python skip-N expectations come from an independent pure-Python implementation.

### Decision Coverage

No trackable decisions in `07-CONTEXT.md` (`skipped: true`, `total: 0`, `honored: 0`) — the context's design decisions are prose bullets, so the gate had nothing to match.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/placeholder markers in any phase-created or phase-modified file | — | None |
| `src/count/engine.rs` | — | No `println!`/`eprintln!`, no `unwrap()`/`expect()` in production code | — | None |
| `src/hash/table.rs` | 483 | Pre-existing nightly-only `AtomicU64::fetch_update` deprecation warning (file untouched by this phase) | ℹ️ Info | MSRV 1.82 clippy gates are warning-free; the default release build emits only this known warning |
| `scripts/bench/tests/test_verify_threads.py` | 321-342 | `test_pre_engine_n_plus_one_stub_is_measured_red` is timing-sensitive: under load the stub can be sampled before its threads exist (`observed=0`) | ℹ️ Info | Not reproduced this round (`Ran 571 tests … OK` on the first run). The gate stays strict (observed=0 is a failure, never a PASS); no test/threshold was softened |
| `src/cli/commands/count.rs` | 349-359 | Phase 8 landed the consuming pair buffer + in-place parallel unstable sort, resolving the earlier pair-materialization note | ℹ️ Info | Was explicitly accepted for Phase 7 (T-07-05); now implemented under OUT-01/OUT-02 |
| `src/count/engine.rs` | — | Single-producer pipeline is the parallel-stage bottleneck (producer ≈ 100% of the parallel count wall) | ℹ️ Info | Predicted by 07-RESEARCH (producer ~5.4 s budget); parallel extraction is the documented next lever, not built |

**Anti-patterns:** 0 blockers, 0 warnings, 5 informational.

### Human Verification Required

N/A — infrastructure/foundation phase with no user-facing elements. All acceptance criteria (engine shape, exactness, extractor semantics, gates, measurement) were verified programmatically and by re-execution; `behavior_unverified` is 0. Per the infrastructure-phase rule, no artificial manual steps are invented.

### Gaps Summary

**No gaps found.** The phase goal is achieved as scoped by the roadmap Note and remains achieved on the current tree:

- CLI counting runs through ONE shared engine (`src/count/engine.rs`) at every thread count; the old per-chunk rayon hot loop is gone. The ENGINE-01 dual-surface half is now complete: `PyCounter::add_from_*` builds the same engine (Phase 9).
- The engine is one producer on the caller thread → N persistent named OS workers over disjoint splitmix64 hash-range partition tables with bounded per-worker queues and a file-boundary flush/ack barrier; `--threads 1` is a true sequential path with no extra thread. The live observer reports exactly 2/9/33 OS threads and the pool-size suite is green.
- The producer/consumer overlap is measured (workers' busy time fits inside the producer wall) and the engine is honestly recorded as producer-bound — the research-documented next lever.
- One `for_each_window` extractor implements skip-N for the CLI and PyO3; Python now shares D2 (Phase 9) without a second extraction loop.
- Exactness is preserved: pinned slice parity, identical sorted `.rkdb` bytes across t1/t4/t16 (recorded on the slice and re-checked on a current-tree fixture), disjointness/conservation property tests, and the verbatim overflow contract at every new summation site.
- The PROF-02 gate is GREEN on the recorded artifact and reproduced GREEN on the current tree; all standing gates (MSRV clippy both crates, full locked suite, 571-test harness suite, PyO3 pytest) are green. The honest caveat is that the current-tree synthetic ratio improvement includes Phase 8's output-stage work, and the slice measurement was not re-executed on the contended host.

The report's previous digest went stale because Phases 8 and 9 changed `src/cli/commands/count.rs`, `src/count/engine.rs`, `src/hash/local.rs`, `pyo3/src/counter.rs`, and `pyo3/tests/test_counter.py`. All those changes are accounted for above; none regressed a Phase 7 truth.

### Verification Metadata

**Verification approach:** Goal-backward against ROADMAP Phase 7 success criteria merged with the four plans' frontmatter must-haves, re-run on the current tree (HEAD `698522d`).
**Must-haves source:** ROADMAP.md success criteria + PLAN frontmatter (07-01..07-04).
**Automated checks:** MSRV 1.82 clippy both crates (exit 0), full locked Rust suite (exit 0; 32 test-result blocks), 571-test harness suite (OK, skipped=1), PyO3 pytest (179 passed/63 skipped), live thread observer (GREEN 2/9/33), current-tree fixture determinism (`.rkdb` and text sha identical across t1/t4/t16), synthetic scaling re-run (GREEN, supplementary), default/profiling engine probe checks.
**Human checks required:** 0.
**Not re-executed:** the 4M-read slice wall/RSS run (recorded evidence + unchanged counting code path; host saturated by concurrent harness runs). The supplementary scaling re-run's provenance caveat is recorded above.
**Total verification time:** ~75 min (including the stale-digest audit, gate re-runs, and the invalidated-then-isolated scaling attempt).

---

*Verified: 2026-11-14T04:20:47Z*
*Verifier: Claude (gsd-verifier)*
