"""
JSON report generator for RustKmer CLI-Python API compatibility testing.

This module generates structured JSON reports for programmatic consumption
and integration with CI/CD pipelines.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from ..data_models import (
    CompatibilityTestSuite,
    TestExecution,
    PerformanceMetrics,
    TestResult,
    TestCategory
)


class JSONReportGenerator:
    """Generate JSON reports for compatibility test results."""

    def __init__(self, output_dir: str = "/Users/forrest/Temp/demodata/test_reports"):
        """Initialize the JSON report generator.

        Args:
            output_dir: Directory to save JSON reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        test_suite: CompatibilityTestSuite,
        output_file: Optional[str] = None,
        include_raw_data: bool = False
    ) -> str:
        """Generate a comprehensive JSON report.

        Args:
            test_suite: Test suite results
            output_file: Optional custom output filename
            include_raw_data: Whether to include raw execution data

        Returns:
            Path to generated JSON file
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"compatibility_report_{timestamp}.json"

        output_path = self.output_dir / output_file

        # Generate JSON content
        json_content = self._generate_json_content(test_suite, include_raw_data)

        # Write to file with pretty formatting
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_content, f, indent=2, ensure_ascii=False)

        return str(output_path)

    def generate_summary_report(
        self,
        test_suite: CompatibilityTestSuite,
        output_file: Optional[str] = None
    ) -> str:
        """Generate a summary JSON report with key metrics only.

        Args:
            test_suite: Test suite results
            output_file: Optional custom output filename

        Returns:
            Path to generated JSON file
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"compatibility_summary_{timestamp}.json"

        output_path = self.output_dir / output_file

        # Generate summary content
        summary_content = self._generate_summary_content(test_suite)

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary_content, f, indent=2, ensure_ascii=False)

        return str(output_path)

    def generate_ci_report(
        self,
        test_suite: CompatibilityTestSuite,
        output_file: Optional[str] = None
    ) -> str:
        """Generate a CI/CD optimized JSON report.

        Args:
            test_suite: Test suite results
            output_file: Optional custom output filename

        Returns:
            Path to generated JSON file
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"compatibility_ci_{timestamp}.json"

        output_path = self.output_dir / output_file

        # Generate CI-optimized content
        ci_content = self._generate_ci_content(test_suite)

        # Write to file (compact for CI)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(ci_content, f, separators=(',', ':'), ensure_ascii=False)

        return str(output_path)

    def _generate_json_content(
        self,
        test_suite: CompatibilityTestSuite,
        include_raw_data: bool = False
    ) -> Dict[str, Any]:
        """Generate the complete JSON content structure.

        Args:
            test_suite: Test suite results
            include_raw_data: Whether to include raw execution data

        Returns:
            Complete JSON structure
        """
        # Calculate statistics
        stats = self._calculate_statistics(test_suite)

        # Build the JSON structure
        content = {
            "metadata": {
                "report_type": "comprehensive",
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "generator": "RustKmer Compatibility Test Suite",
                "environment": test_suite.environment_info
            },
            "summary": {
                "total_tests": test_suite.total_tests,
                "passed_tests": test_suite.total_passed,
                "failed_tests": test_suite.total_failed,
                "skipped_tests": test_suite.total_skipped,
                "pass_rate": test_suite.overall_pass_rate,
                "execution_time": test_suite.total_execution_time,
                "performance_comparisons": stats["performance_comparisons"],
                "performance_within_threshold": stats["performance_within_threshold"],
                "avg_python_time_ms": stats["avg_python_time"],
                "avg_cli_time_ms": stats["avg_cli_time"],
                "performance_ratio_avg": stats.get("performance_ratio_avg", 0)
            },
            "test_results": self._serialize_test_results(test_suite.test_results),
            "statistics": {
                "by_category": stats["category_performance"],
                "by_status": {
                    "passed": stats["passed"],
                    "failed": stats["failed"],
                    "skipped": stats["skipped"]
                },
                "performance_distribution": self._calculate_performance_distribution(test_suite)
            },
            "failed_tests": self._extract_failed_tests(test_suite),
            "performance_analysis": self._analyze_performance(test_suite),
            "recommendations": self._generate_recommendations(stats)
        }

        # Include raw data if requested
        if include_raw_data:
            content["raw_data"] = {
                "test_executions": self._serialize_test_executions(test_suite.test_results)
            }

        return content

    def _generate_summary_content(self, test_suite: CompatibilityTestSuite) -> Dict[str, Any]:
        """Generate a summary JSON content structure.

        Args:
            test_suite: Test suite results

        Returns:
            Summary JSON structure
        """
        stats = self._calculate_statistics(test_suite)

        return {
            "metadata": {
                "report_type": "summary",
                "generated_at": datetime.now().isoformat(),
                "environment": {
                    "python_version": test_suite.environment_info.get("python_version"),
                    "rustkmer_version": test_suite.environment_info.get("rustkmer_version"),
                    "platform": test_suite.environment_info.get("platform")
                }
            },
            "summary": {
                "total_tests": test_suite.total_tests,
                "passed_tests": test_suite.total_passed,
                "failed_tests": test_suite.total_failed,
                "pass_rate_percent": round(test_suite.overall_pass_rate, 2),
                "execution_time_seconds": test_suite.total_execution_time
            },
            "performance_summary": {
                "comparisons_made": stats["performance_comparisons"],
                "within_threshold": stats["performance_within_threshold"],
                "avg_python_time_ms": round(stats["avg_python_time"], 3),
                "avg_cli_time_ms": round(stats["avg_cli_time"], 3),
                "performance_ratio": round(
                    stats["avg_python_time"] / max(stats["avg_cli_time"], 0.001), 2
                )
            },
            "status": self._get_overall_status(test_suite),
            "critical_failures": len([t for t in test_suite.test_results if t.status == "FAILED"])
        }

    def _generate_ci_content(self, test_suite: CompatibilityTestSuite) -> Dict[str, Any]:
        """Generate a CI/CD optimized JSON content structure.

        Args:
            test_suite: Test suite results

        Returns:
            CI-optimized JSON structure
        """
        stats = self._calculate_statistics(test_suite)
        failed_tests = [t for t in test_suite.test_results if t.status == "FAILED"]

        return {
            "timestamp": datetime.now().isoformat(),
            "exit_code": 0 if test_suite.total_failed == 0 else 1,
            "summary": {
                "total": test_suite.total_tests,
                "passed": test_suite.total_passed,
                "failed": test_suite.total_failed,
                "pass_rate": round(test_suite.overall_pass_rate, 1)
            },
            "metrics": {
                "performance_tests": stats["performance_comparisons"],
                "performance_ok": stats["performance_within_threshold"],
                "avg_python_ms": round(stats["avg_python_time"], 2),
                "avg_cli_ms": round(stats["avg_cli_time"], 2)
            },
            "failures": [
                {
                    "name": t.test_name,
                    "category": t.category.value if t.category else "Unknown",
                    "error": t.error_message or "Unknown error"
                }
                for t in failed_tests[:10]  # Limit to first 10 failures for CI
            ],
            "status": "PASS" if test_suite.total_failed == 0 else "FAIL"
        }

    def _serialize_test_results(self, test_results: List[TestResult]) -> List[Dict[str, Any]]:
        """Serialize test results to JSON-compatible format.

        Args:
            test_results: List of test results

        Returns:
            Serialized test results
        """
        serialized = []

        for result in test_results:
            result_dict = {
                "test_name": result.test_name,
                "category": result.category.value if result.category else None,
                "status": result.status,
                "python_method": result.python_method,
                "cli_command": result.cli_command,
                "data_file": result.data_file,
                "parameters": result.parameters or {},
                "error_message": result.error_message,
                "output_differences": result.output_differences or [],
                "test_execution": self._serialize_test_execution(result.test_execution) if result.test_execution else None,
                "performance_metrics": self._serialize_performance_metrics(result.performance_metrics) if result.performance_metrics else None
            }

            serialized.append(result_dict)

        return serialized

    def _serialize_test_execution(self, execution: Optional[TestExecution]) -> Optional[Dict[str, Any]]:
        """Serialize test execution information.

        Args:
            execution: Test execution information

        Returns:
            Serialized execution info
        """
        if not execution:
            return None

        return {
            "execution_id": execution.execution_id,
            "timestamp": execution.timestamp,
            "hostname": execution.hostname,
            "python_version": execution.python_version,
            "rustkmer_version": execution.rustkmer_version,
            "cli_path": execution.cli_path,
            "exit_code": execution.exit_code
        }

    def _serialize_performance_metrics(self, metrics: Optional[PerformanceMetrics]) -> Optional[Dict[str, Any]]:
        """Serialize performance metrics.

        Args:
            metrics: Performance metrics

        Returns:
            Serialized metrics
        """
        if not metrics:
            return None

        return {
            "python_execution_time": metrics.python_execution_time,
            "cli_execution_time": metrics.cli_execution_time,
            "performance_ratio": metrics.performance_ratio,
            "python_memory_mb": metrics.python_memory_mb,
            "cli_memory_mb": metrics.cli_memory_mb,
            "python_cpu_percent": metrics.python_cpu_percent,
            "cli_cpu_percent": metrics.cli_cpu_percent
        }

    def _serialize_test_executions(self, test_results: List[TestResult]) -> List[Dict[str, Any]]:
        """Serialize raw test execution data.

        Args:
            test_results: List of test results

        Returns:
            Serialized execution data
        """
        executions = []

        for result in test_results:
            if result.test_execution:
                exec_data = self._serialize_test_execution(result.test_execution)
                if exec_data:
                    exec_data["test_result"] = {
                        "test_name": result.test_name,
                        "status": result.status
                    }
                    executions.append(exec_data)

        return executions

    def _calculate_statistics(self, test_suite: CompatibilityTestSuite) -> Dict[str, Any]:
        """Calculate comprehensive statistics from test results.

        Args:
            test_suite: Test suite results

        Returns:
            Dictionary of statistics
        """
        stats = {
            "passed": test_suite.total_passed,
            "failed": test_suite.total_failed,
            "skipped": test_suite.total_skipped,
            "performance_comparisons": 0,
            "performance_within_threshold": 0,
            "avg_python_time": 0,
            "avg_cli_time": 0,
            "category_performance": {}
        }

        python_times = []
        cli_times = []
        performance_ratios = []

        # Calculate performance statistics by category
        category_stats = {}

        for test_result in test_suite.test_results:
            # Track category statistics
            category = test_result.category.value if test_result.category else "Unknown"
            if category not in category_stats:
                category_stats[category] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "python_times": [],
                    "cli_times": []
                }

            category_stats[category]["total"] += 1
            if test_result.status == "PASSED":
                category_stats[category]["passed"] += 1
            elif test_result.status == "FAILED":
                category_stats[category]["failed"] += 1

            # Process performance metrics
            if test_result.performance_metrics:
                perf = test_result.performance_metrics

                if perf.python_execution_time is not None:
                    python_times.append(perf.python_execution_time)
                    category_stats[category]["python_times"].append(perf.python_execution_time)

                if perf.cli_execution_time is not None:
                    cli_times.append(perf.cli_execution_time)
                    category_stats[category]["cli_times"].append(perf.cli_execution_time)

                if perf.python_execution_time is not None and perf.cli_execution_time is not None:
                    stats["performance_comparisons"] += 1
                    if perf.performance_ratio <= 1.1:
                        stats["performance_within_threshold"] += 1
                    performance_ratios.append(perf.performance_ratio)

        # Calculate averages
        if python_times:
            stats["avg_python_time"] = sum(python_times) / len(python_times)
        if cli_times:
            stats["avg_cli_time"] = sum(cli_times) / len(cli_times)
        if performance_ratios:
            stats["performance_ratio_avg"] = sum(performance_ratios) / len(performance_ratios)

        # Calculate category averages
        for category, cat_data in category_stats.items():
            stats["category_performance"][category] = {
                "total": cat_data["total"],
                "passed": cat_data["passed"],
                "failed": cat_data["failed"],
                "pass_rate": (cat_data["passed"] / cat_data["total"]) * 100 if cat_data["total"] > 0 else 0,
                "avg_python_time": sum(cat_data["python_times"]) / len(cat_data["python_times"]) if cat_data["python_times"] else 0,
                "avg_cli_time": sum(cat_data["cli_times"]) / len(cat_data["cli_times"]) if cat_data["cli_times"] else 0
            }

        return stats

    def _calculate_performance_distribution(self, test_suite: CompatibilityTestSuite) -> Dict[str, Any]:
        """Calculate performance distribution statistics.

        Args:
            test_suite: Test suite results

        Returns:
            Performance distribution data
        """
        ratios = []
        for result in test_suite.test_results:
            if result.performance_metrics and result.performance_metrics.performance_ratio:
                ratios.append(result.performance_metrics.performance_ratio)

        if not ratios:
            return {}

        ratios.sort()

        return {
            "min": min(ratios),
            "max": max(ratios),
            "median": ratios[len(ratios) // 2],
            "p95": ratios[int(len(ratios) * 0.95)],
            "p99": ratios[int(len(ratios) * 0.99)],
            "within_110_percent": len([r for r in ratios if r <= 1.1]),
            "within_120_percent": len([r for r in ratios if r <= 1.2]),
            "within_150_percent": len([r for r in ratios if r <= 1.5])
        }

    def _extract_failed_tests(self, test_suite: CompatibilityTestSuite) -> List[Dict[str, Any]]:
        """Extract detailed information about failed tests.

        Args:
            test_suite: Test suite results

        Returns:
            List of failed test details
        """
        failed_tests = []

        for result in test_suite.test_results:
            if result.status == "FAILED":
                failed_test = {
                    "test_name": result.test_name,
                    "category": result.category.value if result.category else None,
                    "python_method": result.python_method,
                    "cli_command": result.cli_command,
                    "error_message": result.error_message,
                    "output_differences": result.output_differences or []
                }

                if result.performance_metrics:
                    failed_test["performance_metrics"] = self._serialize_performance_metrics(result.performance_metrics)

                failed_tests.append(failed_test)

        return failed_tests

    def _analyze_performance(self, test_suite: CompatibilityTestSuite) -> Dict[str, Any]:
        """Analyze performance patterns and trends.

        Args:
            test_suite: Test suite results

        Returns:
            Performance analysis results
        """
        analysis = {
            "overall_performance": "unknown",
            "performance_issues": [],
            "recommendations": []
        }

        performance_ratios = []
        for result in test_suite.test_results:
            if result.performance_metrics and result.performance_metrics.performance_ratio:
                performance_ratios.append(result.performance_metrics.performance_ratio)

        if performance_ratios:
            avg_ratio = sum(performance_ratios) / len(performance_ratios)
            max_ratio = max(performance_ratios)

            if avg_ratio <= 1.1:
                analysis["overall_performance"] = "excellent"
            elif avg_ratio <= 1.2:
                analysis["overall_performance"] = "good"
            elif avg_ratio <= 1.5:
                analysis["overall_performance"] = "acceptable"
            else:
                analysis["overall_performance"] = "needs_improvement"

            # Identify performance issues
            slow_tests = [
                result.test_name for result in test_suite.test_results
                if result.performance_metrics and result.performance_metrics.performance_ratio > 2.0
            ]

            if slow_tests:
                analysis["performance_issues"].append({
                    "type": "slow_performance",
                    "description": f"Tests with performance ratio > 2.0x",
                    "affected_tests": slow_tests
                })

            # Generate recommendations
            if max_ratio > 2.0:
                analysis["recommendations"].append(
                    "Investigate tests with performance ratio > 2.0x for optimization opportunities"
                )
            if avg_ratio > 1.5:
                analysis["recommendations"].append(
                    "Consider performance optimizations to bring Python API closer to CLI performance"
                )

        return analysis

    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test results.

        Args:
            stats: Calculated statistics

        Returns:
            List of recommendations
        """
        recommendations = []

        # Pass rate recommendations
        pass_rate = (stats["passed"] / (stats["passed"] + stats["failed"])) * 100 if (stats["passed"] + stats["failed"]) > 0 else 0

        if pass_rate < 80:
            recommendations.append(
                "Critical: Address failed tests immediately - compatibility is below acceptable threshold"
            )
        elif pass_rate < 95:
            recommendations.append(
                "Review and fix failed tests to improve compatibility to excellent levels"
            )

        # Performance recommendations
        if stats["performance_comparisons"] > 0:
            perf_rate = (stats["performance_within_threshold"] / stats["performance_comparisons"]) * 100
            if perf_rate < 70:
                recommendations.append(
                    "Performance needs attention - optimize Python API implementation"
                )
            elif perf_rate < 90:
                recommendations.append(
                    "Consider performance optimizations for better CLI parity"
                )

        # Category-specific recommendations
        for category, cat_stats in stats["category_performance"].items():
            cat_pass_rate = cat_stats.get("pass_rate", 0)
            if cat_pass_rate < 80:
                recommendations.append(
                    f"Focus on {category} category tests - current pass rate: {cat_pass_rate:.1f}%"
                )

        return recommendations

    def _get_overall_status(self, test_suite: CompatibilityTestSuite) -> str:
        """Get overall test status based on results.

        Args:
            test_suite: Test suite results

        Returns:
            Overall status string
        """
        if test_suite.total_failed == 0:
            return "PASS"
        elif test_suite.total_failed <= (test_suite.total_tests * 0.1):  # Up to 10% failures
            return "WARN"
        else:
            return "FAIL"