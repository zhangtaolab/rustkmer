<!-- generated-by: gsd-doc-writer -->
# Python API

The rustkmer Python API provides a powerful interface for k-mer counting, database operations, and fuzzy searching. The bindings ship as the native extension module `pyrustkmer`, built with PyO3 on top of the same Rust core that powers the `rustkmer` CLI — both surfaces read and write the same `.rkdb` binary database format.

## Overview

RustKmer's Python bindings offer high-performance k-mer operations with a simple, Pythonic interface. The API is built using PyO3 to provide seamless integration between Rust's performance and Python's ecosystem.

### Key Features

- **High Performance**: Rust-based implementation with multi-threaded counting (Rayon, GIL released during file processing)
- **Memory Efficient**: Three database load modes, including memory-mapped-style direct I/O for large datasets
- **Rich Functionality**: Exact/batch/prefix/hybrid queries, fuzzy matching, merging, and export to TSV/CSV/JSON
- **Python Integration**: Works seamlessly with pandas, NumPy, BioPython, and more
- **Compressed Input**: FASTA/FASTQ readers accept plain, `.gz`, `.bz2`, and `.xz` files

## Quick Start

### Installation

```bash
pip install pyrustkmer
```

See [Getting Started](getting-started.md) for building from source with `maturin` (Python >= 3.11 required).

### Basic Usage

```python
from pyrustkmer import PyCounter, PyDatabase, PyFuzzyQuery, LoadMode

# 1. Count k-mers and build a database
counter = PyCounter(31, canonical=True)
counter.add_from_fasta("sequences.fasta")
counter.save_database("output.rkdb")

# 2. Query the database
db = PyDatabase("output.rkdb", LoadMode.Preload)
result = db.query_exact("ATCGATCGATCGATCGATCGATCGATCGATC")
print(f"Found: {result.found}, count: {result.count}")

stats = db.get_stats()
print(f"Unique k-mers: {stats.unique_kmers:,}")

# 3. Fuzzy query: allow up to 2 mismatches
fuzzy = PyFuzzyQuery(db)
fuzzy_result = fuzzy.query_fuzzy("ATCGATCGATCGATCGATCGATCGATCGATC", max_mutations=2)
print(f"Found {fuzzy_result.total_matches} similar k-mers")
```

## API Components

### Core Classes

| Component | Description | Key Methods / Attributes |
|-----------|-------------|--------------------------|
| [`PyDatabase`](../database.md) | K-mer database operations | `query_exact()`, `query_exact_batch()`, `query_prefix()`, `get_stats()`, `dump()`, `export_to_csv()`, `merge()` |
| [`PyCounter`](../kmercounter.md) | K-mer counting and database creation | `add_from_fasta()`, `add_from_fastq()`, `get_stats()`, `get_count()`, `save_database()` |
| [`PyQueryResult`](../query.md) | Exact query results | `kmer`, `count`, `found`, `to_dict()` |
| [`PyFuzzyQuery`](../fuzzyquery.md) | Fuzzy query engine | `query_fuzzy()`, `query_fuzzy_position()` |
| [`PyFuzzyResult`](../fuzzyquery.md) | Fuzzy query results | `matches`, `exact_match`, `total_matches`, `get_top_matches()` |
| [`PyDatabaseStats`](../stats.md) | Database statistics | `kmer_size`, `total_kmers`, `unique_kmers`, `file_size`, `is_sorted`, `canonical` |

### Exceptions

The bindings raise standard Python built-in exceptions — `FileNotFoundError` for missing database files, `ValueError` for invalid arguments (k-mer length, invalid characters, out-of-range k), `RuntimeError` for failed query/merge operations, and `PermissionError` for unwritable export paths. A single library error class, `pyrustkmer.RustKmerError` (with `message` and `error_type` attributes), is also exported from the module.

## Navigation

