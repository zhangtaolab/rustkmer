---
phase: 03-memory-safety
plan: 07
subsystem: database
tags: [rust, rkdb, endianness, merge-routing, streaming-merge, data-corruption, tdd]

# Dependency graph
requires:
  - phase: 03-memory-safety
    provides: "Plan 03-01 made merge routing budget-dependent and fixed two latent streaming data-loss bugs (heap-refill strand, chunk-name collision); 03-04 established that a 'streaming' test arm is only proven if the route itself is asserted"
  - phase: 03-memory-safety
    provides: "03-VERIFICATION.md gap G3 (= code-review CR-01) with its measured corruption table; 03-06 landed immediately before this plan and left src/hash/ and src/lib.rs alone"
provides:
  - "`KmerEntry::read_from` is the exact inverse of `write_to` — no endianness heuristic, no per-record big-endian fallback"
  - "`tests/merge_route_parity_tests.rs` — 5 tests: the threshold round-trip matrix, the byte-exact 20-byte v2 record layout, a hand-written-little-endian read, and two above-threshold route-parity arms"
  - "Both merge routes proven to return byte-identical decoded maps for inputs carrying counts of 2,000,000 and 16,777,216, with each arm's route proven by the nonexistent-`temp_dir` probe"
  - "`StreamingMergeIterator::pending_error` — a non-EOF chunk read failure surfaces as `Some(Err(..))` instead of silently ending the run; `merge_sorted_chunks` rejects a chunk whose length is not a whole multiple of the 20-byte record"
affects: [phase-04-benchmark, merge-routing, MERGE-02, MERGE-04, DENSE-02, T-03-24, T-03-26, T-03-27]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
# Same estimateTokens scale (chars/4 over the realized diff), never a harness token count.
actuals:
  tokens: 10314
  tasks: 3
  commits: 3

# Commit ledger — MEASURED with `git rev-list --count`, never narrated (#3968).
commits: 3
plan_head_before: cf64fe3
# The post-TASK state (all three task commits landed). The plan-metadata commit
# that carries this file is its child; a commit cannot contain its own hash, so
# this field names the stable, verifiable parent rather than a self-reference.
plan_head_after: 9b6cd55

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Observation vs restatement for a byte-order claim: the behavioural round-trip matrix carries the fix; source greps (`count_le|count_be`, `> 1_000_000`) only confirm the heuristic text is gone, and `u32::from_le_bytes` is deliberately ungated because its count was 1 both before and after"
    - "EOF is not damage: `UnexpectedEof` at a run refill is the normal end of a run and must never be reported as an error, which is why mid-record truncation is caught earlier and exactly, by a length check in `merge_sorted_chunks`"
    - "Route parity needs an exact-count assertion beside map equality, because the two routes were wrong identically for 16_777_216 (`2^24` byte-swaps to `1`) — equality alone stayed green"
    - "Budgets derived from `RKDatabase::estimate_total_kmers` with an explicit `assert!` that the estimate exceeds them, so a shrunken fixture fails loudly instead of silently changing route"

key-files:
  created:
    - "tests/merge_route_parity_tests.rs — new integration binary, 5 tests: threshold round-trip matrix, byte-exact 20-byte layout, literal-byte read, and two above-threshold route-parity arms"
  modified:
    - "src/database/format.rs — `KmerEntry::read_from` reduced to a plain `u32::from_le_bytes`; the `count_le`/`count_be`/`1_000_000` heuristic and its comments deleted; a long invariant doc comment added; `kmer_entry_round_trips_counts_above_the_old_threshold` added to the existing `#[cfg(test)]` module"
    - "src/database/streaming_merge.rs — `RECORD_SIZE` const; `merge_sorted_chunks` gained a `len % RECORD_SIZE` truncation check and a `match` that reports a failed first-entry read; `StreamingMergeIterator` gained `pending_error` and its refill `if let Ok` became a three-arm `match`"

