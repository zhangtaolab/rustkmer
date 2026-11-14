---
phase: 07-shared-counting-engine
plan: 01
subsystem: counting-engine
tags: [rust, k-mer-counting, window-extractor, splitmix64, partitioning, exactness, rkdb]

requires:
  - phase: 06-parallelism-correctness-hot-path
    provides: LocalKmerCounts per-worker tables, checked merge_local_counts with atomic CAS publication, RollingEncoder, golden/dense gates
provides:
  - ONE skip-N for_each_window extractor (k 1..=64) shared by the engine and the legacy CLI hot loop; Phase 9 switches PyO3 onto it
  - src/count engine module tree (engine, partition) with splitmix64 routing and PartitionLayout
  - Sequential CountEngine::count_file / CountResult exact statistics at --threads 1
  - CountResult::merge_into(&KmerCounter) — the Phase 9 PyCounter bridge through the already-tested counter path
  - LocalKmerCounts::get_count (additive width-correct lookup)
affects: [07-02 worker pipeline, 07-03 PyO3 extractor routing, 07-04 engine measurement, 08 output sort, 09 Python D2/merge]

actuals:
  tokens: 30320
  tasks: 3
  commits: 3
  plan_head_before: 78e81ff
  plan_head_after: 623af47bec189cdec09e24b3a4f897f44595dc1f

tech-stack:
  added: []
  patterns:
    - "ONE extractor: every counting surface calls rustkmer::kmer::extract::for_each_window (no second encode loop)"
    - "Disjoint hash-range partition tables routed by splitmix64 + multiply-shift (no shared writes, no per-window atomics)"
    - "Checked aggregate sums with verbatim fail-loud messages at every new u64 summation site"
    - "CountOutput adapter lets the frozen text/.rkdb writers consume either the legacy counter or the engine result"

key-files:
  created:
    - src/kmer/extract.rs
    - src/count/mod.rs
    - src/count/partition.rs
    - src/count/engine.rs
    - tests/window_extract_differential_tests.rs
    - tests/count_engine_tests.rs
  modified:
    - src/kmer/mod.rs
    - src/lib.rs
    - src/hash/local.rs
    - src/cli/commands/count.rs

key-decisions:
  - "--threads 1 uses a true sequential engine path (no queues, no worker threads); --threads > 1 keeps the Phase 6 legacy path until 07-02"
  - "Partition layout P = min(256, max(64, threads)) with splitmix64 + multiply-shift routing, identical across thread counts"
  - "CountResult keeps the disjoint partition tables instead of eagerly merging; merge_into reuses KmerCounter::merge_local_counts (checked per-key u32 + atomic CAS total)"
  - "The engine path validates FASTA/FASTQ through the legacy validators before counting so empty/invalid inputs fail with the existing message"
  - "Aggregate, unique, and skipped sums use checked_add with the named verbatim messages; seeding stays test-only"

patterns-established:
  - "Tracer slice: extractor + partition routing + sequential engine + CLI cutover proven end-to-end before worker machinery"
  - "Engine warnings are returned as FileStats.skipped_batches (one per 4096-record batch with skips) and printed by the CLI with the legacy wording"
  - "Byte-identity is pinned by sha256 equality between --threads 1 (engine) and --threads 4 (legacy), not merely equal maps"

requirements-completed: [ENGINE-01, ENGINE-03]

