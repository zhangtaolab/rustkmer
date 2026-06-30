# Architecture Patterns

**Domain:** k-mer counting toolkit at human-genome scale
**Researched:** 2025-06-30
**Overall confidence:** MEDIUM

## Executive Summary

Research on human-genome-scale k-mer counting architectures reveals three dominant patterns: (1) **minimizer-based partitioning with external sort** (KMC family), (2) **lock-free hash tables** (Jellyfish family), and (3) **compact filter structures** (Counting Quotient Filters, Bloom filters). rustkmer's current architecture uses a single-threaded HashMap<u128, u32> behind a RwLock, which maps most closely to the Jellyfish approach but without the lock-free optimization.

The migration path to human-scale performance involves: (a) introducing **partitioned counting** to enable true parallelism without lock contention, (b) adopting **dense storage** (u64 packing or CQF) to reduce memory pressure, and (c) making the **streaming merge** the default path with proper memory-budget admission control. These changes map cleanly onto rustkmer's existing layered structure without requiring breaking changes to the .rkdb format or public APIs.

## Recommended Architecture

### High-Level Structure

```text
┌────────────────────────────────────────────────────────────────────────────┐
│                              Entry Surfaces                                 │
├──────────────────────────────────┬─────────────────────────────────────────┤
│   CLI binary                     │   Python binding (pyrustkmer)           │
│   src/main.rs + src/cli/         │   pyo3/src/*.rs                         │
└──────────────┬───────────────────┴──────────────────┬──────────────────────┘
               │                                      │
               ▼                                      ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                    Core library crate `rustkmer`                            │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┬─────────┐  │
│  │   COUNTING   │   STORAGE    │    MERGE     │    QUERY     │  UTILS  │  │
│  │   LAYER      │   LAYER      │   LAYER      │   LAYER      │         │  │
│  └──────────────┴──────────────┴──────────────┴──────────────┴─────────┘  │
│         │              │              │              │                      │
│         ▼              ▼              ▼              ▼                      │
│  ┌───────────┬────────────┬────────────┬────────────┬──────────────┐      │
│  │ Partition │ Dense     │ Streaming  │ Prefix/    │ K-mer       │      │
│  │ Counters  │ Storage    │ Merge      │ Fuzzy      │ Encoding    │      │
│  │ (NEW)     │ (NEW/REF)  │ (EXISTING) │ (EXISTING) │ (EXISTING)  │      │
│  └───────────┴────────────┴────────────┴────────────┴──────────────┘      │
└────────────────────────────────────────────────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  RKDB binary format (.rkdb) — v2, 42-byte header + 20-byte entries        │
│  NO BREAKING CHANGE — format stays compatible                               │
└────────────────────────────────────────────────────────────────────────────┘
```

### Component Boundaries

| Component | Responsibility | File Location | Communicates With | New/Existing |
|-----------|----------------|----------------|-------------------|--------------|
| **PartitionedCounter** | Minimizer-based sharded counters for lock-free parallel counting | `src/hash/partitioned.rs` (NEW) | `FastaProcessor`/`FastqProcessor`, `PartitionStorage`, CLI | NEW |
| **DenseKmerStore** | Packed u64/u128 storage (conditional on k-mer size) to reduce memory | `src/hash/dense.rs` (NEW) | `PartitionedCounter`, `KmerCounter` | NEW |
| **KmerCounter** | Current HashMap<u128, u32> (retained for small k/compatibility) | `src/hash/table.rs` | CLI, PyO3 | EXISTING (refactor) |
| **StreamingMergeOrchestrator** | Admission-controlled merge that routes to streaming vs in-memory | `src/database/merge_orchestrator.rs` (NEW) | `ExternalMerger`, `merge_databases_inmemory`, CLI | NEW |
| **ExternalMerger** | Existing streaming merge (k-way external sort) | `src/database/streaming_merge.rs` | `StreamingMergeIterator`, `DatabaseQuery` | EXISTING (enhance) |
| **PrefixCacheMerger** | Existing prefix-based external sort | `src/database/prefix_cache_merge.rs` | CLI | EXISTING (keep) |
| **MemoryBudgetController** | Memory-aware routing for both counting and merging | `src/memory/budget.rs` (NEW/REF) | `PartitionedCounter`, `StreamingMergeOrchestrator` | NEW |
| **MinimizerPartitioner** | Computes minimizers for sharding | `src/kmer/minimizer.rs` (NEW) | `PartitionedCounter` | NEW |
| **DatabaseQuery** | Query engine (binary search, streaming) | `src/database/query.rs` | CLI, PyO3 | EXISTING |
| **RKDatabase** | In-memory database representation | `src/database/format.rs` | CLI, PyO3 | EXISTING (refactor god module) |

