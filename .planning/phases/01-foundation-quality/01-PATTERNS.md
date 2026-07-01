# Phase 1: Foundation & Quality - Pattern Map

**Mapped:** 2026-07-01
**Files analyzed:** 14 (4 new + 10 modified)
**Analogs found:** 14 / 14 (every file has an in-repo analog; RESEARCH.md skeletons fill the rest)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `.github/workflows/ci.yml` (NEW) | config (CI) | batch (4 jobs) | `.github/workflows/performance-regression.yml` | exact |
| `tests/cjk_check.rs` (NEW) | test | file-I/O / AST-walk | `tests/consistency_tests.rs` (entrypoint shape) + `src/core/monitoring.rs` (`log::` macro-call site as a parseable target) | role-match (entrypoint) — the syn/AST mechanics have NO in-repo analog; use RESEARCH.md §1 skeleton |
| `tests/golden_tests.rs` (NEW) | test | file-I/O (sha256 assert) | `src/database/format.rs:1014-1100` (inline `#[cfg(test)] mod tests`) | role-match (extends the same writers under test) |
| `tests/legacy_readback_tests.rs` (NEW) | test | file-I/O (read fixture) | `tests/integration/queryx_tests.rs` (`Result<()>` + `TempDir` + assert) | role-match |
| `tests/fixtures/golden_*.rkdb` (NEW, 12 binaries) | test-fixture | binary-file | `tests/fixtures/*.fasta` (committed-binary precedent) + `src/database/format.rs:write_to` (writer that generates them) | role-match (precedent) |
| `tests/fixtures/legacy_v2_offset42.rkdb` (NEW) | test-fixture | binary-file | same as above | role-match |
| `tests/round_trip_tests.rs` (NEW or extend `format.rs` inline) | test | round-trip | `src/database/format.rs:1089-1100` (`test_merge_streaming_basic` round-trip) + `tests/common/mod.rs:105` (`databases_have_same_kmers`) | exact |
| `src/lib.rs` (MODIFY — add `#![deny(...)]`) | library-config | n/a (lint attr) | (no in-repo precedent — new attribute; see RESEARCH.md Example 1) | none (new attr) |
| `src/cli/mod.rs` (MODIFY — add `#![allow(...)]`) | library-config | n/a (lint attr) | (no in-repo precedent — paired with the deny above) | none (new attr) |
| `pyo3/src/lib.rs` (MODIFY — add `#![deny(...)]`) | library-config | n/a (lint attr) | (paired with the deny above) | none (new attr) |
| `src/cli/commands/count.rs:497-531` (MODIFY — delegate writer) | library-source (CLI command) | file-write (binary) | `src/database/format.rs:347-372` (`write_to_file` / `write_to`) | exact (this IS the canonical writer to delegate to) |
| `src/database/format.rs:290-296` + `src/database/query.rs:79` (MODIFY — remove clamp) | library-source (readers) | file-read (binary) | `src/database/format.rs:168-182` (`DatabaseHeader::validate` — error path) + `src/error.rs:73` (`ProcessingError::new`) | role-match (replace silent clamp with loud error) |
| `src/database/prefix_cache_merge.rs:90-112, 317-329` (MODIFY — 51 println→log + CJK→EN) | library-source (merge) | event-stream (progress) | `src/core/monitoring.rs:316-333` (`log::info!` macro for multi-line summaries) | exact (in-repo `log::` precedent) |
| ~13 files in `src/` (excl cli) + `pyo3/src/` (MODIFY — console I/O → log, CJK → EN) | library-source | event-stream | `src/core/monitoring.rs:161-373` (the only file already using `log::debug!`/`log::info!`) | exact (in-repo precedent) |
| `Cargo.toml` (MODIFY — add `syn` + `proc-macro2` dev-deps) | config (deps) | n/a | `Cargo.toml:89-99` (existing `[dev-dependencies]` block) | exact |

---

## Pattern Assignments

### `.github/workflows/ci.yml` (config / batch CI)

**Analog:** `.github/workflows/performance-regression.yml`

This is the canonical CI shape already in the repo. `ci.yml` mirrors its trigger, env, permissions, caching, and toolchain steps; the only structural change is **independent parallel jobs** (D-02) instead of `needs:`-chained jobs.

