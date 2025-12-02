# Quick Start Guide: RustKmer Python Bindings

**Version**: 1.0.0
**Date**: 2025-12-01

## Installation

### Install from PyPI

```bash
pip install rustkmer
```

### Install from Source

```bash
git clone https://github.com/your-org/rustkmer.git
cd rustkmer
pip install .
```

### Requirements

- Python 3.9 or higher
- 64-bit system (Linux, macOS, or Windows)

## Getting Started in 5 Minutes

### Basic K-mer Counting

```python
import rustkmer

# Count k-mers in a simple sequence
sequence = "ATCGATCGATCG"
k = 3

# Method 1: Using the convenience function
counts = rustkmer.count_kmers(sequence, k)
print(counts)
# Output: {'ATC': 3, 'TCG': 3, 'CGA': 3, 'GAT': 3}

# Method 2: Using the KmerCounter class
counter = rustkmer.KmerCounter(kmer_length=k)
counts = counter.count_sequence(sequence)
print(counts)
```

### Working with Files

```python
import rustkmer

# Count k-mers in a FASTA file
counter = rustkmer.KmerCounter(kmer_length=31, thread_count=4)
counts = counter.count_file("genome.fasta")

print(f"Found {len(counts)} unique k-mers")
print(f"Top 5 most frequent: {counter.get_top_kmers(5)}")
```

### Database Operations

```python
import rustkmer

# Create a database from sequences
db = rustkmer.create_database(
    output_path="my_database.rkdb",
    k=31,
    input_files=["genome.fasta"],
    canonical=True,
    sorted=True
)

# Query the database
with rustkmer.Database("my_database.rkdb", preload=True) as db:
    result = db.query("ATCGATCGATCGATCGATCGATCGATCGATCG")
    print(f"K-mer count: {result.count}")

    # Batch queries
    kmers = ["ATCGATCGATCGATCGATCGATCGATCGATCG", "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT"]
    results = db.query_multiple(kmers)
    for r in results:
        print(f"{r.kmer}: {r.count}")
```

## Common Use Cases

### 1. Counting K-mers from Multiple Files

```python
import rustkmer
from pathlib import Path

# Initialize counter
counter = rustkmer.KmerCounter(kmer_length=21, canonical=True)

# Process multiple FASTA files
for file_path in Path("data/").glob("*.fasta"):
    print(f"Processing {file_path}...")
    file_counts = counter.count_file(str(file_path))
    print(f"  Found {len(file_counts)} unique k-mers")

# Get final statistics
stats = counter.get_stats()
print(f"Total unique k-mers: {stats.total_kmers}")
print(f"Total k-mer count: {stats.total_count}")
print(f"Processing time: {stats.processing_time:.2f}s")
```

### 2. Fuzzy Query with Wildcards

```python
import rustkmer

# Open database
with rustkmer.Database("genome_k31.rkdb") as db:
    # Create fuzzy query with wildcards
    fuzzy_query = rustkmer.FuzzyQuery(
        query_string="ATCGNCGATCG",  # N matches any nucleotide
        kmer_size=10
    )

    # Execute fuzzy query
    result = fuzzy_query.execute(db)
    print(f"Original query: {result.original_query}")
    print(f"Found {result.total_matches} matches")
    print(f"Match type: {result.match_type}")

    # Show matched k-mers and their counts
    for kmer, count in result.counts.items():
        print(f"  {kmer}: {count}")
```

### 3. Mutation-Tolerant Queries

```python
import rustkmer

# Search for k-mers with up to 1 mutation
with rustkmer.Database("genome_k31.rkdb") as db:
    fuzzy_query = rustkmer.FuzzyQuery(
        query_string="ATCGATCGATCGATCGATCGATCGATCGATCG",
        kmer_size=31,
        mutation_tolerance=1  # Allow 1 mutation
    )

    result = fuzzy_query.execute(db)
    print(f"Generated {result.variant_count} variants")
    print(f"Found {result.total_matches} matches")

    # Show mutations applied (if any)
    if result.mutations_applied:
        for original, mutations in result.mutations_applied.items():
            print(f"Mutations of {original}: {mutations}")
```

### 4. Sequence Analysis

```python
import rustkmer

# Create sequence object with validation
seq = rustkmer.Sequence("ATCGATCGATCG", description="Sample sequence")
print(f"Sequence length: {seq.length}")
print(f"Valid: {seq.validate()}")

# Get k-mers from sequence
kmers = seq.get_kmers(3)
print(f"3-mers: {kmers}")

# Get reverse complement
rc_seq = seq.reverse_complement()
print(f"Reverse complement: {rc_seq.sequence}")
```

### 5. Performance Monitoring

```python
import rustkmer
import time

# Monitor performance of large-scale counting
start_time = time.time()
counter = rustkmer.KmerCounter(kmer_length=31, thread_count=8)

counts = counter.count_file("large_genome.fasta", file_format="fasta")

elapsed = time.time() - start_time
stats = counter.get_stats()

print(f"Performance metrics:")
print(f"  Wall clock time: {elapsed:.2f}s")
print(f"  Processing time: {stats.processing_time:.2f}s")
print(f"  Memory usage: {stats.memory_usage / 1024 / 1024:.2f} MB")
print(f"  K-mers per second: {stats.total_count / stats.processing_time:.0f}")
```

