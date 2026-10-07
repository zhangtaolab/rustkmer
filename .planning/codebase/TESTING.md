---
last_mapped_commit: 511b99e5b23614e60426e04a74bcf91a3c5d1a32
last_mapped_at: 2026-10-07
---
# Testing Patterns

**Analysis Date:** 2026-10-07

## Test Framework

**Runner (Rust):**
- Built-in `#[test]` harness, run with `cargo test` — CI gate `.github/workflows/ci.yml` (`test-root` job, ubuntu + macos).
- Dev-dependencies in `Cargo.toml` (`[dev-dependencies]`): `tempfile = "3.12"`, `proptest = "1.5"`, `criterion = { version = "0.5", features = ["html_reports"] }` (configured but currently unused — no `benches/` directory exists and `[[bench]]` is commented out in `Cargo.toml`), `syn` + `proc-macro2` (for the `tests/cjk_check.rs` source-lint), `rand` + `rand_chacha`.
- `sha2` is a regular dependency reused by golden tests for sha256 hashing (`tests/golden_tests.rs`).

**Assertion Library:**
- `std` macros: `assert!`, `assert_eq!` with a descriptive message as the trailing argument.
- `proptest` macros inside `proptest!` blocks: `prop_assert!`, `prop_assert_eq!` (`tests/property/stats_properties.rs`).
- `anyhow::Result<()>` in test bodies for `?`-propagation (documented as the convention in `tests/golden_tests.rs:17`).

**Runner (Python):**
- `pytest` for the PyO3 bindings (`pyo3/tests/`), with `pytest-cov` configured for coverage (`pyo3/pyproject.toml` `[tool.pytest.ini_options]`), `pytest-benchmark` and `hypothesis` available via extras/README.
- Root `pyo3/pyproject.toml` addopts: `--cov=pyrustkmer --cov-report=term-missing --cov-report=html --cov-report=xml --cov-fail-under=80 -v`.
- Legacy pytest configs also exist at `tests/converted/pytest.ini` and `tests/007-api-compatibility/pytest.ini` (their test bodies are absent — see "Currently orphaned" below).

**Run Commands:**

```bash
cargo test                              # All Rust tests (CI gate)
cargo test --test golden_tests          # Single target
cargo test --test parallel_count_tests -- --ignored capture_parallel_count_baseline
                                        # One-shot baseline capture (do NOT rerun casually)
cargo test --test golden_generate -- --ignored
                                        # One-shot fixture generator — writes committed files
cargo fmt --all --check                 # CI gate
cargo clippy --all-targets -- -D warnings   # CI gate (also run inside pyo3/)

# Python bindings

cd pyo3 && maturin develop --release    # Build the extension first
pytest tests/ -v                        # Run from pyo3/ so pyproject config/coverage applies
pytest tests/test_counter.py -v         # Single file
```

## Test File Organization

**Location — three tiers:**

1. **In-source unit tests:** `#[cfg(test)] mod tests { use super::*; ... }` at the bottom of the module under test. Present in 41 source files, ~213 `#[test]` functions total, e.g. `src/hash/table.rs:479`, `src/kmer/canonical.rs:97`, `src/fuzzy/query.rs:514`. A standalone variant exists at `src/database/merge_tests.rs` (wrapped in its own `#[cfg(test)]`; note it is currently not declared by `src/database/mod.rs`, so it does not compile or run).

2. **Top-level integration targets:** every `.rs` directly under `tests/` is its own cargo test crate. Active targets:

