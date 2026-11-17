---
phase: quick
plan: 261111-rf2
subsystem: infra
tags: [memmap2, rustsec-2026-0186, security, dependencies, cargo, pyo3]

requires: []
provides:
  - "memmap2 >= 0.9.11 (RUSTSEC-2026-0186 patched floor) required by both crate manifests (^0.9.11)"
  - "Both local lockfiles (Cargo.lock, pyo3/Cargo.lock) resolved to exactly memmap2 0.9.11"
  - "Green root build/test/clippy battery and pyo3 cargo check against the bumped dependency"
affects: [dependencies, security, ci]

actuals:
  tokens: 280
  tasks: 2
  commits: 1
plan_head_before: d68abcb04f134523bf1cde9905005ef0cde02dc6
plan_head_after: cb97c81834831bb5787e7b9cddad5daa9e12c9d5

tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - Cargo.toml
    - pyo3/Cargo.toml
    - Cargo.lock (on disk only — gitignored/untracked by project policy)
    - pyo3/Cargo.lock (on disk only — gitignored/untracked by project policy)

key-decisions:
  - "Pinned exactly 0.9.11 (the advisory floor) via cargo update --precise on both lockfiles, per plan primary path; ^0.9.11 manifest requirement still permits future patch updates"
  - "Commit scoped to the two tracked manifests: both Cargo.lock files are gitignored (.gitignore:6,122) and were never tracked in repo history; force-adding them would override deliberate project policy, so the tracking question is surfaced for human decision instead"
  - "Security floor does not depend on committed lockfiles: CI uses no --locked/--frozen, so every fresh resolution (CI, downstream) honors ^0.9.11"

requirements-completed: []

coverage:
  - id: D1
    description: "Both manifests require memmap2 >= 0.9.11 (Cargo.toml:25 and pyo3/Cargo.toml:35 read memmap2 = \"0.9.11\")"
    verification:
      - kind: other
        ref: "grep -q 'memmap2 = \"0.9.11\"' Cargo.toml && grep -q 'memmap2 = \"0.9.11\"' pyo3/Cargo.toml"
        status: pass
    human_judgment: false
  - id: D2
    description: "Both Cargo.lock files resolve memmap2 to exactly 0.9.11 (was 0.9.9), checksum d1219ed1b7f229ee7104d281dd01d6802fe28bb6e95d292942c4daacdeb798c0"
    verification:
      - kind: other
        ref: "grep -A1 'name = \"memmap2\"' Cargo.lock | grep 'version = \"0.9.11\"' (and pyo3/Cargo.lock variant); cargo update -p memmap2 --precise 0.9.11 [--manifest-path pyo3/Cargo.toml]"
        status: pass
    human_judgment: false
  - id: D3
    description: "Root crate builds, full test suite passes, clippy --all-targets -- -D warnings clean against memmap2 0.9.11"
    verification:
      - kind: integration
        ref: "cargo test (23 binaries: 404 passed, 0 failed, 3 pre-existing ignored)"
        status: pass
      - kind: other
        ref: "cargo build (exit 0); cargo clippy --all-targets -- -D warnings (exit 0)"
        status: pass
    human_judgment: false
  - id: D4
    description: "pyo3 bindings crate type-checks against the bumped core"
    verification:
      - kind: other
        ref: "cargo check --manifest-path pyo3/Cargo.toml (exit 0)"
        status: pass
    human_judgment: false

duration: 11min
completed: 2026-11-11
status: complete
---

# Phase quick Plan 261111-rf2: Bump memmap2 to >=0.9.11 security floor (RUSTSEC-2026-0186) Summary

**memmap2 raised to the RUSTSEC-2026-0186 patched floor (^0.9.11) in both crate manifests, both local lockfiles pinned to exactly 0.9.11, with the full root build/test/clippy battery and pyo3 cargo check green — no source, format, API, or performance change**

## Performance

- **Duration:** 11 min
- **Started:** 2026-11-11T11:56:29Z
- **Completed:** 2026-11-11T12:07:27Z
- **Tasks:** 2
- **Files modified:** 2 committed (Cargo.toml, pyo3/Cargo.toml) + 2 lockfiles refreshed on disk (gitignored/untracked)

## Accomplishments

