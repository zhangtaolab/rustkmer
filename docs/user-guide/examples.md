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
from pyrustkmer import PyCounter

# Create counter
counter = PyCounter(21, canonical=True)

# Count k-mers
sequence = "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC"
counter.add_sequence(sequence)

# Get results
stats = counter.get_stats()
total = stats.total_kmers
unique = stats.unique_kmers
print(f"Total: {total}, Unique: {unique}")
```

### Query a Single K-mer

```python
from pyrustkmer import PyDatabase, LoadMode

# Load database
db = PyDatabase("example.rkdb", LoadMode.Preload)

# Query
kmer = "ATCGATCGATCGATCGATCGA"
result = db.query_exact(kmer)
print(f"'{kmer}' appears {result.count} times")
```

## File Processing

### Process FASTA Files

```python
from pyrustkmer import PyCounter
import os

# Process all FASTA files in directory
counter = PyCounter(31, canonical=True)

fa_files = [f for f in os.listdir("data/") if f.endswith((".fa", ".fasta"))]
for file in fa_files:
    filepath = os.path.join("data/", file)
    print(f"Processing {file}...")
    counter.add_from_fasta(filepath)

print(f"\nTotal k-mers from all files: {counter.get_stats().total_kmers:,}")

# Save combined results
counter.save_database("combined_counts.rkdb")
```

### Process FASTQ Files with Quality Filtering

```python
from pyrustkmer import PyCounter

# Create counter
counter = PyCounter(21)

# Process FASTQ (quality scores ignored in counting)
counter.add_from_fastq("reads.fastq")

# For quality-based processing, filter first:
from Bio import SeqIO

quality_threshold = 30
counter = PyCounter(21)

for record in SeqIO.parse("reads.fastq", "fastq"):
    qualities = record.letter_annotations["phred_quality"]
    if all(q >= quality_threshold for q in qualities):
        # High quality read
        counter.add_sequence(str(record.seq))
```

### Handle Compressed Files

```python
from pyrustkmer import PyCounter

# RustKmer automatically handles gzip/bzip2/xz compression
counter = PyCounter(31)

# All these work transparently
files = [
    "genome.fa",
    "genome.fa.gz",
    "reads.fq",
    "reads.fq.gz"
]

for file in files:
    try:
        if file.endswith((".fq", ".fq.gz", ".fastq", ".fastq.gz")):
            counter.add_from_fastq(file)
        else:
            counter.add_from_fasta(file)
        print(f"Processed {file}")
    except Exception as e:
        print(f"Error processing {file}: {e}")
```

## Database Operations

### Create and Query Database

```python
from pyrustkmer import PyCounter, PyDatabase, LoadMode

# Step 1: Count k-mers
counter = PyCounter(31, canonical=True)
counter.add_from_fasta("sample.fa.gz")

# Step 2: Save to database
database_path = "sample_k31.rkdb"
counter.save_database(database_path)

# Step 3: Load and query
db = PyDatabase(database_path, LoadMode.Preload)

# Query specific k-mers (must match the database k-mer size, k=31 here)
test_kmers = [
    "ATCGATCGATCGATCGATCGATCGATCGATC",
    "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGC"
]

for kmer in test_kmers:
    result = db.query_exact(kmer)
    print(f"{kmer[:10]}...: {result.count}")
```

### Database Statistics

```python
from pyrustkmer import PyDatabase, LoadMode

db = PyDatabase("large_database.rkdb", LoadMode.Preload)

# Get comprehensive statistics (a PyDatabaseStats object, not a dict)
stats = db.get_stats()

# Pretty print statistics
print("Database Statistics:")
print(f"  Total k-mers: {stats.total_kmers:,}")
print(f"  Unique k-mers: {stats.unique_kmers:,}")
print(f"  K-mer size: {stats.kmer_size}")
print(f"  Canonical mode: {stats.canonical}")
print(f"  File size: {stats.file_size:,} bytes")

# Calculate additional metrics
if stats.total_kmers > 0:
    avg_abundance = stats.total_kmers / stats.unique_kmers
    print(f"  Average abundance: {avg_abundance:.2f}")
```

### Merge Multiple Databases

```python
from pyrustkmer import PyDatabase, LoadMode

# Create merged database from multiple sources
databases_to_merge = [
    "sample1.rkdb",
    "sample2.rkdb",
    "sample3.rkdb"
]

# Static merge method writes the merged database directly to the output path
PyDatabase.merge(databases_to_merge, "merged_all_samples.rkdb")

# Show final statistics
merged_db = PyDatabase("merged_all_samples.rkdb", LoadMode.Preload)
stats = merged_db.get_stats()
print(f"\nMerged database:")
print(f"  Total k-mers: {stats.total_kmers:,}")
print(f"  Unique k-mers: {stats.unique_kmers:,}")
```

## Batch Processing

### Batch Query from List

```python
from pyrustkmer import PyDatabase, LoadMode
import time

