"""
RustKmer Python Exception Hierarchy

This module defines all Python exceptions for the RustKmer library,
providing structured error handling that maps to Rust error types.
"""

from typing import Optional, Any, Dict


class RustKmerError(Exception):
    """Base exception class for all RustKmer errors."""

    def __init__(self, message: str, error_code: Optional[str] = None, context: Optional[Dict[str, Any]] = None, *args):
        # Pass all arguments to Exception base class for proper args handling
        # Store all positional args (including error_code and context) in args tuple
        all_args = (message,)
        if error_code is not None:
            all_args = all_args + (error_code,)
        if context is not None:
            all_args = all_args + (context,)
        all_args = all_args + args
        super().__init__(*all_args)

        # Store attributes
        self.message = message
        self.error_code = error_code
        self.context = context or {}

    def __str__(self) -> str:
        return str(self.message) if self.message is not None else ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/debugging."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context
        }


class SequenceError(RustKmerError, ValueError):
    """Raised when invalid DNA sequences are encountered."""

    def __init__(self, message: str, sequence: Optional[str] = None, position: Optional[int] = None):
        context = {}
        if sequence is not None:
            context["sequence"] = sequence
        if position is not None:
            context["position"] = position
        super().__init__(message, error_code="SEQ001", context=context)
        self.sequence = sequence
        self.position = position


class DatabaseError(RustKmerError, RuntimeError):
    """Raised for database-related errors."""

    def __init__(self, message: str, database_path: Optional[str] = None, operation: Optional[str] = None):
        # Handle message formatting if it contains placeholders
        if database_path is not None and '{}' in message:
            message = message.format(database_path)
        elif isinstance(database_path, str) and database_path and operation is None:
            # If second arg is a string and no operation specified,
            # assume it's database_path for formatting
            message = message.format(database_path)
            database_path = None  # Don't add to context since it was used for formatting

        context = {}
        if database_path is not None:
            context["database_path"] = database_path
        if operation is not None:
            context["operation"] = operation
        super().__init__(message, error_code="DB001", context=context)
        self.database_path = database_path
        self.operation = operation


class DatabaseCorruptionError(DatabaseError):
    """Raised when database file appears to be corrupted."""

    def __init__(self, message: str, database_path: Optional[str] = None, offset: Optional[int] = None):
        context = {}
        if database_path is not None:
            context["database_path"] = database_path
        if offset is not None:
            context["offset"] = offset
        super().__init__(message, database_path, "validation")
        self.error_code = "DB002"
        self.context.update(context)
        self.offset = offset


class FileNotFoundError(DatabaseError):
    """Raised when a required file cannot be found."""

    def __init__(self, message: str, file_path: str):
        context = {"file_path": file_path}
        super().__init__(message, file_path, "file_access")
        self.error_code = "FS001"
        self.context.update(context)
        self.file_path = file_path


class PermissionError(DatabaseError):
    """Raised when lacking permissions to access a file."""

    def __init__(self, message: str, file_path: str):
        context = {"file_path": file_path}
        super().__init__(message, file_path, "file_access")
        self.error_code = "FS002"
        self.context.update(context)
        self.file_path = file_path


class ValueError(RustKmerError, ValueError):
    """Raised when invalid parameter values are provided."""

    def __init__(self, message: str, parameter_name: Optional[str] = None, parameter_value: Optional[Any] = None):
        context = {}
        if parameter_name is not None:
            context["parameter_name"] = parameter_name
        if parameter_value is not None:
            context["parameter_value"] = str(parameter_value)
        super().__init__(message, error_code="VAL001", context=context)
        self.parameter_name = parameter_name
        self.parameter_value = parameter_value


class KmerSizeError(ValueError):
    """Raised when invalid k-mer size is specified."""

    def __init__(self, kmer_size: int, valid_range: tuple = (1, 128)):
        message = f"Invalid k-mer size: {kmer_size}. Valid range: {valid_range[0]}-{valid_range[1]}"
        super().__init__(message, "kmer_size", kmer_size)
        self.error_code = "VAL002"
        self.kmer_size = kmer_size
        self.valid_range = valid_range


class ThreadCountError(ValueError):
    """Raised when invalid thread count is specified."""

    def __init__(self, thread_count: int):
        message = f"Invalid thread count: {thread_count}. Must be a positive integer."
        super().__init__(message, "thread_count", thread_count)
        self.error_code = "VAL003"
        self.thread_count = thread_count


class MemoryError(RustKmerError, MemoryError):
    """Raised when memory allocation fails or memory limits are exceeded."""

    def __init__(self, message: str, requested_bytes: Optional[int] = None, limit_bytes: Optional[int] = None):
        context = {}
        if requested_bytes is not None:
            context["requested_bytes"] = requested_bytes
        if limit_bytes is not None:
            context["limit_bytes"] = limit_bytes
        super().__init__(message, error_code="MEM001", context=context)
        self.requested_bytes = requested_bytes
        self.limit_bytes = limit_bytes


