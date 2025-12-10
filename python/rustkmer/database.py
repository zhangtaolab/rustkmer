"""
Database module for RustKmer.

This module provides Pythonic wrappers for the Rust-based database operations,
including Database class for querying RKDB files.
"""

from typing import Optional, List, Dict, Union, Any, Type
from pathlib import Path
import warnings
import types

# Import the Rust implementation
from .rustkmer import SimpleDatabase, QueryResult, DatabaseStats
# Import error handling utilities
from .error_handling import (
    handle_errors, ErrorContext, ErrorManager, retry_on_io_error,
    safe_execute, validate_inputs, validate_file_path, validate_one_of,
    validate_non_negative_int, validate_kmer_sequence
)
from .exceptions import DatabaseError, ValidationError, ExportError, QueryError


class Database:
    """
    Python wrapper for RKDB database query operations.

    This class provides a high-level interface for querying k-mer databases
    created with RustKmer. It supports both memory-mapped and regular file access
    for optimal performance.

    Attributes:
        kmer_size (int): Size of k-mers in the database
        canonical (bool): Whether the database uses canonical k-mers
        sorted (bool): Whether the database is sorted
        uses_memory_mapping (bool): Whether memory mapping is being used

    Example:
        >>> from rustkmer import Database
        >>> db = Database()
        >>> db.load("sample.rkdb")
        >>> stats = db.get_stats()
        >>> print(f"Database has {stats.total_kmers} total k-mers")
    """

    def __init__(self, database_path: Optional[Union[str, Path]] = None) -> None:
        """
        Initialize a Database object.

        Args:
            database_path: Optional path to load a database immediately
        """
        self._db = SimpleDatabase()
        self._loaded = False

        if database_path:
            self.load(database_path)

    @handle_errors("database_load", strategies=[retry_on_io_error()])
    @validate_inputs({
        'database_path': validate_file_path
    })
    def load(self, database_path: Union[str, Path]) -> None:
        """
        Load a database from file.

        Automatically chooses between memory-mapped and regular file access
        based on file size (threshold: 100MB).

        Args:
            database_path: Path to the .rkdb database file

        Raises:
            DatabaseError: If loading fails or file format is invalid
            ValidationError: If file path is invalid
            FileNotFoundError: If the database file doesn't exist

        Example:
            >>> db = Database()
            >>> db.load("my_database.rkdb")
            >>> print(f"Loaded database with k={db.kmer_size}")
        """
        database_path = str(database_path)

        # Check file extension
        if not database_path.endswith('.rkdb'):
            raise ValidationError(
                "Database file must have .rkdb extension",
                error_code="INVALID_FILE_EXTENSION",
                parameter="database_path",
                expected_value=".rkdb",
                actual_value=Path(database_path).suffix
            )

        # Create error context
        context = ErrorContext(
            operation="database_load",
            component="Database.load",
            file_path=database_path
        )

        # Check if file exists
        file_path = Path(database_path)
        if not file_path.exists():
            raise FileNotFoundError(
                f"Database file not found: {database_path}",
                error_code="FILE_NOT_FOUND",
                file_path=database_path
            )

        # Add file size to context
        try:
            file_size = file_path.stat().st_size
            context.add_info("file_size_bytes", file_size)
        except Exception:
            context.add_info("file_size_bytes", "unknown")

        # Execute load with error handling
        try:
            safe_execute(
                self._db.load,
                database_path,
                log_errors=True
            )
            self._loaded = True
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Database file not found: {database_path}",
                error_code="FILE_NOT_FOUND",
                file_path=database_path
            ) from e
        except (IOError, OSError) as e:
            raise DatabaseError(
                f"Failed to read database file: {str(e)}",
                error_code="DATABASE_READ_FAILED",
                file_path=database_path,
                context=context.to_dict()
            ) from e
        except Exception as e:
            # Check if it's a format/validation error
            error_msg = str(e).lower()
            if "magic" in error_msg or "format" in error_msg or "version" in error_msg:
                raise DatabaseError(
                    f"Invalid database file format: {str(e)}",
                    error_code="INVALID_DATABASE_FORMAT",
                    file_path=database_path,
                    context=context.to_dict()
                ) from e
            else:
                raise DatabaseError(
                    f"Failed to load database: {str(e)}",
                    error_code="DATABASE_LOAD_FAILED",
                    file_path=database_path,
                    context=context.to_dict()
                ) from e

    @handle_errors("database_query")
    @validate_inputs({
        'kmer': lambda x: isinstance(x, str) and len(x) > 0
    })
    def query(self, kmer: str) -> QueryResult:
        """
        Query a single k-mer in the database.

        Args:
            kmer: The k-mer sequence to query

        Returns:
            QueryResult: Object containing the k-mer, its count, and whether it was found

        Raises:
            DatabaseError: If no database is loaded or query fails
            ValidationError: If k-mer is invalid
            QueryError: If the query operation fails

        Example:
            >>> result = db.query("ATCGATCGATCGATCGATCGATC")
            >>> if result.found:
            ...     print(f"K-mer found with count: {result.count}")
            ... else:
            ...     print("K-mer not found")
        """
        # Check if database is loaded
        if not self._loaded:
            raise DatabaseError(
                "No database loaded. Call load() first",
                error_code="DATABASE_NOT_LOADED"
            )

        # Normalize k-mer
        kmer = kmer.upper()

        # Validate k-mer length
        if len(kmer) != self.kmer_size:
            raise ValidationError(
                f"K-mer length ({len(kmer)}) doesn't match database k-mer size ({self.kmer_size})",
                error_code="INVALID_KMER_LENGTH",
                parameter="kmer",
                expected_value=self.kmer_size,
                actual_value=len(kmer)
            )

        # Validate k-mer sequence
        if not validate_kmer_sequence(kmer):
            raise ValidationError(
                "K-mer contains invalid characters (only A, T, C, G allowed)",
                error_code="INVALID_KMER_SEQUENCE",
                parameter="kmer",
                kmer_sequence=kmer
            )

        # Create error context
        context = ErrorContext(
            operation="database_query",
            component="Database.query",
            additional_info={
                "kmer_length": len(kmer),
                "expected_length": self.kmer_size
            }
        )

        # Execute query with error handling
        try:
            return safe_execute(
                self._db.query,
                kmer,
                log_errors=True
            )
        except Exception as e:
            raise QueryError(
                f"Failed to query k-mer '{kmer}': {str(e)}",
                error_code="QUERY_FAILED",
                kmer_sequence=kmer,
                context=context.to_dict()
            ) from e

    @handle_errors("database_query_batch")
    @validate_inputs({
        'kmers': lambda x: isinstance(x, list) and len(x) > 0
    })
    def query_batch(self, kmers: List[str]) -> List[QueryResult]:
        """
        Query multiple k-mers in batch.

        More efficient than individual queries for large numbers of k-mers.

        Args:
            kmers: List of k-mer sequences to query

        Returns:
            List[QueryResult]: List of query results in the same order as input

        Raises:
            DatabaseError: If no database is loaded or query fails
            ValidationError: If k-mers list is invalid or contains invalid k-mers
            QueryError: If the batch query operation fails

        Example:
            >>> kmers = ["ATCGATCGATCGATCGATCGATC", "GCTAGCTAGCTAGCTAGCTAG"]
            >>> results = db.query_batch(kmers)
            >>> for kmer, result in zip(kmers, results):
            ...     print(f"{kmer}: {result.count}")
        """
        # Check if database is loaded
        if not self._loaded:
            raise DatabaseError(
                "No database loaded. Call load() first",
                error_code="DATABASE_NOT_LOADED"
            )

        # Validate all k-mers
        validated_kmers = []
        invalid_kmers = []

        for i, kmer in enumerate(kmers):
            # Check type
            if not isinstance(kmer, str):
                raise ValidationError(
                    f"All k-mers must be strings (found {type(kmer)} at index {i})",
                    error_code="INVALID_KMER_TYPE",
                    parameter="kmers",
                    index=i
                )

            # Normalize and validate k-mer
            kmer = kmer.upper()

            # Check length
            if len(kmer) != self.kmer_size:
                invalid_kmers.append({
                    'index': i,
                    'kmer': kmer,
                    'error': f"Length {len(kmer)} != {self.kmer_size}"
                })
                continue

            # Check sequence
            if not validate_kmer_sequence(kmer):
                invalid_kmers.append({
                    'index': i,
                    'kmer': kmer,
                    'error': "Contains invalid characters (only A, T, C, G allowed)"
                })
                continue

            validated_kmers.append(kmer)

        # If there were invalid k-mers, report them
        if invalid_kmers:
            errors = [f"Index {item['index']}: {item['error']}" for item in invalid_kmers[:5]]
            if len(invalid_kmers) > 5:
                errors.append(f"... and {len(invalid_kmers) - 5} more")

            raise ValidationError(
                f"Invalid k-mers found in batch: {'; '.join(errors)}",
                error_code="INVALID_KMERS_IN_BATCH",
                parameter="kmers",
                invalid_count=len(invalid_kmers),
                valid_count=len(validated_kmers),
                examples=invalid_kmers[:3]
            )

        # Create error context
        context = ErrorContext(
            operation="database_query_batch",
            component="Database.query_batch",
            additional_info={
                "batch_size": len(validated_kmers),
                "kmer_length": self.kmer_size
            }
        )

        # Execute batch query with error handling
        try:
            return safe_execute(
                self._db.query_multiple,
                validated_kmers,
                log_errors=True
            )
        except Exception as e:
            raise QueryError(
                f"Failed to execute batch query on {len(validated_kmers)} k-mers: {str(e)}",
                error_code="BATCH_QUERY_FAILED",
                batch_size=len(validated_kmers),
                context=context.to_dict()
            ) from e

    def exists(self, kmer: str) -> bool:
        """
        Check if a k-mer exists in the database.

        Args:
            kmer: The k-mer sequence to check

        Returns:
            bool: True if the k-mer exists, False otherwise

        Example:
            >>> if db.exists("ATCGATCGATCGATCGATCGATC"):
            ...     print("K-mer found in database")
        """
        result = self.query(kmer)
        return result.found

    def get_count(self, kmer: str) -> int:
        """
        Get the count of a specific k-mer.

        Args:
            kmer: The k-mer sequence to query

        Returns:
            int: The k-mer count (0 if not found)

        Example:
            >>> count = db.get_count("ATCGATCGATCGATCGATCGATC")
            >>> print(f"K-mer count: {count}")
        """
        result = self.query(kmer)
        return result.count

    def get_stats(self, include_metadata: bool = True) -> DatabaseStats:
        """
        Get database statistics.

        Args:
            include_metadata: Whether to include file metadata in the statistics

        Returns:
            DatabaseStats: Object containing comprehensive database statistics

        Example:
            >>> stats = db.get_stats()
            >>> print(f"Total k-mers: {stats.total_kmers}")
            >>> print(f"Unique k-mers: {stats.unique_kmers}")
            >>> print(f"Min count: {stats.min_count}")
            >>> print(f"Max count: {stats.max_count}")
            >>> print(f"Mean count: {stats.mean_count:.2f}")
        """
        if not self._loaded:
            raise RuntimeError("No database loaded. Call load() first")

        stats = self._db.get_stats()

        # If Rust stats don't include file metadata, add it
        if include_metadata and hasattr(self, '_db') and hasattr(self._db, 'file_path'):
            from .metadata import extract_metadata
            metadata = extract_metadata(self._db.file_path)

            # Add file metadata to stats if it has a to_dict method
            if hasattr(stats, 'file_path') and not stats.file_path:
                stats.file_path = self._db.file_path

            # Add creation date if available
            if 'metadata' in metadata and 'created_date' in metadata['metadata']:
                if hasattr(stats, 'creation_date') and not stats.creation_date:
                    stats.creation_date = metadata['metadata']['created_date']

        return stats

    def close(self) -> None:
        """
        Close the database and release resources.

        For memory-mapped databases, this releases the memory mapping.
        The database object can be reused by calling load() again.

        Example:
            >>> db.close()
            >>> # Database can be reloaded
            >>> db.load("another_database.rkdb")
        """
        # SimpleDatabase doesn't have explicit close method
        # We just mark it as not loaded
        self._loaded = False

    @handle_errors("database_dump", strategies=[retry_on_io_error()])
    @validate_inputs({
        'output_path': validate_file_path,
        'format': validate_one_of(["text", "csv", "json", "tsv"]),
        'min_count': lambda x: x is None or validate_non_negative_int(x),
        'max_count': lambda x: x is None or validate_non_negative_int(x)
    })
    def dump(self, output_path: Union[str, Path], format: str = "text",
             min_count: Optional[int] = None, max_count: Optional[int] = None,
             progress_callback: Optional[callable] = None) -> None:
        """
        Export database contents to a file.

        Args:
            output_path: Path for the output file
            format: Export format - 'text', 'csv', 'json', or 'tsv' (default: 'text')
            min_count: Optional minimum count filter (inclusive)
            max_count: Optional maximum count filter (inclusive)
            progress_callback: Optional callback for progress updates (0-100)

        Raises:
            DatabaseError: If no database is loaded or export fails
            ValidationError: If parameters are invalid
            ExportError: If there's an error writing the output file

        Example:
            >>> db = Database("sample.rkdb")
            >>> # Export as text format (k-mer<TAB>count)
            >>> db.dump("export.txt")
            >>>
            >>> # Export as CSV format
            >>> db.dump("export.csv", format="csv")
            >>>
            >>> # Export as JSON format with metadata
            >>> db.dump("export.json", format="json")
            >>>
            >>> # Export with count filtering
            >>> db.dump("filtered.txt", min_count=5, max_count=100)
        """
        # Check if database is loaded
        if not self._loaded:
            raise DatabaseError(
                "No database loaded. Call load() first",
                error_code="DATABASE_NOT_LOADED"
            )

        # Convert filters to proper types
        min_count_u32 = None if min_count is None else max(0, int(min_count))
        max_count_u32 = None if max_count is None else max(0, int(max_count))

        # Validate filter ranges
        if min_count_u32 is not None and max_count_u32 is not None:
            if min_count_u32 > max_count_u32:
                raise ValidationError(
                    f"min_count ({min_count_u32}) cannot be greater than max_count ({max_count_u32})",
                    error_code="INVALID_FILTER_RANGE",
                    parameter="min_count"
                )

        # Create error context
        context = ErrorContext(
            operation="database_dump",
            component="Database.dump",
            file_path=output_path,
            additional_info={
                "format": format.lower(),
                "min_count": min_count_u32,
                "max_count": max_count_u32
            }
        )

        # Execute dump with error handling
        try:
            safe_execute(
                self._db.dump,
                str(output_path),
                format.lower(),
                min_count_u32,
                max_count_u32,
                progress_callback,
                log_errors=True
            )
        except Exception as e:
            # Wrap in appropriate exception
            if "IO" in str(type(e)) or "file" in str(e).lower():
                raise ExportError(
                    f"Failed to write export file: {str(e)}",
                    error_code="EXPORT_WRITE_FAILED",
                    file_path=str(output_path)
                ) from e
            else:
                raise DatabaseError(
                    f"Database export failed: {str(e)}",
                    error_code="EXPORT_FAILED",
                    context=context.to_dict()
                ) from e

    def reload(self, force_memory_mapping: Optional[bool] = None) -> None:
        """
        Reload the current database.

        Args:
            force_memory_mapping: If True, force memory mapping.
                                  If False, force regular file access.
                                  If None, auto-detect based on file size.

        Example:
            >>> # Force use memory mapping
            >>> db.reload(force_memory_mapping=True)
            >>> # Force regular file access
            >>> db.reload(force_memory_mapping=False)
        """
        if not self._loaded:
            raise RuntimeError("No database loaded. Call load() first")

        self._db.reload(force_memory_mapping)

    @property
    def kmer_size(self) -> int:
        """Get the k-mer size of the loaded database."""
        if not self._loaded:
            raise RuntimeError("No database loaded. Call load() first")
        return self._db.kmer_size

    @property
    def canonical(self) -> bool:
        """Check if the database uses canonical k-mers."""
        if not self._loaded:
            raise RuntimeError("No database loaded. Call load() first")
        return self._db.canonical

    @property
    def sorted(self) -> bool:
        """Check if the database is sorted."""
        if not self._loaded:
            raise RuntimeError("No database loaded. Call load() first")
        return self._db.sorted

    @property
    def uses_memory_mapping(self) -> bool:
        """Check if the database is using memory mapping."""
        if not self._loaded:
            raise RuntimeError("No database loaded. Call load() first")
        return self._db.uses_memory_mapping()

    def __repr__(self) -> str:
        """String representation of the Database object."""
        if self._loaded:
            return (f"Database(k={self.kmer_size}, canonical={self.canonical}, "
                   f"sorted={self.sorted}, memory_mapped={self.uses_memory_mapping})")
        return "Database(not loaded)"

    def __enter__(self) -> 'Database':
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[types.TracebackType]) -> None:
        """Context manager exit - automatically close database."""
        self.close()

    @handle_errors("database_merge", strategies=[retry_on_io_error()])
    @validate_inputs({
        'output_path': validate_file_path,
        'strategy': validate_one_of(["sum", "max", "min"])
    })
    def merge(self, other: 'Database', output_path: Union[str, Path],
              strategy: str = "sum", progress_callback: Optional[callable] = None) -> 'Database':
        """
        Merge this database with another database.

        Args:
            other: Another Database object to merge with
            output_path: Path for the merged database file
            strategy: Merge strategy - 'sum', 'max', or 'min'
            progress_callback: Optional callback for progress updates (0-100)

        Returns:
            Database: New database object with merged data

        Raises:
            DatabaseError: If databases are incompatible or merge fails
            ValidationError: If parameters are invalid
            MergeError: If the merge operation fails

        Example:
            >>> db1 = Database("sample1.rkdb")
            >>> db2 = Database("sample2.rkdb")
            >>> merged = db1.merge(db2, "merged.rkdb", strategy="sum")
            >>> print(f"Merged database has {merged.get_unique_kmers()} unique k-mers")
        """
        # Check if databases are loaded
        if not self._loaded:
            raise DatabaseError(
                "No database loaded. Call load() first.",
                error_code="DATABASE_NOT_LOADED"
            )
        if not other._loaded:
            raise DatabaseError(
                "Other database not loaded.",
                error_code="OTHER_DATABASE_NOT_LOADED"
            )

        # Validate database compatibility
        if self.kmer_size != other.kmer_size:
            raise MergeError(
                f"Databases have different k-mer sizes: {self.kmer_size} vs {other.kmer_size}",
                error_code="INCOMPATIBLE_DATABASES",
                db1_kmer_size=self.kmer_size,
                db2_kmer_size=other.kmer_size
            )

        if self.canonical != other.canonical:
            raise MergeError(
                f"Databases have different canonical settings: {self.canonical} vs {other.canonical}",
                error_code="INCOMPATIBLE_DATABASES",
                db1_canonical=self.canonical,
                db2_canonical=other.canonical
            )

        # Create error context
        context = ErrorContext(
            operation="database_merge",
            component="Database.merge",
            file_path=output_path,
            additional_info={
                "strategy": strategy,
                "db1_kmer_size": self.kmer_size,
                "db2_kmer_size": other.kmer_size,
                "db1_canonical": self.canonical,
                "db2_canonical": other.canonical
            }
        )

        # Convert Path to string if needed
        output_path = str(output_path)

        # Execute merge with error handling
        try:
            safe_execute(
                self._db.merge,
                self._db,
                other._db,
                output_path,
                strategy,
                progress_callback,
                log_errors=True
            )

            # Return new Database object with merged data
            return Database(output_path)
        except (IOError, OSError) as e:
            raise MergeError(
                f"Failed to write merged database: {str(e)}",
                error_code="MERGE_WRITE_FAILED",
                file_path=output_path,
                context=context.to_dict()
            ) from e
        except Exception as e:
            raise MergeError(
                f"Database merge failed: {str(e)}",
                error_code="MERGE_FAILED",
                context=context.to_dict()
            ) from e

    def merge_multiple(self, databases: List['Database'], output_path: Union[str, Path],
                      strategy: str = "sum", progress_callback: Optional[callable] = None) -> 'Database':
        """
        Merge this database with multiple other databases.

        Args:
            databases: List of Database objects to merge
            output_path: Path for the merged database file
            strategy: Merge strategy - 'sum', 'max', or 'min'
            progress_callback: Optional callback for progress updates (0-100)

        Returns:
            Database: New database object with merged data

        Raises:
            ValueError: If databases are incompatible
            RuntimeError: If merge operation fails

        Example:
            >>> db1 = Database("sample1.rkdb")
            >>> db2 = Database("sample2.rkdb")
            >>> db3 = Database("sample3.rkdb")
            >>> merged = db1.merge_multiple([db2, db3], "merged.rkdb")
            >>> print(f"Merged {len(databases)+1} databases")
        """
        if not self._loaded:
            raise RuntimeError("No database loaded. Call load() first.")

        # Validate all databases are loaded
        for i, db in enumerate(databases):
            if not db._loaded:
                raise RuntimeError(f"Database {i+1} not loaded.")

        # Validate strategy
        if strategy not in ["sum", "max", "min"]:
            raise ValueError("Invalid merge strategy. Must be 'sum', 'max', or 'min'")

        # Convert Path to string if needed
        output_path = str(output_path)

        # Extract Rust database objects
        rust_dbs = [db._db for db in databases]

        # Perform merge
        self._db.merge_multiple(self._db, rust_dbs, output_path, strategy, progress_callback)

        # Return new Database object with merged data
        return Database(output_path)


