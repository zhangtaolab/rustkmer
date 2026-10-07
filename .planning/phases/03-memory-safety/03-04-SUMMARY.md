---
phase: 03-memory-safety
plan: 04
subsystem: testing
tags: [rust, integration-test, cross-plan-gate, rkdb, merge, dense-storage, mutation-testing, decoded-differential]

requires:
  - phase: 03-memory-safety
    plan: 01
    provides: "bounded merge dispatcher (RKDatabase::merge_databases header-only estimator, MERGE-02 hard route, D-02 reject) + tests/merge_routing_tests.rs's temp_dir route-observation probe"
  - phase: 03-memory-safety
    plan: 03
    provides: "width-selected KmerKey (dense u64 for k<=32) + decoded-level differential discipline (D-04/D-05) + the committed Phase 1/2 golden .rkdb fixtures this plan reuses as u128 ground truth"
  - phase: 01-foundation-quality
    provides: "12 committed golden .rkdb fixtures + golden_manifest.sha256 (D-10 byte-identity baseline); log:: facade + clippy -D warnings gate on both crates"
  - phase: 02-parallel-counting
    provides: "PCOUNT-04 parallel_count_tests, which must not be regressed by the two Phase 3 swaps"

provides:
  - "tests/dense_merge_integration_tests.rs — 3 GREEN end-to-end tests proving the 03-01 + 03-03 composition: dense u64-path count -> .rkdb v2 write -> bounded merge -> decoded (String, u32) map equals the u128 golden .rkdb -> merge, on BOTH merge routes (4-way)"
  - "The v2 on-disk layout guarantee asserted on MERGE OUTPUT, not just on pre-existing fixtures (magic, version 2, data_offset 42, 42+20*n sizing, header accounting, u64->u128 zero-extension)"
  - "An OBSERVED merge route (temp_dir probe inherited from 03-01) + a DERIVED over-budget budget, so no arm of any test can silently run on the wrong merge path"
  - "merged_database_accounts_for_every_input_kmer_on_both_routes in merge_routing_tests.rs — header accounting + total-count conservation on both routes (the invariants a silent partial merge breaks)"
  - "Mutation-verified (non-vacuous) evidence: 4 deliberate defects injected into production code, each caught by a specific test in this plan"
  - "Full Wave-2 gate GREEN: cargo test --all, all 7 named binaries, clippy -D warnings on BOTH crates, cargo build --release (panic=\"abort\" preserved)"
  - "3 new entries in .planning/phases/03-memory-safety/deferred-items.md + a created .planning/WINDOWS.md ledger (open_count: 0)"
affects: [03-05, phase-04-benchmark, /gsd-verify-work]

actuals:
  tokens: 10152
  tasks: 1
  commits: 1

tech-stack:
  added: []
  patterns:
    - "Cross-plan composition gate: when two sibling plans each swap half a data path, the gate that matters is neither plan's own tests but the composition test, and its u128 arm must be the COMMITTED pre-refactor fixture (not a counter re-run), so a divergence localizes to the count stage or the merge stage instead of staying ambiguous between the two plans"
    - "Prove the route, don't assume it: a budget constant hard-coded to look 'tiny' is not a routing guarantee — the budget must be derived from the estimator AND the route asserted behaviorally, or every assertion on that arm is vacuous"
    - "Mutation-test the gate you are adding: injecting the exact bug class a prior plan fixed into the code under test and confirming the new test fails is the only evidence that a GREEN test means anything"

key-files:
  created:
    - tests/dense_merge_integration_tests.rs
    - .planning/WINDOWS.md
  modified:
    - tests/merge_routing_tests.rs
    - .planning/phases/03-memory-safety/deferred-items.md

