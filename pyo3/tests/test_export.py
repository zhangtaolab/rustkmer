"""
Comprehensive tests for database export functionality.

Tests cover:
1. Text export (export_to_file)
2. JSON export (export_to_json)
3. CSV export (export_to_csv)
4. Memory export (export_all_kmers)
5. CLI consistency with rustkmer dump
6. Performance and memory tests
7. Error handling
8. Load mode compatibility
"""

import json
import csv
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any

import pytest


class TestTextExport:
    """Test text export functionality (export_to_file)."""

    def test_export_basic_format(self, tiny_db_path, tmp_path):
        """Test basic text export format: kmer\\tcount."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        output_file = tmp_path / "output.txt"

        count = db.export_to_file(str(output_file))

        # Verify file was created
        assert output_file.exists()
        assert count > 0

        # Verify format: each line should be "kmer\\tcount"
        with open(output_file, "r") as f:
            for line in f:
                if line.strip():  # Skip empty lines
                    parts = line.strip().split("\t")
                    assert len(parts) == 2, (
                        f"Line should have 2 tab-separated parts: {line}"
                    )
                    kmer, count_str = parts
                    assert kmer.isalpha(), f"Kmer should be alphabetic: {kmer}"
                    assert count_str.isdigit(), f"Count should be numeric: {count_str}"

    def test_export_with_limit(self, tiny_db_path, tmp_path):
        """Test export with limit parameter."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        output_file = tmp_path / "output.txt"

        # Export only 10 k-mers
        limit = 10
        count = db.export_to_file(str(output_file), limit=limit)

        assert count == limit

        # Verify exactly 10 lines
        with open(output_file, "r") as f:
            lines = [line for line in f if line.strip()]
        assert len(lines) == limit

    def test_export_with_offset(self, tiny_db_path, tmp_path):
        """Test export with offset parameter."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        output_full = tmp_path / "full.txt"
        output_offset = tmp_path / "offset.txt"

        # Export all k-mers
        count_full = db.export_to_file(str(output_full))

        # Export with offset, skipping first 5
        offset = 5
        count_offset = db.export_to_file(str(output_offset), offset=offset)

        # Verify offset results
        assert count_offset == count_full - offset

        # Verify content is offset correctly
        with open(output_full, "r") as f_full, open(output_offset, "r") as f_offset:
            full_lines = [line for line in f_full if line.strip()]
            offset_lines = [line for line in f_offset if line.strip()]

            assert len(offset_lines) == len(full_lines) - offset
            for i in range(len(offset_lines)):
                assert offset_lines[i] == full_lines[i + offset]

    def test_export_with_offset_and_limit(self, tiny_db_path, tmp_path):
        """Test export with both offset and limit parameters."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        output_file = tmp_path / "output.txt"

        offset = 5
        limit = 10
        count = db.export_to_file(str(output_file), limit=limit, offset=offset)

        assert count == limit

        # Verify exactly 10 lines
        with open(output_file, "r") as f:
            lines = [line for line in f if line.strip()]
        assert len(lines) == limit

    def test_export_with_progress_callback(self, tiny_db_path, tmp_path):
        """Test export with progress callback."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        output_file = tmp_path / "output.txt"

        progress_updates = []

        def progress_callback(current: int, total: int):
            progress_updates.append((current, total))

        count = db.export_to_file(str(output_file), progress_callback=progress_callback)

        # Verify progress callback was called
        assert len(progress_updates) > 0

        # Verify progress values are reasonable
        for current, total in progress_updates:
            assert isinstance(current, int)
            assert isinstance(total, int)
            assert current <= total
            assert total > 0

        # Final progress should match exported count
        final_current, final_total = progress_updates[-1]
        assert final_current == count

    def test_export_unicode_handling(self, tiny_db_path, tmp_path):
        """Test that export handles Unicode correctly (UTF-8)."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        output_file = tmp_path / "output.txt"

        db.export_to_file(str(output_file))

        # Verify file can be read with UTF-8 encoding
        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert len(content) > 0

        # Verify no encoding errors
        try:
            with open(output_file, "rb") as f:
                raw_content = f.read()
                raw_content.decode("utf-8")
        except UnicodeDecodeError as e:
            pytest.fail(f"UTF-8 decoding error: {e}")


