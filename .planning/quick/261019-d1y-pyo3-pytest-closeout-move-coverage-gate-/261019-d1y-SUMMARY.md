---
phase: quick-261019-d1y
plan: 01
subsystem: ci
tags: [ci, pytest, coverage, pyo3, github-actions]
status: complete
completed: 2026-10-19
commits:
  - b6ea0ee
  - 31071ab
duration_min: 7
files_modified:
  - pyo3/pyproject.toml
  - .github/workflows/ci.yml
  - docs/guides/testing.md
  - docs/guides/configuration.md
  - docs/guides/development.md
---

# Quick Task 261019-d1y Summary: pyo3 pytest closeout — move coverage gate from addopts to CI

One-liner: pyo3 pytest addopts reduced to `["-v"]` while the unchanged 80% gate moved to a new 3-OS `pyo3-pytest` CI job (maturin build → wheel install → `pytest --cov-fail-under=80`), with six doc lines relocated to point at CI.

## What Was Done

Closes the two still-open STATE.md blockers from the 2026-10-17 pyo3 re-verification:

- **Blocker (a) — local pytest forced through coverage flags:** `pyo3/pyproject.toml` `[tool.pytest.ini_options]` addopts is now exactly `["-v"]` (was 5 `--cov*` flags + `-v`). A plain `pytest --collect-only` run no longer prints the `FAIL Required test coverage of 80% not reached. Total coverage: 0.00%` banner, and venvs without pytest-cov no longer die with `unrecognized arguments`. `[tool.coverage.run]` / `[tool.coverage.report]` sections retained (CI still uses them). An explanatory comment above the new addopts records why the flags are not baked in.
- **Blocker (b) — no pyo3 pytest job in CI:** appended a `pyo3-pytest` job to `.github/workflows/ci.yml`: `name: pyo3 pytest`, 3-OS matrix `[ubuntu-latest, macos-latest, windows-latest]`, `fail-fast: false`, `timeout-minutes: 30`; steps checkout → rust-toolchain(stable) → setup-python 3.11 → pip install maturin/pytest/pytest-cov/numpy → cache (own writable key `${{ runner.os }}-cargo-pyo3-test-`, warm restore prefix `cargo-pyo3-` per CR-04) → `maturin build` (pyo3/) → `pip install --no-index --find-links pyo3/target/wheels pyrustkmer` (glob-free, Windows-safe) → `pytest tests/ --cov=pyrustkmer --cov-report=term-missing --cov-fail-under=80` (pyo3/). The 80% threshold value is unchanged — only relocated. pytest-benchmark and hypothesis deliberately NOT installed (suite imports only stdlib + pytest; verified live during planning).
- **Docs:** six gate-location lines rewritten across three guides — plain local pytest runs flag-free (no `--no-cov` workaround), 80% enforcement lives on the CI `pyo3-pytest` command line, with the shim-measurement honesty note (the gate effectively asserts the freshly built extension imports; broken build/import → 0% → red).

## Task Verify-Gate Results

| Task | Gate | Result |
|---|---|---|
| 1 — addopts strip | TOML parses + 0 `--cov` in pyproject + collect-only emits no coverage footer | PASS (`TOML OK`, `ADDOPTS-SMOKE OK`; 79 tests collected, 0.02s) |
| 2 — CI job | YAML parses + `pyo3-pytest` present + exactly 1 `--cov-fail-under=80` + no `pull_request_target` trigger + exactly 1 `contents: read` + 0 deleted diff lines | PASS (`YAML OK`, `CI-JOB OK`) — see Deviation 1 for the one adapted check form |
| 2 — extra structure assert | parsed job: matrix/fail-fast/timeout, pytest strictly after build+install, gate flags on pytest step, pyo3 working-dirs, no benchmark/hypothesis installs | PASS (`STRUCTURE OK`) |
| 3 — docs | no line pairs `cov` with `addopts` + `pyo3-pytest` named in guides + `fail-under` still documented | PASS (`DOCS OK`) |
| Overall | all three gates re-run green post-commit; tracked diff is exactly the five files in files_modified | PASS |

## Commits

