# Python API Examples

This page provides comprehensive examples of using the RustKmer Python API for various bioinformatics workflows and use cases.

## Basic Examples

### Simple K-mer Counting
```python
from rustkmer import KmerCounter

# Create a counter for 21-mers
counter = KmerCounter(k=21, canonical=True)

# Count k-mers from a file
counter.count_file("genome.fa.gz")

# Get basic statistics
total = counter.get_total_count()
unique = counter.get_unique_count()

print(f"Total k-mers: {total:,}")
print(f"Unique k-mers: {unique:,}")
print(f"Uniqueness ratio: {unique/total:.4f}")
```

### Database Querying
```python
from rustkmer import Database

# Load a database
db = Database()
db.load("genome_k21.rkdb")

# Query exact k-mers
result = db.query("ATCGATCGATCGATCGATCG")
if result.exists:
    print(f"Found k-mer: {result.kmer}")
    print(f"Count: {result.count}")

# Get database statistics
stats = db.get_stats()
print(f"Database contains {stats.unique_kmers:,} unique k-mers")

db.close()
```

## Advanced Examples

### Complete Workflow: Counting and Querying
```python
from rustkmer import KmerCounter, Database

def analyze_genome(input_file, db_output):
    """Complete genome analysis workflow."""

    # Step 1: Count k-mers
    print(f"Counting k-mers from {input_file}...")
    counter = KmerCounter(k=21, canonical=True)
    counter.count_file(input_file)

    # Get statistics
    total = counter.get_total_count()
    unique = counter.get_unique_count()
    print(f"Counted {total:,} total k-mers")
    print(f"Found {unique:,} unique k-mers")

    # Step 2: Save to database
    print(f"Saving database to {db_output}...")
    counter.save_to_database(db_output)

    # Step 3: Query the database
    print("Querying database...")
    db = Database()
    db.load(db_output)

    # Get top k-mers
    top_kmers = counter.get_top_kmers(10)
    print("Top 10 most frequent k-mers:")
    for i, (kmer, count) in enumerate(top_kmers, 1):
        print(f"  {i}. {kmer}: {count:,}")

    db.close()
    return counter

# Usage
genome_file = "genome.fa.gz"
database_file = "genome_analysis.rkdb"
counter = analyze_genome(genome_file, database_file)
```

### Batch Processing Multiple Files
```python
from rustkmer import KmerCounter, Database
import glob
import os

def process_chromosomes(chromosome_dir, output_db):
    """Process multiple chromosome files into a single database."""

    # Initialize counter
    counter = KmerCounter(k=21, canonical=True)

    # Find all chromosome files
    chromosome_files = glob.glob(os.path.join(chromosome_dir, "chr*.fa.gz"))
    print(f"Found {len(chromosome_files)} chromosome files")

    # Process each file
    for i, chrom_file in enumerate(chromosome_files, 1):
        chrom_name = os.path.basename(chrom_file)
        print(f"[{i}/{len(chromosome_files)}] Processing {chrom_name}...")

        try:
            counter.count_file(chrom_file)
            print(f"  Current total: {counter.get_total_count():,}")
        except Exception as e:
            print(f"  Error processing {chrom_name}: {e}")
            continue

    # Save combined results
    print(f"Saving combined database to {output_db}...")
    counter.save_to_database(output_db)

    # Final statistics
    print(f"\nFinal Results:")
    print(f"  Total k-mers: {counter.get_total_count():,}")
    print(f"  Unique k-mers: {counter.get_unique_count():,}")

    return counter

# Usage
counter = process_chromosomes("chromosomes/", "all_chromosomes_k21.rkdb")
```

### Fuzzy Querying with Wildcards
```python
from rustkmer import Database

def fuzzy_search_examples(db_file):
    """Demonstrate various fuzzy query patterns."""

    db = Database()
    db.load(db_file)

    # Example 1: Single wildcard (N = any base)
    print("1. Single wildcard queries:")
    patterns = ["AATN", "CGTN", "TTN"]
    for pattern in patterns:
        results = db.fuzzy_query(pattern)
        print(f"  Pattern {pattern}: {len(results)} matches")
        for result in results[:3]:  # Show first 3
            print(f"    {result.kmer}: {result.count}")

    # Example 2: Multiple wildcards
    print("\n2. Multiple wildcard queries:")
    patterns = ["ATNNT", "CGNNG"]
    for pattern in patterns:
        results = db.fuzzy_query(pattern)
        print(f"  Pattern {pattern}: {len(results)} matches")

    # Example 3: Distance-based fuzzy queries
    print("\n3. Distance-based fuzzy queries:")
    query = "ATCGATCGATCGATCGATCG"
    for distance in [1, 2, 3]:
        results = db.fuzzy_query(query, max_distance=distance)
        print(f"  Distance {distance}: {len(results)} matches")
        if results:
            print(f"    Example: {results[0].kmer} (dist={results[0].distance})")

    db.close()

# Usage
fuzzy_search_examples("genome_k21.rkdb")
```

