"""
Utility functions for RustKmer Python bindings.

This module provides helper functions for database operations,
progress reporting, and system utilities.
"""

import time
import os
import psutil
from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager


def get_system_info() -> Dict[str, Any]:
    """Get system information for optimization.

    Returns:
        Dictionary containing system details:
        - cpu_count: Number of CPU cores
        - total_memory: Total system memory in MB
        - available_memory: Available memory in MB
        - platform: Operating system platform
    """
    try:
        import psutil
        return {
            "cpu_count": os.cpu_count() or 1,
            "total_memory": psutil.virtual_memory().total // (1024 * 1024),
            "available_memory": psutil.virtual_memory().available // (1024 * 1024),
            "platform": os.name,
        }
    except ImportError:
        return {
            "cpu_count": os.cpu_count() or 1,
            "total_memory": 0,
            "available_memory": 0,
            "platform": os.name,
        }


def get_resource_stats() -> Dict[str, Any]:
    """Get current resource usage statistics.

    Returns:
        Dictionary containing:
        - memory_mb: Current memory usage in MB
        - cpu_percent: CPU usage percentage
        - mapped_databases: Number of memory-mapped databases
    """
    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return {
            "memory_mb": memory_info.rss // (1024 * 1024),
            "cpu_percent": process.cpu_percent(),
            "mapped_databases": 0,  # TODO: Track from Rust side
        }
    except (ImportError, psutil.AccessDenied):
        return {
            "memory_mb": 0,
            "cpu_percent": 0,
            "mapped_databases": 0,
        }


def cleanup_resources() -> None:
    """Clean up allocated resources.

    This function forces garbage collection and releases
    memory-mapped database files.
    """
    import gc
    gc.collect()
    # TODO: Signal Rust side to cleanup


def optimize_thread_count(
    task_type: str = "general",
    memory_limit: Optional[int] = None,
    cpu_limit: Optional[int] = None,
) -> int:
    """Optimize thread count based on system and task.

    Args:
        task_type: Type of task ('general', 'io_bound', 'cpu_bound')
        memory_limit: Memory limit in MB
        cpu_limit: Maximum number of CPUs to use

    Returns:
        Optimal thread count
    """
    cpu_count = os.cpu_count() or 1

    if cpu_limit:
        cpu_count = min(cpu_count, cpu_limit)

    # Adjust based on task type
    if task_type == "io_bound":
        threads = cpu_count * 2  # More threads for I/O bound tasks
    elif task_type == "cpu_bound":
        threads = cpu_count  # One thread per CPU core
    else:  # general
        threads = max(1, cpu_count - 1)  # Leave one core free

    # Check memory constraints
    if memory_limit:
        # Estimate memory per thread (rough approximation)
        memory_per_thread = 100  # MB
        max_threads_by_memory = memory_limit // memory_per_thread
        threads = min(threads, max_threads_by_memory or 1)

    return max(1, min(threads, 16))  # Cap at 16 threads


def validate_kmer_size(k: int) -> None:
    """Validate k-mer size.

    Args:
        k: K-mer size to validate

    Raises:
        ValueError: If k is invalid
    """
    if not isinstance(k, int):
        raise ValueError(f"k-mer size must be an integer, got {type(k)}")
    if k < 1:
        raise ValueError(f"k-mer size must be at least 1, got {k}")
    if k > 31:
        raise ValueError(f"k-mer size must be at most 31, got {k}")


def validate_sequence(sequence: str) -> None:
    """Validate DNA/RNA sequence.

    Args:
        sequence: Sequence to validate

    Raises:
        ValueError: If sequence contains invalid characters
    """
    if not isinstance(sequence, str):
        raise ValueError(f"Sequence must be a string, got {type(sequence)}")

    # Convert to uppercase and check for valid nucleotides
    valid_bases = set("ATGCN")  # Include N for unknown bases
    invalid = set(sequence.upper()) - valid_bases
    if invalid:
        raise ValueError(f"Sequence contains invalid characters: {sorted(invalid)}")


