---
phase: 03-memory-safety
plan: 17
subsystem: database
tags: [prefix-cache, external-sort, mixed-canonical, streaming-writer, sorted-flag, binary-search, rkdb]

# Dependency graph
requires:
  - phase: 03-memory-safety (03-16)
    provides: the canonicalized shard writes (bucket key == stored key) and the mixed-canonical e2e fixture/oracle this plan's streaming arm reuses
  - phase: 03-memory-safety (03-13)
    provides: both per-bucket merge writers whose writer contracts this plan enforces
provides:
  - 03-VERIFICATION round-3 gaps[0] closed on all three missing items — truth 10's last open subset (the per-bucket streaming writer) holds: mixed-canonical prefix-cache merges are ascending, summed, and exactly queryable under a truthful sorted header on BOTH bucket writers (10/11 -> 11/11)
  - ExternalSortMerger::new's mixed-canonical bucket-writer override (forced "memory" + log::warn; same-mode merges untouched)
  - merge_single_prefix_streaming's record-level descending-run refusal at both pop_front consumption sites (WR-04-preserving Err; equal adjacent keys legal)
  - The merge_mode='streaming' arm of mixed_canonical_prefix_cache_output_is_ascending_summed_and_queryable (RED->GREEN) and the parameterized prefix_cache_config helper
  - Both known-false writer-contract comments corrected with negative-grep proof
