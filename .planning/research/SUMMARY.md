# Project Research Summary

**Project:** rustkmer (performance enhancement milestone)
**Domain:** Bioinformatics — k-mer counting at human-genome scale
**Researched:** 2026-06-30
**Confidence:** HIGH

## Executive Summary

The rustkmer performance milestone targets human-genome-scale k-mer counting (2.5–3B distinct k-mers from Illumina WGS data) with bounded memory usage. Research across the 2025–2026 literature converges on two dominant architectural patterns for this scale: **KMC-style minimizer-based partitioning** (memory-efficient, disk-backed) and **Jellyfish-style lock-free concurrent hash tables** (speed-focused, in-memory). The recommended path for rustkmer is a **hybrid approach**: adopt sharded concurrent hash maps (via `dashmap`) to eliminate the current `RwLock<HashMap>` bottleneck, implement minimizer-based partitioning for memory-bounded scenarios, and optimize storage density with conditional u64 packing for k ≤ 32.

Key risks are well-documented in the literature and have concrete mitigations. The primary bottleneck is the current single-threaded counting with `num_threads = 1` hardcoded and a `RwLock`-protected HashMap that will cause severe lock contention when parallelized. Merge operations currently default to an in-memory path that OOMs on large datasets despite existing streaming merge infrastructure. The research strongly recommends preserving the `.rkdb` v2 format (no breaking change) while optimizing internally, making streaming merge the default, and validating performance against KMC3/Jellyfish2 using the CRR1936095 human genome dataset with fair benchmark methodology.

## Key Findings

### Recommended Stack

**Core technologies (from STACK.md):**

- **dashmap 5.5+** — Lock-free sharded concurrent HashMap replacing `RwLock<HashMap>`; eliminates global lock bottleneck, enables true parallel counting
- **Minimizer-based partitioning** (custom implementation, no established Rust crate) — KMC-style two-pass counting with disk-backed partitions; enables bounded-memory counting on any hardware
- **rayon 1.10+** (upgrade from 1.8) — Data parallelism for file processing; latest optimizations for human-scale data
- **hashbrown 0.15+** (upgrade from 0.14) — HashMap backend with measurable performance improvements
- **Conditional u64 storage** (via `PackedKmer` enum) — Store k ≤ 32 as 8 bytes instead of 16; 50% memory reduction for common k values

**Rust crates to avoid:** `crossbeam::HashMap` (deprecated, use dashmap); probabilistic filters (bloom, cuckoo) — incompatible with exact-counting semantics.

### Expected Features

**Must have (table stakes from FEATURES.md):**
- **Parallel counting** — Current code has `num_threads = 1` hardcoded; KMC3 and Jellyfish2 both parallel
- **Memory budgeting/hard caps** — No admission control currently; in-memory merge loads all k-mers unbounded
- **Disk spill for large datasets** — Streaming merge exists but not default; in-memory path OOMs at scale
- **Variable-width k-mer storage** — Current u128 for all k wastes memory for k ≤ 32 (common case)
- **Streaming merge as default** — In-memory merge unsafe for human-scale data

**Should have (competitive):**
- **Minimizer-based partitioning** — KMC's core advantage; enables lock-free parallelism without contention
- **Adaptive merge routing** — Choose in-memory vs streaming based on estimated memory vs budget
- **u64 packing for k ≤ 32** — 2× memory reduction; standard optimization in production tools

**Defer (v2+, out of scope for performance milestone):**
- New query types, set operations, distributed counting, new output formats, visualization UI

### Architecture Approach

**From ARCHITECTURE.md:** Recommended migration to a partitioned counting architecture with lock-free sharded HashMaps, memory-budget-aware merge routing, and dense storage for small k. The existing layered structure (CLI/Python → core library → RKDB format) remains intact; changes are internal to the counting and merge layers.

**Major components to add:**
1. **PartitionedCounter** (`src/hash/partitioned.rs`) — Minimizer-sharded counters for lock-free parallel counting
2. **DenseKmerStore** (`src/hash/dense.rs`) — Packed u64/u128 storage conditional on k-mer size
3. **StreamingMergeOrchestrator** (`src/database/merge_orchestrator.rs`) — Admission-controlled merge routing
4. **MemoryBudgetController** (`src/memory/budget.rs`) — Memory estimation for counting/merge decisions
5. **MinimizerPartitioner** (`src/kmer/minimizer.rs`) — Computes minimizers for shard routing

**Data flow changes:** Current single-threaded sequential file processing → Rayon-parallel file processing with minimizer-based shard routing. Current in-memory merge default → streaming merge default with admission control.

