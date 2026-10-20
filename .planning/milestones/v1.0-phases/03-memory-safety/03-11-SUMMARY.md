---
phase: 03-memory-safety
plan: 11
subsystem: database
tags: [rkdb, prefix-cache-merge, temp-lifecycle, merge-integrity, wr-04, wr-08]

requires:
  - phase: 03-memory-safety plan 09
    provides: external prefix-bucket merge pipeline + temp-dir sweep lifecycle
provides:
  - A failed prefix bucket aborts the whole merge with a loud Err (WR-04) — partial .rkdb outputs are never produced
  - Failed buckets' shard files are PRESERVED on disk and their absolute paths logged — the recovery path WR-04's aggravator 1 destroyed
  - Non-tautological merge integrity accounting: merged_records_recorded (writer-emitted count) vs copied records, and non_empty_buckets_recorded vs buckets_seen (bucket phase vs concatenation)
  - concatenate_final_output copies merged buckets in fixed RECORD_SIZE * 100_000 blocks (WR-08) — peak bounded by one block, not the largest bucket
  - sweep_stale_merge_dirs reclaims loose rustkmer_sort_*/rustkmer_merge_*.chunk files older than the TTL, symlink-safe — the recorded streaming-chunk sweep gap closed
affects: [merge-error-handling, merge-memory-bounds, temp-cleanup, 04-benchmark]

actuals:
  tokens: 12128   # chars/4 over the realized diff (48510 chars across 3 files)
  tasks: 3
  commits: 3

plan_head_before: 2301ef3a45a14327ec504a2c4b0f9009d4e1bc88
plan_head_after: f8e8355f923dea8bf3cb0e427b6c42d3f5650dd8

tech-stack:
  added: []          # no new dependencies (threat T-03-SC: package gate not triggered)
  patterns:
    - "Decision-in-one-place: should_remove_shards() owns the peak-disk vs recovery trade-off so a future edit cannot re-merge them"
    - "Integrity checks whose two sides derive from DIFFERENT phases (writer-emitted count vs reader-copied count; declared bucket set vs consumed bucket set)"
    - "Fixed-block I/O with one block-size convention (RECORD_SIZE * 100_000) for both concatenation and final write"

key-files:
  created: []
  modified:
    - src/database/prefix_cache_merge.rs
    - src/database/temp_lifecycle.rs
    - tests/merge_cleanup_tests.rs

key-decisions:
  - "Partial merges now FAIL: merge_prefix_buckets returns Err when error_count > 0, naming failed/total buckets and pointing at the preserved shards — a deliberate merge-outcome behaviour change (the deferred item deferred from 03-02 precisely because it is behavioural)"
  - "should_remove_shards() is the single place deciding shard removal: success releases (D-06 peak-disk), Err and keep_intermediate preserve (WR-04 recovery)"
  - "The integrity replacement is TWO checks with distinct jobs: merged_records_recorded catches a zero-length/truncated merged bucket; non_empty_buckets_recorded vs buckets_seen catches a merged file MISSING at concatenation time. Neither side is derived from merged file sizes"
  - "The in-band check deliberately does NOT compare against the Phase-1 input total — that would require disjoint inputs and fail every ordinary overlapping merge; the input-vs-output conservation claim is a separate disjoint-inputs test"
  - "The sweep matches the writers' chunk-name prefixes via pub consts (CHUNK_FILE_PREFIXES/CHUNK_FILE_SUFFIX) rather than fresh literals, mirroring the MERGE_TEMP_PREFIX decision from 03-02"
  - "Considered and REJECTED: routing ExternalMerger's chunks into the process-unique RAII subdir would close the loose-chunk gap more thoroughly, but 03-02 deliberately scoped the subdir to the prefix-cache path and the move changes ExternalMerger::new's contract plus the nonexistent-temp_dir route probe three test binaries depend on — recorded here for a future plan with full context"

