# FuzzyQuery API Reference

Complete reference for RustKmer's fuzzy query functionality in Python.

## Overview

The `FuzzyQuery` class provides advanced k-mer searching capabilities with support for wildcards, mutation tolerance, and complex pattern matching. It extends the basic `Database` functionality to handle flexible and error-tolerant queries.

## Classes

### FuzzyQueryResult

Represents a single fuzzy query match result.

```python
class FuzzyQueryResult:
    def __init__(self):
        self.kmer: str = ""           # Matching k-mer sequence
        self.count: int = 0           # Number of occurrences
        self.distance: int = 0        # Hamming distance from query
        self.match_type: str = ""     # Type of match (exact, wildcard, mutation)
        self.positions: List[int] = []  # Positions of differences
```

**Attributes:**
- `kmer` (str): The matching k-mer sequence
- `count` (int): Number of times this k-mer appears in the database
- `distance` (int): Hamming distance from the original query
- `match_type` (str): Classification of the match type
- `positions` (List[int]): Positions where differences occur

### QueryMetadata

Metadata about the fuzzy query execution.

```python
class QueryMetadata:
    def __init__(self):
        self.query_time_ms: int = 0           # Query execution time in milliseconds
        self.variants_generated: int = 0      # Number of variants generated
        self.memory_usage_mb: float = 0.0     # Memory usage in MB
        self.database_size: int = 0           # Database size in k-mers
```

## Database Methods

### fuzzy_query()

Perform a fuzzy search with wildcards and mutation tolerance.

```python
def fuzzy_query(self,
                pattern: str,
                max_distance: int = 0,
                max_variants: Optional[int] = None,
                parallel: bool = False,
                batch_size: int = 1000) -> List[FuzzyQueryResult]:
    """
    Perform fuzzy k-mer query with pattern matching.

    Args:
        pattern: Query pattern with optional wildcards (N)
        max_distance: Maximum Hamming distance for mutations
        max_variants: Maximum variants to generate (default: 10000)
        parallel: Enable parallel processing
        batch_size: Batch size for processing

    Returns:
        List of FuzzyQueryResult objects

    Raises:
        ValueError: If pattern is invalid
        RuntimeError: If query execution fails
    """
```

**Parameters:**
- `pattern` (str): Query pattern containing A, T, C, G, and N (wildcard)
- `max_distance` (int, optional): Maximum allowed mutations (default: 0)
- `max_variants` (int, optional): Maximum variants to prevent explosion (default: 10000)
- `parallel` (bool, optional): Use parallel processing (default: False)
- `batch_size` (int, optional): Processing batch size (default: 1000)

**Returns:**
- `List[FuzzyQueryResult]`: List of matching k-mers with metadata

**Examples:**

```python
from rustkmer import Database

db = Database()
db.load("genome.rkdb")

# Basic wildcard search
results = db.fuzzy_query("ATNNGTA")

# Search with mutation tolerance
results = db.fuzzy_query("ATCGATCGATCGATCGATCGA", max_distance=2)

# Complex query with optimization
results = db.fuzzy_query(
    pattern="ANNNNNNGT",
    max_distance=1,
    max_variants=5000,
    parallel=True,
    batch_size=500
)
```

### fuzzy_query_batch()

Perform multiple fuzzy queries efficiently.

```python
def fuzzy_query_batch(self,
                      patterns: List[str],
                      max_distance: int = 0,
                      max_variants: Optional[int] = None,
                      parallel: bool = False) -> Dict[str, List[FuzzyQueryResult]]:
    """
    Perform batch fuzzy query processing.

    Args:
        patterns: List of query patterns
        max_distance: Maximum Hamming distance for mutations
        max_variants: Maximum variants per pattern
        parallel: Enable parallel processing

    Returns:
        Dictionary mapping patterns to result lists
    """
```

