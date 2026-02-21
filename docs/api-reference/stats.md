# DatabaseStats

The `DatabaseStats` class contains comprehensive statistics and metadata about a k-mer database. It provides detailed information about database composition, file characteristics, and format versioning.

## Class Definition

```python
@dataclass
class DatabaseStats:
    """Statistics about a k-mer database.

    This class contains metadata about the database such as k-mer size,
    number of unique k-mers, and file information.

    Attributes:
        kmer_size: Length of k-mers in the database
        unique_kmers: Number of unique k-mer sequences
        total_counts: Sum of all k-mer counts
        min_count: Minimum count for any single k-mer
        max_count: Maximum count for any single k-mer
        file_size: Size of database file in bytes
        format_version: Version of the database format
    """
    kmer_size: int
    unique_kmers: int
    total_counts: int
    min_count: int
    max_count: int
    file_size: int
    format_version: str
```

## Attributes

### `kmer_size: int`
Length of k-mers stored in the database (e.g., 31 for 31-mers).

### `unique_kmers: int`
Number of unique k-mer sequences in the database.

### `total_counts: int`
Sum of counts for all k-mers in the database. This represents the total number of k-mer occurrences in the original data.

### `min_count: int`
Minimum count among all k-mers in the database. May be 1 if all k-mers are unique.

### `max_count: int`
Maximum count among all k-mers in the database. Represents the most abundant k-mer.

### `file_size: int`
Size of the database file in bytes.

### `format_version: str`
Version of the database format (e.g., "2.0"). Useful for compatibility checking.

## Methods

### `to_dict() -> Dict[str, Union[str, int]]`
Convert DatabaseStats to a dictionary representation.

**Returns:**
- `Dict[str, Union[str, int]]`: Dictionary containing all statistics

**Example:**
```python
stats = db.get_stats()
data = stats.to_dict()

print(data)
# Output: {
#   'kmer_size': 31,
#   'unique_kmers': 1000000,
#   'total_counts': 5000000,
#   'min_count': 1,
#   'max_count': 1000,
#   'file_size': 25000000,
#   'format_version': '2.0'
# }
```

### `to_json() -> str`
Convert DatabaseStats to a JSON string.

**Returns:**
- `str`: JSON representation of the statistics

**Example:**
```python
stats = db.get_stats()
json_str = stats.to_json()

print(json_str)
# Output: {"kmer_size": 31, "unique_kmers": 1000000, ...}
```

### `from_dict(data: Dict[str, Union[str, int]]) -> DatabaseStats`
Create DatabaseStats from a dictionary.

**Parameters:**
- `data` (Dict[str, Union[str, int]]): Dictionary with statistics data

**Returns:**
- `DatabaseStats`: New DatabaseStats instance

**Example:**
```python
data = {
    "kmer_size": 31,
    "unique_kmers": 1000000,
    "total_counts": 5000000,
    "min_count": 1,
    "max_count": 1000,
    "file_size": 25000000,
    "format_version": "2.0"
}

stats = DatabaseStats.from_dict(data)
print(f"Database has {stats.unique_kmers:,} unique k-mers")
```

## Usage Examples

### Basic Statistics Retrieval

```python
from pyrustkmer import Database

db = PyDatabase("genome.rkdb", LoadMode.Preload)
    stats = db.get_stats()

    print(f"Database Statistics:")
    print(f"  K-mer size: {stats.kmer_size}")
    print(f"  Unique k-mers: {stats.unique_kmers:,}")
    print(f"  Total occurrences: {stats.total_counts:,}")
    print(f"  Count range: {stats.min_count} - {stats.max_count}")
    print(f"  File size: {stats.file_size / 1e6:.1f} MB")
    print(f"  Format version: {stats.format_version}")
```

### Database Comparison

```python
from pyrustkmer import Database

def compare_databases(db_paths):
    """Compare statistics of multiple databases."""
    stats_list = []

    for path in db_paths:
        db = PyDatabase(path, LoadMode.Preload)
            stats = db.get_stats()
            stats_list.append((path, stats))

    # Sort by unique k-mers
    stats_list.sort(key=lambda x: x[1].unique_kmers, reverse=True)

    print("Database Comparison:")
    print(f"{'Database':<30} {'K-mers':<12} {'Total':<12} {'Size (MB)':<12}")
    print("-" * 66)

    for path, stats in stats_list:
        size_mb = stats.file_size / 1e6
        print(f"{path:<30} {stats.unique_kmers:<12,} {stats.total_counts:<12,} {size_mb:<12.1f}")

# Usage
databases = [
    "human_genome.rkdb",
    "mouse_genome.rkdb",
    "drosophila_genome.rkdb"
]

compare_databases(databases)
```

