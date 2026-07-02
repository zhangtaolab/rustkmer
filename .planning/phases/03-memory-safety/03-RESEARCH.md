# Phase 3: Memory Safety - Research

**Researched:** 2026-07-02
**Domain:** Bounded-memory k-mer merge (Rust streaming/external-sort + RAII temp-file cleanup under `panic="abort"`) and dense in-memory k-mer storage (width-selected `u64`/`u128` counter, `.rkdb` v2 on-disk compatibility preserved)
**Confidence:** HIGH

## Summary

Phase 3 closes two memory-safety holes in rustkmer. (1) **The merge side is gap-filling, not greenfield.** A code scout (locked in `03-CONTEXT.md`) found the streaming/prefix-cache machinery, `--max-memory`/`--merge-mode` flags, the `get_default_memory_limit()` auto-budget, and RAII guards on the streaming path all already exist. The work is: fix the estimator's OOM-on-estimate bug (it calls `RKDatabase::from_file_path` per input — loading every entry into RAM *during the estimate*), flip the default so streaming is the safe path with hard admission control, port the RAII pattern to the prefix-cache path (which today only cleans up on the success branch), and route `PyDatabase.merge` through the bounded path with parameters exposed. (2) **The dense-storage side is the larger net-new build** — swap the in-memory counter key from `u128` to a width-selected `u64` for `k ≤ 32`, roughly halving counting memory for the common case, while the `.rkdb` v2 on-disk format stays byte-identical (RAM-only dense, D-03).

Three load-bearing technical facts ground the plan, all verified against the source this session: **(a)** the 42-byte `DatabaseHeader` (`src/database/format.rs:60-165`) already persists `total_kmers` as a `u64` at a fixed byte offset — readable by deserializing only the header, no entry materialization, which is the direct fix for the estimator bug (D-01). **(b)** The release profile sets `panic = "abort"` (`Cargo.toml:112`) — verified via the `tempfile` docs and Ferrous Systems training material that `Drop` does **not** run on abort/SIGKILL/`process::exit`, so RAII alone cannot guarantee cleanup; D-06's process-unique subdir + startup stale-shard sweep is the real defense against `kill -9`/power loss, not `Drop` ([CITED: docs.rs/tempfile]). **(c)** The `u64` and `u128` encoders pack the same k-mer to *different* bit positions (`encode_kmer_bytes` aligns to bit 64, `encode_kmer_bytes_u128` to bit 128 — `src/kmer/encoding.rs:49,221`), so DENSE-03 correctness must be verified at the **decoded (kmer-string, count)** level, never via raw-integer equality (D-04).

