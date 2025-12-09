"""
Enhanced error handling utilities for RustKmer Python API.

Provides comprehensive error handling with context management,
error recovery strategies, and detailed error reporting.
"""

import sys
import traceback
from typing import Dict, Any, Optional, List, Callable, Union, Type
from pathlib import Path
from contextlib import contextmanager
from functools import wraps
from enum import Enum

from .exceptions import (
    RustKmerError,
    DatabaseError,
    QueryError,
    ValidationError,
    MergeError,
    ExportError,
    FuzzyQueryError,
    StatsError,
    UtilsError,
    KmerCountingError,
    EncodingError
)
from .logging_config import get_logger, get_error_handler


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorContext:
    """Context information for errors."""

    def __init__(self,
                 operation: str,
                 component: Optional[str] = None,
                 file_path: Optional[Union[str, Path]] = None,
                 additional_info: Optional[Dict[str, Any]] = None):
        """
        Initialize error context.

        Args:
            operation: Operation being performed
            component: Component/module where error occurred
            file_path: File being processed (if applicable)
            additional_info: Additional context information
        """
        self.operation = operation
        self.component = component
        self.file_path = str(file_path) if file_path else None
        self.additional_info = additional_info or {}
        self.timestamp = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            'operation': self.operation,
            'component': self.component,
            'file_path': self.file_path,
            'additional_info': self.additional_info,
            'timestamp': self.timestamp
        }

    def add_info(self, key: str, value: Any) -> 'ErrorContext':
        """Add additional information to context."""
        self.additional_info[key] = value
        return self


class ErrorRecoveryStrategy:
    """Base class for error recovery strategies."""

    def can_recover(self, error: Exception, context: ErrorContext) -> bool:
        """
        Check if error can be recovered from.

        Args:
            error: Exception that occurred
            context: Error context

        Returns:
            True if error can be recovered from
        """
        return False

    def recover(self, error: Exception, context: ErrorContext) -> Any:
        """
        Attempt to recover from error.

        Args:
            error: Exception that occurred
            context: Error context

        Returns:
            Recovery result

        Raises:
            NotImplementedError: If recovery not implemented
        """
        raise NotImplementedError("Recovery strategy not implemented")


class RetryStrategy(ErrorRecoveryStrategy):
    """Retry strategy for transient errors."""

    def __init__(self,
                 max_retries: int = 3,
                 delay_seconds: float = 1.0,
                 backoff_factor: float = 2.0,
                 retry_on: Optional[List[Type[Exception]]] = None):
        """
        Initialize retry strategy.

        Args:
            max_retries: Maximum number of retry attempts
            delay_seconds: Initial delay between retries
            backoff_factor: Factor to increase delay by each retry
            retry_on: List of exception types to retry on
        """
        self.max_retries = max_retries
        self.delay_seconds = delay_seconds
        self.backoff_factor = backoff_factor
        self.retry_on = retry_on or [IOError, OSError]

    def can_recover(self, error: Exception, context: ErrorContext) -> bool:
        """Check if error is recoverable with retry."""
        return any(isinstance(error, exc_type) for exc_type in self.retry_on)

    def recover(self, error: Exception, context: ErrorContext) -> Any:
        """
        Retry operation with exponential backoff.

        Returns:
            None (operation will be retried by caller)
        """
        import time

        retry_count = context.additional_info.get('retry_count', 0)
        if retry_count >= self.max_retries:
            raise error

        delay = self.delay_seconds * (self.backoff_factor ** retry_count)
        time.sleep(delay)

        # Update retry count
        context.add_info('retry_count', retry_count + 1)


