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
- [ ] A reproducible benchmark harness on synthetic human-scale workloads guards against regressions (CI)
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

**Counting — the primary lever.** The count command currently processes files single-threaded (`num_threads = 1` in `src/cli/commands/count.rs`) and accumulates into a `HashMap<u128, u32>` behind a `parking_lot::RwLock` (`src/hash/table.rs`). At ~30–40 bytes per distinct k-mer, a human genome (~3 Gbp → ~2.5–3 B distinct k-mers for typical k) demands ~100 GB+ of RAM today. Two structural wins are visible: (a) real parallel counting (sharded/partitioned to avoid lock contention), and (b) denser storage — `u128` doubles memory for the common k ≤ 32 case that fits in `u64`, and a minimizer/signature-partitioned or counting-quotient-filter structure (à la KMC) could go much further.

**Merging — the secondary lever.** `merge_databases_inmemory` (`src/database/format.rs`) loads every k-mer of every input into one hashmap, defeating the streaming/external-sort machinery (`src/database/streaming_merge.rs`, `src/database/prefix_cache_merge.rs`) that already exists alongside it. There is no memory-budget admission control before allocation, so a large merge OOMs the process. Routing merge through the streaming path by default and adding admission control is a clear, largely algorithmic win.

**Reference comparators.** KMC (disk-backed, memory-efficient, minimizer-partitioned) and Jellyfish (in-memory, fast, lock-free counters) are the standard human-scale k-mer tools. Pinning which to compete against (or both) determines whether the milestone optimizes for memory efficiency or raw speed.

**Existing perf infrastructure.** `criterion` benchmarks exist (the `python_cli_comparison` bench is currently commented out in `Cargo.toml`); `.github/workflows/performance-regression.yml` is present; there is no Rust CI workflow running `cargo test` / `clippy` / `fmt`. The merge path has untested error/cleanup branches (see CONCERNS.md) that become higher-risk once it is the default.

**Shared core.** Both entry points depend on the same `rustkmer` library crate; the PyO3 crate (`pyo3/`) wraps `rustkmer::hash`, `rustkmer::io`, `rustkmer::kmer`, `rustkmer::database`. Core-layer wins flow to both surfaces automatically.

## Constraints

- **Tech stack**: Rust 1.80+ stable, PyO3 0.27.2, existing dependency set (rayon, memmap2, hashbrown, bio, byteorder, parking_lot, flate2/bzip2/xz2) — work within the established stack rather than introducing a new persistence engine
- **Compatibility**: preserve the `.rkdb` v2 on-disk format and the public CLI / Python APIs unless a specific perf win justifies a breaking change — and then only after surfacing the tradeoff explicitly
- **Dual surface**: changes must benefit (or at least not regress) both the CLI and `pyrustkmer`; the shared core is the delivery vehicle
- **Memory**: human-genome-scale count/merge must fit within practical RAM; the concrete ceiling is set when the reference tool is pinned
- **Benchmark**: synthetic human-scale workloads are acceptable; the harness must be reproducible and run in CI as a regression gate
- **MSRV / Python policy inconsistency**: CLAUDE.md says Python 3.10+, `pyo3/pyproject.toml` says `>=3.11`, no enforced Rust MSRV — not blocking, but to be normalized as part of hardening

## Key Decisions

<!-- Decisions that constrain future work. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Performance (not features, not broad tech debt) is this milestone's focus | Counting + merging at human scale is memory-bound; the user wants competitiveness with reference tools | — Pending |
| Both CLI and Python are first-class surfaces | A single Rust core serves both; core-layer wins flow to both, and the user serves both audiences equally | — Pending |
| Breaking format/API changes are deferred to the point of decision | User prefers to preserve compatibility and weigh tradeoffs only when a concrete change demands it | — Pending |
| Reference comparator (KMC vs Jellyfish vs both) is pinned during requirements | Choice determines whether to optimize for memory-efficiency or raw speed, shaping the whole roadmap | — Pending |

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
*Last updated: 2026-06-30 after initialization*
