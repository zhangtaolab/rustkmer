---
phase: 08-output-pipeline-rkdb-v2-parity
plan: 02
subsystem: output-pipeline
tags: [rust, rkdb-v2, byte-identity, golden-fixtures, binary-search, prefix-query, out-02]

requires:
  - phase: 08-output-pipeline-rkdb-v2-parity
    provides: "08-01 consuming pair collection, in-place par_sort_unstable, streaming through the frozen writer; sorted k21/canon output sha256 a5da813e…"
  - phase: 05-measurement-regression-harness
    provides: "12 pre-refactor golden fixtures + golden_manifest.sha256 (f010e42a…) captured before any hot-path refactor"

provides:
  - "tests/rkdb_v2_byte_identity_tests.rs — six-cell four-arm byte differential: new CLI path == committed pre-refactor fixture == frozen RKDatabase::from_kmer_pairs writer == hand-built 16+4 LE record bytes"
  - "Six unsorted cells proven content-equal (record multiset + totals) under a header with sorted=false"
  - "Fixture-integrity gate: manifest sha256 pinned to f010e42a, all 12 fixtures re-hashed, every write guarded outside tests/fixtures/"
  - "IN-03 asserted on data where the meanings differ: header total_kmers = record count (20), not the sum of counts (279) for the k21/canon golden cell"
  - "DatabaseQuery disk and preloaded binary-search answer parity: 500 sampled oracle keys, 500 reverse complements, 200 absent keys"
  - "Unsorted-disk negative control: query_kmer refuses with a named unsorted-database error; preloaded linear route still answers the full oracle"
  - "extract_prefix_optimized exact oracle subset and exact contiguous block bounds for all eight prefix cases; unsorted linear fallback parity"

affects: [08-03, 08-04, 10]

actuals:
  tokens: 11772
  tasks: 2
  commits: 2
  plan_head_before: fbd34e560ef4ba16db93a8d44adfd2e84b5336b6
  plan_head_after: eeefcc24ddc04c5ba5fdd6d823bf1dff73b77657

tech-stack:
  added: []
  patterns:
    - "Four independent arms over one oracle: real CLI (t1/t4), committed pre-refactor fixture, frozen canonical writer, hand-built byte reference"
    - "Sortedness proven by ANSWERS, not the flag: both binary-search consumers are driven from files the new counting path produced"
    - "Fixture integrity as a test: manifest hash pinned, every fixture re-hashed, every write path guarded outside tests/fixtures/"
    - "Deterministic inline LCG (no external crates) for the 20,000-base consumer fixture"

key-files:
  created:
    - tests/rkdb_v2_byte_identity_tests.rs
  modified: []

key-decisions:
  - "Each task is its own commit even though both extend one file: Task 1 (differential/unsorted/fixture integrity/IN-03) landed first and was verified alone, then Task 2 added the consumer and header tests"
  - "The goldens are never regenerated: the manifest sha256 f010e42a… and all 12 fixture hashes are asserted, and every write helper refuses a tests/fixtures/ path"
  - "Hand-built arm 4 is compared as the data section only (after the 42-byte header) while arms 1-3 are compared as whole files by sha256, exactly as the plan specifies"
  - "The unsorted-disk refusal is asserted by its error message ('unsorted database'), so a silently wrong Some/None can never pass as a refusal"
  - "Prefix block bounds are computed from the ascending oracle list itself (first matching index / one past last / insertion point for no-match), not by calling the private encode_prefix_to_range"
  - "Consumer fixture: 20,000-base LCG sequence at k=21 canonical yields 19,980 distinct k-mers over 19,980 windows; the 500 sampled keys are all non-palindromic, so the reverse-complement arm is non-vacuous"

requirements-completed: [OUT-02]

duration: 8min
completed: 2026-11-13
status: complete
---

# Phase 8 Plan 02: `.rkdb` v2 Byte Identity and Both-Consumer Sortedness Summary

**The new counting output path reproduces all six committed pre-refactor `.rkdb` goldens byte for byte against three independent references, and both binary-search consumers answer exactly from its files while an unsorted file is refused rather than mis-answered.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-11-13T01:25:00+08:00
- **Completed:** 2026-11-13T01:33:00+08:00
- **Tasks:** 2
- **Files modified:** 1 created, 0 modified

## Accomplishments

