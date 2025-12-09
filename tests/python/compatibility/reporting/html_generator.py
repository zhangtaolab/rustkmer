"""
HTML report generator for RustKmer CLI-Python API compatibility testing.

This module generates comprehensive HTML reports with visualizations
for compatibility test results.
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


class HTMLReportGenerator:
    """Generate HTML reports for compatibility test results."""

    def __init__(self, output_dir: str = "/Users/forrest/Temp/demodata/test_reports"):
        """Initialize the HTML report generator.

        Args:
            output_dir: Directory to save HTML reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        test_suite: CompatibilityTestSuite,
        output_file: Optional[str] = None
    ) -> str:
        """Generate a comprehensive HTML report.

        Args:
            test_suite: Test suite results
            output_file: Optional custom output filename

        Returns:
            Path to generated HTML file
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"compatibility_report_{timestamp}.html"

        output_path = self.output_dir / output_file

        # Generate HTML content
        html_content = self._generate_html_content(test_suite)

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return str(output_path)

    def _generate_html_content(self, test_suite: CompatibilityTestSuite) -> str:
        """Generate the complete HTML content.

        Args:
            test_suite: Test suite results

        Returns:
            Complete HTML document as string
        """
        # Calculate statistics
        stats = self._calculate_statistics(test_suite)

        # Generate HTML sections
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RustKmer CLI-Python API Compatibility Report</title>
    {self._get_css_styles()}
    {self._get_javascript()}
</head>
<body>
    <div class="container">
        <header>
            <h1>RustKmer CLI-Python API Compatibility Report</h1>
            <p class="subtitle">
                Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} |
                Python API Version: {test_suite.environment_info.get("python_version", "N/A")} |
                RustKmer Version: {test_suite.environment_info.get("rustkmer_version", "N/A")}
            </p>
        </header>

        {self._generate_summary_section(stats)}
        {self._generate_performance_section(stats)}
        {self._generate_test_results_section(test_suite)}
        {self._generate_details_section(test_suite)}
        {self._generate_appendix_section(test_suite)}
    </div>

    <script>
        {self._get_chart_scripts(stats)}
    </script>
</body>
</html>"""

        return html

    def _get_css_styles(self) -> str:
        """Get CSS styles for the HTML report."""
        return """
<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        line-height: 1.6;
        color: #333;
        background-color: #f5f5f5;
    }

    .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }

    header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 40px;
        border-radius: 10px;
        margin-bottom: 30px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    h1 {
        font-size: 2.5em;
        margin-bottom: 10px;
    }

    .subtitle {
        font-size: 1.1em;
        opacity: 0.9;
    }

    .section {
        background: white;
        margin-bottom: 30px;
        padding: 30px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    h2 {
        color: #333;
        margin-bottom: 20px;
        font-size: 1.8em;
        border-bottom: 2px solid #667eea;
        padding-bottom: 10px;
    }

    h3 {
        color: #555;
        margin: 20px 0 15px 0;
        font-size: 1.3em;
    }

    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
        margin-bottom: 30px;
    }

    .stat-card {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }

    .stat-value {
        font-size: 2em;
        font-weight: bold;
        color: #667eea;
        margin-bottom: 5px;
    }

    .stat-label {
        color: #666;
        font-size: 0.9em;
    }

    .status-passed {
        color: #28a745;
        font-weight: bold;
    }

    .status-failed {
        color: #dc3545;
        font-weight: bold;
    }

    .status-skipped {
        color: #ffc107;
        font-weight: bold;
    }

    .chart-container {
        width: 100%;
        max-width: 600px;
        margin: 20px auto;
    }

    canvas {
        max-width: 100%;
        height: auto;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
        background: white;
    }

    th, td {
        padding: 12px;
        text-align: left;
        border-bottom: 1px solid #ddd;
    }

    th {
        background-color: #f8f9fa;
        font-weight: 600;
        color: #495057;
    }

    tr:hover {
        background-color: #f5f5f5;
    }

    .performance-bar {
        background-color: #e9ecef;
        border-radius: 4px;
        overflow: hidden;
        height: 20px;
        margin: 5px 0;
    }

    .performance-fill {
        height: 100%;
        background: linear-gradient(90deg, #28a745 0%, #ffc107 75%, #dc3545 100%);
        transition: width 0.3s ease;
    }

    .expandable {
        cursor: pointer;
        user-select: none;
    }

    .expandable:hover {
        background-color: #f8f9fa;
    }

    .expandable::before {
        content: '▶ ';
        display: inline-block;
        margin-right: 5px;
        transition: transform 0.2s;
    }

    .expanded::before {
        transform: rotate(90deg);
    }

    .collapsible-content {
        display: none;
        padding-left: 20px;
        border-left: 2px solid #e9ecef;
        margin-left: 10px;
    }

    .visible {
        display: block;
    }

    .alert {
        padding: 15px;
        margin: 20px 0;
        border-radius: 5px;
    }

    .alert-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }

    .alert-danger {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }

    .alert-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }

    .code-block {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 5px;
        padding: 15px;
        font-family: 'Courier New', monospace;
        font-size: 0.9em;
        overflow-x: auto;
        white-space: pre-wrap;
    }

    @media (max-width: 768px) {
        .container {
            padding: 10px;
        }

        header {
            padding: 20px;
        }

        h1 {
            font-size: 2em;
        }

        .stats-grid {
            grid-template-columns: 1fr;
        }

        table {
            font-size: 0.9em;
        }

        th, td {
            padding: 8px;
        }
    }
</style>"""

    def _get_javascript(self) -> str:
        """Get JavaScript includes for the HTML report."""
        return """
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>"""

    def _get_chart_scripts(self, stats: Dict[str, Any]) -> str:
        """Get JavaScript chart initialization scripts."""
        return f"""
// Initialize charts when document is ready
document.addEventListener('DOMContentLoaded', function() {{
    // Test Results Pie Chart
    const resultsCtx = document.getElementById('resultsChart');
    if (resultsCtx) {{
        new Chart(resultsCtx, {{
            type: 'pie',
            data: {{
                labels: ['Passed', 'Failed', 'Skipped'],
                datasets: [{{
                    data: [{stats['passed']}, {stats['failed']}, {stats['skipped']}],
                    backgroundColor: ['#28a745', '#dc3545', '#ffc107'],
                    borderWidth: 2,
                    borderColor: '#fff'
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        position: 'bottom'
                    }},
                    title: {{
                        display: true,
                        text: 'Test Results Distribution'
                    }}
                }}
            }}
        }});
    }}

    // Performance Comparison Chart
    const perfCtx = document.getElementById('performanceChart');
    if (perfCtx) {{
        new Chart(perfCtx, {{
            type: 'bar',
            data: {{
                labels: ['Python API', 'CLI'],
                datasets: [{{
                    label: 'Average Execution Time (ms)',
                    data: [{stats.get('avg_python_time', 0):.2f}, {stats.get('avg_cli_time', 0):.2f}],
                    backgroundColor: ['#667eea', '#764ba2'],
                    borderColor: ['#667eea', '#764ba2'],
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Time (milliseconds)'
                        }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    title: {{
                        display: true,
                        text: 'Performance Comparison'
                    }}
                }}
            }}
        }});
    }}

    // Category Performance Chart
    const catCtx = document.getElementById('categoryChart');
    if (catCtx) {{
        new Chart(catCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(list(stats.get('category_performance', {}).keys()))},
                datasets: [{{
                    label: 'Python API',
                    data: {json.dumps([v.get('python_time', 0) for v in stats.get('category_performance', {}).values()])},
                    backgroundColor: '#667eea'
                }}, {{
                    label: 'CLI',
                    data: {json.dumps([v.get('cli_time', 0) for v in stats.get('category_performance', {}).values()])},
                    backgroundColor: '#764ba2'
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Average Time (milliseconds)'
                        }}
                    }}
                }},
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Performance by Test Category'
                    }}
                }}
            }}
        }});
    }}
}});

// Toggle expandable sections
function toggleSection(element) {{
    element.classList.toggle('expanded');
    const content = element.nextElementSibling;
    content.classList.toggle('visible');
}}"""

    def _calculate_statistics(self, test_suite: CompatibilityTestSuite) -> Dict[str, Any]:
        """Calculate test statistics from the test suite.

        Args:
            test_suite: Test suite results

        Returns:
            Dictionary of calculated statistics
        """
        stats = {
            "total": test_suite.total_tests,
            "passed": test_suite.total_passed,
            "failed": test_suite.total_failed,
            "skipped": test_suite.total_skipped,
            "pass_rate": test_suite.overall_pass_rate,
            "avg_python_time": 0,
            "avg_cli_time": 0,
            "performance_comparisons": 0,
            "performance_within_threshold": 0,
            "category_performance": {}
        }

        # Calculate performance statistics
        python_times = []
        cli_times = []
        category_stats = {}

        for test_result in test_suite.test_results:
            if test_result.performance_metrics:
                perf = test_result.performance_metrics
                if perf.python_execution_time:
                    python_times.append(perf.python_execution_time)
                if perf.cli_execution_time:
                    cli_times.append(perf.cli_execution_time)

                # Count performance comparisons
                if perf.python_execution_time and perf.cli_execution_time:
                    stats["performance_comparisons"] += 1
                    if perf.performance_ratio <= 1.1:  # Within 110% threshold
                        stats["performance_within_threshold"] += 1

            # Track by category
            category = test_result.category.value if test_result.category else "Unknown"
            if category not in category_stats:
                category_stats[category] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "python_time": 0,
                    "cli_time": 0,
                    "performance_count": 0
                }

            category_stats[category]["total"] += 1
            if test_result.status == "PASSED":
                category_stats[category]["passed"] += 1
            elif test_result.status == "FAILED":
                category_stats[category]["failed"] += 1

            if test_result.performance_metrics:
                perf = test_result.performance_metrics
                if perf.python_execution_time:
                    category_stats[category]["python_time"] += perf.python_execution_time
                if perf.cli_execution_time:
                    category_stats[category]["cli_time"] += perf.cli_execution_time
                if perf.python_execution_time and perf.cli_execution_time:
                    category_stats[category]["performance_count"] += 1

        # Calculate averages
        if python_times:
            stats["avg_python_time"] = sum(python_times) / len(python_times)
        if cli_times:
            stats["avg_cli_time"] = sum(cli_times) / len(cli_times)

        # Calculate category averages
        for cat, cat_stats in category_stats.items():
            if cat_stats["performance_count"] > 0:
                cat_stats["python_time"] /= cat_stats["performance_count"]
                cat_stats["cli_time"] /= cat_stats["performance_count"]

        stats["category_performance"] = category_stats

        return stats

    def _generate_summary_section(self, stats: Dict[str, Any]) -> str:
        """Generate the summary section of the report.

        Args:
            stats: Calculated statistics

        Returns:
            HTML section for summary
        """
        pass_rate_color = "#28a745" if stats["pass_rate"] >= 95 else "#ffc107" if stats["pass_rate"] >= 80 else "#dc3545"

        return f"""
        <section class="section">
            <h2>Executive Summary</h2>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{stats['total']}</div>
                    <div class="stat-label">Total Tests</div>
                </div>

                <div class="stat-card">
                    <div class="stat-value status-passed">{stats['passed']}</div>
                    <div class="stat-label">Tests Passed</div>
                </div>

                <div class="stat-card">
                    <div class="stat-value status-failed">{stats['failed']}</div>
                    <div class="stat-label">Tests Failed</div>
                </div>

                <div class="stat-card">
                    <div class="stat-value status-skipped">{stats['skipped']}</div>
                    <div class="stat-label">Tests Skipped</div>
                </div>

                <div class="stat-card">
                    <div class="stat-value" style="color: {pass_rate_color}">{stats['pass_rate']:.1f}%</div>
                    <div class="stat-label">Pass Rate</div>
                </div>

                <div class="stat-card">
                    <div class="stat-value">{stats['performance_comparisons']}</div>
                    <div class="stat-label">Performance Comparisons</div>
                </div>
            </div>

            {self._generate_alerts(stats)}

            <div class="chart-container">
                <canvas id="resultsChart" width="400" height="200"></canvas>
            </div>
        </section>"""

    def _generate_alerts(self, stats: Dict[str, Any]) -> str:
        """Generate alert messages based on statistics.

        Args:
            stats: Calculated statistics

        Returns:
            HTML alerts section
        """
        alerts = []

        # Overall status alert
        if stats["pass_rate"] >= 95:
            alerts.append(('success', '✅ Excellent compatibility! Python API and CLI show strong functional parity.'))
        elif stats["pass_rate"] >= 80:
            alerts.append(('warning', '⚠️ Good compatibility with some issues. Review failed tests for details.'))
        else:
            alerts.append(('danger', '❌ Compatibility concerns detected. Significant discrepancies found.'))

        # Performance alert
        if stats["performance_comparisons"] > 0:
            perf_rate = (stats["performance_within_threshold"] / stats["performance_comparisons"]) * 100
            if perf_rate >= 90:
                alerts.append(('success', f'✅ Performance is excellent! {perf_rate:.1f}% of tests meet the 110% performance threshold.'))
            elif perf_rate >= 70:
                alerts.append(('warning', f'⚠️ Performance needs attention. Only {perf_rate:.1f}% of tests meet the 110% threshold.'))
            else:
                alerts.append(('danger', f'❌ Performance issues detected. Only {perf_rate:.1f}% of tests meet the 110% threshold.'))

        # Generate HTML
        html = ""
        for alert_type, message in alerts:
            html += f'<div class="alert alert-{alert_type}">{message}</div>'

        return html

    def _generate_performance_section(self, stats: Dict[str, Any]) -> str:
        """Generate the performance analysis section.

        Args:
            stats: Calculated statistics

        Returns:
            HTML section for performance
        """
        return f"""
        <section class="section">
            <h2>Performance Analysis</h2>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{stats['avg_python_time']:.3f}</div>
                    <div class="stat-label">Avg Python API Time (ms)</div>
                </div>

                <div class="stat-card">
                    <div class="stat-value">{stats['avg_cli_time']:.3f}</div>
                    <div class="stat-label">Avg CLI Time (ms)</div>
                </div>

                <div class="stat-card">
                    <div class="stat-value">{(stats['avg_python_time'] / max(stats['avg_cli_time'], 0.001)):.2f}x</div>
                    <div class="stat-label">Performance Ratio (Python/CLI)</div>
                </div>
            </div>

            <div class="chart-container">
                <canvas id="performanceChart" width="400" height="200"></canvas>
            </div>

            <div class="chart-container">
                <canvas id="categoryChart" width="400" height="300"></canvas>
            </div>
        </section>"""

    def _generate_test_results_section(self, test_suite: CompatibilityTestSuite) -> str:
        """Generate the detailed test results section.

        Args:
            test_suite: Test suite results

        Returns:
            HTML section for test results
        """
        # Group tests by category
        categorized_results = {}
        for test_result in test_suite.test_results:
            category = test_result.category.value if test_result.category else "Unknown"
            if category not in categorized_results:
                categorized_results[category] = []
            categorized_results[category].append(test_result)

        html = """
        <section class="section">
            <h2>Detailed Test Results</h2>

            <table>
                <thead>
                    <tr>
                        <th>Test Name</th>
                        <th>Category</th>
                        <th>Status</th>
                        <th>Python Time (ms)</th>
                        <th>CLI Time (ms)</th>
                        <th>Performance Ratio</th>
                    </tr>
                </thead>
                <tbody>
        """

        for test_result in test_suite.test_results:
            status_class = f"status-{test_result.status.lower()}"

            python_time = ""
            cli_time = ""
            perf_ratio = ""

            if test_result.performance_metrics:
                perf = test_result.performance_metrics
                python_time = f"{perf.python_execution_time:.3f}" if perf.python_execution_time else ""
                cli_time = f"{perf.cli_execution_time:.3f}" if perf.cli_execution_time else ""
                perf_ratio = f"{perf.performance_ratio:.2f}x" if perf.performance_ratio else ""

            html += f"""
                    <tr>
                        <td>{test_result.test_name}</td>
                        <td>{test_result.category.value if test_result.category else "Unknown"}</td>
                        <td class="{status_class}">{test_result.status}</td>
                        <td>{python_time}</td>
                        <td>{cli_time}</td>
                        <td>{perf_ratio}</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>
        </section>"""

        return html

    def _generate_details_section(self, test_suite: CompatibilityTestSuite) -> str:
        """Generate the test details section with expandable content.

        Args:
            test_suite: Test suite results

        Returns:
            HTML section for test details
        """
        html = """
        <section class="section">
            <h2>Test Execution Details</h2>
        """

        for test_result in test_suite.test_results:
            status_class = f"status-{test_result.status.lower()}"

            html += f"""
            <div class="expandable" onclick="toggleSection(this)">
                <h3 class="{status_class}">{test_result.test_name} - {test_result.status}</h3>
            </div>

            <div class="collapsible-content">
                <p><strong>Category:</strong> {test_result.category.value if test_result.category else "Unknown"}</p>
                <p><strong>Python Method:</strong> {test_result.python_method}</p>
                <p><strong>CLI Command:</strong> {test_result.cli_command}</p>

                {self._generate_test_execution_details(test_result)}
            </div>
            """

        html += """
        </section>"""

        return html

    def _generate_test_execution_details(self, test_result: TestResult) -> str:
        """Generate detailed information for a single test result.

        Args:
            test_result: Single test result

        Returns:
            HTML for test details
        """
        details = []

        # Add data file information
        if test_result.data_file:
            details.append(f"<p><strong>Data File:</strong> {test_result.data_file}</p>")

        # Add test parameters
        if test_result.parameters:
            details.append("<h4>Test Parameters:</h4>")
            details.append('<div class="code-block">')
            for key, value in test_result.parameters.items():
                details.append(f"{key}: {value}")
            details.append('</div>')

        # Add error information if failed
        if test_result.error_message:
            details.append('<h4>Error Details:</h4>')
            details.append(f'<div class="alert alert-danger">{test_result.error_message}</div>')

        # Add output differences
        if test_result.output_differences:
            details.append("<h4>Output Differences:</h4>")
            for diff in test_result.output_differences:
                details.append(f'<p><strong>{diff.get("field", "Unknown")}:</strong> {diff.get("description", "No description")}</p>')

        # Add performance metrics
        if test_result.performance_metrics:
            perf = test_result.performance_metrics
            details.append("<h4>Performance Metrics:</h4>")
            details.append("<table>")
            details.append(f"<tr><td>Python Execution Time</td><td>{perf.python_execution_time:.3f} ms</td></tr>")
            details.append(f"<tr><td>CLI Execution Time</td><td>{perf.cli_execution_time:.3f} ms</td></tr>")
            details.append(f"<tr><td>Performance Ratio</td><td>{perf.performance_ratio:.2f}x</td></tr>")
            if perf.python_memory_mb:
                details.append(f"<tr><td>Python Memory Usage</td><td>{perf.python_memory_mb:.2f} MB</td></tr>")
            if perf.cli_memory_mb:
                details.append(f"<tr><td>CLI Memory Usage</td><td>{perf.cli_memory_mb:.2f} MB</td></tr>")
            details.append("</table>")

        # Add test execution info
        if test_result.test_execution:
            exec_info = test_result.test_execution
            details.append("<h4>Execution Information:</h4>")
            details.append("<table>")
            details.append(f"<tr><td>Execution ID</td><td>{exec_info.execution_id}</td></tr>")
            details.append(f"<tr><td>Timestamp</td><td>{exec_info.timestamp}</td></tr>")
            details.append(f"<tr><td>Host</td><td>{exec_info.hostname}</td></tr>")
            if exec_info.python_version:
                details.append(f"<tr><td>Python Version</td><td>{exec_info.python_version}</td></tr>")
            if exec_info.rustkmer_version:
                details.append(f"<tr><td>RustKmer Version</td><td>{exec_info.rustkmer_version}</td></tr>")
            details.append("</table>")

        return "\n".join(details)

    def _generate_appendix_section(self, test_suite: CompatibilityTestSuite) -> str:
        """Generate the appendix with additional information.

        Args:
            test_suite: Test suite results

        Returns:
            HTML section for appendix
        """
        html = """
        <section class="section">
            <h2>Appendix</h2>

            <h3>Test Environment</h3>
            <table>
                <tr><th>Property</th><th>Value</th></tr>
        """

        env_info = test_suite.environment_info
        for key, value in env_info.items():
            html += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"

        html += """
            </table>

            <h3>Test Methodology</h3>
            <p>This compatibility test validates functional parity between the RustKmer CLI and Python API by:</p>
            <ul>
                <li>Executing equivalent operations using both interfaces</li>
                <li>Comparing output values for exact matches</li>
                <li>Measuring and comparing performance metrics</li>
                <li>Testing with real biological data of various sizes</li>
                <li>Validating error handling and edge cases</li>
            </ul>

            <h3>Performance Benchmark</h3>
            <p>Performance is measured by comparing execution times between the Python API and CLI. The Python API should perform within 110% of the CLI performance (performance ratio ≤ 1.10).</p>

            <h3>Exit Codes</h3>
            <table>
                <tr><th>Code</th><th>Meaning</th></tr>
                <tr><td>0</td><td>All tests passed successfully</td></tr>
                <tr><td>1</td><td>One or more tests failed</td></tr>
                <tr><td>2</td><td>Error in test execution or setup</td></tr>
            </table>
        </section>"""

        return html