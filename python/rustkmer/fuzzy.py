"""
Fuzzy query functionality for wildcard and mutation-tolerant searches.

This module provides classes for performing fuzzy queries with wildcards
and mutation tolerance to find similar k-mers.
"""

from typing import List, Dict, Optional, Any
import itertools

# Import from Rust extension if available
try:
    from ._rustkmer import FuzzyQuery as _FuzzyQuery
    from ._rustkmer import FuzzyQueryResult as _FuzzyQueryResult
    from ._rustkmer import FuzzyMatch as _FuzzyMatch

    # Re-export Rust classes
    FuzzyQuery = _FuzzyQuery
    FuzzyQueryResult = _FuzzyQueryResult
    FuzzyMatch = _FuzzyMatch

except ImportError:
    # Python fallback implementations for development
    class FuzzyMatch:
        """Represents a single fuzzy match result."""

        def __init__(self, kmer: str, count: int, distance: int):
            self.kmer = kmer
            self.count = count
            self.distance = distance

        def __repr__(self) -> str:
            return f"FuzzyMatch(kmer='{self.kmer}', count={self.count}, distance={self.distance})"

    class FuzzyQueryResult:
        """Container for fuzzy query results."""

        def __init__(self, query: str):
            self.query = query
            self.total_matches = 0
            self.matches: List[FuzzyMatch] = []

        def add_match(self, kmer: str, count: int, distance: int):
            """Add a match to the results."""
            self.matches.append(FuzzyMatch(kmer, count, distance))
            self.total_matches += 1

        def get_matches(self) -> List[FuzzyMatch]:
            """Get all matches."""
            return self.matches

        def get_match(self, index: int) -> Optional[FuzzyMatch]:
            """Get match at specific index."""
            if 0 <= index < len(self.matches):
                return self.matches[index]
            return None

        def to_dict(self) -> List[Dict[str, Any]]:
            """Convert matches to list of dictionaries."""
            return [
                {
                    "kmer": m.kmer,
                    "count": m.count,
                    "distance": m.distance
                }
                for m in self.matches
            ]

        def __repr__(self) -> str:
            return f"FuzzyQueryResult(query='{self.query}', total_matches={self.total_matches})"

    class FuzzyQuery:
        """Fuzzy query implementation for wildcard and mutation-tolerant searches."""

        def __init__(self, database=None, max_distance: int = 1):
            """
            Initialize fuzzy query.

            Args:
                database: Database instance to query
                max_distance: Maximum edit distance for matches
            """
            self.database = database
            self.max_distance = max_distance

        def set_database(self, database):
            """Set the database for queries."""
            self.database = database

        def search(self, pattern: str, max_results: Optional[int] = None) -> FuzzyQueryResult:
            """
            Search for k-mers matching a wildcard pattern.

            Args:
                pattern: Pattern with wildcards (*)
                max_results: Maximum number of results to return

            Returns:
                FuzzyQueryResult with matching k-mers
            """
            result = FuzzyQueryResult(pattern)

            if self.database is None:
                return result

            # Expand wildcards
            expanded_patterns = self._expand_pattern(pattern)

            # Query each expanded pattern
            for expanded in expanded_patterns[:max_results or 1000]:
                if len(expanded) == self.database.kmer_size:
                    query_result = self.database.query(expanded)
                    if query_result.found:
                        result.add_match(expanded, query_result.count, 0)

                        # Check if we've reached max_results
                        if max_results and len(result.matches) >= max_results:
                            break

            return result

        def find_similar(self, kmer: str, max_results: Optional[int] = None) -> FuzzyQueryResult:
            """
            Find k-mers similar to the given k-mer within max_distance.

            Args:
                kmer: K-mer to find neighbors for
                max_results: Maximum number of results to return

            Returns:
                FuzzyQueryResult with similar k-mers
            """
            result = FuzzyQueryResult(kmer)

            if self.database is None:
                return result

            # Add exact match
            query_result = self.database.query(kmer)
            if query_result.found:
                result.add_match(kmer, query_result.count, 0)

            # Generate neighbors within max_distance
            if self.max_distance > 0:
                neighbors = self._generate_neighbors(kmer, self.max_distance)

                for neighbor, distance in neighbors[:max_results or 100]:
                    if neighbor != kmer:  # Skip exact match (already added)
                        query_result = self.database.query(neighbor)
                        if query_result.found:
                            result.add_match(neighbor, query_result.count, distance)

                        # Check if we've reached max_results
                        if max_results and len(result.matches) >= max_results:
                            break

            return result

        def _expand_pattern(self, pattern: str) -> List[str]:
            """
            Expand wildcard pattern to all possible k-mers.

            Args:
                pattern: Pattern with * wildcards

            Returns:
                List of expanded k-mers
            """
            if '*' not in pattern:
                return [pattern]

            # Split pattern by wildcards
            parts = pattern.split('*')

            # For now, just return the pattern without wildcards
            # A full implementation would generate all combinations
            return [pattern.replace('*', '')]

        def _generate_neighbors(self, kmer: str, distance: int) -> List[tuple[str, int]]:
            """
            Generate all k-mers within edit distance.

            Args:
                kmer: Original k-mer
                distance: Maximum edit distance

            Returns:
                List of (neighbor_kmer, distance) tuples
            """
            neighbors = []
            nucleotides = ['A', 'T', 'G', 'C']

            if distance >= 1:
                # Generate all single substitutions
                for i in range(len(kmer)):
                    for n in nucleotides:
                        if n != kmer[i]:
                            neighbor = kmer[:i] + n + kmer[i+1:]
                            neighbors.append((neighbor, 1))

            # For distance > 1, this would need recursive generation
            # For now, only handle distance = 1

            return neighbors