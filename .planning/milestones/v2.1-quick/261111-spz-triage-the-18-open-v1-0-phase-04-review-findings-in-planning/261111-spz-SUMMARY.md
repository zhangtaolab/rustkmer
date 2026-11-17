---
phase: quick
plan: 261111-spz
subsystem: docs
status: complete
tags: [triage, code-review, docs, examples, mkdocs, milestone-close]
requires: ["261111-sq0"]
provides: ["04-REVIEW-DISPOSITION triaged (0 open)", "CLI-facing docs corrected", "docs-site configs repaired"]
affects: ["README.md", "CONTRIBUTING.md", "docs/", "mkdocs.yml", "mkdocs.docs.yml", "examples/python/"]
tech-stack:
  added: []
  patterns: ["docs-only triage with negative-gate proof", "per-task atomic commits with explicit path staging"]
key-files:
  created: []
  modified:
    - README.md
    - CONTRIBUTING.md
    - docs/api-reference/index.md
    - docs/api-reference/overview.md
    - mkdocs.yml
    - mkdocs.docs.yml
    - docs/installation.md
    - docs/index.md
    - docs/README.md
    - examples/python/demo_pyo3_binding.py
    - examples/python/test_pyo3_api.py
    - examples/python/demo_performance.py
    - .planning/milestones/v1.0-phases/04-benchmark-validation/04-REVIEW-DISPOSITION.md
decisions:
  - "11 fix-now defects corrected in place; 4 already-fixed closures evidenced (IN-01/IN-05/IN-08/CR-02); 3 code-level findings deferred with concrete follow-ups (IN-06/IN-07/IN-09) — zero behavior change"
  - "Canonical GitHub org is zhangtaolab/rustkmer per live git remote; site_url (Pages target) left untouched"
  - "Root mkdocs.yml Deployment/Background/Appendix nav sections deleted wholesale (dirs do not exist); no pages fabricated"
metrics:
  duration: ~8 min
  completed: 2026-11-11
  tasks: 3
  files: 13
actuals:
  tasks: 3
  commits: 3
plan_head_before: a5eecad6d737cc1db45eb069af3c8b25955da2a0
plan_head_after: e0de050ff5a58b68645c0541fd07556b06b5094a
---

# Phase quick Plan 261111-spz: Triage the 18 open v1.0 Phase-04 review findings Summary

**All 18 open Phase-04 review findings triaged to 0 open (11 fix-now docs/examples corrections applied and gate-proven, 4 already-fixed closures evidenced, 3 harness/test findings deferred with pinned follow-ups), landed as 3 atomic commits whose union is exactly the 13-file set — zero changes under src/, tests/, scripts/, pyo3/, .github/.**

## Triage Census

| Class | Count | IDs |
|-------|-------|-----|
| fix-now (applied) | 11 | WR-01, WR-02, WR-03, WR-04, WR-05, WR-06, WR-07, WR-08, IN-02, IN-03, IN-04 |
| already-fixed (evidenced) | 4 | IN-01, IN-05, IN-08, CR-02 |
| defer (follow-up recorded) | 3 | IN-06, IN-07, IN-09 |
| wont-fix | 0 | — |

