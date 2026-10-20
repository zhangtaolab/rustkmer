---
phase: 02-parallel-counting
fixed_at: 2026-07-02T00:00:00Z
review_path: .planning/phases/02-parallel-counting/02-REVIEW.md
iteration: 1
findings_in_scope: 10
fixed: 10
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-07-02T00:00:00Z
**Source review:** `.planning/phases/02-parallel-counting/02-REVIEW.md`
**Iteration:** 1 (second fix pass — the first pass fixed the original 4 warnings in commits 7ccfd11/bc97c80/9357b89/0c4f6c9; this pass addresses the fresh re-review's 5 new warnings + 5 still-open Info findings)

**Summary:**
- Findings in scope: 10
- Fixed: 10
- Skipped: 0

## Fixed Issues

### WR-01: `KmerCounter::total_kmers` semantics shift breaks `get_filtering_stats` reporting contract

**Files modified:** `src/hash/table.rs`, `src/hash/filtering.rs`
**Commit:** `a545a2d`
**Applied fix:** Documentation fix (option b — lower-risk). The WR-03 fix that moved `total_kmers.fetch_add` below the overflow check changed the meaning of `total_kmers` from "attempts" to "successes", which propagates into `FilteringResult::total_before` / `kept_percentage` via `get_filtering_stats`. Documented the semantic shift in three docstrings (`KmerCounter::get_filtering_stats`, `FilteringResult::total_before` field, `FilteringResult::new`) and added a regression test `test_filtering_stats_after_overflow_uses_success_denominator` that seeds one k-mer at the `u32::MAX` ceiling, attempts an overflow increment (which fails and does not advance `total_kmers`), successfully increments a second k-mer, then pins the post-overflow `FilteringResult::total_before` to equal `counter.total_kmers()`. Chose option (b) over (a) (tracking a separate `total_attempts` atomic) because the new "successful k-mers" denominator is arguably more correct for retention reporting and reverting/re-tracking would risk introducing a new bug. Flagged for human verification per the logic-bug caveat — the test pins the value but a human should confirm the documented semantics match product intent for saturating inputs.

### WR-02: Aggregate warning `eprintln!` in `process_one_record` still races on stderr across rayon workers

**Files modified:** `src/cli/commands/count.rs`
**Commit:** `26cbf36`
**Applied fix:** Changed `process_one_record` to return `ProcessingResult<u64>` (the per-record skip count) instead of emitting the warning itself. Replaced the `try_for_each` calls in both `process_fasta_file` and `process_fastq_file` (4 call sites total: chunk + remainder in each) with `try_fold` + `try_reduce` to aggregate per-record skips into a chunk-level total. Emit ONE `eprintln!` per chunk from the single-threaded producer thread after the `par_iter` completes, removing the cross-worker stderr race entirely. Also dropped the now-unused `record_id` and `show_warnings` parameters from `process_one_record`'s signature. Verified `cargo build`, `cargo clippy --lib`, and the full `cargo test` suite (311 tests) all pass.

### WR-03: `count_sequences` and `total_sequence_length` in `src/io/fasta.rs` still open gzipped files as raw bytes

**Files modified:** `src/io/fasta.rs`
**Commit:** `fad18ef`
**Applied fix:** Applied the same one-call swap WR-01 used for `validate_fasta_file` to both sibling helpers: replaced `io::BufReader::new(std::fs::File::open(path))` with `DefaultCompressedFileReader::open_compressed(path)` (importing the `CompressedFileReader` trait so the method is in scope). Both functions now transparently decompress `.gz` / `.bz2` / `.xz` inputs. Added a regression test `test_count_sequences_and_total_length_gzipped` that writes a gzipped FASTA (3 records, total length 23) and asserts both functions return the correct counts.

### WR-04: `KmerCounter::merge` is safe for single-threaded use but its `&self` signature hides a state-publishing race under concurrent `merge`/`increment`

**Files modified:** `src/hash/table.rs`
**Commit:** `b4d3c62`
**Applied fix:** Documentation-only fix (no signature change). Added a "Thread safety (WR-04)" section to the `merge` docstring stating that `merge` MUST NOT run concurrently with `increment` or another `merge` on the same `KmerCounter`: the per-loop-iteration atomic-publish of `total_kmers` / `unique_kmers` (the WR-02 fix) is only guaranteed to stay consistent with the table contents when observed single-threaded, because a concurrent `increment` completing during `merge`'s loop can land its `fetch_add` between `merge`'s local accumulator and the final publish, transiently under-reporting `total_kmers()`. The values eventually converge but the transient window is observable. Pointed at the two recommended patterns: merge into a counter that is not currently being incremented, or hold an external mutex around `merge`.

### WR-05: `pyrustkmer` `add_from_fasta` / `add_from_fastq` decompression only handles `.gz`, silently mis-handling `.bz2` / `.xz`

**Files modified:** `pyo3/Cargo.toml`, `pyo3/src/counter.rs`, `pyo3/tests/test_counter.py`
**Commit:** `0920cb4`
**Applied fix:** Replaced the inline `.gz`-only compression detection in both `process_fasta_file_on_counter` and `process_fastq_file_on_counter` with a call to `rustkmer::io::fastq::DefaultCompressedFileReader::open_compressed` — the same shared opener the CLI path uses. This brings the Python bindings to parity with the CLI (gzip/bzip2/xz coverage). Removed the now-unused `FastaProcessor` / `FastqProcessor` imports. Added `bzip2 = "0.4"` and `xz2 = "0.1"` to `pyo3/Cargo.toml` so the decoders link (both already transitive deps via the rustkmer path dep, so the lockfile entries are shared — no version bloat). Added 4 regression tests (`.bz2` and `.xz` for both FASTA and FASTQ) alongside the existing `.gz` test. Verified all 85 Python tests pass against the freshly-built wheel installed into `.venv313`.

### IN-01: `tests/parallel_count_tests.rs::count_input_with_workers` silently drops worker errors

**Files modified:** `tests/parallel_count_tests.rs`
**Commit:** `1e56098`
**Applied fix:** Collected the `ScopedJoinHandle`s into a `Vec` inside the `std::thread::scope` closure and joined each one, propagating the first worker `Err` via `?` (the scope closure now returns `ProcessingResult<()>`). A panic inside a worker is surfaced via `join().expect("worker thread panicked in count_input_with_workers")`. This hardens the differential against false-PASS results if a future input overflows or a future failure mode is added to `increment`. Verified the 4 un-ignored tests still pass (the `i` in output is the one-shot `#[ignore]`d baseline capture).

### IN-02: `--sort` is a parsed-but-ignored no-op alias whose help text still implies it actively sorts

**Files modified:** `src/cli/args.rs`
**Commit:** `2c5d0c1`
**Applied fix:** Tightened the clap help string from "Sort output by k-mer sequence (default: sorted for optimal query performance)" to "Retained no-op alias: sorting is enabled by default (decision D-09). Has no effect; pass --no-sort to disable sorted output." No behavior change — `--sort` is still parsed by clap, bound as `_sort`, and never consulted (`should_sort = !*no_sort` per D-09).

### IN-03: `KmerCounter::new` accepts a `_num_threads` parameter it silently ignores

**Files modified:** `src/hash/table.rs`
**Commit:** `996c74e`
**Applied fix:** Updated the `KmerCounter::new` docstring for the `num_threads` arg to say "Currently unused; thread-pool sizing is performed by the caller via `rayon::ThreadPoolBuilder::build_global` (see `execute_count` / `PyCounter::new`). Retained for API stability." Did NOT remove the parameter (that would be a breaking change, out of scope).

### IN-04: `pyrustkmer` `PyCounter::new` silently ignores a failed `build_global` even on the first construction

**Files modified:** `pyo3/Cargo.toml`, `pyo3/src/counter.rs`
**Commit:** `52bfc78`
**Applied fix:** Replaced the `let _ = ... build_global();` discard with an `if let Err(e) = ... { log::warn!(...); }` that surfaces the discarded failure under `RUST_LOG=warn`. Preserved the silent-success contract (no hard error) so the T-02-12 / Pitfall 3 second-call case still does not fail. Added `log = "0.4"` to `pyo3/Cargo.toml` (already a transitive dep via the rustkmer path dep, so the lockfile entry is shared).

### IN-05: `Cargo.toml` declares `proptest = "1.5"` in both `[dependencies]` and `[dev-dependencies]`

**Files modified:** `Cargo.toml`
**Commit:** `188e115`
**Applied fix:** Removed the `proptest = "1.5"` declaration from `[dependencies]` (root `Cargo.toml`). The `[dev-dependencies]` declaration at line 100 already covers all test usages, so removing the runtime declaration does not break any test. Verified `cargo build` succeeds and `cargo test --no-run` still compiles all proptest-using tests.

## Skipped Issues

None — all 10 in-scope findings were fixed.

---

_Fixed: 2026-07-02T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
