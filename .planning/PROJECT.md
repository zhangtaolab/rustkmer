# rustkmer

## What This Is

rustkmer is a high-performance k-mer counting and querying toolkit written in Rust. It ships through two independent entry points that share a single core library: a CLI binary (`rustkmer`, via clap) and a Python extension module (`pyrustkmer`, via PyO3). Both surfaces read and write the same custom binary `.rkdb` format. It targets bioinformaticians who need to count, query, and merge k-mers at genome scale — either from the command line in pipelines or from Python notebooks/scripts. Since v1.0, counting and merging are performance-competitive at human-genome scale: multi-core lock-free counting, bounded-memory merging, and dense k ≤ 32 storage — measured faster and leaner than Jellyfish2 at k=31.

## Core Value

Count, query, and merge k-mers at genome scale within practical memory — fast and lean enough to compete with best-in-class tools (KMC / Jellyfish class), from both the CLI and Python.

## Current Milestone: v2.0 k=21 Counting Parity

**Goal:** Match or beat Jellyfish2 on human-scale k=21 counting — closing the BENCH-02 gap outright — on both the CLI and Python surfaces, with the approach chosen from profiling evidence rather than guesswork.

**Target features:**
- ✅ Deep research + profiling (done 2026-11-12): root cause measured — the gap is parallel-scaling efficiency (~3.5x), not decompression/encoding/data-structure; `--threads` is a silent no-op; evidence in `.planning/research/profiling/`
- **Stage A (spine, in-memory parallelism):** fix `--threads` → thread-local counters + end reduction (kill per-window global atomics) → shared counting engine (`src/count/engine.rs`, persistent workers + disjoint partitioned tables + overlapped producer/consumer) → rolling encode + bit-parallel revcomp → parallel output sort. Targets jellyfish parity on both surfaces.
- **D2 semantics unification:** one shared window-extraction function adopting CLI skip-N semantics (Python output changes on N-reads, user-accepted)
- KMC3 comparison as a second validation reference (BENCH-V2-01, exact-count flags)
- Exact-count contract preserved: 1-vs-N + old-vs-new differentials + golden baselines prove byte-identical counts; `.rkdb` v2 byte-identity
- Regression gate: standing slice bench + parity gate + CI baselines, no performance regression
- **Stage B (CONDITIONAL, D3):** hand-rolled minimizer/signature partitioning + disk-backed bins — the memory-ceiling/KMC3-RAM lever; gated on Stage A missing parity or a memory ceiling Stage A cannot meet

## Requirements

### Validated

<!-- Shipped and relied upon. Inferred from existing code (see .planning/codebase/). -->

- ✓ CLI: `count`, `query`, `stats`, `dump`, `merge`, `fuzzy-query`, `fuzzy-query-batch`, `prefix-query` — existing
- ✓ Python bindings `pyrustkmer` (PyO3): `PyDatabase`, `PyCounter`, `PyFuzzyQuery`, `PyPrefixQuery`, `PyFormatter` — existing
- ✓ Custom binary `.rkdb` format (magic `RKDB`, version 2; 42-byte header + 20-byte entries) — existing
- ✓ Memory-mapped reads and streaming / prefix-cache external-sort merge for large databases — existing
- ✓ `u128` k-mer encoding (k ≤ 64), canonicalization (`min(kmer, revcomp)`) — existing
- ✓ Fuzzy matching (wildcard expansion + Hamming-distance mutation) and sorted-prefix lookup — existing
- ✓ Reproducible benchmark harness on human-scale Illumina WGS data with synthetic-input CI degradation ladder (`scripts/bench/bench.py` + `benchmark.yml` gate + committed per-platform baselines; milestone run on user-approved substitute CRR2044018, CRR1936095 re-runnable via `--input`) — v1.0 (Phase 4)
- ✓ Memory footprint bounded so human-scale count/merge runs within practical RAM (merge admission-controlled + streaming; counting measured 55.2 GiB at k=31 human-scale) — v1.0 (Phases 3–4)
- ✓ CI merge gate (fmt / clippy `-D warnings` / test / pyo3 wheel build, 3-OS) + library output through the `log` facade + single-source `.rkdb` write in `format.rs` + English-only strings enforced by a syn-based CJK gate — v1.0 (Phase 1, FOUND-01..04)
- ✓ Multi-core lock-free counting: DashMap sharded table + rayon chunked per-record parallelism, `--threads` / `RUSTKMER_THREADS` precedence chain, GIL release in `PyCounter` — v1.0 (Phase 2, PCOUNT-01..03)
- ✓ Parallel-count correctness proven identical to sequential: 1-vs-N differentials against committed golden baselines across the k/canonical matrix — v1.0 (Phase 2, PCOUNT-04)
- ✓ Bounded-memory merge: header-only admission control (96 B/k-mer in-memory charge), streaming / prefix-cache routing, RAII temp lifecycle + TTL sweep, shared entry point for CLI and `PyDatabase.merge` — v1.0 (Phase 3, MERGE-01..04)
- ✓ Dense `u64` counting storage for k ≤ 32 (~0.52× table bytes/entry measured on 4M-entry counters) with `.rkdb` v2 byte-identical and canonicalization parity proven — v1.0 (Phase 3, DENSE-01..03)
- ✓ Counting competitive with Jellyfish2 at human scale, k=31: 494 s @ 55.2 GiB vs 843 s @ 84.0 GiB — faster (−41%) AND leaner (−34% RSS); k=21 measured ~5x slower, accepted as a known gap at close — v1.0 (Phase 4, BENCH-02 partial)

