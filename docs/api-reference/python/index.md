# Python API Reference

The Python API provides high-performance k-mer counting and database functionality through native Rust bindings. This interface offers the same performance as the Rust library while maintaining Python's ease of use and integration capabilities.

## Installation

```bash
pip install rustkmer
```

## Quick Start

```python
from rustkmer import KmerCounter, Database

# Count k-mers
counter = KmerCounter(k=21, canonical=True)
counter.count_file("genome.fa.gz")
print(f"Total k-mers: {counter.get_total_count()}")

# Query databases
db = Database()
db.load("genome.rkdb")
result = db.query("ATCGATCGATCG")
print(f"Count: {result.count}")
```

## Core Classes

### [KmerCounter](kmercounter.md)
Main class for k-mer counting operations:
- File and stream processing
- Multiple input formats (FASTA, FASTQ)
- Configurable k-mer sizes and options
- Statistics and result extraction

### [Database](database.md)
Database operations for storing and querying k-mer data:
- Binary database format (.rkdb)
- High-speed querying operations
- Memory-mapped file access
- Fuzzy search capabilities

### [Examples](examples.md)
Practical usage examples and common patterns:
- Basic workflows
- Advanced techniques
- Performance optimization
- Integration examples

## Performance Characteristics

The Python bindings provide near-native performance with minimal overhead:

| Operation | Performance | Memory Usage |
|-----------|-------------|--------------|
| Counting | ~1M k-mers/sec | Linear scaling |
| Querying | ~3.5M queries/sec | <2MB overhead |
| Fuzzy Query | ~80K queries/sec | Pattern dependent |
| File I/O | Streaming | Memory efficient |

## Data Types

### KmerCounter
```python
class KmerCounter:
    def __init__(self, k: int = 21, canonical: bool = True) -> None
    def count_file(self, filename: str) -> None
    def count_string(self, sequence: str) -> None
    def get_total_count(self) -> int
    def get_unique_count(self) -> int
    def get_top_kmers(self, limit: int) -> List[Tuple[str, int]]
```

### Database
```python
class Database:
    def __init__(self) -> None
    def load(self, filename: str, preload: bool = False) -> None
    def query(self, kmer: str) -> QueryResult
    def fuzzy_query(self, pattern: str, max_distance: int = 1) -> List[QueryResult]
    def get_stats(self) -> DatabaseStats
```

### QueryResult
```python
class QueryResult:
    kmer: str
    count: int
    exists: bool
```

## Error Handling

Python exceptions are raised for error conditions:

```python
from rustkmer import KmerError, KmerCounter

try:
    counter = KmerCounter(k=21)
    counter.count_file("nonexistent.fa")
except KmerError as e:
    print(f"Error: {e}")
```

### Exception Types

- **`KmerError`**: Base exception for all k-mer related errors
- **`FileError`**: File reading/writing errors
- **`DatabaseError`**: Database operation errors
- **`ParameterError`**: Invalid parameter values

## Thread Safety

The Python API is thread-safe for most operations:

```python
import threading
from rustkmer import KmerCounter

def worker_function(filename):
    counter = KmerCounter(k=21)
    counter.count_file(filename)
    return counter.get_total_count()

# Multiple threads can use KmerCounter instances simultaneously
threads = []
for file in files:
    thread = threading.Thread(target=worker_function, args=(file,))
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()
```

## Integration Examples

### NumPy Integration
```python
import numpy as np
from rustkmer import KmerCounter

counter = KmerCounter(k=21)
counter.count_file("genome.fa.gz")

# Get top k-mers as NumPy arrays
top_kmers = counter.get_top_kmers(1000)
kmers = np.array([kmer for kmer, count in top_kmers])
counts = np.array([count for kmer, count in top_kmers])
```

### Pandas Integration
```python
import pandas as pd
from rustkmer import KmerCounter

counter = KmerCounter(k=21)
counter.count_file("genome.fa.gz")

# Create DataFrame of results
top_kmers = counter.get_top_kmers(1000)
df = pd.DataFrame(top_kmers, columns=['kmer', 'count'])
df['frequency'] = df['count'] / counter.get_total_count()
```

### Biopython Integration
```python
from Bio import SeqIO
from rustkmer import KmerCounter

counter = KmerCounter(k=21)

# Process Biopython sequences
for record in SeqIO.parse("sequences.fa", "fasta"):
    counter.count_string(str(record.seq))

print(f"Processed {len(list(SeqIO.parse("sequences.fa", "fasta")))} sequences")
```

## Memory Management

The Python API handles memory management automatically:

- **Automatic cleanup**: Resources are freed when objects are destroyed
- **Memory-mapped files**: Databases use efficient memory mapping
- **Streaming processing**: Large files processed without loading entirely into memory

## Configuration

### Environment Variables
```bash
# Set number of threads for parallel processing
export RUSTKMER_THREADS=4

# Enable debug logging
export RUSTKMER_DEBUG=1
```

### Runtime Configuration
```python
import rustkmer

# Configure performance settings
rustkmer.set_thread_count(4)
rustkmer.enable_debug_mode(True)
```

## Best Practices

1. **Use appropriate k-mer sizes**: k=21 for most applications, k=31 for higher specificity
2. **Enable canonical k-mers**: Reduces memory usage and improves matching
3. **Reuse Database objects**: Avoid repeatedly loading the same database
4. **Process files in batches**: More efficient than many small operations
5. **Handle exceptions gracefully**: Always catch and handle KmerError exceptions

## Version Compatibility

- **Python**: 3.8, 3.9, 3.10, 3.11, 3.12, 3.13
- **Platforms**: Linux, macOS, Windows
- **Dependencies**: Minimal - only Python standard library required

For detailed documentation of specific methods and classes, see the individual API reference pages.