**Trigger + env + permissions** (mirror exactly; `performance-regression.yml:3-19`):
```yaml
on:
  pull_request:
    branches: [dev, main]
  push:
    branches: [dev, main]      # NOTE: perf-regression uses main/develop; SPEC pins dev/main
env:
  CARGO_TERM_COLOR: always
permissions:
  contents: read
```

**Toolchain + cargo cache** (mirror verbatim; `performance-regression.yml:29-48`):
```yaml
- uses: actions/checkout@v4
- name: Install Rust
  uses: dtolnay/rust-toolchain@stable        # with: components: clippy (or rustfmt) for lint jobs
- name: Cache cargo registry
  uses: actions/cache@v4
  with:
    path: ~/.cargo/registry
    key: ${{ runner.os }}-cargo-registry-${{ hashFiles('**/Cargo.lock') }}
```
Pitfall (RESEARCH.md §3): the root crate and pyo3 subcrate have **separate** `Cargo.lock` files — use distinct cache keys (`cargo-root-` vs `cargo-pyo3-`) keyed on `Cargo.lock` and `pyo3/Cargo.lock` respectively, or cache stampedes result.

**Matrix + fail-fast** (D-02 — new pattern, not in perf-regression which is ubuntu-only):
```yaml
strategy:
  fail-fast: false                 # so macOS failure doesn't cancel ubuntu
  matrix:
    os: [ubuntu-latest, macos-latest]
```

**Prohibition P1 (SPEC)** — do NOT mirror perf-regression's `if:`-guarded skips (e.g. `if: [ -f "scripts/..." ]; then ... else echo "Warning ... skipping" fi` at lines 66-75, 140-150). Every gate step in `ci.yml` MUST fail loudly.

**pyo3 job** — mirror the maturin install pattern from `performance-regression.yml:55-58`:
```yaml
- name: Install Python
  uses: actions/setup-python@v5        # v5 not v4 (perf-regression uses v4; upgrade per RESEARCH §3)
  with:
    python-version: '3.11'             # 3.11 per pyproject.toml requires-python
- run: pip install 'maturin>=1.0,<2.0'
- name: maturin build
  working-directory: pyo3              # prefer working-directory over `cd pyo3 &&` (bash sandbox)
  run: maturin build
```

**Full concrete `ci.yml` skeleton:** see RESEARCH.md §3 (lines 236-349) — it is copy-ready.

---

### `tests/cjk_check.rs` (test / file-I/O + AST-walk)

**Entrypoint analog:** `tests/consistency_tests.rs:1-15` — confirms that a new `tests/<name>.rs` is auto-discovered as a test target with no registration in `tests/mod.rs` (which is a shared module, NOT a test target — RESEARCH.md §8 / TESTING.md).
```rust
//! Integration tests for consistency
mod consistency;          // pull in shared subdir via mod
#[test]
fn consistency_tests_placeholder() { assert!(true); }
```
`tests/cjk_check.rs` is **simpler**: no `mod` declaration needed (no shared subdir); it is a standalone target. `cargo` auto-discovers each `tests/*.rs` as its own binary.

**Content analog:** NONE in-repo (no AST-walking test exists). Use the **RESEARCH.md §1 verified skeleton** (lines 103-160) verbatim — it is empirically tested against syn 2.0 and contains both required visitor methods (`visit_lit` + `visit_macro`).

**Source-file enumeration analog:** `walkdir 2.4` is already a production dep (`Cargo.toml:68`). No existing test uses it for source enumeration; the CJK test will be the first. Pattern (RESEARCH.md §3, A1):
```rust
for entry in walkdir::WalkDir::new("src").into_iter().filter_map(|e| e.ok()) {
    let path = entry.path();
    if path.extension() == Some("rs") { /* parse + visit */ }
}
```

**Dev-dep declaration analog:** `Cargo.toml:89-99` `[dev-dependencies]` block — add `syn` + `proc-macro2` here (see the Cargo.toml assignment below).

**Test placement rule (RESEARCH.md §1, load-bearing):** the file lives under `tests/` (NOT inline `#[cfg(test)]` in a `src/` file) because `syn` is a dev-dep and a separate target keeps the lib's test build clean.

