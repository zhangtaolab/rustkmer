<!-- generated-by: gsd-doc-writer -->
# API Reference Overview

This section provides comprehensive documentation for the RustKmer Python API (`pyrustkmer`). The API is a native PyO3 extension module that wraps the same Rust core the CLI uses, designed to be intuitive, efficient, and functionally aligned with the RustKmer CLI commands.

## Core Classes

The RustKmer Python API consists of four main engine classes plus supporting result types:

### [Database](database.md)
The primary class for interacting with RKDB k-mer database files.

```python
from pyrustkmer import PyDatabase, LoadMode

# load_mode is a required constructor argument
db = PyDatabase("database.rkdb", LoadMode.Preload)

# Query k-mers
result = db.query_exact("ATCGATCGATCGATCGATCG")
print(f"Count: {result.count}")

# Batch queries
results = db.query_exact_batch(["ATCGATCGATCGATCGATCG", "GCTAGCTAGCTAGCTAGCTA"])

# Get database statistics
stats = db.get_stats()
print(f"K-mer size: {stats.kmer_size}")
print(f"Unique k-mers: {stats.unique_kmers}")
```

**Key Features:**
- Three loading modes (`LoadMode.Preload`, `LoadMode.MemoryMapped`, `LoadMode.Lazy`)
- Exact and batch k-mer queries
- Prefix and hybrid-pattern queries
- Database dump with pagination and export to text/JSON/CSV
- Static `merge()` for combining databases with a memory budget
- Database statistics and metadata

### [KmerCounter](kmercounter.md)
Builds new databases by counting k-mers from sequences and FASTA/FASTQ files.

```python
from pyrustkmer import PyCounter

counter = PyCounter(21, canonical=True)
counter.add_from_fasta("genome.fa.gz")
counter.save_database("genome_k21.rkdb")

stats = counter.get_stats()
print(f"Total: {stats.total_kmers}, Unique: {stats.unique_kmers}")
```

**Key Features:**
- k-mer lengths from 1 to 64
- Canonical (strand-independent) counting
- Gzip/bzip2/xz-compressed FASTA/FASTQ input
- Parallel counting with a configurable rayon thread pool

### [Fuzzy Query](fuzzyquery.md)
Pattern matching with wildcards and mutation tolerance.

```python
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

db = PyDatabase("database.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)

# Allow up to 2 substitutions; N acts as a wildcard
result = fuzzy.query_fuzzy("ATCGATCGATCGATCGATCG", max_mutations=2)
print(f"Found {result.total_matches} similar k-mers")

# Position-specific mutation constraints
result = fuzzy.query_fuzzy_position(
    "ATCGATCGATCGATCGATCG", 2, "10,15:2"
)
```

**Key Features:**
- Hamming-distance mutation tolerance
- `N` wildcard expansion in patterns
- Position-specific mutation constraints
- Distance-based filtering and top-match selection on results

### Prefix Query
`PyPrefixQuery` and `PyExtendedPrefixQuery` provide standalone prefix and hybrid-pattern engines over `.rkdb` files (see [Database](database.md) for the `PyDatabase` equivalents).

```python
from pyrustkmer import PyPrefixQuery, PyExtendedPrefixQuery

pq = PyPrefixQuery("database.rkdb")
matches = pq.query_prefix("ATCG")  # dict: kmer -> count (as str)

eq = PyExtendedPrefixQuery("database.rkdb")
metrics = eq.query_prefix_metrics("ATCG")  # includes execution_time_ms
```

### Result Types
- **[QueryResult](query.md)** (`PyQueryResult`) — k-mer, count, and found flag for exact queries
- **[DatabaseStats](stats.md)** (`PyDatabaseStats`, `PyCounterStats`) — database and counter statistics
- `PyFuzzyResult` / `PyFuzzyMatch` — fuzzy query results
- `PyPrefixQueryResult` / `PyPrefixQueryMetrics` — prefix query results with timing and block metrics

### [Exceptions](exceptions.md)
The bindings raise standard Python exceptions (`ValueError`, `FileNotFoundError`, `RuntimeError`, `PermissionError`); a single `RustKmerError` class is exported as a structured error payload.

```python
from pyrustkmer import PyDatabase, LoadMode

try:
    db = PyDatabase("nonexistent.rkdb", LoadMode.Preload)
except FileNotFoundError as e:
    print(f"Database not found: {e}")

try:
    result = db.query_exact("INVALID")
except ValueError as e:
    print(f"Invalid k-mer: {e}")
```

