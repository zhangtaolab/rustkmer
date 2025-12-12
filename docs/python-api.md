# RustKmer Python API Documentation

## Overview

RustKmer Python bindings provide high-performance k-mer counting, database operations, and fuzzy search capabilities for genomic data analysis. The Python API wraps the efficient Rust implementation while providing a Pythonic interface.

## Installation

```bash
# Install with pip (requires Rust toolchain)
pip install rustkmer

# Or build from source
git clone https://github.com/yourorg/rustkmer
cd rustkmer
pip install -e .
```

## Quick Start

```python
from rustkmer import Database, KmerCounter, FuzzyQuery
import tempfile
import os

# Create a test database
temp_dir = tempfile.mkdtemp()
db_file = os.path.join(temp_dir, "test.rkdb")

# Count k-mers from sequence
counter = KmerCounter(k=21)
counter.count_string("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")
counter.save_to_database(db_file)

# Query existing database
db = Database(db_file)
result = db.query("ATCGATCGATCGATCGATCGA")
if result.found:
    print(f"K-mer found with count: {result.count}")
    # Output: K-mer found with count: 92

# Batch query multiple k-mers
kmers = ["ATCGATCGATCGATCGATCGA", "TTTTTTTTTTTTTTTTTTTTT"]
results = db.query_batch(kmers)
for kmer, result in results.items():
    print(f"{kmer}: found={result.found}, count={result.count}")

# Fuzzy search for similar k-mers
fq = FuzzyQuery(database=db, max_distance=2)
result = fq.find_similar("ATCGATCGATCGATCGATCGATC", max_results=5)
print(f"Found {result.total_matches} similar k-mers")
for match in result.matches:
    print(f"{match.kmer}: distance={match.distance}, count={match.count}")

# Clean up
import shutil
shutil.rmtree(temp_dir)
```

## Core Classes

### Database

The `Database` class provides read-only access to RKDB database files for querying k-mers.

#### Loading a Database

```python
from rustkmer import Database
import tempfile
import os

# Create a test database
temp_dir = tempfile.mkdtemp()
db_file = os.path.join(temp_dir, "test.rkdb")

# Create database with KmerCounter
from rustkmer import KmerCounter
counter = KmerCounter(k=21)
counter.count_string("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")
counter.save_to_database(db_file)

# Load database
db = Database(db_file)

# Get database statistics
stats = db.get_stats()
print(f"K-mer size: {stats.kmer_size}")  # Output: K-mer size: 21
print(f"Total k-mers: {stats.total_kmers}")  # Output: Total k-mers: 24
print(f"Unique k-mers: {stats.unique_kmers}")  # Output: Unique k-mers: 24
```

#### Single K-mer Query

```python
# Query a single k-mer
result = db.query("ATCGATCGATCGATCGATCGA")

# Access result properties
print(f"K-mer: {result.kmer}")          # Output: K-mer: ATCGATCGATCGATCGATCGA
print(f"Found: {result.found}")         # Output: Found: True
print(f"Count: {result.count}")         # Output: Count: 92

# Boolean check for convenience
if result.found:
    print(f"Found with count: {result.count}")
else:
    print("K-mer not found in database")
```

#### Batch Querying

```python
# Query multiple k-mers at once
kmers = [
    "ATCGATCGATCGATCGATCGA",
    "GCTAGCTAGCTAGCTAGCTAGC",
    "TTTTTTTTTTTTTTTTTTTTT",  # Not in database
]

results = db.query_batch(kmers)

# Results is a dictionary mapping k-mers to QueryResult objects
for kmer, result in results.items():
    if result.found:
        print(f"✅ {kmer}: {result.count} occurrences")
    else:
        print(f"❌ {kmer}: not found")
```

#### Query Helper Methods

```python
# Check if a k-mer exists (returns boolean)
exists = db.exists("ATCGATCGATCGATCGATCGA")
print(f"Exists: {exists}")  # Output: Exists: True

# Get count directly (returns int, 0 if not found)
count = db.get_count("ATCGATCGATCGATCGATCGA")
print(f"Count: {count}")  # Output: Count: 92

# More efficient for simple existence checks
if db.exists("ATCGATCGATCGATCGATCGA"):
    count = db.get_count("ATCGATCGATCGATCGATCGA")
    print(f"Found with count: {count}")
```

