---
phase: 09-python-parity
plan: "01"
subsystem: pyo3-binding
tags: [pyo3, counting-engine, d2, skip-n, python-parity]
requires: []
provides:
  - "PyCounter file methods routed through the shared CountEngine (per-call engine, initial_capacity 0)"
  - "D2 skip-N semantics on add_from_fasta, add_from_fastq, and add_sequence"
  - "pyrustkmer.__version__ stale-extension tripwire"
  - "Executed pre-D2 RED evidence (exit 1, 4 divergent cases, python_only_total 33)"
affects:
  - pyo3/src/counter.rs
  - pyo3/src/lib.rs
  - pyo3/tests/test_counter.py
  - pyo3/tests/test_version.py
  - pyo3/tests/test_public_api.py
  - pyo3/tests/test_counter_concurrency.py
tech-stack:
  added: []
  patterns:
    - "Owned Send captures -> py.detach -> per-call CountEngine -> count_file -> finish -> merge_into"
    - "Raw bytes into for_each_window; no strip-and-join pre-filter"
key-files:
  created:
    - pyo3/tests/test_version.py
    - pyo3/tests/test_public_api.py
    - pyo3/tests/test_counter_concurrency.py
    - .planning/phases/09-python-parity/evidence/n_read_differential_pre_d2_red.json
    - .planning/phases/09-python-parity/evidence/pre_d2_red_observation.json
  modified:
    - pyo3/src/counter.rs
    - pyo3/src/lib.rs
    - pyo3/tests/test_counter.py
decisions:
  - "Per-call CountEngine with initial_capacity=0; no engine state cached on PyCounter"
  - "Private threads field stores the already-resolved count; no Python-visible getter"
  - "SequenceKind bound to a local before py.detach for rustfmt format stability"
  - "D2 skip-N applies to whitespace and every non-ACGT byte, not only N"
  - "__version__ from env!(CARGO_PKG_VERSION); the version test has no skip guard"
metrics:
  duration: "6m 39s"
  completed: "2026-11-13"
status: complete
actuals:
  tokens: 14634
  tasks: 3
  commits: 3
  plan_head_before: 4c97787120bd8341176ca99a3f54b7bc6efb5032
  plan_head_after: 5f4714f3b7b8d5b64befee88a45dc6341d8c23aa
---

# Phase 9 Plan 01: Python Counter Engine Cutover and D2 Skip-N Summary

`PyCounter` file methods now count through the shared `CountEngine` with raw-byte D2 skip-N extraction, the rebuilt extension exports `__version__` 0.5.0, and the pre-D2 RED (exit 1, four divergent cases, 33 Python-only chimeric keys) was captured as an executed observation before any binding edit.

## What Was Built

### Task 1: Engine routing, D2 extraction, version export (tracer)

- Captured the pre-D2 RED first: built the untouched tree, rebuilt the extension, and ran
  `n_read_differential.py --expect-unified`. Observed raw exit `1` with divergent cases
  `["n_at_window_end", "n_at_window_start", "multiple_n", "lowercase_n"]`,
  `python_only_total = 33`, `cases = 9`, and a pre-change module with no `__version__`.
  Both evidence files are committed.
- `pyo3/src/counter.rs`: private `threads: usize` field set from `resolved_threads`, a
  `count_file_into_counter` helper building a fresh `EngineConfig::new(k, canonical, threads, 0)`,
  and `add_from_fasta` / `add_from_fastq` releasing the GIL via `py.detach` with owned `Send`
  captures. The obsolete sequential line loops and strip-and-join helpers were deleted.
- `add_sequence` now feeds `seq_str.as_bytes()` straight to `for_each_window`; the non-ACGT
  pre-filter and the `cleaned.len() < k` early return are gone.
- `pyo3/src/lib.rs` registers `__version__` with `env!("CARGO_PKG_VERSION")`.
- The file contains zero occurrences of the deprecated GIL-release identifier and zero
  `reader.lines()` loops.

### Task 2: Version tripwire, API freeze, concurrency proof

- `test_version.py` imports `pyrustkmer` at module scope with no skip guard and compares
  `__version__` to `pyo3/pyproject.toml`'s `[project].version`.
- `test_public_api.py` pins the exact 12-name public `PyCounter` surface by set equality and
  re-asserts the documented constructor keywords (`threads=0` still raises `ValueError`).
- `test_counter_concurrency.py` counts four distinct FASTQ files with four Python threads on one
  shared counter (and on per-thread counters), collecting every future with
  `future.result(timeout=120)` and comparing against exact reference maps.
  `TestCounterAccumulation` covers same-file-twice 2x, disjoint-files-equals-byte-concatenation,
  and the zero-byte record-less FASTQ.

