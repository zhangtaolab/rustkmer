"""Simple PyO3 tests that work with the actual API."""

import pytest


class TestPyO3BasicFunctionality:
    """Test basic PyO3 functionality with correct API signatures."""

    def test_database_query_works(self, PyDatabase, LoadMode, tiny_db_path):
        """Test that database queries work correctly."""
        db = PyDatabase(tiny_db_path, LoadMode.Preload)

        # Query a k-mer
        result = db.query("AAAAAAA")

        # Should have count and found attributes
        assert hasattr(result, "count")
        assert hasattr(result, "found")
        assert isinstance(result.count, int)
        assert isinstance(result.found, bool)

    def test_database_stats_work(self, PyDatabase, LoadMode, tiny_db_path):
        """Test that database stats work."""
        db = PyDatabase(tiny_db_path, LoadMode.Preload)

        stats = db.get_stats()

        # Should have expected attributes
        assert hasattr(stats, "kmer_size")
        assert hasattr(stats, "total_kmers")
        assert hasattr(stats, "unique_kmers")

        assert stats.kmer_size > 0
        assert stats.total_kmers >= 0
        assert stats.unique_kmers >= 0

    def test_fuzzy_query_with_database(self, PyDatabase, LoadMode, tiny_db_path):
        """Test fuzzy query using PyDatabase object."""
        db = PyDatabase(tiny_db_path, LoadMode.Preload)

        # PyFuzzyQuery takes a PyDatabase object
        import pyrustkmer

        query = pyrustkmer.PyFuzzyQuery(db)

        # Test fuzzy query
        result = query.fuzzy_query("ANNNNNN", max_mutations=1)

        assert result is not None
        assert hasattr(result, "total_matches")
        assert isinstance(result.total_matches, int)

    def test_prefix_query_with_database(self, PyDatabase, LoadMode, tiny_db_path):
        """Test prefix query using database path."""
        # PyPrefixQuery takes a string path
        import pyrustkmer

        query = pyrustkmer.PyPrefixQuery(tiny_db_path)

        # Test prefix query - result is a dict
        result = query.query_prefix("AAA")

        assert result is not None
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_all_load_modes_work(self, PyDatabase, LoadMode, tiny_db_path):
        """Test that all load modes work."""
        modes = [LoadMode.Preload, LoadMode.MemoryMapped, LoadMode.Lazy]

        for mode in modes:
            db = PyDatabase(tiny_db_path, mode)
            result = db.query("AAAAAAA")

            assert result is not None
            assert hasattr(result, "count")

    def test_kmer_counter_exists(self, PyCounter):
        """Test that PyCounter can be used."""
        # PyCounter uses positional arguments: k, canonical, _initial_capacity
        counter = PyCounter(21, True, 1000)
        assert counter is not None

        # Get stats
        stats = counter.get_stats()
        assert stats is not None


class TestPyO3EdgeCases:
    """Test edge cases."""

    def test_query_with_wrong_length_kmer(self, PyDatabase, LoadMode, tiny_db_path):
        """Test that wrong length k-mers raise an error."""
        db = PyDatabase(tiny_db_path, LoadMode.Preload)

        with pytest.raises(Exception):
            db.query("ACGTA")  # Wrong length for k=7 database

    def test_nonexistent_database(self, PyDatabase, LoadMode):
        """Test that nonexistent database raises an error."""
        with pytest.raises(Exception):
            PyDatabase("/nonexistent/path.rkdb", LoadMode.Preload)


class TestPyO3ModuleCompleteness:
    """Test that all expected classes and methods exist."""

    def test_core_classes_available(self, pyo3_module):
        """Test that all core classes are available."""
        m = pyo3_module

        assert hasattr(m, "PyDatabase")
        assert hasattr(m, "PyCounter")
        assert hasattr(m, "PyFuzzyQuery")
        assert hasattr(m, "PyPrefixQuery")
        assert hasattr(m, "PyQueryResult")
        assert hasattr(m, "PyDatabaseStats")
        assert hasattr(m, "LoadMode")

    def test_load_mode_values(self, pyo3_module):
        """Test LoadMode enum values."""
        mode = pyo3_module.LoadMode

        assert hasattr(mode, "Preload")
        assert hasattr(mode, "MemoryMapped")
        assert hasattr(mode, "Lazy")

        # All should be different
        assert mode.Preload != mode.MemoryMapped
        assert mode.MemoryMapped != mode.Lazy