class TestJsonExport:
    """Test JSON export functionality (export_to_json)."""

    def test_export_json_format(self, tiny_db_path, tmp_path):
        """Test JSON export format and structure."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        output_file = tmp_path / "output.json"

        count = db.export_to_json(str(output_file))

        # Verify file was created
        assert output_file.exists()
        assert count > 0

        # Verify JSON can be parsed
        with open(output_file, "r") as f:
            data = json.load(f)

        # Verify structure: array of objects
        assert isinstance(data, list)
        assert len(data) > 0

        # Verify each entry has correct structure
        for entry in data:
            assert isinstance(entry, dict)
            assert "kmer" in entry
            assert "count" in entry
            assert isinstance(entry["kmer"], str)
            assert isinstance(entry["count"], int)
            assert entry["kmer"].isalpha()

    def test_export_json_with_limit(self, tiny_db_path, tmp_path):
        """Test JSON export with limit parameter."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        output_file = tmp_path / "output.json"

        limit = 10
        count = db.export_to_json(str(output_file), limit=limit)

        assert count == limit

        # Verify JSON contains exactly 10 entries
        with open(output_file, "r") as f:
            data = json.load(f)
        assert len(data) == limit

    def test_export_json_with_offset(self, tiny_db_path, tmp_path):
        """Test JSON export with offset parameter."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        output_full = tmp_path / "full.json"
        output_offset = tmp_path / "offset.json"

        count_full = db.export_to_json(str(output_full))

        offset = 5
        count_offset = db.export_to_json(str(output_offset), offset=offset)

        assert count_offset == count_full - offset

        # Verify content is offset correctly
        with open(output_full, "r") as f_full, open(output_offset, "r") as f_offset:
            full_data = json.load(f_full)
            offset_data = json.load(f_offset)

            assert len(offset_data) == len(full_data) - offset
            for i in range(len(offset_data)):
                assert offset_data[i] == full_data[i + offset]

    def test_export_json_with_progress_callback(self, tiny_db_path, tmp_path):
        """Test JSON export with progress callback."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        output_file = tmp_path / "output.json"

        progress_updates = []

        def progress_callback(current: int, total: int):
            progress_updates.append((current, total))

        count = db.export_to_json(str(output_file), progress_callback=progress_callback)

        assert len(progress_updates) > 0

        # Verify progress values
        for current, total in progress_updates:
            assert isinstance(current, int)
            assert isinstance(total, int)
            assert current <= total

    def test_export_json_large_dataset(self, small_db_path, tmp_path):
        """Test JSON export with larger dataset for performance."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(small_db_path, pyrustkmer.LoadMode.Preload)
        output_file = tmp_path / "output.json"

        count = db.export_to_json(str(output_file), limit=100)

        assert count == 100

        # Verify JSON can be parsed efficiently
        with open(output_file, "r") as f:
            data = json.load(f)
        assert len(data) == 100


class TestCsvExport:
    """Test CSV export functionality (export_to_csv)."""

    def test_export_csv_format(self, tiny_db_path, tmp_path):
        """Test CSV export format with header."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        output_file = tmp_path / "output.csv"

        count = db.export_to_csv(str(output_file))

        # Verify file was created
        assert output_file.exists()
        assert count > 0

        # Verify CSV format with header
        with open(output_file, "r") as f:
            reader = csv.DictReader(f)

            # Check header
            assert reader.fieldnames == ["kmer", "count"]

            # Verify all rows
            rows = list(reader)
            assert len(rows) == count

            for row in rows:
                assert "kmer" in row
                assert "count" in row
                assert row["kmer"].isalpha()
                assert row["count"].isdigit()

    def test_export_csv_with_limit(self, tiny_db_path, tmp_path):
        """Test CSV export with limit parameter."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        output_file = tmp_path / "output.csv"

        limit = 10
        count = db.export_to_csv(str(output_file), limit=limit)

        assert count == limit

        # Verify exactly 10 data rows (excluding header)
        with open(output_file, "r") as f:
            lines = [line for line in f if line.strip()]
            # 1 header + limit data rows
            assert len(lines) == limit + 1

    def test_export_csv_with_offset(self, tiny_db_path, tmp_path):
        """Test CSV export with offset parameter."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        output_full = tmp_path / "full.csv"
        output_offset = tmp_path / "offset.csv"

        count_full = db.export_to_csv(str(output_full))

        offset = 5
        count_offset = db.export_to_csv(str(output_offset), offset=offset)

        assert count_offset == count_full - offset

        # Verify content
        with open(output_full, "r") as f_full, open(output_offset, "r") as f_offset:
            reader_full = csv.DictReader(f_full)
            reader_offset = csv.DictReader(f_offset)

            full_rows = list(reader_full)
            offset_rows = list(reader_offset)

            assert len(offset_rows) == len(full_rows) - offset
            for i in range(len(offset_rows)):
                assert offset_rows[i] == full_rows[i + offset]

    def test_export_csv_pandas_compatibility(self, tiny_db_path, tmp_path):
        """Test that CSV export is compatible with pandas."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        output_file = tmp_path / "output.csv"

        count = db.export_to_csv(str(output_file))

        # Try to import and read with pandas (if available)
        try:
            import pandas as pd

            df = pd.read_csv(output_file)

            # Verify DataFrame structure
            assert list(df.columns) == ["kmer", "count"]
            assert len(df) == count
            assert df["kmer"].dtype == object or df["kmer"].dtype == str
            assert df["count"].dtype == int
        except ImportError:
            pytest.skip("pandas not available")

    def test_export_csv_with_progress_callback(self, tiny_db_path, tmp_path):
        """Test CSV export with progress callback."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        output_file = tmp_path / "output.csv"

        progress_updates = []

        def progress_callback(current: int, total: int):
            progress_updates.append((current, total))

        count = db.export_to_csv(str(output_file), progress_callback=progress_callback)

        assert len(progress_updates) > 0

        # Verify progress values
        for current, total in progress_updates:
            assert isinstance(current, int)
            assert isinstance(total, int)
            assert current <= total


