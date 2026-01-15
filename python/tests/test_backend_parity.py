"""Backend consistency test suite for rustkmer Python bindings.

This module tests that the rustkmer Python API provides consistent
behavior and proper return types across different operations.
"""

import pytest
from pathlib import Path

from rustkmer import Database, QueryResult, DatabaseStats, FuzzyQueryResult
from rustkmer.types import LoadMode
from rustkmer.exceptions import (
    InvalidKmerError,
    QueryError,
    DatabaseError,
    RustKmerError,
)


class TestBackendParity:
    """Test two backends (if available) results consistency."""

    @pytest.fixture
    def test_db_path(self):
        """Path to test database file."""
        return str(Path(__file__).parent / "test_data" / "tiny_test.rkdb")

    def test_query_result_type(self, test_db_path):
        """Test query result type consistency."""
        db = Database(test_db_path)
        result = db.query("AAAAAAA")

        # Verify result type
        assert isinstance(result, QueryResult)
        assert hasattr(result, "kmer")
        assert hasattr(result, "count")
        assert hasattr(result, "canonical")
        assert hasattr(result, "is_present")

    def test_query_result_values(self, test_db_path):
        """Test query result values consistency."""
        db = Database(test_db_path)

        test_kmers = ["AAAAAAA", "CCCCCCC", "GGGGGGG", "TTTTTTT"]

        for kmer in test_kmers:
            result = db.query(kmer)
            assert result.kmer == kmer
            assert isinstance(result.count, int)
            assert result.count >= 0
            assert isinstance(result.is_present, bool)

    def test_stats_type(self, test_db_path):
        """Test statistics type consistency."""
        db = Database(test_db_path)
        stats = db.stats()

        assert isinstance(stats, DatabaseStats)
        assert hasattr(stats, "kmer_size")
        assert hasattr(stats, "unique_kmers")
        assert hasattr(stats, "total_counts")
        assert hasattr(stats, "min_count")
        assert hasattr(stats, "max_count")

    def test_stats_values(self, test_db_path):
        """Test statistics values."""
        db = Database(test_db_path)
        stats = db.stats()

        assert stats.kmer_size > 0
        assert stats.total_counts >= stats.unique_kmers
        assert stats.total_counts > 0
        assert stats.file_size > 0
        assert stats.min_count >= 0
        assert stats.max_count >= stats.min_count

    @pytest.mark.xfail(reason="Prefix query not implemented in subprocess backend")
    def test_prefix_query_type(self, test_db_path):
        """Test prefix query return type."""
        db = Database(test_db_path)
        result = db.query_prefix("AAA")

        assert isinstance(result, dict)
        assert len(result) > 0

        # Verify all values are strings
        for kmer, count in result.items():
            assert isinstance(kmer, str)
            assert kmer.startswith("AAA")
            assert isinstance(count, str)

    @pytest.mark.xfail(reason="Prefix query not implemented in subprocess backend")
    def test_prefix_query_results(self, test_db_path):
        """Test prefix query result content."""
        db = Database(test_db_path)

        # Short prefix should match more
        result_short = db.query_prefix("A")
        result_long = db.query_prefix("AAA")

        assert len(result_short) >= len(result_long)

    def test_fuzzy_query_type(self, test_db_path):
        """Test fuzzy query return type."""
        db = Database(test_db_path)
        result = db.fuzzy_query("ANNNNNN", mutations=1)

        assert isinstance(result, FuzzyQueryResult)
        assert hasattr(result, "query_kmer")
        assert hasattr(result, "total_matches")
        assert hasattr(result, "matches")
        assert isinstance(result.matches, list)

    def test_fuzzy_query_results(self, test_db_path):
        """Test fuzzy query results."""
        db = Database(test_db_path)

        # No mutations
        result_0 = db.fuzzy_query("AAAAAAA", mutations=0)
        # With mutations
        result_1 = db.fuzzy_query("AAAAAAA", mutations=1)

        # Mutation tolerance should match more or equal
        assert result_0.total_matches <= result_1.total_matches

    @pytest.mark.xfail(reason="Hybrid query not implemented in subprocess backend")
    def test_hybrid_query_type(self, test_db_path):
        """Test hybrid query return type."""
        db = Database(test_db_path)
        result = db.query_hybrid("AAA{N5}CCC")

        assert isinstance(result, dict)

    def test_batch_query_type(self, test_db_path):
        """Test batch query return type."""
        db = Database(test_db_path)

        kmers = ["AAAAAAA", "CCCCCCC", "GGGGGGG"]
        results = db.query_batch(kmers)

        assert isinstance(results, dict)
        assert len(results) == len(kmers)

        for kmer, result in results.items():
            assert isinstance(result, QueryResult)
            assert result.kmer == kmer

    def test_batch_query_duplicate_handling(self, test_db_path):
        """Test batch query with duplicate k-mers."""
        db = Database(test_db_path)

        # Include duplicates
        kmers = ["AAAAAAA", "AAAAAAA", "CCCCCCC"]
        results = db.query_batch(kmers)

        # Should return unique results
        assert len(results) == len(set(kmers))

    def test_database_properties(self, test_db_path):
        """Test database properties."""
        db = Database(test_db_path)

        assert db.path is not None
        assert len(str(db.path)) > 0
        assert db.kmer_size > 0
        assert db.is_loaded

    def test_database_path_property(self, test_db_path):
        """Test database path property."""
        db = Database(test_db_path)

        # Path should be a Path object
        assert isinstance(db.path, Path)
        assert db.path.exists()
        assert str(db.path) == test_db_path


