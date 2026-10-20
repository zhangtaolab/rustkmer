---
phase: 03-memory-safety
verified: 2026-10-20T09:10:26Z
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
covered_digest: "v3:sha256:7a935a5a530728be0b43761e32475edf6b51926ca65994d603706cf747f1dfc4"
behavior_unverified: 0 # Count of PRESENT_BEHAVIOR_UNVERIFIED truths (present + wired, behavior not exercised); each is detailed in behavior_unverified_items below (and in human_verification when status is human_needed)
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 11/11
  gaps_closed: []  # no gaps were open — this round is a staleness refresh, not gap closure
  gaps_remaining: []
  regressions: []
advisory:
  - finding: "Stale pyrustkmer install in the default interpreter: /Users/forrest/miniconda3/lib/python3.13/site-packages/pyrustkmer/ is dated Jul 2 16:33 — BEFORE plan 03-10 landed merge_databases_to_path and plan 03-12 landed the merge kwargs. Running pytest against it would assert against code no longer on disk (exactly the trap STATE.md records for 03-07). The 2026-10-17 behavioral evidence (maturin develop from current source; test_database_merge.py 12/12; full pyo3 suite 125 passed / 0 failed) carries for the current tree because git diff 992e17c..HEAD shows ZERO changes under pyo3/src/ and pyo3/tests/ — only pyo3/pyproject.toml changed (pytest addopts de-cov'd), which does not affect the compiled extension."
    category: other
    reason: "Recorded so the next pyo3 test run rebuilds first (maturin develop) instead of trusting the stale site-packages copy; not a phase-truth failure."
    evidence_status: "git diff audited + module mtime/version checked by me this round"
  - finding: "WINDOWS.md ledger triaged 2026-10-20 (quick-261020-lec): 1 open / 6 waived / 11 fixed. The single open row #15 (a Python-level test driving a final merged-output write failure, asserting the 'Merge operation failed' prefix) is a /gsd-ship gate tied to ROADMAP backlog — not a phase-03 must-have: MERGE-04's truth (PyDatabase.merge routes through the CLI's bounded core) is behaviorally verified (2026-10-17: 12/12 contract suite + 3-variant rejection check with compatible-input control; pyo3/src unchanged since)."
    category: other
    reason: "Ship-gate bookkeeping outside this phase's truths; flagged so the orchestrator knows /gsd-ship still blocks on it."
    evidence_status: "STATE.md ledger note + WINDOWS.md triage records read by me"
  - finding: "gsd-tools `verify.artifacts` cannot parse this phase's plan frontmatter (all 17 plans declare must_haves.artifacts as annotated plain strings, e.g. 'src/database/format.rs (edited: ...)', not {path:} mappings) — it returns all_passed:false with total:0. Manual three-level artifact verification (as in every prior round) was used instead: existence via wc -l, substance via symbol greps at named lines, wiring via module declaration + call-site greps + green behavioral runs."
    category: other
    reason: "Tool/format mismatch, not an artifact failure; noted in case the plan frontmatter format is ever normalized."
    evidence_status: "tool JSON output (total: 0) inspected by me; manual checks re-executed this round"
  - finding: "The three post-verification source changes that drove this refresh were audited hunk-by-hunk: (1) 815aad5+957c069 fastq.rs WR-15/16/17 + IN-12 — helper correctness in INPUT reading only (gz-aware openers, honest count errors, raw-ASCII quality docs), each fix carrying its own new regression test, 13/13 module tests green; no merge/dense-format path touched. (2) b417e3a merge_bounded_memory_tests.rs IN-13 — replaced the two TAUTOLOGICAL premise asserts (estimated > budget where budget = estimated-1) with strict-positivity asserts before subtraction, making the guards MORE discriminating, plus Windows cfg-gating of measurement machinery; 6/6 green. (3) b6ea0ee pyproject.toml — coverage gate relocated from pytest addopts to a CI job; pure build/test config."
    category: other
    reason: "All quality improvements; none falsifies a must-have truth; each covered by a green behavioral run executed by me this round."
    evidence_status: "diffs read + targeted and full-suite runs executed by me this round"
