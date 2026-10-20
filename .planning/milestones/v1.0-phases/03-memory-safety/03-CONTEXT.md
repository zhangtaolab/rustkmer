# Phase 3: Memory Safety - Context

**Gathered:** 2026-07-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Make merge operations memory-bounded (default to the streaming/external-sort path, with memory-budget admission control and failure cleanup) **and** store k ≤ 32 k-mers densely as `u64` in the counting/merge hot path (roughly halving counting memory for the common case) — while preserving `.rkdb` v2 on-disk compatibility exactly and keeping canonicalization/counts identical to the `u128` path. Changes flow to **both** the CLI and `pyrustkmer` through the shared core.

**WHAT is locked by `REQUIREMENTS.md`** (no `03-SPEC.md` exists — REQUIREMENTS is the WHAT-authority for this phase; this document locks the HOW):
- **MERGE-01**: Merge defaults to the streaming/external-sort path — human-scale merges no longer OOM
- **MERGE-02**: Memory-budget admission control — estimate required memory, route to streaming when estimate exceeds budget
- **MERGE-03**: Failed/interrupted streaming merges clean up temp shard files (RAII guard) — no silent disk exhaustion
- **MERGE-04**: `pyrustkmer`'s `PyDatabase` merge uses the same bounded path as the CLI
- **DENSE-01**: k ≤ 32 stored as `u64` (8 bytes) instead of `u128` — ~half the counting memory for the common case
- **DENSE-02**: Dense storage is transparent to existing readers — `.rkdb` v2 backward/forward compatible; any format bump surfaced as an explicit decision (see D-03 / Deferred)
- **DENSE-03**: Canonicalization stays correct under `u64` packing — counts match the `u128` path exactly

**In scope:** the merge dispatch/admission-control path (`src/database/format.rs` `merge_databases` / `should_use_streaming` / `merge_databases_inmemory` / `merge_databases_streaming`, `src/database/streaming_merge.rs`, `src/database/prefix_cache_merge.rs`, `src/cli/commands/merge.rs`, `MergeConfig`), temp-shard cleanup (RAII + process-unique subdir + startup sweep), the `u128`→`u64` dense counter (`src/hash/table.rs`), dense-aware in-memory merge structures, `PyDatabase.merge` (`pyo3/src/database.rs`), and correctness/differential tests.

**Out of scope (per ROADMAP/REQUIREMENTS):** on-disk dense packing / `.rkdb` format bump (Deferred — D-03 locks RAM-only), adaptive 5-/6-prefix shard granularity (MINIM-03, v2), resumable merge (v2), signal-handler-based Ctrl-C cleanup (v2), minimizer/signature-partitioned bounded-memory *counting* (v2), the benchmark harness (Phase 4), query/prefix/fuzzy path optimization, new user-facing commands.

**Reframing for the planner — the merge side is smaller than the roadmap seed plans suggest.** A code scout found that most of the merge machinery already exists: `--max-memory` (auto-defaults to ~50% of system RAM via `get_default_memory_limit`), `--merge-mode auto|memory|streaming`, `--use-prefix-cache`, a `should_use_streaming()` estimator/router, and RAII temp-file guards (`TempFileManager`, `StreamingMergeIterator::Drop`) on the streaming path. Phase 3's merge work is therefore **gap-filling + default-flipping**, not greenfield:
1. Fix the estimator's OOM-on-estimate bug (it currently calls `RKDatabase::from_file_path` per input just to count k-mers — loading every entry into memory before deciding whether the merge would OOM).
2. Flip the default so streaming is the safe path and admission control hard-routes (not warns) when the estimate exceeds budget.
3. Add RAII + a process-unique temp subdir + a startup stale-shard sweep (the prefix-cache path has no RAII today).
4. Route `PyDatabase.merge` through the bounded path with parameters exposed.

The dense-storage side (`u64` counter) is the larger net-new build.

</domain>

<decisions>
## Implementation Decisions

