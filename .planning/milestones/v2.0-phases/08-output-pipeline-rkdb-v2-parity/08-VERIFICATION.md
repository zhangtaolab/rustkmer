---
phase: 08-output-pipeline-rkdb-v2-parity
verified: 2026-11-12T18:20:43Z
status: passed
score: 16/16 must-haves verified
covered_files: [".planning/phases/08-output-pipeline-rkdb-v2-parity/08-01-PLAN.md", ".planning/phases/08-output-pipeline-rkdb-v2-parity/08-01-SUMMARY.md", ".planning/phases/08-output-pipeline-rkdb-v2-parity/08-02-PLAN.md", ".planning/phases/08-output-pipeline-rkdb-v2-parity/08-02-SUMMARY.md", ".planning/phases/08-output-pipeline-rkdb-v2-parity/08-03-PLAN.md", ".planning/phases/08-output-pipeline-rkdb-v2-parity/08-03-SUMMARY.md", ".planning/phases/08-output-pipeline-rkdb-v2-parity/08-04-PLAN.md", ".planning/phases/08-output-pipeline-rkdb-v2-parity/08-04-SUMMARY.md", "scripts/bench/mutation_red.py", "scripts/bench/output_stage.py", "scripts/bench/tests/test_mutation_red.py", "scripts/bench/tests/test_output_stage.py", "src/cli/commands/count.rs", "src/count/engine.rs", "src/hash/local.rs", "tests/output_differential_matrix_tests.rs", "tests/output_pipeline_tests.rs", "tests/rkdb_v2_byte_identity_tests.rs"]
covered_digest: "v4:sha256:ba3a2f9948bc59592d2df6b96538a9f050de84869d681dc71ef8c6cc3a9c66cc"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 8: Output Pipeline & .rkdb v2 Parity Verification Report

