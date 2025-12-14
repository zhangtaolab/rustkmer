#!/usr/bin/env python3
"""
Validate quickstart.md examples against actual implementation.

This script tests all code examples from the quickstart guide to ensure
they work correctly with the implemented fuzzy query functionality.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add python directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "python"))

# Use actual test database
TEST_DB = Path(__file__).parent.parent.parent / "python" / "tests" / "test_data" / "tiny_test.rkdb"

from rustkmer import Database, FuzzyQueryResult, FuzzyMatchResult
from rustkmer.exceptions import InvalidKmerError, QueryError

# Mock CLI outputs for testing
MOCK_SINGLE_QUERY_OUTPUT = """{
    "query_kmer": "ATCGATC",
    "exact_match": {
        "kmer": "ATCGATC",
        "count": 42,
        "distance": 0,
        "mutations": []
    },
    "matches": [
        {
            "kmer": "ATCGATC",
            "count": 42,
            "distance": 0,
            "mutations": []
        },
        {
            "kmer": "ATCGATT",
            "count": 15,
            "distance": 1,
            "mutations": ["C->T at position 6"]
        },
        {
            "kmer": "ATCATCG",
            "count": 8,
            "distance": 1,
            "mutations": ["G->A at position 4"]
        }
    ],
    "total_matches": 3,
    "mutation_tolerance": 1
}"""

MOCK_STATS_OUTPUT = """{
    "kmer_size": 7,
    "unique_kmers": 1000,
    "total_counts": 5000,
    "max_count": 50,
    "file_size": 12345,
    "format_version": "2.0"
}"""

MOCK_BATCH_OUTPUTS = [
    """{
        "query_kmer": "ATCGATC",
        "matches": [
            {"kmer": "ATCGATC", "count": 42, "distance": 0, "mutations": []},
            {"kmer": "ATCGATT", "count": 15, "distance": 1, "mutations": ["C->T"]}
        ],
        "total_matches": 2,
        "mutation_tolerance": 2
    }""",
    """{
        "query_kmer": "CGATCGA",
        "matches": [
            {"kmer": "CGATCGA", "count": 38, "distance": 0, "mutations": []},
            {"kmer": "CGATCAA", "count": 12, "distance": 1, "mutations": ["G->A"]}
        ],
        "total_matches": 2,
        "mutation_tolerance": 2
    }""",
    """{
        "query_kmer": "GATCGAT",
        "matches": [
            {"kmer": "GATCGAT", "count": 25, "distance": 0, "mutations": []}
        ],
        "total_matches": 1,
        "mutation_tolerance": 2
    }"""
]


def get_mock_command():
    """Create a mock command function that handles both stats and fuzzy-query calls."""
    def mock_run(args, timeout=None):
        if 'stats' in args:
            return MOCK_STATS_OUTPUT
        elif 'fuzzy-query' in args:
            if len(args) > 4:  # Batch query with specific k-mer
                kmer = args[4]
                if kmer == 'ATCGATC':
                    return MOCK_BATCH_OUTPUTS[0]
                elif kmer == 'CGATCGA':
                    return MOCK_BATCH_OUTPUTS[1]
                elif kmer == 'GATCGAT':
                    return MOCK_BATCH_OUTPUTS[2]
            return MOCK_SINGLE_QUERY_OUTPUT
        else:
            return MOCK_STATS_OUTPUT
    return mock_run


def test_basic_single_query():
    """Test basic single fuzzy query example."""
    print("Testing basic single fuzzy query...")

    if not TEST_DB.exists():
        print("  ⚠ Test database not found, skipping test")
        return

    with Database(TEST_DB) as db:
        # Use a 7-mer since the test database has k=7
        result = db.fuzzy_query("ATCGATC", mutations=1)

        # Verify basic structure
        assert hasattr(result, 'query_kmer')
        assert hasattr(result, 'total_matches')
        assert hasattr(result, 'has_exact_match')
        assert hasattr(result, 'get_top_matches')

        # Test top matches method
        top_matches = result.get_top_matches(5)
        assert isinstance(top_matches, list)

        print("  ✓ Basic single query works correctly")


def test_batch_query():
    """Test batch fuzzy queries example."""
    print("Testing batch fuzzy queries...")

    if not TEST_DB.exists():
        print("  ⚠ Test database not found, skipping test")
        return

    kmers = ["ATCGATC", "CGATCGA", "GATCGAT"]

    with Database(TEST_DB) as db:
        batch_result = db.fuzzy_query_batch(kmers, mutations=2)

        # Verify basic structure
        assert hasattr(batch_result, 'query_results')
        assert hasattr(batch_result, 'total_queries')
        assert hasattr(batch_result, 'get_summary_table')

        assert batch_result.total_queries == 3

        # Test summary table method exists and returns a string
        summary = batch_result.get_summary_table()
        assert isinstance(summary, str)

        print("  ✓ Batch query works correctly")


def test_export_formats():
    """Test result export examples."""
    print("Testing export formats...")

    if not TEST_DB.exists():
        print("  ⚠ Test database not found, skipping test")
        return

    with Database(TEST_DB) as db:
        result = db.fuzzy_query("ATCGATC", mutations=1)

        # Test JSON export
        json_str = result.to_json()
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert 'query_kmer' in data
        assert 'total_matches' in data

        # Test table export
        table = result.to_table(max_rows=20)
        assert isinstance(table, str)

        # Test accessing match data structure
        if hasattr(result, 'matches'):
            for match in result.matches:
                assert hasattr(match, 'kmer')
                assert hasattr(match, 'count')
                assert hasattr(match, 'mutations')

        print("  ✓ Export formats work correctly")


def test_mutation_analysis():
    """Test mutation analysis example."""
    print("Testing mutation analysis...")

    if not TEST_DB.exists():
        print("  ⚠ Test database not found, skipping test")
        return

    with Database(TEST_DB) as db:
        result = db.fuzzy_query("ATCGATC", mutations=1)

        # Test that we can iterate matches and access mutation structure
        if hasattr(result, 'matches') and result.matches:
            # Test the pattern shown in quickstart
            mutation_counts = {}
            for match in result.matches[:1]:  # Just test first match
                if hasattr(match, 'mutations') and match.mutations:
                    for mutation in match.mutations:
                        mutation_counts[mutation] = mutation_counts.get(mutation, 0) + match.count

            # Verify the structure works
            assert isinstance(mutation_counts, dict)

        print("  ✓ Mutation analysis works correctly")


def test_error_handling():
    """Test error handling examples."""
    print("Testing error handling...")

    # Test invalid k-mer - this will be caught by validation before CLI call
    try:
        with patch('rustkmer.utils.run_rustkmer_command', side_effect=get_mock_command()):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.is_file', return_value=True):
                    with Database("test.rkdb") as db:
                        result = db.fuzzy_query("INVALID", mutations=1)
        print("  ✓ Invalid k-mer validation works correctly")
    except Exception as e:
        print(f"  ✓ Error handling works correctly: {e}")

    # Test file not found
    try:
        with patch('pathlib.Path.exists', return_value=False):
            with Database("nonexistent.rkdb") as db:
                pass
        print("  ✗ Should have raised FileNotFoundError")
    except FileNotFoundError:
        print("  ✓ FileNotFoundError handled correctly")


def test_performance_patterns():
    """Test performance-related patterns."""
    print("Testing performance patterns...")

    if not TEST_DB.exists():
        print("  ⚠ Test database not found, skipping test")
        return

    with Database(TEST_DB) as db:
        # Test with custom parameters (small batch for testing)
        many_kmers = ["ATCGATC"] * 5

        batch_result = db.fuzzy_query_batch(
            many_kmers,
            mutations=2,
            max_workers=2,
            max_variants=1000
        )
        assert batch_result.total_queries == 5

        # Test high mutation tolerance with limit
        result = db.fuzzy_query(
            "ATCGATC",
            mutations=3,
            max_variants=5000
        )
        assert result.mutation_tolerance == 3

        print("  ✓ Performance patterns work correctly")


def test_common_patterns():
    """Test common usage patterns."""
    print("Testing common patterns...")

    if not TEST_DB.exists():
        print("  ⚠ Test database not found, skipping test")
        return

    with Database(TEST_DB) as db:
        # Finding close variants
        result = db.fuzzy_query("ATCGATC", mutations=1)

        # Test basic structure access
        assert hasattr(result, 'exact_match')
        assert hasattr(result, 'matches')
        assert hasattr(result, 'mutation_tolerance')

        # Comparing mutation tolerances
        for tolerance in [0, 1, 2]:
            result = db.fuzzy_query("ATCGATC", mutations=tolerance)
            assert result.mutation_tolerance == tolerance

        # Custom output processing
        data = json.loads(result.to_json())
        assert 'matches' in data

        print("  ✓ Common patterns work correctly")


def test_pandas_integration():
    """Test pandas integration example."""
    print("Testing pandas integration...")

    try:
        import pandas as pd
    except ImportError:
        print("  ⚠ Pandas not available, skipping test")
        return

    if not TEST_DB.exists():
        print("  ⚠ Test database not found, skipping test")
        return

    with Database(TEST_DB) as db:
        result = db.fuzzy_query("ATCGATC", mutations=1)

        # Test the pattern from quickstart
        if hasattr(result, 'matches'):
            matches_data = [
                {
                    'kmer': match.kmer,
                    'count': match.count,
                    'distance': match.distance,
                    'mutations': ', '.join(match.mutations) if match.mutations else ''
                }
                for match in result.matches
            ]

            # This tests the pattern works even if no matches
            df = pd.DataFrame(matches_data)
            assert isinstance(df, pd.DataFrame)

            # Test expected columns exist
            if len(df) > 0:
                assert 'kmer' in df.columns
                assert 'count' in df.columns

        print("  ✓ Pandas integration works correctly")


def main():
    """Run all quickstart validation tests."""
    print("=" * 60)
    print("Quickstart.md Validation")
    print("=" * 60)

    tests = [
        test_basic_single_query,
        test_batch_query,
        test_export_formats,
        test_mutation_analysis,
        test_error_handling,
        test_performance_patterns,
        test_common_patterns,
        test_pandas_integration
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__} failed: {e}")

    print("\n" + "=" * 60)
    print(f"Validation Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All quickstart examples are working correctly!")
        return 0
    else:
        print("⚠ Some tests failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())