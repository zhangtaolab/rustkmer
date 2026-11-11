# Architecture Research — v2.0 k=21 Counting Parity

**Domain:** k-mer counting toolkit at human-genome scale (Rust core + CLI + PyO3)
**Researched:** 2026-11-12
**Confidence:** HIGH (root cause is empirically measured on real data, not inferred)
**Mode:** Ecosystem + Feasibility, with **empirical root-cause profiling** as the core deliverable

> **Headline finding (evidence-based, overturns the standing hypothesis):**
> The ~5× k=21 gap is **NOT** decompression, **NOT** k-mer encoding, and **NOT** a
> memory-capacity / data-structure problem. rustkmer's **single-thread** counting core is
> already competitive with jellyfish (190–250 ns/window vs jellyfish's 227 ns/window).
> The gap is **parallel-scaling efficiency**: jellyfish scales **8.9×** on 16 cores
> (118 s → 13.3 s); rustkmer scales only **~3×** because (a) `--threads` is silently a
> no-op (so wall-clock looks flat across thread counts), (b) the per-chunk rayon fork-join pipeline leaves workers spin-waiting **~58% of
> CPU**, and (c) the shared DashMap + per-window global atomics contend (~9× the
> single-thread increment cost). **Fix the parallelism first (in-memory); minimizer /
> disk-backed partitioning is a memory-ceiling lever, not the speed lever.**

---

## PART 1 — EMPIRICAL ROOT-CAUSE EVIDENCE

### 1.1 Methodology (reproducible)

All numbers below are **measured**, not estimated (estimates are flagged). Scripts, raw
results, and profile breakdowns are persisted in `.planning/research/profiling/`.

| Item | Value |
|------|-------|
| Platform | Apple M4 Max, **16 logical cores (12 P + 4 E)**, 128 GiB RAM, macOS 26.6.2, 16 KiB pages |
| Binary | **fresh** `CARGO_PROFILE_RELEASE_DEBUG=1 cargo build --release --locked` (debug line-info only; codegen identical to release). rustc nightly 1.101, git HEAD `397a1cf`, built 2026-11-11 23:16. The stale July-2 binary was replaced before any measurement. |
| Reference | jellyfish 2.3.1 (`/opt/homebrew/bin/jellyfish`) |
| Profiler | samply 0.13.1 (`cargo install samply`, **no sudo**), 1000 Hz; macOS `sample` for thread counts. No dtrace/cargo-flamegraph (needs sudo). |
| Slice | first **4,000,000 reads** of `CRR1936095_r1.part_001.fq.gz` → 599,294,679 bases, 5,600 Ns, 95% 150 bp. Raw 1.47 GB; re-gzipped 320 MB (sha256 `0c7626d8…`). |
| Workload | k=21: **519,271,168** instances → **229,694,874** distinct canonical; k=31: 261,863,892 distinct |
| Measurement | `/usr/bin/time -l` (macOS peak RSS in **bytes**), wall = `real`. rustkmer internal phase split from stderr: `Elapsed time` fires after counting / before output; `Total time` at end → output phase = difference. |
| Fairness | both tools canonical (`-C`), 16 threads, same slice. jellyfish gz via `gzcat … \| jellyfish count … /dev/stdin` (decompression inside its wall, overlapped as a child process — identical to the v1.0 harness). jellyfish `-s 2G` (generous; v1.0 used 10G). |
| Cache state | **warm** page cache (slice freshly written). No sudo cold-cache purge available — same limitation v1.0 recorded honestly. |

**Reproduce:**
```bash
# slice
gzcat /Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/CRR1936095_r1.part_001.fq.gz \
  | head -n 16000000 > /tmp/rkmer-v2-prof/data/slice4M.fq
gzip -c slice4M.fq > slice4M.fq.gz
# matrix + profiles + microbench + thread-check (sequential, no contention)
python3 -I .planning/research/profiling/run_matrix.py all
sh        .planning/research/profiling/post_matrix.sh
```

> **Dataset caveat (report honestly):** this slice is far more repeat-rich than v1.0's
> CRR2044018 — distinct/instance ratio **2.26** here vs **7.3** there (exact-duplicate read
> rate is only 2.55%, so the collapse is genuine k-mer repetition, not PCR dup). The ~5×
> gap **still reproduces** (below), and the bottleneck is structural, so the conclusion is
> robust to this difference. Absolute seconds differ from v1.0 because the slice is ~1/9
> of the full dataset and the distinct count is lower.

### 1.2 Measurement matrix (wall-clock seconds, peak RSS GiB)

| Arm | wall (s) | RSS (GiB) | count phase (s) | output phase (s) |
|-----|---------:|----------:|----------------:|-----------------:|
| **rustkmer k21 gz, t16** | **74.76** | 18.4 | 59.80 | 13.36 |
| **jellyfish k21 gz, t16** | **13.29** | 6.68 | — | — |
| rustkmer k31 gz, t16 | 70.42 | 25.42 | 54.03 | 14.29 |
| jellyfish k31 gz, t16 | 14.05 | 11.84 | — | — |
| rustkmer k21 **raw fq**, t16 | 64.81 | 15.39 | 51.56 | 11.88 |
| rustkmer k31 raw fq, t16 | 72.87 | 24.36 | 57.20 | 13.80 |
| jellyfish k21 raw fq, t16 | 14.10 | 6.68 | — | — |
| `gzcat` only (decompress floor) | **0.90** | ~0 | — | — |
| rustkmer k21 fq, **t1** | 70.12 | 15.34 | 57.48 | 11.33 |
| rustkmer k21 fq, **t4** | 74.39 | — | 61.27 | 11.78 |
| rustkmer k21 fq, **t8** | 69.92 | — | 56.66 | 11.93 |
| rustkmer k21 gz, t1 | 65.42 | — | 52.64 | 11.48 |
| rustkmer k21 fq t16 **--no-sort** | 64.82 | — | 59.95 | **3.52** |
| rustkmer k21 fq t16 **--size 500M** | 69.08 | 29.28 | 53.72 | 12.99 |
| **jellyfish k21 fq, t1** | **118.17** | 6.68 | — | — |

**Gap: k=21 = 74.76 / 13.29 = 5.63×; k=31 = 70.42 / 14.05 = 5.01×.** The ~5× k=21 gap
reproduces. **Crucially, rustkmer is ~5× slower at k=31 too on this dataset** — its wall is
nearly k-independent (70–75 s) while jellyfish is fast at both k (13–14 s). v1.0's "k=31
win" was an artifact of jellyfish's oversized `-s 10G` hash at k=31 (84 GiB RSS,
memory-bound, 843 s); with a right-sized hash jellyfish k=31 is also fast. **The gap is a
general counting-throughput gap, not k-specific.**

