<!-- generated-by: gsd-doc-writer -->
# Batch Processing Examples

Running many lookups efficiently: batch query files, whole-sequence queries, batch fuzzy queries, and Python-side pagination. All commands verified against `rustkmer` 0.5.0 and the live `pyrustkmer` module.

Setup:

```bash
printf '>seq1\nATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGGCTAGCTAGCTAGCTA\n>seq2\nATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGTTTTTTTTTTTTTTTT\n' > demo.fa
rustkmer count -k 11 -i demo.fa -o demo.rkdb --threads 4
```

## 1. Batch Queries via the CLI

### Many k-mers in one invocation

```bash
rustkmer query demo.rkdb ATCGATCGATC GCTAGCTAGCT TTTTTTTTTTT
```

### From a text file (one k-mer per line)

```bash
printf 'ATCGATCGATC\nGCTAGCTAGCT\n' > queries.txt
rustkmer query demo.rkdb -b queries.txt
```

```text
Querying k-mers from batch file: queries.txt
Loaded 2 k-mers from batch file
ATCGATCGATC	16
GCTAGCTAGCT	2
Processed 2 k-mers, found 2 with non-zero counts
```

`-b` conflicts with positional k-mers and with `-s`; pick one input source per run. Use `-o results.txt` to write to a file instead of stdout.

### Query every k-mer of a sequence file

```bash
# Extracts each k-mer from the FASTA/FASTQ file and looks it up
rustkmer query demo.rkdb -s demo.fa
```

```text
Querying k-mers from sequence file: demo.fa
ATCGATCGATC	16
TCGATCGATCG	16
CGATCGATCGA	14
...
Processed 92 k-mers, found 92 with non-zero counts
```

This is the natural "how many of my reads' k-mers are in the database" check.

## 2. Batch Fuzzy Queries

`fuzzy-query-batch` reads patterns from a file (note: it takes `--default-mutations`, not `-m`):

```bash
printf 'ATCGATCGATC\nGCTAGCTAGCT\n' > fuzzy_queries.txt
rustkmer fuzzy-query-batch demo.rkdb -s fuzzy_queries.txt --default-mutations 1
```

```text
Batch Query Results
Total Queries: 2
Processed: 2

┌─────┬─────────────────────┬───────┬──────┬──────────┬──────────┬─────────┐
│ #   │ Query               │ Vars  │ Mut  │ Matches  │ Time(ms) │ Status  │
│ ... │ ...                 │ ...   │ ...  │ ...      │ ...      │ ...     │
└─────┴─────────────────────┴───────┴──────┴──────────┴──────────┴─────────┘
```

Useful flags: `--default-max-variants`, `-b` (queries per processing batch, default 100), `-f json|tsv|csv`, `--fail-fast` (abort on first bad pattern), `--include-headers`.

## 3. Batch Queries via Python

### One call for many k-mers

```python
from pyrustkmer import PyDatabase, LoadMode

db = PyDatabase("demo.rkdb", LoadMode.Preload)

kmers = ["ATCGATCGATC", "GCTAGCTAGCT", "TTTTTTTTTTT"]
results = db.query_exact_batch(kmers)          # dict: input string -> PyQueryResult
for kmer, r in results.items():
    print(kmer, r.count, r.found)
```

### Generating a query workload from sequences

```python
from pyrustkmer import PyCounter, PyDatabase, LoadMode

counter = PyCounter(11)
counter.add_from_fasta("demo.fa")              # build a reference database
counter.save_database("demo.rkdb")

db = PyDatabase("demo.rkdb", LoadMode.Preload)
queries = [e.kmer for e in db.export_all_kmers(limit=50)]   # sample real k-mers
hits = {k: r.count for k, r in db.query_exact_batch(queries).items()}
print(len(hits), "k-mers checked")
```

## 4. Paginating Large Outputs

Process a big database in bounded chunks with `export_all_kmers(limit, offset)`:

```python
BATCH = 10_000
offset = 0
total = 0
while True:
    batch = db.export_all_kmers(limit=BATCH, offset=offset)
    if not batch:
        break
    for entry in batch:            # entry.kmer, entry.count
        if entry.count >= 5:
            total += 1
    offset += BATCH
print("k-mers with count >= 5:", total)
```

The same `limit`/`offset` pagination works for `dump()` (hex k-mers) and the file exporters:

```python
n = db.export_to_csv("first_million.csv", limit=1_000_000, offset=0)
```

## 5. Progress Reporting for Long Exports

The file exporters accept a callback receiving `(current, total)`:

```python
def progress(current, total):
    if current % 100_000 == 0:
        print(f"{current}/{total}")

n = db.export_to_file("kmers.tsv", progress_callback=progress)
print("exported", n, "k-mers")
```

## 6. Pattern: Check a Candidate Set Against Multiple Databases

```python
from pyrustkmer import PyDatabase, LoadMode

candidates = ["ATCGATCGATC", "GCTAGCTAGCT", "TTTTTTTTTTT"]
dbs = {name: PyDatabase(f"{name}.rkdb", LoadMode.Lazy)
       for name in ("demo", "canonical", "solid")}

for name, db in dbs.items():
    results = db.query_exact_batch(candidates)
    found = [k for k, r in results.items() if r.found]
    print(f"{name}: {len(found)}/{len(candidates)} found")
```

Each database must share the same k-mer size as the candidates; otherwise `ValueError` is raised per mismatched query.

## Runnable Example Scripts

- `examples/bash/03_querying.sh` — single/batch query workflows and result export
- `examples/python/demo_performance.py` — query performance with real genomic data
- `examples/python/unified_query_example.py` — batched use of the unified query interface

## Next Steps

- [Basic Usage](basic-usage.md) and [Fuzzy Search](fuzzy-search.md)
- [Data Export](data-export.md) for output formats
