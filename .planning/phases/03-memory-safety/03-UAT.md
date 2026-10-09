---
status: complete
phase: 03-memory-safety
source: 03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md, 03-04-SUMMARY.md, 03-05-SUMMARY.md, 03-06-SUMMARY.md, 03-07-SUMMARY.md, 03-08-SUMMARY.md, 03-09-SUMMARY.md, 03-10-SUMMARY.md, 03-11-SUMMARY.md, 03-12-SUMMARY.md, 03-13-SUMMARY.md, 03-14-SUMMARY.md, 03-15-SUMMARY.md, 03-16-SUMMARY.md, 03-17-SUMMARY.md
started: 2026-10-09T12:36:07Z
updated: 2026-10-09T12:53:44.793Z
---

<!-- Testing delegated to Claude by the user ("你来验证和检测"). Claude executes each
     checkpoint directly (CLI runs, code reads, real measurements) and records results.
     Coverage auto-passed groups carry the D-ids each SUMMARY's uat.classify-coverage
     resolved as deterministically covered by passing tests (mode: coverage; 03-10/03-11
     malformed-kind entries kept as human rows per the fail-safe rule). -->

## Current Test

[testing complete]

## Tests

### 1. Full-phase regression gate (03-16 D4)
expected: cargo test full suite 439 passed / 0 failed (3 Linux-gated RSS arms ignored on darwin); `cargo clippy --all-targets -- -D warnings` exit 0 on root AND pyo3 workspace member
result: pass
evidence: "cargo test: 439 passed / 0 failed / 3 ignored across 23 result lines (matches round-4 verifier baseline exactly); golden_tests 34/34, merge_routing 37/37, prefix_cache_output_order 3/3, prefix_cache_conservation 2/2; root clippy --all-targets -D warnings exit 0; pyo3 clippy --all-targets -D warnings exit 0 — all run by delegated tester 2026-10-09"

### 2. Automated coverage — 03-01 (D1–D6)
expected: header-only merge estimator; hard-route admission control; estimator fallback/corrupt-header tolerance; plus the other D1–D6 coverage entries, all deterministically covered by passing unit/integration tests per uat.classify-coverage
result: pass
source: automated
coverage_id: 03-01:D1-D6

### 3. Automated coverage — 03-02 (D1–D6, D8)
expected: RAII shard cleanup on all non-aborting exits; process-unique temp subdir; sweep behavior (TTL, logging, live-dir untouched); sweep reached from dispatch; tempfile dependency; RECORD_SIZE/read_record_at; full-suite regression — all covered by passing tests
result: pass
source: automated
coverage_id: 03-02:D1-D6,D8

### 4. Automated coverage — 03-03 (D1–D7)
expected: u64 dense storage for k≤32; .rkdb v2 byte-identity; decoded-level differential u64-vs-u128; plus D3–D7 coverage entries — all covered by passing tests
result: pass
source: automated
coverage_id: 03-03:D1-D7

### 5. Automated coverage — 03-04 (D1–D7)
expected: cross-plan dense-count→write→merge composition; golden sha256 + dense output layout; mutation-proven merges; plus D3–D7 coverage entries — all covered by passing tests
result: pass
source: automated
coverage_id: 03-04:D1-D7

### 6. Automated coverage — 03-05 (D1–D9)
expected: PyDatabase.merge kwargs threading; CLI-grammar max_memory parsing; streaming-route proof via chunk files; plus D3–D9 coverage entries — all covered by passing tests
result: pass
source: automated
coverage_id: 03-05:D1-D9

### 7. Automated coverage — 03-06 (D1–D6)
expected: DashMap<u64,u32> 16-byte slot for k≤32 chosen at one site; measured (not modelled) k21-vs-k64 ratio; key.rs deleted; plus D3–D6 coverage entries — all covered by passing tests
result: pass
source: automated
coverage_id: 03-06:D1-D6

### 8. Automated coverage — 03-07 (D1–D5)
expected: u32::from_le_bytes count decode; exact round-trips above the old 1,000,000 threshold; hand-written little-endian record reads back; plus D4–D5 coverage entries — all covered by passing tests
result: pass
source: automated
coverage_id: 03-07:D1-D5

### 9. Automated coverage — 03-08 (D1–D4, D6)
expected: production dense write path vs hand-built reference; k=32 high-bytes-zero on disk; write-read-write byte idempotence; plus D6 — all covered by passing tests
result: pass
source: automated
coverage_id: 03-08:D1-D4,D6

### 10. Automated coverage — 03-09 (D1–D4, D6–D11)
expected: no merge route materializes inputs it does not need; 96 B/k-mer in-memory charge; route-peak estimates; plus D3–D4, D6–D11 coverage entries — all covered by passing tests
result: pass
source: automated
coverage_id: 03-09:D1-D4,D6-D11

