<!-- generated-by: gsd-doc-writer -->
# Database Operations Examples

Working with `.rkdb` databases on both surfaces: opening modes, inspection, memory behavior, and in-place tricks. Commands below were verified against `rustkmer` 0.5.0 and the live `pyrustkmer` module.

Build the demo database first:

```bash
printf '>seq1\nATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGGCTAGCTAGCTAGCTA\n>seq2\nATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGTTTTTTTTTTTTTTTT\n' > demo.fa
rustkmer count -k 11 -i demo.fa -o demo.rkdb --threads 4
```

## 1. Creating Database Variants

```bash
# Stranded (default) and canonical variants cannot be merged later —
# pick one convention per project.
rustkmer count -k 11 -i demo.fa -o stranded.rkdb
rustkmer count -k 11 -i demo.fa -o canonical.rkdb --canonical

# Unsorted databases skip the sorting pass (faster to build, slower to query)
rustkmer count -k 11 -i demo.fa -o unsorted.rkdb --no-sort

# Threshold filtering at count time
rustkmer count -k 11 -i demo.fa -o solid.rkdb --min-count 2
```

## 2. Inspecting a Database (CLI)

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
```

Machine-readable variants: `rustkmer stats demo.rkdb -f json`, `-f csv`, `-f tsv`; add `--detailed` for the frequency distribution.

## 3. Opening Modes (Python)

`PyDatabase(path, load_mode)` takes one of three `LoadMode` values:

| Mode | Behavior | Best for |
|------|----------|----------|
| `LoadMode.Preload` | All entries cached in a sorted map | Fastest repeated exact queries |
| `LoadMode.Lazy` | Sorted index, binary-search lookups | Large databases, moderate query volumes |
| `LoadMode.MemoryMapped` | File handle only, per-entry reads | Minimal footprint; `get_entry_by_index`, `dump`, and exports |

```python
from pyrustkmer import PyDatabase, LoadMode

db = PyDatabase("demo.rkdb", LoadMode.Preload)

print(db.get_stats())          # PyDatabaseStats(kmer_size=11, ..., is_sorted=True, ...)
print(db.database_info())      # {'database_path': ..., 'kmer_size': ..., 'load_mode': 'preload', ...}
print(db.get_memory_usage())   # {'cache_size': '29', 'mode': 'preload'}

# Drop the preload cache and switch to lazy lookups without reopening
db.force_lazy_mode()

# Direct entry access is available in MemoryMapped mode only:
# returns (encoded_kmer_u128, count) tuples
mm = PyDatabase("demo.rkdb", LoadMode.MemoryMapped)
kmer_u128, count = mm.get_entry_by_index(0)
```

Exact queries are served from the cache/index in Preload and Lazy mode:

```python
for mode in (LoadMode.Preload, LoadMode.Lazy):
    d = PyDatabase("demo.rkdb", mode)
    print(mode, d.query_exact("ATCGATCGATC").count)   # 16 in both
```

Note: in the current implementation `MemoryMapped` serves indexed reads (`get_entry_by_index`, `dump`, exports) but `query_exact` returns `0` in that mode — use Preload or Lazy for lookups.

## 4. Reading and Validating Content

```python
db = PyDatabase("demo.rkdb", LoadMode.Preload)

# Existence checks
print(db.exists("ATCGATCGATC"))    # True
print(db.exists("GGGGGGGGGGG"))    # False

# First entries in sorted order (decoded sequences)
for entry in db.export_all_kmers(limit=5):
    print(entry.kmer, entry.count)

# db.dump(limit) also paginates, but returns hex-encoded k-mers —
# useful for debugging the raw encoding, not for sequence output:
for entry in db.dump(limit=2):
    print(entry.kmer, entry.count)  # e.g. '9c9c9' 2
```

CLI equivalent of a full content check:

```bash
# Header comments + "kmer<TAB>count" lines
rustkmer dump demo.rkdb | head -12
rustkmer dump demo.rkdb -o demo_dump.txt
```

## 5. Counting Straight from Python

```python
from pyrustkmer import PyCounter

counter = PyCounter(11, canonical=False)
counter.add_from_fasta("demo.fa")
counter.add_from_fastq("reads.fastq.gz")   # gz/bz2/xz transparent
print(counter.is_empty(), counter.get_stats())
counter.save_database("py_built.rkdb")
```

`PyCounter` and the CLI produce the same `.rkdb` v2 format — databases built by either surface are interchangeable.

## 6. Compatibility Rules to Remember

- **k-mer size is fixed per database** — queries must be exactly that length (`ValueError` otherwise).
- **Canonical mode must match when merging** — see [Merging Databases](merging.md) for the exact failure message.
- **No concurrent writers** — the format has no locking; two processes writing one path will corrupt it.
- **k is capped at 64** (`u128` encoding); the CLI validates `1..=127` at parse time and the counter enforces `1..=64`.

## Runnable Example Scripts

- `examples/bash/02_database_ops.sh` — database-ops walkthrough (written against an older CLI; prefer the flags shown here, e.g. `stats -f json` instead of `--table`)
- `examples/python/test_pyo3_api.py` — API surface smoke test
- `examples/python/unified_query_example.py` — PyDatabase unified query interface

## Next Steps

- [Basic Usage](basic-usage.md) — counting and querying fundamentals
- [Statistics](statistics.md) and [Data Export](data-export.md)