key-decisions:
  - "The u128 arm of the composition differential is the committed Phase 1/2 golden .rkdb (D-10), not a second KmerCounter run. The plan offered 'forced-u128 constructor OR golden fixture, preferred if no constructor was exposed'; 03-03 exposed none, and the fixture is the better reference anyway — it is what production emitted BEFORE any of Phase 3, so it is independent of the code under test. A pre-merge equality assertion then separates a count-stage bug from a merge-stage bug rather than leaving the failure ambiguous between the two plans."
  - "The merge route is OBSERVED, not assumed. `observed_route` reuses 03-01's nonexistent-`temp_dir` probe, and the over-budget budget is DERIVED from `RKDatabase::estimate_total_kmers` rather than hard-coded. A first draft used `max_memory_usage: 1024`; the golden fixture's 20 unique k-mers estimate to 960 bytes, so every 'streaming' arm silently ran the in-memory path and the entire composition claim was vacuous. A mutation test found it; the docstring now records the trap so the next plan does not repeat it."
  - "The in-memory arm pairs HUGE_BUDGET_BYTES with `merge_mode: \"auto\"`, never `\"memory\"`. With `\"memory\"` an over-budget merge returns Err from the D-02 *reject*, which is indistinguishable from a temp-file failure by outcome alone, so `observed_route` would misreport the route. 03-01 already owns `merge_mode: \"memory\"` behavior; this plan's job is the composition, not re-testing the reject."
  - "Composition is asserted as a 4-WAY decoded-map equality (u64/u128 x in-memory/streaming), not pairwise. 03-01 made route selection budget-dependent, so a claim covering one route is half a claim — and cross-arm equality is what would catch a route-specific regression the per-arm exactness assertions miss."
  - "Every assertion pins exact k-mer COUNTs and header accounting; none asserts merely 'non-empty'. This is the direct lesson of 03-01's two data-loss bugs, which survived because `test_merge_streaming_basic` asserted only non-emptiness (200 k-mers in, 5 out). The new `merged_database_accounts_for_every_input_kmer_on_both_routes` extends that to whole-database invariants (header undercounting, count conservation) that neither union-size nor spot-checked counts can see."
  - "The count.rs write path is REPLICATED (its own DatabaseHeader literal + KmerEntry::write_to) rather than delegated to `RKDatabase::from_kmer_pairs`. The binary is asserting about what the count command actually emits; delegating to a different writer would make the assertion about something production does not do."
  - "The `modelled_bytes` assertion moved from a per-entry ratio to the exact modelled total (`unique_kmers * 36`), which is stronger and also dodges a clippy `manual_checked_ops` denial on the guard division."
  - "Only `tests/merge_routing_tests.rs` was edited from 03-01's output: 03-01 Task 2 deferred nothing explicitly, so rather than pad the file, the single added test is the whole-database cross-validation the plan asked for (header accounting + count conservation), which is also the invariant shape of the known-open prefix-cache defect (a)."

patterns-established:
  - "Mutation-proven gates: for a verification-only plan, the deliverable is not 'tests pass' but 'tests can fail'. Each mutation below was injected into production code, the plan's own tests were run, and the specific failing assertion recorded."
  - "Assertion localization over assertion bulk: `decoded_map_differs` prints the first 5 differing k-mers with both values instead of dumping two 200-entry maps, so a future regression names the offending k-mer."
  - "Copying a test fixture programmatically, not by transcription: GOLDEN_INPUT was spliced from tests/golden_generate.rs and diffed byte-identical. Plan 03-03 lost a cycle to a 2-character slip in this same constant, and because the sequences are repetitive the slip still yields a valid-looking k-mer set."

requirements-completed: [MERGE-01, MERGE-02, DENSE-02, DENSE-03]