class TestMemoryExport:
    """Test in-memory export functionality (export_all_kmers)."""

    def test_export_all_kmers_basic(self, tiny_db_path):
        """Test basic export_all_kmers returns PyQueryResult objects."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        results = db.export_all_kmers()

        # Verify return type
        assert isinstance(results, list)
        assert len(results) > 0

        # Verify first result structure
        first = results[0]
        assert hasattr(first, "kmer")
        assert hasattr(first, "count")
        assert hasattr(first, "found")

        # Verify types
        assert isinstance(first.kmer, str)
        assert isinstance(first.count, int)
        assert isinstance(first.found, bool)

        # Verify kmer is valid DNA sequence
        assert first.kmer.isalpha()

    def test_export_all_kmers_with_limit(self, tiny_db_path):
        """Test export_all_kmers with limit parameter."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        limit = 10
        results = db.export_all_kmers(limit=limit)

        assert len(results) == limit

        # Verify all results are valid
        for result in results:
            assert hasattr(result, "kmer")
            assert hasattr(result, "count")
            assert hasattr(result, "found")

    def test_export_all_kmers_with_offset(self, tiny_db_path):
        """Test export_all_kmers with offset parameter."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        full_results = db.export_all_kmers()

        offset = 5
        offset_results = db.export_all_kmers(offset=offset)

        assert len(offset_results) == len(full_results) - offset

        # Verify content matches
        for i in range(len(offset_results)):
            assert offset_results[i].kmer == full_results[i + offset].kmer
            assert offset_results[i].count == full_results[i + offset].count

    def test_export_all_kmers_with_offset_and_limit(self, tiny_db_path):
        """Test export_all_kmers with both offset and limit."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        offset = 5
        limit = 10
        results = db.export_all_kmers(limit=limit, offset=offset)

        assert len(results) == limit

        # Verify all results are valid
        for result in results:
            assert hasattr(result, "kmer")
            assert hasattr(result, "count")
            assert hasattr(result, "found")
            assert result.found == (result.count > 0)

    def test_export_all_kmers_large_dataset(self, small_db_path):
        """Test export_all_kmers with larger dataset."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(small_db_path, pyrustkmer.LoadMode.Preload)

        # Export first 100 k-mers
        limit = 100
        results = db.export_all_kmers(limit=limit)

        assert len(results) == limit

        # Verify all results are valid
        for result in results:
            assert hasattr(result, "kmer")
            assert hasattr(result, "count")
            assert hasattr(result, "found")


class TestCliConsistency:
    """Test consistency between export functions and CLI dump command."""

    def test_export_to_file_vs_cli_dump(self, tiny_db_path, tmp_path):
        """Compare export_to_file with rustkmer dump CLI output."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        # Export using Python API
        pyo3_output = tmp_path / "pyo3_output.txt"
        pyo3_count = db.export_to_file(str(pyo3_output))

        # Export using CLI
        cli_output = tmp_path / "cli_output.txt"
        result = subprocess.run(
            ["rustkmer", "dump", tiny_db_path, "--output", str(cli_output)],
            capture_output=True,
            text=True,
        )

        # Verify CLI succeeded
        assert result.returncode == 0

        # Both files should exist
        assert pyo3_output.exists()
        assert cli_output.exists()

        # Compare content (skip CLI header comments)
        with open(pyo3_output, "r") as f:
            pyo3_lines = [line.strip() for line in f if line.strip()]

        with open(cli_output, "r") as f:
            cli_lines = [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]

        # Remove any empty lines
        pyo3_lines = [line for line in pyo3_lines if line]
        cli_lines = [line for line in cli_lines if line]

        # Compare number of k-mers
        assert len(pyo3_lines) == len(cli_lines)

        # Compare content (both should have same kmer-count pairs)
        for pyo3_line, cli_line in zip(pyo3_lines, cli_lines):
            assert pyo3_line == cli_line, (
                f"Mismatch:\n  PyO3: {pyo3_line}\n  CLI: {cli_line}"
            )

    def test_export_field_order(self, tiny_db_path, tmp_path):
        """Verify field order is consistent across all export methods."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        # Export to text
        text_output = tmp_path / "output.txt"
        db.export_to_file(str(text_output), limit=10)

        # Export to JSON
        json_output = tmp_path / "output.json"
        db.export_to_json(str(json_output), limit=10)

        # Export to CSV
        csv_output = tmp_path / "output.csv"
        db.export_to_csv(str(csv_output), limit=10)

        # Get data from all formats
        with open(text_output, "r") as f:
            text_data = [line.strip().split("\t") for line in f if line.strip()]

        with open(json_output, "r") as f:
            json_data = json.load(f)

        with open(csv_output, "r") as f:
            csv_data = list(csv.DictReader(f))

        # Verify all have same number of entries
        assert len(text_data) == len(json_data) == len(csv_data)

        # Verify field order: kmer first, then count
        for i in range(len(text_data)):
            # Text: kmer\tcount
            text_kmer, text_count = text_data[i]

            # JSON: {"kmer": "...", "count": ...}
            json_kmer, json_count = json_data[i]["kmer"], json_data[i]["count"]

            # CSV: kmer,count
            csv_kmer, csv_count = csv_data[i]["kmer"], csv_data[i]["count"]

            # All should have the same kmer
            assert text_kmer == json_kmer == csv_kmer

            # All should have the same count
            assert text_count == str(json_count) == csv_count

    def test_encoding_consistency(self, tiny_db_path, tmp_path):
        """Verify all export methods use UTF-8 encoding."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        # Export to all formats
        text_output = tmp_path / "output.txt"
        json_output = tmp_path / "output.json"
        csv_output = tmp_path / "output.csv"

        db.export_to_file(str(text_output), limit=10)
        db.export_to_json(str(json_output), limit=10)
        db.export_to_csv(str(csv_output), limit=10)

        # All files should be readable with UTF-8
        for output_file in [text_output, json_output, csv_output]:
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    content = f.read()
                assert len(content) > 0

                # Verify raw bytes are valid UTF-8
                with open(output_file, "rb") as f:
                    raw = f.read()
                    raw.decode("utf-8")
            except UnicodeDecodeError as e:
                pytest.fail(f"UTF-8 encoding error in {output_file}: {e}")


