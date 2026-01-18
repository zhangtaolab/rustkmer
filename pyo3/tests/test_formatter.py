"""
Comprehensive test suite for PyO3 formatter methods.

Tests all formatting output methods for PyQueryResult, PyPrefixQueryResult,
PyFuzzyResult, and PyDatabaseStats.
"""

import json
import csv
import io
import pytest
from typing import Dict, Any, List

try:
    import pyrustkmer
except ImportError:
    pytest.skip("pyrustkmer module not installed", allow_module_level=True)


# ============================================================================
# PyQueryResult Formatting Tests
# ============================================================================


class TestPyQueryResultFormatting:
    """Test PyQueryResult formatting methods."""

    def test_to_json_structure(self, tiny_db_path):
        """Test that to_json() returns valid JSON with correct structure."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query("AAAAAAA")

        json_str = result.to_json()
        assert isinstance(json_str, str)

        # Verify it's valid JSON
        data = json.loads(json_str)
        assert "kmer" in data
        assert "count" in data
        assert "found" in data
        assert isinstance(data["kmer"], str)
        assert isinstance(data["count"], int)
        assert isinstance(data["found"], bool)

    def test_to_json_values_match_result(self, tiny_db_path):
        """Test that JSON values match the result object attributes."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query("AAAAAAA")

        json_str = result.to_json()
        data = json.loads(json_str)

        assert data["kmer"] == result.kmer
        assert data["count"] == result.count
        assert data["found"] == result.found

    def test_to_csv_has_header(self, tiny_db_path):
        """Test that to_csv() includes proper header."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query("AAAAAAA")

        csv_str = result.to_csv()
        lines = csv_str.strip().split("\n")

        assert len(lines) >= 2  # At least header and one data row
        header = lines[0]
        assert header == "kmer,count,found"

    def test_to_csv_parseable(self, tiny_db_path):
        """Test that CSV output is parseable by Python's csv module."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query("AAAAAAA")

        csv_str = result.to_csv()
        reader = csv.DictReader(io.StringIO(csv_str))

        rows = list(reader)
        assert len(rows) == 1  # One data row
        assert rows[0]["kmer"] == result.kmer
        assert rows[0]["count"] == str(result.count)
        assert rows[0]["found"] == str(result.found).lower()

    def test_to_csv_values_match_result(self, tiny_db_path):
        """Test that CSV values match the result object attributes."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query("AAAAAAA")

        csv_str = result.to_csv()
        lines = csv_str.strip().split("\n")
        data_line = lines[1]  # Skip header

        values = data_line.split(",")
        assert values[0] == result.kmer
        assert values[1] == str(result.count)
        assert values[2] == str(result.found).lower()

    def test_to_tsv_has_header(self, tiny_db_path):
        """Test that to_tsv() includes proper header with tabs."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query("AAAAAAA")

        tsv_str = result.to_tsv()
        lines = tsv_str.strip().split("\n")

        assert len(lines) >= 2  # At least header and one data row
        header = lines[0]
        assert header == "kmer\tcount\tfound"

    def test_to_tsv_parseable(self, tiny_db_path):
        """Test that TSV output is parseable."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query("AAAAAAA")

        tsv_str = result.to_tsv()
        reader = csv.DictReader(io.StringIO(tsv_str), delimiter="\t")

        rows = list(reader)
        assert len(rows) == 1  # One data row
        assert rows[0]["kmer"] == result.kmer
        assert rows[0]["count"] == str(result.count)
        assert rows[0]["found"] == str(result.found).lower()

    def test_to_dict_conversion(self, tiny_db_path):
        """Test to_dict() returns Python dict with correct values."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query("AAAAAAA")

        data = result.to_dict()

        assert isinstance(data, dict)
        assert data["kmer"] == result.kmer
        assert data["count"] == result.count
        assert data["found"] == result.found

    def test_to_dict_matches_json(self, tiny_db_path):
        """Test that to_dict() produces same data as to_json()."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query("AAAAAAA")

        json_str = result.to_json()
        json_data = json.loads(json_str)
        dict_data = result.to_dict()

        assert json_data == dict_data

    def test_format_consistency_across_methods(self, tiny_db_path):
        """Test that all formats contain the same data."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query("AAAAAAA")

        # Extract data from all formats
        json_data = json.loads(result.to_json())
        csv_reader = csv.DictReader(io.StringIO(result.to_csv()))
        csv_data = list(csv_reader)[0]
        tsv_reader = csv.DictReader(io.StringIO(result.to_tsv()), delimiter="\t")
        tsv_data = list(tsv_reader)[0]
        dict_data = result.to_dict()

        # Convert all to same format for comparison
        assert (
            json_data["kmer"]
            == csv_data["kmer"]
            == tsv_data["kmer"]
            == dict_data["kmer"]
        )
        assert (
            json_data["count"]
            == int(csv_data["count"])
            == int(tsv_data["count"])
            == dict_data["count"]
        )
        assert (
            json_data["found"]
            == (csv_data["found"] == "True")
            == (tsv_data["found"] == "True")
            == dict_data["found"]
        )