### Data Flow

#### Current Counting Flow (Single-threaded, RwLock-protected)

```
FASTA/FASTQ files → FastaProcessor/FastqProcessor
                  → encode_kmer_bytes_u128 (kmer/encoding.rs)
                  → optional canonicalization
                  → KmerCounter.increment(u128) [parking_lot::RwLock<HashMap<u128,u32>>]
                  → (all files processed sequentially)
                  → sort entries
                  → output_binary_format writes .rkdb
```

**Bottlenecks:**
- Sequential file processing (num_threads = 1 hardcoded)
- RwLock contention if parallelized
- u128 encoding for all k (even k ≤ 32 where u64 suffices)
- No partitioning — single hashmap stores entire distinct k-mer set

#### Proposed Partitioned Counting Flow (Lock-free, Parallel)

```
FASTA/FASTQ files → Rayon-par-process each file independently
                  → encode + canonicalize per-file
                  → compute minimizer (src/kmer/minimizer.rs)
                  → route to PartitionedCounter shard [HashMap<u64,u32> or dense store]
                     (shard count = 2^m where m = minimizer length, e.g., 8–12)
                  → each shard processes independently (no locks)
                  → periodic spill-to-disk per shard if memory budget exceeded
                  → final merge of shards → output_binary_format writes .rkdb
```

**Why this works:**
- **Minimizer guarantees each k-mer maps to exactly one shard** (deterministic partitioning)
- Shards never conflict — true lock-free parallelism
- Spill-to-disk per shard bounds memory
- Final merge is external-sort (already implemented in `streaming_merge.rs`)

#### Current Merge Flow (Two Paths)

```
merge_databases_inmemory:
  For each .rkdb → db.all_kmers() loads ALL entries
  → accumulate into single HashMapBrown<u128,u32>
  → write merged .rkdb
  (OOMs at scale)

streaming_merge.rs / prefix_cache_merge.rs:
  External k-way merge with memory-bounded buffering
  → reads inputs via DatabaseStreamIterator
  → k-way merge, sums duplicates
  → writes merged .rkdb
  (NOT the default)
```

**Problem:** In-memory path is the current default (or at least prominently surfaced), streaming path exists but is opt-in.

#### Proposed Merge Flow (Admission-Controlled)

```
User invokes merge:
  → MemoryBudgetController.estimate_merge_memory(input_databases)
  → if estimate < budget && input_count small:
       → route to merge_databases_inmemory (fast path)
  → else:
       → route to StreamingMergeOrchestrator
       → k-way external merge via streaming_merge.rs
       → prefix-bucketing if input count high (prefix_cache_merge.rs)
```

**Benefits:**
- OOM prevention via upfront estimation
- Streaming path becomes the safe default
- Existing streaming machinery is leveraged

## Patterns to Follow

### Pattern 1: Minimizer-Based Partitioned Counting

**What:** Assign each k-mer to a shard based on its minimizer (the smallest m-mer within the k-mer). Each shard is an independent counter that can be updated without locks.

**When:** Human-genome-scale counting (billions of distinct k-mers) where a single hashmap would exceed memory or cause lock contention.

**Rationale:**
- **Deterministic partitioning** — same k-mer always routes to same shard
- **Lock-free** — threads write to different shards
- **Memory-bounded** — each shard can spill independently
- **Proven** — KMC uses this architecture for human-scale data

