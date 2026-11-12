---
phase: 07-shared-counting-engine
plan: 03
subsystem: python-bindings
tags: [rust, pyo3, k-mer-counting, window-extractor, pre-filter, d2, msrv, evidence]

requires:
  - phase: 07-shared-counting-engine
    provides: "for_each_window extractor (07-01), persistent engine + CLI cutover (07-02)"
  - phase: 06-parallelism-correctness-hot-path
    provides: "LocalKmerCounts file-local accumulation and checked merge"
provides:
  - "PyO3 add_sequence and process_sequence_into_local extract windows only through the ONE core for_each_window"
  - "Python's pre-D2 non-ACGT pre-filter retained verbatim, pinned by N-read parity tests for k 21/64 x canonical on FASTA/FASTQ/add_sequence"
  - "phase7_pyo3_evidence.json: MSRV 1.82 clippy, full locked suite, module path, pytest summary, one-extractor greps/call sites, manifest freeze, N-read parity matrix"
affects: [09 Python D2/merge, 08 output sort, 11 spill]

actuals:
  tokens: 4571
  tasks: 2
  commits: 2
  plan_head_before: 24f354e981d571ffc268e12f922804437abafb2b
  plan_head_after: 5d431d5e61f0a59e4ed121fcf67438bffe8a4fb5

tech-stack:
  added: []
  patterns:
    - "PyO3 file and sequence paths call the same core extractor as the CLI; the Python pre-filter remains the Phase 9 switch point"
    - "Evidence JSON carries command lines, outputs, and measured matrices rather than bare pass booleans"

key-files:
  created:
    - .planning/phases/07-shared-counting-engine/phase7_pyo3_evidence.json
  modified:
    - pyo3/src/counter.rs
    - pyo3/tests/test_counter.py

key-decisions:
  - "Retain the non-ACGT pre-filter on add_sequence and both file helpers: it is the current Python contract, so D2's skip-N change stays owned by Phase 9"
  - "Map WindowError::InvalidK to the existing invalid-k PyValueError/InvalidKmerSize messages even though it is unreachable after construction validation"
  - "Propagate the extractor's skipped count into LocalKmerCounts::record_skipped so no future caller can silently drop skip accounting"
  - "Enrich the plan's evidence schema with the manifest diff output, call-site matches, and a pre-filter-vs-skip-N comparison while keeping every required field"

requirements-completed: [ENGINE-03]

coverage:
  - id: D1
    description: "Every PyO3 window extraction path calls the ONE core for_each_window; no rolling-encoder symbol or indexed per-window loop remains in pyo3/src/counter.rs"
    requirement: ENGINE-03
    verification:
      - kind: other
        ref: "grep -n 'RollingEncoder::|for i in 0..=(' pyo3/src/counter.rs (no match); grep -n 'for_each_window(' src/count/engine.rs src/cli/commands/count.rs pyo3/src/counter.rs -> engine.rs:815,832 + counter.rs:309,677"
        status: pass
      - kind: integration
        ref: "pyo3/tests/test_counter.py::TestPyCounterLocalAccumulationParity + TestPyCounterRollingPathParity (existing file/sequence parity, k 21/32/64 x canonical)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Python output on N-containing reads is unchanged: the pre-filter joins flanks and the new parity cases fail under CLI skip-N semantics"
    requirement: ENGINE-03
    verification:
      - kind: integration
        ref: "pyo3/tests/test_counter.py::TestPyCounterNReadPreFilterParity::test_add_from_fastq_n_reads_keep_pre_filter_semantics (4 parametrizations)"
        status: pass
      - kind: integration
        ref: "pyo3/tests/test_counter.py::TestPyCounterNReadPreFilterParity::test_add_from_fasta_n_reads_keep_pre_filter_semantics (4 parametrizations)"
        status: pass
      - kind: integration
        ref: "pyo3/tests/test_counter.py::TestPyCounterNReadPreFilterParity::test_add_sequence_internal_n_keeps_pre_filter_semantics (4 parametrizations)"
        status: pass
      - kind: other
        ref: "pre-filter vs skip-N maps differ in all four k/canonical cells (304/28 vs 244/8; 304/24 vs 244/4; 89/41 vs 34/4; 89/40 vs 34/3) — recorded in phase7_pyo3_evidence.json"
        status: pass
    human_judgment: false
  - id: D3
    description: "Dual-surface gates proven with persisted evidence: MSRV 1.82 clippy on both crates, locked release build, full locked test suite, bench harness suite, rebuilt module path, and manifest/lockfile freeze"
    requirement: ENGINE-03
    verification:
      - kind: other
        ref: "cargo +1.82.0 clippy --locked --all-targets -- -D warnings (root and --manifest-path pyo3/Cargo.toml)"
        status: pass
      - kind: other
        ref: "cargo build --release --locked && cargo test --locked (0 failed)"
        status: pass
      - kind: other
        ref: "python3 -m unittest discover -s scripts/bench/tests -t . (Ran 316 tests; OK, skipped=1)"
        status: pass
      - kind: integration
        ref: "maturin develop --release -> /Users/forrest/GitHub/rustkmer/.venv311/lib/python3.11/site-packages/pyrustkmer/__init__.py; pytest pyo3/tests: 158 passed, 63 skipped"
        status: pass
      - kind: other
        ref: "git diff --stat -- Cargo.toml pyo3/Cargo.toml Cargo.lock pyo3/Cargo.lock (empty)"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-11-12
