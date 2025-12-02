# K-mer Counter

Complete guide to using RustKmer's k-mer counting functionality for efficient genomic sequence analysis.

## Overview

The RustKmer `KmerCounter` provides high-performance k-mer counting from genomic sequences. It supports multiple input formats, configurable parameters, and optimized algorithms for different use cases.

## Quick Start

```python
from rustkmer import KmerCounter

# Create counter with default settings
counter = KmerCounter(k=21, canonical=True)

# Count k-mers from file
counter.count_file("input.fa")

# Get results
total_kmers = counter.get_total_count()
unique_kmers = counter.get_unique_count()
top_kmers = counter.get_top_kmers(10)

print(f"Total k-mers: {total_kmers:,}")
print(f"Unique k-mers: {unique_kmers:,}")
```

## Creating K-mer Counters

### Basic Counter
```python
from rustkmer import KmerCounter

# Simple counter with k=21
counter = KmerCounter(k=21)

# Counter with canonical k-mers (recommended for genomes)
counter = KmerCounter(k=21, canonical=True)
```

### Advanced Configuration
```python
# Counter with custom settings
counter = KmerCounter(
    k=31,                    # K-mer size
    canonical=True,          # Use canonical k-mers
    threads=8,              # Number of threads
    memory_limit="4GB"      # Memory limit
)
```

## Input Formats

### FASTA Files
```python
# Count from FASTA file
counter = KmerCounter(k=21, canonical=True)
counter.count_file("genome.fa")

# Count from compressed FASTA
counter.count_file("genome.fa.gz")

# Count from multiple FASTA files
files = ["chr1.fa", "chr2.fa", "chr3.fa"]
for file in files:
    counter.count_file(file)
```

### FASTQ Files
```python
# Count from FASTQ file
counter.count_file("reads.fq")

# Count from compressed FASTQ
counter.count_file("reads.fq.gz")

# Count from paired-end reads
counter.count_file("reads_R1.fq.gz")
counter.count_file("reads_R2.fq.gz")
```

### Streaming Input
```python
# Count from file-like object (streaming)
with open("large_file.fa", "r") as f:
    counter.count_stream(f)

# Count from string
sequence = "ATCGATCGATCGATCGATCGATCGATCGATCGATCG"
counter.count_string(sequence)
```

## Counting Parameters

### K-mer Size Selection
```python
# Small k-mers (13-17): Good for short reads, less memory
small_counter = KmerCounter(k=13, canonical=True)

# Medium k-mers (19-23): Balanced performance and specificity
medium_counter = KmerCounter(k=21, canonical=True)

# Large k-mers (27-31): High specificity, more memory
large_counter = KmerCounter(k=31, canonical=True)
```

### Canonical vs Non-Canonical
```python
# Canonical k-mers (recommended for most applications)
# Counts both sequence and its reverse complement
canonical_counter = KmerCounter(k=21, canonical=True)

# Non-canonical k-mers (faster, larger databases)
# Counts each sequence separately
non_canonical_counter = KmerCounter(k=21, canonical=False)
```

### Thread Configuration
```python
# Auto-detect optimal threads
counter = KmerCounter(k=21, canonical=True)

# Manual thread specification
counter = KmerCounter(k=21, canonical=True, threads=8)

# Single-threaded (for small files or debugging)
counter = KmerCounter(k=21, canonical=True, threads=1)
```

## Memory Management

### Memory Limits
```python
# Set memory limit
counter = KmerCounter(k=21, memory_limit="2GB")

# Process large files in chunks
counter.count_file("large_file.fa", chunk_size=1000000)
```

### Streaming Mode
```python
def process_large_file(filename):
    """Process very large files without loading everything into memory."""

    counter = KmerCounter(k=21, canonical=True)

    with open(filename, 'r') as f:
        for line in f:
            if line.startswith('>'):
                continue  # Skip header

            # Process sequence line by line
            counter.count_string(line.strip())

    return counter
```

## Progress Monitoring

### Progress Callbacks
```python
def progress_callback(current, total):
    """Called during counting to show progress."""
    progress = (current / total) * 100
    print(f"Progress: {progress:.1f}% ({current:,}/{total:,})")

counter = KmerCounter(k=21, canonical=True)
counter.count_file("large_file.fa", progress_callback=progress_callback)
```

