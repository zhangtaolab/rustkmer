---
phase: quick
plan: 261111-uju
type: execute
wave: 1
depends_on: []
files_modified:
  - src/cli/commands/dump.rs
  - src/database/index.rs
  - src/database/prefix_cache_merge.rs
  - src/hash/overflow.rs
autonomous: true
estimate:
  tokens: 20000
  raw_tokens: 20000
  tasks: 2
  confidence: low
must_haves:
  truths:
    - "All 5 MSRV-flagged is_multiple_of call sites in the 4 root source files use the equivalent `% n == 0` form; zero occurrences of the method remain in those files (baseline at HEAD: 1/1/2/1)."
    - "Root `cargo clippy --all-targets -- -D warnings` exits 0 — the CI gate broken by sq0's rust-version=1.80 declaration is restored (RED baseline captured at HEAD 7e55ae1: exit 101, exactly 5 incompatible_msrv errors, no other error kinds)."
    - "Root `cargo test` passes — behavior is unchanged: progress-report cadence (dump, prefix-cache merge), median even/odd branch (index), and overflow file-rotation predicate all evaluate identically."
    - "MSRV stays 1.80 in both manifests; the deliverable commit touches exactly the 4 source files — no manifest/lock changes, no added lint allowances, no unrelated refactors."
    - "The 3 out-of-scope occurrences in pyo3/src/database.rs (lines 1598, 1821, 1991) are untouched and reported in the SUMMARY as a follow-up candidate."
  artifacts:
    - "src/cli/commands/dump.rs, src/database/index.rs, src/database/prefix_cache_merge.rs, src/hash/overflow.rs with the 5 predicates rewritten to `% n == 0`."
    - "261111-uju-SUMMARY.md recording the RED/GREEN clippy evidence, the Task 1 commit hash, and the pyo3 residual."
  key_links:
    - "src/hash/overflow.rs:71 is the file-rotation predicate: kmer_count % records_per_file decides when close_current_file() runs. records_per_file is a private field assigned exactly once (line 45, 1_000_000), so the divisor is provably non-zero and the rewrite is exactly equivalent."
    - "The clippy MSRV gate reads rust-version from Cargo.toml:5 (1.80, unchanged). The reverse lint (manual_is_multiple_of) is itself MSRV-gated and stays silent at 1.80 — Task 2's green gate is the proof."
---

<objective>
Fix the 5 `clippy::incompatible_msrv` failures surfaced by quick task 261111-sq0's `rust-version = "1.80"` declaration (user-approved follow-up 2026-11-11, recorded in STATE.md Operator Next Steps). Rewrite each flagged `is_multiple_of(n)` call to the semantically equivalent `% n == 0` form in the 4 root source files, keeping MSRV 1.80 unchanged, then prove the root clippy gate and test suite are green again.

Purpose: `is_multiple_of` stabilized in Rust 1.87, so under the declared 1.80 MSRV clippy rejects it and the CI lint gate (`-D warnings`) fails. The modulo form is available on all supported compilers and is exactly equivalent here because every divisor is provably non-zero. This restores the gate without suppressing it, bumping the MSRV, or changing behavior on either delivery surface (CLI + pyrustkmer share these core paths).

Output: the 4 source files with 5 rewritten predicates, ONE atomic code commit (Task 1), a green clippy + test battery (Task 2), and a SUMMARY with RED/GREEN evidence and the pyo3 residual. The executor commits the code atomically; the orchestrator commits docs artifacts (PLAN/SUMMARY/STATE) afterwards.

