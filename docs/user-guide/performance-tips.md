# Performance Tips

Optimize RustKmer for maximum speed and efficiency with these performance tuning strategies.

## Overview

RustKmer is designed for high-performance k-mer analysis, but optimal performance requires proper configuration and understanding of the underlying algorithms. This guide covers performance optimization techniques for different use cases.

## Quick Performance Checklist

### Essential Settings for Maximum Speed
- **Use appropriate k-mer size** (13-31 for most applications)
- **Enable canonical k-mers** for genome analysis
- **Use sorted databases** for faster querying
- **Optimize thread count** for your system
- **Choose appropriate file formats** (compressed for storage, uncompressed for speed)

## Memory Optimization

### K-mer Size Selection
```bash
# Smaller k-mers = less memory, faster processing
rustkmer count -k 13 -i input.fa -o output.rkdb

# Larger k-mers = more specificity, more memory
rustkmer count -k 31 -i input.fa -o output.rkdb
```

**Memory Usage Guidelines:**
- **k=13**: ~1GB per 1M k-mers
- **k=21**: ~4GB per 1M k-mers
- **k=31**: ~8GB per 1M k-mers

### Database Format Options
```bash
# Uncompressed (faster loading, more disk space)
rustkmer count -i input.fa -o output.rkdb

# Compressed (slower loading, less disk space)
rustkmer count -i input.fa -o output.rkdb --compress
```

## Speed Optimization

### Thread Configuration
```bash
# Auto-detect optimal threads (recommended)
rustkmer count -i input.fa -o output.rkdb

# Manual thread specification
rustkmer count -i input.fa -o output.rkdb --threads 8

# Disable threading for small files
rustkmer count -i input.fa -o output.rkdb --threads 1
```

### Canonical vs Non-Canonical
```bash
# Canonical k-mers (slower counting, smaller database)
rustkmer count -i input.fa --canonical -o output.rkdb

# Non-canonical k-mers (faster counting, larger database)
rustkmer count -i input.fa -o output.rkdb
```

### Database Sorting
```bash
# Create sorted database for faster querying
rustkmer count -i input.fa -o output.rkdb --sorted

# Query performance comparison
# Unsorted: ~50,000 queries/second
# Sorted: ~200,000 queries/second
```

## Large Dataset Handling

### Batch Processing
```python
import os
from rustkmer import KmerCounter

def process_large_dataset(input_files, k=21, batch_size=1000000):
    """Process large genomic datasets in batches."""

    for i, file in enumerate(input_files):
        print(f"Processing file {i+1}/{len(input_files)}: {file}")

        # Create counter with memory-efficient settings
        counter = KmerCounter(k=k, canonical=True)

        # Process in chunks if very large
        if os.path.getsize(file) > 1_000_000_000:  # 1GB
            counter.count_file(file, chunk_size=1000000)
        else:
            counter.count_file(file)

        # Save intermediate results
        output_file = f"batch_{i+1:03d}.rkdb"
        counter.save_to_database(output_file)

        print(f"Saved: {output_file}")
```

### Streaming Processing
```python
from rustkmer import KmerCounter

def stream_process_fasta(fasta_file, k=21):
    """Stream large FASTA files without loading entirely into memory."""

    counter = KmerCounter(k=k, canonical=True)

    # Process file in streaming mode
    with open(fasta_file, 'r') as f:
        counter.count_stream(f)

    return counter
```

## Query Performance

### Database Indexing
```bash
# Create indexed database for fast queries
rustkmer count -i input.fa -o output.rkdb --indexed

# Query performance comparison
# Non-indexed: ~10,000 queries/second
# Indexed: ~500,000 queries/second
```

### Batch Querying
```python
from rustkmer import Database
import time

def batch_query_examples():
    """Optimize querying with batch operations."""

    queries = [
        "ATCGATCGATCGATCGATCG",
        "GCTAGCTAGCTAGCTAGCTAG",
        # ... thousands more queries
    ]

    with Database() as db:
        db.load("large_database.rkdb")

        # Batch query (much faster)
        start_time = time.time()
        results = db.query_batch(queries)
        batch_time = time.time() - start_time

        print(f"Batch query: {len(queries)} queries in {batch_time:.2f}s")
        print(f"Rate: {len(queries)/batch_time:.0f} queries/second")
```

### Fuzzy Query Optimization
```python
from rustkmer import Database

def optimize_fuzzy_queries():
    """Optimize fuzzy search parameters for speed vs accuracy."""

    with Database() as db:
        db.load("database.rkdb")

        # Fast fuzzy search (less accurate)
        results = db.fuzzy_query(
            pattern="ATCGATCGATCGATCGATCG",
            max_distance=2,
            max_results=100
        )

        # Comprehensive fuzzy search (slower, more accurate)
        results = db.fuzzy_query(
            pattern="ATCGATCGATCGATCGATCG",
            max_distance=3,
            max_results=1000,
            exhaustive=True
        )
```

## System-Level Optimization

### CPU Optimization
```bash
# Check CPU cores for optimal threading
nproc  # Linux/macOS
sysctl -n hw.ncpu  # macOS

# Set threads based on CPU cores
THREADS=$(nproc)
rustkmer count -i input.fa -o output.rkdb --threads $THREADS
```

### Disk I/O Optimization
```bash
# Use fast storage for temporary files
export TMPDIR="/fast/ssd/temp"
rustkmer count -i input.fa -o output.rkdb

# Prefer uncompressed files on fast storage
rustkmer count -i input.fa -o /fast/storage/output.rkdb
```

