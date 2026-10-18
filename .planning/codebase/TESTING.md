---
last_mapped_at: 2026-10-18
last_mapped_commit: 51629b5ea7ed323cfb60ef0be9cab2f30f6a2ed6
---
# Testing Patterns

**Analysis Date:** 2026-10-18

*Scope: `.github/`, `pyo3/`, `src/`, `tests/` (incremental refresh of the 2026-10-17 full map).*

## Test Framework

**Runner (Rust):**
- Built-in `cargo test`; property tests via `proptest 1.5`; benchmarks via `criterion 0.5` (dev-dependencies in `Cargo.toml`)
- No custom test harness; `[[bench]]` python_cli_comparison is commented out

**Runner (Python bindings):**
- `pytest` (+ `pytest-cov`, `pytest-benchmark`) in `pyo3/`; config in `pyo3/pyproject.toml` (maturin backend, package `pyrustkmer`)

**CI Gate (`.github/workflows/ci.yml`, merge gate FOUND-01):**
- `fmt`: `cargo fmt --all --check` (ubuntu)
- `clippy-root`: `cargo clippy --all-targets -- -D warnings` on ubuntu/macos/**windows**
- `test-root`: `cargo test` on ubuntu/macos/windows
- `pyo3-build`: `cargo clippy --all-targets -- -D warnings` + `maturin build` (sdist + wheel) on all three OSes; wheel uploaded as artifact
- No `continue-on-error`, no `|| true` — every gate step failing fails the PR
- PRs use `pull_request` (not `pull_request_target`) with `permissions: contents: read` (T-01-SC)

**Assertion Library:**
- Rust: standard `assert!` / `assert_eq!` with format-message args
- Python: plain `assert` + `pytest.raises` / fixtures

**Run Commands:**

```bash
cargo test                           # Run all Rust tests
cargo test --test merge_bounded_memory_tests   # Single integration binary
cargo clippy --all-targets -- -D warnings      # CI-equivalent lint gate
cd pyo3 && pytest                    # Python binding tests
cd pyo3 && pytest --cov=pyrustkmer   # Coverage (coverage.xml/htmlcov present)
```

## Test File Organization

**Location:**
- Rust integration tests: `tests/*.rs` — each top-level file is a separate binary pulling `mod common;` (or the `#[path = "common/factories.rs"]` factories-only variant)
- Rust unit tests: inline `#[cfg(test)] mod tests` at bottom of source files (`src/database/{format,index,query,streaming_merge}.rs`, `src/database/merge_tests.rs`) and in `tests/common/mod.rs` (helper self-tests)
- Subdirectory suites: `tests/unit/`, `tests/integration/`, `tests/property/`, `tests/contract/`, `tests/consistency/`, `tests/performance/`, `tests/007-api-compatibility/`, `tests/converted/` — wired through `tests/mod.rs` (`pub mod common; integration; property; unit;`)
- Python tests: `pyo3/tests/test_*.py` with `conftest.py` + `utils.py`

**Naming:**
- Files: `*_tests.rs` (integration), `*_properties.rs` (property), `test_*.py` (Python)
- Functions: `test_snake_case`; Python classes `TestPyDatabase` grouping related tests

**Structure:**

```
tests/
├── common/            # Shared helper library: mod.rs (facade+self-tests),
│                      #   factories.rs, memory.rs, performance.rs, temp_files.rs
├── fixtures/          # Golden .rkdb files (k21/32/64 x canon/noncanon x sorted/unsorted)
│                      #   + golden_manifest.sha256 + legacy_v2_offset42.rkdb
├── unit/ integration/ property/ contract/ consistency/ performance/
│                      #   subdirectory suites via tests/mod.rs
├── mod.rs             # suite registry
└── *_tests.rs         # top-level integration binaries (~8,656 lines total)
```

**Notable top-level binaries (phase 03 wave):** `merge_routing_tests.rs`, `merge_route_parity_tests.rs`, `merge_cleanup_tests.rs`, `merge_bounded_memory_tests.rs`, `merge_frontend_validation_tests.rs`, `dense_differential_tests.rs`, `dense_proptest_tests.rs`, `dense_memory_tests.rs`, `dense_merge_integration_tests.rs`, `golden_sha256_tests.rs`, `parallel_count_tests.rs`, `round_trip_tests.rs`, `golden_tests.rs`, `legacy_readback_tests.rs`, `consistency_tests.rs`, `prefix_cache_{conservation,output_order}_tests.rs`.

## Test Structure

**Suite Organization (typical integration test):**

```rust
//! Header doc citing plan/decision (e.g., "Phase 3, plan 03-10 — closes gap G2 (CR-02)")

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
- Matrix-driven coverage loops (k x canonical x sorted — the "D-13 coverage matrix"); `golden_sha256_tests.rs` iterates `GOLDEN_FIXTURES` so a format drift reports as ONE failure naming every affected cell
- `tempfile::NamedTempFile`/`tempdir()` for all scratch files, never fixed paths
- Descriptive assertion messages with parameter context

**RED-scaffold / TDD discipline (Wave-0, phase 03):**
- Failing-first scaffolds are written before implementation; the measurement helper must be executable on the developer's OS so RED is actually observed (rationale documented in `tests/merge_bounded_memory_tests.rs` `current_rss_kb` doc)
- Memory-bound assertions must be derived from pinned constants (e.g., `chunk_size = CHUNK_ENTRIES = 50_000`, bound = `12 * CHUNK_ENTRIES * size_of::<KmerEntry>()`), never from unvalidated N-relative formulas; the rejected formula stays out of the file "by design"
- Assert `size_of::<KmerEntry>()` in-band so the derivation cannot quietly become false
- RSS measurement: peak sampled by a background thread minus a post-fixture baseline (a plain before/after delta measures allocator free-list reuse, not footprint — plan 03-06 pitfall)

## Mocking

**Framework:** None — no mock libraries in either language

**What to do instead:**
- Real `RKDatabase` objects built from in-memory k-mer pairs via factories
- Real temp files/dirs (`tempfile` crate; `tests/common/temp_files.rs`)
- Differential testing replaces mocking: compare two real implementations (u64 vs u128 storage in `tests/dense_differential_tests.rs`, `tests/dense_proptest_tests.rs`; production write-path bytes vs a hand-built reference in `tests/golden_sha256_tests.rs`)
- Cross-plan composition gates: `tests/dense_merge_integration_tests.rs` chains count(u64) -> .rkdb write -> bounded merge -> read -> decoded-map compare, using committed golden fixtures as independent ground truth rather than re-running the counter

## Fixtures and Factories

**Test Data (Rust):**

```rust
// tests/common/factories.rs — re-exported by tests/common/mod.rs
pub type TestResult<T> = Result<T, Box<dyn std::error::Error>>;
pub fn create_test_database(num_kmers: usize, kmer_size: u8, canonical: bool, sorted: bool) -> TestResult<RKDatabase>
pub fn create_overlapping_database(...) -> TestResult<(RKDatabase, Vec<(u128, u32)>)>
pub fn encode_test_kmer(value: u64, kmer_size: u8) -> u128   // base-4 encoding
pub fn databases_have_same_kmers(db1: &RKDatabase, db2: &RKDatabase) -> TestResult<bool>
```

- `tests/common/performance.rs`: `PerformanceMetrics` (durations, ops/sec, MB/s, custom metrics) for perf suites
- `tests/common/memory.rs`, `tests/common/temp_files.rs`: RSS monitors and scratch-file helpers
- Golden binary fixtures: `tests/fixtures/golden_k{21,32,64}_{canon,noncanon}_{sorted,unsorted}.rkdb` + `golden_manifest.sha256`; generator `tests/golden_generate.rs`, hash checks in `tests/golden_sha256_tests.rs` and `tests/golden_tests.rs`
- **Golden baselines are ground truth, never regenerated** (D-10): if the re-hash fails, revert the drift — never re-capture the manifest
- Deterministic inline fixtures: `write_fixture_pair` in `tests/merge_bounded_memory_tests.rs` builds two inputs from disjoint value ranges (offset `1 << 40`) so the union is exactly `2 * entries` and a dropped input moves output size, not just counts

**Test Data (Python):**
- Session-scoped fixtures in `pyo3/tests/conftest.py` (`pyo3_test_data_dir`, `pyo3_test_databases` metadata dict with file sizes and k-mer sizes); shared `.rkdb` corpus referenced from a sibling `python/tests/test_data/` tree

## Coverage

**Requirements:** No enforced Rust threshold. (`pyo3/pyproject.toml` declares `--cov-fail-under=80` in pytest addopts config; coverage.xml/htmlcov artifacts present in `pyo3/tests/`.)

**View Coverage:**

```bash
cd pyo3 && pytest --cov=pyrustkmer   # writes coverage.xml / htmlcov/
```

Rust coverage: none configured.

## Test Types

**Unit Tests:**
- Inline `#[cfg(test)] mod tests` in source files; focused on one module (e.g., `src/database/merge_tests.rs` memory-monitor tests)

**Integration Tests:**
- Cross-module binaries in `tests/`: write/read round trips, merge routing and route parity (`merge_routing_tests.rs`, `merge_route_parity_tests.rs`), merge cleanup (`merge_cleanup_tests.rs`), output-bounded memory (`merge_bounded_memory_tests.rs`), parallel counting (`parallel_count_tests.rs`), memory ceilings (`dense_memory_tests.rs`), cross-plan composition (`dense_merge_integration_tests.rs`)

**Property-Based Tests:**
- `proptest` strategies generating DNA strings; differential invariant "u64 and u128 widths must agree" (`tests/dense_proptest_tests.rs`); statistical properties in `tests/property/stats_properties.rs`
- Strategy pattern: `proptest::collection::vec(prop::sample::select(vec![b'A',b'C',b'G',b'T']), 1usize..=400).prop_map(...)`

**Meta-Lint Tests (unusual, important):**
- `tests/cjk_check.rs`: parses all `src/` and `pyo3/src/` `.rs` files with `syn` and fails on any CJK string literal. Treat it as a repo-wide gate — English-only string literals.

**E2E Tests:**
- Python tests invoke the built CLI via `subprocess` and the PyO3 module directly (`pyo3/tests/`)

## Common Patterns

**Async Testing:** Not used (fully synchronous codebase; parallelism via rayon, not async)

**Error Testing:**

```rust
// exact error-message assertions are deliberate contract tests
assert_eq!(err.to_string(), "expected exact external-sort compatibility text");
```

- Error display strings are asserted verbatim — never reword error messages in `src/error.rs` or `src/database/merge_error.rs` without running the full suite

**Exactness discipline (phase 03 lesson):**
- Pin the exact k-mer set, exact per-k-mer counts, and header `total_kmers` — never assert merely "non-empty" (two latent streaming-merge data-loss bugs survived a non-empty-only assertion; see `tests/dense_merge_integration_tests.rs` header)
- Compare at the DECODED `(String, u32)` level across width families, never raw integers (u64 and u128 encodings left-align differently — D-04)

**Box→anyhow bridge for shared helpers:**

```rust
trait TestResultExt<T> { fn a(self) -> anyhow::Result<T>; }
impl<T> TestResultExt<T> for Result<T, Box<dyn std::error::Error>> { ... }
```

(`tests/round_trip_tests.rs` — reuse this pattern rather than re-inventing per binary)

**Platform-gated measurement tests:**
- `#[cfg(target_os = "linux")]` for `/proc`-based RSS tests (`tests/dense_memory_tests.rs`); `#[cfg(not(any(linux, windows)))]` `ps`-based fallback so the bound still executes on macOS (`tests/merge_bounded_memory_tests.rs`); Windows-specific `#[cfg(target_os = "windows")]` helpers for file-mtime backdating (`tests/merge_cleanup_tests.rs`, `tests/merge_bounded_memory_tests.rs`). CI runs `cargo test` on all three OSes, so every arm is exercised somewhere.

**New-test placement guidance:**
- Tests one module's internals → inline `#[cfg(test)] mod tests` in that file
- Tests cross-module behavior or file I/O → new `tests/*_tests.rs` binary using `mod common;` (or `#[path = "common/factories.rs"]` for factories-only)
- Statistical/generative invariant → `tests/property/` with proptest
- Golden fixture changes → regenerate via `tests/golden_generate.rs` and update `tests/fixtures/golden_manifest.sha256` — but treat a failing re-hash as format drift to revert, not a manifest to refresh

---

*Testing analysis: 2026-10-18*