coverage:
  - id: D1
    description: "Cross-plan composition proven: counting k<=32 via the dense u64 path, writing the resulting .rkdb, and merging it through the bounded dispatcher produces the same decoded (kmer-string, count) map as the u128 golden .rkdb merged the same way"
    requirement: DENSE-03
    verification:
      - kind: integration
        ref: "tests/dense_merge_integration_tests.rs#dense_count_then_merge_matches_u128_merge_k21 (4-way decoded-map equality across u64/u128 x in-memory/streaming, plus a pre-merge equality that localizes a divergence to the count stage or the merge stage)"
        status: pass
      - kind: integration
        ref: "mutation: drop the first k-mer merge_databases_streaming emits -> dense_count_then_merge_matches_u128_merge_k21 FAILS"
        status: pass
      - kind: integration
        ref: "mutation: drop one k-mer merge_databases_inmemory absorbs -> dense_count_then_merge_matches_u128_merge_k21 FAILS"
        status: pass
    human_judgment: false
  - id: D2
    description: "DENSE-02 holds end-to-end: the 12 committed golden .rkdb still sha256-match the manifest after BOTH 03-01 and 03-03, and the dense u64->u128 zero-extension is intact on the merge OUTPUT (not only on pre-existing fixtures)"
    requirement: DENSE-02
    verification:
      - kind: integration
        ref: "tests/golden_sha256_tests.rs#golden_rkdb_sha256_unchanged_post_dense (2/2 over all 12 fixtures) + tests/golden_tests.rs (34/34)"
        status: pass
      - kind: integration
        ref: "tests/dense_merge_integration_tests.rs#dense_merge_output_preserves_rkdb_v2_layout (raw magic + version bytes, data_offset == 42, len == 42 + 20*n, header/record agreement, write->read round trip)"
        status: pass
      - kind: integration
        ref: "mutation: KmerKey::U64(v) => (*v as u128) | (1u128 << 100) in src/hash/key.rs -> dense_merge_output_preserves_rkdb_v2_layout FAILS on the k-mer >> 64 == 0 assertion"
        status: pass
    human_judgment: false
  - id: D3
    description: "MERGE-02's hard route composes with the dense counter: an over-budget `auto` merge completes without OOM or Err, returns the exact k-mer union with summed counts, and its header accounts for every record"
    requirement: MERGE-02
    verification:
      - kind: integration
        ref: "tests/dense_merge_integration_tests.rs#bounded_merge_completes_on_synthetic_over_budget_input (exact union + per-k-mer summed counts + header total_kmers == records, with assert_route proving the streaming route was entered)"
        status: pass
      - kind: integration
        ref: "tests/merge_routing_tests.rs#merge_over_budget_hard_routes_to_streaming (03-01, still GREEN)"
        status: pass
    human_judgment: false
  - id: D4
    description: "MERGE-01 holds: the streaming route MERGE-01 promotes to default returns data interchangeable with the retained in-memory fast path, on real k=21 k-mers counted through the dense path"
    requirement: MERGE-01
    verification:
      - kind: integration
        ref: "tests/dense_merge_integration_tests.rs#bounded_merge_completes_on_synthetic_over_budget_input (streaming result == in-memory result for the same inputs, asserted)"
        status: pass
      - kind: integration
        ref: "tests/merge_routing_tests.rs#merged_database_accounts_for_every_input_kmer_on_both_routes (count conservation + header accounting on both routes)"
        status: pass
    human_judgment: false
  - id: D5
    description: "No merge can silently undercount itself: header.total_kmers equals the records present and total counts are conserved, on both merge routes"
    requirement: MERGE-01
    verification:
      - kind: integration
        ref: "tests/merge_routing_tests.rs#merged_database_accounts_for_every_input_kmer_on_both_routes"
        status: pass
      - kind: integration
        ref: "mutation: from_kmer_pairs writes total_kmers: entries.len() - 1 -> merged_database_accounts_... FAILS on the header/records assertion"
        status: pass
      - kind: integration
        ref: "mutation: streaming drops a k-mer -> merged_database_accounts_... FAILS on the count-conservation assertion"
        status: pass
    human_judgment: false
  - id: D6
    description: "All Wave-0 phase-3 test files are GREEN with no remaining #[ignore] attributes, and the 5 files' tests each report 0 ignored"
    requirement: DENSE-02
    verification:
      - kind: other
        ref: "grep -rnE '^\\s*#\\s*\\[\\s*ignore' over the 5 phase-3 test files -> no matches"
        status: pass
      - kind: other
        ref: "cargo test --test {merge_routing,merge_cleanup,dense_differential,dense_proptest,golden_sha256}_tests -> 0 ignored in every binary"
        status: pass
    human_judgment: false
  - id: D7
    description: "Phase 1/2 regressions: the full Rust suite is green and clippy -D warnings is clean on BOTH the root crate and the pyo3 crate"
    requirement: DENSE-02
    verification:
      - kind: other
        ref: "cargo test --all -> exit 0 (221 lib + 34 golden + 26 merge_cleanup + 26 merge_routing + 23 round_trip + 20 mod + 8 property + 6 dense_differential + 5 cjk + 4 parallel_count + 3 dense_merge_integration + 3 dense_proptest + 3 legacy + 2 golden_sha256 + 2 consistency, 0 failures)"
        status: pass
      - kind: other
        ref: "cargo clippy --all-targets -- -D warnings (root) -> exit 0"
        status: pass
      - kind: other
        ref: "(cd pyo3 && cargo clippy --all-targets -- -D warnings) -> exit 0"
        status: pass
      - kind: other
        ref: "cargo build --release -> exit 0; [profile.release] panic = \"abort\" unchanged (Cargo.toml untouched)"
        status: pass
      - kind: integration
        ref: "tests/parallel_count_tests.rs (4/4 + differential_threads_1_vs_n) -> Phase 2 PCOUNT-04 not regressed"
        status: pass
    human_judgment: false
  - id: D8
    description: "Human-scale memory bound: an over-budget merge of a real human genome completes within its declared budget"
    verification: []
    human_judgment: true
    rationale: "CI has no human-scale dataset. Every bound in this plan is proven at toy scale with a budget DERIVED from the real estimator (03-01's 'bounding proof over scale proof' approach), which proves the routing LOGIC but not the physical memory ceiling. A human must confirm the end-to-end bound against a real dataset — which is plan 03-05 / Phase 4's benchmark (CRR1936095), not a test that could exist here. Carried forward from 03-01's coverage item D7 and 03-03's D8; this plan re-confirms rather than closes it."
  - id: D9
    description: "Cleanup of streaming-merge temp chunks under panic=\"abort\" / SIGKILL (the orphan sweep does not cover loose *.chunk files)"
    verification: []
    human_judgment: true
    rationale: "Only the NORMAL path is machine-checkable. A probe merge in this plan left no strays in config.temp_dir (TempFileManager's Drop works), so what remains open is exclusively the abort/SIGKILL case, where the process cannot assert anything about itself. 03-02 logged this; this plan narrowed its scope (normal path confirmed clean) but cannot close it. Confirm by SIGKILLing a real large streaming merge and checking whether the next run reclaims the chunks."

