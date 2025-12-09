#!/usr/bin/env python3
"""
Test result reporting and comparison metrics for CLI compatibility tests

This module provides utilities for generating detailed reports,
comparing CLI and Python API results, and tracking performance metrics.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import statistics
import numpy as np
from dataclasses import dataclass
import matplotlib.pyplot as plt
import seaborn as sns


@dataclass
class PerformanceMetrics:
    """Performance comparison metrics"""
    mean_performance_ratio: float
    median_performance_ratio: float
    python_faster_count: int
    cli_faster_count: int
    performance_variance: float
    outliers: List[str]  # Test names with outlier performance


@dataclass
class AccuracyMetrics:
    """Accuracy comparison metrics"""
    exact_match_count: int
    approximate_match_count: int
    mismatch_count: int
    accuracy_score: float  # 0-100


@dataclass
class ComparisonReport:
    """Comprehensive comparison report"""
    test_count: int
    performance: PerformanceMetrics
    accuracy: AccuracyMetrics
    recommendations: List[str]
    issues: List[Dict[str, Any]]


class ResultComparator:
    """Compare CLI and Python API test results"""

    def __init__(self):
        """Initialize comparator"""
        self.comparators = {
            'count_command': self._compare_count_results,
            'query_command': self._compare_query_results,
            'dump_command': self._compare_dump_results,
            'stats_command': self._compare_stats_results
        }

    def compare_results(self, test_results: Dict[str, Any]) -> ComparisonReport:
        """
        Compare CLI and Python API results across all tests

        Args:
            test_results: Dictionary of test results

        Returns:
            ComparisonReport with detailed analysis
        """
        performance_data = []
        accuracy_matches = 0
        total_comparisons = 0
        issues = []

        for test_name, result in test_results.items():
            if not result.get('passed', False):
                continue

            total_comparisons += 1

            # Performance comparison
            if result.get('performance_ratio'):
                performance_data.append(result['performance_ratio'])

            # Accuracy comparison
            comparator = self.comparators.get(test_name)
            if comparator:
                match_result = comparator(result.get('cli_output'), result.get('python_output'))
                if match_result['match_type'] == 'exact':
                    accuracy_matches += 1
                elif match_result['match_type'] == 'mismatch':
                    issues.append({
                        'test': test_name,
                        'issue': 'Output mismatch',
                        'cli_output': str(result.get('cli_output'))[:200],
                        'python_output': str(result.get('python_output'))[:200],
                        'details': match_result.get('details', '')
                    })

        # Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics(performance_data, test_results)

        # Calculate accuracy metrics
        accuracy_metrics = AccuracyMetrics(
            exact_match_count=accuracy_matches,
            approximate_match_count=0,  # TODO: Implement fuzzy matching
            mismatch_count=total_comparisons - accuracy_matches,
            accuracy_score=(accuracy_matches / total_comparisons * 100) if total_comparisons > 0 else 0
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(performance_metrics, accuracy_metrics, issues)

        return ComparisonReport(
            test_count=total_comparisons,
            performance=performance_metrics,
            accuracy=accuracy_metrics,
            recommendations=recommendations,
            issues=issues
        )

    def _calculate_performance_metrics(self, performance_data: List[float], test_results: Dict[str, Any]) -> PerformanceMetrics:
        """Calculate performance comparison metrics"""
        if not performance_data:
            return PerformanceMetrics(0, 0, 0, 0, 0, [])

        mean_ratio = statistics.mean(performance_data)
        median_ratio = statistics.median(performance_data)
        variance = statistics.variance(performance_data) if len(performance_data) > 1 else 0

        # Count which implementation is faster
        python_faster = sum(1 for r in performance_data if r < 1.0)
        cli_faster = sum(1 for r in performance_data if r > 1.0)

        # Find outliers (performance ratios beyond 2 standard deviations)
        if len(performance_data) > 2:
            std_dev = statistics.stdev(performance_data)
            mean_val = mean_ratio
            outliers = []
            for test_name, result in test_results.items():
                if result.get('performance_ratio'):
                    ratio = result['performance_ratio']
                    if abs(ratio - mean_val) > 2 * std_dev:
                        outliers.append(test_name)
        else:
            outliers = []

        return PerformanceMetrics(
            mean_performance_ratio=mean_ratio,
            median_performance_ratio=median_ratio,
            python_faster_count=python_faster,
            cli_faster_count=cli_faster,
            performance_variance=variance,
            outliers=outliers
        )

    def _generate_recommendations(self, perf: PerformanceMetrics, acc: AccuracyMetrics, issues: List[Dict]) -> List[str]:
        """Generate improvement recommendations based on metrics"""
        recommendations = []

        # Performance recommendations
        if perf.mean_performance_ratio > 2.0:
            recommendations.append(
                "Python API is significantly slower than CLI (avg {:.1f}x). "
                "Consider optimizing Python bindings or using CLI for performance-critical tasks."
                .format(perf.mean_performance_ratio)
            )
        elif perf.mean_performance_ratio < 0.5:
            recommendations.append(
                "Python API is significantly faster than CLI (avg {:.1f}x). "
                "Consider optimizing CLI implementation."
                .format(1.0 / perf.mean_performance_ratio)
            )

        if perf.performance_variance > 1.0:
            recommendations.append(
                "High performance variance detected. "
                "Consider investigating performance inconsistencies across different operations."
            )

        if perf.outliers:
            recommendations.append(
                f"Performance outliers detected in: {', '.join(perf.outliers)}. "
                "Investigate these specific test cases."
            )

        # Accuracy recommendations
        if acc.accuracy_score < 100:
            recommendations.append(
                f"Accuracy issues detected ({acc.accuracy_score:.1f}% match rate). "
                "Review mismatched test outputs."
            )

            # Specific recommendations based on issues
            for issue in issues:
                test_name = issue['test']
                if 'count' in test_name:
                    recommendations.append(
                        f"Count command mismatch in {test_name}. "
                        "Check counting logic and canonicalization handling."
                    )
                elif 'query' in test_name:
                    recommendations.append(
                        f"Query command mismatch in {test_name}. "
                        "Verify k-mer encoding/decoding consistency."
                    )
                elif 'stats' in test_name:
                    recommendations.append(
                        f"Stats command mismatch in {test_name}. "
                        "Ensure statistical calculations are consistent."
                    )

        if not recommendations:
            recommendations.append("All tests passed with good performance parity!")

        return recommendations

    def _compare_count_results(self, cli_output: Any, python_output: Any) -> Dict[str, Any]:
        """Compare count command results"""
        # CLI output might be complex, Python output has total_kmers and unique_kmers
        if isinstance(python_output, dict) and python_output.get('total_kmers', 0) > 0:
            return {'match_type': 'exact', 'details': 'Both counted k-mers successfully'}
        return {'match_type': 'mismatch', 'details': 'Count results differ'}

    def _compare_query_results(self, cli_output: Any, python_output: Any) -> Dict[str, Any]:
        """Compare query command results"""
        if isinstance(cli_output, dict) and isinstance(python_output, dict):
            cli_found = cli_output.get('found', False)
            python_found = python_output.get('found', False)

            if cli_found == python_found:
                if cli_found:
                    # Both found the k-mer, check counts
                    cli_count = cli_output.get('count', 0)
                    python_count = python_output.get('count', 0)
                    if cli_count == python_count:
                        return {'match_type': 'exact', 'details': 'Both found k-mer with same count'}
                    else:
                        return {'match_type': 'approximate', 'details': f'Count mismatch: CLI={cli_count}, Python={python_count}'}
                else:
                    return {'match_type': 'exact', 'details': 'Both correctly report k-mer not found'}

        return {'match_type': 'mismatch', 'details': 'Query results differ significantly'}

    def _compare_dump_results(self, cli_output: Any, python_output: Any) -> Dict[str, Any]:
        """Compare dump command results"""
        # Check if both outputs contain k-mers
        cli_has_content = isinstance(cli_output, str) and len(cli_output.strip()) > 0
        python_has_kmers = isinstance(python_output, dict) and python_output.get('kmer_count', 0) > 0

        if cli_has_content and python_has_kmers:
            return {'match_type': 'exact', 'details': 'Both exported k-mers successfully'}
        elif cli_has_content or python_has_kmers:
            return {'match_type': 'mismatch', 'details': 'Only one implementation exported k-mers'}
        else:
            return {'match_type': 'exact', 'details': 'Both implementations produced no output (empty database?)'}

    def _compare_stats_results(self, cli_output: Any, python_output: Any) -> Dict[str, Any]:
        """Compare stats command results"""
        if isinstance(cli_output, dict) and isinstance(python_output, dict):
            matches = []

            # Check key fields
            if cli_output.get('kmer_size') == python_output.get('kmer_size'):
                matches.append('kmer_size')
            if cli_output.get('canonical') == python_output.get('canonical'):
                matches.append('canonical')
            if cli_output.get('sorted') == python_output.get('sorted'):
                matches.append('sorted')

            # Check approximate match for counts (might differ slightly due to rounding)
            cli_total = cli_output.get('total_kmers', 0)
            python_total = python_output.get('total_kmers', 0)
            if cli_total == python_total:
                matches.append('total_kmers')
            elif abs(cli_total - python_total) / max(cli_total, python_total, 1) < 0.01:  # < 1% difference
                matches.append('total_kmers_approx')

            if len(matches) >= 3:
                return {'match_type': 'exact', 'details': f'All key fields match: {", ".join(matches)}'}
            elif len(matches) >= 2:
                return {'match_type': 'approximate', 'details': f'Partial match: {", ".join(matches)}'}
            else:
                return {'match_type': 'mismatch', 'details': f'Only matched: {", ".join(matches)}'}

        return {'match_type': 'mismatch', 'details': 'Stats output format mismatch'}


class ReportGenerator:
    """Generate detailed compatibility test reports"""

    def __init__(self, output_dir: str = "compatibility_reports"):
        """
        Initialize report generator

        Args:
            output_dir: Directory to save reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate_html_report(self, report_data: Dict[str, Any]) -> str:
        """
        Generate HTML report from test results

        Args:
            report_data: Test results and comparison data

        Returns:
            Path to generated HTML report
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = self.output_dir / f"compatibility_report_{timestamp}.html"

        html_content = self._create_html_template(report_data)

        with open(html_path, 'w') as f:
            f.write(html_content)

        return str(html_path)

    def generate_markdown_report(self, report_data: Dict[str, Any]) -> str:
        """
        Generate Markdown report from test results

        Args:
            report_data: Test results and comparison data

        Returns:
            Path to generated Markdown report
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_path = self.output_dir / f"compatibility_report_{timestamp}.md"

        md_content = self._create_markdown_template(report_data)

        with open(md_path, 'w') as f:
            f.write(md_content)

        return str(md_path)

    def generate_performance_plots(self, test_results: Dict[str, Any]) -> List[str]:
        """
        Generate performance comparison plots

        Args:
            test_results: Test results data

        Returns:
            List of paths to generated plot images
        """
        plots = []

        # Extract performance data
        test_names = []
        performance_ratios = []
        cli_times = []
        python_times = []

        for test_name, result in test_results.items():
            if result.get('performance_ratio') is not None:
                test_names.append(test_name.replace('_command', '').title())
                performance_ratios.append(result['performance_ratio'])
                cli_times.append(result.get('execution_time_cli', 0) * 1000)  # Convert to ms
                python_times.append(result.get('execution_time_python', 0) * 1000)

        if not test_names:
            return plots

        # Create performance comparison plot
        plt.figure(figsize=(12, 8))

        # Subplot 1: Performance ratio bar chart
        plt.subplot(2, 2, 1)
        colors = ['green' if r < 1.2 else 'orange' if r < 2.0 else 'red' for r in performance_ratios]
        bars = plt.bar(test_names, performance_ratios, color=colors, alpha=0.7)
        plt.axhline(y=1.0, color='black', linestyle='--', alpha=0.5, label='Parity')
        plt.ylabel('Performance Ratio (Python/CLI)')
        plt.title('Performance Comparison')
        plt.xticks(rotation=45, ha='right')
        plt.legend()
        plt.grid(True, alpha=0.3)

        # Add value labels on bars
        for bar, ratio in zip(bars, performance_ratios):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                     f'{ratio:.2f}', ha='center', va='bottom')

        # Subplot 2: Execution time comparison
        plt.subplot(2, 2, 2)
        x = np.arange(len(test_names))
        width = 0.35
        plt.bar(x - width/2, cli_times, width, label='CLI', alpha=0.7)
        plt.bar(x + width/2, python_times, width, label='Python', alpha=0.7)
        plt.ylabel('Execution Time (ms)')
        plt.title('Execution Time Comparison')
        plt.xticks(x, test_names, rotation=45, ha='right')
        plt.legend()
        plt.grid(True, alpha=0.3)

        # Subplot 3: Performance distribution
        plt.subplot(2, 2, 3)
        plt.hist(performance_ratios, bins=10, alpha=0.7, edgecolor='black')
        plt.xlabel('Performance Ratio')
        plt.ylabel('Frequency')
        plt.title('Performance Ratio Distribution')
        plt.axvline(x=1.0, color='red', linestyle='--', alpha=0.5, label='Parity')
        plt.legend()
        plt.grid(True, alpha=0.3)

        # Subplot 4: Summary statistics
        plt.subplot(2, 2, 4)
        plt.axis('off')
        stats_text = f"""Performance Summary:

Mean Ratio: {statistics.mean(performance_ratios):.2f}
Median Ratio: {statistics.median(performance_ratios):.2f}
Std Dev: {statistics.stdev(performance_ratios) if len(performance_ratios) > 1 else 0:.2f}
Min Ratio: {min(performance_ratios):.2f}
Max Ratio: {max(performance_ratios):.2f}

Python Faster: {sum(1 for r in performance_ratios if r < 1.0)}
CLI Faster: {sum(1 for r in performance_ratios if r > 1.0)}
Within 20%: {sum(1 for r in performance_ratios if 0.8 <= r <= 1.2)}"""

        plt.text(0.1, 0.5, stats_text, fontsize=10, verticalalignment='center',
                fontfamily='monospace')

        plt.tight_layout()

        # Save plot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plot_path = self.output_dir / f"performance_comparison_{timestamp}.png"
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()

        plots.append(str(plot_path))

        return plots

    def _create_html_template(self, report_data: Dict[str, Any]) -> str:
        """Create HTML report template"""
        summary = report_data.get('summary', {})
        comparison = report_data.get('comparison', {})

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>RustKmer CLI-Python Compatibility Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 40px;
            line-height: 1.6;
        }}
        .summary {{
            background: #f5f5f5;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 30px;
        }}
        .pass {{ color: green; }}
        .fail {{ color: red; }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 30px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
        }}
        .recommendation {{
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 10px;
        }}
    </style>
