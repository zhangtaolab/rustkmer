---
phase: quick
plan: 261111-sq1
subsystem: infra
tags: [cargo, dependencies, supply-chain, lockfile, pyo3, cleanup]

requires:
  - phase: quick-261111-s6h
    provides: tracked Cargo.lock and pyo3/Cargo.lock (commit 09d90bc)
  - phase: quick-261111-sq0
    provides: rust-version = "1.80" MSRV declaration in both manifests (commit 1d639be)
provides:
  - Root manifest without chrono/inquire; pyo3 manifest without the direct pyo3-build-config 0.22 build-dependency
  - Both lockfiles pruned of the removed packages and their orphaned transitives (removal-only, no retained-package version bumps)
affects: [backlog-999.1, pyo3-build, ci, nightly-unused-dependencies]

actuals:
  tokens: 8520
  tasks: 2
  commits: 1
plan_head_before: dd88eb3f12e5cf05a60b88a6e2360fa84b770c7f
plan_head_after: a5eecad6d737cc1db45eb069af3c8b25955da2a0

tech-stack:
  added: []
  patterns:
    - "Removal-only lock refresh: manifest edit + normal cargo build/check, never blanket cargo update"

key-files:
  created:
    - .planning/quick/261111-sq1-clean-up-nightly-cargo-unused-dependencies-manifest-warnings/261111-sq1-SUMMARY.md
  modified:
    - Cargo.toml
    - pyo3/Cargo.toml
    - Cargo.lock
    - pyo3/Cargo.lock

key-decisions:
  - "All three flagged dependencies removed: live re-grep at HEAD dd88eb3 confirmed zero usage (true positives, not false positives)"
  - "Lock diff's 29 added lines proven to be dependency-reference rewrites (unqualification after duplicate versions were orphaned), not version bumps — (name,version) pair set after is a strict subset of before in both locks"
  - "cargo clippy --all-targets -- -D warnings failure (5x incompatible_msrv) REPORTED, not fixed: pre-existing at HEAD^ via sq0's rust-version=1.80 (1d639be) + nightly clippy; scope locked to the four manifest/lock files"

requirements-completed: []

coverage:
  - id: D1
    description: "chrono and inquire removed from root Cargo.toml and pruned from both lockfiles with zero usage proven"
    verification:
      - kind: other
        ref: "grep -rn --include='*.rs' -E 'chrono|inquire' src/ tests/ pyo3/src/ examples/ (exit 1, zero hits at HEAD dd88eb3)"
        status: pass
      - kind: other
        ref: "Task 1 automated gate: manifest/lock grep counts 1->0 for chrono and inquire in both locks"
        status: pass
      - kind: integration
        ref: "cargo build && cargo test (404 passed, 0 failed, 3 ignored, 23 binaries)"
        status: pass
    human_judgment: false
  - id: D2
    description: "pyo3-build-config 0.22 direct build-dependency removed; 0.22.6 pruned from pyo3/Cargo.lock; pyo3's internal 0.27.2 build-config retained"
    verification:
      - kind: other
        ref: "pyo3/build.rs read in full: only cargo:rerun-if-env-changed=PYO3_BUILD_CONFIG, never references pyo3_build_config; grep pyo3_build_config pyo3/ --include='*.rs' zero hits"
        status: pass
      - kind: other
        ref: "grep -A1 '^name = \"pyo3-build-config\"' pyo3/Cargo.lock -> only version = \"0.27.2\" remains"
        status: pass
      - kind: integration
        ref: "cargo check --manifest-path pyo3/Cargo.toml (exit 0)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Lock refresh is removal-only: no retained package changed version; commit confined to exactly the four deliverable files"
    verification:
      - kind: other
        ref: "LC_ALL=C comm -13 of sorted (name,version) pairs HEAD vs working tree: empty for both locks; zero added 'version =' lines in lock diff"
        status: pass
      - kind: other
        ref: "git diff --name-only HEAD^..HEAD == Cargo.lock,Cargo.toml,pyo3/Cargo.lock,pyo3/Cargo.toml (a5eecad)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Post-commit verification battery green on both crates"
    verification:
      - kind: integration
        ref: "cargo build (exit 0); cargo test (exit 0); cargo check --manifest-path pyo3/Cargo.toml (exit 0)"
        status: pass
      - kind: other
        ref: "cargo clippy --all-targets -- -D warnings (exit 101: 5 pre-existing incompatible_msrv errors, proven unrelated — see Reported Pre-existing Issue)"
        status: fail
    human_judgment: true
    rationale: "The clippy gate fails for a pre-existing cross-item reason (sq0's MSRV 1.80 declaration vs is_multiple_of stabilized in 1.87, nightly clippy). Fixing it requires either source edits or an MSRV policy decision, both outside this item's four-file scope lock — needs orchestrator/user triage."

duration: 7.5 min
completed: 2026-11-11
status: complete
---

# Quick 261111-sq1: Remove unused deps chrono, inquire, pyo3-build-config Summary

