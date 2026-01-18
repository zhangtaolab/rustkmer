# Tutorial: Basic K-mer Analysis Workflow

This tutorial walks you through a complete k-mer analysis workflow using RustKmer Python API. You'll learn how to:

1. Count k-mers from sequence data
2. Create and query databases
3. Perform basic analysis
4. Export and visualize results

## Prerequisites

- Python 3.10 or higher
- RustKmer installed: `pip install rustkmer`
- Basic understanding of genomics concepts

## Step 1: Setup

Import the necessary libraries:

```python
from pyrustkmer import KmerCounter, Database
import matplotlib.pyplot as plt
import pandas as pd
```

## Step 2: Prepare Your Data

For this tutorial, we'll create a simple FASTA file:

```python
# Create a sample FASTA file
sequence_data = """>example_sequence_1
ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC
CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC
>example_sequence_2
GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT"""

with open("tutorial_sequences.fasta", "w") as f:
    f.write(sequence_data)

print("Created tutorial_sequences.fasta")
```

## Step 3: Count K-mers

Create a k-mer counter and count k-mers from your data:

```python
# Create counter with k=21 (common for genomics)
print("Creating k-mer counter (k=21)...")
counter = PyCounter(21, canonical=True)

# Count k-mers from the FASTA file
print("Counting k-mers...")
counter.add_from_fasta("tutorial_sequences.fasta")

# Get basic statistics
total_kmers = counter.get_stats().total_kmers)
unique_kmers = counter.get_unique_count()

print(f"\nK-mer Counting Results:")
print(f"  Total k-mers: {total_kmers:,}")
print(f"  Unique k-mers: {unique_kmers:,}")
print(f"  Reduction ratio: {unique_kmers/total_kmers:.3f}")
```

### Understanding the Results

- **Total k-mers**: All k-mers counted, including duplicates
- **Unique k-mers**: Distinct k-mer sequences
- **Reduction ratio**: Unique/Total, indicates sequence diversity

## Step 4: Create a Database

Save your k-mer counts to a database for fast querying:

```python
# Save to database
database_path = "tutorial_database.rkdb"
counter.save_database(database_path, canonical=True)

print(f"\nDatabase saved to: {database_path}")
print(f"File size: {os.path.getsize(database_path) / 1024:.2f} KB")
```

### Database Format Benefits

- **Fast queries**: Millisecond response time
- **Compact storage**: Efficient binary format
- **Random access**: Query any k-mer directly

## Step 5: Load and Query Database

Load the database and perform queries:

```python
# Load database
db = PyDatabase("database.rkdb", LoadMode.Preload)
db.load(database_path)

# Query specific k-mers
test_kmers = [
    "ATCGATCGATCGATCGATCGATCG",
    "GCTAGCTAGCTAGCTAGCTAGCT",
    "CCCCCCCCCCCCCCCCCCCCCCCC"
]

print("\nQuery Results:")
for kmer in test_kmers:
    count = db.query_exact(kmer)
    print(f"  {kmer[:20]}...: {count}")
```

### Interpreting Query Results

- **Count**: Number of times the k-mer appears in the original data
- **Zero count**: K-mer not found in the data
- **High count**: K-mer is abundant in the sequence

## Step 6: Batch Queries

For multiple k-mers, use batch queries for better performance:

```python
# Prepare many queries
query_list = [f"{'ATCG' * 5}{i:04d}" for i in range(100)]

# Batch query (much faster than individual queries)
print("\nPerforming batch query...")
start_time = time.time()
results = db.query_multiple(query_list)
query_time = time.time() - start_time

# Analyze results
non_zero = sum(1 for count in results if count > 0)
print(f"Queried {len(query_list)} k-mers in {query_time:.3f} seconds")
print(f"Found {non_zero} non-zero k-mers")

# Create a simple histogram
counts = [count for count in results if count > 0]
if counts:
    plt.figure(figsize=(10, 6))
    plt.hist(counts, bins=20, alpha=0.7, color='blue')
    plt.xlabel('K-mer Count')
    plt.ylabel('Frequency')
    plt.title('K-mer Abundance Distribution')
    plt.yscale('log')
    plt.grid(True, alpha=0.3)
    plt.show()
```

