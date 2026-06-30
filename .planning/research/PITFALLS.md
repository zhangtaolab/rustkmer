# Domain Pitfalls

**Domain:** k-mer counting at human-genome scale (performance migration)
**Researched:** 2025-06-30

## Critical Pitfalls

Mistakes that cause rewrites or major issues when scaling k-mer counters to human-genome competitiveness and migrating from simple HashMap counting to partitioned/external-memory structures.

### Pitfall 1: Single Global RwLock HashMap Contention Bottleneck

**What goes wrong:** When migrating from single-threaded counting to parallel counting, wrapping a `HashMap<u128, u32>` in a single `parking_lot::RwLock` creates a severe bottleneck. All reader/writer threads contend for the same cache line and lock, turning parallel hardware into effectively single-threaded execution with overhead.

**Why it happens:** The current codebase already uses this pattern in `src/hash/table.rs` (RwLock-wrapped hashmap). When `num_threads` is increased from 1 to N, every thread serializes on the same lock during k-mer insertion. Lock acquisition/release and cache coherency traffic dominate runtime.

**Consequences:**
- Throughput plateaus or degrades when adding threads (speedup < 1.0×)
- Human-genome datasets (100+ GB) take hours instead of minutes
- Memory bandwidth is wasted on lock traffic rather than actual counting

**Prevention (concrete for Rust codebase):**
1. **Replace single RwLock<HashMap> with sharded HashMaps:**
   ```rust
   // Instead of: RwLock<HashMap<u128, u32>>
   // Use sharded approach:
   struct ShardedCounter {
       shards: Vec<parking_lot::Mutex<HashMap<u128, u32>>>,
       shard_mask: usize,
   }
   impl ShardedCounter {
       fn get_shard(&self, kmer: u128) -> &Mutex<HashMap<u128, u32>> {
           let shard_idx = (kmer as usize) & self.shard_mask;
           &self.shards[shard_idx]
       }
   }
   ```
2. **Shard count = 2× CPU cores or power-of-two (256, 512 for human scale)**
3. **Each shard owns its own HashMap**; threads only lock the shard they need
4. **Alternative:** Use `dashmap` crate (sharded concurrent HashMap) if comfortable with external dependency

**Detection:**
- Flame graphs show `parking_lot::RwLock::write` or `RawRwLock::lock` hotspot
- `perf stat -e cache-misses,cache-references,instructions,cycles` shows high cache miss rate
- Adding threads doesn't improve runtime (runtime constant or increases)

**Which phase:** Parallel-counting phase (migration from `num_threads = 1` to sharded counting)

---

### Pitfall 2: False Sharing in Counter Arrays

**What goes wrong:** Even with sharded HashMaps, if shards are stored in a contiguous `Vec` and accessed simultaneously by different threads, CPU cache line invalidation traffic kills performance. Each thread modifies its own shard, but the shards share cache lines (64 bytes on x86).

**Why it happens:** Rust's `Vec<T>` stores elements contiguously. A `HashMap<u128, u32>` shard is likely > 64 bytes, so multiple threads modifying adjacent shards cause constant cache line bouncing.

**Consequences:**
- Scalability degrades after 4-8 threads despite sharding
- Performance varies wildly based on shard alignment
- Cache contention masks as "mysterious slowdown" in profilers

**Prevention:**
1. **Pad each shard to cache-line size:**
   ```rust
   #[repr(align(64))]
   struct CacheLineAligned<T>(T);
   
   struct ShardedCounter {
       shards: Vec<CacheLineAligned<parking_lot::Mutex<HashMap<u128, u32>>>>,
   }
   ```
2. **Verify alignment:** Use `std::mem::align_of::<CacheLineAligned<_>>()` in tests
3. **Profile with hardware counters:** `perf stat -e cache-misses` before/after padding

**Detection:**
- `perf c2c` (cache-to-cache) tool shows high false sharing rate
- Flamegraph shows time in `pthread_mutex_lock` without actual lock contention
- Performance improves when shards are spaced artificially far apart (diagnostic)

**Which phase:** Parallel-counting phase (shard design)

---

### Pitfall 3: In-Memory Merge OOM on Human-Scale Databases

**What goes wrong:** `merge_databases_inmemory` (`src/database/format.rs:752-842`) loads **all** k-mers from **all** input databases into a single `HashMap` before deduplicating. Human-genome datasets (2.5-3 B distinct k-mers) require 75-120 GB RAM for the HashMap alone; process OOMs on typical 16-64 GB machines.

