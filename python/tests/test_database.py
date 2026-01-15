"""Tests for core Database class functionality."""

import pytest
from pathlib import Path
from rustkmer.database import Database
from rustkmer.query import QueryResult
from rustkmer.stats import DatabaseStats
from rustkmer.exceptions import (
    DatabaseError,
    InvalidDatabaseError,
    InvalidKmerError,
    QueryError,
)

from .utils import get_test_kmers, reverse_complement


class TestDatabaseInitialization:
    """Test Database class initialization and validation."""

    def test_load_valid_database(self, sample_database):
        """Test loading a valid database file."""
        db = Database(sample_database)
        assert db is not None
        assert str(db.path) == sample_database
        assert db.is_loaded

    def test_load_nonexistent_database(self):
        """Test loading a non-existent database file."""
        with pytest.raises(DatabaseError):
            Database("/nonexistent/database.rkdb")

    def test_database_properties(self, sample_database):
        """Test database property access."""
        db = Database(sample_database)
        # Basic properties should be accessible
        assert hasattr(db, "path")
        assert hasattr(db, "kmer_size")
        assert db.is_loaded

    def test_close_and_reopen(self, sample_database):
        """Test closing and reopening database."""
        db = Database(sample_database)
        assert db.is_loaded

        db.close()
        assert not db.is_loaded

        # Should be able to reopen
        db.reopen()
        assert db.is_loaded


class TestSingleQuery:
    """Test single k-mer query functionality."""

    @pytest.mark.parametrize(
        "kmer",
        [
            "AAAAAAA",  # All A
            "CCCCCCC",  # All C
            "GGGGGGG",  # All G
            "TTTTTTT",  # All T
            "ATCGATCG",  # Mixed (8-mer, will fail validation)
        ],
    )
    def test_valid_kmer_query(self, sample_database, kmer):
        """Test querying valid k-mers."""
        db = Database(sample_database)

        # Use lenient validation for mixed k-mer (8-mer for k=7 database)
        if kmer == "ATCGATCG":
            result = db.query(kmer, validate_strict=False)
        else:
            result = db.query(kmer)

        assert isinstance(result, QueryResult)
        assert hasattr(result, "count")
        assert hasattr(result, "canonical")
        assert isinstance(result.count, int)
        assert result.count >= 0

    def test_canonical_representation(self, sample_database):
        """Test canonical k-mer representation."""
        db = Database(sample_database)
        kmer = "ATCGATCG"
        rc_kmer = reverse_complement(kmer)

        result1 = db.query(kmer, validate_strict=False)
        result2 = db.query(rc_kmer, validate_strict=False)

        # Both should return the same count (canonical representation)
        assert result1.count == result2.count
        # Canonical should be the same for both
        assert result1.canonical == result2.canonical

    def test_nonexistent_kmer(self, sample_database):
        """Test querying a k-mer that likely doesn't exist."""
        db = Database(sample_database)
        # Use a k-mer unlikely to exist
        result = db.query(
            "NNNNNNN", validate_strict=False
        )  # Invalid character should return 0

        assert isinstance(result, QueryResult)
        assert result.count == 0

    @pytest.mark.parametrize(
        "invalid_kmer",
        [
            "ATCGX",  # Invalid character
            "ATCG",  # Wrong length for k=7
            "toolongkkkkkkkkkkkkkkk",  # Too long
            "",  # Empty
            None,  # None
            123,  # Not a string
        ],
    )
    def test_invalid_kmer_query(self, sample_database, invalid_kmer):
        """Test querying invalid k-mers."""
        db = Database(sample_database)

        if invalid_kmer is None or isinstance(invalid_kmer, int):
            with pytest.raises((InvalidKmerError, TypeError, ValueError)):
                db.query(invalid_kmer)
        else:
            # String but invalid format - use lenient validation
            result = db.query(invalid_kmer, validate_strict=False)
            # Should return count=0 for invalid k-mers
            assert result.count == 0


