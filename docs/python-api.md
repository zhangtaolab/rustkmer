# RustKmer Python API Documentation

## Overview

RustKmer Python bindings provide high-performance k-mer counting, database operations, and fuzzy search capabilities for genomic data analysis. The Python API wraps the efficient Rust implementation while providing a Pythonic interface.

## Installation

```bash
# Install with pip (requires Rust toolchain)
pip install rustkmer

# Or build from source
git clone https://github.com/yourorg/rustkmer
cd rustkmer
pip install -e .
```

## Quick Start

```python
from rustkmer import Database, KmerCounter, FuzzyQuery

# Query existing database
db = Database("data/genomes.rkdb")
result = db.query("ATCGATCGATCGATCGATCGATC")
if result.found:
    print(f"K-mer found with count: {result.count}")

# Count k-mers from FASTA
counter = KmerCounter(k=31)
counter.count_file("data/sequence.fasta")
counter.save_to_database("data/counts.rkdb")

# Fuzzy search for similar k-mers
fq = FuzzyQuery()
fq.set_database(db)
similar = fq.find_similar("ATCGATCGATCGATCGATCGATC", max_results=10)
for match in similar.get_fuzzy_matches(max_distance=2):
    print(f"{match.kmer}: distance={match.distance}, count={match.count}")
```

## Core Classes

### Database

The `Database` class provides read-only access to RKDB database files.

```python
from rustkmer import Database

# Load database
db = Database("path/to/database.rkdb")

# Query single k-mer
result = db.query("ATCGATCGATCGATCGATCGATC")
print(f"Found: {result.found}, Count: {result.count}")

# Query multiple k-mers efficiently
kmers = ["ATCGATCGATCGATCGATCGATC", "GCTAGCTAGCTAGCTAGCTAG"]
results = db.query_batch(kmers)

# Get database statistics
stats = db.get_stats()
print(f"Total k-mers: {stats.total_kmers}")
print(f"Unique k-mers: {stats.unique_kmers}")
print(f"Min/Max count: {stats.min_count}/{stats.max_count}")
print(f"Mean count: {stats.mean_count:.2f}")

# Check if k-mer exists
exists = db.exists("ATCGATCGATCGATCGATCGATC")

# Export database contents
db.dump("export.txt", format="text")
db.dump("export.csv", format="csv")
db.dump("export.json", format="json")
```

#### Thread Safety

For concurrent access, use the thread-safe wrapper:

```python
from rustkmer import Database, make_thread_safe
import threading

# Create thread-safe wrapper
db = Database("data.rkdb")
safe_db = make_thread_safe(db)

# Safe to use from multiple threads
def query_worker():
    result = safe_db.query("ATCGATCGATCGATCGATCGATC")
    print(f"Thread {threading.current_thread().name}: {result.count}")

threads = [threading.Thread(target=query_worker) for _ in range(4)]
for t in threads:
    t.start()
for t in threads:
    t.join()
```

### KmerCounter

Count k-mers from sequences and save to RKDB format.

```python
from rustkmer import KmerCounter

# Create counter
counter = KmerCounter(k=21, canonical=True)  # Use canonical k-mers

# Count from FASTA/FASTQ file
counter.count_file("sequences.fasta")

# Count from string
counter.count_string("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")

# Count from iterable
sequences = ["ATCGATCG", "GCTAGCTA", "ATCGATCG"]
counter.count_iterable(sequences)

# Save to database
counter.save_to_database("counts.rkdb")

# Get statistics
stats = counter.get_stats()
print(f"Total k-mers: {stats.total_kmers}")
print(f"Unique k-mers: {stats.unique_kmers}")
```

### FuzzyQuery

Find similar k-mers using wildcard patterns or Hamming distance.

```python
from rustkmer import Database, FuzzyQuery

# Set up fuzzy query
fq = FuzzyQuery(database=Database("data.rkdb"))

# Wildcard search
results = fq.search("ATCG*ATCG", max_results=100)
print(f"Pattern matched {results.total_matches} k-mers")

# Find similar k-mers
similar = fq.find_similar("ATCGATCGATCGATCGATCGATC", max_results=50)

# Access results
exact_matches = similar.get_exact_matches()
fuzzy_matches = similar.get_fuzzy_matches(max_distance=2)

# Group by distance
by_distance = similar.get_matches_by_distance()
for distance, matches in by_distance.items():
    print(f"Distance {distance}: {len(matches)} matches")

# Get top matches by count
top_matches = similar.get_top_matches(10, by='count')
for match in top_matches:
    print(f"{match.kmer}: {match.count}")
```

## Export Functionality

Export database contents to various formats with optional compression.

```python
from rustkmer import Database, export_to_json, export_to_csv
from rustkmer.export import ExportConfig, CompressionFormat, OutputFormat

# Using convenience functions
export_to_json(db, "export.json", compression=CompressionFormat.GZIP)
export_to_csv(db, "export.csv")
export_to_tsv(db, "export.tsv")

# Using advanced configuration
config = ExportConfig(
    format=OutputFormat.JSON,
    compression=CompressionFormat.GZIP,
    compression_level=9,
    min_count=5,
    max_count=1000,
    sort_by='count',
    reverse=True
)

exporter = DatabaseExporter(db, config)
stats = exporter.export("compressed_export.json")

print(f"Exported {stats.exported_kmers} k-mers")
print(f"Compression ratio: {stats.compression_ratio:.2f}")
```