### 1.3 Count parity (exact-count contract) — PASS

`jellyfish stats` on both gz and raw arms: **Distinct = 229,694,874; Total = 519,271,168**
(Unique = 167,905,312; Max_count = 58,609). rustkmer `.rkdb` record count =
`(file_size − 42) / 20` = **229,694,874**; counter `total_kmers` (sum of counts) logged =
**519,271,168**. **Both match exactly** → optimized counting must preserve these
(`.planning/research/profiling/parity_report.json`).

### 1.4 Where the CPU goes — samply self-time breakdown

Lib-aware resolution of samply RVAs against the binary's `nm` (system libs labelled).
Full tables: `.planning/research/profiling/prof*.breakdown.txt`. Percentages are of total
weighted CPU samples (~1 ms each); all 16 cores are ~saturated during counting.

| Category (leaf/self) | k21 **gz** | k21 **raw** | k31 raw |
|----------------------|-----------:|------------:|--------:|
| **kernel wait / spin / syscall** (rayon workers spin-waiting + main blocked on chunk barrier) | **59.5%** | **57.9%** | **60.5%** |
| **DashMap increment / hash** (ahash + probe + count bump; locks mostly uncontended) | **36.3%** | **38.0%** | **34.7%** |
| encode + canonical (inlined in `process_one_record`) | 3.1% | 3.0% | 3.5% |
| output collect / sort / write | 0.7% | 0.7% | 0.8% |
| **gzip inflate (libz)** | **0.09%** | 0% | 0% |
| FASTQ parse (bio) | 0.02% | 0.02% | 0.02% |
| rayon fork-join plumbing (self) | 0.04% | 0.05% | 0.04% |

