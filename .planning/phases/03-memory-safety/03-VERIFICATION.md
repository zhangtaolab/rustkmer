---
phase: 03-memory-safety
verified: 2026-10-09T04:27:40Z
status: human_needed
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
covered_digest: "v3:sha256:84733b9011df62a59bb9ac43c21cec8ea5e1a2af865a2f2f5f06f79cc84b1cab"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 7/11
  gaps_closed:
    - "CR-03 / truth 8: streaming route accepted incompatible inputs — CLOSED by 03-12: merge_prologue (format.rs:980-1062) collects every input header via read_header_of, runs validate_header_compatibility (k-mer size), plus a !use_prefix_cache-gated canonical loop; both public entry points call it first (:1261, :1348) and no route fn has another caller; 4 new rejection/capability tests in merge_routing_tests (37/37 green), RED evidence recorded pre-fix on both axes"
    - "CR-01+WR-03 / truth 9: prefix-cache bucket merge lost/misaligned records above one ~4 MB batch and stranded runs on within-file duplicates — CLOSED by 03-13: read_batch_from_file_sync (prefix_cache_merge.rs:976-1029) carries the partial-record tail via data.drain(..offset) with no clear(), only newly-read bytes count toward BATCH_BYTES, read errors propagate as Err; merge_single_prefix_streaming (:879-947) always pop_front()s the consumed head and iterates duplicate consumption before re-queueing the first non-duplicate (VecDeque buffer); >4 MB conservation proof (250k records, vacuousness guard, input-only oracle) green in prefix_cache_conservation_tests 2/2, plus unit conservation tests and mutation RED evidence"
    - "CR-02 / truth 10 (scoped): prefix-cache output claimed sorted:true while ordered by (low_byte, kmer) — CLOSED by 03-15 for same-canonical-mode merges: get_prefix_4mer (:1047-1050) selects the HIGH 8 bits (first 4 bases) so index-order concatenation is globally ascending and the header's sorted:true is truthful; proven by querying through both binary-search consumers (windows(2) global ascending, query_kmer vs oracle incl. a negative, extract_prefix_optimized subset equality, route parity of answers) in prefix_cache_output_order_tests 2/2, RED evidence recorded on the low-byte tree"
    - "WR-05 / truth 11: CLI front-end materialized every input for validation — CLOSED by 03-14: validate_merge_compatibility (merge.rs:392) reads exactly one 42-byte header per input; comment-filtered from_file_path count in merge.rs is 0; --check-compatibility header-only via read_header_of + RKDatabase::new(header); proven behaviorally on body-absent fixtures (loader failure asserted as premise) plus a real-binary CLI smoke, merge_frontend_validation_tests 3/3 green"
  gaps_remaining: []
  regressions: []
advisory:
  - finding: "Fresh-review CR-01 (mixed-canonical prefix-cache order residual — the UNCERTAIN half of truth 10): on the opt-in, advertised mixed-canonical capability (any canonical + any non-canonical input under use_prefix_cache), split_files_by_prefix buckets by the CANONICALIZED high byte but writes entry.kmer RAW (prefix_cache_merge.rs:300-310), so bucket order does not equal raw-key order and concatenate_final_output can emit non-ascending output under a sorted:true header — binary-search consumers silently wrong on exactly that subset. Root cause is the SAME pre-existing raw-write defect recorded open as old WR-04 (fresh WR-03: un-summed duplicate encodings, header claims ANY-input canonical semantics, swallowed canonicalization errors), which the previous verification already dispositioned as developer-triage advisory and the 03-12 executor decision ('belongs to WR-04's developer triage') consciously preserved. The gap-closure round strictly improved it (single-mode merges went untruthful->truthful; mixed stayed broken) — not a regression introduced by the round. No test covers mixed-canonical output order (the capability guard asserts merge success only). Recorded open in 03-REVIEW-DISPOSITION.md with a fix sketch (write processed_kmer, propagate canonicalization errors) that closes content, header, and order at once."
    category: architectural
    reason: "Scope/triage decision for the developer, not a grep-verifiable fact: whether the advertised mixed-canonical sub-capability's pre-existing correctness debt (wrong content AND order on that subset) is in-phase scope or post-phase triage. Promoting it to a gap would be inconsistent with the previous round's explicit advisory disposition of the same root cause; absorbing it silently would hide a fresh critical. Hence surfaced as the UNCERTANT half of truth 10 + human decision item 1."
    evidence_status: "code-reading mechanism confirmed (bucket-by-processed/write-raw at :300-310 vs :1047-1050), no failing test"
  - finding: "Remaining open warnings/infos from the fresh review, none touching a must-have: WR-01 (RAII Drop voids the failed-bucket 'shards preserved' logging promise — MERGE-03's cleanup itself still holds, sweep+RAII green in 29 tests), WR-02 (u32 count overflow in bucket merges, re-report), WR-04 (--batch-size CLI flag is a no-op), WR-05 (--check-compatibility --use-prefix-cache rejects what the merge accepts), WR-06 (validate_merge_compatibility panics on empty slice — unreachable from execute_merge, which guards len>=2), WR-07..WR-10 (pyo3 dump offset overflow, query_exact mmap count 0, from_file_path pre-reserve abort, frequency_distribution unbounded zero-fill — pre-existing, outside merge must-haves), IN-01..IN-08."
    category: other
    reason: "All recorded open in 03-REVIEW-DISPOSITION.md (21 rows) with file:line evidence in 03-REVIEW.md. Warning/info severity; no must-have truth depends on them. Triage belongs to the developer via the disposition record."
    evidence_status: "committed review record"