# Measured at SUMMARY-write time from the ledger at `.git/gsd-plan-head-before-03-04`
# (written before the first commit). `commits: 1` is the single TASK commit. This
# SUMMARY's own commit plus the STATE/ROADMAP/REQUIREMENTS close-out commit follow
# and cannot appear in this field without changing the value being measured:
# So `git rev-list --count 95d846d..HEAD` = 3 once both land. (03-01/03-02 record
# `commits: 4` and 03-03 records `commits: 2` for the same documented reason.)
commits: 1
plan_head_before: 95d846da8d617f0f66dec85d25f9d785447d499f
plan_head_after: f54f099e9af13888034745b182772deaa3ac297f

duration: 10min
completed: 2026-10-07
status: complete
---

# Phase 3 Plan 4: Cross-Plan Composition Gate (Dense Counter × Bounded Merge) Summary

**Counting k-mers through the new dense `u64` path and then merging the resulting `.rkdb` through the bounded dispatcher now provably yields the same data as the unchanged `u128` path — on both merge routes, with exact counts and a v2 layout that is asserted on merge *output*, not just on pre-existing fixtures.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-10-07T02:58:43Z
- **Completed:** 2026-10-07T03:08:22Z
- **Tasks:** 1
- **Files modified:** 4

## Accomplishments

- **`tests/dense_merge_integration_tests.rs` (new, 3 tests).** The trust chain neither 03-01 nor 03-03 can test alone — `KmerCounter` (u64 in RAM) → `.rkdb` v2 write (u128 on disk) → `merge_databases` (bounded admission control) → `.rkdb` read → decoded `(String, u32)` map — is now a single assertion. Threat T-03-13's mitigation is a real test, not a claim.
  - `dense_count_then_merge_matches_u128_merge_k21` — counts `GOLDEN_INPUT` at k=21 canonical through the **u64** encoder family into a real `.rkdb` via a replica of `count.rs::output_binary_format`, takes the **u128** arm from the committed Phase 1/2 golden fixture (D-10), and requires all **four** arms (u64/u128 × in-memory/streaming) to produce identical decoded maps — plus a **pre-merge** equality that localizes any divergence to the count stage or the merge stage.
  - `dense_merge_output_preserves_rkdb_v2_layout` — the v2 guarantee is asserted on merge *output*, which no existing test covered: raw magic bytes, raw version `2`, `data_offset == 42` via the crate's own reader, `len == 42 + 20·n`, header `total_kmers` agreeing with both the record count and `estimate_total_kmers`, a write→read round trip, and `kmer >> 64 == 0` on every key (the u64→u128 zero-extension, which is the *only* thing DENSE-02 actually promises).
  - `bounded_merge_completes_on_synthetic_over_budget_input` — the MERGE-01/MERGE-02 end-to-end proof: an over-budget `auto` merge completes with the **exact** union and summed per-k-mer counts, its header accounts for every record, and the streaming result equals the in-memory result for the same inputs.
- **The tests are mutation-proven non-vacuous.** Four deliberate defects were injected into production code; each is caught by a named assertion:
  | Injected defect | Caught by |
  |---|---|
  | streaming merge drops its first emitted k-mer | `dense_count_then_merge_matches_u128_merge_k21`, `bounded_merge_completes_...`, `merged_database_accounts_...` |
  | in-memory merge drops one k-mer | `dense_count_then_merge_matches_u128_merge_k21`, `bounded_merge_completes_...` |
  | `KmerKey::U64` widening gains a spurious high bit | `dense_merge_output_preserves_rkdb_v2_layout` |
  | `from_kmer_pairs` writes `total_kmers - 1` | `merged_database_accounts_for_every_input_kmer_on_both_routes` |
