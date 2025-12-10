"""
Database merge functionality for RKDB files.

This module provides classes and functions for merging multiple RKDB databases
into a single database, with support for compatibility checking and progress
reporting.
"""

import os
import tempfile
from typing import List, Optional, Dict, Any, Union, Callable
from pathlib import Path
import time
import logging

# Import from Rust extension and Python wrapper
try:
    from .database import Database
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False
    Database = None

# Setup module logger
logger = logging.getLogger(__name__)


class MergeConfig:
    """Configuration for database merge operations."""

    def __init__(
        self,
        max_memory_usage: Optional[int] = None,
        chunk_size: int = 1000000,
        temp_dir: Optional[str] = None,
        use_streaming: bool = False,
        threads: Optional[int] = None,
        verbose: bool = False
    ):
        """
        Initialize merge configuration.

        Args:
            max_memory_usage: Maximum memory usage in bytes (None for auto)
            chunk_size: Processing chunk size for streaming mode
            temp_dir: Temporary directory for operations
            use_streaming: Force streaming mode
            threads: Number of threads for parallel processing (None for auto)
            verbose: Enable detailed logging
        """
        self.max_memory_usage = max_memory_usage or (8 * 1024 * 1024 * 1024)  # 8GB default
        self.chunk_size = chunk_size
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.use_streaming = use_streaming
        self.threads = threads or os.cpu_count() or 1
        self.verbose = verbose


class MergeStats:
    """Statistics for merge operations."""

    def __init__(self):
        """Initialize merge statistics."""
        self.input_databases = []
        self.output_path = ""
        self.start_time = None
        self.end_time = None
        self.total_input_kmers = 0
        self.unique_output_kmers = 0
        self.duplicate_kmers = 0
        self.memory_peak = 0
        self.strategy_used = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        from datetime import datetime

        return {
            "input_databases": self.input_databases,
            "output_path": self.output_path,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None,
            "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "duration_seconds": (self.end_time - self.start_time) if self.start_time and self.end_time else None,
            "total_input_kmers": self.total_input_kmers,
            "unique_output_kmers": self.unique_output_kmers,
            "duplicate_kmers": self.duplicate_kmers,
            "memory_peak_mb": self.memory_peak / (1024 * 1024) if self.memory_peak > 0 else 0,
            "strategy_used": self.strategy_used
        }