key-decisions:
  - "`UnexpectedEof` is the normal end of a run, not a damaged chunk. My first draft treated EVERY refill error as damage and the whole suite went red immediately — `test_external_merge` lost the final k-mer of a 3-record chunk. Chunk files are bare 20-byte record sequences with no count, so EOF at a refill is indistinguishable from truncation *there*; the fix places the check in `merge_sorted_chunks`, the one site that still holds the file length, before any reading starts"
  - "The chunk-truncation check is a length modulus, not a per-record heuristic. `len % RECORD_SIZE != 0` catches a partial tail exactly and cannot misfire on a well-formed chunk. `RECORD_SIZE` is pinned against a real `write_to` encode (`chunk_record_width_matches_the_pinned_constant`) so a layout change turns the check red rather than silently rejecting every chunk"
  - "Route parity is asserted on decoded `(String, u32)` maps, never raw integers — D-04 discipline, matching `tests/dense_differential_tests.rs`. The two encoder families are not guaranteed to agree, so an integer comparison would assert an incidental detail"
  - "Input B's k-mer set is built from a DIFFERENT base, making the two inputs provably disjoint, and `write_fixture_pair` asserts that disjointness. It is load-bearing: the in-memory route accumulates with `saturating_add`, so an overlapping fixture would merge to `2 * big_count` and could no longer distinguish 'read correctly' from 'summed twice'"
  - "No per-k-mer admission constant is pinned anywhere in the new binary. Arm B uses `n * 96 * 4`, which exceeds both today's 24 B/k-mer and plan 03-09's incoming 96, so the arm is stable across the wave boundary; a whole-file grep for the admission-constant identifier prints 0"
  - "`pyo3/tests/test_database_merge.py` was deliberately NOT modified. The installed `pyrustkmer.so` is a prebuilt artifact, so a pytest run would assert against code that no longer exists on disk — a green that means nothing"

patterns-established:
  - "A byte-order claim is carried by a behavioural round-trip matrix and confirmed by a source grep. The grep alone is a REGRESSION gate: it proves the heuristic text is absent, never that the reader is right. Recorded here because the plan's own `from_le_bytes` criterion had to be dropped — that token already sat INSIDE the heuristic, so its count was 1 before and 1 after and the gate was inert"
  - "When a format carries no record count, truncation can only be detected where the length is still available. Put the check at the open, not at the read, and make the run-terminating EOF explicit at the read"
  - "An assertion that two routes produce equal data is only half a claim when the defect could make them equally wrong. Pair every parity assertion with an exact expected value"

requirements-completed: [MERGE-01, MERGE-02, DENSE-02]

# Coverage metadata (#1602) — one entry per shipped deliverable.
coverage:
  - id: D1
    description: "`KmerEntry::read_from` decodes the count as a plain `u32::from_le_bytes` matching `write_to`; the `count_le` / `count_be` / `1_000_000` heuristic is gone from live code"
    requirement: MERGE-02
    verification:
      - kind: unit
        ref: "src/database/format.rs::kmer_entry_round_trips_counts_above_the_old_threshold (1 passed; observed RED at 1_094_848_256 before the fix)"
        status: pass
      - kind: integration
        ref: "tests/merge_route_parity_tests.rs#write_to_read_from_round_trip_is_exact_at_and_above_the_old_threshold (36 (kmer, count) pairs; observed RED at 1_094_848_256 before the fix)"
        status: pass
      - kind: other
        ref: "grep -vE '^\\s*//' src/database/format.rs | grep -c 'count_le\\|count_be' -> 0 (was 5); grep -vE '^\\s*//' src/database/format.rs | grep -c '> 1_000_000' -> 0 (was 1) — both DISCRIMINATE"
        status: pass
    human_judgment: false
  - id: D2
    description: "Counts at and above the old 1,000,000 threshold round-trip exactly: 1_000_001, 2_000_000, 16_777_216 and 4_000_000_000 all decode to themselves"
    requirement: MERGE-02
    verification:
      - kind: integration
        ref: "tests/merge_route_parity_tests.rs#write_to_read_from_round_trip_is_exact_at_and_above_the_old_threshold (4 k-mer values x 9 counts, incl. u32::MAX and u128::MAX)"
        status: pass
      - kind: integration
        ref: "tests/merge_route_parity_tests.rs#a_hand_written_little_endian_record_reads_back_as_itself (literal bytes at counts 2_000_000 / 16_777_216 / 4_000_000_000; observed RED at 2_156_142_080 before the fix)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The in-memory and streaming merge routes return byte-identical decoded maps for an input whose count exceeds 1,000,000, with each route proven to have been taken"
    requirement: MERGE-02
    verification:
      - kind: integration
        ref: "tests/merge_route_parity_tests.rs#routes_agree_and_are_exact_at_count_two_million (16 distinct k-mers, derived budget = estimate saturating_sub(1), Arm A proven by nonexistent-temp_dir Err, Arm B proven by the same path succeeding under merge_mode memory)"
        status: pass
      - kind: integration
        ref: "tests/merge_route_parity_tests.rs#routes_agree_and_are_exact_at_count_sixteen_million"
        status: pass
      - kind: other
        ref: "pre-fix reader: 3 of 5 tests RED — routes disagreed (streaming 2_000_000 vs in-memory 2_156_142_080) and 16_777_216 -> 1 on BOTH routes"
        status: pass
    human_judgment: false
  - id: D4
    description: "The 20-byte little-endian .rkdb v2 record layout is asserted byte by byte, so writer drift is observable by something other than the static golden hashes"
    requirement: DENSE-02
    verification:
      - kind: integration
        ref: "tests/merge_route_parity_tests.rs#record_layout_is_exactly_twenty_bytes_little_endian (buf[0..16] == kmer.to_le_bytes(), buf[16..20] == count.to_le_bytes())"
        status: pass
      - kind: unit
        ref: "src/database/streaming_merge.rs::chunk_record_width_matches_the_pinned_constant (pins RECORD_SIZE against a real encode)"
        status: pass
      - kind: integration
        ref: "cargo test --test golden_sha256_tests -> 2 passed; git status --porcelain tests/fixtures/ -> empty"
        status: pass
    human_judgment: false
  - id: D5
    description: "A damaged chunk surfaces as an Err instead of quietly truncating a run: a mid-record-truncated chunk file is rejected by name, and a non-EOF refill failure is reported via pending_error with no partial run emitted beside it"
    requirement: MERGE-01
    verification:
      - kind: unit
        ref: "src/database/streaming_merge.rs::chunk_truncated_mid_record_is_reported_not_silently_dropped (47-byte chunk -> Err naming 'truncated mid-k-mer' and the file)"
        status: pass
      - kind: unit
        ref: "src/database/streaming_merge.rs::chunk_record_count_that_is_a_whole_multiple_of_record_size_still_merges (the check is not a blanket rejection; the LAST k-mer is emitted)"
        status: pass
      - kind: unit
        ref: "cargo test --lib -> 225 passed, 0 failed (includes the pre-existing test_external_merge, which is what caught the first draft treating EOF as damage)"
        status: pass
    human_judgment: false
  - id: D6
    description: "MERGE-04's Python-side contract remains unverified at the Python level, and that residual is recorded rather than papered over"
    verification: []
    human_judgment: true
    rationale: "Not a testable behaviour in this repo. The `pyrustkmer.so` in the project venv is a prebuilt artifact, so any pytest run asserts against code no longer on disk. Plan 03-10 (wave 3) CHANGES `PyDatabase::merge` semantics — the save is folded into the merge and the 'Failed to save merged database to {}' path disappears — and that change ships with ZERO Python-level verification, because no plan in this phase may run pytest. The Rust route-parity test here is the only executable evidence for MERGE-04's Python behaviour until the extension is rebuilt from source. Making extending `pyo3/tests/test_database_merge.py` meaningful requires fixing the `pyo3/pyproject.toml` `python-source` misconfiguration recorded in `deferred-items.md`."

