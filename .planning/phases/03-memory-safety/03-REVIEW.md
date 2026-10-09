---
phase: 03-memory-safety
reviewed: 2026-10-09T12:05:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - src/cli/commands/merge.rs
  - src/database/format.rs
  - src/database/prefix_cache_merge.rs
  - tests/merge_frontend_validation_tests.rs
  - tests/merge_routing_tests.rs
  - tests/prefix_cache_conservation_tests.rs
  - tests/prefix_cache_output_order_tests.rs
findings:
  critical: 1
  warning: 6
  info: 8
  total: 15
status: issues_found
---

# Phase 3: Code Review Report (gap-closure round, plans 03-12..03-15)

**Reviewed:** 2026-10-09T12:05:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Incremental review of the merge-memory-safety delta since `5e7c3c5`: the header-only cross-input validation in `merge_prologue` (03-12), the record-aligned batch reader + VecDeque unstranding k-way merge (03-13), the header-only CLI merge validation (03-14), and the `get_prefix_4mer` high-byte bucketing fix with its order/parity proofs (03-15). This report replaces the pre-closure round's findings.

**Verified closed by this delta (traced through the code, not assumed):**
- Prior **CR-01** — `read_batch_from_file_sync` now carries the partial-record tail across batches (`data.drain(..offset)`, no `clear()`) and maps read errors to `Err` instead of `break` (prefix_cache_merge.rs:991-1029). The boundary arithmetic holds: first batch consumes 4,005,888 bytes, tail 8 bytes is retained, nothing misaligns.
- Prior **CR-03** — `merge_prologue` (format.rs:980-1080) reads every input's 42-byte header and rejects k-mer-size mismatch (`validate_header_compatibility`) and mixed canonical (unless `use_prefix_cache`) on all three routes from both entry points; the streaming route can no longer silently write input[0]'s k-mer size.
- Prior **WR-03** — the peek-and-add stranding is gone: the consumed head is always `pop_front()`ed and the tail loop re-queues the first non-duplicate head onto the heap (prefix_cache_merge.rs:907-946), restoring the "heap holds the head of every live file" invariant. Unit tests cover within-file and cross-file duplicates across a batch boundary.
- Prior **WR-05** — `validate_merge_compatibility` (merge.rs:392-486) reads headers only; the tests assert the materializing loader's failure as a premise before every `Ok`, so the header-only property is proven, not presumed.
- Prior **CR-02 (main case)** — `get_prefix_4mer` now selects the HIGH byte (prefix_cache_merge.rs:1047-1050), so for all-canonical or all-non-canonical inputs the concatenation's index-order loop emits globally ascending output and `sorted: true` is truthful. The new order/query/parity tests (prefix_cache_output_order_tests.rs) pin this end-to-end.

**Key concern in the new findings:** the CR-02 fix is ordering-correct only when every input has the same canonical mode. On the mixed-canonical route — the prefix-cache route's advertised capability — records are bucketed by their canonicalized high byte but stored and sorted by RAW key, so the output is still non-ascending while the header still claims `sorted: true` (new CR-01). Beyond that: the failed-bucket "shards PRESERVED for recovery" promise is voided by RAII Drop when the error propagates; two prior warnings remain open by explicit triage (u32 count overflow; the raw-record-write that is the root of CR-01); and the CLI accepts a `--batch-size` flag that is wired to nothing.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: Mixed-canonical prefix-cache merges still write non-ascending output under `sorted: true` — CR-02's fix does not hold on the route's advertised mixed-canonical capability

