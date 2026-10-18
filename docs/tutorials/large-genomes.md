<!-- generated-by: gsd-doc-writer -->
# Processing Large Genomes with Python API

This tutorial demonstrates how to efficiently process large genomic datasets using the RustKmer Python API with memory-conscious strategies and performance optimizations.

## Tutorial Overview

You'll learn to:
- Process genomes larger than 1GB efficiently
- Choose the right database loading mode for large files
- Implement chunked processing strategies
- Optimize performance for large-scale k-mer analysis
- Handle memory constraints gracefully

### Prerequisites
- Python 3.11+ with RustKmer installed (`pip install pyrustkmer`)
- Basic understanding of k-mer analysis
- 16GB+ RAM recommended for large genome processing
- 30-60 minutes to complete

---

## Challenge: Large Genomes

Processing large genomes presents unique challenges:
- **Memory usage**: Whole-genome k-mer counting can require >50GB RAM
- **Processing time**: Large datasets need efficient algorithms
- **Storage**: K-mer databases can be several gigabytes
- **I/O bottlenecks**: Disk access becomes limiting factor

### Example Datasets
- **Human genome**: ~3GB FASTA, ~30M unique 31-mers
- **Wheat genome**: ~15GB FASTA, ~500M unique 31-mers
- **Conifer genomes**: ~20GB+ FASTA, billions of k-mers

---

## Strategy 1: Memory-Efficient Database Loading

### Choosing a Load Mode

`PyDatabase` requires a `LoadMode` as its second constructor argument, and the choice drives the memory profile:

- `LoadMode.Preload` — caches every k-mer in memory. Fastest queries, highest memory use.
- `LoadMode.Lazy` — keeps a sorted index and answers exact lookups by binary search. Lower memory than Preload, slightly slower queries. This is the usual choice for large databases.
- `LoadMode.MemoryMapped` — keeps the file open for direct per-entry reads (`get_entry_by_index`); it does not cache entries and is intended for index-based access rather than exact lookups.

`PyDatabase` is not a context manager — load it, use it, and drop the reference when done so the memory is reclaimed.

```python
from pyrustkmer import PyDatabase, LoadMode
import psutil
import os

def load_large_database_safely(db_path):
    """Load a large k-mer database with memory monitoring."""

    # Check available memory
    available_memory = psutil.virtual_memory().available // (1024**3)  # GB
    db_size = os.path.getsize(db_path) // (1024**3)  # GB

    print(f"Database size: {db_size:.2f} GB")
    print(f"Available memory: {available_memory:.2f} GB")

    # Lazy mode avoids caching every k-mer in RAM
    mode = LoadMode.Lazy if db_size > available_memory * 0.8 else LoadMode.Preload
    print(f"Using LoadMode: {mode}")

    db = PyDatabase(db_path, mode)
    stats = db.get_stats()
    print(f"Database loaded successfully!")
    print(f"Unique k-mers: {stats.unique_kmers:,}")
    print(f"K-mer size: {stats.kmer_size}")

    return db, stats

# Usage
db, stats = load_large_database_safely("large_genome.rkdb")
```

### Batched Querying of Large Databases

```python
from pyrustkmer import PyDatabase, LoadMode

def query_large_database_efficiently(db_path, queries, batch_size=1000):
    """Query large database in batches to manage memory."""

    results = {}

    # Lazy mode: binary-search lookups without a full in-memory cache
    db = PyDatabase(db_path, LoadMode.Lazy)

    # Process queries in batches
    for i in range(0, len(queries), batch_size):
        batch = queries[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(queries)-1)//batch_size + 1}")

        # query_exact_batch performs the whole batch in one call and
        # returns {kmer: PyQueryResult}
        batch_results = db.query_exact_batch(batch)

        for query, result in batch_results.items():
            results[query] = result.count

    return results

# Example with many queries (each query must match the database k-mer size)
queries = ["ATCG" + "ACGT" * 8 for i in range(10000)]  # 10k queries, k=36
results = query_large_database_efficiently("human_genome.rkdb", queries)
```

