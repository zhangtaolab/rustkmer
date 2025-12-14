"""Database class for rustkmer Python bindings.

This module provides the main Database class for interacting with
rustkmer k-mer databases through subprocess calls to the CLI.
"""

import re
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Union

from .query import QueryResult
from .stats import DatabaseStats
from .fuzzy_query import FuzzyQueryResult, FuzzyMatchResult, FuzzyBatchResult
from .utils import (
    run_rustkmer_command,
    parse_query_output,
    parse_stats_output,
    parse_fuzzy_query_output,
    validate_kmer,
    validate_fuzzy_kmer,
    canonical_kmer,
)
from .exceptions import (
    DatabaseNotFoundError,
    DatabaseError,
    InvalidDatabaseError,
    QueryError,
    InvalidKmerError,
    InvalidMutationToleranceError,
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

    def fuzzy_query(
        self,
        kmer: str,
        mutations: int = 1,
        max_variants: Optional[int] = None,
        output_format: str = 'auto'
    ) -> FuzzyQueryResult:
        """
        Perform a fuzzy k-mer query with mutation tolerance.

        This method searches for k-mers in the database that are within a specified
        Hamming distance from the query k-mer. Unlike exact queries, fuzzy queries
        can find similar sequences that differ by a small number of mutations,
        which is useful for handling sequencing errors, natural variations,
        or finding related sequences.

        The search generates all possible variants of the query k-mer within the
        specified mutation tolerance and checks each against the database. The
        results are returned as a FuzzyQueryResult containing all matches found.

        Args:
            kmer (str): The k-mer sequence to query. Must contain only A, T, C, G
                       characters and have the correct length for the database
            mutations (int): Maximum number of mutations allowed (0-5). A value
                           of 0 performs an exact match query, while higher values
                           allow increasingly divergent matches
            max_variants (Optional[int]): Maximum number of variants to generate
                                        and check. This limits the combinatorial
                                        explosion for high mutation tolerances.
                                        If None, checks all possible variants
            output_format (str): Output format for the CLI command. Options:
                               - 'auto' (default): Automatically choose best format
                               - 'json': Machine-readable JSON format
                               - 'table': Human-readable table format
                               - 'tsv': Tab-separated values format

        Returns:
            FuzzyQueryResult: Object containing all matches found within the
                mutation tolerance, including:
                - Exact matches (if any)
                - Fuzzy matches with their distances and mutations
                - Summary statistics

        Raises:
            InvalidKmerError: If k-mer contains invalid characters or has
                            incorrect length for the database
            InvalidMutationToleranceError: If mutations is not in the range 0-5
            DatabaseError: If the database has been closed
            QueryError: If the CLI command fails or returns unexpected output
            ValueError: If max_variants is not a positive integer when specified

        Example:
            >>> db = Database("example.rkdb")
            >>> # Find exact matches only
            >>> result = db.fuzzy_query("ATCG", mutations=0)
            >>>
            >>> # Allow up to 2 mutations
            >>> result = db.fuzzy_query("ATCG", mutations=2)
            >>> print(f"Found {result.total_matches} matches")
            >>>
            >>> # Get top 5 most abundant matches
            >>> top_matches = result.get_top_matches(5)
            >>> for match in top_matches:
            ...     print(f"{match.kmer}: {match.count} (distance={match.distance})")

        Note:
            The number of possible variants grows combinatorially with mutation
            tolerance. For a k-mer of length k, the number of variants at distance
            d is k^d * 3^d (each position can be one of 3 alternative bases).
            Use max_variants to limit computational cost for high tolerances.
        """
        # Check if database is closed
        if self._is_closed:
            raise DatabaseError("Cannot perform fuzzy query: database is closed")

        # Validate mutations parameter
        if not isinstance(mutations, int) or mutations < 0 or mutations > 5:
            raise InvalidMutationToleranceError(
                f"Invalid mutation tolerance: {mutations}. Must be an integer between 0 and 5."
            )

        # Validate output format
        supported_formats = {'auto', 'json', 'table', 'tsv'}
        if output_format not in supported_formats:
            raise ValueError(
                f"Invalid output format: '{output_format}'. "
                f"Supported formats are: {', '.join(sorted(supported_formats))}"
            )

        # Validate k-mer (allow N wildcards for fuzzy query)
        validated_kmer = validate_fuzzy_kmer(kmer, self.kmer_size, strict=True)

        # Build CLI command arguments
        args = ['fuzzy-query', str(self._path), validated_kmer, '--mutations', str(mutations)]

        # Add optional arguments
        if max_variants is not None:
            if not isinstance(max_variants, int) or max_variants < 1:
                raise ValueError(f"max_variants must be a positive integer, got {max_variants}")
            args.extend(['--max-variants', str(max_variants)])

        # Add output format if not auto
        if output_format != 'auto':
            args.extend(['--format', output_format])

        # Execute fuzzy query command
        try:
            output = run_rustkmer_command(args)
        except Exception as e:
            raise QueryError(f"Failed to perform fuzzy query for k-mer '{validated_kmer}': {e}")

        # Parse output
        data = parse_fuzzy_query_output(output, output_format)

        # Create FuzzyMatchResult objects from parsed data
        matches = []
        exact_match = None

        for match_data in data.get('matches', []):
            match = FuzzyMatchResult(
                kmer=match_data.get('kmer', ''),
                count=match_data.get('count', 0),
                distance=match_data.get('distance', 0),
                mutations=match_data.get('mutations', [])
            )
            matches.append(match)

            # Track exact match (distance == 0)
            if match.distance == 0:
                exact_match = match

        # Create and return FuzzyQueryResult
        return FuzzyQueryResult(
            query_kmer=validated_kmer,
            exact_match=exact_match,
            matches=matches,
            total_matches=data.get('total_matches', 0),
            mutation_tolerance=mutations,
            database_path=str(self._path)
        )

    def fuzzy_query_batch(
        self,
        kmers: List[str],
        mutations: int = 1,
        max_variants: Optional[int] = None,
        max_workers: int = 4,
        output_format: str = 'auto'
    ) -> FuzzyBatchResult:
        """
        Perform batch fuzzy k-mer queries with parallel processing.

        This method processes multiple k-mers in parallel, each with the same
        fuzzy query parameters. It's significantly more efficient than calling
        fuzzy_query() multiple times for large batches, as it leverages multiple
        CPU cores to run queries concurrently.

        Each k-mer in the batch is processed independently with the same
        mutation tolerance and other parameters. Invalid k-mers are silently
        skipped (they appear in the results with 0 matches). The method returns
        a FuzzyBatchResult that aggregates all individual query results and
        provides summary statistics.

        Args:
            kmers (List[str]): List of k-mer sequences to query. Each must contain
                              only A, T, C, G characters and have the correct
                              length for the database
            mutations (int): Maximum number of mutations allowed per query (0-5).
                           Applied equally to all k-mers in the batch
            max_variants (Optional[int]): Maximum number of variants to generate
                                        and check per query. If None, checks all
                                        possible variants for each k-mer
            max_workers (int): Number of parallel subprocess workers to use.
                             More workers can process more k-mers simultaneously
                             but use more system resources (default: 4)
            output_format (str): Output format for CLI commands. See fuzzy_query()
                               for available options (default: 'auto')

        Returns:
            FuzzyBatchResult: Aggregated results containing:
                - Individual query results for each valid k-mer
                - Summary statistics (total queries, matches, success rates)
                - Per-query success indicators

        Raises:
            DatabaseError: If the database has been closed
            InvalidMutationToleranceError: If mutations is not in the range 0-5
            ValueError: If max_workers is not a positive integer

        Example:
            >>> db = Database("example.rkdb")
            >>> kmers = ["ATCG", "GCTA", "TTAA", "CCGG"]
            >>> # Batch query with 1 mutation tolerance
            >>> batch = db.fuzzy_query_batch(kmers, mutations=1, max_workers=2)
            >>>
            >>> # Check overall statistics
            >>> print(f"Processed {batch.total_queries} queries")
            >>> print(f"{batch.queries_with_matches} found matches")
            >>>
            >>> # Get summary table
            >>> print(batch.get_summary_table())
            >>>
            >>> # Access individual results
            >>> for result in batch.query_results:
            ...     if result.total_matches > 0:
            ...         print(f"{result.query_kmer}: {result.total_matches} matches")

        Note:
            - The method returns a FuzzyBatchResult even for empty input lists
            - Invalid k-mers in the input list are skipped and don't raise errors
            - All queries in the batch use the same parameters (mutations, etc.)
            - Results are ordered based on completion, not input order
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import itertools

        # Check if database is closed
        if self._is_closed:
            raise DatabaseError("Cannot perform batch fuzzy query: database is closed")

        # Validate parameters
        if not isinstance(mutations, int) or mutations < 0 or mutations > 5:
            raise InvalidMutationToleranceError(
                f"Invalid mutation tolerance: {mutations}. Must be an integer between 0 and 5."
            )

        if not isinstance(max_workers, int) or max_workers < 1:
            raise ValueError(f"max_workers must be a positive integer, got {max_workers}")

        # Validate output format
        supported_formats = {'auto', 'json', 'table', 'tsv'}
        if output_format not in supported_formats:
            raise ValueError(
                f"Invalid output format: '{output_format}'. "
                f"Supported formats are: {', '.join(sorted(supported_formats))}"
            )

        # Early return for empty list
        if not kmers:
            return FuzzyBatchResult([], 0, 0, str(self._path))

        # Validate each k-mer
        validated_kmers = []
        for kmer in kmers:
            try:
                validated_kmer = validate_fuzzy_kmer(kmer, self.kmer_size, strict=True)
                validated_kmers.append(validated_kmer)
            except Exception as e:
                # For now, skip invalid k-mers but could include error results
                continue

        # If no valid k-mers, return empty result
        if not validated_kmers:
            return FuzzyBatchResult([], len(kmers), 0, str(self._path))

        # Process queries in parallel
        query_results = []
        total_matches = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all queries
            future_to_kmer = {
                executor.submit(
                    self._single_fuzzy_query,
                    kmer,
                    mutations,
                    max_variants,
                    output_format
                ): kmer
                for kmer in validated_kmers
            }

            # Collect results
            for future in as_completed(future_to_kmer):
                kmer = future_to_kmer[future]
                try:
                    result = future.result()
                    query_results.append(result)
                    total_matches += result.total_matches
                except Exception as e:
                    # Create error result
                    error_result = FuzzyQueryResult(
                        query_kmer=kmer,
                        exact_match=None,
                        matches=[],
                        total_matches=0,
                        mutation_tolerance=mutations,
                        database_path=str(self._path)
                    )
                    query_results.append(error_result)

        return FuzzyBatchResult(
            query_results=query_results,
            total_queries=len(kmers),
            total_matches=total_matches,
            database_path=str(self._path)
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
            validated_kmers[kmer] = validate_fuzzy_kmer(kmer, kmer_size, strict=False)

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

    def _single_fuzzy_query(
        self,
        kmer: str,
        mutations: int,
        max_variants: Optional[int] = None,
        output_format: str = 'auto'
    ) -> FuzzyQueryResult:
        """
        Internal method to perform a single fuzzy query without validation.

        This is a helper method used by fuzzy_query_batch() to perform individual
        queries in parallel. It assumes all input parameters have already been
        validated by the caller and skips validation for better performance.

        Args:
            kmer (str): The validated k-mer sequence to query
            mutations (int): Maximum number of mutations allowed (validated)
            max_variants (Optional[int]): Maximum number of variants to check
            output_format (str): Output format for CLI command ('auto', 'json', 'table', 'tsv')

        Returns:
            FuzzyQueryResult: Query result containing all matches within tolerance

        Raises:
            QueryError: If CLI command fails or returns unexpected output
            ValueError: If output_format is not supported

        Note:
            This method does not check if the database is closed, validate the k-mer,
            or validate the mutations parameter. These checks must be performed by
            the caller for consistent behavior.
        """
        # Validate output format
        supported_formats = {'auto', 'json', 'table', 'tsv'}
        if output_format not in supported_formats:
            raise ValueError(
                f"Invalid output format: '{output_format}'. "
                f"Supported formats are: {', '.join(sorted(supported_formats))}"
            )

        # Build CLI command arguments
        args = ['fuzzy-query', str(self._path), kmer, '--mutations', str(mutations)]

        # Add optional arguments
        if max_variants is not None:
            args.extend(['--max-variants', str(max_variants)])

        # Add output format if not auto
        if output_format != 'auto':
            args.extend(['--format', output_format])

        # Execute fuzzy query command
        try:
            output = run_rustkmer_command(args)
        except Exception as e:
            raise QueryError(f"Failed to perform fuzzy query for k-mer '{kmer}': {e}")

        # Parse output
        data = parse_fuzzy_query_output(output, output_format)

        # Create FuzzyMatchResult objects from parsed data
        matches = []
        exact_match = None

        for match_data in data.get('matches', []):
            match = FuzzyMatchResult(
                kmer=match_data.get('kmer', ''),
                count=match_data.get('count', 0),
                distance=match_data.get('distance', 0),
                mutations=match_data.get('mutations', [])
            )
            matches.append(match)

            # Track exact match (distance == 0)
            if match.distance == 0:
                exact_match = match

        # Create and return FuzzyQueryResult
        return FuzzyQueryResult(
            query_kmer=kmer,
            exact_match=exact_match,
            matches=matches,
            total_matches=data.get('total_matches', 0),
            mutation_tolerance=mutations,
            database_path=str(self._path)
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