### Critical Pitfalls

**From PITFALLS.md — top 5 with highest severity:**

1. **Single RwLock HashMap contention** — When parallelizing current `RwLock<HashMap<u128,u32>>`, all threads contend on same lock. **Prevention:** Sharded HashMaps (dashmap) with cache-line padding per shard.

2. **In-memory merge OOM** — `merge_databases_inmemory` loads all k-mers unbounded; human-scale data (2.5–3B distinct) requires 75–120 GB. **Prevention:** Route to streaming merge by default with admission control (estimate memory before allocating).

3. **Temp file exhaustion on streaming merge failure** — `prefix_cache_merge.rs` writes 256+ temp files but cleanup only on success path. **Prevention:** RAII temp file guard with Drop cleanup; test error paths.

4. **False sharing in counter arrays** — Even with sharding, contiguous Vec storage causes cache line bouncing between threads. **Prevention:** Pad shards to cache-line alignment (64 bytes on x86).

5. **Benchmark methodology errors** — Common mistakes produce false wins: not including decompression time, cached inputs, mismatched settings vs reference tool. **Prevention:** Cold-cache runs, validate output identical, match reference settings (k, canonicalization, quality filtering).

## Implications for Roadmap

Research converges on a **four-phase incremental roadmap** from low-risk wins to core performance work. This ordering resolves tensions between researcher recommendations: ARCHITECTURE.md suggested starting with code hygiene (Phase 1), while STACK.md and FEATURES.md prioritized parallel counting; the synthesis places parallel counting second but behind the foundational work that unblocks it (console I/O cleanup, CI protection, and fixing duplicated RKDB write logic that would otherwise block dense storage).

### Phase 1: Foundation (Low-Risk Wins)
**Rationale:** Unblocks later phases by fixing structural debt that would otherwise complicate performance work. Duplicated RKDB write logic in `count.rs` and `format.rs` becomes a liability when adding dense storage (Phase 3); fixing it now prevents sync bugs. Console I/O cleanup in library code is a prerequisite for the benchmark harness (Phase 4).

**Delivers:** Clean codebase, CI protection, consolidated RKDB write path, proper logging.

**Addresses:** None of the performance features directly; this is infrastructure.

**Avoids:** Pitfall #5 (canonicalization regressions) by consolidating format logic; Pitfall #8 (benchmark methodology) by enabling proper harness construction.

**Stack elements:** None new (dependency upgrades deferred to Phase 2).

**Confidence:** HIGH — Pure refactoring, well-understood patterns.

### Phase 2: Parallel Counting Infrastructure
**Rationale:** Highest-impact performance gain. Removing `num_threads = 1` and replacing `RwLock<HashMap>` with `dashmap` eliminates the primary bottleneck. STACK.md estimates 2–4× speedup; this is the main deliverable for the milestone's "competitive with KMC3/Jellyfish2" goal.

**Delivers:** Lock-free parallel counting via sharded concurrent HashMap, dependency upgrades (rayon 1.10, hashbrown 0.15, ahash 0.8.11), microbenchmarks for counting hot path.

