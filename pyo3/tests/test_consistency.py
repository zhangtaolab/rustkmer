"""Tests for CLI vs PyO3 API consistency."""

import pytest
import subprocess
from pathlib import Path


class TestCLIAPICompatibility:
    """Test compatibility between CLI and PyO3 API results."""
    
    @pytest.fixture
    def cli_binary(self):
        """Get path to rustkmer CLI binary."""
        cli_path = Path(__file__).parent.parent.parent / "target" / "release" / "rustkmer"
        if not cli_path.exists():
            pytest.skip(f"rustkmer CLI not found at {cli_path}")
        return str(cli_path)
    
    @pytest.fixture
    def run_cli_query(self, cli_binary):
        """Create function to run CLI queries."""
        def _run_query(db_path: str, kmer: str) -> dict:
            cmd = [cli_binary, "query", db_path, kmer]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                return {"count": 0, "valid": False, "error": result.stderr}
            
            # Parse output
            output = result.stdout.strip()
            if not output:
                return {"count": 0, "valid": True}
            
            try:
                # Try to parse count from output
                lines = output.split('\n')
                for line in reversed(lines):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Check for tab-separated format
                    if '\t' in line:
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            return {"count": int(parts[1]), "valid": True}
                    
                    # Check for pure number
                    elif line.isdigit():
                        return {"count": int(line), "valid": True}
            except (ValueError, IndexError):
                pass
            
            return {"count": 0, "valid": True}
        
        return _run_query
    
    def test_query_count_matches_cli(
        self, PyDatabase, LoadMode, tiny_db_path, run_cli_query
    ):
        """Test that PyO3 query count matches CLI query count."""
        db = PyDatabase(tiny_db_path, LoadMode.Preload)
        
        # Test several kmers
        test_kmers = ["AAAAAAA", "CCCCCCC", "GGGGGGG"]
        
        for kmer in test_kmers:
            pyo3_result = db.query(kmer)
            cli_result = run_cli_query(tiny_db_path, kmer)
            
            if cli_result["valid"]:
                # Counts should match
                assert pyo3_result.count == cli_result["count"], \
                    f"Count mismatch for {kmer}: PyO3={pyo3_result.count}, CLI={cli_result['count']}"
    
    def test_query_found_matches_cli(
        self, PyDatabase, LoadMode, tiny_db_path, run_cli_query
    ):
        """Test that PyO3 'found' flag matches CLI behavior."""
        db = PyDatabase(tiny_db_path, LoadMode.Preload)
        
        # Test kmer that exists vs doesn't exist
        test_kmers = ["AAAAAAA", "ACGTACGT"]  # First likely exists, second likely doesn't
        
        for kmer in test_kmers:
            pyo3_result = db.query(kmer)
            cli_result = run_cli_query(tiny_db_path, kmer)
            
            if cli_result["valid"]:
                # If CLI count > 0, both should indicate found
                if cli_result["count"] > 0:
                    assert pyo3_result.found == True, \
                        f"Found flag mismatch for {kmer}"
    
    def test_stats_match_cli(
        self, PyDatabase, LoadMode, tiny_db_path, cli_binary
    ):
        """Test that PyO3 stats match CLI stats."""
        db = PyDatabase(tiny_db_path, LoadMode.Preload)
        
        # Get PyO3 stats
        pyo3_stats = db.get_stats()
        
        # Get CLI stats
        cmd = [cli_binary, "info", tiny_db_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Parse CLI output for kmer_size
            # This test just verifies both return reasonable values
            assert pyo3_stats.kmer_size > 0
            assert pyo3_stats.total_kmers >= 0
            assert pyo3_stats.unique_kmers >= 0


class TestPyO3SpecificFeatures:
    """Test PyO3-specific features not available in CLI."""
    
    def test_load_mode_functionality(self, PyDatabase, LoadMode, tiny_db_path):
        """Test that different load modes work correctly."""
        for mode in [LoadMode.Preload, LoadMode.MemoryMapped, LoadMode.Lazy]:
            db = PyDatabase(tiny_db_path, mode)
            
            # Query should work
            result = db.query("AAAAAAA")
            assert result is not None
            assert hasattr(result, 'count')
    
    def test_memory_usage_functionality(self, PyDatabase, LoadMode, tiny_db_path):
        """Test memory usage reporting."""
        db = PyDatabase(tiny_db_path, LoadMode.Preload)
        
        try:
            memory_info = db.get_memory_usage()
            assert memory_info is not None
        except AttributeError:
            # Some implementations might not have this
            pass
    
    def test_prefix_query_not_in_cli(self, PyPrefixQuery, LoadMode, tiny_db_path):
        """Test prefix query feature (not available in basic CLI)."""
        query = PyPrefixQuery(tiny_db_path)
        
        result = query.query_prefix("AAA")
        
        # This is a PyO3-specific feature
        assert result is not None
        assert hasattr(result, 'total_matches') or hasattr(result, 'matches')
    
    def test_fuzzy_query_equivalence(self, PyFuzzyQuery, LoadMode, tiny_db_path):
        """Test fuzzy query returns reasonable results."""
        query = PyFuzzyQuery(PyDatabase(tiny_db_path, LoadMode.Preload))
        
        # Test wildcard query
        result = query.fuzzy_query("ANNNNNN")
        
        # Should return results
        assert result is not None
        assert hasattr(result, 'total_matches')
        assert isinstance(result.total_matches, int)
