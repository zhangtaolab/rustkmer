---
phase: 03-memory-safety
reviewed: 2026-10-08T15:59:04Z
depth: standard
files_reviewed: 21
files_reviewed_list:
  - pyo3/src/database.rs
  - pyo3/tests/test_database_merge.py
  - src/cli/commands/merge.rs
  - src/database/format.rs
  - src/database/merge_config.rs
  - src/database/prefix_cache_merge.rs
  - src/database/stats.rs
  - src/database/streaming_merge.rs
  - src/database/temp_lifecycle.rs
  - src/hash/mod.rs
  - src/hash/table.rs
  - src/lib.rs
  - tests/dense_differential_tests.rs
  - tests/dense_memory_tests.rs
  - tests/dense_merge_integration_tests.rs
  - tests/dense_proptest_tests.rs
  - tests/golden_sha256_tests.rs
  - tests/merge_bounded_memory_tests.rs
  - tests/merge_cleanup_tests.rs
  - tests/merge_route_parity_tests.rs
  - tests/merge_routing_tests.rs
findings:
  critical: 3
  warning: 10
  info: 7
  total: 20
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-10-08T15:59:04Z
**Depth:** standard
**Files Reviewed:** 21
**Status:** issues_found

## Summary

Incremental re-review of the gap-closure work since `d467dc5` (plans 03-06 through 03-11: KmerKey removal/CounterTable monomorphization, LE-only `KmerEntry::read_from`, golden_sha256 re-pointing, header-only merge routes + admission model, `merge_databases_to_path`, prefix-cache merge integrity + loose-chunk sweep), plus the full file contents of all 21 in-scope files.

**Verified correct (prior findings addressed by 03-06..03-11 — not re-reported):** the `CounterTable` enum with single-site width selection and the atomic `bump_entry!` macro (03-06); the endianness-heuristic removal in `KmerEntry::read_from` (03-07); `parse_memory_size` with `checked_mul` (WR-05 fix); the empty-input guard in `merge_prologue` and the single sweep call site (WR-06); the saturating admission model with `INMEMORY_BYTES_PER_KMER = 96` (WR-01); the WR-04 accounting/abort-on-bucket-failure logic and the WR-08 block-copy concatenation and pending-carry hashmap reader; `sweep_stale_merge_dirs` (symlink refusal via `file_type()`, TTL checks, graceful no-op); the chunk `len % RECORD_SIZE` truncation check and monotonic `TempFileManager` file IDs in `streaming_merge.rs`; the placeholder-then-rewrite streaming header write. WR-02 and WR-07 remain documented deferrals, not defects.

**Key concerns in the new findings:** two independent silent-data-corruption defects remain in the prefix-cache route's per-bucket streaming machinery (CR-01 drops a partial record at every ~4 MB batch boundary and permanently misaligns the rest of the shard; CR-02 writes `sorted: true` on output that is not in ascending k-mer order, breaking every binary-search consumer), and the streaming merge route reachable from the Python API performs no cross-input compatibility validation at all (CR-03). Ten warnings cover count-overflow and stranding edge cases in the bucket merges, a CLI front-end that fully materializes every input on the memory-bounded route it exists to protect, temp-file leaks, and two PyO3 correctness defects.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: `read_batch_from_file_sync` drops the partial-record tail at every batch boundary and swallows read errors — silent shard corruption above ~4 MB

**File:** `src/database/prefix_cache_merge.rs:937-968` (callers at `:845` and `:882`)
**Issue:** The per-bucket streaming reader clears its buffer at the start of every call (`data.clear()` at line 942), reads 8192-byte chunks until `bytes_read >= 4_000_000`, then decodes only whole 20-byte records (`while offset + RECORD_SIZE <= data.len()`, lines 961-965) and discards the tail. The arithmetic is deterministic: 488 full reads give 3,997,696 bytes (< 4 MB), so a 489th read runs, ending the batch at 4,005,888 bytes; `4,005,888 mod 20 = 8`, so 8 tail bytes are dropped at every batch boundary. The next batch then starts reading 8 bytes *into the middle of a record*, so every subsequent record in that shard decodes as misaligned garbage k-mers and counts. Any input shard file larger than ~4 MB (i.e., any single input contributing more than ~4 MB of records to one prefix bucket — the normal case for the large merges this route exists for) is silently corrupted. Additionally, `Err(_) => break` (line 954) swallows real I/O errors mid-file as a clean end-of-batch, silently truncating the merge. The WR-08 pending-carry fix was applied to `merge_single_prefix_hashmap`'s reader (lines 707-733) but not to this one. The WR-04 conservation check cannot catch this: both sides of that comparison derive from the same corrupted stream.
**Fix:** Carry the partial-record tail across batches exactly as the hashmap reader does, and propagate read errors:

```rust
fn read_batch_from_file_sync(
    file_state: &mut (std::io::BufReader<File>, Vec<u8>, Vec<KmerEntry>),
) -> ProcessingResult<Vec<KmerEntry>> {
    const BATCH_BYTES: usize = 4_000_000;
    let (reader, data, _) = &mut *file_state;
    // Do NOT clear: `data` holds the partial-record tail from the last batch.

    let mut bytes_read = 0usize;
    let mut buffer = [0u8; 8192];
    while bytes_read < BATCH_BYTES {
        match reader.read(&mut buffer) {
            Ok(0) => break,
            Ok(n) => {
                data.extend_from_slice(&buffer[..n]);
                bytes_read += n;
            }
            Err(e) => {
                return Err(ProcessingError::io_error(format!(
                    "failed reading shard stream: {e}"
                )));
            }
        }
    }

    let mut entries = Vec::new();
    let mut offset = 0usize;
    while offset + RECORD_SIZE <= data.len() {
        let (kmer, count) = read_record_at(data, offset);
        entries.push(KmerEntry::new(kmer, count));
        offset += RECORD_SIZE;
    }
    data.drain(..offset); // keep only the sub-record tail for the next call
    Ok(entries)
}
```

### CR-02: Prefix-cache output is bucketed by the LOW byte but written with `sorted: true` — every binary-search consumer silently returns wrong results

**File:** `src/database/prefix_cache_merge.rs:970-973` (`get_prefix_4mer`), `:1010-1017` (concatenation loop `0..num_buckets`), `:1175` (`sorted: true`); log claim at `:243`
**Issue:** `get_prefix_4mer` returns `kmer & 0xFF`. The k-mer encoding is right-aligned in the u128 (verified in `src/kmer/encoding.rs`: `encoded = (encoded << 2) | value` starting from zero), so `kmer & 0xFF` selects the **last** 4 bases, not the first — the Phase 1 log at line 243 ("data bucketing (by first 4 bases)") and the `prefix_to_dna` bucket labels ("AAAA".."TTTT") are both wrong about what is actually selected. That alone is only a labeling issue; the defect is the combination with `concatenate_final_output`: buckets are concatenated in index order 0..255, and each bucket is internally sorted ascending by full u128, so the output is ordered by `(low_byte, kmer)`. That is **not** ascending u128 order — e.g. k-mer `0x100` (low byte `0x00`, bucket 0) is written before k-mer `0xFF` (low byte `0xFF`, bucket 255) — yet the header written at line 1175 claims `sorted: true`. Every consumer that trusts that flag then breaks: `RKDatabase::query_kmer` (`src/database/format.rs:590-596`) switches to `binary_search_kmer` when `header.sorted`, and `src/database/prefix_query_optimized.rs` binary-searches sorted databases (lines 86-120, 264-310). Exact-match queries on a prefix-cache-merged database silently return `None` (or a wrong count), and prefix extraction silently misses k-mers. The prior phase's `merged_database_accounts_for_every_input_kmer_on_both_routes` test asserts `header.sorted` only for the in-memory and streaming routes, so this is untested on the prefix-cache route.
**Fix:** Either (a) bucket by the true first 4 bases so index order equals u128 order:

```rust
fn get_prefix_4mer(&self, kmer: u128) -> usize {
    // First 4 bases = the HIGH 8 bits of the right-aligned 2k-bit key.
    let shift = 2 * self.kmer_size.saturating_sub(4);
    ((kmer >> shift) & 0xFF) as usize
}
```