## API Design Principles

### 1. **Performance First**
All operations run in compiled Rust:
- Native PyO3 extension module (no subprocess/CLI invocation)
- The GIL is released during file-based counting so rayon workers run in parallel
- Optional preload / memory-mapped / lazy loading strategies per database

### 2. **Pythonic Interface**
- Follows Python naming conventions
- Results are objects with read-only properties
- Dictionary returns for mapping-style results (`query_exact_batch`, `extract_by_prefix`)

### 3. **CLI Alignment**
The Python API shares the Rust core with the CLI:
- Same RKDB format and query engines
- `PyDatabase.merge()` accepts the same `max_memory` / `merge_mode` grammar as the CLI's merge command
- Fuzzy position-mutation grammar matches the CLI's `--position-mutations`

### 4. **Error Handling**
- Standard Python exception types with descriptive messages
- Input validation at the Python boundary (k-mer length, characters, thread counts, merge modes)

## Common Patterns

### Database Operations

```python
from pyrustkmer import PyDatabase, LoadMode

# Open and query
db = PyDatabase("database.rkdb", LoadMode.Preload)
result = db.query_exact("ATCGATCGATCGATCGATCG")
stats = db.get_stats()

# The object holds no OS resources requiring explicit close();
# drop it (or let it go out of scope) when done.
```

### Counting to a New Database

```python
from pyrustkmer import PyCounter

counter = PyCounter(31, canonical=True, threads=8)
counter.add_from_fastq("reads.fastq.gz")
counter.save_database("sample.rkdb")
```

### Fuzzy Querying

```python
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

db = PyDatabase("database.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)

# Basic fuzzy query
result = fuzzy.query_fuzzy("ATCGATCGATCGATCGATCG", max_mutations=2)

# Position-specific mutations (0-indexed positions, limit after the colon)
result = fuzzy.query_fuzzy_position(
    "ATCGATCGATCGATCGATCG", 2, "10,15:2"
)

# Cap the number of returned matches
result = fuzzy.query_fuzzy("ATCGATCGATCGATCGATCG", 3, max_results=100)
```

### Merging Databases

```python
from pyrustkmer import PyDatabase

# Static method; writes the merged database directly to the output path
PyDatabase.merge(
    ["db1.rkdb", "db2.rkdb", "db3.rkdb"],
    "merged.rkdb",
    max_memory="4GB",
    merge_mode="auto",  # "auto" | "memory" | "streaming"
)
```

### Error Handling

```python
from pyrustkmer import PyDatabase, LoadMode

def safe_query(db_path, kmer):
    try:
        db = PyDatabase(db_path, LoadMode.Preload)
        return db.query_exact(kmer)
    except FileNotFoundError:
        print(f"Database file not found: {db_path}")
        return None
    except ValueError as e:
        print(f"Invalid input: {e}")
        return None
```

## Performance Considerations

### Database Loading

```python
# Fastest queries, highest memory (all k-mers cached in a sorted map)
db = PyDatabase("database.rkdb", LoadMode.Preload)

# Direct file I/O; lowest footprint for construction
db = PyDatabase("database.rkdb", LoadMode.MemoryMapped)

# Sorted index for binary search
db = PyDatabase("database.rkdb", LoadMode.Lazy)
```

### Fuzzy Query Optimization

```python
# Use position mutations to limit the search space
result = fuzzy.query_fuzzy_position(kmer, 2, "10,15:2")

# Cap returned matches to prevent unbounded result sets
result = fuzzy.query_fuzzy(kmer, 3, max_results=1000)
```

### Counting in Parallel

```python
# threads configures the rayon pool (default: all available cores)
counter = PyCounter(21, canonical=True, threads=8)
```

## Integration with Bioinformatics Libraries

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

### NumPy Integration

```python
import numpy as np
from pyrustkmer import PyDatabase, LoadMode

def batch_query_numpy(db_path, sequences):
    """Batch querying into a NumPy array."""
    db = PyDatabase(db_path, LoadMode.Preload)
    results = db.query_exact_batch(list(sequences))
    return np.array([results[seq].count for seq in sequences])
```

### Biopython Integration