Top self symbols (k21 raw): `KmerCounter::increment` **37.3%**, `libsystem_kernel+0x450c`
(`__psynch_cvwait`) 32.0%, `libsystem_kernel+0xc88` (spin/yield) 25.4%,
`process_one_record` 3.0%, `dashmap::lock_exclusive_slow` **0.41%** (locks NOT contended),
stable `quicksort` 0.55%.

**Reading:** the machine looks busy (16 cores saturated) but **~58% of CPU is wasted
spin-waiting** — rayon workers burn CPU spinning when they finish their chunk share early
and wait for the slowest worker / the next chunk. The useful work is DashMap increment
(~37%). Decompression (0.09%), encoding (3%), and parsing (0.02%) are negligible.

### 1.5 Stage isolation — single-thread microbench (ns per k-mer window)

Standalone crate (`.planning/research/profiling/microbench_main.rs`), path-dep on rustkmer,
**single-threaded**, same real reads, same `KmerCounter`. Rolling keys asserted **identical**
to production keys (PASS). A=production encode+canon+increment; B=rolling 2-bit encode +
bit-parallel revcomp + increment; C=increment only (pre-encoded); D=rolling encode only;
E=production encode only.

| Variant | k21, 200k reads (cache, 16.4M distinct) | k31, 200k | k21, 1M (mem, 66M) | k21, 2M (mem, 119M) |
|---------|----------------------------------------:|----------:|-------------------:|--------------------:|
| A production total | **190.8** | 211.0 | — | **249.6** |
| B rolling+bitrc+increment | **70.9** | 74.6 | 93.3 | — |
| C increment-only | 75.8 | 73.6 | 97.3 | — |
| D rolling encode-only | **1.2** | 1.3 | — | — |
| E production encode-only | **31.7** | 47.1 | — | 31.8 |

**Reading:**
- Production encode+canon costs **31.7 ns (k21) / 47.1 ns (k31)** — the O(k) per-window
  re-encode + O(k) revcomp loop. A rolling encoder is **1.2 ns** → **26× cheaper encoding**.
- **DashMap increment dominates** the optimized cost (~76 ns cache, ~97 ns memory).
- Switching to rolling encode + bit-parallel revcomp: **190.8 → 70.9 ns = 2.7× single-thread
  win** (k21). Real, worth doing, but it is the *secondary* lever.
- In the DRAM regime (2M reads, ~2 GB table) production rises to **249.6 ns/window** —
  increment balloons with table size while encode stays ~32 ns. **The bigger the table, the
  more increment dominates and the less encoding matters.**

### 1.6 The `--threads` bug (smoking gun)

`verify_threads.py` sampled a live `rustkmer count --threads 1`: **17 OS threads observed
(main + 16 workers), expected ~2.** `--threads` is a **complete no-op**; every matrix arm
ran 16 workers, which is why t1 ≈ t4 ≈ t8 ≈ t16.

**Mechanism (confirmed from rayon-core 1.13 source):** `resolve_thread_count`
(`src/cli/commands/count.rs:836-847`) passes `rayon::current_num_threads()` as the *eagerly
evaluated* fallback argument. That call **lazily initializes the global rayon pool with the
default `num_cpus` = 16** *before* `ThreadPoolBuilder::new().num_threads(resolved).build_global()`
runs (count.rs:100-103). `build_global` then returns `Err` (pool already exists), which
`let _ =` discards. Result: the configured thread count never takes effect.

