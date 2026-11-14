---
phase: 08-output-pipeline-rkdb-v2-parity
plan: 03
subsystem: output-pipeline
tags: [rust, differential-testing, proptest, mutation-testing, byte-identity, out-03]

requires:
  - phase: 08-output-pipeline-rkdb-v2-parity
    provides: "08-01 consuming pair collection, in-place par_sort_unstable, streaming through the frozen writer; sorted k21/canon bytes a5da813e…"
  - phase: 08-output-pipeline-rkdb-v2-parity
    provides: "08-02 six-cell four-arm byte differential, DatabaseQuery + prefix-query sortedness, frozen fixture manifest f010e42a…"

provides:
  - "tests/output_differential_matrix_tests.rs — explicit 12-cell k {21,32,64} x canonical {on,off} x threads {1,4} old-vs-new matrix in text and binary, with old frozen-writer byte equality, t1/t4 byte identity, and non-vacuous skip-N parity"
  - "Output-boundary disjointness/conservation proptest over the exact structures the writer consumes (for_each_count visit-once, pair count == unique_kmers, count sum == total_kmers, strict ascending after sort, filter semantics == filtering_stats, run-to-run identity)"
  - "scripts/bench/mutation_red.py — mechanical exact-unique mutation driver with injectable runner, restore-in-finally, git blob verification, fixed evidence shape, 0/1/2 exit contract"
  - "scripts/bench/tests/test_mutation_red.py — 16 stdlib unit tests for unique-match enforcement, restore-in-finally, verdict matrix, spec validation, and evidence-excerpt provenance"
  - "08-mutation-spec.json + phase8_mutation_red.json — ordering (3/3 gates RED), duplication (2/2 RED), overflow (1/1 RED), every gate green after restore, VERDICT GREEN"

affects: [08-04, 10]

actuals:
  tokens: 18219
  tasks: 3
  commits: 3
  plan_head_before: 097dfc902df4a7b71594a26756864d789338b66b
  plan_head_after: 3c08171de1a3ca30b6e98f18ba767e27aa99aaab

tech-stack:
  added: []
  patterns:
    - "The differential matrix enumerates cells EXPLICITLY and asserts the count is 12, so a later refactor cannot silently narrow coverage"
    - "The old arm writes the same reference map through the frozen from_kmer_pairs writer; the new path must match it byte for byte per cell"
    - "Reference totals are pinned twice: the CLI's stderr `Total k-mers:` line and the header record count vs the sum of on-disk counts"
    - "Skip-N is represented by an encode error per naive window; the focused test pins the total to exactly the N-free window count"
    - "Mutation experiments require an exact-unique find string, record per-gate exit codes and failure excerpts from the observed output, and restore via finally + git blob equality"
    - "A gate that fails without its expected assertion text is exit 2, never a pass — a real RED is never masked as a spec bug"

key-files:
  created:
    - tests/output_differential_matrix_tests.rs
    - scripts/bench/mutation_red.py
    - scripts/bench/tests/test_mutation_red.py
    - .planning/phases/08-output-pipeline-rkdb-v2-parity/08-mutation-spec.json
    - .planning/phases/08-output-pipeline-rkdb-v2-parity/phase8_mutation_red.json
  modified: []

key-decisions:
  - "The 12 cells are a literal loop with an asserted counter (3 k values x 2 canonical modes x 2 thread counts); non-empty map and positive-total assertions make every cell non-vacuous"
  - "The binary arm additionally asserts records.len() == reference.len(), so a duplicated or lost record fails even if the header count happens to match"
  - "The N-bearing record is random LCG ACGT with one internal N at index 45, so exactly k windows cover it and the observed total must equal len-k+1-k — a regression that counts N windows changes the total, not just the key set"
  - "The proptest drives CountEngine directly at threads=4 on generated repeat-rich ACGT (a 40-base motif repeated four times), making min_count>1 filters non-vacuous for both k=21 and k=64"
  - "Mutation driver exit codes: 0 all gates RED then green; 1 a gate stayed green under mutation; 2 invalid setup (non-unique/missing find, malformed spec, restore mismatch, missing expected substring, gate not green after restore)"
  - "The driver's evidence excerpt is always a substring of the combined stdout+stderr of the actual failing gate run, proven by a unit test"
  - "The experiment ran on a clean src/ tree: pre-mutation blobs were count.rs 6e3038d8… and local.rs a002a573…, and both files hash back to those values after the run"

