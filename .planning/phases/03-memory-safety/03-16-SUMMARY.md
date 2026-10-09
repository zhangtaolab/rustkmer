---
phase: 03-memory-safety
plan: 16
subsystem: database
tags: [prefix-cache, external-sort, mixed-canonical, canonicalization, sorted-flag, binary-search, rkdb]

# Dependency graph
requires:
  - phase: 03-memory-safety (03-15)
    provides: first-4-bases (high-byte) bucketing making index-order concatenation ascending for same-mode merges (CR-02), the output-order test binary and its helpers
  - phase: 03-memory-safety (03-13)
    provides: per-bucket streaming/hashmap merge writers that sum duplicate keys within a bucket, conservation test binary
provides:
  - The CR-01/WR-03 one-site fix — split_files_by_prefix stores the canonicalized processed_kmer (bucket key == sort key == stored key) and propagates canonicalization errors via `?` instead of the swallowed fallback
  - A RED-provable mixed-canonical end-to-end proof: globally ascending output, raw+canonical encodings of one k-mer summed per an input-only canonicalizing oracle, exact query_kmer answers, ANY-input canonical header (input[0] NON-canonical)
  - The routing tests' ANY-input header pin in BOTH input orders (reversed order added), replacing the misdescribed input[0]-mode comment
affects: [prefix-cache merge route, query paths trusting header.sorted, MERGE-01, DENSE-02, WR-04 mixed-canonical capability]

actuals:
  tokens: 4319     # chars/4 over the realized diff (17,277 chars across 3 files)
  tasks: 3
  commits: 4       # MEASURED: git rev-list --count a212253..HEAD (plus this docs commit)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fixture honesty guards call the production canonicalizer and assert (never comment) that the fixture discriminates — B keys canonical, >=1 A key whose canonical HIGH BYTE differs, meet-and-sum pair folds to one oracle entry"
    - "A k=16 literal discipline: 24-bit hex literals have high byte 0x00; any fixture keyed on 'first 4 bases' or canonical-form bucketing must use full-width literals (0xFFFF_FFFF for all-T, 0x0100_0000 for a real bucket-0x01 key)"

key-files:
  created: []
  modified:
    - src/database/prefix_cache_merge.rs
    - tests/prefix_cache_output_order_tests.rs
    - tests/merge_routing_tests.rs

key-decisions:
  - "The fix is exactly one site: the shard stores processed_kmer (the value get_prefix_4mer bucketed by) and canonicalization errors propagate via ?; get_prefix_4mer, both bucket merge writers, and the concatenate_final_output header write are untouched — under the fix their labels become truthful for mixed-canonical input"
  - "The plan's all-T literal 0xFFFFFF is a 24-bit key at k=16 whose canonical form is 0x0000FF, not 0x000000; the behavior block's intent (all-T, canonical form 0x000000, meet-and-sum with B's 0x000000) requires the full-width 0xFFFFFFFF — the same k=16 literal trap 03-15 documented for 0x010000"
  - "The fixture was strengthened with a true-high-byte key (0x0100_0000, bucket 0x01) per the plan's own fails_when discipline: with only 24-bit literals every record collapses into bucket 0x00, the hashmap writer's within-bucket sort erases the misplacement, and windows(2) passes pre-fix — only the conservation axis discriminates; with bucket 0x01 non-empty the raw all-T key's misplacement is an ORDER violation too (observed pair 0xffffffff -> 0x1000000)"
  - "KNOWN RESIDUAL (deferred, Rule 4 scale): merge_single_prefix_streaming heap-merges assuming each shard is an ascending run; post-fix a non-canonical input's shard (canonical values in raw-stream order) can be non-ascending, so mixed-canonical correctness is proven on the auto/hashmap path only — the plan explicitly froze both bucket writers; logged in deferred-items.md + WINDOWS.md #17"
  - "cargo fmt --check fails on 21 pre-existing hunks in 4 files no phase-03 plan touched (rustfmt version drift; 03-15 saw the same and scoped formatting to touched files); every 03-16 touched file is fmt-clean — logged in deferred-items.md + WINDOWS.md #18"

patterns-established:
  - "RED-prove BOTH defect axes with one fixture by ensuring a later bucket exists — an order violation needs a concatenation boundary to cross"
  - "Probe before assuming: a throwaway keep_intermediate dump of the shard files showed every record in bucket 0x00 and settled in minutes what hand-tracing got wrong twice"

requirements-completed: [MERGE-01, DENSE-02]

