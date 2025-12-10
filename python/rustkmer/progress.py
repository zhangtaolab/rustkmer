"""
Progress reporting mechanism for RustKmer operations.

This module provides progress callback functionality for long-running operations
like k-mer counting, database queries, and file processing.
"""

import time
import threading
from typing import Callable, Optional, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum

from .exceptions import ProgressCallbackError


class ProgressStage(Enum):
    """Enumeration of operation stages."""
    INITIALIZING = "initializing"
    LOADING = "loading"
    PROCESSING = "processing"
    COUNTING = "counting"
    QUERYING = "querying"
    MERGING = "merging"
    EXPORTING = "exporting"
    FINALIZING = "finalizing"
    COMPLETED = "completed"


@dataclass
class ProgressInfo:
    """Progress information for callbacks."""
    stage: ProgressStage
    current: int = 0
    total: int = 0
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    elapsed: float = 0.0
    eta: Optional[float] = None
    rate: Optional[float] = None  # items per second
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total <= 0:
            return 0.0
        return (self.current / self.total) * 100.0

    @property
    def is_complete(self) -> bool:
        """Check if operation is complete."""
        return self.stage == ProgressStage.COMPLETED or (
            self.total > 0 and self.current >= self.total
        )


class ProgressReporter:
    """
    Thread-safe progress reporter for long-running operations.
    """

    def __init__(self, total: int = 0, stage: ProgressStage = ProgressStage.INITIALIZING):
        self._total = total
        self._current = 0
        self._stage = stage
        self._message = ""
        self._start_time = time.time()
        self._last_update_time = self._start_time
        self._last_current = 0
        self._callbacks: list[Callable[[ProgressInfo], None]] = []
        self._lock = threading.RLock()
        self._completed = False

    def set_total(self, total: int) -> None:
        """Set the total number of items to process."""
        with self._lock:
            self._total = total

    def set_stage(self, stage: ProgressStage, message: str = "") -> None:
        """Set the current operation stage."""
        with self._lock:
            self._stage = stage
            self._message = message
            self._notify_callbacks()

    def update(self, increment: int = 1, message: str = "") -> None:
        """
        Update progress by increment.

        Args:
            increment: Number of items processed since last update
            message: Optional status message
        """
        with self._lock:
            if self._completed:
                return

            self._current += increment
            if message:
                self._message = message
            self._notify_callbacks()

    def set_current(self, current: int, message: str = "") -> None:
        """
        Set current progress directly.

        Args:
            current: Current number of items processed
            message: Optional status message
        """
        with self._lock:
            if self._completed:
                return

            self._current = current
            if message:
                self._message = message
            self._notify_callbacks()

    def add_callback(self, callback: Callable[[ProgressInfo], None]) -> None:
        """
        Add a progress callback function.

        Args:
            callback: Function to call with progress updates
        """
        with self._lock:
            self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[ProgressInfo], None]) -> None:
        """
        Remove a progress callback function.

        Args:
            callback: Function to remove from callbacks
        """
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def complete(self, message: str = "Operation completed") -> None:
        """Mark operation as complete."""
        with self._lock:
            self._current = self._total
            self._stage = ProgressStage.COMPLETED
            self._message = message
            self._completed = True
            self._notify_callbacks()

    def _notify_callbacks(self) -> None:
        """Notify all registered callbacks with current progress."""
        current_time = time.time()
        elapsed = current_time - self._start_time

        # Calculate rate and ETA
        rate = None
        eta = None
        if self._current > self._last_current and elapsed > 0:
            time_diff = current_time - self._last_update_time
            if time_diff > 0:
                current_rate = (self._current - self._last_current) / time_diff
                rate = current_rate

                # Calculate ETA based on remaining items
                if self._total > 0 and rate > 0:
                    remaining = self._total - self._current
                    eta = remaining / rate

        # Create progress info
        progress_info = ProgressInfo(
            stage=self._stage,
            current=self._current,
            total=self._total,
            message=self._message,
            timestamp=current_time,
            elapsed=elapsed,
            eta=eta,
            rate=rate
        )

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(progress_info)
            except Exception as e:
                # Don't let callback errors break progress reporting
                raise ProgressCallbackError(
                    f"Progress callback failed: {e}",
                    callback_name=getattr(callback, '__name__', 'unknown')
                )

        # Update last update tracking
        self._last_update_time = current_time
        self._last_current = self._current

    def get_progress_info(self) -> ProgressInfo:
        """Get current progress information."""
        with self._lock:
            return ProgressInfo(
                stage=self._stage,
                current=self._current,
                total=self._total,
                message=self._message,
                timestamp=time.time(),
                elapsed=time.time() - self._start_time,
                metadata={}
            )


