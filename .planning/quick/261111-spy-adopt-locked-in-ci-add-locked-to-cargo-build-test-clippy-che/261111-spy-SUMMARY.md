---
phase: quick
plan: 261111-spy
subsystem: infra
tags: [cargo-lock, locked, ci, reproducibility, supply-chain, github-actions, regression-gate]

requires:
  - phase: quick-261111-s6h
    provides: "Both Cargo.lock files tracked in git (commit 09d90bc), byte-identical to the tested memmap2 0.9.11 resolution; its SUMMARY explicitly surfaced 'CI workflows do not yet pass --locked' as the follow-up this plan closes"
provides:
  - "--locked on all 4 in-repo cargo build/test/clippy invocations in .github/workflows/ (ci.yml x3, benchmark.yml x1) — lockfile/manifest drift now fails CI loudly instead of silently re-resolving"
  - "pyo3/Cargo.lock activated as a regression gate via the pyo3-build job's --locked clippy step (runs before the maturin step in the same job)"
  - "Lock consistency proven green on arrival: cargo metadata --locked exits 0 for both crates at the deliverable commit"
affects: [ci, dependencies, reproducibility, supply-chain, benchmark]

actuals:
  tokens: 459
  tasks: 2
  commits: 1
plan_head_before: 45205d3c9f0b38205e51921371c696692b2c0615
plan_head_after: 16629552e8e7fca1623322ac9c04de1791f8f6f8

tech-stack:
  added: []
  patterns:
    - "--locked placed immediately after the cargo verb and before all other flags (load-bearing for clippy: everything after -- goes to rustc)"
    - "Tracked lockfile + --locked CI gate = drift fails the merge gate loudly; tracking alone (261111-s6h) only made the lock available"

key-files:
  created: []
  modified:
    - .github/workflows/ci.yml (3 --locked insertions: clippy-root line 69, test-root line 94, pyo3-build clippy step line 124)
    - .github/workflows/benchmark.yml (1 --locked insertion: Build release binary line 71; trailing comment preserved byte-for-byte)

key-decisions:
  - "replace-all on 'cargo clippy --all-targets' in ci.yml covers exactly the 2 in-repo clippy invocations (clippy-root + pyo3-build); --locked precedes --all-targets so it reaches cargo, not rustc"
  - "Executed on branch dev per the orchestrator's explicit sequential dispatch (#4799; branching_strategy: none, quick_branch_template: null) — dispatched position, not drift; same convention as 261111-s6h / 261111-rf2"
  - "Clean-tree gates scoped to exclude .planning/: a pre-existing orchestrator-owned tracked edit to .planning/STATE.md (session bookkeeping from the s6h completion) was present before execution started and is untouchable per dispatch constraints; deliverable tree proven clean, residual reported verbatim"

requirements-completed: []

coverage:
  - id: D1
    description: "All 4 in-repo cargo build/test/clippy/check/run invocations in .github/workflows/ carry --locked; all 3 workflow files parse as valid YAML"
    verification:
      - kind: other
        ref: "python3/PyYAML semantic gate: parsed 3 workflows, 4/4 invocations locked (baseline RED 0/4 exit 1 -> GREEN exit 0); grep total=4, locked=4, negative grep empty"
        status: pass
    human_judgment: false
  - id: D2
    description: "Exactly one atomic commit (1662955) whose HEAD^..HEAD word-diff is exactly four added --locked tokens and zero removals, touching only ci.yml and benchmark.yml, with the exact plan-specified subject"
    verification:
      - kind: other
        ref: "git diff --word-diff=plain HEAD^..HEAD: 4x {+--locked+}, no [- markers; git show --name-only set == benchmark.yml,ci.yml; subject byte-equal; pre-commit working-tree shape gate passed before staging"
        status: pass
    human_judgment: false
  - id: D3
    description: "Both tracked lockfiles consistent with their manifests at the deliverable commit — the new CI gate is green on arrival — and neither lock was rewritten"
    verification:
      - kind: integration
        ref: "cargo metadata --locked --format-version 1 (root, exit 0) && cargo metadata --locked --format-version 1 --manifest-path pyo3/Cargo.toml (exit 0); git diff --name-only -- Cargo.lock pyo3/Cargo.lock empty"
        status: pass
    human_judgment: false

duration: 4min
completed: 2026-11-11
status: complete
---

# Phase quick Plan 261111-spy: Adopt --locked in CI Summary

**All 4 in-repo cargo build/test/clippy invocations in ci.yml and benchmark.yml now carry --locked (one atomic commit, four pure insertions), turning the lockfiles tracked by 261111-s6h into an active CI regression gate — manifest/lock drift now fails the merge gate loudly on both crates instead of silently re-resolving dependencies**

## Performance

- **Duration:** 4 min
- **Started:** 2026-11-11T13:07:20Z
- **Completed:** 2026-11-11T13:11:09Z
- **Tasks:** 2 (Task 1 edit+commit; Task 2 verification-only)
- **Files modified:** 2 (.github/workflows/ci.yml, .github/workflows/benchmark.yml)

