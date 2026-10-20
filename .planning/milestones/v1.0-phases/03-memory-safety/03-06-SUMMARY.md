---
phase: 03-memory-safety
plan: 06
subsystem: core-counting
tags: [rust, dashmap, memory, dense-storage, u64, u128, kmer-counter, mutation-testing]

# Dependency graph
requires:
  - phase: 03-memory-safety
    provides: "Plan 03-03 shipped the width-selected `KmerKey` enum key and the model-based `memory_usage()`; 03-VERIFICATION.md measured that layout and found DENSE-01 inverted (ratio 1.487)"
  - phase: 02-parallel-counting
    provides: "The `DashMap<u128,u32>` counter and the PCOUNT-04 atomic `entry().and_modify().or_insert_with()` per-key invariant this plan had to preserve verbatim on both widths"
provides:
  - "`KmerCounter::stored_key_bytes()` / `uses_dense_storage()` — read the LIVE `CounterTable` variant, so DENSE-01 can be observed instead of restated"
  - "`src/hash/key.rs` deleted; the `KmerKey` enum's 32-byte layout (48-byte DashMap slot) can no longer return"
  - "`tests/dense_memory_tests.rs` — a real-`KmerCounter` /proc/self/status bytes-per-entry measurement proving k=21 < k=64 at 4M entries (ratio 0.5152)"
  - "A mutation-proven red/green split showing the layout pin cannot observe a source mutation while the live-variant and RSS assertions can"
affects: [phase-04-benchmark, dense-storage, kmer-counter, DENSE-01]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 20244
  tasks: 3
  commits: 3

# Commit ledger — MEASURED with `git rev-list --count`, never narrated (#3968).
commits: 3
plan_head_before: ca932d0
# The post-TASK state (both task commits landed). The plan-metadata commit that
# carries this file is its child; a commit cannot contain its own hash, so this
# field names the stable, verifiable parent rather than a self-reference.
plan_head_after: 490fa6e

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Width on the TABLE, not on the KEY: a private `enum CounterTable { Dense(DashMap<u64,u32>), Wide(DashMap<u128,u32>) }` whose payloads never mention each other's width, so `size_of` is decided by the concrete map rather than by an enum discriminant"
    - "Observation vs model: `stored_key_bytes()` matches the live variant (observation); `memory_usage()` remains arithmetic over a model constant (model). Tests build on the former and label it as such"
    - "Single selection point: the width is chosen in exactly one `if` in `KmerCounter::new`, and `key_bytes()` delegates to the accessor rather than re-deriving it — provable as `self.kmer_length <= MAX_KMER_SIZE_IN_U64` count 1 -> 0"
    - "`bump_entry!` macro: one `entry().and_modify().or_insert_with()` shape shared by both arms of `increment` and both arms of `merge`, so the PCOUNT-04 shard-lock hold cannot drift between widths"
    - "RSS-delta measurement holds each counter alive while measuring the next, because a delta after a `drop` measures free-list reuse, not footprint"

key-files:
  created:
    - "tests/dense_memory_tests.rs — slot-layout pin, live-variant width assertions, and the 4M-entry real-KmerCounter RSS ratio"
  modified:
    - "src/hash/table.rs — CounterTable enum, bump_entry! macro, stored_key_bytes()/uses_dense_storage(), narrow_to_dense(), four rewritten inline tests"
    - "src/hash/mod.rs — `pub mod key;` and `pub use key::KmerKey;` removed"
    - "src/lib.rs — root re-export narrowed to `pub use hash::KmerCounter;`"
    - "tests/dense_differential_tests.rs — the two model-restating assertions replaced with live-storage assertions"
    - "tests/dense_merge_integration_tests.rs — the DENSE-01 ratio assertion moved onto `stored_key_bytes()`"
    - "tests/dense_proptest_tests.rs — stale `KmerKey` doc mentions only"
  deleted:
    - "src/hash/key.rs — the `KmerKey { U64(u64), U128(u128) }` enum whose `U128` variant forced 16-byte alignment and a 32-byte key"