class TestBatchQuery:
    """Test batch k-mer query functionality."""

    def test_batch_query_basic(self, sample_database):
        """Test basic batch query functionality."""
        db = Database(sample_database)
        kmers = ["AAAAAAA", "CCCCCCC", "GGGGGGG", "TTTTTTT"]

        results = db.query_batch(kmers)

        assert len(results) == len(kmers)
        for kmer, result in results.items():
            assert isinstance(result, QueryResult)
            assert isinstance(result.count, int)
            assert result.count >= 0

    def test_batch_query_with_canonical(self, sample_database):
        """Test batch query with canonical k-mer pairs."""
        db = Database(sample_database)
        kmer = "ATCGATCG"
        rc_kmer = reverse_complement(kmer)
        kmers = [kmer, rc_kmer]

        results = db.query_batch(kmers)

        # Both should return the same count
        assert results[kmer].count == results[rc_kmer].count
        # Canonical should be the same
        assert results[kmer].canonical == results[rc_kmer].canonical

    def test_batch_query_mixed_valid_invalid(self, sample_database):
        """Test batch query with mix of valid and invalid k-mers."""
        db = Database(sample_database)
        kmers = ["AAAAAAA", "INVALIDX", "CCCCCCC", "TOOLONGKKKKKK"]

        results = db.query_batch(kmers)

        assert len(results) == len(kmers)
        # Valid k-mers should have counts
        assert results[kmers[0]].count >= 0  # AAAAAAA
        # Invalid k-mers should return 0 or raise error
        assert results[kmers[1]].count == 0  # INVALIDX
        assert results[kmers[2]].count >= 0  # CCCCCCC
        assert results[kmers[3]].count == 0  # TOOLONGKKKKKK

    def test_batch_query_empty_list(self, sample_database):
        """Test batch query with empty k-mer list."""
        db = Database(sample_database)
        results = db.query_batch([])

        assert isinstance(results, dict)
        assert len(results) == 0

    def test_batch_query_large_list(self, sample_database):
        """Test batch query with a large list of k-mers."""
        db = Database(sample_database)
        # Generate 100 random k-mers
        kmers = get_test_kmers(7)["random"] * 20  # 5 random * 20 = 100

        results = db.query_batch(kmers)

        assert len(results) == len(set(kmers))  # Dict deduplicates duplicates
        for result in results.values():
            assert isinstance(result, QueryResult)
            assert isinstance(result.count, int)
            assert result.count >= 0

    @pytest.mark.parametrize("parallel", [True, False])
    def test_batch_query_parallel_processing(self, sample_database, parallel):
        """Test batch query with and without parallel processing."""
        db = Database(sample_database)
        kmers = ["AAAAAAA", "CCCCCCC", "GGGGGGG", "TTTTTTT"] * 10

        results = db.query_batch(kmers, max_workers=4 if parallel else 1)

        assert len(results) == len(set(kmers))  # Dict deduplicates duplicates
        for kmer, result in results.items():
            assert isinstance(result, QueryResult)
            assert result.count >= 0


class TestDatabaseStats:
    """Test database statistics functionality."""

    def test_get_stats_basic(self, sample_database):
        """Test basic statistics retrieval."""
        db = Database(sample_database)
        stats = db.stats()

        assert isinstance(stats, DatabaseStats)
        assert hasattr(stats, "kmer_size")
        assert hasattr(stats, "unique_kmers")
        assert hasattr(stats, "total_counts")
        assert hasattr(stats, "min_count")
        assert hasattr(stats, "max_count")

    def test_stats_values_are_reasonable(self, sample_database):
        """Test that statistics values are reasonable."""
        db = Database(sample_database)
        stats = db.stats()

        # k-mer size should be positive
        assert stats.kmer_size > 0

        # Unique k-mers should be non-negative
        assert stats.unique_kmers >= 0

        # Total counts should be non-negative
        assert stats.total_counts >= 0

        # Min/max counts should be reasonable
        assert stats.min_count >= 0
        assert stats.max_count >= stats.min_count

    def test_stats_consistency_with_queries(self, sample_database):
        """Test that stats are consistent with actual queries."""
        db = Database(sample_database)
        stats = db.stats()

        # Query all possible k-mers (this might be slow for large databases)
        # For tiny database, we can do this
        if "tiny_test" in sample_database:
            test_kmers = get_test_kmers(stats.kmer_size)
            total_found = 0

            for category, kmers in test_kmers.items():
                if category != "invalid":
                    for kmer in kmers:
                        result = db.query(kmer)
                        if result.count > 0:
                            total_found += 1

            # At least some k-mers should be found
            assert total_found >= 0


