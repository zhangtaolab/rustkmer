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
- [x] **Phase 3: Memory Safety** - Bounded merge routing and dense k-mer storage (completed 2026-10-09)
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

**Plans**: 17/17 plans complete (gap-closure rounds 1-3 done; round 4 opened 2026-10-09: 03-17)

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
- [x] 03-11-PLAN.md — **WR-04 + WR-08 + MERGE-03 sweep gap**: a failed prefix bucket aborts the merge and preserves its shards, the tautological integrity check is replaced with one that can fire, buckets concatenate in blocks, and the orphan sweep reclaims loose `rustkmer_*_*.chunk` files (Wave 3; depends on 03-09; MERGE-01, MERGE-03)

**Gap Closure Round 2** *(opened 2026-10-09 by `03-VERIFICATION.md` re-verification — status `gaps_found`, 7/11 truths verified; CR-01/CR-02/CR-03 + WR-05 from `03-REVIEW.md`)*

- [x] 03-12-PLAN.md — **CR-03**: header-only cross-input k/canonical validation in `merge_prologue` (read_header_of + validate_header_compatibility), inherited by all three routes and both entry points incl. PyDatabase.merge; streaming-route rejection tests (Wave 1; MERGE-01, MERGE-04)
- [x] 03-13-PLAN.md — **CR-01 + WR-03**: record-aligned batch reads with carried tails and propagated read errors, unstranded duplicate runs (VecDeque buffer), plus >4 MB single-bucket conservation proof through merge_single_prefix_streaming and the full route (Wave 1; MERGE-01, MERGE-03)
- [x] 03-14-PLAN.md — **WR-05**: CLI front-end validation reads 42-byte headers only — the full-load reference and both serial validation loops replaced by one extracted header-only pass (`validate_merge_compatibility`), proven on body-absent inputs (Wave 1; MERGE-01)
- [x] 03-15-PLAN.md — **CR-02**: bucket by the FIRST 4 bases (high 8 bits) so index-order concatenation is globally ascending and the `sorted: true` header is truthful, plus query_kmer / prefix-extraction / route-parity proofs and the IN-07 tautological test rewritten (Wave 2; depends on 03-13; MERGE-01, DENSE-02)

**Gap Closure Round 3** *(opened 2026-10-09 by the user triage of `03-VERIFICATION.md` human decision item 1 — fix fresh-review CR-01 / open WR-03 in-phase via a third round)*

- [x] 03-16-PLAN.md — **CR-01 / WR-03 root cause**: `split_files_by_prefix` writes the canonicalized bucket key to the shard (bucket key == stored key) and propagates canonicalization errors — closes mixed-canonical content (summed encodings), header semantics (ANY-input), and output order at once; RED-provable mixed-canonical order/conservation/query test plus the corrected ANY-canonical routing pin (Wave 3; depends on 03-15; MERGE-01, DENSE-02)

