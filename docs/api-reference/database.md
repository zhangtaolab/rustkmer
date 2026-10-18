<!-- generated-by: gsd-doc-writer -->
# Database

The `PyDatabase` class is the main interface for interacting with rustkmer k-mer databases. It provides methods for querying k-mers, performing prefix and hybrid-pattern searches, retrieving statistics, dumping and exporting database contents, and merging databases.

## Database Class

### `pyrustkmer.PyDatabase`

The `PyDatabase` class provides a high-level interface for working with rustkmer binary database (`.rkdb`) files through Python. It wraps the same Rust `RKDatabase` core that the CLI uses.

### Constructor

```python
PyDatabase(path, load_mode)
```

Initialize a database connection. The loading mode is **required**.

**Parameters:**
- `path` (str): Path to the `.rkdb` database file
- `load_mode` (`LoadMode`): How the database is held in memory:
  - `LoadMode.Preload` — all k-mers cached in a sorted in-memory map (fastest queries, highest memory)
  - `LoadMode.MemoryMapped` — direct file I/O without a full in-memory cache (balanced memory/performance)
  - `LoadMode.Lazy` — a sorted index built for binary search (low memory, slightly slower queries)

**Raises:**
- `FileNotFoundError`: If the database file does not exist
- `ValueError`: If the file cannot be loaded as a valid database

**Example:**
```python
from pyrustkmer import PyDatabase, LoadMode

# Preload for repeated queries (recommended default)
db = PyDatabase("example.rkdb", LoadMode.Preload)

# Direct file access for large databases
db = PyDatabase("example.rkdb", LoadMode.MemoryMapped)

# Sorted-index binary search
db = PyDatabase("example.rkdb", LoadMode.Lazy)
```

### Properties

#### `path: str`

The database file path.

**Example:**
```python
db = PyDatabase("example.rkdb", LoadMode.Preload)
print(f"Database path: {db.path}")
```

#### `kmer_size: int`

The length of k-mers in the database (from the RKDB header).

#### `is_loaded: bool`

Whether the database has been loaded. Always `True` for a successfully constructed `PyDatabase`.

#### `total_kmers: int`

Total number of k-mers recorded in the database header.

#### `unique_kmers: int`

Number of unique k-mers recorded in the database header.

#### `canonical: bool`

Whether the database stores canonical k-mers.

#### `load_mode: LoadMode`

The loading mode this instance was constructed with.

### Query Methods

#### `query_exact(kmer) -> PyQueryResult`

Query a single k-mer for an exact match. If the database stores canonical k-mers, the query k-mer is canonicalized before lookup.

**Parameters:**
- `kmer` (str): The k-mer sequence (A, T, C, G; lower-case input is upper-cased)

**Returns:**
- `PyQueryResult`: Object with `kmer`, `count`, and `found` attributes

**Raises:**
- `ValueError`: If the k-mer length does not match the database k-mer size, or the k-mer contains characters other than A/T/C/G

**Example:**
```python
db = PyDatabase("example.rkdb", LoadMode.Preload)

result = db.query_exact("ATCGATCGATCGATCGATCG")
print(f"Count: {result.count}")
print(f"Found: {result.found}")

if db.exists("ATCGATCGATCGATCGATCG"):
    print("K-mer is present")
```

#### `query_exact_batch(kmers) -> Dict[str, PyQueryResult]`

Query multiple k-mers in one call.

**Parameters:**
- `kmers` (List[str]): List of k-mer sequences

**Returns:**
- `Dict[str, PyQueryResult]`: Mapping from each input k-mer to its result

**Raises:**
- `ValueError`: If any k-mer is invalid (the error names the failing input)

**Example:**
```python
results = db.query_exact_batch([
    "ATCGATCGATCGATCGATCG",
    "GCTAGCTAGCTAGCTAGCTA",
])
for kmer, result in results.items():
    print(f"{kmer}: count={result.count}, found={result.found}")
```

#### `query_prefix(prefix) -> PyPrefixQueryResult`

Optimized prefix query returning matches plus memory-block metrics.

**Parameters:**
- `prefix` (str): Prefix of A/T/C/G characters; an empty prefix returns an empty result

**Returns:**
- `PyPrefixQueryResult`: Object with `matches` (dict of k-mer to count string), `total_matches`, `query_time_ms`, `start_index`, `end_index`, `block_size`, and `is_sorted`

**Raises:**
- `ValueError`: If the prefix contains characters other than A/T/C/G
- `RuntimeError`: If the prefix query engine fails

#### `query_prefix_batch(prefixes) -> List[PyPrefixQueryResult]`

Run `query_prefix` for a list of prefixes.

#### `query_hybrid(pattern) -> Dict[str, str]`

Hybrid-pattern query supporting spacer notation such as `ATAC{N5}ACAC`.

**Parameters:**
- `pattern` (str): Pattern with fixed prefix/suffix and `{N<n>}` spacers

**Returns:**
- `Dict[str, str]`: Mapping of matching k-mer to count (as string)

