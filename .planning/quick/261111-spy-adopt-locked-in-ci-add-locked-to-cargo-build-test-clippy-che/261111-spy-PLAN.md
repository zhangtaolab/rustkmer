---
phase: quick
plan: 261111-spy
type: execute
wave: 1
depends_on: []
files_modified:
  - .github/workflows/ci.yml
  - .github/workflows/benchmark.yml
autonomous: true
must_haves:
  truths:
    - "All 4 in-repo cargo build/test/clippy/check/run invocations in .github/workflows/ carry --locked (ci.yml clippy-root, ci.yml test-root, ci.yml pyo3-build clippy step, benchmark.yml release build), so lockfile/manifest drift fails CI loudly instead of silently re-resolving dependencies."
    - "All 3 workflow files (ci.yml, benchmark.yml, docs.yml) parse as valid YAML after the edit."
    - "The deliverable commit's diff (HEAD^..HEAD) is exactly four --locked insertions in exactly two files — no toolchain, action-version, flag, comment, cache-key, or whitespace change; cargo fmt, maturin, pip, and pytest steps are untouched."
    - "Both tracked lockfiles remain consistent with their manifests (cargo metadata --locked exits 0 for the root crate and for pyo3/Cargo.toml), so the new CI gate is green on arrival."
    - "The four insertions land as exactly one atomic executor commit touching only the two workflow files; the working tree is clean of tracked edits afterwards; nothing is pushed, and SUMMARY.md / .planning artifacts stay uncommitted for the orchestrator's docs commit."
  artifacts:
    - ".github/workflows/ci.yml with --locked inserted on the clippy-root, test-root, and pyo3-build clippy invocations (3 insertions)."
    - ".github/workflows/benchmark.yml with --locked inserted on the release-build invocation (1 insertion; trailing comment preserved verbatim)."
  key_links:
    - "ci.yml pyo3-build clippy step (working-directory: pyo3) -> pyo3/Cargo.lock: the pyo3 crate keeps its own independent lockfile; this --locked gate is what makes the pyo3 lock a regression gate. The later maturin build step in the same job is out of scope and inherits consistency from this earlier step."
    - "ci.yml clippy-root / test-root and benchmark.yml release build -> root Cargo.lock: all three resolve the root crate against the tracked lock."
    - "Tracked lockfiles (commit 09d90bc, quick task 261111-s6h) -> --locked CI gate: tracking was the prerequisite; this plan activates the gate that task explicitly surfaced as its follow-up."
---

<objective>
Adopt --locked in CI: insert --locked into every in-repo cargo build/test/clippy/check/run invocation in .github/workflows/ (4 invocations across ci.yml and benchmark.yml), making lockfile/manifest consistency a regression gate on both crates. Change nothing beyond the four insertions; keep YAML valid; prove completion with grep evidence plus a YAML syntax check.

Purpose: both Cargo.lock files are tracked as of commit 09d90bc (quick task 261111-s6h), but CI still resolves without --locked — a manifest/lock drift would silently re-resolve dependencies in the merge-gate jobs instead of failing. This plan closes that exact follow-up. It is a single vertical slice: edit the four invocation lines -> prove only --locked was added -> commit atomically -> re-prove against the commit range plus YAML validity, full locked coverage, and lock consistency so the gate is green on arrival.

Output: one atomic executor commit touching exactly the two workflow files (four --locked insertions total), green verification gates pinned to that commit's range, and a SUMMARY recording the grep proof and commit hash. The executor commits code atomically on the primary checkout; the orchestrator commits only docs artifacts (PLAN/SUMMARY/STATE) afterwards — SUMMARY.md itself stays uncommitted.

Grounded facts (verified live at planning time against HEAD 45205d3):
- Exactly 3 workflow files exist: ci.yml, benchmark.yml, docs.yml. performance-regression.yml (named in older docs, with a commented-out criterion bench) was DELETED before this batch — benchmark.yml's header comment confirms it ("the deleted performance-regression.yml died of exactly those diseases"). There is nothing to edit there; commented-out lines are not invocations.
- The complete census of in-repo cargo invocations with the item's target verbs (build/test/clippy/check/run) — 4 total, none carrying --locked at HEAD:
  | File:line | Job | Crate | Current text |
  |---|---|---|---|
  | .github/workflows/ci.yml:69 | clippy-root | root | `- run: cargo clippy --all-targets -- -D warnings` |
  | .github/workflows/ci.yml:94 | test-root | root | `- run: cargo test` |
  | .github/workflows/ci.yml:124 | pyo3-build (step "clippy (pyo3)", working-directory: pyo3) | pyo3 | `run: cargo clippy --all-targets -- -D warnings` |
  | .github/workflows/benchmark.yml:71 | benchmark (step "Build release binary") | root | `run: cargo build --release  # never time a debug build` |
