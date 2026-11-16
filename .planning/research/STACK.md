# Stack Research: Producer Parallelization (PEXT) for the Count Pipeline

**Domain:** k-mer counting engine — producer/extract-stage parallelization (v2.1 PEXT conditional phase)
**Researched:** 2026-11-16
**Confidence:** MEDIUM overall — web-sourced crate facts are LOW per the classify-confidence seam and are anchored against the repo's own `Cargo.lock` and two direct local experiments (HIGH); the recommendation itself does not hinge on any web-sourced performance number.

## The Decision This Stack Serves

The v2.0 Phase 7 finding is that the count pipeline is producer-bound: one caller thread runs decompress → FASTQ parse → `for_each_window` extraction → partition routing → bounded `sync_channel` sends, at ~99.99% of parallel wall, while the N persistent workers are mostly idle. This research answers: **what stack additions would a parallel-extraction implementation need, and which are worth it?**

**Headline answer: zero new dependencies are needed for the parallel-extraction implementation itself.** The one stack change worth considering is a *feature flag on the existing flate2 dependency* (the `zlib-rs` backend), and even that is conditional on measurement showing inflate matters more than the local ballpark says it does. Decompression parallelism on single-member gzip is the only thing that would genuinely require a new crate — and the candidate pool there is weak (one MSRV conflict, one unverifiable), while the local measurement says inflate is only ~5–15% of producer wall anyway.

---

## Recommended Stack

### Core Technologies (unchanged — this is the recommendation)

| Technology | Version (locked) | Purpose | Why It Stays |
|------------|------------------|---------|--------------|
| `std::thread` + `std::thread::Builder` (named threads) | Rust 1.82 std | Spawn persistent workers AND any new extractor/producer threads | The engine's documented contract already forbids rayon in blocking worker loops (a blocking `recv` can starve the pool); extractor threads blocking on bounded sends are the same hazard. Plain OS threads with names (`rustkmer-count-{i}` precedent → `rustkmer-extract-{i}`) preserve the contract |
| `std::sync::mpsc::sync_channel` | Rust 1.82 std | Bounded batch queues AND the new reader→extractor chunk channel | `SyncSender` is already clone-able multi-producer/single-consumer — exactly the extractor→worker fan-in shape. Multiple extractor threads can hold clones of each worker's sender with **no new crate and no new channel type**. Queue depth/backpressure semantics already validated in v2.0 Phases 7–9 |
| Existing `PartitionLayout` / `RoutingBuffers` / `for_each_window` | in-repo (`src/count/`, `src/kmer/extract.rs`) | Extraction + routing machinery, reused verbatim | Each new extractor owns its own `RoutingBuffers` set and its own clones of worker senders; batches may interleave in worker queues, but per-key counting is commutative and the sorted `.rkdb` writer output is identical — the exactness contract survives without any synchronization primitive being added |
| `rayon` 1.11.0 | locked | Finish/sort path only (already shipped, Phase 8) | No new rayon use on the producer path |

### The One Conditional Stack Change: flate2 backend switch

| Technology | Version | Purpose | When to Use |
|------------|---------|---------|-------------|
| `flate2` feature `zlib-rs` (replacing the current `zlib` feature) | flate2 1.1.8 (locked; current 1.1.11) pulls `zlib-rs` ^0.6.7 transitively | Faster single-threaded inflate — pure Rust, no C compiler, some internal unsafe | **Only if** the phase's profiling gate (below) attributes ≥ ~20% of producer wall to inflate. It is a feature-flag edit in `Cargo.toml`, not a new dependency edge from rustkmer itself |

Facts (LOW confidence, web — verify at integration with `cargo tree`/docs.rs): flate2's docs call `zlib-rs` "the fastest backend overall"; flate2 1.1.7+ depends on zlib-rs directly (no C-bindings path needed, and 1.1.8 — already in our lockfile — is the first release with the direct pure-Rust dependency). zlib-rs is 0.6.8 (Trifecta Tech Foundation), **MSRV 1.75 — compatible with our 1.82 gate**, license **Zlib** (permissive). Benchmark deltas from the project's own blog: inflate ~7–13% faster than zlib-ng at practical chunk sizes (16 B–64 KB), ~2–6% faster than Chromium's zlib. No published gzip-FASTQ decompression benchmark for flate2+zlib-rs exists; treat any win as unproven until measured on our workload.

