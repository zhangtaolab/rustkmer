<!-- generated-by: gsd-doc-writer -->
# Basic Usage

This guide walks through the fundamental RustKmer operations with both the Rust CLI and the Python API. Every command and snippet below was verified against `rustkmer` 0.5.0 and the `pyrustkmer` module built from `pyo3/src/`.

## Prerequisites

### Rust CLI

- Rust 1.80+ stable toolchain
- Build the binary: `cargo build --release` (produces `target/release/rustkmer`)

### Python API

- Python 3.11+ (the extension targets `>=3.11` per `pyo3/pyproject.toml`)
- Install the module from the repository: `cd pyo3 && maturin develop --release`
- Verify: `python -c "import pyrustkmer; print(pyrustkmer.PyCounter)"`

## Quick Start

### Option 1: Python API

```python
from pyrustkmer import PyCounter, PyDatabase, LoadMode

# 1. Count k-mers from a FASTA file and save a .rkdb database
counter = PyCounter(11, canonical=False)   # k must be 1-64
counter.add_from_fasta("demo.fa")          # .gz / .bz2 / .xz also accepted
counter.save_database("demo.rkdb")

# 2. Open the database and query a k-mer
db = PyDatabase("demo.rkdb", LoadMode.Preload)
result = db.query_exact("ATCGATCGATC")
print(result.count)   # 16
print(result.found)   # True
```

### Option 2: Rust CLI

```bash
# Count k-mers (input files come after -i; output with -o)
rustkmer count -k 11 -i demo.fa -o demo.rkdb --threads 4

# Query two k-mers (database path is positional, k-mers follow it)
rustkmer query demo.rkdb ATCGATCGATC GCTAGCTAGCT
# ATCGATCGATC	16

# Show database statistics
rustkmer stats demo.rkdb
```

## 1. Creating a K-mer Database

### Python API

```python
from pyrustkmer import PyCounter

# From one or more files: call add_from_* once per file
counter = PyCounter(31, canonical=True)
counter.add_from_fasta("file1.fasta")
counter.add_from_fasta("file2.fasta")   # counts accumulate
counter.add_from_fastq("reads.fastq.gz")  # gz/bz2/xz handled transparently
counter.save_database("combined.rkdb")

# From in-memory sequences
counter = PyCounter(21)
counter.add_sequence("ATCGATCGATCGATCGATCGATCGATCGATCGATCG")
counter.add_kmer("ATCGATCGATCGATCGATCGAT")   # must be exactly k long
counter.save_database("from_strings.rkdb")

stats = counter.get_stats()
print(stats.total_kmers, stats.unique_kmers, stats.memory_usage)
```

Notes:

- `PyCounter(kmer_length, canonical=False, initial_capacity=1000, threads=None)` — `threads=None` uses all cores; values below 1 raise `ValueError`.
- `save_database` writes a sorted `.rkdb` file and raises `ValueError` if the counter is empty.
- Non-ACGT characters (e.g. `N`) are skipped; k-mers spanning them are not counted.

### Rust CLI

```bash
# Basic counting
rustkmer count -k 31 -i input.fasta -o database.rkdb

# Multiple input files in one command
rustkmer count -k 25 -i file1.fasta file2.fasta file3.fasta -o combined.rkdb

# Canonical mode (merge forward/reverse-complement), 8 threads, quiet
rustkmer count -k 31 -i input.fasta -o database.rkdb --canonical --threads 8 --quiet

# Count every file in a directory (recursive by default)
rustkmer count -k 31 -d reads_dir/ -o all.rkdb

# Count threshold filters
rustkmer count -k 31 -i input.fasta -o filtered.rkdb --min-count 2 --max-count 1000
```

Useful `count` flags: `-C/--canonical`, `--threads N`, `-L/--min-count`, `-U/--max-count`, `--format text` (instead of binary), `--no-sort` (faster counting, unsorted database), `--quiet`, `--verbose`.

## 2. Querying K-mers

### Python API

```python
from pyrustkmer import PyDatabase, LoadMode

db = PyDatabase("database.rkdb", LoadMode.Preload)

# Single lookup -> PyQueryResult(kmer, count, found)
result = db.query_exact("ATCGATCGATC")
print(result.found, result.count)

# Batch lookup -> dict of input string -> PyQueryResult
results = db.query_exact_batch(["ATCGATCGATC", "TTTTTTTTTTT"])
for kmer, r in results.items():
    print(kmer, r.count)

# Existence check
print(db.exists("ATCGATCGATC"))
```

The query string must match the database k-mer size exactly and contain only A/T/C/G, otherwise a `ValueError` is raised. In canonical databases the lookup canonicalizes the query for you.

### Rust CLI

```bash
# One or more k-mers on the command line
rustkmer query database.rkdb ATCGATCGATC GCTAGCTAGCT

# From a text file, one k-mer per line
printf 'ATCGATCGATC\nGCTAGCTAGCT\n' > queries.txt
rustkmer query database.rkdb -b queries.txt

# Extract and query every k-mer of a FASTA/FASTQ file
rustkmer query database.rkdb -s reads.fastq

# Save results to a file instead of stdout
rustkmer query database.rkdb -b queries.txt -o results.txt
```

## 3. Database Statistics

### Python API