**Mapping to rustkmer:**

New module: `src/kmer/minimizer.rs`

```rust
pub fn compute_minimizer(kmer: u128, k: usize, m: usize) -> u64 {
    // Extract the smallest m-mer within the k-mer
    // For k ≤ 64, work with u64; for larger k, use u128
}

pub fn shard_index(kmer: u128, minimizer: u64, num_shards: usize) -> usize {
    // Hash minimizer to shard index
    // Ensures same k-mer always routes to same shard
}
```

New module: `src/hash/partitioned.rs`

```rust
pub struct PartitionedCounter {
    shards: Vec<HashMap<u64, u32>>,  // u64 for k ≤ 32, dense packing
    shard_count: usize,
    minimizer_length: usize,
}

impl PartitionedCounter {
    pub fn new(shard_count: usize, minimizer_length: usize) -> Self { ... }

    pub fn increment(&mut self, kmer: u128, k: usize) -> Result<()> {
        let minimizer = compute_minimizer(kmer, k, self.minimizer_length);
        let shard_idx = shard_index(kmer, minimizer, self.shard_count);
        self.shards[shard_idx].insert(kmer as u64, count + 1);  // No lock needed per-shard
        Ok(())
    }

    pub fn into_sorted_entries(self) -> Vec<(u128, u32)> {
        // Merge all shards and sort
        // Can use external sort if total size large
    }
}
```

**Integration in CLI:**

`src/cli/commands/count.rs` gains a `--partitioned` flag (default true for k ≤ 31, optional for larger k):

```rust
let counter = if args.partitioned {
    PartitionedCounter::new(args.shard_count.unwrap_or(256), args.minimizer_length.unwrap_or(8))
} else {
    KmerCounter::new(capacity, args.canonical)  // Existing path for small datasets
};

// Rayon parallel file processing
files.par_iter().for_each(|file| {
    process_file(file, &counter)?;
});
```

### Pattern 2: Dense Storage for Small K

**What:** Use u64 (8 bytes) instead of u128 (16 bytes) for k ≤ 32, packing two k-mers per u128 if needed.

**When:** The common case of k=21 or similar, where u128 doubles memory unnecessarily.

**Rationale:**
- **2× memory reduction** for the most common k sizes
- **No .rkdb format change** — encode on write, decode on read
- **Backward compatible** — old files (u128-based) still readable

**Mapping to rustkmer:**

New enum: `src/kmer/encoding.rs`

```rust
pub enum PackedKmer {
    Small(u64),   // k ≤ 32
    Large(u128),  // 32 < k ≤ 64
}
```

Modified write path: `src/database/format.rs` or `src/cli/commands/count.rs`

```rust
fn write_kmer_entry(kmer: PackedKmer, count: u32, writer: &mut BufferedWriter) -> Result<()> {
    match kmer {
        PackedKmer::Small(k) => {
            writer.write_u64(k)?;
        },
        PackedKmer::Large(k) => {
            writer.write_u128(k)?;
        },
    }
    writer.write_u32(count)?;
}
```

**.rkdb compatibility:**
- On read, detect k-mer size from header (already stored)
- If k ≤ 32, read 8 bytes; otherwise read 16 bytes
- **No format version bump needed** — field is already variable-length

### Pattern 3: Admission-Controlled Merge Routing

**What:** Estimate memory required for a merge before committing to a strategy; route to streaming merge if the estimate exceeds budget.

**When:** Any merge operation, but especially when merging >10 databases or total k-mer count is unknown/large.

**Rationale:**
- **Prevent OOM** — fail fast or route to bounded path
- **Safe default** — streaming merge becomes the standard
- **Leverage existing work** — `streaming_merge.rs` already implements this

**Mapping to rustkmer:**

New module: `src/memory/budget.rs`

