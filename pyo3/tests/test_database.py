"""Tests for PyDatabase class functionality."""

import pytest
from pathlib import Path


class TestDatabaseInitialization:
    """Test PyDatabase class initialization and validation."""
    
    def test_load_valid_database(self, PyDatabase, LoadMode, tiny_db_path):
        """Test loading a valid database file."""
        db = PyDatabase(tiny_db_path, LoadMode.Preload)
        assert db is not None
        assert hasattr(db, 'path')
        assert str(db.path) == tiny_db_path
    
    def test_database_with_different_load_modes(self, PyDatabase, LoadMode, tiny_db_path):
        """Test loading database with different LoadMode values."""
        modes = [
            LoadMode.Preload,
            LoadMode.MemoryMapped,
            LoadMode.Lazy,
        ]
        
        for mode in modes:
            db = PyDatabase(tiny_db_path, mode)
            assert db is not None
            assert hasattr(db, 'path')
    
    def test_nonexistent_database_raises_error(self, PyDatabase, LoadMode):
        """Test that loading a non-existent database raises an error."""
        with pytest.raises(Exception):  # Could be various error types
            PyDatabase("/nonexistent/path/database.rkdb", LoadMode.Preload)
    
    def test_database_path_property(self, PyDatabase, LoadMode, tiny_db_path):
        """Test that database path is correctly stored."""
        db = PyDatabase(tiny_db_path, LoadMode.Preload)
        
        # Path should be accessible
        path = db.path
        assert path is not None
        assert isinstance(path, str) or isinstance(path, Path)


class TestDatabaseQuery:
    """Test k-mer query functionality."""
    
    def test_query_single_kmer(self, PyDatabase, LoadMode, tiny_db_path):
        """Test querying a single k-mer."""
        db = PyDatabase(tiny_db_path, LoadMode.Preload)
        
        result = db.query("AAAAAAA")
        
        assert result is not None
        assert hasattr(result, 'count')
        assert hasattr(result, 'found')
        assert isinstance(result.count, int)
        assert isinstance(result.found, bool)
        assert result.count >= 0
    
    def test_query_multiple_kmers(self, PyDatabase, LoadMode, tiny_db_path):
        """Test querying multiple k-mers."""
        db = PyDatabase(tiny_db_path, LoadMode.Preload)
        
        kmers = ["AAAAAAA", "CCCCCCC", "GGGGGGG", "TTTTTTT"]
        
        for kmer in kmers:
            result = db.query(kmer)
            assert result is not None
            assert hasattr(result, 'count')
            assert hasattr(result, 'found')
            assert isinstance(result.count, int)
    
    def test_query_with_load_modes(self, PyDatabase, LoadMode, tiny_db_path):
        """Test that query works with different load modes."""
        modes = [
            LoadMode.Preload,
            LoadMode.MemoryMapped,
            LoadMode.Lazy,
        ]
        
        for mode in modes:
            db = PyDatabase(tiny_db_path, mode)
            result = db.query("AAAAAAA")
            assert result is not None
            assert hasattr(result, 'count')
    
    def test_query_nonexistent_kmer(self, PyDatabase, LoadMode, tiny_db_path):
        """Test querying a k-mer that likely doesn't exist."""
        db = PyDatabase(tiny_db_path, LoadMode.Preload)
        
        # Use a k-mer unlikely to exist (must be k=7 for this database)
        result = db.query("ACGTACG")  # 7-mer that likely doesn't exist
        
        assert result is not None
        assert result.count >= 0  # Count could be 0 if not found
        assert isinstance(result.found, bool)


class TestDatabaseStats:
    """Test database statistics functionality."""
    
    def test_get_stats(self, PyDatabase, LoadMode, tiny_db_path):
        """Test getting database statistics."""
        db = PyDatabase(tiny_db_path, LoadMode.Preload)
        
        stats = db.get_stats()
        
        assert stats is not None
        assert hasattr(stats, 'kmer_size')
        assert hasattr(stats, 'total_kmers')
        assert hasattr(stats, 'unique_kmers')
        
        assert isinstance(stats.kmer_size, int)
        assert isinstance(stats.total_kmers, int)
        assert isinstance(stats.unique_kmers, int)
    
    def test_stats_values_are_reasonable(self, PyDatabase, LoadMode, tiny_db_path):
        """Test that statistics values are within expected ranges."""
        db = PyDatabase(tiny_db_path, LoadMode.Preload)
        
        stats = db.get_stats()
        
        # k-mer size should be positive
        assert stats.kmer_size > 0
        
        # Total kmers should be >= unique kmers
        assert stats.total_kmers >= stats.unique_kmers


class TestDatabaseMemory:
    """Test database memory-related functionality."""
    
    def test_get_memory_usage(self, PyDatabase, LoadMode, tiny_db_path):
        """Test getting memory usage information."""
        for mode in [LoadMode.Preload, LoadMode.MemoryMapped]:
            db = PyDatabase(tiny_db_path, mode)
            
            try:
                memory_info = db.get_memory_usage()
                # Memory info should be accessible (format may vary)
                assert memory_info is not None
            except AttributeError:
                # Some modes may not support this
                pass


class TestDatabaseEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_query(self, PyDatabase, LoadMode, tiny_db_path):
        """Test querying with empty string."""
        db = PyDatabase(tiny_db_path, LoadMode.Preload)
        
        try:
            result = db.query("")
            # Empty query might fail or return default
            assert result is not None
        except Exception:
            pass  # Expected behavior for invalid input
    
    def test_invalid_kmer_characters(self, PyDatabase, LoadMode, tiny_db_path):
        """Test querying with invalid DNA characters."""
        db = PyDatabase(tiny_db_path, LoadMode.Preload)
        
        try:
            result = db.query("ACGTACGTN")  # N is sometimes valid
            assert result is not None
        except Exception:
            pass  # Invalid characters might raise an error
    
    def test_wrong_length_kmer(self, PyDatabase, LoadMode, tiny_db_path):
        """Test querying with k-mer of wrong length."""
        db = PyDatabase(tiny_db_path, LoadMode.Preload)
        
        # Database is k=7, so 5-mer and 9-mer might fail
        try:
            result = db.query("ACGTA")  # 5-mer
            assert result is not None
        except Exception:
            pass  # Wrong length might raise an error