- Deliberate exclusions (do NOT edit these):
  - ci.yml:37 `cargo fmt --all --check` — fmt is not in the item's verb list, and `cargo fmt --help` (checked live) shows NO --locked option; adding it would break the fmt gate job. cargo fmt performs no dependency resolution.
  - ci.yml:127 and ci.yml:170 `maturin build` — not cargo invocations; out of the item's scope. The pyo3 lock is still gated: the pyo3-build job's clippy step (which gets --locked) runs BEFORE its maturin step in the same job.
  - All `pip install` steps — tool installs, explicitly excluded by the item. No `cargo install` step exists anywhere in .github/workflows/.
  - docs.yml — zero cargo invocations (Python/mkdocs only); untouched.
- Both lockfiles are tracked and unchanged since 09d90bc (`git diff 09d90bc HEAD -- Cargo.lock pyo3/Cargo.lock Cargo.toml pyo3/Cargo.toml` is empty); 261111-s6h verified `cargo build --locked` (root) and `cargo check --locked` (pyo3) on that exact resolution, and this planning session re-proved consistency live: `cargo metadata --locked` exits 0 for both crates.
- No sibling batch item touches .github/workflows/ (spz: .planning disposition docs; sq0: Cargo.toml manifests + docs; sq1: Cargo.toml + Cargo.lock, with its own lock refresh if a dep is removed) — hence depends_on: [] and wave 1.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md
@.planning/quick/261111-s6h-start-tracking-cargo-lock-for-reproducib/261111-s6h-SUMMARY.md
@.github/workflows/ci.yml
@.github/workflows/benchmark.yml

The prior SUMMARY is referenced because this plan implements the exact follow-up it recorded ("CI workflows do not yet pass --locked") and inherits its lock-consistency proof. Line numbers above are planning-time anchors; match by content neighborhood, not by line number alone.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Insert --locked into the four in-repo cargo invocations and commit atomically</name>
  <files>.github/workflows/ci.yml, .github/workflows/benchmark.yml</files>
  <action>
    Make exactly four insertions, each placing `--locked` immediately after the cargo verb and before all other flags (for clippy this is load-bearing: everything after `--` goes to rustc, so the flag must precede `--all-targets -- -D warnings`).
    (a) In `.github/workflows/ci.yml`, replace every occurrence of `cargo clippy --all-targets` with `cargo clippy --locked --all-targets`. There are exactly 2 occurrences at planning time — the clippy-root job's run line and the pyo3-build job's named "clippy (pyo3)" step (working-directory: pyo3). Both are in-repo invocations and both must change; a replace-all on that substring is correct and complete.
    (b) In `.github/workflows/ci.yml`, change the test-root job's run line from `- run: cargo test` to `- run: cargo test --locked` (the only `cargo test` occurrence in the file; anchor on end-of-line so no other text is touched).
    (c) In `.github/workflows/benchmark.yml`, change the "Build release binary" step's run line from `cargo build --release` to `cargo build --locked --release`, preserving the trailing two-space + `# never time a debug build` comment byte-for-byte.
    (d) Touch NOTHING else: no edit to the cargo fmt line, maturin/pip/pytest steps, toolchain actions, action versions, cache keys, comments, or docs.yml. No reformatting, no trailing-whitespace cleanup, no YAML restructuring.
    (e) Pre-commit proof (working tree): capture `git diff --word-diff=plain -- .github/workflows/` into a variable and require exactly four added --locked tokens and zero removal markers; capture `git diff --name-only` and require exactly the two workflow files. If either check fails, fix the edits before committing — a malformed edit must never land in history.
    (f) Stage EXACTLY the two deliverables with explicit paths: `git add .github/workflows/ci.yml .github/workflows/benchmark.yml` (never `git add -A` or `git add .`), confirm the staged set equals exactly those two files, then create ONE atomic commit: `ci: adopt --locked for in-repo cargo invocations (quick-batch 261111-spy)` (no co-author trailer, matching the prior quick-task convention). Do NOT push. Do NOT stage or commit anything else — SUMMARY.md and all .planning/ artifacts stay uncommitted; the orchestrator commits docs only, after the item completes.
    Scope lock: the only edited and committed files are .github/workflows/ci.yml and .github/workflows/benchmark.yml; the only semantic change is four --locked insertions.
  </action>
  <verify>
    <automated>WD=$(git diff --word-diff=plain HEAD^..HEAD -- .github/workflows/) && test "$(printf '%s\n' "$WD" | grep -c '{+--locked+}')" = "4" && ! printf '%s\n' "$WD" | grep -q '\[-' && FILES=$(git show --name-only --format= HEAD) && test "$(printf '%s\n' "$FILES" | sort | paste -sd, -)" = ".github/workflows/benchmark.yml,.github/workflows/ci.yml" && SUBJ=$(git log -1 --format=%s) && test "$SUBJ" = "ci: adopt --locked for in-repo cargo invocations (quick-batch 261111-spy)" && UNSTAGED=$(git diff --name-only) && test -z "$UNSTAGED" && STAGED=$(git diff --cached --name-only) && test -z "$STAGED"</automated>
  </verify>
  <done>The commit-range word-level diff (HEAD^..HEAD, HEAD = the new commit) shows exactly 4 added --locked tokens and zero removed tokens (pre-edit baseline: empty diff, 0 insertions — gate fails before the edit, passes after the commit; shape validated against a simulated post-change tree at planning time). The commit's file set is exactly the two workflow files and its subject is the specified message. No unstaged or staged tracked changes remain — the working tree is clean of deliverable edits. One atomic commit, nothing pushed, SUMMARY/.planning uncommitted.</done>
