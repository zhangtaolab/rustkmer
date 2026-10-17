---
phase: 03-memory-safety
verified: 2026-10-17T09:28:19Z
status: passed
score: 11/11 must-haves verified
covered_files:
  - ".planning/phases/03-memory-safety/03-01-PLAN.md"
  - ".planning/phases/03-memory-safety/03-01-SUMMARY.md"
  - ".planning/phases/03-memory-safety/03-02-PLAN.md"
  - ".planning/phases/03-memory-safety/03-02-SUMMARY.md"
  - ".planning/phases/03-memory-safety/03-03-PLAN.md"
  - ".planning/phases/03-memory-safety/03-03-SUMMARY.md"
  - ".planning/phases/03-memory-safety/03-04-PLAN.md"
  - ".planning/phases/03-memory-safety/03-04-SUMMARY.md"
  - ".planning/phases/03-memory-safety/03-05-PLAN.md"
  - ".planning/phases/03-memory-safety/03-05-SUMMARY.md"
  - ".planning/phases/03-memory-safety/03-06-PLAN.md"
  - ".planning/phases/03-memory-safety/03-06-SUMMARY.md"
  - ".planning/phases/03-memory-safety/03-07-PLAN.md"
  - ".planning/phases/03-memory-safety/03-07-SUMMARY.md"
  - ".planning/phases/03-memory-safety/03-08-PLAN.md"
  - ".planning/phases/03-memory-safety/03-08-SUMMARY.md"
  - ".planning/phases/03-memory-safety/03-09-PLAN.md"
  - ".planning/phases/03-memory-safety/03-09-SUMMARY.md"
  - ".planning/phases/03-memory-safety/03-10-PLAN.md"
  - ".planning/phases/03-memory-safety/03-10-SUMMARY.md"
  - ".planning/phases/03-memory-safety/03-11-PLAN.md"
  - ".planning/phases/03-memory-safety/03-11-SUMMARY.md"
  - ".planning/phases/03-memory-safety/03-12-PLAN.md"
  - ".planning/phases/03-memory-safety/03-12-SUMMARY.md"
  - ".planning/phases/03-memory-safety/03-13-PLAN.md"
  - ".planning/phases/03-memory-safety/03-13-SUMMARY.md"
  - ".planning/phases/03-memory-safety/03-14-PLAN.md"
  - ".planning/phases/03-memory-safety/03-14-SUMMARY.md"
  - ".planning/phases/03-memory-safety/03-15-PLAN.md"
  - ".planning/phases/03-memory-safety/03-15-SUMMARY.md"
  - ".planning/phases/03-memory-safety/03-16-PLAN.md"
  - ".planning/phases/03-memory-safety/03-16-SUMMARY.md"
  - ".planning/phases/03-memory-safety/03-17-PLAN.md"
  - ".planning/phases/03-memory-safety/03-17-SUMMARY.md"
  - "pyo3/pyproject.toml"
  - "pyo3/src/database.rs"
  - "pyo3/tests/test_database_merge.py"
  - "src/cli/commands/count.rs"
  - "src/cli/commands/merge.rs"
  - "src/database/format.rs"
  - "src/database/merge_config.rs"
  - "src/database/prefix_cache_merge.rs"
  - "src/database/streaming_merge.rs"
  - "src/database/temp_lifecycle.rs"
  - "src/hash/table.rs"
  - "src/io/fasta.rs"
  - "src/io/fastq.rs"
  - "tests/common/factories.rs"
  - "tests/common/mod.rs"
  - "tests/common/performance.rs"
  - "tests/dense_differential_tests.rs"
  - "tests/dense_memory_tests.rs"
  - "tests/dense_merge_integration_tests.rs"
  - "tests/dense_proptest_tests.rs"
  - "tests/golden_sha256_tests.rs"
  - "tests/merge_bounded_memory_tests.rs"
  - "tests/merge_cleanup_tests.rs"
  - "tests/merge_frontend_validation_tests.rs"
  - "tests/merge_route_parity_tests.rs"
  - "tests/merge_routing_tests.rs"
  - "tests/parallel_count_tests.rs"
  - "tests/prefix_cache_conservation_tests.rs"
  - "tests/prefix_cache_output_order_tests.rs"
