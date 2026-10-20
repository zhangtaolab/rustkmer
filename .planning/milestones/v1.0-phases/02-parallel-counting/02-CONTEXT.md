# Phase 2: Parallel Counting - Context

**Gathered:** 2026-07-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Make k-mer counting multi-core and lock-free so throughput scales with CPU count, across **both** the CLI `count` command and `pyrustkmer`'s `PyCounter` (shared `rustkmer` core), while producing results byte-for-byte identical in *counts* to the current sequential path.

**WHAT is locked by `REQUIREMENTS.md` PCOUNT-01..04** (no `02-SPEC.md` exists — REQUIREMENTS is the WHAT-authority for this phase; this document locks the HOW):
- PCOUNT-01: remove hardcoded `num_threads = 1`; use all cores by default; configure via `--threads` / `RUSTKMER_THREADS`
- PCOUNT-02: replace `RwLock<HashMap>` with a sharded concurrent map (dashmap) — throughput scales without lock contention
- PCOUNT-03: `pyrustkmer.PyCounter` delivers the same parallel speedup via the shared core
- PCOUNT-04: parallel counting produces results identical (counts) to the sequential path

**In scope:** the count hot-path (`src/hash/table.rs` counter + `src/cli/commands/count.rs` per-record loop + `pyo3/src/counter.rs`), thread-count plumbing (CLI flag + env + PyO3 kwarg), and correctness regression tests. Memory *density* (u64 packing) and merge bounding stay in Phase 3.

**Out of scope (per ROADMAP/REQUIREMENTS):** query/prefix/fuzzy paths, merge bounding, dense u64 storage (Phase 3), the benchmark harness (Phase 4), new user-facing commands, distributed/cluster counting.

</domain>

<decisions>
## Implementation Decisions

### Parallelization Strategy (Work Partitioning)
- **D-01: Intra-file, per-record parallelism.** rayon parallelizes across reads/records *within* each file (encode → canonicalize → increment). This is the only strategy that yields near-core-count speedup on CRR1936095, which ships as just 2 split parts — per-file parallelism would cap at ~2× and collapse to single-threaded on one large file. Work happens in `process_fastq_file` / `process_fasta_file`'s record loops.
- **D-02: Do NOT parallelize gzip decompression in Phase 2.** Counting + parsing are parallelized; decompression stays single-threaded (`flate2`). Phase 4's benchmark measures whether decompression caps the speedup; if it does, "split-on-gzip-member parallel gunzip" becomes its own backlog phase. Keeps Phase 2 focused and low-risk.
- **D-03: Global record pool across files.** All reads from all input files flow into one parallel count over one sharded map; output is a single merged result (matches the existing multi-file `count` semantics). Maximizes core utilization regardless of file count; no per-file output is needed today.

### Concurrent Counter Structure
- **D-04: `dashmap` (new dependency).** PCOUNT-02 names it explicitly; it is mature, battle-tested, internally sharded (per-shard lock), and offers an atomic `entry()` upsert. `dashmap` is not a "persistence engine," so it does not violate the PROJECT.md stack-floor constraint, but it IS a new dependency and therefore must pass the Phase 1 `clippy -D warnings` gate on both crates. (Note: `dashmap` 6.x reuses `hashbrown 0.14` — no duplicate hashbrown versions in the tree.)
- **D-05: Public API of `KmerCounter` is preserved.** The swap is internal: `table: RwLock<HashMap<u128,u32>>` → `DashMap<u128,u32>`. The public surface (`increment`, `get_count`, `get_all_counts`, `get_top_n`, `merge`, stats accessors) stays identical, so `count.rs` and `pyo3/src/counter.rs` call-sites do not change. `total_kmers`/`unique_kmers` stay as atomics.

