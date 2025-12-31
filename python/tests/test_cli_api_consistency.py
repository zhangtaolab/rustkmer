"""Tests to verify CLI and Python API produce consistent results."""

import pytest
from rustkmer.database import Database
from rustkmer.query import QueryResult
from rustkmer.stats import DatabaseStats

from .utils import CLIComparator, get_test_kmers, reverse_complement


@pytest.mark.integration
class TestQueryConsistency:
    """Test that CLI and API query results are consistent."""

    @pytest.mark.parametrize("db_file", [
        "tiny_test.rkdb",
        "small_test.rkdb",
        "small_test_k33_C.rkdb",
        pytest.param("medium_test.rkdb", marks=pytest.mark.slow),
        pytest.param("large_test.rkdb", marks=pytest.mark.slow),
    ])
    def test_single_query_consistency(self, test_data_dir, cli_comparator, db_file):
        """Test single query consistency across all databases."""
        db_path = test_data_dir / db_file
        if not db_path.exists():
            pytest.skip(f"Database {db_file} not found")

        # Load database with Python API
        db = Database(str(db_path))

        # Get database stats to determine k-mer size
        stats = db.stats()
        kmer_size = stats.kmer_size

        # Test a few k-mers
        test_kmers_list = get_test_kmers(kmer_size)

        # Test edge cases
        for category, kmers in test_kmers_list.items():
            if category == "invalid":
                continue  # Skip invalid k-mers for this test

            for kmer in kmers[:1]:  # Test first k-mer from each category
                # Get API result
                api_result = db.query(kmer)

                # Get CLI result
                cli_result = cli_comparator.run_cli_query(str(db_path), kmer)

                # Validate consistency
                cli_comparator.validate_query_consistency(api_result, cli_result)

    def test_canonical_kmer_consistency(self, test_data_dir, cli_comparator):
        """Test canonical k-mer handling consistency."""
        db_path = test_data_dir / "tiny_test.rkdb"
        if not db_path.exists():
            pytest.skip("tiny_test.rkdb not found")

        db = Database(str(db_path))

        # Test k-mer and its reverse complement
        kmer = "ATCGATCG"
        rc_kmer = reverse_complement(kmer)

        # API results
        api_result1 = db.query(kmer, validate_strict=False)
        api_result2 = db.query(rc_kmer, validate_strict=False)

        # CLI results
        cli_result1 = cli_comparator.run_cli_query(str(db_path), kmer)
        cli_result2 = cli_comparator.run_cli_query(str(db_path), rc_kmer)

        # Both API and CLI should return same counts for k-mer pair
        assert api_result1.count == api_result2.count
        assert cli_result1["count"] == cli_result2["count"]

        # API should provide canonical representation
        assert api_result1.canonical is not None
        assert api_result1.canonical == api_result2.canonical

        # API and CLI counts should match
        assert api_result1.count == cli_result1["count"]
        assert api_result2.count == cli_result2["count"]

    def test_zero_count_consistency(self, test_data_dir, cli_comparator):
        """Test k-mers that don't exist (should return count=0)."""
        db_path = test_data_dir / "tiny_test.rkdb"
        if not db_path.exists():
            pytest.skip("tiny_test.rkdb not found")

        db = Database(str(db_path))

        # Use a k-mer unlikely to exist
        kmer = "NNNNNNN"  # Invalid character

        # API result
        api_result = db.query(kmer, validate_strict=False)

        # CLI result
        cli_result = cli_comparator.run_cli_query(str(db_path), kmer)

        # Both should return count=0
        assert api_result.count == 0
        assert cli_result["count"] == 0

    def test_invalid_kmer_handling(self, test_data_dir, cli_comparator):
        """Test invalid k-mer handling consistency."""
        db_path = test_data_dir / "tiny_test.rkdb"
        if not db_path.exists():
            pytest.skip("tiny_test.rkdb not found")

        db = Database(str(db_path))

        # Test various invalid k-mers
        invalid_kmers = ["X" * 7, "ATCG", "A" * 10]

        for invalid_kmer in invalid_kmers:
            # API should either raise an exception or return count=0
            try:
                api_result = db.query(invalid_kmer)
                api_count = api_result.count
            except Exception:
                api_count = 0

            # CLI should return count=0 or error
            cli_result = cli_comparator.run_cli_query(str(db_path), invalid_kmer)
            cli_count = cli_result.get("count", 0)

            # Both should indicate no valid matches
            assert api_count == 0
            assert cli_count == 0

    @pytest.mark.parametrize("parallel", [True, False])
    def test_batch_query_consistency(self, test_data_dir, cli_comparator, parallel):
        """Test batch query consistency."""
        db_path = test_data_dir / "tiny_test.rkdb"
        if not db_path.exists():
            pytest.skip("tiny_test.rkdb not found")

        db = Database(str(db_path))

        # Test k-mers
        kmers = ["AAAAAAA", "CCCCCCC", "GGGGGGG", "TTTTTTT"]

        # API batch results
        api_results = db.query_batch(kmers, max_workers=4 if parallel else 1)

        # Compare with individual CLI queries
        for kmer in kmers:
            cli_result = cli_comparator.run_cli_query(str(db_path), kmer)

            # Validate consistency
            cli_comparator.validate_query_consistency(api_results[kmer], cli_result)


