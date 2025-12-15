"""Exception hierarchy for rustkmer Python bindings.

This module defines all custom exceptions used by the rustkmer package
to provide clear, actionable error messages for different failure scenarios.
"""

from typing import Optional


class RustKmerError(Exception):
    """Base exception for all rustkmer errors.

    All rustkmer-specific exceptions inherit from this class, allowing
    users to catch all rustkmer errors with a single except clause.
    """
    pass


class DatabaseError(RustKmerError):
    """Base class for all database-related errors."""
    pass


class DatabaseNotFoundError(DatabaseError, FileNotFoundError):
    """Raised when a database file cannot be found at the specified path."""

    def __init__(self, path: str, message: Optional[str] = None):
        if message is None:
            message = f"Database file not found: {path}"
        super().__init__(message)
        self.path = path


class InvalidDatabaseError(DatabaseError):
    """Raised when a file is not a valid rustkmer database."""

    def __init__(self, path: str, reason: Optional[str] = None):
        if reason is None:
            reason = "File is not a valid rustkmer database"
        message = f"Invalid database '{path}': {reason}"
        super().__init__(message)
        self.path = path
        self.reason = reason


class DatabaseCorruptedError(DatabaseError):
    """Raised when a database file appears to be corrupted or unreadable."""

    def __init__(self, path: str, message: Optional[str] = None):
        if message is None:
            message = f"Database file appears to be corrupted: {path}"
        super().__init__(message)
        self.path = path


class QueryError(RustKmerError):
    """Base class for all query-related errors."""
    pass


class InvalidKmerError(QueryError, ValueError):
    """Raised when an invalid k-mer sequence is provided."""

    def __init__(self, kmer: str, reason: Optional[str] = None):
        if reason is None:
            reason = "contains invalid characters or has incorrect length"
        message = f"Invalid k-mer '{kmer}': {reason}"
        super().__init__(message)
        self.kmer = kmer
        self.reason = reason


class KmerLengthError(InvalidKmerError):
    """Raised when k-mer length doesn't match database k-mer size."""

    def __init__(self, kmer: str, expected: int, actual: int):
        message = (
            f"K-mer length mismatch: expected {expected}, got {actual} "
            f"for k-mer '{kmer}'"
        )
        super().__init__(kmer, message)
        self.expected_length = expected
        self.actual_length = actual


class FuzzyQueryError(QueryError):
    """Base exception for fuzzy query operations."""
    pass


class InvalidMutationToleranceError(FuzzyQueryError):
    """Raised when mutation tolerance is out of valid range."""
    pass


class InvalidPositionMutationError(FuzzyQueryError):
    """Raised when position-mutations parameter has invalid format or values."""

    def __init__(self, message: str, position_config: Optional[str] = None):
        super().__init__(message)
        self.position_config = position_config


class CombinatorialExplosionError(FuzzyQueryError):
    """Raised when fuzzy query would generate too many variants."""
    pass


class BatchQueryError(FuzzyQueryError):
    """Raised when batch fuzzy query encounters issues."""
    pass


class SubprocessError(RustKmerError):
    """Raised when subprocess calls to rustkmer CLI fail."""

    def __init__(self, command: str, returncode: int, stderr: Optional[str] = None):
        message = f"rustkmer command failed with code {returncode}: {command}"
        if stderr:
            message += f"\nStderr: {stderr}"
        super().__init__(message)
        self.command = command
        self.returncode = returncode
        self.stderr = stderr


class ConfigurationError(RustKmerError):
    """Raised when there's a configuration issue with the rustkmer package."""

    def __init__(self, message: str):
        super().__init__(f"Configuration error: {message}")