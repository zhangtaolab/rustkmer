# Database

The `Database` class is the main interface for interacting with rustkmer k-mer databases. It provides methods for querying k-mers, performing fuzzy searches, retrieving statistics, and dumping database contents.

## Database Class

### `rustkmer.database.Database`

```python
class Database:
    """Represents a rustkmer k-mer database."""
```

The `Database` class provides a high-level interface for working with rustkmer binary database (.rkdb) files through Python.

### Constructor

```python
Database.__init__(path: Union[str, Path], validate: bool = False)
```

Initialize a database connection with optional validation.

**Parameters:**
- `path` (Union[str, Path]): Path to the .rkdb database file
- `validate` (bool): Whether to fully validate database on initialization
  - `False` (default): Only checks if file exists and is readable
  - `True`: Performs full validation including stats check

**Raises:**
- `DatabaseNotFoundError`: If database file doesn't exist
- `InvalidDatabaseError`: If file is not a valid database (when validate=True)

**Example:**
```python
from rustkmer import Database

# Basic initialization (recommended for performance)
db = Database("example.rkdb")

# Initialize with full validation
db = Database("example.rkdb", validate=True)
```

### Properties

#### `path: Path`

Get the path to the database file.

**Returns:**
- `Path`: The database file path

**Example:**
```python
db = Database("example.rkdb")
print(f"Database path: {db.path}")
```

#### `kmer_size: Optional[int]`

Get the length of k-mers in the database. Returns `None` until metadata is loaded.

**Returns:**
- `Optional[int]`: K-mer length or None if not yet loaded

**Example:**
```python
db = Database("example.rkdb")
print(f"K-mer size: {db.kmer_size}")  # Will load metadata if needed
```

#### `is_loaded: bool`

Check if database metadata has been loaded.

**Returns:**
- `bool`: True if metadata is loaded, False otherwise

### Methods

#### Query Methods

##### `query(kmer: str, validate_strict: bool = True) -> QueryResult`

Query a single k-mer in the database for exact matches.

**Parameters:**
- `kmer` (str): The k-mer sequence to query
- `validate_strict` (bool):
  - `True` (default): Raise exceptions for invalid k-mers
  - `False`: Return count=0 for invalid k-mers

**Returns:**
- `QueryResult`: Object containing the k-mer information

**Raises:**
- `InvalidKmerError`: If k-mer is invalid and validate_strict=True
- `QueryError`: If query fails
- `DatabaseError`: If database is closed

**Example:**
```python
db = Database("example.rkdb")

# Strict validation (default)
result = db.query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
print(f"Count: {result.count}")
print(f"Canonical: {result.canonical}")

# Non-strict validation
result = db.query("ATXG", validate_strict=False)
print(f"Count: {result.count}")  # Returns 0 for invalid k-mers
```

##### `fuzzy_query(kmer: str, mutations: int = 1, max_variants: Optional[int] = None, output_format: str = 'auto', position_mutations: Optional[str] = None) -> FuzzyQueryResult`

Perform a fuzzy k-mer query with mutation tolerance.

**Parameters:**
- `kmer` (str): The k-mer sequence to query
- `mutations` (int): Maximum number of mutations allowed (0-5, default=1)
- `max_variants` (Optional[int]): Maximum number of variants to generate and check
- `output_format` (str): CLI output format ('auto', 'json', 'table', 'tsv')
- `position_mutations` (Optional[str]): Position-specific mutation constraints

**Position Mutations Format:**
- `"4:1"` - Position 4 with max 1 mutation
- `"3,4,5:2"` - Positions 3,4,5 with max 2 mutations total
- `"4-7:1"` - Positions 4,5,6,7 with max 1 mutation (range notation)
- `"3,4:1;6,7:2"` - Multiple independent groups

**Returns:**
- `FuzzyQueryResult`: Object containing all matches within mutation tolerance

**Raises:**
- `InvalidKmerError`: If k-mer contains invalid characters
- `InvalidMutationToleranceError`: If mutations not in range 0-5
- `InvalidPositionMutationError`: If position_mutations format is invalid
- `DatabaseError`: If database is closed
- `QueryError`: If CLI command fails

