"""Core PyO3 binding tests that work with the actual API."""

import pytest


class TestPyDatabase:
    """Test PyDatabase class."""

    def test_query_kmer(self, tiny_db_path):
        """Test querying a k-mer."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        result = db.query("AAAAAAA")

        assert hasattr(result, "count")
        assert hasattr(result, "found")
        assert isinstance(result.count, int)
        assert isinstance(result.found, bool)

    def test_get_stats(self, tiny_db_path):
        """Test getting database statistics."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        stats = db.get_stats()

        assert hasattr(stats, "kmer_size")
        assert hasattr(stats, "total_kmers")
        assert hasattr(stats, "unique_kmers")
        assert stats.kmer_size > 0

    def test_all_load_modes(self, tiny_db_path):
        """Test all load modes."""
        import pyrustkmer

        for mode in [
            pyrustkmer.LoadMode.Preload,
            pyrustkmer.LoadMode.MemoryMapped,
            pyrustkmer.LoadMode.Lazy,
        ]:
            db = pyrustkmer.PyDatabase(tiny_db_path, mode)
            assert db is not None

    def test_wrong_length_kmer_raises_error(self, tiny_db_path):
        """Test that wrong length k-mers raise an error."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        with pytest.raises(Exception):
            db.query("ACGTA")  # Wrong length for k=7 database


class TestPyFuzzyQuery:
    """Test PyFuzzyQuery class."""

    def test_fuzzy_query_basic(self, tiny_db_path):
        """Test basic fuzzy query."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        query = pyrustkmer.PyFuzzyQuery(db)

        result = query.fuzzy_query("ANNNNNN", max_mutations=1)

        assert hasattr(result, "total_matches")
        assert isinstance(result.total_matches, int)

    def test_fuzzy_query_with_position_mutations(self, tiny_db_path):
        """Test fuzzy query with position mutations."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        query = pyrustkmer.PyFuzzyQuery(db)

        # Use correct format: "positions:limit"
        result = query.fuzzy_query_with_position_mutations("ANNNNNN", 1, "0,6:1")

        assert hasattr(result, "total_matches")
        assert isinstance(result.total_matches, int)


class TestPyPrefixQuery:
    """Test PyPrefixQuery class."""

    def test_prefix_query_returns_dict(self, tiny_db_path):
        """Test that prefix query returns a dict."""
        import pyrustkmer

        query = pyrustkmer.PyPrefixQuery(tiny_db_path)

        result = query.query_prefix("AAA")

        # Result is a dict, not an object with attributes
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_prefix_query_single_char(self, tiny_db_path):
        """Test querying single character prefix."""
        import pyrustkmer

        query = pyrustkmer.PyPrefixQuery(tiny_db_path)

        result = query.query_prefix("A")

        assert isinstance(result, dict)
        assert len(result) > 0

    def test_prefix_query_nonexistent(self, tiny_db_path):
        """Test querying non-existent prefix."""
        import pyrustkmer

        query = pyrustkmer.PyPrefixQuery(tiny_db_path)

        # Use valid DNA characters for prefix
        result = query.query_prefix("TTT")

        assert isinstance(result, dict)
        # Result should be empty or have few matches


class TestPyCounter:
    """Test PyCounter class."""

    def test_create_counter(self):
        """Test creating a counter."""
        import pyrustkmer

        counter = pyrustkmer.PyCounter(21, True, 1000)

        assert counter is not None
        assert hasattr(counter, "get_stats")

    def test_get_stats(self):
        """Test getting counter stats."""
        import pyrustkmer

        counter = pyrustkmer.PyCounter(21, True, 1000)

        stats = counter.get_stats()

        assert stats is not None
        assert hasattr(stats, "unique_kmers")
        assert hasattr(stats, "total_kmers")


class TestLoadMode:
    """Test LoadMode enum."""

    def test_load_mode_values(self):
        """Test LoadMode enum values."""
        import pyrustkmer

        assert hasattr(pyrustkmer.LoadMode, "Preload")
        assert hasattr(pyrustkmer.LoadMode, "MemoryMapped")
        assert hasattr(pyrustkmer.LoadMode, "Lazy")

        # All should be different
        assert pyrustkmer.LoadMode.Preload != pyrustkmer.LoadMode.MemoryMapped
        assert pyrustkmer.LoadMode.MemoryMapped != pyrustkmer.LoadMode.Lazy


class TestModuleCompleteness:
    """Test that all expected classes exist."""

    def test_core_classes_available(self):
        """Test that all core classes are available."""
        import pyrustkmer

        assert hasattr(pyrustkmer, "PyDatabase")
        assert hasattr(pyrustkmer, "PyCounter")
        assert hasattr(pyrustkmer, "PyFuzzyQuery")
        assert hasattr(pyrustkmer, "PyPrefixQuery")
        assert hasattr(pyrustkmer, "PyQueryResult")
        assert hasattr(pyrustkmer, "PyDatabaseStats")
        assert hasattr(pyrustkmer, "LoadMode")
        assert hasattr(pyrustkmer, "RustKmerError")
