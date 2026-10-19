---
phase: quick-261019-dwf
plan: 01
status: complete
subsystem: io
tags: [fastq, gzip, phred, code-review-advisories, wr-15, wr-16, wr-17, in-12, in-13]

requires: []
provides:
  - "Compression-aware, error-honest FASTQ statistic helpers (total_sequence_length, average_quality, count_sequences)"
  - "filter_by_quality documented on raw Phred+33 ASCII semantics under the renamed min_quality_ascii parameter (source + docs page, identical contract)"
  - "Accurate MultiGzDecoder trailing-garbage comment with a pinned loud-failure regression test"
  - "Non-tautological GUARD premise asserts in tests/merge_bounded_memory_tests.rs"
affects: []

actuals:
  tokens: 4028   # chars/4 over the realized diff (16111 chars across 3 commits)
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "All public FASTQ helpers now route through DefaultCompressedFileReader::open_compressed with a compression-name-aware open-error context (single shared opener, no raw File::open remains in the module)"

key-files:
  created: []
  modified:
    - src/io/fastq.rs
    - docs/api-reference/rust/fastq.md
    - tests/merge_bounded_memory_tests.rs

key-decisions:
  - "WR-17 resolved via the review's NON-BREAKING option: parameter renamed min_quality_ascii, docs rewritten to raw Phred+33 ASCII-byte semantics with the threshold-55=Q20 worked example; arithmetic unchanged; the breaking Phred-decode option (Option A) is deferred to a future planned phase per the plan's <deferred> block"
  - "IN-12 fixed as comment-correction + behavior pin (not behavior change): the loud failure on trailing garbage is the already-correct current behavior; the test pins it against future flate2 semantic drift using only this module's own error context"
  - "IN-13 guards assert estimate strict positivity before deriving budget = estimated - 1 (GUARD message style kept), so an empty fixture fails loudly instead of panicking on u64 underflow"

patterns-established:
  - "Pin-test pattern for decoder semantics: assert on this module's own error-context strings, never flate2-internal wording (unstable across versions)"

requirements-completed: ["ROUND4-REVIEW-ADVISORIES"]

coverage:
  - id: D1
    description: "FASTQ statistic helpers are compression-aware and error-honest (WR-15/WR-16)"
    requirement: "ROUND4-REVIEW-ADVISORIES"
    verification:
      - kind: unit
        ref: "src/io/fastq.rs io::fastq::tests::test_total_length_and_average_quality_gzipped"
        status: pass
      - kind: unit
        ref: "src/io/fastq.rs io::fastq::tests::test_count_sequences_truncated_record_is_err"
        status: pass
  - id: D2
    description: "filter_by_quality documented on raw-ASCII semantics with renamed parameter, mirrored in docs page (WR-17)"
    requirement: "ROUND4-REVIEW-ADVISORIES"
    verification:
      - kind: unit
        ref: "src/io/fastq.rs io::fastq::tests::test_filter_by_quality_compares_raw_ascii_bytes"
        status: pass
  - id: D3
    description: "MultiGzDecoder comment accurate and trailing-garbage loud failure pinned (IN-12)"
    requirement: "ROUND4-REVIEW-ADVISORIES"
    verification:
      - kind: unit
        ref: "src/io/fastq.rs io::fastq::tests::test_read_all_errors_on_trailing_garbage_after_gzip_member"
        status: pass
  - id: D4
    description: "Bounded-memory test GUARD asserts state the positivity premise (IN-13)"
    requirement: "ROUND4-REVIEW-ADVISORIES"
    verification:
      - kind: integration
        ref: "tests/merge_bounded_memory_tests.rs (full binary, 6 tests)"
        status: pass
---

# Quick Task 261019-dwf: Address round-4 review advisories WR-15/16/17 + IN-12/13 Summary

Discharged the five open round-4 review advisories on the FASTQ I/O surface and bounded-memory tests: gz-aware statistics, honest truncation errors, raw-ASCII quality docs, an accurate MultiGzDecoder comment with a pinned loud-failure test, and non-vacuous GUARD premise asserts.

## What Was Done

