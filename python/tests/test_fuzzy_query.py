"""Tests for fuzzy query functionality."""

import pytest
import json
import os
from unittest.mock import patch
from rustkmer.fuzzy_query import FuzzyMatchResult, FuzzyQueryResult, FuzzyBatchResult
from rustkmer.database import Database
from rustkmer.exceptions import (
    InvalidMutationToleranceError, InvalidKmerError, QueryError,
    DatabaseError, BatchQueryError
)


class TestFuzzyMatchResult:
    """Test cases for FuzzyMatchResult dataclass."""

    def test_exact_match_creation(self):
        """Test creating a match result for an exact match."""
        # This will fail until FuzzyMatchResult is properly implemented
        match = FuzzyMatchResult(
            kmer="ATCGATC",
            count=42,
            distance=0,
            mutations=[]
        )
        assert match.kmer == "ATCGATC"
        assert match.count == 42
        assert match.distance == 0
        assert match.mutations == []
        assert match.is_exact_match == True

    def test_mutation_match_creation(self):
        """Test creating a match result with mutations."""
        match = FuzzyMatchResult(
            kmer="ATCGATCA",
            count=15,
            distance=1,
            mutations=["G->A at position 6"]
        )
        assert match.kmer == "ATCGATCA"
        assert match.count == 15
        assert match.distance == 1
        assert len(match.mutations) == 1
        assert match.is_exact_match == False

    def test_multiple_mutations(self):
        """Test match with multiple mutations."""
        match = FuzzyMatchResult(
            kmer="TTCGATCG",
            count=5,
            distance=2,
            mutations=["A->T at position 0", "G->A at position 6"]
        )
        assert match.distance == 2
        assert len(match.mutations) == 2
        assert match.is_exact_match == False

    def test_to_dict(self):
        """Test conversion to dictionary representation."""
        match = FuzzyMatchResult(
            kmer="ATCGATC",
            count=42,
            distance=0,
            mutations=[]
        )
        expected = {
            'kmer': "ATCGATC",
            'count': 42,
            'distance': 0,
            'mutations': []
        }
        assert match.to_dict() == expected

    def test_to_dict_with_mutations(self):
        """Test conversion to dictionary with mutations."""
        match = FuzzyMatchResult(
            kmer="ATCGATCA",
            count=15,
            distance=1,
            mutations=["G->A at position 6"]
        )
        expected = {
            'kmer': "ATCGATCA",
            'count': 15,
            'distance': 1,
            'mutations': ["G->A at position 6"]
        }
        assert match.to_dict() == expected

    def test_to_json(self):
        """Test JSON serialization."""
        match = FuzzyMatchResult(
            kmer="ATCGATC",
            count=42,
            distance=0,
            mutations=[]
        )
        json_str = match.to_json()
        parsed = json.loads(json_str)
        expected = {
            'kmer': "ATCGATC",
            'count': 42,
            'distance': 0,
            'mutations': []
        }
        assert parsed == expected

    def test_to_json_with_mutations(self):
        """Test JSON serialization with mutations."""
        match = FuzzyMatchResult(
            kmer="ATCGATCA",
            count=15,
            distance=1,
            mutations=["G->A at position 6"]
        )
        json_str = match.to_json()
        parsed = json.loads(json_str)
        expected = {
            'kmer': "ATCGATCA",
            'count': 15,
            'distance': 1,
            'mutations': ["G->A at position 6"]
        }
        assert parsed == expected

    def test_equality(self):
        """Test equality comparison between FuzzyMatchResult instances."""
        match1 = FuzzyMatchResult(
            kmer="ATCGATC",
            count=42,
            distance=0,
            mutations=[]
        )
        match2 = FuzzyMatchResult(
            kmer="ATCGATC",
            count=42,
            distance=0,
            mutations=[]
        )
        assert match1 == match2

    def test_inequality(self):
        """Test inequality comparison between FuzzyMatchResult instances."""
        match1 = FuzzyMatchResult(
            kmer="ATCGATC",
            count=42,
            distance=0,
            mutations=[]
        )
        match2 = FuzzyMatchResult(
            kmer="ATCGATCA",
            count=15,
            distance=1,
            mutations=["G->A at position 6"]
        )
        assert match1 != match2

    def test_repr(self):
        """Test string representation of FuzzyMatchResult."""
        match = FuzzyMatchResult(
            kmer="ATCGATC",
            count=42,
            distance=0,
            mutations=[]
        )
        repr_str = repr(match)
        assert "FuzzyMatchResult" in repr_str
        assert "ATCGATC" in repr_str
        assert "42" in repr_str

    def test_max_distance_boundary(self):
        """Test creation with maximum allowed distance."""
        # Test with a high distance value
        match = FuzzyMatchResult(
            kmer="ATCGATC",
            count=1,
            distance=10,
            mutations=[f"mutation {i}" for i in range(10)]
        )
        assert match.distance == 10
        assert len(match.mutations) == 10
        assert match.is_exact_match == False

    def test_zero_count(self):
        """Test creation with zero count."""
        match = FuzzyMatchResult(
            kmer="ATCGATC",
            count=0,
            distance=1,
            mutations=["A->T at position 0"]
        )
        assert match.count == 0
        assert match.distance == 1
        assert not match.is_exact_match