### Thread Configuration UX
- **D-06: Default = all cores via a global rayon pool.** When neither flag nor env is set, thread count = `num_cpus` (satisfies PCOUNT-01 "all available CPU cores by default"). The chosen count is applied with `rayon::ThreadPoolBuilder::build_global()` so the `count` command and the existing `merge` rayon usage share one pool — simplest, fewest moving parts.
- **D-07: Precedence chain `--threads` > `RUSTKMER_THREADS` > `RAYON_NUM_THREADS` > all-cores.** The new `RUSTKMER_THREADS` wins; if unset, fall back to `RAYON_NUM_THREADS` so existing users who tune merge via that var are unaffected; if both unset, all cores. This unifies the new requirement with existing behavior without forcing migration.
- **D-08: `PyCounter` exposes `threads` (PCOUNT-03).** `PyCounter(k, canonical, threads=None)` — `None` means all cores, parity with CLI `--threads`. Counting runs inside `pyo3::allow_threads` (GIL released) so the rayon worker threads actually run in parallel; without GIL release the speedup would not materialize under Python.

### Determinism & Correctness
- **D-09: `--sort` becomes the DEFAULT (user decision, overrides the "keep optional" recommendation).** Sorted output is on by default; `--no-sort` disables it; the `--sort` flag is retained as an explicit alias for backward compatibility. Rationale: a sharded map's iteration order is non-deterministic, so default-sort guarantees reproducible output run-to-run and aligns rustkmer's default output with Jellyfish2's sorted output (fairer Phase 4 comparison).
  - **⚠ Flagged tradeoff (surfaced, accepted):** this *changes the existing CLI default* (today sort is opt-in) and adds a sort over the full k-mer set at human scale (~3B entries) on every run. The sort path already exists in `count.rs`; Phase 4's benchmark will measure the real cost. If the cost proves prohibitive, revisit via a fast-path/skip-sort-under-budget option — but the default-sorted contract stands unless that data forces a revisit. Downstream planner must preserve the `--sort`/`--no-sort` flag pair (don't delete `--sort`).
- **D-10: Correctness via golden-capture-first + `--threads 1`-vs-`N` differential + proptest.** Mirrors Phase 1's D-10 discipline: capture a counts baseline from the *current sequential* code BEFORE refactoring the counter; after, assert (a) `--threads 1` vs `--threads N` produce identical count maps (this directly catches lost-update / double-count bugs — addition is commutative, so any count divergence is a concurrency bug, not ordering), (b) output matches the pre-refactor baseline, and (c) proptest holds for random small inputs (counts deterministic regardless of thread count).

