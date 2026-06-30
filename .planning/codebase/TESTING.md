# Testing Patterns

**Analysis Date:** 2026-06-30

The project has **two parallel test ecosystems**: a Rust test suite (root crate `rustkmer`) and a Python test suite for the `pyrustkmer` PyO3 bindings plus cross-validation against the CLI. Both must pass before release.

## Test Frameworks

### Rust

- **Runner:** built-in `cargo test` harness. Property tests via `proptest = "1.5"` (also a normal dependency). Benchmarks via `criterion = { version = "0.5", features = ["html_reports"] }` (`Cargo.toml:91`).
- **Dev-deps** (`Cargo.toml:89-99`): `criterion`, `tempfile = "3.12"`, `proptest = "1.5"`, `rand = "0.8"`, `rand_chacha = "0.3"`.
- **Assertion library:** standard `assert_eq!` / `assert!` / `assert_ne!`. Integration tests also use `anyhow::Result` for ergonomic `?` in test bodies (`tests/integration/queryx_tests.rs:9,22`).
- **No `rustfmt.toml`/`clippy.toml`** — default lint settings; `cargo clippy` is part of the documented workflow (`CLAUDE.md`).

### Python

- **Runner:** `pytest >= 7.0` with `pytest-cov >= 4.0` and `pytest-benchmark >= 4.0` (`pyo3/pyproject.toml:38-46`). Optional: `hypothesis`, `pytest-benchmark` (README).
- **Assertion library:** bare `assert` + `pytest.raises`.
- **Markers** registered in `pyo3/pyproject.toml:90-94`: `slow`, `performance`, `integration`. Additional per-suite markers in `tests/converted/pytest.ini` (`unit`, `integration`, `performance`, `slow`, `memory`, `cli`, `converted`) and `tests/007-api-compatibility/pytest.ini` (`compatibility`, `performance`, `slow`, `integration`, `unit`).

## Run Commands

### Rust

```bash
cargo test                              # All targets (unit + integration + doctests)
cargo test --release                    # Run tests against optimized build
cargo test --release --test integration # Specific test target (see INSTALL.md:243)
cargo test -- --nocapture               # Show println! output from tests
cargo clippy --all-targets              # Lint (required per CLAUDE.md)
cargo bench                             # criterion benchmarks (criterion harness)
```

### Python (pyrustkmer bindings)

Build the extension before testing (maturin):

```bash
cd pyo3 && maturin develop --release     # Build + install into current env
cd pyo3 && PYO3_PYTHON=$(which python3) maturin develop
pytest pyo3/tests/ -v                    # Run all binding tests (cov auto-enabled)
pytest pyo3/tests/test_counter.py -v     # Single file
pytest pyo3/tests/ --cov-report=term-missing --cov-report=html
pytest -m "not slow"                     # Skip slow/perf markers
```

Coverage is **enforced**: `--cov-fail-under=80` in `pyo3/pyproject.toml:100`.

### Python (cross-validation suites)

```bash
python -m pytest tests/007-api-compatibility/ -v   # CLI ↔ Python API parity
python -m pytest tests/converted/ -v               # Converted test set
python -m pytest tests/ -v                          # All repo-level Python tests
```

### Multi-version smoke test (PyO3 matrix)

```bash
./scripts/test_all_envs.sh        # py311, py312, py313 (build+install+validate)
./scripts/test_current.sh py311   # single env, full wheel build
./scripts/test_pyo3_version.sh 0.27.2 py312   # specific PyO3 version
```

## Test File Organization

### Rust

Two locations, both consumed by the same crate:

1. **Inline unit tests** — `#[cfg(test)] mod tests { use super::*; ... }` at the bottom of source files. Examples: `src/kmer/operations.rs`, `src/hash/table.rs`, `src/database/merge_tests.rs:3`, `tests/common/temp_files.rs:242`, `tests/common/mod.rs:137`.
2. **Integration / property tests** — separate files under `tests/`, aggregated via a top-level `tests/mod.rs` (`tests/mod.rs:1-9`) declaring:
   ```rust
   pub mod common;
   pub mod integration;
   pub mod property;
   pub mod unit;
   ```
   Sub-trees:
   - `tests/unit/` — focused unit suites (e.g. `stats_tests.rs`, `database/canonical_handling_tests.rs`, `database/query_canonical_tests.rs`).
   - `tests/integration/` — multi-module flows (`queryx_tests.rs`, `stats_integration.rs`) with shared `tests/integration/common.rs`.
   - `tests/property/` — `proptest!`-based invariant tests (`stats_properties.rs`).
   - `tests/consistency/` — consistency generators/utils (`generators.rs`, `utils.rs`, `mod.rs`) plus the entrypoint `tests/consistency_tests.rs`.
   - `tests/contract/` — contract tests (`basic_query_test.rs`, `query_consistency.rs`).
   - `tests/common/` — shared test helpers (`mod.rs`, `memory.rs`, `performance.rs`, `temp_files.rs`).
   - `tests/fixtures/` — static data: FASTA (`k33_test.fasta`, `k48_test.fasta`, `k64_test.fasta`, `ambiguous_test.fasta`) and JSON k-mer fixtures (`fixtures/kmers/*.json`).
   - `tests/007-api-compatibility/`, `tests/converted/` — Python suites (see below).
   - `tests/performance/` — Python performance scripts (`test_fuzzy_query_performance.py`).

**Naming:** Rust test files are `*_tests.rs` or `<topic>_tests.rs`; test functions are `fn test_<behaviour>()` or `fn <behaviour>()` inside `#[test]`.

### Python

- **Location:** `pyo3/tests/` for binding tests; `tests/007-api-compatibility/` and `tests/converted/` for CLI parity.
- **Discovery:** `testpaths = ["tests"]`, `python_files = ["test_*.py"]`, `python_classes = ["Test*"]`, `python_functions = ["test_*"]` (`pyo3/pyproject.toml:86-89`).
- **Structure:**
  ```
  pyo3/tests/
  ├── conftest.py           # Session fixtures (db paths, module/class accessors)
  ├── utils.py              # PyO3TestHelper, reverse_complement, compare_results
  ├── test_core.py
  ├── test_counter.py       # Class-grouped: TestPyCounterBasicCreation, TestPyCounterAddKmer, ...
  ├── test_counter_simple.py
  ├── test_export.py
  ├── test_import.py
  └── test_pyo3_simple.py
  ```

## Test Structure

### Rust suite organization

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_streaming_stats_processor_basic() {
        let config = StatsConfiguration { /* ... */ };
        let mut processor = StreamingStatsProcessor::new(config);

        processor.add_count(1).unwrap();
        processor.add_count(2).unwrap();

        let stats = processor.finalize(/* ... */);

        assert_eq!(stats.total_kmers, 9);
        assert!(stats.frequency_distribution.is_none());
    }
}
```
*(Pattern from `tests/unit/stats_tests.rs:7-45`)*

**Conventions:**
- Construct domain objects directly (no test-only constructors); configure via plain structs (`StatsConfiguration`, `MergeConfig`).
- Prefer `.unwrap()` on results inside test bodies (failure is the signal).
- Use descriptive `assert!(cond, "message")` for behavioural checks (`tests/integration/queryx_tests.rs:48-51`).
- Integration tests return `anyhow::Result<()>` so `?` can be used; end with `Ok(())` (`tests/integration/queryx_tests.rs:22,53`).

### Python suite organization

```python
class TestPyCounterBasicCreation:
    """Test basic PyCounter creation and initialization."""

    def test_create_counter_default_params(self):
        """Test creating a counter with default parameters."""
        counter = pyrustkmer.PyCounter(21)
        assert counter is not None
        assert counter.kmer_length == 21
        assert counter.canonical == False

    def test_invalid_kmer_size_zero_raises_error(self):
        """Test that k-mer size of 0 raises ValueError."""
        with pytest.raises(ValueError, match="Invalid k-mer size"):
            pyrustkmer.PyCounter(0)
```
*(Pattern from `pyo3/tests/test_counter.py:16-50`)*

**Conventions:**
- Group related tests into `Test*` classes by behaviour; each test method has a one-line docstring.
- Assert on Python-visible attributes (getters) and use `pytest.raises(..., match=...)` for error paths.
- Skip cleanly when the native module is unavailable: `pytest.skip("pyrustkmer module not installed", allow_module_level=True)` (`pyo3/tests/test_counter.py:10-13`).

## Mocking

**Rust:** no mocking framework in use. Tests exercise real implementations. Where isolation is needed, tests construct small in-memory databases (see Fixtures below). `MemoryMonitor` (`src/database/memory.rs`, used in `src/database/merge_tests.rs:39`) is real, not mocked.

**Python:** no `unittest.mock` usage detected. Tests call into the compiled `pyrustkmer` module directly. `pyo3/tests/utils.py` provides real helper wrappers (`PyO3TestHelper`, `get_test_kmers`).

**What to mock (prescriptive):** nothing by default. Prefer real small inputs. Only mock time-bound / external resources (filesystem paths, env vars) using `tmp_path` / `monkeypatch`.

## Fixtures and Factories

### Rust — in-memory factories (shared)

Centralised in `tests/common/mod.rs`. Re-export via `use common::*;` (see `tests/integration/queryx_tests.rs:16-18`).

```rust
pub type TestResult<T> = Result<T, Box<dyn std::error::Error>>;