- **`merged_database_accounts_for_every_input_kmer_on_both_routes`** added to `tests/merge_routing_tests.rs` (25 → 26 tests). 03-01's four routing tests pin union *size* and spot-checked counts; nothing pinned the two whole-database invariants a merge can break without changing either — **header accounting** (a merge that silently skips work returns `Ok` and writes a structurally valid `.rkdb` that undercounts itself) and **total-count conservation** (a dropped or double-counted k-mer moves the total even when the k-mer *set* is unchanged). Both are now asserted on both routes. This is the exact invariant shape of the known-open prefix-cache defect, so it is a guard rather than a fix.
- **Wave-2 gate GREEN.** `cargo test --all` exit 0; all 7 named binaries exit 0; clippy `-D warnings` exit 0 on **both** the root crate and `pyo3/`; `cargo build --release` exit 0 with `[profile.release] panic = "abort"` untouched.
- **All Wave-0 phase-3 stubs are resolved** — zero `#[ignore]` attributes across the 5 phase-3 test files; every binary reports `0 ignored`.

## Task Commits

1. **Task 1: Wave-2 gate audit + dense+merge end-to-end integration test** — `f54f099` (test)

**Plan metadata:** (this commit)

## Files Created/Modified

- `tests/dense_merge_integration_tests.rs` (new, 730 lines) — the 3 composition tests plus their helpers: `count_via_u64_path_then_write_rkdb` (u64-encoder count → real `.rkdb` through a replica of the count.rs write path), `golden_u128_db` (D-10 fixture as ground truth), `decoded_map_from_rkdb` / `decoded_map_from_pairs` (D-04 decoded-level comparison), `decoded_map_differs` (failure localization), `observed_route` / `assert_route` (behavioral route proof), `over_budget_config` (budget derived from the estimator).
- `tests/merge_routing_tests.rs` (modified) — one added cross-validation test; no existing test touched.
- `.planning/phases/03-memory-safety/deferred-items.md` (modified) — 3 new entries (§"Added by plan 03-04").
- `.planning/WINDOWS.md` (created) — broken-windows ledger; `open_count: 0` after waiving 3 non-defect entries.

## Decisions Made

- **The u128 arm is the committed golden `.rkdb`, not a second `KmerCounter` run.** The plan allowed "forced-u128 constructor OR golden fixture, preferred if no constructor was exposed"; 03-03 exposed none, and the fixture is the better reference regardless — it is what production emitted *before any of Phase 3*, so it is independent of the code under test. The pre-merge equality assertion then turns an ambiguous two-plan failure into "count stage or merge stage".
- **Prove the route; never assume it.** `observed_route` reuses 03-01's nonexistent-`temp_dir` probe and the budget is **derived** from `RKDatabase::estimate_total_kmers`. See Deviation 1 — a hard-coded constant made the whole plan vacuous, and only a mutation test caught it.
- **The in-memory arm pairs `HUGE_BUDGET_BYTES` with `merge_mode: "auto"`, never `"memory"`.** With `"memory"`, an over-budget merge returns `Err` from the D-02 *reject*, which is indistinguishable by outcome from a temp-file failure, so the route probe would misreport. 03-01 already owns `merge_mode: "memory"` behavior.
- **4-way equality, not pairwise.** 03-01 made route selection budget-dependent, so a claim covering one route is half a claim; cross-arm equality also catches route-specific regressions that per-arm exactness assertions would miss.
- **Exact counts and header accounting everywhere; never "non-empty".** This is the direct lesson of 03-01's two data-loss bugs, which survived because `test_merge_streaming_basic` asserted only non-emptiness (200 k-mers in, 5 out).
- **The count.rs write path is replicated, not delegated** to `RKDatabase::from_kmer_pairs` — the binary asserts about what the count command actually emits.
- **`modelled_bytes` asserts the exact total** (`unique_kmers * 36`) rather than a per-entry ratio: strictly stronger, and it avoids a clippy `manual_checked_ops` denial on a guard division.
- **`mod common;` omitted** from the new binary (same reasoning as `dense_differential_tests.rs`): it needs none of the shared factories, and importing them would register ~20 unrelated helper tests in the output.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Every "streaming" arm of the composition test was silently running the in-memory path, making the whole plan vacuous**
- **Found during:** Task 1 — a mutation run. Injected "drop the first k-mer the streaming merge emits" into `merge_databases_streaming` and all 3 new tests still passed.
- **Issue:** The plan's own text said `MergeConfig with max_memory_usage = 1024 (forcing the streaming route per 03-01)`, and the first draft copied that constant. But `merge_databases` only streams when `estimated_memory = total_kmers * 24 > max_memory_usage`, and the golden fixture's k=21 canonical set has just **20 unique k-mers** → 20 × 24 = **960 bytes < 1024**. Every "streaming" arm was an in-memory merge wearing a streaming label, so the cross-plan composition claim — the entire deliverable of this plan — was asserting nothing about the streaming path. In the small-input test the gap was wider still (5 k-mers → 240 bytes estimated).
- **Why in scope:** this plan's sole deliverable is proof that the two swaps compose; a vacuous gate is worse than no gate, because it reports the phase verified.
- **Fix:** Two changes, both now documented in the helper docstrings so the trap is inherited rather than rediscovered:
  1. `over_budget_config` **derives** the budget from `RKDatabase::estimate_total_kmers` (`estimated_bytes - 1`), so the hard route fires regardless of fixture size;
  2. `observed_route` / `assert_route` **prove** which path ran, reusing 03-01's nonexistent-`temp_dir` probe (streaming must create a chunk file there → `Err`; in-memory never touches `temp_dir` → `Ok`). Every test now asserts its own route, so a future fixture-size change that pushed an arm back under budget fails loudly instead of silently going vacuous.