### Memory Mapping
```python
from rustkmer import Database

def use_memory_mapping():
    """Enable memory mapping for large databases."""

    with Database() as db:
        # Use memory-mapped access for large files
        db.load("large_database.rkdb", memory_mapped=True)

        # Queries will be much faster for repeated access
        result = db.query("ATCGATCGATCGATCGATCG")
```

## Benchmarking Your System

### Performance Test Script
```python
import time
import psutil
from rustkmer import KmerCounter, Database

def benchmark_system():
    """Benchmark RustKmer performance on your system."""

    print("🚀 RustKmer Performance Benchmark")
    print("=" * 40)

    # System info
    print(f"CPU Cores: {psutil.cpu_count()}")
    print(f"Memory: {psutil.virtual_memory().total / (1024**3):.1f} GB")

    # Test k-mer counting performance
    test_file = "test_data.fa"
    k_sizes = [13, 21, 31]

    for k in k_sizes:
        print(f"\n🧬 Testing k={k}")

        start_time = time.time()
        counter = KmerCounter(k=k, canonical=True)
        counter.count_file(test_file)
        count_time = time.time() - start_time

        total_kmers = counter.get_total_count()
        unique_kmers = counter.get_unique_count()

        print(f"   Counting time: {count_time:.2f}s")
        print(f"   Processing rate: {total_kmers/count_time:.0f} k-mers/sec")
        print(f"   Memory usage: {psutil.Process().memory_info().rss / (1024**2):.1f} MB")
        print(f"   Total k-mers: {total_kmers:,}")
        print(f"   Unique k-mers: {unique_kmers:,}")

    # Test querying performance
    print(f"\n🔍 Testing query performance")

    db_file = "test_database.rkdb"
    queries = ["ATCGATCGATCGATCGATCG"] * 10000  # 10k queries

    with Database() as db:
        db.load(db_file)

        start_time = time.time()
        for query in queries:
            db.query(query)
        query_time = time.time() - start_time

        print(f"   Query time: {query_time:.2f}s")
        print(f"   Query rate: {len(queries)/query_time:.0f} queries/sec")

if __name__ == "__main__":
    benchmark_system()
```

## Performance Comparison Tables

### K-mer Counting Performance
| K-mer Size | Memory Usage | Speed (k-mers/sec) | Database Size |
|------------|--------------|-------------------|---------------|
| k=13 | Low | ~50,000 | Small |
| k=21 | Medium | ~30,000 | Medium |
| k=31 | High | ~15,000 | Large |

### Querying Performance
| Database Type | Load Time | Query Speed | Memory Usage |
|---------------|-----------|-------------|--------------|
| Unsorted | Fast | ~50,000 q/s | Low |
| Sorted | Medium | ~200,000 q/s | Medium |
| Indexed | Slow | ~500,000 q/s | High |

### File Format Performance
| Format | Counting Speed | Storage Size | Loading Speed |
|--------|----------------|--------------|---------------|
| FASTA (uncompressed) | Fastest | Large | Fastest |
| FASTA (gzip) | Medium | Small | Medium |
| FASTQ (uncompressed) | Fast | Large | Fast |
| FASTQ (gzip) | Slow | Small | Slow |

## Troubleshooting Performance Issues

### Slow Counting
**Problem**: K-mer counting is taking too long
**Solutions**:
- Reduce k-mer size (k=13 instead of k=31)
- Disable canonical k-mers if not needed
- Use more threads (check CPU cores)
- Use uncompressed input files
- Split large files into smaller chunks

### High Memory Usage
**Problem**: Running out of memory
**Solutions**:
- Use smaller k-mer size
- Enable database compression
- Process files in batches
- Use streaming mode for very large files
- Close databases when not in use

### Slow Querying
**Problem**: Database queries are slow
**Solutions**:
- Create sorted databases (`--sorted`)
- Use indexed databases for frequent queries
- Batch multiple queries together
- Enable memory mapping for large databases
- Consider using a smaller k-mer size

### Database Loading Issues
**Problem**: Databases take too long to load
**Solutions**:
- Use uncompressed databases on fast storage
- Enable memory mapping
- Load databases once and reuse
- Consider using multiple smaller databases

## Best Practices

### For High-Performance Computing
1. **Use SSD storage** for database files
2. **Allocate sufficient RAM** (2x database size for optimal performance)
3. **Use thread count equal to CPU cores**
4. **Prefer sorted databases** for frequent querying
5. **Batch operations** when possible

### For Production Systems
1. **Monitor memory usage** and implement limits
2. **Use database compression** to save disk space
3. **Implement proper error handling** and retry logic
4. **Use connection pooling** for multi-user systems
5. **Regular performance monitoring** and optimization

### For Development/Testing
1. **Start with small datasets** to test workflows
2. **Use canonical k-mers** for consistency
3. **Implement proper logging** for performance analysis
4. **Test different k-mer sizes** for your use case
5. **Benchmark on target hardware** before deployment

---

## Need More Help?

- **[API Reference](../api-reference/)** - Complete function documentation
- **[Troubleshooting](../getting-started/troubleshooting.md)** - Common issues and solutions
- **[GitHub Issues](https://github.com/rustkmer/rustkmer/issues)** - Report performance problems
- **[Discussions](https://github.com/rustkmer/rustkmer/discussions)** - Performance optimization tips