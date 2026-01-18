# Getting Started

This guide will help you get started with the RustKmer Python API, from installation to your first k-mer analysis.

## Installation

### Requirements

- Python 3.8 or higher
- Rust compiler (for building from source)

### Install from PyPI

The easiest way to install RustKmer is from PyPI:

```bash
pip install rustkmer
```

### Install from Source

For development or the latest features:

```bash
git clone https://github.com/your-org/rustkmer.git
cd rustkmer
pip install .
```

### Verify Installation

```python
import rustkmer
print(f"RustKmer version: {rustkmer.__version__}")
```

## Your First K-mer Analysis

Let's create a simple k-mer database and perform queries:

### 1. Create Sample Data

Create a file named `sample.fasta`:

```fasta
>seq1
ATCGATCGATCGATCGATCGATCGATCGATCGATCG
>seq2
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
>seq3
TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT
```

### 2. Create a K-mer Database

```python
from pyrustkmer import KmerCounter, PyFuzzyQuery

# Create a k-mer counter with k=31
counter = PyCounter(31, canonical=True)

# Count k-mers from FASTA file
print("Counting k-mers...")
counter.add_from_fasta("sample.fasta")

# Save to database
print("Creating database...")
counter.save_database("sample.rkdb")

print("Database created successfully!")
```

### 3. Query the Database

#### Important Note on Fuzzy Queries with N's

When using fuzzy queries with k-mers containing 'N' characters, be aware of the different default behavior between CLI and Python API:

- **CLI**: Default `mutations=0` (exact match only)
- **Python API**: Default `mutations=1` (allows 1 mutation by default)

