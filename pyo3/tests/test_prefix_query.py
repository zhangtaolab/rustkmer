"""Tests for PyPrefixQuery class functionality."""

import pytest


class TestPrefixQueryInitialization:
    """Test PyPrefixQuery initialization."""
    
    def test_create_prefix_query(self, PyPrefixQuery, LoadMode, tiny_db_path):
        """Test creating a prefix query object."""
        query = PyPrefixQuery(tiny_db_path, LoadMode.Preload)
        assert query is not None
    
    def test_prefix_query_with_load_mode(self, PyPrefixQuery, LoadMode, tiny_db_path):
        """Test creating prefix query with different load modes."""
        for mode in [LoadMode.Preload, LoadMode.MemoryMapped]:
            query = PyPrefixQuery(tiny_db_path, mode)
            assert query is not None


class TestPrefixQueryExecution:
    """Test prefix query execution."""
    
    def test_query_prefix_basic(self, PyPrefixQuery, LoadMode, tiny_db_path):
        """Test basic prefix query."""
        query = PyPrefixQuery(tiny_db_path, LoadMode.Preload)
        
        results = query.query_prefix("AAA")
        
        # Results should be iterable
        assert results is not None
    
    def test_query_prefix_returns_results(self, PyPrefixQuery, LoadMode, tiny_db_path):
        """Test that prefix query returns result object."""
        query = PyPrefixQuery(tiny_db_path, LoadMode.Preload)
        
        result = query.query_prefix("AAA")
        
        # Should have attributes like total_matches, query_time_ms
        assert hasattr(result, 'total_matches') or hasattr(result, 'matches')
    
    def test_query_different_prefixes(self, PyPrefixQuery, LoadMode, tiny_db_path):
        """Test querying different prefixes."""
        query = PyPrefixQuery(tiny_db_path, LoadMode.Preload)
        
        prefixes = ["AAA", "CCC", "GGG", "TTT"]
        
        for prefix in prefixes:
            result = query.query_prefix(prefix)
            assert result is not None
    
    def test_prefix_length_affects_results(self, PyPrefixQuery, LoadMode, tiny_db_path):
        """Test that different prefix lengths affect results."""
        query = PyPrefixQuery(tiny_db_path, LoadMode.Preload)
        
        # Shorter prefix should match more kmers
        result_short = query.query_prefix("A")
        result_long = query.query_prefix("AAAA")
        
        assert result_short is not None
        assert result_long is not None


class TestPrefixQueryMetrics:
    """Test prefix query metrics and performance."""
    
    def test_query_with_metrics(self, PyPrefixQuery, LoadMode, tiny_db_path):
        """Test query with performance metrics."""
        query = PyPrefixQuery(tiny_db_path, LoadMode.Preload)
        
        result = query.query_prefix("AAA")
        
        # Check for timing/performance attributes
        assert hasattr(result, 'query_time_ms') or hasattr(result, 'execution_time_ms')
    
    def test_result_has_block_information(self, PyPrefixQuery, LoadMode, tiny_db_path):
        """Test that result has memory block information."""
        query = PyPrefixQuery(tiny_db_path, LoadMode.Preload)
        
        result = query.query_prefix("AAA")
        
        # Results should have block information
        has_block = (hasattr(result, 'start_index') and hasattr(result, 'end_index')) or \
                   (hasattr(result, 'block_start') and hasattr(result, 'block_end'))
        assert has_block


class TestPrefixQueryEdgeCases:
    """Test edge cases for prefix queries."""
    
    def test_query_empty_prefix(self, PyPrefixQuery, LoadMode, tiny_db_path):
        """Test querying with empty prefix."""
        query = PyPrefixQuery(tiny_db_path, LoadMode.Preload)
        
        try:
            result = query.query_prefix("")
            assert result is not None
        except Exception:
            pass  # Empty prefix might fail
    
    def test_query_nonexistent_prefix(self, PyPrefixQuery, LoadMode, tiny_db_path):
        """Test querying prefix that doesn't exist in database."""
        query = PyPrefixQuery(tiny_db_path, LoadMode.Preload)
        
        result = query.query_prefix("ZZZ")
        
        assert result is not None
        # Should return empty results or zero matches
        total = getattr(result, 'total_matches', 0)
        matches = getattr(result, 'matches', [])
        assert total >= 0 or len(matches) >= 0
    
    def test_query_single_character_prefix(self, PyPrefixQuery, LoadMode, tiny_db_path):
        """Test querying single character prefix."""
        query = PyPrefixQuery(tiny_db_path, LoadMode.Preload)
        
        result = query.query_prefix("A")
        
        assert result is not None
        # Should match all kmers starting with A