```rust
pub fn estimate_merge_memory(input_paths: &[PathBuf]) -> Result<usize> {
    // For each .rkdb, read header to get kmer_count
    // Estimate: kmer_count * 20 bytes (entry size) + overhead
    // Return total bytes
}

pub fn choose_merge_strategy(estimated_memory: usize, budget: usize) -> MergeStrategy {
    if estimated_memory < budget && estimated_memory < 100_000_000 {
        MergeStrategy::InMemory
    } else {
        MergeStrategy::Streaming
    }
}
```

New orchestrator: `src/database/merge_orchestrator.rs`

```rust
pub fn merge_with_admission(inputs: Vec<PathBuf>, output: PathBuf, memory_budget: usize) -> Result<()> {
    let estimated = estimate_merge_memory(&inputs)?;
    let strategy = choose_merge_strategy(estimated, memory_budget);

    match strategy {
        MergeStrategy::InMemory => merge_databases_inmemory(inputs, output),
        MergeStrategy::Streaming => {
            let orchestrator = StreamingMergeOrchestrator::new(memory_budget);
            orchestrator.merge(inputs, output)
        },
    }
}
```

**CLI integration:** `src/cli/commands/merge.rs`

```rust
let memory_budget = args.max_memory.unwrap_or(system_memory() * 0.8);
merge_with_admission(input_databases, output_path, memory_budget)?;
```

### Pattern 4: Streaming Merge as Default

**What:** Use `streaming_merge.rs` or `prefix_cache_merge.rs` by default; in-memory merge only for small/verified cases.

**When:** All merge operations, with an explicit `--merge-strategy in-memory` override.

**Rationale:**
- **Scalable** — handles unlimited inputs with bounded memory
- **Existing implementation** — just needs to be surfaced
- **Safe** — no surprise OOMs

**Mapping to rustkmer:**

No new code — just change the default routing in `src/cli/commands/merge.rs` and `src/database/format.rs`:

```rust
// OLD (default):
merge_databases_inmemory(inputs, output)?;

// NEW (default):
if args.merge_strategy == Some(MergeStrategy::InMemory) {
    merge_databases_inmemory(inputs, output)?;
} else {
    // Default to streaming
    streaming_merge_with_admission(inputs, output, memory_budget)?;
}
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Monolithic format.rs Merges Both In-Memory and Streaming Logic

**What happens:** `src/database/format.rs` (1306 lines) mixes `RKDatabase`, serialization, AND both merge strategies (`merge_databases_inmemory` and `merge_databases_streaming`).

**Why it's bad:** Any merge-related change risks touching serialization logic; the module is already flagged as a god module in CONCERNS.md.

**Instead:** Extract merge orchestration to `src/database/merge_orchestrator.rs`. Keep `format.rs` focused on `DatabaseHeader`, `KmerEntry`, and RKDB I/O.

**Migration path:**
1. Create `merge_orchestrator.rs` with admission-controlled routing
2. Move `merge_databases_inmemory` call into the orchestrator (don't delete yet)
3. Route CLI through orchestrator
4. Test thoroughly, then refactor `format.rs` to remove merge logic

### Anti-Pattern 2: Direct Console I/O in Library Code

**What happens:** `src/database/prefix_cache_merge.rs` and `src/database/format.rs` have `println!`/`eprintln!` progress messages (some in Chinese, as flagged in CONCERNS.md). This violates separation of library and presentation.

**Why it's bad:** PyO3 users get spurious stdout; machine-readable CLI output is polluted; violates the layered architecture.

**Instead:** Use the `log` crate (already a dependency). Replace `println!` with `log::info!` and `eprintln!` with `log::warn!`. The CLI configures the logger; library code emits through the facade.

**Migration path:**
1. Add `use log::{info, debug, warn};` to affected files
2. Replace all `eprintln!` with `warn!` or `debug!`
3. Replace `println!` with `info!`
4. Add `#[cfg(test)]` gates where progress messages are only needed for debugging

### Anti-Pattern 3: Unconditional u128 Storage for Small K

**What happens:** All k-mers are stored as u128 even when k ≤ 32, wasting 8 bytes per entry.

**Why it's bad:** For k=21 (common case), human genome (~3B distinct k-mers) wastes ~24 GB memory vs. u64 storage.