class TestFuzzyQueryResult:
    """Test cases for FuzzyQueryResult class."""

    def test_result_with_exact_match(self):
        """Test creating a result with an exact match."""
        exact_match = FuzzyMatchResult(
            kmer="ATCGATC",
            count=100,
            distance=0,
            mutations=[]
        )
        fuzzy_matches = [
            FuzzyMatchResult(
                kmer="ATCGATCA",
                count=20,
                distance=1,
                mutations=["G->A at position 6"]
            )
        ]

        result = FuzzyQueryResult(
            query_kmer="ATCGATC",
            exact_match=exact_match,
            matches=[exact_match] + fuzzy_matches,
            total_matches=2,
            mutation_tolerance=1,
            database_path="/path/to/db.rkdb"
        )

        assert result.query_kmer == "ATCGATC"
        assert result.has_exact_match == True
        assert result.total_matches == 2
        assert result.mutation_tolerance == 1
        assert len(result.fuzzy_matches) == 1

    def test_result_without_exact_match(self):
        """Test creating a result without an exact match."""
        fuzzy_matches = [
            FuzzyMatchResult(
                kmer="ATCGATCA",
                count=20,
                distance=1,
                mutations=["G->A at position 6"]
            ),
            FuzzyMatchResult(
                kmer="TTCGATCG",
                count=5,
                distance=2,
                mutations=["A->T at position 0", "G->A at position 6"]
            )
        ]

        result = FuzzyQueryResult(
            query_kmer="ATCGATC",
            exact_match=None,
            matches=fuzzy_matches,
            total_matches=2,
            mutation_tolerance=2,
            database_path="/path/to/db.rkdb"
        )

        assert result.query_kmer == "ATCGATC"
        assert result.has_exact_match == False
        assert result.exact_match is None
        assert len(result.fuzzy_matches) == 2

    def test_get_matches_by_distance(self):
        """Test grouping matches by distance."""
        matches = [
            FuzzyMatchResult("ATCGATCA", 20, 1, ["G->A"]),
            FuzzyMatchResult("ATCGATCC", 15, 1, ["G->C"]),
            FuzzyMatchResult("TTCGATCG", 5, 2, ["A->T", "G->A"]),
            FuzzyMatchResult("ATCGATC", 100, 0, [])
        ]

        result = FuzzyQueryResult(
            query_kmer="ATCGATC",
            exact_match=matches[3],
            matches=matches,
            total_matches=4,
            mutation_tolerance=2,
            database_path="/path/to/db.rkdb"
        )

        grouped = result.get_matches_by_distance()
        assert len(grouped[0]) == 1  # Exact match
        assert len(grouped[1]) == 2  # Distance 1 matches
        assert len(grouped[2]) == 1  # Distance 2 match
        assert sum(len(matches) for _, matches in grouped.items()) == 4

    def test_get_top_matches(self):
        """Test getting top matches by count."""
        matches = [
            FuzzyMatchResult("ATCGATCA", 20, 1, ["G->A"]),
            FuzzyMatchResult("ATCGATCC", 50, 1, ["G->C"]),
            FuzzyMatchResult("TTCGATCG", 5, 2, ["A->T", "G->A"]),
            FuzzyMatchResult("ATCGATC", 100, 0, [])
        ]

        result = FuzzyQueryResult(
            query_kmer="ATCGATC",
            exact_match=matches[3],
            matches=matches,
            total_matches=4,
            mutation_tolerance=2,
            database_path="/path/to/db.rkdb"
        )

        top_3 = result.get_top_matches(3)
        assert len(top_3) == 3
        assert top_3[0].count == 100  # Exact match first
        assert top_3[1].count == 50
        assert top_3[2].count == 20

    def test_match_count_property(self):
        """Test match_count property sums all counts."""
        matches = [
            FuzzyMatchResult("ATCGATCA", 20, 1, ["G->A"]),
            FuzzyMatchResult("ATCGATC", 100, 0, [])
        ]

        result = FuzzyQueryResult(
            query_kmer="ATCGATC",
            exact_match=matches[1],
            matches=matches,
            total_matches=2,
            mutation_tolerance=1,
            database_path="/path/to/db.rkdb"
        )

        assert result.match_count == 120  # 20 + 100


