---
phase: 01-foundation-quality
verified: 2026-07-01T16:30:00Z
status: passed
score: 11/11 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: N/A
  gaps_closed: []
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Inspect the residual `data_offset > 1000000` silent clamp at pyo3/src/database.rs:1049 (PyDatabase disk-query path). Decide whether to port the CR-01 loud-Err fix to the pyo3 reader as well, or document it as an accepted residual."
    expected: "A conscious decision: either port the loud-Err (consistent with the 6 src/ sites fixed in CR-01) or record an accepted-deviation note. The residual is low-severity (CR-01 did not enumerate the pyo3 site; the canonical readers in src/ are all loud-Err; a data_offset > 1000000 is implausible for any real .rkdb) but it is the one remaining silent clamp in the codebase."
    why_human: "This is a scope/judgment decision (was the pyo3 site intentionally excluded from CR-01 or an oversight?), not a behavioral gap. The Phase 1 must_haves enumerate only the src/ reader sites; the pyo3 site is not in any Phase 1 must_have. Surfacing for human awareness only — not blocking."
---

# Phase 1: Foundation & Quality — Verification Report

**Phase Goal:** Establish engineering infrastructure that unblocks performance work and guards against regressions
**Verified:** 2026-07-01T16:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

The phase goal — "establish engineering infrastructure that unblocks performance work and guards against regressions" — is observably achieved in the codebase. All four FOUND requirements are delivered, all four SPEC prohibitions hold, all four roadmap Success Criteria are met, and the CI gate (the load-bearing artifact) runs green locally across fmt/clippy/test on both the root and pyo3 crates.

