---
phase: 03-memory-safety
reviewed: 2026-10-09T12:18:13Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - src/database/prefix_cache_merge.rs
  - tests/prefix_cache_output_order_tests.rs
findings:
  critical: 0
  warning: 6
  info: 9
  total: 15
status: issues_found
---

# Phase 3: Code Review Report (streaming-writer gap-closure round, plan 03-17)

**Reviewed:** 2026-10-09T12:18:13Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Full re-review of `src/database/prefix_cache_merge.rs` and `tests/prefix_cache_output_order_tests.rs` at standard depth, with cross-file verification of every contract the module depends on (`format.rs` header/`KmerEntry` layout, `DatabaseStreamIterator`, `canonical_kmer_u128` / `reverse_complement_u128`, `temp_lifecycle.rs`, and the sole production caller `merge_databases_prefix_cache_to_path` at `src/database/format.rs:1724-1844`). All 12 unit tests in the module and all 3 integration tests in the order-proof file were run and pass.

**Verified closed by this round's delta (traced through code, not assumed from green tests):**

- Prior **CR-01** — the streaming bucket writer's mixed-canonical corruption is now double-guarded: `ExternalSortMerger::new` forces the sorting (hashmap) writer when the folded mode is canonical AND any input header is not (`prefix_cache_merge.rs:174-190`), and `merge_single_prefix_streaming` refuses a descending run at both record-consumption sites (`:998-1002`, `:1037-1041`). I traced every path by which a record can leave a shard buffer (initial heap push, main-loop pop, inner-loop duplicate consumption) and each record is validated against its own file's previous key exactly once; on refusal the partially-written merged file is abandoned inside the RAII temp dir, so no corrupt bytes escape. The k-way-merge invariant (each live file holds exactly one heap entry mirroring its buffer front) holds at every push/pop site.
- Prior **CR-02 / WR-03** — `get_prefix_4mer` selects the HIGH byte (`:1153-1156`, monotone in the key, `saturating_sub` arm correct for k<4), and phase 1 stores the same canonicalized key it bucketed by (`:356-366`). Index-order concatenation is therefore globally ascending and the `sorted: true` header is truthful; pinned end-to-end by the strict `windows(2)` assertions in the order-proof tests.
- The `read_batch_from_file_sync` partial-record carry (CR-01 of 03-16) is correct across batch boundaries: the tail is retained, only newly read bytes count toward `BATCH_BYTES`, read errors propagate instead of masquerading as EOF.

**The test file is clean.** `tests/prefix_cache_output_order_tests.rs` builds its oracles independently of production merge code, asserts fixture honesty (already-canonical B keys, the differing-high-byte vacuousness guard, the summed all-T/0x000000 fold), and its strict-ascending + `total_kmers` assertions cannot be satisfied by the pre-03-17 duplicate/un-summed shapes. No defects found in it. The two vacuous tests flagged below (IN-11) live in the source file's own `#[cfg(test)]` module.

**No critical findings this round.** The strongest remaining defect is WR-01 (carried): the failed-bucket "PRESERVED for recovery" promise — now also baked into the user-facing abort error this delta added — is voided by the merger's own `Drop` before the caller ever sees the error.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: The failed-bucket "shard files PRESERVED for recovery" promise is voided by RAII Drop before the error reaches the caller (carried, still open; the abort message making the false promise is new this round)

**File:** `src/database/prefix_cache_merge.rs:683-691` (abort error promising preservation under a named dir), `:551-571` (`should_remove_shards` decision + "PRESERVED on disk for recovery" log), `:306-307` (every shard path registered up front), `:1510-1543` (`Drop` removes every registered shard then `TempDir::close()` removes the whole tree); sole production caller `src/database/format.rs:1805` (`merger.external_sort_merge(&temp_output)?` drops the merger on return)
**Issue:** When a bucket merge fails, phase 2 deliberately keeps that bucket's shards and returns an error stating they "were PRESERVED for recovery under '<dir>'". But the error propagates through `external_sort_merge`'s `?` (line 255) to `merge_databases_prefix_cache_to_path`, whose own `?` (format.rs:1805) drops `merger` at function exit. `Drop` then `remove_file`s every path in `self.shard_paths` — which includes exactly the failed buckets' shards, kept precisely so they would survive — and `dir.close()` deletes the entire `rustkmer-merge-<rand>` tree. The directory named in the error does not exist by the time the operator reads it. The 03-17 delta made this worse in one respect: the false promise now ships in the returned `ProcessingError` (not just a mid-flight log line). The unit test `failed_bucket_aborts_the_merge_with_err` (`:2010-2052`) asserts `shard_path.exists()` while `merger` is still alive — before the `?` chain triggers `Drop` — so it proves the wrong moment. Recovery-by-rerun is still possible (the inputs are intact), so no permanent data loss; but the advertised recovery path is unreachable in every default-configuration production flow.
**Fix:** Either make the promise true or stop making it. (a) In `merge_prefix_buckets`, on the `error_count > 0` path, disarm cleanup before returning: `if let Some(dir) = self.merge_temp_subdir.take() { let kept = dir.keep(); /* name `kept` in the error */ }` — mirroring the `keep_intermediate` arm of `Drop`; the stale-dir sweep (`temp_lifecycle::sweep_stale_merge_dirs`) eventually reclaims it. Or (b) reword the error to state the shards were cleaned up and that `--keep-intermediate` preserves them. Either way, extend `failed_bucket_aborts_the_merge_with_err` to assert the on-disk state AFTER the merger is dropped.

