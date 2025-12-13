"""Integration tests for CLI-API consistency.

These tests verify that the Python API produces identical results to the CLI
when using real data, as required by the specification.
"""

import subprocess
import json
from pathlib import Path
import pytest

from rustkmer import Database
from rustkmer.exceptions import RustKmerError


@pytest.mark.integration
class TestCLIAPIConsistency:
    """Test that Python API results match CLI output exactly."""

    @pytest.fixture
    def real_database_path(self):
        """Path to the real database file for testing."""
        # Path specified in the specification
        return "/Users/forrest/Data/data/kmer/K19/R1_001.rkdb"

    @pytest.fixture
    def rustkmer_cli(self):
        """Path to rustkmer CLI executable."""
        # Find rustkmer in the build directory
        cli_path = Path(__file__).parent.parent.parent / "target" / "release" / "rustkmer"
        if not cli_path.exists():
            pytest.skip(f"rustkmer CLI not found at {cli_path}")
        return str(cli_path)

    def run_cli_query(self, cli_path, db_path, kmer):
        """Run rustkmer CLI query command."""
        cmd = [cli_path, "query", db_path, kmer]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        # CLI output is just the count as a string
        return int(result.stdout.strip())

    def run_cli_dump(self, cli_path, db_path, limit=1000, offset=0):
        """Run rustkmer CLI dump command."""
        cmd = [cli_path, "dump", db_path]
        if limit is not None:
            cmd.extend(["--limit", str(limit)])
        if offset > 0:
            cmd.extend(["--offset", str(offset)])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # Parse tab-separated output
        entries = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('\t')
                if len(parts) >= 2:
                    kmer = parts[0]
                    count = int(parts[1])
                    entries.append((kmer, count))
        return entries

    def run_cli_stats(self, cli_path, db_path):
        """Run rustkmer CLI stats command."""
        cmd = [cli_path, "stats", db_path]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # Parse stats output
        stats = {}
        for line in result.stdout.strip().split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                stats[key.strip().lower().replace(' ', '_')] = value.strip()

        return {
            'kmer_size': int(stats.get('k-mer_size', 0)),
            'unique_kmers': int(stats.get('unique_k-mers', 0)),
            'total_counts': int(stats.get('total_counts', 0)),
            'max_count': int(stats.get('max_count', 0)),
            'format_version': stats.get('format_version', 'unknown')
        }

    @pytest.mark.slow
    def test_single_query_consistency(self, real_database_path, rustkmer_cli):
        """Test that single query results match CLI exactly."""
        # Skip if database doesn't exist
        if not Path(real_database_path).exists():
            pytest.skip(f"Real database not found at {real_database_path}")

        # Test k-mers with different patterns
        test_kmers = [
            "ATCGATCGATCGATCGATCG",  # Random
            "AAAAAAAAAAAAAAAAAAAA",  # All A
            "CCCCCCCCCCCCCCCCCCCC",  # All C
            "GGGGGGGGGGGGGGGGGGGG",  # All G
            "TTTTTTTTTTTTTTTTTTTT",  # All T
            "ATCGATCGATCGATCGATCG",  # Repeating pattern
        ]

        with Database(real_database_path) as db:
            for kmer in test_kmers:
                # Get CLI result
                cli_count = self.run_cli_query(rustkmer_cli, real_database_path, kmer)

                # Get Python API result
                api_result = db.query(kmer)

                # Verify they match exactly
                assert api_result.count == cli_count, (
                    f"Count mismatch for {kmer}: "
                    f"CLI={cli_count}, API={api_result.count}"
                )

    @pytest.mark.slow
    def test_dump_consistency_first_1000(self, real_database_path, rustkmer_cli):
        """Test that dump of first 1000 entries matches CLI exactly."""
        # Skip if database doesn't exist
        if not Path(real_database_path).exists():
            pytest.skip(f"Real database not found at {real_database_path}")

        # Get first 1000 entries from CLI
        cli_entries = self.run_cli_dump(rustkmer_cli, real_database_path, limit=1000)

        # Get first 1000 entries from Python API
        with Database(real_database_path) as db:
            api_entries = []
            for result in db.dump(limit=1000):
                api_entries.append((result.kmer, result.count))

        # Verify exact match
        assert len(api_entries) == len(cli_entries), (
            f"Number of entries mismatch: CLI={len(cli_entries)}, API={len(api_entries)}"
        )

        for i, (api_entry, cli_entry) in enumerate(zip(api_entries, cli_entries)):
            api_kmer, api_count = api_entry
            cli_kmer, cli_count = cli_entry

            assert api_kmer == cli_kmer, f"K-mer mismatch at position {i}: API={api_kmer}, CLI={cli_kmer}"
            assert api_count == cli_count, (
                f"Count mismatch at position {i} for {api_kmer}: "
                f"CLI={cli_count}, API={api_count}"
            )

    @pytest.mark.slow
    def test_stats_consistency(self, real_database_path, rustkmer_cli):
        """Test that database stats match CLI exactly."""
        # Skip if database doesn't exist
        if not Path(real_database_path).exists():
            pytest.skip(f"Real database not found at {real_database_path}")

        # Get stats from CLI
        cli_stats = self.run_cli_stats(rustkmer_cli, real_database_path)

        # Get stats from Python API
        with Database(real_database_path) as db:
            api_stats = db.stats()

        # Verify exact match
        assert api_stats.kmer_size == cli_stats['kmer_size'], (
            f"K-mer size mismatch: CLI={cli_stats['kmer_size']}, API={api_stats.kmer_size}"
        )
        assert api_stats.unique_kmers == cli_stats['unique_kmers'], (
            f"Unique k-mers mismatch: CLI={cli_stats['unique_kmers']}, API={api_stats.unique_kmers}"
        )
        assert api_stats.total_counts == cli_stats['total_counts'], (
            f"Total counts mismatch: CLI={cli_stats['total_counts']}, API={api_stats.total_counts}"
        )
        assert api_stats.max_count == cli_stats['max_count'], (
            f"Max count mismatch: CLI={cli_stats['max_count']}, API={api_stats.max_count}"
        )

    @pytest.mark.slow
    def test_batch_vs_individual_consistency(self, real_database_path):
        """Test that batch queries produce same results as individual queries."""
        # Skip if database doesn't exist
        if not Path(real_database_path).exists():
            pytest.skip(f"Real database not found at {real_database_path}")

        test_kmers = [
            "ATCGATCGATCGATCGATCG",
            "CCCCCCCCCCCCCCCCCCCC",
            "GGGGGGGGGGGGGGGGGGGG",
            "TTTTTTTTTTTTTTTTTTTT",
            "AAAAAAAAAAAAAAAAAAAA",
        ]

        with Database(real_database_path) as db:
            # Get individual query results
            individual_results = {}
            for kmer in test_kmers:
                result = db.query(kmer)
                individual_results[kmer] = result

            # Get batch query results
            batch_results = db.query_batch(test_kmers)

            # Verify they match
            for kmer in test_kmers:
                individual = individual_results[kmer]
                batch = batch_results[kmer]

                assert individual.count == batch.count, (
                    f"Count mismatch for {kmer}: "
                    f"individual={individual.count}, batch={batch.count}"
                )
                assert individual.kmer == batch.kmer
                assert individual.canonical == batch.canonical


@pytest.mark.integration
class TestErrorHandlingConsistency:
    """Test that error handling is consistent between CLI and API."""

    def test_nonexistent_database(self):
        """Test error handling for non-existent database."""
        nonexistent_path = "/nonexistent/path/to/database.rkdb"

        # CLI should fail
        with pytest.raises(RustKmerError):
            Database(nonexistent_path)

    def test_invalid_kmer_handling(self, tmp_path):
        """Test error handling for invalid k-mers."""
        # Create a fake database file
        db_path = tmp_path / "test.rkdb"
        db_path.write_text("fake content")

        with Database(db_path, validate=False) as db:
            # Invalid characters
            from rustkmer.exceptions import InvalidKmerError
            with pytest.raises(InvalidKmerError):
                db.query("ATCGX")  # X is invalid

            # Wrong length (assuming k=19)
            db._kmer_size = 19
            with pytest.raises(InvalidKmerError):
                db.query("ATCG")  # Too short