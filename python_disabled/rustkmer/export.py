"""
Database export functionality for RKDB files.

This module provides classes and functions for exporting k-mer data
to various formats including text, CSV, JSON, and TSV with filtering options.
"""

import os
import csv
import json
import gzip
import bz2
import zipfile
from typing import Dict, List, Optional, Any, Union, TextIO, BinaryIO, Iterable
from enum import Enum
from pathlib import Path
import sys

# Import error handling utilities
from .error_handling import (
    handle_errors, ErrorContext, safe_execute, validate_inputs,
    validate_file_path, validate_one_of, validate_non_negative_int,
    validate_range
)
from .exceptions import ExportError, ValidationError

# Import from Rust extension if available
try:
    from ._rustkmer import Database

    HAS_RUST_EXPORT = True
except ImportError:
    HAS_RUST_EXPORT = False
    Database = None


class OutputFormat(Enum):
    """Supported output formats for database export."""

    DICT = "dict"      # Python dictionary
    JSON = "json"      # JSON string/file
    TSV = "tsv"        # Tab-separated values
    CSV = "csv"        # Comma-separated values
    TEXT = "text"      # Human-readable text format


class CompressionFormat(Enum):
    """Supported compression formats for export output."""

    NONE = "none"      # No compression
    GZIP = "gzip"      # gzip compression (.gz)
    BZIP2 = "bzip2"    # bzip2 compression (.bz2)
    ZIP = "zip"        # zip compression (.zip)


class ExportConfig:
    """Configuration for database export operations."""

    def __init__(
        self,
        format: OutputFormat = OutputFormat.TEXT,
        min_count: Optional[int] = None,
        max_count: Optional[int] = None,
        include_header: bool = True,
        sort_by: Optional[str] = None,  # 'count', 'kmer', 'none'
        reverse: bool = False,
        delimiter: Optional[str] = None,  # For CSV/TSV
        quotechar: Optional[str] = None,  # For CSV
        quoting: Optional[int] = None,  # CSV quoting mode
        encoding: str = 'utf-8',
        batch_size: int = 100000,  # For streaming large databases
        compression: CompressionFormat = CompressionFormat.NONE,
        compression_level: Optional[int] = None,  # Compression level (1-9)
    ) -> None:
        """
        Initialize export configuration.

        Args:
            format: Output format for export
            min_count: Minimum k-mer count to include (inclusive)
            max_count: Maximum k-mer count to include (inclusive)
            include_header: Whether to include header row in structured formats
            sort_by: Field to sort by ('count', 'kmer', 'none')
            reverse: Whether to sort in reverse order
            delimiter: Custom delimiter for CSV/TSV format
            quotechar: Quote character for CSV format
            quoting: CSV quoting mode
            encoding: Text encoding for output
            batch_size: Number of k-mers to process at once
            compression: Compression format for output
            compression_level: Compression level (1-9, None for default)
        """
        self.format = format
        self.min_count = min_count
        self.max_count = max_count
        self.include_header = include_header
        self.sort_by = sort_by or 'none'
        self.reverse = reverse
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.quoting = quoting
        self.encoding = encoding
        self.batch_size = batch_size
        self.compression = compression
        self.compression_level = compression_level

        # Set default compression levels
        if self.compression_level is None:
            if self.compression == CompressionFormat.GZIP:
                self.compression_level = 6
            elif self.compression == CompressionFormat.BZIP2:
                self.compression_level = 9
            elif self.compression == CompressionFormat.ZIP:
                self.compression_level = 6

        # Set default delimiters
        if self.format == OutputFormat.TSV and self.delimiter is None:
            self.delimiter = '\t'
        elif self.format == OutputFormat.CSV and self.delimiter is None:
            self.delimiter = ','
        if self.quotechar is None and self.format == OutputFormat.CSV:
            self.quotechar = '"'
        if self.quoting is None and self.format == OutputFormat.TSV:
            self.quoting = csv.QUOTE_NONE
        elif self.quoting is None:
            self.quoting = csv.QUOTE_MINIMAL


