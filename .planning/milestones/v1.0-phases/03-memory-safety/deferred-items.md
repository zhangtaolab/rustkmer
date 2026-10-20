# Deferred Items — Phase 03 (Memory Safety)

## Deferred Items

- `cargo clippy --all-targets -- -D warnings` fails on 4 pre-existing
  `clippy::useless_borrows_in_formatting` errors in `src/io/fasta.rs` and
  `src/io/fastq.rs` (lines 153, 215, 342 + one in fasta.rs), introduced by a
  toolchain bump (local rustc 1.99.0; the Phase 1 clippy sweep ran on an
  older toolchain where this lint did not fire).
  status: resolved
  **Resolved:** 2026-10-10 audit — `cargo clippy --all-targets -- -D warnings`
  verified green on the current tree (exit 0); no `src/` changes since the
  04-01-era verified-green run (git log 28411ad..HEAD -- src/ is empty), so the
  fix predates Phase 04 and this entry simply lagged the code.
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
  status: resolved
  **Resolved:** 2026-10-10 — factories extracted to `tests/common/factories.rs`
  (self-test-free; `mod.rs` re-exports via `pub use factories::*`, no fork);
  `merge_routing_tests` and `merge_cleanup_tests` now `#[path]`-include the
  factory core only (29→9 and 37→17 cases). The flake vector this entry
  underestimated: CI run 37952454763's macOS leg failed on
  `common::performance::tests::test_performance_timer` running inside
  merge_cleanup_tests — also fixed (timer ceiling 150ms→2000ms).
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
  status: resolved
  **Resolved:** 2026-10-10 audit — `src/database/format.rs:1801-1804` now writes
  the intermediate under `merger.merge_temp_subdir_path()` (process-unique,
  owned by the merger's `TempDir`, RAII-cleaned); the `None` arm is the
  documented drop-time degenerate fallback. The in-code comment explicitly
  closes "the disk-exhaustion half of MERGE-03" and the T-03-06 fixed-name
  collision class.
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
  status: resolved
  **Resolved:** 2026-10-10 audit — WR-04 fix at
  `src/database/prefix_cache_merge.rs:683-691`: `error_count > 0` now returns
  `Err` (naming counts and preserving shard files under the shard dir for
  recovery), so `concatenate_final_output` never runs on partial bucket
  output. The in-code comment cites this deferred entry explicitly.
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
  status: resolved
  **Resolved:** 2026-10-10 — deliberate plain `cargo fmt` commit (ba7f451)
  covering all four drifted files (count.rs, merge_bounded_memory_tests.rs,
  merge_cleanup_tests.rs, parallel_count_tests.rs); `cargo fmt --all --check`
  green locally, CI rustfmt job unblocked.
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

## Added by Nyquist validation audit (2026-10-07)

- **BLOCKER-1 — `KmerKey` is 32 bytes, so DENSE-01's dense width INCREASES
  counting memory rather than halving it, and the assertion that "proves" it
  cannot fail.** (Supersedes the scope of the `memory_usage()` modelled-estimate
  entry below — read that entry's 0.6×/0.818× framing as applying to the
  *model* only; the real footprint is worse than either figure.)
  status: open
  **What:** `KmerKey` is an enum with a `u128` variant, so it inherits
  `u128`'s 16-byte alignment and pads to **32 bytes** (measured:
  `size_of::<KmerKey>() == 32`). For the k ≤ 32 case DENSE-01 targets, the real
  per-entry key+count is 36 B versus the pre-Phase-3 20 B — a 1.80× ratio,
  where the model claims 12 B (0.60×). The doc rationale at
  `src/hash/key.rs:31-34` ("the discriminant never adds live storage cost") is
  incorrect: the discriminant is paid on every entry, since the layout is fixed
  at compile time and the `U128` variant forces the alignment.
  **Why the tests miss it:** `KmerCounter::key_bytes()`
  (`src/hash/table.rs:361`) derives the width from `self.kmer_length`, never
  from a stored `KmerKey`, and no test inspects a `KmerKey` value (no
  `size_of` assertion, no variant accessor). So `dense_counter_memory_usage_halved_for_k21`
  (`src/hash/table.rs:1018`), `tests/dense_differential_tests.rs:237,247` and
  `tests/dense_merge_integration_tests.rs:457` all stay green under the mutation
  "always store `KmerKey::U128`". They restate the branch condition rather than
  observing the branch.
  **Scope:** DENSE-01 only. DENSE-02 (golden sha256) and DENSE-03 (decoded-level
  differential) remain sound — see `03-VALIDATION.md` §BLOCKER-1.
  **Suggested fix:** monomorphize the table over the key width (or use two
  concrete counter types selected at `new()`), keeping
  `get_all_counts() -> Vec<(u128, u32)>` unchanged for D-05/DENSE-02. Re-open
  the "Pattern 1 Option A" trade-off from 03-RESEARCH.

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

