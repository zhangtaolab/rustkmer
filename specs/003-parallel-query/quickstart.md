# Quick Start Guide: 21-mer Performance Testing

**Version**: 1.0.0
**Date**: 2025-11-28
**Purpose**: Compare multi-threading vs single-threading performance for 21-mer k-mer queries

## Overview

This guide provides step-by-step instructions for conducting 21-mer performance testing to determine if multi-threading provides significant benefits over single-threaded execution for larger k-mer sizes.

### Key Features

- **Adaptive Parallelism**: Automatically optimizes thread count based on batch size
- **Multiple Input Sources**: Support for command line, file, and stdin input
- **Performance Analysis**: Detailed metrics and optimization recommendations
- **Memory Optimization**: Intelligent database caching and memory mapping
- **Backward Compatibility**: Works with existing rustkmer database formats

## Installation

Ensure you have rustkmer built with parallel query support:

```bash
# From source
git clone https://github.com/your-org/rustkmer.git
cd rustkmer
cargo build --release

# The queryx command will be available as:
./target/release/rustkmer queryx --help
```

## Basic Usage

### Command Line Interface

```bash
rustkmer queryx [OPTIONS] --database <DB_FILE> <INPUT>
```

### Essential Options

- `--database, -d <PATH>`: Database file to query (required)
- `--kmers, -k <SEQ1 SEQ2 ...>`: K-mers to query directly
- `--file, -f <PATH>`: File containing k-mers (one per line)
- `--threads, -t <NUM>`: Thread count (0 = auto-detect)
- `--batch-size <NUM>`: Processing batch size (default: 1000)
- `--preload`: Preload database into memory
- `--profile`: Enable performance profiling
- `--output, -o <PATH>`: Output file (default: stdout)

## Usage Examples

### 1. Quick Batch Query from Command Line

```bash
# Query multiple k-mers directly
rustkmer queryx --database genome.rkdb --kmers ATGCGAT GCTAGCTA TTAGGCC

# With auto thread detection and profiling
rustkmer queryx \
  --database genome.rkdb \
  --kmers ATGCGAT GCTAGCTA TTAGGCC \
  --threads 0 \
  --profile
```

**Expected Output**:
```
ATGCGAT	42
GCTAGCTA	0
TTAGGCC	15

=== Performance Report ===
Total time: 45.2ms
Queries processed: 3
Queries per second: 66.37
Thread count: 4
Speedup factor: 1.8x vs single-threaded
Recommendations: Excellent performance for small batch size
```

### 2. Large Batch Query from File

```bash
# Create a file with k-mers (one per line)
cat > query_kmers.txt << EOF
ATGCGATGCTAGCGCTAGCTA
GCTAGCTAGCTAGCTAGCTAG
TTAGGCCAATGCGATGCTAGC
CGATCGATCGATCGATCGATC
# ... many more k-mers
EOF

# Process large batch with optimized settings
rustkmer queryx \
  --database large_genome.rkdb \
  --file query_kmers.txt \
  --threads 8 \
  --batch-size 2000 \
  --preload \
  --progress \
  --profile \
  --output results.txt
```

**Expected Output** (with --progress):
```
Loading database... [████████████████████] 100%
Processing k-mers... [████████████████████] 100% (10,000/10,000)

=== Performance Report ===
Total time: 1.25s
Database load time: 125.3ms
Queries processed: 10,000
Queries per second: 8,000
Thread count: 8
Cache hit rate: 94.2%
Peak memory usage: 256MB
Speedup factor: 4.2x vs single-threaded
Efficiency score: 0.89

Recommendations:
- Excellent parallel performance for this batch size
- Memory mapping would improve performance for this database size
- Current batch size is optimal for your system
```

### 3. Pipeline Integration

```bash
# Use with other bioinformatics tools
cat transcripts.fasta | \
  extract_kmers.py -k 21 | \
  rustkmer queryx \
    --database transcriptome.rkdb \
    --threads 0 \
    --profile \
  > expression_counts.txt
```

### 4. Performance Comparison

```bash
# Compare single-threaded vs multi-threaded performance
echo "Testing performance with 1000 k-mers..."

# Single-threaded baseline
time rustkmer query \
  --database genome.rkdb \
  --file test_kmers.txt \
  > single_threaded.txt

# Multi-threaded queryx
time rustkmer queryx \
  --database genome.rkdb \
  --file test_kmers.txt \
  --threads 8 \
  --profile \
  > multi_threaded.txt

# Results will show the exact performance improvement
```

## Input Formats

### Command Line Arguments
```bash
rustkmer queryx --database db.rkdb --kmers ATGC CGTA TACG
```

### File Input
Create a text file with one k-mer per line:
```
ATGCGATGCTAGCGCTAGCTA
GCTAGCTAGCTAGCTAGCTAG
TTAGGCCAATGCGATGCTAGC
CGATCGATCGATCGATCGATC
```

### Standard Input
```bash
echo -e "ATGC\nCGTA\nTACG" | rustkmer queryx --database db.rkdb
```

## Output Formats

### Default Tab-Separated Format
```
KMER    COUNT
ATGCGAT 42
GCTAGCTA       0
TTAGGCC 15
```

### JSON Format (with --profile)
```json
{
  "success": true,
  "results": [
    {"kmer": "ATGCGAT", "count": 42, "found": true},
    {"kmer": "GCTAGCTA", "count": null, "found": false}
  ],
  "performance": {
    "total_time_ms": 1250,
    "queries_per_second": 8000,
    "speedup_factor": 3.2,
    "recommendations": [
      "Excellent parallel performance for this batch size"
    ]
  }
}
```

