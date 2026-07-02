---
phase: 02-parallel-counting
fixed_at: 2026-07-02T03:44:05Z
review_path: .planning/phases/02-parallel-counting/02-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-07-02T03:44:05Z
**Source review:** `.planning/phases/02-parallel-counting/02-REVIEW.md`
**Iteration:** 1
**Fix scope:** critical_warning (Warning findings only — 0 Critical in source review; 5 Info findings IN-01..IN-05 are out of scope and intentionally not fixed)

**Summary:**
- Findings in scope: 4 (all Warning-tier: WR-01..WR-04)
- Fixed: 4
- Skipped: 0

All fixes were verified by `cargo build`, the relevant unit/integration tests, `cargo clippy --lib` (clean), and where applicable end-to-end CLI invocation against gzipped/bz2/xz fixtures. The full `cargo test` suite (309 tests across lib + integration targets) passes after the final fix.

## Fixed Issues

### WR-01: Compressed-FASTA inputs (`.fa.gz` / `.fasta.gz` / `.fna.gz` / `.ffn.gz`) produce wrong results silently in the parallel CLI path

**Files modified:** `src/cli/commands/count.rs`, `src/io/fasta.rs`
**Commit:** `9357b89`
**Applied fix:**

Routed the FASTA CLI path through the same compression-aware opener the FASTQ sibling path uses (`DefaultCompressedFileReader::open_compressed`), which transparently decompresses gzip/bzip2/xz inputs. Two call sites were fixed:

1. **`process_fasta_file` (`src/cli/commands/count.rs`)** — the parallel count path. Previously it opened the file via plain `File::open` + `BufReader`, so a `.fa.gz` / `.fasta.gz` / `.fna.gz` / `.ffn.gz` input was parsed as raw deflate bytes by `bio`'s reader — silently producing garbage sequences and 0 counted k-mers, or erroring on the first record. The CLI file-type router already dispatched those extensions to this branch, so the bug was reachable from a plain `rustkmer count input.fa.gz`.

2. **`validate_fasta_file` (`src/io/fasta.rs`)** — the validation step run immediately before `process_fasta_file`. This had the same plain-`File::open` gap and rejected gzipped inputs with a `"stream did not contain valid UTF-8"` error before the (now-fixed) processor ever ran. The FASTQ sibling `validate_fastq_file` already used `open_compressed`; this brings the FASTA path to parity. This second site was not cited in the WR-01 File: line but was required for the fix to actually work end-to-end — the validator would have rejected the file before `process_fasta_file` ran.

End-to-end verified: `rustkmer count -k 5 -i in.fa{,.gz,.bz2,.xz}` now reports identical results (60 k-mers processed, 12 unique on the test fixture). Added `test_validate_gzipped_fasta_file` regression test in `src/io/fasta.rs` pinning the validator behavior.

The review's note that `CompressedFileReader` lives in `src/io/fastq.rs` despite being format-agnostic is preserved as a follow-up comment in the code.

### WR-02: `KmerCounter::merge` persists partial state on overflow and does not update `unique_kmers`/`total_kmers`, leaving the counter internally inconsistent

**Files modified:** `src/hash/table.rs`
**Commit:** `bc97c80`
**Applied fix:**

Updated `total_kmers` and `unique_kmers` incrementally inside the merge loop so the per-iteration boundary keeps the atomics in sync with the table contents. On a mid-loop per-k-mer overflow, the partial atomics are now published before returning `Err`, so the counter is **poisoned-but-internally-consistent** rather than internally inconsistent.

Rolling back the partial DashMap mutation on overflow would require cloning the whole table before the loop (prohibitively expensive at genome scale), so the contract was instead **documented explicitly** on the `merge` docstring: on overflow, all k-mers processed before the overflowing one are already merged into `self.table` and the atomics correctly reflect that partial state, but the counter should be treated as tainted and discarded by the caller. This matches option (b) from the review's fix sketch ("document explicitly that the counter is poisoned after a failed merge").

The successful-merge path still produces the same numeric result as before: the sum of merged `count` values equals `other.total_kmers()` in normal operation (existing `test_merge` confirms `total_kmers() == 4` after merge still holds).

Added `test_merge_overflow_poisons_consistently` regression test asserting the invariant: after an overflow `Err`, `total_kmers()` equals the sum of counts in `self.table` and `unique_kmers()` equals the entry count.

This is a logic-correctness fix flagged for human verification per the verification strategy.

### WR-03: `total_kmers` is incremented before the overflow check, so a failed `increment` inflates the total count

**Files modified:** `src/hash/table.rs`
**Commit:** `7ccfd11`
**Applied fix:**

Moved the `total_kmers.fetch_add(1, ..)` call from the top of `KmerCounter::increment` to after the overflow check. Previously the bump happened unconditionally before `entry().and_modify(..)` ran, so a per-k-mer overflow attempt (returning `Err`) still inflated the reported total — a numeric-correctness discrepancy. Now `total_kmers()` reflects the number of k-mers successfully counted, matching the field's updated docstring ("Total k-mers successfully counted (excludes per-k-mer overflow attempts that return `Err` from `increment`)").

Also added a regression assertion inside the existing `test_overflow_preserved` unit test pinning the corrected behavior: `counter.total_kmers()` must equal 0 after a failed overflow increment.

This is a logic-correctness fix flagged for human verification per the verification strategy. The new behavior is the one the review's recommended patch implements ("Only count successful increments — failed overflow attempts must not inflate the total").

### WR-04: Concurrent `eprintln!` to stderr from rayon workers can interleave

**Files modified:** `src/cli/commands/count.rs`
**Commit:** `0c4f6c9`
**Applied fix:**

Applied option (b) from the review's fix suggestions: aggregate skipped (invalid-base) k-mers into a local `u64` counter inside `process_one_record`'s per-record loop and emit a single aggregate `eprintln!("Warning: Skipped {N} k-mers with invalid characters in sequence {X}")` after the record completes. Previously every invalid window emitted its own `eprintln!` from inside the rayon worker, and concurrent workers could interleave on stderr under heavy contention; a single record full of `N`s would flood stderr from multiple workers simultaneously.

The aggregate warning still runs inside the worker (no `Mutex` needed), but reduces stderr syscalls from one-per-window to one-per-record, shrinking the interleave surface and dropping stderr volume proportionally.

End-to-end verified: a record with `N` characters now emits exactly one warning line per record (`Warning: Skipped 12 k-mers with invalid characters in sequence seq1`) instead of one per invalid window.

---

## Skipped Issues

None — all 4 in-scope Warning findings were fixed successfully.

The 5 Info findings (IN-01..IN-05) are **out of scope** for this `fix_scope: critical_warning` run and were intentionally not addressed:

- IN-01: `tests/parallel_count_tests.rs::count_input_with_workers` silently drops worker errors
- IN-02: `--sort` is parsed with `default_value_t = true` AND `conflicts_with = "no_sort"` (intentional per D-09)
- IN-03: `KmerCounter::new` accepts a `_num_threads` parameter it ignores
- IN-04: `pyrustkmer` `PyCounter::new` silently ignores a failed `build_global` even on first construction
- IN-05: `Cargo.toml` declares `proptest = "1.5"` in both `[dependencies]` and `[dev-dependencies]`

---

_Fixed: 2026-07-02T03:44:05Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