### Real-time Statistics
```python
import time

def count_with_monitoring(filename):
    """Monitor counting progress in real-time."""

    counter = KmerCounter(k=21, canonical=True)

    start_time = time.time()
    last_time = start_time
    last_count = 0

    def monitor_progress(current, total):
        nonlocal last_time, last_count

        current_time = time.time()
        if current_time - last_time >= 5.0:  # Update every 5 seconds
            rate = (current - last_count) / (current_time - last_time)
            progress = (current / total) * 100

            print(f"Progress: {progress:.1f}% | Rate: {rate:.0f} k-mers/sec")

            last_time = current_time
            last_count = current

    counter.count_file(filename, progress_callback=monitor_progress)

    total_time = time.time() - start_time
    total_kmers = counter.get_total_count()

    print(f"Complete! Processed {total_kmers:,} k-mers in {total_time:.1f}s")
    print(f"Average rate: {total_kmers/total_time:.0f} k-mers/sec")

    return counter
```

## Working with Results

### Basic Statistics
```python
counter = KmerCounter(k=21, canonical=True)
counter.count_file("input.fa")

# Get basic counts
total_kmers = counter.get_total_count()
unique_kmers = counter.get_unique_count()
max_count = counter.get_max_count()

print(f"Total k-mers: {total_kmers:,}")
print(f"Unique k-mers: {unique_kmers:,}")
print(f"Max count: {max_count:,}")
print(f"Uniqueness ratio: {unique_kmers/total_kmers:.4f}")
```

### Top K-mers
```python
# Get most frequent k-mers
top_10 = counter.get_top_kmers(10)
print("Top 10 k-mers:")
for i, (kmer, count) in enumerate(top_10, 1):
    print(f"{i:2d}. {kmer}: {count:,}")

# Get specific k-mer count
kmer_count = counter.get_kmer_count("ATCGATCGATCGATCGATCG")
print(f"ATCGATCGATCGATCGATCG: {kmer_count}")
```

### Frequency Distribution
```python
import matplotlib.pyplot as plt

def analyze_frequency_distribution(counter):
    """Analyze the distribution of k-mer frequencies."""

    # Get frequency statistics
    top_kmers = counter.get_top_kmers(1000)
    counts = [count for _, count in top_kmers]

    # Create histogram
    plt.figure(figsize=(10, 6))
    plt.hist(counts, bins=50, alpha=0.7, edgecolor='black')
    plt.xlabel('K-mer Count')
    plt.ylabel('Number of K-mers')
    plt.title('K-mer Frequency Distribution (Top 1000)')
    plt.yscale('log')
    plt.grid(True, alpha=0.3)
    plt.show()

    # Print statistics
    print(f"Frequency Statistics:")
    print(f"  Min: {min(counts)}")
    print(f"  Max: {max(counts)}")
    print(f"  Mean: {sum(counts)/len(counts):.1f}")
    print(f"  Median: {sorted(counts)[len(counts)//2]}")

# Analyze distribution
analyze_frequency_distribution(counter)
```

## Database Creation

### Save to Database
```python
from rustkmer import KmerCounter

counter = KmerCounter(k=21, canonical=True)
counter.count_file("input.fa")

# Save to database
counter.save_to_database("output.rkdb")
print("Database saved successfully!")
```

### Database Options
```python
# Save with compression
counter.save_to_database("compressed.rkdb", compress=True)

# Save with sorting (faster querying)
counter.save_to_database("sorted.rkdb", sort=True)

# Save with indexing (very fast querying)
counter.save_to_database("indexed.rkdb", index=True)
```

### Database Statistics
```python
# Get database statistics before saving
stats = counter.get_database_stats()
print(f"Database Statistics:")
print(f"  K-mer size: {stats.kmer_size}")
print(f"  Total k-mers: {stats.total_kmers:,}")
print(f"  Unique k-mers: {stats.unique_kmers:,}")
print(f"  Estimated database size: {stats.estimated_size_mb:.1f} MB")
```

## Error Handling

### Common Errors and Solutions
```python
from rustkmer import KmerCounter
import os

def safe_count_file(filename):
    """Safely count k-mers with error handling."""

    # Check if file exists
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Input file not found: {filename}")

    # Check file size
    file_size = os.path.getsize(filename)
    if file_size == 0:
        raise ValueError(f"Input file is empty: {filename}")

    try:
        counter = KmerCounter(k=21, canonical=True)
        counter.count_file(filename)
        return counter

    except MemoryError:
        # Handle memory errors
        print("Memory error: try reducing k-mer size or using streaming mode")
        raise

    except Exception as e:
        # Handle other errors
        print(f"Error counting k-mers: {e}")
        raise

# Usage
try:
    counter = safe_count_file("input.fa")
    print(f"Successfully counted {counter.get_total_count():,} k-mers")
except Exception as e:
    print(f"Failed to count k-mers: {e}")
```

