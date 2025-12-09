"""
Data models for RustKmer CLI-Python API compatibility testing.

This module defines the core data structures used throughout the compatibility
testing framework.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union


@dataclass
class TestExecution:
    """Result of a single compatibility test execution."""

    execution_id: str
    test_name: str
    python_class: str
    python_method: str
    cli_command: str
    test_parameters: Dict[str, Any]
    test_data_path: Optional[str]
    python_output: Any
    cli_output: Any
    is_identical: bool
    difference_details: Optional[Dict[str, Any]]
    performance_metrics: Optional['PerformanceMetrics']
    error_comparison: Optional['ErrorComparison']
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "execution_id": self.execution_id,
            "test_name": self.test_name,
            "python_class": self.python_class,
            "python_method": self.python_method,
            "cli_command": self.cli_command,
            "test_parameters": self.test_parameters,
            "test_data_path": self.test_data_path,
            "python_output": str(self.python_output) if not isinstance(self.python_output, (dict, list)) else self.python_output,
            "cli_output": str(self.cli_output) if not isinstance(self.cli_output, (dict, list)) else self.cli_output,
            "is_identical": self.is_identical,
            "difference_details": self.difference_details,
            "performance_metrics": self.performance_metrics.to_dict() if self.performance_metrics else None,
            "error_comparison": self.error_comparison.to_dict() if self.error_comparison else None,
            "timestamp": self.timestamp.isoformat(),
            "passed": self.is_identical and (self.performance_metrics is None or self.performance_metrics.within_threshold)
        }


@dataclass
class PerformanceMetrics:
    """Performance comparison metrics."""

    python_time_ms: float
    cli_time_ms: float
    python_memory_mb: float
    cli_memory_mb: float
    performance_ratio: float  # python_time / cli_time
    memory_ratio: float  # python_memory / cli_memory
    is_within_threshold: bool
    runs_count: int = 1
    confidence_interval: Optional[tuple] = None

    @property
    def time_ratio(self) -> float:
        """Get time ratio (Python/CLI)."""
        return self.performance_ratio

    @property
    def memory_efficient(self) -> bool:
        """Check if memory usage is efficient."""
        return self.memory_ratio <= 1.05  # 5% tolerance

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "python_time_ms": self.python_time_ms,
            "cli_time_ms": self.cli_time_ms,
            "python_memory_mb": self.python_memory_mb,
            "cli_memory_mb": self.cli_memory_mb,
            "performance_ratio": self.performance_ratio,
            "memory_ratio": self.memory_ratio,
            "is_within_threshold": self.is_within_threshold,
            "time_ratio": self.time_ratio,
            "memory_efficient": self.memory_efficient,
            "runs_count": self.runs_count,
            "confidence_interval": self.confidence_interval
        }


@dataclass
class ErrorComparison:
    """Comparison of error handling between Python API and CLI."""

    python_error: Optional[str]
    cli_error: Optional[str]
    error_types_match: bool
    error_messages_similar: bool
    exit_code_match: bool
    similarity_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "python_error": self.python_error,
            "cli_error": self.cli_error,
            "error_types_match": self.error_types_match,
            "error_messages_similar": self.error_messages_similar,
            "exit_code_match": self.exit_code_match,
            "similarity_score": self.similarity_score,
            "compatible": self.error_types_match and self.error_messages_similar and self.exit_code_match
        }


@dataclass
class CompatibilityTestSuite:
    """Container for organizing and managing all compatibility tests."""

    suite_id: str
    test_date: datetime
    python_version: str
    cli_version: str
    configuration: Dict[str, Any]
    results: List[TestExecution] = field(default_factory=list)
    summary: Optional['TestSuiteSummary'] = None

    def add_result(self, result: TestExecution):
        """Add a test result to the suite."""
        self.results.append(result)

    def add_results(self, results: List[TestExecution]):
        """Add multiple test results to the suite."""
        self.results.extend(results)

    def calculate_summary(self) -> 'TestSuiteSummary':
        """Calculate summary statistics."""
        if not self.results:
            return TestSuiteSummary(
                total_tests=0,
                passed_tests=0,
                failed_tests=[],
                performance_summary=None
            )

        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results
                        if r.is_identical and
                        (r.performance_metrics is None or r.performance_metrics.is_within_threshold))
        failed_tests = [r for r in self.results if not (
            r.is_identical and
            (r.performance_metrics is None or r.performance_metrics.is_within_threshold)
        )]

        # Performance summary
        performance_metrics = [r.performance_metrics for r in self.results if r.performance_metrics]
        if performance_metrics:
            avg_ratio = sum(pm.performance_ratio for pm in performance_metrics) / len(performance_metrics)
            within_threshold = sum(1 for pm in performance_metrics if pm.is_within_threshold)
            performance_summary = PerformanceSummary(
                average_ratio=avg_ratio,
                within_threshold_count=within_threshold,
                total_count=len(performance_metrics)
            )
        else:
            performance_summary = None

        summary = TestSuiteSummary(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            performance_summary=performance_summary
        )

        self.summary = summary
        return summary

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "suite_id": self.suite_id,
            "test_date": self.test_date.isoformat(),
            "python_version": self.python_version,
            "cli_version": self.cli_version,
            "configuration": self.configuration,
            "results": [r.to_dict() for r in self.results],
            "summary": self.summary.to_dict() if self.summary else None
        }

    def save_to_file(self, file_path: Union[str, Path]):
        """Save suite to JSON file."""
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


@dataclass
class TestSuiteSummary:
    """Summary statistics for a test suite."""

    total_tests: int
    passed_tests: int
    failed_tests: List[TestExecution]
    performance_summary: Optional['PerformanceSummary'] = None

    @property
    def failed_count(self) -> int:
        """Get number of failed tests."""
        return len(self.failed_tests)

    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        return (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_count": self.failed_count,
            "success_rate": self.success_rate,
            "performance_summary": self.performance_summary.to_dict() if self.performance_summary else None,
            "failed_test_ids": [r.execution_id for r in self.failed_tests]
        }


@dataclass
class PerformanceSummary:
    """Summary of performance metrics across all tests."""

    average_ratio: float
    within_threshold_count: int
    total_count: int

    @property
    def within_threshold_percentage(self) -> float:
        """Get percentage of tests within performance threshold."""
        return (self.within_threshold_count / self.total_count * 100) if self.total_count > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "average_ratio": self.average_ratio,
            "within_threshold_count": self.within_threshold_count,
            "total_count": self.total_count,
            "within_threshold_percentage": self.within_threshold_percentage
        }


@dataclass
class TestConfiguration:
    """Configuration for compatibility tests."""

    test_data_base: str
    performance_thresholds: Dict[str, float]
    timeout_settings: Dict[str, int]
    categories: List[str]
    verbose: bool = False
    save_intermediate_results: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "test_data_base": self.test_data_base,
            "performance_thresholds": self.performance_thresholds,
            "timeout_settings": self.timeout_settings,
            "categories": self.categories,
            "verbose": self.verbose,
            "save_intermediate_results": self.save_intermediate_results
        }


@dataclass
class TestDataInfo:
    """Information about test data files."""

    data_id: str
    data_type: str  # SMALL, MEDIUM, LARGE
    data_format: str  # FASTA, FASTQ, RKDB
    file_path: str
    size_bytes: int
    metadata: Dict[str, Any]

    @property
    def size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.size_bytes / (1024 * 1024)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "data_id": self.data_id,
            "data_type": self.data_type,
            "data_format": self.data_format,
            "file_path": self.file_path,
            "size_bytes": self.size_bytes,
            "size_mb": self.size_mb,
            "metadata": self.metadata
        }


class TestStatus:
    """Test status constants."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TestResultType:
    """Test result type constants."""

    EXACT_MATCH = "exact_match"
    NUMERICAL_DIFFERENCE = "numerical_difference"
    TYPE_MISMATCH = "type_mismatch"
    MISSING_OUTPUT = "missing_output"
    EXTRA_OUTPUT = "extra_output"
    ERROR_MISMATCH = "error_mismatch"
    PERFORMANCE_THRESHOLD_EXCEEDED = "performance_threshold_exceeded"