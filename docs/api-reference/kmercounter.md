# KmerCounter API

The `KmerCounter` class provides high-performance k-mer counting functionality for genomic sequences.

## Class Overview

```python
from rustkmer import KmerCounter

counter = KmerCounter(k=21, canonical=True)
```

## Constructor

### `__init__(k, canonical=False)`

Initialize a new k-mer counter.

**Parameters:**
- `k` (int): The length of k-mers to count
- `canonical` (bool): Whether to use canonical k-mers (forward and reverse complement are considered the same)

**Example:**
```python
# Standard k-mer counting
counter = KmerCounter(k=21)

# Canonical k-mer counting (recommended)
counter = KmerCounter(k=21, canonical=True)
```

## Methods

### `count_file(filename)`

Count k-mers from a FASTA/FASTQ file.

**Parameters:**
- `filename` (str): Path to the input file

**Example:**
```python
counter = KmerCounter(k=21, canonical=True)
counter.count_file("genome.fa.gz")
```

### `count_sequence(sequence)`

Count k-mers from a sequence string.

**Parameters:**
- `sequence` (str): DNA sequence string

**Example:**
```python
counter = KmerCounter(k=7)
counter.count_sequence("ATGCGATCGATCG")
```

### `get_total_count()`

Get the total number of k-mers counted.

**Returns:**
- `int`: Total k-mer count

**Example:**
```python
total = counter.get_total_count()
print(f"Total k-mers: {total:,}")
```

### `get_unique_count()`

Get the number of unique k-mers.

**Returns:**
- `int`: Number of unique k-mers

**Example:**
```python
unique = counter.get_unique_count()
print(f"Unique k-mers: {unique:,}")
```

### `get_top_kmers(n)`

Get the most frequent k-mers.

**Parameters:**
- `n` (int): Number of top k-mers to return

**Returns:**
- `List[Tuple[str, int]]`: List of (k-mer, count) tuples

**Example:**
```python
top_10 = counter.get_top_kmers(10)
for kmer, count in top_10:
    print(f"{kmer}: {count}")
```

### `save_to_file(filename)`

Save the k-mer database to a file.

**Parameters:**
- `filename` (str): Path to output file

**Example:**
```python
counter.save_to_file("output.rkdb")
```

### `load_from_file(filename)`

Load k-mer database from a file.

**Parameters:**
- `filename` (str): Path to input file

**Example:**
```python
counter.load_from_file("database.rkdb")
```

## Properties

### `k`

Get the k-mer size.

**Returns:**
- `int`: k-mer size

### `canonical`

Get whether canonical k-mer counting is enabled.

**Returns:**
- `bool`: Canonical counting status

### `is_empty`

Check if the counter has no k-mers.

**Returns:**
- `bool`: True if no k-mers have been counted

## Error Handling

The KmerCounter may raise the following exceptions:

- `ValueError`: Invalid k-mer size or sequence
- `FileNotFoundError`: Input file does not exist
- `IOError`: File I/O error

## Complete Example

```python
from rustkmer import KmerCounter

# Initialize counter
counter = KmerCounter(k=21, canonical=True)

# Count k-mers from file
counter.count_file("genome.fa.gz")

# Get statistics
print(f"Total k-mers: {counter.get_total_count():,}")
print(f"Unique k-mers: {counter.get_unique_count():,}")

# Get top 10 most frequent k-mers
top_kmers = counter.get_top_kmers(10)
print("\\nTop 10 k-mers:")
for kmer, count in top_kmers:
    print(f"{kmer}: {count}")

# Save database
counter.save_to_file("genome_k21.rkdb")
```

## Performance Tips

1. **Use canonical k-mers** for most applications
2. **Choose appropriate k-mer size** (k=21-31 for most genomic analysis)
3. **Enable sorting** for better query performance
4. **Use memory mapping** for very large datasets
5. **Process in batches** for large input files