### Active

<!-- v2.0 scope — confirmed by user 2026-11-11: k=21 counting parity first; merge untouched this round. -->

- [ ] k=21 counting parity with Jellyfish2 at human scale — match or beat (closes BENCH-02 outright); approach chosen from profiling evidence; candidate direction minimizer/signature partitioning (MINIM-01..03 staged in the v1.0 requirements archive)
- [ ] Root-cause profiling of the k=21 ~5x gap on the real workload — evidence before architecture (hashing overhead hypothesis from the Chorus3 small-k direct-address-vs-DashMap result needs validation on rustkmer's exact-u32 workload)
- [ ] KMC3 benchmark comparison (BENCH-V2-01) — the disk-backed, memory-efficient gold standard as a second validation reference
- [ ] Exact-count preservation proof — optimized counting stays byte-identical to the current counter (1-vs-N differentials + committed golden baselines, PCOUNT-04 discipline)
- [ ] Backlog 999.1–999.3 (pyo3 `build.rs` link args, stale site-packages `pyrustkmer` shadowing, `deferred-items.md` stale sweep claim) — opportunistic, only if touched by the perf work

### Out of Scope

<!-- Explicit boundaries for this round. -->

- Full-scale merge competitiveness — merge is already bounded-memory (v1.0 Phase 3); user chose counting-first 2026-11-11, merge comparison deferred to a later milestone
- New user-facing features / new commands — this round is performance, not feature expansion; would dilute focus
- Rewriting the `.rkdb` format from scratch — format stays compatible; a bump is a surfaced decision only if a specific win demands it
- Non-performance tech debt as the milestone's spine (committed backup files, dead PyO3 modules, orphaned `merge_tests.rs`, god-module splits that don't touch hot paths) — tracked in `.planning/codebase/CONCERNS.md`, cleaned opportunistically when the relevant code is touched, not pursued for its own sake this round
- UI / visualization — N/A (CLI + library)
- Query / prefix-query / fuzzy-query micro-optimization — the user's stated bottleneck is counting, not lookups
- Chorus3-style shortcuts (fixed-k saturating 2-bit counters, rusty_alloc global allocator) — researched 2026-11-11 and rejected: break the exact-u32 count contract, 4^21 dense table is 1 TiB+, rusty_alloc needs MSRV 1.87 and is disqualified for the PyO3 surface

## Context

**Current state (v2.0 started 2026-11-11; v1.0 shipped 2026-10-20).** v1.0: 4 phases, 31 plans, 19 requirements (18 satisfied; BENCH-02 partial by user acceptance). Human-scale verdict vs Jellyfish2 2.3.1 on CRR2044018: k=31 faster (494 vs 843 s) and leaner (55.2 vs 84.0 GiB); k=21 ~5x slower — the gap v2.0 exists to close. Post-v1.0 hygiene wave (2026-11-11, quick tasks): memmap2 ≥0.9.11 security floor, Cargo.lock tracking + CI `--locked`, MSRV 1.80 enforced in both manifests, Python ≥3.11 policy normalized, unused deps removed, Phase-04 review findings triaged (11 fixed / 4 already-fixed / 3 deferred IN-06/07/09), both crates' clippy gates green. The codebase map under `.planning/codebase/` predates v1.0; refresh during v2.0 research.

