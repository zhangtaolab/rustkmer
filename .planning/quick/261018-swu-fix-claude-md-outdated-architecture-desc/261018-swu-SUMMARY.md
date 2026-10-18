---
phase: quick-261018-swu
plan: 01
subsystem: docs-context
tags: [claude-md, architecture-docs, counter, threading]
requires:
  - "src/hash/table.rs CounterTable::{Dense,Wide} DashMap design (plans 02-02/03-06)"
  - "src/cli/commands/count.rs chunked rayon par_iter + resolve_thread_count (plans 02-01/02-02)"
provides:
  - ".claude/CLAUDE.md architecture/stack blocks that match src/ ground truth (no lock-guarded-counter or sequential-counting claims)"
affects:
  - "Agent-loaded project context only; no code, format, or API surface touched"
tech-stack:
  added: []
  patterns: []
key-files:
  created: []
  modified:
    - .claude/CLAUDE.md
decisions:
  - "Target file is gitignored (.gitignore:146 `.claude/`) and untracked — edits left uncommitted on purpose; no `git add -f` (force-tracking a deliberately-ignored path is a user policy decision, #3678 regression class)"
metrics:
  duration: "~5 min"
  completed: 2026-10-18
actuals:
  tokens: 750      # chars/4 over the realized diff (~1865 inserted + ~1120 deleted chars across 9 lines)
  tasks: 2
  commits: 0       # MEASURED: git rev-list --count 219c48a..HEAD == 0 — see Deviations; sole target file is gitignored
plan_head_before: 219c48a698997986052c3614b17aba35f5de9500
plan_head_after: 219c48a698997986052c3614b17aba35f5de9500
status: complete
---

# Phase quick-261018-swu Plan 01: Fix .claude/CLAUDE.md outdated architecture description Summary

One-liner: replaced the two verified-false claims in `.claude/CLAUDE.md` (lock-guarded HashMap counter; sequential single-worker counting) with the real sharded `CounterTable` dense/wide DashMap design and the chunked-rayon four-tier thread precedence, plus the adjacent dashmap/hashbrown stack wording — 9 lines changed, everything else byte-identical.

## What Was Done

All seven plan-mandated corrections landed as scoped single-line Edits (final line numbers after the +1-line stack insertion):

| # | Location (was → is) | Correction |
|---|---------------------|------------|
| 1 | Component Responsibilities row (262 → 263) | KmerCounter described as sharded `dashmap::DashMap` behind private `CounterTable`: `Dense(DashMap<u64, u32>)` k ≤ 32 / `Wide(DashMap<u128, u32>)` 33–64, u128-keyed public API; 3-cell row structure preserved |
| 2 | Pattern Overview (275 → 276) | "an in-memory `HashMap`" → "an in-memory sharded concurrent map (`CounterTable`: dense `DashMap<u64, u32>` / wide `DashMap<u128, u32>`)" |
| 3 | Data Flow state bullet (312 → 313) | lock-wrapped-map parenthetical → sharded `CounterTable` with DashMap interior mutability + atomics |
| 4 | Key Abstractions Examples pin (322 → 323) | stale `src/hash/table.rs:14` → `src/hash/table.rs:37` (the CounterTable enum; verified against source) |
| 5 | Key Abstractions Pattern (323 → 324) | "thread-safe wrapper around HashMap" → concurrent counter over `CounterTable`, width chosen at `KmerCounter::new`, hidden behind u128 public API |
| 6 | Stack Key Dependencies (66 → 66+67) | new line: `dashmap` 6.2.1 concurrent sharded map for the counting table, pins `hashbrown` ^0.14.5; hashbrown rescoped to non-counter uses (in-memory merge accumulator) |
| 7 | Threading constraint (348 → 349) | whole bullet replaced: chunked `CHUNK_SIZE` (4096-record) rayon `par_iter` counting + precedence `--threads` > `RUSTKMER_THREADS` > `RAYON_NUM_THREADS` > all cores (`resolve_thread_count`, count.rs:787–847) |
| 8 | Domain-layer Depends-on (294 → 295) | `dashmap` appended to the enumerated external crates (placed before `hashbrown`, mirroring the stack-block ordering) |

Ground truth spot-checked before editing: `CounterTable` enum at `src/hash/table.rs:37-42`, `CHUNK_SIZE: usize = 4096` at `count.rs:30`, `resolve_thread_count` at `:836` with precedence docs at `:789`/`:827`, `dashmap = "6.2.1"` at `Cargo.toml:61`.

## Verification

