# API Reference Overview

This section provides comprehensive documentation for the RustKmer Python API. The API is designed to be intuitive, efficient, and fully compatible with the RustKmer CLI commands.

## Core Classes

The RustKmer Python API consists of three main classes and supporting data structures:

### [Database](database.md)
The primary class for interacting with RKDB k-mer database files.

```python
from rustkmer import Database

# Initialize database connection
db = Database("database.rkdb")

# Query k-mers
result = db.query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
print(f"Count: {result.count}")

# Fuzzy queries with mutation tolerance
fuzzy_result = db.fuzzy_query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG", mutations=2)
print(f"Found {fuzzy_result.total_matches} similar k-mers")

# Get database statistics
stats = db.stats()
print(f"K-mer size: {stats.kmer_size}")
print(f"Unique k-mers: {stats.unique_kmers}")
```

**Key Features:**
- Memory-mapped access for large databases
- Exact and fuzzy k-mer queries
- Batch query optimization
- Position-specific mutation constraints
- Database statistics and metadata
- Context manager support for resource management

### [QueryResult](query.md)
Represents the result of an exact k-mer query.

```python
from rustkmer import QueryResult

result = QueryResult(
    kmer="ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
    count=42,
    canonical="ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
)

print(f"K-mer: {result.kmer}")
print(f"Count: {result.count}")
print(f"Present: {result.is_present}")
```

**Key Features:**
- Simple dataclass structure
- JSON serialization support
- Dictionary conversion
- Presence checking

### [DatabaseStats](stats.md)
Contains statistics and metadata about a k-mer database.

```python
from rustkmer import DatabaseStats

stats = DatabaseStats(
    kmer_size=31,
    unique_kmers=1000000,
    total_counts=5000000,
    min_count=1,
    max_count=1000,
    file_size=25000000,
    format_version="2.0"
)

print(f"Database contains {stats.unique_kmers:,} unique k-mers")
print(f"Total occurrences: {stats.total_counts:,}")
```

**Key Features:**
- Complete database metadata
- JSON serialization support
- Statistical information for analysis
- File format version tracking

### [Fuzzy Query Classes](fuzzyquery.md)
Classes for representing fuzzy query results with mutation tolerance.

```python
from rustkmer import FuzzyQueryResult, FuzzyMatchResult, FuzzyBatchResult

# Single fuzzy query result
result = FuzzyQueryResult(
    query_kmer="ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
    mutations_allowed=2,
    total_matches=15,
    matches=[...]  # List of FuzzyMatchResult objects
)

# Batch query results
batch_result = FuzzyBatchResult(
    total_queries=10,
    successful_queries=9,
    successes={"ATCG...": result},
    errors={"INVALID": "Invalid k-mer format"}
)
```

**Key Features:**
- Hierarchical result organization
- Distance-based filtering
- Top match selection
- Batch processing support
- Comprehensive error handling

### [Exceptions](exceptions.md)
Comprehensive exception hierarchy for robust error management.

```python
from rustkmer import Database, DatabaseNotFoundError, InvalidKmerError, FuzzyQueryError

try:
    db = Database("nonexistent.rkdb")
except DatabaseNotFoundError as e:
    print(f"Database not found: {e.path}")

try:
    result = db.query("INVALID")
except InvalidKmerError as e:
    print(f"Invalid k-mer: {e.kmer}, reason: {e.reason}")
```

**Key Features:**
- Granular exception types
- Helpful error context
- Structured error information
- Inheritance hierarchy for easy catching

## API Design Principles

### 1. **Performance First**
All operations are optimized for speed and memory efficiency:
- Subprocess calls to optimized Rust CLI
- Memory-mapped file access where possible
- Parallel processing for batch operations
- Lazy loading of metadata

### 2. **Pythonic Interface**
- Follows Python naming conventions
- Uses type hints throughout
- Implements context managers where appropriate
- Returns Python native types and dataclasses