### WR-02: u32 count accumulation can overflow — debug panic, silent wrap in release; the in-memory route saturates (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:782` (`*kmer_counts.entry(kmer).or_insert(0) += count`), `:970` (`current_count += top.count`), `:1043` (`current_count += consumed.count`)
**Issue:** Both per-bucket writers sum counts with plain `+=`. A merged count exceeding `u32::MAX` panics in debug builds and silently wraps in release — and the WR-04 conservation check cannot catch it, because it compares record COUNTS, not count VALUES; the wrapped value flows straight into the output records under a truthful-looking header. The in-memory merge route deliberately uses `saturating_add`; the prefix-cache route — selected precisely for merges too large for memory, where summing many high-count inputs is most reachable — keeps the weaker arithmetic. The in-code comment (:986-989) records this as deliberately deferred to 03-REVIEW-DISPOSITION.md (WR-02, disposition `open`); it remains a live defect in an in-scope file.
**Fix:** `*e = e.saturating_add(count)` in the hashmap writer; `current_count = current_count.saturating_add(top.count)` / `.saturating_add(consumed.count)` at both streaming sites — matching the in-memory route's policy.

### WR-11: The metadata JSON sidecar is written to a path the to-path route guarantees to delete (new this round)

**File:** `src/database/prefix_cache_merge.rs:1436-1442` (`output_path.with_extension("json")` write), `:1411-1435` (the metadata block); route handoff `src/database/format.rs:1801-1816` (output written to `<merge-subdir>/external_sort_merge_output.tmp`, only the `.tmp` is renamed to the destination), Drop at `prefix_cache_merge.rs:1510-1543`
**Issue:** `concatenate_final_output` unconditionally writes a `create_metadata` JSON next to `output_path`. On the only production route, `output_path` is the temp file INSIDE the merger's RAII subdir: the caller renames only the `.rkdb` temp file to the destination, and the merger's `Drop` then deletes the whole subdir — sidecar included. The merged database at its final destination never receives a metadata sidecar; the serialize+write work executes on every merge and its result is guaranteed garbage. With `--keep-intermediate` the sidecar survives, but at a random `rustkmer-merge-<rand>/` path, not next to the output. Either the sidecar is supposed to accompany the output (then it is silently lost — a route-parity defect: databases built via the `save` path do get one, `src/core/database/persistence.rs:77`), or it is not (then the block is dead work).
**Fix:** Move the sidecar write out of `concatenate_final_output` into `merge_databases_prefix_cache_to_path`, after the rename/copy succeeds, keyed on the FINAL `output_path` (`output_path.with_extension("json")`); or delete the block if merged databases are not meant to carry sidecars.

### WR-12: `ExternalSortMerger::new` panics on an empty input list — public API, unguarded index (new this round; same class as carried WR-06 but a distinct, in-scope site)

**File:** `src/database/prefix_cache_merge.rs:129` (`RKDatabase::read_header_of(&input_files[0])`)
**Issue:** The constructor indexes `input_files[0]` before any guard. `ExternalSortMerger` is re-exported as public API (`src/database/mod.rs:23`) with a `pub fn new`, so any external caller (PyO3 bindings, downstream crates) passing an empty `Vec` gets an index-out-of-bounds panic instead of a `ProcessingError`. The sole in-crate caller guards this itself (format.rs:1738-1742, "WR-06 defence in depth"), but the public constructor remains the panic surface; the project's own gap-closure discipline added exactly this class of guard to the merge entry points.
**Fix:** At the top of `new`: `if input_files.is_empty() { return Err(crate::error::ProcessingError::new("At least one input database is required")); }`.

### WR-13: Zero-length merged buckets are deleted even under `--keep-intermediate`, contradicting the flag's documented "keeps everything" contract (new this round)