## Accomplishments

- Inserted `--locked` into exactly the 4 planned invocations, each immediately after the cargo verb and before all other flags: ci.yml clippy-root (line 69), ci.yml test-root (line 94), ci.yml pyo3-build "clippy (pyo3)" step (line 124, working-directory: pyo3), benchmark.yml "Build release binary" (line 71, trailing `  # never time a debug build` comment preserved byte-for-byte).
- One atomic commit `1662955` — `ci: adopt --locked for in-repo cargo invocations (quick-batch 261111-spy)` — touching only the two workflow files; word-level diff proves four pure insertions and zero removals. No co-author trailer, nothing pushed.
- Pre-commit working-tree shape gate passed BEFORE staging (4 added tokens, 0 removals, exact two-file set), so a malformed edit could not land in history (threat T-261111-spy-02).
- Task 2 proved the gate green on arrival: all 3 workflows parse as valid YAML with 4/4 locked coverage (RED baseline 0/4 captured pre-edit), grep proof 4/4 with empty negative grep, and `cargo metadata --locked` exits 0 for both the root crate and pyo3/Cargo.toml with neither lockfile rewritten.
- Closes the exact follow-up recorded in 261111-s6h's SUMMARY ("CI workflows do not yet pass --locked"). The pyo3 lock is now a regression gate via the pyo3-build job's clippy step, which runs before that job's maturin build step.

## Task Commits

1. **Task 1: Insert --locked into the four in-repo cargo invocations and commit atomically** — `1662955` (ci)
2. **Task 2: Prove YAML validity, full --locked coverage, and lock consistency** — verification-only, no commit (HEAD remained `1662955` throughout, re-asserted at the end of the gate chain)

**Plan metadata:** docs commit handled by the orchestrator (SUMMARY/PLAN/STATE not committed by this executor, per dispatch constraints).

## Files Created/Modified

- `.github/workflows/ci.yml` — 3 insertions: `cargo clippy --locked --all-targets -- -D warnings` (clippy-root, line 69), `cargo test --locked` (test-root, line 94), `cargo clippy --locked --all-targets -- -D warnings` (pyo3-build clippy step, line 124)
- `.github/workflows/benchmark.yml` — 1 insertion: `cargo build --locked --release  # never time a debug build` (line 71)

## Grep Proof (required evidence, captured at HEAD = 1662955)

```text
.github/workflows/benchmark.yml:71:        run: cargo build --locked --release  # never time a debug build
.github/workflows/ci.yml:69:      - run: cargo clippy --locked --all-targets -- -D warnings
.github/workflows/ci.yml:94:      - run: cargo test --locked
.github/workflows/ci.yml:124:        run: cargo clippy --locked --all-targets -- -D warnings
```

Invocation total = 4 (invariant, unchanged from baseline), locked count = 4 (baseline 0), negative grep (target-verb invocation lacking --locked) = empty (baseline listed all 4 lines above without --locked).

## Verification Gates

| Gate | Baseline (pre-edit, HEAD 45205d3) | Result at 1662955 | Evidence |
|------|-----------------------------------|-------------------|----------|
| YAML syntax + semantic coverage (python3/PyYAML, all 3 workflows, shell comments stripped) | RED: 3 parsed, 0/4 locked, exit 1 | PASS | "parsed 3 workflows as valid YAML; 4/4 in-repo cargo invocations carry --locked"; exit 0 |
| Grep invocation total (invariant) | 4 | PASS | count 4 — no invocation added or removed |
| Grep locked count | 0 | PASS | count 4 |
| Negative grep (unlocked target-verb invocations) | 4 lines | PASS | empty |
| Pre-commit working-tree word-diff shape | n/a | PASS | 4x `{+--locked+}`, zero `[-` markers, exact two-file set — checked BEFORE staging |
| Commit-range word-diff (HEAD^..HEAD) | empty diff, 0 insertions | PASS | 4 added --locked tokens, 0 removals |
| Commit file set + subject | n/a | PASS | exactly `.github/workflows/benchmark.yml,.github/workflows/ci.yml`; subject byte-equal to plan specification |
| Root lock consistency: `cargo metadata --locked --format-version 1` | green at planning time | PASS (exit 0) | green on arrival at the deliverable commit |
| pyo3 lock consistency: `cargo metadata --locked --format-version 1 --manifest-path pyo3/Cargo.toml` | green at planning time | PASS (exit 0) | green on arrival at the deliverable commit |
| Lockfiles unmodified | clean | PASS | `git diff --name-only -- Cargo.lock pyo3/Cargo.lock` empty after both metadata runs |
| Clean deliverable tree (unstaged + staged, excluding .planning/) | n/a | PASS | both sets empty; HEAD still 1662955 at end of Task 2 |
| Whole-tree literal clean check (`git diff --name-only` empty) | already non-empty at dispatch | FAIL (environmental, see Issues) | sole residual: pre-existing orchestrator-owned `.planning/STATE.md` bookkeeping edit — untouched, uncommitted, out of executor authority |