**Gap Closure Round 4** *(opened 2026-10-09 by `03-VERIFICATION.md` round-3 re-verification — status `gaps_found`, 10/11 truths; truth 10's streaming-writer arm, the only open gap)*

- [x] 03-17-PLAN.md — **truth 10 streaming arm / round-3 CR-01 residual**: force the sorting (hashmap) per-bucket writer for mixed-canonical merges in `ExternalSortMerger::new` (option a) + per-file ascending-run validation refusing descending runs in `merge_single_prefix_streaming` (option b backstop), the `merge_mode='streaming'` e2e arm on the 03-16 fixture, corrected writer-contract comments, WINDOWS.md #17 / deferred-items closure (Wave 4; depends on 03-16; MERGE-01, DENSE-02)

### Phase 4: Benchmark & Validation

**Goal**: Reproducible performance measurement and validation against Jellyfish2 on human-scale data
**Depends on**: Phase 3
**Requirements**: BENCH-01, BENCH-02, BENCH-03, BENCH-04
**Success Criteria** (what must be TRUE):

  1. A reproducible benchmark harness measures counting and merge wall-clock time and peak memory — runnable in CI as a regression gate
  2. **Milestone success criterion:** rustkmer matches or beats Jellyfish2 on counting speed on the CRR1936095 human-scale dataset under fair methodology (cold cache, decompression counted, matched k/canonicalization/input settings)
  3. The benchmark reports peak memory alongside wall-clock — memory wins (not just speed) are visible and validated
  4. The harness degrades gracefully to a slice or synthetic input on machines without the full CRR1936095 dataset — CI can run without the full 5.2 GB data

**Plans**: 3/4 plans executed

Plans:
**Wave 1**
- [x] 04-01-PLAN.md — Harness core: stdlib measurement (wall + peak RSS both platforms), results schema, deterministic synthetic generator, degradation ladder (full/slice/synthetic), dead-infra deletion (Wave 1; BENCH-01, BENCH-03, BENCH-04)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 04-02-PLAN.md — Jellyfish2 fair-comparison methodology: matched BenchmarkConfig argv matrix, count-parity gate, interleaved cold-cache protocol, disk guardrail (Wave 2; depends 04-01; BENCH-02)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 04-03-PLAN.md — CI regression gate: compare.py thresholds (25% wall / 15% RSS), benchmark.yml ubuntu+macOS matrix, per-platform committed baselines + CI-artifact bootstrap (Wave 3; depends 04-01, 04-02; BENCH-01, BENCH-04)

**Wave 4** *(blocked on Wave 3 completion)*
- [ ] 04-04-PLAN.md — Milestone validation on CRR2044018 (user-approved substitute for missing CRR1936095): slice parity pilot, full k=31/k=21 runs, mechanically rendered report (Wave 4; depends 04-01..04-03; BENCH-02, BENCH-03)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Quality | 4/4 | Complete    | 2026-07-01 |
| 2. Parallel Counting | 5/5 | Complete    | 2026-07-01 |
| 3. Memory Safety | 17/17 | Complete    | 2026-10-09 |
| 4. Benchmark & Validation | 3/4 | In Progress | - |

## Backlog

### Phase 999.1: Follow-up — Phase 03 deferred UAT follow-up: Test 22 (BACKLOG)

**Goal:** Resolve the UAT checkpoint deferred during Phase 03 verification
**Source phase:** 03
**Deferred at:** 2026-10-09 during /gsd-verify-work 03 session completion
**Follow-ups:**
- [ ] Test 22: pyo3 0.27 no longer auto-emits -undefined dynamic_lookup; pyo3/build.rs should call pyo3_build_config::add_extension_module_link_args() so the documented manual-build workaround links as-is again (this session injected it via RUSTFLAGS) (deferred 2026-10-09)

### Phase 999.2: Follow-up — Phase 03 deferred UAT follow-up: Test 22 (BACKLOG)

**Goal:** Resolve the UAT checkpoint deferred during Phase 03 verification
**Source phase:** 03
**Deferred at:** 2026-10-09 during /gsd-verify-work 03 session completion
**Follow-ups:**
- [ ] Test 22: dev-venv pitfall: a stale pyrustkmer 0.4.1 package directory in site-packages silently shadows a manually installed pyrustkmer.so extension (deferred 2026-10-09)

### Phase 999.3: Follow-up — Phase 03 deferred UAT follow-up: Test 21 (BACKLOG)

**Goal:** Resolve the UAT checkpoint deferred during Phase 03 verification
**Source phase:** 03
**Deferred at:** 2026-10-09 during /gsd-verify-work 03 session completion
**Follow-ups:**
- [ ] Test 21: deferred-items.md's claim that loose *.chunk files are never swept is stale — temp_lifecycle.rs now sweeps them (CHUNK_FILE_PREFIXES); update the record (deferred 2026-10-09)
