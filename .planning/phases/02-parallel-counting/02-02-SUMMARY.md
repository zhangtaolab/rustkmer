---
phase: 02-parallel-counting
plan: 02
subsystem: core-counter
tags: [rust, concurrency, dashmap, rayon, hot-path]
requires:
  - "02-01 (resolve_thread_count + build_global landed — Task 2 relies on the global pool)"
  - "02-04 (D-10 baselines committed — tests/fixtures/parallel_count_baseline/*.json)"
provides:
  - "dashmap = \"6.2.1\" dependency in root Cargo.toml [dependencies] (reuses hashbrown 0.14.5, no version dup)"
  - "KmerCounter.table: DashMap<u128, u32> (was parking_lot::RwLock<HashMap<u128, u32>>)"
  - "Atomic per-key increment via entry().and_modify(flag-then-check).or_insert_with(..) with verbatim u32::MAX overflow message"
  - "rayon chunked par_iter per-record loop in count.rs (process_fasta_file, process_fastq_file) with bounded CHUNK_SIZE=4096"
  - "process_one_record helper shared by fasta+fastq paths"
  - "D-09 default-sort flip: should_sort = !*no_sort (--sort retained as alias)"
  - "test_increment_atomic_under_concurrency + test_overflow_preserved inline tests"
affects:
  - "src/hash/table.rs (KmerCounter.table swap; all read-side methods rewritten for DashMap native API; 2 new inline tests)"
  - "src/cli/commands/count.rs (par_iter per-record loops; D-09 flip; process_one_record helper; verbose diagnostics)"
  - "Cargo.toml (dashmap dep added; [profile.release] preserved)"
  - "02-03 (pyo3/counter.rs — PyCounter swap flows automatically via shared core; the dashmap swap is internal so no pyo3 call-site changes)"
  - "02-05 (differential correctness — asserts post-refactor counts match 02-04 baselines + --threads 1 vs N parity)"
tech-stack:
  added:
    - "dashmap 6.2.1 (crates.io; reuses hashbrown ^0.14.5; pulls lock_api ^0.4.13, parking_lot_core ^0.9.11 — both already transitively present via parking_lot)"
  patterns:
    - "DashMap entry().and_modify(flag-then-check).or_insert_with(..) — atomic per-key upsert (RESEARCH Pattern 1 / Pitfall 6 workaround for FnOnce(&mut V)->() not being able to return Result)"
    - "Rayon chunked-buffer intra-file parallelism (D-01): sequential reader -> bounded Vec<Record> of CHUNK_SIZE -> chunk.par_iter().try_for_each(..) -> chunk.clear(); gzip stays single-threaded (D-02)"
    - "Bypass FastaProcessor/FastqProcessor::process_file callback (W-3): the callback receives &Record tied to the reader lifetime; read owned records directly via bio::io::{fasta,fastq}::Reader::new(..).records() into the chunk Vec instead"
    - "D-09 default-sort: should_sort = !*no_sort (sharded iteration is non-deterministic; default-sort restores reproducibility and aligns with Jellyfish2)"
key-files:
  created: []
  modified:
    - Cargo.toml
    - src/hash/table.rs
    - src/cli/commands/count.rs
decisions:
  - "Used dashmap 6.2.1 (not 6.1) — RESEARCH-verified via crates.io API that 6.2.1 deps include hashbrown ^0.14.5 exactly matching the project's Cargo.lock, so no duplicate-version bloat"
  - "Flag-then-check pattern for the overflow path (not or_try_insert_with) — and_modify is FnOnce(&mut V)->() and CANNOT return Result (Pitfall 6); a local 'let mut overflow = false' mutated inside the closure, checked AFTER the entry chain (shard lock released), is the standard workaround"
  - "Bypassed FastaProcessor::process_file / FastqProcessor::process_file per W-3 — the callback receives &Record borrowed for the reader's iterator lifetime, which cannot be moved into a Vec<Record> that outlives the call so it can be par_iter'd. Read owned records directly via bio::io::{fasta,fastq}::Reader::new(..).records() into our own chunk buffer, then par_iter the buffer. Mirrors the processor's exact reader setup (compression detection, BufReader wrapping, error-message context) so behavior is byte-identical."
  - "Kept the `sort` clap field (renamed the destructure binding to `_sort` to satisfy unused_variables under -D warnings) — D-09 requires --sort to remain a valid alias, just no longer consulted"
  - "Overflow test seeds the k-mer at u32::MAX directly via the private `table` field (accessible from the child test module via `use super::*`) instead of looping u32::MAX times (4 billion iterations — too slow). Documented in a test comment."
