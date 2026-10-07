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

- `cargo fmt --all --check` (a Phase 1 CI gate, `.github/workflows/ci.yml:37`)
  still fails on pre-existing rustfmt drift in `src/cli/commands/count.rs` and
  `tests/parallel_count_tests.rs`.
  status: open
  **What:** Carried from plan 03-01, re-confirmed by plan 03-03. Neither file is
  modified by any Phase 3 plan, so per the scope boundary they were left alone.
  Plan 03-03 DID close the third instance: `src/hash/table.rs` had drift and is
  now rustfmt-clean, because plan 03-03 edits that file for the `KmerKey` swap.
  **Caution for whoever closes this:** `rustfmt src/lib.rs` follows `mod`
  declarations and will silently reformat `src/cli/commands/count.rs` as a side
  effect. That happened during plan 03-03 and was reverted; format the two files
  explicitly instead, or run a plain `cargo fmt` so the diff is deliberate.
  **How to reproduce:** `cargo fmt --all --check` from the repo root.
  **Suggested fix:** `cargo fmt` (one commit, no semantic change — the drift is
  purely line-wrapping).

- `KmerCounter::memory_usage()` is a *modelled* estimate, not a measurement.
  Plan 03-03 made it branch on the DENSE-01 storage width (24 B overhead + 8 B
  key + 4 B count for k ≤ 32; 24 + 16 + 4 above), and the 24-byte
  `HASH_OVERHEAD_PER_ENTRY` constant is inherited verbatim from the pre-Phase-3
  `len * (24 + 20)` formula.
  status: open
  **What:** The DENSE-01 "roughly half the counting memory" claim is provable
  against the *keyed payload* (20 B → 12 B, a 0.6× ratio, which
  `dense_counter_memory_usage_halved_for_k21` asserts) but NOT against the
  overhead-inclusive total (36/44 = 0.818×), because the modelled hash/shard
  overhead is width-independent. Real dashmap/hashbrown slot overhead is not a
  flat 24 bytes — it depends on control-byte layout and load factor — so the
  reported total has never been a tight bound, before or after this plan.
  **Why deferred:** measuring actual per-entry cost means either a
  `stats_alloc`-style allocator hook or an empirical heap-delta measurement,
  both well outside plan 03-03's scope (which is a key-type swap).
  **Who cares:** anything reading `PyCounterStats.memory_usage` from Python sees
  a modelled number that under-reports the saving. Phase 4's benchmark is the
  right place to replace the model with a measurement.

- The dense `u64` width applies only to `KmerCounter`. Every other in-memory
  k-mer structure still uses `u128` — `merge_databases_inmemory`'s
  `HashMapBrown<u128, u32>` accumulator (`src/database/format.rs`), the
  `RKDatabase` read path, and `merge_prefix_buckets`' bucket buffers.
  status: open
  **What:** Plan 03-03's DENSE-01 scope was the counting hot path
  (`src/hash/table.rs`). An in-memory *merge* of two k=21 databases therefore
  still materializes 16-byte keys, so MERGE-01-scale merges do not yet get the
  memory win. This is consistent with 03-CONTEXT's discretion note ("whether
  dense u64 also applies to the in-memory `RKDatabase`/`DatabaseQuery` read path:
  out of scope unless the change is zero-cost while touching the counter") — it
  was not zero-cost, and it is a different module.
  **Why deferred:** each structure needs its own width-selection point and its
  own decoded-level differential; bundling them would have put DENSE-01's
  sharpness behind untested breadth.
  **Suggested fix:** a follow-up plan applying the same `KmerKey` pattern to
  `merge_databases_inmemory`'s accumulator, reusing `tests/dense_differential_tests.rs`'s
  decoded-level comparison as the gate.