**Instead:** Conditional packing based on `kmer_size` from the database header. Write small k as u64, large k as u128.

**Migration path:**
1. Add `PackedKmer` enum to `src/kmer/encoding.rs`
2. Modify write paths to use `PackedKmer::Small` for k ≤ 32
3. Modify read paths to detect k from header and unpack accordingly
4. Ensure .rkdb v2 readers handle both (they already read variable-length fields)

### Anti-Pattern 4: RwLock Around a Single HashMap for Parallel Counting

**What happens:** If the current `KmerCounter` (RwLock<HashMap<u128,u32>>) is used with parallel file processing, threads contend on the RwLock.

**Why it's bad:** Lock contention defeats parallelism; throughput drops vs. sequential processing.

**Instead:** Use partitioned counters (sharded HashMaps) or replace RwLock with a lock-free concurrent hashmap (e.g., `dashmap` or `chashmap`).

**Migration path:**
1. Implement `PartitionedCounter` (Pattern 1)
2. Benchmark against RwLock approach
3. If partitioning is too complex, consider `dashmap` as a simpler drop-in
4. Deprecate RwLock path after verification

### Anti-Pattern 5: Duplicated .rkdb Write Logic

**What happens:** `output_binary_format` in `src/cli/commands/count.rs` writes the RKDB format inline, duplicating the layout defined in `src/database/format.rs`.

**Why it's bad:** Two implementations of the same binary layout; any format change must be synced.

**Instead:** Build an `RKDatabase` in the command handler, then call `RKDatabase::to_file_path()`.

**Migration path:**
1. Refactor `output_binary_format` to build an `RKDatabase` instead of writing directly
2. Call `RKDatabase::to_file_path` to persist
3. Remove inline `byteorder` writes from `count.rs`

## Scalability Considerations

| Concern | Current (100M k-mers) | Current (10B k-mers, human-scale) | After Partitioning | After Dense Storage |
|---------|----------------------|-----------------------------------|---------------------|---------------------|
| **Counting memory** | ~3-4 GB (HashMap<u128,u32>) | ~300-400 GB (OOM) | ~150-200 GB (partitioned, no locks) | ~75-100 GB (u64 packing) |
| **Counting speed** | Single-threaded, ~50-100M k-mers/min | Same (no parallelism) | ~400-800M k-mers/min (8-way parallel) | Same as partitioning |
| **Merge memory (in-memory)** | ~2 GB | ~200 GB (OOM) | Admission control routes to streaming | Same |
| **Merge memory (streaming)** | Bounded by `max_memory` flag | Same (external sort) | Same, but default | Same |
| **.rkdb file size** | ~2 GB (k=21, 100M entries) | ~200 GB (10B entries) | Same (format unchanged) | Same (format unchanged) |
| **Query speed** | Binary search, O(log n) | Same | Same | Same |

**Key insight:** Partitioning doesn't reduce total memory usage (we still store all distinct k-mers), but it:
- Enables parallelism (no locks)
- Makes memory predictable (shard-local)
- Allows per-shard spill to disk

**Dense storage** (u64 for small k) directly reduces memory by ~50% for the common k ≤ 32 case.

## Incremental Build Order

Based on dependency analysis and risk, here's the recommended build order from least invasive to most invasive:

### Phase 1: Low-Risk Wins (Independent, No Breaking Changes)

**Goal:** Easy wins that don't touch hot paths or APIs.

| Task | Module | Dependencies | Risk | Impact |
|------|--------|--------------|------|--------|
| 1.1 Replace direct console I/O with `log` | `src/database/format.rs`, `src/database/prefix_cache_merge.rs` | None | LOW | Better library hygiene |
| 1.2 Remove dead backup/staging files | `pyo3/src/*_backup.rs`, `.stage1_fix_backup` files | None | LOW | Reduce repo bloat |
| 1.3 Add `rust-version` to `Cargo.toml` | Root manifest | None | LOW | Enforce MSRV |
| 1.4 Add Rust CI workflow (test/clippy/fmt) | `.github/workflows/ci.yml` | None | LOW | Catch regressions |