## Error Handling

```python
import rustkmer

try:
    # This will raise ValueError for invalid k-mer size
    counter = rustkmer.KmerCounter(kmer_length=200)
except rustkmer.KmerError as e:
    print(f"K-mer error: {e}")

try:
    # This will raise FileNotFoundError
    counts = counter.count_file("nonexistent.fasta")
except FileNotFoundError as e:
    print(f"File not found: {e}")

try:
    # This will raise DatabaseError for invalid database
    db = rustkmer.Database("invalid_database.rkdb")
except rustkmer.DatabaseError as e:
    print(f"Database error: {e}")
```

## Performance Tips

### 1. Choose the Right K-mer Size

```python
# For small genomes or short reads
k = 21  # Fast, lower memory
counter = rustkmer.KmerCounter(kmer_length=21)

# For large genomes
k = 31  # More specific, higher memory
counter = rustkmer.KmerCounter(kmer_length=31)
```

### 2. Use Parallel Processing

```python
# Use multiple threads for better performance
import multiprocessing

thread_count = multiprocessing.cpu_count()
counter = rustkmer.KmerCounter(kmer_length=31, thread_count=thread_count)
```

### 3. Optimize Database Usage

```python
# Preload frequently accessed databases
with rustkmer.Database("important_db.rkdb", preload=True) as db:
    # Multiple fast queries
    for kmer in many_kmers:
        result = db.query(kmer)
        process_result(result)

# Use batch queries when possible
results = db.query_multiple(list_of_kmers)
```

### 4. Memory Management

```python
# Use context managers for automatic cleanup
with rustkmer.Database("large_db.rkdb") as db:
    # Database automatically closed
    results = db.query_multiple(kmers)

# Or manually close when done
db = rustkmer.Database("large_db.rkdb")
try:
    results = db.query_multiple(kmers)
finally:
    db.close()
```

## Integration with Bioinformatics Tools

### With Biopython

```python
from Bio import SeqIO
import rustkmer

# Parse sequences with Biopython, count with RustKmer
counter = rustkmer.KmerCounter(kmer_length=21)

for record in SeqIO.parse("sequences.fasta", "fasta"):
    counts = counter.count_sequence(str(record.seq))
    print(f"{record.id}: {len(counts)} unique k-mers")
```

### With Pandas

```python
import pandas as pd
import rustkmer

# Convert k-mer counts to DataFrame for analysis
counter = rustkmer.KmerCounter(kmer_length=21)
counts = counter.count_file("sequences.fasta")

df = pd.DataFrame(list(counts.items()), columns=['kmer', 'count'])
df = df.sort_values('count', ascending=False)

print(df.head(10))
```

### With NumPy

```python
import numpy as np
import rustkmer

# Get count distribution for statistical analysis
counter = rustkmer.KmerCounter(kmer_length=21)
counts = counter.count_file("sequences.fasta")

count_values = np.array(list(counts.values()))
print(f"Mean count: {np.mean(count_values)}")
print(f"Median count: {np.median(count_values)}")
print(f"Standard deviation: {np.std(count_values)}")
```

## Frequently Asked Questions

### Q: What k-mer size should I use?
A: Common choices:
- k=21: Good for short reads, fast processing
- k=31: Standard for genome assembly
- k=51+: Better for large genomes, more memory intensive

### Q: How do I handle very large files?
A: Use streaming processing:
```python
counter = rustkmer.KmerCounter(kmer_length=31)
counts = counter.count_file("very_large_file.fasta")
```

The library automatically handles large files efficiently.

### Q: Can I use RustKmer with compressed files?
A: Yes! The library automatically detects and handles gzip compression:
```python
counts = counter.count_file("genome.fasta.gz")  # Works with .gz files
```

### Q: How do I compare two k-mer count sets?
A: Use dictionary operations:
```python
counts1 = counter1.get_all_counts()
counts2 = counter2.get_all_counts()

# Find unique k-mers in each
unique_to_1 = set(counts1.keys()) - set(counts2.keys())
unique_to_2 = set(counts2.keys()) - set(counts1.keys())
```

### Q: What's the performance compared to other tools?
A: RustKmer is typically 2-5x faster than Python-only implementations and competitive with other C/C++ tools while maintaining memory efficiency.

## Next Steps

- Explore the [API documentation](./contracts/python-api.md) for detailed method descriptions
- Check the [data model](./data-model.md) for entity relationships
- Look at the [research findings](./research.md) for technical details
- Visit the GitHub repository for more examples and contributions

## Getting Help

- **Documentation**: [Full API Reference](./contracts/python-api.md)
- **Issues**: [GitHub Issues](https://github.com/your-org/rustkmer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/rustkmer/discussions)
- **Examples**: [examples/](https://github.com/your-org/rustkmer/tree/main/examples) directory