# Metrics
duration: 34 min
completed: 2026-10-07
status: complete
---

# Phase 03 Plan 07: Endianness Heuristic — Close G3 Summary

**`KmerEntry::read_from` is now the exact inverse of `write_to`, and the two merge routes are proven to return identical, correct data for counts of 2,000,000 and 16,777,216 — the values the phase verifier showed being read back byte-swapped, with the routes disagreeing on one of them.**

## Performance

- **Duration:** 34 min
- **Started:** 2026-10-07T12:17:29Z
- **Completed:** 2026-10-07T12:51:00Z
- **Tasks:** 3
- **Files modified:** 3 (1 created, 2 modified)

## The defect this plan closes

Gap **G3** (= code-review **CR-01**). `write_to` always emits a 4-byte little-endian count. `read_from` applied an endianness heuristic: *if the little-endian read came out above 1,000,000, re-read the same four bytes as big-endian*. On valid input that is not a compatibility feature, it is silent data corruption:

```text
true =    999999  ->    999999  OK
true =   1000001  -> 1094848256  CORRUPTED
true =   2000000  -> 2156142080  CORRUPTED
true =  16777216  ->         1  CORRUPTED
```

Phase 3 made the corruption **route-dependent**. The in-memory merge read each input once — one swap. The streaming merge read the input, wrote the sorted chunk back little-endian, and read the chunk out again — two swaps, which cancelled *by accident*, so the streaming route happened to be right. Same input, same budget, different data depending only on which route the budget picked.

The contract test for this already existed (`pyo3/tests/test_database_merge.py::test_streaming_and_inmemory_routes_produce_identical_data`) and is correct — it simply could not reach the bug, because every fixture count it builds is far below 1,000,000.

## Accomplishments

