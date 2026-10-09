# rustkmer

## What This Is

rustkmer is a high-performance k-mer counting and querying toolkit written in Rust. It ships through two independent entry points that share a single core library: a CLI binary (`rustkmer`, via clap) and a Python extension module (`pyrustkmer`, via PyO3). Both surfaces read and write the same custom binary `.rkdb` format. It targets bioinformaticians who need to count, query, and merge k-mers at genome scale — either from the command line in pipelines or from Python notebooks/scripts.

## Core Value

Count, query, and merge k-mers at genome scale within practical memory — fast and lean enough to compete with best-in-class tools (KMC / Jellyfish class), from both the CLI and Python.

## Requirements

### Validated

<!-- Shipped and relied upon. Inferred from existing code (see .planning/codebase/). -->

- ✓ CLI: `count`, `query`, `stats`, `dump`, `merge`, `fuzzy-query`, `fuzzy-query-batch`, `prefix-query` — existing
- ✓ Python bindings `pyrustkmer` (PyO3): `PyDatabase`, `PyCounter`, `PyFuzzyQuery`, `PyPrefixQuery`, `PyFormatter` — existing
- ✓ Custom binary `.rkdb` format (magic `RKDB`, version 2; 42-byte header + 20-byte entries) — existing
- ✓ Memory-mapped reads and streaming / prefix-cache external-sort merge for large databases — existing
- ✓ `u128` k-mer encoding (k ≤ 64), canonicalization (`min(kmer, revcomp)`) — existing
- ✓ Fuzzy matching (wildcard expansion + Hamming-distance mutation) and sorted-prefix lookup — existing

### Active

<!-- Current milestone: performance. Hypotheses until shipped and benchmarked. -->

- [ ] Counting at human-genome scale is competitive with a reference tool (KMC / Jellyfish) in speed and/or memory
- [ ] Merging at human-genome scale is competitive with a reference tool in speed and/or memory
- [ ] Both the CLI and `pyrustkmer` deliver the gains (single Rust core; neither surface regresses)
- [ ] A reproducible benchmark harness on real human-scale Illumina WGS data (CRR1936095) — supplemented by synthetic inputs where needed — guards against regressions (CI)
- [ ] Memory footprint is bounded so human-scale count/merge runs within practical RAM

### Out of Scope

<!-- Explicit boundaries for this round. -->

- New user-facing features / new commands — this round is performance, not feature expansion; would dilute focus
- Rewriting the `.rkdb` format from scratch — format stays compatible; a bump is a surfaced decision only if a specific win demands it
- Non-performance tech debt as the milestone's spine (committed backup files, dead PyO3 modules, orphaned `merge_tests.rs`, god-module splits that don't touch hot paths) — tracked in `.planning/codebase/CONCERNS.md`, cleaned opportunistically when the relevant code is touched, not pursued for its own sake this round
- UI / visualization — N/A (CLI + library)
- Query / prefix-query / fuzzy-query micro-optimization — the user's stated bottleneck is counting and merging, not lookups

## Context

**Current state (v0.5.0, brownfield).** The codebase is fully mapped under `.planning/codebase/` (STACK, ARCHITECTURE, CONCERNS, STRUCTURE, CONVENTIONS, TESTING, INTEGRATIONS). This milestone builds on that baseline.

**Counting — the primary lever.** Phase 2 (Parallel Counting) shipped: the counter is now `dashmap::DashMap<u128, u32>` (sharded, atomic per-key increments — no global write lock) and the per-record loop runs multi-core via rayon chunked `par_iter`, with thread count configurable through `--threads` / `RUSTKMER_THREADS` (default = all cores; precedence `--threads` > `RUSTKMER_THREADS` > `RAYON_NUM_THREADS` > num_cpus) and the GIL released in `pyrustkmer.PyCounter` via `py.detach`. The hardcoded `num_threads = 1` and `parking_lot::RwLock<HashMap>` contention are gone; both the CLI and Python inherit the speedup through the shared core, and a `--threads 1`-vs-`N` differential test proves counts stay identical to the sequential path (PCOUNT-04). What remains is **denser storage** — `u128` still doubles memory for the common k ≤ 32 case that fits in `u64`, so a human genome (~3 Gbp → ~2.5–3 B distinct k-mers for typical k) still demands ~100 GB+ of RAM today. ✅ u64 packing for k ≤ 32 shipped in Phase 3 (DENSE-01..03: `DashMap<u64, u32>` counting table, ~0.5× table memory measured, `.rkdb` v2 byte-identical, canonicalization parity proven); a minimizer/signature-partitioned or counting-quotient-filter structure (à la KMC) is v2.

**Merging — the secondary lever.** ✅ Phase 3 (Memory Safety) shipped: merge now defaults to the bounded path. Header-only estimation + admission control routes oversized merges to streaming (32 B/k-mer) or prefix-cache external sort instead of the all-in-memory route (96 B/k-mer); `--max-memory` / `max_memory=` set the budget (shared `parse_memory_size` grammar, checked arithmetic, 1 TB ceiling); SIGKILLed merges are reclaimed by a TTL-gated sweep of process-unique `rustkmer-merge-*` dirs and loose chunk files; and `pyrustkmer.PyDatabase.merge` routes through the same bounded entry point (`merge_databases_to_path`) as the CLI. Peak RSS is chunk-bounded (default chunk = 50 M records ≈ 1.6 GB), verified live to 200 M records; UAT 28/28, security audit 51 threats closed.

