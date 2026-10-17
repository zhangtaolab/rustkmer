---
phase: quick-261017-n2p
plan: 01
subsystem: ci
tags: [ci, github-actions, windows, matrix]
requires:
  - "8f23225 (test(win): make the test suite pass on Windows) — full suite verified green locally on Windows"
provides:
  - "windows-latest CI coverage on all three gate jobs (clippy-root, test-root, pyo3-build)"
affects:
  - ".github/workflows/ci.yml"
tech-stack:
  added: []
  patterns:
    - "3-OS matrix expansion with zero gate weakening — identical unmodified gate steps run on the Windows leg"
key-files:
  created: []
  modified:
    - .github/workflows/ci.yml
decisions:
  - "Matrix-only change: no --skip filters, no continue-on-error, no || true, no if-guards, no timeout bump — a failing Windows leg is the signal issue #15 exists to surface, not something to suppress"
  - "fmt stays ubuntu-only (rustfmt is platform-neutral); benchmark workflow untouched (Windows bench baseline deferred to phase-04 flavor system)"
metrics:
  duration: ~1 min
  completed: 2026-10-17
actuals:
  tokens: 244
  tasks: 1
  commits: 1
plan_head_before: ae9992f1b402fd8b02046b1260dc241c4387a582
plan_head_after: b514331b5c0a819bdf7088b4e60f4fdb005e0200
status: complete
---

# Quick Task 261017-n2p: windows-latest in all three CI matrices Summary

One-liner: Added `windows-latest` as the third OS in the clippy-root, test-root, and pyo3-build matrices in `.github/workflows/ci.yml` (3-line diff, closes #15).

## What Was Done

Task 1 — replaced `os: [ubuntu-latest, macos-latest]` with `os: [ubuntu-latest, macos-latest, windows-latest]` in all three matrix jobs (clippy-root at ~L46, test-root at ~L78, pyo3-build at ~L103). Nothing else in the file changed:

- `fmt` job remains `runs-on: ubuntu-latest` with no matrix (rustfmt is platform-neutral).
- No `continue-on-error`, no `|| true`, no `if:` guard, no `cargo test --skip` filter, no `fail-fast` change, no `timeout-minutes` bump — the FOUND-01 merge-gate contract (any gate job failing fails the PR) is intact on the new leg.
- Cache keys were already parameterized on `${{ runner.os }}`, so they namespace per OS with zero edits.
- `.github/workflows/performance-regression.yml` untouched — the Windows benchmark baseline remains a deferred phase-04 follow-up.
- `actionlint` is not installed locally; skipped as informational-only per the plan (CI is the authoritative gate).

## Verification Evidence

The plan's automated gate passed pre-commit:

- `grep -c 'os: \[ubuntu-latest, macos-latest, windows-latest\]'` = 3 (all three matrices)
- `grep -c 'windows-latest'` = 3 (no stray occurrences beyond the matrices)
- `grep -c 'runs-on: ubuntu-latest'` = 1 (fmt job only, non-matrix)
- No non-comment line matches `continue-on-error|\|\| true|--skip`
- `git diff HEAD -- .github/workflows/performance-regression.yml` empty
- Diff stat: 1 file changed, 3 insertions(+), 3 deletions(-)

End-to-end proof is the first CI run after push to dev: all three jobs should show a third `windows-latest` leg. Per commit 8f23225's local Windows verification (fmt, root clippy, `cargo test` 23 suites / 0 failures / lib 237 passed, pyo3 clippy), the legs are expected green. Any Windows-leg failure is a genuine finding for issue #15's follow-up and must be reported, not filtered.

## Deviations from Plan

None — plan executed exactly as written.

## Commits

- b514331: `ci: add windows-latest to clippy/test/pyo3 matrices (closes #15)`

The commit message contains "closes #15", so GitHub auto-closes issue #15 when the commit lands on the default branch (dev).

## Self-Check: PASSED

- `.github/workflows/ci.yml` modified and committed (b514331 is HEAD of dev; 3 matrix lines verified)
- No tracked-file deletions in the commit
- Benchmark workflow unchanged; no suppression mechanisms introduced
