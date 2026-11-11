# Stack Research

**Domain:** Performance milestone v2.0 "k=21 Counting Parity" — existing Rust k-mer toolkit (CLI + PyO3, shared core, `.rkdb` v2)
**Researched:** 2026-11-11
**Confidence:** MEDIUM overall — version/MSRV facts HIGH (crates.io registry API + repo manifests + locked local source); performance-impact predictions MEDIUM/LOW until profiled on the real workload

## Headline Findings (read these first)

1. **The counting table is NOT hashed with ahash today — it uses SipHash-1-3.** Verified from the locked `dashmap-6.2.1` source: `DashMap<K, V, S = std::collections::hash_map::RandomState>` (lib.rs:45,89), and `KmerCounter::new` builds it with `with_capacity` (no custom hasher) at `src/hash/table.rs:162-166`. Rust 1.80.0's own std source states: "The default hashing algorithm is currently SipHash 1-3 … other hashing algorithms will outperform it for small keys such as integers." `grep ahash src/` returns **zero hits** — ahash 0.8 only reaches the *merge accumulator* via hashbrown 0.14's default `DefaultHashBuilder`. The milestone premise "ahash is current" holds for merge, not for the counter. **Swapping the counter to foldhash is the cheapest high-leverage experiment available** (~11x cheaper u64 hashing per published benchmarks: 9.09 ns SipHash-1-3 vs 0.79 ns foldhash on Xeon; foldhash 0.60 ns on Apple M2). [HIGH — local source + Rust 1.80.0 std source]
2. **The architecture lever (KMC-style signature partitioning) must be hand-rolled.** The entire current rust-seq SIMD minimizer stack violates MSRV 1.80: `simd-minimizers` 3.1.0 and 2.3.1 are **edition 2024** (requires Rust ≥1.85), `seq-hash` 0.2.1 is edition 2024, and `packed-seq` 5.1.1 depends on `wide` 1.7 (MSRV 1.89). The algorithm itself (KMC2/KMC3 signatures + super-kmers) is well documented and small. [HIGH for editions/MSRV — manifests fetched from GitHub at tags]
3. **No production Rust counting-quotient-filter crate exists.** `mqf` 1.0.0 (2019) is a dead single-release C++ FFI binding; Squeakr is C++. Disk-backed exact counting should reuse rustkmer's existing external-sort machinery (`streaming_merge.rs`, `prefix_cache_merge.rs`, `temp_lifecycle.rs`) — no new persistence engine, per constraint. [LOW-MEDIUM — search-based absence claim]
4. **Both benchmark prerequisites resolve today:** KMC v3.2.4 ships an **official `KMC3.2.4.mac.arm64.tar.gz` prebuilt** (GitHub releases, 2024-02-09; bioconda also has osx-arm64 build 2). There is no Homebrew formula (verified locally). `samply` 0.13.1 profiles on macOS **without sudo** (mach ports, not dtrace). jellyfish 2.3.1 confirmed at `/opt/homebrew/bin/jellyfish`. [HIGH — GitHub/anaconda APIs + local checks]

**Honest framing:** a hasher swap alone will not close a ~5x gap. At k=21 human scale the table holds billions of distinct k-mers (tens of GB); per-increment cache/TLB misses likely dominate. The hasher swap removes a real, verified ~11x per-op hash overhead; partitioning attacks the memory-locality problem. Profile first (samply), ship the hasher swap as the cheap first measurable step, then commit to partitioning. The Architecture researcher owns root-cause confirmation.

## Recommended Stack

### Core Additions (runtime)

| Technology | Version | MSRV verdict | Purpose | Why Recommended |
|------------|---------|--------------|---------|-----------------|
| foldhash | 0.2.0 (2025-08-23) | **1.60 declared — PASS** | Counter hasher (`fast::RandomState`) for both `CounterTable` arms | ~11x cheaper u64 hash vs the SipHash-1-3 in use today; default hasher of hashbrown 0.16 (ecosystem validation, already in lockfile transitively); pure-Rust, no global state, no allocator interaction — PyO3-safe; flows to CLI + Python via shared core |
| Hand-rolled KMC-style signature partitioning | n/a (no crate) | n/a — project code at 1.80 | Bin reads by signature → per-bin sort+count within RAM budget | The only MSRV-clean, portable path to KMC-class counting; current minimizer crates all fail MSRV 1.80 or require AVX2/NEON compile-time flags; reuses existing encoding + external-sort infra |
| std::arch SIMD kernels (NEON + SSE2/AVX2) | std — no crate | NEON stable since **1.59** — PASS | Encode/canonicalize hot loops, **only if profiling shows them hot** | Zero new deps; runtime dispatch via `is_x86_feature_detected!` keeps wheels/CI portable; aarch64 NEON covers Apple Silicon |
| mimalloc (OPTIONAL, CLI-only feature, default OFF) | 0.1.52 (2026-05-22) | undeclared; edition 2018 — likely PASS, verify on 1.80 | Allocator experiment behind `--features mimalloc` | Upstream explicitly supports Apple arm64 ("`-march=armv8.3` … M1 and better"); drop-in; measurable via samply; **never enabled for the PyO3 cdylib** |

