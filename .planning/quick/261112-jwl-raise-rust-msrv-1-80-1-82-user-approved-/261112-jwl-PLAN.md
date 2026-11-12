---
phase: quick
plan: 261112-jwl
type: execute
wave: 1
depends_on: []
files_modified:
  - Cargo.toml
  - pyo3/Cargo.toml
  - .github/workflows/ci.yml
  - CLAUDE.md
  - .claude/CLAUDE.md
  - README.md
  - INSTALL.md
  - .planning/PROJECT.md
  - .planning/REQUIREMENTS.md
  - .planning/ROADMAP.md
  - .planning/WINDOWS.md
  - .planning/STATE.md
autonomous: true
requirements:
  - WINDOWS-19
  - WINDOWS-20
estimate:
  tokens: 22000
  raw_tokens: 22000
  tasks: 2
  confidence: low
must_haves:
  truths:
    - "Both crate manifests declare rust-version = \"1.82\"; no dependency requirement or lockfile changes occur."
    - "CI clippy jobs use Rust 1.82.0 with msrv182 cache namespaces, while test-root and pyo3-pytest remain on stable and both strict clippy commands remain unchanged."
    - "Current documentation and forward-looking planning guardrails state Rust 1.82; historical records of the former 1.80 policy remain historical."
    - "Rust 1.82.0 root build, root clippy, and PyO3 clippy all exit 0 with --locked; clippy uses --all-targets -- -D warnings on both crates."
    - "WINDOWS rows 19 and 20 are fixed through the CLI only after those gates pass, and windows status reports open_count 0."
  artifacts:
    - "Cargo.toml and pyo3/Cargo.toml with the 1.82 floor"
    - ".github/workflows/ci.yml with two 1.82.0 clippy pins and renamed cache namespaces"
    - "Named user docs and planning guardrails synchronized to 1.82"
    - "261112-jwl-SUMMARY.md recording the user-approved decision, toolchain version, three exit codes, code commit hash, and ledger status"
  key_links:
    - "The declared 1.82 floor matches the existing locked graph: half 2.7.1, indexmap 2.13.0, and proptest 1.9.0 remain unchanged."
    - "CI clippy toolchain and cache namespaces move together so stable and MSRV artifacts cannot mix."
    - "Successful root and PyO3 1.82 clippy runs discharge WINDOWS 19 and 20 respectively; ledger closure is evidence-gated."
---

<objective>
Implement the user-approved 2026-11-12 policy decision to RAISE Rust MSRV from 1.80 to 1.82, rather than pin or update dependencies. The current locked graph cannot satisfy 1.80: root half 2.7.1 requires 1.81, root indexmap 2.13.0 and proptest 1.9.0 require 1.82, and PyO3 indexmap 2.13.0 requires 1.82.

Purpose: Make manifests, CI, documentation, and planning guardrails agree with the existing dependency graph, then prove both crates build/lint on the new floor and close the two resulting ledger defects.
Output: ONE atomic code/config/docs commit containing exactly the ten non-ledger deliverable files, followed by uncommitted orchestrator-owned WINDOWS/STATE/SUMMARY artifacts. No src/ or pyo3/src/ changes, no public API or .rkdb changes, no dependency version changes, and no lockfile edits.

Source audit: GOAL (raise floor to match the locked graph) and CONTEXT (user chose raise, not dependency pinning) are covered by Task 1; REQ/WINDOWS-19 and WINDOWS-20 are covered by Task 1's root/PyO3 gates and Task 2's evidence-gated closures. No RESEARCH.md or deferred ideas apply to this quick item.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/WINDOWS.md
@.planning/PROJECT.md
@.planning/REQUIREMENTS.md
@.planning/ROADMAP.md
@.claude/CLAUDE.md

