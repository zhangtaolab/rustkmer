---
title: Getting Started
---

<!-- generated-by: gsd-doc-writer -->

# Getting Started

rustkmer is a high-performance k-mer counting and querying toolkit written in Rust. It ships two front ends over one shared core: the `rustkmer` command-line tool (clap) and the `pyrustkmer` Python extension module (PyO3). Both read and write the same custom binary `.rkdb` database format. This guide takes you from a fresh clone to a working k-mer count on either surface.

## Prerequisites

| Requirement | Version | Needed for |
|-------------|---------|------------|
| Rust toolchain | 1.82 or newer, stable channel | CLI and core library |
| C/C++ linker | platform default (`cc` on Unix, MSVC tools on Windows) | compiling native code |
| Python | 3.11 or newer | `pyrustkmer` bindings only |
| pip + venv | bundled with Python | `pyrustkmer` bindings only |
| maturin | `>=1.0,<2.0` | building the `pyrustkmer` wheel/extension |

- The Rust minimum supported version is declared as `rust-version = "1.82"` in both `Cargo.toml` and `pyo3/Cargo.toml`. Nothing else needs to be installed for the CLI: compression support (`.gz`, `.bz2`, `.xz`) comes from the crate's Rust dependencies.
- The Python floor is declared as `requires-python = ">=3.11"` in `pyo3/pyproject.toml`.
- Linux, macOS, and Windows are all exercised by the project CI (`.github/workflows/ci.yml`).

Install Rust with [rustup](https://rustup.rs) if you don't already have it:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
rustc --version   # must report 1.82.0 or newer
```

On macOS, a system linker is required (`xcode-select --install`). On Debian/Ubuntu, install `build-essential`.

## Installation steps

### 1. Clone the repository

```bash
git clone https://github.com/zhangtaolab/rustkmer.git
cd rustkmer
```

### 2. Build the CLI

```bash
cargo build --release
./target/release/rustkmer --version
```

The version should match the crate version (`rustkmer 0.5.0` for this release). The first release build compiles all dependencies, so it takes noticeably longer than subsequent builds.

To put `rustkmer` on your `PATH` instead of calling it by path:

```bash
cargo install --path .
rustkmer --version
```

This installs the binary into Cargo's bin directory (`~/.cargo/bin` by default).

### 3. (Optional) Build the Python extension

The Python bindings live in the separate crate under `pyo3/`. They must be built and installed into an active virtual environment:

```bash
cd pyo3
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install 'maturin>=1.0,<2.0'
maturin develop --release
python -c "from pyrustkmer import PyCounter; print('pyrustkmer ready')"
```

`maturin develop` must be run from `pyo3/` and with the virtual environment activated. The extension declares `numpy>=1.21` as its runtime dependency in `pyo3/pyproject.toml`. Return to the repository root (`cd ..`) before running the examples below.

An install from PyPI is also possible if a release has been published:

```bash
pip install pyrustkmer
```

<!-- VERIFY: PyPI publication of pyrustkmer cannot be confirmed from the repository alone; the package name comes from pyo3/pyproject.toml [project].name -->

## First run

### CLI: count and query the bundled demo data

The repository ships a small compressed rice-genome sample at `examples/data/demo_rice_genome.fa.gz` (about 150 KB), so no download is needed. From the repository root:

```bash
./target/release/rustkmer count -k 21 -i examples/data/demo_rice_genome.fa.gz -o demo_k21.rkdb
```

Expected output (abridged; the elapsed time depends on your machine):

```text
Processing file 1/1: examples/data/demo_rice_genome.fa.gz
  Total k-mers processed: 489171
  Unique k-mers found: 479701
...
Counting completed successfully!
Total k-mers: 489171
Unique k-mers: 479701
Results saved to: demo_k21.rkdb
```

`count` writes a sorted `.rkdb` database by default. Without `-o`, it prints the counting statistics and does not save a database.

Inspect the database and look up a k-mer that exists in the sample:

```bash
./target/release/rustkmer stats demo_k21.rkdb
./target/release/rustkmer query demo_k21.rkdb CTAAACCCTAAACCCTAAACC
```

The query prints one tab-separated `kmer<TAB>count` line:

```text
CTAAACCCTAAACCCTAAACC	9
```

### Python: the same workflow through `pyrustkmer`

With the virtual environment that has `pyrustkmer` installed activated, run this from the repository root:

```python
from pyrustkmer import PyCounter, PyDatabase, LoadMode

counter = PyCounter(21, canonical=True)
counter.add_from_fasta("examples/data/demo_rice_genome.fa.gz")

stats = counter.get_stats()
print(stats.total_kmers, stats.unique_kmers)   # 489171 472563

counter.save_database("demo_k21_py.rkdb")

db = PyDatabase("demo_k21_py.rkdb", LoadMode.Preload)
result = db.query_exact("CTAAACCCTAAACCCTAAACC")
print(result.found, result.count)              # True 9
```

The unique count differs from the CLI example because the Python counter was created with `canonical=True`; pass `-C` to the CLI to count canonical k-mers as well. `LoadMode` accepts `Preload` (fastest queries, builds an in-memory cache), `MemoryMapped` (file-backed access for large databases), or `Lazy` (sorted index for infrequent queries).

## Common setup issues

**`rustkmer: command not found`**

A source build leaves the binary at `target/release/rustkmer`; it is not added to `PATH` automatically. Either call it by path (`./target/release/rustkmer ...`), install it with `cargo install --path .`, or add `~/.cargo/bin` to your `PATH`.

**Cargo reports that the package requires a newer rustc**

The crate's MSRV is 1.82. Update the toolchain and rebuild:

```bash
rustup update stable
rustc --version
```

**`maturin develop` refuses to build when conda and virtualenv are both active**

maturin rejects the build when it sees conflicting environment managers. Keep a single active environment; if a conda base environment is exported alongside a venv, clear the conda variable and retry:

```bash
unset CONDA_PREFIX
cd pyo3
maturin develop --release
```

**Python version below 3.11**

`pyo3/pyproject.toml` sets `requires-python = ">=3.11"`, so pip/maturin will refuse older interpreters. Create the environment with an explicit interpreter:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

**`Error: Either input files (-i) or directory (-d) must be specified`**

`rustkmer count` requires at least one input source. Pass `-i <files>...` or point it at a directory with `-d <dir>`. Note that `-i` and `-d` are mutually exclusive.

**`error: linker 'cc' not found` during the build**

A native toolchain is missing. On macOS run `xcode-select --install`; on Debian/Ubuntu install `build-essential`.

## Next steps

- [First Steps tutorial](../getting-started/first-steps.md) — a longer CLI and Python walkthrough with sample data.
- [Quick Start](../user-guide/quickstart.md) — common counting and querying recipes.
- [CLI reference](../user-guide/cli.md) — every subcommand and flag.
- [Python API reference](../api-reference/overview.md) — `PyCounter`, `PyDatabase`, `PyFuzzyQuery`, `PyPrefixQuery`, and `LoadMode`.
- [Configuration guide](configuration.md) — `.rustkmerrc`, `RUSTKMER_*` environment variables, and thread/memory settings.
- [Development guide](development.md) — repository layout, build scripts, and contribution workflow.
- [Testing guide](testing.md) — how to run the Rust, Python, and benchmark test suites.
- [Architecture overview](../architecture/overview.md) — how the CLI, Python bindings, and shared core fit together.
