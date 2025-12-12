"""
Logging configuration for RustKmer Python API.

Provides comprehensive logging with structured output, performance metrics,
and configurable log levels.
"""

import logging
import logging.handlers
import sys
import os
import time
import json
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Union
from contextlib import contextmanager
from functools import wraps

# Import RustKmer exceptions
from .exceptions import RustKmerError


class RustKmerFormatter(logging.Formatter):
    """Custom formatter for RustKmer log messages."""

    def __init__(self, include_performance: bool = True):
        """
        Initialize formatter.

        Args:
            include_performance: Whether to include performance metrics
        """
        super().__init__()
        self.include_performance = include_performance
        self.start_times = {}
        self._lock = threading.Lock()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with enhanced information."""
        # Basic format
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created))
        level = record.levelname.ljust(8)
        module = record.name.split('.')[-1] if '.' in record.name else record.name
        location = f"{module}:{record.lineno}" if hasattr(record, 'lineno') else module

        # Build message
        parts = [
            f"[{timestamp}]",
            f"{level}",
            f"{location}",
            record.getMessage()
        ]

        # Add exception information if present
        if record.exc_info:
            parts.append(f"\nException: {self.formatException(record.exc_info)}")

        # Add performance metrics if enabled and available
        if self.include_performance and hasattr(record, 'performance'):
            perf = record.performance
            parts.append(f"\nPerformance: {perf}")

        return " ".join(parts)


class StructuredLogger:
    """Structured logger for RustKmer with JSON output support."""

    def __init__(self, name: str, output_file: Optional[Union[str, Path]] = None):
        """
        Initialize structured logger.

        Args:
            name: Logger name
            output_file: Optional JSON log file
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(RustKmerFormatter())
        self.logger.addHandler(console_handler)

        # JSON file handler if specified
        if output_file:
            json_handler = logging.FileHandler(output_file)
            json_handler.setFormatter(JsonFormatter())
            self.logger.addHandler(json_handler)

        # Thread safety
        self._lock = threading.Lock()

    def info(self, message: str, **kwargs) -> None:
        """Log info message with optional metadata."""
        with self._lock:
            extra = {'performance': kwargs} if kwargs else {}
            self.logger.info(message, extra=extra)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with optional metadata."""
        with self._lock:
            extra = {'performance': kwargs} if kwargs else {}
            self.logger.warning(message, extra=extra)

    def error(self, message: str, exception: Optional[Exception] = None, **kwargs) -> None:
        """Log error message with optional exception."""
        with self._lock:
            extra = {'performance': kwargs} if kwargs else {}
            if exception:
                self.logger.error(message, exc_info=(type(exception), exception, exception.__traceback__), extra=extra)
            else:
                self.logger.error(message, extra=extra)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with optional metadata."""
        with self._lock:
            extra = {'performance': kwargs} if kwargs else {}
            self.logger.debug(message, extra=extra)

    def performance(self, operation: str, duration: float, **kwargs) -> None:
        """Log performance metrics."""
        with self._lock:
            metrics = {
                'operation': operation,
                'duration_seconds': duration,
                **kwargs
            }
            self.logger.info(f"Performance: {operation}", extra={'performance': metrics})


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S.%fZ', time.gmtime(record.created)),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add exception information
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }

        # Add performance metrics
        if hasattr(record, 'performance') and record.performance:
            log_data['performance'] = record.performance

        return json.dumps(log_data)


