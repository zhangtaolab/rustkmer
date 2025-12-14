#!/usr/bin/env python3
"""
Fuzzy Query Demo for rustkmer Python API

This script demonstrates the fuzzy query functionality for finding
k-mers within specified mutation tolerance.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rustkmer import Database, FuzzyMatchResult, FuzzyQueryResult, FuzzyBatchResult
from rustkmer.exceptions import (
    InvalidKmerError, InvalidMutationToleranceError, QueryError
)


def demo_single_fuzzy_query():
    """Demonstrate single fuzzy query functionality."""
    print("=" * 60)
    print("DEMO 1: Single Fuzzy Query")
    print("=" * 60)

    # Use test database
    test_db = os.path.join(os.path.dirname(__file__), '..', 'tests', 'test_data', 'tiny_test.rkdb')

    if not os.path.exists(test_db):
        print(f"Test database not found: {test_db}")
        print("Please ensure the test database is available.")
        return

    try:
        with Database(test_db) as db:
            print(f"Database: {test_db}")
            print(f"K-mer size: {db.kmer_size}")
            print()

            # Query with 1 mutation tolerance
            query_kmer = "ATCGATC"
            print(f"Querying: {query_kmer}")
            print("Mutation tolerance: 1")
            print("-" * 40)

            result = db.fuzzy_query(query_kmer, mutations=1)

            print(f"Total matches found: {result.total_matches}")
            print(f"Has exact match: {result.has_exact_match}")

            if result.has_exact_match:
                print(f"Exact match count: {result.exact_match.count}")

            # Display top matches
            top_matches = result.get_top_matches(5)
            if top_matches:
                print("\nTop 5 matches:")
                for i, match in enumerate(top_matches, 1):
                    match_type = "EXACT" if match.distance == 0 else f"Distance {match.distance}"
                    mutations = f" ({', '.join(match.mutations)})" if match.mutations else ""
                    print(f"{i}. {match.kmer}: {match.count} [{match_type}]{mutations}")

            # Export results
            print("\n--- JSON Export ---")
            json_result = result.to_json()
            print(json_result[:200] + "..." if len(json_result) > 200 else json_result)

            print("\n--- Table Export ---")
            table_result = result.to_table(max_rows=3)
            print(table_result)

    except Exception as e:
        print(f"Error: {e}")


def demo_batch_fuzzy_query():
    """Demonstrate batch fuzzy query functionality."""
    print("\n" + "=" * 60)
    print("DEMO 2: Batch Fuzzy Query")
    print("=" * 60)

    test_db = os.path.join(os.path.dirname(__file__), '..', 'tests', 'test_data', 'tiny_test.rkdb')

    if not os.path.exists(test_db):
        print(f"Test database not found: {test_db}")
        return

    try:
        with Database(test_db) as db:
            # Define multiple k-mers to query
            kmers = ["ATCGATC", "GATCGAT", "TCGATCG", "CGATCGA"]

            print(f"Querying {len(kmers)} k-mers in parallel...")
            print(f"K-mers: {', '.join(kmers)}")
            print("Mutation tolerance: 1")
            print("Workers: 4")
            print("-" * 40)

            # Perform batch query
            batch_result = db.fuzzy_query_batch(
                kmers,
                mutations=1,
                max_workers=4
            )

            # Display summary
            print("\nBatch Summary:")
            print(batch_result.get_summary_table())

            # Show individual results
            print("\nIndividual Results:")
            for i, result in enumerate(batch_result.query_results, 1):
                status = "✓" if result.matches else "✗"
                exact = " (exact)" if result.has_exact_match else ""
                print(f"{i}. {status} {result.query_kmer}: {result.total_matches} matches{exact}")

    except Exception as e:
        print(f"Error: {e}")


def demo_mutation_tolerance():
    """Demonstrate different mutation tolerance levels."""
    print("\n" + "=" * 60)
    print("DEMO 3: Mutation Tolerance Comparison")
    print("=" * 60)

    test_db = os.path.join(os.path.dirname(__file__), '..', 'tests', 'test_data', 'tiny_test.rkdb')

    if not os.path.exists(test_db):
        print(f"Test database not found: {test_db}")
        return

    try:
        with Database(test_db) as db:
            query_kmer = "ATCGATC"

            # Test different mutation tolerances
            for mutations in [0, 1, 2]:
                print(f"\nMutation tolerance: {mutations}")
                print("-" * 30)

                try:
                    result = db.fuzzy_query(query_kmer, mutations=mutations)
                    print(f"Total matches: {result.total_matches}")

                    # Group by distance
                    grouped = result.get_matches_by_distance()
                    for distance, matches in sorted(grouped.items()):
                        print(f"  Distance {distance}: {len(matches)} matches")

                except Exception as e:
                    print(f"  Error: {e}")

    except Exception as e:
        print(f"Error: {e}")


def demo_error_handling():
    """Demonstrate error handling."""
    print("\n" + "=" * 60)
    print("DEMO 4: Error Handling")
    print("=" * 60)

    test_db = os.path.join(os.path.dirname(__file__), '..', 'tests', 'test_data', 'tiny_test.rkdb')

    if not os.path.exists(test_db):
        print(f"Test database not found: {test_db}")
        return

    try:
        with Database(test_db) as db:
            # Test invalid k-mer
            print("Testing invalid k-mer:")
            try:
                db.fuzzy_query("INVALID", mutations=1)
            except InvalidKmerError as e:
                print(f"  ✓ Caught InvalidKmerError: {e}")

            # Test invalid mutation tolerance
            print("\nTesting invalid mutation tolerance:")
            try:
                db.fuzzy_query("ATCGATC", mutations=10)
            except InvalidMutationToleranceError as e:
                print(f"  ✓ Caught InvalidMutationToleranceError: {e}")

            # Test negative mutations
            print("\nTesting negative mutations:")
            try:
                db.fuzzy_query("ATCGATC", mutations=-1)
            except InvalidMutationToleranceError as e:
                print(f"  ✓ Caught InvalidMutationToleranceError: {e}")

    except Exception as e:
        print(f"Unexpected error: {e}")


def main():
    """Run all demonstrations."""
    print("RustKmer Python Fuzzy Query Demo")
    print("=" * 60)
    print("This demo shows the fuzzy query functionality for finding")
    print("similar k-mers within specified mutation tolerance.\n")

    demo_single_fuzzy_query()
    demo_batch_fuzzy_query()
    demo_mutation_tolerance()
    demo_error_handling()

    print("\n" + "=" * 60)
    print("Demo complete! For more information, see:")
    print("- Python package documentation")
    print("- Quick start guide: python/rustkmer/examples/quickstart.md")
    print("- Test suite: python -m pytest python/tests/test_fuzzy_query.py")


if __name__ == "__main__":
    main()