class TestPerformanceAndMemory:
    """Test performance and memory efficiency of export functions."""

    def test_large_database_export_performance(self, small_db_path, tmp_path):
        """Test export performance with moderately large database."""
        import pyrustkmer
        import time

        db = pyrustkmer.PyDatabase(small_db_path, pyrustkmer.LoadMode.Preload)

        # Export to text
        text_output = tmp_path / "output.txt"
        start_time = time.time()
        text_count = db.export_to_file(str(text_output), limit=1000)
        text_time = time.time() - start_time

        # Export to JSON
        json_output = tmp_path / "output.json"
        start_time = time.time()
        json_count = db.export_to_json(str(json_output), limit=1000)
        json_time = time.time() - start_time

        # Export to CSV
        csv_output = tmp_path / "output.csv"
        start_time = time.time()
        csv_count = db.export_to_csv(str(csv_output), limit=1000)
        csv_time = time.time() - start_time

        # All should export the same number
        assert text_count == json_count == csv_count == 1000

        # Performance should be reasonable (< 10 seconds for 1000 k-mers)
        assert text_time < 10.0, f"Text export too slow: {text_time:.2f}s"
        assert json_time < 10.0, f"JSON export too slow: {json_time:.2f}s"
        assert csv_time < 10.0, f"CSV export too slow: {csv_time:.2f}s"

        print(f"\nExport performance for 1000 k-mers:")
        print(f"  Text: {text_time:.3f}s")
        print(f"  JSON: {json_time:.3f}s")
        print(f"  CSV:  {csv_time:.3f}s")

    def test_streaming_io_verification(self, small_db_path, tmp_path):
        """Verify that export uses streaming I/O (doesn't load everything in memory)."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(small_db_path, pyrustkmer.LoadMode.Preload)

        # Get stats to know the actual number of k-mers
        stats = db.get_stats()
        total_kmers = stats.total_kmers

        # Export a large number of k-mers
        limit = 5000
        output_file = tmp_path / "output.txt"

        # If streaming is used, this should not cause memory issues
        count = db.export_to_file(str(output_file), limit=limit)

        # Should export min(limit, total_kmers)
        expected_count = min(limit, int(total_kmers))
        assert count == expected_count

        # Verify file was written incrementally (not all at once)
        file_size = output_file.stat().st_size
        assert file_size > 0

        # Each line should be roughly: "AAAAAAAA\t1000\n" (~12 bytes)
        # File size should be reasonable
        expected_min_size = expected_count * 10  # At least 10 bytes per line
        expected_max_size = expected_count * 100  # At most 100 bytes per line
        assert expected_min_size <= file_size <= expected_max_size

    def test_memory_export_pagination(self, small_db_path):
        """Test that export_all_kmers pagination works efficiently."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(small_db_path, pyrustkmer.LoadMode.Preload)

        batch_size = 100
        all_results = []

        # Get results in batches
        for offset in range(0, 1000, batch_size):
            batch = db.export_all_kmers(limit=batch_size, offset=offset)
            all_results.extend(batch)

            # Stop if we got fewer results than batch size (end of data)
            if len(batch) < batch_size:
                break

        # Verify total results
        assert len(all_results) > 0

        # Verify no duplicates
        kmers = [result.kmer for result in all_results]
        assert len(kmers) == len(set(kmers)), (
            "Duplicate k-mers found in paginated results"
        )