covered_digest: "v3:sha256:da4b87480af02ded55494e49163df717cc2c0ef6dedf82c04d2792679c6b4609"
behavior_unverified: 0 # Count of PRESENT_BEHAVIOR_UNVERIFIED truths (present + wired, behavior not exercised); each is detailed in behavior_unverified_items below (and in human_verification when status is human_needed)
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 11/11
  gaps_closed:
    - "Carried human item (03-12 D4, WINDOWS.md #16): the pyo3 maturin blocker was lifted by dbb13ef (python-source key dropped, pyo3/pyproject.toml). This round I rebuilt pyrustkmer from CURRENT source (maturin develop, exit 0) and executed the item's exact procedure from Python: k=21+k=31 inputs and mixed-canonical inputs under merge_mode='streaming' both raise PyRuntimeError carrying 'Merge operation failed' + the prologue's k-mer-size / canonical compatibility text, with NO output file written; a compatible-input control merges successfully under the same budget (3/3 PASS). The MERGE-04 contract suite (pyo3/tests/test_database_merge.py) also ran for the first time: 12/12. The prior frontmatter said status: passed while its body carried one open human item — this round the human section is genuinely empty, making 'passed' fully valid."
  gaps_remaining: []
  regressions: []
advisory:
  - finding: "Post-verification source changes audited this round, all regression-clean: (1) 8f23225 touches src/database/prefix_cache_merge.rs ONLY inside #[cfg(test)] mod tests (both hunks at lines 1999+/2027+, production mod tests starts :1545; unix branch of failed_bucket_aborts_the_merge_with_err ran green here); (2) 8102985 swaps GzDecoder->MultiGzDecoder in src/io/fastq.rs open_compressed (production, input-reading only — no merge/dense-format interaction) with a two-member gzip regression test, green in the lib suite; (3) cc64fbc/97f54bf/8f23225 narrow merge_routing/merge_cleanup off shared-common SELF-tests (those still run in golden/round_trip binaries: round_trip 23 passed incl. common::* self-tests) and gate platform-specific test plants; suite 400/0 on darwin; (4) ba7f451 applies rustfmt to the 4 drifted files — rustfmt --check exit 0 on all 8 files I spot-checked."
    category: other
    reason: "None of these falsifies a must-have truth; each is covered by a green behavioral run recorded in this report."
    evidence_status: "diffs read + suite/clippy/fmt runs executed by me this round"
  - finding: "WINDOWS.md ledger rows #16 (unrun-verify: PyRuntimeError manifestation never pytest-run) and #18 (lint-warning: cargo fmt drift on 4 files) are now discharged in substance but still read 'open' in the table: #16's blocker was lifted (dbb13ef) and the manifestation executed this round (12/12 + direct 3-variant check); #18's drift was fixed by ba7f451 (rustfmt --check exit 0 on all 4 named files, re-verified by me). Ledger flips are a developer/orchestrator edit — not made by the verifier."
    category: other
    reason: "Stale bookkeeping, not live defects; flipping the two rows to fixed/closed with this report's evidence would reconcile the ledger."
    evidence_status: "WINDOWS.md rows read; underlying conditions re-verified by me"
  - finding: "Fresh post-fix code review committed after the prior verification (03-REVIEW.md 2026-10-17, critical: 0) grew the open advisory set by 5: WR-15/16/17 (src/io/fastq.rs helpers total_sequence_length/average_quality/count_sequences/filter_by_quality — compression/Phred/parse-error handling; no phase-03 truth depends on these helpers) and IN-12/13 (MultiGzDecoder hard-errors on trailing garbage after the final member; two tautological GUARD asserts in merge_bounded_memory_tests — the routing proofs rest on the missing-temp-dir probe and D-02 rejection-text assertions, which remain discriminating). The 'open' CR-01/CR-02/CR-03 rows are keep-rule artifacts marked 'not in the current review' — the current review confirms closure, and this round's behavioral evidence re-confirms all three (mixed-canonical both-writer test, output-order tests, Python rejection check)."
    category: other
    reason: "All warning/info severity, recorded open in the committed 03-REVIEW-DISPOSITION.md for developer triage; no must-have depends on them."
    evidence_status: "committed review + disposition records read by me"
  - finding: "pyo3 pytest run needs --no-cov on this host: pyproject addopts force --cov-fail-under=80 over testpaths, and 63 of 188 collected Python tests skip on a missing fixture (python/tests/test_data/tiny_test.rkdb, export tests) — pre-existing, outside phase-03 scope. The 125 that ran all passed."
    category: other
    reason: "Repo tooling/fixture state, not a phase truth; recorded so the next pyo3 test run is not misread."
    evidence_status: "reproduced by me (pytest -rs output)"
