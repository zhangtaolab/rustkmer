# Requirements: rustkmer

**Defined:** 2026-06-30
**Core Value:** Count, query, and merge k-mers at genome scale within practical memory — fast and lean enough to compete with best-in-class tools, from both the CLI and Python.
**Milestone:** Performance — make counting + merging competitive with **Jellyfish2** at human-genome scale, with bounded memory, across both surfaces.

## v1 Requirements

Requirements for this performance milestone. Each maps to a roadmap phase (traceability filled by the roadmapper).

### Parallel Counting

- [x] **PCOUNT-01**: Counting uses all available CPU cores by default — the hardcoded `num_threads = 1` single-thread restriction is removed; thread count is configurable via `--threads` / `RUSTKMER_THREADS`
- [x] **PCOUNT-02**: The counter uses a sharded / lock-free concurrent structure (dashmap) instead of a single global `RwLock<HashMap>`, so throughput scales with core count without lock contention
- [x] **PCOUNT-03**: `pyrustkmer`'s `PyCounter` delivers the same parallel speedup as the CLI (shared core library)
- [x] **PCOUNT-04**: Parallel counting produces results identical to the current sequential path — k-mer counts match exactly on the same input (correctness regression guard)

### Bounded Merge

- [x] **MERGE-01**: Merge defaults to the streaming / external-sort path (not the all-in-memory path), so human-scale merges no longer OOM
- [x] **MERGE-02**: Merge respects a memory budget via admission control — it estimates required memory and routes to streaming when the estimate exceeds the budget
- [x] **MERGE-03**: A failed or interrupted streaming merge cleans up its temporary shard files (RAII guard) — no silent disk exhaustion
- [ ] **MERGE-04**: `pyrustkmer`'s `PyDatabase` merge uses the same bounded path as the CLI

### Dense Storage

- [ ] **DENSE-01**: K-mers for k ≤ 32 are stored as `u64` (8 bytes) instead of `u128`, roughly halving counting memory for the common case
- [ ] **DENSE-02**: Dense storage is transparent to existing readers — current `.rkdb` v2 files and queries keep working (backward/forward compatible); if a format bump turns out to be required, the tradeoff is surfaced as an explicit decision with a migration path before it lands
- [ ] **DENSE-03**: Canonicalization stays correct under `u64` packing — counts match the `u128` path exactly

### Benchmark / Validation

- [ ] **BENCH-01**: A reproducible benchmark harness measures counting and merge wall-clock time and peak memory, runnable in CI as a regression gate
- [ ] **BENCH-02**: rustkmer matches or beats **Jellyfish2** on counting speed on the CRR1936095 human-scale dataset, under fair methodology (cold cache, decompression counted, matched k / canonicalization / input settings)
- [ ] **BENCH-03**: The benchmark reports peak memory alongside wall-clock, so memory wins (not just speed) are visible
- [ ] **BENCH-04**: The harness degrades gracefully to a slice or synthetic input on machines without the full CRR1936095 dataset, so CI can still run

### Foundation / Quality

<!-- Engineering prerequisites that unblock the performance phases. Observable/testable even though not end-user-facing. -->

- [x] **FOUND-01**: A Rust CI workflow runs `cargo fmt --check`, `cargo clippy -D warnings`, `cargo test`, and the `pyrustkmer` wheel build on PRs — tests or new warnings cannot merge
- [x] **FOUND-02**: Library code outside `src/cli/` does not write directly to stdout/stderr — it emits through the `log` facade, so machine-readable CLI output and Python embedding are not polluted
- [x] **FOUND-03**: The duplicated `.rkdb` write logic (`count.rs` vs `format.rs`) is consolidated into a single source of truth before dense-storage changes land
- [x] **FOUND-04**: User-facing library output is English (no hardcoded Chinese strings), routing through `log::`

## v2 Requirements

Deferred from this milestone. Tracked but not in the current roadmap.

### Memory-Bounded Counting (Minimizer Partitioning)

- **MINIM-01**: Minimizer / signature-based partitioned (two-pass) counting for bounded-memory counting on any hardware, regardless of dataset size
- **MINIM-02**: `--max-memory` hard cap for counting with disk spill when the budget is exceeded
- **MINIM-03**: Adaptive shard / prefix granularity (5- or 6-prefix, or minimizer-based) tuned for human-scale inputs

### Counter Correctness / Width

- **SAT-01**: Configurable counter width (`u16` / `u32` / `u64`) with a warning when counts saturate the configured width
- **SAT-02**: Promote count storage beyond `u32` for high-coverage datasets where a single k-mer can exceed `u32::MAX`

### Broader Benchmarking

- **BENCH-V2-01**: Benchmark against **KMC3** in addition to Jellyfish2 (covers the memory-efficient, disk-backed comparator)

## Out of Scope

Explicitly excluded from this milestone. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| New query types / query micro-optimization | The stated bottleneck is counting + merging, not lookups; query path left untouched unless it regresses |
| Set operations on databases (union / intersection / difference) | Not a performance-counting concern; use external tools if needed |
| Distributed / cluster counting | Single-machine scope; optimize local parallelism via Rayon |
| New output formats (KFF, KMC native, Jellyfish native) | Not perf-critical; keep `.rkdb` |
| Visualization UI | CLI + library product; UI is a separate concern |
| Real-time / streaming input counting | Batch file counting is the requirement |
| Counting Quotient Filter (CQF) | Would require a major architecture rewrite; incompatible with exact-counting scope |
| KMC3 as a v1 benchmark comparator | v1 targets Jellyfish2 only; KMC3 comparison deferred to v2 (BENCH-V2-01) |
| God-module splits not on a hot path | `format.rs` / `pyo3/database.rs` splits are cleaned only where the perf work touches them; pursued for their own sake in a later cleanup round |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Complete |
| FOUND-02 | Phase 1 | Complete |
| FOUND-03 | Phase 1 | Complete |
| FOUND-04 | Phase 1 | Complete |
| PCOUNT-01 | Phase 2 | Complete |
| PCOUNT-02 | Phase 2 | Complete |
| PCOUNT-03 | Phase 2 | Complete |
| PCOUNT-04 | Phase 2 | Complete |
| MERGE-01 | Phase 3 | Complete |
| MERGE-02 | Phase 3 | Complete |
| MERGE-03 | Phase 3 | Complete |
| MERGE-04 | Phase 3 | Pending |
| DENSE-01 | Phase 3 | Pending |
| DENSE-02 | Phase 3 | Pending |
| DENSE-03 | Phase 3 | Pending |
| BENCH-01 | Phase 4 | Pending |
| BENCH-02 | Phase 4 | Pending |
| BENCH-03 | Phase 4 | Pending |
| BENCH-04 | Phase 4 | Pending |

**Coverage:**

- v1 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-30*
*Last updated: 2026-07-01 after roadmap creation*
