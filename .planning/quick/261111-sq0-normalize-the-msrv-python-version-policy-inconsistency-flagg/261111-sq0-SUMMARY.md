---
phase: 261111-sq0
plan: 01
subsystem: build-metadata-and-version-policy-docs
status: complete
tags: [msrv, rust-version, python-floor, version-policy, quick-batch]
requires: []
provides:
  - "Manifest-enforced Rust MSRV 1.80 (rust-version in both [package] sections)"
  - "Normalized Python 3.11+ policy across README and all guideline surfaces, aligned to binding requires-python >=3.11"
affects:
  - Cargo.toml
  - pyo3/Cargo.toml
  - README.md
  - CLAUDE.md
  - AGENTS.md
  - docs/dev-guide/claude.md
  - docs/dev-guide/agents.md
  - ".claude/CLAUDE.md (local-only, gitignored — see Deviations)"
tech-stack:
  added: []
  patterns:
    - "rust-version MSRV floor declared in [package]; enforced by cargo at build time"
    - "Docs align TO the binding pyo3/pyproject.toml requires-python, never the reverse"
key-files:
  created: []
  modified:
    - Cargo.toml
    - pyo3/Cargo.toml
    - README.md
    - CLAUDE.md
    - AGENTS.md
    - docs/dev-guide/claude.md
    - docs/dev-guide/agents.md
    - ".claude/CLAUDE.md (on disk only; untracked by project ignore policy)"
decisions:
  - "Option B (user decision, 2026-11-11): .claude/CLAUDE.md is gitignored (.gitignore:149, deliberate agent-local block) — edit applied locally but NOT tracked; no git add -f; plan's 8-file commit scope amended to 7 tracked + 1 local-only"
  - "rust-version inserted immediately after edition = 2021 in both manifests; metadata-only, zero resolution change (lockfiles byte-identical)"
metrics:
  duration: "~14 min (861 s, including checkpoint pause for the Option B decision)"
  completed: 2026-11-11
  tasks: 3
actuals:
  tokens: 3616   # chars/4 over the realized diff 1662955..dd88eb3 (14466 chars)
  tasks: 3
  commits: 3     # measured: git rev-list --count 1662955..HEAD
plan_head_before: 16629552e8e7fca1623322ac9c04de1791f8f6f8
plan_head_after: dd88eb3f12e5cf05a60b88a6e2360fa84b770c7f
task-commits:
  TASK1_COMMIT: 1d639beea50c2bf1f0f49ab2fdf41aa121030e97
  TASK2_COMMIT: 056935d14eb31b97030566fd0a98e9ea9c8a3889
  TASK3_COMMIT: dd88eb3f12e5cf05a60b88a6e2360fa84b770c7f
---

# Phase 261111-sq0 Plan 01: Normalize MSRV / Python Version Policy Summary

**Rust MSRV 1.80 now manifest-enforced via `rust-version = "1.80"` in both `[package]` sections (both `--locked` crate builds green, lockfiles byte-identical), and every current-policy Python floor aligned to the binding `requires-python = ">=3.11"` across README, the guideline mirrors, and the local agent constraint file.**

## What Was Built

### Task 1 — End-to-end MSRV enforcement (tracer)
- Inserted `rust-version = "1.80"` immediately after `edition = "2021"` in `Cargo.toml` and `pyo3/Cargo.toml`. Nothing else changed in either manifest.
- Proven end-to-end: `cargo build --locked` (root) exit 0; `cargo check --locked --manifest-path pyo3/Cargo.toml` exit 0; both tracked lockfiles byte-identical (pre-commit and full-range gates).
- Tracer feedback gate (auto mode): full verify chain re-run end-to-end, green — expanded to Tasks 2-3.

