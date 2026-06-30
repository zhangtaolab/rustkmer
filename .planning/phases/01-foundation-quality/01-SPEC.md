# Phase 1: Foundation & Quality — Specification

**Created:** 2026-07-01
**Ambiguity score:** 0.16 (gate: ≤ 0.20)
**Requirements:** 4 locked

## Goal

Establish engineering infrastructure that unblocks the performance phases and guards against regressions: a CI gate workflow (fmt/clippy/test/wheel-build), library output routed through the `log` facade, a single source of truth for `.rkdb` write/read logic, and English-only user-facing library strings — across both the CLI and `pyrustkmer` surfaces.

## Background

The repo ships two CI workflows today (`.github/workflows/docs.yml`, `performance-regression.yml`), but **neither runs `cargo fmt`, `cargo clippy`, `cargo test`, or a pyo3 wheel build as a merge gate** — `performance-regression.yml` only runs `cargo build --release` plus a conditionally-skipped `cargo bench`. Tests and warnings can therefore merge unchallenged.

Library code writes directly to the console: **133** `println!`/`eprintln!`/`dbg!` occurrences across 13 files in `src/` outside `src/cli/` (worst: `prefix_cache_merge.rs` 51, `format.rs` 22, `memory/efficiency.rs` 17, `config/manager.rs` 16), plus **3** in `pyo3/src/`. `env_logger` is already initialized in `src/main.rs:13`, but the `log::` facade is barely used (8 occurrences) — so embedding `rustkmer` as a library or through Python pollutes machine-readable output.

The `.rkdb` write path is duplicated: `src/cli/commands/count.rs:497-531` inlines the header construction (`magic`/`version`) and a `write_u128`/`write_u32` entry loop, while `src/database/format.rs` already owns canonical writers (`DatabaseHeader::write_to:81`, `KmerEntry::write_to:201`, `RKDatabase::write_to:360`). Every reader also defensively re-conciles `data_offset` (forced to 42 when outside 40–1000), an anti-pattern noted in the architecture docs.

User-facing library strings are partly hardcoded Chinese: **74** CJK string literals in `src/` outside `src/cli/` (all in `prefix_cache_merge.rs`) and **66** in `pyo3/src/` (e.g. `database.rs` 30, `database_backup.rs` 15), reaching users via both stdout and Python exceptions.

## Requirements

1. **CI gate workflow**: A Rust CI workflow enforces fmt, clippy, test, and pyo3 wheel build on every PR and push to `dev`/`main`.
   - Current: Only `docs.yml` + `performance-regression.yml` exist; neither gates on fmt/clippy/test/wheel-build
   - Target: A new workflow triggers on PR + push to `dev`/`main`, runs on an `ubuntu-latest` + `macos-latest` matrix with Python 3.11, and gates: `cargo fmt --check`; `cargo clippy -D warnings` on the root crate (all existing warnings fixed in this phase); `cargo test` on the root crate; `maturin build` producing sdist+wheel on both OSes; a separate `cargo clippy` gate on the `pyo3` subcrate. Cargo deps are cached and each job has a timeout.
   - Acceptance: The workflow file triggers on PR + push to `dev`/`main`; each gate step fails the job on its respective failure mode (unformatted code / any warning / any test failure / wheel-build failure); a `clippy` run gates `pyo3/Cargo.toml`; wheel artifacts are produced on both runners.

2. **log facade migration**: Library code outside `src/cli/` emits through the `log` facade instead of direct console writes.
   - Current: 133 direct `println!`/`eprintln!`/`dbg!` in `src/` outside `src/cli/` (13 files) + 3 in `pyo3/src/`; `log::` facade barely used despite `env_logger` being wired
   - Target: All production `.rs` files outside `src/cli/` — including `src/main.rs` (except its `env_logger` init) and `pyo3/src/` — route diagnostics through `log::` (`info!`/`warn!`/`error!`/`debug!`/`trace!`). A CI-enforced clippy configuration denies `clippy::print_stdout`, `clippy::print_stderr`, and `clippy::dbg_macro` in library code, with an allowlist for `src/cli/` and the `main.rs` logger init.
   - Acceptance: `cargo clippy` with the denied lints passes on the library scope; a grep for `println!`/`eprintln!`/`dbg!` in `src/` (excl. `src/cli/`) + `pyo3/src/` returns 0 matches; the migration preserves each message's text and format args verbatim (only the output channel changes); the `env_logger` default filter remains `"info"` (negative criterion P2).

