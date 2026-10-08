---
phase: 03-memory-safety
plan: 14
subsystem: database
tags: [merge, cli, header-only, memory-safety, rkdb, clap]

requires:
  - phase: 03-memory-safety (03-09)
    provides: RKDatabase::read_header_of — the 42-byte header-only read this front-end now validates through
  - phase: 03-memory-safety (03-10)
    provides: merge_databases_to_path — the bounded core the header-only front-end now reaches without a preceding unbounded step
  - phase: 03-memory-safety (03-12)
    provides: merge_prologue cross-route validation — stays the authoritative gate; this front-end pass is CLI recovery UX only
provides:
  - pub fn rustkmer::cli::commands::merge::validate_merge_compatibility — one header-only compatibility pass per merge invocation (k always, canonical unless --use-prefix-cache)
  - tests/merge_frontend_validation_tests.rs — header-only property proven on body-absent inputs + CLI route-wiring smoke through the real binary
  - --check-compatibility mode now header-only as well (42 bytes per input, zero entry materialization)
affects: [04-benchmark-validation, pyo3 merge surface (unchanged this plan), CLI merge UX]

actuals:
  tokens: 7400        # chars/4 over the realized diff (src + tests; 29,419 chars)
  tasks: 2
  commits: 2          # MEASURED: git rev-list --count e3e2b73..HEAD
plan_head_before: e3e2b738cb20e185b7940fc208d20b175105adb7
plan_head_after: e718a97e2c0d09655e8d0b3dcd9e421fb887d427

tech-stack:
  added: []           # std + existing crate APIs only (threat T-03-SC)
  patterns:
    - "pub fn on the cli module path as the testability seam (parse_memory_size / resolve_thread_count_from precedent) — integration tests are external crates"
    - "header-only validation proven behaviorally by body-absent fixtures: truncate a well-formed .rkdb to its 42-byte header, assert the materializing loader fails on it, then assert the validation passes — the Ok cannot have loaded a body"

key-files:
  created:
    - tests/merge_frontend_validation_tests.rs
  modified:
    - src/cli/commands/merge.rs

key-decisions:
  - "validate_merge_compatibility is pub on the cli module path (not a private helper) so the header-only property is asserted from an external test crate — the parse_memory_size precedent pyo3/src/database.rs already imports"
  - "--check-compatibility validates via read_header_of + RKDatabase::new(header): the header-only RKDatabase feeds validate_compatibility_verbose UNCHANGED (it reads only kmer_size()/is_canonical()/header().total_kmers), so the enhanced validation's message text cannot drift and zero entries are materialized"
  - "Loop-1's error texts are the preserved ones; the two resulting deltas are documented in the fn doc comment: the prefix-cache k error gains the third recovery bullet, and the canonical error keeps boolean (true/false) rather than enabled/disabled formatting — loop 2's canonical arm was unreachable pre-plan (loop 1 fired first on the same predicate)"
  - "The reference-header read wraps its failure in the same 'Failed to load database '{}': {}' text as the per-input reads — input[0]'s load error previously propagated unwrapped; the wrapper only adds the failing path"

patterns-established:
  - "Body-absent fixture as a validation-cost proof: a valid 42-byte header plus a declared record count the file does not carry. Loader failure on the fixture is ASSERTED as a premise, mirroring merge_routing_tests.rs's header_only_read_agrees_with_the_materializing_loader"

requirements-completed: [MERGE-01]