human_verification:
  - test: "Decide the disposition of fresh-review CR-01/WR-03 (mixed-canonical prefix-cache correctness debt): either accept it as recorded-open developer triage (post-phase) or commission a third gap-closure round. To see it: merge a canonical=true .rkdb with a canonical=false .rkdb via use_prefix_cache (CLI --use-prefix-cache or MergeConfig{use_prefix_cache:true}) choosing keys whose canonical form's high byte differs from the raw key's (e.g. a raw 0xFF..FF high-byte k-mer whose reverse complement starts 0x00), then inspect the output order and query it."
    expected: "If triaged to fix: globally ascending output under a truthful sorted flag, canonical and raw encodings of the same k-mer summed, canonicalization errors propagated. Today: the mixed-canonical output can be non-ascending while header.sorted is true (query_kmer binary search silently wrong), duplicate encodings un-summed, and the header's canonical flag follows ANY-input semantics — the route's output is wrong at the content level on this subset regardless of order (the pre-existing WR-03/WR-04 debt)."
    why_human: "The defect mechanism is code-confirmed, but whether this opt-in sub-capability is in the phase's contract is a scope/triage judgment: the root cause predates the phase, was explicitly dispositioned as developer-triage advisory by the previous verification (old WR-04) and by the 03-12 executor decision, and the round's delivered CR-02 contract (high-bits bucketing + query proofs) holds for every same-canonical-mode merge. No automated check can decide acceptance vs a third round."
  - test: "Confirm the Python-surface rejection manifestation once the pyo3 maturin/pytest blocker lifts (03-12 coverage D4, human_judgment: true): from Python, call pyrustkmer's PyDatabase.merge with an incompatible input set (k=21 DB + k=31 DB, or mixed canonical without prefix cache) under a streaming-selecting budget."
    expected: "PyRuntimeError carrying the prologue's compatibility message (e.g. 'Database 2 has k-mer size 31, expected 21'); no output file written."
    why_human: "The pyo3 test runner is blocked in-repo (pyo3/pyproject.toml python-source/module-name pairing breaks maturin build/develop; --cov-fail-under addopts fail every pytest run — STATE.md blocker, WINDOWS.md entries 4/5/11). The Rust-core rejection is behaviorally proven through the shared entry point PyDatabase.merge calls (pyo3/src/database.rs:1457 -> merge_databases_to_path -> merge_prologue; merge_routing_tests 37/37), pyo3 source is untouched this round (empty diff vs HEAD) and compiles clean under -D warnings — but the end-to-end Python manifestation has never been executed."
---

# Phase 03: Memory Safety — Re-Verification Report (Round 2)

**Phase Goal:** Bounded-memory merge operations and dense k-mer storage for the common k ≤ 32 case
**Verified:** 2026-10-09T04:27:40Z
**Status:** human_needed
**Re-verification:** Yes — after gap-closure round 2 (03-12..03-15)

