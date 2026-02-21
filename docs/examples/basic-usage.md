# Basic Usage

This guide provides basic usage examples for both the Rust CLI and Python API. Learn the fundamental operations of RustKmer through practical examples.

## Prerequisites

### For Rust CLI
- Rust 1.80+ installed
- Cargo package manager

### For Python API
- Python 3.8+ installed
- RustKmer Python package: `pip install rustkmer`

## Quick Start

### Option 1: Using the Python API (Recommended for beginners)

```python
from pyrustkmer import PyCounter, LoadMode, PyDatabase, PyFuzzyQuery

# Create k-mer database from FASTA file
counter = PyCounter(31, canonical=True)
counter.add_from_fasta("sequences.fasta")
counter.save_database("output.rkdb")

# Query database
db = PyDatabase("output.rkdb", LoadMode.Preload)
result = db.query_exact("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
print(f"Count: {result.count}")
```

### Option 2: Using the Rust CLI

```bash
# Count k-mers from FASTA file
rustkmer count -k 31 -o output.rkdb sequences.fasta

# Query k-mers
rustkmer query output.rkdb ATCGATCGATCGATCGATCGATCGATCGATCGATCG

# Get database statistics
rustkmer stats output.rkdb
```

## 1. Creating a K-mer Database

### Python API

```python
from pyrustkmer import PyCounter, LoadMode, PyFuzzyQuery

# Method 1: From single file
counter = PyCounter(31, canonical=True)
counter.add_from_fasta("input.fasta")
counter.save_database("database.rkdb")

# Method 2: From multiple files
file_list = ["file1.fasta", "file2.fasta", "file3.fasta"]
counter = PyCounter(25)
counter.count_file_list(file_list)
counter.save_database("combined.rkdb")

# Method 3: From sequence strings
sequences = [
    "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG",
    "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG"
]
counter = PyCounter(21)
for seq in sequences:
    counter.add_sequence(seq)
counter.save_database("from_strings.rkdb")
```

### Rust CLI

```bash
# Basic counting
rustkmer count -k 31 input.fasta -o database.rkdb

# Multiple files
rustkmer count -k 25 file1.fasta file2.fasta file3.fasta -o combined.rkdb

# With progress reporting
rustkmer count -k 31 input.fasta -o database.rkdb --progress

# Non-canonical (store both strands)
rustkmer count -k 31 input.fasta -o database_stranded.rkdb --no-canonical
```

## 2. Querying K-mers

### Python API

```python
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

# Single query
db = PyDatabase("database.rkdb", LoadMode.Preload)
result = db.query_exact("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
print(f"Found: {result.found}")
print(f"Count: {result.count}")
print(f"Canonical: {result.canonical}")

# Multiple queries
kmer_list = ["ATCGATCG...", "GCTAGCTA...", "TTTTTTTT..."]
db = PyDatabase("database.rkdb", LoadMode.Preload)
    for kmer in kmer_list:
        result = db.query_exact(kmer)
        status = "✓" if result.found else "✗"
        print(f"{kmer[:10]}... {status} {result.count}")
```

### Rust CLI

```bash
# Single query
rustkmer query database.rkdb ATCGATCGATCGATCGATCGATCGATCGATCGATCG

# Multiple queries from file
echo -e "ATCGATCGATCGATCGATCGATCGATCGATCGATCG\nGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG" > queries.txt
rustkmer query database.rkdb --file queries.txt

# Query with specific k-mer size
rustkmer query database.rkdb ATCGATCGATCGATCGATCGATCGATCGATCGATCG -k 31
```

## 3. Fuzzy Searching

### Python API

```python
from pyrustkmer import Database, PyFuzzyQuery

db = PyDatabase("database.rkdb", LoadMode.Preload)
    # Basic fuzzy query
    reference_kmer = "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
    result = fuzzy.query_fuzzy(reference_kmer, mutations=2)

    print(f"Total matches: {result.total_matches}")
    print(f"Exact matches: {result.exact_matches}")
    print(f"Fuzzy matches: {result.fuzzy_matches}")

    # Show fuzzy matches
    for match in result.get_fuzzy_matches():
        print(f"  {match.kmer}: {match.count} (distance={match.distance})")

    # Position-specific mutations
    result = fuzzy.query_fuzzy(
        reference_kmer,
        mutations=2,
        position_mutations="10,15:1;20,25:2"
    )
```