## Step 7: Database Statistics

Get comprehensive statistics about your database:

```python
# Get detailed statistics
stats = db.get_stats()

print("\nDatabase Statistics:")
print(f"  Database: {database_path}")
print(f"  Total k-mers: {stats['total_kmers']:,}")
print(f"  Unique k-mers: {stats['unique_kmers']:,}")
print(f"  K-mer size: {stats['k_size']}")
print(f"  Canonical mode: {stats['canonical_mode']}")

# Calculate additional metrics
if stats['total_kmers'] > 0 and stats['unique_kmers'] > 0:
    avg_abundance = stats['total_kmers'] / stats['unique_kmers']
    complexity = stats['unique_kmers'] / (4 ** stats['k_size'])

    print(f"\nDerived Metrics:")
    print(f"  Average abundance: {avg_abundance:.2f}")
    print(f"  Complexity ratio: {complexity:.6f}")
```

### Understanding the Metrics

- **Average abundance**: Mean count per unique k-mer
- **Complexity ratio**: Unique k-mers / possible k-mers (4^k)
- **Lower complexity** indicates repetitive sequences
- **Higher complexity** indicates diverse sequences

## Step 8: Compare Different K-mer Sizes

Compare results with different k-mer sizes:

```python
def analyze_with_different_k(file_path):
    """Analyze the same file with different k-mer sizes"""

    k_sizes = [7, 15, 21, 31]
    results = {}

    for k in k_sizes:
        if k == 7:  # k=7 is special (uses u64 encoding)
            print(f"\nAnalyzing with k={k} (u64 encoding)...")
            from rustkmer.u64_counter import KmerCounter as KmerCounter64
            counter = KmerCounter64(k=k, canonical=True)
        else:
            print(f"\nAnalyzing with k={k}...")
            counter = PyCounter(k, canonical=True)

        # Time the counting
        start_time = time.time()
        counter.add_from_fasta(file_path)
        count_time = time.time() - start_time

        # Get results
        total = counter.get_stats().total_kmers)
        unique = counter.get_unique_count()

        results[k] = {
            'total': total,
            'unique': unique,
            'time': count_time,
            'throughput': total / count_time if count_time > 0 else 0
        }

        print(f"  Total: {total:,}, Unique: {unique:,}, Time: {count_time:.3f}s")

    return results

# Run comparison
comparison_results = analyze_with_different_k("tutorial_sequences.fasta")

# Visualize the results
plt.figure(figsize=(15, 5))

# Subplot 1: Total k-mers
plt.subplot(1, 3, 1)
plt.plot(list(comparison_results.keys()),
         [r['total'] for r in comparison_results.values()],
         marker='o')
plt.xlabel('K-mer Size')
plt.ylabel('Total K-mers')
plt.title('Total K-mers vs K-mer Size')
plt.grid(True, alpha=0.3)

# Subplot 2: Unique k-mers
plt.subplot(1, 3, 2)
plt.plot(list(comparison_results.keys()),
         [r['unique'] for r in comparison_results.values()],
         marker='o', color='orange')
plt.xlabel('K-mer Size')
plt.ylabel('Unique K-mers')
plt.title('Unique K-mers vs K-mer Size')
plt.grid(True, alpha=0.3)

# Subplot 3: Throughput
plt.subplot(1, 3, 3)
plt.plot(list(comparison_results.keys()),
         [r['throughput'] for r in comparison_results.values()],
         marker='o', color='green')
plt.xlabel('K-mer Size')
plt.ylabel('Throughput (k-mers/sec)')
plt.title('Processing Throughput vs K-mer Size')
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
```

