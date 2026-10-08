---
phase: 03-memory-safety
plan: 10
subsystem: database
tags: [rkdb, streaming-merge, pyo3, memory-bounds]

requires:
  - phase: 03-memory-safety plan 09
    provides: header-only merge routes + 96 B/k-mer admission model
provides:
  - RKDatabase::merge_databases_to_path — the path-shaped merge entry point both front-ends call; a production merge never holds the merged dataset in RAM
  - MergeSummary (pub) — the four header fields the CLI/Python report, replacing the need to materialize an RKDatabase to print them
  - A streaming writer that emits .rkdb bytes as merge_sorted_chunks yields them (placeholder-then-seek-back header, file_size stays 0)
  - An O(1) rename handoff for the prefix-cache route (cross-device falls back to a streamed copy)
  - merge_prologue + resolve_merge_route shared by both public entry points (single sweep call site; one route decision for both forms)
  - WR-05 closed — parse_memory_size cannot panic on any size string; overflow is an ordinary ValueError from Python
  - WR-02 made visible (warn + doc comment) and explicitly deferred
  - tests/merge_bounded_memory_tests.rs — the chunk-derived RSS bound and five behavioural gates
affects: [04-benchmark-validation, merge subsystem, pyo3 merge surface]

actuals:
  tokens: 20164   # chars/4 over the realized src/ pyo3/src/ tests/ diff
  tasks: 3
  commits: 3      # git rev-list --count 7554f70..HEAD at SUMMARY time (docs commit follows)
plan_head_before: 7554f705743b603bd38a1fb9de9495ac0f718d11
plan_head_after: a316e4f2aac7cbb905a98ff4c86b79a634ce5167

tech-stack:
  added: []       # no new dependencies (T-03-SC)
  patterns:
    - "path-shaped entry point + materializing compat shim — bounded core first, RKDatabase-returning form delegates to it"
    - "peak-RSS measurement via background sampler thread; bound derived from the pinned chunk size, never from N"
    - "route proven before asserted — temp_dir probe with per-route error signatures (chunk-creation vs merge-subdir-creation)"

key-files:
  created:
    - tests/merge_bounded_memory_tests.rs
  modified:
    - src/database/format.rs
    - src/cli/commands/merge.rs
    - pyo3/src/database.rs
    - src/database/stats.rs
    - .planning/phases/03-memory-safety/deferred-items.md

key-decisions:
  - "merge_prologue (WR-06 guard + the single sweep call site) is the FIRST statement of BOTH entry points — the only shape where the in-memory route sweeps and the call-site grep still reads 1; in_memory_route_still_sweeps_stale_orphans is its behavioural guard"
  - "The streaming writer's placeholder-then-seek-back header keeps file_size: 0 — every .rkdb this route has ever produced carries it; populating it would be a silent on-disk format change (T-03-37)"
  - "The prefix-cache handoff renames while the RAII merger is alive (dropping it first would delete the result with the shards); a cross-device rename falls back to a streamed copy so the pre-plan ability to merge across volumes is not regressed"
  - "WR-02 deferred, not fixed: rejecting merge_mode='memory' when the route is PrefixCache would change outcomes for every existing prefix-cache caller; the dual meaning of merge_mode under use_prefix_cache is now warned and documented instead"
  - "PyDatabase::merge semantics changed (save folded into the merge; 'Failed to save merged database to {}' is gone) with ZERO Python-level verification — recorded as the MERGE-04 residual because the installed pyrustkmer.so is a prebuilt artifact"

patterns-established:
  - "Pattern: bound derived from the pinned working set — 4 * CHUNK_ENTRIES * size_of::<KmerEntry>() — so the O(chunk) post-fix working set and the O(N) pre-fix peak land on opposite sides of the threshold (an N-relative bound cannot do that once chunk_size is pinned)"
  - "Pattern: peak-RSS sampling during the operation, not a before/after delta — an end-of-op reading measures allocator retention, not footprint (03-06's lesson, applied at merge scope)"
  - "Pattern: portable RSS source — /proc/self/status VmRSS on linux, ps -o rss elsewhere — so a memory bound executes on every dev host instead of being cfg'd into silence"

requirements-completed: [MERGE-01, MERGE-02, MERGE-04]

