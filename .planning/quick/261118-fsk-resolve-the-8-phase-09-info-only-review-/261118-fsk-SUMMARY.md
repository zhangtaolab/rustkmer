---
phase: quick
plan: 261118-fsk
subsystem: pyo3-counting-docs-and-bench-harness-honesty
tags: [review-disposition, pyo3-docstrings, non-linearizable-snapshot, prior-state-guard, cross-record-join, extension-free-test, compare-mode-quality-gate]

requires:
  - phase: 09-python-parity
    provides: the 09-REVIEW.md Info findings and the harness/test/doc code they target
  - phase: 05-measurement-regression-harness
    provides: the immutable pre-D2 n_read_differential.json artifact that --previous must keep accepting
provides:
  - IN-01 accepted — no code change; preservation gates are not cited as double-sort proof
  - IN-02 closed — parity-class docstring names the per-call CountEngine and checked merge_local_counts bridge
  - IN-03 closed — both save paths document the lock-free non-linearizable snapshot; CLI identity qualified
  - IN-04 closed — load_previous requires expectation "divergence" and a positive integer python_only_total
  - IN-05 closed — record_boundary scoped to the pre-D2 strip-and-join form; N-free two-read probe pinned test-locally
  - IN-06 closed — extension-absent test runs the script under sys.executable -S with PYTHONPATH dropped
  - IN-07 closed — SaveDatabaseError::Database documented as a defensive arm
  - IN-08 closed — compare mode requires --reps >= 3 and exits 2 on any measured arm's cv_warning
  - 09-REVIEW.md reads 7 Fixed / 1 Accepted / 0 Open with a dated Resolution section
affects: [phase-09-review-record, pyo3-counter-docs, scripts-bench-n-read-differential, scripts-bench-python-bench, docs-user-guide]

actuals:
  tokens: 7790
  tasks: 3
  commits: 1
  plan_head_before: 99fdaf9
  plan_head_after: fcbe3d24424b4a38682ea47b964d47087a346775

tech-stack:
  added: []
  patterns:
    - "Prior-artifact guard validates the historical claim itself: expectation == divergence plus a positive int total, bool/float rejected because bool is an int"
    - "Extension-absence is forced, not assumed: real script under sys.executable -S with PYTHONPATH removed, asserting rc 2 + the exact import message"
    - "Measurement quality is a gate layered before verdict math: reps floor and per-arm CV warning both exit 2 with no artifact"

key-files:
  created: []
  modified:
    - pyo3/tests/test_counter.py
    - pyo3/src/counter.rs
    - scripts/bench/n_read_differential.py
    - scripts/bench/tests/test_n_read_differential.py
    - docs/user-guide/n-read-semantics.md
    - scripts/bench/python_bench.py
    - scripts/bench/tests/test_python_bench.py
    - scripts/bench/README.md
    - .planning/milestones/v2.0-phases/09-python-parity/09-REVIEW.md

key-decisions:
  - "IN-01 stays a documentation-only acceptance: the preservation suites also pass on the parent implementation, so the single-sort property remains proven by code inspection and the 09-02 static greps"
  - "IN-05's N-free probe stays in the unit suite, not build_cases: the immutable pre-D2 artifact carries exactly nine cases and load_previous requires exact case-name parity, so a live case would stale the delivered evidence and docs table"
  - "IN-08's CV gate is an invalid-measurement exit 2 (no artifact), not a FAIL verdict, so a noisy run is never reported as PASS or FAIL; bench.py's separate --reps >= 2 comparison protocol was inspected and left unchanged"
  - "Resolution bullets cite quick-261118-fsk per finding, satisfying the plan's hyphenated-id gate while the table Status cells keep the plan's space-separated form"

patterns-established:
  - "Qualified deterministic claims: byte-identity and thread-independence are stated as conditional on no concurrent mutation, with internal consistency promised unconditionally"
  - "Defensive error arms are documented in place (variant + call site) rather than removed, preserving the frozen Display contract"