#### Error Handling

```python
from rustkmer.exceptions import ValidationError

try:
    # Wrong k-mer length (database has k=21)
    result = db.query("ATCG")  # Only 4 bases
except ValidationError as e:
    print(f"Validation error: {e}")
    # Output: Validation error: K-mer length doesn't match database k-mer size

try:
    # Invalid characters
    result = db.query("ATCGXATCGATCGATCGATCGA")  # X is invalid
except ValidationError as e:
    print(f"Validation error: {e}")
    # Output: Validation error: contains invalid characters

try:
    # Empty k-mer
    result = db.query("")
except ValidationError as e:
    print(f"Validation error: {e}")
    # Output: Validation error: Empty k-mer sequence
```

#### Database Statistics

```python
# Get comprehensive database statistics
stats = db.get_stats()

print(f"Database Statistics:")
print(f"  K-mer size: {stats.kmer_size}")
print(f"  Total k-mers (with duplicates): {stats.total_kmers}")
print(f"  Unique k-mers: {stats.unique_kmers}")
print(f"  Minimum count: {stats.min_count}")
print(f"  Maximum count: {stats.max_count}")
print(f"  Mean count: {stats.mean_count:.2f}")
print(f"  Sum of all counts: {stats.sum_counts}")
```

#### Context Manager Usage

```python
# Use Database with context manager for automatic cleanup
with Database() as db:
    db.load(db_file)
    result = db.query("ATCGATCGATCGATCGATCGA")
    print(f"Found: {result.found}")
# Database is automatically closed

# Or initialize directly with path
db = Database(db_file)
result = db.query("ATCGATCGATCGATCGATCGA")
db.close()  # Manual cleanup when done
```

#### Thread Safety

For concurrent access, use the thread-safe wrapper:

```python
from rustkmer import Database, make_thread_safe
import threading

# Create thread-safe wrapper
db = Database("data.rkdb")
safe_db = make_thread_safe(db)

# Safe to use from multiple threads
def query_worker():
    result = safe_db.query("ATCGATCGATCGATCGATCGATC")
    print(f"Thread {threading.current_thread().name}: {result.count}")

threads = [threading.Thread(target=query_worker) for _ in range(4)]
for t in threads:
    t.start()
for t in threads:
    t.join()
```

### KmerCounter

Count k-mers from sequences and save to RKDB format.

```python
from rustkmer import KmerCounter

# Create counter
counter = KmerCounter(k=21, canonical=True)  # Use canonical k-mers

# Count from FASTA/FASTQ file
counter.count_file("sequences.fasta")

# Count from string
counter.count_string("ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG")

# Count from iterable
sequences = ["ATCGATCG", "GCTAGCTA", "ATCGATCG"]
counter.count_iterable(sequences)

# Save to database
counter.save_to_database("counts.rkdb")

# Get statistics
stats = counter.get_stats()
print(f"Total k-mers: {stats.total_kmers}")
print(f"Unique k-mers: {stats.unique_kmers}")
```

### FuzzyQuery

Find similar k-mers using wildcard patterns or Hamming distance for approximate matching.

#### Initialization and Setup

```python
from rustkmer import Database, FuzzyQuery
import tempfile
import os

# Create a test database
temp_dir = tempfile.mkdtemp()
db_file = os.path.join(temp_dir, "test.rkdb")

from rustkmer import KmerCounter
counter = KmerCounter(k=21)
sequence = (
    "ATCGATCGATCGATCGATCGATC" * 10 +
    "ATCGATCGATCGATCGATCGATT" +  # One mutation
    "ATCGATCGATCGATCGATCGATG" +  # One mutation
    "GCTAGCTAGCTAGCTAGCTAGCT" * 5
)
counter.count_string(sequence)
counter.save_to_database(db_file)

# Load database
db = Database(db_file)

# Initialize FuzzyQuery with database
fq = FuzzyQuery(database=db, max_distance=2)

# Check properties
print(f"Max distance: {fq.get_max_distance()}")  # Output: Max distance: 2
print(f"K-mer size: {fq.get_kmer_size()}")      # Output: K-mer size: 21
print(f"Canonical: {fq.is_canonical()}")        # Output: Canonical: False

# Can also set database later
fq2 = FuzzyQuery(max_distance=3)
fq2.set_database(db)
```

