---
phase: quick
plan: 261116-lhq
subsystem: core
tags: [rust, deprecation, msrv, clippy, ci, windows-ledger]
requires:
  - phase: quick-261116-ks7
    provides: WINDOWS.md rows 24 (lint-warning, open) and 25 (deviation, open) recorded at ks7 close
provides:
  - warning-clean `cargo +stable check --lib` build (zero warning lines) with the 1.82.0 CI clippy gate untouched
  - zero open WINDOWS.md rows (open_count: 0 — the /gsd-ship gate condition)
affects: [future MSRV bump to >= 1.95 (the tracking comment prescribes the try_update rename), /gsd-ship gate]

actuals:
  tokens: 224         # chars/4 over the realized source diff (894 chars, 5 insertions)
  tasks: 2
  commits: 1          # MEASURED: git rev-list --count 1432822..HEAD

tech-stack:
  added: []
  patterns: ["MSRV-gated lint suppression: targeted #[allow(deprecated)] + removal-condition tracking comment instead of a rename unavailable at MSRV"]

key-files:
  created:
    - .planning/quick/261116-lhq-silence-atomicu64-fetch-update-deprecati/261116-lhq-SUMMARY.md
  modified:
    - src/hash/table.rs
    - .planning/WINDOWS.md
    - .planning/STATE.md

key-decisions:
  - "Option A (targeted allow), not a rename: `try_update` stabilized in Rust 1.95.0 while the project MSRV is 1.82 (rust-version in both Cargo.toml manifests), where a `try_update` call fails with E0599 and would break the CI clippy gate (-D warnings)"
  - "Fixed row 24 keeps an empty ledger reason cell (precedent: fixed rows 15/19-23); the resolution narrative lives here in the SUMMARY"

patterns-established:
  - "Deprecation warning on a call site whose replacement is newer than MSRV: suppress with #[allow(deprecated)] directly above the statement, comment states the exact removal condition (MSRV >= 1.95 -> rename to try_update)"

requirements-completed: []

coverage:
  - id: T1
    description: "The fetch_update deprecation warning no longer fires on newer-stable toolchains while semantics are unchanged (same method, both Relaxed orderings, checked_add closure byte-identical) and the 1.82.0 CI gate stays green"
    verification:
      - kind: other
        ref: "cargo +stable check --lib 2>&1 | grep -ci warning -> 0 (planning-time HEAD baseline: 2)"
        status: pass
      - kind: other
        ref: "cargo +1.82.0 clippy --locked --all-targets -- -D warnings -> exit 0 (CI-exact, root crate)"
        status: pass
      - kind: other
        ref: "cargo +stable fmt --all -- --check -> exit 0 (ks7 invariant preserved)"
        status: pass
      - kind: other
        ref: "cargo +stable test --lib -> exit 0, test result: ok. 260 passed; 0 failed"
        status: pass
      - kind: other
        ref: "git diff --name-only 3655086^..3655086 -> exactly src/hash/table.rs"
        status: pass
    human_judgment: false
  - id: T2
    description: "WINDOWS rows 24 (fixed) and 25 (waived) closed via the ledger CLI only; counters recomputed by the CLI; STATE.md carries the quick-task row and refreshed last-activity line; all .planning/ edits left uncommitted for the orchestrator"
    verification:
      - kind: other
        ref: "grep -c '^open_count: 0$' .planning/WINDOWS.md -> 1"
        status: pass
      - kind: other
        ref: "grep -c '^waived_count: 7$' .planning/WINDOWS.md -> 1; grep -c '^fixed_count: 18$' .planning/WINDOWS.md -> 1"
        status: pass
      - kind: other
        ref: "grep -c '^| 24 .*| fixed |' .planning/WINDOWS.md -> 1; grep -c '^| 25 .*| waived |' .planning/WINDOWS.md -> 1"
        status: pass
      - kind: other
        ref: "grep -c '261116-lhq' .planning/STATE.md >= 2"
        status: pass
    human_judgment: false
audit_acknowledged:
  milestone: v2.1
  at: 2026-11-18
  status: unknown
---

# Quick Task 261116-lhq: Silence AtomicU64 fetch_update Deprecation Warning Summary

**One-liner:** Targeted `#[allow(deprecated)]` with an MSRV tracking comment on the `total_kmers.fetch_update` publish site (src/hash/table.rs:483) — zero warnings on newer-stable rustc, CI 1.82.0 clippy gate untouched, WINDOWS ledger at zero open rows.

## What Was Built

**CODE_COMMIT: `3655086`** — "fix: allow deprecated AtomicU64::fetch_update until MSRV >= 1.95 (quick 261116-lhq)" — single-file commit, `git diff --name-only 3655086^..3655086` = `src/hash/table.rs` exactly (5 insertions, 0 deletions; no Cargo.lock, nothing under .planning/).

### The code change

Inserted immediately above the `let published = self.total_kmers.fetch_update(` statement inside `merge_local_counts` (now lines 488-492; statement formerly line 483). The committed tracking comment and attribute, verbatim:

```rust
        // `AtomicU64::fetch_update` is renamed to `try_update` in Rust 1.95.0.
        // The project MSRV is 1.82, where `try_update` does not exist, so
        // renaming would break the CI clippy gate (`-D warnings`). Remove
        // this allow and rename to `try_update` when the MSRV reaches >= 1.95.
        #[allow(deprecated)]
        let published = self.total_kmers.fetch_update(
```

The existing lines 471-482 comment block (compare-exchange / concurrent-merge rationale), the method call, both `std::sync::atomic::Ordering::Relaxed` arguments, and the `|current| current.checked_add(merged_total)` closure are byte-for-byte unchanged. No manifest, feature, dependency, or lockfile change of any kind.

### Task 1 gates (all green, run from the checkout root)

| Gate | Command | Result | Exit |
|------|---------|--------|------|
| 1. Stable warning count | `cargo +stable check --lib 2>&1 \| grep -ci warning` | `0` (planning-time HEAD baseline: 2 — the deprecation warning plus its `generated 1 warning` summary line) | 0 |
| 2. CI-exact clippy | `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` | `Finished \`dev\` profile ... in 2.43s`, no diagnostics | 0 |
| 3. Format invariant | `cargo +stable fmt --all -- --check` | clean (ks7 invariant preserved) | 0 |
| 4. Library tests | `cargo +stable test --lib` | `test result: ok. 260 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.10s` | 0 |

The plan's full automated verify chain printed `LHQ-T1-GATES-GREEN` (all four gates plus the single-file commit-scope assertion in one `&&` chain); post-commit deletion check found no deletions.

### Task 2 — WINDOWS.md ledger closures (CLI only, never hand-edited)

1. **Row 24 → fixed** via `gsd_run windows fixed 24` (resolved_at `2026-11-16T07:49:46.495Z`). Per fixed-row precedent (rows 15/19-23) the ledger reason cell stays empty; the resolution narrative lives here:
   > The `AtomicU64::fetch_update` deprecation warning at src/hash/table.rs:483 is silenced by CODE_COMMIT `3655086`, which adds a targeted `#[allow(deprecated)]` directly on the publish statement with the MSRV tracking comment stating the exact removal condition (rename to `try_update` when the project MSRV reaches >= 1.95; `try_update` stabilized in Rust 1.95.0). Every Task 1 gate was green before the flip: stable warning count 2 → 0, CI-exact 1.82.0 clippy `-D warnings` exit 0 (the rename option is impossible there — E0599), fmt check exit 0, `test --lib` 260/260 green, with unchanged semantics (same method, both `Relaxed` orderings, `checked_add` closure).

2. **Row 25 → waived** via `gsd_run windows waive 25 "..."` with the full reason accepted by the CLI verbatim (resolved_at `2026-11-16T07:50:34.301Z`):
   > Accepted deviation, waived 2026-11-16: the ks7 T2V1 gate form was unsatisfiable by construction — a line-counting grep -c over plan-ID mentions cannot reach 3 matching lines when the plan own action spec permits the ID on only 2 lines (4 occurrences), so the gate could not pass without corrupting the actions it verifies. The discriminating evidence stands and proved the property the literal gate approximated: occurrence count 4 >= 3, exactly one Resolved-by-quick-261116-ks7 line, and the quick-task row present. Same defect class as waived rows 12 and 13: the literal grep was the wrong instrument, not a code defect.

   This follows the waived rows 12/13 precedent (unsatisfiable literal grep gate, discriminating evidence used instead).

3. **Counters recomputed by the CLI on every write:** frontmatter now reads `open_count: 0` (the /gsd-ship gate condition), `waived_count: 7`, `fixed_count: 18`. Rendered row 24 shows `fixed`, row 25 shows `waived` with the recorded reason. Task 2's automated verify printed `LHQ-T2-LEDGER-CLOSED`.

### STATE.md updates (exactly two edits, uncommitted)

- `Last activity:` line → `2026-11-16 - Completed quick task 261116-lhq: Silence AtomicU64 fetch_update deprecation warning and close WINDOWS rows 24-25`
- Quick Tasks Completed table gained: `| 261116-lhq | Silence AtomicU64 fetch_update deprecation warning (MSRV-gated allow); close WINDOWS 24/25 | 2026-11-16 | 3655086 | [directory link] |`

## Deviations from Plan

None — plan executed exactly as written.

## Authentication Gates

None.

## Commits

| Commit | Type | Files |
|--------|------|-------|
| `3655086` | fix | src/hash/table.rs (the only executor commit; all .planning/ artifacts intentionally left uncommitted for the orchestrator's docs commit) |

## Self-Check: PASSED

- `src/hash/table.rs` modified in CODE_COMMIT `3655086`: FOUND (commit is HEAD ancestor, single-file scope verified)
- `.planning/WINDOWS.md` counters open 0 / waived 7 / fixed 18 with rows 24 fixed, 25 waived: FOUND (grep-verified, CLI-rendered)
- `.planning/STATE.md` quick-task row + refreshed last-activity line: FOUND
- `261116-lhq-SUMMARY.md` (this file): FOUND