---

# Phase 03: Memory Safety — Re-Verification Report (Round 6, staleness refresh)

**Phase Goal:** Bounded-memory merge operations and dense k-mer storage for the common k ≤ 32 case
**Verified:** 2026-10-20T09:10:26Z
**Status:** passed
**Re-verification:** Yes — staleness refresh. The round-5 report (2026-10-17, 11/11, passed) went stale because three covered files changed afterward via post-verification quick tasks: src/io/fastq.rs + tests/merge_bounded_memory_tests.rs (quick-261019-dwf: WR-15/16/17 + IN-12/13) and pyo3/pyproject.toml (quick-261019-d1y: coverage-gate relocation to CI). This round audits those diffs hunk-by-hunk, re-executes the full behavioral evidence chain on the current tree, and regenerates the covered-input fingerprint.

## Goal Achievement

Adversarial stance applied: I did not take the round-5 report, the SUMMARYs, or the caller's
context claims on faith. The git history since the round-5 verification commit (992e17c) was
enumerated commit-by-commit; the only source changes under src/, tests/, pyo3/src/, pyo3/tests/
are the two files named above (fastq.rs 200 lines changed, merge_bounded_memory_tests.rs 45) —
everything else is docs/.planning. Each changed hunk was read. The full cargo suite, both
clippy gates, and the three most affected test binaries were executed by me on the current
working tree, not inferred from any recorded claim.

### Observable Truths

| # | Truth | Status | Evidence (symbol check + behavioral run executed this round unless noted) |
|---|-------|--------|----------|
| 1 | DENSE-01: k ≤ 32 stored as u64, ~halving counting memory | ✓ VERIFIED | `CounterTable::Dense(DashMap<u64, u32>)` at src/hash/table.rs:40 and `uses_dense_storage()` at :199 re-grepped; dense_differential 6/6, dense_proptest 3/3, dense_memory 2/2 in the full suite I ran |
| 2 | Merge core respects memory budget; routes bounded (MERGE-02) | ✓ VERIFIED | merge_bounded_memory_tests 6/6 (run twice: standalone + in full suite) — including `streaming_merge_peak_memory_is_bounded_by_chunk_not_dataset` with the DE-TAUTOLOGIZED positivity guard; merge_routing_tests 17/17; `estimate_total_kmers`/`estimated_bytes_for_route` live in src/database/format.rs (:871) |
| 3 | In-memory and streaming routes produce identical data | ✓ VERIFIED | merge_route_parity_tests 5/5 green in the full suite I ran |
| 4 | Failed/interrupted merges clean up temp files (MERGE-03) | ✓ VERIFIED | merge_cleanup_tests 9/9 green; temp_lifecycle.rs RAII/sweep machinery intact (MERGE_TEMP_PREFIX :45, sweep_stale_merge_dirs) |
| 5 | u64/u128 counts + canonicalization match (DENSE-03) | ✓ VERIFIED | dense_differential 6/6 + dense_proptest 3/3 green in the suite I ran |
| 6 | PyDatabase merge shares the CLI's bounded path (MERGE-04) | ✓ VERIFIED | pyo3/src/database.rs:1457 calls `RKDatabase::merge_databases_to_path` (re-grepped; pyo3/src byte-identical since 992e17c per git diff — the 2026-10-17 source-built run: test_database_merge.py 12/12 + full pyo3 suite 125/0 + 3-variant rejection check with control, remains valid for identical source). NOTE: the miniconda site-packages extension is a stale Jul-2 build and was deliberately NOT used (see advisory) |
| 7 | .rkdb v2 byte-identity preserved (DENSE-02) | ✓ VERIFIED | golden_sha256_tests 5/5 + golden_tests 34/34 green in the suite I ran; src/database/format.rs untouched by every post-verification commit (git diff --stat) |
| 8 | Incompatible inputs rejected on EVERY route | ✓ VERIFIED | merge_routing_tests 17/17 green (kmer-size-mismatch, empty-list, header-validation, D-02 rejection test fns all in the binary I ran) |
| 9 | Prefix-cache bucket merge lossless for shards > one ~4 MB batch | ✓ VERIFIED | prefix_cache_conservation_tests 2/2 green in the suite I ran |
| 10 | Prefix-cache-merged database queryable correctly (sorted flag truthful) — mixed-canonical capability on BOTH bucket writers | ✓ VERIFIED | prefix_cache_output_order_tests 3/3 green in the suite I ran; both `pop_front` consumption sites present (src/database/prefix_cache_merge.rs:1004, :1032, re-grepped); `prefix_cache_route_still_merges_mixed_canonical` observed `ok` in my merge_routing run |
| 11 | CLI merge front-end does not materialize input databases | ✓ VERIFIED | `from_file_path` grep in src/cli/commands/merge.rs: exactly 2 matches, BOTH inside comments (:257 `//`, :363 `///`) — 0 production calls; merge_frontend_validation_tests 3/3 green |