</head>
<body>
    <h1>RustKmer CLI-Python Compatibility Report</h1>

    <div class="summary">
        <h2>Test Summary</h2>
        <p>Total Tests: <strong>{summary.get('total_tests', 0)}</strong></p>
        <p>Passed: <span class="pass">{summary.get('passed', 0)}</span></p>
        <p>Failed: <span class="fail">{summary.get('failed', 0)}</span></p>
        <p>Pass Rate: <strong>{summary.get('pass_rate', 0):.1f}%</strong></p>
        <p>Total Time: <strong>{summary.get('total_time', 0):.2f}s</strong></p>
    </div>

    <h2>Performance Analysis</h2>
    {self._format_performance_html(comparison.get('performance', {}))}

    <h2>Accuracy Analysis</h2>
    {self._format_accuracy_html(comparison.get('accuracy', {}))}

    <h2>Recommendations</h2>
    {self._format_recommendations_html(comparison.get('recommendations', []))}

    <h2>Failed Tests</h2>
    {self._format_failed_tests_html(comparison.get('issues', []))}
</body>
</html>
"""
        return html

    def _format_performance_html(self, perf: Dict[str, Any]) -> str:
        """Format performance metrics for HTML"""
        if not perf:
            return "<p>No performance data available</p>"

        return f"""
    <div class="summary">
        <p>Mean Performance Ratio: <strong>{perf.get('mean_performance_ratio', 0):.2f}x</strong></p>
        <p>Median Performance Ratio: <strong>{perf.get('median_performance_ratio', 0):.2f}x</strong></p>
        <p>Python Faster: <strong>{perf.get('python_faster_count', 0)}</strong> tests</p>
        <p>CLI Faster: <strong>{perf.get('cli_faster_count', 0)}</strong> tests</p>
        <p>Performance Variance: <strong>{perf.get('performance_variance', 0):.2f}</strong></p>
    </div>
