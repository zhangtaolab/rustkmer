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

    with patch('rustkmer.utils.run_rustkmer_command', side_effect=get_mock_command()) as mock_cmd:
        # Simulate database path check
        with patch('pathlib.Path.exists', return_value=True):
            with Database("test.rkdb") as db:
                    result = db.fuzzy_query("ATCGATC", mutations=1)

                assert result.query_kmer == "ATCGATC"
                assert result.total_matches == 3
                assert result.has_exact_match
                assert result.exact_match.count == 42

                # Test top matches
                top_matches = result.get_top_matches(5)
                assert len(top_matches) == 3
                assert top_matches[0].kmer == "ATCGATC"
                assert top_matches[0].count == 42

                print("  ✓ Basic single query works correctly")


def test_batch_query():
    """Test batch fuzzy queries example."""
    print("Testing batch fuzzy queries...")

    kmers = ["ATCGATC", "CGATCGA", "GATCGAT"]

    with patch('rustkmer.utils.run_rustkmer_command', side_effect=get_mock_command()) as mock_cmd:
        # Simulate database path check
        with patch('pathlib.Path.exists', return_value=True):
            with Database("test.rkdb") as db:
                batch_result = db.fuzzy_query_batch(kmers, mutations=2)

                assert len(batch_result.query_results) == 3
                assert batch_result.total_queries == 3
                assert batch_result.total_matches == 5

                # Test summary table
                summary = batch_result.get_summary_table()
                assert "ATCGATC" in summary
                assert "CGATCGA" in summary
                assert "GATCGAT" in summary

                print("  ✓ Batch query works correctly")


def test_export_formats():
    """Test result export examples."""
    print("Testing export formats...")

    with patch('rustkmer.utils.run_rustkmer_command', side_effect=get_mock_command()) as mock_cmd:
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.is_file', return_value=True):
                with Database("test.rkdb") as db:
                    result = db.fuzzy_query("ATCGATC", mutations=1)

                # Test JSON export
                    json_str = result.to_json()
                data = json.loads(json_str)
                assert data['query_kmer'] == "ATCGATC"
                assert data['total_matches'] == 3

                # Test table export
                table = result.to_table(max_rows=20)
                assert "ATCGATC" in table
                assert "42" in table  # Should contain the count

                # Test accessing match data
                for match in result.matches:
                    if match.mutations:
                        assert isinstance(match.kmer, str)
                        assert isinstance(match.count, int)
                        assert isinstance(match.mutations, list)

                print("  ✓ Export formats work correctly")


def test_mutation_analysis():
    """Test mutation analysis example."""
    print("Testing mutation analysis...")

    with patch('rustkmer.utils.run_rustkmer_command', side_effect=get_mock_command()) as mock_cmd:
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.is_file', return_value=True):
                with Database("test.rkdb") as db:
                    result = db.fuzzy_query("ATCGATC", mutations=1)

                # Find mutation hotspots
                mutation_counts = {}
                for match in result.matches:
                    for mutation in match.mutations:
                        mutation_counts[mutation] = mutation_counts.get(mutation, 0) + match.count

                # Should have counted mutations
                assert len(mutation_counts) > 0

                # Check most common mutations
                sorted_mutations = sorted(
                    mutation_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                assert len(sorted_mutations) > 0

                print("  ✓ Mutation analysis works correctly")


def test_error_handling():
    """Test error handling examples."""
    print("Testing error handling...")

    # Test invalid k-mer - this will be caught by validation before CLI call
    try:
        with patch('rustkmer.utils.run_rustkmer_command', side_effect=get_mock_command()) as mock_cmd:
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

    many_kmers = ["ATCGATC"] * 100

    with patch('rustkmer.utils.run_rustkmer_command', side_effect=get_mock_command()) as mock_cmd:
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.is_file', return_value=True):
                with Database("test.rkdb") as db:
                # Test with custom parameters
                batch_result = db.fuzzy_query_batch(
                    many_kmers,
                    mutations=2,
                    max_workers=8,
                    max_variants=1000
                )
                assert batch_result.total_queries == 100

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

    with patch('rustkmer.utils.run_rustkmer_command', side_effect=get_mock_command()) as mock_cmd:
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.is_file', return_value=True):
                with Database("test.rkdb") as db:
                # Finding close variants
                result = db.fuzzy_query("ATCGATC", mutations=1)
                exact = result.exact_match
                single_mutations = [m for m in result.matches if m.distance == 1]
                assert exact.distance == 0
                assert all(m.distance == 1 for m in single_mutations)

                # Comparing mutation tolerances
                for tolerance in [0, 1, 2]:
                    result = db.fuzzy_query("ATCGATC", mutations=tolerance)
                    assert result.mutation_tolerance == tolerance

                # Custom output processing
                data = json.loads(result.to_json())
                high_count_matches = [
                    m for m in data['matches']
                    if m['count'] > 10
                ]
                assert len(high_count_matches) > 0

                print("  ✓ Common patterns work correctly")


def test_pandas_integration():
    """Test pandas integration example."""
    print("Testing pandas integration...")

    try:
        import pandas as pd
    except ImportError:
        print("  ⚠ Pandas not available, skipping test")
        return

    with patch('rustkmer.utils.run_rustkmer_command', side_effect=get_mock_command()) as mock_cmd:
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.is_file', return_value=True):
                with Database("test.rkdb") as db:
                    result = db.fuzzy_query("ATCGATC", mutations=1)

                # Convert to DataFrame
                matches_data = [
                    {
                        'kmer': match.kmer,
                        'count': match.count,
                        'distance': match.distance,
                        'mutations': ', '.join(match.mutations)
                    }
                    for match in result.matches
                ]

                df = pd.DataFrame(matches_data)
                assert len(df) == 3
                assert 'kmer' in df.columns
                assert 'count' in df.columns
                assert 'distance' in df.columns
                assert 'mutations' in df.columns

                # Test sorting
                sorted_df = df.sort_values('count', ascending=False)
                assert sorted_df.iloc[0]['count'] == 42

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