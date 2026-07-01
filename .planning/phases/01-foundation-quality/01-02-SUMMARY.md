---
phase: 01-foundation-quality
plan: 02
subsystem: logging
tags: [logging, clippy, lint, library-output, foundation]
requires:
  - "PRE: 01-01 green clippy baseline (the deny attribute must not regress it)"
provides:
  - "src/lib.rs + pyo3/src/lib.rs crate-level #![deny(clippy::print_stdout/print_stderr/dbg_macro)] (D-05) — self-enforcing gate via cargo clippy"
  - "src/cli/mod.rs module-level #![allow(...)] exempting the legitimate CLI subtree (D-06)"
  - "All library console I/O routed through the log facade (FOUND-02 core deliverable)"
  - "tests/consistency_tests.rs parallel-merge logging backstop (SPEC edge concurrency | R2)"
affects:
  - "every library diagnostic now flows through log:: (info/warn/error/debug) — CLI users see them at default info level; pyo3 embedding silently discards them (no logger init)"
  - "future PRs that add println!/eprintln!/dbg! to src/ (excl src/cli/) will fail cargo clippy"
tech-stack:
  added: []
  patterns:
    - "Crate-level clippy deny + module-level allow scoping (D-05/D-06) — empirically verified the deny in src/lib.rs propagates to the cli child module, which is exactly why src/cli/mod.rs needs the paired allow"
    - "Fully-qualified log::info!/warn!/error!/debug! form (no `use log::*;`) — matches the in-repo precedent src/core/monitoring.rs"
    - "D-15 severity mapping: println!->log::info!, eprintln!(warning)->log::warn!, eprintln!(error)->log::error!, dbg!->log::debug!"
    - "Empty println!() separators mapped to log::info!(\"\") (log macros require a format string, unlike println!)"
key-files:
  created: []
  modified:
    - src/lib.rs
    - src/cli/mod.rs
    - pyo3/src/lib.rs
    - src/main.rs
    - src/database/prefix_cache_merge.rs
    - src/database/format.rs
    - src/database/query.rs
    - src/database/streaming_merge.rs
    - src/config/manager.rs
    - src/io/discovery.rs
    - src/io/fasta.rs
    - src/io/fastq.rs
    - src/kmer/operations.rs
    - src/kmer/validation.rs
    - src/memory/efficiency.rs
    - tests/consistency_tests.rs
decisions:
  - "Channel-only change: preserved message text and format args verbatim per SPEC R2 acceptance criterion; CJK literal translation deferred to plan 01-04 (FOUND-04) — the plan body Task 1 Step 2 'translate CJK in the same edit' instruction was overridden by the stricter SPEC R2 'only the output channel changes' acceptance criterion and the must_haves.truths row"
  - "Mapped empty println!() separators to log::info!(\"\") rather than removing them — log macros require a format string (println!() was valid; log::info!() is a macro error), so an empty format string preserves the no-op separator intent without changing call shape"
  - "Mapped the 51 merge-progress println! calls in prefix_cache_merge.rs to log::info! (NOT log::debug!) per D-14 — CLI users still see merge progress by default at the preserved info filter level (P2)"
  - "Mapped the 3 '⚠️ 警告' (warning) eprintln! calls in prefix_cache_merge.rs to log::warn! per D-15 severity (recoverable warning); mapped error-path eprintln! ('❌ 处理失败', '错误:') to log::error!"
  - "Excluded src/database/merge_tests.rs from the migration scope — verified dead (mod merge_tests never declared, never compiled), same exclusion precedent as the pyo3 database_backup.rs / database_new_approaches.rs dead files per RESEARCH.md A1/§8"
  - "Used correct clippy CLI syntax: `-D clippy::print_stdout -D clippy::print_stderr -D clippy::dbg_macro` (space-separated, each with its own -D). The plan body's comma-separated `-D clippy::print_stdout,clippy::print_stderr,clippy::dbg_macro` form is parsed by rustc as a single unknown lint name (E0602). The crate-level #![deny(...)] attribute (which DOES use the comma form inside #[...]) is the real enforcement and was verified to catch violations via a temporary println! injection test"
