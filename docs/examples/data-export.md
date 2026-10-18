<!-- generated-by: gsd-doc-writer -->
# Data Export Examples

Getting k-mer data out of `.rkdb` databases as text, CSV, JSON, or pandas DataFrames. Every format shown below is the actual output of `rustkmer` 0.5.0 and the live `pyrustkmer` module.

Setup:

```bash
printf '>seq1\nATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGGCTAGCTAGCTAGCTA\n>seq2\nATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGTTTTTTTTTTTTTTTT\n' > demo.fa
rustkmer count -k 11 -i demo.fa -o demo.rkdb --threads 4
```

## 1. Dump to Text (CLI)

`dump` writes a `#`-commented header followed by one `kmer<TAB>count` line per entry, to stdout or to `-o`:

```bash
rustkmer dump demo.rkdb -o demo_dump.txt
head -9 demo_dump.txt
```

```text
# rustkmer database dump
# k: 11
# total_kmers: 29
# sorted: true
# canonical: false
# format: RKDB
#
AGCTAGCTAGC	1
ATCGATCGATC	16
```

`-o` is the only option `dump` takes — there is no `--limit` or `--format` flag; pipe through standard tools instead:

```bash
# First 1000 entries, plain kmer/count pairs
rustkmer dump demo.rkdb | grep -v '^#' | head -1000 > top.txt

# Compressed archive of a large dump
rustkmer dump big.rkdb | gzip > kmers.txt.gz

# Filter by count with awk
rustkmer dump demo.rkdb | grep -v '^#' | awk -F'\t' '$2 >= 2' > abundant.tsv
```

## 2. Statistics as Data (CLI)

`stats` exports its summary in structured formats for spreadsheets and scripts:

```bash
rustkmer stats demo.rkdb -f json -o stats.json
rustkmer stats demo.rkdb -f csv  -o stats.csv
rustkmer stats demo.rkdb --detailed --split-output -o stats.txt --freq-output freq.txt
```

## 3. File Exports (Python)

`PyDatabase` has three streaming file exporters plus in-memory accessors:

```python
from pyrustkmer import PyDatabase, LoadMode

db = PyDatabase("demo.rkdb", LoadMode.Preload)

# TSV: "kmer<TAB>count" lines
n = db.export_to_file("kmers.tsv")
# CSV: header row "kmer,count" then one row per k-mer
n = db.export_to_csv("kmers.csv")
# JSON: array of {"kmer": ..., "count": ...} objects
n = db.export_to_json("kmers.json")
print("exported", n, "k-mers to each")
```

Real contents (k=11 demo database):

```text
kmers.tsv            kmers.csv           kmers.json
AGCTAGCTAGC	1      kmer,count          [
ATCGATCGATC	16     AGCTAGCTAGC,1         {"kmer": "AGCTAGCTAGC", "count": 1}
...                  ...                   ,  {"kmer": "ATCGATCGATC", "count": 16}
```

All three accept the same options:

- `limit` / `offset` — pagination (`export_to_csv("kmers.csv", limit=2, offset=1)` writes 2 rows starting from the second entry)
- `progress_callback` — a callable receiving `(current, total)` as rows are written

```python
db.export_to_file(
    "kmers.tsv",
    limit=1000,
    offset=0,
    progress_callback=lambda cur, tot: print(f"{cur}/{tot}", end="\r"),
)
```

Exports stream from the loaded database and do not build the whole output in memory, so they suit very large databases.

## 4. In-Memory Export (Python)

For further processing inside Python, paginate over decoded k-mers:

```python
# PyQueryResult objects with .kmer (decoded sequence), .count, .found
entries = db.export_all_kmers(limit=1000, offset=0)
data = [(e.kmer, e.count) for e in entries]
```

`db.dump(limit, offset)` paginates too, but returns **hex-encoded** k-mers (e.g. `9c9c9`) rather than sequences — prefer `export_all_kmers` unless you specifically want the raw encoding.

## 5. pandas Integration

```python
import pandas as pd

# Either via the CSV file...
df = pd.read_csv("kmers.csv")

# ...or straight from the database
from pyrustkmer import PyDatabase, LoadMode
db = PyDatabase("demo.rkdb", LoadMode.Preload)
df = pd.DataFrame(
    [{"kmer": e.kmer, "count": e.count} for e in db.export_all_kmers(limit=100_000)]
)

print(df.describe())
df.sort_values("count", ascending=False).head(10).to_csv("top10.csv", index=False)
```

## 6. JSON Consumption

```python
import json

with open("kmers.json") as f:
    entries = json.load(f)

total = sum(e["count"] for e in entries)
print(f"{len(entries)} unique k-mers, {total} total observations")
```

## 7. Choosing an Export Path

| Need | Use |
|-----|-----|
| Quick shell inspection | `rustkmer dump` + `grep`/`awk` |
| Spreadsheet / pandas | `db.export_to_csv` or `stats -f csv` |
| Web / nested tooling | `db.export_to_json` |
| Custom Python analysis | `export_all_kmers(limit, offset)` loop |
| Very large databases | exporters with `limit`/`offset` + `progress_callback` |

## Runnable Example Scripts

- `examples/bash/01_counting.sh` — counting plus a `dump -o` export walkthrough (older CLI flags elsewhere in the script; prefer the flags shown here)
- `examples/python/integration_pandas.py` — pandas/matplotlib analysis patterns (drafted against an older API; see [python/README.md](python/README.md) for the verified imports)

## Next Steps

- [Statistics](statistics.md) — analyzing what you exported
- [Batch Processing](batch-processing.md) — pagination patterns
