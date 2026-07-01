---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 3
current_phase_name: Memory Safety
status: completed
stopped_at: Completed 02-05-PLAN.md (PCOUNT-04 correctness gate — Phase 02 complete)
last_updated: "2026-07-01T11:13:47.293Z"
last_activity: 2026-07-01
last_activity_desc: Phase 02 complete, transitioned to Phase 3
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 9
  completed_plans: 9
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-30)

**Core value:** Count, query, and merge k-mers at genome scale within practical memory — fast and lean enough to compete with best-in-class tools, from both the CLI and Python.
**Current focus:** Phase 02 — Parallel Counting

## Current Position

Phase: 3 — Memory Safety
Plan: Not started
Status: Phase 02 complete; ready for Phase 03
Last activity: 2026-07-01 — Phase 02 complete, transitioned to Phase 3

Progress: [██████████] 100% (Phase 02)

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

Last session: 2026-07-01T11:00:00.000Z
Stopped at: Completed 02-05-PLAN.md (PCOUNT-04 correctness gate — Phase 02 complete)
Resume file: .planning/phases/02-parallel-counting/02-05-SUMMARY.md