### Merge Budget & Admission Control (MERGE-01, MERGE-02)
- **D-01: Fix the estimator + hard-route to streaming.** `should_use_streaming()` (`src/database/format.rs`) already estimates `total_kmers × ~24B` and compares to `max_memory_usage`, but (a) it obtains `total_kmers` by calling `RKDatabase::from_file_path(path)` per input — which loads **every entry** into RAM, OOMing the process *during the estimate* before the merge even starts; and (b) today it only *selects* the streaming path, it does not enforce a hard cap inside the in-memory path. Fix both:
  - **Estimate from metadata, not full load** — read the persisted `total_kmers` from the `.rkdb` header (or fall back to `file_size / 20` × a safety factor) WITHOUT materializing entries. The 42-byte header already stores `total_kmers`; a header-only / file-size estimator is the fix.
  - **Hard-route** — when the estimate exceeds the budget, route to streaming unconditionally (no "warn and continue in-memory"). MERGE-02's "routes to streaming when budget exceeded" is a hard requirement, not advisory.
  - **Budget default stays auto-detected** — keep the existing `get_default_memory_limit()` (~50% of system RAM on Linux via `/proc/meminfo`, 32 GB fallback) as the zero-config default, with `--max-memory` as the explicit override. No new mandatory flag.

### In-Memory Merge Path Disposition (MERGE-01, compatibility)
- **D-02: Retain `merge_databases_inmemory` behind an explicit mode — do NOT remove it.** The `--merge-mode auto|memory|streaming` flag surface already exists; keep it. The in-memory path is a legitimate fast path for small/test merges (no temp-file overhead). Rules:
  - `auto` (default): small inputs (estimate ≤ budget) may use in-memory; large inputs **hard-route** to streaming per D-01.
  - `streaming`: always streaming.
  - `memory`: explicit in-memory. As a safety net, when `memory` is explicitly chosen but the estimate exceeds budget, **reject with a clear error** (or emit a loud warning and proceed) — do not silently OOM. Planner picks reject-vs-warn; reject is safer for MERGE-01's "no longer OOM" promise.
  - Removing the in-memory path would break existing `--merge-mode memory` callers for no milestone benefit; keeping it bounded (D-01) satisfies MERGE-01.

### Dense Storage Scope (DENSE-01, DENSE-02)
- **D-03: Dense `u64` is RAM-only — the `.rkdb` v2 on-disk format stays byte-identical.** The `u128`→`u64` packing applies to the **in-memory** counting and merge structures only (the `DashMap` key in `KmerCounter`, and the in-memory merge accumulator); `KmerEntry` on disk remains `u128` kmer (16 B) + `u32` count (4 B) = 20 B, little-endian, version 2.
  - Rationale: REQUIREMENTS targets "roughly halving **counting memory**" (RAM). PROJECT.md mandates preserving `.rkdb` v2 "unless a specific perf win justifies a breaking change" — disk savings do not justify a format bump + migration in this milestone. RAM-only u64 satisfies the goal with **zero format risk**.
  - DENSE-02 ("transparent to existing readers") is satisfied trivially: readers see the same v2 bytes. Phase 1/2 committed golden `.rkdb` + sha256 baselines **do not break**.
  - The write path widens `u64`→`u128` when serializing (zero-extension); negligible cost.
  - **On-disk dense packing (v2 dense flag or v3) is explicitly deferred to v2** — see Deferred. This deferral *is* the DENSE-02 "surface the tradeoff" obligation being met.