metrics:
  duration: ~12 min
  completed: "2026-07-01"
  tasks: 2
  files: 3
status: complete
---

# Phase 02 Plan 02: DashMap Swap + Per-Record Rayon Parallelism Summary

Swapped the counter's storage from a single-global-lock `parking_lot::RwLock<HashMap<u128,u32>>` to a sharded `dashmap::DashMap<u128,u32>` (D-04/D-05) with an atomic per-key `entry().and_modify(flag-then-check).or_insert_with()` increment, and parallelized the per-record encode/canonicalize/increment work in `process_fasta_file`/`process_fastq_file` via rayon chunked `par_iter` over bounded 4096-record buffers (D-01, gzip decompression stays single-threaded per D-02). Flipped D-09 default-sort so output is sorted by default (`--no-sort` opts out; `--sort` retained as an alias).

## What Was Built

### Task 1 — `dashmap` dep + `KmerCounter.table` DashMap swap (PCOUNT-02, PCOUNT-04)

**`Cargo.toml`:** added `dashmap = "6.2.1"` adjacent to the existing `rayon = "1.8"` (same concern: concurrency). `[profile.release]` (`lto=true`, `codegen-units=1`, `panic="abort"`) preserved verbatim. dashmap 6.2.1 pulls `hashbrown ^0.14.5` (exact match to Cargo.lock — no duplicate-version bloat), `lock_api ^0.4.13`, `parking_lot_core ^0.9.11` (both already transitively present via `parking_lot`).

