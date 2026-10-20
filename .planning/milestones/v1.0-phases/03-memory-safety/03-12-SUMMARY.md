---
phase: 03-memory-safety
plan: 12
subsystem: database
tags: [rust, rkdb, merge, validation, header-validation, memory-safety]

requires:
  - phase: 03-memory-safety (03-01)
    provides: read_header_of + estimate_total_kmers (42-byte header-only machinery)
  - phase: 03-memory-safety (03-09)
    provides: the admission model (estimated_bytes_for_route, INMEMORY_BYTES_PER_KMER = 96)
  - phase: 03-memory-safety (03-10)
    provides: merge_prologue as the shared first statement of both public merge entry points
provides:
  - Cross-input k-mer-size + canonical-mode validation in merge_prologue, inherited by ALL three routes (in-memory, streaming, prefix-cache) from both public entry points and both shipped front-ends (CLI execute_merge, PyDatabase.merge)
  - Four regression tests: two observed-RED streaming rejection proofs (k mismatch, mixed canonical), the prefix-cache mixed-canonical capability guard, and the in-memory rejection parity pin
affects: [03-memory-safety (03-13..03-15 gap-closure round), phase-04-benchmark]

actuals:
  tokens: 5700   # chars/4 over the realized diff (format.rs + merge_routing_tests.rs + deferred-items.md); plan estimate was 55000 at confidence low
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Shared-prologue validation: one header-only compatibility gate as the first statement of both public entry points, so every route and front-end inherits one implementation instead of per-route checks"

key-files:
  created: []
  modified:
    - src/database/format.rs
    - tests/merge_routing_tests.rs
    - .planning/phases/03-memory-safety/deferred-items.md

key-decisions:
  - "The canonical check is a SEPARATE prologue loop gated on !config.use_prefix_cache, not inside validate_header_compatibility — that fn's contract is the prefix-cache route's convert-to-canonical semantics (it deliberately allows mixed canonical and returns final_canonical); overloading it would revoke the prefix-cache route's advertised mixed-canonical capability, which belongs to WR-04's developer triage"
  - "The k-mer-size check reuses validate_header_compatibility verbatim, so the k-mismatch message cannot drift from the text prefix_cache_kmer_size_mismatch_keeps_its_error_text pins byte-for-byte; the route-level call sites stay as deliberate defense-in-depth"
  - "PyDatabase.merge closes MERGE-04 by inheritance (pyo3/src/database.rs:1457 calls merge_databases_to_path -> merge_prologue) with ZERO pyo3 edits — git diff over pyo3 source is empty and the pyo3 crate compiles clean under -D warnings; the PyRuntimeError manifestation is verified by call-graph inspection, not pytest (maturin python-source blocker, STATE.md)"
  - "RED evidence was captured for BOTH streaming rejection axes, not just the mandated one: the k-mismatch test pre-fix (Task 1, before touching src/) and the mixed-canonical test against a temporarily restored pre-fix format.rs (post-Task-2, restored immediately)"

patterns-established:
  - "Rejection proofs must be header-only by construction: the streaming tests assert the compatibility message text and the ABSENCE of temp-dir/IO error markers, and derive their budgets from estimate_total_kmers with the over-budget premise asserted first (03-04/03-05 discipline)"
  - "A capability guard accompanies every conditional rejection: prefix_cache_route_still_merges_mixed_canonical pins the exact pair the prologue refuses, proving the !use_prefix_cache gate is load-bearing"

requirements-completed: [MERGE-01, MERGE-04]

coverage:
  - id: D1
    description: "Streaming route rejects cross-input k-mer-size mismatch (over-budget auto arm, explicit streaming arm, same-k premise arm) — CR-03 primary axis"
    requirement: MERGE-01
    verification:
      - kind: integration
        ref: tests/merge_routing_tests.rs#streaming_route_rejects_cross_input_kmer_size_mismatch
        status: pass
    human_judgment: false
  - id: D2
    description: "Streaming route rejects mixed canonical modes without prefix cache, and the prefix-cache route still merges the same mixed-canonical pair (capability preserved)"
    requirement: MERGE-01
    verification:
      - kind: integration
        ref: tests/merge_routing_tests.rs#streaming_route_rejects_mixed_canonical_without_prefix_cache
        status: pass
      - kind: integration
        ref: tests/merge_routing_tests.rs#prefix_cache_route_still_merges_mixed_canonical
        status: pass
    human_judgment: false
  - id: D3
    description: "In-memory route rejection parity (same Err, same message shape, now from the prologue) and pinned k-mismatch message text unchanged byte-for-byte"
    requirement: MERGE-01
    verification:
      - kind: integration
        ref: tests/merge_routing_tests.rs#inmemory_route_still_rejects_mismatched_inputs
        status: pass
      - kind: integration
        ref: tests/merge_routing_tests.rs#prefix_cache_kmer_size_mismatch_keeps_its_error_text
        status: pass
    human_judgment: false
  - id: D4
    description: "PyDatabase.merge inherits the rejection with zero pyo3 edits (MERGE-04 closure by inheritance)"
    requirement: MERGE-04
    verification:
      - kind: other
        ref: "git diff --stat over pyo3 source (empty) + cargo clippy --all-targets -D warnings in pyo3/ (exit 0)"
        status: pass
    human_judgment: true
    rationale: "The PyRuntimeError manifestation cannot be asserted by pytest this phase: pyo3/pyproject.toml's maturin python-source pairing blocks every build/develop and the --cov-fail-under addopts makes every pytest run exit 1 (STATE.md blocker, WINDOWS.md entries 4/5/11). Verified by call-graph inspection instead: pyo3/src/database.rs:1457 calls the same merge_databases_to_path entry point whose prologue now rejects, and the pyo3 crate compiles clean against the unchanged public surface. A human confirms the Python-surface behavior once the blocker is lifted."

