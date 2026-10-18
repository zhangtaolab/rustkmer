<!-- generated-by: gsd-doc-writer -->
# KmerCounter API

The `PyCounter` class provides high-performance k-mer counting functionality for genomic sequences. It is the Python surface of the Rust `KmerCounter` and writes the same `.rkdb` format the CLI produces.

## Class Overview

```python
from pyrustkmer import PyCounter

counter = PyCounter(21, canonical=True)
```

## Constructor

### `PyCounter(kmer_length, canonical=False, initial_capacity=1000, threads=None)`

Initialize a new k-mer counter.

**Parameters:**
- `kmer_length` (int): The length of k-mers to count (1–64)
- `canonical` (bool): Whether to count canonical k-mers (forward and reverse complement are considered the same; default `False`)
- `initial_capacity` (int): Initial hash table capacity (default 1000)
- `threads` (Optional[int]): Number of rayon worker threads for parallel counting (default `None` = all available cores; values `< 1` are rejected)

**Raises:**
- `ValueError`: If `kmer_length` is not between 1 and 64, or if `threads` is less than 1

**Example:**
```python
# Standard k-mer counting
counter = PyCounter(21)

# Canonical k-mer counting (recommended), 8 worker threads
counter = PyCounter(21, canonical=True, threads=8)

# Canonical counting with explicit initial capacity
counter = PyCounter(31, True, 100_000)
```

## Methods

### `add_kmer(kmer)`

Add a single k-mer to the counter.

**Parameters:**
- `kmer` (str): K-mer string; must be exactly `kmer_length` characters from `A`, `C`, `G`, `T`

**Raises:**
- `ValueError`: If the k-mer has the wrong length, contains invalid characters, or the count would overflow

**Example:**
```python
counter = PyCounter(21, canonical=True)
counter.add_kmer("ATGCGATGCATGCGATGCAT")
```

### `add_sequence(sequence)`

Extract and count all k-mers from a sequence string.

**Parameters:**
- `sequence` (str): DNA sequence string; whitespace and invalid characters (e.g. `N`) are filtered out, and k-mers spanning them are skipped

**Notes:**
- If the cleaned sequence is shorter than `kmer_length`, the call is a no-op

**Example:**
```python
counter = PyCounter(7)
counter.add_sequence("ATGCGATCGATCG")
```

### `add_from_fasta(file_path)`

Count k-mers from a FASTA file. The GIL is released during processing and the work is parallelized across the rayon thread pool.

**Parameters:**
- `file_path` (str): Path to the FASTA file; gzip (`.gz`), bzip2 (`.bz2`), and xz (`.xz`) compression are detected transparently

**Raises:**
- `ValueError`: If the file cannot be read

**Example:**
```python
counter = PyCounter(21, canonical=True)
counter.add_from_fasta("genome.fa.gz")
```

### `add_from_fastq(file_path)`

Count k-mers from a FASTQ file (sequence lines only; headers and quality strings are ignored). Compression support and GIL behavior match `add_from_fasta`.

**Parameters:**
- `file_path` (str): Path to the FASTQ file

**Raises:**
- `ValueError`: If the file cannot be read

**Example:**
```python
counter = PyCounter(21, canonical=True)
counter.add_from_fastq("reads.fastq.gz")
```

### `get_stats()`

Get statistics for the counter.

**Returns:**
- `PyCounterStats`: Object with `total_kmers`, `unique_kmers`, `kmer_length`, `canonical_mode`, and `memory_usage` (estimated bytes) attributes

**Example:**
```python
stats = counter.get_stats()
print(f"Total k-mers: {stats.total_kmers:,}")
print(f"Unique k-mers: {stats.unique_kmers:,}")
```

### `get_count(kmer)`

Get the count for a specific k-mer.

**Parameters:**
- `kmer` (str): K-mer string of exactly `kmer_length` characters

**Returns:**
- `int`: Count of the k-mer (0 if not found)

**Raises:**
- `ValueError`: If the k-mer has the wrong length or contains invalid characters

**Example:**
```python
count = counter.get_count("ATGCGATGCATGCGATGCAT")
print(f"K-mer appears {count} times")
```

### `get_all_counts()`

Get all k-mer counts as a dictionary.

**Returns:**
- `Dict[str, int]`: Mapping of k-mer strings (canonical form when canonical mode is enabled) to counts

**Notes:**
- May use significant memory for large counters

**Example:**
```python
counts = counter.get_all_counts()
for kmer, count in counts.items():
    print(f"{kmer}: {count}")
```

### `save_database(file_path)`

Save the counted k-mers as a sorted RKDB database file, ready for querying with `PyDatabase`.

**Parameters:**
- `file_path` (str): Path to the output `.rkdb` file

**Raises:**
- `ValueError`: If the counter is empty ("Cannot save empty database") or the file cannot be written

**Example:**
```python
counter.save_database("output.rkdb")

# Load it back for querying
from pyrustkmer import PyDatabase, LoadMode
db = PyDatabase("output.rkdb", LoadMode.Preload)
```

### `reset()`

Clear all counted k-mers, keeping the configuration.

**Example:**
```python
counter.reset()
```

### `is_empty()`

Check if the counter has no k-mers.

**Returns:**
- `bool`: `True` if no k-mers have been counted

## Properties

### `kmer_length`

Get the k-mer size (int).

### `canonical`

Get whether canonical k-mer counting is enabled (bool).

## PyCounterStats

Returned by `get_stats()`. All attributes are read-only properties:

| Attribute | Type | Description |
|-----------|------|-------------|
| `total_kmers` | `int` | Total number of k-mers processed |
| `unique_kmers` | `int` | Number of unique k-mers found |
| `kmer_length` | `int` | K-mer length |
| `canonical_mode` | `bool` | Whether canonical mode is enabled |
| `memory_usage` | `int` | Estimated memory usage in bytes |

## Error Handling

The counter may raise the following exceptions:

- `ValueError`: Invalid k-mer size (must be 1–64), invalid thread count, k-mer length mismatch, invalid characters, empty-counter save, or unreadable input file
- `RuntimeError`: Not raised by `PyCounter` itself (reserved for query-engine failures)

## Complete Example

```python
from pyrustkmer import PyCounter, PyDatabase, LoadMode

# Initialize counter
counter = PyCounter(21, canonical=True, threads=8)

# Count k-mers from file
counter.add_from_fasta("genome.fa.gz")

# Get statistics
stats = counter.get_stats()
print(f"Total k-mers: {stats.total_kmers:,}")
print(f"Unique k-mers: {stats.unique_kmers:,}")

# Look up a single k-mer
count = counter.get_count("ATGCGATGCATGCGATGCAT")
print(f"Count: {count}")

# Save database
counter.save_database("genome_k21.rkdb")

# Query the saved database
db = PyDatabase("genome_k21.rkdb", LoadMode.Preload)
result = db.query_exact("ATGCGATGCATGCGATGCAT")
print(f"In database: found={result.found}, count={result.count}")
```

## Performance Tips

1. **Use canonical k-mers** for most applications (halves the key space)
2. **Choose appropriate k-mer size** (k=21–31 for most genomic analysis; k up to 64 is supported)
3. **Set `threads=`** explicitly when running alongside other workloads; the default uses all available cores
4. **Pre-size with `initial_capacity`** when the approximate unique k-mer count is known in advance
5. **File-based counting releases the GIL** — use `add_from_fasta`/`add_from_fastq` rather than many `add_sequence` calls for large inputs
