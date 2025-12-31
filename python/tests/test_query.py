"""Tests for QueryResult class."""

import pytest
import json
from rustkmer.query import QueryResult


class TestQueryResult:
    """Test QueryResult class methods."""

    def test_query_result_is_present_true(self):
        """Test is_present property when count > 0."""
        result = QueryResult(kmer="ATCGATCG", count=5, canonical="ATCGATCG")
        assert result.is_present is True

    def test_query_result_is_present_false(self):
        """Test is_present property when count = 0."""
        result = QueryResult(kmer="ATCGATCG", count=0, canonical="ATCGATCG")
        assert result.is_present is False

    def test_query_result_to_dict(self):
        """Test dictionary conversion."""
        result = QueryResult(kmer="ATCGATCG", count=5, canonical="ATCGATCG")
        expected = {
            "kmer": "ATCGATCG",
            "count": 5,
            "canonical": "ATCGATCG"
        }
        assert result.to_dict() == expected

    def test_query_result_to_json(self):
        """Test JSON serialization."""
        result = QueryResult(kmer="ATCGATCG", count=5, canonical="ATCGATCG")
        json_str = result.to_json()
        parsed = json.loads(json_str)
        expected = {
            "kmer": "ATCGATCG",
            "count": 5,
            "canonical": "ATCGATCG"
        }
        assert parsed == expected

    def test_query_result_from_dict_with_defaults(self):
        """Test creation from dict with missing fields."""
        data = {"kmer": "ATCGATCG", "count": 5}
        result = QueryResult.from_dict(data)

        # Missing canonical defaults to kmer value
        assert result.kmer == "ATCGATCG"
        assert result.count == 5
        assert result.canonical == "ATCGATCG"  # Defaults to kmer when not provided

    def test_query_result_from_dict_complete(self):
        """Test creation from dict with all fields."""
        data = {"kmer": "ATCGATCG", "count": 5, "canonical": "ATCGATCG"}
        result = QueryResult.from_dict(data)

        assert result.kmer == "ATCGATCG"
        assert result.count == 5
        assert result.canonical == "ATCGATCG"

    def test_query_result_str_representation(self):
        """Test string representation."""
        result = QueryResult(kmer="ATCGATCG", count=5, canonical="ATCGATCG")
        str_repr = str(result)

        # String representation is "kmer: count"
        assert str_repr == "ATCGATCG: 5"
        assert "ATCGATCG" in str_repr
        assert "5" in str_repr

    def test_query_result_repr(self):
        """Test repr representation."""
        result = QueryResult(kmer="ATCGATCG", count=5, canonical="ATCGATCG")
        repr_str = repr(result)

        assert "QueryResult" in repr_str
        assert "ATCGATCG" in repr_str
        assert "count=5" in repr_str

    def test_query_result_equality(self):
        """Test QueryResult equality comparison."""
        result1 = QueryResult(kmer="ATCGATCG", count=5, canonical="ATCGATCG")
        result2 = QueryResult(kmer="ATCGATCG", count=5, canonical="ATCGATCG")
        result3 = QueryResult(kmer="ATCGATCG", count=3, canonical="ATCGATCG")

        assert result1 == result2
        assert result1 != result3

    def test_query_result_with_none_canonical(self):
        """Test QueryResult with None canonical."""
        result = QueryResult(kmer="ATCGATCG", count=0, canonical=None)

        assert result.canonical is None
        assert result.is_present is False
        assert result.to_dict()["canonical"] is None