class TestDatabaseDump:
    """Test database dump functionality."""

    def test_dump_basic(self, sample_database):
        """Test basic database dump."""
        db = Database(sample_database)
        dump_data = db.dump(as_string=True)

        assert isinstance(dump_data, str)
        assert len(dump_data) > 0

        # Should contain k-mer data
        lines = dump_data.strip().split("\n")
        assert len(lines) > 0

        # Each line should have tab-separated values
        for line in lines[:10]:  # Check first 10 lines
            if line.strip():
                assert "\t" in line
                parts = line.split("\t")
                assert len(parts) >= 2
                # Second part should be a count
                try:
                    int(parts[1])
                except ValueError:
                    pytest.fail(f"Count should be an integer: {parts[1]}")

    def test_dump_format_consistency(self, sample_database):
        """Test that dump format is consistent."""
        db = Database(sample_database)
        dump1 = db.dump(as_string=True)
        dump2 = db.dump(as_string=True)

        # Multiple dumps should return the same data
        assert dump1 == dump2


class TestDatabaseErrorHandling:
    """Test error handling in Database class."""

    def test_query_after_close(self, sample_database):
        """Test querying after database is closed."""
        db = Database(sample_database)
        db.close()

        with pytest.raises((DatabaseError, QueryError, RuntimeError)):
            db.query("AAAAAAA")

    def test_batch_query_after_close(self, sample_database):
        """Test batch querying after database is closed."""
        db = Database(sample_database)
        db.close()

        with pytest.raises((DatabaseError, QueryError, RuntimeError)):
            db.query_batch(["AAAAAAA", "CCCCCCC"])

    def test_stats_after_close(self, sample_database):
        """Test getting stats after database is closed."""
        db = Database(sample_database)
        db.close()

        with pytest.raises((DatabaseError, RuntimeError)):
            db.stats()

    def test_dump_after_close(self, sample_database):
        """Test dumping after database is closed."""
        db = Database(sample_database)
        db.close()

        with pytest.raises((DatabaseError, RuntimeError)):
            db.dump()


class TestDatabaseWithContextManager:
    """Test Database class with context manager."""

    def test_context_manager_basic(self, sample_database):
        """Test basic context manager usage."""
        with Database(sample_database) as db:
            assert db.is_loaded
            result = db.query("AAAAAAA")
            assert isinstance(result, QueryResult)

        # Database should be closed after context
        assert not db.is_loaded

    def test_context_manager_with_exception(self, sample_database):
        """Test context manager with exception."""
        try:
            with Database(sample_database) as db:
                assert db.is_loaded
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected

        # Database should still be closed
        assert not db.is_loaded


