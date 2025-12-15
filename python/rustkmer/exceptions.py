"""Exception hierarchy for rustkmer Python bindings.

This module defines all custom exceptions used by the rustkmer package
to provide clear, actionable error messages for different failure scenarios.
"""

from typing import Optional


class RustKmerError(Exception):
    """Base exception for all rustkmer errors.

    All rustkmer-specific exceptions inherit from this class, allowing
    users to catch all rustkmer errors with a single except clause. This
    provides a clean way to handle any rustkmer-related issues while still
    allowing fine-grained error handling with specific exception types.

    Example:
        >>> try:
        ...     db = Database("nonexistent.rkdb")
        ... except RustKmerError as e:
        ...     print(f"rustkmer error occurred: {e}")

    Note:
        This is the root of the rustkmer exception hierarchy. All other
        rustkmer exceptions inherit from either this class or one of its
        direct subclasses (DatabaseError, QueryError, etc.).

    See Also:
        DatabaseError: For database-related errors
        QueryError: For query-related errors
        SubprocessError: For CLI subprocess failures
    """
    pass


class DatabaseError(RustKmerError):
    """Base class for all database-related errors.

    This exception and its subclasses handle issues related to database file
    operations, including file not found errors, invalid database formats,
    and corrupted database files. Catching this exception will handle all
    database-related issues while allowing specific handling with more
    specific subclasses.

    Example:
        >>> try:
        ...     db = Database("invalid.rkdb", validate=True)
        ... except DatabaseError as e:
        ...     print(f"Database error: {e}")

    Note:
        This exception does not include query-related errors, which are
        handled by the QueryError hierarchy.

    See Also:
        DatabaseNotFoundError: When database file doesn't exist
        InvalidDatabaseError: When file is not a valid database
        DatabaseCorruptedError: When database file is corrupted
    """
    pass


class DatabaseNotFoundError(DatabaseError, FileNotFoundError):
    """Raised when a database file cannot be found at the specified path.

    This exception occurs when attempting to open or access a rustkmer
    database file that doesn't exist at the specified path. It inherits
    from both DatabaseError and FileNotFoundError to provide compatibility
    with standard file error handling patterns.

    Attributes:
        path: The path that was attempted to be accessed

    Args:
        path: The path to the database file that was not found
        message: Custom error message. If None, a default message is generated

    Example:
        >>> try:
        ...     db = Database("/nonexistent/path/database.rkdb")
        ... except DatabaseNotFoundError as e:
        ...     print(f"Database not found at: {e.path}")
        ...     print(f"Error: {e}")

    Note:
        This exception is commonly encountered when:
        - Database file path is incorrect
        - Database file was deleted or moved
        - File permissions prevent access
        - Working directory is not what was expected

    See Also:
        InvalidDatabaseError: When file exists but is not a valid database
        DatabaseError: Base class for all database-related errors
    """

    def __init__(self, path: str, message: Optional[str] = None):
        if message is None:
            message = f"Database file not found: {path}"
        super().__init__(message)
        self.path = path


class InvalidDatabaseError(DatabaseError):
    """Raised when a file is not a valid rustkmer database.

    This exception occurs when a file exists at the specified path but
    cannot be recognized as a valid rustkmer database. This typically
    happens when trying to open a file that's not in the .rkdb format
    or when the file format is corrupted in a way that makes it
    unrecognizable.

    Attributes:
        path: The path to the invalid database file
        reason: Description of why the file is considered invalid

    Args:
        path: The path to the file that is not a valid database
        reason: Custom reason for the invalidity. If None, a default
                message is provided.

    Example:
        >>> try:
        ...     db = Database("/path/to/wrong_format.txt", validate=True)
        ... except InvalidDatabaseError as e:
        ...     print(f"Invalid database: {e.reason}")
        ...     print(f"File path: {e.path}")

    Note:
        This exception is commonly encountered when:
        - Trying to open a file that's not in .rkdb format
        - Database file was created with incompatible version
        - File header is corrupted or missing
        - File is a different type (e.g., plain text, binary data)

    See Also:
        DatabaseNotFoundError: When database file doesn't exist
        DatabaseCorruptedError: When database file exists but is corrupted
    """

    def __init__(self, path: str, reason: Optional[str] = None):
        if reason is None:
            reason = "File is not a valid rustkmer database"
        message = f"Invalid database '{path}': {reason}"
        super().__init__(message)
        self.path = path
        self.reason = reason