**File:** `src/database/prefix_cache_merge.rs:294-303` (bucket by canonical key, store raw), `:1047-1050` (`get_prefix_4mer`), `:1245-1256` (output header `sorted: true`); `src/database/format.rs:1918` (`final_canonical = has_canonical`)
**Issue:** In `split_files_by_prefix`, `processed_kmer = canonical_kmer_u128(entry.kmer, k)` when `self.canonical` is true — which `ExternalSortMerger::new` sets from `has_canonical` (ANY input canonical makes it true, format.rs:1918 / prefix_cache_merge.rs:148-155). The bucket is chosen from `processed_kmer`, but the shard stores the RAW `entry.kmer` (lines 303-304). `canonical_kmer_u128` returns `min(kmer, revcomp(kmer))` (src/kmer/canonical.rs:72-82), and the reverse complement of a right-aligned key generally occupies a completely different high byte. So a raw record with high byte `0x05` whose canonical form has high byte `0x30` lands in bucket `0x30`, after bucket `0x10`'s raw `0x10...` records. Each bucket is sorted by raw key and buckets are concatenated in index order — the output is ordered by `(canonical_high_byte, raw_key)`, which is NOT ascending u128 order, yet `concatenate_final_output` writes `sorted: true` unconditionally (line 1250). Every binary-search consumer then silently returns wrong results: `RKDatabase::query_kmer` switches to binary search on the flag (format.rs:591-596), and `extract_prefix_optimized` binary-searches sorted databases. The new 03-15 order tests use `canonical=false` inputs only, so this hole is untested. Root cause is the still-open raw-record-write debt (WR-03 below): fixing that one site also fixes the ordering, because the stored key then equals the bucket key.
**Fix:** Write the canonicalized value to the shard so the bucket key and the sort key are the same value:

```rust
let processed_kmer = if self.canonical {
    canonical_kmer_u128(entry.kmer, self.kmer_size)?   // propagate, don't unwrap_or
} else {
    entry.kmer
};
let prefix = self.get_prefix_4mer(processed_kmer);
if prefix < self.num_buckets {
    bucket_buffers[prefix].extend_from_slice(&processed_kmer.to_le_bytes());
    bucket_buffers[prefix].extend_from_slice(&entry.count.to_le_bytes());
    ...
}
```

Then extend `prefix_cache_output_order_tests.rs` with a mixed-canonical input set asserting `windows(2).all(|w| w[0].kmer < w[1].kmer)`.

## Warnings

### WR-01: The failed-bucket "shard files PRESERVED for recovery" promise is voided by RAII Drop the moment the error propagates

**File:** `src/database/prefix_cache_merge.rs:621-629` (error text promising preservation), `:489-509` (`should_remove_shards` + "PRESERVED on disk" log), `:1404-1436` (`Drop` removes every tracked shard and closes the `TempDir`); propagation site `src/database/format.rs:1805`
**Issue:** When a bucket merge fails, `should_remove_shards` deliberately keeps its shards and the abort error tells the operator: "shard files of the failed buckets were PRESERVED for recovery under '<dir>'". But that error leaves `merge_databases_prefix_cache_to_path` via `?` while `merger` is still the owning local — the `Drop` impl then runs immediately and, with `keep_intermediate == false`, removes every path in `self.shard_paths` (which registered ALL shards up front, line 272-273) and `TempDir::close()` removes the whole tree recursively. The preservation the message promises, and the WR-04 recovery-path design the code comments describe, never survives to the caller. The unit test `failed_bucket_aborts_the_merge_with_err` (lines 1763-1804) asserts `shard_path.exists()` while `merger` is still alive — before the `?` propagation triggers `Drop` — so it proves the wrong thing and gives this design false confidence. Only `--keep-intermediate` actually preserves anything.
**Fix:** Either (a) make the promise true — on the error path, remove the failed buckets' shard paths from `self.shard_paths` and `keep()` the `TempDir` (or move it out) before returning the error, adjusting the sweep story accordingly; or (b) stop promising it — reword the error/log to point at `--keep-intermediate` as the actual recovery mechanism. Either way, extend the test to assert the on-disk state AFTER the merger is dropped, which is the state the operator actually encounters.

### WR-02: u32 count overflow in prefix-cache bucket merges — debug panic, release wrap; the in-memory route saturates (open re-report)