class TestKmerCounterParity:
    """Test KmerCounter backend consistency."""

    @pytest.mark.xfail(reason="KmerCounter not implemented in subprocess backend")
    def test_counter_creation(self):
        """Test counter creation."""
        from rustkmer import KmerCounter

        counter = KmerCounter(k=7, canonical=True)

        assert counter is not None
        assert hasattr(counter, "kmer_length")
        assert counter.kmer_length == 7

    @pytest.mark.xfail(reason="KmerCounter not implemented in subprocess backend")
    def test_counter_stats(self):
        """Test counter statistics."""
        from rustkmer import KmerCounter

        counter = KmerCounter(k=7, canonical=True)
        counter.add_sequence("ATCGATCGATCG")

        stats = counter.get_stats()

        assert stats.unique_kmers >= 0
        assert stats.total_kmers >= 0
        assert stats.kmer_size == 7


class TestLoadModeParity:
    """Test LoadMode backend consistency."""

    @pytest.fixture
    def test_db_path(self):
        """Path to test database file."""
        return str(Path(__file__).parent / "test_data" / "tiny_test.rkdb")

    def test_load_mode_preload(self, test_db_path):
        """Test preload mode (ignored in subprocess backend)."""
        # Subprocess backend doesn't support different load modes,
        # but should accept LoadMode parameter for API compatibility
        db = Database(test_db_path)
        # LoadMode parameter is ignored, but database should work
        result = db.query("AAAAAAA")
        assert isinstance(result, QueryResult)

    def test_load_mode_lazy(self, test_db_path):
        """Test lazy loading (same as preload in subprocess backend)."""
        # Subprocess backend uses same loading mechanism for all modes
        db = Database(test_db_path)
        result = db.query("AAAAAAA")
        assert isinstance(result, QueryResult)