**Raises:**
- `ValueError`: If the pattern is empty or invalid
- `RuntimeError`: If the hybrid query fails

#### `extract_by_prefix(prefix) -> Dict[str, str]`

Simple prefix extraction returning matching k-mers and counts.

**Returns:**
- `Dict[str, str]`: Mapping of k-mer to count (as string); an empty prefix returns an empty dict

#### `extract_by_pattern(pattern) -> Dict[str, str]`

Hybrid-pattern extraction (same grammar as `query_hybrid`).

#### `parse_pattern(pattern) -> Dict[str, str]`

Parse a hybrid pattern without executing a query. Returns keys `prefix`, `suffix`, `n_count`, `total_length`, and `n_positions`.

#### `query_fuzzy(pattern, max_mutations) -> PyFuzzyResult`

A fuzzy-query convenience method on the database object. The full fuzzy engine — including `max_results` and position-mutation constraints — lives in [`PyFuzzyQuery`](fuzzyquery.md), which takes a `PyDatabase` in its constructor and is the recommended interface.

#### Deprecated query methods

`query()`, `query_batch()`, `query_prefix_optimized()`, and `fuzzy_query()` are deprecated aliases of the methods above and will be removed in a future release.

### Database Information

#### `get_stats() -> PyDatabaseStats`

Retrieve database statistics from the header.

**Returns:**
- `PyDatabaseStats`: Object with `kmer_size`, `total_kmers`, `unique_kmers`, `file_size`, `is_sorted`, and `canonical` attributes (see [DatabaseStats](stats.md))

**Example:**
```python
stats = db.get_stats()
print(f"K-mer size: {stats.kmer_size}")
print(f"Total k-mers: {stats.total_kmers}")
print(f"Unique k-mers: {stats.unique_kmers}")
```

#### `database_info() -> Dict[str, str]`

Summary dict with `database_path`, `kmer_size`, `is_loaded`, `total_kmers`, `unique_kmers`, and `load_mode`.

#### `get_memory_usage() -> Dict[str, str]`

Mode-specific memory information (`mode`, plus `cache_size` for Preload or `loaded_entries`/`cached_entries` for Lazy).

#### `get_entry_by_index(index) -> Tuple[int, int]`

Direct file access to a single entry, returning `(encoded_kmer, count)`. Only available in `LoadMode.MemoryMapped` mode.

**Raises:**
- `ValueError`: If not in MemoryMapped mode or the read/seek fails

#### `force_lazy_mode()`

Drop the Preload cache and switch the instance to lazy-style operation.

### Dump and Export

#### `dump(limit=None, offset=0) -> List[PyQueryResult]`

Return database entries with pagination support.

**Parameters:**
- `limit` (Optional[int]): Maximum number of entries to return (`None` for all)
- `offset` (int): Number of entries to skip (default 0)

**Returns:**
- `List[PyQueryResult]`: Entries with `kmer`, `count`, and `found` fields. **Note:** `dump()` reports the k-mer as a lowercase hex string of its `u128` encoding; use `export_all_kmers()` when you need decoded nucleotide sequences.

**Example:**
```python
# Dump first 1000 entries
for result in db.dump(limit=1000):
    print(f"{result.kmer}: {result.count}")
```

#### `export_all_kmers(limit=None, offset=0) -> List[PyQueryResult]`

Like `dump()`, but decodes k-mers back to nucleotide sequences.

**Example:**
```python
# Paginate through the database
batch_size = 1000
for start in range(0, 10_000, batch_size):
    batch = db.export_all_kmers(limit=batch_size, offset=start)
    for result in batch:
        print(f"{result.kmer}: {result.count}")
```

#### `export_to_file(output_path, limit=None, offset=0, progress_callback=None) -> int`

Stream k-mers to a tab-separated text file (`kmer\tcount` per line).

**Parameters:**
- `output_path` (str): Output file path
- `limit` (Optional[int]): Maximum number of entries to export
- `offset` (int): Number of entries to skip
- `progress_callback` (Optional[callable]): Called periodically with `(exported, total)` for progress reporting

**Returns:**
- `int`: Number of k-mers exported

**Raises:**
- `PermissionError`: If the output file cannot be created or written
- `RuntimeError`: If a write fails mid-export

**Example:**
```python
count = db.export_to_file("output.txt", limit=1000)
print(f"Exported {count} k-mers")
```

#### `export_to_json(output_path, limit=None, offset=0, progress_callback=None) -> int`

Export as a JSON array of `{"kmer": ..., "count": ...}` objects. Same parameters and exceptions as `export_to_file`.

#### `export_to_csv(output_path, limit=None, offset=0, progress_callback=None) -> int`

Export as CSV with a `kmer,count` header row. Same parameters and exceptions as `export_to_file`.

### Merging Databases

#### `PyDatabase.merge(databases, output, *, max_memory=None, merge_mode="auto")` (static method)