def format_bytes(bytes_count: int) -> str:
    """Format bytes in human-readable format.

    Args:
        bytes_count: Number of bytes

    Returns:
        Human-readable string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} PB"


def format_count(count: int) -> str:
    """Format count with thousands separators.

    Args:
        count: Number to format

    Returns:
        Formatted string (e.g., "1,234,567")
    """
    return f"{count:,}"


@contextmanager
def progress_reporter(
    callback: Optional[Callable[[float, str], None]] = None,
    message: str = "Processing...",
):
    """Context manager for progress reporting.

    Args:
        callback: Progress callback function
        message: Progress message

    Yields:
        Progress update function
    """
    if callback is None:
        # No-op if no callback provided
        yield lambda _: None
        return

    start_time = time.time()

    def update(progress: float):
        elapsed = time.time() - start_time
        callback(progress, f"{message} ({progress:.1%}, {elapsed:.1f}s)")

    yield update

    # Report completion
    callback(1.0, f"{message} completed ({time.time() - start_time:.1f}s)")


def merge_databases(
    input_files: list[str],
    output_file: str,
    strategy: str = "sum",
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> None:
    """Merge multiple RKDB database files using rustkmer CLI.

    Args:
        input_files: List of input database files
        output_file: Output database file path
        strategy: Merge strategy ('sum', 'max', 'min') - currently only 'sum' is supported
        progress_callback: Optional progress callback

    Raises:
        ValueError: If strategy is invalid or not supported
        FileNotFoundError: If rustkmer CLI or input files don't exist
        RuntimeError: If CLI command fails
    """
    import shutil
    import subprocess

    # Validate strategy - only 'sum' is currently supported via CLI
    if strategy != "sum":
        raise ValueError(f"CLI-based merge only supports 'sum' strategy, got: {strategy}. "
                        "Use direct Rust binding for other strategies.")

    # Check rustkmer CLI is available
    rustkmer_cmd = shutil.which("rustkmer")
    if rustkmer_cmd is None:
        raise FileNotFoundError("rustkmer CLI not found in PATH. Please ensure rustkmer is installed.")

    # Check input files exist
    for file in input_files:
        if not os.path.exists(file):
            raise FileNotFoundError(f"Input file not found: {file}")

    # Build CLI command
    # Note: merge command may not be available in all versions
    cmd = [rustkmer_cmd, "merge", "-o", output_file] + input_files

    # Execute with progress reporting
    with progress_reporter(progress_callback, "Merging databases via CLI") as update:
        try:
            # Run the command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False  # Don't raise exception on non-zero exit
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                raise RuntimeError(f"Merge failed with exit code {result.returncode}: {error_msg}")

            update(1.0, "Merge completed successfully")

        except subprocess.SubprocessError as e:
            raise RuntimeError(f"Failed to execute merge command: {e}") from e


class PerformanceTimer:
    """Context manager for timing operations."""

    def __init__(self, name: str = "Operation", verbose: bool = False):
        self.name = name
        self.verbose = verbose
        self.start_time = None
        self.end_time = None
        self.elapsed = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        if self.verbose:
            print(f"Starting {self.name}...")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.elapsed = self.end_time - self.start_time
        if self.verbose:
            print(f"{self.name} completed in {self.elapsed:.3f} seconds")

    @property
    def seconds(self) -> float:
        """Get elapsed time in seconds."""
        return self.elapsed if self.elapsed is not None else 0.0

    @property
    def milliseconds(self) -> float:
        """Get elapsed time in milliseconds."""
        return self.seconds * 1000

    def __str__(self) -> str:
        return f"{self.name}: {self.elapsed:.3f}s" if self.elapsed else f"{self.name}: not completed"


# Re-export from Rust extension when available
# TODO: Uncomment when Rust implementations are ready
# Currently using Python implementations only
# try:
#     from ._rustkmer import (
#         get_resource_stats as _rust_get_resource_stats,
#         cleanup_resources as _rust_cleanup_resources,
#         merge_databases as _rust_merge_databases,
#         PerformanceTimer as _rust_PerformanceTimer,
#     )
#
#     # Override Python implementations with Rust versions
#     get_resource_stats = _rust_get_resource_stats
#     cleanup_resources = _rust_cleanup_resources
#     merge_databases = _rust_merge_databases
#     PerformanceTimer = _rust_PerformanceTimer
#
# except ImportError:
#     # Use Python implementations when Rust extension not available
#     pass

# Currently using Python implementations only