**Why it happens:** The in-memory merge path was written before the streaming merge infrastructure and has no memory-budget admission control. It optimizes for small merges and assumes "merge happens in RAM" without checking feasibility.

**Consequences:**
- Large merge jobs crash with `memory allocation failed`
- CI/small-scale tests pass, production jobs fail
- No graceful degradation; process aborts mid-operation

**Prevention:**
1. **Route all merges through streaming path by default:**
   ```rust
   // In merge command:
   if merge_strategy == Auto {
       if estimated_memory > available_memory * 0.7 {
           merge_strategy = Streaming;
       } else {
           merge_strategy = InMemory;
       }
   }
   ```
2. **Add admission control before allocation:**
   ```rust
   fn estimate_merge_memory(inputs: &[RKDatabase]) -> usize {
       inputs.iter()
           .map(|db| db.header().kmer_count * (20 + 8))  // entry + hashmap overhead
           .sum::<usize>()
   }
   ```
3. **Make in-memory merge explicit flag only:** `--merge-strategy memory` for small inputs

**Detection:**
- Top shows RSS growing linearly with input size, no plateau
- `dmesg` shows `Out of memory: Killed process`
- Memory monitor (if instrumented) shows > 90% RAM during merge

**Which phase:** Merge-defaulting phase (switch to streaming-by-default)

---

### Pitfall 4: Streaming Merge Temp-File Exhaustion and No Cleanup on Failure

**What goes wrong:** The streaming merge (`src/database/prefix_cache_merge.rs`) writes 256+ temporary shard files to disk but has incomplete cleanup on partial failure. If merge crashes midway (I/O error, disk full, signal), temp files remain and fill the disk. Subsequent runs hit "No space left on device."

**Why it happens:** Temp cleanup at `prefix_cache_merge.rs:309-313` only runs on **success** path. Error paths (early returns, `?` propagation, panics) skip cleanup. No RAII guard ensures cleanup.

**Consequences:**
- Disk fills with orphaned `.tmp` shard files
- Retry attempts fail immediately with ENOSPC
- Manual cleanup required across entire temp directory

**Prevention:**
1. **RAII temp file guard:**
   ```rust
   struct TempFileManager {
       files: Vec<PathBuf>,
       temp_dir: PathBuf,
   }
   impl Drop for TempFileManager {
       fn drop(&mut self) {
           for path in &self.files {
               let _ = std::fs::remove_file(path);  // Best-effort cleanup
           }
           let _ = std::fs::remove_dir(&self.temp_dir);
       }
   }
   ```
2. **Register all temp files with guard on creation**
3. **Test error paths:** Inject failures in tests (disk full simulation, signal interruption)

**Detection:**
- `df -h` shows temp directory at 100% use
- `ls -la /tmp/kmer_*` shows many `.tmp` files
- CI fails with "No space left on device" after retries

**Which phase:** Merge-defaulting phase (streaming merge hardening)

---

### Pitfall 5: Canonicalization Regressions When Optimizing Encoding

**What goes wrong:** When optimizing k-mer storage from `u128` to packed `u64` for k ≤ 32, canonicalization logic (`min(kmer, revcomp(kmer))`) must be updated to work with packed representation. Bugs here silently produce wrong counts (k-mer and its reverse complement counted separately).

**Why it happens:** Canonicalization is currently implemented on `u128` values in `src/kmer/encoding.rs`. Packed `u64` representation changes the bit layout; reverse complement calculation differs. If encoding changes but canonicalization doesn't, counts diverge.

**Consequences:**
- Output databases have 2× expected distinct k-mers
- Query results wrong (no canonical deduplication)
- Silent correctness error; counts look plausible but are wrong

**Prevention:**
1. **Property test canonicalization invariant:**
   ```rust
   #[proptest]
   fn test_canonical_packed_equivalence(#[strategy(any_kmer())] kmer: u128, k: u8) {
       if k <= 32 {
           let packed = encode_packed_u64(kmer, k);
           let unpacked = decode_packed_u64(packed, k);
           let canonical_u128 = canonicalize(kmer, k);
           let canonical_packed = canonicalize_packed(packed, k);
           prop_assert_eq!(canonical_packed, pack_u64(canonical_u128, k));
       }
   }
   ```