Disposition doc final state: 19 rows preserved (incl. CR-01 fixed, byte-identical), `open: 0`, 16 `fixed` rows (15 triaged + pre-fixed CR-01), 3 `deferred`. Triage section appended with vocabulary mapping, provenance (14-finding current review + 5 carried rows), stale-path note (STATE.md's `.planning/phases/...` vs live `.planning/milestones/v1.0-phases/...`), and count reconciliation. 0 critical open.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Correct CLI-facing docs (WR-01/02/03/07) | `bd3736f` | README.md, CONTRIBUTING.md, docs/api-reference/{index,overview}.md |
| 2 | Repair docs-site configs and snippets (WR-04/05/06, IN-02/04) | `55477e9` | mkdocs.yml, mkdocs.docs.yml, docs/installation.md, docs/index.md, docs/README.md |
| 3 | Fix example refs + record full triage (WR-08, IN-03) | `e0de050` | examples/python/{demo_pyo3_binding,test_pyo3_api,demo_performance}.py, 04-REVIEW-DISPOSITION.md |

### Task 1 details
- WR-01: inserted `-i` before positional inputs in 7 README count commands (L273/299/305/433/471/477/556; L474/L654 already correct, untouched); usage template rewritten to USER_GUIDE form `count [OPTIONS] -k <K> -i <INPUT>... -o <OUTPUT>`.
- WR-02: `-k, --kmer-size` → `-k, --k` (clap field `k` derivation, verified in src/cli/args.rs).
- WR-03: CONTRIBUTING paragraph rewritten to match ci.yml pyo3-pytest job (3-OS matrix, wheel build/install, `pytest tests/ --cov=pyrustkmer --cov-report=term-missing --cov-fail-under=80`; local addopts only `-v`); pyo3-pytest row added to the gates table. ci.yml untouched (sibling spy owns it).
- WR-07: migration rows — dump `--limit` dropped with "pagination is Python-only" note (index.md:228, overview.md:382); merge via `-i` (index.md:229); overview.md:383 ellipsis row normalized to explicit `-i <DB1> <DB2> [...]` form. Python-side cells untouched.

### Task 2 details
- WR-04: root mkdocs.yml nav — Tutorials repointed to tutorials/index.md, KmerCounter to api-reference/rust/kmer_counter.md, CLI to api-reference/rust/args.md; Deployment/Background/Appendix sections deleted (15 dead entries → 0). mkdocs.docs.yml logo/favicon keys removed (docs/assets/ absent).
- WR-05: PyPI social link → https://pypi.org/project/pyrustkmer/.
- WR-06: stray-parenthesis f-string fixed in docs/installation.md and docs/index.md.
- IN-02: docs/README.md example uses `if result.found:` (getter verified at pyo3/src/database.rs).
- IN-04: repo_name/repo_url in both configs, mkdocs.yml social link, docs/installation.md issues link → zhangtaolab/rustkmer (live git remote). site_url and already-canonical references untouched.
- IN-01/IN-05 evidence (no edit): `search` declared exactly once per live config (mkdocs.yml:40, mkdocs.docs.yml:53); `dev_addr` absent from both (loopback default applies).

### Task 3 details
- WR-08: dangling guide filenames replaced with docs/guides/pyo3-binding-guide.md and docs/guides/prefix-query-guide.md in both scripts (Chinese prose preserved); all three scripts pass py_compile.
- IN-03: `throughput_mbps` → `throughput_gbps` (2 sites); `queries_per_second` given the sibling's conditional zero-guard.
- Disposition doc: frontmatter + table updated for all 18 rows; one-line rationales in Source cells (no literal pipes); deferred rows carry concrete follow-ups (IN-06 format!/drop placeholder test-hygiene pass; IN-07 reject leading-hyphen paths in validate_path + pinned test; IN-09 explicit fingerprints-section note + test_render_report pin); carried-row "(not in the current review)" flags preserved; legend preserved; CR-01 row byte-identical (diff-proven).

## Verification Results (all gates PASS)

| Gate | Baseline | Post-fix |
|------|----------|----------|
| T1 positional-count / template / long-flag / stale-claim | 7 / 1 / 1 / 1 | 0 / 0 / 0 / 0 |
| T1 pyo3-pytest pin / migration-row | 0 / 3 | 2 / 0 |
| T1 commit-range (4 files) | — | PASS |
| T2 snippet / PyPI-404 / truthy / legacy-org | 2 / 1 / 1 / 4 | 0 / 0 / 0 / 0 |
| T2 found pin / pyrustkmer pin / dev_addr | 0 / 0 / 0 | 1 / 1 / 0 |
| T2 nav missing (root + docs configs) | 15 + 0 | 0 + 0 |
| T2 mkdocs.docs.yml --strict build | exit 0 | exit 0 (re-verified post-T3) |
| T2 commit-range (5 files) | — | PASS |
| T3 dangling-guide / throughput_mbps | 3 / 2 | 0 / 0 |
| T3 throughput_gbps / qps guard / py_compile | 0 / none / — | 2 / PASS / PASS |
| T3 disposition open / id rows / deferred / table-open | 18 / 19 / 0 / 18 | 0 / 19 / 3 / 0 |
| T3 {route} placeholders in tests (no-edit proof) | 2 | 2 (unchanged) |
| T3 CR-01 byte-identity | — | PASS (diff-proven) |
| T3 commit-range (4 files) | — | PASS |
| Scope guard: src/ tests/ scripts/ pyo3/ .github/ porcelain | — | empty (PASS) |
| Full-scope lock: HEAD~3..HEAD union == 13-file set | — | PASS |
| Clean tree excl .planning/ and ignored .claude/ | — | PASS |

## Deviations from Plan

None — plan executed exactly as written. README line numbers had not shifted despite sibling sq0 edits (content-matched regardless). No Rule 1-4 deviations triggered; no auth gates; no checkpoints.

## Known Stubs

None. All corrections are complete in-place fixes; the 3 deferred findings are recorded dispositions with follow-ups, not stubs (they are pre-existing harness/test items outside this item's authorized scope, tracked in the disposition doc's Source cells and triage table).

## Deferred Follow-ups (recorded in disposition doc, not fixed here)

- IN-06: interpolate route name in tests/merge_bounded_memory_tests.rs:670,679 expect_err messages (test-hygiene pass).
- IN-07: reject leading-hyphen paths in scripts/bench/bench.py validate_path (or prefix ./) with a pinned test under scripts/bench/tests/.
- IN-09: explicit note in rendered fingerprints section for results files lacking input_fingerprint, pinned by a test_render_report test.

## Self-Check: PASSED

(verified below — files exist, all 3 commits are ancestors of HEAD)