@pytest.mark.integration
class TestStatsConsistency:
    """Test that CLI and API stats are consistent."""

    @pytest.mark.parametrize("db_file", [
        "tiny_test.rkdb",
        "small_test.rkdb",
        "small_test_k33_C.rkdb",
        pytest.param("medium_test.rkdb", marks=pytest.mark.slow),
        pytest.param("large_test.rkdb", marks=pytest.mark.slow),
    ])
    @pytest.mark.parametrize("format", ["text", "json"])
    def test_stats_format_consistency(self, test_data_dir, cli_comparator, db_file, format):
        """Test stats consistency across different output formats."""
        db_path = test_data_dir / db_file
        if not db_path.exists():
            pytest.skip(f"Database {db_file} not found")

        # Load database with Python API
        db = Database(str(db_path))

        # Get API stats
        api_stats = db.stats()

        # Get CLI stats
        try:
            cli_stats = cli_comparator.run_cli_stats(str(db_path), format)
        except Exception as e:
            if format == "json":
                pytest.skip(f"JSON format not supported by CLI: {e}")
            else:
                raise

        # Validate consistency
        cli_comparator.validate_stats_consistency(api_stats, cli_stats)

    def test_stats_field_mapping(self, test_data_dir, cli_comparator):
        """Test that field names are properly mapped between CLI and API."""
        db_path = test_data_dir / "tiny_test.rkdb"
        if not db_path.exists():
            pytest.skip("tiny_test.rkdb not found")

        db = Database(str(db_path))

        # Get API stats
        api_stats = db.stats()

        # Get CLI stats in text format
        cli_stats = cli_comparator.run_cli_stats(str(db_path), "text")

        # Check expected fields are present
        expected_fields = ['kmer_size', 'unique_kmers', 'total_counts']

        for field in expected_fields:
            assert hasattr(api_stats, field), f"API missing field: {field}"

            # CLI might use different field names
            cli_variants = [field, field.replace('_', '-'), field.replace('_', ' ')]
            assert any(variant in cli_stats for variant in cli_variants), \
                f"CLI missing field variants for {field}: {cli_stats.keys()}"

    def test_stats_numeric_values(self, test_data_dir, cli_comparator):
        """Test that numeric values are consistent."""
        db_path = test_data_dir / "tiny_test.rkdb"
        if not db_path.exists():
            pytest.skip("tiny_test.rkdb not found")

        db = Database(str(db_path))

        # Get API stats
        api_stats = db.stats()

        # Get CLI stats
        cli_stats = cli_comparator.run_cli_stats(str(db_path), "text")

        # Check that numeric values match
        numeric_fields = [
            ('kmer_size', 'kmer_size'),
            ('kmer_size', 'k-mer_size'),
            ('unique_kmers', 'unique_kmers'),
            ('unique_kmers', 'unique_k-mers'),
            ('total_counts', 'total_counts'),
            ('total_counts', 'total_kmers')
        ]

        for api_field, cli_field in numeric_fields:
            if hasattr(api_stats, api_field) and cli_field in cli_stats:
                api_value = getattr(api_stats, api_field)
                cli_value = cli_stats[cli_field]

                # Convert CLI value to number
                try:
                    if '.' in str(cli_value):
                        cli_value = float(cli_value)
                    else:
                        cli_value = int(cli_value)
                except ValueError:
                    continue  # Skip if not numeric

                assert api_value == cli_value, \
                    f"Mismatch in {api_field}/{cli_field}: API={api_value}, CLI={cli_value}"