class DatabaseCorruptedError(DatabaseError):
    """Raised when a database file appears to be corrupted or unreadable.

    This exception occurs when a database file exists and appears to be
    in the correct format, but contains structural damage or corruption
    that makes it impossible to read properly. This is different from
    InvalidDatabaseError in that the file is recognized as a database
    but cannot be successfully parsed or used.

    Attributes:
        path: The path to the corrupted database file

    Args:
        path: The path to the corrupted database file
        message: Custom error message. If None, a default message is generated

    Example:
        >>> try:
        ...     db = Database("/path/to/corrupted.rkdb")
        ... except DatabaseCorruptedError as e:
        ...     print(f"Database corrupted: {e.path}")
        ...     # Try to recover or use backup
        ...     pass

    Note:
        This exception is commonly encountered when:
        - Database file was partially written and then interrupted
        - Storage media corruption occurred
        - File was modified by incompatible software
        - Database format version mismatch causing parsing errors

    See Also:
        InvalidDatabaseError: When file is not a valid database format
        DatabaseError: Base class for all database-related errors
    """

    def __init__(self, path: str, message: Optional[str] = None):
        if message is None:
            message = f"Database file appears to be corrupted: {path}"
        super().__init__(message)
        self.path = path


class QueryError(RustKmerError):
    """Base class for all query-related errors.

    This exception and its subclasses handle issues related to database
    query operations, including invalid k-mers, fuzzy query problems,
    batch processing issues, and other query-related failures. Catching
    this exception will handle all query-related issues while allowing
    specific handling with more targeted subclasses.

    Example:
        >>> try:
        ...     result = db.query("INVALID")
        ... except QueryError as e:
        ...     print(f"Query failed: {e}")

    Note:
        This exception does not include database file errors, which are
        handled by the DatabaseError hierarchy.

    See Also:
        InvalidKmerError: For invalid k-mer sequences
        FuzzyQueryError: For fuzzy query-related errors
        BatchQueryError: For batch query processing errors
    """
    pass


class InvalidKmerError(QueryError, ValueError):
    """Raised when an invalid k-mer sequence is provided.

    This exception occurs when attempting to query with a k-mer that
    contains invalid characters, has incorrect length, or otherwise
    doesn't meet the requirements for the database being queried.

    Attributes:
        kmer: The invalid k-mer sequence that caused the error
        reason: Description of why the k-mer is invalid

    Args:
        kmer: The invalid k-mer sequence
        reason: Custom reason for the invalidity. If None, a default
                message is provided.

    Example:
        >>> try:
        ...     result = db.query("ATXG")  # Invalid character X
        ... except InvalidKmerError as e:
        ...     print(f"Invalid k-mer: {e.kmer}")
        ...     print(f"Reason: {e.reason}")

    Note:
        Valid k-mer sequences must:
        - Only contain characters A, T, C, G, N (uppercase)
        - Have the correct length for the database
        - Not be empty strings

    See Also:
        KmerLengthError: When k-mer length is incorrect
        QueryError: Base class for all query-related errors
    """

    def __init__(self, kmer: str, reason: Optional[str] = None):
        if reason is None:
            reason = "contains invalid characters or has incorrect length"
        message = f"Invalid k-mer '{kmer}': {reason}"
        super().__init__(message)
        self.kmer = kmer
        self.reason = reason


