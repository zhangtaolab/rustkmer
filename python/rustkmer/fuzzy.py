"""
Fuzzy query functionality for wildcard and mutation-tolerant searches.

This module provides a Pythonic wrapper around the Rust implementation for
performing fuzzy queries with wildcards and Hamming distance tolerance.
"""

from typing import List, Dict, Optional, Any, Union
from .database import Database

# Import error handling utilities
from .error_handling import (
    handle_errors, ErrorContext, safe_execute, validate_inputs,
    validate_non_negative_int, validate_kmer_sequence
)
from .exceptions import FuzzyQueryError, ValidationError, DatabaseError

# Import from Rust extension
try:
    from ._rustkmer import FuzzyQuery as _RustFuzzyQuery
    from ._rustkmer import FuzzyQueryResult as _FuzzyQueryResult
    from ._rustkmer import FuzzyMatch as _FuzzyMatch
except ImportError:
    _RustFuzzyQuery = None
    _FuzzyQueryResult = None
    _FuzzyMatch = None


class FuzzyMatch:
    """
    Represents a single fuzzy match result.

    Attributes:
        kmer (str): The matching k-mer sequence
        count (int): The count of the k-mer in the database
        distance (int): Hamming distance from the query (0 for exact match)
    """

    def __init__(self, match: Union[_FuzzyMatch, tuple] = None):
        """Initialize from Rust FuzzyMatch or tuple."""
        if isinstance(match, _FuzzyMatch) if _FuzzyMatch is not None else False:
            # From Rust implementation
            self.kmer = match.kmer
            self.count = match.count
            self.distance = match.distance
        else:
            # From tuple or direct values
            if isinstance(match, tuple):
                self.kmer, self.count, self.distance = match
            else:
                self.kmer = ""
                self.count = 0
                self.distance = 0

    def __repr__(self) -> str:
        """
        Return string representation of the fuzzy match.

        Returns:
            str: String showing k-mer, count, and distance
        """
        return f"FuzzyMatch(kmer='{self.kmer}', count={self.count}, distance={self.distance})"


class FuzzyQueryResult:
    """
    Container for fuzzy query results.

    Provides convenient methods for accessing and analyzing fuzzy query matches.

    Attributes:
        query (str): The original query pattern or k-mer
        total_matches (int): Total number of matches found
    """

    def __init__(self, result: Union[_FuzzyQueryResult, str] = None):
        """Initialize from Rust FuzzyQueryResult or query string."""
        if isinstance(result, _FuzzyQueryResult) if _FuzzyQueryResult is not None else False:
            # From Rust implementation
            self._rust_result = result
            self.query = result.query
            self.total_matches = result.total_matches
        else:
            # Create empty result
            self._rust_result = None
            self.query = result if isinstance(result, str) else ""
            self.total_matches = 0
            self._matches = []

    def get_matches(self) -> List[FuzzyMatch]:
        """
        Get all matches as FuzzyMatch objects.

        Returns:
            List[FuzzyMatch]: List of all matches found in the query
        """
        if self._rust_result is not None:
            # From Rust implementation
            return [FuzzyMatch(m) for m in self._rust_result.get_matches()]
        else:
            # Python fallback
            return self._matches

    def get_match(self, index: int) -> Optional[FuzzyMatch]:
        """
        Get match at specific index.

        Args:
            index: Index of the match to retrieve

        Returns:
            Optional[FuzzyMatch]: Match at the given index, or None if index is out of range

        Example:
            >>> result = fq.search("ATCG*")
            >>> first_match = result.get_match(0)
            >>> if first_match:
            ...     print(f"Found: {first_match.kmer} with count {first_match.count}")
        """
        matches = self.get_matches()
        if 0 <= index < len(matches):
            return matches[index]
        return None

    def get_matches_by_distance(self) -> Dict[int, List[FuzzyMatch]]:
        """
        Group matches by Hamming distance.

        Returns:
            Dict[int, List[FuzzyMatch]]: Dictionary mapping distance to list of matches

        Example:
            >>> result = fq.search("ATCG*")
            >>> by_dist = result.get_matches_by_distance()
            >>> for distance, matches in by_dist.items():
            ...     print(f"Distance {distance}: {len(matches)} matches")
        """
        matches_by_distance = {}
        for match in self.get_matches():
            distance = match.distance
            if distance not in matches_by_distance:
                matches_by_distance[distance] = []
            matches_by_distance[distance].append(match)
        return matches_by_distance

    def get_exact_matches(self) -> List[FuzzyMatch]:
        """
        Get only exact matches (distance = 0).

        Returns:
            List[FuzzyMatch]: List of matches with zero Hamming distance
        """
        return [m for m in self.get_matches() if m.distance == 0]

    def get_fuzzy_matches(self, max_distance: Optional[int] = None) -> List[FuzzyMatch]:
        """
        Get fuzzy (non-exact) matches.

        Args:
            max_distance: Maximum distance to include (None for no limit)

        Returns:
            List[FuzzyMatch]: List of non-exact matches within distance range

        Example:
            >>> result = fq.search("ATCG*")
            >>> # All fuzzy matches
            >>> fuzzy = result.get_fuzzy_matches()
            >>> # Fuzzy matches within distance 2
            >>> fuzzy_2 = result.get_fuzzy_matches(max_distance=2)
        """
        matches = [m for m in self.get_matches() if m.distance > 0]
        if max_distance is not None:
            matches = [m for m in matches if m.distance <= max_distance]
        return matches

    def get_top_matches(self, n: int, by: str = 'count') -> List[FuzzyMatch]:
        """
        Get top n matches sorted by count or distance.

        Args:
            n: Number of matches to return
            by: Sort by 'count' (default) or 'distance'

        Returns:
            List of top matches
        """
        matches = self.get_matches()
        if by == 'count':
            matches.sort(key=lambda m: m.count, reverse=True)
        elif by == 'distance':
            matches.sort(key=lambda m: (m.distance, -m.count))
        else:
            raise ValueError("by must be 'count' or 'distance'")

        return matches[:n]

    def to_dict(self) -> List[Dict[str, Any]]:
        """Convert matches to list of dictionaries."""
        return [
            {
                "kmer": m.kmer,
                "count": m.count,
                "distance": m.distance
            }
            for m in self.get_matches()
        ]

    def __len__(self) -> int:
        """Return number of matches."""
        return self.total_matches

    def __iter__(self):
        """Iterate over matches."""
        return iter(self.get_matches())

    def __repr__(self) -> str:
        return f"FuzzyQueryResult(query='{self.query}', total_matches={self.total_matches})"


