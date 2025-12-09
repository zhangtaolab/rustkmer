#!/usr/bin/env python3
"""
Automated compatibility report generation for RustKmer

This module automatically generates, aggregates, and publishes compatibility test reports
across multiple platforms, Python versions, and test runs.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from email.mime.base import MimeBase
from email import encoders
import jinja2

# Import reporting modules
from reporting import ReportGenerator, ResultComparator
from runner import CompatibilityTestRunner


class CompatibilityReportAggregator:
    """Aggregate compatibility test results from multiple sources"""

    def __init__(self, reports_dir: str = "compatibility_reports"):
        """
        Initialize report aggregator

        Args:
            reports_dir: Directory containing compatibility test reports
        """
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(exist_ok=True)
        self.aggregated_dir = self.reports_dir / "aggregated"
        self.aggregated_dir.mkdir(exist_ok=True)

    def aggregate_reports(self, pattern: str = "compatibility_report_*.json") -> Dict[str, Any]:
        """
        Aggregate all compatibility test reports

        Args:
            pattern: Pattern to match report files

        Returns:
            Aggregated report data
        """
        reports = list(self.reports_dir.glob(pattern))
        if not reports:
            return {"error": "No reports found", "pattern": pattern}

        # Initialize aggregated data structure
        aggregated = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "report_count": len(reports),
                "date_range": None,
                "platforms": set(),
                "python_versions": set(),
                "git_commits": set()
            },
            "summary": {
                "total_tests": 0,
                "total_passed": 0,
                "total_failed": 0,
                "pass_rate": 0,
                "platform_stats": {},
                "python_version_stats": {}
            },
            "results": {
                "by_platform": {},
                "by_python_version": {},
                "by_test": {},
                "all": {}
            },
            "performance": {
                "by_platform": {},
                "by_python_version": {},
                "trends": {}
            },
            "issues": []
        }

        # Process each report
        all_timestamps = []
        for report_path in reports:
            try:
                with open(report_path, 'r') as f:
                    report_data = json.load(f)

                # Extract metadata from filename
                filename = report_path.stem.replace("compatibility_report_", "")
                parts = filename.split("_")
                platform = parts[0] if len(parts) > 0 else "unknown"
                python_version = parts[1] if len(parts) > 1 else "unknown"

                # Update metadata
                aggregated["metadata"]["platforms"].add(platform)
                aggregated["metadata"]["python_versions"].add(python_version)

                # Extract timestamp if available
                if 'timestamp' in report_data.get('summary', {}):
                    ts = datetime.fromisoformat(report_data['summary']['timestamp'])
                    all_timestamps.append(ts)

                # Update summary
                summary = report_data.get('summary', {})
                aggregated["summary"]["total_tests"] += summary.get('total_tests', 0)
                aggregated["summary"]["total_passed"] += summary.get('passed', 0)
                aggregated["summary"]["total_failed"] += summary.get('failed', 0)

                # Store results by platform
                if platform not in aggregated["results"]["by_platform"]:
                    aggregated["results"]["by_platform"][platform] = {}
                aggregated["results"]["by_platform"][platform].update(report_data.get('results', {}))

                # Store results by Python version
                if python_version not in aggregated["results"]["by_python_version"]:
                    aggregated["results"]["by_python_version"][python_version] = {}
                aggregated["results"]["by_python_version"][python_version].update(report_data.get('results', {}))

                # Store all results with unique keys
                for test_name, result in report_data.get('results', {}).items():
                    unique_key = f"{platform}_{python_version}_{test_name}"
                    aggregated["results"]["all"][unique_key] = result

                    # Store by test name
                    if test_name not in aggregated["results"]["by_test"]:
                        aggregated["results"]["by_test"][test_name] = []
                    aggregated["results"]["by_test"][test_name].append({
                        "platform": platform,
                        "python_version": python_version,
                        "result": result
                    })

                # Collect issues
                for failed_test in report_data.get('failed_tests', []):
                    failed_test['platform'] = platform
                    failed_test['python_version'] = python_version
                    aggregated["issues"].append(failed_test)

            except Exception as e:
                print(f"Error processing report {report_path}: {e}")

        # Calculate derived statistics
        if aggregated["summary"]["total_tests"] > 0:
            aggregated["summary"]["pass_rate"] = (
                aggregated["summary"]["total_passed"] / aggregated["summary"]["total_tests"] * 100
            )

        # Update date range
        if all_timestamps:
            aggregated["metadata"]["date_range"] = {
                "start": min(all_timestamps).isoformat(),
                "end": max(all_timestamps).isoformat()
            }

        # Convert sets to lists for JSON serialization
        aggregated["metadata"]["platforms"] = list(aggregated["metadata"]["platforms"])
        aggregated["metadata"]["python_versions"] = list(aggregated["metadata"]["python_versions"])

        # Calculate platform-specific statistics
        for platform in aggregated["metadata"]["platforms"]:
            platform_results = aggregated["results"]["by_platform"].get(platform, {})
            platform_passed = sum(1 for r in platform_results.values() if r.get('passed', False))
            platform_total = len(platform_results)
            platform_rate = (platform_passed / platform_total * 100) if platform_total > 0 else 0

            aggregated["summary"]["platform_stats"][platform] = {
                "total": platform_total,
                "passed": platform_passed,
                "failed": platform_total - platform_passed,
                "pass_rate": platform_rate
            }

        # Calculate Python version specific statistics
        for py_ver in aggregated["metadata"]["python_versions"]:
            py_results = aggregated["results"]["by_python_version"].get(py_ver, {})
            py_passed = sum(1 for r in py_results.values() if r.get('passed', False))
            py_total = len(py_results)
            py_rate = (py_passed / py_total * 100) if py_total > 0 else 0

            aggregated["summary"]["python_version_stats"][py_ver] = {
                "total": py_total,
                "passed": py_passed,
                "failed": py_total - py_passed,
                "pass_rate": py_rate
            }

        # Save aggregated report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        aggregated_path = self.aggregated_dir / f"aggregated_report_{timestamp}.json"
        with open(aggregated_path, 'w') as f:
            json.dump(aggregated, f, indent=2)

        # Also save as latest
        latest_path = self.aggregated_dir / "latest_aggregated_report.json"
        shutil.copy2(aggregated_path, latest_path)

        return aggregated

    def generate_html_dashboard(self, aggregated_data: Dict[str, Any]) -> str:
        """
        Generate HTML dashboard from aggregated data

        Args:
            aggregated_data: Aggregated report data

        Returns:
            Path to generated HTML dashboard
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = self.aggregated_dir / f"dashboard_{timestamp}.html"

        # Use Jinja2 template for HTML generation
        template_str = self._get_dashboard_template()
        template = jinja2.Template(template_str)

        # Prepare data for template
        summary = aggregated_data.get("summary", {})
        metadata = aggregated_data.get("metadata", {})
        issues = aggregated_data.get("issues", [])

        # Generate platform table data
        platform_rows = []
        for platform, stats in summary.get("platform_stats", {}).items():
            platform_rows.append({
                "name": platform,
                "total": stats["total"],
                "passed": stats["passed"],
                "failed": stats["failed"],
                "pass_rate": f"{stats['pass_rate']:.1f}%",
                "status": "✅" if stats["pass_rate"] >= 95 else "⚠️" if stats["pass_rate"] >= 80 else "❌"
            })

        # Generate Python version table data
        py_rows = []
        for py_ver, stats in summary.get("python_version_stats", {}).items():
            py_rows.append({
                "version": py_ver,
                "total": stats["total"],
                "passed": stats["passed"],
                "failed": stats["failed"],
                "pass_rate": f"{stats['pass_rate']:.1f}%",
                "status": "✅" if stats["pass_rate"] >= 95 else "⚠️" if stats["pass_rate"] >= 80 else "❌"
            })

        # Render template
        html_content = template.render(
            metadata=metadata,
            summary=summary,
            platform_rows=platform_rows,
            py_rows=py_rows,
            issues=issues,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        )

        with open(html_path, 'w') as f:
            f.write(html_content)

        # Also save as latest dashboard
        latest_path = self.aggregated_dir / "latest_dashboard.html"
        shutil.copy2(html_path, latest_path)

        return str(html_path)

    def _get_dashboard_template(self) -> str:
        """Get Jinja2 template for HTML dashboard"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RustKmer Compatibility Dashboard</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
        }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #fafafa;
        }
        .summary-card {
            background: white;
            padding: 20px;
            border-radius: 6px;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .summary-card h3 {
            margin: 0 0 10px 0;
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
        }
        .summary-card .value {
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }
        .summary-card .value.pass { color: #4CAF50; }
        .summary-card .value.fail { color: #f44336; }
        .content {
            padding: 30px;
        }
        .section {
            margin-bottom: 40px;
        }
        .section h2 {
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th {
            background: #f8f8f8;
            font-weight: 600;
            color: #666;
        }
        .status-ok { color: #4CAF50; }
        .status-warn { color: #ff9800; }
        .status-error { color: #f44336; }
        .issues {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 4px;
            padding: 15px;
        }
        .issue {
            margin-bottom: 10px;
            padding: 10px;
            background: white;
            border-radius: 4px;
            border-left: 4px solid #f44336;
        }
        .issue-code {
            font-family: monospace;
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
        }
        .footer {
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
            background: #f8f8f8;
        }
        .alert {
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .alert-success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .alert-warning {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            color: #856404;
        }
        .alert-error {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>RustKmer Compatibility Dashboard</h1>
            <p>CLI-Python API Compatibility Test Results</p>
            <p>Generated: {{ timestamp }}</p>
        </div>

        <div class="summary">
            <div class="summary-card">
                <h3>Total Tests</h3>
                <div class="value">{{ summary.total_tests }}</div>
            </div>
            <div class="summary-card">
                <h3>Passed</h3>
                <div class="value pass">{{ summary.total_passed }}</div>
            </div>
            <div class="summary-card">
                <h3>Failed</h3>
                <div class="value fail">{{ summary.total_failed }}</div>
            </div>
            <div class="summary-card">
                <h3>Pass Rate</h3>
                <div class="value {% if summary.pass_rate >= 95 %}pass{% elif summary.pass_rate >= 80 %}pass{% else %}fail{% endif %}">
                    {{ "%.1f"|format(summary.pass_rate) }}%
                </div>
            </div>
        </div>

        <div class="content">
            {% if summary.pass_rate >= 95 %}
            <div class="alert alert-success">
                ✅ Excellent compatibility! All tests are passing with high success rate.
            </div>
            {% elif summary.pass_rate >= 80 %}
            <div class="alert alert-warning">
                ⚠️ Some compatibility issues detected. Review failed tests below.
            </div>
            {% else %}
            <div class="alert alert-error">
                🚨 Critical compatibility issues! Multiple tests are failing.
            </div>
            {% endif %}

            <div class="section">
                <h2>Results by Platform</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Platform</th>
                            <th>Total</th>
                            <th>Passed</th>
                            <th>Failed</th>
                            <th>Pass Rate</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for row in platform_rows %}
                        <tr>
                            <td>{{ row.name }}</td>
                            <td>{{ row.total }}</td>
                            <td>{{ row.passed }}</td>
                            <td>{{ row.failed }}</td>
                            <td>{{ row.pass_rate }}</td>
                            <td class="status-{{ 'ok' if row.status == '✅' else 'warn' if row.status == '⚠️' else 'error' }}">
                                {{ row.status }}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>

            <div class="section">
                <h2>Results by Python Version</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Python Version</th>
                            <th>Total</th>
                            <th>Passed</th>
                            <th>Failed</th>
                            <th>Pass Rate</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for row in py_rows %}
                        <tr>
                            <td>{{ row.version }}</td>
                            <td>{{ row.total }}</td>
                            <td>{{ row.passed }}</td>
                            <td>{{ row.failed }}</td>
                            <td>{{ row.pass_rate }}</td>
                            <td class="status-{{ 'ok' if row.status == '✅' else 'warn' if row.status == '⚠️' else 'error' }}">
                                {{ row.status }}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>

            {% if issues %}
            <div class="section">
                <h2>Issues ({{ issues|length }})</h2>
                <div class="issues">
                    {% for issue in issues[:10] %}
                    <div class="issue">
                        <strong>{{ issue.test }}</strong>
                        {% if issue.platform %} on {{ issue.platform }}{% endif %}
                        {% if issue.python_version %} (Python {{ issue.python_version }}){% endif %}
                        <br>
                        <span class="issue-code">{{ issue.issue }}</span>
                        {% if issue.details %}
                        <br><small>{{ issue.details[:100] }}{% if issue.details|length > 100 %}...{% endif %}</small>
                        {% endif %}
                    </div>
                    {% endfor %}
                    {% if issues|length > 10 %}
                    <p><em>Showing first 10 of {{ issues|length }} issues</em></p>
                    {% endif %}
                </div>
            </div>
            {% endif %}
        </div>

        <div class="footer">
            <p>RustKmer CLI-Python Compatibility Dashboard</p>
            <p>Reports: {{ metadata.report_count }} | Platforms: {{ metadata.platforms|length }} | Python Versions: {{ metadata.python_versions|length }}</p>
        </div>
    </div>
</body>
</html>
        """


