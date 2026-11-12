# Requirements: rustkmer — Milestone v2.0 "k=21 Counting Parity"

**Defined:** 2026-11-12
**Core Value:** Count, query, and merge k-mers at genome scale within practical memory — fast and lean enough to compete with best-in-class tools (KMC / Jellyfish class), from both the CLI and Python.

**Milestone goal:** Match or beat Jellyfish2 on human-scale counting (k=21, and k=31 under fair comparison) on BOTH the CLI and Python surfaces, closing the BENCH-02 gap. Approach ratified from empirical profiling (D1): the gap is parallel-scaling efficiency, not data structures — Stage A in-memory parallelism is the spine; minimizer/disk-backed (Stage B) is conditional (D3). N-read semantics unified on CLI skip-N (D2).

**Evidence base:** `.planning/research/SUMMARY.md` + `.planning/research/profiling/` (HIGH-confidence measured root cause). Guardrails: exact u32 counts (fail-loud overflow), `.rkdb` v2 byte-identity, public CLI/Python APIs frozen, MSRV 1.82, Python ≥3.11, dual surface, benchmark honesty (parity before timing).

## v2.0 Requirements

Committed scope. Each maps to exactly one roadmap phase. MINIM-* are CONDITIONAL (Phase gated on D3 — see below).

### Profiling & Regression Harness (PROF)

- [x] **PROF-01**: A reproducible slice benchmark gates every optimized path with a count-parity check (pinned Distinct/Total against jellyfish on the measured input) and binary provenance (sha256 + commit + build profile) on every artifact; subslices are random-record, not head-of-file.
- [x] **PROF-02**: A `--threads` correctness test asserts the ACTUAL rayon pool size matches the requested thread count, and a thread-scaling gate proves wall-clock differs across t1/t4/t16 (the v1.0 1-vs-N count differential passed while the flag was a no-op).
- [x] **PROF-03**: A multi-thread contention microbench isolates the global-atomics vs memory-bandwidth share of the in-vivo increment multiplier, producing evidence that tunes the engine design.
- [x] **PROF-04**: A Python-surface counting benchmark with a committed baseline exists (the sequential PyO3 pipeline is measured, so Phase PY can prove a win, not assert it).
- [x] **PROF-05**: A CLI-vs-Python N-read differential is run and recorded, quantifying the chimeric-k-mer divergence that D2 resolves.

### Parallel Scaling & Hot Path (PAR)

- [x] **PAR-01**: `--threads` actually sizes the rayon pool (lazy fallback via `available_parallelism`; `build_global` before any rayon query); the `--threads > RUSTKMER_THREADS > RAYON_NUM_THREADS > num_cpus` precedence chain and Python `threads=` / IN-04 warn semantics are preserved.
- [x] **PAR-02**: Counting uses thread-local counters with end-of-run reduction; per-window global atomics (`total_kmers`/`unique_kmers` fetch_add) are removed from the hot path; the reduction uses checked arithmetic with the verbatim fail-loud overflow error (a new overflow site, never saturating).
- [x] **PAR-03**: A rolling 2-bit encoder + bit-parallel reverse-complement (u64 for k≤32) replaces per-window O(L·k) encoding; it masks to 2k bits and resets the valid run at every N and record boundary; differential-tested against the per-window encoder on the edge matrix (N at every position, lowercase, record boundaries, k ∈ {1..64}); the u128 path is retained for k>32 and API stability.

### Shared Counting Engine (ENGINE)

- [x] **ENGINE-01**: ONE counting entry point (`src/count/engine.rs`) is consumed by both `execute_count` (CLI) and `PyCounter::add_from_*` (Python): a fixed rayon pool, a producer streaming records into a bounded queue, and N persistent workers counting into disjoint hash-range-partitioned thread-local tables with overlapped decompression (no per-chunk fork-join barrier).
- [x] **ENGINE-02**: The thread-scaling gate (PROF-02) is green after the engine — rustkmer's parallel-scaling efficiency materially improves toward jellyfish's and the slice wall-clock drops measurably (the ~3.5x lever).
- [x] **ENGINE-03**: ONE window-extraction function in the core implements the D2 skip-N semantics for both surfaces; the MultiGzDecoder multi-member gzip regression (v1.0 8102985) stays green.