```python
db = PyDatabase("database.rkdb", LoadMode.Preload)
stats = db.get_stats()
# PyDatabaseStats fields:
#   kmer_size, total_kmers, unique_kmers, file_size, is_sorted, canonical
print(f"k={stats.kmer_size} unique={stats.unique_kmers} sorted={stats.is_sorted}")

# Additional metadata as a plain dict
print(db.database_info())       # path, kmer_size, load_mode, totals
print(db.get_memory_usage())    # per-mode memory information
```

### Rust CLI

```bash
rustkmer stats database.rkdb              # human-readable text
rustkmer stats database.rkdb -f json      # machine-readable
rustkmer stats database.rkdb -f csv
rustkmer stats database.rkdb --detailed   # add frequency distribution
```

## 4. Dumping and Exporting Content

### Python API

```python
db = PyDatabase("database.rkdb", LoadMode.Preload)

# Paginate over decoded k-mer sequences (recommended)
for entry in db.export_all_kmers(limit=1000, offset=0):
    print(entry.kmer, entry.count)

# Note: db.dump(limit, offset) also exists but returns k-mers as
# hexadecimal encodings; prefer export_all_kmers for sequence output.

# Streaming exports with progress callback
n = db.export_to_file("kmers.tsv")                       # "kmer\tcount" lines
n = db.export_to_csv("kmers.csv")                        # with header row
n = db.export_to_json("kmers.json")                      # [{"kmer": ..., "count": ...}]
n = db.export_to_file("kmers.tsv", limit=1000, offset=0,
                      progress_callback=lambda cur, tot: print(cur, "/", tot))
```

See [Data Export](data-export.md) for the full walkthrough.

### Rust CLI

```bash
# Dump to stdout (a '#' comment header, then "kmer<TAB>count" lines)
rustkmer dump database.rkdb | head

# Dump to a file (the -o flag is the only option dump takes)
rustkmer dump database.rkdb -o kmers.txt
```

## 5. Fuzzy Search (Preview)

```bash
# Wildcards (N) and mutation tolerance in one command
rustkmer fuzzy-query database.rkdb ATCGATCGATN -m 1

# JSON output
rustkmer fuzzy-query database.rkdb ATCGATCGATN -m 1 -f json
```

```python
from pyrustkmer import PyFuzzyQuery

fq = PyFuzzyQuery(db)                      # wraps the PyDatabase instance
result = fq.query_fuzzy("ATCGATCGATN", 1)  # pattern, max_mutations
print(result.total_matches)
for m in result.get_top_matches(5):
    print(m.kmer, m.count, m.match_type)
```

See [Fuzzy Search](fuzzy-search.md) for wildcards, mutation tolerance, and position-specific mutations.

## 6. Error Handling

### Python API

The module raises built-in Python exceptions (no custom exception imports are needed):

```python
from pyrustkmer import PyDatabase, PyCounter, LoadMode

try:
    db = PyDatabase("missing.rkdb", LoadMode.Preload)
except FileNotFoundError as e:
    print("Database file not found:", e)

db = PyDatabase("database.rkdb", LoadMode.Preload)
try:
    db.query_exact("ATCG")   # wrong length for k=11
except ValueError as e:
    print("Invalid query:", e)
# Invalid query: K-mer length 4 does not match database k-mer size 11

try:
    PyCounter(99)            # k must be 1-64
except ValueError as e:
    print("Invalid k:", e)
```

### Rust CLI

The CLI validates input before running and exits with a non-zero status on error, printing all validation problems it found:

```bash
rustkmer count -i demo.fa -o out.rkdb -k 0    # error: K-mer size must be between 1 and 127
rustkmer count -k 11 -i nope.fasta -o out.rkdb # error: file not found
```

## 7. Performance Tips

- **Threads**: pass `--threads N` to `count` (CLI) or `threads=N` to `PyCounter` (Python). Precedence: flag beats `RUSTKMER_THREADS` beats `RAYON_NUM_THREADS` beats all cores.
- **Load modes**: `LoadMode.Preload` gives the fastest exact queries at the highest memory cost; `LoadMode.Lazy` binary-searches sorted entries; `LoadMode.MemoryMapped` keeps only a file handle.
- **Batch queries**: `query_exact_batch` (Python) or `-b queries.txt` (CLI) amortizes database loading over many lookups.
- **Canonical mode** roughly halves the database for strand-agnostic analyses.
- **Unsorted output**: `count --no-sort` skips the sort step when you only need counts, not fast lookups.

## 8. Choosing Between the CLI and Python

Use the **CLI** for one-off counting, shell pipelines, and batch jobs. Use the **Python API** when you need programmatic control, pandas/matplotlib integration, or notebook-driven analysis. Both surfaces read and write the same `.rkdb` format, so you can count with the CLI and analyze with Python (or vice versa).

## Runnable Example Scripts

The repository ships working scripts you can run directly:

- `examples/bash/01_counting.sh` — counting walkthroughs (note: it predates the current CLI; prefer the flags shown in this page, e.g. `--threads` instead of `-t`)
- `examples/bash/03_querying.sh` — query-based workflows
- `examples/python/demo_pyo3_binding.py`, `examples/python/unified_query_example.py` — PyDatabase interface demos
- `examples/data/demo_rice_genome.fa.gz` — bundled demo FASTA (gzipped)
- `examples/README.md` — index of all examples

## Next Steps

- [Database Operations](database-ops.md) — load modes and database management
- [Fuzzy Search](fuzzy-search.md) — wildcards and mutation tolerance
- [Batch Processing](batch-processing.md), [Merging](merging.md), [Statistics](statistics.md), [Data Export](data-export.md), [Advanced Features](advanced.md)
- [Python examples](python/README.md)