**Reference comparators.** KMC (disk-backed, memory-efficient, minimizer-partitioned) and Jellyfish (in-memory, fast, lock-free counters) are the standard human-scale k-mer tools. Pinning which to compete against (or both) determines whether the milestone optimizes for memory efficiency or raw speed.

**Existing perf infrastructure.** `criterion` benchmarks exist (the `python_cli_comparison` bench is currently commented out in `Cargo.toml`); `.github/workflows/performance-regression.yml` is present. **Phase 1 (Foundation & Quality) shipped `.github/workflows/ci.yml`** — a merge gate running `cargo fmt --check`, `cargo clippy -D warnings`, `cargo test`, and the `maturin` wheel build on every PR (ubuntu + macOS matrix). Library code now emits through the `log` facade (no direct `println!`/`eprintln!`/`dbg!` outside `src/cli/`), the `.rkdb` write logic is consolidated to a single source of truth in `format.rs`, and user-facing library strings are English-only (CJK denied by a `syn`-based test). **Phase 2 (Parallel Counting) shipped** `dashmap`-backed sharded counting + rayon per-record parallelism + the `--threads`/`RUSTKMER_THREADS`/GIL-release plumbing, with a `--threads 1`-vs-`N` commutativity differential proving parallel counts == sequential counts (PCOUNT-04). The merge path still has untested error/cleanup branches (see CONCERNS.md) that become higher-risk once it is the default — these belong to Phase 3.

**Shared core.** Both entry points depend on the same `rustkmer` library crate; the PyO3 crate (`pyo3/`) wraps `rustkmer::hash`, `rustkmer::io`, `rustkmer::kmer`, `rustkmer::database`. Core-layer wins flow to both surfaces automatically.

**Benchmark dataset (real, human-scale).** Real Illumina WGS data is available locally at `/Users/forrest/Data/data/illumina/CRR1936095_r1.fq.gz.split/`: `CRR1936095` is a GSA-human human WGS sample, NovaSeq 150 bp paired-end, currently two split parts of read 1 (`part_001`, `part_006`, ~5.2 GB gzipped total; valid standard gzip). This sits outside the repo and is **not** committed — the benchmark harness references the path and degrades gracefully to smaller slices / synthetic inputs on machines without the data. Use it as the primary performance target; synthetic inputs fill in for CI matrix and edge cases.

## Constraints

- **Tech stack**: Rust 1.80+ stable, PyO3 0.27.2, existing dependency set (rayon, memmap2, hashbrown, bio, byteorder, parking_lot, flate2/bzip2/xz2) — work within the established stack rather than introducing a new persistence engine
- **Compatibility**: preserve the `.rkdb` v2 on-disk format and the public CLI / Python APIs unless a specific perf win justifies a breaking change — and then only after surfacing the tradeoff explicitly
- **Dual surface**: changes must benefit (or at least not regress) both the CLI and `pyrustkmer`; the shared core is the delivery vehicle
- **Memory**: human-genome-scale count/merge must fit within practical RAM; the concrete ceiling is set when the reference tool is pinned
- **Benchmark**: real human-scale Illumina WGS data (CRR1936095, 150 bp PE, ~5.2 GB gzipped r1 across split parts) is available locally and is the primary target; the harness must be reproducible, run in CI as a regression gate, and degrade to slices/synthetic inputs where the full dataset is absent
- **MSRV / Python policy inconsistency**: CLAUDE.md says Python 3.10+, `pyo3/pyproject.toml` says `>=3.11`, no enforced Rust MSRV — not blocking, but to be normalized as part of hardening

## Key Decisions

<!-- Decisions that constrain future work. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Performance (not features, not broad tech debt) is this milestone's focus | Counting + merging at human scale is memory-bound; the user wants competitiveness with reference tools | — Pending |
| Both CLI and Python are first-class surfaces | A single Rust core serves both; core-layer wins flow to both, and the user serves both audiences equally | — Pending |
| Breaking format/API changes are deferred to the point of decision | User prefers to preserve compatibility and weigh tradeoffs only when a concrete change demands it | — Pending |
| Reference comparator (KMC vs Jellyfish vs both) is pinned during requirements | Choice determines whether to optimize for memory-efficiency or raw speed, shaping the whole roadmap | — Pending |
| Dense `u64` width applies to the counting hot path only; merge accumulator / read path stays `u128`-wide (Phase 3, 03-06 D7) | DENSE-01 names counting memory; in-memory merge only runs when already under budget and its peak is charged honestly by the admission model | ✅ Phase 3 |
| Prefix-cache mixed-canonical merge capability preserved as-is (Phase 3, WR-04 residual / AR-03-6) | Changing merge outcomes for existing callers is a user-visible break; the residual is documented and developer-triaged, not silently "fixed" | ✅ Phase 3 |

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
*Last updated: 2026-10-09 after Phase 3 (Memory Safety) completion*
