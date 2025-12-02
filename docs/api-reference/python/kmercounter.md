# KmerCounter

The `KmerCounter` class is the primary interface for k-mer counting operations in the Python API. It provides high-performance counting of k-mers from various input sources including files, strings, and streams.

## Constructor

```python
KmerCounter(k: int = 21, canonical: bool = True)
```

**Parameters:**
- `k` (int, optional): Length of k-mers to count. Default is 21.
- `canonical` (bool, optional): Whether to count canonical k-mers (lexicographically smaller of k-mer and reverse complement). Default is True.

**Example:**
```python
from rustkmer import KmerCounter

# Create counter for 21-mers with canonical counting
counter = KmerCounter(k=21, canonical=True)

# Create counter for 31-mers without canonical counting
counter = KmerCounter(k=31, canonical=False)
```

## Methods

### count_file()

Count k-mers from a file.

```python
count_file(filename: str) -> None
```

**Parameters:**
- `filename` (str): Path to the input file. Supports FASTA (.fa, .fasta, .fna) and compressed formats (.fa.gz, .fasta.gz).

**Example:**
```python
counter = KmerCounter(k=21)
counter.count_file("genome.fa.gz")
print(f"Total k-mers: {counter.get_total_count()}")
```

### count_string()

Count k-mers from a DNA/RNA string.

```python
count_string(sequence: str) -> None
```

**Parameters:**
- `sequence` (str): DNA/RNA sequence string. Only A, T, G, C, U characters are processed.

**Example:**
```python
counter = KmerCounter(k=21)
sequence = "ATCGATCGATCGATCGATCGATCG"
counter.count_string(sequence)
print(f"Total k-mers: {counter.get_total_count()}")
```

### get_total_count()

Get the total number of k-mers counted.

```python
get_total_count() -> int
```

**Returns:**
- `int`: Total count of all k-mers processed.

**Example:**
```python
counter = KmerCounter(k=21)
counter.count_file("genome.fa.gz")
total = counter.get_total_count()
print(f"Processed {total:,} k-mers")
```

### get_unique_count()

Get the number of unique k-mers found.

```python
get_unique_count() -> int
```

**Returns:**
- `int`: Number of distinct k-mers in the dataset.

**Example:**
```python
counter = KmerCounter(k=21)
counter.count_file("genome.fa.gz")
unique = counter.get_unique_count()
total = counter.get_total_count()
print(f"Unique: {unique:,}, Total: {total:,}")
print(f"Uniqueness ratio: {unique/total:.4f}")
```

### get_top_kmers()

Get the most frequent k-mers.

```python
get_top_kmers(limit: int) -> List[Tuple[str, int]]
```

**Parameters:**
- `limit` (int): Number of top k-mers to return.

**Returns:**
- `List[Tuple[str, int]]`: List of (kmer, count) tuples sorted by count (descending).

**Example:**
```python
counter = KmerCounter(k=21)
counter.count_file("genome.fa.gz")

# Get top 10 most frequent k-mers
top_10 = counter.get_top_kmers(10)
for kmer, count in top_10:
    print(f"{kmer}: {count}")
```

### save_to_database()

Save counted k-mers to a database file.

```python
save_to_database(filename: str) -> None
```

**Parameters:**
- `filename` (str): Path for the output database file (.rkdb format).

**Example:**
```python
counter = KmerCounter(k=21)
counter.count_file("genome.fa.gz")
counter.save_to_database("genome_k21.rkdb")
```

### clear()

Clear all counted k-mers and reset the counter.

```python
clear() -> None
```

**Example:**
```python
counter = KmerCounter(k=21)
counter.count_file("file1.fa")
print(f"First file: {counter.get_total_count()} k-mers")

counter.clear()
counter.count_file("file2.fa")
print(f"Second file: {counter.get_total_count()} k-mers")
```

## Performance Considerations

### Memory Usage
- Memory usage scales with the number of unique k-mers
- Use smaller k values for memory-constrained environments
- Consider canonical k-mers to reduce memory usage by approximately half

### Processing Speed
- Counting performance: ~1 million k-mers/second
- File I/O is often the bottleneck for compressed files
- Use solid-state drives for best performance with large files

### Optimal k-mer Sizes
- **k=13**: Fastest processing, lower specificity
- **k=21**: Good balance of speed and specificity (recommended)
- **k=31**: Highest specificity, slower processing