**Parameters:**
- `patterns` (List[str]): List of query patterns
- `max_distance` (int, optional): Maximum allowed mutations (default: 0)
- `max_variants` (int, optional): Maximum variants per pattern (default: 10000)
- `parallel` (bool, optional): Use parallel processing (default: False)

**Returns:**
- `Dict[str, List[FuzzyQueryResult]]`: Results keyed by pattern

**Example:**

```python
patterns = ["ATNNGTA", "ANNNNNNGT", "GTCGATCNN"]
results = db.fuzzy_query_batch(patterns, max_distance=2)

for pattern, matches in results.items():
    print(f"Pattern '{pattern}': {len(matches)} matches")
    for match in matches[:3]:  # Show top 3
        print(f"  {match.kmer}: {match.count}")
```

### get_last_query_stats()

Get statistics from the most recent fuzzy query.

```python
def get_last_query_stats(self) -> QueryMetadata:
    """
    Get metadata from the most recent fuzzy query execution.

    Returns:
        QueryMetadata object with execution statistics
    """
```

**Returns:**
- `QueryMetadata`: Statistics about the last query execution

**Example:**

```python
results = db.fuzzy_query("ATNNGTA", max_distance=2)
stats = db.get_last_query_stats()

print(f"Query time: {stats.query_time_ms}ms")
print(f"Variants generated: {stats.variants_generated}")
print(f"Memory used: {stats.memory_usage_mb}MB")
```

## Utility Functions

### calculate_hamming_distance()

Calculate Hamming distance between two sequences.

```python
def calculate_hamming_distance(seq1: str, seq2: str) -> int:
    """
    Calculate Hamming distance between two equal-length sequences.

    Args:
        seq1: First sequence
        seq2: Second sequence

    Returns:
        Hamming distance (number of differing positions)

    Raises:
        ValueError: If sequences have different lengths
    """
```

### expand_wildcard_pattern()

Expand a pattern with wildcards to all possible combinations.

```python
def expand_wildcard_pattern(pattern: str, max_combinations: int = 10000) -> List[str]:
    """
    Expand wildcard pattern to all possible k-mers.

    Args:
        pattern: Pattern with N wildcards
        max_combinations: Maximum combinations to generate

    Returns:
        List of expanded k-mers

    Raises:
        ValueError: If pattern would exceed max_combinations
    """
```

**Example:**

```python
# Expand simple pattern
variants = expand_wildcard_pattern("ATN")  # ["ATA", "ATT", "ATC", "ATG"]

# Expand with limit
variants = expand_wildcard_pattern("ATNN", max_combinations=16)
```

### validate_pattern()

Validate a query pattern before execution.

```python
def validate_pattern(pattern: str) -> bool:
    """
    Validate if a pattern is suitable for fuzzy query.

    Args:
        pattern: Query pattern to validate

    Returns:
        True if valid, False otherwise

    Raises:
        ValueError: If pattern is invalid
    """
```

**Example:**

```python
try:
    validate_pattern("ATNNGTA")  # Valid
    validate_pattern("ATXG")     # Invalid: X not allowed
except ValueError as e:
    print(f"Invalid pattern: {e}")
```

## Match Types

The `match_type` field in `FuzzyQueryResult` indicates how the match was found:

- **"Exact"**: Exact match with no differences
- **"WildcardExpansion"**: Match from wildcard expansion
- **"MutationTolerance"**: Match within mutation distance
- **"LengthNormalization"**: Match after length adjustment
- **"Combined"**: Combination of wildcard and mutation matching

## Performance Considerations

### Parallel Processing

Enable parallel processing for complex queries:

```python
# For complex patterns with many wildcards
results = db.fuzzy_query(
    pattern="ANNNNNNGT",
    max_distance=2,
    parallel=True,
    batch_size=1000
)
```

### Memory Management

For large-scale queries:

```python
# Process in batches to manage memory
batch_size = 100
all_results = []

for i in range(0, len(patterns), batch_size):
    batch = patterns[i:i+batch_size]
    batch_results = db.fuzzy_query_batch(
        batch,
        max_distance=2,
        max_variants=5000  # Conservative limit
    )
    all_results.extend(batch_results.items())
```

### Query Optimization

Optimize queries for better performance:

```python
def optimized_query(db, pattern, max_distance=2):
    """Optimize fuzzy query based on pattern complexity."""

    wildcard_count = pattern.count('N')

    # Adjust parameters based on complexity
    if wildcard_count == 0:
        # Exact pattern, can use higher distance
        return db.fuzzy_query(pattern, max_distance=max_distance)

    elif wildcard_count <= 2:
        # Moderate complexity
        return db.fuzzy_query(
            pattern,
            max_distance=max_distance,
            max_variants=5000,
            parallel=True
        )

    else:
        # High complexity, be conservative
        return db.fuzzy_query(
            pattern,
            max_distance=min(max_distance, 1),
            max_variants=1000,
            batch_size=100
        )
```

## Error Handling

### Common Exceptions

```python
from rustkmer import Database, FuzzyQueryError

try:
    results = db.fuzzy_query("ATNNGTA", max_distance=2)
except ValueError as e:
    # Invalid pattern or parameters
    print(f"Invalid query: {e}")
except FuzzyQueryError as e:
    # Query execution error
    if "combinatorial explosion" in str(e):
        print("Query too complex - reduce wildcards or distance")
    elif "memory" in str(e).lower():
        print("Memory error - try smaller batch size")
    else:
        print(f"Query failed: {e}")
except RuntimeError as e:
    # System-level error
    print(f"System error: {e}")
```

### Validation Before Query

```python
def safe_fuzzy_query(db, pattern, max_distance=2):
    """Perform fuzzy query with comprehensive validation."""

    # Validate pattern
    if not pattern:
        raise ValueError("Pattern cannot be empty")

    if len(pattern) < 3:
        raise ValueError("Pattern too short (minimum 3 characters)")

    # Check for valid characters
    valid_chars = set('ATCGN')
    if not all(char in valid_chars for char in pattern.upper()):
        raise ValueError("Pattern contains invalid characters")

    # Estimate complexity
    complexity = 4 ** pattern.count('N')
    if complexity > 50000:
        print(f"Warning: Pattern will generate {complex:,} variants")

    # Execute query with conservative limits
    return db.fuzzy_query(
        pattern,
        max_distance=max_distance,
        max_variants=min(10000, complexity),
        parallel=complexity > 1000
    )
```

## Integration Examples

### Pandas Integration

```python
import pandas as pd
from rustkmer import Database

def query_to_dataframe(results, pattern):
    """Convert fuzzy query results to pandas DataFrame."""

    data = []
    for result in results:
        data.append({
            'pattern': pattern,
            'kmer': result.kmer,
            'count': result.count,
            'distance': result.distance,
            'match_type': result.match_type
        })

    return pd.DataFrame(data)

# Usage
db = Database()
db.load("genome.rkdb")

results = db.fuzzy_query("ATNNGTA", max_distance=2)
df = query_to_dataframe(results, "ATNNGTA")

# Analyze results
print(df.describe())
print(f"\nTop matches:\n{df.nlargest(10, 'count')}")
```

### Biopython Integration

```python
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from rustkmer import Database

def find_primer_matches(db, fasta_file, max_mismatches=2):
    """Find primer matches in sequences from FASTA file."""

    # Extract potential primers (21-mers)
    primers = []
    for record in SeqIO.parse(fasta_file, "fasta"):
        seq = str(record.seq).upper()
        for i in range(len(seq) - 21 + 1):
            primer = seq[i:i+21]
            primers.append((record.id, i, primer))

    # Search for matches
    matches = []
    for record_id, position, primer in primers:
        results = db.fuzzy_query(primer, max_distance=max_mismatches)

        for result in results:
            if result.distance <= max_mismatches:
                matches.append({
                    'source_record': record_id,
                    'primer_position': position,
                    'primer_sequence': primer,
                    'matched_kmer': result.kmer,
                    'count': result.count,
                    'distance': result.distance
                })

    return matches
```