### Development / Benchmark Tools

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| samply | 0.13.1 (MSRV 1.77) | CPU profiling on macOS aarch64, **no sudo** | `cargo install samply`; `samply record ./target/release/rustkmer …`; Firefox Profiler UI; `samply setup` once to enable attach-to-PID (self-signing, still no sudo). Cannot profile Apple-signed system binaries — irrelevant for cargo builds |
| KMC | 3.2.4 official `mac.arm64` tarball | Second reference comparator (BENCH-V2-01) | Download from GitHub releases; bioconda osx-arm64 as alternative; `ulimit -n 2048` before running; no Homebrew formula exists |
| criterion | keep 0.5 (dev-dep) | Micro-benchmarks | 0.7.0 is the newest MSRV-1.80-compatible release; **0.8.x requires 1.86 — do not upgrade past 0.7**. No upgrade needed for this milestone |
| /usr/bin/sample, /usr/bin/xctrace | system (verified present) | Zero-install profiling fallbacks | `sample <pid> 10` works on own processes without sudo; xctrace Time Profiler for deeper traces |
| /usr/bin/time -l | system | Peak-RSS gate per rep | Pair with phys_footprint (Activity Monitor / `footprint`) per the borrowed Chorus3 discipline: gate on max(rss, phys_footprint) |
| rustup toolchain 1.80 | 1.80.0 | True MSRV verification | **Not installed locally** (present: 1.75, 1.85, 1.99.1, stable, nightly-1.101 default). Install during the phase that adds deps; clippy `incompatible_msrv` alone does not catch dependency MSRV |

## Question 1 — Hashers for the counting table

**Verdict: foldhash 0.2.0 `fast::RandomState`. One construction-site change per `CounterTable` arm.**

| Crate | Version | MSRV (registry) | u64-key speed evidence | PyO3 safety | Verdict |
|-------|---------|-----------------|------------------------|-------------|---------|
| **foldhash** | 0.2.0 | **1.60 — PASS** | 0.79 ns hash-only (Xeon 8481C), 0.60 ns (M2); vs SipHash-1-3 9.09 ns, ahash 1.23 ns | Safe: no global state, no allocator use; small audited `unsafe` only for unaligned byte loads (integer path is safe arithmetic) | **USE** |
| rustc-hash (FxHash) | 2.1.3 | **1.77 — PASS** | Fastest raw u64 (0.67 ns Xeon / 0.41 ns M2) BUT weak avalanche: foldhash's `u64hibits` benchmark shows 67.72 ns/lookup for fxhash vs 1.77 ns foldhash on M2 | Safe | REJECT as counter hasher — 2-bit-packed k-mer keys are exactly the structured-input risk case; clustering lengthens probes in a multi-GB table |
| wyhash | 0.6.0 | undeclared; edition 2018; dep rand_core 0.9 (MSRV 1.63) — likely PASS | Portable scalar multiply-based; competitive but no published edge over foldhash | Safe | ACCEPTABLE ALTERNATIVE — no reason to prefer over foldhash's ecosystem validation |
| gxhash | 3.5.0 stable (4.0.0 in git) | undeclared | Fastest known when AES available | **Build-portability hazard** | **REJECT** — README at 3.5.0 tag: "Other platforms are currently not supported (there is no fallback). GxHash will not build on these platforms." Requires `target-cpu=native`/`+aes` at compile time → breaks plain-x86_64 CI and distributed wheels |
| seahash | 4.1.0 | undeclared | Slower than foldhash/ahash on integers | Safe | REJECT — last release 2021-01-16, dormant ~5 years, no speed edge |
| ahash (baseline) | 0.8.12 | 1.60 — PASS | 1.23 ns u64 (Xeon); AES-accelerated | Safe | Keep for the merge accumulator (hashbrown 0.14 default) — merge is out of scope this milestone |

**Contention vs hash cost — the explicit answer:** DashMap computes the hash *before* selecting/locking the shard, so a faster hasher reduces per-op CPU, **not** shard-lock hold time or contention. Contention is governed by shard count — default `(available_parallelism × 4).next_power_of_two()` (verified in dashmap-6.2.1 source) — tunable via `with_capacity_and_hasher_and_shard_amount`. At k=21 human scale, expect random-access cache/TLB misses on the huge table to dominate both; that is the partitioning case. Treat the hasher swap as a cheap, independently measurable step, not the parity fix. [MEDIUM — mechanism verified in source; workload split unprofiled]

