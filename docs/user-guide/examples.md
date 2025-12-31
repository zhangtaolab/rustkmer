# Code Examples

This page provides practical examples for common RustKmer use cases.

## Table of Contents

- [Basic Operations](#basic-operations)
- [File Processing](#file-processing)
- [Database Operations](#database-operations)
- [Batch Processing](#batch-processing)
- [Advanced Queries](#advanced-queries)
- [Performance Optimization](#performance-optimization)
- [Integration Examples](#integration-examples)

## Basic Operations

### Count K-mers from a String

```python
from rustkmer import KmerCounter

# Create counter
counter = KmerCounter(k=21, canonical=True)

# Count k-mers
sequence = "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC"
counter.count_string(sequence)

# Get results
total = counter.get_total_count()
unique = counter.get_unique_count()
print(f"Total: {total}, Unique: {unique}")
```

### Query a Single K-mer

```python
from rustkmer import Database

# Load database
db = Database()
db.load("example.rkdb")

# Query
kmer = "ATCGATCGATCGATCGATCGATC"
count = db.query(kmer)
print(f"'{kmer}' appears {count} times")
```

## File Processing

### Process FASTA Files

```python
from rustkmer import KmerCounter
import os

# Process all FASTA files in directory
counter = KmerCounter(k=31, canonical=True)

fa_files = [f for f in os.listdir("data/") if f.endswith((".fa", ".fasta"))]
for file in fa_files:
    filepath = os.path.join("data/", file)
    print(f"Processing {file}...")
    counter.count_file(filepath)

print(f"\nTotal k-mers from all files: {counter.get_total_count():,}")

# Save combined results
counter.save_to_database("combined_counts.rkdb")
```

### Process FASTQ Files with Quality Filtering

```python
from rustkmer import KmerCounter

# Create counter
counter = KmerCounter(k=21)

# Process FASTQ (quality scores ignored in counting)
counter.count_file("reads.fastq")

# For quality-based processing, filter first:
from Bio import SeqIO

quality_threshold = 30
counter = KmerCounter(k=21)

for record in SeqIO.parse("reads.fastq", "fastq"):
    if record.letter_annotations["phred_quality"].count(lambda q: q < quality_threshold) == 0:
        # High quality read
        counter.count_string(str(record.seq))
```

### Handle Compressed Files

```python
from rustkmer import KmerCounter

# RustKmer automatically handles gzip compression
counter = KmerCounter(k=31)

# All these work transparently
files = [
    "genome.fa",
    "genome.fa.gz",
    "reads.fq",
    "reads.fq.gz"
]

for file in files:
    try:
        counter.count_file(file)
        print(f"Processed {file}")
    except Exception as e:
        print(f"Error processing {file}: {e}")
```

## Database Operations

### Create and Query Database

```python
from rustkmer import KmerCounter, Database

# Step 1: Count k-mers
counter = KmerCounter(k=31, canonical=True)
counter.count_file("sample.fa.gz")

# Step 2: Save to database
database_path = "sample_k31.rkdb"
counter.save_to_database(database_path, canonical=True)

# Step 3: Load and query
db = Database()
db.load(database_path)

# Query specific k-mers
test_kmers = [
    "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC",
    "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC"
]

for kmer in test_kmers:
    count = db.query(kmer)
    print(f"{kmer[:10]}...: {count}")
```

### Database Statistics

```python
from rustkmer import Database
import json

db = Database()
db.load("large_database.rkdb")

# Get comprehensive statistics
stats = db.get_stats()

# Pretty print statistics
print("Database Statistics:")
print(f"  Total k-mers: {stats['total_kmers']:,}")
print(f"  Unique k-mers: {stats['unique_kmers']:,}")
print(f"  K-mer size: {stats['k_size']}")
print(f"  Canonical mode: {stats['canonical_mode']}")
print(f"  File size: {stats.get('file_size', 'Unknown')} bytes")

# Calculate additional metrics
if stats['total_kmers'] > 0:
    avg_abundance = stats['total_kmers'] / stats['unique_kmers']
    print(f"  Average abundance: {avg_abundance:.2f}")
```

### Merge Multiple Databases

```python
from rustkmer import Database

# Create merged database from multiple sources
databases_to_merge = [
    "sample1.rkdb",
    "sample2.rkdb",
    "sample3.rkdb"
]

# Load first database
merged_db = Database()
merged_db.load(databases_to_merge[0])

# Merge remaining databases
for db_path in databases_to_merge[1:]:
    print(f"Merging {db_path}...")
    merged_db.merge_with(db_path)

# Save merged result
merged_db.save("merged_all_samples.rkdb")

# Show final statistics
stats = merged_db.get_stats()
print(f"\nMerged database:")
print(f"  Total k-mers: {stats['total_kmers']:,}")
print(f"  Unique k-mers: {stats['unique_kmers']:,}")
```

## Batch Processing

### Batch Query from List

```python
from rustkmer import Database
import time

# Load database
db = Database()
db.load("database.rkdb")

# Prepare query list
query_kmers = [
    "ATCGATCGATCGATCGATCGATC",
    "GCTAGCTAGCTAGCTAGCTAGCT",
    "CCCCCCCCCCCCCCCCCCCCCCCC",
    # ... thousands more k-mers
]

# Batch query (more efficient)
start_time = time.time()
results = db.query_multiple(query_kmers)
query_time = time.time() - start_time

# Process results
for kmer, count in zip(query_kmers, results):
    if count > 0:
        print(f"{kmer}: {count}")

print(f"\nQueried {len(query_kmers)} k-mers in {query_time:.2f} seconds")
```

### Batch Counting Multiple Files

```python
from rustkmer import KmerCounter
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

def count_file_kmers(filepath, k=31):
    """Count k-mers in a single file"""
    counter = KmerCounter(k=k, canonical=True)
    counter.count_file(filepath)
    return {
        'file': os.path.basename(filepath),
        'total': counter.get_total_count(),
        'unique': counter.get_unique_count()
    }

# Process files in parallel
files = [os.path.join("data/", f) for f in os.listdir("data/")
         if f.endswith((".fa", ".fa.gz", ".fq", ".fq.gz"))]

results = []
with ThreadPoolExecutor(max_workers=4) as executor:
    future_to_file = {executor.submit(count_file_kmers, f): f for f in files}

    for future in as_completed(future_to_file):
        try:
            result = future.result()
            results.append(result)
            print(f"Processed {result['file']}: {result['total']:,} k-mers")
        except Exception as e:
            file = future_to_file[future]
            print(f"Error processing {file}: {e}")

# Summary
total_kmers = sum(r['total'] for r in results)
print(f"\nTotal k-mers across all files: {total_kmers:,}")
```

## Advanced Queries

### Fuzzy Search with Wildcards

```python
from rustkmer import FuzzyQuery

# Load database for fuzzy search
fq = FuzzyQuery()
fq.load("genome.rkdb")

# Search with wildcards
print("Wildcard searches:")
wildcard_patterns = ["AATN", "NCGA", "ATGNNNTA"]
for pattern in wildcard_patterns:
    results = fq.query(pattern)
    print(f"Pattern '{pattern}': {len(results)} matches")
    for match, count in results[:5]:  # Show first 5
        print(f"  {match}: {count}")
```

### Fuzzy Search with Mismatches

```python
from rustkmer import FuzzyQuery

fq = FuzzyQuery()
fq.load("genome.rkdb")

# Find similar sequences
query = "ATCGATCGATCGATCGATCGATC"
max_mismatches = 2

results = fq.query(query, max_mismatches=max_mismatches)
print(f"Sequences similar to '{query[:10]}...' with ≤{max_mismatches} mismatches:")

# Group by number of mismatches
by_mismatches = {}
for match, count in results:
    mismatches = sum(1 for a, b in zip(query, match) if a != b)
    by_mismatches.setdefault(mismatches, []).append((match, count))

for mismatches, matches in sorted(by_mismatches.items()):
    print(f"\n{mismatches} mismatches ({len(matches)} matches):")
    for match, count in matches[:3]:  # Show first 3
        print(f"  {match}: {count}")
```

### Complex Query Patterns

```python
from rustkmer import Database, FuzzyQuery
import re

# Load databases
db = Database()
db.load("annotations.rkdb")
fq = FuzzyQuery()
fq.load("genome.rkdb")

# Define query patterns
patterns = {
    'promoter': ['TATAAA', 'CAAT', 'GGCGCC'],
    'terminator': ['TTTTTT', 'AAAAAAAA'],
    'restriction': ['GAATTC', 'GGATCC', 'AAGCTT']
}

# Search for patterns
for category, pattern_list in patterns.items():
    print(f"\n{category.upper()} PATTERNS:")

    # Exact matches
    for pattern in pattern_list:
        count = db.query(pattern)
        if count > 0:
            print(f"  {pattern}: {count} exact matches")

    # Fuzzy matches
    for pattern in pattern_list:
        fuzzy_results = fq.query(pattern, max_mismatches=1)
        if len(fuzzy_results) > 0:
            print(f"  {pattern}: {len(fuzzy_results)} similar sequences")
```

## Performance Optimization

### Memory-Mapped Database Access

```python
from rustkmer import Database
import time

# Compare memory usage
large_db = "very_large_database.rkdb"

# Without memory mapping (loads everything)
print("Without memory mapping:")
start_time = time.time()
db1 = Database()
db1.load(large_db, memory_mapped=False)
load_time1 = time.time() - start_time
print(f"  Load time: {load_time1:.2f} seconds")

# With memory mapping (loads on demand)
print("\nWith memory mapping:")
start_time = time.time()
db2 = Database()
db2.load(large_db, memory_mapped=True)
load_time2 = time.time() - start_time
print(f"  Load time: {load_time2:.2f} seconds")

# Query performance comparison
test_kmers = ["ATCGATCG", "GCTAGCTA", "CCCCCCCC"]
print("\nQuery performance:")

# Time queries without memory mapping
start_time = time.time()
for kmer in test_kmers:
    db1.query(kmer)
time1 = time.time() - start_time

# Time queries with memory mapping
start_time = time.time()
for kmer in test_kmers:
    db2.query(kmer)
time2 = time.time() - start_time

print(f"  Without memory mapping: {time1*1000:.2f} ms")
print(f"  With memory mapping: {time2*1000:.2f} ms")
```

### Optimal Thread Configuration

```python
from rustkmer import KmerCounter
import multiprocessing
import time

# Determine optimal thread count
cpu_count = multiprocessing.cpu_count()
file_to_process = "large_genome.fa.gz"

# Test different thread counts
thread_counts = [1, 2, 4, 8, cpu_count]
times = {}

for threads in thread_counts:
    if threads > cpu_count:
        continue

    print(f"\nTesting with {threads} threads...")
    counter = KmerCounter(k=31, canonical=True, threads=threads)

    start_time = time.time()
    counter.count_file(file_to_process)
    elapsed = time.time() - start_time

    times[threads] = elapsed
    print(f"  Time: {elapsed:.2f} seconds")
    print(f"  K-mers: {counter.get_total_count():,}")

# Find optimal configuration
optimal_threads = min(times, key=times.get)
print(f"\nOptimal thread count: {optimal_threads} ({times[optimal_threads]:.2f} seconds)")

# Calculate efficiency
baseline = times[1]
for threads, elapsed in times.items():
    efficiency = baseline / elapsed / threads * 100
    print(f"  {threads} threads: {efficiency:.1f}% efficiency")
```

## Integration Examples

### With Pandas

```python
import pandas as pd
from rustkmer import Database

# Load database
db = Database()
db.load("expression_data.rkdb")

# Read query data
df = pd.read_csv("kmer_queries.csv")

# Batch query
sequences = df['sequence'].tolist()
counts = db.query_multiple(sequences)

# Add results to DataFrame
df['count'] = counts
df['abundance'] = df['count'] / df['count'].sum()

# Filter significant results
significant = df[df['count'] > 100]
print(f"Found {len(significant)} significant k-mers (count > 100)")

# Save results
significant.to_csv("significant_kmers.csv", index=False)
```

### With Matplotlib

```python
import matplotlib.pyplot as plt
import numpy as np
from rustkmer import Database

# Load database
db = Database()
db.load("sample.rkdb")

# Get k-mer abundance distribution
# Note: This requires a method to get all k-mers
# For now, we'll simulate with queries
kmer_counts = []
test_kmers = [f"{'ATCG' * 5}{i:02d}" for i in range(100)]

for kmer in test_kmers:
    count = db.query(kmer)
    if count > 0:
        kmer_counts.append(count)

# Create histogram
plt.figure(figsize=(10, 6))
plt.hist(kmer_counts, bins=50, log=True, alpha=0.7, color='blue')
plt.xlabel('K-mer Count')
plt.ylabel('Number of K-mers (log scale)')
plt.title('K-mer Abundance Distribution')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('kmer_distribution.png', dpi=300)
plt.show()

# Summary statistics
if kmer_counts:
    print(f"\nK-mer count statistics:")
    print(f"  Total k-mers found: {len(kmer_counts)}")
    print(f"  Mean count: {np.mean(kmer_counts):.2f}")
    print(f"  Median count: {np.median(kmer_counts):.2f}")
    print(f"  Max count: {max(kmer_counts)}")
```

### With Scikit-learn

```python
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import PCA
import numpy as np
from rustkmer import Database

# Extract features using RustKmer
def extract_kmer_features(sequences, k=21):
    """Extract k-mer features using RustKmer"""
    db = Database()
    counter = KmerCounter(k=k, canonical=True)

    # Count k-mers from all sequences
    for seq in sequences:
        counter.count_string(seq)

    # Get all unique k-mers as features
    # Note: This would need a method to get all k-mers
    # For now, we'll use a subset
    feature_kmers = test_kmers[:1000]  # Example subset

    # Create feature matrix
    features = np.zeros((len(sequences), len(feature_kmers)))
    for i, seq in enumerate(sequences):
        for j, kmer in enumerate(feature_kmers):
            features[i, j] = counter.get_kmer_count(kmer)

    return features, feature_kmers

# Example usage
sequences = [
    "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC",
    "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC",
    # ... more sequences
]

# Extract features
features, feature_names = extract_kmer_features(sequences, k=7)

# Apply dimensionality reduction
pca = PCA(n_components=10)
reduced_features = pca.fit_transform(features)

print(f"Original features: {features.shape[1]}")
print(f"Reduced features: {reduced_features.shape[1]}")
print(f"Explained variance ratio: {pca.explained_variance_ratio_.sum():.3f}")
```

## Complete Workflow Example

```python
from rustkmer import KmerCounter, Database, FuzzyQuery
import os
import json
import time

def complete_genomics_workflow(input_dir, output_dir):
    """Complete genomics analysis workflow"""

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # 1. Find all sequence files
    sequence_files = []
    for f in os.listdir(input_dir):
        if f.endswith((".fa", ".fa.gz", ".fq", ".fq.gz")):
            sequence_files.append(os.path.join(input_dir, f))

    print(f"Found {len(sequence_files)} sequence files")

    # 2. Count k-mers from all files
    k = 31
    counter = KmerCounter(k=k, canonical=True)

    print("\nCounting k-mers...")
    start_time = time.time()

    for file in sequence_files:
        print(f"  Processing {os.path.basename(file)}")
        counter.count_file(file)

    counting_time = time.time() - start_time
    print(f"Counting completed in {counting_time:.2f} seconds")

    # 3. Save database
    db_path = os.path.join(output_dir, f"kmer_database_k{k}.rkdb")
    counter.save_to_database(db_path)
    print(f"\nDatabase saved to {db_path}")

    # 4. Load database for analysis
    db = Database()
    db.load(db_path)

    # 5. Get statistics
    stats = db.get_stats()
    print(f"\nDatabase Statistics:")
    print(f"  Total k-mers: {stats['total_kmers']:,}")
    print(f"  Unique k-mers: {stats['unique_kmers']:,}")
    print(f"  Database size: {os.path.getsize(db_path) / 1024 / 1024:.2f} MB")

    # 6. Perform some queries
    test_sequences = [
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC",
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC"
    ]

    print("\nQuery Results:")
    for seq in test_sequences:
        count = db.query(seq)
        print(f"  {seq[:20]}...: {count}")

    # 7. Fuzzy search example
    fq = FuzzyQuery()
    fq.load(db_path)

    pattern = "AATN"  # Find sequences with this pattern
    fuzzy_results = fq.query(pattern)
    print(f"\nFuzzy search for '{pattern}': {len(fuzzy_results)} matches")

    # 8. Save results
    results = {
        'statistics': stats,
        'query_results': {seq: db.query(seq) for seq in test_sequences},
        'fuzzy_matches': len(fuzzy_results),
        'processing_time': {
            'counting': counting_time,
            'total': time.time() - start_time
        }
    }

    results_path = os.path.join(output_dir, "analysis_results.json")
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {results_path}")
    return results

# Run the workflow
# results = complete_genomics_workflow("data/sequences", "results/")
```

## Error Handling Patterns

```python
from rustkmer import KmerCounter, Database, SequenceError, DatabaseError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_kmer_counting(file_path, k=31):
    """Safely count k-mers with comprehensive error handling"""
    try:
        # Validate file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Validate k-mer size
        if not 1 <= k <= 127:
            raise ValueError(f"Invalid k-mer size: {k}. Must be between 1 and 127")

        # Create counter
        counter = KmerCounter(k=k, canonical=True)

        # Count k-mers
        logger.info(f"Counting k-mers in {file_path}")
        counter.count_file(file_path)

        # Get results
        total = counter.get_total_count()
        unique = counter.get_unique_count()

        logger.info(f"Successfully counted {total:,} total, {unique:,} unique k-mers")

        return {
            'total': total,
            'unique': unique,
            'file_path': file_path,
            'k': k
        }

    except FileNotFoundError as e:
        logger.error(f"File error: {e}")
        return None

    except ValueError as e:
        logger.error(f"Parameter error: {e}")
        return None

    except SequenceError as e:
        logger.error(f"Sequence processing error: {e}")
        return None

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None

# Usage example
result = safe_kmer_counting("example.fa.gz", k=31)
if result:
    print(f"Success! Total k-mers: {result['total']:,}")
```

These examples demonstrate common patterns and best practices for using RustKmer in various scenarios.