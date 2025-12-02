"""
Custom exception classes for RustKmer Python bindings.

This module defines the exception hierarchy used by RustKmer for error handling
across the Python-Rust boundary.
"""

from typing import Optional, Any


class RustKmerError(Exception):
    """Base exception for all RustKmer errors."""

    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details

    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class KmerError(RustKmerError, ValueError):
    """Exception for k-mer related errors."""

    def __init__(self, message: str, kmer: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.kmer = kmer


class DatabaseError(RustKmerError, RuntimeError):
    """Exception for database-related errors."""

    def __init__(self, message: str, file_path: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.file_path = file_path


class FuzzyQueryError(RustKmerError, ValueError):
    """Exception for fuzzy query related errors."""

    def __init__(self, message: str, query: Optional[str] = None, max_distance: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.query = query
        self.max_distance = max_distance


class SequenceError(RustKmerError, ValueError):
    """Exception for sequence-related errors."""

    def __init__(self, message: str, sequence: Optional[str] = None, position: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.sequence = sequence
        self.position = position


class ConfigurationError(RustKmerError, ValueError):
    """Exception for configuration-related errors."""

    def __init__(self, message: str, parameter: Optional[str] = None, value: Optional[Any] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.parameter = parameter
        self.value = value


class ValidationError(RustKmerError, ValueError):
    """Exception for data validation errors."""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.field = field