## Goal Achievement

All four gaps from the previous verification (2026-10-09T00:00Z, 7/11) are
genuinely closed — I verified each in source and by running the phase's tests,
not by trusting the SUMMARYs. Ten of the eleven must-have truths now hold with
behavioral evidence; the full root-crate suite is 434 passed / 0 failed on this
host. The one open item is a scope decision, not a missing implementation: the
fresh code review's CR-01 shows the CR-02 fix does not extend to the opt-in
mixed-canonical prefix-cache sub-capability, whose output was already recorded
open (old WR-04) as semantically wrong at the content level. That residual is
surfaced for a human accept-or-fix decision rather than silently absorbed or
promoted against the previous round's own advisory precedent.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | DENSE-01: k ≤ 32 stored as u64, ~halving counting memory *(regression)* | ✓ VERIFIED | `src/hash/key.rs` still absent; `CounterTable::Dense(DashMap<u64,u32>)`/`Wide(DashMap<u128,u32>)` (table.rs:37-43); `stored_key_bytes()` matches the live variant (:188-193); dense_memory_tests green in the 434/0 suite (RSS ratio arm Linux-gated, as before) |
| 2 | Merge core respects memory budget; routes bounded *(regression)* | ✓ VERIFIED | read_header_of (:500), `INMEMORY_BYTES_PER_KMER` 96 model, `merge_databases_to_path` streaming writer unchanged by round 2; merge_bounded_memory_tests green in suite |
| 3 | In-memory and streaming routes produce identical data *(regression)* | ✓ VERIFIED | plain-LE `read_from` (format.rs:350) unchanged; merge_route_parity_tests (incl. 2M/16M arms) green in suite |
| 4 | Failed/interrupted merges clean up temp files (MERGE-03) *(regression)* | ✓ VERIFIED | merge_cleanup_tests 29/29 green in suite. New WR-01 advisory: RAII Drop removes preserved shards when a bucket error propagates — cleanup (the must-have) holds; the "preserved for recovery" log promise is the open nicety |
| 5 | u64/u128 counts + canonicalization match (DENSE-03) *(regression)* | ✓ VERIFIED | dense_differential + dense_proptest + dense_merge_integration green in suite |
| 6 | PyDatabase merge shares the CLI's bounded path (MERGE-04) *(regression + extension)* | ✓ VERIFIED | pyo3/src/database.rs:1457 calls `merge_databases_to_path`; pyo3 source untouched by round 2 (empty git diff vs HEAD); Python-surface rejection manifestation routed to human item 2 (pytest blocker) |
| 7 | .rkdb v2 byte-identity preserved (DENSE-02) *(regression)* | ✓ VERIFIED | golden_sha256_tests (real write-path differential) green in suite; fixtures unchanged |
| 8 | Incompatible inputs (k / canonical mismatch) rejected on EVERY route *(was FAILED — CR-03)* | ✓ VERIFIED | `merge_prologue` (format.rs:980-1062): empty-input guard, ALL headers via `read_header_of` (42 B/input, `?`-propagated), `validate_header_compatibility` k-check (:1013 → :1876-1899), canonical loop gated `!use_prefix_cache` (:1024-1062). Both public entry points call it first (:1261, :1348); grep confirms no other caller of any route fn — CLI, PyO3, and all three routes inherit one gate. Tests: `streaming_route_rejects_cross_input_kmer_size_mismatch` (3 arms incl. same-k Ok premise), `streaming_route_rejects_mixed_canonical_without_prefix_cache`, `prefix_cache_route_still_merges_mixed_canonical` (capability guard), `inmemory_route_still_rejects_mismatched_inputs` — merge_routing_tests 37/37 run by me; RED evidence for both rejection axes recorded in 03-12 SUMMARY against the pre-fix tree |
| 9 | Prefix-cache bucket merge lossless for shards > one ~4 MB batch *(was FAILED — CR-01+WR-03)* | ✓ VERIFIED | Reader (prefix_cache_merge.rs:976-1029): no `data.clear()`, partial-record tail carried via `data.drain(..offset)`, only newly-read bytes charged to BATCH_BYTES, read errors → `Err(io_error)` wrapped with the shard path at both call sites (:855-861, :911-920). Writer (:879-947): consumed head ALWAYS `pop_front()`ed (:907), within-file duplicate runs consumed in an iterated loop (:909-946, handles 3+ runs), first non-duplicate re-queued — a file is never left with a non-empty buffer and no heap entry; VecDeque makes it O(1)/pop. Behavioral: `prefix_cache_streaming_merge_conserves_a_bucket_larger_than_one_batch` (250,000 records / 5,000,000 bytes, asserted > the pre-fix 4,005,888-byte first batch, oracle computed from input pairs only, exact equality of records + header + summary + content) and the truncated-input Err pin — 2/2 run by me; unit conservation tests + mutation RED evidence (tail-carry revert: 216,592 vs 200,000; head-removal revert: 100 vs 200,050) in 03-13 SUMMARY |
| 10 | Prefix-cache-merged database queryable correctly (sorted flag truthful) *(was FAILED — CR-02)* | ⚠ UNCERTAIN (scoped) | **Delivered scope VERIFIED:** `get_prefix_4mer` (:1047-1050) selects the HIGH 8 bits (`kmer >> 2*(k-4)`, first 4 bases; saturating k<4 arm still monotone); phase-1 bucketing uses it (:300); concatenation loops `0..num_buckets` (:1087); both bucket writers emit ascending (hashmap sorts :764, heap merge ascending); header `sorted: true` (:1250) — truthful by construction for same-canonical-mode merges, and PROVEN by consumption: `prefix_cache_output_is_globally_sorted_and_queries_correctly` (windows(2) global ascending, every oracle key via query_kmer binary search + one negative, extract_prefix_optimized exact subset, content conservation) and `prefix_cache_answers_match_the_inmemory_route` (route parity of answers) — 2/2 run by me; RED evidence recorded (descending windows(2); query None vs Some(1) disagreement) in 03-15 SUMMARY. **Residual (fresh CR-01, human decision):** on MIXED-canonical merges — the opt-in capability the prologue hint advertises — records are bucketed by canonicalized high byte but written RAW (:300-310), so cross-bucket raw order is not monotone and the sorted:true claim is again untruthful on that subset; root cause is the pre-existing raw-write defect recorded open as old WR-04 / fresh WR-03 (which already makes that output content-wrong: un-summed encodings, ANY-input canonical header). No test covers mixed-canonical order. See human item 1 and advisory[0] |
| 11 | CLI merge front-end does not materialize input databases *(was FAILED/partial — WR-05)* | ✓ VERIFIED | `validate_merge_compatibility` (merge.rs:392-480): one `read_header_of` per input, reference load dropped, k always checked, canonical unless --use-prefix-cache; comment-filtered `from_file_path` count in merge.rs = **0** (was 6); `execute_merge` calls it before config (:162) and merges straight to `merge_databases_to_path` (:340); `--check-compatibility` header-only via `read_header_of` + `RKDatabase::new(header)` (:263-278). Behavioral: `frontend_validation_reads_headers_only` (body-absent fixtures, loader failure asserted as premise — any body load would error), `frontend_validation_rejects_mismatches_with_recovery_text`, `cli_smoke_both_routes_and_mismatch_rejection` (real binary, both route shapes Ok + mismatch exit≠0, no output file) — 3/3 run by me; RED evidence (full loader read past EOF on truncated bodies) in 03-14 SUMMARY |