### Quality Assessment

```python
from pyrustkmer import Database

def assess_database_quality(db_path):
    """Assess database quality based on statistics."""
    db = PyDatabase(db_path, LoadMode.Preload)
        stats = db.get_stats()

    # Calculate derived metrics
    if stats.unique_kmers > 0:
        avg_count = stats.total_counts / stats.unique_kmers
        coverage_estimate = stats.total_counts * stats.kmer_size / 3_000_000_000  # Approximate genome coverage
    else:
        avg_count = 0
        coverage_estimate = 0

    # Quality indicators
    quality_issues = []

    if stats.max_count / avg_count > 1000:  # High redundancy
        quality_issues.append("High count redundancy (possible repeats)")

    if avg_count < 2:
        quality_issues.append("Low average coverage")

    if stats.min_count == 0:
        quality_issues.append("Zero-count k-mers present")

    # Print assessment
    print(f"Database Quality Assessment for: {db_path}")
    print(f"  Average k-mer count: {avg_count:.2f}")
    print(f"  Estimated genome coverage: {coverage_estimate:.1f}x")
    print(f"  Count distribution range: {stats.min_count} - {stats.max_count}")

    if quality_issues:
        print("  Quality concerns:")
        for issue in quality_issues:
            print(f"    - {issue}")
    else:
        print("  No quality concerns detected")

    return stats, quality_issues

# Usage
assess_database_quality("genome.rkdb")
```

### Storage Efficiency Analysis

```python
from pyrustkmer import Database

def analyze_storage_efficiency(db_path):
    """Analyze storage efficiency of database."""
    db = PyDatabase(db_path, LoadMode.Preload)
        stats = db.get_stats()

    # Calculate efficiency metrics
    bytes_per_unique_kmer = stats.file_size / stats.unique_kmers
    bytes_per_count = stats.file_size / stats.total_counts

    # Estimate theoretical minimum (assuming 8 bytes per k-mer + 8 bytes per count)
    theoretical_min = stats.unique_kmers * 16
    efficiency = theoretical_min / stats.file_size * 100

    print(f"Storage Efficiency Analysis for: {db_path}")
    print(f"  File size: {stats.file_size / 1e6:.1f} MB")
    print(f"  Bytes per unique k-mer: {bytes_per_unique_kmer:.2f}")
    print(f"  Bytes per total occurrence: {bytes_per_count:.4f}")
    print(f"  Storage efficiency: {efficiency:.1f}%")

    return {
        'bytes_per_unique_kmer': bytes_per_unique_kmer,
        'bytes_per_count': bytes_per_count,
        'efficiency': efficiency
    }

# Usage
analyze_storage_efficiency("genome.rkdb")
```

### Database Metadata Export

```python
import json
from pyrustkmer import Database

def export_database_metadata(db_path, output_file):
    """Export database metadata to JSON file."""
    db = PyDatabase(db_path, LoadMode.Preload)
        stats = db.get_stats()

    # Add additional metadata
    metadata = stats.to_dict()
    metadata['database_path'] = db_path
    metadata['export_timestamp'] = str(pd.Timestamp.now())

    # Calculate derived metrics
    if stats.unique_kmers > 0:
        metadata['average_count'] = stats.total_counts / stats.unique_kmers
        metadata['count_variance'] = stats.max_count - stats.min_count

    # Save to file
    with open(output_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"Database metadata exported to: {output_file}")
    return metadata

# Usage
import pandas as pd
export_database_metadata("genome.rkdb", "genome_metadata.json")
```

## Integration Examples

### Pandas Integration