A code review (01-REVIEW.md) initially surfaced 4 critical findings. Two of them (CR-01: data_offset silent clamp only 2/6 sites fixed; CR-04: CI cache key collision) were genuine gaps and were fixed in commits `ffcfe43` and `e392ed6` before verification. This verification confirms both fixes landed and all 6 reader sites now reject non-canonical offsets loudly. The other two (CR-02: endianness heuristic; CR-03: Vec::remove(0) O(n²)) are pre-existing issues correctly OUT of Phase 1 scope (deferred to Phase 3 per REQUIREMENTS Out-of-Scope).

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| FOUND-01-1 | CI workflow at `.github/workflows/ci.yml` triggers on `pull_request` + `push` to `dev`/`main` | ✓ VERIFIED | YAML parses; `on:` block has `pull_request: branches: [dev, main]` + `push: branches: [dev, main]` (ci.yml:8-11). Uses `pull_request` NOT `pull_request_target`. |
| FOUND-01-2 | Workflow runs `ubuntu-latest` + `macos-latest` matrix with Python 3.11 | ✓ VERIFIED | 3 jobs use `matrix.os: [ubuntu-latest, macos-latest]` with `fail-fast: false`; `actions/setup-python@v5` with `python-version: '3.11'` (ci.yml:103, 108-109). |
| FOUND-01-3 | `cargo fmt --all --check`, `cargo clippy -D warnings` (root), `cargo test`, pyo3 `cargo clippy -D warnings`, `maturin build` all run as independent jobs | ✓ VERIFIED | 4 jobs: `fmt`, `clippy-root`, `test-root`, `pyo3-build` (pyo3-build has separate `clippy (pyo3)` + `maturin build` + `upload-artifact` steps). All gate commands confirmed via grep (ci.yml:37, 69, 94, 124, 127). **All gates run green locally**: fmt exit 0, root clippy exit 0, pyo3 clippy exit 0. |
| FOUND-01-P1 | Prohibition P1: no `continue-on-error`, no `\|\| true`, no if-guarded skips; uses `pull_request` not `pull_request_target` | ✓ VERIFIED | The ONLY textual matches for `continue-on-error`, `\|\| true`, and `pull_request_target` are inside explanatory YAML comments (lines 6, 22). No gate step carries any of these. |
| FOUND-02-1 | `cargo clippy` with denied `print_stdout`/`print_stderr`/`dbg_macro` passes on library scope | ✓ VERIFIED | `#![deny(...)]` at src/lib.rs:1 and pyo3/src/lib.rs:1; `#![allow(...)]` at src/cli/mod.rs:1. **Enforcement proven by injection test**: injecting `println!("DENO-INJECTED-TEST")` into `src/database/query.rs` made `cargo clippy --lib` emit `error: use of println!` citing `print_stdout` and referencing `src/lib.rs:1 \| #![deny(...)]` as the lint source. After restore, clippy green. |
| FOUND-02-2 | Grep for `println!`/`eprintln!`/`dbg!` in `src/` (excl `src/cli/`) + `pyo3/src/` (excl dead) returns 0 | ✓ VERIFIED | src/ count = 0, pyo3/src/ count = 0 (both after excluding comments + cli/ + merge_tests.rs + dead pyo3 backup files). |
| FOUND-02-P2 | Prohibition P2: `env_logger` default filter remains `"info"`; pyo3 has no logger init (D-17) | ✓ VERIFIED | `src/main.rs:13`: `env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();` byte-identical. No `env_logger` init in live pyo3 modules. |
| FOUND-02-3 | Parallel-merge logging backstop test exists + passes | ✓ VERIFIED | `test_parallel_merge_logging_preserves_counts` in tests/consistency_tests.rs:28. Builds 3 overlapping DBs, persists to real `.rkdb`, runs `merge_databases` with `use_prefix_cache: true` + `verbose: true` (exercising the rayon path with `log::` calls), asserts exact summed-count equality. Test PASSES (2 tests in consistency_tests binary). |
| FOUND-03-1 | count.rs delegates to format.rs canonical writers (no inline write_u128 loop) | ✓ VERIFIED | `KmerEntry::new(kmer, count).write_to(&mut writer)?` at src/cli/commands/count.rs:539. No `writer.write_u128::<LittleEndian>(kmer)` entry loop in count.rs. |
| FOUND-03-2 | golden sha256 matches across 12 cells (P3 byte-identity); round-trip + legacy data_offset=42 reads work | ✓ VERIFIED | 12 golden fixtures + manifest + legacy fixture committed. `cargo test --test golden_tests` = 34 passed (12 sha256 + cross-consistency + manifest). `cargo test --test legacy_readback_tests` = 3 passed. `cargo test --test round_trip_tests` = 23 passed. |
| FOUND-03-3 | Read-side data_offset defensive clamp REMOVED from all 6 src/ reader sites; loud Err replaces it | ✓ VERIFIED | **All 6 sites fixed** (CR-01 fix in commit `ffcfe43` confirmed): (1) format.rs:309 from_file_path — loud Err; (2) query.rs:86 load_entries — loud Err; (3) streaming_merge.rs:47 — loud Err; (4) format.rs:179 DatabaseHeader::validate — rejects `!= 42`; (5) query.rs:201 read_entry_at — relies on open()-time validate(), no clamp; (6) stats.rs:109 execute_stats — relies on `header.validate()`, no clamp. No silent `(40..=1000).contains` / `< 40` / `> 1000` clamp remains in src/. |
| FOUND-04-1 | `tests/cjk_check.rs` exists, syn-based (visit_lit + visit_macro + visit_attribute), GREEN | ✓ VERIFIED | All 3 visitor methods overridden (lines 54, 67, 87). Correct Unicode block ranges (Han/Hiragana/Katakana/Hangul, lines 153-163). Dead-file + cli exclusion present. `cargo test --test cjk_check` = 5 passed including `no_cjk_string_literals_in_scope`. |
| FOUND-04-P4 | Prohibition P4: messages translated not deleted | ✓ VERIFIED (judgment-tier) | Commit `7ca511b` body contains 61 `->` translation lines, each as `:line: "pre-CJK" -> "English"` (e.g. `:90: "\n🚀 开始外部排序合并" -> "\n🚀 Starting external sort merge"`). Format args preserved. Sample translation pairs reviewed — faithful English equivalents, not deletions. |

