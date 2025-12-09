# RustKmer Python Bindings

High-performance k-mer counting, database queries, and fuzzy search for genomic data analysis.

## Installation

### From PyPI (Recommended)

```bash
pip install rustkmer
```

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/rustkmer.git
cd rustkmer

# Install build dependencies
pip install maturin

# Build and install
maturin develop --release
```

## Quick Start

```python
from rustkmer import KmerCounter, Database, FuzzyQuery

# Count k-mers from a FASTA file
counter = KmerCounter(k=21, canonical=True, threads=4)
counts = counter.count_file("genome.fa")

# Save to database
db = counter.save_to_database("genome.rkdb")

# Query the database
db = Database()
db.load("genome.rkdb")
result = db.query("ATCGATCGATCGATCGATCGAT")
if result.found:
    print(f"k-mer count: {result.count}")

# Fuzzy search
fuzzy = FuzzyQuery(db, max_distance=1)
results = fuzzy.search("A*TG*C")
print(f"Found {results.total_matches} matches")
```

## Features

- **High Performance**: Rust-powered implementation with Python bindings
- **Memory Efficient**: Memory-mapped database access for large files
- **Parallel Processing**: Multi-threaded operations with automatic concurrency
- **CLI Compatible**: 100% functional parity with rustkmer CLI
- **Rich API**: Comprehensive Python interface with type hints
- **Error Handling**: Detailed error messages with Chinese translations

## Requirements

- Python 3.10 or higher
- Rust 1.70+ (when building from source)

## Documentation

Full documentation is available at: https://rustkmer.readthedocs.io/

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please see the [contributing guidelines](CONTRIBUTING.md) for details.