Grounding verified live at HEAD 0d3f6aa on dev with a clean tree:
- Cargo.toml:5 and pyo3/Cargo.toml:5 each contain exactly one `rust-version = "1.80"` line.
- Cargo.lock contains half 2.7.1, indexmap 2.13.0, and proptest 1.9.0; pyo3/Cargo.lock contains indexmap 2.13.0. Both lockfiles are tracked and clean and MUST remain byte-identical.
- .github/workflows/ci.yml has `toolchain: 1.80.0` twice (clippy-root and pyo3-build), four lines containing `1.80`, seven lines containing `msrv180`, three `dtolnay/rust-toolchain@stable` lines, and two verbatim `cargo clippy --locked --all-targets -- -D warnings` commands.
- Current-doc line-count baselines for `1.80` / `1.82`: CLAUDE.md 22/0 (19 current-policy lines plus three Recent Changes lines), .claude/CLAUDE.md 6/0, README.md 3/0, INSTALL.md 1/0.
- Planning line-count baselines: PROJECT.md 3/0 (two Constraints lines plus one historical Current state line), REQUIREMENTS.md 1/0, ROADMAP.md 4/0 (guardrail, completed 05-02 plan-list history, Phase 5 note, conditional Phase 11 criterion).
- WINDOWS status at planning time: open_count 2, fixed_count 12; rows 19 and 20 are open. The only ledger mutation commands permitted are the Task 2 CLI commands.

Execution/commit contract: Task 1 stages exactly ten files by path and makes ONE atomic commit; record its hash as CODE_COMMIT. Task 2 runs only after Task 1's gates are green. The executor may update STATE.md and must mutate WINDOWS.md via the CLI, but MUST NOT commit PLAN.md, SUMMARY.md, STATE.md, or WINDOWS.md; the orchestrator owns the docs commit. All commands below assume cwd at the checkout root. Paths in deliverable edits are repo-root-relative; the mandated ledger CLI uses `~` for the user-level GSD installation.
</context>

<!-- planner-discipline-allow: 1\.80 -->
<!-- planner-discipline-allow: msrv180 -->

<tasks>

