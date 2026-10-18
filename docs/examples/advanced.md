<!-- generated-by: gsd-doc-writer -->
# Advanced Features Examples

Beyond counting and exact lookup: prefix/hybrid pattern queries, environment-controlled threading, direct entry access, and a real gap-filling application. All commands verified against `rustkmer` 0.5.0 and the live `pyrustkmer` module.

Setup:

```bash
printf '>seq1\nATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGGCTAGCTAGCTAGCTA\n>seq2\nATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGTTTTTTTTTTTTTTTT\n' > demo.fa
rustkmer count -k 11 -i demo.fa -o demo.rkdb --threads 4
```

## 1. Prefix Queries (CLI)

`prefix-query` finds every k-mer starting with a given prefix — an indexed range scan on sorted databases:

```bash
rustkmer prefix-query demo.rkdb -p ATCGAT
```

```text
Loading database: demo.rkdb
Executing optimized prefix query for: ATCGAT
K-mer	Count
ATCGATCGATC	16
ATCGATCGGCT	1
ATCGATCGTTT	1
```

Use `-x/--prefix` as an alternative to `-p/--pattern`, add count thresholds with `-L/--min-count` / `-U/--max-count`, and choose `-f json|csv|tsv` for structured output.

## 2. Hybrid Patterns (wildcards in the middle)

Hybrid patterns spell the variable stretch as `{N<count>}` — useful for motifs with a fixed-distance spacer:

```bash
rustkmer prefix-query demo.rkdb -p 'ATCGAT{N2}ATC' --hybrid -f csv
```

```text
kmer,count
ATCGATCGATC,16
```

`--hybrid` requires `-p`. The pattern's total length (fixed bases plus the N run) must equal the database k-mer size.

## 3. Prefix and Pattern Queries (Python)

```python
from pyrustkmer import PyDatabase, LoadMode

db = PyDatabase("demo.rkdb", LoadMode.Preload)

# Simple prefix -> plain dict of kmer -> count (counts are strings)
print(db.extract_by_prefix("ATCGAT"))
# {'ATCGATCGATC': '16', 'ATCGATCGGCT': '1', 'ATCGATCGTTT': '1'}

# Hybrid pattern -> same dict shape
print(db.query_hybrid("ATCGAT{N2}ATC"))     # {'ATCGATCGATC': '16'}
print(db.extract_by_pattern("ATCGAT{N2}ATC"))

# Inspect a hybrid pattern before running it
print(db.parse_pattern("ATCGAT{N2}ATC"))
# {'prefix': 'ATCGAT', 'suffix': 'ATC', 'n_count': '2',
#  'total_length': '11', 'n_positions': '[6, 7]'}

# Richer result object with timing and memory-block diagnostics
r = db.query_prefix("ATCGAT")
print(r.total_matches, r.query_time_ms, r.is_sorted)   # 3 0 True
print(r.matches)                                       # kmer -> count string

# Batch of prefixes -> list of PyPrefixQueryResult
print([p.total_matches for p in db.query_prefix_batch(["ATCGAT", "GCTAGC"])])  # [3, 1]
```

`PyPrefixQueryResult` also exposes `start_index`, `end_index`, `block_size` (the scanned memory block) and `to_json()/to_csv()/to_tsv()/to_table()` formatters. The module additionally exports `PyPrefixQuery` and `PyExtendedPrefixQuery` classes for standalone prefix engines.

## 4. Fuzzy Queries with Position Budgets

Covered in depth in [Fuzzy Search](fuzzy-search.md); the short verified form:

```python
from pyrustkmer import PyFuzzyQuery

fq = PyFuzzyQuery(db)
result = fq.query_fuzzy_position("ATCGATCGATC", 1, "0,1:1")   # 1 mutation max, only at positions 0-1
print(result.total_matches, result.has_position_mutations)
```

CLI equivalent: `rustkmer fuzzy-query demo.rkdb ATCGATCGATC -m 1 --position-mutations "0,1:1"`.

## 5. Threading and Environment Control

```bash
# Explicit thread count for counting
rustkmer count -k 31 -i big.fastq.gz -o big.rkdb --threads 16

# Precedence: --threads > RUSTKMER_THREADS > RAYON_NUM_THREADS > all cores
RUSTKMER_THREADS=8 rustkmer count -k 31 -i big.fastq.gz -o big.rkdb
RAYON_NUM_THREADS=4 rustkmer merge -i a.rkdb b.rkdb -o m.rkdb --num-threads 4

# Log verbosity (env_logger)
RUST_LOG=debug rustkmer query demo.rkdb ATCGATCGATC
```