**Score:** 11/11 truths verified (0 present-but-unverified; 0 failed)

### Post-Verification Change Audit (the staleness drivers)

| Change | Commit(s) | Files | Audit result |
|--------|-----------|-------|--------------|
| fastq helper fixes (WR-15/16/17) | 815aad5 | src/io/fastq.rs (+docs) | Input-reading helpers only: `total_sequence_length`/`average_quality` now route through the compression-aware opener; `count_sequences` propagates record-read errors instead of tallying malformed records; `filter_by_quality` raw-ASCII semantics documented + pinned. Each fix has its own new regression test. No merge/dense path touched. 13/13 module tests green (run by me) |
| MultiGzDecoder comment + trailing-garbage pin (IN-12) | 957c069 | src/io/fastq.rs | Comment accuracy fix + `test_read_all_errors_on_trailing_garbage_after_gzip_member` pin; green in my run |
| De-tautologize GUARD asserts (IN-13) | b417e3a | tests/merge_bounded_memory_tests.rs | The two premise asserts were `estimated > budget` with `budget = estimated - 1` (always true); now assert `estimated > 0` BEFORE subtraction — strictly more discriminating. Plus Windows cfg-gating of measurement-only imports/consts. 6/6 green (run by me, twice) |
| Coverage gate relocation | b6ea0ee | pyo3/pyproject.toml (+ci.yml, docs) | addopts reduced to `["-v"]`; 80% gate moved to a CI pyo3-pytest job. No effect on the compiled extension or phase logic; TOML parses (checked) |
| Review/security/validation refresh | 1b97178, 3c486bc, a868bad | .planning docs only | 03-REVIEW.md (2026-10-20): 0 critical / 0 warning / 3 info over exactly the 3 changed files; 03-SECURITY.md: verified, threats_open: 0; 03-VALIDATION.md: nyquist_compliant: true — all read by me |

### Required Artifacts

Step 4 note: `gsd-tools query verify.artifacts` returns total:0 for all 17 plans (their
must_haves.artifacts use annotated plain strings the tool cannot map to paths) — manual
three-level verification, as in every prior round.

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| src/hash/table.rs | Dense u64 table + accessors | ✓ VERIFIED | Dense(DashMap<u64,u32>) :40, uses_dense_storage :199; dense tests 11 total green |
| src/database/format.rs | estimator + bounded core | ✓ VERIFIED | estimate_total_kmers :871, estimated_bytes_for_route; unchanged since 992e17c; golden 5/5 + 34/34 |
| src/database/prefix_cache_merge.rs | override + refusal + both pop_front sites | ✓ VERIFIED | pop_front :1004/:1032 re-grepped; conservation 2/2 + output-order 3/3 green |
| src/database/temp_lifecycle.rs | RAII subdir + sweep | ✓ VERIFIED | MERGE_TEMP_PREFIX :45, sweep machinery intact; cleanup 9/9 green |
| src/io/fastq.rs | compression-aware helpers + regression tests (post quick-261019-dwf) | ✓ VERIFIED | 810 lines, wired via `pub mod fastq` (io/mod.rs:7), imported by count.rs:17 and used at :230/:253; 13/13 module tests green |
| tests/merge_bounded_memory_tests.rs | 6 bounded-memory proofs with non-tautological guards | ✓ VERIFIED | 896 lines; 6/6 green standalone AND in full suite |
| pyo3/pyproject.toml | valid build/test config | ✓ VERIFIED | TOML parses; addopts `["-v"]`; extension-module/maturin config intact |
| pyo3/src/database.rs + test_database_merge.py | MERGE-04 wiring + contract suite | ✓ VERIFIED | :1457 → merge_databases_to_path (re-grepped); files byte-identical to the 2026-10-17 source-built 12/12 run |

