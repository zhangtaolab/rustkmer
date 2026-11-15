<!-- generated-by: gsd-doc-writer -->
# Contributing to rustkmer

Thanks for your interest in improving rustkmer — a high-performance k-mer counting and querying toolkit with two surfaces that share one core library: the `rustkmer` CLI and the `pyrustkmer` Python extension (PyO3). Contributions to either surface, or to the shared core, are welcome. The project is MIT-licensed (see [LICENSE](LICENSE)).

## Prerequisites

- **Rust 1.82+** (stable channel). The MSRV is enforced by `rust-version = "1.82"` in both `Cargo.toml` files. Provides `cargo`, `rustfmt`, and `clippy`; CI runs the clippy jobs on Rust 1.82.0 and the remaining Rust jobs on the stable toolchain.
- **Python 3.11+** with `pip` and `venv` — only needed for the `pyrustkmer` bindings (`pyo3/pyproject.toml` declares `requires-python = ">=3.11"`; CI uses Python 3.11).
- **maturin** (`>=1.0,<2.0`) — build backend for the Python wheel.
- Optional: [pre-commit](https://pre-commit.com/) for the repository hook suite (`.pre-commit-config.yaml`).

## Development setup

```bash
git clone https://github.com/zhangtaolab/rustkmer.git
cd rustkmer
cargo build
```

For work on the Python bindings, build the extension into a virtual environment and run the pytest suite from `pyo3/`:

```bash
cd pyo3
python3 -m venv .venv
source .venv/bin/activate
pip install 'maturin>=1.0,<2.0' pytest pytest-cov numpy
maturin develop --release
pytest
```

`maturin develop` installs into the active virtualenv. If a conda environment is active, deactivate it or `unset CONDA_PREFIX` first — otherwise maturin targets the conda interpreter instead of the venv.

See [docs/guides/getting-started.md](docs/guides/getting-started.md) for prerequisites and first-run instructions, [docs/guides/development.md](docs/guides/development.md) for the full local-development workflow, and [docs/guides/testing.md](docs/guides/testing.md) for the test layout and conventions.

## Build and test commands

These are the gates run by the `CI` workflow (`.github/workflows/ci.yml`), triggered on pull requests and pushes to `dev` and `main`. The formatting job runs on Ubuntu only; every other job runs on Ubuntu, macOS, and Windows. Run them locally before opening a PR:

| Command | Description |
| --- | --- |
| `cargo fmt --all --check` | Verify default `rustfmt` formatting (no `rustfmt.toml` overrides); Ubuntu, stable toolchain |
| `cargo clippy --locked --all-targets -- -D warnings` | Root crate must be clippy-clean; warnings are errors; Rust 1.82.0, all three OSes |
| `cargo test --locked` | Rust unit and integration tests (`src/` modules, `tests/`); stable toolchain, all three OSes |
| `cd pyo3 && cargo clippy --locked --all-targets -- -D warnings` | Bindings crate must be clippy-clean; Rust 1.82.0, all three OSes |
| `cd pyo3 && maturin build` | The `pyrustkmer` sdist and wheel must build; all three OSes |
| `cd pyo3 && pytest tests/ --cov=pyrustkmer --cov-report=term-missing --cov-fail-under=80` | `pyo3-pytest` job: Python binding tests with the 80% coverage gate; Python 3.11, all three OSes |

CI runs the Python test suite: the `pyo3-pytest` job on all three operating systems builds the wheel (`maturin build`), installs it, and runs `pytest tests/ --cov=pyrustkmer --cov-report=term-missing --cov-fail-under=80` from `pyo3/` — the 80% coverage gate is passed on the command line there and lives only in CI. Local `pytest` in `pyo3/` runs plain with no forced coverage flags: the `pyo3/pyproject.toml` addopts are only `-v`. Running `cd pyo3 && pytest` locally before a PR that touches the bindings is still recommended.

A separate `Benchmark` workflow (`.github/workflows/benchmark.yml`) also runs on every pull request and push to `dev`/`main`, on Linux and macOS. It builds the release binary, runs the harness unit tests (`python3 -m unittest discover -s scripts/bench/tests -t .`), runs the synthetic benchmark (`python3 scripts/bench/bench.py --mode synthetic --out results.json`), and gates in two ways: `scripts/bench/compare.py` compares wall-time and peak RSS against the committed per-platform baselines in `scripts/bench/baselines/` (RSS is the hard axis at 15%; wall-time breaches are advisory under `--wall-advisory`), and `scripts/bench/thread_scaling.py` is a standing gate requiring both the t4 and t16 speedups to reach the default 1.3 (`--min-speedup`). The Python-surface benchmark (`scripts/bench/python_bench.py`) also runs and uploads its results, but has no compare gate yet. Run the same scripts locally after performance-sensitive changes; see [docs/guides/benchmarking.md](docs/guides/benchmarking.md).

No gate step in `ci.yml` or `benchmark.yml` uses `continue-on-error`, `|| true`, or a conditional skip — a failing gate fails the PR.

A third workflow, `Documentation Build and Deploy` (`.github/workflows/docs.yml`), builds the MkDocs site with `mkdocs build -f mkdocs.docs.yml --strict` and deploys it to GitHub Pages from `main` pushes and `v*` tags. It also runs on pull requests targeting `main` (not `dev`) whose diff touches `docs/`, `python/`, `mkdocs.yml`, `mkdocs.docs.yml`, or `.pydocstylerc` — so documentation changes are strict-build-checked at promotion time, and a docs edit that breaks the strict MkDocs build must be fixed before `main` can advance.

## Coding standards

- **Rust formatting and linting**: default `cargo fmt` and `cargo clippy --all-targets -- -D warnings`, both enforced in CI (`fmt` on Ubuntu, clippy on all three operating systems).
- **Rust documentation**: every module starts with a `//!` block and every public item carries `///` docs using the `# Arguments` / `# Returns` / `# Errors` / `# Raises` / `# Examples` section convention. Doctests must compile — they run under `cargo test`.
- **Python style** (for code under `pyo3/`): `black` with line length 88 (target `py311`) and `mypy` with strict settings, both configured in `pyo3/pyproject.toml`; `isort` uses the black profile (`.pre-commit-config.yaml`). None of these run in CI, and the pre-commit black/isort/pydocstyle/docformatter hooks are scoped to a `python/` tree that is not present in this repository, so they do not cover `pyo3/` — run those tools manually against `pyo3/` before submitting. Docstrings follow Google style.
- **Pre-commit hooks** (`pre-commit install`): trailing-whitespace, end-of-file, YAML/JSON/TOML validity, merge-conflict markers, case conflicts, and large-file checks.

## Pull requests

- Target the `dev` branch — it is the working branch and the repository default (`origin/HEAD` points at `origin/dev`). `main` is the promotion branch referenced by the CI and Benchmark gate workflows and by the docs deploy.
- No branch-naming scheme is enforced; choose a descriptive name for your branch.
- Use conventional commit messages: `type(scope): subject` (e.g. `feat(query): ...`, `fix(cli): ...`, `docs: ...`, `test: ...`), one logical change per commit.
- The gates in the table above must pass on Ubuntu, macOS, and Windows, and the `Benchmark` workflow must pass on Linux and macOS, before review.
- Add tests alongside behavior changes: Rust tests next to the code / in `tests/` via `cargo test`, binding tests in `pyo3/tests/` via `pytest`.
- Keep the `.rkdb` on-disk format and the public CLI / Python APIs backward-compatible unless the tradeoff is discussed explicitly in the PR description.
- Version bumps are release-time concerns: root `Cargo.toml`, `pyo3/Cargo.toml`, and `pyo3/pyproject.toml` versions must stay in sync (`scripts/sync_versions.sh`) — don't bump them in feature PRs.

## Reporting issues

Open an issue at https://github.com/zhangtaolab/rustkmer/issues. There are no issue templates yet, so please include:

- The `rustkmer` version (`rustkmer --version`) or `pyrustkmer` version, and whether you used the CLI or the Python API.
- Your operating system and Rust toolchain version.
- Steps to reproduce, the exact command or Python snippet, expected behavior, and actual output (including the full error message).
- For data-dependent problems, a minimal input file or command line that triggers the failure.

## Further reading

- [README](README.md) — feature overview and installation
- [docs/guides/getting-started.md](docs/guides/getting-started.md) — prerequisites, installation, and first run
- [docs/guides/development.md](docs/guides/development.md) — local development workflow
- [docs/architecture/overview.md](docs/architecture/overview.md) — system and component architecture
- [docs/guides/configuration.md](docs/guides/configuration.md) — `.rustkmerrc`, environment variables, and CLI precedence
- [docs/guides/testing.md](docs/guides/testing.md) — test layout, fixtures, and conventions
- [docs/guides/benchmarking.md](docs/guides/benchmarking.md) — benchmark harness, baselines, and gate thresholds
- [INSTALL.md](INSTALL.md) and [USER_GUIDE.md](USER_GUIDE.md) — end-user documentation
