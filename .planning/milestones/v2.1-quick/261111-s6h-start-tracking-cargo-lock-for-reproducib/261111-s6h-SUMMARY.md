---
phase: quick
plan: 261111-s6h
subsystem: infra
tags: [cargo-lock, reproducibility, gitignore, supply-chain, rustsec-2026-0186, memmap2, ci]

requires:
  - phase: quick-261111-rf2
    provides: "Both lockfiles resolved to exactly memmap2 0.9.11 (RUSTSEC-2026-0186 floor), fully tested (build + full test suite + clippy) at cb97c81"
provides:
  - "Cargo.lock and pyo3/Cargo.lock tracked in git, byte-identical to the tested memmap2 0.9.11 resolution (SHA-256 pinned)"
  - ".gitignore no longer ignores Cargo.lock at any depth; no ignore source excludes either lockfile"
  - "--locked consistency proven on both crates (root cargo build --locked, pyo3 cargo check --locked)"
affects: [ci, dependencies, reproducibility, supply-chain]

actuals:
  tokens: 31147
  tasks: 2
  commits: 1
plan_head_before: 815d2596ccfc6c82f57e127becf2dc5a9c41649f
plan_head_after: 09d90bca2081909461758571d65330248e612cd0

tech-stack:
  added: []
  patterns:
    - "Lockfiles tracked byte-identical to the tested resolution; --locked gates prove lock/manifest consistency before the tracking commit lands"

key-files:
  created:
    - Cargo.lock (newly tracked; 2386 lines, memmap2 0.9.11)
    - pyo3/Cargo.lock (newly tracked; 2254 lines, memmap2 0.9.11)
  modified:
    - .gitignore (two bare Cargo.lock lines removed: former lines 6 and 122)

key-decisions:
  - "Deleted BOTH duplicate blanket Cargo.lock entries (former lines 6 and 122) by content neighborhood; no negation pattern added — post-edit check-ignore against all ignore sources confirms neither lock is excluded"
  - "Plain git add (no -f) so a residual ignore rule could not be masked; add succeeding is itself part of the proof (threat T-261111-s6h-02)"
  - "Committed the locks byte-identical to the planning-time pins (SHA-256 verified pre- and post-commit); no cargo update, no re-resolution, no dependency change"
  - "Executed on branch dev per the orchestrator's explicit sequential dispatch (#4799; branching_strategy: none, quick_branch_template: null) — dispatched position, not drift"

requirements-completed: []

coverage:
  - id: D1
    description: ".gitignore no longer ignores Cargo.lock at any depth; no ignore source (nested .gitignore, .git/info/exclude, global excludes) excludes either lockfile"
    verification:
      - kind: other
        ref: "test \"$(grep -v '^#' .gitignore | grep -c '^Cargo\\.lock$')\" = 0 && ! git check-ignore -q Cargo.lock && ! git check-ignore -q pyo3/Cargo.lock"
        status: pass
    human_judgment: false
  - id: D2
    description: "Both lockfiles tracked in HEAD, byte-identical to the planning-time tested resolution (Cargo.lock sha256 804d9fe6…0edad1, pyo3/Cargo.lock sha256 53f49890…3ca445), still resolving memmap2 0.9.11"
    verification:
      - kind: other
        ref: "git cat-file -e HEAD:Cargo.lock && git cat-file -e HEAD:pyo3/Cargo.lock && git diff --exit-code HEAD -- Cargo.lock pyo3/Cargo.lock && shasum -a 256 -c (both OK) && grep memmap2 version gates (both 0.9.11)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Both committed lockfiles are consistent with their manifests: root cargo build --locked and cargo check --locked --manifest-path pyo3/Cargo.toml succeed without cargo rewriting either lock"
    verification:
      - kind: integration
        ref: "cargo build --locked (exit 0) && cargo check --locked --manifest-path pyo3/Cargo.toml (exit 0); git diff --name-only -- Cargo.lock pyo3/Cargo.lock empty after both"
        status: pass
    human_judgment: false
  - id: D4
    description: "Exactly one atomic commit (09d90bc) touching only .gitignore, Cargo.lock, pyo3/Cargo.lock — no source, CI, manifest, or documentation change; no co-author trailer; nothing pushed"
    verification:
      - kind: other
        ref: "git show --name-only --format= HEAD sorted set == .gitignore,Cargo.lock,pyo3/Cargo.lock; git show --stat = 3 files, 4640 insertions, 2 deletions"
        status: pass
    human_judgment: false

