# Python API

The RustKmer Python API provides a powerful interface for k-mer analysis, database operations, and fuzzy searching. This section covers the complete Python API documentation.

## Overview

RustKmer's Python bindings offer high-performance k-mer operations with a simple, Pythonic interface. The API is built using PyO3 to provide seamless integration between Rust's performance and Python's ecosystem.

### Key Features

- **High Performance**: Rust-based implementation with multi-threaded processing
- **Memory Efficient**: Memory-mapped database access for large datasets
- **Rich Functionality**: Database operations, fuzzy queries, and k-mer counting
- **Python Integration**: Works seamlessly with pandas, NumPy, BioPython, and more
- **Type Safety**: Full type hints and error handling

## Quick Start

### Installation

```bash
pip install rustkmer
```

### Basic Usage

```python
from rustkmer import Database, KmerCounter

# Create a database from sequences
counter = KmerCounter(k=31, canonical=True)
counter.count_file("sequences.fasta")
counter.save_to_database("output.rkdb")

# Query the database
with Database("output.rkdb") as db:
    result = db.query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
    print(f"Count: {result.count}")

    # Fuzzy query
    fuzzy_result = db.fuzzy_query("ATCGATCGATCGATCGATCGATCGATCGATCGATGG", mutations=2)
    print(f"Found {fuzzy_result.total_matches} similar k-mers")
```

## API Components

### Core Classes

| Component | Description | Key Methods |
|-----------|-------------|-------------|
| [`Database`](database.md) | K-mer database operations | `query()`, `fuzzy_query()`, `stats()`, `dump()` |
| [`KmerCounter`](kmercounter.md) | K-mer counting and database creation | `count_file()`, `count_file_list()`, `save_to_database()` |
| [`QueryResult`](query.md) | Query results and metadata | `count`, `is_present`, `canonical` |
| [`FuzzyQueryResult`](fuzzyquery.md) | Fuzzy query results | `total_matches`, `exact_matches`, `get_fuzzy_matches()` |
| [`DatabaseStats`](stats.md) | Database statistics | `unique_kmers`, `total_counts`, `file_size` |

### Exceptions

| Exception | Description |
|-----------|-------------|
| `DatabaseNotFoundError` | Database file not found or inaccessible |
| `InvalidKmerError` | Invalid k-mer format or characters |
| `QueryError` | General query operation errors |
| `FuzzyQueryError` | Fuzzy query specific errors |

## Navigation

- [**Getting Started**](getting-started.md) - Installation, setup, and first steps
- [**Database**](database.md) - Database operations and management
- [**Query Results**](query.md) - Query result handling and metadata
- [**Fuzzy Queries**](fuzzyquery.md) - Advanced fuzzy searching
- [**Database Stats**](stats.md) - Database statistics and analysis
- [**Kmer Counter**](kmercounter.md) - K-mer counting and database creation
- [**Exceptions**](exceptions.md) - Error handling and exceptions
- [**Examples**](examples.md) - Comprehensive examples and use cases

## Usage Patterns

### Context Manager (Recommended)

Always use context managers for database operations to ensure proper resource cleanup:

```python
with Database("my_database.rkdb") as db:
    # Database operations here
    result = db.query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
    stats = db.stats()
# Database automatically closed here
```

### Batch Operations

For multiple queries, use batch operations for better performance:

```python
kmer_list = ["ATCGATCG...", "GCTAGCTA...", "TTTTTTTT..."]
batch_result = db.fuzzy_query_batch(kmer_list, mutations=2, max_workers=4)

for kmer, result in batch_result.successes.items():
    print(f"{kmer}: {result.total_matches} matches")
```

### Integration with Scientific Libraries

The Python API integrates seamlessly with popular scientific libraries:

```python
import pandas as pd

# Export database to pandas DataFrame
with Database("database.rkdb") as db:
    data = []
    for result in db.dump(limit=10000):
        data.append({
            'kmer': result.kmer,
            'count': result.count,
            'canonical': result.canonical
        })

    df = pd.DataFrame(data)
    print(f"Loaded {len(df)} k-mers into DataFrame")
```

## Performance Considerations