2. **Round-trip test:** encode → canonicalize → decode → canonicalize should be idempotent
3. **Cross-validate:** Run same dataset with both `u128` and `u64` paths; assert distinct count matches

**Detection:**
- `distinct_kmer_count(db_new) != distinct_kmer_count(db_old)` for same input
- Downstream analysis (species abundance, SNP detection) produces inconsistent results
- Property tests fail on edge cases (palindromic k-mers, N-containing)

**Which phase:** Storage-optimization phase (u128 → u64 packing)

---

### Pitfall 6: Binary Format Version Mismatch Breaking Backward Compatibility

**What goes wrong:** Adding a new `.rkdb` format version (e.g., for packed u64 k-mers) without proper version handling causes old files to be unreadable or misread. The current format has a version field (`src/database/format.rs` header), but migration lacks testing.

**Why it happens:** Format bumps touch serialization (`to_file_path`), deserialization (`from_file_path`), and the Python API. If version check is incomplete, code reads new format as old (wrong counts) or rejects old format unnecessarily.

**Consequences:**
- Old `.rkdb` files rejected with "unsupported version" (regression)
- New files read as garbage (wrong counts, crashes)
- Users lose access to existing databases

**Prevention:**
1. **Version enum with explicit migration:**
   ```rust
   enum DatabaseVersion {
       V2 = 2,  // Current u128 format
       V3 = 3,  // Future packed format
   }
   fn load_with_migration(path: &Path) -> Result<RKDatabase> {
       match read_version(path)? {
           DatabaseVersion::V2 => migrate_v2_to_v3(path),
           DatabaseVersion::V3 => load_v3(path),
       }
   }
   ```
2. **Add format compatibility tests:** Load v2 database with v3 code, assert counts unchanged
3. **Write `upgrade` CLI tool:** Explicit format migration command
4. **Document version matrix:** Which features require which version

**Detection:**
- `from_file_path` returns `Err(UnsupportedVersion)` on existing files
- Database round-trip test fails (write → read → assert counts)
- Users report "database broke after update"

**Which phase:** Format-migration phase (if format bump is required for performance)

---

### Pitfall 7: Temp Disk I/O Bottleneck Outweighing Parallel Counting Gains

**What goes wrong:** Streaming merge writes 256+ shard files to disk in parallel. On HDD or slow I/O, disk bandwidth becomes the bottleneck, and parallel counting speedups are erased by slow merge. SSD vs HDD performance difference is 10-100×.

**Why it happens:** Current merge doesn't throttle I/O parallelism. 256 threads writing simultaneously can saturate even SSD bandwidth. On HDD, random write access patterns cause seek thrashing.

**Consequences:**
- Overall pipeline (count + merge) shows no improvement despite faster counting
- Merge dominates runtime (80%+ of total time)
- Performance varies wildly across machines (SSD laptop vs HDD server)

**Prevention:**
1. **Detect storage type:** `sys_info::disk_type(temp_dir)` or heuristic (IOPS benchmark)
2. **Adaptive parallelism:**
   ```rust
   let io_parallelism = if is_ssd(temp_dir) {
       num_cpus::get()  // Full parallelism
   } else {
       2  // Limit concurrent writers on HDD
   };
   ```
3. **Batch writes:** Accumulate to in-memory buffer, flush per-shard sequentially on HDD
4. **Expose tuning flag:** `--merge-io-threads N`

**Detection:**
- `iostat -x 1` shows 100% disk utilization during merge
- Flamegraph shows time in `std::fs::write` / `File::sync_all`
- Merge time > counting time (unusual for human-scale data)

**Which phase:** Merge-defaulting phase (I/O optimization)

---

### Pitfall 8: Benchmarking Methodology Errors Produce False Wins

**What goes wrong:** When benchmarking against KMC/Jellyfish, common mistakes produce misleading "victory" claims: benchmarking only counting (not full pipeline), counting I/O but not counting decompression, using cached input files, or comparing against reference tool with mismatched settings.

**Why it happens:** K-mer counting benchmarks are complex. Different tools have different default behaviors (canonicalization, quality filtering, k-mer size limits). Fair comparison requires identical input, output validation, and time measurement boundaries.

**Consequences:**
- Published "benchmarks" show unrealistic speedup
- Reference tool appears slower due to unfair test
- Optimizations target wrong bottleneck (I/O vs CPU vs memory)