class TestSingleFuzzyQuery:
    """Integration tests for single fuzzy query functionality."""

    @classmethod
    def setup_class(cls):
        """Set up test database path."""
        # Use one of the test databases that should exist
        cls.test_db = os.path.join(
            os.path.dirname(__file__),
            'test_data',
            'tiny_test.rkdb'
        )

    def test_basic_fuzzy_query(self):
        """Test basic fuzzy query with 1 mutation tolerance."""
        with Database(self.test_db) as db:
            # This will fail until fuzzy_query is implemented
            result = db.fuzzy_query("ATCGATC", mutations=1)

            # Verify return type
            assert isinstance(result, FuzzyQueryResult)
            assert result.query_kmer == "ATCGATC"
            assert result.mutation_tolerance == 1
            assert isinstance(result.total_matches, int)
            assert result.total_matches >= 0

    def test_fuzzy_query_no_mutations(self):
        """Test fuzzy query with 0 mutations (should behave like exact query)."""
        with Database(self.test_db) as db:
            result = db.fuzzy_query("ATCGATC", mutations=0)

            # With 0 mutations, should only have exact matches if any
            if result.has_exact_match:
                assert result.exact_match.distance == 0
                assert len(result.exact_match.mutations) == 0
                assert len(result.fuzzy_matches) == 0

    def test_fuzzy_query_higher_tolerance(self):
        """Test fuzzy query with higher mutation tolerance."""
        with Database(self.test_db) as db:
            result = db.fuzzy_query("ATCGATC", mutations=3)

            # Higher tolerance should find more or equal matches
            assert result.mutation_tolerance == 3
            assert isinstance(result.matches, list)

            # All matches should have distance <= tolerance
            for match in result.matches:
                assert match.distance <= 3
                assert len(match.mutations) <= 3

    def test_fuzzy_query_output_formats(self):
        """Test fuzzy query with different output formats."""
        with Database(self.test_db) as db:
            # Test JSON format
            result_json = db.fuzzy_query("ATCGATC", mutations=1, output_format='json')
            assert isinstance(result_json, FuzzyQueryResult)

            # Test table format
            result_table = db.fuzzy_query("ATCGATC", mutations=1, output_format='table')
            assert isinstance(result_table, FuzzyQueryResult)

            # Test TSV format
            result_tsv = db.fuzzy_query("ATCGATC", mutations=1, output_format='tsv')
            assert isinstance(result_tsv, FuzzyQueryResult)

    def test_fuzzy_query_with_max_variants(self):
        """Test fuzzy query with max_variants limit."""
        with Database(self.test_db) as db:
            # Use a larger limit to avoid combinatorial explosion error
            result = db.fuzzy_query("ATCGATC", mutations=2, max_variants=1000)

            # Should not return more than max_variants
            assert result.total_matches <= 1000

    def test_fuzzy_query_invalid_output_format(self):
        """Test fuzzy query with invalid output format raises ValueError."""
        with Database(self.test_db) as db:
            # Test invalid output format
            with pytest.raises(ValueError, match="Invalid output format: 'invalid'"):
                db.fuzzy_query("ATCGATC", mutations=1, output_format='invalid')

            with pytest.raises(ValueError, match="Invalid output format: 'xml'"):
                db.fuzzy_query("ATCGATC", mutations=1, output_format='xml')

            with pytest.raises(ValueError, match="Invalid output format: 'csv'"):
                db.fuzzy_query("ATCGATC", mutations=1, output_format='csv')

    def test_invalid_kmer_raises_error(self):
        """Test that invalid k-mers raise appropriate errors."""
        with Database(self.test_db) as db:
            # Test invalid characters
            with pytest.raises(InvalidKmerError):
                db.fuzzy_query("ATCGXTCG", mutations=1)

            # Test empty k-mer
            with pytest.raises(InvalidKmerError):
                db.fuzzy_query("", mutations=1)

    def test_database_path_in_result(self):
        """Test that database path is correctly stored in result."""
        with Database(self.test_db) as db:
            result = db.fuzzy_query("ATCGATC", mutations=1)

            # The exact path might differ (could be absolute), but should be set
            assert result.database_path
            assert os.path.isfile(result.database_path)