| Target | Focus | Tests |
|--------|-------|-------|
| `tests/golden_tests.rs` | sha256 golden `.rkdb` regression + cross-consistency | 14 |
| `tests/parallel_count_tests.rs` | 1-vs-N thread differential, baseline cross-check, determinism, thread precedence | 5 (1 `#[ignore]`d generator) |
| `tests/cjk_check.rs` | Source-lint gate: no CJK string literals in non-CLI code | 5 |
| `tests/legacy_readback_tests.rs` | Legacy `data_offset = 42` read-back | 3 |
| `tests/round_trip_tests.rs` | write→read round-trip of `.rkdb` | 3 |
| `tests/consistency_tests.rs` | u64/u128 consistency placeholder + parallel-merge logging invariant | 2 |
| `tests/golden_generate.rs` | `#[ignore]`d one-shot fixture generator | 1 |
| `tests/mod.rs` | Aggregator declaring `common`/`integration`/`property`/`unit` | 0 direct |

3. **Nested suites compiled through declarations:** files inside `tests/integration/`, `tests/unit/`, `tests/property/`, `tests/consistency/`, `tests/contract/` compile only when declared by a parent `mod.rs` (or a top-level file). Shared helpers use the `mod common; use common::*;` pattern (`tests/round_trip_tests.rs:15-17`, `tests/golden_tests.rs:19-21`).

**Wiring rule (important):** cargo auto-discovers only `.rs` files directly under `tests/`. A file in a subdirectory that no parent declares is never compiled and never runs. Before adding tests under `tests/<suite>/`, declare the module in `tests/<suite>/mod.rs`.

**Currently orphaned (not declared, do not assume they run):**
- `tests/integration/queryx_tests.rs` (12 tests, imports `rustkmer::cli::commands::queryx` / `rustkmer::database::parallel_query`, which no longer exist in `src/`), `tests/integration/stats_integration.rs` (8), `tests/integration/common.rs`
- `tests/unit/stats_tests.rs` (5), `tests/unit/database/canonical_handling_tests.rs` (9), `tests/unit/database/query_canonical_tests.rs` (3)
- `tests/property/stats_properties.rs` (4 proptest blocks)
- `tests/contract/basic_query_test.rs`, `tests/contract/query_consistency.rs` (no top-level `contract.rs` exists)
- `src/database/merge_tests.rs` (not declared in `src/database/mod.rs`)
- `tests/performance/test_fuzzy_query_performance.py` (imports a `rustkmer` Python package that does not exist in the repo)
- `tests/007-api-compatibility/` and `tests/converted/` contain pytest configs/readmes but no test files, and reference a missing `python/` tree

When touching any of these, decide explicitly: wire it up (`pub mod ...;`) and fix stale imports, or leave it out of the compiled set.

**Naming:**
- Rust: `test_<subject>_<condition>` for most tests (`test_streaming_stats_processor_empty`, `test_round_trip_preserves_kmer_counts`); regression tests that represent a documented decision use outcome names (`golden_k32_canon_sorted_matches_manifest`, `legacy_offset42_reads_via_database_query`, `baseline_matches_current`).
- Python: `test_<behavior>` inside `Test<Class>` classes (`TestPyCounterBasicCreation::test_invalid_kmer_size_zero_raises_error`).

## Test Structure

**Simple unit test (in-source):**

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_canonical_kmer() {
        let atgc_encoded = encode_kmer("ATGC").unwrap();
        let canonical = canonical_kmer(atgc_encoded, 4).unwrap();
        assert_eq!(canonical, atgc_encoded);
    }
}
```

(`src/kmer/canonical.rs:97-115`)

**Integration test body — `anyhow::Result<()>` + `?`, terminal `Ok(())`:**

```rust
#[test]
fn legacy_offset42_loads_post_refactor() -> anyhow::Result<()> {
    let db = RKDatabase::from_file_path(std::path::Path::new(LEGACY_PATH))
        .map_err(|e| anyhow::anyhow!("legacy fixture failed to load post-refactor: {}", e))?;
    let kmers = db.all_kmers()?;
    assert!(!kmers.is_empty(), "legacy fixture must contain nonzero k-mers");
    Ok(())
}
```

(`tests/legacy_readback_tests.rs:22-43`)

**Property test block:**

```rust
proptest! {
    #![proptest_config(ProptestConfig::with_cases(100))]

    #[test]
    fn test_stats_mean_median_invariants(
        counts in prop::collection::vec(1u32..=1000u32, 1..=100)
    ) {
        // ... build processor, add counts ...
        prop_assert_eq!(stats.total_kmers, expected_total);
    }
}
```

(`tests/property/stats_properties.rs:8-72`)

**One-shot generators — `#[ignore]` with a reason and run instructions in the doc comment:**