affects: [prefix-cache merge route, query paths trusting header.sorted, MERGE-01, DENSE-02, WINDOWS #17]

actuals:
  tokens: 6521    # chars/4 over the realized diff (26,084 chars across the 2 source files)
  tasks: 3
  commits: 4      # MEASURED: git rev-list --count d688d8b..HEAD (plus this docs commit)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hold-by-construction or refuse-loudly: when a writer's precondition cannot be verified from headers (which are claims, not properties), either force a writer whose correctness is order-independent, or validate the records at every consumption site and abort"
    "Two-site consumption validation: every record leaving a shard buffer is checked exactly once (the heap entry mirrors its file's buffer front at the top-pop; the run-adjacent duplicate pop is the only other exit) — validating at both sites covers any caller, including ones that bypass header-keyed gates"

key-files:
  created: []
  modified:
    - src/database/prefix_cache_merge.rs
    - tests/prefix_cache_output_order_tests.rs
    - .planning/WINDOWS.md
    - .planning/phases/03-memory-safety/deferred-items.md

key-decisions:
  - "Option (a)+(b) over the plan's option (c): forcing the sorting (hashmap) writer for mixed-canonical header sets in ExternalSortMerger::new is the only option that keeps a merge_mode='streaming' merge SUCCEEDING (correctly, via the override) instead of erroring; (c) per-shard sorting was rejected for doubling phase-1 IO. Option (b) — per-file run validation refusing the first adjacent descending pair at BOTH pop_front sites — is the backstop for inputs no header check can gate, since headers are unverified claims"
  - "The refusal reads RECORDS, not headers: a lying sorted:true header or an unsorted input of ANY canonical mode still cannot smuggle a descending run past the writer, including direct callers that bypass the header-keyed override; equal adjacent keys (duplicate runs) stay legal via the strictly-less-than-only check"
  - "T-03-57 accepted (with rationale, logged): forcing the in-memory per-bucket writer on mixed-canonical merges trades the streaming writer's bounded footprint for correctness on that corner — per-bucket scope (one 4-prefix, ~1/256 of the data), the hashmap writer's own available-memory warning still fires, and the override is loudly logged"
  - "The refusal unit test drives merge_single_prefix_streaming DIRECTLY (raw shard, no headers) so it stays RED on the post-override tree — proving the two fixes are independent layers, not one"
  - "WINDOWS.md frontmatter counts were repaired to the true entry census (10/3/5/18; they had drifted to 11/19) before running `windows fixed` — the CLI recomputes and refuses to operate on a disagreeing ledger"

patterns-established:
  - "RED-prove each layer independently: the e2e arm proves the override's behavior through the public API; the direct-call unit test proves the record-level refusal does not depend on it"

requirements-completed: [MERGE-01, DENSE-02]

coverage:
  - id: D1
    description: "The merge_mode='streaming' arm of the mixed-canonical e2e proof: same fixture through merge_databases_to_path, asserting windows(2) strict global ascending under sorted:true, decode_observations == oracle (meet-and-sum key 0x000000 ONE summed record 8), total_kmers == oracle.len(), first/last == oracle min/max, per-oracle-key query_kmer through binary search, asserted-absent negative, canonical:true ANY-input header"
    requirement: MERGE-01
    verification:
      - kind: integration
        ref: "tests/prefix_cache_output_order_tests.rs#mixed_canonical_prefix_cache_output_is_ascending_summed_and_queryable (3/3 in binary; RED on the unfixed tree at the order assertion)"
        status: pass
    human_judgment: false
  - id: D2
    description: "ExternalSortMerger::new's mixed-canonical override: mixed headers requested as 'streaming'/'auto' -> merger.merge_mode == 'memory' (log::warn, route unchanged); explicit 'memory' idempotent; same-mode control keeps 'streaming'"
    requirement: MERGE-01
    verification:
      - kind: unit
        ref: "cargo test --lib prefix_cache_merge — mixed_canonical_inputs_force_the_sorting_bucket_writer / _requested_as_memory_stay_memory / same_mode_inputs_keep_the_requested_streaming_writer"
        status: pass
      - kind: integration
        ref: "cargo test --test prefix_cache_conservation_tests (2/2 — same-mode streaming fixtures NOT diverted by the override)"
        status: pass
    human_judgment: false
  - id: D3
    description: "merge_single_prefix_streaming refuses a shard with an adjacent descending pair: Err naming the shard path, both keys in hex, and the non-decreasing-run requirement; equal adjacent keys stay legal (dup-run + conservation tests green)"
    requirement: MERGE-01
    verification:
      - kind: unit
        ref: "cargo test --lib prefix_cache_merge::tests::streaming_writer_refuses_a_descending_run (RED on the post-override tree: Ok(2) -> GREEN Err)"
        status: pass
      - kind: unit
        ref: "merge_single_prefix_streaming_conserves_records_across_batch_boundaries + _two_files_strand_nothing_and_dedupe_across_files (adjacent duplicates legal)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Both known-false writer-contract comments corrected (prefix_cache_merge.rs split_files_by_prefix block; tests/prefix_cache_output_order_tests.rs helper): the hashmap writer's fold-and-sort, the forced override, and the streaming writer's non-decreasing-run requirement named"
    verification:
      - kind: other
        ref: "negative gates: grep -c 'every bucket writer emits ascending' tests/prefix_cache_output_order_tests.rs == 0; grep -c 'the bucket writers sum' src/database/prefix_cache_merge.rs == 0"
        status: pass
    human_judgment: false
  - id: D5
    description: "Full-phase gate: complete cargo test 439 passed / 0 failed across 23 result lines (baseline 435 + 4 new tests); root and pyo3 clippy --all-targets -D warnings green; per-file rustfmt --check clean on both touched files"
    verification:
      - kind: other
        ref: "cargo test (439/0, 23 result lines all ok); clippy root+pyo3 exit 0; rustfmt --check both files exit 0"
        status: pass
    human_judgment: false
  - id: D6
    description: "Records closed: WINDOWS.md entry 17 status fixed with the 03-17 closure note; deferred-items.md merge_single_prefix_streaming entry status closed with the closed-by note"
    verification:
      - kind: other
        ref: ".planning/WINDOWS.md line 34 (status fixed, reason populated, resolved_at set; ledger 9 open/6 fixed/18 total) + deferred-items.md status: closed"
        status: pass
    human_judgment: false

# Metrics
duration: 16min
completed: 2026-10-09
status: complete
plan_head_before: d688d8b0fc0e65a7ac84519caaac992cf7d3caa9
plan_head_after: 62f7c47
---

# Phase 03 Plan 17: Streaming-Writer Arm of Truth 10 (gaps[0]) Summary

**Mixed-canonical prefix-cache merges are now ascending, summed, and exactly queryable on BOTH per-bucket writers: ExternalSortMerger::new forces the sorting (hashmap) writer for mixed-canonical header sets and merge_single_prefix_streaming refuses descending runs at record level — RED-proven on both layers, full suite 439/0.**

## Performance

- **Duration:** ~16 min
- **Started:** 2026-10-09T11:47:14Z
- **Completed:** 2026-10-09T12:02:51Z
- **Tasks:** 3
- **Files modified:** 4 (2 source, 2 planning records)

## Accomplishments

- **03-VERIFICATION round-3 gaps[0] closed on all three missing items.** The mixed-canonical capability's last broken subset — the per-bucket STREAMING writer (`merge_mode='streaming'`, or auto over the per-bucket threshold) — now holds the full ordering/summing/queryability guarantee: truth 10's 10/11 becomes 11/11.
- **Option (a), the override:** `ExternalSortMerger::new` detects the canonical-mode mixture (folded canonical true + any input header non-canonical) and stores `"memory"` as the merger's merge_mode in place of the requested one, with a `log::warn!` naming the counts, the ascending-run reason, and the route-unchanged scope. An explicit `"memory"` request stays silent; same-mode sets are untouched (control test + 03-13 conservation binary prove it).
- **Option (b), the refusal backstop:** `merge_single_prefix_streaming` tracks a per-file last-seen key and validates every record at BOTH `pop_front` consumption sites; a strictly descending adjacent pair returns `Err` naming the shard path and both keys in hex with the non-decreasing-run requirement. It propagates into the WR-04 bucket abort (shards preserved, no header written); equal adjacent keys stay legal.
- **Both known-false comments corrected** (the split_files_by_prefix meet-and-sum sentence; the test helper's every-writer-ascending claim), each gated by a negative grep now returning 0.
- **Records closed:** WINDOWS.md #17 flipped to fixed with the 03-17 closure note; deferred-items.md's merge_single_prefix_streaming entry flipped to closed with the closed-by note.

## Red Evidence (recorded against the pre-fix trees, before each fix landed)

1. **Task 1 — the streaming arm on the unfixed tree** (commit 3dbe18f; run before the fix commit 43037f0):

   ```
   running 3 tests
   test prefix_cache_output_is_globally_sorted_and_queries_correctly ... ok
   test prefix_cache_answers_match_the_inmemory_route ... ok
   test mixed_canonical_prefix_cache_output_is_ascending_summed_and_queryable ... FAILED

   ---- mixed_canonical_prefix_cache_output_is_ascending_summed_and_queryable stdout ----

   thread 'mixed_canonical_prefix_cache_output_is_ascending_summed_and_queryable' panicked at tests/prefix_cache_output_order_tests.rs:596:5:
   streaming-mode mixed-canonical prefix-cache output must be globally ascending by encoded u128

   test result: FAILED. 2 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out
   ```

   (The reproduced corruption the round-3 verifier documented: key 0x000000 emitted twice at the head and mid-vector, un-summed 5+3, total 11 vs the oracle's 10, query Some(5) vs Some(8). The panic fires at the arm's FIRST assertion — the order check — which is the plan's stated RED expectation; the auto/hashmap assertions above it in the same test still held.)

2. **Task 3 — the refusal test on the post-Task-2 tree** (direct call, bypassing the header-keyed override; run before the fix commit 2fd1cb0):

   ```
   ---- database::prefix_cache_merge::tests::streaming_writer_refuses_a_descending_run stdout ----

   thread 'database::prefix_cache_merge::tests::streaming_writer_refuses_a_descending_run' panicked at src/database/prefix_cache_merge.rs:1920:26:
   a descending run must be refused, not merged: 2

   test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 235 filtered out
   ```

   (Pre-fix behavior: the writer returned `Ok(2)` — two misordered records emitted — on a shard descending 0x000200 -> 0x000100. This RED also proves the two fixes are independent layers: the override keys on headers, the direct call has none.)

## Task Commits

Each task was committed atomically:

1. **Task 1: RED proof — the streaming arm of the mixed-canonical test + parameterized helper + corrected comments** - `3dbe18f` (test)
2. **Task 2: option (a) — mixed-canonical override in ExternalSortMerger::new + unit tests + corrected source comment** - `43037f0` (fix)
3. **Task 3: option (b) — descending-run refusal in merge_single_prefix_streaming + refusal unit test** - `2fd1cb0` (fix)
4. **Task 3: records closed (WINDOWS #17 fixed, deferred-items closed)** - `62f7c47` (docs)

**Plan metadata:** this SUMMARY's docs commit follows immediately (see `plan_head_after` for the last production commit).

## Files Created/Modified

- `src/database/prefix_cache_merge.rs` — (1) `ExternalSortMerger::new`: mixed-canonical detection + forced `"memory"` merge_mode with `log::warn` (option a); (2) `merge_single_prefix_streaming`: per-file `last_key_per_file` tracker + `descending_run_err` closure + validation at both `pop_front` sites (option b); (3) the CR-01 comment block rewritten into the real two-writer contract; (4) three override unit tests + one refusal unit test in the `tests` mod.
- `tests/prefix_cache_output_order_tests.rs` — `prefix_cache_config` gains a `merge_mode: &str` parameter (three existing call sites pass `"auto"`); the streaming arm inside `mixed_canonical_prefix_cache_output_is_ascending_summed_and_queryable`; corrected helper doc + module-doc fourth proof.
- `.planning/WINDOWS.md` — entry 17 fixed with the 03-17 closure note; frontmatter counts repaired to the true census.
- `.planning/phases/03-memory-safety/deferred-items.md` — merge_single_prefix_streaming entry closed with the closed-by note.

## Decisions Made

- **Option (a)+(b), not (c):** forcing the sorting writer keeps `merge_mode='streaming'` merges SUCCEEDING (correctly) instead of erroring; per-shard sorting (c) was rejected for doubling phase-1 IO with no better worst-case footprint than the hashmap writer it substitutes. The refusal backstop exists because headers are claims, not verified properties — (a) alone cannot gate unsorted or mislabeled inputs of any canonical mode.
- **Refusal reads records at both consumption sites:** a heap entry mirrors its file's buffer front (so `top.kmer` at the heap-top pop IS the popped record's key) and the run-adjacent duplicate pop is the only other buffer exit — validating there checks every record exactly once, for any caller.
- **Strictly-less-than only:** equal adjacent keys (duplicate runs) must stay legal — the 03-13 dup-run unit tests and the conservation binary pin that.
- **No pyo3 edits, no pytest attempted:** the pyo3 surface inherits both changes through `merge_databases_to_path` via the path dependency (MERGE-04 by inheritance); the STATE.md maturin/pytest blocker stands unchanged.
- **D-03 untouched:** the commits touch only the two listed source files plus the two .planning records (git-verified); `src/database/format.rs` has zero diff; golden_sha256_tests green.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] E0382 borrow-of-moved-value in the extended test**
- **Found during:** Task 1 (first compile of the streaming arm)
- **Issue:** the test's first merge call moves `a_path`/`b_path` into its array argument; the streaming arm then needs them again (the same shape as 03-16 deviation #3).
- **Fix:** `&[a_path.clone(), b_path.clone()]` in the first call, commented; the streaming arm uses the owned originals.
- **Files modified:** tests/prefix_cache_output_order_tests.rs
- **Verification:** binary compiles; RED run reproduces.
- **Committed in:** 3dbe18f

**2. [Rule 1 - Bug] acceptance grep tripped by the corrected comment quoting the false phrase**
- **Found during:** Task 1 (acceptance gate)
- **Issue:** the rewritten helper doc quoted "every bucket writer emits ascending" verbatim inside its correction note, so the negative gate `grep -c` returned 1 (must be 0) — 03-16 deviation #4's exact trap.
- **Fix:** reworded to "each bucket writer emits ascending output" (no substring match); meaning unchanged.
- **Files modified:** tests/prefix_cache_output_order_tests.rs
- **Verification:** grep count 0.
- **Committed in:** 3dbe18f

**3. [Rule 3 - Blocking] pre-existing WINDOWS.md frontmatter drift blocked `windows fixed 17`**
- **Found during:** Task 3 (record closing)
- **Issue:** the ledger frontmatter claimed 11 open / 19 total but the 18 entries yield 10/3/5 — the CLI recomputes and refuses to operate on a disagreeing ledger (pre-existing: written by 03-16's append round).
- **Fix:** repaired the counts to the true census (10/3/5/18), then ran `windows fixed 17` (now 9 open / 6 fixed); the CLI left the reason field empty, so the 03-17 closure note was written into both the table row and the JSON entry, mirroring how entries 7/10 record closure.
- **Files modified:** .planning/WINDOWS.md
- **Verification:** `gsd-tools windows status` reports ok, 9/3/6/18.
- **Committed in:** 62f7c47

---

**Total deviations:** 3 auto-fixed (2x Rule 3, 1x Rule 1)
**Impact on plan:** All fixes mechanical or record-keeping; no scope creep. Two measurement notes, not code deviations: the plan's Task 1 baseline for `grep -ci "refus"` said 1 but the true pre-plan count was 0 (post-plan 13, still >= 2); Task 1's RED run was executed immediately before its commit rather than after (same unfixed tree, same output — the RED still precedes both fix commits, which is the discipline the convention exists to enforce).

## Issues Encountered

None beyond the deviations above. (Carried, unchanged: repo-wide `cargo fmt --check` drift on 4 phase-untouched files — WINDOWS.md #18, out of scope; the per-file rustfmt gate the plan prescribes passed on both touched files.)

## Tracer Feedback Gate (Task 1, auto mode)

Auto mode is active (`workflow.auto_advance: true`). The gate's precedence chain: the task carries no `gate="blocking-human"`; auto mode re-runs the tracer `<verify>` end-to-end — the run FAILED at the streaming arm's order assertion, which for this `tdd="true"` tracer IS the designed deliverable (the plan's own `<fails_when>` declares a GREEN run the failure condition: it would mean the arm does not discriminate). The slice is RED for the commissioned reason and Task 2 is the in-plan GREEN step, so expansion proceeded: "Tracer RED verified — expanding to the fix."

## Prohibitions Verified

- Streaming arm order/content gates: `cargo test --test prefix_cache_output_order_tests` 3/3 — windows(2) strict ascending on BOTH the auto/hashmap arm and the streaming arm; `decode_observations == oracle` and `header.total_kmers == oracle.len()` in the streaming arm (no un-summed duplicates, no over-merge — exact BTreeMap equality).
- Record-level refusal: `streaming_writer_refuses_a_descending_run` asserts the Err and its message (shard path + both hex keys + non-decreasing requirement).
- Header-independence: the refusal unit test calls the writer directly with a raw shard (no headers exist to consult); the override keys on the canonical-mode mixture, not on header.sorted claims.
- D-03 on-disk format: zero edits outside the two listed source files + two .planning records (`git diff --name-only d688d8b..HEAD`); `src/database/format.rs` diff empty; golden_sha256_tests 5/5 green.
- Query path untouched: zero format.rs edits; query correctness proven through the unchanged consumer on the fixed output (per-oracle-key binary-search answers + negative).
- Same-mode streaming preserved: control unit test + prefix_cache_conservation_tests 2/2 (streaming-pinned fixtures).

## Verification Results

1. RED (pre-fix): Task 1 streaming arm FAILED at the order assertion (evidence above); Task 3 refusal test FAILED with `Ok(2)` (evidence above).
2. GREEN (post-fix): `cargo test --test prefix_cache_output_order_tests` 3 passed / 0 failed; `cargo test --lib prefix_cache_merge` 12 passed / 0 failed (8 baseline + 4 new); `cargo test --test prefix_cache_conservation_tests` 2 passed / 0 failed.
3. Full gate: complete `cargo test` 439 passed / 0 failed across 23 result lines (baseline 435 + 4 new unit/integration tests); root `cargo clippy --all-targets -- -D warnings` exit 0; pyo3 `cargo clippy --manifest-path pyo3/Cargo.toml --all-targets -- -D warnings` exit 0; `rustfmt --check` clean on both touched files.
4. Negative gates: `grep -c "every bucket writer emits ascending" tests/prefix_cache_output_order_tests.rs` == 0; `grep -c "the bucket writers sum" src/database/prefix_cache_merge.rs` == 0 (baselines 1 each, verified pre-plan).
5. Acceptance greps: windows(2) count 4 (baseline 3); `prefix_cache_config(work.path(), "streaming")` count 1; first()/last() count 2 (baseline 0); `mixed-canonical` (ci) count 10 (baseline 1); `fn mixed_canonical` 2 + same-mode control 1; `refus` (ci) 13; `non-decreasing|ascending run` 8.

## User Setup Required

None - no external service configuration required. (Carried note: Python-level verification remains blocked in-repo by the STATE.md maturin/pytest blocker; both fixes reach the pyo3 surface through the path dependency with zero pyo3 edits.)

## Next Phase Readiness

- 03-VERIFICATION round-3 gaps[0] is fully closed: the stored-key ordering guarantee holds for every writer (forced hashmap for the header-detectable mixture, loud refusal for record-level violations), the streaming arm of the mixed-canonical e2e proof exists and is green, and both known-false comments are corrected with negative-grep proof.
- Truth 10 holds on its last open subset — the phase's 10/11 becomes 11/11 pending the next verification round.
- Records: WINDOWS.md #17 closed (ledger 9 open / 6 fixed / 18 total); deferred-items merge_single_prefix_streaming entry closed. Carried open items unchanged: the pre-existing fmt drift (#18), the maturin/pytest blocker (entries 4/5/11), and the advisory WR/IN rows from 03-REVIEW-DISPOSITION.md.

---
*Phase: 03-memory-safety*
*Completed: 2026-10-09*

## Self-Check: PASSED