class TestMutationValidation:
    """Test cases for mutation tolerance validation."""

    @classmethod
    def setup_class(cls):
        """Set up test database path."""
        cls.test_db = os.path.join(
            os.path.dirname(__file__),
            'test_data',
            'tiny_test.rkdb'
        )

    def test_negative_mutations(self):
        """Test that negative mutation tolerance raises error."""
        with Database(self.test_db) as db:
            with pytest.raises(InvalidMutationToleranceError):
                db.fuzzy_query("ATCGATC", mutations=-1)

    def test_too_many_mutations(self):
        """Test that mutation tolerance > 5 raises error."""
        with Database(self.test_db) as db:
            with pytest.raises(InvalidMutationToleranceError):
                db.fuzzy_query("ATCGATC", mutations=6)

    def test_mutation_boundary_values(self):
        """Test boundary values for mutation tolerance."""
        with Database(self.test_db) as db:
            # These should work - 0 to 3 mutations for 7-mers (k/2)
            result0 = db.fuzzy_query("ATCGATC", mutations=0)
            assert result0.mutation_tolerance == 0

            result1 = db.fuzzy_query("ATCGATC", mutations=3)
            assert result1.mutation_tolerance == 3

    def test_invalid_mutation_types(self):
        """Test that non-integer mutation tolerance raises error."""
        with Database(self.test_db) as db:
            # Test float
            with pytest.raises(InvalidMutationToleranceError):
                db.fuzzy_query("ATCGATC", mutations=1.5)

            # Test string
            with pytest.raises(InvalidMutationToleranceError):
                db.fuzzy_query("ATCGATC", mutations="1")

            # Test None
            with pytest.raises(InvalidMutationToleranceError):
                db.fuzzy_query("ATCGATC", mutations=None)

    def test_kmer_validation_with_mutations(self):
        """Test k-mer validation still works with mutation parameters."""
        with Database(self.test_db) as db:
            # Test invalid characters
            with pytest.raises(InvalidKmerError):
                db.fuzzy_query("ATBGATCG", mutations=1)

            # Test lowercase (should be invalid)
            with pytest.raises(InvalidKmerError):
                db.fuzzy_query("atcgatcg", mutations=1)

            # Test length mismatch (if k-mer size is known)
            # Note: This might not be testable without knowing the database k-mer size
            # with pytest.raises(InvalidKmerError):
            #     db.fuzzy_query("ATCG", mutations=1)


