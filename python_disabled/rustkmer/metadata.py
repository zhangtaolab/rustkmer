"""
Database metadata extraction utilities.

This module provides utilities for extracting metadata from k-mer database files,
including file system metadata and database-specific information.
"""

import os
import time
from typing import Dict, Any, Optional
from pathlib import Path
import struct


class DatabaseMetadata:
    """Extracts and stores metadata about k-mer database files."""

    def __init__(self, file_path: str):
        """
        Initialize metadata extraction for a database file.

        Args:
            file_path: Path to the database file
        """
        self.file_path = file_path
        self._metadata = {}

    def extract_all_metadata(self) -> Dict[str, Any]:
        """
        Extract all available metadata from the database file.

        Returns:
            Dictionary containing all metadata
        """
        metadata = {}

        # Extract file system metadata
        metadata.update(self._extract_filesystem_metadata())

        # Extract database header metadata
        metadata.update(self._extract_database_header())

        return metadata

    def _extract_filesystem_metadata(self) -> Dict[str, Any]:
        """Extract file system metadata."""
        metadata = {}

        if not os.path.exists(self.file_path):
            return metadata

        stat = os.stat(self.file_path)

        # File size information
        metadata['file_size'] = stat.st_size
        metadata['file_size_mb'] = stat.st_size / (1024 * 1024)
        metadata['file_size_gb'] = stat.st_size / (1024 * 1024 * 1024)

        # Timestamp information
        metadata['created_time'] = stat.st_ctime
        metadata['modified_time'] = stat.st_mtime
        metadata['accessed_time'] = stat.st_atime

        # Human-readable timestamps
        metadata['created_date'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_ctime))
        metadata['modified_date'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
        metadata['accessed_date'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_atime))

        # File permissions
        metadata['permissions'] = oct(stat.st_mode)[-3:]

        # File type information
        metadata['is_file'] = os.path.isfile(self.file_path)
        metadata['is_readable'] = os.access(self.file_path, os.R_OK)
        metadata['is_writable'] = os.access(self.file_path, os.W_OK)

        return metadata

    def _extract_database_header(self) -> Dict[str, Any]:
        """Extract database header metadata from RKDB files."""
        metadata = {}

        try:
            with open(self.file_path, 'rb') as f:
                # Read magic number (4 bytes)
                magic = f.read(4)
                if magic != b'RKDB':
                    return metadata  # Not an RKDB file

                metadata['format'] = 'RKDB'
                metadata['magic'] = magic.decode('ascii', errors='ignore')

                # Read version (2 bytes, little-endian)
                version_bytes = f.read(2)
                if len(version_bytes) == 2:
                    metadata['version'] = struct.unpack('<H', version_bytes)[0]

                # Read k-mer size (1 byte)
                kmer_size_bytes = f.read(1)
                if len(kmer_size_bytes) == 1:
                    metadata['kmer_size'] = struct.unpack('B', kmer_size_bytes)[0]

                # Skip padding (1 byte)
                f.read(1)

                # Read padding (2 bytes)
                f.read(2)

                # Read total k-mers (8 bytes, little-endian)
                total_kmers_bytes = f.read(8)
                if len(total_kmers_bytes) == 8:
                    metadata['total_kmers'] = struct.unpack('<Q', total_kmers_bytes)[0]

                # Read flags (1 byte)
                flags_bytes = f.read(1)
                if len(flags_bytes) == 1:
                    flags = struct.unpack('B', flags_bytes)[0]
                    metadata['sorted'] = bool(flags & 0x01)
                    metadata['canonical'] = bool(flags & 0x02)

                # Skip remaining header fields to get to data offset
                f.read(7)  # Skip padding

                # Read data offset (8 bytes, little-endian)
                data_offset_bytes = f.read(8)
                if len(data_offset_bytes) == 8:
                    metadata['data_offset'] = struct.unpack('<Q', data_offset_bytes)[0]

                # Read index offset (8 bytes, little-endian)
                index_offset_bytes = f.read(8)
                if len(index_offset_bytes) == 8:
                    metadata['index_offset'] = struct.unpack('<Q', index_offset_bytes)[0]

                # Calculate additional metadata
                if 'total_kmers' in metadata and 'file_size' in metadata:
                    if metadata['total_kmers'] > 0:
                        metadata['bytes_per_kmer'] = metadata['file_size'] / metadata['total_kmers']
                    else:
                        metadata['bytes_per_kmer'] = 0

                # Estimate database density
                if 'kmer_size' in metadata and metadata['kmer_size'] > 0:
                    possible_kmers = 4 ** metadata['kmer_size']
                    if 'total_kmers' in metadata and possible_kmers > 0:
                        metadata['space_utilization'] = metadata['total_kmers'] / possible_kmers

        except Exception as e:
            metadata['header_error'] = str(e)

        return metadata

    def get_creation_info(self) -> Dict[str, Any]:
        """Get creation information about the database."""
        creation_info = {}

        if not os.path.exists(self.file_path):
            return creation_info

        stat = os.stat(self.file_path)

        creation_info['timestamp'] = stat.st_ctime
        creation_info['date'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_ctime))
        creation_info['iso_date'] = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(stat.st_ctime))
        creation_info['days_since_creation'] = (time.time() - stat.st_ctime) / (24 * 60 * 60)

        # Calculate file age category
        days_old = creation_info['days_since_creation']
        if days_old < 1:
            creation_info['age_category'] = 'new'
        elif days_old < 7:
            creation_info['age_category'] = 'recent'
        elif days_old < 30:
            creation_info['age_category'] = 'weeks'
        elif days_old < 365:
            creation_info['age_category'] = 'months'
        else:
            creation_info['age_category'] = 'years'

        return creation_info

    def get_database_info(self) -> Dict[str, Any]:
        """Get database-specific information."""
        db_info = {}

        # Extract basic database info from header
        header_info = self._extract_database_header()
        db_info.update(header_info)

        # Add derived information
        if 'file_size' in db_info and 'total_kmers' in db_info:
            if db_info['total_kmers'] > 0:
                db_info['avg_bytes_per_kmer'] = db_info['file_size'] / db_info['total_kmers']
                db_info['compression_ratio'] = (20 * db_info['total_kmers']) / db_info['file_size']  # Assuming 20 bytes per k-mer originally
            else:
                db_info['avg_bytes_per_kmer'] = 0
                db_info['compression_ratio'] = 0

        # Format-specific information
        if db_info.get('format') == 'RKDB':
            db_info['format_description'] = 'RustKmer Database Format'
            if 'version' in db_info:
                db_info['format_version'] = f"v{db_info['version']}"

        return db_info

    def to_dict(self) -> Dict[str, Any]:
        """Convert all metadata to a dictionary."""
        return {
            'file_path': self.file_path,
            'metadata': self.extract_all_metadata(),
            'creation_info': self.get_creation_info(),
            'database_info': self.get_database_info()
        }


def extract_metadata(file_path: str) -> Dict[str, Any]:
    """
    Convenience function to extract metadata from a database file.

    Args:
        file_path: Path to the database file

    Returns:
        Dictionary containing all metadata
    """
    extractor = DatabaseMetadata(file_path)
    return extractor.to_dict()


def get_file_age_category(file_path: str) -> str:
    """
    Get the age category of a file.

    Args:
        file_path: Path to the file

    Returns:
        Age category: 'new', 'recent', 'weeks', 'months', or 'years'
    """
    if not os.path.exists(file_path):
        return 'unknown'

    days_old = (time.time() - os.path.getctime(file_path)) / (24 * 60 * 60)

    if days_old < 1:
        return 'new'
    elif days_old < 7:
        return 'recent'
    elif days_old < 30:
        return 'weeks'
    elif days_old < 365:
        return 'months'
    else:
        return 'years'