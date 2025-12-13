"""Utility functions for rustkmer Python bindings.

This module provides helper functions for CLI interaction, data parsing,
and common operations used throughout the rustkmer package.
"""

import json
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import Dict, List, Optional, Union

from .exceptions import (
    InvalidKmerError,
    KmerLengthError,
    SubprocessError,
    ConfigurationError,
)

# Cache for the rustkmer executable path
_rustkmer_path_cache: Optional[str] = None
_path_cache_lock = threading.Lock()


def validate_kmer(kmer: str, kmer_size: Optional[int] = None, strict: bool = True) -> Optional[str]:
    """Validate a k-mer sequence.

    Args:
        kmer: The k-mer sequence to validate
        kmer_size: Expected k-mer size (optional)
        strict: If True, raise exceptions for invalid k-mers. If False, return None for invalid k-mers.

    Returns:
        The validated k-mer (uppercase) if valid, None if invalid and strict=False

    Raises:
        InvalidKmerError: If k-mer contains invalid characters and strict=True
        KmerLengthError: If k-mer size doesn't match expected size and strict=True
    """
    # Handle None or non-string inputs
    if kmer is None:
        if strict:
            raise InvalidKmerError("None", "k-mer cannot be None")
        else:
            return None

    # Handle non-string types
    if not isinstance(kmer, str):
        if strict:
            raise InvalidKmerError(str(kmer), f"k-mer must be a string, got {type(kmer).__name__}")
        else:
            return None

    # Convert to uppercase
    kmer = kmer.upper()

    # Check for valid DNA characters
    if not re.match(r'^[ATCG]+$', kmer):
        if strict:
            raise InvalidKmerError(kmer, "contains invalid characters (only A, T, C, G allowed)")
        else:
            return None

    # Check length if specified
    if kmer_size is not None and len(kmer) != kmer_size:
        if strict:
            raise KmerLengthError(kmer, kmer_size, len(kmer))
        else:
            return None

    return kmer


def run_rustkmer_command(args: List[str], timeout: Optional[float] = None) -> str:
    """Execute a rustkmer CLI command and return stdout.

    Args:
        args: Command line arguments for rustkmer
        timeout: Optional timeout in seconds

    Returns:
        The command's stdout output

    Raises:
        SubprocessError: If the command fails
        ConfigurationError: If rustkmer is not found
    """
    # Find rustkmer executable
    rustkmer_cmd = find_rustkmer_executable()

    # Build full command
    full_cmd = [rustkmer_cmd] + args
    cmd_str = ' '.join(full_cmd)

    try:
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        # Parse common error patterns to provide helpful messages
        stderr = e.stderr.strip().lower() if e.stderr else ""

        if "no such file" in stderr or "not found" in stderr:
            if len(args) >= 2 and args[0] in ['query', 'dump', 'stats']:
                db_path = args[1]
                raise SubprocessError(
                    cmd_str,
                    e.returncode,
                    "Database file not found: '" + db_path + "'. "
                    "Please check the file path and ensure it exists."
                )

        if "permission denied" in stderr:
            raise SubprocessError(
                cmd_str,
                e.returncode,
                "Permission denied. Check file/directory permissions."
            )

        if "invalid" in stderr and "database" in stderr:
            raise SubprocessError(
                cmd_str,
                e.returncode,
                "Invalid database format. The file may be corrupted or not a valid .rkdb file."
            )

        # Generic error with stderr output
        error_msg = "Command failed with exit code " + str(e.returncode)
        if e.stderr:
            error_msg += ": " + e.stderr.strip()
        else:
            error_msg += ". No error output available."

        raise SubprocessError(cmd_str, e.returncode, error_msg)

    except subprocess.TimeoutExpired as e:
        raise SubprocessError(
            cmd_str,
            -1,
            "Command timed out after " + str(timeout) + " seconds. "
            "Consider increasing timeout or using a smaller limit parameter."
        )
    except FileNotFoundError:
        raise ConfigurationError(
            "rustkmer executable not found at: " + rustkmer_cmd + ". "
            "Please ensure rustkmer is properly installed."
        )