**File:** `src/database/prefix_cache_merge.rs:720` (hashmap writer `*kmer_counts.entry(kmer).or_insert(0) += count`), `:884` (`current_count += top.count`), `:937` (`current_count += consumed.count`); contrast `src/database/format.rs:1644` (`saturating_add`)
**Issue:** Both per-bucket merge writers accumulate counts with plain `+=", so a merged count exceeding `u32::MAX` panics in debug builds and silently wraps in release builds. The in-memory route deliberately uses `saturating_add` ("Merge k-mers with overflow protection"), and the prefix-cache route — selected precisely for merges large enough to be over budget — retains the weaker behavior exactly where overflow is most reachable. A code comment states this is triaged in `03-REVIEW-DISPOSITION.md` and "deliberately NOT introduced here"; the disposition file records it **open**. It remains a live defect in an in-scope file and should not drop off the record.
**Fix:** `*e = e.saturating_add(count)` in the hashmap writer and `current_count = current_count.saturating_add(top.count)` / `.saturating_add(consumed.count)` in the streaming writer, matching the in-memory route's documented policy.

### WR-03: Mixed-canonical route writes RAW records while the output header claims canonical (from ANY input) — plus swallowed canonicalization errors (open re-report, prior WR-04)

**File:** `src/database/prefix_cache_merge.rs:294-303` (raw write; `unwrap_or(entry.kmer)`), `:1249-1250` (header claim); semantics source `src/database/format.rs:1902-1918`; inaccurate pin `tests/merge_routing_tests.rs:1299-1306`
**Issue:** Three related defects on the advertised mixed-canonical capability. (1) `split_files_by_prefix` writes `entry.kmer` (raw) to the shard while bucketing by the canonicalized value, so canonical and non-canonical encodings of the same k-mer remain separate records and never sum. (2) The output header claims `canonical: self.canonical`, but `self.canonical = final_canonical = has_canonical` — true if ANY input is canonical, not "input[0]'s mode" as the routing test's comment asserts (that test passes only because its input[0] happens to be canonical; a `[noncanon, canon]` ordering would claim `canonical: true` on a merge whose first input was non-canonical). (3) `canonical_kmer_u128(...).unwrap_or(entry.kmer)` silently swallows canonicalization failures and buckets by the un-canonicalized value. This finding is also the root cause of CR-01's ordering break. Recorded **open** in the disposition file; re-reported because it is in an in-scope file and carries user-visible wrong-query results.
**Fix:** Write `processed_kmer` to the shard and propagate the canonicalization error instead of `unwrap_or` (see CR-01's snippet); correct the routing test's comment/pin to the ANY-canonical semantics (or change the semantics to input[0]'s and pin that deliberately).

### WR-04: The CLI `--batch-size` flag is a silent no-op

**File:** `src/cli/commands/merge.rs:114-120` (arg declaration), `:141-357` (`execute_merge` never reads it)
**Issue:** `MergeArgs::batch_size` (default 50000) is documented to users as "Batch size for prefix cache merge (k-mers per buffer flush). Lower values use less memory but are slower." — but `execute_merge` never reads the field and `MergeConfig` has no corresponding field (its `chunk_size` is never set from it either). The quantities it appears to describe are hard-coded: the splitter's flush threshold is `BATCH_SIZE * RECORD_SIZE` with `BATCH_SIZE = 10_000` (prefix_cache_merge.rs:277) and the phase-1 stream iterator uses a fixed `500_000`. A user tuning `--batch-size` to constrain memory gets silently identical behavior.
**Fix:** Wire it through (`config.chunk_size = args.batch_size` and/or thread it into `ExternalSortMerger` for the splitter's flush threshold), or remove the flag; do not leave a help-text promise that nothing honors.

### WR-05: `--check-compatibility --use-prefix-cache` rejects mixed-canonical input sets that the merge with the same flags accepts

**File:** `src/cli/commands/merge.rs:414-423` (front-end deliberately skips the canonical check on the prefix-cache route), `:281-317` (the `--check-compatibility` branch runs `validate_compatibility_verbose`, which rejects mixed canonical unconditionally)
**Issue:** With `--use-prefix-cache`, `validate_merge_compatibility` prints "Skipping canonical-mode validation … using prefix cache merge" and passes a mixed-canonical set — the route's advertised capability — and the actual merge succeeds. But `rustkmer merge --check-compatibility --use-prefix-cache` on the SAME set first prints the skipping notice and then fails with "Database compatibility check failed: … has canonical mode …". The pre-flight check reports "incompatible" for inputs the requested operation would merge correctly, contradicting itself within a single run.
**Fix:** In the `--check-compatibility` branch, gate the canonical comparison the same way the front-end pass does — e.g. skip `validate_compatibility_verbose`'s canonical arm (or annotate its result as informational) when `args.use_prefix_cache` is set, so the check's verdict matches the merge's behavior.

### WR-06: `validate_merge_compatibility` panics on an empty input slice

**File:** `src/cli/commands/merge.rs:399` (`let first_db_path = &input_paths[0];`)
**Issue:** The function is `pub` specifically so external integration tests can call it, yet it indexes `input_paths[0]` before any guard — an empty slice panics with index-out-of-bounds instead of returning `Err`. The CLI path is safe today only because `execute_merge` checks `args.input.len() < 2` first (and clap's `num_args = 2..` guards before that), but the core merge spent a whole gap-closure finding (prior WR-06) adding exactly this class of guard to every entry point; the new pub extraction reintroduces the unguarded shape at the front-end layer.
**Fix:**

```rust
if input_paths.is_empty() {
    return Err(anyhow::anyhow!("At least one input database is required"));
}
```

## Info

### IN-01: `merge_prologue` runs twice on the materializing delegating path (re-report)

**File:** `src/database/format.rs:1348` (`merge_databases` calls it), `:1367` (delegates to `merge_databases_to_path`), `:1261` (which calls it again)
**Issue:** `merge_databases` runs the prologue, then its Streaming/PrefixCache arm delegates to `merge_databases_to_path`, which runs the prologue again — two header-read passes and two stale-dir sweeps per materializing merge, contradicting the documented "single sweep call site … covers all three strategies from both entry points" invariant (single call site, executed twice on this path). Behaviorally benign (idempotent within the TTL window); the drift hazard is that the invariant's wording overstates what is guaranteed.
**Fix:** Skip the prologue in `merge_databases` and let the to-path core own it for the delegating arms (the in-memory arm would then need its own call), or reword the invariant to "single call site, possibly executed twice on the materializing path".

### IN-02: `Drop for ExternalSortMerger` logs the wrong directory when `close()` fails (re-report)

**File:** `src/database/prefix_cache_merge.rs:1425-1434`
**Issue:** After `self.merge_temp_subdir.take()`, the failure log prints `self.shard_dir().display()` — but `shard_dir()` now reads the already-taken field and falls back to the bare `temp_dir`, so the warning names the parent temp root, not the merge subdir that failed to be removed.
**Fix:** Capture the path before taking (`let path = dir.path().to_path_buf();`) and log that.

### IN-03: Phase-1 log claims parallel bucketing; the loop is serial

**File:** `src/database/prefix_cache_merge.rs:249-253` (log: "Using N worker threads for parallel bucketing"), `:280` (plain serial `for` over `input_files`)
**Issue:** `split_files_by_prefix` logs a worker-thread count for "parallel bucketing", but the phase is a serial `for` loop; only phase 2 (`merge_prefix_buckets`) uses rayon. The log misleads an operator reading progress output about where parallelism applies.
**Fix:** Reword the phase-1 log (e.g. "bucketing serially; parallel merge will use N workers"), or actually parallelize per-file bucketing.

### IN-04: Dead duplicate shard readers masked by `#[allow(dead_code)]`