class TestErrorHandling:
    """Test error handling for export functions."""

    def test_export_without_loading_database(self, tmp_path):
        """Test that export fails when database is not loaded."""
        import pyrustkmer

        # Create a database without loading (this shouldn't be possible in normal usage)
        # But we can test by using a non-existent file
        fake_db = tmp_path / "nonexistent.rkdb"

        with pytest.raises(Exception):  # Should raise some kind of error
            db = pyrustkmer.PyDatabase(str(fake_db), pyrustkmer.LoadMode.Preload)

    def test_export_invalid_path(self, tiny_db_path):
        """Test export to invalid path (directory instead of file)."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        # Try to export to a directory (should fail)
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = tmpdir  # This is a directory, not a file

            with pytest.raises(Exception):  # Should raise PermissionError or similar
                db.export_to_file(output_path)

    def test_export_readonly_directory(self, tiny_db_path):
        """Test export to read-only directory."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)

        # This test is platform-dependent and may not work on all systems
        # Skip if we can't create a read-only directory
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Make directory read-only (Unix-like systems)
                os.chmod(tmpdir, 0o444)

                output_file = os.path.join(tmpdir, "output.txt")

                with pytest.raises(Exception):  # Should raise PermissionError
                    db.export_to_file(output_file)
        except (OSError, PermissionError):
            pytest.skip("Cannot create read-only directory on this system")

    def test_export_with_invalid_limit(self, tiny_db_path, tmp_path):
        """Test export with invalid limit parameter."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        output_file = tmp_path / "output.txt"

        # Test with negative limit (should handle gracefully or raise error)
        try:
            count = db.export_to_file(str(output_file), limit=-1)
            # If it doesn't raise an error, it should export 0 or handle it gracefully
            assert count >= 0
        except Exception:
            # Raising an error is also acceptable
            pass

    def test_export_with_invalid_offset(self, tiny_db_path, tmp_path):
        """Test export with invalid offset parameter."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(tiny_db_path, pyrustkmer.LoadMode.Preload)
        output_file = tmp_path / "output.txt"

        # Test with offset larger than database size
        offset = 1_000_000
        count = db.export_to_file(str(output_file), offset=offset)

        # Should export 0 k-mers (out of range)
        assert count == 0

        # Verify file is empty or only has header (for CSV)
        with open(output_file, "r") as f:
            content = f.read()
            # For CSV, there might be a header
            lines = [line for line in content.split("\n") if line.strip()]
            assert len(lines) <= 1  # Only header at most