### Output & `.rkdb` Parity (OUT)

- [ ] **OUT-01**: Output uses unstable/parallel sort (`sort_unstable_by_key` / `rayon::par_sort_unstable`) and streaming write (no `get_all_counts` full materialization); text output sorts by numeric key.
- [ ] **OUT-02**: `.rkdb` v2 byte-identity is proven — golden sha256 captured BEFORE the refactor, sortedness proven through BOTH binary-search consumers (`DatabaseQuery` AND prefix query), header literals and the single `format.rs` writer frozen (IN-03 total_kmers meanings preserved).
- [ ] **OUT-03**: An old-vs-new AND 1-vs-N differential matrix across k × canonical proves exact counts are preserved by every new path (partitioned tables + end reduction), with disjointness and conservation property tests.

### Python Parity (PY)

- [ ] **PY-01**: `PyCounter` file methods route through the shared engine (no longer a sequential line loop); the public `PyCounter` API is frozen; every parallel/blocking path uses `py.detach` with owned Send captures; the `save_database` double-sort is fixed.
- [ ] **PY-02**: The D2 skip-N semantics is implemented in Python and the output change for N-containing reads is documented; the Python benchmark shows a measured win against the PROF-04 baseline.

### Benchmark Verdict (BENCH)

- [ ] **BENCH-V2-01**: A KMC3 comparison runs with exact-count configuration (install KMC 3.2.4 official mac.arm64 tarball; `-ci1 -cx4294967295 -cs4294967295`, matched threads/canonical, agreed `-m`), a parity gate on the measured input BEFORE timing, temp-disk recording, and graceful degradation when KMC3 is absent.
- [ ] **BENCH-V2-02**: A full human-scale jellyfish parity verdict is produced on BOTH surfaces — slice gate at every step, then the full run; medians of counterbalanced reps, honest per-rep cache_state, CI baselines regenerated only from the CI runner class. Acceptance: rustkmer matches or beats jellyfish at k=21 (and k=31 under fair, matched-hash comparison).

### Conditional Minimizer / Memory Ceiling (MINIM) — Stage B, gated on D3

> These requirements are IN SCOPE only if the conditional phase triggers: Stage A misses the parity gate, OR the user sets a memory ceiling Stage A cannot meet (e.g. beating KMC3 on RAM). If Stage A hits parity and memory is acceptable, MINIM-* descope/defer to a later milestone. They reuse the ENGINE partitioned tables + v1.0 external-sort/temp-lifecycle machinery; no new persistence engine; MSRV-clean hand-roll (no edition-2024 minimizer crates).

- [ ] **MINIM-01**: Hand-rolled canonical minimizer/signature extraction (KMC2 exclusion rules: AAA*/ACA*/internal AA) + super-mer runs, with a strand-invariance proptest (canonical minimizer = min(m-mer, revcomp(m-mer)), tie-breaks matching `canonical_kmer_u128`).
- [ ] **MINIM-02**: Skew-controlled bins (bucket histogram + adaptive re-partition; adversarial poly-A test input) and `--max-memory` counting admission with honest byte accounting; temp lifecycle extended (counting prefix paired with the prefix-based TTL sweep selector; `DiskOverflow` not reused).
- [ ] **MINIM-03**: Disk-backed bucket spill via BufReader (never mmap under an RSS budget); a bounded-RAM proof measured as max(rss, phys_footprint) red/green gate; KMC3 memory comparison.

## Future Requirements (deferred)

