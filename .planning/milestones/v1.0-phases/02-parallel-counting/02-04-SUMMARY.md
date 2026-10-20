---
phase: 02-parallel-counting
plan: 04
subsystem: testing
tags: [rust, testing, golden-capture, correctness, concurrency]
requires:
  - "src/hash/table.rs (CURRENT sequential KmerCounter — the pre-refactor baseline source; untouched by this plan)"
  - "src/kmer/encoding.rs (encode_kmer_bytes_u128)"
  - "src/kmer/canonical.rs (canonical_kmer_u128)"
  - "tests/golden_generate.rs (the D-10 capture-first template this plan mirrors)"
  - "tests/round_trip_tests.rs (test-binary conventions)"
provides:
  - "tests/fixtures/parallel_count_baseline/*.json (6 committed pre-refactor count MAPS — the D-10 baseline 02-05 asserts against)"
  - "tests/parallel_count_tests.rs (differential test binary skeleton: #[ignore]d capture generator + 3 #[ignore]d differential stubs that 02-05 fills in)"
affects:
  - "02-02 (dashmap swap) — must NOT land before this plan's baselines are committed (D-10 sequencing); once it lands, the committed JSON is read-only ground truth"
  - "02-05 (differential correctness) — consumes the baselines and un-ignores/fills the three stubs"
tech-stack:
  added: []   # no new deps — serde_json + serde already root deps; available to test binaries transitively
  patterns:
    - "D-10 golden-capture-first (mirrors tests/golden_generate.rs #[ignore]d run-once generator)"
    - "BTreeMap<u128,u32> → JSON with stringified u128 keys in NUMERIC order (order-independent baseline; Pitfall 5 mitigation)"
    - "Compiling #[ignore]d differential stubs (not should_panic) — 02-05 un-ignores them"
key-files:
  created:
    - tests/parallel_count_tests.rs
    - tests/fixtures/parallel_count_baseline/k21_canon.json
    - tests/fixtures/parallel_count_baseline/k21_noncanon.json
    - tests/fixtures/parallel_count_baseline/k32_canon.json
    - tests/fixtures/parallel_count_baseline/k32_noncanon.json
    - tests/fixtures/parallel_count_baseline/k64_canon.json
    - tests/fixtures/parallel_count_baseline/k64_noncanon.json
  modified: []
decisions:
  - "Serialize baselines as BTreeMap<u128,u32> directly (serde_json stringifies u128 keys; BTreeMap gives NUMERIC not lexicographic ordering) — satisfies 'sorted numeric order' acceptance criterion and keeps the 02-05 from_str::<BTreeMap<String,u32>> deserialize contract intact"
  - "Omit 'mod common;' header from the test binary for now (none of the stubs use shared factories); in-file comment documents that 02-05 re-adds it when the differential bodies need databases_have_same_kmers. Required to keep clippy -D warnings green (FOUND-01 gate)"
  - "Use #[ignore] with reason strings (not #[should_panic]) for the differential stubs so a future --ignored run surfaces them as TODO markers rather than masking as passing tests"
metrics:
  duration: ~6min
  completed: 2026-07-01
  tasks: 1
  files: 7
status: complete
---

# Phase 02 Plan 04: Pre-refactor Count Baseline Capture (D-10) Summary

Pre-refactor sequential count MAPS captured as 6 committed JSON baselines (D-13 matrix: k in {21,32,64} x canonical {true,false}) plus a compiling differential test binary skeleton — the D-10 golden-capture-first foundation that plan 02-05's differential asserts against, captured BEFORE 02-02 swaps KmerCounter to DashMap.

## What Was Built

### `tests/fixtures/parallel_count_baseline/*.json` (6 committed baselines)

One JSON file per D-13 cell. Each is a pretty-printed JSON object mapping the stringified u128 k-mer encoding to its u32 count, with keys in **numeric** order (BTreeMap<u128,u32> serialized via serde_json, which emits integer keys as JSON strings). Counts produced by the CURRENT sequential `KmerCounter::new(k, canonical, 4096, 1)` run over a fixed deterministic 384-bp DNA input.