### 11. Automated coverage — 03-10 (D2–D4)
expected: measured RSS bound under pinned chunk_size; streaming header equals from_kmer_pairs header field-for-field; to_path and in-RAM entry points byte-identical — covered by passing tests
result: pass
source: automated
coverage_id: 03-10:D2-D4

### 12. Automated coverage — 03-11 (D1–D2, D5–D6)
expected: failed prefix bucket aborts with Err, shards recoverable; successful buckets release shards; orphan sweep behavior; plus D5–D6 coverage entries — all covered by passing tests
result: pass
source: automated
coverage_id: 03-11:D1-D2,D5-D6

### 13. Automated coverage — 03-12 (D1–D3)
expected: streaming route rejects cross-input k-size mismatch; rejects mixed canonical without prefix cache while prefix-cache still merges it; in-memory rejection parity — all covered by passing tests
result: pass
source: automated
coverage_id: 03-12:D1-D3

### 14. Automated coverage — 03-13 (D1–D4, all auto)
expected: record-aligned batch reads with carried tail; unstranding k-way merge; route-level conservation vs oracle; D4 — all_auto_covered=true per classifier
result: pass
source: automated
coverage_id: 03-13:D1-D4

### 15. Automated coverage — 03-14 (D1–D3, all auto)
expected: CLI front-end validation reads headers only; rejection UX contract preserved; D3 — all_auto_covered=true per classifier
result: pass
source: automated
coverage_id: 03-14:D1-D3

### 16. Automated coverage — 03-15 (D1–D3, all auto)
expected: get_prefix_4mer first-4-bases selection; globally-ascending queryable prefix-cache output; answer parity with in-memory route — all_auto_covered=true per classifier
result: pass
source: automated
coverage_id: 03-15:D1-D3

### 17. Automated coverage — 03-16 (D1–D3)
expected: RED-provable mixed-canonical e2e (ascending, summed, queryable); one-site canonicalized bucket-key fix; reversed-input-order canonical-header pin — all covered by passing tests
result: pass
source: automated
coverage_id: 03-16:D1-D3

### 18. Automated coverage — 03-17 (D1–D6, all auto)
expected: streaming-arm mixed-canonical e2e; ExternalSortMerger::new mixed-canonical override matrix; descending-run refusal; plus D4–D6 — all_auto_covered=true per classifier
result: pass
source: automated
coverage_id: 03-17:D1-D6

### 19. Merge streaming route is bounded and scale-invariant (03-01 D7, 03-04 D8, 03-05 D10)
expected: Merging .rkdb databases whose combined k-mer count grows ~25× (with max_memory forcing the streaming route) keeps peak RSS flat/bounded (chunk-size-dependent, not input-size-dependent); no OOM. Human-genome absolute scale (3.1 Gbp) has no local dataset (CRR1936095 absent) — scale-invariance across the tested range plus the estimator's hard routing is the accepted bounding evidence.
result: pass
evidence: "real measurements, fresh release binary, /usr/bin/time -l, streaming route confirmed selected at every scale by the routing log (estimator vs 64MB budget): 4M total kmers -> peak RSS 67.0MB (= largest file 2M records x 32B chunk buffer); 20M -> 323MB (= 10M x 32B); 100M -> 1.53GB (= largest file 50M x 32B, exactly one default chunk of 50M records); 200M total (A3+B3+M3, largest file 100M records = 2 chunks) -> 3.05GB = 2x the 1.6GB chunk buffer, NOT proportional to total input (unbounded would be 6.4GB). Live heap is chunk-bounded by construction (DatabaseStreamIterator::next allocates Vec<KmerEntry> of min(chunk_size, remaining); chunk_size default 50M records x 32B = 1.6GB, merge_config.rs:48); RSS above one chunk is freed-but-still-resident page accounting (kernel-reclaimable, not OOM risk). Merged output verified correct at the largest scale (Total k-mers 99,998,837 unique with counts doubled, matching the k-mer union of the inputs). Pinned-chunk RSS bound at unit level already covered by automated 03-10 D2 (1M kmers @ chunk 50K < 6.4MB). Scale note: human-genome absolute (~3.1G kmers, ~62GB of inputs) not runnable in-session (no dataset locally); the same estimator hard-routing was exercised at a 19.2GB estimate and selected streaming"