3. **`.rkdb` write/read consolidation**: The `.rkdb` binary layout has a single source of truth in `format.rs`.
   - Current: `count.rs:497-531` inlines the header + entry write loop; `format.rs` already owns canonical writers; every reader re-conciles `data_offset` defensively
   - Target: `count.rs` delegates to the `format.rs` canonical writers (`DatabaseHeader::write_to`, `KmerEntry::write_to`) instead of inlining the layout; the read-side `data_offset` reconciliation anti-pattern is removed so the offset is sourced from one place. Output stays byte-identical and `.rkdb` v2 backward/forward compatible.
   - Acceptance: golden-file `sha256` of the consolidated count-path output equals the pre-refactor output for identical input; write→read round-trip yields identical counts; a legacy `.rkdb` sample with `data_offset = 42` still reads correctly; the consolidated writer preserves exact field widths (`u128` kmer, `u32` count) and little-endian byte order (negative criterion P3 — no layout change).

4. **English-only user-facing strings**: User-facing library string literals contain no CJK characters.
   - Current: 74 CJK string literals in `src/` outside `src/cli/` (all in `prefix_cache_merge.rs`) + 66 in `pyo3/src/`
   - Target: User-facing string literals in `src/` (excl. `src/cli/`) and `pyo3/src/` are translated to English; a comment-aware CI check denies CJK characters (Han + Hiragana + Katakana + Hangul Unicode blocks) in those literals while leaving code comments untouched.
   - Acceptance: The CJK check (Han + Hiragana + Katakana + Hangul blocks) passes on string literals in `src/` (excl. `src/cli/`) + `pyo3/src/`; any literal containing ≥1 covered CJK character fails (mixed English+CJK literals must be fully translated, not partially); Chinese messages are translated to English, not deleted or emptied (negative criterion P4).

## Boundaries

**In scope:**
- A new Rust CI workflow (`.github/workflows/*.yml`) gating fmt/clippy/test/wheel-build on PR + push to `dev`/`main`
- Fixing all existing root-crate clippy warnings so `-D warnings` is green
- Migrating all console I/O in `src/` (excl. `src/cli/`), `src/main.rs` non-init writes, and `pyo3/src/` to the `log` facade
- clippy deny configuration for `print_stdout`/`print_stderr`/`dbg_macro` + a comment-aware CJK detection check, with allowlists
- Consolidating `count.rs` write path to delegate to `format.rs`, and removing the read-side `data_offset` reconciliation anti-pattern
- Translating CJK string literals in `src/` (excl. `src/cli/`) + `pyo3/src/` to English
- Regression tests: golden-file `sha256`, write→read round-trip, legacy-sample read-back

**Out of scope:**
- Multi-Python wheel matrix (3.11/3.12/3.13) — release-readiness is v2; v1 gates a single Python 3.11 wheel build
- macOS x86_64 cross-build (Intel) and manylinux matrix expansion — v1 uses `macos-latest` (arm64) + `ubuntu-latest`; broader release matrix deferred
- Translating CJK in code comments — string literals only this phase; comments deferred to a later cleanup
- God-module splits in `format.rs` / `pyo3/database.rs` not on the write/read-consolidation path — later cleanup round (per REQUIREMENTS Out-of-Scope table)
- `src/cli/` console output and `indicatif` progress bars — `src/cli/` is explicitly exempt from the log-migration requirement (legitimate CLI user output)
- CI security hardening (action SHA pinning, `pull_request_target` discipline, secret handling, injection/path-traversal) — canon, owned by `/gsd-secure-phase`; not minted here
- Parallel counting, bounded merge, dense storage, Jellyfish2 benchmarking — Phases 2/3/4