| File | k | canonical | Unique k-mers | Bytes |
|------|---|-----------|---------------|-------|
| k21_canon.json | 21 | true | 104 | 2113 |
| k21_noncanon.json | 21 | false | 130 | 2835 |
| k32_canon.json | 32 | true | 156 | 4116 |
| k32_noncanon.json | 32 | false | 185 | 5284 |
| k64_canon.json | 64 | true | 292 | 12645 |
| k64_noncanon.json | 64 | false | 330 | 15726 |

Determinism verified: sha256-stable across two capture runs (deterministic fixed input + BTreeMap ordering).

### `tests/parallel_count_tests.rs` (test binary skeleton)

- `//!` module doc explaining the D-10 capture-first purpose and the baseline format contract (stringified u128 keys, BTreeMap<u128,u32> source, 02-05 deserializes via `from_str::<BTreeMap<String,u32>>()`).
- `BASELINE_INPUT` — fixed deterministic 384-bp &str (same shape as `golden_generate.rs::GOLDEN_INPUT`).
- `all_cells()` — D-13 matrix generator: k in {21,32,64} x canonical {true,false} (6 cells; sorted is intentionally NOT a capture axis — the baseline is a count MAP, order-independent by construction).
- `count_input_to_map(k, canonical, input) -> ProcessingResult<BTreeMap<u128,u32>>` — the heart of the baseline. Uses the CURRENT sequential `KmerCounter` (num_threads=1) unchanged, mirroring the per-record encode/canonicalize/increment loop from `golden_generate.rs::count_input`.
- `capture_parallel_count_baseline` — `#[ignore]`d one-shot generator. Run with `cargo test --test parallel_count_tests -- --ignored capture_parallel_count_baseline`. Writes the 6 JSON files. DO NOT regenerate after 02-02 lands (T-02-04).
- Three compiling-but-`#[ignore]`d differential stubs that 02-05 fills in:
  - `differential_threads_1_vs_n` (PCOUNT-04)
  - `deterministic_sorted_output` (D-09)
  - `test_thread_resolution` (PCOUNT-01)

All stubs are `#[ignore]` with reason strings (not `#[should_panic]`) so a future `--ignored` run surfaces them as TODO markers, not as masking-as-passing tests.

## How to Run

```bash
# (Re)generate the baselines (run-once; committed, do NOT regenerate post-02-02):
cargo test --test parallel_count_tests -- --ignored capture_parallel_count_baseline

# Normal test gate (stubs pass trivially, generator + stubs all ignored):
cargo test --test parallel_count_tests

# FOUND-01 clippy gate (must stay green):
cargo clippy --all-targets -- -D warnings
```

## Verification Results

- `cargo test --test parallel_count_tests -- --ignored capture_parallel_count_baseline` — exits 0, writes 6 JSON files.
- Two capture runs produce byte-identical baselines (sha256 diff empty) — deterministic.
- `cargo test --test parallel_count_tests` (no `--ignored`) — exits 0; 4 tests ignored, 0 passed, 0 failed.
- `cargo clippy --all-targets -- -D warnings` — green on root crate.
- Full root `cargo test` — 23 integration tests + 8 doctests pass; new binary's 4 ignored stubs skip cleanly.
- Baseline JSON keys are in NUMERIC order (verified: `head -c 300 k21_canon.json` shows `0, 2, 11, 44, 177, 710, ...`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] Omitted `mod common;` header from test binary**
- **Found during:** Task 1 (clippy gate)
- **Issue:** The plan's `<action>` says to mirror `round_trip_tests.rs`'s header (`mod common; use common::*;` + the `TestResultExt` adapter). But none of the three differential stubs currently use the shared factories (`encode_test_kmer`, `databases_have_same_kmers`), and the capture generator counts a fixed &str directly. Including `mod common; use common::*;` triggers `unused_imports` warnings → fails `cargo clippy -D warnings` (FOUND-01 hard gate).
- **Fix:** Omitted `mod common;` and the `TestResultExt` trait for now. Added an in-file comment block documenting that 02-05 re-adds them when it fills in the differential bodies (which DO need `databases_have_same_kmers` for the order-independent map-equality assertion).
- **Files modified:** tests/parallel_count_tests.rs (header section)
- **Commit:** b02df33