class FallbackStrategy(ErrorRecoveryStrategy):
    """Fallback strategy for using alternative methods."""

    def __init__(self,
                 fallback_func: Callable,
                 fallback_args: Optional[Dict[str, Any]] = None):
        """
        Initialize fallback strategy.

        Args:
            fallback_func: Fallback function to call
            fallback_args: Arguments for fallback function
        """
        self.fallback_func = fallback_func
        self.fallback_args = fallback_args or {}

    def can_recover(self, error: Exception, context: ErrorContext) -> bool:
        """Check if fallback is available."""
        return self.fallback_func is not None

    def recover(self, error: Exception, context: ErrorContext) -> Any:
        """Execute fallback strategy."""
        logger = get_logger()
        logger.warning(f"Using fallback strategy for {context.operation}")

        try:
            return self.fallback_func(**self.fallback_args)
        except Exception as fallback_error:
            logger.error(f"Fallback strategy failed: {fallback_error}")
            raise error  # Raise original error


class ErrorManager:
    """Manages error handling, logging, and recovery."""

    def __init__(self):
        """Initialize error manager."""
        self.logger = get_logger()
        self.error_handler = get_error_handler()
        self.strategies: List[ErrorRecoveryStrategy] = []
        self.error_history: List[Dict[str, Any]] = []

    def add_strategy(self, strategy: ErrorRecoveryStrategy) -> None:
        """Add error recovery strategy."""
        self.strategies.append(strategy)

    def handle_error(self,
                    error: Exception,
                    context: ErrorContext,
                    reraise: bool = True) -> Optional[Any]:
        """
        Handle an error with recovery attempts.

        Args:
            error: Exception to handle
            context: Error context
            reraise: Whether to reraise if unrecoverable

        Returns:
            Recovery result if successful, None otherwise
        """
        import time
        context.timestamp = time.time()

        # Log error
        self.logger.error(
            f"Error in {context.operation}: {str(error)}",
            exception=error,
            **context.to_dict()
        )

        # Record error
        error_record = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context.to_dict(),
            'traceback': traceback.format_exc()
        }
        self.error_history.append(error_record)

        # Attempt recovery
        for strategy in self.strategies:
            try:
                if strategy.can_recover(error, context):
                    self.logger.info(f"Attempting recovery with {type(strategy).__name__}")
                    result = strategy.recover(error, context)
                    self.logger.info("Recovery successful")
                    return result
            except Exception as recovery_error:
                self.logger.warning(f"Recovery failed: {recovery_error}")
                continue

        # No recovery succeeded
        if reraise:
            raise error
        return None

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors encountered."""
        if not self.error_history:
            return {'total_errors': 0}

        error_counts = {}
        for record in self.error_history:
            error_type = record['error_type']
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

        return {
            'total_errors': len(self.error_history),
            'error_counts': error_counts,
            'recent_errors': self.error_history[-10:]  # Last 10 errors
        }


class ErrorReporter:
    """Generates detailed error reports."""

    def __init__(self, output_dir: Optional[Union[str, Path]] = None):
        """
        Initialize error reporter.

        Args:
            output_dir: Directory to save reports
        """
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.output_dir.mkdir(exist_ok=True)

    def generate_report(self, error_manager: ErrorManager) -> Path:
        """
        Generate error report.

        Args:
            error_manager: Error manager with error history

        Returns:
            Path to generated report file
        """
        report_file = self.output_dir / "error_report.json"

        import json
        from datetime import datetime

        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': error_manager.get_error_summary(),
            'full_history': error_manager.error_history
        }

        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        # Generate text report
        text_report = self.output_dir / "error_report.txt"
        with open(text_report, 'w') as f:
            f.write("RustKmer Error Report\n")
            f.write("=" * 30 + "\n\n")
            f.write(f"Generated: {report['generated_at']}\n\n")

            summary = report['summary']
            f.write(f"Total Errors: {summary['total_errors']}\n\n")

            if summary['total_errors'] > 0:
                f.write("Error Types:\n")
                for error_type, count in summary['error_counts'].items():
                    f.write(f"  {error_type}: {count}\n")
                f.write("\n")

                f.write("Recent Errors (last 10):\n")
                for error in summary['recent_errors']:
                    f.write(f"\n{error['error_type']}: {error['error_message']}\n")
                    if error['context'].get('operation'):
                        f.write(f"  Operation: {error['context']['operation']}\n")
                    if error['context'].get('file_path'):
                        f.write(f"  File: {error['context']['file_path']}\n")

        return report_file


# Decorators for error handling
def handle_errors(context_operation: str,
                 strategies: Optional[List[ErrorRecoveryStrategy]] = None,
                 reraise: bool = True):
    """
    Decorator for automatic error handling.

    Args:
        context_operation: Description of operation
        strategies: List of recovery strategies
        reraise: Whether to reraise unrecoverable errors

    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create error context
            context = ErrorContext(
                operation=context_operation,
                component=f"{func.__module__}.{func.__name__}"
            )

            # Add argument info
            if args:
                context.add_info('args_count', len(args))
            if kwargs:
                context.add_info('kwargs_keys', list(kwargs.keys()))

            # Try to execute function
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Handle error
                manager = ErrorManager()

                # Add strategies if provided
                if strategies:
                    for strategy in strategies:
                        manager.add_strategy(strategy)

                result = manager.handle_error(e, context, reraise=reraise)
                return result

        return wrapper
    return decorator


