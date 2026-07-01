---
phase: 01-foundation-quality
plan: 04
subsystem: cross-cutting
tags: [i18n, cjk-gate, syn, lint, english-only, found-04, p4-translate]
requires:
  - 01-01 (clippy-clean baseline the gate must preserve)
  - 01-02 (log facade migration; the translated strings live inside log::info!/log::error!)
  - 01-03 (syn + proc-macro2 dev-deps pre-staged; clippy-clean baseline)
provides:
  - "Self-enforcing syn-based CJK string-literal gate (tests/cjk_check.rs) — catches future CJK regressions on PR"
  - "tests/cjk_check.rs: visit_lit + visit_macro + visit_attribute (#[doc] skip) + Unicode block ranges"
  - "All src/database/prefix_cache_merge.rs user-facing strings in English (the 51-CJK epicenter)"
  - "FOUND-04 delivered: English-only user-facing library strings + automated gate"
affects:
  - "Any future PR adding a CJK literal to src/ (excl cli/) or pyo3/src/ (excl dead) will fail cargo test --test cjk_check"
  - "tests/cjk_check.rs is part of the FOUND-01 clippy gate surface — must stay fmt/clippy clean"
tech-stack:
  added:
    - "syn 2.0 features [extra-traits, visit] (added on top of 01-03's [full, parsing])"
  patterns:
    - "syn::visit::Visit triad overriding visit_lit (bare literals) + visit_macro (macro-embedded literals via TokenTree walk) + visit_attribute (#[doc] skip)"
    - "Unicode block-range CJK detector (char ranges, not bytes — handles supplementary planes)"
    - "P4 traceability via commit-message file:line: pre-CJK -> English pairs (grep -c '->')"
key-files:
  created:
    - tests/cjk_check.rs
  modified:
    - Cargo.toml
    - src/database/prefix_cache_merge.rs
decisions:
  - "D-07 (syn-based CJK test) delivered: tests/cjk_check.rs uses syn::visit::Visit overriding BOTH visit_lit (catches bare Lit::Str) AND visit_macro (walks proc_macro2::TokenTree recursively to catch every CJK literal inside println!/format!/eprintln!/log::*! macro bodies). Verified load-bearing: a visit_lit-only visitor would silently miss all 51 macro-embedded CJK strings in prefix_cache_merge.rs (RESEARCH.md §1)."
  - "Rule 3 auto-fix (blocking): extended the visitor with a THIRD override, visit_attribute, that skips Lit::Str literals inside #[doc = \"...\"] attributes. rustc desugars /// and //! doc-comments into #[doc] attributes, so syn parses their text as Lit::Str — without this skip, every /// 中文 doc-comment would false-positive as a CJK string literal. SPEC boundary explicitly defers code comments; the visit_attribute override makes the test match the stated scope. This surfaced 30 pyo3 hits that were ALL doc-comments (zero non-comment quoted CJK strings exist in pyo3/src live modules — verified by grep)."
  - "P4 upheld (judgment-tier): every former CJK literal in src/database/prefix_cache_merge.rs has a faithful English replacement of equivalent meaning. Format args ({}, {:.1}s, {:?}) preserved verbatim — only the literal text changed. No literal was deleted or emptied. The Task 2 commit message enumerates 55 file:line: 'pre-CJK' -> 'English' pairs as the traceability artifact (git log -1 --format=%B | grep -c '->' = 61; 55 with explicit file:line: prefix)."
  - "Span line-lookup fallback: proc_macro2::Span::start() requires the proc-macro feature (nightly-only). Outside a real proc-macro context, byte offsets are not portably accessible. The test scans source lines for the literal value text post-hoc — reliable for the report-what-to-translate purpose, and any line ambiguity does not affect the pass/fail verdict."
metrics:
  duration: ~26 min
  completed: 2026-07-01
  tasks: 2/2
  files-created: 1
  files-modified: 2
  literals-translated: 51 (src/database/prefix_cache_merge.rs)
  tests-added: 5 (1 gate + 4 sanity helpers)
  commits: 2
status: complete
---

# Phase 1 Plan 04: CJK->English Translation + syn-based CJK Gate Summary