### Rust CLI

```bash
# Basic fuzzy query
rustkmer fuzzy-query database.rkdb ATCGATCGATCGATCGATCGATCGATCGATCGATCG -m 2

# Position mutations
rustkmer fuzzy-query database.rkdb ATCGATCGATCGATCGATCGATCGATCGATCGATCG \
    -m 3 \
    --position-mutations "10,15:1;20,25:2"

# Multiple fuzzy queries
echo -e "ATCGATCGATCGATCGATCGATCGATCGATCGATCG\nGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG" > fuzzy_queries.txt
rustkmer fuzzy-query database.rkdb --file fuzzy_queries.txt -m 2
```

## 4. Database Statistics

### Python API

```python
from pyrustkmer import Database, PyFuzzyQuery

db = PyDatabase("database.rkdb", LoadMode.Preload)
    stats = db.get_stats()

    print("Database Statistics:")
    print(f"  K-mer size: {stats.kmer_size}")
    print(f"  Unique k-mers: {stats.unique_kmers:,}")
    print(f"  Total counts: {stats.total_counts:,}")
    print(f"  File size: {stats.file_size:,} bytes")
    print(f"  Format version: {stats.format_version}")

    # Calculate derived statistics
    if stats.unique_kmers > 0:
        avg_count = stats.total_counts / stats.unique_kmers
        compression_ratio = stats.file_size / (stats.unique_kmers * 8)
        print(f"  Average count: {avg_count:.2f}")
        print(f"  Compression ratio: {compression_ratio:.3f}")
```

### Rust CLI

```bash
# Basic statistics
rustkmer stats database.rkdb

# Detailed statistics
rustkmer stats database.rkdb --verbose

# CSV format output
rustkmer stats database.rkdb --format csv > stats.csv

# JSON format output
rustkmer stats database.rkdb --format json > stats.json
```

## 5. Exporting Database Content

### Python API

```python
import csv
from pyrustkmer import Database, PyFuzzyQuery

# Export to CSV
db = PyDatabase("database.rkdb", LoadMode.Preload)
    with open("kmer_export.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["kmer", "count", "canonical"])

        for result in db.dump(limit=10000):
            writer.writerow([result.kmer, result.count, result.canonical])

# Export canonical k-mers only
db = PyDatabase("database.rkdb", LoadMode.Preload)
    canonical_kmers = []
    for result in db.dump(limit=5000, canonical_only=True):
        canonical_kmers.append((result.kmer, result.count))

print(f"Exported {len(canonical_kmers)} canonical k-mers")
```

### Rust CLI

```bash
# Export to stdout
rustkmer dump database.rkdb

# Export with limit
rustkmer dump database.rkdb --limit 10000

# Export canonical only
rustkmer dump database.rkdb --canonical-only

# Export to file
rustkmer dump database.rkdb > kmer_export.txt

# TSV format
rustkmer dump database.rkdb --format tsv > kmer_export.tsv
```

## 6. Batch Operations

### Python API

```python
from pyrustkmer import Database, PyFuzzyQuery

# Batch exact queries
kmer_list = ["ATCGATCG...", "GCTAGCTA...", "TTTTTTTT..."]

db = PyDatabase("database.rkdb", LoadMode.Preload)
    results = {}
    for kmer in kmer_list:
        result = db.query_exact(kmer)
        results[kmer] = result.count

# Batch fuzzy queries
db = PyDatabase("database.rkdb", LoadMode.Preload)
    batch_result = db.fuzzy_query_batch(
        kmer_list,
        mutations=2,
        max_workers=4
    )

    for kmer, result in batch_result.successes.items():
        print(f"{kmer}: {result.total_matches} matches")
```

### Rust CLI

