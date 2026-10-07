---
gsd_state_version: "1.0"
milestone: v1.0
current_phase: 03
current_phase_name: Memory Safety
status: gap-closure-in-progress
stopped_at: "Completed 03-06-PLAN.md (DENSE-01 un-inverted: KmerKey deleted, real 4M-entry RSS ratio 0.5152)"
last_updated: "2026-10-07T12:15:18.375Z"
last_activity: 2026-10-07
last_activity_desc: "Completed 03-06 (G1: DENSE-01 un-inverted — KmerKey deleted, real 4M-entry RSS ratio 0.5152)"
state_head: 490fa6ed7bfc6a7e82330a58e39772ff8e2e3920
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 9
  completed_plans: 9
milestone_name: milestone
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-30)

**Core value:** Count, query, and merge k-mers at genome scale within practical memory — fast and lean enough to compete with best-in-class tools, from both the CLI and Python.
**Current focus:** Phase 03 — Memory Safety

## Current Position

Phase: 03 (Memory Safety) — GAP CLOSURE in progress (6/11 plans complete)
Plan: 6 of 11
Status: 03-06 closed G1 (DENSE-01 was inverted; now measured at ratio 0.5152 with mutation-proven assertions). Remaining: 03-07..03-11, then `/gsd-verify-work 03`. Still open from 03-VERIFICATION.md: G2 (no merge strategy is memory-bounded) and G3 (routes disagree above 1M counts).
Last activity: 2026-10-07 — Completed 03-06 (G1: DENSE-01 un-inverted — `KmerKey` deleted, dense table is `DashMap<u64,u32>`, 35.66 vs 69.21 B/entry over 4M entries)

Progress: [█████░░░░░] 6/11 plans (Phase 03)

## Performance Metrics

**Velocity:**

