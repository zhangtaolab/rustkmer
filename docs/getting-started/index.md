# Getting Started

Welcome to RustKmer! This section will help you get up and running quickly with k-mer counting and genomic analysis.

## Quick Navigation

- **[Installation](installation.md)** - How to install RustKmer on your system
- **[First Steps](first-steps.md)** - Your first k-mer counting and querying operations

## Why RustKmer?

RustKmer delivers world-class performance for genomic analysis:

| Feature | Performance | Benefits |
|---------|-------------|----------|
| **Query Speed** | 3,986,981 queries/sec | Process millions of queries instantly |
| **Memory Usage** | <2MB overhead | Work with massive datasets efficiently |
| **Python Integration** | Native bindings | Seamless bioinformatics workflow integration |
| **Cross-Platform** | Linux, macOS, Windows | Deploy anywhere |

## What You'll Learn

In this section, you'll:

1. **Install** RustKmer using your preferred method
2. **Count** your first k-mers from genomic data
3. **Query** k-mer databases with exact and fuzzy searches
4. **Integrate** RustKmer into your existing workflows

## Before You Begin

- **System Requirements**: Python 3.11+ or Rust 1.80+
- **Data Format**: FASTA/FASTQ files (compressed supported)
- **Memory**: 4GB+ RAM recommended for large genomes
- **Storage**: Additional space for database files

## Choose Your Path

!!! example "New to k-mer counting?"
    Start with the [First Steps](first-steps.md) guide for a complete walkthrough.

!!! example "Integrating into existing workflow?"
    Jump to the [User Guide](../user-guide/) for advanced usage patterns.

!!! example "Need performance optimization?"
    Check the [Performance Tips](../user-guide/performance-tips.md) guide for optimization strategies.

## Ready to Start?

Choose your installation method below and begin your RustKmer journey!

```bash
# Quick test with Python (after installation)
python -c "from pyrustkmer import PyCounter; print('RustKmer ready! 🚀')"
```

Let's get started with [Installation](installation.md)!

## Python Quickstart (pyrustkmer)

The `pyrustkmer` module is the Python entry point to the same Rust core the CLI uses — both read and write the same `.rkdb` database files. The quick test snippet above assumes the module is already installed; here is the shortest path from a fresh clone to a working module.

**Requirements:** Python 3.11 or newer and a Rust 1.80+ toolchain (`pyo3/pyproject.toml` sets `requires-python = ">=3.11"`; the extension is compiled from source with maturin).

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install maturin

# 2. Build and install the extension into the active environment
cd pyo3
maturin develop --release

# 3. Verify the module imports
python -c "from pyrustkmer import PyCounter; print('pyrustkmer ready')"
```

On macOS, the helper script `pyo3/build_with_python.sh` applies the required Python linker flags for you.

Counting k-mers in Python:

```python
from pyrustkmer import PyCounter

counter = PyCounter(21, canonical=True)   # k-mer size, 1-64
counter.add_from_fasta("sample.fa")       # also: add_from_fastq, add_sequence
stats = counter.get_stats()
print(stats.total_kmers, stats.unique_kmers)
counter.save_database("sample_k21.rkdb")  # same .rkdb file the CLI reads
```

For more, see [Installation](installation.md) for all install methods (including virtual environment and uv workflows), [First Steps](first-steps.md) for querying databases from Python, and the [PyO3 binding guide](../guides/pyo3-binding-guide.md) for the full binding API.

## Next Steps

- **[First Steps](first-steps.md)** — counting, querying, and searching k-mer databases, from both the CLI and Python
- **[User Guide](../user-guide/)** — advanced usage patterns and performance tips
- **[Architecture Overview](../architecture/overview.md)** — how the `rustkmer` CLI and `pyrustkmer` module share one Rust core and one `.rkdb` format
- **[Configuration Guide](../guides/configuration.md)** — `.rustkmerrc`, `RUSTKMER_` environment variables, and CLI flag precedence
- **[Benchmarking Guide](../guides/benchmarking.md)** — running the benchmark harness, the parity gate, and the CI regression thresholds
- **[Troubleshooting](troubleshooting.md)** — fixes for common installation and import problems