**Outcome:** Cleaner codebase, enforced MSRV, CI protection. None of these affect counting/merge performance or APIs.

### Phase 2: Safe Merge Path Improvements (Zero API Impact)

**Goal:** Make streaming merge the safe default without breaking the in-memory path.

| Task | Module | Dependencies | Risk | Impact |
|------|--------|--------------|------|--------|
| 2.1 Implement `MemoryBudgetController` | `src/memory/budget.rs` | None | LOW | Foundation for admission control |
| 2.2 Create `merge_orchestrator.rs` | `src/database/merge_orchestrator.rs` | 2.1 | LOW | Centralizes merge routing |
| 2.3 Route CLI merge through orchestrator | `src/cli/commands/merge.rs` | 2.2 | MEDIUM | Changes default behavior |
| 2.4 Add integration tests for merge routing | `tests/integration/merge_routing.rs` | 2.2 | LOW | Validate behavior |
| 2.5 Document new merge behavior | `docs/user-guide/merge.md` | 2.3 | LOW | User communication |

**Outcome:** Merge is OOM-safe by default. In-memory path still accessible via flag. No .rkdb format change, no API change.

**Breaking-change implications:** None (CLI flag changes are additive; `--merge-strategy in-memory` restores old behavior).

### Phase 3: Dense Storage (Internal Optimization, Format-Compatible)

**Goal:** Reduce memory by using u64 for small k.

| Task | Module | Dependencies | Risk | Impact |
|------|--------|--------------|------|--------|
| 3.1 Add `PackedKmer` enum | `src/kmer/encoding.rs` | None | LOW | Representation change |
| 3.2 Modify write path to use packing | `src/database/format.rs` or `src/cli/commands/count.rs` | 3.1 | MEDIUM | Affects .rkdb write |
| 3.3 Modify read path to detect and unpack | `src/database/query.rs`, `src/database/format.rs` | 3.1 | MEDIUM | Affects .rkdb read |
| 3.4 Test backward compatibility | `tests/integration/compatibility.rs` | 3.2, 3.3 | HIGH | Validate old files still read |
| 3.5 Benchmark memory savings | `tests/performance/dense_storage.rs` | 3.2, 3.3 | LOW | Quantify impact |

**Outcome:** ~50% memory reduction for k ≤ 32 (most common case). .rkdb format unchanged (variable-length field already accommodates this).

**Breaking-change implications:** None IF the read path correctly handles both u64 and u128 entries (the format already permits variable-length k-mer encoding). Test 3.4 is critical.

### Phase 4: Partitioned Counting (New Feature, API Extension)

**Goal:** Lock-free parallel counting for human-scale data.

| Task | Module | Dependencies | Risk | Impact |
|------|--------|--------------|------|--------|
| 4.1 Implement `MinimizerPartitioner` | `src/kmer/minimizer.rs` | None | LOW | Core algorithm |
| 4.2 Implement `PartitionedCounter` | `src/hash/partitioned.rs` | 4.1 | MEDIUM | New counter type |
| 4.3 Add `--partitioned` flag to count command | `src/cli/args.rs`, `src/cli/commands/count.rs` | 4.2 | MEDIUM | CLI change |
| 4.4 Rayon-parallelize file processing | `src/cli/commands/count.rs` | 4.2 | HIGH | Parallelism |
| 4.5 Benchmark vs. sequential counting | `tests/performance/partitioned_count.rs` | 4.2, 4.4 | MEDIUM | Validate speedup |
| 4.6 Add PyO3 wrapper for `PartitionedCounter` | `pyo3/src/counter.rs` | 4.2 | MEDIUM | Python API extension |
| 4.7 Document partitioned counting | `docs/user-guide/counting.md` | 4.3, 4.6 | LOW | User communication |

**Outcome:** Lock-free parallel counting, ~4-8× speedup on multi-core systems. No breaking change — `--partitioned` is opt-in initially.