---

### `tests/golden_tests.rs` (test / file-I/O sha256 assertion)

**Analog:** `src/database/format.rs:1014-1100` — the existing `#[cfg(test)] mod tests` block that already round-trips `RKDatabase` through `to_file_path` / `from_kmer_pairs`. This is the canonical "exercise the writers" pattern in the repo.

**Imports + factory reuse** (from `src/database/format.rs:1016-1018` and `tests/common/mod.rs`):
```rust
use super::*;                       // bring writers into test scope
use tempfile::tempdir;              // existing dev-dep (Cargo.toml:94)
// For tests/golden_tests.rs (separate target):
mod common;
use common::*;                      // create_test_database, databases_have_same_kmers (tests/common/mod.rs:12,105)
```

**Round-trip + assert pattern** (from `src/database/format.rs:1040-1080`):
```rust
let temp_dir = tempdir().unwrap();
let db1_path = temp_dir.path().join("db1.rkdb");
db1.to_file_path(&db1_path).unwrap();           // canonical writer
// ... load back, assert counts match ...
```

**sha256 assertion (NEW mechanic, no in-repo analog)** — use the sha2 0.10 API per RESEARCH.md Example 3 (lines 913-922). `sha2 = "0.10"` is already a production dep (`Cargo.toml:77` — do NOT bump to 0.11):
```rust
use sha2::{Sha256, Digest};
let bytes = std::fs::read("tests/fixtures/golden_k21_canon_sorted.rkdb")?;
let actual = format!("{:x}", Sha256::digest(&bytes));
let expected = include_str!("tests/fixtures/golden_k21_canon_sorted.sha256").trim();
assert_eq!(actual, expected, "golden sha256 mismatch for k21/canon/sorted");
```

**Fixture-naming precedent:** `tests/fixtures/k33_test.fasta`, `k48_test.fasta`, `k64_test.fasta` (committed binaries at varying k sizes). Mirror the `k{21,32,64}_*` naming for the 12 golden `.rkdb` files (D-13 matrix).

**Cross-consistency pattern (D-09b)** — see RESEARCH.md §5 (lines 526-542) for the count-path-vs-canonical-path byte-identity assertion skeleton. This is new mechanic; the analog is the round-trip block above with two writers instead of one.

**CRITICAL SEQUENCING (D-10):** Task 1 of the consolidation plan MUST generate these golden files from the **current** (pre-refactor) count.rs BEFORE any delegation refactor. The generation step uses the writers in `src/cli/commands/count.rs:503-531` + `src/database/format.rs:347-372` as they exist today.

---

### `tests/legacy_readback_tests.rs` (test / fixture read)

**Analog:** `tests/integration/queryx_tests.rs:1-54` — the canonical "create temp dir, point at a file, exercise a code path, assert" integration-test shape in this repo.
```rust
use std::path::PathBuf;
use tempfile::TempDir;
use anyhow::Result;                 // ergonomic ? in test bodies (TESTING.md convention)
use rustkmer::database::format::RKDatabase;

mod common;                         // pull in factories
use common::*;

#[test]
fn test_legacy_offset42_reads() -> Result<()> {
    let fixture = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/legacy_v2_offset42.rkdb");
    let db = RKDatabase::from_file_path(&fixture)?;
    assert!(db.total_kmers() > 0, "legacy file must read nonzero kmers");
    Ok(())
}
```
Note: `tests/integration/queryx_tests.rs:16-18` shows the `mod common; use common::*;` pull-in pattern for sharing factories.

---

### `tests/round_trip_tests.rs` OR extend `src/database/format.rs` inline (test / round-trip)

**Analog (exact):** `src/database/format.rs:1089-1100` — already exercises `from_kmer_pairs` → `to_file_path` → reload. The new round-trip test extends this with the **cross-writer consistency** angle (count-path vs canonical-path byte identity per D-09b).
```rust
// src/database/format.rs:1089-1100 (existing live pattern)
let temp_dir = tempdir().unwrap();
let db1_path = temp_dir.path().join("db1.rkdb");
let db1 = RKDatabase::from_kmer_pairs(vec![(0x0010, 10), (0x0020, 20), (0x0030, 30)], 31, false, true).unwrap();
db1.to_file_path(&db1_path).unwrap();
```
Reuse `tests/common/mod.rs:105` `databases_have_same_kmers(db1, &loaded)` for the post-round-trip count assertion (it already compares via `HashMap`).