## Performance Tips

### Optimizing Counting Speed
```python
# Use appropriate k-mer size
fast_counter = KmerCounter(k=13, canonical=True)  # Faster than k=31

# Use multiple threads
parallel_counter = KmerCounter(k=21, canonical=True, threads=8)

# Use uncompressed files for speed
counter.count_file("input.fa")  # Faster than input.fa.gz

# Disable canonical mode if not needed
non_canonical_counter = KmerCounter(k=21, canonical=False)  # Faster counting
```

### Memory Optimization
```python
# Use smaller k-mer size for large files
memory_efficient_counter = KmerCounter(k=13, canonical=True)

# Process in chunks for very large files
def count_large_file_efficiently(filename):
    counter = KmerCounter(k=21, canonical=True)

    # Process file in chunks of 1MB
    chunk_size = 1024 * 1024
    counter.count_file(filename, chunk_size=chunk_size)

    return counter

# Use streaming mode
def count_streaming(filename):
    counter = KmerCounter(k=21, canonical=True)

    with open(filename, 'r') as f:
        for line in f:
            if not line.startswith('>'):
                counter.count_string(line.strip())

    return counter
```

## Advanced Usage

### Multi-sample Counting
```python
def count_multiple_samples(sample_files, output_prefix):
    """Count k-mers from multiple samples and save individual databases."""

    results = {}

    for sample_name, filename in sample_files.items():
        print(f"Processing {sample_name}...")

        counter = KmerCounter(k=21, canonical=True)
        counter.count_file(filename)

        # Save to database
        db_file = f"{output_prefix}_{sample_name}.rkdb"
        counter.save_to_database(db_file)

        # Store statistics
        results[sample_name] = {
            'total_kmers': counter.get_total_count(),
            'unique_kmers': counter.get_unique_count(),
            'database_file': db_file
        }

        print(f"  Total k-mers: {results[sample_name]['total_kmers']:,}")
        print(f"  Unique k-mers: {results[sample_name]['unique_kmers']:,}")
        print(f"  Database: {db_file}")

    return results

# Usage
samples = {
    'sample1': 'sample1.fa',
    'sample2': 'sample2.fa',
    'control': 'control.fa'
}

results = count_multiple_samples(samples, "experiment")
```

### Comparative Analysis
```python
def compare_kmer_compositions(counter1, counter2, name1="Sample1", name2="Sample2"):
    """Compare k-mer compositions between two samples."""

    # Get top k-mers from both
    top1 = dict(counter1.get_top_kmers(100))
    top2 = dict(counter2.get_top_kmers(100))

    # Find common and unique k-mers
    common_kmers = set(top1.keys()) & set(top2.keys())
    unique1 = set(top1.keys()) - set(top2.keys())
    unique2 = set(top2.keys()) - set(top1.keys())

    print(f"Comparison between {name1} and {name2}:")
    print(f"  Common top k-mers: {len(common_kmers)}")
    print(f"  Unique to {name1}: {len(unique1)}")
    print(f"  Unique to {name2}: {len(unique2)}")

    # Show some examples
    if unique1:
        print(f"\nUnique to {name1} (top 5):")
        for kmer in sorted(unique1, key=lambda x: top1[x], reverse=True)[:5]:
            print(f"  {kmer}: {top1[kmer]}")

    if unique2:
        print(f"\nUnique to {name2} (top 5):")
        for kmer in sorted(unique2, key=lambda x: top2[x], reverse=True)[:5]:
            print(f"  {kmer}: {top2[kmer]}")

    return {
        'common_kmers': common_kmers,
        'unique_to_1': unique1,
        'unique_to_2': unique2
    }

# Usage
counter1 = KmerCounter(k=21, canonical=True)
counter1.count_file("sample1.fa")

counter2 = KmerCounter(k=21, canonical=True)
counter2.count_file("sample2.fa")

comparison = compare_kmer_compositions(counter1, counter2, "Sample1", "Sample2")
```

## Complete Examples