metrics:
  duration: ~16 min
  completed: 2026-07-01
  tasks: 2/2
  files_created: 0
  files_modified: 16
status: complete
---

# Phase 01 Plan 02: log Facade Migration + clippy deny Gate Summary

Migrated all 133 direct console writes (`println!`/`eprintln!`/`dbg!`) in library scope (`src/` excl `src/cli/`, plus `src/main.rs` non-init writes) to the `log` facade, and added the self-enforcing clippy gate (`#![deny(...)]` in `src/lib.rs` + `pyo3/src/lib.rs`, `#![allow(...)]` in `src/cli/mod.rs`) so the constraint cannot regress. Added the held-out parallel-merge logging backstop test.

## What Was Built

### Task 1 — clippy deny/allow attributes + console-to-log migration

**Lint gate (3 attribute additions):**
- `src/lib.rs:1` — `#![deny(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]` at the very top (before the `//!` doc block). Crate-level; propagates to every child module of the rlib including `src/cli/` (which is why `src/cli/mod.rs` needs the paired allow).
- `src/cli/mod.rs:1` — `#![allow(...)]` at the very top. Re-permits the lints for the entire `cli` subtree (`cli/args.rs`, `cli/commands/*`) per D-06 — verified in RESEARCH.md §2 that child modules inherit the parent's lint caps.
- `pyo3/src/lib.rs:1` — `#![deny(...)]` at the very top. pyo3 is a standalone cdylib crate (no workspace inheritance), so it needs its own deny. No allow needed (no pyo3/src/cli analog).