---

## Strategy 2: Chunked FASTA Processing

### Process Large FASTA Files in Chunks

```python
from pyrustkmer import PyCounter
from Bio import SeqIO
import tempfile
import os

def process_large_fasta_in_chunks(fasta_file, k=31, chunk_size=1000000, output_prefix="genome"):
    """Process large FASTA file in manageable chunks."""

    print(f"Processing {fasta_file} with k={k}")
    print(f"Chunk size: {chunk_size:,} sequences")

    chunk_num = 0
    all_databases = []

    # Create temporary directory for chunks
    temp_dir = tempfile.mkdtemp()
    print(f"Using temporary directory: {temp_dir}")

    def count_chunk(sequences, chunk_num):
        chunk_file = os.path.join(temp_dir, f"chunk_{chunk_num}.fa")
        db_file = os.path.join(temp_dir, f"chunk_{chunk_num}.rkdb")

        print(f"\nProcessing chunk {chunk_num} ({len(sequences)} sequences)")

        # Write chunk to temporary FASTA
        with open(chunk_file, 'w') as out:
            for i, seq in enumerate(sequences):
                out.write(f">seq_{i}\n{seq}\n")

        # Count k-mers in chunk (parallelized internally via Rayon)
        counter = PyCounter(k, canonical=True)
        counter.add_from_fasta(chunk_file)

        # Save chunk database
        counter.save_database(db_file)
        return db_file

    with open(fasta_file) as handle:
        sequences = []
        seq_count = 0

        for record in SeqIO.parse(handle, "fasta"):
            seq_count += 1
            sequences.append(str(record.seq).upper())

            # Process chunk when full
            if len(sequences) >= chunk_size:
                chunk_num += 1
                all_databases.append(count_chunk(sequences, chunk_num))
                sequences.clear()

    # Handle remaining sequences
    if sequences:
        chunk_num += 1
        all_databases.append(count_chunk(sequences, chunk_num))

    print(f"\nProcessed {seq_count:,} sequences in {chunk_num} chunks")
    return all_databases, temp_dir

# Usage
chunk_databases, temp_dir = process_large_fasta_in_chunks(
    "large_genome.fasta",
    k=31,
    chunk_size=500000
)
```

### Memory Monitoring During Processing

```python
import psutil
import time

def monitor_memory_during_processing(process_func, *args, **kwargs):
    """Monitor memory usage during long-running processes."""

    def memory_report():
        memory = psutil.virtual_memory()
        process = psutil.Process()
        return {
            'total_gb': memory.total / (1024**3),
            'available_gb': memory.available / (1024**3),
            'used_gb': memory.used / (1024**3),
            'process_gb': process.memory_info().rss / (1024**3),
            'percent': memory.percent
        }

    print("Starting process with memory monitoring...")
    start_time = time.time()

    # Initial memory state
    initial = memory_report()
    print(f"Initial memory: {initial['process_gb']:.2f} GB process, {initial['available_gb']:.2f} GB available")

    # Run the process
    result = process_func(*args, **kwargs)

    # Final memory state
    final = memory_report()
    duration = time.time() - start_time

    print(f"\nProcess completed in {duration:.1f} seconds")
    print(f"Final memory: {final['process_gb']:.2f} GB process, {final['available_gb']:.2f} GB available")
    print(f"Peak memory usage: {final['process_gb'] - initial['process_gb']:.2f} GB increase")

    return result

# Usage
chunk_databases, temp_dir = monitor_memory_during_processing(
    process_large_fasta_in_chunks,
    "huge_genome.fasta",
    k=31,
    chunk_size=1000000
)
```

---

## Strategy 3: Merging Large Databases

### Efficient Database Merging

`PyDatabase.merge()` is the memory-bounded way to combine chunk databases: it reads the total k-mer count from the input headers, compares it against a memory budget (`max_memory`), and routes to a streaming merge when the inputs exceed the budget. The merged database is written directly to the output file — it is never fully materialized in RAM.