duration: 3min
completed: 2026-11-11
status: complete
---

# Phase quick Plan 261111-s6h: Start tracking Cargo.lock for reproducible builds Summary

**Both Cargo.lock files now tracked in git byte-identical to the fully-tested memmap2 0.9.11 resolution (RUSTSEC-2026-0186 floor), with both blanket ignore entries removed and --locked consistency proven on root and pyo3 — fresh clones now resolve the exact tested dependency set**

## Performance

- **Duration:** 3 min
- **Started:** 2026-11-11T12:29:50Z
- **Completed:** 2026-11-11T12:32:34Z
- **Tasks:** 2
- **Files modified:** 3 (.gitignore modified; Cargo.lock and pyo3/Cargo.lock newly tracked)

## Accomplishments

- Removed both duplicate bare `Cargo.lock` ignore entries from `.gitignore` (former line 6 in the first Rust-artifacts block, former line 122 in the second), matched by content neighborhood. No other line touched; no negation pattern needed — `git check-ignore -q` now exits non-zero for each lockfile against ALL ignore sources.
- Tracked `Cargo.lock` (2386 lines) and `pyo3/Cargo.lock` (2254 lines) in one atomic commit `09d90bc`, byte-identical to the planning-time SHA-256 pins — the exact resolution produced and fully tested by quick task 261111-rf2 (cb97c81). No `cargo update`, no re-resolution, no dependency version change; both locks still resolve memmap2 0.9.11.
- Proved lock/manifest consistency before committing: `cargo build --locked` (root) and `cargo check --locked --manifest-path pyo3/Cargo.toml` both exit 0, and neither lock was rewritten by the builds.
- Plain `git add` (no `-f`) succeeded — itself proof that no residual ignore rule masks either lockfile (threat T-261111-s6h-02 mitigation).
- Closes the open question raised by 261111-rf2's deviation 1: the user decided to track the locks; `.claude/CLAUDE.md`'s standing claim "Cargo.lock files committed" is now true (no doc edit needed or made).

## Task Commits

1. **Task 1: Remove both Cargo.lock ignore entries and stage the three deliverable files** — staged only, no commit (by design: Task 2 commits only after the --locked gates pass)
2. **Task 2: Prove --locked consistency on both crates, then commit the three files atomically** — `09d90bc` (build)

**Plan metadata:** docs commit handled by the orchestrator (SUMMARY/STATE not committed by this executor, per dispatch constraints).

## Files Created/Modified

- `.gitignore` — deleted the two bare `Cargo.lock` lines (former lines 6 and 122); diff is exactly 2 deletions, nothing else
- `Cargo.lock` — newly tracked (2386 lines); sha256 `804d9fe624abc9b4468d7876b5e2c496bc38c7e58557037f5365a6e50f0edad1`; memmap2 0.9.11
- `pyo3/Cargo.lock` — newly tracked (2254 lines); sha256 `53f498903c32fbacd2e73ed375b69e23707465363ed0e46d19d755e1383ca445`; memmap2 0.9.11

## Verification Gates

| Gate | Command | Exit | Evidence |
|------|---------|------|----------|
| Ignore removal | `grep -v '^#' .gitignore \| grep -c '^Cargo\.lock$'` | PASS | count 2 at HEAD → 0 after Task 1 |
| Ignore sources | `git check-ignore -q Cargo.lock` / `pyo3/Cargo.lock` (per-path) | PASS | both exited 0 (ignored) at HEAD → both non-zero after; re-verified post-commit |
| Tracking | `git ls-files --error-unmatch` + `git cat-file -e HEAD:` | PASS | untracked/absent (128) at HEAD → both in index after staging, both blobs in HEAD after commit |
| Root consistency | `cargo build --locked` | 0 | Finished dev profile in 0.10s (warm cache); re-run in post-commit chain also 0 |
| pyo3 consistency | `cargo check --locked --manifest-path pyo3/Cargo.toml` | 0 | Finished dev profile in 0.06s (warm cache); re-run in post-commit chain also 0 |
| Locks untouched | `git diff --name-only -- Cargo.lock pyo3/Cargo.lock` | PASS | empty after both builds |
| Atomicity | staged set + `git show --name-only --format= HEAD` | PASS | both exactly `.gitignore,Cargo.lock,pyo3/Cargo.lock`; 3 files, 4640 insertions(+), 2 deletions(-) |
| Byte identity | `git diff --exit-code HEAD -- locks` + `shasum -a 256 -c` checklist | PASS | committed == on-disk == planning-time pins (both `OK`) |
| memmap2 invariant | `grep -A1 'name = "memmap2"'` on both locks | PASS | both `version = "0.9.11"` |