**Examples:**
```python
db = Database("example.rkdb")

# Exact match only
result = db.fuzzy_query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG", mutations=0)

# Allow up to 2 mutations
result = db.fuzzy_query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG", mutations=2)
print(f"Found {result.total_matches} matches")

# Get top 5 most abundant matches
top_matches = result.get_top_matches(5)
for match in top_matches:
    print(f"{match.kmer}: {match.count} (distance={match.distance})")

# Position-specific mutations
result = db.fuzzy_query(
    "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
    position_mutations="10,15:2"  # Allow 2 mutations at positions 10 and 15
)
```

##### `fuzzy_query_batch(kmers: List[str], mutations: int = 1, max_variants: Optional[int] = None, max_workers: int = 4, output_format: str = 'auto', position_mutations: Optional[str] = None) -> FuzzyBatchResult`

Perform fuzzy queries on multiple k-mers in parallel.

**Parameters:**
- `kmers` (List[str]): List of k-mer sequences to query
- `mutations` (int): Maximum number of mutations allowed (0-5, default=1)
- `max_variants` (Optional[int]): Maximum number of variants per query
- `max_workers` (int): Maximum number of parallel workers (default=4)
- `output_format` (str): CLI output format ('auto', 'json', 'table', 'tsv')
- `position_mutations` (Optional[str]): Position-specific mutation constraints

**Returns:**
- `FuzzyBatchResult`: Results for all queries including successes and failures

**Example:**
```python
db = Database("example.rkdb")
kmers = ["ATCGATCGATCGATCGATCGATCGATCGATCGATCG", "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA"]

results = db.fuzzy_query_batch(kmers, mutations=2, max_workers=8)
for kmer, result in results.successes.items():
    print(f"{kmer}: {result.total_matches} matches")
```

#### Database Information

##### `stats() -> DatabaseStats`

Retrieve database statistics including k-mer size, total k-mers, unique k-mers, and count distribution.

**Returns:**
- `DatabaseStats`: Object containing database statistics

**Example:**
```python
db = Database("example.rkdb")
stats = db.stats()
print(f"K-mer size: {stats.kmer_size}")
print(f"Total k-mers: {stats.total_kmers}")
print(f"Unique k-mers: {stats.unique_kmers}")
print(f"Total count: {stats.total_count}")
```

##### `dump(limit: Optional[int] = None, canonical_only: bool = False, output_format: str = 'auto') -> Iterator[DumpResult]`

Dump database contents as an iterator of k-mer results.

**Parameters:**
- `limit` (Optional[int]): Maximum number of results to return
- `canonical_only` (bool): Only return canonical k-mers
- `output_format` (str): CLI output format ('auto', 'json', 'table', 'tsv')

**Returns:**
- `Iterator[DumpResult]`: Iterator over k-mer entries in the database

**Example:**
```python
db = Database("example.rkdb")

# Dump first 1000 k-mers
for i, result in enumerate(db.dump(limit=1000)):
    print(f"{result.kmer}: {result.count}")
    if i >= 10:  # Print first 10 for demo
        break

# Dump only canonical k-mers
for result in db.dump(canonical_only=True):
    print(f"Canonical: {result.kmer}")
```

#### Context Manager

##### `__enter__() -> Database`

Enter the runtime context for the database.

##### `__exit__(exc_type, exc_val, exc_tb) -> None`

Exit the runtime context and close the database.

**Example:**
```python
from rustkmer import Database

# Using context manager (recommended)
with Database("example.rkdb") as db:
    count = db.query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG").count
    print(f"K-mer count: {count}")
# Database automatically closed

# Manual management
db = Database("example.rkdb")
try:
    count = db.query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG").count
    print(f"K-mer count: {count}")
finally:
    db.close()
```

#### Resource Management

##### `close()`

Close the database and free resources. After closing, the database cannot be used for queries.

**Example:**
```python
db = Database("example.rkdb")
try:
    result = db.query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
    print(f"Count: {result.count}")
finally:
    db.close()  # Always close to free resources
```

## Performance Considerations

### Database Initialization

