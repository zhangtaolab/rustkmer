#!/usr/bin/env python3
"""Test N wildcard support with actual k-mers from the database."""

import sys
from pathlib import Path

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

from rustkmer import Database

def test_n_wildcards_real():
    """Test fuzzy query with N wildcards using known k-mers."""

    test_db = Path(__file__).parent / "python" / "tests" / "test_data" / "tiny_test.rkdb"

    if not test_db.exists():
        print(f"Test database not found: {test_db}")
        return

    print("Testing N wildcard support with real examples...")

    with Database(test_db) as db:
        # Test 1: Replace one base with N in a known k-mer
        print("\n1. Testing 'AAACANT' (based on known k-mer 'AAACAGT'):")
        try:
            result = db.fuzzy_query("AAACANT", mutations=0)
            print(f"   Query: {result.query_kmer}")
            print(f"   Total matches: {result.total_matches}")
            for match in result.get_top_matches(5):
                print(f"   Match: {match.kmer} (count={match.count}, distance={match.distance})")
        except Exception as e:
            print(f"   Error: {e}")

        # Test 2: Replace one base with N and allow 1 mutation
        print("\n2. Testing 'AAACANT' with mutations=1:")
        try:
            result = db.fuzzy_query("AAACANT", mutations=1)
            print(f"   Query: {result.query_kmer}")
            print(f"   Total matches: {result.total_matches}")
            for match in result.get_top_matches(5):
                print(f"   Match: {match.kmer} (count={match.count}, distance={match.distance})")
        except Exception as e:
            print(f"   Error: {e}")

        # Test 3: Multiple Ns but limited variants
        print("\n3. Testing 'AAANNNN' (two Ns):")
        try:
            result = db.fuzzy_query("AAANNNN", mutations=0)
            print(f"   Query: {result.query_kmer}")
            print(f"   Total matches: {result.total_matches}")
            for match in result.get_top_matches(5):
                print(f"   Match: {match.kmer} (count={match.count}, distance={match.distance})")
        except Exception as e:
            print(f"   Error: {e}")

        # Test 4: Compare exact vs N wildcard
        print("\n4. Comparing exact 'AAACAGT' vs wildcard 'AAACANT':")
        try:
            exact_result = db.fuzzy_query("AAACAGT", mutations=0)
            wildcard_result = db.fuzzy_query("AAACANT", mutations=0)
            print(f"   Exact 'AAACAGT': {exact_result.total_matches} matches")
            print(f"   Wildcard 'AAACANT': {wildcard_result.total_matches} matches")

            if wildcard_result.matches:
                print("   Wildcard matches:")
                for match in wildcard_result.get_top_matches(5):
                    print(f"     {match.kmer} (count={match.count})")
        except Exception as e:
            print(f"   Error: {e}")

        # Test 5: Mixed N and mutations
        print("\n5. Testing 'ANACAGT' with mutations=1 (N + mutation):")
        try:
            result = db.fuzzy_query("ANACAGT", mutations=1)
            print(f"   Query: {result.query_kmer}")
            print(f"   Total matches: {result.total_matches}")
            for match in result.get_top_matches(5):
                print(f"   Match: {match.kmer} (count={match.count}, distance={match.distance})")
        except Exception as e:
            print(f"   Error: {e}")

        # Test 6: Batch query with mixed patterns
        print("\n6. Batch query with mixed patterns:")
        try:
            queries = ["AAACANT", "AAANNNN", "ANACAGT"]
            batch_result = db.fuzzy_query_batch(queries, mutations=1, max_variants=1000)
            print(f"   Total queries: {batch_result.total_queries}")
            print(f"   Total matches: {batch_result.total_matches}")
            for result in batch_result.query_results:
                print(f"   Query {result.query_kmer}: {result.total_matches} matches")
                if result.matches:
                    print(f"     Top match: {result.matches[0].kmer}")
        except Exception as e:
            print(f"   Error: {e}")

if __name__ == "__main__":
    test_n_wildcards_real()