## Performance Optimization

### Adaptive Thread Management

queryx automatically adjusts thread count based on batch size:

- **Small batches (<100)**: Single-threaded (avoid overhead)
- **Medium batches (100-1000)**: 50% of CPU cores
- **Large batches (>1000)**: All available CPU cores

### Memory Optimization

```bash
# For small databases (<1GB)
rustkmer queryx --database small.rkdb --file kmers.txt --preload

# For large databases (>1GB)
rustkmer queryx --database large.rkdb --file kmers.txt

# For memory-constrained systems
rustkmer queryx --database db.rkdb --file kmers.txt --batch-size 500
```

### Batch Size Tuning

```bash
# Test different batch sizes for your system
for size in 500 1000 2000 5000; do
  echo "Testing batch size: $size"
  rustkmer queryx \
    --database db.rkdb \
    --file large_kmer_list.txt \
    --batch-size $size \
    --threads 8 \
    --profile
done
```

## Troubleshooting

### Common Issues

#### 1. Out of Memory
```bash
# Reduce memory usage
rustkmer queryx \
  --database huge_db.rkdb \
  --file kmers.txt \
  --batch-size 100 \
  --threads 2
```

#### 2. Poor Performance
```bash
# Check if database is sorted (required for optimal performance)
rustkmer info database.rkdb

# If not sorted, recreate with sorting
rustkmer count --input input.fa --output sorted_db.rkdb --sort
```

#### 3. Thread Issues
```bash
# Limit thread count manually
rustkmer queryx --database db.rkdb --file kmers.txt --threads 4

# Or let system decide (recommended)
rustkmer queryx --database db.rkdb --file kmers.txt --threads 0
```

### Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `Database not found` | Database file path incorrect | Verify file path and permissions |
| `Invalid k-mer sequence` | Non-DNA characters in input | Filter input to A,C,G,T only |
| `Insufficient memory` | Not enough RAM for preload | Use without --preload flag |
| `Thread creation failed` | System thread limit reached | Reduce thread count |

### Performance Debugging

```bash
# Enable verbose output for detailed debugging
rustkmer queryx \
  --database db.rkdb \
  --file kmers.txt \
  --verbose \
  --profile

# Check system resources
rustkmer queryx \
  --database db.rkdb \
  --file kmers.txt \
  --profile \
  --memory-limit-mb 512
```

## Best Practices

### 1. Database Preparation
```bash
# Always use sorted databases for optimal performance
rustkmer count --input genome.fa --output genome_sorted.rkdb --sort
```

### 2. Batch Size Optimization
- Start with default (1000) and adjust based on performance
- Larger batches generally perform better with more threads
- Monitor memory usage when increasing batch size

### 3. Thread Count
- Use `--threads 0` for automatic optimization
- Manually set only if you have specific constraints
- Consider other system load when setting thread count

### 4. Memory Management
- Use `--preload` for databases that fit in available RAM
- For large databases, let queryx manage memory automatically
- Monitor memory usage with `--profile`

## Integration Examples

### Bash Script Integration
```bash
#!/bin/bash
# batch_query.sh - Process multiple query files

DATABASE=$1
THREADS=${2:-0}
OUTPUT_DIR="results"

mkdir -p $OUTPUT_DIR

for file in query_files/*.txt; do
  basename=$(basename "$file" .txt)
  echo "Processing $file..."

  rustkmer queryx \
    --database "$DATABASE" \
    --file "$file" \
    --threads "$THREADS" \
    --profile \
    --output "$OUTPUT_DIR/${basename}_results.txt"
done

echo "All queries completed. Results in $OUTPUT_DIR/"
```

### Python Integration
```python
#!/usr/bin/env python3
# parallel_query.py - Python wrapper for queryx

import subprocess
import json
import sys

def run_queryx(database, kmers, threads=0):
    """Run queryx and return results"""
    cmd = [
        'rustkmer', 'queryx',
        '--database', database,
        '--kmers'] + kmers + [
        '--threads', str(threads),
        '--profile'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"queryx failed: {result.stderr}")

    return result.stdout

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parallel_query.py <database> [kmers...]")
        sys.exit(1)

    database = sys.argv[1]
    kmers = sys.argv[2:] if len(sys.argv) > 2 else ["ATGC", "CGTA"]

    output = run_queryx(database, kmers)
    print(output)
```

## Performance Benchmarks

### Expected Performance by Batch Size

| Batch Size | Expected Speedup | Optimal Threads |
|------------|------------------|-----------------|
| 10-50      | 1.1-1.3x        | 2-4             |
| 100-500    | 1.5-2.5x        | 4-6             |
| 1,000-5,000| 2.5-4.0x        | 6-8             |
| 10,000+    | 3.0-5.0x        | All cores       |

### Memory Requirements

| Database Size | Memory Usage (with preload) | Memory Usage (without preload) |
|---------------|----------------------------|--------------------------------|
| <100MB        | ~150MB                     | ~50MB                          |
| 100MB-1GB     | ~1.2x DB size              | ~100MB                         |
| 1GB-10GB      | Not recommended            | ~200MB                         |
| >10GB         | Not recommended            | ~300MB                         |

## Support

For issues, feature requests, or contributions:
- GitHub Repository: https://github.com/your-org/rustkmer
- Documentation: https://rustkmer.org/docs
- Issues: https://github.com/your-org/rustkmer/issues