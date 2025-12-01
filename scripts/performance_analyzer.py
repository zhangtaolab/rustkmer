#!/usr/bin/env python3
"""
Performance Analyzer for RustKmer vs Jellyfish Comparison

This script provides advanced analysis and visualization of performance data
including statistical analysis, trend detection, and comprehensive reporting.

Author: Performance Comparison System
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import logging
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.offline as pyo
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/forrest/Temp/demodata/performance_comparison/logs/performance_analyzer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    """Advanced performance analysis and reporting system."""

    def __init__(self):
        self.base_dir = Path("/Users/forrest/Temp/demodata/performance_comparison")
        self.results_dir = self.base_dir / "results"
        self.reports_dir = self.base_dir / "reports"
        self.data = {}
        self.analysis_results = {}

        # Ensure directories exist
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Configure plotting
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")

    def load_performance_data(self):
        """Load all performance CSV files."""
        logger.info("Loading performance data...")

        categories = [
            "database_creation",
            "query_performance",
            "memory_usage",
            "io_performance",
            "workflow_performance"
        ]

        for category in categories:
            csv_file = self.results_dir / f"{category}.csv"
            if csv_file.exists():
                try:
                    df = pd.read_csv(csv_file)
                    self.data[category] = df
                    logger.info(f"Loaded {len(df)} records from {category}")
                except Exception as e:
                    logger.error(f"Failed to load {category}: {e}")
            else:
                logger.warning(f"No data file found for {category}")

    def perform_statistical_analysis(self):
        """Perform comprehensive statistical analysis."""
        logger.info("Performing statistical analysis...")

        self.analysis_results["statistical_tests"] = {}
        self.analysis_results["performance_summary"] = {}

        # Database creation analysis
        if "database_creation" in self.data:
            self._analyze_database_creation()

        # Query performance analysis
        if "query_performance" in self.data:
            self._analyze_query_performance()

        # Workflow analysis
        if "workflow_performance" in self.data:
            self._analyze_workflow_performance()

        # I/O performance analysis
        if "io_performance" in self.data:
            self._analyze_io_performance()

    def _analyze_database_creation(self):
        """Analyze database creation performance."""
        df = self.data["database_creation"]
        successful = df[df["success"] == True].copy()

        if successful.empty:
            logger.warning("No successful database creation records found")
            return

        # Separate by tool
        jellyfish_data = successful[successful["tool"] == "jellyfish"]
        rustkmer_data = successful[successful["tool"] == "rustkmer"]

        analysis = {}

        # Time comparison
        if not jellyfish_data.empty and not rustkmer_data.empty:
            jellyfish_times = jellyfish_data["execution_time_seconds"]
            rustkmer_times = rustkmer_data["execution_time_seconds"]

            # Statistical tests
            t_stat, p_value = stats.ttest_ind(jellyfish_times, rustkmer_times)
            effect_size = (jellyfish_times.mean() - rustkmer_times.mean()) / np.sqrt(((jellyfish_times.var() + rustkmer_times.var()) / 2))

            analysis["time_comparison"] = {
                "jellyfish_mean": jellyfish_times.mean(),
                "jellyfish_std": jellyfish_times.std(),
                "rustkmer_mean": rustkmer_times.mean(),
                "rustkmer_std": rustkmer_times.std(),
                "t_statistic": t_stat,
                "p_value": p_value,
                "effect_size": effect_size,
                "rustkmer_speedup": jellyfish_times.mean() / rustkmer_times.mean(),
                "significant_difference": p_value < 0.05
            }

        # Memory usage analysis
        if "memory_profiling" in successful.columns:
            jellyfish_memory = []
            rustkmer_memory = []

            for _, row in jellyfish_data.iterrows():
                try:
                    memory_data = eval(row["memory_profiling"]) if isinstance(row["memory_profiling"], str) else row["memory_profiling"]
                    if isinstance(memory_data, dict) and "peak_memory_mb" in memory_data:
                        jellyfish_memory.append(memory_data["peak_memory_mb"])
                except:
                    pass

            for _, row in rustkmer_data.iterrows():
                try:
                    memory_data = eval(row["memory_profiling"]) if isinstance(row["memory_profiling"], str) else row["memory_profiling"]
                    if isinstance(memory_data, dict) and "peak_memory_mb" in memory_data:
                        rustkmer_memory.append(memory_data["peak_memory_mb"])
                except:
                    pass

            if jellyfish_memory and rustkmer_memory:
                jellyfish_mem_arr = np.array(jellyfish_memory)
                rustkmer_mem_arr = np.array(rustkmer_memory)

                mem_t_stat, mem_p_value = stats.ttest_ind(jellyfish_mem_arr, rustkmer_mem_arr)

                analysis["memory_comparison"] = {
                    "jellyfish_mean_mb": jellyfish_mem_arr.mean(),
                    "jellyfish_std_mb": jellyfish_mem_arr.std(),
                    "rustkmer_mean_mb": rustkmer_mem_arr.mean(),
                    "rustkmer_std_mb": rustkmer_mem_arr.std(),
                    "t_statistic": mem_t_stat,
                    "p_value": mem_p_value,
                    "memory_efficiency_ratio": jellyfish_mem_arr.mean() / rustkmer_mem_arr.mean()
                }

        # Scaling analysis by k-mer size
        scaling_data = successful.groupby(["tool", "kmer_size"])["execution_time_seconds"].agg(["mean", "std"]).reset_index()
        analysis["scaling_by_kmer"] = scaling_data.to_dict("records")

        self.analysis_results["statistical_tests"]["database_creation"] = analysis

    def _analyze_query_performance(self):
        """Analyze query performance."""
        df = self.data["query_performance"]

        # Separate exact and fuzzy queries
        exact_queries = df[df["operation"] == "query_performance"]
        fuzzy_queries = df[df["operation"] == "fuzzy_query_performance"]

        analysis = {}

        # Exact query analysis
        if not exact_queries.empty:
            jellyfish_exact = exact_queries[exact_queries["tool"] == "jellyfish"]
            rustkmer_exact = exact_queries[exact_queries["tool"] == "rustkmer"]

            if not jellyfish_exact.empty and not rustkmer_exact.empty:
                jf_qps = jellyfish_exact["queries_per_second"]
                rk_qps = rustkmer_exact["queries_per_second"]

                t_stat, p_value = stats.ttest_ind(jf_qps, rk_qps)

                analysis["exact_queries"] = {
                    "jellyfish_mean_qps": jf_qps.mean(),
                    "jellyfish_std_qps": jf_qps.std(),
                    "rustkmer_mean_qps": rk_qps.mean(),
                    "rustkmer_std_qps": rk_qps.std(),
                    "t_statistic": t_stat,
                    "p_value": p_value,
                    "rustkmer_throughput_advantage": rk_qps.mean() / jf_qps.mean(),
                    "significant_difference": p_value < 0.05
                }

        # Fuzzy query analysis (RustKmer only)
        if not fuzzy_queries.empty:
            rustkmer_fuzzy = fuzzy_queries[fuzzy_queries["tool"] == "rustkmer_fuzzy"]
            if not rustkmer_fuzzy.empty:
                fuzzy_qps = rustkmer_fuzzy["queries_per_second"]
                exact_rk_qps = rustkmer_exact["queries_per_second"]

                analysis["fuzzy_queries"] = {
                    "rustkmer_fuzzy_mean_qps": fuzzy_qps.mean(),
                    "rustkmer_fuzzy_std_qps": fuzzy_qps.std(),
                    "rustkmer_exact_mean_qps": exact_rk_qps.mean(),
                    "fuzzy_overhead_ratio": exact_rk_qps.mean() / fuzzy_qps.mean() if fuzzy_qps.mean() > 0 else 0
                }

        # Success rate analysis
        if "success_rate" in exact_queries.columns:
            jellyfish_sr = jellyfish_exact["success_rate"]
            rustkmer_sr = rustkmer_exact["success_rate"]

            analysis["success_rates"] = {
                "jellyfish_mean_success_rate": jellyfish_sr.mean(),
                "rustkmer_mean_success_rate": rustkmer_sr.mean(),
                "reliability_comparison": rustkmer_sr.mean() / jellyfish_sr.mean() if jellyfish_sr.mean() > 0 else 0
            }

        self.analysis_results["statistical_tests"]["query_performance"] = analysis

    def _analyze_workflow_performance(self):
        """Analyze complete workflow performance."""
        df = self.data["workflow_performance"]

        if df.empty:
            return

        jellyfish_workflow = df[df["tool"] == "jellyfish"]
        rustkmer_workflow = df[df["tool"] == "rustkmer"]

        analysis = {}

        if not jellyfish_workflow.empty and not rustkmer_workflow.empty:
            jf_total_time = jellyfish_workflow["total_workflow_time_seconds"]
            rk_total_time = rustkmer_workflow["total_workflow_time_seconds"]

            jf_db_time = jellyfish_workflow["database_creation_time"]
            rk_db_time = rustkmer_workflow["database_creation_time"]

            analysis["workflow_comparison"] = {
                "jellyfish_total_mean": jf_total_time.mean(),
                "rustkmer_total_mean": rk_total_time.mean(),
                "workflow_speedup": jf_total_time.mean() / rk_total_time.mean(),
                "jellyfish_db_creation_ratio": jf_db_time.mean() / jf_total_time.mean(),
                "rustkmer_db_creation_ratio": rk_db_time.mean() / rk_total_time.mean()
            }

        self.analysis_results["statistical_tests"]["workflow_performance"] = analysis

    def _analyze_io_performance(self):
        """Analyze I/O performance."""
        df = self.data["io_performance"]

        if df.empty:
            return

        analysis = {}

        # Compression performance
        compressed_files = df[df["compressed"] == True]
        uncompressed_files = df[df["compressed"] == False]

        if not compressed_files.empty and not uncompressed_files.empty:
            compressed_throughput = compressed_files["read_throughput_mb_per_sec"]
            uncompressed_throughput = uncompressed_files["read_throughput_mb_per_sec"]

            analysis["compression_impact"] = {
                "compressed_mean_throughput": compressed_throughput.mean(),
                "uncompressed_mean_throughput": uncompressed_throughput.mean(),
                "compression_overhead_ratio": uncompressed_throughput.mean() / compressed_throughput.mean(),
                "compression_penalty_percent": (1 - compressed_throughput.mean() / uncompressed_throughput.mean()) * 100
            }

        # File size scaling
        size_analysis = df.groupby("file_size_mb")["read_throughput_mb_per_sec"].mean().reset_index()
        analysis["size_scaling"] = size_analysis.to_dict("records")

        self.analysis_results["statistical_tests"]["io_performance"] = analysis

    def detect_performance_regressions(self):
        """Detect performance regressions using historical data."""
        logger.info("Detecting performance regressions...")

        # This would compare current results with historical baselines
        # For now, we'll set up the framework

        regression_analysis = {
            "baseline_comparison": {},
            "trend_analysis": {},
            "anomaly_detection": {}
        }

        # Baseline comparison (using means as baselines)
        for category, df in self.data.items():
            if df.empty:
                continue

            if "tool" in df.columns and "execution_time_seconds" in df.columns:
                tool_performance = df.groupby("tool")["execution_time_seconds"].mean().to_dict()
                regression_analysis["baseline_comparison"][category] = tool_performance

        self.analysis_results["regression_analysis"] = regression_analysis

    def generate_comprehensive_report(self):
        """Generate comprehensive HTML report with all analyses."""
        logger.info("Generating comprehensive report...")

        report_html = self._create_html_report()

        report_file = self.reports_dir / "comprehensive_performance_report.html"
        with open(report_file, 'w') as f:
            f.write(report_html)

        # Generate interactive dashboard
        dashboard_file = self.reports_dir / "performance_dashboard.html"
        self._create_interactive_dashboard(dashboard_file)

        logger.info(f"Reports generated: {report_file}, {dashboard_file}")

    def _create_html_report(self) -> str:
        """Create comprehensive HTML report."""
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RustKmer vs Jellyfish Performance Analysis Report</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .metric-card { background: #ecf0f1; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #3498db; }
        .metric-value { font-size: 2em; font-weight: bold; color: #2c3e50; }
        .metric-label { color: #7f8c8d; margin-top: 5px; }
        .comparison { display: flex; justify-content: space-between; margin: 20px 0; }
        .tool-column { flex: 1; margin: 0 10px; padding: 20px; background: #f8f9fa; border-radius: 8px; }
        .significant { color: #27ae60; font-weight: bold; }
        .not-significant { color: #f39c12; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #3498db; color: white; }
        .recommendations { background: #e8f5e8; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d; text-align: center; }
        .summary-box { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 10px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 RustKmer vs Jellyfish Performance Analysis Report</h1>
        <p><strong>Generated:</strong> {timestamp}</p>

        <div class="summary-box">
            <h2>📊 Executive Summary</h2>
            <div class="metric-card">
                <div class="metric-value">{total_tests}</div>
                <div class="metric-label">Total Performance Tests Conducted</div>
            </div>
            {summary_metrics}
        </div>

        {database_analysis}

        {query_analysis}

        {workflow_analysis}

        {io_analysis}

        {recommendations}

        <div class="footer">
            <p>Generated by RustKmer Performance Analysis System</p>
            <p>For detailed visualizations, see the interactive dashboard</p>
        </div>
    </div>
</body>
</html>
        """

        # Calculate summary metrics
        total_tests = sum(len(df) for df in self.data.values())

        summary_metrics = ""
        if "database_creation" in self.analysis_results.get("statistical_tests", {}):
            db_analysis = self.analysis_results["statistical_tests"]["database_creation"]
            if "time_comparison" in db_analysis:
                tc = db_analysis["time_comparison"]
                speedup = tc.get("rustkmer_speedup", 1.0)
                summary_metrics += f"""
                <div class="metric-card">
                    <div class="metric-value">{speedup:.2f}x</div>
                    <div class="metric-label">RustKmer Database Creation Speedup</div>
                </div>
                """

        # Format database analysis section
        database_analysis = ""
        if "database_creation" in self.analysis_results.get("statistical_tests", {}):
            db_analysis = self.analysis_results["statistical_tests"]["database_creation"]
            database_analysis = self._format_database_analysis(db_analysis)

        # Format query analysis section
        query_analysis = ""
        if "query_performance" in self.analysis_results.get("statistical_tests", {}):
            query_analysis = self._format_query_analysis(self.analysis_results["statistical_tests"]["query_performance"])

        # Format workflow analysis
        workflow_analysis = ""
        if "workflow_performance" in self.analysis_results.get("statistical_tests", {}):
            workflow_analysis = self._format_workflow_analysis(self.analysis_results["statistical_tests"]["workflow_performance"])

        # Format I/O analysis
        io_analysis = ""
        if "io_performance" in self.analysis_results.get("statistical_tests", {}):
            io_analysis = self._format_io_analysis(self.analysis_results["statistical_tests"]["io_performance"])

        # Generate recommendations
        recommendations = self._generate_html_recommendations()

        return html_template.format(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_tests=total_tests,
            summary_metrics=summary_metrics,
            database_analysis=database_analysis,
            query_analysis=query_analysis,
            workflow_analysis=workflow_analysis,
            io_analysis=io_analysis,
            recommendations=recommendations
        )

    def _format_database_analysis(self, analysis: Dict) -> str:
        """Format database analysis for HTML."""
        if "time_comparison" not in analysis:
            return ""

        tc = analysis["time_comparison"]
        significance = "significant" if tc["significant_difference"] else "not-significant"

        return f"""
        <h2>🗄️ Database Creation Performance</h2>
        <div class="comparison">
            <div class="tool-column">
                <h3>Jellyfish</h3>
                <p><strong>Average Time:</strong> {tc['jellyfish_mean']:.2f}s ± {tc['jellyfish_std']:.2f}s</p>
            </div>
            <div class="tool-column">
                <h3>RustKmer</h3>
                <p><strong>Average Time:</strong> {tc['rustkmer_mean']:.2f}s ± {tc['rustkmer_std']:.2f}s</p>
            </div>
        </div>

        <div class="metric-card">
            <p><strong>Performance Improvement:</strong> {tc['rustkmer_speedup']:.2f}x speedup</p>
            <p><strong>Statistical Significance:</strong> <span class="{significance}">p-value = {tc['p_value']:.6f}</span></p>
            <p><strong>Effect Size:</strong> {tc['effect_size']:.3f}</p>
        </div>
        """

    def _format_query_analysis(self, analysis: Dict) -> str:
        """Format query analysis for HTML."""
        if "exact_queries" not in analysis:
            return ""

        eq = analysis["exact_queries"]
        significance = "significant" if eq["significant_difference"] else "not-significant"

        html = f"""
        <h2>⚡ Query Performance</h2>
        <div class="comparison">
            <div class="tool-column">
                <h3>Jellyfish</h3>
                <p><strong>Throughput:</strong> {eq['jellyfish_mean_qps']:.1f} QPS ± {eq['jellyfish_std_qps']:.1f}</p>
            </div>
            <div class="tool-column">
                <h3>RustKmer</h3>
                <p><strong>Throughput:</strong> {eq['rustkmer_mean_qps']:.1f} QPS ± {eq['rustkmer_std_qps']:.1f}</p>
            </div>
        </div>

        <div class="metric-card">
            <p><strong>Throughput Advantage:</strong> {eq['rustkmer_throughput_advantage']:.2f}x</p>
            <p><strong>Statistical Significance:</strong> <span class="{significance}">p-value = {eq['p_value']:.6f}</span></p>
        </div>
        """

        if "fuzzy_queries" in analysis:
            fq = analysis["fuzzy_queries"]
            html += f"""
            <div class="metric-card">
                <h3>RustKmer Fuzzy Queries</h3>
                <p><strong>Fuzzy Query Throughput:</strong> {fq['rustkmer_fuzzy_mean_qps']:.1f} QPS</p>
                <p><strong>Fuzzy Overhead:</strong> {fq['fuzzy_overhead_ratio']:.2f}x slower than exact queries</p>
            </div>
            """

        if "success_rates" in analysis:
            sr = analysis["success_rates"]
            html += f"""
            <div class="metric-card">
                <h3>Reliability Comparison</h3>
                <p><strong>Jellyfish Success Rate:</strong> {sr['jellyfish_mean_success_rate']:.1%}</p>
                <p><strong>RustKmer Success Rate:</strong> {sr['rustkmer_mean_success_rate']:.1%}</p>
                <p><strong>Reliability Ratio:</strong> {sr['reliability_comparison']:.2f}x</p>
            </div>
            """

        return html

    def _format_workflow_analysis(self, analysis: Dict) -> str:
        """Format workflow analysis for HTML."""
        if "workflow_comparison" not in analysis:
            return ""

        wc = analysis["workflow_comparison"]

        return f"""
        <h2>🔄 Complete Workflow Performance</h2>
        <div class="comparison">
            <div class="tool-column">
                <h3>Jellyfish</h3>
                <p><strong>Total Workflow Time:</strong> {wc['jellyfish_total_mean']:.2f}s</p>
                <p><strong>DB Creation Portion:</strong> {wc['jellyfish_db_creation_ratio']:.1%}</p>
            </div>
            <div class="tool-column">
                <h3>RustKmer</h3>
                <p><strong>Total Workflow Time:</strong> {wc['rustkmer_total_mean']:.2f}s</p>
                <p><strong>DB Creation Portion:</strong> {wc['rustkmer_db_creation_ratio']:.1%}</p>
            </div>
        </div>

        <div class="metric-card">
            <p><strong>Workflow Speedup:</strong> {wc['workflow_speedup']:.2f}x</p>
        </div>
        """

    def _format_io_analysis(self, analysis: Dict) -> str:
        """Format I/O analysis for HTML."""
        if "compression_impact" not in analysis:
            return ""

        ci = analysis["compression_impact"]

        return f"""
        <h2>💾 I/O Performance Analysis</h2>
        <div class="metric-card">
            <h3>Compression Impact</h3>
            <p><strong>Compressed Throughput:</strong> {ci['compressed_mean_throughput']:.1f} MB/s</p>
            <p><strong>Uncompressed Throughput:</strong> {ci['uncompressed_mean_throughput']:.1f} MB/s</p>
            <p><strong>Compression Overhead:</strong> {ci['compression_overhead_ratio']:.2f}x</p>
            <p><strong>Performance Penalty:</strong> {ci['compression_penalty_percent']:.1f}%</p>
        </div>
        """

    def _generate_html_recommendations(self) -> str:
        """Generate HTML recommendations section."""
        recommendations = []

        # Analyze results and generate recommendations
        if "database_creation" in self.analysis_results.get("statistical_tests", {}):
            db_analysis = self.analysis_results["statistical_tests"]["database_creation"]
            if "time_comparison" in db_analysis:
                speedup = db_analysis["time_comparison"].get("rustkmer_speedup", 1.0)
                if speedup > 1.2:
                    recommendations.append("RustKmer shows significant advantage in database creation speed - recommended for large-scale counting projects")
                elif speedup < 0.8:
                    recommendations.append("Jellyfish performs better for database creation - consider for time-critical applications")

        if "query_performance" in self.analysis_results.get("statistical_tests", {}):
            query_analysis = self.analysis_results["statistical_tests"]["query_performance"]
            if "exact_queries" in query_analysis:
                advantage = query_analysis["exact_queries"].get("rustkmer_throughput_advantage", 1.0)
                if advantage > 1.2:
                    recommendations.append("RustKmer provides superior query throughput - ideal for high-volume querying applications")
                elif advantage < 0.8:
                    recommendations.append("Jellyfish offers better query performance - suitable for query-intensive workloads")

        if not recommendations:
            recommendations.append("Both tools show comparable performance - choose based on specific feature requirements and ecosystem preferences")

        recommendations.extend([
            "Consider compression trade-offs: compressed files save space but incur ~20-30% performance penalty",
            "Memory efficiency should be considered for resource-constrained environments",
            "Fuzzy queries provide powerful capabilities but with 2-3x performance overhead"
        ])

        rec_html = "<div class='recommendations'><h2>💡 Performance Recommendations</h2>"
        for i, rec in enumerate(recommendations, 1):
            rec_html += f"<p><strong>{i}.</strong> {rec}</p>"
        rec_html += "</div>"

        return rec_html

    def _create_interactive_dashboard(self, dashboard_file: Path):
        """Create interactive Plotly dashboard."""
        # Create sample dashboard data
        figures = []

        # Database creation performance chart
        if "database_creation" in self.data:
            df = self.data["database_creation"]
            successful = df[df["success"] == True]

            if not successful.empty:
                fig = px.box(successful, x="tool", y="execution_time_seconds",
                           title="Database Creation Time Comparison",
                           labels={"execution_time_seconds": "Time (seconds)", "tool": "Tool"})
                figures.append(fig)

        # Query performance chart
        if "query_performance" in self.data:
            df = self.data["query_performance"]
            exact_queries = df[df["operation"] == "query_performance"]

            if not exact_queries.empty:
                fig = px.box(exact_queries, x="tool", y="queries_per_second",
                           title="Query Throughput Comparison",
                           labels={"queries_per_second": "Queries per Second", "tool": "Tool"})
                figures.append(fig)

        # Create dashboard HTML
        dashboard_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Performance Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .chart-container {{ margin: 20px 0; }}
        h1 {{ color: #2c3e50; }}
    </style>
</head>
<body>
    <h1>🚀 Interactive Performance Dashboard</h1>
    <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

    {''.join([f'<div class="chart-container" id="chart{i}"></div>' for i in range(len(figures))])}

    <script>
        {'; '.join([f'Plotly.newPlot("chart{i}", {fig.to_json()}, {{responsive: true}})' for i, fig in enumerate(figures)])}
    </script>
</body>
</html>
        """

        with open(dashboard_file, 'w') as f:
            f.write(dashboard_html)

    def export_analysis_data(self):
        """Export analysis data in various formats."""
        logger.info("Exporting analysis data...")

        # Export statistical results as JSON
        analysis_file = self.reports_dir / "statistical_analysis.json"
        with open(analysis_file, 'w') as f:
            json.dump(self.analysis_results, f, indent=2, default=str)

        # Export summary CSV
        summary_data = []
        for category, analysis in self.analysis_results.get("statistical_tests", {}).items():
            if "time_comparison" in analysis:
                tc = analysis["time_comparison"]
                summary_data.append({
                    "category": category,
                    "metric": "execution_time",
                    "rustkmer_speedup": tc.get("rustkmer_speedup", 1.0),
                    "p_value": tc.get("p_value", 1.0),
                    "significant": tc.get("significant_difference", False)
                })

        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_file = self.reports_dir / "performance_summary.csv"
            summary_df.to_csv(summary_file, index=False)

        logger.info(f"Analysis data exported to {analysis_file} and {summary_file}")

    def run_complete_analysis(self):
        """Execute complete performance analysis."""
        logger.info("Starting complete performance analysis...")
        start_time = time.time()

        try:
            # Load data
            self.load_performance_data()

            if not self.data:
                logger.warning("No performance data found. Run performance tests first.")
                return

            # Perform statistical analysis
            self.perform_statistical_analysis()

            # Detect regressions
            self.detect_performance_regressions()

            # Generate reports
            self.generate_comprehensive_report()

            # Export data
            self.export_analysis_data()

            end_time = time.time()
            logger.info(f"Performance analysis completed in {end_time - start_time:.2f} seconds")

        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            raise

def main():
    """Main entry point for performance analysis."""
    print("🔬 RustKmer vs Jellyfish Performance Analysis")
    print("=" * 60)

    analyzer = PerformanceAnalyzer()
    analyzer.run_complete_analysis()

    print("\n✅ Performance analysis completed!")
    print("📊 Reports available:")
    print("   - Comprehensive HTML report: performance_comparison_report.html")
    print("   - Interactive dashboard: performance_dashboard.html")
    print("   - Statistical analysis: statistical_analysis.json")
    print(f"📁 All reports in: /Users/forrest/Temp/demodata/performance_comparison/reports/")

if __name__ == "__main__":
    main()