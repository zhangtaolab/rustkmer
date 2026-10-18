<!-- generated-by: gsd-doc-writer -->
# Fuzzy Query

The fuzzy query functionality allows searching for k-mers within a specified Hamming distance, enabling tolerant matching for sequencing errors, natural variations, and related sequences. It also supports `N` wildcards in the query pattern.

## Overview

Fuzzy queries find k-mers that are similar to a query pattern within a specified mutation tolerance. Unlike exact queries, fuzzy queries can handle:

- Sequencing errors in genomic data
- Natural variations and mutations
- Ambiguous positions in k-mers (`N` wildcard)
- Discovery of sequence variants

The implementation uses the Hamming distance metric, which counts the number of positions at which two k-mers differ.

Fuzzy querying is provided by the `PyFuzzyQuery` engine, constructed from a `PyDatabase`. (`PyDatabase` also has a `query_fuzzy()` convenience method with the same signature, but `PyFuzzyQuery` is the documented interface for fuzzy workloads.)

## Classes

### PyFuzzyMatch

Represents a single matched k-mer within the mutation tolerance. Instances are produced inside `PyFuzzyResult` — you do not construct them directly.

**Attributes:**
- `kmer` (str): The matched k-mer sequence found in the database
- `count` (int): Number of occurrences of this k-mer in the database
- `distance` (Optional[int]): Hamming distance from the query pattern (`None` when not applicable; 0 for exact matches)
- `match_type` (str): How the match was produced — `"exact"`, `"wildcard_expansion[...]"`, `"mutation_tolerance[...]"`, or `"length_normalization"`
- `mutation_positions` (List[int]): Positions involved in the wildcard expansion or mutations (empty for plain exact matches)

**Example:**
```python
for match in result.matches:
    print(f"{match.kmer}: count={match.count}, distance={match.distance}, "
          f"type={match.match_type}")
```

### PyFuzzyResult

Contains all matches for a single fuzzy query operation.

**Attributes:**
- `query_kmer` (str): The upper-cased query pattern
- `exact_match` (Optional[PyFuzzyMatch]): The exact match, if one was found
- `matches` (List[PyFuzzyMatch]): All matches, exact and fuzzy
- `total_matches` (int): Total number of matches found
- `mutation_tolerance` (int): The mutation tolerance used for the query
- `query_time_ms` (int): Query execution time in milliseconds
- `has_position_mutations` (bool): Whether position-specific mutations were used

**Methods:**

#### `get_matches_by_distance(distance: int) -> List[PyFuzzyMatch]`
Get matches at a specific Hamming distance.

**Parameters:**
- `distance` (int): Specific distance to filter by (0 = exact matches)

**Returns:**
- `List[PyFuzzyMatch]`: Matches at the specified distance

#### `get_top_matches(limit: int) -> List[PyFuzzyMatch]`
Get the most abundant matches, sorted by count (descending).

**Parameters:**
- `limit` (int): Number of matches to return

**Returns:**
- `List[PyFuzzyMatch]`: Top matches sorted by count

#### `to_json() -> str`
Serialize the full result (query, exact match, matches, and metadata) to a JSON string.

#### `to_csv() -> str` / `to_tsv() -> str`
Serialize the matches as CSV/TSV with a `kmer,count,distance,match_type,mutation_positions` header, plus comment lines carrying the query metadata.

**Example:**
```python
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

db = PyDatabase("example.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
result = fuzzy.query_fuzzy("ATCGATCGATCGATCGATCG", max_mutations=2)

print(f"Query: {result.query_kmer}")
print(f"Total matches: {result.total_matches}")

# Exact match (if any)
if result.exact_match is not None:
    print(f"Exact: {result.exact_match.kmer} x{result.exact_match.count}")

# Get matches at distance 2
distance_2 = result.get_matches_by_distance(2)
print(f"Found {len(distance_2)} matches at distance 2")

# Get top 5 most abundant matches
top_5 = result.get_top_matches(5)
for match in top_5:
    print(f"{match.kmer}: {match.count} (distance={match.distance})")
```

### PyFuzzyQuery

The fuzzy query engine, created from a loaded database.

#### Constructor

```python
PyFuzzyQuery(database: PyDatabase)
```