#### Exact Match Search

```python
# Search for exact match (no wildcards)
result = fq.search("ATCGATCGATCGATCGATCGATC")

print(f"Pattern: ATCGATCGATCGATCGATCGATC")
print(f"Total matches: {result.total_matches}")  # Output: Total matches: 1

# Access matches
for match in result.matches:
    print(f"K-mer: {match.kmer}")
    print(f"Count: {match.count}")
    print(f"Distance: {match.distance}")
    # Output:
    # K-mer: ATCGATCGATCGATCGATCGATC
    # Count: 10
    # Distance: 0
```

#### Wildcard Search

```python
# Search with wildcard (*) - matches any characters at that position
result = fq.search("ATCGATCGATCGATCGATC*")

print(f"Pattern: ATCGATCGATCGATCGATC*")
print(f"Total matches: {result.total_matches}")  # Output: Total matches: 3

# Access matches
for match in result.matches:
    print(f"K-mer: {match.kmer}, Count: {match.count}, Distance: {match.distance}")
    # Output:
    # K-mer: ATCGATCGATCGATCGATCGATC, Count: 10, Distance: 1
    # K-mer: ATCGATCGATCGATCGATCGATT, Count: 1, Distance: 1
    # K-mer: ATCGATCGATCGATCGATCGATG, Count: 1, Distance: 1
```

#### Find Similar K-mers

```python
# Find k-mers similar to a query within max distance
result = fq.find_similar("ATCGATCGATCGATCGATCGATC", max_results=5)

print(f"Query: ATCGATCGATCGATCGATCGATC")
print(f"Total matches: {result.total_matches}")  # Output: Total matches: 3

# Access matches sorted by distance
for match in result.matches:
    print(f"K-mer: {match.kmer}")
    print(f"Count: {match.count}")
    print(f"Distance: {match.distance}")
    # Output:
    # K-mer: ATCGATCGATCGATCGATCGATC, Count: 10, Distance: 0
    # K-mer: TTCGATCGATCGATCGATCGATC, Count: 1, Distance: 1
```

#### Adjusting Search Parameters

```python
# Set maximum distance for fuzzy matching
fq.set_max_distance(3)
print(f"New max distance: {fq.get_max_distance()}")  # Output: New max distance: 3

# Search with adjusted parameters
result = fq.search("ATCGATCGATCGATCG*", max_results=10)
print(f"Found {result.total_matches} matches with distance <= 3")
```

#### Result Object Structure

```python
result = fq.search("ATCGATCGATCGATCGATC*")

# Total number of matches
print(f"Total matches: {result.total_matches}")

# List of individual matches
for match in result.matches:
    print(f"\nMatch details:")
    print(f"  K-mer: {match.kmer}")
    print(f"  Count: {match.count}")
    print(f"  Distance: {match.distance}")

# Each match is a FuzzyMatch object with:
# - kmer: the k-mer sequence
# - count: occurrence count in database
# - distance: edit distance from query pattern

# Query pattern used
print(f"Query pattern: {result.query_pattern}")
```

#### Error Handling

```python
from rustkmer.exceptions import RuntimeError

# FuzzyQuery requires a database
fq_no_db = FuzzyQuery(max_distance=2)

try:
    result = fq_no_db.search("ATCG*ATCG")
except RuntimeError as e:
    print(f"Error: {e}")
    # Output: Error: No database set

# Set database and retry
fq_no_db.set_database(db)
result = fq_no_db.search("ATCG*ATCG")
print(f"Success! Found {result.total_matches} matches")

# Invalid patterns (too many wildcards)
try:
    result = fq.search("****************")  # Many wildcards
except ValueError as e:
    print(f"Error: {e}")
    # Output: Error: too many wildcards in pattern: 16 (max 8)
```

#### Practical Examples

##### Example 1: Find Variants of a K-mer

