"""Tests for DatabaseStats class."""

import pytest
import json
from rustkmer.stats import DatabaseStats


class TestDatabaseStats:
    """Test DatabaseStats class methods."""

    def test_database_stats_to_dict(self):
        """Test dictionary conversion."""
        stats = DatabaseStats(
            kmer_size=7,
            unique_kmers=1000,
            total_counts=2500,
            min_count=1,
            max_count=10,
            file_size=102400,
            format_version="1.0"
        )

        expected = {
            "kmer_size": 7,
            "unique_kmers": 1000,
            "total_counts": 2500,
            "min_count": 1,
            "max_count": 10,
            "file_size": 102400,
            "format_version": "1.0"
        }
        assert stats.to_dict() == expected

    def test_database_stats_to_json(self):
        """Test JSON serialization."""
        stats = DatabaseStats(
            kmer_size=7,
            unique_kmers=1000,
            total_counts=2500,
            min_count=1,
            max_count=10,
            file_size=102400,
            format_version="1.0"
        )

        json_str = stats.to_json()
        parsed = json.loads(json_str)

        expected = {
            "kmer_size": 7,
            "unique_kmers": 1000,
            "total_counts": 2500,
            "min_count": 1,
            "max_count": 10,
            "file_size": 102400,
            "format_version": "1.0"
        }
        assert parsed == expected

    def test_database_stats_from_dict_with_defaults(self):
        """Test creation from dict with missing fields."""
        data = {
            "kmer_size": 7,
            "unique_kmers": 1000,
            "total_counts": 2500,
            "max_count": 10,
            "file_size": 102400,
            "format_version": "1.0"
            # Missing min_count
        }
        stats = DatabaseStats.from_dict(data)

        assert stats.kmer_size == 7
        assert stats.unique_kmers == 1000
        assert stats.total_counts == 2500
        assert stats.min_count == 0  # Default value
        assert stats.max_count == 10
        assert stats.file_size == 102400
        assert stats.format_version == "1.0"

    def test_database_stats_from_dict_complete(self):
        """Test creation from dict with all fields."""
        data = {
            "kmer_size": 7,
            "unique_kmers": 1000,
            "total_counts": 2500,
            "min_count": 1,
            "max_count": 10,
            "file_size": 102400,
            "format_version": "1.0"
        }
        stats = DatabaseStats.from_dict(data)

        assert stats.kmer_size == 7
        assert stats.unique_kmers == 1000
        assert stats.total_counts == 2500
        assert stats.min_count == 1
        assert stats.max_count == 10
        assert stats.file_size == 102400
        assert stats.format_version == "1.0"

    def test_database_stats_average_count_zero_division(self):
        """Test average_count when unique_kmers is 0."""
        stats = DatabaseStats(
            kmer_size=7,
            unique_kmers=0,  # Zero unique k-mers
            total_counts=0,
            min_count=0,
            max_count=0,
            file_size=102400,
            format_version="1.0"
        )

        # Should handle zero division gracefully
        assert stats.average_count == 0

    def test_database_stats_average_count_normal(self):
        """Test average_count with normal values."""
        stats = DatabaseStats(
            kmer_size=7,
            unique_kmers=1000,
            total_counts=2500,
            min_count=1,
            max_count=10,
            file_size=102400,
            format_version="1.0"
        )

        # Average = total_counts / unique_kmers = 2500 / 1000 = 2.5
        assert stats.average_count == 2.5

    def test_database_stats_str_representation(self):
        """Test string representation."""
        stats = DatabaseStats(
            kmer_size=7,
            unique_kmers=1000,
            total_counts=2500,
            min_count=1,
            max_count=10,
            file_size=102400,
            format_version="1.0"
        )

        str_repr = str(stats)

        # String representation is "DatabaseStats(k=X, unique=Y, total=Z)"
        assert str_repr == "DatabaseStats(k=7, unique=1000, total=2500)"
        assert "DatabaseStats" in str_repr
        assert "k=7" in str_repr
        assert "unique=1000" in str_repr
        assert "total=2500" in str_repr

    def test_database_stats_repr(self):
        """Test repr representation."""
        stats = DatabaseStats(
            kmer_size=7,
            unique_kmers=1000,
            total_counts=2500,
            min_count=1,
            max_count=10,
            file_size=102400,
            format_version="1.0"
        )

        repr_str = repr(stats)

        assert "DatabaseStats" in repr_str
        assert "kmer_size=7" in repr_str
        assert "unique_kmers=1000" in repr_str

    def test_database_stats_equality(self):
        """Test DatabaseStats equality comparison."""
        stats1 = DatabaseStats(
            kmer_size=7,
            unique_kmers=1000,
            total_counts=2500,
            min_count=1,
            max_count=10,
            file_size=102400,
            format_version="1.0"
        )

        stats2 = DatabaseStats(
            kmer_size=7,
            unique_kmers=1000,
            total_counts=2500,
            min_count=1,
            max_count=10,
            file_size=102400,
            format_version="1.0"
        )

        stats3 = DatabaseStats(
            kmer_size=33,
            unique_kmers=1000,
            total_counts=2500,
            min_count=1,
            max_count=10,
            file_size=102400,
            format_version="1.0"
        )

        assert stats1 == stats2
        assert stats1 != stats3

    def test_database_stats_property_access(self):
        """Test property access patterns."""
        stats = DatabaseStats(
            kmer_size=7,
            unique_kmers=1000,
            total_counts=2500,
            min_count=1,
            max_count=10,
            file_size=102400,
            format_version="1.0"
        )

        # All properties should be accessible
        assert isinstance(stats.kmer_size, int)
        assert isinstance(stats.unique_kmers, int)
        assert isinstance(stats.total_counts, int)
        assert isinstance(stats.min_count, int)
        assert isinstance(stats.max_count, int)
        assert isinstance(stats.file_size, int)
        assert isinstance(stats.format_version, str)
        assert isinstance(stats.average_count, float)