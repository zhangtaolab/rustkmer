"""Utility functions for pyrustkmer tests."""

from typing import List, Dict, Any, Optional
from pathlib import Path


def get_test_kmers(db_path: str, count: int = 10) -> List[str]:
    """Generate test k-mers from database query results.

    Args:
        db_path: Path to database file
        count: Number of k-mers to retrieve

    Returns:
        List of k-mer strings
    """
    import pyrustkmer

    db = pyrustkmer.PyDatabase(db_path, pyrustkmer.LoadMode.Preload)

    # Query some k-mers that exist in the database
    kmers = []

    # Query a few specific k-mers
    test_kmers = [
        "AAAAAAA",  # All A
        "CCCCCCC",  # All C
        "GGGGGGG",  # All G
        "TTTTTTT",  # All T
    ]

    for kmer in test_kmers:
        try:
            result = db.query(kmer)
            if hasattr(result, "count") and result.count > 0:
                kmers.append(kmer)
        except Exception:
            continue

    return kmers


def reverse_complement(sequence: str) -> str:
    """Generate reverse complement of a DNA sequence.

    Args:
        sequence: DNA sequence (A, T, C, G)

    Returns:
        Reverse complement sequence
    """
    complement = {
        "A": "T",
        "T": "A",
        "C": "G",
        "G": "C",
        "a": "t",
        "t": "a",
        "c": "g",
        "g": "c",
    }

    try:
        return "".join(complement[base] for base in reversed(sequence))
    except KeyError:
        # Handle invalid characters gracefully
        return sequence


def compare_results(result1: Any, result2: Any, fields: List[str]) -> bool:
    """Compare two result objects on specified fields.

    Args:
        result1: First result object
        result2: Second result object
        fields: List of field names to compare

    Returns:
        True if all specified fields match
    """
    for field in fields:
        val1 = getattr(result1, field, None)
        val2 = getattr(result2, field, None)
        if val1 != val2:
            return False
    return True


class PyO3TestHelper:
    """Helper class for PyO3-specific testing operations."""

    def __init__(self, db_path: str, load_mode: Any = None):
        """Initialize with database path.

        Args:
            db_path: Path to database file
            load_mode: LoadMode enum value
        """
        import pyrustkmer

        if load_mode is None:
            load_mode = pyrustkmer.LoadMode.Preload

        self.db = pyrustkmer.PyDatabase(db_path, load_mode)
        self.load_mode = load_mode

    def query_kmer(self, kmer: str) -> Dict[str, Any]:
        """Query a single k-mer and return result as dict.

        Args:
            kmer: DNA sequence to query

        Returns:
            Dictionary with query results
        """
        result = self.db.query(kmer)
        return {
            "count": result.count if hasattr(result, "count") else 0,
            "found": result.found if hasattr(result, "found") else False,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Dictionary with statistics
        """
        stats = self.db.get_stats()
        return {
            "kmer_size": stats.kmer_size if hasattr(stats, "kmer_size") else 0,
            "total_kmers": stats.total_kmers if hasattr(stats, "total_kmers") else 0,
            "unique_kmers": stats.unique_kmers if hasattr(stats, "unique_kmers") else 0,
        }

    def test_all_load_modes(self) -> Dict[str, bool]:
        """Test database loading in all available modes.

        Returns:
            Dictionary mapping LoadMode name to success status
        """
        import pyrustkmer

        results = {}

        for mode_name in ["Preload", "MemoryMapped", "Lazy"]:
            try:
                mode = getattr(pyrustkmer.LoadMode, mode_name)
                db = pyrustkmer.PyDatabase(self.db.path, mode)

                # Try a simple query
                result = db.query("AAAAAAA")

                results[mode_name] = True
            except Exception as e:
                results[mode_name] = False

        return results