requirements-completed: [OUT-03]

coverage:
  - id: D1
    description: "Explicit 12-cell old-vs-new and 1-vs-N differential matrix reproduces the pre-refactor reference exactly in text and binary, with old frozen-writer byte equality, t1/t4 byte identity, and pinned skip-N semantics"
    requirement: OUT-03
    verification:
      - kind: integration
        ref: "tests/output_differential_matrix_tests.rs#old_vs_new_matrix_reproduces_the_reference_in_text_and_binary (12 cells asserted)"
        status: pass
      - kind: integration
        ref: "tests/output_differential_matrix_tests.rs#n_containing_record_skips_exactly_the_windows_that_cover_the_n"
        status: pass
    human_judgment: false
  - id: D2
    description: "Output-boundary disjointness and conservation proptest over the structures the writer consumes"
    requirement: OUT-03
    verification:
      - kind: integration
        ref: "tests/output_differential_matrix_tests.rs#proptest_output_boundary_disjointness_and_conservation (12 cases, k in {21,64} x canonical x min_count 1..=3)"
        status: pass
      - kind: integration
        ref: "cargo test --locked --test count_engine_tests (20 passed, existing partition-level proof still green)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Mechanical mutation-RED driver observes ordering, duplication, and overflow defects turn their named gates red, then restores the tree to green with matching blob hashes"
    requirement: OUT-03
    verification:
      - kind: unit
        ref: "python3 -m unittest discover -s scripts/bench/tests -t . -p test_mutation_red.py (16 passed)"
        status: pass
      - kind: e2e
        ref: "python3 scripts/bench/mutation_red.py run -> MUTATION VERDICT result=GREEN; ordering 3/3, duplication 2/2, overflow 1/1 gates observed RED; all restored_blob_matches=true; post_restore_exit=0"
        status: pass
      - kind: other
        ref: "git status --porcelain -- src/ empty; count.rs/local.rs git hash-object equal to pre-mutation values; output_pipeline_tests 9, rkdb_v2_byte_identity_tests 8, thread_local_count_tests 10 all green"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-11-13
status: complete
---

# Phase 8 Plan 03: Differential Matrix and Mutation-RED Summary

**Every cell of the k x canonical x threads matrix reproduces the pre-refactor reference exactly in both formats, the output boundary is proven disjoint and conserving, and three injected defects — inverted ordering, duplicated records, and a disabled overflow guard — each turned their named gates red before a verified restore.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-11-12T17:35:54Z
- **Completed:** 2026-11-12T17:41:49Z
- **Tasks:** 3
- **Files modified:** 5 (5 created, 0 modified)

## Accomplishments

