<!-- generated-by: gsd-doc-writer -->
# Development Guide

## Overview

rustkmer is developed as two Cargo crates against one shared core: the root crate `rustkmer` (library `rlib` + `rustkmer` CLI binary, built from `Cargo.toml` at the repo root) and the bindings crate in `pyo3/` (`rustkmer-pyo3`, a `cdylib` that ships as the Python module `pyrustkmer`). The bindings crate depends on the root crate by path, so there is no separate install step for the core. Local development is plain Cargo plus a maturin/venv loop for the Python side; CI enforces `rustfmt`, `clippy -D warnings`, `cargo test`, wheel builds, and a committed-baseline performance gate on every PR to `dev`/`main`.

## Local setup

### Prerequisites

- **Rust 1.80+ stable** toolchain with cargo (rustup is the usual route; no `rust-toolchain.toml` pin — CI installs `dtolnay/rust-toolchain@stable`)
- A working **C/C++ linker** for the native build
- **Python 3.11+** with pip + venv for the bindings (`pyo3/pyproject.toml` sets `requires-python = ">=3.11"`; CI builds with 3.11)
- **maturin** `>=1.0,<2.0` (installed via pip inside the venv below)

### Rust CLI and library only

```bash
git clone https://github.com/rustkmer/rustkmer.git
cd rustkmer
cargo build                 # debug binary at target/debug/rustkmer
cargo build --release       # optimized binary at target/release/rustkmer
```

### Python bindings (`pyrustkmer`)

```bash
cd pyo3
python3 -m venv .venv && source .venv/bin/activate
pip install 'maturin>=1.0,<2.0' pytest pytest-cov
maturin develop --release   # builds the extension and installs it into the venv
python -c "from pyrustkmer import PyDatabase; print('pyrustkmer ready')"
```

- Use `maturin develop` (no `--release`) for faster debug-iteration builds, and `maturin develop --python python3.11` to target a specific interpreter.
- The `dev` optional-dependency group in `pyo3/pyproject.toml` pins the Python tooling (pytest, pytest-cov, pytest-benchmark, black, flake8, mypy, pyo3-build-config); the `performance`, `docs`, and `jupyter` groups also live there.
- The two crates keep **separate build state**: the root crate builds into `target/`, the bindings crate into `pyo3/target/` (each has its own `Cargo.lock`). Run build/lint/test commands from the directory of the crate you are touching.
- `scripts/test_current.sh` and `scripts/test_all_envs.sh` automate the build-wheel → install → validate loop across local Python 3.11/3.12/3.13 environments, but they hardcode the original author's conda paths — adjust them before reuse on another machine. (`pyo3/build_with_python.sh` is similar: a macOS debug-linking helper with hardcoded local paths; prefer `maturin develop`.)

No `.env` files or required environment variables exist; see the [configuration guide](configuration.md) for the `.rustkmerrc` file, `RUSTKMER_*` variables, and thread/memory configuration.

## Build commands