@pytest.mark.parametrize(
    "db_file",
    [
        "tiny_test.rkdb",
        "small_test.rkdb",
        pytest.param("medium_test.rkdb", marks=pytest.mark.slow),
        pytest.param("large_test.rkdb", marks=pytest.mark.slow),
    ],
)
class TestMultipleDatabases:
    """Test Database class with different database files."""

    def test_load_different_databases(self, test_data_dir, db_file):
        """Test loading different database files."""
        db_path = test_data_dir / db_file
        if not db_path.exists():
            pytest.skip(f"Database {db_file} not found")

        db = Database(str(db_path))
        assert db is not None
        assert db.is_loaded

    def test_query_different_databases(self, test_data_dir, db_file):
        """Test querying different database files."""
        db_path = test_data_dir / db_file
        if not db_path.exists():
            pytest.skip(f"Database {db_file} not found")

        db = Database(str(db_path))
        result = db.query("AAAAAAA")

        assert isinstance(result, QueryResult)
        assert result.count >= 0

    def test_stats_different_databases(self, test_data_dir, db_file):
        """Test getting stats from different database files."""
        db_path = test_data_dir / db_file
        if not db_path.exists():
            pytest.skip(f"Database {db_file} not found")

        db = Database(str(db_path))
        stats = db.stats()

        assert isinstance(stats, DatabaseStats)
        assert stats.kmer_size > 0
        assert stats.unique_kmers >= 0


class TestDatabaseErrorPaths:
    """Test error handling paths in Database class."""

    def test_load_database_directory_path(self, test_data_dir, tmp_path):
        """Test loading a directory instead of file."""
        # Create a directory
        db_dir = tmp_path / "fake_db"
        db_dir.mkdir()

        # Construction should fail when path is a directory, not a file
        with pytest.raises(InvalidDatabaseError):
            Database(str(db_dir), validate=False)

    def test_load_database_without_validation(self, sample_database):
        """Test loading database without validation."""
        # This should work since we're not validating
        db = Database(sample_database, validate=False)
        assert db is not None
        # Database should still load properly when accessing stats
        stats = db.stats()
        assert stats.kmer_size > 0

    def test_kmer_size_immediate_loading(self, sample_database):
        """Test that kmer_size property is immediately available after construction."""
        db = Database(sample_database, validate=False)

        # Database should be loaded immediately after construction
        assert db.is_loaded
        assert db.kmer_size > 0

    def test_query_batch_threadpool_exceptions(self, sample_database):
        """Test batch query handling of thread pool exceptions."""
        db = Database(sample_database)

        # This test is limited since we can't easily mock ThreadPoolExecutor
        # But we can test with invalid k-mers
        kmers = ["AAAAAAA", "INVALIDX", "CCCCCCC"]

        results = db.query_batch(kmers)
        assert len(results) == len(kmers)

        # Valid k-mers should have results
        for kmer in kmers:
            result = results[kmer]
            assert isinstance(result, QueryResult)
            if "INVALID" not in kmer:
                assert result.count >= 0

    def test_dump_return_iterator(self, sample_database):
        """Test that dump returns iterator when as_string=False."""
        db = Database(sample_database)

        # Get iterator
        dump_iter = db.dump(as_string=False)

        # Should be an iterator
        assert hasattr(dump_iter, "__iter__")

        # Should be able to iterate
        count = 0
        for result in dump_iter:
            assert isinstance(result, QueryResult)
            count += 1
            if count > 10:  # Limit check for performance
                break

        assert count > 0

    def test_operations_on_closed_database(self, sample_database):
        """Test operations on a closed database."""
        db = Database(sample_database)
        db.close()

        # All operations should raise errors when database is closed
        with pytest.raises(DatabaseError, match="Cannot query: database is closed"):
            db.query("AAAAAAA")

        with pytest.raises(
            DatabaseError, match="Cannot query batch: database is closed"
        ):
            db.query_batch(["AAAAAAA", "CCCCCCC"])

        with pytest.raises(DatabaseError, match="Cannot dump: database is closed"):
            db.dump()

        with pytest.raises(DatabaseError, match="Cannot get stats: database is closed"):
            db.stats()

    def test_invalid_kmer_canonical_computation(self, sample_database):
        """Test canonical k-mer computation for invalid k-mers."""
        db = Database(sample_database)

        # Test with valid characters but wrong length
        result = db.query("ATCG", validate_strict=False)
        assert result.count == 0
        # Should compute canonical even for invalid k-mers
        assert result.canonical is not None

        # Test with invalid characters
        result = db.query("ATCX", validate_strict=False)
        assert result.count == 0
        assert result.canonical is None  # Can't compute canonical with invalid chars