coverage:
  - id: D1
    description: "CLI merge front-end compatibility validation reads 42-byte headers only — validate_merge_compatibility extracted, the materializing loader gone from merge.rs (comment-filtered count 6 -> 0)"
    requirement: MERGE-01
    verification:
      - kind: integration
        ref: "tests/merge_frontend_validation_tests.rs#frontend_validation_reads_headers_only"
        status: pass
      - kind: integration
        ref: "tests/merge_frontend_validation_tests.rs#frontend_validation_rejects_mismatches_with_recovery_text"
        status: pass
      - kind: other
        ref: "grep -vE '^\\s*//' src/cli/commands/merge.rs | grep -c from_file_path -> 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "Rejection UX contract preserved: k mismatch keeps headline + Recovery suggestions + 'rustkmer count --k' bullet; canonical mismatch keeps its headline; unreadable input keeps the Failed-to-load wrapper; --use-prefix-cache skips canonical while still checking k"
    requirement: MERGE-01
    verification:
      - kind: integration
        ref: "tests/merge_frontend_validation_tests.rs#frontend_validation_rejects_mismatches_with_recovery_text"
        status: pass
      - kind: e2e
        ref: "manual CLI run: mismatched-k merge exits 1 with all three recovery bullets on stderr, no output file written"
        status: pass
    human_judgment: false
  - id: D3
    description: "Route wiring intact: real-binary CLI merges succeed in both shapes (plain and --use-prefix-cache) with exact merged counts, through the bounded core"
    requirement: MERGE-01
    verification:
      - kind: e2e
        ref: "tests/merge_frontend_validation_tests.rs#cli_smoke_both_routes_and_mismatch_rejection"
        status: pass
      - kind: other
        ref: "cargo test (full root crate, 0 FAILED) + cargo clippy --all-targets -D warnings (root and pyo3)"
        status: pass
    human_judgment: false

duration: 11min
completed: 2026-10-08
status: complete
---

# Phase 03 Plan 14: WR-05 Header-Only CLI Merge Validation Summary

**The CLI merge front-end validates compatibility from 42-byte headers only (`validate_merge_compatibility`, one pass per input); the materializing loader call count in merge.rs went 6 → 0 with every rejection text preserved.**

## Performance

- **Duration:** ~11 min
- **Started:** 2026-10-08T17:41:14Z
- **Completed:** 2026-10-08T17:52:10Z
- **Tasks:** 2
- **Files modified:** 2 (`src/cli/commands/merge.rs`, `tests/merge_frontend_validation_tests.rs`)

## Accomplishments

