---
phase: 03-memory-safety
verified: 2026-10-09T06:16:15Z
status: gaps_found
score: 10/11 must-haves verified
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
  - "pyo3/src/database.rs"
  - "pyo3/tests/test_database_merge.py"
  - "src/cli/commands/merge.rs"
  - "src/database/format.rs"
  - "src/database/merge_config.rs"
  - "src/database/prefix_cache_merge.rs"
  - "src/database/stats.rs"
  - "src/database/streaming_merge.rs"
  - "src/database/temp_lifecycle.rs"
  - "src/hash/mod.rs"
  - "src/hash/table.rs"
  - "src/lib.rs"
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
  - "tests/prefix_cache_conservation_tests.rs"
  - "tests/prefix_cache_output_order_tests.rs"
covered_digest: "v3:sha256:11751295a495261b2be186e89538fc948f016ccd8ca9084d2d3a61f6804ad6b6"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 10/11
  gaps_closed:
    - "Truth 10, hashmap/auto arm (fresh-review round-2 CR-01): split_files_by_prefix now writes the canonicalized processed_kmer (bucket key == stored key, prefix_cache_merge.rs:308-318) and propagates canonicalization errors via `?` (unwrap_or(entry.kmer) grep count 0). Mixed-canonical merges through the auto/hashmap per-bucket writer are globally ascending, oracle-summed, and exactly queryable — mixed_canonical_prefix_cache_output_is_ascending_summed_and_queryable green (run by me), RED evidence on both defect axes recorded pre-fix in 03-16-SUMMARY (order pair 0xffffffff -> 0x1000000; un-summed 0xFFFFFFFF:3 + 0x000000:5 vs oracle 8). ANY-input canonical header pinned non-coincidentally in BOTH input orders (merge_routing_tests.rs:1296-1330, 37/37 run by me); the misdescribed input[0]-mode comment is gone (grep count 0). Full root suite 435/0 across 23 binaries + root and pyo3 clippy -D warnings green (all run by me)."
  gaps_remaining:
    - "Truth 10, streaming-writer arm: the SAME mixed-canonical capability is still broken when the per-bucket streaming writer is used — merge_mode='streaming' (a documented public MergeConfig field and CLI flag) or auto with any bucket over the per-bucket threshold. Empirically reproduced by me in-repo (see gaps[0]): non-ascending output (key 0x000000 emitted twice, at positions 0 and 9) under header sorted=true, and query_kmer returns Some(5) where the oracle is Some(8). Logged by the executor as WINDOWS.md #17 / deferred-items.md and confirmed critical by the fresh 03-REVIEW.md CR-01."
  regressions: []