```python
# Given a query k-mer, find all variants with up to 2 mutations
query = "ATCGATCGATCGATCGATCGATC"
result = fq.find_similar(query, max_distance=2, max_results=100)

print(f"Variants of {query}:")
print(f"Found {result.total_matches} variants")

# Group by distance
distance_groups = {}
for match in result.matches:
    dist = match.distance
    if dist not in distance_groups:
        distance_groups[dist] = []
    distance_groups[dist].append(match)

for distance in sorted(distance_groups.keys()):
    matches = distance_groups[distance]
    print(f"\nDistance {distance}: {len(matches)} variants")
    for match in matches[:5]:  # Show first 5
        print(f"  {match.kmer} (count: {match.count})")
```

##### Example 2: Search for Motif Variants

```python
# Search for motif with flexible positions
motif = "ATCG*ATCG*ATCG"

# Create separate database for motif searching
counter = KmerCounter(k=21)
motif_sequence = "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG"
counter.count_string(motif_sequence)
counter.save_to_database(db_file)

db2 = Database(db_file)
fq2 = FuzzyQuery(database=db2, max_distance=1)

result = fq2.search(motif, max_results=50)
print(f"Motif pattern: {motif}")
print(f"Found {result.total_matches} matching k-mers")

for match in result.matches[:10]:
    print(f"  {match.kmer}")
```

##### Example 3: Compare K-mer Frequencies

```python
# Find similar k-mers and analyze their counts
query = "ATCGATCGATCGATCGATCGATC"
result = fq.find_similar(query, max_distance=2, max_results=20)

print(f"Frequency analysis for variants of {query}:")
print(f"{'K-mer':<25} {'Count':<10} {'Distance':<10}")
print("-" * 45)

for match in result.matches:
    print(f"{match.kmer:<25} {match.count:<10} {match.distance:<10}")

# Find most frequent variant
if result.matches:
    most_frequent = max(result.matches, key=lambda m: m.count)
    print(f"\nMost frequent variant: {most_frequent.kmer}")
    print(f"Count: {most_frequent.count}, Distance: {most_frequent.distance}")
```

## Export Functionality

Export database contents to various formats with optional compression.

```python
from rustkmer import Database, export_to_json, export_to_csv
from rustkmer.export import ExportConfig, CompressionFormat, OutputFormat

# Using convenience functions
export_to_json(db, "export.json", compression=CompressionFormat.GZIP)
export_to_csv(db, "export.csv")
export_to_tsv(db, "export.tsv")

# Using advanced configuration
config = ExportConfig(
    format=OutputFormat.JSON,
    compression=CompressionFormat.GZIP,
    compression_level=9,
    min_count=5,
    max_count=1000,
    sort_by='count',
    reverse=True
)

exporter = DatabaseExporter(db, config)
stats = exporter.export("compressed_export.json")

print(f"Exported {stats.exported_kmers} k-mers")
print(f"Compression ratio: {stats.compression_ratio:.2f}")
```

## Error Handling

The API uses comprehensive error handling with specific exception types:

```python
from rustkmer import Database
from rustkmer.exceptions import DatabaseError, ValidationError, QueryError

try:
    db = Database("nonexistent.rkdb")
except DatabaseError as e:
    print(f"Database error: {e.error_code} - {e}")
    if e.error_code == "FILE_NOT_FOUND":
        print("Please check the file path")

try:
    db.query("INVALID_KMER")
except ValidationError as e:
    print(f"Validation error: {e.error_code}")
    print(f"Parameter: {e.parameter}")
```

## Performance Considerations

### Memory Usage

- Use memory-mapped files for large databases
- Batch queries are more efficient than individual queries
- Thread-safe operations have minimal overhead for read operations

### Query Optimization

```python
# Good: Batch queries
kmers = ["ATCGATCG", "GCTAGCTA"] * 1000
results = db.query_batch(kmers)

# Good: Use canonical k-mers when possible
counter = KmerCounter(k=31, canonical=True)

# Good: Thread-safe wrapper for concurrent access
safe_db = make_thread_safe(db)
```

## Examples

### Basic Workflow

```python
from rustkmer import KmerCounter, Database

# 1. Count k-mers from sequences
counter = KmerCounter(k=31)
counter.count_file("genome.fasta")

# 2. Save to database
counter.save_to_database("genome.rkdb")

# 3. Query the database
db = Database("genome.rkdb")

# 4. Find frequent k-mers
stats = db.get_stats()
print(f"Most common k-mers have count ~{stats.max_count}")

# 5. Export for analysis
db.dump("frequent_kmers.txt", min_count=100)
```

