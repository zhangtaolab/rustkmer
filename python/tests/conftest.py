"""Pytest configuration and fixtures for rustkmer tests."""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_db_file():
    """Create a temporary file path for database testing."""
    with tempfile.NamedTemporaryFile(suffix='.rkdb', delete=False) as f:
        temp_path = f.name
    yield temp_path
    # Clean up
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def test_database_path():
    """Path to a real test database (if available)."""
    # Check for the real test database mentioned in the spec
    test_path = "/Users/forrest/Data/data/kmer/K19/R1_001.rkdb"
    if os.path.exists(test_path):
        yield test_path
    else:
        pytest.skip(f"Test database not found at {test_path}")


@pytest.fixture
def mock_kmer_data():
    """Mock k-mer data for testing without real database."""
    return {
        "ATCGATCGATCGATCGATCG": {"count": 42, "canonical": "ATCGATCGATCGATCGATCG"},
        "GCTAGCTAGCTAGCTAGCTA": {"count": 15, "canonical": "ATCGATCGATCGATCGATCG"},
        "CCCCCCCCCCCCCCCCCCCC": {"count": 100, "canonical": "GGGGGGGGGGGGGGGGGGGG"},
    }


@pytest.fixture
def sample_kmers():
    """Sample k-mer sequences for testing."""
    return [
        "ATCGATCGATCGATCGATCG",
        "GCTAGCTAGCTAGCTAGCTA",
        "CCCCCCCCCCCCCCCCCCCC",
        "GGGGGGGGGGGGGGGGGGGG",
        "TATATATATATATATATATA",
    ]


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup environment for all tests."""
    # Set a consistent test environment
    monkeypatch.setenv("RUSTKMER_TEST_MODE", "1")
    # Clear any existing RUSTKMER_PATH to ensure consistent testing
    monkeypatch.delenv("RUSTKMER_PATH", raising=False)


@pytest.fixture
def mock_rustkmer_binary():
    """Mock rustkmer binary path for testing."""
    return os.path.join(
        os.path.dirname(__file__),
        "..",
        "rustkmer",
        "bin",
        "rustkmer-test"
    )


# Skip integration tests if rustkmer is not installed
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests requiring rustkmer binary"
    )
    config.addinivalue_line(
        "markers",
        "benchmark: marks tests as performance benchmarks"
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

        # Mark performance tests
        if "performance" in str(item.fspath) or "test_performance" in item.name:
            item.add_marker(pytest.mark.benchmark)
            item.add_marker(pytest.mark.slow)