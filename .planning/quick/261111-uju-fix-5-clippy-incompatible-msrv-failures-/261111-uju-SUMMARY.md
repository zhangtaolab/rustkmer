---
phase: quick
plan: 261111-uju
subsystem: core (cli/database/hash)
status: complete
tags: [msrv, clippy, incompatible-msrv, lint-gate, rust-1.80]
requires: ["261111-sq0 (rust-version=1.80 declaration that surfaced the lint)"]
provides: ["Root clippy -D warnings gate restored at MSRV 1.80"]
affects: [src/cli/commands/dump.rs, src/database/index.rs, src/database/prefix_cache_merge.rs, src/hash/overflow.rs]
tech-stack:
  added: []
  patterns: ["modulo-form divisibility predicate (% n == 0) for MSRV 1.80 compatibility"]
key-files:
  created: []
  modified:
    - src/cli/commands/dump.rs
    - src/database/index.rs
    - src/database/prefix_cache_merge.rs
    - src/hash/overflow.rs
decisions:
  - "Rewrote is_multiple_of(n) to % n == 0 at all 5 root sites instead of bumping MSRV or adding lint allowances — all divisors provably non-zero (4 literals; records_per_file assigned once to 1_000_000), so semantics are exactly preserved."
  - "Left the 3 pyo3/src/database.rs occurrences untouched per scope lock; recorded as follow-up candidate."
metrics:
  duration: ~4 min
  completed: 2026-11-11T14:10:49Z
  tasks: 2
  files: 4
actuals:
  tokens: 682
  tasks: 2
  commits: 1
commits: 1
plan_head_before: 179c364fd1e501afe9b7c0df0bc307765b13a97e
plan_head_after: 0872b7b502808b15c2bcfb38ef2bcdb7076bab88
---

# Quick 261111-uju: Fix 5 clippy incompatible_msrv failures Summary

Rewrote the 5 MSRV-flagged `is_multiple_of(n)` predicates to the exactly-equivalent `% n == 0` form in the 4 root source files, restoring the root `cargo clippy --all-targets -- -D warnings` CI gate at the declared MSRV 1.80 without suppressing the lint, bumping the MSRV, or changing behavior.

## Deliverable Commit

- **Task 1 (atomic code commit):** `0872b7b502808b15c2bcfb38ef2bcdb7076bab88` — `fix: rewrite is_multiple_of to % n == 0 for MSRV 1.80 (quick 261111-uju)`
- Touches exactly 4 files, 5 insertions / 5 deletions (one boolean expression per site):

| Site | Before | After |
|------|--------|-------|
| src/cli/commands/dump.rs:169 | `processed.is_multiple_of(100_000)` | `processed % 100_000 == 0` |
| src/database/index.rs:106 | `counts.len().is_multiple_of(2)` | `counts.len() % 2 == 0` |
| src/database/prefix_cache_merge.rs:599 | `done.is_multiple_of(10) \|\| done == non_empty_count` | `done % 10 == 0 \|\| done == non_empty_count` |
| src/database/prefix_cache_merge.rs:1385 | `processed_kmers.is_multiple_of(1_000_000)` | `processed_kmers % 1_000_000 == 0` |
| src/hash/overflow.rs:71 | `self.kmer_count.is_multiple_of(self.records_per_file as u64)` | `self.kmer_count % (self.records_per_file as u64) == 0` |

Equivalence basis: all 5 receivers are unsigned counters, all conditions positive (no negation flip), all divisors non-zero — four literals plus `records_per_file`, whose census (declaration line 23, single initialization to 1_000_000 at line 45, use at line 71) was re-confirmed by grep before editing. The zero-divisor divergence between std's method and `%` is unreachable at every site.

## RED / GREEN Evidence

- **RED (captured at planning time, HEAD 7e55ae1):** root `cargo clippy --all-targets -- -D warnings` exited 101 with exactly 5 errors, all `current MSRV is 1.80.0 but this item is stable since 1.87.0`, at the 5 named sites; no other error kinds.
- **GREEN (this execution, at commit 0872b7b):** root `cargo clippy --all-targets -- -D warnings` exited **0**. The reverse `manual_is_multiple_of` lint stayed silent (it is itself MSRV-gated at 1.80) — this run is the proof.
- **Behavioral backstop:** root `cargo test` exited **0** — 404 passed, 0 failed, 3 ignored (all 3 ignored tests pre-existing; no test files touched). Progress cadence (dump, prefix-cache merge), median even/odd branch (index), and overflow file rotation all evaluate identically.

## Gate Results

- **Task 1 gate chain: ALL PASS** — negative counts 1/1/2/1 -> 0; positive replacement-form counts 0 -> 1 each; `rust-version = "1.80"` count 1 in Cargo.toml; commit range HEAD^..HEAD lists exactly the 4 source files; diff adds zero `allow(` lines (3 pre-existing allowance lines untouched); deliverable tree clean.
- **Task 2 gate chain: ALL PASS** — clippy exit 0; cargo test exit 0; MSRV 1.80 in both manifests; `git status --porcelain` empty for the 4 deliverable files, both manifests, and both lockfiles. No edits were made to achieve green; the tested state is exactly Task 1's committed deliverable.
- No manifest/lock/MSRV changes, no lint allowances, no unrelated refactors, no formatters run.

## Deviations from Plan

None — plan executed exactly as written.

## Out-of-Scope Residual (follow-up candidate)

`pyo3/src/database.rs` still contains 3 occurrences of `is_multiple_of` — lines **1598, 1821, 1991** (all `exported_count.is_multiple_of(1000)`). Untouched per scope lock (verified count = 3 post-commit). `pyo3/Cargo.toml` also declares `rust-version = "1.80"` (line 5), so the **pyo3 crate's own clippy gate will flag these 3 sites** with the same incompatible_msrv error. Candidate for a follow-up quick task applying the identical `% 1000 == 0` rewrite (divisor is a non-zero literal; receiver is an unsigned counter).

## Self-Check: PASSED

- All 4 modified files exist and contain the replacement forms (gate chain above).
- Commit `0872b7b` exists at HEAD of dev (measured: `git rev-list --count 179c364..HEAD` = 1).
- SUMMARY left UNCOMMITTED per contract — the orchestrator commits docs artifacts afterwards.