class ReportPublisher:
    """Publish compatibility reports to various channels"""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize report publisher

        Args:
            config_file: Configuration file path with publishing settings
        """
        self.config = self._load_config(config_file)

    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """Load publishing configuration"""
        default_config = {
            "email": {
                "enabled": False,
                "smtp_server": "",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "from_address": "",
                "to_addresses": []
            },
            "webhook": {
                "enabled": False,
                "url": "",
                "secret": ""
            },
            "s3": {
                "enabled": False,
                "bucket": "",
                "region": "",
                "access_key": "",
                "secret_key": ""
            }
        }

        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    def publish_email_report(self, report_data: Dict[str, Any], report_files: List[str]) -> bool:
        """
        Send compatibility report via email

        Args:
            report_data: Aggregated report data
            report_files: List of report files to attach

        Returns:
            True if email was sent successfully
        """
        if not self.config["email"]["enabled"]:
            return False

        try:
            # Create message
            msg = MimeMultipart()
            msg['From'] = self.config["email"]["from_address"]
            msg['To'] = ", ".join(self.config["email"]["to_addresses"])
            msg['Subject'] = f"RustKmer Compatibility Report - {datetime.now().strftime('%Y-%m-%d')}"

            # Create HTML body
            html_body = self._create_email_html(report_data)
            msg.attach(MimeText(html_body, 'html'))

            # Attach report files
            for file_path in report_files:
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        part = MimeBase('application', "octet-stream")
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{os.path.basename(file_path)}"'
                    )
                    msg.attach(part)

            # Send email
            server = smtplib.SMTP(
                self.config["email"]["smtp_server"],
                self.config["email"]["smtp_port"]
            )
            server.starttls()
            server.login(
                self.config["email"]["username"],
                self.config["email"]["password"]
            )
            server.send_message(msg)
            server.quit()

            return True

        except Exception as e:
            print(f"Failed to send email report: {e}")
            return False

    def _create_email_html(self, report_data: Dict[str, Any]) -> str:
        """Create HTML email body"""
        summary = report_data.get("summary", {})
        metadata = report_data.get("metadata", {})

        return f"""
        <html>
        <body>
            <h2>RustKmer Compatibility Report</h2>
            <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Tests Run:</strong> {summary.get('total_tests', 0)}</p>
            <p><strong>Passed:</strong> {summary.get('total_passed', 0)}</p>
            <p><strong>Failed:</strong> {summary.get('total_failed', 0)}</p>
            <p><strong>Pass Rate:</strong> {summary.get('pass_rate', 0):.1f}%</p>

            <h3>Platform Results</h3>
            <table border="1" cellpadding="5" cellspacing="0">
                <tr><th>Platform</th><th>Total</th><th>Passed</th><th>Pass Rate</th></tr>
                {% for platform, stats in summary.get('platform_stats', {}).items() %}
                <tr>
                    <td>{{ platform }}</td>
                    <td>{{ stats.total }}</td>
                    <td>{{ stats.passed }}</td>
                    <td>{{ "%.1f"|format(stats.pass_rate) }}%</td>
                </tr>
                {% endfor %}
            </table>

            <p>See attached files for detailed reports.</p>
        </body>
        </html>
        """

    def publish_webhook(self, report_data: Dict[str, Any]) -> bool:
        """
        Send report data via webhook

        Args:
            report_data: Aggregated report data

        Returns:
            True if webhook was sent successfully
        """
        if not self.config["webhook"]["enabled"]:
            return False

        import requests

        try:
            payload = {
                "timestamp": datetime.now().isoformat(),
                "summary": report_data.get("summary", {}),
                "metadata": report_data.get("metadata", {})
            }

            headers = {
                "Content-Type": "application/json"
            }

            if self.config["webhook"]["secret"]:
                import hmac
                import hashlib
                signature = hmac.new(
                    self.config["webhook"]["secret"].encode(),
                    json.dumps(payload).encode(),
                    hashlib.sha256
                ).hexdigest()
                headers["X-Webhook-Signature"] = f"sha256={signature}"

            response = requests.post(
                self.config["webhook"]["url"],
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            return True

        except Exception as e:
            print(f"Failed to send webhook: {e}")
            return False


class AutomatedReporter:
    """Main automated reporter that ties everything together"""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize automated reporter

        Args:
            config_file: Optional configuration file
        """
        self.aggregator = CompatibilityReportAggregator()
        self.publisher = ReportPublisher(config_file)
        self.generator = ReportGenerator()

    def run_daily_report(self) -> Dict[str, Any]:
        """
        Run daily automated compatibility report

        Returns:
            Dictionary with report status and file paths
        """
        print("Starting automated compatibility report generation...")
        print("-" * 50)

        # Aggregate all reports
        print("Aggregating test reports...")
        aggregated_data = self.aggregator.aggregate_reports()

        if "error" in aggregated_data:
            print(f"❌ Error aggregating reports: {aggregated_data['error']}")
            return {"status": "error", "message": aggregated_data["error"]}

        print(f"✅ Aggregated {aggregated_data['metadata']['report_count']} reports")

        # Generate HTML dashboard
        print("Generating HTML dashboard...")
        dashboard_path = self.aggregator.generate_html_dashboard(aggregated_data)
        print(f"✅ Dashboard generated: {dashboard_path}")

        # Generate detailed report
        print("Generating detailed HTML report...")
        html_report = self.generator.generate_html_report(aggregated_data)
        print(f"✅ HTML report generated: {html_report}")

        print("Generating Markdown report...")
        md_report = self.generator.generate_markdown_report(aggregated_data)
        print(f"✅ Markdown report generated: {md_report}")

        # Generate performance plots
        print("Generating performance plots...")
        try:
            plots = self.generator.generate_performance_plots(aggregated_data.get("results", {}))
            print(f"✅ Generated {len(plots)} performance plots")
            for plot in plots:
                print(f"  - {plot}")
        except Exception as e:
            print(f"⚠️ Could not generate performance plots: {e}")
            plots = []

        # Publish reports
        report_files = [dashboard_path, html_report, md_report] + plots
        published = []

        # Email
        if self.publisher.publish_email_report(aggregated_data, report_files):
            published.append("email")
            print("✅ Email report sent")

        # Webhook
        if self.publisher.publish_webhook(aggregated_data):
            published.append("webhook")
            print("✅ Webhook notification sent")

        # Summary
        summary = aggregated_data.get("summary", {})
        print("\n" + "=" * 50)
        print("DAILY COMPATIBILITY REPORT SUMMARY")
        print("=" * 50)
        print(f"Total Tests: {summary.get('total_tests', 0)}")
        print(f"Passed: {summary.get('total_passed', 0)}")
        print(f"Failed: {summary.get('total_failed', 0)}")
        print(f"Pass Rate: {summary.get('pass_rate', 0):.1f}%")
        print(f"Published to: {', '.join(published) if published else 'None'}")

        return {
            "status": "success",
            "aggregated_data": aggregated_data,
            "dashboard": dashboard_path,
            "html_report": html_report,
            "markdown_report": md_report,
            "plots": plots,
            "published_to": published
        }


def main():
    """Main entry point for automated reporting"""
    import argparse

    parser = argparse.ArgumentParser(description="Generate automated compatibility reports")
    parser.add_argument(
        "--config",
        help="Configuration file for publishing settings"
    )
    parser.add_argument(
        "--pattern",
        default="compatibility_report_*.json",
        help="Pattern for report files to aggregate"
    )

    args = parser.parse_args()

    # Create automated reporter
    reporter = AutomatedReporter(config_file=args.config)

    # Run daily report
    result = reporter.run_daily_report()

    # Exit with appropriate code
    sys.exit(0 if result["status"] == "success" else 1)


if __name__ == "__main__":
    main()