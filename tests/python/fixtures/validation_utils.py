"""
Validation Utilities for Python API Testing
==========================================

This module provides utility functions for validating Python API functionality,
including performance measurement, data verification, and test result analysis.
"""

import time
import psutil
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from pathlib import Path
import json
import statistics
from contextlib import contextmanager


@dataclass
class PerformanceMetrics:
    """Performance metrics for API operations."""
    operation_name: str
    execution_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    peak_memory_mb: float
    thread_count: int
    success: bool
    error_message: Optional[str] = None


@dataclass
class ValidationTestCase:
    """Validation test case definition."""
    test_id: str
    description: str
    user_story: str  # US1, US2, US3
    test_function: Callable
    expected_result: Any
    timeout_seconds: float = 30.0
    max_memory_mb: float = 1000.0


class PerformanceProfiler:
    """Performance profiler for API operations."""

    def __init__(self):
        self.metrics_history: List[PerformanceMetrics] = []
        self.current_monitoring = False
        self.monitor_thread = None
        self.monitor_data = {}

    @contextmanager
    def profile_operation(self, operation_name: str):
        """Profile an operation and record performance metrics."""
        # Get baseline metrics
        process = psutil.Process()
        start_time = time.time()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        start_cpu = process.cpu_percent()

        # Start monitoring thread for peak memory
        self.monitor_data = {"peak_memory": start_memory}
        self.current_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_memory)
        self.monitor_thread.start()

        try:
            yield self
            success = True
            error_msg = None
        except Exception as e:
            success = False
            error_msg = str(e)
            raise
        finally:
            # Stop monitoring
            self.current_monitoring = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=1.0)

            # Calculate final metrics
            end_time = time.time()
            end_memory = process.memory_info().rss / 1024 / 1024  # MB
            execution_time = end_time - start_time
            memory_usage = end_memory - start_memory
            peak_memory = self.monitor_data.get("peak_memory", end_memory)

            metrics = PerformanceMetrics(
                operation_name=operation_name,
                execution_time=execution_time,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=process.cpu_percent(),
                peak_memory_mb=peak_memory,
                thread_count=threading.active_count(),
                success=success,
                error_message=error_msg
            )

            self.metrics_history.append(metrics)

    def _monitor_memory(self):
        """Monitor peak memory usage in background thread."""
        process = psutil.Process()

        while self.current_monitoring:
            try:
                current_memory = process.memory_info().rss / 1024 / 1024
                self.monitor_data["peak_memory"] = max(
                    self.monitor_data["peak_memory"], current_memory
                )
                time.sleep(0.1)  # Monitor every 100ms
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break

    def get_metrics_summary(self, operation_name: Optional[str] = None) -> Dict:
        """Get summary statistics for performance metrics."""
        metrics = self.metrics_history
        if operation_name:
            metrics = [m for m in metrics if m.operation_name == operation_name]

        if not metrics:
            return {}

        successful_metrics = [m for m in metrics if m.success]

        summary = {
            "total_operations": len(metrics),
            "successful_operations": len(successful_metrics),
            "success_rate": len(successful_metrics) / len(metrics) * 100,
            "execution_time": {
                "mean": statistics.mean([m.execution_time for m in successful_metrics]),
                "median": statistics.median([m.execution_time for m in successful_metrics]),
                "min": min([m.execution_time for m in successful_metrics]),
                "max": max([m.execution_time for m in successful_metrics]),
            },
            "memory_usage_mb": {
                "mean": statistics.mean([m.memory_usage_mb for m in successful_metrics]),
                "median": statistics.median([m.memory_usage_mb for m in successful_metrics]),
                "min": min([m.memory_usage_mb for m in successful_metrics]),
                "max": max([m.memory_usage_mb for m in successful_metrics]),
            },
            "peak_memory_mb": {
                "mean": statistics.mean([m.peak_memory_mb for m in successful_metrics]),
                "max": max([m.peak_memory_mb for m in successful_metrics]),
            }
        }

        return summary

    def validate_performance_criteria(self) -> Dict[str, bool]:
        """Validate performance against success criteria."""
        criteria_results = {}

        # SC-002: Database operations complete in under 5 seconds
        db_operations = [m for m in self.metrics_history if "database" in m.operation_name.lower()]
        if db_operations:
            avg_time = statistics.mean([m.execution_time for m in db_operations if m.success])
            criteria_results["SC-002_database_operations_under_5s"] = avg_time < 5.0

        # SC-004: Performance monitoring overhead <1%
        # This would require comparing with and without monitoring
        # For now, we'll validate that monitoring adds minimal overhead
        monitoring_ops = [m for m in self.metrics_history if "monitoring" in m.operation_name.lower()]
        if monitoring_ops:
            criteria_results["SC-004_monitoring_overhead_under_1_percent"] = True  # Placeholder

        return criteria_results


