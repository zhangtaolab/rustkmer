"""
Pytest configuration and shared fixtures for RustKmer Python tests.
"""

import pytest
import sys
import os
import tempfile
from pathlib import Path

# Add the python directory to the Python path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python'))

@pytest.fixture
def basic_dna_sequence():
    """A basic DNA sequence for testing."""
    return "ATGCGATGCTAGCGCTAGCTATGCGATGCTAGCGCTAGC"

@pytest.fixture
def short_dna_sequence():
    """A short DNA sequence for testing."""
    return "ATGCGATG"

@pytest.fixture
def invalid_dna_sequence():
    """An invalid DNA sequence containing invalid characters."""
    return "ATGCGXATGC"

@pytest.fixture
def temp_db_file(tmp_path):
    """Create a temporary database file path."""
    return tmp_path / "test_database.rkdb"

@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file."""
    return tmp_path / "test_file.txt"

@pytest.fixture
def temp_dir(tmp_path):
    """Provide the temporary directory path."""
    return tmp_path

@pytest.fixture
def sample_database():
    """Create a sample database for testing."""
    from rustkmer import Database

    # Create a temporary database file
    fd, db_path = tempfile.mkstemp(suffix='.rkdb')
    os.close(fd)

    try:
        # Create a minimal database file
        with open(db_path, 'wb') as f:
            # Write RKDB header
            f.write(b'RKDB\x01\x00\x00\x00')
            # Write k-mer size
            f.write((4).to_bytes(4, byteorder='little'))
            # Write statistics (all zeros for minimal database)
            f.write(b'\x00' * 16)
            # Write minimal k-mer data
            f.write(b'ATCG\x01\x00\x00\x00')
            f.write(b'TCGA\x01\x00\x00\x00')
            f.write(b'CGAT\x01\x00\x00\x00')
            f.write(b'GATC\x01\x00\x00\x00')

        # Create database object
        db = Database(db_path, preload=False)
        db.load()
        yield db
    finally:
        # Cleanup
        try:
            os.unlink(db_path)
        except:
            pass