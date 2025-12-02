"""
Test Fixtures Package for Python API Validation
===============================================

This package provides comprehensive test data generators and validation utilities
for testing the RustKmer Python API improvements.

Modules:
- test_data_generators: Generate k-mers, fuzzy queries, and large-scale test data
- validation_utils: Performance profiling and test result analysis utilities
"""

from .test_data_generators import (
    KmerDataGenerator,
    FuzzyQueryDataGenerator,
    LargeScaleDataGenerator,
    ErrorCaseGenerator,
    TestDataSuite
)

from .validation_utils import (
    PerformanceMetrics,
    ValidationTestCase,
    PerformanceProfiler,
    DataValidator,
    TestResultAnalyzer,
    ValidationTestRunner,
    create_test_database_path,
    validate_file_creation,
    measure_memory_usage
)

__all__ = [
    # Data generators
    'KmerDataGenerator',
    'FuzzyQueryDataGenerator',
    'LargeScaleDataGenerator',
    'ErrorCaseGenerator',
    'TestDataSuite',

    # Validation utilities
    'PerformanceMetrics',
    'ValidationTestCase',
    'PerformanceProfiler',
    'DataValidator',
    'TestResultAnalyzer',
    'ValidationTestRunner',
    'create_test_database_path',
    'validate_file_creation',
    'measure_memory_usage',
]

__version__ = "1.0.0"