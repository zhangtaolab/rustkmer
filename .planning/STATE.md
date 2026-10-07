---
gsd_state_version: "1.0"
milestone: v1.0
current_phase: 03
current_phase_name: Memory Safety
status: executing
stopped_at: Completed 03-01-PLAN.md
last_updated: "2026-10-07T02:28:57.188Z"
last_activity: 2026-10-07
last_activity_desc: Phase 03 execution started
state_head: 3aa2d2ff2b96e3d456d19a7e22ce380d1c54d25b
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

Phase: 03 (Memory Safety) — EXECUTING
Plan: 2 of 5
Status: In progress
Last activity: 2026-10-07 — Completed 03-01 (header-only merge estimator + hard admission control)

Progress: [████░░░░░░] 1/5 plans (Phase 03)

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

Last session: 2026-10-07T02:28:57.101Z
Stopped at: Completed 03-01-PLAN.md
Resume file: None
