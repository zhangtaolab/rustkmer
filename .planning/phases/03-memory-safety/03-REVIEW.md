---
phase: 03-memory-safety
reviewed: 2026-10-17T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - src/database/prefix_cache_merge.rs
  - src/io/fastq.rs
  - tests/merge_bounded_memory_tests.rs
  - tests/merge_cleanup_tests.rs
  - tests/merge_routing_tests.rs
findings:
  critical: 0
  warning: 9
  info: 12
  total: 21
status: issues_found
---

# Phase 3: Code Review Report (incremental re-review, round 4)

**Reviewed:** 2026-10-17
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Incremental re-review of the standing phase-03 scope intersected with everything
changed since round 3 (commit `8325d4d`). This report **replaces** the round-3
report; every carried finding below was re-verified against the current tree,
not copied.

**Delta verification (traced through code, not assumed from green tests):**

- **`src/io/fastq.rs` (8102985, MultiGzDecoder):** the fix is correct. Verified
  against the pinned flate2 1.1.10 source (`MultiGzDecoder::new` =
  `GzDecoder::new(r).multi(true)`; the multi loop continues members until
  `fill_buf()` EOF, CRC-checked per member). The regression test is genuine:
  its fixture asserts exactly two `\x1f\x8b` magics, drives the same
  `process_file -> open_compressed` path the CLI uses, and pins content and
  ordering of records from both members. `src/io/fasta.rs` imports
  `DefaultCompressedFileReader` from this module (fasta.rs:134), so FASTA
  inputs get the fix for free — no remaining single-member FASTQ/FASTA reader
  exists (`src/core/database/persistence.rs:245` uses `GzDecoder` on a
  roundtrip format this crate itself writes single-member, which is fine).
  Three further defects in this file's current state are new findings below
  (WR-15/WR-16/WR-17), plus one behavioral edge of the switch (IN-12).
- **`src/database/prefix_cache_merge.rs` (8f23225, Windows share-mode
  injection in `mod tests` only):** sound. On Windows the planted file is
  selected (`metadata().len()` = 18 > 0), `merge_single_prefix_hashmap`'s
  `File::open` fails with a sharing violation under `share_mode(0)`, the
  `_share_lock` binding is declared after `merger` and so drops after it needs
  to — and drop order at scope end releases the lock before the merger's
  `Drop`, so no residue is left behind. Production code is unchanged since
  round 3; all six carried warnings and ten carried infos remain open at
  their (shifted) line numbers.
- **`tests/merge_cleanup_tests.rs`, `tests/merge_bounded_memory_tests.rs`
  (8f23225, Windows cfg-gating + FILE_WRITE_ATTRIBUTES backdate):** correct.
  `access_mode(FILE_WRITE_ATTRIBUTES) | custom_flags(FILE_FLAG_BACKUP_SEMNATICS)`
  is the right pair for opening directories on Windows, and the non-Windows
  branch's `File::open(dir)` + `set_times` is valid on Unix. The duplicated
  `backdate` helper across the two binaries is deliberate and documented
  (avoids cross-binary test coupling); not flagged.
- **`tests/merge_routing_tests.rs` (cc64fbc, factory-only `mod common`
  narrowing):** sound. `tests/common/factories.rs` exports both
  `create_test_database` and `encode_test_kmer`; the header byte offsets the
  tests patch (`total_kmers` at [10..18), `data_offset` at [26..34), 42-byte
  header) were verified against `DatabaseHeader::write_to`
  (format.rs:183-204) and the `read_header_of` rejection text
  ("Unsupported data_offset {} (expected 42)") at format.rs:517 — the tests'
  quoted messages match. The sweep/subdir contracts the cleanup tests rely on
  (`MERGE_TEMP_PREFIX`, 7-day `DEFAULT_MERGE_TEMP_TTL`, `file_type()` symlink
  refusal, `mtime >= cutoff` protection) were verified in
  `temp_lifecycle.rs:98-260`. No defects found in the three test files beyond
  IN-13.