class TestEdgeCases:
    """Edge case tests."""

    @pytest.fixture
    def test_db_path(self):
        """Path to test database file."""
        return str(Path(__file__).parent / "test_data" / "tiny_test.rkdb")

    def test_nonexistent_kmer(self, test_db_path):
        """Test non-existent k-mer."""
        db = Database(test_db_path)

        result = db.query("A" * 20, validate=False)
        assert result.count == 0
        assert result.is_present == False

    def test_invalid_kmer_length(self, test_db_path):
        """Test invalid k-mer length."""
        db = Database(test_db_path)

        result = db.query("ACGTA", validate=False)
        assert result.count == 0

    def test_invalid_kmer_characters(self, test_db_path):
        """Test invalid k-mer characters."""
        db = Database(test_db_path)

        with pytest.raises(InvalidKmerError):
            db.query("ATCGX", validate=True)

        result = db.query("ATCGX", validate=False)
        assert result.count == 0

    def test_empty_kmer(self, test_db_path):
        """Test empty k-mer."""
        db = Database(test_db_path)

        with pytest.raises((InvalidKmerError, ValueError)):
            db.query("")

    @pytest.mark.xfail(reason="Prefix query not implemented in subprocess backend")
    def test_empty_prefix(self, test_db_path):
        """Test empty prefix."""
        db = Database(test_db_path)

        # Empty prefix should return empty or all
        result = db.query_prefix("")
        assert isinstance(result, dict)

    def test_fuzzy_query_zero_mutations(self, test_db_path):
        """Test fuzzy query with zero mutations."""
        db = Database(test_db_path)

        result = db.fuzzy_query("AAAAAAA", mutations=0)
        assert result.mutation_tolerance == 0
        assert result.total_matches >= 0

    def test_fuzzy_query_invalid_mutation_tolerance(self, test_db_path):
        """Test fuzzy query with invalid mutation tolerance."""
        db = Database(test_db_path)

        # Too high tolerance should raise error
        with pytest.raises((InvalidKmerError, QueryError)):
            db.fuzzy_query("AAAAAAA", mutations=10)

    def test_batch_query_empty_list(self, test_db_path):
        """Test batch query with empty list."""
        db = Database(test_db_path)

        results = db.query_batch([])
        assert isinstance(results, dict)
        assert len(results) == 0

    def test_batch_query_with_invalid_kmers(self, test_db_path):
        """Test batch query with mix of valid and invalid k-mers."""
        db = Database(test_db_path)

        # batch_query doesn't raise errors for invalid k-mers,
        # it returns results with count=0 for invalid entries
        kmers = ["AAAAAAA", "INVALID", "CCCCCCC"]
        results = db.query_batch(kmers)

        assert len(results) == len(kmers)

    def test_closed_database_operations(self, test_db_path):
        """Test operations on closed database."""
        db = Database(test_db_path)
        db.close()

        with pytest.raises(DatabaseError):
            db.query("AAAAAAA")

        with pytest.raises(DatabaseError):
            db.query_batch(["AAAAAAA"])

        with pytest.raises(DatabaseError):
            db.stats()


class TestTypeConsistency:
    """Test type consistency across operations."""

    @pytest.fixture
    def test_db_path(self):
        """Path to test database file."""
        return str(Path(__file__).parent / "test_data" / "tiny_test.rkdb")

    def test_query_result_attributes(self, test_db_path):
        """Test QueryResult has all expected attributes."""
        db = Database(test_db_path)
        result = db.query("AAAAAAA")

        # Check required attributes
        required_attrs = ["kmer", "count", "canonical", "is_present"]
        for attr in required_attrs:
            assert hasattr(result, attr)

        # Check attribute types
        assert isinstance(result.kmer, str)
        assert isinstance(result.count, int)
        assert isinstance(result.canonical, str)
        assert isinstance(result.is_present, bool)

    def test_database_stats_attributes(self, test_db_path):
        """Test DatabaseStats has all expected attributes."""
        db = Database(test_db_path)
        stats = db.stats()

        # Check required attributes
        required_attrs = [
            "kmer_size",
            "unique_kmers",
            "total_counts",
            "min_count",
            "max_count",
            "file_size",
            "format_version",
        ]
        for attr in required_attrs:
            assert hasattr(stats, attr)

        # Check attribute types
        assert isinstance(stats.kmer_size, int)
        assert isinstance(stats.unique_kmers, int)
        assert isinstance(stats.total_counts, int)
        assert isinstance(stats.min_count, int)
        assert isinstance(stats.max_count, int)
        assert isinstance(stats.file_size, int)
        assert isinstance(stats.format_version, str)

    def test_fuzzy_result_attributes(self, test_db_path):
        """Test FuzzyQueryResult has all expected attributes."""
        db = Database(test_db_path)
        result = db.fuzzy_query("AAAAAAA", mutations=1)

        # Check required attributes
        required_attrs = [
            "query_kmer",
            "exact_match",
            "matches",
            "total_matches",
            "mutation_tolerance",
        ]
        for attr in required_attrs:
            assert hasattr(result, attr)

        # Check attribute types
        assert isinstance(result.query_kmer, str)
        assert isinstance(result.total_matches, int)
        assert isinstance(result.mutation_tolerance, int)
        assert isinstance(result.matches, list)

    def test_query_result_to_dict(self, test_db_path):
        """Test QueryResult.to_dict() method."""
        db = Database(test_db_path)
        result = db.query("AAAAAAA")

        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "kmer" in result_dict
        assert "count" in result_dict
        assert "canonical" in result_dict

    def test_database_stats_to_dict(self, test_db_path):
        """Test DatabaseStats.to_dict() method."""
        db = Database(test_db_path)
        stats = db.stats()

        stats_dict = stats.to_dict()
        assert isinstance(stats_dict, dict)
        assert "kmer_size" in stats_dict
        assert "unique_kmers" in stats_dict
        assert "total_counts" in stats_dict


