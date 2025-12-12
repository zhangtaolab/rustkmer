#!/usr/bin/env python3
"""
Check for performance regressions in benchmark results.

This script compares benchmark results against a baseline and reports
any performance regressions beyond a specified threshold.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional


def load_criterion_results(baseline_dir: Path, current_dir: Path) -> Tuple[Dict, Dict]:
    """Load Criterion benchmark results from baseline and current directories."""
    baseline_results = {}
    current_results = {}

    # Load baseline results
    if baseline_dir.exists():
        for benchmark_dir in baseline_dir.iterdir():
            if benchmark_dir.is_dir():
                json_path = benchmark_dir / "new" / "estimates.json"
                if json_path.exists():
                    with open(json_path) as f:
                        baseline_results[benchmark_dir.name] = json.load(f)

    # Load current results
    if current_dir.exists():
        for benchmark_dir in current_dir.iterdir():
            if benchmark_dir.is_dir():
                # Check for different possible result locations
                for result_subdir in ["new", "base", "change"]:
                    json_path = benchmark_dir / result_subdir / "estimates.json"
                    if json_path.exists():
                        with open(json_path) as f:
                            current_results[benchmark_dir.name] = json.load(f)
                        break

    return baseline_results, current_results


def compare_performance(baseline: Dict, current: Dict, threshold: float) -> List[Dict]:
    """Compare baseline and current performance metrics."""
    regressions = []

    for benchmark_name in current:
        if benchmark_name not in baseline:
            # New benchmark, no baseline to compare against
            continue

        baseline_data = baseline[benchmark_name]
        current_data = current[benchmark_name]

        # Compare median estimates
        if "median" in baseline_data and "median" in current_data:
            baseline_median = baseline_data["median"]["point_estimate"]
            current_median = current_data["median"]["point_estimate"]

            # Calculate percentage change
            if baseline_median > 0:
                change = (current_median - baseline_median) / baseline_median
                percent_change = change * 100

                # Check for regression
                if change > threshold:
                    regression = {
                        "benchmark": benchmark_name,
                        "baseline": baseline_median,
                        "current": current_median,
                        "change_percent": percent_change,
                        "severity": "high" if change > threshold * 2 else "medium"
                    }
                    regressions.append(regression)

    return regressions


def generate_report(regressions: List[Dict], threshold: float) -> Dict:
    """Generate a performance regression report."""
    report = {
        "summary": {
            "total_benchmarks": 0,
            "regressions": len(regressions),
            "threshold_percent": threshold * 100,
            "regression_detected": len(regressions) > 0
        },
        "regressions": regressions,
        "recommendations": []
    }

    # Add recommendations based on regressions
    if regressions:
        high_severity = [r for r in regressions if r["severity"] == "high"]
        medium_severity = [r for r in regressions if r["severity"] == "medium"]

        if high_severity:
            report["recommendations"].append(
                f"URGENT: {len(high_severity)} high-severity regressions detected (> {threshold * 200:.0f}% slower)"
            )

        if medium_severity:
            report["recommendations"].append(
                f"WARNING: {len(medium_severity)} medium-severity regressions detected (> {threshold * 100:.0f}% slower)"
            )

        report["recommendations"].extend([
            "Review recent changes that might affect performance",
            "Consider updating performance baselines if the change is intentional",
            "Add specific performance tests for regressed components"
        ])

    return report


def save_report(report: Dict, output_path: Optional[Path] = None):
    """Save the performance report to file and/or print to console."""
    report_text = []

    # Header
    report_text.append("# Performance Regression Report")
    report_text.append(f"Generated: {report.get('timestamp', 'Unknown')}")
    report_text.append("")

    # Summary
    report_text.append("## Summary")
    summary = report["summary"]
    if summary["regression_detected"]:
        report_text.append(f"⚠️ **PERFORMANCE REGRESSIONS DETECTED**")
        report_text.append(f"- {summary['regressions']} out of {summary['total_benchmarks']} benchmarks regressed")
        report_text.append(f"- Threshold: {summary['threshold_percent']:.1f}% slower")
    else:
        report_text.append(f"✅ **No significant performance regressions**")
        report_text.append(f"- All benchmarks within {summary['threshold_percent']:.1f}% of baseline")
    report_text.append("")

    # Regressions details
    if report["regressions"]:
        report_text.append("## Regressions Details")
        report_text.append("")

        for regression in report["regressions"]:
            severity_emoji = "🔴" if regression["severity"] == "high" else "🟡"
            report_text.append(f"{severity_emoji} **{regression['benchmark']}**")
            report_text.append(f"- Baseline: {regression['baseline']:.6f}")
            report_text.append(f"- Current: {regression['current']:.6f}")
            report_text.append(f"- Change: +{regression['change_percent']:.1f}%")
            report_text.append("")

    # Recommendations
    if report["recommendations"]:
        report_text.append("## Recommendations")
        report_text.append("")
        for rec in report["recommendations"]:
            report_text.append(f"- {rec}")
        report_text.append("")

    # Output report
    report_content = "\n".join(report_text)

    # Print to console
    print(report_content)

    # Save to file if requested
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(report_content)
        print(f"\nReport saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Check for performance regressions in Criterion benchmark results"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.10,
        help="Regression threshold as fraction (default: 0.10 for 10%)"
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        required=True,
        help="Path to baseline benchmark results directory"
    )
    parser.add_argument(
        "--current",
        type=Path,
        required=True,
        help="Path to current benchmark results directory"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Path to save performance report (optional)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format"
    )

    args = parser.parse_args()

    # Load benchmark results
    print(f"Loading baseline results from: {args.baseline}")
    print(f"Loading current results from: {args.current}")

    baseline_results, current_results = load_criterion_results(args.baseline, args.current)

    if not baseline_results:
        print("Warning: No baseline results found")
        sys.exit(1)

    if not current_results:
        print("Warning: No current results found")
        sys.exit(1)

    print(f"Found {len(baseline_results)} baseline benchmarks")
    print(f"Found {len(current_results)} current benchmarks")

    # Compare performance
    regressions = compare_performance(baseline_results, current_results, args.threshold)

    # Generate report
    from datetime import datetime
    report = generate_report(regressions, args.threshold)
    report["timestamp"] = datetime.now().isoformat()
    report["summary"]["total_benchmarks"] = len(current_results)

    # Output results
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        save_report(report, args.output)

    # Exit with error code if regressions detected
    if regressions:
        print(f"\n⚠️ {len(regressions)} performance regression(s) detected!")
        sys.exit(1)
    else:
        print("\n✅ No performance regressions detected!")
        sys.exit(0)


if __name__ == "__main__":
    main()