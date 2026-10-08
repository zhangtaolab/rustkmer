# Roadmap: rustkmer Performance Milestone

## Overview

Transform rustkmer from a functional k-mer counting toolkit into a performance-competitive tool at human-genome scale. This milestone targets the primary bottlenecks preventing human-scale analysis: single-threaded counting, unbounded memory usage during merge, and inefficient k-mer storage. By implementing lock-free parallel counting, bounded-memory merging, and dense k-mer storage, rustkmer will match or beat Jellyfish2 on real Illumina WGS data while preserving the existing `.rkdb` format and dual-surface (CLI + Python) compatibility.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3, 4): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation & Quality** - Establish CI protection, consolidate format logic, and clean library I/O (completed 2026-07-01)
- [x] **Phase 2: Parallel Counting** - Implement lock-free concurrent counting for multi-core speedup (completed 2026-07-01)
- [ ] **Phase 3: Memory Safety** - Bounded merge routing and dense k-mer storage
- [ ] **Phase 4: Benchmark & Validation** - Reproducible harness and Jellyfish2 comparison on CRR1936095

## Phase Details

### Phase 1: Foundation & Quality

**Goal**: Establish engineering infrastructure that unblocks performance work and guards against regressions
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04
**Success Criteria** (what must be TRUE):

  1. A Rust CI workflow runs on every PR, enforcing `cargo fmt`, `cargo clippy -D warnings`, `cargo test`, and pyo3 wheel build — failing tests or new warnings block merge
  2. Library code outside `src/cli/` emits through `log::` facade instead of direct `eprintln!`/`println!` — embedding `rustkmer` and Python bindings get clean output
  3. The `.rkdb` write logic is consolidated into a single source of truth (`src/database/format.rs`) — `count.rs` no longer duplicates binary layout
  4. All user-facing library output uses English strings (no hardcoded Chinese) — consistent UX and parseable logs

**Plans**: 4/4 plans complete

Plans:
**Wave 1**

