<!-- generated-by: gsd-doc-writer -->
# Python API Examples

Python examples for the `pyrustkmer` extension module (built with PyO3 from `pyo3/src/`). Everything in the "Common Usage Patterns" section below was executed against the live module.

## Setup

```bash
# Build and install the extension into your virtualenv (Python >= 3.11)
cd pyo3
pip install maturin
maturin develop --release

# Verify the import surface
python -c "import pyrustkmer; print([n for n in dir(pyrustkmer) if not n.startswith('_')])"
```

Expected exports: `LoadMode`, `PyCounter`, `PyCounterStats`, `PyDatabase`, `PyDatabaseStats`, `PyExtendedPrefixQuery`, `PyFormatter`, `PyFuzzyMatch`, `PyFuzzyQuery`, `PyFuzzyResult`, `PyPrefixQuery`, `PyPrefixQueryMetrics`, `PyPrefixQueryResult`, `PyQueryResult`, `RustKmerError`.

## Files in This Directory

| File | Topic |
|------|-------|
| `basic_usage.py` | Database creation, loading, and queries |
| `fuzzy_search.py` | Fuzzy queries and mutation analysis |
| `database_operations.py` | Statistics, dumping, and exports |
| `integration_pandas.py` | pandas/matplotlib analysis of k-mer tables |
| `integration_biopython.py` | BioPython workflows over FASTA/FASTQ |

These companion scripts were drafted against an earlier binding surface and do not currently run unmodified: they import `KmerCounter` (the module now exports `PyCounter`), and some code blocks are mis-indented. Treat them as topical outlines and pair them with the verified patterns below when writing new code.

For scripts that run against the current API today, see the repository's [`examples/python/`](../../../examples/python/) directory: `demo_pyo3_binding.py`, `unified_query_example.py`, `simple_prefix_query.py`, `demo_fuzzy.py`, `demo_fuzzy_enhanced.py`, `demo_performance.py`, `demo_position_mutations_fixed.py`, `validate_position_mutations.py`, and `test_pyo3_api.py`.

## Common Usage Patterns (verified)

### Counting and building a database

```python
from pyrustkmer import PyCounter

counter = PyCounter(31, canonical=True, threads=4)  # k, canonical, capacity, threads
counter.add_from_fasta("sequences.fasta")           # .gz/.bz2/.xz transparent
counter.add_from_fastq("reads.fastq.gz")

stats = counter.get_stats()
print(stats.total_kmers, stats.unique_kmers, stats.memory_usage)

counter.save_database("output.rkdb")                # sorted .rkdb, binary v2
```

### Opening a database and querying

```python
from pyrustkmer import PyDatabase, LoadMode

db = PyDatabase("output.rkdb", LoadMode.Preload)    # exactly two arguments

result = db.query_exact("ATCGATCGATCGATCGATCGATCGATCGATC")
print(result.count, result.found)                   # PyQueryResult(kmer, count, found)

batch = db.query_exact_batch(["ATCGATCGATCGATCGATCGATCGATCGATC",
                              "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT"])
for kmer, r in batch.items():                       # dict: input string -> PyQueryResult
    print(kmer, r.count)
```

### Database statistics

```python
stats = db.get_stats()  # PyDatabaseStats
print(f"k={stats.kmer_size} unique={stats.unique_kmers}")
print(f"sorted={stats.is_sorted} canonical={stats.canonical} size={stats.file_size}")
```

### Fuzzy queries

```python
from pyrustkmer import PyFuzzyQuery

fq = PyFuzzyQuery(db)                        # wraps the PyDatabase instance
result = fq.query_fuzzy("ATCGATCGATCGATCGATCGATCGATCGATN", 1)  # pattern, max_mutations

print(result.total_matches, result.mutation_tolerance, result.query_time_ms)
for m in result.get_top_matches(10):         # sorted by count
    print(m.kmer, m.count, m.distance)       # distance can be None (wildcard hits)

# Position-scoped mutations: "0,1:1" = up to 1 mutation among positions 0 and 1
result = fq.query_fuzzy_position("ATCGATCGATCGATCGATCGATCGATCGATC",
                                 1, "0,1:1")
```

### Dumping and exporting

```python
# Paginate over decoded sequences (recommended)
for entry in db.export_all_kmers(limit=1000, offset=0):
    print(entry.kmer, entry.count)

# Note: db.dump(limit) returns k-mers as hex strings; prefer export_all_kmers.

# File exports (all return the number of k-mers written)
db.export_to_file("kmers.tsv")                       # "kmer<TAB>count" lines
db.export_to_csv("kmers.csv")                        # header + kmer,count
db.export_to_json("kmers.json")                      # [{"kmer": ..., "count": ...}]
db.export_to_file("kmers.tsv", limit=1000, offset=0,
                  progress_callback=lambda cur, tot: print(f"{cur}/{tot}"))
```

### Merging databases

```python
PyDatabase.merge(["db1.rkdb", "db2.rkdb"], "merged.rkdb",
                 max_memory="4GB", merge_mode="streaming")
# merge_mode: "auto" (default) | "memory" | "streaming"; max_memory e.g. "4GB", "512MB"
```

### Error handling

The binding raises built-in exceptions — no custom exception classes to import:

```python
try:
    db = PyDatabase("missing.rkdb", LoadMode.Preload)
except FileNotFoundError as e:
    print(e)                  # Database file not found: missing.rkdb

try:
    db.query_exact("ATCG")    # wrong length for this database
except ValueError as e:
    print(e)                  # K-mer length 4 does not match database k-mer size 31
```

(`RustKmerError` is exported for catching errors raised by the Rust core with `message` and `error_type` attributes.)

## Integration Snippets

### pandas

```python
import pandas as pd
from pyrustkmer import PyDatabase, LoadMode

db = PyDatabase("output.rkdb", LoadMode.Preload)
df = pd.DataFrame(
    [{"kmer": e.kmer, "count": e.count} for e in db.export_all_kmers(limit=100000)]
)
print(df["count"].describe())
df.to_csv("kmers.csv", index=False)
```

### BioPython

```python
from Bio import SeqIO
from pyrustkmer import PyCounter

counter = PyCounter(31, canonical=True)
for record in SeqIO.parse("sequences.fasta", "fasta"):
    counter.add_sequence(str(record.seq))
counter.save_database("biopython_built.rkdb")
```

## Requirements

```bash
# Core (from the repository)
cd pyo3 && maturin develop --release

# For the integration examples
pip install pandas matplotlib seaborn biopython
```

## Performance Tips

1. **Batch queries** (`query_exact_batch`) amortize lookups; avoid tight one-at-a-time loops.
2. **Load modes**: `Preload` for fastest queries, `Lazy` for lower memory, `MemoryMapped` for direct file access (`get_entry_by_index`).
3. **Canonical counting** (`canonical=True`) halves the k-mer universe for strand-agnostic workloads.
4. **Threads**: `PyCounter(..., threads=N)` sizes the Rayon pool; the first construction wins (later values are ignored, logged under `RUST_LOG=warn`).
5. **Paginate big exports** with `export_all_kmers(limit, offset)` or the `progress_callback` of `export_to_*`.

## Next Steps

- [Basic Usage](../basic-usage.md), [Fuzzy Search](../fuzzy-search.md), [Data Export](../data-export.md)
- Repository examples: [`examples/python/`](../../../examples/python/), [`examples/README.md`](../../../examples/README.md)
