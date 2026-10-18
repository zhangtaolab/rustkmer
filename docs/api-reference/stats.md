<!-- generated-by: gsd-doc-writer -->
# DatabaseStats

The `PyDatabaseStats` class contains statistics and metadata about a k-mer database, read directly from the RKDB header. Its counterpart `PyCounterStats` reports live statistics for a running `PyCounter`.

## Class Definition

```python
class PyDatabaseStats:
    """Statistics about a k-mer database.

    Attributes:
        kmer_size: Length of k-mers in the database
        total_kmers: Total k-mers recorded in the header
        unique_kmers: Number of unique k-mer sequences
        file_size: Database file size in bytes
        is_sorted: Whether the database entries are sorted
        canonical: Whether the database stores canonical k-mers
    """
```

`PyDatabaseStats` instances are returned by `PyDatabase.get_stats()` — you do not construct them directly.

## Attributes

### `kmer_size: int`
Length of k-mers stored in the database (e.g., 31 for 31-mers).

### `total_kmers: int`
Total number of k-mers recorded in the database header.

### `unique_kmers: int`
Number of unique k-mer sequences in the database.

### `file_size: int`
Size of the database file in bytes.

### `is_sorted: bool`
Whether the database entries are stored in sorted order (sorted databases enable binary-search queries).

### `canonical: bool`
Whether the database stores canonical k-mers (each k-mer and its reverse complement merged into one entry).

## Methods

### `to_json() -> str`
Convert the statistics to a JSON string.

**Returns:**
- `str`: JSON representation of all six attributes

**Example:**
```python
stats = db.get_stats()
print(stats.to_json())
# Output: {"kmer_size": 31, "total_kmers": 1000000, "unique_kmers": 1000000,
#          "file_size": 20000042, "is_sorted": true, "canonical": true}
```

### `to_csv() -> str`
Convert the statistics to a CSV string with a `metric,value` header, one row per attribute.

**Example:**
```python
print(db.get_stats().to_csv())
# metric,value
# kmer_size,31
# total_kmers,1000000
# ...
```

### `to_tsv() -> str`
Convert the statistics to a TSV string with a `metric\tvalue` header.

### `__repr__() -> str`
String representation listing all attributes.

**Example:**
```python
print(db.get_stats())
# Output: PyDatabaseStats(kmer_size=31, total_kmers=1000000, unique_kmers=1000000,
#         file_size=20000042, is_sorted=True, canonical=True)
```

## PyCounterStats

Returned by `PyCounter.get_stats()` for a running counter:

| Attribute | Type | Description |
|-----------|------|-------------|
| `total_kmers` | `int` | Total number of k-mers processed |
| `unique_kmers` | `int` | Number of unique k-mers found |
| `kmer_length` | `int` | K-mer length |
| `canonical_mode` | `bool` | Whether canonical counting is enabled |
| `memory_usage` | `int` | Estimated memory usage in bytes |

```python
from pyrustkmer import PyCounter

counter = PyCounter(21, canonical=True)
counter.add_from_fasta("genome.fa.gz")

stats = counter.get_stats()
print(f"Total: {stats.total_kmers:,}, Unique: {stats.unique_kmers:,}")
print(f"Memory: {stats.memory_usage / 1e6:.1f} MB")
```

## Usage Examples

### Basic Statistics Retrieval

```python
from pyrustkmer import PyDatabase, LoadMode

db = PyDatabase("genome.rkdb", LoadMode.Preload)
stats = db.get_stats()

print(f"Database Statistics:")
print(f"  K-mer size: {stats.kmer_size}")
print(f"  Total k-mers: {stats.total_kmers:,}")
print(f"  Unique k-mers: {stats.unique_kmers:,}")
print(f"  File size: {stats.file_size / 1e6:.1f} MB")
print(f"  Sorted: {stats.is_sorted}")
print(f"  Canonical: {stats.canonical}")
```

### Database Comparison

```python
from pyrustkmer import PyDatabase, LoadMode

def compare_databases(db_paths):
    """Compare statistics of multiple databases."""
    stats_list = []
    for path in db_paths:
        db = PyDatabase(path, LoadMode.Preload)
        stats_list.append((path, db.get_stats()))

    stats_list.sort(key=lambda x: x[1].unique_kmers, reverse=True)

    print(f"{'Database':<30} {'Unique':<12} {'Total':<12} {'Size (MB)':<12}")
    print("-" * 66)
    for path, stats in stats_list:
        print(f"{path:<30} {stats.unique_kmers:<12,} "
              f"{stats.total_kmers:<12,} {stats.file_size / 1e6:<12.1f}")

# Usage
compare_databases([
    "human_genome.rkdb",
    "mouse_genome.rkdb",
    "drosophila_genome.rkdb",
])
```

### Storage Efficiency Analysis