gaps:
  - truth: "Prefix-cache-merged database queryable correctly (sorted flag truthful) — the mixed-canonical capability through the per-bucket STREAMING writer (merge_mode='streaming', or auto for any bucket whose shards exceed the per-bucket threshold)"
    status: failed
    reason: "merge_single_prefix_streaming (src/database/prefix_cache_merge.rs:814-971) is a k-way BinaryHeap merge that assumes every shard is an ascending run. Post-03-16, split_files_by_prefix stores the CANONICALIZED key but appends records in input-stream (raw-key) order, so a NON-canonical input's shard in a mixed set need not be ascending. Verified empirically in-repo via public API on the 03-16 fixture (build_mixed_canonical_inputs inputs) with MergeConfig{use_prefix_cache: true, merge_mode: 'streaming'}: output entries [(0,5),(1,9),(171,6),(65536,5),(65537,11),(4194304,4),(8327732,2),(11239507,4),(16716340,7),(0,3),(16777216,13)] — key 0 appears twice (positions 0 and 9), windows(2) ascending=false, header sorted=true total_kmers=11 (oracle: 10 unique, 0x000000 summed to 8), and query_kmer on the all-A key returns Some(5) instead of Some(8) — the binary-search consumer is silently wrong on a header claiming sorted. Identical inputs through the hashmap writer (merge_mode='memory') are correct (ascending=true, content==oracle). This falsifies 03-16's own unqualified must-have truths 1-3 (ascending output / summed encodings / exact query answers) on a documented, CLI-reachable configuration, and it is the same damage class the user triaged fix-in-phase on 2026-10-09 (03-VERIFICATION human decision item 1)."
    artifacts:
      - path: "src/database/prefix_cache_merge.rs"
        issue: "merge_single_prefix_streaming (:814-971) heap-merges assuming ascending shard runs and consumes only run-adjacent duplicates (:946-951); split_files_by_prefix (:291-328) writes canonical values in raw stream order; concatenate_final_output writes sorted: true unconditionally (~:1264); the comment at :302-304 ('what lets the bucket writers sum...') is false for the streaming writer"
      - path: "tests/prefix_cache_output_order_tests.rs"
        issue: "the mixed-canonical proof exercises only the auto/hashmap writer (tiny inputs); the config-helper comment at :94-96 ('every bucket writer emits ascending') is false for the streaming writer on mixed-canonical input"
    missing:
      - "Make the stored-key ordering guarantee hold for EVERY writer, or refuse configurations that break it — e.g. (a) in ExternalSortMerger::new, when self.canonical is true and any input is non-canonical, force the sorting (hashmap) writer for all buckets and log the override; or (b) have merge_single_prefix_streaming validate its runs and fail loudly on the first adjacent descending pair; or (c) sort each shard by stored key before the bucket phase reads it"
      - "Extend mixed_canonical_prefix_cache_output_is_ascending_summed_and_queryable with a merge_mode='streaming' arm (tiny inputs, explicit streaming writer) asserting the same ascending + summed + queryable oracles so this regression cannot recur untested"
      - "Correct the :302-304 comment in prefix_cache_merge.rs and the :94-96 comment in prefix_cache_output_order_tests.rs"
advisory:
  - finding: "Carried open findings from the fresh 03-REVIEW.md / 03-REVIEW-DISPOSITION.md (22 rows, all recorded open with file:line evidence): WR-01 (RAII Drop voids the failed-bucket 'shards preserved' logging promise — cleanup itself holds), WR-02 (u32 count overflow in bucket writers), WR-04 (--batch-size CLI no-op), WR-05 (--check-compatibility --use-prefix-cache contradicts the merge), WR-06 (validate_merge_compatibility panics on empty slice — unreachable from execute_merge), WR-07..WR-10 (pyo3/reader robustness, pre-existing), IN-01..IN-09 (incl. IN-09: the 03-16 error-propagation comment describes a failure mode canonical_kmer_u128 cannot produce — vacuous-but-harmless future-proofing). None touches a must-have truth other than the gap above."
    category: other
    reason: "All recorded open in the committed disposition record for developer triage; warning/info severity; no additional must-have depends on them."
    evidence_status: "committed review + disposition records"
  - finding: "cargo fmt --check fails on 21 hunks in 4 files no phase-03 commit touches (count.rs, merge_bounded_memory_tests.rs, merge_cleanup_tests.rs, parallel_count_tests.rs — rustfmt version drift, WINDOWS.md #18). All three 03-16-touched files are fmt-clean (rustfmt --check per-file exit 0, verified by me). The 03-16 D4 human_judgment record (reformat vs pin toolchain) stands."
    category: other
    reason: "Pre-existing drift outside every phase-03 plan's scope; a human decides one cargo fmt commit vs a toolchain pin."
    evidence_status: "reproduced by me (cargo fmt --check diff listing); per-file cleanliness verified"
human_verification:
  - test: "Carried from round 2 (03-12 coverage D4): once the pyo3 maturin/pytest blocker lifts (python-source/module-name pairing + --cov-fail-under addopts, WINDOWS.md entries 4/5/11), call pyrustkmer's PyDatabase.merge from Python on an incompatible input set (k=21 + k=31, or mixed canonical without prefix cache) under a streaming-selecting budget."
    expected: "PyRuntimeError carrying the prologue's compatibility message; no output file written."
    why_human: "The pyo3 test runner is blocked in-repo. The Rust-core rejection is behaviorally proven through the exact entry point Python calls (pyo3/src/database.rs:1457 -> merge_databases_to_path -> merge_prologue; merge_routing_tests 37/37), and pyo3/src is untouched since (empty diff vs HEAD, clippy -D warnings green) — but the end-to-end Python manifestation has never been executed."
---