---

# Phase 03: Memory Safety — Re-Verification Report (Round 5, staleness refresh)

**Phase Goal:** Bounded-memory merge operations and dense k-mer storage for the common k ≤ 32 case
**Verified:** 2026-10-17T09:28:19Z
**Status:** passed
**Re-verification:** Yes — staleness refresh. The round-4 report (2026-10-09, 11/11) went stale because covered source changed afterward (8f23225 test-module-only Windows cfg in prefix_cache_merge.rs; 8102985 MultiGzDecoder production fix in src/io/fastq.rs; merge_* test Windows gating/de-flake/narrowing; ba7f451 rustfmt). This round regenerates the report over the current covered set and re-executes the full behavioral evidence chain.

## Goal Achievement

I did not take the prior report's word for standing truths: I audited every post-verification
diff, re-ran the full cargo suite, both clippy gates, rustfmt on every touched file, and —
because dbb13ef lifted the maturin blocker — rebuilt `pyrustkmer` from current source and
executed the one item that had kept this phase from a clean pass: the Python-surface
merge-rejection manifestation, including a compatible-input control. Everything is green.

### Observable Truths

| # | Truth | Status | Evidence (re-executed this round unless noted) |
|---|-------|--------|----------|
| 1 | DENSE-01: k ≤ 32 stored as u64, ~halving counting memory | ✓ VERIFIED | `CounterTable::Dense(DashMap<u64, u32>)` + `uses_dense_storage()` live in src/hash/table.rs:40,163,199 (re-read); dense_differential 6/6, dense_proptest 3/3, dense_memory 2/2 in the suite I ran |
| 2 | Merge core respects memory budget; routes bounded (MERGE-02) | ✓ VERIFIED | merge_bounded_memory_tests 6/6 and merge_routing_tests 17/17 green in the suite I ran |
| 3 | In-memory and streaming routes produce identical data | ✓ VERIFIED | merge_route_parity_tests 5/5 green |
| 4 | Failed/interrupted merges clean up temp files (MERGE-03) | ✓ VERIFIED | merge_cleanup_tests 9/9 green (post-narrowing binary; removed cases were shared-common self-tests, which still run in golden/round_trip binaries) |
| 5 | u64/u128 counts + canonicalization match (DENSE-03) | ✓ VERIFIED | dense_differential 6/6 + dense_proptest 3/3 green |
| 6 | PyDatabase merge shares the CLI's bounded path (MERGE-04) | ✓ VERIFIED | **Upgraded from carried-human to behaviorally verified.** pyo3/src/database.rs:1457 still calls `RKDatabase::merge_databases_to_path` (re-read; pyo3/src untouched since 4b9f095). Freshly built extension from current source: pyo3/tests/test_database_merge.py 12/12 (first-ever run), full pyo3 suite 125 passed / 0 failed, and my direct 3-variant check below |
| 7 | .rkdb v2 byte-identity preserved (DENSE-02) | ✓ VERIFIED | golden_sha256_tests 5/5 green; format.rs untouched by every post-verification commit (git log) |
| 8 | Incompatible inputs rejected on EVERY route | ✓ VERIFIED | merge_routing_tests 17/17 green (kmer-size-mismatch text, empty-list, header-validation, D-02 reject all present as test fns, re-listed by me); PLUS Python-surface variants A and B below now executed and passing |
| 9 | Prefix-cache bucket merge lossless for shards > one ~4 MB batch | ✓ VERIFIED | prefix_cache_conservation_tests 2/2 green |
| 10 | Prefix-cache-merged database queryable correctly (sorted flag truthful) — mixed-canonical capability on BOTH bucket writers | ✓ VERIFIED | prefix_cache_output_order_tests 3/3 green incl. `mixed_canonical_prefix_cache_output_is_ascending_summed_and_queryable` (both writer arms); override + same-mode-control + refusal unit tests all green in the lib suite (re-confirmed by name in the log); both `pop_front` consumption sites present (:1004, :1032, re-grepped); 8f23225 touched this file only inside `mod tests` (hunks 1999+/2027+, mod starts :1545) |
| 11 | CLI merge front-end does not materialize input databases | ✓ VERIFIED | comment-filtered `from_file_path` grep in src/cli/commands/merge.rs = 0 (re-run by me); merge_frontend_validation_tests 3/3 green |

