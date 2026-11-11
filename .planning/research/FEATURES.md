# Feature Research — Algorithm Landscape for k=21 Counting Parity

**Domain:** High-performance exact k-mer counting (algorithmic techniques, not user-facing features)
**Researched:** 2026-11-11
**Confidence:** MEDIUM overall (algorithm mechanisms cross-checked across papers + theses + source mirrors + the official Jellyfish manual; codebase observations HIGH; Rust-crate availability MEDIUM)
**Milestone:** rustkmer v2.0 "k=21 Counting Parity" — match/beat Jellyfish2 at human-scale k=21, exact u32 counts, canonical k-mers, preserve `.rkdb` v2 + dual CLI/PyO3 surface, MSRV 1.80.

> "Features" here = the **algorithmic techniques** best-in-class exact counters use to be fast at small k. Each is classified TABLE STAKES / DIFFERENTIATOR / ANTI-FEATURE, with mechanism, complexity, and dependency on rustkmer's existing capabilities. The goal is to let the roadmapper see which technique(s) to pursue for k=21 parity and in what order.

---

## The Core Problem: Why k=21 Is Hard (and why k=31 already wins)

At k=21 there are 4^21 ≈ 4.4×10^12 possible k-mers. A human WGS read set yields ~2–3 billion **distinct** k-mers (milestone estimate; Kmerind measured 1,909M distinct at k=21 vs 1,670M at k=31 on a human set — distinct count *falls* as k grows because longer k-mers are more often unique genomic positions while shorter k-mers collapse repeats but admit more error-generated singletons). Direct addressing is infeasible: 4^21 × 2 bits = 1 TiB, × u32 = 16 TiB. So the counter is a **giant hash table** → memory-bandwidth-bound, cache-miss-heavy, hashing-overhead-dominated.

**The decisive mechanism (well-grounded):** small k makes the *per-entry* cost cheap but the *number of entries* large, so the table is huge and every increment is a random DRAM round-trip. What separates Jellyfish2 from rustkmer at k=21 is **bytes-per-entry and lock overhead**, not encoding:

- **Jellyfish2** stores entries **bit-packed**: memory/entry = `2k − l + r + 1` *bits* (l = log2 table size, r = reprobe bits), i.e. ~2–5 bytes/entry at k=21–31 (official manual, §2.3). The k-mer *is* its own hash (invertible GF(2) matrix), so there is no separate hash compute. Increments are **lock-free CAS on 64-bit words** — threads almost never wait. Compact + lock-free → far fewer cache misses and no shard-lock traffic.
- **rustkmer** stores `DashMap<u64,u32>` = 16-byte `(K,V)` slot **+ 24 B modelled hash/shard overhead** (`HASH_OVERHEAD_PER_ENTRY` in `src/hash/table.rs`) ≈ 36 B/entry, plus SwissTable control bytes and ~4×num_cpus shard `RwLock`s. `entry().and_modify().or_insert_with()` takes a **write lock on the shard** per increment. At ~2–3 B distinct k-mers this table is ~5–10× fatter than Jellyfish's → far more DRAM traffic per increment, plus lock/atomic overhead. **This is the k=21 bottleneck hypothesis, and the literature strongly corroborates it.**

**Critical codebase observation (HIGH confidence, direct read):** the current hot path (`src/cli/commands/count.rs::process_one_record`) re-encodes **every window from scratch** via `encode_kmer_bytes_u128` (O(k) per window, per-base `to_ascii_uppercase` + match) and canonicalizes via `reverse_complement_u128` (another O(k) loop per window). This is O(L·k) per read instead of O(L) rolling. **But note:** this cost is *cheaper* at k=21 than k=31 (21 vs 31 bases/window), so encoding is **NOT** the reason k=21 is slower — the table is. Rolling-hash/SIMD encoding is still worth doing (it speeds both k values and is a prerequisite for minimizers), but it is a secondary lever. **Profiling must confirm table-bound vs encoding-bound vs decompression-bound before committing** (milestone already mandates this; the Chorus3 k=17 result was saturating 2-bit on a 135 Mbp reference, NOT this exact-u32 read-set workload).

---

## Feature Landscape

### Table Stakes (must have to compete at small k)

Techniques every best-in-class exact counter has. Missing these = structurally cannot match Jellyfish2/KMC3 at k=21.