def safe_execute(func: Callable,
                *args,
                default_value: Any = None,
                log_errors: bool = True,
                **kwargs) -> Any:
    """
    Safely execute a function with error handling.

    Args:
        func: Function to execute
        *args: Function arguments
        default_value: Default value on error
        log_errors: Whether to log errors
        **kwargs: Function keyword arguments

    Returns:
        Function result or default value on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger = get_logger()
            logger.error(
                f"Error in {func.__name__}: {str(e)}",
                exception=e,
                function=func.__name__,
                module=func.__module__
            )
        return default_value


# Context managers for error handling
@contextmanager
def error_context(operation: str,
                 component: Optional[str] = None,
                 strategies: Optional[List[ErrorRecoveryStrategy]] = None):
    """
    Context manager for error handling.

    Args:
        operation: Description of operation
        component: Component name
        strategies: Recovery strategies
    """
    context = ErrorContext(operation=operation, component=component)
    manager = ErrorManager()

    if strategies:
        for strategy in strategies:
            manager.add_strategy(strategy)

    try:
        yield context, manager
    except Exception as e:
        manager.handle_error(e, context)


# Predefined recovery strategies
def retry_on_io_error(max_retries: int = 3, delay_seconds: float = 1.0) -> RetryStrategy:
    """Create retry strategy for I/O errors."""
    return RetryStrategy(
        max_retries=max_retries,
        delay_seconds=delay_seconds,
        retry_on=[IOError, OSError, FileNotFoundError]
    )


def fallback_to_memory() -> FallbackStrategy:
    """Create fallback strategy for memory-based operations."""
    def memory_fallback(file_path: str, **kwargs):
        """Read file into memory instead of streaming."""
        with open(file_path, 'r') as f:
            return f.read()

    return FallbackStrategy(
        fallback_func=memory_fallback,
        fallback_args={}
    )


# Exception mapping
EXCEPTION_MAP = {
    'database': DatabaseError,
    'query': QueryError,
    'validation': ValidationError,
    'merge': MergeError,
    'export': ExportError,
    'fuzzy': FuzzyQueryError,
    'stats': StatsError,
    'utils': UtilsError,
    'counting': KmerCountingError,
    'encoding': EncodingError
}


def create_exception(error_type: str, message: str, **kwargs) -> RustKmerError:
    """
    Create a RustKmer exception of the specified type.

    Args:
        error_type: Type of exception
        message: Error message
        **kwargs: Additional exception parameters

    Returns:
        RustKmer exception instance
    """
    exc_class = EXCEPTION_MAP.get(error_type.lower(), RustKmerError)
    return exc_class(message, **kwargs)