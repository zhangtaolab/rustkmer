# RustKmer Performance Recommendations: Optimized 21-mer Query Processing

**Based on Comprehensive Performance Analysis**
**Date**: 2025-11-28

## Summary of Findings

After extensive testing with 21-mer k-mer queries using OSA1 r7 assembly data, we have determined that **multi-threading provides no performance benefit** for k-mer query operations. This guide provides practical recommendations for optimal RustKmer usage.

## Core Recommendation

> **Use single-threaded mode (`rustkmer query`) for all k-mer query operations, including 21-mers.**

**Avoid multi-threaded mode (`rustkmer queryx`) as it provides no benefit and may slightly degrade performance.**

## Optimal Usage Patterns

### 1. Single Query Processing

```bash
# ✅ RECOMMENDED: Single-threaded query
rustkmer query database.rkdb ATGCGATGCTAGCGCTAGCTA

# ❌ NOT RECOMMENDED: Multi-threaded query (no benefit)
rustkmer queryx database.rkdb --kmers ATGCGATGCTAGCGCTAGCTA
```

### 2. Batch Query Processing

```bash
# ✅ RECOMMENDED: Process file with single-threaded mode
rustkmer query database.rkdb --file queries.txt --output results.txt

# ❌ NOT RECOMMENDED: Multi-threaded batch processing
rustkmer queryx database.rkdb --file queries.txt --threads 8
```

### 3. Large Query Sets

For processing large numbers of queries, use sequential batch processing:

```bash
# ✅ OPTIMAL: Split large query sets and process sequentially
split -l 1000 large_queries.txt batch_
for batch in batch_*; do
    echo "Processing batch: $batch"
    rustkmer query database.rkdb --file "$batch" >> results.txt
    rm "$batch"  # Clean up batch file
done
```

## Database Optimization

### 1. Create Sorted Databases

Always create sorted databases for optimal query performance:

```bash
# ✅ Use sorted databases
rustkmer count --input genome.fa --output genome_sorted.rkdb --sort --threads 1
```

### 2. Verify Database Properties

Check database before use:

```bash
# Verify database is properly sorted
rustkmer info database.rkdb
```

## Memory Management

### 1. Database Loading

```bash
# For databases that fit in RAM (<2GB)
rustkmer query database.rkdb --file queries.txt --load

# For large databases (>2GB), use memory mapping
rustkmer query database.rkdb --file queries.txt --no-load
```

### 2. Resource Monitoring

```bash
# Monitor memory usage during queries
/usr/bin/time -l rustkmer query database.rkdb --file queries.txt
```

## Pipeline Integration

### 1. Bioinformatics Pipeline

```bash
#!/bin/bash
# optimal_pipeline.sh - Optimized k-mer query pipeline

DATABASE=$1
QUERY_FILE=$2
OUTPUT_FILE=$3

echo "Processing k-mer queries with optimal single-threaded configuration..."
rustkmer query "$DATABASE" --file "$QUERY_FILE" --output "$OUTPUT_FILE"

echo "Query processing completed successfully"
echo "Results saved to: $OUTPUT_FILE"
```

### 2. Python Integration

```python
#!/usr/bin/env python3
# optimal_queries.py - Python wrapper for optimal RustKmer usage

import subprocess
import sys
import os

def query_kmers_optimal(database_path, queries, output_file=None):
    """
    Query k-mers using optimal single-threaded RustKmer configuration.

    Args:
        database_path: Path to RustKmer database file
        queries: List of k-mer strings or path to query file
        output_file: Optional output file path
    """

    cmd = ['rustkmer', 'query', database_path]

    if isinstance(queries, str) and os.path.isfile(queries):
        # Query from file
        cmd.extend(['--file', queries])
    else:
        # Query from list
        cmd.extend(queries)

    if output_file:
        cmd.extend(['--output', output_file])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise Exception(f"RustKmer query failed: {e.stderr}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python optimal_queries.py <database> <query_file> [output_file]")
        sys.exit(1)

    database = sys.argv[1]
    query_file = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else None

    print("Processing queries with optimal configuration...")
    results = query_kmers_optimal(database, query_file, output_file)

    if not output_file:
        print(results)

if __name__ == "__main__":
    main()
```

