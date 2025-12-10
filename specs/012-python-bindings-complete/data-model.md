# Data Model: RustKmer Python Bindings

## Core Entities

### 1. KmerCounter

**Description**: Main class for counting k-mers in sequence data

**Fields**:
```python
class KmerCounter:
    k: int              # k-mer size (default: 21)
    canonical: bool     # whether to use canonical k-mers
    threads: int        # number of threads for parallel processing
    _counter: object    # internal Rust KmerCounter instance
```

**Methods**:
- `count_file(file_path: str) -> None`: Count k-mers from FASTA/FASTQ file
- `count_string(sequence: str) -> None`: Count k-mers from string
- `get_total_count() -> int`: Get total k-mer count
- `get_unique_count() -> int`: Get unique k-mer count
- `get_kmer_count(kmer: str) -> int`: Get count for specific k-mer
- `get_top_kmers(n: int) -> List[Tuple[str, int]]`: Get top n k-mers
- `save_to_database(path: str, compress: bool = True, sort: bool = True) -> Database`: Save counts to database

**Validation Rules**:
- k must be between 1 and 64 (due to u128 encoding)
- sequence must only contain A, C, G, T characters
- file_path must exist and be readable

### 2. Database

**Description**: Wrapper for RKDB database files providing query operations

**Fields**:
```python
class Database:
    filename: str       # Path to database file
    header: DatabaseHeader  # Database metadata
    _database: object    # Internal Rust DatabaseQuery instance
    loaded: bool        # Whether database is loaded
```

**Methods**:
- `load(path: str) -> None`: Load database from file
- `query(kmer: str) -> QueryResult`: Query single k-mer
- `query_batch(kmers: List[str]) -> List[QueryResult]`: Query multiple k-mers
- `exists(kmer: str) -> bool`: Check if k-mer exists
- `get_stats() -> DatabaseStats`: Get database statistics
- `fuzzy_query(pattern: str, max_distance: int, max_results: int = 100) -> List[FuzzyQueryResult]`: Fuzzy query
- `merge(other: Database, output_path: str) -> Database`: Merge with another database
- `dump(output_path: str, format: str = "text", threshold: int = 1) -> None`: Export database

**Validation Rules**:
- kmer must match database k-mer size
- pattern for fuzzy query can contain N wildcards
- max_distance must be between 0 and k-mer size

### 3. DatabaseHeader

**Description**: Metadata about database file

**Fields**:
```python
class DatabaseHeader:
    version: int        # Database format version
    kmer_size: int      # k-mer size used
    total_kmers: int    # Total k-mer count
    unique_kmers: int   # Unique k-mer count
    canonical: bool     # Whether k-mers are canonical
    created_at: str     # Creation timestamp
    file_size: int      # File size in bytes
```

### 4. QueryResult

**Description**: Result of a k-mer query

**Fields**:
```python
class QueryResult:
    kmer: str           # The k-mer that was queried
    count: int          # Count of the k-mer
    found: bool         # Whether k-mer was found
```

### 5. FuzzyQuery

**Description**: Class for performing fuzzy queries with wildcards

**Fields**:
```python
class FuzzyQuery:
    database: Database  # Database to query
    max_distance: int   # Maximum Hamming distance
```

**Methods**:
- `load_database(path: str) -> None`: Load database
- `query(pattern: str, max_distance: Optional[int] = None) -> List[FuzzyQueryResult]`: Perform fuzzy query
- `set_max_distance(distance: int) -> None`: Set maximum distance
- `query_batch(patterns: List[str]) -> List[List[FuzzyQueryResult]]`: Batch fuzzy query

### 6. DatabaseStats

**Description**: Statistics about a database

**Fields**:
```python
class DatabaseStats:
    kmer_size: int      # k-mer size
    total_kmers: int    # Total k-mers counted
    unique_kmers: int   # Unique k-mer sequences
    coverage: float     # Estimated coverage
    histogram: List[Tuple[int, int]]  # Count frequency histogram
    percentiles: Dict[str, int]  # P25, P50, P75, P95, P99
```

## Data Relationships

```
KmerCounter
    │
    ├─ count_string() ──┐
    │                   │
    └─ save_to_database() ──► Database
                           │
                           ├─ query() ──► QueryResult
                           │
                           ├─ fuzzy_query() ──► FuzzyQueryResult
                           │
                           └─ get_stats() ──► DatabaseStats
```

## Error Hierarchy

```python
class RustKmerError(Exception):
    """Base exception for all RustKmer errors"""
    pass

class SequenceError(RustKmerError):
    """Invalid DNA sequence"""
    pass

class DatabaseError(RustKmerError):
    """Database-related errors"""
    pass

class FileNotFoundError(DatabaseError):
    """Database file not found"""
    pass

class MemoryError(RustKmerError):
    """Memory allocation errors"""
    pass

class ValueError(RustKmerError):
    """Invalid parameter values"""
    pass
```

## Performance Considerations

### Memory Layout

1. **KmerCounter**: Uses Rust's HashMap<u128, u64> internally
2. **Database**: Memory-mapped file access for large databases
3. **Query Results**: Batched operations to minimize Rust-Python transitions

### Threading Model

- Thread-safe database access using Arc<RwLock<>>
- Parallel processing using Rayon
- GIL released for CPU-intensive operations

## Serialization Formats

### Database Format (.rkdb)

```
Header (fixed size):
- Magic: 8 bytes ("RKDBv2\0")
- Version: 4 bytes (u32)
- K-mer size: 4 bytes (u32)
- Flags: 4 bytes (canonical, compressed)
- Reserved: 16 bytes

Index Section (sorted k-mers):
- Each entry: 16 bytes (u128 k-mer) + 8 bytes (u64 count)

Optional Compression:
- LZ4 compression for count data
- Delta encoding for k-mer sequences
```

### Export Formats

1. **Text**: `kmer<TAB>count` per line
2. **CSV**: `kmer,count,canonical` with header
3. **JSON**: Structured with metadata
4. **Binary**: Rust serialization format

## Integration Points

### Python Ecosystem

- **NumPy**: Buffer protocol for k-mer arrays
- **Pandas**: DataFrame conversion for query results
- **BioPython**: Sequence object compatibility
- **Dask**: Distributed k-mer processing

### Rust Core

- Direct bridge to existing Rust implementations
- Zero-copy operations where possible
- Memory-safe sharing via Arc/Mutex patterns

## Versioning Strategy

- Database format includes version number
- Backward compatibility for reading older formats
- Migration path for format upgrades

## Security Considerations

- Memory safety guaranteed by Rust
- No unsafe code blocks in Python bindings
- Input validation at Rust-Python boundary
- Safe handling of user-provided file paths