coverage:
  - id: D1
    description: "merge_databases_to_path exists; the streaming route writes its output entry-by-entry with no intermediate collection; the prefix-cache handoff is a rename"
    requirement: MERGE-01
    verification:
      - kind: integration
        ref: "tests/merge_bounded_memory_tests.rs#streaming_merge_peak_memory_is_bounded_by_chunk_not_dataset"
        status: pass
      - kind: integration
        ref: "tests/merge_bounded_memory_tests.rs#prefix_cache_to_path_leaves_no_intermediate_behind"
        status: pass
      - kind: grep
        ref: "grep -c 'let mut sorted_kmers: Vec<(u128, u32)> = Vec::new()' src/database/format.rs == 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "Measured RSS bound: streaming merge of 1,000,000 k-mers at pinned chunk_size=50,000 adds under 6,400,000 B; observed RED at 36,257,792 B with the accumulating body restored"
    requirement: MERGE-01
    verification:
      - kind: integration
        ref: "cargo test --test merge_bounded_memory_tests -- --test-threads=1 --nocapture (rss_delta_bytes=3440640 green / 36257792 red, rss_bound_bytes=6400000, chunk_size=50000)"
        status: pass
    human_judgment: false
  - id: D3
    description: "DENSE-02: the streaming route's emitted header is field-for-field the from_kmer_pairs header, including file_size == 0"
    requirement: MERGE-02
    verification:
      - kind: integration
        ref: "tests/merge_bounded_memory_tests.rs#streaming_to_path_header_equals_the_from_kmer_pairs_header_field_for_field"
        status: pass
    human_judgment: false
  - id: D4
    description: "merge_databases_to_path and merge_databases produce byte-identical .rkdb output on all three routes, each route proven via the temp_dir probe first"
    requirement: MERGE-02
    verification:
      - kind: integration
        ref: "tests/merge_bounded_memory_tests.rs#to_path_and_in_ram_entry_points_agree_byte_for_byte"
        status: pass
      - kind: integration
        ref: "tests/merge_bounded_memory_tests.rs#streaming_route_probe_survives_the_to_path_entry_point"
        status: pass
    human_judgment: false
  - id: D5
    description: "Both front-ends (CLI execute_merge, PyDatabase::merge) call merge_databases_to_path; no front-end materializes the merged database; every user-facing label and the 'Merge operation failed:' prefix preserved"
    requirement: MERGE-04
    verification:
      - kind: grep
        ref: "grep -c 'merge_databases_to_path' src/cli/commands/merge.rs == 1; pyo3/src/database.rs == 2; 'to_file_path(&args.output)' == 0; non-comment 'write_to_file' in pyo3 == 0"
        status: pass
      - kind: cli
        ref: "cargo test (20 binaries ok, incl. cli merge tests exercising execute_merge)"
        status: pass
      - kind: lint
        ref: "cargo clippy --all-targets -- -D warnings green on root crate and pyo3/"
        status: pass
    human_judgment: false
  - id: D6
    description: "WR-05 closed: parse_memory_size's four unit multipliers are checked_mul chains; every real overflow boundary returns the ordinary 'too large' Err instead of panicking; the over-usize parser boundary documented and asserted separately"
    requirement: MERGE-04
    verification:
      - kind: unit
        ref: "src/cli/commands/merge.rs#parse_memory_size_rejects_an_overflowing_size_without_panicking (4 boundary cases + parser-boundary case + accepted-range controls)"
        status: pass
      - kind: grep
        ref: "grep -c 'checked_mul' src/cli/commands/merge.rs == 12 (>= 4 required)"
        status: pass
    human_judgment: false
  - id: D7
    description: "MERGE-04 residual: PyDatabase::merge no longer emits 'Failed to save merged database to {}' (the save is inside the merge) and no Python-level assertion covers that semantic change"
    requirement: MERGE-04
    verification: []
    human_judgment: true
    rationale: "The installed pyrustkmer.so is a prebuilt artifact and no plan in this phase may run pytest or maturin, so the Python surface cannot be executed against the changed core — a green there would assert against code that no longer exists on disk. The Rust-side evidence is D3/D4 plus the pyo3 clippy compile gate; the residual becomes verifiable only after the pyo3/pyproject.toml python-source misconfiguration (deferred-items.md) is fixed and the extension rebuilt."

duration: 31min
completed: 2026-10-08
status: complete
---

# Phase 03 Plan 10: Streaming Merge Writes To Its Destination Summary

**A path-shaped merge entry point (`merge_databases_to_path`) whose streaming route emits `.rkdb` bytes as the merge yields them — with a chunk-derived, measurement-proven RSS bound (3,440,640 B green / 36,257,792 B red against 6,400,000 B) — plus a WR-05 overflow-proof `parse_memory_size` and both front-ends pointed at the bounded core.**

