# Deferred Items — Phase 03 (Memory Safety)

## Deferred Items

- `cargo clippy --all-targets -- -D warnings` fails on 4 pre-existing
  `clippy::useless_borrows_in_formatting` errors in `src/io/fasta.rs` and
  `src/io/fastq.rs` (lines 153, 215, 342 + one in fasta.rs), introduced by a
  toolchain bump (local rustc 1.99.0; the Phase 1 clippy sweep ran on an
  older toolchain where this lint did not fire).
  status: open
  **What:** Not caused by plan 03-01 — those files are untouched by this phase's
  merge work. But plan 03-01 Task 2 lists `cargo clippy --all-targets -- -D warnings
  exits 0` as a blocking acceptance criterion, so the gate cannot pass while
  these stand. Tracked here and handled as a Rule 3 (blocking) fix inside Task 2
  rather than silently skipped.
  **How to reproduce:** `cargo clippy --all-targets -- -D warnings` from the repo root.

- `tests/merge_routing_tests.rs` declares `mod common;`, which compiles the
  shared `tests/common/{memory,performance,temp_files}.rs` helper modules into
  this test binary. That registers 20 extra `common::*::tests::*` test cases in
  `cargo test --test merge_routing_tests` output (they are the shared module's
  own unit tests, not merge-routing coverage).
  status: open
  **What:** Pre-existing convention — `tests/golden_tests.rs` and
  `tests/round_trip_tests.rs` do the same. Harmless (they pass), but it makes
  the per-target test count noisy. Not worth a deviation; a future cleanup could
  move the factories into a `common/factories.rs` submodule that carries no
  `#[cfg(test)]` tests.
  **Also:** `tests/merge_cleanup_tests.rs` (plan 03-02) does the same, for the
  same reason.

- `merge_databases_prefix_cache` writes its intermediate result to
  `config.temp_dir.join("external_sort_merge_output.tmp")` — **outside** the
  process-unique `rustkmer-merge-<rand>/` subdir plan 03-02 introduced, and it
  is never removed.
  status: open
  **What:** Found during plan 03-02 while moving every *shard* under the
  subdir. Two consequences, both pre-existing and neither introduced or worsened
  by 03-02:
  1. The file is roughly the size of the entire merged dataset and survives the
     merge — the same disk-exhaustion class MERGE-03 targets (threat T-03-05),
     so MERGE-03 is only partly met for this artifact.
  2. Its name is fixed, so two concurrent prefix-cache merges writing to the
     same `temp_dir` collide on it — the same cross-merge collision D-06 was
     chosen to remove (threat T-03-06).
  **Why deferred rather than fixed here:** plan 03-02's `<behavior>` block
  enumerates its scope precisely (shards under the subdir, RAII on the merger,
  the sweep, `RECORD_SIZE`), and this is the merge *result* handoff rather than
  a shard. Fixing it means changing where `merge_databases_prefix_cache` reads
  its result back from — a call-site decision the plan did not delegate.
  **Suggested fix (small):** write the intermediate result into
  `merger.merge_temp_subdir_path()` instead of `config.temp_dir`, or delete it
  immediately after `RKDatabase::from_file_path(&temp_output)` succeeds.
  **How to reproduce:** run a `--use-prefix-cache` merge and list `$TMPDIR` for
  `external_sort_merge_output.tmp` afterwards.

- `ExternalSortMerger::merge_prefix_buckets` logs per-bucket failures and then
  returns `Ok(())` regardless of how many buckets failed
  (`prefix_cache_merge.rs`, the `error_count` block).
  status: open
  **What:** Found during plan 03-02 while replacing the success-only cleanup
  gate. If any prefix bucket's merge errors, `error_count > 0` is only logged —
  the function still reports success, so `external_sort_merge` continues into
  `concatenate_final_output` and writes a **partial** `.rkdb` with a
  `total_kmers` header that reflects only the buckets that happened to succeed.
  The result is silent k-mer loss dressed up as a successful merge.
  **Why deferred rather than fixed here:** pre-existing, unrelated to temp-file
  lifecycle, and fixing it changes merge *outcomes* (merges that currently
  "succeed" partially would start failing) — a behavioral decision outside this
  plan's scope. Note plan 03-01 fixed two comparable latent data-loss bugs on
  the **streaming** path precisely because it promotes that path to default;
  the prefix-cache path is not the promoted default, so the same urgency does
  not apply here.
  **Suggested fix:** return `Err` when `error_count > 0`, after the loop, so
  `concatenate_final_output` never runs on partial bucket output.