duration: 12min
completed: 2026-10-08
status: complete
---

# Phase 03 Plan 12: CR-03 — Cross-Input Validation on the Streaming Merge Route Summary

**Header-only cross-input k-mer-size/canonical validation in `merge_prologue`: every merge route and both front-ends (CLI + PyDatabase.merge) now reject an incompatible input set from 42-byte header reads before any merge work or output byte.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-10-08T16:56:46Z
- **Completed:** 2026-10-08T17:08:35Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- **CR-03 closed** (03-VERIFICATION.md gaps[0]): `merge_prologue` (src/database/format.rs) now collects every input's header via `read_header_of` (42 bytes per input — the D-01 rule), runs `validate_header_compatibility` for the k-mer-size check, and applies a `!use_prefix_cache`-gated canonical-mismatch loop. Because the prologue is the shared first statement of BOTH public entry points, all three routes (in-memory, streaming, prefix-cache) and both front-ends inherit one implementation. Pre-fix, the streaming route — the default over-budget route, reachable directly from `PyDatabase.merge` — validated nothing and silently wrote a corrupt database.
- **MERGE-04 closed by inheritance**: `PyDatabase.merge` (pyo3/src/database.rs:1457) calls `merge_databases_to_path`, whose first statement is the prologue — the Python surface now surfaces the rejection as `PyRuntimeError` with the core message, with zero pyo3 edits (`git diff` over pyo3 source is empty; pyo3 clippy `-D warnings` green).
- **Message stability proven**: `prefix_cache_kmer_size_mismatch_keeps_its_error_text` (tests/merge_routing_tests.rs) is green byte-for-byte — the prologue reuses the same `validate_header_compatibility` fn that produced the text, so the message simply surfaces earlier.
- **Capability preserved**: mixed-canonical inputs still merge under `use_prefix_cache: true` (pinned by `prefix_cache_route_still_merges_mixed_canonical`, which also asserts the output header claims input[0]'s canonical mode) — the `!config.use_prefix_cache` gate is load-bearing.
- **Gates green**: full root-crate suite 425 passed / 0 failed (merge_routing_tests 37 = 33 existing + 4 new); clippy `-D warnings` green on root AND pyo3; `in_memory_route_still_sweeps_stale_orphans` still green (sweep/empty-guard invariants untouched — the validation sits between the guard and the sweep, exactly as planned).

## RED Evidence (the pre-fix gap, observed)

Per this phase's red-evidence culture (03-06/03-08 precedents), both streaming rejection tests were observed failing against the pre-fix tree:

**1. k-mer-size axis** — `streaming_route_rejects_cross_input_kmer_size_mismatch`, added BEFORE any src/ edit and run against the unmodified tree:

```
thread 'streaming_route_rejects_cross_input_kmer_size_mismatch' panicked at tests/merge_routing_tests.rs:1163:10:
a k-mer-size mismatch must be rejected on the streaming route: MergeSummary { kmer_size: 21, total_kmers: 4, canonical: true, sorted: true }
test result: FAILED. 0 passed; 1 failed
```

The merge returned `Ok` and wrote a corrupt database whose header claims k=21 (input[0]'s size) over a k=21 + k=31 input set — exactly the gap CR-03 describes.

**2. canonical axis** — `streaming_route_rejects_mixed_canonical_without_prefix_cache`, run against the pre-fix `format.rs` restored from commit 68f246e via a targeted single-file `git checkout` (restored to HEAD immediately after):

```
thread 'streaming_route_rejects_mixed_canonical_without_prefix_cache' panicked at tests/merge_routing_tests.rs:1250:10:
mixed canonical modes must be rejected on the streaming route: MergeSummary { kmer_size: 21, total_kmers: 4, canonical: true, sorted: true }
test result: FAILED. 0 passed; 1 failed
```

The merge returned `Ok` claiming `canonical: true` (input[0]'s mode) over a canonical=true + canonical=false input set.

Both tests pass after the fix; the same-k premise arm merges `Ok` under the identical over-budget config, proving the rejections are attributable to the mismatches, not the budgets.

## The Inheritance Argument for PyDatabase.merge (MERGE-04)

`PyDatabase::merge` (pyo3/src/database.rs:1457) validates file existence, the `merge_mode` enum, and `max_memory` parsing at the boundary, then calls `RKDatabase::merge_databases_to_path` — whose FIRST statement is now `merge_prologue`, which performs the cross-input validation. An incompatible set therefore terminates in `Err` inside the core before any route runs, and pyo3's `?`-propagation converts `ProcessingError` into `PyRuntimeError` carrying the same message — no pyo3 code change required, and none made (`git diff` over pyo3 source is empty; the `pyo3/.coverage` binary artifact was already modified at spawn time and was neither touched nor staged by this plan).

**Why this is not pytest-verified:** the pyo3 test runner remains blocked — `pyo3/pyproject.toml` sets `python-source="."` with `module-name="pyrustkmer"` while `pyo3/pyrustkmer/` has never existed, so maturin build/develop both refuse, and the `--cov-fail-under=80` addopts makes every pytest run exit 1 (STATE.md blocker; WINDOWS.md entries 4/5/11). Recorded as an unrun-verify instance in WINDOWS.md for this plan's Python-surface claim.

## Task Commits

Each task was committed atomically:

1. **Task 1: Header-only cross-input validation in merge_prologue** - `6c2fa52` (feat)
2. **Task 2: Gates — clippy, adjacent merge suites, sweep/empty-guard invariants** - `a35b916` (test)

**Plan metadata:** committed after this SUMMARY (docs)

## Files Created/Modified

- `src/database/format.rs` - `merge_prologue` gains the header collection + `validate_header_compatibility` call + conditional canonical loop, with doc-comment coverage of why the check spans all routes and why the canonical arm is prefix-cache-exempt; doc comment's "and nothing else" claim corrected
- `tests/merge_routing_tests.rs` - four new tests: `streaming_route_rejects_cross_input_kmer_size_mismatch` (3 arms), `streaming_route_rejects_mixed_canonical_without_prefix_cache`, `prefix_cache_route_still_merges_mixed_canonical`, `inmemory_route_still_rejects_mismatched_inputs`
- `.planning/phases/03-memory-safety/deferred-items.md` - out-of-scope discovery logged (pre-existing flaky config test, see Issues Encountered)

## Decisions Made

See key-decisions in the frontmatter. Additional execution note: rustfmt was applied ONLY to the two plan files (Task 2 action 4, per plan); this also normalized pre-existing rustfmt drift inside `format.rs`'s 03-09/03-10 regions (layout-only hunks), while the known drift in `src/cli/commands/count.rs` and `tests/parallel_count_tests.rs` was confirmed untouched (`git status --porcelain` on both prints nothing).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

One full-suite `cargo test` invocation failed on `config::manager::tests::test_config_file_operations` (`left: Some(21), right: Some(25)`). Diagnosis: a pre-existing parallel-execution env-var race in `src/config/manager.rs` — `test_env_overrides` sets `RUSTKMER_DEFAULT_K=21` while `test_config_file_operations` concurrently loads a temp file with `default_k = 25`, and env beats file. Unrelated to this plan (the config module is untouched; only `format.rs` and `merge_routing_tests.rs` changed). 20+ subsequent runs — filtered, paired at `--test-threads 2`, and full-suite — were all green; the Task 2 gate run passed with 425/0. Logged to `deferred-items.md` with a suggested fix rather than repaired (scope boundary: pre-existing, unrelated).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Gap CR-03 is closed; 03-13 (CR-01 bucket-merge record loss), 03-14 (WR-05 CLI materialization), and 03-15 (CR-02/G3 prefix-cache ordering) remain in the gap-closure round.
- MERGE-01 stays shared-open until 03-13/03-14/03-15 produce SUMMARYs (shared-ID gate); MERGE-04 is marked complete by this plan.
- The pyo3 pytest blocker still stands for every Python-surface claim in this phase (WINDOWS.md entries 4/5/11 + this plan's instance).

## Self-Check: PASSED

- Files exist on disk: `src/database/format.rs`, `tests/merge_routing_tests.rs`, `03-12-SUMMARY.md`
- Commits are ancestors of HEAD: `6c2fa52` (Task 1), `a35b916` (Task 2)
- `gsd-tools check evaluation-scope --plan 03-12 --commits-only` resolved (status `resolved`, exit 0)
- All plan `<verification>` commands re-run green: merge_routing_tests 37/0, full root-crate suite 425/0, root + pyo3 clippy `-D warnings` exit 0, pyo3 source diff empty

---
*Phase: 03-memory-safety*
*Completed: 2026-10-08*