# ============================================================================
# PyPrefixQueryResult Formatting Tests
# ============================================================================


class TestPyPrefixQueryResultFormatting:
    """Test PyPrefixQueryResult formatting methods."""

    def test_to_json_structure(self, tiny_db_path):
        """Test that to_json() returns valid JSON with correct structure."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query_prefix("A")

        json_str = result.to_json()
        assert isinstance(json_str, str)

        data = json.loads(json_str)
        assert "matches" in data
        assert "total_matches" in data
        assert "start_index" in data
        assert "end_index" in data
        assert "block_size" in data
        assert "is_sorted" in data
        assert "query_time_ms" in data

    def test_to_json_metadata_fields(self, tiny_db_path):
        """Test that JSON includes all metadata fields."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query_prefix("A")

        json_str = result.to_json()
        data = json.loads(json_str)

        assert isinstance(data["matches"], list)
        assert isinstance(data["total_matches"], int)
        assert isinstance(data["start_index"], int)
        assert isinstance(data["end_index"], int)
        assert isinstance(data["block_size"], int)
        assert isinstance(data["is_sorted"], bool)
        assert isinstance(data["query_time_ms"], int)

    def test_to_csv_has_header(self, tiny_db_path):
        """Test that to_csv() includes proper header."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query_prefix("A")

        csv_str = result.to_csv()
        lines = csv_str.strip().split("\n")

        assert len(lines) >= 2
        header = lines[0]
        assert header == "kmer,count"

    def test_to_csv_has_metadata_comments(self, tiny_db_path):
        """Test that CSV includes metadata as comments."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query_prefix("A")

        csv_str = result.to_csv()
        lines = csv_str.strip().split("\n")

        # Check for metadata comments
        comment_lines = [l for l in lines if l.startswith("#")]
        assert len(comment_lines) > 0

        # Verify specific metadata fields
        metadata_text = "\n".join(comment_lines)
        assert "# total_matches=" in metadata_text
        assert "# query_time_ms=" in metadata_text
        assert "# start_index=" in metadata_text
        assert "# end_index=" in metadata_text
        assert "# block_size=" in metadata_text
        assert "# is_sorted=" in metadata_text

    def test_to_csv_parseable(self, tiny_db_path):
        """Test that CSV output is parseable by Python's csv module."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query_prefix("A")

        csv_str = result.to_csv()

        # Parse only data rows (skip comments)
        reader = csv.DictReader(io.StringIO(csv_str), skipinitialspace=False)

        rows = [row for row in reader if not row["kmer"].startswith("#")]
        assert len(rows) > 0

    def test_to_csv_matches_result_dict(self, tiny_db_path):
        """Test that CSV matches the result.matches dictionary."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query_prefix("A")

        csv_str = result.to_csv()
        csv_reader = csv.DictReader(io.StringIO(csv_str))
        csv_rows = list(csv_reader)

        # Filter out comment rows
        csv_data = {
            row["kmer"]: row["count"]
            for row in csv_rows
            if row["kmer"] and not row["kmer"].startswith("#")
        }

        # Compare with result.matches
        for kmer, count in result.matches.items():
            assert kmer in csv_data
            assert csv_data[kmer] == count

    def test_to_tsv_has_header(self, tiny_db_path):
        """Test that to_tsv() includes proper header with tabs."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query_prefix("A")

        tsv_str = result.to_tsv()
        lines = tsv_str.strip().split("\n")

        assert len(lines) >= 2
        header = lines[0]
        assert header == "kmer\tcount"

    def test_to_tsv_has_metadata_comments(self, tiny_db_path):
        """Test that TSV includes metadata as comments."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query_prefix("A")

        tsv_str = result.to_tsv()
        lines = tsv_str.strip().split("\n")

        comment_lines = [l for l in lines if l.startswith("#")]
        assert len(comment_lines) > 0

        metadata_text = "\n".join(comment_lines)
        assert "# total_matches=" in metadata_text
        assert "# query_time_ms=" in metadata_text

    def test_to_table_structure(self, tiny_db_path):
        """Test that to_table() has proper ASCII table structure."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query_prefix("A")

        table_str = result.to_table()
        lines = table_str.strip().split("\n")

        # Check for table borders
        assert any(line.startswith("+") and line.endswith("+") for line in lines)
        assert any(line.startswith("|") and line.endswith("|") for line in lines)

    def test_to_table_has_header(self, tiny_db_path):
        """Test that to_table() includes column headers."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query_prefix("A")

        table_str = result.to_table()
        lines = table_str.split("\n")

        # Find header line
        header_lines = [l for l in lines if "kmer" in l.lower() and "|" in l]
        assert len(header_lines) > 0

    def test_to_table_has_metadata(self, tiny_db_path):
        """Test that to_table() includes metadata section."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query_prefix("A")

        table_str = result.to_table()

        # Check for metadata in table
        assert "Total matches:" in table_str
        assert "Query time:" in table_str
        assert "Memory block:" in table_str
        assert "Sorted:" in table_str

    def test_to_table_values_match_result(self, tiny_db_path):
        """Test that table values match the result object."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query_prefix("A")

        table_str = result.to_table()

        # Check for total_matches
        assert str(result.total_matches) in table_str
        assert f"{result.query_time_ms}ms" in table_str

    def test_format_consistency(self, tiny_db_path):
        """Test that all formats contain the same k-mer data."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query_prefix("A")

        json_data = json.loads(result.to_json())
        csv_reader = csv.DictReader(io.StringIO(result.to_csv()))
        csv_rows = list(csv_reader)
        tsv_reader = csv.DictReader(io.StringIO(result.to_tsv()), delimiter="\t")
        tsv_rows = list(tsv_reader)

        # Get k-mers from each format (skip comments)
        json_kmers = {m[0] for m in json_data["matches"]}
        csv_kmers = {
            r["kmer"] for r in csv_rows if r["kmer"] and not r["kmer"].startswith("#")
        }
        tsv_kmers = {
            r["kmer"] for r in tsv_rows if r["kmer"] and not r["kmer"].startswith("#")
        }
        dict_kmers = set(result.matches.keys())

        assert json_kmers == csv_kmers == tsv_kmers == dict_kmers


# ============================================================================
# PyFuzzyResult Formatting Tests
# ============================================================================


class TestPyFuzzyResultFormatting:
    """Test PyFuzzyResult formatting methods."""

    def test_to_json_structure(self, tiny_db_path):
        """Test that to_json() returns valid JSON with correct structure."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        fuzzy_query = pyrustkmer.PyFuzzyQuery(db)
        result = fuzzy_query.query_fuzzy("ANNNNNN", max_mutations=1)

        json_str = result.to_json()
        assert isinstance(json_str, str)

        data = json.loads(json_str)
        assert "query_kmer" in data
        assert "exact_match" in data
        assert "matches" in data
        assert "total_matches" in data
        assert "mutation_tolerance" in data
        assert "query_time_ms" in data
        assert "has_position_mutations" in data

    def test_to_json_matches_fields(self, tiny_db_path):
        """Test that JSON matches all result fields."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        fuzzy_query = pyrustkmer.PyFuzzyQuery(db)
        result = fuzzy_query.query_fuzzy("ANNNNNN", max_mutations=1)

        json_str = result.to_json()
        data = json.loads(json_str)

        assert data["query_kmer"] == result.query_kmer
        assert data["total_matches"] == result.total_matches
        assert data["mutation_tolerance"] == result.mutation_tolerance
        assert data["query_time_ms"] == result.query_time_ms
        assert data["has_position_mutations"] == result.has_position_mutations

    def test_to_csv_has_header(self, tiny_db_path):
        """Test that to_csv() includes proper header."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        fuzzy_query = pyrustkmer.PyFuzzyQuery(db)
        result = fuzzy_query.query_fuzzy("ANNNNNN", max_mutations=1)

        csv_str = result.to_csv()
        lines = csv_str.strip().split("\n")

        assert len(lines) >= 2
        header = lines[0]
        expected_fields = [
            "kmer",
            "count",
            "distance",
            "match_type",
            "mutation_positions",
        ]
        for field in expected_fields:
            assert field in header

    def test_to_csv_has_metadata_comments(self, tiny_db_path):
        """Test that CSV includes metadata as comments."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        fuzzy_query = pyrustkmer.PyFuzzyQuery(db)
        result = fuzzy_query.query_fuzzy("ANNNNNN", max_mutations=1)

        csv_str = result.to_csv()
        lines = csv_str.strip().split("\n")

        comment_lines = [l for l in lines if l.startswith("#")]
        assert len(comment_lines) > 0

        metadata_text = "\n".join(comment_lines)
        assert "# query_kmer=" in metadata_text
        assert "# total_matches=" in metadata_text
        assert "# mutation_tolerance=" in metadata_text
        assert "# query_time_ms=" in metadata_text
        assert "# has_position_mutations=" in metadata_text

    def test_to_csv_exact_match_priority(self, tiny_db_path):
        """Test that exact matches appear first in CSV."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        fuzzy_query = pyrustkmer.PyFuzzyQuery(db)
        result = fuzzy_query.query_fuzzy("ANNNNNN", max_mutations=1)

        csv_str = result.to_csv()
        lines = csv_str.strip().split("\n")

        # Skip header and get data rows (not comments)
        data_rows = [l for l in lines[1:] if l and not l.startswith("#")]

        if len(data_rows) > 1 and result.exact_match:
            # First data row should be exact match
            first_row = data_rows[0]
            assert "exact" in first_row

    def test_to_tsv_has_header(self, tiny_db_path):
        """Test that to_tsv() includes proper header with tabs."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        fuzzy_query = pyrustkmer.PyFuzzyQuery(db)
        result = fuzzy_query.query_fuzzy("ANNNNNN", max_mutations=1)

        tsv_str = result.to_tsv()
        lines = tsv_str.strip().split("\n")

        assert len(lines) >= 2
        header = lines[0]
        expected_fields = [
            "kmer",
            "count",
            "distance",
            "match_type",
            "mutation_positions",
        ]
        for field in expected_fields:
            assert field in header

    def test_to_tsv_has_metadata_comments(self, tiny_db_path):
        """Test that TSV includes metadata as comments."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        fuzzy_query = pyrustkmer.PyFuzzyQuery(db)
        result = fuzzy_query.query_fuzzy("ANNNNNN", max_mutations=1)

        tsv_str = result.to_tsv()
        lines = tsv_str.strip().split("\n")

        comment_lines = [l for l in lines if l.startswith("#")]
        assert len(comment_lines) > 0

        metadata_text = "\n".join(comment_lines)
        assert "# query_kmer=" in metadata_text
        assert "# total_matches=" in metadata_text

    def test_format_consistency(self, tiny_db_path):
        """Test that all formats contain the same match data."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        fuzzy_query = pyrustkmer.PyFuzzyQuery(db)
        result = fuzzy_query.query_fuzzy("ANNNNNN", max_mutations=1)

        json_data = json.loads(result.to_json())
        csv_reader = csv.DictReader(io.StringIO(result.to_csv()))
        csv_rows = list(csv_reader)
        tsv_reader = csv.DictReader(io.StringIO(result.to_tsv()), delimiter="\t")
        tsv_rows = list(tsv_reader)

        # Get matches from each format
        json_kmers = {m["kmer"] for m in json_data["matches"]}
        csv_kmers = {
            r["kmer"] for r in csv_rows if r["kmer"] and not r["kmer"].startswith("#")
        }
        tsv_kmers = {
            r["kmer"] for r in tsv_rows if r["kmer"] and not r["kmer"].startswith("#")
        }
        result_kmers = {m.kmer for m in result.matches}

        assert json_kmers == csv_kmers == tsv_kmers == result_kmers


# ============================================================================
# PyDatabaseStats Formatting Tests
# ============================================================================


class TestPyDatabaseStatsFormatting:
    """Test PyDatabaseStats formatting methods."""

    def test_to_json_structure(self, tiny_db_path):
        """Test that to_json() returns valid JSON with correct structure."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        stats = db.get_stats()

        json_str = stats.to_json()
        assert isinstance(json_str, str)

        data = json.loads(json_str)
        expected_fields = [
            "kmer_size",
            "total_kmers",
            "unique_kmers",
            "file_size",
            "is_sorted",
            "canonical",
        ]
        for field in expected_fields:
            assert field in data

    def test_to_json_values_match_stats(self, tiny_db_path):
        """Test that JSON values match the stats object attributes."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        stats = db.get_stats()

        json_str = stats.to_json()
        data = json.loads(json_str)

        assert data["kmer_size"] == stats.kmer_size
        assert data["total_kmers"] == stats.total_kmers
        assert data["unique_kmers"] == stats.unique_kmers
        assert data["file_size"] == stats.file_size
        assert data["is_sorted"] == stats.is_sorted
        assert data["canonical"] == stats.canonical

    def test_to_csv_has_header(self, tiny_db_path):
        """Test that to_csv() includes proper header."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        stats = db.get_stats()

        csv_str = stats.to_csv()
        lines = csv_str.strip().split("\n")

        assert len(lines) >= 2
        header = lines[0]
        assert header == "metric,value"

    def test_to_csv_parseable(self, tiny_db_path):
        """Test that CSV output is parseable by Python's csv module."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        stats = db.get_stats()

        csv_str = stats.to_csv()
        reader = csv.DictReader(io.StringIO(csv_str))

        rows = list(reader)
        assert len(rows) >= 6  # All 6 metrics

    def test_to_csv_contains_all_metrics(self, tiny_db_path):
        """Test that CSV contains all database statistics."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        stats = db.get_stats()

        csv_str = stats.to_csv()
        csv_reader = csv.DictReader(io.StringIO(csv_str))
        csv_data = {row["metric"]: row["value"] for row in csv_reader}

        expected_metrics = [
            "kmer_size",
            "total_kmers",
            "unique_kmers",
            "file_size",
            "is_sorted",
            "canonical",
        ]
        for metric in expected_metrics:
            assert metric in csv_data

    def test_to_csv_values_match_stats(self, tiny_db_path):
        """Test that CSV values match the stats object."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        stats = db.get_stats()

        csv_str = stats.to_csv()
        csv_reader = csv.DictReader(io.StringIO(csv_str))
        csv_data = {row["metric"]: row["value"] for row in csv_reader}

        assert csv_data["kmer_size"] == str(stats.kmer_size)
        assert csv_data["total_kmers"] == str(stats.total_kmers)
        assert csv_data["unique_kmers"] == str(stats.unique_kmers)
        assert csv_data["file_size"] == str(stats.file_size)
        assert csv_data["is_sorted"] == str(stats.is_sorted).lower()
        assert csv_data["canonical"] == str(stats.canonical).lower()

    def test_to_tsv_has_header(self, tiny_db_path):
        """Test that to_tsv() includes proper header with tabs."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        stats = db.get_stats()

        tsv_str = stats.to_tsv()
        lines = tsv_str.strip().split("\n")

        assert len(lines) >= 2
        header = lines[0]
        assert header == "metric\tvalue"

    def test_to_tsv_parseable(self, tiny_db_path):
        """Test that TSV output is parseable."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        stats = db.get_stats()

        tsv_str = stats.to_tsv()
        reader = csv.DictReader(io.StringIO(tsv_str), delimiter="\t")

        rows = list(reader)
        assert len(rows) >= 6  # All 6 metrics

    def test_to_tsv_contains_all_metrics(self, tiny_db_path):
        """Test that TSV contains all database statistics."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        stats = db.get_stats()

        tsv_str = stats.to_tsv()
        tsv_reader = csv.DictReader(io.StringIO(tsv_str), delimiter="\t")
        tsv_data = {row["metric"]: row["value"] for row in tsv_reader}

        expected_metrics = [
            "kmer_size",
            "total_kmers",
            "unique_kmers",
            "file_size",
            "is_sorted",
            "canonical",
        ]
        for metric in expected_metrics:
            assert metric in tsv_data

    def test_format_consistency(self, tiny_db_path):
        """Test that all formats contain the same data."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        stats = db.get_stats()

        json_data = json.loads(stats.to_json())
        csv_reader = csv.DictReader(io.StringIO(stats.to_csv()))
        csv_data = {row["metric"]: row["value"] for row in csv_reader}
        tsv_reader = csv.DictReader(io.StringIO(stats.to_tsv()), delimiter="\t")
        tsv_data = {row["metric"]: row["value"] for row in tsv_reader}

        # Compare all formats
        for metric in [
            "kmer_size",
            "total_kmers",
            "unique_kmers",
            "file_size",
            "is_sorted",
            "canonical",
        ]:
            json_value = json_data[metric]
            csv_value = csv_data[metric]
            tsv_value = tsv_data[metric]

            # Convert boolean values
            if isinstance(json_value, bool):
                assert str(json_value).lower() == csv_value == tsv_value
            else:
                assert str(json_value) == csv_value == tsv_value


# ============================================================================
# Edge Cases and Boundary Tests
# ============================================================================


class TestFormatterEdgeCases:
    """Test formatter edge cases and special handling."""

    def test_empty_prefix_query_formatting(self, tiny_db_path):
        """Test formatting when prefix query returns no results."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        # Try a prefix that likely doesn't exist (valid but unlikely in database)
        result = db.query_prefix("AAAAA")

        # Should still be able to format empty results
        json_str = result.to_json()
        csv_str = result.to_csv()
        tsv_str = result.to_tsv()
        table_str = result.to_table()

        assert isinstance(json_str, str)
        assert isinstance(csv_str, str)
        assert isinstance(tsv_str, str)
        assert isinstance(table_str, str)

        # Verify JSON structure
        data = json.loads(json_str)
        assert data["matches"] == []

    def test_not_found_query_formatting(self, tiny_db_path):
        """Test formatting when k-mer is not found."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        # Query a k-mer that likely doesn't exist (valid but not in database)
        result = db.query("TTTTTTT")

        json_str = result.to_json()
        data = json.loads(json_str)

        assert data["found"] == False
        assert data["count"] == 0

    def test_single_match_formatting(self, tiny_db_path):
        """Test formatting with single match result."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query("AAAAAAA")

        # All formats should handle single match correctly
        json_str = result.to_json()
        csv_str = result.to_csv()
        tsv_str = result.to_tsv()

        assert isinstance(json_str, str)
        assert isinstance(csv_str, str)
        assert isinstance(tsv_str, str)

    def test_large_result_formatting(self, small_db_path):
        """Test formatting with larger result sets."""
        db = pyrustkmer.PyDatabase(small_db_path, pyrustkmer.LoadMode.Preload)
        result = db.query_prefix("A")

        # Should handle larger result sets
        json_str = result.to_json()
        csv_str = result.to_csv()
        tsv_str = result.to_tsv()

        assert isinstance(json_str, str)
        assert isinstance(csv_str, str)
        assert isinstance(tsv_str, str)

        # Verify JSON contains all matches
        data = json.loads(json_str)
        assert len(data["matches"]) > 0


