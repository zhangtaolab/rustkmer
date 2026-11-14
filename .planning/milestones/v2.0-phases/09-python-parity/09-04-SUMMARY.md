---
phase: 09-python-parity
plan: "04"
subsystem: bench-harness + user-docs
tags: [n-read, skip-N, differential, before-after, mkdocs, pyo3, migration-note]
requires:
  - phase: 05-measurement-regression-harness
    provides: committed pre-D2 n_read_differential.json (sha256 6d929a45…, python_only_total 33)
  - phase: 09-python-parity
    provides: 09-01 D2 skip-N PyCounter and updated method docstrings
provides:
  - "n_read_differential.py records skip-N-windows on both surfaces and pins it with a unit test"
  - "n_read_differential.py --previous validates k/canonical/case-set/shape and embeds a before block"
  - "docs/user-guide/n-read-semantics.md wired into the root mkdocs.yml nav and the user-guide index"
  - "pyo3/README.md Phase 9 migration subsection with the exact 70 -> 37 / 33-key evidence"
affects:
  - 09-05 final evidence run (--expect-unified --previous)
  - Phase 10 CI baseline documentation surfaces
tech-stack:
  added: []
  patterns:
    - "Validate-before-embed: a prior artifact is schema-checked before it can become a before block"
    - "Docs proof: exact committed before/after numbers pinned by content greps on every surface"
key-files:
  created:
    - docs/user-guide/n-read-semantics.md
  modified:
    - scripts/bench/n_read_differential.py
    - scripts/bench/tests/test_n_read_differential.py
    - mkdocs.yml
    - docs/user-guide/index.md
    - pyo3/README.md
decisions:
  - "EXPECTED_SEMANTICS records skip-N-windows on both surfaces; a unit test pins the literal so the retired value cannot return"
  - "--previous is a plain parser.add_argument outside the --expect-* mutually exclusive group so it composes with --expect-unified"
  - "load_previous rejects k/canonical/case-set/shape mismatches with ValueError; malformed JSON propagates as JSONDecodeError; both map to exit 2"
  - "Top-level cases stay the after state; the validated prior is embedded only as doc[before]"
  - "Docs gates are file/nav/content greps; mkdocs build --strict is skipped because the host lacks the section-index plugin"
requirements-completed: [PY-02]
coverage:
  - id: D1
    description: "Differential records unified skip-N semantics and embeds a strictly validated pre-D2 before block via --previous"
    requirement: PY-02
    verification:
      - kind: unit
        ref: "scripts/bench/tests/test_n_read_differential.py (33 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "N-read semantics docs page, mkdocs nav, index link, and pyo3/README.md migration note state the exact 33/70/37 evidence"
    requirement: PY-02
    verification:
      - kind: other
        ref: "task 2 <automated>: file/nav/content grep gate (n-read-semantics.md, mkdocs.yml, index.md, pyo3/README.md)"
        status: pass
    human_judgment: true
    rationale: "Content greps pin the presence of the exact numbers but not their semantic correctness; 09-05's measured --expect-unified run is the authoritative re-proof of the documented before/after."
duration: "5min"
completed: "2026-11-13"
status: complete
actuals:
  tokens: 6068
  tasks: 2
  commits: 2
  plan_head_before: 57ba6d959e9d5dd14a328e51de944365ff1b09cb
  plan_head_after: dd70da794dd8fa4f398869422f1f0984f76ddaae
---

# Phase 9 Plan 04: N-read Unified Semantics and Documentation Summary

The N-read differential now records skip-N on both surfaces and can embed the committed pre-D2 record as a validated `before` block, while a new user-guide page and README migration note document the 33-key / 70→37 change with the exact committed evidence.

## Performance

- **Duration:** 5 min
- **Started:** 2026-11-13T01:48Z
- **Completed:** 2026-11-13T01:53Z
- **Tasks:** 2
- **Files modified:** 6 (1 created, 5 modified)

## Accomplishments

- `EXPECTED_SEMANTICS` now records `{"cli": "skip-N-windows", "python": "skip-N-windows"}`; the retired strip-and-join literal is gone and a unit test pins the unified value.
- `load_previous(path)` validates a prior differential before embedding it: k, canonical, the exact nine-case name set, uniqueness, and each case's `{distinct, total}` integer shape. Every incompatibility is exit-2 invalid; malformed JSON propagates as `JSONDecodeError`.
- `--previous PATH` is registered with `parser.add_argument` outside the `--expect-divergence`/`--expect-unified` group, so 09-05's `--expect-unified --previous …` invocation parses. The top-level `cases` remain the after state; the prior lands in `doc["before"]`.
- The module docstring and argparse description no longer claim the script is record-only; they state Phase 9 landed D2.
- `docs/user-guide/n-read-semantics.md` states what skip-N means (any non-ACGT byte, windows never span records), the full nine-case before/after table, why `total_kmers` drops by design, the whitespace consequence, strict FASTA/FASTQ `ValueError` parsing, and the absence of a skipped-window API.
- The page is in the root `mkdocs.yml` User Guide nav immediately after Counting k-mers, linked from `docs/user-guide/index.md`, and mirrored by a `## Migration Guide` subsection in `pyo3/README.md` with the same 70→37 / 33 numbers, `__version__`, and the exact `.venv313` rebuild command.
- Read-only confirmation: `load_previous` accepts the committed Phase 5 artifact with sha256 `6d929a4519059f445e9beb8062b86d1e5a455c04797e75b177798fe1447b6b32` and `python_only_total == 33`; the artifact itself was not modified.

