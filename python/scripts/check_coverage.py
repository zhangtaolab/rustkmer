#!/usr/bin/env python3
"""Test coverage verification script for rustkmer Python bindings.

This script runs pytest with coverage and verifies that the coverage threshold
is met. It exits with non-zero status if coverage is below the threshold.
"""

import argparse
import json
import sys
from pathlib import Path

def parse_coverage_xml(xml_file: Path) -> float:
    """Parse coverage.xml and return total coverage percentage."""
    import xml.etree.ElementTree as ET

    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Find the coverage summary
    coverage = root.find(".//coverage")
    if coverage is not None and 'line-rate' in coverage.attrib:
        return float(coverage.attrib['line-rate']) * 100

    # Fallback to first coverage element
    for elem in root.iter():
        if 'line-rate' in elem.attrib:
            return float(elem.attrib['line-rate']) * 100

    return 0.0


def parse_coverage_json(json_file: Path) -> dict:
    """Parse coverage.json and return coverage data."""
    with open(json_file, 'r') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Check test coverage for rustkmer Python bindings"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=90.0,
        help="Coverage threshold percentage (default: 90.0)"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="rustkmer",
        help="Source package to measure coverage for (default: rustkmer)"
    )
    parser.add_argument(
        "--pytest-args",
        type=str,
        default="tests/",
        help="Arguments to pass to pytest (default: tests/)"
    )
    parser.add_argument(
        "--output-format",
        choices=["text", "json", "xml", "html"],
        nargs="+",
        default=["text"],
        help="Coverage output formats (default: text)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Build pytest command
    cmd = [
        "python", "-m", "pytest",
        f"--cov={args.source}",
        f"--cov-fail-under={args.threshold}",
        "--cov-report=term-missing",
    ]

    # Add output formats
    if "json" in args.output_format:
        cmd.append("--cov-report=json")
    if "xml" in args.output_format:
        cmd.append("--cov-report=xml")
    if "html" in args.output_format:
        cmd.append("--cov-report=html")

    # Add pytest args
    if args.pytest_args:
        cmd.extend(args.pytest_args.split())

    if args.verbose:
        cmd.append("-v")

    # Change to python directory
    python_dir = Path(__file__).parent.parent
    original_cwd = Path.cwd()

    try:
        import os
        os.chdir(python_dir)

        if args.verbose:
            print(f"Running: {' '.join(cmd)}")
            print(f"In directory: {python_dir}")
            print(f"Coverage threshold: {args.threshold}%")
            print()

        # Run pytest with coverage
        import subprocess
        result = subprocess.run(cmd, capture_output=False)

        # Parse coverage report if requested
        coverage_pct = 0.0

        if "json" in args.output_format:
            try:
                coverage_data = parse_coverage_json(python_dir / "coverage.json")
                coverage_pct = coverage_data.get("totals", {}).get("percent_covered", 0.0)
            except FileNotFoundError:
                pass

        if "xml" in args.output_format:
            try:
                coverage_pct = parse_coverage_xml(python_dir / "coverage.xml")
            except FileNotFoundError:
                pass

        # Print results
        if args.verbose or result.returncode != 0:
            print()
            print(f"Coverage: {coverage_pct:.2f}%")
            print(f"Threshold: {args.threshold}%")

            if coverage_pct >= args.threshold:
                print("✓ Coverage threshold met!")
            else:
                print(f"✗ Coverage below threshold by {args.threshold - coverage_pct:.2f}%")

        # Exit with pytest's exit code
        sys.exit(result.returncode)

    finally:
        os.chdir(original_cwd)


if __name__ == "__main__":
    main()