**Why this is the only defensible "addition":** it changes one feature flag on a dependency we already pin; it pulls one transitive crate (plus `libz-rs-sys` is not even needed on the direct path); it is MSRV-clean; and it is reversible with a one-line diff if the measured win is noise. Everything else in the candidate pool fails a harder gate (see What NOT to Use).

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| None for extraction parallelization | — | — | **Zero-new-deps is feasible and recommended** for the parallel-extraction implementation: `std::thread` + `sync_channel` clones + existing routing cover multi-file producer-per-file AND record-chunk handoff (both patterns below) |
| Dev-only: Instruments Time Profiler (macOS dev host) / `perf record` (Linux CI) | system tools | Producer-phase attribution (inflate vs parse vs extract vs route) | Always, before choosing any of the variants |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `--features profiling` build (existing) | `EngineDiagnostics.producer_nanos` / `WorkerDiagnostics.busy_nanos` already exist; extend with extractor-id and per-phase timers | The measurement harness for the decision gate — no new tooling needed |
| `scripts/bench/bench.py` (existing) | Regression gate for any landed change | MEM guardrail (peak RSS < jellyfish at both k) must be re-verified; extractor record-chunk buffers add small bounded memory |

---

## Integration Points into CountEngine's Producer

Grounded in `src/count/engine.rs` (all line refs from the 2026-11-16 tree):

1. **`count_file_inner` (engine.rs:803)** is the single-producer loop: `DefaultCompressedFileReader::open_compressed` → `bio::io::fastq::Reader::records()` → `count_sequence` → `for_each_window` → `route_key` → `send_batch`. Two viable parallelization patterns hang off this loop:
   - **Pattern A — producer-per-file (multi-file).** A new `count_files(&[PathBuf], kind)` spawns E producer threads, one per input file (the benchmark ships 6 independent gzip parts — verified locally 2026-11-16), each running the *entire* producer loop with its own `RoutingBuffers` and `SyncSender::clone()`s of every worker queue. Zero coordination on the hot path; exactness is trivial (per-file skip sums reduced with the existing `checked_sum` pattern). Smallest diff, biggest fit with the real benchmark.
   - **Pattern B — record-chunk handoff (single large file).** One reader thread keeps the `MultiGzDecoder` + `BufReader`, fills ~1 MiB raw byte chunks aligned to FASTQ record boundaries (track the 4-line cycle), and hands them through a new bounded `sync_channel(2·E)` to E extractor threads; each extractor parses records from an in-memory cursor, runs `for_each_window`, routes into its **own** `RoutingBuffers`, and sends via cloned worker senders. This parallelizes parse AND extraction; decompression stays serial (unavoidable on a single-member stream — see below).