# ============================================================================
# Format Standards Tests
# ============================================================================


class TestFormatStandards:
    """Test that output formats meet standards."""

    def test_json_is_valid(self, tiny_db_path):
        """Test that all JSON output is valid and parseable."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        # Test all JSON methods
        query_result = db.query("AAAAAAA")
        prefix_result = db.query_prefix("A")
        fuzzy_query = pyrustkmer.PyFuzzyQuery(db)
        fuzzy_result = fuzzy_query.query_fuzzy("ANNNNNN", max_mutations=1)
        stats = db.get_stats()

        # All should produce valid JSON
        json.loads(query_result.to_json())
        json.loads(prefix_result.to_json())
        json.loads(fuzzy_result.to_json())
        json.loads(stats.to_json())

    def test_csv_compatible_with_pandas(self, tiny_db_path):
        """Test that CSV output can be read by pandas."""
        pytest.importorskip("pandas")
        import pandas as pd

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        # Test CSV with pandas
        query_result = db.query("AAAAAAA")
        prefix_result = db.query_prefix("A")
        stats = db.get_stats()

        # Filter comments for pandas
        from io import StringIO

        query_df = pd.read_csv(
            StringIO(query_result.to_csv()), comment="#", on_bad_lines="skip"
        )
        prefix_df = pd.read_csv(
            StringIO(prefix_result.to_csv()), comment="#", on_bad_lines="skip"
        )
        stats_df = pd.read_csv(
            StringIO(stats.to_csv()), comment="#", on_bad_lines="skip"
        )

        assert len(query_df) >= 1
        assert len(prefix_df) >= 1
        assert len(stats_df) >= 6

    def test_tsv_compatible_with_pandas(self, tiny_db_path):
        """Test that TSV output can be read by pandas."""
        pytest.importorskip("pandas")
        import pandas as pd

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        query_result = db.query("AAAAAAA")
        prefix_result = db.query_prefix("A")
        stats = db.get_stats()

        from io import StringIO

        query_df = pd.read_csv(
            StringIO(query_result.to_tsv()), sep="\t", comment="#", on_bad_lines="skip"
        )
        prefix_df = pd.read_csv(
            StringIO(prefix_result.to_tsv()), sep="\t", comment="#", on_bad_lines="skip"
        )
        stats_df = pd.read_csv(
            StringIO(stats.to_tsv()), sep="\t", comment="#", on_bad_lines="skip"
        )

        assert len(query_df) >= 1
        assert len(prefix_df) >= 1
        assert len(stats_df) >= 6

    def test_csv_field_names_match_attributes(self, tiny_db_path):
        """Test that CSV field names match object attributes."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        # PyQueryResult
        result = db.query("AAAAAAA")
        csv_str = result.to_csv()
        lines = csv_str.strip().split("\n")
        header = lines[0]
        fields = header.split(",")

        assert "kmer" in fields
        assert "count" in fields
        assert "found" in fields

        # PyDatabaseStats
        stats = db.get_stats()
        csv_str = stats.to_csv()
        lines = csv_str.strip().split("\n")
        header = lines[0]
        fields = header.split(",")

        assert "metric" in fields
        assert "value" in fields