**Score:** 10/11 truths verified (1 UNCERTAIN — scoped residual pending human triage; 0 failed)

### Re-Verification of the Four Prior Gaps (full 3-level treatment)

**CR-03 / truth 8 (03-12) — CLOSED.** Level 1: the validation exists in
`merge_prologue`. Level 2: it is substantive — every input's header collected
(`?`-propagated, so a missing/corrupt input fails on every route), k-mer-size
check via the same `validate_header_compatibility` whose message text a pin
test holds byte-for-byte, canonical check as a separate loop whose
`!use_prefix_cache` gate preserves the prefix-cache route's advertised
mixed-canonical capability (load-bearing via the capability-guard test). Level
3 (wiring): both public entry points call the prologue as their first
statement, and I grepped for any other caller of `merge_databases_streaming_to_path`
/ `merge_databases_inmemory` — there is none; the CLI (merge.rs:340) and
PyDatabase (pyo3/src/database.rs:1457) both reach the routes only through
`merge_databases_to_path`. Behavioral: the 4 new tests ran green here; the
SUMMARY records both rejection axes observed RED pre-fix (merge returned
`Ok` with input[0]'s k/canonical on mismatched sets — exactly the gap).

**CR-01+WR-03 / truth 9 (03-13) — CLOSED.** Level 1: reader and writer
rewritten. Level 2: the arithmetic defect is gone by construction —
record-aligned parsing from the carried buffer start, `drain(..offset)`
conserves every byte across batch boundaries, and `Err` replaces `break`.
Level 3: both per-bucket strategies read through this reader; the k-way loop
maintains the heap invariant (one entry per live file). Behavioral: the
>4 MB conservation test ran green here (0.91 s, post-VecDeque); the
vacuousness guard asserts the fixture exceeds the pre-fix first-batch
consumption, and the oracle never touches production merge code — the test
discriminates (SUMMARY: pre-fix RED 250,004 vs 250,005; mutation A 216,592 vs
200,000; mutation B 100 vs 200,050).

**CR-02 / truth 10 (03-15) — CLOSED for its delivered scope; residual UNCERTAIN.**
The gap's missing-item contract ("bucket by the HIGH bits … so index-order
concatenation is globally ascending … plus a test that queries a
prefix-cache-merged database") is delivered and behaviorally proven — through
the consumers, not the flag. The fresh review's CR-01 (independently confirmed
by my own reading of :300-310 vs :1047-1050) shows the construction argument
has a hole exactly when bucket key ≠ written key — the mixed-canonical
raw-write, i.e. the same root cause as the open WR-03/old-WR-04 debt the
previous round already triaged to the developer. Judgment: not a regression
introduced by the round (single-mode output went untruthful→truthful; mixed
stayed broken as before), not covered by any test, and confined to an opt-in
capability whose output is already content-wrong under that recorded debt —
so it is surfaced as a WARNING + human decision rather than a third
gap-closure mandate. A developer who disagrees can hand human item 1 back as
a gap.