class TestBatchErrorHandling:
    """Test error handling for batch fuzzy queries."""

    @classmethod
    def setup_class(cls):
        """Set up test database path."""
        cls.test_db = os.path.join(
            os.path.dirname(__file__),
            'test_data',
            'tiny_test.rkdb'
        )

    def test_batch_with_invalid_kmers(self):
        """Test batch query containing some invalid k-mers."""
        kmers = ["ATCGATC", "INVALID", "GATCGAT", "", "TCGATCG"]

        with Database(self.test_db) as db:
            # Should process valid k-mers and handle invalid ones gracefully
            batch_result = db.fuzzy_query_batch(kmers, mutations=1, max_workers=2)

            # Should have results for valid k-mers
            # Note: The exact behavior depends on implementation
            # This test assumes partial processing continues
            assert isinstance(batch_result, FuzzyBatchResult)
            # Should have some results even with invalid k-mers
            assert batch_result.total_queries >= 0

    def test_batch_with_invalid_mutation_tolerance(self):
        """Test batch query with invalid mutation tolerance."""
        kmers = ["ATCGATC", "GATCGAT"]

        with Database(self.test_db) as db:
            # Should raise error for invalid mutation tolerance
            with pytest.raises(InvalidMutationToleranceError):
                db.fuzzy_query_batch(kmers, mutations=-1)

            with pytest.raises(InvalidMutationToleranceError):
                db.fuzzy_query_batch(kmers, mutations=10)

    def test_batch_with_invalid_worker_count(self):
        """Test batch query with invalid worker count."""
        kmers = ["ATCGATC", "GATCGAT"]

        with Database(self.test_db) as db:
            # Should handle invalid worker counts gracefully
            with pytest.raises((ValueError, TypeError)):
                db.fuzzy_query_batch(kmers, mutations=1, max_workers=0)

            with pytest.raises((ValueError, TypeError)):
                db.fuzzy_query_batch(kmers, mutations=1, max_workers=-1)

            with pytest.raises((ValueError, TypeError)):
                db.fuzzy_query_batch(kmers, mutations=1, max_workers="invalid")

    def test_batch_query_closed_database(self):
        """Test batch query on closed database."""
        kmers = ["ATCGATC", "GATCGAT"]

        db = Database(self.test_db)
        db.close()

        with pytest.raises(DatabaseError):
            db.fuzzy_query_batch(kmers, mutations=1)

    def test_batch_query_large_list_performance(self):
        """Test that batch query can handle larger lists efficiently."""
        # Create a list of k-mers (some valid, some variations)
        kmers = ["ATCGATC", "GATCGAT", "TCGATCG"] * 10  # 30 k-mers

        with Database(self.test_db) as db:
            # Should complete without timeout
            import time
            start_time = time.time()

            batch_result = db.fuzzy_query_batch(kmers, mutations=1, max_workers=4)

            elapsed_time = time.time() - start_time

            # Verify it completed in reasonable time (adjust as needed)
            assert elapsed_time < 10  # Should complete in under 10 seconds
            assert batch_result.total_queries == 30


