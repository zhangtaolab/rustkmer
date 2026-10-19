<!-- generated-by: gsd-doc-writer -->
# Testing Guide

## Overview

rustkmer has four distinct test surfaces, each with its own runner:

1. **Rust crate tests** (`cargo test`) — unit tests inside `src/` modules, runnable doc examples, and 20 auto-discovered integration-test binaries under `tests/` (19 named binaries plus the `mod` target that wires the shared helper trees). Property-based tests use `proptest`.
2. **Python binding tests** (`pyo3/tests/`, pytest) — 178 test methods across 7 `test_*.py` files exercising the `pyrustkmer` extension, with an 80% coverage gate enforced by the CI `pyo3-pytest` job.
3. **Benchmark harness tests** (`scripts/bench/tests/`) — 130 tests in 8 modules, stdlib `unittest` only (no pytest, no conftest, no pip installs).
4. **Cross-validation / legacy Python trees** (`tests/007-api-compatibility/`, `tests/converted/`, `tests/performance/`) — pytest configuration and committed reports, but currently no collected test modules (see [Legacy Python trees](#legacy-python-trees)).

CI enforces the Rust and benchmark surfaces (plus lint/wheel jobs) on every PR and push to `dev`/`main`; the pytest suites are run locally, not in CI (see [CI integration](#ci-integration)).

## Test framework and setup

### Rust — `cargo test` + proptest

- Framework: cargo's built-in test harness. `cargo test` compiles every `tests/*.rs` file as its own binary, runs `#[cfg(test)]` modules inside `src/` (41 source files contain them), and runs doc tests (runnable ` ```rust ` examples exist in `src/lib.rs` and `src/fuzzy/mod.rs`).
- Property-based testing: `proptest` 1.5 (`[dev-dependencies]` in `Cargo.toml`), used by `tests/dense_proptest_tests.rs`.
- Benchmarks: `criterion` 0.5 is a dev-dependency; the `[[bench]]` target (`python_cli_comparison`) is currently commented out in `Cargo.toml`, so `cargo bench` has no active targets. Performance measurement lives in the separate `scripts/bench/` harness instead.
- No setup beyond a Rust 1.80+ stable toolchain: `cargo test` works from a fresh clone.

### Python bindings — pytest via maturin

- Framework: `pytest>=7.0` with `pytest-cov>=4.0` and `pytest-benchmark>=4.0` (the `dev` extra in `pyo3/pyproject.toml`). Configuration lives in `[tool.pytest.ini_options]`: `testpaths = ["tests"]`, `python_files = ["test_*.py"]`, markers `slow` / `performance` / `integration`.
- Default `addopts` are verbosity-only (`["-v"]`): a plain `pytest` run carries no forced flags; the 80% gate runs in CI on the `pyo3-pytest` job's command line (see [CI integration](#ci-integration)).
- Requires Python 3.11+ and the native module built and installed into the active environment first:

```bash
cd pyo3
pip install -e ".[dev]"      # or: pip install pytest pytest-cov pytest-benchmark maturin
maturin develop --release    # builds and installs the pyrustkmer extension
```

- Every test module guards the native import: `try: import pyrustkmer / except ImportError: pytest.skip(...)` — with the module missing, files skip cleanly instead of erroring.
- Maintainer-only helpers `scripts/test_current.sh [py311|py312|py313]` and `scripts/test_all_envs.sh` build and install the wheel across local conda environments; note they hardcode a `/Users/forrest/miniconda3` path, so they are not portable.

### Benchmark harness — stdlib unittest

`scripts/bench/tests/` is deliberately dependency-free ("stdlib unittest only — no pytest, no conftest", per its module docstrings). Python 3.10+ is enough; nothing to install.

## Running tests

### Full Rust suite

```bash
cargo test                 # unit tests + all 20 integration binaries + doctests
cargo test --release       # same, against the optimized build (slower to compile)
```

### Single binary or filtered run

```bash
cargo test --test merge_routing_tests          # one integration binary
cargo test merge                               # name filter across all targets
cargo test --test golden_sha256_tests dense    # filter within one binary
```

### Golden fixture regeneration (on demand)

`tests/golden_generate.rs` is `#[ignore]`d — it writes committed binary fixtures and is not part of the regression gate:

```bash
cargo test --test golden_generate -- --ignored --nocapture
```

### Python binding tests

Run from `pyo3/` after `maturin develop --release`:

```bash
cd pyo3
pytest                                   # full suite (coverage gate enforced)
pytest tests/test_counter.py             # one file
pytest tests/test_counter.py -k invalid  # filtered run
pytest -m "not slow"                     # marker-based deselection
```

### Benchmark harness tests

Run from the repo root (the tests import `scripts.bench.*`, so the root must be on `sys.path`):

```bash
python3 -m unittest scripts.bench.tests.test_time_parser    # quick module
python3 -m unittest scripts.bench.tests.test_schema \
    scripts.bench.tests.test_compare                        # several modules
```

Note: some modules (e.g. `test_schema`) shell out to a real `bench.py --self-check` run and take on the order of a minute; `test_time_parser` and `test_generator` are near-instant.

### Performance gate locally

The CI regression gate can be reproduced by hand (see `scripts/bench/README.md`):

```bash
cargo build --release                # never time a debug build
python3 scripts/bench/bench.py --mode synthetic --out results.json
python3 scripts/bench/compare.py \
  --baseline scripts/bench/baselines/bench_baseline.darwin.json \
  --current results.json --wall-threshold 0.25 --rss-threshold 0.15 --wall-advisory
```

Use `bench_baseline.linux.json` on Linux. `bench.py --mode synthetic --self-check` is a ~1-minute sanity run that asserts exact k-mer counts.

## Rust integration-test inventory

One binary per `tests/*.rs` file (verified via `cargo metadata`; 20 targets total):

| Binary (`--test <name>`) | What it covers |
|---|---|
| `cjk_check` | CJK string-literal gate: `syn`-parses `src/` and `pyo3/src/` and fails on Han/Hiragana/Katakana/Hangul in string literals (FOUND-04, D-07) |
| `consistency_tests` | u64/u128 consistency helpers (`mod consistency`) plus a rayon logging-interleaving backstop test |
| `dense_differential_tests` | Fixed-input differential: u64-storage vs u128-storage counter on identical input (DENSE-03, D-05/D-13) |
| `dense_memory_tests` | Storage-width claim asserted against the representation a real `KmerCounter` stores (DENSE-01) |
| `dense_merge_integration_tests` | End-to-end cross-plan composition gate for merge over dense storage (MERGE-01) |
| `dense_proptest_tests` | Property-based dense differential: generates inputs and proves the two widths agree (DENSE-03, proptest) |
| `golden_generate` | Ignored one-shot generator of the golden `.rkdb` fixtures (D-10) — run with `--ignored` |
| `golden_sha256_tests` | `.rkdb` v2 byte-identity guard for the dense write path: committed fixtures vs committed SHA-256 manifest, plus a hand-built reference-byte differential (DENSE-02) |
| `golden_tests` | Golden-file regression: one hash check per committed fixture (D-09/D-11/D-13) |
| `legacy_readback_tests` | Read-back of legacy `.rkdb` files with `data_offset = 42` (D-12 boundary) |
| `merge_bounded_memory_tests` | Merge output-boundedness: resident-memory growth bounded by a pinned chunk size, not by N (G2/CR-02) |
| `merge_cleanup_tests` | Temp-shard cleanup on failed/interrupted streaming merges (MERGE-03) |
| `merge_frontend_validation_tests` | Merge CLI front-end validation (MERGE-01 at the CLI surface, gap WR-05) |
| `merge_route_parity_tests` | Route parity above the old endianness threshold (G3/CR-01) |
| `merge_routing_tests` | Merge routing + memory-budget admission control; path selection observed via a temp-dir probe (MERGE-01/02, D-01/D-02) |
| `mod` | Wires `tests/{common,integration,property,unit}`; currently runs the shared-helper self-tests in `tests/common/mod.rs` |
| `parallel_count_tests` | 1-vs-N thread-count differential — a divergence is a definitive concurrency bug (PCOUNT-04) |
| `prefix_cache_conservation_tests` | Route-level conservation proofs for the prefix-cache bucket merge (CR-01/WR-03) |
| `prefix_cache_output_order_tests` | End-to-end output-order and query proofs for the prefix-cache route (CR-02) |
| `round_trip_tests` | `.rkdb` write→read round-trip with byte-identical k-mer counts (D-09, SPEC R3) |

**Wiring caveat:** files in `tests/` subdirectories are only compiled when a top-level `tests/*.rs` binary includes them (`mod x;` or `#[path = ...]`). Currently `tests/consistency/` is included via `consistency_tests.rs`, and `tests/common/factories.rs` is included either through `mod common;` or directly via `#[path = "common/factories.rs"]` (used by `merge_routing_tests.rs` and `merge_cleanup_tests.rs`). The files `tests/integration/queryx_tests.rs`, `tests/integration/stats_integration.rs`, `tests/unit/stats_tests.rs`, `tests/unit/database/*.rs`, `tests/property/stats_properties.rs`, and `tests/contract/*.rs` are referenced by no binary and **do not run** — wire them into a target before relying on them.

## Writing new tests

### Rust conventions

- **Header comments cite requirement/decision IDs.** Every test binary opens with a `//!` block naming the requirement it covers and the decisions it honors (e.g. `MERGE-01`, `DENSE-03`, `D-13`), plus the observation strategy when the behavior is not directly observable. Match this when adding a binary.
- **Shared helpers live in `tests/common/`**, split into `factories.rs` (database/k-mer factories), `memory.rs`, `performance.rs`, and `temp_files.rs`. Include the full module with `mod common;` (compiles its self-tests into your binary), or factories only with `#[path = "common/factories.rs"] mod common;`. The module is `#![allow(dead_code)]` because each binary uses a different subset.
- **Property tests use `proptest`** — see `tests/dense_proptest_tests.rs` for the pattern (strategy + differential assertion).
- **Exactness discipline:** assert exact values, never merely non-empty. The same rule shapes the bench harness ("a silent zero-count 'success' is a failure" — every run asserts `distinct_kmers > 0`).
- **Golden baselines are ground truth.** If `golden_*` hash checks fail, the fix is to revert the drift — never to re-capture fixtures. Regeneration is exclusively the ignored `golden_generate` binary (see above).
- **New `tests/*.rs` files are auto-discovered** — no `Cargo.toml` registration needed. Files meant to be shared go under a subdirectory and must be `mod`-included explicitly (see the wiring caveat above).

### Python conventions

- File naming `test_*.py`, classes `Test*`, functions `test_*` (enforced by `pyo3/pyproject.toml`).
- Keep the module-level import guard (`try: import pyrustkmer except ImportError: pytest.skip(...)`) at the top of every new file.
- Every test method carries a one-line docstring describing the behavior under test; failures are asserted with `pytest.raises(ValueError, match="...")` against the exact message.
- Fixtures live in `pyo3/tests/conftest.py` (session-scoped test-database metadata, `tiny_db_path` and friends); helpers in `pyo3/tests/utils.py`.

### Benchmark harness conventions

- Stdlib `unittest` only — no pytest, no conftest, no third-party imports. Module docstrings cite the contract being tested (e.g. the `results.json` schema, BENCH-03) and tests import the production validator (`scripts.bench.bench.validate_schema`) rather than re-implementing it.
- Tests must run from the repo root so `scripts.bench.*` imports resolve.

## Coverage requirements

| Surface | Tool | Threshold |
|---|---|---|
| Python bindings | `pytest-cov`, invoked by the CI `pyo3-pytest` job's pytest command line (`--cov=pyrustkmer --cov-report=term-missing`) | **80%** (`--cov-fail-under=80`) |
| Rust crate | none | No coverage threshold configured |
| Benchmark harness | none | Functional sanity assertion only (`distinct_kmers > 0` per run) |

The Python gate is enforced in CI by the `pyo3-pytest` job's pytest command line; a plain local `pytest` in `pyo3/` runs with verbosity-only default options and needs no `--no-cov` workaround anymore. Coverage measures the `pyrustkmer` module only (`[tool.coverage.run] source = ["pyrustkmer"]`, tests omitted) — in practice that is the maturin-generated `pyrustkmer/__init__.py` shim re-exporting the native extension, so the gate effectively asserts that the freshly built extension imports (a broken build or import yields 0% and red). To explore coverage locally, run `pytest --cov=pyrustkmer --cov-report=html` and open `pyo3/htmlcov/index.html`.

## CI integration

### `ci.yml` — merge gate

Triggered on pull requests and pushes to `dev`/`main`; every gate job fails the PR (no `continue-on-error` anywhere). Matrix is `ubuntu-latest`, `macos-latest`, `windows-latest` where noted:

| Job | Runner | Command |
|---|---|---|
| `fmt` | ubuntu | `cargo fmt --all --check` |
| `clippy-root` | 3-OS matrix | `cargo clippy --all-targets -- -D warnings` |
| `test-root` | 3-OS matrix | `cargo test` |
| `pyo3-build` | 3-OS matrix | `cargo clippy --all-targets -- -D warnings` (in `pyo3/`), then `maturin build`; wheels uploaded as artifacts |

Note what CI does **not** run: the pytest suites (`pyo3/tests/`, the cross-validation trees) and `scripts/bench/tests/` are local-only; CI covers the Rust suite plus the benchmark gate below.

### `benchmark.yml` — performance regression gate

Triggered on the same events; a 2-flavor matrix (ubuntu → `linux`, macos → `darwin`), 45-minute timeout:

1. `cargo build --release`
2. `python3 scripts/bench/bench.py --mode synthetic --out results.json` (whole-pipeline wall time and peak RSS of the release binary, OS rusage accounting)
3. Upload `results.json` as an artifact
4. Gate: `python3 scripts/bench/compare.py --baseline scripts/bench/baselines/bench_baseline.<flavor>.json --current results.json --wall-threshold 0.25 --rss-threshold 0.15 --wall-advisory`

Exit codes carry the verdict: 0 within thresholds, 1 regression (the PR fails), 2 invalid input. Peak RSS is the hard gate at 15%; wall-clock is advisory (macOS wall times vary too much run-to-run for a committed baseline). Committed baselines: `scripts/bench/baselines/bench_baseline.{linux,darwin}.json`.

## Fixtures and test data

- **`tests/fixtures/`** — 12 golden `.rkdb` files (k21/k32/k64 × canonical/non-canonical × sorted/unsorted) with `golden_manifest.sha256`, plus `legacy_v2_offset42.rkdb`, FASTA inputs (`ambiguous_test.fasta`, `k33/k48/k64_test.fasta`), and the `parallel_count_baseline` directory. Ground truth — see the golden-baselines rule above.
- **`test_data/`** (repo root) — shared datasets: `databases/*.rkdb` (`tiny`/`small`/`medium`/`large_test.rkdb`, merged outputs), `sequences/`, `kmers/`, and `generate_test_data.py` to regenerate them.
- **pyo3 fixture caveat** — `pyo3/tests/conftest.py` resolves its session fixtures to `<repo>/python/tests/test_data`, which does not exist in the repository; tests depending on `tiny_db_path`-style fixtures `pytest.skip` when the file is absent. Point the fixture at `test_data/databases/` (or restore the expected tree) if you need those tests to execute.

## Legacy Python trees

These directories contain pytest infrastructure but currently collect no tests:

- **`tests/007-api-compatibility/`** — `pytest.ini` (`testpaths = tests/007-api-compatibility`, markers incl. `compatibility`), `test_data/small_dataset.fa`, and committed JSON reports under `test_reports/`. The `compatibility_framework/` and `performance_benchmarks/` trees its README describes do not exist yet. Run pattern (when tests are added): `pytest -c tests/007-api-compatibility/pytest.ini` from the repo root.
- **`tests/converted/`** — `pytest.ini` plus a README describing the conversion of legacy root `test*.py` scripts; no `test_*.py` files are present.
- **`tests/performance/test_fuzzy_query_performance.py`** — a pytest-marked performance suite importing `from rustkmer import Database`; no such Python module exists at the repo root, so it is not runnable as-is and belongs to no configured suite.

Treat all three as scaffolding: verify before extending, and prefer `pyo3/tests/` for new binding tests.