</task>

<task type="auto">
  <name>Task 2: Prove YAML validity, full --locked coverage, and lock consistency</name>
  <files>.github/workflows/ci.yml, .github/workflows/benchmark.yml</files>
  <action>
    Verification-only task — make NO file edits and NO additional commits; the deliverable is the Task 1 commit, and HEAD is still that commit (pin every commit-range gate to HEAD^..HEAD; if an unexpected intervening commit has moved HEAD, locate the Task 1 commit by its message and pin <hash>^..<hash> instead). From the repo root, run the automated gate chain below. It proves, in order:
    (a) YAML syntax + semantic coverage: python3 (PyYAML 6.0.3 verified present) parses ALL 3 workflow files and walks every job step's run block, counting cargo invocations of the five target verbs with shell comments stripped — asserting exactly 4 invocations exist and all 4 carry --locked. Baseline at HEAD: parses 3 files, 0/4 locked, exit 1 (RED); simulated post-change tree: 4/4, exit 0 (GREEN).
    (b) Grep proof (the item's required evidence): total invocation-line count is 4 (invariant — proves no invocation was added or removed), locked-line count is 4 (0 at HEAD), and the negative grep listing any target-verb invocation lacking --locked is empty (4 lines at HEAD). Capture the four locked invocation lines (`grep -nE 'cargo (build|test|clippy|check|run) --locked' .github/workflows/*.yml`) into the SUMMARY as the grep proof.
    (c) Lock consistency: `cargo metadata --locked` exits 0 for the root crate and for pyo3/Cargo.toml — the cheapest full-resolution proof that the new CI gate will be green on arrival (both passed live at planning time; registry cache is warm). Then confirm neither lockfile was rewritten in the working tree.
    (d) Commit-range shape + clean tree: the word-diff of HEAD^..HEAD shows exactly four added --locked tokens and zero removal markers; the commit's file set is exactly the two workflow files; and the unstaged and staged tracked-change sets are both empty (the deliverable is fully committed; untracked .planning/ orchestrator artifacts are expected and out of scope).
    Contingency: if a --locked consistency gate fails with "the lock file needs to be updated" (or similar), STOP and report — do NOT run cargo update, do NOT edit manifests or locks to force green. That would contradict the planning-time observation (possibly a sibling batch item landed a manifest change without its lock refresh) and needs the orchestrator's eyes. If a gate fails for an unrelated environmental reason (network/registry/toolchain), report it rather than widening scope.
    Record in the SUMMARY: the Task 1 commit hash (`git rev-parse HEAD`); the grep proof lines; that performance-regression.yml is absent (deleted pre-batch, nothing to do); that cargo fmt was deliberately excluded (not in the item's verb list; no --locked support per cargo fmt --help); and that maturin build steps were left as-is (pyo3 lock gated by the earlier clippy step in the same job). Leave SUMMARY.md itself uncommitted — the orchestrator owns the docs commit.
  </action>
  <verify>
    <automated>python3 -c 'import glob, re, yaml
verb = re.compile(r"\bcargo\s+(build|test|clippy|check|run)\b")
files = sorted(glob.glob(".github/workflows/*.yml"))
total = locked = 0
for f in files:
    doc = yaml.safe_load(open(f))
    for jname, job in (doc.get("jobs") or {}).items():
        for step in (job.get("steps") or []):
            for line in (step.get("run") or "").splitlines():
                code = line.split("#", 1)[0]
                if verb.search(code):
                    total += 1
                    if "--locked" in code:
                        locked += 1
                    else:
                        print("MISSING --locked: %s job=%s: %s" % (f, jname, line.strip()))
print("parsed %d workflows as valid YAML; %d/%d in-repo cargo invocations carry --locked" % (len(files), locked, total))
assert total == 4, "expected 4 in-repo cargo invocations, found %d" % total
assert locked == total, "%d invocation(s) lack --locked" % (total - locked)
print("YAML+locked gate PASS")' && test "$(grep -hE 'cargo (build|test|clippy|check|run)([[:space:]]|$)' .github/workflows/*.yml | wc -l | tr -d ' ')" = "4" && test "$(grep -hE 'cargo (build|test|clippy|check|run)([[:space:]]|$)' .github/workflows/*.yml | grep -c -- '--locked')" = "4" && ! grep -nE 'cargo (build|test|clippy|check|run)([[:space:]]|$)' .github/workflows/*.yml | grep -v -- '--locked' && WD=$(git diff --word-diff=plain HEAD^..HEAD -- .github/workflows/) && test "$(printf '%s\n' "$WD" | grep -c '{+--locked+}')" = "4" && ! printf '%s\n' "$WD" | grep -q '\[-' && FILES=$(git show --name-only --format= HEAD) && test "$(printf '%s\n' "$FILES" | sort | paste -sd, -)" = ".github/workflows/benchmark.yml,.github/workflows/ci.yml" && cargo metadata --locked --format-version 1 >/dev/null && cargo metadata --locked --format-version 1 --manifest-path pyo3/Cargo.toml >/dev/null && LOCKDIFF=$(git diff --name-only -- Cargo.lock pyo3/Cargo.lock) && test -z "$LOCKDIFF" && UNSTAGED=$(git diff --name-only) && test -z "$UNSTAGED" && STAGED=$(git diff --cached --name-only) && test -z "$STAGED"</automated>
  </verify>
  <done>All 3 workflows parse as valid YAML; the semantic gate reports 4/4 in-repo cargo invocations carrying --locked (pre-edit baseline: 0/4); grep proof shows invocation total 4 (unchanged), locked count 4 (pre-edit: 0), and an empty negative grep (pre-edit: 4 lines); the commit-range word-diff (HEAD^..HEAD) shows exactly 4 --locked insertions and zero removals with the exact two-file commit set; cargo metadata --locked exits 0 for both crates and leaves both lockfiles unmodified; the working tree has no unstaged or staged tracked changes; no file was edited and no additional commit was created in this task.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| crates.io resolution -> CI merge-gate builds | Without --locked, CI re-resolves dependencies whenever manifest and lock drift, admitting untested versions into the jobs that gate every PR. |
| Plan edits -> gate workflow integrity | The gate workflows themselves are the control; an over-broad edit could weaken them (dropped -D warnings, softened exits, changed toolchain). |

## STRIDE Threat Register

ASVS level 1; blocking threshold high. Threat IDs are scoped to this quick task's full slug (261111-spy) so they cannot collide with sibling batch items' registers.

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261111-spy-01 | Tampering | CI dependency resolution (all 4 in-repo cargo invocations) | high | mitigate | Without --locked, a manifest/lock drift lets CI silently resolve newer — potentially compromised or untested — crate versions into the merge-gate builds, defeating the tracked-lockfile guarantee from 09d90bc. Mitigated by the deliverable itself: --locked on all 4 invocations makes cargo refuse (loud job failure) rather than re-resolve; Task 2 proves 4/4 coverage and live lock consistency on both crates. |
| T-261111-spy-02 | Tampering | Gate-workflow integrity during the edit | medium | mitigate | An over-broad edit could weaken a gate (removing -D warnings, adding continue-on-error, bumping toolchain/actions). Mitigated by Task 1's pre-commit working-tree word-diff gate and the post-commit HEAD^..HEAD re-proof: exactly 4 added --locked tokens, zero removed tokens, exact two-file commit set — any other edit fails the gate before or after landing. |
| T-261111-spy-03 | Tampering | Out-of-scope build steps left unlocked (maturin build x2, cargo fmt) | low | accept | maturin build internally invokes cargo but is not a cargo invocation per the item's scope; the pyo3 lock is gated by the --locked clippy step that runs before maturin in the same job, so drift fails the job before a wheel is built. cargo fmt accepts no --locked (verified via --help) and does no dependency resolution. Both exclusions are documented in the SUMMARY. |
| T-261111-spy-SC | Tampering | npm/pip/cargo installs during plan execution | high | mitigate | This plan installs nothing: no install task exists, and verification uses only read-only cargo metadata --locked, which cannot alter the resolution (cargo enforces the registry checksums already recorded in both tracked locks). No [ASSUMED]/[SUS] package introduction, so no Package Legitimacy Audit table or blocking human checkpoint is warranted. |
</threat_model>

<verification>
All commands run from the repo root. Every gate below was executed live at planning time (HEAD 45205d3) and against a simulated post-change tree in /tmp; baselines are recorded so no gate can pass vacuously.

1. Insertion-shape gate (CHANGE gate — empty diff / 0 insertions pre-edit; pinned to HEAD^..HEAD after the Task 1 commit: 4 insertions, 0 removals):
   commit-range word-diff count of `{+--locked+}` = 4 and zero `[-` removal markers; commit file set (`git show --name-only --format= HEAD`) exactly `.github/workflows/benchmark.yml,.github/workflows/ci.yml`. Task 1 additionally runs the same shape check on the working tree BEFORE committing, so a malformed edit never lands in history.
2. YAML syntax + semantic coverage gate (CHANGE gate — RED pre-edit: 3 files parse, 0/4 locked, exit 1; GREEN post-commit: 4/4, exit 0):
   the python3/PyYAML gate in Task 2 parses all 3 workflows and asserts exactly 4 target-verb cargo invocations, all carrying --locked (YAML comments excluded by the parser; shell comments stripped per line).
3. Grep proof gates (CHANGE + INVARIANT — pre-edit: total 4, locked 0, negative grep lists 4 lines; post-commit: total 4, locked 4, negative grep empty):
   invocation total stays 4 (no invocation added/removed); locked count reaches 4; no target-verb invocation lacks --locked. No comment line in any workflow matches the invocation pattern (verified live), so the gates are not self-invalidated by header prose.
4. Lock-consistency gates (INVARIANT — green pre-edit, must stay green post-commit): `cargo metadata --locked` exits 0 for the root crate and pyo3/Cargo.toml; `git diff --name-only -- Cargo.lock pyo3/Cargo.lock` stays empty.
5. Scope: no src/, pyo3/, tests/, manifest, lockfile, or docs change; docs.yml untouched; exactly one executor code commit touching only the two workflow files; nothing pushed; SUMMARY.md and .planning/ artifacts left uncommitted for the orchestrator's docs commit.
6. Commit-range and clean-tree gates: shape gates are pinned to HEAD^..HEAD — the Task 1 commit (Task 2 creates no commits, so HEAD remains that commit throughout verification). Clean-tree gates require the unstaged and staged tracked-change sets to be empty after Task 1, proving the deliverable is fully committed; untracked .planning/ orchestrator artifacts are expected and excluded from these checks. Git output is captured into shell variables first (assignment status checked via &&) before any comparison, so a failing git command cannot read as clean.
</verification>

<success_criteria>
- Exactly four --locked insertions across .github/workflows/ci.yml (3) and .github/workflows/benchmark.yml (1); the commit-range word-diff (HEAD^..HEAD) proves nothing else changed.
- All 3 workflow files parse as valid YAML; grep proof shows 4/4 in-repo cargo build/test/clippy/check/run invocations carrying --locked, with the negative grep empty.
- cargo fmt, maturin, pip, pytest, toolchain actions, action versions, cache keys, and comments are byte-identical to the pre-edit state (HEAD^).
- Both lockfiles remain consistent with their manifests (cargo metadata --locked green on both crates) and unmodified.
- Exactly one atomic executor commit — `ci: adopt --locked for in-repo cargo invocations (quick-batch 261111-spy)` — touching only the two workflow files; working tree clean of tracked edits; nothing pushed. SUMMARY.md stays uncommitted (orchestrator-owned) and records the commit hash, the grep proof, and the documented exclusions (fmt, maturin, absent performance-regression.yml).
</success_criteria>

<output>
Create `.planning/quick/261111-spy-adopt-locked-in-ci-add-locked-to-cargo-build-test-clippy-che/261111-spy-SUMMARY.md` when done.
</output>