```python
from Bio import SeqIO
from pyrustkmer import PyDatabase, LoadMode

def analyze_sequences(db_path, fasta_file, k=31):
    """Analyze sequences from FASTA against database."""
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

## Type Hints Reference

Signatures of the most-used methods (as implemented in `pyo3/src/`):

```python
# PyDatabase
def __init__(self, path: str, load_mode: LoadMode) -> None: ...

def query_exact(self, kmer: str) -> PyQueryResult: ...
def query_exact_batch(self, kmers: list[str]) -> dict[str, PyQueryResult]: ...
def exists(self, kmer: str) -> bool: ...
def get_stats(self) -> PyDatabaseStats: ...
def dump(self, limit: int | None = None, offset: int = 0) -> list[PyQueryResult]: ...
def export_all_kmers(self, limit: int | None = None, offset: int = 0) -> list[PyQueryResult]: ...
def extract_by_prefix(self, prefix: str) -> dict[str, str]: ...
def query_prefix(self, prefix: str) -> PyPrefixQueryResult: ...
def export_to_file(self, output_path: str, limit: int | None = None,
                   offset: int = 0, progress_callback=None) -> int: ...

@staticmethod
def merge(databases: list[str], output: str, *,
          max_memory: str | None = None,
          merge_mode: str = "auto") -> None: ...

# PyCounter
def __init__(self, kmer_length: int, canonical: bool = False,
             initial_capacity: int = 1000,
             threads: int | None = None) -> None: ...

def add_kmer(self, kmer: str) -> None: ...
def add_sequence(self, sequence: str) -> None: ...
def add_from_fasta(self, file_path: str) -> None: ...
def add_from_fastq(self, file_path: str) -> None: ...
def save_database(self, file_path: str) -> None: ...
def get_stats(self) -> PyCounterStats: ...
def get_count(self, kmer: str) -> int: ...
def get_all_counts(self) -> dict[str, int]: ...

# PyFuzzyQuery
def __init__(self, database: PyDatabase) -> None: ...

def query_fuzzy(self, pattern: str, max_mutations: int,
                max_results: int | None = None) -> PyFuzzyResult: ...
def query_fuzzy_position(self, pattern: str, max_mutations: int,
                         position_mutations: str,
                         max_results: int | None = None) -> PyFuzzyResult: ...

# Result types
class PyQueryResult:
    kmer: str
    count: int
    found: bool

class PyDatabaseStats:
    kmer_size: int
    total_kmers: int
    unique_kmers: int
    file_size: int
    is_sorted: bool
    canonical: bool
```

## Best Practices

1. **Pick the right LoadMode**: `Preload` for repeated queries, `Lazy`/`MemoryMapped` to bound memory
2. **Use `query_exact_batch`** when querying many k-mers at once
3. **Use position mutations** in fuzzy queries to limit the search space
4. **Cap fuzzy results** with `max_results` to avoid unbounded result sets
5. **Handle built-in exceptions** (`ValueError`, `FileNotFoundError`, `RuntimeError`) rather than generic catching
6. **Set `threads=`** on `PyCounter` to control parallel counting workers

## Migration from CLI

If you're migrating from the CLI, here's a quick reference:

| CLI Command | Python Equivalent |
|-------------|-------------------|
| `rustkmer query database.rkdb ATCG` | `PyDatabase("database.rkdb", LoadMode.Preload).query_exact("ATCG")` |
| `rustkmer fuzzy-query database.rkdb ATCG --mutations 2` | `PyFuzzyQuery(db).query_fuzzy("ATCG", max_mutations=2)` |
| `rustkmer stats database.rkdb` | `PyDatabase("database.rkdb", LoadMode.Preload).get_stats()` |
| `rustkmer dump database.rkdb --limit 1000` | `PyDatabase("database.rkdb", LoadMode.Preload).dump(limit=1000)` |
| `rustkmer merge ... -o merged.rkdb` | `PyDatabase.merge([...], "merged.rkdb")` |

For detailed migration guides, see the [User Guide](../user-guide/).

## Version History

### Current Version (0.5.0)
- Database query API (`PyDatabase`) with three load modes
- Fuzzy query with position-mutation support (`PyFuzzyQuery`)
- Parallel k-mer counting with `PyCounter` (rayon, GIL released)
- Bounded, streaming-capable `PyDatabase.merge()`
- Database export to text/JSON/CSV with progress callbacks
- Native PyO3 extension module (`pyrustkmer`), Python 3.11+