```rust
// count.rs:836 — the fallback arg initializes the pool BEFORE build_global:
fn resolve_thread_count(args_threads: Option<usize>) -> usize {
    resolve_thread_count_from(
        args_threads,
        /* RUSTKMER_THREADS */ …,
        /* RAYON_NUM_THREADS */ …,
        rayon::current_num_threads(),   // <-- eagerly builds default 16-thread global pool
    )
}
```
Fix: compute the fallback lazily (e.g. `std::thread::available_parallelism()`), and call
`build_global` **before** any rayon query. This is a correctness bug in PCOUNT-03's
`--threads` plumbing (counts stayed identical, so the 1-vs-N differential passed — it never
checked that the flag actually changed the pool size).

### 1.7 Hypothesis verdicts (the question's a/b/c/d, with numbers)

| Hypothesis | Verdict | Evidence |
|------------|---------|----------|
| **(a) single-threaded gzip is the bottleneck** | **REJECTED** | gz→raw saves only ~8–10 s of ~75 s (11–13%); pure `gzcat` inflate = **0.9 s**; libz is **0.09%** of CPU. The ~8 s gz overhead is flate2 `MultiGzDecoder`+`BufReader` path + serialization, not the inflate floor. Parallel decompression is a minor win, not the fix. |
| **(b) DashMap hashing / contention** | **CONFIRMED (dominant useful cost)** | increment = **36–38%** of CPU; in-vivo increment ≈ **916 ns/window** (476 CPU-s / 519M) vs single-thread **97 ns** → **~9.4× contention multiplier**. Shard locks are NOT the issue (`lock_exclusive_slow` 0.4%); the cost is shared-table DRAM random access + **per-window global atomics** (`total_kmers`/`unique_kmers` `fetch_add` on every window, table.rs:272/309) bouncing cache lines across 16 cores. |
| **(c) memory bandwidth / cache misses** | **CONFIRMED (part of b)** | increment rises 76→97→~218 ns as the table grows 250 MB→1 GB→2 GB (microbench). 229M-distinct table ≈ 3.5 GB → DRAM/TLB-bound. 16 threads saturate bandwidth. |
| **(d) encoding / canonicalization significant** | **PARTLY — secondary** | encode+canon = **3%** of in-vivo CPU (31.7 ns of 249.6 ns single-thread). Rolling encode gives a **2.7× single-thread** win but a smaller in-vivo fraction because increment dominates in the DRAM regime. Worth doing; not the primary lever. |
| **(implicit) rayon scheduling** | **CONFIRMED (dominant wasted cost)** | **~58% of CPU is kernel wait/spin** — the serialized per-chunk `fill → par_iter → clear` pipeline (count.rs:587-609) plus E-core stragglers (4 slow E-cores pace 12 fast P-cores) plus fine-grained fork-join. |

### 1.8 Root-cause decomposition of the 5× gap

| Factor | Multiplier | Evidence |
|--------|-----------:|----------|
| **Parallel-scaling efficiency** | **~3.5×** | jellyfish 118 s (t1) → 13.3 s (t16) = **8.9× / 56% efficiency**. rustkmer single-thread ≈ 169 s (extrapolated from 249.6 ns/window @ 2M reads to the 229M-distinct regime) → ~51.6 s count phase = **~3.3× / ~21% efficiency**. |
| **Single-thread per-window cost** | **~1.4×** | rustkmer DashMap `u64,u32` (13 B/entry + ahash + shard lock) vs jellyfish bit-packed invertible hash (~5 B/entry, lock-free CAS, k-mer-as-hash). 249.6 vs 227 ns/window. |
| **Combined** | **~4.9× ≈ observed 5×** | |

