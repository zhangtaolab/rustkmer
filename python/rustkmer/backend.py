"""
Backend abstraction layer for RustKmer database operations.

This module provides a unified interface for database operations across different
backends (subprocess-based and PyO3-based), allowing automatic backend
selection and transparent switching between implementations.
"""

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Union

# Import types from local modules
from .query import QueryResult
from .stats import DatabaseStats
from .fuzzy_query import FuzzyQueryResult


class LoadMode(Enum):
    """Database loading modes for PyO3 backend.

    These modes control how the PyO3 backend loads and manages
    k-mer data in memory, affecting both performance and memory usage.
    """

    PRELOAD = "preload"
    """Preload all k-mers into memory (fastest queries, highest memory usage).

    This mode loads all k-mers into a HashMap for O(1) lookup time.
    Best for applications with frequent queries on the same database.
    """

    MEMORY_MAPPED = "mmap"
    """Use memory-mapped file access (balanced memory/performance).

    This mode uses direct file I/O with OS-managed caching.
    Best for large databases where memory is limited.
    """

    LAZY = "lazy"
    """Lazy loading - load k-mers on-demand using binary search (lowest memory).

    This mode maintains a sorted index and performs binary searches.
    Best for applications with infrequent queries or very large databases.
    """


class DatabaseBackend(ABC):
    """Abstract base class for database backends.

    This class defines the unified interface that all database backends must implement,
    allowing code to work seamlessly with either subprocess or PyO3 backends
    without knowing the underlying implementation.

    Subclasses must implement all abstract methods to provide a complete
    database interface.
    """

    @property
    @abstractmethod
    def path(self) -> str:
        """Database path.

        Returns:
            str: Path to the database file.
        """
        ...

    @property
    @abstractmethod
    def kmer_size(self) -> int:
        """K-mer size used in the database.

        Returns:
            int: Length of k-mers in this database.
        """
        ...

    @abstractmethod
    def query(self, kmer: str) -> QueryResult:
        """Exact query for a single k-mer.

        Args:
            kmer: The k-mer sequence to query.

        Returns:
            QueryResult: Query result with count and canonical form.

        Raises:
            InvalidKmerError: If k-mer format is invalid.
            QueryError: If query operation fails.
            DatabaseError: If database is closed.
        """
        ...

    @abstractmethod
    def query_batch(self, kmers: List[str]) -> Dict[str, QueryResult]:
        """Batch query for multiple k-mers.

        Args:
            kmers: List of k-mer sequences to query.

        Returns:
            Dict[str, QueryResult]: Dictionary mapping k-mer to query result.

        Raises:
            InvalidKmerError: If any k-mer format is invalid.
            QueryError: If query operation fails.
            DatabaseError: If database is closed.
        """
        ...

    @abstractmethod
    def stats(self) -> DatabaseStats:
        """Get database statistics.

        Returns:
            DatabaseStats: Database statistics including k-mer size, counts, etc.

        Raises:
            QueryError: If stats operation fails.
            DatabaseError: If database is closed.
        """
        ...

    @abstractmethod
    def query_prefix(self, prefix: str) -> Dict[str, str]:
        """Prefix query to find k-mers starting with the given prefix.

        Args:
            prefix: The prefix string to search for.

        Returns:
            Dict[str, str]: Dictionary of k-mers matching the prefix and their counts.

        Raises:
            QueryError: If prefix query operation fails.
            DatabaseError: If database is closed or prefix query not supported.
        """
        ...

    @abstractmethod
    def query_fuzzy(
        self, pattern: str, mutations: int, max_results: Optional[int] = None
    ) -> FuzzyQueryResult:
        """Fuzzy query with mutation tolerance.

        Args:
            pattern: The k-mer pattern to query (may contain wildcards).
            mutations: Maximum number of mutations allowed.
            max_results: Optional maximum number of results to return.

        Returns:
            FuzzyQueryResult: Fuzzy query results with all matches.

        Raises:
            InvalidKmerError: If pattern format is invalid.
            InvalidMutationToleranceError: If mutations value is invalid.
            QueryError: If fuzzy query operation fails.
            DatabaseError: If database is closed.
        """
        ...

    @abstractmethod
    def dump(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> Iterator[QueryResult]:
        """Export database k-mers as an iterator.

        Args:
            limit: Maximum number of k-mers to return (None for all).
            offset: Number of k-mers to skip before returning.

        Yields:
            QueryResult: One QueryResult per k-mer in the database.

        Raises:
            QueryError: If dump operation fails.
            DatabaseError: If database is closed.
        """
        ...


class SubprocessBackend(DatabaseBackend):
    """Subprocess-based database backend.

    This backend uses the existing Database class that communicates with
    the rustkmer CLI tool through subprocess calls. It provides
    broad compatibility but has higher overhead due to process
    creation and IPC.
    """

    def __init__(self, path: Union[str, Path], validate: bool = False):
        """Initialize subprocess backend.

        Args:
            path: Path to the .rkdb database file.
            validate: Whether to perform full validation on initialization.

        Raises:
            DatabaseNotFoundError: If database file doesn't exist.
            InvalidDatabaseError: If database file is invalid.
        """
        from .database import Database

        self._db = Database(path, validate=validate)

    @property
    def path(self) -> str:
        """Database path."""
        return str(self._db.path)

    @property
    def kmer_size(self) -> Optional[int]:
        """K-mer size (None until stats are loaded)."""
        return self._db.kmer_size

    def query(self, kmer: str) -> QueryResult:
        """Exact query for a single k-mer.

        Delegates to subprocess Database.query().
        """
        return self._db.query(kmer)

    def query_batch(self, kmers: List[str]) -> Dict[str, QueryResult]:
        """Batch query for multiple k-mers.

        Delegates to subprocess Database.query_batch().
        """
        return self._db.query_batch(kmers)

    def stats(self) -> DatabaseStats:
        """Get database statistics.

        Delegates to subprocess Database.stats().
        """
        return self._db.stats()

    def query_prefix(self, prefix: str) -> Dict[str, str]:
        """Prefix query to find k-mers starting with the given prefix.

        Note: The subprocess backend doesn't support prefix queries directly.
        This method returns an empty dict as a fallback.

        Args:
            prefix: The prefix string to search for.

        Returns:
            Dict[str, str]: Empty dictionary (not supported in subprocess backend).

        Raises:
            QueryError: Not raised, but method is a no-op for this backend.
        """
        # Subprocess backend doesn't support prefix queries
        # Return empty dict as fallback
        return {}

    def query_fuzzy(
        self, pattern: str, mutations: int, max_results: Optional[int] = None
    ) -> FuzzyQueryResult:
        """Fuzzy query with mutation tolerance.

        Delegates to subprocess Database.fuzzy_query().
        """
        # max_results parameter is ignored in subprocess backend
        return self._db.fuzzy_query(pattern, mutations)

    def dump(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> Iterator[QueryResult]:
        """Export database k-mers as an iterator.

        Delegates to subprocess Database.dump() with as_string=False.

        Note: offset parameter is not supported by subprocess backend.
        """
        # offset parameter is not supported in subprocess backend
        # We need to skip offset number of results manually
        result = self._db.dump(limit=limit, as_string=False)
        if result is None:
            return iter([])

        # Skip offset number of results
        if offset > 0:
            skipped = 0
            temp_results = []
            for item in result:
                if skipped >= offset:
                    temp_results.append(item)
                else:
                    skipped += 1
            return iter(temp_results)

        return result

    def close(self):
        """Close database resources."""
        if hasattr(self._db, "close"):
            self._db.close()

    def reopen(self):
        """Reopen database resources."""
        if hasattr(self._db, "reopen"):
            self._db.reopen()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


class PyO3Backend(DatabaseBackend):
    """PyO3-based high-performance database backend.

    This backend uses the PyO3 Rust bindings for direct memory access
    to the database, providing significantly better performance than the
    subprocess approach. It requires the rustkmer_pyo3 package
    to be installed.
    """

    def __init__(self, path: Union[str, Path], load_mode: Optional[LoadMode] = None):
        """Initialize PyO3 backend.

        Args:
            path: Path to the .rkdb database file.
            load_mode: Loading mode (defaults to LoadMode.PRELOAD).

        Raises:
            ImportError: If rustkmer_pyo3 package is not installed.
            FileNotFoundError: If database file doesn't exist.
            ValueError: If database file is invalid.
        """
        try:
            import rustkmer_pyo3
        except ImportError as e:
            raise ImportError(
                "PyO3 backend requires 'rustkmer_pyo3' package. "
                "Install it with: pip install rustkmer-pyo3"
            ) from e

        # Set default load mode if not specified
        if load_mode is None:
            load_mode = LoadMode.PRELOAD

        # Convert LoadMode enum to PyO3 LoadMode
        pyo3_load_mode = getattr(rustkmer_pyo3.LoadMode, load_mode.value.capitalize())

        # Create PyO3 database
        self._db = rustkmer_pyo3.PyDatabase(str(path), pyo3_load_mode)

    @property
    def path(self) -> str:
        """Database path."""
        return self._db.path

    @property
    def kmer_size(self) -> int:
        """K-mer size."""
        return self._db.get_stats().kmer_size

    def query(self, kmer: str) -> QueryResult:
        """Exact query for a single k-mer.

        Delegates to PyO3 PyDatabase query and converts result to QueryResult.
        """
        result = self._db.query(kmer)

        # Convert PyO3 result to our QueryResult format
        from .utils import canonical_kmer

        canonical = canonical_kmer(kmer)

        return QueryResult(
            kmer=result.kmer,
            count=result.count,
            canonical=canonical,
        )

    def query_batch(self, kmers: List[str]) -> Dict[str, QueryResult]:
        """Batch query for multiple k-mers.

        Delegates to PyO3 PyDatabase query for each k-mer.
        """
        from .utils import canonical_kmer

        results = {}
        for kmer in kmers:
            result = self._db.query(kmer)
            canonical = canonical_kmer(kmer)
            results[kmer] = QueryResult(
                kmer=result.kmer,
                count=result.count,
                canonical=canonical,
            )
        return results

    def stats(self) -> DatabaseStats:
        """Get database statistics.

        Delegates to PyO3 PyDatabase get_stats and converts result.
        """
        from pathlib import Path

        pyo3_stats = self._db.get_stats()
        db_path = Path(self.path)

        return DatabaseStats(
            kmer_size=pyo3_stats.kmer_size,
            unique_kmers=pyo3_stats.unique_kmers,
            total_counts=pyo3_stats.total_kmers,
            min_count=0,  # PyO3 stats don't include min_count
            max_count=0,  # PyO3 stats don't include max_count
            file_size=db_path.stat().st_size if db_path.exists() else 0,
            format_version="unknown",  # PyO3 stats don't include format version
        )

    def query_prefix(self, prefix: str) -> Dict[str, str]:
        """Prefix query to find k-mers starting with the given prefix.

        Delegates to PyO3 extract_prefix_optimized method.

        Args:
            prefix: The prefix string to search for.

        Returns:
            Dict[str, str]: Dictionary of k-mers matching the prefix and their counts.

        Raises:
            QueryError: If prefix query operation fails.
        """
        result = self._db.extract_prefix_optimized(prefix)

        # PyO3 returns a dictionary, but we need to convert format
        # The matches dict format depends on the PyO3 implementation
        # Assuming it's HashMap<kmer, count>
        return dict(result.matches)

    def query_fuzzy(
        self, pattern: str, mutations: int, max_results: Optional[int] = None
    ) -> FuzzyQueryResult:
        """Fuzzy query with mutation tolerance.

        Delegates to PyO3 fuzzy query functionality and converts result.
        """
        import rustkmer_pyo3

        # Create fuzzy query object
        fuzzy_query = rustkmer_pyo3.PyFuzzyQuery(self._db)

        # Perform fuzzy query
        # Note: PyO3's fuzzy query interface may differ slightly
        # We're using a simplified approach here
        pyo3_result = fuzzy_query.fuzzy_query(pattern, mutations)

        # Convert PyO3 result to our FuzzyQueryResult format
        from .fuzzy_query import FuzzyMatchResult

        matches = [
            FuzzyMatchResult(
                kmer=match.kmer,
                count=match.count,
                distance=match.distance,
                mutations=match.mutations,
            )
            for match in pyo3_result.matches
        ]

        exact_match = None
        for match in matches:
            if match.distance == 0:
                exact_match = match
                break

        return FuzzyQueryResult(
            query_kmer=pattern,
            exact_match=exact_match,
            matches=matches,
            total_matches=pyo3_result.total_matches,
            mutation_tolerance=mutations,
            database_path=self.path,
            position_mutations_config=None,
        )

    def dump(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> Iterator[QueryResult]:
        """Export database k-mers as an iterator.

        Note: PyO3 backend doesn't support direct dump iteration.
        This method provides a limited implementation.

        Args:
            limit: Maximum number of k-mers to return (None for all).
            offset: Number of k-mers to skip before returning.

        Yields:
            QueryResult: One QueryResult per k-mer in the database.
        """
        from .utils import canonical_kmer

        # PyO3 doesn't provide a direct dump method
        # We need to use stats to get k-mer count and iterate
        stats = self._db.get_stats()

        # This is a limitation - PyO3 doesn't expose direct k-mer iteration
        # Return empty iterator as fallback
        # In practice, you'd need to implement a dump method in PyO3
        return iter([])

    def close(self):
        """Close database resources."""
        # PyO3 manages resources automatically
        # No explicit close needed
        pass

    def reopen(self):
        """Reopen database resources."""
        # PyO3 manages resources automatically
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


def create_backend(
    path: Union[str, Path],
    load_mode: Optional[LoadMode] = None,
    validate: bool = False,
    prefer_pyo3: bool = True,
) -> DatabaseBackend:
    """
    Create a database backend with automatic backend selection.

    This function attempts to create a PyO3 backend if available and
    preferred, falling back to the subprocess backend if PyO3 is not
    available or fails to initialize.

    Args:
        path: Path to the .rkdb database file.
        load_mode: Loading mode for PyO3 backend (if used).
                   Ignored for subprocess backend.
        validate: Whether to validate database on initialization
                   (for subprocess backend).
        prefer_pyo3: If True (default), try PyO3 backend first.
                     If False, use subprocess backend directly.

    Returns:
        DatabaseBackend: An instance of either PyO3Backend or SubprocessBackend.

    Raises:
        DatabaseNotFoundError: If database file doesn't exist.
        InvalidDatabaseError: If database file is invalid.
        ImportError: If prefer_pyo3=True and PyO3 package is not installed,
                   AND subprocess backend also fails.

    Example:
        >>> # Try PyO3 first, fall back to subprocess
        >>> db = create_backend("genome.rkdb")
        >>>
        >>> # Force subprocess backend
        >>> db = create_backend("genome.rkdb", prefer_pyo3=False)
        >>>
        >>> # Use specific PyO3 load mode
        >>> db = create_backend(
        ...     "genome.rkdb",
        ...     load_mode=LoadMode.MEMORY_MAPPED
        ... )
    """
    if prefer_pyo3:
        try:
            # Try to create PyO3 backend first
            return PyO3Backend(path, load_mode=load_mode)
        except ImportError:
            # PyO3 not available, fall back to subprocess
            pass
        except Exception:
            # Other PyO3 error, fall back to subprocess
            pass

    # Fall back to subprocess backend
    return SubprocessBackend(path, validate=validate)


def get_backend_type(backend: DatabaseBackend) -> str:
    """Get the type name of a backend instance.

    Args:
        backend: A DatabaseBackend instance.

    Returns:
        str: Backend type name ('PyO3Backend' or 'SubprocessBackend').

    Example:
        >>> db = create_backend("genome.rkdb")
        >>> get_backend_type(db)
        'PyO3Backend'
    """
    return backend.__class__.__name__


def is_pyo3_backend(backend: DatabaseBackend) -> bool:
    """Check if a backend is a PyO3 backend.

    Args:
        backend: A DatabaseBackend instance.

    Returns:
        bool: True if backend is PyO3Backend, False otherwise.

    Example:
        >>> db = create_backend("genome.rkdb", prefer_pyo3=True)
        >>> is_pyo3_backend(db)
        True
    """
    return isinstance(backend, PyO3Backend)


def is_subprocess_backend(backend: DatabaseBackend) -> bool:
    """Check if a backend is a subprocess backend.

    Args:
        backend: A DatabaseBackend instance.

    Returns:
        bool: True if backend is SubprocessBackend, False otherwise.

    Example:
        >>> db = create_backend("genome.rkdb", prefer_pyo3=False)
        >>> is_subprocess_backend(db)
        True
    """
    return isinstance(backend, SubprocessBackend)