class EncodingError(RustKmerError):
    """Raised when k-mer encoding/decoding fails."""

    def __init__(self, message: str, kmer: Optional[str] = None, encoding_type: Optional[str] = None):
        context = {}
        if kmer is not None:
            context["kmer"] = kmer
        if encoding_type is not None:
            context["encoding_type"] = encoding_type
        super().__init__(message, error_code="ENC001", context=context)
        self.kmer = kmer
        self.encoding_type = encoding_type


class QueryError(RustKmerError):
    """Raised when database queries fail."""

    def __init__(self, message: str, **kwargs):
        # Store all kwargs as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)
        super().__init__(message)


class FuzzyQueryError(QueryError):
    """Raised when fuzzy query operations fail."""

    def __init__(self, message: str, **kwargs):
        # Store all kwargs as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)
        super().__init__(message)


class MergeError(DatabaseError):
    """Raised when database merge operations fail."""

    def __init__(self, message: str, **kwargs):
        # Store all kwargs as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)
        super().__init__(message)


class ExportError(DatabaseError):
    """Raised when database export operations fail."""

    def __init__(self, message: str, **kwargs):
        # Store all kwargs as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)
        super().__init__(message)


class CompressionError(RustKmerError):
    """Raised when compression/decompression operations fail."""

    def __init__(self, message: str, algorithm: Optional[str] = None, file_path: Optional[str] = None):
        context = {}
        if algorithm is not None:
            context["algorithm"] = algorithm
        if file_path is not None:
            context["file_path"] = file_path
        super().__init__(message, error_code="CMP001", context=context)
        self.algorithm = algorithm
        self.file_path = file_path


class ProgressCallbackError(RustKmerError):
    """Raised when progress callback operations fail."""

    def __init__(self, message: str, callback_name: Optional[str] = None):
        context = {}
        if callback_name is not None:
            context["callback_name"] = callback_name
        super().__init__(message, error_code="PRG001", context=context)
        self.callback_name = callback_name


class ThreadSafetyError(RustKmerError):
    """Raised when thread safety violations are detected."""

    def __init__(self, message: str, operation: Optional[str] = None, thread_id: Optional[str] = None):
        context = {}
        if operation is not None:
            context["operation"] = operation
        if thread_id is not None:
            context["thread_id"] = thread_id
        super().__init__(message, error_code="THR001", context=context)
        self.operation = operation
        self.thread_id = thread_id


class ValidationError(ValueError):
    """Raised when validation checks fail."""

    def __init__(self, message: str, *args, **kwargs):
        # Handle message formatting if it contains placeholders and args provided
        if args and '{}' in message:
            try:
                message = message.format(*args)
            except (IndexError, KeyError):
                # If formatting fails, use original message
                pass

        # Store all kwargs as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)
        super().__init__(message)


class StatsError(DatabaseError):
    """Raised when statistics calculation fails."""

    def __init__(self, message: str, **kwargs):
        # Store all kwargs as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)
        super().__init__(message)


class UtilsError(RustKmerError):
    """Raised when utility operations fail."""

    def __init__(self, message: str, **kwargs):
        # Store all kwargs as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)
        super().__init__(message)


class KmerCountingError(RustKmerError):
    """Raised when k-mer counting operations fail."""

    def __init__(self, message: str, **kwargs):
        # Store all kwargs as attributes
        for key, value in kwargs.items():
            setattr(self, key, value)
        super().__init__(message)


class NotImplementedError(RustKmerError):
    """Raised when attempting to use functionality that is not yet implemented."""

    def __init__(self, message: str, feature_name: Optional[str] = None):
        context = {}
        if feature_name is not None:
            context["feature_name"] = feature_name
        super().__init__(message, error_code="IMP001", context=context)
        self.feature_name = feature_name


# Exception mapping dictionary for Rust error translation
RUST_ERROR_MAPPING = {
    # Database errors
    "DatabaseError": DatabaseError,
    "DatabaseCorruptionError": DatabaseCorruptionError,
    "FileNotFoundError": FileNotFoundError,
    "PermissionError": PermissionError,

    # Value errors
    "ValueError": ValueError,
    "KmerSizeError": KmerSizeError,
    "ThreadCountError": ThreadCountError,
    "ValidationError": ValidationError,

    # Sequence errors
    "SequenceError": SequenceError,
    "EncodingError": EncodingError,

    # Query errors
    "QueryError": QueryError,
    "FuzzyQueryError": FuzzyQueryError,

    # Operation errors
    "MergeError": MergeError,
    "ExportError": ExportError,
    "CompressionError": CompressionError,
    "StatsError": StatsError,

    # System errors
    "MemoryError": MemoryError,
    "ThreadSafetyError": ThreadSafetyError,
    "ProgressCallbackError": ProgressCallbackError,
    "UtilsError": UtilsError,
    "KmerCountingError": KmerCountingError,
}


def translate_rust_error(error_type: str, message: str, **kwargs) -> RustKmerError:
    """
    Translate Rust error to Python exception.

    Args:
        error_type: Rust error type name
        message: Error message
        **kwargs: Additional error context

    Returns:
        Appropriate Python exception instance
    """
    exception_class = RUST_ERROR_MAPPING.get(error_type, RustKmerError)
    return exception_class(message, **kwargs)