- Task 1 automated gate: **TASK1-PASS** (0 × `parking_lot::RwLock`, 0 × `num_threads = 1`, 4 × `DashMap<u64, u32>`, `RUSTKMER_THREADS` present, `CHUNK_SIZE` present, 14 GSD markers, KmerCounter row still NF==5).
- Task 2 automated gate: **TASK2-PASS** (`dashmap` ≥ 2, `dashmap` 6.2.1 line present, stale literals 0, 14 GSD markers).
- Final full-file sweep (re-read, 402 lines): no remaining line describes the counter as lock-guarded or counting as sequential. The one surviving `RwLock` mention (line 74) is the `ConfigManager` parking_lot line — correct, untouched.
- File integrity: 401 → 402 lines (exactly +1 from the dashmap insertion), trailing newline preserved, all 14 GSD markers intact, every non-targeted line byte-identical (verified by full re-read against the pre-edit capture).

## Deviations from Plan

### Commit deviation — target file is gitignored and untracked (blocking for the commit steps only)

- **Found during:** Task 1 commit step.
- **Issue:** The plan's sole artifact `.claude/CLAUDE.md` is ignored by `.gitignore:146 (`.claude/`)` and was never tracked (`git ls-files` error; zero log history; `git check-ignore -v` confirms the rule fires on the exact path). `git add .claude/CLAUDE.md` refuses; `git diff --numstat` on it is vacuous (prints nothing, exits 0).
- **Resolution:** Edits completed and verified on disk — the file's entire purpose is local agent context loaded from the filesystem, so the plan's objective is fully served. Deliberately NOT `git add -f`-ed: force-tracking a path the user explicitly ignored is a repo-policy change (leaks a GSD-generated context file into shared history — the #3678 regression class; the executor treats gitignored-target skips as an intentional success path). Recorded here for the user/orchestrator to decide: either accept the local-only fix, or opt into tracking via `git add -f .claude/CLAUDE.md` + a `!.claude/CLAUDE.md` negation in `.gitignore`.
- **Consequence for this SUMMARY:** `commits: 0` with `plan_head_before == plan_head_after == 219c48a`. This is NOT the "uncommitted tracked changes" halt case: `git status --short` shows zero modified tracked files — the only touched file is invisible to git by the user's own ignore rule. Per-task commits and any executor-side docs commit are therefore all skipped; the orchestrator's docs commit covers `.planning/` artifacts as usual.
- **Gate substitution:** Task 2's `git diff --numstat | awk '$2 <= 10'` check passes vacuously on an untracked file, so equivalent real evidence was captured instead: absence greps for all five old literals (all 0), presence greps for all nine new lines, 14-marker count, +1-line arithmetic (401 → 402), and the full re-read byte-comparison. Effective diff: 9 insertions / 8 deletions, confined to the targeted lines — within the plan's ≤ 10-deletions bound.

Otherwise the plan executed exactly as written.

## Auth Gates

None.

## Known Stubs

None — documentation-only change.

## Observed Out-of-Scope Items (candidates for a follow-up quick task)

Per the plan's explicit flag-don't-fix boundary, these remain in `.claude/CLAUDE.md`:

1. **data_offset constraint bullet (line 353) + both Anti-Pattern headers (lines 358/360)** — suspected stale per STATE.md decisions 01-03/03-09 (the clamp was replaced by a loud `Err`; count.rs now delegates to `KmerEntry::write_to`). Mandated flag from the plan.
2. **Conventions-block stale KmerCounter line pins** — `src/hash/table.rs:14` (line 147), `:15-26` (line 210), `:60-91` (line 208), `:100-103` (line 222) predate the Phase-2/3 rewrite of table.rs. Out of the plan's architecture/stack block scope (must_haves require byte-identity elsewhere).
3. **Project-block constraint (line 13)** dependency list names hashbrown/parking_lot but not dashmap.
4. **Root `CLAUDE.md`** (repo root, tracked, "Auto-generated from all feature plans", dated 2025-11-28) is a separate stale file not in this plan's scope at all.

## Threat Flags

None — no new security-relevant surface (documentation-only; T-261018-swu-01 accuracy gates all passed).

## Self-Check: PASSED

- FOUND: `.planning/quick/261018-swu-fix-claude-md-outdated-architecture-desc/261018-swu-SUMMARY.md`
- FOUND: `.claude/CLAUDE.md` (edited; 4 `CounterTable` mentions confirm corrections in place)
- Commits since plan base: 0, exactly as documented under Deviations (sole target file is gitignored/untracked; `git status` shows zero modified tracked files — nothing committable exists, not an uncommitted-work case)
- Both task gates re-confirmed green at self-check time (TASK1-PASS / TASK2-PASS sentinels above)