| Technique | Why Required | Complexity | rustkmer Status / Notes |
|-----------|--------------|------------|--------------------------|
| **Cache-conscious, compact counting table** | The k=21 table is DRAM-bound; bytes/entry and probe locality dominate runtime. Jellyfish ~2–5 B/entry vs rustkmer ~36 B/entry is the gap. | HIGH | ❌ DashMap is general-purpose, fat (24 B overhead/entry), shard-locked. This is the #1 lever. |
| **Rolling hash (ntHash-class) for k-mer iteration** | O(L) per read instead of O(L·k); also the substrate for computing minimizers. KMC/Jellyfish/Squeakr all avoid per-window re-hash. | MEDIUM | ❌ Current path re-encodes each window O(k). `simd-minimizers`/`fracsync` provide rolling ntHash in Rust. |
| **Bit-parallel canonicalization (revcomp)** | `min(kmer, revcomp)` must be O(1) word ops, not an O(k) loop. Required for canonical mode at speed. | LOW–MEDIUM | ❌ `reverse_complement_u128` is an O(k) base loop. Replace with byte-swap + complement bit trick (u64 for k≤32). |
| **Lock-free or contention-free parallel increments** | Shard write-locks per increment add atomic traffic at 2–3 B keys. Jellyfish CAS is wait-free-ish; KMC avoids sharing via partitioning. | HIGH | ⚠️ DashMap shards reduce but don't eliminate contention; partitioning removes it entirely. |
| **Memory-bounded counting at human scale** | ~2–3 B distinct k-mers must fit practical RAM. KMC bounds to largest bin; Jellyfish spills to disk when `-s` exceeded. | HIGH | ⚠️ Counting is unbounded in RAM today (55.2 GiB at k=31); merge is already bounded (v1.0). |
| **Exact, non-saturating u32 counts** | Contract. Jellyfish uses variable-length counters (multiple entries for high counts) — exact, never capped. | LOW (keep) | ✅ Already exact u32 with overflow guard. Must preserve through any rewrite. |
| **Canonical k-mer support** | Double-stranded DNA; `min(kmer,revcomp)`. | LOW (keep) | ✅ Implemented (`src/kmer/canonical.rs`). |

### Differentiators (rustkmer's edge — where to compete)

Techniques that close the gap *while preserving* exact-u32 + `.rkdb` v2 + dual surface. These are the pursuit candidates.

| Technique | Value Proposition | Complexity | Notes / Dependency on existing capabilities |
|-----------|-------------------|------------|----------------------------------------------|
| **Minimizer/signature partitioning + per-bucket exact counting (KMC-class)** | THE architecture lever. Partition k-mers into content-defined buckets; each bucket's working set fits L2/L3 → cache-local counting; buckets are independent → embarrassingly parallel, **zero shared-table contention**; one-bucket-at-a-time → bounded memory. Attacks the exact bottleneck (DRAM-bound fat table). | HIGH | Builds on existing rayon + **streaming/external-sort merge** (`streaming_merge.rs`, `prefix_cache_merge.rs`) + memmap2. Output stays `.rkdb` v2 (concatenate per-bucket sorted entries). MINIM-01..03 staged. |
| **In-memory partitioned counting (hash-prefix → thread-local tables)** | Lighter stepping-stone: route k-mers by high hash bits to thread-local compact tables, merge at end. Removes DashMap shard-lock contention + improves per-thread locality WITHOUT disk. | MEDIUM | Reuses `KmerCounter::merge` semantics + rayon. Lower risk than full minimizer pipeline; good Phase-1 win if profiling shows lock/contention bound. |
| **Dense u64 per-bucket sub-tables (bucketed hybrid, exact)** | Within a minimizer bucket the remaining address space is small; a dense sub-array or compact sorted vec gives O(1)/cache-local exact counting. Extends the shipped DENSE-01 u64 win to the partitioned regime. | MEDIUM | Depends on partitioning. Preserves exact u32 (dense array of u32, NOT 2-bit saturating). |
| **SIMD 2-bit encoding + canonical minimizers (`simd-minimizers`)** | ~4 s/human-genome single-thread minimizers (AVX2/NEON), canonical ~6 s; ntHash rolling + two-stack sliding min. Makes partitioning's minimizer step cheap. | MEDIUM | Crate is pure Rust, MIT, builds on `packed_seq`/`seq-hash`. Verify MSRV 1.80 + aarch64 NEON path (macOS) + no global-allocator/PyO3 conflict. |
| **Counting Quotient Filter (CQF) — exact mode** | Cache-friendly, mergeable, resizable; Squeakr reports 2–4.3× faster + 1.5–4.3× leaner than KMC2/Jellyfish2 on count+query. Alternative to partitioning. | VERY HIGH | Exact mode needs invertible hash + enlarged remainder. Rust `qfilter` is RSQF (approximate fingerprint, NOT exact-u32); `cqf-rust`/`mqf` wrap C++ (MSRV/build/PyO3 risk). Higher risk than partitioning; defer. |

