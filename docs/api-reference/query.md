# QueryResult

The `QueryResult` class represents the result of an exact k-mer query operation. It provides a simple container for query information with convenient methods for data access and serialization.

## Class Definition

```python
@dataclass
class QueryResult:
    """Result of a k-mer query.

    Attributes:
        kmer: The queried k-mer sequence
        count: Number of occurrences in the database
        canonical: Canonical representation of the k-mer
    """
    kmer: str
    count: int
    canonical: str
```

## Attributes

### `kmer: str`
The original k-mer sequence that was queried.

### `count: int`
Number of occurrences of this k-mer in the database. Returns 0 if the k-mer is not present.

### `canonical: str`
The canonical representation of the k-mer. For DNA sequences, this is typically the lexicographically smaller of the k-mer and its reverse complement.

## Properties

### `is_present: bool`
Check if the k-mer exists in the database.

**Returns:**
- `bool`: `True` if count > 0, `False` otherwise

**Example:**
```python
result = db.query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")

if result.is_present:
    print(f"K-mer found with count: {result.count}")
else:
    print("K-mer not found in database")
```

## Methods

### `to_dict() -> Dict[str, Union[str, int]]`
Convert the QueryResult to a dictionary representation.

**Returns:**
- `Dict[str, Union[str, int]]`: Dictionary with keys 'kmer', 'count', and 'canonical'

**Example:**
```python
result = db.query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
data = result.to_dict()

print(data)
# Output: {'kmer': 'ATCGATCG...', 'count': 42, 'canonical': 'ATCGATCG...'}
```

### `to_json() -> str`
Convert the QueryResult to a JSON string.

**Returns:**
- `str`: JSON representation of the QueryResult

**Example:**
```python
result = db.query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
json_str = result.to_json()

print(json_str)
# Output: {"kmer": "ATCGATCG...", "count": 42, "canonical": "ATCGATCG..."}
```

### `from_dict(data: Dict[str, Union[str, int]]) -> QueryResult`
Create a QueryResult from a dictionary.

**Parameters:**
- `data` (Dict[str, Union[str, int]]): Dictionary containing kmer, count, and canonical

**Returns:**
- `QueryResult`: New QueryResult instance

**Example:**
```python
data = {"kmer": "ATCGATCG...", "count": 42, "canonical": "ATCGATCG..."}
result = QueryResult.from_dict(data)

print(result.kmer)  # "ATCGATCG..."
print(result.count)  # 42
```

### `__str__() -> str`
String representation of the QueryResult.

**Returns:**
- `str`: String in format "kmer: count"

**Example:**
```python
result = db.query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
print(str(result))
# Output: ATCGATCGATCGATCGATCGATCGATCGATCGATCG: 42
```

## Usage Examples

### Basic Query Result Processing

```python
from rustkmer import Database

with Database("database.rkdb") as db:
    # Query a k-mer
    result = db.query("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")

    # Check if k-mer exists
    if result.is_present:
        print(f"Found k-mer {result.kmer} with count {result.count}")
        print(f"Canonical form: {result.canonical}")
    else:
        print(f"K-mer {result.kmer} not found in database")
```

### Batch Query Processing

```python
from rustkmer import Database

def analyze_kmers(db_path, kmers):
    """Analyze multiple k-mers and return statistics."""
    with Database(db_path) as db:
        results = []

        for kmer in kmers:
            result = db.query(kmer)
            results.append(result)

            # Process result
            if result.is_present:
                print(f"{kmer}: {result.count} occurrences")
            else:
                print(f"{kmer}: not found")

        return results

# Usage
kmers = [
    "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
    "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"
]

results = analyze_kmers("database.rkdb", kmers)
```

### Data Serialization

```python
import json
from rustkmer import Database

def export_query_results(db_path, kmers, output_file):
    """Export query results to JSON file."""
    with Database(db_path) as db:
        all_results = []

        for kmer in kmers:
            result = db.query(kmer)
            all_results.append(result.to_dict())

        # Save to JSON file
        with open(output_file, 'w') as f:
            json.dump(all_results, f, indent=2)

# Usage
kmers = ["ATCGATCG...", "GCTAGCTA..."]
export_query_results("database.rkdb", kmers, "query_results.json")
```

### Integration with Pandas

```python
import pandas as pd
from rustkmer import Database

def create_kmer_dataframe(db_path, kmers):
    """Create a pandas DataFrame from query results."""
    with Database(db_path) as db:
        results = []

        for kmer in kmers:
            result = db.query(kmer)
            results.append({
                'kmer': result.kmer,
                'count': result.count,
                'canonical': result.canonical,
                'present': result.is_present
            })

        return pd.DataFrame(results)

# Usage
kmers = ["ATCGATCG...", "GCTAGCTA...", "TTTTTTTT..."]
df = create_kmer_dataframe("database.rkdb", kmers)

# Analyze results
print(df.describe())
print(f"\nK-mers found: {df['present'].sum()}")
print(f"Total occurrences: {df[df['present']]['count'].sum()}")
```

## Performance Considerations

### Memory Efficiency

QueryResult objects are lightweight and can be stored in large quantities:

```python
# Store millions of results efficiently
all_results = []
with Database("large_db.rkdb") as db:
    for kmer in many_kmers:  # Could be millions
        result = db.query(kmer)
        all_results.append(result)  # Low memory overhead
```

### Serialization for Caching

Serialize frequently accessed results to avoid repeated queries:

```python
import json
import os
from rustkmer import Database

def cached_query(db_path, kmer, cache_dir="query_cache"):
    """Query with caching to avoid repeated database access."""
    cache_file = os.path.join(cache_dir, f"{kmer}.json")

    # Check cache first
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            data = json.load(f)
        return QueryResult.from_dict(data)

    # Perform query and cache result
    with Database(db_path) as db:
        result = db.query(kmer)

        # Save to cache
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_file, 'w') as f:
            f.write(result.to_json())

        return result
```

## Comparison with FuzzyQueryResult

QueryResult is designed for exact queries and provides a simpler interface compared to FuzzyQueryResult:

| Feature | QueryResult | FuzzyQueryResult |
|---------|-------------|------------------|
| Query Type | Exact matches only | Fuzzy matches within tolerance |
| Count | Single count value | Multiple matches with individual counts |
| Distance | Not applicable | Hamming distance for each match |
| Mutations | Not applicable | List of mutations for each match |
| Performance | Faster | Slower (generates variants) |

Choose QueryResult when:
- You need exact matches only
- Performance is critical
- You're doing presence/absence checking

Choose FuzzyQueryResult when:
- You need to handle sequencing errors
- You're looking for similar sequences
- You need mutation tolerance

## Best Practices

1. **Use context managers** for Database objects to ensure proper cleanup
2. **Check `is_present`** before accessing count if you need to differentiate between absent and zero-count
3. **Serialize results** if you need to reuse them later
4. **Batch queries** when processing many k-mers to reduce database overhead
5. **Cache frequent queries** if the database doesn't change often

## Error Handling

QueryResult itself doesn't raise exceptions, but the database operations that create it can:

```python
from rustkmer import Database, InvalidKmerError, DatabaseError

def safe_query(db_path, kmer):
    try:
        with Database(db_path) as db:
            return db.query(kmer)

    except InvalidKmerError as e:
        print(f"Invalid k-mer: {e.kmer} - {e.reason}")
        return None

    except DatabaseError as e:
        print(f"Database error: {e}")
        return None
```