This means that the same query will return different results depending on which interface you use. See [Fuzzy Query with N's: Behavior and Best Practices](../../../fuzzy_query_n_behavior.md) for detailed information.

For example, when querying "GCCGCGNNNNNNNGCCACC":

```python
# Python API default behavior (mutations=1)
result = fuzzy.query_fuzzy("GCCGCGNNNNNNNGCCACC")
# May return matches where left/right sequences differ

# To maintain fixed sequences, use mutations=0
result = fuzzy.query_fuzzy("GCCGCGNNNNNNNGCCACC", mutations=0)
# Only returns matches where N's are replaced, fixed sequences maintained
```

```python
from pyrustkmer import Database, PyFuzzyQuery

# Open database (context manager recommended)
db = PyDatabase("sample.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
    # Query a k-mer
    kmer = "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
    result = db.query_exact(kmer)

    print(f"Query k-mer: {kmer}")
    print(f"Found: {result.found}")
    print(f"Count: {result.count}")
    print(f"Canonical: {result.canonical}")

    # Get database statistics
    stats = db.get_stats()
    print(f"\nDatabase Statistics:")
    print(f"  K-mer size: {stats.kmer_size}")
    print(f"  Unique k-mers: {stats.unique_kmers:,}")
    print(f"  Total counts: {stats.total_counts:,}")
    print(f"  File size: {stats.file_size:,} bytes")
```

## Core Concepts

### K-mer Size

The k-mer size affects specificity and database size:

- **Small k (15-21)**: More matches, less specific, good for short reads
- **Medium k (25-31)**: Good balance for most applications
- **Large k (51+)**: Highly specific, less memory efficient

```python
# Different k-mer sizes for different use cases
counter_small = PyCounter(15)  # For metagenomics
counter_medium = PyCounter(31)  # General purpose
counter_large = PyCounter(51)  # For long sequences
```

### Canonical K-mers

Canonical k-mers store each k-mer and its reverse complement only once, reducing database size by ~50%:

```python
# With canonical k-mers (recommended)
counter_canonical = PyCounter(31, canonical=True)

# Without canonical k-mers (stores both strands)
counter_stranded = PyCounter(31, canonical=False)
```

### Context Managers

Always use context managers for database operations:

```python
# Good: Context manager automatically handles cleanup
db = PyDatabase("my_database.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
    result = db.query_exact("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")

# Manual handling (not recommended)
db = PyDatabase("my_database.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
db.open()
try:
    result = db.query_exact("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
finally:
```

## Common Operations

### Batch Processing

For multiple FASTA files:

```python
from pyrustkmer import KmerCounter, PyFuzzyQuery

# Create counter
counter = PyCounter(31, canonical=True)

# Process multiple files
file_list = ["file1.fasta", "file2.fasta", "file3.fasta"]
counter.count_file_list(file_list)

# Save combined database
counter.save_database("combined.rkdb")
```

### Multiple Queries

Query multiple k-mers efficiently:

```python
kmer_list = [
    "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
    "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
    "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"
]

db = PyDatabase("sample.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
    for kmer in kmer_list:
        result = db.query_exact(kmer)
        status = "✓" if result.found else "✗"
        print(f"{kmer[:10]:10}... {status} Count: {result.count}")
```

### Database Export

Export database content to other formats:

```python
import csv

db = PyDatabase("sample.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
    # Export to CSV
    with open("kmer_counts.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["kmer", "count", "canonical"])

        for result in db.dump(limit=1000):
            writer.writerow([result.kmer, result.count, result.canonical])

    print("Exported to kmer_counts.csv")
```

## Fuzzy Queries

Find similar k-mers with mutations:

```python
db = PyDatabase("sample.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
    # Exact query
    exact_kmer = "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
    exact_result = db.query_exact(exact_kmer)
    print(f"Exact matches: {exact_result.count}")

    # Fuzzy query (allow 1 mutation)
    fuzzy_result = fuzzy.query_fuzzy(exact_kmer, mutations=1)
    print(f"Fuzzy matches: {fuzzy_result.total_matches}")

    # Show fuzzy matches
    for match in fuzzy_result.get_fuzzy_matches():
        print(f"  {match.kmer}: {match.count} (distance={match.distance})")
```

## Error Handling

Handle common errors properly:

```python
from pyrustkmer import DatabaseNotFoundError, InvalidKmerError, QueryError, PyFuzzyQuery

try:
    db = PyDatabase("nonexistent.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
        result = db.query_exact("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")

except DatabaseNotFoundError:
    print("Database file not found!")

except InvalidKmerError as e:
    print(f"Invalid k-mer: {e.kmer} - {e.reason}")

except QueryError as e:
    print(f"Query error: {e}")

except Exception as e:
    print(f"Unexpected error: {e}")
```

## Performance Tips

### 1. Use Appropriate K-mer Size

```python
# For short reads (<100 bp)
k = 21

# For long reads (>1000 bp)
k = 31

# For very long sequences (>10 kb)
k = 51
```

### 2. Enable Canonical Mode

```python
# Reduces database size by ~50%
counter = PyCounter(31, canonical=True)
```

### 3. Use Batch Operations

```python
# Better than individual queries
batch_result = db.fuzzy_query_batch(kmer_list, mutations=2)
```

### 4. Process Large Datasets Efficiently

```python
# For large database dumps, use generators
db = PyDatabase("large_database.rkdb", LoadMode.Preload)
    count = 0
    for result in db.dump():  # Process all k-mers
        count += 1
        if count % 100000 == 0:
            print(f"Processed {count:,} k-mers...")
```

## Integration with Other Libraries

### Pandas Integration

```python
import pandas as pd

# Load database into pandas DataFrame
db = PyDatabase("sample.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
    data = []
    for result in db.dump(limit=10000):
        data.append({
            'kmer': result.kmer,
            'count': result.count,
            'canonical': result.canonical
        })

    df = pd.DataFrame(data)

# Analyze with pandas
print(f"Database summary:")
print(f"  Total k-mers: {len(df)}")
print(f"  Mean count: {df['count'].mean():.1f}")
print(f"  Max count: {df['count'].max()}")
print(f"  Unique canonical: {df['canonical'].nunique()}")
```

### NumPy Integration

```python
import numpy as np

# Extract counts for statistical analysis
db = PyDatabase("sample.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
    counts = [result.count for result in db.dump(limit=10000)]

# NumPy statistics
counts_array = np.array(counts)
print(f"Count statistics:")
print(f"  Mean: {np.mean(counts_array):.1f}")
print(f"  Median: {np.median(counts_array):.1f}")
print(f"  Std dev: {np.std(counts_array):.1f}")
print(f"  95th percentile: {np.percentile(counts_array, 95):.1f}")
```

## Next Steps

Now that you have the basics, explore these resources:

- [Database Operations](database.md) - Advanced database management
- [Fuzzy Queries](fuzzyquery.md) - Advanced fuzzy searching techniques
- [Examples](examples.md) - Comprehensive use case examples
- [Tutorials](../../tutorials/) - Step-by-step tutorials for specific workflows

## Complete Example

Here's a complete example that ties everything together:

```python
#!/usr/bin/env python3
"""
Complete RustKmer example: Create, analyze, and query a k-mer database.
"""

from pyrustkmer import KmerCounter, Database, PyFuzzyQuery
import pandas as pd
import matplotlib.pyplot as plt
import tempfile
import os

def main():
    # Create sample data
    sequences = [
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",
        "ATCGATCGATCGATCGATCGATCGATCGATCGATGG",  # 1 mutation
        "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
        "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"
    ]

    # Create temporary FASTA file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as f:
        for i, seq in enumerate(sequences):
            f.write(f">seq_{i+1}\n{seq}\n")
        fasta_file = f.name

    try:
        # 1. Create k-mer database
        print("Creating k-mer database...")
        counter = PyCounter(31, canonical=True)
        counter.add_from_fasta(fasta_file)
        db_path = "example.rkdb"
        counter.save_database(db_path)

        # 2. Analyze database
        print("Analyzing database...")
        db = PyDatabase(db_path, LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)
            stats = db.get_stats()
            print(f"  Unique k-mers: {stats.unique_kmers:,}")
            print(f"  Total counts: {stats.total_counts:,}")

            # 3. Query database
            print("\nQuerying database...")
            query_kmer = sequences[0][:31]  # First k-mer from first sequence
            result = db.query_exact(query_kmer)
            print(f"  Query: {query_kmer}")
            print(f"  Found: {result.found} (count: {result.count})")

            # 4. Fuzzy query
            print("\nFuzzy query...")
            fuzzy_result = fuzzy.query_fuzzy(query_kmer, mutations=2)
            print(f"  Total matches: {fuzzy_result.total_matches}")

            # 5. Export and visualize
            print("\nExporting data...")
            data = []
            for result in db.dump(limit=1000):
                data.append({'kmer': result.kmer, 'count': result.count})

            df = pd.DataFrame(data)

            # Create simple visualization
            plt.figure(figsize=(10, 6))
            plt.hist(df['count'], bins=50, alpha=0.7)
            plt.xlabel('K-mer Count')
            plt.ylabel('Frequency')
            plt.title('K-mer Count Distribution')
            plt.savefig('kmer_distribution.png', dpi=150, bbox_inches='tight')
            print("  Visualization saved to: kmer_distribution.png")

        print("\nExample completed successfully!")

    finally:
        # Clean up
        os.unlink(fasta_file)
        if os.path.exists(db_path):
            os.unlink(db_path)

if __name__ == "__main__":
    main()
```

This example demonstrates creating a database, querying it, performing fuzzy searches, and visualizing the results.

## Troubleshooting

### Common Issues

1. **Import Error**: Make sure rustkmer is properly installed
2. **Database Not Found**: Check file paths and permissions
3. **Memory Issues**: Use smaller k-mer sizes or process in chunks
4. **Slow Performance**: Use batch queries and appropriate k-mer sizes

### Getting Help

- Check the [examples](../../examples/) for complete working code
- Review the [API reference](index.md) for detailed documentation
- Look at the [tutorials](../../tutorials/) for specific workflows
- Report issues on the project GitHub repository