# Backward compatibility aliases
DatabaseHeader = DatabaseStats  # For compatibility with older code


def load_database(database_path: Union[str, Path]) -> Database:
    """
    Convenience function to load a database in one call.

    Args:
        database_path: Path to the .rkdb database file

    Returns:
        Database: Loaded database object

    Example:
        >>> from rustkmer.database import load_database
        >>> db = load_database("my_database.rkdb")
        >>> stats = db.get_stats()
    """
    return Database(database_path)


def query_database(database_path: Union[str, Path], kmer: str) -> QueryResult:
    """
    Convenience function to query a k-mer in one call.

    Args:
        database_path: Path to the .rkdb database file
        kmer: The k-mer sequence to query

    Returns:
        QueryResult: Query result

    Example:
        >>> from rustkmer.database import query_database
        >>> result = query_database("my_database.rkdb", "ATCGATCGATCGATCGATCGATC")
        >>> print(f"Count: {result.count}")
    """
    with Database(database_path) as db:
        return db.query(kmer)


def batch_query_database(database_path: Union[str, Path], kmers: List[str]) -> List[QueryResult]:
    """
    Convenience function to query multiple k-mers in one call.

    Args:
        database_path: Path to the .rkdb database file
        kmers: List of k-mer sequences to query

    Returns:
        List[QueryResult]: List of query results

    Example:
        >>> from rustkmer.database import batch_query_database
        >>> kmers = ["ATCGATCGATCGATCGATCGATC", "GCTAGCTAGCTAGCTAGCTAG"]
        >>> results = batch_query_database("my_database.rkdb", kmers)
        >>> for result in results:
        ...     print(f"{result.kmer}: {result.count}")
    """
    with Database(database_path) as db:
        return db.query_batch(kmers)


# Import thread safety utilities for convenience
from .thread_safety import (
    ThreadSafeDatabase,
    make_thread_safe,
    with_thread_safe,
    ConnectionPool,
    ThreadSafeCache,
    thread_safe
)