---
phase: 03-memory-safety
verified: 2026-10-09T00:00:00Z
status: gaps_found
score: 7/11 must-haves verified
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
  - "tests/merge_route_parity_tests.rs"
  - "tests/merge_routing_tests.rs"
covered_digest: "v3:sha256:177c1ecc436387be94cdbb58a3c3eb84f08ef1034ba1fe4d31335dd2047f7068"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/7
  gaps_closed:
    - "DENSE-01: K-mers for k <= 32 are stored as u64 instead of u128 — roughly halving counting memory for the common case ( CLOSED by 03-06: KmerKey deleted, CounterTable::Dense(DashMap<u64,u32>) 16-byte slot, variant-matched stored_key_bytes, slot-layout + live-width tests green)"
    - "Merge respects a memory budget via admission control — bounded merge, no OOM at human scale (CLOSED at the core by 03-09 + 03-10: read_header_of at all merge call sites, 96 B/k-mer per-route model, merge_databases_to_path streams output entry-by-entry, CLI and PyO3 rewired)"
    - "Merge routes produce identical data (in-memory vs streaming) for the same input (CLOSED by 03-07: endianness heuristic deleted, plain LE round trip, route parity proven at 2M and 16M counts)"
  gaps_remaining: []
  regressions: []
gaps:
  - truth: "Merging databases with incompatible k-mer sizes or canonical modes returns an error on every route — the streaming route (the default over-budget route, reachable directly from PyDatabase.merge) must not silently produce a corrupt database"
    status: failed
    reason: >
      CR-03 of 03-REVIEW.md, independently confirmed by code reading.
      merge_databases_streaming_to_path (format.rs:1348-1350) reads
      kmer_size/canonical from read_header_of(input_paths[0]) only and never
      compares them against the other inputs; ExternalMerger::sort_database
      performs no validation either. The other two routes validate
      (in-memory: validate_compatibility_verbose at format.rs:1545;
      prefix-cache: validate_header_compatibility at format.rs:1687), and the
      CLI front-end pre-validates (merge.rs:165-239) — but PyDatabase.merge
      (pyo3/src/database.rs:1370-1465) checks only existence/merge_mode/
      max_memory before calling merge_databases_to_path. From Python, merging
      a k=21 DB with a k=31 DB under a budget that selects streaming (the
      automatic choice for large merges) silently writes a corrupt database
      whose header claims input[0]'s k-mer size. Same defect class as the G3
      gap this round just closed: route-dependent silent corruption, now on
      the validation axis. The function was created by this gap-closure round
      (d444d63) and the Python rewiring (4b9f095) made it the Python surface.
    artifacts:
      - path: "src/database/format.rs"
        issue: ":1348-1350 header of input[0] only; no cross-input kmer_size/canonical comparison anywhere on the streaming path (:966-996 prologue checks only emptiness; :1014 resolve_merge_route checks only memory)"
      - path: "src/database/streaming_merge.rs"
        issue: "sort_database (:263) reads/sorts/writes chunks with no kmer_size or canonical validation"
      - path: "pyo3/src/database.rs"
        issue: "PyDatabase.merge validates file existence, merge_mode and max_memory only — no k/canonical check before merge_databases_to_path"
    missing:
      - "Cross-input header validation on the streaming route — validate_header_compatibility over read_header_of results for every input (the same 42-byte-read pattern the prefix-cache route already uses at format.rs:1687), enforced inside merge_databases_streaming_to_path or in merge_prologue so all three routes and both entry points inherit it"
      - "A test that merges two databases with different k (and mixed canonical) via merge_databases_to_path under a streaming-selecting budget and asserts an Err"
  - truth: "A prefix-cache bucket merge preserves every input k-mer — shard files larger than one ~4 MB batch are read without dropping the partial-record tail, without misaligning the stream, and without stranding runs on within-file duplicates"
    status: failed
    reason: >
      CR-01 (+ WR-03) of 03-REVIEW.md, independently confirmed by code
      reading and arithmetic. read_batch_from_file_sync
      (prefix_cache_merge.rs:937-968) reads 8192-byte chunks until
      bytes_read >= 4_000_000, so it consumes 4,005,888 bytes (489 x 8192);
      4,005,880 is the last 20-byte record boundary, the trailing 8 bytes are
      dropped by the `offset + RECORD_SIZE <= data.len()` parse loop and
      destroyed by the next call's `data.clear()` — and the BufReader
      position is left 8 bytes mid-record, so EVERY subsequent record in that
      shard is parsed from a shifted offset. `Err(_) => break` also swallows
      read errors as EOF. Reachable via use_prefix_cache with the streaming
      bucket strategy (explicit merge_mode='streaming', or auto once a
      bucket's total_size exceeds merge_buffer_mb) whenever a shard file
      exceeds ~4 MB — routine at exactly the human scale this phase targets.
      Additionally (WR-03, same writer) the peek-and-add branches at :886-887
      and :897-899 consume a within-file duplicate by adding its count but
      neither remove it nor push a heap entry for its file, so the rest of
      that file's run is stranded and silently lost. The 03-11 integrity
      checks cannot see either defect: merged_records_recorded counts what
      this same corrupted writer emits, and the set comparison compares
      phases that both run after the corruption. No test covers shards above
      one batch (all fixtures are tiny). Defect code predates the phase
      (3b18d54) but lives in the file this gap-closure round modified and
      whose integrity 03-11 explicitly guaranteed ("a partial .rkdb is never
      concatenated and never reported as a successful merge").
    artifacts:
      - path: "src/database/prefix_cache_merge.rs"
        issue: ":937-968 read_batch_from_file_sync over-reads past BATCH_BYTES in 8192-byte chunks, drops the partial-record tail, leaves the stream misaligned, and swallows read errors; :886-887/:897-899 peek-and-add strands the remainder of a file's run on within-file duplicate k-mers"
    missing:
      - "Record-aligned batch reads: read in units of RECORD_SIZE (or carry the partial tail into the next batch instead of clearing it), and propagate read errors instead of `Err(_) => break`"
      - "Fix the duplicate-consume branches so a consumed entry is removed and the file's successor is re-queued (heap entry), or dedup within the writer the way merge_single_prefix_hashmap does"
      - "A test with a bucket shard larger than 4,000,000 bytes (200,294+ records) asserting exact record-count and content conservation through merge_single_prefix_streaming"
  - truth: "A prefix-cache-merged database is queryable correctly — its header's sorted flag must match the actual record order, so query_kmer's binary search and prefix queries return correct results"
    status: failed
    reason: >
      CR-02 of 03-REVIEW.md, independently confirmed by code reading.
      get_prefix_4mer (prefix_cache_merge.rs:970-973) returns `kmer & 0xFF` —
      the LOW byte of the right-aligned encoding (the last 4 bases), not the
      first. concatenate_final_output loops buckets in index order 0..255
      (:1010) and each bucket is internally sorted ascending by full u128,
      so the output is ordered by (low_byte, kmer) — e.g. k-mer 0x100 (bucket
      0) is written before k-mer 0xFF (bucket 255), violating ascending u128
      order — yet the header is written with `sorted: true` (:1175). Every
      consumer that trusts the flag then breaks: RKDatabase::query_kmer
      (format.rs:591-596) switches to binary_search_kmer when header.sorted,
      and prefix_query_optimized.rs binary-searches sorted databases
      (:86-120, :264-310) — exact-match queries silently return None or a
      wrong count. The phase's route tests assert header.sorted only for the
      in-memory and streaming routes, so this is untested on the prefix-cache
      route; the one unit test naming prefix extraction (IN-07) never calls
      get_prefix_4mer and is tautological. Defect predates the phase
      (3b18d54/f24658f) but lives in the file this gap-closure round
      rewrote (block-copy concatenation, integrity checks) while leaving the
      ordering claim intact.
    artifacts:
      - path: "src/database/prefix_cache_merge.rs"
        issue: ":970-973 low-byte bucket selection; :1010 index-order concatenation; :1175 header claims sorted: true on (low_byte, kmer)-ordered output"
    missing:
      - "Either bucket by the HIGH bits (first bases: `kmer >> (2*(k-4))` style prefix) so index-order concatenation is globally ascending, or write `sorted: false`, or sort during concatenation — plus a test that queries a prefix-cache-merged database (query_kmer and prefix extraction) and asserts correct results"
  - truth: "A merge invoked through the CLI front-end does not materialize input databases — compatibility validation reads 42-byte headers only"
    status: partial
    reason: >
      WR-05 of 03-REVIEW.md, independently confirmed by code reading. The CLI
      loads input[0] fully via RKDatabase::from_file_path (merge.rs:165) and
      holds it for the entire function, then runs TWO serial validation loops
      (merge.rs:177-234 and :241-293), each loading every remaining input
      fully, one at a time — including on --use-prefix-cache (only the
      canonical comparison is skipped; the loads still happen). The core
      merge is now bounded (03-09/03-10), but the user-invoked operation on
      the project's primary surface still pulls the whole of input[0] plus
      each other input twice into RAM before the bounded core runs, so
      SC-1's "human-scale merges no longer OOM the process" is not delivered
      at the CLI surface for inputs that individually exceed memory. The fix
      is the read_header_of call 03-09 already built. Note the serial
      one-at-a-time pattern (plus the held reference) is a large improvement
      over the pre-phase peak of all-inputs-plus-output, hence partial
      rather than failed.
    artifacts:
      - path: "src/cli/commands/merge.rs"
        issue: ":165 from_file_path(input[0]) held throughout; :177-234 and :241-293 two serial loops each calling from_file_path on every remaining input for k/canonical checks that need only headers"
    missing:
      - "Replace all three front-end validation loads with RKDatabase::read_header_of comparisons (validate_header_compatibility already exists for exactly this); drop reference_db after reading its two fields"
      - "A routing/bounded-memory test that invokes the CLI merge path (or extracts its validation into a testable unit) and asserts no input is fully loaded"
deferred: []
advisory:
  - finding: "WR-01: StreamingMergeIterator's pending_error re-check at streaming_merge.rs:440-445 is unreachable (the error is take()n in the same call that sets it, :496-499) and the iterator is not finished after an Err (heap/current_kmer retain stale state). The 03-07 must-have still holds — the immediate return DOES surface the error and the only current caller stops at the first Err — so this is dead-code hygiene, not a live truncation."
    category: architectural
    reason: "Confirmed by code reading; cosmetic now, a trap if a future caller retries a failed iterator. Deleting the unreachable re-check or finishing the iterator on Err would resolve it."
    evidence_status: "none provided"
  - finding: "Remaining open warnings/infos from 03-REVIEW.md not promoted to gaps here: WR-02 (u32 count overflow in prefix-cache bucket merges — debug panic vs release wrap, while the in-memory route saturates), WR-04 (mixed-canonical prefix-cache merge writes raw records while the header claims input[0]'s canonical), WR-06 (compat-shim fallback file leaks on error and is never swept), WR-07 (PyDatabase.dump offset overflow), WR-08 (query_exact MemoryMapped mode always count 0), WR-09 (from_file_path pre-reserve aborts on crafted header), WR-10 (frequency_distribution unbounded zero-fill), IN-01..IN-07."
    category: other
    reason: "All 20 findings are recorded open in 03-REVIEW-DISPOSITION.md (commit 5e7c3c5) with file:line evidence in 03-REVIEW.md. They are warning/info severity, not new-scope blockers under the #3304 gate (the critical three were promoted to gaps above); triage belongs to the developer via the disposition record."
    evidence_status: "none provided"
---

# Phase 03: Memory Safety — Re-Verification Report

**Phase Goal:** Bounded-memory merge operations and dense k-mer storage for the common k ≤ 32 case
**Verified:** 2026-10-09T00:00:00Z
**Status:** gaps_found
**Re-verification:** Yes — after gap closure (03-06 through 03-11)

## Goal Achievement

**All three gaps from the previous verification are genuinely closed** — I verified
each in source and by running the phase's tests, not by trusting the SUMMARYs.
The dense half of the goal (DENSE-01/02/03) is now fully delivered, including the
memory inversion fix. The merge core is now bounded end-to-end where the previous
pass found three-fold materialization.

**However, the goal is still not achieved.** A fresh code review (03-REVIEW.md,
commit 5e7c3c5) found three new Critical defects; I independently confirmed all
three by direct code reading (mechanism + arithmetic, cited per line below), plus
WR-05 (CLI front-end still materializes every input). All four live in files the
gap-closure round modified — CR-03's very function was created by commit d444d63 —
so under the #3304 evidence gate they are in-contract regressions, not new-scope
opinions. They are the same defect class that motivated two of the three original
gaps (silent, route-dependent data corruption), and the prior verification's own
standard ("pre-existing defects that this phase made newly load-bearing") applies
to them squarely. They are recorded open and unaddressed in 03-REVIEW-DISPOSITION.md.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | DENSE-01: k ≤ 32 stored as u64, ~halving counting memory *(carried gap G1)* | ✓ VERIFIED | `src/hash/key.rs` deleted (test !-e passes); 0 non-comment `KmerKey` refs in table.rs; `CounterTable::Dense(DashMap<u64,u32>)` 16-byte slot vs `Wide` 32-byte (table.rs:37-43); `stored_key_bytes()` matches the live variant (:188-193), never `kmer_length`; `slot_layout_is_pinned_for_both_widths` + `real_counter_reports_the_width_it_actually_stores` green; `get_all_counts() -> Vec<(u128,u32)>` preserved (:340-345). The 4M-entry RSS ratio test exists and is correctly `#[cfg(target_os = "linux")]` — it did not execute on this darwin host; the layout pins that did run make the slot-width claim deterministic (a `DashMap<u64,u32>` slot cannot inflate beyond its layout, which was the exact mechanism of the prior 48-byte inversion) |
| 2 | Merge core respects memory budget; routes bounded, no whole-DB materialization *(carried gap G2)* | ✓ VERIFIED | `read_header_of` (format.rs:500) used by streaming route (:1348), prefix-cache (:1668-1681, headers-only validation), estimator; `INMEMORY_BYTES_PER_KMER = 96` (:81) with `estimated_bytes_for_route` (:927); `merge_databases_to_path` (:1172) streams via one `KmerEntry::write_to` per yielded pair — no `sorted_kmers` Vec, no `from_kmer_pairs` (:1403-1416); prefix-cache handoff holds `Vec<DatabaseHeader>`; compat shim delegates to to-path core (:1284-1291); `merge_bounded_memory_tests` 6/6 green (RSS-bound arm Linux-gated). Front-end leak recorded as truth 11 |
| 3 | In-memory and streaming routes produce identical data *(carried gap G3)* | ✓ VERIFIED | `KmerEntry::read_from` is a plain LE read (format.rs:345-353); heuristic gone (remaining `1_000_000` literals are the round-trip test's threshold table and doc comments); chunk truncation caught by `len % RECORD_SIZE` (streaming_merge.rs:338-346) and mid-run failures surface `Err` immediately (:475-500); `merge_route_parity_tests` 5/5 green incl. parity at counts 2,000,000 and 16,777,216 |
| 4 | Failed/interrupted merges clean up temp files (MERGE-03) | ✓ VERIFIED (regression + extension) | 03-11 delivered: `should_remove_shards` decides deletion in one place, failed buckets PRESERVE shards and log paths (prefix_cache_merge.rs:489-510), bucket failure aborts with `Err` (:604-617), conservation checks that can fire (:1124-1156), block-copy concatenation (:1008, :1038-1053), sweep extended to loose `rustkmer_sort_*/rustkmer_merge_*.chunk` (temp_lifecycle.rs:62, :115+); `merge_cleanup_tests` 29/29 green |
| 5 | u64/u128 counts + canonicalization match (DENSE-03) | ✓ VERIFIED (regression) | `dense_differential_tests` 6/6, `dense_proptest_tests` compiled in suite, `dense_merge_integration_tests` 3/3 green |
| 6 | PyDatabase merge shares the CLI's bounded path (MERGE-04) | ✓ VERIFIED (regression) | Both front-ends call `RKDatabase::merge_databases_to_path` (cli/commands/merge.rs:460, pyo3/src/database.rs:1457); same `MergeConfig`, same prologue/route resolution |
| 7 | .rkdb v2 byte-identity preserved (DENSE-02) | ✓ VERIFIED (regression + 03-08) | `golden_sha256_tests` now drives the real write path: `dense_write_path_bytes_match_a_hand_built_reference` (hand-built reference arm traverses none of the code under test), `dense_k32_high_bytes_are_zero_on_disk`, `write_read_write_is_byte_idempotent` — 5/5 green; 12 Phase-1 fixtures unchanged |
| 8 | Incompatible inputs (k / canonical mismatch) are rejected on EVERY route | ✗ FAILED | **CR-03.** Streaming route validates nothing: header of input[0] only (format.rs:1348-1350); sort_database has no checks; PyO3 validates only existence/mode/memory. In-memory route rejects (format.rs:1545), prefix-cache rejects (format.rs:1687), CLI pre-validates — Python + streaming silently corrupts. See gaps[0] |
| 9 | Prefix-cache bucket merge is lossless for shards > one ~4 MB batch | ✗ FAILED | **CR-01 + WR-03.** `read_batch_from_file_sync` over-reads to 4,005,888 B, drops the 8-byte partial-record tail, leaves the stream misaligned for the rest of the shard, swallows read errors (`Err(_) => break`); duplicate-consume branches strand a file's remaining run. 03-11's conservation checks cannot see it. See gaps[1] |
| 10 | Prefix-cache-merged database is queryable correctly (sorted flag truthful) | ✗ FAILED | **CR-02.** Buckets selected by `kmer & 0xFF` (low byte), concatenated 0..255, header claims `sorted: true` (prefix_cache_merge.rs:970-973, :1010, :1175) — output is (low_byte, kmer)-ordered; `query_kmer` binary-searches on the flag (format.rs:591-596) and silently returns wrong results. See gaps[2] |
| 11 | CLI merge front-end does not materialize input databases | ✗ FAILED (partial) | **WR-05.** `from_file_path(input[0])` held throughout + two serial full-load validation loops (merge.rs:165, :177-234, :241-293), including on `--use-prefix-cache`. Core bounded; surface not. See gaps[3] |

**Score:** 7/11 truths verified (4 failed — all four are new findings from the gap-closure-modified code surface, not regressions of previously passed truths)

### Re-Verification of the Three Prior Gaps (full 3-level treatment)

**G1 / DENSE-01 (03-06) — CLOSED.** Level 1: `src/hash/key.rs` absent, `src/hash/mod.rs`
carries no `key` module, `src/lib.rs` re-export narrowed. Level 2: `CounterTable`
is a real two-variant enum monomorphizing `DashMap<u64,u32>` / `DashMap<u128,u32>`;
the single width-selection site is `KmerCounter::new` (table.rs:162). Level 3: all
consumers (`increment`, `get_count`, `get_all_counts`, `memory_usage`) dispatch on
the live variant; the prior self-fulfilling `key_bytes()` derivation is gone.
Behavioral: the discriminator the prior pass demanded ("an observation, not a
restatement") exists — `stored_key_bytes()` matches `self.table`, and
`real_counter_reports_the_width_it_actually_stores` asserts 8 vs 16 from real
`KmerCounter::new(21/64, ..)` counters. The mutation "build Wide for every k"
turns it red because the accessor reads the variant. The 4M-entry RSS ratio test
is present, real-counter-based, and Linux-gated (`/proc/self/status` does not
exist on darwin); the deterministic slot-layout pins ran green here. The measured
1.487 inversion is structurally impossible now: the dense slot is 16 B vs the wide
32 B, with no competing-width variant in the layout.

**G2 / bounded merge (03-09 + 03-10) — CLOSED at the core.** All three `missing`
items from the prior gap delivered: header-only reads at the flagged sites
(format.rs:852 → `read_header_of` at :1348; prefix_cache_merge.rs:76/:82-86 →
headers at :128/:135), output streamed instead of accumulated (:1403-1416, one
`write_to` per pair; placeholder header rewritten in place), per-route constant
recalibrated (24 → 96 B/k-mer, `estimated_bytes_for_route`, Python copy pinned by
`test_python_budget_model_tracks_the_core`). Front-ends rewired to
`merge_databases_to_path`. The prefix-cache intermediate lives in the RAII subdir;
`merge_prologue` gives one sweep + empty-input guard site for both entry points.
Caveat recorded as truth 11: the CLI front-end's own validation loops still
materialize inputs — the prior gap was filed against the strategies, which are
fixed; the front-end leak is filed as a new gap.

**G3 / route parity (03-07) — CLOSED.** The heuristic is deleted (source read at
:345-353 is a plain `u32::from_le_bytes` matching `write_to`'s LE write); damaged
chunks surface `Err` (length-multiple check + first-entry match + immediate
`pending_error` return); the round-trip table pins 999_999 / 1_000_000 /
1_000_001 / 2_000_000 / 16_777_216 and the two route-parity arms run above the
old threshold — all green. Note WR-01: the `pending_error` re-check at the top of
`next()` is unreachable (set-and-take in one call) — hygiene, not a live defect;
the error does surface.

### Why the New Criticals Block (evidence gate #3304 disposition)

- **CR-03** — flagged file `src/database/format.rs` modified since prior
  `verified:` (2026-10-07T04:20:00Z) by eb9c28f/33882b1/d444d63/4b9f095;
  `pyo3/src/database.rs` by 4b9f095. `merge_databases_streaming_to_path` was
  created by this round. In-contract regression → blocks.
- **CR-01 / CR-02** — flagged file `src/database/prefix_cache_merge.rs` modified
  by 8cbaa11/11a43dd/ee4b336/83a6ac2. The underlying defect code predates the
  phase (3b18d54), but the gate checks file-level modification deliberately, and
  the phase claimed integrity guarantees for exactly this route (03-11's
  must-haves) that these defects defeat. In-contract → blocks.
- **WR-05** — `src/cli/commands/merge.rs` modified by 4b9f095. In-contract;
  graded partial (large improvement over pre-phase peak, core fully bounded).
- All four were independently confirmed by code reading with line-level
  mechanisms (the batch arithmetic 4,005,880 + 8; the (low_byte, kmer) order
  argument; the absent validation vs the two routes that have it) — they are not
  unevidenced architectural opinions. No test covers any of them (all fixtures
  are small; the route tests assert `header.sorted` only for in-memory/streaming).

### Advisory (New Scope, Unevidenced)

Reported, not blocking beyond the gaps above. See `advisory:` frontmatter for the
two entries: WR-01 (dead `pending_error` re-check — confirmed, cosmetic) and the
remaining 16 open warning/info findings from 03-REVIEW.md, all recorded in
03-REVIEW-DISPOSITION.md for developer triage.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/hash/table.rs` | CounterTable enum + variant-matched accessors | ✓ VERIFIED | :37-43, :162, :188-201; 230 lib tests green |
| `src/hash/key.rs` | DELETED | ✓ VERIFIED | absent |
| `tests/dense_memory_tests.rs` | layout pin + live-width + RSS ratio | ✓ VERIFIED | 2/2 green on darwin; RSS arm Linux-gated |
| `src/database/format.rs` | read_header_of, to-path merge, MergeSummary, 96 B/k-mer | ✓ VERIFIED | :81, :388, :500, :927, :966, :1014, :1172, :1328 |
| `src/database/streaming_merge.rs` | error propagation, RECORD_SIZE check | ✓ VERIFIED | :25, :338-346, :440-500 (dead re-check noted) |
| `tests/merge_route_parity_tests.rs` | threshold round-trip + >1M parity | ✓ VERIFIED | 5/5 green |
| `tests/golden_sha256_tests.rs` | real write-path differential | ✓ VERIFIED | 5/5 green; fixtures unchanged |
| `src/database/prefix_cache_merge.rs` | header-only, failure abort, conservation, block copy | ✓ VERIFIED (03-11 scope) | :128/:135, :489-510, :604-617, :1008, :1124-1156 — but carries CR-01/CR-02 (gaps 2-3) |
| `src/database/temp_lifecycle.rs` | sweep loose chunk files | ✓ VERIFIED | :62, :115+ |
| `src/cli/commands/merge.rs` | calls to-path core, checked parse | ✓ WIRED / ⚠ front-end loads | :460 calls core; :165+:177+:241 materialize inputs (gap 4) |
| `pyo3/src/database.rs` | calls to-path core | ✓ WIRED | :1457; validation gap → CR-03 |
| `tests/merge_bounded_memory_tests.rs` | RSS bound + byte identity + header equality | ✓ VERIFIED | 6/6 green (RSS arm Linux-gated) |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| KmerCounter::new | CounterTable variant | single width-selection site (table.rs:162) | ✓ WIRED | exactly one selection point |
| stored_key_bytes | live CounterTable variant | match on self.table (:188-193) | ✓ WIRED | observation, not restatement |
| CLI merge | bounded core | merge_databases_to_path (merge.rs:460) | ✓ WIRED | front-end validation loads flagged (WR-05) |
| PyDatabase.merge | bounded core | merge_databases_to_path (database.rs:1457) | ✓ WIRED | missing k validation (CR-03) |
| merge_sorted_chunks iterator | streaming writer | per-item KmerEntry::write_to (format.rs:1406-1416) | ✓ WIRED | consumed once, incrementally |
| merge_prologue | both public entry points | sweep + empty guard (:966-996, :1177, :1265) | ✓ WIRED | one call site each |
| prefix-cache route | header validation | validate_header_compatibility (:1687) | ✓ WIRED | contrasts with streaming route's absence (CR-03) |
| bucket writers → merged_records_recorded → concatenation | conservation check | writer-side counter (:516-519) vs copy-side total (:1128-1143) | ✓ WIRED | cannot see CR-01 (both sides downstream of the corrupting reader) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| streaming writer | merge_iter | ExternalMerger over input chunk files | Yes — per-yield writes | ✓ FLOWING |
| estimator | estimated_memory | read_header_of per input | Yes — 42-byte headers, saturating sum | ✓ FLOWING |
| prefix-cache output header | total_kmers | data_size / RECORD_SIZE from concatenation | Yes — but records may originate from the misaligning batch reader | ⚠ FLOWING-CORRUPTED (CR-01) |
| PyDatabase.merge budget | max_memory_usage | parse_memory_size (CLI's parser) | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Dense layout + live width | `cargo test --test dense_memory_tests` | 2 passed, 0 failed | ✓ PASS |
| Route parity above 1M | `cargo test --test merge_route_parity_tests` | 5 passed (incl. 2M / 16M arms) | ✓ PASS |
| Real write-path golden differential | `cargo test --test golden_sha256_tests` | 5 passed | ✓ PASS |
| Cleanup / sweep / conservation | `cargo test --test merge_cleanup_tests` | 29 passed | ✓ PASS |
| Routing / admission model | `cargo test --test merge_routing_tests` | 33 passed | ✓ PASS |
| Bounded-memory + byte identity | `cargo test --test merge_bounded_memory_tests` | 6 passed (RSS arm Linux-gated) | ✓ PASS |
| Lib (incl. table inline tests) | `cargo test --lib` | 230 passed, 0 failed, 0 ignored | ✓ PASS |
| DENSE-03 differential | `cargo test --test dense_differential_tests --test dense_merge_integration_tests` | 6 + 3 passed | ✓ PASS |
| RSS ratio (DENSE-01) + RSS bound (G2) | Linux-gated `/proc/self/status` tests | not executed — darwin host | ? SKIP (platform; tests exist and are correctly cfg-gated) |

### Probe Execution

Not applicable — no `scripts/*/tests/probe-*.sh` declared by any Phase-3 plan or
SUMMARY, and the phase is not a migration/tooling phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| MERGE-01 | 03-01, 03-04, 03-07, 03-09, 03-10, 03-11 | Default streaming, no OOM at human scale | **PARTIAL** | Core bounded and default-routes to streaming (verified); CLI front-end still materializes inputs (WR-05), prefix-cache route corrupts/missorts (CR-01/02), streaming route lacks input validation (CR-03) |
| MERGE-02 | 03-01, 03-04, 03-07, 03-09, 03-10 | Admission control, budget-respecting routing | **MET** | Header-only estimator, 96 B/k-mer per-route model, D-02 reject, saturating sum; 33 routing tests green; Python constant pinned |
| MERGE-03 | 03-02, 03-09, 03-11 | Temp cleanup on any exit, no disk exhaustion | **MET** | RAII subdir, sweep incl. loose chunks, failure-path shard preservation; 29 tests green |
| MERGE-04 | 03-05, 03-10 | PyDatabase merge uses the CLI's bounded path | **MET** (with CR-3 caveat) | Same `merge_databases_to_path` + `MergeConfig`; the shared core's streaming route lacks the validation the CLI front-end performs separately — scored under MERGE-01 |
| DENSE-01 | 03-03, 03-06 | k ≤ 32 as u64, ~halved counting memory | **MET** | Inversion fixed (16 B slot vs 32 B); layout pinned; variant-matched accessor; RSS test on Linux |
| DENSE-02 | 03-03, 03-04, 03-08 | Transparent to existing readers, byte identity | **MET** | Real write-path differential green; 12 fixtures unchanged |
| DENSE-03 | 03-03, 03-04 | Canonicalization/counts match u128 exactly | **MET** | Differential + proptest green |

Orphaned requirements: none — all 7 Phase-3 IDs appear in plan frontmatter and in
REQUIREMENTS.md's traceability table. NOTE: REQUIREMENTS.md marks all 7 "Complete"
and 03-VALIDATION.md signs off 7/7 nyquist-compliant (BLOCKER-1 resolved); this
verification contradicts the MERGE-01 "Complete" marking and qualifies MERGE-04.

### Decision Coverage

Gate run via `check.decision-coverage-verify`: 6/6 trackable CONTEXT.md decisions
honored by shipped artifacts (skipped: false, blocking: false).

### Test Quality Audit

| Test File | Linked Req | Active | Skipped | Circular | Assertion Level | Verdict |
|-----------|-----------|--------|---------|----------|-----------------|---------|
| dense_memory_tests.rs | DENSE-01 | 2 (+1 Linux-gated) | 0 | 0 | Value/layout | SOUND — variant-matched accessor discriminates |
| merge_route_parity_tests.rs | MERGE-01/02 | 5 | 0 | 0 | Value (byte-exact) | SOUND — reference arm hand-built |
| golden_sha256_tests.rs | DENSE-02 | 5 | 0 | 0 | Value (bytes on disk) | SOUND — reference arm traverses none of the code under test; mutation evidence committed (03-08-mutation-evidence.md) |
| merge_cleanup/routing/bounded/integration | MERGE-01/02/03 | 68 | 0 | 0 | Behavioral | SOUND — route probes discriminate via nonexistent temp_dir |

Disabled tests on requirements: 0. Circular patterns: 0 (the 03-08 rewrite
specifically replaced the prior from_kmer_pairs-vs-from_kmer_pairs tautology with
a hand-built reference). Known blind spots are the four gaps: no test covers
cross-k streaming merges, >4 MB prefix-cache shards, prefix-cache output
queryability, or CLI front-end memory behavior.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| src/database/prefix_cache_merge.rs | 937-968 | batch reader drops partial record + misaligns + swallows IO errors (CR-01) | 🛑 Blocker | silent shard corruption above ~4 MB |
| src/database/prefix_cache_merge.rs | 970-973, 1010, 1175 | low-byte bucket order written with `sorted: true` (CR-02) | 🛑 Blocker | binary-search queries silently wrong |
| src/database/format.rs (+ pyo3/src/database.rs) | 1348-1350 | no cross-input k/canonical validation on streaming route (CR-03) | 🛑 Blocker | silent corrupt merge from Python |
| src/database/prefix_cache_merge.rs | 886-887, 897-899 | peek-and-add strands a file's run on duplicates (WR-03) | 🛑 (folded into CR-01 gap) | silent loss in bucket merge |
| src/cli/commands/merge.rs | 165, 177-234, 241-293 | front-end fully loads every input for validation (WR-05) | ⚠ Warning→gap (partial) | OOM risk at CLI surface |
| src/database/streaming_merge.rs | 440-445 | unreachable pending_error re-check (WR-01) | ⚠ Warning | hygiene; error still surfaces |
| (per 03-REVIEW-DISPOSITION.md) | — | WR-02/04/06..10, IN-01..07 open | ⚠/ℹ | recorded for triage |

Debt-marker gate: clean — no TBD/FIXME/XXX in any phase file (one `b"XXXX"` literal
in a format.rs test is test data, not a marker).

### Human Verification Required

Not emitted — status is gaps_found (Step 9 rule 1); the four gaps are
code-level and reproducibly evidenced, requiring fixes rather than human testing.

### Gaps Summary

The gap-closure round (03-06..03-11) did exactly what it was commissioned to do,
and did it well: all three recorded gaps are closed with discriminating tests,
and the engine is green (230 lib + 82 integration tests across the phase's
binaries, 0 ignored). The dense-storage half of the goal is complete.

What keeps the phase open is the merge half's correctness surface, judged by the
same standard the previous verification applied to G3 ("pre-existing defects
that this phase made newly load-bearing" are gaps): four confirmed defects, all
on files this round modified, none covered by any test, all recorded open in
03-REVIEW-DISPOSITION.md with no later milestone phase addressing them (Phase 4
is benchmarks only):

1. **CR-03 — streaming route accepts incompatible inputs** (format.rs:1348). The
   default over-budget route, reachable from `PyDatabase.merge` with an ordinary
   call, silently writes a corrupt database where the in-memory route errors.
   Fix: run the existing `validate_header_compatibility` over `read_header_of`
   results inside the streaming route (or the shared prologue), plus one test.
2. **CR-01 (+WR-03) — prefix-cache bucket merge loses/corrupts records** for
   shards above one ~4 MB batch and strands runs on within-file duplicates
   (prefix_cache_merge.rs:937-968, :886-899). Fix: record-aligned batch reads
   with carried tails and propagated errors; re-queue consumed duplicates.
3. **CR-02 — prefix-cache output claims `sorted: true` but is (low_byte, kmer)-
   ordered** (prefix_cache_merge.rs:970-973, :1010, :1175). Every binary-search
   consumer silently returns wrong results. Fix: bucket by high bits, or write
   `sorted: false`, or sort at concatenation; add a query test.
4. **WR-05 — CLI front-end materializes every input for validation**
   (merge.rs:165, :177-234, :241-293). The bounded core 03-09/03-10 built is
   reached only after full loads. Fix: `read_header_of` (already built) at all
   three sites.

Items 1 and 4 are small, mechanical fixes against machinery that already exists
(`validate_header_compatibility`, `read_header_of`); items 2 and 3 are confined to
`merge_single_prefix_streaming` / `concatenate_final_output` on the opt-in
prefix-cache route but are silent-data-loss class and defeat 03-11's integrity
guarantees.

---

_Verified: 2026-10-09T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