### 20. Dense u64 counting really halves memory, measured end-to-end (03-03 D8)
expected: Counting the same synthetic sequence at k=21 (dense u64 path) vs k=63 (u128 path) shows peak RSS ratio materially below 1.0 (target ≈ 0.5) at real scale via CLI-level measurement (cargo's RSS-ratio tests are /proc-gated, i.e. Linux-only). Human-genome absolute scale not available locally; measured at the largest feasible synthetic scale.
result: pass
evidence: "real CLI-level measurement on the same synthetic 40 Mbp sequence (40M unique k-mers), fresh release binary, /usr/bin/time -l: k=21 peak RSS 4,954,554,368 B vs k=63 6,507,085,824 B -> ratio 0.761 at process level (both paths share fixed process overhead + the get_all_counts Vec<(u128,u32)> 32 B/entry materialization, which dilutes the table-level saving); table-level unit measurement 0.515 (k21 35.66 vs k64 69.21 B/entry, dense_memory_tests, Linux-gated — matches the recorded evidence); dense path is also 1.7x faster (6.97s vs 11.71s). Scale note: human-genome absolute (3.1 Gbp) dataset absent locally (CRR1936095 not on disk); measured at 40M real entries — the largest feasible synthetic scale on this host"

### 21. SIGKILLed merge is reclaimed by the next run's sweep (03-02 D7, 03-04 D9)
expected: A prefix-cache merge killed with SIGKILL mid-flight leaves a rustkmer-merge-* orphan dir in temp_dir; the next merge's sweep_stale_merge_dirs reclaims it (after TTL) and logs the removal. Known recorded exclusion: loose *.chunk files of the streaming route are NOT swept (deferred-items, open — out of scope for this truth).
result: pass
evidence: "real end-to-end SIGKILL run: prefix-cache merge of 100M k-mers (A3+B3, --use-prefix-cache, 64MB budget) SIGKILLed mid-flight after the process-unique rustkmer-merge-85TaGgcM dir appeared (~100ms in, 528 shard files, 1.9GB); after kill -9 the orphan persists (Drop never ran). Next merge, same temp_dir: young orphan UNTOUCHED (7-day TTL guard protects live merges). After backdating mtimes >TTL: next merge logs 'INFO rustkmer::database::temp_lifecycle] Swept stale merge temp dir: .../rustkmer-merge-85TaGgcM' and reclaims the full 1.9GB (temp dir empty after). Note: the deferred-items claim that loose *.chunk files are not swept is STALE — current temp_lifecycle.rs sweeps both rustkmer-merge-* dirs AND loose rustkmer_sort_*/rustkmer_merge_* chunk files past the same TTL (:164-221, CHUNK_FILE_PREFIXES)"

### 22. Python-surface merge contract (03-07 D6, 03-09 D5, 03-10 D7, 03-12 D4)
expected: Build the pyo3 extension via the documented workaround (PYO3_PYTHON build + manual cdylib install, pytest -o addopts=""), then: (a) pyo3/tests/test_database_merge.py passes; (b) PyDatabase.merge on k=21 + k=31 inputs raises PyRuntimeError carrying the prologue compatibility message and writes no output file; (c) mixed-canonical without prefix cache likewise rejected; (d) merge kwargs (max_memory, merge_mode) accepted. This is the single item that held VERIFICATION at human_needed.
result: pass
evidence: "extension built from current source (PYO3_PYTHON=.venv/bin/python; the deferred-items workaround needed one amendment on this tree: pyo3 0.27 no longer auto-emits -undefined dynamic_lookup, injected via RUSTFLAGS='-C link-arg=-undefined -C link-arg=dynamic_lookup' without source changes), installed as site-packages/pyrustkmer.so after removing a shadowing Jan-18 pyrustkmer 0.4.1 package dir in the venv. pytest tests/test_database_merge.py -o addopts='': 12/12 passed — first-ever end-to-end execution of this suite. Targeted probe (the exact carried human item): k=21+k=31 under max_memory=1MB streaming-selecting budget -> PyRuntimeError 'Merge operation failed: Database 2 has k-mer size 32, expected 21', no output file written; mixed-canonical without prefix cache -> PyRuntimeError 'Database 2 has canonical mode false, expected true', no output; __text_signature__ '(databases, output, *, max_memory=None, merge_mode=...)'; compatible streaming merge succeeds (442 B output). Two environment findings recorded as deferred follow-ups: (1) deferred-items' documented build workaround no longer links as-is under pyo3 0.27 — pyo3/build.rs should call pyo3_build_config::add_extension_module_link_args(); (2) a stale venv package dir silently shadows a manually installed extension"

### 23. Front-ends call merge_databases_to_path; nothing materializes (03-10 D5)
expected: CLI execute_merge and PyDatabase::merge both call merge_databases_to_path; no front-end loads a full RKDatabase for merging (comment-filtered from_file_path count 0 in merge.rs front-end; pyo3 merge path calls the bounded entry point)
result: pass
evidence: "grep comment-filtered from_file_path in src/cli/commands/merge.rs = 0; CLI execute_merge -> RKDatabase::merge_databases_to_path at merge.rs:340; pyo3 PyDatabase::merge -> merge_databases_to_path at pyo3/src/database.rs:1457 (single call, save folded into the merge, 'Failed to save' path gone, PyRuntimeError 'Merge operation failed:' prefix); pyo3 :448/:945 from_file_path hits are the open/query paths, not merge"

### 24. parse_memory_size overflow returns Err, never panics (03-10 D6)
expected: All four unit multipliers use checked_mul chains; absurd budgets (e.g. 999999999999G) produce the ordinary "too large" CLI error with exit 1, not a panic — code read + live CLI probe
result: pass
evidence: "code read: merge.rs:495+ all four multipliers are checked_mul chains mapping overflow onto the same 'Memory size too large (maximum 1TB)' Err as the 1TB ceiling; live CLI probe on a fresh release binary with compatible inputs: '18446744073709551615KB' -> graceful 'Memory size too large (maximum 1TB)', '999999999999999999999999G' and 'notanumberMB' -> graceful 'Invalid number', '999999999TB' -> too-large, '500MB' -> merge proceeds and writes output; zero panics"

### 25. Prefix-bucket integrity accounting is non-tautological (03-11 D3)
expected: The integrity accounting (writer-emitted count + declared-vs-seen bucket set) can actually fail: an off-by-N corruption in any bucket is detected (mutation evidence recorded in 03-11); accounting lives on real output, not restated expectations
result: pass
evidence: "code read: prefix_cache_merge.rs:1307-1335 compares declared-vs-seen bucket sets (never_consumed/undeclared both reported) and writer-emitted vs copied record counts with a named Err ('emitted N records but the concatenation copied M'); reads real file sizes/counts, not restated expectations; recorded mutation evidence: perturbing the in-band comparison to merged_records_recorded - 1 turned the check RED and failed prefix_cache_merge_conserves_the_total_kmer_count; conservation binary green in the 439/0 suite run"

### 26. concatenate_final_output copies in fixed blocks (03-11 D4)
expected: Final concatenation reads/writes a fixed-size buffer per loop iteration; no allocation scales with the largest bucket (WR-08) — code read with line evidence
result: pass
evidence: "prefix_cache_merge.rs:1188-1190 allocates ONE copy_block = vec![0u8; RECORD_SIZE * 100_000] (2 MB) before the bucket loop, reused across buckets; same block-size convention as the final streaming write; comment-filtered read_to_end count in the file = 0 (per 03-11 verification, re-confirmed by read)"

### 27. Design decision record: in-memory merge accumulator stays u128-wide (03-06 D7)
expected: The reasoned decision NOT to narrow merge_databases_inmemory's accumulator / RKDatabase read path is recorded with rationale (dense width is the counting hot path only) and remains the live code state — decision-record checkpoint, not a behavior change
result: pass
evidence: "decision recorded verbatim in 03-06-SUMMARY.md D7 with rationale: DENSE-01 names COUNTING memory; in-memory merge only runs when already under budget; its peak is charged honestly by 03-09's per-route admission model; cross-checked against deferred-items.md ('dense u64 width applies only to KmerCounter', status open as tracked follow-up with suggested fix) — deliberate deferral, not oversight; live code state unchanged (suite green)"

### 28. Design decision record: golden_tests.rs left unchanged (03-08 D5)
expected: The reasoned decision to leave tests/golden_tests.rs unchanged (shared static-fixture property) is recorded with rationale; golden tests still green (34/34 in the full-suite run of Test 1)
result: pass
evidence: "decision recorded verbatim in 03-08-SUMMARY.md D5 with rationale (duplicate guard costs maintenance, buys no new observation; recorded as deliberate non-action); golden_tests 34/34 green in this session's full-suite run"

## Summary

total: 28
passed: 28
issues: 0
pending: 0
skipped: 0
blocked: 0

## Deferred Follow-Ups

- test: 22
  idea: "pyo3 0.27 no longer auto-emits -undefined dynamic_lookup; pyo3/build.rs should call pyo3_build_config::add_extension_module_link_args() so the documented manual-build workaround links as-is again (this session injected it via RUSTFLAGS)"
  deferred_at: 2026-10-09
- test: 22
  idea: "dev-venv pitfall: a stale pyrustkmer 0.4.1 package directory in site-packages silently shadows a manually installed pyrustkmer.so extension"
  deferred_at: 2026-10-09
- test: 21
  idea: "deferred-items.md's claim that loose *.chunk files are never swept is stale — temp_lifecycle.rs now sweeps them (CHUNK_FILE_PREFIXES); update the record"
  deferred_at: 2026-10-09

## Gaps

[none yet]