```python
from pyrustkmer import PyDatabase, LoadMode
import os

def merge_chunk_databases(chunk_databases, output_file, max_memory="8GB"):
    """Merge multiple k-mer databases into one large database."""

    print(f"Merging {len(chunk_databases)} databases into {output_file}")

    # Static call: bounded merge, streams when the inputs exceed max_memory
    PyDatabase.merge(
        [str(f) for f in chunk_databases],
        output_file,
        max_memory=max_memory,
        merge_mode="auto",  # "memory" refuses to run over budget; "streaming" always streams
    )

    print("Merge completed!")

    # Read back statistics from the merged database
    merged = PyDatabase(output_file, LoadMode.Lazy)
    stats = merged.get_stats()
    print(f"Merged unique k-mers: {stats.unique_kmers:,}")

    return output_file

# Usage
merged_db = merge_chunk_databases(chunk_databases, "large_genome_merged.rkdb")
```

---

## Strategy 4: Performance Optimization

### Parallel Query Processing

```python
from pyrustkmer import PyDatabase, LoadMode
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

def parallel_database_query(db_path, query_list, max_workers=None):
    """Query database with multiple parallel workers."""

    if max_workers is None:
        max_workers = min(multiprocessing.cpu_count(), 8)

    print(f"Starting parallel query with {max_workers} workers")
    print(f"Processing {len(query_list):,} queries")

    def worker_batch_queries(queries_chunk):
        """Worker function for batch queries."""
        results = {}
        db = PyDatabase(db_path, LoadMode.Lazy)
        for query in queries_chunk:
            try:
                result = db.query_exact(query)
                results[query] = result.count
            except Exception as e:
                print(f"Query failed: {e}")
                results[query] = 0
        return results

    # Split queries into chunks for workers
    chunk_size = max(1, len(query_list) // max_workers)
    query_chunks = [query_list[i:i + chunk_size]
                    for i in range(0, len(query_list), chunk_size)]

    all_results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_chunk = {
            executor.submit(worker_batch_queries, chunk): i
            for i, chunk in enumerate(query_chunks)
        }

        # Collect results as they complete
        for future in as_completed(future_to_chunk):
            chunk_id = future_to_chunk[future]
            try:
                chunk_results = future.result()
                all_results.update(chunk_results)
                print(f"Completed chunk {chunk_id + 1}/{len(query_chunks)}")
            except Exception as e:
                print(f"Chunk {chunk_id} failed: {e}")

    print(f"Processed {len(all_results):,} queries successfully")
    return all_results

# Usage
large_query_set = [f"ATCG{'ACGT' * 8}" for i in range(100000)]
results = parallel_database_query("human_genome.rkdb", large_query_set)
```

### Caching Frequently Accessed K-mers

```python
from pyrustkmer import PyDatabase, LoadMode
from functools import lru_cache
import pickle

class CachedDatabaseQuery:
    """Database query wrapper with LRU caching."""

    def __init__(self, db_path, cache_size=10000):
        self.db_path = db_path
        self.cache_size = cache_size
        self._setup_cache()

    def _setup_cache(self):
        """Load the database once and cache lookups on top of it."""

        # One shared database instance; Lazy mode keeps memory low
        db = PyDatabase(self.db_path, LoadMode.Lazy)

        @lru_cache(maxsize=self.cache_size)
        def cached_query(kmer):
            return db.query_exact(kmer).count

        self.cached_query = cached_query

    def query(self, kmer):
        """Query k-mer with caching."""
        return self.cached_query(kmer)

    def query_batch(self, kmer_list):
        """Query multiple k-mers with cache benefits."""
        return {kmer: self.query(kmer) for kmer in kmer_list}

    def save_cache(self, cache_file):
        """Save cache statistics to file for persistence."""
        cache_info = self.cached_query.cache_info()
        cache_data = {
            'hits': cache_info.hits,
            'misses': cache_info.misses,
            'maxsize': cache_info.maxsize,
            'currsize': cache_info.currsize
        }

        with open(cache_file, 'wb') as f:
            pickle.dump(cache_data, f)

        total = cache_info.hits + cache_info.misses
        if total > 0:
            print(f"Cache hit rate: {cache_info.hits/total:.2%}")
        print(f"Cache statistics saved to {cache_file}")

# Usage
cached_db = CachedDatabaseQuery("large_genome.rkdb", cache_size=50000)

# Query with caching
results = []
for query in frequent_queries:
    count = cached_db.query(query)
    results.append((query, count))

# Save cache statistics
cached_db.save_cache("query_cache_stats.pkl")
```

