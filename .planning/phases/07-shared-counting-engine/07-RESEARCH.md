# Phase 7: Shared Counting Engine - Research

**Researched:** 2026-11-12
**Domain:** High-performance Rust k-mer counting — shared CLI/PyO3 counting engine, parallel pipeline architecture, partitioned exact-u32 accumulation
**Confidence:** HIGH on the engine shape, partition scheme, and memory (measured this session); MEDIUM on the projected t16 wall-clock and scaling ratio (extrapolated from measured components, must be confirmed by the Phase 7 implementation run)

## User Constraints (no Phase 7 CONTEXT.md)

There is no `.planning/phases/07-shared-counting-engine/07-CONTEXT.md` (the directory was empty at research start). The binding inputs are the milestone dispatch and the ratified decisions D1/D2/D3, reproduced here because they constrain the design:

### Locked Decisions (from milestone dispatch + PROJECT.md)
- **D1 — parallelism-first (Stage A) is the milestone spine; minimizer/disk-backed is conditional Stage B.** The measured ~5x gap is ~3.5x parallel-scaling inefficiency x ~1.4x single-thread cost, not a data-structure problem. Phase 7 is the `src/count/engine.rs` phase.
- **D2 — unify CLI/Python N-read semantics on CLI skip-N.** Phase 7 implements the ONE skip-N window-extraction function; the Python-side semantic proof and documentation complete in Phase 9 (PY-01/PY-02). Phase 7 must not silently change Python output.
- **D3 — minimizer/disk-backed stays conditional (Phase 11).** Phase 7 must not build a disk-backed path, a new persistence engine, or a minimizer.
- **Guardrails:** exact `u32` counts with fail-loud overflow (verbatim messages); checked arithmetic in every new summation; `.rkdb` v2 byte-identity in sorted mode; single `format.rs` writer; frozen header literals and IN-03 meanings; public CLI/Python APIs frozen; MSRV 1.82; Python >= 3.11; existing dependency set (no new deps); dual surface through the shared core; practical RAM; benchmark honesty (parity before timing, provenance on every artifact).

### Claude's Discretion
- The producer/consumer primitive, queue capacity, batch/record grouping, partition-count formula, partition-to-worker mapping, and the end-reduction shape.
- Whether Phase 7 wires only the CLI or also adds the PyO3 bridge; the roadmap Note assigns the dual-surface completion to Phase 9, but ENGINE-01 names both consumers. This research recommends an engine API ready for both and Phase 7 CLI wiring (see Q6 and Open Questions).
- Whether the static partition scheme is kept or a dynamic work-stealing fallback is added; the evidence below recommends static for Phase 7 with a measured trigger for the fallback.

### Deferred Ideas (OUT OF SCOPE)
- Parallel/unstable output sort and streaming write — Phase 8 (OUT-01/02/03).
- PyCounter routing, D2 Python semantic change, `save_database` double-sort — Phase 9 (PY-01/02).
- minimizer/signature partitioning, disk-backed bins, `--max-memory` counting admission — conditional Phase 11 (MINIM-01..03).
- Counter hasher swap (foldhash), mimalloc, SIMD encoding kernels, parser swap, request/query-path optimization — explicitly out of scope.

## Project Constraints (from CLAUDE.md)

Actionable directives that bind this phase (the planner must verify compliance):

| Directive | Source | Phase 7 implication |
|-----------|--------|---------------------|
| Rust 1.82 MSRV, edition 2021; `rust-version = "1.82"` in both manifests; `clippy::incompatible_msrv` active under `-D warnings` | `.claude/CLAUDE.md` Version policy; `Cargo.toml:5` | Use only std APIs available at 1.82 (`thread::scope` is 1.63; `sync_channel` is 1.0); run `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` on BOTH crates |
| Existing dependency set; work within it, no new persistence engine | `.claude/CLAUDE.md` Constraints | No `crossbeam-channel`, no async runtime, no new crate. `std::sync::mpsc`, `std::thread`, existing `rayon`/`parking_lot`/`hashbrown` only |
| Preserve `.rkdb` v2 and public CLI/Python APIs | `.claude/CLAUDE.md` Compatibility | Engine result feeds the existing sorted writer; `KmerCounter` public API unchanged; engine adds public API only |
| Exact `u32` counts; fail-loud overflow with verbatim message; checked arithmetic everywhere | `.claude/CLAUDE.md`; milestone guardrails | Reuse `LocalKmerCounts::increment`'s checked semantics; aggregate totals/uniques with `checked_add`; new summation sites return the verbatim error |
| Dual surface through the shared core | `.claude/CLAUDE.md`; PROJECT.md | Engine lives in `src/` (rlib), used by CLI in Phase 7 and reachable from `pyo3` in Phase 9; no CLI-only logic in the engine |
| Library logging through `log`, no `println!`/`eprintln!`/`dbg!` outside `src/cli/` (`#![deny(clippy::print_stdout, print_stderr, dbg_macro)]`) | `src/lib.rs:1`; `.claude/CLAUDE.md` | The engine must not print warnings; the CLI receives per-batch skip counts and prints them |
| No `.unwrap()` in library code reachable from Python; convert errors to `PyErr` | `.claude/CLAUDE.md` Error Handling | Engine methods return `ProcessingResult`; workers return errors, never panic; `panic = "abort"` in release means panics abort |
| Rust doc comments: `//!` header, `///` items with `# Arguments/# Returns/# Errors`, runnable doctests; English-only strings (CJK gate) | `.claude/CLAUDE.md` Comments & Documentation | New public items need full docs; examples must compile (or be `rust,ignore` for file-dependent ones); no CJK strings |
| Python formatting: black line-length 88, isort black profile, mypy strict; PyO3 tests guard the native import | `.claude/CLAUDE.md` Python formatting | Only relevant if the PyO3 bridge is included; the core is Rust-only |
| Benchmark honesty: parity before timing, true per-rep cache_state, counterbalanced medians, provenance | ROADMAP guardrails | Engine measurements reuse `scripts/bench/` provenance and parity gates; never compare a warm-cache engine run to a cold-cache reference |
| Preserve `[profile.release]` `lto = true`, `codegen-units = 1`, `panic = "abort"` | `.claude/CLAUDE.md`; `Cargo.toml:111-114` | Do not add `panic = "unwind"` or profiling flags to the release profile; use a feature/env-gated debug counter if needed |

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ENGINE-01 | ONE counting entry point (`src/count/engine.rs`) consumed by both `execute_count` (CLI) and `PyCounter::add_from_*` (Python): a fixed rayon pool, a producer streaming records into a bounded queue, and N persistent workers counting into disjoint hash-range-partitioned thread-local tables with overlapped decompression (no per-chunk fork-join barrier). | Q1/Q2/Q4/Q6 below; recommended `CountEngine`/`CountResult` API; producer = caller thread, N persistent OS workers, N bounded `sync_channel` queues, 64 static partition tables (`P = min(256, max(64, threads))`), `CountResult::merge_into(&KmerCounter)` as the Phase 9 bridge |
| ENGINE-02 | The thread-scaling gate (PROF-02) is green after the engine — rustkmer's parallel-scaling efficiency materially improves toward jellyfish's and the slice wall-clock drops measurably (the ~3.5x lever). | Q3/Q5/Q8; measured component budgets (producer ~5.4 s, worker increment work ~19-21 s single-thread, partition tables 6.95 GB); projected t16 count phase ~6-8 s vs Phase 6 26.96 s total; validation plan requires the real engine measurement, not extrapolation |
| ENGINE-03 | ONE window-extraction function in the core implements the D2 skip-N semantics for both surfaces; the MultiGzDecoder multi-member gzip regression (v1.0 8102985) stays green. | Q6; `src/kmer/extract.rs::for_each_window` spec; existing `RollingEncoder` skip-N semantics reused; engine-level multi-member + trailing-garbage fixtures; Python keeps its pre-filter in Phase 7 so output is unchanged |

## Architectural Responsibility Map

This is a single-process Rust library/CLI (no network/service tiers). The relevant tiers are the core library's producer/worker threads and the thin CLI/PyO3 surfaces.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Input discovery, format detection, file opening | CLI/PyO3 surface | Core library I/O | The CLI already detects `.fa/.fq/.gz/.bz2/.xz` (`execute_count`); the engine opens through `DefaultCompressedFileReader` so both surfaces share decompression semantics |
| Decompression + record parsing | Core library — producer (caller) thread | — | gzip/bzip2/xz and `bio` readers are sequential; one producer overlaps them with counting |
| Window extraction + canonicalization | Core library — producer thread | — | One `for_each_window` function; the producer encodes once per window and routes keys, so workers never encode |
| Partitioned exact-u32 accumulation | Core library — N persistent worker threads | — | Disjoint hash-range tables; no shared table, no per-window atomics |
| Per-file stats / flush barrier | Core library — producer thread | Worker threads (ack) | Per-file statistics need a happens-before edge; per-worker ack channels provide it |
| End reduction / result aggregation | Core library — caller thread, optionally rayon | — | Workers return their tables; checked sums; `merge_into` may use rayon for the Phase 9 counter merge |
| Sorted output and `.rkdb` write | CLI surface + `database/format.rs` | — | Phase 7 keeps the existing sorted writer; Phase 8 owns the parallel/unstable sort and streaming write |
| PyO3 bridge | `pyo3/src/counter.rs` (Phase 9) | Core engine | `py.detach` + owned `Send` captures; `CountResult::merge_into` preserves the public `PyCounter` API |

## Summary

Phase 7 replaces the per-chunk rayon `fill -> par_iter -> clear` pipeline with a persistent producer/consumer engine. The evidence is unambiguous about what to build and what not to build. The current pipeline spends ~58-60% of CPU in kernel spin/wait around per-chunk barriers, ~36-38% in shared DashMap increments, and only ~0.09% in gzip and ~3% in encoding (`.planning/research/profiling/evidence.json`; ARCHITECTURE.md). Phase 6 removed the per-window global atomics and sped the hot path, but left the structural barrier and the per-worker table memory: slice t16 is 26.96 s with 25.1 GiB peak RSS, versus jellyfish 13.29 s at 6.68 GiB (`.planning/phases/06-parallelism-correctness-hot-path/phase6_slice_green.json`).

This session measured the three quantities that decide the engine design on the real 4M-read slice (599,294,679 bases, 519,271,168 k21 windows, 229,694,874 distinct canonical):

1. **Single-producer throughput is sufficient.** Decompress+parse = 1.81-1.93 s (2.1-2.2M records/s); rolling extraction + canonicalization + splitmix routing = 3.60 s for 519M windows (144M windows/s, 126.6k batches of 4096 keys); extract-only = 0.354 s (1.47B windows/s). A fused producer budget of ~5.4 s is below any plausible t16 count phase.
2. **A strong mixer is mandatory.** 64-way partitioning of the canonical key by raw top bits gives max/mean = 3.54; splitmix64 gives max/mean = 1.02 on windows and 1.00 on distinct keys. Raw bits would create a 3.5x straggler.
3. **Disjoint partitioned tables solve the memory problem.** A streaming single-thread probe that reads, extracts, routes, and increments all 519M windows into 64 `LocalKmerCounts` tables holds exactly 519,271,168 total / 229,694,874 unique at **6,949,748,736 bytes peak RSS (6.95 GB / 6.47 GiB)** — versus **25.1 GiB (26.95 GB)** for the Phase 6 t16 slice. A single-thread variant with retained reads measured 22.97 s and 7.69 GB; the clean streaming run measured 26.10 s (19.9M windows/s).

