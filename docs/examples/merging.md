<!-- generated-by: gsd-doc-writer -->
# Merging Databases Examples

Combining multiple `.rkdb` databases into one, with memory-bounded streaming for genome-scale inputs. All commands verified against `rustkmer` 0.5.0 and the live `pyrustkmer` module.

Setup — two compatible databases (same k and same canonical setting):

```bash
printf '>seq1\nATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGGCTAGCTAGCTAGCTA\n>seq2\nATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGTTTTTTTTTTTTTTTT\n' > demo.fa
rustkmer count -k 11 -i demo.fa -o demo_a.rkdb --threads 4
rustkmer count -k 11 -i demo.fa -o demo_b.rkdb --threads 4
```

## 1. Basic Merge (CLI)

```bash
rustkmer merge -i demo_a.rkdb demo_b.rkdb -o merged.rkdb --merge-mode memory
```

```text
Merging 2 databases...
Loading reference database: demo_a.rkdb
Saving merged database to: merged.rkdb
Merge completed successfully!
  Total input databases: 2
  Output database: merged.rkdb
  K-mer size: 11
  Total k-mers: 29
  Time elapsed: 0.00s
  Canonical mode: false
  Sorted: true
```

Merging **sums the counts** of shared k-mers: each input had `total_kmers: 92` over 29 uniques, and the merged database reports 184 total (92 + 92) over the same 29 uniques.

`-i` accepts two or more databases; `-o` is the merged output path.

## 2. Compatibility Rules (and the Real Error Message)

Inputs must agree on k-mer size and canonical mode. A canonical-mode mismatch aborts the merge before any writing:

```bash
rustkmer count -k 11 -i demo.fa -o canonical.rkdb --canonical
rustkmer merge -i demo_a.rkdb canonical.rkdb -o bad_merge.rkdb
```

```text
Merging 2 databases...
Loading reference database: demo_a.rkdb
Error: Database 'canonical.rkdb' has canonical mode true, expected false

Recovery suggestions:
  • Create a new database with canonical mode false
  • Use 'rustkmer count --canonical' or 'rustkmer count --no-canonical' as needed
  • Verify all databases use the same canonical mode before merging
```

Check compatibility without merging:

```bash
rustkmer merge -i demo_a.rkdb demo_b.rkdb -o /dev/null --check-compatibility
```

## 3. Memory-Bounded Merging

For inputs whose combined size exceeds your budget, the merge can stream instead of loading everything:

```bash
# auto (default): stream only when inputs exceed the budget
rustkmer merge -i a.rkdb b.rkdb c.rkdb -o merged.rkdb

# Hard memory ceiling; inputs over budget are streamed automatically
rustkmer merge -i a.rkdb b.rkdb -o merged.rkdb --max-memory 32GB

# Force a strategy
rustkmer merge -i a.rkdb b.rkdb -o merged.rkdb --merge-mode streaming
rustkmer merge -i a.rkdb b.rkdb -o merged.rkdb --merge-mode memory
```

- `--merge-mode auto` routes to streaming when the summed k-mer totals (read from the 42-byte headers) exceed the budget.
- `--merge-mode memory` refuses to run over budget rather than risking an OOM.
- `--merge-mode streaming` always streams; the merged bytes are written directly as the merge proceeds — the merged database is never fully held in RAM.
- Without `--max-memory`, the budget defaults to 50% of system memory.

Additional flags: `--num-threads N` (0 = all cores), `--temp-dir DIR` for streaming spill files, `--use-prefix-cache` + `--batch-size N` for the prefix-cache strategy, `--keep-intermediate` (debugging), `-v`/`-q`.

## 4. Merging from Python

`PyDatabase.merge` is a static method that goes through the same bounded core as the CLI:

```python
from pyrustkmer import PyDatabase, LoadMode

PyDatabase.merge(["demo_a.rkdb", "demo_b.rkdb"], "merged.rkdb")

# With a budget and forced streaming (same grammar as the CLI's --max-memory)
PyDatabase.merge(["a.rkdb", "b.rkdb"], "merged.rkdb",
                 max_memory="4GB", merge_mode="streaming")
```

Behavior verified on the live module:

- `merge_mode` must be one of `"auto"`, `"memory"`, `"streaming"` — anything else raises `ValueError`.
- A missing input file raises `FileNotFoundError` before any work starts.
- An empty database list raises `ValueError`.
- The over-budget `merge_mode="memory"` rejection surfaces as `RuntimeError` carrying the core's message.
- The output file is written directly by the merge; there is no separate save step.

Inspect the result:

```python
db = PyDatabase("merged.rkdb", LoadMode.Preload)
print(db.get_stats())     # PyDatabaseStats(kmer_size=11, total_kmers=184, unique_kmers=29, ...)
```

## 5. Pattern: Cohort Merge (one database per sample)

```bash
# One database per sample, then a cohort-wide merge
for sample in S1 S2 S3; do
    rustkmer count -k 31 -i reads_${sample}.fastq.gz -o ${sample}.rkdb \
        --canonical --threads 8 --quiet
done

rustkmer merge -i S1.rkdb S2.rkdb S3.rkdb -o cohort.rkdb \
    --max-memory 32GB --num-threads 8
```

Shared k-mers accumulate counts across samples — after the merge, `count` is the total observations of that k-mer across the whole cohort (useful for joint fingerprints); per-sample presence/absence requires keeping the individual databases.

```python
# Compare a k-mer's abundance before and after the merge
from pyrustkmer import PyDatabase, LoadMode
cohort = PyDatabase("cohort.rkdb", LoadMode.Lazy)
print(cohort.query_exact("ATCGATCGATCGATCGATCGATCGATCGATC").count)
```

## Runnable Example Scripts

- `examples/bash/02_database_ops.sh` — database creation/inspection workflow used as merge input prep
- `examples/utils/verify_consistency.sh` — output consistency checks

## Next Steps

- [Database Operations](database-ops.md) and [Statistics](statistics.md)
- [Basic Usage](basic-usage.md) for counting fundamentals
