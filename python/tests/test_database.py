"""
Unit tests for RustKmer Database functionality

This module tests the Database class and related functionality including:
- Database creation and initialization
- Query operations (single and batch)
- Database statistics and metadata
- Context manager support
- Error handling and edge cases
"""

import pytest
import tempfile
import os
from pathlib import Path

# Import the rustkmer classes we're testing
from rustkmer import Database, DatabaseError, QueryResult, DatabaseStats


class TestDatabaseCreation:
    """Test Database creation and initialization"""

    def test_in_memory_database_creation(self):
        """Test creating an in-memory database"""
        db = Database()
        assert db is not None
        assert not db.is_open()
        assert not db.is_preloaded()
        assert db.get_path() is None

    def test_file_database_creation(self):
        """Test creating a database with a file path"""
        with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            db = Database(file_path=tmp_path, preload=False)
            assert db is not None
            assert db.is_open()
            assert not db.is_preloaded()
            assert db.get_path() == tmp_path
        finally:
            os.unlink(tmp_path)

    def test_file_database_creation_with_preload(self):
        """Test creating a database with preload=True"""
        with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            db = Database(file_path=tmp_path, preload=True)
            assert db is not None
            assert db.is_open()
            assert db.is_preloaded()
            assert db.get_path() == tmp_path
        finally:
            os.unlink(tmp_path)

    def test_database_string_representation(self):
        """Test database string representations"""
        db = Database()
        repr_str = repr(db)
        str_str = str(db)
        assert "Database" in repr_str
        assert "closed" in repr_str
        assert repr_str == str_str

        with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            db_file = Database(file_path=tmp_path)
            repr_str = repr(db_file)
            assert tmp_path in repr_str
            assert "k=21" in repr_str
            assert "open=true" in repr_str
        finally:
            os.unlink(tmp_path)


class TestDatabaseQueries:
    """Test Database query operations"""

    def test_single_query(self):
        """Test querying a single k-mer"""
        with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            db = Database(file_path=tmp_path)
            result = db.query("ATCGATCGATCG")

            assert isinstance(result, QueryResult)
            assert result.kmer == "ATCGATCGATCG"
            assert result.count == 0
            assert result.found is False
        finally:
            os.unlink(tmp_path)

    def test_single_query_case_insensitive(self):
        """Test that k-mer queries are case insensitive"""
        with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            db = Database(file_path=tmp_path)
            result_lower = db.query("atcgtcgatcg")
            result_upper = db.query("ATCGATCGATCG")
            result_mixed = db.query("AtCgTaCgAtCg")

            # All should return uppercase (canonical form)
            assert result_lower.kmer == "ATCGTCGATCG"
            assert result_upper.kmer == "ATCGATCGATCG"
            assert result_mixed.kmer == "ATCGTACGATCG"
        finally:
            os.unlink(tmp_path)

    def test_multiple_queries(self):
        """Test querying multiple k-mers"""
        with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            db = Database(file_path=tmp_path)
            kmers = ["ATCGATCGATCG", "GCTAGCTAGCT", "AAAAAA", "CCCCCC"]
            results = db.query_multiple(kmers)

            assert len(results) == 4
            assert all(isinstance(r, QueryResult) for r in results)
            assert all(r.count == 0 for r in results)
            assert all(not r.found for r in results)

            # Check that k-mers are returned in uppercase
            assert results[0].kmer == "ATCGATCGATCG"
            assert results[1].kmer == "GCTAGCTAGCT"
        finally:
            os.unlink(tmp_path)

    def test_empty_query_list(self):
        """Test querying an empty list of k-mers"""
        with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            db = Database(file_path=tmp_path)
            results = db.query_multiple([])
            assert results == []
        finally:
            os.unlink(tmp_path)

    def test_query_on_closed_database(self):
        """Test querying a closed database raises error"""
        db = Database()
        db.close()

        with pytest.raises(DatabaseError) as exc_info:
            db.query("ATCG")

        assert "Database is not open" in str(exc_info.value)

    def test_query_multiple_on_closed_database(self):
        """Test querying multiple k-mers on a closed database raises error"""
        db = Database()
        db.close()

        with pytest.raises(DatabaseError) as exc_info:
            db.query_multiple(["ATCG", "GCTA"])

        assert "Database is not open" in str(exc_info.value)


