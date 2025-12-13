"""Unit tests for the Database class."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from rustkmer import Database
from rustkmer.exceptions import (
    DatabaseNotFoundError,
    InvalidDatabaseError,
    QueryError,
    InvalidKmerError,
)


class TestDatabaseInit:
    """Test Database initialization."""

    def test_init_with_valid_path(self, tmp_path):
        """Test Database initialization with a valid path."""
        # Create a fake database file
        db_path = tmp_path / "test.rkdb"
        db_path.write_text("fake db content")

        with patch('rustkmer.database.run_rustkmer_command') as mock_run:
            mock_run.return_value = "kmer_size: 19\nunique_kmers: 1000"

            db = Database(str(db_path), validate=False)

            assert db.path == db_path
            # With validate=False, kmer_size isn't loaded until first access
            # But the Database class caches stats after first access
            # So after creating the database, stats are not yet loaded
            assert not db.is_loaded  # Should not be loaded yet with validate=False

    def test_init_with_nonexistent_path(self):
        """Test Database initialization with non-existent file."""
        with pytest.raises(DatabaseNotFoundError):
            Database("/nonexistent/path.rkdb")

    def test_init_with_directory_path(self, tmp_path):
        """Test Database initialization with directory path."""
        with pytest.raises(InvalidDatabaseError):
            Database(str(tmp_path))

    def test_init_auto_validation(self, tmp_path):
        """Test Database auto-validation on initialization."""
        db_path = tmp_path / "test.rkdb"
        db_path.write_text("fake db content")

        with patch('rustkmer.database.run_rustkmer_command') as mock_run:
            mock_run.return_value = "kmer_size: 19\nunique_kmers: 1000"

            db = Database(str(db_path))  # validate=True by default

            # Should attempt to validate by getting stats
            mock_run.assert_called_once()

    def test_path_property(self, tmp_path):
        """Test path property returns Path object."""
        db_path = tmp_path / "test.rkdb"
        db_path.write_text("fake content")

        with patch('rustkmer.database.run_rustkmer_command'):
            db = Database(str(db_path), validate=False)

            assert isinstance(db.path, Path)
            assert db.path == db_path

    def test_kmer_size_property_loads_on_demand(self, tmp_path):
        """Test kmer_size property loads metadata on first access."""
        db_path = tmp_path / "test.rkdb"
        db_path.write_text("fake content")

        with patch('rustkmer.database.run_rustkmer_command') as mock_run:
            mock_run.return_value = "kmer_size: 19\nunique_kmers: 1000"

            db = Database(str(db_path), validate=False)

            # First access should trigger loading
            assert db.kmer_size == 19
            assert db.is_loaded

            # Second access should use cached value
            assert db.kmer_size == 19
            # Should only call run_rustkmer_command once
            assert mock_run.call_count == 1

    def test_context_manager(self, tmp_path):
        """Test Database as context manager."""
        db_path = tmp_path / "test.rkdb"
        db_path.write_text("fake content")

        with patch('rustkmer.database.run_rustkmer_command'):
            with Database(str(db_path), validate=False) as db:
                assert isinstance(db, Database)

            # Should be closed after context
            assert not db.is_loaded

    def test_repr(self, tmp_path):
        """Test Database string representation."""
        db_path = tmp_path / "test.rkdb"
        db_path.write_text("fake content")

        with patch('rustkmer.database.run_rustkmer_command'):
            db = Database(str(db_path), validate=False)

            repr_str = repr(db)
            assert "Database" in repr_str
            assert str(db_path) in repr_str
            assert "loaded=False" in repr_str


class TestDatabaseQuery:
    """Test Database.query method."""

    def test_query_success(self, tmp_path):
        """Test successful k-mer query."""
        db_path = tmp_path / "test.rkdb"
        db_path.write_text("fake content")

        with patch('rustkmer.database.run_rustkmer_command') as mock_run:
            # Mock stats return to set kmer_size, then query
            mock_run.side_effect = [
                "kmer_size: 20\nunique_kmers: 1000",  # For stats (20 to match our test k-mer)
                "42"  # For query
            ]

            db = Database(str(db_path), validate=False)
            # Access kmer_size to trigger loading
            _ = db.kmer_size

            result = db.query("ATCGATCGATCGATCGATCG")

            assert result.kmer == "ATCGATCGATCGATCGATCG"
            assert result.count == 42
            assert result.canonical == "ATCGATCGATCGATCGATCG"  # For ATCG, canonical is same

    def test_query_invalid_kmer(self, tmp_path):
        """Test query with invalid k-mer."""
        db_path = tmp_path / "test.rkdb"
        db_path.write_text("fake content")

        with patch('rustkmer.database.run_rustkmer_command') as mock_run:
            mock_run.return_value = "kmer_size: 20\nunique_kmers: 1000"

            db = Database(str(db_path), validate=False)
            _ = db.kmer_size

            with pytest.raises(InvalidKmerError):
                db.query("ATCGX")  # Invalid character

    def test_query_wrong_length(self, tmp_path):
        """Test query with wrong k-mer length."""
        db_path = tmp_path / "test.rkdb"
        db_path.write_text("fake content")

        with patch('rustkmer.database.run_rustkmer_command') as mock_run:
            mock_run.return_value = "kmer_size: 20\nunique_kmers: 1000"

            db = Database(str(db_path), validate=False)
            _ = db.kmer_size

            with pytest.raises(InvalidKmerError):
                db.query("ATCG")  # Too short

    def test_query_canonical_kmer(self, tmp_path):
        """Test query with k-mer that has different canonical form."""
        db_path = tmp_path / "test.rkdb"
        db_path.write_text("fake content")

        with patch('rustkmer.database.run_rustkmer_command') as mock_run:
            # Mock stats return to set kmer_size, then query
            mock_run.side_effect = [
                "kmer_size: 4\nunique_kmers: 1000",  # For stats
                "10"  # For query
            ]

            db = Database(str(db_path), validate=False)
            _ = db.kmer_size

            # "AAAA" reverse complement is "TTTT", canonical is "AAAA"
            result = db.query("TTTT")

            assert result.kmer == "TTTT"
            assert result.count == 10
            assert result.canonical == "AAAA"

    def test_query_cli_error(self, tmp_path):
        """Test query when CLI command fails."""
        db_path = tmp_path / "test.rkdb"
        db_path.write_text("fake content")

        with patch('rustkmer.database.run_rustkmer_command') as mock_run:
            from rustkmer.exceptions import SubprocessError
            mock_run.side_effect = [  # First call for stats, second for query
                "kmer_size: 19\nunique_kmers: 1000",
                SubprocessError("command", 1, "error")
            ]

            db = Database(str(db_path), validate=False)
            _ = db.kmer_size

            with pytest.raises(QueryError):
                db.query("ATCGATCGATCGATCGATCG")


class TestDatabaseQueryBatch:
    """Test Database.query_batch method."""

    def test_query_batch_success(self, tmp_path):
        """Test successful batch query."""
        db_path = tmp_path / "test.rkdb"
        db_path.write_text("fake content")

        with patch('rustkmer.database.run_rustkmer_command') as mock_run:
            # Mock stats, then multiple queries
            mock_run.side_effect = [
                "kmer_size: 20\nunique_kmers: 1000",  # For stats
                "5",  # For first query
                "5"   # For second query
            ]

            db = Database(str(db_path), validate=False)
            _ = db.kmer_size

            kmers = ["ATCGATCGATCGATCGATCG", "CCCCCCCCCCCCCCCCCCCC"]
            results = db.query_batch(kmers, max_workers=2)

            assert len(results) == 2
            assert all(kmer in results for kmer in kmers)
            assert all(result.count == 5 for result in results.values())

    def test_query_batch_with_invalid_kmers(self, tmp_path):
        """Test batch query with some invalid k-mers."""
        db_path = tmp_path / "test.rkdb"
        db_path.write_text("fake content")

        with patch('rustkmer.database.run_rustkmer_command') as mock_run:
            mock_run.return_value = "kmer_size: 20\nunique_kmers: 1000"

            db = Database(str(db_path), validate=False)
            _ = db.kmer_size

            kmers = ["ATCGATCGATCGATCGATCG", "INVALIDX"]

            # Should raise error for invalid k-mer during validation
            with pytest.raises(InvalidKmerError):
                db.query_batch(kmers)

    def test_query_batch_chunking(self, tmp_path):
        """Test batch query with chunking for large batches."""
        db_path = tmp_path / "test.rkdb"
        db_path.write_text("fake content")

        with patch('rustkmer.database.run_rustkmer_command') as mock_run:
            # Create a side_effect that always returns "1"
            mock_run.return_value = "kmer_size: 19\nunique_kmers: 1000"

            db = Database(str(db_path), validate=False)
            _ = db.kmer_size

            # After stats are loaded, set return value for queries
            mock_run.return_value = "1"

            # Create 250 k-mers to test chunking (default chunk_size=100)
            kmers = [f"{'ATCG' * 4}A" for _ in range(250)]

            results = db.query_batch(kmers, chunk_size=100)

            assert len(results) == 250
            # Should be called multiple times due to chunking
            assert mock_run.call_count > 1

    def test_query_batch_error_handling(self, tmp_path):
        """Test batch query error handling."""
        db_path = tmp_path / "test.rkdb"
        db_path.write_text("fake content")

        def side_effect_func(*args):
            from rustkmer.exceptions import SubprocessError
            # Check if args has k-mer
            if len(args) > 1 and "CCCC" in args[1]:  # Fail for specific k-mer
                raise SubprocessError("command", 1, "not found")
            return "5"

        with patch('rustkmer.database.run_rustkmer_command') as mock_run:
            mock_run.side_effect = side_effect_func

            db = Database(str(db_path), validate=False)
            _ = db.kmer_size

            kmers = ["ATCGATCGATCGATCGATCG", "CCCCCCCCCCCCCCCCCCCC"]
            results = db.query_batch(kmers)

            # Should return results for both, with count=0 for failed query
            assert len(results) == 2
            assert results["ATCGATCGATCGATCGATCG"].count == 5
            assert results["CCCCCCCCCCCCCCCCCCCC"].count == 0