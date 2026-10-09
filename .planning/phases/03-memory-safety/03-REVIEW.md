---
phase: 03-memory-safety
reviewed: 2026-10-09T14:40:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - src/database/prefix_cache_merge.rs
  - tests/merge_routing_tests.rs
  - tests/prefix_cache_output_order_tests.rs
findings:
  critical: 1
  warning: 5
  info: 9
  total: 15
status: issues_found
---

# Phase 3: Code Review Report (gap-closure round, plan 03-16)

**Reviewed:** 2026-10-09T14:40:00Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Incremental review of the delta since `6b878b7` (commits b0b4189..9cd7795, plan 03-16): the one-site CR-01 fix in `split_files_by_prefix` (canonicalize before bucketing, store the canonicalized `processed_kmer` in the shard, `?` instead of `unwrap_or(entry.kmer)`), the RED-provable mixed-canonical e2e test in `tests/prefix_cache_output_order_tests.rs`, and the ANY-input canonical-header pin with corrected comment in `tests/merge_routing_tests.rs`. This report replaces the 03-12..03-15 round's report; prior findings are traced below. Only the three listed files changed in the range (plus `.planning/` artifacts), so prior line numbers in `src/cli/commands/merge.rs` and `src/database/format.rs` still hold.

**Verified closed by this delta (traced through the code and confirmed empirically, not assumed):**

- Prior **CR-01** — `split_files_by_prefix` now stores the canonicalized key (prefix_cache_merge.rs:308-318), so on the per-bucket **hashmap** writer path the identity bucket key == sort key == stored key holds, the two encodings of one k-mer meet in one bucket and SUM, and index-order concatenation is globally ascending. Confirmed by running the delta's tests (all green) and by a control merge built for this review: mixed-canonical inputs through the hashmap writer produce `[0x00000001/9, 0x000000FF/1]`, ascending, with `query_kmer` returning the summed count.
- Prior **WR-03** (root cause) — closed by the same fix: the raw-record write is gone (:317), and the ANY-input canonical semantics that the old report flagged as unpinned are now pinned NON-coincidentally in both input orders (merge_routing_tests.rs:1299-1330 asserts `canonical: true` with the NON-canonical input first; prefix_cache_output_order_tests.rs:536-542 pins the same with a content-level oracle).

**Key concern in the new findings:** the fix is only half a fix. Phase 1 appends records to each shard in the input's RAW order while storing CANONICAL keys, so a shard from a NON-canonical input is no longer an ascending run — and `merge_single_prefix_streaming` (the per-bucket writer forced by `merge_mode: "streaming"` and auto-selected for any bucket over the buffer threshold) is a k-way heap merge that REQUIRES ascending runs. For mixed-canonical input it still emits non-ascending, un-summed output under the same unconditional `sorted: true` header — the exact CR-01 damage class, now **empirically demonstrated** (new CR-01 below; the delta's e2e tests use tiny inputs that route to the hashmap writer, so this path is untested). Additionally, the fix's error-propagation half is vacuous: `canonical_kmer_u128` has no error path (new IN-09).

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: The 03-16 canonicalization fix holds only for the hashmap bucket writer — the streaming bucket writer still emits non-ascending, un-summed mixed-canonical output under an unconditional `sorted: true` header