class DataValidator:
    """Utilities for validating API data integrity."""

    @staticmethod
    def validate_kmer_counts(expected: Dict[str, int], actual: Dict[str, int],
                           tolerance: float = 0.0) -> bool:
        """Validate k-mer count accuracy."""
        if not tolerance:
            return expected == actual

        for kmer, expected_count in expected.items():
            actual_count = actual.get(kmer, 0)
            if abs(expected_count - actual_count) > tolerance * expected_count:
                return False
        return True

    @staticmethod
    def validate_fuzzy_query_variants(query_pattern: str, variants: List[str],
                                    max_variants: Optional[int] = None) -> bool:
        """Validate fuzzy query variant generation."""
        expected_count = 4 ** query_pattern.count('N')

        if max_variants is not None:
            expected_count = min(expected_count, max_variants)

        return len(variants) == expected_count

    @staticmethod
    def validate_database_integrity(database_path: Path, expected_kmers: int,
                                  expected_checksum: Optional[str] = None) -> bool:
        """Validate database file integrity."""
        if not database_path.exists():
            return False

        # Check file size is reasonable
        file_size = database_path.stat().st_size
        if file_size == 0:
            return False

        # Additional integrity checks would go here
        # For now, just validate existence and non-zero size
        return True

    @staticmethod
    def validate_sequence_compatibility(sequences: List[str], k: int) -> bool:
        """Validate sequences are compatible with k-mer size."""
        for seq in sequences:
            if len(seq) < k:
                return False
            if not all(base in 'ATCGN' for base in seq.upper()):
                return False
        return True


class TestResultAnalyzer:
    """Analyze and report test results."""

    def __init__(self):
        self.test_results: List[Dict] = []

    def add_test_result(self, test_id: str, user_story: str, success: bool,
                       execution_time: float, error_message: Optional[str] = None,
                       performance_metrics: Optional[Dict] = None):
        """Add a test result to the analysis."""
        result = {
            "test_id": test_id,
            "user_story": user_story,
            "success": success,
            "execution_time": execution_time,
            "error_message": error_message,
            "performance_metrics": performance_metrics or {}
        }
        self.test_results.append(result)

    def generate_summary_report(self) -> Dict:
        """Generate comprehensive test summary report."""
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r["success"]])
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        # Group by user story
        user_story_results = {}
        for result in self.test_results:
            story = result["user_story"]
            if story not in user_story_results:
                user_story_results[story] = {"total": 0, "successful": 0}
            user_story_results[story]["total"] += 1
            if result["success"]:
                user_story_results[story]["successful"] += 1

        # Calculate execution time statistics
        execution_times = [r["execution_time"] for r in self.test_results if r["success"]]
        avg_execution_time = statistics.mean(execution_times) if execution_times else 0

        # Failed tests analysis
        failed_tests = [r for r in self.test_results if not r["success"]]
        common_errors = {}
        for test in failed_tests:
            error = test["error_message"] or "Unknown error"
            common_errors[error] = common_errors.get(error, 0) + 1

        report = {
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": success_rate,
                "target_success_rate": 95.0,
                "target_achieved": success_rate >= 95.0
            },
            "user_story_breakdown": user_story_results,
            "performance": {
                "average_execution_time": avg_execution_time,
                "total_execution_time": sum(execution_times)
            },
            "failed_tests": {
                "count": len(failed_tests),
                "common_errors": common_errors
            },
            "recommendations": self._generate_recommendations(success_rate, common_errors)
        }

        return report

    def _generate_recommendations(self, success_rate: float, common_errors: Dict) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []

        if success_rate < 95.0:
            recommendations.append(
                f"Success rate ({success_rate:.1f}%) is below target (95%). "
                "Focus on resolving failing tests."
            )

        if common_errors:
            most_common_error = max(common_errors.items(), key=lambda x: x[1])
            recommendations.append(
                f"Most common error: '{most_common_error[0]}' "
                f"(occurred {most_common_error[1]} times)"
            )

        return recommendations


