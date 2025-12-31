"""Utility functions for testing CLI-API consistency."""

import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple, TYPE_CHECKING
import json

if TYPE_CHECKING:
    from rustkmer.database import Database
    from rustkmer.query import QueryResult
    from rustkmer.stats import DatabaseStats


class CLIComparator:
    """Utility class for comparing CLI and API results."""

    def __init__(self, rustkmer_binary: str):
        """Initialize with path to rustkmer binary."""
        self.rustkmer_binary = rustkmer_binary
        # Verify binary exists
        if not Path(rustkmer_binary).exists():
            raise FileNotFoundError(f"rustkmer binary not found at {rustkmer_binary}")

    def run_cli_query(self, db_path: str, kmer: str) -> Dict[str, Any]:
        """Execute CLI query and parse output.

        Args:
            db_path: Path to the database file
            kmer: k-mer sequence to query

        Returns:
            Dictionary with 'count' and 'valid' keys
        """
        cmd = [self.rustkmer_binary, "query", db_path, kmer]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False  # Don't raise exception on non-zero exit
        )

        if result.returncode != 0:
            # CLI error - could be invalid k-mer or other error
            stderr = result.stderr.strip()
            if "Invalid" in stderr.lower() or "error" in stderr.lower():
                return {"count": 0, "valid": False, "error": stderr}
            else:
                raise RuntimeError(f"CLI query failed: {stderr}")

        # Parse output
        output = result.stdout.strip()
        stderr = result.stderr.strip()

        # CLI might output progress/info to stderr, that's normal
        # Check for actual error messages in stderr
        if stderr and "error" in stderr.lower():
            return {"count": 0, "valid": False, "error": stderr}

        if not output:
            # No output means count is 0 (k-mer not found)
            return {"count": 0, "valid": True}

        # Try to parse as integer
        try:
            # CLI outputs "kmer<TAB>count" or just "count"
            lines = output.strip().split('\n')
            for line in reversed(lines):  # Check from bottom up
                line = line.strip()
                if not line:
                    continue

                # Check for tab-separated format: "kmer<TAB>count"
                if '\t' in line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        try:
                            count = int(parts[1])
                            return {"count": count, "valid": True}
                        except ValueError:
                            continue

                # Check for pure number
                elif line.isdigit():
                    return {"count": int(line), "valid": True}
        except ValueError:
            pass

        # If we can't parse, assume count is 0
        return {"count": 0, "valid": True}

    def run_cli_stats(self, db_path: str, format: str = "text") -> Dict[str, Any]:
        """Execute CLI stats and parse output.

        Args:
            db_path: Path to the database file
            format: Output format (text, json, csv, tsv)

        Returns:
            Dictionary with parsed statistics
        """
        cmd = [self.rustkmer_binary, "stats", db_path, "-f", format]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        return self.parse_stats_output(result.stdout, format)

    def parse_stats_output(self, output: str, format: str) -> Dict[str, Any]:
        """Parse CLI stats output into structured data.

        Args:
            output: Raw CLI output
            format: Output format (text, json, csv, tsv)

        Returns:
            Dictionary with parsed statistics
        """
        if format == "json":
            # JSON output may include progress messages
            lines = output.strip().split('\n')
            for line in lines:
                if line.startswith('{'):
                    return json.loads(line)
            # If no JSON line found, fall back to text parsing
            format = "text"

        if format in ("text", "csv", "tsv"):
            stats = {}
            lines = output.strip().split('\n')

            for line in lines:
                if ':' in line:
                    # Text format: "Key: Value"
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_').replace('-', '_')
                    value = value.strip()
                    stats[key] = value
                elif '\t' in line and format == "tsv":
                    # TSV format: "Key\tValue"
                    key, value = line.split('\t', 1)
                    key = key.strip().lower().replace(' ', '_').replace('-', '_')
                    value = value.strip()
                    stats[key] = value
                elif ',' in line and format == "csv":
                    # CSV format: "Key,Value"
                    key, value = line.split(',', 1)
                    key = key.strip().lower().replace(' ', '_').replace('-', '_')
                    value = value.strip()
                    stats[key] = value

            # Convert numeric values
            numeric_fields = [
                'kmer_size', 'k_mer_size',
                'unique_kmers', 'unique_k_mers',
                'total_kmers', 'total_counts',
                'min_count', 'max_count',
                'mean_count', 'median_count'
            ]

            for field in numeric_fields:
                if field in stats:
                    try:
                        # Handle possible units like "1.05" for mean
                        if '.' in stats[field]:
                            stats[field] = float(stats[field])
                        else:
                            stats[field] = int(stats[field])
                    except ValueError:
                        pass  # Keep as string if not numeric

            # Map field names to expected output names
            field_mapping = {
                'k_mer_size': 'kmer_size',
                'unique_k_mers': 'unique_kmers',
                'total_k_mers': 'total_counts'  # CLI uses total_k_mers, API expects total_counts
            }

            # Apply field mapping
            mapped_stats = {}
            for key, value in stats.items():
                mapped_key = field_mapping.get(key, key)
                mapped_stats[mapped_key] = value

            return mapped_stats

        else:
            raise ValueError(f"Unsupported format: {format}")

    def validate_query_consistency(self, api_result: 'QueryResult', cli_result: Dict[str, Any]) -> None:
        """Validate API and CLI query results are consistent.

        Args:
            api_result: Result from Python API
            cli_result: Result from CLI

        Raises:
            AssertionError: If results don't match
        """
        assert api_result.count == cli_result["count"], (
            f"Count mismatch: API={api_result.count}, CLI={cli_result['count']}"
        )

        # Check canonical k-mer consistency
        if cli_result["valid"]:
            # For valid k-mers, API should have canonical representation
            assert api_result.canonical is not None, "API should provide canonical k-mer for valid queries"

    def validate_stats_consistency(self, api_stats: 'DatabaseStats', cli_stats: Dict[str, Any]) -> None:
        """Validate API and CLI stats are consistent.

        Args:
            api_stats: Stats from Python API
            cli_stats: Stats from CLI

        Raises:
            AssertionError: If stats don't match
        """
        # Map CLI field names to API field names
        field_mapping = {
            'kmer_size': 'kmer_size',
            'k_mer_size': 'kmer_size',
            'unique_kmers': 'unique_kmers',
            'unique_k_mers': 'unique_kmers',
            'total_counts': 'total_counts',
            'total_kmers': 'total_counts',
            'min_count': 'min_count',
            'max_count': 'max_count'
        }

        for cli_field, api_field in field_mapping.items():
            if cli_field in cli_stats and hasattr(api_stats, api_field):
                api_value = getattr(api_stats, api_field)
                cli_value = cli_stats[cli_field]

                # Convert to same type for comparison
                if isinstance(api_value, (int, float)):
                    cli_value = float(cli_value) if '.' in str(cli_value) else int(cli_value)

                assert api_value == cli_value, (
                    f"{api_field} mismatch: API={api_value}, CLI={cli_value}"
                )


