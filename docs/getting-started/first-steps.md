# First Steps

Welcome to your first k-mer counting experience with RustKmer! This guide will walk you through basic operations and help you understand the fundamentals.

## What You'll Learn

- Count k-mers from genomic data
- Query k-mer databases
- Understand basic k-mer concepts
- Perform your first fuzzy search

## Prerequisites

- RustKmer installed ([Installation Guide](installation.md))
- A sample FASTA file (or create one using the examples below)

## Understanding k-mers

A **k-mer** is a sequence of length *k* from a DNA or RNA string. For example, in the sequence `ATCGATCG`, the 3-mers are:

```
ATC, TCG, CGA, GAT, ATC, TCG
```

**Canonical k-mers** represent each k-mer and its reverse complement as the lexicographically smaller one. This reduces memory usage and simplifies matching.

---

## Example 1: Counting k-mers from a File

### Create Sample Data

Create a sample FASTA file named `sample.fa`:

```bash
cat > sample.fa << 'EOF'
>sample_sequence_1
ATCGATCGATCGATCGATCGATCGATCGATCGATCG
ATCGATCGATCGATCGATCGATCGATCGATCGATCG
>sample_sequence_2
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
EOF
```

### Python Implementation

```python
from pyrustkmer import PyCounter

# Create a k-mer counter
print("🧬 Creating k-mer counter...")
counter = PyCounter(21, canonical=True)
print(f"   K-mer size: {counter.k}")
print(f"   Canonical mode: {counter.canonical}")

# Count k-mers from file
print("📊 Counting k-mers from file...")
counter.add_from_fasta("sample.fa")

# Get results
total_kmers = counter.get_stats().total_kmers
unique_kmers = counter.get_unique_count()

print(f"✅ Counting complete!")
print(f"   Total k-mers processed: {total_kmers:,}")
print(f"   Unique k-mers found: {unique_kmers:,}")
print(f"   Uniqueness ratio: {unique_kmers/total_kmers:.4f}")
```

### Command Line Implementation

```bash
# Count k-mers using the CLI
echo "🧬 Counting k-mers with RustKmer CLI..."
rustkmer count -k 21 -i sample.fa -o sample_k21.rkdb --verbose

# The --verbose flag shows progress and statistics
```

**Expected Output:**
```
🧬 Counting k-mers with RustKmer CLI...
Processing file: sample.fa
  K-mer size: 21
  Canonical mode: true
  Total k-mers processed: 116
  Unique k-mmers found: 58
  Uniqueness ratio: 0.5000
✅ Database saved to: sample_k21.rkdb
```

---

## Example 2: Querying k-mer Databases

Now let's query the database we created:

### Python Querying

```python
from pyrustkmer import PyDatabase, LoadMode

# Load the database
print("🔍 Loading k-mer database...")
db = PyDatabase("sample_k21.rkdb", LoadMode.Preload)

# Query specific k-mers
test_kmers = [
    "ATCGATCGATCGATCGATCGATCG",
    "GCTAGCTAGCTAGCTAGCTAGCTA",
    "CCCCCCCCCCCCCCCCCCCCCCCC"  # This won't exist
]

print("🔎 Querying k-mers...")
for kmer in test_kmers:
    result = db.query_exact(kmer)
    if result.found:  # Use .found instead of .exists
        print(f"   ✅ Found {result.kmer}: {result.count:,} occurrences")
    else:
        print(f"   ❌ {result.kmer}: not found")

# Get database statistics
stats = db.get_stats()
print(f"\n📊 Database Statistics:")
print(f"   K-mer size: {stats.kmer_size}")
print(f"   Total k-mers: {stats.total_kmers:,}")
print(f"   Unique k-mers: {stats.unique_kmers:,}")

```

### Command Line Querying

```bash
# Query individual k-mers
echo "🔍 Querying k-mers with RustKmer CLI..."

# Exact match query
echo "ATCGATCGATCGATCGATCGATCG" | rustkmer query -d sample_k21.rkdb --file -

# Batch query from file
cat > queries.txt << EOF
ATCGATCGATCGATCGATCGATCG
GCTAGCTAGCTAGCTAGCTAGCTA
TTTTTTTTTTTTTTTTTTTTT
EOF

rustkmer query -d sample_k21.rkdb -f queries.txt
```

---

## Example 3: Fuzzy Searching

RustKmer supports pattern matching with wildcards and distance-based searches.

### Wildcard Querying (N = any base)

**Note:** Fuzzy query functionality is planned but not yet implemented in the current version.
The examples below show the intended interface for future development.

```python
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

# Load database
db = PyDatabase("sample_k21.rkdb", LoadMode.Preload)

# Try some wildcard patterns using PyFuzzyQuery
patterns = [
    "ATCGATCGATCGATCGATCGATC",  # Original k-mer
]

print("🔍 Fuzzy searching with wildcards...")
fuzzy = PyFuzzyQuery(db)
for pattern in patterns:
    results = fuzzy.query_fuzzy(pattern, max_distance=1)
    print(f"   Pattern '{pattern}': found {len(results)} matches within distance 1")

```

### Hamming Distance Search

**Note:** Distance-based fuzzy searching is planned for a future version.

```python
from pyrustkmer import PyDatabase, LoadMode, PyFuzzyQuery

# Load database
db = PyDatabase("sample_k21.rkdb", LoadMode.Preload)

# Original k-mer with some distance tolerance
original = "ATCGATCGATCGATCGATCGATCG"

print("🎯 Distance-based fuzzy searching...")
fuzzy = PyFuzzyQuery(db)
results = fuzzy.query_fuzzy(original, max_distance=2)
print(f"   Found {len(results)} k-mers within distance 2 of '{original}'")

```