**Primary recommendation:** Build `src/count/engine.rs` as a single-producer / N-persistent-worker pipeline: the caller thread reads/decompresses/parses records, calls ONE `for_each_window` extractor, routes each emitted key by `splitmix64` into a fixed **64 hash-range partitions** (`P = min(256, max(64, threads))`), and sends 4096-key partition-tagged batches over **N bounded per-worker `std::sync::mpsc::sync_channel` queues** (one queue per worker); each worker owns a contiguous set of partition tables (`LocalKmerCounts`, dense u64 for k <= 32 / wide u128 for k > 32) and never touches another worker's table. Keep the global rayon pool (built before any rayon query by the existing `--threads` path) for the end reduction and Phase 8 sort, but do NOT run blocking queue receives inside rayon tasks. Use the sequential path when `threads == 1` so the t1 baseline is a true single-thread measurement. Do not use dynamic work stealing in Phase 7: the measured producer is the pipeline bottleneck, so static partition ownership has ample headroom; add stealing only if the Phase 7 measurement shows a worker pacing the pipeline (documented trigger below).

## Design Decisions (research questions answered)

### Q1 — Engine architecture: persistent workers + bounded queue vs per-chunk rayon

**Decision: one producer (the caller thread) + N persistent OS worker threads + N bounded SPSC queues (one per worker, batches tagged with their partition); no rayon tasks for blocking work.**

Shape:

```
caller thread (producer)                        N persistent workers (std::thread)
┌──────────────────────────────┐   N queues    ┌──────────────────────────────┐
│ DefaultCompressedFileReader   │  sync_channel │ worker 0: LocalKmerCounts[0..P/N) │
│  -> bio fasta/fastq reader    │ ────────────► │ worker 1: LocalKmerCounts[P/N..2P/N) │
│  -> for_each_window per record│  (bounded,    │ ...                              │
│  -> splitmix partition route  │  batched)     │ each: increment key -> table     │
│  -> 4096-key batches          │               │ overflow -> Err (verbatim)       │
│ flush@file end -> per-worker ack               └──────────────────────────────┘
└──────────────────────────────┘
```

Why not the current per-chunk rayon `par_chunks(64).try_for_each_init` (count.rs:462-474): the producer fills a 4096-record chunk, blocks in `par_iter` until every rayon task finishes, then continues. The barrier strands fast P-cores waiting for E-core stragglers and prevents decompression from overlapping counting — the measured 58-60% spin/wait. Persistent workers plus a bounded queue remove the barrier entirely: the producer keeps producing while workers consume, and the only coupling is queue backpressure.

Why not run the workers as rayon tasks: rayon is a work-stealing pool; a task that blocks on `Receiver::recv()` holds a rayon worker and can starve the pool (rayon docs warn against blocking in tasks). Per-worker `sync_channel` receivers are `!Sync` and are moved into dedicated OS threads; this is the intended ownership model, not a workaround. The global rayon pool remains configured (the `--threads` path calls `build_global` before any rayon query) and is used only for non-blocking parallel reductions/sorts.

Queue choice: `std::sync::mpsc::sync_channel::<CountBatch>(QUEUE_BATCHES)` per worker. It is bounded, and `send` blocks when full, giving backpressure without an unbounded buffer. `SyncSender<T>` is `Send + Sync` for `T: Send` and can be cloned; `Receiver<T>` is `Send` but `!Sync`, so exactly one worker owns each receiver. This also makes future file-level parallelism trivial: multiple producer threads can clone the same per-worker senders and feed one receiver (multi-producer, single-consumer per queue). Verified from the official docs: "When the internal buffer becomes full, future sends will block waiting for the buffer to open up" ([CITED: doc.rust-lang.org/std/sync/mpsc/fn.sync_channel.html]); `SyncSender` is `Send`/`Sync` when `T: Send`, `Receiver` is `Send`/`!Sync` ([CITED: doc.rust-lang.org/std/sync/mpsc/struct.SyncSender.html], [CITED: doc.rust-lang.org/std/sync/mpsc/struct.Receiver.html]).

Batch/queue sizing (initial values; sweep in the measurement task):
- `KEYS_PER_BATCH = 4096` — matches the measured 126,642 batches for 519M windows; one batch is ~0.15-0.4 ms of worker work, so channel and flush overhead is amortized.
- `QUEUE_BATCHES = 8` per worker — dense 8 x 4096 x 8 B = 256 KiB/worker, 4 MiB at 16 workers; wide 8 MiB. The producer is slower than the workers in the measured regime, so queues stay near empty; capacity exists to absorb OS jitter.
- `RECORDS_PER_WARNING_BATCH = 4096` — preserves the existing one-warning-per-chunk behavior and wording ("Warning: Skipped N k-mer(s) with invalid characters in chunk").
- `P = min(256, max(64, threads))` — a **fixed 64-partition layout for the target machine** (P = 64 for t1/t4/t16), decoupled from the worker count. Each worker statically owns `ceil(P / threads)` contiguous partitions (for `threads = 16`, P = 64, four tables per worker; for `threads = 1`, one thread owns all 64). Fixing P at 64 matches the measured probe exactly (max/mean 1.00 on distinct keys, 6.95 GB, routing cost identical to 16 partitions), keeps the partition assignment identical across t1/t4/t16 so determinism/differentials compare like with like, and gives Phase 8's per-partition sort and Phase 11's bins a stable layout. The cap of 256 keeps the table count bounded; `max(threads)` ensures at least one partition per worker on very high-core hosts.
- `threads == 1`: sequential path, no queues, no worker threads; the caller reads, extracts, and increments into the P partition tables directly. This preserves the true t1 baseline and avoids a second thread inflating t1.

End reduction: workers return their `LocalKmerCounts` tables via `JoinHandle<ProcessingResult<Vec<LocalKmerCounts>>>`; the caller joins, sums per-table totals/uniques with checked `u64` adds, and builds `CountResult`. No atomics and no shared table are touched during counting. Per-file statistics use a `Flush { token }` batch sent to each worker plus a per-worker ack channel (`sync_channel(1)`) carrying `(token, total, unique)`; this gives the required happens-before edge and detects a dead worker by disconnection. The flush is a file-boundary barrier only, never per chunk.

### Q2 — Partitioning scheme: disjoint hash-range tables vs shared thread-local + merge

**Decision: static disjoint hash-range partitioning, one partition per key, a fixed `P = min(256, max(64, threads))` tables (64 on the target machine), workers own contiguous partition ranges. Reject shared thread-local + merge (the Phase 6 scheme) for Phase 7.**

The comparison, with the measured evidence:

| Scheme | Memory (4M slice) | Contention during counting | Load balance | Requirement fit | Verdict |
|---|---|---|---|---|---|
| Shared `DashMap` (v1.0-Phase 5) | 15.9-17.1 GiB pre-Phase 6 | Shard locks + DRAM cache-line bouncing + per-window atomics (measured 120.22 ns/window atomics share) | dynamic | No: shared table | Reject |
| Shared thread-local tables + end merge (Phase 6) | **25.1 GiB t16** (measured) | None during counting; merge/reduction tail | dynamic | Partial: N full tables | **Reject: N x memory** |
| Static hash-range partition tables (this design) | **6.95 GB / 6.47 GiB** (measured, 64 tables) | None: one owner per key, no shared writes, no atomics | static per worker; producer is the measured bottleneck | Yes: disjoint thread-local partition tables | **Adopt** |
| Dynamic batch stealing + per-partition locks | ~same table memory | Per-batch locks; collisions on the same partition | dynamic | Partial: tables migrate between workers | Fallback only |

Why partition tables solve the memory problem: in the Phase 6 scheme every worker accumulates into a full key-space table; with 16 workers the sum of per-worker distinct sets approaches N x the global table (measured 25 GiB vs 17 GiB pre-change). With hash-range ownership each key belongs to exactly one table, so the tables sum to one global table (measured 6.95 GB). Partitioning also removes the shared DashMap's per-shard control structures and its one-table power-of-two capacity slack (a single 229.7M-entry table rounds to 2^29 slots; 64 tables of ~3.6M entries round to 2^22 slots each, for roughly half the total slot count) — one reason the probe is both leaner and faster than the single-table path.

Why the mixer is mandatory: partitioning on raw key bits is dangerous for 2-bit packed DNA. On the real slice, the raw top-6-bits split had max/mean = **3.54** (p99/mean 3.54) while splitmix64 had **1.02** on windows and **1.00** on distinct keys. A 3.5x straggler partition would cap scaling regardless of queue design. The mixer is a standard splitmix64 finalizer over the folded key:

```rust
#[inline]
fn mix64(mut z: u64) -> u64 {
    z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    z ^ (z >> 31)
}

#[inline]
fn partition_of(key: u128, partitions: usize) -> usize {
    let folded = (key as u64) ^ ((key >> 64) as u64);
    let h = mix64(folded);
    ((h as u128 * partitions as u128) >> 64) as usize // uniform for any P, no division
}
```

