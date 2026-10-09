---
phase: 03-memory-safety
verified: 2026-10-09T12:27:48Z
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
  - "src/database/prefix_cache_merge.rs"
  - "tests/prefix_cache_output_order_tests.rs"
covered_digest: "v3:sha256:5b07c0a165bd7fb8808fe51e3c3bb053e89f4301e407d42b626bd6778e1c5806"
behavior_unverified: 0 # Count of PRESENT_BEHAVIOR_UNVERIFIED truths (present + wired, behavior not exercised); each is detailed in behavior_unverified_items below (and in human_verification when status is human_needed)
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 10/11
  gaps_closed:
    - "Truth 10, streaming-writer arm (round-3 gaps[0], WINDOWS #17): ExternalSortMerger::new now detects the mixed-canonical header set (folded canonical true + any input non-canonical) and overrides merge_mode to 'memory' with log::warn (prefix_cache_merge.rs:158-190), wired through self.merge_mode -> merge_mode_arc -> per-bucket writer selection (:482, :526-541) so a mixed-canonical merge can structurally never reach the streaming writer; merge_single_prefix_streaming refuses an adjacent descending run at BOTH pop_front consumption sites via a per-file last-key tracker (:947-1041, Err names shard path + both keys + the non-decreasing-run requirement; equal keys legal). The merge_mode='streaming' e2e arm (prefix_cache_output_order_tests.rs:573-665) passes with oracle equality, windows(2) strict ascending, total_kmers==oracle.len(), per-key query_kmer, negative query, ANY-input canonical header; override/same-mode-control/refusal unit tests 12/12; RED-first commit ordering verified by me via git show (test 3dbe18f lacks the override; fixes 43037f0/2fd1cb0 add it). Records closed: WINDOWS.md #17 status fixed with closure note; deferred-items.md entry status closed; both known-false comments gone (negative greps 0/0). Full suite 439 passed / 0 failed across 23 result lines; root and pyo3 clippy -D warnings exit 0; both touched files rustfmt-clean (all run by me). Fresh post-fix code review (03-REVIEW.md, 2026-10-09T12:18Z) independently traced every record-leaving path and confirms closure with critical: 0."
  gaps_remaining: []
  regressions: []
advisory:
  - finding: "Fresh post-03-17 code review (03-REVIEW.md, critical: 0, 6 warnings / 9 infos) open findings, all recorded open in the committed 03-REVIEW-DISPOSITION.md with file:line evidence: WR-01 (RAII Drop voids the failed-bucket 'shards preserved' promise — carried), WR-02 (u32 count overflow in bucket writers — carried), WR-11 (metadata JSON sidecar written to a path the to-path route deletes — new), WR-12 (ExternalSortMerger::new panics on empty input list — public API, new; sole in-crate caller guards it), WR-13 (zero-length merged buckets deleted under --keep-intermediate — new), WR-14 (no k-mer-size range validation; corrupt/foreign headers with k in 65..=127 or 0 pass checks — new; crate's own writers cannot produce these), IN-10 (streaming refusal aborts with no fallback hint), IN-11 (two vacuous pre-existing tests in the module's tests mod), plus carried WR-04..WR-10/IN-01..IN-09 from earlier rounds. None falsifies a must-have truth; all are developer-triage items."
    category: other
    reason: "All recorded open in the committed disposition record for developer triage; warning/info severity; no must-have depends on them. The disposition ledger's 'CR-01/CR-02/CR-03 open' rows are prior-round rows preserved by the keep-rule (Source: 'not in the current review') — the current review explicitly confirms all three closed; the stale 'open' disposition is ledger bookkeeping, not a live defect claim."
    evidence_status: "committed review + disposition records"
  - finding: "cargo fmt --check still fails on 21 hunks in 4 phase-03-untouched files (count.rs, merge_bounded_memory_tests.rs, merge_cleanup_tests.rs, parallel_count_tests.rs — rustfmt version drift, WINDOWS.md #18, open). Both 03-17-touched files are fmt-clean (rustfmt --check exit 0, verified by me)."
    category: other
    reason: "Pre-existing drift outside every phase-03 plan's scope; a human decides one cargo fmt commit vs a toolchain pin."
    evidence_status: "reproduced by me (rustfmt --check per-file exit 0 on both touched files); WINDOWS #18 open"