### Key Link Verification

Step 5 note: same frontmatter-format caveat as Step 4; wiring verified manually (greps) plus behaviorally (test runs).

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| PyDatabase.merge (Python) | bounded core | pyo3/src/database.rs:1457 → `RKDatabase::merge_databases_to_path` | ✓ WIRED | re-grepped this round; behaviorally proven 2026-10-17 on byte-identical source (12/12 + 3-variant rejection incl. control) |
| CLI execute_merge | to-path core (no materialization) | src/cli/commands/merge.rs — 0 production `from_file_path` | ✓ WIRED | grep re-run by me: only 2 comment matches (:257, :363); frontend validation tests 3/3 |
| every record leaving a shard buffer | last-key monotonicity check | both pop_front sites prefix_cache_merge.rs:1004, :1032 | ✓ WIRED | re-grepped; output-order tests 3/3 green |
| FASTQ compressed read path | full-member decode | fastq.rs MultiGzDecoder + compression-aware openers | ✓ WIRED | 13/13 module tests incl. multi-member, trailing-garbage, gzipped-helpers pins |
| Dense counter → .rkdb write | u64→u128 zero-extension, v2 bytes | KmerEntry path + golden/write-path differentials | ✓ WIRED | golden_sha256 5/5, dense_merge_integration 3/3, round_trip 23+8 green |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| prefix-cache merged output (both writer arms) | entries + header counts | canonicalized shards → override → writer | Yes — conservation + oracle-equality e2e green this round | ✓ FLOWING |
| merge route outputs | .rkdb bytes per route | real fixtures → estimator-routed core | Yes — route parity 5/5 green | ✓ FLOWING |
| FASTQ stats helpers | length/quality/count | real decompressed records (now gz-aware) | Yes — exact-value assertions on gzipped fixtures (new tests green) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full cargo suite (single full run) | `cargo test` | every binary `ok`, 0 failed anywhere; lib 241/0 (up from 237 — the 4 new fastq tests); exit 0 | ✓ PASS |
| merge_bounded_memory_tests (changed file) | `cargo test --test merge_bounded_memory_tests` | 6 passed / 0 failed | ✓ PASS |
| fastq module (changed source) | `cargo test --lib io::fastq` | 13 passed / 0 failed (incl. 4 new pins) | ✓ PASS |
| merge_routing_tests | `cargo test --test merge_routing_tests` | 17 passed / 0 failed | ✓ PASS |
| Root clippy gate | `cargo clippy --all-targets -- -D warnings` | exit 0 | ✓ PASS |
| pyo3 clippy gate | `cargo clippy --all-targets -- -D warnings` (pyo3/) | exit 0 | ✓ PASS |
| Debt-marker gate | grep TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER on both changed files | 0 matches | ✓ PASS |
| pyo3 pytest vs stale extension | not run — site-packages .so predates phase-03 merge work (Jul 2) | would assert against code no longer on disk | ? SKIP (recorded 2026-10-17 source-built evidence carries; see advisory) |

### Probe Execution