**WR-05 / truth 11 (03-14) — CLOSED.** The materializing loader count in
merge.rs is 0 (comment-filtered, was 6 — including the `--check-compatibility`
loop and the in-file unit-test load-backs). The header-only property is
proven behaviorally by body-absent fixtures whose materializing load fails
(observed RED pre-conversion per the SUMMARY), and the CLI smoke drives the
real binary through both route shapes plus the rejection path.

### Quick Regression of the Seven Previously-Passed Truths

All seven re-checked at existence + wiring + suite level (sources re-read for
the dense-table and pyo3 wiring; the rest via the full-suite run): no
regressions. `git diff --stat HEAD -- pyo3/src/` is empty, so truth 6's wiring
is exactly as previously verified plus the prologue it now inherits (truth 8).
Full `cargo test`: **434 passed, 0 failed** across 23 result lines (lib +
all integration binaries), 0 ignored, no panics.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/database/format.rs` | prologue cross-input validation (03-12) | ✓ VERIFIED | :980-1062 headers+compat+canonical; both entry points wired (:1261/:1348) |
| `src/database/prefix_cache_merge.rs` | record-aligned reader, unstranding writer, high-byte bucketing (03-13/03-15) | ✓ VERIFIED (with CR-01 residual on the mixed-canonical subset — advisory[0]) | :976-1029, :879-947, :1047-1050; tests green |
| `src/cli/commands/merge.rs` | header-only front-end validation (03-14) | ✓ VERIFIED | :392-480 + :162 + :340; from_file_path count 0 |
| `tests/merge_routing_tests.rs` | streaming rejection + capability + parity tests | ✓ VERIFIED | 4 new tests; binary 37/37 |
| `tests/prefix_cache_conservation_tests.rs` | >4 MB conservation + Err pin | ✓ VERIFIED | 2/2; vacuousness guard + input-only oracle |
| `tests/prefix_cache_output_order_tests.rs` | global order + query + answer-parity proofs | ✓ VERIFIED | 2/2; windows(2) + query_kmer + extract_prefix_optimized |
| `tests/merge_frontend_validation_tests.rs` | header-only property + CLI smoke | ✓ VERIFIED | 3/3 incl. real-binary CARGO_BIN_EXE smoke |
| `src/hash/table.rs`, `src/hash/mod.rs`, `src/lib.rs` | dense table (regression) | ✓ VERIFIED | unchanged since 03-06; suite green |
| `src/database/streaming_merge.rs`, `temp_lifecycle.rs`, `merge_config.rs`, `stats.rs` | bounded core + cleanup (regression) | ✓ VERIFIED | unchanged this round; suites green |
| `pyo3/src/database.rs` | to-path core call (regression) | ✓ VERIFIED | :1457; pyo3 src diff vs HEAD empty |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| both public merge entry points | merge_prologue | first statement (:1261, :1348) | ✓ WIRED | no other caller of any route fn (grep) |
| PyDatabase.merge | bounded core + prologue | merge_databases_to_path (database.rs:1457) | ✓ WIRED | inheritance with zero pyo3 edits; manifestation → human item 2 |
| CLI execute_merge | validate_merge_compatibility → bounded core | merge.rs:162, :340 | ✓ WIRED | loader count 0 |
| phase-1 bucketing | high-byte prefix | get_prefix_4mer (:300 → :1047) | ✓ WIRED | monotone for same-mode merges |
| bucket writers | carried-tail reader | read_batch_from_file_sync (:855, :911) | ✓ WIRED | both call sites wrap Err with shard path |
| consumed heads | buffer removal + heap re-queue | pop_front + iterated tail step (:907-946) | ✓ WIRED | invariant: one heap entry per live file |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| prologue headers | Vec<DatabaseHeader> | read_header_of per input | Yes — 42 B/input, `?`-propagated | ✓ FLOWING |
| prefix-cache output header | total_kmers | data_size / RECORD_SIZE from concatenation | Yes — reader fixed, records conserved (test-proven at 5 MB) | ✓ FLOWING |
| prefix-cache output order | bucket sequence | high-byte bucketing + ascending writers | Yes for same-mode inputs; mixed-canonical raw-write breaks bucket=key identity | ⚠ FLOWING with CR-01 residual (advisory[0]) |
| CLI validation | ref_header/per-input headers | read_header_of (merge.rs:406, :429) | Yes — no body read (body-absent fixtures pass) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| CR-03 rejections (k + canonical, streaming auto/explicit, capability guard, in-memory parity) | `cargo test --test merge_routing_tests` | 37 passed, 0 failed | ✓ PASS |
| CR-01+WR-03 conservation >4 MB + Err pin | `cargo test --test prefix_cache_conservation_tests` | 2 passed, 0 failed (0.91 s) | ✓ PASS |
| CR-02 order + query + answer parity | `cargo test --test prefix_cache_output_order_tests` | 2 passed, 0 failed | ✓ PASS |
| WR-05 header-only + CLI smoke (real binary) | `cargo test --test merge_frontend_validation_tests` | 3 passed, 0 failed | ✓ PASS |
| Full-suite regression (all truths) | `cargo test` | 434 passed, 0 failed, 0 ignored (23 binaries) | ✓ PASS |
| RSS-ratio / RSS-bound arms | Linux-gated `/proc/self/status` tests | not executed — darwin host | ? SKIP (platform; correctly cfg-gated, as previously accepted) |

### Probe Execution

Not applicable — no `scripts/*/tests/probe-*.sh` exist in the repository and
none are declared by any Phase-3 plan or SUMMARY.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| MERGE-01 | 03-01..05, 03-07, 03-09..15 | Default streaming, no OOM at human scale | **MET** (with human item 1 pending on the mixed-canonical subset) | Bounded core + header-only validation at both front-ends + conservation + order proofs; 434/0 |
| MERGE-02 | 03-01, 03-04, 03-07, 03-09, 03-10 | Admission control, budget routing | **MET** | 37 routing tests green; model unchanged this round |
| MERGE-03 | 03-02, 03-09, 03-11, 03-13 | Temp cleanup on any exit | **MET** | 29 cleanup tests green; WR-01 advisory affects only the preserve-promise text, not cleanup |
| MERGE-04 | 03-05, 03-10, 03-12 | PyDatabase merge uses the CLI's bounded path | **MET** | Shared entry point + inherited prologue; pyo3 src untouched; Python manifestation → human item 2 |
| DENSE-01 | 03-03, 03-06 | k ≤ 32 as u64 | **MET** | regression green |
| DENSE-02 | 03-03, 03-04, 03-08, 03-15 | Transparent to readers, byte identity | **MET** | golden differential green; prefix-cache output queryable (same-mode proven) |
| DENSE-03 | 03-03, 03-04 | Canonicalization/counts match u128 | **MET** | differential + proptest green |

Orphaned requirements: none — all 7 Phase-3 IDs appear in REQUIREMENTS.md's
traceability table (all marked Complete, Phase 3) and in plan frontmatter
across the 15 plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| src/database/prefix_cache_merge.rs | 300-310 | buckets by canonicalized high byte, writes raw entry.kmer → mixed-canonical output non-ascending under sorted:true (fresh CR-01; root of WR-03 too) | ⚠ Warning → human item 1 | silent wrong queries on the opt-in mixed-canonical subset (already content-wrong per open WR-03) |
| src/database/prefix_cache_merge.rs | 498-517 region | RAII Drop voids the failed-bucket "shards preserved" promise (fresh WR-01) | ⚠ Warning | cleanup (MERGE-03) still holds; recovery/logging promise only |
| src/cli/commands/merge.rs | validate_merge_compatibility | panics on empty input slice (fresh WR-06) | ⚠ Warning | unreachable from execute_merge (len>=2 guard at :145) |
| per 03-REVIEW-DISPOSITION.md | — | WR-02/04/05/07..10, IN-01..08 open | ⚠/ℹ | recorded for developer triage |

Debt-marker gate: clean — no TBD/FIXME/XXX in any round-2 file (the
`b"XXXX"` literal in a format.rs test is test data, as previously accepted).
No stub patterns: all implementations are substantive; all test binaries real
and passing; 0 ignored tests.

### Human Verification Required

### 1. Mixed-canonical prefix-cache disposition (fresh CR-01 / open WR-03 root cause)

**Test:** Merge a canonical=true .rkdb with a canonical=false .rkdb through the
prefix-cache route (`--use-prefix-cache` / `use_prefix_cache: true`), then
decide: accept as recorded-open developer triage, or commission a third
gap-closure round (fix: write `processed_kmer` to the shard and propagate
canonicalization errors — one change closes content, header, and order).
**Expected:** If fixed: globally ascending output under a truthful sorted
flag, encodings of the same k-mer summed, header semantics corrected. Today:
non-ascending output possible under `sorted: true`, un-summed encodings,
ANY-input canonical header — the subset's output is already content-wrong per
the open debt.
**Why human:** Scope/triage judgment on a pre-existing, root-caused,
deliberately-triaged defect outside the delivered gap contract; consistent
precedent (previous round's advisory disposition of old WR-04) argues warning,
the fresh review's critical severity argues a third round — a developer call,
not a grep fact.

### 2. Python-surface rejection manifestation (03-12 D4)

**Test:** Once the pyo3 maturin/pytest blocker lifts, call `PyDatabase.merge`
from Python on a k=21 + k=31 input set (and a mixed-canonical set without
prefix cache) under a streaming-selecting budget.
**Expected:** `PyRuntimeError` carrying the prologue's compatibility message;
no output file.
**Why human:** The pyo3 test runner is blocked in-repo (python-source/
module-name pairing + cov-fail-under addopts). The Rust-core rejection is
proven through the exact entry point Python calls, and pyo3 compiles clean —
but the end-to-end manifestation has never been executed.

### Gaps Summary

No truth FAILED; no gaps are filed this round. All four prior gaps are closed
with discriminating, RED-evidenced tests, the suite is 434/0, and the phase
goal (bounded-memory merges + dense k ≤ 32 storage) plus all six roadmap
success criteria hold. The phase's remaining exposure is one human scope
decision (mixed-canonical prefix-cache debt — fresh CR-01/WR-03, recorded
open with a one-change fix sketch) and one blocker-gated Python-surface
confirmation; sixteen further warning/info findings are recorded open in
03-REVIEW-DISPOSITION.md for developer triage.

---

_Verified: 2026-10-09T04:27:40Z_
_Verifier: Claude (gsd-verifier)_