**`src/hash/table.rs`:**
- **Imports:** dropped `use parking_lot::RwLock as ParkingLotRwLock;` and `use std::collections::HashMap;` (no longer used after the swap — clippy-clean); added `use dashmap::DashMap;`.
- **Struct field (D-05 internal swap):** `table: ParkingLotRwLock<HashMap<u128, u32>>` → `table: DashMap<u128, u32>`. All other fields unchanged (`total_kmers`/`unique_kmers` atomics, `kmer_length`, `canonical_mode`, `max_count: u32`).
- **Constructor:** `ParkingLotRwLock::new(HashMap::with_capacity(..))` → `DashMap::<u128, u32>::with_capacity(..)`. The 1..=64 k-mer-size validation stays verbatim.
- **`increment` rewrite (RESEARCH Pattern 1 / Pitfalls 1, 2, 6):** replaced the global-write-lock `match table.get_mut(..) { Some => .., None => insert }` body with the flag-then-check `entry` chain. A local `let mut overflow = false;` is mutated inside `and_modify(|count| { if *count == self.max_count { overflow = true } else { *count += 1 } })`, then `.or_insert_with(|| { unique_kmers.fetch_add(1, Relaxed); 1 })`, then `if overflow { return Err(..) }` AFTER the chain (shard lock released → safe return). The `and_modify` closure is `FnOnce(&mut V) -> ()` and CANNOT return `Result` (Pitfall 6); the flag-then-check is the standard workaround. The EXACT verbatim overflow message `"K-mer count overflow reached maximum value {}"` is preserved (PCOUNT-04 byte-identical behavior). The `entry` chain holds the shard lock for its lifetime → atomic per-key (no lost update / double count under concurrency — PCOUNT-04 invariant).
- **Read-side methods rewritten** for DashMap native API: `get_count` → `self.table.get(&k).map(|r| *r)`; `get_all_counts` → `self.table.iter().map(|r| (*r.key(), *r.value())).collect()`; `get_top_n` → same iter pattern; `filter_by_count` → same iter with filter; `reset` → `self.table.clear();` (no write guard needed); `memory_usage` → `self.table.len() * (24 + 20)`; `merge` → per-entry `entry().and_modify(flag-then-check).or_insert_with(..)` mirroring `increment`'s pattern, with the verbatim `"Count overflow during merge"` error preserved.
- **Two inline Wave-0 tests** (VALIDATION.md):
  - `test_increment_atomic_under_concurrency` — spawns 8 threads via `std::thread::scope` each incrementing the same k-mer 1000 times on a shared `&KmerCounter`; asserts `get_count(k) == Some(8000)`, `total_kmers() == 8000`, `unique_kmers() == 1`. Commutativity property at unit scale.
  - `test_overflow_preserved` — seeds a k-mer at `u32::MAX` directly via the private `table` field (the test module is a child of `table`'s module, so private fields are in scope; avoids 4 billion increment iterations); asserts the next `increment` returns `Err` whose message contains the verbatim `"K-mer count overflow reached maximum value"` prefix and the `4294967295` value, and that the count does NOT wrap past the ceiling.

**Public API byte-identical (D-05):** every existing call site in `count.rs` and `pyo3/src/counter.rs` compiles unchanged. The 8 pre-existing inline tests (`test_basic_increment`, `test_multiple_increments`, `test_top_n`, `test_filter_by_count`, `test_merge`, `test_merge_different_lengths`, `test_reset`, `test_builder`) all pass unchanged.

### Task 2 — Per-record `par_iter` parallelization + D-09 default-sort flip (D-01, D-02, D-09)

**`src/cli/commands/count.rs`:**
- Added `use rayon::prelude::*;` and `const CHUNK_SIZE: usize = 4096;` at module scope (D-discretion; bounded to avoid layering a second memory blowup on top of the u128 DashMap).
- **`process_one_record` helper extracted** — the per-record encode → canonicalize → increment body (previously duplicated inline in both fasta and fastq closures), now shared by both paths (DRY).
- **`process_fasta_file` and `process_fastq_file` rewritten** to bypass `FastaProcessor`/`FastqProcessor::process_file` (W-3 / known integration issue: the callback receives `&Record` borrowed for the reader's iterator lifetime, which cannot be moved into a `Vec<Record>` that outlives the call so it can be `par_iter`'d). Instead reads owned records directly via `bio::io::{fasta,fastq}::Reader::new(..).records()` into a bounded `Vec<Record>` of size `CHUNK_SIZE`, then `chunk.par_iter().try_for_each(|record| process_one_record(..) )?`. `try_for_each` (not `for_each`) so an overflow `Err` from `counter.increment` short-circuits the chunk and propagates. `chunk.clear()` after each `par_iter` bounds memory. The reader setup (compression detection for fastq, BufReader wrapping, error-message context) mirrors the processor's internals exactly so behavior is byte-identical. **gzip decompression stays single-threaded (D-02)** — only the per-record work is parallelized.
- **D-09 default-sort flip:** `let should_sort = if *no_sort { false } else { *sort };` → `let should_sort = !*no_sort;`. Sorted output is now the default (sharded DashMap iteration is run-to-run non-deterministic; default-sort restores reproducibility and aligns with Jellyfish2's sorted output). `--no-sort` is the sole opt-out. The `sort` clap field is RETAINED (D-09 explicit requirement — `--sort` stays a valid alias); the destructure binding is renamed to `_sort` to satisfy `unused_variables` under `-D warnings`.
- **Verbose diagnostics updated:** `"Processing mode: sequential"` → dynamic `"Processing mode: parallel (N rayon workers, 4096 records/chunk)"` reporting the resolved thread count from 02-01's `resolve_thread_count`.

## Verification Results

| Check | Result |
|-------|--------|
| `cargo test --lib hash::table::tests` | 10 passed (8 existing unchanged + 2 new Wave-0 tests) |
| `cargo test --test round_trip_tests` | 23 passed (count round-trip correct under the new parallel path — weak PCOUNT-04 check) |
| `cargo test --test golden_tests` | 34 passed (committed fixtures unaffected — Pitfall 5 confirmed) |
| `cargo test --test parallel_count_tests` | 0 passed, 4 ignored (02-04 stubs; 02-05 un-ignores them) |
| `cargo test` (full root) | 208 lib + all integration binaries + 8 doctests green |
| `cargo clippy --all-targets -- -D warnings` (root) | green (FOUND-01 gate preserved) |
| `cd pyo3 && cargo clippy -- -D warnings` | green (dashmap flows via path dep; FOUND-01 gate preserved on both crates) |
| `cd pyo3 && cargo build` | green (path dep picks up dashmap automatically — RESEARCH Assumption A6 confirmed) |
| `cargo build --release` | green (`[profile.release]` lto/codegen-units=1/panic=abort preserved) |
| Manual smoke: `count -k 21 -i tests/fixtures/k33_test.fasta -o /tmp/p2.rkdb --no-sort` | exit 0; 109 total k-mers, 8 unique |
| Manual smoke: `count -k 21 -i tests/fixtures/k33_test.fasta -o /tmp/p2s.rkdb` (default sort) | exit 0; 8 unique k-mers, sorted |
| Manual smoke: default-sort determinism (two runs, sha256 diff) | byte-identical sha256 — D-09 determinism holds across runs |

### Acceptance Criteria (grep-based)

| Criterion | Expected | Actual |
|-----------|----------|--------|
| `dashmap = "6` in Cargo.toml | >= 1 | 1 |
| `table: DashMap<u128, u32>` in table.rs | 1 | 1 |
| `ParkingLotRwLock\|RwLock<HashMap` in table.rs | 0 | 0 |
| `and_modify` in table.rs | >= 1 | 8 (increment + merge + comments) |
| `K-mer count overflow reached maximum value` in table.rs | >= 1 | 3 (increment body + comment + test) |
| `[profile.release]` `lto = true` / `codegen-units = 1` / `panic = "abort"` | each 1 | 1 / 1 / 1 (preserved) |
| `fn test_increment_atomic_under_concurrency\|fn test_overflow_preserved` in table.rs | 2 | 2 |
| `use rayon::prelude` in count.rs | >= 1 | 1 |
| `CHUNK_SIZE` in count.rs | >= 1 | 8 (const + 7 references) |
| `par_iter\|try_for_each` in count.rs | >= 1 | 16 |
| `let should_sort = !*no_sort` in count.rs | 1 | 1 |
| `if *no_sort { false } else { *sort }` in count.rs (old logic) | 0 | 0 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Clippy `unusual_byte_groupings` on a test hex literal**
- **Found during:** Task 1 GREEN verification (FOUND-01 clippy gate)
- **Issue:** The `test_increment_atomic_under_concurrency` test used `0xCAFEBABE_DEAD_BEEF` (8/8 hex digits); clippy's `unusual_byte_groupings` lint (under `-D warnings`) flagged the grouping as non-uniform and demanded `0xCAFE_BABE_DEAD_BEEF` (4-digit byte groups).
- **Fix:** Rephrased to `0xCAFE_BABE_DEAD_BEEF`. Semantic content unchanged.
- **Files modified:** src/hash/table.rs
- **Commit:** 1c30e5c (folded into the Task 1 commit)

**2. [Rule 1 - Bug] `unused_variables` warning on the now-unconsulted `sort` field**
- **Found during:** Task 2 build
- **Issue:** After the D-09 flip (`should_sort = !*no_sort`), the `sort` field destructured in `execute_count`'s match arm is no longer consulted. `-D warnings` treats `unused_variables` as an error.
- **Fix:** Renamed the destructure binding from `sort` to `_sort` (idiomatic Rust convention for intentionally-unused bindings). The clap `sort` field itself is RETAINED (D-09 explicit requirement: `--sort` stays a valid alias); only the local binding is renamed. Documented the rationale in an inline comment.
- **Files modified:** src/cli/commands/count.rs
- **Commit:** 2511298 (folded into the Task 2 commit)

### Notes

- The plan's `<action>` for the overflow test suggested either (a) looping `u32::MAX` times (too slow — 4 billion iterations), or (b) a test-only setter on `max_count`. I used a third approach: seed the k-mer directly at `u32::MAX` via the private `table` field (accessible because the inline `#[cfg(test)] mod tests` is a child module of `table`'s module, so private fields are in scope via `use super::*`). This requires NO production API surface change (D-05 fully honored — the public API is byte-identical) and the test runs in milliseconds. Documented in the test comment.

## TDD Gate Compliance

Task 1 was marked `tdd="true"`. The plan's `<behavior>` block defines the atomicity + overflow properties, and the `<action>` block orders the implementation (steps a-f) BEFORE the tests (step g) because the properties are behaviorally observable under both the old (RwLock) and new (DashMap) implementations — i.e., the test does not "fail first" in any meaningful sense at the unit level (the RwLock path was already atomic per-key under `&self`, and the overflow guard already existed). The meaningful RED→GREEN gate for this plan is the 02-05 **differential** test (`--threads 1` vs `--threads N` produce identical count maps), which lands in Wave 3 and asserts against the 02-04 baselines.

Git log gate sequence for plan 02-02:
1. **GREEN (Task 1):** `1c30e5c feat(02-02): swap KmerCounter.table to DashMap with atomic per-key increment` — the implementation + both Wave-0 inline tests in a single commit (refactor where the tests verify behavior achievable by both implementations). All 10 `hash::table::tests` pass.
2. **GREEN (Task 2):** `2511298 feat(02-02): parallelize per-record loop via rayon chunked par_iter + D-09 default-sort` — the parallelization + default-sort flip. Verified by `round_trip_tests` (23 passed) + `golden_tests` (34 passed) + manual smoke + sha256 determinism.

No separate `test(02-02)` (RED) commit because the tests are added alongside the implementation they verify, and the RED-vs-GREEN distinction is not meaningful for a same-semantics refactor (the properties hold under both the old and new storage). The deferred RED gate is the 02-05 differential test (Wave 3), which is where a real divergence would surface.

## Threat Mitigations (from plan `<threat_model>`)

| Threat | Disposition | Applied |
|--------|-------------|---------|
| T-02-06 (Tampering — lost update / double count under concurrent increment, Pitfall 1) | mitigate | `DashMap::entry(k).and_modify(flag-then-check).or_insert_with(..)` holds the shard lock for the entry's whole lifetime → atomic per-key. `test_increment_atomic_under_concurrency` directly asserts 8 threads × 1000 increments on one k-mer yield count == 8000. The 02-05 `--threads 1` vs `--threads N` differential will catch any residual divergence. |
| T-02-07 (DoS — DashMap deadlock from nested references, Pitfall 2) | mitigate | The increment path uses a single `entry` chain — no `get()`+`insert()` split, no `Ref`/`RefMut`/`Entry` guard held across another DashMap call. The `merge` method follows the same single-entry-chain discipline. No deadlocks observed in any test run. |
| T-02-08 (Tampering — silent count overflow past u32::MAX) | mitigate | The flag-then-check pattern inside `and_modify` preserves the EXACT error-on-u32::MAX semantics from table.rs:75-80 (PCOUNT-04). `test_overflow_preserved` asserts the error fires with the verbatim message and that the count does not wrap. |
| T-02-09 (DoS — unbounded memory growth from buffering all records) | mitigate | Bounded `CHUNK_SIZE = 4096` Vec with `chunk.clear()` after each `par_iter` — memory is bounded to one chunk (4096 records, ~620 KB for 150 bp PE reads) on top of the DashMap. |
| T-02-10 (Tampering — new dashmap dependency supply-chain risk) | mitigate | RESEARCH §Package Legitimacy Audit: dashmap verdict OK (crates.io since 2019, ~5M weekly, github.com/xacrimon/dashmap). dashmap 6.2.1 verified to pull `hashbrown ^0.14.5` (exact match to Cargo.lock — no duplicate-version bloat). |

## Known Stubs

None for this plan's deliverables. The 4 `#[ignore]`d stubs in `tests/parallel_count_tests.rs` (the capture generator + 3 differential stubs) belong to plan 02-04 and 02-05, not 02-02. They remain `#[ignore]`d as designed; 02-05 (Wave 3) un-ignores and fills them to assert post-refactor counts match the 02-04 baselines.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries were introduced. The only trust boundaries crossed are (a) the rayon-worker → DashMap-shard boundary (mitigated per T-02-06/T-02-07) and (b) the producer-thread → chunk-Vec boundary (mitigated per T-02-09). Both are in-process and intra-trust-domain.

## Self-Check: PASSED

- FOUND: Cargo.toml (modified — dashmap dep added, [profile.release] preserved)
- FOUND: src/hash/table.rs (modified — DashMap swap + 2 new inline tests)
- FOUND: src/cli/commands/count.rs (modified — par_iter + D-09 flip + process_one_record helper)
- FOUND: 1c30e5c (Task 1 commit)
- FOUND: 2511298 (Task 2 commit)