**Breaking-change implications:** None (additive feature). Default can be switched to partitioned in a future version after validation.

### Phase 5: Refactor God Modules (Technical Debt, Post-Performance)

**Goal:** Reduce fragility of `format.rs` and `pyo3/database.rs`.

| Task | Module | Dependencies | Risk | Impact |
|------|--------|--------------|------|--------|
| 5.1 Extract merge logic from `format.rs` | `src/database/merge_impl.rs` | Phase 2 complete | MEDIUM | Smaller modules |
| 5.2 Split `pyo3/database.rs` by concern | `pyo3/src/database/query.rs`, `pyo3/src/database/merge.rs`, etc. | None | MEDIUM | Smaller modules |
| 5.3 Remove deprecated PyO3 methods | `pyo3/src/database.rs` | None | MEDIUM | Cleaner API |
| 5.4 Centralize `data_offset` validation | `src/database/format.rs` | None | LOW | Fix anti-pattern |

**Outcome:** More maintainable codebase. No performance impact, purely structural.

**Breaking-change implications:** Deprecated PyO3 methods removal is a breaking change for the 2.x → 3.0 boundary (acceptable for a major version).

## Interaction with Existing God Modules and Duplicated Logic

### format.rs (1306 lines, God Module)

**Current state:** Mixes `RKDatabase`, `DatabaseHeader`, `KmerEntry`, merge logic, and inline tests.

**Interaction with performance work:**
- **Merge routing (Phase 2):** New `merge_orchestrator.rs` will CALL `format.rs` functions, not absorb them. No immediate refactoring needed.
- **Dense storage (Phase 3):** Will modify `KmerEntry` write/read paths within `format.rs`. Increases complexity temporarily.
- **Post-performance (Phase 5):** Extract merge-specific functions (`merge_databases_inmemory`, `merge_databases_streaming`) to `merge_impl.rs`.

**Recommendation:** Defer major refactoring until after performance phases. Touch `format.rs` only for the specific changes required (dense storage, merge routing). Do the big split in Phase 5 when the hot paths are stable.

### pyo3/database.rs (2053 lines, God Module)

**Current state:** One `#[pyclass] PyDatabase` with dozens of methods, module-wide `#![allow(deprecated)]`.

**Interaction with performance work:**
- **Minimal** — PyO3 layer is a thin wrapper. Core performance work happens in `src/`.
- **Phase 4 (Partitioned Counter):** Will add a `PyPartitionedCounter` class, adding to this module.

**Recommendation:** Leave untouched during performance phases. The split into sub-modules (Phase 5) is purely cosmetic and can wait.

### Duplicated .rkdb Write Logic

**Current state:** `output_binary_format` in `src/cli/commands/count.rs` duplicates the RKDB layout from `src/database/format.rs`.

**Interaction with performance work:**
- **Phase 3 (Dense Storage):** This duplication becomes a liability — must sync the packing logic in TWO places.
- **High priority to fix** before or during Phase 3.

**Recommendation:** Refactor in Phase 1.2 (or 1.5 if added):
1. Create `RKDatabase::from_counter(counts: &KmerCounter)` in `format.rs`
2. Call `rkdb.to_file_path(output)` from `count.rs`
3. Delete `output_binary_format`

This unblocks Phase 3 and reduces technical debt early.

## Breaking-Change Implications

### .rkdb Format

**Current version:** v2 (42-byte header + 20-byte entries per KmerEntry).

**Does any phase require a format bump?**
- **Phase 1-2:** No change.
- **Phase 3 (Dense Storage):** No bump IF the k-mer field is treated as variable-length (it already is). The field stores up to 16 bytes; for k ≤ 32, we write 8 bytes and pad or adjust the reader. The header's `kmer_size` field disambiguates.
- **Phase 4 (Partitioned Counting):** No change — counter implementation is internal; .rkdb write path unchanged.
- **Phase 5 (Refactoring):** No change.

**Verdict:** No .rkdb version bump required for any phase. The v2 format is forward-compatible with dense storage.

