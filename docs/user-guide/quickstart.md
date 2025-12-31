# Quick Start Guide

Get started with RustKmer Python API in just 5 minutes!

## Installation

First, install RustKmer:

```bash
pip install rustkmer
```

## Basic K-mer Counting

```python
from rustkmer import KmerCounter

# Create a counter for k=31 (common for genomics)
counter = KmerCounter(k=31, canonical=True)

# Count k-mers from a string sequence
sequence = "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC"
counter.count_string(sequence)

# Get results
print(f"Total k-mers: {counter.get_total_count()}")
print(f"Unique k-mers: {counter.get_unique_count()}")

# Save to database
counter.save_to_database("my_data.rkdb")
```

## Processing FASTA/FASTQ Files

```python
from rustkmer import KmerCounter

# Count k-mers from a file
counter = KmerCounter(k=21, canonical=True)
counter.count_file("genome.fa.gz")  # Supports compressed files!

print(f"Processed {counter.get_total_count():,} k-mers")
```

## Database Queries

```python
from rustkmer import Database

# Load a database
db = Database()
db.load("my_data.rkdb")

# Query specific k-mers
count = db.query("ATCGATCGATCGATCGATCGATC")
print(f"K-mer appears {count} times")

# Batch queries
sequences = ["ATCGATCG", "GCTAGCTA", "CCCCCCCC"]
results = db.query_multiple(sequences)
for seq, count in zip(sequences, results):
    print(f"{seq}: {count}")
```

## Fuzzy Search

```python
from rustkmer import FuzzyQuery

# Create fuzzy query interface
fq = FuzzyQuery()
fq.load("my_data.rkdb")

# Search with wildcards (N = any base)
results = fq.query("AATN")  # Matches AATA, AATC, AATG, AATT

# Search with mismatches
results = fq.query("ATCGATCG", max_mismatches=2)

# Display results
for match, count in results:
    print(f"Found: {match}, Count: {count}")
```

## Database Statistics

```python
from rustkmer import Database

db = Database()
db.load("my_data.rkdb")

# Get comprehensive statistics
stats = db.get_stats()
print(f"Database statistics:")
print(f"  Total k-mers: {stats['total_kmers']:,}")
print(f"  Unique k-mers: {stats['unique_kmers']:,}")
print(f"  K-mer size: {stats['k_size']}")
print(f"  Canonical mode: {stats['canonical_mode']}")
```

## Database Merging

```python
from rustkmer import Database

# Load first database
db = Database()
db.load("sample1.rkdb")

# Merge with second database
db.merge_with("sample2.rkdb")

# Save merged result
db.save("merged_samples.rkdb")
```

## Complete Example

```python
from rustkmer import KmerCounter, Database, FuzzyQuery
import os

# 1. Count k-mers from multiple files
files = ["sample1.fa.gz", "sample2.fa.gz"]
counter = KmerCounter(k=31, canonical=True)

for file in files:
    if os.path.exists(file):
        print(f"Processing {file}...")
        counter.count_file(file)
    else:
        print(f"File not found: {file}")

# 2. Save results
counter.save_to_database("combined.rkdb")
print(f"Total k-mers counted: {counter.get_total_count():,}")

# 3. Load and analyze
db = Database()
db.load("combined.rkdb")
stats = db.get_stats()
print("\nDatabase Statistics:")
for key, value in stats.items():
    print(f"  {key}: {value}")

# 4. Perform some queries
test_kmers = ["ATCGATCGATCGATCGATCGATC", "GCTAGCTAGCTAGCTAGCTAGCT"]
print("\nQuery Results:")
for kmer in test_kmers:
    count = db.query(kmer)
    print(f"  {kmer[:10]}...: {count}")

# 5. Fuzzy search example
fq = FuzzyQuery()
fq.load("combined.rkdb")
fuzzy_results = fq.query("ATGNNNGT", max_mismatches=2)
print(f"\nFuzzy search found {len(fuzzy_results)} matches")
```

## Next Steps

- Read the [User Guide](concepts.md) for deeper understanding
- Check out [Examples](examples.md) for real-world use cases
- Follow [Tutorials](tutorials/) for step-by-step workflows
- Reference the [API Documentation](../api-reference/) for detailed information

## Tips

1. **Use canonical mode** (`canonical=True`) for DNA sequences to save memory
2. **Choose k=21-31** for most genomic applications
3. **Compressed files** (.gz) work automatically
4. **Batch queries** are more efficient than individual queries
5. **Memory-mapped access** (`memory_mapped=True`) helps with large databases

## Need Help?

- Check the [FAQ](../faq.md)
- Browse [Examples](../examples/)
- Report issues on [GitHub](https://github.com/rustkmer/rustkmer/issues)