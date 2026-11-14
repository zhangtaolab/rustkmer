<!-- generated-by: gsd-doc-writer -->
# Development Guide

## Overview

rustkmer is developed as two Cargo crates against one shared core: the root crate `rustkmer` (library `rlib` + `rustkmer` CLI binary, built from `Cargo.toml` at the repo root) and the bindings crate in `pyo3/` (`rustkmer-pyo3`, a `cdylib` that ships as the Python module `pyrustkmer`). The bindings crate depends on the root crate by path, so there is no separate install step for the core. Local development is plain Cargo plus a maturin/venv loop for the Python side; CI enforces `rustfmt`, `clippy -D warnings`, `cargo test`, the `pyrustkmer` pytest suite with its 80% coverage gate, wheel builds, and a committed-baseline performance gate on every PR to `dev`/`main`.

## Local setup

### Prerequisites

- **Rust 1.82+ (stable)** toolchain with cargo (rustup is the usual route; no `rust-toolchain.toml` pin). The MSRV is enforced by `rust-version = "1.82"` in both `Cargo.toml` and `pyo3/Cargo.toml`; CI pins Rust 1.82.0 for the clippy jobs and uses stable for the test jobs.
- A working **C/C++ linker** for the native build
- **Python 3.11+** with pip + venv for the bindings (`pyo3/pyproject.toml` sets `requires-python = ">=3.11"`; CI builds with 3.11)
- **maturin** `>=1.0,<2.0` (installed via pip inside the venv below)

### Rust CLI and library only

```bash
git clone https://github.com/zhangtaolab/rustkmer.git
cd rustkmer
cargo build                 # debug binary at target/debug/rustkmer
cargo build --release       # optimized binary at target/release/rustkmer
```

### Python bindings (`pyrustkmer`)

```bash
cd pyo3
python3 -m venv .venv && source .venv/bin/activate
pip install 'maturin>=1.0,<2.0' pytest pytest-cov numpy
maturin develop --release   # builds the extension and installs it into the venv
python -c "from pyrustkmer import PyDatabase; print('pyrustkmer ready')"
```

- Use `maturin develop` (no `--release`) for faster debug-iteration builds. `maturin develop` always installs into the **active** virtualenv (maturin 1.x has no `--python` flag); activate the venv for the interpreter you want, and if conda is active, deactivate it or `unset CONDA_PREFIX` so maturin does not target the conda environment instead.
- `numpy` is a declared runtime dependency of `pyrustkmer` (`pyo3/pyproject.toml`); installing it in the venv as shown above avoids import failures regardless of how the build backend resolves dependencies.
- The `dev` optional-dependency group in `pyo3/pyproject.toml` pins the Python tooling (pytest, pytest-cov, pytest-benchmark, black, flake8, mypy, pyo3-build-config); the `performance`, `docs`, and `jupyter` groups also live there.
- The two crates keep **separate build state**: the root crate builds into `target/`, the bindings crate into `pyo3/target/` (each has its own `Cargo.lock`). The root is not a Cargo workspace, so run build/lint/test/fmt commands from the directory of the crate you are touching.
- `scripts/test_current.sh` and `scripts/test_all_envs.sh` automate the build-wheel → install → validate loop across local Python 3.11/3.12/3.13 environments, but they hardcode the original author's conda paths and still validate via the old `rustkmer_pyo3` import name (the module is now `pyrustkmer`) — fix both before reuse on another machine. (`pyo3/build_with_python.sh` is an older macOS debug-linking helper with the same hardcoded paths and stale import; prefer `maturin develop`.)

No `.env` files or required environment variables exist; see the [configuration guide](configuration.md) for the `.rustkmerrc` file, `RUSTKMER_*` variables, and thread/memory configuration.

## Build commands

