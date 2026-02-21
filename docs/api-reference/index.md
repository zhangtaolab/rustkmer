# API Reference

This section provides comprehensive API documentation for both Rust and Python interfaces of RustKmer. Whether you're integrating RustKmer into a Rust application or using the Python bindings for bioinformatics workflows, you'll find detailed documentation for all available functions, classes, and methods.

## Quick Navigation

### Rust API
- **[KmerCounter](rust/kmer_counter.md)** - Core k-mer counting functionality
- **[Database](rust/database.md)** - Database operations and storage
- **[Fuzzy Query](rust/fuzzy_query.md)** - Pattern matching and fuzzy search
- **[CLI](rust/cli.md)** - Command-line interface

### Python API
- **[Database](database.md)** - Python database interface for k-mer queries
- **[QueryResult](query.md)** - Exact query result representation
- **[DatabaseStats](stats.md)** - Database statistics and metadata
- **[Fuzzy Query](fuzzyquery.md)** - Fuzzy search with mutation tolerance
- **[Exceptions](exceptions.md)** - Error handling and exception hierarchy
- **[Overview](overview.md)** - Complete API overview and usage patterns

## Language Bindings

### Rust Library
The Rust library provides the highest performance and most comprehensive feature set:

```rust
use rustkmer::KmerCounter;

let mut counter = KmerCounter::new(21, true);
counter.add_from_fasta("genome.fa.gz")?;
println!("Total k-mers: {}", counter.get_stats().total_kmers));
```

### Python Bindings
Python bindings offer easy integration with bioinformatics workflows through database queries:

```python
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

# Query existing database
db = PyDatabase("genome.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
    result = db.query_exact("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
    print(f"K-mer count: {result.count}")

    # Fuzzy query with mutations
    fuzzy_result = fuzzy.query_fuzzy("ATCGATCGATCGATCGATCGATCGATCGATCGATCG", mutations=2)
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
- **RKDB format**: Efficient binary format for storing k-mer databases

### Database Operations
- **Query**: Exact k-mer lookup with count retrieval
- **Fuzzy Query**: Search within specified Hamming distance
- **Position Mutations**: Constrain mutations to specific positions
- **Batch Processing**: Query multiple k-mers efficiently
- **Statistics**: Retrieve database metadata and composition

### Fuzzy Querying
- **Mutation Tolerance**: Allow up to N substitutions in matches
- **Position Constraints**: Restrict mutations to specific k-mer positions
- **Hamming Distance**: Number of differing positions between k-mers
- **Batch Operations**: Parallel processing of multiple queries

## Performance Characteristics

| Operation | Rust Performance | Python Performance | Notes |
|-----------|------------------|-------------------|-------|
| Database Query | ~4M queries/sec | ~3.5M queries/sec | Minimal overhead |
| Fuzzy Query | ~100K queries/sec | ~80K queries/sec | Pattern matching overhead |
| Batch Query | ~200K queries/sec | ~150K queries/sec | Parallel processing |
| Memory Usage | Minimal | Minimal | Efficient implementations |

## Error Handling

### Rust Error Types
```rust
use rustkmer::{KmerError, KmerResult};

fn process_file() -> KmerResult<()> {
    // Your code here
    Ok(())
}
```

### Python Exceptions
```python
from pyrustkmer import (, PyFuzzyQuery
    PyDatabase, DatabaseNotFoundError, InvalidKmerError,
    FuzzyQueryError, QueryError
)

try:
    db = PyDatabase("database.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
        result = db.query_exact("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
except DatabaseNotFoundError as e:
    print(f"Database not found: {e.path}")
except InvalidKmerError as e:
    print(f"Invalid k-mer: {e.kmer} - {e.reason}")
except QueryError as e:
    print(f"Query failed: {e}")
```

## Thread Safety

- **Rust**: All operations are thread-safe when used properly
- **Python**: Thread-safe through subprocess isolation and CLI calls
- **Performance**: Multi-threading available through batch operations
- **Concurrency**: Parallel processing for batch fuzzy queries

## Version Compatibility

- **Rust**: Requires Rust 1.80+ stable
- **Python**: Supports Python 3.8+
- **Database Format**: Versioned format with backward compatibility
- **Cross-platform**: Linux, macOS, Windows

## Python API Structure

The Python API provides a clean, object-oriented interface:

```python
from pyrustkmer import (, PyFuzzyQuery
    PyDatabase, PyQueryResult, PyDatabaseStats,
    PyFuzzyResult, PyFuzzyMatch, PyPrefixQueryResult
)

# Database class - main interface
db = PyDatabase("database.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)

# Query results
result = db.query_exact("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
print(f"Count: {result.count}")

# Fuzzy queries
fuzzy_result = fuzzy.query_fuzzy("ATCGATCGATCGATCGATCGATCGATCGATCGATCG", mutations=2)
top_matches = fuzzy_result.get_top_matches(5)

# Database statistics
stats = db.get_stats()
print(f"K-mer size: {stats.kmer_size}")
```

## Integration Examples

### Pandas Integration
```python
import pandas as pd
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

def query_dataframe(db_path, df, sequence_col='sequence'):
    """Query k-mers from a pandas DataFrame."""
    db = PyDatabase(db_path, LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
        df['count'] = df[sequence_col].apply(
            lambda seq: db.query_exact(seq).count
        )
    return df
```

### Biopython Integration
```python
from Bio import SeqIO
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

def extract_and_query(fasta_file, db_path):
    """Extract k-mers from FASTA and query database."""
    db = PyDatabase(db_path, LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
        for record in SeqIO.parse(fasta_file, "fasta"):
            seq = str(record.seq).upper()
            # Extract 31-mers (example)
            for i in range(len(seq) - 31 + 1):
                kmer = seq[i:i+31]
                if 'N' not in kmer:
                    result = db.query_exact(kmer)
                    if result.found:
                        yield record.id, kmer, result.count
```

### NumPy Integration
```python
import numpy as np
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

def batch_query_numpy(db_path, sequences):
    """Vectorized batch querying."""
    db = PyDatabase(db_path, LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
        return np.array([db.query_exact(seq).count for seq in sequences])
```

## Getting Help

- **Examples**: See the [User Guide](../user-guide/) section
- **Tutorials**: Check the [Tutorials](../tutorials/) section
- **Troubleshooting**: Visit the [Error Handling](exceptions.md) documentation
- **GitHub Issues**: Report bugs and request features
- **Community**: Join discussions and contribute

## Migration Guide

### From Rust CLI to Python API

| CLI Command | Python Equivalent |
|-------------|-------------------|
| `rustkmer query db.rkdb ATCG` | `Database("db.rkdb").query_exact("ATCG")` |
| `rustkmer fuzzy-query db.rkdb ATCG --mutations 2` | `Database("db.rkdb").fuzzy_query("ATCG", mutations=2)` |
| `rustkmer stats db.rkdb` | `Database("db.rkdb").stats()` |
| `rustkmer dump db.rkdb --limit 1000` | `Database("db.rkdb").dump(limit=1000)` |

### Key Differences

1. **Interface**: Python uses method calls vs CLI commands
2. **Error Handling**: Structured exceptions vs exit codes
3. **Data Types**: Python objects vs text output
4. **Batch Processing**: Built-in parallelization vs manual scripting

For detailed documentation of specific APIs, use the navigation sidebar to explore the Rust and Python API references.