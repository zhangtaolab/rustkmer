"""
File format validation utilities for RustKmer.

This module provides validation functions for various file formats
used by RustKmer, including RKDB databases, FASTA, FASTQ, and export formats.
"""

import os
import struct
from typing import Optional, Tuple, Dict, Any, BinaryIO
from pathlib import Path

from .exceptions import (
    DatabaseCorruptionError,
    FileNotFoundError,
    ValidationError,
    EncodingError,
    CompressionError
)


# RKDB file format constants
RKDB_MAGIC = b"RKDB"
RKDB_MIN_SIZE = 42  # Minimum size for a valid RKDB header
RKDB_CURRENT_VERSION = 2


def validate_rkdb_file(file_path: str) -> Dict[str, Any]:
    """
    Validate RKDB database file format and structure.

    Args:
        file_path: Path to the RKDB file

    Returns:
        Dictionary containing validation results and metadata

    Raises:
        FileNotFoundError: If file doesn't exist
        DatabaseCorruptionError: If file format is invalid
        ValidationError: If validation fails
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Database file not found: {file_path}")

    if not os.path.isfile(file_path):
        raise ValidationError(f"Path is not a file: {file_path}")

    file_size = os.path.getsize(file_path)
    if file_size < RKDB_MIN_SIZE:
        raise DatabaseCorruptionError(
            f"File too small for RKDB format: {file_size} bytes (minimum: {RKDB_MIN_SIZE})",
            database_path=file_path
        )

    try:
        with open(file_path, 'rb') as f:
            # Read and validate magic bytes
            magic = f.read(4)
            if magic != RKDB_MAGIC:
                raise DatabaseCorruptionError(
                    f"Invalid RKDB magic bytes: {magic!r} (expected: {RKDB_MAGIC!r})",
                    database_path=file_path,
                    offset=0
                )

            # Read version
            version_bytes = f.read(4)
            if len(version_bytes) != 4:
                raise DatabaseCorruptionError(
                    "Could not read version bytes",
                    database_path=file_path,
                    offset=4
                )

            version = struct.unpack('<I', version_bytes)[0]
            if version > RKDB_CURRENT_VERSION:
                raise ValidationError(
                    f"Unsupported RKDB version: {version} (max supported: {RKDB_CURRENT_VERSION})"
                )

            # Read k-mer size
            kmer_bytes = f.read(1)
            if len(kmer_bytes) != 1:
                raise DatabaseCorruptionError(
                    "Could not read k-mer size",
                    database_path=file_path,
                    offset=8
                )

            kmer_size = kmer_bytes[0]
            if kmer_size == 0 or kmer_size > 128:
                raise ValidationError(
                    f"Invalid k-mer size: {kmer_size} (valid range: 1-128)"
                )

            # Read total k-mers
            total_kmers_bytes = f.read(8)
            if len(total_kmers_bytes) != 8:
                raise DatabaseCorruptionError(
                    "Could not read total k-mers count",
                    database_path=file_path,
                    offset=9
                )

            total_kmers = struct.unpack('<Q', total_kmers_bytes)[0]

            # Calculate expected file size
            if version >= 2 and kmer_size > 32:
                # u128 encoding
                entry_size = 16 + 4  # kmer (16) + count (4)
            else:
                # u64 encoding
                entry_size = 8 + 4   # kmer (8) + count (4)

            expected_min_size = RKDB_MIN_SIZE + (total_kmers * entry_size)
            if file_size < expected_min_size:
                raise DatabaseCorruptionError(
                    f"File size inconsistency: {file_size} bytes (expected at least: {expected_min_size})",
                    database_path=file_path
                )

            return {
                "valid": True,
                "version": version,
                "kmer_size": kmer_size,
                "total_kmers": total_kmers,
                "file_size": file_size,
                "entry_size": entry_size,
                "encoding": "u128" if version >= 2 and kmer_size > 32 else "u64"
            }

    except struct.error as e:
        raise DatabaseCorruptionError(
            f"Binary data parsing error: {e}",
            database_path=file_path
        )
    except IOError as e:
        raise DatabaseCorruptionError(
            f"I/O error reading database: {e}",
            database_path=file_path
        )


def validate_fasta_file(file_path: str) -> Dict[str, Any]:
    """
    Validate FASTA file format.

    Args:
        file_path: Path to the FASTA file

    Returns:
        Dictionary containing validation results

    Raises:
        FileNotFoundError: If file doesn't exist
        ValidationError: If file format is invalid
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"FASTA file not found: {file_path}")

    if not os.path.isfile(file_path):
        raise ValidationError(f"Path is not a file: {file_path}")

    try:
        with open(file_path, 'r') as f:
            first_line = f.readline().strip()
            if not first_line:
                raise ValidationError("FASTA file is empty")

            if not first_line.startswith('>'):
                raise ValidationError(
                    f"Invalid FASTA format: first line must start with '>' (got: {first_line[:50]}...)"
                )

            # Count sequences and validate format
            sequence_count = 0
            total_length = 0
            in_sequence = False
            line_number = 0

            f.seek(0)
            for line in f:
                line_number += 1
                line = line.strip()

                if not line:
                    continue

                if line.startswith('>'):
                    sequence_count += 1
                    in_sequence = True
                elif in_sequence:
                    # Validate sequence contains only valid DNA characters
                    invalid_chars = set(line.upper()) - set('ACGTN-')
                    if invalid_chars:
                        raise ValidationError(
                            f"Invalid characters in sequence at line {line_number}: {invalid_chars}"
                        )
                    total_length += len(line)
                else:
                    raise ValidationError(
                        f"Invalid FASTA format: sequence data before header at line {line_number}"
                    )

            if sequence_count == 0:
                raise ValidationError("No sequences found in FASTA file")

            return {
                "valid": True,
                "sequence_count": sequence_count,
                "total_length": total_length,
                "file_size": os.path.getsize(file_path)
            }

    except IOError as e:
        raise ValidationError(f"Error reading FASTA file: {e}")


