# Project Research Summary

**Project:** rustkmer — milestone v2.0 "k=21 Counting Parity"
**Domain:** Performance milestone on a shipped exact k-mer counting toolkit (Rust core + CLI + PyO3, shared `.rkdb` v2 format)
**Researched:** 2026-11-12 (STACK/FEATURES/PITFALLS 2026-11-11; ARCHITECTURE empirical profiling 2026-11-11/12)
**Confidence:** HIGH on the root cause (empirically measured on real data); MEDIUM on the predicted parity outcome (extrapolated, must be validated)

## Executive Summary

rustkmer v2.0 exists to close the measured ~5x k=21 counting gap vs Jellyfish2 on human-scale WGS data, on both the CLI and Python surfaces, with the approach chosen from profiling evidence (user directive "需要认真调研"). The Architecture researcher ran that profiling on a fresh release binary against a real CRR1936095 slice (4M reads, 519,271,168 k21 instances, 229,694,874 distinct canonical; Apple M4 Max, 16 cores), and the result **overturns the standing minimizer-first hypothesis**: the gap is **parallel-scaling efficiency, not decompression, not encoding, and not a memory-capacity/data-structure problem**. rustkmer's single-thread counting core is already competitive with jellyfish (190–250 ns/window vs jellyfish's 227). jellyfish scales 8.9x on 16 cores (118.2 s → 13.3 s); rustkmer effectively scales only ~3.3x. The gap decomposes as ~3.5x scaling efficiency × ~1.4x single-thread cost ≈ the observed 5x. The smoking gun: **`--threads` is a silent no-op** (17 OS threads observed at `--threads 1`; `resolve_thread_count` eagerly calls `rayon::current_num_threads()`, initializing the default 16-thread pool before `build_global`, whose error is discarded by `let _ =`), samply shows **59.5% of CPU in kernel spin-wait** (rayon per-chunk fork-join barriers), and per-window global atomics + shared-table DRAM access inflate the increment ~9.4x in vivo (916 vs 97 ns/window). gzip inflate is 0.09% of CPU; encoding ~3%. The gap is also **general, not k-specific**: k=31 is 5.01x slower on this dataset too — v1.0's "k=31 win" was jellyfish crippled by an oversized `-s 10G` hash. All evidence is persisted in `.planning/research/profiling/` (evidence.json, results.jsonl, samply breakdowns, microbench, verify_threads.py, parity_report.json).

**Recommended approach: Stage A first — fix the in-memory parallelism; Stage B (minimizer/disk-backed) is conditional.** Stage A: fix `--threads` → thread-local counters with end-of-run reduction (kill per-window global atomics) → a shared counting engine (`src/count/engine.rs`) with persistent workers, disjoint partitioned thread-local tables, and an overlapped producer/consumer pipeline → rolling 2-bit encode + bit-parallel revcomp (measured 2.7x single-thread win) → parallel/unstable output sort. This targets jellyfish parity (~13 s on the slice) and flows to both surfaces through one shared core. Stage B — hand-rolled KMC-style minimizer/signature partitioning with disk-backed bins — is the **memory-ceiling and KMC3-beating lever, not the speed lever**: jellyfish proves the workload fits in RAM and runs in 13 s in-memory. **The evidence does not justify leading with a data-structure rewrite.** The originally staged MINIM-01..03 direction should be demoted to a conditional phase, gated on Stage A's measured outcome and the memory target.

Key risks are known and have concrete mitigations. (1) Stage-A-achieves-parity is an extrapolation (MEDIUM) — the reproducible slice gate (count parity already PASS: Distinct 229,694,874 / Total 519,271,168, byte-compatible with jellyfish) must validate every step. (2) The dual surface is a trap: the PyO3 file-counting path is a **separate sequential pipeline** (no rayon anywhere in `pyo3/src/`), and CLI vs Python **already disagree on N-read semantics** (CLI skips N-windows; Python strips N and concatenates flanks, creating chimeric k-mers) — "byte-identical on both surfaces" is ill-defined until the user decides the unified semantics. (3) The exact-u32 / `.rkdb` v2 contract must survive: goldens captured before refactoring, fail-loud overflow (the new end-reduction summation is a new overflow site), globally sorted output proven through both binary-search consumers. (4) MSRV 1.80 excludes the entire current Rust minimizer-crate ecosystem (edition 2024) — Stage B must hand-roll; no production Rust CQF exists. (5) KMC3's defaults are **not exact counting** (`-ci2` drops singletons, `-cs255` saturates, `-cx1e9` caps) — BENCH-V2-01 needs `-ci1 -cx4294967295 -cs4294967295` and a parity gate before any timing.

## Key Findings

### The Decisive Empirical Finding (ARCHITECTURE.md — the milestone's decision basis)

Measured, not inferred. Full methodology and raw data: `.planning/research/profiling/` (`evidence.json`, `results.jsonl`, `prof*.breakdown.txt`, `microbench_main.rs`, `verify_threads.py`, `parity_report.json`).