coverage:
  - id: D1
    description: "A RED-provable mixed-canonical end-to-end test: globally ascending output (windows(2)), truthful sorted flag, content equal to the input-only canonicalizing oracle (raw all-T + canonical 0x000000 summed to one record), header.total_kmers == oracle.len(), per-oracle-key query_kmer through binary search, one asserted-absent negative query, canonical:true header with input[0] NON-canonical"
    requirement: MERGE-01
    verification:
      - kind: integration
        ref: "tests/prefix_cache_output_order_tests.rs#mixed_canonical_prefix_cache_output_is_ascending_summed_and_queryable"
        status: pass
    human_judgment: false
  - id: D2
    description: "The one-site fix: split_files_by_prefix stores the canonicalized processed_kmer (bucket key == stored key) and propagates canonicalization errors via ? (unwrap_or(entry.kmer) gone, grep count 0)"
    requirement: MERGE-01
    verification:
      - kind: unit
        ref: "cargo test --lib prefix_cache_merge (8 passed) — includes the 03-15 bucketing unit tests"
        status: pass
      - kind: integration
        ref: "cargo test --test prefix_cache_output_order_tests (3 passed) + cargo test --test prefix_cache_conservation_tests (2 passed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "ANY-input canonical header semantics pinned non-coincidentally in the routing tests: corrected comment plus a reversed-input-order merge (input[0] NON-canonical) asserting canonical == true; the inaccurate input[0]-mode claim is gone (grep count 0)"
    requirement: DENSE-02
    verification:
      - kind: integration
        ref: "tests/merge_routing_tests.rs#prefix_cache_route_still_merges_mixed_canonical (37/37 in binary)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Full-phase regression gate: complete cargo test (23 result lines, 435 passed / 0 failed = baseline 434 + 1 new), root clippy -D warnings green, pyo3 clippy -D warnings green, cargo fmt --check"
    verification:
      - kind: other
        ref: "cargo test (435 passed, 0 failed, all result lines ok)"
        status: pass
      - kind: other
        ref: "cargo clippy --all-targets -- -D warnings (root) and --manifest-path pyo3/Cargo.toml (both exit 0)"
        status: pass
      - kind: other
        ref: "cargo fmt --check (exit 1: 21 hunks in 4 files untouched by any phase-03 plan — pre-existing rustfmt drift, WINDOWS.md #18; all 03-16 touched files fmt-clean)"
        status: fail
    human_judgment: true
    rationale: "The fmt sub-gate cannot pass without reformatting 4 files outside this plan's scope (pre-existing drift, verified pre-dating the session via git log); a human decides whether to reformat or pin the toolchain version."

# Metrics
duration: 27min
completed: 2026-10-09
status: complete
plan_head_before: a212253b9e7bfa0104786711f3c422faf43abf2c
plan_head_after: 9cd7795
---

# Phase 03 Plan 16: Mixed-Canonical Prefix-Cache Correctness (CR-01/WR-03) Summary

**The one-site CR-01/WR-03 fix — split_files_by_prefix stores the canonicalized bucket key and propagates canonicalization errors — makes mixed-canonical prefix-cache merges globally ascending, content-summed, and correctly queryable under a truthful header, RED-proven on both defect axes before the fix landed.**

## Performance

