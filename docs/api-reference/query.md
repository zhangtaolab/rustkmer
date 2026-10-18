<!-- generated-by: gsd-doc-writer -->
# QueryResult

The `PyQueryResult` class represents the result of an exact k-mer query operation. It provides a simple container for query information with convenient methods for data access and serialization.

## Class Definition

```python
class PyQueryResult:
    """Result of a k-mer query.

    Attributes:
        kmer: The queried k-mer sequence
        count: Number of occurrences in the database
        found: Whether the k-mer was present in the database
    """
```

`PyQueryResult` instances are produced by `PyDatabase` methods — you do not construct them directly:

- `PyDatabase.query_exact(kmer)` → single `PyQueryResult`
- `PyDatabase.query_exact_batch(kmers)` → `Dict[str, PyQueryResult]`
- `PyDatabase.dump(limit, offset)` → `List[PyQueryResult]`
- `PyDatabase.export_all_kmers(limit, offset)` → `List[PyQueryResult]`

## Attributes

### `kmer: str`
The k-mer sequence associated with the result. For `query_exact` this is the upper-cased query k-mer; for `dump()` it is the lowercase hex encoding of the stored `u128` k-mer (use `export_all_kmers()` for decoded nucleotide sequences).

### `count: int`
Number of occurrences of this k-mer in the database. Returns 0 if the k-mer is not present.

### `found: bool`
Whether the k-mer exists in the database (`count > 0`).

## Methods

### `to_dict() -> Dict[str, Union[str, int, bool]]`
Convert the result to a dictionary representation.

**Returns:**
- `Dict`: Dictionary with keys `kmer`, `count`, and `found`

**Example:**
```python
result = db.query_exact("ATCGATCGATCGATCGATCG")
data = result.to_dict()

print(data)
# Output: {'kmer': 'ATCGATCGATCGATCGATCG', 'count': 42, 'found': True}
```

### `to_json() -> str`
Convert the result to a JSON string.

**Returns:**
- `str`: JSON representation with `kmer`, `count`, and `found` fields

**Example:**
```python
result = db.query_exact("ATCGATCGATCGATCGATCG")
print(result.to_json())
# Output: {"kmer": "ATCGATCGATCGATCGATCG", "count": 42, "found": true}
```

### `to_csv() -> str`
Convert the result to a CSV string with a `kmer,count,found` header row.

### `to_tsv() -> str`
Convert the result to a TSV string with a `kmer\tcount\tfound` header row.

### `__repr__() -> str`
String representation of the result.

**Example:**
```python
result = db.query_exact("ATCGATCGATCGATCGATCG")
print(result)
# Output: PyQueryResult(kmer='ATCGATCGATCGATCGATCG', count=42, found=True)
```

## Usage Examples

### Basic Query Result Processing

```python
from pyrustkmer import PyDatabase, LoadMode

db = PyDatabase("database.rkdb", LoadMode.Preload)

# Query a k-mer
result = db.query_exact("ATCGATCGATCGATCGATCG")

# Check if k-mer exists
if result.found:
    print(f"Found k-mer {result.kmer} with count {result.count}")
else:
    print(f"K-mer {result.kmer} not found in database")
```

### Batch Query Processing

```python
from pyrustkmer import PyDatabase, LoadMode

def analyze_kmers(db_path, kmers):
    """Analyze multiple k-mers and return statistics."""
    db = PyDatabase(db_path, LoadMode.Preload)
    results = db.query_exact_batch(kmers)

    for kmer, result in results.items():
        if result.found:
            print(f"{kmer}: {result.count} occurrences")
        else:
            print(f"{kmer}: not found")

    return results

# Usage
kmers = [
    "ATCGATCGATCGATCGATCG",
    "GCTAGCTAGCTAGCTAGCTA",
    "TTTTTTTTTTTTTTTTTTTT",
]

results = analyze_kmers("database.rkdb", kmers)
```

### Data Serialization

```python
import json
from pyrustkmer import PyDatabase, LoadMode

def export_query_results(db_path, kmers, output_file):
    """Export query results to JSON file."""
    db = PyDatabase(db_path, LoadMode.Preload)
    results = db.query_exact_batch(kmers)

    all_results = [result.to_dict() for result in results.values()]

    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)

# Usage
kmers = ["ATCGATCGATCGATCGATCG", "GCTAGCTAGCTAGCTAGCTA"]
export_query_results("database.rkdb", kmers, "query_results.json")
```

### Integration with Pandas

```python
import pandas as pd
from pyrustkmer import PyDatabase, LoadMode

def create_kmer_dataframe(db_path, kmers):
    """Create a pandas DataFrame from query results."""
    db = PyDatabase(db_path, LoadMode.Preload)
    results = db.query_exact_batch(kmers)

    rows = [{
        'kmer': result.kmer,
        'count': result.count,
        'present': result.found
    } for result in results.values()]

    return pd.DataFrame(rows)

# Usage
kmers = ["ATCGATCGATCGATCGATCG", "GCTAGCTAGCTAGCTAGCTA", "TTTTTTTTTTTTTTTTTTTT"]
df = create_kmer_dataframe("database.rkdb", kmers)

print(df.describe())
print(f"\nK-mers found: {df['present'].sum()}")
print(f"Total occurrences: {df[df['present']]['count'].sum()}")
```

## Performance Considerations

### Memory Efficiency

`PyQueryResult` objects are lightweight and can be stored in large quantities:

```python
# Collect results for many k-mers
db = PyDatabase("large_db.rkdb", LoadMode.Preload)
results = db.query_exact_batch(many_kmers)  # Dict[str, PyQueryResult]
```

### Pagination for Database Scans

When scanning a whole database, page through it with `limit`/`offset` rather than materializing everything at once:

```python
db = PyDatabase("large_db.rkdb", LoadMode.Preload)
for start in range(0, 1_000_000, 10_000):
    batch = db.export_all_kmers(limit=10_000, offset=start)
    if not batch:
        break
    process(batch)
```

## Comparison with PyFuzzyResult

`PyQueryResult` is designed for exact queries and provides a simpler interface compared to `PyFuzzyResult`:

| Feature | PyQueryResult | PyFuzzyResult |
|---------|---------------|---------------|
| Query Type | Exact matches only | Fuzzy matches within tolerance |
| Count | Single count value | Multiple matches with individual counts |
| Distance | Not applicable | Hamming distance for each match |
| Match types | Not applicable | `exact`, `wildcard_expansion`, `mutation_tolerance` |
| Performance | Faster | Slower (generates variants) |

Choose `PyQueryResult` (via `query_exact`) when:
- You need exact matches only
- Performance is critical
- You're doing presence/absence checking

Choose `PyFuzzyResult` (via `PyFuzzyQuery`) when:
- You need to handle sequencing errors
- You're looking for similar sequences
- You need mutation tolerance

## Best Practices

1. **Use `query_exact_batch`** when processing many k-mers to reduce call overhead
2. **Check `found`** to distinguish absent k-mers from zero counts
3. **Use `export_all_kmers`** rather than `dump()` when you need nucleotide sequences rather than hex encodings
4. **Serialize results** with `to_dict()`/`to_json()` if you need to reuse them later

## Error Handling

`PyQueryResult` itself doesn't raise exceptions, but the database operations that create it can:

```python
from pyrustkmer import PyDatabase, LoadMode

def safe_query(db_path, kmer):
    try:
        db = PyDatabase(db_path, LoadMode.Preload)
        return db.query_exact(kmer)
    except FileNotFoundError as e:
        print(f"Database not found: {e}")
        return None
    except ValueError as e:
        print(f"Invalid k-mer: {e}")
        return None
```