class TestDatabaseStatistics:
    """Test Database statistics and metadata"""

    def test_database_stats(self):
        """Test getting database statistics"""
        with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            db = Database(file_path=tmp_path)
            stats = db.get_stats()

            assert isinstance(stats, DatabaseStats)
            assert stats.kmer_size == 21
            assert stats.total_kmers == 0
            assert stats.unique_kmers == 0
            assert stats.sorted is True
            assert stats.canonical is False
            assert stats.preloaded is False
        finally:
            os.unlink(tmp_path)

    def test_database_stats_with_preload(self):
        """Test database statistics with preloaded database"""
        with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            db = Database(file_path=tmp_path, preload=True)
            stats = db.get_stats()
            assert stats.preloaded is True
        finally:
            os.unlink(tmp_path)

    def test_get_kmer_size(self):
        """Test getting k-mer size"""
        with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            db = Database(file_path=tmp_path)
            kmer_size = db.get_kmer_size()
            assert kmer_size == 21
        finally:
            os.unlink(tmp_path)

    def test_get_kmer_size_no_database(self):
        """Test getting k-mer size from in-memory database raises error"""
        db = Database()

        with pytest.raises(DatabaseError) as exc_info:
            db.get_kmer_size()

        assert "No database loaded" in str(exc_info.value)

    def test_stats_on_closed_database(self):
        """Test getting stats from closed database raises error"""
        db = Database(file_path="/tmp/test.rkdb")
        db.close()

        with pytest.raises(DatabaseError) as exc_info:
            db.get_stats()

        assert "Database is not open" in str(exc_info.value)


class TestDatabaseLifecycle:
    """Test Database lifecycle operations"""

    def test_load_and_close(self):
        """Test loading and closing databases"""
        with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            db = Database()
            assert not db.is_open()

            db.load(tmp_path, preload=False)
            assert db.is_open()
            assert not db.is_preloaded()
            assert db.get_path() == tmp_path

            db.close()
            assert not db.is_open()
        finally:
            os.unlink(tmp_path)

    def test_load_with_preload(self):
        """Test loading database with preload"""
        with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            db = Database()
            db.load(tmp_path, preload=True)
            assert db.is_open()
            assert db.is_preloaded()
        finally:
            os.unlink(tmp_path)

    def test_context_manager(self):
        """Test database as context manager"""
        with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with Database(file_path=tmp_path) as db:
                assert db.is_open()
                result = db.query("ATCGATCGATCG")
                assert isinstance(result, QueryResult)

            # Database should be closed after context
            assert not db.is_open()
        finally:
            os.unlink(tmp_path)

    def test_context_manager_exception(self):
        """Test context manager handles exceptions properly"""
        with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with pytest.raises(ValueError):
                with Database(file_path=tmp_path) as db:
                    assert db.is_open()
                    raise ValueError("Test exception")

            # Database should still be closed after exception
            assert not db.is_open()
        finally:
            os.unlink(tmp_path)