**File:** `src/database/prefix_cache_merge.rs:308-318` (canonicalize-and-append in raw input order), `:482-493` (per-bucket writer selection), `:857-884` and `:893-960` (`merge_single_prefix_streaming`'s k-way merge), `:302-304` (comment claiming both bucket writers sum), `:1264` (`sorted: true` written unconditionally); dispatcher passthrough `src/database/format.rs:1134-1151`; consumer `src/database/format.rs:591-596`
**Issue:** Phase 1 iterates each input's records in file order and appends the CANONICALIZED key to the shard in that order. For a NON-canonical input in a mixed set (`self.canonical` true), the input is sorted by RAW key, but `canonical_kmer_u128` returns `min(k, revcomp(k))` (src/kmer/canonical.rs:72-82), which can move a record to a completely different position in value order. Concrete pair at k=16: raw `0x000000FF` canonicalizes to itself (high byte `0x00`), raw `0xBFFFFFFF` canonicalizes to `0x00000001` (high byte `0x00`) — raw-ascending order stores the descending run `[0x000000FF, 0x00000001]` in bucket 0x00's shard. The hashmap writer sorts explicitly (`sorted_kmers.sort_by_key`, :778) so it is unaffected, but `merge_single_prefix_streaming` pushes each file's front entry into a `BinaryHeap` and pops assuming each file is an ascending run; its duplicate handling (:946) consumes only CONSECUTIVE duplicates. On a non-ascending shard it emits records out of order and emits non-adjacent duplicate encodings of one k-mer as separate un-summed records — and `concatenate_final_output` still writes `sorted: true` (:1264), so `query_kmer`'s binary search (format.rs:591-596) silently returns wrong counts. **Empirically proven for this review** (scratch crate outside the repo, public API only): mixed-canonical inputs A=`{(0x000000FF,1),(0xBFFFFFFF,7)}` (non-canonical, raw-sorted) and B=`{(0x00000001,2)}` (canonical) merged with `use_prefix_cache: true, merge_mode: "streaming"` produced entries `[0x00000001/2, 0x000000FF/1, 0x00000001/7]` — non-ascending, the two encodings of `0x00000001` un-summed, header `sorted=true total_kmers=3`, and `query_kmer` answered `Some(2)` where the oracle is `Some(9)`. The same inputs through the hashmap writer were correct. Reachability is not exotic: `use_prefix_cache` routes unconditionally to `ExternalSortMerger` (format.rs:1134-1151, only a warning about the dual meaning of `merge_mode`) and passes `merge_mode` through, so `"streaming"` forces this writer for every bucket; under `"auto"`, any bucket whose shards exceed `merge_buffer_mb` MB (floor 1 MB — i.e., any real-scale bucket) selects streaming. The delta's e2e tests exercise only the hashmap writer (prefix_cache_output_order_tests.rs:94-96 acknowledges tiny inputs take the per-bucket hashmap strategy under "auto"), so the defect is untested. The comment at :302-304 ("what lets the bucket writers sum the raw and canonical encodings of one k-mer once they meet in the same bucket") is false for the streaming writer. The WR-04 conservation check cannot catch it either: both sides count the wrongly emitted records.
**Fix:** Make the stored-key ordering guarantee hold for every writer, or refuse configurations that break it. Options, in order of safety: (a) in `ExternalSortMerger::new` (which already reads every input's header, :135-139) record whether any input is non-canonical while `self.canonical` is true, and force the sorting (hashmap) writer for all buckets in that case, logging why `merge_mode`'s streaming choice is overridden; (b) have `merge_single_prefix_streaming` validate its runs — on the first adjacent descending pair in a shard, fail loudly instead of emitting corrupt order (cheapest guard, converts silent corruption into an error); (c) sort each shard by stored key at finalize (equivalent memory cost to (a) per bucket). Regardless of choice, extend `mixed_canonical_prefix_cache_output_is_ascending_summed_and_queryable` with a `merge_mode: "streaming"` arm (tiny inputs, explicit streaming writer) asserting the same ascending + summed + queryable oracles, so this exact regression cannot recur untested. Also correct the :302-304 comment.

## Warnings

### WR-01: The failed-bucket "shard files PRESERVED for recovery" promise is voided by RAII Drop the moment the error propagates (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:635-643` (error text promising preservation), `:52-54` and `:503-523` (`should_remove_shards` + "PRESERVED on disk" log), `:1418-1451` (`Drop` removes every tracked shard and closes the `TempDir`); test asserting the wrong moment `:1776-1818`
**Issue:** When a bucket merge fails, its shards are deliberately kept and the abort error tells the operator they were "PRESERVED for recovery". But the error leaves via `?` while `merger` is still the owning local — `Drop` then runs immediately and, with `keep_intermediate == false`, removes every path in `self.shard_paths` (all shards were registered up front, :272-273) and `TempDir::close()` removes the whole tree. The promised preservation never survives to the caller; only `--keep-intermediate` actually preserves anything. The unit test asserts `shard_path.exists()` while `merger` is still alive, before the `?` propagation triggers `Drop`, so it proves the wrong thing. Unchanged by this delta.
**Fix:** Either (a) make the promise true — on the error path remove the failed buckets' shard paths from `self.shard_paths` and `keep()` the `TempDir` before returning the error; or (b) stop promising it — reword the error/log to point at `--keep-intermediate`. Either way, extend the test to assert the on-disk state AFTER the merger is dropped.

### WR-02: u32 count overflow in prefix-cache bucket merges — debug panic, release wrap; the in-memory route saturates (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:734` (hashmap writer `*kmer_counts.entry(kmer).or_insert(0) += count`), `:896` and `:951` (streaming writer `current_count += top.count` / `+= consumed.count`); contrast `src/database/format.rs:1644` (`saturating_add`)
**Issue:** Both per-bucket merge writers accumulate counts with plain `+=`, so a merged count exceeding `u32::MAX` panics in debug and silently wraps in release. The in-memory route deliberately uses `saturating_add`; the prefix-cache route — selected for merges large enough to be over budget — keeps the weaker behavior where overflow is most reachable. The disposition file records this as deliberately deferred; it remains a live defect in an in-scope file.
**Fix:** `*e = e.saturating_add(count)` in the hashmap writer and `current_count = current_count.saturating_add(...)` at both streaming sites, matching the in-memory route's policy.

### WR-04: The CLI `--batch-size` flag is a silent no-op (carried from 03-12..03-15 round; file outside this round's scope, unchanged by the delta)

**File:** `src/cli/commands/merge.rs:114-120` (arg declaration), `:141-357` (`execute_merge` never reads it)
**Issue:** `MergeArgs::batch_size` is documented to users as controlling buffer flush size, but nothing reads it: the splitter's flush threshold is hard-coded `BATCH_SIZE = 10_000` (prefix_cache_merge.rs:277) and the phase-1 stream iterator uses a fixed `500_000` (:289). A user tuning `--batch-size` gets silently identical behavior.
**Fix:** Wire it through (e.g., thread it into `ExternalSortMerger` for the splitter's flush threshold and/or `config.chunk_size`), or remove the flag.

### WR-05: `--check-compatibility --use-prefix-cache` rejects mixed-canonical input sets that the merge with the same flags accepts (carried; file outside this round's scope, unchanged)

**File:** `src/cli/commands/merge.rs:414-423` (front-end skips the canonical check on the prefix-cache route), `:281-317` (the `--check-compatibility` branch runs `validate_compatibility_verbose`, which rejects mixed canonical unconditionally)
**Issue:** With `--use-prefix-cache`, the pre-flight check prints the skipping notice and then fails with a canonical-mode incompatibility on the same input set the actual merge accepts and merges correctly — the check contradicts the operation it is previewing within a single run.
**Fix:** Gate the canonical comparison in the `--check-compatibility` branch the same way the front-end pass does (skip/annotate when `args.use_prefix_cache`), so the verdict matches the merge's behavior.

### WR-06: `validate_merge_compatibility` panics on an empty input slice (carried; file outside this round's scope, unchanged)

**File:** `src/cli/commands/merge.rs:399` (`let first_db_path = &input_paths[0];`)
**Issue:** The function is `pub` for external tests but indexes `input_paths[0]` before any guard — an empty slice panics instead of returning `Err`. The CLI path is safe only because callers check length first; the core merge spent a gap-closure finding adding exactly this class of guard to every entry point, and the pub extraction reintroduced the unguarded shape.
**Fix:** Add `if input_paths.is_empty() { return Err(anyhow::anyhow!("At least one input database is required")); }` before the index.

## Info

### IN-01: `merge_prologue` runs twice on the materializing delegating path (carried; file outside this round's scope, unchanged)

**File:** `src/database/format.rs:1348` (`merge_databases` calls it), `:1367` (delegates to `merge_databases_to_path`), `:1261` (which calls it again)
**Issue:** The prologue (header reads + stale-dir sweep) executes twice on the materializing path's delegating arms; behaviorally benign within the TTL window, but the documented "single sweep call site covers all three strategies from both entry points" invariant overstates what is guaranteed.
**Fix:** Let the to-path core own the prologue for the delegating arms (in-memory arm gets its own call), or reword the invariant.

### IN-02: `Drop for ExternalSortMerger` logs the wrong directory when `close()` fails (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:1439-1448`
**Issue:** After `self.merge_temp_subdir.take()`, the failure log prints `self.shard_dir().display()` — which now reads the already-taken field and falls back to the bare parent `temp_dir`, so the warning names the wrong directory.
**Fix:** Capture the path before taking (`let path = dir.path().to_path_buf();`) and log that.

### IN-03: Phase-1 log claims parallel bucketing; the loop is serial (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:249-253` (log: "Using N worker threads for parallel bucketing"), `:280` (plain serial `for` over `input_files`)
**Issue:** Only phase 2 uses rayon; the phase-1 progress output misleads an operator about where parallelism applies.
**Fix:** Reword the log, or parallelize per-file bucketing.

### IN-04: Dead duplicate shard readers masked by `#[allow(dead_code)]` (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:973-988` (`read_entries_from_file_sync`), `:1382-1397` (`read_entries_from_file`), `:106` (the `#[allow(dead_code)]` that keeps them alive)
**Issue:** Two byte-identical whole-file `read_to_end` readers with zero callers; if revived they would contradict the bounded-memory discipline (block reads + pending carry) the rest of the file enforces.
**Fix:** Delete both, or consolidate into one block-based reader if a caller ever materializes.

### IN-05: Merger's `total_kmers`/`estimated_kmers_per_file` come from the FIRST input only (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:156`, `:175-176`, `:212`
**Issue:** The constructor loops over every input's header for validation but takes the record count only from `input_files[0]`, so the "Total k-mers: X M" banner under-reports every multi-input merge.
**Fix:** Sum the headers' `total_kmers` (saturating), or relabel the log.

### IN-06: Stale "24 B/k-mer" comments contradict the 96 model the same test file asserts (carried, still open)

**File:** `tests/merge_routing_tests.rs:24-25`, `:64-66`
**Issue:** The module and `INPUT_KMERS` comments still describe the retired 24 B/k-mer admission model, while `estimated_bytes_per_route_reflects_each_routes_peak` in the same file pins 96 and asserts the old model "must not be back".
**Fix:** Update both comments to the 96 B/k-mer model (400 kmers → 38,400 bytes estimated).

### IN-07: `is_multiple_of` raises the effective MSRV above the documented Rust 1.80+ baseline (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:551`, `:1293`
**Issue:** `u64::is_multiple_of` stabilized in Rust 1.87; the project documents "Rust 1.80+ stable" and `Cargo.toml` declares no `rust-version`, so a 1.80–1.86 toolchain fails to build with nothing explaining the requirement.
**Fix:** Add `rust-version = "1.87"` to `Cargo.toml` (and update the documented baseline), or use `% == 0`.

### IN-08: Final prefix-cache output is flushed but never fsync'd, unlike every other artifact in the route (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:1316-1317` (`writer.flush()?; drop(writer);` — no `sync_all`)
**Issue:** The route fsyncs the merged bucket files, the concatenated temp data (:1166), and each bucket writer's output; the FINAL database — the artifact the user keeps — gets only a `BufWriter::flush`, so a crash shortly after success can leave a truncated output.
**Fix:** Retain/reopen the `File` and `sync_all()` it before returning from `concatenate_final_output`.

### IN-09: The 03-16 error-propagation claim is vacuous — `canonical_kmer_u128` has no error path (new this round)

**File:** `src/database/prefix_cache_merge.rs:304-312` (comment + `?`), `src/kmer/canonical.rs:72-82` (`Ok(if kmer_encoded <= rev_comp { ... })` — unconditionally `Ok`)
**Issue:** The new comment states "A canonicalization failure propagates with `?`, aborting the merge loudly — the pre-fix swallowed-error fallback silently substituted the raw key (T-03-53/T-03-54)". But `canonical_kmer_u128` returns `Ok(...)` unconditionally; it cannot fail, so the `?` can never fire and the pre-fix `.unwrap_or(entry.kmer)` was equally dead code. The change is harmless (and defensive if the function ever becomes fallible), but the "closed a swallowed-error hole" claim in the comment, the commit message, and the threat tags describes a failure mode that cannot occur through this function — future maintainers will trace a phantom fix.
**Fix:** Either soften the comment to "propagates the error if canonicalization ever becomes fallible" and drop the T-03-53/T-03-54 attribution, or make the vacuousness explicit (`canonical_kmer_u128` is currently infallible; the `?` is future-proofing).

---

_Reviewed: 2026-10-09T14:40:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