2. **Flush-token contract needs a design decision (the main integration subtlety).** `flush_pipeline` (engine.rs:1256) sends one `CountBatch::Flush{token}` per worker and reads one ack per worker from a 1-capacity ack channel. With E concurrent producers this serializes only if flushes can interleave. Correct-by-construction options: (a) producers only route; the caller thread performs all flushes after a producer-join epoch (recommended — preserves the existing "ack after every prior batch" FIFO reasoning verbatim); (b) make `next_token` global-unique and tag acks with producer id. The phase must pick one and pin it with a test before any benchmark.
3. **Exactness invariants the phase must re-prove (existing gates suffice):** per-key counts are commutative, so arbitrary inter-extractor batch interleaving yields identical tables; the t1/t4/t16 sha256-identical `.rkdb` golden gate and the 2N+1 differential (mutation-RED control) extend naturally to E-extractor counts. Overflow fail-loud is inherited because extractors reuse `route_key`/`LocalKmerCounts::increment` — nothing about the error contract changes.
4. **Profiling feature extension:** add extractor attribution (decompress / parse / extract / route / send) to `EngineDiagnostics` so the next profiling pass can re-verify the producer split after the change.

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `crossbeam-channel` 0.5.x (MSRV 1.60, MIT/Apache-2.0) | No capability gap: std `SyncSender` is already clonable multi-producer; benchmarks vs modern std are mixed (std bounded channels improved after the 1.67+ mpsc rewrite, and can win at larger capacities). The engine needs neither `select!` nor MPMC receivers. Adding a concurrency crate to a proven hot path is exactly the dependency-creep the stack constraint resists | `std::sync::mpsc::sync_channel` clones (already in the engine) |
| `rayon` on the producer/extractor path | The engine's own documented contract forbids blocking calls on rayon workers (starvation hazard); extractors block on bounded sends just like workers. rayon's fork-join model also fights the persistent-pipeline shape (no per-chunk barrier wanted) | `std::thread` with named builders |
| `paraseq` 0.6.3 (MIT, MSRV undeclared) | Integration model conflicts: it owns processing via its `ParallelProcessor` callback + private ThreadPool, whereas our workers own disjoint partition tables and the engine owns the loop. It also pulls `niffler` for transparent decompression — **niffler was already removed from this repo** ("to avoid zstd issues", Cargo.toml comment), and its decompression is a serial transparent step anyway, i.e. it buys nothing Pattern B doesn't already do in-repo | In-repo chunk handoff |
| `rapidgzip-core` 0.3.1 (BSD-3/MIT) — the one crate that genuinely parallelizes standard gzip | **MSRV 1.87 (edition 2024) hard-conflicts with `rust-version = "1.82"`** and the active `clippy::incompatible_msrv` `-D warnings` gate. Pre-1.0, decoder-only, evolving API. Taking it would require a user-ratified MSRV raise (precedent exists: 1.80→1.82 was ratified) **and** evidence inflate dominates — which it does not (profiling gate below) | Multi-file producer-per-file; `zlib-rs` backend if inflate ≥ 20% |
| `lgz` 0.3.17 (MIT/Apache-2.0) — pugz-style speculative gzip split | **No MSRV declared** (1.82 compat unverifiable pre-adoption); docs.rs builds x86_64-linux only while dev host + CI include macOS aarch64; single-maintainer pre-1.0; gains on files without sync-flush markers are modest (speculative path measured 527 MB/s vs 6,100 MB/s on marker files, on 32 cores) | Same as above |
| `gzp` 2.0.4 | Parallel **compression** library; its parallel decompression works only for Mgzip/BGZF block-delimited formats, not the standard single-member gzip our benchmark ships (verified single-member locally) | — |
| `libdeflater` 1.26.x (Apache-2.0) | Buffer-only API, **no streaming**: requires pre-allocated output and an upper bound on decompressed size — incompatible with streaming FASTQ reads of unknown size; the crate's own docs recommend flate2 for streaming | Keep flate2 |
| External-process route (`pigz -dc` / `pugz` CLI via pipe) | pigz does **not** parallelize decompression of standard gzip (its docs/paper are explicit); pugz is a research artifact (Kerbiriou & Chikhi 2019), not a maintained tool; an external-tool dependency in the harness wouldn't benefit the Python surface at all | In-process patterns above; harness-level pre-decompression only as a measurement aid |
| async runtimes (`tokio`, `async-compression`) | Nothing in this path is I/O-bound waiting; CPU-bound counting with bounded channels is the anti-case for async | Sync threads + bounded channels |

---

## Stack Patterns by Variant (the decision rule)