class TestDatabaseEdgeCases:
    """Test edge cases and error handling"""

    def test_nonexistent_file_path(self):
        """Test creating database with non-existent file path"""
        nonexistent_path = "/tmp/nonexistent_12345.rkdb"

        # This should work - the database is created but empty
        db = Database(file_path=nonexistent_path)
        assert db.is_open()
        assert db.get_path() == nonexistent_path

        # Clean up
        db.close()
        if os.path.exists(nonexistent_path):
            os.unlink(nonexistent_path)

    def test_invalid_kmer_sequences(self):
        """Test querying with invalid k-mer sequences"""
        with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            db = Database(file_path=tmp_path)

            # Test with invalid characters (should still work, just treat as not found)
            result = db.query("ATXG")  # X is not a valid DNA base
            assert isinstance(result, QueryResult)
            assert result.count == 0
            assert not result.found

            # Test with very short k-mer
            result = db.query("A")
            assert isinstance(result, QueryResult)

            # Test with very long k-mer (within safe limits)
            long_kmer = "A" * 30
            result = db.query(long_kmer)
            assert isinstance(result, QueryResult)
        finally:
            os.unlink(tmp_path)

    def test_multiple_database_instances(self):
        """Test creating multiple database instances"""
        with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp1, \
             tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp2:
            tmp_path1 = tmp1.name
            tmp_path2 = tmp2.name

        try:
            db1 = Database(file_path=tmp_path1)
            db2 = Database(file_path=tmp_path2)
            db3 = Database()  # In-memory

            assert db1.get_path() == tmp_path1
            assert db2.get_path() == tmp_path2
            assert db3.get_path() is None

            assert db1.is_open()
            assert db2.is_open()
            assert not db3.is_open()

            # All should work independently
            result1 = db1.query("ATCG")
            result2 = db2.query("GCTA")

            assert result1.kmer == "ATCG"
            assert result2.kmer == "GCTA"
        finally:
            os.unlink(tmp_path1)
            os.unlink(tmp_path2)

    def test_database_state_consistency(self):
        """Test that database state remains consistent across operations"""
        with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            db = Database(file_path=tmp_path, preload=True)

            # Initial state
            assert db.is_open()
            assert db.is_preloaded()

            # After queries
            db.query("ATCG")
            db.query_multiple(["GCTA", "CCCC"])
            assert db.is_open()
            assert db.is_preloaded()

            # After getting stats
            db.get_stats()
            db.get_kmer_size()
            assert db.is_open()
            assert db.is_preloaded()

            # After close
            db.close()
            assert not db.is_open()
            # Note: is_preloaded() might still return True, but is_open() is what matters
        finally:
            os.unlink(tmp_path)


class TestQueryResultAndStatsClasses:
    """Test QueryResult and DatabaseStats classes"""

    def test_query_result_creation(self):
        """Test QueryResult can be created directly"""
        result = QueryResult("ATCG", 5, True)
        assert result.kmer == "ATCG"
        assert result.count == 5
        assert result.found is True

    def test_query_result_string_representation(self):
        """Test QueryResult string representation"""
        result = QueryResult("ATCG", 5, True)
        repr_str = repr(result)
        str_str = str(result)

        assert "QueryResult" in repr_str
        assert "kmer='ATCG'" in repr_str
        assert "count=5" in repr_str
        assert "found=true" in repr_str
        assert repr_str == str_str

    def test_database_stats_creation(self):
        """Test DatabaseStats can be created directly"""
        stats = DatabaseStats(
            kmer_size=31,
            total_kmers=1000,
            unique_kmers=800,
            sorted=True,
            canonical=True,
            preloaded=False
        )

        assert stats.kmer_size == 31
        assert stats.total_kmers == 1000
        assert stats.unique_kmers == 800
        assert stats.sorted is True
        assert stats.canonical is True
        assert stats.preloaded is False

    def test_database_stats_string_representation(self):
        """Test DatabaseStats string representation"""
        stats = DatabaseStats(
            kmer_size=21,
            total_kmers=500,
            unique_kmers=400,
            sorted=False,
            canonical=True,
            preloaded=True
        )

        repr_str = repr(stats)
        str_str = str(stats)

        assert "DatabaseStats" in repr_str
        assert "kmer_size=21" in repr_str
        assert "total_kmers=500" in repr_str
        assert "unique_kmers=400" in repr_str
        assert "sorted=false" in repr_str
        assert "canonical=true" in repr_str
        assert "preloaded=true" in repr_str
        assert repr_str == str_str


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])