**No critical findings.** The warning profile is unchanged in kind: the
strongest defects are the carried WR-01 (a user-facing error message promises
shard preservation that the merger's own `Drop` voids before the caller reads
it), the carried WR-11 (the metadata sidecar is written to a path the
production route guarantees to delete), and three new fastq.rs public-API
defects (WR-15/16/17) exposed now that this file is in scope.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: The failed-bucket "shard files PRESERVED for recovery" promise is voided by RAII Drop before the error reaches the caller (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:683-691` (abort error promising preservation under a named dir), `:551-571` (`should_remove_shards` decision + "PRESERVED on disk for recovery" log), `:306-307` (every shard path registered up front), `:1510-1543` (`Drop` removes every registered shard, then `TempDir::close()` removes the whole tree); sole production caller `src/database/format.rs:1805` (`merger.external_sort_merge(&temp_output)?` drops the merger on return)
**Issue:** When a bucket merge fails, phase 2 keeps that bucket's shards and returns an error stating they "were PRESERVED for recovery under '<dir>'". The error propagates through `external_sort_merge`'s `?` to `merge_databases_prefix_cache_to_path`, whose `?` (format.rs:1805) drops the merger at function exit; `Drop` then removes every path in `self.shard_paths` — including exactly the failed buckets' shards — and deletes the whole `rustkmer-merge-<rand>` tree. The directory named in the error does not exist by the time the operator reads it. Inputs remain intact (recovery-by-rerun works), so no permanent data loss — but the advertised recovery path is unreachable in every default-configuration production flow. The unit test `failed_bucket_aborts_the_merge_with_err` (whose Windows arm this round's delta added) still asserts `shard_path.exists()` while `merger` is alive — before the `?` chain triggers `Drop` — so it proves the wrong moment on both platforms.
**Fix:** Either make the promise true or stop making it. (a) On the `error_count > 0` path in `merge_prefix_buckets`, disarm cleanup before returning: `if let Some(dir) = self.merge_temp_subdir.take() { let kept = dir.keep(); /* name `kept` in the error */ }` — mirroring the `keep_intermediate` arm of `Drop`; the stale-dir sweep reclaims it later. Or (b) reword the error to state the shards were cleaned up and that `--keep-intermediate` preserves them. Either way, extend the test to assert on-disk state AFTER the merger is dropped.

### WR-02: u32 count accumulation can overflow — debug panic, silent wrap in release; the in-memory route saturates (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:782` (`*kmer_counts.entry(kmer).or_insert(0) += count`), `:970` (`current_count += top.count`), `:1043` (`current_count += consumed.count`)
**Issue:** Both per-bucket writers sum counts with plain `+=`. A merged count exceeding `u32::MAX` panics in debug builds and silently wraps in release; the WR-04 conservation check cannot catch it (it compares record COUNTS, not count VALUES), so the wrapped value flows into output records under a truthful-looking header. The in-memory merge route deliberately uses `saturating_add`; the prefix-cache route — selected for merges too large for memory — keeps the weaker arithmetic. The in-code comment (:986-990) records this as deferred to 03-REVIEW-DISPOSITION.md; it remains a live defect in an in-scope file.
**Fix:** `*e = e.saturating_add(count)` in the hashmap writer; `current_count = current_count.saturating_add(top.count)` / `.saturating_add(consumed.count)` at both streaming sites — matching the in-memory route's policy.

### WR-11: The metadata JSON sidecar is written to a path the to-path route guarantees to delete (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:1436-1442` (`output_path.with_extension("json")` write), route handoff `src/database/format.rs:1801-1833` (output written to `<merge-subdir>/external_sort_merge_output.tmp`, only the `.tmp` is renamed to the destination), Drop at `prefix_cache_merge.rs:1510-1543`
**Issue:** `concatenate_final_output` unconditionally writes a `create_metadata` JSON next to `output_path`. On the only production route, `output_path` is the temp file INSIDE the merger's RAII subdir: the caller renames only the `.rkdb` temp file to the destination, and the merger's `Drop` then deletes the whole subdir — sidecar included. The merged database at its final destination never receives a metadata sidecar; the serialize+write work runs on every merge and its result is guaranteed garbage. Databases built via the `save` path do get one (`src/core/database/persistence.rs:77`), so this is a route-parity defect.
**Fix:** Move the sidecar write out of `concatenate_final_output` into `merge_databases_prefix_cache_to_path`, after the rename/copy succeeds, keyed on the FINAL `output_path`; or delete the block if merged databases are not meant to carry sidecars.

### WR-12: `ExternalSortMerger::new` panics on an empty input list — public API, unguarded index (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:129` (`RKDatabase::read_header_of(&input_files[0])`)
**Issue:** The constructor indexes `input_files[0]` before any guard. `ExternalSortMerger` is re-exported as public API (`src/database/mod.rs:23`) with a `pub fn new`, so any external caller (PyO3 bindings, downstream crates, integration tests) passing an empty `Vec` gets an index-out-of-bounds panic instead of a `ProcessingError`. The sole in-crate caller guards this itself (format.rs:1738-1742), but the public constructor remains the panic surface.
**Fix:** At the top of `new`: `if input_files.is_empty() { return Err(crate::error::ProcessingError::new("At least one input database is required")); }`.

### WR-13: Zero-length merged buckets are deleted even under `--keep-intermediate`, contradicting the flag's documented "keeps everything" contract (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:1204-1208` (unconditional `let _ = std::fs::remove_file(&prefix_file);` on the empty-file branch); contract stated at `:46-47` and the correctly-gated sibling at `:1238-1240`
**Issue:** Phase 3 removes a zero-length merged bucket file unconditionally, while every other intermediate removal in the same loop and in `should_remove_shards` is gated on `!self.keep_intermediate`. Both per-bucket writers can legitimately leave an empty merged file (all shards shorter than one 20-byte record), so the branch is reachable. Small impact, but the flag's semantics are stated absolutely in this same file.
**Fix:** `if !self.keep_intermediate { let _ = std::fs::remove_file(&prefix_file); }` (the warning log can stay unconditional).

### WR-14: No k-mer-size range validation — headers with `kmer_size` in 65..=127 or 0 pass every check, then shift-overflow (debug panic) or silently collapse every canonical key to 0 (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:129-130` (`kmer_size = first_header.kmer_size as usize`, no range check), `:356-357` (canonicalization with that k), `:1153-1156` (`get_prefix_4mer`'s shift); sentinel `src/kmer/encoding.rs` (`reverse_complement_u128` returns 0 for `length > 64`), `MAX_KMER_SIZE_IN_U128 = 64`
**Issue:** A foreign or corrupt header with k in 65..=127 enters the merge unvalidated: (a) `get_prefix_4mer` computes a shift >= 128 for k >= 68 — panic in debug, masked shift in release (bucketing degenerates toward the low-byte shape CR-02 fixed); (b) whenever `self.canonical` is true, `reverse_complement_u128`'s `return 0` sentinel makes `canonical_kmer_u128` = `min(kmer, 0)` = 0 for EVERY record (re-verified: `canonical.rs:72-82` always returns `Ok`, so the `?` cannot intercept) — all k-mers collapse to key 0 with counts summed, emitted under a truthful-looking `sorted: true` header with `total_kmers = 1`. The crate's stated policy for corrupt files is loud rejection, not silent garbage.
**Fix:** In `ExternalSortMerger::new`, after reading the first header: `if kmer_size == 0 || kmer_size > crate::kmer::encoding::MAX_KMER_SIZE_IN_U128 { return Err(ProcessingError::new(format!("Unsupported k-mer size {kmer_size} (expected 1..=64) for prefix-cache merge"))); }`.

### WR-15: `total_sequence_length` and `average_quality` ignore compression entirely, unlike every sibling FASTQ helper and the already-fixed FASTA analogues (new this round)

**File:** `src/io/fastq.rs:424-442` (`total_sequence_length` opens the raw file with `io::BufReader::new(std::fs::File::open(path))` at :427-429), `:451-486` (`average_quality`, same raw open at :454-456); contrast `:58-88` (`DefaultCompressedFileReader::open_compressed`, used by `process_file`, `process_file_with_progress`, `validate_fastq_file`, `count_sequences`) and `src/io/fasta.rs:184-236` (the FASTA `count_sequences`/`total_sequence_length` were fixed for exactly this defect class — fasta.rs:338-360 carries a "WR-03 regression" test pinning gzipped inputs)
**Issue:** Both public functions parse a `.fastq.gz` path as uncompressed FASTQ: the decoder bytes are handed straight to `bio::io::fastq::Reader`, which either errors with an opaque record-parse message (a `.gz` caller gets "Error reading FASTQ record" with no hint the file is compressed) or, if compressed bytes happen to line up as lines, returns a meaningless statistic. The module's contract (transparent compression, `CompressionType::from_path`) and the sibling functions all support gzip; the FASTA twins of these two functions were explicitly repaired for this same class while the FASTQ ones were left behind.
**Fix:** Route both through the shared reader, as fasta.rs does:
```rust
let (reader, _) = DefaultCompressedFileReader::open_compressed(path)?;
let reader = Reader::new(reader);
```
and add the gzipped-input regression test mirroring `fasta.rs:343-360`.

### WR-16: `count_sequences` swallows parse errors and counts them as sequences (new this round)

**File:** `src/io/fastq.rs:410-413` (`for _ in reader.records() { count += 1; }`)
**Issue:** The loop discards each `io::Result` without inspecting it. Verified against bio 2.3.0 (`bio/src/io/fastq.rs:501-509`): `Records::next()` returns `Some(Err(err))` for a malformed record and the iterator keeps polling afterwards. So a truncated or corrupt FASTQ yields `Ok(count)` where count includes at least one error item — the function's contract ("Number of sequences or error") is violated exactly on the inputs where the caller most needs to know. Every sibling (`process_file`, `validate_fastq_file`) propagates record errors with context.
**Fix:**
```rust
for record_result in reader.records() {
    record_result.map_err(|e| {
        ProcessingError::with_context(
            format!("Error reading FASTQ record from file: {:?}", path),
            e,
        )
    })?;
    count += 1;
}
```

### WR-17: `filter_by_quality` / `average_quality` document Phred scores but operate on raw ASCII bytes — doc-following callers get a near-no-op filter (new this round)

**File:** `src/io/fastq.rs:283-305` (`filter_by_quality`, doc at :287 says "Minimum quality score (0-40 for Phred+33)" while :295 compares `*q >= min_quality` against raw Phred+33 byte values), `:451-486` (`average_quality` returns the mean of raw ASCII values — the module's own test :570-572 asserts 72.5, i.e. ASCII 'I'/'H', not the Phred 40/39 mean of 39.5)
**Issue:** A caller following the documented 0-40 range and passing, say, `20` (intending Q20) compares every quality byte (>= 33 for any real data) against 20 — the filter keeps everything, silently disabling quality filtering for downstream analysis. Passing `30` behaves identically. The raw-byte semantics are only discoverable from the test fixtures. Same class for `average_quality`: the returned number is ~33 higher than any documented "quality score" scale and is unlabeled.
**Fix:** Either decode before comparing (`*q - 33 >= min_quality`, guarding `*q >= 33`) and subtract 33 in `average_quality`'s accumulator — or fix both doc comments to state "raw Phred+33 ASCII value (e.g. 55 for Q20)" and rename the parameter (`min_quality_ascii`). The former matches the documented contract; the latter is the non-breaking option.

## Info

### IN-02: `Drop` logs the wrong directory when `TempDir::close()` fails (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:1531-1539` (`.take()` then `self.shard_dir().display()`), fallback at `:226-231`
**Issue:** After `self.merge_temp_subdir.take()`, `shard_dir()` falls back to the PARENT `temp_dir`, so the `close()`-failure warning names the parent, not the `rustkmer-merge-<rand>` subdir it failed to remove.
**Fix:** Capture `dir.path()` before `close()` and log that.

### IN-03: Phase-1 log claims parallel bucketing; the loop is serial (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:283-287` ("Using {} worker threads for parallel bucketing") vs the serial `for` loop at `:314`
**Issue:** `split_files_by_prefix` logs a worker-thread count but iterates input files serially; `num_workers` appears only in that misleading log. (Phase 2 IS parallel.)
**Fix:** Reword the log to describe sequential bucketing (or drop the worker count from it).

### IN-04: Dead duplicate shard readers masked by an impl-level `#[allow(dead_code)]` (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:106` (`#[allow(dead_code)]` on the whole impl), `:1065-1080` (`read_entries_from_file_sync`), `:1474-1489` (`read_entries_from_file` — a byte-for-byte duplicate with a `&self` receiver); also the always-true guard `:364` (`prefix < self.num_buckets` after a `& 0xFF` mask)
**Issue:** Neither reader has any caller in the crate (grep across `src/` and `tests/`); they are near-identical duplicates, and the impl-wide `allow` also masks any FUTURE dead code in the module. The `prefix` guard can never be false (mask yields 0..=255 against 256 buckets).
**Fix:** Delete both readers and the dead `prefix` guard; narrow the `#[allow(dead_code)]` to specific items if any legitimately need it.

### IN-05: `total_kmers` reflects the FIRST input only; `estimated_kmers_per_file` and `num_threads` are never read (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:156`, `:210`, `:246`, `:67`
**Issue:** The "Total k-mers" progress line reports input[0]'s record count as if it were the merge total; `estimated_kmers_per_file` (name says per-file estimate; value is the first file's total) is write-only; `num_threads` is assigned and never read (rayon's global pool is used).
**Fix:** Sum `total_kmers` across all read headers (they are all read at :135-139 anyway) or relabel the log; delete the two dead fields or wire them.

### IN-07: `is_multiple_of` raises the effective MSRV above the documented Rust 1.80+ baseline (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:599`, `:1385`
**Issue:** `usize::is_multiple_of` was stabilized in Rust 1.87; CLAUDE.md declares "Rust 1.80+ stable channel" as the baseline and `Cargo.toml` pins no `rust-version` (verified absent), so a 1.80..1.86 toolchain fails to compile with an unexplained error.
**Fix:** Either add `rust-version = "1.87"` to `Cargo.toml` (and update CLAUDE.md), or use `done % 10 == 0` / `processed_kmers % 1_000_000 == 0`.

### IN-08: Final prefix-cache output is flushed but never fsync'd, unlike every other artifact in the route (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:1408` (`writer.flush()?` only), contrast `:846`, `:1060`, `:1258` (intermediates all `sync_all`)
**Issue:** Every intermediate artifact in the route is fsync'd, but the one file the user keeps is not — a crash after flush can leave a truncated final database.
**Fix:** After `writer.flush()?`, `drop(writer)` then `File::open(output_path)?.sync_all()`.

### IN-09: The 03-16 "canonicalization failure propagates with `?`" claim is vacuous (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:350-357` (comment + `?`); `src/kmer/canonical.rs:72-82` (`canonical_kmer_u128` always returns `Ok` — re-verified this round)
**Issue:** `canonical_kmer_u128` has no error path, so the `?` can never fire and the comment's error-propagation story documents a guard that does not exist.
**Fix:** Reword the comment to state canonicalization is infallible for validated k, or make `canonical_kmer_u128` return `Err` for `k == 0 || k > 64` (which would also harden WR-14).

### IN-10: A streaming-writer refusal aborts the whole merge with no fallback and no remediation hint (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:957-965` (refusal error text), `:530-541` (auto-mode dispatch with no post-refusal fallback), `:683-691` (any single bucket failure aborts)
**Issue:** For same-mode inputs no header check can gate (e.g. a large UNsorted non-canonical database — `sorted: false` files are legal), auto mode selects the streaming writer, the record-level backstop refuses a descending run, and the entire merge fails — although the hashmap writer could complete it correctly. Neither the refusal message nor the abort error tells the operator the one-flag workaround.
**Fix:** Append a remediation line to `descending_run_err` ("re-run with --merge-mode memory to use the sorting per-bucket writer"), or catch the refusal in the auto branch only and retry that bucket with `merge_single_prefix_hashmap`.

### IN-11: Two vacuous tests in the module's test module (carried, still open)

**File:** `src/database/prefix_cache_merge.rs:1549-1562` (`test_external_sort_merger_creation` asserts only `is_err()` on two nonexistent paths — any failure cause passes), `:1564-1568` (`test_merger_structure` asserts only that a `tempfile::tempdir()` path exists — it tests tempfile, not the merger)
**Issue:** `test_merger_structure` proves nothing about the code under test; the creation test cannot distinguish "file not found" from a genuine constructor-contract rejection. Pure test noise in an otherwise high-discipline suite.
**Fix:** Delete `test_merger_structure`; in the creation test, assert the error message mentions the missing file (e.g. `assert!(err.to_string().contains("test1.rkdb"))`).

### IN-12: The MultiGzDecoder switch hard-errors on trailing garbage after the final member; the "byte-identical on single-member files" comment overclaims (new this round)

**File:** `src/io/fastq.rs:67-75` (comment), `:73` (`MultiGzDecoder::new(file)`)
**Issue:** Verified against flate2 1.1.10 (`gz/bufread.rs` `GzDecoder::read`, `GzState::Finished` arm): in `multi` mode, any non-EOF bytes after a member trigger a new header parse; bytes that are not a valid gzip header surface as an io error mid-stream. The old `GzDecoder` stopped at the first member and ignored the rest. So a `.fastq.gz` with trailing junk (padded writes, appended text, a torn second member) previously counted the first member silently — now the read fails loudly. Loud is the right direction for genomics data, but: (a) the code comment claims byte-identical behavior on single-member files, which holds only for files with no trailing garbage; (b) no test pins the trailing-garbage outcome, so a future flate2 semantic change would be invisible.
**Fix:** Amend the comment ("a file with trailing non-gzip garbage now errors instead of silently stopping at the first member"), and add a small test pinning the chosen behavior for `member + b"junk"`.

### IN-13: Two "GUARD" asserts in the bounded-memory tests are tautologies, and the `estimated - 1` budgets latent underflow (new this round)

**File:** `tests/merge_bounded_memory_tests.rs:406-414` (`let budget = estimated - 1; assert!(estimated > budget, ...)` — `estimated > estimated - 1` is always true for `estimated > 0`), `:720-727` (same pattern)
**Issue:** Both guards are advertised as premise-assertions ("derived not hard-coded... asserted to sit below the estimate") but can never fire; the file's own discipline (e.g. `model_change_routes_a_budget_the_old_model_admitted_to_streaming` in merge_routing_tests.rs:948-956, whose guard CAN fire) shows what these were meant to be. Additionally, if `estimated` were ever 0 (an empty input reaching this code path), `estimated - 1` underflows and panics in debug builds rather than failing the guard. Currently unreachable because the fixture sizes are asserted first, but the guard gives no protection if the fixture ever changes.
**Fix:** Assert the meaningful premise instead — e.g. `assert!(estimated > 0 && budget < estimated)` computed without subtraction (`let budget = estimated.checked_sub(1).expect("estimate must be positive")`), or assert `n > 0` explicitly before subtracting.

---

_Reviewed: 2026-10-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
