"""Database class for rustkmer Python bindings.

This module provides the main Database class for interacting with
rustkmer k-mer databases through subprocess calls to the CLI.
"""

import re
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Union

from .query import QueryResult
from .stats import DatabaseStats
from .utils import (
    run_rustkmer_command,
    parse_query_output,
    parse_stats_output,
    validate_kmer,
    canonical_kmer,
)
from .exceptions import (
    DatabaseNotFoundError,
    DatabaseError,
    InvalidDatabaseError,
    QueryError,
)


class Database:
    """
    Represents a rustkmer k-mer database.

    This class provides methods to query k-mers, dump database contents,
    and retrieve database statistics through subprocess calls to the
    rustkmer CLI tool.

    Example:
        >>> db = Database("/path/to/database.rkdb")
        >>> count = db.query("ATCG")
        >>> stats = db.stats()
        >>> for result in db.dump(limit=1000):
        ...     print(result.kmer, result.count)

    Context manager usage:
        >>> with Database("/path/to/database.rkdb") as db:
        ...     count = db.query("ATCG")
    """

    def __init__(self, path: Union[str, Path], validate: bool = True):
        """
        Initialize database connection.

        Args:
            path: Path to the .rkdb database file
            validate: Whether to validate database on initialization

        Raises:
            DatabaseNotFoundError: If database file doesn't exist
            InvalidDatabaseError: If file is not a valid database
        """
        self._path = Path(path)
        self._kmer_size: Optional[int] = None
        self._is_loaded = False
        self._is_closed = False
        self._stats_cache: Optional[DatabaseStats] = None

        if validate:
            self._validate_database()

    @property
    def path(self) -> Path:
        """Path to the database file."""
        return self._path

    @property
    def kmer_size(self) -> Optional[int]:
        """Length of k-mers in database (None until stats are loaded)."""
        if not self._is_loaded:
            self._load_metadata()
        return self._kmer_size

    @property
    def is_loaded(self) -> bool:
        """Whether database metadata has been loaded."""
        return self._is_loaded

    def _validate_database(self) -> None:
        """Validate that the database file exists and is readable."""
        if not self._path.exists():
            raise DatabaseNotFoundError(str(self._path))

        if not self._path.is_file():
            raise InvalidDatabaseError(
                str(self._path),
                "Path exists but is not a file"
            )

        # Try to get stats to validate it's a real database
        try:
            self.stats()
        except Exception as e:
            raise InvalidDatabaseError(
                str(self._path),
                f"Failed to read database: {e}"
            )

    def _load_metadata(self) -> None:
        """Load basic metadata from the database."""
        if self._is_loaded:
            return

        try:
            stats = self.stats()
            self._kmer_size = stats.kmer_size
            self._is_loaded = True
        except Exception as e:
            raise QueryError(f"Failed to load database metadata: {e}")

    def query(self, kmer: str, validate_strict: bool = True) -> QueryResult:
        """
        Query a single k-mer in the database.

        Args:
            kmer: The k-mer sequence to query
            validate_strict: If True, raise exceptions for invalid k-mers. If False, return count=0 for invalid k-mers.

        Returns:
            QueryResult object with the k-mer information

        Raises:
            InvalidKmerError: If k-mer is invalid and validate_strict=True
            QueryError: If query fails
            DatabaseError: If database is closed
        """
        # Check if database is closed
        if self._is_closed:
            raise DatabaseError("Cannot query: database is closed")

        # Validate k-mer
        validated_kmer = validate_kmer(kmer, self.kmer_size, strict=validate_strict)

        # Handle invalid k-mer if not strict
        if validated_kmer is None:
            # Still try to compute canonical form if kmer has valid characters
            if isinstance(kmer, str) and re.match(r'^[ATCG]+$', kmer.upper()):
                canonical = canonical_kmer(kmer.upper())
            else:
                canonical = None

            # Return result with count=0 for invalid k-mers
            return QueryResult(
                kmer=kmer,
                count=0,
                canonical=canonical
            )

        # Get canonical form
        canonical = canonical_kmer(validated_kmer)

        # Execute query
        try:
            output = run_rustkmer_command([
                'query',
                str(self._path),
                validated_kmer
            ])
        except Exception as e:
            raise QueryError(f"Failed to query k-mer '{validated_kmer}': {e}")

        # Parse output
        data = parse_query_output(output)

        # Create and return result
        return QueryResult(
            kmer=validated_kmer,
            count=data.get('count', 0),
            canonical=canonical
        )

    def query_batch(
        self,
        kmers: List[str],
        max_workers: int = 4,
        chunk_size: int = 100
    ) -> Dict[str, QueryResult]:
        """
        Query multiple k-mers in parallel with optimized batching.

        Args:
            kmers: List of k-mer sequences to query
            max_workers: Maximum number of parallel subprocess calls
            chunk_size: Number of kmers to process in each chunk for large batches

        Returns:
            Dictionary mapping k-mer to QueryResult

        Raises:
            InvalidKmerError: If any k-mer is invalid
            DatabaseError: If database is closed
        """
        # Check if database is closed
        if self._is_closed:
            raise DatabaseError("Cannot query batch: database is closed")

        from concurrent.futures import ThreadPoolExecutor, as_completed
        import math

        # Validate all kmers first (batch validation for performance)
        validated_kmers = {}
        kmer_size = self.kmer_size  # Get once to avoid repeated property access

        for kmer in kmers:
            validated_kmers[kmer] = validate_kmer(kmer, kmer_size, strict=False)

        results = {}

        # Handle invalid k-mers (those that got None from validation)
        for original_kmer, validated_kmer in list(validated_kmers.items()):
            if validated_kmer is None:
                # Invalid k-mer, return count=0
                results[original_kmer] = QueryResult(
                    kmer=original_kmer,
                    count=0,
                    canonical=None
                )
                # Remove from validated list so we don't try to query it
                del validated_kmers[original_kmer]

        # For small batches, process all at once
        if len(kmers) <= chunk_size:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_kmer = {
                    executor.submit(
                        self._query_single,
                        validated_kmer
                    ): original_kmer
                    for original_kmer, validated_kmer in validated_kmers.items()
                }

                for future in as_completed(future_to_kmer):
                    original_kmer = future_to_kmer[future]
                    try:
                        result = future.result()
                        results[original_kmer] = result
                    except Exception as e:
                        results[original_kmer] = QueryResult(
                            kmer=original_kmer,
                            count=0,
                            canonical=validated_kmers[original_kmer]
                        )
        else:
            # For large batches, process in chunks to avoid overwhelming the system
            chunks = list(validated_kmers.items())
            num_chunks = math.ceil(len(chunks) / chunk_size)

            for i in range(num_chunks):
                chunk_start = i * chunk_size
                chunk_end = min((i + 1) * chunk_size, len(chunks))
                chunk = dict(chunks[chunk_start:chunk_end])

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_kmer = {
                        executor.submit(
                            self._query_single,
                            validated_kmer
                        ): original_kmer
                        for original_kmer, validated_kmer in chunk.items()
                    }

                    for future in as_completed(future_to_kmer):
                        original_kmer = future_to_kmer[future]
                        try:
                            result = future.result()
                            results[original_kmer] = result
                        except Exception:
                            results[original_kmer] = QueryResult(
                                kmer=original_kmer,
                                count=0,
                                canonical=validated_kmers[original_kmer]
                            )

        return results

    def _query_single(self, kmer: str) -> QueryResult:
        """Internal method to query a single k-mer."""
        # This is used by query_batch for parallel execution
        # We implement it by calling the public query method
        # but without validation (already done)
        try:
            output = run_rustkmer_command([
                'query',
                str(self._path),
                kmer
            ])
        except Exception as e:
            raise QueryError(f"Failed to query k-mer '{kmer}': {e}")

        # Parse output
        data = parse_query_output(output)

        # Get canonical form
        canonical = canonical_kmer(kmer)

        # Create and return result
        return QueryResult(
            kmer=kmer,
            count=data.get('count', 0),
            canonical=canonical
        )

    def dump(
        self,
        limit: Optional[int] = None,
        as_string: bool = True
    ) -> Union[Iterator[QueryResult], str]:
        """
        Iterate over k-mers in the database or return as formatted string.

        Since the rustkmer CLI dump command doesn't support streaming or limit/offset
        arguments, this method dumps the entire database and yields results with
        optional limit enforcement.

        Args:
            limit: Maximum number of k-mers to return (optional)
            as_string: If True (default), return formatted string instead of iterator

        Yields:
            QueryResult objects for each k-mer (if as_string=False)

        Returns:
            Formatted string with all k-mers (if as_string=True, default)

        Raises:
            QueryError: If dump operation fails
            DatabaseError: If database is closed
        """
        # Create a temporary file for output
        import tempfile
        import os

        # Check if database is closed
        if self._is_closed:
            raise DatabaseError("Cannot dump: database is closed")

        # Create a temporary file for output
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tmp_file:
            tmp_path = tmp_file.name

        try:
            # Build dump command with output file
            args = ['dump', '-o', tmp_path, str(self._path)]

            # Run dump command with appropriate timeout
            # For large databases, we need more time even for small limits
            # since the CLI dumps everything
            if limit is None:
                timeout = 3600  # 1 hour for full dump
            elif limit <= 1000:
                timeout = 600  # 10 minutes for small limits (full dump still required)
            else:
                timeout = 1800  # 30 minutes for larger limits

            try:
                run_rustkmer_command(args, timeout=timeout)
            except Exception as e:
                raise QueryError(f"Failed to dump database: {e}")

            # Read and parse the output file
            yielded = 0
            results = []
            query_results = []

            with open(tmp_path, 'r') as f:
                for line in f:
                    if not line.strip():
                        continue

                    # Apply limit if specified
                    if limit is not None and yielded >= limit:
                        break

                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        kmer = parts[0]
                        count = int(parts[1])
                        canonical = canonical_kmer(kmer)

                        result = QueryResult(
                            kmer=kmer,
                            count=count,
                            canonical=canonical
                        )

                        # Store for both possible return types
                        query_results.append(result)
                        results.append(f"{kmer}\t{count}")

                        yielded += 1

            # Return based on as_string parameter
            if as_string:
                return '\n'.join(results)
            else:
                # Return an iterator over the QueryResults
                return iter(query_results)

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def stats(self) -> DatabaseStats:
        """
        Get database statistics.

        Returns:
            DatabaseStats object with database information

        Raises:
            QueryError: If stats operation fails
            DatabaseError: If database is closed
        """
        # Check if database is closed
        if self._is_closed:
            raise DatabaseError("Cannot get stats: database is closed")

        # Check cache first
        if self._stats_cache is not None:
            return self._stats_cache

        try:
            output = run_rustkmer_command(['stats', str(self._path)])
        except Exception as e:
            raise QueryError(f"Failed to get database stats: {e}")

        # Parse output
        data = parse_stats_output(output)

        # Create DatabaseStats object
        stats = DatabaseStats(
            kmer_size=data['kmer_size'],
            unique_kmers=data['unique_kmers'],
            total_counts=data['total_counts'],
            min_count=data.get('min_count', 0),  # Add min_count field with default
            max_count=data['max_count'],
            file_size=self._path.stat().st_size,
            format_version=data['format_version']
        )

        # Cache the result
        self._stats_cache = stats
        self._kmer_size = stats.kmer_size
        self._is_loaded = True

        return stats

    def close(self):
        """Close database resources."""
        # Clear the cache and mark as closed
        self._stats_cache = None
        self._is_loaded = False
        self._is_closed = True

    def reopen(self):
        """Reopen database resources."""
        if self._is_closed:
            self._is_closed = False
            # Reload metadata when needed
            self._load_metadata()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        # Don't suppress exceptions
        return False

    def __repr__(self) -> str:
        """String representation."""
        return f"Database(path='{self._path}', loaded={self._is_loaded})"