(with the `shift == 0` case for `k < 4` decided explicitly), or (b) keep low-byte bucketing but clear the `sorted` flag in the output header — noting that (b) degrades prefix extraction to linear scans — or (c) emit buckets in an order that produces globally sorted output only if the bucket key is the high byte, which is option (a). Independently, correct the "first 4 bases" log/label claim to match whatever is implemented, and add a test that asserts global ascending order of a prefix-cache-merged output.

### CR-03: Streaming merge route performs no cross-input k-mer-size/canonical validation — Python API silently merges incompatible databases

**File:** `src/database/format.rs:1344-1350` (validation gap); entry point `pyo3/src/database.rs:1370-1465`; contrast `src/database/prefix_cache_merge.rs:128-143` and `src/database/format.rs:1545`
**Issue:** `merge_databases_streaming_to_path` reads `kmer_size` and `canonical` from `read_header_of(&input_paths[0])` only (lines 1348-1350) and never compares them against the other inputs. `merge_prologue` (format.rs:966-996) checks only for an empty list, and `resolve_merge_route` only estimates memory. The other two routes validate: the in-memory route calls `validate_compatibility_verbose` (format.rs:1545) and the prefix-cache route compares every input's header k-mer size (prefix_cache_merge.rs:128-143). The CLI front-end also pre-validates (src/cli/commands/merge.rs:165-299). But `PyDatabase.merge` (pyo3/src/database.rs:1370-1465) validates only file existence, `merge_mode`, and `max_memory` parsing before calling `merge_databases_to_path` — so from Python, merging a k=21 database with a k=31 database (or mixed canonical modes) on the streaming route (selected automatically once the admission model says the merge is over budget) silently produces a corrupt database whose header claims input[0]'s k-mer size, instead of returning an error. This is the same class of route-disagreement as prior CR-01, now on the validation axis.
**Fix:** Validate every input header once, in the shared path, so all routes and both front-ends inherit it:

```rust
fn merge_prologue(
    input_paths: &[std::path::PathBuf],
    config: &crate::database::MergeConfig,
) -> crate::error::ProcessingResult<()> {
    if input_paths.is_empty() { /* existing guard */ }

    // Cross-input compatibility: header-only (D-01), so the over-budget
    // route never materializes an input just to reject it.
    let first = Self::read_header_of(&input_paths[0])?;
    for path in input_paths.iter().skip(1) {
        let h = Self::read_header_of(path)?;
        if h.kmer_size != first.kmer_size {
            return Err(crate::error::ProcessingError::new(format!(
                "Database '{}' has k-mer size {}, expected {}",
                path.display(), h.kmer_size, first.kmer_size
            )));
        }
        // canonical mismatch: reject here unless the prefix-cache route's
        // mixed-canonical capability is intentionally selected (see WR-04).
    }
    // ... existing sweep call ...
}
```

## Warnings

### WR-01: `StreamingMergeIterator`'s `pending_error` machinery is dead code and the iterator is not actually finished after an `Err`