# Load database
db = PyDatabase("database.rkdb", LoadMode.Preload)

# Prepare query list (k-mers must match the database k-mer size)
query_kmers = [
    "ATCGATCGATCGATCGATCGATC",
    "GCTAGCTAGCTAGCTAGCTAGCT",
    "CCCCCCCCCCCCCCCCCCCCCCCC",
    # ... thousands more k-mers
]

# Batch query (more efficient; returns a dict of k-mer -> PyQueryResult)
start_time = time.time()
results = db.query_exact_batch(query_kmers)
query_time = time.time() - start_time

# Process results
for kmer, result in results.items():
    if result.found:
        print(f"{kmer}: {result.count}")

print(f"\nQueried {len(query_kmers)} k-mers in {query_time:.2f} seconds")
```

### Batch Counting Multiple Files

```python
from pyrustkmer import PyCounter
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

def count_file_kmers(filepath, k=31):
    """Count k-mers in a single file"""
    counter = PyCounter(k, canonical=True)
    counter.add_from_fasta(filepath)
    stats = counter.get_stats()
    return {
        'file': os.path.basename(filepath),
        'total': stats.total_kmers,
        'unique': stats.unique_kmers
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
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

# Load database for fuzzy search
db = PyDatabase("genome.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)

# Search with wildcards (patterns must match the database k-mer size)
print("Wildcard searches:")
wildcard_patterns = ["ATCGATCGATCGATCGATCGN", "NCGAATCGATCGATCGATCGA", "ATGNNNTAATCGATCGATCGA"]
for pattern in wildcard_patterns:
    results = fuzzy.query_fuzzy(pattern, max_mutations=0)
    print(f"Pattern '{pattern}': {results.total_matches} matches")
    for match in results.matches[:5]:  # Show first 5
        print(f"  {match.kmer}: {match.count}")
```

### Fuzzy Search with Mismatches

```python
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

db = PyDatabase("genome.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)

# Find similar sequences
query = "ATCGATCGATCGATCGATCGA"
max_mismatches = 2

results = fuzzy.query_fuzzy(query, max_mutations=max_mismatches)
print(f"Sequences similar to '{query[:10]}...' with ≤{max_mismatches} mismatches:")

# Group by number of mismatches
by_mismatches = {}
for match in results.matches:
    mismatches = match.distance if match.distance is not None else 0
    by_mismatches.setdefault(mismatches, []).append(match)

for mismatches, matches in sorted(by_mismatches.items()):
    print(f"\n{mismatches} mismatches ({len(matches)} matches):")
    for match in matches[:3]:  # Show first 3
        print(f"  {match.kmer}: {match.count}")
```

### Complex Query Patterns

```python
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

# Load databases
db = PyDatabase("annotations.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(PyDatabase("genome.rkdb", LoadMode.Preload))

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
        result = db.query_exact(pattern)
        if result.found:
            print(f"  {pattern}: {result.count} exact matches")

    # Fuzzy matches
    for pattern in pattern_list:
        fuzzy_results = fuzzy.query_fuzzy(pattern, max_mutations=1)
        if fuzzy_results.total_matches > 0:
            print(f"  {pattern}: {fuzzy_results.total_matches} similar sequences")
```

## Performance Optimization

### Memory-Mapped Database Access

```python
from pyrustkmer import PyDatabase, LoadMode
import time

# Compare memory usage
large_db = "very_large_database.rkdb"

# Without memory mapping (loads everything)
print("Without memory mapping:")
start_time = time.time()
db1 = PyDatabase(large_db, LoadMode.Preload)

load_time1 = time.time() - start_time
print(f"  Load time: {load_time1:.2f} seconds")

# With memory mapping (direct file access)
print("\nWith memory mapping:")
start_time = time.time()
db2 = PyDatabase(large_db, LoadMode.MemoryMapped)

load_time2 = time.time() - start_time
print(f"  Load time: {load_time2:.2f} seconds")

# Query performance comparison
test_kmers = ["ATCGATCGATCGATCGATCGA", "GCTAGCTAGCTAGCTAGCTAG", "CCCCCCCCCCCCCCCCCCCCC"]
print("\nQuery performance:")

# Time queries without memory mapping
start_time = time.time()
for kmer in test_kmers:
    db1.query_exact(kmer)
time1 = time.time() - start_time

# Time queries with memory mapping
start_time = time.time()
for kmer in test_kmers:
    db2.query_exact(kmer)
time2 = time.time() - start_time

print(f"  Without memory mapping: {time1*1000:.2f} ms")
print(f"  With memory mapping: {time2*1000:.2f} ms")
```

### Optimal Thread Configuration

```python
from pyrustkmer import PyCounter
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
    counter = PyCounter(31, canonical=True, threads=threads)

    start_time = time.time()
    counter.add_from_fasta(file_to_process)
    elapsed = time.time() - start_time

    times[threads] = elapsed
    print(f"  Time: {elapsed:.2f} seconds")
    print(f"  K-mers: {counter.get_stats().total_kmers:,}")

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
from pyrustkmer import PyDatabase, LoadMode

# Load database
db = PyDatabase("expression_data.rkdb", LoadMode.Preload)

# Read query data
df = pd.read_csv("kmer_queries.csv")

# Batch query (returns a dict of k-mer -> PyQueryResult)
sequences = df['sequence'].tolist()
results = db.query_exact_batch(sequences)

# Add results to DataFrame
df['count'] = [results[seq].count for seq in sequences]
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
from pyrustkmer import PyDatabase, LoadMode

# Load database
db = PyDatabase("sample.rkdb", LoadMode.Preload)

# Get k-mer abundance distribution directly from the database
entries = db.export_all_kmers()
kmer_counts = [entry.count for entry in entries if entry.found]

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
from pyrustkmer import PyCounter

# Extract features using RustKmer
def extract_kmer_features(sequences, k=21):
    """Extract k-mer features using RustKmer"""
    counter = PyCounter(k, canonical=True)

    # Count k-mers from all sequences
    for seq in sequences:
        counter.add_sequence(seq)

    # Get all unique k-mers as features (example subset)
    feature_kmers = sorted(counter.get_all_counts())[:1000]

    # Create feature matrix
    features = np.zeros((len(sequences), len(feature_kmers)))
    for i, seq in enumerate(sequences):
        seq_counter = PyCounter(k, canonical=True)
        seq_counter.add_sequence(seq)
        for j, kmer in enumerate(feature_kmers):
            features[i, j] = seq_counter.get_count(kmer)

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
from pyrustkmer import PyCounter, PyDatabase, PyFuzzyQuery, LoadMode
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
    counter = PyCounter(k, canonical=True)

    print("\nCounting k-mers...")
    start_time = time.time()

    for file in sequence_files:
        print(f"  Processing {os.path.basename(file)}")
        counter.add_from_fasta(file)

    counting_time = time.time() - start_time
    print(f"Counting completed in {counting_time:.2f} seconds")

    # 3. Save database
    db_path = os.path.join(output_dir, f"kmer_database_k{k}.rkdb")
    counter.save_database(db_path)
    print(f"\nDatabase saved to {db_path}")

    # 4. Load database for analysis
    db = PyDatabase(db_path, LoadMode.Preload)

    # 5. Get statistics
    stats = db.get_stats()
    print(f"\nDatabase Statistics:")
    print(f"  Total k-mers: {stats.total_kmers:,}")
    print(f"  Unique k-mers: {stats.unique_kmers:,}")
    print(f"  Database size: {os.path.getsize(db_path) / 1024 / 1024:.2f} MB")

    # 6. Perform some queries (k-mers must be 31 characters for k=31)
    test_sequences = [
        "ATCGATCGATCGATCGATCGATCGATCGATC",
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGC"
    ]

    print("\nQuery Results:")
    for seq in test_sequences:
        result = db.query_exact(seq)
        print(f"  {seq[:20]}...: {result.count}")

    # 7. Fuzzy search example
    fq = PyFuzzyQuery(db)

    pattern = "ATCGATCGATCGATCGATCGN"  # Find sequences with this pattern
    fuzzy_results = fq.query_fuzzy(pattern, max_mutations=0)
    print(f"\nFuzzy search for '{pattern}': {fuzzy_results.total_matches} matches")

    # 8. Save results
    results = {
        'statistics': {
            'total_kmers': stats.total_kmers,
            'unique_kmers': stats.unique_kmers,
            'kmer_size': stats.kmer_size,
        },
        'query_results': {seq: db.query_exact(seq).count for seq in test_sequences},
        'fuzzy_matches': fuzzy_results.total_matches,
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
from pyrustkmer import PyCounter
import logging
import os

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
        if not 1 <= k <= 64:
            raise ValueError(f"Invalid k-mer size: {k}. Must be between 1 and 64")

        # Create counter
        counter = PyCounter(k, canonical=True)

        # Count k-mers
        logger.info(f"Counting k-mers in {file_path}")
        counter.add_from_fasta(file_path)

        # Get results
        stats = counter.get_stats()
        total = stats.total_kmers
        unique = stats.unique_kmers

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

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None

# Usage example
result = safe_kmer_counting("example.fa.gz", k=31)
if result:
    print(f"Success! Total k-mers: {result['total']:,}")
```

These examples demonstrate common patterns and best practices for using RustKmer in various scenarios.