| Command | Where | Description |
|---------|-------|-------------|
| `cargo build` | root | Debug build of the `rustkmer` library + CLI binary |
| `cargo build --release` | root | Optimized binary (`target/release/rustkmer`) |
| `cargo fmt --all` | root | Format the root crate with default rustfmt settings (no `rustfmt.toml`); since `pyo3/` is a separate package rather than a workspace member, it is not included — run `cargo fmt` inside `pyo3/` separately |
| `cargo fmt --check` | `pyo3/` | Formatting check for the bindings crate (not run by CI — the `rustfmt` job only checks the root crate) |
| `cargo clippy --all-targets -- -D warnings` | root | Lint gate — warnings are errors (CI runs the same with `--locked`) |
| `cargo test` | root | Rust unit + integration tests; `tests/` has 29 auto-discovered test targets (28 named suites plus the `mod` target that wires shared helper trees), e.g. `merge_routing_tests`, `dense_differential_tests`, `golden_sha256_tests`, `merge_bounded_memory_tests` (CI adds `--locked`) |
| `cargo test --test cjk_check` | root | CJK string-literal gate (see [Code style](#code-style)) |
| `cargo clippy --all-targets -- -D warnings` | `pyo3/` | Lint gate for the bindings crate (CI runs the same with `--locked`) |
| `maturin develop --release` | `pyo3/` | Build and install `pyrustkmer` into the active venv |
| `maturin build` | `pyo3/` | Build the `pyrustkmer` wheel into `pyo3/target/wheels/` (what CI runs and uploads); add `--sdist` to also build a source distribution |
| `pytest` | `pyo3/` | Python tests in `pyo3/tests/` — plain run; `pyo3/pyproject.toml` addopts are only `-v`, and the 80% coverage gate lives in the CI `pyo3-pytest` job |
| `python3 -m unittest discover -s scripts/bench/tests -t .` | root | Unit tests for the benchmark harness (Python stdlib only) |
| `python3 scripts/bench/bench.py --mode synthetic --self-check` | root | ~1-minute benchmark sanity self-check (exact k-mer counts on synthetic input) |
| `python3 scripts/bench/compare.py --baseline ... --current ...` | root | Performance gate comparator (exit 0 within / 1 regression / 2 invalid input) |
| `./scripts/sync_versions.sh` | root | Sync `pyo3/Cargo.toml` and `pyo3/pyproject.toml` versions to the root `Cargo.toml` version (uses BSD `sed -i ''` syntax — adjust on Linux) |

Notes:

- The release profile in `Cargo.toml` is tuned (`lto = true`, `codegen-units = 1`, `panic = "abort"`) — preserve these settings when touching `[profile.release]`.
- **Never benchmark a debug build.** The harness measures the release binary; run `cargo build --release` first (see `scripts/bench/README.md`).
- A typical local gate before opening a PR mirrors CI: `cargo fmt --all --check && cargo clippy --locked --all-targets -- -D warnings && cargo test --locked` at the root, then `cd pyo3 && cargo clippy --locked --all-targets -- -D warnings` (plus `maturin develop --release && pytest` if you touched bindings).

See the [testing guide](testing.md) for the full test layout, per-suite commands, and coverage details.

## Code style

### Rust

- **rustfmt** with default settings (no `rustfmt.toml` or `clippy.toml` exists). Run `cargo fmt --all` locally; CI gates with `cargo fmt --all --check`. The `rustfmt` job runs at the repo root and therefore covers only the root crate — `pyo3/` is a separate package and its formatting is not CI-gated.
- **clippy** must pass with `-D warnings` on both crates, on Ubuntu, macOS, and Windows.
- Edition 2021; standard conventions — fallible library functions return `ProcessingResult<T>` / `Result<T, KmerError>`, CLI entry points use `anyhow::Result`, PyO3 methods return `PyResult<T>`.

### CJK string-literal gate

`tests/cjk_check.rs` parses every `.rs` file in `src/` (excluding `src/cli/`) and `pyo3/src/` (excluding git-tracked dead backup files) with `syn` and fails if **any string literal** contains a CJK code point (Han, Hiragana, Katakana, Hangul). Emoji and Latin are allowed, and comments (including doc comments) are not scanned. In practice: keep user-facing and log strings in `src/` and `pyo3/src/` ASCII/English; run `cargo test --test cjk_check` when adding messages.

### Python

Tooling is configured in `pyo3/pyproject.toml`: **black** (line length 88, py311 target), **mypy** strict mode (`disallow_untyped_defs`, `warn_unreachable`, ...), plus pytest/coverage settings. `ruff check .` is referenced in `AGENTS.md`, but no ruff configuration file is checked into the repository. New Python in `pyo3/` should be fully typed.

### pre-commit

`.pre-commit-config.yaml` installs hygiene hooks (trailing-whitespace [excluding `.md`], end-of-file fixer, YAML/JSON/TOML checks, merge-conflict and case-conflict guards, large-file guard). The black/isort/pydocstyle/docformatter hooks and the local docstring-coverage hook are all scoped to `python/` — a directory that does not exist in this repository (Python code lives in `pyo3/`) — so they match no files. Install with `pre-commit install` if you want the hygiene checks; for binding code, use the `pyo3/pyproject.toml` tool configs directly (black with line length 88, mypy strict).

## Branch conventions

- **`dev` is the working/default branch**: `origin/HEAD` points at `origin/dev`, and [CONTRIBUTING.md](https://github.com/zhangtaolab/rustkmer/blob/dev/CONTRIBUTING.md) says to target PRs at `dev` (`main` receives promoted states). Both `.github/workflows/ci.yml` and `.github/workflows/benchmark.yml` trigger on pull requests and direct pushes to `dev` and `main`; at the time of writing, origin also carries a `0.5` branch and has no `main` branch.
- **No branch-naming scheme is mandated** — CONTRIBUTING.md says to choose a descriptive name. Commit messages should follow Conventional Commits (`type(scope): subject`, e.g. `feat(query): ...`, `docs: ...`, `test: ...`) with one logical change per commit; history follows this style, and no CI step enforces the message format.

## Pull request process

There is no PR template (and no issue templates); the requirements are enforced by CI, not a checklist.

1. **Open the PR against `dev`** (or `main` for release-oriented changes).
2. **The `CI` workflow must be fully green** — every job is a hard gate with no `continue-on-error` or skipped steps (stated in the header comment of `.github/workflows/ci.yml`):
   - `rustfmt`: `cargo fmt --all --check` (Ubuntu).
   - `clippy (root)`: `cargo clippy --locked --all-targets -- -D warnings` on an Ubuntu/macOS/Windows matrix, pinned to Rust 1.82.0.
   - `test (root)`: `cargo test --locked` on the same three-OS matrix using the stable toolchain.
   - `pyo3 clippy + wheel`: `cargo clippy --locked --all-targets -- -D warnings` plus `maturin build` on the three-OS matrix; wheels are uploaded as artifacts.
   - `pyo3 pytest`: builds the wheel, installs it into Python 3.11, and runs `pytest tests/ --cov=pyrustkmer --cov-report=term-missing --cov-fail-under=80` on all three OSes — the 80% coverage gate lives here and only here.
3. **The `Benchmark` workflow also gates the PR** (`.github/workflows/benchmark.yml`, Linux and macOS matrix): it builds the release binary, runs the harness unit tests (`python3 -m unittest discover -s scripts/bench/tests -t .`), runs `python3 scripts/bench/bench.py --mode synthetic --out results.json`, and compares wall-clock and peak RSS against the committed per-platform baseline (`scripts/bench/baselines/bench_baseline.linux.json` / `.darwin.json`) via `scripts/bench/compare.py`. Peak RSS is the hard gate at a 15% threshold; wall-clock uses an advisory 25% threshold (runner noise made a hard wall gate unreliable — see the workflow header). Exit codes: 0 within thresholds, 1 regression, 2 invalid input such as a platform mismatch. The workflow also runs the Python-surface benchmark (artifact only, no gate) and a standing thread-scaling gate (`scripts/bench/thread_scaling.py`), which is green only when both t1→t4 and t1→t16 speedups reach 1.3.
4. **Version bumps stay in sync.** If you change the crate version, run `./scripts/sync_versions.sh` so `pyo3/Cargo.toml` and `pyo3/pyproject.toml` match the root `Cargo.toml` (the CLI version is derived from `CARGO_PKG_VERSION`, never hard-coded).
5. **Keep new string literals CJK-free** in `src/` and `pyo3/src/` so the `cjk_check` gate stays green.

## Further reading

- [CONTRIBUTING.md](https://github.com/zhangtaolab/rustkmer/blob/dev/CONTRIBUTING.md) — contribution workflow, coding standards, and PR expectations
- [Testing guide](testing.md) — test layout, commands, and coverage gates
- [Configuration guide](configuration.md) — `.rustkmerrc`, environment variables, thread/memory configuration
- [Architecture overview](../architecture/overview.md) — component and layering details
- `scripts/bench/README.md` — benchmark harness internals, baseline bootstrapping, and maintainer procedures
