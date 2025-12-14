#!/usr/bin/env python3
"""Test N wildcard support in fuzzy query."""

import sys
from pathlib import Path

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

from rustkmer import Database

def test_n_wildcards():
    """Test fuzzy query with N wildcards."""

    test_db = Path(__file__).parent / "python" / "tests" / "test_data" / "tiny_test.rkdb"

    if not test_db.exists():
        print(f"Test database not found: {test_db}")
        return

    print("Testing N wildcard support in fuzzy query...")

    with Database(test_db) as db:
        # Test single N
        print("\n1. Testing 'ATTTNAA':")
        try:
            result = db.fuzzy_query("ATTTNAA", mutations=1)
            print(f"   Query: {result.query_kmer}")
            print(f"   Total matches: {result.total_matches}")
            print(f"   Has exact match: {result.has_exact_match}")
            for match in result.get_top_matches(5):
                print(f"   Match: {match.kmer} (count={match.count}, distance={match.distance})")
        except Exception as e:
            print(f"   Error: {e}")

        # Test multiple Ns
        print("\n2. Testing 'AAANNNTTT':")
        try:
            result = db.fuzzy_query("AAANNNTTT", mutations=0)
            print(f"   Query: {result.query_kmer}")
            print(f"   Total matches: {result.total_matches}")
            for match in result.get_top_matches(5):
                print(f"   Match: {match.kmer} (count={match.count}, distance={match.distance})")
        except Exception as e:
            print(f"   Error: {e}")

        # Test N at the end
        print("\n3. Testing 'AAAAAAN':")
        try:
            result = db.fuzzy_query("AAAAAAN", mutations=0)
            print(f"   Query: {result.query_kmer}")
            print(f"   Total matches: {result.total_matches}")
            for match in result.get_top_matches(5):
                print(f"   Match: {match.kmer} (count={match.count}, distance={match.distance})")
        except Exception as e:
            print(f"   Error: {e}")

        # Test all Ns
        print("\n4. Testing 'NNNNNNN':")
        try:
            result = db.fuzzy_query("NNNNNNN", mutations=0)
            print(f"   Query: {result.query_kmer}")
            print(f"   Total matches: {result.total_matches}")
            print(f"   Note: This might be slow as it generates all 4^7 = 16384 variants")
            for match in result.get_top_matches(3):
                print(f"   Match: {match.kmer} (count={match.count}, distance={match.distance})")
        except Exception as e:
            print(f"   Error: {e}")

        # Test batch query with N wildcards
        print("\n5. Testing batch query with N wildcards:")
        try:
            queries = ["ATTTNAA", "AAANNNTTT", "AAAAAAN"]
            batch_result = db.fuzzy_query_batch(queries, mutations=1)
            print(f"   Total queries: {batch_result.total_queries}")
            print(f"   Total matches: {batch_result.total_matches}")
            for result in batch_result.query_results:
                print(f"   Query {result.query_kmer}: {result.total_matches} matches")
        except Exception as e:
            print(f"   Error: {e}")

if __name__ == "__main__":
    test_n_wildcards()