Toolchain: cargo 1.101.0-nightly (3960fa69b 2026-10-12), rustc 1.101.0-nightly (07e526db9 2026-10-19). Full test suite / clippy deliberately NOT re-run (out of scope per plan — the identical resolution passed them in 261111-rf2).

## Decisions Made

- Deleted both blanket entries rather than adding a negation pattern: with both gone, no remaining pattern matches either lockfile (verified live against all ignore sources, including nested .gitignore files, .git/info/exclude, and global excludes).
- Used plain `git add` (never `-f`) so a residual ignore rule could not be masked — add succeeding is part of the proof chain for threat T-261111-s6h-02.
- Committed the locks exactly as on disk (SHA-256 pinned pre-commit and re-verified post-commit); no `cargo update` or any lock rewrite at any point.
- Executed on branch `dev` per the orchestrator's explicit sequential dispatch (#4799; `branching_strategy: "none"`, `quick_branch_template: null`). `gsd_run query git.base-branch --is-protected dev` reports `true` (dev is the default branch), but this was a dispatched position, not drift — no branch switch, no worktree, no protected-ref rewrite, matching the repo's standing quick-task convention (261111-rf2 did the same).

## Deviations from Plan

None - plan executed exactly as written. Both tasks ran in order, all gates green on first attempt, one atomic commit with the exact plan-specified message and no co-author trailer.

## Issues Encountered

- Nightly cargo emits pre-existing manifest-level `unused_dependencies` warnings (root: `chrono`, `inquire`; pyo3: `pyo3-build-config`). These are environmental cargo manifest lints, not errors — both --locked gates exited 0. Out of scope under the 3-file lock; not fixed (same observation as 261111-rf2).

## Known Stubs

None.

## Threat Flags

None. All three threat-register dispositions were applied as planned: T-261111-s6h-01 mitigated (locks tracked byte-identical to the tested resolution, --locked consistency proven on both crates); T-261111-s6h-02 mitigated (both entries deleted, plain add, per-path check-ignore gates, exact staged/commit file-set proofs, HEAD blob existence); T-261111-s6h-SC satisfied (no new packages introduced — no install, no cargo update, no resolution change; --locked forbids alteration and cargo enforces the registry checksums already recorded in both locks). No new network endpoint, auth path, file-access pattern, or trust-boundary schema change was introduced.

## Out-of-Scope Follow-Up (surface, not implemented)

**CI workflows do not yet pass `--locked`.** Now that both lockfiles are tracked, CI cargo invocations (`.github/workflows/ci.yml` and siblings) could adopt `--locked` to make reproducibility a regression gate — a fresh CI resolution that drifts from the committed lock would then fail loudly instead of silently building a different dependency set. This is a separate decision (it changes CI behavior on every workflow that builds Rust) and is deliberately NOT implemented here. Propose it as a separate quick task.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Fresh clones and CI now resolve the exact tested dependency set, including the memmap2 0.9.11 RUSTSEC-2026-0186 security floor; the supply-chain drift window left open by 261111-rf2 is closed.
- The only open item is the advisory CI `--locked` adoption follow-up above (non-blocking).
- STATE.md / ROADMAP.md updates and the docs commit are handled by the orchestrator per dispatch constraints (quick tasks do not update ROADMAP).

## Self-Check: PASSED

- FOUND: SUMMARY.md (status: complete)
- FOUND: .gitignore, Cargo.lock, pyo3/Cargo.lock on disk
- FOUND: commit 09d90bc (ancestor of HEAD); HEAD:Cargo.lock and HEAD:pyo3/Cargo.lock blobs present
- Working tree: only the untracked SUMMARY.md (docs commit handled by orchestrator per dispatch constraints)

---
*Phase: quick*
*Completed: 2026-11-11*