- Both manifests now require `memmap2 = "0.9.11"` (root Cargo.toml:25, pyo3/Cargo.toml:35), removing the unsound memmap2 < 0.9.11 code (RUSTSEC-2026-0186, INFO/Unsound) from every future resolution on both delivery surfaces (CLI + pyrustkmer).
- Both lockfiles refreshed from vulnerable 0.9.9 to exactly 0.9.11 via `cargo update -p memmap2 --precise 0.9.11` (root and `--manifest-path pyo3/Cargo.toml`); identical registry checksum `d1219ed1…798c0` recorded in both.
- Full verification battery green: `cargo build` exit 0; `cargo test` exit 0 (23 test binaries, 404 passed / 0 failed / 3 pre-existing ignored, incl. 9 doc-tests); `cargo clippy --all-targets -- -D warnings` exit 0; `cargo check --manifest-path pyo3/Cargo.toml` exit 0.
- Diff confined to dependency declarations: zero changes under src/, pyo3/src/, tests/, pyo3/tests/ — the bump is API-transparent (rustkmer calls only MmapOptions::map/map_mut, not the advisory's vulnerable range functions).

## Task Commits

1. **Task 1: Raise the memmap2 floor to 0.9.11 in both manifests and refresh both lockfiles** — `cb97c81` (fix)
2. **Task 2: Verify the bumped dependency across both crates** — verification-only, no commit (no edits)

**Plan metadata:** docs commit handled by the orchestrator (SUMMARY/STATE not committed by this executor, per dispatch constraints).

## Files Created/Modified

- `Cargo.toml` — line 25: `memmap2 = "0.9"` → `memmap2 = "0.9.11"` (committed)
- `pyo3/Cargo.toml` — line 35: `memmap2 = "0.9"` → `memmap2 = "0.9.11"` (committed)
- `Cargo.lock` — memmap2 0.9.9 → 0.9.11 + checksum (on disk; gitignored/untracked, see Deviations)
- `pyo3/Cargo.lock` — memmap2 0.9.9 → 0.9.11 + checksum (on disk; gitignored/untracked, see Deviations)

## Verification Gates

| Gate | Command | Exit | Evidence |
|------|---------|------|----------|
| Manifest + lock + scope | plan verification gate 1 (grep manifests/locks + empty src/tests diff) | PASS | both manifests 0.9.11; both locks 0.9.11; `git diff --name-only -- src pyo3/src tests pyo3/tests` empty |
| Build | `cargo build` | 0 | Finished dev profile in 11.08s |
| Test | `cargo test` | 0 | 23 binaries: 404 passed, 0 failed, 3 ignored (pre-existing); 0 failure markers |
| Clippy | `cargo clippy --all-targets -- -D warnings` | 0 | Finished dev profile in 10.35s |
| pyo3 check | `cargo check --manifest-path pyo3/Cargo.toml` | 0 | Finished dev profile in 21.75s |

Toolchain: cargo 1.101.0-nightly (3960fa69b 2026-10-12). Logs: /tmp/gsd-261111-rf2-verify/{build,test,clippy,pyo3check}.log.

## Decisions Made

- Pinned exactly 0.9.11 (advisory floor) rather than latest 0.9.12, per the plan's surgical-diff rationale; the `^0.9.11` requirement still permits future patch updates.
- Commit scoped to the two tracked manifests after discovering the lockfiles are gitignored and were never tracked (see Deviations). The security objective is fully met without committing locks: the manifest floor governs every fresh resolution, and CI uses no `--locked`/`--frozen`.
- Executed on branch `dev` per the orchestrator's explicit sequential dispatch (#4799; `branching_strategy: "none"`, `quick_branch_template: null`). `gsd_run query git.base-branch --is-protected dev` reports `true` (dev is the default branch), but this was a dispatched position, not drift — no branch switch, no worktree, no protected-ref rewrite, matching the repo's standing quick-task convention.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Lockfiles are gitignored and were never tracked — commit scoped to the two manifests**
- **Found during:** Task 1 (pre-commit scope check)
- **Issue:** The plan (grounded on the codebase map's "Cargo.lock files committed" claim) assumed both lockfiles were tracked deliverables of a 4-file atomic commit. Reality: `.gitignore` ignores `Cargo.lock` at lines 6 and 122, `git ls-files` shows neither lock tracked, `git log --all -- Cargo.lock` is empty (never tracked), and `git show HEAD:Cargo.lock` fails. Staging them as written is impossible without `git add -f`.
- **Fix:** Refreshed both lockfiles on disk to exactly 0.9.11 (the plan's resolution must-haves and threat T-261111-02's update+grep mitigation are satisfied), and committed only the two tracked manifests. Deliberately did NOT `git add -f` the ignored locks: overriding the project's explicit, standing tracking policy is a human decision (Rule 4 class), not an executor auto-fix. The orchestrator's scope constraint ("commit touches only the 4 authorized files") is honored as a subset.
- **Files modified:** commit scope = Cargo.toml, pyo3/Cargo.toml; lockfiles refreshed on disk only
- **Verification:** `git show --stat cb97c81` = 2 files, 2 insertions, 2 deletions; both locks grep 0.9.11; working tree clean except orchestrator-owned STATE.md
- **Committed in:** cb97c81
- **Open question for human:** whether to start tracking Cargo.lock (would require removing the two .gitignore entries and force-adding). Not required for the security floor — advisory only; the project has never tracked locks and CI resolves fresh.

**2. [Rule 3 - Blocking] First `--precise 0.9.11` run resolved 0.9.12 on both lockfiles (index-refresh race)**
- **Found during:** Task 1 (lockfile refresh)
- **Issue:** On nightly cargo 1.101.0, the first `cargo update -p memmap2 --precise 0.9.11` (root and pyo3) exited 0 but reported "Updating memmap2 v0.9.9 -> v0.9.12", concurrent with the crates.io index refresh. Registry index confirms 0.9.11 exists and is NOT yanked.
- **Fix:** Re-ran the identical `--precise 0.9.11` commands after the index settled; both reported "Downgrading memmap2 v0.9.12 -> v0.9.11" and both locks now resolve exactly 0.9.11. The plan's fallback (latest 0.9.x) was NOT needed — the primary exact-floor target was achieved.
- **Files modified:** Cargo.lock, pyo3/Cargo.lock (on disk)
- **Verification:** `grep -A1 'name = "memmap2"'` on both locks → `version = "0.9.11"`, checksum d1219ed1b7f229ee7104d281dd01d6802fe28bb6e95d292942c4daacdeb798c0
- **Committed in:** n/a (lockfiles untracked; see deviation 1)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Security objective fully achieved on both surfaces; commit scope adapted to the repo's actual tracking state. No scope creep — no source file touched, no policy overridden unilaterally.

## Issues Encountered

- Nightly cargo emits manifest-level `unused_dependencies` warnings (root: `inquire`; pyo3: `pyo3-build-config`). These are pre-existing/environmental cargo manifest warnings, not clippy code lints — all four gates exited 0 with `-D warnings`. Out of scope under the 4-file lock; not fixed.
- The `--precise` index-refresh race (deviation 2) — resolved by retry; final state is the plan's exact target.

## Known Stubs

None.

## Threat Flags

None. The bump removes unsound code from the dependency tree (T-261111-01 mitigated); no new network endpoint, auth path, file-access pattern, or trust-boundary schema change was introduced. T-261111-02 mitigated via explicit `--precise` updates + exact-version grep gates on both locks; T-261111-SC satisfied (patch bump of a pre-existing canonical crate, registry checksum enforced and recorded).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both delivery surfaces now require the patched memmap2 floor; ready for any subsequent dependency or security work.
- Advisory (non-blocking): the lockfile-tracking policy question in deviation 1 is the only open item — a human may decide whether committed lockfiles are wanted for reproducibility. The RUSTSEC-2026-0186 floor holds regardless.
- STATE.md / ROADMAP.md updates and the docs commit are handled by the orchestrator per dispatch constraints (quick tasks do not update ROADMAP).

## Self-Check: PASSED

- FOUND: SUMMARY.md (status: complete)
- FOUND: commit cb97c81 (ancestor of HEAD)
- FOUND: root manifest memmap2 = "0.9.11"; pyo3 manifest memmap2 = "0.9.11"
- FOUND: Cargo.lock memmap2 0.9.11; pyo3/Cargo.lock memmap2 0.9.11
- Working tree: only orchestrator-owned STATE.md modification + untracked SUMMARY.md (docs commit handled by orchestrator)

---
*Phase: quick*
*Completed: 2026-11-11*