class ExportStats:
    """Statistics for export operations."""

    def __init__(self) -> None:
        """Initialize export statistics."""
        self.total_kmers = 0
        self.exported_kmers = 0
        self.filtered_out = 0
        self.start_time = None
        self.end_time = None
        self.output_file = ""
        self.output_format = ""
        self.compression = ""
        self.bytes_written = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_kmers": self.total_kmers,
            "exported_kmers": self.exported_kmers,
            "filtered_out": self.filtered_out,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "output_file": self.output_file,
            "output_format": self.output_format,
            "compression": self.compression,
            "bytes_written": self.bytes_written,
            "filter_efficiency": self.filtered_out / self.total_kmers if self.total_kmers > 0 else 0
        }


class DatabaseExporter:
    """Export k-mer data from RKDB databases to various formats."""

    def __init__(self, database, config: Optional[ExportConfig] = None) -> None:
        """
        Initialize database exporter.

        Args:
            database: Database instance to export from
            config: Export configuration options
        """
        self.database = database
        self.config = config or ExportConfig()
        self.stats = ExportStats()

    @handle_errors("database_export")
    def export(self, output: Union[str, TextIO, BinaryIO]) -> ExportStats:
        """
        Export database to specified output.

        Args:
            output: Output file path or file-like object

        Returns:
            Export statistics

        Raises:
            ExportError: If export operation fails
            ValidationError: If output path is invalid
        """
        import time
        self.stats.start_time = time.time()

        # Create error context
        context = ErrorContext(
            operation="database_export",
            component="DatabaseExporter.export",
            file_path=str(output) if isinstance(output, (str, Path)) else None,
            additional_info={
                "output_format": self.config.format.value,
                "compression": self.config.compression.value,
                "min_count": self.config.min_count,
                "max_count": self.config.max_count
            }
        )

        try:
            self.stats.output_format = self.config.format.value
            self.stats.compression = self.config.compression.value

            if isinstance(output, (str, Path)):
                # Validate file path
                if not validate_file_path(str(output)):
                    raise ValidationError(
                        f"Invalid output path: {output}",
                        error_code="INVALID_OUTPUT_PATH",
                        parameter="output"
                    )

                # File path provided
                self.stats.output_file = str(output)
                with self._open_output_file(output, self.config.encoding) as f:
                    self._export_to_file(f)
            else:
                # File-like object provided
                self._export_to_file(output)

        except (ValidationError, ExportError):
            # Re-raise our custom exceptions
            raise
        except (IOError, OSError) as e:
            raise ExportError(
                f"Failed to write export: {str(e)}",
                error_code="EXPORT_WRITE_FAILED",
                file_path=str(output) if isinstance(output, (str, Path)) else None,
                context=context.to_dict()
            ) from e
        except Exception as e:
            raise ExportError(
                f"Export operation failed: {str(e)}",
                error_code="EXPORT_FAILED",
                context=context.to_dict()
            ) from e
        finally:
            import time
            self.stats.end_time = time.time()

        return self.stats

    def export_to_dict(self) -> List[Dict[str, Any]]:
        """
        Export database to Python dictionary format.

        Returns:
            List of k-mer dictionaries
        """
        # Get all k-mers from database
        kmer_data = self._get_all_kmers()

        # Apply filters
        filtered_data = self._apply_filters(kmer_data)

        # Sort if requested
        if self.config.sort_by != 'none':
            filtered_data = self._sort_data(filtered_data)

        self.stats.total_kmers = len(kmer_data)
        self.stats.exported_kmers = len(filtered_data)
        self.stats.filtered_out = self.stats.total_kmers - self.stats.exported_kmers

        return filtered_data

    def _open_output_file(self, path: Union[str, Path], encoding: str) -> Any:
        """Open output file with appropriate mode based on format and compression."""
        path = Path(path)

        # Add appropriate file extension based on compression
        if self.config.compression != CompressionFormat.NONE:
            if self.config.compression == CompressionFormat.GZIP:
                if not str(path).endswith('.gz'):
                    path = path.with_suffix(str(path).suffix + '.gz')
                return gzip.open(path, 'wt', encoding=encoding, newline='',
                                 compresslevel=self.config.compression_level)
            elif self.config.compression == CompressionFormat.BZIP2:
                if not str(path).endswith('.bz2'):
                    path = path.with_suffix(str(path).suffix + '.bz2')
                return bz2.open(path, 'wt', encoding=encoding, newline='',
                                compresslevel=self.config.compression_level)
            elif self.config.compression == CompressionFormat.ZIP:
                if not str(path).endswith('.zip'):
                    path = path.with_suffix(str(path).suffix + '.zip')
                return self._open_zip_file(path, encoding)

        # No compression - use regular file open
        if self.config.format in [OutputFormat.JSON, OutputFormat.TEXT]:
            return open(path, 'w', encoding=encoding, newline='')
        else:
            return open(path, 'w', encoding=encoding, newline='')

    def _open_zip_file(self, path: Path, encoding: str) -> 'DatabaseExporter.ZipFileWrapper':
        """Open file for ZIP compression."""
        # Create zip file with a single entry
        zip_file = zipfile.ZipFile(
            path,
            'w',
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=self.config.compression_level
        )

        # Return a wrapper that writes to the zip file
        class ZipFileWrapper:
            def __init__(self, zip_file, filename) -> None:
                self.zip_file = zip_file
                self.buffer = []
                self.filename = filename

            def write(self, data: str) -> None:
                self.buffer.append(data)

            def flush(self) -> None:
                pass

            def close(self) -> None:
                content = ''.join(self.buffer)
                self.zip_file.writestr(self.filename, content.encode(encoding))
                self.zip_file.close()

        # Use a simple filename based on format
        filename = 'export'
        if self.config.format == OutputFormat.JSON:
            filename += '.json'
        elif self.config.format == OutputFormat.CSV:
            filename += '.csv'
        elif self.config.format == OutputFormat.TSV:
            filename += '.tsv'
        else:
            filename += '.txt'

        return ZipFileWrapper(zip_file, filename)

    def _export_to_file(self, file_obj: Any) -> None:
        """Export database to file object."""
        if self.config.format == OutputFormat.DICT:
            data = self.export_to_dict()
            file_obj.write(str(data))

        elif self.config.format == OutputFormat.JSON:
            self._export_json(file_obj)

        elif self.config.format in [OutputFormat.CSV, OutputFormat.TSV]:
            self._export_csv(file_obj)

        elif self.config.format == OutputFormat.TEXT:
            self._export_text(file_obj)

        else:
            raise ValueError(f"Unsupported export format: {self.config.format}")

    def _export_json(self, file_obj: Any) -> None:
        """Export database to JSON format."""
        data = self.export_to_dict()

        # Create JSON with pretty printing
        json.dump(data, file_obj, indent=2, ensure_ascii=False)

        # Update stats
        if hasattr(file_obj, 'tell'):
            self.stats.bytes_written = file_obj.tell()

    def _export_csv(self, file_obj: Any) -> None:
        """Export database to CSV/TSV format."""
        data = self.export_to_dict()

        if not data:
            return

        # Create CSV writer
        writer = csv.writer(
            file_obj,
            delimiter=self.config.delimiter,
            quotechar=self.config.quotechar,
            quoting=self.config.quoting
        )

        # Write header if requested
        if self.config.include_header:
            headers = ['kmer', 'count']
            writer.writerow(headers)

        # Write data rows
        for item in data:
            writer.writerow([item['kmer'], item['count']])

        # Update stats
        if hasattr(file_obj, 'tell'):
            self.stats.bytes_written = file_obj.tell()

    def _export_text(self, file_obj: Any) -> None:
        """Export database to human-readable text format."""
        data = self.export_to_dict()

        if not data:
            file_obj.write("No k-mers found matching the specified filters.\n")
            return

        # Write header
        file_obj.write(f"# RustKmer Database Export\n")
        file_obj.write(f"# Format: {self.config.format.value}\n")
        if self.config.min_count is not None:
            file_obj.write(f"# Min count filter: {self.config.min_count}\n")
        if self.config.max_count is not None:
            file_obj.write(f"# Max count filter: {self.config.max_count}\n")
        file_obj.write(f"# Total k-mers: {self.stats.total_kmers}\n")
        file_obj.write(f"# Exported k-mers: {self.stats.exported_kmers}\n")
        file_obj.write(f"# Filtered out: {self.stats.filtered_out}\n")
        file_obj.write("\n")

        # Write data
        file_obj.write("K-mer\tCount\n")
        file_obj.write("-" * 50 + "\n")

        for item in data:
            file_obj.write(f"{item['kmer']}\t{item['count']}\n")

    def _get_all_kmers(self) -> List[Dict[str, Any]]:
        """Get all k-mers from database."""
        kmer_list = []

        if HAS_RUST_EXPORT and hasattr(self.database, '_get_all_kmers'):
            # Use Rust implementation if available
            kmer_data = self.database._get_all_kmers()
            for kmer, count in kmer_data:
                kmer_list.append({
                    'kmer': kmer,
                    'count': count
                })
        else:
            # Fallback to querying the database
            # This is a simplified version - in a real implementation,
            # we would need to iterate through all possible k-mers
            # or use database-specific export methods
            pass  # Placeholder - would implement database iteration

        return kmer_list

    def _apply_filters(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply count filters to data."""
        if self.config.min_count is None and self.config.max_count is None:
            return data

        filtered = []
        for item in data:
            count = item['count']

            if self.config.min_count is not None and count < self.config.min_count:
                continue
            if self.config.max_count is not None and count > self.config.max_count:
                continue

            filtered.append(item)

        return filtered

    def _sort_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort data by specified field."""
        if self.config.sort_by == 'count':
            data.sort(key=lambda x: x['count'], reverse=self.config.reverse)
        elif self.config.sort_by == 'kmer':
            data.sort(key=lambda x: x['kmer'], reverse=self.config.reverse)

        return data


# Convenience functions
def dump_database(
    database,
    output: Union[str, TextIO],
    format: str = "text",
    min_count: Optional[int] = None,
    max_count: Optional[int] = None,
    **kwargs
) -> ExportStats:
    """
    Convenience function to dump database to file.

    Args:
        database: Database instance to dump
        output: Output file path or file-like object
        format: Output format ('text', 'json', 'csv', 'tsv', 'dict')
        min_count: Minimum count filter
        max_count: Maximum count filter
        **kwargs: Additional configuration options

    Returns:
        Export statistics
    """
    config = ExportConfig(
        format=OutputFormat(format),
        min_count=min_count,
        max_count=max_count,
        **kwargs
    )

    exporter = DatabaseExporter(database, config)
    return exporter.export(output)


@handle_errors("export_to_json")
@validate_inputs({
    'file_path': validate_file_path
})
def export_to_json(database, file_path: str, **kwargs) -> ExportStats:
    """
    Export database to JSON format.

    Args:
        database: Database instance to export
        file_path: Output JSON file path
        **kwargs: Additional export options

    Returns:
        Export statistics

    Raises:
        ExportError: If export fails
        ValidationError: If file path is invalid
    """
    return dump_database(database, file_path, format="json", **kwargs)


@handle_errors("export_to_csv")
@validate_inputs({
    'file_path': validate_file_path
})
def export_to_csv(
    database,
    file_path: str,
    delimiter: Optional[str] = None,
    **kwargs
) -> ExportStats:
    """
    Export database to CSV format.

    Args:
        database: Database instance to export
        file_path: Output CSV file path
        delimiter: Custom delimiter (default: comma)
        **kwargs: Additional export options

    Returns:
        Export statistics

    Raises:
        ExportError: If export fails
        ValidationError: If file path is invalid
    """
    return dump_database(database, file_path, format="csv", delimiter=delimiter, **kwargs)


@handle_errors("export_to_tsv")
@validate_inputs({
    'file_path': validate_file_path
})
def export_to_tsv(database, file_path: str, **kwargs) -> ExportStats:
    """
    Export database to TSV format.

    Args:
        database: Database instance to export
        file_path: Output TSV file path
        **kwargs: Additional export options

    Returns:
        Export statistics

    Raises:
        ExportError: If export fails
        ValidationError: If file path is invalid
    """
    # TSV typically doesn't use quoting
    kwargs.setdefault('quotechar', '\x00')  # Use null char as placeholder (won't be used)
    kwargs.setdefault('quoting', csv.QUOTE_NONE)  # Disable quoting
    return dump_database(database, file_path, format="tsv", **kwargs)