- **12-cell matrix green.** For k ∈ {21, 32, 64} × canonical on/off × threads ∈ {1, 4}: the text map equals the decoded naive-window reference map, the parsed text arm's `Total k-mers:` / `Unique k-mers:` stderr lines equal the reference total and distinct count, the binary records decode to exactly the reference map, keys are strictly ascending, the record parse lands on the file end, the header record count equals the reference distinct keys, and the sum of on-disk counts equals the reference total. The cell counter is asserted to be exactly 12.
- **Old arm is byte-identical in every cell.** The reference pairs written through the frozen `RKDatabase::from_kmer_pairs(..).to_file_path(..)` writer match the new CLI path's bytes for all 12 cells, and threads=1 vs threads=4 produce byte-identical text and binary files.
- **Skip-N parity is pinned non-vacuously.** On a random 90-base record with one internal N at index 45, both `k=21` and `k=32` arms agree with the reference in text and binary; the observed count total equals exactly `len - k + 1 - k` (the N-free windows), so counting N-bearing windows would change the total. The distinct-key count is strictly below the naive window count.
- **Output-boundary proptest green.** The engine is driven directly on generated repeat-rich ACGT for k ∈ {21, 64} × canonical × `min_count` 1..=3. For every case: `for_each_count` visits each key once, `into_filtered_pairs(&None)` has length `unique_kmers` and count sum `total_kmers`, `sort_unstable_by` yields strictly ascending keys, the filtered set equals the passing set and `filtering_stats.kept_after`, and two identical runs yield the identical pair multiset. `min_count > 1` is asserted to drop at least one count-1 key.
- **Mutation-RED driver lands and proves the gates can fail.** The driver enforces an exact-unique find string, requires each named gate to exit nonzero with its expected assertion text, restores in a `finally`, verifies `git hash-object` equality, and re-runs every gate requiring exit 0. Its 16 unit tests cover zero/one/multiple matches, restore-on-raiser, the full verdict matrix, spec validation, and excerpt provenance. The full experiment printed:

  ```
  MUTATION ordering result=RED restored=ok
  MUTATION duplication result=RED restored=ok
  MUTATION overflow result=RED restored=ok
  MUTATION VERDICT result=GREEN
  ```

- **Observed RED evidence (from `phase8_mutation_red.json`).**

  | Mutation | Target | Gates RED | Observed assertion text |
  |---|---|---|---|
  | ordering | `|(a, _), (b, _)| a.cmp(b)` → `b.cmp(a)` in `src/cli/commands/count.rs` | 3/3 | `sorted .rkdb records must be strictly ascending by numeric key`; `… the new path no longer emits the golden bytes … are not byte-identical`; `DatabaseQuery disk binary search returned the wrong count for oracle key 0xf307741 (AAAAAAATTATAACTCTCAAC)` |
  | duplication | the single `KmerEntry::new(kmer, count).write_to(&mut writer)?;` expression written twice | 2/2 | `sorted .rkdb records must be strictly ascending by numeric key`; `the header record count must equal the records parsed from disk` |
  | overflow | wide-arm guard `if *count == self.max_count` → `if *count == self.max_count && false` in `src/hash/local.rs` | 1/1 | `attempt to add with overflow` (panic at the k=64 cell; the dense k=21 cell still passed) |

  Every gate recorded `observed_exit=101`, `expect_substring_seen=true`, and `post_restore_exit=0`. Both mutated files (`count.rs` blob `6e3038d8…` → `9eeb477c…`/`95597a5d…`, `local.rs` blob `a002a573…` → `42ddcbf6…`) hash back to their pre-mutation values (`restored_blob_matches=true`), and `git status --porcelain -- src/` is empty.
- **Guardrails held.** `src/database/format.rs` is still git blob `eb0d5bf2…`; `tests/fixtures/` untouched; no dependency or manifest change. MSRV 1.82 `cargo clippy --locked --all-targets -- -D warnings` is clean on both crates, the full `cargo test --locked` suite reports 31 green summaries with 0 failures, and the full harness discovery reports `Ran 361 tests … OK (skipped=1)`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Old-vs-new and 1-vs-N differential matrix across k, canonical, and threads** — `52d8c4a` (feat)
2. **Task 2: Disjointness and conservation properties at the output boundary** — `991c243` (feat)
3. **Task 3: Mutation-RED driver: observe ordering, duplication, and overflow defects turn named gates red** — `3c08171` (feat)

**Plan metadata:** the final docs commit with this SUMMARY, STATE.md, ROADMAP.md, and REQUIREMENTS.md.

## Files Created/Modified

- `tests/output_differential_matrix_tests.rs` — 611-line integration test: 12-cell old-vs-new matrix (`old_vs_new_matrix_reproduces_the_reference_in_text_and_binary`), focused skip-N proof (`n_containing_record_skips_exactly_the_windows_that_cover_the_n`), and the output-boundary proptest (`proptest_output_boundary_disjointness_and_conservation`).
- `scripts/bench/mutation_red.py` — 364-line stdlib driver: spec validation, exact-unique replacement, injectable gate runner and blob hasher, restore-in-finally, blob verification, fixed evidence document, machine-greppable lines, 0/1/2 exit contract.
- `scripts/bench/tests/test_mutation_red.py` — 394-line, 16-test stdlib suite; no cargo, no sleeps, all writes under a temp dir.
- `.planning/phases/08-output-pipeline-rkdb-v2-parity/08-mutation-spec.json` — the three mutation definitions with named gates and actual assertion substrings.
- `.planning/phases/08-output-pipeline-rkdb-v2-parity/phase8_mutation_red.json` — observed RED/GREEN evidence with per-gate exit codes, excerpts, and blob hashes.

