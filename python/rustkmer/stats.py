"""DatabaseStats and related classes for rustkmer Python bindings."""

from dataclasses import dataclass
from typing import Dict, Union


@dataclass
class DatabaseStats:
    """Statistics about a k-mer database.

    This class contains metadata about the database such as k-mer size,
    number of unique k-mers, and file information.

    Attributes:
        kmer_size: Length of k-mers in the database
        unique_kmers: Number of unique k-mer sequences
        total_counts: Sum of all k-mer counts
        min_count: Minimum count for any single k-mer
        max_count: Maximum count for any single k-mer
        file_size: Size of database file in bytes
        format_version: Version of the database format
    """
    kmer_size: int
    unique_kmers: int
    total_counts: int
    min_count: int
    max_count: int
    file_size: int
    format_version: str

    def to_dict(self) -> Dict[str, Union[str, int]]:
        """Convert to dictionary representation."""
        return {
            'kmer_size': self.kmer_size,
            'unique_kmers': self.unique_kmers,
            'total_counts': self.total_counts,
            'min_count': self.min_count,
            'max_count': self.max_count,
            'file_size': self.file_size,
            'format_version': self.format_version
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        import json
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, int]]) -> 'DatabaseStats':
        """Create DatabaseStats from dictionary."""
        return cls(
            kmer_size=int(data.get('kmer_size', 0)),
            unique_kmers=int(data.get('unique_kmers', 0)),
            total_counts=int(data.get('total_counts', 0)),
            min_count=int(data.get('min_count', 0)),
            max_count=int(data.get('max_count', 0)),
            file_size=int(data.get('file_size', 0)),
            format_version=str(data.get('format_version', 'unknown'))
        )

    @property
    def average_count(self) -> float:
        """Calculate average k-mer count."""
        if self.unique_kmers == 0:
            return 0.0
        return self.total_counts / self.unique_kmers

    def __str__(self) -> str:
        """String representation."""
        return (
            f"DatabaseStats(k={self.kmer_size}, "
            f"unique={self.unique_kmers}, "
            f"total={self.total_counts})"
        )