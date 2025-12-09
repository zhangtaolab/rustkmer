"""
Configuration for RustKmer CLI-Python API compatibility tests.

This module contains configuration settings and constants used throughout
the compatibility testing framework.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class TestConfig:
    """Configuration for compatibility tests"""

    # Test data paths
    test_data_base: str = "/Users/forrest/Temp/demodata"

    # Performance thresholds
    performance_time_threshold: float = 1.10  # Python API can be up to 110% of CLI time
    performance_memory_threshold: float = 1.05  # Python API can be up to 105% of CLI memory

    # Test execution settings
    default_kmer_sizes: List[int] = field(default_factory=lambda: [21, 31, 51])
    performance_runs: int = 5
    timeout_seconds: int = 300  # 5 minutes per test

    # File size categories (in bytes)
    small_file_max: int = 1_000_000  # 1MB
    medium_file_max: int = 100_000_000  # 100MB

    # Test data categories
    test_categories: List[str] = field(default_factory=lambda: ["small", "medium", "large"])

    # CLI settings
    cli_path: Optional[str] = None  # Will auto-detect if None
    cli_timeout: int = 600  # 10 minutes for CLI commands

    # Output settings
    verbose: bool = False
    save_intermediate_results: bool = True
    generate_html_reports: bool = True
    generate_json_reports: bool = True

    # Parallel execution
    max_parallel_tests: int = 4

    # Error handling
    continue_on_test_failure: bool = True
    max_retry_attempts: int = 3


class TestCategories:
    """Test data size categories"""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

    @staticmethod
    def categorize_file_size(file_size: int) -> str:
        """
        Categorize a file based on its size.

        Args:
            file_size: File size in bytes

        Returns:
            Category string (small, medium, or large)
        """
        if file_size < TestConfig.small_file_max:
            return TestCategories.SMALL
        elif file_size < TestConfig.medium_file_max:
            return TestCategories.MEDIUM
        else:
            return TestCategories.LARGE


class DefaultSequences:
    """Default test sequences for queries"""

    # Standard test k-mers (31-mers)
    TEST_SEQUENCES_31 = [
        "ATCGATCGATCGATCGATCGATCGATCGATCGAT",
        "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT",
        "TTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT",
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAACG",
        "CGATCGATCGATCGATCGATCGATCGATCGATCGA"
    ]

    # Shorter test k-mers (21-mers)
    TEST_SEQUENCES_21 = [
        "ATCGATCGATCGATCGATCGATC",
        "GCTAGCTAGCTAGCTAGCTAGCT",
        "TTTTTTTTTTTTTTTTTTTTT",
        "AAAAAAAAAAAAAAAAAAACG"
    ]

    # Very short test k-mers (7-mers)
    TEST_SEQUENCES_7 = [
        "ATCGATCG",
        "GCTAGCT",
        "TTTTTTT",
        "AAAAACG"
    ]


class ErrorMappings:
    """Mappings between Python exceptions and CLI error messages"""

    PYTHON_TO_CLI_ERRORS = {
        'FileNotFoundError': ['No such file', 'not found', 'does not exist'],
        'ValueError': ['Invalid', 'malformed', 'incorrect'],
        'RuntimeError': ['Error', 'failed', 'cannot'],
        'IOError': ['Input/output error', 'permission denied', 'access denied'],
        'MemoryError': ['out of memory', 'memory'],
        'TimeoutError': ['timeout', 'timed out']
    }

    @staticmethod
    def cli_error_matches_python(python_error: str, cli_error: str) -> bool:
        """
        Check if a CLI error message matches a Python error type.

        Args:
            python_error: Python exception type
            cli_error: CLI error message

        Returns:
            True if the errors are considered equivalent
        """
        if python_error not in ErrorMappings.PYTHON_TO_CLI_ERRORS:
            return False

        cli_keywords = ErrorMappings.PYTHON_TO_CLI_ERRORS[python_error]
        cli_error_lower = cli_error.lower()

        return any(keyword.lower() in cli_error_lower for keyword in cli_keywords)


class ReportTemplates:
    """Templates for generating test reports"""

    HTML_TEMPLATE_HEADER = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>RustKmer CLI-Python API Compatibility Report</title>
        <meta charset="utf-8">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 40px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .header {
                text-align: center;
                border-bottom: 2px solid #007bff;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }
            .summary {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .metric {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                text-align: center;
            }
            .metric h3 {
                margin: 0;
                font-size: 24px;
                color: #007bff;
            }
            .metric p {
                margin: 5px 0 0 0;
                color: #666;
            }
            .pass { background-color: #d4edda; }
            .fail { background-color: #f8d7da; }
            .warning { background-color: #fff3cd; }
            .chart-container {
                width: 100%;
                height: 400px;
                margin: 20px 0;
            }
            .test-details {
                margin-top: 30px;
            }
            .test-item {
                border: 1px solid #ddd;
                margin: 10px 0;
                padding: 15px;
                border-radius: 5px;
            }
            .test-name {
                font-weight: bold;
                margin-bottom: 10px;
            }
            .test-result {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .performance-bar {
                width: 200px;
                height: 20px;
                background-color: #e9ecef;
                border-radius: 10px;
                overflow: hidden;
                position: relative;
            }
            .performance-fill {
                height: 100%;
                background-color: #28a745;
                transition: width 0.3s ease;
            }
            .performance-text {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 12px;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>RustKmer CLI-Python API Compatibility Report</h1>
                <p>Generated on: {timestamp}</p>
            </div>
    """

    HTML_TEMPLATE_FOOTER = """
        </div>
    </body>
    </html>
    """


# Global configuration instance
default_config = TestConfig()


def get_config(**kwargs) -> TestConfig:
    """
    Get a test configuration with optional overrides.

    Args:
        **kwargs: Configuration overrides

    Returns:
        TestConfig instance
    """
    config = TestConfig()

    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)

    return config


def get_env_config() -> TestConfig:
    """
    Get configuration from environment variables.

    Returns:
        TestConfig instance with values from environment
    """
    config = TestConfig()

    # Override with environment variables if present
    if 'RUSTKMER_TEST_DATA_BASE' in os.environ:
        config.test_data_base = os.environ['RUSTKMER_TEST_DATA_BASE']

    if 'RUSTKMER_CLI_PATH' in os.environ:
        config.cli_path = os.environ['RUSTKMER_CLI_PATH']

    if 'RUSTKMER_VERBOSE' in os.environ:
        config.verbose = os.environ['RUSTKMER_VERBOSE'].lower() in ['true', '1', 'yes']

    if 'RUSTKMER_PERFORMANCE_RUNS' in os.environ:
        config.performance_runs = int(os.environ['RUSTKMER_PERFORMANCE_RUNS'])

    if 'RUSTKMER_TIMEOUT' in os.environ:
        config.timeout_seconds = int(os.environ['RUSTKMER_TIMEOUT'])

    return config