**Prevention (benchmark harness design):**
1. **Cold-cache runs:** Clear page cache between runs (`sync; echo 3 > /proc/sys/vm/drop_caches`)
2. **Include decompression:** Time from compressed FASTQ to final `.rkdb`, not just in-memory counting
3. **Validate output:** Assert `rustkmer db | query` vs `KMC db | query` produce identical k-mer counts
4. **Match reference settings:**
   - Same k-mer size (k)
   - Same canonicalization (on/off)
   - Same quality filtering (if any)
   - Same output format (both binary or both text)
5. **Measure full pipeline:** Read FASTQ → Count → Merge → Query
6. **Document environment:** CPU, RAM, SSD/HDD, OS, Rust version

**Detection:**
- Benchmarked time is < 10% of real-world runtime
- Output validation shows count mismatches
- Re-running benchmark shows 2× variance (cache effects)
- Reference tool performs differently when invoked directly vs via benchmark harness

**Which phase:** Benchmark-harness phase (fair comparison methodology)

---

### Pitfall 9: u32 Count Saturation on High-Coverage Human WGS

**What goes wrong:** `KmerEntry.count` is `u32` (max ~4.29B). Deep-coverage human WGS (> 60× coverage) or merge of multiple samples can exceed this limit for common k-mers. Current merge saturates silently (`count.saturating_add(other.count)`), losing precision without warning.

**Why it happens:** The codebase uses `u32` for storage efficiency. Human-genome k-mer distributions are highly skewed; some repetitive k-mers appear billions of times. Saturation is not detected or reported.

**Consequences:**
- Common k-mer counts capped at `u32::MAX`
- Downstream abundance estimates wrong (species proportions, coverage calculations)
- No warning; results look plausible but are truncated

**Prevention:**
1. **Detect saturation and emit warning:**
   ```rust
   fn merge_counts(a: u32, b: u32) -> u32 {
       let merged = a.saturating_add(b);
       if merged == u32::MAX && (a + b) > u32::MAX {
           log::warn!("K-mer count saturated at u32::MAX; consider u64 counts");
       }
       merged
   }
   ```
2. **Add statistics:** Track how many k-mers saturated; report in stats output
3. **Long-term:** Migrate count field to `u64` (requires format bump, see Pitfall 6)

**Detection:**
- Stats show many k-mers at exactly `4,294,967,295` (unlikely to be real)
- Total read count ÷ distinct k-mers > 10⁹ (implies some k-mers exceed u32)
- Coverage calculations produce impossible values (> 1000× for human genome)

**Which phase:** Merge-defaulting phase (saturation detection)

---

### Pitfall 10: Streaming Merge Sharding Strategy Produces Imbalanced Buckets

**What goes wrong:** Current streaming merge uses 4-prefix sharding (256 buckets). For non-uniform k-mer distributions (human genome has highly skewed k-mer frequencies), some buckets become much larger than others. The largest bucket dominates merge time and memory.

**Why it happens:** 4-prefix (first 4 bases) doesn't evenly distribute real genomic k-mers. AT-rich and GC-rich regions produce uneven prefix frequencies. A single bucket can contain 10× more k-mers than average.

**Consequences:**
- Merge time is dominated by slowest bucket (poor parallelism)
- Memory usage spikes during largest bucket merge
- Some shards OOM even when total memory is sufficient

**Prevention:**
1. **Adaptive prefix length:** Use 5- or 6-prefix for very large datasets
2. **Minimizer-based sharding (like KMC):** Choose minimum m-mer within k-mer as shard key
3. **Profile bucket distribution:** Log top 10 bucket sizes; warn if > 5× average
4. **Load-balance strategy:** Split large buckets into sub-shards

**Detection:**
- During merge, progress bar shows one shard at 1% while others at 90%
- Shard files vary widely in size (some 1 GB, others 100 MB)
- `du -sh prefix_cache_*` shows heavy-tailed distribution

**Which phase:** Merge-defaulting phase (sharding strategy)

---

## Moderate Pitfalls

### Pitfall 11: Gzip Decompression Single-Threaded Bottleneck

**What goes wrong:** FASTQ input is gzipped (`CRR1936095_r1.fq.gz`). Default `flate2` decompression is single-threaded. Even with parallel counting, decompresses at ~200 MB/s per core. Multi-core CPU sits idle waiting for input.

**Why it happens:** `flate2::read::GzDecoder` is single-threaded by default. Input reading blocks on one thread while counting threads wait.