coverage:
  - id: D1
    description: "ONE for_each_window skip-N extractor matches the per-window reference for k 1..=64, canonical on/off, lowercase, N at every position, N runs, empty/short sequences, and record boundaries"
    requirement: ENGINE-03
    verification:
      - kind: integration
        ref: "tests/window_extract_differential_tests.rs#extractor_matches_reference_for_k_1_through_64"
        status: pass
      - kind: unit
        ref: "cargo test --locked --lib kmer::extract"
        status: pass
    human_judgment: false
  - id: D2
    description: "CLI --threads 1 counts through CountEngine and produces byte-identical text maps and sorted .rkdb bytes versus the legacy --threads 4 path"
    requirement: ENGINE-01
    verification:
      - kind: e2e
        ref: "tests/count_engine_tests.rs#cli_t1_engine_matches_legacy_and_rkdb_sha256"
        status: pass
      - kind: integration
        ref: "tests/count_engine_tests.rs#sequential_engine_map_matches_reference_across_k_and_canonical"
        status: pass
    human_judgment: false
  - id: D3
    description: "CountResult exposes exact stats, filtering, per-key lookup, pair iteration, and a checked merge_into bridge with verbatim overflow messages"
    requirement: ENGINE-01
    verification:
      - kind: integration
        ref: "tests/count_engine_tests.rs#merge_into_matches_reference_counter"
        status: pass
      - kind: integration
        ref: "tests/count_engine_tests.rs#stats_and_filtering_match_counter_semantics"
        status: pass
      - kind: unit
        ref: "cargo test --locked --lib count::engine"
        status: pass
    human_judgment: false
  - id: D4
    description: "CLI boundary preserved: N-reads, multi-file cumulative stats, one warning per 4096-record batch, text/binary ordering, -L/-U filters, and --no-sort"
    requirement: ENGINE-01
    verification:
      - kind: integration
        ref: "tests/count_engine_tests.rs#n_containing_reads_match_skip_n_reference"
        status: pass
      - kind: integration
        ref: "tests/count_engine_tests.rs#multi_file_stats_and_warnings_are_preserved"
        status: pass
      - kind: integration
        ref: "tests/count_engine_tests.rs#count_filters_are_unchanged"
        status: pass
      - kind: integration
        ref: "tests/count_engine_tests.rs#text_and_binary_output_order_is_unchanged"
        status: pass
      - kind: integration
        ref: "tests/count_engine_tests.rs#no_sort_still_writes_the_same_set"
        status: pass
    human_judgment: false
  - id: D5
    description: "No new dependencies; Cargo.toml/Cargo.lock untouched; MSRV 1.82 clippy clean on both crates; thread-pool characterization still observes 2 OS threads at --threads 1"
    requirement: ENGINE-01
    verification:
      - kind: other
        ref: "cargo +1.82.0 clippy --locked --all-targets -- -D warnings (root and pyo3)"
        status: pass
      - kind: integration
        ref: "tests/thread_pool_size_tests.rs#pool_size_characterization_records_requested_pool"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-11-12
status: complete
---

# Phase 7 Plan 01: Shared Counting Engine Tracer Summary

**One skip-N extractor, splitmix64-partitioned sequential engine, and a `--threads 1` CLI cutover with exact counts and byte-identical `.rkdb` output.**

## Performance

- **Duration:** 8 min (501 s)
- **Started:** 2026-11-12T14:57:49Z
- **Completed:** 2026-11-12T15:06:10Z
- **Tasks:** 3
- **Files modified:** 10 (6 created, 4 modified)

## Accomplishments

- `src/kmer/extract.rs::for_each_window` is now the ONE window extractor: rolling encoder for k <= 32, per-window u128 reference for 33..=64, skip-N semantics, fallible sink. The differential suite covers k 1..=64, canonical on/off, lowercase, `N` at every position, `N` runs, empty/short sequences, record boundaries, and sink-error propagation.
- `src/count/{partition,engine}.rs` land the tracer architecture: splitmix64 + multiply-shift routing into `P = min(256, max(64, threads))` disjoint `LocalKmerCounts` tables, a sequential `CountEngine` with checked aggregate statistics, and `CountResult` with exact `get_count` / `for_each_count` / `filtered_pairs` / `filtering_stats`.
- `execute_count` at `--threads 1` delegates to the engine while `--threads > 1` keeps the Phase 6 legacy path; the legacy `count_record_into` also uses `for_each_window`, so no second encode loop exists in `count.rs`.
- `CountResult::merge_into(&KmerCounter)` composes the partition tables through the already-tested `merge_local_counts` (checked per-key u32, atomic CAS total) — the Phase 9 PyCounter bridge.
- Aggregate sums fail loud with the verbatim messages; direct `u64::MAX - 1 + 2` and seeded `u32::MAX + 1` tests prove no wrap/saturation.
- The frozen sorted `.rkdb` writer is unchanged: t1 engine and t4 legacy produce identical sha256 for both text and binary outputs; goldens, dense differential, thread-local, and pool-size gates stay green.

