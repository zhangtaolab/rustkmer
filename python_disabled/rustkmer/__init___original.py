"""
RustKmer Python Bindings

High-performance k-mer counting, database queries, and fuzzy search
for genomic data analysis.
"""

__version__ = "0.1.0"

# Import from Rust extension first, fall back to Python placeholders
try:
    # Try to import from the Rust extension
    from ._rustkmer import (
        KmerCounter,
        SimpleDatabase,  # Raw Rust implementation
        FuzzyQuery,
        QueryResult,
        FuzzyQueryResult,
        FuzzyMatch,
        DatabaseStats,
        CounterStats
    )

    # Import Pythonic wrapper for Database
    from .database import Database

    # Set other imports that might not be available yet
    set_verbosity = None
    get_version = None

    # Import exceptions from our exceptions module
    from .exceptions import (
        RustKmerError,
        SequenceError,
        DatabaseError,
        DatabaseCorruptionError,
        FileNotFoundError,
        PermissionError,
        ValueError,
        KmerSizeError,
        ThreadCountError,
        MemoryError,
        EncodingError,
        QueryError,
        FuzzyQueryError,
        MergeError,
        ExportError,
        CompressionError,
        ProgressCallbackError,
        ThreadSafetyError,
        translate_rust_error
    )

    # Legacy aliases for backward compatibility
    KmerError = EncodingError
    ConfigurationError = ValueError
    ValidationError = ValueError

    # Import export functionality from Python module (has Rust integration)
    from .export import (
        OutputFormat,
        ExportConfig,
        ExportStats,
        DatabaseExporter,
        dump_database,
        export_to_json,
        export_to_csv,
        export_to_tsv
    )

    # Import stub classes for missing functionality
    from .stubs import (
        FuzzyQueryEngine,
        FuzzyResult,
        FuzzyQueryConfig,
        DatabaseMerger,
        MergeConfig,
        MergeResult,
        MergeProgressCallback,
        FilterConfig
    )

    # Import metadata functionality
    from .metadata import (
        DatabaseMetadata,
        extract_metadata,
        get_file_age_category
    )

    # Import thread safety utilities
    from .thread_safety import (
        ThreadSafeDatabase,
        make_thread_safe,
        with_thread_safe,
        ConnectionPool,
        ThreadSafeCache,
        thread_safe
    )

    # Import error handling utilities
    from .error_handling import (
        ErrorContext,
        ErrorManager,
        ErrorHandler,
        RetryStrategy,
        FallbackStrategy,
        safe_execute,
        validate_file_path,
        validate_kmer_sequence,
        validate_one_of,
        validate_non_negative_int
    )

    # Try to import optional utilities
    try:
        from ._rustkmer import set_verbosity, get_version
    except ImportError:
        pass

    try:
        from ._rustkmer import (
            get_log_level, log_message, is_log_enabled, get_system_info,
            enable_debug_mode, enable_trace_mode, flush_logs
        )
    except ImportError:
        # Create no-op versions
        def get_log_level(): return "INFO"
        def log_message(level, msg): pass
        def is_log_enabled(): return False
        def get_system_info(): return {}
        def enable_debug_mode(): pass
        def enable_trace_mode(): pass
        def flush_logs(): pass

    try:
        from ._rustkmer import get_resource_stats, cleanup_resources
    except ImportError:
        # Create no-op versions
        def get_resource_stats(): return {}
        def cleanup_resources(): pass

    try:
        from ._rustkmer import PerformanceTimer
    except ImportError:
        # Use Python version from utils
        from .utils import PerformanceTimer

    # Re-export classes
    __all__ = [
        'KmerCounter',
        'Database',
        'FuzzyQuery',
        'QueryResult',
        'FuzzyQueryResult',
        'FuzzyMatch',
        'DatabaseStats',
        'CounterStats',
        'set_verbosity',
        'get_version',
        'RustKmerError',
        'SequenceError',
        'DatabaseError',
        'DatabaseCorruptionError',
        'FileNotFoundError',
        'PermissionError',
        'ValueError',
        'KmerSizeError',
        'ThreadCountError',
        'MemoryError',
        'EncodingError',
        'QueryError',
        'FuzzyQueryError',
        'MergeError',
        'ExportError',
        'CompressionError',
        'ProgressCallbackError',
        'ThreadSafetyError',
        'translate_rust_error',
        # Legacy aliases
        'KmerError',
        'ConfigurationError',
        'ValidationError',
        # Logging and debugging utilities
        'get_log_level',
        'log_message',
        'is_log_enabled',
        'get_system_info',
        'enable_debug_mode',
        'enable_trace_mode',
        'flush_logs',
        # Memory management utilities
        'get_resource_stats',
        'cleanup_resources',
        # Performance utilities
        'PerformanceTimer',
        # Export functionality
        'OutputFormat',
        'ExportConfig',
        'ExportStats',
        'DatabaseExporter',
        'dump_database',
        'export_to_json',
        'export_to_csv',
        'export_to_tsv',
        # Metadata functionality
        'DatabaseMetadata',
        'extract_metadata',
        'get_file_age_category',
        # Thread safety utilities
        'ThreadSafeDatabase',
        'make_thread_safe',
        'with_thread_safe',
        'ConnectionPool',
        'ThreadSafeCache',
        'thread_safe',
        # Error handling utilities
        'ErrorContext',
        'ErrorManager',
        'ErrorHandler',
        'RetryStrategy',
        'FallbackStrategy',
        'safe_execute',
        'validate_file_path',
        'validate_kmer_sequence',
        'validate_one_of',
        'validate_non_negative_int',
        # Stub classes for missing functionality
        'FuzzyQueryEngine',
        'FuzzyResult',
        'FuzzyQueryConfig',
        'DatabaseMerger',
        'MergeConfig',
        'MergeResult',
        'MergeProgressCallback',
        'FilterConfig'
    ]