key-decisions:
  - "The dense/wide width lives on the TABLE (a private two-variant enum), not on the KEY. An enum key with a `u128` variant costs 32 bytes regardless of which variant is populated, because the layout is fixed at compile time — so plan 03-03's own doc rationale ('the discriminant never adds live storage cost') was false and the feature increased memory"
  - "`stored_key_bytes()` / `uses_dense_storage()` match the live `CounterTable` variant and never re-derive from `kmer_length`. That single rule is the difference between an observation and a restatement, and it is what makes the 'always Wide' mutation detectable"
  - "`key_bytes()` was kept as a one-line delegate to `stored_key_bytes()` rather than deleted, so `memory_usage()`'s arithmetic stays in one place while its input becomes an observation"
  - "The entry chain is one `bump_entry!` macro invoked once per arm, with `modify`/`insert` blocks passed in — the two call sites differ in their overflow predicate and fresh-insert bookkeeping, and forcing them into one parameterised shape would have hidden a real semantic difference"
  - "`dense_narrowing_rejects_high_bits_on_the_u64_path` was rewritten to call the public `increment()` rather than deleted. The deleted enum made the old body uncompilable, and deleting it would have silently removed the only coverage of threat T-03-09's detection path"
  - "The RSS measurement holds each counter alive while measuring its sibling, and asserts `unique_kmers` and `stored_key_bytes` on every reading. Both were added after the first draft produced figures that were not measurements"

patterns-established:
  - "A claim about a *representation* must be asserted by reading the representation, not by recomputing it from configuration. Three of this phase's assertions violated this and were provably green under a mutation that removed the feature they claimed to test"
  - "A layout constant (`size_of::<T>()`) is not evidence for a behavioural requirement — it cannot go red under a source mutation. Assert it as a floor, name it as a floor, and point at the behavioural test for the claim"
  - "RSS deltas measure allocator behaviour, not allocation. Warm the allocator, hold siblings alive, and never report a per-entry figure below the type's own slot size"

requirements-completed: [DENSE-01, DENSE-02, DENSE-03]

# Coverage metadata (#1602) — one entry per shipped deliverable.
coverage:
  - id: D1
    description: "A k <= 32 KmerCounter stores its table as DashMap<u64,u32> (a 16-byte slot) and a k > 32 counter as DashMap<u128,u32>; the width is chosen at exactly one site in KmerCounter::new"
    requirement: DENSE-01
    verification:
      - kind: integration
        ref: "tests/dense_memory_tests.rs#real_counter_reports_the_width_it_actually_stores"
        status: pass
      - kind: integration
        ref: "tests/dense_memory_tests.rs#k21_counting_memory_is_below_k64_over_the_same_entry_count"
        status: pass
      - kind: unit
        ref: "src/hash/table.rs::dense_counter_memory_usage_halved_for_k21"
        status: pass
      - kind: other
        ref: "grep -vE '^\\s*//' src/hash/table.rs | grep -c KmerKey -> 0 (was 14); test ! -e src/hash/key.rs -> exit 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "DENSE-01 is measured, not modelled: a 4,000,000-entry real KmerCounter at k=21 uses strictly fewer bytes per entry than one at k=64, ratio below 1.0, in both measurement orders"
    requirement: DENSE-01
    verification:
      - kind: integration
        ref: "tests/dense_memory_tests.rs#k21_counting_memory_is_below_k64_over_the_same_entry_count (k21=35.66, k64=69.21 B/entry, ratio 0.5152; order A 0.5164, order B 0.5152)"
        status: pass
      - kind: other
        ref: "mutation 'always Wide' -> this test RED at ratio 1.0005; layout pin stayed GREEN"
        status: pass
    human_judgment: false
  - id: D3
    description: "src/hash/key.rs is deleted and the KmerKey enum's 32-byte / 48-byte-slot layout can no longer return"
    requirement: DENSE-01
    verification:
      - kind: other
        ref: "cargo build --lib exits 0 with no reference to the deleted module; cargo clippy --all-targets -D warnings exits 0"
        status: pass
      - kind: integration
        ref: "cargo test --test parallel_count_tests (the Phase 2 PCOUNT-04 consumer) exits 0"
        status: pass
    human_judgment: false
  - id: D4
    description: "The public u128-typed counter surface is unchanged, so .rkdb v2 bytes, count.rs and pyo3 are untouched (DENSE-02 byte-identity preserved)"
    requirement: DENSE-02
    verification:
      - kind: integration
        ref: "cargo test --test golden_sha256_tests (2 passed, 12 fixtures unchanged on disk)"
        status: pass
      - kind: integration
        ref: "cargo test --test dense_merge_integration_tests (3 passed, incl. dense_merge_output_preserves_rkdb_v2_layout)"
        status: pass
      - kind: integration
        ref: "pyo3: pytest tests/test_database_merge.py -o addopts='' -> 11 passed"
        status: pass
    human_judgment: false
  - id: D5
    description: "Decoded-level differential and proptest stay green and still discriminate a genuine narrowing bug (DENSE-03)"
    requirement: DENSE-03
    verification:
      - kind: integration
        ref: "cargo test --test dense_differential_tests (6 passed)"
        status: pass
      - kind: integration
        ref: "cargo test --test dense_proptest_tests (3 passed)"
        status: pass
      - kind: other
        ref: "mutation 'always Wide' -> dense_differential_tests 4 FAILED, 3 lib tests FAILED, confirming the assertions still bite"
        status: pass
    human_judgment: false
  - id: D6
    description: "Threat T-03-09's narrowing detection path survives the deletion of the type it used to name: a k=21 counter fed u128::MAX still panics with the original message substring, and a k=64 counter accepts it"
    requirement: DENSE-01
    verification:
      - kind: unit
        ref: "src/hash/table.rs::dense_narrowing_rejects_high_bits_on_the_u64_path (should_panic, 1 passed)"
        status: pass
      - kind: unit
        ref: "src/hash/table.rs::dense_narrowing_guard_does_not_fire_on_the_u128_path"
        status: pass
    human_judgment: false
  - id: D7
    description: "The reasoned decision NOT to narrow the in-memory merge accumulator (HashMapBrown<u128,u32> at src/database/format.rs:912) or the RKDatabase Vec<KmerEntry> read path"
    requirement: DENSE-01
    verification: []
    human_judgment: true
    rationale: "This is a scope judgement, not a testable behaviour. DENSE-01 names COUNTING memory; the in-memory merge route only runs when the merge is already under budget, and its peak is charged honestly by the per-route admission model delivered in plan 03-09. Narrowing those structures needs its own width-selection point and its own decoded-level differential, and bundling it here would put DENSE-01's sharpness behind untested breadth — the same reason 03-03 deferred it. Recorded as a deliberate deferral, not an oversight."