---

## Example 4: Working with Real Data

### Processing Large Files

```python
from pyrustkmer import KmerCounter

# For larger files, consider these optimizations:

# 1. Use appropriate k-mer size (smaller = faster, larger = more specific)
print("🧬 Optimizing for large file processing...")
counter = PyCounter(13, canonical=True)  # Smaller k for speed

# 2. Process in chunks if needed
counter.add_from_fasta("large_genome.fa.gz")  # Handles gzip automatically

print("📊 Large file results:")
print(f"   Total k-mers: {counter.get_stats().total_kmers):,}")
print(f"   Unique k-mmers: {counter.get_unique_count():,}")

# 3. Save intermediate results
counter.save_database("large_genome_k13.rkdb")
print("💾 Database saved: large_genome_k13.rkdb")
```

### Batch Processing Multiple Files

```python
from pyrustkmer import KmerCounter
import glob

def process_multiple_files(file_pattern, k=21):
    """Process multiple files and combine results."""

    counter = PyCounter(k, canonical=True)
    files = glob.glob(file_pattern)

    print(f"📁 Processing {len(files)} files matching '{file_pattern}'")

    for i, file_path in enumerate(files, 1):
        filename = file_path.split('/')[-1]
        print(f"   [{i}/{len(files)}] Processing {filename}...")

        try:
            counter.add_from_fasta(file_path)
            print(f"      Current total: {counter.get_stats().total_kmers):,}")
        except Exception as e:
            print(f"      ⚠️  Error processing {filename}: {e}")

    return counter

# Example usage
# counter = process_multiple_files("chromosome_*.fa.gz")
```

---

## Quick Reference Cheat Sheet

### Python API
```python
from pyrustkmer import PyCounter, PyDatabase, LoadMode, PyFuzzyQuery

# Counting
counter = PyCounter(21, canonical=True)
counter.add_from_fasta("data.fa.gz")
total = counter.get_stats().total_kmers
unique = counter.get_unique_count()
top_kmers = counter.get_top_kmers(10)
counter.save_database("data.rkdb")

# Querying
db = PyDatabase("data.rkdb", LoadMode.Preload)
result = db.query_exact("ATCGATCGATCGATCGATCGATCG")

# Fuzzy querying
fuzzy = PyFuzzyQuery(db)
fuzzy_results = fuzzy.query_fuzzy("ATCGATCGATCGATCGATCGATC", max_distance=1)

stats = db.get_stats()
```

### Command Line Interface
```bash
# Counting
rustkmer count -k 21 -i data.fa -o data.rkdb --canonical

# Querying
rustkmer query -d data.rkdb -q "ATCGATCG" -f queries.txt

# Fuzzy querying
rustkmer fuzzy-query -d data.rkdb -p "ATN" -m 1

# Getting help
rustkmer --help
rustkmer count --help
```

---

## Performance Tips

### Choosing k-mer Size

| k-mer Size | Memory Usage | Specificity | Use Case |
|------------|--------------|------------|---------|
| k=13 | Low | Low | Fast processing, large datasets |
| k=21 | Medium | Medium | **Recommended default** |
| k=31 | High | High | Precise analysis, research |

### Memory Optimization

```python
# For memory-constrained environments
counter = PyCounter(13)  # Smaller k = less memory

# For query-heavy workloads
db = PyDatabase("database.rkdb", LoadMode.MemoryMapped)  # Memory-mapped (default)
# db = PyDatabase("database.rkdb", LoadMode.Preload)  # Preload for speed
```

## Next Steps

Congratulations! You've completed your first k-mer counting operations with RustKmer. You're now ready to:

1. **Explore the [User Guide](../user-guide/)** for advanced techniques
2. **Try the [Tutorials](../tutorials/)** for practical workflows
3. **Learn about [Performance Optimization](../user-guide/performance-tips.md)**
4. **Check out the [API Reference](../api-reference/)** for complete documentation

---

## Need Help?

### 📚 Documentation
- **[User Guide](../user-guide/)** - Comprehensive usage instructions
- **[API Reference](../api-reference/)** - Complete function documentation
- **[Performance Tips](../user-guide/performance-tips.md)** - Optimization strategies

### 🔧 Troubleshooting
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and solutions
- **[Installation Help](installation.md)** - Installation problems

### 💬 Community Support
- **[GitHub Issues](https://github.com/rustkmer/rustkmer/issues)** - Bug reports and feature requests
- **[GitHub Discussions](https://github.com/rustkmer/rustkmer/discussions)** - Questions and discussions

---

## 📖 Continue Your Journey

Now that you've mastered the basics, explore these topics:

### 🎯 Next Steps
1. **[Basic Workflow Tutorial](../tutorials/basic-workflow.md)** - Complete end-to-end project
2. **[Performance Optimization](../user-guide/performance-tips.md)** - Speed up your analysis
3. **[Advanced Counting](../user-guide/counting-kmers.md)** - Advanced k-mer counting techniques

### 🧬 Advanced Topics
- **[Database Querying](../user-guide/querying.md)** - Master database operations
- **[Large Genome Analysis](../tutorials/large-genomes.md)** - Handle massive datasets
- **[Integration Guide](../tutorials/integration.md)** - Connect to existing workflows

Happy k-mer counting! 🧬✨