```rust
#[test]
#[ignore = "one-shot pre-refactor baseline capture (D-10); run with --ignored"]
fn capture_parallel_count_baseline() -> Result<(), Box<dyn std::error::Error>> { ... }
```

(`tests/parallel_count_tests.rs:229`, `tests/golden_generate.rs:169`). Committed generated artifacts are treated as ground truth — comments explicitly warn against regeneration.

**Panic expectation (rare):**

```rust
#[test]
#[should_panic(expected = "Sequences must have the same length")]
fn test_hamming_distance_different_lengths() { ... }
```

(`src/fuzzy/mutation.rs:678`)

**Patterns:**
- One assertion theme per test; matrix cells each get their own `#[test]` so failures localize (`golden_k{21,32,64}_{canon,sorted}` — 12 separate tests in `tests/golden_tests.rs`).
- Assertions carry messages explaining the contract: `assert!(result.is_ok(), "QueryX execution should succeed")` (`tests/integration/queryx_tests.rs:48`).
- Tests reference the decision IDs (D-09, PCOUNT-04, etc.) in comments and test names where behavior is contractual.
- Deterministic inputs are hand-built, not random, for regression tests (fixed `BASELINE_INPUT` in `tests/parallel_count_tests.rs`); `rand` is only used for synthetic binary blobs (`tests/common/temp_files.rs:130`).
- Concurrency tests spawn workers with `std::thread::scope`, join every handle, and propagate the first error (`tests/parallel_count_tests.rs:166-207`).

## Mocking

**Framework:** None for Rust. The codebase deliberately tests against real implementations and real files — there is no `mockall`, `wiremock`, or trait-fake infrastructure anywhere in `tests/` or `src/`.

**Patterns:**
- Real `.rkdb` databases built in-memory and written to `tempfile` dirs: `RKDatabase::from_kmer_pairs(...)` + `TempDir`/`NamedTempFile` (51 usages of temp-dir helpers across `tests/` and `src/`).
- Real files on disk from shared factories (`tests/common/mod.rs`) and committed fixtures (`tests/fixtures/`).
- CLI-level tests invoke the compiled binary directly — `Command::new("./target/debug/rustkmer")` (`tests/consistency/utils.rs:89`, `tests/integration/stats_integration.rs:9`). Requires `cargo build` first; prefer in-process `execute_*` calls where possible.
- Error-type bridging is done with a small adapter trait rather than mocks:

```rust
trait TestResultExt<T> { fn a(self) -> anyhow::Result<T>; }
impl<T> TestResultExt<T> for Result<T, Box<dyn std::error::Error>> {
    fn a(self) -> anyhow::Result<T> { self.map_err(|e| anyhow::anyhow!("{}", e)) }
}
```

(`tests/round_trip_tests.rs:20-29`)

**What to Mock (Python):** nothing — pytest fixtures skip rather than mock when prerequisites are missing (`pytest.skip(f"Test database not found: {db_file}")`, `pyo3/tests/conftest.py:59`; module-import skip in `pyo3/tests/test_counter.py:9-12`).

## Fixtures and Factories

**Test Data:**
- `tests/fixtures/` — committed golden data:
  - `golden_k{21,32,64}_{canon,noncanon}_{sorted,unsorted}.rkdb` + `golden_manifest.sha256` (12 fixtures, name → sha256)
  - `legacy_v2_offset42.rkdb` (legacy format read-back)
  - `parallel_count_baseline/k{21,32,64}_{canon,noncanon}.json` (pre-refactor count maps; JSON object keyed by stringified u128, numerically ordered `BTreeMap`)
  - `k64_test.fasta`, `k33_test.fasta`, `ambiguous_test.fasta`, `kmers/*.json` (`basic_kmers`, `canonical_pairs`, `edge_cases`, `invalid_sequences`)
