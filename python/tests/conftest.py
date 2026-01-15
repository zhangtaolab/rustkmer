"""Pytest configuration and fixtures for rustkmer tests."""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest


@pytest.fixture(scope="session")
def test_data_dir():
    """Path to the test data directory."""
    return Path(__file__).parent / "test_data"


@pytest.fixture(scope="session")
def cli_binary():
    """Path to rustkmer CLI executable."""
    # Find rustkmer in the build directory
    cli_path = Path(__file__).parent.parent.parent / "target" / "release" / "rustkmer"
    if not cli_path.exists():
        pytest.skip(f"rustkmer CLI not found at {cli_path}")
    return str(cli_path)


@pytest.fixture(scope="session")
def test_databases():
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


@pytest.fixture(scope="session")
def cli_comparator(cli_binary):
    """Create CLI comparator for the session."""
    from .utils import CLIComparator

    return CLIComparator(cli_binary)


@pytest.fixture
def sample_database(test_data_dir):
    """Get a sample database for testing (tiny_test.rkdb)."""
    db_file = test_data_dir / "tiny_test.rkdb"
    if not db_file.exists():
        pytest.skip(f"Test database not found: {db_file}")
    return str(db_file)


@pytest.fixture
def test_kmer_sets():
    """Return sets of test k-mers for different scenarios."""
    return {
        "edge_cases": {
            "all_A": "AAAAAAA",
            "all_C": "CCCCCCC",
            "all_G": "GGGGGGG",
            "all_T": "TTTTTTT",
        },
        "palindromic": ["ATGCGCAT", "CGATATCG"],
        "high_complexity": ["ATCGATCG", "GCTAGCTA"],
        "invalid": ["ATCGX", "ATCG", "toolongkkkkkkkkkkkkkkk"],
    }


@pytest.fixture(scope="session")
def pyo3_available():
    """Check if PyO3 is available"""
    try:
        import rustkmer_pyo3

        return True
    except ImportError:
        return False


@pytest.fixture(scope="session")
def rustkmer_cli_available():
    """Check if CLI is available"""
    import shutil

    return shutil.which("rustkmer") is not None


# Auto-use fixtures for all tests
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup environment for all tests."""
    # Set a consistent test environment
    monkeypatch.setenv("RUSTKMER_TEST_MODE", "1")
    # Clear any existing RUSTKMER_PATH to ensure consistent testing
    monkeypatch.delenv("RUSTKMER_PATH", raising=False)


# Configure pytest with custom markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests requiring rustkmer binary",
    )
    config.addinivalue_line(
        "markers", "benchmark: marks tests as performance benchmarks"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add marks based on test names/locations."""
    for item in items:
        # Mark integration tests
        if "integration" in str(item.fspath) or "test_integration" in item.name:
            item.add_marker(pytest.mark.integration)

        # Mark benchmark tests
        if "benchmark" in str(item.fspath) or "test_benchmark" in item.name:
            item.add_marker(pytest.mark.benchmark)
            item.add_marker(pytest.mark.slow)

        # Mark CLI-API consistency tests
        if "cli_api_consistency" in str(item.fspath) or item.name:
            item.add_marker(pytest.mark.integration)

        # Mark database-specific tests
        if "databases" in str(item.fspath) or item.name:
            item.add_marker(pytest.mark.integration)

        # Mark PyO3 tests
        if "pyo3" in str(item.fspath) or "test_pyo3" in item.name:
            item.add_marker(pytest.mark.pyo3)

        # Mark subprocess tests
        if "subprocess" in str(item.fspath) or "test_subprocess" in item.name:
            item.add_marker(pytest.mark.subprocess)

        # Mark parity tests
        if "parity" in str(item.fspath) or "test_parity" in item.name:
            item.add_marker(pytest.mark.parity)

        # Mark contract tests
        if "contract" in str(item.fspath) or "test_contract" in item.name:
            item.add_marker(pytest.mark.contract)