Translated every user-facing CJK (Chinese) string literal in `src/database/prefix_cache_merge.rs` to English and added a self-enforcing `syn`-based CJK detection test (`tests/cjk_check.rs`) that walks BOTH `visit_lit` and `visit_macro` (plus `visit_attribute` for `#[doc]` skip) so future CJK regressions fail on PR. Delivers FOUND-04 (English-only library strings) and the automated gate that makes the policy stick.

## What Was Built

### Task 1 — `tests/cjk_check.rs` (RED gate, D-07)

The syn-based CJK detector implementing the RESEARCH.md §1 verified skeleton:

- **`struct CjkLiteralScanner`** implementing `syn::visit::Visit<'ast>`.
- **`fn visit_lit`** — matches `Lit::Str`, calls `contains_cjk(&ls.value())`. Catches bare string literals: `let s = "...";`, raw strings, mixed strings.
- **`fn visit_macro`** (load-bearing) — clones `macro.tokens`, iterates `proc_macro2::TokenTree`, calls `collect_str_lits` recursively. Catches every CJK literal embedded in `println!`/`format!`/`eprintln!`/`log::info!`/`log::error!`/`log::warn!` macro bodies. A `visit_lit`-only visitor SILENTLY MISSES these because syn parses macro arguments as a raw `TokenStream`, not as a `Lit::Str` AST node. RESEARCH.md §1 verified this empirically — without `visit_macro`, all 51 CJK strings in `prefix_cache_merge.rs` would be invisible.
- **`fn visit_attribute`** (Rule 3 auto-fix) — pushes a flag on entry to any `#[doc = "..."]` attribute and pops on exit; `visit_lit` consults the stack to skip the contained literal. rustc desugars `///` and `//!` doc-comments into `#[doc]` attributes, so without this skip every Chinese doc-comment would false-positive. SPEC boundary explicitly defers code comments; the override makes the test match the stated scope.
- **`fn collect_str_lits`** — recurses through `TokenTree::Literal` (re-parses as `LitStr` via `syn::parse2`) and `TokenTree::Group` (descends into nested parens/braces).
- **`fn contains_cjk`** — exact Unicode block ranges per SPEC edge R4/encoding:
  - Han: U+4E00-9FFF + Ext A U+3400-4DBF + Ext B U+20000-2A6DF
  - Hiragana: U+3040-309F
  - Katakana: U+30A0-30FF + Phonetic Ext U+31F0-31FF
  - Hangul: Syllables U+AC00-D7AF + Jamo U+1100-11FF + Compat Jamo U+3130-318F
  - Emoji and Latin correctly EXCLUDED (verified by the `contains_cjk_allows_emoji_and_latin` sanity test).
- **`fn is_dead_pyo3_file` / `fn is_cli_file`** — exclude the FOUND-04 boundary (`src/cli/**`) and the dead pyo3 files (`*_backup*`, `*new_approaches*`, `*stage1_fix_backup*` — git-tracked but not compiled; RESEARCH.md §1 A1).
- **Source enumeration via `walkdir`** (already a production dep): `src/**/*.rs` (excl `src/cli/`) + `pyo3/src/**/*.rs` (excl dead files).
- **4 sanity tests** pinning each Unicode block detector and confirming emoji/Latin/Cyrillic are NOT flagged, plus dead-file and cli-file exclusion patterns.

### `Cargo.toml` — syn features completed

Extended 01-03's `syn = { version = "2.0", features = ["full", "parsing"] }` with `extra-traits` and `visit` (required for `syn::visit::Visit`). `proc-macro2 = "1.0"` was already present from 01-03.

### Task 2 — Translation to GREEN (src/database/prefix_cache_merge.rs)

Translated all 51 user-facing CJK string literals in `src/database/prefix_cache_merge.rs` (the epicenter) to English of equivalent meaning. Examples:

- `log::info!("\n🚀 开始外部排序合并")` → `log::info!("\n🚀 Starting external sort merge")`
- `log::info!("   输入文件: {} 个", self.input_files.len())` → `log::info!("   Input files: {}", self.input_files.len())`
- `anyhow::anyhow!("无法打开文件 {}: {}", file_path.display(), e)` → `anyhow::anyhow!("Failed to open file {}: {}", file_path.display(), e)`
- `log::warn!("   ⚠️  警告: 预估内存需求超过可用内存！")` → `log::warn!("   ⚠️  Warning: estimated memory exceeds available memory!")`