- **The heuristic is deleted, and the reader is documented as the writer's exact inverse.** `read_from` is now `read_u128::<LittleEndian>()` plus a plain `u32::from_le_bytes`. The doc comment records *why* there is no big-endian fallback: the v2 layout has only ever been written little-endian by this crate, so there is no legacy file to preserve, and `tests/fixtures/legacy_v2_offset42.rkdb` round-trips through the same path.
- **The behavioural gate was observed RED before it was GREEN.** Both new round-trip tests were run against the restored pre-fix reader and failed with the verifier's exact numbers — not an approximation of them.
- **Both routes are proven, not assumed.** Arm A's budget is derived from `RKDatabase::estimate_total_kmers` as `saturating_sub(1)` with an `assert!` that the estimate really exceeds it, and its streaming route is proven by an `Err` against a nonexistent `temp_dir`. Arm B uses the *same* nonexistent path and succeeds under `merge_mode: "memory"`, which the streaming route could not — that `Ok` is the in-memory proof. Neither budget pins a per-k-mer admission constant.
- **A damaged chunk now surfaces instead of truncating.** This turned out to be two defects, not one — see Deviations 2 and 3.
- **DENSE-02 survived untouched.** All 12 golden `.rkdb` fixtures still match `tests/fixtures/golden_manifest.sha256`; `git status --porcelain tests/fixtures/` is empty. No fixture was re-captured or regenerated.

## Task Commits

Each task was committed atomically:

1. **Task 1: Delete the endianness heuristic so `read_from` is the exact inverse of `write_to`** — `eb9c28f` (fix)
2. **Task 2: Pin the previously-corrupted counts with a threshold round-trip table** — `e334fa1` (test)
3. **Task 3: Prove the two routes produce identical data above the old threshold** — `9b6cd55` (test)

Task 1 is a `tracer` task; its feedback gate re-ran the plan's `<verify>` verbatim end-to-end and passed.

**Plan metadata:** *(the commit carrying this file — a commit cannot record its own hash)*

## Files Created/Modified

- `src/database/format.rs` — `read_from`'s count read reduced to one `u32::from_le_bytes`; `count_le` / `count_be` / the `1_000_000` comparison and their comments deleted; invariant doc comment added; `kmer_entry_round_trips_counts_above_the_old_threshold` added to the **existing** `#[cfg(test)]` module (which holds `test_kmer_entry_serialization`) rather than a new one
- `src/database/streaming_merge.rs` — `RECORD_SIZE` const; `merge_sorted_chunks` gained a `len % RECORD_SIZE` truncation check and a `match` reporting a failed first-entry read with the chunk path; `StreamingMergeIterator` gained `pending_error` and a three-arm refill `match`; three new unit tests
- `tests/merge_route_parity_tests.rs` — **new** integration binary, 5 tests

`write_to`, the `.rkdb` v2 layout, `DATABASE_VERSION` and every golden fixture were **not** touched.

## RED evidence — observed, not reconstructed

The pre-fix heuristic was temporarily restored in `read_from` and the new binary run against it. The tree was then restored from commit `eb9c28f` (`git checkout -- src/database/format.rs`) and re-verified green.

| Test | Pre-fix result |
|---|---|
| `write_to_read_from_round_trip_is_exact_at_and_above_the_old_threshold` | **FAILED** — `count 1000001 round-tripped as 1094848256` |
| `routes_agree_and_are_exact_at_count_two_million` | **FAILED** — routes disagreed: streaming `2000000` vs in-memory **`2156142080`** |
| `routes_agree_and_are_exact_at_count_sixteen_million` | **FAILED** — streaming returned **`1`**, expected `16777216` |
| `record_layout_is_exactly_twenty_bytes_little_endian` | GREEN — correct: layout was never the defect |
| `a_hand_written_little_endian_record_reads_back_as_itself` | **RED** after strengthening — `k-mer 0x1e8480, count 2000000` read back as `count 2156142080`. It was **GREEN** in its first form (k-mer 2,000,000 with count 5) because the heuristic fired on the *count* field and 5 never exceeds the threshold; that first form could not have caught the defect, so Task 3 added literal-byte cases at counts 2,000,000 / 16,777,216 / 4,000,000,000 and left the small-count case in place, labelled in-place as the field-order check it actually is. |

The pre-fix lib unit test was captured first, at the same commit as the fix's RED state:

```text
assertion `left == right` failed: count 1000001 round-tripped as 1094848256
  left: 1094848256
 right: 1000001
```

Post-fix: `cargo test` exits 0 across all 19 binaries, 225 lib tests + 5 new parity tests, zero `test result: FAILED`.

## Decisions Made