### Choosing K-mer Size

Guidelines for selecting k-mer size:

- **k=7-15**: High sensitivity, good for short reads
- **k=21-31**: Balance of sensitivity and specificity
- **k=31+**: High specificity, good for unique identification

## Step 9: Export Results

Export your results for further analysis:

```python
# Export k-mer counts to CSV
export_data = []

# Note: In a real application, you'd need a method to get all k-mers
# For now, we'll use our test queries
for kmer, count in zip(query_list, results):
    if count > 0:
        export_data.append({
            'kmer': kmer,
            'count': count,
            'abundance': count / sum(results)
        })

if export_data:
    df = pd.DataFrame(export_data)
    df = df.sort_values('count', ascending=False)

    # Save to CSV
    df.to_csv("kmer_counts.csv", index=False)
    print(f"\nExported {len(df)} k-mers to kmer_counts.csv")

    # Show top 10 most abundant k-mers
    print("\nTop 10 Most Abundant K-mers:")
    print(df.head(10).to_string(index=False))
```

## Step 10: Clean Up

Clean up temporary files:

```python
import os

# Remove temporary files
files_to_remove = [
    "tutorial_sequences.fasta",
    "tutorial_database.rkdb",
    "kmer_counts.csv"
]

for file in files_to_remove:
    if os.path.exists(file):
        os.remove(file)
        print(f"Removed: {file}")
```

## Complete Workflow Script

Here's the complete workflow in a single script:

```python
#!/usr/bin/env python3
"""Complete k-mer analysis workflow tutorial"""

import os
import time
import matplotlib.pyplot as plt
from pyrustkmer import KmerCounter, Database

def main():
    print("RustKmer Basic Workflow Tutorial")
    print("=" * 40)

    # Step 1: Create sample data
    print("\n1. Creating sample data...")
    # (Insert the sequence creation code from above)

    # Step 2: Count k-mers
    print("\n2. Counting k-mers...")
    counter = PyCounter(21, canonical=True)
    counter.add_from_fasta("tutorial_sequences.fasta")

    total = counter.get_stats().total_kmers)
    unique = counter.get_unique_count()
    print(f"   Total: {total:,}, Unique: {unique:,}")

    # Step 3: Create database
    print("\n3. Creating database...")
    db_path = "tutorial_db.rkdb"
    counter.save_database(db_path)
    print(f"   Database: {db_path}")

    # Step 4: Query database
    print("\n4. Querying database...")
    db = PyDatabase("database.rkdb", LoadMode.Preload)
    db.load(db_path)

    test_kmer = "ATCGATCGATCGATCGATCGATCG"
    count = db.query_exact(test_kmer)
    print(f"   '{test_kmer[:15]}...': {count}")

    # Step 5: Get statistics
    print("\n5. Database statistics...")
    stats = db.get_stats()
    print(f"   Total k-mers: {stats['total_kmers']:,}")
    print(f"   Unique k-mers: {stats['unique_kmers']:,}")

    # Step 6: Clean up
    print("\n6. Cleaning up...")
    for file in ["tutorial_sequences.fasta", "tutorial_db.rkdb"]:
        if os.path.exists(file):
            os.remove(file)
            print(f"   Removed: {file}")

    print("\nWorkflow completed successfully!")

if __name__ == "__main__":
    main()
```

## Next Steps

You've completed the basic k-mer analysis workflow! Next, you might want to:

1. Try the [Large Datasets](large-datasets.md) tutorial
2. Learn about [Performance Optimization](performance.md)
3. Explore [Integration with other tools](integration.md)
4. Check out [Advanced Features](../examples/advanced.md)

## Key Takeaways

- **Start with k=21** for most genomic applications
- **Use canonical mode** for DNA sequences to save memory
- **Batch queries** are much more efficient than individual queries
- **Choose k-mer size** based on your specific application needs
- **Save intermediate results** in databases for fast re-analysis