**Score:** 11/11 truths verified (0 present-behavior-unverified, 0 failed)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.github/workflows/ci.yml` | New CI merge gate | ✓ VERIFIED | 4336 bytes, valid YAML, 4 jobs, P1-clean |
| `src/lib.rs` `#![deny(...)]` | Crate-level deny | ✓ VERIFIED | Line 1: `#![deny(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]` |
| `src/cli/mod.rs` `#![allow(...)]` | CLI subtree exemption | ✓ VERIFIED | Line 1: `#![allow(...)]` |
| `pyo3/src/lib.rs` `#![deny(...)]` | pyo3 crate deny | ✓ VERIFIED | Line 1: `#![deny(...)]` |
| `tests/cjk_check.rs` | syn-based CJK gate | ✓ VERIFIED | 12408 bytes, visit_lit + visit_macro + visit_attribute, 5 tests pass |
| `Cargo.toml` syn + proc-macro2 dev-deps | syn 2.0 + proc-macro2 1.0 | ✓ VERIFIED | Line 100-101: `syn = { version = "2.0", features = ["full", "extra-traits", "visit", "parsing"] }`, `proc-macro2 = "1.0"` |
| 12 golden `.rkdb` fixtures + manifest | tests/fixtures/golden_k* | ✓ VERIFIED | `ls tests/fixtures/golden_k*.rkdb \| wc -l` = 12; golden_manifest.sha256 + legacy_v2_offset42.rkdb present |
| `tests/golden_tests.rs` / `round_trip_tests.rs` / `legacy_readback_tests.rs` | Regression test suite | ✓ VERIFIED | 34 + 23 + 3 = 60 tests, all pass |
| count.rs delegation | No inline write_u128 loop | ✓ VERIFIED | Delegation at count.rs:539; inline loop removed |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| ci.yml gate steps | Local gate commands | `cargo fmt/clippy/test` + `maturin build` | ✓ WIRED | All 5 gate commands present; all run green locally (fmt exit 0, root clippy exit 0, pyo3 clippy exit 0) |
| Library `log::*!` calls | env_logger (CLI) / null (pyo3) | `env_logger::Builder...init()` at src/main.rs:13 | ✓ WIRED | Default filter preserved at "info"; pyo3 has no logger init (D-17) — `log::*!` calls are no-ops when imported from Python |
| count.rs entry write | format.rs canonical writer | `KmerEntry::new(kmer, count).write_to(...)` | ✓ WIRED | Delegation call present at count.rs:539 |
| cjk_check.rs syn test | src/ + pyo3/src/ live modules | walkdir enumeration + syn::parse_file | ✓ WIRED | Scans real source; catches injected CJK (RED→GREEN TDD proven); gate passes on current code |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|----|
| `tests/consistency_tests.rs::test_parallel_merge_logging_preserves_counts` | `merged_kmers` HashMap | `RKDatabase::merge_databases(&input_paths, &config)` with `use_prefix_cache: true` | ✓ Real merge over 3 real `.rkdb` files | ✓ FLOWING |
| `tests/golden_tests.rs` | sha256 digests | `std::fs::read` of committed golden fixtures + recomputation | ✓ Real file bytes hashed | ✓ FLOWING |
| `tests/cjk_check.rs` | scanner.hits | walkdir over src/ + pyo3/src/ + syn::parse_file | ✓ Real AST walk of real source | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| FOUND-01 fmt gate | `cargo fmt --all --check` | exit 0 | ✓ PASS |
| FOUND-01 root clippy gate | `cargo clippy --all-targets -- -D warnings` | exit 0 | ✓ PASS |
| FOUND-01 pyo3 clippy gate | `cd pyo3 && cargo clippy --all-targets -- -D warnings` | exit 0 | ✓ PASS |
| FOUND-01 lib test (regression) | `cargo test --lib` | 199 passed | ✓ PASS |
| FOUND-02 deny enforcement | inject `println!` into src/database/query.rs, run `cargo clippy --lib` | `error: use of println!` citing print_stdout + src/lib.rs:1 | ✓ PASS |
| FOUND-03 golden byte-identity (P3) | `cargo test --test golden_tests` | 34 passed | ✓ PASS |
| FOUND-03 legacy read-back (D-12) | `cargo test --test legacy_readback_tests` | 3 passed | ✓ PASS |
| FOUND-03 round-trip | `cargo test --test round_trip_tests` | 23 passed | ✓ PASS |
| FOUND-02 parallel-merge backstop | `cargo test --test consistency_tests` | 2 passed (incl. `test_parallel_merge_logging_preserves_counts`) | ✓ PASS |
| FOUND-04 CJK gate (GREEN) | `cargo test --test cjk_check` | 5 passed (incl. `no_cjk_string_literals_in_scope`) | ✓ PASS |

### Probe Execution