### CLI API

**Current commands:** `count`, `query`, `stats`, `dump`, `merge`, `fuzzy-query`, `fuzzy-query-batch`, `prefix-query`.

**Breaking changes:**
- **Phase 2 (Merge Routing):** Changes default merge behavior. Users relying on in-memory merge must pass `--merge-strategy in-memory`. This is a behavioral change but not a removal.
- **Phase 4 (Partitioned Counting):** Adds `--partitioned`, `--shard-count`, `--minimizer-length` flags. No removals.

**Verdict:** No breaking changes to CLI surface. Additive flags only.

### Python API

**Current classes:** `PyDatabase`, `PyCounter`, `PyFuzzyQuery`, `PyPrefixQuery`, `PyFormatter`.

**Breaking changes:**
- **Phase 4:** Adds `PyPartitionedCounter`. Existing classes unchanged.
- **Phase 5:** Removes deprecated methods (e.g., legacy `load` shims). This IS a breaking change but appropriate for a major version bump.

**Verdict:** One breaking change in Phase 5 (deprecated method removal). All performance phases (1-4) are additive.

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| **Partitioned counting architecture** | HIGH | Well-documented in KMC literature; minimizer partitioning is a proven pattern |
| **Dense storage feasibility** | HIGH | .rkdb format already supports variable-length k-mer encoding; no format change needed |
| **Merge routing strategy** | HIGH | Streaming merge already exists; admission control is straightforward |
| **Mapping to existing modules** | MEDIUM | Existing structure is layered and clean; new components fit clearly. God modules (`format.rs`, `pyo3/database.rs`) are concerns but don't block this work |
| **Incremental build order** | MEDIUM | Phases are logically independent, but real-world integration may reveal dependencies (e.g., dense storage may require merge routing tweaks) |
| **No .rkdb format change needed** | MEDIUM-HIGH | The v2 format's variable-length k-mer field should accommodate u64 packing, but this needs verification via testing |
| **Performance impact estimates** | MEDIUM | Based on literature (KMC benchmarks) and theoretical analysis; real benchmarking on CRR1936095 data required |

## Sources

- [KMC: Fast and frugal disk based k-mer counter (GitHub)](https://github.com/refresh-bio/KMC) — Minimizer partitioning reference implementation
- [Abakus: Accelerating k-mer Counting with Storage Technology (ACM)](https://dl.acm.org/doi/full/10.1145/3632952) — Minimizer partitioning strategies
- [Dataset-adaptive minimizer order reduces memory usage (bioRxiv)](https://www.biorxiv.org/content/10.1101/2021.12.02.470910.full) — 30% memory reduction via minimizers
- [Jellyfish: Fast, lock-free k-mer counting (Bioinformatics)](https://academic.oup.com/bioinformatics/article/27/6/764/234905) — Lock-free hash table architecture
- [MQF and Buffered MQF: Quotient Filters for K-mers (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7885209/) — CQF architecture for dense storage
- [HySortK: Distributed memory k-mer counting (arXiv 2024)](https://arxiv.org/pdf/2407.07718) — Distributed memory partitioning
- [Memory Efficient Minimum Substring Partitioning (UCSB)](https://sites.cs.ucsb.edu/~xyan/papers/vldb13_debruijn.pdf) — Partitioning for duplicate k-mer merging
- [KMC 2: Fast and resource-frugal k-mer counting (ResearchGate)](https://www.researchgate.net/publication/263736737_KMC_2_Fast_and_resource-frugal_k-mer_counting) — KMC binary format structure
- [The K-mer File Format: Standardized compact storage (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9477520/) — 3-5× space savings via dense encoding
- [Minimal Encodings of Canonical K-mers (Peer Community)](https://mcb.peercommunityin.org/articles/rec?id=188) — Array-based dense storage for canonical k-mers
- [Krusted: K-mer Counter in Rust using Rayon (Biostars)](https://www.biostars.org/p/9488554/) — Rust + Rayon reference implementation

---

*Architecture research: 2025-06-30*