Grounded facts (verified live at planning time, HEAD 7e55ae1, clean tree):
- RED baseline: `cargo clippy --all-targets -- -D warnings` (root) exits 101 with EXACTLY 5 errors, all `current MSRV is 1.80.0 but this item is stable since 1.87.0`, at src/cli/commands/dump.rs:169:30, src/database/index.rs:106:44, src/database/prefix_cache_merge.rs:599:25, src/database/prefix_cache_merge.rs:1385:40, src/hash/overflow.rs:71:32. No other error kinds in the log.
- Repo-wide census: 8 occurrences of the method — the 5 root sites above PLUS 3 in pyo3/src/database.rs (1598, 1821, 1991, all `exported_count.is_multiple_of(1000)`). The pyo3 sites are OUT OF SCOPE (scope lock: 4 root files; verification gate is root-only). Report them, do not edit them.
- All 5 root receivers are unsigned counters and all 5 conditions are positive (non-negated) — no `!` to flip. Divisors: four non-zero literals (100_000; 2; 10; 1_000_000) and `self.records_per_file as u64` in overflow.rs, whose field is assigned exactly once (line 45: `records_per_file: 1_000_000`; only other mentions are the field decl at line 23 and the use at line 71). Zero-divisor behavior therefore cannot differ (std's method returns `self == 0` for a zero divisor while `% 0` panics — unreachable at all 5 sites).
- Gate baselines at HEAD: negative counts 1 (dump), 1 (index), 2 (prefix_cache_merge), 1 (overflow); the five positive replacement-form counts are all 0; `rust-version = "1.80"` count is 1 in each manifest; the 4 files contain 3 pre-existing `allow(` lines that must remain untouched.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md

Relevant current files (repo-root-relative; line numbers verified at HEAD, locate by content if shifted):
- `src/cli/commands/dump.rs:169` — progress-report predicate inside the dump loop.
- `src/database/index.rs:106` — even/odd branch selecting the median formula.
- `src/database/prefix_cache_merge.rs:599` — parallel-merge progress predicate (disjunction with `done == non_empty_count`).
- `src/database/prefix_cache_merge.rs:1385` — streaming-write progress predicate (multi-line disjunction with a 5-second elapsed check).
- `src/hash/overflow.rs:71` — file-rotation predicate; field `records_per_file` declared line 23, initialized line 45.
- `Cargo.toml:5` and `pyo3/Cargo.toml:5` — `rust-version = "1.80"`. READ-ONLY evidence; do not edit.

Scope lock: the 4 source files ONLY. No manifest/lock/MSRV changes, no lint allowances, no unrelated refactors, no pyo3/src/ edits. The executor commits exactly these 4 files in ONE atomic code commit (Task 1); the orchestrator commits docs artifacts (PLAN/SUMMARY/STATE) afterwards. Do NOT touch BATCH.json, STATE.md, or ROADMAP.md.
</context>

<!-- planner-discipline-allow: is_multiple_of -->
<!-- planner-discipline-allow: % 100_000 == 0 -->
<!-- planner-discipline-allow: counts.len() % 2 == 0 -->
<!-- planner-discipline-allow: done % 10 == 0 -->
<!-- planner-discipline-allow: processed_kmers % 1_000_000 == 0 -->
<!-- planner-discipline-allow: self.kmer_count % (self.records_per_file as u64) == 0 -->

<tasks>

<task type="auto">
  <name>Task 1: Rewrite the 5 MSRV-flagged predicates to modulo form and commit atomically</name>
  <files>src/cli/commands/dump.rs, src/database/index.rs, src/database/prefix_cache_merge.rs, src/hash/overflow.rs</files>
  <action>
    Locate the call sites by content, not line number: `grep -n 'is_multiple_of' src/cli/commands/dump.rs src/database/index.rs src/database/prefix_cache_merge.rs src/hash/overflow.rs` must show exactly 5 hits (1/1/2/1). If the census differs, STOP and report — do not improvise extra edits.

    Rewrite each predicate in place, changing ONLY the boolean expression — preserve surrounding control flow, disjuncts, comments, and formatting. All five are positive conditions on unsigned receivers with non-zero divisors, so `x.is_multiple_of(n)` becomes `x % n == 0` with no negation flip:
    (a) src/cli/commands/dump.rs:169 — receiver `processed`, literal divisor: the condition becomes `processed % 100_000 == 0`.
    (b) src/database/index.rs:106 — receiver `counts.len()`: the condition becomes `counts.len() % 2 == 0`.
    (c) src/database/prefix_cache_merge.rs:599 — receiver `done`: the condition becomes `done % 10 == 0 || done == non_empty_count` (keep the second disjunct verbatim).
    (d) src/database/prefix_cache_merge.rs:1385 — receiver `processed_kmers`, multi-line condition: the first line becomes `processed_kmers % 1_000_000 == 0`; keep the `|| last_report.elapsed().as_secs() >= 5` continuation and braces exactly as they are.
    (e) src/hash/overflow.rs:71 — receiver `self.kmer_count`, expression divisor: the condition becomes `self.kmer_count % (self.records_per_file as u64) == 0` (keep the cast parenthesized). Before editing, re-confirm `grep -n 'records_per_file' src/hash/overflow.rs` shows only the declaration (line 23), the single initialization to 1_000_000 (line 45), and this use — i.e. the divisor can never be zero. If any other assignment exists, STOP and report.

    Do NOT touch the 3 occurrences in pyo3/src/database.rs (out of scope — record them in the SUMMARY as a follow-up candidate). Do NOT add lint-allowance attributes (the 3 pre-existing `allow(` lines in these files stay untouched), do NOT edit manifests or lockfiles, do NOT bump the MSRV, do NOT run formatters or refactor anything else.

    Then stage EXACTLY the 4 deliverable files and create ONE atomic code commit: `git add src/cli/commands/dump.rs src/database/index.rs src/database/prefix_cache_merge.rs src/hash/overflow.rs` then `git commit -m "fix: rewrite is_multiple_of to % n == 0 for MSRV 1.80 (quick 261111-uju)"` (no co-author trailer, matching prior quick-task convention). Do NOT stage the SUMMARY or any .planning/ file. Record the commit hash for the SUMMARY.
  </action>
  <verify>
    <automated>test "$(grep -c 'is_multiple_of' src/cli/commands/dump.rs)" = "0" && test "$(grep -c 'is_multiple_of' src/database/index.rs)" = "0" && test "$(grep -c 'is_multiple_of' src/database/prefix_cache_merge.rs)" = "0" && test "$(grep -c 'is_multiple_of' src/hash/overflow.rs)" = "0" && test "$(grep -c '% 100_000 == 0' src/cli/commands/dump.rs)" = "1" && test "$(grep -c 'counts.len() % 2 == 0' src/database/index.rs)" = "1" && test "$(grep -c 'done % 10 == 0' src/database/prefix_cache_merge.rs)" = "1" && test "$(grep -c 'processed_kmers % 1_000_000 == 0' src/database/prefix_cache_merge.rs)" = "1" && test "$(grep -c 'self.kmer_count % (self.records_per_file as u64) == 0' src/hash/overflow.rs)" = "1" && test "$(grep -c 'rust-version = "1.80"' Cargo.toml)" = "1" && D=$(git diff --name-only HEAD^..HEAD) && test "$(printf '%s\n' "$D" | LC_ALL=C sort | tr '\n' ',')" = "src/cli/commands/dump.rs,src/database/index.rs,src/database/prefix_cache_merge.rs,src/hash/overflow.rs," && DIFF=$(git diff HEAD^..HEAD) && test "$(printf '%s\n' "$DIFF" | grep -c '^+.*allow(')" = "0" && S=$(git status --porcelain -- src/cli/commands/dump.rs src/database/index.rs src/database/prefix_cache_merge.rs src/hash/overflow.rs) && test -z "$S"</automated>
  </verify>
  <done>The 4 files contain zero occurrences of the method (baselines 1/1/2/1, so the negative gates fail before the edit and pass after) and exactly one occurrence each of the five replacement forms (baselines all 0); MSRV is still 1.80; ONE atomic commit (HEAD) touches exactly the 4 source files and adds no allowance lines; the working tree is clean of deliverable edits. The 3 pyo3 occurrences remain untouched.</done>
</task>

<task type="auto">
  <name>Task 2: Verify the restored clippy gate and the full test suite</name>
  <files>src/cli/commands/dump.rs, src/database/index.rs, src/database/prefix_cache_merge.rs, src/hash/overflow.rs</files>
  <action>
    Verification-only task — make NO edits and create NO new commit; this runs AFTER Task 1's atomic code commit and measures the committed deliverable. From the repo root:
    (a) `cargo clippy --all-targets -- -D warnings` — must exit 0. Planning-time RED baseline at HEAD 7e55ae1 was exit 101 with exactly 5 incompatible_msrv errors; this is the GREEN proof that the gate is restored. The modulo form is not flagged back by the reverse manual-is-multiple-of lint because that lint is MSRV-gated and silent at 1.80 — this run is the evidence.
    (b) `cargo test` — the full root suite must pass, proving the rewrites are behavior-preserving (progress cadence, median branch, overflow file rotation).
    (c) Confirm both manifests still declare `rust-version = "1.80"` and the working tree is clean of deliverable and manifest/lock edits.
    If any gate fails for a reason unrelated to the 5 rewrites, REPORT it rather than editing unrelated source to force green — the deliverable is locked to the 4 files already committed in Task 1. Do not run pytest, maturin, or benchmarks; do not push.
  </action>
  <verify>
    <automated>cargo clippy --all-targets -- -D warnings && cargo test && test "$(grep -c 'rust-version = "1.80"' Cargo.toml)" = "1" && test "$(grep -c 'rust-version = "1.80"' pyo3/Cargo.toml)" = "1" && S=$(git status --porcelain -- src/cli/commands/dump.rs src/database/index.rs src/database/prefix_cache_merge.rs src/hash/overflow.rs Cargo.toml pyo3/Cargo.toml Cargo.lock pyo3/Cargo.lock) && test -z "$S"</automated>
  </verify>
  <done>`cargo clippy --all-targets -- -D warnings` exits 0 (RED→GREEN against the captured exit-101 baseline); `cargo test` passes the full root suite; MSRV is 1.80 in both manifests; no file was modified to achieve green — the tested state is exactly Task 1's committed deliverable.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| executor edit -> shared-core predicates | The 5 predicates drive progress reporting, median selection, and overflow file rotation in code paths shared by the CLI and pyrustkmer; a semantically wrong rewrite silently changes behavior on both surfaces. |
| source tree -> CI clippy MSRV gate | The gate reads rust-version from the manifests; suppressing the lint or bumping the MSRV would silently disable a regression gate instead of fixing the code. |

## STRIDE Threat Register

ASVS level 1; blocking threshold high. Threat IDs are scoped to this quick item (261111-uju).

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261111-uju-01 | Tampering | The 5 rewritten predicates, esp. src/hash/overflow.rs:71 file rotation | medium | mitigate | Operand-order/negation/zero-divisor drift would change rotation or reporting behavior. All 5 sites are positive conditions with provably non-zero divisors (4 literals; records_per_file assigned once to 1_000_000 — re-confirmed by grep in Task 1 before editing). The per-site equivalence table pins the exact replacement forms (positive grep gates), and the full cargo test suite (Task 2) is the behavioral backstop. |
| T-261111-uju-02 | Tampering | CI MSRV gate (rust-version declaration / clippy configuration) | medium | mitigate | Gate bypass via lint suppression or MSRV bump is forbidden: the commit-range gate confines the deliverable to exactly the 4 source files, a diff gate asserts zero added allowance lines, and count gates assert rust-version stays 1.80 in both manifests. |
| T-261111-uju-SC | Tampering | cargo build/clippy/test during verification (supply chain) | low | accept | No package-install tasks and no new dependencies — only already-vetted, locked crates are compiled. No [ASSUMED]/[SUS] package-legitimacy audit or blocking human checkpoint is warranted; cargo continues to enforce registry checksums. |
</threat_model>

<verification>
Run from the repo root (all baselines recorded live at planning HEAD 7e55ae1):

1. RED baseline (already captured at planning time): `cargo clippy --all-targets -- -D warnings` exited 101 with exactly 5 incompatible_msrv errors at the 5 named sites and no other error kinds. Task 2 must turn this GREEN (exit 0).
2. Task 1 gate chain (negative counts baseline 1/1/2/1 -> 0; positive replacement-form counts baseline 0 -> 1; MSRV count invariant 1; commit-range gates measure Task 1's deliverable commit HEAD^..HEAD; the 3 pre-existing allowance lines in the 4 files stay untouched and the diff adds none):
   `test "$(grep -c 'is_multiple_of' src/cli/commands/dump.rs)" = "0" && test "$(grep -c 'is_multiple_of' src/database/index.rs)" = "0" && test "$(grep -c 'is_multiple_of' src/database/prefix_cache_merge.rs)" = "0" && test "$(grep -c 'is_multiple_of' src/hash/overflow.rs)" = "0" && test "$(grep -c '% 100_000 == 0' src/cli/commands/dump.rs)" = "1" && test "$(grep -c 'counts.len() % 2 == 0' src/database/index.rs)" = "1" && test "$(grep -c 'done % 10 == 0' src/database/prefix_cache_merge.rs)" = "1" && test "$(grep -c 'processed_kmers % 1_000_000 == 0' src/database/prefix_cache_merge.rs)" = "1" && test "$(grep -c 'self.kmer_count % (self.records_per_file as u64) == 0' src/hash/overflow.rs)" = "1" && test "$(grep -c 'rust-version = "1.80"' Cargo.toml)" = "1" && D=$(git diff --name-only HEAD^..HEAD) && test "$(printf '%s\n' "$D" | LC_ALL=C sort | tr '\n' ',')" = "src/cli/commands/dump.rs,src/database/index.rs,src/database/prefix_cache_merge.rs,src/hash/overflow.rs," && DIFF=$(git diff HEAD^..HEAD) && test "$(printf '%s\n' "$DIFF" | grep -c '^+.*allow(')" = "0" && S=$(git status --porcelain -- src/cli/commands/dump.rs src/database/index.rs src/database/prefix_cache_merge.rs src/hash/overflow.rs) && test -z "$S"`
3. `cargo clippy --all-targets -- -D warnings && cargo test` — both exit 0 (run after Task 1's commit).
4. `git diff --name-only HEAD^..HEAD` lists exactly the 4 source files. pyo3/src/database.rs still contains its 3 occurrences (untouched residual, reported in SUMMARY).
</verification>

<success_criteria>
- The 5 MSRV-flagged call sites use `% n == 0` with identical semantics; zero occurrences of the method remain in the 4 root files.
- Root `cargo clippy --all-targets -- -D warnings` exits 0 (restored from the captured exit-101 RED baseline) and root `cargo test` passes.
- MSRV remains 1.80 in both manifests; no lint allowances added; no manifest/lock/test/doc changes.
- Exactly ONE atomic code commit (Task 1) touches the 4 source files; the working tree is clean of deliverable edits afterwards.
- SUMMARY records the RED/GREEN evidence, the commit hash, and the 3-site pyo3/src/database.rs residual as a follow-up candidate. SUMMARY.md stays uncommitted — the orchestrator commits docs artifacts (PLAN/SUMMARY/STATE) afterwards.
</success_criteria>

<output>
Create `.planning/quick/261111-uju-fix-5-clippy-incompatible-msrv-failures-/261111-uju-SUMMARY.md` when done. Record: (1) the RED baseline (exit 101, 5 incompatible_msrv errors at the named sites) and the GREEN clippy/test results; (2) the Task 1 code commit hash; (3) the out-of-scope residual: pyo3/src/database.rs lines 1598/1821/1991 still use the method and pyo3/Cargo.toml also declares rust-version 1.80, so the pyo3 crate's own clippy gate will flag them — candidate for a follow-up quick task. The 4 deliverable files were already committed atomically in Task 1 — leave SUMMARY.md itself UNCOMMITTED; the orchestrator commits docs artifacts (PLAN/SUMMARY/STATE) afterwards. Do NOT touch BATCH.json, STATE.md, or ROADMAP.md.
</output>
