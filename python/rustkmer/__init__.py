"""RustKmer Python Bindings

A Python package for querying k-mer databases through the rustkmer CLI tool.
This package provides an object-oriented interface for database operations
without requiring PyO3.
"""

__version__ = "0.1.0"
__author__ = "RustKmer Team"
__email__ = "team@rustkmer.org"

# Import main classes
from .database import Database
from .query import QueryResult
from .stats import DatabaseStats

# Import exceptions
from .exceptions import (
    RustKmerError,
    DatabaseError,
    DatabaseNotFoundError,
    InvalidDatabaseError,
    DatabaseCorruptedError,
    QueryError,
    InvalidKmerError,
    KmerLengthError,
    SubprocessError,
    ConfigurationError,
)

# Public API
__all__ = [
    # Main classes
    "Database",
    "QueryResult",
    "DatabaseStats",

    # Exceptions
    "RustKmerError",
    "DatabaseError",
    "DatabaseNotFoundError",
    "InvalidDatabaseError",
    "DatabaseCorruptedError",
    "QueryError",
    "InvalidKmerError",
    "KmerLengthError",
    "SubprocessError",
    "ConfigurationError",
]