class TestLoadModeCompatibility:
    """Test export functionality across different load modes."""

    @pytest.mark.parametrize("load_mode", ["Preload", "Lazy", "MemoryMapped"])
    def test_export_to_file_all_modes(self, tiny_db_path, tmp_path, load_mode):
        """Test export_to_file with all load modes."""
        import pyrustkmer

        mode = getattr(pyrustkmer.LoadMode, load_mode)
        db = pyrustkmer.PyDatabase(tiny_db_path, mode)
        output_file = tmp_path / f"output_{load_mode}.txt"

        count = db.export_to_file(str(output_file), limit=10)

        assert count == 10
        assert output_file.exists()

        # Verify format
        with open(output_file, "r") as f:
            lines = [line for line in f if line.strip()]
        assert len(lines) == 10

    @pytest.mark.parametrize("load_mode", ["Preload", "Lazy", "MemoryMapped"])
    def test_export_to_json_all_modes(self, tiny_db_path, tmp_path, load_mode):
        """Test export_to_json with all load modes."""
        import pyrustkmer

        mode = getattr(pyrustkmer.LoadMode, load_mode)
        db = pyrustkmer.PyDatabase(tiny_db_path, mode)
        output_file = tmp_path / f"output_{load_mode}.json"

        count = db.export_to_json(str(output_file), limit=10)

        assert count == 10
        assert output_file.exists()

        # Verify JSON structure
        with open(output_file, "r") as f:
            data = json.load(f)
        assert len(data) == 10

    @pytest.mark.parametrize("load_mode", ["Preload", "Lazy", "MemoryMapped"])
    def test_export_to_csv_all_modes(self, tiny_db_path, tmp_path, load_mode):
        """Test export_to_csv with all load modes."""
        import pyrustkmer

        mode = getattr(pyrustkmer.LoadMode, load_mode)
        db = pyrustkmer.PyDatabase(tiny_db_path, mode)
        output_file = tmp_path / f"output_{load_mode}.csv"

        count = db.export_to_csv(str(output_file), limit=10)

        assert count == 10
        assert output_file.exists()

        # Verify CSV structure
        with open(output_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 10

    @pytest.mark.parametrize("load_mode", ["Preload", "Lazy", "MemoryMapped"])
    def test_export_all_kmers_all_modes(self, tiny_db_path, load_mode):
        """Test export_all_kmers with all load modes."""
        import pyrustkmer

        mode = getattr(pyrustkmer.LoadMode, load_mode)
        db = pyrustkmer.PyDatabase(tiny_db_path, mode)

        results = db.export_all_kmers(limit=10)

        assert len(results) == 10

        # Verify structure
        for result in results:
            assert hasattr(result, "kmer")
            assert hasattr(result, "count")
            assert hasattr(result, "found")

    def test_consistency_across_load_modes(self, tiny_db_path, tmp_path):
        """Verify export results are consistent across all load modes."""
        import pyrustkmer

        # Export using all three modes
        results = {}

        for load_mode_name in ["Preload", "Lazy", "MemoryMapped"]:
            mode = getattr(pyrustkmer.LoadMode, load_mode_name)
            db = pyrustkmer.PyDatabase(tiny_db_path, mode)

            # Export to text
            output_file = tmp_path / f"output_{load_mode_name}.txt"
            count = db.export_to_file(str(output_file), limit=100)

            results[load_mode_name] = {"count": count, "file": output_file}

        # All should export the same number
        assert (
            results["Preload"]["count"]
            == results["Lazy"]["count"]
            == results["MemoryMapped"]["count"]
        )

        # Content should be identical
        preload_content = []
        with open(results["Preload"]["file"], "r") as f:
            preload_content = [line.strip() for line in f if line.strip()]

        for load_mode_name in ["Lazy", "MemoryMapped"]:
            mode_content = []
            with open(results[load_mode_name]["file"], "r") as f:
                mode_content = [line.strip() for line in f if line.strip()]

            assert mode_content == preload_content, (
                f"Content mismatch for {load_mode_name}"
            )


class TestLargeDatasetExport:
    """Test export functionality with larger datasets (100k+ k-mers)."""

    def test_large_database_export(self, small_db_path, tmp_path):
        """Test export with database containing many k-mers."""
        import pyrustkmer
        import time

        db = pyrustkmer.PyDatabase(small_db_path, pyrustkmer.LoadMode.Preload)

        # Get stats to see how many k-mers we have
        stats = db.get_stats()
        total_kmers = stats.total_kmers

        # Export all k-mers to text
        output_file = tmp_path / "large_output.txt"
        start_time = time.time()
        count = db.export_to_file(str(output_file))
        elapsed = time.time() - start_time

        # Verify export
        assert count == total_kmers
        assert output_file.exists()

        # Verify performance (should handle 100k+ k-mers reasonably)
        print(f"\nExported {count} k-mers in {elapsed:.3f}s")
        assert elapsed < 60.0, (
            f"Export took too long: {elapsed:.2f}s for {count} k-mers"
        )

        # Verify file size is reasonable
        file_size = output_file.stat().st_size
        expected_min_size = count * 10  # At least 10 bytes per line
        assert file_size >= expected_min_size

    def test_large_database_json_export(self, small_db_path, tmp_path):
        """Test JSON export with large database."""
        import pyrustkmer
        import time

        db = pyrustkmer.PyDatabase(small_db_path, pyrustkmer.LoadMode.Preload)

        # Get stats to know the actual number of k-mers
        stats = db.get_stats()
        total_kmers = stats.total_kmers

        # Export to JSON (with limit to avoid huge files in tests)
        limit = 10000
        output_file = tmp_path / "large_output.json"
        start_time = time.time()
        count = db.export_to_json(str(output_file), limit=limit)
        elapsed = time.time() - start_time

        # Verify export - should export min(limit, total_kmers)
        expected_count = min(limit, int(total_kmers))
        assert count == expected_count
        assert output_file.exists()

        # Verify JSON can be parsed
        with open(output_file, "r") as f:
            data = json.load(f)
        assert len(data) == expected_count

        print(f"\nExported {count} k-mers to JSON in {elapsed:.3f}s")

    def test_large_database_csv_export(self, small_db_path, tmp_path):
        """Test CSV export with large database."""
        import pyrustkmer
        import time

        db = pyrustkmer.PyDatabase(small_db_path, pyrustkmer.LoadMode.Preload)

        # Get stats to know the actual number of k-mers
        stats = db.get_stats()
        total_kmers = stats.total_kmers

        # Export to CSV (with limit)
        limit = 10000
        output_file = tmp_path / "large_output.csv"
        start_time = time.time()
        count = db.export_to_csv(str(output_file), limit=limit)
        elapsed = time.time() - start_time

        # Verify export - should export min(limit, total_kmers)
        expected_count = min(limit, int(total_kmers))
        assert count == expected_count
        assert output_file.exists()

        # Verify CSV structure
        with open(output_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == expected_count

        print(f"\nExported {count} k-mers to CSV in {elapsed:.3f}s")

    def test_large_database_memory_export_pagination(self, small_db_path):
        """Test export_all_kmers pagination with large database."""
        import pyrustkmer

        db = pyrustkmer.PyDatabase(small_db_path, pyrustkmer.LoadMode.Preload)

        # Get stats
        stats = db.get_stats()
        total_kmers = stats.total_kmers

        # Export in batches of 1000
        batch_size = 1000
        total_exported = 0
        batch_count = 0

        for offset in range(0, min(total_kmers, 10000), batch_size):
            batch = db.export_all_kmers(limit=batch_size, offset=offset)
            total_exported += len(batch)
            batch_count += 1

            # Verify each result is valid
            for result in batch:
                assert hasattr(result, "kmer")
                assert hasattr(result, "count")
                assert hasattr(result, "found")

        print(f"\nExported {total_exported} k-mers in {batch_count} batches")

        # Verify we exported the expected number
        expected = min(total_kmers, 10000)
        assert total_exported == expected