<task type="tracer">
  <name>Task 1: Raise and synchronize MSRV, prove both crates on 1.82, and commit atomically</name>
  <files>Cargo.toml, pyo3/Cargo.toml, .github/workflows/ci.yml, CLAUDE.md, .claude/CLAUDE.md, README.md, INSTALL.md, .planning/PROJECT.md, .planning/REQUIREMENTS.md, .planning/ROADMAP.md</files>
  <precondition>The live census matches the context baselines and WINDOWS rows 19/20 are open. If any manifest, CI, doc, lockfile, or ledger baseline differs, halt and report instead of broad-replacing from stale assumptions.</precondition>
  <action>
    First re-observe every statement to be edited with `rg -n '1\.80|msrv180' Cargo.toml pyo3/Cargo.toml .github/workflows/ci.yml CLAUDE.md .claude/CLAUDE.md README.md INSTALL.md .planning/PROJECT.md .planning/REQUIREMENTS.md .planning/ROADMAP.md` and compare it with the grounded census. Install the pinned toolchain idempotently with `rustup toolchain install 1.82.0 --profile minimal --component clippy`, then record `rustc +1.82.0 --version` and `cargo +1.82.0 --version`; the rustc version must be exactly 1.82.0.

    Apply only these edits:
    1. In both manifests, replace the single package-floor value with `rust-version = "1.82"`. Do not alter dependencies, features, profiles, package versions, or lockfiles; do not run cargo update/generate-lockfile or use --ignore-rust-version.
    2. In ci.yml, change the two clippy-root/pyo3-build pins to `toolchain: 1.82.0`; replace every `msrv180` cache/comment token with `msrv182` (seven baseline lines, including keys and restore prefixes); update the two explanatory Rust 1.80 comments to 1.82. Keep test-root and pyo3-pytest on `dtolnay/rust-toolchain@stable`; keep both `cargo clippy --locked --all-targets -- -D warnings` commands verbatim and do not alter cache paths or job structure.
    3. In CLAUDE.md, raise only Active Technologies and Code Style Rust floors (19 lines) to 1.82; preserve all three Recent Changes entries verbatim as history. In .claude/CLAUDE.md update all six current Rust floor/policy statements (Constraints, Languages, Runtime, Platform Requirements, Conventions) to 1.82. In README.md update the three Rust requirements at the system requirements, PyO3 environment, and rustc troubleshooting locations. In INSTALL.md change the minimum to 1.82.0+ stable. Preserve unrelated content and all non-MSRV numbers.
    4. In PROJECT.md update only the two Constraints bullets: Tech stack becomes Rust 1.82+, and Version policy records `Rust MSRV 1.82`, `rust-version = "1.82"`, APIs available at 1.82, and `(MSRV raise user-approved 2026-11-12)`. Preserve the historical Current state account of the earlier 1.80 normalization. In REQUIREMENTS.md change only the Evidence base guardrail to MSRV 1.82; leave the unrelated rusty_alloc MSRV 1.87 rationale untouched.
    5. In ROADMAP.md update the milestone MSRV guardrail to require the 1.82 toolchain on BOTH crates, the Phase 5 Note to install Rust 1.82, and the forward-looking conditional Phase 11 criterion to MSRV 1.82-clean. Phase 6 has no 1.80 occurrence. Preserve the completed 05-02 plan-list title as historical evidence of what that plan originally delivered.

    Run each verification command separately and record its exact exit code for the SUMMARY: root `cargo +1.82.0 build --locked`, root `cargo +1.82.0 clippy --locked --all-targets -- -D warnings`, and PyO3 `cargo +1.82.0 clippy --locked --all-targets --manifest-path pyo3/Cargo.toml -- -D warnings`. All three MUST exit 0; do not close either ledger row if any fails. Do not suppress new warnings or edit source/dependencies to force green—report any unrelated failure.

    After every pre-commit gate passes, stage exactly the ten files listed in this task and make ONE commit: `git add Cargo.toml pyo3/Cargo.toml .github/workflows/ci.yml CLAUDE.md .claude/CLAUDE.md README.md INSTALL.md .planning/PROJECT.md .planning/REQUIREMENTS.md .planning/ROADMAP.md && git commit -m "build: raise Rust MSRV to 1.82 (quick 261112-jwl)"`. Do not stage WINDOWS.md, STATE.md, PLAN.md, SUMMARY.md, lockfiles, or source. Record `git rev-parse HEAD` as CODE_COMMIT and run the post-commit scope gate.
  </action>
  <verify>
    <automated>test "$(grep -c '^rust-version = "1.82"' Cargo.toml)" = "1" && test "$(grep -c '^rust-version = "1.82"' pyo3/Cargo.toml)" = "1" && test "$(rg -c '1\.80' Cargo.toml pyo3/Cargo.toml)" = ""</automated>
    <automated>test "$(rg -c 'toolchain: 1\.82\.0' .github/workflows/ci.yml)" = "2" && test "$(rg -c 'msrv182' .github/workflows/ci.yml)" = "7" && test "$(rg -c '1\.80|msrv180' .github/workflows/ci.yml)" = "" && test "$(rg -c 'dtolnay/rust-toolchain@stable' .github/workflows/ci.yml)" = "3" && test "$(rg -c 'cargo clippy --locked --all-targets -- -D warnings' .github/workflows/ci.yml)" = "2"</automated>
    <automated>test "$(rg -c '1\.82' CLAUDE.md)" = "19" && test "$(rg -c '1\.80' CLAUDE.md)" = "3" && test "$(rg -c '1\.82' .claude/CLAUDE.md)" = "6" && test "$(rg -c '1\.80' .claude/CLAUDE.md)" = "" && test "$(rg -c '1\.82' README.md)" = "3" && test "$(rg -c '1\.80' README.md)" = "" && test "$(rg -c '1\.82' INSTALL.md)" = "1" && test "$(rg -c '1\.80' INSTALL.md)" = ""</automated>
    <automated>test "$(rg -c '1\.82' .planning/PROJECT.md)" = "2" && test "$(rg -c '1\.80' .planning/PROJECT.md)" = "1" && test "$(rg -c 'MSRV raise user-approved 2026-11-12' .planning/PROJECT.md)" = "1" && test "$(rg -c 'MSRV 1\.82' .planning/REQUIREMENTS.md)" = "1" && test "$(rg -c '1\.82' .planning/ROADMAP.md)" = "3" && test "$(rg -c '1\.80' .planning/ROADMAP.md)" = "1"</automated>
    <automated>rustc +1.82.0 --version && cargo +1.82.0 --version</automated>
    <automated>cargo +1.82.0 build --locked</automated>
    <automated>cargo +1.82.0 clippy --locked --all-targets -- -D warnings</automated>
    <automated>cargo +1.82.0 clippy --locked --all-targets --manifest-path pyo3/Cargo.toml -- -D warnings</automated>
    <automated>test -z "$(git status --porcelain -- Cargo.lock pyo3/Cargo.lock src pyo3/src)" && test "$(git diff --name-only CODE_COMMIT^..CODE_COMMIT)" = "$(printf '.claude/CLAUDE.md\n.github/workflows/ci.yml\n.planning/PROJECT.md\n.planning/REQUIREMENTS.md\n.planning/ROADMAP.md\nCLAUDE.md\nCargo.toml\nINSTALL.md\nREADME.md\npyo3/Cargo.toml')"</automated>
  </verify>
  <done>All ten files carry the intended 1.82 policy with historical exceptions limited to three CLAUDE.md Recent Changes lines, one PROJECT.md Current state line, and one ROADMAP.md completed-plan line. Rust 1.82.0 build and both strict clippy commands exit 0 with unchanged lockfiles/source, and CODE_COMMIT contains exactly the ten declared files.</done>