`partition_of` is deterministic and depends only on the key and P; counts therefore do not depend on thread count. The probe verified the distribution on 519M real windows and on synthetic inputs. Poly-A is the known worst case: every window is the same key, so all of its increments go to one partition by definition (measured max/mean = 64 for a constant key). That is inherent to disjoint exact counting and is bounded in practice by the maximum count (the pinned slice's `Max_count = 58,609` per `parity_report.json`); a hot key's increments are cache-hot and cheap, and no correctness is at risk. No hot-key splitting or key replication is needed for Phase 7.

Determinism and conservation: because each key has exactly one owner, `sum(partition.total) == total` and `sum(partition.unique) == unique` are structural, not statistical. The property tests must assert (a) every key appears in exactly one table, (b) the union of the tables equals the single-thread reference map, (c) totals/uniques sum to the reference, and (d) the sorted `.rkdb` bytes are identical across t1/t4/t16.

Rejected alternatives:
- **Shared thread-local tables + merge** — measured 25.1 GiB; cost scales with worker count; rejected by ENGINE-01 and the memory guardrail.
- **Canonical-minimizer partitioning** — a memory-ceiling/KMC lever, not a speed lever; Stage B/Phase 11; no.
- **Dynamic work stealing in Phase 7** — see Q3: the producer is the bottleneck, so static ownership has headroom; stealing adds per-batch locks and migration complexity without a measured need.

Phase 11 compatibility: each partition's `LocalKmerCounts` is the natural disk-backed bin. A bin can be spilled/replaced without changing key ownership, the partition mixer, or the final merge, so this layout is the bounded-memory stepping stone the conditional Phase 11 reuses. The Phase 7 engine does not implement spill; it just keeps the bin boundary clean.

### Q3 — P/E-core scheduling on the M4 Max

Hardware: 16 logical cores = **12 P + 4 E** (`sysctl -n hw.perflevel0.logicalcpu` = 12, `hw.perflevel1.logicalcpu` = 4; `hw.ncpu` = 16). `available_parallelism()` reports 16 (the `--threads` fallback uses it at count.rs:884-886), so the default engine uses N = 16.

Guidance:
- **Keep the requested worker count; do not pin or exclude E-cores.** macOS offers no portable thread affinity; jellyfish reaches 8.9x on this machine with 16 unpinned threads. The OS scheduler is the right placement policy.
- **Batch coarsely.** 4096-key batches (~0.15-0.4 ms of worker work) amortize queue wakeups and prevent per-record/per-window channel chatter. This is the main lever against E-core straggler pacing: a slow worker consumes fewer batches, and the producer is not blocked because the queues rarely fill in the measured regime.
- **Do not use rayon work-stealing for the pipeline.** Blocking receives in rayon tasks are an anti-pattern and can deadlock the pool. Dedicated OS threads let the scheduler migrate/deschedule them naturally.
- **Static partition ownership is sufficient here.** The measured component budget is: producer ~5.4 s for the slice; extraction+routing ~3.6 s; increment work ~19-21 s on one thread (the preloaded `insert` mode measured 22.97 s total with ~3.6 s extraction/routing -> ~19.4 s of increments; the fused `insert_stream` run measured 26.10 s including ~1.9 s decompress+parse). At 16 workers the ideal worker time is ~1.2 s; even if the slowest E-core worker runs at ~0.6x the P-core rate, its share is ~2.0 s — still well below the producer's 5.4 s. The producer, not the E-cores, paces Phase 7.
- **Fallback trigger (documented, not built):** if the Phase 7 measurement shows the slowest worker's total processing time exceeds ~0.8 x the producer total (or the scaling gate is RED for a worker-bound reason), add dynamic batch stealing: a single MPMC batch queue plus per-partition `parking_lot::Mutex<LocalKmerCounts>` (one lock per batch, not per key; 64+ partitions keep collisions low). Do not add it speculatively.
- **Scaling-ratio honesty:** the PROF-02 gate is a regression gate (speedups >= 1.3), not the parity metric. Phase 6 measured slice t4 34.98 s vs t16 26.96 s (t16 better) and synthetic speedups t4 1.63x / t16 2.02x; the engine should preserve the t16 advantage because workers are persistent and the producer is no longer per-chunk-gated. If t16 regresses below t4, suspect queue/allocator contention or CI oversubscription, not the partition scheme. Because the engine also makes t1 faster (measured 26.10 s count-only for the engine-shaped single thread), the t1/t16 ratio may land around 2.5-4x rather than jellyfish's 8.9x, while the absolute t16 wall drops well below the Phase 6 baseline. Parity is judged by slice wall-clock against jellyfish 13.29 s in Phase 10. If the team wants the ratio itself closer to 8.9x, the lever is a parallel extraction stage (2-4 encoder threads feeding the same worker queues) or file-level producers (the queue API already supports multiple senders), not a different table scheme.

### Q4 — Producer/consumer overlap and multi-member gzip

**Decision: one producer on the caller thread; decode/parse/extract/route owned key batches; keep `MultiGzDecoder` unchanged; one producer is sufficient for Phase 7.**

Measured producer budget on the real slice:
- Decompress + parse: **1.81-1.93 s** for 4,000,000 records / 599,294,679 bases (2.1-2.2M records/s, 310-331M bases/s) through `DefaultCompressedFileReader` + `bio::io::fastq::Reader`.
- Extraction + canonicalization + splitmix routing: **3.60 s** for 519,271,168 windows (144M windows/s, 126,642 batches) — this is the production-shaped measurement (no histogram, flush check once per record). Extract-only is 0.354 s (1.47B windows/s), so routing costs ~6.2 ns/window; this is the dominant producer cost and the first tuning lever if the producer ever binds.
- Fused producer estimate: ~5.4 s for the slice, below the projected t16 count phase and far below the Phase 6 slice count phase.

Decompression is not the bottleneck: libz was 0.09% of CPU in the Phase 5 profiles, and the producer's only serialized I/O is ~1.9 s for 4M reads. Parallel inflate (pigz/rapidgzip class) remains out of scope and is unnecessary.

Handoff: the producer parses records on the caller thread and emits **owned batches of encoded keys** (`Vec<u64>` for k <= 32, `Vec<u128>` for k > 32) — never borrowed `bio::Record` values. This keeps the queue payload `Send`, avoids per-record allocation, and makes the worker path a tight increment loop. The producer owns a `Vec<Vec<u64>>`/`Vec<Vec<u128>>` routing buffer per partition; after each record it flushes any buffer that reached `KEYS_PER_BATCH`. Worst-case routing-buffer memory is `P x (KEYS_PER_BATCH + max_read_len)` keys: ~2.2 MB dense / ~4.3 MB wide at P = 64, and usually far less because only a few buffers hold a partial batch at a time. One batch `send` moves the `Vec`; a full queue blocks the producer (backpressure).

Multi-member gzip: the engine MUST open files through `DefaultCompressedFileReader::open_compressed`, whose gzip arm is `flate2::read::MultiGzDecoder::new(file)` ([VERIFIED: src/io/fastq.rs:78] — `let decoder = flate2::read::MultiGzDecoder::new(file);`). The docs confirm it "decodes a gzip file that may have multiple members" ([CITED: docs.rs/flate2/latest/flate2/read/struct.MultiGzDecoder.html]). Do not replace it with `GzDecoder`, do not hand-roll a member loop, and do not treat the trailing-garbage behavior as undefined: the existing regression pins loud failure on trailing non-gzip bytes ([VERIFIED: src/io/fastq.rs:782], test `test_read_all_errors_on_trailing_garbage_after_gzip_member`). Phase 7 adds engine-level end-to-end fixtures:
1. A two-member `.fastq.gz` (2 records in member A + 3 in B) counts exactly the concatenation of both members.
2. A one-member `.fastq.gz` followed by literal garbage returns an error carrying the file context (no silent truncation, no panic).
3. The same fixtures at t1 and t4 (sequential and parallel paths) produce identical counts.

Is one producer enough? Yes for Phase 7. The throughput ratio is deliberate: the producer's ~5.4 s is faster than the single-thread worker path (~19-21 s) but slower than the ideal 16-worker worker path (~1.2-2 s), so the producer is the binding stage in the parallel engine — and at ~5.4 s it still finishes well inside the target window. The producer's ~5.4 s is below the Phase 6 slice count phase and below the projected worker-bound time; the pipeline wall should be producer-bound at ~6-8 s. If Phase 7 measurement shows workers faster than the producer (possible after further tuning), the next lever is 2-4 extraction threads between the reader and the workers, or multiple file-level producers; the per-worker `sync_channel` senders are already `Clone + Sync`, so file-level parallelism needs no queue redesign.

### Q5 — Atomics vs bandwidth at DRAM scale

Phase 5's attribution at 18M distinct was: global atomics 120.22 ns/window (115.2% of the shared-vs-local gap), bandwidth share -15.82 ns (recorded as inconclusive, never clamped), t16/t1 multiplier 1.877 (`contention_evidence.json`, 05-05 summary). The engine design makes the atomics question moot: each key is incremented by exactly one worker into a private table, so there are no shared atomic RMWs, no per-window `fetch_add`, and no shared cache-line bouncing during counting. The only atomics left are optional (`AtomicBool` error/stop flags checked once per batch); per-file statistics arrive over channels after quiescence, not via atomics.

The remaining cost is DRAM random access into the partition tables. The new single-thread streaming probe measures the full shape at 229.7M distinct: **26.10 s for 519M windows (19.9M windows/s)** including decompression, parsing, extraction, routing, and increment, at **6.95 GB** peak RSS. That is ~50 ns/window end-to-end and shows no bandwidth cliff at the DRAM scale — the partitioned layout is cache/allocator-friendlier than the single shared table (smaller per-table capacity slack, no shard locks, no atomics). At t16 the partitions are disjoint, so workers do not share cache lines; whatever bandwidth remains is parallelizable and is exactly what the Phase 7 measurement must quantify.

Recommendation: no software prefetch hints in Phase 7. Hash-table lookups are pointer-chasing; software prefetch would require a batch lookahead and has no measured basis here. No hasher swap (foldhash stays a hypothesis-grade experiment, out of scope). The engine's measurement task must record ns/window at t1/t4/t16 and compare against Phase 5/6; if scaling is unexpectedly poor, profile with samply to attribute producer vs worker vs memory, then consider the Q3 fallback, not a speculative prefetch.

### Q6 — Dual surface and the ONE window-extraction function (D2)

**ONE function:** `src/kmer/extract.rs` (new core module):

```rust
pub struct WindowSummary { pub emitted: u64, pub skipped: u64 }

pub enum WindowError<E> { InvalidK(usize), Emit(E) }

/// Emit every valid k-mer window of `seq` with D2 skip-N semantics.
/// k <= 32 uses the rolling encoder; k 33..=64 uses the per-window u128
/// reference encoder. Any non-ACGT byte resets the window; each call starts
/// fresh, so no window spans a record boundary.
pub fn for_each_window<E, F>(
    seq: &[u8],
    k: usize,
    canonical: bool,
    emit: F,
) -> Result<WindowSummary, WindowError<E>>
where
    F: FnMut(u128) -> Result<(), E>;
```

Implementation delegates to the existing `RollingEncoder` for k <= 32 (verified: masked to 2k bits, reset at every non-ACGT byte and every call; `src/kmer/encoding.rs:443-499`, `try_for_each` at 586-591) and to `encode_kmer_bytes_u128` + `canonical_kmer_u128` for 33..=64. `emitted` is the number of valid windows; `skipped` is the count of windows containing a non-ACGT byte. The producer's sink is infallible (`E = Infallible`); `WindowError::InvalidK` maps to `KmerError::InvalidKmerSize` at the engine boundary; `Emit` propagates the first sink error (needed by `add_sequence`, which must abort on counter overflow exactly as today).

Wiring:
- **CLI/engine (Phase 7):** delete the encoding/canonicalization body of `count_record_into` and call `for_each_window`; the CLI output remains identical because the CLI already uses skip-N through `RollingEncoder`.
- **PyO3 (Phase 7, behavior-preserving):** route `process_sequence_into_local` (and `add_sequence`'s window loop) through `for_each_window` **after** the existing non-ACGT byte pre-filter. Python output on N-containing reads stays exactly as today; the D2 semantic change and its documentation are Phase 9 (PY-02), per the roadmap Note. This makes the function the only extraction implementation without silently changing Python.
- **PyO3 (Phase 9):** remove the pre-filter and document the output change for N-containing reads.

Dual-surface engine bridge (Phase 9, but design it now): `CountResult::merge_into(&KmerCounter) -> ProcessingResult<()>` merges the disjoint partition tables into an existing shared counter using the already-tested `KmerCounter::merge_local_counts` (checked per-key sums, atomic CAS total publication; `src/hash/table.rs:381-502`). Then `PyCounter::add_from_fastq`/`add_from_fasta` become: clone `Arc<RustPyCounter>`, `py.detach` with owned path/counter captures, create an engine with the counter's k/canonical/threads, `count_file`, `merge_into`, return. The public `PyCounter` API is unchanged. `add_kmer` stays a direct `KmerCounter::increment`; `add_sequence` uses `for_each_window` with a counter-increment sink (Phase 9 removes its pre-filter too).

Note on ENGINE-01 wording: the roadmap Note assigns the dual-surface completion to Phase 9 (PY-01). Phase 7 should build and wire the engine for the CLI, and may add the behavior-preserving PyCounter bridge if budget allows; it must not change Python N semantics early. The API above makes the Phase 9 bridge a thin adapter, not a second engine.

### Q7 — Exactness, `.rkdb` v2, and determinism

- **Per-key counts:** each partition table is a `LocalKmerCounts`, so `increment` inherits the exact semantics: `*count == u32::MAX` returns the verbatim `K-mer count overflow reached maximum value <max>` and leaves the count at the ceiling; a successful increment advances the local total by one; a fresh key advances unique by one; WR-03 "failed increments do not advance the total" is preserved ([VERIFIED: src/hash/local.rs:152-208]; verbatim message at 342-347, and the same text at `src/hash/table.rs:308-313`). Do not write a second increment implementation in the engine.
- **Aggregate totals:** after joining workers, sum per-table `u64` totals and uniques with `checked_add`; on overflow return a fail-loud error (reuse the existing "Total k-mer count overflow during local reduction" wording at `src/hash/table.rs:464-467`, or a new explicitly tested message). The per-file flush ack sums are also checked. This is a new summation site: test it with seeded `u64::MAX` values.
- **Skipped windows:** counted by the single producer, so the total is exact and no shared counter is needed. Per-4096-record warning batches preserve the existing wording and frequency.
- **`.rkdb` v2 byte identity:** the engine emits the same exact `(u128, u32)` pairs; the CLI keeps the existing sorted binary path (`sort_by_key` by key, then the frozen header and entry writers). The header stays 42 bytes: `DATABASE_MAGIC` = `b"RKDB"`, `DATABASE_VERSION` = `2` ([VERIFIED: src/database/format.rs:11-14] — `pub const DATABASE_MAGIC: &[u8; 4] = b"RKDB";` and `pub const DATABASE_VERSION: u16 = 2;`); entries stay 16-byte LE `u128` + 4-byte LE `u32` ([VERIFIED: src/database/format.rs:308-311] — `writer.write_u128::<LittleEndian>(self.kmer)?; writer.write_u32::<LittleEndian>(self.count)`). The header `total_kmers` remains the RECORD count (`kmer_count`), not the sum of counts (IN-03), as today.
- **Determinism:** sorted output is identical across runs and thread counts. Partition assignment depends only on the key and P; on the target machine P is fixed at 64 for t1/t4/t16 (it only grows above 64 threads), so the partition layout is identical across the measured thread counts. Counts and the globally sorted pair sequence are independent of thread count regardless. Tests must assert identical `.rkdb` sha256 at t1/t4/t16, not merely equal maps. `--no-sort` remains iteration-order dependent (as today) and is not a determinism target.
- **Golden discipline:** the Phase 5 golden manifest is immutable; never regenerate it to make a diff green. The engine must pass `tests/golden_sha256_tests.rs` and the CLI differentials unchanged. The pinned slice parity (Distinct 229,694,874 / Total 519,271,168) must pass before any timing.
- **Public API freeze:** `KmerCounter`'s signatures and `.rkdb` bytes are unchanged. `LocalKmerCounts` gains only an additive `get_count` accessor (needed by `CountResult::get_count`); `src/count/` and `src/kmer/extract.rs` are new public modules.

### Q8 — Highest-risk choices and validation evidence

| # | Risk | Why it is risky | Evidence needed before committing | Mitigation |
|---|------|-----------------|-----------------------------------|------------|
| R1 | Single producer becomes the wall (measured ~5.4 s/slice) | If workers scale better than expected, the pipeline is producer-bound and the wall stops dropping | Engine-internal producer/worker timing (feature-gated counters) in the first measurement task; if producer > ~0.7 x t16 count wall, add 2-4 extraction threads or file-level producers | Parallel extraction stage; per-worker senders are already multi-producer-capable |
| R2 | E-core straggler pacing with static partitions | Static ownership cannot rebalance if a worker is much slower | Per-worker processed-batch counts and times; slowest worker total vs producer total | Dynamic batch stealing fallback (single MPMC queue + per-partition `parking_lot::Mutex`) |
| R3 | Peak RSS regression from queues/results | The table win could be eaten by queue buffers or the `into_pairs` materialization | `/usr/bin/time -l` peak RSS at t1/t4/t16 on the slice, with and without output; target <= Phase 6 25.1 GiB, expected ~12 GB | Bounded queues; small batch buffers; Phase 8 removes the global pair materialization |
| R4 | Extraction semantics regression (N, lowercase, record boundaries, k > 32) | A second extraction copy or a rolling reset bug silently creates chimeric k-mers | Differential suite against the unchanged reference for k 1..=64, N at every position, lowercase, empty/short sequences, record pairs; engine CLI maps equal | One function; no duplicated encode loop; extend `kmer_rolling_differential_tests` |
| R5 | Multi-member gzip regression | Replacing `MultiGzDecoder` or reading members manually truncates real inputs | Engine-level 2-member fixture and trailing-garbage fixture, at t1 and t4 | Keep `DefaultCompressedFileReader`; add tests |
| R6 | Deadlock or swallowed worker error | Producer blocks on a full queue while a worker errors; ack/flush barrier can hang | Injected overflow and parse-error tests with timeouts; worker disconnect paths; no `unwrap` in workers | Shared stop flag checked per batch; `send` errors treated as worker failure; drop senders + join on every error path; `Drop` joins |
| R7 | Byte-identity / determinism | Partition order changes the pair order before sorting | Golden sha256 at t1/t4/t16; parity gate | Keep the existing sort/writer; assert sha256 equality across thread counts |
| R8 | Per-file flush tail | A file-boundary barrier on many small files could reintroduce a serial tail | Measure many-small-files workload; ack overhead is N messages per file | Flush only at file boundaries; consider a single final flush when per-file stats are not required |
| R9 | PROF-02 pool-size gate goes RED | The gate currently asserts total OS threads == requested + 1; the engine adds N workers | Updated observer counts both pools (see below) | **Do not widen/soften the gate**; update it to the new exact formula and add an engine-worker assertion |
| R10 | MSRV/CI drift | New code could use a post-1.82 API or break the PyO3 build | `cargo +1.82.0 clippy -D warnings` on both crates; `maturin develop --release` + pytest | Use only 1.82-stable std APIs; rebuild/version-assert before pytest |

**CRITICAL integration risk — the PROF-02 pool-size gate.** `tests/thread_pool_size_tests.rs` currently asserts, for each requested N in {1,4,16}, that the live CLI child has exactly `requested + 1` OS threads (`.planning/research/profiling/verify_threads.py`; assertion at `tests/thread_pool_size_tests.rs:218-222`: `observed == requested + 1`). The Phase 7 engine adds N worker threads, so the observed total becomes: `1 (main/producer) + N (engine workers) + N (rayon workers)` for N > 1, and `2` for N = 1 (sequential engine, no workers). The gate would go RED even though `--threads` is working correctly. Phase 7 MUST update the observer and its unit tests (`scripts/bench/tests/test_verify_threads.py`) to the new exact formula and assert both counts — e.g., label rayon threads and engine threads, or assert the total formula `2N + 1` for N > 1 / `2` for N = 1. This is a stronger gate than before (it proves both pools are sized), not a softened one. Never replace it with a self-report or a `>=` check. **Also fix the observer's polling race:** `verify_threads.py` currently polls only until the observed thread count exceeds 1 (`observe`, "Poll until the child's thread count exceeds 1"). With the engine, the process reaches `N + 1` (rayon + main) before the N engine workers spawn, so an early sample would record the intermediate count and produce a false RED. Poll until the observed count equals the expected total (or the timeout fires), and treat an observed count above the expectation as a measured mismatch. **Ensure the sampling window overlaps the counting phase:** the existing 100k-read debug fixture was chosen because the debug binary is slow enough to sample; re-verify that with the engine (workers exit at `finish`), or add an env-gated readiness marker the observer waits for. A timeout is exit 2, never a false PASS.

### Recommended engine API surface (`src/count/engine.rs`)

```rust
pub mod count; // src/lib.rs: pub mod count;

pub struct EngineConfig {
    pub k: usize,                    // 1..=64, validated
    pub canonical: bool,
    pub threads: usize,              // resolved worker count; 1 => sequential path
    pub initial_capacity: usize,     // --size hint, divided across partitions
    pub keys_per_batch: usize,       // default 4096
    pub queue_batches: usize,        // default 8 per worker
    pub records_per_warning_batch: usize, // default 4096
}

pub enum SequenceKind { Fasta, Fastq }

pub struct EngineStats {
    pub total_kmers: u64,            // SUM OF COUNTS (IN-03)
    pub unique_kmers: u64,           // distinct records
    pub skipped_windows: u64,
}

pub struct FileStats {
    pub stats: EngineStats,          // cumulative after this file
    pub skipped_batches: Vec<u64>,   // one entry per warning batch with >0 skips
}

pub struct CountResult { /* P partition tables + layout + stats */ }

impl CountResult {
    pub fn kmer_length(&self) -> usize;
    pub fn canonical_mode(&self) -> bool;
    pub fn stats(&self) -> EngineStats;
    pub fn get_count(&self, kmer: u128) -> Option<u32>;
    pub fn for_each_count<F: FnMut(u128, u32)>(&self, f: F);
    pub fn into_pairs(self) -> Vec<(u128, u32)>;           // Phase 7 output path
    pub fn filtered_pairs(&self, filter: &Option<CountFilter>) -> Vec<(u128, u32)>;
    pub fn filtering_stats(&self, filter: &Option<CountFilter>) -> FilteringResult;
    pub fn merge_into(&self, counter: &KmerCounter) -> ProcessingResult<()>; // Phase 9
}

pub struct CountEngine { /* senders, join handles, partition layout, stats */ }

impl CountEngine {
    pub fn new(config: EngineConfig) -> ProcessingResult<Self>;
    pub fn count_file(&mut self, path: &Path, kind: SequenceKind) -> ProcessingResult<FileStats>;
    pub fn stats(&self) -> EngineStats;                     // last flushed cumulative
    pub fn flush(&mut self) -> ProcessingResult<EngineStats>; // explicit file boundary
    pub fn finish(self) -> ProcessingResult<CountResult>;
}
// Drop: drop senders, join workers, ignore errors (no leaked threads).
```

Engine-internal modules (recommended split):
- `src/count/engine.rs` — `CountEngine`, producer loop, worker loop, flush protocol, error propagation.
- `src/count/partition.rs` — `mix64`, `partition_of`, `PartitionLayout { partitions, owners }`, unit tests for uniformity (random keys, non-power-of-two P, real/adversarial keys).
- `src/count/batch.rs` — `enum CountBatch { Dense { partition: u32, keys: Vec<u64> }, Wide { partition: u32, keys: Vec<u128> }, Flush { token: u64 } }` and `enum WorkerStat { Flush { token, total, unique } }`.
- `src/kmer/extract.rs` — `for_each_window`, `WindowSummary`, `WindowError`.

`execute_count` flow after the change:
1. Validate k / filters / inputs (unchanged).
2. Resolve threads and `build_global` (unchanged; before any rayon query).
3. Detect each file's `SequenceKind` (the existing `get_file_type` logic stays in `count.rs`).
4. `let mut engine = CountEngine::new(EngineConfig { ... })?;`
5. For each file: `let file = engine.count_file(path, kind)?;` print progress, skipped warnings from `file.skipped_batches`, and cumulative stats.
6. `let result = engine.finish()?;`
7. Apply the filter and call adapted `output_text_format(&result, ...)` / `output_binary_format(&result, ...)`; print final stats/filtering stats from `result`.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `std::sync::mpsc::sync_channel` | Rust 1.82 std | Bounded per-worker batch queue with blocking backpressure | Zero new deps; documented bounded semantics and correct `Send`/`Sync` split for one receiver per worker ([CITED: doc.rust-lang.org/std/sync/mpsc/fn.sync_channel.html]) |
| `std::thread` | Rust 1.82 std | N persistent worker threads + join handles | Blocking receives must not run on rayon's work-stealing pool; `std::thread` gives exclusive table ownership and join-based result collection (`std::thread::scope` is stable since 1.63 [CITED: doc.rust-lang.org/std/thread/fn.scope.html]) |
| `rayon` | **1.11.0** [VERIFIED: Cargo.lock:1297-1305] | Global pool sizing via the existing `--threads` path; end reduction; Phase 8 sort | Already a runtime dependency; the pool is built once with `build_global` and must not be queried first ([CITED: docs.rs/rayon/latest/rayon/struct.ThreadPoolBuilder.html]) |
| `hashbrown` | **0.14.5** [VERIFIED: Cargo.lock:696-704] | Partition tables via `LocalKmerCounts` (AHash dense/wide maps) | Existing dependency; the Phase 5/6 hot path already uses it; measured 6.95 GB for 229.7M distinct in 64 tables |
| `ahash` | **0.8.12** [VERIFIED: Cargo.lock:11-22] | Default hasher behind `hashbrown`'s `HashMap` | Existing; no hasher swap in this phase |
| `bio` | 2.0 (workspace dep) | FASTA/FASTQ record readers | Existing parser; parse cost is ~0.02% of CPU; no parser swap |
| `flate2` (`zlib`) | 1.x (workspace dep) | `MultiGzDecoder` — multi-member gzip | Existing; pinned by the v1.0 regression ([VERIFIED: src/io/fastq.rs:78]) |
| `byteorder` | 1.5 (workspace dep) | Little-endian `.rkdb` header/entry write | Existing frozen writer ([VERIFIED: src/database/format.rs:308-311]) |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `parking_lot` | **0.12.5** [VERIFIED: Cargo.lock:1067-1075] | `Mutex`/`Condvar` | Only if the dynamic-stealing fallback or a hand-rolled queue is chosen; the static SPSC design does not need it |
| `dashmap` | 6.2.1 | Existing `KmerCounter` storage; Phase 9 `merge_into` target | Not on the engine hot path; retained for the public counter and merge |
| `tempfile` | 3.12 | Existing test/merge temp lifecycle | Engine tests that need on-disk fixtures |
| `criterion` | 0.5 | Existing bench harness | Optional engine microbench; the standing slice bench is the primary evidence |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `std::sync::mpsc::sync_channel` | `crossbeam-channel` | Crossbeam offers MPMC + `select`, but it is **not in `Cargo.lock`** (only `crossbeam-deque`/`epoch`/`utils` arrive transitively via rayon), so it is a new dependency — rejected by the no-new-deps constraint. `sync_channel` is MPSC per queue, which is exactly the shape needed (one receiver per worker; multiple producers possible via cloned `SyncSender`) |
| Persistent OS workers | Rayon `scope`/`spawn` worker tasks | Blocking on a bounded queue inside a rayon task holds a work-stealing thread and can starve/deadlock the pool; rayon is for non-blocking CPU work only |
| Static partition ownership | Dynamic batch stealing + per-partition locks | Dynamic balances E-core skew, but adds per-batch locking and table migration. The measured producer is the bottleneck, so static has headroom; keep dynamic as the documented fallback (R2) |
| `splitmix64` range mapping | Raw key bits; `hash % P` | Raw bits are 3.54x skewed on real data (measured); `%` is a division per window. Splitmix + multiply-shift is uniform and branch-free |
| `LocalKmerCounts` | A new engine-specific table | Reimplementing increment/overflow would duplicate the exactness contract; reuse the tested type and add only `get_count` |
| Unbounded channel | `mpsc::channel` | Unbounded memory growth under a slow worker; violates the peak-RSS guardrail |

**Installation:** none. This phase adds no external packages. All builds/tests run `--locked`.

## Package Legitimacy Audit

**No external packages are installed or added by this phase.** The engine uses only the existing locked dependency set (`std` + rayon/hashbrown/ahash/bio/flate2/byteorder/dashmap/parking_lot). The package-legitimacy gate is therefore not applicable; the relevant integrity check is that `Cargo.lock` and both manifests are unchanged (except no dependency edits at all).

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| — (none) | — | — | — | — | — | No new packages |

**Packages removed due to SLOP verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

If the planner considers the dynamic-stealing fallback, it must still use `parking_lot` (already locked) — no new package. `crossbeam-channel` is explicitly rejected.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │ CLI: execute_count                                          │
                    │  validate k/filters/inputs                                  │
                    │  resolve_thread_count -> build_global (before any rayon)    │
                    │  detect file kinds                                          │
                    └───────────────┬─────────────────────────────────────────────┘
                                    │ EngineConfig { k, canonical, threads, size }
                                    ▼
┌───────────────────────────────────────────────────────────────────────────────────┐
│ CountEngine (src/count/engine.rs)                                                 │
│                                                                                   │
│  caller thread = PRODUCER                              N persistent workers      │
│  ┌─────────────────────────────────────────┐   N queues   ┌────────────────────┐  │
│  │ DefaultCompressedFileReader              │  sync_channel│ worker i           │  │
│  │  (MultiGzDecoder / bz2 / xz / plain)     │  bounded     │  owns partitions   │  │
│  │  -> bio fastq/fasta Reader.records()     │ ───────────► │  [i*P/N..(i+1)*P/N)│  │
│  │  -> for_each_window(seq,k,canonical)     │              │  LocalKmerCounts   │  │
│  │       (ONE core extractor, skip-N)       │              │  increment(key)    │  │
│  │  -> partition_of(key,P)  (splitmix64)    │              │  checked u32       │  │
│  │  -> per-partition Vec buffers            │              │  overflow -> Err   │  │
│  │  -> 4096-key CountBatch                  │              └────────────────────┘  │
│  │  flush at file end -> Flush{token}       │                                      │
│  │  collect per-worker ack stats            │                                      │
│  └─────────────────────────────────────────┘                                      │
│                                    │ finish (drop senders, join)                   │
│                                    ▼                                               │
│  CountResult { P x LocalKmerCounts, stats }                                        │
│    into_pairs() / filtered_pairs() / filtering_stats()   [Phase 7 CLI output]      │
│    merge_into(&KmerCounter)                              [Phase 9 PyCounter]        │
└───────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
        Existing sorted `.rkdb` writer (DATABASE_MAGIC "RKDB", version 2,
        42-byte header + 20-byte entries) — Phase 7 unchanged; Phase 8 owns
        parallel/unstable sort + streaming write.
```

### Recommended Project Structure

```
src/
├── count/                  # NEW: the shared counting engine
│   ├── mod.rs              # pub mod engine; pub mod partition; pub mod batch;
│   ├── engine.rs           # CountEngine, EngineConfig, CountResult, producer/worker loops
│   ├── partition.rs        # mix64, partition_of, PartitionLayout + uniformity tests
│   └── batch.rs            # CountBatch, WorkerStat, batch/flush protocol types
├── kmer/
│   ├── extract.rs          # NEW: ONE for_each_window (D2 skip-N), WindowSummary/WindowError
│   ├── encoding.rs         # unchanged RollingEncoder / reverse_complement_u64
│   └── canonical.rs        # unchanged canonical_kmer_u128
├── hash/
│   ├── local.rs            # + additive LocalKmerCounts::get_count
│   └── table.rs            # unchanged public KmerCounter (Phase 9 merge target)
├── cli/commands/count.rs   # engine wiring; output functions take &CountResult
└── lib.rs                  # + pub mod count; + pub use for the engine types (optional)
tests/
├── count_engine_tests.rs   # NEW: disjointness/conservation, t1/t4/t16 parity, multi-file
├── window_extract_differential_tests.rs # NEW: k 1..64, N matrix, boundaries (or extend rolling suite)
└── thread_pool_size_tests.rs # UPDATE: engine + rayon thread-count formula
```

### Pattern 1: Producer/consumer with bounded per-worker queues

**What:** The caller thread produces owned key batches; N dedicated workers consume from their own bounded queues and increment private tables.
**When to use:** CPU-bound consumers plus a serial I/O/parse stage, when the producer and consumers must overlap.
**Trade-offs:** Removes the per-chunk barrier and shared-memory contention; couples the producer to the slowest worker only through bounded-queue backpressure (acceptable here because the producer is the bottleneck).

```rust
// std 1.82; verified bounded-send semantics from the official docs.
let (tx, rx) = std::sync::mpsc::sync_channel::<CountBatch>(QUEUE_BATCHES);
let handle = std::thread::Builder::new()
    .name(format!("rustkmer-count-{i}"))
    .spawn(move || -> ProcessingResult<Vec<LocalKmerCounts>> {
        let mut tables = init_partitions(owned_partition_range, k, canonical, cap);
        while let Ok(batch) = rx.recv() {
            match batch {
                CountBatch::Dense { partition, keys } => {
                    let t = &mut tables[local_index(partition)];
                    for key in keys { t.increment(key as u128)?; }
                }
                CountBatch::Wide { partition, keys } => {
                    let t = &mut tables[local_index(partition)];
                    for key in keys { t.increment(key)?; }
                }
                CountBatch::Flush { token } => {
                    ack_tx.send(WorkerStat::Flush {
                        token,
                        total: tables.iter().map(|t| t.total_kmers()).sum(),
                        unique: tables.iter().map(|t| t.key_count() as u64).sum(),
                    }).ok();
                }
            }
        }
        Ok(tables)
    })?;
```

### Pattern 2: Hash-range partitioning with a strong mixer

**What:** Map each canonical key to exactly one partition via splitmix64 + multiply-shift; a worker statically owns a contiguous set of partitions.
**When to use:** Contention-free exact accumulation with bounded memory.
**Trade-offs:** Static ownership cannot rebalance a slow worker; a strong mixer is required (raw bits measured 3.54x skew).

```rust
#[inline]
fn part(key: u128, p: usize) -> usize {
    let folded = (key as u64) ^ ((key >> 64) as u64);
    let mut z = folded;
    z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    z ^= z >> 31;
    ((z as u128 * p as u128) >> 64) as usize
}
```

### Pattern 3: One extraction function, record-boundary reset

**What:** All surfaces call `for_each_window(seq, k, canonical, emit)`; the function starts fresh per record, skips any window containing a non-ACGT byte, and uses the rolling encoder for k <= 32.
**When to use:** Any counting path (engine producer, PyCounter file/sequence helpers, tests).
**Trade-offs:** A fallible sink is required for overflow propagation; the producer's sink is infallible.

### Pattern 4: Sequential path for `--threads 1`

**What:** When the resolved count is 1, run the same producer/extraction/partition code on the caller thread with no queues or workers.
**When to use:** `--threads 1`, single-thread benchmarks, and deterministic debugging.
**Trade-offs:** Two code paths (sequential/parallel), but the per-record and per-key code is shared; this preserves a true t1 baseline and avoids an extra producer thread inflating t1.

### Anti-Patterns to Avoid

- **Per-chunk fork-join (`fill -> par_iter -> clear`):** the measured 58-60% spin/wait; replace with persistent workers + bounded queue.
- **Per-window global atomics / shared DashMap on the hot path:** measured 120.22 ns/window atomics share; each key must have one owner.
- **Blocking receives inside rayon tasks:** holds a work-stealing thread; can deadlock the pool.
- **Unbounded queues or buffer-all:** unbounded memory; violates the RSS guardrail.
- **Partitioning on raw key bits:** 3.54x measured skew on real data.
- **N full key-space thread-local tables + end merge:** the Phase 6 scheme; measured 25.1 GiB.
- **A second window-extraction implementation in the engine or PyO3:** reintroduces N/boundary drift; use `for_each_window`.
- **Replacing `MultiGzDecoder` with `GzDecoder` or a manual member loop:** silently truncates multi-member inputs.
- **Widening the pool-size gate to accommodate engine threads:** update the exact formula instead (R9); never soften a standing gate.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bounded queue + backpressure | Hand-rolled ring buffer with atomics | `std::sync::mpsc::sync_channel` | Documented bounded semantics; correct `Send`/`Sync` split; zero new deps |
| Thread pool / worker lifecycle | Custom work-stealing scheduler | `std::thread` + join; rayon only for non-blocking reductions | OS scheduling already handles P/E placement; custom stealing adds deadlock risk |
| Multi-member gzip | Member-by-member loop or magic-byte scanner | `flate2::read::MultiGzDecoder` via `DefaultCompressedFileReader` | Existing v1.0 regression; trailing-garbage behavior pinned |
| FASTQ/FASTA parsing | Byte-by-byte line parser | `bio::io::fastq::Reader` / `bio::io::fasta::Reader` | Existing; parse is 0.02% of CPU; edge cases handled |
| Exact count table | A new engine table | `LocalKmerCounts` (`hashbrown` dense/wide) | Tested increment/overflow semantics; measured memory |
| Rolling encode + revcomp | A second encoder | `RollingEncoder` / `reverse_complement_u64` | Differential-tested for k 1..=32; masked and N-reset |
| Overflow/checked summation | `saturating_add` / wrapping | `checked_add` + verbatim `ProcessingError` | Exact-count contract; fail-loud guardrail |
| Partition mixer | Ad-hoc `key % P` or raw bits | splitmix64 finalizer + multiply-shift | Measured uniform (1.00-1.02); no division per window |
| Poisoned-mutex recovery | Custom unsafe | `parking_lot::Mutex` (fallback only) or `lock_local`'s poison recovery | Existing patterns; no unsafe |

**Key insight:** every piece of this engine already has a tested in-repo or std implementation. The only genuinely new logic is the pipeline orchestration and the partition layout — keep it thin, and reuse the exactness/tests rather than duplicating them.

## Common Pitfalls

### Pitfall 1: The PROF-02 pool-size gate counts total OS threads
**What goes wrong:** The gate asserts `observed == requested + 1`; the engine adds N workers, so t4/t16 go RED even though both pools are correctly sized. A rushed fix widens the assertion to `>=` or deletes the gate.
**Why it happens:** The gate was written when rayon was the only pool; total thread count was a proxy for the rayon pool size.
**How to avoid:** Update the observer and its unit tests to the exact new formula: `1 (main/producer) + N (engine) + N (rayon)` for N > 1, and `2` for N = 1 (sequential engine). Name threads (`rustkmer-count-{i}`, rayon workers) so the counts are attributable. Fix the polling condition: wait until the observed count equals the expected total (not merely `> 1`), because the process passes through the `N + 1` intermediate state before the engine workers spawn. Keep it a hard equality; never soften it.
**Warning signs:** The test fails at t4/t16 only; someone proposes `observed >= requested + 1` or a self-reported pool size.

### Pitfall 2: `--threads 1` is no longer single-threaded
**What goes wrong:** Running one worker plus a producer thread makes t1 use two cores, corrupting the t1 baseline and the scaling ratio.
**Why it happens:** The pipeline shape naturally adds a producer thread.
**How to avoid:** Special-case `threads == 1` to the sequential path (producer == consumer, no queue, no worker threads).
**Warning signs:** The pool-size observer sees 3 threads at t1; t1 wall drops suspiciously; the scaling gate's t1 looks too fast.

### Pitfall 3: Producer blocks on a slow worker's queue (head-of-line)
**What goes wrong:** With static per-worker queues, a slow E-core worker's queue fills; the producer blocks, starving all other workers.
**Why it happens:** Bounded queues apply backpressure globally when one consumer is slow.
**How to avoid:** The measured producer is slower than the workers, so this is not expected in Phase 7; set `QUEUE_BATCHES` to absorb jitter (8-16), measure per-worker batch counts, and keep the dynamic-stealing fallback documented. Do not use unbounded queues as a "fix".
**Warning signs:** One worker's queue is persistently full; other workers idle; per-worker timing shows one straggler.

### Pitfall 4: Weak partition mixer / raw key bits
**What goes wrong:** One partition gets 3.5x the keys; scaling caps regardless of worker count.
**Why it happens:** 2-bit packed DNA keys are structured; poly-A and low-complexity windows cluster near zero.
**How to avoid:** splitmix64 + multiply-shift; measure max/mean on real and synthetic (poly-A, homopolymer, repeat) inputs; assert max/mean stays near 1 on distinct keys (poly-A's single-key concentration is inherent and acceptable).
**Warning signs:** One table's `key_count` is > 1.5x the mean; the slowest worker's batch count is much higher.

### Pitfall 5: N x memory from full key-space locals
**What goes wrong:** Each worker holds every key range; memory scales with worker count (25.1 GiB measured).
**Why it happens:** Thread-local tables without key-space partitioning.
**How to avoid:** One owner per key via hash-range partitions; assert the sum of table unique counts equals the global unique; measure peak RSS.
**Warning signs:** Peak RSS grows with `--threads`; sum of per-table unique counts exceeds the global distinct count (would indicate duplicate keys across tables — a bug).

### Pitfall 6: Extraction semantics drift
**What goes wrong:** A duplicated encode loop or a missing N/boundary reset silently counts chimeric k-mers.
**Why it happens:** The CLI and PyO3 currently have separate extraction code (and Python pre-filters Ns).
**How to avoid:** One `for_each_window`; differential tests for k 1..=64, N at every position, lowercase, empty/short sequences, record pairs; keep the Python pre-filter until Phase 9.
**Warning signs:** Engine counts differ from the Phase 6 CLI on N-containing reads; `.rkdb` golden differs.

### Pitfall 7: Multi-member gzip truncation / silent trailing-garbage acceptance
**What goes wrong:** Replacing `MultiGzDecoder` or reading only the first member truncates real archive inputs; accepting trailing garbage hides corruption.
**Why it happens:** `GzDecoder` decodes one member and stops at its EOF; a hand-rolled loop may ignore errors.
**How to avoid:** Keep `DefaultCompressedFileReader`; add engine-level two-member and trailing-garbage tests at t1 and t4.
**Warning signs:** Counts are a fraction of jellyfish's on a concatenated `.gz`; the trailing-garbage fixture returns Ok.

### Pitfall 8: Aggregate-sum overflow handled with wrapping/saturating arithmetic
**What goes wrong:** A new summation site (per-file ack sums, final total) silently wraps.
**Why it happens:** `sum()` / `+=` are unchecked; the per-key `u32` path is checked but the aggregate `u64` is easy to overlook.
**How to avoid:** `checked_add` on every aggregate; test with seeded `u64::MAX`; return the verbatim fail-loud error.
**Warning signs:** A test seeds `u64::MAX` and gets a wrapped small number; no test exercises the aggregate path.

### Pitfall 9: Worker error deadlock / swallowed error
**What goes wrong:** A worker returns on overflow; the producer blocks forever on a full queue or waits for an ack that never arrives.
**Why it happens:** The producer does not observe worker disconnection; the ack channel is shared and not disconnected when one worker dies.
**How to avoid:** Per-worker queues and per-worker ack channels; treat `send`/`recv` errors as worker failure; a shared `AtomicBool` stop flag checked per batch; drop senders and join on every error path; `Drop` joins; no `unwrap` in workers.
**Warning signs:** Tests hang instead of failing; `send` errors are ignored; a single ack channel serves all workers.

### Pitfall 10: File-boundary flush tail on many small files
**What goes wrong:** A `Flush`/ack barrier per file serializes the pipeline at every file.
**Why it happens:** Per-file cumulative stats require quiescence.
**How to avoid:** Flush only at file boundaries (not per chunk), ack with N messages (one per worker); if many tiny files dominate, consider one final flush and per-file producer-side counters. Measure a many-small-files workload.
**Warning signs:** Wall time scales with file count rather than data volume.

### Pitfall 11: `into_pairs` + stable sort materialization eats the memory win
**What goes wrong:** The engine tables are lean, then the CLI copies 229M pairs (4.6 GB) and stable-sorts them, so peak RSS stays high.
**Why it happens:** The Phase 7 output path is intentionally unchanged; Phase 8 owns the streaming/parallel output.
**How to avoid:** Accept the Phase 7 peak (~12 GB expected, still below 25.1 GiB), measure it, and let Phase 8 remove the materialization. Do not "fix" the sort in Phase 7 (scope boundary).
**Warning signs:** Peak RSS after counting is much higher than the table total; the sort shows as a serial tail.

### Pitfall 12: Panics in workers (`panic = "abort"`)
**What goes wrong:** A worker panic aborts the whole process in release; no error message, no partial result.
**Why it happens:** `unwrap`/indexing/asserts inside the worker path.
**How to avoid:** Workers return `ProcessingResult`; use checked arithmetic; no `unwrap`; `debug_assert`s only where the invariant is validated at construction. Tests run in dev (unwind) and can catch join errors; release must be panic-free.
**Warning signs:** `unwrap()` in `src/count/`; indexing a per-partition vec with an unchecked id.

## Code Examples

### Bounded per-worker queue with correct ownership (std 1.82)

```rust
// Source: std docs (bounded send blocks; SyncSender is Send+Sync for T: Send;
// Receiver is Send and !Sync), verified 2026-11-12.
use std::sync::mpsc::{sync_channel, Receiver, SyncSender};

fn spawn_worker(
    rx: Receiver<CountBatch>,
    tables: Vec<LocalKmerCounts>,
    ack: SyncSender<WorkerStat>,
    worker_index: usize,
) -> ProcessingResult<std::thread::JoinHandle<ProcessingResult<Vec<LocalKmerCounts>>>> {
    std::thread::Builder::new()
        .name(format!("rustkmer-count-{worker_index}"))
        .spawn(move || worker_loop(rx, tables, ack))
        .map_err(|e| ProcessingError::new(format!("failed to spawn counting worker: {}", e)))
}
```

### Flush protocol with per-worker acks (happens-before for per-file stats)

```rust
// Design pattern from this research; exactness from LocalKmerCounts.
let token = self.next_token;
for tx in &self.senders {
    tx.send(CountBatch::Flush { token })?; // bounded; workers drain
}
let mut total = 0u64;
let mut unique = 0u64;
for rx in &self.acks {
    let stat = rx.recv().map_err(|_| ProcessingError::new("counting worker disconnected"))?;
    let WorkerStat::Flush { token: got, total: t, unique: u } = stat;
    if got != token {
        return Err(ProcessingError::new("stale counting-worker ack"));
    }
    total = total.checked_add(t).ok_or_else(|| ProcessingError::new(
        "Total k-mer count overflow during local reduction"))?;
    unique = unique.checked_add(u).ok_or_else(|| ProcessingError::new(
        "Unique k-mer count overflow during local reduction"))?;
}
```

### One extraction function (D2 skip-N), used by the producer and PyO3

```rust
// Source: rotating encoder semantics from src/kmer/encoding.rs:443-499,
// try_for_each at 586-591; differential-tested in Phase 6.
pub fn for_each_window<E, F>(
    seq: &[u8],
    k: usize,
    canonical: bool,
    mut emit: F,
) -> Result<WindowSummary, WindowError<E>>
where
    F: FnMut(u128) -> Result<(), E>,
{
    if !(1..=64).contains(&k) {
        return Err(WindowError::InvalidK(k));
    }
    if k <= MAX_KMER_SIZE_IN_U64 {
        let enc = RollingEncoder::new(k, canonical).map_err(|_| WindowError::InvalidK(k))?;
        let mut emitted = 0u64;
        let skipped = enc.try_for_each(seq, |v| {
            emitted += 1;
            emit(v as u128).map_err(WindowError::Emit)
        })?;
        Ok(WindowSummary { emitted, skipped })
    } else {
        if seq.len() < k {
            return Ok(WindowSummary { emitted: 0, skipped: 0 });
        }
        let mut emitted = 0u64;
        let mut skipped = 0u64;
        for i in 0..=(seq.len() - k) {
            match encode_kmer_bytes_u128(&seq[i..i + k]) {
                Ok(v) => {
                    let v = if canonical {
                        match canonical_kmer_u128(v, k) {
                            Ok(c) => c,
                            // Unreachable for a validated k (1..=64); count it
                            // as skipped so the summary invariant holds.
                            Err(_) => { skipped += 1; continue; }
                        }
                    } else { v };
                    emit(v).map_err(WindowError::Emit)?;
                    emitted += 1;
                }
                Err(_) => skipped += 1,
            }
        }
        Ok(WindowSummary { emitted, skipped })
    }
}
```

### `CountResult::merge_into` (Phase 9 bridge, exact per-key checked sums)

```rust
// Uses the Phase 6 tested merge: per-key checked u32 + atomic CAS aggregate.
pub fn merge_into(&self, counter: &KmerCounter) -> ProcessingResult<()> {
    use rayon::prelude::*;
    self.tables.par_iter().try_for_each(|t| counter.merge_local_counts(t))
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-chunk `fill -> par_iter -> clear` with rayon | Persistent producer/consumer with bounded queues | Phase 7 | Removes the per-chunk barrier and the 58-60% spin/wait |
| Shared `DashMap` + per-window atomics | Disjoint hash-range partition tables + thread-local totals | Phase 6 (atomics) / Phase 7 (partitioning) | No shared writes, no per-key contention, bounded memory |
| N full key-space thread-local tables + merge | One table per hash-range partition | Phase 7 | Measured 6.95 GB vs 25.1 GiB on the 4M slice |
| Raw-key partitioning / `% P` | splitmix64 + multiply-shift | Phase 7 | Measured max/mean 1.02 vs 3.54 |
| Single-thread stable sort of 229M keys | Parallel/unstable sort + streaming write | Phase 8 (pending) | ~10 s serial tail removed |
| PyCounter sequential line loop | Shared engine + `merge_into` | Phase 9 (pending) | Python inherits the engine speed structurally |

**Deprecated/outdated:**
- `resolve_thread_count` using `rayon::current_num_threads()` as the fallback — Phase 6 fixed it; do not reintroduce any rayon query before `build_global`.
- Per-window `total_kmers`/`unique_kmers` `fetch_add` — removed in Phase 6; the engine must not bring them back.
- `par_chunks(64)` for the counting hot loop — replaced in Phase 7; keep `CHUNK_SIZE` only as the warning-batch size if desired.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `[ASSUMED]` One producer (~5.4 s/slice measured) is sufficient for Phase 7; the producer is the bottleneck, not the workers | Q1/Q4/Q8 R1 | If workers scale better than expected, the wall caps at the producer; mitigation: parallel extraction or file-level producers |
| A2 | `[ASSUMED]` Static partition ownership is sufficient; E-core imbalance is absorbed because the producer is slower than the slowest worker's share | Q2/Q3/Q8 R2 | If worker time grows, scaling caps at the slowest worker; mitigation: dynamic batch stealing |
| A3 | `[ASSUMED]` splitmix64 remains uniform on other human WGS inputs and adversarial composition | Q2/Pitfall 4 | Skewed partitions; mitigation: measure max/mean, add a skew-aware adaptive partition boundary (Phase 11 territory) |
| A4 | `[ASSUMED]` Peak RSS lands ~12 GB on the 4M slice (7 GB tables + ~4.6 GB pair materialization), below the Phase 6 25.1 GiB | Q8 R3 | A regression would violate the memory guardrail; measure at t1/t4/t16 |
| A5 | `[ASSUMED]` Phase 7 can wire only the CLI and leave the PyCounter bridge to Phase 9 per the roadmap Note, while ENGINE-01's "both surfaces" completes in Phase 9 | Q6/Open Q1 | A strict ENGINE-01 reading would require a PyCounter bridge in Phase 7; the API is ready, and a behavior-preserving bridge can be added if the verifier requires it |
| A6 | `[ASSUMED]` Keeping the existing sorted output path in Phase 7 is acceptable | Q7/Pitfall 11 | Peak RSS/time remains higher than the engine table; Phase 8 owns the output win |
| A7 | `[ASSUMED]` `--size` can be reinterpreted as a total pre-allocation hint divided across partitions | Q1/API | Users who rely on `--size` as an exact allocation see different initial capacity; it was always a hint |
| A8 | `[ASSUMED]` The measured probe (single-thread, 64 tables) predicts the multi-worker engine's behavior | Summary/Q5 | The real engine must be measured; probes are component evidence, not the engine |
| A9 | `[ASSUMED]` An E-core runs at roughly 0.6x a P-core for this workload; this factor is used only to bound the static-partition risk | Q3 | The headroom estimate changes, but the conclusion rests on the measured producer/worker budget; measure per-worker times |

## Open Questions

1. **Should Phase 7 add the PyCounter bridge or leave it to Phase 9?** — **RESOLVED**
   - Resolution (07-CONTEXT.md "Dual surface"): Phase 7 wires the CLI and exposes `CountResult::merge_into(&KmerCounter)` as the Phase 9 bridge; PyO3 routing stays in Phase 9 (07-03 only routes extraction through `for_each_window`, behavior-preserving). Never change Python N semantics before Phase 9.
   - What we know: ENGINE-01 names both consumers; the roadmap Note assigns the dual-surface completion (D2 proof and documentation) to Phase 9 (PY-01/PY-02).
   - Recommendation kept for the record: build the `CountResult::merge_into` API and wire the CLI in Phase 7; a behavior-preserving PyCounter bridge may be added later if the verifier requires it.

2. **What is the exact producer/worker split in the real engine?** — **RESOLVED**
   - Resolution (07-CONTEXT.md "Overlapped I/O"; 07-04 Task 2): measure it with the feature-gated `EngineDiagnostics`/`WorkerDiagnostics` probe (producer wall, per-worker batch counts/busy time, wall); no pre-optimization. If the producer exceeds ~70% of the t16 count wall, the documented next lever is parallel extraction or file-level producers.
   - What we know: probe components are 1.9 s decompress+parse, 3.6 s extraction+routing, and ~19-21 s single-thread increment work (directionally).
   - Recommendation kept for the record: first measurement task records producer wall, worker batch counts/times, and per-file flush time.

3. **What is the dynamic-stealing trigger threshold?** — **RESOLVED**
   - Resolution (07-CONTEXT.md Claude's Discretion + Deferred Ideas): dynamic stealing is not built in Phase 7. The trigger stays "slowest worker > 0.8x producer time, or a worker-bound RED gate"; 07-04 records the per-worker diagnostics that would expose it, and the fallback remains deferred.
   - What we know: static ownership is sufficient under the measured budget.
   - Recommendation kept for the record: implement dynamic stealing only on that measured trigger.

4. **Do per-file warnings need to be emitted during the file, or is after-file equivalent?** — **RESOLVED**
   - Resolution (07-CONTEXT.md Claude's Discretion): after-file via `FileStats.skipped_batches`; 07-01/07-02 pin the existing wording and one-warning-per-4096-record-batch frequency. No test requires interleaving.
   - What we know: the current CLI prints one warning per 4096-record chunk from the producer thread; the wording is pinned.
   - Recommendation kept for the record: if a test later requires interleaving, add a producer-thread callback.

5. **Is the 4x partition granularity optimal?** — **RESOLVED**
   - Resolution (07-CONTEXT.md "Partition scheme"): start with `P = min(256, max(64, threads))` (64 on the target machine); the partition unit tests pin determinism/uniformity and 07-04 measures the real engine. Further tuning is measurement-driven, not speculative.
   - What we know: 16 and 64 partitions have the same routing cost (~3.6 s); 64 gives max/mean 1.00 on distinct keys.
   - Recommendation kept for the record: measure routing, skew, and memory; tune within the plan.

6. **Does the existing CI runner class handle 2N+1 threads at t16?** — **RESOLVED IN DESIGN**
   - Resolution (07-CONTEXT.md "CRITICAL gate update"): keep the exact 2N+1 / 2 formula and run the full gate battery in 07-04 Task 3; if CI oversubscription regresses the t16 wall, fix placement/fixture or cap worker count at `available_parallelism` while honoring an explicit `--threads` — never weaken the pool-size observation.
   - What we know: the gate already oversubscribes 16 rayon threads on 2-4 core runners; the unmeasured part is only whether 33 threads (16 engine + 16 rayon + main) cause enough context switching to regress the t16 wall on CI.


## Runtime State Inventory

This is an internal hot-path restructure, not a rename/migration. The only persisted artifact is the `.rkdb` file, whose v2 byte layout is unchanged.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no database keys, collection names, or IDs reference the counting implementation. `.rkdb` content is defined by the input sequences and the frozen writer. | None; verify golden sha256 |
| Live service config | None — single-process CLI/library; no external service, no daemon, no config server. | None |
| OS-registered state | None — no scheduler tasks, launchd units, or process registrations. | None |
| Secrets/env vars | None new. The existing `RUSTKMER_THREADS` / `RAYON_NUM_THREADS` precedence chain is unchanged; `RUST_LOG` continues to control logging. | Keep the precedence chain and tests |
| Build artifacts / installed packages | The `pyrustkmer` extension embeds the core rlib; a Phase 7 core change requires a `maturin develop --release` rebuild before Python tests (Phase 9) to avoid a stale `.so`. The CLI binary is rebuilt by `cargo build --release`. | Rebuild + version-assert before pytest; no package reinstall |

**Canonical question:** after every file in the repo is updated, what runtime systems still have the old counting path cached or registered? Answer: none — the process is per-invocation; the only risk is the stale `pyrustkmer` `.so` on developer machines, which is a rebuild/setup concern, not a data migration.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Rust 1.82 toolchain | MSRV clippy/build | Yes | `rustc 1.82.0 (f6e511eec 2024-10-15)` | None needed; `rustup toolchain install 1.82.0` |
| Default Rust/cargo | Dev builds/tests | Yes | `rustc 1.101.0-nightly`, cargo 1.101.0-nightly | 1.82 is available for MSRV gates |
| Python 3.11+ | PyO3 build/tests | Yes | `.venv311` Python 3.11.14; system Python 3.13.11 | Use `.venv311` |
| maturin | PyO3 rebuild | Yes | 1.11.5 in `.venv311` | `pip install 'maturin>=1.0,<2.0'` |
| jellyfish | Parity reference | Yes | 2.3.1 (`/opt/homebrew/bin/jellyfish`) | Skip reference runs; synthetic parity still works |
| samply | Profiling if the engine misses the gate | Yes | 0.13.1 | No profiler; use phase timings |
| `/usr/bin/time -l` | Peak RSS evidence (macOS bytes) | Yes | macOS built-in | `/proc/<pid>/status` on Linux |
| Real dataset | Slice parity/timing | Yes | `CRR1936095_r1.part_001.fq.gz` (2,785,381,389 B) + part_006 (2,785,388,289 B) | Synthetic degradation ladder in CI |
| Crossbeam-channel | Not needed | No | — | `std::sync::mpsc::sync_channel`; do not add |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none blocking.

## Validation Architecture

`workflow.nyquist_validation` is `true` in `.planning/config.json`, so this section is required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Rust built-in `cargo test` + `proptest` 1.5 (workspace dev-dep); Python `pytest` >= 7 in `pyo3/tests/` (Phase 9 / optional bridge) |
| Config file | `Cargo.toml`, `pyo3/pyproject.toml` (`[tool.pytest.ini_options]`, coverage gate `--cov-fail-under=80`) |
| Quick run command | `cargo test --locked --lib --test thread_local_count_tests --test kmer_rolling_differential_tests` |
| Full suite command | `cargo test --locked` (26 suites, 432 passed / 0 failed / 4 ignored at Phase 6 close) |
| Harness gates | `python3 scripts/bench/thread_scaling.py --mode synthetic --reads 500000 --reps 3`; slice: `--mode slice --input "$SLICE" --slice-reads 4000000`; `python3 scripts/bench/bench.py --mode synthetic --parity-only`; `python3 -m unittest discover -s scripts/bench/tests -t .` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| ENGINE-01 | `execute_count` counts through `CountEngine`; no per-chunk `par_chunks` hot loop; engine CLI output equals the reference map at t1/t4/t16 | integration | `cargo test --locked --test count_engine_tests` (new) | ❌ Wave 0 |
| ENGINE-01 | Disjointness + conservation: every key in exactly one partition; sum totals/uniques = reference; union = reference map | property/integration | `cargo test --locked --test count_engine_tests disjointness_conservation` | ❌ Wave 0 |
| ENGINE-01 | Multi-file cumulative counts = elementwise sum of per-file runs (existing Phase 6 pattern extended to the engine) | e2e | `cargo test --locked --test count_engine_tests multi_file` | ❌ Wave 0 |
| ENGINE-01 | `--threads N` sizes both the rayon pool and the engine workers; update the observer formula | integration | `cargo test --locked --test thread_pool_size_tests`; `python3 -m unittest scripts.bench.tests.test_verify_threads` | ✅ update needed |
| ENGINE-02 | Thread-scaling gate GREEN after the engine; slice wall drops vs the Phase 6 baseline; counts identical | e2e/benchmark | `python3 scripts/bench/thread_scaling.py --mode synthetic --reads 500000 --reps 3`; slice run with provenance | ✅ gate exists; new evidence artifact |
| ENGINE-02 | Peak RSS measured at t1/t4/t16 on the slice; no regression vs Phase 6 25.1 GiB (target ~12 GB) | benchmark | `/usr/bin/time -l` around the slice arms; record max RSS in the scaling doc | ✅ harness supports RSS |
| ENGINE-02 | Pinned parity (Distinct 229,694,874 / Total 519,271,168) before timing | e2e | `python3 scripts/bench/bench.py --mode ... --parity-only`; slice parity report | ✅ exists |
| ENGINE-03 | `for_each_window` equals the reference for k 1..=64: N at every position, lowercase, record boundaries, empty/short, canonical on/off | differential | `cargo test --locked --test window_extract_differential_tests` (new) or extended rolling suite | ❌ Wave 0 |
| ENGINE-03 | Multi-member gzip counts all members; trailing garbage fails loudly; same counts at t1/t4 | integration | `cargo test --locked --test count_engine_tests multi_member_gzip` (new) | ❌ Wave 0 |
| ENGINE-03 | Python output unchanged in Phase 7 (pre-filter retained); D2 change documented/proven in Phase 9 | e2e | `pytest pyo3/tests/test_counter.py -q` after `maturin develop --release` | ✅ exists; Phase 9 updates |
| Exactness | Golden `.rkdb` v2 sha256 unchanged at t1/t4/t16; sortedness through both consumers | differential | `cargo test --locked --test golden_sha256_tests`; slice sha256 comparison | ✅ exists |
| Exactness | Per-key u32 overflow verbatim; new aggregate summation sites fail loud (seeded `u64::MAX`) | unit/integration | `cargo test --locked --test thread_local_count_tests`; new engine overflow tests | ✅ + ❌ Wave 0 |
| Exactness | Old-vs-new and 1-vs-N differential matrix (k x canonical), partitioned tables | differential | `cargo test --locked --test dense_differential_tests --test parallel_count_tests`; new engine matrix | ✅ + ❌ Wave 0 |
| MSRV/CI | 1.82 clippy on both crates; PyO3 wheel builds; full suite green | gate | `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` (root + `pyo3/Cargo.toml`); `maturin build`/`develop` | ✅ exists |

### Sampling Rate
- **Per task commit:** `cargo test --locked --lib` plus the suite touched by the task (engine tests, extraction differential, golden).
- **Per wave merge:** `cargo test --locked` full suite; `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` on both crates; `python3 -m unittest discover -s scripts/bench/tests -t .`.
- **Phase gate:** full suite; `thread_scaling.py` GREEN on synthetic; slice scaling + RSS + parity with provenance; golden sha256 at t1/t4/t16; engine MultiGz fixtures; PyO3 rebuild + `pytest pyo3/tests`; no stale binary/module.

### Wave 0 Gaps
- [ ] `tests/count_engine_tests.rs` — engine vs reference map, disjointness/conservation, t1/t4/t16, multi-file, overflow seeding, multi-member gzip, error propagation.
- [ ] `tests/window_extract_differential_tests.rs` (or extend `tests/kmer_rolling_differential_tests.rs`) — the full k/N/boundary matrix for `for_each_window`.
- [ ] `tests/thread_pool_size_tests.rs` update + `.planning/research/profiling/verify_threads.py` + `scripts/bench/tests/test_verify_threads.py` — the exact new thread-count formula (2N+1 for N>1, 2 for N=1), with thread naming.
- [ ] A test-only overflow seed path for aggregate sums (`CountResult` stats / `sum_checked`) mirroring `LocalKmerCounts::seed_count` and the Phase 6 ceiling tests.
- [ ] A small benchmark/probe instrument for producer vs worker timing (feature-gated counters or a standalone probe) so R1/R2 are measured, not guessed.
- [ ] No framework install needed: `cargo test`, `proptest`, `pytest`, `maturin` are present.

## Security Domain

`security_enforcement` is enabled (`security_asvs_level: 1`, `security_block_on: high`), so this section is required.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | No | No auth surface in a local CLI/library |
| V3 Session Management | No | No sessions |
| V4 Access Control | No | No multi-user access control; file permissions are the OS's |
| V5 Input Validation | Yes | Validate k (`1..=64`) before constructing the engine/extractor; file kind detection unchanged; compressed-stream errors propagate with file context; bounded batch/queue sizes; no input-length assumptions |
| V6 Cryptography | No (new) | No new cryptography; gzip/bzip2/xz decompression is existing and unchanged (`MultiGzDecoder`); no hashing used for security |
| V7 Error Handling & Logging | Yes | Fail loud with verbatim messages; no `unwrap` in library/worker paths; no partial silent success; logging via the `log` facade |
| V8 Data Protection | No | No secrets or PII; `.rkdb` is the user's data |
| V9 Communications | No | No network |
| V10 Malicious Code | Yes | No new dependencies; `--locked` builds; no unsafe in the new code; no global allocator |
| V12 Files & Resources | Yes | Bounded queues/batches; no temp-file changes in Phase 7; output path handling unchanged |

### Known Threat Patterns for the Rust counting stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed/truncated gzip or FASTQ/FASTA causes a panic or silent truncation | Tampering / DoS | `DefaultCompressedFileReader` + `bio` return `Result`; propagate with context; engine-level trailing-garbage fixture; no `unwrap` |
| Invalid k / out-of-range index in the extractor | Tampering | Validate k at the public boundary; `WindowError::InvalidK`; `debug_assert` only for construction-validated invariants |
| Integer overflow in per-key or aggregate counts | Tampering | `LocalKmerCounts` checked u32; `checked_add` for every u64 aggregate; verbatim fail-loud error; seeded-overflow tests |
| Unbounded memory from a hostile input | DoS | Bounded queues (8 batches/worker), 4096-key batches, no buffer-all; table memory is proportional to distinct keys by design (same as the pre-existing counter) |
| Data race / lost update in partitioned counting | Tampering | One owner per key; tables moved into worker threads; no shared mutable state during counting; channel/join happens-before; property tests |
| Deadlock/starvation (worker error, full queue, flush) | DoS | Per-worker queues/acks; disconnect detection; shared stop flag; drop-senders-then-join on every error path; `Drop` joins; timeout tests |
| Thread-count gate bypass (gate softened to accommodate engine threads) | Repudiation/Tampering | Keep the exact formula; count both pools; no `>=`, no self-report |
| Stale `pyrustkmer` `.so` shadowing the new core | Tampering | Rebuild `maturin develop --release`, assert module path/version before pytest (Phase 9) |

## Sources

### Primary (HIGH confidence)

- **In-repo source, read this session (file:line anchors):**
  - `src/cli/commands/count.rs:31` (`const CHUNK_SIZE: usize = 4096;`), `:371` (`const SUBSLICE_RECORDS: usize = 64;`), `:462-474` (`par_chunks` + `try_for_each_init`), `:875-888` (lazy `resolve_thread_count`), `:101-104` (`build_global`).
  - `src/hash/local.rs:54` (`const LOCAL_INITIAL_CAPACITY: usize = 8192;`), `:80-106` (`LocalKmerCounts` struct), `:152-208` (`increment`), `:269-276` (`iter`), `:342-347` (verbatim overflow message).
  - `src/hash/table.rs:40-46` (`CounterTable` Dense/Wide), `:253-324` (`KmerCounter::increment`), `:381-502` (`merge_local_counts`, checked + atomic CAS), `:526-560` (`reduce_local_counts`), `:588-595` (`get_all_counts`), `:308-313` (verbatim overflow message).
  - `src/kmer/encoding.rs:14-17` (`MAX_KMER_SIZE_IN_U64 = 32`, `MAX_KMER_SIZE_IN_U128 = 64`), `:388-398` (`reverse_complement_u64`), `:443-499` (`RollingEncoder`), `:586-591` (`try_for_each`).
  - `src/kmer/canonical.rs:64-77` (`canonical_kmer_u128` = min(forward, revcomp)).
  - `src/io/fastq.rs:78` (`MultiGzDecoder::new(file)`), `:639-705` (multi-member regression), `:782-810` (trailing-garbage regression).
  - `src/database/format.rs:11-14` (`DATABASE_MAGIC = b"RKDB"`, `DATABASE_VERSION = 2`), `:101-139` (`DatabaseHeader`), `:179-...` (`write_to`), `:294-311` (`KmerEntry::write_to` 16 B LE u128 + 4 B LE u32), `:640-...` (`from_kmer_pairs`).
  - `pyo3/src/counter.rs:371,416` (`py.detach` + owned captures), `:443-487` (`save_database` double sort), `:737-793`/`:806-858` (sequential file paths with N pre-filter).
  - `tests/thread_pool_size_tests.rs:218-222` (`observed == requested + 1`), `:130-231` (standing gate + characterization).
  - `Cargo.lock:1297-1305` (rayon 1.11.0), `:1067-1075` (parking_lot 0.12.5), `:696-704` (hashbrown 0.14.5), `:11-22` (ahash 0.8.12).
- **Phase 5/6 measured evidence:** `.planning/research/profiling/evidence.json`; `.planning/phases/05-measurement-regression-harness/contention_evidence.json`; `.planning/phases/06-parallelism-correctness-hot-path/phase6_slice_green.json`, `phase6_scaling_green.json`, `phase6_measurement.json`, `06-VERIFICATION.md`; `06-02/03/04/05-SUMMARY.md`.
- **This session's probe (measured 2026-11-12, outside the repo):** `/tmp/rk7-probe` (Cargo.toml + `src/main.rs`), built with `CARGO_TARGET_DIR=/Users/forrest/GitHub/rustkmer/target cargo build --release --offline`; commands and results:
  - `rk7-probe <part_001.fq.gz> 4000000 route2` -> load 1.810 s (2,210,434 records/s, 331,175,404 bases/s); route2 parts=16 3.596 s (144,412,627 windows/s), parts=64 3.613 s (143,736,208 windows/s).
  - `rk7-probe ... insert_stream` -> records 4,000,000; windows 519,271,168; skipped 23,511; total 519,271,168; unique 229,694,874; wall 26.102 s (19,894,015 windows/s); max_partition_unique/mean 1.00; peak RSS 6,949,748,736 B.
  - `rk7-probe ... insert` (retained reads) -> wall 22.966 s; peak RSS 7,690,862,592 B; total/unique exact.
  - Probe route mode (64 parts, histogram) -> max/mean 1.02, p99/mean 1.02; raw top-bits -> max/mean 3.54, p99/mean 3.54; poly-A -> max/mean 64 for both (single constant key); extract-only -> 0.354 s (1,465,828,893 windows/s).

### Secondary (MEDIUM confidence)

- Official Rust std docs: [`sync_channel`](https://doc.rust-lang.org/std/sync/mpsc/fn.sync_channel.html) (bounded sends block); [`SyncSender`](https://doc.rust-lang.org/std/sync/mpsc/struct.SyncSender.html) (`Send`/`Sync` for `T: Send`); [`Receiver`](https://doc.rust-lang.org/std/sync/mpsc/struct.Receiver.html) (`Send`, `!Sync`); [`thread::scope`](https://doc.rust-lang.org/std/thread/fn.scope.html) (stable 1.63, scoped borrowing).
- [`rayon::ThreadPoolBuilder`](https://docs.rs/rayon/latest/rayon/struct.ThreadPoolBuilder.html) (`build_global` once; second call returns `Err`; `build()` returns an owned pool).
- [`flate2::read::MultiGzDecoder`](https://docs.rs/flate2/latest/flate2/read/struct.MultiGzDecoder.html) (decodes multiple members).
- [`parking_lot::Condvar` 0.12.5](https://docs.rs/parking_lot/0.12.5/parking_lot/struct.Condvar.html) (pair with one mutex; `wait_while`; `notify_one`/`notify_all`; no spurious wakeups) — only for the fallback queue/stealing design.
- Project research docs: `.planning/research/SUMMARY.md`, `ARCHITECTURE.md`, `PITFALLS.md`, `STACK.md`, `FEATURES.md`.

### Tertiary (LOW confidence / assumptions)

- The P/E throughput model (E-core at ~0.6x a P-core) is an assumption used to bound the static-partition risk; it is not separately measured. The conclusion (static is sufficient) rests on the measured producer/worker budget, not on the 0.6 factor.
- Multi-host CI behavior with 2N+1 threads on 2-4 core runners is unmeasured; the plan must run the updated gate on the CI runner class.
- The exact producer/worker split of the 26.10 s single-thread probe is directional (decompression/parse vs extraction/routing vs increment were measured separately but not fused with instrumentation).

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — no new packages; locked versions read from `Cargo.lock`; std semantics verified from official docs.
- Architecture: **HIGH** for the engine shape, partition scheme, extraction function, and memory (measured components + full single-thread shape); **MEDIUM** for the projected t16 wall and scaling ratio (extrapolated; the plan must measure the real engine).
- Pitfalls: **HIGH** for the code-anchored items (duplicate extraction, MultiGz, pool-size gate, overflow, stale PyO3 module); **MEDIUM** for the P/E and CI-oversubscription items.

**Research date:** 2026-11-12
**Valid until:** 2026-12-12 (30 days; the engine measurement in Phase 7 supersedes the projections). Re-validate if the dependency lock, dataset path, or macOS/hardware changes.

---

*Phase: 07-shared-counting-engine*
*Research completed: 2026-11-12*
*Ready for planning: yes — engine shape, partition scheme, producer/consumer protocol, exactness/format plan, memory strategy, and validation evidence are specified; the plan must measure the real engine before locking the parity claim.*