# Metrics
duration: 20 min
completed: 2026-10-07
status: complete
---

# Phase 03 Plan 06: Dense Storage Width — Close G1 Summary

**DENSE-01 was inverted and is now measured in the right direction: `KmerKey` is deleted so a k ≤ 32 counter really stores a 16-byte `DashMap<u64,u32>` slot, and two real 4,000,000-entry counters measure 35.66 vs 69.21 bytes/entry — ratio 0.5152, against the pre-fix 1.487.**

## Performance

- **Duration:** 20 min
- **Started:** 2026-10-07T11:53:27Z
- **Completed:** 2026-10-07T12:13:45Z
- **Tasks:** 3
- **Files modified:** 7 (1 created, 5 modified, 1 deleted)

## The defect this plan closes

Phase verification found DENSE-01 **empirically inverted**, not merely unverified. Plan 03-03 had made the dense key an enum:

```rust
pub enum KmerKey { U64(u64), U128(u128) }
```

An enum with a `u128` variant inherits `u128`'s 16-byte alignment, so `size_of::<KmerKey>()` is **32 bytes** and the `(K, V)` slot the `DashMap` actually stores is **48 bytes** — not 32, as the pre-Phase-3 `DashMap<u128, u32>` was. Measured over 4M entries through `/proc/self/status`: **102.89 B/entry** for k ≤ 32 against **69.34 B/entry** pre-Phase-3, **ratio 1.487**. Counting memory for exactly the k ≤ 32 case DENSE-01 is about went **up ~49%**. The plan's own doc rationale at `key.rs:31-34` — "the discriminant never adds live storage cost" — was false: layout is fixed at compile time and the discriminant is paid on every entry.

Worse, the three assertions purporting to demonstrate DENSE-01 were self-fulfilling. `key_bytes()` derived the width from `self.kmer_length`, never from a stored key, so `memory_usage()` restated the branch condition. The mutation "always store the wide variant" left all three green.

## Accomplishments

