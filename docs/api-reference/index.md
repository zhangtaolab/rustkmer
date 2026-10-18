<!-- generated-by: gsd-doc-writer -->
# API Reference

This section provides comprehensive API documentation for both Rust and Python interfaces of RustKmer. Whether you're integrating RustKmer into a Rust application or using the Python bindings (`pyrustkmer`) for bioinformatics workflows, you'll find detailed documentation for all available classes and methods.

## Quick Navigation

### Rust API
- **[KmerCounter](rust/kmer_counter.md)** - Core k-mer counting functionality
- **[Database](rust/database.md)** - Database operations and storage
- **[Fuzzy Query](rust/fuzzy.md)** - Pattern matching and fuzzy search

### Python API
- **[Database](database.md)** - Python database interface for k-mer queries
- **[QueryResult](query.md)** - Exact query result representation
- **[DatabaseStats](stats.md)** - Database statistics and metadata
- **[Fuzzy Query](fuzzyquery.md)** - Fuzzy search with mutation tolerance
- **[Exceptions](exceptions.md)** - Error handling in the Python bindings
- **[Overview](overview.md)** - Complete API overview and usage patterns

## Language Bindings

### Rust Library
The Rust library provides the highest performance and most comprehensive feature set:

```rust
use rustkmer::KmerCounter;
use rustkmer::kmer::encoding::encode_kmer_u128;

// KmerCounter::new(kmer_length, canonical_mode, initial_capacity, threads)
let counter = KmerCounter::new(21, true, 1000, 4)?;
counter.increment(encode_kmer_u128("ATGCGATGCATGCGATGCAT")?)?;
let stats = counter.get_stats();
println!("Total k-mers: {}", stats.total_kmers);
```

### Python Bindings
The `pyrustkmer` package is a native PyO3 extension module that wraps the same Rust core:

```python
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

# Load an existing database (load_mode is required)
db = PyDatabase("genome.rkdb", LoadMode.Preload)

# Exact query
result = db.query_exact("ATCGATCGATCGATCGATCG")
print(f"K-mer count: {result.count}")

# Fuzzy query with mutation tolerance
fuzzy = PyFuzzyQuery(db)
fuzzy_result = fuzzy.query_fuzzy("ATCGATCGATCGATCGATCG", max_mutations=1)
print(f"Found {fuzzy_result.total_matches} similar k-mers")

# Database statistics
stats = db.get_stats()
print(f"Database contains {stats.unique_kmers:,} unique k-mers")
```

## Core Concepts

### K-mer Counting
- **k-mer**: A sequence of length k from DNA/RNA sequences
- **Canonical k-mer**: The lexicographically smaller of a k-mer and its reverse complement
- **Counting**: Tallying occurrences of each k-mer in a dataset
- **RKDB format**: Binary format for storing k-mer databases (magic `RKDB`, version 2)

### Database Operations
- **Query**: Exact k-mer lookup with count retrieval
- **Fuzzy Query**: Search within a specified Hamming distance
- **Position Mutations**: Constrain mutations to specific positions
- **Prefix Query**: Retrieve all k-mers sharing a prefix (or a hybrid pattern like `ATAC{N5}ACAC`)
- **Statistics**: Retrieve database metadata and composition

### Fuzzy Querying
- **Mutation Tolerance**: Allow up to N substitutions in matches
- **Position Constraints**: Restrict mutations to specific k-mer positions
- **Hamming Distance**: Number of differing positions between k-mers
- **Wildcards**: `N` characters in the pattern expand to any base

## Performance Characteristics

Both surfaces share the same Rust core, so Python carries only the FFI boundary overhead:

| Operation | Relative Cost | Notes |
|-----------|---------------|-------|
| Exact query (`query_exact`) | Fastest | Hash/binary-search lookup, no variant generation |
| Batch exact query (`query_exact_batch`) | Fast | One call boundary for many k-mers |
| Prefix query (`query_prefix`) | Moderate | Sorted-block scan |
| Fuzzy query (`query_fuzzy`) | Slowest | Combinatorial variant generation; keep `max_mutations` low or use `max_results` |

## Error Handling

### Rust Error Types
```rust
use rustkmer::{KmerCounter, ProcessingResult};

fn build_counter() -> ProcessingResult<KmerCounter> {
    KmerCounter::new(21, true, 1000, 4)
}
```

### Python Exceptions
The bindings raise standard Python exceptions. Catch the built-in types:

```python
from pyrustkmer import PyDatabase, LoadMode

try:
    db = PyDatabase("database.rkdb", LoadMode.Preload)
    result = db.query_exact("ATCGATCGATCGATCGATCG")
except FileNotFoundError as e:
    print(f"Database not found: {e}")
except ValueError as e:
    print(f"Invalid input or database: {e}")
except RuntimeError as e:
    print(f"Query failed: {e}")
```

See [Exceptions](exceptions.md) for the full mapping.

## Thread Safety

