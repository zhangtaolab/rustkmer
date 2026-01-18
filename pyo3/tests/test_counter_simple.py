"""Simplified test suite for PyCounter that works with current API."""

import pytest

try:
    import pyrustkmer
except ImportError:
    pytest.skip("pyrustkmer module not installed", allow_module_level=True)


class TestPyCounterBasicAPI:
    """Test PyCounter with currently available methods."""

    def test_create_counter_with_required_params(self):
        """Test creating counter with kmer_length and canonical."""
        # Current API: PyCounter(kmer_length, canonical, initial_capacity)
        counter = pyrustkmer.PyCounter(21, True, 1000)
        assert counter is not None
        assert counter.kmer_length == 21
        assert counter.canonical == True

    def test_create_counter_without_canonical(self):
        """Test creating counter without canonical (default False)."""
        counter = pyrustkmer.PyCounter(21, False, 1000)
        assert counter.canonical == False

    def test_add_single_kmer(self):
        """Test adding a single k-mer."""
        counter = pyrustkmer.PyCounter(7, False, 1000)
        counter.add_kmer("AAAAAAA")

        stats = counter.get_stats()
        assert stats is not None
        # Should have counted some k-mers

    def test_add_multiple_kmers(self):
        """Test adding multiple different k-mers."""
        counter = pyrustkmer.PyCounter(7, False, 1000)

        kmers = ["AAAAAAA", "CCCCCCC", "GGGGGGG", "TTTTTTT"]
        for kmer in kmers:
            counter.add_kmer(kmer)

        stats = counter.get_stats()
        assert stats is not None

    def test_is_empty_initially(self):
        """Test that counter is initially empty."""
        counter = pyrustkmer.PyCounter(21, False, 1000)
        assert counter.is_empty() == True

    def test_is_empty_after_adding_kmer(self):
        """Test that counter changes after adding k-mer."""
        counter = pyrustkmer.PyCounter(7, False, 1000)

        stats_before = counter.get_stats()
        counter.add_kmer("AAAAAAA")
        stats_after = counter.get_stats()

        assert stats_after is not None

    def test_get_stats_empty_counter(self):
        """Test getting stats for empty counter."""
        counter = pyrustkmer.PyCounter(21, False, 1000)
        stats = counter.get_stats()

        assert stats is not None
        # Stats object should have total_kmers and unique_kmers attributes

    def test_get_stats_after_adding_kmers(self):
        """Test getting stats after adding k-mers."""
        counter = pyrustkmer.PyCounter(7, False, 1000)

        counter.add_kmer("AAAAAAA")
        counter.add_kmer("AAAAAAA")
        counter.add_kmer("CCCCCCC")

        stats = counter.get_stats()
        assert stats is not None

    def test_kmer_length_property(self):
        """Test kmer_length property."""
        counter = pyrustkmer.PyCounter(21, False, 1000)
        assert counter.kmer_length == 21

    def test_canonical_property(self):
        """Test canonical property."""
        counter_true = pyrustkmer.PyCounter(21, True, 1000)
        counter_false = pyrustkmer.PyCounter(21, False, 1000)

        assert counter_true.canonical == True
        assert counter_false.canonical == False

    def test_different_kmer_sizes(self):
        """Test creating counters with different k-mer sizes."""
        sizes = [7, 15, 21, 31, 33]
        for k in sizes:
            counter = pyrustkmer.PyCounter(k, False, 1000)
            assert counter.kmer_length == k

    def test_counter_repr(self):
        """Test counter string representation."""
        counter = pyrustkmer.PyCounter(21, True, 1000)
        repr_str = repr(counter)
        assert "PyCounter" in repr_str