## Data Analysis Examples

### K-mer Frequency Analysis
```python
from rustkmer import KmerCounter
import matplotlib.pyplot as plt
import numpy as np

def analyze_kmer_frequency(input_file, top_n=1000):
    """Analyze k-mer frequency distribution."""

    # Count k-mers
    counter = KmerCounter(k=21, canonical=True)
    counter.count_file(input_file)

    # Get top k-mers
    top_kmers = counter.get_top_kmers(top_n)

    # Extract counts
    counts = [count for kmer, count in top_kmers]
    kmers = [kmer for kmer, count in top_kmers]

    # Calculate statistics
    total_count = counter.get_total_count()
    frequencies = [count / total_count for count in counts]

    print(f"Frequency Analysis Results:")
    print(f"  Most frequent k-mer: {kmers[0]} ({counts[0]:,} occurrences)")
    print(f"  Frequency of most common: {frequencies[0]:.8f}")
    print(f"  Median frequency (top {top_n}): {np.median(frequencies):.8f}")
    print(f"  Mean frequency (top {top_n}): {np.mean(frequencies):.8f}")

    # Create visualization
    plt.figure(figsize=(12, 8))

    # Plot 1: Frequency distribution
    plt.subplot(2, 2, 1)
    plt.hist(frequencies, bins=50, log=True, alpha=0.7, color='blue')
    plt.xlabel('K-mer Frequency')
    plt.ylabel('Number of K-mers (log scale)')
    plt.title('K-mer Frequency Distribution')

    # Plot 2: Top 20 k-mers
    plt.subplot(2, 2, 2)
    top_20 = top_kmers[:20]
    y_pos = range(len(top_20))
    plt.barh(y_pos, [count for kmer, count in top_20])
    plt.yticks(y_pos, [kmer for kmer, count in top_20])
    plt.xlabel('Count')
    plt.title('Top 20 Most Frequent K-mers')
    plt.gca().invert_yaxis()

    # Plot 3: Cumulative frequency
    plt.subplot(2, 2, 3)
    cumulative = np.cumsum(frequencies)
    plt.plot(range(len(cumulative)), cumulative)
    plt.xlabel('Rank')
    plt.ylabel('Cumulative Frequency')
    plt.title('Cumulative Frequency Distribution')

    # Plot 4: Count vs rank (log-log scale)
    plt.subplot(2, 2, 4)
    plt.loglog(range(1, len(counts) + 1), counts)
    plt.xlabel('Rank')
    plt.ylabel('Count')
    plt.title('Count vs Rank (Log-Log Scale)')

    plt.tight_layout()
    plt.savefig('kmer_frequency_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()

    return counter, top_kmers

# Usage
counter, top_kmers = analyze_kmer_frequency("genome.fa.gz")
```

### Comparative K-mer Analysis
```python
from rustkmer import KmerCounter
import pandas as pd
from collections import defaultdict

def compare_genomes(files_dict, output_file="genome_comparison.csv"):
    """Compare k-mer frequencies across multiple genomes."""

    results = defaultdict(dict)

    # Process each genome file
    for genome_name, file_path in files_dict.items():
        print(f"Processing {genome_name}...")

        counter = KmerCounter(k=21, canonical=True)
        counter.count_file(file_path)

        # Get top k-mers for this genome
        top_kmers = counter.get_top_kmers(1000)

        # Store results
        for kmer, count in top_kmers:
            results[kmer][genome_name] = count

    # Convert to DataFrame
    df = pd.DataFrame.from_dict(results, orient='index')
    df = df.fillna(0)  # Replace NaN with 0 for missing k-mers
    df['total_count'] = df.sum(axis=1)
    df = df.sort_values('total_count', ascending=False)

    # Calculate correlations
    genome_columns = list(files_dict.keys())
    correlation_matrix = df[genome_columns].corr()

    print(f"K-mer Comparison Results:")
    print(f"  Total unique k-mers across all genomes: {len(df)}")
    print(f"  Correlation matrix:")
    print(correlation_matrix)

    # Save results
    df.to_csv(output_file)
    print(f"Results saved to {output_file}")

    # Find genome-specific k-mers
    print("\nGenome-specific top k-mers:")
    for genome in genome_columns:
        genome_specific = df[(df[genome] > 0) & (df.drop(columns=[genome, 'total_count']).sum(axis=1) == 0)]
        print(f"  {genome}: {len(genome_specific)} unique k-mers")
        if len(genome_specific) > 0:
            print(f"    Top: {genome_specific.index[0]} ({genome_specific.iloc[0][genome]:,})")

    return df, correlation_matrix

# Usage
files_to_compare = {
    "human": "hg38.fa.gz",
    "mouse": "mm10.fa.gz",
    "zebrafish": "danRer11.fa.gz"
}

df, correlations = compare_genomes(files_to_compare)
```