- [**Getting Started**](getting-started.md) - Installation, setup, and first steps
- [**API Overview**](../overview.md) - API reference overview
- [**Database**](../database.md) - `PyDatabase` operations and management
- [**K-mer Counter**](../kmercounter.md) - `PyCounter` counting and database creation
- [**Query Results**](../query.md) - `PyQueryResult` handling
- [**Fuzzy Queries**](../fuzzyquery.md) - `PyFuzzyQuery` and fuzzy searching
- [**Database Stats**](../stats.md) - `PyDatabaseStats` and analysis
- [**Examples**](examples.md) - Comprehensive examples and use cases

## Usage Patterns

### Batch Operations

For multiple exact queries, use `query_exact_batch` instead of a Python loop:

```python
kmer_list = [
    "ATCGATCGATCGATCGATCGATCGATCGATC",
    "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
]

batch = db.query_exact_batch(kmer_list)

for kmer, result in batch.items():
    print(f"{kmer}: {'found' if result.found else 'missing'} (count: {result.count})")
```

### Exporting Data

Prefer the streaming exporters for large databases. Note that `dump()` returns k-mers as hexadecimal strings of their encoded `u128` values; `export_all_kmers()` returns decoded nucleotide sequences:

```python
# Decoded k-mers, paginated in memory
for r in db.export_all_kmers(limit=1000):
    print(f"{r.kmer}: {r.count}")

# Stream straight to disk (TSV: "kmer<TAB>count" per line)
db.export_to_file("all_kmers.tsv")

# CSV with header row, or JSON
db.export_to_csv("kmers.csv")
db.export_to_json("kmers.json")
```

### Merging Databases

`PyDatabase.merge` is a static method with the same memory-bounded streaming merge as the CLI:

```python
PyDatabase.merge(["db1.rkdb", "db2.rkdb"], "merged.rkdb")

# Bound memory and force streaming
PyDatabase.merge(
    ["db1.rkdb", "db2.rkdb"],
    "merged.rkdb",
    max_memory="4GB",
    merge_mode="streaming",
)
```

### Integration with Scientific Libraries

The Python API integrates seamlessly with popular scientific libraries:

```python
import pandas as pd

db = PyDatabase("database.rkdb", LoadMode.Preload)

data = [
    {"kmer": r.kmer, "count": r.count}
    for r in db.export_all_kmers(limit=10000)
]

df = pd.DataFrame(data)
print(f"Loaded {len(df)} k-mers into DataFrame")
```

## Performance Considerations

### K-mer Size Selection

- **Small k (15-21)**: Better for short reads, more matches
- **Medium k (25-31)**: Good balance for most applications
- **Large k (51-64)**: Higher specificity, better for long sequences

The k-mer size is hard-limited to 1-64 (`PyCounter` raises `ValueError` otherwise).

### Memory Usage

- Use `canonical=True` to roughly halve the number of unique k-mers stored
- Open large databases with `LoadMode.MemoryMapped` or `LoadMode.Lazy` instead of `LoadMode.Preload`
- Stream exports with `export_to_file` rather than materializing dumps in Python

### Query Optimization

- `query_exact_batch` is more efficient than repeated single queries
- Preload mode gives the fastest lookups; Lazy mode trades query speed for memory
- Use `max_results` on fuzzy queries to cap expensive high-tolerance expansions

## Best Practices

1. **Match Query Length to the Database**: query strings must be exactly `db.kmer_size` characters
2. **Validate K-mers**: k-mers may contain only A, T, C, G (plus N in fuzzy patterns)
3. **Use Batch Operations**: better performance for multiple queries
4. **Choose an Appropriate Load Mode**: preload for repeated queries, lazy/mapped for large databases
5. **Monitor Memory Usage**: `db.get_stats().file_size` and `db.get_memory_usage()` report database and cache footprint

## Getting Help

- **Examples**: See the [examples section](../../examples/) for complete working examples
- **Tutorials**: Check the [tutorials section](../../tutorials/) for step-by-step guides
- **API Reference**: Detailed documentation for each component is available in the navigation above
- **GitHub Issues**: Report bugs or request features on the project repository