requirements-completed: []

metrics:
  duration: 6min
  completed: 2026-11-18
status: complete
---

# Quick 261118-fsk: Resolve the Eight Phase-09 Info-Only Review Findings Summary

**Closed the last carried review block — honest PyO3 counting docs (per-call CountEngine path, lock-free snapshot, debugged defensive arm), a prior-state guard and test-local cross-record-join probe for the N-read differential, a deterministic extension-free test, and compare-mode measurement-quality gates — with the review record flipped to 7 Fixed / 1 Accepted / 0 Open in one atomic nine-file commit.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-11-18T03:31:35Z
- **Completed:** 2026-11-18T03:37:59Z
- **Tasks:** 3/3
- **Files modified:** 9

## Accomplishments

- **IN-01 (Accepted, no code change):** The two preservation suites stay as preservation gates; the Resolution record states they also pass on the parent implementation and are not proof that the double sort was removed (that property remains code-inspection plus the 09-02 static greps).
- **IN-02:** `TestPyCounterLocalAccumulationParity`'s docstring now says the file helpers count through a per-call `CountEngine` and merge its partition tables via the checked `merge_local_counts` bridge; `add_sequence` stays on the shared increment path. The stale "one `LocalKmerCounts` per file call" sentence is gone.
- **IN-03:** `save_database`'s Notes now include the lock-free snapshot bullet and qualify the CLI-identity claim to "with no concurrent mutation"; `save_database_on_counter` documents that `get_all_counts` may observe a concurrent `add_*`/`reset` partially or not at all and the emitted DB is always internally consistent but not any point-in-time state.
- **IN-04:** `load_previous` requires `expectation == "divergence"` and a positive integer `totals.python_only_total` (bool/float/zero/absent rejected), returns the validated values, and documents the rule. The committed pre-D2 artifact still loads unchanged (`expectation` divergence, `python_only_total` 33, nine cases).
- **IN-05:** The `build_cases` docstring and the N-read semantics page now scope `record_boundary` to the pre-D2 strip-and-join form. A test-local `TestCrossRecordJoinProbe` pins two N-free 25 bp reads: per-record 2 distinct / 10 total vs concatenated 22 distinct / 30 total, 20 chimeric windows including `A*20+C` and `A+C*20`, empty intersection with per-record keys. The live fixture and committed artifacts are untouched.
- **IN-06:** `test_missing_extension_exits_2` now runs the real script under `sys.executable -S` in a subprocess with `PYTHONPATH` dropped, asserting exit 2, `cannot import pyrustkmer`, and no artifact; no skip. Verified OK under both system `python3` and `.venv313/bin/python`.
- **IN-07:** `SaveDatabaseError::Database` is documented as a defensive arm (`from_sorted_kmer_pairs` currently cannot fail), with a comment at the `.map_err` site; the "Failed to create database: " Display text and all signatures are unchanged.
- **IN-08:** Compare mode rejects `--reps < 3` before any measurement (exit 2, no artifact) and exits 2 after measurement when either control arm's `cv_warning` is set, naming the arms and the 10% threshold. Non-compare modes keep the `>= 1` floor and default `--reps 3`. README documents both gates; tests pin both plus a low-CV fake measure that preserves the existing PASS/FAIL verdict-math assertions.
- **Review record:** `09-REVIEW.md` shows IN-01 `Accepted — no code change (quick 261118-fsk)`, IN-02..IN-08 `Fixed — quick 261118-fsk`, zero Open cells, and a dated `## Resolution 2026-11-18 (quick-261118-fsk)` section recording actual observed results. Frontmatter and finding bodies are untouched.

## Task Commits

One atomic commit, exactly the nine files named in the plan frontmatter:

1. **All tasks: resolve the eight Phase-09 info-only findings** — `fcbe3d2` (fix)