## Constraints

- Preserve the `.rkdb` v2 on-disk format (magic `RKDB`, version 2): no version bump, no field-width or endianness change, byte-identical output
- Preserve the public CLI and Python APIs — no breaking surface changes
- Both the CLI and `pyrustkmer` surfaces must remain green under the new CI gate (dual-surface constraint)
- Rust 1.80+ stable, PyO3 0.27.2, existing dependency set — no new persistence or logging engine
- CI matrix: `ubuntu-latest` (x86_64) + `macos-latest` (arm64), Python 3.11 via `actions/setup-python`; cargo deps cached; per-job timeout set
- clippy deny must allowlist `src/cli/` (legitimate CLI output) and `src/main.rs`'s `env_logger::Builder…init()` (logger setup, not a console write)

## Acceptance Criteria

- [ ] A CI workflow triggers on PR + push to `dev`/`main` and runs on `ubuntu-latest` + `macos-latest`
- [ ] `cargo fmt --check` step fails the job on unformatted code
- [ ] `cargo clippy -D warnings` step passes on the root crate (all prior warnings fixed this phase) and fails on any new warning
- [ ] `cargo test` step fails the job on any test failure
- [ ] `maturin build` produces sdist+wheel on both `ubuntu-latest` and `macos-latest`
- [ ] A separate `cargo clippy` gate covers the `pyo3` subcrate (`pyo3/Cargo.toml`)
- [ ] No gate step uses `continue-on-error`, `|| true`, or an `if`-guarded skip that turns a failure green (P1)
- [ ] `cargo clippy` with denied `print_stdout`/`print_stderr`/`dbg_macro` passes on library scope; grep for `println!`/`eprintln!`/`dbg!` in `src/` (excl. `src/cli/`) + `pyo3/src/` returns 0
- [ ] Migrated messages preserve their original text and format args verbatim (channel-only change)
- [ ] `env_logger` default filter remains `"info"` (P2)
- [ ] golden-file `sha256` of consolidated count-path output equals pre-refactor output for identical input
- [ ] write→read round-trip yields identical k-mer counts
- [ ] A legacy `.rkdb` sample with `data_offset = 42` still reads correctly after the read-side refactor
- [ ] The CJK check (Han + Hiragana + Katakana + Hangul blocks) passes on string literals in `src/` (excl. `src/cli/`) + `pyo3/src/`; any literal with ≥1 covered CJK character fails
- [ ] Chinese messages are translated to English, not deleted or emptied (P4)
- [ ] Existing `.rkdb` v2 files and existing queries keep working (no format/API regression)

## Edge Coverage

**Coverage:** 9/9 applicable edges resolved · 0 unresolved

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| unclassified (manual) | R1 | ✅ covered | New AC: pyo3 subcrate gated via separate `cargo clippy` + `maturin build` (root crate runs fmt/clippy/test) |
| adjacency | R2 | ⛔ dismissed | The `src/cli/` allowlist already defines the library/CLI seam — no additional edge |
| empty | R2 | ⛔ dismissed | Modules with zero existing console I/O are vacuously compliant — nothing to migrate |
| ordering | R2 | ✅ covered | AC: migration preserves message text/format args verbatim (channel-only change) |
| concurrency | R2 | 🧪 backstop | Held-out edge test for plan-phase `must_haves`: parallel merge path logs without interleave-corruption; counts unchanged (env_logger is thread-safe) |
| boundary | R3 | ✅ covered | AC: legacy `.rkdb` with `data_offset = 42` still reads after read-side refactor |
| precision | R3 | ✅ covered | AC: consolidated writer preserves exact field widths (`u128`/`u32`) + little-endian (folds into golden-file `sha256`) |
| empty | R4 | ✅ covered | AC: any literal with ≥1 covered CJK char fails; mixed English+CJK literals must be fully translated |
| encoding | R4 | ✅ covered | AC: CJK check scope = Han + Hiragana + Katakana + Hangul Unicode blocks; emoji/Latin allowed |