**File:** `src/database/prefix_cache_merge.rs:959-974` (`read_entries_from_file_sync`), `:1368-1383` (`read_entries_from_file`)
**Issue:** Two byte-identical whole-file readers (`read_to_end` into a Vec, then record decode) with zero callers anywhere in the crate; they survive only because the whole `impl` block carries `#[allow(dead_code)]` (line 106). If ever revived, `read_to_end` contradicts the bounded-memory discipline the rest of the file now enforces (block reads + pending carry).
**Fix:** Delete both (and the `#[allow(dead_code)]` reliance they justify), or consolidate into one block-based reader if a caller ever materializes.

### IN-05: Merger's `total_kmers`/`estimated_kmers_per_file` come from the FIRST input only — startup log under-reports multi-input merges

**File:** `src/database/prefix_cache_merge.rs:156` (`let total_kmers = first_header.total_kmers;`), `:175-176` (fields), `:212` ("Total k-mers: X M" log)
**Issue:** The constructor loops over every input's header for validation but takes the record count only from `input_files[0]`; the "🚀 Starting external sort merge / Total k-mers: X M" banner therefore reports input[0]'s count, not the sum, for every multi-input merge. Diagnostic-only fields, but the number is plainly wrong for the common case.
**Fix:** Sum the headers' `total_kmers` (saturating) when computing the field, or relabel the log to "first input declares X M records".

