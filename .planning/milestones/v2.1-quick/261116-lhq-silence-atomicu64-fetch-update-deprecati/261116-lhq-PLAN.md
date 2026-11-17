---
phase: quick
plan: 261116-lhq
type: execute
wave: 1
depends_on: []
files_modified:
  - src/hash/table.rs
  - .planning/WINDOWS.md
  - .planning/STATE.md
autonomous: true
requirements: []
estimate:
  tokens: 10000
  raw_tokens: 10000
  tasks: 2
  confidence: low
must_haves:
  truths:
    - "cargo +stable check --lib emits zero warning lines (planning-time baseline at HEAD a8b82f1 on stable 1.99.1: 2 — the AtomicU64::fetch_update deprecation warning plus its generated-N summary line)."
    - "cargo +1.82.0 clippy --locked --all-targets -- -D warnings (root crate, CI-exact) still exits 0 — the allow attribute introduces no regression on the pinned toolchain where try_update does not exist."
    - "cargo +stable test --lib exits 0 with a green test result summary."
    - "cargo +stable fmt --all -- --check exits 0 — the ks7-established clean-tree invariant stays intact."
    - "WINDOWS.md rows 24 and 25 are closed via the windows CLI only — row 24 fixed, row 25 waived with a recorded reason — and the frontmatter counters read open_count: 0, waived_count: 7, fixed_count: 18. No hand edits to the ledger."
    - "The single executor commit contains only src/hash/table.rs; PLAN.md, SUMMARY.md, STATE.md, WINDOWS.md, both Cargo.lock files, and everything else under .planning/ stay outside it."
  artifacts:
    - "src/hash/table.rs carrying a targeted #[allow(deprecated)] on the total_kmers.fetch_update statement with the MSRV tracking comment directly above it"
    - "Updated .planning/WINDOWS.md with row 24 fixed and row 25 waived, counters recomputed by the CLI"
    - "Updated .planning/STATE.md with the Quick Tasks Completed row for 261116-lhq and the refreshed Last activity line"
    - "261116-lhq-SUMMARY.md recording gate outputs, CODE_COMMIT, the committed tracking comment, and both row closures"
  key_links:
    - "MSRV policy (rust-version = \"1.82\" in both Cargo.toml manifests) <-> the allow attribute: the allow exists only because try_update stabilized in Rust 1.95.0 while the MSRV is 1.82; the tracking comment states the exact removal condition (MSRV >= 1.95)."
    - "WINDOWS.md row 24 <-> CODE_COMMIT: the lint-warning row flips to fixed only after every Task 1 gate is green and the atomic code commit exists; the resolution narrative citing CODE_COMMIT and the tracking comment lives in the SUMMARY."
---

<objective>
Silence the `AtomicU64::fetch_update` deprecation warning at src/hash/table.rs:483 with a targeted `#[allow(deprecated)]` plus an MSRV tracking comment (option A — a plain rename to `try_update` is impossible because `try_update` stabilized in Rust 1.95.0 while the project MSRV is 1.82, where a `try_update` call fails with E0599 and would break the CI clippy gate), then close WINDOWS.md rows 24 (fixed) and 25 (waived) through the ledger CLI.

Purpose: keep newer-stable local builds warning-clean without breaking the 1.82.0 CI gate, and zero out the ledger's open_count (the /gsd-ship gate condition).
Output: ONE atomic commit containing exactly src/hash/table.rs, CLI-closed WINDOWS.md rows with recomputed counters, an updated (uncommitted) STATE.md, and an evidence SUMMARY.

Source audit: GOAL (silence the warning at table.rs:483 without changing semantics) is covered by Task 1; CONTEXT row closures (24 fixed with resolution citing the commit + tracking comment, 25 waived per the rows-12/13 precedent) are covered by Task 2. No RESEARCH.md applies; no deferred ideas are implemented by this quick item.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/WINDOWS.md
@.claude/CLAUDE.md

