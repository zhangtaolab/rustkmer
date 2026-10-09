---
gsd_state_version: "1.0"
milestone: v1.0
current_phase: 04
current_phase_name: Benchmark & Validation
status: executing
stopped_at: Completed 04-03-PLAN.md
last_updated: "2026-10-09T15:41:37.464Z"
last_activity: 2026-10-09
last_activity_desc: Phase 04 execution started
state_head: 3ae8ab37cc414c306ea2da2ac44305180c8774a2
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 4
  completed_plans: 9
milestone_name: milestone
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-09)

**Core value:** Count, query, and merge k-mers at genome scale within practical memory — fast and lean enough to compete with best-in-class tools, from both the CLI and Python.
**Current focus:** Phase 04 — Benchmark & Validation

## Current Position

Phase: 04 (Benchmark & Validation) — EXECUTING
Plan: 4 of 4
Status: Ready to execute
Last activity: 2026-10-09 — Phase 04 execution started

Progress: [████████░░] 75%

## Performance Metrics

**Velocity:**

- Total plans completed: 26
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
| 03 | 17 | - | - |

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
| Phase 03 P07 | 34min | 3 tasks | 3 files |
| Phase 03 P07 | 34 min | 3 tasks | 3 files |
| Phase 03 P08 | 4 min | 1 tasks | 2 files |
| Phase 03 P09 | 12 min | 3 tasks | 6 files |
| Phase 03 P10 | 31min | 3 tasks | 6 files |
| Phase 03 P11 | 21min | 3 tasks | 3 files |
| Phase 03 P12 | 12min | 2 tasks | 3 files |
| Phase 03 P13 | 17 min | 2 tasks | 2 files |
| Phase 03 P14 | 11min | 2 tasks | 2 files |
| Phase 03 P15 | 10min | 2 tasks | 2 files |
| Phase 03 P16 | 27min | 3 tasks | 3 files |
| Phase 03 P17 | 16min | 3 tasks | 4 files |
| Phase 04 P01 | 15 min | 3 tasks | 15 files |
| Phase 04 P02 | 16 min | 2 tasks | 2 files |
| Phase 04 P03 | 33 min | 3 tasks | 6 files |

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
- [Phase 03]: 03-07: KmerEntry::read_from is now the exact inverse of write_to with NO endianness heuristic — the count is a plain u32::from_le_bytes, matching write_to's write_u32::<LittleEndian>. The pre-fix heuristic byte-swapped every valid count above 1,000,000 (2_000_000 -> 2_156_142_080, 16_777_216 -> 1), and because the in-memory merge swapped once while the streaming merge swapped twice, the two routes produced DIFFERENT DATA for the same input under the same budget. Observed RED against the restored pre-fix reader at 1_094_848_256 before the fix
- [Phase 03]: 03-07: UnexpectedEof at a streaming run refill is the NORMAL end of that run, not damage — treating it as an error dropped the final k-mer of every merge (a 3-record chunk merged to 2 results plus an error). Mid-record chunk truncation is instead caught by a len % RECORD_SIZE check in merge_sorted_chunks, the last site that still holds the file length, because chunk files carry no record count
- [Phase 03]: 03-07: Route parity is asserted on decoded (String, u32) maps plus an EXACT expected count. Map equality alone stayed green while both routes were equally wrong for 16_777_216 — 2^24 byte-swaps to 1, a small plausible-looking value
- [Phase 03]: 03-07: The parity fixture's two inputs are built from different bases and asserted DISJOINT, because the in-memory route accumulates with saturating_add — an overlapping fixture would merge to 2x the value under test and could no longer distinguish 'read correctly' from 'summed twice'
- [Phase 03]: 03-07: No per-k-mer admission constant is pinned in tests/merge_route_parity_tests.rs. Arm B uses n*96*4 = 384 bytes/k-mer, which exceeds both today's 24 and plan 03-09's incoming 96, so the in-memory arm survives the wave boundary. A whole-file grep for the admission-constant identifier prints 0
- [Phase 03]: 03-07: pyo3/tests/test_database_merge.py is deliberately untouched — the installed pyrustkmer.so is a prebuilt artifact, so a pytest run would assert against code no longer on disk. RECORDED RESIDUAL: plan 03-10 changes PyDatabase::merge semantics (the save is folded into the merge and the 'Failed to save merged database to {}' path disappears) and that change ships with ZERO Python-level verification, because no plan in this phase may run pytest
- [Phase 03]: 03-08: The DENSE-02 guard's reference arm is a BYTE STRING the test assembles with to_le_bytes(), not a second from_kmer_pairs call - the plan's earlier shape compared one pure function with itself on the same input and stayed GREEN under the injected u64 -> u128 widening
- [Phase 03]: 03-08: Both new write-path tests were observed RED under `v as u128 ^ (1u128 << 96)` while the committed-fixture re-hash stayed GREEN. A single catching test would not have been the same claim as a differential that catches it - and the committed-fixture re-hash is exactly the blind spot WR-03 named
- [Phase 03]: 03-08: The k=32 tight-bound test drives the counter with canonical:false, because no CANONICAL k-mer encodes to u64::MAX (a 32-base T k-mer's reverse complement is 32 bases of A, which encodes to 0). The non-canonical path is a real production path (count --no-canonical) and the claim under test - how a dense u64 key is widened - is independent of the flag
- [Phase 03]: 03-08: An input fixture's claimed property is asserted, not commented. table_is_already_canonical runs canonical_kmer_u128 over every literal table entry, so a canonicalization change fails loudly instead of silently counting a different k-mer set. Same discipline as 03-06's stored_key_bytes: observe, never restate
- [Phase 03]: 03-08: tests/golden_tests.rs deliberately unchanged. It shares the static-fixture property, its own file comment is already candid that both binaries read the same manifest, and a duplicated DIFFERENTIAL is worse than a duplicated guard because independence is the property most easily lost by accident
- [Phase 03]: 03-08: A test that hashes COMMITTED artifacts proves those artifacts are unchanged; it says nothing about the code that produced them. Any file whose mandate is 'no docstring may claim something false' must also drive the production path, or its own green is the tautology it accuses others of
- [Phase 03]: 03-09: read_header_of is the single door through which every merge route learns an input's shape, and it applies from_file_path's identical data_offset != 42 rejection and error text - one rejection, two readers that cannot disagree. Routing estimate_total_kmers through it is a real behaviour change: a header carrying an unaccepted data_offset now falls back to the file-size bound with a log::warn!, which is the SAFE direction because from_file_path always refused such a file outright
- [Phase 03]: 03-09: INMEMORY_BYTES_PER_KMER = 96 is DERIVED from the three structures the in-memory route holds live (32 for the input Vec<KmerEntry> + 32 for the hashbrown (u128,u32) bucket + 32 for the Vec drained from it), and size_of::<KmerEntry>() == size_of::<(u128,u32)>() == 32 is asserted so the derivation cannot quietly become false. The source comment makes NO direction claim about the true peak: the real peak is 32N + 64U .. 32N + 68U and 96 sits at neither end, because hashbrown's control bytes are not modelled. A false direction claim in admission-control source is the same class of error 03-06 found in key.rs
- [Phase 03]: 03-09: the admission estimate is computed ONCE in merge_databases and handed to should_use_streaming, which is now a pure comparison. should_use_streaming previously re-derived it from a second copy of the per-k-mer constant - two sites computing the same quantity with two literals is exactly how they drifted
- [Phase 03]: 03-09: the total_kmers sum SATURATES. .iter().sum() panicked with 'attempt to add with overflow' on two crafted headers in a debug build, i.e. the one component whose entire job is surviving hostile input was where a panic was least acceptable. Observed RED before the fix
- [Phase 03]: 03-09: a streaming route proof is only as strong as the error it matches. 'contains("temp") || contains("No such file")' is satisfied by a k-mer-size mismatch, a bad input path and a corrupt input alike; the replacement asserts the chunk-creation operation AND the nonexistent directory's own file name, the same pair the Python test already used. Three Rust tests now use it
- [Phase 03]: 03-09: the Python copy of the admission model was not cosmetic to repair - with BYTES_PER_KMER_ESTIMATE left at 24, _within_budget returns 5760 against the core's new 11520, so test_inmemory_route_never_touches_temp_dir would have raised the D-02 RuntimeError outright and the streaming/in-memory parity test would have silently taken the streaming route on BOTH arms. The two copies are now paired BEHAVIOURALLY by parsing the figures the core echoes in its own rejection, because two comments cannot be shown to agree
- [Phase 03]: 03-09: WR-07's use_streaming is DOCUMENTED, not deprecated and not removed. Deprecating a public field with five construction sites would fail -D warnings in three files this plan has no business touching; removal is a breaking public-API change. IN-03's two total_kmers meanings are named at both sites for the same reason - a silent trap is now a labelled one
- [Phase 03]: 03-09: the external-sort compatibility error strings are byte-identical by construction, but nothing asserted it - test_validate_compatibility_kmer_size_mismatch exercises the IN-MEMORY validator, not the external-sort one. Found by checking a claim the SUMMARY was about to make rather than asserting it, then closed with a real test
- [Phase 03-10]: 03-10: merge_prologue (empty-input guard + single sweep call site) is the first statement of BOTH merge entry points — the only shape where the in-memory route sweeps and the call-site grep still reads 1
- [Phase 03-10]: 03-10: streaming writer keeps file_size: 0 via placeholder-then-seek-back header — populating it would be a silent on-disk format change; every .rkdb this route produced carries 0
- [Phase 03-10]: 03-10: RSS bound derived from the pinned working set (4 x chunk_size x 32B), not from N — GREEN 3,440,640 B vs RED 36,257,792 B sit on opposite sides of the 6,400,000 B bound
- [Phase 03-10]: 03-10: WR-02 deferred not fixed — rejecting merge_mode='memory' on the PrefixCache route would change outcomes for every existing prefix-cache caller; now warned + documented instead
- [Phase 03-10]: 03-10: PyDatabase::merge save folded into the merge (semantic change) with zero Python-level verification — recorded as MERGE-04 residual because the installed pyrustkmer.so is prebuilt
- [Phase 03-11]: 03-11: Partial prefix-cache merges now FAIL loudly — merge_prefix_buckets returns Err when any bucket failed (names failed/total buckets, points at preserved shards); the deferred 03-02 item closed as the intended behaviour change, propagating unchanged to CLI and PyO3
- [Phase 03-11]: 03-11: should_remove_shards() is the ONE place deciding shard removal — success releases shards (D-06 peak-disk), Err and keep_intermediate preserve them (WR-04 recovery path, paths logged)
- [Phase 03-11]: 03-11: The tautological total_kmers != total_kmers_in_files check is replaced by TWO phase-independent signals — merged_records_recorded (writer-emitted count, catches zero-length/truncated buckets) and non_empty_buckets_recorded vs buckets_seen (catches a merged file missing at concatenation); valid for OVERLAPPING inputs, deliberately not compared against the Phase-1 input total; observed red under a -1 operand perturbation
- [Phase 03-11]: 03-11: The orphan sweep reclaims loose rustkmer_sort_*/rustkmer_merge_*.chunk files older than the TTL (CHUNK_FILE_PREFIXES/SUFFIX pub consts mirror TempFileManager's naming); routing streaming chunks into the RAII subdir was considered and REJECTED as an ExternalMerger::new contract change — recorded in 03-11-SUMMARY for a future plan
- [Phase 03]: 03-12: Canonical cross-input check is a separate merge_prologue loop gated on !use_prefix_cache, NOT inside validate_header_compatibility — that fn's contract is the prefix-cache route's convert-to-canonical semantics; overloading it would revoke the advertised mixed-canonical capability (WR-04 triage)
- [Phase 03]: 03-12: The prologue's k-mer-size check reuses validate_header_compatibility verbatim so the k-mismatch message cannot drift — prefix_cache_kmer_size_mismatch_keeps_its_error_text stayed green byte-for-byte; route-level calls kept as defense-in-depth
- [Phase 03]: 03-12: CR-03 closed in merge_prologue so PyDatabase.merge inherits the rejection through merge_databases_to_path with zero pyo3 edits; RED evidence captured for BOTH streaming rejection axes (k mismatch and mixed canonical) against the pre-fix tree
- [Phase 03]: 03-14: validate_merge_compatibility is pub on the cli module path (parse_memory_size/resolve_thread_count_from precedent) so the header-only property is assertable from an external integration test crate
- [Phase 03]: 03-14: --check-compatibility validates via read_header_of + RKDatabase::new(header) feeding validate_compatibility_verbose UNCHANGED — the header-only DB carries everything that fn reads (kmer_size/is_canonical/header.total_kmers), so its message text cannot drift and zero entries materialize
- [Phase 03]: 03-14: loop-1's error texts are the preserved ones; two documented deltas — prefix-cache k error gains the third recovery bullet, canonical error keeps boolean formatting (loop 2's canonical arm was unreachable pre-plan)
- [Phase 03]: 03-14 Rule 1 fix: --check-compatibility's 'Total k-mers' line printed the k-mer SIZE (validate_compatibility_verbose returns (kmer_size, canonical)); now prints the summed header record counts
- [Phase 03]: 03-15: get_prefix_4mer buckets by the HIGH byte (first 4 bases) so index-order concatenation is globally ascending and the header's sorted:true is truthful by construction — option (a) chosen over (b) sorted:false (linear-scan degradation) and (c) sort-at-concatenation (re-sorts the dataset the route exists to avoid); header write/concatenation/prefix_to_dna deliberately untouched, their labels become correct for the first time
- [Phase 03]: 03-15: the plan's unit-test literal 0x010000 rendered as 0x0100_0000 at k=16 — the literal is a 24-bit number (high byte 0x00) so the plan's own strict bucket==0x01 assertion was unsatisfiable; the integration fixture keeps the literal pair 0x0000FF/0x010000 (red pre-fix, green post-fix at k=16)
- [Phase 03]: 03-15: CR-02's consumer proof captured red on the pre-fix tree — prefix-cache query_kmer answered None where the in-memory route answered Some(1) on k-mer 0x1 (binary search over (low_byte, kmer)-ordered entries); route parity of ANSWERS is asserted, not assumed
- [Phase 03]: CR-01 (mixed-canonical prefix-cache ordering residual) triaged by user 2026-10-09: fix in-phase via third gap round (/gsd-plan-phase 03 --gaps) rather than accepting as advisory — Fresh-review critical on the opt-in mixed-canonical prefix-cache route: split_files_by_prefix buckets by canonicalized high byte but writes raw kmer, so output can be non-ascending under sorted:true (silent wrong results for binary-search consumers). One-site fix (write processed_kmer + propagate canonicalization errors). Verifier scored 10/11 with 0 failures; user chose fix-now over accept-as-advisory.
- [Phase 03]: 03-16: The fix is exactly one site - the shard stores processed_kmer (bucket key == sort key == stored key) and canonicalization errors propagate via ?, making index-order concatenation globally ascending and letting bucket writers sum the two encodings of one k-mer (CR-01/WR-03, T-03-53/T-03-54)
- [Phase 03]: the plan's 0xFFFFFF literal is a 24-bit key at k=16 whose canonical form is 0x0000FF - the all-T meet-and-sum intent requires 0xFFFFFFFF; same k=16 literal trap as 03-15's 0x010000
- [Phase 03]: a mixed-canonical ORDER violation is only RED-provable when a later bucket exists - 24-bit literals all have high byte 0x00 at k=16 so everything collapses into bucket 0x00 where the hashmap writer's sort erases misplacement; a true-high-byte key (0x0100_0000) was added to make windows(2) discriminate
- [Phase 03]: 03-16 KNOWN RESIDUAL (deferred): merge_single_prefix_streaming assumes ascending shard runs, but post-fix a non-canonical input's shard can be non-ascending under mixed-canonical merges - correctness proven on the auto/hashmap path only; plan froze both bucket writers, logged deferred-items.md + WINDOWS.md #17
- [Phase 03]: 03-17: Option (a)+(b) over (c) for the streaming-writer gap — ExternalSortMerger::new forces the sorting (hashmap) per-bucket writer for mixed-canonical header sets (keeps merge_mode='streaming' merges SUCCEEDING correctly instead of erroring) while merge_single_prefix_streaming refuses adjacent descending runs; per-shard sorting was rejected for doubling phase-1 IO
- [Phase 03]: 03-17: The refusal reads RECORDS at both pop_front consumption sites, not headers — a heap entry mirrors its file's buffer front and the run-adjacent duplicate pop is the only other buffer exit, so every record is validated exactly once for any caller, including direct calls that bypass the header-keyed override; equal adjacent keys stay legal (strictly-less-than only)
- [Phase 03]: 03-17: T-03-57 accepted with rationale — forcing the in-memory per-bucket writer on mixed-canonical merges trades the streaming writer's bounded footprint for correctness on that corner; per-bucket scope (~1/256 of the data), the hashmap writer's own available-memory warning still fires, and the override is loudly logged
- [Phase 03]: 03-17: The refusal unit test drives merge_single_prefix_streaming DIRECTLY on a raw shard so it stays RED on the post-override tree — proving the override and the refusal are independent layers (headers vs records)
- [Phase 03]: 03-17: WINDOWS.md frontmatter counts repaired to the true entry census (10/3/5/18, drifted to 11/19) before running windows-fixed — the CLI recomputes and refuses to operate on a disagreeing ledger
- [Phase 04]: 04-01: count inputs go through -i (num_args 1..) and FASTQ headers carry '@' — the plan's builder sketch failed clap and the bio reader; fixed against args.rs ground truth
- [Phase 04]: 04-01: bench.py slice extraction streams gunzip -c via pure-subprocess list form (no sh -c) — removes the env-path command-injection surface instead of validating metacharacters
- [Phase 04]: 04-01: mode precedence is --mode > RUSTKMER_BENCH_MODE > size ladder (1 GiB default, injectable); a single resolved input is measured twice honestly rather than fabricating a second input
- [Phase 04]: 04-01: exact-count self-check (reads x (L-k+1)) scoped to synthetic mode; merge count-conservation and distinct-union assertions run in every mode
- [Phase 04]: 04-01: blanket .gitignore *.txt rule silently excluded the time fixtures; negation entries added (golden *.rkdb precedent)
- [Phase 04]: 04-02: comparison protocol engages at --reps >= 2 — multi-rep means both tools; CI's reps=1 synthetic path never needs jellyfish (must_haves satisfied by construction)
- [Phase 04]: 04-02: hash_size and decompressor join paths in the T-04-03 screen (regex allowlists) — both cross into the single sh -c string from CLI args; screening paths alone would leave the pipe open
- [Phase 04]: 04-02: -s 10G default commits ~85 GiB RSS even on smoke inputs (jellyfish touches the whole initial hash) — smoke comparisons pass --hash-size 1G; full-scale milestone runs keep the generous 10G fairness default
- [Phase 04]: 04-02: every comparison run asserts count parity on the measured input itself — a timing comparison between tools that counted different things is meaningless; plan's builder sketch omitted -i, kept per args.rs (04-01 Rule 1 repeat)
- [Phase 04]: 04-03: compare.py derives arm medians from reps when arm-level median fields are absent — the plan's CI step (reps=1 default) emits no median fields, so without the fallback every CI gate would exit 2; median-of-one is that rep, MEDIAN-not-mean unit-pinned
- [Phase 04]: 04-03: baselines keep the rustkmer arms only (count-A/count-B/merge) — CI current results are produced without jellyfish (BENCH-04) and one-sided arms exit 2, so the jellyfish arm from the --reps 3 dev-host run is dropped by the documented conversion
- [Phase 04]: 04-03: committed baselines must come from the runner class that gates them — the interim 16-thread M4 Max darwin baseline breached +230%/+1041% wall against the 3-vCPU macOS runner on the first CI run; both final baselines are converted from one run's CI artifacts (bootstrap procedure)

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

None yet.

### Blockers/Concerns

[Issues that affect future work]

- No pyo3 test in phase 3 can be EXECUTED: pyo3/pyproject.toml sets python-source="." with module-name="pyrustkmer" while pyo3/pyrustkmer/ has never existed, so maturin build/develop both refuse (and CI's pyo3-build job runs maturin build, so that job cannot be green as configured); addopts also hard-codes --cov-fail-under=80 against a compiled extension, so every pytest run exits 1 even when green; and .github/workflows/ci.yml has no pyo3 pytest job at all. Consequence: 03-09's admission-model change and 03-10's PyDatabase::merge semantics change both ship with ZERO Python-level verification. One-line fix that would unblock all of it: delete the python-source key from [tool.maturin] (a pure-Rust extension has no Python sources to package). Carried in deferred-items.md + WINDOWS.md with open status.
- deferred-items.md's IN-02 clippy entry is STALE and should be marked closed: the 4 `useless_borrows_in_formatting` sites it names no longer exist (src/io/fastq.rs:216 writes `self.file_path`, :343 writes `path`, src/io/fasta.rs:56 writes `self.file_path`, and fasta.rs:153 is not a `format!` at all), and `cargo clippy --all-targets -- -D warnings` — the entry's own reproduction command — exits 0. Verified by plan 03-09; the file itself was outside that plan's scope.
- [Phase 03 UAT 2026-10-09] Partially superseded by the UAT session: the pyo3 extension WAS built and the merge suite EXECUTED 12/12 green (manual PYO3_PYTHON build + RUSTFLAGS dynamic_lookup + manual .so install — see 03-UAT test 22); the maturin/CI structural issues (python-source key, --cov-fail-under, missing CI pytest job) remain open. pyo3 0.27 additionally needs the extension crate's build.rs to call pyo3_build_config::add_extension_module_link_args() — deferred to ROADMAP backlog 999.1.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-10-09T15:41:37.368Z
Stopped at: Completed 04-03-PLAN.md
Resume file: None