---

### `src/lib.rs` (MODIFY — add crate-level deny attribute)

**No in-repo analog** for the attribute itself (it is new). Place it at the **very top** of the file, before the `//!` doc-comment block, per Rust attribute convention. Concrete pattern (RESEARCH.md Example 1, lines 884-895):
```rust
#![deny(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]

//! RustKmer Library
//! ...
pub mod cli;       // line 20 today — child module INHERITS the deny (RESEARCH.md §2)
pub mod config;
// ...
```
**Verified (RESEARCH.md §2):** `src/cli/` inherits this deny because it is a child module of the rlib — which is exactly why `src/cli/mod.rs` needs the paired `#![allow(...)]`.

**Pitfall (RESEARCH.md §2, load-bearing):** `cargo build` does NOT enforce these lints (they are clippy-only). The plan must not claim `cargo build` fails — only `cargo clippy`.

---

### `src/cli/mod.rs` (MODIFY — add module-level allow attribute)

**No in-repo analog** for the attribute. Paired with the deny above. Place at the **very top**, before the existing `//!` doc-comment (line 1 today):
```rust
#![allow(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]

//! Command-line interface module
//! ...
pub mod args;       // line 5 today
pub mod commands;   // line 6 today
```
**Verified (RESEARCH.md §2):** this single attribute re-permits the lints for the **entire cli subtree** (`cli/args.rs`, `cli/commands/*`) because child modules inherit the parent's lint caps. No per-file allows needed.

`src/main.rs:13`'s `env_logger::Builder…init()` is a method call, not a print macro — it needs NO allow (D-06).

---

### `pyo3/src/lib.rs` (MODIFY — add crate-level deny attribute)

Same as `src/lib.rs` but for the standalone cdylib crate (`pyo3/Cargo.toml` has no workspace inheritance — RESEARCH.md §2). Place at the top of `pyo3/src/lib.rs` before the `//!` block:
```rust
#![deny(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]

//! Enhanced PyO3 binding for RustKmer ...
```
No `#![allow(...)]` needed on the pyo3 side — there is no `pyo3/src/cli` analog. The CI `cd pyo3 && cargo clippy -- -D warnings` step (D-03) is the gate.

---

### `src/cli/commands/count.rs:497-531` (MODIFY — delegate to canonical writers)

**Analog (exact):** `src/database/format.rs:347-372` — the canonical writers that count.rs must delegate to. This is not "analogous to" — it IS the target.

**Current duplicated code to replace** (`src/cli/commands/count.rs:503-531`):
```rust
let header = DatabaseHeader { magic: *DATABASE_MAGIC, version: DATABASE_VERSION, /* ... */
    file_size: 42 + (kmer_count as u64 * 12),   // BUG-marked in RESEARCH §4; field not serialized
};
header.write_to(&mut writer)?;                  // canonical header writer (line 81)
for (kmer, count) in kmers {                    // INLINE entry loop — the duplication to remove
    writer.write_u128::<LittleEndian>(kmer)?;
    writer.write_u32::<LittleEndian>(count)?;
}
```

**Target delegation (Option B, thinnest — RESEARCH.md §4 lines 456-463):**
```rust
let header = DatabaseHeader { /* same fields, file_size: 0 to match canonical */ };
header.write_to(&mut writer)?;                           // DatabaseHeader::write_to (format.rs:81)
for (kmer, count) in &kmers {
    KmerEntry::new(*kmer, *count).write_to(&mut writer)?; // KmerEntry::write_to (format.rs:201)
}
```
**Verified (RESEARCH.md §4):** `file_size` and `unique_kmers` are struct fields but are **never serialized** by `DatabaseHeader::write_to` (format.rs:81-108 writes exactly 42 bytes: magic+version+kmer_size+padding+total_kmers+flags+padding+data_offset+index_offset). The two writers already produce **byte-identical** output — the `file_size: 42 + kmer_count*12` value in count.rs is computed then discarded on write. So delegation is byte-safe; the golden sha256 (D-10) is the empirical proof.