## RED -> GREEN Evidence (Task 1, tracer)

**RED (recorded before implementation):**

```
$ cargo test --locked --test window_extract_differential_tests --test count_engine_tests

error[E0432]: unresolved import `rustkmer::kmer::extract`
  --> tests/window_extract_differential_tests.rs:23:21
23 | use rustkmer::kmer::extract::{for_each_window, WindowError};
   |                     ^^^^^^^ could not find `extract` in `kmer`

error[E0432]: unresolved import `rustkmer::count`
  --> tests/count_engine_tests.rs:18:15
18 | use rustkmer::count::{CountEngine, EngineConfig, SequenceKind};
   |               ^^^^^^^ could not find `count` in `rustkmer`
```

**GREEN (after implementation):**

- `cargo test --locked --test window_extract_differential_tests` -> 9 passed, 0 failed
- `cargo test --locked --test count_engine_tests` -> 10 passed, 0 failed (2 at Task 1, 5 after Task 2, 10 after Task 3)
- `cargo test --locked --test golden_tests` -> 34 passed; `golden_sha256_tests` -> 5 passed
- `cargo test --locked --test thread_pool_size_tests` -> 2 passed (t1 still observes exactly 2 OS threads)
- `cargo test --locked --test dense_differential_tests` -> 6 passed; `thread_local_count_tests` -> 10 passed
- `cargo test --locked --lib` -> 255 passed (includes 3 new `count::engine` unit tests)
- Full suite `cargo test --locked` -> every suite green (255 lib + 26 integration binaries, 0 failed)
- `cargo build --release --locked` -> OK
- `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` -> clean on both `rustkmer` and `rustkmer-pyo3`

**Measured parity evidence (release binary, k = 21 canonical):**

| Fixture | Threads | Text sha256 | `.rkdb` sha256 | Total (sum of counts) | Unique | Max count |
|---|---|---|---|---|---|---|
| 12 reads / 1,200 bases (1 N-read, 1 lowercase read) | t1 | `a6d44b9aa80bd01c1a2f703236d376085b1da02aa71b0154638095949916c4fe` | `9cd8fd98d4a4901c91ae9cb2caa0701bb8ac2f781aa66a4b69b3e68b84c85ba8` | 939 | 939 | 1 |
| same, duplicated 3x (36 reads) | t1 | `3a0f2cabaa5499e523fc45a9668660981af1ec2f0476ee5a5d72f486b38fe480` | `404952162cb475398139a4b3e8472d25bc7facf32bef62dde6a0244df0774c48` | 2,817 | 939 | 3 |
| same | t4 | identical to t1 | identical to t1 | identical | identical | identical |

The single-run `.rkdb` is 18,822 bytes (42-byte v2 header + 939 x 20-byte records), magic `RKDB`, version 2.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end CLI at --threads 1 through the shared extractor and sequential engine** - `2544a93` (feat)
2. **Task 2: CountResult statistics exactness and the Phase 9 merge bridge** - `070a615` (test)
3. **Task 3: CLI behavior preservation at the engine/legacy boundary** - `623af47` (test)

Plan metadata: the final docs commit with this SUMMARY, STATE.md, ROADMAP.md, and REQUIREMENTS.md.

## Files Created/Modified