## Performance Monitoring

### 1. Benchmarking Script

```bash
#!/bin/bash
# benchmark_performance.sh - Performance benchmarking for RustKmer

DATABASE=$1
QUERY_COUNT=${2:-1000}
OUTPUT_DIR="benchmark_results"

mkdir -p "$OUTPUT_DIR"

echo "Generating test queries..."
python3 -c "
import random
random.seed(42)
bases = ['A', 'C', 'G', 'T']
for i in range($QUERY_COUNT):
    kmer = ''.join(random.choices(bases, k=21))
    print(kmer)
" > "$OUTPUT_DIR/test_queries.txt"

echo "Running benchmark..."
echo "Database: $DATABASE"
echo "Query count: $QUERY_COUNT"
echo "Starting at $(date)"

# Single-threaded benchmark (recommended)
echo "=== Single-threaded Performance ==="
start_time=$(date +%s.%N)
rustkmer query "$DATABASE" --file "$OUTPUT_DIR/test_queries.txt" > "$OUTPUT_DIR/single_results.txt"
end_time=$(date +%s.%N)
single_time=$(echo "$end_time - $start_time" | bc)
single_qps=$(echo "scale=2; $QUERY_COUNT / $single_time" | bc)

echo "Single-threaded time: ${single_time}s"
echo "Single-threaded QPS: ${single_qps}"
echo "Results saved to: $OUTPUT_DIR/single_results.txt"

echo "Benchmark completed at $(date)"
```

## Common Pitfalls to Avoid

### 1. Do Not Use Multi-threading for Queries

```bash
# ❌ AVOID: Multi-threaded query processing
rustkmer queryx database.rkdb --file queries.txt --threads 8

# ✅ INSTEAD: Use single-threaded processing
rustkmer query database.rkdb --file queries.txt
```

### 2. Do Not Preload Large Databases Unnecessarily

```bash
# ❌ AVOID: Preloading very large databases
rustkmer query huge_database.rkdb --file queries.txt --load  # May exceed RAM

# ✅ INSTEAD: Use memory mapping for large databases
rustkmer query huge_database.rkdb --file queries.txt --no-load
```

### 3. Do Not Ignore Database Sorting

```bash
# ❌ AVOID: Using unsorted databases (poor performance)
rustkmer count --input genome.fa --output unsorted.rkdb

# ✅ INSTEAD: Always create sorted databases
rustkmer count --input genome.fa --output sorted.rkdb --sort
```

## Troubleshooting Guide

### Performance Issues

1. **Slow Query Performance**
   - Verify database is sorted: `rustkmer info database.rkdb`
   - Check available memory: `free -h` or `htop`
   - Use memory mapping for large databases: `--no-load`

2. **Memory Issues**
   - Reduce batch size for large query sets
   - Use `--no-load` for databases larger than available RAM
   - Monitor memory usage: `/usr/bin/time -l rustkmer query ...`

3. **File I/O Issues**
   - Ensure database files are on fast storage (SSD preferred)
   - Check file permissions and disk space
   - Use absolute paths for database files

## Conclusion

By following these recommendations, you can achieve optimal performance for RustKmer k-mer query operations:

1. **Always use single-threaded mode** (`rustkmer query`)
2. **Create sorted databases** for optimal performance
3. **Use appropriate memory management** based on database size
4. **Process large query sets in reasonable batches**
5. **Monitor resource usage** to identify bottlenecks

These practices are based on comprehensive performance analysis and provide the best performance for both 13-mer and 21-mer k-mer queries.

## References

- Full performance analysis: `specs/003-parallel-query/21MER_PERFORMANCE_ANALYSIS.md`
- Test data and results: `/Users/forrest/Temp/demodata/test_runs/osa1_21mer_performance_test/`
- Original research question: "如果是 21mer 呢？ 多线程和单线程比如果性能没有明显提升也请明确的告诉我"