status: complete
---

# Phase 7 Plan 03: PyO3 Extractor Routing Summary

**PyCounter's file and sequence paths now extract windows only through the shared `for_each_window` extractor while keeping Python's strip-N pre-filter byte-for-byte, with the one-extractor, MSRV, and dependency-freeze gates persisted as evidence.**

## Performance

- **Duration:** 6 min (354 s)
- **Started:** 2026-11-12T15:23:30Z
- **Completed:** 2026-11-12T15:29:24Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- `pyo3/src/counter.rs` no longer owns a window loop. `add_sequence` builds its cleaned byte buffer and calls `for_each_window`; `process_sequence_into_local` (the file-path per-sequence helper) does the same and forwards the extractor's `skipped` count into `LocalKmerCounts::record_skipped`. The rolling-encoder branch, the k 33..=64 per-window u128 loop, and both `for i in 0..=(` loops are gone.
- Python semantics are demonstrably unchanged for N-containing input. The existing non-ACGT pre-filter remains on `add_sequence` and both file helpers, so the extractor only ever sees ACGT; a fuzzable pure-Python reference (strip non-ACGT, join flanks, slide) matches the extension for k 21/64 x canonical on FASTA, FASTQ, and sequence paths. A standalone measurement shows the pre-filter and CLI skip-N maps diverge in all four cells, so the new tests are genuine D2-leak guards (they would fail if the cutover adopted skip-N early).
- The public `PyCounter` surface, `py.detach` + owned `Send` captures, and the file-local accumulation/reduction pattern are untouched. `add_kmer` and `get_count` keep their single-kmer encode path.
- The dual-surface gate battery is green and persisted: MSRV 1.82 clippy on both crates with `-D warnings`, locked release build, the full locked Rust suite (0 failures), the 316-test bench harness suite, a rebuilt/version-asserted `pyrustkmer`, and empty manifest/lockfile diffs.

## Measured Evidence

**PyO3 pytest (rebuilt extension):**

```
======================= 158 passed, 63 skipped in 0.12s ========================
```

Baseline before this plan was 146 passed / 63 skipped; the 12 new N-read parity cases (3 paths x k {21,64} x canonical {off,on}) account for the delta. Module path recorded: `/Users/forrest/GitHub/rustkmer/.venv311/lib/python3.11/site-packages/pyrustkmer/__init__.py`.

**One-extractor proof:**

```
grep -n "RollingEncoder::" src/cli/commands/count.rs src/count/engine.rs pyo3/src/counter.rs   -> no match
grep -n "for i in 0..=("     src/cli/commands/count.rs src/count/engine.rs pyo3/src/counter.rs   -> no match
grep -n "for_each_window("   src/count/engine.rs src/cli/commands/count.rs pyo3/src/counter.rs
  src/count/engine.rs:815        (sequential engine path)
  src/count/engine.rs:832        (parallel engine path)
  pyo3/src/counter.rs:309        (add_sequence)
  pyo3/src/counter.rs:677        (process_sequence_into_local)
```

`src/cli/commands/count.rs` has no direct extractor call because it delegates entirely to the engine (07-02 cutover).

**N-read parity (pre-filter vs CLI skip-N, same fixture):**