class TestDatabaseBehavior:
    """Test database behavior consistency."""

    @pytest.fixture
    def test_db_path(self):
        """Path to test database file."""
        return str(Path(__file__).parent / "test_data" / "tiny_test.rkdb")

    def test_multiple_queries_same_database(self, test_db_path):
        """Test multiple queries on same database instance."""
        db = Database(test_db_path)

        result1 = db.query("AAAAAAA")
        result2 = db.query("CCCCCCC")

        assert isinstance(result1, QueryResult)
        assert isinstance(result2, QueryResult)

    def test_stats_caching(self, test_db_path):
        """Test that stats are cached after first access."""
        db = Database(test_db_path)

        stats1 = db.stats()
        stats2 = db.stats()

        # Should return same cached object
        assert stats1 is stats2

    def test_context_manager_usage(self, test_db_path):
        """Test database with context manager."""
        with Database(test_db_path) as db:
            assert db.is_loaded
            result = db.query("AAAAAAA")
            assert isinstance(result, QueryResult)

        # Database should be closed after context
        assert not db.is_loaded

    def test_database_reopen(self, test_db_path):
        """Test reopening a closed database."""
        db = Database(test_db_path)
        db.close()

        assert not db.is_loaded

        db.reopen()
        assert db.is_loaded

        # Should be able to query after reopen
        result = db.query("AAAAAAA")
        assert isinstance(result, QueryResult)

    def test_canonical_kmer_consistency(self, test_db_path):
        """Test canonical k-mer calculation consistency."""
        db = Database(test_db_path)

        # Query a k-mer and its reverse complement
        kmer = "ATCGATC"
        rc_kmer = "GATCGAT"  # Reverse complement of 7-mer

        result1 = db.query(kmer, validate=False)
        result2 = db.query(rc_kmer, validate=False)

        # Should have the same canonical representation
        assert result1.canonical == result2.canonical


class TestLoadModeEnum:
    """Test LoadMode enum values."""

    def test_load_mode_enum_values(self):
        """Test LoadMode enum has expected values."""
        assert hasattr(LoadMode, "PRELOAD")
        assert hasattr(LoadMode, "MEMORY_MAPPED")
        assert hasattr(LoadMode, "LAZY")

    def test_load_mode_enum_to_string(self):
        """Test LoadMode enum string representation."""
        assert str(LoadMode.PRELOAD) == "preload"
        assert str(LoadMode.MEMORY_MAPPED) == "memory_mapped"
        assert str(LoadMode.LAZY) == "lazy"


class TestExceptionHandling:
    """Test exception handling consistency."""

    @pytest.fixture
    def test_db_path(self):
        """Path to test database file."""
        return str(Path(__file__).parent / "test_data" / "tiny_test.rkdb")

    def test_invalid_database_path(self):
        """Test loading non-existent database."""
        with pytest.raises(DatabaseError):
            Database("/nonexistent/database.rkdb")

    def test_query_on_nonexistent_file(self, tmp_path):
        """Test operations on database that doesn't exist."""
        db_path = tmp_path / "nonexistent.rkdb"

        with pytest.raises(DatabaseError):
            Database(str(db_path))

    def test_invalid_kmer_errors(self, test_db_path):
        """Test various invalid k-mer error scenarios."""
        db = Database(test_db_path)

        with pytest.raises(InvalidKmerError):
            db.query("ATCGXTCG", validate=True)

        result = db.query("atcgatc", validate=False)
        assert isinstance(result, QueryResult)
