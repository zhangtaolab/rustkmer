"""
Statistics and result types for RustKmer operations.

This module contains data classes for representing query results,
statistics, and metadata from k-mer counting and database operations.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

# Placeholder classes for development
@dataclass
class QueryResult:
    """Result from a single k-mer query operation.

    Attributes:
        kmer: The queried k-mer sequence (uppercase)
        count: The number of occurrences of this k-mer
        found: Whether the k-mer was found in the database
        distance: Edit distance from query (for fuzzy queries, 0 for exact queries)
    """
    kmer: str
    count: int
    found: bool
    distance: int = 0  # Default to 0 for exact queries

    @property
    def exists(self) -> bool:
        """Alias for found property for compatibility with documentation."""
        return self.found

@dataclass
class FuzzyQueryResult:
    """Results from fuzzy query operations with match details.

    Attributes:
        kmer: The matching k-mer sequence found in the database
        count: The number of occurrences of this k-mer
        distance: Edit distance from the original query pattern
        pattern: The original query pattern (may contain wildcards)
        matched_positions: List of positions where substitutions occurred
    """
    kmer: str
    count: int
    distance: int
    pattern: str
    matched_positions: Optional[List[int]] = None

@dataclass
class CounterStats:
    """Statistics for k-mer counting operations.

    Attributes:
        total_kmers: Total number of unique k-mers
        total_count: Total k-mer occurrences
        average_count: Average k-mer count
        median_count: Median k-mer count
        max_count: Maximum k-mer count
    """
    total_kmers: int
    total_count: int
    average_count: float
    median_count: float
    max_count: int

@dataclass
class DatabaseStats:
    """Statistics and metadata for a k-mer database.

    Attributes:
        kmer_size: The length of k-mers stored in the database
        total_kmers: Total number of k-mer occurrences (including duplicates)
        unique_kmers: Number of unique k-mer sequences
        sorted: Whether the database is sorted for efficient querying
        canonical: Whether the database stores canonical k-mers
        preloaded: Whether the database is preloaded into memory
        filename: The path to the database file
    """
    kmer_size: int
    total_kmers: int
    unique_kmers: int
    sorted: bool
    canonical: bool
    preloaded: bool
    filename: str