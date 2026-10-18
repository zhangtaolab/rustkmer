<!-- generated-by: gsd-doc-writer -->
# Statistics Examples

Summarizing k-mer databases: built-in statistics, frequency distributions, and custom analyses in Python. All outputs below are real output from `rustkmer` 0.5.0 and the live `pyrustkmer` module.

Setup:

```bash
printf '>seq1\nATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGGCTAGCTAGCTAGCTA\n>seq2\nATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGTTTTTTTTTTTTTTTT\n' > demo.fa
rustkmer count -k 11 -i demo.fa -o demo.rkdb --threads 4
```

## 1. Text Summary (CLI)

```bash
rustkmer stats demo.rkdb
```

```text
Database Statistics
===================
Database: "demo.rkdb"
K-mer size: 11
Canonical: false
Sorted: true
Total k-mers: 92
Unique k-mers: 29
Min count: 1
Max count: 16
Mean count: 3.17
Median count: 1.00
Processing time: 42.416µs
```

`Total k-mers` counts all observations; `Unique k-mers` is the number of distinct k-mer sequences stored.

## 2. Frequency Distribution (CLI)

Add `--detailed` for the count histogram:

```bash
rustkmer stats demo.rkdb --detailed
```

```text
Frequency Distribution:
Count	Frequency
1	22
2	2
...
14	2
16	2
```

Read it as: 22 k-mers occur once, 2 occur twice, and so on — the classic error-tail shape. `--max-bins N` (default 1000) caps histogram resolution for very deep databases, and `--approximate` switches to a faster streaming median estimate.

## 3. Machine-Readable Output (CLI)

```bash
rustkmer stats demo.rkdb -f json
```

```json
{"database_file":"demo.rkdb","kmer_size":11,"canonical":false,"sorted":true,
 "total_kmers":92,"unique_kmers":29,"min_count":1,"max_count":16,
 "mean_count":3.1724137931034484,"median_count":1.0,"processing_time":0,
 "memory_peak_bytes":0}
```

```bash
rustkmer stats demo.rkdb -f csv        # one header row + one data row
rustkmer stats demo.rkdb -f tsv
rustkmer stats demo.rkdb -f json -o stats.json     # write to file
rustkmer stats demo.rkdb --detailed --split-output --freq-output freq.txt
```

`--split-output` writes basic stats to `-o` and the frequency distribution to `--freq-output` (required when splitting).

Compare databases in a shell loop:

```bash
for db in *.rkdb; do
    printf '%-20s ' "$db"
    rustkmer stats "$db" -f json | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["unique_kmers"], "unique, mean", round(d["mean_count"],2))'
done
```

## 4. Counter Statistics (Python)

While counting, before a database even exists:

```python
from pyrustkmer import PyCounter

counter = PyCounter(11, canonical=False)
counter.add_from_fasta("demo.fa")

stats = counter.get_stats()      # PyCounterStats
print(stats.total_kmers)         # all k-mer observations processed
print(stats.unique_kmers)        # distinct k-mers counted
print(stats.kmer_length)         # 11
print(stats.canonical_mode)      # False
print(stats.memory_usage)        # estimated bytes used by the table
```

## 5. Database Statistics (Python)

```python
from pyrustkmer import PyDatabase, LoadMode

db = PyDatabase("demo.rkdb", LoadMode.Preload)
stats = db.get_stats()           # PyDatabaseStats

print(stats.kmer_size)       # 11
print(stats.total_kmers)     # 92 (sum of counts, from the header)
print(stats.unique_kmers)    # 29
print(stats.is_sorted)       # True
print(stats.canonical)       # False
print(stats.file_size)       # size recorded in the header (may be 0 for CLI-built files)

print(db.database_info())    # dict: path, kmer_size, is_loaded, totals, load_mode
```

Note: `file_size` comes from the database header; databases written by the CLI may record `0` there — use `os.path.getsize(db.path)` for the on-disk size.

## 6. Custom Analyses over k-mer Abundance

Iterate `export_all_kmers` (decoded sequences, sorted order) and compute anything the built-ins do not provide:

```python
import statistics

db = PyDatabase("demo.rkdb", LoadMode.Preload)
counts = [e.count for e in db.export_all_kmers()]

print("unique:", len(counts))
print("total :", sum(counts))
print("median:", statistics.median(counts))
print("p95   :", sorted(counts)[int(len(counts) * 0.95)])

# Error-tail heuristic: fraction of k-mers seen exactly once
singletons = sum(1 for c in counts if c == 1)
print(f"singleton rate: {singletons / len(counts):.1%}")
```

For large databases, paginate instead of materializing everything:

```python
BATCH = 100_000
offset = singletons = total = 0
while True:
    batch = db.export_all_kmers(limit=BATCH, offset=offset)
    if not batch:
        break
    singletons += sum(1 for e in batch if e.count == 1)
    total += len(batch)
    offset += BATCH
print(f"singleton rate: {singletons / total:.1%}")
```

## 7. Watch Statistics Change with Filters

```bash
# Full database vs. count-filtered rebuilds
rustkmer stats demo.rkdb -f json | python3 -m json.tool | grep unique
rustkmer count -k 11 -i demo.fa -o solid.rkdb --min-count 2 --quiet
rustkmer stats solid.rkdb -f json | python3 -m json.tool | grep unique
```

Filtering with `--min-count 2` removes the singleton error tail, which typically drops both the unique count and the file size sharply.

## Runnable Example Scripts

- `examples/bash/02_database_ops.sh` — stats-driven database comparison workflow (older CLI flags; prefer `stats -f json` as shown here)
- `examples/python/demo_performance.py` — timing and statistics on real genomic data

## Next Steps

- [Database Operations](database-ops.md) and [Data Export](data-export.md)
- [Merging Databases](merging.md) for cohort-wide counting