class KmerLengthError(InvalidKmerError):
    """Raised when k-mer length doesn't match database k-mer size.

    This exception provides specific information about length mismatches
    between the provided k-mer and the expected k-mer size for the
    database being queried. It's a more specific version of InvalidKmerError
    that helps users identify and fix length-related issues quickly.

    Attributes:
        expected_length: The correct k-mer length for the database
        actual_length: The length of the provided k-mer

    Args:
        kmer: The k-mer with incorrect length
        expected: The expected k-mer length
        actual: The actual length of the provided k-mer

    Example:
        >>> try:
        ...     result = db.query("ATCG")  # Too short for k=31 database
        ... except KmerLengthError as e:
        ...     print(f"Expected length: {e.expected_length}")
        ...     print(f"Actual length: {e.actual_length}")
        ...     print(f"Invalid k-mer: {e.kmer}")

    Note:
        This error commonly occurs when:
        - Using k-mers from a different k-mer size database
        - Truncating k-mers accidentally
        - Using k-mers from external sources with different settings
        - Testing with short example k-mers on real databases

    See Also:
        InvalidKmerError: Base class for all invalid k-mer errors
        DatabaseStats.kmer_size: Check expected k-mer size for a database
    """

    def __init__(self, kmer: str, expected: int, actual: int):
        message = (
            f"K-mer length mismatch: expected {expected}, got {actual} "
            f"for k-mer '{kmer}'"
        )
        super().__init__(kmer, message)
        self.expected_length = expected
        self.actual_length = actual


class FuzzyQueryError(QueryError):
    """Base exception for fuzzy query operations.

    This exception and its subclasses handle issues specifically related to
    fuzzy query operations, including mutation tolerance errors, position
    mutation configuration problems, and batch processing issues. These
    errors occur when performing approximate k-mer matching with
    mutation allowances.

    Example:
        >>> try:
        ...     result = db.fuzzy_query("ATCG", mutations=10)  # Too high
        ... except FuzzyQueryError as e:
        ...     print(f"Fuzzy query error: {e}")

    Note:
        Fuzzy queries allow finding k-mers within a specified Hamming
        distance, but have additional constraints compared to exact queries.

    See Also:
        InvalidMutationToleranceError: For mutation tolerance issues
        InvalidPositionMutationError: For position mutation errors
        BatchQueryError: For batch query processing errors
    """
    pass


class InvalidMutationToleranceError(FuzzyQueryError):
    """Raised when mutation tolerance is out of valid range.

    This exception occurs when the mutation tolerance parameter for a
    fuzzy query is outside the supported range. Mutation tolerance
    controls the maximum Hamming distance allowed between the query
    k-mer and potential matches.

    Note:
        Valid mutation tolerance values are typically 0-5, but the
        exact range may depend on the database and implementation.

    Example:
        >>> try:
        ...     result = db.fuzzy_query("ATCG", mutations=10)  # Too high
        ... except InvalidMutationToleranceError as e:
        ...     print("Mutation tolerance too high")
        ...     print("Use a smaller value (0-5)")

    See Also:
        FuzzyQueryError: Base class for fuzzy query errors
    """
    pass


class InvalidPositionMutationError(FuzzyQueryError):
    """Raised when position-mutations parameter has invalid format or values.

    This exception occurs when the position-mutations parameter for a
    fuzzy query has invalid syntax, out-of-bounds positions, or logical
    inconsistencies. Position mutations allow constraining mutations
    to specific k-mer positions.

    Attributes:
        position_config: The invalid position mutation configuration string

    Args:
        message: Error message describing the validation failure
        position_config: The invalid position mutation configuration

    Example:
        >>> try:
        ...     result = db.fuzzy_query("ATCG", position_mutations="invalid")
        ... except InvalidPositionMutationError as e:
        ...     print(f"Invalid format: {e.position_config}")
        ...     print("Use format like '3,4:1' or '2-5:2'")

    Note:
        Valid position-mutations formats:
        - "3:1" - Position 3 with max 1 mutation
        - "3,4,5:2" - Positions 3,4,5 with max 2 mutations total
        - "4-7:1" - Positions 4,5,6,7 with max 1 mutation
        - "3,4:1;6,7:2" - Multiple independent groups

    See Also:
        FuzzyQueryError: Base class for fuzzy query errors
    """

    def __init__(self, message: str, position_config: Optional[str] = None):
        super().__init__(message)
        self.position_config = position_config