**Phase Goal:** Counting output is fast (unstable/parallel sort, streaming write) and byte-level compatibility of every new counting path is proven — the milestone's contract gate before any verdict runs.
**Verified:** 2026-11-12T18:20:43Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Sorted output sorts with rayon's in-place parallel unstable sort and streams through the frozen writer with no `get_all_counts` materialization | ✓ VERIFIED | `sort_pairs_ascending` = `pairs.par_sort_unstable_by(\|(a,_),(b,_)\| a.cmp(b))` (`src/cli/commands/count.rs:358`); `CountResult::into_filtered_pairs` drains each partition table into one Vec (`src/count/engine.rs:413`); writer emits one `KmerEntry::write_to` per record after `header.write_to` (`count.rs:490-500`); `get_all_counts` appears nowhere in the output path |
| 2 | Text output ordered by numeric encoded key, equal to decoded order for every k 1..=64 | ✓ VERIFIED | `sort_pairs_ascending` replaced the per-comparison decode sort; `numeric_order_equals_decoded_order_for_every_k` (seeded keys k 1..=64, string-permutation equality) + inverted-order control pass; CLI text order test passes |
| 3 | Pre-change output-stage baseline captured from the untouched tree with provenance, pinned slice fingerprint, counts, and sha256 | ✓ VERIFIED | `pre/phase8_output_stage_pre.json` schema/provenance validates; binary `d107d17e…`, HEAD `4d53102`, fingerprint `71c6264b…` (1,472,481,891 B), counts 229,694,874/519,271,168, sha `0976f29c…`; sorted 18.73 s / unsorted 9.82 s / raw delta 8.91 s |
| 4 | Post-change output stage GREEN vs the immutable baseline (strictly lower sorted wall, delta ≤ 0.5x, same sha, RSS not regressed) | ✓ VERIFIED (re-executed) | Independent `output_stage.py compare` run: sorted 10.37 s vs 18.73 s, raw delta 1.60 s ≤ 0.5×8.91, sha256_match True in all 3 reps, sorted RSS 12.04 GB ≤ 17.97 GB; verdict GREEN exit 0 (plan recorded 10.41 s / 1.70 s — same verdict, noise-level difference) |
| 5 | Six sorted cells (k∈{21,32,64}×canonical) reproduce the committed pre-refactor fixture, the frozen `from_kmer_pairs` writer, and a hand-built byte reference — four independent arms | ✓ VERIFIED | `new_count_path_matches_all_six_committed_sorted_goldens` (8/8 byte-identity tests pass); arms 1–3 whole-file sha256-equal, arm 4 data section equals hand-built `u128 LE + u32 LE` bytes with no production writer |
| 6 | Six unsorted cells carry the same record multiset under `sorted=false`; all 12 fixtures and the manifest are unmodified | ✓ VERIFIED | `unsorted_cells_carry_the_same_record_multiset` passes; manifest sha256 `f010e42a…` re-verified, all 12 fixture files independently re-hashed to manifest (0 mismatches), `git status -- tests/fixtures/` empty, write helpers refuse fixture paths |
| 7 | `DatabaseQuery` binary search (disk and preloaded) answers every sampled oracle key, reverse complements, and absent keys; unsorted disk is refused, preload linear still answers | ✓ VERIFIED | `database_query_binary_search_answers_every_oracle_key_from_the_new_write_path` and `disk_binary_search_refuses_an_unsorted_database` pass; production `query.rs:165-170` returns the named "Cannot query unsorted database…" error |
| 8 | Prefix query returns exactly the oracle subset with exact contiguous block bounds for all eight cases; unsorted linear fallback parity | ✓ VERIFIED | `prefix_query_answers_exactly_on_files_produced_by_the_new_write_path` passes (four single bases, 3-base, 10-base, full-length, no-match; start/end/block_size/total_matches asserted against an independently computed oracle block) |
| 9 | 42-byte header literals frozen and IN-03 meanings preserved (header `total_kmers` = record count, not sum of counts) | ✓ VERIFIED | `header_bytes_match_the_frozen_v2_literals` asserts magic/version/kmer_size/flags=3/padding/data_offset=42/index_offset=0 byte-by-byte; `record_count_and_sum_of_counts_have_distinct_meaning` asserts 20 (records) vs 279 (sum) on the golden cell |
| 10 | Single frozen `format.rs` writer; blob unchanged from phase base | ✓ VERIFIED | `git hash-object src/database/format.rs` = `eb0d5bf2…`; `DatabaseHeader`/`KmerEntry` defined only in `src/database/format.rs`; count path uses only `header.write_to` + `KmerEntry::write_to`; no format.rs change in `4d53102..HEAD` |
| 11 | 12-cell old-vs-new matrix (k×canonical×threads{1,4}) in text and binary, old-arm byte equality, t1/t4 identity, non-vacuous skip-N parity | ✓ VERIFIED | `old_vs_new_matrix_reproduces_the_reference_in_text_and_binary` asserts `cells == 12`, text/binary maps equal the pre-refactor reference, stderr totals pinned, old frozen-writer bytes equal new bytes per cell, t1==t4; `n_containing_record_skips_exactly_the_windows_that_cover_the_n` pins the exact N-free window count |
| 12 | Disjointness and conservation hold at the output boundary | ✓ VERIFIED | `proptest_output_boundary_disjointness_and_conservation` (12 cases, k∈{21,64}×canonical×min_count 1..=3) passes: visit-once, pair count == unique, sum == total, strict ascending, filter == filtering_stats, run-to-run identity; `count_engine_tests` 20/20 green |
| 13 | Injected ordering, duplication, and overflow defects are observed RED, then restored and re-greened with blob verification | ✓ VERIFIED (re-executed) | `mutation_red.py run` re-run on this tree: ordering 3/3 gates RED, duplication 2/2 RED, overflow 1/1 RED; every `expect_substring_seen=true`, every `post_restore_exit=0`, `restored_blob_matches=true`; `MUTATION VERDICT result=GREEN`; `git status` clean and `count.rs`/`local.rs` blobs equal the pre-mutation values |
| 14 | Slice t1/t4/t16 walls and RSS below the Phase 7 values with pinned counts, and all three slice `.rkdb` files hash to `0976f29c…` | ✓ VERIFIED (re-executed) | Independent `thread_scaling.py --measure-only` run: 31.83 / 10.27 / 9.12 s vs Phase 7 36.92 / 17.76 / 23.83 s; RSS 12.037 / 12.043 / 12.044 GB vs ~17.96 GB; counts 229,694,874 / 519,271,168 in every arm; `shasum` of the three produced databases = `0976f29c5ede…` each (also the sorted output-stage database) |
| 15 | Standing gates green: MSRV 1.82 clippy both crates, full locked suite, harness unit discovery, rebuilt PyO3 pytest | ✓ VERIFIED (re-executed) | `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` root exit 0 and pyo3 exit 0; `cargo test --locked` 31 "test result: ok" summaries, 0 failed, exit 0; `python3 -m unittest discover` Ran 361 tests OK (skipped=1); `.venv311` module pytest 158 passed / 63 skipped |
| 16 | No gate softened and no frozen evidence moved: workflow silencing 0, README/thread_scaling counts equal HEAD and the Phase 7 baseline, fixtures/baselines/Phase 5–7 evidence untouched | ✓ VERIFIED | Independent grep: workflow 0, README 2, thread_scaling 2 (the two matches are quoted doctrine forbidding `\|\| true`/`continue-on-error`); files have no commits in `4d53102..HEAD`; `git diff 4d53102..HEAD` touches only phase files, 3 source files, tests, and scripts — no Cargo manifest/lock, pyo3/src, fixtures, baselines, or Phase 5–7 evidence |