class PerformanceLogger:
    """Logger for tracking performance metrics."""

    def __init__(self, logger: Optional[StructuredLogger] = None):
        """
        Initialize performance logger.

        Args:
            logger: Optional structured logger to use
        """
        self.logger = logger or StructuredLogger('rustkmer.performance')
        self.metrics: Dict[str, list] = {}
        self._lock = threading.Lock()

    @contextmanager
    def time_operation(self, operation_name: str, **metadata):
        """
        Context manager for timing operations.

        Args:
            operation_name: Name of operation being timed
            **metadata: Additional metadata to log
        """
        start_time = time.time()
        operation_id = f"{operation_name}_{start_time}"

        try:
            yield operation_id
        finally:
            duration = time.time() - start_time

            # Record metric
            with self._lock:
                if operation_name not in self.metrics:
                    self.metrics[operation_name] = []
                self.metrics[operation_name].append(duration)

            # Log performance
            self.logger.performance(
                operation=operation_name,
                duration=duration,
                operation_id=operation_id,
                **metadata
            )

    def log_metric(self, operation: str, value: float, unit: str = 'seconds', **metadata) -> None:
        """
        Log a performance metric.

        Args:
            operation: Operation name
            value: Metric value
            unit: Unit of measurement
            **metadata: Additional metadata
        """
        with self._lock:
            if operation not in self.metrics:
                self.metrics[operation] = []
            self.metrics[operation].append(value)

        self.logger.performance(
            operation=operation,
            duration=value,
            unit=unit,
            **metadata
        )

    def get_statistics(self, operation: Optional[str] = None) -> Dict[str, Dict[str, float]]:
        """
        Get performance statistics.

        Args:
            operation: Specific operation to get stats for (None for all)

        Returns:
            Dictionary of statistics
        """
        with self._lock:
            if operation:
                if operation not in self.metrics:
                    return {}
                values = self.metrics[operation]
                return {operation: self._calculate_stats(values)}
            else:
                return {op: self._calculate_stats(vals)
                       for op, vals in self.metrics.items()}

    def _calculate_stats(self, values: list) -> Dict[str, float]:
        """Calculate statistics for a list of values."""
        if not values:
            return {}

        import statistics
        return {
            'count': len(values),
            'total': sum(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'min': min(values),
            'max': max(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0
        }

    def reset(self) -> None:
        """Reset all recorded metrics."""
        with self._lock:
            self.metrics.clear()


class ErrorHandler:
    """Centralized error handling with logging."""

    def __init__(self, logger: Optional[StructuredLogger] = None):
        """
        Initialize error handler.

        Args:
            logger: Optional structured logger to use
        """
        self.logger = logger or StructuredLogger('rustkmer.errors')
        self.error_counts: Dict[str, int] = {}
        self._lock = threading.Lock()

    def handle_error(self,
                    error: Exception,
                    context: Optional[Dict[str, Any]] = None,
                    reraise: bool = True) -> None:
        """
        Handle an error with logging.

        Args:
            error: Exception to handle
            context: Additional context information
            reraise: Whether to reraise the exception
        """
        error_type = type(error).__name__

        # Count errors
        with self._lock:
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

        # Log error
        context_str = f" | Context: {context}" if context else ""
        self.logger.error(
            f"{error_type}: {str(error)}{context_str}",
            exception=error,
            error_type=error_type,
            error_count=self.error_counts[error_type],
            **context or {}
        )

        if reraise:
            raise error

    def log_warning(self, warning: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log a warning message."""
        context_str = f" | Context: {context}" if context else ""
        self.logger.warning(f"{warning}{context_str}", **context or {})

    def get_error_summary(self) -> Dict[str, Dict[str, int]]:
        """Get summary of errors encountered."""
        with self._lock:
            return dict(self.error_counts)


def log_exceptions(logger: Optional[StructuredLogger] = None):
    """
    Decorator to automatically log exceptions.

    Args:
        logger: Optional structured logger to use

    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler = ErrorHandler(logger)
                error_handler.handle_error(
                    e,
                    context={
                        'function': func.__name__,
                        'module': func.__module__,
                        'args_count': len(args),
                        'kwargs_keys': list(kwargs.keys())
                    },
                    reraise=True
                )
        return wrapper
    return decorator


def configure_logging(level: str = 'INFO',
                    log_file: Optional[Union[str, Path]] = None,
                    json_file: Optional[Union[str, Path]] = None,
                    max_bytes: int = 10 * 1024 * 1024,  # 10MB
                    backup_count: int = 5) -> StructuredLogger:
    """
    Configure RustKmer logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional text log file
        json_file: Optional JSON log file
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup log files to keep

    Returns:
        Configured structured logger
    """
    # Create logger
    logger = StructuredLogger('rustkmer')

    # Set level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.logger.setLevel(numeric_level)

    # Clear existing handlers
    logger.logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(RustKmerFormatter())
    logger.logger.addHandler(console_handler)

    # File handler with rotation
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(RustKmerFormatter())
        logger.logger.addHandler(file_handler)

    # JSON file handler with rotation
    if json_file:
        json_handler = logging.handlers.RotatingFileHandler(
            json_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        json_handler.setFormatter(JsonFormatter())
        logger.logger.addHandler(json_handler)

    return logger


# Global instances
_default_logger = None
_performance_logger = None
_error_handler = None


def get_logger() -> StructuredLogger:
    """Get default RustKmer logger."""
    global _default_logger
    if _default_logger is None:
        _default_logger = StructuredLogger('rustkmer')
    return _default_logger


def get_performance_logger() -> PerformanceLogger:
    """Get default performance logger."""
    global _performance_logger
    if _performance_logger is None:
        _performance_logger = PerformanceLogger(get_logger())
    return _performance_logger


def get_error_handler() -> ErrorHandler:
    """Get default error handler."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler(get_logger())
    return _error_handler


# Convenience functions
def log_info(message: str, **kwargs) -> None:
    """Log info message using default logger."""
    get_logger().info(message, **kwargs)


def log_warning(message: str, **kwargs) -> None:
    """Log warning message using default logger."""
    get_logger().warning(message, **kwargs)


def log_error(message: str, exception: Optional[Exception] = None, **kwargs) -> None:
    """Log error message using default logger."""
    get_logger().error(message, exception=exception, **kwargs)


def log_debug(message: str, **kwargs) -> None:
    """Log debug message using default logger."""
    get_logger().debug(message, **kwargs)


def handle_error(error: Exception, context: Optional[Dict[str, Any]] = None, reraise: bool = True) -> None:
    """Handle error using default error handler."""
    get_error_handler().handle_error(error, context=context, reraise=reraise)


def time_operation(operation_name: str, **metadata):
    """Get performance timing context manager."""
    return get_performance_logger().time_operation(operation_name, **metadata)