```python
import pandas as pd
from pyrustkmer import Database

def create_stats_dataframe(db_paths):
    """Create a pandas DataFrame with statistics for multiple databases."""
    stats_data = []

    for path in db_paths:
        try:
            db = PyDatabase(path, LoadMode.Preload)
                stats = db.get_stats()

                # Add derived metrics
                stats_dict = stats.to_dict()
                stats_dict['database_path'] = path
                stats_dict['avg_count'] = stats.total_counts / max(stats.unique_kmers, 1)
                stats_dict['size_mb'] = stats.file_size / 1e6

                stats_data.append(stats_dict)

        except Exception as e:
            print(f"Error processing {path}: {e}")

    return pd.DataFrame(stats_data)

# Usage
db_paths = ["human.rkdb", "mouse.rkdb", "drosophila.rkdb"]
df = create_stats_dataframe(db_paths)

# Analyze
print(df.sort_values('unique_kmers', ascending=False)[['database_path', 'unique_kmers', 'size_mb']])
print(f"\nAverage k-mer counts:")
print(df[['database_path', 'avg_count']].sort_values('avg_count', ascending=False))
```

### Statistical Analysis

```python
import numpy as np
from pyrustkmer import Database

def analyze_database_distribution(db_path, sample_size=10000):
    """Analyze k-mer count distribution in database."""
    db = PyDatabase(db_path, LoadMode.Preload)
        stats = db.get_stats()

        # Sample k-mers for distribution analysis
        samples = []
        for i, result in enumerate(db.dump(limit=sample_size)):
            samples.append(result.count)
            if i >= sample_size - 1:
                break

        # Calculate distribution statistics
        samples = np.array(samples)

        distribution_stats = {
            'sample_mean': np.mean(samples),
            'sample_median': np.median(samples),
            'sample_std': np.std(samples),
            'percentile_25': np.percentile(samples, 25),
            'percentile_75': np.percentile(samples, 75),
            'percentile_95': np.percentile(samples, 95),
            'sample_size': len(samples)
        }

        print(f"K-mer Count Distribution Analysis for: {db_path}")
        print(f"  Database stats: {stats.unique_kmers:,} unique k-mers")
        print(f"  Sample size: {len(samples):,} k-mers")
        print(f"  Sample mean: {distribution_stats['sample_mean']:.2f}")
        print(f"  Sample median: {distribution_stats['sample_median']:.2f}")
        print(f"  Sample std: {distribution_stats['sample_std']:.2f}")
        print(f"  25th percentile: {distribution_stats['percentile_25']:.2f}")
        print(f"  75th percentile: {distribution_stats['percentile_75']:.2f}")
        print(f"  95th percentile: {distribution_stats['percentile_95']:.2f}")

        return stats, distribution_stats

# Usage
analyze_database_distribution("genome.rkdb")
```

## Performance Considerations

### Lazy Loading

Database statistics are loaded lazily when first accessed:

```python
db = PyDatabase("large_db.rkdb")  # Stats not loaded yet
stats = db.get_stats()  # Stats loaded now
stats2 = db.get_stats()  # Returns cached version
```

### Caching

Statistics are cached in the Database object after first access:

```python
# Efficient: Stats loaded once and reused
db = PyDatabase("database.rkdb", LoadMode.Preload)
    stats1 = db.get_stats()  # Loads from disk
    stats2 = db.get_stats()  # Returns cached version

    # Both operations are fast after initial load
```

## Format Versioning

The format_version attribute helps ensure compatibility:

```python
def check_compatibility(stats):
    """Check if database format is compatible."""
    supported_versions = ["1.0", "2.0"]

    if stats.format_version not in supported_versions:
        raise ValueError(f"Unsupported database format version: {stats.format_version}")

    print(f"Database format {stats.format_version} is compatible")

# Usage
stats = db.get_stats()
check_compatibility(stats)
```

## Best Practices

1. **Access stats once** per Database object and reuse the result
2. **Store statistics** if you need them frequently to avoid repeated database access
3. **Monitor file size** trends when updating databases
4. **Check format version** when working with databases from different sources
5. **Use derived metrics** (like average count) for database quality assessment

## Error Handling

```python
from pyrustkmer import Database, DatabaseError

def get_stats_safely(db_path):
    """Get database statistics with error handling."""
    try:
        db = PyDatabase(db_path, LoadMode.Preload)
            return db.get_stats()

    except DatabaseNotFoundError:
        print(f"Database file not found: {db_path}")
        return None

    except InvalidDatabaseError:
        print(f"Invalid database format: {db_path}")
        return None

    except DatabaseError as e:
        print(f"Database error: {e}")
        return None

# Usage
stats = get_stats_safely("database.rkdb")
if stats:
    print(f"Database has {stats.unique_kmers:,} unique k-mers")
```