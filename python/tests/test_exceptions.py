"""Tests for exception classes."""

import pytest
from rustkmer.exceptions import (
    DatabaseError,
    DatabaseNotFoundError,
    InvalidDatabaseError,
    DatabaseCorruptedError,
    InvalidKmerError,
    KmerLengthError,
    QueryError,
    SubprocessError,
    ConfigurationError,
    RustKmerError
)


class TestDatabaseError:
    """Test DatabaseError base class."""

    def test_database_error_basic(self):
        """Test basic DatabaseError initialization."""
        error = DatabaseError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_database_error_inheritance(self):
        """Test DatabaseError inheritance."""
        error = DatabaseError("Test message")
        assert isinstance(error, Exception)
        assert isinstance(error, BaseException)


class TestDatabaseNotFoundError:
    """Test DatabaseNotFoundError class."""

    def test_database_not_found_error_default_message(self):
        """Test default error message."""
        error = DatabaseNotFoundError("/path/to/missing.rkdb")
        assert "/path/to/missing.rkdb" in str(error)
        assert "not found" in str(error).lower()

    def test_database_not_found_error_custom_message(self):
        """Test custom error message."""
        error = DatabaseNotFoundError("/path/to/missing.rkdb", "Custom message")
        assert str(error) == "Custom message"
        assert error.path == "/path/to/missing.rkdb"

    def test_database_not_found_error_inheritance(self):
        """Test DatabaseNotFoundError inheritance."""
        error = DatabaseNotFoundError("/path/to/missing.rkdb")
        assert isinstance(error, DatabaseError)
        assert isinstance(error, Exception)


class TestInvalidDatabaseError:
    """Test InvalidDatabaseError class."""

    def test_invalid_database_error_default_message(self):
        """Test default error message."""
        error = InvalidDatabaseError("/path/to/invalid.rkdb")
        assert "/path/to/invalid.rkdb" in str(error)
        assert "invalid" in str(error).lower()

    def test_invalid_database_error_with_reason(self):
        """Test error with specific reason."""
        error = InvalidDatabaseError("/path/to/invalid.rkdb", "File format not recognized")
        assert "/path/to/invalid.rkdb" in str(error)
        assert "File format not recognized" in str(error)

    def test_invalid_database_error_inheritance(self):
        """Test InvalidDatabaseError inheritance."""
        error = InvalidDatabaseError("/path/to/invalid.rkdb")
        assert isinstance(error, DatabaseError)
        assert isinstance(error, Exception)


class TestDatabaseCorruptedError:
    """Test DatabaseCorruptedError class."""

    def test_database_corrupted_error_default_message(self):
        """Test default error message."""
        error = DatabaseCorruptedError("/path/to/corrupted.rkdb")
        assert "/path/to/corrupted.rkdb" in str(error)
        assert "corrupted" in str(error).lower()

    def test_database_corrupted_error_with_details(self):
        """Test error with corruption details."""
        error = DatabaseCorruptedError(
            "/path/to/corrupted.rkdb",
            "Header checksum mismatch"
        )
        assert str(error) == "Header checksum mismatch"
        assert error.path == "/path/to/corrupted.rkdb"

    def test_database_corrupted_error_inheritance(self):
        """Test DatabaseCorruptedError inheritance."""
        error = DatabaseCorruptedError("/path/to/corrupted.rkdb")
        assert isinstance(error, DatabaseError)
        assert isinstance(error, Exception)


class TestInvalidKmerError:
    """Test InvalidKmerError class."""

    def test_invalid_kmer_error_default_message(self):
        """Test default error message."""
        error = InvalidKmerError("ATCGX")
        assert "ATCGX" in str(error)
        assert "invalid" in str(error).lower()

    def test_invalid_kmer_error_with_reason(self):
        """Test error with specific reason."""
        error = InvalidKmerError("ATCGX", "Contains invalid character 'X'")
        assert "ATCGX" in str(error)
        assert "Contains invalid character 'X'" in str(error)

    def test_invalid_kmer_error_inheritance(self):
        """Test InvalidKmerError inheritance."""
        error = InvalidKmerError("ATCGX")
        assert isinstance(error, ValueError)  # Check if it inherits from ValueError
        assert isinstance(error, Exception)

    def test_invalid_kmer_error_empty_string(self):
        """Test error with empty k-mer."""
        error = InvalidKmerError("")
        assert "" in str(error)

    def test_invalid_kmer_error_wrong_length(self):
        """Test error with wrong length."""
        error = InvalidKmerError("ATCG", "Wrong length: expected 7, got 4")
        assert "ATCG" in str(error)
        assert "Wrong length: expected 7, got 4" in str(error)