### IN-06: Stale "24 B/k-mer" comments contradict the 96 model the same test file asserts

**File:** `tests/merge_routing_tests.rs:24-25` ("`sum(total_kmers) * 24 > max_memory_usage` → stream"), `:65-66` ("`400 * 24 = 9600` bytes estimated")
**Issue:** The module/constant comments still describe the retired 24 B/k-mer admission model, while `estimated_bytes_per_route_reflects_each_routes_peak` in the same file (lines 855-912) pins 96 and explicitly asserts "the pre-WR-01 model must not be back". A reader reconciling the comments with the assertions wastes time or "fixes" the constants to match the comments.
**Fix:** Update both comments to the 96 B/k-mer model (400 kmers → 38,400 bytes estimated).

### IN-07: `is_multiple_of` raises the effective MSRV above the documented Rust 1.80+ baseline

**File:** `src/database/prefix_cache_merge.rs:537` (`done.is_multiple_of(10)`), `:1279` (`processed_kmers.is_multiple_of(1_000_000)`)
**Issue:** `u64::is_multiple_of` was stabilized in Rust 1.87; the project documents "Rust 1.80+ stable channel" (CLAUDE.md) and `Cargo.toml` declares no `rust-version`, so a 1.80–1.86 toolchain fails to build with an opaque error and nothing in the manifest explains the requirement. (The same pattern exists outside this scope in `index.rs`, `overflow.rs`, `dump.rs`, so this is a repo-wide drift the in-scope files participate in.)
**Fix:** Either add `rust-version = "1.87"` to `Cargo.toml` (and update the documented baseline), or use `% == 0` in these spots.

### IN-08: Final prefix-cache output is flushed but never fsync'd, unlike every other artifact in the route

**File:** `src/database/prefix_cache_merge.rs:1302-1303` (`writer.flush()?; drop(writer);` — no `sync_all`)
**Issue:** The route fsyncs the merged bucket files, the concatenated `ext_sort_final_data.tmp` (line 1152), and each bucket writer's output; the streaming route's final output is `sync_all`'d (format.rs:1544). The prefix-cache route's FINAL database — the one artifact the user keeps — gets only a `BufWriter::flush`, so a crash shortly after "Merge completed successfully!" can leave a truncated/zero-length output on some filesystems while the durability-conscious intermediates were all synced.
**Fix:** After `drop(writer)`, reopen or retain the `File` handle and `sync_all()` it (the rename handoff in `merge_databases_prefix_cache_to_path` happens before the merger drops, so syncing inside `concatenate_final_output` covers both the direct and renamed paths).

---

_Reviewed: 2026-10-09T12:05:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