**Addresses:** Parallel counting (top table-stakes gap from FEATURES.md), RwLock bottleneck (Pitfall #1).

**Uses:** dashmap 5.5+, rayon 1.10+ (from STACK.md).

**Implements:** PartitionedCounter component (ARCHITECTURE.md).

**Avoids:** Pitfall #1 (lock contention), Pitfall #2 (false sharing via cache-line padding).

**Confidence:** HIGH — dashmap is battle-tested; pattern is well-documented.

### Phase 3: Memory Safety (Merge + Dense Storage)
**Rationale:** Merge safety and dense storage are synergistic — both touch the RKDB format read/write paths. Doing them together consolidates format changes and reduces integration risk. Streaming merge default prevents OOMs (Pitfall #3); dense storage reduces memory pressure for the common k ≤ 32 case (50% savings).

**Delivers:** Streaming merge as default with admission-controlled routing, u64 packing for k ≤ 32 (PackedKmer enum), RAII temp file guards for cleanup.

**Addresses:** Memory budgeting (table-stakes gap), disk spill for large datasets (table-stakes), variable-width storage (differentiator).

**Uses:** ext-sort 0.1.5+ (optional, existing streaming_merge.rs may suffice).

**Implements:** StreamingMergeOrchestrator, MemoryBudgetController, DenseKmerStore (ARCHITECTURE.md components).

**Avoids:** Pitfall #3 (in-memory OOM), Pitfall #4 (temp file exhaustion), Pitfall #6 (format version breakage via backward-compat testing).

**Confidence:** HIGH — Streaming merge already exists; dense storage format-compatible (.rkdb v2 supports variable-length k-mer field).

### Phase 4: Memory-Bounded Counting (Minimizer Partitioning)
**Rationale:** Most complex phase; saved for last because it's optional for competitiveness (parallel counting from Phase 2 already achieves 2–4× speedup). Minimizer partitioning enables counting on any hardware within configurable memory bounds but requires new algorithm (no established Rust crate; custom implementation needed). This phase validates the full KMC-style architecture.

**Delivers:** Minimizer-based partitioned counting (two-pass: partition → count → merge), `--max-memory` flag for counting, SSD-aware I/O throttling.

**Addresses:** Disk spill for large datasets (advanced), minimizer partitioning (differentiator), hard memory cap enforcement.

**Implements:** MinimizerPartitioner, enhanced PartitionedCounter with spill-to-disk (ARCHITECTURE.md).

**Avoids:** Pitfall #7 (disk I/O bottleneck via adaptive parallelism), Pitfall #10 (imbalanced buckets via adaptive prefix length).

**Confidence:** MEDIUM — Algorithm is well-documented (KMC3) but Rust implementation is from scratch; requires extensive testing.

### Phase 5: Validation (Benchmark Harness + Fair Comparison)
**Rationale:** Final phase validates "competitive with KMC3/Jellyfish2" success criterion using CRR1936095 human genome data. Must demonstrate fair comparison: cold-cache runs, identical input validation, matching settings (k, canonicalization, quality filtering). This phase produces the evidence that the milestone is complete.

**Delivers:** Benchmark harness for KMC3/Jellyfish2 comparison, validation on CRR1936095 dataset, performance report.

**Addresses:** Benchmark methodology (Pitfall #8), quality filtering consistency (Pitfall #13).

**Avoids:** Pitfall #8 (unfair comparison), Pitfall #13 (quality filtering mismatch).

**Confidence:** HIGH — Methodology is standard; work is measurement rather than algorithm development.

### Phase Ordering Rationale

**Dependency flow:**
- Phase 1 → Phase 2: Duplicated RKDB write logic consolidation prevents sync bugs when adding dense storage in Phase 3.
- Phase 2 → Phase 3: Parallel counting infrastructure is prerequisite for memory-bounded counting (Phase 4); merge defaulting and dense storage can be done in parallel.
- Phase 3 → Phase 4: Streaming merge default and dense storage reduce memory pressure, making minimizer partitioning's complexity worth the investment.
- Phase 4 → Phase 5: All optimizations complete before validation.

**Risk escalation:**
- Phases 1–2 are low-risk (well-understood patterns).
- Phase 3 is medium-risk (format changes but backward-compatible).
- Phase 4 is high-risk (new algorithm, custom implementation).
- Phase 5 is validation (risk is measurement, not implementation).

**Conflict resolution:**
- STACK.md suggested "low-hanging fruit" (dashmap) first; ARCHITECTURE.md suggested code hygiene first. **Resolved:** Do code hygiene (Phase 1) first because it unblocks dense storage (consolidates RKDB write logic) and doesn't delay parallel counting significantly.
- FEATURES.md prioritized minimizer partitioning as a differentiator. **Resolved:** Defer to Phase 4 because it's highest complexity; parallel counting (Phase 2) delivers more speedup with less risk.

### Research Flags

**Phases requiring deeper research during planning:**

- **Phase 4 (Minimizer Partitioning):** Complex algorithm implementation from scratch; no established Rust crate. Recommend `--research-phase 4` during planning to validate minimizer selection details, minimizer length (m=10–12) for human genome, and shard count tuning.

- **Phase 5 (Benchmark Harness):** Requires reference tool setup and CRR1936095 dataset validation. Recommend `--research-phase 5` for benchmark harness design, fair comparison methodology, and dataset access.

**Phases with standard patterns (skip research-phase):**

- **Phase 1:** Well-documented refactoring patterns; clear dependency upgrades.
- **Phase 2:** dashmap usage is standard; lock-free concurrent hashing is established pattern.
- **Phase 3:** Streaming merge and dense storage are standard optimizations; .rkdb format compatibility is straightforward.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack** | HIGH | Dashmap, rayon, hashbrown upgrades are battle-tested; crate versions verified as of 2026-06-30 |
| **Features** | HIGH | Table-stakes gaps (parallel counting, memory budgeting) are unequivocally missing; differentiators align with KMC/Jellyfish literature |
| **Architecture** | MEDIUM-HIGH | Partitioned counting pattern is well-documented (KMC3); mapping to rustkmer's module structure is clear; god modules are concerns but don't block this work |
| **Pitfalls** | HIGH | All 16 pitfalls are backed by literature or direct codebase observation; mitigations are concrete and tested in production tools |
| **Phase ordering** | MEDIUM-HIGH | Phases are logically independent; real-world integration may reveal dependencies (e.g., dense storage may require merge routing tweaks) but current ordering minimizes risk escalation |

**Overall confidence:** HIGH — Recommendations converge across independent research files; conflicts are resolved with explicit rationale; open decisions are surfaced clearly.

### Gaps to Address

**Gaps identified during research:**

1. **Exact minimizer implementation in Rust** — No established crate; must reference KMC3 or implement from scratch. **Handle during Phase 4 planning:** Allocate research spike for minimizer selection algorithm; verify minimizer length (m) choice for human genome.

2. **Real-world dashmap performance on CRR1936095** — Literature suggests 2–4× speedup; needs validation. **Handle during Phase 2 execution:** Benchmark dashmap vs current RwLock on real data; adjust if speedup insufficient.

3. **.rkdb v2 backward compatibility for dense storage** — Research indicates format is forward-compatible (variable-length k-mer field) but needs verification. **Handle during Phase 3 execution:** Add comprehensive compatibility tests; verify old v2 files readable after packing changes.

4. **Reference tool selection for benchmarking** — KMC3 vs Jellyfish2 as comparator? **Handle during Phase 5 planning:** Decision needed; both are valid. Recommendation: benchmark against both for comprehensive comparison.

5. **Format version bump for dense storage?** — Research says "no bump needed" but this is architecture researcher's inference. **Handle during Phase 3 execution:** If format compatibility breaks, add migration path and `rustkmer migrate` command.

## Sources

### Primary (HIGH confidence)

**Academic literature:**
- [KMC3: counting and manipulating k-mer statistics (Oxford Academic)](https://academic.oup.com/bioinformatics/article-pdf/33/17/2759/49040995/bioinformatics_33_17_2759.pdf) — Minimizer partitioning architecture, external sort merge
- [Jellyfish2: fast, lock-free concurrent k-mer counting (Bioinformatics)](https://academic.oup.com/bioinformatics/article/27/6/764/234905) — Lock-free hash table design, CAS operations
- [HySortK: High-Performance Sorting-Based k-mer Counting (SC '24)](https://dl.acm.org/doi/fullHtml/10.1145/3673038.3673072) — 2024 state-of-art: supermer concept, 2× speedup
- [Abakus: Accelerating k-mer Counting with Storage Technology (ACM)](https://dl.acm.org/doi/full/10.1145/3632952) — Minimizer partitioning, SSD vs HDD performance
- [A benchmark study of k-mer counting methods (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6280066/) — Runtime and memory comparisons, KMC/Jellyfish performance

**Production implementations:**
- [KMC GitHub Repository](https://github.com/refresh-bio/KMC) — Reference minimizer-based implementation
- [Jellyfish GitHub Repository](https://github.com/gmarcais/jellyfish) — Lock-free hash reference

**Rust ecosystem:**
- [dashmap - crates.io](https://crates.io/crates/dashmap) — Concurrent HashMap documentation and benchmarks
- [rayon - crates.io](https://crates.io/crates/rayon) — Data parallelism patterns

### Secondary (MEDIUM confidence)

- [The K-mer File Format: standardized compact format (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9477520/) — Dense encoding strategies
- [MQF and buffered MQF: quotient filters for k-mers (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7885209/) — CQF architecture (rejected for exact-counting scope)
- [Dataset-adaptive minimizer order reduces memory usage (bioRxiv)](https://www.biorxiv.org/content/10.1101/2021.12.02.470910.full) — Minimizer optimization strategies
- [ext-sort - GitHub](https://github.com/dapper91/ext-sort-rs) — External sort crate for Rust

### Codebase context (HIGH confidence — direct observation)

- `src/cli/commands/count.rs:121` — `num_threads = 1` hardcoded
- `src/hash/table.rs` — `RwLock<HashMap<u128, u32>>` concurrent counter
- `src/database/format.rs:752-842` — In-memory merge loads unbounded
- `src/database/streaming_merge.rs`, `src/database/prefix_cache_merge.rs` — Streaming merge exists but not default
- `src/kmer/encoding.rs` — u128 encoding for all k (k ≤ 64)

### Tertiary (LOW confidence)

- Community discussions on Reddit/Rust Users Forum about external sort and bloom filter landscape (web search only, not validated against production code)

---
*Research completed: 2026-06-30*
*Ready for roadmap: yes*
