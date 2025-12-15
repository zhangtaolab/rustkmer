# Fuzzy Query Guide

Complete guide to fuzzy k-mer queries with RustKmer, supporting wildcard patterns, mutation tolerance, and advanced pattern matching.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Query Types](#query-types)
- [Python API](#python-api)
- [Command Line Interface](#command-line-interface)
- [Batch Processing](#batch-processing)
- [Export Options](#export-options)
- [Performance Optimization](#performance-optimization)
- [Use Cases](#use-cases)
- [Best Practices](#best-practices)

## Overview

RustKmer's fuzzy query functionality allows you to search for k-mers with flexibility and tolerance, supporting:

- **Wildcard Searches**: Use `N` to match any nucleotide (A, T, C, G)
- **Mutation Tolerance**: Find k-mers within a specified Hamming distance
- **Pattern Matching**: Complex queries with multiple wildcards and constraints
- **High Performance**: Optimized algorithms for large-scale searches

### Key Benefits

- 🔍 **Flexible Search**: Handle ambiguous sequences and variations
- 🧬 **Biological Relevance**: Model real-world mutations and sequencing errors
- ⚡ **High Performance**: Efficient algorithms for genome-scale data
- 📊 **Rich Results**: Detailed match information and statistics

## Quick Start

### Python API

```python
from rustkmer import Database

# Load database
db = Database()
db.load("genome_k21.rkdb")

# Wildcard search
results = db.fuzzy_query("ATNNGTA")  # N matches any base
print(f"Found {len(results)} matches")

# Mutation tolerance search
results = db.fuzzy_query("ATCGATCGATCGATCGATCGA", max_distance=2)
print(f"Found {len(results)} variants within distance 2")

# Process results
for result in results:
    print(f"{result.kmer}: {result.count} (distance: {result.distance})")
```

### Command Line

```bash
# Basic wildcard search
rustkmer fuzzy-query -d genome_k21.rkdb -q "ATNNGTA"

# Search with mutation tolerance
rustkmer fuzzy-query -d genome_k21.rkdb -q "ATCGATCGATCGATCGATCGA" -m 2

# Export results to CSV
rustkmer fuzzy-query -d genome_k21.rkdb -q "ATNNGTA" -o results.csv -f csv

# Batch processing from file
rustkmer fuzzy-query -d genome_k21.rkdb -f queries.txt -o all_results.json
```

## Query Types

### 1. Wildcard Queries

Use `N` in your query to match any nucleotide. Each `N` expands to 4 possibilities (A, T, C, G).

```python
# Single wildcard
results = db.fuzzy_query("ATN")  # Expands to: ATA, ATT, ATC, ATG

# Multiple wildcards
results = db.fuzzy_query("ATNN")  # Expands to 16 combinations (4²)

# Complex pattern
results = db.fuzzy_query("ATNNGTANN")  # 4⁴ = 256 combinations
```

**Complexity Warning**: Be careful with multiple wildcards as the number of combinations grows exponentially (4^n where n is the number of wildcards).

### 2. Mutation Tolerance Queries

Find k-mers within a specified Hamming distance (number of mutations).

```python
# Exact match (distance 0)
results = db.fuzzy_query("ATCGATCGATCGATCGATCGA", max_distance=0)

# Allow 1 mutation
results = db.fuzzy_query("ATCGATCGATCGATCGATCGA", max_distance=1)

# Allow up to 3 mutations
results = db.fuzzy_query("ATCGATCGATCGATCGATCGA", max_distance=3)
```

### 3. Combined Queries

Combine wildcards and mutation tolerance for maximum flexibility.

```python
# Wildcard + mutation tolerance
results = db.fuzzy_query("ATNNGTA", max_distance=1)
# 1. Expand wildcards: 16 combinations
# 2. Apply mutation tolerance to each combination
```

## Python API

### Basic Usage

```python
from rustkmer import Database

# Load database
db = Database()
db.load("database.rkdb")

# Perform fuzzy query
results = db.fuzzy_query("ATNNGTA", max_distance=2)

# Results are returned as a list of FuzzyQueryResult objects
for result in results:
    print(f"K-mer: {result.kmer}")
    print(f"Count: {result.count}")
    print(f"Distance: {result.distance}")
    print(f"Match type: {result.match_type}")
    print("---")
```

### Advanced Options

```python
# Query with specific parameters
results = db.fuzzy_query(
    pattern="ATNNGTA",
    max_distance=2,
    max_variants=10000,  # Limit total variants to prevent combinatorial explosion
    parallel=True,       # Enable parallel processing
    batch_size=1000      # Batch size for processing
)

# Get query statistics
stats = db.get_last_query_stats()
print(f"Query time: {stats.query_time_ms}ms")
print(f"Variants generated: {stats.variants_generated}")
print(f"Memory used: {stats.memory_usage_mb}MB")
```

### Result Filtering

```python
# Filter results by count
filtered_results = [r for r in results if r.count >= 100]

# Filter by distance
exact_matches = [r for r in results if r.distance == 0]
close_matches = [r for r in results if r.distance <= 2]

# Sort by count
results_sorted = sorted(results, key=lambda x: x.count, reverse=True)

# Get top N matches
top_matches = results_sorted[:10]
```

### Error Handling

```python
try:
    results = db.fuzzy_query("ATNNGTA", max_distance=2)
except ValueError as e:
    print(f"Invalid query: {e}")
except RuntimeError as e:
    print(f"Query execution failed: {e}")
```

## Command Line Interface

### Basic Syntax

```bash
rustkmer fuzzy-query [OPTIONS] <DATABASE> <QUERY>
```

### Core Options

- `-d, --database <DATABASE>`: Database file path
- `-q, --query <QUERY>`: Query string with optional wildcards
- `-m, --mutations <MUTATIONS>`: Maximum mutation distance [default: 0]
- `-M, --max-variants <MAX_VARIANTS>`: Maximum variants to generate [default: 10000]
- `-f, --format <FORMAT>`: Output format [table|json|csv|tsv] [default: table]
- `-o, --output <OUTPUT>`: Output file path
- `-p, --parallel`: Enable parallel processing
- `-b, --batch-size <BATCH_SIZE>`: Batch processing size [default: 1000]

### Examples

```bash
# Basic wildcard search
rustkmer fuzzy-query -d genome.rkdb -q "ATNNGTA"

# Mutation tolerance search
rustkmer fuzzy-query -d genome.rkdb -q "ATCGATCGATCGATCGATCGA" -m 2

# JSON output with parallel processing
rustkmer fuzzy-query -d genome.rkdb -q "ATNNGTA" -f json -p -o results.json

# Batch processing from file
rustkmer fuzzy-query -d genome.rkdb --query-file queries.txt -o all_results.csv

# Custom limits for complex queries
rustkmer fuzzy-query -d genome.rkdb -q "ANNNNNNGT" -m 1 -M 5000 -b 500
```

### Query File Format

For batch processing, create a text file with one query per line:

```
# queries.txt
ATNNGTA
ATCGATCGATCGATCGATCGA
ANNNNNNGT
GTCGATCNNTACG
```

Then run:

```bash
rustkmer fuzzy-query -d genome.rkdb --query-file queries.txt -o batch_results.json
```

## Important Note: N's in Queries

When using N characters in queries, be aware of the different default behavior between CLI and Python API:

- **CLI**: Default `mutations=0` (exact match only)
- **Python API**: Default `mutations=1` (allows 1 mutation by default)

This means the same query will return different results depending on which interface you use. See [Fuzzy Query with N's: Behavior and Best Practices](fuzzy_query_n_behavior.md) for detailed information.

## Batch Processing

### Processing Multiple Queries

```python
from rustkmer import Database
import json

# Load database once
db = Database()
db.load("genome.rkdb")

# List of queries to process
queries = [
    "ATNNGTA",
    "ATCGATCGATCGATCGATCGA",
    "ANNNNNNGT",
    "GTCGATCNNTACG"
]

# Process all queries
all_results = {}
for query in queries:
    try:
        results = db.fuzzy_query(query, max_distance=2)
        all_results[query] = [
            {
                "kmer": r.kmer,
                "count": r.count,
                "distance": r.distance
            }
            for r in results
        ]
    except Exception as e:
        all_results[query] = {"error": str(e)}

# Save results to JSON
with open("batch_results.json", "w") as f:
    json.dump(all_results, f, indent=2)
```

### Efficient Batch Processing

```python
def process_query_batch(db, queries, max_distance=2):
    """Efficiently process a batch of queries."""

    results = {}

    # Group queries by complexity
    simple_queries = [q for q in queries if q.count('N') <= 1]
    complex_queries = [q for q in queries if q.count('N') > 1]

    # Process simple queries first
    for query in simple_queries:
        try:
            results[query] = db.fuzzy_query(query, max_distance=max_distance)
        except Exception as e:
            results[query] = {"error": str(e)}
            print(f"Error processing {query}: {e}")

    # Process complex queries with stricter limits
    for query in complex_queries:
        try:
            results[query] = db.fuzzy_query(
                query,
                max_distance=max_distance,
                max_variants=5000,  # Stricter limit for complex queries
                batch_size=500      # Smaller batch size
            )
        except Exception as e:
            results[query] = {"error": str(e)}
            print(f"Error processing {query}: {e}")

    return results

# Usage
batch_results = process_query_batch(db, queries, max_distance=2)
```

## Export Options

### Table Format (Default)

```bash
rustkmer fuzzy-query -d genome.rkdb -q "ATNNGTA" -f table
```

Output:
```
K-mer              Count    Distance    Match Type
ATATGTA            1250     0           Exact
ATTGTA             892      1           Mutation
ATCGGTA            756      1           Mutation
ATAGGTA            623      1           Mutation
...
```

### JSON Format

```bash
rustkmer fuzzy-query -d genome.rkdb -q "ATNNGTA" -f json
```

Output:
```json
{
  "query": "ATNNGTA",
  "max_distance": 0,
  "total_matches": 4,
  "total_count": 3521,
  "query_time_ms": 15,
  "results": [
    {
      "kmer": "ATATGTA",
      "count": 1250,
      "distance": 0,
      "match_type": "WildcardExpansion"
    },
    {
      "kmer": "ATTGTA",
      "count": 892,
      "distance": 1,
      "match_type": "WildcardExpansion"
    }
  ],
  "metadata": {
    "variants_generated": 16,
    "database_size": 150000000,
    "memory_usage_mb": 2.1
  }
}
```

### CSV Format

```bash
rustkmer fuzzy-query -d genome.rkdb -q "ATNNGTA" -f csv -o results.csv
```

CSV output includes headers: `kmer,count,distance,match_type`

### TSV Format

```bash
rustkmer fuzzy-query -d genome.rkdb -q "ATNNGTA" -f tsv -o results.tsv
```

Tab-separated values format for easy integration with spreadsheet applications.

## Performance Optimization

### Query Design Best Practices

1. **Limit Wildcards**: Use minimum necessary wildcards
   ```python
   # Good: Specific pattern
   results = db.fuzzy_query("ATNNGTA")  # 16 variants

   # Avoid: Too many wildcards
   results = db.fuzzy_query("NNNNNNNN")  # 65,536 variants
   ```

2. **Use Appropriate Mutation Distance**:
   ```python
   # For exact matches: distance = 0
   # For close variants: distance = 1-2
   # For distant variants: distance = 3+
   ```

3. **Set Variant Limits**:
   ```python
   # Prevent combinatorial explosion
   results = db.fuzzy_query("ATNNGTA", max_variants=5000)
   ```

### Memory Optimization

```python
# For large databases, use memory mapping
db = Database()
db.load("large_db.rkdb", memory_mapped=True)

# Process queries in batches
batch_size = 100
for i in range(0, len(queries), batch_size):
    batch = queries[i:i+batch_size]
    process_batch(db, batch)
```

### Parallel Processing

```python
# Enable parallel processing for complex queries
results = db.fuzzy_query(
    "ATNNGTA",
    max_distance=2,
    parallel=True,
    batch_size=1000  # Optimal batch size for parallel processing
)
```

## Use Cases

### 1. SNP Detection

```python
def detect_snps(db, reference_kmer, min_frequency=0.01):
    """Detect SNPs around a reference sequence."""

    # Find all single-mutation variants
    variants = db.fuzzy_query(reference_kmer, max_distance=1)

    # Calculate total count
    total = sum(r.count for r in variants) + db.query(reference_kmer).count

    # Filter significant variants
    significant_snps = []
    for variant in variants:
        if variant.distance == 1:  # Only single mutations
            frequency = variant.count / total
            if frequency >= min_frequency:
                significant_snps.append({
                    'kmer': variant.kmer,
                    'count': variant.count,
                    'frequency': frequency,
                    'mutation': identify_mutation(reference_kmer, variant.kmer)
                })

    return significant_snps
```

### 2. Primer Design

```python
def design_primers(db, target_sequence, primer_length=20):
    """Design primers with tolerance for mismatches."""

    primers = []
    for i in range(len(target_sequence) - primer_length + 1):
        primer = target_sequence[i:i+primer_length]

        # Allow 2 mismatches at the 3' end
        results = db.fuzzy_query(primer, max_distance=2)

        if results:
            # Calculate binding strength
            total_binding = sum(r.count for r in results if r.distance <= 1)

            primers.append({
                'sequence': primer,
                'position': i,
                'binding_strength': total_binding,
                'matches': len(results)
            })

    # Sort by binding strength
    primers.sort(key=lambda x: x['binding_strength'], reverse=True)
    return primers[:10]  # Top 10 candidates
```

### 3. Motif Discovery

```python
def discover_motifs(db, seed_pattern, min_occurrences=50):
    """Discover related motifs using fuzzy search."""

    # Find similar patterns
    results = db.fuzzy_query(seed_pattern, max_distance=3)

    # Filter by frequency
    significant = [r for r in results if r.count >= min_occurrences]

    # Group by distance
    distance_groups = {}
    for r in significant:
        if r.distance not in distance_groups:
            distance_groups[r.distance] = []
        distance_groups[r.distance].append(r)

    return distance_groups
```

## Best Practices

### 1. Query Planning

Before running fuzzy queries, consider:

- **Query Complexity**: Number of wildcards and mutation distance
- **Database Size**: Larger databases may need longer timeouts
- **Result Size**: Anticipated number of matches

### 2. Error Handling

Always handle potential errors:

```python
try:
    results = db.fuzzy_query("ATNNGTA", max_distance=2)
except ValueError as e:
    print(f"Invalid query: {e}")
except RuntimeError as e:
    if "combinatorial explosion" in str(e):
        print("Query too complex, try reducing wildcards or mutation distance")
    else:
        print(f"Execution error: {e}")
```

### 3. Performance Monitoring

Monitor query performance:

```python
import time

start_time = time.time()
results = db.fuzzy_query("ATNNGTA", max_distance=2)
end_time = time.time()

print(f"Query completed in {end_time - start_time:.2f} seconds")
print(f"Found {len(results)} matches")
print(f"Average: {len(results)/(end_time - start_time):.0f} matches/second")
```

### 4. Result Validation

Validate results for biological relevance:

```python
def validate_results(results, expected_gc_range=(0.4, 0.6)):
    """Validate results based on biological constraints."""

    valid_results = []
    for result in results:
        # Check GC content
        gc_content = (result.kmer.count('G') + result.kmer.count('C')) / len(result.kmer)

        if expected_gc_range[0] <= gc_content <= expected_gc_range[1]:
            valid_results.append(result)

    return valid_results
```

## Troubleshooting

### Common Issues

1. **Combinatorial Explosion**
   - **Problem**: Too many wildcards or high mutation distance
   - **Solution**: Reduce wildcards or set lower `max_variants`

2. **Memory Issues**
   - **Problem**: Large database or many results
   - **Solution**: Use memory mapping and batch processing

3. **Slow Queries**
   - **Problem**: Complex queries on large databases
   - **Solution**: Enable parallel processing, optimize query design

4. **No Results**
   - **Problem**: Query too specific or database mismatch
   - **Solution**: Reduce mutation distance, check database k-mer size

### Debug Mode

Enable debug output for troubleshooting:

```python
# Enable verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Query with statistics
results = db.fuzzy_query("ATNNGTA", max_distance=2)
stats = db.get_last_query_stats()
print(f"Query stats: {stats}")
```

## Advanced Features

### Custom Scoring

Implement custom scoring for results:

```python
def score_results(results, query, position_weights=None):
    """Score results based on position-specific importance."""

    if position_weights is None:
        # Default: higher weight for central positions
        position_weights = [1, 2, 3, 4, 5, 4, 3, 2, 1]

    scored_results = []
    for result in results:
        score = 0

        # Add position-specific scores
        for i, (q_base, r_base) in enumerate(zip(query, result.kmer)):
            if i < len(position_weights) and q_base == r_base:
                score += position_weights[i]

        # Add count bonus
        score += result.count // 100

        scored_results.append((result, score))

    # Sort by score
    scored_results.sort(key=lambda x: x[1], reverse=True)
    return [result for result, score in scored_results]
```

### Pattern Libraries

Create reusable pattern libraries:

```python
PATTERNS = {
    'promoter': ['TATAAA', 'CAAT', 'GGCCGG'],
    'terminator': ['ATGCA', 'TAA'],
    'restriction_site': ['GAATTC', 'GGATCC', 'CTGCAG']
}

def search_pattern_library(db, pattern_type, max_distance=1):
    """Search all patterns of a specific type."""

    patterns = PATTERNS.get(pattern_type, [])
    all_results = {}

    for pattern in patterns:
        results = db.fuzzy_query(pattern, max_distance=max_distance)
        all_results[pattern] = results

    return all_results
```

This guide provides a comprehensive overview of RustKmer's fuzzy query capabilities. For more specific examples and advanced use cases, see the [Examples](examples/fuzzy-search.md) section.