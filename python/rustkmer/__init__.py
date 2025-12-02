"""
RustKmer Python Bindings

High-performance k-mer counting, database queries, and fuzzy search
for genomic data analysis.
"""

__version__ = "0.1.0"

# Import from Rust extension first, fall back to Python placeholders
try:
    # Try to import from the Rust extension
    from ._rustkmer import KmerCounter, Database, FuzzyQuery
    from ._rustkmer import QueryResult, FuzzyQueryResult, DatabaseStats  # Stats classes from Rust
    from ._rustkmer import set_verbosity, get_version
    from ._rustkmer import (
        RustKmerError, KmerError, DatabaseError, FuzzyQueryError,
        SequenceError, ConfigurationError, ValidationError
    )
    # Import logging and debugging utilities
    from ._rustkmer import (
        get_log_level, log_message, is_log_enabled, get_system_info,
        enable_debug_mode, enable_trace_mode, flush_logs
    )
    # Import memory management utilities
    from ._rustkmer import get_resource_stats, cleanup_resources
    # Import performance timer
    from ._rustkmer import PerformanceTimer

    # Re-export Rust classes
    __all__ = [
        'KmerCounter',
        'Database',
        'FuzzyQuery',
        'QueryResult',
        'FuzzyQueryResult',
        'DatabaseStats',
        'set_verbosity',
        'get_version',
        'RustKmerError',
        'KmerError',
        'DatabaseError',
        'FuzzyQueryError',
        'SequenceError',
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
        'PerformanceTimer'
    ]

except ImportError:
    # Rust extension not available, import Python placeholders
    try:
        from .core import KmerCounter, Database
        from .fuzzy import FuzzyQuery
        from .sequence import Sequence
        from .stats import QueryResult, FuzzyQueryResult, CounterStats, DatabaseStats
        from .exceptions import KmerError, DatabaseError, FuzzyQueryError, SequenceError

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
        ]

    except ImportError:
        # No implementation available
        __all__ = []