- **Rust**: `KmerCounter` uses a sharded concurrent map (`DashMap`); increments are thread-safe
- **Python**: `pyrustkmer` is a native extension (not subprocess-based); file-based counting (`PyCounter.add_from_fasta` / `add_from_fastq`) releases the GIL and parallelizes across a rayon thread pool
- **`PyCounter(threads=...)`**: controls the rayon worker count for counting (default: all available cores)

## Version Compatibility

- **Rust**: Requires Rust 1.80+ stable
- **Python**: Requires Python 3.11+ (`requires-python = ">=3.11"` in `pyo3/pyproject.toml`)
- **Package version**: 0.5.0 (kept in sync across `Cargo.toml`, `pyo3/Cargo.toml`, and `pyo3/pyproject.toml`)
- **Database format**: `.rkdb` binary format, version 2
- **Platforms**: Linux and macOS (manylinux/macOS wheels built with maturin)

## Python API Structure

The Python API provides an object-oriented interface. All types are exported from the top-level `pyrustkmer` module:

```python
from pyrustkmer import (
    PyDatabase, PyDatabaseStats, PyQueryResult, PyPrefixQueryResult, LoadMode,
    PyCounter, PyCounterStats,
    PyFuzzyQuery, PyFuzzyResult, PyFuzzyMatch,
    PyPrefixQuery, PyExtendedPrefixQuery, PyPrefixQueryMetrics,
    PyFormatter, RustKmerError,
)

# Database class - main query interface
db = PyDatabase("database.rkdb", LoadMode.Preload)

# Query results
result = db.query_exact("ATCGATCGATCGATCGATCG")
print(f"Count: {result.count}")

# Fuzzy queries
fuzzy = PyFuzzyQuery(db)
fuzzy_result = fuzzy.query_fuzzy("ATCGATCGATCGATCGATCG", max_mutations=2)
top_matches = fuzzy_result.get_top_matches(5)

# Database statistics
stats = db.get_stats()
print(f"K-mer size: {stats.kmer_size}")
```

## Integration Examples

### Pandas Integration
```python
import pandas as pd
from pyrustkmer import PyDatabase, LoadMode

def query_dataframe(db_path, df, sequence_col='sequence'):
    """Query k-mers from a pandas DataFrame."""
    db = PyDatabase(db_path, LoadMode.Preload)
    df['count'] = df[sequence_col].apply(
        lambda seq: db.query_exact(seq).count
    )
    return df
```

### Biopython Integration
```python
from Bio import SeqIO
from pyrustkmer import PyDatabase, LoadMode

def extract_and_query(fasta_file, db_path, k=31):
    """Extract k-mers from FASTA and query database."""
    db = PyDatabase(db_path, LoadMode.Preload)
    for record in SeqIO.parse(fasta_file, "fasta"):
        seq = str(record.seq).upper()
        for i in range(len(seq) - k + 1):
            kmer = seq[i:i+k]
            if 'N' not in kmer:
                result = db.query_exact(kmer)
                if result.found:
                    yield record.id, kmer, result.count
```

### NumPy Integration
```python
import numpy as np
from pyrustkmer import PyDatabase, LoadMode

def batch_query_numpy(db_path, sequences):
    """Batch querying via query_exact_batch."""
    db = PyDatabase(db_path, LoadMode.Preload)
    results = db.query_exact_batch(list(sequences))
    return np.array([results[seq].count for seq in sequences])
```

## Getting Help

- **Examples**: See the [User Guide](../user-guide/) section and `examples/python/` in the repository
- **Tutorials**: Check the [Tutorials](../tutorials/) section
- **Troubleshooting**: Visit the [Error Handling](exceptions.md) documentation
- **GitHub Issues**: Report bugs and request features

## Migration Guide

### From Rust CLI to Python API

| CLI Command | Python Equivalent |
|-------------|-------------------|
| `rustkmer query db.rkdb ATCG` | `PyDatabase("db.rkdb", LoadMode.Preload).query_exact("ATCG")` |
| `rustkmer fuzzy-query db.rkdb ATCG --mutations 2` | `PyFuzzyQuery(db).query_fuzzy("ATCG", max_mutations=2)` |
| `rustkmer stats db.rkdb` | `PyDatabase("db.rkdb", LoadMode.Preload).get_stats()` |
| `rustkmer dump db.rkdb --limit 1000` | `PyDatabase("db.rkdb", LoadMode.Preload).dump(limit=1000)` |
| `rustkmer merge a.rkdb b.rkdb -o merged.rkdb` | `PyDatabase.merge(["a.rkdb", "b.rkdb"], "merged.rkdb")` |

### Key Differences

1. **Interface**: Python uses method calls vs CLI commands
2. **Error Handling**: Python exceptions vs CLI exit codes
3. **Data Types**: Python objects vs text output
4. **Construction**: `PyDatabase` requires an explicit `LoadMode` argument

For detailed documentation of specific APIs, use the navigation sidebar to explore the Rust and Python API references.