pub fn create_test_database(
    num_kmers: usize, kmer_size: u8, canonical: bool, sorted: bool,
) -> TestResult<RKDatabase> { /* ... */ }

pub fn create_overlapping_database(...) -> TestResult<(RKDatabase, Vec<(u128, u32)>)> { /* ... */ }
pub fn create_database_from_kmers(kmers: Vec<(u128, u32)>, ...) -> TestResult<RKDatabase> { /* ... */ }
pub fn encode_test_kmer(value: u64, kmer_size: u8) -> u128 { /* base-4 packing */ }
pub fn databases_have_same_kmers(db1: &RKDatabase, db2: &RKDatabase) -> TestResult<bool> { /* ... */ }
```
*(From `tests/common/mod.rs:9-135`)*

### Rust — temporary files & cleanup

`tests/common/temp_files.rs` provides `TempFileManager` (RAII via `Drop`), convenience functions, and macros:

```rust
let path = temp_file!("test content", ".txt")?;          // macro → .tmp
let fasta = temp_fasta!("hdr1" => "ATCG", "hdr2" => "GCGC")?;  // macro → .fasta

// Programmatic:
let mut mgr = TempFileManager::new()?;                    // dedicated TempDir, auto-cleaned on drop
let p = mgr.create_temp_fasta(&[("s1".into(), "ATCG".into())])?;
let db_path = mgr.save_database_to_temp(&db)?;
```
*(From `tests/common/temp_files.rs:33-239`)*

For tests that don't need tracking, use `TempFileManager::new_with_system_temp()` or the `tempfile::TempDir`/`tempdir()` crate directly (`src/database/merge_tests.rs:9,30`).

### Rust — consistency generators

`tests/consistency/generators.rs` builds FASTA content and expected k-mer counts in-memory (`generate_test_fasta`, `generate_expected_counts`, `create_mixed_sequences`). Marked `#[allow(dead_code)]` because not every config uses them.

### Rust — static fixtures

- `tests/fixtures/*.fasta` — fixed FASTA inputs at k=33/48/64 and ambiguous-base cases.
- `tests/fixtures/kmers/*.json` — `basic_kmers.json`, `canonical_pairs.json`, `edge_cases.json`, `invalid_sequences.json` (see `tests/fixtures/kmers/README.md`).

### Python — pytest fixtures

Session-scoped data providers live in `pyo3/tests/conftest.py`:

```python
@pytest.fixture(scope="session")
def pyo3_test_data_dir():
    return Path(__file__).parent.parent.parent / "python" / "tests" / "test_data"

@pytest.fixture
def tiny_db_path(pyo3_test_data_dir) -> str:
    db_file = pyo3_test_data_dir / "tiny_test.rkdb"
    if not db_file.exists():
        pytest.skip(f"Test database not found: {db_file}")
    return str(db_file)

@pytest.fixture
def PyCounter(pyo3_module):
    if not hasattr(pyo3_module, "PyCounter"):
        pytest.skip("PyCounter class not available")
    return pyrustkmer.PyCounter
```
*(From `pyo3/tests/conftest.py:11-130`)*

Database fixture catalogue is declared once in `pyo3_test_databases` (`conftest.py:17-51`) with size / kmer_size / file_size metadata. Class-accessor fixtures (`PyDatabase`, `PyCounter`, `PyFuzzyQuery`, `PyPrefixQuery`, `LoadMode`) skip the test if the symbol is missing — enables graceful degradation across PyO3 versions.

**Static Python test data:** `test_data/databases/`, `test_data/kmers/`, `test_data/sequences/`; regeneration scripts in `test_data/generate_test_data.py` and `test_data/verify_git_tracking.py`.

## Coverage

