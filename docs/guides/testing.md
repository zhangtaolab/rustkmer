<!-- generated-by: gsd-doc-writer -->
# Testing Guide

## Overview

rustkmer has four distinct test surfaces, each with its own runner:

1. **Rust crate tests** (`cargo test`) — unit tests inside `src/` modules, runnable doc examples, and 29 auto-discovered integration-test targets under `tests/` (28 named binaries plus the `mod` target that wires the shared helper trees). Property-based tests use `proptest`.
2. **Python binding tests** (`pyo3/tests/`, pytest) — 204 test methods across 11 `test_*.py` files exercising the `pyrustkmer` extension, with an 80% coverage gate enforced by the CI `pyo3-pytest` job.
3. **Benchmark harness tests** (`scripts/bench/tests/`) — 17 stdlib `unittest` modules with 571 test methods (no pytest, no conftest, no pip installs). CI runs them inside the benchmark workflow.
4. **Cross-validation / legacy Python trees** (`tests/007-api-compatibility/`, `tests/converted/`, `tests/performance/`) — pytest configuration and committed reports exist, but no test modules are currently collected (see [Legacy Python trees](#legacy-python-trees)).

CI enforces the Rust suite, the Python binding suite, and the benchmark harness on every PR and push to `dev`/`main`; only the legacy Python trees are local-only.

## Test framework and setup

### Rust — `cargo test` + proptest

- Framework: cargo's built-in test harness. `cargo test` compiles every `tests/*.rs` file as its own binary, runs `#[cfg(test)]` modules (45 files under `src/` contain them), and runs doc tests.
- Doc tests: runnable examples live in `src/fuzzy/mod.rs` (module-level example) and `src/database/format.rs` (`RKDatabase::from_sorted_kmer_pairs`). The module-level example in `src/lib.rs` is marked `rust,ignore` because it needs a real FASTA file.
- Property-based testing: `proptest` 1.5 (`[dev-dependencies]` in `Cargo.toml`), used by `tests/dense_proptest_tests.rs`, `tests/count_engine_tests.rs`, and `tests/output_differential_matrix_tests.rs`.
- Benchmarks: `criterion` 0.5 is a dev-dependency, but the `[[bench]]` target (`python_cli_comparison`) is commented out in `Cargo.toml`, so `cargo bench` has no active targets. Performance measurement lives in the separate `scripts/bench/` harness — see the [Benchmarking Guide](benchmarking.md).
- No setup beyond a Rust 1.82+ stable toolchain (`rust-version = "1.82"` in both `Cargo.toml` manifests): `cargo test` works from a fresh clone.

### Python bindings — pytest via maturin

- Framework: `pytest>=7.0` with `pytest-cov>=4.0` and `pytest-benchmark>=4.0` (the `dev` extra in `pyo3/pyproject.toml`). Configuration lives in `[tool.pytest.ini_options]`: `testpaths = ["tests"]`, `python_files = ["test_*.py"]`, markers `slow` / `performance` / `integration`.
- Default `addopts` are verbosity-only (`["-v"]`): a plain `pytest` run carries no forced coverage flags. The 80% gate runs in CI on the `pyo3-pytest` job's command line (see [CI integration](#ci-integration)).
- Requires Python 3.11+ (`requires-python = ">=3.11"`) and the native module built and installed into the active environment first:

```bash
cd pyo3
python3.11 -m venv .venv
source .venv/bin/activate
pip install "pytest>=7.0" "pytest-cov>=4.0" numpy "maturin>=1.0,<2.0"
maturin develop --release
```

- CI uses the wheel route instead of `maturin develop` (which requires a virtualenv):

```bash
cd pyo3
maturin build --release
pip install --no-index --find-links target/wheels pyrustkmer
```

- The maintainer scripts `scripts/test_current.sh` and `scripts/test_all_envs.sh` build and install the wheel across local conda environments. They hardcode a `/Users/forrest/miniconda3` path, so they are not portable. Both unset `VIRTUAL_ENV` and `CONDA_PREFIX` before invoking maturin; an active conda environment can otherwise interfere with the build.
- Import guards differ by file: 6 of the 11 test modules start with `try: import pyrustkmer` / `except ImportError: pytest.skip(..., allow_module_level=True)` — the counter (`test_counter.py`, `test_counter_simple.py`, `test_counter_concurrency.py`), database-merge (`test_database_merge.py`), public-API (`test_public_api.py`), and byte-identity (`test_save_database_byte_identity.py`) suites. `test_version.py` deliberately has no guard, so a missing or stale extension fails instead of skipping. `test_pyo3_simple.py` uses the `pyo3_module` fixture in `pyo3/tests/conftest.py` (which skips when the module is unavailable) for its core-class tests while importing `pyrustkmer` directly elsewhere. `test_core.py`, `test_export.py`, and `test_import.py` import `pyrustkmer` directly inside test bodies, so a missing extension surfaces as a failure rather than a clean skip.

### Benchmark harness — stdlib unittest

`scripts/bench/tests/` is deliberately dependency-free ("stdlib unittest only — no pytest, no conftest", per its module docstrings). Python 3.10+ is enough; nothing to install.

### Legacy trees — pytest configuration only

`tests/007-api-compatibility/` and `tests/converted/` each carry a `pytest.ini` and a README, but no `test_*.py` modules. See [Legacy Python trees](#legacy-python-trees) before adding tests there.

## Running tests

### Full Rust suite

```bash
cargo test                 # unit tests + all 29 integration targets + doctests
cargo test --release       # same, against the optimized build (slower to compile)
cargo test --locked        # what CI runs; requires the committed Cargo.lock
```

### Single binary or filtered run

```bash
cargo test --test merge_routing_tests          # one integration binary
cargo test merge                               # name filter across all targets
cargo test --test golden_sha256_tests dense    # filter within one binary
```

### Ignored generators and timing gates

These are `#[ignore]`d and do not run in the default suite:

```bash
# Regenerate the committed golden .rkdb fixtures (writes tests/fixtures/)
cargo test --test golden_generate -- --ignored --nocapture

# Rolling-encoder release-build timing gate
cargo test --release --test kmer_rolling_differential_tests -- --ignored

# One-shot pre-refactor baseline capture; do NOT regenerate the committed JSON
cargo test --test parallel_count_tests -- --ignored --nocapture
```

The `parallel_count_tests` capture is ground truth for the 1-vs-N differential. Regenerating it destroys the reference.

### Python binding tests

Run from `pyo3/` after `maturin develop --release`:

```bash
cd pyo3
pytest                                   # full suite
pytest tests/test_counter.py             # one file
pytest tests/test_counter.py -k invalid  # filtered run
pytest -m "not slow"                     # marker-based deselection
pytest --cov=pyrustkmer --cov-report=html  # optional local coverage report
```

The suite currently has 204 test methods in 11 files; `test_counter.py` (94) and `test_export.py` (41) are the largest. Many database-backed tests skip because of the fixture path issue described in [Fixtures and test data](#fixtures-and-test-data).

### Benchmark harness tests

Run from the repo root (the tests import `scripts.bench.*`, so the root must be on `sys.path`):

```bash
python3 -m unittest scripts.bench.tests.test_time_parser    # quick module
python3 -m unittest scripts.bench.tests.test_schema \
    scripts.bench.tests.test_compare                        # several modules
python3 -m unittest discover -s scripts/bench/tests -t .    # full suite, as CI runs it
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

Use `bench_baseline.linux.json` on Linux. `bench.py --mode synthetic --self-check` is a ~1-minute sanity run that asserts exact k-mer counts. The Python-surface benchmark and the thread-scaling gate can also be run directly:

```bash
python3 scripts/bench/python_bench.py --python python3 --mode synthetic \
  --reads 200000 --reps 2 --out python_bench.json
python3 scripts/bench/thread_scaling.py --mode synthetic --reads 200000 \
  --reps 2 --measure-only --out thread_scaling.json
python3 scripts/bench/thread_scaling.py --current thread_scaling.json
```

## Rust integration-test inventory

One binary per `tests/*.rs` file (verified via `cargo metadata`; 29 targets total):

| Binary (`--test <name>`) | What it covers |
|---|---|
| `cjk_check` | CJK string-literal gate: `syn`-parses `src/` (excluding `src/cli/`) and `pyo3/src/` and fails on Han/Hiragana/Katakana/Hangul in string literals, including macro arguments |
| `consistency_tests` | Entry target for the shared u64/u128 consistency helpers under `tests/consistency/` |
| `count_engine_tests` | Shared `CountEngine` proofs: exact per-window reference maps, statistics, merge bridge, and CLI engine-path vs legacy-path parity |
| `dense_differential_tests` | Fixed-input differential between u64-storage and u128-storage counters |
| `dense_memory_tests` | Storage-width claim asserted against the representation a real `KmerCounter` stores |
| `dense_merge_integration_tests` | End-to-end merge composition gate over dense storage |
| `dense_proptest_tests` | Property-based dense differential over generated inputs |
| `golden_generate` | Ignored one-shot generator of the golden `.rkdb` fixtures — run with `--ignored` |
| `golden_sha256_tests` | `.rkdb` v2 byte-identity guard for the dense write path against the committed SHA-256 manifest |
| `golden_tests` | One hash check per committed golden fixture plus writer cross-consistency |
| `kmer_rolling_differential_tests` | Rolling 2-bit encoder vs the per-window reference encoder (values, order, skipped-window count) |
| `legacy_readback_tests` | Read-back of the legacy `.rkdb` fixture with `data_offset = 42` |
| `merge_bounded_memory_tests` | Streaming-merge output boundedness: RSS growth bounded by the chunk size, not by input size |
| `merge_cleanup_tests` | Temp-shard cleanup on failed or interrupted streaming merges |
| `merge_frontend_validation_tests` | CLI merge front-end validation reads headers only and never materializes inputs |
| `merge_route_parity_tests` | Route parity above the old endianness threshold |
| `merge_routing_tests` | Merge routing and memory-budget admission control, observed through a temp-dir probe |
| `mod` | Wires `tests/{common,integration,property,unit}`; currently runs the shared-helper self-tests in `tests/common/mod.rs` |
| `output_differential_matrix_tests` | Old-vs-new output pipeline and 1-vs-N differential across the k × canonical × threads matrix |
| `output_pipeline_tests` | Output-pipeline contract: golden bytes, strict ascending keys, record/count consistency, thread invariance |
| `parallel_count_tests` | 1-vs-N thread-count differential; contains an ignored one-shot baseline capture |
| `prefix_cache_conservation_tests` | Route-level conservation proofs for the prefix-cache bucket merge |
| `prefix_cache_output_order_tests` | End-to-end output-order and query proofs for the prefix-cache route |
| `rkdb_v2_byte_identity_tests` | `.rkdb` v2 byte identity for the counting output path plus sortedness proven through both query consumers |
| `round_trip_tests` | `.rkdb` write→read round-trip with byte-identical k-mer counts |
| `sorted_pairs_constructor_tests` | Byte contract for `RKDatabase::from_sorted_kmer_pairs` |
| `thread_local_count_tests` | Thread-local accumulation plus checked end-of-file reduction produce exactly the pre-change maps |
| `thread_pool_size_tests` | Live rayon counting-pool observation through independent child CLI processes |
| `window_extract_differential_tests` | Skip-N window extractor differential over k 1–64, canonical modes, case, N positions, and record boundaries |

**Wiring caveat:** files in `tests/` subdirectories are only compiled when a top-level `tests/*.rs` binary includes them (`mod x;` or `#[path = ...]`). Currently `tests/consistency/` is included via `consistency_tests.rs`, and `tests/common/factories.rs` is included either through `mod common;` or directly via `#[path = "common/factories.rs"]` (used by `merge_routing_tests.rs` and `merge_cleanup_tests.rs`). The files `tests/integration/queryx_tests.rs`, `tests/integration/stats_integration.rs`, `tests/unit/stats_tests.rs`, `tests/unit/database/*.rs`, `tests/property/stats_properties.rs`, and `tests/contract/*.rs` are referenced by no binary and **do not run** — wire them into a target before relying on them.

## Writing new tests

### Rust conventions

- **Header comments cite the identifier under test.** Nearly every test binary opens with a `//!` block naming what it verifies and its observation strategy. Most cite a requirement ID (e.g. `OUT-01`, `ENGINE-03`, `PAR-02`); the `golden_*` binaries cite plan/decision IDs (`D-09`, `D-10`, `D-11`, `D-13`) and the prefix-cache binaries cite review IDs (`CR-01`, `CR-02`, `WR-03`). `tests/mod.rs` and `tests/consistency_tests.rs` have descriptive headers only. Match the convention when adding a binary.
- **Shared helpers live in `tests/common/`**, split into `factories.rs` (database/k-mer factories), `memory.rs`, `performance.rs`, and `temp_files.rs`. Include the full module with `mod common;` (compiles its self-tests into your binary), or factories only with `#[path = "common/factories.rs"] mod common;`. The module is `#![allow(dead_code)]` because each binary uses a different subset.
- **Each `tests/*.rs` file is a separate crate.** Small helpers shared between top-level binaries are duplicated rather than imported; only files under `tests/common/` and similar subdirectories can be shared via `mod`.
- **Property tests use `proptest`** — see `tests/dense_proptest_tests.rs` for the strategy + differential pattern.
- **Exactness discipline:** assert exact values, never merely non-empty. The same rule shapes the bench harness ("a silent zero-count 'success' is a failure" — every run asserts `distinct_kmers > 0`).
- **Golden baselines are ground truth.** If `golden_*` hash checks fail, revert the drift — never re-capture fixtures. Regeneration is exclusively the ignored `golden_generate` binary.
- **New `tests/*.rs` files are auto-discovered** — no `Cargo.toml` registration needed. Files meant to be shared go under a subdirectory and must be `mod`-included explicitly (see the wiring caveat above).

### Python conventions

- File naming `test_*.py`, classes `Test*`, functions `test_*` (enforced by `pyo3/pyproject.toml`).
- Prefer the module-level import guard at the top of every new file:

```python
try:
    import pyrustkmer
except ImportError:
    pytest.skip("pyrustkmer module not installed", allow_module_level=True)
```

- `test_version.py` is the deliberate exception: it must fail on a missing or stale extension, never skip.
- Every test method carries a one-line docstring describing the behavior under test; failures are asserted with `pytest.raises(ValueError, match="...")` against the exact message where the API specifies one.
- Fixtures live in `pyo3/tests/conftest.py` (session-scoped test-database metadata, `tiny_db_path` and friends); helpers live in `pyo3/tests/utils.py`.

### Benchmark harness conventions

- Stdlib `unittest` only — no pytest, no conftest, no third-party imports. Module docstrings cite the contract being tested (e.g. the `results.json` schema), and tests import the production validator (`scripts.bench.bench.validate_schema`) rather than re-implementing it.
- Tests must run from the repo root so `scripts.bench.*` imports resolve.

## Coverage requirements

| Surface | Tool | Threshold |
|---|---|---|
| Python bindings | `pytest-cov`, invoked by the CI `pyo3-pytest` job (`--cov=pyrustkmer --cov-report=term-missing`) | **80%** (`--cov-fail-under=80`) |
| Rust crate | none | No coverage threshold configured |
| Benchmark harness | none | Functional sanity assertion only (`distinct_kmers > 0` per run) |

The Python gate is enforced only in CI; a plain local `pytest` in `pyo3/` runs with verbosity-only default options. Coverage measures the `pyrustkmer` module only (`[tool.coverage.run] source = ["pyrustkmer"]`, tests omitted) — in practice that is the maturin-generated `pyrustkmer/__init__.py` shim re-exporting the native extension, so the gate effectively asserts that the freshly built extension imports (a broken build or import yields 0% and red). To explore coverage locally, run `pytest --cov=pyrustkmer --cov-report=html` and open `pyo3/htmlcov/index.html`.

## CI integration

### `ci.yml` — merge gate

Triggered on pull requests and pushes to `dev`/`main`; every gate job fails the PR (there is no `continue-on-error` anywhere). Matrix is `ubuntu-latest`, `macos-latest`, `windows-latest` where noted:

| Job | Runner | Command |
|---|---|---|
| `fmt` | ubuntu | `cargo fmt --all --check` |
| `clippy-root` | 3-OS matrix, Rust 1.82.0 | `cargo clippy --locked --all-targets -- -D warnings` |
| `test-root` | 3-OS matrix, stable | `cargo test --locked` |
| `pyo3-build` | 3-OS matrix, Rust 1.82.0, Python 3.11 | `cargo clippy --locked --all-targets -- -D warnings` in `pyo3/`, then `maturin build`; wheels uploaded as artifacts |
| `pyo3-pytest` | 3-OS matrix, stable, Python 3.11 | `maturin build`, install the wheel with `pip install --no-index --find-links ...`, then `pytest tests/ --cov=pyrustkmer --cov-report=term-missing --cov-fail-under=80` |

The `pyo3-pytest` job covers the Python binding suite in CI. The legacy Python trees are not part of this workflow.

### `benchmark.yml` — performance regression gate

Triggered on the same events; a 2-flavor matrix (ubuntu → `linux`, macos → `darwin`), 45-minute timeout. Steps per leg:

1. `cargo build --locked --release`
2. `python3 -m unittest discover -s scripts/bench/tests -t .` (harness unit tests)
3. `python3 scripts/bench/bench.py --mode synthetic --out results.json` (whole-pipeline wall time and peak RSS of the release binary, OS rusage accounting)
4. Upload `results.json` as an artifact before the gate step, so a missing-baseline exit 2 still leaves evidence
5. Gate: `python3 scripts/bench/compare.py --baseline scripts/bench/baselines/bench_baseline.<flavor>.json --current results.json --wall-threshold 0.25 --rss-threshold 0.15 --wall-advisory`
6. Build and install the PyO3 wheel, then run `python3 scripts/bench/python_bench.py --python python3 --mode synthetic --reads 200000 --reps 2 --out python_bench.json` (artifact only; no compare gate because no CI-class Python baseline exists yet)
7. Measure thread scaling with `scripts/bench/thread_scaling.py --measure-only`, upload the evidence, then run `thread_scaling.py --current thread_scaling.json` as the standing gate (fails if t4/t16 speedups miss 1.3x)

Exit codes carry the verdict: 0 within thresholds, 1 regression (the PR fails), 2 invalid input. Peak RSS is the hard gate at 15%; wall-clock is advisory (macOS wall times vary too much run-to-run for a committed baseline). Committed baselines: `scripts/bench/baselines/bench_baseline.{linux,darwin}.json`.

### `docs.yml` — documentation build

Triggered by pushes to `main`, version tags, PRs touching `docs/**`, `python/**`, `mkdocs.yml`, `mkdocs.docs.yml`, or `.pydocstylerc`, and manual `workflow_dispatch`. The `build-docs` job builds the MkDocs site with `--strict` and deploys to GitHub Pages on `main`/tags; a dependent `test-docs` job checks key pages and a clean `--strict` rebuild. It does not run the test suites.

### What CI does not run

- The legacy Python trees (`tests/007-api-compatibility/`, `tests/converted/`, `tests/performance/`).
- The maintainer-only conda scripts in `scripts/` (`test_current.sh`, `test_all_envs.sh`, `test_pyo3_version.sh`).
- Full human-scale benchmark data; CI uses the synthetic input, and the jellyfish parity arm is dev-host only.

## Fixtures and test data

- **`tests/fixtures/`** — 12 golden `.rkdb` files (k21/k32/k64 × canonical/non-canonical × sorted/unsorted) with `golden_manifest.sha256` (12 entries), plus `legacy_v2_offset42.rkdb`, FASTA inputs (`ambiguous_test.fasta`, `k33/k48/k64_test.fasta`), and the `parallel_count_baseline/` directory (6 JSON baselines). `tests/fixtures/kmers/` holds JSON k-mer fixtures intended for Python API tests, but no test or script currently references them — only the directory README describes them. Treat everything here as read-only ground truth — see the golden-baselines rule above.
- **`test_data/`** (repo root) — shared datasets: `databases/*.rkdb` (`tiny_test`/`small_test`/`medium_test`/`large_test`, `small_test_k33_C`, prefix/merge/perf databases), `sequences/`, `kmers/`, `example_usage.py`, `generate_test_data.py` to regenerate them, `verify_git_tracking.py`, and a README.
- **pyo3 fixture caveat** — `pyo3/tests/conftest.py` resolves its session fixtures to `<repo>/python/tests/test_data`, which does not exist in the repository. Tests depending on `tiny_db_path`-style fixtures `pytest.skip` when the file is absent. Point the fixture at `test_data/databases/` (which contains the expected file names) if you need those tests to execute.

## Legacy Python trees

These directories contain pytest infrastructure but currently collect no tests:

- **`tests/007-api-compatibility/`** — `pytest.ini` (`testpaths = tests/007-api-compatibility`, markers including `compatibility`), `test_data/small_dataset.fa`, and committed JSON reports under `test_reports/`. The `compatibility_framework/` and `performance_benchmarks/` trees its README describes do not exist. Run pattern (when tests are added): `pytest -c tests/007-api-compatibility/pytest.ini` from the repo root.
- **`tests/converted/`** — `pytest.ini` plus a README describing the conversion of legacy root `test*.py` scripts; no `test_*.py` files are present.
- **`tests/performance/test_fuzzy_query_performance.py`** — a pytest-based performance suite importing `from rustkmer import Database` (no `pytest.mark` markers; pytest is used only for `pytest.skip`); no such Python module exists at the repo root, so it is not runnable as-is and belongs to no configured suite. Its expected database path (`tests/test_data/tiny_test.rkdb`) is also absent.

Treat all three as scaffolding: verify before extending, and prefer `pyo3/tests/` for new binding tests.