class TestQueryError:
    """Test QueryError class."""

    def test_query_error_basic(self):
        """Test basic QueryError initialization."""
        error = QueryError("Query failed")
        assert str(error) == "Query failed"
        assert isinstance(error, Exception)

    def test_query_error_inheritance(self):
        """Test QueryError inheritance."""
        error = QueryError("Query failed")
        assert isinstance(error, Exception)
        assert isinstance(error, BaseException)

    def test_query_error_with_context(self):
        """Test QueryError with additional context."""
        # QueryError doesn't accept keyword arguments, just use basic message
        error = QueryError("Query failed: kmer=ATCGATCG, database=/path/to/db.rkdb")
        assert "Query failed" in str(error)
        assert "ATCGATCG" in str(error)
        assert "/path/to/db.rkdb" in str(error)


class TestKmerLengthError:
    """Test KmerLengthError class."""

    def test_kmer_length_error(self):
        """Test KmerLengthError initialization."""
        error = KmerLengthError("ATCGATCG", expected=7, actual=8)
        assert "expected 7, got 8" in str(error)
        assert "ATCGATCG" in str(error)
        assert error.expected_length == 7
        assert error.actual_length == 8

    def test_kmer_length_error_inheritance(self):
        """Test KmerLengthError inheritance."""
        error = KmerLengthError("ATCGATCG", expected=7, actual=8)
        assert isinstance(error, InvalidKmerError)
        assert isinstance(error, QueryError)
        assert isinstance(error, ValueError)
        assert isinstance(error, Exception)


class TestSubprocessError:
    """Test SubprocessError class."""

    def test_subprocess_error_basic(self):
        """Test SubprocessError initialization."""
        error = SubprocessError("rustkmer query", returncode=1)
        assert "rustkmer query" in str(error)
        assert "code 1" in str(error)
        assert error.command == "rustkmer query"
        assert error.returncode == 1
        assert error.stderr is None

    def test_subprocess_error_with_stderr(self):
        """Test SubprocessError with stderr."""
        stderr_msg = "Database not found"
        error = SubprocessError(
            "rustkmer query",
            returncode=1,
            stderr=stderr_msg
        )
        assert "rustkmer query" in str(error)
        assert "code 1" in str(error)
        assert stderr_msg in str(error)
        assert error.stderr == stderr_msg

    def test_subprocess_error_inheritance(self):
        """Test SubprocessError inheritance."""
        error = SubprocessError("rustkmer query", returncode=1)
        assert isinstance(error, RustKmerError)
        assert isinstance(error, Exception)


class TestConfigurationError:
    """Test ConfigurationError class."""

    def test_configuration_error(self):
        """Test ConfigurationError initialization."""
        error = ConfigurationError("Invalid configuration")
        assert str(error) == "Configuration error: Invalid configuration"
        assert isinstance(error, Exception)

    def test_configuration_error_inheritance(self):
        """Test ConfigurationError inheritance."""
        error = ConfigurationError("Invalid configuration")
        assert isinstance(error, RustKmerError)
        assert isinstance(error, Exception)
        assert isinstance(error, BaseException)


class TestExceptionHierarchy:
    """Test exception hierarchy and relationships."""

    def test_all_database_errors_inherit_from_database_error(self):
        """Test that all database-specific errors inherit from DatabaseError."""
        db_path = "/path/to/test.rkdb"

        not_found = DatabaseNotFoundError(db_path)
        invalid = InvalidDatabaseError(db_path)
        corrupted = DatabaseCorruptedError(db_path)

        assert isinstance(not_found, DatabaseError)
        assert isinstance(invalid, DatabaseError)
        assert isinstance(corrupted, DatabaseError)

    def test_exception_catching_hierarchy(self):
        """Test that catching DatabaseError catches specific database errors."""
        db_path = "/path/to/test.rkdb"
        errors = [
            DatabaseNotFoundError(db_path),
            InvalidDatabaseError(db_path),
            DatabaseCorruptedError(db_path)
        ]

        for error in errors:
            # Should be caught by DatabaseError
            caught = False
            try:
                raise error
            except DatabaseError:
                caught = True

            assert caught, f"{type(error).__name__} should be caught by DatabaseError"

    def test_exception_str_repr_consistency(self):
        """Test that __str__ and __repr__ provide useful information."""
        errors = [
            DatabaseNotFoundError("/path/to/file.rkdb"),
            InvalidDatabaseError("/path/to/file.rkdb", "Bad format"),
            DatabaseCorruptedError("/path/to/file.rkdb", "Checksum error"),
            InvalidKmerError("ATCGX", "Invalid char"),
            QueryError("Query timeout"),
            ConfigurationError("Bad config")
        ]

        for error in errors:
            str_repr = str(error)
            repr_repr = repr(error)

            # String should contain meaningful information
            assert len(str_repr) > 0
            assert repr_repr.startswith(f"<{type(error).__name__}") or str_repr in repr_repr

            # Should not raise when converting to string
            assert str(error) is not None