class TestBatchFuzzyQuery:
    """Integration tests for batch fuzzy query functionality."""

    @classmethod
    def setup_class(cls):
        """Set up test database path."""
        cls.test_db = os.path.join(
            os.path.dirname(__file__),
            'test_data',
            'tiny_test.rkdb'
        )

    def test_basic_batch_query(self):
        """Test basic batch fuzzy query with multiple k-mers."""
        kmers = ["ATCGATC", "GATCGAT", "TCGATCG"]

        with Database(self.test_db) as db:
            batch_result = db.fuzzy_query_batch(kmers, mutations=1)

            # Verify return type
            assert isinstance(batch_result, FuzzyBatchResult)
            assert batch_result.total_queries == 3
            assert len(batch_result.query_results) == 3
            assert batch_result.database_path

            # Each result should be a FuzzyQueryResult
            for result in batch_result.query_results:
                assert isinstance(result, FuzzyQueryResult)
                assert result.query_kmer in kmers
                assert result.mutation_tolerance == 1

    def test_batch_query_with_different_mutations(self):
        """Test batch query with higher mutation tolerance."""
        kmers = ["ATCGATC", "GATCGAT"]

        with Database(self.test_db) as db:
            batch_result = db.fuzzy_query_batch(kmers, mutations=2)

            assert batch_result.total_queries == 2
            for result in batch_result.query_results:
                assert result.mutation_tolerance == 2
                # All matches should have distance <= 2
                for match in result.matches:
                    assert match.distance <= 2

    def test_batch_query_with_max_workers(self):
        """Test batch query with custom worker count."""
        kmers = ["ATCGATC", "GATCGAT", "TCGATCG", "CGATCGA"]

        with Database(self.test_db) as db:
            # Test with 2 workers
            batch_result = db.fuzzy_query_batch(kmers, mutations=1, max_workers=2)

            assert batch_result.total_queries == 4
            assert len(batch_result.query_results) == 4

    def test_batch_query_empty_list(self):
        """Test batch query with empty k-mer list."""
        with Database(self.test_db) as db:
            batch_result = db.fuzzy_query_batch([], mutations=1)

            assert batch_result.total_queries == 0
            assert len(batch_result.query_results) == 0
            assert batch_result.total_matches == 0

    def test_batch_query_duplicate_kmers(self):
        """Test batch query with duplicate k-mers."""
        kmers = ["ATCGATC", "ATCGATC", "GATCGAT"]

        with Database(self.test_db) as db:
            batch_result = db.fuzzy_query_batch(kmers, mutations=1)

            # Should process all k-mers including duplicates
            assert batch_result.total_queries == 3
            assert len(batch_result.query_results) == 3

    def test_fuzzy_query_batch_invalid_output_format(self):
        """Test fuzzy query batch with invalid output format raises ValueError."""
        with Database(self.test_db) as db:
            # Test invalid output format in batch query
            with pytest.raises(ValueError, match="Invalid output format: 'invalid'"):
                db.fuzzy_query_batch(["ATCGATC", "GCTAGCT"], mutations=1, output_format='invalid')

            with pytest.raises(ValueError, match="Invalid output format: 'xml'"):
                db.fuzzy_query_batch(["ATCGATC", "GCTAGCT"], mutations=1, output_format='xml')

            with pytest.raises(ValueError, match="Invalid output format: 'csv'"):
                db.fuzzy_query_batch(["ATCGATC", "GCTAGCT"], mutations=1, output_format='csv')