**File:** `src/database/streaming_merge.rs:436-445, 475-500`
**Issue:** The error arm sets `self.pending_error = Some(...)` (lines 484-490) and then immediately returns `Some(Err(self.pending_error.take().expect(...)))` (lines 496-499) — so `pending_error` is always `None` again by the time `next()` is re-entered, making the top-of-`next` check and state reset (lines 440-445) unreachable dead code. Worse, the comments claim "the run it belonged to has already been abandoned" and "the heap / `current_kmer` / `current_count` are left untouched, so no k-mer is double-counted if a caller ever retries and no partial run is emitted beside the error" — but leaving the heap and current run intact means a caller that continues iterating after the `Err` (any `for` loop that doesn't break, `collect::<Result<...>>` retry logic, `iterator.map(...).take_while(...)`) receives further `Ok` records from the still-live heap, i.e. a partial run IS emitted beside the error. The production consumer aborts via `?`, so impact is contained today, but the documented contract is false and the next consumer will be built on it.
**Fix:** Decide the contract and implement it directly: to make "finished after error" true, clear the state before returning the error (as the dead branch at 440-443 intended) and drop the take/return dance:

```rust
Err(e) => {
    let err = ProcessingError::io_error(format!(
        "Failed to read k-mer entry from chunk file '{}': {}",
        self._temp_files[merge_item.file_index].display(), e
    ));
    // Terminal: no further items after an error.
    self.current_kmer = None;
    self.current_count = 0;
    self.heap.clear();
    return Some(Err(err));
}
```

### WR-02: u32 count overflow in prefix-cache bucket merges — panics in debug, wraps in release; in-memory route saturates

**File:** `src/database/prefix_cache_merge.rs:719` (hashmap), `:866, :887, :899` (streaming); contrast `src/database/format.rs:1561-1562`
**Issue:** The per-bucket merge accumulates counts with plain `+=` (`*kmer_counts.entry(kmer).or_insert(0) += count;` and `current_count += top.count`). Merging databases whose summed count for one k-mer exceeds `u32::MAX` panics in debug builds and silently wraps in release builds. The in-memory route deliberately uses `saturating_add` (format.rs:1562, "Merge k-mers with overflow protection") — the prefix-cache route, which exists precisely for the merges large enough to be over budget, has the weaker behavior on exactly the path where overflow is most reachable.
**Fix:** Use `saturating_add` at all four sites, e.g. `*e = e.saturating_add(count)` / `current_count = current_count.saturating_add(top.count)`, matching the in-memory route's documented overflow policy.

### WR-03: `merge_single_prefix_streaming` peek-and-add strands the rest of a file's run on within-file duplicate k-mers

**File:** `src/database/prefix_cache_merge.rs:886-895` (refill branch; identical pattern at `:897-906`)
**Issue:** After popping an entry, the code peeks at the file's next buffered head; if `current_kmer == Some(first_entry.kmer)` it adds the count to the current run but neither removes the head from the buffer nor pushes it onto the heap (lines 886-887, 898-899). The merge invariant is "the heap holds the head of each live file"; once a file's head is consumed this way without a heap entry, nothing ever references that file again — the head and every remaining record of that file are silently dropped. This triggers whenever a shard file contains duplicate k-mer records (possible for hand-built or externally produced `.rkdb` inputs; the function also never checks the input's `sorted` flag, it just assumes each shard is a sorted run, so an unsorted input corrupts the heap merge silently rather than erroring).
**Fix:** Always remove the consumed head and only conditionally push:

```rust
let first_entry = file_states[top.file_idx].2.remove(0);
if !file_states[top.file_idx].2.is_empty() || /* refill happened */ {
    ...
}
if current_kmer == Some(first_entry.kmer) {
    current_count = current_count.saturating_add(first_entry.count);
} else {
    heap.push(HeapEntry { kmer: first_entry.kmer, count: first_entry.count,
                          file_idx: top.file_idx });
}
```

i.e. treat the peeked head as consumed in both branches. Also reject (or document and verify) unsorted shard inputs rather than assuming sorted runs.

### WR-04: Prefix-cache mixed-canonical merge writes raw (non-canonical) records while the output header claims `canonical` from input[0]

**File:** `src/database/prefix_cache_merge.rs:292-303` (selection-only canonicalization, `unwrap_or` at `:294`), `:1174` (header claim); capability advertised at `src/database/format.rs:796`
**Issue:** In `split_files_by_prefix`, `processed_kmer` (the canonicalized value) is used ONLY to choose the bucket (line 299); the raw `entry.kmer` is what gets written to the shard (lines 302-303). Mixed-canonical merging is this route's advertised capability ("Use --use-prefix-cache for flexible canonical mode merging", format.rs:796), but on such a merge the non-canonical inputs' records are never converted — the output contains non-canonical k-mers while its header claims `canonical: self.canonical` (input[0]'s flag, line 1174). Downstream canonical-mode consumers get wrong query semantics, and canonical/non-canonical encodings of the same k-mer stay as separate records instead of merging. Additionally, `canonical_kmer_u128(...).unwrap_or(entry.kmer)` (line 294) silently swallows canonicalization errors and buckets by the un-canonicalized value.
**Fix:** Write the canonicalized value to the shard: `bucket_buffers[prefix].extend_from_slice(&processed_kmer.to_le_bytes())` (and propagate the canonicalization error instead of `unwrap_or(entry.kmer)`); or, if raw-preserve is intended, derive the output header's `canonical` flag from whether every input was canonical and say so in the route's documentation.

### WR-05: CLI merge fully materializes every input database just to validate — including on `--use-prefix-cache`, the memory-bounded route it exists for

**File:** `src/cli/commands/merge.rs:165-299` (reference load at `:165`; validation loop 1 at `:168-236`; always-runs loop 2 at `:241-299`)
**Issue:** `execute_merge` contains two sequential per-input validation loops that each call `RKDatabase::from_file_path(db_path)`, loading the entire database into RAM. Loop 1 runs when `!use_prefix_cache`; loop 2 runs unconditionally — so with `--use-prefix-cache`, every input is still fully materialized one at a time purely to compare `kmer_size()` (line 253), defeating the purpose of the bounded-memory route at the exact front-end where users select it (the 03-09/D-01 fix removed whole-database loads from the core routing, but not from this CLI front-end). When `!use_prefix_cache` the two loops are also plain duplicated work (same loads, same comparisons, different error message wording).
**Fix:** Replace both loops with one header-only pass:

```rust
let ref_header = RKDatabase::read_header_of(first_db_path)?;
for db_path in args.input.iter().skip(1) {
    let h = RKDatabase::read_header_of(db_path)?;
    if h.kmer_size != ref_header.kmer_size { /* error with recovery suggestions */ }
    if !args.use_prefix_cache && h.canonical != ref_header.canonical { /* error */ }
}
```

and drop the `reference_db` full load (nothing else in the function needs it once the header is read directly).

### WR-06: Compat-shim fallback file leaks on error and is never swept

**File:** `src/database/format.rs:1222-1231` (fallback target), `:1284-1290` (leak); sweep mismatch at `src/database/temp_lifecycle.rs:232-243`
**Issue:** When `compat_materialization_target` cannot create a merge subdir, `merge_databases`'s Streaming/PrefixCache arm writes to `rustkmer-merge-compat-<pid>-<nanos>.rkdb` directly under `temp_dir`. If `merge_databases_to_path` or `from_file_path` then returns `Err`, the `?` at lines 1285/1286 returns before the `remove_file` at line 1289 runs — the file leaks. It is also never reclaimed by the orphan sweep: the file name carries the `rustkmer-merge-` prefix, but the sweep's directory branch explicitly skips non-directories (`Ok(_) => continue`, temp_lifecycle.rs:233-234) and the loose-chunk branch requires the `.chunk` suffix.
**Fix:** Clean up on the error path (and/or make the sweep's prefix branch handle files named with `MERGE_TEMP_PREFIX` that end in `.rkdb`):

```rust
let (subdir, temp_path) = Self::compat_materialization_target(config);
let result = Self::merge_databases_to_path(input_paths, config, &temp_path)
    .and_then(|_| Self::from_file_path(&temp_path).map(|db| (db, ())));
if subdir.is_none() {
    let _ = std::fs::remove_file(&temp_path);
}
result.map(|(merged, _)| merged)
```

### WR-07: `PyDatabase.dump(limit=None, offset>0)` overflows `offset + usize::MAX` — panic in debug, empty result in release

**File:** `pyo3/src/database.rs:1254, 1261-1265`
**Issue:** `dump` sets `actual_limit = limit.unwrap_or(usize::MAX)` (line 1254) and the Preload arm's break condition is `count >= offset + actual_limit` (line 1263). With `limit=None` and any `offset > 0`, `offset + usize::MAX` overflows: in a build with overflow checks it panics; in release it wraps to `offset - 1`, and since the enclosing condition already established `count >= offset`, the break fires immediately — the call returns an empty list instead of "everything from offset". (The MemoryMapped arm correctly uses `offset.saturating_add(...)`; Lazy uses skip/take and is fine.)
**Fix:** `if count >= offset.saturating_add(actual_limit) { break; }` — or better, `if results.len() >= actual_limit { break; }` after the offset skip.

### WR-08: `PyDatabase.query_exact` in MemoryMapped mode always returns count 0 / found False

**File:** `pyo3/src/database.rs:606-611`
**Issue:** The `LoadMode::MemoryMapped` arm of `query_exact_impl` returns the literal `0` with the comment "This is a simplified implementation". Every exact query against a memory-mapped database reports the k-mer as absent. Pre-existing (outside the diff range) but never reported and directly user-visible from Python: callers get silently wrong answers rather than an "unsupported mode" error.
**Fix:** Either implement the file-backed binary search (the format guarantees 20-byte fixed records after the 42-byte header when `header.sorted`), or fail loudly: `return Err(PyErr::new::<pyo3::exceptions::PyNotImplementedError, _>("query_exact is not supported in memory-mapped mode"));`.

### WR-09: `from_file_path` pre-reserves `header.total_kmers` entries — crafted header aborts the process instead of returning an error

**File:** `src/database/format.rs:463`
**Issue:** `Vec::with_capacity(header.total_kmers as usize)` runs immediately after the 42-byte header is read and validated for magic/version/data_offset, but before any consistency check against the file's actual size. A crafted or truncated-corrupt header claiming `total_kmers` near `u64::MAX` (or merely a large implausible value) makes `with_capacity` attempt a huge allocation: capacity-overflow panic (and the release profile's `panic = "abort"` turns that into a process abort), or an allocation-failure abort — on what should be a rejectable input. The read loop would otherwise catch the mismatch via `read_from`'s `UnexpectedEof`, but only after the reservation.
**Fix:** Clamp the reservation and let the loop grow the vector, cross-checking against file size:

```rust
let file_len = std::fs::metadata(&file_path).map(|m| m.len()).unwrap_or(0);
let data_bytes = file_len.saturating_sub(header.data_offset);
if header.total_kmers > data_bytes / RECORD_SIZE_U64 {
    return Err(crate::error::ProcessingError::new(format!(
        "header claims {} k-mers but the file holds at most {}",
        header.total_kmers, data_bytes / RECORD_SIZE_U64
    )));
}
let mut entries = Vec::with_capacity(header.total_kmers as usize);
```

### WR-10: `frequency_distribution` zero-fills `min_count..=max_count` — unbounded allocation up to ~4.3 billion entries

**File:** `src/database/stats.rs:229-247` (loop at `:241`)
**Issue:** When `detailed` is set, the distribution is materialized by iterating `self.min_count..=self.max_count` and pushing one `(u32, u64)` per value, zero-filling gaps. Counts are u32, so a dataset whose max count is large (a high-coverage region, a repeated k-mer — values in the 1e8..1e9 range are reachable, `u32::MAX` is the bound) allocates and iterates up to ~4.29e9 entries (~51 GB) before returning — an out-of-memory abort, not slow-but-correct behavior, so this is a crash robustness defect rather than a performance nit. Pre-existing (outside the diff range), not previously reported.
**Fix:** Either iterate the `frequency_histogram` directly (emit only observed counts plus explicit gap markers), or cap the zero-fill range with a documented bound (e.g. fill at most the first N count values and summarize the tail) and make `detailed` semantics reflect that.

## Info

### IN-01: `Drop for ExternalSortMerger` logs the wrong directory when `close()` fails

**File:** `src/database/prefix_cache_merge.rs:1350-1359`
**Issue:** After `self.merge_temp_subdir.take()`, the error log prints `self.shard_dir().display()` — but `shard_dir()` now reads the already-taken field and falls back to the bare `temp_dir`, so the warning names the parent temp root instead of the merge subdir that failed to be removed.
**Fix:** Capture the path before taking: `let path = dir.path().to_path_lossy().to_string();` then `dir.close()` and log `path`.

### IN-02: `merge_databases` runs `merge_prologue` twice per call via delegation

**File:** `src/database/format.rs:1265` and `:1285` (delegating into `merge_databases_to_path` at `:1177`)
**Issue:** `merge_databases` calls `merge_prologue` itself, then its Streaming/PrefixCache arm calls `merge_databases_to_path`, which calls `merge_prologue` again — two sweeps and two empty-list checks per materializing merge, contradicting the documented "single sweep call site ... covers all three strategies from both entry points" invariant. Behaviorally harmless (the sweep is idempotent within the TTL window); the drift hazard is that the invariant's test can't distinguish one-site-reached-twice from one-site.
**Fix:** Either skip the prologue in `merge_databases` and let the to-path core own it for the delegating arms, or reword the invariant to "single call site, possibly executed twice on the materializing path".

### IN-03: Stale admission-model constant copied into the integration tests

**File:** `tests/dense_merge_integration_tests.rs:441`
**Issue:** `over_budget_config` computes `estimated_kmers.saturating_mul(24)` while its comment claims "Same model as RKDatabase::merge_databases" — the core's per-k-mer constant is now 96 (`INMEMORY_BYTES_PER_KMER`, format.rs:81, after 03-09's WR-01 fix). Functionally benign today (a smaller estimate is still over-budget, and the route is verified via the `assert_route` probe), but the comment is false and the copy invites a future budget change to silently invalidate the "over budget" premise of every test using this helper.
**Fix:** Import or re-derive the constant from the core (expose `estimated_bytes_for_route` for tests, as `merge_routing_tests.rs` already does) instead of duplicating `24`.

### IN-04: Dead magic-number clamp in `get_entry_by_index`

**File:** `pyo3/src/database.rs:1048-1054`
**Issue:** `if self.header.data_offset > 1000000 { 42 } else { self.header.data_offset }` silently rewrites a field that `from_file_path` already enforces to exactly 42 (the same D-12 silent-clamp pattern removed elsewhere in this phase). Unreachable on any database this class can open; if ever reached it would mask corruption instead of reporting it.
**Fix:** Use `self.header.data_offset` directly (it is invariantly 42), or assert/error on a non-42 value.

### IN-05: `DatabaseStreamIterator::header()` fabricates an invalid header

**File:** `src/database/streaming_merge.rs:78-91`
**Issue:** The public `header()` returns `kmer_size: 0`, `data_offset: 0`, `sorted: false`, `canonical: false` — values that would fail the very `data_offset == 42` check the constructor itself enforces and that misrepresent the underlying file to any caller that trusts them (no production callers today; `remaining`/`total_kmers` is the only field that reflects reality).
**Fix:** Store the real header read in `new` (it is already parsed there) and return a clone, or make the method private/remove it.

### IN-06: `extract_by_prefix` reloads the entire database from disk on every call

**File:** `pyo3/src/database.rs:945`
**Issue:** The method ignores `self.rk_database` (already open) and calls `RKDatabase::from_file_path(Path::new(&self.path))` per invocation, re-reading and re-materializing the full database each time. Correctness is unaffected; the quality defect is redundant full loads on a repeat-call Python API.
**Fix:** Reuse `self.rk_database` (or the cached entries) when its loading mode already holds the data.

### IN-07: `test_prefix_extraction_values` tests nothing about the production prefix extraction

**File:** `src/database/prefix_cache_merge.rs:1389-1396`
**Issue:** The unit test computes `(kmer >> (2 * (57 - 4))) & 0xFFF` itself — it never calls `get_prefix_4mer` — and with a 64-bit kmer shifted right by 106 the result is always 0, so the final `assert!(prefix < 256)` is a tautology. This is the only unit-level test naming prefix extraction, on exactly the function that carries CR-02, and it provides false confidence (it also disagrees with the production mask: `0xFFF`/12 bits vs the production `0xFF`/8 bits).
**Fix:** Test the real function across representative k values and assert bucket semantics (e.g. `get_prefix_4mer(0x00FF) == 0xFF`, `get_prefix_4mer(0x0100) == 0x00`), pinning whichever end (first vs last 4 bases) the fix in CR-02 settles on.

---

_Reviewed: 2026-10-08T15:59:04Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