- **Files modified:** `tests/dense_merge_integration_tests.rs`
- **Verification:** re-ran all four mutations after the fix — the streaming-drop and in-memory-drop mutations now each fail 2 of 3 tests, and the high-bit-widening mutation fails the layout test. All mutations reverted; `git diff HEAD -- src/` is empty.
- **Committed in:** `f54f099`

**2. [Rule 2 - Missing Critical] Added whole-database cross-validation (header accounting + count conservation) that 03-01 left uncovered**
- **Found during:** Task 1, (a) — auditing `tests/merge_routing_tests.rs` for deferred assertions.
- **Issue:** 03-01 deferred nothing explicitly, so the plan's instruction was ambiguous. But auditing its four routing tests showed a real gap: each pins union *size* and spot-checks two counts, and none pins the invariants a merge can violate without changing either. The live prefix-cache defect 03-02 logged — `merge_prefix_buckets` logs bucket failures but returns `Ok(())`, writing a valid `.rkdb` with an undercounted `total_kmers` — is exactly this shape, and would pass every existing routing test.
- **Why in scope:** the plan's `files_modified` lists this file for "cross-validation assertions", and Rule 2 covers critical missing correctness coverage. A silent undercount is the failure mode most likely to survive to production precisely because every reader trusts the header.
- **Fix:** Added `merged_database_accounts_for_every_input_kmer_on_both_routes`, asserting on both routes that `header.total_kmers` equals the records present, the output is canonical v2 with `sorted` set, merged counts sum to the inputs' total, and the invariant survives write→read and agrees with `estimate_total_kmers`.
- **Files modified:** `tests/merge_routing_tests.rs`
- **Verification:** 25 → 26 tests GREEN; the header-undercount mutation and the streaming-drop mutation each fail it with the intended assertion.
- **Committed in:** `f54f099`

**3. [Rule 1 - Bug] Re-transcribed `GOLDEN_INPUT` with the same 2-character drift plan 03-03 hit**
- **Found during:** Task 1 — a `diff` against `tests/golden_generate.rs` before the first test run.
- **Issue:** Sequence 3 came out 68 characters instead of 66 — byte-identical to the drift 03-03 recorded for this exact constant. Because the fixture sequences are repetitive, the slip still produces a valid-looking k-mer set; here it would have failed loudly (the decoded-map comparison against the golden `.rkdb` would not match) but only after a confusing debugging cycle.
- **Fix:** Spliced the array body programmatically from `tests/golden_generate.rs` and verified byte-identity by `diff`. The doc comment now carries the verify command and states the constant must be copied programmatically, never by hand.
- **Files modified:** `tests/dense_merge_integration_tests.rs`
- **Verification:** `diff <(sed -n '40,45p' tests/golden_generate.rs) <(sed -n '117,122p' tests/dense_merge_integration_tests.rs)` — identical modulo indentation.
- **Committed in:** `f54f099`

**4. [Rule 3 - Blocking] Worked around a clippy `manual_checked_ops` denial in the new test**
- **Found during:** Task 1 acceptance-criteria gate — `cargo clippy --all-targets -- -D warnings` failed on the new binary.
- **Issue:** `modelled_bytes_per_entry: if unique_kmers == 0 { 0 } else { counter.memory_usage() / unique_kmers }` is exactly the shape `clippy::manual_checked_ops` flags (it wants `checked_div`), and the plan lists that command as a blocking acceptance criterion.
- **Fix:** Returned the raw `memory_usage()` total and moved the guard out of the helper, asserting `modelled_bytes == unique_kmers * DENSE_BYTES_PER_ENTRY` in the test. Strictly stronger than the per-entry ratio the plan sketched, and no manual checked-op.
- **Files modified:** `tests/dense_merge_integration_tests.rs`
- **Verification:** `cargo clippy --all-targets -- -D warnings` exit 0 on root; `(cd pyo3 && ...)` exit 0.
- **Committed in:** `f54f099`