- **The width moved from the key to the table.** A private `enum CounterTable { Dense(DashMap<u64,u32>), Wide(DashMap<u128,u32>) }` carries the width in the *table's* type. Neither payload mentions the other's width, so `size_of` is decided by the concrete map and not by a discriminant. `src/hash/key.rs` is deleted, so the 32-byte key layout cannot return.
- **The observation point now exists.** `stored_key_bytes()` and `uses_dense_storage()` match the **live** `CounterTable` variant. Under the "always Wide" mutation a k=21 counter reports 16 instead of 8, which is what makes the defect detectable at all.
- **DENSE-01 is measured, not modelled.** A real 4,000,000-entry `KmerCounter` at k=21 and one at k=64, through `/proc/self/status`, in both orders: **k21 = 35.66 B/entry, k64 = 69.21 B/entry, ratio 0.5152** (order A 0.5164, order B 0.5152). The k=64 figure reproduces the verifier's 69.34 pre-Phase-3 baseline, which is what makes the two directly comparable — and the dense counter is now the cheaper one, as DENSE-01 claims.
- **The layout pin is labelled as a pin.** `size_of::<(u64,u32)>() == 16` is asserted and its docstring says plainly that a language constant cannot observe a source mutation and is not the G1 evidence. The mutation run proves it: it stayed GREEN while both behavioural tests went RED.
- **DENSE-02 and DENSE-03 survived untouched.** `get_all_counts() -> Vec<(u128, u32)>` is unchanged and every `u64` key still zero-extends losslessly: all 12 golden `.rkdb` sha256s match, the decoded differential (6) and proptest (3) stay green, and pyo3's merge contract still passes 11/11.
- **Threat T-03-09's detection path survived its own type's deletion.** `dense_narrowing_rejects_high_bits_on_the_u64_path` no longer compiles against a deleted enum, so it was rewritten to drive the public `increment()` — and still catches its panic against the original message substring.

## Task Commits

Each task was committed atomically:

1. **Task 1: Move the width choice from the KEY onto the TABLE** - `683c2ec` (refactor)
2. **Task 2: Replace the self-fulfilling DENSE-01 assertions with a stored-representation observation and a real measurement** - `490fa6e` (test)

Task 3 is verification-only and produced no code change; its results are recorded below and in the plan's acceptance table.

**Plan metadata:** *(the commit carrying this file — a commit cannot record its own hash)*

## Files Created/Modified

- `src/hash/table.rs` - private `CounterTable` enum, `bump_entry!` macro, `stored_key_bytes()` / `uses_dense_storage()` / `narrow_to_dense()`, four inline tests rewritten
- `src/hash/key.rs` - **deleted** — the `KmerKey` enum (the 32-byte key)
- `src/hash/mod.rs` - `pub mod key;` and `pub use key::KmerKey;` removed
- `src/lib.rs` - root re-export narrowed to `pub use hash::KmerCounter;`
- `tests/dense_memory_tests.rs` - **new** integration binary: layout pin, live-variant width assertions, real-`KmerCounter` RSS ratio
- `tests/dense_differential_tests.rs` - the two model-restating assertions replaced with live-storage assertions; decoded-map equality untouched
- `tests/dense_merge_integration_tests.rs` - DENSE-01 assertion moved onto `stored_key_bytes()`; 4-way equality and route-probe machinery untouched
- `tests/dense_proptest_tests.rs` - stale `KmerKey` doc mentions only (no behavioural change)
- `.planning/phases/03-memory-safety/03-06-red-evidence{,-classifier-record}.json` - the captured mutation RED run and its classifier record

## Measurement results

| | k=21 (dense) | k=64 (wide) | ratio |
|---|---|---|---|
| Order A (k21 first) | 35.80 B/entry | 69.34 B/entry | 0.5164 |
| Order B (k64 first) | 35.66 B/entry | 69.21 B/entry | **0.5152** |
| **Pre-fix baseline (verifier)** | **102.89 B/entry** | 69.34 B/entry | **1.487** |

4,000,000 entries per counter, both real `KmerCounter`s, `stored_key_bytes` confirmed as 8 and 16 respectively on the measured instances, `unique_kmers == 4_000_000` asserted on all four. Reproducible across three consecutive runs to the printed precision.

### Mutation red/green split — "always build `CounterTable::Wide`"