In Python, the Rayon pool is configured by the first `PyCounter(..., threads=N)` construction; later constructions cannot change it (a warning is logged at `RUST_LOG=warn`).

## 6. Direct Entry Access and Query Modes

```bash
# Force preloading for repeated CLI queries (or -L to disable it)
rustkmer query demo.rkdb -b big_queries.txt --load

# Interactive stdin session
rustkmer query demo.rkdb --interactive
```

```python
from pyrustkmer import PyDatabase, LoadMode

# MemoryMapped mode exposes raw (encoded_kmer_u128, count) tuples by index
mm = PyDatabase("demo.rkdb", LoadMode.MemoryMapped)
print(mm.get_entry_by_index(0))       # (641481, 1) on the demo database

# Lazy mode keeps binary-search lookups without the full cache
lazy = PyDatabase("demo.rkdb", LoadMode.Lazy)
print(lazy.query_exact("ATCGATCGATC").count)   # 16
```

(Exact lookups return `0` in `MemoryMapped` mode in the current implementation — see [Database Operations](database-ops.md).)

## 7. Compressed and Directory Inputs

```bash
# .gz / .bz2 / .xz are detected transparently by count (CLI and PyCounter)
rustkmer count -k 31 -i reads.fastq.gz -o reads.rkdb

# Count a whole directory tree (recursive by default; --no-recursive to flatten)
rustkmer count -k 31 -d reads_dir/ -o all.rkdb
```

The bundled demo genome is itself gzipped: `examples/data/demo_rice_genome.fa.gz`.

## 8. Application Example: Filling N-Gaps in a FASTA

The repository contains a real application of prefix/pattern queries — repairing runs of `N` in assemblies by looking up the spanning k-mers:

- `examples/application/pyo3_fill_fasta.py` — fill N regions in a FASTA using the k-mer database
- `examples/application/pyo3_fill_n.py`, `examples/application/pyo3_fill_oneseq.py`, `examples/application/pyo3_fill_fasta_startN.py` — focused variants
- `examples/application/process_fasta_gaps_pyo3.py` — batch processor for gapped FASTA files
- `examples/application/n_region_gap_filling_balanced_57mer.py` — gap filling with balanced 57-mer patterns
- `examples/application/gap_filling.py`, `examples/application/mark_N_script_pyo3.py` — supporting utilities
- Demo inputs: `examples/application/Chr10_demo.fa`, `Chr10_hard.fa`, and related `*_marked.fa` / `*_fill.fa` files

The core loop of these scripts: scan for `N` runs, build prefix/hybrid patterns from the flanking sequence, query the database with `PyDatabase` (via `LoadMode.MemoryMapped` in `simple_prefix_query.py`), and write the repaired sequence. `examples/python/unified_query_example.py` is a compact introduction to the same unified query interface.

## 9. Error Type from the Rust Core

Errors raised by the Rust core can be caught via the exported `RustKmerError` class, which carries `message` and `error_type` attributes. Boundary validation surfaces as standard built-in exceptions instead:

```python
from pyrustkmer import PyDatabase, LoadMode

try:
    PyDatabase("missing.rkdb", LoadMode.Preload)
except FileNotFoundError as e:
    print(e)          # Database file not found: missing.rkdb

db = PyDatabase("demo.rkdb", LoadMode.Preload)
try:
    db.query_exact("ATCG")   # wrong length
except ValueError as e:
    print(e)         # K-mer length 4 does not match database k-mer size 11
```

## Runnable Example Scripts

- `examples/python/demo_pyo3_binding.py` — prefix-query binding demo
- `examples/python/simple_prefix_query.py` — prefix/hybrid queries against a real database
- `examples/python/unified_query_example.py` — the unified PyDatabase query interface
- `examples/python/demo_performance.py` — query performance on genomic data
- `examples/utils/prepare_data.sh`, `examples/utils/verify_consistency.sh` — data prep and consistency checks

## Next Steps

- [Fuzzy Search](fuzzy-search.md) for wildcard/mutation queries
- [Batch Processing](batch-processing.md) and [Merging Databases](merging.md)
- [Python examples](python/README.md)