# Phase 03: Memory Safety — Re-Verification Report (Round 3)

**Phase Goal:** Bounded-memory merge operations and dense k-mer storage for the common k ≤ 32 case
**Verified:** 2026-10-09T06:16:15Z
**Status:** gaps_found
**Re-verification:** Yes — after gap-closure round 3 (03-16, user triage of round-2 human decision item 1)

## Goal Achievement

Round 3 executed the user's fix-in-phase triage via plan 03-16 (commits b0b4189, 90c4285,
a347b61, 9cd7795 — all verified present). The one-site fix is genuinely in the code and
genuinely works — **on the per-bucket hashmap writer**, which is what the default `auto`
mode selects for small buckets and what the new e2e test exercises. I re-ran every
discriminating test binary myself (all green), the full root suite (435/0 across 23
binaries), and both clippy gates (exit 0).

But the fresh code review's new CR-01 is correct, and I did not take its word for it: I
**reproduced the defect myself, in-repo, through the public API** on the 03-16 fixture
with `MergeConfig { use_prefix_cache: true, merge_mode: "streaming" }`. The streaming
per-bucket writer — selected by the documented, CLI-reachable `--merge-mode streaming`,
and auto-selected for any bucket whose shards exceed the per-bucket threshold — emits
**non-ascending output containing an un-summed duplicate record under a header claiming
`sorted: true`**, and `query_kmer` then returns `Some(5)` where the oracle is `Some(8)`.
Same inputs through the hashmap writer are correct. This is the same silent-corruption
damage class the user triaged fix-in-phase, on the bounded-memory arm of this
bounded-memory phase, so it is filed as a gap rather than absorbed: the commissioned
capability is half-fixed, and 03-16's own must-have truths 1-3 are written without a
writer qualifier that would excuse it.

Ten of the eleven standing truths hold with behavioral evidence and show no regressions.
The remaining one is truth 10, now failed on a precisely-scoped subset.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | DENSE-01: k ≤ 32 stored as u64, ~halving counting memory *(regression)* | ✓ VERIFIED | `CounterTable::Dense(DashMap<u64,u32>)`/`Wide(DashMap<u128,u32>)` (table.rs) unchanged since 03-06/03-09; dense_differential + dense_proptest + dense_memory green in the 435/0 suite I ran |
| 2 | Merge core respects memory budget; routes bounded *(regression)* | ✓ VERIFIED | merge_bounded_memory_tests green in suite; routing model unchanged this round |
| 3 | In-memory and streaming routes produce identical data *(regression)* | ✓ VERIFIED | merge_route_parity_tests (incl. 2M/16M arms) green in suite |
| 4 | Failed/interrupted merges clean up temp files (MERGE-03) *(regression)* | ✓ VERIFIED | merge_cleanup_tests green in suite; WR-01 carried advisory affects only the preserve-promise text |
| 5 | u64/u128 counts + canonicalization match (DENSE-03) *(regression)* | ✓ VERIFIED | differential + proptest green in suite |
| 6 | PyDatabase merge shares the CLI's bounded path (MERGE-04) *(regression)* | ✓ VERIFIED | pyo3/src/database.rs:1457 calls `merge_databases_to_path`; pyo3/src diff vs HEAD empty; pyo3 clippy -D warnings exit 0 (run by me); Python manifestation still human-blocked (carried item) |
| 7 | .rkdb v2 byte-identity preserved (DENSE-02) *(regression)* | ✓ VERIFIED | golden_sha256_tests green in suite; fixtures unchanged |
| 8 | Incompatible inputs rejected on EVERY route *(regression)* | ✓ VERIFIED | merge_prologue at both entry points (format.rs:1261, :1348); merge_routing_tests 37/37 run by me |
| 9 | Prefix-cache bucket merge lossless for shards > one ~4 MB batch *(regression)* | ✓ VERIFIED | prefix_cache_conservation_tests 2/2 run by me; reader/writer mechanics unchanged by 03-16 |
| 10 | Prefix-cache-merged database queryable correctly (sorted flag truthful) — mixed-canonical capability | ✗ FAILED (scoped: streaming-writer arm) | **Hashmap/auto arm VERIFIED:** fix at :308-318 (`processed_kmer.to_le_bytes()` written, `?` propagation), negative gates pass (`unwrap_or(entry.kmer)` count 0); `mixed_canonical_prefix_cache_output_is_ascending_summed_and_queryable` green (run by me) — ascending, oracle-summed, exact queries, ANY-input canonical header; same-mode 03-15 proofs stay green. **Streaming arm FAILED (my reproduction):** `merge_mode: "streaming"` output `[(0,5),…,(0,3),…]` — key 0 emitted twice, `ascending: false`, header `sorted=true total_kmers=11` vs oracle 10 unique, `query_kmer(all-A key) = Some(5)` vs oracle `Some(8)`; hashmap control arm on identical inputs correct. Mechanism code-confirmed: :291-328 appends canonical values in raw stream order; :814-971 heap-merges assuming ascending runs; header `sorted: true` unconditional. Falsifies 03-16 truths 1-3 as written (no merge_mode qualifier). See gaps[0], WINDOWS.md #17, 03-REVIEW.md CR-01 |
| 11 | CLI merge front-end does not materialize input databases *(regression)* | ✓ VERIFIED | comment-filtered `from_file_path` count in merge.rs = 0; merge_frontend_validation_tests 3/3 run by me |