def validate_fastq_file(file_path: str) -> Dict[str, Any]:
    """
    Validate FASTQ file format.

    Args:
        file_path: Path to the FASTQ file

    Returns:
        Dictionary containing validation results

    Raises:
        FileNotFoundError: If file doesn't exist
        ValidationError: If file format is invalid
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"FASTQ file not found: {file_path}")

    if not os.path.isfile(file_path):
        raise ValidationError(f"Path is not a file: {file_path}")

    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()

            if len(lines) == 0:
                raise ValidationError("FASTQ file is empty")

            if len(lines) % 4 != 0:
                raise ValidationError(
                    f"Invalid FASTQ format: number of lines ({len(lines)}) is not divisible by 4"
                )

            sequence_count = 0
            total_length = 0

            for i in range(0, len(lines), 4):
                header_line = lines[i].strip()
                sequence_line = lines[i + 1].strip()
                plus_line = lines[i + 2].strip()
                quality_line = lines[i + 3].strip()

                # Validate header
                if not header_line.startswith('@'):
                    raise ValidationError(
                        f"Invalid FASTQ format: header line {i+1} must start with '@' (got: {header_line[:50]}...)"
                    )

                # Validate plus line
                if not plus_line.startswith('+'):
                    raise ValidationError(
                        f"Invalid FASTQ format: plus line {i+3} must start with '+' (got: {plus_line})"
                    )

                # Validate sequence and quality length match
                seq_len = len(sequence_line)
                qual_len = len(quality_line)

                if seq_len != qual_len:
                    raise ValidationError(
                        f"Invalid FASTQ format: sequence and quality length mismatch at record {i//4 + 1} "
                        f"(sequence: {seq_len}, quality: {qual_len})"
                    )

                # Validate sequence characters
                invalid_chars = set(sequence_line.upper()) - set('ACGTN-')
                if invalid_chars:
                    raise ValidationError(
                        f"Invalid characters in sequence at record {i//4 + 1}: {invalid_chars}"
                    )

                sequence_count += 1
                total_length += seq_len

            if sequence_count == 0:
                raise ValidationError("No sequences found in FASTQ file")

            return {
                "valid": True,
                "sequence_count": sequence_count,
                "total_length": total_length,
                "file_size": os.path.getsize(file_path)
            }

    except IOError as e:
        raise ValidationError(f"Error reading FASTQ file: {e}")


def validate_sequence_string(sequence: str) -> Dict[str, Any]:
    """
    Validate a DNA sequence string.

    Args:
        sequence: DNA sequence to validate

    Returns:
        Dictionary containing validation results

    Raises:
        ValidationError: If sequence is invalid
    """
    if not sequence:
        raise ValidationError("Sequence is empty")

    # Remove whitespace and convert to uppercase
    clean_seq = ''.join(sequence.split()).upper()

    if not clean_seq:
        raise ValidationError("Sequence contains no valid characters")

    # Check for valid DNA characters
    invalid_chars = set(clean_seq) - set('ACGTN-')
    if invalid_chars:
        raise ValidationError(
            f"Invalid characters in sequence: {invalid_chars} "
            f"(valid characters: A, C, G, T, N, -)"
        )

    # Count nucleotides
    counts = {
        'A': clean_seq.count('A'),
        'C': clean_seq.count('C'),
        'G': clean_seq.count('G'),
        'T': clean_seq.count('T'),
        'N': clean_seq.count('N'),
        '-': clean_seq.count('-')
    }

    # Calculate statistics
    total_valid = counts['A'] + counts['C'] + counts['G'] + counts['T']
    gc_content = (counts['G'] + counts['C']) / total_valid * 100 if total_valid > 0 else 0

    return {
        "valid": True,
        "length": len(clean_seq),
        "counts": counts,
        "gc_content": gc_content,
        "has_ambiguous": counts['N'] > 0,
        "has_gaps": counts['-'] > 0
    }


def validate_kmer_size(k: int, max_k: int = 128) -> None:
    """
    Validate k-mer size parameter.

    Args:
        k: K-mer size to validate
        max_k: Maximum allowed k-mer size

    Raises:
        ValidationError: If k-mer size is invalid
    """
    if not isinstance(k, int):
        raise ValidationError(f"K-mer size must be an integer, got {type(k).__name__}")

    if k <= 0:
        raise ValidationError(f"K-mer size must be positive, got {k}")

    if k > max_k:
        raise ValidationError(f"K-mer size too large: {k} (maximum: {max_k})")

    # Check if k-mer fits in encoding
    if k > 64:
        # Requires u128 encoding
        if k * 2 > 128:
            raise ValidationError(f"K-mer size {k} exceeds maximum encodable size (128 bits)")


def validate_thread_count(threads: int) -> None:
    """
    Validate thread count parameter.

    Args:
        threads: Thread count to validate

    Raises:
        ValidationError: If thread count is invalid
    """
    if not isinstance(threads, int):
        raise ValidationError(f"Thread count must be an integer, got {type(threads).__name__}")

    if threads < 1:
        raise ValidationError(f"Thread count must be at least 1, got {threads}")

    # Check against system CPU count (optional warning)
    import multiprocessing
    cpu_count = multiprocessing.cpu_count()
    if threads > cpu_count * 2:
        # This is just a warning, not an error
        pass


def validate_export_format(export_format: str) -> str:
    """
    Validate export format parameter.

    Args:
        export_format: Export format to validate

    Returns:
        Normalized export format

    Raises:
        ValidationError: If export format is invalid
    """
    if not isinstance(export_format, str):
        raise ValidationError(f"Export format must be a string, got {type(export_format).__name__}")

    format_lower = export_format.lower().strip()

    valid_formats = {
        'text': 'text',
        'txt': 'text',
        'csv': 'csv',
        'json': 'json',
        'tsv': 'tsv'
    }

    if format_lower not in valid_formats:
        raise ValidationError(
            f"Invalid export format: {export_format} "
            f"(valid formats: {', '.join(valid_formats.keys())})"
        )

    return valid_formats[format_lower]


def validate_file_path(file_path: str, must_exist: bool = True) -> str:
    """
    Validate file path parameter.

    Args:
        file_path: File path to validate
        must_exist: Whether the file must already exist

    Returns:
        Normalized file path

    Raises:
        ValidationError: If file path is invalid
        FileNotFoundError: If must_exist is True and file doesn't exist
    """
    if not isinstance(file_path, str):
        raise ValidationError(f"File path must be a string, got {type(file_path).__name__}")

    if not file_path.strip():
        raise ValidationError("File path cannot be empty")

    # Convert to Path object for normalization
    path = Path(file_path)

    if must_exist and not path.exists():
        raise FileNotFoundError(f"File does not exist: {path}")

    if path.exists() and not path.is_file():
        raise ValidationError(f"Path is not a file: {path}")

    return str(path.resolve())


def validate_compression_algorithm(algorithm: str) -> str:
    """
    Validate compression algorithm parameter.

    Args:
        algorithm: Compression algorithm to validate

    Returns:
        Normalized algorithm name

    Raises:
        ValidationError: If algorithm is invalid
    """
    if not isinstance(algorithm, str):
        raise ValidationError(f"Compression algorithm must be a string, got {type(algorithm).__name__}")

    algo_lower = algorithm.lower().strip()

    valid_algorithms = {
        'gzip': 'gzip',
        'gz': 'gzip',
        'bzip2': 'bzip2',
        'bz2': 'bzip2',
        'lz4': 'lz4',
        'zstd': 'zstd'
    }

    if algo_lower not in valid_algorithms:
        raise ValidationError(
            f"Invalid compression algorithm: {algorithm} "
            f"(valid algorithms: {', '.join(valid_algorithms.keys())})"
        )

    return valid_algorithms[algo_lower]