- **Duration:** ~27 min
- **Started:** 2026-10-09T04:57:15Z
- **Completed:** 2026-10-09T05:24:44Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- **CR-01 / open WR-03 closed on the auto/hashmap path (03-VERIFICATION.md human decision item 1, user triage 2026-10-09):** `split_files_by_prefix` (src/database/prefix_cache_merge.rs) now writes `processed_kmer` — the identical value `get_prefix_4mer` bucketed the record by — so bucket key == sort key == stored key. Index-order concatenation is globally ascending for mixed-canonical input (CR-02's construction argument extended), the raw and canonical encodings of one k-mer meet in one bucket and are SUMMED by the bucket writer, and the swallowed-error fallback is replaced with `?` propagation (T-03-53/T-03-54 mitigated).
- **Both defect axes RED-proven before the fix:** the new test failed on the unfixed tree at the ORDER assertion (violation pair `0xffffffff -> 0x1000000` at the bucket-0x00/bucket-0x01 boundary) and at the CONSERVATION assertion (un-summed `0xFFFFFFFF: 3` + `0x000000: 5` where the oracle holds one summed `0x000000: 8`). Post-fix GREEN with exact query answers and a truthful ANY-input canonical header.
- **Routing tests corrected and strengthened:** the misdescribed input[0]-mode comment is rewritten to the actual ANY-input semantics, and a reversed-input-order merge (`[b, a]`, input[0] NON-canonical) now pins `canonical: true` — the order under which the old claim was false (T-03-55).
- **Full-phase gate green on tests and both clippy crates:** 435 passed / 0 failed (baseline 434 + the 1 new test), `merge_routing_tests` 37/37, root and pyo3 `clippy --all-targets -- -D warnings` both clean.

## Red Evidence (recorded against the pre-fix tree, before the fix landed)

1. **Order axis** (after the fixture strengthening, commit 90c4285; run before the fix commit a347b61):

   ```
   running 3 tests
   test prefix_cache_output_is_globally_sorted_and_queries_correctly ... ok
   test mixed_canonical_prefix_cache_output_is_ascending_summed_and_queryable ... FAILED
   test prefix_cache_answers_match_the_inmemory_route ... ok

   ---- mixed_canonical_prefix_cache_output_is_ascending_summed_and_queryable stdout ----

   thread 'mixed_canonical_prefix_cache_output_is_ascending_summed_and_queryable' panicked at tests/prefix_cache_output_order_tests.rs:483:5:
   mixed-canonical prefix-cache output must be globally ascending by encoded u128

   test result: FAILED. 2 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out
   ```

   (Mechanism confirmed by a keep_intermediate shard dump: the raw all-T key was bucketed into bucket 0x00 by its canonical form 0x000000 but WRITTEN raw as 0xFFFFFFFF — sorted last inside bucket 0x00, emitted ahead of bucket 0x01's 0x0100_0000.)

2. **Conservation axis** (first RED run, commit b0b4189, before the strengthening):

   ```
   thread 'mixed_canonical_prefix_cache_output_is_ascending_summed_and_queryable' panicked at tests/prefix_cache_output_order_tests.rs:485:5:
   assertion `left == right` failed: content conservation: every output (kmer, summed count) must equal the canonicalizing input-only oracle
     left: {0: 5, 1: 9, 171: 6, 65536: 5, 65537: 11, 4194304: 4, 8327732: 2, 11239507: 4, 16716340: 7, 4294967295: 3}
    right: {0: 8, 1: 9, 171: 6, 65536: 5, 65537: 11, 4194304: 4, 8327732: 2, 11239507: 4, 16716340: 7}

   test result: FAILED. 2 passed; 1 failed
   ```

   (left = output: the two encodings of one k-mer as separate un-summed records; right = oracle: one summed `0x000000: 8`.)

## Task Commits

Each task was committed atomically:

1. **Task 1: RED proof — mixed-canonical test + fixture helper** - `b0b4189` (test)
2. **Task 1 (strengthening): true-high-byte key makes the order violation RED-provable** - `90c4285` (test)
3. **Task 2: one-site fix — store processed_kmer, propagate canonicalization errors** - `a347b61` (fix)
4. **Task 3: ANY-input header pin in both orders + full-phase gate** - `9cd7795` (test)

**Plan metadata:** this SUMMARY's docs commit follows immediately (see `plan_head_after` for the last production commit).

## Files Created/Modified

- `src/database/prefix_cache_merge.rs` — `split_files_by_prefix`: the shard stores `processed_kmer.to_le_bytes()` (count still `entry.count`), the `canonical_kmer_u128` call propagates via `?`, and a decision comment states the bucket-key == stored-key invariant (T-03-53/T-03-54). Nothing else in the file changed.
- `tests/prefix_cache_output_order_tests.rs` — `build_mixed_canonical_inputs` (raw-key input A + canonical input B + production-fn oracle, with asserted fixture-honesty guards) and `mixed_canonical_prefix_cache_output_is_ascending_summed_and_queryable`; CR-01/WR-03 module-doc paragraph; the proof enumeration names the third proof.
- `tests/merge_routing_tests.rs` — `prefix_cache_route_still_merges_mixed_canonical`: corrected ANY-input comment, reworded assertion message, reversed-order merge asserting `canonical: true`; `b_path` gains a mechanical `.clone()`.

## Decisions Made

- **One site, per the plan and the 03-VERIFICATION fix sketch:** only the shard write and the error propagation changed. `get_prefix_4mer`, both bucket merge writers, and the `concatenate_final_output` header write are untouched — under the fix their labels become truthful for mixed-canonical input for the first time.
- **All-T key rendered as `0xFFFF_FFFF`:** the plan's shorthand `0xFFFFFF` is a 24-bit key at k=16 (`AAAA` + twelve `T`s) whose canonical form is `0x0000FF`, not `0x000000` — it cannot satisfy the behavior block's meet-and-sum intent. Verified with a Python mirror of `reverse_complement_u128` before writing the fixture.
- **Fixture strengthened with `0x0100_0000`:** without a true-high-byte key, every record collapses into bucket 0x00 (all 24-bit literals have high byte 0x00 at k=16) and the hashmap writer's within-bucket sort erases the placement defect — windows(2) passed pre-fix and only conservation discriminated. The plan's fails_when clause ("strengthen the fixture") and its explicit RED expectation for windows(2) sanctioned the addition.
- **No pytest attempted:** the pyo3 surface inherits the fix through the path dependency with zero pyo3 edits (MERGE-04 by inheritance); Python-level verification remains blocked in-repo by the STATE.md maturin/pytest blocker (python-source key + --cov-fail-under; WINDOWS.md entries 4/5/11).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan's all-T fixture literal unsatisfiable at k=16**
- **Found during:** Task 1 (fixture design, before the first commit)
- **Issue:** the plan's input-A literal `0xFFFFFF` is a 24-bit key at k=16 whose canonical form is `0x0000FF` — the behavior block's "all-T; its canonical form is 0x000000" and the meet-and-sum oracle entry `0x000000 = 3 + 5` are unsatisfiable with that literal (the same k=16 literal trap 03-15 documented for `0x010000`).
- **Fix:** `const ALL_T_RAW: u128 = 0xFFFF_FFFF` (the 16-base all-T key), documented in the const's doc comment; all other literals kept verbatim.
- **Files modified:** tests/prefix_cache_output_order_tests.rs
- **Verification:** Python mirror of `reverse_complement_u128` over every fixture key before writing the test; oracle `0x000000 -> 8` guard passes at runtime.
- **Committed in:** b0b4189

**2. [Rule 1 - Bug] windows(2) could not discriminate on the plan's literal set (order axis not RED-provable)**
- **Found during:** Task 1 (first RED run passed windows(2) pre-fix)
- **Issue:** every plan literal is 24-bit (high byte 0x00 at k=16), so all ten records landed in bucket 0x00 (confirmed by a keep_intermediate shard dump); the hashmap writer sorts within a bucket, erasing the misplacement — the plan's stated RED expectation for the order assertion was unreachable.
- **Fix:** added `(0x0100_0000, 13)` to input B (a true-high-byte canonical key making bucket 0x01 non-empty), per the plan's own "strengthen the fixture" instruction; pre-fix violation pair `0xffffffff -> 0x1000000` verified before committing.
- **Files modified:** tests/prefix_cache_output_order_tests.rs
- **Verification:** second RED run failed at the windows(2) assertion; post-fix GREEN.
- **Committed in:** 90c4285

**3. [Rule 3 - Blocking] E0382 borrow-of-moved-value in the extended routing test**
- **Found during:** Task 3 (compile of merge_routing_tests)
- **Issue:** the reversed merge reuses `b_path`, which the pre-existing first merge call moved into its array argument.
- **Fix:** `&[a_path.clone(), b_path.clone()]` in the first call (mechanical; the merge and its assertions unchanged).
- **Files modified:** tests/merge_routing_tests.rs
- **Verification:** binary compiles; 37/37 green.
- **Committed in:** 9cd7795

**4. [Rule 3 - Blocking] acceptance grep tripped by the fix's own comment**
- **Found during:** Task 2 (acceptance gate)
- **Issue:** the new comment quoted the pre-fix pattern `.unwrap_or(entry.kmer)` in prose, so `grep -c "unwrap_or(entry.kmer)"` returned 1 (must be 0).
- **Fix:** reworded the comment ("swallowed-error fallback silently substituted the raw key").
- **Files modified:** src/database/prefix_cache_merge.rs
- **Verification:** grep count 0 on the fixed tree (the plan's negative gate).
- **Committed in:** a347b61

**5. [Scope boundary] cargo fmt --check fails on pre-existing drift**
- **Found during:** Task 3 (full-phase gate)
- **Issue:** exit 1 with 21 hunks across `src/cli/commands/count.rs`, `tests/merge_bounded_memory_tests.rs`, `tests/merge_cleanup_tests.rs`, `tests/parallel_count_tests.rs` — files zero phase-03-16 commits touch (git-verified: last commits 26cbf36/a316e4f/f8e8355/1e56098; the same drift 03-15 scoped out). All 03-16 touched files pass `rustfmt --check` individually.
- **Fix:** none applied (out of scope) — logged to deferred-items.md and WINDOWS.md #18 with a suggested one-commit `cargo fmt` fix or toolchain pin.
- **Committed in:** n/a (documentation in this plan's metadata commit)

---

**Total deviations:** 4 auto-fixed (2x Rule 1, 2x Rule 3) + 1 out-of-scope discovery documented
**Impact on plan:** All fixes preserve or strengthen the plan's stated behavior (the behavior block governed over the literal list); no scope creep. The fmt gate is the only plan verification item not cleanly green, blocked entirely by pre-existing conditions.

## Issues Encountered

**Streaming-writer residual discovered during Task 2 analysis (deferred, Rule 4 scale):** `merge_single_prefix_streaming` is a k-way heap merge over runs it assumes ascending. Post-fix, a NON-canonical input's shard stores canonical values in raw-stream order, which need not be ascending (the fixture's own bucket-0 shard: `0x0000AB, 0x007F1234, 0x00AB8053, 0x00FF1234, 0x000000`), so on the `merge_mode="streaming"` subset (or any bucket above the per-bucket `merge_buffer_mb` threshold under auto) a mixed-canonical merge can still emit non-ascending bucket output and miss equal-key summing — traced by hand on the fixture. NOT fixed here: the plan explicitly froze both bucket writers, and the fix (re-sort shards / sort at writer entry / drop the sorted-run assumption) is a design decision. Logged to deferred-items.md and WINDOWS.md #17 with a reproduction recipe. The delivered fix strictly improves every path (pre-fix, the streaming path was equally wrong on this subset — globally mis-ordered at bucket boundaries and un-summed).

## Prohibitions Verified

- `grep -c "unwrap_or(entry.kmer)" src/database/prefix_cache_merge.rs` returns 0 on the fixed tree (was exactly 1 pre-plan, at :295).
- The kmer write uses `processed_kmer.to_le_bytes()` and the count write still `entry.count.to_le_bytes()`, both inside the split_files_by_prefix block; no `.unwrap_or` remains on any `canonical_kmer_u128` call in the file.
- `get_prefix_4mer`, both bucket merge writers, and the `concatenate_final_output` header write (`canonical: self.canonical, sorted: true`) are untouched — verified by the commit diff touching only the 18 lines around the shard write.
- The routing test's capability-guard purpose and doc-comment first paragraph (prologue-gate rationale) survive; only the header-semantics comment/message changed plus the added reversed-order merge.

## Verification Results

1. RED (pre-fix): order assertion FAILED (evidence above) after strengthening; conservation assertion FAILED (evidence above) on the original fixture; both 03-15 tests passed in both runs.
2. GREEN (post-fix): `cargo test --test prefix_cache_output_order_tests` 3 passed / 0 failed; `cargo test --lib prefix_cache_merge` 8 passed / 0 failed; `cargo test --test prefix_cache_conservation_tests` 2 passed / 0 failed.
3. Routing: `cargo test --test merge_routing_tests` 37 passed / 0 failed.
4. Full gate: `cargo test` 23 result lines, all ok, 435 passed / 0 failed total (baseline 434 + 1 new); root `cargo clippy --all-targets -- -D warnings` exit 0; pyo3 `cargo clippy --manifest-path pyo3/Cargo.toml --all-targets -- -D warnings` exit 0; `cargo fmt --check` blocked by pre-existing drift only (see Deviations #5).

## User Setup Required

None - no external service configuration required. (Carried note: no Python-level run is possible in-repo — the STATE.md maturin python-source / pytest cov blocker stands; the pyo3 crate inherits this fix via its path dependency with zero pyo3 edits.)

## Next Phase Readiness

- 03-VERIFICATION.md human decision item 1 (CR-01 disposition) is executed: fixed in-phase, not accepted as advisory. Truth 10's UNCERTAIN half is now verifiable on the default (auto/hashmap) path; the phase's 10/11 becomes 11/11 modulo the streaming-writer residual recorded in WINDOWS.md #17 (reachable only via explicit merge_mode="streaming" or >threshold buckets).
- MERGE-01's "with human item 1 pending on the mixed-canonical subset" qualifier and DENSE-02's "same-mode proven" qualifier are discharged with behavioral evidence on the auto path.
- Known deferred items carried forward: the streaming-writer mixed-canonical residual (#17), the pre-existing fmt drift (#18), the maturin/pytest blocker (entries 4/5/11).

---
*Phase: 03-memory-safety*
*Completed: 2026-10-09*
