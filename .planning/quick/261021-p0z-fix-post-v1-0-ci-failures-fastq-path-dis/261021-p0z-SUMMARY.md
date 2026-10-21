---
phase: quick
plan: 261021-p0z
subsystem: ci
tags: [windows, fastq, pyo3, docs, mkdocs, ci]
status: complete
dependency-graph:
  requires: []
  provides:
    - "Windows-native path rendering in FASTQ count_sequences errors"
    - "Cross-platform bogus-temp-dir probe (TMPDIR/TMP/TEMP)"
    - "Buildable MkDocs docs site with tracked requirements"
  affects:
    - ".github/workflows/docs.yml"
    - "mkdocs.docs.yml"
tech-stack:
  added: []
  patterns:
    - "Path::display() for user-facing path messages (native separators)"
    - "Redirect TMPDIR/TMP/TEMP together for cross-platform std::env::temp_dir() probes"
    - "MkDocs config at repo root with docs_dir: docs / site_dir: site"
key-files:
  created:
    - docs/requirements.txt
    - mkdocs.docs.yml
  modified:
    - src/io/fastq.rs
    - pyo3/tests/test_database_merge.py
    - .github/workflows/docs.yml
    - docs/index.md
    - docs/guides/development.md
    - .gitignore
  deleted:
    - docs/mkdocs.yml
decisions:
  - "MkDocs config moved to repo-root mkdocs.docs.yml: docs_dir may not equal the config file's directory, and docs/ had to remain the source location"
  - "docs/requirements.txt needed a .gitignore negation because the blanket *.txt rule excluded it"
metrics:
  duration: ~2 min
  completed: 2026-10-21T10:08:31Z
  commits: 3
  files_changed: 8
plan_head_before: 3c7cb93d4e8b5970da931995406f3303c8363fed
plan_head_after: 6c2ebcbb65c9ee678525df7a4016448c89b3b0b6
---

# Quick 261021-p0z: Fix Post-v1.0 CI Failures (FASTQ Path Display, Temp-Dir Probe, Docs Workflow)

Restores green CI on `dev` with three atomic commits: Windows-safe FASTQ error paths via `Path::display()`, a cross-platform bogus-temp-dir probe that also redirects `TMP`/`TEMP`, and a documentation workflow that builds strictly from a tracked, relocated MkDocs config.

## Tasks

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Format FASTQ error paths with `display()` | `5283527` | `src/io/fastq.rs` |
| 2 | Redirect `TMPDIR`/`TMP`/`TEMP` in the bogus-temp-dir probe | `336f182` | `pyo3/tests/test_database_merge.py` |
| 3 | Repair the Documentation Build and Deploy workflow | `6c2ebcb` | `.github/workflows/docs.yml`, `mkdocs.docs.yml` (moved from `docs/mkdocs.yml`), `docs/requirements.txt`, `docs/index.md`, `docs/guides/development.md`, `.gitignore` |

### Task 1 detail

In `count_sequences` only, the open-failure message now interpolates `path.display()` and the record-read failure message likewise. `Path`'s `Debug` escapes backslashes on Windows (`C:\\Users\\...`) while the test asserts the native single-backslash path; `display()` renders native separators everywhere. The other `{:?}` path uses elsewhere in `fastq.rs` were left untouched, as was the test assertion.

### Task 2 detail

`_bogus_temp_dir` now sets `TMPDIR`, `TMP`, and `TEMP` to the nonexistent directory. `std::env::temp_dir()` consults `TMPDIR` on Unix but `TMP`/`TEMP` on Windows (ignoring `TMPDIR`), so the previous helper left the Windows probe pointing at a valid directory. The docstring records the cross-platform env-var set and the Windows reason. No test bodies or assertions changed.

### Task 3 detail

- `docs/requirements.txt` created with `mkdocs>=1.6,<2`, `mkdocs-material>=9.5`, `pymdown-extensions>=10`.
- `docs/mkdocs.yml` relocated via `git mv` to root `mkdocs.docs.yml` with `docs_dir: docs` and `site_dir: site`.
- Nav: deleted the four dead `Tutorials:` entries; deduplicated the `search` plugin; removed `dev_addr`; added `exclude_docs` for `README.md`, `api-reference/rust/**`, `examples/python/**`.
- Out-of-tree links fixed in `docs/index.md` and `docs/guides/development.md` to point at the GitHub `CONTRIBUTING.md` URL.
- `docs.yml`: added `mkdocs.docs.yml` to PR paths (keeping the existing root `mkdocs.yml` trigger); made pydocstyle conditional on `python/rustkmer`; removed the two steps calling nonexistent scripts; builds/deploys with `-f mkdocs.docs.yml` from the repo root; `test-docs` now installs `docs/requirements.txt` before its MkDocs calls.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `docs/requirements.txt` was excluded by the blanket `*.txt` gitignore rule**
- **Found during:** Task 3 staging
- **Issue:** `.gitignore:56` ignores `*.txt`, so the new requirements file would not be committed and `pip install -r docs/requirements.txt` would fail on a clean CI checkout.
- **Fix:** Added a `!docs/requirements.txt` negation, matching the existing precedent for time fixtures and golden files. File is now tracked (`git check-ignore` reports not ignored).
- **Files modified:** `.gitignore`
- **Commit:** `6c2ebcb`

## Verification

| Check | Command | Result |
|-------|---------|--------|
| FASTQ lib tests | `cargo test --lib io::fastq` | PASS — 13 passed, 0 failed |
| pyo3 merge tests | `.venv313/bin/python -m pytest pyo3/tests/test_database_merge.py -q` | PASS — 12 passed |
| Strict docs build (fresh venv) | `python3 -m venv "$VENV" && "$VENV/bin/pip" install -q -r docs/requirements.txt && "$VENV/bin/mkdocs" build -f mkdocs.docs.yml --strict` | PASS — exit 0, 0 WARNING lines, `site/index.html` written |
| Workflow YAML parse | `yaml.safe_load('.github/workflows/docs.yml')` | PASS |
| Working tree | `git status --short` | Clean (`site/` gitignored) |
| Commit hygiene | `git log -3 --format="...%(trailers)"` | 3 commits, no trailers |

Windows CI (`windows-latest` root test and pyo3 pytest) remains the authoritative check for failures 1 and 2; the macOS runs prove no regression.

## Observations (not changed)

- The repo already had a root `mkdocs.yml` (a separate site config). The workflow's `paths` entry for it is a legitimate trigger, so `mkdocs.docs.yml` was added alongside it rather than replacing it.
- MkDocs 1.6+ emits INFO-level notices (not warnings) for relative links in pages outside the nav (e.g. `tutorials/basic-workflow.md`, `user-guide/index.md`, Chinese anchors). They do not fail `--strict`; per plan, they were reported rather than edited.
- Remaining references to `docs/mkdocs.yml` exist only in `.planning/` history (PLAN, milestone review docs), which is out of this task's scope.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, file-access patterns, or schema changes.

## Self-Check: PASSED