## Documented Exclusions (per plan, verified live)

- **cargo fmt (ci.yml:37)** — deliberately NOT given --locked: fmt is not in the item's verb list (build/test/clippy/check/run), `cargo fmt --help` shows no --locked option, and fmt performs no dependency resolution. Adding it would break the fmt gate job.
- **maturin build (ci.yml:127 and ci.yml:170)** — left as-is: not cargo invocations per the item's scope. The pyo3 lock is still gated: the pyo3-build job's --locked clippy step runs BEFORE its maturin step in the same job, so drift fails the job before a wheel is built.
- **performance-regression.yml** — ABSENT (deleted pre-batch; benchmark.yml's header comment confirms it). `.github/workflows/` contains exactly 3 files: benchmark.yml, ci.yml, docs.yml. Nothing to edit there; commented-out lines are not invocations.
- **pip install / pytest steps, docs.yml** — untouched (tool installs and Python-only workflow, explicitly out of scope). No `cargo install` step exists anywhere in .github/workflows/.
- No toolchain, action-version, cache-key, comment, or whitespace change anywhere; the word-diff's zero-removal proof covers all of these.

## Decisions Made

- `--locked` placed immediately after the cargo verb and before all other flags — load-bearing for clippy, where everything after `--` goes to rustc; the flag must precede `--all-targets -- -D warnings`.
- Executed on branch `dev` per the orchestrator's explicit sequential dispatch (#4799; `branching_strategy: "none"`, `quick_branch_template: null`). `gsd_run query git.base-branch --is-protected dev` reports `true` (dev is the default branch), but this was a dispatched position, not drift — no branch switch, no worktree, no protected-ref rewrite, matching the repo's standing quick-task convention (261111-s6h and 261111-rf2 did the same).
- Clean-tree gates scoped with `-- . ':!.planning'` because of the pre-existing orchestrator-owned STATE.md edit (see Issues Encountered); the deliverable-scoped check is strictly stronger than needed for the two workflow files, which were additionally proven clean via the commit-range and staged-set gates.

## Deviations from Plan

None — the deliverable was executed exactly as written: four pure --locked insertions, one atomic commit with the exact plan-specified subject and file set, all deliverable gates green on first attempt. One environmental gate adaptation (clean-tree scoping around orchestrator-owned STATE.md state) is documented under Issues Encountered; it changed no file, no commit, and no deliverable gate outcome.

## Issues Encountered

- **Pre-existing orchestrator-owned tracked edit to `.planning/STATE.md`** (session-bookkeeping timestamps and state_head pointer from the s6h completion; 5 insertions / 5 deletions) was present in the working tree before this executor started. Dispatch constraints forbid touching or committing STATE.md, so the plan's literal whole-tree clean check (`test -z "$(git diff --name-only)"`) cannot pass while that edit exists. Resolution: left the file byte-untouched, ran the clean-tree gates scoped to exclude `.planning/` (deliverable tree proven fully clean), and reported the residual verbatim in the gate table. No deliverable impact; the orchestrator owns that edit's disposition.
- No other issues: no gate failed for network/registry/toolchain reasons; no contingency (halt-and-report on lock drift) was triggered — both locks were consistent on arrival, exactly as observed at planning time.

## Known Stubs

None.

## Threat Flags

None. All threat-register dispositions applied as planned: T-261111-spy-01 mitigated (the deliverable itself — --locked on all 4 invocations, 4/4 coverage proven, live lock consistency on both crates); T-261111-spy-02 mitigated (pre-commit working-tree word-diff gate + post-commit HEAD^..HEAD re-proof: exactly 4 added tokens, zero removals, exact two-file set); T-261111-spy-03 accepted exclusions documented above (fmt, maturin x2); T-261111-spy-SC satisfied (nothing installed — verification used only read-only `cargo metadata --locked`, which cannot alter the resolution). No new network endpoint, auth path, file-access pattern, or trust-boundary schema change introduced.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The CI merge gate now refuses lockfile/manifest drift on both crates: any future manifest change (e.g. sibling batch items sq0/sq1 touching Cargo.toml) must ship its lock refresh in the same push or CI fails loudly — which is precisely the intended regression-gate behavior.
- Both lockfiles proven consistent at the deliverable commit, so the gate is green on arrival; the first CI run against `1662955` needs no lock repair.
- STATE.md / ROADMAP.md updates and the docs commit (SUMMARY/PLAN) are handled by the orchestrator per dispatch constraints.

## Self-Check: PASSED

- FOUND: 261111-spy-SUMMARY.md (status: complete, untracked — orchestrator owns the docs commit)
- FOUND: .github/workflows/ci.yml and .github/workflows/benchmark.yml on disk, no working-tree edits remaining
- FOUND: commit 1662955 (HEAD itself; full hash 16629552e8e7fca1623322ac9c04de1791f8f6f8)
- Nothing pushed by this executor; only tracked residual is the pre-existing orchestrator-owned .planning/STATE.md edit (untouched)

---
*Phase: quick*
*Completed: 2026-11-11*