- **Gap WR-05 closed (03-VERIFICATION.md gaps[3], partial → closed):** `execute_merge`'s validation block (reference full-load at :165 + two serial full-load loops at :177-234 and :241-293) collapsed into one `pub fn validate_merge_compatibility` that reads exactly one 42-byte header per input via `RKDatabase::read_header_of`. Comment-filtered count of the materializing loader call in merge.rs: **6 → 0**.
- **Header-only property proven, not inferred:** `frontend_validation_reads_headers_only` feeds two inputs truncated to their 42-byte headers (valid headers, declared counts, absent bodies), ASSERTS the materializing loader fails on them, and asserts the validation returns `Ok(())` — any body load would have errored.
- **Rejection UX contract intact:** k mismatch keeps `has k-mer size` + `Recovery suggestions` + `rustkmer count --k`; canonical mismatch keeps `canonical mode`; unreadable inputs keep the `Failed to load database` wrapper; `--use-prefix-cache` still skips canonical while still checking k.
- **Route wiring proven through the real binary:** plain and `--use-prefix-cache` CLI merges exit 0 with exact merged counts (0x1234→15, 0x5678→20, 0x9ABC→15); the mismatched-k invocation exits non-zero with the recovery text on stderr and writes no output file.
- **`--check-compatibility` also de-materialized:** that block (the 4th loader call site, covered by the plan's 0-count acceptance criterion) now reads headers via `read_header_of` and feeds `RKDatabase::new(header)` into `validate_compatibility_verbose` unchanged.

## Behavioral RED Observation (header-only property)

Sequence per the plan's red-first instruction (extract verbatim first, convert second):

1. The pre-plan validation block was extracted VERBATIM into `pub fn validate_merge_compatibility` (still full-loading); `cargo build` green — no behavior change.
2. The new test binary ran against that state:

```
test frontend_validation_reads_headers_only ... FAILED
thread panicked: header-only validation must pass on body-absent inputs whose headers
  match: Failed to read k-mer entry: failed to fill whole buffer
test frontend_validation_rejects_mismatches_with_recovery_text ... ok
test result: FAILED. 1 passed; 1 failed
```

The full loader read past EOF on the truncated bodies — direct behavioral proof the OLD path materializes inputs and that the property test can fail.

3. After the header-only conversion: `test result: ok. 2 passed; 0 failed`.

## CLI Smoke Results (recorded per plan `<output>`)

Plain route (real binary, k=31 inputs from `rustkmer count`):

```
$ rustkmer merge -i a31.rkdb b31.rkdb -o merged_plain.rkdb
Merging 2 databases...
Reading reference database header: a31.rkdb     <-- new accurate status line
Saving merged database to: merged_plain.rkdb
Merge completed successfully! ... K-mer size: 31, Total k-mers: 20
exit=0
```

`--use-prefix-cache` route: `exit=0` through the full 3-phase external-sort pipeline (bucketing → 17/256 prefix buckets → concatenation).

Mismatched-k rejection (user-visible stderr):

```
Error: Database 'c21.rkdb' has k-mer size 21, expected 31

Recovery suggestions:
  • Create a new database with k-mer size 31
  • Use 'rustkmer stats' to verify database parameters before merging
  • Use 'rustkmer count --k <size>' to create compatible databases
exit=1   (and no merged_bad.rkdb written)
```

## The Two Deliberate Message Deltas (documented in the fn doc comment)

1. On `--use-prefix-cache`, the k-mismatch error now carries the third recovery bullet (`rustkmer count --k <size>`) that loop 2's two-bullet message lacked — one more suggestion, same headline.
2. The canonical error uses loop 1's boolean formatting (`true`/`false`) rather than loop 2's `enabled`/`disabled` — loop 2's canonical arm was unreachable pre-plan (loop 1 fired first on the same predicate on the non-prefix-cache path, and the arm was skipped on the prefix-cache path), so no user-visible rejection outcome changes.

Also: input[0]'s unreadable-file error now carries the `Failed to load database '{}': {}` wrapper like every other input (previously it propagated unwrapped) — the wrapper only adds the failing path.

## Task Commits

1. **Task 1: header-only validation pass, extracted and callable** — `03d7db0` (feat)
2. **Task 2: route wiring gate — CLI smoke + full gates** — `e718a97` (test)

Tracer feedback gate (Task 1, `type="tracer"`): verify re-run end-to-end before expansion — 2 passed, loader count 0 — expanded to Task 2.

**Plan metadata:** (see final docs commit below)

## Files Created/Modified

- `src/cli/commands/merge.rs` — `pub fn validate_merge_compatibility` (header-only single pass); `execute_merge` calls it; `reference_db` full-load, both serial loops, the check-compat `from_file_path` loop, and both unit-test load-backs all removed/replaced; `--check-compatibility` header-only via `read_header_of` + `RKDatabase::new(header)`; status line reworded to `Reading reference database header:`
- `tests/merge_frontend_validation_tests.rs` — NEW binary: `truncated_header_db` helper (well-formed .rkdb truncated to 42 bytes, loader failure asserted as premise), `frontend_validation_reads_headers_only`, `frontend_validation_rejects_mismatches_with_recovery_text`, `cli_smoke_both_routes_and_mismatch_rejection` (real binary via `CARGO_BIN_EXE_rustkmer`)

## Decisions Made

See key-decisions in frontmatter. Additional execution notes:

- The unit tests inside merge.rs now verify their outputs header-only (`read_header_of`: existence, k, record count); the deep merged-COUNTS assertions moved to the integration binary's smoke (this file is bound by the zero-materializing-loader discipline the acceptance criterion enforces).
- `--use-prefix-cache` + `--verbose` status line reworded from the now-false "Skipping compatibility validation" to "Skipping canonical-mode validation (k-mer size still checked; using prefix cache merge)" — no test asserts the old string, and k IS still checked.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `--check-compatibility` printed the k-mer size as "Total k-mers"**
- **Found during:** Task 1 (restructuring that block's data source)
- **Issue:** `validate_compatibility_verbose` returns `(kmer_size, canonical)`; the block bound it as `Ok((total_kmers, _))` and printed that first element under "Total k-mers across all databases" — so any k=31 set reported "Total k-mers: 31".
- **Fix:** the real sum of the per-header record counts is accumulated while reading headers and printed.
- **Files modified:** src/cli/commands/merge.rs
- **Verification:** existing suites green (no test asserted the wrong value — which is how it survived); value now derived from the same headers the block validates.
- **Committed in:** 03d7db0

### Plan-scope notes (criteria-driven, not scope creep)

- The plan's `<action>` described only the :160-299 block, but its acceptance criterion (`grep -vE '^\s*//' src/cli/commands/merge.rs | grep -c from_file_path` == 0, "(6 today)") covers all six occurrences — including the `--check-compatibility` loop and the two in-file unit-test load-backs. All six were converted; the check-compat rewrite keeps `validate_compatibility_verbose` as the single message source (no drift), and the unit tests keep equivalent coverage header-only plus the integration binary's deep count assertions.

**Total deviations:** 1 auto-fixed (Rule 1)
**Impact on plan:** All fixes were within the file and UX surfaces the plan's own acceptance criteria govern. No scope creep; no rejections lost; no capabilities narrowed.

## Issues Encountered

- A blanket `cargo fmt` (intended for two files only — the `--` pass-through does not scope cargo fmt) briefly reformatted four out-of-scope files (`count.rs`, `parallel_count_tests.rs`, `merge_bounded_memory_tests.rs`, `merge_cleanup_tests.rs`). Reverted immediately with file-scoped `git checkout -- <files>`; subsequent formatting used `rustfmt --edition 2021 <files>` directly. Task 2's out-of-scope criterion (`git status --porcelain src/cli/commands/count.rs tests/parallel_count_tests.rs` prints nothing) verified clean at commit time.
- First smoke-test draft used repeated `-i a -i b`; `MergeArgs` declares `num_args = 2..`, so the correct shape is one `-i` with both paths (`-i a b`, the module doc's usage). Fixed; clap error reproduced and understood, not papered over.

None of these affected the committed result.

## Authentication Gates

None — no external services, no package installs (threat T-03-SC: std + existing crate APIs only).

## User Setup Required

None - no external service configuration required.

## Known Stubs

None — no placeholder data paths, no unwired outputs, no skipped tests, no unrun verifies.

## Next Phase Readiness

- Gap WR-05 closed from partial; the CLI surface performs no full input load before the bounded core, asserted behaviorally (03-VERIFICATION.md gaps[3] missing items both delivered: read_header_of comparisons with the reference load dropped, and the testable-unit extraction with a no-full-load assertion).
- Gates at close: full `cargo test` green (0 FAILED), `cargo clippy --all-targets -- -D warnings` green on root and pyo3, comment-filtered loader count 0, out-of-scope files untouched.
- The pyo3 surface was untouched by design (the plan prohibited pyo3 changes); PyDatabase.merge inherits nothing new here — the core prologue (03-12) remains its gate.

## Self-Check: PASSED

- src/cli/commands/merge.rs — FOUND
- tests/merge_frontend_validation_tests.rs — FOUND
- Task commits 03d7db0, e718a97 — FOUND (ancestors of HEAD)
- commits: 2 measured from the plan ledger (e3e2b73..e718a97), matching the 2 tasks

---
*Phase: 03-memory-safety*
*Completed: 2026-10-08*
