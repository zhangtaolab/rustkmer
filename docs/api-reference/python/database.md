# Database

The `Database` class provides high-performance k-mer database operations for storing, loading, and querying k-mer data. It supports the RustKmer binary database format (.rkdb) with memory-mapped file access for optimal performance.

## Constructor

```python
Database() -> None
```

Creates a new Database instance. The database is initially empty and must be loaded with data using the `load()` method.

**Example:**
```python
from rustkmer import Database

# Create a new database instance
db = Database()
```

## Methods

### load()

Load k-mer data from a database file.

```python
load(filename: str, preload: bool = False) -> None
```

**Parameters:**
- `filename` (str): Path to the database file (.rkdb format).
- `preload` (bool, optional): Whether to load the entire database into memory. Default is False (memory-mapped access).

**Example:**
```python
db = Database()

# Load with memory-mapped access (default)
db.load("genome_k21.rkdb")

# Load with preloading for maximum query speed
db.load("genome_k21.rkdb", preload=True)
```

### query()

Query for exact k-mer matches.

```python
query(kmer: str) -> QueryResult
```

**Parameters:**
- `kmer` (str): The k-mer sequence to query.

**Returns:**
- `QueryResult`: Result object containing the query information.

**Example:**
```python
db = Database()
db.load("genome_k21.rkdb")

result = db.query("ATCGATCGATCGATCGATCG")
print(f"K-mer: {result.kmer}")
print(f"Count: {result.count}")
print(f"Exists: {result.exists}")
```

### fuzzy_query()

Query for k-mers with wildcard patterns and distance matching.

```python
fuzzy_query(pattern: str, max_distance: int = 1) -> List[QueryResult]
```

**Parameters:**
- `pattern` (str): Query pattern with wildcards (N for any base, or specific patterns).
- `max_distance` (int, optional): Maximum Hamming distance for matches. Default is 1.

**Returns:**
- `List[QueryResult]`: List of matching k-mers and their counts.

**Example:**
```python
db = Database()
db.load("genome_k21.rkdb")

# Query with wildcards
results = db.fuzzy_query("AATN")  # Matches AATA, AATC, AATG, AATT
print(f"Found {len(results)} matches")

# Query with distance tolerance
results = db.fuzzy_query("AATCG", max_distance=2)
for result in results:
    print(f"{result.kmer}: {result.count} (distance: {result.distance})")
```

### get_stats()

Get database statistics and metadata.

```python
get_stats() -> DatabaseStats
```

**Returns:**
- `DatabaseStats`: Statistics object with database information.

**Example:**
```python
db = Database()
db.load("genome_k21.rkdb")

stats = db.get_stats()
print(f"K-mer size: {stats.kmer_size}")
print(f"Total k-mers: {stats.total_kmers}")
print(f"Unique k-mers: {stats.unique_kmers}")
print(f"Database file: {stats.filename}")
print(f"Is sorted: {stats.sorted}")
print(f"Is preloaded: {stats.preloaded}")
```

### close()

Close the database and release resources.

```python
close() -> None
```

**Example:**
```python
db = Database()
db.load("genome_k21.rkdb")

# Use the database...
result = db.query("ATCGATCGATCGATCGATCG")

# Close when done
db.close()
```

### create_from_counter()

Create a database from a KmerCounter instance.

```python
create_from_counter(counter: KmerCounter, filename: str) -> None
```

**Parameters:**
- `counter` (KmerCounter): The counter instance containing k-mer data.
- `filename` (str): Path for the output database file.

**Example:**
```python
from rustkmer import KmerCounter, Database

# Count k-mers
counter = KmerCounter(k=21, canonical=True)
counter.count_file("genome.fa.gz")

# Create database directly from counter
db = Database()
db.create_from_counter(counter, "genome_k21.rkdb")
```

## Data Types

### QueryResult

```python
class QueryResult:
    kmer: str           # The k-mer sequence
    count: int          # Number of occurrences
    exists: bool        # Whether the k-mer was found
    distance: int       # Hamming distance (for fuzzy queries, 0 for exact queries)
```

### DatabaseStats

```python
class DatabaseStats:
    kmer_size: int      # Length of k-mers in the database
    total_kmers: int    # Total number of k-mer occurrences
    unique_kmers: int   # Number of unique k-mers
    filename: str       # Database file path
    sorted: bool        # Whether the database is sorted
    preloaded: bool     # Whether the database is preloaded in memory
```

## Usage Examples

### Basic Query Operations
```python
from rustkmer import Database

# Load database
db = Database()
db.load("genome_k21.rkdb")

# Exact query
result = db.query("ATCGATCGATCGATCGATCG")
if result.exists:
    print(f"Found {result.kmer} with count {result.count}")
else:
    print(f"K-mer {result.kmer} not found")

# Get database statistics
stats = db.get_stats()
print(f"Database contains {stats.unique_kmers:,} unique k-mers")

# Close database
db.close()
```

