# Feature Landscape

**Domain:** k-mer counting and querying toolkit
**Researched:** 2026-06-30
**Focus:** Performance-relevant capabilities for competitive k-mer counting

## Table Stakes

Features users expect from a production-grade k-mer counter. Missing = product feels incomplete for serious bioinformatics work.

| Feature | Why Expected | Complexity | rustkmer Status | Notes |
|---------|--------------|------------|------------------|-------|
| **Canonical k-mer representation** | DNA is double-stranded; canonical (min(kmer, revcomp)) prevents double-counting | Low | ✅ Has (`src/kmer/canonical.rs`) | Already implemented correctly |
| **Parallel counting** | Human genome (3B+ k-mers) requires multi-threading for practical runtime | High | ❌ Single-threaded (`num_threads = 1` hardcoded) | Critical gap; KMC3 and Jellyfish2 both parallel |
| **Memory budgeting / hard caps** | Users need to prevent OOM on shared machines; predictability requirement | High | ❌ No admission control; in-memory merge loads all k-mers unbounded | KMC3: explicit memory parameter; Jellyfish2: `-s` size flag |
| **Disk spill for large datasets** | Human genome exceeds typical RAM; must gracefully spill to disk | High | ⚠️ Streaming merge exists but not default; in-memory path unbounded | KMC3's core strength; Jellyfish2 is pure in-memory |
| **Canonicalization toggle** | Some workflows need strand-specific counts, most don't | Low | ✅ `--canonical` flag exists | Matches both KMC3 (`-ci`) and Jellyfish2 (`-C`) |
| **Supported k range (k ≤ 31 or k ≤ 64)** | Short reads (k=21-31) and long reads (k=31-127) both common | Low | ✅ k ≤ 64 supported (u128 encoding) | Competitive; Jellyfish2: k ≤ 31, KMC3: k ≤ 256 |
| **Count saturation handling** | High-coverage k-mers exceed u32::MAX (4.29B); silent corruption unacceptable | Medium | ⚠️ u32 counts with saturation at u32::MAX, no warning | KMC3: configurable counter width; Jellyfish2: 64-bit by default |
| **Binary output format** | Text is too large; binary required for storage efficiency | Medium | ✅ Custom `.rkdb` binary format | KMC has KMC1/KMC2; Jellyfish has binary format |
| **Text export (dump)** | Interoperability with downstream tools; human inspection | Low | ✅ `dump` command supports text formats | Both KMC3 and Jellyfish2 support export |
| **Merge databases** | Combining counts from multiple samples/large datasets split for counting | High | ⚠️ In-memory merge only; loads all inputs unbounded | KMC3: `kmc_tools merge` efficient; rustkmer has streaming merge unused |
| **Merge semantics: union with sum** | Standard merge behavior: counts summed when k-mer appears in multiple inputs | Medium | ✅ Streaming merge sums correctly | Matches expected semantics |
| **Memory-mapped database reads** | Fast query without loading full database | Low | ✅ `memmap2` support in query path | Performance optimization already present |
| **Progress reporting** | Long-running counts need user feedback; estimation of completion | Medium | ⚠️ Limited progress feedback (Chinese strings in merge code) | KMC3: detailed progress; Jellyfish2: hash table stats |
| **Compressed input support** | FASTQ/FASTA commonly gzipped; decompress-on-the-fly expected | Low | ✅ Supports gzip via `flate2`, `bio` crate | Standard feature |
| **FASTA + FASTQ support** | Both formats universally used in genomics | Low | ✅ `FastaProcessor` and `FastqProcessor` | Standard feature |
| **Counter width options** | Low-coverage projects: u16 sufficient; metagenomics: u64 needed | Medium | ❌ Fixed u32 for all counts | KMC3: `-ci` and `-cs` for counter size |
| **Output sorting** | Some downstream tools require sorted k-mer lists | Low | ✅ Optional sort before write | Standard feature |

## Differentiators

Features that separate leaders (KMC3, Jellyfish2) from the pack. Not expected, but valued when present.