- Use `validate=False` (default) for better performance when opening databases
- Only use `validate=True` when you need to verify database integrity

### Query Performance

- Exact queries (`query()`) are much faster than fuzzy queries
- Fuzzy queries generate combinatorial variants; use `max_variants` to limit computational cost
- Lower mutation tolerances in fuzzy queries are faster
- Batch queries (`fuzzy_query_batch()`) are more efficient for multiple k-mers

### Memory Usage

- Database metadata is loaded lazily (when first needed)
- Dump operations stream results to minimize memory usage
- Large fuzzy queries can be memory-intensive due to variant generation

## Error Handling

### Common Exceptions

- `DatabaseNotFoundError`: Database file doesn't exist
- `InvalidDatabaseError`: File is not a valid .rkdb database
- `InvalidKmerError`: K-mer contains invalid characters or wrong length
- `QueryError`: Query operation failed
- `DatabaseError`: Database is closed or invalid state

### Best Practices

```python
from rustkmer import Database, DatabaseNotFoundError, InvalidKmerError

try:
    db = Database("example.rkdb")

    # Handle specific errors
    try:
        result = db.query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
        print(f"Count: {result.count}")
    except InvalidKmerError as e:
        print(f"Invalid k-mer: {e.kmer}, reason: {e.reason}")

finally:
    db.close()
```

## Integration Examples

### Scientific Computing

```python
import numpy as np
from rustkmer import Database

def analyze_kmer_frequencies(db_path: str, kmers: List[str]) -> np.ndarray:
    """Get k-mer frequencies as numpy array."""
    db = Database(db_path)
    frequencies = []

    for kmer in kmers:
        result = db.query(kmer)
        frequencies.append(result.count)

    db.close()
    return np.array(frequencies)
```

### High-Throughput Analysis

```python
from concurrent.futures import ThreadPoolExecutor
from rustkmer import Database

def parallel_kmer_analysis(db_path: str, kmer_lists: List[List[str]]) -> List[dict]:
    """Analyze multiple k-mer lists in parallel."""

    def process_kmer_list(kmers: List[str]) -> dict:
        with Database(db_path) as db:
            results = db.fuzzy_query_batch(kmers, mutations=2)
            return {
                'total_queries': len(kmers),
                'successful_queries': len(results.successes),
                'total_matches': sum(r.total_matches for r in results.successes.values())
            }

    with ThreadPoolExecutor(max_workers=4) as executor:
        return list(executor.map(process_kmer_list, kmer_lists))
```

### Real-World Bioinformatics Workflows

#### Pandas Integration for K-mer Analysis

```python
import pandas as pd
from rustkmer import Database
from pathlib import Path

def analyze_multiple_samples(db_directory: str, queries: List[str]) -> pd.DataFrame:
    """Analyze k-mer presence across multiple samples using pandas."""

    db_files = list(Path(db_directory).glob("*.rkdb"))
    results = []

    for db_file in db_files:
        sample_name = db_file.stem
        sample_data = {'Sample': sample_name}

        with Database(db_file) as db:
            for query in queries:
                try:
                    result = db.query(query)
                    sample_data[query] = result.count
                except Exception as e:
                    sample_data[query] = 0

        results.append(sample_data)

    return pd.DataFrame(results)

# Usage
df = analyze_multiple_samples("results/databases/", [
    "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
    "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG"
])

# Analyze results
print("K-mer count matrix:")
print(df)
print("\nK-mer statistics:")
print(df.iloc[:, 1:].describe())
```

#### Database Comparison and Similarity Analysis

