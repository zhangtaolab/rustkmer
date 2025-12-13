# Data Model: Python Binding API for rustkmer

**Feature**: 001-python-binding
**Date**: 2025-01-13

## Core Entities

### 1. Database

Represents a k-mer database file and provides methods for querying and analysis.

**Attributes**:
- `path`: Path to the .rkdb database file
- `kmer_size`: Length of k-mers in the database
- `total_kmers`: Total number of unique k-mers stored
- `total_counts`: Sum of all k-mer counts
- `format_version`: Version of the database format

**Validation Rules**:
- Path must exist and be readable
- File must be a valid .rkdb format
- File size must be reasonable for available memory

**State Transitions**:
```
Unloaded → Loaded → Closed
    ↓         ↓        ↓
  error → querying → error
```

### 2. QueryResult

Represents the result of a single k-mer query.

**Attributes**:
- `kmer`: The queried k-mer sequence
- `count`: Number of occurrences in the database
- `canonical`: Canonical representation of the k-mer

**Validation Rules**:
- kmer must be a valid DNA sequence (A, T, C, G)
- count must be a non-negative integer
- canonical form must match reverse complement rule

### 3. DatabaseStats

Statistics about the database (replaces "Database Metadata" for consistency).

**Attributes**:
- `kmer_size`: Length of k-mers
- `unique_kmers`: Number of unique k-mer sequences
- `total_counts`: Sum of all counts
- `max_count`: Maximum count for any single k-mer
- `file_size`: Size of database file in bytes
- `format_version`: Database format version

## Data Structures

### Database Class Design

```python
from pathlib import Path
from typing import Optional, List, Dict, Union, Iterator
from concurrent.futures import ThreadPoolExecutor
import subprocess
import json

class Database:
    """
    Represents a rustkmer k-mer database.

    Example:
        >>> db = Database("/path/to/database.rkdb")
        >>> count = db.query("ATCG")
        >>> stats = db.stats()
        >>> for result in db.dump(limit=1000):
        ...     print(result.kmer, result.count)
    """

    def __init__(self, path: Union[str, Path], validate: bool = True):
        """Initialize database connection"""

    @property
    def path(self) -> Path:
        """Path to the database file"""

    @property
    def kmer_size(self) -> Optional[int]:
        """Length of k-mers in database (None until loaded)"""

    @property
    def is_loaded(self) -> bool:
        """Whether database metadata has been loaded"""

    def query(self, kmer: str) -> QueryResult:
        """Query a single k-mer"""

    def query_batch(self, kmers: List[str],
                   max_workers: int = 4) -> Dict[str, QueryResult]:
        """Query multiple k-mers in parallel"""

    def dump(self, limit: Optional[int] = None,
             offset: int = 0) -> Iterator[QueryResult]:
        """Dump k-mers from database"""

    def stats(self) -> DatabaseStats:
        """Get database statistics"""

    def close(self):
        """Close database resources"""

    def __enter__(self):
        """Context manager entry"""

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""

@dataclass
class QueryResult:
    """Result of a k-mer query"""
    kmer: str
    count: int
    canonical: str

    @property
    def is_present(self) -> bool:
        """Whether k-mer exists in database"""

    def to_dict(self) -> Dict[str, Union[str, int]]:
        """Convert to dictionary representation"""

    def to_json(self) -> str:
        """Convert to JSON string"""

@dataclass
class DatabaseStats:
    """Database statistics"""
    kmer_size: int
    unique_kmers: int
    total_counts: int
    max_count: int
    file_size: int
    format_version: str

    def to_dict(self) -> Dict[str, Union[str, int]]:
        """Convert to dictionary"""

    @classmethod
    def from_cli_output(cls, output: str) -> 'DatabaseStats':
        """Parse stats from CLI output"""
```

## Error Handling

### Exception Hierarchy

```python
class RustKmerError(Exception):
    """Base exception for all rustkmer errors"""
    pass

class DatabaseError(RustKmerError):
    """Errors related to database operations"""
    pass

class DatabaseNotFoundError(DatabaseError, FileNotFoundError):
    """Database file does not exist"""
    pass

class InvalidDatabaseError(DatabaseError):
    """Database file is invalid or corrupted"""
    pass

class QueryError(RustKmerError):
    """Errors related to querying operations"""
    pass

class InvalidKmerError(QueryError, ValueError):
    """Invalid k-mer sequence"""
    pass
```

### Error Mapping from CLI

| CLI Error Pattern | Python Exception |
|-------------------|------------------|
| "No such file" | DatabaseNotFoundError |
| "Invalid database" | InvalidDatabaseError |
| "Invalid k-mer" | InvalidKmerError |
| "Permission denied" | PermissionError |
| Exit code != 0 | RustKmerError (with message) |

## Performance Considerations

### Memory Management
- Use generators/iterators for large dump operations
- Implement batch size limits for bulk operations
- Clear subprocess output buffers promptly

### Parallel Processing
- Use ThreadPoolExecutor for batch queries
- Limit concurrent subprocesses based on CPU cores
- Implement timeout for individual queries

### Caching Strategy
- Cache database stats after first access
- Consider LRU cache for frequently queried k-mers
- Invalidate cache on database modification

## Integration Points

### CLI Command Mapping

| Python Method | CLI Command | Output Format |
|---------------|-------------|---------------|
| `Database.query()` | `rustkmer query <db> <kmer>` | JSON/Text |
| `Database.stats()` | `rustkmer stats <db>` | JSON/Text |
| `Database.dump()` | `rustkmer dump <db> --limit N` | TSV/JSON |
| `Database.query_batch()` | Multiple `rustkmer query` calls | Combined JSON |