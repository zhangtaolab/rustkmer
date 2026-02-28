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

    def test_save_database_with_count_filter(self, tmp_path):
        """Test save_database with min_count and max_count filtering."""
        import pyrustkmer

        counter = pyrustkmer.PyCounter(7, canonical=False)

        # Add k-mers with different counts
        counter.add_sequence("AAAAAAA")  # count 1
        counter.add_sequence("AAAAAAA")  # count 2
        counter.add_sequence("AAAAAAA")  # count 3
        counter.add_sequence("CCCCCCC")  # count 1
        counter.add_sequence("CCCCCCC")  # count 2
        counter.add_sequence("GGGGGGG")  # count 1

        output_file = tmp_path / "filtered.rkdb"

        # Test with min_count filter (keep only k-mers with count >= 2)
        counter.save_database(str(output_file), min_count=2)

        db = pyrustkmer.PyDatabase(str(output_file), pyrustkmer.LoadMode.Preload)

        # AAA should have count 3, CCC should have count 2, GGG should not exist
        aaa_result = db.query("AAAAAAA")
        ccc_result = db.query("CCCCCCC")
        ggg_result = db.query("GGGGGGG")

        assert aaa_result.found is True
        assert aaa_result.count == 3
        assert ccc_result.found is True
        assert ccc_result.count == 2
        assert ggg_result.found is False  # Filtered out (count=1 < min_count=2)

    def test_save_database_with_max_count_filter(self, tmp_path):
        """Test save_database with max_count filter."""
        import pyrustkmer

        counter = pyrustkmer.PyCounter(7, canonical=False)

        # Add k-mers with different counts
        counter.add_sequence("AAAAAAA")  # count 1
        counter.add_sequence("AAAAAAA")  # count 2
        counter.add_sequence("AAAAAAA")  # count 3
        counter.add_sequence("CCCCCCC")  # count 1
        counter.add_sequence("CCCCCCC")  # count 2
        counter.add_sequence("GGGGGGG")  # count 1

        output_file = tmp_path / "max_filtered.rkdb"

        # Test with max_count filter (keep only k-mers with count <= 2)
        counter.save_database(str(output_file), max_count=2)

        db = pyrustkmer.PyDatabase(str(output_file), pyrustkmer.LoadMode.Preload)

        # AAA should not exist (count=3 > max_count=2)
        # CCC should have count 2, GGG should have count 1
        aaa_result = db.query("AAAAAAA")
        ccc_result = db.query("CCCCCCC")
        ggg_result = db.query("GGGGGGG")

        assert aaa_result.found is False  # Filtered out (count=3 > max_count=2)
        assert ccc_result.found is True
        assert ccc_result.count == 2
        assert ggg_result.found is True
        assert ggg_result.count == 1

    def test_save_database_with_min_max_count_filter(self, tmp_path):
        """Test save_database with both min_count and max_count filter."""
        import pyrustkmer

        counter = pyrustkmer.PyCounter(7, canonical=False)

        # Add k-mers with different counts: 1, 2, 3, 4, 5
        for _ in range(5):
            counter.add_sequence("AAAAAAA")
        for _ in range(3):
            counter.add_sequence("CCCCCCC")
        for _ in range(1):
            counter.add_sequence("GGGGGGG")

        output_file = tmp_path / "range_filtered.rkdb"

        # Test with range filter (keep only k-mers with 2 <= count <= 4)
        counter.save_database(str(output_file), min_count=2, max_count=4)

        db = pyrustkmer.PyDatabase(str(output_file), pyrustkmer.LoadMode.Preload)

        aaa_result = db.query("AAAAAAA")  # count=5, should be filtered out
        ccc_result = db.query("CCCCCCC")  # count=3, should be kept
        ggg_result = db.query("GGGGGGG")  # count=1, should be filtered out

        assert aaa_result.found is False  # count=5 > max_count=4
        assert ccc_result.found is True
        assert ccc_result.count == 3
        assert ggg_result.found is False  # count=1 < min_count=2

    def test_save_database_invalid_filter_raises_error(self, tmp_path):
        """Test that min_count > max_count raises ValueError."""
        import pyrustkmer

        counter = pyrustkmer.PyCounter(7, canonical=False)
        counter.add_sequence("AAAAAAA")

        output_file = tmp_path / "invalid.rkdb"

        with pytest.raises(ValueError, match="min_count cannot exceed max_count"):
            counter.save_database(str(output_file), min_count=10, max_count=5)


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
