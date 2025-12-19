# RustKmer PyO3 Python Bindings

High-performance Python bindings for the RustKmer k-mer counting and querying library using PyO3.

## Features

- **High Performance**: Native Rust extensions with minimal Python overhead
- **Memory Efficient**: Optimized memory usage for large genomic datasets
- **Flexible Loading**: Choose between Preload, MemoryMapped, or Lazy loading modes
- **Complete API**: Full access to k-mer counting, database querying, and fuzzy matching
- **Pythonic Interface**: Clean, intuitive Python API design
- **Compatible**: Works with Python 3.11+

## Database Loading Modes

The `PyDatabase` class supports three loading modes to balance performance and memory usage:

### LoadMode.Preload
- **Description**: Loads all k-mers into memory HashMap for fastest queries
- **Performance**: Fastest query speed (sub-millisecond)
- **Memory Usage**: High (stores all k-mers in memory)
- **Best For**: Applications with frequent queries on the same database

### LoadMode.MemoryMapped
- **Description**: Uses memory-mapped file access for balanced performance
- **Performance**: Good query speed with moderate memory usage
- **Memory Usage**: Low to Moderate (OS manages caching)
- **Best For**: Large databases where memory is limited

### LoadMode.Lazy
- **Description**: Loads k-mers on-demand using binary search
- **Performance**: Slower queries but no memory overhead for unused k-mers
- **Memory Usage**: Very Low (only stores sorted index)
- **Best For**: Applications with infrequent queries or very large databases

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

# Load database with different modes
# Preload: Fastest queries, highest memory usage
db_preload = rustkmer_pyo3.PyDatabase("genome.rkdb", rustkmer_pyo3.LoadMode.Preload)

# Lazy: Lowest memory usage, binary search
db_lazy = rustkmer_pyo3.PyDatabase("genome.rkdb", rustkmer_pyo3.LoadMode.Lazy)

# Query k-mers
result = db_preload.query("ATCGATCGATCGATCG")
print(f"K-mer count: {result.count}")

# Check memory usage
memory_info = db_preload.get_memory_usage()
print(f"Memory usage: {memory_info}")

# Perform fuzzy queries
fuzzy = rustkmer_pyo3.PyFuzzyQuery(db_preload)
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

