# Quick Start Guide: RustKmer Python Bindings

## Overview

This guide helps you quickly get started with the RustKmer Python API for high-performance k-mer counting, database queries, and genomic data analysis.

## Prerequisites

1. **Python Environment**:
   ```bash
   # Ensure Python 3.10+ is installed
   python --version  # Should be 3.10 or higher
   ```

2. **Install RustKmer**:
   ```bash
   # Install from PyPI
   pip install rustkmer

   # Or install development version
   pip install git+https://github.com/your-org/rustkmer.git
   ```

## Quick Examples

### 1. K-mer Counting

```python
from rustkmer import KmerCounter

# Create a k-mer counter
counter = KmerCounter(k=21, canonical=True, threads=4)

# Count k-mers in a FASTA file
database = counter.count_file("sequences.fasta", "output.rkdb")

# Count k-mers in a FASTQ string
counts = counter.count_string("ATCGATCGATCGATCGATCGATCGATCGATCG")
print(f"Counts: {counts}")
```

### 2. Database Queries

```python
from rustkmer import Database

# Load an existing database
db = Database("existing.rkdb")

# Query a single k-mer
count = db.query("ATCGATCGATCGATCGATCGATCG")
print(f"K-mer count: {count}")

# Check if k-mer exists
if db.exists("ATCGATCGATCGATCGATCGATCG"):
    print("K-mer found in database")

# Batch query multiple k-mers
kmers = ["ATCGATCG", "GCTAGCTA", "TATATATA"]
results = db.query_batch(kmers)
print(f"Batch results: {results}")
```

### 3. Fuzzy Query

```python
from rustkmer import Database, FuzzyQuery

# Load database and create fuzzy query
db = Database("existing.rkdb")
fuzzy = FuzzyQuery(db, max_mutations=1)

# Search with wildcard pattern
result = fuzzy.query("A*TG*C")
print(f"Found {len(result.matches)} matches")

# Search with mutation tolerance
result = fuzzy.query("AAAAA", max_distance=1)
for match in result.matches:
    print(f"{match.kmer}: {match.count} (distance: {match.distance})")
```

### 4. Database Statistics

```python
from rustkmer import Database

db = Database("existing.rkdb")
stats = db.get_statistics()

print(f"K-mer size: {stats.kmer_size}")
print(f"Total k-mers: {stats.total_kmers}")
print(f"Unique k-mers: {stats.unique_kmers}")
print(f"Coverage estimate: {stats.coverage_estimate}")

# Get histogram data
histogram = stats.calculate_histogram(max_bins=100)
print(f"Histogram: {histogram}")
```

### 5. Database Merging

```python
from rustkmer import Database

# Load multiple databases
db1 = Database("sample1.rkdb")
db2 = Database("sample2.rkdb")
db3 = Database("sample3.rkdb")

# Merge databases
merged_db = db1.merge([db2, db3], "merged.rkdb")
print(f"Merged database contains {merged_db.total_kmers} k-mers")
```

### 6. Data Export

```python
from rustkmer import Database

db = Database("existing.rkdb")

# Export to text format
db.dump("output.txt", format="text")

# Export to CSV with threshold
db.dump("filtered.csv", format="csv", threshold=10)

# Export to JSON
db.dump("data.json", format="json")
```

## Advanced Usage

### Progress Callbacks

```python
from rustkmer import KmerCounter

def progress_callback(progress: float, message: str):
    print(f"Progress: {progress:.1%} - {message}")

counter = KmerCounter(k=31)
database = counter.count_file(
    "large_file.fasta",
    "output.rkdb",
    progress_callback=progress_callback
)
```

### Configuration Management

```python
from rustkmer import KmerCounter
import os

# Configure via environment variables
os.environ['RUSTKMER_THREADS'] = '8'
os.environ['RUSTKMER_VERBOSE'] = 'true'

counter = KmerCounter(k=21)
# Will use 8 threads and verbose output
```

### Error Handling

```python
from rustkmer import KmerCounter, SequenceError, DatabaseError
import logging

logging.basicConfig(level=logging.INFO)

try:
    counter = KmerCounter(k=21)
    database = counter.count_file("invalid.fasta")
except SequenceError as e:
    logging.error(f"Invalid sequence: {e}")
except DatabaseError as e:
    logging.error(f"Database error: {e}")
```

## Performance Tips

### 1. Use Memory Mapping for Large Databases

```python
# Database automatically uses memory mapping
db = Database("large_database.rkdb")  # Efficient for >1GB files
```

### 2. Batch Operations

```python
# Use batch queries for better performance
kmers = ["ATCG" * 10 for _ in range(1000)]
results = db.query_batch(kmers)  # Much faster than individual queries
```

### 3. Thread-Safe Usage

```python
from threading import Thread
from rustkmer import Database

def query_worker(db_path, kmer):
    db = Database(db_path)
    return db.query(kmer)

# Database objects can be safely used across threads
threads = [
    Thread(target=query_worker, args=("db.rkdb", "ATCG")),
    Thread(target=query_worker, args=("db.rkdb", "GCTA")),
]
for t in threads:
    t.start()
for t in threads:
    t.join()
```

## Common Workflows

### 1. Complete Counting and Analysis Pipeline

```python
from rustkmer import KmerCounter, Database

# Step 1: Count k-mers
counter = KmerCounter(k=31, threads=8)
database = counter.count_file("reads.fastq", "sample.rkdb")

# Step 2: Analyze database
db = Database("sample.rkdb")
stats = db.get_statistics()

# Step 3: Export results
db.dump("analysis_report.txt", format="text")
stats.calculate_histogram().to_csv("histogram.csv")
```

### 2. Comparative Analysis

```python
from rustkmer import Database

# Load multiple samples
samples = {
    "control": Database("control.rkdb"),
    "treatment": Database("treatment.rkdb"),
    "replica1": Database("replica1.rkdb"),
}

# Compare k-mer counts
test_kmers = ["ATCGATCGATCGATCGATCGATCG", "GCTAGCTAGCTAGCTAGCTAGCT"]
results = {}
for name, db in samples.items():
    results[name] = db.query_batch(test_kmers)

# Find k-mers with significant differences
for kmer in test_kmers:
    control_count = results["control"].get(kmer, 0)
    treatment_count = results["treatment"].get(kmer, 0)
    if abs(treatment_count - control_count) > 100:
        print(f"Significant change in {kmer}: {control_count} → {treatment_count}")
```

## Troubleshooting

### Common Issues

1. **Import Error**: Ensure RustKmer is properly installed
   ```bash
   pip install --upgrade rustkmer
   ```

2. **Database Loading Error**: Check file format and permissions
   ```python
   import os
   if not os.path.exists("database.rkdb"):
       print("Database file not found")
   ```

3. **Memory Issues**: Use smaller k-mer sizes or batch processing
   ```python
   # For very large files
   counter = KmerCounter(k=21)  # Smaller k-mers use less memory
   ```

### Getting Help

- Check the RustKmer documentation: `help(rustkmer)`
- Review CLI command help: `rustkmer --help`
- Report issues on GitHub repository
- Join the RustKmer community discussions

## Next Steps

1. **Explore the API**: Use `dir()` to explore available methods
2. **Run Examples**: Try the examples with your own data
3. **Read Documentation**: Check the full API documentation
4. **Join Community**: Participate in discussions and contribute

## Reference

For detailed API documentation and advanced usage patterns, see the complete RustKmer Python documentation.