### 3. **CLI Compatibility**
The Python API provides 100% functional parity with CLI commands:
- Same algorithms and parameters
- Identical output formats
- Consistent error handling
- Position-mutation feature support

### 4. **Error Handling**
- Comprehensive exception hierarchy
- Informative error messages with context
- Graceful degradation options
- Validation at multiple levels

## Common Patterns

### Database Operations

```python
from rustkmer import Database

# Context manager usage (recommended)
with Database("database.rkdb") as db:
    result = db.query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
    stats = db.stats()
# Database automatically closed

# Manual management
db = Database("database.rkdb")
try:
    result = db.query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
    process_result(result)
finally:
    db.close()  # Always close to free resources
```

### Fuzzy Querying

```python
from rustkmer import Database

db = Database("database.rkdb")

# Basic fuzzy query
result = db.fuzzy_query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG", mutations=2)

# Position-specific mutations
result = db.fuzzy_query(
    "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
    position_mutations="10,15:2"  # Allow 2 mutations at positions 10 and 15
)

# Batch fuzzy queries
kmers = ["ATCGATCG...", "GCTAGCTA...", "TTTTTTTT..."]
batch_result = db.fuzzy_query_batch(kmers, mutations=2, max_workers=8)
```

### Error Handling

```python
from rustkmer import (
    Database, DatabaseNotFoundError, InvalidKmerError,
    FuzzyQueryError, QueryError
)

def safe_query(db_path, kmer):
    try:
        with Database(db_path) as db:
            result = db.query(kmer)
            return result

    except DatabaseNotFoundError:
        print(f"Database file not found: {db_path}")
        return None

    except InvalidKmerError as e:
        print(f"Invalid k-mer: {e.kmer} - {e.reason}")
        return None

    except QueryError as e:
        print(f"Query failed: {e}")
        return None
```

## Performance Considerations

### Database Initialization

```python
# Fast initialization (recommended)
db = Database("database.rkdb")  # validate=False by default

# Full validation (slower)
db = Database("database.rkdb", validate=True)
```

### Fuzzy Query Optimization

```python
# Use position mutations to limit search space
result = db.fuzzy_query(
    kmer,
    mutations=2,
    position_mutations="10,15:2"  # Much faster than allowing mutations anywhere
)

# Limit variants to prevent combinatorial explosion
result = db.fuzzy_query(
    kmer,
    mutations=3,
    max_variants=1000  # Conservative limit
)

# Batch processing for multiple queries
batch_result = db.fuzzy_query_batch(kmers, mutations=2, max_workers=8)
```

### Memory Management

```python
# Database automatically handles memory mapping
# Use context managers for proper resource cleanup
with Database("large_db.rkdb") as db:
    for result in db.dump(limit=100000):
        process_result(result)
# Resources automatically freed
```

## Integration with Bioinformatics Libraries

### Pandas Integration

```python
import pandas as pd
from rustkmer import Database

def query_dataframe(db_path, df, sequence_col='sequence'):
    """Query k-mers from a pandas DataFrame."""
    db = Database(db_path)

    # Add count column
    df['count'] = df[sequence_col].apply(
        lambda seq: db.query(seq).count
    )

    db.close()
    return df

# Usage
df = pd.read_csv("sequences.csv")
df_with_counts = query_dataframe("database.rkdb", df)
```

### NumPy Integration

```python
import numpy as np
from rustkmer import Database

def batch_query_numpy(db_path, sequences):
    """Vectorized batch querying."""
    db = Database(db_path)

    # Convert to array for processing
    seq_array = np.array(sequences)
    counts = np.array([db.query(seq).count for seq in seq_array])

    db.close()
    return counts

# Usage
sequences = ["ATCGATCG...", "GCTAGCTA...", "TTTTTTTT..."]
counts = batch_query_numpy("database.rkdb", sequences)
```

### Biopython Integration