**Gate verification (load-bearing):** Confirmed via a temporary `println!("DENO-TEST")` injection into `src/database/query.rs` that `cargo clippy --lib` catches the violation, citing `src/lib.rs:1:9` as the lint level source. The gate is real and self-enforcing — `cargo build` does NOT enforce it (clippy-only, per RESEARCH.md §2), but `cargo clippy` (the project's documented command) does.

**Migration (15 files):** Applied the D-15 mapping to every `println!`/`eprintln!`/`dbg!` in library scope:
- `src/database/prefix_cache_merge.rs` — 51 calls (the rayon-parallel merge path, incl. the worker closures in `merge_prefix_buckets` that are the subject of Task 2's backstop test)
- `src/database/format.rs` — 22 calls (verbose merge diagnostics)
- `src/memory/efficiency.rs` — 17 calls (MemoryEfficiencyReport)
- `src/config/manager.rs` — 16 calls (ConfigReport)
- `src/kmer/validation.rs` — 10 calls (u128 validation summary)
- `src/io/fastq.rs` — 8 calls
- `src/io/fasta.rs` — 3 calls
- `src/io/discovery.rs` — 3 calls
- `src/database/query.rs`, `src/database/streaming_merge.rs`, `src/kmer/operations.rs`, `src/main.rs` — 1 each

**pyo3/src/ live modules:** already had **0** console macros (only the dead `database_backup.rs` had them — excluded per RESEARCH.md A1). No migration needed in pyo3.

**Message preservation (SPEC R2):** Text and format args preserved verbatim — only the output channel changed. CJK literals (in `prefix_cache_merge.rs`) stay Chinese for now; translation is plan 01-04's job (FOUND-04). This follows the SPEC R2 "ordering" edge resolution and the `must_haves.truths` row "ONLY the output channel changes" — the stricter acceptance criterion overrides the plan body's "translate CJK in the same edit" instruction.

**`env_logger` default preserved (P2):** `default_filter_or("info")` at `src/main.rs:13` is byte-identical to the pre-migration state. CLI users see `log::info!` diagnostics at the default info level (the 51 merge-progress calls remain visible by default per D-14).

**pyo3 embedding (D-17):** No `env_logger::init()` / `Builder::from_env(...).init()` added anywhere in `pyo3/src/` live modules. When `pyrustkmer` is imported, all `log::` calls become no-ops (no global logger registered → silent discard). This is the core FOUND-02 goal: zero stderr pollution into Python.

### Task 2 — parallel-merge logging backstop test

Added `test_parallel_merge_logging_preserves_counts` to `tests/consistency_tests.rs` — the held-out SPEC "concurrency | R2" edge test (non-inferable from other Phase-1 tests).

The test:
1. Builds 3 small databases with **overlapping** k-mer sets and deterministic counts:
   - db_a: `{(10,5), (20,7), (30,3)}`; db_b: `{(20,4), (30,2), (40,9)}`; db_c: `{(10,1), (30,6), (50,8)}`
   - Expected union (counts summed): `{10→6, 20→11, 30→11, 40→9, 50→8}`
2. Persists them to temp `.rkdb` files (merge reads from disk).
3. Calls `RKDatabase::merge_databases` with `use_prefix_cache: true`, `merge_mode: "memory"`, `verbose: true` — selecting the prefix-cache path whose `merge_prefix_buckets` runs `non_empty_prefixes.into_par_iter()` and emits `log::info!`/`log::error!` from inside each parallel worker.
4. Asserts the merged result's k-mer counts **exactly** equal the expected union (every k-mer present, every count exact, no extras/drops).

Counts are < 1M each (avoids the `KmerEntry::read_from` endianness heuristic per RESEARCH.md Pitfall 9). The test is a regression guard: `env_logger` is thread-safe by construction, so this is not a live-lock assertion — it catches future refactors that break the merge-count invariant under parallel logging (e.g. by sharing a buffer across workers).

## Acceptance Criteria Verification

From 01-02-PLAN.md / 01-SPEC.md (FOUND-02 subset):

- ✅ `head -1 src/lib.rs` → `#![deny(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]`
- ✅ `head -1 src/cli/mod.rs` → `#![allow(...)]`
- ✅ `head -1 pyo3/src/lib.rs` → `#![deny(...)]`
- ✅ `grep -rInE 'println!|eprintln!|dbg!' src --include='*.rs' | grep -v '^src/cli/' | grep -v '^src/database/merge_tests.rs:' | grep -v '//' | wc -l` = **0** (merge_tests.rs excluded — verified dead: `mod merge_tests` never declared)
- ✅ `grep -rInE 'println!|eprintln!|dbg!' pyo3/src --include='*.rs' | grep -vE 'database_backup|database_new_approaches|stage1_fix_backup' | grep -v '//' | wc -l` = **0**
- ✅ `cargo clippy --all-targets -- -D clippy::print_stdout -D clippy::print_stderr -D clippy::dbg_macro` exits 0 (root) — deny enforced by clippy
- ✅ `cd pyo3 && cargo clippy --all-targets -- -D warnings` exits 0 (pyo3 — also green after its own `#![deny(...)]`)
- ✅ `cargo clippy --all-targets -- -D warnings` exits 0 (root — 01-01 baseline preserved, no regression)
- ✅ `grep -q 'default_filter_or("info")' src/main.rs` (P2 preserved — line 13 byte-identical)
- ✅ `! grep -rIn 'env_logger' pyo3/src --include='*.rs' | grep -vE 'database_backup|database_new_approaches|stage1_fix_backup' | grep -q .` (D-17 preserved — no logger init in live pyo3 modules)
- ✅ `cargo test --lib` exits 0 — 199 tests passed (no behavioral regression)
- ✅ `cargo test --test consistency_tests` exits 0 — 2 tests passed (incl. the new backstop)
- ✅ `cargo test` (full root suite) exits 0 — 199 lib + 2 consistency + 20 + 9 integration + 8 doc-tests all green
- ✅ `cargo fmt --all --check` exits 0

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Empty `log::info!()` calls failed to compile**
- **Found during:** Task 1 verification
- **Issue:** The original `println!()` (empty, no args) — used as a visual blank-line separator in `prefix_cache_merge.rs` (2 sites) and `memory/efficiency.rs` (2 sites) — became `log::info!()` after migration. Unlike `println!`, the `log::` macros require at least a format string, so `log::info!()` is a macro-expansion error (`missing tokens in macro arguments`, E0602-style).
- **Fix:** Mapped all 4 empty separators to `log::info!("")` — an empty format string is valid for `log::` macros and preserves the no-op separator intent without changing the call shape. The alternative (removing the separators entirely) would have changed the diagnostic output shape more than necessary.
- **Files modified:** `src/database/prefix_cache_merge.rs`, `src/memory/efficiency.rs`
- **Commit:** 2dba05c

**2. [Rule 1 - Bug] clippy `field_reassign_with_default` on the new backstop test**
- **Found during:** Task 2 verification
- **Issue:** The backstop test initialized `MergeConfig` via `let mut config = MergeConfig::default(); config.use_prefix_cache = true; ...` (4 field reassignments). clippy's `field_reassign_with_default` lint (implied by `-D warnings`) fired on this pattern.
- **Fix:** Converted to struct-literal initialization: `MergeConfig { use_prefix_cache: true, temp_dir: ..., merge_mode: "memory".to_string(), verbose: true, ..Default::default() }`. Removed the now-unused `mut`.
- **Files modified:** `tests/consistency_tests.rs`
- **Commit:** 1c98a9c

**3. [Rule 1 - Bug] rustfmt drift on multi-line `log::info!` calls**
- **Found during:** Task 1 verification
- **Issue:** Several migrated multi-line `log::info!(...)` calls (e.g. in `src/database/format.rs`) had two args on one line; rustfmt wanted one arg per line with trailing commas (consistent with the `println!`/`eprintln!` macro style, but the original single-line `eprintln!` form hid this). `cargo fmt --all --check` reported diffs.
- **Fix:** Ran `cargo fmt --all` to apply the mechanical reformatting across the migrated files. No semantic change.
- **Files modified:** `src/database/format.rs` (and other migrated files with multi-arg macro calls)
- **Commit:** 2dba05c

### Plan-body vs acceptance-criterion conflict resolution

**[Documentation] CJK translation scope**
- The plan body Task 1 Step 2 instructed: "In the SAME edit, translate any CJK literal in those calls to English." But the `must_haves.truths` row and SPEC R2 acceptance criterion both state: "Migrated messages preserve their original text and format args verbatim — ONLY the output channel changes."
- **Resolution:** Followed the stricter SPEC R2 acceptance criterion (channel-only change). CJK literals in `prefix_cache_merge.rs` stay Chinese; translation is explicitly plan 01-04 (FOUND-04). This is also called out in the plan's own `<plan_context>` SCOPE BOUNDARY note. Documented in `decisions:` frontmatter above.
- **Commit:** 2dba05c (no separate deviation commit — the decision is baked into the migration)

**[Documentation] Plan-body CLI lint syntax typo**
- The plan body's `<verify><automated>` and `<acceptance_criteria>` commands use `-D clippy::print_stdout,clippy::print_stderr,clippy::dbg_macro` (comma-separated, single `-D`). rustc parses this as a single unknown lint name (E0602 warning, no enforcement).
- **Resolution:** Used the correct space-separated form `-D clippy::print_stdout -D clippy::print_stderr -D clippy::dbg_macro` (each lint with its own `-D`). The crate-level `#![deny(...)]` attribute (which DOES use the comma form correctly inside `#[...]`) is the real enforcement either way; the CLI flag is redundant defense-in-depth. Verified both forms via a temporary `println!` injection test. Documented in `decisions:` frontmatter.

### Out-of-scope discoveries (logged, NOT fixed)

- **`src/database/merge_tests.rs`** — orphaned dead file (never declared as `mod merge_tests`, never compiled). Contains 2 `println!` calls at lines 69-70. Excluded from the migration scope per RESEARCH.md A1/§8 (same precedent as the pyo3 `database_backup.rs` exclusion). Deletion is out of scope per the project's "cleaned opportunistically when the relevant code is touched" rule — merge_tests.rs was not touched by this plan.
- All other CONCERNS.md tech debt (dead pyo3 backup files, unused deps, mmap SAFETY, `Cargo.lock` gitignored, no enforced MSRV, Python version-policy inconsistency) remains untouched.

## Authentication Gates

None.

## Known Stubs

None. No data sources were left un-wired; no placeholder output flows to users. The `log::` calls emit real diagnostic content (preserved verbatim from the original `println!`/`eprintln!` text).

## Threat Flags

None. The threat surface matches the plan's `<threat_model>` exactly:
- **T-02-01 (Information Disclosure / log:: calls):** accepted as planned. The migration preserves message text verbatim (D-15) and the project has no secrets (STACK.md). The pyo3 surface goes from "writes to stderr unconditionally" to "no-op unless a host initializes a logger" — strictly LESS information disclosure.
- **T-02-02 (Tampering / pyo3 logger init):** mitigated as planned. The grep gate confirms no `env_logger` init exists in live pyo3 modules (D-17 preserved).

No new network endpoints, auth paths, file access patterns, or schema changes outside the threat register.

## Verification Commands Run

```bash
# Task 1 verification
set -o pipefail && cargo clippy --all-targets -- -D clippy::print_stdout -D clippy::print_stderr -D clippy::dbg_macro && \
  (cd pyo3 && cargo clippy --all-targets -- -D warnings) && \
  cargo clippy --all-targets -- -D warnings && \
  test "$(grep -rInE 'println!|eprintln!|dbg!' src --include='*.rs' | grep -v '^src/cli/' | grep -v '^src/database/merge_tests.rs:' | grep -v '//' | wc -l | tr -d ' ')" = "0" && \
  test "$(grep -rInE 'println!|eprintln!|dbg!' pyo3/src --include='*.rs' | grep -vE 'database_backup|database_new_approaches|stage1_fix_backup' | grep -v '//' | wc -l | tr -d ' ')" = "0" && \
  grep -q 'default_filter_or("info")' src/main.rs && \
  ! grep -rIn 'env_logger' pyo3/src --include='*.rs' | grep -vE 'database_backup|database_new_approaches|stage1_fix_backup' | grep -q . && \
  cargo test --lib && cargo fmt --all --check
# → all green (199 lib tests passed; both crates clippy-clean; gate verified to catch violations)

# Task 2 verification
cargo test --test consistency_tests
# → 2 tests passed (incl. test_parallel_merge_logging_preserves_counts)

# Full suite
cargo test
# → green (199 lib + 2 consistency + 20 + 9 integration + 8 doc-tests)
```

## Self-Check: PASSED

**Files modified (verified present):**
- FOUND: src/lib.rs
- FOUND: src/cli/mod.rs
- FOUND: pyo3/src/lib.rs
- FOUND: src/main.rs
- FOUND: src/database/prefix_cache_merge.rs
- FOUND: src/database/format.rs
- FOUND: src/database/query.rs
- FOUND: src/database/streaming_merge.rs
- FOUND: src/config/manager.rs
- FOUND: src/io/discovery.rs
- FOUND: src/io/fasta.rs
- FOUND: src/io/fastq.rs
- FOUND: src/kmer/operations.rs
- FOUND: src/kmer/validation.rs
- FOUND: src/memory/efficiency.rs
- FOUND: tests/consistency_tests.rs

**Commits (verified present via `git log --oneline -3`):**
- FOUND: 2dba05c — `refactor(01-02): migrate library console I/O to log facade + add clippy deny`
- FOUND: 1c98a9c — `test(01-02): add parallel-merge logging backstop test`