### Task 1 — FASTQ helper behaviors (WR-15, WR-16, WR-17) — commit 815aad5
- **WR-15:** `total_sequence_length` and `average_quality` now open inputs through `DefaultCompressedFileReader::open_compressed` with the compression-name-aware open-error context (the same opener `process_file`, `count_sequences`, and the WR-03-fixed FASTA analogues use). A `.fastq.gz` caller now gets exact decompressed statistics instead of "stream did not contain valid UTF-8".
- **WR-16:** `count_sequences` binds each record Result and propagates failures via `ProcessingError::with_context("Error reading FASTQ record from file: {path:?}")` — matching the error contract of `process_file`/`validate_fastq_file`. A truncated final record now yields Err naming the file, never Ok with the broken record tallied.
- **WR-17 (non-breaking option):** `filter_by_quality` parameter renamed `min_quality_ascii`; doc rewritten to raw Phred+33 ASCII-byte semantics with the worked example (threshold 55 = Q20) and an explicit warning that a decoded Phred score would silently keep every record. `average_quality`'s # Returns labeled "mean of the raw Phred+33 ASCII quality bytes". Arithmetic of both functions unchanged. `docs/api-reference/rust/fastq.md` `filter_by_quality` entry mirrors the identical contract.
- **Tests (TDD):** RED confirmed for the gz statistics test (failed on the raw-deflate parse) and the truncated-record test (failed with Ok(2)); GREEN after the fixes. The WR-17 test is a semantics pin and passes on both sides by design (the fix is doc-only).

### Task 2 — MultiGzDecoder comment + trailing-garbage pin (IN-12) — commit 957c069
- The "byte-identical on single-member files" overclaim was replaced with the accurate statement: output matches the single-member decoder only when nothing follows the final member; trailing non-gzip bytes (padded writes, appended text, a torn second member) surface as a mid-stream io error instead of silent truncation — loud failure is deliberate.
- New pin test `test_read_all_errors_on_trailing_garbage_after_gzip_member`: one valid member + literal junk through the CLI's own `process_file -> open_compressed` path must Err containing this module's record-reading context. No flate2-internal wording is pinned (unstable across versions). Pin test passes on the current flate2 1.1.x — that is its purpose.

### Task 3 — GUARD premise asserts (IN-13) — commit b417e3a
- Both tautological `estimated > budget` asserts (RSS-measurement test and `streaming_route_probe_survives_the_to_path_entry_point`) replaced with a strict-positivity premise assert (`estimated > 0`, GUARD message style kept), after which `budget = estimated - 1` is derived safely. An empty fixture now fails the guard loudly instead of panicking on u64 underflow or passing vacuously. MergeConfig construction, temp-dir probes, and all other assertions untouched.

## Deviations from Plan

None material. One transparency note: Task 3 also updated the second test's doc comment (which still described the removed "asserted to sit below the estimate" tautology) to describe the positivity guard — a comment, not an assertion or surrounding code, staying within the task's intent.

## Deferred (surfaced, not implemented — per plan)

**WR-17 Option A — Phred-decoding semantics:** decoding quality bytes before comparison (guarding the +33 offset) and subtracting the offset in `average_quality`'s accumulator would make the code match the previously documented Phred contract, but it is a public-API semantic change for every external consumer of `rustkmer::io::fastq`. The non-breaking doc/code alignment shipped here fully removes the misleading-contract hazard (repo-wide grep confirmed zero in-repo callers outside the module's own tests). Flipping to Phred-native semantics (or adding `average_phred_score` / `filter_by_phred` variants) should be a deliberate API decision in a future planned phase.

## Verification

From the repo root, all gates run and passing:

| Gate | Result |
|------|--------|
| `cargo test --lib io::fastq` | 13 passed, 0 failed (4 new tests included) |
| `cargo test --test merge_bounded_memory_tests` | 6 passed, 0 failed |
| `cargo test` (full suite, CI's command) | exit 0 — all 23 test binaries green |
| `cargo clippy --all-targets -- -D warnings` | exit 0, no warnings |
| `grep -c 'for _ in' src/io/fastq.rs` | 0 |
| `grep -c '0-40' src/io/fastq.rs` / `docs/api-reference/rust/fastq.md` | 0 / 0 |
| `grep -c 'min_quality_ascii' src/io/fastq.rs` | 3 (doc + signature + body) |
| `grep -c 'byte-identical' src/io/fastq.rs` | 0 |
| `grep -c 'estimated > budget' tests/merge_bounded_memory_tests.rs` | 0 |

## Auth Gates

None encountered.

## Known Stubs

None — no placeholder logic, no unwired data, no skipped tests were introduced.

## Threat Flags

None — all four registered threats (T-dwf-01..T-dwf-04) were mitigated exactly as the plan's threat model specified; no security-relevant surface beyond that model was introduced.

## Self-Check: PASSED

- Files exist: src/io/fastq.rs, docs/api-reference/rust/fastq.md, tests/merge_bounded_memory_tests.rs — all present and modified.
- Commits 815aad5, 957c069, b417e3a — all verified as ancestors of HEAD.
- All plan-level gates re-run after the final commit: cargo test exit 0, clippy exit 0, all grep truths hold.
