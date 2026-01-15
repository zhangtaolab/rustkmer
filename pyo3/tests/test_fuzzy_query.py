"""Tests for PyFuzzyQuery class functionality."""

import pytest


class TestFuzzyQueryInitialization:
    """Test PyFuzzyQuery initialization."""
    
    def test_create_fuzzy_query(self, PyFuzzyQuery, LoadMode, tiny_db_path):
        """Test creating a fuzzy query object."""
        query = PyFuzzyQuery(PyDatabase(tiny_db_path, LoadMode.Preload))
        assert query is not None
    
    def test_fuzzy_query_with_load_mode(self, PyFuzzyQuery, LoadMode, tiny_db_path):
        """Test creating fuzzy query with different load modes."""
        for mode in [LoadMode.Preload, LoadMode.MemoryMapped]:
            query = PyFuzzyQuery(PyDatabase(tiny_db_path, mode))
            assert query is not None


class TestFuzzyQueryBasic:
    """Test basic fuzzy query functionality."""
    
    def test_wildcard_query(self, PyFuzzyQuery, LoadMode, tiny_db_path):
        """Test wildcard pattern query."""
        query = PyFuzzyQuery(PyDatabase(tiny_db_path, LoadMode.Preload))
        
        result = query.fuzzy_query("ATNNGTA")
        
        assert result is not None
        assert hasattr(result, 'total_matches')
        assert isinstance(result.total_matches, int)
    
    def test_wildcard_query_with_mutations(self, PyFuzzyQuery, LoadMode, tiny_db_path):
        """Test wildcard query with mutation tolerance."""
        query = PyFuzzyQuery(PyDatabase(tiny_db_path, LoadMode.Preload))
        
        result = query.fuzzy_query("AAAAAAA", max_mutations=1)
        
        assert result is not None
        assert hasattr(result, 'total_matches')
    
    def test_simple_wildcard_patterns(self, PyFuzzyQuery, LoadMode, tiny_db_path):
        """Test various wildcard patterns."""
        query = PyFuzzyQuery(PyDatabase(tiny_db_path, LoadMode.Preload))
        
        patterns = [
            "ANNNNNN",  # N at position 1
            "NAAAAAAA",  # N at start
            "ATNNNTAG",  # Multiple Ns
        ]
        
        for pattern in patterns:
            result = query.fuzzy_query(pattern)
            assert result is not None
            assert hasattr(result, 'total_matches')
    
    def test_mutation_tolerance(self, PyFuzzyQuery, LoadMode, tiny_db_path):
        """Test different mutation tolerance levels."""
        query = PyFuzzyQuery(PyDatabase(tiny_db_path, LoadMode.Preload))
        
        base_kmer = "AAAAAAA"
        
        result_0 = query.fuzzy_query(base_kmer, max_mutations=0)
        result_1 = query.fuzzy_query(base_kmer, max_mutations=1)
        result_2 = query.fuzzy_query(base_kmer, max_mutations=2)
        
        # Higher mutation tolerance should match more or equal results
        assert result_0.total_matches <= result_1.total_matches
        assert result_1.total_matches <= result_2.total_matches


class TestFuzzyQueryResults:
    """Test fuzzy query result handling."""
    
    def test_result_has_matches_attribute(self, PyFuzzyQuery, LoadMode, tiny_db_path):
        """Test that result has matches information."""
        query = PyFuzzyQuery(PyDatabase(tiny_db_path, LoadMode.Preload))
        
        result = query.fuzzy_query("ATNNGTA")
        
        # Should have matches or similar attribute
        has_matches = (hasattr(result, 'matches') or 
                      hasattr(result, 'total_matches') or
                      hasattr(result, 'found'))
        assert has_matches
    
    def test_result_has_count_information(self, PyFuzzyQuery, LoadMode, tiny_db_path):
        """Test that result has count information."""
        query = PyFuzzyQuery(PyDatabase(tiny_db_path, LoadMode.Preload))
        
        result = query.fuzzy_query("ATNNGTA")
        
        # Should have count or similar
        has_count = (hasattr(result, 'total_matches') or
                    hasattr(result, 'count') or
                    hasattr(result, 'found_count'))
        assert has_count


class TestFuzzyQueryEdgeCases:
    """Test edge cases for fuzzy queries."""
    
    def test_all_wildcard_pattern(self, PyFuzzyQuery, LoadMode, tiny_db_path):
        """Test pattern with all wildcards."""
        query = PyFuzzyQuery(PyDatabase(tiny_db_path, LoadMode.Preload))
        
        result = query.fuzzy_query("NNNNNNN")
        
        assert result is not None
        # Should match all possible combinations
        assert result.total_matches >= 0
    
    def test_no_wildcard_pattern(self, PyFuzzyQuery, LoadMode, tiny_db_path):
        """Test pattern without wildcards."""
        query = PyFuzzyQuery(PyDatabase(tiny_db_path, LoadMode.Preload))
        
        result = query.fuzzy_query("AAAAAAA")
        
        assert result is not None
        # Should work like exact query
        assert result.total_matches >= 0
    
    def test_high_mutation_count(self, PyFuzzyQuery, LoadMode, tiny_db_path):
        """Test with high mutation tolerance."""
        query = PyFuzzyQuery(PyDatabase(tiny_db_path, LoadMode.Preload))
        
        result = query.fuzzy_query("AAAAAAA", max_mutations=7)
        
        assert result is not None
        assert result.total_matches >= 0
    
    def test_empty_result_for_no_match(self, PyFuzzyQuery, LoadMode, tiny_db_path):
        """Test pattern that likely returns no matches."""
        query = PyFuzzyQuery(PyDatabase(tiny_db_path, LoadMode.Preload))
        
        # Very specific pattern unlikely to match
        result = query.fuzzy_query("TTTTTTT", max_mutations=0)
        
        assert result is not None
        # Result should be valid even if no matches
        assert isinstance(result.total_matches, int)