### Claude's Discretion
- **Shard count / hasher:** use `dashmap` defaults (internal ~4×num_cpus shards; default hasher). No hand-tuning unless the benchmark shows contention.
- **Overflow semantics:** preserve the current u32 count with error-on-`u32::MAX`-per-kmer behavior (`table.rs:75-80`) — required for PCOUNT-04 identical-results.
- **Flag mechanics for sort:** `should_sort = !no_sort`; keep `--sort` as a redundant-but-valid alias. Exact help text / arg attrs follow `args.rs` conventions.
- **`--threads` validation:** reject `< 1` with a clear error (mirror `InvalidKmerSize` style); report the resolved thread count in `-v/--verbose` output.
- **`RAYON_NUM_THREADS` fallback:** only consulted when both `--threads` and `RUSTKMER_THREADS` are unset.
- **Unsorted comparison in existing tests:** any test doing byte-comparison on *unsorted* output must switch to set/sorted comparison (sharded iteration order differs from the current `HashMap`). Golden coverage should span `k ∈ {21, 32, 64}` × canonical × multiple input sizes (echoing Phase 1's D-13 matrix).
- **Buffering granularity for intra-file parallelism:** bio's reader is sequential, so records must be buffered then `par_iter`'d (or read in chunks). Use bounded chunked buffering (not buffer-all) to avoid layering a second memory blowup on top of the u128 HashMap — exact chunk size is the planner's call.
- **Where encode/canonicalize runs:** on the worker side inside the rayon task (keeps the producer loop to read+parse only).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap (the WHAT authority)
- `.planning/REQUIREMENTS.md` §"Parallel Counting" — PCOUNT-01..04 definitions; §"Out of Scope" table (scope-creep guardrail); §Traceability (PCOUNT-* → Phase 2). Treat as the locked WHAT in lieu of a `02-SPEC.md`.
- `.planning/ROADMAP.md` §"Phase 2: Parallel Counting" — phase goal, 4 success criteria, the 4 seed plans (`02-01`..`02-04`).
- `.planning/PROJECT.md` §Context (counting is the primary lever; current `num_threads=1` + `RwLock<HashMap>`; ~100GB+ at human scale), §Constraints (existing-stack floor, dual-surface, Jellyfish2 is the v1 comparator), §Key Decisions.

### Prior phase (carry-forward discipline)
- `.planning/phases/01-foundation-quality/01-CONTEXT.md` — **D-10** golden-capture-before-refactor sequencing (Phase 2 D-10 reuses this), **D-13** coverage matrix (k×canonical×sorted), the CI clippy `-D warnings` gate (D-04..D-08), log-facade migration (count.rs still uses `eprintln!` legitimately under `src/cli/`).

### Codebase maps (grounding)
- `.planning/codebase/ARCHITECTURE.md` — `KmerCounter` threading model (`parking_lot::RwLock<HashMap>`, `num_threads=1`), data flow for Count, "Architectural Constraints → Threading".
- `.planning/codebase/CONCERNS.md` — `u128` memory doubling (Phase 3, not here), `hashbrown 0.14` two-majors-behind (relevant if dashmap interacts), dependency-bloat theme (justify the new dashmap dep), "No enforced MSRV".
- `.planning/codebase/STACK.md` — rayon / parking_lot / hashbrown / ahash / num_cpus already in the dep graph; release profile (`lto`, `codegen-units=1`, `panic="abort"`) to preserve when editing `Cargo.toml`.
- `.planning/codebase/TESTING.md` — `tests/common/mod.rs` factories, `tests/common/temp_files.rs` RAII + `temp_file!`/`temp_fasta!`, `tests/fixtures/` convention, inline `#[cfg(test)]` pattern, `proptest` dev-dep.

### Source hot-path (the integration points)
- `src/hash/table.rs` — `KmerCounter` (the `RwLock<HashMap<u128,u32>>` → `DashMap` swap; `increment` overflow semantics at `:75-80`; `_num_threads` param already a placeholder at `:44`).
- `src/cli/commands/count.rs` — `num_threads = 1` hardcode (`:121-123`), `process_fasta_file`/`process_fastq_file` per-record loops (the parallelization site), `--sort`/`--no_sort` + `should_sort` logic (`:47`), `output_text_format`/`output_binary_format` (`:264-270`).
- `src/cli/args.rs` — `Commands::Count` struct (where `--threads` is added; existing `validate_*` helpers as the validation pattern).
- `src/config/manager.rs` — env-var discovery (`RUSTKMER_` prefix) — where `RUSTKMER_THREADS` is read and the `RAYON_NUM_THREADS` fallback lives.
- `pyo3/src/counter.rs` — `PyCounter` wrapper (where the `threads` kwarg + `pyo3::allow_threads` GIL-release land for PCOUNT-03).
- `Cargo.toml` — `dashmap` added under `[dependencies]`; release profile preserved.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`rayon` is already a dependency** (used by `prefix_cache_merge.rs`, `streaming_merge.rs`) — `par_iter` / `ThreadPoolBuilder` available with no new dep. `num_cpus` comes along transitively with rayon.
- **`ahash`, `hashbrown`, `parking_lot` already in the stack** — relevant context for the dashmap choice and for any fallback design.
- **Phase 1 log facade + clippy gate** — count command's `eprintln!` under `src/cli/` is legitimate (exempt via `src/cli/mod.rs` `#![allow]`); new diagnostics should use the same pattern. The new `dashmap` dep must compile clean under `cargo clippy -D warnings` on both crates.
- **`tests/common/` factories + `temp_file!`/`temp_fasta!` + `tests/fixtures/`** — reuse for the golden/differential test scaffolding (D-10).
- **`proptest 1.5`, `tempfile`, `rand`/`rand_chacha` are dev-deps** — available for the property-based correctness tests (D-10).
- **`KmerCounter::new` already takes `_num_threads`** (`table.rs:44`, currently unused) — the API slot for thread count already exists; Phase 2 wires it up.

### Established Patterns
- **Dual-surface shared core:** counter changes in `src/hash/` flow to both `count.rs` and `pyo3/src/counter.rs` automatically (the delivery vehicle for PCOUNT-03).
- **Golden-capture-before-refactor (Phase 1 D-10):** the proven sequencing discipline — capture baseline FIRST, refactor SECOND. Phase 2 D-10 reuses it for the counter.
- **Coverage matrix (Phase 1 D-13):** `k ∈ {21,32,64}` × canonical × sorted/unsorted — echo for golden/differential coverage.
- **Env-layered config:** file + env (`RUSTKMER_`) + CLI flag, via thread-safe `ConfigManager` — `RUSTKMER_THREADS` follows this.

### Integration Points
- `src/hash/table.rs` — internal `table` field type swap; `increment` body rewrites to dashmap `entry().and_modify().or_insert()`.
- `src/cli/commands/count.rs` — `num_threads = 1` → resolved thread count (D-06/D-07); record loops → `par_iter`; default sort flip (D-09).
- `src/cli/args.rs::Commands::Count` — add `--threads` / `--no-sort` handling (the `--sort`/`--no-sort` pair already exists).
- `src/config/manager.rs` — `RUSTKMER_THREADS` env read + `RAYON_NUM_THREADS` fallback (D-07).
- `pyo3/src/counter.rs` — `PyCounter` gains `threads` kwarg; wrap counting in `pyo3::allow_threads` (D-08).
- `Cargo.toml` — `dashmap` dependency.

</code_context>

<specifics>
## Specific Ideas

- **Why intra-file is non-negotiable for this dataset:** CRR1936095's read-1 ships as only 2 split parts. Per-file parallelism would top out at ~2× and degrade to single-threaded on any single large file — directly failing PCOUNT-02's "scales with core count." Intra-file per-record parallelism is the only design that delivers the phase's goal on the real target data.
- **Why the 1-vs-N differential is the sharp correctness tool:** k-mer counting is just integer addition, which is commutative and associative. Therefore the final count for each k-mer is mathematically independent of threading — ANY divergence between `--threads 1` and `--threads N` output is, by construction, a concurrency bug (lost update or double count), not a benign ordering difference. That makes the differential test a high-signal bug detector.
- **Why default-sort was chosen despite the cost:** guarantees reproducible output by default (sharded-map iteration is otherwise run-to-run non-deterministic) and aligns with Jellyfish2's sorted output for fair Phase 4 comparison. The cost is real (sort over ~3B entries) and explicitly flagged for Phase 4 measurement.
- **Compatibility stance on the two tradeoffs:** both `dashmap` (new dep) and default-sort (CLI behavior change) are accepted deviations from the conservative baseline. They are recorded as deliberate, requirement-driven decisions — not drift. Downstream agents should not "undo" them to be conservative; the user explicitly weighed and accepted them.

</specifics>

<deferred>
## Deferred Ideas

- **Parallel gzip decompression** (split compressed stream on gzip-member boundaries, multi-threaded gunzip) — deferred because CRR1936095 is plain gzip (not BGZF), making member-boundary detection fragile. Gated on Phase 4's benchmark: only if decompression is measured to cap the counting speedup does this become its own phase. Tracked here, not lost.
- **Adaptive shard / prefix granularity for counting** (the `MINIM-02`/`MINIM-03` minimizer-partitioning line) — that is bounded-memory *counting*, which is v2 work (REQUIREMENTS §"Memory-Bounded Counting"), distinct from Phase 2's parallelism goal.
- **Configurable counter width / saturation warning** (`SAT-01`/`SAT-02`) — v2; Phase 2 keeps u32 with existing overflow semantics.

</deferred>

---

*Phase: 02-parallel-counting*
*Context gathered: 2026-07-01*