**File:** `src/database/prefix_cache_merge.rs:1204-1208` (unconditional `let _ = std::fs::remove_file(&prefix_file);` on the empty-file branch); contract stated at `:46-47` ("`keep_intermediate` keeps everything, as its name promises") and `:1238-1240` (the correctly-gated non-empty branch)
**Issue:** Phase 3 removes a zero-length merged bucket file unconditionally, while every other intermediate removal in the same loop and in `should_remove_shards` is gated on `!self.keep_intermediate`. Both per-bucket writers can legitimately leave an empty merged file (all shards shorter than one 20-byte record), so the branch is reachable. Impact is small (an empty file), but the flag's semantics are stated absolutely in this same file, and the inconsistency invites the next reader to trust the wrong pattern.
**Fix:** Gate it like the sibling branch: `if !self.keep_intermediate { let _ = std::fs::remove_file(&prefix_file); }` (the warning log can stay unconditional).

### WR-14: No k-mer-size range validation — headers with `kmer_size` in 65..=127 or 0 pass every check, then shift-overflow (debug panic) or silently collapse every canonical key to 0 (new this round)

**File:** `src/database/prefix_cache_merge.rs:129-130` (`kmer_size = first_header.kmer_size as usize`, no range check), `:356-357` (canonicalization with that k), `:1153-1156` (`get_prefix_4mer`'s `kmer >> 2*(k-4)`); sentinel `src/kmer/encoding.rs:326-329` (`reverse_complement_u128` returns 0 for `length > 64`), `MAX_KMER_SIZE_IN_U128 = 64` at `encoding.rs:17`
**Issue:** `read_header_of` checks only `data_offset` (format.rs:515-520) and `validate_header_compatibility` checks only cross-input equality (format.rs:1875-1877) — and even `DatabaseHeader::validate()` accepts 1..=127 (format.rs:273), wider than the u128 encoding's hard limit of 64. A foreign or corrupt header with k in 65..=127 therefore enters the merge unvalidated, and then: (a) `get_prefix_4mer` computes `kmer >> 128` for k=68+ — panic in debug, shift-amount masked in release so bucketing silently degenerates toward the low-byte shape CR-02 just fixed; (b) far worse, whenever `self.canonical` is true, `reverse_complement_u128`'s `return 0` sentinel makes `canonical_kmer_u128` = `min(kmer, 0)` = 0 for EVERY record — all k-mers collapse to key 0 with counts summed, emitted under a truthful-looking `sorted: true` header with `total_kmers = 1`. k=0 collapses identically (loop runs zero times, rc=0). The crate's own writers cannot produce these headers, but the codebase's stated policy for corrupt files is loud rejection, not silent garbage (cf. the data_offset comment at format.rs:51-56).
**Fix:** In `ExternalSortMerger::new`, after reading the first header: `if kmer_size == 0 || kmer_size > crate::kmer::encoding::MAX_KMER_SIZE_IN_U128 { return Err(ProcessingError::new(format!("Unsupported k-mer size {kmer_size} (expected 1..=64) for prefix-cache merge"))); }` — and consider tightening `DatabaseHeader::validate()` separately.

## Info

### IN-02: `Drop` logs the wrong directory when `TempDir::close()` fails (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:1531-1541` (`.take()` then `self.shard_dir().display()`), fallback at `:226-231`
**Issue:** After `self.merge_temp_subdir.take()`, `shard_dir()` falls back to the PARENT `temp_dir`, so the `close()`-failure warning names the parent, not the `rustkmer-merge-<rand>` subdir it failed to remove.
**Fix:** Capture `dir.path()` before `close()` and log that.

### IN-03: Phase-1 log claims parallel bucketing; the loop is serial (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:283-287` ("Using {} worker threads for parallel bucketing") vs the serial `for` loop at `:314`
**Issue:** `split_files_by_prefix` logs a worker-thread count but iterates input files serially; `num_workers` is used only in that misleading log. (Phase 2 IS parallel — the false claim is phase-1-specific.)
**Fix:** Reword the log to describe sequential bucketing (or drop the worker count from it).

### IN-04: Dead duplicate shard readers masked by an impl-level `#[allow(dead_code)]` (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:106` (`#[allow(dead_code)]` on the whole impl), `:1065-1080` (`read_entries_from_file_sync`), `:1474-1489` (`read_entries_from_file` — a byte-for-byte duplicate with a `&self` receiver); also the always-true guard `:364` (`prefix < self.num_buckets` after a `& 0xFF` mask)
**Issue:** Neither reader has any caller in the crate (verified by grep across `src/` and `tests/`); they are near-identical duplicates, and the impl-wide `allow` also masks any FUTURE dead code in the module. `if prefix < self.num_buckets` can never be false (the mask guarantees 0..=255 against 256 buckets).
**Fix:** Delete both readers (or keep one if a caller lands) and narrow the `#[allow(dead_code)]` to specific items if any legitimately need it; delete the dead `prefix` guard.

### IN-05: `total_kmers` reflects the FIRST input only; `estimated_kmers_per_file` and `num_threads` are never read (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:156` (`total_kmers = first_header.total_kmers`), `:210` (`estimated_kmers_per_file: total_kmers`), `:246` ("Total k-mers: {} M" log), `:67` (`num_threads` field, assigned at `:211`, never read — rayon's global pool is used)
**Issue:** The "Total k-mers" progress line reports input[0]'s record count as if it were the merge total, and `estimated_kmers_per_file` (name says per-file estimate; value is the first file's total) is write-only. Misleading observability on a route whose whole point is large merges.
**Fix:** Sum `total_kmers` across all read headers, or relabel the log "first input k-mers"; delete the two dead fields or wire them.

