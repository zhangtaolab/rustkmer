---
last_mapped_commit: 0f442541636e002a322db9d1ba091ff046e62284
last_mapped_at: 2026-10-08
---
# Testing Patterns

**Analysis Date:** 2026-10-08

## Test Framework

**Runner (Rust):**
- Built-in `cargo test`; property tests via `proptest 1.5`; benchmarks via `criterion 0.5` (dev-dependencies in `Cargo.toml`)
- No custom test harness; `[[bench]]` python_cli_comparison is commented out

**Runner (Python bindings):**
- `pytest` (+ `pytest-cov`) in `pyo3/`; config in `pyo3/pyproject.toml` (maturin backend, package `pyrustkmer`)

**Assertion Library:**
- Rust: standard `assert!` / `assert_eq!` with format-message args
- Python: plain `assert` + `pytest.raises` / fixtures

**Run Commands:**

```bash
cargo test                    # Run all Rust tests
cargo test --test round_trip_tests   # Single integration binary
cargo clippy                  # Lint gate (per CLAUDE.md)
cd pyo3 && pytest             # Python binding tests
cd pyo3 && pytest --cov=pyrustkmer  # Coverage (coverage.xml/htmlcov present)
```

## Test File Organization

**Location:**
- Rust integration tests: `tests/*.rs` (each a separate binary pulling `mod common;`)
- Rust unit tests: inline `#[cfg(test)] mod tests` at bottom of source files (e.g., `src/database/merge_tests.rs` is included from the database module; `src/database/{format,index,query,suffix_query,prefix_query,streaming_merge}.rs` contain `mod tests`)
- Subdirectory suites: `tests/unit/`, `tests/integration/`, `tests/property/`, `tests/contract/`, `tests/consistency/`, `tests/performance/`, `tests/007-api-compatibility/`, `tests/converted/` — all wired through `tests/mod.rs` (`pub mod common; integration; property; unit;`)
- Python tests: `pyo3/tests/test_*.py` with `conftest.py` + `utils.py`

**Naming:**
- Files: `*_tests.rs` (integration), `*_properties.rs` (property tests), `test_*.py` (Python)
- Functions: `test_snake_case`; Python classes `TestPyDatabase` grouping related tests

**Structure:**

```
tests/
├── common/            # Shared factory/helper library (mod.rs + memory, performance, temp_files)
├── fixtures/          # Golden .rkdb files (k21/32/64 x canon/noncanon x sorted/unsorted), FASTA, sha256 manifest
├── unit/              # unit/database/{canonical_handling,query_canonical}_tests.rs
├── integration/       # queryx_tests.rs, stats_integration.rs, common.rs
├── property/          # stats_properties.rs
├── mod.rs             # suite registry
└── *_tests.rs         # top-level integration binaries
```

## Test Structure

**Suite Organization (typical integration test):**

```rust
//! Header doc citing plan/decision (e.g., "Plan 01-03, Task 2 (decision D-09)")

mod common;
use common::*;
use rustkmer::database::format::RKDatabase;

#[test]
fn round_trip_full_matrix() -> anyhow::Result<()> {
    for &k in &[21usize, 32, 64] {
        for &canonical in &[true, false] {
            for &sorted in &[true, false] {
                let original = create_test_database(50, k as u8, canonical, sorted).a()?;
                // ... assert! with descriptive format message
            }
        }
    }
    Ok(())
}
```

**Patterns:**
- Return `anyhow::Result<()>` from I/O-heavy tests; `Ok(())` at end
- Matrix-driven coverage loops (k x canonical x sorted — the "D-13 coverage matrix") instead of duplicated tests
- `tempfile::NamedTempFile`/`tempdir()` for all scratch files, never fixed paths
- Descriptive assertion messages with parameter context (`"round-trip failed for k={}, canonical={}, sorted={}"`)

## Mocking

**Framework:** None — no mock libraries in either language

**What to do instead:**
- Real `RKDatabase` objects built from in-memory k-mer pairs via factories
- Real temp files/dirs (`tempfile` crate; `tests/common/temp_files.rs`)
- Differential testing replaces mocking: compare two real implementations against each other (u64 vs u128 storage in `tests/dense_differential_tests.rs`, `tests/dense_proptest_tests.rs`)