**Integration point (exact):** `src/hash/table.rs:162-166` — the single width-selection site in `KmerCounter::new`:

```rust
// CounterTable arms gain a hasher type parameter (private enum — no public API change):
Dense(DashMap<u64, u32, foldhash::fast::RandomState>),
Wide(DashMap<u128, u32, foldhash::fast::RandomState>),
// construction:
CounterTable::Dense(DashMap::with_capacity_and_hasher(
    initial_capacity,
    foldhash::fast::RandomState::default(),
))
```

`foldhash::fast::RandomState` implements `BuildHasher` (verified in cached 0.2.0 source, `src/fast.rs:127-142`). Public signatures (`increment(u128)`, `get_all_counts() -> Vec<(u128, u32)>`) are untouched; `.rkdb` v2 write path unchanged.

**Golden-baseline safety:** `count` sorts output **by default** (`should_sort = !*no_sort`, D-09 in `src/cli/commands/count.rs:65-68`) — sorted `.rkdb` bytes are hasher-independent, so PCOUNT-04-style golden baselines hold. Only `--no-sort` output order changes, and it is already run-to-run nondeterministic with sharded DashMap. Any test asserting raw iteration order must sort first. [HIGH — local source]

## Question 2 — Minimizer / signature partitioning: hand-roll

**Verdict: hand-roll KMC-style signatures + super-kmers in the core. No crate dependency.**

Ecosystem surveyed (all versions from crates.io registry API, manifests from GitHub at tags):

| Crate | Version | MSRV / portability verdict | Notes |
|-------|---------|---------------------------|-------|
| simd-minimizers | 3.1.0 (2026-10-26) | **FAIL — edition 2024 (Rust ≥1.85)**; also requires AVX2 or NEON at compile time (x64: `target-cpu=x86-64-v3`), no runtime dispatch | Best-in-class algorithm (SEA 2025 paper; human-genome minimizers in ~4 s single-thread), MIT. v2.3.1 also edition 2024. **v1.4.0** (2025-09-03) is edition 2021 + wide 0.7 + packed-seq 3.2.1 (edition 2021, wide 0.7, mem_dbg 0.3) — *likely* 1.80-compatible but unverified (mem_dbg MSRV unchecked) and still AVX2/NEON-gated → at most an opt-in native-build experiment, never a default dep |
| seq-hash | 0.2.1 | **FAIL — edition 2024** | NtHasher etc.; transitive blocker |
| packed-seq | 5.1.1 | **FAIL — depends on wide 1.7 (MSRV 1.89)** | Transitive blocker |
| syncmers | 0.1.5 | dormant since 2022-12; ~115 recent downloads | REJECT |
| fracsync | 0.2.0 (2026-09) | niche, ~28 recent downloads | REJECT — sketching-focused, not counting |
| digest-rs | 0.1.0 (2025-05) | requires external C++ digest library | REJECT — C++ dependency against the established-stack constraint |
| nthash | 0.5.1 (2022-02) | rolling hash for DNA k-mers | Reference only — a rolling hash is ~30 lines to hand-roll if needed |
| debruijn | 0.3.4 (2021-09) | 10X Genomics; stale | Not evaluated deeply; age + likely API churn make it a poor bet [LOW] |

**Why hand-rolling is the right call, not NIH:**
1. **MSRV:** every current option fails 1.80 (edition 2024 is a hard compiler floor, not a lint).
2. **Portability:** simd-minimizers has no runtime SIMD dispatch — a default dependency would break plain-x86_64 CI and any distributed wheel. rustkmer ships both.
3. **Signatures ≠ plain minimizers:** KMC's bin-balancing trick is the *exclusion rules* (below), which minimizer libraries don't implement; you'd write the signature layer anyway.
4. **Small surface:** lexicographic m-mer minimum over the existing 2-bit encoding (`src/kmer/encoding.rs` already packs/unpacks), a sliding-window minimum (monotonic deque), and run-length super-kmer emission — a few hundred lines, fully testable against the existing exact-count goldens.

**KMC3 reference algorithm (for the Architecture researcher):** two stages — (1) split reads into several hundred disk **bins** by **signature**: the canonical minimal m-mer of each k-mer, *excluding* m-mers starting `AAA`/`ACA` or containing `AA` except at position 0 (better bin balance, fewer super-kmers); consecutive k-mers sharing a signature form a **super-kmer** stored as one substring; (2) process one bin at a time: sort (KMC3 uses RADULS radix sort) and count duplicates, entirely in a bounded RAM budget. KMC3's deltas over KMC2: faster gzipped-FASTQ I/O, improved signature→bin mapping, RADULS. Sources: KMC3 paper (Bioinformatics 2017;33:2759, arXiv:1701.08022), KMC2 paper (Bioinformatics 2015;31:1569). [MEDIUM — peer-reviewed + cross-checked]