## Added by plan 03-04 (wave-merge gate)

- The plan's literal acceptance-criteria grep for open stubs matches *prose*, not
  attributes. `grep -rn '#\[ignore\]' tests/merge_routing_tests.rs
  tests/dense_differential_tests.rs tests/dense_proptest_tests.rs
  tests/golden_sha256_tests.rs tests/merge_cleanup_tests.rs` returns 3 hits
  (`merge_routing_tests.rs:43`, `:181`, `golden_sha256_tests.rs:27`) — all
  inside `//!` / `///` doc comments that *describe* the Wave-0 scaffold history
  ("began `#[ignore]`d so the target compiled against the PRE-fix API").
  status: open
  **What:** There are **zero** `#[ignore]` attributes in those 5 files. The
  attribute-shaped grep (`grep -rnE '^\s*#\s*\[\s*ignore'`) returns no matches,
  and `cargo test --test <each>` reports `0 ignored` for all five. The only two
  real `#[ignore = "..."]` attributes in the repo are the Phase 1/2 run-once
  generators (`tests/golden_generate.rs:169`,
  `tests/parallel_count_tests.rs:229`), which this plan is explicitly not
  authorized to un-ignore.
  **Why logged:** `/gsd-verify-work` should classify these three matches as
  closed stubs, not open ones. Do not "fix" them by deleting the explanatory
  doc comments — the history is worth keeping — and do not un-ignore the two
  Phase 1/2 generators.