**Score:** 10/11 truths verified (0 present-but-unverified; 1 failed on a scoped subset)

### Plan 03-16 Contract Truths (this round's gap-closure plan)

| # | 03-16 must-have truth | Status | Evidence |
|---|----------------------|--------|----------|
| T1 | Mixed-canonical output strictly ascending (windows(2)) under sorted: true | ✗ FAILED on the streaming-writer subset / ✓ VERIFIED on auto+hashmap | My repro: `ascending: false` under `sorted=true` with merge_mode="streaming"; the committed test proves the auto/hashmap arm (3/3 green) |
| T2 | Raw+canonical encodings sum into ONE record per the input-only oracle | ✗ FAILED on streaming subset (0x000000 emitted as two records 5 and 3; total_kmers 11 vs oracle 10) / ✓ VERIFIED on auto+hashmap | Same runs as T1 |
| T3 | query_kmer exact for every oracle key; None for asserted-absent | ✗ FAILED on streaming subset (Some(5) vs Some(8)) / ✓ VERIFIED on auto+hashmap | Same runs as T1 |
| T4 | ANY-input canonical header pinned in BOTH input orders | ✓ VERIFIED | Code :148-155; merge_routing_tests.rs:1296-1330 (reversed order, input[0] NON-canonical, asserts canonical==true); old comment gone (grep 0); 37/37 run by me |
| T5 | Canonicalization failure propagates; swallowed fallback gone | ✓ VERIFIED | :309 `?` on canonical_kmer_u128; `unwrap_or(entry.kmer)` grep count 0 (run by me). Note IN-09: vacuous today (the fn is infallible) — the code shape is as claimed; the comment overstates the closed hole |
| T6 | Same-canonical-mode merges unchanged (03-15 + 03-13 tests green) | ✓ VERIFIED | prefix_cache_output_order_tests 3/3 + prefix_cache_conservation_tests 2/2 run by me |
| T7 | Full root suite passes; clippy -D warnings green on root AND pyo3 | ✓ VERIFIED | `cargo test`: 435 passed / 0 failed across 23 result lines (run by me); root clippy exit 0; pyo3 clippy exit 0. (cargo fmt --check fails only on 4 phase-untouched files — pre-existing drift, WINDOWS.md #18; all 3 touched files fmt-clean, verified by me) |

### Re-Verification of the Round-2 Escalation (full 3-level treatment)

**Human decision item 1 (mixed-canonical CR-01 disposition) — PARTIALLY executed.**
Level 1 (exists): the one-site fix is in `split_files_by_prefix`. Level 2 (substantive):
the shard stores the canonicalized `processed_kmer` (:317) with `?` propagation (:309);
RED evidence on both defect axes is recorded verbatim in 03-16-SUMMARY (order pair
`0xffffffff -> 0x1000000`; un-summed `0xFFFFFFFF: 3` + `0x000000: 5` vs oracle `8`) and
the commits exist in history (verified). Level 3 (wiring): bucket key, sort key, and
stored key are now the same value through `get_prefix_4mer` (:314) — the identity holds
end-to-end **into the hashmap writer**, which folds to a map and sorts (:734, :777-778),
so its output is ascending regardless of shard order. Level 4 (data flow): the auto-path
proof chains input records → canonicalizing oracle → merged output → binary-search
query answers, all real. **The hole:** the same identity does NOT hold *into the
streaming writer*. `merge_single_prefix_streaming` (:857-971) seeds a BinaryHeap with
each shard's front entry and pops assuming ascending runs; a non-canonical input's shard
now stores canonical values in raw-key stream order (my repro's shard sequence per
deferred-items #17: `0x0000AB, 0x007F1234, 0x00AB8053, 0x00FF1234, 0x000000` — not
ascending), so the k-way merge emits out of order and misses non-adjacent duplicates,
while `concatenate_final_output` still writes `sorted: true` unconditionally. The
executor discovered this during Task 2, logged it honestly (03-16-SUMMARY Issues,
deferred-items.md, WINDOWS.md #17, "Rule 4 scale"), and the fresh review (03-REVIEW.md
CR-01, committed after the summary) proved it empirically in a scratch crate. My own
in-repo reproduction (scratch integration test, since deleted; public API only;
hashmap control arm isolating the writer as the variable) confirms it deterministically.

**Why FAILED rather than UNCERTAIN or advisory:** round 2's UNCERTAIN classification
rested on an open scope question — is this opt-in sub-capability in-phase? — which the
user answered on 2026-10-09: fix in phase. What remains is not a judgment call but an
empirically reproduced failure inside the commissioned capability, on a documented
public configuration (`MergeConfig.merge_mode`, advertised "auto/memory/streaming" and
settable via the CLI `--merge-mode` flag, merge.rs:137/:200), with the same
silent-wrong-query damage class the triage was meant to end. The re-verification
evidence gate does not soften it: the flagged file was modified by this round's own
gap-closure commit (a347b61), and the finding carries deterministic evidence (my
reproduction command + output below). Precedent cuts the same way — the round-2
half of this same defect, same damage class, same capability, was escalated and the
user chose a fix, not an acceptance.

### Quick Regression of the Ten Standing Truths

All re-checked at existence + wiring + suite level: no regressions. Key wirings re-read:
prologue first-statement at both entry points (format.rs:1261/:1348), pyo3 :1457
untouched (empty diff vs HEAD), CLI `from_file_path` count still 0, dense table last
touched by 03-09. Full `cargo test`: **435 passed, 0 failed** (23 result lines, 0
ignored) — exactly the recorded baseline 434 + the one new 03-16 test.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/database/prefix_cache_merge.rs` | split_files_by_prefix stores canonicalized key, propagates errors (03-16) | ✓ VERIFIED (with the streaming-writer residual — gaps[0]) | :308-318 fix + `?`; negative gates pass; unit tests 8/8 via suite |
| `tests/prefix_cache_output_order_tests.rs` | mixed-canonical e2e proof + fixture helper with honesty guards | ✓ VERIFIED (scope: auto/hashmap writer — the streaming arm is untested; :94-96 comment now known-false) | 3/3 run by me; windows(2) count 3, canonical_kmer_u128 count 8 |
| `tests/merge_routing_tests.rs` | ANY-input header pin in both orders, corrected comment | ✓ VERIFIED | :1296-1330; 37/37 run by me |
| regression artifacts (format.rs, streaming_merge.rs, temp_lifecycle.rs, merge_config.rs, stats.rs, table.rs, lib.rs, merge.rs, pyo3/src/database.rs + their test binaries) | unchanged/holding | ✓ VERIFIED | suite 435/0; wirings re-grepped |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| split_files_by_prefix stored key | get_prefix_4mer bucket key | both derived from processed_kmer (:308-317) | ✓ WIRED | the CR-01 identity holds — into the hashmap writer |
| stored-key ordering → streaming writer ascending-run assumption | merge_single_prefix_streaming heap (:857-971) | assumed, not enforced | ✗ NOT_WIRED for mixed-canonical input | shard order is raw-stream order, not canonical order — the assumption the writer depends on is exactly what the fix broke for non-canonical inputs; gaps[0] |
| ANY-input canonical | output header canonical flag | ExternalSortMerger::new (:148-155) → concatenate header | ✓ WIRED | pinned both input orders |
| canonicalization failure | Err out of split_files_by_prefix | `?` (:309) | ✓ WIRED | vacuous today (IN-09) but the propagation path is real |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| prefix-cache output (auto/hashmap) | entries + header counts | canonicalized shards → map-fold → sort → concatenate | Yes — oracle-proven, query-proven | ✓ FLOWING |
| prefix-cache output (streaming writer, mixed-canonical) | entries under sorted: true | canonical-in-raw-order shards → heap merge assuming ascending runs | Content present but order/summing wrong — header claim disconnected from content | ✗ DISCONNECTED (the sorted:true claim has no enforcing data flow on this arm) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Mixed-canonical auto/hashmap: ascending + summed + queryable + ANY-input header | `cargo test --test prefix_cache_output_order_tests` | 3 passed, 0 failed | ✓ PASS |
| Routing rejections + capability guard + reversed-order ANY pin | `cargo test --test merge_routing_tests` | 37 passed, 0 failed | ✓ PASS |
| >4 MB bucket conservation + Err pin | `cargo test --test prefix_cache_conservation_tests` | 2 passed, 0 failed | ✓ PASS |
| CLI header-only validation + real-binary smoke | `cargo test --test merge_frontend_validation_tests` | 3 passed, 0 failed | ✓ PASS |
| **Streaming-writer mixed-canonical (GAP reproduction)** | scratch integration test (public API, 03-16 fixture, `merge_mode: "streaming"`; file created, run, deleted) | entries `[(0,5),(1,9),(171,6),(65536,5),(65537,11),(4194304,4),(8327732,2),(11239507,4),(16716340,7),(0,3),(16777216,13)]`; `ascending: false`; header `sorted=true canonical=true total_kmers=11`; `query_kmer(all-A key) = Some(5)` (oracle 8); hashmap control arm: `ascending=true`, content==oracle | ✗ FAIL (deterministic — this is gaps[0]) |
| Full-suite regression | `cargo test` | 435 passed, 0 failed (23 result lines) | ✓ PASS |
| Clippy gates | `cargo clippy --all-targets -- -D warnings` (root + pyo3) | both exit 0 | ✓ PASS |
| RSS-ratio arms | Linux-gated | not executed — darwin host | ? SKIP (platform; correctly cfg-gated, as previously accepted) |

### Probe Execution

Not applicable — no `scripts/*/tests/probe-*.sh` exist in the repository and none are
declared by any Phase-3 plan or SUMMARY.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| MERGE-01 | 03-01..05, 03-07, 03-09..16 | Default streaming path, no OOM at human scale | **MET with open gap** (gaps[0] — output correctness on the mixed-canonical streaming-writer subset) | bounded core + header-only validation + conservation + order proofs; 435/0 |
| MERGE-02 | 03-01, 03-04, 03-07, 03-09, 03-10 | Admission control, budget routing | **MET** | 37 routing tests green |
| MERGE-03 | 03-02, 03-09, 03-11, 03-13 | Temp cleanup on any exit | **MET** | cleanup tests green in suite |
| MERGE-04 | 03-05, 03-10, 03-12 | PyDatabase merge uses the CLI's bounded path | **MET** | shared entry point + inherited prologue; Python manifestation carried as human item |
| DENSE-01 | 03-03, 03-06 | k ≤ 32 as u64 | **MET** | regression green |
| DENSE-02 | 03-03, 03-04, 03-08, 03-15, 03-16 | Transparent to readers, byte identity | **MET with open gap** (queryability of prefix-cache output on the same subset) | golden differential green; mixed-canonical queryability proven on hashmap arm |
| DENSE-03 | 03-03, 03-04 | Canonicalization/counts match u128 | **MET** | differential + proptest green |

Orphaned requirements: none — all 7 phase-3 IDs appear in REQUIREMENTS.md (all marked
Complete, Phase 3) and across plan frontmatter. Deferred-items filtering (Step 9b):
Phase 4 is Benchmark & Validation (BENCH-01..04, performance measurement) — it does not
cover this gap; no deferral match.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| src/database/prefix_cache_merge.rs | 814-971 (+ :291-328, ~:1264 | k-way heap merge assumes ascending runs; unconditional `sorted: true` header | 🛑 Blocker (gaps[0]) | silently wrong query_kmer on mixed-canonical streaming-writer output — empirically reproduced |
| src/database/prefix_cache_merge.rs | 302-304 | comment claims both bucket writers sum encodings — false for the streaming writer | ⚠ Warning | misleading record; folded into gaps[0].missing |
| tests/prefix_cache_output_order_tests.rs | 94-96 | comment claims "every bucket writer emits ascending" — false for the streaming writer on mixed-canonical input | ⚠ Warning | misleading record; folded into gaps[0].missing |
| per 03-REVIEW-DISPOSITION.md | — | WR-01/02/04/05/06/07..10, IN-01..09 open | ⚠/ℹ | carried advisory; no other must-have depends on them |

Debt-marker gate: clean — no TBD/FIXME/XXX in any round-3 file (the `b"XXXX"` literal at
merge_routing_tests.rs:510 is corrupt-file test data, same class as the previously
accepted format.rs:2334 one). No real `#[ignore]` attributes (the two mentions are
doc-comment history, previously dispositioned); all binaries report 0 ignored.

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| tests/prefix_cache_output_order_tests.rs | MERGE-01, DENSE-02 | 3 | 0 | 0 (oracle is input-only, folds through the production canonicalizer) | Behavioral (value + e2e) | SUFFICIENT for the auto/hashmap arm; the streaming arm is UNTESTED — the proof's scoping comments overstate what is covered |
| tests/merge_routing_tests.rs | MERGE-01, MERGE-02, MERGE-04 | 37 | 0 | 0 | Behavioral | SUFFICIENT |
| tests/prefix_cache_conservation_tests.rs | MERGE-01, MERGE-03 | 2 | 0 | 0 (input-only oracle) | Behavioral | SUFFICIENT |

### Human Verification Required

### 1. Carried: Python-surface rejection manifestation (03-12 D4)

**Test:** Once the pyo3 maturin/pytest blocker lifts, call `PyDatabase.merge` from
Python on a k=21 + k=31 input set (and mixed-canonical without prefix cache) under a
streaming-selecting budget.
**Expected:** `PyRuntimeError` carrying the prologue's compatibility message; no
output file.
**Why human:** the pyo3 test runner is blocked in-repo (python-source/module-name
pairing + cov-fail-under addopts); the Rust-core rejection is proven through the exact
entry point Python calls, but the end-to-end manifestation has never been executed.

(The round-2 human decision item 1 — mixed-canonical disposition — was answered by the
user on 2026-10-09 (fix in phase) and is superseded by gaps[0]: what remains is no
longer a scope judgment but an evidenced, structured gap for `/gsd-plan-phase --gaps`.)

### Gaps Summary

One gap blocks goal closure. The user-commissioned mixed-canonical prefix-cache fix
(03-16) is genuinely delivered and genuinely correct **on the per-bucket hashmap
writer** — the default for small buckets — with strong RED/GREEN evidence, truthful
ANY-input header semantics pinned in both input orders, zero regressions (435/0 suite,
both clippy gates green, all run by me). But the capability's **streaming per-bucket
writer** (`--merge-mode streaming`, and auto for over-threshold buckets — i.e. the
large-merge regime this bounded-memory phase exists for) still emits non-ascending,
un-summed output under an unconditional `sorted: true` header, which I reproduced
deterministically in-repo through the public API: `query_kmer` silently returns
`Some(5)` where the truth is `Some(8)`. The executor logged this residual honestly at
every level (SUMMARY, deferred-items, WINDOWS.md #17) and the fresh review confirmed
it critically; honest logging does not make the truth hold. Fix options and the
required streaming-arm test extension are itemized in `gaps[0].missing`; the suggested
smallest safe fix is forcing the sorting (hashmap) writer for mixed-canonical merges in
`ExternalSortMerger::new` (option a), which is also the only option that keeps
`merge_mode: "streaming"` available without silent corruption.

---

_Verified: 2026-10-09T06:16:15Z_
_Verifier: Claude (gsd-verifier)_