| Feature | Value Proposition | Complexity | In Scope for Perf Milestone? |
|---------|-------------------|------------|------------------------------|
| **Minimizer/signature-based partitioning** | Enables parallel counting without lock contention; orders k-mers for efficient disk-backed merge | High | ⚠️ Partial - aligns with performance goal but algorithm is new work | KMC3's signature partitioning is its core advantage over hash-based approaches |
| **Supermer concept** | Groups k-mers sharing same minimizer; reduces memory and I/O | High | ❌ No - advanced optimization beyond baseline competitiveness | 2024 research (HySortK) shows 2x speedup + 30% memory reduction |
| **Variable-width k-mer storage** | u64 for k ≤ 32 instead of u128: ~2x memory reduction for common cases | Medium | ✅ Yes - directly addresses performance goal | Current rustkmer uses u128 for all k; wastes memory for k ≤ 32 |
| **Counting Quotient Filter (CQF)** | Space-efficient probabilistic structure; ~2-3x more compact than hash map | Very High | ❌ No - would require major architecture rewrite | Used by modern tools; KMC3 uses sort+aggregate instead |
| **Lock-free concurrent hash** | Jellyfish2's approach: eliminates mutex overhead; high parallelism | High | ⚠️ Maybe - aligns with parallel counting goal | Current `parking_lot::RwLock<HashMap>` is bottleneck |
| **Distributed memory counting** | Scales beyond single-machine RAM; cluster deployment | Very High | ❌ No - out of scope (single-machine focus stated) | 2024 trend (HySortK) but not milestone target |
| **Adaptive minimizer ordering** | 30% memory reduction by choosing minimizer scheme based on dataset skew | Medium | ❌ No - advanced optimization beyond baseline | Published 2021-2022 research |
| **Query acceleration structures** | Prefix query, fuzzy matching already present | Low | ❌ No - milestone scope is counting/merging only | rustkmer already has these; not perf focus |
| **Streaming k-way merge** | Merge N databases in O(N log k) with bounded memory | Medium | ✅ Yes - exists but not default; making it default is win | `streaming_merge.rs` and `prefix_cache_merge.rs` already implemented |
| **Hard memory cap enforcement** | User specifies max memory; tool respects it absolutely | Medium | ✅ Yes - admission control before allocation | KMC3's `-m` parameter; prevents OOM |
| **Multiple output format support** | KMC, KFF, Jellyfish, BED for interoperability | Low | ❌ No - not perf-critical; compatibility Nice-to-have | KFF (K-mer File Format) achieves 3-5x space savings |
| **Set operations (union/intersection/difference)** | Comparative genomics workflows require database algebra | High | ❌ No - milestone is counting/merging only | GenomeTester4's GListCompare; not perf round |

## Anti-Features

Features to explicitly NOT pursue this round (performance milestone focus).

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **New query types** | Milestone is counting+merging performance; query already fast | Focus optimization on counting path only |
| **New output formats** | KFF/Jellyfish format support doesn't improve counting speed | Keep `.rkdb` format; focus on counting efficiency |
| **Distributed/cluster counting** | Single-machine scope; distributed is separate architecture | Optimize single-machine parallelism with Rayon |
| **Visualization UI** | CLI + library product; UI is separate concern | Maintain CLI/Python surfaces only |
| **Real-time/streaming counting** | Static file counting is requirement; streaming not needed | Keep batch-oriented workflow |
| **New k-mer encodings** | 2-bit encoding is standard; alternatives don't improve perf | Keep u128 encoding; add variable-width packing |
| **Query/prefix/fuzzy micro-optimization** | User bottleneck is counting, not lookup | Leave query path untouched unless regression |
| **Set operations on databases** | Out of scope for performance milestone | Use external tools if needed |

## Feature Dependencies

```
Parallel counting → Memory budgeting (multi-threaded contention)
Memory budgeting → Disk spill (when budget exceeded)
Disk spill → Streaming merge (external sorting)
Variable-width storage → Format version bump (breaking change)
Streaming merge default → Remove in-memory merge path
Lock-free hash → Remove RwLock bottleneck
```