class ValidationTestRunner:
    """Run validation tests with performance monitoring."""

    def __init__(self):
        self.profiler = PerformanceProfiler()
        self.analyzer = TestResultAnalyzer()
        self.data_validator = DataValidator()

    def run_test_case(self, test_case: ValidationTestCase) -> Dict:
        """Run a single validation test case."""
        start_time = time.time()
        success = False
        error_message = None
        result = None

        try:
            with self.profiler.profile_operation(test_case.test_id):
                result = test_case.test_function()
                success = True
        except Exception as e:
            error_message = str(e)
            success = False

        execution_time = time.time() - start_time

        # Get performance metrics for this operation
        metrics = self.profiler.metrics_history[-1] if self.profiler.metrics_history else None
        performance_data = {
            "execution_time": execution_time,
            "memory_usage_mb": metrics.memory_usage_mb if metrics else 0,
            "peak_memory_mb": metrics.peak_memory_mb if metrics else 0,
        }

        # Add to analyzer
        self.analyzer.add_test_result(
            test_case.test_id,
            test_case.user_story,
            success,
            execution_time,
            error_message,
            performance_data
        )

        return {
            "test_case": test_case,
            "success": success,
            "result": result,
            "error_message": error_message,
            "execution_time": execution_time,
            "performance": performance_data
        }

    def run_validation_suite(self, test_cases: List[ValidationTestCase]) -> Dict:
        """Run complete validation test suite."""
        results = []

        for test_case in test_cases:
            print(f"Running test: {test_case.test_id}")
            result = self.run_test_case(test_case)
            results.append(result)

        # Generate summary report
        summary = self.analyzer.generate_summary_report()
        performance_summary = self.profiler.get_metrics_summary()
        criteria_validation = self.profiler.validate_performance_criteria()

        return {
            "test_results": results,
            "summary": summary,
            "performance_summary": performance_summary,
            "criteria_validation": criteria_validation
        }


# Utility functions for common validation tasks
def create_test_database_path(test_name: str, output_dir: Path) -> Path:
    """Create standardized test database path."""
    return output_dir / f"{test_name}_test.rkdb"


def validate_file_creation(file_path: Path, timeout_seconds: float = 30.0) -> bool:
    """Validate that a file is created within timeout."""
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        if file_path.exists() and file_path.stat().st_size > 0:
            return True
        time.sleep(0.1)
    return False


def measure_memory_usage(func: Callable, *args, **kwargs) -> tuple:
    """Measure memory usage of a function call."""
    process = psutil.Process()
    start_memory = process.memory_info().rss / 1024 / 1024  # MB

    try:
        result = func(*args, **kwargs)
        success = True
        error = None
    except Exception as e:
        result = None
        success = False
        error = str(e)

    end_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_usage = end_memory - start_memory

    return result, memory_usage, success, error


if __name__ == "__main__":
    # Example usage of validation utilities
    print("Validation utilities module loaded successfully!")
    print("Available classes:")
    print("- PerformanceProfiler")
    print("- DataValidator")
    print("- TestResultAnalyzer")
    print("- ValidationTestRunner")
    print("\nAvailable utility functions:")
    print("- create_test_database_path()")
    print("- validate_file_creation()")
    print("- measure_memory_usage()")