patterns-established:
  - "Pattern: prove an integrity check can fire by perturbing one operand in the source and observing the Err at the public entry point — a check never observed red is the exact defect this plan removed"
  - "Pattern: fixtures whose claimed property (disjointness, self-canonicality) is ASSERTED in the test, never assumed — overlap is computed from decoded key sets before merging"

requirements-completed: [MERGE-01, MERGE-03]

coverage:
  - id: D1
    description: "A failed prefix bucket aborts the merge with Err and its shards stay recoverable (WR-04)"
    requirement: MERGE-03
    verification:
      - kind: unit
        ref: "src/database/prefix_cache_merge.rs::tests::failed_bucket_aborts_the_merge_with_err"
        status: pass
      - kind: unit
        ref: "src/database/prefix_cache_merge.rs::tests::should_remove_shards_truth_table"
        status: pass
    human_judgment: false
  - id: D2
    description: "Successful buckets still release their shards (D-06 peak-disk optimization intact through both private and public entry points)"
    requirement: MERGE-03
    verification:
      - kind: unit
        ref: "src/database/prefix_cache_merge.rs::tests::successful_bucket_releases_its_shards"
        status: pass
      - kind: integration
        ref: "tests/merge_cleanup_tests.rs::successful_prefix_merge_releases_its_shards"
        status: pass
    human_judgment: false
  - id: D3
    description: "Non-tautological integrity accounting replacing the deleted tautology (writer-emitted count + declared-vs-seen bucket set), observed red under a deliberate off-by-one perturbation"
    requirement: MERGE-01
    verification:
      - kind: mutation
        ref: "in-band comparison perturbed to merged_records_recorded - 1: Err 'emitted 40 records but the concatenation copied 41 (9 of 256 prefix buckets declared non-empty)' propagated to RKDatabase::merge_databases and failed prefix_cache_merge_conserves_the_total_kmer_count; mutation reverted, tree verified identical"
        status: pass
    human_judgment: false
  - id: D4
    description: "concatenate_final_output copies merged buckets in fixed blocks (WR-08) — no allocation scales with the largest bucket"
    requirement: MERGE-01
    verification:
      - kind: command
        ref: "grep read_to_end(&mut buffer) over non-comment lines of prefix_cache_merge.rs prints 0; RECORD_SIZE * 100_000 block convention shared by copy and final write"
        status: pass
      - kind: command
        ref: "cargo test (full suite, 421 passed / 0 failed)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Orphan sweep reclaims stale loose chunks, leaves fresh ones, refuses symlinks and their targets"
    requirement: MERGE-03
    verification:
      - kind: integration
        ref: "tests/merge_cleanup_tests.rs::sweep_reclaims_stale_loose_chunk_files"
        status: pass
    human_judgment: false
  - id: D6
    description: "End-to-end total-k-mer conservation over DISJOINT inputs through the public merge entry point"
    requirement: MERGE-01
    verification:
      - kind: integration
        ref: "tests/merge_cleanup_tests.rs::prefix_cache_merge_conserves_the_total_kmer_count"
        status: pass
    human_judgment: false

duration: 21min
completed: 2026-10-08
status: complete
---

# Phase 03 Plan 11: Prefix-Cache Merge Integrity Plan Summary

**Failed prefix buckets now abort the merge loudly with their shards preserved and logged, the can-never-fire integrity tautology is replaced by two phase-independent conservation checks, concatenation is block-bounded (WR-08), and the orphan sweep reclaims loose streaming chunks (WR-04 + WR-08 + the recorded sweep gap).**

## Performance
- **Duration:** 21 min
- **Started:** 2026-10-08T15:07:16Z
- **Completed:** 2026-10-08T15:28:25Z
- **Tasks:** 3/3
- **Files modified:** 3 (src/database/prefix_cache_merge.rs, src/database/temp_lifecycle.rs, tests/merge_cleanup_tests.rs)

## The Behaviour Change (read this first)