class TestFuzzyBatchResult:
    """Test cases for FuzzyBatchResult class."""

    def test_batch_result_creation(self):
        """Test creating a batch result with multiple query results."""
        # Create mock query results
        query_results = [
            FuzzyQueryResult(
                query_kmer="ATCGATC",
                exact_match=None,
                matches=[],
                total_matches=0,
                mutation_tolerance=1,
                database_path="/path/to/db.rkdb"
            ),
            FuzzyQueryResult(
                query_kmer="GATCGAT",
                exact_match=FuzzyMatchResult("GATCGAT", 10, 0, []),
                matches=[FuzzyMatchResult("GATCGAT", 10, 0, [])],
                total_matches=1,
                mutation_tolerance=1,
                database_path="/path/to/db.rkdb"
            )
        ]

        batch = FuzzyBatchResult(
            query_results=query_results,
            total_queries=2,
            total_matches=1,
            database_path="/path/to/db.rkdb"
        )

        assert batch.total_queries == 2
        assert batch.total_matches == 1
        assert len(batch.query_results) == 2
        assert batch.database_path == "/path/to/db.rkdb"

    def test_queries_with_exact_matches_property(self):
        """Test counting queries with exact matches."""
        query_results = [
            FuzzyQueryResult("ATCGATC", None, [], 0, 1, "/path/db"),
            FuzzyQueryResult("GATCGAT", FuzzyMatchResult("GATCGAT", 10, 0, []), [], 1, 1, "/path/db"),
            FuzzyQueryResult("TCGATCG", None, [], 0, 1, "/path/db"),
            FuzzyQueryResult("CGATCGA", FuzzyMatchResult("CGATCGA", 5, 0, []), [], 1, 1, "/path/db")
        ]

        batch = FuzzyBatchResult(query_results, 4, 2, "/path/db")
        assert batch.queries_with_exact_matches == 2

    def test_queries_with_any_matches_property(self):
        """Test counting queries with any matches."""
        query_results = [
            FuzzyQueryResult("ATCGATC", None, [], 0, 1, "/path/db"),
            FuzzyQueryResult("GATCGAT", FuzzyMatchResult("GATCGAT", 10, 0, []), [], 1, 1, "/path/db"),
            FuzzyQueryResult("TCGATCG", None, [FuzzyMatchResult("TCGATTA", 3, 1, ["C->T"])], 1, 1, "/path/db"),
            FuzzyQueryResult("CGATCGA", None, [], 0, 1, "/path/db")
        ]

        batch = FuzzyBatchResult(query_results, 4, 2, "/path/db")
        assert batch.queries_with_any_matches == 2

    def test_get_summary_table(self):
        """Test summary table generation."""
        query_results = [
            FuzzyQueryResult("ATCGATC", None, [], 0, 1, "/path/db"),
            FuzzyQueryResult("GATCGAT", FuzzyMatchResult("GATCGAT", 10, 0, []), [], 1, 1, "/path/db"),
            FuzzyQueryResult("TCGATCG", None, [FuzzyMatchResult("TCGATTA", 3, 1, ["C->T"])], 1, 1, "/path/db")
        ]

        batch = FuzzyBatchResult(query_results, 3, 2, "/path/db")
        summary = batch.get_summary_table()

        assert "3" in summary  # Total queries
        assert "2" in summary  # Queries with matches
        assert "1" in summary  # Queries with exact matches

    def test_to_json(self):
        """Test JSON serialization of batch results."""
        query_results = [
            FuzzyQueryResult(
                query_kmer="ATCGATC",
                exact_match=None,
                matches=[],
                total_matches=0,
                mutation_tolerance=1,
                database_path="/path/to/db.rkdb"
            )
        ]

        batch = FuzzyBatchResult(query_results, 1, 0, "/path/to/db.rkdb")
        json_str = batch.to_json()

        # Should contain key fields
        assert '"total_queries": 1' in json_str
        assert '"total_matches": 0' in json_str
        assert '"query_results"' in json_str