Grounding observed live at planning time, HEAD a8b82f1 on dev, working tree clean:
- The call site is the `let published = self.total_kmers.fetch_update(` statement at src/hash/table.rs:483 inside `merge_local_counts`. The comment block at lines 471-482 explains why the compare-exchange semantics are required (concurrent `merge_local_counts` is a supported configuration; a bare `fetch_add` would silently wrap past u64::MAX). Do NOT change the method, its two `Relaxed` orderings, or the `checked_add` closure, and do not touch that comment block. The `fetch_update` mention at line 1224 is a doc comment, not a call — it warns nowhere and needs nothing.
- Local default toolchain is nightly 1.101; the warning fires on stable 1.99.1 (planning-time run of `cargo +stable check --lib` grep-counts 2 warning lines at HEAD: the deprecation warning plus its `generated 1 warning` summary). rustup has `stable` and `1.82.0` installed — pin toolchains explicitly on every cargo command. `cargo +stable fmt --all -- --check` exits 0 at HEAD (ks7 invariant).
- The CI clippy gate pins 1.82.0 with `-D warnings` (`rust-version = "1.82"` in both Cargo.toml manifests), where `try_update` does not exist — the agreed fix is the targeted allow, not a rename.
- WINDOWS.md is a CLI-managed ledger: the markdown table and frontmatter counts are rendered from a JSON entries block; the CLI re-renders and recomputes on every write and refuses a disagreeing ledger. NEVER hand-edit rows or counts. Baselines at HEAD: `grep -c "^| 24 .*| open |"` = 1, `grep -c "^| 25 .*| open |"` = 1, `^open_count: 2$` = 1, `^waived_count: 6$` = 1, `^fixed_count: 17$` = 1.
- Closure precedents: row 25 follows waived rows 12/13 (unsatisfiable literal grep gate, discriminating evidence used instead — narrative recorded in the reason cell via `windows waive`). Row 24 follows the fixed-row pattern of quick 261111-v69 (row 15): `windows fixed <id>` sets status + resolved_at and recomputes counters, and it records NO reason text (all fixed rows 15/19-23 carry an empty reason cell) — the resolution narrative citing CODE_COMMIT and the tracking comment lives in the SUMMARY.
- Execution/commit contract: Task 1 makes ONE commit containing exactly src/hash/table.rs (record its hash as CODE_COMMIT). Task 2 runs only after every Task 1 gate is green and edits only .planning/ artifacts. The executor MUST NOT commit PLAN.md, SUMMARY.md, STATE.md, WINDOWS.md, either Cargo.lock, or anything else under .planning/; the orchestrator owns the docs commit. All commands assume cwd at the checkout root; every path is repo-root-relative.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Targeted allow(deprecated) on the fetch_update publish site, gates green, atomic commit</name>
  <files>src/hash/table.rs</files>
  <action>
In src/hash/table.rs, inside `merge_local_counts`, insert immediately above the `let published = self.total_kmers.fetch_update(` statement (line 483) a four-line tracking comment and the attribute, so the site reads: a comment block stating that fetch_update is renamed to try_update in Rust 1.95.0, that the project MSRV is 1.82 where try_update does not exist so the rename would break the CI clippy gate, and to remove this allow and rename to try_update when the project MSRV reaches >= 1.95; then the attribute `#[allow(deprecated)]` on the let statement itself. Keep the existing lines 471-482 comment block, the method, both `std::sync::atomic::Ordering::Relaxed` arguments, and the `|current| current.checked_add(merged_total)` closure byte-for-byte unchanged. Make no other edit anywhere in the file; no manifest, feature, dependency, or lockfile change of any kind.
Then run the four gates from the checkout root and require every one green: (1) `cargo +stable check --lib 2>&1 | grep -ci warning` must print 0 (baseline HEAD=2, EXPECT=0); (2) `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` (root crate, CI-exact) exits 0; (3) `cargo +stable fmt --all -- --check` exits 0; (4) `cargo +stable test --lib` exits 0 with a green `test result: ok` summary.
Then commit atomically: `git add src/hash/table.rs` and `git commit -m "fix: allow deprecated AtomicU64::fetch_update until MSRV >= 1.95 (quick 261116-lhq)"`; record `git rev-parse HEAD` as CODE_COMMIT. Never stage either Cargo.lock or anything under .planning/.
  </action>
  <verify>
    <automated>cargo +stable check --lib >/dev/null 2>&1 && test "$(cargo +stable check --lib 2>&1 | grep -ci warning)" = "0" && cargo +1.82.0 clippy --locked --all-targets -- -D warnings >/dev/null 2>&1 && cargo +stable fmt --all -- --check >/dev/null 2>&1 && cargo +stable test --lib 2>&1 | grep -q "test result: ok" && test "$(git diff --name-only CODE_COMMIT^..CODE_COMMIT)" = "src/hash/table.rs" && echo LHQ-T1-GATES-GREEN</automated>
  </verify>
  <done>All four gates exit green with zero warning lines on stable, and CODE_COMMIT is a single-file commit whose only path is src/hash/table.rs.</done>
  <reversibility rating="reversible">A two-line allow + comment at one call site; revert by deleting the attribute and comment, or superseded wholesale by an MSRV bump to >= 1.95 plus the rename the tracking comment prescribes.</reversibility>
</task>

<task type="auto">
  <name>Task 2: Close WINDOWS rows 24 (fixed) and 25 (waived) via the ledger CLI, update STATE.md</name>
  <files>.planning/WINDOWS.md, .planning/STATE.md</files>
  <action>
