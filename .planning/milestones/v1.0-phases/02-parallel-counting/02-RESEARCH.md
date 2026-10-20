# Phase 2: Parallel Counting - Research

**Researched:** 2026-07-01
**Domain:** Multi-core concurrent k-mer counting (Rust rayon + dashmap + PyO3 GIL release)
**Confidence:** HIGH

## Summary

Phase 2 transforms the count hot-path from single-threaded `RwLock<HashMap<u128,u32>>` into a multi-core, sharded, lock-free pipeline. Three coordinated changes deliver PCOUNT-01..04: (1) the `KmerCounter.table` field swaps from `parking_lot::RwLock<HashMap>` to `dashmap::DashMap<u128,u32>` (D-04/D-05), keeping the public API byte-identical; (2) the per-record loop in `count.rs::process_fastq_file`/`process_fasta_file` parallelizes across records via rayon `par_iter` over chunked-record buffers (D-01), with the producer loop staying single-threaded for gzip (D-02); (3) thread-count plumbing (`--threads` / `RUSTKMER_THREADS` / `RAYON_NUM_THREADS` precedence, D-06/D-07) configures a global rayon pool, and `PyCounter` exposes a `threads` kwarg with counting wrapped in `pyo3::allow_threads` (D-08).

The dominant risk is **count divergence under concurrency** (lost updates / double counts). The mitigation is sharp: k-mer counting is integer addition, which is commutative and associative, so the `--threads 1` vs `--threads N` differential test (D-10) is a high-signal bug detector — any per-k-mer count divergence is, by construction, a concurrency bug. The dashmap `entry().and_modify(overflow_check).or_insert(1)` pattern holds the shard lock for the entry's lifetime, making the upsert atomic per-key and preserving the existing u32::MAX overflow error semantics (PCOUNT-04).

Two non-obvious discoveries ground the plan: (a) `dashmap` 6.x depends on `hashbrown ^0.14.5` — verified via crates.io — so it reuses the project's existing hashbrown 0.14.5 with no duplicate-version bloat (D-04 premise holds); (b) `rayon::ThreadPoolBuilder::build_global` returns `Err` (not panic) on a second call, and `merge.rs:348` already calls it with `.expect()` — Phase 2 must centralize pool init in `execute_count` BEFORE the file loop so merge's later call degrades gracefully, otherwise merge's existing thread-config path will panic.

**Primary recommendation:** Implement in the seed-plan order 02-01 (thread plumbing) → 02-02 (dashmap swap + par_iter) → 02-03 (PyCounter GIL release) → 02-04 (differential correctness tests). Land 02-04's golden-baseline capture FIRST as a pre-step (D-10 golden-capture-before-refactor), then refactor.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01: Intra-file, per-record parallelism.** rayon parallelizes across reads/records *within* each file (encode → canonicalize → increment). Work happens in `process_fastq_file` / `process_fasta_file`'s record loops. Per-file parallelism is rejected (CRR1936095 ships as 2 split parts → caps at ~2×).
- **D-02: Do NOT parallelize gzip decompression in Phase 2.** Counting + parsing are parallelized; decompression stays single-threaded (`flate2`). Deferred to a Phase-4-gated backlog item.
- **D-03: Global record pool across files.** All reads from all input files flow into one parallel count over one sharded map; output is a single merged result (matches existing multi-file `count` semantics).
- **D-04: `dashmap` (new dependency).** dashmap 6.x, internally sharded (per-shard lock), atomic `entry()` upsert. NOT a "persistence engine" so does not violate the stack-floor constraint, but IS a new dep so must pass Phase 1's `clippy -D warnings` gate on BOTH crates. dashmap 6.x reuses hashbrown 0.14 (no duplicate hashbrown).
- **D-05: Public API of `KmerCounter` is preserved.** Internal swap only: `table: RwLock<HashMap<u128,u32>>` → `DashMap<u128,u32>`. Public surface (`increment`, `get_count`, `get_all_counts`, `get_top_n`, `merge`, stats accessors) stays identical; `count.rs` and `pyo3/src/counter.rs` call-sites do not change. `total_kmers`/`unique_kmers` stay as atomics.
- **D-06: Default = all cores via a global rayon pool.** Thread count = `num_cpus` when no flag/env set (PCOUNT-01). Applied with `rayon::ThreadPoolBuilder::build_global()` so `count` and the existing `merge` rayon usage share one pool.
- **D-07: Precedence chain `--threads` > `RUSTKMER_THREADS` > `RAYON_NUM_THREADS` > all-cores.** New `RUSTKMER_THREADS` wins; falls back to `RAYON_NUM_THREADS` so existing merge-tuning users are unaffected; if both unset, all cores.
- **D-08: `PyCounter` exposes `threads` (PCOUNT-03).** `PyCounter(k, canonical, threads=None)` — `None` means all cores. Counting runs inside `pyo3::allow_threads` (GIL released).
- **D-09: `--sort` becomes the DEFAULT (user decision, overrides the "keep optional" recommendation).** Sorted output on by default; `--no-sort` disables; `--sort` retained as backward-compat alias. ⚠ Sort over the full k-mer set at human scale (~3B entries) on every run — Phase 4 measures the real cost.
- **D-10: Correctness via golden-capture-first + `--threads 1`-vs-`N` differential + proptest.** Capture counts baseline from the *current sequential* code BEFORE refactoring; after, assert (a) `--threads 1` vs `--threads N` produce identical count maps, (b) output matches the pre-refactor baseline, (c) proptest holds for random small inputs. Coverage matrix echoes Phase 1 D-13: `k ∈ {21, 32, 64}` × canonical × multiple sizes.

### Claude's Discretion
- **Shard count / hasher:** use `dashmap` defaults (~4×num_cpus shards; default hasher). No hand-tuning unless the benchmark shows contention.
- **Overflow semantics:** preserve current u32 count with error-on-`u32::MAX`-per-kmer (`table.rs:75-80`) — required for PCOUNT-04.
- **Flag mechanics for sort:** `should_sort = !no_sort`; keep `--sort` as a redundant-but-valid alias.
- **`--threads` validation:** reject `< 1` with a clear error (mirror `InvalidKmerSize` style); report resolved thread count in `-v/--verbose` output.
- **`RAYON_NUM_THREADS` fallback:** only consulted when both `--threads` and `RUSTKMER_THREADS` are unset.
- **Unsorted comparison in existing tests:** any test doing byte-comparison on *unsorted* output must switch to set/sorted comparison (sharded iteration order differs from `HashMap`). Golden coverage spans `k ∈ {21, 32, 64}` × canonical × multiple sizes.
- **Buffering granularity for intra-file parallelism:** use bounded chunked buffering (not buffer-all) — exact chunk size is the planner's call.
- **Where encode/canonicalize runs:** on the worker side inside the rayon task (keeps the producer loop to read+parse only).

