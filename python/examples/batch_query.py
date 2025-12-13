#!/usr/bin/env python3
"""Batch query example for rustkmer Python bindings.

This example demonstrates efficient batch querying of k-mers
using parallel subprocess calls.
"""

import time
from pathlib import Path
import sys

# Add parent directory to path for development
sys.path.insert(0, str(Path(__file__).parent.parent))

from rustkmer import Database
from rustkmer.exceptions import RustKmerError


def generate_test_kmers(num_kmers: int, kmer_size: int = 20) -> list[str]:
    """Generate test k-mer sequences."""
    import random

    # Simple random DNA sequence generator
    bases = ['A', 'T', 'C', 'G']
    kmers = []

    for _ in range(num_kmers):
        kmer = ''.join(random.choices(bases, k=kmer_size))
        kmers.append(kmer)

    return kmers


def benchmark_batch_query():
    """Benchmark batch query performance."""
    db_path = "/Users/forrest/Data/data/kmer/K19/R1_001.rkdb"

    print("=== Batch Query Benchmark ===\n")

    # Test different batch sizes
    batch_sizes = [10, 50, 100, 500, 1000]

    try:
        with Database(db_path) as db:
            print(f"Database: {db.path}")
            print(f"Database loaded: {db.is_loaded}")
            print(f"K-mer size: {db.kmer_size}")
            print()

            stats = db.stats()
            print(f"Database stats: {stats.unique_kmers:,} unique k-mers")
            print()

            # Generate test kmers
            max_batch = max(batch_sizes)
            print(f"Generating {max_batch} test k-mers...")
            test_kmers = generate_test_kmers(max_batch, db.kmer_size)
            print("✓ Done\n")

            # Benchmark different batch sizes
            for batch_size in batch_sizes:
                print(f"Testing batch size: {batch_size}")

                kmers_to_query = test_kmers[:batch_size]

                # Time the batch query
                start_time = time.time()
                results = db.query_batch(kmers_to_query, max_workers=4)
                end_time = time.time()

                duration = end_time - start_time
                successful_queries = sum(1 for r in results.values() if r.count > 0)

                print(f"   Duration: {duration:.3f} seconds")
                print(f"   Queries per second: {batch_size/duration:.0f}")
                print(f"   Successful queries: {successful_queries}/{batch_size}")
                print(f"   Average time per query: {duration*1000/batch_size:.2f} ms")
                print()

            print("✓ Benchmark completed!")

    except RustKmerError as e:
        print(f"✗ Error: {e}")
        return False

    return True


def compare_serial_vs_parallel():
    """Compare serial vs parallel query performance."""
    db_path = "/Users/forrest/Data/data/kmer/K19/R1_001.rkdb"
    num_queries = 100

    print("=== Serial vs Parallel Comparison ===\n")

    try:
        with Database(db_path) as db:
            # Generate test kmers
            test_kmers = generate_test_kmers(num_queries, db.kmer_size)

            # Serial queries
            print(f"Running {num_queries} serial queries...")
            start_time = time.time()

            for kmer in test_kmers:
                try:
                    result = db.query(kmer)
                except Exception as e:
                    print(f"   Error querying {kmer}: {e}")

            serial_duration = time.time() - start_time
            print(f"   Serial duration: {serial_duration:.3f} seconds")
            print(f"   Serial rate: {num_queries/serial_duration:.0f} queries/sec")
            print()

            # Parallel queries
            print(f"Running {num_queries} parallel queries...")
            start_time = time.time()

            results = db.query_batch(test_kmers, max_workers=8)

            parallel_duration = time.time() - start_time
            successful_queries = sum(1 for r in results.values() if r.count > 0)
            print(f"   Parallel duration: {parallel_duration:.3f} seconds")
            print(f"   Parallel rate: {num_queries/parallel_duration:.0f} queries/sec")
            print(f"   Successful queries: {successful_queries}/{num_queries}")
            print()

            # Calculate speedup
            speedup = serial_duration / parallel_duration if parallel_duration > 0 else 0
            print(f"Speedup: {speedup:.2f}x faster")

    except RustKmerError as e:
        print(f"✗ Error: {e}")
        return False

    return True


def main():
    """Run batch query examples."""
    print("RustKmer Python Bindings - Batch Query Examples\n")

    # Run benchmark
    if not benchmark_batch_query():
        print("✗ Benchmark failed")
        return

    print()

    # Run comparison
    if not compare_serial_vs_parallel():
        print("✗ Comparison failed")
        return

    print("\n✓ All batch query examples completed!")


if __name__ == "__main__":
    main()