---

## Strategy 5: Real-World Example

### Human Genome K-mer Analysis

```python
#!/usr/bin/env python3
"""
Human genome k-mer analysis pipeline.
Demonstrates processing of a 3GB human genome with 31-mers.
"""

import os
import time
import psutil
from pyrustkmer import PyCounter, PyDatabase, LoadMode
import matplotlib.pyplot as plt
import pandas as pd

class HumanGenomeAnalyzer:
    """Analyze human genome k-mers efficiently."""

    def __init__(self, genome_file, k=31):
        self.genome_file = genome_file
        self.k = k
        self.db_file = f"human_genome_k{k}.rkdb"

    def analyze_genome(self):
        """Complete human genome analysis pipeline."""

        print("Human Genome K-mer Analysis Pipeline")
        print("=" * 50)

        # Step 1: Estimate processing requirements
        self._estimate_requirements()

        # Step 2: Count the genome
        self._count_genome()

        # Step 3: Analyze k-mer distribution
        self._analyze_kmer_distribution()

        # Step 4: Generate report
        self._generate_report()

    def _estimate_requirements(self):
        """Estimate memory and time requirements."""

        file_size = os.path.getsize(self.genome_file) / (1024**3)  # GB
        available_memory = psutil.virtual_memory().available / (1024**3)  # GB

        print(f"\nResource Estimation:")
        print(f"   Genome file size: {file_size:.2f} GB")
        print(f"   Available memory: {available_memory:.2f} GB")

        # Rough estimation: 31-mers from human genome
        estimated_kmers = file_size * 1000 * 1000 * 1000  # Approximate
        estimated_unique = estimated_kmers // 10  # Rough unique estimate

        print(f"   Estimated k-mers: {estimated_kmers:,}")
        print(f"   Estimated unique: {estimated_unique:,}")

        if available_memory < 16:
            print(f"   Low memory detected, using conservative settings")
            self.analyze_limit = 100000
        else:
            print(f"   Sufficient memory for normal processing")
            self.analyze_limit = 1000000

    def _count_genome(self):
        """Count k-mers and save the database."""

        print(f"\nCounting k-mers (k={self.k})")
        start_time = time.time()

        # Create k-mer counter (counting is parallelized internally via Rayon)
        counter = PyCounter(self.k, canonical=True)

        # Count k-mers from file (RustKmer handles large files efficiently)
        print("   Counting k-mers...")
        counter.add_from_fasta(self.genome_file)

        # Get statistics
        stats = counter.get_stats()

        print(f"   Total k-mers: {stats.total_kmers:,}")
        print(f"   Unique k-mers: {stats.unique_kmers:,}")

        # Save database
        print(f"   Saving database to {self.db_file}")
        counter.save_database(self.db_file)

        processing_time = time.time() - start_time
        print(f"   Processing time: {processing_time:.1f} seconds")

        # Store statistics
        self.stats = {
            'total_kmers': stats.total_kmers,
            'unique_kmers': stats.unique_kmers,
            'processing_time': processing_time,
            'kmer_size': self.k
        }

    def _analyze_kmer_distribution(self):
        """Analyze k-mer frequency distribution."""

        print(f"\nAnalyzing k-mer distribution")

        # Load database for analysis (Lazy: no full in-memory cache)
        db = PyDatabase(self.db_file, LoadMode.Lazy)

        # Paginated read of decoded k-mers; sort by count for the top list
        entries = db.export_all_kmers(limit=self.analyze_limit)

        # Analyze frequency distribution
        frequencies = [result.count for result in entries]

        # Create DataFrame for analysis
        df = pd.DataFrame({
            'kmer': [result.kmer for result in entries],
            'count': frequencies
        })

        # Statistics
        self.frequency_stats = {
            'max_count': max(frequencies),
            'min_count': min(frequencies),
            'mean_count': sum(frequencies) / len(frequencies),
            'median_count': sorted(frequencies)[len(frequencies)//2]
        }

        print(f"   Max k-mer count: {self.frequency_stats['max_count']:,}")
        print(f"   Min k-mer count: {self.frequency_stats['min_count']:,}")
        print(f"   Mean k-mer count: {self.frequency_stats['mean_count']:.1f}")

        # Store data for visualization
        self.frequency_data = df

    def _generate_report(self):
        """Generate analysis report."""

        print(f"\nGenerating Analysis Report")

        # Create report
        report = f"""
# Human Genome K-mer Analysis Report

## Summary
- **Genome file**: {self.genome_file}
- **K-mer size**: {self.k}
- **Processing time**: {self.stats['processing_time']:.1f} seconds

## Statistics
- **Total k-mers**: {self.stats['total_kmers']:,}
- **Unique k-mers**: {self.stats['unique_kmers']:,}
- **Uniqueness ratio**: {self.stats['unique_kmers']/self.stats['total_kmers']:.4f}

## Frequency Distribution
- **Maximum count**: {self.frequency_stats['max_count']:,}
- **Minimum count**: {self.frequency_stats['min_count']:,}
- **Mean count**: {self.frequency_stats['mean_count']:.1f}
- **Median count**: {self.frequency_stats['median_count']}

## Database
- **File**: {self.db_file}
- **Size**: {os.path.getsize(self.db_file)/(1024**3):.2f} GB

## Top 10 K-mers
"""

        # Add top 10 k-mers
        top_10 = self.frequency_data.nlargest(10, 'count')
        for _, row in top_10.iterrows():
            report += f"  {row['kmer']}: {row['count']:,}\n"

        # Save report
        with open("human_genome_analysis_report.md", "w") as f:
            f.write(report)

        print("   Report saved to: human_genome_analysis_report.md")

        # Create visualization
        self._create_visualization()

    def _create_visualization(self):
        """Create k-mer frequency visualization."""

        try:
            plt.figure(figsize=(12, 8))

            # Histogram of frequencies
            plt.subplot(2, 2, 1)
            plt.hist(self.frequency_data['count'], bins=50, alpha=0.7)
            plt.xlabel('K-mer Count')
            plt.ylabel('Frequency')
            plt.title('K-mer Count Distribution')
            plt.yscale('log')

            # Top 20 k-mers bar chart
            plt.subplot(2, 2, 2)
            top_20 = self.frequency_data.nlargest(20, 'count')
            plt.bar(range(len(top_20)), top_20['count'])
            plt.xlabel('Rank')
            plt.ylabel('Count')
            plt.title('Top 20 K-mers')

            # Cumulative distribution
            plt.subplot(2, 2, 3)
            sorted_counts = sorted(self.frequency_data['count'], reverse=True)
            cumulative = [sum(sorted_counts[:i+1])/sum(sorted_counts)
                         for i in range(len(sorted_counts))]
            plt.plot(range(len(cumulative)), cumulative)
            plt.xlabel('K-mer Rank')
            plt.ylabel('Cumulative Fraction')
            plt.title('Cumulative K-mer Distribution')

            # Count vs rank (log-log)
            plt.subplot(2, 2, 4)
            plt.loglog(range(1, len(top_20)+1), top_20['count'], 'o-')
            plt.xlabel('Rank (log scale)')
            plt.ylabel('Count (log scale)')
            plt.title('K-mer Rank-Count Relationship')

            plt.tight_layout()
            plt.savefig('human_genome_kmer_analysis.png', dpi=300, bbox_inches='tight')
            print("   Visualization saved to: human_genome_kmer_analysis.png")

        except Exception as e:
            print(f"   Visualization failed: {e}")
            print("   Install matplotlib for visualizations: pip install matplotlib")

# Usage
if __name__ == "__main__":
    # Example with human genome
    analyzer = HumanGenomeAnalyzer("human_genome.fasta", k=31)
    analyzer.analyze_genome()
```