### Deferred Ideas (OUT OF SCOPE)
- **Parallel gzip decompression** (split compressed stream on gzip-member boundaries, multi-threaded gunzip) — deferred; gated on Phase 4's benchmark.
- **Adaptive shard / prefix granularity for counting** (minimizer-partitioning / MINIM-02/03) — v2 bounded-memory counting, distinct from Phase 2's parallelism goal.
- **Configurable counter width / saturation warning** (SAT-01/02) — v2; Phase 2 keeps u32 with existing overflow semantics.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PCOUNT-01 | Counting uses all available CPU cores by default — the hardcoded `num_threads = 1` is removed; thread count configurable via `--threads` / `RUSTKMER_THREADS` | §Architecture Patterns (Thread Configuration UX); §Code Examples (rayon `ThreadPoolBuilder::build_global` + precedence resolution). The `KmerCounter::new` `_num_threads` param at `table.rs:44` is currently unused — thread count is a rayon-pool concern, NOT a counter concern; it lives at the command level in `execute_count`. |
| PCOUNT-02 | The counter uses a sharded concurrent map (dashmap) instead of `RwLock<HashMap>`, so throughput scales with core count without lock contention | §Standard Stack (dashmap 6.x); §Architecture Patterns (dashmap `entry` upsert); §Code Examples (atomic upsert preserving overflow semantics). dashmap is internally sharded (~4×num_cpus), per-shard `RwLock`; `entry()` holds only the relevant shard lock. |
| PCOUNT-03 | `pyrustkmer`'s `PyCounter` delivers the same parallel speedup as the CLI (shared core) | §Architecture Patterns (PyO3 GIL release); §Code Examples (`py.allow_threads` wrapping rayon work). `PyCounter(k, canonical, threads=None)` signature via `#[pyo3(signature = (...))]`. Shared core means the `table.rs` swap flows to both surfaces automatically. |
| PCOUNT-04 | Parallel counting produces results identical to the current sequential path — k-mer counts match exactly (correctness guard) | §Common Pitfalls (Lost update / deadlock); §Validation Architecture (1-vs-N differential test design). The commutativity of integer addition makes 1-vs-N divergence a definitive concurrency-bug signal. dashmap `entry().and_modify().or_insert()` preserves the existing `table.rs:75-80` overflow-error semantics. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Per-record k-mer encode/canonicalize/increment | CLI command handler (`count.rs`) | Core library (`hash/`, `kmer/`) | The per-record loop is the parallelization site; rayon tasks call into the shared core's `counter.increment`. The core owns the data structure; the CLI owns the orchestration. |
| Concurrent count storage | Core library (`hash/table.rs`) | — | `KmerCounter` owns the `DashMap`; thread-safety is the core's responsibility. The DashMap is shared across rayon workers via `Arc<KmerCounter>`. |
| Global thread-pool configuration | CLI command handler (`count.rs`) / PyO3 init (`pyo3/src/counter.rs`) | Config layer (`config/manager.rs`) | `rayon::ThreadPoolBuilder::build_global` is process-global and must be called once, early. The CLI `execute_count` and the PyO3 `PyCounter::new` are the two entry points that need to configure it. Config manager reads `RUSTKMER_THREADS` (already does, `manager.rs:333`). |
| GIL release for parallel Python counting | PyO3 binding layer (`pyo3/src/counter.rs`) | — | The GIL is a Python-runtime concern; only the binding layer can call `py.allow_threads`. Rayon workers cannot hold the GIL. |
| Deterministic output ordering | CLI output formatting (`count.rs::output_*_format`) | — | Sharded iteration order is non-deterministic; the sort step in the output formatter restores determinism (D-09 default-sort). |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `dashmap` | `6.1` / `6.2.1` (latest stable) | Sharded concurrent `HashMap<u128, u32>` — the PCOUNT-02 concurrent counter | The locked decision (D-04). Mature (published 2019, ~5M weekly downloads, 305M total, repo github.com/xacrimon/dashmap). Internally sharded (~4×num_cpus), per-shard `RwLock`, direct replacement for `RwLock<HashMap>`. `entry()` API mimics `std::collections::HashMap` for an atomic upsert. `[VERIFIED: crates.io API + docs.rs]` — depends on `hashbrown ^0.14.5` (same as project's existing 0.14.5), so NO duplicate-version bloat. |
| `rayon` | `1.8` (already a dep, transitively 1.10) | Data parallelism — `par_iter` over chunked record buffers; `ThreadPoolBuilder::build_global` for pool config | Already in the dep graph (used by `prefix_cache_merge.rs`, `streaming_merge.rs`). `num_cpus` comes transitively. No new dep. `[VERIFIED: Cargo.toml + Cargo.lock]` |
| `pyo3` | `0.27.2` (already pinned) | Python bindings; `py.allow_threads` for GIL release | Already pinned in `pyo3/Cargo.toml`. CRITICAL: in 0.27.2 the API is `Python::allow_threads` — `Python::detach` is the rename landing in pyo3 0.28+ and is NOT available in 0.27.2. `[VERIFIED: pyo3 CHANGELOG + WebSearch]` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `num_cpus` | (transitive via rayon) | Resolve `threads=None` → logical CPU count for PCOUNT-01 default | Use `num_cpus::get()` (or `rayon::current_num_threads()` after pool init) when `--threads`/`RUSTKMER_THREADS`/`RAYON_NUM_THREADS` are all unset. `[ASSUMED]` — not a direct dep but accessible via rayon. |
| `proptest` | `1.5` (already a dev-dep) | Property-based count-determinism tests (D-10) | Already a dev-dep. Pattern exists in `tests/property/stats_properties.rs`. `[VERIFIED: Cargo.toml:95]` |
| `parking_lot` | `0.12` (already a dep) | `RwLock` for any remaining single-writer spots; `parking_lot_core` is also pulled by dashmap | Keep for `ConfigManager` (`config/manager.rs`) and any non-counter shared state. The counter itself moves off `parking_lot::RwLock`. `[VERIFIED: Cargo.toml]` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `dashmap` | `evmap` (eventual-consistency MVCC map) | `evmap` is read-optimized but requires a second pass to merge writer-side state; `dashmap`'s strong consistency is what PCOUNT-04 (identical counts) demands. D-04 locks `dashmap`; do not relitigate. |
| `dashmap` | `crossbeam-skiplist` | Lock-free but higher per-op constant factor for u128 keys at this scale; `dashmap`'s sharded `RwLock` is the established pattern. |
| `par_iter` over chunked buffers | `par_bridge` (rayon's parallel bridge from a sequential iterator) | `par_bridge` has unbounded-buffer / backpressure caveats and is documented as less efficient than explicit chunking for IO-bound producers. Bounded chunked buffering (D-discretion) gives explicit memory control — important since u128 HashMap is already memory-heavy (CONCERNS.md). `[CITED: rayon docs / GitHub issue #210]` |
| Global rayon pool (`build_global`) | Local `ThreadPool` per command | Local pool is rayon's recommended default for isolation, but D-06 explicitly locks `build_global` so count and merge share one pool (simplest, fewest moving parts). |

**Installation:**
```bash
# Add to Cargo.toml [dependencies]:
dashmap = "6.1"   # or "6.2.1" — both pin hashbrown ^0.14.5

# rayon is already present; num_cpus comes transitively.
# No changes to pyo3/Cargo.toml (rustkmer path-dep flows dashmap through automatically).
```

**Version verification (run before writing the Standard Stack table; results documented above):**
```bash
# Confirmed via crates.io API (2026-07-01):
# dashmap max_stable_version = 6.2.1, newest = 6.2.1
# dashmap 6.1.0 deps: hashbrown ^0.14.0, lock_api ^0.4.10, parking_lot_core ^0.9.8
# dashmap 6.2.1 deps: hashbrown ^0.14.5, lock_api ^0.4.13, parking_lot_core ^0.9.11
# Project's Cargo.lock already has hashbrown 0.14.5 → no version conflict.
```

## Package Legitimacy Audit

> Run via `gsd-tools query package-legitimacy check --ecosystem crates dashmap rayon num_cpus` (2026-07-01).

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `dashmap` | crates.io | since 2019-08-25 (~7 yrs) | ~5.1M weekly / 305M total | github.com/xacrimon/dashmap | OK | Approved |
| `rayon` | crates.io | since 2015-12-10 (~10 yrs) | ~7.3M weekly | github.com/rayon-rs/rayon | OK | Approved (already a dep) |
| `num_cpus` | crates.io | since 2015-03-16 (~11 yrs) | ~6.2M weekly | github.com/seanmonstar/num_cpus | OK | Approved (transitive via rayon) |

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious [SUS]:** none

*All three packages are well-established Rust ecosystem crates with high download volume, official source repos, and no deprecation flags. `dashmap` is the only NEW direct dependency introduced by this phase; `rayon` and `num_cpus` are already in the dependency graph.*

## Architecture Patterns

### System Architecture Diagram

```text
                         ┌─────────────────────────────────────┐
                         │  CLI: rustkmer count (count.rs)     │
                         │  OR  pyrustkmer.PyCounter           │
                         │                                     │
                         │  1. Resolve thread count            │
                         │     (--threads > RUSTKMER_THREADS > │
                         │      RAYON_NUM_THREADS > num_cpus)  │
                         │  2. build_global() ONCE, early      │
                         └────────────────┬────────────────────┘
                                          │
                                          ▼
           ┌──────────────────────────────────────────────────────┐
           │  Per-file producer loop (SINGLE-THREADED for gzip    │
           │  decompression — D-02; sequential bio::io reader)    │
           │                                                      │
           │  for file in files_to_process:                       │
           │    reader = open+decompress(file)                    │
           │    loop {                                            │
           │      buffer N records into Vec<Record>   ─────────┐  │
           │      (bounded chunk — D-discretion)               │  │
           │    }                                               │  │
           └──────────────────────────────────┬─────────────────┘  │
                                              │                    │
                                              ▼                    │
           ┌──────────────────────────────────────────────────┐    │
           │  rayon par_iter over the chunk  (D-01)           │◀───┘
           │                                                  │
           │  chunk.par_iter().for_each(|record| {            │
           │    for window in record.seq().windows(k) {       │
           │      kmer = encode_kmer_bytes_u128(window)?      │
           │      kmer = canonical_kmer_u128(kmer, k)?  [opt] │
           │      counter.increment(kmer)?  ◀── Arc shared    │
           │    }                                             │
           │  })                                              │
           └──────────────────────┬───────────────────────────┘
                                  │
                                  ▼
           ┌──────────────────────────────────────────────────┐
           │  KmerCounter (hash/table.rs) — D-04/D-05         │
           │  table: DashMap<u128, u32>  (sharded, ~4×cores)  │
           │                                                  │
           │  increment(kmer):                                │
           │    total_kmers.fetch_add(1, Relaxed)  [atomic]   │
           │    table.entry(kmer)                             │
           │      .and_modify(|c| {                           │
           │        // overflow check inline (shard lock held)│
           │        if *c == max_count { return Err(...) }    │
           │        *c += 1;                                  │
           │      })                                          │
           │      .or_insert_with(|| {                        │
           │        unique_kmers.fetch_add(1, Relaxed); 1     │
           │      });                                         │
           └──────────────────────┬───────────────────────────┘
                                  │
                                  ▼
           ┌──────────────────────────────────────────────────┐
           │  Output (count.rs::output_*_format) — D-09       │
           │  default-sort = true (deterministic; sharded     │
           │  iteration is otherwise run-to-run random)       │
           │  get_filtered_kmers() → Vec → sort → write       │
           └──────────────────────────────────────────────────┘
```

A reader can trace the primary use case (count a FASTQ file) from input (file open + gzip decompress, single-threaded) through the parallel stage (chunk → `par_iter` → encode/canonicalize/increment against the shared `DashMap`) to output (deterministic sorted write). Decision points: thread-count precedence resolution at the top; the `canonical` branch inside each rayon task; the default-sort flip at the bottom.

### Recommended Project Structure
```
src/
├── hash/
│   └── table.rs          # KmerCounter: RwLock<HashMap> → DashMap swap (D-05)
├── cli/
│   ├── args.rs           # Commands::Count: add --threads field (D-07)
│   └── commands/
│       └── count.rs      # build_global() init; process_*_file → par_iter; default-sort flip
├── config/
│   └── manager.rs        # already reads RUSTKMER_THREADS (manager.rs:333) — wire it through
└── ...
pyo3/src/
└── counter.rs            # PyCounter(k, canonical, threads=None); allow_threads around counting
tests/
├── common/               # reuse factories + temp_file! for differential harness
├── fixtures/             # 12 golden .rkdb files (k×canon×sorted) — D-13 matrix
├── golden_tests.rs       # sha256 gate on COMMITTED fixtures (not regenerated — safe)
├── golden_generate.rs    # #[ignore]d baseline generator (D-10 capture-first template)
└── parallel_count_tests.rs  # NEW: --threads 1 vs N differential (plan 02-04)
```

### Pattern 1: dashmap atomic upsert preserving overflow semantics (PCOUNT-02, PCOUNT-04)
**What:** Replace `RwLock<HashMap>` write-lock-then-mutate with dashmap's `entry().and_modify().or_insert()`, which holds only the relevant shard lock for the entry's lifetime.
**When to use:** Every `KmerCounter::increment` call (the hot path).
**Why it preserves PCOUNT-04:** the entry holds the shard lock, so the overflow check + increment is atomic per-key — no lost update, no double count. The existing `table.rs:75-80` error-on-`u32::MAX` semantics survive verbatim.
**Example:**
```rust
// Source: dashmap docs.rs Entry API (verified 2026-07-01)
//         + existing src/hash/table.rs:67-91 overflow semantics

use dashmap::DashMap;

pub struct KmerCounter {
    table: DashMap<u128, u32>,                          // was: RwLock<HashMap<u128,u32>>
    total_kmers: std::sync::atomic::AtomicU64,          // keep
    unique_kmers: std::sync::atomic::AtomicU64,         // keep
    kmer_length: usize,
    canonical_mode: bool,
    max_count: u32,                                     // keep (u32::MAX)
}

pub fn increment(&self, kmer_encoded: u128) -> ProcessingResult<()> {
    self.total_kmers
        .fetch_add(1, std::sync::atomic::Ordering::Relaxed);

    // CRITICAL: the overflow check MUST be inline inside and_modify.
    // The Entry guard holds the shard lock for its lifetime; splitting this
    // into get() + insert() would (a) risk deadlock (docs.rs: "May deadlock
    // if called when holding any sort of reference into the map") and
    // (b) lose atomicity → lost updates under concurrency.
    //
    // and_modify takes FnOnce(&mut V) — it cannot short-circuit return Err.
    // Pattern: mutate a flag inside the closure, then check after.
    let mut overflow = false;
    self.table
        .entry(kmer_encoded)
        .and_modify(|count| {
            if *count == self.max_count {
                overflow = true;
            } else {
                *count += 1;
            }
        })
        .or_insert_with(|| {
            self.unique_kmers
                .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            1
        });

    if overflow {
        return Err(ProcessingError::new(format!(
            "K-mer count overflow reached maximum value {}",
            self.max_count
        )));
    }
    Ok(())
}
```

> **Planner note:** the `and_modify` closure is `FnOnce(&mut V) -> ()` and cannot propagate `Result`. The flag-then-check pattern above is the standard workaround; the planner should specify it explicitly in the plan to avoid the executor reaching for `or_try_insert_with` (which only covers the insert path, not the modify path).

### Pattern 2: rayon chunked-buffer intra-file parallelism (D-01, D-02)
**What:** The producer loop reads records sequentially (gzip stays single-threaded, D-02) into bounded chunks; each chunk is then `par_iter`'d.
**When to use:** `process_fastq_file` / `process_fasta_file` record loops.
**Why chunked (not `par_bridge`):** `par_bridge` has documented unbounded-buffer/backpressure caveats and is less efficient than explicit chunking for IO-bound producers. Bounded chunks give explicit memory control — important because the u128 HashMap is already memory-heavy (CONCERNS.md). `[CITED: rayon GitHub issue #210 + docs.rs IndexedParallelIterator]`
**Example:**
```rust
// Source: established Rust rayon+FASTQ pattern (verified via WebSearch 2026-07-01)
//         + existing src/io/fastq.rs::FastqProcessor::process_file structure

use rayon::prelude::*;

const CHUNK_SIZE: usize = 4_096; // planner's call (D-discretion); bounded to avoid memory blowup

fn process_fastq_file(/* ... */) -> ProcessingResult<()> {
    let reader = open_and_decompress(path)?;          // SINGLE-THREADED gzip (D-02)
    let fastq_reader = bio::io::fastq::Reader::new(reader);

    let mut chunk: Vec<bio::io::fastq::Record> = Vec::with_capacity(CHUNK_SIZE);
    for record_result in fastq_reader.records() {
        let record = record_result?;
        chunk.push(record);
        if chunk.len() == CHUNK_SIZE {
            let chunk_ref = &chunk;                    // borrow, don't clone
            chunk_ref.par_iter().try_for_each(|record| {
                // encode → canonicalize → increment, per-record
                process_one_record(record, &counter, k, canonical)
            })?;
            chunk.clear();
        }
    }
    // drain the remainder
    if !chunk.is_empty() {
        chunk.par_iter().try_for_each(|record| {
            process_one_record(record, &counter, k, canonical)
        })?;
    }
    Ok(())
}
```

> **Planner note:** `try_for_each` propagates the `ProcessingResult<()>` from `counter.increment` (which can now return the overflow error from Pattern 1). The producer loop's `chunk.clear()` bounds memory to `CHUNK_SIZE` records. The exact `CHUNK_SIZE` is Claude-discretion — recommend 4096 as a starting point; the planner can parameterize.

### Pattern 3: Global rayon pool with precedence resolution (D-06, D-07)
**What:** Resolve the thread count from the precedence chain, then call `ThreadPoolBuilder::build_global` ONCE, early, before any rayon use.
**When to use:** At the top of `execute_count`, before the file loop.
**Why build_global:** D-06 locks it — count and merge share one pool. The existing `merge.rs:346-360` already implements the same pattern (and will panic if the pool is already initialized — see Pitfall 3).
**Example:**
```rust
// Source: existing src/cli/commands/merge.rs:346-360 (precedence pattern)
//         + rayon docs.rs ThreadPoolBuilder (build_global returns Err on 2nd call)

fn resolve_thread_count(args: &Args) -> usize {
    // Precedence (D-07): --threads > RUSTKMER_THREADS > RAYON_NUM_THREADS > num_cpus
    if let Some(threads) = args.threads() {           // --threads CLI flag
        return threads;
    }
    if let Ok(val) = std::env::var("RUSTKMER_THREADS") {
        if let Ok(t) = val.parse::<usize>() { return t; }
    }
    if let Ok(val) = std::env::var("RAYON_NUM_THREADS") {
        if let Ok(t) = val.parse::<usize>() { return t; }
    }
    num_cpus::get()
}

// In execute_count, BEFORE the file loop:
let threads = resolve_thread_count(args);
if *verbose { eprintln!("Using {} threads", threads); }
let _ = rayon::ThreadPoolBuilder::new()
    .num_threads(threads)
    .build_global();   // ignore Err — pool may already be initialized (tests, embed)
```

> **Planner note (Pitfall 3):** `build_global` returns `Result<(), ThreadPoolBuildError>` and the `Err` variant fires on a second call. The existing `merge.rs:348` uses `.expect("Failed to set rayon thread pool")` — that WILL panic if `execute_count` already initialized the pool. Two fix options for the planner: (a) have `execute_count` own pool init and make `merge` tolerant (ignore Err with a warning), or (b) extract pool init into a shared helper that both call idempotently. Recommend (a) since count is the primary lever and merge already has a fallback (`RAYON_NUM_THREADS` env).

### Pattern 4: PyO3 GIL release for parallel Python counting (D-08, PCOUNT-03)
**What:** `PyCounter` wraps its counting methods in `py.allow_threads(|| { ... })` so rayon workers run in parallel; the `threads` kwarg configures the global pool at construction time.
**When to use:** Every `PyCounter` method that triggers counting (`add_from_fastq`, `add_from_fasta`, `add_sequence`).
**Why allow_threads (not detach):** the project pins `pyo3 = "0.27.2"`. `Python::detach` is the rename landing in pyo3 0.28+ and is NOT available in 0.27.2. `[VERIFIED: pyo3 CHANGELOG 0.28 + WebSearch]`
**Example:**
```rust
// Source: pyo3 0.27 parallelism guide + docs.rs/pyo3/0.27 (verified 2026-07-01)

#[pyclass(name = "PyCounter")]
pub struct PyCounter {
    counter: Arc<RustPyCounter>,   // Arc so workers can share; currently owned, needs swap
}

#[pymethods]
impl PyCounter {
    #[new]
    #[pyo3(signature = (kmer_length, canonical=false, initial_capacity=1000, threads=None))]
    fn new(
        kmer_length: i64,
        canonical: bool,
        initial_capacity: usize,
        threads: Option<usize>,
    ) -> PyResult<Self> {
        // ... validate kmer_length 1..=64 ...
        let resolved = threads.unwrap_or_else(num_cpus::get);
        // build_global once; ignore Err if already initialized
        let _ = rayon::ThreadPoolBuilder::new()
            .num_threads(resolved)
            .build_global();
        let counter = Arc::new(RustPyCounter::new(kmer_length as usize, canonical, initial_capacity, resolved)?);
        Ok(Self { counter })
    }

    fn add_from_fastq(&self, py: Python<'_>, file_path: &Bound<'_, PyString>) -> PyResult<()> {
        // CRITICAL: extract all Python args into plain Rust types BEFORE allow_threads.
        // The closure CANNOT capture &PyString / Bound<T> — unsafe without the GIL.
        let path_str = file_path.to_str()?.to_owned();   // owned String
        let counter = self.counter.clone();              // Arc clone
        py.allow_threads(move || {
            // GIL released — rayon workers run in parallel here
            process_fastq_owned(&counter, &path_str)
        }).map_err(|e: rustkmer::ProcessingError| {
            PyErr::new::<PyValueError, _>(format!("Failed to process FASTQ: {}", e))
        })
    }
}
```

> **Planner notes:** (1) `PyCounter.counter` must move from owned `RustPyCounter` to `Arc<RustPyCounter>` so rayon workers can share it — this is an internal field-swap that does NOT change the Python-visible API. (2) The `process_sequence_bytes` helper currently takes `&mut self`; under parallel counting it must take `&Arc<RustPyCounter>` (DashMap gives interior mutability, so `increment` already takes `&self`). (3) `add_kmer`/`add_sequence` may not need `allow_threads` (single k-mer / short sequence) — the planner should decide which methods warrant GIL release based on workload size.

### Anti-Patterns to Avoid
- **Splitting the dashmap upsert into `get()` + `insert()`:** loses atomicity (lost updates under concurrency — directly violates PCOUNT-04) AND risks deadlock per docs.rs ("May deadlock if called when holding any sort of reference into the map"). Use `entry().and_modify().or_insert()` with the overflow check inline.
- **Using `Python::detach` in pyo3 0.27.2:** the API does not exist; it is the 0.28+ rename. Use `py.allow_threads(...)`. Compiling against 0.27.2 with `detach` will fail.
- **Calling `ThreadPoolBuilder::build_global` from `merge` AFTER `count` already called it:** the second call returns `Err`; merge's existing `.expect()` will panic. Phase 2 must centralize pool init.
- **Parallelizing gzip decompression:** explicitly out of scope (D-02). CRR1936095 is plain gzip (not BGZF), so member-boundary detection is fragile. Keep `flate2` single-threaded; the producer loop reads sequentially.
- **Byte-comparing unsorted count-path output across runs:** sharded DashMap iteration order is non-deterministic run-to-run. The D-09 default-sort flip + set/sorted comparison in differential tests (D-10) are the guards.
- **Holding the GIL across `par_iter`:** rayon workers would execute serially (no parallelism); PCOUNT-03's speedup would not materialize. Always wrap in `py.allow_threads`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Concurrent hash map | Custom sharded `Vec<RwLock<HashMap>>` | `dashmap::DashMap` (D-04) | dashmap handles shard selection, resizing, and the `entry` API atomically; a hand-rolled version would re-derive ~7 years of bug fixes (deadlock avoidance, shard sizing, hasher integration). |
| Thread pool | Custom `std::thread::spawn` worker queue | `rayon::ThreadPoolBuilder::build_global` (D-06) | rayon provides work-stealing, scoped tasks, and integrates with `par_iter`; a hand-rolled pool would lose work-stealing and the `par_iter` ergonomic. |
| GIL management | Manual `Python::with_gil` + thread spawning | `py.allow_threads(\|\| {...})` | PyO3's GIL tracking is subtle; `allow_threads` is the supported, sound way to release and re-acquire. Hand-rolling risks UB. |
| Atomic count upsert | `lock().get_mut().unwrap()` chain | `DashMap::entry().and_modify().or_insert()` | The entry API is the only sound way to do atomic check-then-increment under dashmap's sharded locking. |
| Count determinism check | Custom serialized-counter diff | The `--threads 1` vs `--threads N` differential (D-10) | Integer addition is commutative; ANY divergence is a concurrency bug by construction. No custom logic needed — just compare count maps. |

**Key insight:** every piece of concurrency machinery this phase needs (sharded map, work-stealing pool, GIL release) already exists as a mature, audited crate. The phase's job is integration, not invention. Hand-rolling any of these would re-introduce bugs the ecosystem solved years ago.

## Runtime State Inventory

> Phase 2 is NOT a rename/refactor/migration phase — it is a parallelization refactor. However, it does change the iteration order of count-path output (sharded vs HashMap) and flips a CLI default (sort). The relevant runtime-state categories:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `.rkdb` files on disk: format unchanged (still v2, 42-byte header, 20-byte entries). No data migration. | None — format preserved (D-05). |
| Live service config | No daemon/server. `RUSTKMER_THREADS` env var — NEW; users who set it for merge will now also affect count. | Document the new env var in USER_GUIDE / INSTALL. The precedence chain (D-07) ensures `RAYON_NUM_THREADS`-only users are unaffected. |
| OS-registered state | None. | None. |
| Secrets/env vars | `RUSTKMER_THREADS` (new), `RAYON_NUM_THREADS` (existing, now also consulted by count). No secrets involved. | Wire `RUSTKMER_THREADS` into the count path's `resolve_thread_count` (already read by `config/manager.rs:333` but not yet consumed by `execute_count`). |
| Build artifacts | `Cargo.lock` will gain `dashmap` + transitive deps (`lock_api`, `parking_lot_core` already present via `parking_lot`). No `dashmap` in lockfile today. | `cargo build` will update `Cargo.lock`. Confirm `dashmap` 6.x pulls `hashbrown 0.14.5` (verified — no version conflict). |

**Nothing found that blocks execution.** The phase is a code-only refactor with no data migration and no OS-level changes.

## Common Pitfalls

### Pitfall 1: Lost update / double count from non-atomic dashmap upsert
**What goes wrong:** Per-k-mer counts differ between `--threads 1` and `--threads N` (violates PCOUNT-04).
**Why it happens:** Splitting the increment into `get()` then `insert()` (or `get_mut` then write) creates a TOCTOU window: two rayon workers can both read count=5, both compute 6, both write 6 — losing one increment.
**How to avoid:** Use `DashMap::entry(k).and_modify(|c| {...}).or_insert_with(|| {...})`. The `Entry` holds the shard lock for its entire lifetime, making the read-modify-write atomic per-key. The overflow check MUST be inline inside `and_modify` (see Pattern 1).
**Warning signs:** The D-10 `--threads 1` vs `--threads N` differential test fails on any k-mer count. Because addition is commutative, ANY divergence is this bug (or its double-count sibling).

### Pitfall 2: dashmap deadlock from nested references
**What goes wrong:** Runtime hang during counting.
**Why it happens:** docs.rs (verified): DashMap methods "May deadlock if called when holding any sort of reference into the map." If `increment` is called while another reference (e.g., an `iter()` guard, a `get()` guard) is alive on the same shard, the second lock attempt deadlocks.
**How to avoid:** Never hold a `Ref`/`RefMut`/`Entry` guard across another DashMap call. The `entry().and_modify().or_insert()` chain is safe because it's a single guard lifetime. Do NOT do `let r = map.get(&k); map.insert(k, r+1);` — that's both a deadlock risk and a lost update.
**Warning signs:** Test hangs indefinitely (no panic, no error). Run under `cargo test -- --test-threads=1` to isolate; if it still hangs, suspect deadlock.

### Pitfall 3: `build_global` panic when merge runs after count
**What goes wrong:** `rustkmer count ... && rustkmer merge ...` or any workflow calling both commands panics in merge.
**Why it happens:** `rayon::ThreadPoolBuilder::build_global` returns `Err` on the second call (verified via docs.rs). The existing `merge.rs:348` uses `.expect("Failed to set rayon thread pool")`, which panics on Err. If `execute_count` already initialized the pool, merge's call panics.
**How to avoid:** Centralize pool init. Options: (a) `execute_count` calls `build_global` and ignores Err (pool may already exist from a prior command in a shell pipeline); (b) make `merge.rs` tolerant — replace `.expect()` with `if let Err(e) = ... { log::warn!("thread pool already initialized: {}", e); }`. Recommend (a) + (b) together: both call sites tolerate already-initialized pools.
**Warning signs:** `rustkmer merge` panics with "Failed to set rayon thread pool" after `rustkmer count` ran in the same process (rare for CLI, common for tests and for `pyrustkmer` users who call both).

### Pitfall 4: Capturing Python objects across `allow_threads`
**What goes wrong:** PyO3 compile error ("lifetime mismatch" / "Python objects cannot be sent across threads") or runtime UB.
**Why it happens:** `py.allow_threads(|| {...})` releases the GIL; the closure cannot capture `&PyString`, `PyObject`, `Bound<T>`, or any type holding a `Python<'py>` token. Rayon workers are OS threads without GIL access.
**How to avoid:** Extract all Python arguments into plain owned Rust types (`String`, `Vec<u8>`, `usize`) BEFORE the `allow_threads` closure. Clone `Arc<RustPyCounter>` and move it into the closure. See Pattern 4.
**Warning signs:** Compile error mentioning `PyNativeType` / `Bound` / `Python<'py>` not `Send`.

### Pitfall 5: Existing golden byte-comparison test misread
**What goes wrong:** Planner assumes `golden_tests.rs` will break when DashMap lands (because iteration order changes) — it will NOT.
**Why it happens:** `golden_tests.rs` reads the COMMITTED fixture files (`tests/fixtures/golden_*.rkdb`) and hashes them; it does NOT regenerate them at test time. The fixtures are static bytes. The sharded-iteration-order change only affects RUNTIME output, not the committed fixtures.
**How to avoid:** Understand the test layering: `golden_generate.rs` is `#[ignore]`d (run-once baseline capture); `golden_tests.rs` only checks the committed bytes haven't drifted. The D-10 differential test is a NEW test (`tests/parallel_count_tests.rs`, plan 02-04) that regenerates counts at runtime and compares them as SETS/maps, not bytes.
**Warning signs:** Over-engineering "fixes" to `golden_tests.rs` when it is not actually broken. The real gate is the new differential test.

### Pitfall 6: `and_modify` closure cannot return `Result`
**What goes wrong:** Compile error when trying to `return Err(...)` inside `and_modify(|c| { if *c == max { return Err(...) } })`.
**Why it happens:** `and_modify` takes `FnOnce(&mut V) -> ()` — it has no error channel. The closure must complete normally.
**How to avoid:** Use the flag-then-check pattern (Pattern 1): mutate a `let mut overflow = false;` inside the closure, then `if overflow { return Err(...) }` after the `entry` chain completes. The shard lock is released when the chain finishes (the `RefMut` guard drops), so the error return is safe.

## Code Examples

### Verified: Existing `increment` (sequential, to be replaced) — `src/hash/table.rs:67-91`
```rust
// Source: src/hash/table.rs (read 2026-07-01) — the PRE-refactor baseline.
// PCOUNT-04 requires the POST-refactor path to produce IDENTICAL counts.
pub fn increment(&self, kmer_encoded: u128) -> ProcessingResult<()> {
    self.total_kmers
        .fetch_add(1, std::sync::atomic::Ordering::Relaxed);

    let mut table = self.table.write();                    // global write lock

    match table.get_mut(&kmer_encoded) {
        Some(count) => {
            if *count == self.max_count {                  // overflow check (preserve!)
                return Err(ProcessingError::new(format!(
                    "K-mer count overflow reached maximum value {}", self.max_count
                )));
            }
            *count += 1;
        }
        None => {
            table.insert(kmer_encoded, 1);
            self.unique_kmers
                .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        }
    }
    Ok(())
}
```

### Verified: Existing thread-pool precedence (merge.rs:346-360 — the template for count)
```rust
// Source: src/cli/commands/merge.rs:346-360 (read 2026-07-01)
// This is the ESTABLISHED precedence pattern; count.rs should mirror it
// but tolerate the "pool already initialized" Err (Pitfall 3).
if args.num_threads > 0 {
    config.num_threads = args.num_threads;
    rayon::ThreadPoolBuilder::new()
        .num_threads(args.num_threads)
        .build_global()
        .expect("Failed to set rayon thread pool");    // <-- PITFALL 3: panics on 2nd call
} else if let Ok(num_threads_str) = std::env::var("RAYON_NUM_THREADS") {
    if let Ok(num_threads) = num_threads_str.parse::<usize>() {
        if num_threads > 0 {
            config.num_threads = num_threads;
            rayon::ThreadPoolBuilder::new()
                .num_threads(num_threads)
                .build_global()
                .expect("Failed to set rayon thread pool");
        }
    }
}
```

### Verified: Existing `PyCounter::new` signature (the threads kwarg lands here)
```rust
// Source: pyo3/src/counter.rs:124-146 (read 2026-07-01)
#[new]
#[pyo3(signature = (kmer_length, canonical=false, initial_capacity=1000))]
//                                   ^^ add threads=None here (D-08) ^^
fn new(kmer_length: i64, canonical: bool, initial_capacity: usize) -> PyResult<Self> {
    if !(1..=64).contains(&kmer_length) {
        return Err(PyErr::new::<PyValueError, _>(format!(
            "Invalid k-mer size: {}. Must be between 1 and 64", kmer_length
        )));
    }
    let kmer_length_usize = kmer_length as usize;
    // Currently passes num_threads=1; Phase 2 wires the resolved thread count here.
    let counter = RustPyCounter::new(kmer_length_usize, canonical, initial_capacity, 1)
        .map_err(|e| PyErr::new::<PyValueError, _>(format!("Failed to create counter: {}", e)))?;
    Ok(Self { counter })
}
```

### Verified: golden-capture-first template (`tests/golden_generate.rs`)
```rust
// Source: tests/golden_generate.rs (read 2026-07-01) — the D-10 template.
// Plan 02-04 should mirror this: capture pre-refactor counts BEFORE the dashmap
// swap, persist as a baseline, then assert post-refactor counts match.
const GOLDEN_INPUT: &[&str] = &[ /* fixed deterministic DNA sequences */ ];

#[test]
#[ignore] // run-once baseline capture: `cargo test --test golden_generate -- --ignored`
fn capture_baseline_counts() {
    // Run the CURRENT sequential counter on GOLDEN_INPUT across the D-13 matrix
    // (k ∈ {21,32,64} × canonical × sorted), serialize the count MAPS (not bytes)
    // to tests/fixtures/parallel_count_baseline/<cell>.json.
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `RwLock<HashMap>` global write lock | `DashMap` sharded per-shard locks | dashmap 3.0 (2019), stable 6.x | Removes the single global lock that serialized all increments; throughput now scales with shard count (~4×num_cpus). |
| `Python::allow_threads` | `Python::detach` (rename) | pyo3 0.28 (2025) | Project pins 0.27.2 → MUST use `allow_threads`. Future pyo3 upgrade will require a rename pass. |
| rayon `par_bridge` for streaming parallelism | Explicit chunked `par_iter` | rayon 1.x current guidance | `par_bridge` has unbounded-buffer caveats; bounded chunks give explicit memory control (critical for u128 HashMap). |
| Sequential gzip decompression | (unchanged in Phase 2) | — | D-02 defers parallel gunzip to a Phase-4-gated backlog item. |

**Deprecated/outdated:**
- `pyo3::Python::allow_threads`: NOT deprecated in 0.27.2 (the project's version); `detach` is the 0.28+ rename. Do NOT migrate mid-phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `num_cpus::get()` is accessible (transitive via rayon) without adding `num_cpus` as a direct dep. | Standard Stack (Supporting) | LOW — if not directly importable, add `num_cpus = "0.4"` to `[dependencies]` (it is already a transitive dep, so no lockfile bloat). |
| A2 | The `KmerCounter::new` `_num_threads` param (`table.rs:44`) is the right place to plumb the resolved thread count for the PyO3 path, even though the actual pool config happens via `build_global` at the command/init level. | Pattern 3 / Pattern 4 | LOW — the param exists and is currently ignored; wiring it (even just for stats reporting) is safe. The real pool config is at the command/init level, not in the counter constructor. |
| A3 | The default `dashmap` hasher (RandomState) is acceptable for u128 keys at genome scale; no need for `ahash` integration. | Claude's Discretion (shard/hasher) | LOW — D-discretion explicitly says "use defaults unless benchmark shows contention." Phase 4 measures. |
| A4 | `CHUNK_SIZE = 4096` records is a reasonable starting chunk for bounded buffering. | Pattern 2 | LOW — explicitly Claude-discretion ("exact chunk size is the planner's call"); the planner can tune. |
| A5 | `merge.rs`'s existing `.expect()` on `build_global` is the only second-caller site; no other code calls `build_global`. | Pitfall 3 | MEDIUM — a grep confirms only `merge.rs:348,357` call it today, but the planner should re-grep before assuming. |
| A6 | The `pyrustkmer` wheel build (`maturin`) will pick up the new `dashmap` dep automatically via the `rustkmer` path dependency; no `pyo3/Cargo.toml` change needed. | Standard Stack | LOW — `pyo3/Cargo.toml` depends on `rustkmer = { path = ".." }`, so dep additions in the root `Cargo.toml` flow through. |

**If this table is empty:** (not empty — 6 assumptions; A1–A4 are LOW risk, A5 is MEDIUM and warrants a planner grep, A6 is LOW.)

## Open Questions

1. **Should `add_kmer` and `add_sequence` also release the GIL?**
   - What we know: `add_from_fastq` / `add_from_fasta` are the heavy counting methods that justify GIL release. `add_kmer` (single k-mer) and `add_sequence` (short string) are tiny workloads.
   - What's unclear: whether the overhead of `allow_threads` (GIL release/reacquire) outweighs the benefit for sub-millisecond operations.
   - Recommendation: planner should have the executor wrap `add_from_fastq`/`add_from_fasta` in `allow_threads` (clear win) and leave `add_kmer`/`add_sequence` holding the GIL unless a benchmark shows otherwise. Document the decision in the plan.

2. **Exact `CHUNK_SIZE` for bounded buffering (D-discretion)**
   - What we know: must be bounded (memory); too small → scheduling overhead dominates; too large → memory blowup + tail latency.
   - What's unclear: the right value for CRR1936095-scale reads (150bp PE, ~17M reads per split part).
   - Recommendation: planner parameterizes as a `const CHUNK_SIZE: usize` (start 4096); Phase 4 benchmark sweeps it. Not blocking.

3. **Whether `config.kmer_counting.threads` (already populated by `manager.rs:333`) should be the source of truth for `RUSTKMER_THREADS`, or whether `execute_count` reads the env var directly.**
   - What we know: the config layer already parses `RUSTKMER_THREADS` into `config.kmer_counting.threads`. The existing `merge.rs` reads `RAYON_NUM_THREADS` directly via `std::env::var`, NOT through the config layer.
   - What's unclear: whether to route count's thread resolution through `ConfigManager` (consistent with the layered-config pattern) or mirror merge's direct-env-read (consistent with the existing merge path).
   - Recommendation: planner mirrors merge's direct-env-read for `RAYON_NUM_THREADS` (consistency with merge) but routes `RUSTKMER_THREADS` through the config layer (it's already parsed there). Either way, the precedence chain (D-07) is the contract.

## Environment Availability

> Phase 2 depends on the existing Rust + Python toolchain plus the new `dashmap` crate. No new external runtimes/services.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Rust stable toolchain | All Rust code | ✓ (per CLAUDE.md, 1.80+) | stable | — |
| `rayon` | Parallelism (D-01) | ✓ (already a dep) | 1.8+ (Cargo.lock) | — |
| `dashmap` | Concurrent counter (D-04) | ✗ (not yet) | 6.1 / 6.2.1 (crates.io) | None — required dep; will be added |
| `pyo3` | Python bindings (D-08) | ✓ (pinned) | 0.27.2 | — |
| `maturin` | pyrustkmer wheel build | ✓ (CI uses it) | >=1.0,<2.0 | — |
| `proptest` | D-10 property tests | ✓ (dev-dep) | 1.5 | — |
| CRR1936095 dataset | Human-scale validation | ✓ (local, per PROJECT.md) | — | Slice/synthetic (BENCH-04, Phase 4) |

**Missing dependencies with no fallback:** none. `dashmap` is the only addition and it is available on crates.io (verified).

**Missing dependencies with fallback:** none.

## Validation Architecture

> `workflow.nyquist_validation` is enabled in `.planning/config.json` (absent key treated as enabled). This section is REQUIRED.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `cargo test` (built-in) + `proptest 1.5` (dev-dep) + `pytest 8.4+` (pyo3/tests/) |
| Config file | Root: none (inline `#[cfg(test)]`); pyo3: `pyo3/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cargo test --test parallel_count_tests` |
| Full suite command | `cargo test` (root) + `cargo test` (pyo3) + `maturin develop && pytest pyo3/tests/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PCOUNT-01 | `count --threads N` uses N threads; default uses num_cpus; `RUSTKMER_THREADS` env respected | unit + integration | `cargo test --test parallel_count_tests -- test_thread_resolution` | ❌ Wave 0 (plan 02-04) |
| PCOUNT-02 | DashMap swap compiles + `increment` is atomic per-key | unit (inline in `table.rs`) | `cargo test --lib hash::table::tests` | ✅ (existing, will extend) |
| PCOUNT-03 | `PyCounter(k, canonical, threads=4)` releases GIL; counting parallelizes | integration (pytest) | `pytest pyo3/tests/test_counter.py::test_parallel_counting` | ❌ Wave 0 (plan 02-04) |
| PCOUNT-04 | `--threads 1` vs `--threads N` produce identical count maps | integration (differential) | `cargo test --test parallel_count_tests -- differential_threads_1_vs_n` | ❌ Wave 0 (plan 02-04) |
| (cross-cutting) | Default-sort produces deterministic output run-to-run | integration | `cargo test --test parallel_count_tests -- deterministic_sorted_output` | ❌ Wave 0 (plan 02-04) |
| (cross-cutting) | Overflow error still fires at u32::MAX per k-mer | unit (inline in `table.rs`) | `cargo test --lib hash::table::tests::test_overflow` | ❌ Wave 0 (extend existing) |

### Sampling Rate
- **Per task commit:** `cargo test --test parallel_count_tests` (fast differential subset) + `cargo clippy -D warnings` (the FOUND-01 gate must stay green on both crates).
- **Per wave merge:** `cargo test` (full root suite) + `cargo test` (pyo3) + `maturin develop && pytest pyo3/tests/` (Python contract).
- **Phase gate:** Full suite green before `/gsd-verify-work`. Differential test passes for all D-13 cells (`k ∈ {21,32,64}` × canonical × ≥2 thread counts).

### The Commutativity Property (why 1-vs-N is a sharp detector)
K-mer counting is integer addition: `count(k) = sum over each occurrence of k of 1`. Addition is commutative (`a+b == b+a`) and associative (`(a+b)+c == a+(b+c)`). Therefore the final count for each k-mer is **mathematically independent of the order or parallelism of increments**. Consequence: if `--threads 1` and `--threads N` produce different count maps, the ONLY possible cause is a concurrency bug (lost update — two workers both read `c`, both write `c+1`, losing one increment; or double count — a worker reads stale state and inserts where it should have modified). This makes the differential test a high-signal, low-noise detector: no flakiness from "benign ordering differences," because there are no benign ordering differences.

### Differential Test Dimensions (guards PCOUNT-04)
| Axis | Values | Why |
|------|--------|-----|
| Thread count | `{1, 2, N}` where N = `num_cpus::get()` | 1 is the sequential baseline; 2 catches the simplest races; N stresses the sharded map. |
| k-mer width | `{21, 32, 64}` | D-13 matrix; exercises u128 at all bit-fill densities (21 = sparse, 64 = full). |
| Canonical | `{true, false}` | D-13 matrix; canonical adds a per-record computation step that interleaves with increment. |
| Input scale | `{tiny fixture, medium slice, large}` | tiny = fast feedback; medium = catches most bugs; large = stress (CRR1936095 slice if available). |
| Input shape | `{FASTA, FASTQ, gzipped}` | covers both `process_fasta_file` and `process_fastq_file` parallel paths + the gzip single-threaded producer. |

### Wave 0 Gaps
- [ ] `tests/parallel_count_tests.rs` — the NEW differential test binary (covers PCOUNT-01, PCOUNT-04). Reuses `tests/common/` factories + `tests/fixtures/`.
- [ ] `tests/fixtures/parallel_count_baseline/` — pre-refactor count MAPS (JSON, not bytes) captured via the golden-capture-first template (D-10). One per D-13 cell.
- [ ] `pyo3/tests/test_parallel_counter.py` — PyCounter threads kwarg + GIL release test (covers PCOUNT-03). Skip if `pyrustkmer` not importable.
- [ ] Extend `src/hash/table.rs` inline tests: add `test_increment_atomic_under_concurrency` (spawn N threads incrementing the same k-mer, assert final count == N) and `test_overflow_preserved` (increment a k-mer to u32::MAX, assert next increment errors).

*(Framework install: none — `cargo test`, `proptest`, and `pytest` are all already present.)*

## Security Domain

> `security_enforcement: true` in `.planning/config.json` (`security_asvs_level: 1`, `security_block_on: "high"`).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Local CLI/library; no networked auth. |
| V3 Session Management | no | No sessions; per-invocation only. |
| V4 Access Control | no | No privileged resources; file-system permissions suffice. |
| V5 Input Validation | yes | clap derive validates `--threads` (usize); reject `< 1` (D-discretion: "mirror InvalidKmerSize style"). k-mer size validation already at `count.rs:42`. |
| V6 Cryptography | no | No crypto in this phase. (Existing `sha2` use is for golden-test sha256, not security.) |
| V7 Error Handling & Logging | yes | Preserve `KmerError::InvalidKmerSize` style for the new `--threads < 1` error (D-discretion). Do NOT unwrap rayon pool config in library paths (Pitfall 3). |
| V8 Data Protection | no | No sensitive data; `.rkdb` is genomic, not PII. |
| V9 Communications | no | No network. |
| V10 Business Logic | yes | The commutativity property (Validation Architecture) is the business-logic invariant: count results MUST be thread-count-independent (PCOUNT-04). |

### Known Threat Patterns for the Rust + rayon + dashmap + PyO3 stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Data race on shared mutable state (lost/double count) | Tampering | `DashMap::entry().and_modify().or_insert()` atomic upsert (Pattern 1); 1-vs-N differential test (D-10). |
| Deadlock from nested DashMap references | Denial of Service | Never hold a `Ref`/`RefMut`/`Entry` across another DashMap call (Pitfall 2); dashmap docs.rs locking guarantees. |
| GIL violation (UB from Python object access without GIL) | Tampering / EoP | `py.allow_threads` closure captures ONLY `Send` Rust types (Pattern 4); PyO3's `Send` bound enforcement catches violations at compile time. |
| rayon `build_global` double-call panic | Denial of Service | Tolerate `Err` from `build_global` (Pitfall 3); centralize pool init. |
| Overflow wrapping (silent count corruption) | Tampering | Preserve `table.rs:75-80` error-on-u32::MAX (D-discretion); flag-then-check pattern (Pattern 1). |

**Security-relevant carry-over from CONCERNS.md:** the `unsafe { env::set_var }` soundness note (`config/manager.rs`) is pre-existing and NOT touched by this phase; the new `RUSTKMER_THREADS` read uses `env::var` (immutable, safe), not `set_var`.

## Sources

### Primary (HIGH confidence)
- **Codebase grep + Read** (2026-07-01): `src/hash/table.rs`, `src/cli/commands/count.rs`, `pyo3/src/counter.rs`, `src/cli/args.rs`, `src/config/manager.rs`, `src/io/fastq.rs`, `src/cli/commands/merge.rs`, `Cargo.toml`, `pyo3/Cargo.toml`, `tests/golden_tests.rs`, `tests/golden_generate.rs`, `tests/common/mod.rs`, `tests/round_trip_tests.rs`. Every integration point claim is grounded in the actual source.
- **`gsd-tools query package-legitimacy check`** (2026-07-01): dashmap/rayon/num_cpus all verdict `OK` (verifies existence, downloads, source repo).
- **crates.io API** (2026-07-01): `dashmap` max_stable = 6.2.1; dashmap 6.1.0 deps include `hashbrown ^0.14.0`; dashmap 6.2.1 deps include `hashbrown ^0.14.5` (confirms no duplicate-hashbrown claim).
- **Cargo.lock** (2026-07-01): hashbrown 0.14.5 + 0.16.1 already present (0.16.1 from `statrs`, unrelated); dashmap not yet present.

### Secondary (MEDIUM confidence)
- **docs.rs/dashmap** (via mcp__web_reader__webReader, 2026-07-01): `DashMap` struct page + `Entry` enum page. Confirmed `entry().and_modify(FnOnce(&mut V) -> Self).or_insert(V) -> RefMut` signatures; confirmed "May deadlock if called when holding any sort of reference into the map" locking warning.
- **rayon docs.rs + GitHub** (via WebSearch, 2026-07-01): `ThreadPoolBuilder::build_global` returns `Err` (not panic) on second call; `num_threads(0)` or unset → rayon auto-selects = num logical CPUs.
- **pyo3 parallelism guide + CHANGELOG** (via WebSearch, 2026-07-01): `Python::allow_threads` is the 0.27.2 API; `Python::detach` rename landed in 0.28 (PR #5221). Project pins 0.27.2 → must use `allow_threads`.
- **rayon GitHub issue #210 + community** (via WebSearch, 2026-07-01): `par_bridge` has unbounded-buffer caveats; explicit chunked `par_iter` preferred for IO-bound producers.

### Tertiary (LOW confidence)
- None. All claims are either codebase-verified or sourced from official docs (`[CITED]`) / registry (`[VERIFIED]`). The 6 assumptions in the Assumptions Log are the only `[ASSUMED]` items.

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — dashmap/rayon/pyo3 versions and compat verified via crates.io API + Cargo.lock + docs.rs; legitimacy gate clean.
- Architecture: **HIGH** — every integration point grounded in actual source (Read, not assumed); patterns (dashmap `entry`, rayon chunked `par_iter`, pyo3 `allow_threads`) verified against official docs.
- Pitfalls: **HIGH** — Pitfall 1/2/3 directly from docs.rs + existing merge.rs code; Pitfall 4/5 from PyO3 docs + existing test layering (read, not assumed); Pitfall 6 from the `and_modify` signature on docs.rs.
- Validation: **HIGH** — test infrastructure (golden fixtures, golden_tests.rs, proptest, common factories) all confirmed via Read; the commutativity argument is mathematical, not empirical.

**Research date:** 2026-07-01
**Valid until:** 2026-07-31 (30 days — stable stack; the only fast-moving piece is pyo3's `allow_threads`→`detach` rename, which is locked by the project's 0.27.2 pin)
