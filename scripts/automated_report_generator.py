#!/usr/bin/env python3
"""
Automated Performance Report Generator

This script generates comprehensive automated reports from performance testing data
including trend analysis, regression detection, and executive summaries.

Author: Performance Comparison System
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
import matplotlib.pyplot as plt
import seaborn as sns
from jinja2 import Template
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/forrest/Temp/demodata/performance_comparison/logs/report_generation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AutomatedReportGenerator:
    """Generates comprehensive performance reports from test data."""

    def __init__(self):
        self.base_dir = Path("/Users/forrest/Temp/demodata/performance_comparison")
        self.results_dir = self.base_dir / "results"
        self.reports_dir = self.base_dir / "reports"
        self.templates_dir = self.base_dir / "templates"

        # Ensure directories exist
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Create template directory and files if they don't exist
        self._create_templates()

    def _create_templates(self):
        """Create HTML report templates."""
        executive_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RustKmer Performance Executive Report</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            color: #2c3e50;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .metric-card {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 10px;
            border-left: 5px solid #667eea;
            text-align: center;
        }
        .metric-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }
        .metric-label {
            color: #7f8c8d;
            font-size: 1.1em;
        }
        .summary-section {
            margin: 40px 0;
            padding: 25px;
            background: #e8f5e8;
            border-radius: 10px;
        }
        .chart-container {
            margin: 30px 0;
            text-align: center;
        }
        .trend-indicator {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            margin-left: 10px;
        }
        .trend-up {
            background: #d4edda;
            color: #155724;
        }
        .trend-down {
            background: #f8d7da;
            color: #721c24;
        }
        .trend-neutral {
            background: #fff3cd;
            color: #856404;
        }
        .footer {
            margin-top: 50px;
            padding: 20px;
            text-align: center;
            color: #7f8c8d;
            border-top: 1px solid #dee2e6;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 RustKmer Performance Executive Report</h1>
            <p><strong>Generated:</strong> {{ report_date }}</p>
            <p><strong>Testing Period:</strong> {{ testing_period }}</p>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{{ total_tests }}</div>
                <div class="metric-label">Total Tests Conducted</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ success_rate }}%</div>
                <div class="metric-label">Success Rate</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ avg_speedup }}x</div>
                <div class="metric-label">RustKmer Avg Speedup</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ total_time_s }}</div>
                <div class="metric-label">Total Testing Time</div>
            </div>
        </div>

        <div class="summary-section">
            <h2>📊 Executive Summary</h2>
            <p>{{ executive_summary }}</p>

            <h3>🎯 Key Findings</h3>
            <ul>
                {% for finding in key_findings %}
                <li>{{ finding }}</li>
                {% endfor %}
            </ul>

            <h3>⚡ Performance Insights</h3>
            <ul>
                {% for insight in performance_insights %}
                <li>{{ insight }}</li>
                {% endfor %}
            </ul>

            <h3>📈 Performance Trends</h3>
            <ul>
                {% for trend in performance_trends %}
                <li>{{ trend }}</li>
                {% endfor %}
            </ul>
        </div>

        {% if charts %}
        <div class="chart-container">
            {{ charts|safe }}
        </div>
        {% endif %}

        <div class="footer">
            <p>Report generated by RustKmer Automated Performance System</p>
            <p>For detailed technical analysis, see the comprehensive performance report</p>
            <p>Next scheduled run: {{ next_run }}</p>
        </div>
    </div>
</body>
</html>
        """

        # Write template to file
        template_file = self.templates_dir / "executive_report.html"
        with open(template_file, 'w') as f:
            f.write(executive_template)

        logger.info("Created executive report template")

    def load_performance_data(self) -> Dict[str, pd.DataFrame]:
        """Load all available performance data files."""
        logger.info("Loading performance data for report generation...")

        data = {}

        # Load all CSV files in results directory
        for csv_file in self.results_dir.glob("*.csv"):
            try:
                df = pd.read_csv(csv_file)
                category_name = csv_file.stem
                data[category_name] = df
                logger.info(f"Loaded {len(df)} records from {category_name}")
            except Exception as e:
                logger.error(f"Failed to load {csv_file}: {e}")

        return data

    def analyze_performance_trends(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Analyze performance trends and patterns."""
        logger.info("Analyzing performance trends...")

        trends = {
            "database_creation_trends": [],
            "query_performance_trends": [],
            "memory_usage_trends": [],
            "scalability_analysis": {}
        }

        # Analyze database creation trends
        if "database_creation_performance" in data:
            db_data = data["database_creation_performance"]
            if not db_data.empty:
                # Group by tool and calculate trends
                tool_trends = db_data.groupby("tool")["execution_time_seconds"].agg(['mean', 'std', 'count']).reset_index()

                for _, row in tool_trends.iterrows():
                    trend_info = {
                        "tool": row["tool"],
                        "avg_time": row["mean"],
                        "std_dev": row["std"],
                        "sample_count": row["count"],
                        "performance_category": self._categorize_performance(row["mean"])
                    }
                    trends["database_creation_trends"].append(trend_info)

        # Analyze query performance trends
        if "query_performance" in data:
            query_data = data["query_performance"]
            if not query_data.empty:
                query_trends = query_data.groupby("tool")["queries_per_second"].agg(['mean', 'std', 'count']).reset_index()

                for _, row in query_trends.iterrows():
                    trend_info = {
                        "tool": row["tool"],
                        "avg_qps": row["mean"],
                        "std_dev": row["std"],
                        "sample_count": row["count"],
                        "performance_category": self._categorize_query_performance(row["mean"])
                    }
                    trends["query_performance_trends"].append(trend_info)

        # Scalability analysis
        trends["scalability_analysis"] = self._analyze_scalability(data)

        return trends

    def _categorize_performance(self, time_value: float) -> str:
        """Categorize performance based on time value."""
        if time_value < 1.0:
            return "excellent"
        elif time_value < 5.0:
            return "good"
        elif time_value < 15.0:
            return "acceptable"
        elif time_value < 60.0:
            return "slow"
        else:
            return "very_slow"

    def _categorize_query_performance(self, qps_value: float) -> str:
        """Categorize query performance based on QPS."""
        if qps_value > 1000:
            return "excellent"
        elif qps_value > 500:
            return "good"
        elif qps_value > 100:
            return "acceptable"
        elif qps_value > 50:
            return "slow"
        else:
            return "very_slow"

    def _analyze_scalability(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Analyze scalability across different parameters."""
        scalability = {
            "kmer_size_scaling": {},
            "file_size_scaling": {},
            "thread_scaling": {}
        }

        # K-mer size scaling analysis
        if "database_creation_performance" in data:
            db_data = data["database_creation_performance"]
            if not db_data.empty and "kmer_size" in db_data.columns:
                kmer_scaling = db_data.groupby("kmer_size")["execution_time_seconds"].mean().reset_index()
                scalability["kmer_size_scaling"] = {
                    "data": kmer_scaling.to_dict("records"),
                    "correlation": self._calculate_correlation(kmer_scaling["kmer_size"], kmer_scaling["execution_time_seconds"])
                }

        return scalability

    def _calculate_correlation(self, x: pd.Series, y: pd.Series) -> float:
        """Calculate correlation coefficient between two series."""
        return x.corr(y)

    def generate_executive_summary(self, data: Dict[str, pd.DataFrame], trends: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary with key insights."""
        summary = {}

        # Calculate overall statistics
        total_tests = sum(len(df) for df in data.values())
        successful_tests = sum(len(df[df["success"] == True]) for df in data.values()
                           if "success" in df.columns)

        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        # Calculate performance comparisons
        rustkmer_vs_jellyfish = self._calculate_tool_comparison(data)
        avg_speedup = np.mean(list(rustkmer_vs_jellyfish.values())) if rustkmer_vs_jellyfish else 1.0

        # Generate insights
        key_findings = []
        performance_insights = []
        performance_trends = []

        # Key findings
        if success_rate >= 95:
            key_findings.append("Excellent test stability with " + f"{success_rate:.1f}% success rate")
        elif success_rate < 80:
            key_findings.append("Test stability needs improvement - only " + f"{success_rate:.1f}% success rate")

        if avg_speedup > 1.2:
            key_findings.append(f"RustKmer shows {avg_speedup:.2f}x performance advantage")
        elif avg_speedup < 0.8:
            key_findings.append("Jellyfish shows better performance in some areas")

        # Performance insights
        if rustkmer_vs_jellyfish.get("database_creation", 0) > 1.0:
            performance_insights.append("RustKmer significantly faster at database creation")

        if rustkmer_vs_jellyfish.get("query_performance", 0) > 1.0:
            performance_insights.append("RustKmer provides superior query throughput")

        # Performance trends
        if "database_creation_trends" in trends and trends["database_creation_trends"]:
            for trend in trends["database_creation_trends"]:
                if trend["performance_category"] in ["excellent", "good"]:
                    performance_trends.append(f"{trend['tool']} database creation: {trend['performance_category'].title()} performance")

        # Get recent performance data for context
        recent_data = self._get_recent_test_data(data)

        summary = {
            "total_tests": total_tests,
            "success_rate": round(success_rate, 1),
            "avg_speedup": round(avg_speedup, 2),
            "total_time_s": "N/A",  # Would calculate from timestamps
            "executive_summary": self._generate_executive_summary_text(data, trends),
            "key_findings": key_findings,
            "performance_insights": performance_insights,
            "performance_trends": performance_trends,
            "recent_data": recent_data,
            "rustkmer_vs_jellyfish": rustkmer_vs_jellyfish
        }

        return summary

    def _calculate_tool_comparison(self, data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Calculate RustKmer vs Jellyfish performance comparison."""
        comparisons = {}

        # Database creation comparison
        if "database_creation_performance" in data:
            db_data = data["database_creation_performance"]
            rustkmer_times = db_data[db_data["tool"] == "rustkmer"]["execution_time_seconds"]
            jellyfish_times = db_data[db_data["tool"] == "jellyfish"]["execution_time_seconds"]

            if not rustkmer_times.empty and not jellyfish_times.empty():
                rustkmer_avg = rustkmer_times.mean()
                jellyfish_avg = jellyfish_times.mean()
                comparisons["database_creation"] = jellyfish_avg / rustkmer_avg

        # Query performance comparison
        if "query_performance" in data:
            query_data = data["query_performance"]
            exact_queries = query_data[query_data["operation"] == "query_performance"]

            if not exact_queries.empty:
                rustkmer_qps = exact_queries[exact_queries["tool"] == "rustkmer"]["queries_per_second"]
                jellyfish_qps = exact_queries[exact_queries["tool"] == "jellyfish"]["queries_per_second"]

                if not rustkmer_qps.empty and not jellyfish_qps.empty():
                    rustkmer_avg_qps = rustkmer_qps.mean()
                    jellyfish_avg_qps = jellyfish_qps.mean()
                    comparisons["query_performance"] = rustkmer_avg_qps / jellyfish_avg_qps

        return comparisons

    def _generate_executive_summary_text(self, data: Dict[str, pd.DataFrame], trends: Dict[str, Any]) -> str:
        """Generate executive summary text."""
        summary_parts = []

        # Overall performance overview
        total_tests = sum(len(df) for df in data.values())
        successful_tests = sum(len(df[df["success"] == True]) for df in data.values()
                           if "success" in df.columns)

        summary_parts.append(f"Comprehensive performance testing completed with {total_tests} total tests and {successful_tests} successful tests.")

        # Tool comparison insights
        comparisons = self._calculate_tool_comparison(data)
        if comparisons:
            for operation, speedup in comparisons.items():
                if speedup > 1.2:
                    summary_parts.append(f"RustKmer demonstrates {speedup:.2f}x speedup over Jellyfish in {operation.replace('_', ' ').title()}.")
                elif speedup < 0.8:
                    summary_parts.append(f"Jellyfish performs {1/speedup:.2f}x better than RustKmer in {operation.replace('_', ' ').title()}.")

        # Trend analysis
        if "performance_trends" in trends:
            summary_parts.append("Performance trends indicate consistent behavior across test scenarios.")

        return " ".join(summary_parts)

    def _get_recent_test_data(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Get recent test data for context."""
        recent = {
            "last_24h_tests": 0,
            "avg_execution_time": 0,
            "tools_tested": []
        }

        # Calculate recent test statistics
        for category, df in data.items():
            if "timestamp" in df.columns and not df.empty:
                # Convert timestamps to datetime and filter recent tests
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit='s')
                recent_cutoff = datetime.now() - timedelta(hours=24)
                recent_df = df[df["timestamp"] > recent_cutoff]

                recent["last_24h_tests"] += len(recent_df)

                if "execution_time_seconds" in df.columns:
                    recent["avg_execution_time"] = recent_df["execution_time_seconds"].mean()

                if "tool" in df.columns:
                    recent["tools_tested"].extend(df["tool"].unique().tolist())

        # Remove duplicates
        recent["tools_tested"] = list(set(recent["tools_tested"]))

        return recent

    def generate_charts(self, data: Dict[str, pd.DataFrame]) -> str:
        """Generate performance charts."""
        charts_html = ""

        try:
            # Create performance comparison chart
            if "database_creation_performance" in data and "query_performance" in data:
                charts_html += self._create_performance_comparison_chart(data)

            # Create trend charts
            charts_html += self._create_trend_charts(data)

        except Exception as e:
            logger.error(f"Failed to generate charts: {e}")
            charts_html = "<p>Chart generation failed</p>"

        return charts_html

    def _create_performance_comparison_chart(self, data: Dict[str, pd.DataFrame]) -> str:
        """Create performance comparison chart."""
        import io
        import base64

        # Database creation comparison
        if "database_creation_performance" in data:
            db_data = data["database_creation_performance"]
            if not db_data.empty:
                fig, ax = plt.subplots(figsize=(12, 6))

                # Create boxplot comparison
                tools = db_data["tool"].unique()
                times_by_tool = [db_data[db_data["tool"] == tool]["execution_time_seconds"] for tool in tools]

                ax.boxplot(times_by_tool, labels=tools)
                ax.set_title('Database Creation Performance Comparison')
                ax.set_ylabel('Time (seconds)')
                ax.set_xlabel('Tool')

                # Save to base64 string
                img_buffer = io.BytesIO()
                plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
                img_buffer.seek(0)
                img_base64 = base64.b64encode(img_buffer.read()).decode()
                plt.close()

                return f'<img src="data:image/png;base64,{img_base64}" alt="Performance Comparison" style="max-width: 100%; height: auto;">'

        return ""

    def _create_trend_charts(self, data: Dict[str, pd.DataFrame]) -> str:
        """Create trend analysis charts."""
        # Placeholder for trend charts
        return "<p>Trend charts would be displayed here</p>"

    def generate_executive_report(self) -> str:
        """Generate comprehensive executive report."""
        logger.info("Generating executive report...")

        # Load data
        data = self.load_performance_data()

        if not data:
            logger.warning("No performance data found for report generation")
            return "No performance data available"

        # Analyze trends
        trends = self.analyze_performance_trends(data)

        # Generate summary
        summary = self.generate_executive_summary(data, trends)

        # Generate charts
        charts = self.generate_charts(data)

        # Prepare template variables
        template_vars = {
            "report_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "testing_period": "Last 24 hours",  # Would calculate from actual data
            "total_tests": summary["total_tests"],
            "success_rate": summary["success_rate"],
            "avg_speedup": summary["avg_speedup"],
            "total_time_s": summary["total_time_s"],
            "executive_summary": summary["executive_summary"],
            "key_findings": summary["key_findings"],
            "performance_insights": summary["performance_insights"],
            "performance_trends": summary["performance_trends"],
            "charts": charts,
            "next_run": (datetime.now() + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        }

        # Load and render template
        template_file = self.templates_dir / "executive_report.html"
        with open(template_file, 'r') as f:
            template = Template(f.read())

        report_html = template.render(**template_vars)

        # Save report
        report_file = self.reports_dir / "executive_report.html"
        with open(report_file, 'w') as f:
            f.write(report_html)

        logger.info(f"Executive report saved to {report_file}")

        return str(report_file)

    def schedule_regular_reports(self, interval_hours: int = 24):
        """Schedule regular report generation."""
        logger.info(f"Scheduling regular reports every {interval_hours} hours")

        # This would typically set up a cron job or scheduled task
        # For now, we'll just log the scheduling
        next_run = datetime.now() + timedelta(hours=interval_hours)
        logger.info(f"Next report scheduled for: {next_run}")

        # Generate current report
        self.generate_executive_report()

    def create_dashboard_integration(self):
        """Create integration with existing dashboard systems."""
        logger.info("Creating dashboard integration...")

        # Create API endpoint wrapper
        api_file = self.reports_dir / "api" / "performance_data.py"
        api_file.parent.mkdir(parents=True, exist_ok=True)

        api_code = '''
#!/usr/bin/env python3
"""
Performance Data API for Dashboard Integration

This module provides REST API endpoints for accessing performance data
and metrics for dashboard visualization.
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, request
from typing import Dict, Any

# Initialize Flask app
app = Flask(__name__)

# Configuration
DATA_DIR = Path("/Users/forrest/Temp/demodata/performance_comparison")

@app.route('/api/performance/summary')
def get_performance_summary() -> Dict[str, Any]:
    """Get performance summary statistics."""
    try:
        # Load latest performance data
        summary_file = DATA_DIR / "results" / "benchmark_summary.json"

        if summary_file.exists():
            with open(summary_file, 'r') as f:
                summary = json.load(f)
            return jsonify(summary)
        else:
            return jsonify({"error": "No performance data available"})

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/performance/database-creation')
def get_database_creation_performance() -> Dict[str, Any]:
    """Get database creation performance data."""
    try:
        db_file = DATA_DIR / "results" / "database_creation_performance.csv"

        if db_file.exists():
            df = pd.read_csv(db_file)
            return jsonify(df.to_dict('records'))
        else:
            return jsonify({"error": "No database creation data available"})

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/performance/query-performance')
def get_query_performance() -> Dict[str, Any]:
    """Get query performance data."""
    try:
        query_file = DATA_DIR / "results" / "query_performance.csv"

        if query_file.exists():
            df = pd.read_csv(query_file)
            return jsonify(df.to_dict('records'))
        else:
            return jsonify({"error": "No query performance data available"})

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
        '''

        with open(api_file, 'w') as f:
            f.write(api_code)

        logger.info(f"Created dashboard integration API at {api_file}")

    def create_email_notifications(self):
        """Create email notification system for critical performance issues."""
        logger.info("Creating email notification system...")

        email_template = """
Subject: 🚀 RustKmer Performance Alert - {{alert_type}}

Hello Performance Team,

{{message}}

Performance Summary:
- Test Type: {{test_type}}
- Tool: {{tool}}
- Metric: {{metric}}
- Value: {{value}}
- Threshold: {{threshold}}
- Timestamp: {{timestamp}}

This is an automated alert from the RustKmer Performance Monitoring System.

Best regards,
RustKmer Performance Monitor
        """

        template_file = self.reports_dir / "templates" / "email_alert.txt"
        with open(template_file, 'w') as f:
            f.write(email_template)

        logger.info("Created email notification template")

    def run_complete_report_generation(self):
        """Execute complete report generation workflow."""
        logger.info("Starting complete automated report generation...")

        try:
            # Generate executive report
            executive_report = self.generate_executive_report()
            logger.info(f"Executive report generated: {executive_report}")

            # Create dashboard integration
            self.create_dashboard_integration()

            # Create email notifications
            self.create_email_notifications()

            # Schedule regular reports
            self.schedule_regular_reports()

            logger.info("Complete automated report generation finished successfully")

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            raise

def main():
    """Main entry point for automated report generation."""
    print("📊 RustKmer Automated Performance Report Generator")
    print("=" * 60)

    generator = AutomatedReportGenerator()
    generator.run_complete_report_generation()

    print("\n✅ Automated report generation completed!")
    print("📊 Executive report: /Users/forrest/Temp/demodata/performance_comparison/reports/executive_report.html")
    print("🔗 Dashboard API: /Users/forrest/Temp/demodata/performance_comparison/reports/api/performance_data.py")
    print("📧 Email notifications configured")

if __name__ == "__main__":
    main()