**Format args preserved verbatim** — `{}`, `{:.1}s`, `{:?}`, `{:.1} MB` position and args unchanged; only the literal text was translated. **P4 upheld**: no literal was deleted or emptied; each has a faithful English replacement.

The 30 CJK "hits" reported by `cjk_check` in `pyo3/src/{database,prefix_query,fuzzy_query}.rs` were ALL `///` doc-comments (zero non-comment quoted CJK strings exist in pyo3/src live modules — verified via `grep -rnE '"[^"]*<CJK>'`). They are correctly excluded by the `visit_attribute` `#[doc]` skip and remain out of scope per the SPEC boundary (comments deferred).

## Verification Results

All gates GREEN after Task 2:

| Gate | Result |
|------|--------|
| `cargo test --test cjk_check` | 5 passed (gate GREEN — 0 CJK literals in scope) |
| `cargo test --lib` | 199 passed (no behavioral regression) |
| `cargo test --test golden_tests` | 34 passed (P3 byte-identity preserved — refactor didn't touch write path) |
| `cargo clippy --all-targets -- -D warnings` (root) | 0 errors |
| `cargo clippy --all-targets -- -D warnings` (pyo3) | 0 errors |
| `cargo fmt --all --check` | clean |

**P4 traceability verified**: `git log -1 --format=%B | grep -c '\->'` returns 61; `grep -cE '^\s+:[0-9]+:'` returns 55 file:line translation entries (>= the 51 literals fixed, accounting for fmt-induced line shifts).

## Acceptance Criteria

All Task 1 + Task 2 acceptance grep checks pass:
- `grep -q 'syn = { version = "2"' Cargo.toml && grep -q 'proc-macro2 = "1' Cargo.toml` — dev-deps present (from 01-03)
- `grep -q 'features = \["full", "extra-traits", "visit", "parsing"\]' Cargo.toml` — required syn features completed
- `test -f tests/cjk_check.rs` — gate exists
- `grep -q 'fn visit_lit' tests/cjk_check.rs && grep -q 'fn visit_macro' tests/cjk_check.rs && grep -q 'fn visit_attribute' tests/cjk_check.rs` — all THREE visitor methods overridden (visit_attribute is the doc-skip auto-fix)
- `grep -qE '4E00|3400|AC00|3040|30A0' tests/cjk_check.rs` — Unicode block ranges present
- `grep -qE 'backup|new_approaches|stage1_fix_backup' tests/cjk_check.rs` — dead-file exclusion present
- `cargo test --test cjk_check --no-run` exits 0 — test compiles
- `cargo test --test cjk_check` exits 0 — GREEN, zero CJK literals in scope (was RED before Task 2)
- `cargo test --lib` exits 0 — no behavioral regression
- `cargo clippy --all-targets -- -D warnings` (root + pyo3) green
- `cargo fmt --all --check` clean
- Task 2 commit message enumerates `file:line: "pre-CJK" -> "English"` pairs — grep-checkable as `git log -1 --format=%B | grep -c '\->'` = 61 (>= 51 hits fixed)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] syn flags `#[doc = "..."]` attribute literals — added `visit_attribute` override**

- **Found during:** Task 2 (after translating prefix_cache_merge.rs, cjk_check still reported 30 hits in pyo3/src/{database,prefix_query,fuzzy_query}.rs)
- **Issue:** The plan stated "DO NOT translate CJK in CODE COMMENTS (out of scope per SPEC boundary — comments deferred). The syn test only scans string literals, so comments are naturally ignored". This is a research gap: rustc desugars `///` and `//!` doc-comments into `#[doc = "..."]` attributes, and syn parses the doc text as a `Lit::Str` inside that attribute. So a `/// 获取k-mer大小` doc-comment appears to the test as a CJK string literal and would false-positive. All 30 pyo3 "hits" were `///` doc-comments (verified: zero non-comment quoted CJK strings exist in pyo3/src live modules).
- **Fix:** Added a third visitor override `visit_attribute` that pushes a flag on entry to any `#[doc]` attribute (matched via `i.path().is_ident("doc")`) and pops on exit; `visit_lit` consults the top of the stack to skip the contained literal. This precisely matches the plan's stated scope ("comments are naturally ignored") — without it, the test would over-report and force translating doc-comments the SPEC explicitly defers.
- **Files modified:** tests/cjk_check.rs (committed in Task 2 because the deviation surfaced during Task 2 translation)
- **Commit:** 7ca511b