### K-mer Size Selection

- **Small k (15-21)**: Better for short reads, more matches
- **Medium k (25-31)**: Good balance for most applications
- **Large k (51-127)**: Higher specificity, better for long sequences

### Memory Usage

- Use `canonical=True` to reduce database size by ~50%
- Process large files in chunks using file lists
- Use generators for database dumps to minimize memory usage

### Query Optimization

- Batch queries are more efficient than individual queries
- Position mutations can significantly improve fuzzy query performance
- Use appropriate mutation tolerances to balance sensitivity and speed

## Integration Examples

### BioPython Integration

```python
from Bio import SeqIO
from rustkmer import KmerCounter, Database

# Process BioPython sequences
sequences = [record for record in SeqIO.parse("input.fasta", "fasta")]

# Create database
counter = KmerCounter(k=31, canonical=True)
counter.count_file("input.fasta")
counter.save_to_database("database.rkdb")

# Query with BioPython sequences
with Database("database.rkdb") as db:
    for record in sequences[:10]:  # Sample first 10
        if len(record.seq) >= 31:
            kmer = str(record.seq[:31])
            result = db.query(kmer)
            print(f"{record.id}: {result.count}")
```

### Jupyter Notebook Workflow

```python
# In Jupyter notebooks, use display and progress indicators
from IPython.display import display, clear_output
import time

with Database("large_database.rkdb") as db:
    stats = db.stats()
    display(f"Database: {stats.unique_kmers:,} unique k-mers")

    # Process with progress feedback
    results = []
    for i, result in enumerate(db.dump(limit=10000)):
        results.append(result)

        if i % 1000 == 0:
            clear_output(wait=True)
            print(f"Processed {i:,} k-mers...")
            time.sleep(0.1)
```

## Best Practices

1. **Always Use Context Managers**: Prevent resource leaks
2. **Handle Errors Appropriately**: Use try-catch blocks with specific exceptions
3. **Validate K-mers**: Ensure k-mers contain only A,T,C,G characters
4. **Use Batch Operations**: Better performance for multiple queries
5. **Choose Appropriate K-mer Size**: Balance specificity and performance
6. **Monitor Memory Usage**: Use generators for large datasets

## Common Workflows

### Database Creation and Analysis

```python
from rustkmer import KmerCounter, Database
import pandas as pd

# 1. Create database from FASTA
counter = KmerCounter(k=31, canonical=True)
counter.count_file("sequences.fasta")
counter.save_to_database("analysis.rkdb")

# 2. Analyze database content
with Database("analysis.rkdb") as db:
    stats = db.stats()
    print(f"Database stats: {stats}")

    # 3. Export for analysis
    df = pd.DataFrame([
        {'kmer': r.kmer, 'count': r.count}
        for r in db.dump(limit=50000, canonical_only=True)
    ])

    # 4. Statistical analysis
    print(f"Mean count: {df['count'].mean():.1f}")
    print(f"Median count: {df['count'].median():.1f}")
    print(f"Max count: {df['count'].max()}")
```

### Fuzzy Search Pipeline

```python
def find_variants(reference_kmer, database_path, max_mutations=3):
    """Find variants of a reference k-mer."""

    with Database(database_path) as db:
        # Progressive search with increasing mutation tolerance
        for mutations in range(max_mutations + 1):
            result = db.fuzzy_query(reference_kmer, mutations=mutations)

            if result.total_matches > 0:
                print(f"Found {result.total_matches} variants with {mutations} mutations")

                # Get detailed matches
                for match in result.get_fuzzy_matches():
                    print(f"  {match.kmer}: {match.count} (distance={match.distance})")

                return result

        print("No variants found")
        return None
```

## Getting Help

- **Examples**: See the [examples section](../examples/) for complete working examples
- **Tutorials**: Check the [tutorials section](../../tutorials/) for step-by-step guides
- **API Reference**: Detailed documentation for each component is available in the navigation
- **GitHub Issues**: Report bugs or request features on the project repository

## Version Information

The Python API follows semantic versioning and maintains compatibility within major versions. Check the [compatibility guide](../compatibility/) for detailed version information.