### IN-07: `is_multiple_of` raises the effective MSRV above the documented Rust 1.80+ baseline (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:599`, `:1385`
**Issue:** `u64/usize::is_multiple_of` was stabilized in Rust 1.87; CLAUDE.md declares "Rust 1.80+ stable channel" as the project baseline and `Cargo.toml` pins no `rust-version`, so a 1.80..1.86 toolchain fails to compile with an unexplained error.
**Fix:** Either add `rust-version = "1.87"` to `Cargo.toml` (and update CLAUDE.md), or use `done % 10 == 0` / `processed_kmers % 1_000_000 == 0`.

### IN-08: Final prefix-cache output is flushed but never fsync'd, unlike every other artifact in the route (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:1408` (`writer.flush()?` only — no `sync_all` on the final output file), contrast `:846`, `:1060`, `:1258` (intermediates all `sync_all`)
**Issue:** Every intermediate artifact in the route is fsync'd, but the one file the user keeps is not — a crash after flush can leave a truncated/partial final database.
**Fix:** After `writer.flush()?`, `drop(writer)` then `File::open(output_path)?.sync_all()` — or restructure to hold the `File` and `sync_all()` before dropping.

### IN-09: The 03-16 "canonicalization failure propagates with `?`" claim is vacuous (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:350-357` (comment + `?`); `src/kmer/canonical.rs:72-82` (`canonical_kmer_u128` always returns `Ok`)
**Issue:** `canonical_kmer_u128` has no error path, so the `?` at line 357 can never fire and the comment's error-propagation story is documentation of a guard that does not exist.
**Fix:** Reword the comment to state canonicalization is infallible for validated k, or make `canonical_kmer_u128` return `Err` for `k == 0 || k > 64` (which would also harden WR-14).

### IN-10: A streaming-writer refusal aborts the whole merge with no fallback and no remediation hint (new this round)

**File:** `src/database/prefix_cache_merge.rs:957-965` (refusal error text), `:530-541` (auto-mode dispatch with no post-refusal fallback), `:683-691` (any single bucket failure aborts)
**Issue:** For same-mode inputs no header check can gate (e.g., a large UNsorted non-canonical database — `sorted: false` files are legal), auto mode selects the streaming writer for any bucket over the buffer threshold, the record-level backstop refuses it, and the entire merge fails — although the hashmap writer could complete it correctly. The T-03-57 trade-off is documented and refusing beats corrupting, but neither the refusal message nor the abort error tells the operator the one-flag workaround (`--merge-mode memory`).
**Fix:** Append a remediation line to `descending_run_err` ("re-run with --merge-mode memory to use the sorting per-bucket writer"), or catch the refusal in the auto branch only and retry that bucket with `merge_single_prefix_hashmap`.

### IN-11: Two vacuous tests in the module's test module (new this round)

**File:** `src/database/prefix_cache_merge.rs:1564-1568` (`test_merger_structure` asserts only that a `tempfile::tempdir()` path exists — it tests tempfile, not the merger), `:1549-1562` (`test_external_sort_merger_creation` asserts only `is_err()` on two nonexistent paths — any failure cause passes)
**Issue:** `test_merger_structure` proves nothing about the code under test; `test_external_sort_merger_creation` cannot distinguish "file not found" from a genuine constructor-contract rejection. Pure test noise in an otherwise high-discipline suite.
**Fix:** Delete `test_merger_structure`; in the creation test, assert the error message mentions the missing file (e.g., `assert!(err.to_string().contains("test1.rkdb"))`).

---

_Reviewed: 2026-10-09T12:18:13Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