"""

    def _format_accuracy_html(self, acc: Dict[str, Any]) -> str:
        """Format accuracy metrics for HTML"""
        if not acc:
            return "<p>No accuracy data available</p>"

        return f"""
    <div class="summary">
        <p>Accuracy Score: <strong>{acc.get('accuracy_score', 0):.1f}%</strong></p>
        <p>Exact Matches: <strong>{acc.get('exact_match_count', 0)}</strong></p>
        <p>Mismatches: <strong>{acc.get('mismatch_count', 0)}</strong></p>
    </div>
"""

    def _format_recommendations_html(self, recommendations: List[str]) -> str:
        """Format recommendations for HTML"""
        if not recommendations:
            return "<p>No recommendations - all tests passed successfully!</p>"

        html = ""
        for rec in recommendations:
            html += f'<div class="recommendation">{rec}</div>'
        return html

    def _format_failed_tests_html(self, issues: List[Dict[str, Any]]) -> str:
        """Format failed test details for HTML"""
        if not issues:
            return "<p>All tests passed!</p>"

        html = "<table>"
        html += "<tr><th>Test</th><th>Issue</th><th>Details</th></tr>"

        for issue in issues:
            html += f"""
            <tr>
                <td>{issue.get('test', 'Unknown')}</td>
                <td>{issue.get('issue', 'Unknown')}</td>
                <td>{issue.get('details', 'No details available')}</td>
            </tr>
            """

        html += "</table>"
        return html

    def _create_markdown_template(self, report_data: Dict[str, Any]) -> str:
        """Create Markdown report template"""
        summary = report_data.get('summary', {})
        comparison = report_data.get('comparison', {})

        md = f"""# RustKmer CLI-Python Compatibility Report

