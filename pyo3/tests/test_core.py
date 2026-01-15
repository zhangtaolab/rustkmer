"""Core PyO3 binding tests that work with the actual API."""

import pytest


class TestPyDatabase:
    """Test PyDatabase class."""
    
    def test_query_kmer(self, tiny_db_path):
        """Test querying a k-mer."""
        import rustkmer_pyo3
        db = rustkmer_pyo3.PyDatabase(tiny_db_path, rustkmer_pyo3.LoadMode.Preload)
        
        result = db.query("AAAAAAA")
        
        assert hasattr(result, 'count')
        assert hasattr(result, 'found')
        assert isinstance(result.count, int)
        assert isinstance(result.found, bool)
    
    def test_get_stats(self, tiny_db_path):
        """Test getting database statistics."""
        import rustkmer_pyo3
        db = rustkmer_pyo3.PyDatabase(tiny_db_path, rustkmer_pyo3.LoadMode.Preload)
        
        stats = db.get_stats()
        
        assert hasattr(stats, 'kmer_size')
        assert hasattr(stats, 'total_kmers')
        assert hasattr(stats, 'unique_kmers')
        assert stats.kmer_size > 0
    
    def test_all_load_modes(self, tiny_db_path):
        """Test all load modes."""
        import rustkmer_pyo3
        
        for mode in [rustkmer_pyo3.LoadMode.Preload, 
                     rustkmer_pyo3.LoadMode.MemoryMapped,
                     rustkmer_pyo3.LoadMode.Lazy]:
            db = rustkmer_pyo3.PyDatabase(tiny_db_path, mode)
            assert db is not None
    
    def test_wrong_length_kmer_raises_error(self, tiny_db_path):
        """Test that wrong length k-mers raise an error."""
        import rustkmer_pyo3
        db = rustkmer_pyo3.PyDatabase(tiny_db_path, rustkmer_pyo3.LoadMode.Preload)
        
        with pytest.raises(Exception):
            db.query("ACGTA")  # Wrong length for k=7 database


class TestPyFuzzyQuery:
    """Test PyFuzzyQuery class."""
    
    def test_fuzzy_query_basic(self, tiny_db_path):
        """Test basic fuzzy query."""
        import rustkmer_pyo3
        db = rustkmer_pyo3.PyDatabase(tiny_db_path, rustkmer_pyo3.LoadMode.Preload)
        query = rustkmer_pyo3.PyFuzzyQuery(db)
        
        result = query.fuzzy_query("ANNNNNN", max_mutations=1)
        
        assert hasattr(result, 'total_matches')
        assert isinstance(result.total_matches, int)
    
    def test_fuzzy_query_with_position_mutations(self, tiny_db_path):
        """Test fuzzy query with position mutations."""
        import rustkmer_pyo3
        db = rustkmer_pyo3.PyDatabase(tiny_db_path, rustkmer_pyo3.LoadMode.Preload)
        query = rustkmer_pyo3.PyFuzzyQuery(db)
        
        # Use correct format: "positions:limit" 
        result = query.fuzzy_query_with_position_mutations("ANNNNNN", 1, "0,6:1")
        
        assert hasattr(result, 'total_matches')
        assert isinstance(result.total_matches, int)


class TestPyPrefixQuery:
    """Test PyPrefixQuery class."""
    
    def test_prefix_query_returns_dict(self, tiny_db_path):
        """Test that prefix query returns a dict."""
        import rustkmer_pyo3
        query = rustkmer_pyo3.PyPrefixQuery(tiny_db_path)
        
        result = query.query_prefix("AAA")
        
        # Result is a dict, not an object with attributes
        assert isinstance(result, dict)
        assert len(result) > 0
    
    def test_prefix_query_single_char(self, tiny_db_path):
        """Test querying single character prefix."""
        import rustkmer_pyo3
        query = rustkmer_pyo3.PyPrefixQuery(tiny_db_path)
        
        result = query.query_prefix("A")
        
        assert isinstance(result, dict)
        assert len(result) > 0
    
    def test_prefix_query_nonexistent(self, tiny_db_path):
        """Test querying non-existent prefix."""
        import rustkmer_pyo3
        query = rustkmer_pyo3.PyPrefixQuery(tiny_db_path)
        
        # Use valid DNA characters for prefix
        result = query.query_prefix("TTT")
        
        assert isinstance(result, dict)
        # Result should be empty or have few matches


class TestPyKmerCounter:
    """Test PyKmerCounter class."""
    
    def test_create_counter(self):
        """Test creating a counter."""
        import rustkmer_pyo3
        counter = rustkmer_pyo3.PyKmerCounter(21, True, 1000)
        
        assert counter is not None
        assert hasattr(counter, 'get_stats')
    
    def test_get_stats(self):
        """Test getting counter stats."""
        import rustkmer_pyo3
        counter = rustkmer_pyo3.PyKmerCounter(21, True, 1000)
        
        stats = counter.get_stats()
        
        assert stats is not None
        assert hasattr(stats, 'unique_kmers')
        assert hasattr(stats, 'total_kmers')


class TestLoadMode:
    """Test LoadMode enum."""
    
    def test_load_mode_values(self):
        """Test LoadMode enum values."""
        import rustkmer_pyo3
        
        assert hasattr(rustkmer_pyo3.LoadMode, 'Preload')
        assert hasattr(rustkmer_pyo3.LoadMode, 'MemoryMapped')
        assert hasattr(rustkmer_pyo3.LoadMode, 'Lazy')
        
        # All should be different
        assert rustkmer_pyo3.LoadMode.Preload != rustkmer_pyo3.LoadMode.MemoryMapped
        assert rustkmer_pyo3.LoadMode.MemoryMapped != rustkmer_pyo3.LoadMode.Lazy


class TestModuleCompleteness:
    """Test that all expected classes exist."""
    
    def test_core_classes_available(self):
        """Test that all core classes are available."""
        import rustkmer_pyo3
        
        assert hasattr(rustkmer_pyo3, 'PyDatabase')
        assert hasattr(rustkmer_pyo3, 'PyKmerCounter')
        assert hasattr(rustkmer_pyo3, 'PyFuzzyQuery')
        assert hasattr(rustkmer_pyo3, 'PyPrefixQuery')
        assert hasattr(rustkmer_pyo3, 'PyQueryResult')
        assert hasattr(rustkmer_pyo3, 'PyDatabaseStats')
        assert hasattr(rustkmer_pyo3, 'LoadMode')
        assert hasattr(rustkmer_pyo3, 'RustKmerError')