**Primary recommendation:** Decompose into the roadmap's five seed plans. Merge side: 03-01 (estimator fix + default flip + hard admission control — D-01/D-02), 03-02 (RAII on prefix-cache path + process-unique subdir + startup sweep — D-06), 03-05 (PyDatabase bounded routing — MERGE-04). Dense side: 03-03 (width-selected counter — D-03), 03-04 (decoded-level differential correctness against existing golden baselines — D-04/D-05). The merge side is small; the dense side is where the implementation risk lives. **Capture a pre-refactor u128 differential baseline first** if any new fixture dimension is added (Phase 1 D-10 discipline) — but the existing `tests/fixtures/parallel_count_baseline/k{21,32,64}_{canon,noncanon}.json` + 12 golden `.rkdb` files already cover the D-13 matrix and need no re-derivation.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01: Fix the estimator + hard-route to streaming.** `should_use_streaming()` obtains `total_kmers` by calling `RKDatabase::from_file_path(path)` per input — which materializes every entry, OOMing *during the estimate*. Fix: estimate from header metadata (or `file_size / 20` × safety factor) WITHOUT materializing entries. Hard-route to streaming when estimate exceeds budget (not advisory). Keep `get_default_memory_limit()` (~50% system RAM, 32 GB fallback) as the zero-config default; `--max-memory` is the explicit override.
- **D-02: Retain `merge_databases_inmemory` behind `--merge-mode memory` + auto-small.** Streaming is the safe default. `memory` mode must reject (or loud-warn) when estimate exceeds budget — reject is safer for MERGE-01's "no longer OOM" promise. Removing the in-memory path would break existing `--merge-mode memory` callers for no milestone benefit.
- **D-03: Dense `u64` is RAM-only — `.rkdb` v2 on-disk stays 16-byte u128 + 4-byte u32.** The u128→u64 packing applies to in-memory counting/merge structures only; `KmerEntry` on disk stays 20-byte little-endian v2. Write path widens `u64`→`u128` (zero-extension) when serializing. On-disk dense packing deferred to v2.
- **D-04: Verify dense correctness at the decoded (kmer-string, count) level, NOT the raw-integer level.** `u64` and `u128` encoders pack bits differently — same biological k-mer yields different raw integer values in the two widths. Differential compares decoded k-mer strings + counts against Phase 1/2 golden baselines (k ∈ {21, 32, 64} × canonical × sorted).
- **D-05: `u128`-vs-`u64` differential is the sharp correctness tool** (analog to Phase 2's `--threads 1`-vs-`N` differential). K-mer counting is integer addition (commutative/associative), so any count divergence between the `u64` and `u128` paths on the same input is a packing/canonicalization bug.
- **D-06: RAII on the prefix-cache path + process-unique temp subdir `rustkmer-merge-<pid>-<rand>/` + startup stale-shard sweep. NO signal handler. NOT resumable.** Streaming path already has RAII (`TempFileManager::Drop`, `StreamingMergeIterator::Drop`); prefix-cache path does NOT (only `remove_file`s on success at `prefix_cache_merge.rs:322-326`). Add an RAII guard mirroring the streaming path. Process-unique subdir makes orphan detection unambiguous + avoids concurrent-merge collisions. Startup sweep defends against `kill -9`/power loss (because `Drop` does not run under `panic="abort"`/SIGTERM/SIGKILL).

### Claude's Discretion
- **`PackedKmer` representation:** enum `Kmer::U64(u64)`/`Kmer::U128(u128)` vs parallel `KmerCounterU64` type vs generic-over-width — pick the lowest-blast-radius option that preserves the public API (Phase 2 D-05 discipline).
- **Estimator source:** header `total_kmers` vs `file_size / 20` vs both-with-fallback — planner's call, as long as it does NOT load entries.
- **Startup-sweep TTL / orphan-detection heuristic** (PID-liveness vs age-based TTL) — age-based is simpler and portable (no `/proc` on macOS).
- **`memory` mode over-budget behavior** (reject vs loud-warn) — planner picks; reject is safer.
- **Whether dense u64 applies to the in-memory `RKDatabase`/`DatabaseQuery` read path:** out of scope unless zero-cost while touching the counter. Default: leave the read path on `u128`.
- **Exactly how `PyDatabase.merge` exposes budget/strategy** (kwargs `max_memory=`/`merge_mode=` mirroring CLI) — planner decides, but MUST route through the same bounded core path (MERGE-04).

### Deferred Ideas (OUT OF SCOPE)
- **On-disk dense `u64` packing** (`.rkdb` v2 dense flag or v3) with migration — deferred to v2. RAM-only u64 (D-03) satisfies the milestone's "halving counting memory" goal without a format bump.
- **Adaptive / configurable shard granularity** (5-/6-prefix) for the prefix-cache merge — `MINIM-03` (v2).
- **Resumable streaming merge** (checkpoint/resume after crash) — v2.
- **Signal-handler-based graceful Ctrl-C cleanup** (`ctrlc` crate) — v2; soundness-sensitive scope creep.
- **Minimizer / signature-partitioned bounded-memory *counting*** (`MINIM-01`/`MINIM-02`) — v2.
- **Configurable counter width / saturation warning** (`SAT-01`/`SAT-02`) — v2.
- **Dense u64 on the query/read path** (`DatabaseQuery`, mmap, in-memory `RKDatabase`) — out of scope; query memory is not the stated bottleneck.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MERGE-01 | Merge defaults to the streaming/external-sort path — human-scale merges no longer OOM | §Architecture Patterns (Default-flip + hard admission control); §Common Pitfalls (Pitfall 1 — estimator OOM-on-estimate). The estimator fix (D-01) at `format.rs:692-708` is the single load-bearing change. Validation: §Validation Architecture MERGE-01 row — synthetic oversized-input + tiny-budget routing test. |
| MERGE-02 | Memory-budget admission control — estimate required memory, route to streaming when estimate exceeds budget | §Code Examples (header-only read path); §Common Pitfalls (Pitfall 2 — in-memory path has no bound). `DatabaseHeader::read_from` at `format.rs:112-165` reads `total_kmers` from a 42-byte header WITHOUT loading entries. Validation: §Validation Architecture MERGE-02 row — budget-threshold branch test. |
| MERGE-03 | Failed/interrupted streaming merges clean up temp shard files (RAII guard) — no silent disk exhaustion | §Architecture Patterns (RAII mirror + process-unique subdir + startup sweep); §Common Pitfalls (Pitfall 3 — `panic="abort"` skips `Drop`). The cleanup gap is at `prefix_cache_merge.rs:322-326` (success-only `remove_file`). Validation: §Validation Architecture MERGE-03 row — panic-injection + orphan-dir-sweep tests. |
| MERGE-04 | `pyrustkmer`'s `PyDatabase` merge uses the same bounded path as the CLI | §Architecture Patterns (PyDatabase bounded routing); §Code Examples (kwargs signature). Current site: `pyo3/src/database.rs:1346-1392` uses `MergeConfig::default()` with no params. Validation: §Validation Architecture MERGE-04 row — Python contract test asserting kwargs thread through. |
| DENSE-01 | K-mers for k ≤ 32 stored as `u64` (8 bytes) instead of `u128` — roughly halving counting memory | §Architecture Patterns (PackedKmer width-selection — recommended option A); §Code Examples (DashMap enum-key). Swap site: `src/hash/table.rs:22` `table: DashMap<u128, u32>`. Validation: §Validation Architecture DENSE-01 row — `memory_usage()` assertion showing ~50% reduction for k=21. |
| DENSE-02 | Dense storage transparent to existing readers — `.rkdb` v2 backward/forward compatible | §Architecture Patterns (RAM-only dense — disk stays v2 20-byte); §Common Pitfalls (Pitfall 4 — u64/u128 bit-alignment difference). 12 golden `.rkdb` + sha256 baselines (`tests/fixtures/golden_manifest.sha256`) must still match post-dense. Validation: §Validation Architecture DENSE-02 row — golden sha256 re-verification. |
| DENSE-03 | Canonicalization stays correct under `u64` packing — counts match the `u128` path exactly | §Architecture Patterns (Decoded-level differential — D-04/D-05); §Common Pitfalls (Pitfall 5 — raw-integer equality is wrong). u64 encode/canonical/decode primitives already exist (`encoding.rs:49,136,310`). Validation: §Validation Architecture DENSE-03 row — u64-vs-u128 differential on decoded (string, count) maps across the D-13 matrix. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Merge-strategy dispatch + admission control | Core library (`database/format.rs::merge_databases`, `should_use_streaming`) | CLI config (`cli/commands/merge.rs::MergeConfig` assembly) | The estimator and the hard-route decision are pure functions of file metadata + budget; the core owns the routing so both CLI and PyO3 inherit it. CLI only assembles `MergeConfig` from flags. |
| Header-only `total_kmers` estimation | Core library (`database/format.rs::DatabaseHeader::read_from`) | — | Reading 42 bytes without materializing entries is a header-deserialization concern; colocating with `DatabaseHeader` keeps the format's read logic in one place (CONCERNS anti-pattern: "header reconciliation in every reader"). |
| Temp-shard RAII + cleanup | Core library (`database/streaming_merge.rs::TempFileManager`, new prefix-cache RAII guard) | — | The streaming path's `TempFileManager::Drop` is the canonical pattern; mirror it on the prefix-cache path. The process-unique subdir + startup sweep are also core-library concerns (cross-cutting merge infrastructure). |
| Width-selected in-memory counter | Core library (`hash/table.rs::KmerCounter`) | — | `KmerCounter` owns the `DashMap`; the `u128`→width-selected swap is internal (Phase 2 D-05 discipline). Width selection happens at `KmerCounter::new(kmer_length, …)` where `kmer_length` is known. |
| K-mer encode/decode/canonical primitives | Core library (`kmer/encoding.rs`, `kmer/canonical.rs`) | — | Both u64 and u128 primitives already exist; Phase 3 wires the counter to the right one. The encode path is called from the count worker, but the primitive selection is the counter's responsibility. |
| PyDatabase bounded merge routing | PyO3 binding layer (`pyo3/src/database.rs::PyDatabase::merge`) | Core library (`RKDatabase::merge_databases`) | The binding layer translates Python kwargs (`max_memory=`, `merge_mode=`) into `MergeConfig` and calls the same core `merge_databases` — inherits the bounded path automatically (D-01 fix lands in core, flows to both surfaces). |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `tempfile` | `3.24.0` (Cargo.lock); declared `^3.12` in `[dev-dependencies]` (`Cargo.toml:96`) | `TempDir` for the process-unique merge subdir (`rustkmer-merge-<pid>-<rand>/`); `NamedTempFile` not required | The locked decision (D-06). Mature Rust crate (Stebalien/tempfile, since 2015, ~11.3M weekly downloads). **ACTION REQUIRED:** currently in `[dev-dependencies]` only — must move to `[dependencies]` to use `TempDir` in production merge code. `[VERIFIED: crates.io + Cargo.lock:tempfile 3.24.0]` — legitimacy gate `OK`. |
| `dashmap` | `6.2.1` (`Cargo.toml:61`, `Cargo.lock`) | Width-selected `DashMap<KmerKey, u32>` for the dense counter (D-03) | Already a dep (Phase 2 PCOUNT-02). Legitimacy gate `OK` (xacrimon/dashmap, since 2019, ~5.1M weekly). The dense swap reuses this — no new dep. `[VERIFIED: Cargo.toml + Cargo.lock]` |
| `rayon` | `1.8` declared (`Cargo.toml:56`), transitively 1.10 | Parallel prefix-bucket processing in `prefix_cache_merge.rs` | Already in the dep graph; no change for Phase 3. `[VERIFIED: Cargo.toml]` |
| `sys-info` | `0.9` (`Cargo.toml:89`) | System memory detection | **Already a dep but NOT currently used by `get_default_memory_limit()`** — that fn (`merge_config.rs:142-163`) reads `/proc/meminfo` (Linux-only) and falls back to a hardcoded 32 GB. macOS has no `/proc`; the 32 GB constant is the de-facto macOS behavior. Phase 3 may optionally wire `sys_info::mem_info()` for cross-platform accuracy, but D-01 does not require it. `[VERIFIED: Cargo.toml + source grep]` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `proptest` | `1.5` (`Cargo.toml:97`) | Property-based dense-correctness tests (D-05 differential on random small inputs) | Already a dev-dep. Reuse for u64-vs-u128 differential property tests. Note CONCERNS tech-debt: proptest appears in BOTH `[dependencies]` (`:53`) and `[dev-dependencies]` (`:95`) — production code never imports it. Phase 3 should not worsen this; if anything, flag it. `[VERIFIED: Cargo.toml]` |
| `rand` / `rand_chacha` | `0.8` / `0.3` (`Cargo.toml:106-107`) | Random component of the process-unique subdir name (`<rand>`) | Already dev-deps. **Note:** `tempfile::TempDir` already provides process-unique naming internally via `Builder::new().prefix("rustkmer-merge-").rand_bytes(N).tempdir()` — likely NO direct `rand` call needed in production code. `[VERIFIED: Cargo.toml]` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `tempfile::TempDir` for the merge subdir | `std::env::temp_dir()` + manual `format!("rustkmer-merge-{}-{}", pid, rand)` + `fs::create_dir_all` | `TempDir` gives RAII `Drop` cleanup on scope-exit for free (still useful for the in-process case, even though it doesn't survive abort). Manual approach = more code + a hand-rolled `Drop` impl. Prefer `TempDir`. |
| `sys_info::mem_info()` for cross-platform budget | Keep `/proc/meminfo` + 32 GB fallback | `sys_info` is already a dep and works on macOS+Linux. But D-01 doesn't mandate changing the budget source — only the estimator input. Planner's call (Claude's discretion). |
| Generic-over-width counter (`KmerCounter<T>`) | Enum `KmerKey::U64(u64)`/`U128(u128)` (recommended) | Generic requires `T: Hash + Eq + Copy` bound pollution across the public API; enum is monomorphic and keeps `DashMap<KmerKey, u32>` as one concrete type. See §Architecture Patterns for the blast-radius analysis. |

**Installation:**
```bash
# Move tempfile from [dev-dependencies] to [dependencies] (one-line Cargo.toml edit)
# No new crates needed — dashmap, rayon, sys-info, proptest, rand already in the graph.
```

**Version verification:** Confirmed via `Cargo.lock`: `tempfile 3.24.0`, `dashmap 6.2.1`, `rayon 1.10`, `sys-info 0.9`, `proptest 1.5`, `rand 0.8`, `rand_chacha 0.3` — all current and in the dependency graph.

## Package Legitimacy Audit

> No new packages are introduced in Phase 3. `tempfile` is promoted from `[dev-dependencies]` to `[dependencies]` (same crate, same version, already vetted in the Phase 1 CI gate).

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `tempfile` | crates.io | ~11 yrs (since 2015-04-14) | ~11.3M / week | github.com/Stebalien/tempfile | OK | Approved (promote dev→dep) |
| `dashmap` | crates.io | ~7 yrs (since 2019-08-25) | ~5.1M / week | github.com/xacrimon/dashmap | OK | Approved (already dep, reused) |

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram — Merge Decision Flow

```text
                ┌─────────────────────────────────────────────┐
                │  CLI (merge.rs) / PyDatabase.merge           │
                │  assembles MergeConfig {                     │
                │    max_memory_usage, merge_mode,             │
                │    use_prefix_cache, temp_dir, ...           │
                │  }                                            │
                └──────────────────────┬───────────────────────┘
                                       │
                                       ▼
        ┌──────────────────────────────────────────────────────────┐
        │  RKDatabase::merge_databases(input_paths, config)         │
        │  (src/database/format.rs:640)                             │
        └──────────────────────┬───────────────────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────────────────┐
        │  DECISION A: use_prefix_cache?                            │
        │  (explicit flag, short-circuits admission control)        │
        └──────┬───────────────────────────────────┬───────────────┘
               │ yes                               │ no
               ▼                                   ▼
   ┌───────────────────────┐         ┌─────────────────────────────┐
   │ merge_databases_      │         │  ESTIMATOR (D-01 fix):       │
   │ prefix_cache()        │         │  read 42-byte header per     │
   │ (4-prefix/256-bucket  │         │  input → sum total_kmers     │
   │ external sort)        │         │  (NO entry materialization)  │
   │                       │         │  est = total_kmers × 24 B    │
   │ [needs RAII guard —  │         │  fallback: file_size / 20    │
   │  D-06 gap]            │         └────────────┬────────────────┘
   └───────────────────────┘                      │
                                                  ▼
        ┌──────────────────────────────────────────────────────────┐
        │  DECISION B (D-01 hard-route): est > max_memory_usage ?   │
        └──────┬───────────────────────────────────┬───────────────┘
               │ yes                               │ no
               ▼                                   ▼
   ┌───────────────────────┐       ┌───────────────────────────────┐
   │ merge_databases_      │       │  DECISION C: merge_mode?       │
   │ streaming()           │       │  (explicit user choice)        │
   │ (ExternalMerger,      │       └───┬───────────┬───────────┬────┘
   │  k-way heap merge,    │           │auto       │memory     │streaming
   │  TempFileManager RAII │           ▼           ▼           ▼
   │  already present)     │       ┌──────┐  ┌──────────┐  ┌─────────┐
   └───────────────────────┘       │small │  │ D-02:    │  │streaming│
                                   │in-mem│  │ reject   │  │         │
                                   │      │  │ if over  │  │         │
                                   └──────┘  │ budget   │  └─────────┘
                                             └──────────┘
   All paths write to a process-unique subdir rustkmer-merge-<pid>-<rand>/
   under temp_dir; startup sweep removes orphaned subdirs (D-06)
```

The reader should be able to trace: a user invokes merge → `MergeConfig` is assembled → the estimator reads only headers → if the estimate exceeds budget, the merge is hard-routed to streaming regardless of `merge_mode` (except `memory` mode which errors). Every temp shard lives under a process-unique subdir that the startup sweep cleans if the process died leaving orphans.

### Recommended Project Structure
```
src/
├── database/
│   ├── format.rs              # merge_databases dispatch, should_use_streaming (D-01 fix),
│   │                          # merge_databases_inmemory (D-02 gate), DatabaseHeader (read total_kmers)
│   ├── streaming_merge.rs     # TempFileManager (RAII pattern to mirror), StreamingMergeIterator::Drop
│   ├── prefix_cache_merge.rs  # ADD RAII guard mirroring TempFileManager; centralize const RECORD_SIZE = 20;
│   │                          # write shards under process-unique subdir; accept startup-sweep hook
│   ├── merge_config.rs        # MergeConfig (add fields if needed), get_default_memory_limit (optionally sys_info)
│   └── temp_lifecycle.rs      # (NEW, optional) process-unique subdir helper + startup sweep fn
├── hash/
│   └── table.rs               # KmerCounter (DashMap key swap u128 → KmerKey width-selected)
├── kmer/
│   ├── encoding.rs            # u64 + u128 primitives already present (no new code)
│   └── canonical.rs           # canonical_kmer_u128 present; ensure canonical_kmer_u64 path if missing
└── cli/commands/merge.rs      # MergeConfig assembly (unchanged surface), parse_memory_size
pyo3/src/
└── database.rs                # PyDatabase::merge — add max_memory/merge_mode kwargs (MERGE-04)
tests/
├── fixtures/                  # 12 golden .rkdb + parallel_count_baseline JSON (REUSE — do not re-derive)
└── (new) dense_differential_tests.rs, merge_cleanup_tests.rs
```

### Pattern 1: PackedKmer Width-Selection — Recommend Option A (Enum Key)

**What:** Replace `DashMap<u128, u32>` with `DashMap<KmerKey, u32>` where `KmerKey` is an enum selected at `KmerCounter::new` time based on `kmer_length`.

**When to use:** Whenever the counter is constructed with `kmer_length <= 32` (use `U64`); else `U128`.

**Blast-radius analysis (the deciding factor):**

| Option | Blast Radius | Public API Change? | DashMap Implication | Verdict |
|--------|--------------|---------------------|---------------------|---------|
| **A. Enum `KmerKey::U64(u64)` / `Kmer::U128(u128)`** | LOW — `table.rs` field type + `increment`/`get_count`/`get_all_counts` signatures take `KmerKey` internally; public methods keep accepting `u128` and widen internally OR the public surface stays `u128` and the counter converts at the boundary | No (if boundary conversion) or minor (if `KmerKey` leaks) | One concrete `DashMap<KmerKey, u32>` type; `KmerKey` derives `Hash+Eq+Copy+PartialEq` — dashmap works with any such key | **RECOMMENDED** |
| B. Parallel `KmerCounterU64` type | HIGH — duplicates the entire `KmerCounter` impl (`increment`, `merge`, `get_top_n`, `filter_by_count`, stats, `KmerCounterBuilder`); call sites in `count.rs`/`pyo3/src/counter.rs` must choose type at runtime → enum-of-counter or generic call site | Yes (new public type) | Two distinct DashMap types | Rejected — duplicates ~400 LOC |
| C. Generic `KmerCounter<T: Hash+Eq+Copy>` | MEDIUM-HIGH — `T` bound pollution propagates into `KmerCounterBuilder`, `CounterStats`, `pyo3::PyCounter` (PyO3 does not support generic `#[pyclass]` easily) | Yes (generic API) | One generic DashMap | Rejected — PyO3 friction + bound pollution |

**Recommendation:** Option A. Define:
```rust
// src/hash/key.rs (new small module) or inline in table.rs
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum KmerKey {
    /// k ≤ 32 — dense path (DENSE-01)
    U64(u64),
    /// 32 < k ≤ 64 — legacy width
    U128(u128),
}
```
At `KmerCounter::new(kmer_length, …)`: if `kmer_length <= MAX_KMER_SIZE_IN_U64` (32), the counter stores `KmerKey::U64`; else `KmerKey::U128`. The `increment(u128)` public signature can either (a) stay `u128` and the counter narrows internally (zero-cost when the high bits are zero for k≤32), or (b) be overloaded via a separate `increment_u64` — planner's call under Claude's discretion. The `memory_usage()` estimate at `table.rs:283` should branch on width (`U64 → 8+overhead`, `U128 → 16+overhead`).

**DashMap enum-key behavior:** `DashMap` requires `K: Hash + Eq` (same as `HashMap`). The derived `Hash`/`Eq` on `KmerKey` discriminate by variant first, then by inner value — so `KmerKey::U64(5)` and `KmerKey::U128(5)` hash to different buckets (no collision). Within a single counter, only one variant is ever inserted (width is fixed at construction), so this is correct. `[CITED: docs.rs/dashmap — DashMap<K,V,S> bounds: K: Clone + Send + Sync + Unpin, requires Hash + Eq via HashMap]` `[ASSUMED — derive behavior is standard Rust]`

**Example:**
```rust
// src/hash/table.rs (sketch)
use dashmap::DashMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum KmerKey {
    U64(u64),
    U128(u128),
}

pub struct KmerCounter {
    table: DashMap<KmerKey, u32>,  // was DashMap<u128, u32>
    kmer_length: usize,
    // ... (rest unchanged)
}

impl KmerCounter {
    pub fn new(kmer_length: usize, canonical_mode: bool, initial_capacity: usize, _num_threads: usize) -> ProcessingResult<Self> {
        if !(1..=64).contains(&kmer_length) {
            return Err(KmerError::InvalidKmerSize(kmer_length as u32).into());
        }
        Ok(Self {
            table: DashMap::with_capacity(initial_capacity),
            // width is implicit in how increment() packs — store a flag if needed
            kmer_length,
            // ...
        })
    }
}
```

### Pattern 2: Header-Only Estimator (D-01 Fix)

**What:** Replace `RKDatabase::from_file_path(path)?` per input (which loads every entry) with a header-only read.

**When to use:** In `should_use_streaming` (`format.rs:692-708`) and in `merge_databases` (`format.rs:644-652`) where `total_kmers` is summed.

**Why it fixes the OOM-on-estimate bug:** `DatabaseHeader::read_from` (`format.rs:112-165`) reads exactly 42 bytes (4 magic + 2 version + 1 kmer_size + 3 padding + 8 total_kmers + 1 flags + 7 padding + 8 data_offset + 8 index_offset) and returns. No `KmerEntry` is materialized. On a human-scale merge this is the difference between reading ~42 bytes × N files vs. loading ~3B entries into RAM.

**Fallback:** If the header read fails (corrupt magic, wrong version) OR `total_kmers == 0` (untrusted/legacy file), fall back to `file_metadata.len() / 20` (file size divided by the 20-byte record size). Apply a safety factor (e.g. `× 1.5`) to over-estimate and route to streaming conservatively.

**Example:**
```rust
// src/database/format.rs (sketch — D-01 fix)
fn estimate_total_kmers(path: &std::path::Path) -> crate::error::ProcessingResult<u64> {
    use std::fs::File;
    use std::io::BufReader;
    let file = File::open(path)
        .map_err(|e| crate::error::ProcessingError::io_error(e.to_string()))?;
    let mut reader = BufReader::new(file);
    // Header-only read — does NOT load entries (the fix for the OOM-on-estimate bug)
    match DatabaseHeader::read_from(&mut reader) {
        Ok(header) if header.total_kmers > 0 => Ok(header.total_kmers),
        _ => {
            // Fallback: file_size / RECORD_SIZE
            let meta = std::fs::metadata(path)
                .map_err(|e| crate::error::ProcessingError::io_error(e.to_string()))?;
            // RECORD_SIZE = 42 (header) + 20 * n entries; subtract header, divide
            let entries = meta.len().saturating_sub(42) / 20;
            Ok(entries)
        }
    }
}

fn should_use_streaming(
    input_paths: &[std::path::PathBuf],
    config: &crate::database::MergeConfig,
) -> crate::error::ProcessingResult<bool> {
    let mut total_kmers = 0u64;
    for path in input_paths {
        total_kmers += Self::estimate_total_kmers(path)?;  // header-only, no materialization
    }
    let estimated_memory = total_kmers as usize * 24;
    Ok(estimated_memory > config.max_memory_usage)
}
```

### Pattern 3: RAII Mirror for Prefix-Cache + Process-Unique Subdir (D-06)

**What:** Add an RAII guard on the prefix-cache path mirroring `TempFileManager` (`streaming_merge.rs:113-176`); write all temp shards under a process-unique subdir; sweep stale subdirs on merge start.

**When to use:** The prefix-cache path (`prefix_cache_merge.rs`) currently only `remove_file`s on the success branch (`:322-326`). Panic / early return / `kill` leaks shards.

**Why RAII alone is insufficient (the `panic="abort"` problem):**
The release profile sets `panic = "abort"` (`Cargo.toml:112`). Under abort, the runtime calls `abort()` immediately — **no stack unwinding, no `Drop`**. Verified via the `tempfile` crate docs and Ferrous Systems training: `TempDir` and `NamedTempFile` rely on `Drop` for cleanup; if destructors don't run (abort, SIGKILL, `process::exit`), the files persist on disk. `[CITED: docs.rs/tempfile — Resource Leaking section]` `[CITED: rust-training.ferrous-systems.com/latest/book/drop-panic-abort]`

| Scenario | Does `Drop` run? | Cleanup? |
|---|---|---|
| Normal scope exit | Yes | Yes (RAII works) |
| `panic!` with unwinding (default) | Yes (during unwind) | Yes |
| `panic = "abort"` (this project's release) | **No** | **No** |
| `std::process::exit()` | No | No |
| SIGTERM / SIGKILL | No | No |

**The D-06 defense in depth:**
1. **RAII** (in-process safety): `Drop` cleans up on normal scope exit and on `panic=unwind`. Handles the common case (early `return`, `?` propagation, logic error panic under test builds which use `panic=unwind`).
2. **Process-unique subdir** (`rustkmer-merge-<pid>-<rand>/`): makes orphan detection unambiguous (no collision with other live merges) and lets the sweep identify "this dir belongs to a dead process."
3. **Startup stale-shard sweep**: on merge start, scan `temp_dir` for `rustkmer-merge-*` dirs; remove those older than a TTL (age-based, portable — no `/proc` dependency). This is the real defense against abort/SIGKILL/power loss.

**Orphan-detection heuristic (Claude's discretion → recommend age-based TTL):**
- **Age-based TTL** (recommend): any `rustkmer-merge-*` dir with mtime older than e.g. 24h is removed. Simple, portable (works on macOS + Linux), no PID-liveness check. Risk: removes a long-running merge's subdir if it runs >24h — mitigate by touching mtime during the merge or choosing a generous TTL (e.g. 7 days).
- **PID-liveness** (rejected): parse `<pid>` from the dir name, check if that PID is live. Not portable (no `/proc` on macOS — would need `kill(pid, 0)` which has permission quirks), and PIDs wrap around (a rebooted process could reuse the PID).

**Using `tempfile::TempDir` for the process-unique subdir:**
```rust
// tempfile::TempDir gives process-unique naming + RAII Drop cleanup
use tempfile::TempDir;
let merge_subdir: TempDir = tempfile::Builder::new()
    .prefix("rustkmer-merge-")
    .rand_bytes(8)  // process-unique + collision-free
    .tempdir_in(&config.temp_dir)?;
// All temp shards written under merge_subdir.path()
// On normal return or panic=unwind, Drop removes the whole subdir recursively.
// Under panic=abort / SIGKILL, the startup sweep (next merge) cleans it up.
```
`TempDir::drop` removes the directory and all contents recursively — so individual `remove_file` calls become unnecessary when shards live under the `TempDir`.

**Startup sweep (sketch):**
```rust
fn sweep_stale_merge_dirs(temp_dir: &Path, ttl: std::time::Duration) {
    let cutoff = std::time::SystemTime::now() - ttl;
    if let Ok(entries) = std::fs::read_dir(temp_dir) {
        for entry in entries.flatten() {
            let name = entry.file_name();
            let name = name.to_string_lossy();
            if name.starts_with("rustkmer-merge-") {
                if let Ok(meta) = entry.metadata() {
                    if let Ok(mtime) = meta.modified() {
                        if mtime < cutoff {
                            let _ = std::fs::remove_dir_all(entry.path());
                            log::info!("Swept stale merge temp dir: {}", entry.path().display());
                        }
                    }
                }
            }
        }
    }
}
```

### Pattern 4: Decoded-Level Differential Correctness (D-04/D-05)

**What:** Verify dense correctness by comparing **decoded k-mer strings + counts** between the u64 and u128 paths, never raw integers.

**When to use:** Every DENSE-03 correctness assertion. The golden baselines are ground truth.

**Why raw-integer equality is wrong:** `encode_kmer_bytes` (u64, `encoding.rs:49`) left-shifts the final encoded value by `pos * 2` to align to bit 64. `encode_kmer_bytes_u128` (u128, `encoding.rs:221`) starts by shifting `bits_to_shift = 128 - length*2` to align to bit 128. So the same k-mer `"ATGC"` packs to `57 << 56` in u64 but `57 << 120` in u128 — different integers. Canonicalization (`min(kmer, revcomp)`) is width-internal: as long as encode→canonical→increment is self-consistent inside each width, per-k-mer **counts** match. The differential decodes both sides back to strings and compares `(String, u32)` maps.

**Baseline reuse:** Phase 1/2 committed 12 golden `.rkdb` files (`tests/fixtures/golden_k{21,32,64}_{canon,noncanon}_{sorted,unsorted}.rkdb`) + sha256 manifest + 6 parallel_count_baseline JSON maps. **Reuse directly** — D-13 coverage matrix `k ∈ {21, 32, 64} × canonical × sorted` already spans the u64 (k=21, k=32) and u128 (k=64) split. **Do not re-derive** (Phase 1 D-10 golden-capture-first discipline — the baselines exist and are the ground truth).

**⚠ Baseline-format caveat (discovered this session):** The parallel_count_baseline JSON files store **raw u128-encoded integer keys**, NOT decoded k-mer strings (e.g. `{"5749079041": 6, ...}`). The existing `baseline_matches_current` Phase 2 test compares within the same u128 path so integer keys are fine there. For the Phase 3 dense differential, the u64 path produces different integer keys → the test must **decode both sides to k-mer strings** before comparison, OR compare the u64 path's output (decoded) against the u128 golden `.rkdb` (decoded). Do not compare integer maps across widths.

**Example:**
```rust
// tests/dense_differential_tests.rs (sketch)
use rustkmer::kmer::encoding::{decode_kmer, decode_kmer_u128};

fn counter_to_decoded_map(counter: &KmerCounter, k: usize, width_is_u64: bool) -> HashMap<String, u32> {
    counter.get_all_counts().into_iter().map(|(kmer_int, count)| {
        let kmer_str = if width_is_u64 {
            decode_kmer(kmer_int as u64, k)              // u64 decoder, bit-aligned to 64
        } else {
            decode_kmer_u128(kmer_int, k)                // u128 decoder, bit-aligned to 128
        };
        (kmer_str, count)
    }).collect()
}

#[test]
fn dense_u64_matches_u128_on_k21_canon() {
    // Run the SAME input through a u64 counter (k=21) and a u128 counter (k=21)
    // ... (construct both, feed identical FASTA)
    let u64_map = counter_to_decoded_map(&u64_counter, 21, true);
    let u128_map = counter_to_decoded_map(&u128_counter, 21, false);
    assert_eq!(u64_map, u128_map, "u64 and u128 paths must produce identical decoded (kmer, count) maps (DENSE-03 / D-04)");
}
```

### Anti-Patterns to Avoid
- **Raw-integer equality between u64 and u128 paths:** will fail and is meaningless (D-04). Always decode to strings first.
- **Removing the in-memory merge path** (`merge_databases_inmemory`): D-02 explicitly retains it for small/test merges. Removing it breaks `--merge-mode memory` callers for no milestone benefit.
- **Relying on `Drop` for cleanup under `panic="abort"`:** does not run. The startup sweep is the real defense (D-06).
- **`/proc`-based orphan detection on macOS:** `/proc` is Linux-only. Age-based TTL is portable.
- **Promoting `tempfile` to `[dependencies]` without keeping it in `[dev-dependencies]`:** Cargo permits a crate in both sections; tests already use it. Cleanest is move to `[dependencies]` (tests inherit).
- **Hand-rolling a process-unique temp dir** when `tempfile::Builder::new().prefix(..).rand_bytes(N).tempdir_in(..)` already does it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Process-unique temp subdir | `format!("rustkmer-merge-{}-{}", std::process::id(), random_u64())` + `fs::create_dir_all` | `tempfile::Builder::new().prefix("rustkmer-merge-").rand_bytes(8).tempdir_in(parent)` | `tempfile` handles PID+random naming, RAII `Drop` (recursive `remove_dir_all`), and collision retry. Already a dep. Hand-rolled version omits collision handling and needs a manual `Drop` impl. |
| K-mer encoding/canonicalization | Re-derive u64 encode/decode/reverse_complement | `encode_kmer_bytes`, `decode_kmer`, `reverse_complement`, `encode_kmer_bytes_u128`, `decode_kmer_u128`, `reverse_complement_u128` (`src/kmer/encoding.rs`) | All primitives already exist and are tested. Phase 3 wires them into the counter; no new encoding code. |
| Streaming external merge | New external-sort impl | `ExternalMerger` / `StreamingMergeIterator` (`streaming_merge.rs`), `ExternalSortMerger` (`prefix_cache_merge.rs`) | Already implemented and tested on the streaming path. D-01 just routes to it. |
| RAII temp-file guard | New `Drop` impl on the prefix-cache path | Mirror `TempFileManager` (`streaming_merge.rs:113-176`) — same `files: Vec<PathBuf>` + `Drop` that `remove_file`s each | The pattern is proven on the streaming path. Copy it. |
| Header deserialization | Re-implement the 42-byte read | `DatabaseHeader::read_from` (`format.rs:112-165`) | Already validates magic + version + reads `total_kmers`. Re-using avoids the "header reconciliation in every reader" anti-pattern (CONCERNS). |

**Key insight:** Phase 3 is unusually well-served by existing assets. The merge machinery, encoding primitives, RAII pattern (to mirror), and golden baselines all exist. The net-new code is: (a) ~30 LOC estimator fix, (b) one RAII struct + sweep fn on the prefix-cache path, (c) the `KmerKey` enum + counter swap, (d) `PyDatabase.merge` kwargs, (e) the decoded-level differential test. Everything else is wiring.

## Runtime State Inventory

> Phase 3 modifies runtime behavior (merge defaults, counter width) but is NOT a rename/refactor/migration phase. The inventory is included for completeness per the protocol; the categories most at risk are OS-registered state (temp files) and build artifacts.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None. The `.rkdb` v2 on-disk format is unchanged (D-03). No key/collection/ID renames. | None |
| Live service config | None. rustkmer has no daemon/server (ARCHITECTURE). Merge config is per-invocation. | None |
| OS-registered state | **Temp shard files** under `std::env::temp_dir()` (loose today; will move under `rustkmer-merge-<pid>-<rand>/` per D-06). On macOS+Linux these are plain files, not Task Scheduler/launchd entries. Existing orphaned shards from prior runs (if any) will be swept by the new startup sweep. | Code edit: write shards under process-unique subdir. Data migration: startup sweep removes pre-existing orphans on first run. |
| Secrets/env vars | None. `--max-memory`/`--merge-mode` are CLI flags, not secrets. `RUSTKMER_*` env vars unchanged. | None |
| Build artifacts | **`target/` release binary** recompiled with `panic="abort"` (unchanged). **`pyrustkmer` wheel** rebuilt via `maturin develop`. No `egg-info` equivalent. The `.coverage` files in `pyo3/` (CONCERNS tech-debt) are unaffected. | Rebuild: `cargo build --release` + `maturin develop --release` after the swap. |

**Nothing found in categories:** Stored data (verified: D-03 locks on-disk format), Live service config (verified: ARCHITECTURE — "no daemon, no server, no IPC"), Secrets (verified: `.planning/codebase/STACK.md` — "no `.env` files present").

## Common Pitfalls

### Pitfall 1: Estimator OOM-on-Estimate (the MERGE-01 blocker)
**What goes wrong:** `should_use_streaming` (`format.rs:692-708`) and `merge_databases` (`format.rs:644-652`) call `RKDatabase::from_file_path(path)?` per input to read `total_kmers`. `from_file_path` (`format.rs:287-342`) allocates `Vec::with_capacity(header.total_kmers)` and reads every `KmerEntry` into RAM. On a human-scale merge (~3B entries across inputs), this OOMs the process *during the estimate*, before the merge strategy is even chosen — defeating the entire purpose of the estimator.
**Why it happens:** The estimator was written assuming `from_file_path` was cheap. It is not.
**How to avoid:** Read the 42-byte header only (`DatabaseHeader::read_from`), or fall back to `file_size / 20`. Never call `from_file_path` in the estimator. (D-01.)
**Warning signs:** Merge command dies with OOM before printing "Using streaming merge". CI merge tests pass on small inputs but production OOMs.

### Pitfall 2: `panic="abort"` Skips RAII `Drop`
**What goes wrong:** Developer adds an RAII `Drop` guard on the prefix-cache path, assumes it cleans up on panic, ships. A user runs `rustkmer merge ...` on a huge dataset, hits a panic (or `kill -9`, or power loss), and the temp shards leak — disk fills over multiple failed runs.
**Why it happens:** The release profile sets `panic = "abort"` (`Cargo.toml:112`). Under abort, `Drop` does not run. Tests (which build with `panic=unwind` by default) pass cleanup assertions, masking the bug.
**How to avoid:** D-06: pair RAII with a process-unique subdir + startup stale-shard sweep. The sweep is the real defense against abort/SIGKILL. Test the abort case explicitly (inject a panic, verify the next run's sweep cleans up — see §Validation Architecture MERGE-03).
**Warning signs:** Temp dir grows over time across failed merges; `/tmp/rustkmer-*` accumulates. `[CITED: docs.rs/tempfile — Resource Leaking]`

### Pitfall 3: macOS Has No `/proc` — Budget Detection Diverges
**What goes wrong:** `get_default_memory_limit` (`merge_config.rs:142-163`) reads `/proc/meminfo` (Linux-only); on macOS the read fails silently and the fn returns the hardcoded 32 GB fallback. A macOS user with 16 GB RAM gets a 32 GB budget → in-memory path is always selected → OOM.
**Why it happens:** Original code assumed Linux. macOS has no `/proc`.
**How to avoid:** Either (a) accept the 32 GB fallback as conservative-enough (it's a *ceiling* — if estimate > 32 GB, route to streaming, which is safe even on a 16 GB machine), or (b) wire `sys_info::mem_info()` (already a dep, `Cargo.toml:89`) for cross-platform accuracy. Option (a) is the default — D-01 doesn't require changing the budget source. The 32 GB fallback is actually defensible: any merge whose estimate exceeds 32 GB goes to streaming regardless of actual RAM.
**Warning signs:** Tests pass on Linux CI but macOS users report OOM on medium merges. (CI uses `ubuntu-latest` per STACK.md — macOS path is untested in CI.)

### Pitfall 4: u64/u128 Bit-Alignment Difference Breaks Naive Equality
**What goes wrong:** Developer writes `assert_eq!(u64_counter_map, u128_counter_map)` thinking the same input produces the same integer keys. It does not — u64 aligns to bit 64, u128 to bit 128. Test fails with a confusing diff, or worse, a "correctness" check passes by accident because both sides happen to use the same width.
**Why it happens:** `encode_kmer_bytes` (`encoding.rs:78`) does `encoded <<= pos * 2` (align to 64); `encode_kmer_bytes_u128` (`encoding.rs:230`) does `bits_to_shift = (128 - length*2)` (align to 128).
**How to avoid:** D-04: always decode both sides to k-mer strings before comparing. Never compare raw integers across widths.
**Warning signs:** Differential test fails on the integer comparison but the decoded output is identical.

### Pitfall 5: Hand-merged u64+u128 Databases (Non-Issue, Verified)
**What goes wrong (hypothetically):** A u64-path database (k=21) and a u128-path database (k=21) are merged. Do their (different) integer keys collide or desync?
**Why it's a non-issue:** D-03 locks the on-disk format to `.rkdb` v2 (u128 + u32). The u64 path widens to u128 (zero-extension) when serializing. So on disk, both paths produce identical v2 bytes — the merge reads v2 bytes back into `u128` and merges identically. The "mixed-k merge rejected" carry-forward (`KmerCounter::merge` returns `Err` on differing `kmer_length`) is unaffected. Mixing different `k` remains an error; mixing same-`k` different-width-RAM-path is impossible on disk (both are v2 u128).
**How to avoid:** N/A — verified non-issue. Documented here so downstream planners don't over-engineer a mixed-width-DB guard.

### Pitfall 6: `tempfile` in `[dev-dependencies]` — Won't Compile in Production
**What goes wrong:** Developer adds `use tempfile::TempDir;` to `src/database/prefix_cache_merge.rs` without moving `tempfile` to `[dependencies]`. `cargo build --release` fails: "unresolved import `tempfile`". (Tests pass because `[dev-dependencies]` are available to tests, but `src/` is not a test.)
**Why it happens:** `tempfile` is at `Cargo.toml:96` under `[dev-dependencies]` (it was added for test fixtures in earlier phases).
**How to avoid:** Move `tempfile = "3.12"` from `[dev-dependencies]` to `[dependencies]` (or duplicate in both — Cargo permits). One-line Cargo.toml edit.
**Warning signs:** `cargo build` fails with unresolved import; `cargo test` passes.

## Code Examples

### Header-Only `total_kmers` Read (D-01)
```rust
// Source: src/database/format.rs (DatabaseHeader::read_from, lines 112-165) — adapted for estimator use
use std::fs::File;
use std::io::BufReader;
use crate::database::format::DatabaseHeader;

/// Read just the persisted total_kmers from a .rkdb header WITHOUT materializing entries.
/// This is the D-01 fix for the OOM-on-estimate bug in should_use_streaming.
fn read_total_kmers_from_header(path: &std::path::Path) -> crate::error::ProcessingResult<u64> {
    let file = File::open(path)
        .map_err(|e| crate::error::ProcessingError::io_error(e.to_string()))?;
    let mut reader = BufReader::new(file);
    // Reads exactly 42 bytes: magic(4) + version(2) + kmer_size(1) + padding(3)
    //                       + total_kmers(8) + flags(1) + padding(7) + data_offset(8) + index_offset(8)
    let header = DatabaseHeader::read_from(&mut reader)?;
    Ok(header.total_kmers)
}
```

### RAII TempFileManager (Pattern to Mirror — Existing)
```rust
// Source: src/database/streaming_merge.rs:113-176 (verbatim — the pattern D-06 says to mirror)
pub struct TempFileManager {
    temp_dir: PathBuf,
    files: Vec<PathBuf>,
    prefix: String,
    auto_cleanup: bool,
}

impl Drop for TempFileManager {
    fn drop(&mut self) {
        if self.auto_cleanup {
            self.cleanup();  // remove_file each tracked path
        }
    }
}
```

### Process-Unique Subdir via `tempfile::TempDir` (D-06)
```rust
// Source: tempfile crate docs (https://docs.rs/tempfile/) — adapted for rustkmer-merge
use tempfile::TempDir;

let merge_subdir: TempDir = tempfile::Builder::new()
    .prefix("rustkmer-merge-")
    .rand_bytes(8)
    .tempdir_in(&config.temp_dir)?;

// Shards go under merge_subdir.path() — TempDir::drop removes the whole tree on scope exit.
// Under panic=abort / SIGKILL, the startup sweep (next merge run) removes it by mtime TTL.
```

### PyDatabase.merge with kwargs (MERGE-04)
```rust
// Source: pyo3/src/database.rs:1346-1392 (current) — sketch of the MERGE-04 change
#[staticmethod]
#[pyo3(signature = (databases, output, *, max_memory=None, merge_mode="auto".to_string()))]
fn merge(
    databases: Vec<String>,
    output: String,
    max_memory: Option<String>,   // mirrors CLI --max-memory (e.g. "32GB")
    merge_mode: String,           // mirrors CLI --merge-mode (auto|memory|streaming)
) -> PyResult<()> {
    // ... input validation (unchanged) ...
    let input_paths: Vec<PathBuf> = databases.into_iter().map(PathBuf::from).collect();

    let mut config = MergeConfig::default();
    config.merge_mode = merge_mode.clone();
    if let Some(mem_str) = &max_memory {
        config.max_memory_usage = parse_memory_size_py(mem_str)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e))?;
    }

    let merged_db = RKDatabase::merge_databases(&input_paths, &config)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Merge failed: {}", e)))?;
    merged_db.write_to_file(Path::new(&output))
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Save failed: {}", e)))?;
    Ok(())
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `should_use_streaming` calls `RKDatabase::from_file_path` (loads all entries) | Header-only `total_kmers` read | Phase 3 (D-01) | Estimator no longer OOMs on human-scale inputs |
| Prefix-cache path: manual `remove_file` on success branch only | RAII guard + process-unique subdir + startup sweep | Phase 3 (D-06) | Failed/interrupted merges no longer leak shards |
| `DashMap<u128, u32>` for all k | `DashMap<KmerKey, u32>` (width-selected) | Phase 3 (D-03) | ~50% counting memory reduction for k ≤ 32 |
| `PyDatabase.merge(databases, output)` — no params | `PyDatabase.merge(databases, output, *, max_memory=None, merge_mode="auto")` | Phase 3 (MERGE-04) | Python users get the same budget control as CLI |
| External tools: KMC bins + Jellyfish `.jf` spill files | Same conceptual pattern (disk-spill + external merge), rustkmer's `ExternalMerger`/`ExternalSortMerger` | Industry-standard since KMC1 (2013) / Jellyfish (2011) | rustkmer's approach is conventional; the gap was the estimator + cleanup, not the algorithm |

**Deprecated/outdated:**
- The estimator's `from_file_path` call (`format.rs:700-703`) — the OOM-on-estimate bug. Replaced by header-only read.
- The prefix-cache success-only cleanup (`prefix_cache_merge.rs:322-326`) — replaced by RAII + sweep.
- The `encode_kmer_auto` fn (`encoding.rs:299`) — exists but unused in production; the dense counter swap makes it relevant (or it stays unused if the counter does width-selection internally).

## Assumptions Log

> List of claims tagged `[ASSUMED]` in this research. Most claims are verified against source this session; the few `[ASSUMED]` items are minor and non-blocking.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `DashMap<K, V>` works with a derived-`Hash+Eq` enum key (`KmerKey::U64`/`U128`) | Architecture Patterns / Pattern 1 | LOW — derive behavior is standard Rust; if dashmap has an undocumented enum-key quirk, fall back to a newtype wrapper. |
| A2 | `tempfile::TempDir::drop` removes the directory tree recursively (not just the dir node) | Architecture Patterns / Pattern 3 | LOW — `tempfile` docs confirm recursive removal; if not, individual `remove_file` calls still work. |
| A3 | The parallel_count_baseline JSON keys are raw u128 integers (verified by inspection: `head -c 400`) | Architecture Patterns / Pattern 4 | LOW — verified this session; if they were strings, the differential would still work (just skip the decode on the u128 baseline side). |
| A4 | KMC/Jellyfish use disk-spill + cleanup-after-processing (informative only — not binding) | State of the Art | NONE — v1 comparator is Jellyfish2; the pattern is industry-standard regardless. |

**Note on confidence:** All load-bearing technical claims (header layout, `panic=abort` skipping `Drop`, encode/decode bit-alignment, the cleanup gap site, the estimator bug, the existing RAII pattern, golden baseline presence, Cargo.toml dep placement) were **verified against source code or authoritative docs this session** — not assumed.

## Open Questions

1. **Should `sys_info::mem_info()` replace `/proc/meminfo` for cross-platform budget detection?**
   - What we know: `get_default_memory_limit` (`merge_config.rs:142-163`) reads `/proc/meminfo` (Linux-only) and falls back to 32 GB. `sys_info` is already a dep (`Cargo.toml:89`) and works on macOS+Linux. CONCERNS lists "`sys_info::mem_info()` failure fallback" as an untested path.
   - What's unclear: whether the 32 GB fallback is "good enough" (it's a ceiling — any merge > 32 GB estimate goes to streaming, which is safe on any machine) or whether macOS users need accurate budget detection.
   - Recommendation: Leave as Claude's discretion. The 32 GB fallback is defensible (D-01 doesn't mandate changing the budget source). If the planner wants cross-platform accuracy, `sys_info::mem_info()` is a 5-line change with no new dep.

2. **Should the u64 counter expose `increment(u64)` as a new public method, or keep `increment(u128)` and narrow internally?**
   - What we know: Phase 2 D-05 mandates public API stability. `increment(u128)` is the existing signature.
   - What's unclear: whether narrowing `u128` → `u64` internally (panicking or erroring if high bits are set for k≤32) is acceptable, or whether a parallel `increment_u64` should be added.
   - Recommendation: Keep `increment(u128)` unchanged; narrow internally with a debug-assert that high bits are zero for k≤32 (zero-cost in release). The count.rs call site (`encode_kmer_bytes_u128` → `increment`) can switch to `encode_kmer_bytes` (u64) → new internal path. Planner's call under Claude's discretion.

3. **TTL for the startup sweep — 24h vs 7 days?**
   - What we know: Age-based TTL is the recommended heuristic (portable, simple). A merge that runs longer than the TTL would have its subdir wrongly swept.
   - Recommendation: 7 days (generous — human-scale merges complete in hours, not days). Optionally touch the subdir mtime periodically during long merges to refresh.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Rust stable toolchain | All Rust code | ✓ | 1.95.0-nightly (local); CI uses `dtolnay/rust-toolchain@stable` | — |
| `cargo` | Build | ✓ | 1.95.0-nightly | — |
| Python 3.11+ | pyrustkmer build/tests | ✓ (multiple `.venv*` dirs present) | 3.11/3.12/3.13 | — |
| `maturin` | pyrustkmer wheel build | ✓ (per `pyo3/build_with_python.sh`) | >=1.0,<2.0 | — |
| `tempfile` crate (production use) | D-06 process-unique subdir | ✓ in `[dev-dependencies]`; **must promote to `[dependencies]`** | 3.24.0 | — |
| `dashmap` crate | D-03 dense counter | ✓ | 6.2.1 | — |
| `sys_info` crate (optional) | Cross-platform budget | ✓ (unused by `get_default_memory_limit` today) | 0.9 | `/proc/meminfo` + 32 GB fallback (existing) |
| CRR1936095 human-scale dataset | Full benchmark | LOCAL (per PROJECT.md) | — | **Phase 3 does NOT need the full dataset** — correctness is proven on synthetic + the D-13 matrix fixtures; Phase 4 owns the full benchmark |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none — all required crates are already in the graph; `tempfile` requires a one-line section move.

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json`. This section is the planner's source for Dimension 8 (validation requirements). Nyquist sampling: per-task commit = quick test, per-wave merge = full suite, phase gate = full suite green before `/gsd-verify-work`.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `cargo test` (built-in) + `proptest 1.5` (Rust property tests); `pytest >=7.0` (Python contract tests for pyrustkmer) |
| Config file | Root: none (cargo defaults). pyo3: `pyo3/pyproject.toml` `[tool.pytest.ini_options]` (coverage gate `--cov-fail-under=80`) |
| Quick run command | `cargo test --lib` (unit tests in `src/`) |
| Full suite command | `cargo test --all && cargo test --test parallel_count_tests && (cd pyo3 && maturin develop --release && pytest)` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MERGE-01 | Merge defaults to streaming; oversized estimate routes to streaming not in-memory | unit + integration | `cargo test --lib merge_default_streaming -- --exact` and `cargo test --test merge_routing_tests` | ❌ Wave 0 (new: `tests/merge_routing_tests.rs`) |
| MERGE-02 | Admission control: estimate > budget hard-routes to streaming; header-only read (no entry materialization) | unit | `cargo test --lib should_use_streaming_header_only -- --exact` and `cargo test --lib estimator_does_not_materialize_entries` | ❌ Wave 0 (inline in `src/database/format.rs` `#[cfg(test)]`) |
| MERGE-03 | Failed/interrupted streaming merge cleans up temp shards (RAII + sweep) | integration | `cargo test --test merge_cleanup_tests -- --exact` covering: (a) panic-injection leaves no shards, (b) orphan subdir swept on next start, (c) process-unique subdir isolates concurrent merges | ❌ Wave 0 (new: `tests/merge_cleanup_tests.rs`) |
| MERGE-04 | `PyDatabase.merge` threads `max_memory`/`merge_mode` kwargs through to the bounded core | Python contract | `(cd pyo3 && maturin develop --release && pytest tests/test_database_merge.py -k bounded_merge)` | ❌ Wave 0 (new: `pyo3/tests/test_database_merge.py`) |
| DENSE-01 | k ≤ 32 counter uses u64 internally; `memory_usage()` reflects ~50% reduction | unit + benchmark | `cargo test --lib dense_counter_memory -- --exact` asserting `counter.memory_usage()` for k=21 is roughly half of an equivalent u128 counter (within hash overhead tolerance) | ❌ Wave 0 (inline in `src/hash/table.rs` `#[cfg(test)]`) |
| DENSE-02 | `.rkdb` v2 byte-identity preserved post-dense; golden sha256 baselines unchanged | integration (golden re-verification) | `cargo test --test golden_sha256_tests` re-hashes the 12 `tests/fixtures/golden_k*.rkdb` and compares to `golden_manifest.sha256` | ❌ Wave 0 (new: `tests/golden_sha256_tests.rs`) — reuses existing fixtures, no new baseline capture |
| DENSE-03 | u64 path canonicalization + counts == u128 path (decoded-level differential, D-04/D-05) | integration + property | `cargo test --test dense_differential_tests` (D-13 matrix: k ∈ {21,32,64} × canon × sorted, u64-vs-u128 decoded-map equality) + `cargo test --test dense_proptest` (random small inputs, proptest) | ❌ Wave 0 (new: `tests/dense_differential_tests.rs`, `tests/dense_proptest.rs`) |

### How to PROVE MERGE-01 (no-OOM) and DENSE-03 (canonicalization correctness) without a human-scale dataset in CI

**MERGE-01 (no-OOM) — synthetic bounding proof:** The CI does not have CRR1936095. The proof strategy is **bounding, not scale**: construct a synthetic `.rkdb` pair whose summed `total_kmers × 24 B` estimate exceeds a tiny test budget (e.g. set `max_memory_usage = 1024` bytes and use databases with a few hundred entries). Assert: (a) the estimator reads the header only (no `from_file_path` call — verify by mocking or by asserting the read count), (b) `merge_databases` selects the streaming path, (c) the merge completes without allocating an unbounded hashmap. The *logic* that prevents OOM at human scale is the same logic tested at toy scale — the estimator is `total_kmers × 24 > budget`, independent of absolute size. Phase 4's benchmark validates the actual human-scale behavior; Phase 3 validates the routing logic.

**DENSE-03 (canonicalization correctness) — decoded differential against golden baselines:** Reuse the Phase 1/2 golden `.rkdb` files (k=21, k=32 → exercise u64; k=64 → exercise u128). For each (k, canonical, sorted) combo: (a) load the golden `.rkdb`, decode every entry to `(String, u32)` via `decode_kmer_u128`; (b) re-count the same source FASTA through a u64-path counter (k≤32), decode via `decode_kmer`; (c) assert the two decoded maps are equal. This proves the u64 path produces the same (kmer-string, count) pairs as the u128 path on identical input. Add a proptest that generates random short DNA sequences, counts through both paths, and asserts decoded-map equality — catches any random-input packing/canonicalization bug the fixed golden fixtures miss.

### Sampling Rate
- **Per task commit:** `cargo test --lib` (fast unit tests in `src/`)
- **Per wave merge:** `cargo test --all && cargo test --test parallel_count_tests && cargo test --test dense_differential_tests && cargo test --test merge_cleanup_tests`
- **Phase gate:** Full Rust suite + `pyo3` Python suite green before `/gsd-verify-work`. Clippy gate: `cargo clippy --all-targets -- -D warnings` on BOTH the root crate and `pyo3/` (Phase 1 FOUND-01).

### Wave 0 Gaps
- [ ] `tests/merge_routing_tests.rs` — covers MERGE-01, MERGE-02 (estimator fix + hard-route)
- [ ] `tests/merge_cleanup_tests.rs` — covers MERGE-03 (RAII + process-unique subdir + startup sweep; panic-injection)
- [ ] `tests/dense_differential_tests.rs` — covers DENSE-03 (u64-vs-u128 decoded differential, D-13 matrix)
- [ ] `tests/dense_proptest.rs` — covers DENSE-03 (proptest on random small inputs)
- [ ] `tests/golden_sha256_tests.rs` — covers DENSE-02 (re-verify 12 golden `.rkdb` sha256 unchanged post-dense)
- [ ] `pyo3/tests/test_database_merge.py` — covers MERGE-04 (PyDatabase.merge kwargs contract)
- [ ] Inline `#[cfg(test)]` in `src/hash/table.rs` — covers DENSE-01 (`memory_usage()` ~50% reduction assertion)
- [ ] Framework check: `cargo test` already configured; `proptest 1.5` already a dev-dep; `pytest` configured in `pyo3/pyproject.toml`. No new framework install needed.

*(Existing infrastructure covers the carry-forward Phase 1/2 tests — `tests/parallel_count_tests.rs` stays green; the dense swap must not regress PCOUNT-04.)*

## Security Domain

> `security_enforcement: true` in `.planning/config.json`; ASVS level 1. Phase 3 touches temp-file lifecycle and merge routing — the relevant categories are below. rustkmer is a local CLI/library with no networked auth, so V2/V3 are largely N/A.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — local CLI/library, no auth (ARCHITECTURE) |
| V3 Session Management | no | N/A — no sessions, per-invocation state only |
| V4 Access Control | no | N/A — local file access governed by OS user permissions |
| V5 Input Validation | yes | `DatabaseHeader::read_from` validates magic + version + (post-Phase-1) `data_offset == 42` before any read. The D-01 estimator reuses this — corrupt/tampered `.rkdb` files surface as `Err`, not silent garbage. `parse_memory_size` (`merge.rs:475`) validates `--max-memory` strings. |
| V6 Cryptography | no | N/A — no crypto operations in Phase 3 (sha256 is for golden-fixture verification, not security) |
| V7 Error Handling & Logging | yes | `log::` facade (Phase 1 FOUND-02); merge diagnostics via `log::info!`/`warn!` not `println!`. Errors via `ProcessingResult`/`PyResult`. |
| V12 Files & Resources | yes | Temp-file lifecycle (D-06): process-unique subdir prevents cross-user/cross-process collision; startup sweep prevents disk exhaustion (DoS mitigation). `tempfile::TempDir` uses `0600` perms on temp files by default (creator-only). |

### Known Threat Patterns for the merge/temp-file stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Temp-file symlink attack (TOCTOU: attacker swaps a temp file between create and read) | Tampering | `tempfile` uses `O_CREAT|O_EXCL` (or `O_TMPFILE` on Linux) — file is created with exclusive flag, cannot be pre-existing. `tempfile::TempDir`/`NamedTempFile` are the standard mitigation. `[CITED: docs.rs/tempfile]` |
| Disk exhaustion (attacker or accident fills `/tmp` with orphaned shards) | Denial of Service | D-06 startup sweep + process-unique subdir (bounded growth). The `rustkmer-merge-*` prefix enables unambiguous identification of rustkmer-owned temp dirs. |
| Path traversal via crafted `.rkdb` path | Tampering | `DatabaseHeader::read_from` validates magic/version; `data_offset == 42` validation (Phase 1) prevents reading arbitrary offsets. Paths come from user CLI args (trusted input for a local tool). |
| Cross-process merge collision (two merges write the same temp file) | Tampering | D-06 process-unique subdir (`rustkmer-merge-<pid>-<rand>/`) — no collision possible. |

## Sources

### Primary (HIGH confidence — verified against source code this session)
- `src/database/format.rs` — `DatabaseHeader` (42-byte layout, `total_kmers` field at fixed offset), `read_from`/`write_to`, `merge_databases` dispatch, `should_use_streaming` (OOM-on-estimate bug), `merge_databases_inmemory`, `KmerEntry` (20-byte: 16 u128 + 4 u32)
- `src/database/streaming_merge.rs` — `TempFileManager` (RAII `Drop` pattern, lines 113-176), `StreamingMergeIterator::Drop` (lines 398-414), `ExternalMerger`, `DatabaseStreamIterator`
- `src/database/prefix_cache_merge.rs` — `ExternalSortMerger`, manual success-only cleanup (lines 322-326), the 8 `try_into().unwrap()` 20-byte conversion sites (lines 475/477, 664/665, 698/699, 940/941)
- `src/database/merge_config.rs` — `MergeConfig`, `get_default_memory_limit` (`/proc/meminfo` + 32 GB fallback, no `sys_info`)
- `src/hash/table.rs` — `KmerCounter` (`DashMap<u128, u32>` swap site at line 22, `increment` atomicity, `memory_usage()` at line 283)
- `src/kmer/encoding.rs` — `encode_kmer_bytes` (u64, bit-64 alignment, line 78), `encode_kmer_bytes_u128` (u128, bit-128 alignment, line 230), `decode_kmer`/`decode_kmer_u128`, `reverse_complement`/`reverse_complement_u128`, `MAX_KMER_SIZE_IN_U64=32`, `encode_kmer_auto` (unused in production)
- `src/cli/commands/merge.rs` — `MergeArgs` (`--max-memory`, `--merge-mode`, `--use-prefix-cache`), `parse_memory_size`, `MergeConfig` assembly (lines 302-338)
- `pyo3/src/database.rs` — `PyDatabase::merge` (lines 1346-1392, current `MergeConfig::default()` with no params)
- `Cargo.toml` / `Cargo.lock` — release profile `panic="abort"` (line 112), `tempfile` in `[dev-dependencies]` (line 96), `dashmap 6.2.1`, `rayon 1.8`, `sys-info 0.9`, `proptest 1.5`
- `tests/fixtures/golden_manifest.sha256` — 12 golden `.rkdb` sha256 baselines (D-13 matrix)
- `tests/fixtures/parallel_count_baseline/k21_canon.json` — baseline format inspection (raw u128 integer keys)
- `.planning/phases/03-memory-safety/03-CONTEXT.md` — locked decisions D-01..D-06 + carry-forward
- `.planning/codebase/{ARCHITECTURE,CONCERNS,STACK}.md` — merge bottlenecks, fragile areas, test-coverage gaps

### Secondary (MEDIUM confidence — authoritative docs / verified external)
- [docs.rs/tempfile](https://docs.rs/tempfile/) — `TempDir`/`NamedTempFile` rely on `Drop` for cleanup; `Drop` skipped on abort/SIGKILL/`process::exit` (Resource Leaking section). `[CITED]`
- [Ferrous Systems — Drop, Panic and Abort](https://rust-training.ferrous-systems.com/latest/book/drop-panic-abort) — training material confirming `Drop` does not run under `panic="abort"`. `[CITED]`
- [Rust Users Forum — Temporary directory but not deleted on panic?](https://users.rust-lang.org/t/temporary-directory-but-not-deleted-on-panic/96704) — community confirmation of the abort-skip-Drop behavior. `[CITED]`
- Package legitimacy gate (`gsd-tools query package-legitimacy check`): `tempfile` OK (since 2015, 11.3M/wk, Stebalien/tempfile), `dashmap` OK (since 2019, 5.1M/wk, xacrimon/dashmap)

### Tertiary (LOW confidence — informative, not binding)
- [KMC GitHub / KMC 2 paper (Oxford Academic)](https://academic.oup.com/bioinformatics/article/31/10/1569/177467) — disk-based k-mer counting with bin-then-sort; industry-standard pattern. `[ASSUMED — informative only]`
- [Jellyfish GitHub / manual v2.3.0](https://github.com/gmarcais/Jellyfish) — hash-table spill + `.jf` merge; v1 comparator approach. `[ASSUMED — informative only]`
- [Benchmark study of k-mer counting methods (PMC6280066)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6280066/) — comparative assessment of Jellyfish/KMC/DSK/Khmer. `[ASSUMED — informative only]`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all crates verified in `Cargo.toml`/`Cargo.lock`; `tempfile`/`dashmap` pass legitimacy gate
- Architecture: HIGH — all integration points verified against source code line-by-line this session
- Pitfalls: HIGH — `panic="abort"` behavior confirmed via docs.rs/tempfile + Ferrous Systems training; estimator bug confirmed in source; u64/u128 bit-alignment confirmed in encoding.rs
- Dense correctness approach: HIGH — D-04/D-05 design validated against the actual baseline format (raw integer keys → must decode before cross-width comparison)

**Research date:** 2026-07-02
**Valid until:** 2026-08-01 (30 days — stable; no fast-moving deps introduced. The only external risk is a `tempfile` major bump, but the API used — `Builder::new().prefix().rand_bytes().tempdir_in()` — has been stable since tempfile 3.0.)
