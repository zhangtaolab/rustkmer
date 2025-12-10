# RustKmer Python API Quick Start

## Installation

```bash
# Install from source (requires Rust)
git clone https://github.com/rust-lang/rustkmer.git
cd rustkmer
pip install .

# Install from PyPI (when available)
pip install rustkmer
```

## Basic Usage

### 1. Counting K-mers

```python
from rustkmer import KmerCounter

# Create a counter
counter = KmerCounter(k=21, canonical=True)

# Count from a FASTA file
counter.count_file("sequences.fasta")

# Get statistics
print(f"Total k-mers: {counter.get_total_count()}")
print(f"Unique k-mers: {counter.get_unique_count()}")

# Get count for specific k-mer
count = counter.get_kmer_count("ATCGATCGATCGATCGATCG")
print(f"Count: {count}")

# Get top k-mers
top_kmers = counter.get_top_kmers(n=10)
for kmer, count in top_kmers:
    print(f"{kmer}: {count}")
```

### 2. Database Operations

```python
from rustkmer import KmerCounter, Database

# Create and populate database
counter = KmerCounter(k=31)
counter.count_file("large_dataset.fastq")

# Save to database
database = counter.save_to_database("mydata.rkdb")

# Load existing database
db = Database()
db.load("mydata.rkdb")

# Query k-mers
result = db.query("ATCGATCGATCGATCGATCGATCGATCGATCG")
if result.found:
    print(f"Count: {result.count}")
else:
    print("K-mer not found")

# Batch queries
kmers = ["ATCGATCGATCGATCGATCG", "GCTAGCTAGCTAGCTAGCTA"]
results = db.query_batch(kmers)
for result in results:
    print(f"{result.kmer}: {result.count if result.found else 'not found'}")

# Check existence
if db.exists("ATCGATCGATCGATCGATCG"):
    print("K-mer exists in database")
```

### 3. Fuzzy Queries

```python
from rustkmer import FuzzyQuery

# Create fuzzy query
fq = FuzzyQuery()
fq.load_database("mydata.rkdb")
fq.set_max_distance(2)

# Query with wildcards
results = fq.query("ATCGATCGATNGATCGATCG")  # N is wildcard
for result in results:
    print(f"{result.kmer}: {result.count} (distance: {result.distance})")

# Batch fuzzy queries
patterns = ["ATCGATCGATNGATCGATCG", "GCTAGCTANNNNNNNNN"]
batch_results = fq.query_batch(patterns)
```

### 4. Database Statistics

```python
from rustkmer import Database

db = Database()
db.load("mydata.rkdb")

stats = db.get_stats()
print(f"K-mer size: {stats.kmer_size}")
print(f"Total k-mers: {stats.total_kmers}")
print(f"Unique k-mers: {stats.unique_kmers}")
print(f"Coverage: {stats.coverage:.2f}%")

# Histogram data
for count, frequency in stats.histogram[:10]:
    print(f"Count {count}: {frequency} k-mers")

# Percentiles
print(f"P50: {stats.percentiles['P50']}")
print(f"P95: {stats.percentiles['P95']}")
```

### 5. Database Merge

```python
from rustkmer import Database

# Load multiple databases
db1 = Database()
db1.load("sample1.rkdb")

db2 = Database()
db2.load("sample2.rkdb")

# Merge databases
merged = db1.merge(db2, "merged.rkdb")

# Verify merge
merged_stats = merged.get_stats()
print(f"Merged database has {merged_stats.total_kmers} k-mers")
```

### 6. Export Data

```python
from rustkmer import Database

db = Database()
db.load("mydata.rkdb")

# Export as text
db.dump("export.txt", format="text", threshold=5)

# Export as CSV
db.dump("export.csv", format="csv")

# Export as JSON
db.dump("export.json", format="json")
```

## Advanced Usage

### Thread Safety

```python
from rustkmer import Database
import threading

db = Database()
db.load("mydata.rkdb")

def worker(kmers):
    for kmer in kmers:
        result = db.query(kmer)
        # Process result...

# Multiple threads can safely access the same database
threads = []
for i in range(4):
    t = threading.Thread(target=worker, args=[kmers[i::4]])
    threads.append(t)
    t.start()

for t in threads:
    t.join()
```

### Error Handling

```python
from rustkmer import KmerCounter, RustKmerError, SequenceError

try:
    counter = KmerCounter(k=65)  # k too large for u128
except ValueError as e:
    print(f"Invalid parameter: {e}")

try:
    counter = KmerCounter()
    counter.count_string("AXCG")  # Invalid sequence
except SequenceError as e:
    print(f"Sequence error: {e}")

# Generic error handling
try:
    db = Database()
    db.load("nonexistent.rkdb")
except RustKmerError as e:
    print(f"RustKmer error: {e}")
```

### Performance Tips

1. **Use batch operations** when possible:
   ```python
   # Good - batch query
   results = db.query_batch(kmers)

   # Avoid - individual queries
   for kmer in kmers:
       result = db.query(kmer)
   ```

2. **Choose appropriate k-mer size**:
   - Small k (15-21): More unique k-mers, faster queries
   - Large k (31-63): More specific, less memory

3. **Use canonical k-mers** for counting if strand doesn't matter:
   ```python
   counter = KmerCounter(k=21, canonical=True)  # Merges reverse complements
   ```

4. **Enable compression** for large databases:
   ```python
   counter.save_to_database("large.rkdb", compress=True)
   ```

## Integration with BioPython

```python
from rustkmer import KmerCounter
from Bio import SeqIO

# Process BioPython sequences
counter = KmerCounter(k=21)

for record in SeqIO.parse("sequences.fasta", "fasta"):
    # Convert to string
    sequence = str(record.seq).upper()
    counter.count_string(sequence)

print(f"Processed {counter.get_total_count()} k-mers")
```

## Integration with Pandas

```python
from rustkmer import Database
import pandas as pd

db = Database()
db.load("mydata.rkdb")

# Get top k-mers and convert to DataFrame
top_kmers = counter.get_top_kmers(n=100)
df = pd.DataFrame(top_kmers, columns=['kmer', 'count'])

# Sort by count
df = df.sort_values('count', ascending=False)
print(df.head())
```

## Troubleshooting

### Common Issues

1. **Installation fails**:
   ```bash
   # Ensure Rust is installed
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   source ~/.cargo/env
   ```

2. **Database loading is slow**:
   - Large files may take time to memory map
   - Use SSD storage for better performance

3. **Out of memory errors**:
   - Reduce k-mer size
   - Use streaming instead of loading entire files

4. **Thread safety warnings**:
   - Database objects are thread-safe
   - KmerCounter objects should not be shared between threads

### Getting Help

- Check the [documentation](https://rustkmer.readthedocs.io/)
- Open an issue on [GitHub](https://github.com/rust-lang/rustkmer/issues)
- Review the [examples](https://github.com/rust-lang/rustkmer/tree/main/examples)