| Binary | Test | Under mutation |
|---|---|---|
| `dense_memory_tests` | `real_counter_reports_the_width_it_actually_stores` | **RED** — k=1 reported 16, expected 8 |
| `dense_memory_tests` | `k21_counting_memory_is_below_k64_over_the_same_entry_count` | **RED** — ratio 1.0005 (order A) / 1.0000 (order B) |
| `dense_memory_tests` | `slot_layout_is_pinned_for_both_widths` | **GREEN** ← exactly why it is not the G1 evidence |
| `dense_differential_tests` | 4 of 6 tests | **RED** |
| `dense_merge_integration_tests` | `dense_count_then_merge_matches_u128_merge_k21` | **RED** |
| `cargo test --lib` | 3 tests (incl. `dense_counter_memory_usage_halved_for_k21`) | **RED** |
| `dense_proptest_tests` | all 3 | GREEN (correctness, not width) |

Classifier verdict on the JUnit report: **`RED_EVIDENCE_OK`**, reason `target_test_failed`, `tests=3 pass=1 fail=2`, `report_errors=[]`. The mutation was reverted and `src/hash/table.rs` is byte-identical to the Task 1 commit.

## Decisions Made

- **Width on the table, not on the key.** Reopening RESEARCH Pattern 1 Option A, which 03-03 rejected on blast-radius grounds. The private two-variant enum costs one `match` per accessor and nothing at the public boundary.
- **Accessors read the live variant, never `kmer_length`.** This is the whole difference between an observation and a restatement, and it is the single rule the new tests are built on.
- **`key_bytes()` kept as a one-line delegate** rather than deleted, keeping `memory_usage()`'s arithmetic in one place while its input becomes an observation.
- **One `bump_entry!` macro, blocks passed in.** The two call sites differ in their overflow predicate (`*count == self.max_count` vs `*existing > u32::MAX - count`) and their fresh-insert bookkeeping; a single parameterised shape that hid that difference would be worse than the duplication it replaced.
- **The T-03-09 test was rewritten, not deleted.** Deleting it would have silently removed the only coverage of a `high`-severity tampering threat — a regression disguised as a cleanup.
- **The RSS measurement holds each counter alive while measuring its sibling.** See Deviations below; the first draft was not a measurement.
- **`src/lib.rs` was edited although it is not in the plan's `files_modified` list.** `pub use hash::{KmerCounter, KmerKey};` is a real code reference outside `src/hash/`, so deleting the module would not compile. Rule 3 (blocking).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `src/lib.rs` re-exported the deleted `KmerKey`**
- **Found during:** Task 1
- **Issue:** `src/lib.rs:35` had `pub use hash::{KmerCounter, KmerKey};`. The plan's step 8 asserted "Nothing outside `src/hash/` references `KmerKey`" — that was **false**, and the plan itself required re-verifying with `grep -rn 'KmerKey' src/ tests/ pyo3/src/` before deleting. The grep found this line plus four test files (all comment/string mentions). Deleting `src/hash/key.rs` without editing `lib.rs` would not compile.
- **Fix:** Narrowed to `pub use hash::KmerCounter;` with a comment recording why `KmerKey` is gone and that the counter's `u128` surface is unchanged.
- **Files modified:** `src/lib.rs`
- **Verification:** `cargo build --lib` and `cargo clippy --all-targets -- -D warnings` both exit 0; the whole `u128`-typed surface every other caller depends on is unchanged.
- **Committed in:** `683c2ec`

**2. [Rule 1 - Bug] The first RSS-delta measurement was not a measurement**
- **Found during:** Task 2, after the first GREEN run
- **Issue:** Two distinct allocator artifacts corrupted the figures. (a) The first large allocation in a process pays arena growth and first-touch faults, so whichever counter was built first read high regardless of width — order A reported 0.9697 against order B's 0.0682 on the identical tree. (b) Once a counter is dropped, the next one can be satisfied entirely from already-resident free-list blocks, so the RSS delta collapses: a clean 4M-entry dense counter read **2.51 B/entry, below its own 16-byte `(u64, u32)` slot** — physically impossible as a footprint, which is the tell.
- **Fix:** `build_and_measure` now returns the counter instead of dropping it, and `measure_both` holds the first counter alive while measuring the second, so both deltas must come from pages the process does not have. A discarded first attempt at a warm-up pass was removed once the hold-alive approach made it unnecessary. Each reading additionally asserts `unique_kmers` and `stored_key_bytes`, so a shrunk fixture or a mismatched width fails loudly instead of producing a flattering ratio.
- **Files modified:** `tests/dense_memory_tests.rs`
- **Verification:** Post-fix the two orders agree to three significant figures (0.5164 / 0.5152) and reproduce identically across three consecutive runs; the k=64 figure lands on 69.21–69.34 B/entry, matching the verifier's independent pre-Phase-3 baseline of 69.34.
- **Committed in:** `490fa6e`