**2. [Rule 1 - Bug] Escaped `> 1)` in doc comment to satisfy clippy::doc_lazy_continuation**
- **Found during:** Task 1 (first clippy run)
- **Issue:** A doc comment contained `> 1)` which clippy interpreted as a markdown blockquote start, firing `clippy::doc_lazy_continuation` under `-D warnings`.
- **Fix:** Escaped as `\> 1)`.
- **Files modified:** tests/parallel_count_tests.rs (BASELINE_INPUT doc comment)
- **Commit:** b02df33

### Decisions Made

**Serialize BTreeMap<u128,u32> directly (not BTreeMap<String,u32>)**
The plan's `<action>` suggests building an explicit `BTreeMap<String, u32>` with `format!("{}", kmer)` keys. I serialized the `BTreeMap<u128, u32>` directly instead. serde_json emits each u128 key as a JSON string (JSON object keys MUST be strings), and because the source is a BTreeMap, keys land in **numeric** order (`0, 2, 11, 44, ...`) — not lexicographic string order (`"0", "1035...", "11", ...`). This satisfies the acceptance criterion "keys in sorted numeric order" AND keeps the 02-05 deserialize contract (`from_str::<BTreeMap<String,u32>>()` rebuilds its own BTreeMap regardless of source ordering, so the round-trip is unaffected).

## TDD Gate Compliance

This task is `tdd="true"` in the plan frontmatter, but the test-binary scaffold nature of the work means the RED/GREEN/REFACTOR cycle does not map cleanly:

- There is no production code being added (no `src/` changes — this plan is test-fixture + test-scaffold only per `files_modified`).
- The "test" IS the artifact: the capture generator + differential stubs. The behavior under test (count determinism / 1-vs-N parity) does not exist yet — it lands in 02-02 (dashmap) and 02-05 (differential assertions).

Git log gate sequence for this plan:
1. `test(02-04): capture pre-refactor count baselines + differential stubs` (b02df33) — single commit capturing both the baselines and the test scaffold.

No separate `feat(02-04)` or `refactor(02-04)` commits because no production feature was implemented — the deliverable is the committed baseline + the compiling stub harness. The "GREEN" gate (implementation passing the test) is deferred to 02-05 by design (the stubs are `#[ignore]`d precisely because the implementation does not exist yet).

## Threat Flags

None. The only files created are committed JSON fixtures (read by the future 02-05 test from disk — they are ground truth, not untrusted input — per the plan's `<threat_model>` T-02-04/T-02-05 dispositions, both mitigated by the committed-once + deterministic-input discipline). No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries were introduced.

## Known Stubs

- `tests/parallel_count_tests.rs::differential_threads_1_vs_n` — `#[ignore]`d no-op stub. **Reason:** assertion depends on the dashmap + par_iter work landing in 02-02; this plan is the D-10 baseline capture step ONLY. **Resolves in:** plan 02-05 (Wave 3).
- `tests/parallel_count_tests.rs::deterministic_sorted_output` — `#[ignore]`d no-op stub. **Reason:** depends on D-09 default-sort wiring through `count.rs`. **Resolves in:** plan 02-05.
- `tests/parallel_count_tests.rs::test_thread_resolution` — `#[ignore]`d no-op stub. **Reason:** depends on `resolve_thread_count_from` plumbing added by plan 02-01. **Resolves in:** plan 02-05.

These stubs do NOT prevent this plan's goal (capture the pre-refactor baseline + scaffold the harness) from being achieved — they are explicitly `#[ignore]`d so the pre-refactor `cargo test` gate stays green without masking the real checks 02-05 will add.

## Self-Check: PASSED

All 7 created files verified present on disk. Task commit `b02df33` verified present in git log.