```python
from Bio import SeqIO
from rustkmer import Database

def extract_kmers_from_fasta(fasta_file, k=31):
    """Extract k-mers from FASTA sequences."""
    kmers = []
    for record in SeqIO.parse(fasta_file, "fasta"):
        seq = str(record.seq).upper()
        for i in range(len(seq) - k + 1):
            kmer = seq[i:i+k]
            if 'N' not in kmer:  # Skip ambiguous k-mers
                kmers.append(kmer)
    return kmers

def analyze_sequences(db_path, fasta_file):
    """Analyze sequences from FASTA against database."""
    db = Database(db_path)
    kmers = extract_kmers_from_fasta(fasta_file)

    results = []
    for kmer in kmers[:1000]:  # Limit for demo
        result = db.query(kmer)
        if result.is_present:
            results.append({
                'kmer': kmer,
                'count': result.count,
                'canonical': result.canonical
            })

    db.close()
    return results
```

## Type Hints Reference

```python
from typing import Optional, List, Dict, Any, Union
from pathlib import Path

# Database class type signatures
def __init__(self,
             path: Union[str, Path],
             validate: bool = False) -> None: ...

def query(self,
          kmer: str,
          validate_strict: bool = True) -> QueryResult: ...

def fuzzy_query(self,
                kmer: str,
                mutations: int = 1,
                max_variants: Optional[int] = None,
                output_format: str = 'auto',
                position_mutations: Optional[str] = None) -> FuzzyQueryResult: ...

def fuzzy_query_batch(self,
                      kmers: List[str],
                      mutations: int = 1,
                      max_variants: Optional[int] = None,
                      max_workers: int = 4,
                      output_format: str = 'auto',
                      position_mutations: Optional[str] = None) -> FuzzyBatchResult: ...

def stats(self) -> DatabaseStats: ...

def dump(self,
         limit: Optional[int] = None,
         canonical_only: bool = False,
         output_format: str = 'auto') -> Iterator[DumpResult]: ...

# Result classes
class QueryResult:
    kmer: str
    count: int
    canonical: str

class DatabaseStats:
    kmer_size: int
    unique_kmers: int
    total_counts: int
    min_count: int
    max_count: int
    file_size: int
    format_version: str
```

## Best Practices

1. **Always use context managers** (`with` statements) for Database objects
2. **Choose validate=False** for Database initialization unless validation is needed
3. **Use position mutations** in fuzzy queries to limit search space
4. **Batch queries** when possible to reduce overhead
5. **Handle specific exceptions** rather than generic catching
6. **Use max_variants** to prevent combinatorial explosion in fuzzy queries
7. **Close databases** manually when not using context managers

## Migration from CLI

If you're migrating from the CLI, here's a quick reference:

| CLI Command | Python Equivalent |
|-------------|-------------------|
| `rustkmer query database.rkdb ATCG` | `Database("database.rkdb").query("ATCG")` |
| `rustkmer fuzzy-query database.rkdb ATCG --mutations 2` | `Database("database.rkdb").fuzzy_query("ATCG", mutations=2)` |
| `rustkmer stats database.rkdb` | `Database("database.rkdb").stats()` |
| `rustkmer dump database.rkdb --limit 1000` | `Database("database.rkdb").dump(limit=1000)` |
| `rustkmer fuzzy-query database.rkdb ATCG --position-mutations "10,15:2"` | `Database("database.rkdb").fuzzy_query("ATCG", position_mutations="10,15:2")` |

For detailed migration guides, see the [User Guide](../user-guide/).

## Version History

### Current Version (0.1.0)
- Complete database query API
- Fuzzy query with position-mutation support
- Comprehensive exception hierarchy
- Batch processing capabilities
- CLI compatibility through subprocess calls

### Key Features Added
- Position-specific mutation constraints
- Parallel batch fuzzy queries
- Enhanced error handling with context
- Google-style docstring documentation
- Type hints throughout the API