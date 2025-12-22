# Handling Large Datasets

When working with large genomic datasets (millions of k-mers), proper optimization becomes crucial for performance and memory efficiency.

## Memory Management Strategies

### 1. Use Memory-Mapped Access

For very large databases, use memory-mapped access instead of preloading:

```python
import rustkmer_pyo3

# Use memory mapping for large databases
engine = rustkmer_pyo3.PyDatabase(
    "large_genome.rkdb", 
    rustkmer_pyo3.LoadMode.MemoryMapped
)
```

### 2. Batch Processing

Process large datasets in smaller chunks:

```python
def process_large_dataset(database_path, batch_size=10000):
    engine = rustkmer_pyo3.PyDatabase(database_path, rustkmer_pyo3.LoadMode.MemoryMapped)
    
    # Get all k-mers in batches
    all_kmers = engine.get_all_kmers()
    
    for i in range(0, len(all_kmers), batch_size):
        batch = all_kmers[i:i+batch_size]
        process_batch(batch)
        
def process_batch(batch):
    # Process each batch
    for kmer, count in batch.items():
        # Your processing logic here
        pass
```

## Performance Optimization

### 1. Use Appropriate K-mer Sizes

Larger k-mers reduce database size:

```bash
# For large datasets, consider k=31 or k=41
rustkmer count -k 31 --sort -i large_genome.fa -o genome_k31.rkdb
```

### 2. Enable Database Sorting

Always use sorted databases for better query performance:

```bash
rustkmer count -k 21 --sort -i genome.fa -o sorted_genome.rkdb
```

## Best Practices

1. **Monitor Memory Usage**: Use `engine.get_memory_usage()` to track memory consumption
2. **Use Streaming**: For very large files, consider streaming processing
3. **Parallel Processing**: Use multiple threads for I/O-bound operations
4. **Database Compression**: Consider database compression for storage efficiency

## Example: Large Genome Analysis

```python
import rustkmer_pyo3

# Load large genome database
engine = rustkmer_pyo3.PyDatabase("human_genome_k31.rkdb", rustkmer_pyo3.LoadMode.MemoryMapped)

# Get statistics
stats = engine.get_stats()
print(f"Total k-mers: {stats.total_kmers:,}")
print(f"Unique k-mers: {stats.unique_kmers:,}")

# Efficient prefix queries（推荐使用新命名）
prefix_results = engine.query_exact_batch(["ATG", "GTG", "CTG"])  # Start codons

# 兼容性说明：旧方法名仍然可用但已废弃
# prefix_results = engine.query_batch(["ATG", "GTG", "CTG"])  # 已废弃，请使用 query_exact_batch()
```

This approach ensures efficient processing of large genomic datasets while maintaining optimal memory usage.