def find_rustkmer_executable() -> str:
    """Find the rustkmer executable (with caching).

    Searches in the following order:
    1. Cache (previous successful lookup)
    2. RUSTKMER_PATH environment variable
    3. Package bin directory
    4. System PATH

    Returns:
        Path to the rustkmer executable

    Raises:
        ConfigurationError: If rustkmer cannot be found
    """
    global _rustkmer_path_cache

    # Check cache first
    with _path_cache_lock:
        if _rustkmer_path_cache is not None:
            # Verify cached path still exists
            if Path(_rustkmer_path_cache).exists():
                return _rustkmer_path_cache
            else:
                # Clear invalid cache
                _rustkmer_path_cache = None

    import os

    # Check environment variable
    if 'RUSTKMER_PATH' in os.environ:
        path = Path(os.environ['RUSTKMER_PATH'])
        if path.exists() and path.is_file():
            # Verify it's executable
            if os.access(path, os.X_OK) or sys.platform == 'win32':
                return str(path)
            else:
                raise ConfigurationError(
                    "rustkmer found at " + str(path) + " but is not executable. "
                    "Please check file permissions: chmod +x " + str(path)
                )
        else:
            raise ConfigurationError(
                "RUSTKMER_PATH is set to '" + str(path) + "' but file does not exist. "
                "Please check the path or unset RUSTKMER_PATH to use system search."
            )

    # Check package bin directory
    package_dir = Path(__file__).parent
    bin_dir = package_dir / 'bin'

    # Platform-specific binary name
    if sys.platform == 'win32':
        binary_name = 'rustkmer-windows.exe'
    elif sys.platform == 'darwin':
        binary_name = 'rustkmer-macos'
    else:
        binary_name = 'rustkmer-linux'

    binary_path = bin_dir / binary_name
    if binary_path.exists():
        return str(binary_path)

    # Check system PATH
    import shutil
    rustkmer_path = shutil.which('rustkmer')
    if rustkmer_path:
        # Cache the result
        with _path_cache_lock:
            _rustkmer_path_cache = rustkmer_path
        return rustkmer_path

    # Build helpful error message
    error_msg = [
        "rustkmer executable not found in any of the searched locations:",
        "",
        "1. RUSTKMER_PATH environment variable (not set)",
        "2. Package bin directory: " + str(bin_dir) + " (not found)",
        "3. System PATH (rustkmer command not found)",
        "",
        "To fix this issue:",
        "• Install rustkmer: https://github.com/rustkmer/rustkmer",
        "• Set RUSTKMER_PATH to the full path of your rustkmer executable",
        "• Add rustkmer to your system PATH",
        "",
        "Current platform: " + sys.platform
    ]

    # Add platform-specific installation hints
    if sys.platform == 'darwin':
        error_msg.extend([
            "macOS installation:",
            "  brew install rustkmer  # if available",
            "  or download from GitHub releases"
        ])
    elif sys.platform == 'linux':
        error_msg.extend([
            "Linux installation:",
            "  cargo install rustkmer  # if Rust is installed",
            "  or download .deb/.rpm package from releases"
        ])
    elif sys.platform == 'win32':
        error_msg.extend([
            "Windows installation:",
            "  Download rustkmer-windows.exe from GitHub releases",
            "  or install via cargo install rustkmer"
        ])

    raise ConfigurationError('\n'.join(error_msg))


def parse_query_output(output: str, format_hint: str = 'auto') -> Dict[str, Union[str, int]]:
    """Parse output from rustkmer query command.

    Args:
        output: The raw output string from rustkmer query
        format_hint: Expected format ('auto', 'json', 'text')

    Returns:
        Dictionary with parsed data
    """
    # Try JSON first
    if format_hint in ('auto', 'json') and output.strip().startswith('{'):
        try:
            data = json.loads(output)
            return {
                'kmer': data.get('kmer', ''),
                'count': int(data.get('count', 0)),
                'canonical': data.get('canonical', '')
            }
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

    # Parse text format
    lines = output.strip().split('\n')
    if len(lines) == 1 and '\t' in lines[0]:
        # Tab-separated format
        parts = lines[0].split('\t')
        return {
            'kmer': parts[0] if len(parts) > 0 else '',
            'count': int(parts[1]) if len(parts) > 1 else 0,
            'canonical': parts[2] if len(parts) > 2 else parts[0]
        }

    # Fallback: try to extract count from text
    count_match = re.search(r'count[:\s]+(\d+)', output, re.IGNORECASE)
    kmer_match = re.search(r'[ATCG]+', output)

    return {
        'kmer': kmer_match.group(0) if kmer_match else '',
        'count': int(count_match.group(1)) if count_match else 0,
        'canonical': kmer_match.group(0) if kmer_match else ''
    }


def parse_stats_output(output: str) -> Dict[str, Union[str, int]]:
    """Parse output from rustkmer stats command.

    Args:
        output: The raw output string from rustkmer stats

    Returns:
        Dictionary with parsed statistics
    """
    # Try JSON first
    if output.strip().startswith('{'):
        try:
            data = json.loads(output)
            return {
                'kmer_size': int(data.get('kmer_size', 0)),
                'unique_kmers': int(data.get('unique_kmers', 0)),
                'total_counts': int(data.get('total_counts', 0)),
                'max_count': int(data.get('max_count', 0)),
                'file_size': int(data.get('file_size', 0)),
                'format_version': data.get('format_version', 'unknown')
            }
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

    # Parse text format
    stats = {}
    for line in output.strip().split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().lower().replace(' ', '_').replace('-', '_')
            value = value.strip()

            # Try to parse as integer
            try:
                stats[key] = int(value)
            except ValueError:
                # Try to parse float (for mean, median)
                try:
                    stats[key] = float(value)
                except ValueError:
                    stats[key] = value

    # Map field names to expected output names
    field_mapping = {
        'k_mer_size': 'kmer_size',
        'unique_k_mers': 'unique_kmers',
        'total_k_mers': 'total_counts'  # CLI uses total_k_mers, API expects total_counts
    }

    # Apply field mapping
    mapped_stats = {}
    for key, value in stats.items():
        mapped_key = field_mapping.get(key, key)
        mapped_stats[mapped_key] = value

    # Set defaults for missing fields
    defaults = {
        'kmer_size': 0,
        'unique_kmers': 0,
        'total_counts': 0,
        'min_count': 0,
        'max_count': 0,
        'file_size': 0,
        'format_version': 'unknown'
    }

    for key, default in defaults.items():
        if key not in mapped_stats:
            mapped_stats[key] = default

    return mapped_stats


def canonical_kmer(kmer: str) -> str:
    """Return the canonical representation of a k-mer.

    The canonical k-mer is the lexicographically smaller of the k-mer
    and its reverse complement.

    Args:
        kmer: The k-mer sequence

    Returns:
        The canonical k-mer
    """
    complement = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C'}

    # Get reverse complement
    rc = ''.join(complement[base] for base in reversed(kmer))

    # Return lexicographically smaller
    return min(kmer, rc)