human_verification:
  - test: "Carried from round 2 (03-12 coverage D4): once the pyo3 maturin/pytest blocker lifts (python-source='.' + module-name='pyrustkmer' while pyo3/pyrustkmer/ has never existed, plus --cov-fail-under=80 addopts; WINDOWS.md entries 4/5/11 — blocker re-confirmed present by me this round), call pyrustkmer's PyDatabase.merge from Python on an incompatible input set (k=21 + k=31, or mixed canonical without prefix cache) under a streaming-selecting budget."
    expected: "PyRuntimeError carrying the prologue's compatibility message; no output file written."
    why_human: "The pyo3 test runner is blocked in-repo. The Rust-core rejection is behaviorally proven through the exact entry point Python calls (pyo3/src/database.rs -> merge_databases_to_path -> merge_prologue; merge_routing_tests 37/37 in the suite I ran), and pyo3/src is untouched since (git diff 005b280..HEAD over pyo3/src is empty) — but the end-to-end Python manifestation has never been executed."
---

# Phase 03: Memory Safety — Re-Verification Report (Round 4)

**Phase Goal:** Bounded-memory merge operations and dense k-mer storage for the common k ≤ 32 case
**Verified:** 2026-10-09T12:27:48Z
**Status:** human_needed
**Re-verification:** Yes — after gap-closure round 4 (03-17, the streaming-writer arm of truth 10)

## Goal Achievement