- **`UnexpectedEof` is the normal end of a run, not damage.** See Deviation 2 — this is the single most important decision in the plan, because the naive reading of "surface read errors" silently loses the last k-mer of every merge.
- **Truncation is caught by a length modulus at chunk open, not by a per-record heuristic at read time.** Chunk files are bare 20-byte record sequences carrying no count, so EOF at a refill genuinely cannot distinguish "run finished" from "file truncated" — the information is gone by then. `len % RECORD_SIZE != 0` catches the partial tail exactly and cannot misfire on a well-formed chunk.
- **`RECORD_SIZE` is pinned against a real encode.** A literal constant that can drift from the layout would turn the truncation check into either a blanket rejection or a silent pass. `chunk_record_width_matches_the_pinned_constant` writes a real `KmerEntry` and asserts `buf.len() == RECORD_SIZE`.
- **Route parity is asserted on decoded `(String, u32)` maps**, per D-04 — never raw integers, because the two encoder families are only guaranteed to invert each other.
- **The fixture's inputs are provably disjoint**, and that disjointness is asserted rather than assumed. It is load-bearing, not incidental: the in-memory route accumulates with `saturating_add`, so an overlapping fixture would merge to `4_000_000` and could no longer distinguish "read correctly" from "summed twice".
- **Arm B's budget is `n * 96 * 4 = 384 * n`.** This deliberately exceeds both today's 24 B/k-mer admission model and plan 03-09's incoming 96, so the arm survives the wave boundary. No per-k-mer constant is pinned in the file; if the model ever grows past 384 B/k-mer the arm hits the D-02 `Err` and the test fails loudly, which is the intended alarm rather than a silent route flip.
- **`pyo3/tests/test_database_merge.py` was deliberately NOT modified** — see the residual below.

## Residual — MERGE-04's Python surface ships unverified

Recorded as the plan requires, and this is the part worth carrying forward:

- **This plan changes no Python semantics.** `pyo3/tests/test_database_merge.py` is left untouched because the installed `pyrustkmer.so` in the project venv is a **prebuilt artifact** — a pytest run would assert against code that no longer exists on disk, i.e. a green that means nothing. `git status --porcelain pyo3/` is empty.
- **The Python fixture set remains the one place the same contract is expressed through a stale binary.** Extending it becomes meaningful only once the `pyo3/pyproject.toml` `python-source` misconfiguration (recorded in `deferred-items.md`) is fixed and the extension is rebuilt from source.
- **Plan 03-10 (wave 3) CHANGES `PyDatabase::merge` semantics** — the save is folded into the merge and the `"Failed to save merged database to {}"` path disappears — **and that change ships with zero Python-level verification**, because no plan in this phase may run pytest. The Rust route-parity test in this plan is the **only** executable evidence for MERGE-04's Python behaviour until the extension is rebuilt. A human should weigh that before treating 03-10's Python change as verified.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The plan's `1_000_000` grep criterion is unsatisfiable once step 10 is honoured**
- **Found during:** Task 1, running the acceptance criteria
- **Issue:** The plan asserts `grep -vE '^\s*//' src/database/format.rs | grep -c '1_000_000'` prints **2**, reasoning that of the 3 pre-fix occurrences only `:231` is the heuristic and the other two are `max_memory_usage: 1_000_000` in this file's own test module. But step 10 of the *same task* requires adding `kmer_entry_round_trips_counts_above_the_old_threshold` with `1_000_000` in its boundary list — a third non-comment occurrence. The criterion and the action contradict each other.
- **Fix:** The test was written as the plan requires, with the literal present. Rather than contort the code to hit an arbitrary number, the measured value is reported as **3**, and a genuinely discriminating gate was added: `grep -vE '^\s*//' src/database/format.rs | grep -c '> 1_000_000'` prints **0** (was 1) — that is the heuristic's actual syntax and it does discriminate.
- **Files modified:** none (reporting change only; the gate lives in the SUMMARY)
- **Verification:** Occurrence sites after the fix are `:227` (a doc comment, filtered by the grep), `:1342` (the required test's boundary list), `:1611` and `:1658` (the pre-existing `max_memory_usage` values). The heuristic line `:231` is gone.
- **Committed in:** n/a — measurement recorded, no code change

**2. [Rule 1 - Bug] Treating every refill error as damage loses the last k-mer of every run**
- **Found during:** Task 1, immediately after the first fix — `cargo test --lib` went red on the pre-existing `test_external_merge`
- **Issue:** The plan's step 8 says to turn the silent `if let Ok(next_entry)` into an error-propagating form. Implemented literally ("any read error is an error"), it returned `Some(Err(..))` when the reader hit EOF at the end of a run — but EOF at a refill is the **normal** termination of that run. A 3-record chunk merged to 2 results plus an error: the third k-mer was dropped and the merge reported failure. Shipping that would have replaced a silent-truncation bug with a data-losing one.
- **Fix:** The refill became a three-arm `match`: `Ok` re-queues; `Err(e) if e.kind() == UnexpectedEof` ends the run normally; any other `Err` sets `pending_error` (first failure only) and returns `Some(Err(..))` immediately, leaving the heap, `current_kmer` and `current_count` untouched and not re-queueing the popped item. Plan 03-01's refill-ordering fix (successor read *before* the emit branch) is preserved unchanged.
- **Files modified:** `src/database/streaming_merge.rs`
- **Verification:** `test_external_merge` green again (its third `next()` returns `(0x0030, 30)` and the fourth is `None`); 225 lib tests pass; `chunk_record_count_that_is_a_whole_multiple_of_record_size_still_merges` asserts the last record is emitted.
- **Committed in:** `eb9c28f`

**3. [Rule 2 - Missing Critical] Mid-record truncation was still silent after Deviation 2's fix**
- **Found during:** Task 1, immediately after Deviation 2
- **Issue:** Consequence of Deviation 2: once EOF is correctly classified as a normal end of run, a chunk file truncated mid-record becomes **indistinguishable** from a clean end at the refill site — chunk files carry no record count, so the information needed to tell them apart is gone by then. The plan's must-have ("no route silently truncates a damaged run") would therefore have been satisfied only for non-EOF I/O failures.
- **Fix:** The check moved to `merge_sorted_chunks`, which opens every chunk file and is the last site that still has its length: `file.metadata()?.len() % RECORD_SIZE != 0` returns an `Err` naming the file and saying "truncated mid-k-mer". `RECORD_SIZE: u64 = 20` is a documented `pub const`, pinned against a real `write_to` encode by `chunk_record_width_matches_the_pinned_constant` so a layout change turns the check red rather than silently rejecting every chunk. `merge_sorted_chunks`'s first-entry read also became a `match` returning `Err` naming the chunk path — EOF there means a zero-record chunk, which `sort_database` never writes.
- **Files modified:** `src/database/streaming_merge.rs`
- **Verification:** `chunk_truncated_mid_record_is_reported_not_silently_dropped` (47-byte chunk → `Err` naming "truncated mid-k-mer" and `damaged.chunk`); `chunk_record_count_that_is_a_whole_multiple_of_record_size_still_merges` proves the check is not a blanket rejection.
- **Committed in:** `eb9c28f`

**4. [Rule 1 - Bug] The first fixture generator produced 4 distinct k-mers, not 8**
- **Found during:** Task 3, first test run
- **Issue:** The fixture varied only the **last** base over `["A","C","G","T"]`, so `dedup` collapsed 8 generated k-mers to 4. The test failed loudly on its own `anyhow::ensure!(shared.len() == 8, ...)` guard — the guard earned its place — but the fixture was wrong.
- **Fix:** Two trailing positions now carry `i` in base 4, giving 16 distinct sequences. `write_fixture_pair` also gained an explicit disjointness assertion between A's and B's k-mer sets, so an accidental future overlap (which would silently turn the merged count into a sum of two) fails immediately.
- **Files modified:** `tests/merge_route_parity_tests.rs`
- **Verification:** Both route-parity arms pass and assert a 16-k-mer union.
- **Committed in:** `9b6cd55`

**6. [Rule 1 - Bug] One of the three Task-2 tests could not have failed**
- **Found during:** Task 3, reviewing the RED evidence table
- **Issue:** `a_hand_written_little_endian_record_reads_back_as_itself` asserted a hand-written record of (k-mer 2,000,000, count 5). The heuristic fired on the **count** field, and 5 never exceeds the 1,000,000 threshold — so this test was **GREEN against the pre-fix reader**. It was the plan's literal tuple, and the plan presented it as pinning "the exact value the verifier recorded as becoming 2_156_142_080", but that corruption was a *count* of 2,000,000, not a k-mer of 2,000,000. Shipping it as-is would have added a green test that reads as evidence and is not.
- **Fix:** The test now drives literal bytes at counts 2,000,000 / 16,777,216 / 4,000,000,000 as well, which **is** red pre-fix. The original small-count case is kept — it is a genuine field-order check the round-trip matrix cannot make, since that test validates the reader against the writer and would pass if both swapped the field order consistently — and it is now labelled in place as the non-discriminating check it is, with the reason.
- **Files modified:** `tests/merge_route_parity_tests.rs`
- **Verification:** Against the restored pre-fix reader this test is now **RED** (`k-mer 0x1e8480, count 2000000` read back as `count 2156142080`); green after the fix. Its RED status was captured explicitly, not inferred.
- **Committed in:** `9b6cd55` (amended)

**5. [Rule 1 - Bug] Three clippy `-D warnings` failures in the new binary**
- **Found during:** Task 3
- **Issue:** (a) `clippy::manual_repeat_n` on `std::iter::repeat(head).take(K - 2)`. (b) `clippy::type_complexity` on `both_routes`'s `Result<(BTreeMap<String, u32>, BTreeMap<String, u32>, u64)>` — and the third tuple element turned out to be unused, so it was removed entirely and a `type DecodedMap` alias introduced for the other two. (c) A stale unused `RKDB_V2_HEADER_SIZE` const, removed. (d) `grep -c 'BYTES_PER_KMER'` printed **1** instead of 0 — a doc comment explaining the no-pinned-constant rule had named the identifier, breaking the very gate that enforces it. Same trap plan 03-06 hit as its Deviation 5.
- **Fix:** `repeat_n`; the unused tuple element deleted and `DecodedMap` aliased; the const removed; the comment reworded so the identifier appears nowhere.
- **Files modified:** `tests/merge_route_parity_tests.rs`
- **Verification:** `cargo clippy --all-targets -- -D warnings` exits 0 on both crates; `grep -c BYTES_PER_KMER tests/merge_route_parity_tests.rs` prints **0**; `rustfmt --check` clean on all three touched files.
- **Committed in:** `9b6cd55` (and the unused-`K` clippy fix, which broke the Task-2 intermediate commit, was folded in by `git commit --amend` so no commit in this plan is clippy-red)

---

**Total deviations:** 6 auto-fixed (5 bug, 1 missing-critical)
**Impact on plan:** Deviations 2 and 3 together are the substantive work of this plan's second half. The plan's step 8, read literally, would have **lost the last k-mer of every streaming merge** — a worse data-loss bug than the silent truncation it was meant to fix — and Deviation 3 exists only because Deviation 2 made the truncation undetectable at the refill site. Deviations 1, 4 and 5 are corrections to the plan's own gates and fixture code, not scope expansion. No file outside the plan's scope was edited: `src/hash/`, `src/lib.rs`, `tests/golden_sha256_tests.rs`, `tests/merge_routing_tests.rs`, `src/cli/commands/count.rs` and `tests/parallel_count_tests.rs` are all untouched, and `pyo3/` is byte-identical.

## Plan acceptance gates — measured

### Task 1

| Gate | Expected | Measured |
|---|---|---|
| `kmer_entry_round_trips_counts_above_the_old_threshold` | 1 passed | **1 passed** — *DISCRIMINATES*: RED at `1_094_848_256` pre-fix |
| `grep -vE '^\s*//' format.rs \| grep -c 'count_le\|count_be'` | 0 (was 5) | **0** — *DISCRIMINATES* |
| `grep -vE '^\s*//' format.rs \| grep -c '> 1_000_000'` | 0 (was 1) | **0** — *DISCRIMINATES* (added in Deviation 1) |
| `grep -vE '^\s*//' format.rs \| grep -c '1_000_000'` | 2 (was 3) | **3** — criterion unsatisfiable alongside step 10; see Deviation 1 |
| `grep -vE '^\s*//' format.rs \| grep -c 'from_be_bytes'` | 0 (was 1) | **0** — *REGRESSION gate*, 1-before/1-after discipline |
| `grep -c 'pending_error' streaming_merge.rs` | ≥ 3 (was 0) | **8** |
| `grep -vE '^\s*//' streaming_merge.rs \| grep -c 'if let Ok(next_entry)'` | 0 (was 1) | **0** |
| `cargo test` | exit 0, no `test result: FAILED` | **exit 0, 0 FAILED, 225 lib + 19 binaries** |
| `cargo test --test golden_sha256_tests` | exit 0 | **exit 0, 2 passed** |
| `git status --porcelain tests/fixtures/` | empty | **empty** |
| `cargo clippy --all-targets -- -D warnings` (root, pyo3) | exit 0 | **exit 0 / exit 0** |

### Tasks 2 + 3

| Gate | Expected | Measured |
|---|---|---|
| `cargo test --test merge_route_parity_tests` | 5 passed | **5 passed** |
| `grep -c '2_000_000'` | ≥ 2 | **6** |
| `grep -c '16_777_216'` | ≥ 1 | **7** |
| `grep -c '4_000_000_000'` | ≥ 1 | **2** |
| `grep -c 'to_le_bytes'` | ≥ 2 | **4** |
| `grep -c 'estimate_total_kmers'` | ≥ 1 | **2** |
| Arm-A budget is `saturating_sub(1)` with a preceding `assert!` | present | **present** (`grep -c saturating_sub` → 1) |
| `grep -c 'BYTES_PER_KMER'` | 0 | **0** |
| `git status --porcelain pyo3/` | empty | **empty** |
| red-before-green round-trip result recorded | yes | **recorded above** |

## Recorded finding — a known pre-existing defect, not this plan's to fix

`tests/merge_routing_tests.rs:283` (plan 03-01's file) requires only that the over-budget route probe's error message contains `"temp"` or `"No such file"`. Several unrelated failures satisfy that substring, so it is a weaker route proof than the one this plan uses. It was **not** rewritten — that file belongs to plan 03-09. Reporting it here because 03-09 will edit that file and should tighten the assertion while it is there.

## Known Stubs

None. Every assertion in the new binary is wired to live production code; no fixture is mocked, no value is hard-coded to make a test pass, and no `#[ignore]`d test was left behind.

## Issues Encountered

- **`cargo` is not on `PATH`** in this executor's environment. Resolved with `export PATH="$HOME/.cargo/bin:$PATH"`, as plan 03-06 also had to do.
- **`/tmp/opencode` is not writable** (`Permission denied`), so the pre-fix reader could not be stashed there before the RED run. Resolved by restoring with `git checkout -- src/database/format.rs` from commit `eb9c28f`, which is strictly safer anyway — the restore could not silently differ from the committed state.
- **`ProcessingError` implements neither `PartialEq` nor `Debug`-for-`vec!`**, and `StreamingMergeIterator` is not `Debug`, so `assert_eq!` on a `Vec<Result<..>>` and `expect_err` both fail to compile. Resolved by mapping to `Vec<(u128, u32)>` and by a `match` instead of `expect_err` — no new derives were added, since that would widen `src/error.rs` beyond this plan's scope.
- **Whole-file `grep -c` gates constrain documentation, not just code** (Deviation 5d). A comment explaining that a token must not appear will itself trip the gate. Same lesson as plan 03-06's Deviation 5, recorded again because it has now recurred twice in this phase.

## Self-Check: PASSED

- **Created file exists:** `tests/merge_route_parity_tests.rs` — verified present.
- **Commits exist and are ancestors of HEAD:** `eb9c28f`, `e334fa1`, `9b6cd55` — verified via `git merge-base --is-ancestor`.
- **`commits: 3` is MEASURED, not narrated:** `git rev-list --count cf64fe3..HEAD` → 3, with `plan_head_before: cf64fe3` and `plan_head_after: 9b6cd55`.
- **`actuals.tokens: 10314`** is `chars/4` over the realized `src/` + `tests/` diff (41,259 chars) — the same scale as an `estimateTokens`, not a harness token count. This plan's frontmatter carries no `estimate` block, so there is nothing to pair it against yet.
- **Out-of-scope files untouched:** `src/hash/`, `src/lib.rs`, `tests/golden_sha256_tests.rs` (03-08's), `tests/merge_routing_tests.rs` (03-09's), `src/cli/commands/count.rs`, `tests/parallel_count_tests.rs`, and all of `pyo3/` — `git status --porcelain` empty for every one.
- **No mutation residue:** `src/database/format.rs` carries no `from_be_bytes` and no `count_le`/`count_be`; the heuristic restored for the RED run was reverted from the committed state, not by hand.
- **No accidental deletions:** `git show --diff-filter=D --name-only HEAD` for each task commit prints nothing.
- **`rustfmt --check` clean** on all three touched files. Pre-existing rustfmt drift in `src/cli/commands/count.rs` and `tests/parallel_count_tests.rs` was left alone, as instructed.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **G3 is closed on evidence, not assertion.** The heuristic is gone from live code, the round-trip matrix was seen RED at the verifier's exact numbers before the fix, and both routes are now proven to agree *and* to be exact on inputs above the threshold.
- **03-08 can proceed.** `tests/golden_sha256_tests.rs` was not touched; `cargo test --test golden_sha256_tests` is green (2 passed) and `tests/fixtures/` is byte-identical. Note for 03-08: plan 03-06 already reported stale `KmerKey` mentions in that file's docstrings.
- **03-09 can proceed.** No admission constant is pinned in `tests/merge_route_parity_tests.rs` (`grep -c BYTES_PER_KMER` → 0), and Arm B's `384 * n` budget exceeds the incoming 96 B/k-mer model, so replacing the model will not silently flip this plan's in-memory arm. `tests/merge_routing_tests.rs:283`'s weak substring assertion is worth tightening there.
- **Still open from `03-VERIFICATION.md`:** **G2** — no merge strategy is memory-bounded (`format.rs:852` loads `input_paths[0]` in full on the over-budget path; `:869-876` accumulates the entire merged output before `from_kmer_pairs` builds a third copy). Neither half of the phase's central deliverable is closed until that lands.
- **Carry-forward residual for 03-10:** `PyDatabase::merge`'s save semantics change in wave 3 with no runnable Python-level verification in this phase. It should be weighed at ship time.

---
*Phase: 03-memory-safety*
*Completed: 2026-10-07*