</task>

<task type="auto">
  <name>Task 2: Close WINDOWS 19/20 against the green 1.82 evidence</name>
  <files>.planning/WINDOWS.md, .planning/STATE.md</files>
  <precondition>CODE_COMMIT exists, its scope gate passed, and all three Task 1 cargo gates exited 0; WINDOWS rows 19 and 20 are still open and open_count is 2. Halt without ledger mutation if any condition is unmet.</precondition>
  <action>
    Close the root defect with `node ~/.claude/gsd-core/bin/gsd-tools.cjs windows fixed 19`, then the PyO3 defect with `node ~/.claude/gsd-core/bin/gsd-tools.cjs windows fixed 20`. Never hand-edit WINDOWS.md; the CLI owns row status, timestamps, and count recomputation. Run `node ~/.claude/gsd-core/bin/gsd-tools.cjs windows status` and verify both rows are fixed and open_count is exactly 0 (fixed_count becomes 14, total_count stays 20).

    Update STATE.md without committing it: record the user-approved 2026-11-12 decision to raise MSRV to 1.82 for the existing locked graph (no dependency pin/update), mark the 05-02 Rust 1.80 clippy blocker resolved by the recorded 1.82 build/clippy evidence, and reference CODE_COMMIT. Do not alter unrelated phase position, decisions, or deferred items. In the SUMMARY record rustc/cargo 1.82.0 version output, the three individual cargo exit codes, CODE_COMMIT, lockfile/source immutability, and final ledger counts. Do not commit WINDOWS.md, STATE.md, PLAN.md, or SUMMARY.md.
  </action>
  <verify>
    <automated>node -e 'const {execFileSync}=require("child_process"); const s=JSON.parse(execFileSync(process.execPath,[process.env.HOME+"/.claude/gsd-core/bin/gsd-tools.cjs","windows","status"],{encoding:"utf8"})); const rows=s.ledger.entries.filter(e=>e.id===19||e.id===20); if(s.ledger.open_count!==0||s.ledger.fixed_count!==14||s.ledger.total_count!==20||rows.length!==2||!rows.every(e=>e.status==="fixed")) process.exit(1); console.log(`open_count=${s.ledger.open_count} fixed_count=${s.ledger.fixed_count} rows=${rows.map(e=>e.id+":"+e.status).join(",")}`);'</automated>
    <automated>test -n "$(git status --porcelain -- .planning/WINDOWS.md)" && test -z "$(git status --porcelain -- Cargo.lock pyo3/Cargo.lock src pyo3/src)" && test "$(git diff --name-only CODE_COMMIT^..CODE_COMMIT)" = "$(printf '.claude/CLAUDE.md\n.github/workflows/ci.yml\n.planning/PROJECT.md\n.planning/REQUIREMENTS.md\n.planning/ROADMAP.md\nCLAUDE.md\nCargo.toml\nINSTALL.md\nREADME.md\npyo3/Cargo.toml')"</automated>
  </verify>
  <done>CLI-driven WINDOWS status shows rows 19 and 20 fixed, open_count 0, fixed_count 14, total_count 20. STATE.md and the SUMMARY record the approved decision and evidence, while all planning artifacts remain uncommitted for the orchestrator and CODE_COMMIT remains the only executor commit.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| rustup distribution -> local 1.82.0 toolchain | Executor installs a pinned compiler/clippy from the configured rustup channel; version output and locked builds establish what was used. |