**Critical path for performance milestone:**
1. **Parallel counting** (remove `num_threads = 1`)
2. **Memory budgeting** (admission control, hard cap)
3. **Streaming merge by default** (route through bounded path)
4. **Variable-width k-mer storage** (u64 for k ≤ 32)

These four are interdependent: parallel counting without memory caps is dangerous; streaming merge requires memory budgeting to know when to switch; variable-width storage optimizes both.

## MVP Recommendation for Performance Milestone

**Prioritize (table stakes gaps):**
1. ✅ Parallel counting (remove single-thread restriction) - HIGH gap vs KMC3/Jellyfish2
2. ✅ Memory budgeting + hard caps - HIGH gap; currently unbounded allocation
3. ✅ Streaming merge as default - HIGH gap; in-memory merge OOMs on large inputs
4. ✅ Variable-width k-mer storage - MEDIUM gap; 2x memory waste for k ≤ 32

**Defer (not perf-critical):**
- New query types - out of scope
- Set operations - out of scope
- Distributed counting - out of scope
- New output formats - not perf-blocking
- Count saturation warnings - correctness, not speed

**Dependencies to resolve:**
- Parallel counting requires sharding/partitioning to avoid `RwLock` contention
- Memory budgeting requires estimating k-mer cardinality before allocation
- Streaming merge default requires testing and CI coverage of error paths (currently untested)

## Sources

### Primary Sources (HIGH confidence)
- [KMC 3: counting and manipulating k-mer statistics (Oxford Academic)](https://academic.oup.com/bioinformatics/article-pdf/33/17/2759/49040995/bioinformatics_33_17_2759.pdf) - KMC3 architecture, signature-based partitioning, sort+aggregate pipeline
- [Jellyfish: A fast k-mer counter (University of Maryland)](https://www.cbcb.umd.edu/software/jellyfish/jellyfish-manual-1.1.pdf) - Lock-free hash table design, concurrent counting
- [High-Performance Sorting-Based K-mer Counting (HySortK, SC '24)](https://dl.acm.org/doi/fullHtml/10.1145/3673038.3673072) - 2024 state-of-art: 2x speedup, 30% memory reduction via supermer concept
- [Dataset-adaptive minimizer order reduces memory usage (bioRxiv)](https://www.biorxiv.org/content/10.1101/2021.12.02.470910.full) - 30% memory reduction with adaptive minimizers
- [Compact and evenly distributed k-mer binning (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8428581/) - Signature-based partitioning, FastKmer approach

### Secondary Sources (MEDIUM confidence)
- [The K-mer File Format: standardized compact format (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9477520/) - KFF achieves 3-5x space savings, 2-bit encoding
- [MQF and buffered MQF: quotient filters for k-mers (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7885209/) - Counting Quotient Filter architecture
- [General encoding of canonical k-mers (bioRxiv)](https://www.biorxiv.org/content/10.1101/2023.03.09.531845v3.full) - 2-bit per nucleotide encoding, variable-width representation
- [A benchmark study of k-mer counting methods (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6280066/) - Runtime and memory usage comparison, KMC/Jellyfish performance
- [Space-Efficient Representation of Genomic k-Mer Count Tables (WABI)](https://drops.dagstuhl.de/storage/00lipics/lipics-vol201-wabi2021/LIPIcs.WABI.2021.8.pdf) - Compressed static functions, minimizer bucketing

### Codebase Context (HIGH confidence - direct observation)
- `src/cli/commands/count.rs:121` - `num_threads = 1` hardcoded (single-threaded)
- `src/hash/table.rs` - `RwLock<HashMap<u128, u32>>` concurrent counter
- `src/database/format.rs:752-842` - In-memory merge loads all k-mers unbounded
- `src/database/streaming_merge.rs`, `src/database/prefix_cache_merge.rs` - Streaming merge exists but not default
- `src/kmer/encoding.rs` - u128 encoding for all k (k ≤ 64)
- `src/database/prefix_cache_merge.rs:90-112` - Chinese progress strings (i18n issue)

### Sources with LOW confidence (web search only)
- General external memory merge algorithms (not k-mer specific)
- Rust Rayon partitioning patterns (limited bioinformatics-specific guidance)