**v2.0 research input (2026-11-11, Chorus3 investigation).** Sibling lab repo Chorus3 vendors rustkmer but worked AROUND its unbounded DashMap counter, not on it: chorus-kmer is a fixed-k=17 direct-address table of 2-bit saturating counters (clips counts at 3) + disk-spill; rusty_alloc is a binary-only global allocator. None of it transfers to rustkmer's k=21 exact-u32 counting of read sets (saturating counts break the exact-count contract; a 4^21 dense table is 1 TiB at 2 bits / 16 TiB at u32; rusty_alloc needs MSRV 1.87 and a global allocator is disqualified for PyO3). The v2 direction stands: minimizer/signature partitioning or CQF. Borrowable discipline: pre-registered peak-gate measurement max(rss, phys_footprint); never mmap spill files when RSS is the budget. The ~5x small-k direct-address-vs-DashMap result corroborates hashing overhead as the k=21 bottleneck hypothesis — but it was measured at k=17 on a 135 Mbp reference with saturating semantics, so it MUST be validated on rustkmer's actual workload before the architecture is chosen.

**Counting — the primary lever.** Phase 2 (Parallel Counting) shipped: the counter is now `dashmap::DashMap<u128, u32>` (sharded, atomic per-key increments — no global write lock) and the per-record loop runs multi-core via rayon chunked `par_iter`, with thread count configurable through `--threads` / `RUSTKMER_THREADS` (default = all cores; precedence `--threads` > `RUSTKMER_THREADS` > `RAYON_NUM_THREADS` > num_cpus) and the GIL released in `pyrustkmer.PyCounter` via `py.detach`. The hardcoded `num_threads = 1` and `parking_lot::RwLock<HashMap>` contention are gone; both the CLI and Python inherit the speedup through the shared core, and a `--threads 1`-vs-`N` differential test proves counts stay identical to the sequential path (PCOUNT-04). What remains is **denser storage** — `u128` still doubles memory for the common k ≤ 32 case that fits in `u64`, so a human genome (~3 Gbp → ~2.5–3 B distinct k-mers for typical k) still demands ~100 GB+ of RAM today. ✅ u64 packing for k ≤ 32 shipped in Phase 3 (DENSE-01..03: `DashMap<u64, u32>` counting table, ~0.5× table memory measured, `.rkdb` v2 byte-identical, canonicalization parity proven); a minimizer/signature-partitioned or counting-quotient-filter structure (à la KMC) is v2.

**Merging — the secondary lever.** ✅ Phase 3 (Memory Safety) shipped: merge now defaults to the bounded path. Header-only estimation + admission control routes oversized merges to streaming (32 B/k-mer) or prefix-cache external sort instead of the all-in-memory route (96 B/k-mer); `--max-memory` / `max_memory=` set the budget (shared `parse_memory_size` grammar, checked arithmetic, 1 TB ceiling); SIGKILLed merges are reclaimed by a TTL-gated sweep of process-unique `rustkmer-merge-*` dirs and loose chunk files; and `pyrustkmer.PyDatabase.merge` routes through the same bounded entry point (`merge_databases_to_path`) as the CLI. Peak RSS is chunk-bounded (default chunk = 50 M records ≈ 1.6 GB), verified live to 200 M records; UAT 28/28, security audit 51 threats closed.

**Reference comparators.** KMC (disk-backed, memory-efficient, minimizer-partitioned) and Jellyfish (in-memory, fast, lock-free counters) are the standard human-scale k-mer tools. Pinning which to compete against (or both) determines whether the milestone optimizes for memory efficiency or raw speed.

**Existing perf infrastructure.** `criterion` benchmarks exist (the `python_cli_comparison` bench is currently commented out in `Cargo.toml`); `.github/workflows/performance-regression.yml` is present. **Phase 1 (Foundation & Quality) shipped `.github/workflows/ci.yml`** — a merge gate running `cargo fmt --check`, `cargo clippy -D warnings`, `cargo test`, and the `maturin` wheel build on every PR (ubuntu + macOS matrix). Library code now emits through the `log` facade (no direct `println!`/`eprintln!`/`dbg!` outside `src/cli/`), the `.rkdb` write logic is consolidated to a single source of truth in `format.rs`, and user-facing library strings are English-only (CJK denied by a `syn`-based test). **Phase 2 (Parallel Counting) shipped** `dashmap`-backed sharded counting + rayon per-record parallelism + the `--threads`/`RUSTKMER_THREADS`/GIL-release plumbing, with a `--threads 1`-vs-`N` commutativity differential proving parallel counts == sequential counts (PCOUNT-04). The merge path still has untested error/cleanup branches (see CONCERNS.md) that become higher-risk once it is the default — these belong to Phase 3.