- **Four-arm byte differential green on all six sorted cells.** For k ∈ {21, 32, 64} × canonical on/off, the real CLI (threads 1 and 4) emits bytes that sha256-match the committed fixture and the frozen `RKDatabase::from_kmer_pairs(..).to_file_path(..)` writer, and whose data section byte-equals a hand-built 16-byte-LE-key + 4-byte-LE-count section built directly from the oracle. Measured new-path hashes vs the pinned manifest:

  | Cell | New-path sha256 | Equals fixture |
  |---|---|---|
  | k=21 canon | `a5da813e2977157afc4b8c395dc6fbc721516024c52cb257208490e29b796af7` | YES |
  | k=21 noncanon | `6395577a302f2c22c102724f00d58d4b3cd2f117942b914bc1617f79fea4f264` | YES |
  | k=32 canon | `3b020fe0306ffa3e2726228a4461838af9d56f8b8ca745d5731657c1783c7572` | YES |
  | k=32 noncanon | `c8b5102c1082a881f1c660ddb71b7cfb3e4ffedb639ab2c03f63b31708fb9799` | YES |
  | k=64 canon | `b886b35b48641e5f9be3e3ed63f7c66de503f5ec13eaf0fd4297ae990c4513e1` | YES |
  | k=64 noncanon | `39231759cb2e9eff7c295c5ac53c49e29c6ee074a59d5a26e054d05158ff23fa` | YES |

- **Six unsorted cells content-equal.** `--no-sort` runs carry `sorted=false`, the cell's canonical flag, exactly the oracle's distinct record count, the exact sorted multiset of (decoded sequence, count), and the oracle's count total; the record parse lands exactly on the file end (no trailing partial record). Byte order is never asserted.
- **Fixture integrity.** `sha256(tests/fixtures/golden_manifest.sha256)` = `f010e42a213de6786ac67e2a6f9227485320e7ddfca4c6521cf019880786f25f`; all 12 fixtures hash to their manifest entries; `git status --porcelain -- tests/fixtures/` is empty. Every write helper in the test refuses a `tests/fixtures/` path, so no test can regenerate a golden.
- **IN-03 distinction asserted where it matters.** For the k=21 canonical sorted cell the header's `total_kmers` is 20 (record count) while the sum of the records' counts is 279 (total observations); the test asserts both, plus that the two differ, so an inverted meaning cannot pass.
- **Header literals frozen byte-by-byte.** On both the t1 and t4 consumer files: magic `RKDB`, version 2, kmer_size 21, flags byte 3 (sorted+canonical), `data_offset` 42, `index_offset` 0, seven zero padding bytes, and `total_kmers` equal to the on-disk record count; records are strictly ascending; t1 and t4 bytes are identical.
- **Consumer one — `DatabaseQuery`.** Disk binary search answers all 500 sampled oracle keys and their 500 reverse complements with the canonical count, and returns `None` for 200 valid absent k-mers; preloaded search answers every oracle key (19,980) plus the absent set. The unsorted-disk negative control returns an `Err` whose message names the unsorted database, while the preloaded linear route answers the full oracle.
- **Consumer two — prefix query.** `extract_prefix_optimized` on new-path files returns exactly the oracle subset in file order with exact contiguous block bounds for all eight cases: `A` (8,769 matches), `C` (6,192), `G` (3,714), `T` (1,305), a 3-base prefix `CAG` (439), a 10-base prefix (1), a full-length key (1), and a no-match prefix `AAAAAAAAAA` (0, block start == end == insertion point). The unsorted file's linear fallback returns the same match sets with `is_sorted=false`.
- **Gates.** `cargo test --locked --test rkdb_v2_byte_identity_tests` = 8 passed; `golden_sha256_tests` = 5 passed; `golden_tests` = 34 passed; `prefix_cache_output_order_tests` = 3 passed; MSRV 1.82 `cargo clippy --locked --all-targets -- -D warnings` clean on both the root and pyo3 crates; `src/database/format.rs` git blob still `eb0d5bf2…`; `Cargo.toml`/`Cargo.lock` untouched.

## Task Commits

Each task was committed atomically:

1. **Task 1: Four-arm byte differential across the six sorted golden cells plus the unsorted content cells** — `fcdc3c2` (feat)
2. **Task 2: Prove sortedness through both binary-search consumers and freeze the header literals** — `eeefcc2` (feat)