## Task Commits

Each task was committed atomically:

1. **Task 1: Record unified semantics and add --previous before/after loading** - `5664c7a` (feat)
2. **Task 2: Write and wire the N-read semantics page plus README migration note** - `dd70da7` (docs)

**Plan metadata:** committed after this summary (docs: complete plan)

## Files Created/Modified

- `scripts/bench/n_read_differential.py` — unified `EXPECTED_SEMANTICS`, `load_previous`, `_validated_surface_counts`, `--previous`, updated docstring/description, `doc["before"]` embedding.
- `scripts/bench/tests/test_n_read_differential.py` — `TestUnifiedSemantics`, `TestPreviousLoading` (valid embed; k/canonical/missing/extra/duplicate case-name; missing cases list; malformed JSON; malformed case blocks; parse composition with `--expect-unified`), plus a shared `run_main` helper.
- `docs/user-guide/n-read-semantics.md` — user-visible D2 semantics page with the exact nine-case evidence table.
- `mkdocs.yml` — `N-read Semantics: user-guide/n-read-semantics.md` nav entry after Counting k-mers.
- `docs/user-guide/index.md` — Guide Overview bullet linking the new page.
- `pyo3/README.md` — Phase 9 migration subsection (numbers, whitespace, strict parser, `__version__`, rebuild command). The pre-existing `Current Version: 0.4.1` line and version-history entries were left untouched.

## Decisions Made

- Kept `--previous` out of the mutually exclusive group (phase invariant 1); the parse-composition test guards against regression.
- Embedded only the validated projection of the prior artifact (path, sha256, expectation, totals, per-case counts) rather than the whole file, so extra keys cannot leak unvalidated data into the evidence doc.
- Added duplicate-case-name rejection beyond the minimum ask: set equality alone would let a duplicated name through.
- Used grep gates instead of `mkdocs build --strict` because the host lacks the `section-index` plugin; no packages or plugins were installed.

## Deviations from Plan

None - plan executed exactly as written. (Two extra unit tests — duplicate case names and `--previous`/`--expect-unified` parse composition — were added inside the planned test file to directly cover the plan's acceptance criteria.)

## Issues Encountered

- **Stale worktree base:** the worktree was created at `2fc58cb`, an ancestor of the expected base `57ba6d9`, and the phase 9 plan files were absent. Since the agent branch had no own commits and the tree was clean, the branch was fast-forwarded (`git merge --ff-only 57ba6d9…`) onto the expected base before any edit. No merge commit, no history rewrite, no work lost.
- **Full harness discovery is 370/372 green:** the two failures (`test_schema.TestRealRunProvenance`, `test_schema.TestRealSelfCheckOutput`) fail with rc=127 because `target/release/rustkmer` does not exist in this fresh worktree. They are environmental and unrelated to this plan's files (no binary was built here); the plan's own suite is 33/33 green.

## Authentication Gates

None.

## Known Stubs

None.

## Threat Flags

None — no new endpoints, auth paths, or trust-boundary surface beyond the planned prior-artifact validation (mitigated by `load_previous`).

## Next Phase Readiness

- 09-05 can run `.venv313/bin/python scripts/bench/n_read_differential.py --expect-unified --previous .planning/phases/05-measurement-regression-harness/n_read_differential.json --rustkmer target/release/rustkmer --out .planning/phases/09-python-parity/evidence/n_read_differential_d2.json` and expect exit 0 with totals 0/0/0 and a `before` block carrying `python_only_total == 33`.
- The docs and README already state the exact numbers that the measured artifact must reproduce.

---
*Phase: 09-python-parity*
*Completed: 2026-11-13*

## Self-Check: PASSED

- FOUND: docs/user-guide/n-read-semantics.md
- FOUND: scripts/bench/n_read_differential.py
- FOUND: .planning/phases/09-python-parity/09-04-SUMMARY.md
- FOUND: 5664c7a (Task 1)
- FOUND: dd70da7 (Task 2)