**Shared core.** Both entry points depend on the same `rustkmer` library crate; the PyO3 crate (`pyo3/`) wraps `rustkmer::hash`, `rustkmer::io`, `rustkmer::kmer`, `rustkmer::database`. Core-layer wins flow to both surfaces automatically.

**Benchmark dataset (real, human-scale).** Real Illumina WGS data is available locally at `/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/`: `CRR1936095` is a GSA-human human WGS sample, NovaSeq 150 bp paired-end, currently two split parts of read 1 (`part_001`, `part_006`, ~5.2 GB gzipped total; valid standard gzip). This sits outside the repo and is **not** committed — the benchmark harness references the path and degrades gracefully to smaller slices / synthetic inputs on machines without the data. Use it as the primary performance target; synthetic inputs fill in for CI matrix and edge cases.

## Constraints

- **Tech stack**: Rust 1.82+ stable, PyO3 0.27.2, existing dependency set (rayon, memmap2, hashbrown, bio, byteorder, parking_lot, flate2/bzip2/xz2) — work within the established stack rather than introducing a new persistence engine
- **Compatibility**: preserve the `.rkdb` v2 on-disk format and the public CLI / Python APIs unless a specific perf win justifies a breaking change — and then only after surfacing the tradeoff explicitly
- **Dual surface**: changes must benefit (or at least not regress) both the CLI and `pyrustkmer`; the shared core is the delivery vehicle
- **Memory**: human-genome-scale count/merge must fit within practical RAM; the concrete ceiling is set when the reference tool is pinned
- **Benchmark**: real human-scale Illumina WGS data (CRR1936095, 150 bp PE, ~5.2 GB gzipped r1 across split parts) is available locally and is the primary target; the harness must be reproducible, run in CI as a regression gate, and degrade to slices/synthetic inputs where the full dataset is absent
- **Version policy (normalized 2026-11-11; MSRV raise user-approved 2026-11-12)**: Rust MSRV 1.82 enforced via `rust-version = "1.82"` in both `Cargo.toml` manifests; Python floor 3.11+ per `pyo3/pyproject.toml`. New code must use only APIs available at 1.82 (the `clippy::incompatible_msrv` gate is active under `-D warnings`)

## Key Decisions