class CombinatorialExplosionError(FuzzyQueryError):
    """Raised when fuzzy query would generate too many variants.

    This exception occurs when a fuzzy query with high mutation tolerance
    would generate an impractically large number of k-mer variants, potentially
    causing excessive memory usage or computation time.

    Example:
        >>> try:
        ...     result = db.fuzzy_query("ATCGATCGATCG", mutations=5)
        ... except CombinatorialExplosionError as e:
        ...     print("Too many variants would be generated")
        ...     # Try reducing mutations or using max_variants parameter
        ...     result = db.fuzzy_query("ATCGATCGATCG", mutations=3, max_variants=1000)

    Note:
        The number of possible variants grows combinatorially with
        mutation tolerance: k^d * 3^d where k is k-mer length and d is distance.

    See Also:
        FuzzyQueryError: Base class for fuzzy query errors
    """
    pass


class BatchQueryError(FuzzyQueryError):
    """Raised when batch fuzzy query encounters issues.

    This exception occurs when processing multiple fuzzy queries in a
    batch operation encounters problems, such as individual query failures
    or resource constraints.

    Example:
        >>> try:
        ...     results = db.fuzzy_query_batch(["ATCG", "GCTA", "INVALID"])
        ... except BatchQueryError as e:
        ...     print("Batch query failed")
        ...     # Process queries individually to identify the problem
        ...     for kmer in ["ATCG", "GCTA", "INVALID"]:
        ...         try:
        ...             result = db.fuzzy_query(kmer)
        ...         except FuzzyQueryError as query_error:
        ...             print(f"Query {kmer} failed: {query_error}")

    Note:
        Batch queries can fail due to individual query failures or
        system resource limitations during bulk processing.

    See Also:
        FuzzyQueryError: Base class for fuzzy query errors
    """
    pass


class SubprocessError(RustKmerError):
    """Raised when subprocess calls to rustkmer CLI fail.

    This exception occurs when the rustkmer Python API attempts to execute
    the underlying rustkmer CLI command and the subprocess fails. This can
    happen due to missing executable, permission issues, or CLI errors.

    Attributes:
        command: The full command that was attempted
        returncode: The exit code returned by the subprocess
        stderr: Standard error output from the failed command

    Args:
        command: The full command that was attempted
        returncode: The exit code returned by the subprocess
        stderr: Standard error output from the failed command

    Example:
        >>> try:
        ...     result = db.query("ATCG")  # This calls rustkmer CLI internally
        ... except SubprocessError as e:
        ...     print(f"Command failed: {e.command}")
        ...     print(f"Exit code: {e.returncode}")
        ...     if e.stderr:
        ...         print(f"Error output: {e.stderr}")

    Note:
        This exception typically indicates system-level issues:
        - rustkmer executable not found
        - Incorrect installation
        - Permission problems
        - Version incompatibilities

    See Also:
        ConfigurationError: For rustkmer package configuration issues
        RustKmerError: Base class for all rustkmer errors
    """

    def __init__(self, command: str, returncode: int, stderr: Optional[str] = None):
        message = f"rustkmer command failed with code {returncode}: {command}"
        if stderr:
            message += f"\nStderr: {stderr}"
        super().__init__(message)
        self.command = command
        self.returncode = returncode
        self.stderr = stderr


class ConfigurationError(RustKmerError):
    """Raised when there's a configuration issue with the rustkmer package.

    This exception occurs when the rustkmer package configuration is incorrect
    or when required environment setup is missing. This is distinct from
    database-related or query-related errors.

    Args:
        message: Description of the configuration issue

    Example:
        >>> try:
        ...     db = Database("database.rkdb")  # May trigger config validation
        ... except ConfigurationError as e:
        ...     print(f"Configuration issue: {e}")
        ...     print("Check rustkmer installation and environment")

    Note:
        Configuration issues may include:
        - Missing or incorrect RUSTKMER_PATH environment variable
        - Invalid Python package installation
        - Missing required system dependencies

    See Also:
        SubprocessError: For CLI execution issues
        RustKmerError: Base class for all rustkmer errors
    """

    def __init__(self, message: str):
        super().__init__(f"Configuration error: {message}")