Merge multiple `.rkdb` databases into a single output database. The merge goes through the same bounded core the CLI uses: total k-mer counts are read from the headers, compared against the memory budget, and routed to the in-memory or streaming path accordingly. The output file is written directly by the merge — the merged database is never held fully in RAM.

**Parameters:**
- `databases` (List[str]): Database file paths to merge
- `output` (str): Output database file path
- `max_memory` (Optional[str]): Memory budget, e.g. `"4GB"`, `"512MB"`, or `"1024"` for raw bytes. `None` (default) uses 50% of system memory
- `merge_mode` (str): One of `"auto"` (default), `"memory"`, or `"streaming"`

**Raises:**
- `ValueError`: If `databases` is empty, `merge_mode` is invalid, or `max_memory` cannot be parsed
- `FileNotFoundError`: If an input database file does not exist
- `RuntimeError`: If the merge fails (including the over-budget `merge_mode="memory"` rejection)

**Example:**
```python
from pyrustkmer import PyDatabase

PyDatabase.merge(
    ["db1.rkdb", "db2.rkdb", "db3.rkdb"],
    "merged.rkdb",
)

# Bound the memory and force streaming
PyDatabase.merge(
    ["db1.rkdb", "db2.rkdb"],
    "merged.rkdb",
    max_memory="4GB",
    merge_mode="streaming",
)
```

## Performance Considerations

### Database Initialization

- Use `LoadMode.Preload` for the fastest repeated queries when the database fits in memory
- Use `LoadMode.MemoryMapped` for large databases to avoid a full in-memory cache
- Use `LoadMode.Lazy` for binary-search lookups with a lower footprint

### Query Performance

- Exact queries (`query_exact`) are much faster than fuzzy queries
- Fuzzy queries generate combinatorial variants; keep `max_mutations` low and set `max_results` (see [Fuzzy Query](fuzzyquery.md))
- Batch queries (`query_exact_batch`) amortize the call boundary across many k-mers

### Memory Usage

- `dump()` and `export_all_kmers()` build their result lists in memory; page through large databases with `limit`/`offset`
- The streaming exports (`export_to_file`, `export_to_json`, `export_to_csv`) write incrementally and suit very large databases
- `PyDatabase.merge` never materializes the merged database in RAM

## Error Handling

### Common Exceptions

- `FileNotFoundError`: Database file doesn't exist (constructor, `merge`)
- `ValueError`: File is not a valid `.rkdb` database, k-mer length mismatch, invalid characters, invalid pagination/merge parameters
- `RuntimeError`: Query-engine failures (prefix, hybrid, merge)
- `PermissionError`: Export target cannot be created or written

### Best Practices

```python
from pyrustkmer import PyDatabase, LoadMode

try:
    db = PyDatabase("example.rkdb", LoadMode.Preload)
    result = db.query_exact("ATCGATCGATCGATCGATCG")
    print(f"Count: {result.count}")
except FileNotFoundError as e:
    print(f"Database file not found: {e}")
except ValueError as e:
    print(f"Invalid database or k-mer: {e}")
```

`PyDatabase` holds no operating-system resources that require an explicit `close()` — simply let the object go out of scope when you are done with it.

## Integration Examples

### Scientific Computing

```python
import numpy as np
from pyrustkmer import PyDatabase, LoadMode

def analyze_kmer_frequencies(db_path: str, kmers: list) -> np.ndarray:
    """Get k-mer frequencies as numpy array."""
    db = PyDatabase(db_path, LoadMode.Preload)
    results = db.query_exact_batch(kmers)
    return np.array([results[kmer].count for kmer in kmers])
```

### Multi-Sample Analysis

```python
from pathlib import Path
import pandas as pd
from pyrustkmer import PyDatabase, LoadMode

def analyze_multiple_samples(db_directory: str, queries: list) -> pd.DataFrame:
    """Analyze k-mer presence across multiple samples using pandas."""
    db_files = list(Path(db_directory).glob("*.rkdb"))
    results = []

    for db_file in db_files:
        db = PyDatabase(str(db_file), LoadMode.Preload)
        sample_data = {'Sample': db_file.stem}
        for query in queries:
            try:
                sample_data[query] = db.query_exact(query).count
            except ValueError:
                sample_data[query] = 0
        results.append(sample_data)

    return pd.DataFrame(results)
```

### Large-Database Mining

```python
from pyrustkmer import PyDatabase, LoadMode

def find_abundant_kmers(db_path: str, min_count: int = 100,
                        max_results: int = 1000) -> list:
    """Find highly abundant k-mers in the database."""
    abundant = []
    db = PyDatabase(db_path, LoadMode.Preload)

    batch_size = 10_000
    start = 0
    while len(abundant) < max_results:
        batch = db.export_all_kmers(limit=batch_size, offset=start)
        if not batch:
            break
        for result in batch:
            if result.count >= min_count:
                abundant.append({'kmer': result.kmer, 'count': result.count})
        start += batch_size

    abundant.sort(key=lambda x: x['count'], reverse=True)
    return abundant[:max_results]
```