**Integration points:** new `src/kmer/signature.rs` (m-mer minimizer + exclusion rules over packed u64) and a partitioned counting path beside `src/cli/commands/count.rs`'s chunked rayon loop; bin files via existing `tempfile`/`temp_lifecycle.rs` RAII patterns; per-bin sort+count reusing the external-sort patterns in `src/database/streaming_merge.rs` / `prefix_cache_merge.rs`; final `.rkdb` v2 write stays in `format.rs` (single source of truth). Both surfaces inherit via the shared core; `PyCounter` semantics preserved. **Memory discipline (borrowed from Chorus3, per milestone context): gate on max(rss, phys_footprint); never mmap spill files when RSS is the budget.**

## Question 3 — Disk-backed exact counting: reuse, don't add

**Verdict: no new structure crate and no new persistence engine. If evidence demands disk-backed counting, build KMC-style partition→sort→count on the existing stack.**

- **CQF crates:** none production-ready in Rust. `mqf` 1.0.0 (2019) = FFI to C++ Mixed Quotient Filter, single release, effectively dead. Squeakr (the CQF reference implementation) is C++ (splatlab/squeakr); wrapping it means a C++ build dependency + FFI maintenance — against the established-stack constraint. Exact-mode CQF also costs ~83–140 bits/k-mer (CPM 2021), which is not obviously better than a sorted 12-byte run for k=21. [LOW-MEDIUM — absence is search-based; bit-cost from published paper]
- **LMDB / RocksDB / sled / redb:** all violate the explicit "no new persistence engine" constraint, and per-key B-tree/LSM overhead is the wrong shape for billions of 12-byte records written once and read once. REJECT outright.
- **What rustkmer already has:** memory-bounded external-sort merge (`streaming_merge.rs`, 32 B/k-mer streaming charge), prefix-cache merge, header-only admission control, RAII temp dirs with TTL sweep (`temp_lifecycle.rs`), `byteorder` binary I/O, rayon. A partitioned counter is these pieces plus a bin writer and per-bin counting — the milestone's MINIM direction, not a new storage layer.
- **`.rkdb` v2 stays:** bins are *intermediate* files (process-unique temp dirs, already the merge pattern); the final database is still written by `format.rs`. No format bump needed for partitioned counting. [HIGH — constraint + local architecture]

## Question 4 — SIMD encoding / canonicalization

**Verdict: no new SIMD dependency by default. If profiling shows encoding hot, hand-write `std::arch` kernels (NEON + SSE2/AVX2 with runtime dispatch); `wide =0.7.33` is the unsafe-free fallback.**

| Option | Version | MSRV verdict | Notes |
|--------|---------|--------------|-------|
| std::simd (portable_simd) | nightly | **FAIL — nightly-only**, tracking rust#86656; stable docs mark everything experimental | Disqualified at MSRV 1.80 regardless of future stabilization |
| packed_simd | 0.3.9 | **FAIL — nightly-only + deprecated** | README: superseded by portable_simd; original crate unmaintained |
| simdutf8 | 0.1.5 | n/a | **Irrelevant** — UTF-8 *validation* only; DNA input is ASCII ACGT; does not do byte encoding/transcoding |
| wide (current) | 1.7.1 | **FAIL — MSRV 1.89** (entire 0.8.x–1.x line) | Do not add |
| **wide (pinned)** | **=0.7.33** (2025-06-21) | **PASS — MSRV 1.61** | Safe portable SIMD (SSE/NEON); older line, superseded — acceptable only as an unsafe-free convenience |
| fearless_simd | 1.2.0 | **FAIL — MSRV 1.89** | Do not add |
| macerator | 0.5.2 | **FAIL — MSRV 1.94** | Do not add |
| pulp | 0.22.3 | undeclared — unverified | Not needed; do not add without an MSRV check |
| **std::arch (chosen)** | std | **PASS — aarch64 NEON stable since 1.59** (releases.rs); x86 SSE2/AVX2 long stable | `unsafe` intrinsics + `is_x86_feature_detected!` runtime dispatch (safe-callable intrinsics only arrived 1.87 — `unsafe` blocks are fine at 1.80). Covers Apple Silicon (NEON baseline on aarch64-darwin) and x86_64 CI/wheels portably |