Round 4 executed plan 03-17 (commits 3dbe18f, 43037f0, 2fd1cb0, 62f7c47 — all verified
present, RED-first ordering confirmed by me via `git show` against each commit's tree).
I did not take the SUMMARY's word for the fix: I read the override and the refusal
backstop in the code, traced the wiring end-to-end, re-ran every discriminating test
binary myself, ran the full suite (439/0 across 23 result lines), and ran both clippy
gates. A fresh code review committed AFTER the fix (03-REVIEW.md, 2026-10-09T12:18Z)
independently traced every path by which a record can leave a shard buffer and confirms
the closure with **critical: 0**.

The round-3 gap is closed on all three `missing` items. All eleven standing truths now
hold with behavioral evidence and show no regressions. The only open item is the
carried human-verification item (pyo3 Python-surface manifestation), whose blocker
re-confirmed present — hence `human_needed`, not `passed`.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | DENSE-01: k ≤ 32 stored as u64, ~halving counting memory *(regression)* | ✓ VERIFIED | dense_differential + dense_proptest + dense_memory green in the 439/0 suite I ran; src/hash/table.rs untouched since round 3 (git diff 005b280..HEAD over src/, pyo3/src, tests/ = only the two 03-17 files) |
| 2 | Merge core respects memory budget; routes bounded *(regression)* | ✓ VERIFIED | merge_bounded_memory_tests green in suite; routing model untouched this round |
| 3 | In-memory and streaming routes produce identical data *(regression)* | ✓ VERIFIED | merge_route_parity_tests green in suite |
| 4 | Failed/interrupted merges clean up temp files (MERGE-03) *(regression)* | ✓ VERIFIED | merge_cleanup_tests green in suite; WR-01 carried advisory affects only the preserve-promise text |
| 5 | u64/u128 counts + canonicalization match (DENSE-03) *(regression)* | ✓ VERIFIED | differential + proptest green in suite |
| 6 | PyDatabase merge shares the CLI's bounded path (MERGE-04) *(regression)* | ✓ VERIFIED | pyo3/src/database.rs still calls `RKDatabase::merge_databases_to_path` (re-read by me); pyo3/src diff empty; pyo3 clippy -D warnings exit 0; Python manifestation remains the carried human item |
| 7 | .rkdb v2 byte-identity preserved (DENSE-02) *(regression)* | ✓ VERIFIED | golden_sha256_tests green in suite; zero format/writer edits this round (git diff over format.rs/streaming_merge.rs = 0) |
| 8 | Incompatible inputs rejected on EVERY route *(regression)* | ✓ VERIFIED | merge_prologue entry points untouched; merge_routing_tests 37/37 in the suite I ran |
| 9 | Prefix-cache bucket merge lossless for shards > one ~4 MB batch *(regression)* | ✓ VERIFIED | prefix_cache_conservation_tests 2/2 in suite (same-mode streaming fixtures NOT diverted by the new override) |
| 10 | Prefix-cache-merged database queryable correctly (sorted flag truthful) — mixed-canonical capability on BOTH bucket writers | ✓ VERIFIED | **Streaming arm closed this round.** Override: ExternalSortMerger::new (:158-190) forces "memory" when folded-canonical + any non-canonical input, log::warn included; wired :482 → :526-541 (self.merge_mode → Arc → writer selection) so mixed-canonical cannot reach the streaming writer. Backstop: merge_single_prefix_streaming refuses adjacent descending runs at BOTH pop_front sites (:947-1041), Err names shard + both keys; equal keys legal. Behavioral: `mixed_canonical_prefix_cache_output_is_ascending_summed_and_queryable` 3/3 including the merge_mode='streaming' arm (oracle equality, strict ascending, total_kmers, per-key query_kmer incl. Some(8) on the meet-and-sum key, negative query, ANY-input canonical header); unit tests 12/12 (override for streaming+auto, memory idempotent, same-mode control keeps streaming, refusal direct-call). RED-first ordering verified by me (git show: test commit 3dbe18f lacks the override; 43037f0/2fd1cb0 add it) |
| 11 | CLI merge front-end does not materialize input databases *(regression)* | ✓ VERIFIED | comment-filtered `from_file_path` count in merge.rs = 0 (re-run by me); merge.rs untouched; merge_frontend_validation_tests green in suite |

**Score:** 11/11 truths verified (0 present-but-unverified; 0 failed)

### Plan 03-17 Contract Truths (this round's gap-closure plan)

| # | 03-17 must-have truth | Status | Evidence |
|---|----------------------|--------|----------|
| T1 | Mixed-canonical + merge_mode="streaming" produces strictly ascending, oracle-equal, summed output under sorted: true (total_kmers 10, meet-and-sum key ONE record count 8) | ✓ VERIFIED | Streaming arm :573-665 — windows(2) strict ascending, decode_observations == oracle, total_kmers == oracle.len(); 3/3 run by me |
| T2 | query_kmer exact through binary search (Some(8) on the meet-and-sum key), None on asserted-absent; canonical: true ANY-input header; first/last == oracle min/max | ✓ VERIFIED | Same run — per-oracle-key query loop, negative query, boundary pins, header assertions all present and passing |
| T3 | Override forces 'memory' for streaming AND auto on mixed-canonical sets with log::warn; same-mode 'streaming' keeps the streaming writer | ✓ VERIFIED | Code :158-190 + :482/:526-541; unit tests mixed_canonical_inputs_force_the_sorting_bucket_writer (both requests), _requested_as_memory_stay_memory, same_mode_inputs_keep_the_requested_streaming_writer — 12/12 run by me |
| T4 | merge_single_prefix_streaming refuses an adjacent descending pair with Err naming shard + key pair; equal keys legal; Err propagates into the WR-04 bucket abort | ✓ VERIFIED | streaming_writer_refuses_a_descending_run (direct call, asserts Err text: shard path, 0x200/0x100, "non-decreasing") run by me; propagation is the same Result channel whose abort behavior failed_bucket_aborts_the_merge_with_err proves; dup-run/conservation tests confirm equal keys stay legal |
| T5 | Same-canonical-mode merges unchanged (03-15/03-16 order+parity, 03-13 conservation with streaming-pinned fixtures, unit tests) | ✓ VERIFIED | prefix_cache_output_order_tests 3/3, prefix_cache_conservation_tests 2/2, 12 lib tests — all run by me |
| T6 | Full root suite 0 failed; clippy -D warnings green on root AND pyo3; touched files rustfmt-clean | ✓ VERIFIED | cargo test: 439 passed / 0 failed across 23 result lines (3 ignored = platform-gated RSS arms, as previously accepted); root clippy exit 0; pyo3 clippy exit 0; rustfmt --check both files exit 0 — all run by me |

### Prohibition Disposition (03-17 must_haves.prohibitions)

All eight prohibitions hold. The seven `enforced` ones are covered by the passing
tests and greps above (both-arm strict-ascending, oracle map equality incl. no
over-merge, refusal unit test, golden sha256 green + git diff over format.rs = 0,
same-mode control + conservation, no query-path edits). The one `design-guard`
prohibition ("the guarantee must NOT be gated on header claims alone") is resolved
by design review performed this round: the run check reads the RECORDS — a per-file
last-key tracker compared against every record at both consumption sites
(:998-1002, :1037-1041) — and covers unsorted/mislabeled inputs of ANY canonical
mode and direct callers that bypass the header-keyed override. No header.sorted-based
gate exists anywhere in the writer.

### Re-Verification of the Round-3 Gap (full 3-level treatment)

**Level 1 (exists):** override block at prefix_cache_merge.rs:158-190; refusal
tracker + closure at :947-965 with checks at :998-1002 and :1037-1041; streaming
test arm at tests/prefix_cache_output_order_tests.rs:573-665; four new/extended unit
tests. **Level 2 (substantive):** the override rebinds `merge_mode` before the
struct is built and logs counts + reason; the refusal compares actual record keys
(strictly-less-only) and returns a descriptive `anyhow` error; the e2e arm asserts
value-level oracles, not smoke. **Level 3 (wiring):** overridden `self.merge_mode`
→ `merge_mode_arc` (:482) → writer selection (:526-541) — "memory" selects
`merge_single_prefix_hashmap` for every bucket; "streaming"/"auto" on same-mode sets
keep the streaming writer (control test). **Level 4 (data flow):** the e2e arm chains
real .rkdb inputs → public `merge_databases_to_path` → output read back through
`from_file_path` + `query_kmer` and compared against an input-only canonicalizing
oracle — real data end-to-end. **Behavioral:** every discriminating binary run by me,
all green; RED-first ordering established against commit trees; the round-3 verifier's
own pre-fix reproduction (identical fixture, identical corruption signature) stands as
the RED evidence. **Records:** WINDOWS.md #17 `fixed` with populated closure reason
and resolved_at; deferred-items.md entry `status: closed` with the closure note; both
known-false comments gone (negative greps both 0).

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/database/prefix_cache_merge.rs` | override + refusal + corrected comment + unit tests (03-17) | ✓ VERIFIED | All present and substantive (read by me); 12/12 unit tests run by me; rustfmt-clean |
| `tests/prefix_cache_output_order_tests.rs` | streaming arm + merge_mode-parameterized helper + corrected doc | ✓ VERIFIED | :573-665 arm with full oracle assertions; helper :124-127; 3/3 run by me |
| `.planning/WINDOWS.md` #17 / `deferred-items.md` | flipped to fixed/closed with 03-17 reference | ✓ VERIFIED | Both records read by me; ledger counts repaired (9 open/6 fixed/18 total) |
| regression artifacts (format.rs, streaming_merge.rs, temp_lifecycle.rs, merge_config.rs, stats.rs, table.rs, lib.rs, merge.rs, pyo3/src/database.rs + their test binaries) | unchanged/holding | ✓ VERIFIED | git diff 005b280..HEAD over src/, pyo3/src, tests/ touches ONLY the two 03-17 files; suite 439/0 |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| ExternalSortMerger::new canonical fold + non-canonical count | merger.merge_mode = "memory" | override :174-190 | ✓ WIRED | unit-pinned for "streaming" and "auto"; log::warn present |
| merger.merge_mode | per-bucket writer selection | merge_mode_arc :482 → :526-541 | ✓ WIRED | "memory" → hashmap writer for every bucket; the round-3 NOT_WIRED link is closed |
| every record leaving a shard buffer | per-file last-key monotonicity check | both pop_front sites :998-1002, :1037-1041 | ✓ WIRED | heap entry mirrors its file's buffer front; inner-loop duplicate consumption is the second exit — both validated |
| refusal Err | WR-04 bucket abort | generic Result channel :530 → error accounting | ✓ WIRED | abort behavior proven by failed_bucket_aborts_the_merge_with_err; no final header written on abort (concatenate never runs) |
| ANY-input canonical | output header canonical flag | ExternalSortMerger::new (:148-155) → concatenate header | ✓ WIRED | pinned both input orders (merge_routing_tests 37/37) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| prefix-cache output (auto/hashmap arm) | entries + header counts | canonicalized shards → map-fold → sort → concatenate | Yes — oracle-proven, query-proven | ✓ FLOWING |
| prefix-cache output (requested streaming, mixed-canonical) | entries + header counts | override → hashmap writer (same as above) | Yes — the streaming e2e arm's oracle equality, total_kmers, and per-key query assertions all pass | ✓ FLOWING (the round-3 DISCONNECTED row is closed) |
| prefix-cache output (streaming writer, ascending-run inputs) | entries under sorted: true | heap merge over validated non-decreasing runs | Yes — conservation tests (2/2) on >4 MB shards; descending runs now refused, never emitted | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Mixed-canonical order/summing/query proof, BOTH writer arms (auto/hashmap + requested streaming) | `cargo test --test prefix_cache_output_order_tests` | 3 passed, 0 failed | ✓ PASS |
| Override + same-mode control + refusal + conservation unit layer | `cargo test --lib prefix_cache_merge` | 12 passed, 0 failed | ✓ PASS |
| Routing rejections + capability guard + ANY-input header pins | `cargo test` (merge_routing_tests binary in full run) | 37 passed, 0 failed | ✓ PASS |
| >4 MB bucket conservation through the streaming writer (same-mode, not diverted) | `cargo test` (prefix_cache_conservation_tests binary) | 2 passed, 0 failed | ✓ PASS |
| RED-first ordering of the fix | `git show <commit>:file \| grep` on 3dbe18f / 43037f0 / 2fd1cb0 | override count 0 → 1; refusal 0 → 1; streaming arm present at test commit | ✓ PASS (deterministic) |
| Full-suite regression | `cargo test` | 439 passed, 0 failed across 23 result lines (3 ignored, platform-gated) | ✓ PASS |
| Clippy gates | `cargo clippy --all-targets -- -D warnings` (root + pyo3) | both exit 0 | ✓ PASS |
| rustfmt on both touched files | `rustfmt --check <files>` | exit 0 | ✓ PASS |
| Negative comment gates | `grep -c 'every bucket writer emits ascending' tests/...` and `grep -c 'the bucket writers sum' src/...` | both 0 | ✓ PASS |
| RSS-ratio arms | Linux-gated | not executed — darwin host | ? SKIP (platform; correctly cfg-gated, as previously accepted) |

### Probe Execution

Not applicable — no `scripts/*/tests/probe-*.sh` exist in the repository (re-checked)
and none are declared by any Phase-3 plan or SUMMARY.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| MERGE-01 | 03-01..05, 03-07, 03-09..17 | Default streaming path, no OOM at human scale; output correct | **MET** (gap closed) | bounded core + validation + conservation + order proofs on BOTH writers; 439/0 |
| MERGE-02 | 03-01, 03-04, 03-07, 03-09, 03-10 | Admission control, budget routing | **MET** | routing tests green |
| MERGE-03 | 03-02, 03-09, 03-11, 03-13 | Temp cleanup on any exit | **MET** | cleanup tests green |
| MERGE-04 | 03-05, 03-10, 03-12 | PyDatabase merge uses the CLI's bounded path | **MET** | shared entry point re-read; inherited prologue; Python manifestation carried as the human item below |
| DENSE-01 | 03-03, 03-06 | k ≤ 32 as u64 | **MET** | regression green |
| DENSE-02 | 03-03, 03-04, 03-08, 03-15..17 | Transparent to readers, byte identity | **MET** (gap closed) | golden differential green; mixed-canonical queryability now proven on BOTH bucket writers |
| DENSE-03 | 03-03, 03-04 | Canonicalization/counts match u128 | **MET** | differential + proptest green |

Orphaned requirements: none — all 7 phase-3 IDs appear in REQUIREMENTS.md (all marked
Complete, Phase 3) and across plan frontmatter (03-17 declares MERGE-01, DENSE-02).
Step 9b deferred filtering: no gaps exist to defer; the milestone's Phase 4
(BENCH-01..04) covers performance measurement only.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (none in the two touched files) | — | debt-marker greps TBD/FIXME/XXX and TODO/HACK/PLACEHOLDER both return 0 matches | — | debt-marker gate clean |
| per 03-REVIEW-DISPOSITION.md | — | WR-01/02/04..14, IN-01..11 open (6 new warnings, 2 new infos this round) | ⚠/ℹ advisory | carried advisory; recorded open for developer triage; no must-have depends on them |

Debt-marker gate: clean. The 3 suite-ignored tests are the previously accepted
Linux-gated RSS-ratio arms (`/proc/self/status`), not skipped work.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| tests/prefix_cache_output_order_tests.rs | MERGE-01, DENSE-02 | 3 (incl. the two-writer mixed-canonical proof) | 0 | 0 (oracle is input-only, folds through the production canonicalizer) | Behavioral (value + e2e, both writer arms) | SUFFICIENT |
| tests/merge_routing_tests.rs | MERGE-01, MERGE-02, MERGE-04 | 37 | 0 | 0 | Behavioral | SUFFICIENT |
| tests/prefix_cache_conservation_tests.rs | MERGE-01, MERGE-03 | 2 | 0 | 0 (input-only oracle) | Behavioral | SUFFICIENT |
| prefix_cache_merge.rs tests mod | MERGE-01 | 12 | 0 | 0 (direct shard construction pins the writer contract independently of the override) | Behavioral (unit) | SUFFICIENT (IN-11's two vacuous tests are pre-existing struct checks, outside the 03-17 proofs) |

### Human Verification Required

### 1. Carried: Python-surface rejection manifestation (03-12 D4)

**Test:** Once the pyo3 maturin/pytest blocker lifts, call `PyDatabase.merge` from
Python on a k=21 + k=31 input set (and mixed canonical without prefix cache) under a
streaming-selecting budget.
**Expected:** `PyRuntimeError` carrying the prologue's compatibility message; no
output file.
**Why human:** the pyo3 test runner is blocked in-repo (python-source/module-name
pairing + cov-fail-under addopts — re-confirmed present this round); the Rust-core
rejection is proven through the exact entry point Python calls, but the end-to-end
Python manifestation has never been executed.

### Gaps Summary

No gaps. The round-3 gap (truth 10's streaming-writer arm) is fully closed with
behavioral evidence on both layers: the header-keyed override makes a mixed-canonical
merge structurally incapable of reaching the streaming bucket writer, and the
record-level descending-run refusal backstops every other path (unsorted or
mislabeled inputs of any canonical mode, direct callers). The e2e streaming arm, the
unit layer (12/12), the full suite (439/0), both clippy gates, and the RED-first
commit ordering were all verified by me, and a fresh post-fix code review
independently confirms closure with zero critical findings. The records (WINDOWS #17,
deferred-items) are properly closed. The remaining advisory items (open warnings in
03-REVIEW-DISPOSITION.md, pre-existing cargo fmt drift in 4 untouched files) are
developer-triage material, not phase-truth failures. The single outstanding item is
the carried human verification of the Python-surface manifestation, blocked by the
pyo3 tooling issue — the phase is otherwise complete at 11/11.

---

_Verified: 2026-10-09T12:27:48Z_
_Verifier: Claude (gsd-verifier)_