### Task 3: Pre-D2 tests inverted to skip-N with anti-softening guards

- Whitespace, newline, and `N`-containing `add_sequence` inputs now assert zero k-mers.
- `TestPyCounterRollingPathParity` and `TestPyCounterNReadSkipParity` use skip-N references and
  each carries `test_fixture_still_exercises_d2_not_strip_and_join`, asserting the module-level
  `_strip_join_counts` (retired behavior) differs from the skip-N reference on the same fixture.
- The nonexistent-FASTQ assertion now matches `Failed to process FASTQ` (the engine's actual
  open-error prefix).

## Verification

| Gate | Result |
|------|--------|
| Pre-D2 RED | exit 1; 9 cases; 4 divergent; `python_only_total=33`; no `__version__` |
| Static routing gates | 1 `CountEngine::new`, 1 `count_file(Path::new`, 1 `merge_into(counter)`, 0 `reader.lines()`, 0 deprecated identifier, 2 `py.detach` sites |
| `rustfmt --edition 2021 --check pyo3/src/counter.rs` | clean |
| `cargo +1.82.0 clippy --locked --all-targets --manifest-path pyo3/Cargo.toml -- -D warnings` | passed |
| Focused FASTA/FASTQ/save pytest selection | 23 passed |
| `pytest pyo3/tests/test_counter.py -q` | 119 passed |
| New Task 2 test files | 9 passed |
| Full `pytest pyo3/tests -q` | 169 passed, 63 skipped (pre-existing skips) |
| D2 integration probe (`--expect-unified`, output to `/tmp`) | exit 0, all 9 cases equal, 0 divergent |
| Four manifests/lockfiles vs base | byte-unchanged (`git diff --stat` empty) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree was created from a stale base commit**
- **Found during:** Startup worktree branch check
- **Issue:** HEAD was `2fc58cb` while the declared expected base was `4c97787...` on `dev`.
  `2fc58cb` is a strict ancestor of the expected base with zero divergent commits, so no work
  had landed on the stale base.
- **Fix:** `git merge --ff-only 4c97787120bd8341176ca99a3f54b7bc6efb5032` before any edit; HEAD
  then matched the expected base exactly.
- **Files modified:** none

**2. [Rule 3 - Blocking] `.venv313` is untracked and therefore absent from the worktree**
- **Found during:** Pre-D2 RED setup
- **Issue:** The plan's rebuild/test commands use `$PWD/.venv313`, but virtualenvs are untracked
  and worktrees do not copy them.
- **Fix:** Created a worktree-local `.venv313` symlink to the existing
  `/Users/forrest/GitHub/rustkmer/.venv313`; every mandated command then ran verbatim
  (`VIRTUAL_ENV="$PWD/.venv313"`, `PATH="$PWD/.venv313/bin:$PATH"`). The symlink is untracked
  and not committed.
- **Files modified:** `.venv313` (untracked symlink only)

**3. [Rule 3 - Tooling] Observation generator used the venv interpreter**
- **Found during:** Writing `pre_d2_red_observation.json`
- **Issue:** The plan asks for a `python3 -c` guard, but the system `python3` cannot import
  `pyrustkmer` (needed to read `__version__` and resolve the native module hash).
- **Fix:** Ran the same guarded one-liner with `.venv313/bin/python -c`; the assertions (exit
  code 1, exact four cases, `python_only_total == 33`, absent version attribute) are unchanged.
- **Files modified:** none

## Authentication Gates

None. No credential, login, or secret-bearing step was required.

## Known Stubs

None. Every changed path is wired to real data; the evidence files are executed observations.

## Threat Flags

None. The changes match the plan's threat model (owned `Send` captures across `py.detach`, no new
dependencies, strict `bio` parsing mapped to `PyValueError`, and the `__version__` tripwire against
a stale `.so`).

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | `d8befcf` | feat(09-01): route PyCounter file methods through the shared counting engine |
| 2 | `25bf259` | test(09-01): version tripwire, 12-name API freeze, concurrent exact-count tests |
| 3 | `5f4714f` | test(09-01): invert pre-D2 parity tests to skip-N with anti-softening guards |

## Self-Check

- Created files verified present: `pyo3/tests/test_version.py`, `pyo3/tests/test_public_api.py`,
  `pyo3/tests/test_counter_concurrency.py`,
  `.planning/phases/09-python-parity/evidence/n_read_differential_pre_d2_red.json`,
  `.planning/phases/09-python-parity/evidence/pre_d2_red_observation.json`.
- Commits verified ancestors of HEAD: `d8befcf`, `25bf259`, `5f4714f`.

## Self-Check: PASSED
