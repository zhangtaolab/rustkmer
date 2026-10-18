# Quick Start Guide

Get started with RustKmer Python API in just 5 minutes!

## Installation

First, install RustKmer:

```bash
pip install pyrustkmer
```

## Basic K-mer Counting

```python
from pyrustkmer import PyCounter

# Create a counter for k=31 (common for genomics)
counter = PyCounter(31, canonical=True)

# Count k-mers from a string sequence
sequence = "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC"
counter.add_sequence(sequence)

# Get results
stats = counter.get_stats()
print(f"Total k-mers: {stats.total_kmers}")
print(f"Unique k-mers: {stats.unique_kmers}")


# Save to database
counter.save_database("my_data.rkdb")
```

## Processing FASTA/FASTQ Files

```python
from pyrustkmer import PyCounter

# Count k-mers from a file
counter = PyCounter(21, canonical=True)
counter.add_from_fasta("genome.fa.gz")  # Supports compressed files!

print(f"Processed {counter.get_stats().total_kmers:,} k-mers")
```

## Database Queries

```python
from pyrustkmer import PyDatabase, LoadMode

# Load a database
db = PyDatabase("my_data.rkdb", LoadMode.Preload)

# Query specific k-mers (length must match the database's k-mer size)
result = db.query_exact("ATCGATCGATCGATCGATCGATCGATCGATC")
print(f"K-mer appears {result.count} times")

# Batch queries (returns a dict mapping each k-mer to its result)
sequences = ["ATCGATCGATCGATCGATCGATCGATCGATC", "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGC"]
results = db.query_exact_batch(sequences)
for seq, res in results.items():
    print(f"{seq}: {res.count}")
```

## Fuzzy Search

```python
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

# Load database
db = PyDatabase("my_data.rkdb", LoadMode.Preload)

# Create fuzzy query interface
fuzzy = PyFuzzyQuery(db)

# Search with wildcards (N = any base); pattern length must match the k-mer size
results = fuzzy.query_fuzzy("AATCGATCGATCGATCGATCGATCGATCGAN", max_mutations=0)

# Search with mismatches
results = fuzzy.query_fuzzy("ATCGATCGATCGATCGATCGATCGATCGATC", max_mutations=2)

# Display results
for match in results.matches:
    print(f"Found: {match.kmer}, Count: {match.count}")
```

## Database Statistics

```python
from pyrustkmer import PyDatabase, LoadMode

db = PyDatabase("my_data.rkdb", LoadMode.Preload)

# Get comprehensive statistics (get_stats() returns a PyDatabaseStats object)
stats = db.get_stats()
print(f"Database statistics:")
print(f"  Total k-mers: {stats.total_kmers:,}")
print(f"  Unique k-mers: {stats.unique_kmers:,}")
print(f"  K-mer size: {stats.kmer_size}")
print(f"  Canonical mode: {stats.canonical}")
```

## Database Merging

```python
from pyrustkmer import PyDatabase

# Merge multiple databases into a single output file (static method)
PyDatabase.merge(
    ["sample1.rkdb", "sample2.rkdb"],
    "merged_samples.rkdb",
)
```

## Complete Example

```python
from pyrustkmer import PyCounter, PyDatabase, PyFuzzyQuery, LoadMode
import os

# 1. Count k-mers from multiple files
files = ["sample1.fa.gz", "sample2.fa.gz"]
counter = PyCounter(31, canonical=True)

for file in files:
    if os.path.exists(file):
        print(f"Processing {file}...")
        counter.add_from_fasta(file)
    else:
        print(f"File not found: {file}")

# 2. Save results
counter.save_database("combined.rkdb")
print(f"Total k-mers counted: {counter.get_stats().total_kmers:,}")

# 3. Load and analyze
db = PyDatabase("combined.rkdb", LoadMode.Preload)
stats = db.get_stats()
print("\nDatabase Statistics:")
print(f"  Total k-mers: {stats.total_kmers:,}")
print(f"  Unique k-mers: {stats.unique_kmers:,}")

# 4. Perform some queries (k-mers must be 31 characters for k=31)
test_kmers = ["ATCGATCGATCGATCGATCGATCGATCGATC", "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGC"]
print("\nQuery Results:")
for kmer in test_kmers:
    result = db.query_exact(kmer)
    print(f"  {kmer[:10]}...: {result.count}")

# 5. Fuzzy search example
fq = PyFuzzyQuery(db)
fuzzy_results = fq.query_fuzzy("ATGNNNGTATCGATCGATCGATCGATCGAT", max_mutations=2)
print(f"\nFuzzy search found {fuzzy_results.total_matches} matches")
```

## Next Steps

- Read the [User Guide](concepts.md) for deeper understanding
- Check out [Examples](examples.md) for real-world use cases
- Follow [Tutorials](../tutorials/) for step-by-step workflows
- Reference the [API Documentation](../api-reference/) for detailed information

## Tips

1. **Use canonical mode** (`canonical=True`) for DNA sequences to save memory
2. **Choose k=21-31** for most genomic applications
3. **Compressed files** (.gz) work automatically
4. **Batch queries** are more efficient than individual queries
5. **Memory-mapped access** (`LoadMode.MemoryMapped`) helps with large databases

## Need Help?

- Check the [Troubleshooting guide](../getting-started/troubleshooting.md)
- Browse [Examples](../examples/)
- Report issues on [GitHub](https://github.com/rustkmer/rustkmer/issues)