## Usage Examples

### Basic Workflow
```python
from rustkmer import KmerCounter

# Create counter
counter = KmerCounter(k=21, canonical=True)

# Process file
counter.count_file("genome.fa.gz")

# Get statistics
total = counter.get_total_count()
unique = counter.get_unique_count()

print(f"Total k-mers: {total:,}")
print(f"Unique k-mers: {unique:,}")
print(f"Top k-mers:")
for kmer, count in counter.get_top_kmers(5):
    print(f"  {kmer}: {count}")

# Save for later use
counter.save_to_database("genome_k21.rkdb")
```

### Batch Processing
```python
from rustkmer import KmerCounter
import glob

files = glob.glob("chromosome_*.fa.gz")
counter = KmerCounter(k=21, canonical=True)

for file in files:
    print(f"Processing {file}...")
    counter.count_file(file)
    print(f"  Total so far: {counter.get_total_count():,}")

print(f"Final total: {counter.get_total_count():,}")
counter.save_to_database("all_chromosomes_k21.rkdb")
```

### Analysis Pipeline
```python
from rustkmer import KmerCounter
import matplotlib.pyplot as plt

# Count k-mers
counter = KmerCounter(k=21)
counter.count_file("genome.fa.gz")

# Get frequency distribution
top_kmers = counter.get_top_kmers(1000)
counts = [count for kmer, count in top_kmers]

# Plot distribution
plt.figure(figsize=(10, 6))
plt.hist(counts, bins=50, log=True)
plt.xlabel('K-mer Count')
plt.ylabel('Number of K-mers')
plt.title('K-mer Frequency Distribution')
plt.show()

# Print statistics
print(f"Most common k-mer: {top_kmers[0][0]} ({top_kmers[0][1]} occurrences)")
print(f"Median of top 1000: {sorted(counts)[500]}")
```

## Error Handling

```python
from rustkmer import KmerCounter, KmerError

counter = KmerCounter(k=21)

try:
    counter.count_file("nonexistent.fa")
except KmerError as e:
    print(f"File error: {e}")

try:
    counter.count_string("INVALID_SEQUENCE_WITH_X")
except KmerError as e:
    print(f"Sequence error: {e}")
```

## Integration with Other Tools

### Pandas Integration
```python
import pandas as pd
from rustkmer import KmerCounter

counter = KmerCounter(k=21)
counter.count_file("genome.fa.gz")

# Create DataFrame of top k-mers
top_kmers = counter.get_top_kmers(100)
df = pd.DataFrame(top_kmers, columns=['kmer', 'count'])
df['frequency'] = df['count'] / counter.get_total_count()

# Save to CSV
df.to_csv('top_kmers.csv', index=False)
```

### NumPy Integration
```python
import numpy as np
from rustkmer import KmerCounter

counter = KmerCounter(k=21)
counter.count_file("genome.fa.gz")

# Get k-mer counts as arrays
top_kmers = counter.get_top_kmers(1000)
kmers = np.array([kmer for kmer, count in top_kmers])
counts = np.array([count for kmer, count in top_kmers])

# Calculate statistics
mean_count = np.mean(counts)
median_count = np.median(counts)
std_count = np.std(counts)

print(f"Count statistics - Mean: {mean_count:.2f}, Median: {median_count}, Std: {std_count:.2f}")
```

## Thread Safety

Multiple `KmerCounter` instances can be used safely in parallel:

```python
import threading
from rustkmer import KmerCounter

def process_file(filename):
    counter = KmerCounter(k=21)
    counter.count_file(filename)
    return counter.get_total_count()

files = ["chr1.fa", "chr2.fa", "chr3.fa"]
threads = []

for file in files:
    thread = threading.Thread(target=process_file, args=(file,))
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()

print("All files processed in parallel")
```

## Best Practices

1. **Choose appropriate k-mer size**: Balance between specificity and performance
2. **Use canonical k-mers**: Reduces memory usage and improves matching
3. **Process large files in chunks**: For very large genomes, consider processing chromosome by chromosome
4. **Save intermediate results**: Use `save_to_database()` to preserve work
5. **Handle exceptions**: Always wrap operations in try-catch blocks
6. **Monitor memory usage**: Large genomes may require substantial RAM for unique k-mers