| Measurement | Result | Implication |
|---|---|---|
| Slice gap (gz, t16, warm cache) | rustkmer 74.76 s vs jellyfish 13.29 s = **5.63x** (k31: 5.01x) | Gap reproduces; it is general across k, not small-k-specific |
| jellyfish thread scaling | 118.17 s (t1) → 13.29 s (t16) = **8.9x / 56% efficiency** | The workload parallelizes; in-memory is sufficient |
| rustkmer thread scaling | t1 ≈ t4 ≈ t8 ≈ t16 (all ran 16 workers — bug); extrapolated ~3.3x / ~21% | **~3.5x scaling deficit is the dominant lever** |
| `--threads 1` live thread count | **17 OS threads** (expected ~2) | `--threads` is a complete no-op; PCOUNT-03 plumbing bug |
| samply CPU breakdown (k21 gz) | **59.5% kernel spin/wait**, 36.3% DashMap increment, 3.1% encode, **0.09% gzip**, 0.02% parse; shard-lock slow path 0.41% | Workers spin at per-chunk barriers; locks are NOT contended; decompression/encoding rejected as primary |
| In-vivo vs single-thread increment | ~916 vs 97.3 ns/window = **~9.4x multiplier** | Per-window global atomics (`total_kmers`/`unique_kmers` fetch_add) + shared-table DRAM random access |
| Single-thread microbench | production 190.8 ns (cache) / 249.6 ns (DRAM) vs jellyfish 227; rolling+bitrc **70.9 ns (2.7x)**; rolling encode 1.2 vs 31.7 ns (26x) | Single-thread core is competitive; rolling encode is a real but secondary lever |
| Count parity | Distinct 229,694,874 / Total 519,271,168 — **exact match vs jellyfish** | The parity gate baseline for every optimized path |
| Peak RSS (slice) | rustkmer 18.4 GiB vs jellyfish 6.68 GiB | Speed is Stage A; **leanness is Stage B territory** |
| Output phase | 13.4 s sorted vs 3.5 s `--no-sort` | ~10 s single-thread stable sort on 229M u128 keys — cheap win |

Root-cause decomposition: **~3.5x parallel-scaling efficiency × ~1.4x single-thread per-window cost ≈ 4.9x ≈ observed 5x.** The biggest lever is recovering parallel scaling — an engineering problem, not a data-structure replacement.

### Recommended Stack (STACK.md, reconciled with the profiling evidence)

Stage A needs **no new runtime dependencies**: the `--threads` fix, thread-local counters, bounded-queue pipeline (`std::sync::mpsc` / existing parking_lot), rolling encoder, and `sort_unstable`/`rayon::par_sort_unstable` are all std/existing-dep work. The one candidate addition is a counter hasher swap — treated as a hypothesis-grade experiment, not a plan premise.

