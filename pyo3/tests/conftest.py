"""Pytest configuration and fixtures for pyrustkmer tests."""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

import pytest


@pytest.fixture(scope="session")
def pyo3_test_data_dir():
    """Path to the test data directory (shared with python tests)."""
    return Path(__file__).parent.parent.parent / "python" / "tests" / "test_data"


@pytest.fixture(scope="session")
def pyo3_test_databases(pyo3_test_data_dir):
    """Return metadata for all available test databases."""
    return {
        "tiny_test.rkdb": {
            "size": "8KB",
            "kmer_size": 7,
            "description": "Tiny database for quick unit tests",
            "file_size": 7962,
        },
        "small_test.rkdb": {
            "size": "86KB",
            "kmer_size": 7,
            "description": "Small database for integration tests",
            "file_size": 86402,
        },
        "small_test_k33_C.rkdb": {
            "size": "96KB",
            "kmer_size": 33,
            "description": "Special k=33 database for edge cases",
            "file_size": 95642,
        },
        "medium_test.rkdb": {
            "size": "160KB",
            "kmer_size": 7,
            "description": "Medium database for performance tests",
            "file_size": 159762,
        },
        "large_test.rkdb": {
            "size": "164KB",
            "kmer_size": 7,
            "description": "Large database for stress tests",
            "file_size": 163882,
        },
    }


@pytest.fixture
def tiny_db_path(pyo3_test_data_dir) -> str:
    """Get path to tiny_test.rkdb database."""
    db_file = pyo3_test_data_dir / "tiny_test.rkdb"
    if not db_file.exists():
        pytest.skip(f"Test database not found: {db_file}")
    return str(db_file)


@pytest.fixture
def small_db_path(pyo3_test_data_dir) -> str:
    """Get path to small_test.rkdb database."""
    db_file = pyo3_test_data_dir / "small_test.rkdb"
    if not db_file.exists():
        pytest.skip(f"Test database not found: {db_file}")
    return str(db_file)


@pytest.fixture
def k33_db_path(pyo3_test_data_dir) -> str:
    """Get path to small_test_k33_C.rkdb database."""
    db_file = pyo3_test_data_dir / "small_test_k33_C.rkdb"
    if not db_file.exists():
        pytest.skip(f"Test database not found: {db_file}")
    return str(db_file)


@pytest.fixture
def pyo3_module():
    """Import and return the pyrustkmer module."""
    try:
        import pyrustkmer

        return pyrustkmer
    except ImportError as e:
        pytest.skip(f"pyrustkmer module not installed: {e}")


@pytest.fixture
def PyDatabase(pyo3_module):
    """Return PyDatabase class."""
    if not hasattr(pyo3_module, "PyDatabase"):
        pytest.skip("PyDatabase class not available")
    return pyo3_module.PyDatabase


@pytest.fixture
def PyKmerCounter(pyo3_module):
    """Return PyKmerCounter class."""
    if not hasattr(pyo3_module, "PyKmerCounter"):
        pytest.skip("PyKmerCounter class not available")
    return pyo3_module.PyKmerCounter


@pytest.fixture
def PyFuzzyQuery(pyo3_module):
    """Return PyFuzzyQuery class."""
    if not hasattr(pyo3_module, "PyFuzzyQuery"):
        pytest.skip("PyFuzzyQuery class not available")
    return pyo3_module.PyFuzzyQuery


@pytest.fixture
def PyPrefixQuery(pyo3_module):
    """Return PyPrefixQuery class."""
    if not hasattr(pyo3_module, "PyPrefixQuery"):
        pytest.skip("PyPrefixQuery class not available")
    return pyo3_module.PyPrefixQuery


@pytest.fixture
def LoadMode(pyo3_module):
    """Return LoadMode enum."""
    if not hasattr(pyo3_module, "LoadMode"):
        pytest.skip("LoadMode enum not available")
    return pyo3_module.LoadMode