- `test_data/` at repo root (`sequences/`, `kmers/`) — older dataset location.
- Python data (expected at `python/tests/test_data/` from `pyo3/tests/conftest.py`; currently missing → fixtures skip).

**Factories (`tests/common/mod.rs`):**

```rust
pub fn create_test_database(num_kmers: usize, kmer_size: u8, canonical: bool, sorted: bool) -> TestResult<RKDatabase>;
pub fn create_overlapping_database(num_kmers, kmer_size, canonical, sorted, overlap_ratio) -> TestResult<(RKDatabase, Vec<(u128, u32)>)>;
pub fn create_database_from_kmers(kmers: Vec<(u128, u32)>, kmer_size, canonical, sorted) -> TestResult<RKDatabase>;
pub fn encode_test_kmer(value: u64, kmer_size: u8) -> u128;
pub fn generate_kmer_sequence(start: u64, count: usize, kmer_size: u8) -> Vec<u128>;
pub fn databases_have_same_kmers(db1: &RKDatabase, db2: &RKDatabase) -> TestResult<bool>;
```

Import via `mod common; use common::*;`. The module carries `#![allow(dead_code)]` because each test crate compiles only the subset it uses (`tests/common/mod.rs:3-10`).

**Temp-file helpers (`tests/common/temp_files.rs`):**
- `TempFileManager` — RAII: `Drop` runs best-effort cleanup; methods `create_temp_file`, `create_temp_text_file`, `create_temp_fasta`, `create_temp_fastq`, `save_database_to_temp`, `create_temp_binary`, `get_file_size`, `cleanup`.
- Macros: `temp_file!("content", ".txt")`, `temp_fasta!("header1" => "ATCG", ...)`.
- `TempFileError` is a domain `thiserror` enum, mirroring library conventions.

**Performance/memory helpers:** `tests/common/performance.rs` (`PerformanceMetrics`, ops/sec, throughput), `tests/common/memory.rs` (`MemoryMonitor`, `get_current_memory_usage`). Both carry `#![allow(dead_code)]`.

**Python fixtures (`pyo3/tests/conftest.py`):**
- Session-scoped: `pyo3_test_data_dir`, `pyo3_test_databases` metadata map.
- DB path fixtures (`tiny_db_path`, `small_db_path`, `k33_db_path`) skip when the file is absent.
- Class fixtures (`PyDatabase`, `PyCounter`, `PyFuzzyQuery`, `PyPrefixQuery`, `LoadMode`) import `pyrustkmer` and skip when unavailable.
- Shared helper functions in `pyo3/tests/utils.py` (`get_test_kmers`, `reverse_complement`, `compare_results`).

## Coverage

**Requirements:**
- Rust: no coverage target configured or enforced; CI runs `cargo test` only (`.github/workflows/ci.yml`). No `cargo-llvm-cov`/tarpaulin config.
- Python: `--cov-fail-under=80` for `pyrustkmer` (`pyo3/pyproject.toml`). This applies when pytest resolves its rootdir to `pyo3/` (run from `pyo3/`). `pyo3/tests/.coverage` and `pyo3/.coverage` artifacts exist from local runs.
- Docs pipeline runs `python -m pydocstyle python/rustkmer/ --config=.pydocstylerc` non-blocking (`.github/workflows/docs.yml:53`).

**View Coverage:**

```bash
cd pyo3 && pytest tests/ --cov=pyrustkmer --cov-report=term-missing
```

