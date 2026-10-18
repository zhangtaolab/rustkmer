<!-- generated-by: gsd-doc-writer -->
# Fuzzy Search Examples

Practical examples of RustKmer's fuzzy search: wildcard (`N`) pattern expansion, Hamming-distance mutation tolerance, and position-specific mutation budgets. All commands were verified against `rustkmer` 0.5.0; the Python snippets were run against the live `pyrustkmer` module.

The examples use a two-sequence demo database built with:

```bash
printf '>seq1\nATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGGCTAGCTAGCTAGCTA\n>seq2\nATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGTTTTTTTTTTTTTTTT\n' > demo.fa
rustkmer count -k 11 -i demo.fa -o demo.rkdb --threads 4
```

## 1. Basic Examples (CLI)

### Exact and wildcard queries

```bash
# Exact lookup
rustkmer fuzzy-query demo.rkdb ATCGATCGATC

# One 'N' wildcard expands to A/T/C/G
rustkmer fuzzy-query demo.rkdb ATCGATCGATN

# Allow up to 1 mutation at any position (Hamming distance)
rustkmer fuzzy-query demo.rkdb ATCGATCGATC -m 1
```

Real output of the last command (k=11 database, 29 unique k-mers):

```text
Loading database: demo.rkdb
Query: ATCGATCGATC
Mutations: 1
Variants Generated: 34
Total Matches: 17
Query Time: 0ms

┌─────────────────────┬───────┬─────────┐
│ Sequence            │ Count │ Type    │
├─────────────────────┼───────┼─────────┤
│ AACGATCGATC         │ 1     │ Exact   │
│ ATCGATCGATC         │ 16    │ Exact   │
└─────────────────────┴───────┴─────────┘
```

### Output formats

```bash
rustkmer fuzzy-query demo.rkdb ATCGATCGATN -m 0 -f json
rustkmer fuzzy-query demo.rkdb ATCGATCGATN -m 0 -f tsv
rustkmer fuzzy-query demo.rkdb ATCGATCGATN -m 0 -f csv
rustkmer fuzzy-query demo.rkdb ATCGATCGATN -m 1 -f json -o matches.json
```

The JSON output carries the full result plus query metadata:

```json
{
  "total_count": 16,
  "individual_matches": [
    {
      "sequence": "ATCGATCGATC",
      "count": 16,
      "match_type": "Exact",
      "hamming_distance": null
    }
  ],
  "query_metadata": {
    "query_params": { "...": "..." }
  }
}
```

### Tuning knobs

| Flag | Meaning | Default |
|------|---------|---------|
| `-m, --mutations` | Max Hamming distance tolerated | 0 |
| `-M, --max-variants` | Cap on generated variants | 10000 |
| `-b, --batch-size` | Variants processed per batch | 1000 |
| `-f, --format` | `table` / `json` / `tsv` / `csv` | `table` |
| `--position-mutations` | Position-scoped budgets, e.g. `"3,4,5:2"` | off |
| `--profile` | Performance profiling output | off |

## 2. Wildcard Patterns

Each `N` in the query expands to the four bases, so a pattern with *w* wildcards generates *4^w* concrete k-mers (bounded by `-M`). Wildcard expansion combines freely with mutation tolerance.

```bash
# 1 wildcard -> 4 k-mers
rustkmer fuzzy-query demo.rkdb ATCGATCGATN

# 2 wildcards -> 16 k-mers
rustkmer fuzzy-query demo.rkdb ATCGATCNNAT -m 0

# Wildcards + mutation tolerance together
rustkmer fuzzy-query demo.rkdb ATCGATCNNAT -m 1
```

Pattern rules (enforced by the CLI and the Python layer alike):

- The pattern length must equal the database k-mer size.
- Only `A`, `T`, `C`, `G`, and `N` are allowed; anything else is rejected.

## 3. Mutation Tolerance (Hamming Distance)

`-m N` accepts k-mers within Hamming distance N of the query. The number of variants grows as `sum(C(k, i) * 3^i for i in 0..=N)`, so keep `-M` in mind for large k.

```bash
# SNP-tolerant lookup: any single substitution matches
rustkmer fuzzy-query demo.rkdb ATCGATCGATC -m 1

# Wider tolerance
rustkmer fuzzy-query demo.rkdb ATCGATCGATC -m 2 -M 100000
```

## 4. Position-Specific Mutations

Restrict where mutations may occur with `--position-mutations`. The syntax is `positions:count` groups separated by `;`, where positions are 0-indexed:

```bash
# Up to 2 mutations among positions 3,4,5
rustkmer fuzzy-query demo.rkdb ATCGATCGATC -m 2 --position-mutations "3,4,5:2"

# Two groups: 1 mutation in {0,1}, 1 mutation in {9,10}
rustkmer fuzzy-query demo.rkdb ATCGATCGATC -m 2 --position-mutations "0,1:1;9,10:1"
```