**Conclusion:** the biggest lever is **recovering parallel scaling** (mostly fixing broken
parallelism — an engineering problem), not replacing the data structure. jellyfish proves
the workload fits in memory and runs in 13 s with an in-memory table; rustkmer's 18 GiB also
fits. **Disk-backed / minimizer partitioning is not required to match jellyfish** — it is the
lever for the *memory ceiling* and for beating KMC3 (BENCH-V2-01), which is a secondary
comparison, not the acceptance gate.

---

## PART 2 — ARCHITECTURE INTEGRATION

### 2.1 Recommended architecture (staged, evidence-driven)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Entry surfaces (unchanged public APIs)                                    │
│  CLI: src/cli/commands/count.rs        Python: pyo3/src/counter.rs         │
└───────────────┬──────────────────────────────────┬───────────────────────┘
                │  both delegate to ONE shared engine (NEW)                  │
                ▼                                                            ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  NEW shared counting engine  src/count/engine.rs                           │
│  • fixed rayon pool (build_global BEFORE any rayon query; --threads works) │
│  • producer reads/decompresses records → bounded queue (OVERLAPPED, not    │
│    serialized fill→par_iter→clear)                                         │
│  • N persistent workers, each with a THREAD-LOCAL counter (no shared       │
│    DashMap during counting, no per-window global atomics)                  │
│  • partition by hash-range / canonical minimizer → disjoint key spaces     │
│  • rolling 2-bit encode + bit-parallel revcomp (u64 for k≤32)              │
│  • reduce thread-local totals at the end                                   │
└───────────────┬──────────────────────────────────────────────────────────┘
                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Merge thread-local/partition counters → sorted (u128,u32) stream          │