**Why this helps k=21 specifically (conditional):** encoding cost is per-base and k-independent, so it is *not* the obvious cause of a k-dependent 5x gap — but at k=21 the table op gets cheaper per useful byte, so the encode/canonicalize share of runtime grows. Profile before investing. Integration: `src/kmer/encoding.rs` (`encode_kmer_bytes_u128`) and `src/kmer/canonical.rs` (`canonical_kmer_u128`), behind `cfg(target_arch)` with a scalar fallback that the existing 1-vs-N/golden differentials already cover. Note `[profile.release] lto=true, codegen-units=1` already maximizes auto-vectorization chances — check the generated loop in samply before writing intrinsics. bio 2.0's parsing is scalar; a parser swap (needletail 0.7.4 / seq_io 0.3.4, MSRV 1.61) is a *surfaced decision* against the established-stack constraint, justified only if profiling shows FASTQ parsing hot — not a default addition. [MEDIUM]

## Question 5 — Allocators (PyO3-safe pattern)

**Verdict: optional `mimalloc` cargo feature, CLI binary only, default OFF. Skip jemalloc. Expect modest gains; measure.**

- **mimalloc 0.1.52** (libmimalloc-sys 0.1.49; upstream C mimalloc v3.6.1): MIT, edition 2018, **no MSRV declared** — verify on a real 1.80 toolchain during the phase. Upstream explicitly supports Apple arm64 ("On Apple arm64 the default is `-march=armv8.3` (which is supported on the M1 and better)"), is a drop-in malloc replacement, and "can co-exist with other allocators". Requires a C compiler (already needed for bzip2/xz2). [MEDIUM — manifests + upstream README]
- **The PyO3 safety rule (hard):** a `#[global_allocator]` declared in the **core rlib would propagate into the Python cdylib** and hijack CPython's allocator — disqualified. The declaration must live **only in the binary target** `src/main.rs`, behind `#[cfg(feature = "mimalloc")]`. The `pyo3` crate depends on the rlib, never on `main.rs`, so the feature can never reach `pyrustkmer`; keep root `default = []` and never enable the feature from `pyo3/Cargo.toml`. This is exactly the class of problem that killed rusty_alloc (also MSRV 1.87 — already rejected 2026-11-11, do not re-propose).
- **Why only "optional experiment":** DashMap counting performs few, large allocations (shard tables growing), not a malloc-storm; macOS libmalloc is already magazine-based. Allocator choice is unlikely to be the k=21 lever. Worth one measured A/B run *after* the hasher swap, kept only if it shows a real win on the human-scale workload. Dual-surface complexity is contained by the feature gate (CLI-only by construction; Python unaffected).
- **tikv-jemallocator 0.7.0:** edition 2018, no MSRV declared, jemalloc-sys 0.7.0. jemalloc runs on darwin-arm64 but the build is heavier and macOS track record weaker than mimalloc. REJECT as first choice; same binary-only feature rule would apply.

```toml
# root Cargo.toml
[features]
mimalloc = ["dep:mimalloc"]
[dependencies]
mimalloc = { version = "0.1.52", optional = true }
```
```rust
// src/main.rs ONLY — never src/lib.rs
#[cfg(feature = "mimalloc")]
#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;
```

## Question 6 — Profiling on macOS aarch64 without sudo

**Verdict: samply. It exists precisely for this use case.**

- **samply 0.13.1** (MSRV 1.77, dev tool — outside the crate MSRV gate anyway): on macOS it uses mach task ports + `DYLD_INSERT_LIBRARIES` injection into processes it launches — **no sudo, no dtrace, no SIP changes**. 1000 Hz default, on- and off-CPU samples per thread with timestamps, Firefox Profiler UI (flame graphs, per-thread views — ideal for separating rayon workers from the gzip reader thread). `cargo install samply`, then `samply record ./target/release/rustkmer count -k 21 …`. Attaching to an already-running PID needs `samply setup` once (self-signs with entitlements — still no sudo). Limitation: cannot profile Apple-signed system binaries (system python etc.) — irrelevant for cargo-built `rustkmer`. [MEDIUM — README + registry; mechanism cross-checked across sources]
- **Symbolication note:** add `debug = 1` to `[profile.release]` (line tables only; no perf cost) or a `[profile.profiling] inherits = "release"` with `debug = true`, so samply shows function names. The existing `profiling` cargo feature is unrelated bookkeeping — keep. `panic = "abort"` does not affect sampling.
- **Zero-install fallbacks (verified present):** `/usr/bin/sample <pid> <seconds>` (no sudo for own processes) and `/usr/bin/xctrace` (Instruments Time Profiler / Allocations templates).
- **cargo-flamegraph: AVOID on macOS** — dtrace-based, needs sudo and fights SIP; samply supersedes it here.
- **criterion:** keep 0.5 for micro-benches (hasher A/B, signature throughput). If an upgrade is ever wanted, **0.7.0 is the ceiling at MSRV 1.80** (0.8.x needs 1.86 — registry-verified).
- **Memory gate per rep:** `/usr/bin/time -l` (max RSS) plus phys_footprint (Activity Monitor / `footprint`); record max(rss, phys_footprint) per the pre-registered Chorus3-borrowed discipline. Never mmap spill files when RSS is the budget.