This is useful for primer design (conserve the 3' end) or motif scans where only certain columns are variable.

## 5. Batch Fuzzy Queries

Run many patterns from a file with `fuzzy-query-batch`. Note this subcommand takes `--default-mutations` (there is no `-m` here):

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

Useful flags: `--default-max-variants`, `-b` (queries per batch), `-f json|tsv|csv`, `--fail-fast` (stop on first error), `--include-headers` (header row for CSV/TSV).

## 6. Python API Examples

### Setup

```python
from pyrustkmer import PyCounter, PyDatabase, PyFuzzyQuery, LoadMode

counter = PyCounter(11)
counter.add_from_fasta("demo.fa")
counter.save_database("demo.rkdb")

db = PyDatabase("demo.rkdb", LoadMode.Preload)
fq = PyFuzzyQuery(db)          # constructed from a PyDatabase instance
```

### Wildcard query

```python
result = fq.query_fuzzy("ATCGATCGATN", 0)   # pattern, max_mutations
print(result.total_matches)                  # 16 with the demo data (single wildcard hit)
for m in result.matches:
    print(m.kmer, m.count, m.match_type)
```

### Mutation tolerance and top matches

```python
result = fq.query_fuzzy("ATCGATCGATC", 1, max_results=100)
top = result.get_top_matches(5)             # sorted by count, descending
for m in top:
    print(m.kmer, m.count, m.distance)      # distance may be None for wildcard hits
```

`PyFuzzyResult` fields: `query_kmer`, `exact_match` (or `None`), `matches`, `total_matches`, `mutation_tolerance`, `query_time_ms`, `has_position_mutations`. Helper methods: `get_matches_by_distance(d)`, `get_top_matches(n)`, `to_json()`, `to_csv()`, `to_tsv()`.

Each `PyFuzzyMatch` exposes `kmer`, `count`, `distance`, `match_type` (`"exact"`, `"wildcard_expansion[...]"`, `"mutation_tolerance[...]"`), and `mutation_positions`.

### Position-specific mutations

```python
# Up to 1 mutation among positions 0 and 1
result = fq.query_fuzzy_position("ATCGATCGATC", 1, "0,1:1")
print(result.has_position_mutations)   # True
```

### Exporting results

```python
result = fq.query_fuzzy("ATCGATCGATN", 1)
with open("fuzzy.json", "w") as f:
    f.write(result.to_json())
with open("fuzzy.csv", "w") as f:
    f.write(result.to_csv())
```

## 7. Real-World Pattern: SNP-Tolerant Marker Lookup

```python
from pyrustkmer import PyDatabase, PyFuzzyQuery, LoadMode

db = PyDatabase("markers.rkdb", LoadMode.Preload)
fq = PyFuzzyQuery(db)

# Marker sequence with a known variable site; tolerate sequencing errors
marker = "ATCGATCGATCGATCGATCGA"

# 1. wildcard at the variable site only
wildcard = fq.query_fuzzy(marker[:8] + "N" + marker[9:], 0)

# 2. tolerate one error anywhere (catches flanking sequencing noise)
tolerant = fq.query_fuzzy(marker, 1)

print(f"wildcard hits: {wildcard.total_matches}, tolerant hits: {tolerant.total_matches}")
for m in tolerant.get_top_matches(10):
    print(f"{m.kmer}\t{m.count}\t{m.match_type}")
```

## 8. Performance Notes

- Variant generation dominates cost: with `-m 2` on k=31 the engine generates `C(31,0)*3^0 + C(31,1)*3^1 + C(31,2)*3^2 = 1 + 93 + 4185` variants. Raise `-M` only if you need them all.
- `--profile` prints per-stage timings for a single query.
- The Python `PyFuzzyQuery` reloads the database file per query; for many queries prefer one `fuzzy-query-batch` (CLI) run or reuse patterns in a single session.
- `max_results` on `query_fuzzy` caps returned matches without changing variant generation.

## Runnable Example Scripts

- `examples/bash/04_fuzzy_search.sh` — CLI fuzzy walkthrough against the demo rice genome (written against an older CLI; prefer the flags shown in this page)
- `examples/python/demo_fuzzy.py` — N-wildcard pattern matching with real genomic data
- `examples/python/demo_fuzzy_enhanced.py` — extended fuzzy demo
- `examples/python/demo_position_mutations_fixed.py` — position-mutation usage with the current parameter names
- `examples/python/validate_position_mutations.py` — position-mutation validation without large databases

## Next Steps

- [Basic Usage](basic-usage.md) and [Batch Processing](batch-processing.md)
- [Advanced Features](advanced.md) for prefix and hybrid pattern queries
- Python examples: [README](python/README.md)
