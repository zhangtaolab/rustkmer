---
gsd_state_version: "1.0"
milestone: v2.0
milestone_name: k=21 Counting Parity
status: Awaiting next milestone
stopped_at: Phase 10 complete — verified 8/8, review disposition 0 open; D3 answered (Phase 11 not executed); ready for milestone audit
last_updated: "2026-11-14T04:39:24.823Z"
last_activity: 2026-11-14
last_activity_desc: Milestone v2.0 completed and archived
state_head: 73f9451d13bfa93a9861313b87ecc5150369482b
progress:
  total_phases: 7
  completed_phases: 6
  total_plans: 29
  completed_plans: 29
  percent: 86
current_phase: 10
current_phase_name: Benchmark Verdict
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-11-14)

**Core value:** Count, query, and merge k-mers at genome scale within practical memory — fast and lean enough to compete with best-in-class tools (KMC / Jellyfish class), from both the CLI and Python.
**Current focus:** Milestone v2.0 shipped (overall YES); planning the next milestone

## Current Position

Phase: Milestone v2.0 complete
Plan: —
Status: Awaiting next milestone
Last activity: 2026-11-14 — Milestone v2.0 completed and archived

## Performance Metrics

**Velocity (v2.0):**

- Total plans completed: 29
- Average duration: - min
- Total execution time: 0.0 hours
- v1.0 history: 31 plans / 4 phases (per-plan metrics archived in milestones/v1.0-phases/)
- Post-v1.0 hygiene wave (2026-10-21 → 2026-11-11): 10 quick tasks (memmap2 security floor, Cargo.lock + --locked CI, MSRV normalization, clippy fixes, review triage, WINDOWS #15) — records in .planning/quick/

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Foundation & Quality (v1.0) | 4/4 | - | - |
| 2. Parallel Counting (v1.0) | 5/5 | - | - |
| 3. Memory Safety (v1.0) | 17/17 | - | - |
| 4. Benchmark & Validation (v1.0) | 5/5 | - | - |
| 5. Measurement & Regression Harness | 7/7 | - | - |
| 6. Parallelism Correctness & Hot Path | 5/5 | - | - |
| 7. Shared Counting Engine | 4/4 | - | - |
| 8. Output Pipeline & .rkdb v2 Parity | 4/4 | - | - |
| 9. Python Parity | 5/5 | - | - |
| 10. Benchmark Verdict | 4/4 | - | - |
| 11. Minimizer & Memory Ceiling (conditional) | 0/TBD | - | - |
| 05 | 7 | - | - |
| 06 | 5 | - | - |
| 07 | 4 | - | - |
| 08 | 4 | - | - |
| 9 | 5 | - | - |

**Recent Trend:**

- Last 5 plans: - (v2.0 not started)
- Trend: -

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 05 P01 | 37 min | 2 tasks | 4 files |
| Phase 05 P02 | 18 min | 2 tasks | 3 files |
| Phase 05 P03 | 17 min | 2 tasks | 6 files |
| Phase 05 P04 | 45 min | 2 tasks | 5 files |
| Phase 05 P05 | 31 min | 2 tasks | 6 files |
| Phase 05 P06 | 21 min | 2 tasks | 6 files |
| Phase 05 P07 | 4 min | 2 tasks | 2 files |
| Phase 06 P01 | 31 min | 3 tasks | 7 files |
| Phase 06 P02 | 10 min | 3 tasks | 7 files |
| Phase 06 P03 | 7 | 3 tasks | 6 files |
| Phase 06 P04 | 27 min | 3 tasks | 8 files |
| Phase 06 P05 | 3 min | 2 tasks | 2 files |
| Phase 7 P01 | 8min | 3 tasks | 10 files |
| Phase 07 P02 | 13 | 3 tasks | 8 files |
| Phase 07 P03 | 6min | 2 tasks | 3 files |
| Phase 7 P04 | 23min | 3 tasks | 10 files |
| Phase 08 P01 | 27 | 3 tasks | 7 files |
| Phase 08 P02 | 8min | 2 tasks | 1 files |
| Phase 08 P03 | 6min | 3 tasks | 5 files |
| Phase 8 P04 | 19min | 2 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table (v1.0 execution decision log archived with the milestone).
Recent decisions affecting current work:

- [v2.0 scope, 2026-11-11]: k=21 counting parity first; merge untouched this round; acceptance = match or beat Jellyfish2 on both surfaces
- [v2.0 D1, ratified 2026-11-12]: parallelism-first Stage A is the spine — measured root cause is ~3.5x parallel-scaling inefficiency × ~1.4x single-thread cost, NOT data structures; `--threads` is a silent no-op; minimizer/disk-backed demoted to conditional Stage B
- [v2.0 D2, ratified 2026-11-12]: unify N-read semantics on CLI skip-N; Python output changes on N-containing reads (user-accepted, never silent — WR-04 precedent)
- [v2.0 D3, ratified 2026-11-12]: BENCH-V2-01 (KMC3 comparison) stays in v2.0; Phase 11 (MINIM-01..03) executes only if Stage A misses parity OR a memory ceiling Stage A cannot meet; otherwise descope/defer
- [v2.0 roadmap, 2026-11-12]: Phases 5-11 continue v1.0 numbering; research flags on Phases 7/10/(11 if triggered); Phases 6+7 may merge at planning, 8/9 may overlap; never run Phase 10 before 8/9; goldens captured in Phase 5 before any hot-path refactor
- [Phase 05]: [05-01] PROF-02 scaling gate reserves exit 1 for the measured RED verdict; infra failures exit 2 (__main__ guard), so an uncaught exception can never masquerade as expected-RED
- [Phase 05]: [05-01] Shared binary_provenance/validate_provenance in bench.py: actual-bytes sha256 + git HEAD + dirty + profile; SCHEMA_VERSION stays 1, validate_schema untouched (v1 baselines load)
- [Phase 05]: [05-01] Expected-RED verified twice freshness-bound: speedup_t4 1.005/0.977, speedup_t16 1.056/1.055 (<1.3), t1~t4~t16~13s on 500k synthetic reads; gate stays RED until Phase 6 PAR-01
- [Phase 05]: [05-02] Preserve locked-dependency MSRV failures as blockers; no dependency bumps, lockfile edits, --ignore-rust-version, or warning suppression
- [Quick 261112-jwl, user-approved 2026-11-12]: Raise Rust MSRV 1.80 to 1.82 for the existing locked graph; no dependency pin/update. Policy commit `69a82cf`; approved behavior-preserving clippy fix `23967d5`; all three 1.82.0 gates exited 0.
- [Phase 05]: [05-02] Random slicer uses single-pass Algorithm R with O(N) memory, source-index-sorted records, and deterministic fingerprint/seed/index/output-sha256 manifests
- [Phase 05]: [05-03] verify_threads.py hardened: exit-2 paths write no JSON and no verdict line; exceptions exit 2 without traceback; --build-profile flag keeps Rust-test debug provenance honest (dev-host capture stays release)
- [Phase 05]: [05-03] PROF-02 pool-size pair landed: characterization GREEN-now self-destructs when Phase 6 fixes --threads; standing gate ignored RED-now (observed 18/17/17 at requested 1/4/16, release sha256 8f64d442); WINDOWS skipped-test tracks the Phase-6 handoff
- [Phase 05]: [05-03] Golden capture is read-only rehash + manifest equality (12 fixtures, golden test rc 0, manifest sha256 f010e42a); generator never run, fixtures byte-identical; Phase 8 OUT-02 still needs a real write-path differential
- [Phase 05]: [05-04] Parity reference bound to the FULL random recipe (source_sha256 + seed + selection_manifest_sha256 + live-recomputed output_sha256); unbound/missing-identity/ambiguous/duplicate all exit 2; pinned head-4M constants (229694874/519271168) asserted on capture, never re-pinned; --hash-size 2G for real runs
- [Phase 05]: [05-04] Real-data gates proven on CRR1936095 part_001 (source dae91042): head-4M 229694874/519271168 + 1M random seed 20261112 73578421/129801125, both gate-proof re-runs exit 0; random distinct/instance 1.76 vs head 2.26 confirms head repeat-rich
- [Phase 05]: [05-04] Real-slice RED scaling baseline committed (t1/t4/t16 72.27/70.05/68.80s, speedup_t4 1.0318 / speedup_t16 1.0505, both <1.3) — standing Phase 6 PAR-01 target; freshness-bound capture, honest warm cache, no hot-path change
- [Phase 05]: [05-05] Microbench manifest declares rust-version 1.82 (plan literal 1.80 superseded by user-approved MSRV raise 69a82cf); standalone crate builds --locked from committed audited microbench_Cargo.lock whose measured-mechanism closure (dashmap 6.2.1/hashbrown 0.14.5/ahash 0.8.12 + padding/lock/zerocopy/libc deps) is aligned to the production lock; sha256 eabd946a recorded in evidence
- [Phase 05]: [05-05] Attribution-v1 at t16 on real 200k subslice (18M distinct): global-atomics share 120.22 ns/window = 115.2% of shared-vs-local gap; bandwidth share -15.82 ns recorded with inconclusive note (never clamped); t16/t1 multiplier 1.877 vs research 9.4x in-vivo (DRAM-regime + rayon spin-wait absent here) — Phase 7 reads atomics-dominant, bandwidth unproven at 18M distinct
- [Phase 05]: [05-05] Conservation recomputed from raw counts (flag never trusted): any failure exits 1 and the microbench aborts without JSON (mutation-proven); child exit 1 maps to controller exit 1, other child failures exit 2; negative/near-zero (<1% of gap) shares get honest inconclusive notes
- [Phase 05]: [Phase 05]: [05-06] N-free control is the committed Python comparison basis: deterministic drop-records-with-N filter of the 1M random subslice (seed 20261112), live CLI-vs-Python parity on the same bytes BEFORE timing, exact counts pinned across reps — invariant under Phase 9's D2 skip-N change; real-N arm labeled timing-only-real-N-pre-D2
- [Phase 05]: [Phase 05]: [05-06] Fresh-worker Python measurement + module provenance: every rep is a new interpreter process under /usr/bin/time (never an in-process clock); worker resolves maturin 1.11's editable-shim inner native .so so the fingerprint (c7701806) covers the measured bytes; stale/shadowed/zero-count/rep-disagreement runs exit 2, never skip
- [Phase 05]: [Phase 05]: [05-06] N-read differential recorded D2 evidence only: control exactly equal; 33 Python-only chimeric k-mers in n_at_window_end/n_at_window_start/multiple_n/lowercase_n; 0 CLI-only; --expect-unified reserved for Phase 9; neither surface's semantics changed
- [Phase 05]: [05-07] CI gains standing gates: harness unit suite + Python-surface benchmark + PROF-02 measure→upload→verdict; no Python compare gate because no CI-class baseline exists (Phase 10 owns it)
- [Phase 05]: [05-07] Evidence retention exception: all three artifact uploads use always() + if-no-files-found: warn so failed measurement steps leave evidence; measurement/gate steps stay unconditional and the job verdict is never altered
- [Phase 05]: [05-07] PROF-02 red is intentional and documented in the workflow and README with a Phase 6 (PAR-01) handoff checklist; prohibited silencing constructs named in the README (continue-on-error, || true, conditional gates, baseline recapture)
- [Phase 06]: PAR-01: all-cores fallback computed lazily via std::thread::available_parallelism; no rayon query before build_global, so --threads sizes the pool (observed 2/5/17 for 1/4/16)
- [Phase 06]: PAR-01 gates: pool-size standing gate un-ignored and characterization inverted; thread-scaling GREEN (speedup_t4 1.8118, speedup_t16 1.4372)
- [Phase 06]: PAR-01 baselines: synthetic t1 18.77 s; real 4M slice t1 142.54 s (229,694,874/519,271,168, slice sha256 71c6264b); Phase 5 RED baseline byte-identical
- [Phase 06]: verify_threads.py counts unique thread ids: macOS sample emits the main thread as both a summary header and a section header after a rebuild
- [Phase 06]: [06-02] PAR-02: per-worker LocalKmerCounts keyed by a unique counter id + generation; drain bumps the generation so a drained local can never be reused (multi-file exactness)
- [Phase 06]: [06-02] PAR-02: reduction uses checked_add per u32 key and for the shared u64 total; partial-merge atomics follow merge's WR-02 poison-consistency contract; overflow returns the verbatim message
- [Phase 06]: [06-02] Dual surface: PyO3 file methods use one local per call + one merge under py.detach; add_kmer/add_sequence stay on the shared increment path
- [Phase 06]: RollingEncoder is a Copy value with k/mask/shift precomputed; the hot loop constructs it per record rather than carrying mutable state across rayon chunks
- [Phase 06]: Rolling emission is a fallible sink (try_for_each) so LocalKmerCounts::increment errors propagate without a per-window branch; each call returns the reference skipped-window count
- [Phase 06]: canonical.rs re-exports RollingEncoder rather than duplicating it; add_sequence/add_kmer stay on their unchanged shared-increment per-window path
- [Phase 06]: Scaling regression fixed at the source: 06-02's serial per-file local reduction was parallelized (per-key DashMap shard locks keep checked sums exact) after the first post-change gate measured RED 1.197/1.253; final gate GREEN 1.633/2.016 with no threshold, input, or baseline change
- [Phase 06]: Post-hot-path true t1 strictly improved vs the 06-01 baselines: synthetic 18.77 -> 13.59 s (0.724x) and 4M slice 142.54 -> 57.16 s (0.401x); Phase 5 and both 06-01 baselines verified byte-identical
- [Phase 06]: PROF-02 gates are documented as standing: benchmark.yml and thread_scaling.py wording de-REDed; README was already standing after 06-01; no continue-on-error or fallback construct exists
- [Phase 06]: [06-05] Aggregate total_kmers is published with AtomicU64::fetch_update + checked_add (a Relaxed compare-exchange loop), not load+store; a bare fetch_add is rejected because it silently wraps past u64::MAX
- [Phase 06]: [06-05] Deterministic concurrent-reduction regression (16 threads x 2000 rounds, barrier-synchronized with all assertions outside the round loop) recorded RED lost rounds=266/2000 on the pre-fix tree and GREEN post-fix
- [Phase 06]: [06-05] Concurrent merge_local_counts is documented as supported while concurrent counting remains unsupported; per-key checked u32 merges stay parallel and .rkdb v2, public APIs, and MSRV 1.82 are untouched
- [Phase 7]: ONE for_each_window skip-N extractor (k 1..=64) is the only window loop in counting code; the engine and legacy CLI both use it, PyO3 routing is 07-03
- [Phase 7]: Partition layout P = min(256, max(64, threads)) with splitmix64 + multiply-shift routing, independent of thread count
- [Phase 7]: CountResult::merge_into reuses KmerCounter::merge_local_counts; all new u64 aggregate sums are checked with verbatim fail-loud messages
- [Phase 7]: The --threads 1 path uses a true sequential engine path (no worker threads); --threads > 1 keeps the Phase 6 legacy path until 07-02
- [Phase 07]: Engine shape (07-02): caller-thread producer + N named persistent OS workers over bounded per-worker sync_channel queues; workers own disjoint partition tables with no shared writes
- [Phase 07]: threads == 1 remains the true sequential path (0 workers, no queue); worker_count() reports 0 vs N so the t1 baseline stays honest
- [Phase 07]: Every send/recv/worker failure joins all workers first and prefers the worker-returned error, so seeded overflows surface verbatim instead of as a disconnect
- [Phase 07]: CLI counts through CountEngine at every thread count and consumes CountResult directly; the legacy per-chunk path, CountOutput, and CHUNK_SIZE are deleted
- [Phase 07]: PROF-02 asserts exact equality (2 at N=1, 2N+1 otherwise) with polling to the expected total; exit 2 is reserved for unobservable/infra outcomes and the pre-engine N+1 model is proven RED end-to-end
- [Phase 07]: [07-03] PyO3 add_sequence and process_sequence_into_local extract only through for_each_window; the non-ACGT pre-filter is retained so Python N-read output is unchanged until Phase 9 (D2)
- [Phase 07]: [07-03] N-read parity is pinned by a pure-Python strip-non-ACGT reference for k 21/64 x canonical on FASTA/FASTQ/sequence; the pre-filter and skip-N maps differ in all four cells, so the tests guard the D2 boundary
- [Phase 07]: [07-03] phase7_pyo3_evidence.json persists command lines, module path, pytest summary, one-extractor greps/call sites, manifest freeze, and the N-read parity matrix rather than bare pass booleans
- [Phase 7]: [07-04] ENGINE-02 measured on the final binary: synthetic 6.42/4.09/4.00 s vs Phase 6 13.59/8.32/6.74 s (GREEN 1.5697/1.605); slice 36.92/17.76/23.83 s vs 57.16/34.98/26.96 s with pinned 229,694,874/519,271,168 and one .rkdb sha256 across t1/t4/t16
- [Phase 7]: [07-04] Producer bounds the parallel engine (~0.9999 of t4/t16 wall; workers idle ~1.2-4.7 s busy each): parallel extraction stays the unbuilt next lever, and the slice t16>t4 gap is output sort/write variance handed to Phase 8
- [Phase 7]: [07-04] Diagnostics are profiling-only and the default release binary is byte-identical d107d17e before/after instrumentation; the pre-existing broken profiling feature was minimally repaired to build the probe
- [Phase 08]: The pre-change output-stage baseline was captured from the untouched tree (binary d107d17e, HEAD 4d53102) before any src edit; git_dirty reflects only the untracked harness files
- [Phase 08]: par_sort_unstable_by (pdqsort, in place) is mandated over the merge-sort family, whose slice-sized temporary buffer would raise peak RSS
- [Phase 08]: The pair buffer is the single sort buffer; each partition table is dropped as it drains, so post sorted RSS is 12.04 GB vs 17.97 GB pre-change
- [Phase 08]: Text output sorts by the numeric encoded key, proven equal to the decoded lexicographic order for every k in 1..=64
- [Phase 08]: Post-change compare measured GREEN on the same slice: sort delta 8.91 s -> 1.71 s (0.192x), sorted .rkdb sha256 unchanged at 0976f29c
- [Phase 08]: Four-arm .rkdb v2 differential green on all six sorted cells: new CLI (t1/t4) == committed pre-refactor fixture == frozen RKDatabase::from_kmer_pairs writer (whole-file sha256) and == hand-built 16+4 LE record bytes (data section)
- [Phase 08]: Fixture integrity is enforced in-test: manifest sha256 f010e42a pinned, all 12 fixtures re-hashed, and every write helper refuses a tests/fixtures/ path (goldens are never regenerated)
- [Phase 08]: Sortedness proven by answers: DatabaseQuery disk+preloaded binary search (500 oracle keys, 500 reverse complements, 200 absent) and extract_prefix_optimized exact contiguous block bounds on eight prefix cases; unsorted disk binary search refuses with a named error while preloaded linear search answers
- [Phase 08]: Explicit 12-cell matrix enumeration with an asserted counter; binary arm also asserts records.len()==reference.len() so duplicates/lost keys fail even when the header count matches
- [Phase 08]: Skip-N is pinned by an exact observation count on a random record with one internal N at index 45; a repeat-rich record would satisfy distinct<naive windows for the wrong reason
- [Phase 08]: Mutation driver exit classification: all gates RED then green = 0; a gate staying green = 1; non-unique find, restore mismatch, missing expected assertion text, or gate not green after restore = 2
- [Phase 08]: Output-boundary proptest drives CountEngine directly (12 in-process cases) instead of the CLI so the test stays fast while exercising the exact pair structures the writer consumes
- [Phase 8]: Post-change output-stage compare re-ran on the final tree: GREEN with sorted 10.41 s vs 18.73 s, sort delta 1.70 s (0.191x), sha256 0976f29c unchanged, sorted RSS 12.04 GB vs 17.97 GB
- [Phase 8]: Slice arms 31.82/10.15/9.31 s vs Phase 7 36.92/17.76/23.83 s at 12.04/12.04/12.05 GB RSS; all three .rkdb hash to 0976f29c, so output bytes are thread-count independent at 229M keys
- [Phase 8]: Final battery green with the writer frozen at blob eb0d5bf2 and the golden manifest at f010e42a; anti-softening current==HEAD==(workflow 0, README 2, thread_scaling.py 2), expected-failure wording zero
- [Phase 09]: Per-call `CountEngine` (no cached engine on `PyCounter`); the `threads` count is a private field because `KmerCounter::new` discards it; engine `initial_capacity = 0` so repeated calls do not re-reserve per partition
- [Phase 09]: D2 skip-N removed every Python non-ACGT pre-filter, including `add_sequence` — whitespace now breaks a window instead of joining flanks. Each rewritten pre-D2 test class carries an explicit `_strip_join_counts != _reference_counts` assertion so a mere expectation flip cannot pass
- [Phase 09]: `save_database` sorts once with `par_sort_unstable_by_key` then calls the new pure-addition `RKDatabase::from_sorted_kmer_pairs` (format.rs +78/−0) under `py.detach`; the Phase 8 whole-file blob pin `eb0d5bf2…` is superseded for that one file only, with the pure-addition proof and green golden/byte suites as the replacement evidence
- [Phase 09]: The Python benchmark verdict is identity-guarded, not positional — exactly one `*-n-free-control-t1` arm with a real `threads == 1`, and the worker's resolved rayon count is checked against the arm (read-only `PyCounterStats.threads`, preserving the 12-name frozen `PyCounter` surface). Compare mode rejects any `--threads` other than 1
- [Phase 09]: Measured on the shipped tree: 9/9 differential cells equal, 0 divergence, 33 chimeric k-mers eliminated; `speedup_t1 2.35x` / `speedup_default 8.71x` vs the committed Phase 5 sequential baseline with the N-free control exact counts preserved

### Pending Todos

None yet.

### Blockers/Concerns

- [Carried W1, OPEN] Unpushed local dev commits lack remote CI validation (memmap2 floor, Cargo.lock tracking, --locked CI, MSRV declaration, clippy fixes). Push dev to resolve.
- [Resolved 05-02] Rust 1.80.0 + clippy installed locally; remaining MSRV blocker is locked dependency compatibility, recorded below.
- [v2.0 research] Stage-A-achieves-parity is a MEDIUM-confidence extrapolation — Phase 9 measured the Python arm at 2.35x/8.71x on the slice; the full-scale verdict is Phase 10's job and still feeds the D3 trigger decision (Phase 11).
- [Phase 10, CLOSED] Overall YES at both k on both surfaces from recorded same-session t16 medians: k=21 CLI 144.69 s / Python 165.05 s vs jellyfish 194.85 / 197.95 s; k=31 CLI 147.08 s / Python 178.22 s vs 1380.92 / 187.14 s. Exact count parity; peak memory below jellyfish at both k. Verified 8/8; review disposition 0 open (27 findings across 3 rounds). The k=31 jellyfish CLI-session median is a disclosed 7.38x outlier; the verdict is robust to using the faster reference.
- [Phase 10, CLOSED] D3 answered 2026-11-14: Phase 11 (minimizer partitioning / memory ceiling) does NOT execute in v2.0. MINIM-01..03 deferred to a later milestone; no Phase 11 directory or plan exists.
- [Phase 9, OPEN] Security audit never ran for phase 9 (`SECURITY.md` absent). Phase 9 shipped under a plan-level threat model only — run `/gsd-secure-phase 9` before the milestone audit if that coverage is required.
- [Phase 9, OPEN] 8 Info-severity review findings remain in `09-REVIEW.md` (info only; the verifier confirmed none weakens a must-have). Notable: `--previous` accepts any structurally valid differential without a pre-D2 sha pin; `save_database`'s snapshot is not documented as non-linearizable.
- [Environment, OPEN] `scripts/bench/tests/test_verify_threads.py::TestNegativeControls::test_pre_engine_n_plus_one_stub_is_measured_red` is a pre-existing ~50% macOS `sample`-race flake; the file is untouched by Phases 5-9. A shared `target/` across git worktrees can also bake a deleted `CARGO_MANIFEST_DIR` into test binaries — purge artifacts containing the stale path before trusting a red result.
- [Carried] Phase-04 review findings IN-06/07/09 deferred (triage 261111-spz: 11 fixed / 4 already-fixed / 3 deferred); backlog 999.1-999.3 opportunistic only if touched by the perf work.
- [Resolved quick 261112-jwl] User approved raising MSRV to 1.82 for the unchanged locked graph; `69a82cf` carries the policy and `23967d5` the sole behavior-preserving clippy fix. Rust 1.82.0 root build/root clippy/PyO3 clippy all exited 0; WINDOWS 19/20 are fixed.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 261112-jwl | Raise Rust MSRV 1.80 to 1.82 | 2026-11-12 | 69a82cf | [261112-jwl-raise-rust-msrv-1-80-1-82-user-approved-](./quick/261112-jwl-raise-rust-msrv-1-80-1-82-user-approved-/) |

## Deferred Items

Items acknowledged and carried forward, most recent first:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Deferred items | Phase 06 `deferred-items.md`: pre-existing `cargo fmt` drift in `src/database/prefix_cache_merge.rs:1382` and `pyo3/src/counter.rs:197` (both later normalized by 06-03) | Acknowledged at v2.0 close (override closeout) | 2026-11-14 |
| Deferred items | Phase 08 `deferred-items.md`: pre-existing `cargo fmt --all --check` drift on 7 files not touched by 08-02; owner = next plan touching the CI format gate or a formatting quick task | Acknowledged at v2.0 close (override closeout) | 2026-11-14 |
| Review findings | IN-06/07/09 (Phase-04 harness/test code) | Deferred (triaged 261111-spz) | 2026-11-11 |
| Backlog | 999.1 pyo3 build.rs link args; 999.2 stale site-packages shadowing; 999.3 deferred-items stale sweep claim | Opportunistic in v2.0 if touched | 2026-10-09 |

## Session Continuity

Last session: 2026-11-14T05:00:00Z
Stopped at: Phase 10 complete — verified 8/8, overall YES; ready for milestone audit
Resume file: None

## Operator Next Steps


- Start the next milestone with /gsd-new-milestone