## Question 7 — KMC3 installability on macOS (BENCH-V2-01)

**Verdict: official prebuilt Apple Silicon tarball. No Homebrew formula exists.**

| Path | Status | Evidence |
|------|--------|----------|
| **GitHub release tarball (recommended)** | **Available: `KMC3.2.4.mac.arm64.tar.gz`** in refresh-bio/KMC v3.2.4 (published 2024-02-09) | GitHub releases API, verified 2026-11-11; ships `kmc`, `kmc_tools`, `kmc_dump` |
| bioconda | Available: kmc 3.2.4 **osx-arm64** build 2 (uploaded 2024-10-09); recipe builds from source with macOS patches | anaconda.org API, verified 2026-11-11; `conda create -n kmc -c bioconda kmc=3.2.4` or `pixi global install kmc` |
| Homebrew | **Does not exist** | `brew search kmc` → only `kmod`, `jmc` (verified locally) |
| Source build | Works with caveats | `make -f makefile_mac` (C++17; Homebrew g++), bundled **x86-64 zlib** in `kmc_core/libs` must be replaced on arm64; only needed if the tarball fails |

**Harness notes:** run `ulimit -n 2048` before KMC (macOS default open-file limit is too low for its temp bins). KMC counts canonical k-mers by default (matches rustkmer canonical mode; `-b` disables). Use `kmc_tools transform <db> dump` for exact-count differentials against `.rkdb` dumps. Wire into `scripts/bench/bench.py` as a third comparator with the same graceful-degradation ladder (absent → skip with recorded reason), same per-rep cache-state honesty as the jellyfish harness. Pin **3.2.4** (latest release; repo quiet since 2024). [HIGH — APIs + local checks]

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| gxhash (any version) | No non-AES fallback — "will not build" without `target-cpu` flags; breaks plain-x86_64 CI + wheels; MSRV undeclared | foldhash |
| seahash | Dormant since 2021-01; slower on integers | foldhash |
| rustc-hash/FxHash for the counter | Documented avalanche pathology on structured u64 keys (67.72 ns vs 1.77 ns lookup on M2) | foldhash `fast` |
| std::simd / packed_simd | Nightly-only; packed_simd additionally deprecated | std::arch + runtime detection (NEON stable 1.59) |
| simdutf8 | UTF-8 validation only — irrelevant to DNA 2-bit encoding | nothing (not a real candidate) |
| wide 0.8–1.x, fearless_simd, macerator | MSRV 1.89 / 1.89 / 1.94 — all fail the 1.80 gate | std::arch; or pinned `wide =0.7.33` (MSRV 1.61) if unsafe-free code is required |
| simd-minimizers 2.x/3.x + seq-hash + packed-seq 5.x | Edition 2024 (Rust ≥1.85) and/or wide 1.7 (MSRV 1.89); compile-time AVX2/NEON requirement kills portability | Hand-rolled KMC-style signatures; revisit only via an explicit MSRV-bump decision |
| syncmers, fracsync, digest-rs | Dormant / niche / C++ dependency respectively | Hand-rolled signatures |
| mqf / Squeakr FFI / any CQF crate | Dead 2019 FFI binding; C++ toolchain; no production Rust CQF | Existing external-sort machinery (partition→sort→count) |
| LMDB, RocksDB, sled, redb | Violates "no new persistence engine"; per-key overhead wrong shape for billions of 12-byte records | Flat binary bin runs + `byteorder` + `tempfile` |
| Global allocator in the core rlib or the PyO3 crate | Hijacks CPython's allocator via the cdylib — disqualified | CLI-binary-only `#[global_allocator]` behind a feature |
| tikv-jemallocator as first choice | Heavier build, weaker macOS record than mimalloc; same PyO3 hazard if mis-wired | mimalloc (optional, CLI-only) |
| rusty_alloc, Chorus3 saturating counters | Already researched & rejected 2026-11-11 (MSRV 1.87; breaks exact-u32 contract; 4^21 dense table ≥1 TiB) | Do not re-propose |
| criterion 0.8.x | MSRV 1.86 | Keep 0.5 (0.7.0 ceiling if ever needed) |
| hashbrown 0.16 as the direct dep / dashmap replacement | dashmap 6.2.1 pins hashbrown ^0.14.5; bumping the direct dep forks the table implementation for zero k=21 benefit (0.16 already present transitively — harmless) | Keep dashmap 6.2.1 + hashbrown 0.14; change only the hasher |
| needletail / seq_io parser swap by default | Against established-stack constraint; parsing not yet shown hot | bio 2.0 stays; swap only as a surfaced decision if profiling implicates FASTQ parsing |
| cargo-flamegraph on macOS | dtrace needs sudo + SIP concessions | samply |

