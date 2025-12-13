#!/usr/bin/env python3
"""Basic usage example for rustkmer Python bindings.

This example demonstrates the core functionality of the rustkmer package:
- Opening a database
- Querying single k-mers
- Getting database statistics
- Using the context manager
"""

import sys
from pathlib import Path

# Add parent directory to path for development
sys.path.insert(0, str(Path(__file__).parent.parent))

from rustkmer import Database, QueryResult
from rustkmer.exceptions import (
    DatabaseNotFoundError,
    InvalidKmerError,
    RustKmerError,
)


def main():
    """Demonstrate basic rustkmer usage."""
    # Database file path - replace with your actual database
    db_path = "/Users/forrest/Data/data/kmer/K19/R1_001.rkdb"

    print("=== RustKmer Python Bindings - Basic Usage Example ===\n")

    try:
        # Example 1: Open database with context manager (recommended)
        print("1. Opening database with context manager...")
        with Database(db_path) as db:
            print(f"   Database: {db.path}")
            print(f"   Loaded: {db.is_loaded}")

            # Example 2: Query a single k-mer
            print("\n2. Querying single k-mers...")
            test_kmers = ["ATCGATCGATCGATCGATCG", "CCCCCCCCCCCCCCCCCCCC", "GGGGGGGGGGGGGGGGGGGG"]

            for kmer in test_kmers:
                try:
                    result = db.query(kmer)
                    print(f"   {kmer}: count={result.count}, canonical={result.canonical}")
                except InvalidKmerError as e:
                    print(f"   {kmer}: Error - {e}")

            # Example 3: Batch queries
            print("\n3. Performing batch queries...")
            batch_kmers = ["ATCGATCGATCGATCGATCG", "GCTAGCTAGCTAGCTAGCTA", "TATATATATATATATATATA"]

            # Execute batch queries in parallel
            results = db.query_batch(batch_kmers, max_workers=3)

            print("   Batch results:")
            for original_kmer, result in results.items():
                status = "found" if result.is_present else "not found"
                print(f"   {original_kmer}: {result.count} ({status})")

            # Example 4: Get database statistics
            print("\n4. Getting database statistics...")
            stats = db.stats()
            print(f"   K-mer size: {stats.kmer_size}")
            print(f"   Unique k-mers: {stats.unique_kmers:,}")
            print(f"   Total counts: {stats.total_counts:,}")
            print(f"   Max count: {stats.max_count:,}")
            print(f"   File size: {stats.file_size:,} bytes")
            print(f"   Format version: {stats.format_version}")
            print(f"   Average count: {stats.average_count:.2f}")

            # Example 5: Dump k-mers (limited)
            print("\n5. Dumping first 5 k-mers...")
            count = 0
            for result in db.dump(limit=5):
                print(f"   {result.kmer}: {result.count}")
                count += 1
            print(f"   Total dumped: {count}")

        print("\n✓ All examples completed successfully!")

    except DatabaseNotFoundError:
        print(f"✗ Error: Database not found at '{db_path}'")
        print("  Please ensure the database file exists and is accessible.")
        print("  You can also change the db_path variable in this script.")
        sys.exit(1)

    except InvalidKmerError as e:
        print(f"✗ Error: Invalid k-mer sequence - {e}")
        sys.exit(1)

    except RustKmerError as e:
        print(f"✗ RustKmer error occurred: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()