### Dense Verification (DENSE-03)
- **D-04: Verify dense correctness at the decoded (kmer-string, count) level, NOT the raw-integer level.** The `u64` and `u128` encoders pack bits differently — `encode_kmer_bytes` aligns the k-mer to bit 64, `encode_kmer_bytes_u128` aligns to bit 128 — so the same biological k-mer yields **different raw integer values** in the two widths. Canonicalization (`min(kmer, revcomp)`) is therefore width-internal: as long as encode→canonical→increment is self-consistent inside the `u64` path, per-k-mer **counts** match the `u128` path. The differential assertion compares decoded k-mer strings + counts, using the Phase 1/2 golden `.rkdb` baselines (k ∈ {21, 32, 64} × canonical × sorted) as ground truth. A raw-integer equality assertion would be wrong and would fail.
- **D-05: `u128`-vs-`u64` differential is the sharp correctness tool** (analog to Phase 2's `--threads 1`-vs-`N` differential, D-10 there). k-mer counting is integer addition (commutative/associative), so any count divergence between the `u64` and `u128` paths on the same input is a packing/canonicalization bug, not an ordering artifact. The differential catches exactly the DENSE-03 failure mode.

### Streaming Failure Cleanup & Interruption (MERGE-03)
- **D-06: RAII on the prefix-cache path + process-unique temp subdir + startup stale-shard sweep. No signal handler. Not resumable.**
  - The streaming path (`streaming_merge.rs`) already has RAII (`TempFileManager::Drop`, `StreamingMergeIterator::Drop`). The **prefix-cache path** (`prefix_cache_merge.rs`) does NOT — it only `remove_file`s on the success path (`prefix_cache_merge.rs:322-326`); panic / early return / `kill` leaks shards. **Add an RAII guard mirroring the streaming path's `TempFileManager`** so `Drop` removes the shards on any unwind.
  - **Process-unique temp subdir:** write all temp shards under `temp_dir/rustkmer-merge-<pid>-<random>/` (not loose in `temp_dir`). This makes orphan detection unambiguous and avoids collisions between concurrent merges.
  - **Startup stale-shard sweep:** on merge start, sweep `temp_dir` for `rustkmer-merge-*` dirs that are orphaned (no matching live process, or older than a TTL) and remove them. This is the defense against `kill -9` / power loss, because `Drop` does **not** run under `SIGTERM`/`SIGKILL`/default `SIGINT` handlers (they terminate the process without unwinding).
  - **No signal handler** in Phase 3 — installing a `ctrlc` handler for graceful Ctrl-C cleanup is soundness-sensitive scope creep; the subdir + startup-sweep combo covers the disk-exhaustion risk without it. (Deferred to v2.)
  - **Not resumable** — a failed/interrupted merge is a clean restart (shards swept, merge re-runs). Checkpoint/resume is v2 complexity.
  - This decision also closes the CONCERNS.md test-coverage gap: "Streaming-merge error paths untested" / "partial-failure cleanup" become asserted.

### Carry-Forward (locked from prior phases, do not re-litigate)
- **Public API stability** (Phase 2 D-05): the `KmerCounter` / `KmerEntry` public surfaces stay unchanged; the `u128`→`u64` swap is internal. The ROADMAP's "PackedKmer enum" lives inside the counter/memory layer, not the persistence or PyO3 surface.
- **Golden-capture-first sequencing** (Phase 1 D-10): the `u128` golden baselines already exist (captured in Phases 1/2) — reuse them as ground truth; do not re-derive. If any NEW baseline is needed, capture BEFORE refactoring.
- **Coverage matrix** (Phase 1 D-13): `k ∈ {21, 32, 64}` × canonical × sorted — echo for the dense differential. k=21 and k=32 exercise `u64`; k=64 exercises `u128` (the unchanged path).
- **Mixed-k merge rejected** (existing behavior): `KmerCounter::merge` returns `Err` on differing `kmer_length`; `validate_compatibility` guards DB-level merge. Dense does not change this — a u64 (k≤32) DB and a u128 (k≤32) DB represent the same on-disk v2 bytes, so they merge identically; mixing different `k` remains an error.

### Claude's Discretion
- **`PackedKmer` representation:** the roadmap names a "PackedKmer enum" — the planner chooses between (a) an enum `Kmer::U64(u64)` / `Kmer::U128(u128)` keyed off `kmer_length` at `KmerCounter::new`, (b) a parallel `KmerCounterU64` type selected at construction, or (c) a generic-over-width design. The constraint is: public API unchanged (carry-forward) and `DashMap` key type swaps internally. Pick the lowest-blast-radius option.
- **Estimator source:** header `total_kmers` field vs `file_size / 20` vs both-with-fallback — planner's call, as long as it does NOT load entries.
- **Startup-sweep TTL / orphan-detection heuristic** (PID-liveness check vs age-based TTL) — planner picks; age-based is simpler and portable.
- **`memory` mode over-budget behavior** (reject vs loud-warn, D-02) — planner picks; reject is safer.
- **Whether dense u64 also applies to the in-memory `RKDatabase`/`DatabaseQuery` read path:** out of scope unless the change is zero-cost while touching the counter. The milestone goal is counting+merge memory; query-path memory is not the stated bottleneck (PROJECT.md Out of Scope: query micro-optimization). Default: leave the read path on `u128`.
- **Exactly how `PyDatabase.merge` exposes budget/strategy** (kwargs `max_memory=` / `merge_mode=` mirroring CLI) — planner decides, but it MUST route through the same bounded core path as the CLI (MERGE-04).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap (the WHAT authority)
- `.planning/REQUIREMENTS.md` §"Bounded Merge" — MERGE-01..04 definitions; §"Dense Storage" — DENSE-01..03 definitions (esp. DENSE-02's "format bump surfaced as explicit decision"); §"Out of Scope" table (scope-creep guardrail — on-disk format, minimizer counting, query opt); §Traceability (MERGE-* / DENSE-* → Phase 3). Treat as the locked WHAT in lieu of an `03-SPEC.md`.
- `.planning/ROADMAP.md` §"Phase 3: Memory Safety" — phase goal, 6 success criteria, 5 seed plans (`03-01`..`03-05`).
- `.planning/PROJECT.md` §Context ("Merging — the secondary lever": `merge_databases_inmemory` defeats streaming; no admission control), §Constraints (`.rkdb` v2 preservation, dual-surface, existing-stack floor), §Key Decisions.

### Prior phases (carry-forward discipline)
- `.planning/phases/02-parallel-counting/02-CONTEXT.md` — **D-04/D-05** dashmap swap with public API preserved (dense swap reuses this discipline), **D-10** 1-vs-N differential (analog → u128-vs-u64 differential, D-05 here), default-sort / `--threads` precedence (context only).
- `.planning/phases/01-foundation-quality/01-CONTEXT.md` — **D-10** golden-capture-before-refactor sequencing (reuse the existing u128 golden baselines), **D-13** coverage matrix `k ∈ {21,32,64} × canonical × sorted`, CI clippy `-D warnings` gate, log-facade migration (merge modules emit via `log::`, not `println!`).

### Codebase maps (grounding)
- `.planning/codebase/ARCHITECTURE.md` — Merge Flow (3 strategies), `KmerEntry` 20-byte layout, "Memory management" cross-cutting (`max_memory` flag, streaming/prefix-cache exist to bound merge memory), "Scaling Limits — Single-process memory-bound merge" (no upper bound before allocating; 4-prefix/256-bucket cap).
- `.planning/codebase/CONCERNS.md` — **Performance Bottleneck:** `merge_databases_inmemory` loads every k-mer into one hashmap (`format.rs:808-824`); **Performance Bottleneck:** `u128` doubles memory for k ≤ 32; **Fragile Area:** `prefix_cache_merge.rs` (manual `try_into().unwrap()` byte-slice conversions assuming 20-byte layout — centralize `const RECORD_SIZE`); **Test Coverage Gaps:** "Streaming-merge error paths untested" / "partial-failure cleanup" (the `remove_file` branch at `prefix_cache_merge.rs:309-313`), memory-threshold branch selection, `sys_info::mem_info()` fallback; **Scaling Limits:** in-memory path has no upper-bound check; u32 count saturates at `u32::MAX` (SAT-01/02 deferred).
- `.planning/codebase/STACK.md` — rayon / memmap2 / hashbrown / ahash / dashmap / sys_info / tempfile already in the dep graph; release profile (`lto`, `codegen-units=1`, `panic="abort"`) to preserve when editing `Cargo.toml`. NOTE: `panic="abort"` means `Drop` does NOT run on panic-unwind — relevant to D-06 (RAII alone is insufficient for panic if `panic=abort`; the subdir+sweep is the real defense).

### Source hot-path (the integration points)
- `src/database/format.rs` — `merge_databases` dispatch (~`:640-690`), `should_use_streaming` estimator (~`:692-708`, the OOM-on-estimate bug), `merge_databases_inmemory` (~`:766-901`, hashbrown `HashMapBrown<u128,u32>`, no bound), `merge_databases_streaming` (~`:710-764`), `KmerEntry` (`:196-238`, 16 B u128 + 4 B u32, little-endian, weird `count_le>1M → count_be` read workaround), `DatabaseHeader` (42 B, `DATABASE_VERSION=2`).
- `src/database/streaming_merge.rs` — `ExternalMerger`, `StreamingMergeIterator`, `DatabaseStreamIterator`; **`TempFileManager` (RAII `Drop`, ~`:113-176`)** and **`StreamingMergeIterator::Drop` (`:398-414`)** — the RAII pattern to mirror on the prefix-cache path.
- `src/database/prefix_cache_merge.rs` — `ExternalSortMerger::new` (`:32-85`), fixed `num_buckets = 256` (4-prefix, `:40`), temp-file naming (`{prefix}_{ts}.chunk`, `:143`; `ext_sort_{dna}_file_{idx:03}.tmp`, `:254-256`), **manual-only cleanup** (`:322-326`, the gap), the `try_into().unwrap()` 20-byte assumptions (`:461,463,645,646,679,680,917,918`), `sys_info::mem_info()` threshold reads.
- `src/cli/commands/merge.rs` — `MergeArgs` / flag parsing (`--max-memory`, `--merge-mode auto|memory|streaming`, `--use-prefix-cache`, `--batch-size`, `--keep-intermediate`, `--temp-dir`, `--num-threads`, `--check-compatibility`), `parse_memory_size`, `MergeConfig` assembly (~`:307-333`).
- `src/database/merge_config.rs` (or wherever `MergeConfig` lives) — `get_default_memory_limit()` (~`:142-163`, 50% `/proc/meminfo`, 32 GB fallback), `max_memory_usage` field.
- `src/hash/table.rs` — `KmerCounter` (`DashMap<u128, u32>` at `:22` — the dense swap site), `new(kmer_length, …)` (`:49`, where k-width is known → select u64 vs u128), `increment`/`merge` overflow semantics, `memory_usage()` estimate (`:283`).
- `src/kmer/encoding.rs` — **u64 AND u128 encode/decode/reverse_complement already exist** (`encode_kmer_bytes`/`decode_kmer`/`reverse_complement` for u64; `encode_kmer_bytes_u128`/`decode_kmer_u128`/`reverse_complement_u128` for u128); `encode_kmer_auto` (`:299`) already picks u64 for k ≤ 32; `MAX_KMER_SIZE_IN_U64=32` (`:14`), `MAX_KMER_SIZE_IN_U128=64` (`:17`). The dense primitives are present — Phase 3 wires them into the counter.
- `pyo3/src/database.rs` — `PyDatabase::merge` (`#[staticmethod]`, ~`:1348-1391`) currently uses `MergeConfig::default()` with no strategy/budget params exposed — the MERGE-04 site.
- `Cargo.toml` — `dashmap`, `sys_info`, `tempfile`, `rayon` present; check whether a new dep is needed for the subdir-randomization (likely `tempfile::TempDir` already covers it) before adding anything.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Merge machinery already exists** — `should_use_streaming()` estimator/router, `--max-memory`/`--merge-mode`/`--use-prefix-cache` flags, `get_default_memory_limit()` auto-budget, three merge paths (`inmemory`/`streaming`/`prefix_cache`), and RAII guards on the streaming path. Phase 3 fixes the estimator, flips defaults, and adds RAII to the prefix-cache path — it does NOT build merge from scratch.
- **`TempFileManager` RAII pattern** (`streaming_merge.rs:113-176`) — `Drop` calls `cleanup()` which `remove_file`s each tracked path; mirror this for the prefix-cache path's shards.
- **`tempfile` crate** (already a dev-dep; check `[dependencies]`) — `TempDir` gives a process-unique, auto-removed temp directory; usable directly for the `rustkmer-merge-<pid>-<rand>/` subdir (D-06) without a new dependency.
- **u64 encode/decode/canonical primitives** (`src/kmer/encoding.rs`) — `encode_kmer_bytes`, `decode_kmer`, `reverse_complement`, `encode_kmer_auto` already implement the u64 path; `MAX_KMER_SIZE_IN_U64=32` is the boundary constant. No new encoding code needed; just wire the counter to use u64 keys for k ≤ 32.
- **Phase 1/2 golden `.rkdb` + sha256 baselines** (`tests/fixtures/`) — the DENSE-03 ground truth (k ∈ {21,32,64} × canonical × sorted). Reuse directly for the u128-vs-u64 differential (D-04/D-05).
- **`tests/common/`** factories + `temp_file!`/`temp_fasta!` + `tests/common/temp_files.rs` `TempFileManager` (test-side) — reuse for merge-cleanup / stale-shard-sweep tests.
- **`proptest 1.5`, `tempfile`, `rand`/`rand_chacha`** dev-deps — available for property-based dense-correctness tests.

### Established Patterns
- **Dual-surface shared core:** counter/merge changes in `src/hash/` + `src/database/` flow to both `count.rs`/`merge.rs` and `pyo3/src/{counter,database}.rs` automatically — the delivery vehicle for MERGE-04 (PyDatabase inherits the bounded merge by calling the same core fn).
- **Internal-swap-preserves-public-API** (Phase 2 D-05): the `RwLock<HashMap>`→`DashMap` swap kept the public surface identical; the `u128`→`u64` dense swap follows the same discipline.
- **Golden-capture-before-refactor + differential** (Phase 1 D-10 / Phase 2 D-10): the proven correctness discipline — reused for DENSE-03 (u128-vs-u64 differential against existing golden baselines).
- **log-facade + clippy `-D warnings` gate** (Phase 1): new merge diagnostics use `log::info!`/`warn!` (not `println!`); any new dep (e.g. for sweep) must compile clean under `-D warnings` on both crates. Note `src/cli/` is the only module with the print-macro allowlist.
- **Layered config** (`ConfigManager`, `RUSTKMER_` env prefix): `--max-memory` follows the flag→config→env layering already in `merge.rs`.

### Integration Points
- `src/database/format.rs::merge_databases` — flip default + hard-route (D-01); fix `should_use_streaming` estimator to header/file-size (D-01).
- `src/database/format.rs::merge_databases_inmemory` — keep, but gate behind explicit `memory` mode + reject-when-over-budget (D-02).
- `src/database/prefix_cache_merge.rs::ExternalSortMerger` — add RAII guard; write shards under process-unique subdir; accept a startup-sweep hook (D-06); centralize the 20-byte `RECORD_SIZE` constant (CONCERNS fragile-area fix while touching it).
- `src/hash/table.rs::KmerCounter` — internal key type `u128`→width-selected (`PackedKmer` enum or parallel type) for k ≤ 32 (D-03); `new()` selects width from `kmer_length`.
- `pyo3/src/database.rs::PyDatabase::merge` — route through bounded core; expose `max_memory`/`merge_mode` kwargs (MERGE-04, D-02).
- `Cargo.toml` — only if a new dep is truly needed (likely none — `tempfile` covers subdir randomization).

</code_context>

<specifics>
## Specific Ideas

- **The estimator's OOM-on-estimate bug is the single most important merge-side fix.** `should_use_streaming` calls `RKDatabase::from_file_path` per input to read `total_kmers` — but `from_file_path` materializes every entry. So the very function meant to *prevent* OOM loads the full dataset into RAM first. On a human-scale merge this OOMs during the estimate, before the merge strategy is even chosen. The fix (read the header's persisted `total_kmers` or use `file_size / 20`) is small but load-bearing for MERGE-01/02.
- **`panic = "abort"` (release profile) means RAII `Drop` does NOT run on a panic.** This is why D-06 does NOT rely on RAII alone for the interruption case — the process-unique subdir + startup stale-shard sweep is the real defense against `kill -9` / panic-abort / power loss. The planner must not assume `Drop` cleans up on abort.
- **DENSE-03 correctness is a decoded-string comparison, not an integer comparison** — because u64 and u128 pack the same k-mer to different bit positions. A naive `assert_eq!(u64_kmer, u128_kmer)` is wrong; decode both and compare `(String, count)`. The golden baselines make this cheap.
- **The roadmap's 5 seed plans map cleanly onto these decisions:** 03-01 (streaming default + admission control = D-01/D-02), 03-02 (RAII temp guards = D-06), 03-03 (u64 PackedKmer = D-03), 03-04 (dense correctness + v2 compat = D-04/D-05 + D-03), 03-05 (PyDatabase bounded merge = MERGE-04). The planner can keep this decomposition.
- **Both accepted deviations are deliberate, not drift:** (a) keeping the in-memory path (D-02) rather than removing it — preserves a useful fast path and backward compat while bounding it; (b) RAM-only dense (D-03) rather than touching disk — honors the v2-preservation constraint and keeps golden fixtures intact. Downstream agents should not "undo" these to be conservative; the user weighed and accepted them.

</specifics>

<deferred>
## Deferred Ideas

- **On-disk dense `u64` packing** (`.rkdb` v2 dense flag or v3) with a migration path — deferred to v2. RAM-only u64 (D-03) satisfies the milestone's "halving counting memory" goal without a format bump; the disk win is not worth the compatibility/migration cost this round. This deferral fulfills DENSE-02's "surface the tradeoff as an explicit decision" obligation. Re-evaluate if Phase 4's benchmark shows disk I/O (not RAM) is the bottleneck.
- **Adaptive / configurable shard granularity** (5-/6-prefix) for the prefix-cache merge on very large inputs — `MINIM-03` (v2 "Memory-Bounded Counting"). Phase 3 keeps the fixed 4-prefix/256-bucket scheme.
- **Resumable streaming merge** (checkpoint progress mid-merge, resume after crash) — v2 complexity. Phase 3: failed/interrupted merge = clean restart (D-06).
- **Signal-handler-based graceful Ctrl-C cleanup** (`ctrlc` crate) — v2; soundness-sensitive scope creep. Phase 3 covers disk-exhaustion via subdir + startup sweep (D-06).
- **Minimizer / signature-partitioned bounded-memory *counting*** (`MINIM-01`/`MINIM-02`) — v2; distinct from Phase 3's dense-storage goal (Phase 3 halves per-k-mer memory; minimizer partitioning bounds total memory regardless of dataset size).
- **Configurable counter width / saturation warning** (`SAT-01`/`SAT-02`, u16/u32/u64 counts) — v2; Phase 3 keeps `u32` counts with existing overflow semantics.
- **Dense u64 on the query/read path** (`DatabaseQuery`, mmap, in-memory `RKDatabase`) — out of scope unless zero-cost while touching the counter; the milestone goal is counting+merge memory, and query memory is not the stated bottleneck (PROJECT.md Out of Scope).

</deferred>

---

*Phase: 03-memory-safety*
*Context gathered: 2026-07-02*