## Integration Examples

### Integration with Biopython
```python
from Bio import SeqIO
from rustkmer import KmerCounter, Database
import pandas as pd

def biopython_integration(input_fasta, db_output):
    """Integrate RustKmer with Biopython for sequence analysis."""

    # Create counter
    counter = KmerCounter(k=21, canonical=True)

    # Read sequences with Biopython
    sequences = []
    lengths = []
    gc_contents = []

    print(f"Reading sequences from {input_fasta}...")
    for record in SeqIO.parse(input_fasta, "fasta"):
        sequences.append(str(record.seq))
        lengths.append(len(record.seq))

        # Calculate GC content
        seq_str = str(record.seq)
        gc_count = seq_str.count('G') + seq_str.count('C')
        gc_content = gc_count / len(seq_str) * 100
        gc_contents.append(gc_content)

        # Count k-mers for this sequence
        counter.count_string(str(record.seq))

    # Create database
    counter.save_to_database(db_output)

    # Create summary dataframe
    summary_data = {
        'sequence_id': [f"seq_{i+1}" for i in range(len(sequences))],
        'length': lengths,
        'gc_content': gc_contents
    }
    summary_df = pd.DataFrame(summary_data)

    print(f"Processed {len(sequences)} sequences")
    print(f"Average length: {np.mean(lengths):.0f} bp")
    print(f"Average GC content: {np.mean(gc_contents):.2f}%")
    print(f"Total k-mers counted: {counter.get_total_count():,}")
    print(f"Unique k-mers: {counter.get_unique_count():,}")

    return counter, summary_df

# Usage
counter, seq_summary = biopython_integration("sequences.fa", "sequences_db.rkdb")
```

### Integration with NumPy and Pandas
```python
from rustkmer import KmerCounter, Database
import numpy as np
import pandas as pd

def numpy_pandas_integration(input_files):
    """Advanced data analysis with NumPy and Pandas."""

    all_results = []

    for file_path in input_files:
        filename = file_path.split('/')[-1]
        print(f"Processing {filename}...")

        # Count k-mers
        counter = KmerCounter(k=21, canonical=True)
        counter.count_file(file_path)

        # Get top k-mers
        top_kmers = counter.get_top_kmers(500)
        kmers = np.array([kmer for kmer, count in top_kmers])
        counts = np.array([count for kmer, count in top_kmers])

        # Calculate statistics
        total_count = counter.get_total_count()
        frequencies = counts / total_count

        # Create DataFrame for this file
        df = pd.DataFrame({
            'kmer': kmers,
            'count': counts,
            'frequency': frequencies,
            'file': filename
        })

        # Add additional calculated columns
        df['gc_content'] = df['kmer'].apply(lambda x: (x.count('G') + x.count('C')) / len(x))
        df['log_count'] = np.log10(df['count'])
        df['rank'] = range(1, len(df) + 1)

        all_results.append(df)

    # Combine all results
    combined_df = pd.concat(all_results, ignore_index=True)

    # Global analysis
    print(f"\nGlobal Analysis across {len(input_files)} files:")
    print(f"  Total k-mer observations: {combined_df['count'].sum():,}")
    print(f"  Average k-mer count per file: {combined_df.groupby('file')['count'].sum().mean():.0f}")
    print(f"  Average GC content: {combined_df['gc_content'].mean():.3f}")

    # Find k-mers common to all files
    kmer_files = combined_df.groupby('kmer')['file'].nunique()
    common_kmers = kmer_files[kmer_files == len(input_files)].index
    print(f"  K-mers common to all files: {len(common_kmers)}")

    # Save results
    combined_df.to_csv('kmer_analysis_results.csv', index=False)
    print("Results saved to 'kmer_analysis_results.csv'")

    return combined_df

# Usage
input_files = ["chr1.fa.gz", "chr2.fa.gz", "chr3.fa.gz"]
results_df = numpy_pandas_integration(input_files)
```