```python
from rustkmer import Database
import numpy as np
from sklearn.metrics import jaccard_score

def compute_sample_similarity(db_files: List[str], common_kmers: List[str]) -> np.ndarray:
    """Compute similarity matrix between samples based on k-mer presence."""

    n_samples = len(db_files)
    similarity_matrix = np.zeros((n_samples, n_samples))

    # Extract presence data for all samples
    presence_data = []
    for db_file in db_files:
        with Database(db_file) as db:
            presence = []
            for kmer in common_kmers:
                result = db.query(kmer)
                presence.append(1 if result.is_present else 0)
            presence_data.append(presence)

    # Compute pairwise similarities
    for i in range(n_samples):
        for j in range(n_samples):
            if i <= j:
                # Compute Jaccard similarity
                intersection = np.sum(np.logical_and(presence_data[i], presence_data[j]))
                union = np.sum(np.logical_or(presence_data[i], presence_data[j]))
                similarity = intersection / union if union > 0 else 0
                similarity_matrix[i, j] = similarity_matrix[j, i] = similarity

    return similarity_matrix

# Usage
db_files = ["sample1.rkdb", "sample2.rkdb", "sample3.rkdb"]
common_kmers = ["ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
                "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",
                "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"]

similarity_matrix = compute_sample_similarity(db_files, common_kmers)
print("Sample similarity matrix:")
print(similarity_matrix)
```

#### Large-Scale K-mer Mining

```python
from rustkmer import Database
from collections import Counter
import time

def find_abundant_kmers(db_path: str, min_count: int = 100, max_results: int = 1000) -> List[dict]:
    """Find highly abundant k-mers in the database."""

    abundant_kmers = []

    print(f"Mining abundant k-mers from {db_path}...")
    start_time = time.time()

    with Database(db_path) as db:
        # Stream through database to find abundant k-mers
        for result in db.dump():
            if result.count >= min_count:
                abundant_kmers.append({
                    'kmer': result.kmer,
                    'canonical': result.canonical,
                    'count': result.count
                })

                # Limit results to prevent memory issues
                if len(abundant_kmers) >= max_results:
                    break

        # Sort by count (descending)
        abundant_kmers.sort(key=lambda x: x['count'], reverse=True)

    mining_time = time.time() - start_time
    print(f"Found {len(abundant_kmers)} k-mers with count >= {min_count}")
    print(f"Mining completed in {mining_time:.1f} seconds")

    return abundant_kmers

# Usage
abundant_kmers = find_abundant_kmers("large_genome.rkdb", min_count=100)

# Display top 10
print("\nTop 10 most abundant k-mers:")
for i, kmer_data in enumerate(abundant_kmers[:10], 1):
    print(f"{i:2d}. {kmer_data['kmer']}: {kmer_data['count']:,}")
```

#### K-mer Pattern Discovery

```python
from rustkmer import Database
from Bio.Seq import reverse_complement
import re

def find_palindromic_kmers(db_path: str, min_count: int = 10) -> List[dict]:
    """Find palindromic k-mers in the database."""

    palindromes = []

    with Database(db_path) as db:
        for result in db.dump(canonical_only=True):
            if result.count < min_count:
                continue

            # Check if k-mer is palindromic
            seq = result.kmer.upper()
            rev_comp = str(reverse_complement(seq))

            if seq == rev_comp:
                palindromes.append({
                    'kmer': seq,
                    'count': result.count,
                    'length': len(seq)
                })

    return palindromes

def find_repeat_motifs(db_path: str, min_repeat_length: int = 3, min_count: int = 50) -> List[dict]:
    """Find k-mers containing repeat motifs."""

    repeat_kmers = []

    with Database(db_path) as db:
        for result in db.dump(canonical_only=True):
            if result.count < min_count:
                continue

            seq = result.kmer.upper()

            # Look for repeated patterns
            for length in range(min_repeat_length, len(seq) // 2 + 1):
                pattern = seq[:length]
                repeats = len(seq) // length

                if pattern * repeats == seq[:length * repeats]:
                    repeat_kmers.append({
                        'kmer': seq,
                        'count': result.count,
                        'pattern': pattern,
                        'repeat_count': repeats
                    })
                    break  # Only record the largest repeat pattern

    return repeat_kmers

# Usage
palindromes = find_palindromic_kmers("genome.rkdb", min_count=100)
print(f"Found {len(palindromes)} palindromic k-mers")

repeat_motifs = find_repeat_motifs("genome.rkdb", min_repeat_length=4)
print(f"Found {len(repeat_motifs)} k-mers with repeat motifs")
```

#### Performance Benchmarking