**`KmerEntry::write_to` field widths** (`format.rs:200-204`): `write_u128::<LittleEndian>(self.kmer)` (16 bytes) + `write_u32::<LittleEndian>(self.count)` (4 bytes) = 20 bytes/entry, little-endian — matches the inline loop exactly.

---

### `src/database/format.rs:289-296` + `src/database/query.rs:77-85` (MODIFY — remove silent clamp)

**Analog (role-match):** `src/database/format.rs:168-182` (`DatabaseHeader::validate`) — the **error-reporting** site for bad headers. This is the semantic the refactor moves toward: fail loudly, don't silently rewrite.

**Current silent-rewrite clamp** (identical at both sites; shown for `format.rs:289-296`):
```rust
let actual_data_offset = if header.data_offset < 40 {
    42
} else if header.data_offset > 1000 {
    42
} else {
    header.data_offset
};
```

**Target (loud error — RESEARCH.md §4 lines 486-496, recommended over debug_assert):**
```rust
if header.data_offset != 42 {
    return Err(crate::error::ProcessingError::new(format!(
        "Unsupported data_offset {} (expected 42); file may be from an incompatible rustkmer version",
        header.data_offset
    )));
}
let actual_data_offset = header.data_offset;   // now always 42
```
**Error constructor analog:** `src/error.rs:72-78` `ProcessingError::new(message: impl Into<String>)` — already used everywhere in `format.rs` (e.g. `:524`, `:568`).

**CRITICAL:** both sites (`format.rs:from_file_path` AND `query.rs:load_entries`) MUST change consistently — the duplication IS the anti-pattern. The third site (`format.rs:173` in `validate`) is already an error path — leave it alone.

**Legacy fixture (D-12):** generated with `data_offset = 42` (the correct value the writers set at `format.rs:464` and `count.rs:509`), so the loud error does NOT fire on it — the fixture reads correctly post-refactor.

---

### `src/database/prefix_cache_merge.rs:90-112, 317-329` (MODIFY — 51 println→log + CJK→English)

**Analog (exact, in-repo):** `src/core/monitoring.rs:316-333` — the **only** file in `src/` already using the `log::` facade correctly for multi-line progress summaries:
```rust
pub fn log_summary(&self) {
    log::info!(
        "Performance Summary - {} samples recorded",
        self.total_samples
    );
    for (operation, timings) in &self.active_timings {
        if let Some(stats) = self.get_operation_stats(operation) {
            log::info!(
                "  {}: {} ops, avg {:?}, min {:?}, max {:?}",
                operation, stats.count, stats.average, stats.min, stats.max
            );
        }
    }
}
```
Mirror this exactly: multi-arg `log::info!("... {} ...", x)` form, 2-space indent on continuation lines, `{}`/`{:?}` formatters preserved verbatim.

**Mapping (D-15, mechanical):**
- `println!(...)` → `log::info!(...)`     (51 occurrences in this file)
- `eprintln!(...)` → `log::warn!(...)` or `log::error!(...)` (by severity)
- `dbg!(...)` → `log::debug!(...)`

**CJK→English** (RESEARCH.md Example 2, lines 898-911): translate the literal text, keep format args verbatim. Example at `prefix_cache_merge.rs:90-94`:
```rust
// BEFORE:
println!("\n🚀 开始外部排序合并");
println!("   输入文件: {} 个", self.input_files.len());
// AFTER:
log::info!("Starting external sort merge");
log::info!("   Input files: {}", self.input_files.len());
```
The SPEC acceptance (FOUND-02) requires **channel-only change** — text translation is the FOUND-04 angle; both must happen in the same edit.

---

### ~13 files in `src/` (excl `src/cli/`) + `pyo3/src/` (MODIFY — console I/O → log, CJK → EN)

**Analog:** `src/core/monitoring.rs:161-373` — the in-repo reference for the `log::` facade. Use the same import-free style (`log::info!` fully qualified; no `use log::*;` at module top — verified across all 8 existing usages in monitoring.rs).

**Mapping table (D-15 — apply verbatim):**