**Parameters:**
- `database` (`PyDatabase`): A loaded database instance (the engine reads the database's k-mer size at construction and reloads the database from its path when executing queries)

**Raises:**
- `ValueError`: If the database cannot be loaded

#### `query_fuzzy(pattern, max_mutations, max_results=None) -> PyFuzzyResult`

Perform a fuzzy query with wildcard and mutation support.

**Parameters:**
- `pattern` (str): The query pattern; must be exactly the database's k-mer size long and contain only `A`, `T`, `C`, `G`, `N` (`N` acts as a wildcard)
- `max_mutations` (int): Maximum number of substitutions allowed
- `max_results` (Optional[int]): Cap on the number of returned matches (default `None` = uncapped)

**Returns:**
- `PyFuzzyResult`: All matches within the mutation tolerance

**Raises:**
- `ValueError`: If the pattern length does not match the database k-mer size, the pattern contains invalid characters, or `max_mutations` is rejected by the engine
- `RuntimeError`: If the database cannot be reloaded or the query execution fails

**Example:**
```python
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

db = PyDatabase("example.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)

# Exact-and-neighbors search
result = fuzzy.query_fuzzy("ATCGATCGATCGATCGATCG", max_mutations=2)
print(f"Found {result.total_matches} matches")

# N-wildcard pattern
result = fuzzy.query_fuzzy("GCCCGNNNNNNNNNNNGCC", max_mutations=1)

# Cap the returned matches
result = fuzzy.query_fuzzy("ATCGATCGATCGATCGATCG", 3, max_results=100)
```

#### `query_fuzzy_position(pattern, max_mutations, position_mutations, max_results=None) -> PyFuzzyResult`

Perform a fuzzy query with position-specific mutation constraints.

**Parameters:**
- `pattern` (str): The query pattern (same rules as `query_fuzzy`)
- `max_mutations` (int): Overall maximum number of substitutions
- `position_mutations` (str): Position constraint configuration (see below)
- `max_results` (Optional[int]): Cap on the number of returned matches

**Returns:**
- `PyFuzzyResult`: Matches satisfying both the global tolerance and the position constraints (`has_position_mutations` is `True`)

**Raises:**
- `ValueError`: Invalid pattern or invalid position-mutation configuration
- `RuntimeError`: Database load or execution failure

**Position Mutations Format:**

A semicolon-separated list of groups, each `positions:limit`:
- `"4:1"` — position 4 with a budget of 1 mutation
- `"3,4,5:2"` — positions 3, 4, 5 sharing a budget of 2 mutations
- `"4-7:1"` — positions 4, 5, 6, 7 (range notation) with 1 mutation
- `"3,4:1;6,7:2"` — two independent groups

Positions are 0-indexed.

**Example:**
```python
# Allow mutations only at positions 10 and 15 (max 2 total)
result = fuzzy.query_fuzzy_position("ATCGATCGATCGATCGATCG", 2, "10,15:2")

# Range notation: positions 5-8 with a budget of 1
result = fuzzy.query_fuzzy_position("ATCGATCGATCGATCGATCG", 2, "5-8:1")
```

#### Deprecated methods

`fuzzy_query()` and `fuzzy_query_with_position_mutations()` are deprecated aliases of `query_fuzzy()` and `query_fuzzy_position()` respectively.

#### `kmer_size` (property)

The database's k-mer size, as read when the engine was constructed.

## Performance Considerations

### Combinatorial Explosion

The number of possible variants grows combinatorially with mutation tolerance. For a k-mer of length k:
- Distance 1: k × 3 variants
- Distance 2: k² × 3² variants
- Distance 3: k³ × 3³ variants

Cap the result set with `max_results` and keep the tolerance low:

```python
# Safe: low mutation tolerance
result = fuzzy.query_fuzzy(kmer, max_mutations=1)

# Higher tolerance, capped results
result = fuzzy.query_fuzzy(kmer, max_mutations=3, max_results=1000)
```

### Position Mutations

Position mutations can dramatically reduce the search space by restricting where mutations may occur:

```python
# Much faster than allowing mutations anywhere
result = fuzzy.query_fuzzy_position(kmer, 2, "10,15:2")
```

### Per-Query Database Load

`PyFuzzyQuery` reloads the database from disk each time a query executes, so query time includes I/O. Reuse one `PyFuzzyQuery` for many patterns rather than constructing a new engine per query, and prefer `get_top_matches`/`get_matches_by_distance` for repeated slicing of the same result instead of re-querying.

## Use Cases

### Error Correction

Find potential correct versions of erroneous k-mers:

```python
def find_corrections(fuzzy, erroneous_kmer, max_mutations=2):
    """Find potential corrections for an erroneous k-mer."""
    result = fuzzy.query_fuzzy(erroneous_kmer, max_mutations=max_mutations)

    # Sort by abundance (most likely to be correct)
    candidates = result.get_top_matches(5)

    corrections = []
    for match in candidates:
        if match.distance and match.distance > 0:
            corrections.append({
                'corrected': match.kmer,
                'distance': match.distance,
                'confidence': match.count,
            })

    return corrections
```

### Variant Discovery

Find variants of a known sequence grouped by distance:

```python
def discover_variants(fuzzy, reference_kmer, max_mutations=3):
    """Discover variants of a reference sequence."""
    result = fuzzy.query_fuzzy(reference_kmer, max_mutations=max_mutations)

    variants = {}
    for distance in range(1, max_mutations + 1):
        variants[distance] = result.get_matches_by_distance(distance)

    return variants

# Example
variants = discover_variants(fuzzy, "ATCGATCGATCGATCGATCG")

for distance, matches in variants.items():
    print(f"Distance {distance}: {len(matches)} variants")
    for match in matches[:3]:
        print(f"  {match.kmer}: {match.count}")
```

### Quality Control

Assess sequencing quality by comparing exact and neighboring k-mer abundance:

```python
def assess_sequencing_quality(fuzzy, high_confidence_kmers, max_mutations=2):
    """Assess sequencing quality using high-confidence k-mers."""
    quality_metrics = {}

    for kmer in high_confidence_kmers:
        result = fuzzy.query_fuzzy(kmer, max_mutations=max_mutations)

        exact_count = result.exact_match.count if result.exact_match else 0
        total_abundance = sum(m.count for m in result.matches)

        error_rate = (total_abundance - exact_count) / total_abundance \
            if total_abundance > 0 else 0

        quality_metrics[kmer] = {
            'exact_matches': exact_count,
            'neighbor_matches': len(result.matches),
            'error_rate': error_rate,
            'total_abundance': total_abundance,
        }

    return quality_metrics
```

## Integration Examples

### Pandas Integration

```python
import pandas as pd
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

def fuzzy_query_to_dataframe(db_path, query_kmer, max_mutations=2):
    """Convert a fuzzy query result to a pandas DataFrame."""
    db = PyDatabase(db_path, LoadMode.Preload)
    fuzzy = PyFuzzyQuery(db)
    result = fuzzy.query_fuzzy(query_kmer, max_mutations=max_mutations)

    data = [{
        'query_kmer': query_kmer,
        'matched_kmer': match.kmer,
        'count': match.count,
        'distance': match.distance,
        'match_type': match.match_type,
    } for match in result.matches]

    return pd.DataFrame(data)

# Usage
df = fuzzy_query_to_dataframe(
    "example.rkdb", "ATCGATCGATCGATCGATCG", max_mutations=2)

print(f"Distance distribution:\n{df['distance'].value_counts().sort_index()}")
print(f"\nTop matches:\n{df.nlargest(10, 'count')[['matched_kmer', 'count', 'distance']]}")
```

### NumPy Integration

```python
import numpy as np
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

def analyze_mutation_spectrum(db_path, reference_kmer, max_mutations=3):
    """Analyze the mutation spectrum using NumPy."""
    db = PyDatabase(db_path, LoadMode.Preload)
    fuzzy = PyFuzzyQuery(db)
    result = fuzzy.query_fuzzy(reference_kmer, max_mutations=max_mutations)

    distances = np.array([m.distance or 0 for m in result.matches])
    counts = np.array([m.count for m in result.matches])

    total_abundance = np.sum(counts)
    weighted_distance = np.average(distances, weights=counts) if total_abundance else 0

    return {
        'reference': reference_kmer,
        'total_matches': result.total_matches,
        'total_abundance': int(total_abundance),
        'weighted_distance': weighted_distance,
    }
```

### JSON Export

```python
import json
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

db = PyDatabase("genome.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
result = fuzzy.query_fuzzy("ATCGATCGATCGATCGATCG", max_mutations=2)

with open("fuzzy_result.json", "w") as f:
    f.write(result.to_json())
```

This API reference provides comprehensive documentation for rustkmer's fuzzy query functionality, including all classes, methods, and practical usage examples for advanced bioinformatics applications.