```python
from rustkmer import Database
import time
import random
import string

def benchmark_database_performance(db_path: str, num_queries: int = 10000) -> dict:
    """Benchmark database query performance."""

    # Generate random k-mers for testing
    with Database(db_path) as db:
        stats = db.stats()
        kmer_size = stats.kmer_size

    test_kmers = [''.join(random.choices('ATCG', k=kmer_size)) for _ in range(num_queries)]

    print(f"Benchmarking {num_queries} queries on {db_path}...")

    # Benchmark exact queries
    start_time = time.time()
    exact_results = []

    with Database(db_path) as db:
        for kmer in test_kmers:
            result = db.query(kmer)
            exact_results.append(result.count)

    exact_time = time.time() - start_time
    exact_queries_per_sec = num_queries / exact_time

    # Benchmark fuzzy queries (subset for performance)
    fuzzy_kmers = test_kmers[:100]  # Smaller subset for fuzzy queries

    start_time = time.time()
    fuzzy_results = []

    with Database(db_path) as db:
        for kmer in fuzzy_kmers:
            result = db.fuzzy_query(kmer, mutations=2)
            fuzzy_results.append(result.total_matches)

    fuzzy_time = time.time() - start_time
    fuzzy_queries_per_sec = len(fuzzy_kmers) / fuzzy_time

    # Return benchmark results
    return {
        'database_path': db_path,
        'kmer_size': kmer_size,
        'exact_queries': {
            'total_queries': num_queries,
            'time_seconds': exact_time,
            'queries_per_second': exact_queries_per_sec
        },
        'fuzzy_queries': {
            'total_queries': len(fuzzy_kmers),
            'mutations': 2,
            'time_seconds': fuzzy_time,
            'queries_per_second': fuzzy_queries_per_sec
        }
    }

# Usage
benchmark_results = benchmark_database_performance("genome.rkdb", num_queries=10000)
print(f"Exact query performance: {benchmark_results['exact_queries']['queries_per_second']:.0f} queries/sec")
print(f"Fuzzy query performance: {benchmark_results['fuzzy_queries']['queries_per_second']:.0f} queries/sec")
```

#### Memory-Efficient Large Database Analysis

```python
from rustkmer import Database
import psutil
import gc

def analyze_large_database_safely(db_path: str, progress_interval: int = 100000) -> dict:
    """Analyze large database with memory monitoring and safety checks."""

    def get_memory_usage():
        return psutil.Process().memory_info().rss / (1024**3)  # GB

    print(f"Analyzing large database: {db_path}")
    print(f"Initial memory usage: {get_memory_usage():.2f} GB")

    total_kmers = 0
    max_count = 0
    min_count = float('inf')
    kmer_size = None

    try:
        with Database(db_path) as db:
            # Get basic stats
            stats = db.stats()
            kmer_size = stats.kmer_size
            unique_kmers = stats.unique_kmers

            print(f"Database contains {unique_kmers:,} unique k-mers of size {kmer_size}")

            # Stream through k-mers with progress tracking
            for i, result in enumerate(db.dump(canonical_only=True)):
                total_kmers += 1
                max_count = max(max_count, result.count)
                min_count = min(min_count, result.count)

                # Progress update
                if i % progress_interval == 0:
                    memory_gb = get_memory_usage()
                    print(f"Processed {i:,} k-mers, Memory: {memory_gb:.2f} GB")

                    # Safety check: abort if memory usage gets too high
                    if memory_gb > 8.0:  # 8GB limit
                        print("WARNING: Memory usage too high, stopping analysis")
                        break

                # Periodic garbage collection
                if i % (progress_interval * 10) == 0:
                    gc.collect()

        print(f"Analysis completed successfully!")
        print(f"Total k-mers processed: {total_kmers:,}")
        print(f"Max count: {max_count:,}")
        print(f"Min count: {min_count:,}")
        print(f"Final memory usage: {get_memory_usage():.2f} GB")

        return {
            'total_kmers': total_kmers,
            'kmer_size': kmer_size,
            'max_count': max_count,
            'min_count': min_count,
            'unique_kmers': unique_kmers
        }

    except Exception as e:
        print(f"Error during analysis: {e}")
        return {'error': str(e), 'processed_kmers': total_kmers}