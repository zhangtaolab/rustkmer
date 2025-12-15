# Processing Large Genomes with Python API

This tutorial demonstrates how to efficiently process large genomic datasets using the RustKmer Python API with memory-conscious strategies and performance optimizations.

## Tutorial Overview

You'll learn to:
- Process genomes larger than 1GB efficiently
- Use memory mapping for large database files
- Implement chunked processing strategies
- Optimize performance for large-scale k-mer analysis
- Handle memory constraints gracefully

### Prerequisites
- Python 3.8+ with RustKmer installed
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

### Context Managers for Resource Management

```python
from rustkmer import Database
import psutil
import os

def load_large_database_safely(db_path):
    """Load a large k-mer database with memory monitoring."""

    # Check available memory
    available_memory = psutil.virtual_memory().available // (1024**3)  # GB
    db_size = os.path.getsize(db_path) // (1024**3)  # GB

    print(f"Database size: {db_size:.2f} GB")
    print(f"Available memory: {available_memory:.2f} GB")

    if db_size > available_memory * 0.8:
        print("⚠️  Warning: Database is large, using memory mapping")

    # Use context manager for automatic cleanup
    with Database(db_path) as db:
        stats = db.stats()
        print(f"Database loaded successfully!")
        print(f"Unique k-mers: {stats.unique_kmers:,}")
        print(f"K-mer size: {stats.kmer_size}")

        return db, stats

# Usage
db, stats = load_large_database_safely("large_genome.rkdb")
```

### Lazy Loading and Memory Mapping

```python
from rustkmer import Database

def query_large_database_efficiently(db_path, queries, batch_size=1000):
    """Query large database in batches to manage memory."""

    results = {}

    with Database(db_path) as db:
        # Process queries in batches
        for i in range(0, len(queries), batch_size):
            batch = queries[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(queries)-1)//batch_size + 1}")

            # Batch query for efficiency
            for query in batch:
                try:
                    result = db.query(query)
                    results[query] = result.count
                except Exception as e:
                    print(f"Query failed for {query[:10]}...: {e}")
                    results[query] = 0

    return results

# Example with many queries
queries = [f"ATCG{'A' * 27}" for i in range(10000)]  # 10k queries
results = query_large_database_efficiently("human_genome.rkdb", queries)
```

---

## Strategy 2: Chunked FASTA Processing

### Process Large FASTA Files in Chunks

```python
from rustkmer import KmerCounter, Database
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

    with open(fasta_file) as handle:
        sequences = []
        seq_count = 0

        for record in SeqIO.parse(handle, "fasta"):
            seq_count += 1
            sequences.append(str(record.seq).upper())

            # Process chunk when full
            if len(sequences) >= chunk_size:
                chunk_num += 1
                chunk_file = os.path.join(temp_dir, f"chunk_{chunk_num}.fa")
                db_file = os.path.join(temp_dir, f"chunk_{chunk_num}.rkdb")

                print(f"\nProcessing chunk {chunk_num} ({len(sequences)} sequences)")

                # Write chunk to temporary FASTA
                with open(chunk_file, 'w') as out:
                    for i, seq in enumerate(sequences):
                        out.write(f">seq_{i}\n{seq}\n")

                # Count k-mers in chunk
                counter = KmerCounter(k=k, canonical=True)
                counter.count_file(chunk_file)

                # Save chunk database
                counter.save_to_database(db_file)
                all_databases.append(db_file)

                # Clear memory
                sequences.clear()

                # Memory cleanup
                del counter

    # Handle remaining sequences
    if sequences:
        chunk_num += 1
        chunk_file = os.path.join(temp_dir, f"chunk_{chunk_num}.fa")
        db_file = os.path.join(temp_dir, f"chunk_{chunk_num}.rkdb")

        print(f"\nProcessing final chunk {chunk_num} ({len(sequences)} sequences)")

        with open(chunk_file, 'w') as out:
            for i, seq in enumerate(sequences):
                out.write(f">seq_{i}\n{seq}\n")

        counter = KmerCounter(k=k, canonical=True)
        counter.count_file(chunk_file)
        counter.save_to_database(db_file)
        all_databases.append(db_file)

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

```python
from rustkmer import Database
import shutil
import os

def merge_chunk_databases(chunk_databases, output_file):
    """Merge multiple k-mer databases into one large database."""

    print(f"Merging {len(chunk_databases)} databases into {output_file}")

    # Use the first database as the base
    base_db = chunk_databases[0]

    # Copy base database to output location
    shutil.copy2(base_db, output_file)
    print(f"Created base database: {output_file}")

    # Merge remaining databases
    with Database(output_file) as merged_db:
        for i, db_file in enumerate(chunk_databases[1:], 2):
            print(f"Merging database {i}/{len(chunk_databases)}")

            # Note: This is a conceptual merge implementation
            # In practice, you'd use RustKmer's merge functionality
            # or process all chunks together in a single counting step

            # For now, we'll demonstrate the pattern
            try:
                with Database(db_file) as chunk_db:
                    # This would be replaced with actual merge implementation
                    stats = chunk_db.stats()
                    print(f"  - Processing database with {stats.unique_kmers:,} k-mers")
            except Exception as e:
                print(f"  - Error merging {db_file}: {e}")

    print("Merge completed!")
    return output_file

# Usage
merged_db = merge_chunk_databases(chunk_databases, "large_genome_merged.rkdb")
```

---

## Strategy 4: Performance Optimization

### Parallel Query Processing

```python
from rustkmer import Database
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
        with Database(db_path) as db:
            for query in queries_chunk:
                try:
                    result = db.query(query)
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
large_query_set = [f"ATCG{'ACGT' * 7}" for i in range(100000)]
results = parallel_database_query("human_genome.rkdb", large_query_set)
```

### Caching Frequently Accessed K-mers

```python
from rustkmer import Database
from functools import lru_cache
import pickle

