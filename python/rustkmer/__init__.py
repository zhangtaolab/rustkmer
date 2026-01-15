"""RustKmer Python Bindings

A Python package for querying k-mer databases through rustkmer CLI tool.
This package provides an object-oriented interface for database operations
without requiring PyO3.
"""

__version__ = "0.2.0"
__author__ = "RustKmer Team"
__email__ = "team@rustkmer.org"

# Import main classes
from .database import Database
from .query import QueryResult
from .stats import DatabaseStats
from .fuzzy_query import FuzzyMatchResult, FuzzyQueryResult, FuzzyBatchResult
from .backend import (
    DatabaseBackend,
    LoadMode,
    SubprocessBackend,
    PyO3Backend,
    create_backend,
)

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
    FuzzyQueryError,
    InvalidMutationToleranceError,
    CombinatorialExplosionError,
    BatchQueryError,
)

# Public API
__all__ = [
    # Main classes
    "Database",
    "QueryResult",
    "DatabaseStats",
    "DatabaseBackend",
    "LoadMode",
    "SubprocessBackend",
    "PyO3Backend",
    "create_backend",
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
    "FuzzyQueryError",
    "InvalidMutationToleranceError",
    "CombinatorialExplosionError",
    "BatchQueryError",
    # Fuzzy query classes
    "FuzzyMatchResult",
    "FuzzyQueryResult",
    "FuzzyBatchResult",
]