| Before | After | Severity rule |
|--------|-------|---------------|
| `println!(...)` | `log::info!(...)` | default progress |
| `eprintln!("Error: ...")` / `eprintln!("   ❌ ...")` | `log::error!(...)` | failure |
| `eprintln!("Warning: ...")` | `log::warn!(...)` | recoverable |
| `dbg!(x)` | `log::debug!("{:?}", x)` | debug |

**pyo3-specific rule (D-17, RESEARCH.md §6):** `pyo3/src/` MUST NOT add any `env_logger::init()` / `Builder::from_env(...).init()` call. Verified: pyo3/src/ has zero logger-init today; the migration only converts `println!`→`log::info!` (which becomes a no-op when no logger is registered — zero stderr pollution into Python, the FOUND-02 goal).

**CJK translation applies to the same edits** (FOUND-04): every Chinese literal in these files becomes English in the same commit.

---

### `Cargo.toml` (MODIFY — add `syn` + `proc-macro2` dev-deps)

**Analog (exact):** `Cargo.toml:89-99` — the existing `[dev-dependencies]` block. Append in the same block; do NOT create a second `[dev-dependencies]` section.

```toml
[dev-dependencies]
# Benchmarking
criterion = { version = "0.5", features = ["html_reports"] }
# Testing
tempfile = "3.12"
proptest = "1.5"
# Random number generation
rand = "0.8"
rand_chacha = "0.3"
# CJK string-literal detection in tests/cjk_check.rs (Phase 1)
syn = { version = "2", features = ["full", "extra-traits", "visit", "parsing"] }
proc-macro2 = "1"
```
**Constraint (RESEARCH.md §4 / CLAUDE.md):** do NOT touch `[profile.release]` (`Cargo.toml:101-104` — `lto = true`, `codegen-units = 1`, `panic = "abort"`). Do NOT bump `sha2` (pinned 0.10; 0.11 breaks the API).

---

## Shared Patterns

### log facade migration (FOUND-02)
**Source:** `src/core/monitoring.rs:161-373` (the only in-repo `log::` precedent)
**Apply to:** every `src/` file outside `src/cli/` + every `pyo3/src/` file (the ~13 files above)
```rust
log::info!("... {} ...", arg);      // was println!
log::warn!("...");                    // was eprintln! (recoverable)
log::error!("...");                   // was eprintln! (failure)
log::debug!("{:?}", x);               // was dbg!(x)
```
**Rule:** fully-qualified `log::` (no `use log::*;`), preserve format args verbatim, translate CJK literals to English in the same edit.

### clippy deny / allow scoping (D-05, D-06)
**Source:** RESEARCH.md §2 (empirically verified) + Example 1
**Apply to:** `src/lib.rs` (deny), `src/cli/mod.rs` (allow), `pyo3/src/lib.rs` (deny)
```rust
// src/lib.rs (top of file):
#![deny(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]
// src/cli/mod.rs (top of file):
#![allow(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]
// pyo3/src/lib.rs (top of file):
#![deny(clippy::print_stdout, clippy::print_stderr, clippy::dbg_macro)]
```
**Pitfall:** `cargo build` does NOT enforce these — only `cargo clippy` does (RESEARCH.md §2). CI gate is `cargo clippy --all-targets -- -D warnings`.

### sha256 golden assertion (D-09)
**Source:** RESEARCH.md Example 3 (sha2 0.10 API)
**Apply to:** `tests/golden_tests.rs` (and cross-consistency variant for the consolidation)
```rust
use sha2::{Sha256, Digest};
let actual = format!("{:x}", Sha256::digest(&std::fs::read(&path)?));
assert_eq!(actual, include_str!("...sha256").trim());
```
**Pitfall:** `sha2` is pinned at `0.10` (`Cargo.toml:77`); do NOT bump to `0.11` (API drift).

