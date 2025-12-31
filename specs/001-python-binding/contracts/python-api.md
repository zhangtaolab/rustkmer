# Python API Contract: RustKmer Binding

**Version**: 0.1.0
**Feature**: 001-python-binding

## API Overview

The RustKmer Python API provides an object-oriented interface for querying k-mer databases through subprocess calls to the rustkmer CLI.

## Module Structure

```python
# rustkmer/__init__.py
from .database import Database, QueryResult, DatabaseStats
from .exceptions import (
    RustKmerError,
    DatabaseError,
    DatabaseNotFoundError,
    InvalidDatabaseError,
    QueryError,
    InvalidKmerError
)

__version__ = "0.1.0"
__all__ = [
    "Database",
    "QueryResult",
    "DatabaseStats",
    "RustKmerError",
    "DatabaseError",
    "DatabaseNotFoundError",
    "InvalidDatabaseError",
    "QueryError",
    "InvalidKmerError"
]
```

## Database Class Contract

### Constructor

```python
def __init__(self, path: Union[str, Path], validate: bool = True) -> None
```

**Parameters**:
- `path`: Path to the .rkdb database file
- `validate`: Whether to validate database on initialization

**Raises**:
- `DatabaseNotFoundError`: If file doesn't exist
- `InvalidDatabaseError`: If file is not a valid database

### Properties

```python
@property
def path(self) -> Path
```
Returns: Path to the database file

```python
@property
def kmer_size(self) -> Optional[int]
```
Returns: Length of k-mers in database (None until stats loaded)

```python
@property
def is_loaded(self) -> bool
```
Returns: Whether database metadata has been loaded

### Methods

#### query()

```python
def query(self, kmer: str) -> QueryResult
```

Query a single k-mer in the database.

**Parameters**:
- `kmer`: DNA sequence to query

**Returns**: `QueryResult` object

**Raises**:
- `InvalidKmerError`: If kmer contains invalid characters
- `QueryError`: If query fails

**Example**:
```python
result = db.query("ATCGATCG")
# result.kmer -> "ATCGATCG"
# result.count -> 42
# result.canonical -> "ATCGATCG"
```

#### query_batch()

```python
def query_batch(self, kmers: List[str], max_workers: int = 4) -> Dict[str, QueryResult]
```

Query multiple k-mers in parallel.

**Parameters**:
- `kmers`: List of k-mer sequences
- `max_workers`: Number of parallel subprocess calls

**Returns**: Dictionary mapping k-mer to QueryResult

**Complexity**: O(N) where N = len(kmers), with parallel factor = max_workers

#### dump()

```python
def dump(self, limit: Optional[int] = None, offset: int = 0) -> Iterator[QueryResult]
```

Iterate over k-mers in the database.

**Parameters**:
- `limit`: Maximum number of k-mers to return
- `offset`: Number of k-mers to skip

**Returns**: Iterator yielding QueryResult objects

**Performance**: Constant memory usage (streaming)

#### stats()

```python
def stats(self) -> DatabaseStats
```

Get database statistics.

**Returns**: `DatabaseStats` object

**Caching**: Results cached after first call

## Data Classes

### QueryResult

```python
@dataclass
class QueryResult:
    kmer: str
    count: int
    canonical: str

    @property
    def is_present(self) -> bool

    def to_dict(self) -> Dict[str, Union[str, int]]

    def to_json(self) -> str
```

### DatabaseStats

```python
@dataclass
class DatabaseStats:
    kmer_size: int
    unique_kmers: int
    total_counts: int
    max_count: int
    file_size: int
    format_version: str

    def to_dict(self) -> Dict[str, Union[str, int]]
```

## Exception Hierarchy

```
Exception
└── RustKmerError
    ├── DatabaseError
    │   ├── DatabaseNotFoundError
    │   └── InvalidDatabaseError
    └── QueryError
        └── InvalidKmerError
```

## CLI Integration Contract

The Python API maps to CLI commands as follows:

| Python Method | CLI Command | Arguments | Output Format |
|---------------|-------------|-----------|---------------|
| `query(kmer)` | `rustkmer query <db> <kmer>` | `--format json` if available | JSON → QueryResult |
| `query_batch()` | Multiple `rustkmer query` calls | Parallel execution | Combined dict |
| `stats()` | `rustkmer stats <db>` | `--format json` if available | JSON → DatabaseStats |
| `dump()` | `rustkmer dump <db>` | `--limit N --offset O --format tsv` | TSV → QueryResult iterator |

## Performance Requirements

- Single query: <100ms for typical databases
- Batch query: O(N) with parallel factor up to max_workers
- Dump: Constant memory, streaming with <10ms per k-mer
- Stats cache: Single subprocess call, cached results

## Thread Safety

- Database objects are NOT thread-safe
- Multiple Database instances can be used in different threads
- query_batch() is thread-safe within the method

## Version Compatibility

- Python 3.10+ required
- rustkmer CLI must be installed and in PATH
- Database format compatibility: v2.0+