## Error Handling

The API uses comprehensive error handling with specific exception types:

```python
from rustkmer import Database
from rustkmer.exceptions import DatabaseError, ValidationError, QueryError

try:
    db = Database("nonexistent.rkdb")
except DatabaseError as e:
    print(f"Database error: {e.error_code} - {e}")
    if e.error_code == "FILE_NOT_FOUND":
        print("Please check the file path")

try:
    db.query("INVALID_KMER")
except ValidationError as e:
    print(f"Validation error: {e.error_code}")
    print(f"Parameter: {e.parameter}")
```

## Performance Considerations

### Memory Usage

- Use memory-mapped files for large databases
- Batch queries are more efficient than individual queries
- Thread-safe operations have minimal overhead for read operations

### Query Optimization

```python
# Good: Batch queries
kmers = ["ATCGATCG", "GCTAGCTA"] * 1000
results = db.query_batch(kmers)

# Good: Use canonical k-mers when possible
counter = KmerCounter(k=31, canonical=True)

# Good: Thread-safe wrapper for concurrent access
safe_db = make_thread_safe(db)
```

## Examples

### Basic Workflow

```python
from rustkmer import KmerCounter, Database

# 1. Count k-mers from sequences
counter = KmerCounter(k=31)
counter.count_file("genome.fasta")

# 2. Save to database
counter.save_to_database("genome.rkdb")

# 3. Query the database
db = Database("genome.rkdb")

# 4. Find frequent k-mers
stats = db.get_stats()
print(f"Most common k-mers have count ~{stats.max_count}")

# 5. Export for analysis
db.dump("frequent_kmers.txt", min_count=100)
```

### Comparative Analysis

```python
from rustkmer import Database

# Load multiple databases
databases = [
    Database("sample1.rkdb"),
    Database("sample2.rkdb"),
    Database("sample3.rkdb")
]

# Compare statistics
for i, db in enumerate(databases, 1):
    stats = db.get_stats()
    print(f"Sample {i}: {stats.total_kmers} total, {stats.unique_kmers} unique")

# Find shared k-mers (requires manual comparison)
all_kmers = set()
for db in databases:
    # This would require an iterator implementation
    pass
```

## API Reference

### Database Class Methods

| Method | Description | Parameters | Returns |
|--------|-------------|------------|--------|
| `load(path)` | Load database from file | `path: str | Path` | `None` |
| `query(kmer)` | Query single k-mer | `kmer: str` | `QueryResult` |
| `query_batch(kmers)` | Query multiple k-mers | `kmers: List[str]` | `List[QueryResult]` |
| `exists(kmer)` | Check if k-mer exists | `kmer: str` | `bool` |
| `get_count(kmer)` | Get k-mer count | `kmer: str` | `int` |
| `get_stats()` | Get database statistics | `include_metadata: bool = True` | `DatabaseStats` |
| `dump(path, format)` | Export database contents | `path: str`, `format: str` | `None` |

### QueryResult Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `kmer` | str | The k-mer sequence |
| `count` | int | K-mer occurrence count |
| `found` | bool | Whether k-mer was found |

### DatabaseStats Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `total_kmers` | int | Total k-mer count (including duplicates) |
| `unique_kmers` | int | Number of unique k-mers |
| `min_count` | int | Minimum k-mer count |
| `max_count` | int | Maximum k-mer count |
| `mean_count` | float | Mean k-mer count |
| `sum_counts` | int | Sum of all counts |

## Thread Safety

All Database operations are thread-safe when using the `ThreadSafeDatabase` wrapper:

```python
from rustkmer import Database, make_thread_safe
from rustkmer.thread_safety import ThreadSafeDatabase

# Option 1: Wrapper function
safe_db = make_thread_safe(Database("data.rkdb"))

# Option 2: Direct class
safe_db = ThreadSafeDatabase(Database("data.rkdb"))

# Multiple threads can safely query
def worker(thread_id, db):
    result = db.query("ATCGATCGATCGATCGATCGATC")
    print(f"Thread {thread_id}: {result.count}")

import threading
threads = []
for i in range(10):
    t = threading.Thread(target=worker, args=(i, safe_db))
    t.start()
    threads.append(t)

for t in threads:
    t.join()
```

## Best Practices

1. **Use canonical k-mers** when possible to reduce database size
2. **Batch queries** for better performance
3. **Close databases** when done to free resources
4. **Use thread-safe wrapper** for concurrent access
5. **Handle errors gracefully** with specific exception types
6. **Export with compression** for large datasets
7. **Memory-map large files** automatically handled based on size

## Troubleshooting

### Common Issues

1. **ImportError**: Ensure Rust toolchain is installed and Python environment is activated
2. **File not found**: Check file paths and ensure `.rkdb` extension
3. **Memory errors**: Use smaller batch sizes or memory-mapped files
4. **Performance issues**: Use batch queries and consider thread-safe concurrent access

### Debug Mode

```python
import rustkmer
rustkmer.enable_debug_mode()
rustkmer.enable_trace_mode()
```

### Getting Help

- Check the RustKmer GitHub repository for issues and discussions
- Review test files in `python/tests/` for usage examples
- Use the exception messages and error codes for debugging