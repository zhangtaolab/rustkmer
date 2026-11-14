# Phase 6: Parallelism Correctness & Hot Path - Context

**Gathered:** 2026-11-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Make thread control actually work and make the single-thread hot path measurably faster while counts stay EXACTLY equal — establishing the true t1 baseline and contention-free accumulation before the Phase 7 engine restructure. This phase changes the counting hot path (src/), unlike Phase 5's infrastructure. It does NOT restructure into the shared engine (Phase 7) and does NOT change output/.rkdb (Phase 8).

Requirements: PAR-01 (working --threads), PAR-02 (thread-local counters + end reduction, no per-window global atomics), PAR-03 (rolling encode + bit-parallel revcomp).

</domain>

<decisions>
## Implementation Decisions

### Research-locked (from .planning/research/SUMMARY.md + Phase 5 measured evidence — treat as constraints)

- **PAR-01 — the `--threads` no-op fix.** Root cause (Phase 5 verified, count.rs:836-845): `resolve_thread_count` passes `rayon::current_num_threads()` as the fallback argument, which eagerly initializes the default 16-thread global pool BEFORE `build_global()` runs; `build_global` then fails silently (`let _ =`). Fix: compute the fallback LAZILY (via `std::thread::available_parallelism`, not `rayon::current_num_threads`), and call `build_global` BEFORE any rayon query. Preserve the `--threads > RUSTKMER_THREADS > RAYON_NUM_THREADS > all-cores` precedence chain and Python `threads=` / IN-04 warn semantics. Phase 5's pool-size test (`requested=1 observed=18`) and thread-scaling gate (RED) must turn GREEN.
- **PAR-02 — thread-local counters + end reduction; kill per-window global atomics.** The contention evidence (Phase 5, `contention_evidence.json`) shows global atomics attribution 120.22 ns (~115% of the shared-vs-local gap) — the per-window `total_kmers`/`unique_kmers` fetch_add bounces cache lines across cores. Accumulate in thread-local counters and reduce at end-of-run. The reduction is a NEW summation site: use CHECKED arithmetic with the verbatim fail-loud u32 overflow error (never saturating/wrapping). Preserve `KmerCounter`'s public API (`increment`/`get_count`/`get_all_counts` signatures + verbatim overflow semantics + the Dense u64 / Wide u128 width selection).
- **PAR-03 — rolling 2-bit encoder + bit-parallel revcomp.** Replace per-window O(L·k) encoding with a rolling shift-in encoder (u64 for k≤32) + word-level reverse-complement (microbench measured 2.7x single-thread win; rolling encode alone 1.2 vs 31.7 ns). Mask to 2k bits and RESET the valid run at every N and record boundary — otherwise it silently reproduces the chimeric-k-mer / stale-window bug. Differential-test rolling vs the existing per-window encoder on the edge matrix (N at every position, lowercase, record boundaries, k ∈ {1..64}); retain the u128 path for k>32 and API stability.
- **Preserve exact counts.** The old-vs-new AND 1-vs-N differentials across k × canonical must stay green; `.rkdb` v2 byte-identity unchanged (output sorting is Phase 8, but counting must not change emitted counts). No public API change; no .rkdb format change.
- **Dual surface:** PyCounter must inherit the win (thread-local accumulation + rolling encode in the shared core). PyO3 paths use `py.detach` with owned Send captures.

### Claude's Discretion
The concrete thread-local counter data structure (e.g. per-worker `HashMap`/`DashMap`/sharded Vec), how `KmerCounter` exposes thread-local accumulation while keeping its public API, the rolling-encoder buffer layout and revcomp word tricks, and how the end reduction merges per-thread maps — all at Claude's discretion within the constraints above. Pick the simplest structure that Phase 7 can build the persistent-worker engine on top of.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/hash/table.rs` — `KmerCounter` + private `CounterTable` enum (Dense DashMap<u64,u32> k≤32 / Wide DashMap<u128,u32> k>32), `stored_key_bytes()`, `uses_dense_storage()`, verbatim overflow error.
- `src/kmer/encoding.rs` / `canonical.rs` — `encode_kmer_u128`/`decode_kmer_u128`/`canonical_kmer_u128`; the per-window reference encoder for PAR-03 differential.
- `src/cli/commands/count.rs` — rayon chunked `par_iter` (CHUNK_SIZE 4096), `resolve_thread_count`(836-845), per-window global atomics.
- `pyo3/src/counter.rs` — `PyCounter` add_from_* (sequential today; engine in Phase 9, but thread-local core accumulates here).
- Phase 5 gates: `tests/thread_pool_size_tests.rs` (ignored standing gate + characterization), `scripts/bench/thread_scaling.py`, `contention_evidence.json`.
- v1.0 1-vs-N differential pattern (tests/) + golden baselines.

### Established Patterns
- Fail-loud overflow at u32::MAX with verbatim message; checked arithmetic in new summations.
- Structured-diff discipline (1-vs-N, old-vs-new) across k × canonical.
- D-09 default-sort for reproducibility (hasher/iteration-order changes must not break sorted output).

### Integration Points
- The `--threads` fix is at count.rs `resolve_thread_count` + the `build_global` call site in `execute_count`.
- Thread-local accumulation replaces the per-window atomic path; end reduction merges before output.
- Rolling encode lives in encoding.rs/canonical.rs, consumed by the count hot loop.
- Phase 7 will move this into `src/count/engine.rs` — keep the counter/threshold logic separable.

</code_context>

<specifics>
## Specific Ideas

- The pool-size test is the milestone's smoking-gun: Phase 5 proved `requested=1 observed=18`; PAR-01 must flip it green (un-ignore the standing gate, invert the characterization).
- Atomics attribution is measured dominant — the end-reduction design should remove the per-window atomic entirely, not just reduce its frequency.
- Rolling encoder MUST reset at N and record boundaries; the Phase 5 N-read differential (33 chimeric k-mers) is the cautionary evidence for boundary bugs.

</specifics>

<deferred>
## Deferred Ideas

- The persistent-worker shared engine (`src/count/engine.rs`) — Phase 7.
- Parallel/unstable output sort + `.rkdb` byte-identity proof — Phase 8.
- Python routing through the shared engine + D2 skip-N implementation — Phase 9.

</deferred>