| manifests/CI -> developer and CI build behavior | An incomplete floor or cache rename could produce false MSRV assurance or cross-toolchain cache reuse. |
| verification evidence -> WINDOWS ship ledger | Closing rows before both crate gates pass would falsely unblock shipping. |

## STRIDE Threat Register

ASVS level 1; blocking threshold high. Threat IDs are scoped to quick item 261112-jwl.

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261112-jwl-01 | Tampering | Cargo manifests and both lockfiles | high | mitigate | Only the two rust-version values change. --locked gates plus the exact ten-file commit-scope gate prove no dependency, source, or lockfile change; no cargo update or ignore-rust-version escape is allowed. |
| T-261112-jwl-02 | Tampering | CI clippy toolchains and caches | medium | mitigate | Gates require two 1.82.0 pins, seven msrv182 lines, zero stale CI tokens, three unchanged stable toolchains, and two unchanged strict clippy commands. |
| T-261112-jwl-03 | Spoofing | WINDOWS 19/20 closure evidence | high | mitigate | Task 2 has a hard precondition on three exit-0 cargo gates and uses only the ledger CLI; parsed status must show both rows fixed and open_count 0. |
| T-261112-jwl-SC | Tampering | rustup toolchain install and locked cargo compilation | high | mitigate | Use the existing rustup distribution configuration with an exact 1.82.0 toolchain and record version output. No crate is added/updated and no dependency resolution is permitted; Cargo lockfiles and registry checksums remain authoritative. No npm/pip/cargo package-install task or new package legitimacy audit is triggered. |
</threat_model>

<verification>
Run from the checkout root and record all results in the SUMMARY:
1. Version: `rustc +1.82.0 --version` reports 1.82.0 and clippy is installed.
2. Root build: `cargo +1.82.0 build --locked` exits 0.
3. Root lint: `cargo +1.82.0 clippy --locked --all-targets -- -D warnings` exits 0.
4. PyO3 lint: `cargo +1.82.0 clippy --locked --all-targets --manifest-path pyo3/Cargo.toml -- -D warnings` exits 0.
5. Immutability: no diff in Cargo.lock, pyo3/Cargo.lock, src/, or pyo3/src/; no dependency requirement changed.
6. Text gates: Task 1 counts match their recorded baselines and expected post-change counts (`rg -c` counts matching lines, not total occurrences). CI stable/strict-clippy invariants remain 3/2.
7. Atomicity: CODE_COMMIT^..CODE_COMMIT contains exactly the ten Task 1 files. WINDOWS/STATE/PLAN/SUMMARY are outside that commit.
8. Ledger: parsed `windows status` gives rows 19/20 fixed, open_count 0, fixed_count 14, total_count 20.
</verification>

<success_criteria>
- The declared and documented MSRV is 1.82 across both manifests, both CI clippy jobs, named current docs, and all forward-looking planning guardrails.
- The existing locked dependency graph is unchanged and now passes root build plus root/PyO3 strict clippy on Rust 1.82.0.
- No source behavior, public API, .rkdb format, dependency version, lockfile, stable test job, or strict clippy command changes.
- Exactly one executor commit contains the ten code/config/docs files; the user-approved decision and all version/exit-code evidence are recorded.
- WINDOWS 19 and 20 are closed only through the CLI after green evidence, leaving open_count 0; planning artifacts remain for the orchestrator's docs commit.
</success_criteria>

<output>
Create `.planning/quick/261112-jwl-raise-rust-msrv-1-80-1-82-user-approved-/261112-jwl-SUMMARY.md` when done. Record the user-approved raise-not-pin decision, CODE_COMMIT, exact rustc/cargo versions, root build/root clippy/PyO3 clippy exit codes, unchanged lockfiles/source, and final WINDOWS counts. Task 1 already committed the ten deliverable files; leave PLAN.md, SUMMARY.md, STATE.md, and WINDOWS.md uncommitted for the orchestrator.
</output>