---

**Total deviations:** 4 auto-fixed (2 Rule 1 bugs, 1 Rule 2 missing coverage, 1 Rule 3 blocking)
**Impact on plan:** Deviation 1 is the important one: without it this plan would have reported the cross-plan composition *verified* while every one of its assertions ran on the in-memory path. Deviation 2 adds coverage the plan asked for but did not specify. Deviations 3 and 4 are test-authoring and lint-gate issues. No production code was modified — `git diff HEAD -- src/` is empty — which is correct: the plan is pure verification, and the value delivered is a gate that provably fails when the thing it guards breaks.

## Issues Encountered

- **The plan's acceptance criterion for AC1 is a grep that matches prose.** `grep -rn '#\[ignore]'` over the 5 phase-3 test files returns 3 matches — all inside `//!`/`///` doc comments *describing* Wave-0 history ("began `#[ignore]`d so the target compiled against the PRE-fix API"). There are **zero** `#[ignore]` attributes in those files: the attribute-shaped grep (`grep -rnE '^\s*#\s*\[\s*ignore'`) returns no matches and every binary reports `0 ignored`. Logged to `deferred-items.md` and to `.planning/WINDOWS.md` (waived, `open_count: 0`) so `/gsd-verify-work` classifies them as closed rather than open. The doc comments were deliberately **kept** — the history is worth having — and the two genuine repo-wide `#[ignore]`s (`tests/golden_generate.rs:169`, `tests/parallel_count_tests.rs:229`) are the Phase 1/2 run-once generators this plan is explicitly not authorized to un-ignore.
- **Deferred-item (c) refined, not closed.** 03-02 logged that streaming-merge chunks "land loose in temp_dir and are NOT covered by the orphan sweep". A probe merge here (8 k-mers, `chunk_size: 2`, real temp dir) left **no** strays behind — `TempFileManager`'s `Drop` is correct on the normal path. So the open half is *only* the sweep-coverage gap under `panic = "abort"` / SIGKILL. Logged with the narrowed scope so nobody re-investigates the RAII path.
- **Deferred items (a) and (b) not hit.** The prefix-cache path (`merge_prefix_buckets`, `external_sort_merge_output.tmp`) was never exercised — `use_prefix_cache` defaults false and no test here enables it. Both remain open and are still **not** this plan's to fix.
- **In-memory MERGE of two k=21 databases still gets no DENSE-01 memory win.** Confirmed, as 03-03 predicted: `merge_databases_inmemory`'s `HashMapBrown<u128, u32>` accumulator is untouched. The gate verifies the *actual current composition*, not an idealized one; this remains a deferred item for a follow-up.
- `cargo` is not on the default `PATH` here; `export PATH="$HOME/.cargo/bin:$PATH"` is needed per invocation, and `gsd_run` lives at `.opencode/gsd-core/bin/`. Same as 03-01/03-02/03-03.
- `rustfmt` was run on the two touched files individually, never `cargo fmt` — the latter sweeps `src/cli/commands/count.rs` as a side effect (documented hazard in `deferred-items.md`). After formatting, `cargo fmt --all --check` reports drift in exactly the two pre-existing files and nothing else.

## Known Stubs

