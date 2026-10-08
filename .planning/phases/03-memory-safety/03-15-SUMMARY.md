---
phase: 03-memory-safety
plan: 15
subsystem: database
tags: [prefix-cache, external-sort, bucketing, sorted-flag, binary-search, rkdb]

# Dependency graph
requires:
  - phase: 03-memory-safety (03-13)
    provides: CR-01/WR-03 conservation proofs for the per-bucket streaming merge (scheme-agnostic fixtures that stay green under re-bucketing)
provides:
  - First-4-bases (high-byte) prefix bucketing in ExternalSortMerger — index-order concatenation is globally ascending, making the output header's sorted:true truthful by construction (CR-02 closed)
  - A real unit test of get_prefix_4mer (IN-07's tautology removed)
  - End-to-end proof that a prefix-cache-merged database answers query_kmer and extract_prefix_optimized exactly per the oracle, and agrees with the in-memory route's answers (route parity of ANSWERS)
affects: [query paths trusting header.sorted, prefix-cache merge route, MERGE-04 route-parity claims]

actuals:
  tokens: 4957     # chars/4 over the realized diff (19,826 chars across the 2 files)
  tasks: 2
  commits: 3       # MEASURED: git rev-list --count 3ff8e23..HEAD

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Bucket by the HIGH byte of the right-aligned key so index-order concatenation equals u128 order — the flag becomes true by construction, not by assertion"

key-files:
  created:
    - tests/prefix_cache_output_order_tests.rs
  modified:
    - src/database/prefix_cache_merge.rs

key-decisions:
  - "Option (a) high-byte bucketing chosen over (b) sorted:false (degrades prefix extraction to linear scans, breaks the phase's sorted-output contract) and (c) sort-at-concatenation (re-reads and re-sorts the whole dataset the route exists to avoid touching)"
  - "The header write, concatenation loop, and prefix_to_dna were deliberately NOT modified — under high-byte bucketing the existing labels and the 'by first 4 bases' log claim become semantically correct for the first time"
  - "The k<4 arm keeps bucket == whole sub-byte key (shift saturates to 0) — monotone in the key, one k-mer per bucket at k=3"
  - "The plan's unit-test literal 0x010000 rendered as 0x0100_0000 at k=16: the literal is a 24-bit number whose HIGH byte is 0x00, so the plan's own strict assertion (bucket == 0x01) is unsatisfiable with the literal; the (high<<24)|low rendering preserves the strict 0x00 < 0x01 discriminator"

patterns-established:
  - "Prove a flag truthful by querying through its consumers (query_kmer binary search, extract_prefix_optimized), never by inspecting the flag alone"
  - "RED evidence captured for both the unit discriminator and the end-to-end order/query test against the pre-fix tree before the fix landed"

requirements-completed: [MERGE-01, DENSE-02]

coverage:
  - id: D1
    description: "get_prefix_4mer selects the FIRST 4 bases (high 8 bits of the right-aligned 2k-bit key), pinned by a unit test calling the production function"
    requirement: MERGE-01
    verification:
      - kind: unit
        ref: "src/database/prefix_cache_merge.rs#test_prefix_extraction_values"
        status: pass
    human_judgment: false
  - id: D2
    description: "A prefix-cache-merged database is globally ascending across the whole entries vector with a truthful sorted flag, answers every query_kmer exactly per the oracle (incl. a negative query), returns the exact oracle subset for a first-bases prefix via extract_prefix_optimized, and conserves content"
    requirement: DENSE-02
    verification:
      - kind: integration
        ref: "tests/prefix_cache_output_order_tests.rs#prefix_cache_output_is_globally_sorted_and_queries_correctly"
        status: pass
    human_judgment: false
  - id: D3
    description: "Route parity of ANSWERS — the prefix-cache output's decoded (kmer, count) map equals the in-memory route's on the same inputs and query_kmer agrees on every oracle key"
    requirement: MERGE-01
    verification:
      - kind: integration
        ref: "tests/prefix_cache_output_order_tests.rs#prefix_cache_answers_match_the_inmemory_route"
        status: pass
    human_judgment: false

# Metrics
duration: 10min
completed: 2026-10-09
status: complete
plan_head_before: 3ff8e23aa9ce2de1b2e5b3962f4784fac97095b3
plan_head_after: ad19683
---

# Phase 03 Plan 15: Prefix-Cache Output Order (CR-02) Summary

**First-4-bases (high-byte) prefix bucketing makes the prefix-cache route's index-order concatenation globally ascending, so its `sorted: true` header is truthful by construction — proven by querying the merged database through both binary-search consumers, not by inspecting the flag.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-10-08T23:28:01Z
- **Completed:** 2026-10-08T23:37:40Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- **CR-02 closed (03-VERIFICATION.md gaps[2]):** `get_prefix_4mer` (src/database/prefix_cache_merge.rs) now computes `((kmer >> 2 * kmer_size.saturating_sub(4)) & 0xFF)` — the HIGH 8 bits of the right-aligned 2k-bit key, i.e. the first 4 bases. Bucket order now agrees with key order (`a < b` implies `bucket(a) <= bucket(b)`), so `concatenate_final_output`'s index-order loop emits globally ascending output and the header's `sorted: true` is truthful.
- **IN-07 closed:** the tautological `test_prefix_extraction_values` (computed `(kmer >> (2 * (57 - 4))) & 0xFFF` itself, never called the production fn, asserted `< 256`) is rewritten into a real test calling `merger.get_prefix_4mer` — identity, the CR-02 order-discriminator pair, 0x7F/0x80 top-bit-boundary monotonicity, and the k=3 saturating arm.
- **End-to-end query proof:** `tests/prefix_cache_output_order_tests.rs` proves a prefix-cache-merged database is strictly ascending over the WHOLE entries vector (`windows(2)`), answers `query_kmer` exactly for every oracle key (plus one negative), returns exactly the oracle subset through `extract_prefix_optimized` for a first-bases prefix, conserves content, and gives ANSWERS identical to the in-memory route on the same inputs.

## Red Evidence (recorded against the pre-fix tree, before the fix landed)

1. **Unit discriminator:** the rewritten `test_prefix_extraction_values` FAILED on the low-byte implementation — `assert_eq!(get_prefix_4mer((0xAB << 24) | 0x123456), 0xAB)` panicked with `left: 86, right: 171` (0x56 is the LOW byte of `0x123456`; 0xAB = 171 is the expected high byte).
2. **End-to-end order test:** `prefix_cache_output_is_globally_sorted_and_queries_correctly` FAILED at the `windows(2)` ascending assertion (the first assertion in the test, exactly as the plan predicted) — the output was ordered by `(low_byte, kmer)`: bucket 0 (low byte 0x00) ended with 0xFF0000 followed by bucket 1's 0x000001, and the discriminator pair itself was inverted (0x010000 in low-byte bucket 0 written before 0x0000FF in bucket 255).
3. **Consumer proof (parity test):** `prefix_cache_answers_match_the_inmemory_route` FAILED with `routes disagree on the answer for k-mer 0x00000001 (AAAAAAAAAAAAAAAC): left: None, right: Some(1)` — the prefix-cache route's `query_kmer` binary search over non-ascending entries silently returned `None` where the in-memory route answered correctly. This is the exact consumer breakage CR-02 described.

## Task Commits

Each task was committed atomically:

1. **Task 1: Bucket by the first 4 bases** - `242c786` (feat)
2. **Rule 3 follow-up: clippy identity_op literal rewrite** - `9aa4039` (fix)
3. **Task 2: End-to-end order + query + route-parity proofs** - `ad19683` (test)

**Plan metadata:** this SUMMARY's docs commit follows immediately (see `plan_head_after` for the last production commit).

## Files Created/Modified

- `src/database/prefix_cache_merge.rs` — `get_prefix_4mer` computes the high-byte prefix with the right-alignment rationale documented; `test_prefix_extraction_values` rewritten (identity, order discriminator, monotonicity, k<4 arm). Header write, concatenation loop, `prefix_to_dna`, and both bucket merge strategies deliberately untouched.
- `tests/prefix_cache_output_order_tests.rs` — new integration binary: `prefix_cache_output_is_globally_sorted_and_queries_correctly` + `prefix_cache_answers_match_the_inmemory_route`.

## Decisions Made

- **Option (a) high-byte bucketing** over (b) `sorted: false` — (b) degrades prefix extraction to linear scans and breaks the phase's sorted-output contract — and over (c) sort-at-concatenation — (c) re-reads and re-sorts the whole dataset the route exists to avoid touching.
- **Untouched machinery:** the header write (:1234 region), the concatenation loop, and `prefix_to_dna` — under high-byte bucketing the existing labels and the `:244` log claim ("by first 4 bases") become semantically correct for the first time.
- **k < 4 arm:** `saturating_sub` makes the shift 0, so bucket == the whole sub-byte key — still monotone (one k-mer per bucket at k=3).
- **Discriminator literal at k=16:** the plan's `0x010000` is a 24-bit number (high byte 0x00 at k=16), so the plan's own strict assertion `bucket(b) == 0x01` is unsatisfiable with the literal; rendered as `0x0100_0000` (== `(0x01 << 24) | 0x00`) in the unit test, preserving the strict `0x00 < 0x01` discriminator and the pre-fix descending counterfactual. The integration fixture keeps the plan's literal pair `0x0000FF`/`0x010000` — at k=16 it is red pre-fix (descending output) and green post-fix (same 0x00-high-byte bucket, ascending within).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan's unit-test discriminator literal unsatisfiable at k=16**
- **Found during:** Task 1 (RED phase)
- **Issue:** the plan asserts `get_prefix_4mer(0x010000) == 0x01` on a k=16 merger, but `0x010000` is a 24-bit number whose high byte (bits 24..31) is 0x00 — the assertion cannot hold under the plan's own fix.
- **Fix:** rendered the pair at k=16 as `(0x00 << 24) | 0xFF == 0x0000FF` vs `(0x01 << 24) | 0x00 == 0x0100_0000`; the strict `0x00 < 0x01` discriminator and the pre-fix `0xFF > 0x00` descending counterfactual are preserved exactly.
- **Files modified:** src/database/prefix_cache_merge.rs (test body only)
- **Verification:** unit test RED pre-fix / GREEN post-fix; integration fixture keeps the plan's literal pair and is RED pre-fix / GREEN post-fix.
- **Committed in:** 242c786

**2. [Rule 3 - Blocking] clippy `-D identity_op` rejected two deliberate test literals**
- **Found during:** Task 2 (root clippy gate; Task 1's verify chain does not run clippy)
- **Issue:** `(0x00_u128 << 24) | 0xFF` and `(0x01_u128 << 24) | 0x00` in the rewritten unit test are identity operations under `-D clippy::identity-op`, failing the phase's blocking gate.
- **Fix:** rewritten as the plain hex literals `0x0000FF` / `0x0100_0000` with the `(high<<24)|low` reading kept in trailing comments; semantics unchanged.
- **Files modified:** src/database/prefix_cache_merge.rs (5 lines, test only)
- **Verification:** `cargo clippy --all-targets -- -D warnings` green on root; 8/8 lib tests still green.
- **Committed in:** 9aa4039

**3. [Rule 3 - Blocking] three compile errors in the first draft of the new test binary**
- **Found during:** Task 2 (red-evidence run)
- **Issue:** `dir.path()` called on a `&Path` parameter (2 sites) and a double-reference in the prefix-subset filter closure.
- **Fix:** `dir.join(...)`, `|(&kmer, _)|` / `|(&kmer, &count)|` destructuring.
- **Files modified:** tests/prefix_cache_output_order_tests.rs
- **Verification:** binary compiles; RED then GREEN as designed.
- **Committed in:** ad19683

---

**Total deviations:** 3 auto-fixed (1x Rule 1, 2x Rule 3)
**Impact on plan:** All fixes preserve the plan's semantics exactly; no scope creep. The rejected alternatives ((b) `sorted: false`, (c) sort-at-concatenation) were rejected by the plan itself and not implemented.

## Issues Encountered

None beyond the deviations above.

## Prohibitions Verified

- The output header still claims `sorted: true` AND the concatenated records are globally ascending by encoded u128 — asserted by `windows(2)` over the whole entries vector (the cheap `sorted: false` alternative was rejected).
- The re-bucketing changed only which intermediate shard a record transits: content conservation asserted unchanged against the same oracle shape 03-13 uses (`decode_observations == oracle`, `header.total_kmers == oracle.len()`), and 03-13's own conservation binary stayed green.
- Route parity of ANSWERS asserted, not assumed: the parity test fails loudly on the first disagreeing oracle key (it did, pre-fix, on k-mer 0x1).

## Verification Results

1. `cargo test --lib prefix_cache_merge` — ok. 8 passed; 0 failed (rewritten bucketing unit test + 03-13's conservation tests green under the re-bucketing).
2. `cargo test --test prefix_cache_output_order_tests` — ok. 2 passed; 0 failed.
3. Red evidence recorded (see Red Evidence section): unit discriminator + end-to-end order assertion + route disagreement, all against the low-byte tree.
4. Full `cargo test` green; `merge_cleanup_tests` 29/29; clippy `-D warnings` green on root AND pyo3; `rustfmt` applied to the two touched files; `git status --porcelain src/cli/commands/count.rs tests/parallel_count_tests.rs` empty.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 03-VERIFICATION.md gaps[2] (CR-02) is closed: the sorted flag is truthful on the prefix-cache route and every binary-search consumer returns correct results — proven by querying a prefix-cache-merged database.
- 03-13's conservation proofs and 03-11's 29 cleanup guarantees are green under the new bucketing.
- Phase 03 plan 15 of 15 complete: all plans in the phase have summaries; the phase is ready for verification / gap re-scan.

---
*Phase: 03-memory-safety*
*Completed: 2026-10-09*

## Self-Check: PASSED

- Files exist: tests/prefix_cache_output_order_tests.rs, .planning/phases/03-memory-safety/03-15-SUMMARY.md
- Commits are ancestors of HEAD: 242c786, 9aa4039, ad19683
- Evaluation scope resolved (plan 03-15, commits present on this branch)