| k | canonical | pre-filter total/unique | skip-N total/unique | maps distinct |
|---|---|---|---|---|
| 21 | off | 304 / 28 | 244 / 8 | yes |
| 21 | on | 304 / 24 | 244 / 4 | yes |
| 64 | off | 89 / 41 | 34 / 4 | yes |
| 64 | on | 89 / 40 | 34 / 3 | yes |

**Other gates:** `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` clean on both crates; `cargo build --release --locked` OK; `cargo test --locked` exit 0 with 0 failures; `python3 -m unittest discover -s scripts/bench/tests -t .` → Ran 316 tests, OK (skipped=1); `git diff --stat -- Cargo.toml pyo3/Cargo.toml Cargo.lock pyo3/Cargo.lock` empty.

## Task Commits

Each task was committed atomically:

1. **Task 1: Route PyO3 window extraction through the ONE core extractor (behavior-preserving)** - `2230ae8` (feat)
2. **Task 2: MSRV, full-suite, manifest freeze, and one-extractor evidence** - `5d431d5` (docs)

Plan metadata: the final docs commit with this SUMMARY, STATE.md, ROADMAP.md, and REQUIREMENTS.md.

## Files Created/Modified

- `pyo3/src/counter.rs` - `for_each_window` routing in `add_sequence` and `process_sequence_into_local`; removed the second window loop; pre-filter and GIL/`py.detach` behavior preserved; `WindowError` mapping to the existing PyO3/`ProcessingError` messages
- `pyo3/tests/test_counter.py` - `TestPyCounterNReadPreFilterParity`: N at first/last base, internal NN, internal NNNN, lowercase n; pure-Python pre-filter reference for k 21/64 x canonical across FASTA, FASTQ, and `add_sequence`
- `.planning/phases/07-shared-counting-engine/phase7_pyo3_evidence.json` - clippy command lines, release/test/harness results, module path, pytest summary, one-extractor greps and call sites, manifest-freeze proof, N-read parity matrix

## Decisions Made

- **Pre-filter retained by design:** the cutover only replaces extraction; Python's strip-N contract stays until Phase 9, making D2 a deletion rather than a second implementation.
- **Extractor skipped count propagated:** even though the pre-filter makes it zero on current paths, `record_skipped` keeps the accounting honest for any future caller.
- **Unreachable `InvalidK` mapped, never panicked:** `add_sequence` maps it to the same `Invalid k-mer size` PyValueError; the file helper maps it to `KmerError::InvalidKmerSize`, mirroring `engine::map_window_error`.
- **Evidence is command/output based:** the plan's required schema is kept and extended with the actual manifest diff (empty), call-site line numbers, and the four-cell pre-filter-vs-skip-N comparison.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The default nightly toolchain emits a pre-existing `Atomic::fetch_update` deprecation warning from `src/hash/table.rs:483`. That file is untouched by this plan and the pinned MSRV 1.82 clippy gates are warning-free; the warning is out of scope (nightly-only, pre-existing) and was not suppressed or "fixed".

## User Setup Required

None - no external service configuration required.

## Known Stubs

None. No placeholders, skipped tests, or unrun verifications were introduced.

## Threat Flags

None beyond the plan's threat model. T-07-13 (GIL/Send captures), T-07-14 (stale `.so`, mitigated by rebuild + import/capability assert + recorded module path), T-07-15 (N-read semantics, mitigated by retained pre-filter + parity matrix), and T-07-16 / T-07-SC (MSRV/dependency drift, mitigated by `--locked` clippy and empty manifest/lockfile diffs) are all satisfied.

## Next Phase Readiness

- Phase 9 can switch Python onto the extractor's skip-N semantics by deleting the pre-filter; the extractor call sites and error mappings are already in place.
- Phase 8 is unaffected: no writer, sort, `.rkdb`, public API, or dependency change.
- No blockers; both surfaces now share one extraction implementation.

## Self-Check: PASSED

- Created file verified present: `.planning/phases/07-shared-counting-engine/phase7_pyo3_evidence.json`; modified files present.
- Task commits verified as ancestors of HEAD: `2230ae8`, `5d431d5`.
- `Cargo.toml` / `pyo3/Cargo.toml` / both lockfiles unchanged.

---
*Phase: 07-shared-counting-engine*
*Completed: 2026-11-12*