### NumPy Integration

```python
import numpy as np
from rustkmer import Database

def analyze_kmer_variants(db, reference_kmer, max_distance=3):
    """Analyze variants around a reference using NumPy."""

    results = db.fuzzy_query(reference_kmer, max_distance=max_distance)

    # Convert to NumPy arrays for analysis
    kmers = np.array([r.kmer for r in results])
    counts = np.array([r.count for r in results])
    distances = np.array([r.distance for r in results])

    # Statistical analysis
    total_count = np.sum(counts)
    weighted_distance = np.average(distances, weights=counts)

    # Group by distance
    unique_distances = np.unique(distances)
    distance_stats = {}

    for dist in unique_distances:
        mask = distances == dist
        distance_stats[dist] = {
            'count': np.sum(mask),
            'total_occurrences': np.sum(counts[mask]),
            'mean_count': np.mean(counts[mask])
        }

    return {
        'reference': reference_kmer,
        'total_variants': len(results),
        'total_occurrences': total_count,
        'weighted_distance': weighted_distance,
        'distance_breakdown': distance_stats
    }
```

## Reference Implementation

Here's a complete example showing all major features:

```python
from rustkmer import Database
import json
import time

def comprehensive_fuzzy_analysis(db_path, patterns_file, output_file):
    """
    Comprehensive fuzzy query analysis with multiple patterns.

    Args:
        db_path: Path to RKDB database
        patterns_file: File containing query patterns (one per line)
        output_file: JSON output file for results
    """

    # Load database
    print(f"Loading database: {db_path}")
    db = Database()
    db.load(db_path)

    # Read patterns
    with open(patterns_file, 'r') as f:
        patterns = [line.strip() for line in f if line.strip()]

    print(f"Processing {len(patterns)} patterns...")

    # Process all patterns
    all_results = {}
    total_time = 0

    for i, pattern in enumerate(patterns, 1):
        print(f"[{i}/{len(patterns)}] Processing: {pattern}")

        try:
            start_time = time.time()

            # Perform fuzzy query with optimization
            results = db.fuzzy_query(
                pattern=pattern,
                max_distance=2,
                max_variants=5000,
                parallel=True,
                batch_size=1000
            )

            query_time = time.time() - start_time
            total_time += query_time

            # Get query statistics
            stats = db.get_last_query_stats()

            # Convert to serializable format
            all_results[pattern] = {
                'matches': len(results),
                'total_count': sum(r.count for r in results),
                'query_time_ms': stats.query_time_ms,
                'variants_generated': stats.variants_generated,
                'memory_usage_mb': stats.memory_usage_mb,
                'results': [
                    {
                        'kmer': r.kmer,
                        'count': r.count,
                        'distance': r.distance,
                        'match_type': r.match_type
                    }
                    for r in results[:20]  # Top 20 results
                ]
            }

            print(f"  ✓ Found {len(results)} matches in {query_time:.2f}s")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            all_results[pattern] = {'error': str(e)}

    # Save results
    summary = {
        'database': db_path,
        'patterns_processed': len(patterns),
        'total_time_seconds': total_time,
        'average_time_per_pattern': total_time / len(patterns),
        'results': all_results
    }

    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\nAnalysis complete. Results saved to: {output_file}")
    print(f"Total time: {total_time:.2f} seconds")

# Usage
comprehensive_fuzzy_analysis(
    db_path="genome_k21.rkdb",
    patterns_file="queries.txt",
    output_file="fuzzy_analysis_results.json"
)
```

This API reference provides complete documentation for RustKmer's fuzzy query functionality, including all methods, parameters, examples, and integration patterns.