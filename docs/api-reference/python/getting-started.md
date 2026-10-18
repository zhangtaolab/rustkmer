<!-- generated-by: gsd-doc-writer -->
# Getting Started

This guide will help you get started with the rustkmer Python API (`pyrustkmer`), from installation to your first k-mer analysis.

## Installation

### Requirements

- Python >= 3.11
- `numpy >= 1.21` (installed automatically as a dependency)
- For building from source: a Rust 1.80+ stable toolchain and `maturin`

### Install from PyPI

The easiest way to install the bindings is from PyPI:

```bash
pip install pyrustkmer
```

### Build from Source

The Python extension lives in the `pyo3/` directory of the repository and is built with `maturin`:

```bash
git clone https://github.com/rustkmer/rustkmer.git
cd rustkmer/pyo3

python -m venv .venv
source .venv/bin/activate

pip install maturin
maturin develop --release
```

`pip install .` run from the `pyo3/` directory also works — `maturin` is the declared PEP 517 build backend.

### Verify Installation

The module does not export a `__version__` attribute; verify the installation by running a tiny counting round-trip:

```python
from pyrustkmer import PyCounter

counter = PyCounter(3, canonical=True)
counter.add_sequence("ATGCGATGCATGCGATGCAT")

stats = counter.get_stats()
print(stats)
# PyCounterStats(total_kmers=18, unique_kmers=..., kmer_length=3, canonical_mode=True, memory_usage=...)
```

## Your First K-mer Analysis

Let's create a simple k-mer database and perform queries.

### 1. Create Sample Data

Create a file named `sample.fasta`:

```fasta
>seq1
ATCGATCGATCGATCGATCGATCGATCGATCGATCG
>seq2
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
>seq3
TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT
```

### 2. Count K-mers and Build a Database

```python
from pyrustkmer import PyCounter

# Create a k-mer counter with k=31
counter = PyCounter(31, canonical=True)

print("Counting k-mers...")
counter.add_from_fasta("sample.fasta")

stats = counter.get_stats()
print(f"Total k-mers processed: {stats.total_kmers:,}")
print(f"Unique k-mers: {stats.unique_kmers:,}")

print("Creating database...")
counter.save_database("sample.rkdb")
print("Database created successfully!")
```

### 3. Query the Database

```python
from pyrustkmer import PyDatabase, LoadMode

# Open the database in preload mode (fastest queries)
db = PyDatabase("sample.rkdb", LoadMode.Preload)

# Query a k-mer — the string length must equal the database k-mer size
kmer = "ATCGATCGATCGATCGATCGATCGATCGATC"
result = db.query_exact(kmer)

print(f"Query k-mer: {kmer}")
print(f"Found: {result.found}")
print(f"Count: {result.count}")

# Get database statistics
stats = db.get_stats()
print(f"\nDatabase Statistics:")
print(f"  K-mer size: {stats.kmer_size}")
print(f"  Unique k-mers: {stats.unique_kmers:,}")
print(f"  Total k-mers: {stats.total_kmers:,}")
print(f"  File size: {stats.file_size:,} bytes")
print(f"  Canonical: {stats.canonical}")
```

## Core Concepts

### K-mer Size

The k-mer size must be between 1 and 64 (k-mers are encoded in a single `u128`). It affects specificity and database size:

- **Small k (15-21)**: More matches, less specific, good for short reads
- **Medium k (25-31)**: Good balance for most applications
- **Large k (51-64)**: Highly specific, useful for long sequences

```python
# Different k-mer sizes for different use cases
counter_small = PyCounter(15)   # For metagenomics
counter_medium = PyCounter(31)  # General purpose
counter_large = PyCounter(51)   # For long sequences
```

### Canonical K-mers

Canonical k-mers store each k-mer and its reverse complement only once, roughly halving the number of unique k-mers:

```python
# With canonical k-mers (recommended)
counter_canonical = PyCounter(31, canonical=True)

# Without canonical k-mers (stores both strands)
counter_stranded = PyCounter(31, canonical=False)
```

### Database Load Modes

`PyDatabase` requires an explicit load mode as its second argument:

| Mode | Behavior | Best for |
|------|----------|----------|
| `LoadMode.Preload` | All k-mers cached in memory | Fastest repeated queries |
| `LoadMode.MemoryMapped` | Direct file I/O, entry access by index | Large databases, bounded memory |
| `LoadMode.Lazy` | Sorted index with binary-search lookups | Large databases, slower queries |

```python
from pyrustkmer import PyDatabase, LoadMode

db = PyDatabase("sample.rkdb", LoadMode.Preload)
```

`PyDatabase` does not implement a context manager. Databases hold no locks or background resources — simply drop the reference (or let it go out of scope) when you are done with it.

## Common Operations

### Multiple Input Files

Call `add_from_fasta` / `add_from_fastq` once per file on the same counter. Both accept plain, `.gz`, `.bz2`, and `.xz` compressed inputs:

```python
from pyrustkmer import PyCounter

counter = PyCounter(31, canonical=True)

# Process multiple files into one counter
for path in ["file1.fasta", "file2.fasta", "reads.fastq.gz"]:
    counter.add_from_fasta(path) if path.endswith((".fasta", ".fa")) else counter.add_from_fastq(path)

# Save the combined database
counter.save_database("combined.rkdb")
```

### Batch Queries

Query many k-mers at once with `query_exact_batch`, which returns a dictionary keyed by the queried k-mer:

```python
kmer_list = [
    "ATCGATCGATCGATCGATCGATCGATCGATC",
    "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT",
    "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
]

results = db.query_exact_batch(kmer_list)

for kmer, result in results.items():
    status = "found" if result.found else "missing"
    print(f"{kmer}: {status} (count: {result.count})")
```

### Database Export

Use the built-in exporters instead of manual iteration for large databases:

```python
# Export to a tab-separated text file (kmer<TAB>count per line)
n = db.export_to_file("kmer_counts.tsv", limit=1000)
print(f"Exported {n} k-mers")

# Export to CSV (with header row) or JSON
db.export_to_csv("kmer_counts.csv")
db.export_to_json("kmer_counts.json")

# Paginate in memory with decoded k-mer sequences
first_100 = db.export_all_kmers(limit=100, offset=0)
for r in first_100:
    print(f"{r.kmer}: {r.count}")
```

Note: `db.dump()` returns k-mers as hexadecimal strings of their encoded `u128` values. Use `export_all_kmers()` when you need the decoded nucleotide sequences.

## Fuzzy Queries

Find similar k-mers with `PyFuzzyQuery`. The `max_mutations` argument is required — there is no default:

```python
from pyrustkmer import PyDatabase, PyFuzzyQuery, LoadMode

db = PyDatabase("sample.rkdb", LoadMode.Preload)
fuzzy = PyFuzzyQuery(db)

query_kmer = "ATCGATCGATCGATCGATCGATCGATCGATC"

# Exact query
exact_result = db.query_exact(query_kmer)
print(f"Exact count: {exact_result.count}")

# Fuzzy query: allow up to 1 mutation
fuzzy_result = fuzzy.query_fuzzy(query_kmer, max_mutations=1)
print(f"Total matches: {fuzzy_result.total_matches}")

# Inspect the matches
for match in fuzzy_result.matches:
    print(f"  {match.kmer}: {match.count} (distance={match.distance}, type={match.match_type})")

# Most frequent matches first
for match in fuzzy_result.get_top_matches(5):
    print(f"  {match.kmer}: {match.count}")
```

Fuzzy patterns may contain `N` wildcard characters (in addition to `A`, `T`, `C`, `G`) and must be exactly the database k-mer size long. For position-specific mutation constraints, see `query_fuzzy_position(pattern, max_mutations, position_mutations)` on the [Fuzzy Queries](../fuzzyquery.md) page.

## Error Handling

The bindings raise standard Python built-in exceptions. The most common ones:

| Exception | Raised when |
|-----------|-------------|
| `FileNotFoundError` | The database file passed to `PyDatabase` does not exist |
| `ValueError` | Invalid arguments: k-mer size outside 1-64, query length mismatch, invalid characters, unwritable output |
| `RuntimeError` | A query or merge operation failed internally |
| `PermissionError` | An export output file cannot be created or written |

```python
from pyrustkmer import PyDatabase, LoadMode

try:
    db = PyDatabase("nonexistent.rkdb", LoadMode.Preload)
except FileNotFoundError as e:
    print(f"Database file not found: {e}")

try:
    db = PyDatabase("sample.rkdb", LoadMode.Preload)
    result = db.query_exact("ATG")  # wrong length for k=31
except ValueError as e:
    print(f"Invalid query: {e}")
```

The module also exports a single library error class, `pyrustkmer.RustKmerError`, with `message` and `error_type` attributes.

## Performance Tips

### 1. Use an Appropriate K-mer Size

```python
# For short reads (<100 bp)
k = 21

# For long reads (>1000 bp)
k = 31

# For very long sequences (>10 kb)
k = 51
```

### 2. Enable Canonical Mode

```python
# Roughly halves the number of unique k-mers stored
counter = PyCounter(31, canonical=True)
```

### 3. Use Batch Operations

```python
# One call instead of a Python loop over query_exact
results = db.query_exact_batch(kmer_list)
```

### 4. Process Large Datasets Efficiently

```python
# Stream exports to disk instead of materializing everything in Python
def progress(current, total):
    print(f"Progress: {current}/{total}")

n = db.export_to_file("all_kmers.tsv", progress_callback=progress)
print(f"Wrote {n:,} k-mers")
```

File-based counting (`add_from_fasta` / `add_from_fastq`) releases the GIL and counts in parallel across a Rayon thread pool. Control the thread count at construction time:

```python
counter = PyCounter(31, canonical=True, threads=8)
```

## Integration with Other Libraries

### Pandas Integration

```python
import pandas as pd

rows = [
    {"kmer": r.kmer, "count": r.count}
    for r in db.export_all_kmers(limit=10000)
]
df = pd.DataFrame(rows)

print(f"Total k-mers loaded: {len(df)}")
print(f"Mean count: {df['count'].mean():.1f}")
print(f"Max count: {df['count'].max()}")
```

Alternatively, export to CSV and read it back:

```python
db.export_to_csv("kmer_counts.csv")
df = pd.read_csv("kmer_counts.csv")
```

### NumPy Integration

```python
import numpy as np

counts = np.array([r.count for r in db.export_all_kmers(limit=10000)])

print(f"Mean: {np.mean(counts):.1f}")
print(f"Median: {np.median(counts):.1f}")
print(f"Std dev: {np.std(counts):.1f}")
print(f"95th percentile: {np.percentile(counts, 95):.1f}")
```

## Next Steps

- [Database Operations](../database.md) - `PyDatabase` reference
- [K-mer Counter](../kmercounter.md) - `PyCounter` reference
- [Fuzzy Queries](../fuzzyquery.md) - Advanced fuzzy searching
- [Query Results](../query.md) - `PyQueryResult` reference
- [Database Stats](../stats.md) - `PyDatabaseStats` reference
- [Examples](examples.md) - Comprehensive use case examples
- [Tutorials](../../tutorials/) - Step-by-step tutorials for specific workflows

## Complete Example

Here's a complete example that ties everything together:

```python
#!/usr/bin/env python3
"""Complete rustkmer example: create, analyze, and query a k-mer database."""

import os
import tempfile

from pyrustkmer import PyCounter, PyDatabase, PyFuzzyQuery, LoadMode


def main():
    sequences = [
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",
        "ATCGATCGATCGATCGATCGATCGATCGATCGATGG",  # 1 mutation vs seq1
        "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
        "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".fasta", delete=False) as f:
        for i, seq in enumerate(sequences):
            f.write(f">seq_{i + 1}\n{seq}\n")
        fasta_file = f.name

    db_path = "example.rkdb"

    try:
        # 1. Create the k-mer database
        print("Creating k-mer database...")
        counter = PyCounter(31, canonical=True)
        counter.add_from_fasta(fasta_file)
        counter.save_database(db_path)

        cstats = counter.get_stats()
        print(f"  Total k-mers counted: {cstats.total_kmers:,}")
        print(f"  Unique k-mers: {cstats.unique_kmers:,}")

        # 2. Analyze the database
        print("Analyzing database...")
        db = PyDatabase(db_path, LoadMode.Preload)
        stats = db.get_stats()
        print(f"  K-mer size: {stats.kmer_size}")
        print(f"  Unique k-mers: {stats.unique_kmers:,}")
        print(f"  File size: {stats.file_size:,} bytes")

        # 3. Query the database
        print("\nQuerying database...")
        query_kmer = sequences[0][:31]
        result = db.query_exact(query_kmer)
        print(f"  Query: {query_kmer}")
        print(f"  Found: {result.found} (count: {result.count})")

        # 4. Fuzzy query
        print("\nFuzzy query...")
        fuzzy = PyFuzzyQuery(db)
        fuzzy_result = fuzzy.query_fuzzy(query_kmer, max_mutations=2)
        print(f"  Total matches: {fuzzy_result.total_matches}")
        for match in fuzzy_result.get_top_matches(5):
            print(f"  {match.kmer}: {match.count} (distance={match.distance})")

        # 5. Export
        print("\nExporting data...")
        n = db.export_to_file("kmer_counts.tsv", limit=1000)
        print(f"  Exported {n} k-mers to kmer_counts.tsv")

        print("\nExample completed successfully!")

    finally:
        os.unlink(fasta_file)
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    main()
```

## Troubleshooting

### Common Issues

1. **`ImportError: No module named pyrustkmer`** — the extension was not built into the active environment. Run `maturin develop --release` from the `pyo3/` directory of the repository, and confirm your interpreter is Python >= 3.11.
2. **`FileNotFoundError`** — check the database path passed to `PyDatabase`.
3. **`ValueError: K-mer length ... does not match database k-mer size ...`** — query strings must be exactly `db.kmer_size` characters long.
4. **`ValueError: Invalid k-mer size`** — `PyCounter` accepts k-mer lengths from 1 to 64 only.
5. **Memory pressure on large databases** — open with `LoadMode.Lazy` or `LoadMode.MemoryMapped`, and prefer `export_to_file` over materializing results in Python.

### Getting Help

- Check the [examples](../../examples/) for complete working code
- Review the [API reference](index.md) for detailed documentation
- Look at the [tutorials](../../tutorials/) for specific workflows
- Report issues on the project GitHub repository