- Full-scale merge competitiveness vs a reference tool — merge is bounded-memory (v1.0); user chose counting-first, merge comparison deferred.
- Counter hasher swap (foldhash 0.2.0) as a committed optimization — hypothesis-grade until A/B'd on real keys with per-shard histograms AFTER the thread-local restructure; never fxhash-class; default sort untouched.
- mimalloc CLI-only allocator feature — low-priority experiment; evidence does not implicate allocation; never in the core rlib (PyO3 allocator hijack).
- std::arch SIMD encoding kernels — only if encoding still shows hot after the rolling scalar encoder (~3% of CPU today).
- Backlog 999.1–999.3 (pyo3 build.rs link args, stale site-packages shadowing, deferred-items stale sweep claim) — opportunistic.

## Out of Scope

| Feature | Reason |
|---------|--------|
| New user-facing features / commands | Performance milestone, not feature expansion |
| `.rkdb` format rewrite | Format stays v2 byte-compatible; a bump is a surfaced decision only if a specific win demands it |
| Approximate / saturating counting (Chorus3 2-bit counters) | Breaks the exact-u32 count contract |
| 4^21 direct-address table | 1 TiB (2-bit) / 16 TiB (u32) — infeasible |
| rusty_alloc / any global allocator in the core rlib | MSRV 1.87 + hijacks CPython's allocator via the cdylib |
| New persistence engine (LMDB/RocksDB/sled/redb) | Established-stack constraint; reuse external-sort machinery |
| Parallel gzip inflate (pigz/rapidgzip) | libz is 0.09% of CPU; pigz cannot parallelize inflate anyway |
| Parser swap (needletail/seq_io) by default | FASTQ parsing is 0.02% of CPU |
| CQF exact mode | No production pure-Rust exact CQF crate; VERY HIGH risk |
| GPU / distributed counting | Out of scope for this milestone |
| Query / prefix-query / fuzzy-query micro-optimization | Bottleneck is counting, not lookups |
| gxhash / fxhash for the counter | gxhash has no non-AES fallback (breaks portable builds); fxhash avalanche pathology on structured 2-bit keys |

## Traceability

Each requirement maps to exactly one phase. MINIM-* map to conditional Phase 11 (D3-gated).

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROF-01 | Phase 5 | Complete |
| PROF-02 | Phase 5 | Complete |
| PROF-03 | Phase 5 | Complete |
| PROF-04 | Phase 5 | Complete |
| PROF-05 | Phase 5 | Complete |
| PAR-01 | Phase 6 | Complete |
| PAR-02 | Phase 6 | Complete |
| PAR-03 | Phase 6 | Complete |
| ENGINE-01 | Phase 7 | Complete |
| ENGINE-02 | Phase 7 | Complete |
| ENGINE-03 | Phase 7 | Complete |
| OUT-01 | Phase 8 | Pending |
| OUT-02 | Phase 8 | Pending |
| OUT-03 | Phase 8 | Pending |
| PY-01 | Phase 9 | Pending |
| PY-02 | Phase 9 | Pending |
| BENCH-V2-01 | Phase 10 | Pending |
| BENCH-V2-02 | Phase 10 | Pending |
| MINIM-01 | Phase 11 (conditional — D3) | Pending (conditional) |
| MINIM-02 | Phase 11 (conditional — D3) | Pending (conditional) |
| MINIM-03 | Phase 11 (conditional — D3) | Pending (conditional) |

**Coverage:**
- v2.0 requirements: 21 total (18 committed + 3 conditional MINIM)
- Mapped to phases: 21/21 (100%) — 18 committed → Phases 5-10; MINIM-01..03 → conditional Phase 11 (executes only if D3 triggers; otherwise descope/defer)
- Unmapped: 0

---
*Requirements defined: 2026-11-12*
*Last updated: 2026-11-12 after roadmap creation (Phases 5-11; traceability populated, 21/21 mapped)*