### Task 2 — Primary policy surfaces
- `.claude/CLAUDE.md` (LOCAL-ONLY, see Deviations): all 5 planned edits applied on disk — flagged "MSRV / Python policy inconsistency" constraint replaced by the resolved "Version policy (normalized)" bullet (Python 3.11+ per binding; Rust MSRV 1.80 manifest-enforced); Languages/Runtime/Platform-Requirements floors raised to 3.11+; stale "(3.10+ acceptable for CI/docs)" exception dropped. Lines already at 3.11+ left untouched.
- `README.md` (committed): all 8 planned edits — compatibility note, both bash comments, environment-requirements row, compatibility matrix (3.10 now "❌ 不支持" citing `requires-python >= 3.11`), both install-comparison table cells, and the installation-check snippet (`sys.version_info >= (3, 11)` + matching else-branch message, changed together).

### Task 3 — Guideline mirrors + full audit
- Mechanical floor replacement in current-policy sections only: `CLAUDE.md` (12 lines: 2× 3.8+ → 3.11+, 10× 3.10+ → 3.11+), `AGENTS.md` (2 lines), `docs/dev-guide/claude.md` (11 lines), `docs/dev-guide/agents.md` (2 lines). 27 lines total.
- "## Recent Changes" historical entries byte-identical to base in all four files (verified: 0 changed history lines; all remaining `Python 3.10+` occurrences are Recent Changes records).
- Full item battery re-run with all three hashes: 28/28 gates PASS.

## Commits (one atomic commit per task, staged explicitly by path)

| Task | Commit | Message | Files |
| ---- | ------ | ------- | ----- |
| 1 | `1d639beea50c2bf1f0f49ab2fdf41aa121030e97` | build: declare rust-version 1.80 MSRV (quick-batch 261111-sq0) | Cargo.toml, pyo3/Cargo.toml |
| 2 | `056935d14eb31b97030566fd0a98e9ea9c8a3889` | docs: align Python floor to binding >=3.11 in policy docs (quick-batch 261111-sq0) | README.md (amended per Option B) |
| 3 | `dd88eb3f12e5cf05a60b88a6e2360fa84b770c7f` | docs: normalize Python floors in guideline mirrors (quick-batch 261111-sq0) | CLAUDE.md, AGENTS.md, docs/dev-guide/claude.md, docs/dev-guide/agents.md |

Union of the three commits = exactly the 7 tracked files (full-range gate PASS). No deletions in any commit. SUMMARY.md left uncommitted (orchestrator-owned).

## Verification — 28/28 PASS

| Gate | Result |
| ---- | ------ |
| `rust-version = "1.80"` count: Cargo.toml / pyo3/Cargo.toml | 1 / 1 (baselines 0/0) |
| `cargo build --locked` (root) | exit 0 |
| `cargo check --locked --manifest-path pyo3/Cargo.toml` | exit 0 |
| Lockfiles byte-identical: pre-commit `git diff HEAD` and full-range `1d639be^..dd88eb3` | exit 0 / exit 0 |
| `requires-python = ">=3.11"` in pyo3/pyproject.toml; file untouched full-range | 1 (unchanged); exit 0 |
| .claude/CLAUDE.md: `3\.10` / inconsistency / resolved-policy counts (local) | 0 / 0 / 1 |
| README.md: `3\.10` / `3\.11-3\.12` / `(3, 10)` | 1 (only the rewritten unsupported row) / 4 / 0 |
| CLAUDE.md: `Python 3\.11+` / `Python 3\.10+` | 12 / 3 (Recent Changes only) |
| AGENTS.md: `Python 3\.11+` / `Python 3\.10+` | 2 / 1 (Recent Changes only) |
| docs/dev-guide/claude.md: `Python 3\.11+` / `Python 3\.10+` | 11 / 3 (Recent Changes only) |
| docs/dev-guide/agents.md: `Python 3\.11+` / `Python 3\.10+` | 2 / 1 (Recent Changes only) |
| Per-task commit scope (T1 two manifests; T2 README.md amended; T3 four mirrors) | PASS / PASS / PASS |
| Full-range union == 7 tracked files (Option B amendment) | PASS |
| src/ + pyo3/src/ untouched full-range | exit 0 |
| Clean tree excluding .planning/ and ignored .claude/ | CLEAN |
| Commits measured from ledger (1662955..HEAD) | 3 |

## Deviations from Plan

### 1. [Rule 4 → user decision] .claude/CLAUDE.md is gitignored — Option B local-only handling

