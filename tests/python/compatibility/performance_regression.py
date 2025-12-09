#!/usr/bin/env python3
"""
Performance regression testing for RustKmer CLI-Python compatibility

This module provides tools to track performance over time, detect regressions,
and compare Python vs CLI performance across different versions.
"""

import json
import os
import time
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy import stats

# Import compatibility test runner
from runner import CompatibilityTestRunner, CLITester, PythonTester


@dataclass
class PerformanceSnapshot:
    """Snapshot of performance metrics at a point in time"""
    timestamp: str
    git_commit: str
    rust_version: str
    python_version: str
    test_results: Dict[str, Any]
    performance_summary: Dict[str, float]


@dataclass
class RegressionAlert:
    """Alert for performance regression"""
    test_name: str
    metric: str
    current_value: float
    baseline_value: float
    regression_percent: float
    severity: str  # 'minor', 'major', 'critical'
    recommendation: str


class PerformanceTracker:
    """Track performance over time and detect regressions"""

    def __init__(self, data_dir: str = "performance_data"):
        """
        Initialize performance tracker

        Args:
            data_dir: Directory to store performance data
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.snapshots_file = self.data_dir / "performance_snapshots.json"
        self.baseline_file = self.data_dir / "performance_baseline.json"
        self.regressions_file = self.data_dir / "performance_regressions.json"

    def record_performance(self, test_suite_result: Any, git_commit: Optional[str] = None) -> PerformanceSnapshot:
        """
        Record a performance snapshot

        Args:
            test_suite_result: Result from compatibility test suite
            git_commit: Current git commit hash

        Returns:
            PerformanceSnapshot created
        """
        # Get git info
        if git_commit is None:
            git_commit = self._get_git_commit() or "unknown"

        # Get version info
        rust_version = self._get_rust_version()
        python_version = self._get_python_version()

        # Calculate performance summary
        performance_summary = self._calculate_performance_summary(test_suite_result.test_results)

        # Create snapshot
        snapshot = PerformanceSnapshot(
            timestamp=datetime.now().isoformat(),
            git_commit=git_commit,
            rust_version=rust_version,
            python_version=python_version,
            test_results=test_suite_result.test_results,
            performance_summary=performance_summary
        )

        # Save snapshot
        self._save_snapshot(snapshot)

        return snapshot

    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash"""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except:
            return None

    def _get_rust_version(self) -> str:
        """Get Rust version"""
        try:
            import subprocess
            result = subprocess.run(
                ["rustc", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except:
            return "unknown"

    def _get_python_version(self) -> str:
        """Get Python version"""
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def _calculate_performance_summary(self, test_results: Dict[str, Any]) -> Dict[str, float]:
        """Calculate summary statistics from test results"""
        summary = {}

        # Collect all performance ratios
        ratios = []
        for result in test_results.values():
            if result.get('performance_ratio') is not None:
                ratios.append(result['performance_ratio'])

        if ratios:
            summary['mean_performance_ratio'] = statistics.mean(ratios)
            summary['median_performance_ratio'] = statistics.median(ratios)
            summary['min_performance_ratio'] = min(ratios)
            summary['max_performance_ratio'] = max(ratios)
            summary['performance_std'] = statistics.stdev(ratios) if len(ratios) > 1 else 0.0

        # Collect test-specific metrics
        for test_name, result in test_results.items():
            if result.get('performance_ratio') is not None:
                summary[f"{test_name}_ratio"] = result['performance_ratio']
            if result.get('execution_time_cli') is not None:
                summary[f"{test_name}_cli_time"] = result['execution_time_cli']
            if result.get('execution_time_python') is not None:
                summary[f"{test_name}_python_time"] = result['execution_time_python']

        return summary

    def _save_snapshot(self, snapshot: PerformanceSnapshot):
        """Save performance snapshot to file"""
        snapshots = self._load_snapshots()
        snapshots.append(asdict(snapshot))

        # Keep only last 100 snapshots
        if len(snapshots) > 100:
            snapshots = snapshots[-100:]

        with open(self.snapshots_file, 'w') as f:
            json.dump(snapshots, f, indent=2)

    def _load_snapshots(self) -> List[Dict[str, Any]]:
        """Load all performance snapshots"""
        if not self.snapshots_file.exists():
            return []

        with open(self.snapshots_file, 'r') as f:
            return json.load(f)

    def detect_regressions(self, baseline_days: int = 30) -> List[RegressionAlert]:
        """
        Detect performance regressions compared to baseline

        Args:
            baseline_days: Number of days to use for baseline calculation

        Returns:
            List of regression alerts
        """
        snapshots = self._load_snapshots()
        if len(snapshots) < 2:
            return []

        # Filter snapshots for baseline period
        cutoff_date = datetime.now() - timedelta(days=baseline_days)
        baseline_snapshots = [
            s for s in snapshots
            if datetime.fromisoformat(s['timestamp']) >= cutoff_date
        ]

        if not baseline_snapshots:
            return []

        # Get most recent snapshot
        latest_snapshot = snapshots[-1]

        # Calculate baseline statistics
        baseline_stats = {}
        for snapshot in baseline_snapshots:
            for key, value in snapshot.get('performance_summary', {}).items():
                if isinstance(value, (int, float)):
                    if key not in baseline_stats:
                        baseline_stats[key] = []
                    baseline_stats[key].append(value)

        # Calculate baseline means
        baseline_means = {}
        for key, values in baseline_stats.items():
            if values:
                baseline_means[key] = statistics.mean(values)

        # Detect regressions
        regressions = []

        # Check performance ratio regressions (Python getting slower relative to CLI)
        for key, latest_value in latest_snapshot.get('performance_summary', {}).items():
            if key.endswith('_ratio') and key in baseline_means:
                baseline_value = baseline_means[key]
                regression_percent = ((latest_value - baseline_value) / baseline_value) * 100

                if regression_percent > 20:  # 20% slower than baseline
                    severity = 'critical' if regression_percent > 100 else 'major' if regression_percent > 50 else 'minor'
                    test_name = key.replace('_ratio', '')

                    regressions.append(RegressionAlert(
                        test_name=test_name,
                        metric='performance_ratio',
                        current_value=latest_value,
                        baseline_value=baseline_value,
                        regression_percent=regression_percent,
                        severity=severity,
                        recommendation=self._get_regression_recommendation(test_name, 'performance_ratio', regression_percent)
                    ))

        # Check absolute time regressions (both CLI and Python getting slower)
        for key, latest_value in latest_snapshot.get('performance_summary', {}).items():
            if (key.endswith('_time') or key.endswith('_cli_time') or key.endswith('_python_time')) \
               and key in baseline_means:
                baseline_value = baseline_means[key]
                regression_percent = ((latest_value - baseline_value) / baseline_value) * 100

                if regression_percent > 50:  # 50% slower than baseline
                    severity = 'critical' if regression_percent > 200 else 'major' if regression_percent > 100 else 'minor'
                    test_name = key.replace('_time', '').replace('_cli', '').replace('_python', '')

                    regressions.append(RegressionAlert(
                        test_name=test_name,
                        metric=key,
                        current_value=latest_value,
                        baseline_value=baseline_value,
                        regression_percent=regression_percent,
                        severity=severity,
                        recommendation=self._get_regression_recommendation(test_name, key, regression_percent)
                    ))

        # Save regressions
        with open(self.regressions_file, 'w') as f:
            json.dump([asdict(r) for r in regressions], f, indent=2)

        return regressions

    def _get_regression_recommendation(self, test_name: str, metric: str, regression_percent: float) -> str:
        """Get recommendation for a regression"""
        if metric == 'performance_ratio':
            if regression_percent > 100:
                return f"Critical performance regression in {test_name}. Python API is now >2x slower than CLI. Immediate investigation required."
            elif regression_percent > 50:
                return f"Major performance regression in {test_name}. Python API is significantly slower. Review recent changes."
            else:
                return f"Minor performance regression in {test_name}. Monitor for further degradation."
        else:
            if 'cli' in metric:
                return f"CLI performance regression detected in {test_name}. Check for algorithmic changes or resource constraints."
            elif 'python' in metric:
                return f"Python performance regression detected in {test_name}. Review Python bindings and data transfer overhead."
            else:
                return f"Performance regression in {test_name}. Investigate both implementations."

    def generate_performance_trend_plot(self, output_dir: str = "performance_plots") -> str:
        """
        Generate performance trend plots

        Args:
            output_dir: Directory to save plots

        Returns:
            Path to generated plot
        """
        snapshots = self._load_snapshots()
        if len(snapshots) < 2:
            return "Not enough data for trend analysis"

        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

        # Extract time series data
        timestamps = []
        mean_ratios = []
        cli_times = {}
        python_times = {}

        for snapshot in snapshots:
            timestamp = datetime.fromisoformat(snapshot['timestamp'])
            timestamps.append(timestamp)

            summary = snapshot.get('performance_summary', {})
            mean_ratios.append(summary.get('mean_performance_ratio', 0))

            # Collect individual test times
            for key, value in summary.items():
                if key.endswith('_cli_time'):
                    test_name = key.replace('_cli_time', '')
                    if test_name not in cli_times:
                        cli_times[test_name] = []
                    cli_times[test_name].append(value)
                elif key.endswith('_python_time'):
                    test_name = key.replace('_python_time', '')
                    if test_name not in python_times:
                        python_times[test_name] = []
                    python_times[test_name].append(value)

        # Create subplot figure
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('RustKmer Performance Trends', fontsize=16)

        # Plot 1: Mean Performance Ratio Over Time
        axes[0, 0].plot(timestamps, mean_ratios, 'b-', linewidth=2, label='Mean Ratio')
        axes[0, 0].axhline(y=1.0, color='red', linestyle='--', alpha=0.5, label='Parity')
        axes[0, 0].set_title('Python/CLI Performance Ratio Over Time')
        axes[0, 0].set_ylabel('Performance Ratio')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        axes[0, 0].xaxis.set_major_locator(mdates.DayLocator(interval=7))
        plt.setp(axes[0, 0].xaxis.get_majorticklabels(), rotation=45)

        # Plot 2: CLI Execution Times
        for test_name, times in cli_times.items():
            if len(times) == len(timestamps):
                axes[0, 1].plot(timestamps, times, label=test_name, marker='o', markersize=3)
        axes[0, 1].set_title('CLI Execution Times Over Time')
        axes[0, 1].set_ylabel('Time (seconds)')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        axes[0, 1].xaxis.set_major_locator(mdates.DayLocator(interval=7))
        plt.setp(axes[0, 1].xaxis.get_majorticklabels(), rotation=45)

        # Plot 3: Python Execution Times
        for test_name, times in python_times.items():
            if len(times) == len(timestamps):
                axes[1, 0].plot(timestamps, times, label=test_name, marker='s', markersize=3)
        axes[1, 0].set_title('Python Execution Times Over Time')
        axes[1, 0].set_ylabel('Time (seconds)')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        axes[1, 0].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        axes[1, 0].xaxis.set_major_locator(mdates.DayLocator(interval=7))
        plt.setp(axes[1, 0].xaxis.get_majorticklabels(), rotation=45)

        # Plot 4: Performance Distribution Heatmap
        if len(mean_ratios) > 1:
            # Create performance categories
            performance_matrix = []
            time_labels = [t.strftime('%Y-%m-%d') for t in timestamps]

            # Calculate performance metrics for each day
            for i, snapshot in enumerate(snapshots):
                row = []
                summary = snapshot.get('performance_summary', {})

                # Performance ratio
                row.append(summary.get('mean_performance_ratio', 0))

                # Individual test ratios
                for test in ['count', 'query', 'dump', 'stats']:
                    ratio_key = f"{test}_command_ratio"
                    if ratio_key in summary:
                        row.append(summary[ratio_key])
                    else:
                        row.append(0)

                performance_matrix.append(row)

            performance_matrix = np.array(performance_matrix)

            im = axes[1, 1].imshow(performance_matrix.T, cmap='RdYlGn_r', aspect='auto')
            axes[1, 1].set_title('Performance Heatmap (Ratio Values)')
            axes[1, 1].set_xlabel('Date')
            axes[1, 1].set_ylabel('Metric')

            # Set tick labels
            axes[1, 1].set_xticks(range(len(time_labels)))
            axes[1, 1].set_xticklabels(time_labels, rotation=45, ha='right')
            axes[1, 1].set_yticks(range(5))
            axes[1, 1].set_yticklabels(['Mean', 'Count', 'Query', 'Dump', 'Stats'])

            # Add colorbar
            plt.colorbar(im, ax=axes[1, 1], label='Performance Ratio')

        plt.tight_layout()

        # Save plot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plot_path = output_dir / f"performance_trends_{timestamp}.png"
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()

        return str(plot_path)


class RegressionTestRunner:
    """Run performance regression tests"""

    def __init__(self, tracker: PerformanceTracker):
        """
        Initialize regression test runner

        Args:
            tracker: PerformanceTracker instance
        """
        self.tracker = tracker
        self.runner = CompatibilityTestRunner()

    def run_regression_test(self, test_iterations: int = 3) -> Tuple[Any, List[RegressionAlert]]:
        """
        Run performance regression test with multiple iterations

        Args:
            test_iterations: Number of times to run each test for stability

        Returns:
            Tuple of (test results, regression alerts)
        """
        print(f"Running performance regression test with {test_iterations} iterations...")
        print("-" * 50)

        # Run tests multiple times
        all_results = []
        best_result = None
        best_score = float('inf')

        for i in range(test_iterations):
            print(f"\nIteration {i + 1}/{test_iterations}")
            try:
                result = self.runner.run_all_tests()

                # Score the result (lower is better - prefers Python not being too slow)
                score = self._score_result(result)
                if score < best_score:
                    best_score = score
                    best_result = result

                all_results.append(result)
            except Exception as e:
                print(f"Iteration {i + 1} failed: {e}")

        if not best_result:
            raise RuntimeError("All test iterations failed")

        # Record performance
        snapshot = self.tracker.record_performance(best_result)

        # Detect regressions
        regressions = self.tracker.detect_regressions()

        print("\nRegression Test Complete")
        print("-" * 50)
        print(f"Best score: {best_score:.2f}")
        print(f"Recorded snapshot: {snapshot.timestamp}")

        if regressions:
            print(f"\n⚠️  Detected {len(regressions)} performance regressions:")
            for regression in regressions:
                print(f"  - {regression.test_name}: {regression.severity} ({regression.regression_percent:.1f}% regression)")
        else:
            print("\n✅ No performance regressions detected")

        return best_result, regressions

    def _score_result(self, result: Any) -> float:
        """
        Score a test result for performance

        Args:
            result: Test suite result

        Returns:
            Performance score (lower is better)
        """
        score = 0.0
        count = 0

        for test_result in result.test_results.values():
            if test_result.get('performance_ratio') is not None:
                # Penalize high performance ratios (Python slower than CLI)
                ratio = test_result['performance_ratio']
                if ratio > 2.0:
                    score += (ratio - 2.0) * 10  # Heavy penalty for very slow Python
                elif ratio > 1.5:
                    score += (ratio - 1.5) * 5   # Medium penalty
                elif ratio < 0.5:
                    score -= (0.5 - ratio) * 2   # Reward for Python being much faster
                count += 1

        return score / max(count, 1)


def main():
    """Main entry point for performance regression testing"""
    import argparse

    parser = argparse.ArgumentParser(description="Run RustKmer performance regression tests")
    parser.add_argument(
        "--iterations", "-i",
        type=int,
        default=3,
        help="Number of test iterations (default: 3)"
    )
    parser.add_argument(
        "--baseline-days",
        type=int,
        default=30,
        help="Days to use for baseline calculation (default: 30)"
    )
    parser.add_argument(
        "--generate-plots",
        action="store_true",
        help="Generate performance trend plots"
    )

    args = parser.parse_args()

    # Initialize tracker and runner
    tracker = PerformanceTracker()
    runner = RegressionTestRunner(tracker)

    # Run regression test
    result, regressions = runner.run_regression_test(test_iterations=args.iterations)

    # Check for regressions
    critical_regressions = [r for r in regressions if r.severity == 'critical']
    if critical_regressions:
        print(f"\n🚨 CRITICAL: {len(critical_regressions)} critical performance regressions detected!")
        for regression in critical_regressions:
            print(f"  - {regression.test_name}: {regression.recommendation}")

    # Generate plots if requested
    if args.generate_plots:
        print("\nGenerating performance trend plots...")
        plot_path = tracker.generate_performance_trend_plot()
        print(f"Plot saved to: {plot_path}")

    # Exit with appropriate code
    sys.exit(1 if critical_regressions else 0)


if __name__ == "__main__":
    main()