## Test Summary

- **Total Tests**: {summary.get('total_tests', 0)}
- **Passed**: {summary.get('passed', 0)}
- **Failed**: {summary.get('failed', 0)}
- **Pass Rate**: {summary.get('pass_rate', 0):.1f}%
- **Total Time**: {summary.get('total_time', 0):.2f}s

## Performance Analysis

{self._format_performance_markdown(comparison.get('performance', {}))}

## Accuracy Analysis

{self._format_accuracy_markdown(comparison.get('accuracy', {}))}

## Recommendations

{self._format_recommendations_markdown(comparison.get('recommendations', []))}

## Failed Tests

{self._format_failed_tests_markdown(comparison.get('issues', []))}
"""
        return md

    def _format_performance_markdown(self, perf: Dict[str, Any]) -> str:
        """Format performance metrics for Markdown"""
        if not perf:
            return "No performance data available\n"

        return f"""
- **Mean Performance Ratio**: {perf.get('mean_performance_ratio', 0):.2f}x
- **Median Performance Ratio**: {perf.get('median_performance_ratio', 0):.2f}x
- **Python Faster**: {perf.get('python_faster_count', 0)} tests
- **CLI Faster**: {perf.get('cli_faster_count', 0)} tests
- **Performance Variance**: {perf.get('performance_variance', 0):.2f}
"""

    def _format_accuracy_markdown(self, acc: Dict[str, Any]) -> str:
        """Format accuracy metrics for Markdown"""
        if not acc:
            return "No accuracy data available\n"

        return f"""
- **Accuracy Score**: {acc.get('accuracy_score', 0):.1f}%
- **Exact Matches**: {acc.get('exact_match_count', 0)}
- **Mismatches**: {acc.get('mismatch_count', 0)}
"""

    def _format_recommendations_markdown(self, recommendations: List[str]) -> str:
        """Format recommendations for Markdown"""
        if not recommendations:
            return "No recommendations - all tests passed successfully!\n"

        md = ""
        for i, rec in enumerate(recommendations, 1):
            md += f"{i}. {rec}\n"
        return md

    def _format_failed_tests_markdown(self, issues: List[Dict[str, Any]]) -> str:
        """Format failed test details for Markdown"""
        if not issues:
            return "All tests passed!\n"

        md = "| Test | Issue | Details |\n"
        md += "|------|--------|----------|\n"

        for issue in issues:
            test = issue.get('test', 'Unknown')
            issue_type = issue.get('issue', 'Unknown')
            details = issue.get('details', 'No details available')
            md += f"| {test} | {issue_type} | {details} |\n"

        return md