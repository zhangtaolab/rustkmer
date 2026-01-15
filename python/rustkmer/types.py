"""Unified type definitions for rustkmer Python bindings.

This module provides a centralized location for all type definitions used
across the rustkmer Python API, ensuring consistency and making imports easier.

The types defined here are simplified versions designed for ease of use
while maintaining API compatibility with existing rustkmer classes.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

# Import exceptions for convenience
from .exceptions import (
    RustKmerError,
    DatabaseError,
    DatabaseNotFoundError,
    InvalidDatabaseError,
    DatabaseCorruptedError,
    QueryError,
    InvalidKmerError,
    KmerLengthError,
    FuzzyQueryError,
    InvalidMutationToleranceError,
    InvalidPositionMutationError,
    CombinatorialExplosionError,
    BatchQueryError,
    SubprocessError,
    ConfigurationError,
)


@dataclass
class QueryResult:
    """Unified query result type for k-mer database queries.

    This class represents result of querying a single k-mer in the database.
    It provides information about the k-mer, its count, and its canonical form.

    Attributes:
        kmer: The queried k-mer sequence
        count: Number of occurrences in the database
        canonical: Canonical representation of the k-mer (if available)
        found: Whether the k-mer was found in the database

    Example:
        >>> result = QueryResult("ATCGATCG", 10, "ATCGATCG", True)
        >>> print(f"{result.kmer}: {result.count}")
        >>> ATCGATCG: 10
    """

    kmer: str
    count: int
    canonical: Optional[str] = None
    found: bool = False

    @property
    def is_present(self) -> bool:
        """Check if the k-mer exists in the database."""
        return self.count > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "kmer": self.kmer,
            "count": self.count,
            "canonical": self.canonical,
            "found": self.found,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        import json

        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryResult":
        """Create QueryResult from dictionary."""
        return cls(
            kmer=str(data.get("kmer", "")),
            count=int(data.get("count", 0)),
            canonical=str(data.get("canonical", "")) or None,
            found=bool(data.get("found", data.get("count", 0) > 0)),
        )

    def __str__(self) -> str:
        """String representation."""
        if self.found:
            return f"{self.kmer}: {self.count}"
        return f"{self.kmer}: not found"


@dataclass
class DatabaseStats:
    """Unified database statistics type.

    This class contains comprehensive metadata about a k-mer database,
    including k-mer size, counts, and file information.

    Attributes:
        kmer_size: Length of k-mers in the database
        total_kmers: Total number of k-mer entries (including duplicates)
        unique_kmers: Number of unique k-mer sequences
        file_size: Size of database file in bytes
        is_sorted: Whether the database is sorted
        is_canonical: Whether canonical k-mers are used

    Example:
        >>> stats = DatabaseStats(21, 1000000, 500000, 2097152, True, True)
        >>> print(f"Database has {stats.unique_kmers} unique k-mers")
    """

    kmer_size: int
    total_kmers: int
    unique_kmers: int
    file_size: int
    is_sorted: bool = False
    is_canonical: bool = False

    @property
    def average_count(self) -> float:
        """Calculate average k-mer count."""
        if self.unique_kmers == 0:
            return 0.0
        return self.total_kmers / self.unique_kmers

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "kmer_size": self.kmer_size,
            "total_kmers": self.total_kmers,
            "unique_kmers": self.unique_kmers,
            "file_size": self.file_size,
            "is_sorted": self.is_sorted,
            "is_canonical": self.is_canonical,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        import json

        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatabaseStats":
        """Create DatabaseStats from dictionary."""
        return cls(
            kmer_size=int(data.get("kmer_size", 0)),
            total_kmers=int(data.get("total_kmers", 0)),
            unique_kmers=int(data.get("unique_kmers", 0)),
            file_size=int(data.get("file_size", 0)),
            is_sorted=bool(data.get("is_sorted", False)),
            is_canonical=bool(data.get("is_canonical", False)),
        )

    def __str__(self) -> str:
        """String representation."""
        return (
            f"DatabaseStats(k={self.kmer_size}, "
            f"unique={self.unique_kmers:,}, "
            f"total={self.total_kmers:,})"
        )


@dataclass
class FuzzyMatch:
    """Simplified fuzzy match result type.

    This class represents a single k-mer match within mutation tolerance.
    It's a simplified version designed for ease of use.

    Attributes:
        kmer: The matched k-mer sequence
        count: Number of occurrences in the database
        distance: Hamming distance from the query (0 = exact match)
        match_type: Type of match ('exact' or 'fuzzy')

    Example:
        >>> match = FuzzyMatch("ATCG", 10, 0, "exact")
        >>> print(f"{match.kmer}: {match.count} ({match.match_type})")
    """

    kmer: str
    count: int
    distance: Optional[int] = None
    match_type: str = "exact"

    @property
    def is_exact_match(self) -> bool:
        """Check if this is an exact match."""
        return (
            self.distance == 0
            if self.distance is not None
            else self.match_type == "exact"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "kmer": self.kmer,
            "count": self.count,
            "distance": self.distance,
            "match_type": self.match_type,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        import json

        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FuzzyMatch":
        """Create FuzzyMatch from dictionary."""
        distance_value = data.get("distance")
        distance = int(distance_value) if distance_value is not None else None
        return cls(
            kmer=str(data.get("kmer", "")),
            count=int(data.get("count", 0)),
            distance=distance,
            match_type=str(data.get("match_type", "exact")),
        )


@dataclass
class FuzzyResult:
    """Simplified fuzzy query result type.

    This class aggregates all matching k-mers found within mutation tolerance.
    It's a simplified version designed for ease of use.

    Attributes:
        query: The original query k-mer
        exact_match: The exact match if found (distance = 0)
        matches: List of all matches found
        total_matches: Total number of unique k-mer matches
        mutation_tolerance: Maximum Hamming distance allowed
        has_position_mutations: Whether position-specific constraints were used

    Example:
        >>> result = FuzzyResult("ATCG", exact_match=None,
        ...                        matches=[], total_matches=0,
        ...                        mutation_tolerance=2)
        >>> print(f"Found {result.total_matches} matches")
    """

    query: str
    exact_match: Optional[FuzzyMatch] = None
    matches: List[FuzzyMatch] = field(default_factory=list)
    total_matches: int = 0
    mutation_tolerance: int = 0
    has_position_mutations: bool = False

    @property
    def has_exact_match(self) -> bool:
        """Check if an exact match was found."""
        return self.exact_match is not None

    @property
    def fuzzy_matches(self) -> List[FuzzyMatch]:
        """Get all non-exact matches."""
        return [m for m in self.matches if not m.is_exact_match]

    @property
    def match_count(self) -> int:
        """Calculate total count of all matched k-mers."""
        return sum(m.count for m in self.matches)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "query": self.query,
            "exact_match": self.exact_match.to_dict() if self.exact_match else None,
            "matches": [m.to_dict() for m in self.matches],
            "total_matches": self.total_matches,
            "mutation_tolerance": self.mutation_tolerance,
            "has_position_mutations": self.has_position_mutations,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        import json

        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FuzzyResult":
        """Create FuzzyResult from dictionary."""
        exact_data = data.get("exact_match")
        exact_match = FuzzyMatch.from_dict(exact_data) if exact_data else None

        matches_data = data.get("matches", [])
        matches = [FuzzyMatch.from_dict(m) for m in matches_data]

        return cls(
            query=str(data.get("query", "")),
            exact_match=exact_match,
            matches=matches,
            total_matches=int(data.get("total_matches", 0)),
            mutation_tolerance=int(data.get("mutation_tolerance", 0)),
            has_position_mutations=bool(data.get("has_position_mutations", False)),
        )


@dataclass
class CounterStats:
    """Statistics for k-mer counter operations.

    This class provides metadata about k-mer counting operations,
    similar to DatabaseStats but focused on the counting context.

    Attributes:
        unique_kmers: Number of unique k-mer sequences counted
        total_kmers: Total k-mer count (including duplicates)
        kmer_size: Length of k-mers being counted
        is_canonical: Whether canonical k-mers are being used

    Example:
        >>> stats = CounterStats(500000, 1000000, 21, True)
        >>> print(f"Counted {stats.unique_kmers} unique k-mers")
    """

    unique_kmers: int
    total_kmers: int
    kmer_size: int
    is_canonical: bool = False

    @property
    def average_count(self) -> float:
        """Calculate average k-mer count."""
        if self.unique_kmers == 0:
            return 0.0
        return self.total_kmers / self.unique_kmers

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "unique_kmers": self.unique_kmers,
            "total_kmers": self.total_kmers,
            "kmer_size": self.kmer_size,
            "is_canonical": self.is_canonical,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        import json

        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CounterStats":
        """Create CounterStats from dictionary."""
        return cls(
            unique_kmers=int(data.get("unique_kmers", 0)),
            total_kmers=int(data.get("total_kmers", 0)),
            kmer_size=int(data.get("kmer_size", 0)),
            is_canonical=bool(data.get("is_canonical", False)),
        )

    def __str__(self) -> str:
        """String representation."""
        return (
            f"CounterStats(k={self.kmer_size}, "
            f"unique={self.unique_kmers:,}, "
            f"total={self.total_kmers:,})"
        )


class LoadMode(Enum):
    """Database loading mode enumeration.

    Defines different strategies for loading k-mer databases into memory,
    affecting performance and memory usage.

    Attributes:
        PRELOAD: Load entire database into memory (fastest, highest memory)
        MEMORY_MAPPED: Use memory-mapped file access (balanced)
        LAZY: Load data on-demand (lowest memory, slower access)

    Example:
        >>> mode = LoadMode.PRELOAD
        >>> print(f"Using mode: {mode.value}")
    """

    PRELOAD = "preload"
    """Load entire database into memory for fastest access.

    Best for:
        - Small databases (< 2GB)
        - Frequent queries
        - Maximum performance needed
    """

    MEMORY_MAPPED = "memory_mapped"
    """Use memory-mapped file access for balanced performance.

    Best for:
        - Medium databases (2GB - 10GB)
        - Balanced memory usage
        - Good performance with reasonable memory footprint
    """

    LAZY = "lazy"
    """Load data on-demand for minimal memory usage.

    Best for:
        - Large databases (> 10GB)
        - Memory-constrained environments
        - Infrequent queries
    """

    def __str__(self) -> str:
        """String representation."""
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "LoadMode":
        """Create LoadMode from string value."""
        for mode in cls:
            if mode.value == value.lower():
                return mode
        raise ValueError(
            f"Invalid LoadMode value: {value}. Must be one of: {[m.value for m in cls]}"
        )


__all__ = [
    # Result types
    "QueryResult",
    "DatabaseStats",
    "FuzzyMatch",
    "FuzzyResult",
    "CounterStats",
    # Enums
    "LoadMode",
    # Exceptions
    "RustKmerError",
    "DatabaseError",
    "DatabaseNotFoundError",
    "InvalidDatabaseError",
    "DatabaseCorruptedError",
    "QueryError",
    "InvalidKmerError",
    "KmerLengthError",
    "FuzzyQueryError",
    "InvalidMutationToleranceError",
    "InvalidPositionMutationError",
    "CombinatorialExplosionError",
    "BatchQueryError",
    "SubprocessError",
    "ConfigurationError",
]