**CI summary:**
- `.github/workflows/ci.yml`: `fmt` (rustfmt check), `clippy-root` + `test-root` (ubuntu/macos, `cargo test`), `pyo3-build` (clippy + `maturin build`, no pytest execution).
- `.github/workflows/performance-regression.yml`: criterion benchmark jobs exist but are guarded — the referenced `python_cli_comparison` bench target is commented out in `Cargo.toml`, so jobs skip with a warning; later steps call Python scripts under a missing `python/`/`scripts/` path.
- `.github/workflows/docs.yml`: docs build + link check + pydocstyle (non-blocking).

## Test Types

**Unit Tests (Rust):** in-source `#[cfg(test)] mod tests` per module — pure functions, validation, encoding/canonical round-trips, per-module error paths (~213 tests across 41 files).

**Integration Tests (Rust):** top-level `tests/*.rs` exercising real file I/O, format round-trips, and command handlers in-process (`execute_count(&args)` in `tests/contract/basic_query_test.rs`) or via the compiled binary (`tests/consistency/utils.rs`).

**Golden / Regression:** sha256 manifest verification of committed `.rkdb` bytes plus write-path cross-consistency (`tests/golden_tests.rs`); legacy read-back (`tests/legacy_readback_tests.rs`).

**Differential / Concurrency:** 1-worker vs N-worker count-map equality, committed-baseline comparison, byte-identical sorted output across runs, thread-count precedence chain (`tests/parallel_count_tests.rs`).

**Property-Based:** `proptest` with 100 cases per property, asserting statistical invariants (mean/median bounds, frequency-distribution sums) — canonical example at `tests/property/stats_properties.rs` (currently orphaned).

**Source-Lint Tests:** `tests/cjk_check.rs` parses every in-scope `.rs` file with `syn` and fails on CJK string literals, with sanity tests for each Unicode block and for the exclusion patterns.

**Performance Tests:** Python timing benchmarks (`tests/performance/test_fuzzy_query_performance.py`, time-based, asserts batch vs individual speedup). Criterion benchmarks are configured as a dev-dependency but have no `benches/` target.

**Python Binding Tests:** class-based pytest suites (`pyo3/tests/test_core.py`, `test_counter.py`, `test_export.py`, `test_import.py`, `test_pyo3_simple.py`, `test_counter_simple.py`) covering constructors, validation errors, load modes, query results, and exports. Note there is duplication between `test_counter.py` and `test_counter_simple.py` / `test_pyo3_simple.py` (parallel coverage of the same APIs).

**E2E:** not used (no Playwright/Cypress equivalents; no CLI end-to-end harness beyond `Command::new` patterns above).

## Common Patterns

**Async Testing:** Not applicable — the codebase is synchronous; concurrency is tested with `rayon` and `std::thread::scope` (see `tests/parallel_count_tests.rs:166-207` for the join-all-and-propagate-first-error pattern).

**Error Testing (Rust):**

```rust
let result = execute_queryx(&command);
assert!(result.is_err(), "QueryX should fail with invalid k-mers");
```

Or prefer `?`-propagation in `anyhow::Result` bodies when the error is not the subject of the assertion.

**Error Testing (Python):**

```python
with pytest.raises(ValueError, match="Invalid k-mer size"):
    pyrustkmer.PyCounter(0)
```

(`pyo3/tests/test_counter.py:47-49`)

**CLI subprocess testing (pattern to reuse):**

```rust
let output = Command::new("./target/debug/rustkmer").args(args).output().expect("Failed to execute rustkmer stats");
let stdout = String::from_utf8(output.stdout).unwrap();
let exit_code = output.status.code().unwrap();
```

(`tests/integration/stats_integration.rs:8-25`) — remember this requires a prior `cargo build`.

**Building databases inside tests:** prefer the `tests/common/mod.rs` factories over hand-rolling `RKDatabase` construction; use `TempDir` for on-disk round-trips (`tests/round_trip_tests.rs`).

**Regenerating fixtures:** only through the `#[ignore]`d generators (`golden_generate.rs`, `capture_parallel_count_baseline`) and only when intentionally re-baselining; committed artifacts and their sha256 manifest are the contract.

---

*Testing analysis: 2026-10-07*
