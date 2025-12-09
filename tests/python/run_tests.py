#!/usr/bin/env python3
"""
Test runner script for RustKmer Python API.
Provides comprehensive testing with different options and reporting.
"""

import sys
import os
import argparse
import subprocess
import json
from pathlib import Path
from datetime import datetime

# Add repository root to path
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root / "python"))


def run_unit_tests(verbose=False, coverage=False):
    """Run unit tests."""
    cmd = [sys.executable, "-m", "pytest", "tests/python/unit/"]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend(["--cov=rustkmer", "--cov-report=term-missing"])

    result = subprocess.run(cmd, cwd=repo_root)
    return result.returncode == 0


def run_integration_tests(verbose=False):
    """Run integration tests."""
    cmd = [sys.executable, "-m", "pytest", "tests/python/integration/"]

    if verbose:
        cmd.append("-v")

    result = subprocess.run(cmd, cwd=repo_root)
    return result.returncode == 0


def run_performance_tests(verbose=False):
    """Run performance tests."""
    cmd = [sys.executable, "-m", "pytest",
           "tests/python/performance/", "-m", "performance"]

    if verbose:
        cmd.append("-v")

    # Add timeout for performance tests
    cmd.extend(["--timeout=600"])

    result = subprocess.run(cmd, cwd=repo_root)
    return result.returncode == 0


def run_compatibility_tests(verbose=False):
    """Run CLI-Python compatibility tests."""
    compat_script = repo_root / "tests" / "python" / "compatibility" / "runner.py"

    if not compat_script.exists():
        print("Warning: Compatibility test runner not found")
        return True

    cmd = [sys.executable, str(compat_script)]

    if verbose:
        cmd.append("--verbose")

    result = subprocess.run(cmd, cwd=repo_root)
    return result.returncode == 0


def generate_test_report(results):
    """Generate test report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "python_version": sys.version,
        "results": results
    }

    report_file = repo_root / "tests" / "python" / "test_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    return report_file


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Run RustKmer Python API tests")

    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run unit tests"
    )

    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run integration tests"
    )

    parser.add_argument(
        "--performance",
        action="store_true",
        help="Run performance tests"
    )

    parser.add_argument(
        "--compatibility",
        action="store_true",
        help="Run CLI compatibility tests"
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tests"
    )

    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )

    parser.add_argument(
        "--failfast",
        action="store_true",
        help="Stop on first failure"
    )

    args = parser.parse_args()

    # Default to running unit tests if no specific test type selected
    if not any([args.unit, args.integration, args.performance,
                args.compatibility, args.all]):
        args.unit = True

    # Check if rustkmer module is available
    try:
        import rustkmer
        print(f"✓ RustKmer Python module found: {rustkmer.__version__}")
    except ImportError:
        print("✗ RustKmer Python module not found!")
        print("Please build the Python bindings first:")
        print("  cd python && maturin develop --release")
        return 1

    # Check if CLI binary is available for compatibility tests
    cli_binary = repo_root / "target" / "release" / "rustkmer"
    if sys.platform == "windows":
        cli_binary = cli_binary.with_suffix(".exe")

    cli_available = cli_binary.exists()
    if not cli_available:
        print("⚠ RustKmer CLI binary not found at target/release/rustkmer")
        print("  Build with: cargo build --release")
        if args.compatibility:
            print("  Skipping compatibility tests")

    # Collect results
    results = {}
    overall_success = True

    # Run unit tests
    if args.unit or args.all:
        print("\n" + "=" * 70)
        print("Running Unit Tests")
        print("=" * 70)

        success = run_unit_tests(args.verbose, args.coverage)
        results["unit"] = {
            "passed": success,
            "coverage": args.coverage
        }

        if not success:
            overall_success = False
            if args.failfast:
                return 1

    # Run integration tests
    if args.integration or args.all:
        print("\n" + "=" * 70)
        print("Running Integration Tests")
        print("=" * 70)

        success = run_integration_tests(args.verbose)
        results["integration"] = {"passed": success}

        if not success:
            overall_success = False
            if args.failfast:
                return 1

    # Run performance tests
    if args.performance or args.all:
        print("\n" + "=" * 70)
        print("Running Performance Tests")
        print("=" * 70)

        success = run_performance_tests(args.verbose)
        results["performance"] = {"passed": success}

        if not success:
            overall_success = False
            if args.failfast:
                return 1

    # Run compatibility tests
    if (args.compatibility or args.all) and cli_available:
        print("\n" + "=" * 70)
        print("Running CLI-Python Compatibility Tests")
        print("=" * 70)

        success = run_compatibility_tests(args.verbose)
        results["compatibility"] = {"passed": success}

        if not success:
            overall_success = False
            if args.failfast:
                return 1

    # Generate report
    report_file = generate_test_report(results)
    print(f"\nTest report saved to: {report_file}")

    # Print summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    for test_type, result in results.items():
        status = "✓ PASSED" if result["passed"] else "✗ FAILED"
        print(f"{test_type.title():<15}: {status}")

    print("\n" + "=" * 70)
    if overall_success:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())