## Performance
- **Duration:** 31min / **Started:** 2026-10-08T14:25:31Z / **Completed:** 2026-10-08T14:56:31Z
- **Tasks:** 3 / **Files modified:** 6 (5 code + deferred-items.md)

## Accomplishments
- **G2b closed (CR-02's substantive half).** `merge_databases_streaming_to_path` consumes `merge_sorted_chunks()` exactly once, one `KmerEntry::write_to` per yielded `(kmer, count)`, writing a placeholder 42-byte header first and seeking back to fill in the counts (`file_size` stays 0). The `sorted_kmers: Vec<(u128, u32)>` accumulator and the `from_kmer_pairs` third copy are gone.
- **`RKDatabase::merge_databases_to_path` + `pub MergeSummary`** — the bounded entry point. Prefix-cache arm renames the external sorter's finished file onto the destination while the RAII merger is alive; in-memory arm (admission-gated) writes its one materialized copy out.
- **`merge_prologue` + `resolve_merge_route`** shared by both public entry points: exactly one `sweep_stale_merge_dirs` call site in the subsystem (`grep` reads 1), every route sweeps, and one route decision serves both forms (T-03-39). The D-02 rejection message is byte-identical; the `use_prefix_cache` arm still returns above it, now with the WR-02 warn + deferral doc.
- **`merge_databases` survives as a documented materializing shim**: InMemory keeps its body; Streaming/PrefixCache delegate to the to-path core and load once. Byte-identity between the two entry points is pinned per route.
- **CLI + PyO3 point at the bounded core.** `execute_merge` reports from `MergeSummary` with byte-identical labels ("Saving merged database to:" moved before the merge so the destination is visible first); `PyDatabase::merge` folds the save into the merge under the existing `Merge operation failed:` prefix. No new kwargs/classes.
- **WR-05 closed.** All four unit multipliers in `parse_memory_size` are `checked_mul` chains mapping overflow onto the existing `too large` Err. New unit test drives the four REAL overflow boundaries (`18446744073709551615KB`, `17592186044416MB`, `17179869184GB`, `16777216TB` — each numeric part parses as `usize` and its k-fold `* 1024` reaches `usize::MAX + 1`), the different over-`usize` parser boundary (`99999999999999999999TB` → `Invalid number`), and accepted-range controls.
- **Six-test binary `tests/merge_bounded_memory_tests.rs`** with the measurement and five behavioural gates (header equality, three-route byte identity, route probe survival, in-memory sweep, prefix-cache no-intermediate).

## Task Commits
1. **Task 1: One path-shaped entry point, and a streaming route that writes what it yields** - `d444d63` (feat, tracer — verify re-run green end-to-end before expanding)
2. **Task 2: Point both front-ends at the bounded path** - `4b9f095` (feat)
3. **Task 3: Prove the streaming route is bounded, and that the shim cannot drift from it** - `a316e4f` (test)

**Plan metadata:** `7554f70` (head before) → `a316e4f`

## The Measurement (recorded as numbers, per the plan's output spec)

| quantity | value |
|---|---|
| pinned `chunk_size` (`CHUNK_ENTRIES`) | 50,000 entries |
| `size_of::<KmerEntry>()` (asserted) | 32 B |
| `RSS_BOUND_BYTES` = 4 x 50,000 x 32 | **6,400,000 B** |
| GREEN `rss_delta_bytes` (post-fix, 1,000,000-k-mer streaming merge) | **3,440,640 B** (repeat runs 3,440,640 / 1,900,544) |
| RED `rss_delta_bytes` (accumulating body restored, then reverted) | **36,257,792 B** — 5.7x the bound |
| derived streaming-selecting budget | 95,999,999 B (estimate 96,000,000 minus 1, asserted > budget) |

The RED figure is 36.3 MB rather than the modelled ~64 MB because the peak sampler (a background thread; `ps` spawn cadence ~10-20 ms on this host) caught the fully-grown 32 MB `sorted_kmers` accumulator plus transients, landing between the doubling instants where accumulator + `from_kmer_pairs` Vec briefly coexist at ~64-80 MB. That does not weaken the claim: RED (36.3 M) and GREEN (3.4 M) sit on OPPOSITE sides of the 6.4 M bound by wide margins, which is the discriminator property the plan defines. A red run that did not state how far over it went would be indistinguishable from an unrelated OOM — hence this table.

## Files Created/Modified
- `src/database/format.rs` — `MergeSummary`, `merge_databases_to_path`, `merge_prologue`, `resolve_merge_route`, `merge_databases_streaming_to_path`, `merge_databases_prefix_cache_to_path`, `compat_materialization_target`; `merge_databases` reduced to the shim; `merge_databases_streaming`/`merge_databases_prefix_cache` (old forms) removed
- `src/cli/commands/merge.rs` — `execute_merge` on the to-path core; WR-05 `checked_mul` chains + boundary unit test
- `pyo3/src/database.rs` — `PyDatabase::merge` on the to-path core; docstring updated (output written as part of the merge)
- `src/database/stats.rs` — module-level clippy allow (toolchain drift, see deviations)
- `tests/merge_bounded_memory_tests.rs` — new 6-test binary
- `.planning/phases/03-memory-safety/deferred-items.md` — clippy drift entry

## Decisions Made
See key-decisions in the frontmatter. Additionally: the RSS measurement reads `VmRSS` from `/proc/self/status` on Linux and `ps -o rss=` elsewhere, and tracks the PEAK during the merge rather than an end delta (rationale under Deviations 2).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocker] Pre-existing clippy failure blocked the `-D warnings` gate**
- **Found during:** Task 1 verification
- **Issue:** `clippy::redundant_field_names` fires on `StatsError::Io { #[from] source: std::io::Error }` under the local clippy 1.99 — thiserror's `#[from]` expansion generates `{ source: source }` with the span mapped onto our field. Pre-existing; `stats.rs` is untouched by merge work. Field- and enum-level `#[allow]` cannot reach the generated code; a module-level inner attribute does.
- **Fix:** `#![allow(clippy::redundant_field_names)]` + explanatory comment at the top of `stats.rs`; logged to `deferred-items.md` (status: closed) per the 03-01 precedent.
- **Files modified:** `src/database/stats.rs`, `.planning/phases/03-memory-safety/deferred-items.md`
- **Verification:** `cargo clippy --all-targets -- -D warnings` green on root + pyo3.
- **Commit:** `d444d63`