None. All 3 new tests and the 1 added test are GREEN, `0 ignored`, no `TODO`/`FIXME`/`todo!()`, no placeholder text, no unwired data source. The two `#[ignore]`d tests in the repo are the Phase 1/2 run-once fixture generators, pre-existing and out of scope.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **The Wave-2 gate is clear.** Phase 3's four Wave-1 plans now compose into a single proven claim: DENSE-01/02/03 (counting memory halved, `.rkdb` v2 byte-identical, canonicalization correct) and MERGE-01/02/03 (bounded estimator, hard route, RAII temp lifecycle) all hold together, with no Phase 1/2 regressions and clippy clean on both crates.
- **03-05 (MERGE-04, `PyDatabase.merge`) is unblocked and low-risk.** `merge_databases` is unchanged by this plan; the new tests are test-only, so `PyDatabase.merge` inherits the corrected bounded dispatch exactly as 03-01 predicted.
- **Phase 4's benchmark is the remaining human-judgment item** (coverage D8/D9): the physical memory ceiling at human scale, and `memory_usage()` being a model rather than a measurement. Neither is machine-checkable here, and both are exactly what a benchmark against CRR1936095 is for.
- **For downstream planners:** `merge_databases` remains the single admission-control point; nothing in this plan added a public symbol. If you write a phase test that needs to exercise a *specific* merge path, use `observed_route`/`over_budget_config` from `tests/dense_merge_integration_tests.rs` rather than a budget constant — the constant is wrong more often than it looks right.
- **Open defects carried forward unchanged** (all pre-existing, none introduced here): `merge_prefix_buckets` silent partial merge; `external_sort_merge_output.tmp` outside the process-unique subdir and never deleted; loose `rustkmer_sort_*.chunk` files not covered by the orphan sweep (normal-path cleanup confirmed working, abort-path coverage still open); the dense `u64` width not applied to the in-memory merge accumulator or the `RKDatabase` read path; `memory_usage()` modelled not measured; `cargo fmt --all --check` drift in `src/cli/commands/count.rs` + `tests/parallel_count_tests.rs` (a Phase 1 CI gate failure independent of Phase 3).

---

## Self-Check: PASSED

- **Files verified on disk:** `tests/dense_merge_integration_tests.rs`, `tests/merge_routing_tests.rs`, `.planning/phases/03-memory-safety/03-04-SUMMARY.md`, `deferred-items.md`, `.planning/WINDOWS.md` ✓
- **Commits verified present in history:** `f54f099` (task), `bc2db7d` (SUMMARY), `7098752` (STATE/ROADMAP/REQUIREMENTS) ✓
- **`commits: 1` is MEASURED** via `git rev-list --count 95d846d..HEAD` (ledger at `.git/gsd-plan-head-before-03-04`, written before the first commit) = **3** at SUMMARY-close time: 1 task + this SUMMARY commit + the STATE/ROADMAP commit. The frontmatter records the *task* count with the derivation documented inline, matching the 03-01/03-02/03-03 convention.
- **Production code untouched:** `git diff 95d846d..HEAD --stat -- src/ pyo3/ Cargo.toml` is **empty**. All 4 mutation defects injected during verification were reverted before the task commit.
- **All Task 1 acceptance criteria re-run, each with its actual result:**
  | Criterion | Result |
  |---|---|
  | No `#[ignore]` attributes in the 5 phase-3 test files | PASS — attribute-shaped grep returns zero matches; every binary reports `0 ignored` (the plan's *literal* grep returns 3 doc-comment prose hits; see Issues Encountered) |
  | `cargo test --test dense_merge_integration_tests` exits 0 | PASS — 3 passed, 0 failed, 0 ignored |
  | `cargo test --all` exits 0 | PASS — 221 lib + 34 golden + 26 merge_cleanup + 26 merge_routing + 23 round_trip + 20 mod + 8 property + 6 dense_differential + 5 cjk + 4 parallel_count + 3 dense_merge_integration + 3 dense_proptest + 3 legacy + 2 golden_sha256 + 2 consistency, 0 failures |
  | `cargo test --test parallel_count_tests` exits 0 (PCOUNT-04 not regressed) | PASS — 4 passed, 0 failed (+1 pre-existing Phase 2 ignored baseline-capture generator) |
  | `cargo test --test golden_sha256_tests` exits 0 (DENSE-02 byte-identity) | PASS — 2 passed over all 12 fixtures; `golden_tests` 34/34 |
  | `cargo clippy --all-targets -- -D warnings` (root) exits 0 | PASS |
  | `(cd pyo3 && cargo clippy --all-targets -- -D warnings)` exits 0 | PASS |
  | `cargo build --release` exits 0 (`panic="abort"` preserved) | PASS — `Cargo.toml` unmodified; `[profile.release] panic = "abort"` intact |
  | `rustfmt` clean on both touched test files | PASS — `cargo fmt --all --check` drift is confined to the two documented pre-existing files (`src/cli/commands/count.rs`, `tests/parallel_count_tests.rs`) |
- **Non-vacuity verified by 4 mutations** (all reverted): streaming k-mer drop, in-memory k-mer drop, dense widening high bit, header undercount — each fails a specific named assertion. A 5th check confirmed a *passing* mutation (the `max_memory_usage: 1024` routing mistake) revealed that the original version of these tests asserted nothing about the streaming path.
- **Ship gate not blocked:** `.planning/WINDOWS.md` `open_count: 0` (3 entries waived with reasons; none is an open defect).

---
*Phase: 03-memory-safety*
*Completed: 2026-10-07*