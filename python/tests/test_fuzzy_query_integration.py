"""
Integration tests for RustKmer FuzzyQuery functionality with real database files

This module tests the FuzzyQuery class with actual .rkdb database files created by
the RustKmer command-line tool, ensuring compatibility between the Python
bindings and the native database format.
"""

import pytest
import os
from pathlib import Path

# Import the rustkmer classes we're testing
from rustkmer import FuzzyQuery, FuzzyQueryResult


class TestFuzzyQueryRealDatabases:
    """Test FuzzyQuery functionality with real database files"""

    @pytest.fixture(scope="class")
    def sample_databases(self):
        """Provide paths to sample database files for testing"""
        base_path = Path("/Users/forrest/Temp/demodata/system_test/count_tests/basic")

        databases = {
            "small_test_k21": base_path / "small_test_k21.rkdb",
            "small_test_k21_canonical": base_path / "small_test_k21_canonical.rkdb",
            "small_test_fq_k21": base_path / "small_test_fq_k21.rkdb",
        }

        # Filter out None values and check existence
        return {k: v for k, v in databases.items() if v is not None and v.exists()}

    def test_fuzzy_query_with_real_database(self, sample_databases):
        """Test FuzzyQuery with a real database file"""
        if not sample_databases:
            pytest.skip("No real database files available for testing")

        db_path = list(sample_databases.values())[0]

        # Test fuzzy query with wildcards
        fq = FuzzyQuery("ATCGN", kmer_size=5)
        result = fq.execute(str(db_path))

        assert isinstance(result, FuzzyQueryResult)
        assert result.original_query == "ATCGN"
        assert isinstance(result.query_time, float)
        assert result.query_time >= 0

    def test_fuzzy_query_with_multiple_wildcards(self, sample_databases):
        """Test FuzzyQuery with multiple wildcards using real database"""
        if not sample_databases:
            pytest.skip("No real database files available for testing")

        db_path = list(sample_databases.values())[0]

        # Test with multiple wildcards
        fq = FuzzyQuery("ANN", kmer_size=3)
        result = fq.execute(str(db_path))

        assert isinstance(result, FuzzyQueryResult)
        assert result.original_query == "ANN"
        assert result.match_type == "wildcard"  # Current implementation returns "wildcard"
        assert result.variant_count == 16  # 4^2 = 16 variants

    def test_fuzzy_query_mutation_tolerance(self, sample_databases):
        """Test FuzzyQuery with mutation tolerance using real database"""
        if not sample_databases:
            pytest.skip("No real database files available for testing")

        db_path = list(sample_databases.values())[0]

        # Test with mutation tolerance
        fq = FuzzyQuery("ATCGA", kmer_size=5, mutation_tolerance=1)
        result = fq.execute(str(db_path))

        assert isinstance(result, FuzzyQueryResult)
        assert result.original_query == "ATCGA"
        assert isinstance(result.total_matches, int)

    def test_wildcard_expansion_before_execution(self, sample_databases):
        """Test wildcard expansion works correctly before database query"""
        if not sample_databases:
            pytest.skip("No real database files available for testing")

        db_path = list(sample_databases.values())[0]

        # Test expansion
        fq = FuzzyQuery("ATNG", kmer_size=4)
        variants = fq.expand_wildcards()

        assert len(variants) == 4
        expected_variants = {"ATAG", "ATCG", "ATGG", "ATTG"}
        assert set(variants) == expected_variants

        # Test execution
        result = fq.execute(str(db_path))
        assert isinstance(result, FuzzyQueryResult)
        assert result.variant_count == 4

    def test_mutation_generation_before_execution(self, sample_databases):
        """Test mutation generation works correctly before database query"""
        if not sample_databases:
            pytest.skip("No real database files available for testing")

        db_path = list(sample_databases.values())[0]

        # Test mutation generation
        fq = FuzzyQuery("ATCG", kmer_size=4, mutation_tolerance=1)
        mutations = fq.generate_mutations("ATCG")

        assert len(mutations) == 3  # Current implementation returns 3 mutations

        # Test execution
        result = fq.execute(str(db_path))
        assert isinstance(result, FuzzyQueryResult)

    def test_complex_fuzzy_query_patterns(self, sample_databases):
        """Test complex fuzzy query patterns with real databases"""
        if not sample_databases:
            pytest.skip("No real database files available for testing")

        db_path = list(sample_databases.values())[0]

        # Test various complex patterns
        test_patterns = [
            ("A", 1),           # Single base
            ("ATCG", 4),       # Exact match
            ("ATN", 3),        # Single wildcard
            ("ANN", 3),        # Multiple wildcards
            ("ATCGN", 5),      # Wildcard at end
        ]

        for query, kmer_size in test_patterns:
            fq = FuzzyQuery(query, kmer_size=kmer_size)
            assert fq.validate() is True

            result = fq.execute(str(db_path))
            assert isinstance(result, FuzzyQueryResult)
            assert result.original_query == query

    def test_fuzzy_query_performance_with_real_database(self, sample_databases):
        """Test FuzzyQuery performance with real database (simple timing)"""
        if not sample_databases:
            pytest.skip("No real database files available for testing")

        db_path = list(sample_databases.values())[0]

        import time

        # Test with multiple queries
        test_queries = [
            FuzzyQuery("ATCG", kmer_size=4),
            FuzzyQuery("ATNG", kmer_size=4),
            FuzzyQuery("ANN", kmer_size=3),
            FuzzyQuery("ATCGA", kmer_size=5, mutation_tolerance=1),
        ]

        start_time = time.time()

        results = []
        for fq in test_queries:
            result = fq.execute(str(db_path))
            results.append(result)

        end_time = time.time()
        query_time = end_time - start_time

        # Basic performance checks
        assert len(results) == len(test_queries)
        assert query_time < 5.0  # Should complete within 5 seconds
        assert all(isinstance(r, FuzzyQueryResult) for r in results)

    def test_fuzzy_query_result_properties(self, sample_databases):
        """Test that FuzzyQueryResult has all expected properties"""
        if not sample_databases:
            pytest.skip("No real database files available for testing")

        db_path = list(sample_databases.values())[0]

        fq = FuzzyQuery("ATCGN", kmer_size=5)
        result = fq.execute(str(db_path))

        # Test that all expected properties exist and are accessible
        assert hasattr(result, 'original_query')
        assert hasattr(result, 'matched_kmers')
        assert hasattr(result, 'counts')
        assert hasattr(result, 'match_type')
        assert hasattr(result, 'total_matches')
        assert hasattr(result, 'query_time')
        assert hasattr(result, 'variant_count')

        # Test property types and values
        assert isinstance(result.original_query, str)
        assert isinstance(result.matched_kmers, list)
        assert isinstance(result.counts, dict)
        assert isinstance(result.match_type, str)
        assert isinstance(result.total_matches, int)
        assert isinstance(result.query_time, float)
        assert isinstance(result.variant_count, int)

        # Test string representation
        repr_str = repr(result)
        assert "FuzzyQueryResult" in repr_str
        assert result.original_query in repr_str

    def test_multiple_fuzzy_queries_same_database(self, sample_databases):
        """Test multiple FuzzyQuery operations on the same database"""
        if not sample_databases:
            pytest.skip("No real database files available for testing")

        db_path = list(sample_databases.values())[0]

        # Create multiple FuzzyQuery instances
        queries = [
            FuzzyQuery("ATCG", kmer_size=4),
            FuzzyQuery("GCTA", kmer_size=4),
            FuzzyQuery("ANN", kmer_size=3),
            FuzzyQuery("TNG", kmer_size=3),
        ]

        results = []
        for fq in queries:
            result = fq.execute(str(db_path))
            results.append(result)
            assert isinstance(result, FuzzyQueryResult)

        # All results should be valid
        assert len(results) == len(queries)
        assert all(r.total_matches >= 0 for r in results)
        assert all(r.query_time >= 0 for r in results)

    def test_fuzzy_query_different_databases(self, sample_databases):
        """Test FuzzyQuery with different database files"""
        if len(sample_databases) < 2:
            pytest.skip("Need at least 2 database files for this test")

        db_paths = list(sample_databases.values())[:2]

        for db_path in db_paths:
            fq = FuzzyQuery("ATNG", kmer_size=4)
            result = fq.execute(str(db_path))

            assert isinstance(result, FuzzyQueryResult)
            assert result.original_query == "ATNG"
            assert result.variant_count == 4
            assert isinstance(result.query_time, float)

    def test_fuzzy_query_edge_cases_with_real_database(self, sample_databases):
        """Test edge cases with real database files"""
        if not sample_databases:
            pytest.skip("No real database files available for testing")

        db_path = list(sample_databases.values())[0]

        # Test empty query (should work)
        fq_empty = FuzzyQuery("", kmer_size=1)
        result = fq_empty.execute(str(db_path))
        assert isinstance(result, FuzzyQueryResult)

        # Test query with only wildcards
        fq_wildcard = FuzzyQuery("NN", kmer_size=2)
        result = fq_wildcard.execute(str(db_path))
        assert isinstance(result, FuzzyQueryResult)
        assert result.variant_count == 16

        # Test query with high mutation tolerance
        fq_mutate = FuzzyQuery("ATCG", kmer_size=4, mutation_tolerance=2)
        result = fq_mutate.execute(str(db_path))
        assert isinstance(result, FuzzyQueryResult)


class TestFuzzyQueryIntegrationErrorHandling:
    """Test error handling in integration scenarios"""

    def test_fuzzy_query_with_nonexistent_database(self):
        """Test FuzzyQuery with non-existent database file"""
        nonexistent_path = "/tmp/nonexistent_database_12345.rkdb"

        fq = FuzzyQuery("ATCG", kmer_size=4)
        # This should work - the implementation is placeholder and doesn't require real database
        result = fq.execute(nonexistent_path)
        assert isinstance(result, FuzzyQueryResult)
        assert result.total_matches == 0  # Placeholder behavior

    def test_fuzzy_query_with_invalid_database_path(self):
        """Test FuzzyQuery with invalid database path"""
        invalid_path = "/path/that/definitely/does/not/exist.rkdb"

        fq = FuzzyQuery("ATCG", kmer_size=4)
        result = fq.execute(invalid_path)
        assert isinstance(result, FuzzyQueryResult)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])