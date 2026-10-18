<!-- generated-by: gsd-doc-writer -->
# Python API Examples

This page provides comprehensive examples of using the rustkmer Python API (`pyrustkmer`) for various bioinformatics applications. The examples range from basic usage to advanced workflows, demonstrating real-world use cases and best practices.

## Table of Contents

- [Basic Usage Examples](#basic-usage-examples)
- [Database Operations](#database-operations)
- [Query and Analysis Examples](#query-and-analysis-examples)
- [Performance Optimization](#performance-optimization)
- [Integration with Bioinformatics Tools](#integration-with-bioinformatics-tools)

---

## Basic Usage Examples

### Querying an Existing Database

```python
#!/usr/bin/env python3
"""Basic pyrustkmer usage: open a database and inspect it."""

from pyrustkmer import PyDatabase, LoadMode

def basic_example():
    """Demonstrate basic database inspection and querying."""

    db = PyDatabase("example.rkdb", LoadMode.Preload)

    # Query a single k-mer (must be exactly db.kmer_size characters)
    kmer = "ATCGATCGATCGATCGATCGATCGATCGATC"
    result = db.query_exact(kmer)

    print(f"Query: {kmer}")
    print(f"Found: {result.found}")
    print(f"Count: {result.count}")

    # Existence check
    print(f"Exists: {db.exists(kmer)}")

    # Database statistics
    stats = db.get_stats()
    print(f"\nK-mer size: {stats.kmer_size}")
    print(f"Unique k-mers: {stats.unique_kmers:,}")
    print(f"Total k-mers: {stats.total_kmers:,}")
    print(f"File size: {stats.file_size:,} bytes")
    print(f"Canonical: {stats.canonical}")

    # Memory / mode introspection
    print(f"\nDatabase info: {db.database_info()}")
    print(f"Memory usage: {db.get_memory_usage()}")

if __name__ == "__main__":
    basic_example()
```

### Creating and Querying Databases

```python
#!/usr/bin/env python3
"""Create a k-mer database from sequences and query it."""

import os
import tempfile

from pyrustkmer import PyCounter, PyDatabase, LoadMode

def create_and_query_database():
    """Create a database from sequences and query it."""

    sequences = [
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG",
        "ATCGATCGATCGATCGATCGATCGATCGATCGATCG",  # duplicate of seq 1
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".fasta", delete=False) as f:
        for i, seq in enumerate(sequences):
            f.write(f">seq_{i + 1}\n{seq}\n")
        fasta_file = f.name

    try:
        print("=== Creating k-mer database ===")

        counter = PyCounter(31, canonical=True)
        counter.add_from_fasta(fasta_file)

        stats = counter.get_stats()
        print(f"Total k-mers: {stats.total_kmers:,}")
        print(f"Unique k-mers: {stats.unique_kmers:,}")

        db_file = "example_database.rkdb"
        counter.save_database(db_file)
        print(f"Database saved to: {db_file}")

        print("\n=== Querying database ===")
        db = PyDatabase(db_file, LoadMode.Preload)

        # Exact query (taken from the first input sequence)
        result1 = db.query_exact(sequences[0][:31])
        print(f"Exact query: found={result1.found}, count={result1.count}")

        # Query a k-mer that was never counted
        result2 = db.query_exact("A" * 31)
        print(f"Absent query: found={result2.found}, count={result2.count}")

        # Single k-mer lookup directly on the counter
        print(f"Counter lookup: {counter.get_count(sequences[0][:31])}")

    finally:
        os.unlink(fasta_file)

if __name__ == "__main__":
    create_and_query_database()
```

---

## Database Operations

### Merging and Comparing Databases

```python
#!/usr/bin/env python3
"""Merge databases with PyDatabase.merge and compare their contents."""

from pathlib import Path
import tempfile

import pandas as pd

from pyrustkmer import PyCounter, PyDatabase, LoadMode

def build_database(sequences, k, db_file):
    """Count a sequence list into a .rkdb file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".fasta", delete=False) as f:
        for i, seq in enumerate(sequences):
            f.write(f">seq_{i + 1}\n{seq}\n")
        fasta_file = f.name

    counter = PyCounter(k, canonical=True)
    counter.add_from_fasta(fasta_file)
    counter.save_database(db_file)

    Path(fasta_file).unlink()
    return counter.get_stats().unique_kmers

def merge_and_compare_databases():
    """Demonstrate database merging and comparison."""

    print("=== Creating sample databases ===")

    k = 21
    db_files = [
        "sample1_k21.rkdb",
        "sample2_k21.rkdb",
    ]

    # Database 1: AT-rich, Database 2: GC-rich
    sample_sequences = [
        ["AT" * 18, "ATCG" * 9],
        ["GC" * 18, "GCTA" * 9],
    ]

    for db_file, seqs in zip(db_files, sample_sequences):
        unique = build_database(seqs, k, db_file)
        print(f"Created {db_file} with {unique:,} unique k-mers")

    try:
        # Merge the databases (same bounded, streaming merge as the CLI)
        print("\n=== Merging databases ===")
        PyDatabase.merge(db_files, "merged_k21.rkdb")

        merged = PyDatabase("merged_k21.rkdb", LoadMode.Preload)
        print(f"Merged unique k-mers: {merged.get_stats().unique_kmers:,}")

        # Compare database contents via decoded k-mer sets
        print("\n=== Comparing databases ===")

        kmer_sets = []
        for db_file in db_files:
            db = PyDatabase(db_file, LoadMode.Preload)
            kmer_sets.append({r.kmer for r in db.export_all_kmers()})

        common = set.intersection(*kmer_sets)
        union = set.union(*kmer_sets)
        print(f"Total unique k-mers across databases: {len(union):,}")
        print(f"Common k-mers in all databases: {len(common):,}")

        # Presence matrix for a sample of the union k-mers
        query_kmers = sorted(union)[:20]

        presence_data = []
        for sample_name, db_file in zip(["sample_1", "sample_2"], db_files):
            db = PyDatabase(db_file, LoadMode.Preload)
            row = {"Sample": sample_name}
            for kmer in query_kmers:
                row[kmer] = 1 if db.exists(kmer) else 0
            presence_data.append(row)

        df = pd.DataFrame(presence_data)
        print("\nPresence matrix (first 10 k-mers):")
        print(df.iloc[:, :11])  # Sample column + first 10 k-mers

    finally:
        for f in db_files + ["merged_k21.rkdb"]:
            if Path(f).exists():
                Path(f).unlink()

if __name__ == "__main__":
    merge_and_compare_databases()
```

### Database Validation

```python
#!/usr/bin/env python3
"""Database validation utilities."""

import hashlib

from pyrustkmer import PyDatabase, LoadMode

def validate_database(db_path):
    """Validate that a database loads and answers queries."""

    try:
        db = PyDatabase(db_path, LoadMode.Preload)

        # Header statistics are readable
        stats = db.get_stats()
        print(f"  k={stats.kmer_size}, unique={stats.unique_kmers:,}, "
              f"sorted={stats.is_sorted}, canonical={stats.canonical}")

        # A well-formed query round-trips without raising
        db.query_exact("A" * stats.kmer_size)

        # Entries are readable with decoded sequences
        entries = db.export_all_kmers(limit=10)
        print(f"  Read {len(entries)} entries successfully")

        return True

    except Exception as e:
        print(f"Database validation failed: {e}")
        return False

def calculate_file_checksum(file_path):
    """Calculate the SHA-256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

if __name__ == "__main__":
    validate_database("example.rkdb")
    print(calculate_file_checksum("example.rkdb"))
```

---

## Query and Analysis Examples

### Fuzzy Query Analysis

```python
#!/usr/bin/env python3
"""Fuzzy query analysis with PyFuzzyQuery."""

from collections import defaultdict

import numpy as np

from pyrustkmer import PyDatabase, PyFuzzyQuery, LoadMode

def analyze_fuzzy_queries():
    """Analyze how mutation tolerance affects match sets."""

    db = PyDatabase("example.rkdb", LoadMode.Preload)
    fuzzy = PyFuzzyQuery(db)

    k = db.kmer_size
    test_kmers = [
        "ATCG" * (k // 4) + "ATC"[: k % 4],  # balanced
        "A" * k,                              # low complexity
        "GC" * ((k + 1) // 2),                # high GC
        "T" * k,                              # homopolymer
    ]

    print("=== Fuzzy Query Analysis ===")

    all_results = []

    for kmer in test_kmers:
        print(f"\nAnalyzing: {kmer[:20]}...")

        for max_mutations in range(3):  # 0, 1, 2 mutations
            result = fuzzy.query_fuzzy(kmer, max_mutations=max_mutations)

            counts = [m.count for m in result.matches]
            analysis = {
                "kmer": kmer,
                "max_mutations": max_mutations,
                "total_matches": result.total_matches,
                "n_matches": len(result.matches),
                "max_count": max(counts) if counts else 0,
                "mean_count": float(np.mean(counts)) if counts else 0.0,
                "query_time_ms": result.query_time_ms,
            }
            all_results.append(analysis)

            print(f"  tolerance {max_mutations}: {result.total_matches} matches "
                  f"({result.query_time_ms} ms)")

    # Mutation-position profile at tolerance 2
    print("\n=== Mutation Position Analysis ===")

    result = fuzzy.query_fuzzy(test_kmers[0], max_mutations=2)

    position_weights = defaultdict(int)
    for match in result.matches:
        for position in match.mutation_positions:
            position_weights[position] += match.count

    total = sum(position_weights.values())
    if total:
        print(f"K-mer: {test_kmers[0][:20]}...")
        for position in sorted(position_weights):
            print(f"  Position {position}: {position_weights[position] / total:.2%}")

    # Distance-filtered and top-N views
    print("\n=== Filtered Views ===")
    print(f"Matches at distance 1: {len(result.get_matches_by_distance(1))}")
    for match in result.get_top_matches(5):
        print(f"  {match.kmer}: {match.count} (distance={match.distance}, "
              f"type={match.match_type})")

    return all_results

if __name__ == "__main__":
    analyze_fuzzy_queries()
```

### Batch Query Processing

```python
#!/usr/bin/env python3
"""Batch exact-query processing with progress tracking."""

import random
import time

import pandas as pd

from pyrustkmer import PyDatabase, LoadMode

class BatchQueryProcessor:
    """Process large query lists in chunks via query_exact_batch."""

    def __init__(self, db_path: str, chunk_size: int = 500):
        self.db = PyDatabase(db_path, LoadMode.Preload)
        self.chunk_size = chunk_size
        self.results = []

    def process(self, queries):
        """Run all queries in chunks, tracking progress."""
        start_time = time.time()

        for i in range(0, len(queries), self.chunk_size):
            chunk = queries[i:i + self.chunk_size]

            # One native call per chunk: dict {kmer: PyQueryResult}
            batch = self.db.query_exact_batch(chunk)

            for kmer, result in batch.items():
                self.results.append({
                    "query": kmer,
                    "found": result.found,
                    "count": result.count,
                })

            done = min(i + self.chunk_size, len(queries))
            print(f"Progress: {done}/{len(queries)}")

        elapsed = time.time() - start_time
        print(f"Processed {len(queries)} queries in {elapsed:.2f}s "
              f"({len(queries) / elapsed:.0f} queries/second)")

        return self.results

    def summary(self):
        """Summarize batch results as a DataFrame."""
        df = pd.DataFrame(self.results)

        found = int(df["found"].sum())
        print(f"Found: {found}/{len(df)} ({found / len(df):.1%})")
        print(f"Mean count of found k-mers: "
              f"{df[df['found']]['count'].mean():.2f}")

        return df

def generate_test_queries(num_queries=1000, kmer_length=31):
    """Generate random test k-mers plus a few known patterns."""
    queries = [
        "".join(random.choices("ACGT", k=kmer_length))
        for _ in range(num_queries)
    ]
    queries.extend([
        "A" * kmer_length,
        "T" * kmer_length,
        "C" * kmer_length,
        "G" * kmer_length,
        "ATCG" * (kmer_length // 4) + "ATC"[: kmer_length % 4],
    ])
    return queries

if __name__ == "__main__":
    queries = generate_test_queries(num_queries=500)
    processor = BatchQueryProcessor("example.rkdb", chunk_size=100)
    processor.process(queries)
    processor.summary()
```

---

## Performance Optimization

### Memory-Efficient Database Processing

```python
#!/usr/bin/env python3
"""Memory-efficient techniques for processing large databases."""

from pyrustkmer import PyDatabase, LoadMode

def process_in_pages(db_path, page_size=100_000):
    """Paginate through a database with bounded Python-side memory.

    Uses LoadMode.Lazy (binary-search lookups, no full cache) plus
    export_all_kmers(limit, offset) pagination. Each PyQueryResult
    carries a decoded k-mer sequence and its count.
    """
    db = PyDatabase(db_path, LoadMode.Lazy)

    total_processed = 0
    offset = 0

    while True:
        page = db.export_all_kmers(limit=page_size, offset=offset)
        if not page:
            break

        for entry in page:
            # ... process entry.kmer / entry.count ...
            pass

        total_processed += len(page)
        offset += page_size
        print(f"Processed {total_processed:,} k-mers...")

    print(f"Done: {total_processed:,} k-mers")
    return total_processed

def stream_database_to_file(db_path, output_file, max_items=None):
    """Stream database contents to disk without materializing them.

    export_to_file is implemented natively and writes one
    "kmer<TAB>count" line per entry; the optional callback receives
    (current, total) progress updates.
    """
    db = PyDatabase(db_path, LoadMode.Preload)

    def track_progress(current, total):
        if current % 100_000 == 0 or current == total:
            print(f"Progress: {current:,}/{total:,}")

    n = db.export_to_file(output_file, limit=max_items,
                          progress_callback=track_progress)
    print(f"Wrote {n:,} k-mers to {output_file}")
    return n

def export_for_downstream_analysis(db_path):
    """Export to CSV/JSON for pandas or other tooling."""
    db = PyDatabase(db_path, LoadMode.Preload)

    n_csv = db.export_to_csv("kmers.csv", limit=1_000_000)
    n_json = db.export_to_json("kmers.json")

    print(f"Exported {n_csv:,} rows to CSV and {n_json:,} entries to JSON")

if __name__ == "__main__":
    process_in_pages("large_genome.rkdb", page_size=100_000)
    stream_database_to_file("large_genome.rkdb", "database_contents.tsv",
                            max_items=500_000)
    export_for_downstream_analysis("large_genome.rkdb")
```

Notes:

- `db.dump()` returns k-mers as hexadecimal strings of their encoded `u128` values; use `export_all_kmers()` when you need decoded nucleotide sequences, or the export methods when you need files.
- `LoadMode.Preload` gives the fastest queries but caches every entry; `LoadMode.Lazy` and `LoadMode.MemoryMapped` trade query speed for a smaller footprint.
- `add_from_fasta` / `add_from_fastq` release the GIL and count in parallel on a Rayon thread pool — control it with `PyCounter(k, canonical=True, threads=8)`.

---

## Integration with Bioinformatics Tools

### BioPython Integration

```python
#!/usr/bin/env python3
"""Integrate pyrustkmer with BioPython for sequence analysis."""

from Bio import SeqIO

from pyrustkmer import PyCounter, PyDatabase, LoadMode

class KmerBioAnalyzer:
    """Combine BioPython parsing with rustkmer counting and queries."""

    def __init__(self, k=31):
        self.k = k
        self.db = None

    def build_database(self, fasta_file):
        """Count a FASTA file into a .rkdb database."""
        db_file = fasta_file + ".rkdb"

        counter = PyCounter(self.k, canonical=True)
        counter.add_from_fasta(fasta_file)
        counter.save_database(db_file)

        stats = counter.get_stats()
        print(f"Database created: {db_file}")
        print(f"Total k-mers: {stats.total_kmers:,}, "
              f"unique: {stats.unique_kmers:,}")

        self.db = PyDatabase(db_file, LoadMode.Preload)
        return db_file

    def query_records(self, fasta_file, max_records=None):
        """Query the first k-mer of each record against the database."""
        results = []

        for i, record in enumerate(SeqIO.parse(fasta_file, "fasta")):
            if max_records is not None and i >= max_records:
                break

            seq = str(record.seq).upper()
            if len(seq) < self.k:
                continue

            kmer = seq[: self.k]
            if "N" in kmer:
                continue  # exact queries accept A/T/C/G only

            result = self.db.query_exact(kmer)
            results.append({
                "id": record.id,
                "kmer": kmer,
                "found": result.found,
                "count": result.count,
            })

        return results

    def kmer_density(self, sequence, window_size=1000, step=100):
        """Compute per-window k-mer hit density for one sequence."""
        seq = str(sequence).upper()
        densities = []

        for start in range(0, max(len(seq) - self.k + 1, 1), step):
            end = min(start + window_size, len(seq))
            window = seq[start:end]

            valid = 0
            found = 0
            for i in range(len(window) - self.k + 1):
                kmer = window[i:i + self.k]
                if "N" in kmer:
                    continue
                valid += 1
                if self.db.exists(kmer):
                    found += 1

            densities.append({
                "start": start,
                "end": end,
                "valid_kmers": valid,
                "found_kmers": found,
                "density": found / valid if valid else 0.0,
            })

        return densities

if __name__ == "__main__":
    analyzer = KmerBioAnalyzer(k=31)
    analyzer.build_database("genome.fasta")

    for r in analyzer.query_records("genome.fasta", max_records=10):
        print(f"{r['id']}: found={r['found']} count={r['count']}")

    first = next(SeqIO.parse("genome.fasta", "fasta"))
    top_windows = sorted(
        analyzer.kmer_density(first.seq),
        key=lambda w: w["density"],
        reverse=True,
    )[:5]
    for window in top_windows:
        print(f"{window['start']}-{window['end']}: density={window['density']:.3f}")
```

---

This examples reference provides comprehensive, real-world examples of using the rustkmer Python API for various bioinformatics applications. Each example uses only the live `pyrustkmer` surface: `PyCounter`, `PyDatabase` (with an explicit `LoadMode`), `PyFuzzyQuery`, and their result classes.