---

## Performance Tips for Large Genomes

### 1. Memory Optimization
```python
# Use smaller k-mer sizes for memory efficiency
counter = PyCounter(21, canonical=True)  # Instead of k=31

# Load large databases in Lazy mode instead of Preload
db = PyDatabase("large_db.rkdb", LoadMode.Lazy)

# Read entries in paginated batches instead of all at once
batch = db.export_all_kmers(limit=10000, offset=0)
```

### 2. I/O Optimization
```python
# Use fast storage (SSD preferred)
db_path = "/fast_storage/human_genome.rkdb"

# Batch queries to reduce per-call overhead
results = db.query_exact_batch(large_query_list)

# Note: the older query_batch() alias still works but is deprecated;
# prefer query_exact_batch()

# Cache frequently accessed k-mers (see CachedDatabaseQuery above)
cached_queries = CachedDatabaseQuery(db_path, cache_size=50000)
```

### 3. Parallel Processing
```python
# PyCounter parallelizes counting internally via its `threads` argument
counter = PyCounter(31, canonical=True, threads=8)

# Use process pools for independent Python-side work (e.g. per-chromosome
# post-processing)
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(process_chromosome, chr_file)
               for chr_file in chromosome_files]
```

---

## Troubleshooting Large Genome Processing

### Memory Issues
```python
# Check memory before processing
import psutil
available_gb = psutil.virtual_memory().available / (1024**3)

if available_gb < 8:
    print("Insufficient memory for large genome processing")
    print("Consider:")
    print("  - Using smaller k-mer size (k=21 instead of k=31)")
    print("  - Processing chromosomes separately, then merging with")
    print("    PyDatabase.merge(..., max_memory=..., merge_mode='streaming')")
    print("  - Using a machine with more RAM")
```