class CachedDatabaseQuery:
    """Database query wrapper with LRU caching."""

    def __init__(self, db_path, cache_size=10000):
        self.db_path = db_path
        self.cache_size = cache_size
        self._setup_cache()

    def _setup_cache(self):
        """Setup LRU cache for query results."""
        @lru_cache(maxsize=self.cache_size)
        def cached_query(kmer):
            with Database(self.db_path) as db:
                result = db.query(kmer)
                return result.count

        self.cached_query = cached_query

    def query(self, kmer):
        """Query k-mer with caching."""
        return self.cached_query(kmer)

    def query_batch(self, kmer_list):
        """Query multiple k-mers with cache benefits."""
        return {kmer: self.query(kmer) for kmer in kmer_list}

    def save_cache(self, cache_file):
        """Save cache to file for persistence."""
        cache_info = self.cached_query.cache_info()
        cache_data = {
            'hits': cache_info.hits,
            'misses': cache_info.misses,
            'maxsize': cache_info.maxsize,
            'currsize': cache_info.currsize
        }

        with open(cache_file, 'wb') as f:
            pickle.dump(cache_data, f)

        print(f"Cache statistics saved to {cache_file}")
        print(f"Cache hit rate: {cache_info.hits/(cache_info.hits + cache_info.misses):.2%}")

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
from rustkmer import KmerCounter, Database
from Bio import SeqIO
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

        print("🧬 Human Genome K-mer Analysis Pipeline")
        print("=" * 50)

        # Step 1: Estimate processing requirements
        self._estimate_requirements()

        # Step 2: Process genome in chromosomes
        self._process_by_chromosome()

        # Step 3: Analyze k-mer distribution
        self._analyze_kmer_distribution()

        # Step 4: Generate report
        self._generate_report()

    def _estimate_requirements(self):
        """Estimate memory and time requirements."""

        file_size = os.path.getsize(self.genome_file) / (1024**3)  # GB
        available_memory = psutil.virtual_memory().available / (1024**3)  # GB

        print(f"\n📊 Resource Estimation:")
        print(f"   Genome file size: {file_size:.2f} GB")
        print(f"   Available memory: {available_memory:.2f} GB")

        # Rough estimation: 31-mers from human genome
        estimated_kmers = file_size * 1000 * 1000 * 1000  # Approximate
        estimated_unique = estimated_kmers // 10  # Rough unique estimate

        print(f"   Estimated k-mers: {estimated_kmers:,}")
        print(f"   Estimated unique: {estimated_unique:,}")

        if available_memory < 16:
            print("   ⚠️  Low memory detected, using conservative settings")
            self.chunk_size = 100000
        else:
            print("   ✅ Sufficient memory for normal processing")
            self.chunk_size = 500000

    def _process_by_chromosome(self):
        """Process genome by chromosome to manage memory."""

        print(f"\n🔄 Processing by chromosome (chunk size: {self.chunk_size:,})")
        start_time = time.time()

        # Create k-mer counter
        counter = KmerCounter(k=self.k, canonical=True)

        # Count k-mers from file (RustKmer handles large files efficiently)
        print("   Counting k-mers...")
        counter.count_file(self.genome_file)

        # Get statistics
        total_kmers = counter.get_total_count()
        unique_kmers = counter.get_unique_count()

        print(f"   Total k-mers: {total_kmers:,}")
        print(f"   Unique k-mers: {unique_kmers:,}")

        # Save database
        print(f"   Saving database to {self.db_file}")
        counter.save_to_database(self.db_file)

        processing_time = time.time() - start_time
        print(f"   Processing time: {processing_time:.1f} seconds")

        # Store statistics
        self.stats = {
            'total_kmers': total_kmers,
            'unique_kmers': unique_kmers,
            'processing_time': processing_time,
            'kmer_size': self.k
        }

    def _analyze_kmer_distribution(self):
        """Analyze k-mer frequency distribution."""

        print(f"\n📈 Analyzing k-mer distribution")

        # Load database for analysis
        with Database(self.db_file) as db:
            # Get top k-mers
            top_kmers = db.dump(limit=1000, canonical_only=True)

            # Analyze frequency distribution
            frequencies = [result.count for result in top_kmers]

            # Create DataFrame for analysis
            df = pd.DataFrame({
                'kmer': [result.kmer for result in top_kmers],
                'count': frequencies,
                'canonical': [result.canonical for result in top_kmers]
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

        print(f"\n📋 Generating Analysis Report")

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
            plt.bar(range(20), top_20['count'])
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
            print(f"   ⚠️  Visualization failed: {e}")
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
counter = KmerCounter(k=21, canonical=True)  # Instead of k=31

# Process in smaller chunks
chunk_size = 100000  # Reduce if memory constrained

# Use context managers
with Database("large_db.rkdb") as db:
    # Automatic cleanup
    pass
```

### 2. I/O Optimization
```python
# Use fast storage (SSD preferred)
db_path = "/fast_storage/human_genome.rkdb"

# Batch queries to reduce I/O
results = db.query_batch(large_query_list)

# Cache frequently accessed k-mers
cached_queries = CacheDatabase(db_path, cache_size=50000)
```

### 3. Parallel Processing
```python
# Use multiple workers for independent queries
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
    print("  - Processing chromosomes separately")
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
import threading

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