## Alternatives Considered

| Recommended | Alternative | When the Alternative Makes Sense |
|-------------|-------------|----------------------------------|
| foldhash `fast` | foldhash `quality` | Only if a hasher consumer needs full avalanche (HyperLogLog/MinHash-style); counting tables do not — README says the extra quality is "almost never worth" the overhead for hash maps |
| foldhash | wyhash 0.6.0 | If foldhash shows a pathology on the real k-mer key distribution (unlikely; SMHasher-clean) — wyhash is portable and MSRV-fine |
| Hand-rolled signatures | pinned `simd-minimizers =1.4.0` (edition 2021, wide 0.7) | Only as an opt-in, native-CPU experiment after verifying mem_dbg 0.3 MSRV on 1.80; never a default dependency (AVX2/NEON compile-time gate) |
| Partition→sort→count on existing infra | Hand-rolled exact CQF | Only if profiling + literature show sort-based counting cannot hit the memory ceiling; much larger build risk — stage it as a later decision, not the opening move |
| std::arch kernels | `wide =0.7.33` | If the team rejects `unsafe` in the encoding path; costs a pinned-old-line dependency |
| mimalloc (CLI-only feature) | tikv-jemallocator | If mimalloc A/B shows a regression on the workload and jemalloc shows a win; same feature-gate pattern |
| KMC official tarball | bioconda osx-arm64 | If the harness already manages a conda env, or the tarball misbehaves on the host |

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| foldhash 0.2.0 (MSRV 1.60) | dashmap 6.2.1 (MSRV 1.65), Rust 1.80, PyO3 0.27.2 | `fast::RandomState: BuildHasher` — drop-in third type param; coexists with ahash 0.8 (merge path untouched) |
| dashmap 6.2.1 | hashbrown ^0.14.5 (pinned internally) | Do not bump the direct hashbrown dep; counter table implementation must not fork |
| wide =0.7.33 (MSRV 1.61) | Rust 1.80, aarch64 + x86_64 | Exact-pin (`=0.7.33`); 0.8.0+ jumps to MSRV 1.89 |
| mimalloc 0.1.52 | Rust 1.80 (unverified — no declared MSRV), macOS arm64, C compiler | Optional dep; feature never enabled from pyo3 crate; verify with `cargo +1.80 check --features mimalloc` |
| criterion 0.5 (dev) | Rust 1.80 | Upgrade ceiling 0.7.0 (MSRV 1.80); 0.8.x needs 1.86 |
| samply 0.13.1 (dev tool) | macOS aarch64, no sudo | Installed via `cargo install samply` with any toolchain; not a crate dependency |
| KMC 3.2.4 (external) | macOS arm64 (official tarball), `ulimit -n 2048` | Comparator binary only — never linked into rustkmer |
| Edition-2024 crates (simd-minimizers 2.3+/3.x, seq-hash 0.2) | **NOT compatible with Rust 1.80** | Edition 2024 requires Rust ≥1.85 — a hard compiler error, not a clippy lint; this is how MSRV violations sneak past `incompatible_msrv` |

## Installation

```bash
# Runtime (root crate) — the only default addition
cargo add foldhash@0.2.0

# Optional CLI-only allocator experiment (default OFF; never enable from pyo3/)
cargo add mimalloc@0.1.52 --optional
# then add: [features] mimalloc = ["dep:mimalloc"]  and the cfg-gated global allocator in src/main.rs

# Optional unsafe-free SIMD fallback (only if chosen over std::arch)
cargo add wide@=0.7.33

# Profiling (dev machine, not a crate dep)
cargo install samply            # 0.13.1
samply setup                    # one-time self-sign, enables attach-to-PID (no sudo)

# KMC comparator (BENCH-V2-01) — official Apple Silicon prebuilt
curl -LO https://github.com/refresh-bio/KMC/releases/download/v3.2.4/KMC3.2.4.mac.arm64.tar.gz
# extract into a git-ignored tools/ dir; harness records absence gracefully
ulimit -n 2048                  # required before running kmc

# True MSRV verification (toolchain absent locally today)
rustup toolchain install 1.80
cargo +1.80 check --all-targets
```

## Stack Patterns by Variant (profile-driven decision tree)