class CompatibilityError(Exception):
    """Raised when databases are not compatible for merging."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class MergeError(Exception):
    """Raised when a merge operation fails."""
    pass


def check_compatibility(database_paths: List[str]) -> Dict[str, Any]:
    """
    Check if databases are compatible for merging.

    Args:
        database_paths: List of database file paths to check

    Returns:
        Dictionary with compatibility information

    Raises:
        CompatibilityError: If databases are not compatible
    """
    if not database_paths:
        raise CompatibilityError("No databases provided")

    if len(database_paths) < 2:
        raise CompatibilityError("At least 2 databases are required for merging")

    # Load first database as reference
    if not HAS_RUST_MERGE:
        # Fallback to CLI
        return _check_compatibility_cli(database_paths)

    ref_db = Database()
    try:
        ref_db.load(database_paths[0])
        ref_stats = ref_db.get_stats()
    except Exception as e:
        raise CompatibilityError(f"Failed to load reference database '{database_paths[0]}': {e}")

    # Check compatibility
    issues = []
    warnings = []

    ref_kmer_size = ref_stats.kmer_size
    ref_canonical = ref_stats.canonical

    for i, db_path in enumerate(database_paths[1:], 1):
        try:
            db = Database()
            db.load(db_path)
            stats = db.get_stats()

            # Check k-mer size
            if stats.kmer_size != ref_kmer_size:
                issues.append(
                    f"Database '{db_path}' has k-mer size {stats.kmer_size}, "
                    f"expected {ref_kmer_size}"
                )

            # Check canonical mode
            if stats.canonical != ref_canonical:
                issues.append(
                    f"Database '{db_path}' has canonical mode {stats.canonical}, "
                    f"expected {ref_canonical}"
                )

        except Exception as e:
            issues.append(f"Failed to load database '{db_path}': {e}")

    result = {
        "compatible": len(issues) == 0,
        "reference": {
            "path": database_paths[0],
            "kmer_size": ref_kmer_size,
            "canonical": ref_canonical
        },
        "issues": issues,
        "warnings": warnings
    }

    if issues:
        error_msg = "Databases are not compatible for merging:\n" + "\n".join(f"  • {issue}" for issue in issues)
        raise CompatibilityError(error_msg, result)

    return result


def _check_compatibility_cli(database_paths: List[str]) -> Dict[str, Any]:
    """Fallback compatibility check using CLI."""
    try:
        # Get rustkmer binary path
        script_dir = Path(__file__).parent.parent.parent
        binary_path = script_dir / "target" / "release" / "rustkmer"

        if not binary_path.exists():
            raise CompatibilityError(
                "RustKmer binary not found. Please run 'cargo build --release' first."
            )

        # Use stats command to check each database
        databases_info = []
        for db_path in database_paths:
            result = subprocess.run(
                [str(binary_path), "stats", "--json", db_path],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                # Try without --json flag
                result = subprocess.run(
                    [str(binary_path), "stats", db_path],
                    capture_output=True,
                    text=True
                )

            if result.returncode != 0:
                raise CompatibilityError(f"Failed to get stats for '{db_path}': {result.stderr}")

            # Parse stats output
            info = {
                "path": db_path,
                "kmer_size": 0,
                "canonical": False
            }

            # Try to parse JSON output first
            if result.stdout.strip().startswith('{'):
                import json
                try:
                    stats_data = json.loads(result.stdout)
                    info["kmer_size"] = stats_data.get("kmer_size", 0)
                    info["canonical"] = stats_data.get("canonical", False)
                except json.JSONDecodeError:
                    pass

            # Fallback to text parsing
            if info["kmer_size"] == 0:
                for line in result.stdout.split('\n'):
                    if "K-mer size:" in line:
                        try:
                            info["kmer_size"] = int(line.split(':')[-1].strip())
                        except ValueError:
                            pass
                    elif "Canonical:" in line:
                        info["canonical"] = "true" in line.lower()

            databases_info.append(info)

        # Check compatibility
        ref_info = databases_info[0]
        issues = []

        for info in databases_info[1:]:
            if info["kmer_size"] != ref_info["kmer_size"]:
                issues.append(
                    f"K-mer size mismatch: {info['kmer_size']} vs {ref_info['kmer_size']}"
                )
            if info["canonical"] != ref_info["canonical"]:
                issues.append(
                    f"Canonical mode mismatch: {info['canonical']} vs {ref_info['canonical']}"
                )

        return {
            "compatible": len(issues) == 0,
            "reference": ref_info,
            "issues": issues,
            "warnings": []
        }

    except Exception as e:
        if isinstance(e, CompatibilityError):
            raise
        raise CompatibilityError(f"Failed to check compatibility: {e}")


def merge_databases(
    database_paths: List[Union[str, Path]],
    output_path: Union[str, Path],
    strategy: str = "sum",
    progress_callback: Optional[Callable[[float], None]] = None,
    config: Optional[MergeConfig] = None
) -> MergeStats:
    """
    Merge multiple RKDB databases into a single database.

    Args:
        database_paths: List of input database file paths
        output_path: Path for the output merged database
        strategy: Merge strategy - 'sum', 'max', or 'min'
        progress_callback: Optional callback for progress updates (0-100)
        config: Merge configuration options (currently ignored, kept for compatibility)

    Returns:
        MergeStats object with operation statistics

    Raises:
        CompatibilityError: If databases are not compatible
        MergeError: If merge operation fails

    Example:
        >>> from rustkmer.merge import merge_databases
        >>> stats = merge_databases(
        ...     ["db1.rkdb", "db2.rkdb"],
        ...     "merged.rkdb",
        ...     strategy="sum"
        ... )
        >>> print(f"Merged {stats.total_input_kmers} k-mers")
    """
    if not HAS_DATABASE:
        raise MergeError("Database module not available. Please check installation.")

    if config is None:
        config = MergeConfig()

    # Convert paths to strings
    database_paths = [str(p) for p in database_paths]
    output_path = str(output_path)

    stats = MergeStats()
    stats.input_databases = database_paths.copy()
    stats.output_path = output_path
    stats.start_time = time.time()
    stats.strategy_used = strategy

    try:
        # Validate inputs
        if len(database_paths) < 2:
            raise ValueError("At least 2 databases are required for merging")

        # Check compatibility
        check_compatibility(database_paths)

        # Load databases
        logger.info(f"Loading {len(database_paths)} databases for merging")
        databases = []
        for path in database_paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Database file not found: {path}")
            db = Database(path)
            databases.append(db)

        # Perform merge
        logger.info(f"Starting merge with strategy: {strategy}")

        # Use first database as base and merge others
        base_db = databases[0]
        if len(databases) > 2:
            # Multiple database merge
            other_dbs = databases[1:]
            merged_db = base_db.merge_multiple(
                other_dbs,
                output_path,
                strategy,
                progress_callback
            )
        else:
            # Single database merge
            merged_db = base_db.merge(
                databases[1],
                output_path,
                strategy,
                progress_callback
            )

        # Collect statistics
        output_stats = merged_db.get_stats()
        stats.unique_output_kmers = output_stats.unique_kmers
        stats.total_input_kmers = sum(
            Database(db_path).get_stats().total_kmers
            for db_path in database_paths
        )
        stats.duplicate_kmers = max(0, stats.total_input_kmers - stats.unique_output_kmers)

        stats.end_time = time.time()
        logger.info(f"Merge complete: {output_path}")

        return stats

    except Exception as e:
        stats.end_time = time.time()
        if isinstance(e, (CompatibilityError, MergeError, ValueError, FileNotFoundError)):
            raise
        raise MergeError(f"Merge failed: {e}") from e


# Convenience functions
def merge_files(
    input_files: List[Union[str, Path]],
    output_file: Union[str, Path],
    strategy: str = "sum",
    progress_callback: Optional[Callable[[float], None]] = None,
    verbose: bool = False
) -> MergeStats:
    """
    Convenience function to merge database files.

    Args:
        input_files: List of input database files
        output_file: Output database file
        strategy: Merge strategy - 'sum', 'max', or 'min'
        progress_callback: Optional callback for progress updates
        verbose: Enable verbose output

    Returns:
        MergeStats object
    """
    if verbose:
        logging.basicConfig(level=logging.INFO)

    return merge_databases(input_files, output_file, strategy, progress_callback)


def quick_merge(input_files: List[Union[str, Path]], output_file: Union[str, Path]) -> MergeStats:
    """
    Quick merge with default settings.

    Args:
        input_files: List of input database files
        output_file: Output database file

    Returns:
        MergeStats object
    """
    return merge_files(input_files, output_file, strategy="sum", verbose=False)


# Progress tracking utilities
class ProgressTracker:
    """Simple progress tracker for merge operations."""

    def __init__(self, description: str = "Merging databases"):
        """Initialize progress tracker.

        Args:
            description: Description of the operation
        """
        self.description = description
        self.start_time = None

    def __call__(self, progress: float) -> None:
        """Progress callback function.

        Args:
            progress: Progress percentage (0-100)
        """
        if self.start_time is None:
            self.start_time = time.time()
            logger.info(f"{self.description}: Started")

        if progress >= 100.0:
            duration = time.time() - self.start_time
            logger.info(f"{self.description}: Complete in {duration:.1f}s")
        elif progress % 10 == 0:  # Log every 10%
            elapsed = time.time() - self.start_time
            if progress > 0:
                eta = (elapsed / progress) * (100.0 - progress)
                logger.info(f"{self.description}: {progress:.0f}% (ETA: {eta:.0f}s)")