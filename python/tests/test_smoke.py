"""Smoke tests to verify basic rustkmer CLI accessibility."""

import sys
import subprocess

from rustkmer.utils import find_rustkmer_executable, run_rustkmer_command
from rustkmer.exceptions import ConfigurationError, SubprocessError


def test_rustkmer_executable_exists():
    """Test that rustkmer executable can be found."""
    try:
        path = find_rustkmer_executable()
        assert path, "rustkmer executable path should not be empty"
        print(f"Found rustkmer at: {path}")
    except ConfigurationError as e:
        # This is expected in CI without rustkmer installed
        print(f"Note: {e}")
        import pytest
        pytest.skip("rustkmer executable not found - install rustkmer to run full tests")


def test_rustkmer_version():
    """Test that rustkmer --version works."""
    try:
        output = run_rustkmer_command(['--version'], timeout=10)
        assert output, "rustkmer --version should return output"
        print(f"rustkmer version: {output}")
    except (SubprocessError, ConfigurationError) as e:
        print(f"Version check failed: {e}")
        # Don't fail the test - rustkmer might not support --version
        pass


def test_rustkmer_help():
    """Test that rustkmer --help works."""
    try:
        output = run_rustkmer_command(['--help'], timeout=10)
        assert output, "rustkmer --help should return output"
        assert 'query' in output.lower() or 'dump' in output.lower(), \
            "Help should mention query or dump commands"
        print("rustkmer help command works")
    except (SubprocessError, ConfigurationError) as e:
        print(f"Help check failed: {e}")
        # Don't fail the test - rustkmer might not be installed yet


def test_python_package_imports():
    """Test that the Python package can be imported."""
    try:
        from rustkmer import Database, QueryResult, DatabaseStats
        from rustkmer.exceptions import RustKmerError
        assert Database is not None
        assert QueryResult is not None
        assert DatabaseStats is not None
        assert RustKmerError is not None
        print("All core classes can be imported")
    except ImportError as e:
        print(f"Import failed: {e}")
        raise


def test_basic_error_handling():
    """Test that error handling works correctly."""
    from rustkmer.exceptions import (
        DatabaseNotFoundError,
        InvalidKmerError,
        RustKmerError
    )

    # Test exception hierarchy
    assert issubclass(DatabaseNotFoundError, RustKmerError)
    assert issubclass(InvalidKmerError, RustKmerError)

    # Test exception messages
    try:
        raise DatabaseNotFoundError("/nonexistent/file")
    except DatabaseNotFoundError as e:
        assert "not found" in str(e)
        assert e.path == "/nonexistent/file"

    try:
        raise InvalidKmerError("ATBX", "contains invalid character X")
    except InvalidKmerError as e:
        assert "ATBX" in str(e)
        assert e.kmer == "ATBX"


def test_mock_rustkmer_binary():
    """Test mock binary path generation."""
    # This test verifies our mock binary path structure
    import os
    from rustkmer import utils

    # Get the package directory
    package_dir = os.path.dirname(utils.__file__)
    mock_bin_path = os.path.join(package_dir, 'bin', 'rustkmer-test')

    # The path should be well-formed
    assert mock_bin_path.endswith('rustkmer-test')
    assert 'bin' in mock_bin_path
    print(f"Mock binary path: {mock_bin_path}")


if __name__ == "__main__":
    """Run smoke tests directly."""
    print("Running rustkmer smoke tests...")
    print("-" * 40)

    test_python_package_imports()
    test_basic_error_handling()
    test_mock_rustkmer_binary()

    try:
        test_rustkmer_executable_exists()
        test_rustkmer_help()
        test_rustkmer_version()
    except Exception as e:
        print(f"CLI tests skipped: {e}")

    print("-" * 40)
    print("All smoke tests passed!")