### Anti-Features (wrong fit — explicitly do NOT pursue)

| Anti-Feature | Why Tempting | Why Wrong for rustkmer | Alternative |
|--------------|--------------|------------------------|-------------|
| **Direct-address 4^21 table** | "k≤32 fits u64, just index it" | 4^21 × 2 bits = 1 TiB, × u32 = 16 TiB. Infeasible. (Jellyfish only direct-addresses k<15.) | Minimizer/signature partitioning into cache-sized buckets. |
| **Saturating 2-bit counters (Chorus3)** | ~5× small-k speedup measured | Breaks exact-u32 contract (clips at 3). Measured at k=17 on 135 Mbp reference, not this workload. Already rejected 2026-11-11. | Exact u32 dense sub-tables per bucket. |
| **`rusty_alloc` global allocator** | Binary-only speed win | Needs MSRV 1.87 (project is 1.80); global allocator disqualified for PyO3 surface. Already rejected. | Standard allocator; win via data structure, not allocator. |
| **GPU counting (Gerbil-style)** | GPU hash insertion is fast | No GPU dep in stack; dual-surface PyO3 wheel can't assume CUDA; GPU speedup vanishes for large k; ~50% of Gerbil runtime is I/O anyway. | CPU minimizer partitioning (Gerbil's *partitioning* idea transfers; the GPU does not). |
| **Replacing `.rkdb` v2 / new persistence engine** | "A better format would be faster" | Out of scope; breaks compatibility + dual surface. Format is not the bottleneck. | Keep `.rkdb` v2; per-bucket sorted entries concatenate into it. |
| **Approximate counting (Bloom/count-min sketch, RSQF default)** | Smaller, faster | Violates exact-u32 contract. (Jellyfish's `--bf` singleton-drop is also approximate — not acceptable here.) | Exact CQF mode if CQF pursued; else exact partitioned counting. |
| **Distributed/cluster counting (Kmerind, HySortK)** | Scales past single-machine RAM | Single-machine scope; separate architecture. | Single-machine rayon partitioning. |

---

## Technique Mechanisms (deep, for the roadmapper)

### 1. KMC3 — minimizer/signature partitioning + disk-backed 2-stage counting  `[TABLE STAKES architecture / DIFFERENTIATOR for rustkmer]`

**Data flow (two stages):**
- **Stage 1 (distribution):** reader threads decompress reads → splitter threads compute each k-mer's **signature** (a restricted canonical minimizer) and group consecutive k-mers sharing a signature into **super-mers** (maximal runs with the same minimizer) → super-mers written to disk **bins** keyed by signature. Partitioning super-mers partitions all k-mers. Many signatures map to one bin heuristically to balance sizes.
- **Stage 2 (sort+count):** each bin loaded into memory **one at a time**, super-mers split into k-mers, **sorted** (KMC2 radix sort; KMC3 a more efficient sort for larger k), adjacent equal k-mers aggregated into exact counts, results flushed, memory freed.

**Signature constraints (the clever bit):** canonical minimizers must **not start with AAA or ACA** and must **not contain AA except at the start**. This avoids A-run-dominated giant bins and tiny super-mers, minimizing (a) the largest bin (which **bounds peak memory**), (b) total bin volume (disk), (c) load imbalance. This is why KMC stays fast and memory-bounded at k=21: the working set is always one balanced bin, not the whole 2–3 B-key table.

**KMC3 over KMC2:** faster input parsing (better I/O throughput), memory-efficient signature→bin assignment, improved sort. KMC3 uses ~constant RAM across k (e.g. 32 GB at k=22..31 in the KMC paper; ~11.9 GB + 151 GB disk in ntStat 2025) where Jellyfish RAM grows with k.

**Fit for rustkmer:** HIGH. This is the standing direction (MINIM-01..03). rustkmer already has the hard parts — rayon parallelism, **external-sort streaming merge**, memmap2. The per-bucket sort+count maps onto the existing merge machinery; output concatenates into `.rkdb` v2. **In-memory variant** (hold super-mers in RAM, process one bucket's k-mers in a cache-sized table) gives the cache-locality speed win without disk I/O; disk-backed is the fallback for the memory ceiling. **Complexity: HIGH** (new partitioning stage + signature/minimizer computation + bucket scheduling). **Confidence: MEDIUM** (mechanism cross-checked: GigaScience benchmark PMC6280066, Comenius thesis, UMD dissertation, WABI 2022; primary KMC3 paper text not directly retrieved — secondary sources agree).

### 2. Jellyfish2 — lock-free invertible-hash table  `[TABLE STAKES reference; the parity target]`

**Mechanism:**
- **Invertible hash:** k-mer (2k bits) multiplied by an invertible binary matrix over GF(2); low l bits = table position; only the **2k−l remainder bits** stored (full key reconstructible from position + remainder + reprobe count). The k-mer effectively *is* its hash → no separate hash compute.
- **Quadratic reprobing:** reprobe i → offset i(i+1)/2; reprobed slots store the **reprobe count** (r bits) instead of the remainder. Memory/entry = `2k−l+r+1` bits; table = `2^l·(2k−l+r+1)/8` bytes (official manual §2.3).
- **Lock-free CAS:** insertion/increment via `__sync_val_compare_and_swap` on **64-bit words**; threads almost never wait → near-linear scaling to 32 threads (paper). When key+counter fit one word, a single CAS suffices.
- **Small k:** for k<15, **direct indexing** (4^k array). For k=21 it's the hash table, but entries are tiny (2k−l small) → compact → cache-friendly.
- **Exact counts:** variable-length counter (`-c` bits, default 7); a k-mer exceeding the field uses **multiple entries** — exact, never capped. When the hash fills (`-s`), it dumps to disk, zeroes, resumes; intermediary files merged later.

**Why fast at k=21 specifically:** compact bit-packed entries (~2–5 B) + k-mer-as-hash + lock-free CAS → minimal DRAM traffic and no lock contention, even with billions of distinct keys. **This is exactly what rustkmer's fat shard-locked DashMap lacks.**

**Fit for rustkmer:** the *target*, not necessarily the *implementation*. Reproducing Jellyfish's bit-packed lock-free hash in Rust is possible but a very large rewrite that risks the exact-u32 + `.rkdb` + PyO3 contract. **Recommendation: match its *properties* (compact, contention-free, cache-local) via partitioning rather than clone its bit-packed CAS table.** **Confidence: MEDIUM-HIGH** (official manual read directly; invertible-hash/CAS/reprobe cross-checked with CSE549 slides, Banana Slug notes, and `large_hash_array.hpp`/`invertible_hash_array.hpp` source mirrors).

### 3. Gerbil / BCALM2 / DSK / Turtle  `[context; partitioning idea transfers, GPU does not]`

- **Gerbil:** two-phase minimizer partitioning (reader→parser→splitter→writer pipeline builds super-mer bins; phase 2 routes k-mers by hash to dedicated hasher threads, GPU accelerates open-addressing quadratic-probe insertion). **~50% of runtime is I/O; threads idle >75%** (NSF PAR profiling) — partitioning is only as fast as its I/O. DGerbil/AdaOrder balances bins by sampling + penalizing high-load minimizers (borrows KMC3's idea). **Takeaway: the CPU minimizer-partitioning structure transfers; the GPU is an anti-feature for rustkmer.**
- **BCALM2:** counting step is a **modified DSK** (via GATB) whose bucket partitioning matches its minimizer compaction stage; buckets compacted in parallel then "reunited." Doesn't strictly honor `-max-memory` during counting. Confirms minimizer-bucket counting is a proven, reusable pattern.
- **DSK:** disk-based, very low memory (6 GB in KMC paper) but slow (~4,200–6,500 s). One of only two tools (with KMC3) accurate at both k=28 and k=55 in the GigaScience benchmark.
- **Turtle:** had **correctness bugs** (outputs mismatched other tools) and aTurtle crashed `std::bad_alloc` on human data. **Cautionary: not a reliability reference.**

**Confidence: MEDIUM** (GigaScience benchmark PMC6280066, Gerbil arXiv 1607.06618 / AMB 2017, BCALM2 PMC4908363, Cuttlefish2 Genome Biology 2022).

### 4. Counting Quotient Filter (CQF)  `[DIFFERENTIATOR, high-risk alternative — defer]`

**Mechanism:** a cache-friendly quotient filter storing quotient+remainder with run/shift metadata; supports insert/delete/**count**/resize/**merge**/concurrent access. **Exact mode** = invertible hash + enlarged remainder (no false positives); approximate mode = MurmurHash + small remainder (one-sided overestimation). Squeakr (Pandey et al., Bioinformatics 2018) reports **2–4.3× faster, 1.5–4.3× leaner** than KMC2/Jellyfish2 on count+point-query; per-thread local CQFs merged into a global CQF. Mantis uses 40-bit invertible hashes for exactness.

**Rust availability (MEDIUM confidence, crates.io + docs.rs + GitHub cross-checked):**
- **`qfilter`** (arthurprs, MIT, ~1M downloads, actively maintained) — **RSQF** (Rank-Select QF) variant, fingerprint API on u64 hashes, xxhash3, deletions/merging/resizing/serde. **Caveat: approximate fingerprint semantics, NOT exact-u32 counting out of the box; requires `popcnt` on x86_64** (panics without; `legacy_x86_64_support` feature ~10% slower). Would need adaptation for exact counts.
- **`COMBINE-lab/cqf-rust`** — wraps the original C++ CQF; true `qf_insert(item,count)`/`qf_count_key_value` semantics. **C++ dependency + libssl + Haswell-optimized build → MSRV/maturin-wheel/PyO3 risk.**
- **`mqf`** (v1.0.0, 2019) — C++ bindings, stale.

**Fit for rustkmer:** cache-friendly + mergeable is attractive and aligns with the existing merge infrastructure, but **exact-u32 + MSRV 1.80 + pure-Rust PyO3 wheel** constraints make the available crates a poor drop-in. **Complexity: VERY HIGH. Recommend DEFER behind minimizer partitioning** (which reuses more existing code and has no C++/approximation risk). Revisit only if partitioning stalls.

### 5. Minimizer / syncmer / UHS theory  `[enabler for partitioning — parameter choice matters]`

- **Density:** random minimizers ≈ 2/(w+1); theoretical lower bound 1/w; miniception ≤1.67/w. Open syncmers ≈ 1/(k−s+1), closed ≈ 2/(k−s+1). Lower density = fewer super-mer boundaries = less I/O.
- **Canonical pitfall (important):** making a scheme canonical via `min(fwd,rc)` can **destroy the window guarantee** (Marçais et al., Bioinformatics 2024). t=0 syncmers keep a strong guarantee; 0<t≤s/2 relaxed; t≥s none. `simd-minimizers` canonical mode requires **odd l = w+k−1** and a preferred-strand heuristic. **Choose (w,k) and canonical scheme carefully so buckets stay balanced and every window is covered.**
- **Non-uniformity:** real genomes aren't i.i.d. — lexicographic and KMC2 orders are highly skewed (max bin ratio 367/166); random/minimap2 orders much flatter (~9–10). **Use a random/ntHash-based order (or KMC-style forbidden-pattern signatures) to avoid giant bins** that would blow the memory bound. UHS-based orders are computationally limited to k≤16 — not directly usable at k=21, but the *sparsity* insight informs order choice.
- **Parameter guidance for k=21:** pick window w to balance bucket count vs super-mer length; larger w → fewer, longer super-mers (less I/O) but coarser buckets. KMC's signature constraints (no AAA/ACA prefix, no internal AA) are a proven anti-skew recipe worth borrowing.

**Confidence: MEDIUM** (Shaw PhD thesis 2024, Zheng CMU thesis 2022/2023, Marçais 2024 btae629, UHS/sparsity paper, ESA 2021).

### 6. SIMD encoding + rolling hash (ntHash)  `[TABLE STAKES enabler; secondary speed lever]`

- **ntHash:** rolling hash `H(i) = rol·H(i−1) ⊕ rol^k·h(r[i−1]) ⊕ h(r[i+k−1])`, O(n) regardless of k; canonical via fwd+rc in one loop. **ntHash2** (Bioinformatics 2022): up to 2.1× faster than v1, fixes the k>64 `rol^64=x` collision bug (split rotation), canonical = **sum** of fwd+rc (not min) for better uniformity. MIT, github.com/bcgsc/ntHash.
- **SIMD 2-bit packing + bit-parallel revcomp:** replace the O(k) per-window `encode_kmer_bytes_u128` + O(k) `reverse_complement_u128` with rolling 2-bit shift-in and word-level revcomp (byte-swap + complement). For k≤32 use u64.
- **Rust:** `simd-minimizers` (rust-seq, SEA 2025, AVX2/NEON, 32-bit ntHash + two-stack sliding min, ~4 s/human-genome) provides rolling hash + minimizers together; `fracsync` documents the O(n) recurrence.

**Is encoding even a significant cost vs the table?** At k=21, encoding is O(L·21) — *cheaper* than k=31 — so it is **not** the k=21 differentiator. But it is (a) a real CPU cost worth removing, and (b) a **prerequisite for minimizer computation**. **Complexity: MEDIUM. Confidence: MEDIUM** (ntHash paper, ntHash2 PMC9563681, simd-minimizers docs.rs/GitHub/SEA 2025). **Caveat: verify simd-minimizers MSRV ≤1.80 and aarch64 NEON path for the macOS/PyO3 surface.**

### 7. Direct-address / bucketed hybrid for k≤32 (exact)  `[DIFFERENTIATOR, depends on partitioning]`

You cannot direct-address 4^21. But **partition first** (by minimizer, or by high hash bits), then within a bucket the remaining address space is small enough for a **dense u32 sub-array** or a compact sorted vec:
- Radix/prefix partition by b high bits → 2^b buckets each covering 4^21/2^b addresses. E.g. b=20 → ~4M addresses × 4 B = 16 MB/bucket (fits L3), processed one at a time. **Caveat: buckets are sparse** (few of the possible k-mers present), so a dense sub-array wastes init time/space — prefer **content-defined minimizer buckets** (balanced occupancy) + per-bucket sort+count or a small compact hash.
- This **extends the shipped DENSE-01 u64 win** into the partitioned regime while keeping **exact u32** (dense u32 array, NOT 2-bit saturating).

**Complexity: MEDIUM (after partitioning exists). Confidence: MEDIUM** (synthesis of KMC bucketing + jellyfish direct-address threshold + DENSE-01 codebase observation).

---

## Feature Dependencies

```
Profiling (root-cause k=21 gap)  [MANDATED FIRST]
    └──informs──> choice of lever
                      ├──> Rolling hash (ntHash) + bit-parallel revcomp + SIMD encode
                      │         └──required-by──> Minimizer computation (simd-minimizers)
                      │                               └──required-by──> Minimizer/signature partitioning
                      │                                                     ├──enables──> Dense u64 per-bucket sub-tables (exact)
                      │                                                     └──reuses──> existing streaming/external-sort merge → .rkdb v2
                      ├──> In-memory hash-prefix partitioned counting (lighter stepping-stone)
                      │         └──reuses──> KmerCounter::merge + rayon
                      └──> CQF (alternative; conflicts with pure-Rust/MSRV/exact constraints) [DEFER]

Anti-features (conflict with contract): saturating counters, 4^21 direct table, rusty_alloc, GPU, .rkdb rewrite, approximate counting
```

### Dependency Notes
- **Profiling gates everything:** the milestone mandates evidence before architecture. Confirm table-bound (expected) vs encoding-bound vs decompression-bound. If decompression-bound (gzip single-threaded per D-02), parallel decompression may be a cheaper first win than any table rewrite.
- **Rolling hash + SIMD encode is a prerequisite for minimizers**, so it lands before/with partitioning even though it's a secondary speed lever on its own.
- **Partitioning reuses the existing merge machinery** (`streaming_merge.rs`, `prefix_cache_merge.rs`, memmap2) — this is why it's lower-risk than CQF and the recommended spine.
- **In-memory hash-prefix partitioning** is a lighter alternative if profiling shows shard-lock contention dominates and full minimizer I/O is overkill.
- **CQF conflicts** with pure-Rust + MSRV 1.80 + exact-u32 (available crates are approximate or C++-backed) → defer.

---

## MVP Definition (recommended pursuit order for k=21 parity)

### Launch With (the parity spine)
- [ ] **Root-cause profiling** on the real CRR1936095/CRR2044018 workload — confirm the fat-table/DRAM-bound hypothesis; measure bytes/entry, cache-miss rate, lock contention, decompression share. (Mandated; cheap; de-risks everything.)
- [ ] **Rolling ntHash + bit-parallel canonicalization + SIMD 2-bit encoding** — remove O(L·k) per-window cost; prerequisite for minimizers. Evaluate `simd-minimizers` (verify MSRV/NEON/PyO3).
- [ ] **Minimizer/signature partitioning + per-bucket exact counting** (KMC-class, in-memory first) — THE architecture lever. Cache-sized buckets, contention-free parallelism, bounded memory, `.rkdb` v2 output via existing merge. Borrow KMC signature anti-skew constraints; use random/ntHash order for balance.

### Add After Validation
- [ ] **Dense u64 per-bucket sub-tables** — extend DENSE-01 into buckets for cache-local exact counting (trigger: per-bucket sort+count is the bottleneck).
- [ ] **Disk-backed bucket spill** — only if the in-memory variant exceeds the RAM ceiling (trigger: profiling/memory gate). Reuses streaming merge; never mmap spill when RSS is the budget (Chorus3 discipline).
- [ ] **KMC3 benchmark comparison (BENCH-V2-01)** — second validation reference once partitioning lands.

### Future Consideration (defer)
- [ ] **CQF (exact mode)** — only if partitioning stalls; needs a pure-Rust exact-u32 CQF (none off-the-shelf). High risk.
- [ ] **In-memory hash-prefix partitioning** — may be promoted to Phase-1 quick win if profiling shows contention-bound rather than pure DRAM-bound.

---

## Feature Prioritization Matrix

| Technique | Parity Value | Implementation Cost | Priority |
|-----------|--------------|---------------------|----------|
| Root-cause profiling | HIGH (gates all) | LOW | **P1** |
| Rolling hash + bit-parallel revcomp + SIMD encode | MEDIUM (enabler + secondary speed) | MEDIUM | **P1** |
| Minimizer/signature partitioning + per-bucket exact count | HIGH (the lever) | HIGH | **P1** |
| Dense u64 per-bucket sub-tables | MEDIUM | MEDIUM | P2 |
| Disk-backed bucket spill | MEDIUM (memory ceiling) | MEDIUM | P2 |
| In-memory hash-prefix partitioned counting | MEDIUM (lighter alt) | MEDIUM | P2 (promote if contention-bound) |
| CQF exact mode | MEDIUM | VERY HIGH | P3 (defer) |
| GPU / distributed / saturating / 4^21 direct / rusty_alloc | — | — | **Anti-feature** |

**Priority key:** P1 = parity spine; P2 = add when triggered; P3 = defer/future.

---

## Competitor / Reference Analysis

| Dimension | Jellyfish2 (target) | KMC3 (model to borrow) | Gerbil | rustkmer today | rustkmer plan |
|-----------|---------------------|------------------------|--------|----------------|---------------|
| Core structure | Lock-free invertible-hash, bit-packed | Minimizer/signature bins + sort+count | Minimizer bins + GPU hash | Fat shard-locked DashMap | Minimizer bins + per-bucket exact count |
| Bytes/entry | ~2–5 B (2k−l+r+1 bits) | bin-bounded | compact | ~36 B (24 overhead+12) | dense u64 per bucket |
| Parallelism | CAS, wait-free-ish | independent bins | hasher threads + GPU | rayon + DashMap shards | independent bins (no sharing) |
| Memory at human k=21 | grows with k; spills at `-s` | ~constant (largest bin) | low + disk | unbounded RAM | bounded (one bucket at a time) |
| Exact counts | yes (multi-entry counter) | yes | yes | yes (u32) | yes (u32, preserved) |
| Small-k strength | compact + lock-free | balanced bins, cache-local | partitioning (I/O-bound) | — | borrow KMC bins, match Jellyfish properties |
| Fit to constraints | reference only | HIGH (reuses merge) | GPU = anti-feature | — | exact-u32 + .rkdb v2 + dual surface |

**Bottom line for the roadmapper:** pursue **minimizer/signature partitioning with per-bucket exact counting** as the spine (it attacks the confirmed fat-table/DRAM bottleneck, reuses the existing external-sort merge + rayon + memmap2, and preserves `.rkdb` v2 + exact-u32 + dual surface). Land **rolling-hash/SIMD encoding** first as its prerequisite. **Profile before committing.** Treat **CQF as a deferred alternative** and **GPU/saturating/direct-4^21/rusty_alloc as anti-features.** Match Jellyfish's *properties* (compact, contention-free, cache-local) rather than cloning its bit-packed CAS table.

---

## Sources (confidence per research-seam: websearch cross-checked = MEDIUM; webfetch = LOW→raised where primary; codebase = HIGH)

### Primary / official (read directly)
- Jellyfish manual v1.1.4 (official PDF, read in full) — memory/entry `2k−l+r+1` bits, `-s` hash size + disk-dump-on-full, `-c` variable-length exact counter, `-C` canonical, `-p` reprobes. https://gensoft.pasteur.fr/docs/jellyfish/2.3.0/jellyfish.pdf  *(MEDIUM-HIGH: primary source)*
- Codebase (HIGH, direct read): `src/hash/table.rs` (DashMap, 24 B `HASH_OVERHEAD_PER_ENTRY`, shard write-lock per `entry()`), `src/cli/commands/count.rs::process_one_record` (O(k) per-window re-encode + O(k) revcomp), `src/kmer/encoding.rs`, `src/kmer/canonical.rs`.

### Algorithm papers / theses (MEDIUM, cross-checked)
- KMC3: GigaScience benchmark PMC6280066 (https://pmc.ncbi.nlm.nih.gov/articles/PMC6280066/); Comenius thesis (signature constraints); UMD dissertation; WABI 2022 LIPIcs.WABI.2022.12. Primary KMC3 paper (Kokot 2017, Bioinformatics 33:2759) text not directly retrieved — secondary sources agree.
- Jellyfish hash: CSE549 slides https://rob-p.github.io/CSE549F16/lectures/CSE549-Lec16-Kmers.pdf; source mirrors `large_hash_array.hpp`, `invertible_hash_array.hpp`, `compare_and_swap.hpp` (gitlab.ics.uci.edu/mars-research/kvstore/Jellyfish); paper PMC3051319 (captcha-blocked).
- Gerbil: arXiv 1607.06618 / AMB 2017 (https://rd.springer.com/article/10.1186/s13015-017-0097-9); DGerbil/AdaOrder bioRxiv 2021.12.02.470910; I/O profiling NSF PAR 10534719.
- BCALM2: PMC4908363; Cuttlefish2 Genome Biology 2022 (s13059-022-02743-6).
- CQF/Squeakr: Bioinformatics 34:568 (https://academic.oup.com/bioinformatics/article-pdf/34/4/568/48913860/bioinformatics_34_4_568.pdf); bioRxiv 122077; Mantis Cell Systems 2018.
- Minimizer/syncmer/UHS: Shaw PhD thesis 2024 (Toronto); Zheng CMU thesis 2022/2023; Marçais 2024 Bioinformatics btae629; UHS/sparsity paper; ESA 2021 LIPIcs-ESA-2021-64.
- ntHash/ntHash2: ntHash paper (ScienceOpen PubMedCentral); ntHash2 PMC9563681 / Bioinformatics btac564.
- Benchmark context: Kmerind IEEE/ACM TCBB 2017 (distinct 1909M@k21 vs 1670M@k31); Merfin Nature Methods 2022 supplement (k31 = 1.5× mem, 1.6–2.6× compute vs k21; 72–89% singletons); KMC paper Table 2 PMC3680041; ntStat PLOS Comp Biol 2025.

### Rust crates (MEDIUM, crates.io + docs.rs + GitHub)
- `simd-minimizers` (rust-seq, SEA 2025, MIT, AVX2/NEON): https://github.com/rust-seq/simd-minimizers , https://crates.io/crates/simd-minimizers — **verify MSRV ≤1.80 + aarch64 NEON + PyO3 compatibility before adopting.**
- `qfilter` (arthurprs, MIT, RSQF, approximate fingerprint, needs popcnt): https://docs.rs/crate/qfilter — NOT exact-u32 out of the box.
- `COMBINE-lab/cqf-rust` (C++ wrapper, exact counting): https://github.com/COMBINE-lab/cqf-rust — C++/libssl/MSRV/wheel risk.
- `mqf` (C++ bindings, stale 2019): https://lib.rs/crates/mqf .
- `fracsync` (rolling ntHash port): https://docs.rs/fracsync .

### Gaps / to validate in phase-specific research
- Primary KMC3 paper exact sort algorithm + signature→bin mapping details (secondary sources only).
- `simd-minimizers` MSRV and aarch64/PyO3 build compatibility (not yet verified against 1.80).
- Whether the real workload is table-bound vs decompression-bound (profiling — mandated, not yet run).
- Exact distinct-k-mer count and bytes/entry on CRR1936095/CRR2044018 at k=21 (profiling).
- Whether a pure-Rust exact-u32 CQF exists or must be built (none found off-the-shelf).

---
*Feature research for: rustkmer v2.0 k=21 counting parity (algorithm landscape)*
*Researched: 2026-11-11*