class FuzzyQuery:
    """
    Python wrapper for fuzzy query operations on k-mer databases.

    Provides high-level interface for:
    - Wildcard pattern matching with *
    - Hamming distance similarity search
    - Batch queries for performance

    Example:
        >>> from rustkmer import Database, FuzzyQuery
        >>> db = Database("my_database.rkdb")
        >>> fq = FuzzyQuery(database=db, max_distance=2)
        >>>
        >>> # Wildcard search
        >>> results = fq.search("ATCG*ATCG", max_results=10)
        >>> for match in results:
        ...     print(f"{match.kmer}: {match.count}")
        >>>
        >>> # Similarity search
        >>> similar = fq.find_similar("ATCGATCGATCGATCGATCGATC")
        >>> print(f"Found {len(similar)} similar k-mers")
    """

    def __init__(self, database: Optional[Database] = None, max_distance: int = 1):
        """
        Initialize fuzzy query.

        Args:
            database: Database instance to query (optional)
            max_distance: Maximum Hamming distance for similarity search (1-31)

        Raises:
            ValueError: If max_distance > 31
        """
        if _RustFuzzyQuery is None:
            raise RuntimeError("Rust implementation not available")

        # Convert Database to SimpleDatabase for Rust
        rust_db = None
        if database is not None:
            # Access the underlying SimpleDatabase
            rust_db = database._db

        self._rust_fq = _RustFuzzyQuery(database=rust_db, max_distance=max_distance)
        self.database = database

    def set_database(self, database: Database) -> None:
        """
        Set the database for queries.

        Args:
            database: Database instance to query
        """
        self.database = database
        self._rust_fq.set_database(database._db)

    @handle_errors("fuzzy_search")
    @validate_inputs({
        'pattern': lambda x: isinstance(x, str) and len(x) > 0,
        'max_results': lambda x: x is None or (isinstance(x, int) and x > 0)
    })
    def search(self, pattern: str, max_results: Optional[int] = None) -> FuzzyQueryResult:
        """
        Search for k-mers matching a wildcard pattern.

        The wildcard character (*) matches any nucleotide (A, T, C, or G).
        Multiple wildcards are supported but limited to prevent combinatorial explosion.

        Args:
            pattern: Search pattern with * as wildcard
            max_results: Maximum number of results to return (None for no limit)

        Returns:
            FuzzyQueryResult containing all matching k-mers

        Raises:
            FuzzyQueryError: If search fails or database not set
            ValidationError: If pattern or max_results is invalid
            DatabaseError: If no database is set

        Example:
            >>> results = fq.search("ATCG*ATCG", max_results=10)
            >>> print(f"Found {results.total_matches} matches")
            >>> for match in results:
            ...     print(f"{match.kmer} (distance {match.distance}): {match.count}")
        """
        # Check if database is set
        if not self.database:
            raise DatabaseError(
                "No database set. Call set_database() first.",
                error_code="DATABASE_NOT_SET"
            )

        # Validate pattern - check for too many wildcards
        wildcard_count = pattern.count('*')
        if wildcard_count > 8:
            raise ValidationError(
                f"Pattern has too many wildcards ({wildcard_count} > 8). This may cause combinatorial explosion.",
                error_code="TOO_MANY_WILDCARDS",
                parameter="pattern",
                wildcard_count=wildcard_count,
                max_allowed=8
            )

        # Validate pattern characters
        for char in pattern.upper():
            if char not in 'ATCG*':
                raise ValidationError(
                    f"Pattern contains invalid character '{char}'. Only A, T, C, G, and * are allowed.",
                    error_code="INVALID_PATTERN_CHAR",
                    parameter="pattern",
                    invalid_char=char
                )

        # Create error context
        context = ErrorContext(
            operation="fuzzy_search",
            component="FuzzyQuery.search",
            additional_info={
                "pattern": pattern,
                "wildcard_count": wildcard_count,
                "max_results": max_results
            }
        )

        # Execute search with error handling
        try:
            rust_result = safe_execute(
                self._rust_fq.search,
                pattern,
                max_results,
                log_errors=True
            )
            return FuzzyQueryResult(rust_result)
        except Exception as e:
            raise FuzzyQueryError(
                f"Fuzzy search failed for pattern '{pattern}': {str(e)}",
                error_code="FUZZY_SEARCH_FAILED",
                pattern=pattern,
                max_results=max_results,
                context=context.to_dict()
            ) from e

    @handle_errors("fuzzy_find_similar")
    @validate_inputs({
        'kmer': validate_kmer_sequence,
        'max_results': lambda x: x is None or (isinstance(x, int) and x > 0)
    })
    def find_similar(self, kmer: str, max_results: Optional[int] = None) -> FuzzyQueryResult:
        """
        Find k-mers similar to the given k-mer within max_distance.

        Similarity is measured by Hamming distance (number of differing positions).
        The exact match (distance 0) is always included if it exists.

        Args:
            kmer: Query k-mer
            max_results: Maximum number of results to return (None for no limit)

        Returns:
            FuzzyQueryResult containing similar k-mers with their distances

        Raises:
            FuzzyQueryError: If similarity search fails or database not set
            ValidationError: If kmer or max_results is invalid
            DatabaseError: If no database is set

        Example:
            >>> similar = fq.find_similar("ATCGATCGATCGATCGATCGATC", max_results=20)
            >>> exact = similar.get_exact_matches()
            >>> fuzzy = similar.get_fuzzy_matches(max_distance=2)
            >>> print(f"Exact: {len(exact)}, Fuzzy: {len(fuzzy)}")
        """
        # Check if database is set
        if not self.database:
            raise DatabaseError(
                "No database set. Call set_database() first.",
                error_code="DATABASE_NOT_SET"
            )

        # Check k-mer length matches database
        if len(kmer) != self.database.kmer_size:
            raise ValidationError(
                f"K-mer length ({len(kmer)}) doesn't match database k-mer size ({self.database.kmer_size})",
                error_code="INVALID_KMER_LENGTH",
                parameter="kmer",
                expected_value=self.database.kmer_size,
                actual_value=len(kmer)
            )

        # Create error context
        context = ErrorContext(
            operation="fuzzy_find_similar",
            component="FuzzyQuery.find_similar",
            additional_info={
                "kmer": kmer,
                "kmer_length": len(kmer),
                "max_results": max_results
            }
        )

        # Execute similarity search with error handling
        try:
            rust_result = safe_execute(
                self._rust_fq.find_similar,
                kmer,
                max_results,
                log_errors=True
            )
            return FuzzyQueryResult(rust_result)
        except Exception as e:
            raise FuzzyQueryError(
                f"Fuzzy similarity search failed for k-mer '{kmer}': {str(e)}",
                error_code="FUZZY_SIMILARITY_FAILED",
                kmer_sequence=kmer,
                max_results=max_results,
                context=context.to_dict()
            ) from e

    def query_batch(self, queries: List[str], max_results_per_query: Optional[int] = None) -> List[FuzzyQueryResult]:
        """
        Query multiple patterns or k-mers in a single call for better performance.

        Automatically detects whether each query contains wildcards and uses the
        appropriate search method.

        Args:
            queries: List of query patterns or k-mers
            max_results_per_query: Maximum results per query (None for no limit)

        Returns:
            List of FuzzyQueryResult objects, one for each query

        Example:
            >>> queries = [
            ...     "ATCG*ATCG",  # Wildcard
            ...     "GCTAGCTAGCTAGCTAGCTAG",  # Exact
            ...     "CCCCCCCCCCCCCCCCCCCCCCC"  # Exact
            ... ]
            >>> results = fq.query_batch(queries)
            >>> for i, result in enumerate(results):
            ...     print(f"Query {i}: {result.total_matches} matches")
        """
        if not self.database:
            raise RuntimeError("No database set. Call set_database() first.")

        rust_results = self._rust_fq.query_batch(queries, max_results_per_query)
        return [FuzzyQueryResult(r) for r in rust_results]

    def set_max_distance(self, max_distance: int) -> None:
        """
        Set maximum Hamming distance for similarity searches.

        Args:
            max_distance: New maximum distance (1-31)

        Raises:
            ValueError: If max_distance > 31
        """
        self._rust_fq.set_max_distance(max_distance)

    def get_max_distance(self) -> int:
        """Get current maximum Hamming distance."""
        return self._rust_fq.get_max_distance()

    def get_kmer_size(self) -> int:
        """Get k-mer size of the loaded database."""
        if not self.database:
            raise RuntimeError("No database set. Call set_database() first.")
        return self._rust_fq.get_kmer_size()

    def is_canonical(self) -> bool:
        """Check if the database uses canonical k-mers."""
        if not self.database:
            raise RuntimeError("No database set. Call set_database() first.")
        return self._rust_fq.is_canonical()

    def __repr__(self) -> str:
        """String representation of FuzzyQuery."""
        if self.database:
            return (f"FuzzyQuery(k={self.get_kmer_size()}, "
                   f"max_distance={self.get_max_distance()}, "
                   f"canonical={self.is_canonical()})")
        return "FuzzyQuery(no database)"


