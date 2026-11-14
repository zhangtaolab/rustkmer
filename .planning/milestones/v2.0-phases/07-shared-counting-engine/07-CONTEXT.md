# Phase 7: Shared Counting Engine - Context

**Gathered:** 2026-11-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Build ONE shared counting engine (`src/count/engine.rs`) consumed by both the CLI (`execute_count`) and — structurally ready for — PyO3: caller thread is a single producer (decompress + parse + one `for_each_window` extractor + splitmix routing), N persistent OS worker threads consume bounded partition-tagged batches and count into disjoint hash-range partition tables, with decompression overlapped with counting (no per-chunk fork-join barrier). ENGINE-02: scaling efficiency materially improves toward jellyfish's 8.9x/16 cores and slice wall drops vs the Phase 6 baseline. ENGINE-03: ONE core skip-N window extractor; MultiGzDecoder multi-member regression stays green.

Does NOT: implement D2 Python semantics (Phase 9 — Python keeps its N pre-filter here), change output sort/.rkdb writer (Phase 8 owns byte-identity proof), or minimize memory via disk spill (conditional Phase 11).

</domain>

<decisions>
## Design decisions — research-locked (from 07-RESEARCH.md, measured this session)

- **Engine shape (HIGH):** caller thread = single producer (decompress + FASTQ/FASTA parse + ONE `for_each_window` extract + canonical + splitmix64 route); N persistent OS worker threads; N bounded `std::sync::mpsc::sync_channel` queues carrying 4096-key partition-tagged batches. No rayon tasks for blocking/worker work; the global rayon pool stays configured for reduction/sort. `threads == 1` takes a true sequential path (no extra producer thread) so the t1 semantics stay honest.
- **Partition scheme (HIGH, memory-decided):** static disjoint hash-range partitioning, `P = min(256, max(64, threads))` (64 on the 16-core target, decoupled from thread count); workers own contiguous partition ranges; each partition is a `LocalKmerCounts` (dense u64 k≤32 / wide u128 k>32). Routing key MUST be splitmix64-mixed (raw top key bits skew 3.54 max/mean; splitmix 1.02). Measured: 64 partitioned tables peak 6.95 GB vs 25.1 GiB for the shared-TLS+merge scheme — the partitioned scheme is required for the memory guardrail.
- **Overlapped I/O:** producer decompresses (MultiGzDecoder / flate2, multi-member) and hands off owned record batches; counting proceeds concurrently. Producer ≈5.4 s vs worker increment ≈19–21 s single-thread on the 4M slice, so one producer is sufficient but IS the parallel-stage bottleneck — parallel extraction / file-level producers is the documented next lever IF measurement contradicts (record, don't pre-optimize).
- **CRITICAL gate update (never soften):** PROF-02's pool-size observer currently asserts total OS threads == requested + 1. The engine's expected total becomes `2N+1` (main + N engine workers + N rayon workers) for N>1 and `2` for N==1; `verify_threads.py` must also stop sampling at the first `>1` observation (it would otherwise catch the intermediate rayon-only state). Update the gate to the exact new formula; a red gate must stay red on a real defect.
- **D2 extraction:** ONE core window-extraction function (`for_each_window`) implementing the CLI skip-N semantics (skip any window containing a non-ACGT base; reset at record boundaries). Python keeps its existing strip-N pre-filter in Phase 7 (D2 semantics change is Phase 9); the single extractor is what Phase 9 switches Python onto.
- **Exactness/format:** reuse `LocalKmerCounts::increment` (verbatim u32 overflow, fail-loud) and checked u64 aggregate sums (the 06-05 CAS publication pattern); the frozen sorted `.rkdb` v2 writer (`RKDB`, version 2, 42-byte header, 20-byte entries); output must be byte-identical (sha256) across t1/t4/t16. Goldens/parity gates stay green; no fixture regeneration.
- **Dual surface:** `CountResult::merge_into(&KmerCounter)` is the Phase 9 PyCounter bridge; Phase 7 makes the engine the CLI entry point and exposes the bridge; it may wire PyCounter `add_from_*` through the engine only if behavior-preserving (the roadmap Note leaves that to Phase 9; if wired, `py.detach` + owned Send captures).
- **No new dependencies** (std sync_channel/thread + existing rayon/parking_lot/hashbrown/bio/flate2/byteorder); MSRV 1.82.
- **Determinism:** partition assignment is a pure function of the key; the end reduction and sorted output are order-independent. Prove sha256 equality across thread counts and repeated runs.

### Claude's Discretion
Queue capacity, batch/frame struct layout, worker shutdown/poison protocol, reduction threading (caller-thread vs rayon), dynamic work-stealing trigger (research suggests: slowest worker > 0.8× producer time, or a worker-bound RED gate), interleaved vs after-file skip warnings (`FileStats.skipped_batches` recommended), and partition-count tuning (start 64; routing cost measured flat 16 vs 64).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/hash/local.rs` — `LocalKmerCounts` (dense/wide, verbatim overflow, skip counter) + `LocalHandleRegistry`.
- `src/hash/table.rs` — `KmerCounter`, `merge_local_counts` (AtomicU64::fetch_update CAS total), `reduce_local_counts` parallel merges.
- `src/kmer/encoding.rs` — `RollingEncoder` + `reverse_complement_u64` (k≤32) + u128 path.
- `src/cli/commands/count.rs` — current `par_chunks(64).try_for_each_init` loop, `resolve_thread_count`/`build_global`, CHUNK_SIZE 4096.
- `src/io/fastq.rs` — MultiGzDecoder multi-member gzip (v1.0 8102985 regression).
- `pyo3/src/counter.rs` — `add_from_*` (sequential today), `py.detach`.
- Phase 5/6 gates: `thread_scaling.py`, `tests/thread_pool_size_tests.rs`, `verify_threads.py`, `contention_evidence.json`, golden/parity suites.

### Established Patterns
- Fail-loud u32 overflow with verbatim message; checked arithmetic in every new summation.
- Frozen `.rkdb` v2 writer; deterministic sorted output; goldens never regenerated.
- Deterministic concurrent tests (barrier-synchronized, exact totals) — no scheduling-luck passes.
- Dual-surface via one shared core entry point (v1.0 merge precedent).

### Integration Points
- New `src/count/engine.rs` (module tree `src/count/`); `execute_count` delegates to it.
- `for_each_window` extractor used by CLI now and PyO3 in Phase 9.
- `CountResult`/`merge_into` bridge exposed for Phase 9.
- Pool-size gate + thread-scaling gate updated to the engine's thread model.

</code_context>

<specifics>
## Specific Ideas

- The 2N+1 thread formula is a hard integration point: update the observer, prove the gate red on a real defect, never widen it to mask.
- Memory is a first-class constraint: 64 partitioned tables measured 6.95 GB vs 25.1 GiB shared-TLS; the engine must keep the partitioned scheme.
- Measure the engine on the real 4M slice with parity-before-timing; record producer vs worker split, t1/t4/t16 wall, peak RSS, and sha256 determinism.

</specifics>

<deferred>
## Deferred Ideas

- Parallel extraction / file-level producers — only if the engine measurement shows the producer dominates (documented next lever).
- Python D2 skip-N semantics — Phase 9.
- Parallel/unstable output sort + `.rkdb` byte-identity proof — Phase 8 (engine emits a sorted stream into the frozen writer).
- Dynamic work-stealing — only if a worker-bound RED gate appears.

</deferred>