| Commit | Tasks | Content |
|---|---|---|
| `b6ea0ee` | 1+2 (atomic, per plan key_link — gate never absent between local and CI) | `ci(quick-261019-d1y): move pyo3 coverage gate from pytest addopts to new pyo3-pytest CI job` — pyo3/pyproject.toml + .github/workflows/ci.yml (52 insertions, 0 deletions on ci.yml: single append hunk at EOF; triggers, `permissions: contents: read`, and the pyo3-build job byte-identical) |
| `31071ab` | 3 | `docs(quick-261019-d1y): relocate gate-location docs from pytest addopts to CI pyo3-pytest job` — 3 guide files |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 2 verify's `pull_request_target` count check is unsatisfiable as literally written**
- **Found during:** Task 2 verify gate
- **Issue:** The gate asserts `grep -c 'pull_request_target' == 0`, but the count is 1 — from the PRE-EXISTING security comment at ci.yml:22 (`# (NOT \`pull_request_target\`) so untrusted PR code checks out with the...`), which predates this task and itself asserts the safe behavior. Fixing the comment would create a deleted diff line and fail the plan's own append-only check — the two constraints are mutually contradictory against the current file.
- **Fix:** Ran the check in its YAML-key form (`grep -c 'pull_request_target:' == 0` → 0), which distinguishes trigger usage from prose mention. Threat-model T-d1y-01's intent ("no pull_request_target trigger") is fully preserved: trigger-key count is 0, the `on:` block and `permissions:` are outside the diff (verified: the HEAD~2→HEAD ci.yml diff is one append hunk at EOF with 0 deleted lines).
- **Files modified:** none (verify-gate adaptation only)
- **Commit:** n/a

**2. [Rule 3 - Blocking] Sixth cov+addopts doc pairing at testing.md:9**
- **Found during:** Task 3 pre-flight
- **Issue:** The plan names five gate-location spots, but its Task 3 verify gate (`no line containing `cov` may contain `addopts`) applies file-wide. `docs/guides/testing.md:9` ("...80% coverage gate enforced by default `addopts`") would have failed the gate.
- **Fix:** Rewrote line 9 to "...80% coverage gate enforced by the CI `pyo3-pytest` job." — same rewrite pattern as the five named spots.
- **Files modified:** docs/guides/testing.md
- **Commit:** 31071ab

## Post-Push CI Expectation

Local verification is complete; the CI-green proof happens on GitHub after the user pushes:

- Three NEW legs appear and should run green: `pyo3 pytest (ubuntu-latest)`, `pyo3 pytest (macos-latest)`, `pyo3 pytest (windows-latest)`.
- Existing jobs unchanged and still green: `rustfmt`, `clippy (root)` x3, `test (root)` x3, `pyo3 clippy + wheel` x3.
- First run will be slow-ish on cargo compile (cold `-test-` cache key; warm-restored from pyo3-build's `cargo-pyo3-` prefix); subsequent runs warm.
- Known risk documented in the plan: Windows pytest+coverage variance; `fail-fast: false` keeps ubuntu/macos legs informative if windows flakes. Documented fallback (trim matrix to ubuntu+macos) is deferred until flakiness is actually observed.
- Coverage semantics (honesty note): `--cov=pyrustkmer` traces the maturin-generated 4-line `pyrustkmer/__init__.py` shim; the gate effectively asserts "extension built AND imports" — same semantics as before, now preceded by a fresh build every run.

## Notes

- Untouched per plan/constraints: Rust sources, pyo3-build job, coverage threshold value (80), versions, ROADMAP.md.
- Working tree after completion: only the four pre-existing untracked files from before this task (`.coverage`, `.opencode/package-lock.json`, `.planning/INBOX-TRIAGE.md`, `.planning/state.json`) — untouched, out of scope.
- STATE.md blockers section: this task closes the two STILL OPEN items (a) and (b) under the "[LARGELY RESOLVED 2026-10-17] pyo3 test executability" blocker.

## Self-Check: PASSED

- All five files_modified exist and are committed: PASS
- Commit ancestry b6ea0ee, 31071ab in HEAD: PASS (merge-base --is-ancestor)
- ci.yml diff HEAD~2→HEAD: 0 deleted lines, single append hunk: PASS
- addopts is exactly `["-v"]` (pyo3/pyproject.toml:103): PASS