# Re-export Rust classes for direct use if needed
if _RustFuzzyQuery is not None:
    FuzzyQueryResult = _FuzzyQueryResult
    FuzzyMatch = _FuzzyMatch


# Convenience functions
def fuzzy_search(database_path: str, pattern: str, max_results: Optional[int] = None,
                  max_distance: int = 1) -> FuzzyQueryResult:
    """
    Convenience function to perform a single fuzzy search.

    Args:
        database_path: Path to the .rkdb database file
        pattern: Search pattern with wildcards
        max_results: Maximum number of results
        max_distance: Maximum Hamming distance

    Returns:
        FuzzyQueryResult with matching k-mers

    Example:
        >>> from rustkmer.fuzzy import fuzzy_search
        >>> results = fuzzy_search("my_db.rkdb", "ATCG*ATCG", max_results=10)
    """
    with Database(database_path) as db:
        fq = FuzzyQuery(database=db, max_distance=max_distance)
        return fq.search(pattern, max_results)


def find_similar_kmers(database_path: str, kmer: str, max_distance: int = 1,
                       max_results: Optional[int] = None) -> FuzzyQueryResult:
    """
    Convenience function to find similar k-mers.

    Args:
        database_path: Path to the .rkdb database file
        kmer: Query k-mer
        max_distance: Maximum Hamming distance
        max_results: Maximum number of results

    Returns:
        FuzzyQueryResult with similar k-mers

    Example:
        >>> from rustkmer.fuzzy import find_similar_kmers
        >>> similar = find_similar_kmers("my_db.rkdb", "ATCGATCGATCGATCGATCGATC", max_distance=2)
    """
    with Database(database_path) as db:
        fq = FuzzyQuery(database=db, max_distance=max_distance)
        return fq.find_similar(kmer, max_results)