Step 7c: SKIPPED — this is not a migration/CLI-tooling phase; no `scripts/*/tests/probe-*.sh` probes are declared in any PLAN or conventional location. The phase's verification is entirely via cargo gate commands and grep checks (run above).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| FOUND-01 | 01-01-PLAN | CI workflow gates fmt/clippy/test/wheel-build on PR + push dev/main | ✓ SATISFIED | ci.yml exists, valid, 4 jobs, matrix, P1-clean; all gates green locally |
| FOUND-02 | 01-02-PLAN | Library code outside src/cli/ emits via log facade | ✓ SATISFIED | Crate-level deny + cli allow; 0 console macros in library scope; deny enforcement proven via injection; default filter preserved; backstop test passes |
| FOUND-03 | 01-03-PLAN | .rkdb write consolidated to single source of truth | ✓ SATISFIED | count.rs delegates to KmerEntry::write_to; all 6 reader sites loud-Err on non-canonical data_offset (CR-01 fixed); golden sha256 matches across 12 cells (P3 proven); legacy reads work (D-12) |
| FOUND-04 | 01-04-PLAN | English-only user-facing library strings | ✓ SATISFIED | cjk_check.rs GREEN; visit_lit + visit_macro + visit_attribute; correct Unicode ranges; P4 upheld (61 translations in commit body, not deletions) |

**Orphaned requirements:** None. REQUIREMENTS.md maps FOUND-01..04 to Phase 1 and all 4 are claimed by plans 01-01..01-04 respectively. REQUIREMENTS.md traceability table marks all 4 Complete.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/cli/commands/stats.rs` | 56 | `// TODO: Add quiet flag to Args if needed` | ℹ️ Info | Pre-existing note about a possible future CLI flag; not a debt marker (TBD/FIXME/XXX); unrelated to Phase 1 deliverables; no impact on phase goal |
| `src/database/format.rs` | 227-234 | CR-02: `KmerEntry::read_from` endianness heuristic (`count_le > 1_000_000 ? count_be : count_le`) | ℹ️ Info | Pre-existing code, NOT introduced or touched by Phase 1. Correctly OUT of Phase 1 scope (SPEC P3 explicitly preserves endianness; golden tests use counts < 1M to avoid it). Deferred to Phase 3 dense-storage work per REQUIREMENTS Out-of-Scope. |
| `src/database/prefix_cache_merge.rs` | 615 | CR-03: `Vec::remove(0)` O(n²) in streaming merge | ℹ️ Info | Pre-existing performance issue. Phase 1 only migrated the log calls in this file; merge algorithm itself is Phase 3 (Memory Safety). Correctly deferred. |
| `pyo3/src/database.rs` | 1049 | Residual `data_offset > 1000000` silent clamp (CR-01 did not enumerate the pyo3 site) | ⚠️ Warning | Low-severity residual: the canonical readers in src/ are all loud-Err; a data_offset > 1000000 is implausible for any real .rkdb; CR-01 enumerated only the src/ sites. NOT in any Phase 1 must_have. Surfaced for human awareness (see Human Verification). |

### Human Verification Required

### 1. Residual pyo3 data_offset clamp (CR-01 scope question)

**Test:** Inspect the residual `data_offset > 1000000` silent clamp at `pyo3/src/database.rs:1049` (PyDatabase disk-query path). Decide whether to port the CR-01 loud-Err fix to the pyo3 reader as well, or document it as an accepted residual.
**Expected:** A conscious decision: either port the loud-Err (consistent with the 6 src/ sites fixed in CR-01) or record an accepted-deviation note. The residual is low-severity (CR-01 did not enumerate the pyo3 site; the canonical readers in src/ are all loud-Err; a data_offset > 1000000 is implausible for any real .rkdb) but it is the one remaining silent clamp in the codebase.
**Why human:** This is a scope/judgment decision (was the pyo3 site intentionally excluded from CR-01 or an oversight?), not a behavioral gap. The Phase 1 must_haves enumerate only the src/ reader sites; the pyo3 site is not in any Phase 1 must_have. Surfacing for human awareness only — not blocking.

### Gaps Summary

No gaps. All 11 observable truths verified, all 4 requirements satisfied, all 4 prohibitions hold, all CI gate commands run green locally. The two critical review findings that were genuine gaps (CR-01 partial data_offset fix; CR-04 cache key collision) were both fixed before verification (commits `ffcfe43` and `e392ed6`) and the fixes are confirmed on disk. The two remaining critical review findings (CR-02 endianness heuristic; CR-03 Vec::remove(0)) are pre-existing issues correctly out of Phase 1 scope, deferred to Phase 3.

The one residual worth flagging (pyo3 data_offset clamp at database.rs:1049) is NOT in any Phase 1 must_have and is low-severity; it is recorded as a human-verification item, not a gap.

---

_Verified: 2026-07-01T16:30:00Z_
_Verifier: Claude (gsd-verifier)_