**Core technologies:**
- **Existing stack (rayon, dashmap 6.2.1, byteorder, bio, flate2, parking_lot)** — Stage A is a restructure, not a dependency change; satisfies the established-stack constraint.
- **foldhash 0.2.0 `fast::RandomState` (MSRV 1.60 — PASS)** — candidate counter hasher. **Verified fact: the counter today uses SipHash-1-3, NOT ahash** (dashmap 6.2.1 default `RandomState`, confirmed in locked source; `grep ahash src/` = zero hits; ahash only reaches the merge accumulator). Published ~11x cheaper u64 hashing, but the profiling shows increment cost is dominated by DRAM + atomics, and PITFALLS warns structured 2-bit keys can cluster weak-avalanche hashers (shard imbalance). **A/B only after the thread-local restructure, with per-shard histograms on real keys; never fxhash-class.**
- **Hand-rolled KMC-style signatures (Stage B only)** — every current minimizer crate fails MSRV 1.80: simd-minimizers 2.3+/3.x and seq-hash are edition 2024 (Rust ≥1.85), packed-seq 5.x needs wide 1.7 (MSRV 1.89), and simd-minimizers has compile-time AVX2/NEON gates that break portable wheels/CI. No production Rust CQF crate exists (mqf is a dead 2019 C++ FFI). Disk-backed counting must reuse `streaming_merge.rs` / `prefix_cache_merge.rs` / `temp_lifecycle.rs` — **no new persistence engine**.
- **std::arch SIMD (NEON stable since 1.59; SSE2/AVX2 runtime-dispatched)** — only if encoding still shows hot after the rolling scalar encoder (it is ~3% of CPU today). No new SIMD crate by default (`wide =0.7.33` is the unsafe-free fallback; wide 0.8+/fearless_simd/macerator all fail MSRV).
- **mimalloc 0.1.52 (optional, CLI-binary-only feature, default OFF)** — low-priority experiment; the evidence does not implicate allocation. Hard rule: `#[global_allocator]` only in `src/main.rs`, never the core rlib (would hijack CPython's allocator via the cdylib).

**Dev/benchmark tools:** samply 0.13.1 (no sudo — already used for the evidence); KMC 3.2.4 official `mac.arm64` tarball (no Homebrew formula; `ulimit -n 2048` required); criterion stays 0.5 (upgrade ceiling 0.7.0 at MSRV 1.80); **rustup 1.80 toolchain is not installed locally** — install it in the first phase that adds dependencies and run MSRV-aware clippy on both crates.

**Rejected (do not re-propose):** gxhash (no non-AES fallback, breaks portable builds), fxhash for the counter (avalanche pathology on structured keys), rusty_alloc (MSRV 1.87 + PyO3-disqualified), Chorus3 saturating counters (break exact-u32), 4^21 direct table (1 TiB+), LMDB/RocksDB/sled/redb (no new persistence engine), rapidgzip/pigz-class parallel inflate (libz is 0.09% of CPU; pigz cannot parallelize inflate anyway), needletail/seq_io parser swap by default (parsing is 0.02% of CPU), hashbrown 0.16 direct bump (forks dashmap's table for zero benefit).

### Expected Features (FEATURES.md — technique landscape, re-prioritized by the evidence)

FEATURES.md (researched pre-profiling) hypothesized the fat table (~36 B/entry vs jellyfish's bit-packed ~2–5 B/entry, lock-free CAS, k-mer-is-its-own-hash) was THE gap. The measurement demotes that to the ~1.4x single-thread factor and promotes contention-free parallelism to the top lever. Its technique classification still holds; the pursuit order changes.

**Must have (table stakes — Stage A):**
- **Contention-free parallel increments** — thread-local/partitioned tables, no per-window global atomics; the measured 9.4x multiplier and 58% spin-wait are the gap.
- **Correct, observable thread control** — `--threads` must actually size the pool (currently a no-op); precedence chain preserved.
- **Rolling encode + bit-parallel canonicalization** — O(L) per read instead of O(L·k); measured 2.7x single-thread win; also the prerequisite for any future minimizer work.
- **Overlapped producer/consumer I/O** — decompression concurrent with counting (recovers the ~8–10 s gz serialization overhead; no new decoder needed).
- **Exact non-saturating u32 counts + canonical k-mers** — preserved contract, fail-loud overflow, on every new path.

**Should have (differentiators — Stage B, conditional):**
- **Minimizer/signature partitioning + per-bucket exact counting (KMC-class)** — bounds peak RAM to the largest bucket (vs 18–55 GiB today); the path to beating KMC3 on memory. In-memory disjoint hash-range partitioning (Stage A) captures the contention/locality benefits without disk.
- **Dense u64 per-bucket sub-tables** — extends the shipped DENSE-01 win into the partitioned regime (exact u32 arrays, never 2-bit saturating).
- **Disk-backed bucket spill** — only when the memory ceiling demands it; reuses the v1.0 external-sort machinery.

**Defer / anti-features:** CQF exact mode (no pure-Rust exact crate; VERY HIGH risk), GPU counting, distributed counting, approximate/saturating counting, `.rkdb` rewrite, 4^21 direct addressing, parallel gzip inflate. Match jellyfish's *properties* (compact, contention-free, cache-local) — do not clone its bit-packed CAS table.

### Architecture Approach (ARCHITECTURE.md)

One shared counting engine delivers to both surfaces; the `.rkdb` v2 writer and public APIs stay frozen. Stage A restructures the in-memory pipeline; Stage B adds partitioned disk-backed counting only if triggered.

**Major components:**
1. **NEW `src/count/engine.rs`** — the single counting entry point for CLI and PyO3: fixed rayon pool (built before any rayon query), producer thread streaming records into a bounded queue, N persistent workers counting into **disjoint thread-local tables** (hash-range partitioned on the canonical key), rolling encode, thread-local totals reduced at end.
2. **`src/kmer/encoding.rs` / `canonical.rs` (modify)** — add rolling 2-bit shift-in + word-level revcomp (`u64` for k≤32); mask to 2k bits and reset the valid-run counter at every N and record boundary; existing u128 functions kept for k>32 and API stability.
3. **`src/hash/table.rs` (modify)** — thread-local/partitioned counter variant; totals off the per-window path; `increment`/`get_count`/`get_all_counts` signatures and verbatim overflow semantics preserved.
4. **`src/cli/commands/count.rs` (modify)** — fix `resolve_thread_count` (lazy fallback via `available_parallelism`, `build_global` first); delegate to the engine; `sort_unstable_by_key` / parallel sort; streaming write.
5. **`pyo3/src/counter.rs` (modify)** — route `add_from_fastq`/`add_from_fasta` through the engine (today a sequential line loop); fix `save_database` double-sort; `py.detach` + owned Send captures; public `PyCounter` API unchanged.
6. **`src/database/format.rs` (UNCHANGED)** — single `.rkdb` v2 writer (42-byte header + 20-byte entries); the engine emits a globally sorted `(u128, u32)` stream into it; byte-identity proven by golden sha256 + both binary-search consumers.

**Patterns to follow:** thread-local accumulation with end reduction; disjoint partitioning; bounded-queue overlap; coarse batches sized to avoid E-core stragglers pacing P-cores. **Anti-patterns (measured):** per-chunk `fill → par_iter → clear` barriers; eager rayon queries before `build_global`; per-window global atomics; single-thread stable sort of 229M keys; `get_all_counts` full materialization; premature disk/CQF rewrite for a speed problem.

### Critical Pitfalls (PITFALLS.md — top items, evidence-weighted)

1. **Thread-pool mis-initialization and precedence regressions (Pitfall 12 + the measured `--threads` bug)** — compute the fallback lazily, `build_global` before any rayon query, keep the build-once idiom and the `--threads > RUSTKMER_THREADS > RAYON_NUM_THREADS > num_cpus` chain (and Python's `threads=` / IN-04 warn). Add a test that asserts the actual pool size — the 1-vs-N count differential passed for a year while the flag did nothing.
2. **Extraction-semantics drift, including the existing CLI/Python N divergence (Pitfall 10 — a verified finding, not a hypothesis)** — CLI skips N-windows (the jellyfish-validated reference); Python strips N and joins flanks. Surface the unification decision (D2 below), then extract ONE window-extraction function into the core. A rolling encoder adds a third risk: mask + N-reset or it silently reproduces the chimeric-k-mer bug in the CLI. Differential-test rolling vs per-window on the edge matrix (N at every position, lowercase, record boundaries, k ∈ {1..64}).
3. **`.rkdb` v2 byte-identity: bucket order ≠ sorted order (Pitfall 15)** — partitioned output must be merged/sorted into one globally ascending stream before the frozen `format.rs` writer; header literals frozen (note IN-03: counter `total_kmers` = sum of counts, header `total_kmers` = record count); prove sortedness through BOTH binary-search consumers; goldens captured BEFORE the refactor, never updated to make a diff green.
4. **Exact-count drift in new counters and reductions (Pitfalls 8, 9)** — u32 everywhere, overflow `Err` with the verbatim contract-pinned message; the end-of-run/pass-2 summation is a NEW overflow site (checked arithmetic, never `saturating_add`); two phase-independent conservation checks + disjointness property tests; 1-vs-N AND old-vs-new differential matrix across k × canonical.
5. **Dual-surface divergence: CLI gets the win, Python doesn't (Pitfall 16)** — the PyO3 file path is sequential today; swapping the table alone delivers nothing to Python. One shared engine entry point (the v1.0 `merge_databases_to_path` precedent), plus a Python-surface benchmark with a committed baseline — pytest correctness passing is not evidence of speed.
6. **KMC3 benchmark unfairness (Pitfall 18)** — defaults are not exact counting (`-ci2`, `-cs255`, `-cx1e9`); configure `-ci1 -cx4294967295 -cs4294967295`, matched threads/canonical, agreed `-m`; parity gate on the measured input BEFORE timing; record temp-disk usage; a mismatch is a methodology finding, never a reason to touch rustkmer semantics.
7. **MSRV / PyO3 guardrails (Pitfalls 17, 13)** — edition-2024 deps fail MSRV 1.80 as a hard compiler error that `incompatible_msrv` does not catch; audit every new dep's manifest + tree; 1.80 clippy on BOTH crates; every thread-spawning PyO3 path uses `py.detach` with owned Send captures (deadlock otherwise); no global allocator in the rlib; `maturin develop --release` + module version assert before every pytest (stale `.so` shadowing is a known trap).

Stage-B-specific pitfalls (apply only if the conditional phase triggers): canonical-unaware minimizers split counts (1), bucket-local key leakage (2), severe bucket skew max/mean ~80 (3), super-mer/read-end boundary loss (4), temp-lifecycle reuse — the TTL sweep is prefix-based and `DiskOverflow` is a trap (5), fsync/fd-exhaustion on hundreds of bins (6), never mmap spill under an RSS budget + honest admission accounting (7).

## User Decisions Required (surface during requirements, before the affected phases)

**D1 — Ratify the parallelism-first pivot (Stage A) over the originally staged minimizer-first direction.**
PROJECT.md staged MINIM-01..03 as the candidate architecture and records "approach chosen from profiling evidence, not guesswork." The evidence now says the speed lever is parallelism, not partitioning. Recommendation: **approve Stage A as the milestone spine; demote minimizer/disk-backed to conditional Stage B.** This changes the milestone's staged scope, so it belongs to the user — but the data is unambiguous (`.planning/research/profiling/evidence.json`).

**D2 — Unify CLI/Python N-read semantics (changes Python output).**
Today the CLI skips windows containing N; Python strips non-ACGT bases and concatenates flanks, counting chimeric k-mers the CLI never counts. Real Illumina reads contain Ns, so "byte-identical counts on both surfaces" is ill-defined until this is decided. Recommendation: **adopt the CLI skip-N semantics** (it is what the jellyfish parity gate validated) in the single shared extraction function, and explicitly accept that Python output changes for N-containing reads. Never silently "fix" it (WR-04 precedent). Alternative (keep both semantics behind a flag) forks the extraction core and is not recommended.

**D3 — Is Stage B (minimizer/disk-backed memory work) in v2.0 scope, or deferred?**
jellyfish parity does not require it (13 s in-memory, 6.68 GiB). It is the lever for the memory ceiling (rustkmer 18.4 GiB on the slice; 55.2 GiB at k31 human scale) and for beating KMC3 on RAM. Recommendation: **keep BENCH-V2-01 (the KMC3 comparison itself) in v2.0** — it is cheap once the tarball is installed and is already an Active requirement — and **gate the Stage B architecture phase** on (a) Stage A missing the parity gate, or (b) the user setting a memory ceiling Stage A cannot meet. If Stage A hits parity and memory is acceptable, descope MINIM-01..03 to a future milestone.

## Requirement Candidates (for the roadmapper / requirements definition)

Grouped candidates; IDs are suggestions except BENCH-V2-01 and MINIM-01..03 which already exist in PROJECT.md / the v1.0 archive.

**Profiling / regression harness (foundation):**
- Reproducible slice benchmark with the count-parity gate (Distinct 229,694,874 / Total 519,271,168) and binary provenance (sha256 + commit + build profile) on every artifact; random-record subslices, not head-of-file.
- `--threads` correctness test asserting the actual pool size; thread-scaling gate (t1 vs t4 vs t16 must differ).
- Multi-thread microbench variant isolating global-atomics vs memory-bandwidth share of the 9.4x multiplier.
- Python-surface counting benchmark with a committed baseline (currently unmeasured; sequential pipeline known).
- CI degradation ladder preserved (slices/synthetic when the real dataset is absent); true per-rep cache_state.

**Parallel-scaling fixes (the lever):**
- Fix `resolve_thread_count` (lazy fallback; `build_global` before any rayon query); precedence chain + IN-04 semantics preserved.
- Thread-local counters with end-of-run reduction; per-window global atomics removed; checked reduction arithmetic with the verbatim overflow error.
- Persistent-worker engine with bounded producer/consumer queue (overlapped decompression), coarse batches, disjoint hash-range partitioning on canonical keys; P/E-core-aware scheduling.

**Hot path / encoding:**
- Rolling 2-bit encoder + bit-parallel revcomp (u64 for k≤32), masked, N-reset, differential-tested against `encode_kmer_bytes_u128` on the edge matrix; u128 path retained for k>32.
- Hasher A/B (foldhash 0.2.0) only with real-key evidence + per-shard histograms, after the restructure; default sort untouched.

**Shared dual-surface engine:**
- ONE counting entry point (`src/count/engine.rs`) consumed by `execute_count` AND `PyCounter::add_from_*`; ONE window-extraction function; PyO3 layer reduced to validation + `py.detach` + error mapping.
- D2 semantics decision implemented and documented; `PyCounter` public API frozen; `save_database` double-sort fixed.

**Output / `.rkdb` byte-identity:**
- `sort_unstable_by_key` / `rayon::par_sort_unstable`; streaming write (no `get_all_counts` full materialization); text-output sort by numeric key.
- Golden sha256 captured pre-refactor; sortedness proven through `DatabaseQuery` AND prefix query; header literals and the single `format.rs` writer frozen.

**Benchmark / verdict (incl. KMC3):**
- jellyfish parity verdict: slice gate at every step, then full human-scale run; medians, counterbalanced reps, honest cache_state; CI baselines regenerated only from the CI runner class.
- BENCH-V2-01: install KMC 3.2.4 (official mac.arm64 tarball), exact-count flags `-ci1 -cx4294967295 -cs4294967295`, parity-before-timing, temp-disk recording, graceful absence degradation.

**Conditional minimizer / disk-backed (Stage B — only if D3 gates it in):**
- MINIM-01..03 re-scoped: hand-rolled canonical signatures (KMC2 exclusion rules) + super-mers; bucket histogram + skew control + adaptive re-partition; `--max-memory` admission with honest byte accounting; temp lifecycle extension (counting prefix paired with the TTL sweep selector); disk spill via BufReader (never mmap); live max(rss, phys_footprint) red/green gate.

## Implications for Roadmap

Suggested phase structure (7 phases; Phase 7 conditional). This reorders PITFALLS.md's working P1–P5 labels, which assumed minimizer-first — the evidence supersedes that ordering while keeping its "profiling first" mandate (already largely fulfilled).

### Phase 1: Measurement & Regression Harness Foundations
**Rationale:** Everything downstream is claimed against gates; the profiling evidence exists but is not yet a standing regression gate. Cheap, de-risks all later phases, and closes the known measurement gaps (contention sub-attribution, Python baseline, slice representativeness).
**Delivers:** Standing slice bench + parity gate, `--threads` pool-size test, thread-scaling gate, multi-thread contention microbench, Python baseline, provenance discipline.
**Addresses:** Profiling/harness requirement candidates; FEATURES P1 "root-cause profiling" (extend, don't redo).
**Avoids:** Pitfalls 19 (stale binary/warm cache/bad slice), 11/14 (measure before acting), 10 (run the CLI-vs-Python N differential and record it for D2).

### Phase 2: Parallelism Correctness + Hot Path
**Rationale:** The `--threads` fix is near-free and unblocks true single-thread measurement; thread-local counters + rolling encode are low-risk, independently measurable wins (2.7x single-thread measured) that both surfaces inherit. Establishes the correct, faster baseline before the big restructure.
**Delivers:** Working `--threads`, no per-window global atomics, rolling encoder + bit-parallel revcomp with full differential coverage, true t1 baseline numbers.
**Uses:** std/existing deps only; microbench-proven rolling keys.
**Avoids:** Pitfalls 12 (pool init/precedence), 8 (reduction overflow), 10 (rolling N-reset), 17 (MSRV).

### Phase 3: Shared Counting Engine (the ~3.5x lever)
**Rationale:** The dominant measured cost is the serialized per-chunk pipeline + shared-table contention. Persistent workers, disjoint partitioned tables, and overlapped I/O attack exactly that; building it as the shared core entry point makes Python inheritance structural, not accidental.
**Delivers:** `src/count/engine.rs` with producer/consumer overlap and partitioned thread-local counting; CLI wired through it; scaling gate green.
**Implements:** ARCHITECTURE Stage A steps 3; FEATURES "in-memory partitioned counting" (promoted from stepping-stone to spine).
**Avoids:** Pitfalls 11 (overlap, MultiGzDecoder preserved + multi-member regression), 12, 9 (disjointness/conservation), 16 (shared entry).

### Phase 4: Output Pipeline + `.rkdb` v2 Parity Proof
**Rationale:** ~10 s of the slice wall is single-thread stable sort; the writer contract is the milestone's compatibility gate. Depends on the engine's sorted-stream output.
**Delivers:** Unstable/parallel sort, streaming write, golden byte-identity + both-consumer sortedness proof, old-vs-new + 1-vs-N differential matrix.
**Avoids:** Pitfalls 15 (bucket order ≠ sorted order, header freeze, IN-03), 8/9 (boundary proofs), `get_all_counts` materialization trap.

### Phase 5: Python Parity
**Rationale:** Acceptance explicitly includes `pyrustkmer`; the Python path is sequential today and semantically divergent. Requires D2 resolved (ideally at requirements time) and the engine + output proof in place.
**Delivers:** `PyCounter` file methods routed through the engine, unified extraction semantics per D2, detach audit, double-sort fix, Python benchmark showing the win against its Phase-1 baseline.
**Avoids:** Pitfalls 13 (GIL/deadlock, stale `.so`), 10 (semantics), 16 (measured, not asserted).

### Phase 6: Benchmark Verdict (jellyfish gate + KMC3 BENCH-V2-01)
**Rationale:** The verdict is the milestone's acceptance; run it only on proven-correct code. KMC3 install + exact-flag configuration is small, well-researched work.
**Delivers:** Full human-scale parity verdict vs jellyfish on both surfaces; KMC3 exact-count comparison with parity-before-timing; regenerated CI baselines; honest cache-state report.
**Avoids:** Pitfalls 18 (KMC3 defaults), 19 (provenance/cache honesty), 14 (no unevidenced hasher swap sneaking into the verdict build).

### Phase 7 (CONDITIONAL — D3): Minimizer Partitioning / Memory Ceiling
**Rationale:** Only if Stage A misses parity or the user sets a memory ceiling Stage A cannot meet (e.g., beating KMC3 on RAM). Reuses the Phase-3 partitioned engine + v1.0 external-sort/temp-lifecycle machinery. **If Stage A hits parity and memory is acceptable, descope to memory-only work or defer to a later milestone.**
**Delivers (if triggered):** Hand-rolled canonical signatures + super-mers, skew-controlled bins, `--max-memory` counting with disk spill, bounded-RAM proof, KMC3 memory comparison.
**Avoids:** Pitfalls 1–7 (canonical minimizers, key leakage, skew, boundary loss, temp lifecycle, fsync/fd, mmap/admission), 15, 17.

### Phase Ordering Rationale

- **Evidence → correctness → structure → proof → verdict:** the harness makes every claim measurable; the `--threads` fix makes single-thread truth observable; the engine is the measured lever; output/parity proofs protect the contract before any verdict; KMC3 closes the second reference.
- **Dependencies:** rolling encode and thread-local counters (2) are prerequisites for the engine (3); the engine's sorted stream feeds the output stage (4); Python routing (5) needs the engine + semantics decision; the verdict (6) needs both surfaces proven; Stage B (7) reuses the partitioned engine.
- **Pitfall avoidance is structural:** the two verified dual-surface findings (sequential Python pipeline, N-semantics divergence) are addressed by the shared-engine spine rather than patched per surface; goldens are captured before any refactor lands.
- **Flex point:** Phases 2 and 3 may merge if planning finds the thread-local counter work inseparable from the engine; Phases 4 and 5 may partially overlap. Do not reorder 6 before 4/5.

### Research Flags

Phases likely needing deeper research during planning (`/gsd-plan-phase --research-phase`):
- **Phase 3:** engine design choices need validation — hash-range vs canonical-minimizer partitioning for the in-memory tables, queue/batch sizing on P+E hybrid cores, and the atomics-vs-bandwidth sub-attribution (run the multi-thread microbench first). Highest-leverage phase; design evidence pays for itself.
- **Phase 6:** KMC3 exact-flag behavior must be re-verified at run time against the pinned 3.2.4 release (source checked was master); install + `ulimit` + temp-disk accounting on macOS.
- **Phase 7 (if triggered):** KMC3 primary-paper details (signature→bin packing, RADULS-class sort), bucket-skew measurement on the real slice, MSRV-clean hand-roll design. Sparse primary sources; PITFALLS flags the primary KMC3 paper was not directly retrieved.

Phases with standard patterns (skip research-phase):
- **Phase 1:** the harness and profiling scripts already exist (`scripts/bench/`, `.planning/research/profiling/`); this is extension, not discovery.
- **Phase 2:** the bug mechanism is confirmed in rayon-core source; the rolling encoder is already implemented and key-verified in the microbench.
- **Phase 4:** sort + existing writer + existing golden/differential discipline (v1.0 DENSE-02/PCOUNT-04 precedents).
- **Phase 5:** the v1.0 shared-entry merge precedent (`merge_databases_to_path`) is the template; PyO3 detach patterns are in-repo.

### Non-Negotiable Guardrails (every phase)

- **Exact counts:** u32, fail-loud at `u32::MAX`, verbatim overflow message; checked arithmetic in every new summation; no saturating/wrapping anywhere.
- **Compatibility:** `.rkdb` v2 byte-identical (sorted mode), single `format.rs` writer, frozen header literals, public CLI/Python APIs unchanged; any break is a surfaced decision only.
- **MSRV 1.80 / Python ≥3.11:** 1.80-aware clippy on both crates (toolchain must be installed); audit new deps for edition-2024/MSRV/global-allocator/PyO3-bump traps.
- **PyO3 safety:** `py.detach` + owned Send captures around all parallel/blocking work; no Python callbacks from workers; no global allocator reachable from the cdylib; rebuild + version-assert before pytest.
- **Benchmark honesty:** parity before timing; true cache_state; medians of counterbalanced reps; per-platform baselines from the CI runner class only; binary/module provenance on every artifact.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH (facts) / MEDIUM-LOW (perf predictions) | Versions/MSRV/installability verified against crates.io API, locked local source, GitHub manifests; hasher-swap win on the real workload unmeasured |
| Features | MEDIUM | Mechanisms cross-checked (papers + official jellyfish manual + code); its pre-profiling prioritization (fat table = THE gap) is corrected by measurement to the ~1.4x single-thread factor |
| Architecture | HIGH (root cause) / MEDIUM (outcome) | Root cause directly measured: 14-arm matrix, 4 samply profiles, single-thread microbench, live thread verification; Stage-A-parity is extrapolated from scaling efficiencies |
| Pitfalls | MEDIUM-HIGH | Codebase findings HIGH (file:line anchored, incl. two verified dual-surface findings); external claims MEDIUM (≥2 sources); a few rayon-doc nuances LOW |

**Overall confidence:** HIGH on the diagnosis and the recommended direction; MEDIUM on the predicted parity outcome — which is exactly what the phase gates exist to convert into measurement.

### Gaps to Address

- **Stage-A-achieves-parity is extrapolated:** the ~169 s single-thread full-slice estimate comes from a 2M-read microbench scaled to the 229M-distinct regime. Validate via the slice gate after Phases 2–4; re-measure true t1 once `--threads` works.
- **Contention sub-attribution unisolated:** global atomics vs memory bandwidth both implicated in the 9.4x multiplier; the multi-thread microbench (Phase 1) separates them and tunes Phase 3.
- **Hasher identity/cost discrepancy:** STACK verified the counter uses SipHash-1-3 (dashmap default), while the samply breakdown notes label increment frames "ahash" — treat the source verification as authoritative; hash-only cost was never isolated, so the foldhash win is hypothesis-grade until A/B'd on real keys with shard histograms.
- **Cold-cache and true single-thread CLI not measurable today:** no sudo (warm-cache only, as v1.0 — record honestly); the `--threads` bug blocked real t1 runs. Both are recorded limitations, not blockers.
- **Slice representativeness:** head-of-file 4M-read slice is repeat-rich (distinct/instance 2.26 vs v1.0's 7.3); the structural conclusion is robust but absolute seconds are not comparable to v1.0 — validate on random subslices and the full dataset before the verdict.
- **KMC3 not installed:** BENCH-V2-01 deferred to Phase 6; exact-count flags re-verified against the pinned release at run time.
- **Rust 1.80 toolchain absent locally:** install in the first dep-adding phase; dev-host stable clippy is not MSRV evidence.
- **Python baseline unmeasured:** the sequential pipeline is code-verified but its magnitude is unknown — Phase 1 establishes the baseline so Phase 5 can prove the win.
- **Stage A memory outcome unknown:** rustkmer 18.4 GiB vs jellyfish 6.68 GiB on the slice; partitioned thread-local tables change the peak in ways not yet measured. Leanness vs KMC3 remains Stage B territory (D3).

## Sources

### Primary (HIGH confidence)
- `.planning/research/profiling/` — this milestone's empirical evidence: `evidence.json`, `results.jsonl` (14-arm matrix), `prof21-gz-t16/prof21-fq-t16/prof31-fq-t16.breakdown.txt` (samply self-time), `microbench_main.rs` (+ `microbench_Cargo.toml`), `verify_threads.py`, `parity_report.json`, `run_matrix.py`/`run_profiles.py`/`post_matrix.sh` (reproduction). Raw profiles regenerable in `/tmp/rkmer-v2-prof/`.
- rustkmer source (direct reads, file:line anchors in the four research docs): `src/cli/commands/count.rs`, `src/hash/table.rs`, `src/kmer/encoding.rs`/`canonical.rs`, `src/io/fastq.rs`, `src/database/format.rs`/`query.rs`/`streaming_merge.rs`/`temp_lifecycle.rs`, `pyo3/src/counter.rs`, `scripts/bench/bench.py`, `tests/golden_sha256_tests.rs`.
- Locked crate source: dashmap 6.2.1 (default `RandomState` = SipHash-1-3, shard formula), hashbrown 0.14.5/0.16.1, foldhash 0.2.0; rayon-core 1.13 (`current_num_threads` → default-pool init); Rust 1.80.0 std source.
- crates.io registry API + GitHub manifests at tags (MSRV/edition verification, fetched 2026-11-11); GitHub releases API (KMC 3.2.4 mac.arm64 tarball); local system checks (jellyfish 2.3.1 present, no brew kmc, toolchain inventory).
- v1.0 benchmark artifacts: `.planning/milestones/v1.0-phases/04-benchmark-validation/` results + `scripts/bench/` methodology and baselines.

### Secondary (MEDIUM confidence)
- Jellyfish2 official manual (bit-packed entries `2k−l+r+1` bits, CAS, `-s`/`-c` semantics) — primary document, cross-checked with source mirrors and lecture notes.
- KMC2/KMC3 papers and cross-checks (Bioinformatics 2017;33:2759, arXiv:1701.08022, GigaScience PMC6280066, WABI 2022, theses) — signature rules, two-stage design, skew ratios, temp-disk figures; primary KMC3 paper text not directly retrieved.
- KMC source `kmc_CLI/kmc.cpp` usage text + issue #136 (default `-ci2`/`-cs255`/`-cx1e9`); re-verify at benchmark time.
- ntHash/ntHash2, simd-minimizers (SEA 2025), minimizer/syncmer theory (Marçais 2024, Shaw/Zheng theses), Squeakr/CQF papers, Gerbil/BCALM2/DSK benchmarks, Rust Performance Book + hashbrown hasher benchmarks, foldhash/gxhash/mimalloc/samply READMEs, bioconda KMC recipe.
- Research cache digests: `.planning/research/.cache/` (websearch, reused by ARCHITECTURE).

### Tertiary (LOW confidence — flagged, needs validation)
- CQF-crate absence claim (search-based: only dead mqf FFI + C++ Squeakr found); debruijn suitability; pulp MSRV.
- rayon `with_min_len`/`with_max_len` hint semantics and fold split nondeterminism (single official-doc fetch).
- pigz/rapidgzip parallel-inflate claims (cached literature; moot for this milestone — libz is 0.09% of CPU).

---
*Research completed: 2026-11-12*
*Synthesized from: STACK.md, FEATURES.md, ARCHITECTURE.md (empirical), PITFALLS.md — full detail in those files*
*Ready for roadmap: yes — with user decisions D1 (parallelism-first pivot), D2 (N-read semantics), D3 (Stage B scope) to resolve during requirements*