**Removed three proven-unused dependencies (chrono, inquire from the root crate; pyo3-build-config 0.22 from the PyO3 build-deps), pruning 37/38 package entries from the two tracked lockfiles with a removal-only diff and a green build/test/check battery — one atomic four-file commit `a5eecad`.**

## Performance

- **Duration:** ~7.5 min
- **Started:** 2026-11-11T13:33:43Z
- **Completed:** 2026-11-11T13:41:12Z
- **Tasks:** 2 (Task 1 removal+commit; Task 2 verification-only, no commit)
- **Files modified:** 4 (Cargo.toml, pyo3/Cargo.toml, Cargo.lock, pyo3/Cargo.lock)

## Accomplishments

- Root `Cargo.toml`: deleted `chrono = { version = "0.4", features = ["serde"] }` + its orphaned comment, and `inquire = "0.7"` + its orphaned comment. Nothing else touched.
- `pyo3/Cargo.toml`: deleted `pyo3-build-config = "0.22"` and the now-empty `[build-dependencies]` section header. Nothing else touched.
- Both lockfiles refreshed via normal `cargo build` / `cargo check --manifest-path pyo3/Cargo.toml` (no blanket `cargo update`): chrono 0.4.43, inquire 0.7.5, and 35 orphaned transitives pruned from `Cargo.lock`; the same set plus pyo3-build-config 0.22.6 and target-lexicon 0.12.16 pruned from `pyo3/Cargo.lock`. pyo3's internal **pyo3-build-config 0.27.2 remains** (with target-lexicon 0.13.4).
- Removal-only diff proven: the post-resolution (name, version) pair set is a strict subset of the pre-resolution set in both locks; zero added `version =` lines. The diff's 29 added lines are all dependency-reference rewrites (cargo unqualifies `name version` references when a duplicate version becomes orphaned — e.g. `bitflags`, `unicode-width`, `windows-targets`, `pyo3-build-config`, `target-lexicon`).
- ONE atomic code commit `a5eecad` touches exactly the four deliverable files; no src/, pyo3/src/, tests/, or pyo3/tests/ change — no .rkdb format, public API, or performance change. Working tree clean of deliverable edits after commit and after the battery.

## Task Commits

1. **Task 1: Remove the three unused dependencies and refresh both lockfiles** — `a5eecad` (build)
2. **Task 2: Verify both crates across the full build/test/lint/check battery** — no commit (verification-only, per plan)

SUMMARY.md itself is left UNCOMMITTED for the orchestrator (docs artifacts are committed separately). STATE.md, ROADMAP.md, BATCH.json untouched.

## Per-Dependency Usage Evidence (re-confirmed live at HEAD dd88eb3 before removal)

| Dependency | Declaration (pre-removal) | Evidence of zero usage |
|---|---|---|
| `chrono` (root) | `Cargo.toml` `chrono = { version = "0.4", features = ["serde"] }` under "# Date/time handling for metadata" | `grep -rn --include='*.rs' chrono src/ tests/ pyo3/src/ examples/` → zero hits. `src/core/metadata.rs:6` uses `std::time::{SystemTime, UNIX_EPOCH}`; `update_timestamp()` (lines 306–308) computes timestamps via `SystemTime::now().duration_since(UNIX_EPOCH)` — the CLAUDE.md "chrono for metadata timestamps" note is stale. No root build.rs exists. |
| `inquire` (root) | `Cargo.toml` `inquire = "0.7"` under "# Interactive file selection" | Same repo-wide `.rs` grep → zero hits. The CLAUDE.md "inquire for interactive file selection" note is stale. |
| `pyo3-build-config` (pyo3 build-dep) | `pyo3/Cargo.toml` `[build-dependencies]` sole entry `pyo3-build-config = "0.22"` | `pyo3/build.rs` read in full: only `println!("cargo:rerun-if-env-changed=PYO3_BUILD_CONFIG")` — never references `pyo3_build_config`. `grep -rn pyo3_build_config pyo3/ --include='*.rs'` → zero hits. pyo3 0.27.2 carries its OWN internal pyo3-build-config 0.27.2 for its build script; removing the direct 0.22 declaration does not affect it (0.27.2 verified still present in pyo3/Cargo.lock post-refresh). |

Negative-grep baselines observed live before removal (all matched the plan): root manifest chrono=1, inquire=1; pyo3 manifest pyo3-build-config=1; root lock chrono=1, inquire=1, pyo3-build-config=0; pyo3 lock chrono=1, inquire=1, 0.22.6=1, 0.27.2=1. All post-removal gates read 0 (except 0.27.2, which stays 1).

## Gate Results

| Gate | Result |
|---|---|
| Task 1: manifest greps (chrono/inquire/pyo3-build-config = 0, comments excluded) | PASS |
| Task 1: lock greps (chrono/inquire = 0 in both locks; 0.22.6 = 0 in pyo3 lock) | PASS |
| Task 1: lock diff removal-only, no retained-package version bump (subset proof + 0 added `version =` lines) | PASS |
| Task 1: commit-range gate — HEAD^..HEAD is exactly Cargo.lock, Cargo.toml, pyo3/Cargo.lock, pyo3/Cargo.toml | PASS |
| Task 1: working tree clean of deliverable edits after commit | PASS |
| Task 2: `cargo build` | PASS (exit 0) |
| Task 2: `cargo test` | PASS (exit 0; 404 passed, 0 failed, 3 ignored across 23 test binaries; the 3 ignored are pre-existing) |
| Task 2: `cargo clippy --all-targets -- -D warnings` | **FAIL (exit 101) — pre-existing, unrelated to the removals; reported per plan, not fixed** |
| Task 2: `cargo check --manifest-path pyo3/Cargo.toml` | PASS (exit 0) |
| Task 2: working tree clean of deliverable edits after battery | PASS |