**Consequences:**
- CPU utilization < 30% during counting
- Throughput limited by decompression speed, not counting
- Multi-threaded counting shows diminishing returns

**Prevention:**
1. **Use multi-threaded gzip:** `flate2` with `rust_backend` or external `pigz` for preprocessing
2. **Pre-decompress to pipe:** `pigz -dc input.fq.gz | rustkmer count -`
3. **Or use uncompressed FASTQ for benchmarking:** Eliminates decompression variable

**Detection:**
- Flamegraph shows `flate2` functions in hot path
- `top` shows single core at 100%, others idle
- Uncompressed input runs 3-5× faster

**Which phase:** Parallel-counting phase (I/O optimization)

---

### Pitfall 12: Memory-Mapped Database Writes Cause Page Fault Storms

**What goes wrong:** When using memory-mapped files for database output, every page fault triggers disk I/O. Writing `.rkdb` via mmap causes random write pattern and page fault storms, especially on HDD.

**Why it happens:** Codebase has mmap support (`src/memory/efficiency.rs`, `src/io/mmap.rs`) but uses it for writes. Mmap is optimized for read-heavy workloads, not write-heavy sequential output.

**Consequences:**
- Database writing is slow (random I/O instead of sequential)
- HDD performance degrades to < 10 MB/s due to seeks
- SSD wear increases from random writes

**Prevention:**
1. **Use buffered `File::write` for output:** Sequential writes are faster
2. **Reserve mmap for read-only queries:** Database reads, not writes
3. **Batch writes:** Accumulate 64 KB+ buffers, flush sequentially

**Detection:**
- `iostat` shows high IOPS but low throughput during database write
- `mmap` writes slower than `write` benchmarked directly
- HDD audible seeks during database generation

**Which phase:** Storage-optimization phase (write path redesign)

---

### Pitfall 13: Quality Filtering Inconsistency Between Tools

**What goes wrong:** rustkmer currently doesn't filter low-quality bases. KMC and Jellyfish offer optional quality filtering (ignore bases with Q < score). Benchmark comparisons without matching this setting produce different k-mer sets.

**Why it happens:** Quality filtering requires per-base quality scores from FASTQ. Current FASTQ parser (`src/io/fastq.rs`) may read quality scores but doesn't filter. Missing this feature makes counts incomparable with reference tools.

**Consequences:**
- rustkmer counts more k-mers than KMC (includes low-quality k-mers)
- Benchmark appears unfavorable (different input k-mer set)
- Downstream analysis has higher error rate

**Prevention:**
1. **Match reference tool behavior:** Implement `--min-quality` flag
2. **Default to no filtering for raw counting:** Match KMC default behavior
3. **Document flag:** Explicitly note quality filtering in benchmark methodology

**Detection:**
- `kmer_count(rustkmer) > kmer_count(KMC)` for same input
- Quality-aware reference tools have lower counts
- Benchmarked against tool with filtering disabled

**Which phase:** Benchmark-harness phase (feature parity)

---

### Pitfall 14: Thread Pool Starvation in Nested Parallelism

**What goes wrong:** Rayon global thread pool defaults to `num_cpus`. If user runs `rustkmer count --threads 32` on 32-core machine but Rayon also uses 32 threads internally, thread oversubscription causes context switching overhead.

**Why it happens:** Rayon uses global thread pool. Explicit thread management (custom thread count) plus Rayon's internal parallelism can oversubscribe.

**Consequences:**
- Context switching dominates CPU time
- Performance degrades with > `num_cpus` threads
- OS scheduler thrashes

**Prevention:**
1. **Partition thread budget:** `rayon_threads = max_threads / 2`, manual threads = remainder
2. **Or disable Rayon internal parallelism:** `RAYON_NUM_THREADS=1`
3. **Document thread model:** Clarify how `--threads` interacts with parallelism

**Detection:**
- `perf top` shows time in `schedule` / `context_switch`
- `rustkmer --threads 64` slower than `--threads 32`
- `top` shows many more threads than CPU cores

**Which phase:** Parallel-counting phase (thread pool configuration)

---

## Minor Pitfalls

### Pitfall 15: L0 Cache Misses in K-mer Encoding Hot Path

**What goes wrong:** K-mer encoding (`encode_kmer_u128` in `src/kmer/encoding.rs`) is called per-read, per-base. Inefficient encoding (e.g., multiple branches, per-base string conversion) causes L1 cache misses and branch mispredictions.