<!-- Decisions that constrain future work. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Performance (not features, not broad tech debt) is this milestone's focus | Counting + merging at human scale is memory-bound; the user wants competitiveness with reference tools | ✅ v1.0 (scope held; 18/19 requirements satisfied, BENCH-02 partial) |
| Both CLI and Python are first-class surfaces | A single Rust core serves both; core-layer wins flow to both, and the user serves both audiences equally | ✅ v1.0 (both surfaces share the bounded core; no Python regression) |
| Breaking format/API changes are deferred to the point of decision | User prefers to preserve compatibility and weigh tradeoffs only when a concrete change demands it | ✅ v1.0 (`.rkdb` v2 unchanged; public APIs preserved) |
| Reference comparator (KMC vs Jellyfish vs both) is pinned during requirements | Choice determines whether to optimize for memory-efficiency or raw speed, shaping the whole roadmap | ✅ Jellyfish2 2.3.1 for v1 (KMC3 deferred to v2) |
| Milestone benchmark ran on substitute dataset CRR2044018 with honest per-rep cache-state recording (Phase 4, user-approved 2026-10-09) | CRR1936095 absent from host; sudo cold-cache purge unavailable — every rep records its true cache_state and the report states cold-cache PARTIALLY satisfied | ✅ Phase 4 (measured) |
| BENCH-02 verdict computed conservatively from recorded medians: NO overall (k=31 YES, k=21 ~5x slower) | A NO is a valid measured outcome; the acceptance decision belongs to the user | ⚠ Accepted as known gap at v1.0 close (user decision 2026-10-20) |
| BENCH-02 gap accepted as tech debt — ship v1.0 on the k=31 result; k=21 performance deferred to v2 | k=31 is faster AND leaner than jellyfish2; k=21 needs minimizer-class work (MINIM-01..03 staged) — an honest gap beats a tuned verdict | ⚠ Known gap, recorded in MILESTONES.md (user decision 2026-10-20) |
| Dense `u64` width applies to the counting hot path only; merge accumulator / read path stays `u128`-wide (Phase 3, 03-06 D7) | DENSE-01 names counting memory; in-memory merge only runs when already under budget and its peak is charged honestly by the admission model | ✅ Phase 3 |
| Prefix-cache mixed-canonical merge capability preserved as-is (Phase 3, WR-04 residual / AR-03-6) | Changing merge outcomes for existing callers is a user-visible break; the residual is documented and developer-triaged, not silently "fixed" | ✅ Phase 3 |
| v2.0 scope: k=21 counting parity first; merge untouched this round | User decision 2026-11-11 — the measured BENCH-02 NO is the k=21 counting gap; merge is already bounded-memory and full-scale merge comparison defers to a later milestone | — Pending |
| v2.0 acceptance: match or beat Jellyfish2 at human-scale k=21 | User decision 2026-11-11 — closes BENCH-02 outright; profiling later showed the gap is general (k=31 also ~5x under fair comparison), so the verdict covers both k | — Pending |
| v2.0 approach chosen from profiling evidence, not guesswork | User directive "需要认真调研" 2026-11-11 — deep research + root-cause profiling on the real workload precedes the architecture decision; Chorus3 shortcuts already researched and rejected | ✅ Research done 2026-11-12 (empirical, HIGH confidence) |
| D1: parallelism-first (Stage A) is the v2.0 spine; minimizer/disk-backed demoted to conditional Stage B | User-ratified 2026-11-12 on profiling evidence — the ~5x gap is ~3.5x parallel-scaling inefficiency (—threads no-op, 59% rayon spin-wait, per-window global atomics) × ~1.4x single-thread cost, NOT a data-structure problem; single-thread core already competitive with jellyfish | ✅ Ratified |
| D2: unify CLI/Python N-read semantics on CLI skip-N | User-ratified 2026-11-12 — CLI skip-N is what the jellyfish parity gate validated; Python's strip-N+join-flanks creates chimeric k-mers. Explicitly accepts Python output changes on N-containing reads (no silent change, WR-04 precedent) | ✅ Ratified |
| D3: BENCH-V2-01 (KMC3 comparison) stays in v2.0; minimizer architecture phase is conditional | User-ratified 2026-11-12 — minimizer/disk-backed is the memory-ceiling/KMC3-RAM lever, not the speed lever; gated on Stage A missing parity OR a memory ceiling Stage A cannot meet; descope/defer if Stage A hits parity and memory is acceptable | ✅ Ratified |
| MSRV raised 1.80 → 1.82 (Phase 5, 2026-11-12) | User-ratified — the locked dependency graph requires rustc 1.81/1.82 (half@2.7.1, indexmap@2.13.0, proptest@1.9.0), so the 1.80 floor was unsatisfiable; raising the floor (not pinning deps) keeps the graph intact. One behavior-preserving clippy `needless_range_loop` fix (prefix_cache_merge.rs) accompanied it | ✅ Ratified (both crates clippy green under 1.82; WINDOWS 19/20 closed) |
| Phase 5 harness: atomics dominate contention (contention_evidence, 18M-distinct subslice) | Measured global-atomics attribution 120.22 ns (~115% of the shared-vs-local gap); bandwidth inconclusive at this scale (honest, not clamped). Confirms per-window global atomics as the Phase 7 engine target | ✅ Measured (re-measure at DRAM scale if decision-critical) |
| Phase 6 delivered the parallelism lever: `--threads` fixed + thread-local counters + rolling encode | Measured on a fresh 1.82 binary: real 4M slice t1 142.54s → 57.16s (ratio 0.401), t4 34.98s / t16 26.96s; synthetic t1 18.77→13.59s; scaling gate GREEN (t4 1.63x, t16 2.02x); counts byte-exact; per-worker-local peak RSS rose (slice t4/t16 25 GiB vs 17 GiB) — the partitioned-memory cost is explicitly assigned to Phase 7's engine design | ✅ Exceeded the phase goal (verification 20/20 after a concurrent-total gap fix) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-11-12 after Phase 6 (Parallelism Correctness & Hot Path)*
