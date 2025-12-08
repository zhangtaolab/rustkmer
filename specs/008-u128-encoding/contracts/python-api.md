# Python API Contract: rustkmer u128 Support

## Classes

### SimpleKmerCounter

Creates and manages k-mer counting operations.

```python
class SimpleKmerCounter:
    def __init__(self, kmer_size: int, canonical: bool = True)

    def process_fasta(self, file_path: str) -> ProcessingStats
    def process_fastq(self, file_path: str) -> ProcessingStats
    def process_sequence(self, sequence: str) -> int
    def get_kmers(self) -> Dict[str, int]
    def save(self, file_path: str) -> None
    def clear(self) -> None
```

#### Constructor Parameters

- `kmer_size`: K-mer size (1-64)
- `canonical`: Whether to store canonical k-mers (default: True)

#### Methods

**process_fasta(file_path: str) → ProcessingStats**
- Processes a FASTA file
- Returns statistics about processed k-mers

**process_fastq(file_path: str) → ProcessingStats**
- Processes a FASTQ file
- Returns statistics about processed k-mers

**process_sequence(sequence: str) → int**
- Processes a single DNA sequence
- Returns number of k-mers extracted

**get_kmers() → Dict[str, int]**
- Returns dictionary of k-mer → count mappings
- Returns Python dict with string keys

**save(file_path: str) → None**
- Saves counter to RKDB file
- Raises DatabaseError on failure

### SimpleDatabase

Reads and queries k-mer databases.

```python
class SimpleDatabase:
    def __init__(self, file_path: str)

    def query(self, kmer: str) -> Optional[int]
    def query_batch(self, kmers: List[str]) -> List[Optional[int]]
    def contains(self, kmer: str) -> bool
    def get_kmer_count(self, kmer: str) -> int
    def get_all_kmers(self) -> Dict[str, int]
    def get_stats(self) -> DatabaseStats
```

#### Constructor Parameters

- `file_path`: Path to RKDB database file

#### Methods

**query(kmer: str) → Optional[int]**
- Queries a single k-mer
- Returns count if found, None otherwise
- Automatically uses canonical representation

**query_batch(kmers: List[str]) → List[Optional[int]]**
- Queries multiple k-mers efficiently
- Returns list of counts in same order
- Faster than individual queries

**contains(kmer: str) → bool**
- Checks if k-mer exists in database
- Returns True/False

**get_kmer_count(kmer: str) → int**
- Returns count for k-mer
- Returns 0 if not found

**get_all_kmers() → Dict[str, int]**
- Returns all k-mers and counts
- Warning: May consume significant memory for large databases

**get_stats() → DatabaseStats**
- Returns database statistics

### Data Classes

#### ProcessingStats

```python
@dataclass
class ProcessingStats:
    total_sequences: int
    valid_kmers: int
    skipped_ambiguous: int
    skipped_too_short: int
    unique_kmers: int
    total_count: int
    processing_time: float  # seconds
```

#### DatabaseStats

```python
@dataclass
class DatabaseStats:
    kmer_size: int
    total_kmers: int
    unique_kmers: int
    total_count: int
    file_size: int  # bytes
    is_canonical: bool
    is_sorted: bool
```

## Exceptions

```python
class RustKmerError(Exception):
    """Base exception for all rustkmer errors"""
    pass

class KmerError(RustKmerError):
    """K-mer related errors"""
    pass

class DatabaseError(RustKmerError):
    """Database related errors"""
    pass

class EncodingError(KmerError):
    """Encoding/decoding errors"""
    pass
```

## Usage Examples

### Creating a Database

```python
from rustkmer import SimpleKmerCounter

# Create counter with k=48
counter = SimpleKmerCounter(kmer_size=48)

# Process a FASTA file
stats = counter.process_fasta("genome.fasta")
print(f"Processed {stats.total_sequences} sequences")
print(f"Found {stats.unique_kmers} unique k-mers")

# Save to database
counter.save("genome_k48.rkdb")
```

### Querying a Database

```python
from rustkmer import SimpleDatabase

# Load database
db = SimpleDatabase("genome_k48.rkdb")

# Single query
count = db.query("ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT")
if count:
    print(f"K-mer found {count} times")
else:
    print("K-mer not found")

# Batch query
queries = [
    "ACGT" * 12,
    "GCTA" * 12,
    "TTTT" * 12
]
results = db.query_batch(queries)

for query, result in zip(queries, results):
    if result:
        print(f"{query[:16]}...: {result}")
    else:
        print(f"{query[:16]}...: not found")

# Check if k-mer exists
if db.contains("ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT"):
    print("K-mer exists in database")
```

### Getting Statistics

```python
from rustkmer import SimpleDatabase

db = SimpleDatabase("genome_k48.rkdb")
stats = db.get_stats()

print(f"K-mer size: {stats.kmer_size}")
print(f"Total k-mers: {stats.total_kmers:,}")
print(f"Unique k-mers: {stats.unique_kmers:,}")
print(f"Database size: {stats.file_size / (1024**3):.2f} GB")
```

### Error Handling

```python
from rustkmer import SimpleKmerCounter, KmerError, DatabaseError

try:
    counter = SimpleKmerCounter(kmer_size=65)  # Invalid
except KmerError as e:
    print(f"K-mer error: {e}")

try:
    db = SimpleDatabase("nonexistent.rkdb")
except DatabaseError as e:
    print(f"Database error: {e}")
```

## Performance Considerations

### Memory Usage

- Python integers automatically handle u128 values
- Large databases may use significant memory when loaded
- Use `query_batch()` for better performance with multiple queries

### Batch Operations

```python
# Efficient: batch query
queries = [f"{'ACGT' * 16}" for _ in range(1000)]
results = db.query_batch(queries)

# Inefficient: individual queries
for query in queries:
    count = db.query(query)  # Much slower
```

### Large Datasets

```python
# Process large files in chunks
counter = SimpleKmerCounter(kmer_size=64)

# Process multiple files
for fasta_file in ["chr1.fa", "chr2.fa", "chr3.fa"]:
    stats = counter.process_fasta(fasta_file)
    print(f"{fasta_file}: {stats.valid_kmers:,} k-mers")

# Save once at the end
counter.save("combined_k64.rkdb")
```

## Type Conversion

### Python ↔ Rust Types

| Python | Rust | Notes |
|--------|------|-------|
| `int` | `u128` | Automatic conversion |
| `str` | `String` | DNA sequences |
| `bool` | `bool` | Direct mapping |
| `dict` | `HashMap` | For k-mer mappings |

### K-mer Format

- Input: DNA strings (A, C, G, T)
- Output: Python integers for counts
- Internal: u128 encoding for storage

## Thread Safety

- `SimpleKmerCounter`: Not thread-safe for mutations
- `SimpleDatabase`: Thread-safe for queries
- Multiple threads can query the same database concurrently