### Comparative Analysis

```python
from rustkmer import Database

# Load multiple databases
databases = [
    Database("sample1.rkdb"),
    Database("sample2.rkdb"),
    Database("sample3.rkdb")
]

# Compare statistics
for i, db in enumerate(databases, 1):
    stats = db.get_stats()
    print(f"Sample {i}: {stats.total_kmers} total, {stats.unique_kmers} unique")

# Find shared k-mers (requires manual comparison)
all_kmers = set()
for db in databases:
    # This would require an iterator implementation
    pass
```

## API Reference

### Database Class

The `Database` class provides methods for querying k-mer databases.

#### Methods

| Method | Description | Parameters | Returns |
|--------|-------------|------------|--------|
| `__init__(path=None)` | Initialize Database | `path: str, optional` | `Database` |
| `load(path)` | Load database from file | `path: str` | `None` |
| `query(kmer)` | Query single k-mer | `kmer: str` | `QueryResult` |
| `query_batch(kmers)` | Query multiple k-mers | `kmers: List[str]` | `Dict[str, QueryResult]` |
| `query_multiple(kmers)` | Query multiple k-mers | `kmers: List[str]` | `List[QueryResult]` |
| `exists(kmer)` | Check if k-mer exists | `kmer: str` | `bool` |
| `get_count(kmer)` | Get k-mer count | `kmer: str` | `int` |
| `get_stats()` | Get database statistics | None | `DatabaseStats` |
| `close()` | Close database and free resources | None | `None` |

#### Usage Examples

```python
# Initialize and load
db = Database()
db.load("database.rkdb")

# Query single k-mer
result = db.query("ATCGATCGATCGATCGATCGATC")

# Batch query
results = db.query_batch(["ATCGATCGATCGATCGATCGA", "GCTAGCTAGCTAGCTAGCTAGC"])

# Check existence
if db.exists("ATCGATCGATCGATCGATCGA"):
    count = db.get_count("ATCGATCGATCGATCGATCGA")

# Get statistics
stats = db.get_stats()
print(f"Unique k-mers: {stats.unique_kmers}")

# Clean up
db.close()
```

### QueryResult Class

Represents the result of a k-mer query.

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `kmer` | str | The queried k-mer sequence |
| `count` | int | K-mer occurrence count (0 if not found) |
| `found` | bool | Whether k-mer was found in database |
| `exists` | bool | Alias for `found` (for compatibility) |

#### Methods

| Method | Description | Returns |
|--------|-------------|--------|
| `get_kmer()` | Get k-mer sequence | `str` |
| `get_count()` | Get count | `int` |
| `get_exists()` | Get existence status | `bool` |

#### Usage Examples

```python
result = db.query("ATCGATCGATCGATCGATCGA")

# Access attributes
print(result.kmer)      # "ATCGATCGATCGATCGATCGA"
print(result.count)     # 92
print(result.found)     # True

# Use as boolean
if result:
    print(f"Found with count: {result.count}")

# Get data via methods
kmer = result.get_kmer()
count = result.get_count()
exists = result.get_exists()
```

### DatabaseStats Class

Contains database statistics and metadata.

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `kmer_size` | int | Size of k-mers in database |
| `total_kmers` | int | Total k-mer count (including duplicates) |
| `unique_kmers` | int | Number of unique k-mers |
| `min_count` | int | Minimum k-mer count |
| `max_count` | int | Maximum k-mer count |
| `mean_count` | float | Mean k-mer count |
| `sum_counts` | int | Sum of all counts |

#### Usage Examples

```python
stats = db.get_stats()

print(f"Database: {stats.kmer_size}-mers")
print(f"Total occurrences: {stats.total_kmers:,}")
print(f"Unique sequences: {stats.unique_kmers:,}")
print(f"Average count: {stats.mean_count:.2f}")
print(f"Range: {stats.min_count} - {stats.max_count}")
```

### FuzzyQuery Class

Provides fuzzy matching and wildcard search capabilities for k-mers.

#### Constructor

```python
FuzzyQuery(database=None, max_mutations=1, max_results=100, max_distance=3)
```

