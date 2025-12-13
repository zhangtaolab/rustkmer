#!/usr/bin/env python3
"""Large dataset processing example for rustkmer Python bindings.

This example demonstrates memory-efficient processing of large k-mer databases
using streaming and batch operations.
"""

import sys
import time
from pathlib import Path
from collections import Counter

# Add parent directory to path for development
sys.path.insert(0, str(Path(__file__).parent.parent))

from rustkmer import Database, QueryResult
from rustkmer.exceptions import RustKmerError


def analyze_kmer_distribution(db_path: str, sample_size: int = 10000):
    """Analyze k-mer count distribution in the database."""
    print(f"Analyzing k-mer distribution (sample: {sample_size:,})")

    try:
        with Database(db_path) as db:
            # Initialize counters
            count_distribution = Counter()
            total_kmers = 0
            total_count = 0
            max_count = 0
            max_kmer = ""

            start_time = time.time()

            # Stream dump and collect statistics
            print("  Processing k-mers...")
            for result in db.dump(limit=sample_size):
                count_distribution[result.count] += 1
                total_kmers += 1
                total_count += result.count

                if result.count > max_count:
                    max_count = result.count
                    max_kmer = result.kmer

                # Progress indicator
                if total_kmers % 1000 == 0:
                    print(f"  Processed {total_kmers:,} k-mers...")

            duration = time.time() - start_time
            print(f"  Completed in {duration:.2f} seconds")
            print(f"  Rate: {total_kmers/duration:.0f} k-mers/second")
            print()

            # Display distribution summary
            print("  K-mer count distribution:")
            for count, frequency in sorted(count_distribution.items(), reverse=True)[:10]:
                print(f"    {count:8d} k-mers appear {frequency:4d} times")

            print()
            print(f"  Summary:")
            print(f"    Total k-mers processed: {total_kmers:,}")
            print(f"    Total count sum: {total_count:,}")
            print(f"    Maximum count: {max_count:,} (k-mer: {max_kmer})")
            print(f"    Average count: {total_count/total_kmers:.2f}")

            return {
                'total_kmers': total_kmers,
                'total_count': total_count,
                'max_count': max_count,
                'max_kmer': max_kmer,
                'count_distribution': count_distribution
            }

    except RustKmerError as e:
        print(f"✗ Error: {e}")
        return None


def find_high_frequency_kmers(db_path: str, threshold: int = 1000, limit: int = 100):
    """Find k-mers with high frequency counts."""
    print(f"Finding k-mers with count >= {threshold:,} (limit: {limit})")

    try:
        with Database(db_path) as db:
            high_freq_kmers = []
            total_checked = 0

            start_time = time.time()

            for result in db.dump():
                total_checked += 1

                if result.count >= threshold:
                    high_freq_kmers.append(result)

                    # Sort and keep top N
                    if len(high_freq_kmers) > limit:
                        high_freq_kmers.sort(key=lambda x: x.count, reverse=True)
                        high_freq_kmers = high_freq_kmers[:limit]

                # Progress indicator
                if total_checked % 10000 == 0:
                    print(f"  Checked {total_checked:,} k-mers, found {len(high_freq_kmers)} high-frequency")

            duration = time.time() - start_time
            print(f"  Completed in {duration:.2f} seconds")
            print(f"  Total k-mers checked: {total_checked:,}")
            print(f"  High-frequency k-mers found: {len(high_freq_kmers)}")
            print()

            # Display results
            print("  Top high-frequency k-mers:")
            for i, result in enumerate(high_freq_kmers, 1):
                print(f"    {i:3d}. {result.kmer}: {result.count:,}")

            return high_freq_kmers

    except RustKmerError as e:
        print(f"✗ Error: {e}")
        return []


def stream_processing_example():
    """Demonstrate memory-efficient stream processing."""
    db_path = "/Users/forrest/Data/data/kmer/K19/R1_001.rkdb"

    print("=== Memory-Efficient Stream Processing ===\n")
    print(f"Database: {db_path}")
    print()

    try:
        with Database(db_path) as db:
            # Get stats first
            stats = db.stats()
            print(f"Database stats: {stats.unique_kmers:,} unique k-mers")
            print(f"File size: {stats.file_size:,} bytes")
            print()

            # Process in chunks to avoid memory issues
            chunk_size = 1000
            processed = 0

            print(f"Processing k-mers in chunks of {chunk_size:,}...")
            start_time = time.time()

            for chunk_num in range(1, 100):  # Process up to 100 chunks
                chunk_kmers = []
                for i, result in enumerate(db.dump(limit=chunk_size, offset=(chunk_num-1)*chunk_size)):
                    chunk_kmers.append(result)
                    processed += 1
                    if i >= chunk_size - 1:
                        break

                if not chunk_kmers:
                    break

                # Process chunk (example: count k-mers with count > 100)
                high_count_in_chunk = [k for k in chunk_kmers if k.count > 100]

                if high_count_in_chunk:
                    avg_count = sum(k.count for k in high_count_in_chunk) / len(high_count_in_chunk)
                    print(f"  Chunk {chunk_num:3d}: {len(chunk_kmers)} k-mers, "
                          f"{len(high_count_in_chunk)} with count > 100, "
                          f"avg count={avg_count:.1f}")
                else:
                    print(f"  Chunk {chunk_num:3d}: {len(chunk_kmers)} k-mers processed")

                # Early termination if database is smaller than expected
                if len(chunk_kmers) < chunk_size:
                    print(f"  Reached end of database after {processed:,} k-mers")
                    break

            duration = time.time() - start_time
            print()
            print(f"✓ Stream processing completed!")
            print(f"  Total k-mers processed: {processed:,}")
            print(f"  Processing time: {duration:.2f} seconds")
            print(f"  Memory usage: Constant (streaming)")

    except RustKmerError as e:
        print(f"✗ Error: {e}")
        return False

    return True


def main():
    """Run large dataset processing examples."""
    print("RustKmer Python Bindings - Large Dataset Examples\n")

    # Example 1: Analyze k-mer distribution
    db_path = "/Users/forrest/Data/data/kmer/K19/R1_001.rkdb"

    print("=== K-mer Distribution Analysis ===")
    distribution = analyze_kmer_distribution(db_path, sample_size=5000)

    if distribution:
        print("\n=== High-Frequency K-mer Discovery ===")
        find_high_frequency_kmers(db_path, threshold=100, limit=20)
    else:
        print("\nSkipping high-frequency search due to analysis error.")

    print()

    # Example 2: Stream processing demonstration
    if stream_processing_example():
        print("\n✓ All examples completed successfully!")
    else:
        print("\n✗ Stream processing failed")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())