- **Found during:** Task 2 commit staging (halted with a blocking-human decision checkpoint before any partial commit).
- **Issue:** The plan assumed `.claude/CLAUDE.md` was tracked (its "baseline at HEAD" gates and the 8-file union gate). In reality `.gitignore` line 149 ignores the entire `.claude/` directory — a deliberate agent-local-tooling ignore block (grouped with `.serena/`, `.spekrit/`, `.specify/`); `git ls-files .claude/` is empty. Satisfying the plan as written would have required `git add -f`, overriding project ignore policy — a Rule 4 policy decision, not auto-fixable.
- **Decision:** User chose **Option B on 2026-11-11**: keep the `.claude/CLAUDE.md` edits on disk (uncommitted, ignored); do NOT force-add; do NOT revert.
- **Amendments applied (user-directed):**
  - Task 2 commit contains exactly `README.md` only; its post-commit scope gate amended to `README.md`.
  - Full-range union gate amended from 8 files to the **7 tracked files**: AGENTS.md, CLAUDE.md, Cargo.toml, README.md, docs/dev-guide/agents.md, docs/dev-guide/claude.md, pyo3/Cargo.toml.
  - Clean-tree gates exclude `.planning/` (orchestrator bookkeeping) and the ignored `.claude/` path.
- **Effect:** The plan's 8-file scope is realized as **7 tracked + 1 local-only**. The local agent constraint file carries the resolved policy on disk immediately; the repo's tracked mirrors (root CLAUDE.md, docs/dev-guide/claude.md) carry the same normalized policy into history via Task 3. pyproject.toml, lockfile, and source-untouched gates unchanged and green.
- **Commits:** Task 2 `056935d`, Task 3 `dd88eb3` (amended gates); Task 1 `1d639be` unaffected.

No other deviations — all edits matched the plan's exact content specifications.

## Preserved Exclusions (verified untouched)

- "## Recent Changes" historical entries in all four mirrors (byte-identical; 0 changed history lines).
- `pyo3/pyproject.toml` `requires-python = ">=3.11"` — the binding constraint, never lowered, byte-identical.
- README line 988 pure-Python stubs row (3.8-3.13, separate subprocess artifact); conda `python=3.11` examples; already-correct Rust 1.80+ statements; README line 1652 (already >=3.11).
- `docs/guides/benchmarking.md` / `docs/guides/testing.md` bench-harness 3.10+ component minimums (stdlib-only, does not import the binding).
- INSTALL.md / USER_GUIDE.md and all other docs verified at planning time as already correct (no-ops).
- Both lockfiles, src/, pyo3/src/ — zero changes across the whole item.

## Notes

- Builds emit pre-existing nightly unused-dependency manifest warnings (root: 2 incl. `inquire`; pyo3: 1 `pyo3-build-config`). Out of scope — owned by sibling item 261111-sq1; both builds exit 0.
- No GSD commands invoked; STATE.md / ROADMAP.md / BATCH.json untouched (orchestrator-owned). No package installs, no source changes, no new trust boundaries (threat model T-sq0-01 mitigations proven by the --locked + lockfile-identity gates; T-sq0-02/T-sq0-SC accepted as documented).
- Known stubs: none introduced (metadata + documentation only). WINDOWS ledger: no open defects to record — the single deviation is user-resolved (Option B), not an open defect; ledger writes skipped per batch constraint (no GSD commands).

## Self-Check: PASSED

- FOUND: Cargo.toml, pyo3/Cargo.toml, .claude/CLAUDE.md, README.md, CLAUDE.md, AGENTS.md, docs/dev-guide/claude.md, docs/dev-guide/agents.md (all 8 on disk)
- FOUND: 1d639beea50c2bf1f0f49ab2fdf41aa121030e97 (ancestor of HEAD)
- FOUND: 056935d14eb31b97030566fd0a98e9ea9c8a3889 (ancestor of HEAD)
- FOUND: dd88eb3f12e5cf05a60b88a6e2360fa84b770c7f (ancestor of HEAD; HEAD == TASK3_COMMIT)
- Commit count measured from ledger: 3 (1662955..dd88eb3); realized diff 7 files, 38 insertions, 36 deletions