## Performance Examples

### High-Performance Querying
```python
from rustkmer import Database
import time
import random

def benchmark_queries(db_file, num_queries=100000):
    """Benchmark query performance."""

    # Generate random k-mers for testing
    def generate_random_kmer(k=21):
        bases = 'ATCG'
        return ''.join(random.choice(bases) for _ in range(k))

    # Create test queries
    test_queries = [generate_random_kmer() for _ in range(num_queries)]

    # Load database with preloading for maximum speed
    db = Database()
    print(f"Loading database {db_file}...")
    db.load(db_file, preload=True)

    # Benchmark queries
    print(f"Benchmarking {num_queries} queries...")
    start_time = time.time()

    found_count = 0
    for query in test_queries:
        result = db.query(query)
        if result.exists:
            found_count += 1

    end_time = time.time()
    duration = end_time - start_time
    queries_per_second = num_queries / duration

    print(f"Query Performance Results:")
    print(f"  Total queries: {num_queries:,}")
    print(f"  Queries found: {found_count:,}")
    print(f"  Duration: {duration:.2f} seconds")
    print(f"  Queries per second: {queries_per_second:,.0f}")
    print(f"  Average query time: {duration/num_queries*1000:.3f} ms")

    db.close()
    return queries_per_second

# Usage
performance = benchmark_queries("genome_k21.rkdb")
```

### Memory-Efficient Processing
```python
from rustkmer import KmerCounter
import psutil
import os

def monitor_memory():
    """Monitor current memory usage."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB

def memory_efficient_processing(large_file):
    """Process large files efficiently with memory monitoring."""

    print(f"Memory before processing: {monitor_memory():.1f} MB")

    # Use conservative k-mer size for memory efficiency
    counter = KmerCounter(k=13, canonical=True)

    try:
        counter.count_file(large_file)
    except Exception as e:
        print(f"Error during processing: {e}")
        return None

    print(f"Memory after processing: {monitor_memory():.1f} MB")

    # Get results
    total = counter.get_total_count()
    unique = counter.get_unique_count()

    print(f"Processing Results:")
    print(f"  Total k-mers: {total:,}")
    print(f"  Unique k-mers: {unique:,}")
    print(f"  Memory efficiency: {total/(monitor_memory()*1024*1024):.1f} k-mers per MB")

    return counter

# Usage
# result = memory_efficient_processing("very_large_genome.fa.gz")
```

## Error Handling Examples

### Robust Error Handling
```python
from rustkmer import KmerCounter, Database, KmerError
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def robust_kmer_analysis(file_path, output_db):
    """Robust k-mer analysis with comprehensive error handling."""

    try:
        # Validate input file
        if not file_path.endswith(('.fa', '.fasta', '.fa.gz', '.fasta.gz')):
            raise ValueError(f"Invalid file format: {file_path}")

        # Create counter with validation
        counter = KmerCounter(k=21, canonical=True)
        logger.info(f"Created k-mer counter: k=21, canonical=True")

        # Process file with error handling
        try:
            logger.info(f"Processing file: {file_path}")
            counter.count_file(file_path)
            logger.info("File processing completed successfully")
        except KmerError as e:
            logger.error(f"K-mer processing error: {e}")
            return None
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return None
        except MemoryError:
            logger.error("Insufficient memory for processing")
            # Try with smaller k-mer size
            logger.info("Retrying with k=13")
            counter = KmerCounter(k=13, canonical=True)
            counter.count_file(file_path)

        # Validate results
        total_count = counter.get_total_count()
        unique_count = counter.get_unique_count()

        if total_count == 0:
            logger.warning("No k-mers were counted - possible empty or invalid file")

        # Save database with error handling
        try:
            counter.save_to_database(output_db)
            logger.info(f"Database saved to: {output_db}")
        except KmerError as e:
            logger.error(f"Database save error: {e}")
            return None

        # Return results
        results = {
            'total_count': total_count,
            'unique_count': unique_count,
            'kmer_size': 21,
            'canonical': True,
            'output_database': output_db
        }

        logger.info(f"Analysis completed successfully: {results}")
        return results

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None

# Usage
results = robust_kmer_analysis("genome.fa.gz", "genome_robust.rkdb")
if results:
    print("Analysis completed successfully!")
else:
    print("Analysis failed - see logs for details")
```

These examples demonstrate the versatility and power of the RustKmer Python API for various bioinformatics workflows. Each example includes best practices for performance, error handling, and integration with other popular Python libraries.