**A prefix-cache merge that previously "succeeded" partially now returns `Err`.**
`merge_prefix_buckets` returns `Err` when any bucket failed, so `concatenate_final_output`
never runs on partial bucket output and `merge_databases_prefix_cache`'s `?` propagates
the error unchanged to the CLI and to PyO3 (as `PyRuntimeError` carrying the core
message). Before this plan, a failed bucket was logged and swallowed, producing a
valid-looking `.rkdb` whose `total_kmers` header reflected only the buckets that happened
to succeed — silent k-mer loss dressed up as success. deferred-items.md deferred exactly
this change from 03-02 because it is a behavioural decision; that is why it lands in this
gap-closure plan.

The failed bucket's shard files are **preserved** (not deleted) and their absolute paths
are `log::error!`ed, restoring the recovery path the D-06 failure-path deletion destroyed
(WR-04 aggravator 1). The decision lives in ONE place, `should_remove_shards(result,
keep_intermediate)` = `!keep_intermediate && result.is_ok()`.

## The Replacement Integrity Check (WR-04 aggravator 2)

The deleted check compared `total_kmers` (bytes the concatenation wrote / 20) against
`total_kmers_in_files` (`metadata().len()` of the SAME merged bucket files / 20) — a
comparison that could never differ, and could not even see a zero-length bucket (it is
`continue`d and contributes to both sides equally). Two replacements, whose sides derive
from different phases:

1. **`merged_records_recorded: AtomicU64`** on the merger — the total records the bucket
   phase's merge WRITERS emitted (`sorted_kmers.len()` in the hashmap writer, a
   per-write increment in the streaming writer), `fetch_add`ed from inside the rayon
   closure. Never derived from a merged file's size. **Catches a zero-length or truncated
   merged bucket** and any short `write_all`.
2. **`non_empty_buckets_recorded: Mutex<BTreeSet<usize>>`** (prefixes the bucket phase
   merged, inserted at the top of each closure task before any fallible work) vs
   `buckets_seen` (prefixes whose merged file the concatenation loop reached, inserted
   before the zero-length `continue`). **Catches a merged file MISSING from disk at
   concatenation time** — and only that: a zero-length file's prefix lands in BOTH sets,
   so the set check does not catch it (the count check does). Neither is redundant.

**Overlapping inputs:** the in-band check is valid for them — it compares the bucket
phase against the concatenation, and duplicate suppression inside a bucket is correct
behaviour, not loss. It deliberately does NOT compare against the Phase-1 input total,
which would require disjoint inputs and fail ordinary overlapping merges. The
input-vs-output conservation claim is the separate DISJOINT-inputs test
(`prefix_cache_merge_conserves_the_total_kmer_count`), whose docstring states the
requirement in exactly these terms.

## The Red Proof (a check never observed firing is the defect this plan removed)

The in-band comparison was temporarily perturbed to compare `total_kmers` against
`merged_records_recorded - 1`:

- **PRIMARY (in-band check observed firing):** the merge returned
  `prefix-cache merge integrity failure: the bucket phase's merge writers emitted 40
  records but the concatenation copied 41 (9 of 256 prefix buckets declared non-empty);
  a zero-length or truncated merged bucket can cause this` — the off-by-one named in the
  message.
- **SECOND witness (public entry point):** the same Err propagated through
  `RKDatabase::merge_databases` and failed
  `prefix_cache_merge_conserves_the_total_kmer_count` at its `.expect(...)`.

The mutation was then reverted; `git diff` against the Task 2 commit confirmed the source
was byte-identical again, and the full suite went back to green.

## Sweep Results (stale / fresh / symlink)

