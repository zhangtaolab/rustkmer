# Quickstart Guide: u128 K-mer Support

This guide demonstrates how to use rustkmer with u128 encoding to process k-mers up to size 64.

## Installation

```bash
# Build the latest version with u128 support
cargo build --release

# Python bindings (optional)
cargo build --release --features python
```

## CLI Usage

### Creating a Database with Large K-mers

```bash
# Create a database with k=48
./target/release/rustkmer count --kmer-size 48 --output virus_k48.rkdb virus_genome.fasta

# Create a database with maximum k=64
./target/release/rustkmer count -k 64 -o human_k64.rkdb human_genome.fa
```

### Querying Large K-mers

```bash
# Query a specific 48-mer
./target/release/rustkmer query --database virus_k48.rkdb ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT

# Batch query from file
./target/release/rustkmer query -d virus_k48.rkdb --batch queries.txt
```

### Database Statistics

```bash
# Get statistics including skipped ambiguous k-mers
./target/release/rustkmer stats --database virus_k48.rkdb

# Output in JSON format
./target/release/rustkmer stats -d human_k64.rkdb --format json
```

### Memory Management

```bash
# Set memory limit for large operations
./target/release/rustkmer count -k 64 -o large.rkdb huge_genome.fa --memory-limit 8GB

# Control concurrency
./target/release/rustkmer query -d db.rkdb --max-concurrent 20 queries.txt
```

## Python API Usage

```python
from rustkmer import SimpleKmerCounter, SimpleDatabase

# Create a database with k=48
counter = SimpleKmerCounter(kmer_size=48)
counter.process_fasta("large_genome.fasta")
counter.save("large_k48.rkdb")

# Load and query a database
db = SimpleDatabase("large_k48.rkdb")
count = db.query("ACGT" * 12)  # 48-mer
print(f"K-mer count: {count}")

# Batch query
queries = ["ACGT" * 12, "GCTA" * 12, "TTTT" * 12]
results = db.query_batch(queries)
for query, count in zip(queries, results):
    print(f"{query}: {count}")

# Get statistics
stats = db.get_stats()
print(f"Total k-mers: {stats.total_kmers}")
print(f"Unique k-mers: {stats.unique_kmers}")
```

## Working with Edge Cases

### Handling Ambiguous Bases

```bash
# Count statistics (automatically skips k-mers with N)
./target/release/rustkmer count -k 64 -o test.rkdb test.fa --verbose

# Output will include:
# INFO: Skipped 1,234 k-mers containing ambiguous bases
```

### Maximum K-mer Size

```bash
# Use the maximum supported k-mer size
./target/release/rustkmer count -k 64 -o max_k.rkdb sequence.fa

# Error for invalid k-mer sizes
./target/release/rustkmer count -k 65 -o error.rkdb seq.fa
# ERROR: Invalid k-mer size: 65 (must be 1-64)
```

## Performance Tips

### Large Datasets

```bash
# Process in chunks for very large files
split -l 1000000 huge_genome.fa chunk_
for f in chunk_*; do
    ./target/release/rustkmer count -k 64 -o "${f}.rkdb" "$f"
done

# Use memory limits to prevent OOM
./target/release/rustkmer count -k 64 -o final.rkdb huge_genome.fa \
    --memory-limit 16GB --chunk-size 1000000
```

### Query Optimization

```bash
# Batch queries are more efficient than individual queries
./target/release/rustkmer query -d db.rkdb --batch large_query_set.txt

# Use JSON output for machine processing
./target/release/rustkmer query -d db.rkdb --batch queries.txt --format json > results.json
```

## Testing Your Implementation

### Unit Tests

```bash
# Run all tests
cargo test

# Run tests for specific module
cargo test kmer::encoding

# Run tests with large k-mers
cargo test -- --include-ignored
```

### Benchmarks

```bash
# Benchmark encoding performance
cargo bench encoding_bench

# Benchmark query performance
cargo bench query_bench

# Compare u64 vs u128 performance
cargo bench compare_encodings
```

## Common Pitfalls

### Memory Usage

Remember that u128 databases are 33% larger:
- u64 format: 12 bytes per entry
- u128 format: 16 bytes per entry

```bash
# Check database size before querying
ls -lh large_k64.rkdb
# -rw-r--r-- 1 user user 48G large_k64.rkdb

# Adjust memory limits accordingly
./target/release/rustkmer query -d large_k64.rkdb --memory-limit 24GB queries.txt
```

### Canonical K-mers

The database stores canonical k-mers (lexicographically smaller of forward and reverse complement):

```python
# Both queries return the same count
db = SimpleDatabase("example.rkdb")
count1 = db.query("ACGTACGTACGT" * 4)      # Forward
count2 = db.query("ACGT" * 4 + "TACG" * 3)  # Reverse complement
assert count1 == count2
```

## Getting Help

```bash
# General help
./target/release/rustkmer --help

# Command-specific help
./target/release/rustkmer count --help
./target/release/rustkmer query --help

# Check version
./target/release/rustkmer --version
# rustkmer 2.0.0 (u128 support)
```

## Migration from u64

Since this version doesn't support backward compatibility:

1. Re-create all databases with the new format
2. Verify k-mer sizes (now supports up to 64)
3. Update any scripts using k>32
4. Test with your actual data to ensure consistency

```bash
# Example migration script
#!/bin/bash
for f in *.fasta; do
    echo "Processing $f with k=48..."
    ./target/release/rustkmer count -k 48 -o "${f%.fasta}_k48.rkdb" "$f"
done
```