**Parameters:**
- `database`: Database instance to query (optional, can be set later)
- `max_mutations`: Maximum number of mutations (alias for max_distance)
- `max_results`: Maximum number of results to return
- `max_distance`: Maximum edit distance for fuzzy matching

#### Methods

| Method | Description | Parameters | Returns |
|--------|-------------|------------|--------|
| `search(pattern, max_results=None)` | Search with wildcard pattern | `pattern: str`, `max_results: int, optional` | `FuzzyQueryResult` |
| `find_similar(kmer, max_distance=None, max_results=None)` | Find similar k-mers | `kmer: str`, `max_distance: int, optional`, `max_results: int, optional` | `FuzzyQueryResult` |
| `set_database(database)` | Set database | `database: Database` | `None` |
| `get_max_distance()` | Get max distance | None | `int` |
| `set_max_distance(distance)` | Set max distance | `distance: int` | `None` |
| `get_kmer_size()` | Get database k-mer size | None | `int` |
| `is_canonical()` | Check if database uses canonical k-mers | None | `bool` |

#### Usage Examples

```python
# Initialize
fq = FuzzyQuery(database=db, max_distance=2)

# Wildcard search
result = fq.search("ATCG*ATCG*ATCG")
for match in result.matches:
    print(f"{match.kmer}: {match.count}")

# Find similar k-mers
result = fq.find_similar("ATCGATCGATCGATCGATCGATC", max_results=10)
for match in result.matches:
    print(f"{match.kmer}: distance={match.distance}")

# Adjust parameters
fq.set_max_distance(3)
result = fq.search("ATCG*", max_results=50)
```

### FuzzyQueryResult Class

Contains results from a fuzzy query operation.

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `query_pattern` | str | The query pattern used |
| `total_matches` | int | Total number of matches found |
| `matches` | List[FuzzyMatch] | List of individual matches |

#### Usage Examples

```python
result = fq.search("ATCG*ATCG")

print(f"Pattern: {result.query_pattern}")
print(f"Found: {result.total_matches} matches")

for match in result.matches:
    print(f"  {match.kmer} (count: {match.count}, distance: {match.distance})")
```

### FuzzyMatch Class

Represents a single match from a fuzzy query.

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `kmer` | str | The matching k-mer sequence |
| `count` | int | K-mer occurrence count in database |
| `distance` | int | Edit distance from query pattern |

#### Usage Examples

```python
result = fq.search("ATCG*ATCG")

for match in result.matches:
    print(f"K-mer: {match.kmer}")
    print(f"Frequency: {match.count}")
    print(f"Distance: {match.distance}")
```

## Thread Safety

All Database operations are thread-safe when using the `ThreadSafeDatabase` wrapper:

```python
from rustkmer import Database, make_thread_safe
from rustkmer.thread_safety import ThreadSafeDatabase

# Option 1: Wrapper function
safe_db = make_thread_safe(Database("data.rkdb"))

# Option 2: Direct class
safe_db = ThreadSafeDatabase(Database("data.rkdb"))

# Multiple threads can safely query
def worker(thread_id, db):
    result = db.query("ATCGATCGATCGATCGATCGATC")
    print(f"Thread {thread_id}: {result.count}")

import threading
threads = []
for i in range(10):
    t = threading.Thread(target=worker, args=(i, safe_db))
    t.start()
    threads.append(t)

for t in threads:
    t.join()
```

## Best Practices

1. **Use canonical k-mers** when possible to reduce database size
2. **Batch queries** for better performance
3. **Close databases** when done to free resources
4. **Use thread-safe wrapper** for concurrent access
5. **Handle errors gracefully** with specific exception types
6. **Export with compression** for large datasets
7. **Memory-map large files** automatically handled based on size

## Troubleshooting

### Common Issues

1. **ImportError**: Ensure Rust toolchain is installed and Python environment is activated
2. **File not found**: Check file paths and ensure `.rkdb` extension
3. **Memory errors**: Use smaller batch sizes or memory-mapped files
4. **Performance issues**: Use batch queries and consider thread-safe concurrent access

### Debug Mode

```python
import rustkmer
rustkmer.enable_debug_mode()
rustkmer.enable_trace_mode()
```

### Getting Help

- Check the RustKmer GitHub repository for issues and discussions
- Review test files in `python/tests/` for usage examples
- Use the exception messages and error codes for debugging