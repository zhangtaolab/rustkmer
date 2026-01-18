# Core Concepts

Understanding the key concepts behind RustKmer will help you use it effectively.

## What are K-mers?

A k-mer is a substring of length k from a longer biological sequence. For example, in the sequence "ATCGATCG":

- The 3-mers (k=3) are: "ATC", "TCG", "CGA", "GAT", "ATC", "TCG"
- k-mers are the fundamental building blocks used in genomic analysis

### Why K-mers Matter

1. **Genome Assembly**: k-mers help reconstruct genomes from short reads
2. **Metagenomics**: Identify species in environmental samples
3. **Variant Detection**: Find mutations and variations
4. **Sequence Similarity**: Compare genomic sequences efficiently

## Canonical K-mers

In DNA, sequences come in complementary pairs. A canonical k-mer represents both strands:

```
Sequence:    ATCGATCG
Complement:  TAGCTAGC
Canonical:   ATCGATCG (lexicographically smaller)
```

**Benefits of using canonical k-mers:**
- Reduces memory usage by ~50%
- Treats DNA as double-stranded
- Standard practice in genomics

## The RKDB Database Format

RustKmer uses a custom binary format (RKDB) for storing k-mer data:

### Structure
- **Header**: Metadata (k-size, canonical mode, counts)
- **Index**: Fast lookup structure
- **Data**: Compressed k-mer and count pairs

### Advantages
- **Fast queries**: Milliseconds even for billions of k-mers
- **Memory efficient**: Stores only necessary information
- **Portable**: Cross-platform compatible
- **Compressed**: Minimizes disk space

## Performance Characteristics

### Speed
- **Counting**: Up to 100,000+ k-mers/second
- **Queries**: 10,000-100,000 queries/second
- **Scaling**: Near-linear with thread count

### Memory Usage
- **Counting**: ~1KB per 1000 unique k-mers
- **Database**: 12-16 bytes per unique k-mer
- **Queries**: <100MB overhead even for large databases

## Key Operations

### 1. K-mer Counting

```python
from pyrustkmer import KmerCounter

# Create counter
counter = PyCounter(31, canonical=True)

# Count from file
counter.add_from_fasta("genome.fa")

# Get statistics
total = counter.get_stats().total_kmers)  # Total k-mers counted
unique = counter.get_unique_count()  # Unique k-mers
```

### 2. Database Queries

```python
from pyrustkmer import Database

db = PyDatabase("database.rkdb", LoadMode.Preload)
db.load("genome.rkdb")

# Exact match
count = db.query_exact("ATCGATCGATCGATCGATCGATC")

# Batch queries (more efficient)
results = db.query_multiple(["ATCG", "GCTA", "CCCC"])
```

### 3. Fuzzy Searching

Find k-mers with patterns or mismatches:

```python
from pyrustkmer import FuzzyQuery

fq = FuzzyQuery()
fq.load("genome.rkdb")

# Wildcard search (N = any base)
results = fuzzy.query_fuzzy("AATN")  # Matches AATA, AATC, AATG, AATT

# Mismatch search
results = fuzzy.query_fuzzy("ATCGATCG", max_mismatches=2)
```

## Choosing K-mer Size

The choice of k affects results:

| k-size | Use Case | Characteristics |
|--------|----------|----------------|
| 15-21  | Query/Match | Good for exact matches, high sensitivity |
| 21-31  | General    | Balance between specificity and sensitivity |
| 31+    | Species ID | High specificity, good for unique identification |

### Guidelines
- **Short reads** (100bp): Use k=15-21
- **Long reads** (>1kb): Use k=21-31
- **Species identification**: Use k=31 or larger
- **Assembly**: Vary k based on read length

## Thread Usage

RustKmer uses multiple threads for performance:

```python
# Automatic thread count (uses all available cores)
counter = PyCounter(31)

# Specify thread count
counter = PyCounter(31, threads=8)
```