**2. [Rule 1 - Bug] `proc_macro2::Span::start()` not available outside proc-macro context**

- **Found during:** Task 1 (compile error E0599: no method named `start` found for `&Span`)
- **Issue:** The RESEARCH.md §1 verified skeleton referenced `span.start()` for line lookup, but `proc_macro2::Span::start()` requires the `proc-macro` feature on `proc-macro2`, which is gated to nightly and only works inside an actual proc-macro context. On stable, the API is unavailable.
- **Fix:** Replaced span-based line lookup with a source-text scan in `locate_line(source, literal_value)`: iterate `source.lines()`, return the 1-based index of the first line containing the literal value. Reliable for the report-what-to-translate purpose; any line ambiguity does not affect the pass/fail verdict. Falls back to line 1 if the literal value isn't found (which never happens for real hits — the literal came from the source).
- **Files modified:** tests/cjk_check.rs
- **Commit:** d56a094

**3. [Rule 1 - Bug] Sanity test used Bopomofo char (U+3105) outside the Hangul Compat Jamo range**

- **Found during:** Task 1 (RED state verification — `contains_cjk_detects_each_block` failed)
- **Issue:** The sanity test asserted `contains_cjk("ㄅ")` expecting it to be in Hangul Compatibility Jamo (U+3130-318F), but `ㄅ` is U+3105 (Bopomofo), which is correctly NOT in any of the SPEC-named ranges.
- **Fix:** Changed the test char to `ㄱ` (U+3131), an actual Hangul Compatibility Jamo character. The detector ranges are unchanged — the test was wrong, not the ranges.
- **Files modified:** tests/cjk_check.rs
- **Commit:** d56a094

### Auth Gates

None — no auth-gated operations in this plan.

### Threat Flags

None — the only trust-boundary surface (syn + proc-macro2 dev-deps supply chain) is already tracked in the plan's threat model as T-04-01 (low, accept; both packages verified via Package Legitimacy Audit in RESEARCH.md). They are dev-deps and never compiled into the release binary or pyo3 cdylib. T-04-02 (error message language change) is also tracked and accepted — translating error messages changes the language but not the information content; no secrets present (STACK.md).

## Known Stubs

None. The CJK gate is fully wired — it scans real source files, parses them with syn, walks the AST, and asserts on real hits. The translations are real English replacements (not placeholders) backed by the P4 traceability artifact in the commit message.

## TDD Gate Compliance

The plan marked both tasks as `tdd="true"`. This IS a classic RED→GREEN cycle, unlike 01-03's baseline-preservation pattern:

1. **RED gate commit** (d56a094, `test(01-04):`): the `cjk_check` test was written and verified to FAIL against the current (pre-translation) code — it found the 51 CJK literals in `prefix_cache_merge.rs` + 30 doc-comment "hits" in pyo3 (which the Rule 3 deviation later correctly excluded). The RED state proves the test actually works.
2. **GREEN gate commit** (7ca511b, `feat(01-04):`): Task 2 translated every flagged literal, turning the test GREEN. `cargo test --test cjk_check` now reports `5 passed; 0 failed`.

TDD gate compliance: satisfied in the classic RED→GREEN sense. The MVP+TDD gate was inactive (`mvp_mode: false` in STATE.md), so the behavior-adding-task gate did not apply.

## Self-Check: PASSED

**Files created/modified (all FOUND):**
- tests/cjk_check.rs (new — gate + 4 sanity tests)
- Cargo.toml (syn features completed: full, extra-traits, visit, parsing)
- src/database/prefix_cache_merge.rs (51 literals translated)
- .planning/phases/01-foundation-quality/01-04-SUMMARY.md (this file)

**Commits (all FOUND in `git log --all`):**
- d56a094 (Task 1: RED gate)
- 7ca511b (Task 2: GREEN translation + visit_attribute deviation)