**Measure first — the profiling gate (this is the phase's first task):**

1. **Producer attribution** — build with `--features profiling`, run the real slice at t16 under Instruments/perf, split `producer_nanos` into inflate / bio-parse / extract+route / send+flush-wait.
2. **Plain-vs-gzip differential (no profiler needed)** — count the same slice as plain `.fastq` vs `.fq.gz` at `--threads 1`; Δwall ≈ decompression share.
3. **Local ballpark already measured (HIGH confidence — direct experiment on this machine, 2026-11-16):** a 256 MiB gzip slice of `CRR1936095_r1.part_001.fq.gz` decompressed to 1,169,883,136 bytes in 0.93 s wall / 0.87 s user → **≈1.2–1.3 GB/s single-threaded inflate** on FASTQ (ratio ≈ 4.56×). Full-scale v2.0: 144.69 s for ~23.7 GB of decompressed plain text → inflate ≈ 19 s ≈ **13% of total wall**; on the 4M-record slice it is ≈5%. Combined with `MultiGzDecoder` staying serial, **extraction+parse dominates the producer (~85%+)** — which is precisely why zero-deps extraction parallelization, not decompression parallelism, is the lever.
4. **Member scan (HIGH confidence — direct inspection, 2026-11-16):** all six benchmark parts are **single-member standard gzip** (1 `1f 8b` header each, verified by trailer walk). Intra-file parallel inflate would need pugz-style *speculative* decoding (research-grade, weak crate pool). Note: the split directory now holds **six** parts (~2.79 GB each, ~16.7 GB gzipped total) — PROJECT.md's "two parts, ~5.2 GB" description is stale; multi-file producer-per-file (Pattern A) has six independent files to spread across on the current layout.
5. **Backpressure sizing after the change** — with E extractors feeding N workers, workers stop being idle; measure `busy_nanos` per worker at E=4–6 and confirm N (worker count) still bounds correctly before claiming the win.

**If inflate < ~20% of producer wall (expected, per ballpark):**
- Pattern A (multi-file producer-per-file) + Pattern B (chunk handoff) with **zero new dependencies**. Skip the backend switch.

**If inflate ≈ 20–50%:**
- Pattern A/B **plus** the flate2 `zlib-rs` backend feature (one-line `Cargo.toml` feature change, transitive zlib-rs 0.6.x, MSRV-clean) — then re-run the gate to confirm the measured delta.

**If inflate > ~50% (contradicts the ballpark; would need explaining):**
- First exploit multi-file parallelism (six independent parts make single-file inflate far less binding).
- Only then surface the new-dependency question to the user: `rapidgzip-core` requires an MSRV raise to 1.87 (ratified-precedent path, but pre-1.0 risk); `lgz` is unverifiable on MSRV/platform. Recommend against both unless the measured ceiling justifies it.

**Predicted-win sizing (Amdahl, from measured numbers — MEDIUM confidence, to be re-derived by the phase):** producer ≈ 99.99% of t16 wall; extraction+parse ≈ 85% of producer. Perfect 4-way extraction split: producer 9.31 s → ~2.1 s → wall ~2.3 s on the slice (~4× producer shrink); full-scale 144.69 s → plausibly ~60–80 s, bounded afterward by worker increment capacity and the serial inflate tail. The MEM guardrail (peak RSS < jellyfish) must be re-verified — chunk buffers are bounded but worker tables still dominate.

---

## Version Compatibility

| Component | Compatible With | Notes |
|-----------|-----------------|-------|
| `std::thread` / `sync_channel` clones | Rust 1.82 (MSRV gate) | Clonable `SyncSender` is stable since forever; nothing newer used |
| `flate2` 1.1.8 (locked) + `zlib-rs` feature | zlib-rs ^0.6.7 → **MSRV 1.75** ✓ license Zlib | zlib-rs direct-dep path exists since flate2 1.1.7/1.1.8 — already in lockfile; flate2 1.1.11 is current, patch-level bump, verify build under 1.82 at integration |
| flate2 `zlib-ng` alternative | `libz-ng-sys` ^1.1.16, needs C compiler + cmake | Not recommended: zlib-rs is at parity-or-better and pure Rust |
| `rapidgzip-core` 0.3.1 | **MSRV 1.87 — FAILS the 1.82 gate** | Only path in if MSRV is user-raised |
| `lgz` 0.3.17 | MSRV undeclared — unverifiable | Also platform-skewed (docs.rs builds linux-x86_64 only) |
| `crossbeam-channel` 0.5.x | MSRV 1.60 ✓ MIT/Apache | Compatible but unnecessary — no capability gap |
| `paraseq` 0.6.3 | MSRV undeclared | Also rejected on architecture + niffler history |

**License check:** every candidate in the pool is permissive (zlib-rs: Zlib; rapidgzip-core: BSD-3/MIT; lgz: MIT/Apache-2.0; crossbeam-channel: MIT/Apache-2.0; paraseq: MIT; libdeflater: Apache-2.0). License disqualifies nothing; **MSRV and streaming-architecture fit are the actual gates.**

**Constraint interpretation (asked explicitly):** "work within the established stack rather than introducing a new persistence engine" names persistence engines — a concurrency crate would not violate its letter. But the spirit (minimize new hot-path dependencies; this repo already removed niffler once) favors zero-deps when feasible, and for extraction parallelization it **is** feasible. The `zlib-rs` backend switch does not even add a direct dependency edge. Any parallel-inflate crate (rapidgzip-core/lgz) would be a genuine stack addition requiring user ratification — and the measurement gate says that branch is unlikely to open.

---

## Installation

No installation is required for the recommended path (zero new dependencies). The conditional backend switch, if the gate opens it:

```bash
# Cargo.toml [dependencies] — replace features on the existing flate2 pin:
# flate2 = { version = "1.0", default-features = false, features = ["zlib"] }
flate2 = { version = "1.1", default-features = false, features = ["zlib-rs"] }
cargo update -p flate2   # pick up 1.1.8 → 1.1.11 (patch-level); verify under MSRV 1.82
cargo tree -p flate2     # confirm zlib-rs 0.6.x enters the graph transitively
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Zero-deps chunk handoff (Pattern B) | `paraseq` callback pipeline | Never for this engine — its ownership model and niffler history conflict; only consider if the engine were being rewritten around someone else's loop |
| Producer-per-file (Pattern A) + chunk handoff | rapidgzip-core parallel inflate (MSRV raise required) | Only if profiling ever shows inflate ≥ ~50% of producer wall AND multi-file spread can't cover the workload — requires explicit user ratification of MSRV 1.87 |
| std `sync_channel` clones | `crossbeam-channel` | Only if the design later needs `select!` over multiple queues or MPMC receivers — neither is in any variant considered |
| flate2 `zlib-rs` backend | flate2 `zlib-ng` backend | Only if zlib-rs shows a build/platform problem on aarch64-macos and the inflate gate is open; zlib-ng needs a C compiler and cmake in CI for marginal/parity gains |

---

## Sources

**Local ground truth (HIGH confidence — direct inspection/experiment, 2026-11-16):**
- `src/count/engine.rs`, `src/io/fastq.rs`, `src/kmer/extract.rs` — producer path, flush/token contract, MultiGzDecoder usage
- Root `Cargo.lock` — flate2 1.1.8, rayon 1.11.0, libz-sys 1.1.23 (zlib backend), bio 2.3.0, crossbeam-* transitive-only
- Member scan of all 6 `CRR1936095_r1.part_00*.fq.gz` — single-member standard gzip each
- Inflate throughput experiment — 256 MiB slice → 1.17 GB in 0.93 s (~1.2–1.3 GB/s)

**Web-derived (LOW confidence per classify-confidence seam — versions re-verify at integration):**
- flate2 docs (docs.rs/flate2/1.1.11) — backend feature table, precedence, MultiGzDecoder semantics
- Trifecta Tech Foundation blog "zlib-rs is faster than C" (2025-02) — inflate deltas vs zlib-ng/Chromium zlib; zlib-rs crates.io/GitHub — 0.6.8, MSRV 1.75, license Zlib
- Cargo PR #15417 — zlib-rs adoption rationale (compression-heavy workload 3.30s → 1.25s)
- docs.rs crate pages — gzp 2.0.4, lgz 0.3.13/0.3.17, rapidgzip-core 0.3.1, libdeflater 1.26.x, paraseq 0.6.3 (lib.rs)
- crossbeam-channel RFC + benchmark discussions — std vs crossbeam bounded-channel performance (mixed)
- Jellyfish2 User Guide / Biowulf docs — single input stream bottleneck admission, `-F`/`-g` mitigations
- KMC docs (Biowulf/GitHub) — `-sf` dedicated FASTQ reading threads; reader-thread bottleneck thesis
- Kerbiriou & Chikhi 2019 (HiCOMB, "Parallel decompression of gzip-compressed files") — pugz speculative two-pass algorithm; pigz does not parallelize standard-gzip decompression

---
*Stack research for: rustkmer v2.1 PEXT — producer parallelization*
*Researched: 2026-11-16*