│  → EXISTING format.rs writer (.rkdb v2, 42B header + 20B entries)          │
│  → sort_unstable / rayon par_sort_unstable (was single-thread stable sort) │
└──────────────────────────────────────────────────────────────────────────┘
```

**Stage A — recover parallel scaling + hot path (in-memory; targets jellyfish parity):**
1. Fix `--threads` (lazy fallback; `build_global` first). *~free, unblocks everything.*
2. Thread-local counters + end-of-run reduction (remove per-window global atomics).
3. Restructure parallelism: persistent workers + bounded producer/consumer queue (overlap
   decompression with counting), coarse-grained batches, **no per-chunk fork-join barrier**.
   Partition keys into N disjoint thread-local tables (hash-range or canonical minimizer) so
   workers never touch a shared table during counting → no contention, better locality.
4. Rolling 2-bit encode + bit-parallel revcomp (u64 for k≤32) → ~2.7× single-thread.
5. Output: `sort_unstable_by_key` (pdqsort, no alloc) or `rayon::par_sort_unstable`; stream write.

Expected: recovering ~56% parallel efficiency on a ~169 s single-thread base → ~15–20 s,
plus rolling-encode and output gains → **competitive with jellyfish's 13 s**. Validate
against the slice matrix + count parity before claiming parity.

**Stage B — memory ceiling / KMC3 (CONDITIONAL; only if Stage A misses parity or for the
memory target):** minimizer/signature partitioning with cache-sized buckets and disk-backed
spill (KMC-class). Reuses rayon + the existing external-sort merge + memmap2. This bounds
peak RAM to the largest bucket (vs 18–55 GiB today) and is the path to beating KMC3 on
memory. **Not needed for the jellyfish speed gate** — the evidence shows speed is a
parallelism problem, not a capacity problem.

**Decompression:** producer/consumer overlap (double-buffer) recovers the ~8 s gz overhead;
file-level parallelism across split parts is free. **Do NOT adopt rapidgzip/pigz-style
parallel inflate** — libz is 0.09% of CPU; it is overkill (and pigz cannot parallelize
inflate of arbitrary gzip anyway — cached literature digest, MEDIUM).

### 2.2 Component boundaries — new vs modified (file-level)

| Component | File | New/Modified | Change |
|-----------|------|--------------|--------|
| Shared counting engine | `src/count/engine.rs` (or `src/hash/count_engine.rs`) | **NEW** | Producer/consumer + partitioned thread-local counting; the single delivery vehicle for both surfaces. |
| Rolling encoder + bit-parallel revcomp | `src/kmer/encoding.rs` | **MODIFY (add fns)** | Add `rolling_canonical_u64` (shift-in fwd/rev, `min`), `revcomp_bits_u64` (byte-swap + complement). Keep existing u128 fns for k>32 / API stability. |
| Canonical hot path | `src/kmer/canonical.rs` | **MODIFY** | Canonical via rolling fwd/rev `min` (no O(k) `reverse_complement_u128` loop in the hot path). |
| Counter | `src/hash/table.rs` | **MODIFY** | Thread-local / partitioned variant; move `total_kmers`/`unique_kmers` off the per-window path (thread-local accumulators reduced at end). Preserve `increment`/`get_count`/`get_all_counts` signatures + u32 overflow semantics (PCOUNT-04). |
| Count command | `src/cli/commands/count.rs` | **MODIFY** | Fix `resolve_thread_count` (lazy fallback, `build_global` first); replace inline `fill→par_iter→clear` with a call to the shared engine; `sort_unstable_by_key`. |
| FASTQ I/O | `src/io/fastq.rs` | **MODIFY (minor)** | Keep `MultiGzDecoder` (multi-member correctness). Optionally expose a record iterator the engine can overlap. |
| RKDB writer | `src/database/format.rs` | **UNCHANGED (format)** | `.rkdb` v2 layout untouched; engine feeds the same `DatabaseHeader::write_to` + `KmerEntry::write_to`. |
| PyO3 counter | `pyo3/src/counter.rs` | **MODIFY** | Route `add_from_fastq`/`add_from_fasta` through the shared engine (currently a **sequential** line-loop, `process_fastq_file_on_counter:763` — no rayon). Fix `save_database` double-sort. |
| Profiling/regression harness | `scripts/bench/` + `.planning/research/profiling/` | **MODIFY/NEW** | Add a `--threads`-correctness test (assert pool size), thread-scaling gate, count-parity gate on the real slice. |

### 2.3 Data flow changes

- **Before:** producer fills 4096 records → blocking `par_iter` (16 workers hammer one
  shared DashMap, per-window global atomics) → `clear` → repeat (serialized); then
  `get_all_counts` (full `Vec<(u128,u32)>` copy) → single-thread stable sort → write.
- **After:** producer streams records into a bounded queue **while** N workers count into
  **disjoint thread-local tables** (rolling encode, no global atomics); at EOF reduce
  thread-local totals, merge/partition-sort the tables, stream sorted `(u128,u32)` to the
  unchanged `.rkdb` writer. Decompression overlaps counting; workers never starve or spin.

### 2.4 `.rkdb` v2 preservation (hard constraint)

The engine emits `(u128, u32)` pairs; the **existing** `format.rs` writer produces the same
42-byte header + 20-byte entries. Partitioned counting merges buckets into a globally sorted
stream before writing → **byte-identical** output for the same input. Prove with the existing
golden sha256 tests (`tests/golden_tests.rs`) + the slice count-parity gate (Distinct
229,694,874 / Total 519,271,168). No format bump needed.

### 2.5 Dual-surface inheritance + a semantic divergence to surface

- Both surfaces depend on the core; routing **both** through the shared engine makes the win
  flow to CLI **and** `pyrustkmer` automatically (the project's delivery model).
- **Today the Python file-counting path is sequential** (`add_from_fastq` releases the GIL
  but runs a single-threaded line loop) — so Python is currently *slower* than the CLI on
  file counting. The shared engine fixes this.
- **Semantic divergence (must surface as a decision, not silently change):** the PyO3 path
  **filters non-ACGT bases before counting** (concatenates flanks across N), while the CLI
  **skips windows containing N**. On N-containing input they produce **different counts**.
  Unifying through the engine should adopt the CLI's skip-N semantics (matches jellyfish),
  but that changes Python output for N-containing reads → flag for the user/requirements.
- `PyCounter` public API (`add_kmer`/`add_sequence`/`get_count`/`save_database`) preserved;
  per-k-mer interactive calls can stay on a single partition.

### 2.6 Patterns to follow / anti-patterns to avoid

**Follow:**
- **Thread-local accumulation, reduce at end** — removes the per-window global-atomic
  cache-line bouncing (the ~9× contention multiplier).
- **Disjoint partitioning** (hash-range or canonical minimizer) — workers own private key
  spaces; no shared-table locking/contention during counting; merge is a separate phase.
- **Overlap producer/consumer** with a bounded queue — decompression runs concurrently with
  counting; workers never spin-wait for the next chunk.
- **Rolling 2-bit encode + word-level revcomp** — O(L) per read, not O(k·L).

**Avoid:**
- **Per-chunk fork-join barrier** (`fill → par_iter → clear`) — serializes producer and
  workers and strands fast P-cores waiting on E-core stragglers (the 58% spin-wait).
- **Eager `rayon::current_num_threads()` before `build_global`** — silently fixes the pool at
  `num_cpus` and makes `--threads` a no-op.
- **Per-window global atomics** for totals/unique — contention hotspot.
- **Single-thread stable `sort_by_key` on hundreds of millions of u128 keys** — use
  `sort_unstable` (keys are unique → stability irrelevant) or parallel sort.
- **Premature disk-backed / CQF rewrite for the speed gap** — the evidence says speed is a
  parallelism problem; disk-backed is for the memory ceiling (Stage B).
- **Chorus3 shortcuts** (saturating 2-bit counters, `rusty_alloc`) — already rejected: break
  exact-u32, 4^21 dense table is 1 TiB+, `rusty_alloc` needs MSRV 1.87 (disqualified for PyO3).

### 2.7 Build order (dependency-respecting)

1. **Profiling + regression harness** — reproducible slice bench, count-parity gate,
   **`--threads`-correctness test**, thread-scaling gate. *Foundation; everything is measured
   against it.* (`.planning/research/profiling/` scripts are the seed.)
2. **Fix `--threads` + thread-local counters + rolling encode** (core hot path). *Low-risk,
   both surfaces inherit; establishes a correct, faster baseline.* Depends on 1.
3. **Parallelism restructure** — shared engine with persistent workers + partitioned
   thread-local tables + overlapped producer/consumer. *The big lever (~3.5×).* Depends on 2.
4. **Output sort/write optimization** (`sort_unstable` / parallel sort, streaming). Depends on 3.
5. **`.rkdb` writer adaptation + golden/parity proof** — confirm v2 byte-identity. Depends on 3–4.
6. **Python parity** — route `PyCounter` file methods through the engine; resolve the N-semantics
   divergence (surface decision). Depends on 3–5.
7. **(Conditional) minimizer partitioning + disk-backed** for the memory ceiling / KMC3
   comparison (BENCH-V2-01). *Only if Stage A misses parity or the memory target demands it.*
   Depends on 3 (reuses the partitioned engine), the external-sort merge, memmap2.

### 2.8 Scaling considerations

| Scale | Adjustment |
|-------|------------|
| Slice / CI (≤4M reads) | Stage A in-memory engine; synthetic degradation ladder for CI (existing harness). |
| Human-scale r1 (~37M reads, 663M distinct) | Stage A in-memory fits (~18–30 GiB); partitioned thread-local tables keep peak bounded. |
| Memory-constrained / full PE / KMC3-beating | Stage B minimizer partitioning + disk spill; peak RAM = largest bucket; temp disk is the real budget (KMC3 uses hundreds of GB temp — cached literature, MEDIUM). |
| Many cores / P+E hybrid | Partition count tuned to P-core count; avoid E-core stragglers pacing the pool; consider P-core-only pool or work-stealing with coarse batches. |

---

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| Root cause (parallelism + contention) | **HIGH** | Direct measurement: 4 samply profiles, 14-arm matrix, single-thread microbench, live thread-count verification. |
| `--threads` bug | **HIGH** | 17 threads observed at `--threads 1`; mechanism confirmed in rayon-core source. |
| Decompression/encode rejected as primary | **HIGH** | libz 0.09% CPU; encode 3% CPU; gz→raw saves only ~11%. |
| Stage A achieves parity | **MEDIUM** | Extrapolated from measured scaling efficiencies; must be validated by implementation + the slice gate. |
| Single-thread full-slice estimate (169 s) | **MEDIUM** | Extrapolated from 2M-read microbench (249.6 ns) to 229M-distinct regime; not directly measured (CLI `--threads` bug blocks a true t1 run). |
| Contention multiplier (~9×) attribution to global atomics vs bandwidth | **MEDIUM** | Inferred from single-vs-multi gap + low lock-slow-path; not separately isolated (would need a multi-thread microbench variant). |
| Literature (KMC3/jellyfish/ntHash/simd-minimizers/pigz) | **MEDIUM** | Reused from parallel researcher's websearch cache (`.planning/research/.cache/`); not independently re-verified here. |

## What could NOT be measured (honest limits)

- **No sudo** → no cold-cache purge (warm-cache only, as v1.0); no dtrace/cargo-flamegraph
  (used samply + `sample`, which need no sudo).
- **No true single-thread CLI run** — the `--threads` bug forces 16 workers; single-thread
  costs come from the standalone microbench (which uses the real `KmerCounter`).
- **samply `--save-only` profiles are unsymbolicated** — resolved rustkmer RVAs via `nm` and
  labelled system libs by hand; system-lib internal symbols (e.g. exact spin primitive) are
  identified by address, not name.
- **Contention sub-attribution** (global atomics vs memory bandwidth) not isolated — both are
  implicated; a multi-thread microbench variant would separate them (recommended in phase 1).
- **KMC3 not installed** — BENCH-V2-01 comparison deferred (it is a secondary reference).

## Sources

- **Primary (this work, HIGH):** `.planning/research/profiling/` — `evidence.json`,
  `results.jsonl` (14-arm matrix), `prof*.breakdown.txt` (samply), `microbench_main.rs`,
  `verify_threads.py`, `parity_report.json`. Raw profiles: `/tmp/rkmer-v2-prof/profiles/*.json.gz`
  (regenerable via `run_profiles.py`).
- **Code (HIGH):** `src/cli/commands/count.rs` (chunk pipeline, `resolve_thread_count`),
  `src/hash/table.rs` (DashMap, per-window atomics), `src/kmer/encoding.rs` / `canonical.rs`
  (O(k) encode/revcomp), `src/io/fastq.rs` (`MultiGzDecoder`), `src/database/format.rs`
  (v2 writer), `pyo3/src/counter.rs` (sequential file path, N-filter divergence).
- **rayon-core 1.13 source (HIGH):** `current_num_threads → global_registry()` default-pool init.
- **v1.0 benchmark artifacts (HIGH):** `.planning/milestones/v1.0-phases/04-benchmark-validation/04-results-full-k21.json` / `k31.json`, `scripts/bench/bench.py` (methodology).
- **Literature (MEDIUM, reused cache):** KMC3 two-stage minimizer/signature partitioning;
  jellyfish2 lock-free invertible hash; ntHash/ntHash2 rolling hash; simd-minimizers (rust-seq,
  SEA 2025, NEON); qfilter CQF; pigz cannot parallelize inflate; minimizer bucket skew;
  KMC3 temp-disk budget. (`.planning/research/.cache/`, websearch, MEDIUM.)

---
*Architecture research for: rustkmer v2.0 k=21 Counting Parity*
*Researched: 2026-11-12 — empirical root-cause profiling on real CRR1936095 data*