### Test factory + temp-file reuse
**Source:** `tests/common/mod.rs:12,105` + `tests/common/temp_files.rs:114`
**Apply to:** `tests/golden_tests.rs`, `tests/round_trip_tests.rs`, `tests/legacy_readback_tests.rs`
```rust
mod common;
use common::*;
// create_test_database(num, kmer_size, canonical, sorted)
// create_database_from_kmers(kmers, kmer_size, canonical, sorted)
// databases_have_same_kmers(db1, db2)
// TempFileManager::save_database_to_temp(&db)
```
**Note (RESEARCH.md §1):** do NOT add tests to `src/database/merge_tests.rs` (orphaned, never compiled as `mod merge_tests` is undeclared). Use `tests/` integration targets or extend `format.rs:1014` inline block.

### Error construction (loud failure)
**Source:** `src/error.rs:72-78` (`ProcessingError::new`)
**Apply to:** the `data_offset` clamp removal (format.rs + query.rs)
```rust
return Err(crate::error::ProcessingError::new(format!(
    "Unsupported data_offset {} (expected 42)", header.data_offset
)));
```

---

## No Analog Found

| File | Role | Data Flow | Reason | Fallback |
|------|------|-----------|--------|----------|
| `tests/cjk_check.rs` (AST-walk mechanics) | test | AST-walk | No in-repo test parses `.rs` with `syn` | RESEARCH.md §1 verified skeleton (lines 103-160) — empirically tested against syn 2.0; copy the `visit_lit` + `visit_macro` + `collect_str_lits` triad verbatim |
| `src/lib.rs` / `src/cli/mod.rs` / `pyo3/src/lib.rs` lint attributes | library-config | n/a | No crate-level clippy-deny attribute exists in-repo today | RESEARCH.md Example 1 (lines 884-895) — verified via throwaway test crate (RESEARCH.md §2) |
| `tests/fixtures/*.sha256` sidecars | test-fixture | n/a | No committed-text-sidecar precedent | New; trivial (`<hex>\n`) — generate via `sha256sum file > file.sha256` or the test itself |

Everything else has a real in-repo analog (CI shape, test entrypoint, log-facade precedent, write/read consolidation target, factory helpers, dev-dep block).

---

## Metadata

**Analog search scope:**
- `.github/workflows/` (both existing workflows read in full)
- `src/lib.rs`, `src/main.rs`, `src/cli/mod.rs`, `src/cli/commands/count.rs` (write block)
- `src/database/format.rs` (full header/writer/test-block read; `from_kmer_pairs`, `write_to_file`, `write_to`, `validate`, inline `#[cfg(test)]`)
- `src/database/query.rs` (clamp site + open/load_entries)
- `src/database/prefix_cache_merge.rs` (CJK println block)
- `src/core/monitoring.rs` (the only `log::` facade precedent)
- `src/error.rs` (ProcessingError)
- `pyo3/src/lib.rs`, `pyo3/src/database.rs` (CJK migration site + module structure)
- `pyo3/Cargo.toml`, `Cargo.toml` (dep/dev-dep blocks, release profile)
- `tests/mod.rs`, `tests/consistency_tests.rs`, `tests/integration/queryx_tests.rs`, `tests/common/mod.rs`, `tests/common/temp_files.rs` (test organization + factories)
- `tests/fixtures/` (committed-binary precedent)

**Files scanned:** ~20
**Pattern extraction date:** 2026-07-01
**Key load-bearing facts (cross-referenced to RESEARCH.md):**
- `DatabaseHeader::write_to` serializes exactly 42 bytes; `file_size`/`unique_kmers` are in-memory-only → count.rs delegation is byte-safe (RESEARCH.md §4)
- `cargo build` does NOT enforce clippy print lints; only `cargo clippy` does (RESEARCH.md §2 pitfall)
- `src/cli/` is a child module of the rlib → inherits `#![deny]` from `src/lib.rs` → needs `#![allow]` at `src/cli/mod.rs` (RESEARCH.md §2)
- `tests/mod.rs` is a shared module, NOT a test target; new `tests/*.rs` files are auto-discovered (RESEARCH.md §8)
- CJK syn visitor needs BOTH `visit_lit` and `visit_macro` (else `println!`/`format!` CJK strings are missed — RESEARCH.md §1)
- Dead files (`*_backup*`, `*new_approaches*`) in `pyo3/src/` must be excluded from the CJK scan (RESEARCH.md §1, A1)
- D-10 (golden-first) is the only hard sequencing constraint across the 4 plans