**Score:** 16/16 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/cli/commands/count.rs` | in-place parallel unstable sort; consuming streaming text/binary writers | ✓ VERIFIED | Real implementation, wired from `execute_count`; 122-line diff limited to the output stage + unit test |
| `src/count/engine.rs` | consuming `into_pairs` / `into_filtered_pairs` | ✓ VERIFIED | Additive public methods; drains each table as it iterates |
| `src/hash/local.rs` | consuming `LocalKmerCounts::into_pairs_into` | ✓ VERIFIED | Dense zero-extension/wide move; no second copy |
| `tests/output_pipeline_tests.rs` | golden byte identity, ascending order, header count, thread identity, text order | ✓ VERIFIED | 9 tests, 9 passed, 0 skipped; invokes `CARGO_BIN_EXE_rustkmer` |
| `tests/rkdb_v2_byte_identity_tests.rs` | four-arm differential, unsorted cells, fixture integrity, IN-03, both consumers, header literals | ✓ VERIFIED | 8 tests, 8 passed, 0 skipped; guards every write outside `tests/fixtures/` |
| `tests/output_differential_matrix_tests.rs` | 12-cell matrix, skip-N, output-boundary proptest | ✓ VERIFIED | 3 tests (12 explicit cells + 12 proptest cases), 3 passed |
| `scripts/bench/output_stage.py` + tests | standing capture/compare gate with strict verdict | ✓ VERIFIED | 29 unit tests in the 361-test discovery; verdict requires all four conditions, identity gate rejects different params/fingerprint |
| `scripts/bench/mutation_red.py` + tests | exact-unique mutation driver, restore-in-finally, blob verification | ✓ VERIFIED | 16 unit tests; re-run produced GREEN with per-gate exit codes and excerpts |
| `pre/phase8_output_stage_pre.json` | immutable pre-change baseline | ✓ VERIFIED | Harness validators pass; provenance pins binary `d107d17e` + HEAD `4d53102` |
| `post/phase8_output_stage_post.json` | post measurement + GREEN verdict | ✓ VERIFIED | Harness validators pass; verdict recomputed by `stage_verdict` = exit 0 |
| `post/phase8_slice_green.json` | t1/t4/t16 slice arms | ✓ VERIFIED | Counts/walls/RSS/fingerprint consistent; per-arm `.rkdb` hashes are not persisted in the document, but were reproduced independently by this verification (see truth 14) |
| `phase8_gates_evidence.json` | gate evidence | ✓ VERIFIED | Every recorded fact re-executed and matched |
| `phase8_mutation_red.json` + `08-mutation-spec.json` | observed RED evidence | ✓ VERIFIED | Re-generated evidence matched: RED counts, excerpts, blob restore |
| `src/database/format.rs` | frozen writer | ✓ VERIFIED | Blob `eb0d5bf2…`, unchanged in phase range |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `execute_count` | output writers | `CountResult` moved by value | ✓ WIRED | Stats computed before the move (`count.rs:279-282`); no borrow-after-move |
| output writers | frozen `.rkdb` codec | `DatabaseHeader::write_to` + `KmerEntry::write_to` | ✓ WIRED | Single call sites; per-record flush with mapped `FileWriteError` |
| real CLI (`CARGO_BIN_EXE_rustkmer`) | committed goldens | byte equality in test | ✓ WIRED | Six sorted cells match fixtures; drift message names first differing offset |
| new-path `.rkdb` | `DatabaseQuery` disk/preload | `query_kmer` | ✓ WIRED | 500 sampled keys + 500 reverse complements + 200 absent keys |
| new-path `.rkdb` | prefix consumer | `extract_prefix_optimized` | ✓ WIRED | Exact subset and block bounds for 8 prefix cases |
| `output_stage.py compare` | pre baseline → post verdict | frozen baseline document | ✓ WIRED | Re-executed GREEN with identity gate satisfied |
| `thread_scaling.py` slice arms | three `.rkdb` hashes | `shasum` after the runs | ✓ WIRED | All three = `0976f29c…` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `output_binary_format` | `kmers: Vec<(u128,u32)>` | `CountResult::into_filtered_pairs` over engine partition tables | Yes — 229,694,874 records from real slice input, pinned counts in every arm | ✓ FLOWING |
| `output_text_format` | `kmers` | same engine result | Yes — decoded per line from real counts | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full locked Rust suite | `cargo test --locked` | 31 "ok" summaries, 0 failed, exit 0 | ✓ PASS |
| Phase-8 binaries | (within suite) | output_pipeline 9, rkdb_v2_byte_identity 8, differential_matrix 3, all 0 skipped | ✓ PASS |
| Golden fixtures | (within suite) | golden_sha256_tests 5, golden_tests 34 | ✓ PASS |
| MSRV clippy, both crates | `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` (± pyo3 manifest) | both exit 0 | ✓ PASS |
| Harness unit tests | `python3 -m unittest discover -s scripts/bench/tests -t .` | Ran 361 tests, OK (skipped=1), exit 0 | ✓ PASS |
| Rebuilt PyO3 module | `.venv311/bin/python -m pytest pyo3/tests -q` | 158 passed, 63 skipped | ✓ PASS |
| Mutation-RED | `python3 scripts/bench/mutation_red.py run --spec … --out …` | ordering 3/3, duplication 2/2, overflow 1/1 RED; VERDICT GREEN; tree restored | ✓ PASS |
| Output-stage gate | `python3 scripts/bench/output_stage.py compare --baseline pre/…json` | GREEN: 10.37 s, delta 1.60 s, sha match, RSS 12.04 GB | ✓ PASS |
| Slice determinism | `python3 scripts/bench/thread_scaling.py --mode slice --measure-only` | 31.83/10.27/9.12 s, counts pinned, three `.rkdb` all `0976f29c…` | ✓ PASS |
| Fixture integrity | per-line `shasum -a 256` against manifest | 12/12 match, manifest `f010e42a…` | ✓ PASS |

### Probe Execution

N/A — no `scripts/*/tests/probe-*.sh` files exist and no probe is declared or implied by the phase plans/summaries.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| OUT-01 | 08-01, 08-04 | Unstable/parallel sort + streaming write, no `get_all_counts` materialization, numeric text order, measurable stage drop | ✓ SATISFIED | Code path verified; 10.37 s vs 18.73 s baseline, delta 1.60 s (0.18x), RSS 12.04 vs 17.97 GB, sha unchanged |
| OUT-02 | 08-02, 08-04 | `.rkdb` v2 byte identity, both binary-search consumers, frozen header/writer/IN-03 | ✓ SATISFIED | 12/12 fixtures match manifest; six-cell four-arm differential; DatabaseQuery + prefix consumer tests; format.rs blob frozen; slice-scale sha `0976f29c` |
| OUT-03 | 08-03, 08-04 | Old-vs-new and 1-vs-N matrix, disjointness/conservation properties, mutation-RED | ✓ SATISFIED | 12-cell matrix + skip-N parity; proptest; mutation RED re-observed with verified restore |

No orphaned requirements: REQUIREMENTS.md maps only OUT-01..03 to Phase 8, and all three are claimed by plans and satisfied.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| `tests/output_pipeline_tests.rs` | OUT-01 | 9 | 0 | No — expected bytes are the committed pre-refactor fixture | Value/behavioral | PASS |
| `tests/rkdb_v2_byte_identity_tests.rs` | OUT-02 | 8 | 0 | No — independent naive-window oracle + hand-built byte reference; fixtures predate the refactor (created 2026-07-01) | Value/behavioral | PASS |
| `tests/output_differential_matrix_tests.rs` | OUT-03 | 3 (+12 proptest cases) | 0 | No — reference is the pre-refactor naive algorithm | Value/behavioral | PASS |
| `scripts/bench/tests/test_output_stage.py` | OUT-01 | 29 (in 361) | 0 | No | Behavioral | PASS |
| `scripts/bench/tests/test_mutation_red.py` | OUT-03 | 16 (in 361) | 0 | No | Behavioral | PASS |

**Disabled tests on requirements:** 0 (the only `#[ignore]`d tests in the suite are pre-existing one-shot generators/timing gates unrelated to Phase 8).
**Circular patterns detected:** 0.
**Insufficient assertions:** 0.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No `TBD`/`FIXME`/`XXX`, placeholder, empty-return, or hollow-data patterns in any phase-modified source/test/script file | — | None |
| (repo-wide) | — | `cargo fmt --all --check` red on pre-existing files untouched by this phase | ℹ️ Info | Recorded in `deferred-items.md`; not caused by this phase; no phase file implicated (new test file is rustfmt-clean); does not affect the goal |
| `src/hash/table.rs:483` | 483 | Nightly-only deprecation of `AtomicU64::fetch_update` in untouched Phase 6 code | ℹ️ Info | Pre-existing; MSRV 1.82 clippy is clean |

### Decision Coverage

No trackable decisions in `08-CONTEXT.md` (decision-coverage gate returned `skipped: true`, total 0). The fixed-contract decisions were nonetheless verified directly: frozen writer, goldens never regenerated, and sortedness proven through both consumers.

### Human Verification Required

N/A — infrastructure/foundation phase with no user-facing elements. All acceptance criteria are programmatic and were verified by re-execution.

### Gaps Summary

None. The phase goal is achieved: the output stage uses an in-place parallel unstable sort and streams the sorted slice through the untouched `format.rs` writer, the stage is measurably faster (sorted 18.73 s → 10.37 s re-measured, raw sort delta 8.91 s → 1.60 s = 0.18x, RSS 17.97 GB → 12.04 GB), byte identity holds against all 12 pre-refactor goldens and at 229M-key slice scale across t1/t4/t16 (`0976f29c…`), both binary-search consumers answer correctly (and unsorted disk is refused), and the proof gates were re-observed RED under injected ordering/duplication/overflow defects before a blob-verified restore. The tree is clean; no frozen artifact, manifest, lockfile, fixture, baseline, or public API moved.

---

_Verified: 2026-11-12T18:20:43Z_
_Verifier: Claude (gsd-verifier)_