- [x] 01-01-PLAN.md — CI workflow (fmt/clippy/test/wheel-build) + fix 85 existing clippy warnings so -D warnings is green (Wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Migrate library console I/O to log facade + crate-level deny/cli allow attrs + parallel-merge backstop test (Wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-PLAN.md — Consolidate .rkdb write to single source of truth + remove data_offset clamp (golden-capture-first per D-10) (Wave 3)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 01-04-PLAN.md — Translate CJK string literals to English + syn-based self-enforcing CJK detection gate (Wave 4)

### Phase 2: Parallel Counting

**Goal**: Multi-core k-mer counting that scales with CPU count without lock contention
**Depends on**: Phase 1
**Requirements**: PCOUNT-01, PCOUNT-02, PCOUNT-03, PCOUNT-04
**Success Criteria** (what must be TRUE):

  1. The `count` command uses all available CPU cores by default (removes hardcoded `num_threads = 1`) — thread count configurable via `--threads` / `RUSTKMER_THREADS`
  2. Counting uses a sharded concurrent HashMap (dashmap) instead of `RwLock<HashMap>` — throughput scales with core count without lock contention
  3. `pyrustkmer`'s `PyCounter` delivers the same parallel speedup as the CLI — shared core library benefits both surfaces
  4. Parallel counting produces results identical to the current sequential path — k-mer counts match exactly on the same input (correctness guard)

**Plans**: 5/5 plans executed

**Wave 1** *(parallel, no dependencies)*

- [x] 02-01-PLAN.md — Thread-count plumbing: `--threads` flag, D-07 precedence chain (`--threads > RUSTKMER_THREADS > RAYON_NUM_THREADS > num_cpus`), centralized Err-tolerant `build_global` in `execute_count`, fix merge.rs Pitfall-3 `.expect()` landmine (Wave 1; PCOUNT-01)
- [x] 02-04-PLAN.md — Golden-capture-first: commit pre-refactor count MAPS (JSON, D-13 matrix) to `tests/fixtures/parallel_count_baseline/` BEFORE any table.rs edit, plus the `tests/parallel_count_tests.rs` scaffold with `#[ignore]d` differential stubs (Wave 1; D-10 sequencing prereq for 02-02)

**Wave 2** *(blocked on Wave 1)*

- [x] 02-02-PLAN.md — DashMap swap (`RwLock<HashMap>` -> `DashMap<u128,u32>`) with atomic `entry().and_modify().or_insert()` increment preserving verbatim overflow semantics + rayon chunked `par_iter` per-record loops (gzip stays single-threaded per D-02) + D-09 default-sort flip + inline atomicity/overflow tests (Wave 2; depends on 02-01, 02-04; PCOUNT-02, PCOUNT-04)
- [x] 02-03-PLAN.md — PyCounter GIL release: `threads` kwarg (`None` = all cores), `Arc<RustPyCounter>` field, wrap `add_from_fastq`/`add_from_fasta` in `pyo3::allow_threads` (0.27.2 API, NOT `detach`) (Wave 2; depends on 02-01; PCOUNT-03)

**Wave 3** *(blocked on Wave 2)*

- [x] 02-05-PLAN.md — Differential correctness gate: un-ignore the 1-vs-N commutativity differential, D-10 baseline-vs-current assertion, D-09 determinism, PCOUNT-01 precedence test, plus Python `TestPyCounterParallel` (Wave 3; depends on 02-02, 02-03; PCOUNT-01, PCOUNT-03, PCOUNT-04)

### Phase 3: Memory Safety

**Goal**: Bounded-memory merge operations and dense k-mer storage for the common k ≤ 32 case
**Depends on**: Phase 2
**Requirements**: MERGE-01, MERGE-02, MERGE-03, MERGE-04, DENSE-01, DENSE-02, DENSE-03
**Success Criteria** (what must be TRUE):

  1. Merge defaults to the streaming/external-sort path — human-scale merges no longer OOM the process
  2. Merge respects a memory budget via admission control — estimates required memory and routes to streaming when budget exceeded
  3. Failed or interrupted streaming merges clean up temporary shard files — RAII guard prevents silent disk exhaustion
  4. K-mers for k ≤ 32 are stored as `u64` instead of `u128` — roughly halving counting memory for the common case while preserving `.rkdb` v2 compatibility
  5. Dense storage maintains correctness — canonicalization and counts match the `u128` path exactly
  6. `pyrustkmer`'s `PyDatabase` merge uses the same bounded path as the CLI

**Plans**: 10/11 plans executed + 6 gap-closure plans pending (03-06..03-11)

**Wave 1** *(parallel, no dependencies)*

- [x] 03-01-PLAN.md — Header-only estimator + hard-route + D-02 reject branch (D-01/D-02; MERGE-01, MERGE-02)
- [x] 03-02-PLAN.md — RAII temp guards + process-unique subdir + startup sweep + tempfile dev→dep (D-06; MERGE-03)
- [x] 03-03-PLAN.md — KmerKey enum + DashMap width-swap for k ≤ 32 (D-03/D-04/D-05; DENSE-01, DENSE-02, DENSE-03)

**Wave 2** *(blocked on Wave 1)*

- [x] 03-04-PLAN.md — Wave-2 gate: dense+merge end-to-end integration + full suite + clippy on both crates (depends on 03-01, 03-03; MERGE-01, MERGE-02, DENSE-02, DENSE-03)
- [x] 03-05-PLAN.md — `PyDatabase.merge` kwargs (`max_memory`/`merge_mode`) routing through bounded core (depends on 03-01; MERGE-04)

**Gap Closure** *(opened 2026-10-07 by `03-VERIFICATION.md` — status `gaps_found`, 4/7 must-haves verified)*

- [x] 03-06-PLAN.md — **G1 / DENSE-01 inverted**: move the width choice from the key onto the table (`CounterTable::Dense(DashMap<u64,u32>)` | `Wide(DashMap<u128,u32>)`), delete the 32-byte `KmerKey` enum, and replace the self-fulfilling memory assertions with a stored-representation observation plus a 4M-entry `/proc/self/status` ratio test asserting < 1.0 (Wave 1; DENSE-01, DENSE-02, DENSE-03)
- [x] 03-07-PLAN.md — **G3 / CR-01**: delete the `count_le > 1_000_000` endianness heuristic in `KmerEntry::read_from`, make a damaged chunk read surface an `Err` instead of a silent `if let Ok`, and prove in-memory and streaming route parity on fixtures at and above 1,000,000 (Wave 1; MERGE-01, MERGE-02, DENSE-02)
- [x] 03-08-PLAN.md — **WR-03**: replace the inert golden-sha256 differential with a real write-path differential (dense vs non-dense bytes, k=32 zero-extension on disk, write/read/write idempotence) (Wave 1; DENSE-02)
- [x] 03-09-PLAN.md — **G2a / CR-02 header half + WR-01 + WR-06 + IN-01**: add `RKDatabase::read_header_of` and use it at all four `from_file_path` call sites, charge the in-memory route 96 B/k-mer instead of 24, hoist the empty-input guard, and relocate the prefix-cache intermediate into the RAII subdir (Wave 2; depends on 03-07; MERGE-01, MERGE-02, MERGE-03)
- [x] 03-10-PLAN.md — **G2b / CR-02 substance + MERGE-04**: add `RKDatabase::merge_databases_to_path` + `MergeSummary`, stream the merged output to disk instead of accumulating it, rename the prefix-cache handoff, and point the CLI and PyO3 binding at the bounded entry point (Wave 3; depends on 03-09; MERGE-01, MERGE-02, MERGE-04)
- [ ] 03-11-PLAN.md — **WR-04 + WR-08 + MERGE-03 sweep gap**: a failed prefix bucket aborts the merge and preserves its shards, the tautological integrity check is replaced with one that can fire, buckets concatenate in blocks, and the orphan sweep reclaims loose `rustkmer_*_*.chunk` files (Wave 3; depends on 03-09; MERGE-01, MERGE-03)

### Phase 4: Benchmark & Validation

**Goal**: Reproducible performance measurement and validation against Jellyfish2 on human-scale data
**Depends on**: Phase 3
**Requirements**: BENCH-01, BENCH-02, BENCH-03, BENCH-04
**Success Criteria** (what must be TRUE):

  1. A reproducible benchmark harness measures counting and merge wall-clock time and peak memory — runnable in CI as a regression gate
  2. **Milestone success criterion:** rustkmer matches or beats Jellyfish2 on counting speed on the CRR1936095 human-scale dataset under fair methodology (cold cache, decompression counted, matched k/canonicalization/input settings)
  3. The benchmark reports peak memory alongside wall-clock — memory wins (not just speed) are visible and validated
  4. The harness degrades gracefully to a slice or synthetic input on machines without the full CRR1936095 dataset — CI can run without the full 5.2 GB data

**Plans**: TBD

Plans:

- [ ] 04-01: Build reproducible benchmark harness with wall-clock and peak memory measurement
- [ ] 04-02: Implement fair comparison methodology against Jellyfish2 (cold cache, matched settings)
- [ ] 04-03: Add graceful degradation for CI environments without full CRR1936095 dataset
- [ ] 04-04: Run milestone validation on CRR1936095 and generate performance report

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Quality | 4/4 | Complete    | 2026-07-01 |
| 2. Parallel Counting | 5/5 | Complete    | 2026-07-01 |
| 3. Memory Safety | 10/11 | In Progress | - |
| 4. Benchmark & Validation | 0/4 | Not started | - |