| Command | Where | Description |
|---------|-------|-------------|
| `cargo build` | root | Debug build of the `rustkmer` library + CLI binary |
| `cargo build --release` | root | Optimized binary (`target/release/rustkmer`) |
| `cargo fmt --all` | root | Format all crates with default rustfmt settings (no `rustfmt.toml`) |
| `cargo clippy --all-targets -- -D warnings` | root | Lint gate — warnings are errors (matches CI) |
| `cargo test` | root | Rust unit + integration tests (`tests/` holds roughly 20 test binaries, e.g. `merge_routing_tests`, `dense_differential_tests`, `golden_sha256_tests`, `merge_bounded_memory_tests`) |
| `cargo test --test cjk_check` | root | CJK string-literal gate (see [Code style](#code-style)) |
| `cargo clippy --all-targets -- -D warnings` | `pyo3/` | Lint gate for the bindings crate |
| `maturin develop --release` | `pyo3/` | Build and install `pyrustkmer` into the active venv |
| `maturin build` | `pyo3/` | Build sdist + wheel into `pyo3/target/wheels/` (what CI runs and uploads) |
| `pytest` | `pyo3/` | Python tests in `pyo3/tests/` — plain run, no forced flags (`--no-cov` workaround obsolete); the 80% coverage gate lives in the CI `pyo3-pytest` job |
| `python3 -m unittest discover -s scripts/bench/tests -t .` | root | Unit tests for the benchmark harness (Python stdlib only) |
| `python3 scripts/bench/bench.py --mode synthetic --self-check` | root | ~1-minute benchmark sanity self-check (exact k-mer counts on synthetic input) |
| `python3 scripts/bench/compare.py --baseline ... --current ...` | root | Performance gate comparator (exit 0 within / 1 regression / 2 invalid input) |
| `./scripts/sync_versions.sh` | root | Align the version across both `Cargo.toml` files and `pyo3/pyproject.toml` |

Notes:

- The release profile in `Cargo.toml` is tuned (`lto = true`, `codegen-units = 1`, `panic = "abort"`) — preserve these settings when touching `[profile.release]`.
- **Never benchmark a debug build.** The harness measures the release binary; run `cargo build --release` first (see `scripts/bench/README.md`).
- A typical local gate before opening a PR mirrors CI: `cargo fmt --all && cargo clippy --all-targets -- -D warnings && cargo test` at the root, then `cd pyo3 && cargo clippy --all-targets -- -D warnings` (plus `maturin develop --release && pytest` if you touched bindings).

See the [testing guide](testing.md) for the full test layout, per-suite commands, and coverage details.

## Code style

### Rust

- **rustfmt** with default settings (no `rustfmt.toml` or `clippy.toml` exists). Run `cargo fmt --all` locally; CI gates with `cargo fmt --all --check`.
- **clippy** must pass with `-D warnings` on both crates, on Ubuntu, macOS, and Windows.
- Edition 2021; standard conventions — fallible library functions return `ProcessingResult<T>` / `Result<T, KmerError>`, CLI entry points use `anyhow::Result`, PyO3 methods return `PyResult<T>`.

### CJK string-literal gate

`tests/cjk_check.rs` parses every `.rs` file in `src/` (excluding `src/cli/`) and `pyo3/src/` (excluding git-tracked dead backup files) with `syn` and fails if **any string literal** contains a CJK code point (Han, Hiragana, Katakana, Hangul). Emoji and Latin are allowed, and comments are not scanned. In practice: keep user-facing and log strings in `src/` and `pyo3/src/` ASCII/English; run `cargo test --test cjk_check` when adding messages.

### Python

Tooling is configured in `pyo3/pyproject.toml`: **black** (line length 88, py311 target), **mypy** strict mode (`disallow_untyped_defs`, `warn_unreachable`, ...), plus pytest/coverage settings. `ruff` is also used for linting (`ruff check .`). New Python in `pyo3/` should be fully typed.

### pre-commit

`.pre-commit-config.yaml` installs hygiene hooks (trailing-whitespace [excluding `.md`], end-of-file fixer, YAML/JSON/TOML checks, large-file guard) plus black/isort/pydocstyle/docformatter scoped to `python/`. Install with `pre-commit install` if you work in that tree.

## Branch conventions

- The protected branches are **`dev` and `main`** — both `ci.yml` and `benchmark.yml` gate pull requests and direct pushes to them. Day-to-day work lands on `dev` via PR.
- No branch-naming scheme is documented ([CONTRIBUTING.md](../../CONTRIBUTING.md) exists at the repo root, but it does not define a branch-naming scheme; no PR template exists). Commit messages in history follow Conventional-Commits-style prefixes such as `docs:` and `type(scope):`; matching that style is customary, not enforced.

## Pull request process

There is no PR template; the requirements are enforced by CI, not a checklist.

1. **Open the PR against `dev`** (or `main` for release-oriented changes).
2. **The `CI` workflow must be fully green** — every job is a hard gate with no `continue-on-error` or skipped steps (stated in the header comment of `.github/workflows/ci.yml`):
   - `rustfmt`: `cargo fmt --all --check` (Ubuntu).
   - `clippy (root)` and `test (root)`: `cargo clippy --all-targets -- -D warnings` and `cargo test` on an Ubuntu/macOS/Windows matrix.
   - `pyo3 clippy + wheel`: clippy with `-D warnings` plus `maturin build` (sdist + wheel) on the same three-OS matrix; wheels are uploaded as artifacts.
3. **The `Benchmark` workflow also gates the PR** (`.github/workflows/benchmark.yml`): it builds the release binary, runs the synthetic benchmark, and compares wall-clock and peak RSS against the committed per-platform baseline (`scripts/bench/baselines/bench_baseline.linux.json` / `.darwin.json`) via `scripts/bench/compare.py`. Peak RSS is the hard gate at a 15% threshold; wall-clock uses a 25% advisory threshold (runner noise made a hard wall gate unreliable — see the workflow header). Exit codes: 0 within thresholds, 1 regression, 2 invalid input such as a platform mismatch.
4. **Version bumps stay in sync.** If you change the crate version, run `./scripts/sync_versions.sh` so the root `Cargo.toml`, `pyo3/Cargo.toml`, and `pyo3/pyproject.toml` all agree (the CLI version is derived from `CARGO_PKG_VERSION`, never hard-coded).
5. **Keep new string literals CJK-free** in `src/` and `pyo3/src/` so the `cjk_check` gate stays green.

## Further reading

- [Testing guide](testing.md) — test layout, commands, and coverage gates
- [Configuration guide](configuration.md) — `.rustkmerrc`, environment variables, thread/memory configuration
- [Architecture overview](../architecture/overview.md) — component and layering details
- `scripts/bench/README.md` — benchmark harness internals, baseline bootstrapping, and maintainer procedures
