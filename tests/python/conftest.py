"""
Pytest configuration and shared fixtures for RustKmer Python tests.
"""

import pytest
import sys
import os

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