`sweep_reclaims_stale_loose_chunk_files` proves all three paths independently of the
clock (mtime driven by the file's existing `backdate()` helper, TTL driven through the
sweep's parameter):

| Case | Result |
| ---- | ------ |
| backdated `rustkmer_sort_<pid>_<micros>_0.chunk`, TTL 0 | **reclaimed** |
| fresh chunk, one-year TTL | **survives** (a live merge is never corrupted, T-03-46) |
| symlink named `rustkmer_sort_..._1.chunk` -> sentinel outside temp dir, TTL 0 | **symlink AND target both survive** (T-03-07 refusal extended to the file branch via `entry.file_type()`) |

## Bucket-Failure Test (Err message + preserved shard)

`failed_bucket_aborts_the_merge_with_err` plants a DIRECTORY at
`<subdir>/ext_sort_AAAA_file_000.tmp` (prefix 0, input 0). A directory's
`metadata().len()` is non-zero, so the bucket is selected; `File::open`/`read_to_end`
then fails with `EISDIR` — deterministic, no permissions, no race, and no dependence on
running as non-root (a root-run `chmod 000` gate would pass vacuously). Observed:

- `merge_prefix_buckets()` returns `Err` whose message contains `1 of 1` (failed out of
  total non-empty buckets) and `PRESERVED ... under '<subdir>'`.
- The shard path `<subdir>/ext_sort_AAAA_file_000.tmp` **still exists** after the call —
  the assertion distinguishing `should_remove_shards == false for Err` from a
  sweep-everything implementation.

## Accomplishments
- `should_remove_shards<T>(result, keep_intermediate)` — the one-place decision, truth-table unit tested (true only for Ok + !keep_intermediate)
- `merge_prefix_buckets` returns `Err` on `error_count > 0` via `ProcessingError::new` (propagates through `format.rs`'s `?` to CLI and PyO3)
- `merged_records_recorded` + `non_empty_buckets_recorded` fields on `ExternalSortMerger`, both updated inside the rayon closure and published onto the merger after the fan-out; merge writers return their emitted-record counts
- Tautological `total_kmers != total_kmers_in_files` check deleted with a comment explaining why it could never fire (so nobody "restores" it); `total_kmers_in_files` survives only as a diagnostic log line
- WR-08: `concatenate_final_output` copies in `RECORD_SIZE * 100_000` blocks; `data_size` accumulates bytes actually written (`n`), keeping the integrity comparison and `file_size` header truthful
- `merge_single_prefix_hashmap`'s shard reader also converted to fixed-block carry-remainder decoding (see Deviations)
- `sweep_stale_merge_dirs` file branch: loose `rustkmer_sort_*`/`rustkmer_merge_*` `.chunk` files, TTL-gated on mtime, symlink-refusing, with a reclamation-count `log::info!`; the directory branch is untouched
- `CHUNK_FILE_PREFIXES` / `CHUNK_FILE_SUFFIX` pub consts mirror `TempFileManager::create_temp_file`'s naming so sweep and writers cannot drift
- 3 new integration tests + 3 new unit tests; `grep`-criteria and full-suite gates all green

## Task Commits
1. **Task 1: A failed bucket aborts the merge, and its shards stay recoverable** - `ee4b336` (fix, tracer verified end-to-end)
2. **Task 2: Concatenate buckets in blocks, and teach the orphan sweep about loose chunks** - `83a6ac2` (feat)
3. **Task 3: Three tests that can actually catch what the removed checks could not** - `f8e8355` (test)

**Plan metadata:** base `2301ef3` -> head `f8e8355` (3 commits, measured via the plan ledger)

## Files Created/Modified
- `src/database/prefix_cache_merge.rs` - shard-preservation decision, Err-on-failure, integrity accounting fields + checks, block-copy concatenation, block-decode shard reader, 3 new unit tests
- `src/database/temp_lifecycle.rs` - loose-chunk sweep branch + chunk-name pub consts
- `tests/merge_cleanup_tests.rs` - conservation test (disjoint fixtures, asserted), loose-chunk sweep test, public-entry-point shard-release test, `encode_dna` helper

## Decisions Made
See key-decisions in the frontmatter. The rejected alternative deserves the full record:

**Routing `ExternalMerger`'s chunks into the process-unique RAII subdir would close the
loose-chunk gap more thoroughly** (they would be reclaimed with the directory). NOT
taken: 03-02 deliberately scoped the subdir to the prefix-cache path, and moving the
streaming chunks changes `ExternalMerger::new(chunk_size, temp_dir)`'s contract and the
nonexistent-`temp_dir` route probe that three test binaries depend on. A future plan can
pick this up with full context; until then the TTL sweep is the defense for
abort/SIGKILL'd streaming merges.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - clippy gate] `op_ref` on the set-equality comparison**
- **Found during:** Task 1 verification (`cargo clippy --all-targets -- -D warnings`)
- **Issue:** The plan's snippet wrote `if &buckets_seen != &*declared`; the toolchain's clippy (1.99) denies `clippy::op_ref` for that shape, failing the plan's own blocking clippy criterion.
- **Fix:** Applied clippy's suggestion verbatim: `if buckets_seen != *declared` (auto-borrowed comparison, identical semantics).
- **Files modified:** src/database/prefix_cache_merge.rs
- **Commit:** ee4b336 (folded into Task 1 before its commit)

**2. [Rule 3 - blocking acceptance criterion] `read_to_end(&mut buffer)` grep counts the hashmap shard reader too**
- **Found during:** Task 2 acceptance-criteria loop
- **Issue:** The criterion `grep -vE '^\s*//' ... | grep -c 'read_to_end(&mut buffer)' == 0` matches TWO pre-plan sites: `concatenate_final_output`'s merged-bucket read (WR-08's actual target, replaced per the plan) AND `merge_single_prefix_hashmap`'s per-bucket input-shard reader at old :562, which the plan's Part A prose never mentions (its read_first scopes Task 2 to :825-860/:900-935).
- **Fix:** Converted the shard reader to the same fixed-block (`RECORD_SIZE * 100_000`) carry-remainder decode loop. Behaviour-preserving: identical records decoded, trailing sub-record bytes ignored exactly as before; only the transient buffer stops scaling with the shard's size. Satisfies the criterion honestly rather than by renaming a variable.
- **Files modified:** src/database/prefix_cache_merge.rs
- **Verification:** full suite green (the hashmap writer is the default per-bucket strategy on every existing merge test).
- **Commit:** 83a6ac2

**3. [Plan-text reconciliation] `should_remove_shards` generic over the success type**
- The plan specifies the signature `fn should_remove_shards(result: &Result<(), anyhow::Error>, ...)` AND mandates the merge writers return `Result<u64, anyhow::Error>` (the emitted-record count). The two clauses conflict; the fn is generic `<T>` so it decides on `is_ok()` for any success type. The truth-table test calls it with `Ok::<u64, _>`/`Err` pairs covering all four rows.

**4. [Plan-text imprecision, implemented per the correctness requirement] `data_size` accumulates `n`, not `block.len()`**
- Part A says "add `block.len() as u64` to `data_size` on `Ok(n)`" but also "`data_size` must accumulate from the bytes ACTUALLY written, which is what the integrity comparison and the `file_size` header field are derived from". On the final partial read `n < block.len()`, so `block.len()` would overcount and corrupt the header. Implemented as `temp_file.write_all(&block[..n])?; data_size += n as u64;` — the correctness requirement governs.

**Total deviations:** 4 (2 auto-fixed against gates, 2 plan-text reconciliations). **Impact:** none semantic beyond the plan's own intended behaviour change; all gates green.

## Issues Encountered
None beyond the deviations above.

## Authentication Gates
None — no external services involved.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None — no stubs, no skipped tests, no unrun verifies. (Pre-existing pyo3 maturin/pytest blockers are carried in WINDOWS.md from 03-10 and are untouched by this plan.)

## Next Phase Readiness
- Phase 03 execution complete (11/11 plans). WR-04 and WR-08 are closed; the streaming-chunk sweep gap is closed.
- The prefix-cache route now fails loudly on partial merges — any caller-visible documentation of merge semantics should mention it.
- Carried forward (unchanged, recorded in deferred-items.md / WINDOWS.md): pyo3 maturin `python-source` pairing + `--cov-fail-under` addopts; `cargo fmt` drift in two files; the dense-width deferral to the in-memory merge accumulator.
- "Phase complete, ready for verification."

## Self-Check: PASSED