### When to Use Multiple Threads
- **Large files** (>10MB): Benefits from parallelization
- **Many small files**: Process multiple files in parallel
- **Complex queries**: Fuzzy search benefits from threads

### When to Use Single Thread
- **Small files** (<1MB): Overhead outweighs benefits
- **Memory-constrained**: Fewer threads use less memory
- **Debugging**: Easier to trace issues

## Memory Optimization

### Canonical Mode
```python
# Halves memory usage for DNA
counter = PyCounter(31, canonical=True)
```

### Memory Mapping
```python
# For databases larger than RAM
db = PyDatabase("database.rkdb", LoadMode.Preload)
db.load("huge_db.rkdb", memory_mapped=True)
```

### Progressive Counting
```python
# Process files incrementally
for file in file_list:
    counter = PyCounter(31)
    counter.add_from_fasta(file)
    # Save intermediate results if needed
```

## File Formats

### Supported Input Formats
- **FASTA**: `.fa`, `.fasta`, `.fna`
- **FASTQ**: `.fq`, `.fastq`
- **Compressed**: Any of the above with `.gz`

### Automatic Detection
RustKmer automatically detects file format from extension:

```python
# All these work automatically
counter.add_from_fasta("genome.fa")
counter.add_from_fasta("reads.fq")
counter.add_from_fasta("data.fa.gz")
counter.add_from_fasta("sequences.fastq.gz")
```

## Error Handling

Common errors and how to handle them:

```python
from pyrustkmer import KmerCounter, SequenceError, DatabaseError

try:
    counter = PyCounter(31)
    counter.add_from_fasta("nonexistent.fa")
except SequenceError as e:
    print(f"File error: {e}")
except DatabaseError as e:
    print(f"Database error: {e}")
```

### Common Issues
1. **Invalid k-mer size**: Must be 1-127
2. **File not found**: Check file path
3. **Invalid characters**: Non-ACGT characters in sequences
4. **Memory limits**: Use canonical mode or smaller k

## Performance Tips

1. **Choose appropriate k**: Balance specificity and memory
2. **Use canonical mode**: For DNA sequences
3. **Batch operations**: More efficient than individual operations
4. **Compress input files**: Faster I/O
5. **Use SSD storage**: Improves I/O performance

## Integration Patterns

### With Pandas
```python
import pandas as pd
from pyrustkmer import Database

db = PyDatabase("database.rkdb", LoadMode.Preload)
db.load("data.rkdb")

# Query from DataFrame
df = pd.read_csv("queries.csv")
df['count'] = df['sequence'].apply(db.query)
```

### With Biopython
```python
from Bio import SeqIO
from pyrustkmer import KmerCounter

counter = PyCounter(21)
for record in SeqIO.parse("sequences.fasta", "fasta"):
    counter.add_sequence(str(record.seq))
```

### With NumPy
```python
import numpy as np
from pyrustkmer import Database

db = PyDatabase("database.rkdb", LoadMode.Preload)
sequences = np.array(['ATCG', 'GCTA', 'CCCC'])
counts = np.array([db.query_exact(seq) for seq in sequences])
```

## Understanding the Output

### K-mer Counts
- **Total count**: Sum of all k-mers (including duplicates)
- **Unique count**: Number of distinct k-mers
- **Query result**: Exact occurrence count

### Database Statistics
```python
stats = db.get_stats()
# Returns:
# {
#     'total_kmers': 1234567,      # Total occurrences
#     'unique_kmers': 98765,       # Distinct k-mers
#     'k_size': 21,                # K-mer length used
#     'canonical_mode': True,       # Whether canonical k-mers
#     'file_size': 1048576          # Database file size in bytes
# }
```

## Best Practices

1. **Always validate k**: Ensure appropriate for your data
2. **Use canonical mode**: Default choice for DNA
3. **Batch operations**: More efficient than individual calls
4. **Handle errors gracefully**: Especially for file operations
5. **Monitor memory**: With very large datasets
6. **Choose threads wisely**: Based on workload and system resources