- Verified, NOT a new defect: the streaming merge leaves **no** stray chunk
  files in `config.temp_dir` on the normal return path. A probe merge (8
  k-mers, `chunk_size: 2`, real temp dir) left only its input `.rkdb` behind —
  `TempFileManager`'s `Drop` cleans up correctly.
  status: closed
  **What:** This closes the *normal-path* half of plan 03-02's open item that
  "streaming_merge chunks (`rustkmer_sort_*.chunk`) land loose in temp_dir and
  are NOT covered by the orphan sweep". Normal cleanup is fine; what remains
  open is **only** the sweep-coverage gap — a merge SIGKILLed or
  `panic = "abort"`ed (this project's release profile) leaves chunks in
  `temp_dir` that `sweep_stale_merge_dirs` will never reclaim, because it only
  removes `rustkmer-merge-*` *directories* and never looks at loose `*.chunk`
  files. **How to reproduce:** the earlier plan 03-02 item stands; this note
  only narrows its scope so nobody re-investigates the RAII path.

- Verification technique worth reusing: a plan's "streaming route" arm is only
  proven if the **route itself** is asserted. Plan 03-04's first draft used a
  hard-coded `max_memory_usage: 1024`; the golden fixture's 20 unique k-mers
  estimate to only 960 bytes, so every "streaming" arm silently ran the
  in-memory path and the whole cross-plan composition claim was vacuous. A
  mutation test (drop the first k-mer the streaming merge emits — the exact bug
  class plan 03-01 shipped fixes for) passed against it, which is how the flaw
  was found.
  status: closed
  **What:** `tests/dense_merge_integration_tests.rs` now derives the
  over-budget budget from `RKDatabase::estimate_total_kmers` and *proves* the
  route with the `temp_dir` probe `tests/merge_routing_tests.rs` established
  (nonexistent `temp_dir` => streaming was entered, `Ok` => in-memory).
  `assert_route` fails loudly if a future fixture-size change pushes an arm
  back under the budget. The same trap applies to any future phase test that
  wants to exercise a specific merge path at toy scale.

## Added by plan 03-05 (PyO3 merge parity)

- `maturin develop` and `maturin build` both refuse to run in this repository.
  `pyo3/pyproject.toml` sets `python-source = "."` with
  `module-name = "pyrustkmer"`, but the mixed-layout package directory
  `pyo3/pyrustkmer/` has **never existed** in git history
  (`git log --all -- pyo3/pyrustkmer` returns nothing). maturin validates this
  pairing before building anything and exits 1.
  status: open
  **What:** `.github/workflows/ci.yml`'s `pyo3-build` job — a FOUND-01 merge
  gate — runs `maturin build` as its final step, so that job cannot be green as
  configured. It also means the repo has no working *documented* path for
  building the extension locally, which is why plan 03-05's `<verify>` command
  had to be replaced (see Deviations 2 and 3 in `03-05-SUMMARY.md`).
  **How to reproduce:** `cd pyo3 && maturin build` -> "python-source is set to
  `.../pyo3`, but the python module at `.../pyo3/pyrustkmer` does not exist."
  **Suggested fix (one line):** delete the `python-source` key from
  `[tool.maturin]` — this is a pure-Rust extension module with no Python
  sources to package, so maturin's mixed layout does not apply. Not done here:
  a packaging-config change is outside MERGE-04's scope and would alter the
  artifact CI publishes.
  **Workaround that works today:** build the cdylib and install it by hand —
  `cd pyo3 && PYO3_PYTHON=<venv>/bin/python cargo build --release --features
  extension-module`, then copy `target/release/libpyrustkmer.so` to
  `<venv>/lib/pythonX.Y/site-packages/pyrustkmer.so`. **`PYO3_PYTHON` must be
  set**: without it `pyo3-build-config` picks up whatever interpreter is
  discoverable through `PATH`/`CONDA_PREFIX`, and the resulting `.so` fails to
  import with `ImportError: undefined symbol: PyUnicode_EqualToUTF8AndSize`
  (seen on this machine, where the ambient interpreter is 3.14 and the venv is
  3.11).

- `pyo3/pyproject.toml`'s `[tool.pytest.ini_options] addopts` hard-codes
  `--cov=pyrustkmer ... --cov-fail-under=80`, so **every** pytest run under
  `pyo3/` exits 1 even when all tests pass: `pyrustkmer` is a compiled
  extension, so coverage is structurally 0.00% and `fail-under` always trips.
  Verified pre-existing — `pytest tests/test_counter.py` on an unmodified tree
  reports "85 passed" and then "FAIL Required test coverage of 80% not
  reached", exit 1.
  status: open
  **What:** the plan's criterion "pytest tests/test_database_merge.py exits 0"
  is unsatisfiable for *any* test file in this crate. Plan 03-05 ran the suite
  with `-o addopts=""` and documented the substitution. Compounding it,
  `.github/workflows/ci.yml` has **no** pyo3 pytest job at all (only clippy +
  `maturin build`), so the 124-test `pyo3/tests/` suite is developer-run only
  and nothing in CI would have caught this.
  **Suggested fix:** drop the `--cov*` flags from `addopts` (or move them to an
  opt-in extra), and consider adding a pyo3 pytest CI job now that the Python
  surface carries 11 new contract tests. Not done here: editing the crate's
  test configuration is outside MERGE-04's scope and would change the quality
  bar every later contributor runs under.

- `clippy::redundant_field_names` fires on `src/database/stats.rs`'s
  `StatsError::Io { #[from] source: std::io::Error }` under the local clippy
  1.99 toolchain (same bump that produced the 03-01 entry above). The lint
  targets thiserror's `#[from]` expansion — the generated `From` impl
  initializes the variant with `{ source: source }` — and the span is mapped
  back onto the field definition, so neither a field-level nor an enum-level
  `#[allow]` reaches the generated code. Pre-existing and not caused by plan
  03-10 (stats.rs is untouched by merge work), but the plan's blocking
  criterion `cargo clippy --all-targets -- -D warnings exits 0` cannot pass
  while it stands. Fixed as a Rule 3 (blocking) fix with a module-level
  `#![allow(clippy::redundant_field_names)]` plus an explanatory comment in
  stats.rs, mirroring the 03-01 precedent. A thiserror upgrade (2.x codegen
  uses the shorthand) would let the allow be dropped.
  status: closed (plan 03-10, module-level allow in src/database/stats.rs)

- `src/config/manager.rs`'s unit tests have a parallel-execution env-var race:
  `test_env_overrides` does `env::set_var("RUSTKMER_DEFAULT_K", "21")` while
  `test_config_file_operations` concurrently loads a temp config file whose
  `default_k = 25` and asserts `Some(25)`. Env beats file (which
  `test_env_overrides` itself is the proof of), so when the two tests'
  `load()` calls interleave under the full 230-test lib run's thread
  contention, the file test observes `Some(21)` and fails with
  `left: Some(21), right: Some(25)`.
  status: open
  **What:** Found during plan 03-12 Task 2's full-suite gate — one `cargo
  test` invocation failed on exactly this pair, then 20+ subsequent runs
  (filtered, paired with `--test-threads 2`, and full-suite) were all green;
  the failure is a rare scheduling-dependent flake, not deterministic. Not
  caused by 03-12 (that plan touches only `src/database/format.rs` and
  `tests/merge_routing_tests.rs`; the config module is untouched), so it is
  logged here rather than fixed — fixing it means editing a test this plan
  has no business touching.
  **Suggested fix:** make `test_config_file_operations` robust to ambient env
  (clear the `RUSTKMER_*` vars it does not set, or serialise the two tests
  behind a shared mutex), or convert `test_env_overrides` to a subprocess so
  its `set_var` cannot leak into sibling tests.
  **How to reproduce:** `cargo test --lib` repeatedly under load; observed
  once in ~25 full runs on this machine.

- `merge_single_prefix_streaming` (src/database/prefix_cache_merge.rs) assumes
  each shard is an ascending run; after the 03-16 fix a NON-canonical input's
  shard under a mixed-canonical merge (ANY input canonical) can violate that
  assumption, so the mixed-canonical correctness CR-01 closed holds on the
  auto/hashmap path but NOT on the streaming-writer subset.
  status: closed
  **What:** Found during plan 03-16 Task 2 analysis. `split_files_by_prefix`
  now writes the canonicalized `processed_kmer`, but it writes records in
  input-stream (raw-key) order — for a sorted non-canonical input the stored
  canonical values need not be ascending (e.g. raw 0xFFFFFFFF sorts last in
  stream order but stores canonical 0x000000 last in the shard). The hashmap
  bucket writer folds into a map and sorts (unaffected); the streaming bucket
  writer is a k-way heap merge over runs it assumes ascending, so a
  non-ascending shard can produce non-ascending bucket output and miss
  equal-key dedup/summing (traced by hand on the 03-16 fixture: shard
  [0x0000AB, 0x007F1234, 0x00AB8053, 0x00FF1234, 0x000000] emits 0x0000AB
  before 0x000001 and emits 0x000000 twice un-summed). Reachable with
  merge_mode="streaming" or any bucket whose shards exceed the per-bucket
  `merge_buffer_mb` threshold (auto). Not fixed in 03-16 because the plan
  explicitly froze both bucket writers ("both bucket merge writers stay as
  03-13 delivered them"); the fix is a design decision (re-sort shards,
  sort-at-bucket-writer-entry, or drop the sorted-run assumption) — Rule 4
  scale.
  **Suggested fix:** for `self.canonical` merges, sort each shard's records
  before the bucket phase reads them (or make
  `merge_single_prefix_streaming` heap-per-shard / read-then-sort each run),
  then add a mixed-canonical conservation test that forces
  merge_mode="streaming".
  **How to reproduce:** merge the 03-16 mixed-canonical fixture
  (tests/prefix_cache_output_order_tests.rs build_mixed_canonical_inputs)
  with `MergeConfig{use_prefix_cache: true, merge_mode: "streaming", ..}`;
  the output is non-ascending and 0x000000 appears twice (counts 5 and 3)
  where the oracle holds one summed record (8).
  **Closed by:** plan 03-17 (03-VERIFICATION round-3 gaps[0]) with the
  override-plus-refusal design, not the suggested re-sort: option (a) —
  `ExternalSortMerger::new` detects the mixed-canonical header set (folded
  canonical true + any input non-canonical) and forces the sorting (hashmap)
  per-bucket writer for every bucket with a `log::warn` override (a
  requested merge_mode="streaming"/"auto" merge still SUCCEEDS, correctly,
  instead of erroring); option (b) — `merge_single_prefix_streaming`
  validates every record at both `pop_front` consumption sites against a
  per-file last-seen-key tracker and refuses the first adjacent DESCENDING
  pair with an Err naming the shard (propagates into the WR-04 bucket abort,
  shards preserved), so no header check is trusted and unsorted/mislabeled
  inputs of any canonical mode are caught too. Equal adjacent keys stay
  legal. Proven RED->GREEN by the streaming arm of
  `mixed_canonical_prefix_cache_output_is_ascending_summed_and_queryable`
  plus unit tests (override matrix + same-mode control + descending-run
  refusal). Full suite 439/0; root + pyo3 clippy -D warnings green.

- `cargo fmt --check` fails on 4 files untouched by phase 03 (21 diff hunks:
  4x src/cli/commands/count.rs, 4x tests/merge_bounded_memory_tests.rs, 3x
  tests/merge_cleanup_tests.rs, 10x tests/parallel_count_tests.rs) — the
  03-16 full-phase fmt gate cannot pass while it stands.
  status: open
  **What:** Found during plan 03-16 Task 3's gate. The drift pattern
  (collapsing short multi-line calls, breaking long method chains) matches a
  local rustfmt style-version change rather than any phase-03 edit —
  `git log` shows zero phase-03 commits touching these files (last touches:
  26cbf36, a316e4f, f8e8355, 1e56098) and 03-15's SUMMARY records the same
  drift being scoped out then ("rustfmt applied to the two touched files",
  porcelain check on count.rs / parallel_count_tests.rs). Every 03-16
  touched file is fmt-clean (rustfmt --check per-file exits 0).
  **Suggested fix:** one `cargo fmt` commit touching exactly these 4 files
  (verify CI's rustfmt version agrees first — if CI is green on fmt, the
  local toolchain drifted and `rustup component add rustfmt@<ci-version>`
  is the fix instead).
  **How to reproduce:** `cargo fmt --check` on this tree.