# ============================================================================
# Integration Tests
# ============================================================================


class TestFormatterIntegration:
    """Integration tests for formatter methods."""

    def test_json_roundtrip(self, tiny_db_path):
        """Test that JSON can roundtrip through parse."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        result = db.query("AAAAAAA")
        json_str = result.to_json()
        parsed = json.loads(json_str)

        # Should be able to serialize back to JSON
        json_str2 = json.dumps(parsed, indent=2)
        parsed2 = json.loads(json_str2)

        assert parsed == parsed2

    def test_multiple_queries_format_consistency(self, tiny_db_path):
        """Test format consistency across multiple queries."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        kmers = ["AAAAAAA", "TTTTTTT", "CCCCCCC"]

        for kmer in kmers:
            result = db.query(kmer)

            json_data = json.loads(result.to_json())
            csv_reader = csv.DictReader(io.StringIO(result.to_csv()))
            csv_data = list(csv_reader)[0]

            assert json_data["kmer"] == csv_data["kmer"] == kmer
            assert json_data["count"] == int(csv_data["count"])

    def test_prefix_and_fuzzy_format_comparison(self, tiny_db_path):
        """Test format consistency between prefix and fuzzy results."""
        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        prefix_result = db.query_prefix("A")
        fuzzy_query = pyrustkmer.PyFuzzyQuery(db)
        fuzzy_result = fuzzy_query.query_fuzzy("ANNNNNN", max_mutations=1)

        # Both should have valid JSON, CSV, TSV output
        json.loads(prefix_result.to_json())
        json.loads(fuzzy_result.to_json())

        csv.DictReader(io.StringIO(prefix_result.to_csv()))
        csv.DictReader(io.StringIO(fuzzy_result.to_csv()))

        csv.DictReader(io.StringIO(prefix_result.to_tsv()), delimiter="\t")
        csv.DictReader(io.StringIO(fuzzy_result.to_tsv()), delimiter="\t")