### Disk Space
```python
# Check disk space before creating databases
import shutil

total, used, free = shutil.disk_usage("/path/to/storage")
free_gb = free / (1024**3)

print(f"Available disk space: {free_gb:.2f} GB")
print(f"Estimated database size: {estimated_size_gb:.2f} GB")

if free_gb < estimated_size_gb * 1.5:
    print("Warning: Low disk space for database creation")
```

### Performance Monitoring
```python
# Monitor progress during long operations
import time

class ProgressMonitor:
    def __init__(self, total_operations):
        self.total = total_operations
        self.completed = 0
        self.start_time = time.time()

    def update(self, increment=1):
        self.completed += increment
        progress = self.completed / self.total
        elapsed = time.time() - self.start_time
        eta = elapsed / progress * (1 - progress) if progress > 0 else 0

        print(f"\rProgress: {progress:.1%} | ETA: {eta:.0f}s", end="", flush=True)
```

---

## Next Steps

- **Explore advanced features**: Position-specific mutations, batch processing
- **Optimize for your data**: Adjust chunk sizes and k-mer lengths
- **Integrate with pipelines**: Snakemake, Nextflow workflows
- **Scale to clusters**: Distributed k-mer processing

## Related Documentation

- [Python API Reference](../api-reference/python/)
- [Batch Processing Tutorial](batch-processing.md)
- [Integration Tutorial](integration.md)
- [Performance Tips](../user-guide/performance-tips.md)