```bash
# Create query file
cat > queries.txt << EOF
ATCGATCGATCGATCGATCGATCGATCGATCGATCG
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT
EOF

# Batch query
rustkmer query database.rkdb --file queries.txt

# Batch fuzzy query
rustkmer fuzzy-query database.rkdb --file queries.txt -m 2
```

## 7. Error Handling

### Python API

```python
from pyrustkmer import Database, DatabaseNotFoundError, InvalidKmerError, QueryError, PyFuzzyQuery

# Proper error handling
try:
    db = PyDatabase("nonexistent.rkdb", LoadMode.Preload)
        result = db.query_exact("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
except DatabaseNotFoundError:
    print("Database file not found!")
except InvalidKmerError as e:
    print(f"Invalid k-mer: {e.kmer} - {e.reason}")
except QueryError as e:
    print(f"Query error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")

# Validate k-mers before querying
def validate_kmer(kmer):
    """Validate k-mer format."""
    if not kmer:
        raise InvalidKmerError(kmer, "Empty k-mer")
    if not all(base in 'ATCG' for base in kmer.upper()):
        raise InvalidKmerError(kmer, "Invalid nucleotides")
    if len(kmer) < 10:
        raise InvalidKmerError(kmer, "K-mer too short")
    return kmer.upper()

try:
    kmer = validate_kmer("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
    db = PyDatabase("database.rkdb", LoadMode.Preload)
        result = db.query_exact(kmer)
except InvalidKmerError as e:
    print(f"Validation failed: {e}")
```

### Rust CLI

```bash
# Check if file exists before querying
if [ -f "database.rkdb" ]; then
    rustkmer query database.rkdb ATCGATCGATCGATCGATCGATCGATCGATCGATCG
else
    echo "Database file not found!"
fi

# Validate k-mer format
kmer="ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
if [[ $kmer =~ ^[ATCGatcg]+$ ]]; then
    rustkmer query database.rkdb "$kmer"
else
    echo "Invalid k-mer format!"
fi
```

## 8. Performance Tips

### Python API

```python
from pyrustkmer import KmerCounter, Database, PyFuzzyQuery
import time

# Use appropriate k-mer size
def choose_kmer_size(read_length):
    """Choose optimal k-mer size based on read length."""
    if read_length < 100:
        return 21
    elif read_length < 500:
        return 31
    else:
        return 51

# Use batch operations for better performance
def batch_query(database_path, kmer_list, mutations=2):
    """Perform batch queries for better performance."""
    db = PyDatabase(database_path, LoadMode.Preload)
        return db.fuzzy_query_batch(kmer_list, mutations=mutations, max_workers=4)

# Memory-efficient processing of large databases
def process_large_database(database_path, output_file):
    """Process large database without loading everything into memory."""
    db = PyDatabase(database_path, LoadMode.Preload)
        with open(output_file, 'w') as f:
            for result in db.dump():
                if result.count > 10:  # Filter high-count k-mers
                    f.write(f"{result.kmer}\t{result.count}\n")
```

### Rust CLI

```bash
# Use progress reporting for long operations
rustkmer count -k 31 large_file.fasta -o database.rkdb --progress

# Use compression for large outputs
rustkmer dump database.rkdb | gzip > kmer_export.txt.gz

# Process in parallel (when available)
rustkmer count -k 31 *.fasta -o combined.rkdb --threads 8

# Use streaming mode for very large files
rustkmer query database.rkdb --file huge_query_list.txt --streaming
```

## 9. Real-world Example: K-mer Analysis Pipeline

### Python API

