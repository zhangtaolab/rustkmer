"""
Database merge functionality for RKDB files.

This module provides classes and functions for merging multiple RKDB databases
into a single database, with support for compatibility checking and progress
reporting.
"""

import os
import subprocess
import tempfile
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
import time

# Import from Rust extension if available
try:
    from ._rustkmer import Database

    # Check if we have Rust merge implementation
    try:
        from ._rustkmer import merge_databases
        HAS_RUST_MERGE = True
    except ImportError:
        HAS_RUST_MERGE = False

except ImportError:
    HAS_RUST_MERGE = False
    Database = None


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
    database_paths: List[str],
    output_path: str,
    config: Optional[MergeConfig] = None
) -> MergeStats:
    """
    Merge multiple RKDB databases into a single database.

    Args:
        database_paths: List of input database file paths
        output_path: Path for the output merged database
        config: Merge configuration options

    Returns:
        MergeStats object with operation statistics

    Raises:
        CompatibilityError: If databases are not compatible
        MergeError: If merge operation fails
    """
    if config is None:
        config = MergeConfig()

    stats = MergeStats()
    stats.input_databases = database_paths.copy()
    stats.output_path = output_path
    stats.start_time = time.time()

    try:
        # Check compatibility first
        check_compatibility(database_paths)

        if HAS_RUST_MERGE and hasattr(Database, 'merge_files'):
            # Use Rust implementation if available
            _merge_rust(database_paths, output_path, config, stats)
        else:
            # Fallback to CLI implementation
            _merge_cli(database_paths, output_path, config, stats)

        # Verify output was created
        if not os.path.exists(output_path):
            raise MergeError("Merge completed but output file not found")

        stats.end_time = time.time()

        # Get output database statistics
        if HAS_RUST_MERGE:
            try:
                output_db = Database()
                output_db.load(output_path)
                output_stats = output_db.get_stats()
                stats.unique_output_kmers = output_stats.unique_kmers
                stats.total_input_kmers = sum(
                    _get_db_kmer_count(path) for path in database_paths
                )
                stats.duplicate_kmers = max(0, stats.total_input_kmers - stats.unique_output_kmers)
            except Exception:
                pass  # Stats collection is optional

        return stats

    except Exception as e:
        stats.end_time = time.time()
        if isinstance(e, (CompatibilityError, MergeError)):
            raise
        raise MergeError(f"Merge failed: {e}") from e


def _get_db_kmer_count(db_path: str) -> int:
    """Get total k-mer count from a database."""
    try:
        db = Database()
        db.load(db_path)
        stats = db.get_stats()
        return stats.total_kmers
    except Exception:
        return 0


def _merge_rust(
    database_paths: List[str],
    output_path: str,
    config: MergeConfig,
    stats: MergeStats
):
    """Merge using Rust implementation."""
    # This would use the Rust merge_databases function
    # For now, fall back to CLI
    _merge_cli(database_paths, output_path, config, stats)


def _merge_cli(
    database_paths: List[str],
    output_path: str,
    config: MergeConfig,
    stats: MergeStats
):
    """Merge using CLI implementation."""
    # Get rustkmer binary path
    script_dir = Path(__file__).parent.parent.parent
    binary_path = script_dir / "target" / "release" / "rustkmer"

    if not binary_path.exists():
        raise MergeError(
            "RustKmer binary not found. Please run 'cargo build --release' first."
        )

    # Build command
    cmd = [str(binary_path), "merge"]

    # Add input files
    cmd.extend(["-i"] + database_paths)

    # Add output file
    cmd.extend(["-o", output_path])

    # Add options
    if config.verbose:
        cmd.append("--verbose")
    if config.threads:
        cmd.extend(["--threads", str(config.threads)])
    # Note: CLI doesn't expose all config options

    if config.verbose:
        print(f"Running merge command: {' '.join(cmd)}")

    # Run merge
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        error_msg = f"Merge command failed with exit code {result.returncode}"
        if result.stderr:
            error_msg += f":\n{result.stderr}"
        raise MergeError(error_msg)

    stats.strategy_used = "cli"

    if config.verbose and result.stdout:
        print("Merge output:")
        print(result.stdout)


# Convenience functions
def merge_files(
    input_files: List[str],
    output_file: str,
    verbose: bool = False
) -> MergeStats:
    """
    Convenience function to merge database files.

    Args:
        input_files: List of input database files
        output_file: Output database file
        verbose: Enable verbose output

    Returns:
        MergeStats object
    """
    config = MergeConfig(verbose=verbose)
    return merge_databases(input_files, output_file, config)


def quick_merge(input_files: List[str], output_file: str) -> MergeStats:
    """
    Quick merge with default settings.

    Args:
        input_files: List of input database files
        output_file: Output database file

    Returns:
        MergeStats object
    """
    return merge_files(input_files, output_file, verbose=False)