- Total plans completed: 9
- Average duration: - min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Foundation & Quality | 0/4 | - | - |
| 2. Parallel Counting | 0/4 | - | - |
| 3. Memory Safety | 0/5 | - | - |
| 4. Benchmark & Validation | 0/4 | - | - |
| 01 | 4 | - | - |
| 02 | 5 | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01 P01 | 25 | - tasks | - files |
| Phase 01 P02 | 16 | 2 tasks | 16 files |
| Phase 01 P03 | 23m | 3 tasks | 27 files |
| Phase 01 P04 | ~26 min | 2 tasks | 3 files |
| Phase 02 P01 | 8min | - tasks | - files |
| Phase 02 P01 | 8min | 2 tasks | 3 files |
| Phase 02 P04 | ~6min | 1 tasks | 7 files |
| Phase 02 P02 | ~12 min | 2 tasks | 3 files |
| Phase 02 P03 | ~10 min | 1 tasks | 2 files |
| Phase 02 P05 | ~25 min | 2 tasks | 3 files |
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 03 P01 | 42min | 2 tasks | 6 files |
| Phase 03 P02 | 38min | 2 tasks | 7 files |
| Phase 03 P03 | 10min | 2 tasks | 7 files |
| Phase 03 P04 | 10min | 1 tasks | 4 files |
| Phase 03 P05 | 35min | 2 tasks | 5 files |
| Phase 03 P06 | 20 min | 3 tasks | 7 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Initial planning]: Performance (not features, not broad tech debt) is this milestone's focus
- [Initial planning]: Both CLI and Python are first-class surfaces — shared core wins flow to both
- [Initial planning]: Breaking format/API changes are deferred to the point of decision
- [Initial planning]: Reference comparator is Jellyfish2 for v1 (KMC3 comparison deferred to v2)
- [Phase ?]: 01-01: Established .github/workflows/ci.yml as the FOUND-01 merge gate (fmt/clippy/test/pyo3-wheel-build on PR+push to dev/main)
- [Phase ?]: 01-01: Cleared all 85 pre-existing clippy warnings (68 root + 17 pyo3) so -D warnings is green on both crates
- [Phase ?]: 01-01: Distinct cargo cache keys per crate (cargo-root- / cargo-pyo3-) to prevent cache stampede across separate lockfiles
- [Phase ?]: 01-02: Library code (src/ excl cli/ + pyo3/src/ live modules) now emits via log:: facade; clippy #![deny(print_stdout/print_stderr/dbg_macro)] in src/lib.rs + pyo3/src/lib.rs makes the gate self-enforcing; src/cli/mod.rs has the paired #![allow] exempting legitimate CLI output
- [Phase ?]: 01-02: Channel-only migration per SPEC R2 - message text and format args preserved verbatim; CJK translation deferred to plan 01-04. pyo3 stays silent by default (no env_logger init, D-17); CLI users see log::info! diagnostics at the preserved info default filter (P2)
- [Phase ?]: D-10 honored: golden fixtures captured BEFORE refactor (12caa42 precedes 68f3d31)
- [Phase ?]: count.rs delegates to KmerEntry::write_to; data_offset clamp replaced with loud Err in both readers
- [Phase ?]: P3 byte-identity proven: 12 golden sha256s match post-refactor (k in {21,32,64} x canonical x sorted)
- [Phase ?]: D-07 delivered: tests/cjk_check.rs uses syn::visit::Visit overriding visit_lit + visit_macro (+ visit_attribute for #[doc] skip)
- [Phase ?]: FOUND-04 complete: src/ CJK literals translated to English; pyo3/src/ has zero non-comment CJK quoted strings
- [Phase ?]: 02-01: Added --threads Option<usize> to Commands::Count (Option not default_value so 'unset' is distinguishable from '0' - required by D-07 precedence chain)
- [Phase ?]: 02-01: Split resolve_thread_count_from (pure, testable) from resolve_thread_count (env-reading wrapper) to avoid env-var races; used rayon::current_num_threads() for num_cpus fallback
- [Phase ?]: 02-01: Centralized build_global in execute_count (let _ = discards Err); merge.rs both .expect() sites made Err-tolerant (Pitfall 3 count->merge panic mitigated)
- [Phase ?]: 02-04: Captured 6 pre-refactor count MAPS as committed JSON baselines (D-10 golden-capture-first; k in {21,32,64} x canonical) BEFORE 02-02 dashmap swap — ground truth for 02-05 differential
- [Phase ?]: 02-02: Swapped KmerCounter.table from parking_lot::RwLock<HashMap<u128,u32>> to dashmap::DashMap<u128,u32> (D-04/D-05) with atomic per-key entry().and_modify(flag-then-check).or_insert_with() increment; public API byte-identical; dashmap 6.2.1 pins hashbrown ^0.14.5 (no version dup)
- [Phase ?]: 02-02: Parallelized process_fasta_file/process_fastq_file via rayon chunked par_iter (CHUNK_SIZE=4096, D-01); bypassed the process_file callback (W-3: &Record borrow tied to reader) by reading owned records directly via bio::io::Reader::records() into a bounded Vec; gzip stays single-threaded (D-02)
- [Phase ?]: 02-02: D-09 default-sort flip landed (should_sort = !*no_sort); --sort retained as backward-compatible alias; sharded DashMap iteration is non-deterministic so default-sort restores run-to-run reproducibility
- [Phase ?]: 02-03: Used py.detach (NOT py.allow_threads) for GIL release — pyo3 0.27.2 source confirms allow_threads is #[deprecated(since=0.26.0)] and delegates to detach; RESEARCH note claiming detach is 0.28+ only was factually inverted
- [Phase ?]: 02-03: Added rayon as direct dep to pyo3/Cargo.toml (Rule 3 — plan wrongly assumed rayon was accessible by name; it is only transitive via rustkmer path dep); used std::thread::available_parallelism() for None->all-cores (no num_cpus dep)
- [Phase ?]: 02-05: PCOUNT-04 gate GREEN — 4 un-ignored asserting Rust tests (differential_threads_1_vs_n, baseline_matches_current, deterministic_sorted_output, test_thread_resolution) + 4 Python tests prove parallel counting == sequential counting (1-vs-N identical across D-13 matrix), post-refactor counts == committed pre-refactor baselines (D-10), output is deterministic run-to-run (D-09), D-07 precedence chain works (PCOUNT-01), PyCounter(threads=1)==(threads=N) at the Python layer (PCOUNT-03)
- [Phase ?]: 02-05: Drove the 1-vs-N differential via std::thread::scope against a shared Arc<KmerCounter> (DashMap interior mutability) instead of CLI subprocess — build_global is one-call-per-process; thread::scope exercises the same entry().and_modify().or_insert_with() atomicity path the CLI's rayon workers rely on
- [Phase ?]: 02-05: Made resolve_thread_count_from pub in src/cli/commands/count.rs (was private fn) so the integration test binary can call it directly (pub(crate) insufficient — integration tests are external crates); one-line visibility change authorized by plan 02-05 Task 1 action (d)
- [Phase 03]: 03-01: estimate_total_kmers is a pub associated fn on RKDatabase (not a free fn) so the integration test can assert the D-01 header-only property from an external test crate; mirrors the 02-05 resolve_thread_count_from precedent — Integration tests are external crates - a private/free fn would be unassertable, leaving MERGE-02 without a direct proof
- [Phase 03]: 03-01: A corrupt/unreadable .rkdb header falls back to the file-size estimate instead of erroring, so the merge still routes conservatively to streaming and surfaces real corruption during the streaming path's own per-chunk validation — Returning Err would fail the merge before a strategy is chosen - a worse failure mode than over-estimating. Fallback only over-estimates (threat T-03-01)
- [Phase 03]: 03-01: Merge path selection is observed in tests via a nonexistent temp_dir probe (streaming writes chunk files there, in-memory does not) rather than adding a public strategy-returning API or capturing logs — merge_databases returns an RKDatabase, not a strategy tag; the probe is a deterministic side-effect discriminator that needs no public API change
- [Phase 03]: 03-01: estimated_memory uses saturating_mul instead of the original `total_kmers as usize * 24` — The old form could overflow into a panic in debug builds given a large header value
- [Phase 03]: 03-01: Fixed two latent streaming-merge data-loss bugs (StreamingMergeIterator heap-refill strand; TempFileManager chunk-name collision) as part of this plan — MERGE-01 promotes that exact path to hard-route default. Measured 200 k-mers in -> 5 out. Shipping the hard route on top of a truncating merge would have turned a latent bug into guaranteed data corruption for every over-budget merge
- [Phase 03]: 03-01: Fixed 4 pre-existing clippy useless_borrows_in_formatting errors in src/io/{fasta,fastq}.rs (toolchain drift) to unblock the plan's -D warnings gate — Plan acceptance criteria list `cargo clippy --all-targets -- -D warnings` as blocking; logged to deferred-items.md before fixing
- [Phase 03]: 03-01: estimate_total_kmers is a pub associated fn on RKDatabase (not a free fn) so the integration test can assert the D-01 header-only property from an external test crate; mirrors the 02-05 resolve_thread_count_from precedent — Integration tests are external crates - a private/free fn would be unassertable, leaving MERGE-02 without a direct proof
- [Phase 03]: 03-01: A corrupt/unreadable .rkdb header falls back to the file-size estimate instead of erroring, so the merge still routes conservatively to streaming and surfaces real corruption during the streaming path's own per-chunk validation — Returning Err would fail the merge before a strategy is chosen - a worse failure mode than over-estimating. The fallback only over-estimates (threat T-03-01)
- [Phase 03]: 03-01: Merge path selection is observed in tests via a nonexistent temp_dir probe (streaming writes chunk files there, in-memory does not) rather than adding a public strategy-returning API or capturing logs — merge_databases returns an RKDatabase, not a strategy tag; the probe is a deterministic side-effect discriminator needing no public API change
- [Phase 03]: 03-01: estimated_memory uses saturating_mul instead of the original `total_kmers as usize * 24` — The old form could overflow into a panic in debug builds given a large header value
- [Phase 03]: 03-01: Fixed two latent streaming-merge data-loss bugs (StreamingMergeIterator heap-refill strand; TempFileManager chunk-name collision) as part of this plan — MERGE-01 promotes that exact path to hard-route default. Measured 200 k-mers in -> 5 out. Shipping the hard route on top of a truncating merge would have turned a latent bug into guaranteed corruption for every over-budget merge
- [Phase 03]: 03-01: Fixed 4 pre-existing clippy useless_borrows_in_formatting errors in src/io/{fasta,fastq}.rs (toolchain drift) to unblock the plan's -D warnings gate — Plan acceptance criteria list `cargo clippy --all-targets -- -D warnings` as blocking; logged to deferred-items.md before fixing

- [Phase 03]: 03-02: The sweep's single call site is the top of RKDatabase::merge_databases (not ExternalSortMerger::new), so one placement covers all three merge strategies — the plan's key_links asked for exactly one site in the shared dispatch
- [Phase 03]: 03-02: The per-bucket best-effort shard delete was de-gated from `result.is_ok() &&` rather than deleted outright. It is a peak-disk optimization, not the cleanup guarantee; Drop is the guarantee. Removing it would have made a long merge retain every bucket's shards until the end
- [Phase 03]: 03-02: MERGE_TEMP_PREFIX is a pub const, not a repeated literal — subdir creation and the sweep must agree on the string or orphan cleanup silently stops working
- [Phase 03]: 03-02: The sweep refuses symlinks carrying the prefix (entry.file_type(), not entry.metadata()) so a planted symlink in a shared temp dir cannot redirect remove_dir_all at an arbitrary tree — T-03-07 was accepted, escalating it to arbitrary-target deletion was not
- [Phase 03]: 03-02: Two pre-existing prefix-cache bugs were logged to deferred-items.md, not fixed — external_sort_merge_output.tmp is written outside the subdir and never removed (T-03-05/T-03-06), and merge_prefix_buckets returns Ok(()) after bucket failures, producing a silent partial merge. Neither is caused by this plan and fixing the second would change merge outcomes
- [Phase 03]: 03-02: Subdir uniqueness uses rand_bytes(8), not the PID — random bytes also survive PID reuse after a reboot, which PID-based naming does not
- [Phase 03]: 03-03: KmerKey's narrowing debug_assert lives in KmerKey::from_u128 rather than in increment (the plan's location) — get_count and merge narrow at the same boundary, so one assertion covers all three call sites; increment still trips it because it routes through from_u128
- [Phase 03]: 03-03: No use_u64 field on KmerCounter — width is derived from the immutable kmer_length on demand. kmer_length cannot change for a counter's lifetime, so a cached flag could only ever be redundant state capable of disagreeing with the length it came from
- [Phase 03]: 03-03: DENSE-01's 'roughly half' is asserted on the keyed PAYLOAD (20B -> 12B, ratio 0.6), not the overhead-inclusive total (36/44 = 0.818). The plan's own formula mandates the same 24-byte modelled overhead on both widths, which makes its proposed [0.4,0.7] band unreachable on the total — the band brackets the payload ratio
- [Phase 03]: 03-03: The dense differential uses THREE independent references per cell (counter-free u128 oracle, production u128-encoder counter, committed golden .rkdb) rather than two — a single two-way comparison would not localize a failure to 'the counter' vs 'the shared encoders'
- [Phase 03]: 03-03: The D-10 golden baseline caught a 2-character transcription drift in the differential's hand-copied GOLDEN_INPUT (all 6 tests failed, one entry off by 2). Fix was to splice the generator's array in programmatically instead of by transcription — evidence that reusing committed baselines rather than regenerating them is the right discipline
- [Phase 03]: 03-04: The u128 arm of the cross-plan composition differential is the committed Phase 1/2 golden .rkdb (D-10), not a second KmerCounter run — The plan allowed either; 03-03 exposed no forced-u128 constructor, and the fixture is the better reference anyway - it is what production emitted BEFORE any of Phase 3, so it is independent of the code under test. A pre-merge equality assertion then turns an ambiguous two-plan failure into 'count stage or merge stage'
- [Phase 03]: 03-04: A plan's 'streaming route' arm is only proven if the route ITSELF is asserted - the budget must be derived from the estimator, not hard-coded — The plan text and first draft used max_memory_usage: 1024, but the golden fixture's 20 unique k-mers estimate to only 960 bytes, so every 'streaming' arm silently ran the IN-MEMORY path and the entire cross-plan composition claim was vacuous. Only a mutation test caught it. tests/dense_merge_integration_tests.rs now derives the budget from RKDatabase::estimate_total_kmers and proves the route with 03-01's nonexistent-temp_dir probe
- [Phase 03]: 03-04: The in-memory test arm pairs HUGE_BUDGET_BYTES with merge_mode 'auto', never 'memory' — With merge_mode 'memory' an over-budget merge returns Err from the D-02 REJECT, which is indistinguishable by outcome alone from a temp-file failure, so the route probe would misreport the route. 03-01 already owns merge_mode 'memory' behavior
- [Phase 03]: 03-04: Composition is asserted as a 4-WAY decoded-map equality (u64/u128 x in-memory/streaming), not pairwise — 03-01 made route selection budget-dependent, so a claim covering one route is half a claim; cross-arm equality also catches route-specific regressions that per-arm exactness assertions would miss
- [Phase 03]: 03-04: Added header-accounting + total-count-conservation cross-validation to merge_routing_tests.rs (the only 03-01 edit this plan made) — 03-01 deferred nothing explicitly, but auditing its four routing tests showed a real gap: each pins union size and spot-checked counts, none pins the invariants a merge can break without changing either. The live prefix-cache defect 03-02 logged (merge_prefix_buckets returns Ok(()) after bucket failures -> valid .rkdb with undercounted total_kmers) is exactly this shape and would pass every existing routing test
- [Phase 03]: 03-04: Every merge assertion pins exact k-mer COUNTS and header accounting; none asserts merely 'non-empty' — The direct lesson of 03-01's two data-loss bugs, which survived because test_merge_streaming_basic asserted only non-emptiness (200 k-mers in, 5 out)
- [Phase 03]: 03-04: The new integration test binary mutates production code to prove it can fail, and reverted it — Four defects injected (streaming k-mer drop, in-memory k-mer drop, dense widening high bit, header undercount); each is caught by a specific named assertion. For a verification-only plan the deliverable is not 'tests pass' but 'tests CAN fail' - a GREEN gate that cannot fail reports the phase verified while proving nothing
- [Phase 03]: 03-05: max_memory is REUSED from src/cli/commands/merge.rs::parse_memory_size (made pub) rather than copied into the binding — a duplicated parser would accept different strings on the two surfaces, and the drift would surface only as a user's budget behaving differently in Python than in the shell, the exact failure MERGE-04 exists to prevent
- [Phase 03]: 03-05: Both new kwargs are keyword-only (* in the pyo3 signature), mirroring PyCounter(threads=...) from 02-03. This narrows accepted call shapes but cannot regress an existing caller — the pre-MERGE-04 signature accepted only two positional args
- [Phase 03]: 03-05: MergeConfig is assembled with struct-update syntax, not the field-by-field form the plan spelled out, because clippy::field_reassign_with_default (denied by the pyo3 crate's own -D warnings gate, which the plan lists as a blocking criterion) rejects that exact shape
- [Phase 03]: 03-05: No new public API for route observation — merge still returns None. TMPDIR pointed at a nonexistent directory turns MergeConfig::temp_dir's existing default into a side-effect discriminator, so 03-01's probe reached the Python surface with zero new API and no log capture
- [Phase 03]: 03-05: The over-budget test budget is 1024 (parse_memory_size's floor) and is usable only because the helper ASSERTS the derived estimate exceeds it first — that assertion turns a shrunken fixture from a silently vacuous routing test into a loud failure (inherited from 03-04's finding)
- [Phase 03]: 03-05: Pre-existing pyo3 breakage reported, not fixed — maturin's python-source pairing (breaks the CI pyo3-build job's maturin build step) and the --cov-fail-under=80 addopts gate (makes every pyo3 pytest run exit 1). Both are one-line config fixes outside MERGE-04, recorded in deferred-items.md + WINDOWS.md with open status so a human decides at ship time
- [Phase 03]: 03-06: The dense/wide width lives on the TABLE (a private two-variant CounterTable enum), not on the KEY — an enum key with a u128 variant costs 32 bytes whichever variant is populated, because layout is fixed at compile time, which is why plan 03-03's density claim was inverted — 03-06: The dense/wide width lives on the TABLE (a private two-variant CounterTable enum), not on the KEY — an enum key with a u128 variant costs 32 bytes whichever variant is populated, because layout is fixed at compile time, which is why plan 03-03's density claim was inverted
- [Phase 03]: 03-06: stored_key_bytes()/uses_dense_storage() match the LIVE CounterTable variant and never re-derive from kmer_length — that single rule is what makes the DENSE-01 assertions observations rather than restatements, and what turns them red under the 'always Wide' mutation — 03-06: stored_key_bytes()/uses_dense_storage() match the LIVE CounterTable variant and never re-derive from kmer_length — that single rule is what makes the DENSE-01 assertions observations rather than restatements, and what turns them red under the 'always Wide' mutation
- [Phase 03]: 03-06: The entry chain is one bump_entry! macro invoked once per arm with modify/insert blocks passed in — increment and merge genuinely differ in overflow predicate and fresh-insert bookkeeping, so forcing them into one parameterised shape would hide a real semantic difference — 03-06: The entry chain is one bump_entry! macro invoked once per arm with modify/insert blocks passed in — increment and merge genuinely differ in overflow predicate and fresh-insert bookkeeping, so forcing them into one parameterised shape would hide a real semantic difference
- [Phase 03]: 03-06: dense_narrowing_rejects_high_bits_on_the_u64_path was REWRITTEN against the public increment(), not deleted — the type it named was deleted, but dropping the test would have silently removed the only coverage of threat T-03-09's detection path — 03-06: dense_narrowing_rejects_high_bits_on_the_u64_path was REWRITTEN against the public increment(), not deleted — the type it named was deleted, but dropping the test would have silently removed the only coverage of threat T-03-09's detection path
- [Phase 03]: 03-06: The RSS measurement holds each counter alive while measuring its sibling. An RSS delta after a drop measures allocator free-list reuse, not footprint — a clean 4M-entry dense counter read 2.51 B/entry, below its own 16-byte slot, which is physically impossible and was the tell — 03-06: The RSS measurement holds each counter alive while measuring its sibling. An RSS delta after a drop measures allocator free-list reuse, not footprint — a clean 4M-entry dense counter read 2.51 B/entry, below its own 16-byte slot, which is physically impossible and was the tell
- [Phase 03]: 03-06: Deliberate deferral — the dense width is applied to KmerCounter's table only, NOT to merge_databases_inmemory's HashMapBrown<u128,u32> accumulator (src/database/format.rs:912) or the Vec<KmerEntry> read path. DENSE-01 names COUNTING memory; the in-memory route only runs when already under budget, and narrowing those structures needs its own width-selection point and its own decoded-level differential — 03-06: Deliberate deferral — the dense width is applied to KmerCounter's table only, NOT to merge_databases_inmemory's HashMapBrown<u128,u32> accumulator (src/database/format.rs:912) or the Vec<KmerEntry> read path. DENSE-01 names COUNTING memory; the in-memory route only runs when already under budget, and narrowing those structures needs its own width-selection point and its own decoded-level differential

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

None yet.

### Blockers/Concerns

[Issues that affect future work]

None yet.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-10-07T12:15:18.278Z
Stopped at: Completed 03-06-PLAN.md (DENSE-01 un-inverted: KmerKey deleted, real 4M-entry RSS ratio 0.5152)
Resume file: None