**Why it happens:** Encoding happens in tight loop. Branching on character ('A', 'C', 'G', 'T', 'N') per base causes branch mispredictions.

**Consequences:**
- 5-10% overhead in counting runtime
- Profile shows encoding as significant hotspot
- Impossible to eliminate but worth optimizing

**Prevention:**
1. **Branchless encoding:** Use lookup table `const ENCODE: [u8; 256]` indexed by byte
2. **SIMD encoding:** Process 16 bases per vector instruction
3. **Profile first:** Only optimize if encoding is > 5% of runtime

**Detection:**
- Flamegraph shows `encode_kmer_u128` in top 10 functions
- `perf stat -e branches,branch-misses` shows high miss rate

**Which phase:** Parallel-counting phase (micro-optimization, if profiling shows need)

---

### Pitfall 16: Python API GIL Contention in Query Workloads

**What goes wrong:** When users query `pyrustkmer` from Python in parallel (multiprocessing), each process loads the full `.rkdb` into memory. The GIL isn't the bottleneck—memory is. But single-process multi-threaded queries contend on Python GIL.

**Why it happens:** PyO3 releases GIL during Rust execution, but re-acquires for Python callbacks. Query-heavy workloads spend time in Python wrapper, not Rust core.

**Consequences:**
- Parallel queries don't scale in single Python process
- Users must use multiprocessing (high memory overhead)
- Confusion about "parallel" Python API

**Prevention:**
1. **Document multiprocessing pattern:** `multiprocessing.Pool` not `threading`
2. **Ensure GIL release:** All PyO3 query methods use `#[pyo3(gil)] = false` correctly
3. **Consider read-only shared memory:** mmap the database, share across processes

**Detection:**
- Python query benchmark shows no speedup beyond 1 thread
- `top` shows single Python core at 100%

**Which phase:** Python API phase (GIL optimization, if query performance is priority)

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| **Parallel-counting** | Single RwLock contention (Pitfall 1), false sharing (Pitfall 2) | Sharded HashMaps with cache-line padding; profile with perf |
| **Merge-defaulting** | In-memory OOM (Pitfall 3), temp file exhaustion (Pitfall 4), bucket imbalance (Pitfall 10) | Route to streaming by default; RAII temp guards; adaptive sharding |
| **Benchmark-harness** | Unfair comparison (Pitfall 8), quality filtering mismatch (Pitfall 13) | Cold-cache runs; validate output; match reference settings |
| **Storage-optimization** | Canonicalization regressions (Pitfall 5), format version breakage (Pitfall 6) | Property tests; version migration code; compatibility test matrix |
| **I/O-optimization** | Disk bottleneck (Pitfall 7), gzip decompression (Pitfall 11), mmap writes (Pitfall 12) | Detect storage type; use pigz or uncompressed input; buffered writes |

## Sources

- [KMC GitHub Repository](https://github.com/refresh-bio/KMC) - External memory, minimizer partitioning architecture
- [Jellyfish GitHub Repository](https://github.com/gmarcais/jellyfish) - Lock-free hash table design
- [DSK: k-mer counting with very low memory usage](https://academic.oup.com/bioinformatics/article/29/5/652/253092) - Streaming algorithm, partitioned files
- [Abakus: Accelerating k-mer Counting with Storage Technology](https://dl.acm.org/doi/full/10.1145/3632952) - Minimizer partitioning, storage optimization
- [HySortK: High-Performance Sorting-Based k-mer Counting](https://arxiv.org/html/2407.07718v1) - Memory pressure mitigation
- [A benchmark study of k-mer counting methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC6280066/) - Benchmark methodology
- [DashMap - Sharded Concurrent HashMap](https://github.com/xacrimon/dashmap) - Rust sharding patterns
- [Concurrent Hash Map Designs](https://bluuewhale.github.io/posts/concurrent-hashmap-designs/) - Sharding vs locking strategies
- [False sharing in Rust](https://www.reddit.com/r/rust/comments/17z7eha/false_sharing_can_happen_to_you_too/) - Cache line padding
- [Optimizing High Performance Distributed Memory Parallel Hash Tables](https://www.intel.com/content/dam/www/public/us/en/ai/documents/Optimizing-High-Performance-Distributed-Memory-Parallel-Hash-Tables-for-DNA-kmer-Counting.pdf) - Parallel hash table optimization