## Fixtures and Factories

**Test Data (Rust):**

```rust
// tests/common/mod.rs — shared factories, `#![allow(dead_code)]` (per-binary usage varies)
pub type TestResult<T> = Result<T, Box<dyn std::error::Error>>;
pub fn create_test_database(num_kmers: usize, kmer_size: u8, canonical: bool, sorted: bool) -> TestResult<RKDatabase>
pub fn create_overlapping_database(...) -> TestResult<(RKDatabase, Vec<(u128, u32)>)>
pub fn encode_test_kmer(value: u64, kmer_size: u8) -> u128   // base-4 encoding
pub fn databases_have_same_kmers(db1: &RKDatabase, db2: &RKDatabase) -> TestResult<bool>
```

- Golden binary fixtures: `tests/fixtures/golden_k{21,32,64}_{canon,noncanon}_{sorted,unsorted}.rkdb` + `golden_manifest.sha256`; generator at `tests/golden_generate.rs`, hash checks in `tests/golden_sha256_tests.rs` and behavior checks in `tests/golden_tests.rs`
- Legacy format fixture: `tests/fixtures/legacy_v2_offset42.rkdb`

**Test Data (Python):**
- Session-scoped fixtures in `pyo3/tests/conftest.py` (`pyo3_test_data_dir`, `pyo3_test_databases` metadata dict with file sizes and k-mer sizes); shared `.rkdb` corpus referenced from a sibling `python/tests/test_data/` tree

## Coverage

**Requirements:** No enforced threshold

**View Coverage:**

```bash
cd pyo3 && pytest --cov=pyrustkmer   # writes coverage.xml / htmlcov/
```

Rust coverage: none configured (a stale `pyo3/.coverage` artifact exists).

## Test Types

**Unit Tests:**
- Inline `#[cfg(test)] mod tests` in source files; focused on one module (e.g., `src/database/merge_tests.rs` memory-monitor tests)

**Integration Tests:**
- Cross-module binaries in `tests/` exercising write/read round trips, merge routing (`merge_routing_tests.rs`, `merge_route_parity_tests.rs`), parallel counting (`parallel_count_tests.rs`), memory ceilings (`dense_memory_tests.rs`)

**Property-Based Tests:**
- `proptest` strategies generating DNA strings; differential invariant "u64 and u128 widths must agree" (`tests/dense_proptest_tests.rs`); statistical properties in `tests/property/stats_properties.rs`
- Strategy pattern: `proptest::collection::vec(prop::sample::select(vec![b'A',b'C',b'G',b'T']), 1usize..=400).prop_map(...)`

**Meta-Lint Tests (unusual, important):**
- `tests/cjk_check.rs`: parses all `src/` and `pyo3/src/` `.rs` files with `syn` and fails on any CJK string literal (visits both `Lit` and macro `TokenTree`s). Treat it as a repo-wide gate — English-only string literals.

**E2E Tests:**
- Python tests invoke the built CLI via `subprocess` and the PyO3 module directly (`pyo3/tests/`)

## Common Patterns

**Async Testing:** Not used (fully synchronous codebase; parallelism via rayon, not async)

**Error Testing:**

```rust
// exact error-message assertions are deliberate contract tests
assert_eq!(err.to_string(), "expected exact external-sort compatibility text");
```

- Error display strings are asserted verbatim (commit dc1c25a) — never reword error messages in `src/error.rs` or `src/database/merge_error.rs` without running the full suite

**Box→anyhow bridge for shared helpers:**

```rust
trait TestResultExt<T> { fn a(self) -> anyhow::Result<T>; }
impl<T> TestResultExt<T> for Result<T, Box<dyn std::error::Error>> { ... }
```

(`tests/round_trip_tests.rs` — reuse this pattern rather than re-inventing per binary)

**New-test placement guidance:**
- Tests one module's internals → inline `#[cfg(test)] mod tests` in that file
- Tests cross-module behavior or file I/O → new `tests/*_tests.rs` binary using `mod common;`
- Statistical/generative invariant → `tests/property/` with proptest
- Golden fixture changes → regenerate via `tests/golden_generate.rs` and update `tests/fixtures/golden_manifest.sha256`

---

*Testing analysis: 2026-10-08*
