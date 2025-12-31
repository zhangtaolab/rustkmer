"""QueryResult and related classes for rustkmer Python bindings."""

from dataclasses import dataclass
from typing import Dict, Union


@dataclass
class QueryResult:
    """Result of a k-mer query.

    Attributes:
        kmer: The queried k-mer sequence
        count: Number of occurrences in the database
        canonical: Canonical representation of the k-mer
    """
    kmer: str
    count: int
    canonical: str

    @property
    def is_present(self) -> bool:
        """Check if the k-mer exists in the database."""
        return self.count > 0

    def to_dict(self) -> Dict[str, Union[str, int]]:
        """Convert to dictionary representation."""
        return {
            'kmer': self.kmer,
            'count': self.count,
            'canonical': self.canonical
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        import json
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, int]]) -> 'QueryResult':
        """Create QueryResult from dictionary."""
        return cls(
            kmer=str(data.get('kmer', '')),
            count=int(data.get('count', 0)),
            canonical=str(data.get('canonical', data.get('kmer', '')))
        )

    def __str__(self) -> str:
        """String representation."""
        return f"{self.kmer}: {self.count}"