**2. [Rule 3 - Blocker] The RSS measurement was made portable and peak-tracking, not /proc-only end-delta**
- **Found during:** Task 3 design
- **Issue:** The plan specifies reading `VmRSS` from `/proc/self/status` before and after the merge. (a) This host is macOS — `/proc` does not exist, so the linux-gated test would be compiled out and the plan's own acceptance criteria (output containing `rss_delta`, SUMMARY recording measured numbers, the RED demonstration) would be unmeetable. (b) An end-of-merge reading measures allocator retention, not footprint: the mutated merge's 64 MB transient is freed (and on macOS munmap'd) before the second reading, which would have made the RED demonstration impossible — exactly the masking 03-06 recorded ("an RSS delta after a drop measures allocator free-list reuse, not footprint").
- **Fix:** `current_rss_kb()` keeps `/proc/self/status` VmRSS as the `#[cfg(target_os = "linux")]` implementation and uses `ps -o rss=` (same quantity, same kB unit) elsewhere; `run_tracking_peak_rss` samples the peak from a background thread at ~2 ms while the merge runs on the calling thread. `--test-threads=1` documentation and the `VmRSS`/`target_os = "linux"` greps all still hold.
- **Files modified:** `tests/merge_bounded_memory_tests.rs`
- **Verification:** GREEN 3,440,640 B < 6,400,000 B; RED (mutation) 36,257,792 B — the mutation check is itself the proof that the measurement is not masked.
- **Commit:** `a316e4f`

**3. [Rule 2 - Missing critical functionality] Cross-device prefix-cache handoff fallback**
- **Found during:** Task 1 implementation
- **Issue:** A bare `std::fs::rename` fails with EXDEV when `--temp-dir` and the output sit on different volumes; the pre-plan code (read all + write) worked across volumes, so a rename-only handoff would have regressed a real capability.
- **Fix:** rename first; on failure, fall back to `std::fs::copy` + remove (streamed through kernel buffers — never a resident dataset) with a `log::warn!` naming both paths.
- **Files modified:** `src/database/format.rs`
- **Verification:** same-volume path exercised by `to_path_and_in_ram_entry_points_agree_byte_for_byte` and `prefix_cache_to_path_leaves_no_intermediate_behind`.
- **Commit:** `d444d63`

**4. [Rule 1 - Bug] Two clippy lints in the new test file**
- **Found during:** Task 3 verification (`bool_assert_comparison`, `cloned_ref_to_slice_refs`)
- **Fix:** `assert!(summary.sorted)`; `std::slice::from_ref(&input_path)`.
- **Commit:** `a316e4f`

**Total deviations:** 4 auto-fixed (1x Rule 1, 1x Rule 2, 2x Rule 3). **Impact:** none changed merge outcomes, route selection, or on-disk bytes; the gates that prove that (byte identity, header equality, golden sha256s) are all green.

## Issues Encountered
None beyond the deviations above. One acceptance-criterion repair during Task 3: the module docstring initially quoted the withdrawn `N * 20` formula verbatim, which trips that criterion's own grep (it must print 0); reworded to prose ("twenty bytes per k-mer, quartered").

## Authentication Gates
None — no external services or credentials involved.

## Known Stubs
None. No placeholder values, no unwired data paths, no skipped tests.

## User Setup Required
None - no external service configuration required.

## WR-02 (recorded, deferred by design)
`resolve_merge_route`'s `use_prefix_cache` arm still returns ABOVE the D-02 rejection. With `--use-prefix-cache` and `merge_mode != "auto"`, one `log::warn!` now names that `merge_mode` selects the per-bucket strategy inside `ExternalSortMerger` and the over-budget `memory` rejection is unreachable on that path. Actually rejecting `merge_mode == "memory"` when the route is `PrefixCache` is a behaviour change for every existing prefix-cache caller and needs its own decision — the arm's doc comment records the deferral.

## MERGE-04 Residual (recorded, not resolved)
`PyDatabase::merge` previously called `merge_databases` then `write_to_file`; a save failure raised `Failed to save merged database to {output}`. After this plan the save is inside the merge and that message no longer exists — every failure surfaces as `Merge operation failed: {core message}`. **No Python-level assertion covers this semantic change**, because the installed `pyrustkmer.so` is a prebuilt artifact (pytest would assert against code that no longer exists on disk) and no plan in this phase may run pytest or maturin. `pyo3/tests/` was not modified (`git status --porcelain pyo3/tests/` is empty). The Rust-side evidence is `to_path_and_in_ram_entry_points_agree_byte_for_byte` and `streaming_to_path_header_equals_the_from_kmer_pairs_header_field_for_field`, plus the pyo3 `cargo clippy --all-targets -- -D warnings` compile gate. Verification becomes possible once the `pyo3/pyproject.toml` `python-source` misconfiguration (deferred-items.md, carried in STATE.md blockers) is fixed and the extension is rebuilt.

## Verification Results (plan-level `<verification>`)
1. `cargo test` — exit 0, 20 test binaries ok, 0 failed.
2. `cargo clippy --all-targets -- -D warnings` — green on the root crate and inside `pyo3/`.
3. RSS bound — measured: 3,440,640 B < 6,400,000 B with `chunk_size` pinned to 50,000; observed RED at 36,257,792 B with the accumulating body restored (then reverted; `git status --porcelain src/` empty). `grep -c 'N \* 20' tests/merge_bounded_memory_tests.rs` prints 0.
4. `merge_databases_to_path` vs `merge_databases` byte-identical on all three routes — `to_path_and_in_ram_entry_points_agree_byte_for_byte` ok.
5. Streaming-route probe still flips outcomes — `streaming_route_probe_survives_the_to_path_entry_point` ok (asserts the chunk-creation operation AND the missing directory's name).
6. `tests/golden_sha256_tests.rs` green; `git status --porcelain tests/fixtures/` empty.
7. CLI labels byte-identical (all ten `eprintln!` lines preserved; "Saving merged database to:" relocated ahead of the merge by plan instruction); PyO3 `Merge operation failed:` prefix preserved; `Failed to save merged database to {}` removed as the plan specifies and recorded as the residual above.

## Next Phase Readiness
Phase 03 execution continues with plan 03-11 (final wave). G2a (input materialization, 03-09) and G2b (output materialization, this plan) are both closed; MERGE-01's "human-scale merges no longer OOM" now has a measured, mutation-proven bound on the streaming route. The pyo3 build/test configuration blocker (python-source + cov addopts) remains the phase's one open carry-forward and is the gate on verifying any Python-surface change made in this phase.

## Self-Check: PASSED
---
*Phase: 03-memory-safety*
*Completed: 2026-10-08*
