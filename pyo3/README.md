# RustKmer PyO3 Python Bindings

High-performance Python bindings for the RustKmer k-mer counting and querying library using PyO3.

## Features

- **High Performance**: Native Rust extensions with minimal Python overhead
- **Memory Efficient**: Optimized memory usage for large genomic datasets
- **Complete API**: Full access to k-mer counting, database querying, and fuzzy matching
- **Pythonic Interface**: Clean, intuitive Python API design
- **Compatible**: Works with Python 3.11+

## Installation

```bash
# Install from source
maturin develop --release

# Or with pip (when published)
pip install rustkmer-pyo3
```

## Quick Start

```python
import rustkmer_pyo3

# Create a k-mer counter
counter = rustkmer_pyo3.PyKmerCounter(k=21, canonical=True)

# Add sequences to count k-mers
counter.add_sequence("ATCGATCGATCGATCG")

# Get statistics
stats = counter.get_stats()
print(f"Counted {stats.unique_kmers} unique k-mers")

# Load and query a database
db = rustkmer_pyo3.PyDatabase("genome.rkdb")
result = db.query("ATCGATCGATCGATCG")
print(f"K-mer count: {result.count}")

# Perform fuzzy queries
fuzzy = rustkmer_pyo3.PyFuzzyQuery(db)
result = fuzzy.fuzzy_query("ATNNGTA", max_mutations=2)
print(f"Found {result.total_matches} fuzzy matches")
```

## API Reference

### PyKmerCounter

High-performance k-mer counter for counting k-mers in DNA sequences.

### PyDatabase

Efficient database querying for k-mer count lookups.

### PyFuzzyQuery

Advanced fuzzy matching with wildcard and mutation support.

## Requirements

- Python 3.11+
- Rust toolchain
- maturin build tool

## License

MIT License