except ImportError:
    # Rust extension not available, import Python placeholders
    try:
        from .core import KmerCounter
        from .database import Database
        from .fuzzy import FuzzyQuery
        from .sequence import Sequence
        from .stats import QueryResult, FuzzyQueryResult, CounterStats, DatabaseStats
        from .exceptions import KmerError, DatabaseError, FuzzyQueryError, SequenceError
        from .merge import (
            MergeConfig,
            MergeStats,
            CompatibilityError,
            MergeError,
            check_compatibility,
            merge_databases,
            merge_files,
            quick_merge
        )
        from .export import (
            OutputFormat,
            ExportConfig,
            ExportStats,
            DatabaseExporter,
            dump_database,
            export_to_json,
            export_to_csv,
            export_to_tsv
        )
        from .metadata import (
            DatabaseMetadata,
            extract_metadata,
            get_file_age_category
        )
        from .stubs import (
            FuzzyQueryEngine,
            FuzzyResult,
            FuzzyQueryConfig,
            DatabaseMerger,
            MergeConfig,
            MergeResult,
            MergeProgressCallback,
            FilterConfig
        )

        __all__ = [
            'KmerCounter',
            'Database',
            'FuzzyQuery',
            'Sequence',
            'QueryResult',
            'FuzzyQueryResult',
            'CounterStats',
            'DatabaseStats',
            'KmerError',
            'DatabaseError',
            'FuzzyQueryError',
            'SequenceError',
            # Merge functionality
            'MergeConfig',
            'MergeStats',
            'CompatibilityError',
            'MergeError',
            'check_compatibility',
            'merge_databases',
            'merge_files',
            'quick_merge',
            # Export functionality
            'OutputFormat',
            'ExportConfig',
            'ExportStats',
            'DatabaseExporter',
            'dump_database',
            'export_to_json',
            'export_to_csv',
            'export_to_tsv',
            # Metadata functionality
            'DatabaseMetadata',
            'extract_metadata',
            'get_file_age_category',
            # Stub classes for missing functionality
            'FuzzyQueryEngine',
            'FuzzyResult',
            'FuzzyQueryConfig',
            'DatabaseMerger',
            'MergeResult',
            'MergeProgressCallback',
            'FilterConfig'
        ]

    except ImportError:
        # No implementation available
        __all__ = []