Commit scope verified post-commit: 9 files changed, 313 insertions(+), 39 deletions(-). No Cargo manifest, dependency, public API, `.rkdb` format, ROADMAP, STATE.md, or other phase artifact touched. No file deletions.

## Files Created/Modified

- `pyo3/tests/test_counter.py` — IN-02 parity-class docstring rewritten (per-call `CountEngine` + checked `merge_local_counts` bridge).
- `pyo3/src/counter.rs` — IN-03 snapshot notes on `save_database`/`save_database_on_counter` and the qualified identity bullet; IN-07 defensive-arm doc plus call-site comment.
- `scripts/bench/n_read_differential.py` — IN-04 expectation/positive-total prior guard (returns validated values); IN-05 softened `build_cases` docstring.
- `scripts/bench/tests/test_n_read_differential.py` — IN-04 guard tests, IN-05 `TestCrossRecordJoinProbe`, IN-06 deterministic `-S` subprocess test.
- `docs/user-guide/n-read-semantics.md` — record-boundary bullet qualified: `record_boundary` covers only the pre-D2 strip-and-join form.
- `scripts/bench/python_bench.py` — IN-08 compare-mode `--reps >= 3` guard and CV-warning exit-2 gate (`CV_WARNING_THRESHOLD_PCT` imported).
- `scripts/bench/tests/test_python_bench.py` — `walls`-aware fake measure, `LOW_CV_COMPARE_WALLS`/`make_low_cv_measure`, low-CV default for `run_compare`, and the two new gate tests.
- `scripts/bench/README.md` — compare-mode measurement-quality requirements documented.
- `.planning/milestones/v2.0-phases/09-python-parity/09-REVIEW.md` — eight Status cells updated; dated Resolution section appended.

## Decisions Made

None beyond the plan, except the two mechanical reconciliations documented under Deviations.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The plan's hyphenated-id gate conflicted with its own space-form status cells**
- **Found during:** Task 3 verification
- **Issue:** The status-cell gates require the exact strings `| Fixed — quick 261118-fsk |` (>= 7) and `| Accepted — no code change (quick 261118-fsk) |` (>= 1), while the gate `grep -cF 'quick-261118-fsk' >= 9` expects the hyphenated id on at least nine lines. The mandated cells use a space, and the Resolution heading is a single hyphenated line, so the gate read 1.
- **Fix:** Kept the mandated table cells verbatim and cited `(quick-261118-fsk)` in each of the eight Resolution finding bullets. Hyphenated-id lines became 9 (heading + 8 bullets); both space-form cell gates and the hyphenated gate now pass. No finding text changed.
- **Files modified:** `.planning/milestones/v2.0-phases/09-python-parity/09-REVIEW.md`
- **Commit:** `fcbe3d2`

**2. [Rule 1 - Bug] The docs gate phrase was split by sentence wrapping**
- **Found during:** Task 2 verification
- **Issue:** The planned qualification wrapped `covers the pre-D2 strip-and-join form` across two source lines, so the `grep -cF` gate read 0 even though the rendered text was correct.
- **Fix:** Reflowed the same sentence so the phrase stays contiguous in source; wording and meaning are unchanged and the measured-evidence table is untouched.
- **Files modified:** `docs/user-guide/n-read-semantics.md`
- **Commit:** `fcbe3d2`

**3. [Rule 1 - Bug] The defensive-arm doc phrase was initially split by wrapping**
- **Found during:** Task 1 verification
- **Issue:** The first draft of the IN-07 doc comment broke `currently cannot fail` across a `///` line boundary, failing its own gate.
- **Fix:** Rewrapped the comment so the phrase is contiguous. No code or Display-string change.
- **Files modified:** `pyo3/src/counter.rs`
- **Commit:** `fcbe3d2`

### Not Applicable

- No package installs, no authentication gates, no checkpoints, no architectural changes.

## Verification Evidence

