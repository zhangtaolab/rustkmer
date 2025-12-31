# RustKmer Python API Examples

This directory contains comprehensive examples demonstrating how to use the rustkmer Python API for various bioinformatics workflows. Each example is self-contained and showcases different aspects of the API.

## Overview

[RustKmer](https://github.com/your-org/rustkmer) is a high-performance k-mer database library with both CLI and Python interfaces. These examples demonstrate practical usage patterns for genomic data analysis, batch processing, and integration with scientific Python ecosystems.

## Available Examples

### 1. [basic_usage.py](basic_usage.py)
**Purpose**: Introduction to fundamental rustkmer operations

**Features demonstrated**:
- Database loading with context managers
- Single k-mer queries with validation
- Database statistics retrieval
- Basic error handling patterns
- Comparison of different loading approaches

**Ideal for**: First-time users learning the API basics

```bash
python basic_usage.py
```

### 2. [batch_processing.py](batch_processing.py)
**Purpose**: Efficient bulk querying of multiple k-mers

**Features demonstrated**:
- Parallel batch queries with configurable workers
- Performance optimization strategies
- Progress tracking for large batches
- Mixed valid/invalid k-mer handling
- Memory-efficient chunked processing

**Ideal for**: Processing large sets of k-mers efficiently

```bash
python batch_processing.py
```

### 3. [advanced_features.py](advanced_features.py)
**Purpose**: Advanced API capabilities and sophisticated workflows

**Features demonstrated**:
- Database dumping (streaming vs string)
- K-mer validation modes (strict vs lenient)
- Canonical k-mer representation
- JSON serialization for API integration
- Database metadata exploration
- CLI integration patterns

**Ideal for**: Complex workflows and integration scenarios

```bash
python advanced_features.py
```

### 4. [real_world_analysis.py](real_world_analysis.py)
**Purpose**: Practical bioinformatics workflows

**Features demonstrated**:
- K-mer extraction from FASTA files
- Cross-database comparison
- Frequency distribution analysis
- Multi-format data export (CSV, JSON, Excel)
- Integration with pandas and matplotlib
- Genomic sequence analysis workflow

**Ideal for**: Real-world genomic analysis applications

```bash
# Optional: Install dependencies for enhanced features
pip install pandas matplotlib

python real_world_analysis.py
```

## Test Data

All examples use test databases located in `../tests/test_data/`:

| Database | Size | k-mer Size | Description |
|----------|------|------------|-------------|
| `tiny_test.rkdb` | 8KB | 7 | Tiny database for quick testing |
| `small_test.rkdb` | 86KB | 7 | Small database for examples |
| `small_test_k33_C.rkdb` | 96KB | 33 | Special k=33 database |
| `medium_test.rkdb` | 160KB | 7 | Medium database for performance tests |
| `large_test.rkdb` | 164KB | 7 | Large database for stress tests |

Additionally, FASTA source files are available:
- `tiny_test.fasta`
- `small_test.fasta`
- `medium_test.fasta`
- `large_test.fasta`

## Prerequisites

### System Requirements
- Python 3.10 or higher
- RustKmer Python package installed

### Installation

```bash
# From the rustkmer repository root
cd python
pip install -e .

# Or install from PyPI (when available)
pip install rustkmer
```

### Optional Dependencies for Enhanced Features

For full functionality, install these optional packages:

```bash
# For data export and analysis
pip install pandas openpyxl

# For visualization
pip install matplotlib numpy
```

## Usage Patterns

### 1. Basic Database Operations

```python
from rustkmer import Database

# Context manager (recommended)
with Database("path/to/database.rkdb") as db:
    result = db.query("ATCGATCG")
    print(f"Count: {result.count}")

# Get database statistics
stats = db.stats()
print(f"Database has {stats.unique_kmers} unique k-mers")
```

### 2. Batch Processing

```python
from rustkmer import Database

kmer_list = ["AAAAAAA", "TTTTTTT", "ATCGATC", ...]

with Database("database.rkdb") as db:
    # Process in parallel
    results = db.query_batch(kmer_list, max_workers=4)

    for kmer, result in results.items():
        print(f"{kmer}: {result.count}")
```

### 3. Error Handling

```python
from rustkmer import Database
from rustkmer.exceptions import InvalidKmerError

try:
    with Database("database.rkdb") as db:
        result = db.query("ATCGX")  # Invalid character
except InvalidKmerError as e:
    print(f"Invalid k-mer: {e}")
```

### 4. Data Export

```python
import json
from rustkmer import Database

with Database("database.rkdb") as db:
    # Export query results
    results = db.query_batch(kmer_list)

    # To JSON
    export_data = {kmer: result.to_dict() for kmer, result in results.items()}
    with open("results.json", "w") as f:
        json.dump(export_data, f, indent=2)
```

## API Reference

### Core Classes

#### `Database`
Main interface for k-mer database operations.

**Key Methods**:
- `query(kmer, validate_strict=True)` - Query single k-mer
- `query_batch(kmers, max_workers=4, chunk_size=100)` - Query multiple k-mers
- `stats()` - Get database statistics
- `dump(limit=None, as_string=True)` - Iterate over k-mers
- `close()` / `reopen()` - Database resource management

#### `QueryResult`
Result of a k-mer query operation.

**Attributes**:
- `kmer` - Queried k-mer sequence
- `count` - Number of occurrences in database
- `canonical` - Canonical k-mer representation

**Methods**:
- `to_dict()` - Convert to dictionary
- `to_json()` - Convert to JSON string

#### `DatabaseStats`
Database metadata and statistics.

**Attributes**:
- `kmer_size` - Length of k-mers
- `unique_kmers` - Number of unique k-mers
- `total_counts` - Sum of all k-mer counts
- `min_count`, `max_count` - Minimum and maximum counts
- `average_count` - Average k-mer count (calculated)

### Exception Hierarchy

```
RustKmerError
├── DatabaseError
│   ├── DatabaseNotFoundError
│   ├── InvalidDatabaseError
│   └── DatabaseCorruptedError
├── QueryError
│   ├── InvalidKmerError
│   └── KmerLengthError
├── SubprocessError
└── ConfigurationError
```

## Performance Tips

### 1. Batch Processing
- Use `query_batch()` for multiple k-mers instead of individual queries
- Optimal worker count: typically 2-8 depending on your CPU
- Chunk size of 100-1000 works well for most datasets

### 2. Memory Management
- Use streaming dump for large databases: `db.dump(as_string=False)`
- Process large datasets in chunks to avoid memory issues
- Close databases when not in use

### 3. Validation Strategies
- Use `validate_strict=True` for production code (default)
- Use `validate_strict=False` for exploratory analysis
- Pre-validate k-mers for batch processing with strict validation

## Integration Examples

### With pandas

```python
import pandas as pd
from rustkmer import Database

with Database("database.rkdb") as db:
    results = db.query_batch(kmer_list)

    # Convert to DataFrame
    df = pd.DataFrame([result.to_dict() for result in results.values()])

    # Analyze
    print(df['count'].describe())
```

### With matplotlib

```python
import matplotlib.pyplot as plt
from rustkmer import Database

with Database("database.rkdb") as db:
    results = list(db.dump(as_string=False, limit=1000))
    counts = [r.count for r in results]

    plt.hist(counts, bins=50, log=True)
    plt.xlabel('K-mer Count')
    plt.ylabel('Frequency')
    plt.show()
```

## Troubleshooting

### Common Issues

1. **Database not found**
   - Ensure the database path is correct
   - Use absolute paths for reliability

2. **Invalid k-mer errors**
   - Check that k-mers only contain A, T, C, G
   - Verify k-mer length matches database

3. **Performance issues**
   - Use batch processing for multiple queries
   - Reduce worker count if memory is limited

4. **Memory errors**
   - Use streaming dump for large databases
   - Process data in chunks

### Getting Help

- Check the [RustKmer documentation](https://rustkmer.readthedocs.io/)
- Review API docstrings: `help(Database)`
- Examine test files for additional examples
- Open an issue on GitHub for bugs or feature requests

## Contributing

Contributions to these examples are welcome! Please:

1. Follow the existing code style and documentation patterns
2. Test your examples with all available test databases
3. Include appropriate error handling
4. Add comments explaining complex workflows
5. Update this README for new examples

## License

These examples are part of the RustKmer project and follow the same license terms.