```python
#!/usr/bin/env python3
"""
Complete k-mer analysis pipeline.
"""

from pyrustkmer import KmerCounter, Database, PyFuzzyQuery
import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os

def analyze_fasta(input_fasta, k=31, output_prefix="analysis"):
    """Complete k-mer analysis pipeline."""

    print(f"Analyzing {input_fasta} with k={k}")

    # 1. Count k-mers
    print("1. Counting k-mers...")
    counter = PyCounter(k, canonical=True)
    counter.add_from_fasta(input_fasta)

    # 2. Save database
    db_path = f"{output_prefix}.rkdb"
    counter.save_database(db_path)

    # 3. Get statistics
    print("2. Getting statistics...")
    db = PyDatabase(db_path, LoadMode.Preload)
        stats = db.get_stats()
        print(f"   Unique k-mers: {stats.unique_kmers:,}")
        print(f"   Total counts: {stats.total_counts:,}")

    # 4. Extract top k-mers
    print("3. Extracting top k-mers...")
    db = PyDatabase(db_path, LoadMode.Preload)
        data = []
        for result in db.dump(limit=10000, canonical_only=True):
            data.append({
                'kmer': result.kmer,
                'count': result.count
            })

    df = pd.DataFrame(data)

    # 5. Save results
    print("4. Saving results...")
    df.to_csv(f"{output_prefix}_kmer_counts.csv", index=False)

    # 6. Create visualization
    plt.figure(figsize=(10, 6))
    plt.hist(df['count'], bins=50, alpha=0.7)
    plt.xlabel('K-mer Count')
    plt.ylabel('Frequency')
    plt.title('K-mer Count Distribution')
    plt.savefig(f"{output_prefix}_distribution.png", dpi=150, bbox_inches='tight')

    print(f"Analysis complete! Results saved to {output_prefix}_*")

    # 7. Summary statistics
    print("\nSummary Statistics:")
    print(f"   Mean count: {df['count'].mean():.1f}")
    print(f"   Median count: {df['count'].median():.1f}")
    print(f"   Max count: {df['count'].max()}")
    print(f"   Top 1% threshold: {df['count'].quantile(0.99):.1f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="K-mer analysis pipeline")
    parser.add_argument("input", help="Input FASTA file")
    parser.add_argument("-k", type=int, default=31, help="K-mer size")
    parser.add_argument("-o", "--output", default="analysis", help="Output prefix")

    args = parser.parse_args()
    analyze_fasta(args.input, args.k, args.output)
```

### Rust CLI Equivalent

```bash
#!/bin/bash
# kmer_analysis.sh - K-mer analysis pipeline

set -euo pipefail

input_file=$1
k=${2:-31}
output_prefix=${3:-analysis}

echo "Analyzing $input_file with k=$k"

# 1. Count k-mers
echo "1. Counting k-mers..."
rustkmer count -k $k "$input_file" -o "${output_prefix}.rkdb" --progress

# 2. Get statistics
echo "2. Getting statistics..."
stats=$(rustkmer stats "${output_prefix}.rkdb" --format json)
echo "   Statistics: $stats"

# 3. Extract top k-mers
echo "3. Extracting top k-mers..."
rustkmer dump "${output_prefix}.rkdb" --limit 10000 --canonical-only > "${output_prefix}_kmer_counts.txt"

# 4. Convert to CSV format
echo "4. Converting to CSV..."
awk 'NR>1 {print $1","$2}' "${output_prefix}_kmer_counts.txt" > "${output_prefix}_kmer_counts.csv"

echo "Analysis complete! Results saved to ${output_prefix}_*"
```

## 10. Choosing Between Python API and CLI

### Use Python API when:
- You need programmatic control
- Integration with other Python libraries (pandas, matplotlib, etc.)
- Complex data processing pipelines
- Custom error handling
- Interactive analysis (Jupyter notebooks)

### Use CLI when:
- Simple, one-off operations
- Shell scripting workflows
- High-performance batch processing
- Integration with other command-line tools
- Minimal setup required

### Example Decision Flow:

```python
# Use Python API for analysis
if need_custom_processing or integrate_with_python_libs:
    use_python_api()

# Use CLI for simple operations
elif simple_oneoff_task or shell_scripting:
    use_cli()

# Use both for complex pipelines
else:
    use_cli_for_heavy_lifting()
    use_python_api_for_analysis()
```

## Next Steps

- Explore [advanced examples](../python/) for specific use cases
- Read the [Python API documentation](../../api-reference/python/)
- Check the [tutorials](../../tutorials/) for detailed workflows
- Review the [full API reference](../../api-reference/) for all available features