- `src/kmer/extract.rs` - `for_each_window`, `WindowSummary`, `WindowError`; the one skip-N extractor
- `src/kmer/mod.rs` - declares `pub mod extract`
- `src/count/mod.rs` - engine module root and re-exports
- `src/count/partition.rs` - `mix64`, `partition_of`, `PartitionLayout` + routing/ownership unit tests
- `src/count/engine.rs` - `EngineConfig`, `SequenceKind`, `EngineStats`, `FileStats`, `CountEngine`, `CountResult`, checked sums, warning batches, merge bridge
- `src/hash/local.rs` - additive `LocalKmerCounts::get_count`
- `src/cli/commands/count.rs` - `CountOutput` adapter, engine `--threads 1` path, `for_each_window` in `count_record_into`, shared file-type/kind detection
- `src/lib.rs` - declares `pub mod count`
- `tests/window_extract_differential_tests.rs` - full extractor differential matrix (9 tests)
- `tests/count_engine_tests.rs` - engine parity, exactness, merge bridge, and CLI-boundary preservation (10 tests)

## Decisions Made

- **True sequential path at `--threads 1`:** the caller thread increments directly into the partition tables, so t1 spawns no extra thread and the pool-size characterization still observes 2 OS threads. The 07-02 worker pipeline consumes the same layout.
- **Fixed partition layout:** `P = min(256, max(64, threads))` and splitmix64 + multiply-shift routing make the partition assignment independent of the thread count, so counts and sorted output compare like with like across t1/t4/t16.
- **CountResult keeps tables:** no eager merge; `merge_into` is the Phase 9 bridge and reuses `merge_local_counts` rather than duplicating the overflow contract.
- **Engine-path validation:** `detect_sequence_kind` calls the same `validate_fasta_file` / `validate_fastq_file` as the legacy path (for recognized extensions) so empty/invalid inputs keep their existing error behavior; unknown extensions keep the legacy filename-substring fallback without pre-validation.
- **Checked arithmetic everywhere new:** per-file cumulative stats, `flush`, `finish`, and warning-batch skip counts use `checked_add` with named verbatim messages.

## Deviations from Plan

### Auto-fixed Issues

None — no Rule 1-4 deviations were needed.

### Sequencing note (no behavioral change)

The private checked-sum helper landed with Task 1 because `count_file` needs it to construct `FileStats`; Task 2 added the direct helper unit tests, the seeded `merge_into` overflow test, and the integration exactness proofs exactly as specified. No scope was added or dropped.

## Issues Encountered

- Two test-code compile/runtime issues were fixed while iterating: `CountResult::into_pairs` consumes the result (stats are now captured before consumption), and the absent-key search used `1u128 << (2 * k)`, which overflows at k = 64 (capped at `u128::MAX`). Production code was unaffected.

## Known Stubs

None. No hardcoded empty values, placeholders, TODOs, skipped tests, or unrun verifications were introduced.

## Threat Flags

None beyond the plan's threat model. `for_each_window` validates k at the public boundary; every engine open/read error carries the file path; no new dependencies, no new network/auth surface, and `Cargo.toml` / `Cargo.lock` are untouched.

## Next Phase Readiness

- The extractor, partition layout, exact result surface, and merge bridge are proven; 07-02 can add the persistent producer/worker pipeline over the same `PartitionLayout` without changing counts or output.
- `for_each_window` is ready for 07-03's behavior-preserving PyO3 routing (Python keeps its N pre-filter until Phase 9).
- The `2N + 1` pool-size gate update remains for 07-02/07-04, when engine workers actually spawn; this plan deliberately kept t1 at 2 OS threads.

## Self-Check: PASSED

- Created files verified present: `src/kmer/extract.rs`, `src/count/mod.rs`, `src/count/partition.rs`, `src/count/engine.rs`, `tests/window_extract_differential_tests.rs`, `tests/count_engine_tests.rs`.
- Task commits verified as ancestors of HEAD: `2544a93`, `070a615`, `623af47`.
- `Cargo.toml` / `Cargo.lock` unchanged (10 changed files are source/test only).

---
*Phase: 07-shared-counting-engine*
*Completed: 2026-11-12*