**Score:** 11/11 truths verified (0 present-but-unverified; 0 failed)

### Python-Surface Rejection Manifestation (carried human item — CLOSED this round)

The blocker (maturin `python-source` refusal, WINDOWS.md #16) was lifted by dbb13ef. I rebuilt
`pyrustkmer` from current source into a scratch venv (`maturin develop`, exit 0) and executed
the item's exact procedure:

| Variant | Procedure | Result |
|---------|-----------|--------|
| A: k=21 + k=31 inputs, `merge_mode="streaming"`, `max_memory="1024"` | `PyDatabase.merge` → expect PyRuntimeError + no output file | **PASS** — PyRuntimeError carrying "Merge operation failed" + k-mer-size text; `out.rkdb` not written |
| B: mixed canonical (one `canonical=True`, one `canonical=False`, k=21), same budget | same expectation | **PASS** — PyRuntimeError carrying "Merge operation failed" + canonical text; no output file |
| Control: compatible inputs, same budget | merge must succeed | **PASS** — output file written, non-empty |

Script: 3/3 PASS (exit 0). This discharges WINDOWS.md #16's substance and closes the last open
human-verification item; the human_verification section is therefore empty and `passed` is valid.

### Post-Verification Change Audit (the staleness drivers)

| Change | Files | Audit result |
|--------|-------|--------------|
| 8102985 fix(io) MultiGzDecoder | src/io/fastq.rs (production) | Real fix: reads ALL concatenated gzip members; two-member regression test asserts exact ids/seqs/quals from both members, green in lib suite (237). Input-reading only — no merge/dense-format path touched. Note: file is phase-03 covered source via plan 03-01 key-files. |
| 8f23225 test(win) | prefix_cache_merge.rs + merge_bounded/merge_cleanup tests | prefix_cache_merge.rs diff is 100% inside `#[cfg(test)] mod tests` (both hunks after :1545); darwin/unix branches ran green here; Windows share-lock plant is CI's windows-latest leg (now in matrix per b514331) |
| cc64fbc narrow + 97f54bf de-flake | tests/common/{factories,mod,performance}.rs, merge_routing/merge_cleanup/bounded tests | Removed per-binary cases were `common::*::tests::*` shared-helper SELF-tests (still run in golden/round_trip binaries — round_trip 23 passed includes them); no routing/cleanup test was deleted (test fns re-listed by me); de-flake recalibrates wall-clock assertions only |
| ba7f451 rustfmt | count.rs, parallel_count, merge_bounded, merge_cleanup tests | rustfmt --check exit 0 on all 8 files I checked (incl. all 4 named in WINDOWS #18) — fmt drift resolved |
| dbb13ef maturin fix | pyo3/pyproject.toml | python-source key dropped; extension builds and imports (verified by me — build + 125 passing Python tests) |

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| src/database/prefix_cache_merge.rs | override + refusal + unit tests (03-17) intact after 8f23225 | ✓ VERIFIED | production code byte-identical to round-4-verified state (8f23225 test-mod-only); override :158-190, refusal :947-1041, both pop_front sites :1004/:1032 (re-grepped) |
| src/io/fastq.rs | MultiGzDecoder + regression test | ✓ VERIFIED | production swap :73 + two-member fixture test with exact-content assertions, green |
| src/hash/table.rs | Dense u64 table | ✓ VERIFIED | CounterTable::Dense(DashMap<u64,u32>) :40, :163; uses_dense_storage :199; dense tests green |
| tests/* evidence binaries | all green | ✓ VERIFIED | 23 result lines, 400 passed / 0 failed / 3 ignored (platform-gated) |
| pyo3 extension + tests | buildable, MERGE-04 suite green | ✓ VERIFIED | maturin develop exit 0; test_database_merge.py 12/12; full pyo3 pytest 125/0 |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| PyDatabase.merge (Python) | bounded core | pyo3/src/database.rs:1457 → `RKDatabase::merge_databases_to_path` | ✓ WIRED | **behaviorally executed this round** (12/12 + 3-variant check incl. control) |
| ExternalSortMerger::new canonical fold | merge_mode="memory" override | :158-190 → :482 → :526-541 | ✓ WIRED | unit tests green in lib suite (names re-confirmed in log) |
| every record leaving a shard buffer | last-key monotonicity check | both pop_front sites :1004, :1032 | ✓ WIRED | refusal unit test green |
| CLI execute_merge | to-path core (no materialization) | merge.rs (0 comment-filtered `from_file_path`) | ✓ WIRED | grep re-run by me = 0; frontend validation tests 3/3 |
| gzip inputs | full-member decode | fastq.rs:73 MultiGzDecoder | ✓ WIRED | regression test green (2 members, 5 records, exact ids) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| prefix-cache merged output (both writer arms) | entries + header counts | canonicalized shards → override → writer | Yes — oracle-equality e2e tests green | ✓ FLOWING |
| Python merge output / rejection | output file or PyRuntimeError | real .rkdb inputs → shared bounded core | Yes — control writes real output; variants A/B raise with the core's message | ✓ FLOWING |
| FASTQ compressed read path | decoded records | MultiGzDecoder over real multi-member fixture | Yes — exact ids/seqs/quals from both members | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full cargo suite (23 binaries) | `cargo test` | 400 passed / 0 failed / 3 ignored; CARGO_EXIT=0 | ✓ PASS |
| lib unit layer (override/refusal/fastq/format/streaming) | in suite | 237 passed / 0 failed | ✓ PASS |
| Discriminating names present in log | grep log for override/refusal/mixed-canonical/fastq-gzip test names | all present, all `ok` | ✓ PASS |
| Python merge rejection + control (this round's closure) | `python -I check.py` (fresh maturin build of current source) | 3/3 PASS, exit 0 | ✓ PASS |
| pyo3 MERGE-04 contract suite (first run ever) | `pytest pyo3/tests/test_database_merge.py --no-cov -q` | 12 passed | ✓ PASS |
| Full pyo3 Python suite | `pytest pyo3/tests/ --no-cov -q` | 125 passed / 0 failed / 63 skipped (missing fixture data, pre-existing) | ✓ PASS |
| Root clippy gate | `cargo clippy --all-targets -- -D warnings` | exit 0 | ✓ PASS |
| pyo3 clippy gate | `cargo clippy --all-targets -- -D warnings` (pyo3 crate) | exit 0 | ✓ PASS |
| rustfmt on all files touched since round 4 | `rustfmt --check` (8 files) | exit 0 | ✓ PASS |
| Debt-marker gate | grep TBD/FIXME/XXX + TODO/HACK/PLACEHOLDER on 10 touched files | 0 real markers (one false positive: `b"XXXX"` test bytes) | ✓ PASS |
| Windows-only test branches (share-lock plant, cfg(windows) backdate) | not executable on darwin | ? SKIP (platform; runs in windows-latest CI leg added by b514331; production code unaffected — 8f23225 is test-mod-only) |

### Probe Execution

Not applicable — no `scripts/*/tests/probe-*.sh` exist in the repository and none are declared
by any Phase-3 plan or SUMMARY (re-checked).

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
| ----------- | ------------ | ----------- | ------ | -------- |
| MERGE-01 | 03-01..05, 03-07, 03-09..17 | Default streaming path, no OOM at human scale; output correct | **MET** | bounded core + validation + conservation + order proofs on BOTH writers; suite 400/0 |
| MERGE-02 | 03-01, 03-04, 03-07, 03-09, 03-10 | Admission control, budget routing | **MET** | routing 17/17 + bounded 6/6 green |
| MERGE-03 | 03-02, 03-09, 03-11, 03-13 | Temp cleanup on any exit | **MET** | cleanup 9/9 green |
| MERGE-04 | 03-05, 03-10, 03-12 | PyDatabase merge uses the CLI's bounded path | **MET** | shared entry point re-read; **Python manifestation now behaviorally executed** (12/12 + 3-variant check) |
| DENSE-01 | 03-03, 03-06 | k ≤ 32 as u64 | **MET** | dense_memory/differential/proptest green; Dense table live |
| DENSE-02 | 03-03, 03-04, 03-08, 03-15..17 | Transparent to readers, byte identity | **MET** | golden_sha256 5/5; mixed-canonical queryability proven on BOTH writers |
| DENSE-03 | 03-03, 03-04 | Canonicalization/counts match u128 | **MET** | differential + proptest green |

Orphaned requirements: none — all 7 phase-3 IDs appear in REQUIREMENTS.md (all marked Complete,
Phase 3) and every ID is declared in at least one plan's `requirements` frontmatter (re-checked
this round). Step 9b deferred filtering: no gaps exist to defer.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| tests/merge_routing_tests.rs | 516 | `b"XXXX"` matched the XXX debt grep | — | false positive: 4 literal test bytes written to a header fixture, not a debt marker |
| src/hash/matrix.rs | 9 | "placeholder implementation" doc comment | ℹ️ info | pre-existing file, untouched by phase 03, not load-bearing for any truth |
| per 03-REVIEW-DISPOSITION.md | — | WR-01..WR-17, IN-01..IN-13 open (5 new this round: WR-15/16/17, IN-12/13) | ⚠/ℹ advisory | recorded open for developer triage; current review verdict critical: 0; no must-have depends on them |

Debt-marker gate: clean. The 3 suite-ignored tests are platform/flag-gated
(golden_generate regen flag, parallel_count platform arm, lib doctest), not skipped work.

### Human Verification Required

None. The single carried item (Python-surface rejection manifestation) was executed this round
by the verifier with a compatible-input control, after the maturin blocker (dbb13ef) lifted:
variants A (k=21+k=31) and B (mixed canonical) both raise PyRuntimeError with the prologue's
compatibility message and write no output file; the control merges successfully. The pyo3
contract suite ran 12/12 for the first time. No visual/UX/external-service items exist for
this phase (03-UAT.md: status complete, pending 0, blocked 0).

### Gaps Summary

No gaps. All eleven standing truths hold with re-executed behavioral evidence over the current
code. The staleness drivers were audited one by one: the only production-code change
(MultiGzDecoder) is a correct input-reading fix with its own green regression test and no
interaction with merge/dense truths; the prefix_cache_merge.rs change is test-module-only;
the test-binary narrowing removed only shared-helper self-tests (which still run in the
full-common binaries); formatting drift is fixed. The last open item from round 4 — the
never-executed Python-surface merge rejection — is now executed and green, closing WINDOWS.md
#16 in substance (row flip left to the developer). Advisory items (open warnings in
03-REVIEW-DISPOSITION.md, two stale WINDOWS.md ledger rows, pyo3 pytest --no-cov note,
63 fixture-missing Python skips) are developer-triage material, not phase-truth failures.

---

_Verified: 2026-10-17T09:28:19Z_
_Verifier: Claude (gsd-verifier)_