| Gate | Result |
|------|--------|
| Stale "one `LocalKmerCounts` per file call" (comments excluded) | 0 (was 1) |
| `per-call \`CountEngine\`` / `checked \`merge_local_counts\` bridge` | 1 / 1 (was 0 / 0) |
| `taken without locking`, `always internally consistent`, `With no concurrent mutation`, `currently cannot fail` | all present |
| `The emitted bytes are identical to the CLI \`count\` output for the` | 0 (was 1) |
| `Failed to create database: ` (Display contract) | 1 (unchanged) |
| `python3 -c "import ast, ... ast.parse(test_counter.py)"` | exit 0 |
| `cargo check --manifest-path pyo3/Cargo.toml` | exit 0 |
| `cargo fmt --manifest-path pyo3/Cargo.toml --check` | exit 0 |
| Prior guard messages (`prior artifact expectation=`, `is not 'divergence'`, `is not a positive integer`) | all present |
| False claim `equality here proves there` (comments excluded) | 0 (was 1) |
| `pre-D2 strip-and-join form` in code / `covers the pre-D2 strip-and-join form` in docs | 1 / 1 |
| Committed pre-D2 artifact reload (`python_only_total` 33, nine cases) | exit 0 |
| `python3 -m unittest scripts.bench.tests.test_n_read_differential` | 37 tests, OK (was 33) |
| `test_missing_extension_exits_2` under `.venv313/bin/python` | OK (1 test) |
| `python3 -m unittest scripts.bench.tests.test_python_bench` | 95 tests, OK, 1 skipped (was 93) |
| Combined n_read_differential + python_bench | 132 tests, OK, 1 skipped |
| Compare-mode gate phrases + `CV_WARNING_THRESHOLD_PCT` | present / present / 2 |
| Non-compare floor `--reps must be >= 1` | 1 (unchanged) |
| `LOW_CV_COMPARE_WALLS`, `test_compare_requires_three_reps`, `test_compare_high_cv_exits_2` | 2 / 1 / 1 |
| README `--reps >= 3` + preserved `There is no noise band` | 1 / 1 |
| Review record cells | 7 Fixed, 1 Accepted, 0 Open |
| `## Resolution 2026-11-18 (quick-261118-fsk)` + intact IN-01 body | 1 / 1 |
| `quick-261118-fsk` lines in review record | 9 |
| Working-tree diff before commit | exactly the nine intended files |
| Landed commit `fcbe3d2` file list / deletions | exactly the nine intended files / none |

`scripts/bench/tests/test_verify_threads.py` was not run (known pre-existing macOS `sample`-race flake, excluded by the task constraint).

## Known Stubs

None. No placeholder paths, empty data flows, or unrun verifications were introduced.

## Threat Flags

None. No new network endpoint, auth path, file access pattern, or schema change is introduced. Threat mitigations T-quick-fsk-01 (prior-state guard) and T-quick-fsk-02 (measurement-quality gates) are pinned by the tests above; T-quick-fsk-03's record integrity is pinned by the cell and body-preservation gates; T-quick-fsk-04's artifact immutability is preserved (live nine-case fixture untouched, committed evidence reloaded); T-quick-fsk-SC is satisfied (no installs or dependency changes).

## Self-Check: PASSED

- FOUND: `pyo3/tests/test_counter.py`
- FOUND: `pyo3/src/counter.rs`
- FOUND: `scripts/bench/n_read_differential.py`
- FOUND: `scripts/bench/tests/test_n_read_differential.py`
- FOUND: `docs/user-guide/n-read-semantics.md`
- FOUND: `scripts/bench/python_bench.py`
- FOUND: `scripts/bench/tests/test_python_bench.py`
- FOUND: `scripts/bench/README.md`
- FOUND: `.planning/milestones/v2.0-phases/09-python-parity/09-REVIEW.md`
- FOUND: `fcbe3d24424b4a38682ea47b964d47087a346775` (ancestor of HEAD)
