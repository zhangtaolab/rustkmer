"""Database class for rustkmer Python bindings.

This module provides the main Database class for interacting with
rustkmer k-mer databases through subprocess calls to the CLI.
"""

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
    InvalidDatabaseError,
    InvalidKmerError,
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

    def query(self, kmer: str) -> QueryResult:
        """
        Query a single k-mer in the database.

        Args:
            kmer: The k-mer sequence to query

        Returns:
            QueryResult object with the k-mer information

        Raises:
            InvalidKmerError: If k-mer is invalid
            QueryError: If query fails
        """
        # Validate k-mer
        validated_kmer = validate_kmer(kmer, self.kmer_size)

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
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import math

        # Validate all kmers first (batch validation for performance)
        validated_kmers = {}
        kmer_size = self.kmer_size  # Get once to avoid repeated property access

        for kmer in kmers:
            validated_kmers[kmer] = validate_kmer(kmer, kmer_size)

        results = {}

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
        offset: int = 0,
        chunk_size: int = 10000,
        stream_large: bool = True
    ) -> Iterator[QueryResult]:
        """
        Iterate over k-mers in the database with memory-efficient streaming.

        For large databases (>1M k-mers), automatically uses chunked streaming
        to avoid loading all results into memory at once.

        Args:
            limit: Maximum number of k-mers to return
            offset: Number of k-mers to skip
            chunk_size: Number of k-mers to fetch in each chunk for streaming
            stream_large: Force streaming mode for databases of any size

        Yields:
            QueryResult objects for each k-mer

        Raises:
            QueryError: If dump operation fails
        """
        # Get database stats to determine size (cached)
        stats = self.stats()

        # Determine if we should use streaming
        use_streaming = stream_large or stats.unique_kmers > 1000000  # > 1M k-mers

        if limit is not None and limit <= chunk_size and not use_streaming:
            # Small request, fetch all at once
            args = ['dump', str(self._path)]

            if offset > 0:
                args.extend(['--offset', str(offset)])

            args.extend(['--limit', str(limit)])

            try:
                output = run_rustkmer_command(args, timeout=60)
            except Exception as e:
                raise QueryError(f"Failed to dump database: {e}")

            # Parse and yield results
            lines = output.strip().split('\n')
            for line in lines:
                if not line.strip():
                    continue

                parts = line.split('\t')
                if len(parts) >= 2:
                    kmer = parts[0]
                    count = int(parts[1])
                    canonical = canonical_kmer(kmer)

                    yield QueryResult(
                        kmer=kmer,
                        count=count,
                        canonical=canonical
                    )
        else:
            # Large request, use streaming with chunks
            remaining = limit
            current_offset = offset
            yielded = 0

            while remaining is None or remaining > 0:
                # Determine chunk size for this iteration
                current_chunk = chunk_size
                if remaining is not None:
                    current_chunk = min(chunk_size, remaining)

                # Build command for this chunk
                args = ['dump', str(self._path)]

                if current_offset > 0:
                    args.extend(['--offset', str(current_offset)])

                args.extend(['--limit', str(current_chunk)])

                try:
                    # Use longer timeout for large chunks
                    timeout = max(60, current_chunk // 100)  # 1 second per 100 k-mers minimum
                    output = run_rustkmer_command(args, timeout=timeout)
                except Exception as e:
                    if yielded > 0:
                        # We've already yielded some results, just stop
                        break
                    else:
                        raise QueryError(f"Failed to dump database: {e}")

                # Check if we got any results
                if not output.strip():
                    break  # No more results

                # Parse and yield results from this chunk
                lines = output.strip().split('\n')
                chunk_yielded = 0

                for line in lines:
                    if not line.strip():
                        continue

                    parts = line.split('\t')
                    if len(parts) >= 2:
                        kmer = parts[0]
                        count = int(parts[1])
                        canonical = canonical_kmer(kmer)

                        yield QueryResult(
                            kmer=kmer,
                            count=count,
                            canonical=canonical
                        )

                        yielded += 1
                        chunk_yielded += 1

                # Update counters for next iteration
                current_offset += chunk_yielded
                if remaining is not None:
                    remaining -= chunk_yielded

                # If we got fewer results than requested, we've reached the end
                if chunk_yielded < current_chunk:
                    break

    def stats(self) -> DatabaseStats:
        """
        Get database statistics.

        Returns:
            DatabaseStats object with database information

        Raises:
            QueryError: If stats operation fails
        """
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
        # In this implementation, we don't have persistent resources
        # But we clear the cache
        self._stats_cache = None
        self._is_loaded = False

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