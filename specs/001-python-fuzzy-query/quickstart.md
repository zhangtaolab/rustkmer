# Quick Start: Python Fuzzy Query API

## Installation
```bash
# Ensure rustkmer is installed and available in PATH
pip install rustkmer
```

## Basic Usage

### Single Fuzzy Query
```python
from rustkmer import Database

# Open a k-mer database
with Database("genome.rkdb") as db:
    # Query for similar sequences with 1 mutation tolerance
    result = db.fuzzy_query("ATCGATCGATCGATCG", mutations=1)

    print(f"Query: {result.query_kmer}")
    print(f"Total matches: {result.total_matches}")

    if result.has_exact_match:
        print(f"Exact match count: {result.exact_match.count}")

    # Display top 5 most abundant variants
    for match in result.get_top_matches(5):
        print(f"{match.kmer}: {match.count} (distance={match.distance})")
```

### Batch Fuzzy Queries
```python
from rustkmer import Database

# Multiple k-mers to query
kmers = [
    "ATCGATCGATCGATCG",
    "CGATCGATCGATCGAT",
    "GATCGATCGATCGATC"
]

with Database("genome.rkdb") as db:
    # Process all queries in parallel
    batch_result = db.fuzzy_query_batch(kmers, mutations=2)

    # View summary
    print(batch_result.get_summary_table())

    # Access individual results
    for result in batch_result.query_results:
        if result.matches:
            print(f"\n{result.query_kmer}:")
            # Group by distance
            for distance, matches in result.get_matches_by_distance().items():
                print(f"  Distance {distance}: {len(matches)} matches")
```

## Working with Results

### Exporting Results
```python
# JSON format (for programmatic use)
json_str = result.to_json()
with open("results.json", "w") as f:
    f.write(json_str)

# Table format (for human reading)
table = result.to_table(max_rows=20)
print(table)

# Access individual match data
for match in result.matches:
    if match.mutations:
        print(f"K-mer: {match.kmer}")
        print(f"  Mutations: {', '.join(match.mutations)}")
        print(f"  Count: {match.count}")
```

### Mutation Analysis
```python
# Find mutation hotspots
mutation_counts = {}
for match in result.matches:
    for mutation in match.mutations:
        mutation_counts[mutation] = mutation_counts.get(mutation, 0) + match.count

# Most common mutations
for mutation, count in sorted(mutation_counts.items(),
                             key=lambda x: x[1], reverse=True)[:10]:
    print(f"{mutation}: {count} occurrences")
```

## Error Handling
```python
from rustkmer import Database, InvalidKmerError, QueryError

try:
    with Database("genome.rkdb") as db:
        result = db.fuzzy_query("ATCGATCG", mutations=1)
except InvalidKmerError as e:
    print(f"Invalid k-mer: {e}")
except QueryError as e:
    print(f"Query failed: {e}")
except FileNotFoundError:
    print("Database file not found")
```

## Performance Tips

### For Large Batch Queries
```python
# Adjust worker count based on your system
batch_result = db.fuzzy_query_batch(
    many_kmers,
    mutations=2,
    max_workers=8,  # Increase for more parallelism
    max_variants=1000  # Limit variants per query for performance
)
```

### For High Mutation Tolerance
```python
# Use max_variants to limit search space
result = db.fuzzy_query(
    "ATCGATCGATCGATCG",
    mutations=3,
    max_variants=5000  # Prevent explosion of variants
)
```

## Common Patterns

### Finding Close Variants
```python
# Get only exact matches and single mutations
result = db.fuzzy_query(kmer, mutations=1)
exact = result.exact_match
single_mutations = [m for m in result.matches if m.distance == 1]
```

### Comparing Mutation Tolerances
```python
for tolerance in [0, 1, 2]:
    result = db.fuzzy_query(kmer, mutations=tolerance)
    print(f"Tolerance {tolerance}: {result.total_matches} matches")
```

### Custom Output Processing
```python
import json

result = db.fuzzy_query(kmer, mutations=2)
data = json.loads(result.to_json())

# Custom filtering
high_count_matches = [
    m for m in data['matches']
    if m['count'] > 100
]
```

## Integration with Pandas
```python
import pandas as pd

# Convert results to DataFrame
matches_data = [
    {
        'kmer': match.kmer,
        'count': match.count,
        'distance': match.distance,
        'mutations': ', '.join(match.mutations)
    }
    for match in result.matches
]

df = pd.DataFrame(matches_data)
print(df.sort_values('count', ascending=False))