Not applicable — no `scripts/*/tests/probe-*.sh` exist in the repository and none are declared
by any Phase-3 plan or SUMMARY (re-checked).

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
| ----------- | ------------ | ----------- | ------ | -------- |
| MERGE-01 | 03-01..05, 03-07, 03-09..17 (12 plan claims) | Default streaming path, no OOM at human scale; output correct | ✓ SATISFIED | bounded core symbols re-grepped; suite all-green incl. bounded 6/6, parity 5/5, conservation 2/2, output-order 3/3 |
| MERGE-02 | 03-01, 03-04, 03-07, 03-09, 03-10 (5 claims) | Admission control, budget routing | ✓ SATISFIED | routing 17/17 + bounded 6/6 (de-tautologized guards) green this round |
| MERGE-03 | 03-02, 03-09, 03-11, 03-13 (4 claims) | Temp cleanup on any exit | ✓ SATISFIED | cleanup 9/9 green; sweep test in bounded binary green |
| MERGE-04 | 03-05, 03-10, 03-12 (3 claims) | PyDatabase merge uses the CLI's bounded path | ✓ SATISFIED | database.rs:1457 wiring re-grepped; pyo3/src unchanged since the 2026-10-17 source-built 12/12 + 125/0 run |
| DENSE-01 | 03-03, 03-06 (2 claims) | k ≤ 32 as u64 | ✓ SATISFIED | Dense table live (:40); dense_memory 2/2, differential 6/6, proptest 3/3 green |
| DENSE-02 | 03-03, 03-04, 03-08, 03-15..17 (8 claims) | Transparent to readers, byte identity | ✓ SATISFIED | golden_sha256 5/5 + golden_tests 34/34 green; mixed-canonical output-order 3/3 |
| DENSE-03 | 03-03, 03-04 (3 claims) | Canonicalization/counts match u128 | ✓ SATISFIED | differential 6/6 + proptest 3/3 green |

Orphaned requirements: none — all 7 phase-3 IDs appear in REQUIREMENTS.md (marked Complete,
Phase 3) and each is claimed by at least one plan's `requirements` frontmatter (counts
re-checked this round: MERGE-01×12, MERGE-02×5, MERGE-03×4, MERGE-04×3, DENSE-01×2,
DENSE-02×8, DENSE-03×3). Step 9b deferred filtering: no gaps exist to defer.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| src/io/fastq.rs | 419-436 | `count_sequences` now errors on malformed records (behavior change) | ℹ️ info | deliberate WR-16 fix with regression test; stricter, not stubbed |
| (none) | — | no TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER in either changed file; no empty-return/console-only stubs | — | clean |

Prior-round advisories (WR/IN rows in 03-REVIEW-DISPOSITION.md) were dispositioned by
quick-261019-dwf (WR-15/16/17 + IN-12/13 fixed — verified in code and tests this round) and
quick-261020-lec (ledger triage); the current incremental 03-REVIEW.md (2026-10-20) reads
0 critical / 0 warning / 3 info over exactly the three changed files.

### Human Verification Required

None. 03-UAT.md: status complete, pending 0, blocked 0. No `<verify><human-check>` blocks are
deferred in any phase-03 plan (re-checked). The single prior carried item (Python-surface
merge rejection) was behaviorally closed on 2026-10-17 and its evidence carries unchanged
(pyo3/src byte-identical since). No visual/UX/external-service items exist for this phase.

### Gaps Summary

No gaps. All eleven standing truths hold with behavioral evidence executed by me on the
current tree (full suite + both clippy gates + three targeted binaries). The three
staleness-driving changes were audited hunk-by-hunk: two are input-helper/test-quality
improvements with their own green regression tests and no interaction with merge or
dense-format truths; one is pytest/CI configuration. The report and its covered-input
fingerprint are regenerated over the current covered set. Advisory items (stale miniconda
pyrustkmer install — do not pytest against it without rebuilding; WINDOWS.md #15 ship-gate
row still open; verify.artifacts tool unable to parse annotated plan frontmatter) are
developer-triage material, not phase-truth failures.

---

_Verified: 2026-10-20T09:10:26Z_
_Verifier: Claude (gsd-verifier)_