**3. [Rule 1 - Bug] `seed_saturated`'s guard duplicated the width-selection condition**
- **Found during:** Task 1
- **Issue:** The helper's first draft asserted `kmer_length <= MAX_KMER_SIZE_IN_U64` per arm, putting a **second** occurrence of the width predicate in the file. The plan's acceptance criterion requires exactly one non-comment occurrence — the no-double-selection invariant. A test helper that restates the production predicate is also precisely the drift the plan exists to prevent.
- **Fix:** The helper now compares the caller's `kmer_length` against `counter.kmer_length()` (a caller-consistency check, not a width restatement) and narrows through the production `narrow_to_dense`, so test seeds are covered by the T-03-09 guard too.
- **Files modified:** `src/hash/table.rs`
- **Verification:** `grep -vE '^\s*//' src/hash/table.rs | grep -c 'kmer_length <= MAX_KMER_SIZE_IN_U64'` prints 1; the count was 2 before the fix.
- **Committed in:** `683c2ec`

**4. [Rule 1 - Bug] `clippy::doc_lazy_continuation` blocked `-D warnings` on a rewritten doc comment**
- **Found during:** Task 1
- **Issue:** The rewritten `memory_usage()` doc comment opened a line with `k > 32 counter.`, which the markdown doc parser reads as a blockquote and reports as an unindented list item under `-D warnings`. That makes the plan's clippy gate fail on prose.
- **Fix:** Reworded so no doc line begins with `>`, without changing the meaning.
- **Files modified:** `src/hash/table.rs`
- **Verification:** `cargo clippy --all-targets -- -D warnings` exits 0 on both crates.
- **Committed in:** `683c2ec`

**5. [Rule 1 - Bug] The `grep -c DashMap` gate was broken by the file's own explanation**
- **Found during:** Task 2
- **Issue:** The plan's gate is `grep -c 'DashMap' tests/dense_memory_tests.rs` printing **0** — a plain grep with no comment filter. The module docstring explained the rule by naming the map type seven times (including inside two assertion messages), so the gate read 7.
- **Fix:** Reworded so the token appears nowhere in the file. The rule is now stated as "this file contains no reference to the map type at all, by design: `grep -c` for it over this file must print 0", which keeps the explanation without breaking the gate.
- **Files modified:** `tests/dense_memory_tests.rs`
- **Verification:** `grep -c DashMap tests/dense_memory_tests.rs` prints 0; the file still builds and all three tests run.
- **Committed in:** `490fa6e`

---

**Total deviations:** 5 auto-fixed (3 bug, 1 blocking, 1 bug-in-gate)
**Impact on plan:** All five were corrections to the plan's own code or gates, not scope expansion. Deviation 1 was a factual error in the plan's step 8 that would have blocked compilation. Deviations 2 and 5 are the two that mattered most: without 2 the headline ratio would have been a number the test could not defend, and without 5 the plan's non-vacuity gate would have read 7 instead of 0. No new files outside the plan's scope were created.

## Plan acceptance gates — measured

### Task 1 (all PASS)