## Decisions Made

- **Explicit matrix enumeration with an asserted counter.** The plan's blind-spot threat is held structurally: a narrowed loop fails `assert_eq!(cells, 12)`.
- **Two independent total checks.** The text arm pins the reference total to the non-quiet `Total k-mers:` line, and the binary arm pins the header record count and the sum of on-disk counts to the same reference values — an IN-03 inversion or a lost/duplicated record cannot pass both.
- **Random N record, not a repeat-rich one.** Using an LCG ACGT record with a single internal N makes the exact `len - 2k + 1` observation count meaningful; a repeat-rich record would make "distinct < naive windows" true for the wrong reason.
- **Proptest drives the engine, not the CLI.** The plan asks for the exact structures the writer consumes; running `CountEngine` in-process keeps the suite fast (12 short cases) while still exercising partition routing and reduction.
- **Gate-stayed-green is exit 1, spec-shape errors are exit 2.** A nonzero gate exit without the expected text is an invalid experiment, not a pass; restore mismatch and post-restore non-green are also exit 2. The outer verifier therefore cannot mistake a broken spec for evidence.
- **Mutation driver restores before re-running gates.** The `finally` restore happens first, then blob comparison, then every gate is re-run green — so a failed restore can never be reported as a green post-state.

## Deviations from Plan

None — the plan executed exactly as written.

## Issues Encountered

- The default nightly toolchain emits the pre-existing `AtomicU64::fetch_update` deprecation warning in `src/hash/table.rs` (not touched by this plan); the MSRV 1.82 clippy gate is clean.
- The new Rust test file was formatted with `rustfmt --edition 2021` before each commit; no other file was reformatted. The repository-wide `cargo fmt --all --check` drift recorded in `deferred-items.md` by 08-02 is unchanged and out of scope.

## Known Stubs

None. No placeholder values, skipped tests, or unrun verifications were introduced.

## Threat Flags

None beyond the plan's threat model. T-08-11 (claimed RED without observation) is held by recorded per-gate exit codes, expected-substring checks, and the driver's unit tests; T-08-12 (mutation left in the tree) by restore-in-finally, blob equality per file, the empty `git status --porcelain -- src/`, and green re-runs; T-08-13 (matrix blind spots/vacuous cells) by the explicit 12-cell counter, non-empty/positive assertions per cell, and the exact N-window count; T-08-14 (duplicates/lost keys) by the output-boundary proptest; T-08-SC by no dependency or manifest change and `--locked` throughout.

## Next Phase Readiness

- 08-04 can treat the 12-cell matrix, the output-boundary proptest, and `phase8_mutation_red.json` as the OUT-03 evidence set; the driver is reusable for later phases.
- The frozen writer (`format.rs` blob `eb0d5bf2…`), the 12 golden fixtures, and the manifests/lockfiles are unchanged.
- No blockers.

## Self-Check

- Created files verified present: `tests/output_differential_matrix_tests.rs`, `scripts/bench/mutation_red.py`, `scripts/bench/tests/test_mutation_red.py`, `08-mutation-spec.json`, `phase8_mutation_red.json`.
- Task commits verified as ancestors of HEAD: `52d8c4a`, `991c243`, `3c08171`.
- Frozen contracts: `git hash-object src/database/format.rs` = `eb0d5bf2…`; `tests/fixtures/` clean; `src/` blob hashes equal to the pre-mutation values.

## Self-Check: PASSED

---
*Phase: 08-output-pipeline-rkdb-v2-parity*
*Completed: 2026-11-13*