def get_test_kmers(kmer_size: int) -> Dict[str, List[str]]:
    """Get test k-mers adjusted for the given k-mer size.

    Args:
        kmer_size: Size of k-mers in the database

    Returns:
        Dictionary with different categories of test k-mers
    """
    # Base patterns
    patterns = {
        "all_A": "A",
        "all_C": "C",
        "all_G": "G",
        "all_T": "T",
        "repeating": "ATCG",
        "palindromic1": "ATGCGCAT",
        "palindromic2": "CGATATCG",
        "high_complexity1": "ATCGATCG",
        "high_complexity2": "GCTAGCTA"
    }

    test_kmers = {}

    # Adjust patterns to k-mer size
    for category, pattern in patterns.items():
        # Repeat pattern to reach k-mer size
        full_kmer = (pattern * ((kmer_size // len(pattern)) + 1))[:kmer_size]
        test_kmers[category] = [full_kmer]

    # Add some random k-mers
    import random
    random.seed(42)  # For reproducible tests

    test_kmers["random"] = []
    for _ in range(5):
        kmer = ''.join(random.choices('ATCG', k=kmer_size))
        test_kmers["random"].append(kmer)

    # Add invalid k-mers
    test_kmers["invalid"] = [
        "X" * kmer_size,  # Invalid character
        "ATCG",  # Wrong length (unless k=4)
        "A" * (kmer_size + 1),  # Too long
        "A" * (kmer_size - 1) if kmer_size > 1 else ""  # Too short
    ]

    return test_kmers


def generate_test_kmers(kmer_size: int, count: int = 10) -> List[str]:
    """Generate random test k-mers of specified size.

    Args:
        kmer_size: Length of k-mers to generate
        count: Number of k-mers to generate

    Returns:
        List of random k-mer sequences
    """
    import random
    random.seed(42)  # For reproducible tests

    kmers = []
    for _ in range(count):
        kmer = ''.join(random.choices('ATCG', k=kmer_size))
        kmers.append(kmer)
    return kmers


def reverse_complement(kmer: str) -> str:
    """Return the reverse complement of a k-mer.

    Args:
        kmer: The k-mer sequence

    Returns:
        The reverse complement k-mer
    """
    complement = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C'}
    return ''.join(complement.get(base, base) for base in reversed(kmer))