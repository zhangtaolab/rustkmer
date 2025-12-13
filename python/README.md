# RustKmer Python Bindings

Python bindings for the rustkmer k-mer database library, providing an object-oriented interface for querying k-mer databases through subprocess calls to the rustkmer CLI tool.

## Installation

### From PyPI (when published)

```bash
pip install rustkmer
```

### From Source (Development Installation)

```bash
git clone https://github.com/rustkmer/rustkmer
cd rustkmer
pip install -e ./python
```

### Prerequisites

- Python 3.10 or higher
- rustkmer CLI tool installed and accessible in PATH
  - Installation methods:
    ```bash
    # Via cargo (requires Rust)
    cargo install rustkmer

    # Or download pre-built binaries from GitHub releases
    # https://github.com/rustkmer/rustkmer/releases
    ```

## Quick Start

```python
from rustkmer import Database

# Open a database
with Database("path/to/database.rkdb") as db:
    # Query a single k-mer
    result = db.query("ATCGATCGATCGATCGATCG")
    print(f"Count: {result.count}")
    print(f"Canonical: {result.canonical}")

    # Query multiple k-mers in parallel
    kmers = ["ATCGATCGATCGATCGATCG", "CCCCCCCCCCCCCCCCCCCC", "GGGGGGGGGGGGGGGGGGGG"]
    results = db.query_batch(kmers, max_workers=4)
    for kmer, result in results.items():
        print(f"{kmer}: {result.count}")

    # Get database statistics
    stats = db.stats()
    print(f"K-mer size: {stats.kmer_size}")
    print(f"Unique k-mers: {stats.unique_kmers:,}")
    print(f"Total counts: {stats.total_counts:,}")
    print(f"Max count: {stats.max_count:,}")
    print(f"Average count: {stats.average_count:.2f}")

    # Dump k-mers (memory-efficient streaming)
    for result in db.dump(limit=1000):
        print(f"{result.kmer}\t{result.count}")
```

## API Reference

### Database Class

The main interface for interacting with k-mer databases.

#### Constructor

```python
Database(path: Union[str, Path], validate: bool = True)
```

- `path`: Path to the .rkdb database file
- `validate`: Whether to validate the database on initialization (default: True)

#### Properties

- `path`: Path to the database file (Path object)
- `kmer_size`: Length of k-mers in the database (int, None until stats are loaded)
- `is_loaded`: Whether database metadata has been loaded (bool)

#### Methods

##### query()

```python
query(kmer: str) -> QueryResult
```

Query a single k-mer in the database.

- `kmer`: The k-mer sequence to query
- Returns: QueryResult object
- Raises: InvalidKmerError, QueryError

##### query_batch()

```python
query_batch(kmers: List[str], max_workers: int = 4, chunk_size: int = 100) -> Dict[str, QueryResult]
```

Query multiple k-mers in parallel.

- `kmers`: List of k-mer sequences to query
- `max_workers`: Maximum number of parallel subprocess calls (default: 4)
- `chunk_size`: Number of k-mers to process in each chunk for large batches (default: 100)
- Returns: Dictionary mapping k-mer to QueryResult

##### dump()

```python
dump(limit: Optional[int] = None, offset: int = 0, chunk_size: int = 10000, stream_large: bool = True) -> Iterator[QueryResult]
```

Iterate over k-mers in the database with memory-efficient streaming.

- `limit`: Maximum number of k-mers to return
- `offset`: Number of k-mers to skip
- `chunk_size`: Number of k-mers to fetch in each chunk for streaming
- `stream_large`: Force streaming mode for databases of any size
- Yields: QueryResult objects for each k-mer

##### stats()

```python
stats() -> DatabaseStats
```

Get database statistics. Results are cached for performance.

- Returns: DatabaseStats object
- Raises: QueryError

### QueryResult Class

Result of a k-mer query.

#### Attributes

- `kmer`: The queried k-mer sequence (str)
- `count`: Number of occurrences in the database (int)
- `canonical`: Canonical representation of the k-mer (str)

#### Properties

- `is_present`: Whether the k-mer exists in the database (bool)

#### Methods

- `to_dict()`: Convert to dictionary representation
- `to_json()`: Convert to JSON string
- `from_dict()`: Create QueryResult from dictionary

### DatabaseStats Class

Statistics about a k-mer database.

#### Attributes

- `kmer_size`: Length of k-mers in the database (int)
- `unique_kmers`: Number of unique k-mer sequences (int)
- `total_counts`: Sum of all k-mer counts (int)
- `max_count`: Maximum count for any single k-mer (int)
- `file_size`: Size of database file in bytes (int)
- `format_version`: Version of the database format (str)

#### Properties

- `average_count`: Average k-mer count (float)

#### Methods

- `to_dict()`: Convert to dictionary representation
- `to_json()`: Convert to JSON string
- `from_dict()`: Create DatabaseStats from dictionary

## Environment Configuration

### RUSTKMER_PATH

Set the path to the rustkmer executable:

```bash
export RUSTKMER_PATH="/path/to/rustkmer"
```

This is useful if you have multiple versions of rustkmer installed or want to use a specific build.

## Error Handling

The package provides a comprehensive exception hierarchy:

```python
from rustkmer.exceptions import (
    RustKmerError,           # Base exception
    DatabaseError,           # Database-related errors
    DatabaseNotFoundError,   # Database file not found
    InvalidDatabaseError,    # Invalid/corrupted database
    DatabaseCorruptedError,  # Database corruption detected
    QueryError,             # Query operation errors
    InvalidKmerError,       # Invalid k-mer sequence
    KmerLengthError,        # K-mer length mismatch
    SubprocessError,        # Subprocess execution errors
    ConfigurationError,     # Configuration issues
)
```

## Examples

### Memory-Efficient Processing of Large Databases

```python
from rustkmer import Database

# Process large database without loading everything into memory
with Database("large_database.rkdb") as db:
    stats = db.stats()
    print(f"Processing {stats.unique_kmers:,} unique k-mers")

    # Process in chunks
    chunk_size = 10000
    processed = 0

    for result in db.dump(chunk_size=chunk_size):
        # Process each k-mer
        if result.count > 100:
            print(f"High-frequency k-mer: {result.kmer} (count: {result.count})")

        processed += 1
        if processed % 100000 == 0:
            print(f"Processed {processed:,} k-mers...")
```

### Batch Query with Progress Tracking

```python
from rustkmer import Database
from tqdm import tqdm  # Optional progress bar

db = Database("database.rkdb")

# Generate test k-mers
test_kmers = [f"{'ATCG' * 5}" for _ in range(1000)]

# Batch query with progress tracking
results = db.query_batch(test_kmers, max_workers=8)

# Count successful queries
found = sum(1 for r in results.values() if r.is_present)
print(f"Found {found}/{len(test_kmers)} k-mers in database")
```

## Performance Tips

1. **Batch Queries**: Use `query_batch()` for multiple k-mers instead of individual `query()` calls
2. **Streaming Dumps**: Use the `dump()` method's streaming capability for large databases
3. **Cached Stats**: Database stats are cached after first access
4. **Adjust Workers**: Tune `max_workers` in `query_batch()` based on your system
5. **Chunk Size**: For very large datasets, adjust `chunk_size` in `dump()` based on memory constraints

## Testing

Run the test suite:

```bash
cd python
pytest tests/ -v --cov=rustkmer
```

## Contributing

Please see the main rustkmer repository for contributing guidelines.

## License

MIT License - see LICENSE file for details.