**Python:** enforced at **80% minimum** via `--cov-fail-under=80` (`pyo3/pyproject.toml:95-102`). Reports generated in term-missing, HTML, and XML. Source scoped to `pyrustkmer`; omits `*/tests/*`, `*/test_*`, `setup.py`, `build.py` (`pyproject.toml:142-149`). Excluded lines include `pragma: no cover`, `raise NotImplementedError`, `if __name__ == .__main__.`, abstract methods (`pyproject.toml:151-163`). Existing reports: `pyo3/coverage.xml`, `pyo3/htmlcov/`.

**Rust:** no coverage gate configured (no `tarpaulin`/`llvm-cov` config). Treat the inline + `tests/` suites as the coverage vehicle; add a property test alongside any new invariant-heavy code.

**View Python coverage:**
```bash
pytest pyo3/tests/ --cov=pyrustkmer --cov-report=html
open pyo3/htmlcov/index.html
```

## Test Types

**Unit tests (Rust):** `#[cfg(test)] mod tests` in each source file; also dedicated files in `tests/unit/` (`stats_tests.rs`, `database/canonical_handling_tests.rs`, `database/query_canonical_tests.rs`). Fast, in-memory, no I/O.

**Property tests (Rust):** `proptest!` blocks with `ProptestConfig::with_cases(100)`. Verify invariants over generated inputs (sum/min/max/mean relations, frequency-distribution properties) — see `tests/property/stats_properties.rs:8-100`.

**Integration tests (Rust):** `tests/integration/*` exercise multi-module flows end-to-end (CLI command construction → `execute_queryx` → file output assertions). Use `TempDir` + real database files (`tests/integration/queryx_tests.rs:22-54`).

**Contract / consistency tests (Rust):** `tests/contract/`, `tests/consistency/`, `tests/consistency_tests.rs`. NOTE: `consistency_tests.rs:8-15` is currently a `assert!(true)` placeholder with a TODO — real consistency coverage for u64/u128 parity is missing.

**Python binding tests:** `pyo3/tests/test_*.py` — exercise `pyrustkmer` from Python: object construction, getters, file I/O, error mapping, round-trip count/query, export formats.

**Cross-validation tests (Python):** `tests/007-api-compatibility/` asserts CLI and Python API produce identical results; emits JSON reports under `test_reports/`. `tests/converted/` holds migrated test sets.

**Performance tests:** `tests/performance/test_fuzzy_query_performance.py` (Python) and Rust `criterion` benchmarks (currently commented out in `Cargo.toml:115-117`). CI: `.github/workflows/performance-regression.yml`.

**Examples double as integration checks:** `examples/python/test_pyo3_api.py`, `validate_position_mutations.py`, `demo_*.py`.

## Common Patterns

### Async / threaded testing

The crate is multi-threaded (`rayon`, `parking_lot`). Tests do not spawn explicit async runtimes. Thread-safety is verified behaviourally, e.g. `tests/integration/queryx_tests.rs` constructs `Commands::QueryX { threads: 2, batch_size: 10, ... }` and asserts output correctness after parallel execution.

### Error-path testing

```rust
#[test]
fn test_invalid_kmer_size() {
    let result = KmerCounter::new(0, true, 100, 1);
    assert!(result.is_err());
}
```

```python
with pytest.raises(ValueError, match="Invalid k-mer size"):
    pyrustkmer.PyCounter(65)        # > 64 rejected (u128 ceiling)
```
*(Pattern: `pyo3/tests/test_counter.py:57-60`)*

### Parameterised / data-driven tests

- Rust: `proptest!` with strategies like `prop::collection::vec(1u32..=1000u32, 1..=100)` (`tests/property/stats_properties.rs:13`).
- Python: prefer `pytest.mark.parametrize` for new code (not yet widely used in this repo). Multi-value cases currently use simple `for` loops (`pyo3/tests/test_counter.py:42-45`).

### Temp-file hygiene

Always scope file-producing tests under a `TempDir` / `TempFileManager` so cleanup runs on `Drop` even on panic (`tests/common/temp_files.rs:186-191`). Never write test artifacts into the repo root (the root already contains stray `*.rkdb`, `*.rkd`, `*_result.txt` debug files — do not add more).

### Skip-when-absent pattern (Python)

Native extension tests must skip, not error, when the module isn't built:

```python
try:
    import pyrustkmer
except ImportError:
    pytest.skip("pyrustkmer module not installed", allow_module_level=True)
```
*(From `pyo3/tests/test_counter.py:10-13`)*

---

*Testing analysis: 2026-06-30*