### Genome Analysis Pipeline
```python
def complete_genome_analysis(genome_file, output_prefix):
    """Complete k-mer analysis pipeline for a genome."""

    print(f"🧬 Starting genome analysis for {genome_file}")

    # Step 1: Count k-mers with different sizes
    k_sizes = [13, 21, 31]
    counters = {}

    for k in k_sizes:
        print(f"\n📊 Counting k-mers (k={k})...")

        counter = KmerCounter(k=k, canonical=True)
        counter.count_file(genome_file)

        counters[k] = counter

        total = counter.get_total_count()
        unique = counter.get_unique_count()

        print(f"   Total k-mers: {total:,}")
        print(f"   Unique k-mers: {unique:,}")
        print(f"   Uniqueness ratio: {unique/total:.4f}")

    # Step 2: Save databases
    print(f"\n💾 Saving databases...")
    for k, counter in counters.items():
        db_file = f"{output_prefix}_k{k}.rkdb"
        counter.save_to_database(db_file, sort=True, index=True)
        print(f"   Saved: {db_file}")

    # Step 3: Generate analysis report
    print(f"\n📈 Generating analysis report...")
    report_file = f"{output_prefix}_analysis.txt"

    with open(report_file, 'w') as f:
        f.write(f"Genome K-mer Analysis Report\n")
        f.write(f"=" * 40 + "\n\n")
        f.write(f"Input file: {genome_file}\n")
        f.write(f"Output prefix: {output_prefix}\n\n")

        for k, counter in counters.items():
            f.write(f"K-mer size: {k}\n")
            f.write(f"  Total k-mers: {counter.get_total_count():,}\n")
            f.write(f"  Unique k-mers: {counter.get_unique_count():,}\n")
            f.write(f"  Max count: {counter.get_max_count():,}\n")

            # Top 10 k-mers
            f.write(f"  Top 10 k-mers:\n")
            for i, (kmer, count) in enumerate(counter.get_top_kmers(10), 1):
                f.write(f"    {i:2d}. {kmer}: {count:,}\n")
            f.write("\n")

    print(f"   Report saved: {report_file}")
    print(f"\n✅ Analysis complete!")

    return counters

# Usage
# results = complete_genome_analysis("genome.fa", "genome_analysis")
```

### Metagenomics Sample Processing
```python
def process_metagenomics_samples(sample_files, output_dir):
    """Process multiple metagenomics samples."""

    import os

    os.makedirs(output_dir, exist_ok=True)

    all_results = {}

    for sample_name, filename in sample_files.items():
        print(f"\n🔬 Processing sample: {sample_name}")

        try:
            # Count k-mers
            counter = KmerCounter(k=21, canonical=True)
            counter.count_file(filename)

            # Save database
            db_file = os.path.join(output_dir, f"{sample_name}.rkdb")
            counter.save_to_database(db_file, sort=True)

            # Collect statistics
            stats = {
                'total_kmers': counter.get_total_count(),
                'unique_kmers': counter.get_unique_count(),
                'database_file': db_file,
                'top_kmers': counter.get_top_kmers(20)
            }

            all_results[sample_name] = stats

            print(f"   Total k-mers: {stats['total_kmers']:,}")
            print(f"   Unique k-mers: {stats['unique_kmers']:,}")
            print(f"   Database: {db_file}")

        except Exception as e:
            print(f"   Error processing {sample_name}: {e}")
            all_results[sample_name] = {'error': str(e)}

    # Generate summary report
    summary_file = os.path.join(output_dir, "metagenomics_summary.txt")

    with open(summary_file, 'w') as f:
        f.write("Metagenomics Sample Summary\n")
        f.write("=" * 40 + "\n\n")

        for sample_name, stats in all_results.items():
            if 'error' in stats:
                f.write(f"{sample_name}: ERROR - {stats['error']}\n\n")
            else:
                f.write(f"{sample_name}:\n")
                f.write(f"  Total k-mers: {stats['total_kmers']:,}\n")
                f.write(f"  Unique k-mers: {stats['unique_kmers']:,}\n")
                f.write(f"  Database: {stats['database_file']}\n\n")

    print(f"\n📊 Summary report: {summary_file}")
    return all_results
```

---

## Need More Help?

- **[Database Creation](database-creation.md)** - Working with k-mer databases
- **[Querying](querying.md)** - Querying k-mer databases
- **[Performance Tips](performance-tips.md)** - Optimization strategies
- **[API Reference](../api-reference/python/)** - Complete function documentation