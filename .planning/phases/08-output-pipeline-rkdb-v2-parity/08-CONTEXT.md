# Phase 8: Output Pipeline & .rkdb v2 Parity - Context

**Gathered:** 2026-11-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Make counting output fast (unstable/parallel sort, streaming write) and PROVE byte-level compatibility of every new counting path — the milestone's contract gate before the Phase 10 verdict. Phase 7 established that the output sort/write is now the dominant component of the slice wall (count-only is producer-bound at ~6.4 s; the slice wall above it is output). This phase owns that stage and the `.rkdb` v2 byte-identity proof.

Requirements: OUT-01 (fast sort + streaming write), OUT-02 (`.rkdb` v2 byte-identity + both-consumer sortedness), OUT-03 (old-vs-new + 1-vs-N differential matrix; gates fail on injected defects).

Does NOT: change the writer format/header (frozen), implement D2 (Phase 9), or build the minimizer (conditional Phase 11).

</domain>

<decisions>
## Implementation Decisions

### Fixed contract (non-negotiable)
- **Frozen writer:** `src/database/format.rs` remains the single `.rkdb` v2 writer — magic `RKDB`, version 2, 42-byte header + 20-byte entries; the header literals and the IN-03 `total_kmers` meanings stay verbatim (counter total = sum of counts; header total = record count). Byte-identity is the gate; do not "fix" header semantics.
- **Pre-refactor goldens:** `tests/fixtures/golden_manifest.sha256` (12 fixtures, k={21,32,64}×canonical×sorted/unsorted) captured in Phase 5 BEFORE any hot-path refactor. These hashes are the proof; NEVER regenerate or update them to make a diff green. `tests/golden_sha256_tests.rs` + `tests/golden_tests.rs` must stay green.
- **Sortedness is proven through BOTH binary-search consumers:** `DatabaseQuery` AND the prefix query path (v1.0 CR-02 precedent — route parity of ANSWERS, not just the header flag).

### Claude's Discretion (within the contract)
- Replace the stable sorts (`sort_unstable_by_key` / `rayon::par_sort_unstable` over the engine's collected `(u128,u32)` entries) and stream them into the frozen writer without a separate full `get_all_counts` materialization. Keep text output sorted by numeric key.
- Choose the streaming shape (write in bounded chunks from the sorted slice vs a pull-iterator) so peak memory does not regress (Phase 7 ~17.96 GB slice RSS is the reference).
- Determinism: the engine's partition assignment and reduction are order-independent; the sorted output must be byte-identical across t1/t4/t16 (Phase 7 already proves sha256 identity — keep it).
- Differential/property-test design for OUT-03 (old-vs-new across k×canonical; disjointness/conservation; injected-defect RED demonstrations: overflow/duplication/ordering mutations observed RED).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/count/engine.rs` — `CountResult::into_pairs`/tables; the engine emits the counting stage.
- `src/cli/commands/count.rs:368,416` — current stable sorts (`sort_by`, `sort_by_key`) before text/`.rkdb` output.
- `src/database/format.rs:546` `write_to_file` (462 sort at :652 is the merge path; the count writer path is frozen), `:676` `to_file_path`; header constants `DATABASE_MAGIC`/`DATABASE_VERSION`.
- `tests/golden_sha256_tests.rs` + `tests/fixtures/golden_manifest.sha256` (12 pre-refactor hashes); `tests/dense_differential_tests.rs`, `tests/parallel_count_tests.rs`, `tests/thread_local_count_tests.rs`, `tests/count_engine_tests.rs` (existing differential patterns).
- `src/database/query.rs` (DatabaseQuery binary search) + `src/database/prefix_query_optimized.rs` (prefix binary-search consumer).
- Phase 5/7 evidence: slice sha256 `0976f29c…` across t1/t4/t16; Phase 7 slice RSS ~17.96 GB.

### Established Patterns
- Goldens captured before refactor; mutation-RED proof discipline (an injected defect must turn a named gate red).
- Byte-identity via sha256; sortedness proven via both consumers; exact counts fail-loud.
- No fixture regeneration; no `get_all_counts` materialization on the hot path.

### Integration Points
- The engine's `CountResult` feeds the output stage; the CLI's `CountOutput` adapter writes text/.rkdb.
- The frozen `format.rs` writer consumes the sorted entry stream.
- `DatabaseQuery` + prefix query validate sortedness by answering correctly.

</code_context>

<specifics>
## Specific Ideas

- Phase 7 showed output now dominates the slice wall — the sort must be parallel/unstable and the write streaming; measure the drop from the ~13.4 s single-thread stable sort on 229M keys.
- The only acceptable reason a golden hash changes is a deliberate, surfaced format decision — never a refactor. Any such change would be a user decision.
- OUT-03 must include RED demonstrations: mutate overflow/duplication/ordering and observe named gates fail.

</specifics>

<deferred>
## Deferred Ideas

- Python D2 skip-N semantics — Phase 9.
- Full human-scale jellyfish verdict + KMC3 comparison — Phase 10.
- Minimizer/disk spill — conditional Phase 11.

</deferred>