# Built-in progress callbacks
def console_progress_callback(info: ProgressInfo) -> None:
    """Simple console progress callback."""
    if info.total > 0:
        percentage = info.percentage
        bar_length = 50
        filled_length = int(bar_length * percentage / 100)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)

        print(f'\r{info.stage.value.title():12} |{bar}| {percentage:5.1f}% '
              f'({info.current:,}/{info.total:,}) {info.message}', end='', flush=True)

        if info.is_complete:
            print()  # New line when complete
    else:
        print(f'\r{info.stage.value.title()}: {info.message}', end='', flush=True)


def logging_progress_callback(info: ProgressInfo) -> None:
    """Logging progress callback."""
    import logging

    logger = logging.getLogger('rustkmer.progress')

    if info.total > 0:
        logger.info(
            f"{info.stage.value}: {info.percentage:.1f}% "
            f"({info.current:,}/{info.total:,}) - {info.message}"
        )
    else:
        logger.info(f"{info.stage.value}: {info.message}")


class ProgressBar:
    """Text-based progress bar for terminal output."""

    def __init__(self, total: int, width: int = 50, show_percentage: bool = True,
                 show_eta: bool = True, show_rate: bool = True):
        self.total = total
        self.width = width
        self.show_percentage = show_percentage
        self.show_eta = show_eta
        self.show_rate = show_rate
        self.start_time = time.time()
        self.last_update = 0

    def update(self, current: int, message: str = "") -> None:
        """Update progress bar display."""
        if current < self.last_update:
            return  # Don't go backwards

        percentage = (current / self.total) * 100 if self.total > 0 else 0
        filled_length = int(self.width * percentage / 100)
        bar = '█' * filled_length + '-' * (self.width - filled_length)

        parts = [f'\r|{bar}|']

        if self.show_percentage:
            parts.append(f' {percentage:5.1f}%')

        parts.append(f' ({current:,}/{self.total:,})')

        if message:
            parts.append(f' {message}')

        # Calculate ETA and rate
        elapsed = time.time() - self.start_time
        if elapsed > 0 and current > 0:
            rate = current / elapsed
            if self.show_rate:
                parts.append(f' [{rate:,.0f} items/s]')

            if self.show_eta and current < self.total:
                remaining = self.total - current
                eta = remaining / rate if rate > 0 else float('inf')
                if eta < float('inf'):
                    parts.append(f' ETA: {eta:.0f}s')

        print(''.join(parts), end='', flush=True)
        self.last_update = current

    def finish(self, message: str = "Complete!") -> None:
        """Finish progress bar with final message."""
        self.update(self.total, message)
        print()  # New line


# Context manager for progress reporting
class ProgressContext:
    """Context manager for progress reporting."""

    def __init__(self, total: int = 0, stage: ProgressStage = ProgressStage.PROCESSING,
                 callbacks: Optional[list[Callable[[ProgressInfo], None]]] = None):
        self.reporter = ProgressReporter(total, stage)
        if callbacks:
            for callback in callbacks:
                self.reporter.add_callback(callback)

    def __enter__(self) -> ProgressReporter:
        return self.reporter

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.reporter.complete()
        else:
            self.reporter.set_stage(ProgressStage.FINALIZING, "Operation failed")


# Utility functions
def create_simple_callback(prefix: str = "") -> Callable[[ProgressInfo], None]:
    """Create a simple console callback with custom prefix."""
    def callback(info: ProgressInfo):
        if info.total > 0:
            print(f'\r{prefix} {info.percentage:5.1f}% ({info.current:,}/{info.total:,}) '
                  f'- {info.message}', end='', flush=True)
        else:
            print(f'\r{prefix} {info.message}', end='', flush=True)
    return callback


def create_tqdm_callback(total: int = None, desc: str = "Processing"):
    """Create a tqdm-compatible callback if tqdm is available."""
    try:
        from tqdm import tqdm

        pbar = tqdm(total=total, desc=desc)

        def callback(info: ProgressInfo):
            if info.total > 0 and info.total != pbar.total:
                pbar.total = info.total
            pbar.update(info.current - pbar.n)
            if info.message:
                pbar.set_description(f"{desc}: {info.message}")
            if info.is_complete:
                pbar.close()

        return callback
    except ImportError:
        # Fallback to simple console callback
        return console_progress_callback


# Throttled callback wrapper
class ThrottledCallback:
    """Wrapper to throttle callback updates to avoid overwhelming the output."""

    def __init__(self, callback: Callable[[ProgressInfo], None], min_interval: float = 0.1):
        self.callback = callback
        self.min_interval = min_interval
        self.last_call = 0

    def __call__(self, info: ProgressInfo):
        current_time = time.time()
        if current_time - self.last_call >= self.min_interval or info.is_complete:
            self.callback(info)
            self.last_call = current_time