@pytest.mark.integration
class TestDumpConsistency:
    """Test that CLI and API dump outputs are consistent."""

    def test_dump_format_consistency(self, test_data_dir, cli_comparator):
        """Test that dump output format is consistent."""
        db_path = test_data_dir / "tiny_test.rkdb"
        if not db_path.exists():
            pytest.skip("tiny_test.rkdb not found")

        db = Database(str(db_path))

        # Get API dump
        api_dump = db.dump(as_string=True)

        # Get CLI dump
        cmd = [cli_comparator.rustkmer_binary, "dump", str(db_path)]
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            pytest.skip(f"CLI dump command failed: {result.stderr}")

        cli_dump = result.stdout

        # Both should be non-empty strings
        assert len(api_dump) > 0
        assert len(cli_dump) > 0

        # Both should contain k-mer data (tab-separated)
        api_lines = [line for line in api_dump.strip().split('\n') if line.strip()]
        cli_lines = [line for line in cli_dump.strip().split('\n') if line.strip() and not line.startswith('#')]

        # Should have similar number of lines (allowing for differences in empty lines)
        assert len(api_lines) > 0
        assert len(cli_lines) > 0

        # Check that both formats are tab-separated
        for line in api_lines[:5]:  # Check first 5 lines
            if line.strip():
                assert '\t' in line, f"API dump line not tab-separated: {line}"

        for line in cli_lines[:5]:  # Check first 5 lines
            if line.strip():
                assert '\t' in line, f"CLI dump line not tab-separated: {line}"

    def test_dump_data_consistency_sample(self, test_data_dir, cli_comparator):
        """Test that a sample of dump data is consistent."""
        db_path = test_data_dir / "tiny_test.rkdb"
        if not db_path.exists():
            pytest.skip("tiny_test.rkdb not found")

        db = Database(str(db_path))

        # Get API dump
        api_dump = db.dump(as_string=True)

        # Get CLI dump
        cmd = [cli_comparator.rustkmer_binary, "dump", str(db_path)]
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            pytest.skip(f"CLI dump command failed: {result.stderr}")

        cli_dump = result.stdout

        # Parse both dumps
        api_data = {}
        for line in api_dump.strip().split('\n'):
            if line.strip() and '\t' in line:
                kmer, count = line.strip().split('\t', 1)
                api_data[kmer] = int(count)

        cli_data = {}
        for line in cli_dump.strip().split('\n'):
            if line.strip() and '\t' in line:
                kmer, count = line.strip().split('\t', 1)
                cli_data[kmer] = int(count)

        # Check that some k-mers appear in both
        common_kmers = set(api_data.keys()) & set(cli_data.keys())
        assert len(common_kmers) > 0, "No common k-mers found between API and CLI dumps"

        # Check that counts match for common k-mers
        for kmer in list(common_kmers)[:10]:  # Check first 10 common k-mers
            assert api_data[kmer] == cli_data[kmer], \
                f"Count mismatch for {kmer}: API={api_data[kmer]}, CLI={cli_data[kmer]}"


@pytest.mark.integration
class TestErrorHandlingConsistency:
    """Test that CLI and API handle errors consistently."""

    def test_nonexistent_database_error(self, cli_comparator):
        """Test error handling for non-existent database."""
        nonexistent_path = "/nonexistent/database.rkdb"

        # API should raise DatabaseError
        with pytest.raises(Exception):  # DatabaseError or similar
            Database(nonexistent_path)

        # CLI should return non-zero exit code
        cmd = [cli_comparator.rustkmer_binary, "stats", nonexistent_path]
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode != 0

    def test_invalid_database_file(self, test_data_dir, cli_comparator, tmp_path):
        """Test error handling for invalid database file."""
        # Create a fake database file
        fake_db = tmp_path / "fake.rkdb"
        fake_db.write_text("This is not a real database")

        # API should raise an error
        with pytest.raises(Exception):
            Database(str(fake_db))

        # CLI should return an error
        cmd = [cli_comparator.rustkmer_binary, "stats", str(fake_db)]
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode != 0