### Fuzzy Query with Wildcards
```python
from rustkmer import Database

db = Database()
db.load("genome_k21.rkdb")

# Simple wildcard query
wildcard_results = db.fuzzy_query("AATN")  # N = any base
print(f"Wildcard query found {len(wildcard_results)} matches")

# Multiple wildcards
multi_wildcard = db.fuzzy_query("ATNNT")
print(f"Multi-wildcard query found {len(multi_wildcard)} matches")

# Distance-based fuzzy query
distance_results = db.fuzzy_query("ATCGATCGATCGATCGATCG", max_distance=2)
print(f"Distance query found {len(distance_results)} matches")

for result in distance_results[:10]:  # Show first 10
    print(f"{result.kmer}: {result.count} (distance: {result.distance})")
```

### Batch Query Operations
```python
from rustkmer import Database

def query_batch(db, kmer_list):
    """Query multiple k-mers efficiently."""
    results = []
    for kmer in kmer_list:
        result = db.query(kmer)
        if result.exists:
            results.append(result)
    return results

# Load database once for multiple queries
db = Database()
db.load("genome_k21.rkdb", preload=True)  # Preload for maximum speed

# Query multiple k-mers
kmers_to_query = [
    "ATCGATCGATCGATCGATCG",
    "GCTAGCTAGCTAGCTAGCT",
    "TTGGAACCAGGTCCAACTTG",
    # ... many more k-mers
]

results = query_batch(db, kmers_to_query)
print(f"Found {len(results)} matching k-mers out of {len(kmers_to_query)} queried")

db.close()
```

### Database Creation and Management
```python
from rustkmer import KmerCounter, Database

# Create k-mer counter
counter = KmerCounter(k=21, canonical=True)
counter.count_file("genome.fa.gz")

# Create database
db = Database()
db.create_from_counter(counter, "genome_k21.rkdb")

# Verify the created database
db.load("genome_k21.rkdb")
stats = db.get_stats()
print(f"Created database with {stats.unique_kmers:,} unique k-mers")
print(f"Total k-mer count: {stats.total_kmers:,}")

db.close()
```

## Performance Optimization

### Memory vs Speed Trade-offs

```python
# Memory-mapped (default) - Lower memory usage, slightly slower queries
db = Database()
db.load("large_db.rkdb")  # Uses memory mapping

# Preloaded - Higher memory usage, maximum query speed
db = Database()
db.load("large_db.rkdb", preload=True)  # Loads entire database into memory

stats = db.get_stats()
print(f"Database loaded - Preloaded: {stats.preloaded}")
```

### Query Performance Tips

1. **Preload databases** for frequent querying
2. **Batch operations** to reduce overhead
3. **Use exact queries** when possible (faster than fuzzy queries)
4. **Limit fuzzy query distance** for better performance

### Large Database Handling

```python
import psutil
import os

def monitor_memory():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB

# Check memory before loading
print(f"Memory before: {monitor_memory():.1f} MB")

db = Database()
db.load("very_large_genome.rkdb")  # Use memory mapping for large files

# Check memory after loading
print(f"Memory after: {monitor_memory():.1f} MB")

# Perform queries
result = db.query("ATCGATCGATCGATCGATCG")

db.close()
print(f"Memory after close: {monitor_memory():.1f} MB")
```

## Error Handling

```python
from rustkmer import Database, KmerError

db = Database()

try:
    # Try to load non-existent file
    db.load("nonexistent.rkdb")
except KmerError as e:
    print(f"Database loading error: {e}")

try:
    # Query with invalid k-mer
    result = db.query("INVALID_KMER_WITH_X")
except KmerError as e:
    print(f"Query error: {e}")

try:
    # Fuzzy query with excessive distance
    results = db.fuzzy_query("ATCG", max_distance=100)  # Too large distance
except KmerError as e:
    print(f"Fuzzy query error: {e}")
```

## Thread Safety

Database objects can be safely used in parallel when each thread has its own instance:

```python
import threading
from rustkmer import Database

def worker_query(db_path, queries):
    """Worker function for parallel queries."""
    db = Database()
    db.load(db_path, preload=True)  # Each thread loads its own copy

    results = []
    for query in queries:
        result = db.query(query)
        if result.exists:
            results.append(result)

    db.close()
    return results

# Parallel processing with multiple threads
db_path = "genome_k21.rkdb"
query_sets = [
    ["ATCGATCG", "GCTAGCTA", "TTGGAACC"],
    ["CCAACTTG", "GGTTGCCT", "AAGGCCAA"],
    ["TTCGATTC", "AAGCTTAA", "CCGGAAGG"]
]

threads = []
for queries in query_sets:
    thread = threading.Thread(target=worker_query, args=(db_path, queries))
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()

print("All parallel queries completed")
```

## Best Practices

1. **Choose appropriate loading mode**: Use memory-mapping for large databases, preloading for frequent queries
2. **Close databases explicitly**: Ensure resources are released when done
3. **Handle exceptions**: Always wrap database operations in try-catch blocks
4. **Monitor memory usage**: Be aware of memory requirements for large databases
5. **Use batch queries**: Reduce overhead by grouping multiple queries
6. **Limit fuzzy query parameters**: Use reasonable distance limits for performance
7. **Database file management**: Keep database files organized and backed up