```python
from pyrustkmer import PyDatabase, LoadMode

def analyze_storage_efficiency(db_path):
    """Analyze storage efficiency of the database."""
    db = PyDatabase(db_path, LoadMode.Preload)
    stats = db.get_stats()

    bytes_per_unique_kmer = stats.file_size / max(stats.unique_kmers, 1)

    # RKDB v2 stores 16 bytes of encoded k-mer + 4 bytes of count per entry
    theoretical_min = stats.unique_kmers * 20
    efficiency = theoretical_min / stats.file_size * 100 if stats.file_size else 0

    print(f"Storage Efficiency Analysis for: {db_path}")
    print(f"  File size: {stats.file_size / 1e6:.1f} MB")
    print(f"  Bytes per unique k-mer: {bytes_per_unique_kmer:.2f}")
    print(f"  Storage efficiency vs 20B/entry: {efficiency:.1f}%")

    return {'bytes_per_unique_kmer': bytes_per_unique_kmer,
            'efficiency': efficiency}

# Usage
analyze_storage_efficiency("genome.rkdb")
```

### Database Metadata Export

```python
import json
from pyrustkmer import PyDatabase, LoadMode

def export_database_metadata(db_path, output_file):
    """Export database metadata to a JSON file."""
    db = PyDatabase(db_path, LoadMode.Preload)
    stats = db.get_stats()

    # Parse the stats JSON produced by the binding itself
    metadata = json.loads(stats.to_json())
    metadata['database_path'] = db_path

    with open(output_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"Database metadata exported to: {output_file}")
    return metadata

# Usage
export_database_metadata("genome.rkdb", "genome_metadata.json")
```

## Integration Examples

### Pandas Integration

```python
import pandas as pd
from pyrustkmer import PyDatabase, LoadMode

def create_stats_dataframe(db_paths):
    """Create a pandas DataFrame with statistics for multiple databases."""
    rows = []
    for path in db_paths:
        try:
            db = PyDatabase(path, LoadMode.Preload)
            stats = db.get_stats()
            rows.append({
                'database_path': path,
                'kmer_size': stats.kmer_size,
                'unique_kmers': stats.unique_kmers,
                'total_kmers': stats.total_kmers,
                'size_mb': stats.file_size / 1e6,
                'is_sorted': stats.is_sorted,
                'canonical': stats.canonical,
            })
        except (FileNotFoundError, ValueError) as e:
            print(f"Error processing {path}: {e}")

    return pd.DataFrame(rows)

# Usage
df = create_stats_dataframe(["human.rkdb", "mouse.rkdb", "drosophila.rkdb"])
print(df.sort_values('unique_kmers', ascending=False)
        [['database_path', 'unique_kmers', 'size_mb']])
```

### Count Distribution Analysis

```python
import numpy as np
from pyrustkmer import PyDatabase, LoadMode

def analyze_database_distribution(db_path, sample_size=10000):
    """Analyze k-mer count distribution in the database."""
    db = PyDatabase(db_path, LoadMode.Preload)
    stats = db.get_stats()

    samples = np.array([
        result.count
        for result in db.export_all_kmers(limit=sample_size)
    ])

    print(f"K-mer Count Distribution Analysis for: {db_path}")
    print(f"  Database stats: {stats.unique_kmers:,} unique k-mers")
    print(f"  Sample size: {len(samples):,} k-mers")
    print(f"  Sample mean: {samples.mean():.2f}")
    print(f"  Sample median: {np.median(samples):.2f}")
    print(f"  95th percentile: {np.percentile(samples, 95):.2f}")

    return stats, samples

# Usage
analyze_database_distribution("genome.rkdb")
```

## Performance Considerations

### Header-Backed, Not Computed

`PyDatabaseStats` is populated from the database header at query time — it does not scan the database body:

```python
db = PyDatabase("large_db.rkdb", LoadMode.MemoryMapped)
stats = db.get_stats()  # reads header fields only; fast in every load mode
```

### Reuse the Object

Each `get_stats()` call builds a fresh object; fetch it once and reuse it:

```python
db = PyDatabase("database.rkdb", LoadMode.Preload)
stats = db.get_stats()  # use this everywhere downstream
```

## Best Practices

1. **Fetch stats once** per `PyDatabase` object and reuse the result
2. **Use `to_json()`** for machine-readable export rather than re-formatting attributes by hand
3. **Check `is_sorted`** before relying on ordering-sensitive iteration
4. **Check `canonical`** to know whether queries are strand-independent for this database
5. **Use `PyCounterStats.memory_usage`** to size counters before calling `save_database`

## Error Handling

```python
from pyrustkmer import PyDatabase, LoadMode

def get_stats_safely(db_path):
    """Get database statistics with error handling."""
    try:
        db = PyDatabase(db_path, LoadMode.Preload)
        return db.get_stats()
    except FileNotFoundError:
        print(f"Database file not found: {db_path}")
        return None
    except ValueError as e:
        print(f"Invalid database format: {e}")
        return None

# Usage
stats = get_stats_safely("database.rkdb")
if stats:
    print(f"Database has {stats.unique_kmers:,} unique k-mers")
```