**If samply shows hash computation hot (SipHash frames in rayon workers):**
- Ship the foldhash swap first — one construction site, goldens protected by default-sorted output.
- Because the verified baseline is SipHash-1-3 (not ahash), expect a larger win than the "ahash→foldhash" framing suggested.

**If samply shows cache-miss/memory-bound table ops (expected at k=21 human scale):**
- Commit to hand-rolled signature partitioning (MINIM direction); per-bin working sets fit cache/RAM budget.
- Because the 5x gap is architectural; hasher and allocator wins are single-digit-to-modest percentages on a memory-bound loop.

**If allocation frames (malloc/free, shard growth) are hot:**
- A/B the `mimalloc` CLI feature; keep only on a measured win; Python surface untouched by construction.

**If encode/canonicalize loops are hot:**
- std::arch NEON (aarch64) + SSE2/AVX2 runtime-dispatched (x86_64) kernels in `src/kmer/`, scalar fallback retained for the differential tests.

**If gzip/FASTQ parsing is hot:**
- Surface a parser decision (needletail 0.7.4 / seq_io 0.3.4) explicitly — it touches the established-stack constraint; do not silently swap bio 2.0.

## Sources

**Primary, directly verified (HIGH):**
- Locked local source: `~/.cargo/registry/src/.../dashmap-6.2.1/src/lib.rs` (default `S = std RandomState`; `with_hasher` family; shard formula), `hashbrown-0.14.5/Cargo.toml` (default = ahash), `hashbrown-0.16.1/Cargo.toml` (default-hasher = foldhash 0.2), `foldhash-0.2.0/src/{lib,fast}.rs` (MSRV 1.60, `fast::RandomState: BuildHasher`, contained unsafe)
- rustkmer source: `src/hash/table.rs:162-166`, `src/cli/commands/count.rs` (D-09 sorted default), `grep ahash src/` (zero hits)
- Rust 1.80.0 std source via GitHub API: `library/std/src/collections/hash/map.rs` — "The default hashing algorithm is currently SipHash 1-3"
- Local system: Apple M4 Max / 128 GiB, jellyfish 2.3.1 present, no brew kmc formula, `/usr/bin/sample` + `/usr/bin/xctrace` present, toolchains (no 1.80 installed)
- crates.io registry API (versions + `rust_version` fields, fetched 2026-11-11): foldhash, wyhash, gxhash, rustc-hash, seahash, ahash, dashmap, mimalloc, libmimalloc-sys, tikv-jemallocator, simdutf8, wide (full version history), packed_simd, simd-minimizers (full history), packed_seq, seq-hash, syncmers, fracsync, debruijn, nthash, needletail, seq_io, criterion (history), samply, rand_core, pulp, fearless_simd, macerator
- GitHub releases API: refresh-bio/KMC v3.2.4 assets (mac.arm64 tarball); anaconda.org API: bioconda/kmc osx-arm64 build 2
- GitHub manifests at tags: simd-minimizers (master, v2.3.1, v1.4.0), packed-seq (master, v3.2.1), seq-hash, wyhash-rs, jemallocator, gxhash (master + 3.5.0 README), mimalloc_rust, rust-lang/rust@1.80.0

**Web, cross-checked (MEDIUM):**
- https://github.com/orlp/foldhash — benchmarks (u64 ns figures, fxhash pathology), fast vs quality, DoS caveats
- https://github.com/ogxd/gxhash — hardware requirements, no-fallback statement (also at 3.5.0 tag)
- https://github.com/rust-seq/simd-minimizers — AVX2/NEON requirement, super-kmers/syncmers, performance, paper
- https://github.com/microsoft/mimalloc — platform support incl. Apple arm64, drop-in/coexistence, v3.6.1
- https://github.com/mstange/samply — mach-port mechanism, no-sudo flow, `samply setup`, limitations
- https://doc.rust-lang.org/std/simd/index.html + rust-lang/rust#86656 — portable SIMD nightly status
- https://releases.rs/docs/1.59.0/ — "armv8 neon intrinsics for aarch64" stabilized
- KMC3 paper https://academic.oup.com/bioinformatics/article/33/17/2759/3796399 + arXiv:1701.08022; KMC2 signature rules cross-checked via https://pmc.ncbi.nlm.nih.gov/articles/PMC6280066/
- http://bioconda.github.io/recipes/kmc/README.html + bioconda-recipes meta.yaml — osx-arm64, source-build recipe

**Web, single-round (LOW — flagged in text):**
- CQF-crate absence (search round: only mqf 2019 FFI + C++ Squeakr found); debruijn suitability; pulp MSRV

---
*Stack research for: rustkmer v2.0 k=21 Counting Parity*
*Researched: 2026-11-11*