## Prohibitions (must-NOT)

**Coverage:** 4/4 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| MUST NOT swallow a CI gate step's failure via `continue-on-error`, `|| true`, or an `if`-guarded skip | R1 | resolved / test | Workflow YAML scan: no gate step carries `continue-on-error`/`|| true`/skip. Descriptor: `check_kind=lint-rule`, `check_target=.github/workflows/`, `check_rule=tbd-custom-yaml-scan`, `check_violation_fixture=tbd-known-bad-workflow-yaml` |
| MUST NOT lower the `env_logger` default filter below `"info"` (no debug/trace default) | R2 | resolved / test | Grep `default_filter_or("info")` in `src/main.rs`. Descriptor: `check_kind=lint-rule`, `check_target=src/main.rs` |
| MUST NOT alter the `.rkdb` v2 on-disk byte layout (no version bump, no field-width/endianness change) | R3 | resolved / test | golden-file `sha256` equality (same check as R3 acceptance). Descriptor: `check_kind=node-test`, `check_target=tbd-golden-file-test` |
| MUST NOT pass the CJK check by deleting or emptying user-facing message literals — messages must be translated, not erased | R4 | resolved / judgment | Review-time check: each former CJK literal has an English replacement of equivalent meaning |

Canon referrals (NOT minted here — owned by `/gsd-secure-phase` + standard CI security): action SHA pinning / `pull_request_target` discipline / secret handling / injection / path-traversal. Breadcrumb only.

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                       |
|--------------------|-------|------|--------|-------------------------------------------------------------|
| Goal Clarity       | 0.85  | 0.75 | ✓      | 4 concrete deliverables, dual-surface                       |
| Boundary Clarity   | 0.82  | 0.70 | ✓      | Explicit in/out-of-scope; log/CJK scope locked              |
| Constraint Clarity | 0.82  | 0.65 | ✓      | CI matrix, clippy policy, wheel form, v2-format preservation |
| Acceptance Criteria| 0.85  | 0.70 | ✓      | 16 pass/fail criteria, all machine-verifiable               |
| **Ambiguity**      | 0.16  | ≤0.20| ✓      |                                                             |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

| Round | Perspective      | Question summary                                              | Decision locked                                                                 |
|-------|------------------|---------------------------------------------------------------|---------------------------------------------------------------------------------|
| 1     | Researcher       | CI OS matrix? clippy existing-warning policy? wheel form?     | ubuntu+macOS matrix; fix-all-warnings this phase; `maturin build` sdist+wheel   |
| 2     | Boundary Keeper  | log facade boundary? CJK scope? consolidation depth?          | All `.rs` outside `src/cli/` (incl. `main.rs`, `pyo3/src/`); string-literal only both surfaces; thin delegation + read-side `data_offset` fix |
| 3     | Failure Analyst  | Verification mechanism? write-path equivalence? CI trigger?   | clippy deny `print_*`/`dbg_macro` + custom CJK lint; golden-file + round-trip + legacy read-back; PR + push dev/main, matrix, cache, timeout |
| 5.5   | Edge probe       | pyo3 subcrate gating? CJK block scope? parallel-thread logs?  | Root crate fmt/clippy/test + pyo3 via maturin+clippy; Han+kana+hangul blocks; backstop test for rayon-path logging |
| 5.6   | Prohibition probe| 4 must-NOTs (gate integrity, log level, byte layout, CJK gaming) | All 4 kept: P1/P2/P3 = test tier, P4 = judgment tier; canon CI-security referred to /gsd-secure-phase |

*Defaults adopted (not asked — adjustable in plan-phase):* CI Python version pinned to 3.11; macOS runner is `macos-latest` (arm64); clippy allowlist covers `src/cli/` and the `main.rs` `env_logger` init.

---

*Phase: 01-foundation-quality*
*Spec created: 2026-07-01*
*Next step: /gsd-discuss-phase 1 — implementation decisions (workflow file layout, clippy scope mechanics, CJK-check tool choice, golden-file test scaffolding)*