| Gate | Expected | Measured |
|---|---|---|
| `grep -vE '^\s*//' src/hash/table.rs \| grep -c KmerKey` | 0 (was 14) | **0** — *discriminates* |
| `test ! -e src/hash/key.rs` | exit 0 (file existed) | **exit 0** — *discriminates* |
| `grep -c 'pub use key::KmerKey' src/hash/mod.rs` | 0 (was 1) | **0** |
| `grep -c 'fn stored_key_bytes' src/hash/table.rs` | 1 (was 0) | **1** |
| `grep -c 'fn uses_dense_storage' src/hash/table.rs` | 1 (was 0) | **1** |
| bare `kmer_length <= MAX_KMER_SIZE_IN_U64` (non-comment) | 1 | **1** — *invariant only: 1 before and 1 after, cannot distinguish the move* |
| `self.kmer_length <= MAX_KMER_SIZE_IN_U64` | 0 (was 1) | **0** — *this is the gate that discriminates the move* |
| `dense_narrowing_rejects_high_bits_on_the_u64_path` count | 1 | **1** |
| `dense_narrowing_guard_does_not_fire_on_the_u128_path` count | 1 | **1** |
| `KmerKey::from_u128` (non-comment) | 0 | **0** |
| `size_of::<u64>()` (non-comment) | ≥ 1 | **2** |
| `stored_key_bytes` in `src/hash/table.rs` | ≥ 3 | **12** |
| `cargo test --lib` | exit 0, non-zero passed | **exit 0, 221 passed** |
| `cargo test --lib dense_narrowing_rejects_high_bits_on_the_u64_path` | 1 passed | **1 passed** (caught panic) |
| `cargo clippy --all-targets -- -D warnings` | exit 0, no `error` | **exit 0** |
| `cargo test --test golden_sha256_tests` | exit 0 | **exit 0, 2 passed** |

### Task 2 (all PASS)

| Gate | Expected | Measured |
|---|---|---|
| `dense_memory_tests --test-threads=1 --nocapture` | exit 0, prints both figures | **exit 0; 35.66 / 69.21 B/entry** |
| ratio assertion is `k21 / k64 < 1.0` | present | **present** (asserted in all three order-robust forms) |
| `grep -c KmerCounter::new` in the new binary | ≥ 2 | **4** |
| `grep -c DashMap tests/dense_memory_tests.rs` | 0 | **0** |
| `grep -c stored_key_bytes src/hash/table.rs` | ≥ 3 | **12** |
| `grep -c stored_key_bytes tests/dense_differential_tests.rs` | ≥ 1 | **6** |
| `size_of::<u64>()` non-comment in `table.rs` | ≥ 1 | **2** |
| `cargo test --test dense_differential_tests` | exit 0 | **6 passed** |
| `cargo test --test dense_proptest_tests` | exit 0 | **3 passed** |
| `cargo test --test dense_merge_integration_tests` | exit 0 | **3 passed** |
| mutation red/green split recorded | 2 RED, layout pin GREEN | **recorded above** |
| `git status --porcelain src/` at end | empty | **empty** |

### Task 3 (all PASS, with one recorded finding)

| Gate | Expected | Measured |
|---|---|---|
| `cargo test` | exit 0, no `test result: FAILED` | **exit 0, 18 binaries + doc-tests green, 221 lib tests** |
| `cargo clippy --all-targets -- -D warnings` (root) | exit 0 | **exit 0** |
| `cargo clippy --all-targets -- -D warnings` (pyo3) | exit 0 | **exit 0** |
| `git status --porcelain src/cli/commands/count.rs tests/parallel_count_tests.rs` | empty | **empty** — rustfmt did not reach them |
| plan-touched files rustfmt-clean | clean | **clean** |
| pyo3 merge contract (extra, MERGE-04 shared-core) | green | **11 passed** |

**Recorded finding — one acceptance criterion is not satisfiable as written.** Task 3's criterion says "no `0 passed` result line", but `cargo test` emits two, and both are pre-existing and structural:

- `unittests src/main.rs` — the CLI binary has no `#[cfg(test)]` module (0 at the base commit `8da6316` too).
- `tests/golden_generate.rs` — a fixture *generator*; its single test is `#[ignore]`d by design (also 1 `#[ignore]` at the base commit).

Neither is touched by this plan and neither indicates a problem. Recording it rather than papering over it: the criterion should read "no `0 passed` result line **other than the two structural ones**", or simply "no `test result: FAILED`". This plan did **not** add tests to either binary.

**Recorded finding — pre-existing rustfmt drift left in place, as instructed.** `rustfmt --check src/lib.rs` follows `mod` declarations and reports 4 diffs in `src/cli/commands/count.rs`. The identical 4 diffs are present at the base commit `8da6316`, and `deferred-items.md` explicitly warns this plan is not authorised to touch that file. All files this plan did touch are rustfmt-clean.

## Deliberate non-goal — the in-memory merge accumulator is NOT narrowed

Recorded as the plan requires, with the reasoning intact:

The dense width is applied to `KmerCounter`'s table only. It is deliberately **not** applied to `merge_databases_inmemory`'s `HashMapBrown<u128, u32>` accumulator (`src/database/format.rs:912`) or the `RKDatabase` read path (`pub entries: Vec<KmerEntry>`, `src/database/format.rs:267`).

**Judgement:** DENSE-01 names **counting** memory, and the in-memory merge route only runs when the merge is already under budget — its peak is charged honestly by the per-route admission model delivered in plan 03-09. Narrowing those structures needs its own width-selection point and its own decoded-level differential, and bundling it here would put DENSE-01's sharpness behind untested breadth — the same reason 03-03 deferred it. This is a reasoned deferral, not an oversight, and `src/database/format.rs` is not in this plan's `files_modified` list (it belongs to sibling plan 03-07).

## Issues Encountered

- **`gsd_run` is not on `PATH`** in this executor's environment. Resolved by invoking `.opencode/gsd-core/bin/gsd_run` directly with `$PWD/.opencode/gsd-core/bin` prepended.
- **The TDD RED evidence classifier has no libtest adapter.** Its `report-parser` supports TAP, JUnit XML, swift-testing and Python unittest — not Rust's default `pretty` output, and `cargo nextest` is not installed. Resolved with libtest's own `--format=junit`, which is gated behind `-Z unstable-options` on stable; `RUSTC_BOOTSTRAP=1` unlocks the reporter for report generation only. The toolchain and the tree are unchanged, and the JUnit report is the unmodified reporter output. Classifier verdict: `RED_EVIDENCE_OK`.
- **`clippy::doc_lazy_continuation` fires on doc lines beginning with `>`.** Handled in Deviation 4.
- **`grep -c` gates have no comment filter**, so prose that names a gated token breaks them. Handled in Deviation 5 and in `seed_saturated` (Deviation 3) — the general lesson being that a whole-file `grep -c` gate constrains documentation, not just code.

## Self-Check: PASSED

- Created file exists: `tests/dense_memory_tests.rs` — verified present.
- Deleted as intended: `src/hash/key.rs` — verified absent, and `git show --diff-filter=D` names it in commit `683c2ec`.
- Commits exist and are ancestors of HEAD:
  - `683c2ec` (Task 1) — verified
  - `490fa6e` (Task 2) — verified
- `commits: 3` is **measured**, not narrated: `git rev-list --count ca932d0..a3886be` → 3, with `plan_head_before: ca932d0` and `plan_head_after: 9bd8cdf`. The three are the two task commits plus this plan's metadata commit.
- `actuals.tokens: 20244` is `chars/4` over the realized `src/` + `tests/` diff (80,976 chars) — the same scale as the plan's `estimateTokens`, not a harness token count.
- Out-of-scope files untouched: `src/cli/commands/count.rs`, `tests/parallel_count_tests.rs`, `src/database/format.rs` (03-07), `tests/golden_sha256_tests.rs` (03-08) — all verified clean via `git status --porcelain`.
- No mutation residue: `src/hash/table.rs` is byte-identical to the Task 1 commit (`git diff` empty), and `git status --porcelain src/` prints nothing.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **DENSE-01 is now closed on evidence, not assertion.** The measured ratio inverted from 1.487 to 0.5152, and the assertions that carry it have been seen RED.
- **Sibling plans in this wave are safe.** 03-07 (`src/database/format.rs`, `tests/merge_route_parity_tests.rs`) and 03-08 (`tests/golden_sha256_tests.rs`) were not touched; both build on commits `683c2ec` / `490fa6e`.
- **Note for 03-08:** `tests/golden_sha256_tests.rs` still describes the change as "the `KmerKey` swap" and mentions `KmerKey::U64` in four docstrings. Those are now stale — the enum is deleted. 03-08 owns that file; this plan deliberately left it alone.
- **Phase 3 still has two open gaps** from `03-VERIFICATION.md` that this plan did not address: G2 (no merge strategy is memory-bounded — `format.rs:852` loads an input in full, `:869-876` accumulates the whole output) and G3 (routes disagree above 1M counts — the `read_from` endianness heuristic). Neither is in 03-06's scope.
- **One deferred decision to revisit:** whether to narrow the in-memory merge accumulator (`format.rs:912`) and the `Vec<KmerEntry>` read path. Deliberately out of scope here; it would need its own width-selection point and its own decoded-level differential.

---
*Phase: 03-memory-safety*
*Completed: 2026-10-07*