Run only after Task 1 is fully green and committed (precondition below). From the checkout root, using the ledger CLI (gsd_run on PATH; fallback: `node ~/.claude/gsd-core/bin/gsd-tools.cjs`):
1. Flip row 24 (lint-warning at src/hash/table.rs:483) to fixed: `gsd_run windows fixed 24`. The CLI sets status and resolved_at and recomputes the frontmatter counts; it records no reason text (all fixed-row precedent 15/19-23 carry an empty reason cell) — record the resolution narrative in the SUMMARY instead (step 4). Never hand-edit the ledger file.
2. Waive row 25 (the ks7 T2V1 unsatisfiable literal grep gate) with this recorded reason, passed as ONE double-quoted argument: `gsd_run windows waive 25 "Accepted deviation, waived 2026-11-16: the ks7 T2V1 gate form was unsatisfiable by construction — a line-counting grep -c over plan-ID mentions cannot reach 3 matching lines when the plan own action spec permits the ID on only 2 lines (4 occurrences), so the gate could not pass without corrupting the actions it verifies. The discriminating evidence stands and proved the property the literal gate approximated: occurrence count 4 >= 3, exactly one Resolved-by-quick-261116-ks7 line, and the quick-task row present. Same defect class as waived rows 12 and 13: the literal grep was the wrong instrument, not a code defect."` If gsd_run rejects the text length or characters, shorten only the middle sentence, keeping the waive-date, the unsatisfiability argument, the three discriminating-evidence items, and the rows-12/13 defect-class citation.
3. In .planning/STATE.md make exactly two edits: (a) replace the `Last activity:` line under Current Position with `Last activity: 2026-11-16 - Completed quick task 261116-lhq: Silence AtomicU64 fetch_update deprecation warning and close WINDOWS rows 24-25`; (b) append to the Quick Tasks Completed table the row `| 261116-lhq | Silence AtomicU64 fetch_update deprecation warning (MSRV-gated allow); close WINDOWS 24/25 | 2026-11-16 | CODE_COMMIT | [261116-lhq-silence-atomicu64-fetch-update-deprecati](./quick/261116-lhq-silence-atomicu64-fetch-update-deprecati/) |` — replacing CODE_COMMIT with the Task 1 hash. Touch nothing else in STATE.md.
4. Write 261116-lhq-SUMMARY.md per the summary template, recording: each Task 1 gate command with its exact exit code and the warning-count before (2) / after (0); CODE_COMMIT; the committed tracking-comment text; the row 24 closure with its resolution narrative citing CODE_COMMIT and the tracking comment (fixed rows keep an empty ledger reason cell, per precedent); and the row 25 waive reason as recorded by the CLI. Leave PLAN.md, SUMMARY.md, STATE.md, and WINDOWS.md UNCOMMITTED — the orchestrator owns the docs commit.
  </action>
  <verify>
    <automated>test "$(grep -c "^open_count: 0$" .planning/WINDOWS.md)" = "1" && test "$(grep -c "^waived_count: 7$" .planning/WINDOWS.md)" = "1" && test "$(grep -c "^fixed_count: 18$" .planning/WINDOWS.md)" = "1" && test "$(grep -c "^| 24 .*| fixed |" .planning/WINDOWS.md)" = "1" && test "$(grep -c "^| 25 .*| waived |" .planning/WINDOWS.md)" = "1" && test "$(grep -c "261116-lhq" .planning/STATE.md)" -ge "2" && echo LHQ-T2-LEDGER-CLOSED</automated>
  </verify>
  <done>WINDOWS.md frontmatter reads open_count: 0 (the /gsd-ship gate condition), waived_count: 7, fixed_count: 18; rendered row 24 shows fixed and row 25 shows waived with the recorded reason; STATE.md carries the quick-task row and refreshed last-activity line; all .planning/ edits remain uncommitted for the orchestrator.</done>
  <precondition>CODE_COMMIT exists as a single-file commit touching only src/hash/table.rs, and all four Task 1 gates exited 0. Halt without touching the ledger or STATE.md otherwise.</precondition>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| executor -> WINDOWS.md ledger | The defect register gates /gsd-ship; a corrupted or hand-edited ledger silently disables the ship block |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261116-lhq-01 | Repudiation | .planning/WINDOWS.md rows 24/25 and frontmatter counts | medium | mitigate | Ledger flips happen only via the windows CLI (which recomputes counts, stamps resolved_at, and refuses a disagreeing ledger) after all Task 1 gates are green and CODE_COMMIT exists; closure evidence (gate outputs, hash, reason text) is recorded in the SUMMARY; Task 2 verifies counters and rendered statuses by grep before declaring done |
</threat_model>

<verification>
- `cargo +stable check --lib 2>&1 | grep -ci warning` prints 0 (planning-time HEAD baseline: 2).
- `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` exits 0 (CI-exact, root crate).
- `cargo +stable fmt --all -- --check` exits 0 (ks7 invariant preserved).
- `cargo +stable test --lib` exits 0.
- WINDOWS.md: open_count 0 / waived_count 7 / fixed_count 18; row 24 fixed, row 25 waived — all via the CLI, never hand-edited.
- CODE_COMMIT touches exactly src/hash/table.rs; all .planning/ artifacts stay uncommitted for the orchestrator.
</verification>

<success_criteria>
The AtomicU64::fetch_update deprecation warning no longer fires on newer-stable toolchains while the 1.82.0 CI clippy gate stays green with unchanged semantics (same method, orderings, closure); WINDOWS.md has zero open rows with 24 fixed and 25 waived; STATE.md records the completed quick task; the executor leaves exactly one code commit and uncommitted docs artifacts.
</success_criteria>

<output>
Create `.planning/quick/261116-lhq-silence-atomicu64-fetch-update-deprecati/261116-lhq-SUMMARY.md` when done
</output>