## Reported Pre-existing Issue (NOT caused by this change — needs triage outside this item)

`cargo clippy --all-targets -- -D warnings` fails with 5 × `clippy::incompatible_msrv` errors: `u64/usize::is_multiple_of` is stable since Rust **1.87**, but the declared MSRV is **1.80**:

- `src/cli/commands/dump.rs:169`
- `src/database/index.rs:106`
- `src/database/prefix_cache_merge.rs:599` and `:1385`
- `src/hash/overflow.rs:71`

**Proof it is pre-existing at HEAD^ (dd88eb3):**
1. This commit's diff has ZERO source changes (`git diff HEAD^..HEAD -- src/ pyo3/src/ tests/ pyo3/tests/` is empty).
2. `rust-version = "1.80"` was already present in BOTH manifests at HEAD^ — introduced by sibling sq0's commit `1d639be` ("build: declare rust-version 1.80 MSRV").
3. All five flagged source lines are byte-identical at HEAD^.
4. The `incompatible_msrv` lint's inputs (source text, declared MSRV, toolchain cargo/rustc 1.101.0-nightly) are therefore identical before and after this commit; removing three zero-usage dependencies cannot affect it. `cargo build` and `cargo test` are green, proving the removals are compilation-transparent.

**Root cause:** cross-item interaction — sq0's MSRV declaration + pre-existing `is_multiple_of` call sites + nightly clippy's `incompatible_msrv` lint. Resolution options (for the orchestrator/user, outside this item's scope lock): replace the five `is_multiple_of(n)` calls with `% n == 0` (MSRV-1.80-compatible), or raise the declared MSRV to ≥1.87, or allow the lint. Per the plan's Task 2 contract ("REPORT it rather than editing unrelated source to force green"), no source was touched.

## Backlog 999.1 Re-add Caveat (REQUIRED carry-forward)

STATE.md backlog **999.1** (from the 2026-10-09 Phase 03 UAT note): pyo3 0.27 may need `pyo3/build.rs` to call `pyo3_build_config::add_extension_module_link_args()`. That work is deferred and NOT present in build.rs today — which is exactly why removing the direct build-dependency is correct now. **If/when that link-args work lands, `pyo3-build-config` MUST be re-added as a `[build-dependencies]` entry in `pyo3/Cargo.toml`** (at a version compatible with pyo3 0.27, i.e. the 0.27 series, not the removed 0.22). Removal does not affect pyo3's own internal pyo3-build-config 0.27.2, which remains in pyo3/Cargo.lock.

## Decisions Made

- All three dependencies removed (plan rule: "remove only if genuinely unused"): live re-grep at current HEAD confirmed the planning-time zero-usage finding for each.
- Lock refresh via manifest edit + normal build/check only; no `cargo update` of any kind. The 29 added diff lines were investigated before committing and proven to be reference rewrites, not version bumps (strict-subset check on (name, version) pairs, C collation).
- Clippy failure reported rather than fixed, per the plan's explicit Task 2 instruction and the four-file scope lock.

## Deviations from Plan

None — plan executed exactly as written, including its prescribed report-don't-fix branch for the unrelated clippy failure. (Line numbers in the plan were planning-time; sq0's rust-version insertion shifted them by one — edits were matched by content, as the plan's substance requires.)

## Issues Encountered

- Initial subset check reported a spurious `winapi-util 0.1.11` difference: `comm` ran in the default locale against `LC_ALL=C sort` output. Re-ran with `LC_ALL=C comm` → empty after-only set; winapi-util confirmed retained unchanged (1→1 entry, same version). Verification artifact, not a deliverable issue.
- The clippy gate failure described above (pre-existing, reported).

## Next Phase Readiness

- The nightly `unused_dependencies` warnings for these three declarations are resolved; dependency tree and supply-chain surface shrink on both delivery surfaces.
- OPEN for orchestrator triage: the 5 `incompatible_msrv` clippy errors block any `-D warnings` gate on nightly until the MSRV/`is_multiple_of` interaction is resolved (belongs to sq0's MSRV scope or the 261111-spz triage item, not this one).
- Backlog 999.1 caveat above must travel with any future pyo3 build.rs link-args work.

## Self-Check: PASSED

- All four deliverable files exist and are committed in `a5eecad` (verified ancestor of HEAD; commit stat shows exactly the four files, 29 insertions / 719 deletions).
- SUMMARY.md exists at the required path and is UNTRACKED (left uncommitted for the orchestrator).
- Working tree clean of deliverable edits after both the commit and the full battery.