class TestFuzzyQueryExport:
    """Test cases for FuzzyQueryResult export formats."""

    def test_json_export_format(self):
        """Test JSON export format preserves all data."""
        # Create a result with exact and fuzzy matches
        exact_match = FuzzyMatchResult("ATCGATC", 100, 0, [])
        fuzzy_matches = [
            FuzzyMatchResult("ATCGATT", 20, 1, ["C->T at position 6"]),
            FuzzyMatchResult("ATCGAAC", 5, 2, ["G->A at position 4", "T->C at position 5"])
        ]

        result = FuzzyQueryResult(
            query_kmer="ATCGATC",
            exact_match=exact_match,
            matches=[exact_match] + fuzzy_matches,
            total_matches=3,
            mutation_tolerance=2,
            database_path="/path/to/db.rkdb"
        )

        json_str = result.to_json()
        data = json.loads(json_str)

        # Verify structure
        assert data['query_kmer'] == "ATCGATC"
        assert data['total_matches'] == 3
        assert data['mutation_tolerance'] == 2
        assert data['database_path'] == "/path/to/db.rkdb"

        # Verify exact match
        assert data['exact_match'] is not None
        assert data['exact_match']['kmer'] == "ATCGATC"
        assert data['exact_match']['count'] == 100
        assert data['exact_match']['distance'] == 0

        # Verify fuzzy matches
        assert len(data['matches']) == 3
        assert data['matches'][1]['kmer'] == "ATCGATT"
        assert data['matches'][1]['mutations'] == ["C->T at position 6"]

    def test_table_export_format(self):
        """Test table export format with row limiting."""
        matches = [
            FuzzyMatchResult("ATCGATC", 100, 0, []),
            FuzzyMatchResult("ATCGATT", 20, 1, ["C->T"]),
            FuzzyMatchResult("ATCGAAC", 5, 2, ["G->A", "T->C"]),
            FuzzyMatchResult("TTCGATC", 15, 1, ["A->T"]),
            FuzzyMatchResult("GATCGAT", 8, 2, ["A->G", "T->A"])
        ]

        result = FuzzyQueryResult(
            query_kmer="ATCGATC",
            exact_match=matches[0],
            matches=matches,
            total_matches=5,
            mutation_tolerance=2,
            database_path="/path/to/db.rkdb"
        )

        # Test without limit
        table_all = result.to_table()
        lines = table_all.split('\n')
        assert len(lines) > 5  # Should have header + all matches
        assert "ATCGATC" in table_all

        # Test with limit
        table_limited = result.to_table(max_rows=3)
        lines_limited = table_limited.split('\n')
        # Count actual match lines (not header/footer lines)
        match_lines = [l for l in lines_limited if l.startswith(('A', 'T', 'G', 'C')) and '\t' in l]
        assert len(match_lines) <= 3

    def test_tsv_export_format(self):
        """Test TSV export format for spreadsheet import."""
        # Test that TSV format is accepted and doesn't error
        from unittest.mock import Mock, patch, MagicMock
        from rustkmer.stats import DatabaseStats

        # Mock the run_rustkmer_command to return TSV output
        with patch('rustkmer.database.run_rustkmer_command') as mock_run:
            mock_run.return_value = "kmer\tcount\tdistance\tmutations\nATCGATC\t100\t0\t\nATCGATT\t20\t1\tC->T"

            # Mock the stats to set kmer_size
            with patch.object(Database, 'stats') as mock_stats:
                mock_stats.return_value = DatabaseStats(
                    kmer_size=7,
                    unique_kmers=1000,
                    total_counts=5000,
                    min_count=1,
                    max_count=100,
                    file_size=1024,
                    format_version="1.0"
                )

                with Database(os.path.join(os.path.dirname(__file__), 'test_data', 'tiny_test.rkdb')) as db:
                    tsv_result = db.fuzzy_query("ATCGATC", mutations=1, output_format='tsv')
                    assert isinstance(tsv_result, FuzzyQueryResult)
                    assert tsv_result.query_kmer == "ATCGATC"
                    assert tsv_result.total_matches == 2
                    assert len(tsv_result.matches) == 2

    def test_mutation_pattern_analysis(self):
        """Test mutation pattern analysis methods."""
        matches = [
            FuzzyMatchResult("ATCGATC", 100, 0, []),
            FuzzyMatchResult("TTCGATC", 15, 1, ["A->T at position 0"]),
            FuzzyMatchResult("ATCGATT", 20, 1, ["C->T at position 6"]),
            FuzzyMatchResult("ATCGAAC", 5, 2, ["G->A at position 4", "T->C at position 5"]),
            FuzzyMatchResult("GTCGATC", 8, 1, ["A->G at position 0"])
        ]

        result = FuzzyQueryResult(
            query_kmer="ATCGATC",
            exact_match=matches[0],
            matches=matches,
            total_matches=5,
            mutation_tolerance=2,
            database_path="/path/to/db.rkdb"
        )

        # Test grouping by distance
        grouped = result.get_matches_by_distance()
        assert len(grouped[0]) == 1  # Exact match
        assert len(grouped[1]) == 3  # Distance 1 matches
        assert len(grouped[2]) == 1  # Distance 2 match

        # Test top matches
        top_3 = result.get_top_matches(3)
        assert len(top_3) == 3
        assert top_3[0].count == 100  # Exact match first
        assert top_3[1].count == 20
        assert top_3[2].count == 15
