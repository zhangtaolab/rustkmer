"""Tests for PyKmerCounter class functionality."""

import pytest


class TestKmerCounterInitialization:
    """Test PyKmerCounter initialization."""
    
    def test_create_counter_with_k_size(self, PyKmerCounter):
        """Test creating counter with specific k-mer size."""
        counter = PyKmerCounter(k=21)
        assert counter is not None
    
    def test_create_counter_with_different_k_sizes(self, PyKmerCounter):
        """Test creating counters with various k-mer sizes."""
        for k_size in [7, 15, 21, 31]:
            counter = PyKmerCounter(k=k_size)
            assert counter is not None
    
    def test_create_counter_with_canonical_flag(self, PyKmerCounter):
        """Test creating counter with canonical flag."""
        counter = PyKmerCounter(k=21, canonical=True)
        assert counter is not None
        
        counter2 = PyKmerCounter(k=21, canonical=False)
        assert counter2 is not None


class TestKmerCounterBasicOperations:
    """Test basic k-mer counting operations."""
    
    def test_add_single_sequence(self, PyKmerCounter):
        """Test adding a single DNA sequence."""
        counter = PyKmerCounter(k=7)
        
        counter.add_sequence("ATCGATCGATCG")
        
        # Should not raise an error
        assert counter is not None
    
    def test_add_multiple_sequences(self, PyKmerCounter):
        """Test adding multiple sequences."""
        counter = PyKmerCounter(k=7)
        
        sequences = [
            "ATCGATCG",
            "GGGGGGGG",
            "ACGTACGT",
        ]
        
        for seq in sequences:
            counter.add_sequence(seq)
        
        assert counter is not None
    
    def test_add_empty_sequence(self, PyKmerCounter):
        """Test adding empty sequence."""
        counter = PyKmerCounter(k=7)
        
        counter.add_sequence("")
        
        # Should not raise an error
        assert counter is not None
    
    def test_add_short_sequence(self, PyKmerCounter):
        """Test adding sequence shorter than k-mer size."""
        counter = PyKmerCounter(k=7)
        
        # Sequence shorter than k=7 should be handled
        counter.add_sequence("ATCG")
        
        assert counter is not None


class TestKmerCounterStats:
    """Test k-mer counter statistics."""
    
    def test_get_stats(self, PyKmerCounter):
        """Test getting counter statistics."""
        counter = PyKmerCounter(k=7)
        counter.add_sequence("ATCGATCGATCG")
        
        stats = counter.get_stats()
        
        assert stats is not None
        assert hasattr(stats, 'unique_kmers')
        assert hasattr(stats, 'total_kmers')
        
        assert isinstance(stats.unique_kmers, int)
        assert isinstance(stats.total_kmers, int)
    
    def test_stats_after_adding_sequences(self, PyKmerCounter):
        """Test that stats update after adding sequences."""
        counter = PyKmerCounter(k=7)
        
        stats_before = counter.get_stats()
        
        counter.add_sequence("ATCGATCGATCG")
        
        stats_after = counter.get_stats()
        
        # Stats should be accessible
        assert stats_after.unique_kmers >= stats_before.unique_kmers


class TestKmerCounterEdgeCases:
    """Test edge cases for k-mer counter."""
    
    def test_counter_with_large_k_size(self, PyKmerCounter):
        """Test counter with large k-mer size."""
        counter = PyKmerCounter(k=31)
        assert counter is not None
        
        counter.add_sequence("A" * 50)  # Add sequence longer than k
        
        stats = counter.get_stats()
        assert stats is not None
    
    def test_counter_with_very_large_k(self, PyKmerCounter):
        """Test counter with very large k-mer size (k=64)."""
        counter = PyKmerCounter(k=64)
        assert counter is not None
        
        counter.add_sequence("A" * 100)
        
        stats = counter.get_stats()
        assert stats is not None
