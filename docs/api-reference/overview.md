# API Reference Overview

This section provides comprehensive documentation for the RustKmer Python API. The API is designed to be intuitive, efficient, and fully compatible with the RustKmer CLI commands.

## Core Classes

The RustKmer Python API consists of four main classes:

### [KmerCounter](kmercounter.md)
The primary class for counting k-mers in sequence data.

```python
from rustkmer import KmerCounter

# Create a counter
counter = KmerCounter(k=31, canonical=True, threads=4)

# Count from file
counter.count_file("sequences.fa.gz")

# Get results
total = counter.get_total_count()
unique = counter.get_unique_count()

# Save to database
counter.save_to_database("output.rkdb")
```

**Key Features:**
- Supports FASTA and FASTQ formats
- Automatic gzip decompression
- Multi-threaded counting
- Canonical k-mer support
- Progress reporting callbacks

### [Database](database.md)
Manages RKDB database files for fast k-mer queries.

```python
from rustkmer import Database

# Load database
db = Database()
db.load("database.rkdb")

# Query k-mers
count = db.query("ATCGATCGATCGATCGATCGATC")

# Batch queries
sequences = ["ATCG", "GCTA", "CCCC"]
results = db.query_multiple(sequences)

# Get statistics
stats = db.get_stats()
```

**Key Features:**
- Memory-mapped access for large databases
- Exact k-mer queries
- Batch query optimization
- Database statistics
- Export capabilities

### [FuzzyQuery](fuzzyquery.md)
Performs fuzzy k-mer searches with wildcards and mismatches.

```python
from rustkmer import FuzzyQuery

# Create fuzzy query
fq = FuzzyQuery()
fq.load("database.rkdb")

# Search with wildcards
results = fq.query("AATN")  # N matches any base

# Search with mismatches
results = fq.query("ATCGATCG", max_mismatches=2)

# Get all matches
for sequence, count in results:
    print(f"{sequence}: {count}")
```

**Key Features:**
- Wildcard support (N for any base)
- Configurable mismatch tolerance
- Efficient search algorithms
- Result ranking

### [Exceptions](exceptions.md)
Error handling classes for robust error management.

```python
from rustkmer import KmerCounter, SequenceError, DatabaseError

try:
    counter = KmerCounter(k=31)
    counter.count_file("invalid_file.fa")
except SequenceError as e:
    print(f"Sequence error: {e}")
except DatabaseError as e:
    print(f"Database error: {e}")
```

## API Design Principles

### 1. **Performance First**
All operations are optimized for speed and memory efficiency:
- Zero-copy where possible
- Memory-mapped file access
- Parallel processing

### 2. **Pythonic Interface**
- Follows Python naming conventions
- Uses type hints throughout
- Implements context managers where appropriate
- Returns Python native types

### 3. **CLI Compatibility**
The Python API provides 100% functional parity with CLI commands:
- Same algorithms and parameters
- Identical output formats
- Consistent error handling

### 4. **Error Handling**
- Comprehensive exception hierarchy
- Informative error messages
- Graceful degradation

## Common Patterns

### File Processing

```python
from rustkmer import KmerCounter

# Standard pattern
counter = KmerCounter(k=31, canonical=True)
counter.count_file("input.fa.gz")
counter.save_to_database("output.rkdb")
```

### Database Queries

```python
from rustkmer import Database

# Load once, query many
db = Database()
db.load("database.rkdb")

for query in queries:
    count = db.query(query)
    process_result(query, count)
```

### Batch Processing

```python
from rustkmer import KmerCounter

# Process multiple files
counter = KmerCounter(k=21)
for file in file_list:
    counter.count_file(file)
    save_intermediate_results(file, counter)
```

## Performance Considerations

### Thread Usage
```python
# Use multiple threads for large files
counter = KmerCounter(k=31, threads=8)  # Use 8 threads

# Disable for small files
counter = KmerCounter(k=31, threads=1)  # Single thread
```

### Memory Management
```python
# Memory-mapped access for large databases
db = Database()
db.load("large_db.rkdb", memory_mapped=True)

# Preload for small databases
db = Database()
db.load("small_db.rkdb", memory_mapped=False)
```

### Canonical K-mers
```python
# Reduce memory by 2x with canonical mode
counter = KmerCounter(k=31, canonical=True)  # Recommended
```

## Integration with Bioinformatics Libraries

### Pandas Integration
```python
import pandas as pd
from rustkmer import Database

db = Database()
db.load("database.rkdb")

# Query from DataFrame
df = pd.read_csv("queries.csv")
results = [db.query(seq) for seq in df['sequence']]
df['count'] = results
```

### Biopython Integration
```python
from Bio import SeqIO
from rustkmer import KmerCounter

# Process Biopython sequences
counter = KmerCounter(k=21)
for record in SeqIO.parse("sequences.fasta", "fasta"):
    counter.count_string(str(record.seq))
```

### NumPy Integration
```python
import numpy as np
from rustkmer import KmerCounter

# Vectorized processing
sequences = np.array(['ATCG', 'GCTA', 'CCCC'])
counter = KmerCounter(k=7)
for seq in sequences:
    counter.count_string(seq)
```

## Version History

### Current Version (0.1.0)
- Complete API coverage
- All CLI features available
- Performance optimizations
- Comprehensive error handling

### Planned Features
- Asynchronous operations
- GPU acceleration
- Distributed computing support
- Advanced statistics

## Type Hints Reference

```python
from typing import Optional, List, Tuple, Dict, Any, Union
from pathlib import Path

# Common type signatures
def count_file(self,
               filepath: Union[str, Path],
               threads: Optional[int] = None) -> None: ...

def query(self,
          sequence: str) -> int: ...

def query_multiple(self,
                   sequences: List[str]) -> List[int]: ...

def get_stats(self) -> Dict[str, Any]: ...

def fuzzy_query(self,
                pattern: str,
                max_mismatches: int = 1) -> List[Tuple[str, int]]: ...
```

## Best Practices

1. **Always use canonical mode** for DNA sequences unless strand information is needed
2. **Choose k-mer size carefully**: 21-31 for general use, larger for specificity
3. **Use memory mapping** for databases larger than available RAM
4. **Batch queries** when possible to reduce I/O overhead
5. **Handle exceptions** gracefully for production code
6. **Use progress callbacks** for long-running operations

## Migration from CLI

If you're migrating from the CLI, here's a quick reference:

| CLI Command | Python Equivalent |
|-------------|-------------------|
| `rustkmer count` | `KmerCounter.count_file()` |
| `rustkmer query` | `Database.query()` |
| `rustkmer fuzzy-query` | `FuzzyQuery.query()` |
| `rustkmer merge` | `Database.merge_with()` |
| `rustkmer stats` | `Database.get_stats()` |
| `rustkmer dump` | `Database.dump()` |

For detailed migration guides, see the [User Guide](../user-guide/).