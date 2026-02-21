# Counting K-mers

Complete guide to k-mer counting operations with RustKmer, from basic usage to advanced optimization strategies.

## Table of Contents

- [Understanding K-mer Counting](#understanding-k-mer-counting)
- [Basic Counting Operations](#basic-counting-operations)
- [Advanced Counting Features](#advanced-counting-features)
- [Performance Optimization](#performance-optimization)
- [Memory Management](#memory-management)
- [Batch Processing](#batch-processing)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)

## Understanding K-mer Counting

### What are K-mers?

A **k-mer** is a subsequence of length *k* from a longer DNA/RNA sequence. For a sequence `ATCGATCG`, the 3-mers (k=3) are:

```
ATC, TCG, CGA, GAT, ATC, TCG
```

### Canonical K-mers

**Canonical k-mers** represent each k-mer and its reverse complement as the lexicographically smaller one. This reduces memory usage by half and ensures consistent counting regardless of DNA strand orientation.

```python
# Example: ATCG and its reverse complement CGAT
# Canonical representation is ATCG (lexicographically smaller)

# Non-canonical counting: "ATCG" and "CGAT" counted separately
# Canonical counting: both counted as "ATCG"
```

### Why K-mer Counting Matters

- **Genome Assembly**: Identify overlapping sequences
- **Metagenomics**: Classify organisms in environmental samples
- **Variant Detection**: Find genetic variations
- **Phylogenetics**: Compare genetic relationships
- **Gene Finding**: Identify coding regions

---

## Basic Counting Operations

### Counting from Files

#### FASTA Files

```python
from pyrustkmer import KmerCounter

# Create counter for 21-mers (recommended for most applications)
counter = PyCounter(21, canonical=True)

# Count k-mers from FASTA file
counter.add_from_fasta("genome.fa.gz")  # Handles gzip automatically

# Get results
total = counter.get_stats().total_kmers)
unique = counter.get_unique_count()

print(f"Total k-mers: {total:,}")
print(f"Unique k-mers: {unique:,}")
print(f"Uniqueness ratio: {unique/total:.4f}")
```

#### FASTQ Files

```python
# FASTQ files work the same way
counter.add_from_fasta("reads.fq.gz")

# Get basic statistics
print(f"Processed {counter.get_stats().total_kmers):,} k-mers")
print(f"Found {counter.get_unique_count():,} unique k-mers")
```

### Counting from Strings

```python
# Count k-mers from a sequence string
sequence = "ATCGATCGATCGATCGATCGATCGATCGATCG"
counter.add_sequence(sequence)

print(f"Counted {counter.get_stats().total_kmers)} k-mers from string")
```

### Getting Results

```python
# Get basic statistics
total_count = counter.get_stats().total_kmers)
unique_count = counter.get_unique_count()
top_kmers = counter.get_top_kmers(10)  # Top 10 most frequent

print("📊 K-mer Counting Results:")
print(f"Total k-mers: {total_count:,}")
print(f"Unique k-mers: {unique_count:,}")

print("\n🔝 Top 10 Most Frequent K-mers:")
for i, (kmer, count) in enumerate(top_kmers, 1):
    print(f"  {i:2d}. {kmer}: {count:,}")
```

---

## Advanced Counting Features

### Choosing K-mer Size

The choice of k-mer size balances specificity and performance:

| k-mer Size | Best For | Memory Usage | Specificity |
|------------|----------|--------------|------------|
| k=13 | Quick analysis, large datasets | Low | Low |
| k=21 | **General purpose**, metagenomics | Medium | **Medium** |
| k=31 | Precise analysis, research | High | High |
| k=51 | Very specific applications | Very High | Very High |

```python
# Example: Different k-mer sizes for different purposes

# Quick screening (smaller k = faster)
screen_counter = PyCounter(13, canonical=True)

# Standard analysis (recommended default)
standard_counter = PyCounter(21, canonical=True)

# High-specificity research (larger k = more specific)
research_counter = PyCounter(31, canonical=True)
```

### Canonical vs Non-canonical Counting

```python
# Canonical counting (recommended for most applications)
canonical_counter = PyCounter(21, canonical=True)
canonical_counter.add_from_fasta("genome.fa.gz")

# Non-canonical counting (when strand matters)
noncanonical_counter = PyCounter(21, canonical=False)
noncanonical_counter.add_from_fasta("genome.fa.gz")

# Compare results
print(f"Canonical unique k-mers: {canonical_counter.get_unique_count():,}")
print(f"Non-canonical unique k-mers: {noncanonical_counter.get_unique_count():,}")
# Non-canonical will typically have ~2x more unique k-mers
```

### Working with Multiple Files

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
chromosomes = process_multiple_files("chr*.fa.gz")
print(f"\nFinal results:")
print(f"Total k-mers: {chromosomes.get_total_count():,}")
print(f"Unique k-mers: {chromosomes.get_unique_count():,}")
```

---

## Performance Optimization

### Memory Optimization

```python
# For memory-constrained environments
import psutil
import os

def monitor_memory():
    """Monitor current memory usage."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB

print(f"Memory before processing: {monitor_memory():.1f} MB")

# Use smaller k-mer size for memory efficiency
counter = PyCounter(13, canonical=True)
counter.add_from_fasta("large_genome.fa.gz")

print(f"Memory after processing: {monitor_memory():.1f} MB")
print(f"Memory efficiency: {counter.get_stats().total_kmers)/(monitor_memory()*1024*1024):.1f} k-mers per MB")
```

### Processing Large Files

```python
# For very large files, consider these strategies:

# 1. Use appropriate k-mer size
counter = PyCounter(13, canonical=True)  # Smaller k = less memory

# 2. Process compressed files directly
counter.add_from_fasta("huge_genome.fa.gz")  # Handles streaming decompression

# 3. Save intermediate results
counter.save_database("intermediate.rkdb")
print("💾 Intermediate results saved")

# 4. Process in chunks if memory is extremely limited
# (This requires manual implementation for very specific use cases)
```

### Batch Optimization

```python
import time
from concurrent.futures import ThreadPoolExecutor
import os

def optimal_batch_size(file_size_mb):
    """Determine optimal batch size based on file size."""
    if file_size_mb < 100:
        return 1
    elif file_size_mb < 1000:
        return 4
    else:
        return min(8, os.cpu_count())

def benchmark_batch_processing(files, batch_sizes=[1, 2, 4, 8]):
    """Benchmark different batch sizes for optimal performance."""

    results = {}

    for batch_size in batch_sizes:
        start_time = time.time()

        # Process files in batches
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            for i in range(0, len(files), batch_size):
                batch = files[i:i+batch_size]
                futures = []

                for file_path in batch:
                    counter = PyCounter(21, canonical=True)
                    future = executor.submit(counter.count_file, file_path)
                    futures.append(future)

                # Wait for batch to complete
                for future in futures:
                    future.result()

        duration = time.time() - start_time
        results[batch_size] = duration
        print(f"Batch size {batch_size}: {duration:.2f} seconds")

    # Find optimal batch size
    optimal_batch = min(results.keys(), key=lambda x: results[x])
    print(f"\nOptimal batch size: {optimal_batch} ({results[optimal_batch]:.2f} seconds)")

    return optimal_batch
```

---

## Memory Management

### Understanding Memory Usage

```python
def analyze_memory_usage(counter):
    """Analyze memory usage patterns of k-mer counting."""

    total_kmers = counter.get_stats().total_kmers)
    unique_kmers = counter.get_unique_count()

    # Estimate memory usage
    # Each unique k-mer typically uses ~32 bytes (k-mer + count + overhead)
    estimated_memory_mb = unique_kmers * 32 / 1024 / 1024

    print(f"📊 Memory Analysis:")
    print(f"Total k-mers processed: {total_kmers:,}")
    print(f"Unique k-mers stored: {unique_kmers:,}")
    print(f"Uniqueness ratio: {unique_kmers/total_kmers:.4f}")
    print(f"Estimated memory usage: {estimated_memory_mb:.1f} MB")

    # Recommendations
    if estimated_memory_mb > 1000:
        print("⚠️  High memory usage detected. Consider:")
        print("   - Using smaller k-mer size")
        print("   - Processing in chunks")
        print("   - Using canonical counting")

    return estimated_memory_mb

# Usage
counter = PyCounter(21, canonical=True)
counter.add_from_fasta("genome.fa.gz")
analyze_memory_usage(counter)
```

### Memory-Efficient Processing

```python
def memory_efficient_counting(file_path, k=13, chunk_size=None):
    """Process files with memory efficiency in mind."""

    import psutil
    import os

    def get_memory_usage():
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024  # MB

    # Monitor memory before processing
    initial_memory = get_memory_usage()
    print(f"Initial memory: {initial_memory:.1f} MB")

    # Create counter with memory-efficient settings
    counter = PyCounter(k, canonical=True)

    try:
        # Process file
        counter.add_from_fasta(file_path)

        # Check memory after processing
        final_memory = get_memory_usage()
        memory_used = final_memory - initial_memory

        print(f"Final memory: {final_memory:.1f} MB")
        print(f"Memory used: {memory_used:.1f} MB")
        print(f"Memory efficiency: {counter.get_stats().total_kmers)/memory_used/1024:.1f} k-mers per MB")

        return counter

    except MemoryError:
        print("❌ Memory error detected. Try with smaller k-mer size.")
        # Fallback to smaller k-mer
        if k > 13:
            print("🔄 Retrying with k=13...")
            return memory_efficient_counting(file_path, k=13)
        raise
```

---

## Batch Processing

### Processing Multiple Files Efficiently

```python
from pyrustkmer import KmerCounter
import glob
import time
from pathlib import Path

class BatchProcessor:
    """Efficient batch processor for multiple genomic files."""

    def __init__(self, k=21, canonical=True):
        self.k = k
        self.canonical = canonical
        self.results = {}

    def process_directory(self, directory, pattern="*.fa.gz"):
        """Process all files matching pattern in directory."""

        file_pattern = f"{directory}/{pattern}"
        files = glob.glob(file_pattern)

        print(f"📁 Found {len(files)} files to process")

        for i, file_path in enumerate(files, 1):
            filename = Path(file_path).name
            print(f"\n[{i}/{len(files)}] Processing {filename}...")

            start_time = time.time()

            try:
                counter = PyCounter(self.k, canonical=self.canonical)
                counter.add_from_fasta(file_path)

                duration = time.time() - start_time

                # Store results
                self.results[filename] = {
                    'total_kmers': counter.get_stats().total_kmers),
                    'unique_kmers': counter.get_unique_count(),
                    'duration': duration,
                    'file_size': Path(file_path).stat().st_size,
                    'top_kmers': counter.get_top_kmers(5)
                }

                print(f"   ✅ Completed in {duration:.2f}s")
                print(f"   Total k-mers: {counter.get_stats().total_kmers):,}")
                print(f"   Unique k-mers: {counter.get_unique_count():,}")

            except Exception as e:
                print(f"   ❌ Error: {e}")
                self.results[filename] = {'error': str(e)}

    def generate_report(self, output_file="batch_report.csv"):
        """Generate a CSV report of batch processing results."""

        import csv

        with open(output_file, 'w', newline='') as csvfile:
            fieldnames = ['filename', 'total_kmers', 'unique_kmers', 'uniqueness_ratio',
                         'duration', 'file_size', 'kmer_rate']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for filename, result in self.results.items():
                if 'error' not in result:
                    writer.writerow({
                        'filename': filename,
                        'total_kmers': result['total_kmers'],
                        'unique_kmers': result['unique_kmers'],
                        'uniqueness_ratio': result['unique_kmers'] / result['total_kmers'],
                        'duration': result['duration'],
                        'file_size': result['file_size'],
                        'kmer_rate': result['total_kmers'] / result['duration']
                    })
                else:
                    writer.writerow({'filename': filename, 'error': result['error']})

        print(f"\n📊 Report saved to {output_file}")

    def get_summary(self):
        """Get summary statistics of batch processing."""

        successful = {k: v for k, v in self.results.items() if 'error' not in v}
        failed = {k: v for k, v in self.results.items() if 'error' in v}

        if successful:
            total_kmers = sum(r['total_kmers'] for r in successful.values())
            total_unique = sum(r['unique_kmers'] for r in successful.values())
            avg_duration = sum(r['duration'] for r in successful.values()) / len(successful)

            print(f"\n📈 Batch Processing Summary:")
            print(f"   Files processed: {len(successful)}")
            print(f"   Files failed: {len(failed)}")
            print(f"   Total k-mers: {total_kmers:,}")
            print(f"   Total unique k-mers: {total_unique:,}")
            print(f"   Average processing time: {avg_duration:.2f}s")

        else:
            print("❌ No files were processed successfully")

# Usage example
processor = BatchProcessor(k=21, canonical=True)
processor.process_directory("genomes/", "*.fa.gz")
processor.generate_report()
processor.get_summary()
```

---

## Error Handling

### Common Issues and Solutions

```python
from pyrustkmer import KmerCounter, KmerError
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def robust_counting(file_path, k=21, canonical=True):
    """Robust k-mer counting with comprehensive error handling."""

    try:
        # Validate input file
        if not file_path.endswith(('.fa', '.fasta', '.fa.gz', '.fasta.gz', '.fq', '.fastq', '.fq.gz', '.fastq.gz')):
            raise ValueError(f"Unsupported file format: {file_path}")

        # Check if file exists
        from pathlib import Path
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Create counter
        counter = PyCounter(k, canonical=canonical)
        logger.info(f"Created k-mer counter: k={k}, canonical={canonical}")

        # Process file
        logger.info(f"Processing file: {file_path}")
        counter.add_from_fasta(file_path)

        # Validate results
        total_count = counter.get_stats().total_kmers)
        unique_count = counter.get_unique_count()

        if total_count == 0:
            logger.warning("No k-mers were counted - possible empty or invalid file")

        logger.info(f"Processing complete: {total_count:,} total, {unique_count:,} unique")

        return counter

    except KmerError as e:
        logger.error(f"K-mer processing error: {e}")
        return None

    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return None

    except MemoryError:
        logger.error("Insufficient memory for processing")
        # Try with smaller k-mer size
        if k > 13:
            logger.info("Retrying with smaller k-mer size...")
            return robust_counting(file_path, k=13, canonical=canonical)
        raise

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None

# Usage with error handling
counter = robust_counting("genome.fa.gz")
if counter:
    print("✅ Processing successful!")
else:
    print("❌ Processing failed - check logs for details")
```

### Validation and Quality Control

```python
def validate_kmer_counting(counter, min_kmers=1000, max_uniqueness_ratio=0.1):
    """Validate k-mer counting results for quality control."""

    total = counter.get_stats().total_kmers)
    unique = counter.get_unique_count()
    uniqueness_ratio = unique / total if total > 0 else 0

    issues = []

    # Check minimum k-mer count
    if total < min_kmers:
        issues.append(f"Very low k-mer count: {total} (expected > {min_kmers})")

    # Check uniqueness ratio
    if uniqueness_ratio > max_uniqueness_ratio:
        issues.append(f"High uniqueness ratio: {uniqueness_ratio:.4f} (expected < {max_uniqueness_ratio})")

    # Check for zero counts
    if total == 0:
        issues.append("No k-mers were counted")

    # Report results
    if issues:
        print("⚠️  Quality control issues detected:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print("✅ Quality control checks passed")
        return True

# Usage
counter = robust_counting("genome.fa.gz")
if counter and validate_kmer_counting(counter):
    print("✅ Processing successful and validated!")
```

---

## Best Practices

### Recommended Workflow

```python
def recommended_workflow(file_path, output_db=None):
    """Recommended k-mer counting workflow for most applications."""

    print("🧬 Starting recommended k-mer counting workflow...")

    # Step 1: Setup with optimal parameters
    counter = PyCounter(21, canonical=True)  # Best balance of speed/specificity

    # Step 2: Process file with error handling
    if not robust_counting(file_path, k=21, canonical=True):
        return None

    # Step 3: Validate results
    if not validate_kmer_counting(counter):
        return None

    # Step 4: Get results
    total = counter.get_stats().total_kmers)
    unique = counter.get_unique_count()
    top_kmers = counter.get_top_kmers(10)

    # Step 5: Save database if requested
    if output_db:
        counter.save_database(output_db)
        print(f"💾 Database saved to {output_db}")

    # Step 6: Report results
    print(f"\n📊 Results Summary:")
    print(f"   Total k-mers: {total:,}")
    print(f"   Unique k-mers: {unique:,}")
    print(f"   Uniqueness ratio: {unique/total:.4f}")
    print(f"   Top k-mer: {top_kmers[0][0]} ({top_kmers[0][1]:,} occurrences)")

    return counter
```

### Performance Tips

1. **Choose the right k-mer size**:
   - k=21 for general use
   - k=13 for speed/memory
   - k=31+ for specificity

2. **Use canonical counting** unless strand information matters

3. **Process compressed files directly** - RustKmer handles decompression efficiently

4. **Save intermediate results** for large analyses

5. **Monitor memory usage** for very large datasets

6. **Use batch processing** for multiple files

### Common Pitfalls to Avoid

1. **Wrong k-mer size** - too small = not specific, too large = memory intensive
2. **File format errors** - ensure valid FASTA/FASTQ files
3. **Memory limits** - watch for memory errors with large datasets
4. **Ignoring quality control** - validate results before analysis
5. **Not using canonical counting** - doubles memory usage unnecessarily

---

## Quick Reference

### Python API
```python
from pyrustkmer import KmerCounter

# Create counter
counter = PyCounter(21, canonical=True)

# Count from file
counter.add_from_fasta("data.fa.gz")

# Get results
total = counter.get_stats().total_kmers)
unique = counter.get_unique_count()
top_kmers = counter.get_top_kmers(10)

# Save database
counter.save_database("output.rkdb")
```

### Command Line
```bash
# Count k-mers
rustkmer count -k 21 -i data.fa.gz -o output.rkdb --canonical

# With progress information
rustkmer count -k 21 -i data.fa.gz -o output.rkdb --verbose

# Multiple files
rustkmer count -k 21 -i file1.fa -i file2.fa -o combined.rkdb
```

---

## Need Help?

- **Documentation**: [Querying Databases](querying.md) for next steps
- **API Reference**: [Python API](../api-reference/python/) for complete reference
- **Performance Tips**: [Performance Guide](performance-tips.md) for optimization
- **Troubleshooting**: [FAQ](../appendix/faq.md) for common issues