**Plan metadata:** the final docs commit with this SUMMARY, STATE.md, ROADMAP.md, and REQUIREMENTS.md.

## Files Created/Modified

- `tests/rkdb_v2_byte_identity_tests.rs` — 1,140-line integration test with four test groups: (1) `new_count_path_matches_all_six_committed_sorted_goldens`, `unsorted_cells_carry_the_same_record_multiset`, `golden_manifest_hash_and_fixtures_are_unmodified`, `record_count_and_sum_of_counts_have_distinct_meaning`; (2) `header_bytes_match_the_frozen_v2_literals`, `database_query_binary_search_answers_every_oracle_key_from_the_new_write_path`, `disk_binary_search_refuses_an_unsorted_database`, `prefix_query_answers_exactly_on_files_produced_by_the_new_write_path`. No production source changed.

## Decisions Made

- **Two commits, one file.** Both tasks extend `tests/rkdb_v2_byte_identity_tests.rs`; Task 1's tests were committed and verified alone (4/4 green, clippy-clean) before Task 2's additions were restored and verified (8/8 green).
- **Reference independence.** The oracle is built with the pre-refactor algorithm (encode + optional canonicalize per naive window), and arm 4 serializes it with no production call in between. Arms 1-3 cover the write path, the committed contract, and the frozen writer respectively.
- **No fixture regeneration, ever.** The integrity test pins the manifest hash and every fixture, and the write guard makes a `tests/fixtures/` write a hard failure rather than a convention.
- **Negative control by message.** The unsorted-disk refusal asserts the error text, because the failure mode under test is a player answering wrongly under a lying `sorted` flag — not merely returning an error of some kind.

## Deviations from Plan

None — the plan executed exactly as written.

## Issues Encountered

- **Pre-existing formatting drift, out of scope.** `cargo fmt --all --check` is red at HEAD on files this plan never touched: `src/cli/commands/count.rs`, `src/count/engine.rs`, `src/count/mod.rs`, `src/database/prefix_cache_merge.rs`, `src/kmer/extract.rs`, `tests/count_engine_tests.rs`, `tests/window_extract_differential_tests.rs` (reproduced with both stable and nightly rustfmt). The new test file itself is rustfmt-clean. Recorded in `deferred-items.md`; not fixed here per the scope boundary.
- The nightly toolchain emits a deprecation warning for `AtomicU64::fetch_update` in `src/hash/table.rs` (not touched by this plan); the MSRV 1.82 clippy gate is clean.

## Known Stubs

None. No placeholder values, skipped tests, or unrun verifications were introduced.

## Threat Flags

None beyond the plan's threat model. T-08-06 (fixture regeneration) is held by the pinned manifest hash, the 12 fixture re-hashes, and the write guard; T-08-07 (header/IN-03 drift) by byte-offset literal assertions and the record-count-vs-sum test on data where the values differ; T-08-08 (lying sorted flag) by strict ascending records, both consumers answering oracle queries, and the unsorted-disk refusal; T-08-09 (arm collusion) by the four-arm construction with a hand-built byte reference; T-08-SC by `--locked` test runs and the untouched `Cargo.toml`/`Cargo.lock`.

## Next Phase Readiness

- 08-03 can reference `new_count_path_matches_all_six_committed_sorted_goldens` and mutate the comparator token `|(a, _), (b, _)| a.cmp(b)` / the consuming collector to observe named gates fail.
- 08-04 can pin `src/database/format.rs` (still git blob `eb0d5bf2…`) and the unchanged manifests/lockfiles, and can run the same gates as the formal post artifact.
- The fixture contract is now actively enforced by a differential, not just a re-hash: a write-path drift on any of the six sorted cells turns this binary red.
- One item for the phase's attention: the repository-wide `cargo fmt --all --check` job is red at HEAD for pre-existing reasons (see `deferred-items.md`), independent of this plan.

## Self-Check

- Created file verified present: `tests/rkdb_v2_byte_identity_tests.rs`.
- Task commits verified as ancestors of HEAD: `fcdc3c2`, `eeefcc2`.
- Frozen contracts: `git hash-object src/database/format.rs` = `eb0d5bf29330301930d98d801480cf73d1cf826a`; `tests/fixtures/` clean; `Cargo.toml`/`Cargo.lock` unchanged.

## Self-Check: PASSED

---
*Phase: 08-output-pipeline-rkdb-v2-parity*
*Completed: 2026-11-13*
