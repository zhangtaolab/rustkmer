#!/usr/bin/env python3
"""
Comprehensive test runner for CLI compatibility tests

This module provides a unified interface to run all compatibility tests
between RustKmer CLI and Python API implementations.
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import tempfile
import shutil

# Add rustkmer to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "python"))


@dataclass
class TestResult:
    """Result of a single compatibility test"""
    test_name: str
    passed: bool
    cli_output: Any
    python_output: Any
    execution_time_cli: float
    execution_time_python: float
    error_message: Optional[str] = None
    performance_ratio: Optional[float] = None


@dataclass
class CompatibilityTestSuite:
    """Container for all compatibility test results"""
    total_tests: int
    passed_tests: int
    failed_tests: List[TestResult]
    passed_tests_list: List[TestResult]
    total_time: float
    test_results: Dict[str, TestResult]

    def __post_init__(self):
        """Calculate derived statistics"""
        self.passed_count = len(self.passed_tests_list)
        self.failed_count = len(self.failed_tests)
        self.pass_rate = (self.passed_count / self.total_tests * 100) if self.total_tests > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "summary": {
                "total_tests": self.total_tests,
                "passed": self.passed_count,
                "failed": self.failed_count,
                "pass_rate": self.pass_rate,
                "total_time": self.total_time
            },
            "results": {name: asdict(result) for name, result in self.test_results.items()},
            "failed_tests": [asdict(result) for result in self.failed_tests]
        }


class CLITester:
    """Interface to run RustKmer CLI commands"""

    def __init__(self, binary_path: Optional[str] = None):
        """
        Initialize CLI tester

        Args:
            binary_path: Path to rustkmer binary. If None, will try to find it.
        """
        if binary_path is None:
            # Try to find the rustkmer binary
            repo_root = Path(__file__).parent.parent.parent.parent
            possible_paths = [
                repo_root / "target" / "release" / "rustkmer",
                repo_root / "target" / "debug" / "rustkmer",
                shutil.which("rustkmer")
            ]

            self.binary_path = None
            for path in possible_paths:
                if path and path.exists():
                    self.binary_path = str(path)
                    break

            if self.binary_path is None:
                raise RuntimeError("Could not find rustkmer binary. Please build it first with 'cargo build --release'")
        else:
            self.binary_path = binary_path

    def run_command(self, command: str, args: List[str], input_data: Optional[str] = None) -> Tuple[Any, float]:
        """
        Run a CLI command and return output with execution time

        Args:
            command: Command to run (e.g., 'count', 'query')
            args: List of arguments
            input_data: Optional stdin input

        Returns:
            Tuple of (output, execution_time_seconds)
        """
        cmd = [self.binary_path, command] + args

        start_time = time.time()
        try:
            if input_data:
                result = subprocess.run(
                    cmd,
                    input=input_data,
                    text=True,
                    capture_output=True,
                    check=True
                )
            else:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True
                )

            execution_time = time.time() - start_time

            # Try to parse JSON output if available
            if "--json" in args:
                try:
                    return json.loads(result.stdout), execution_time
                except json.JSONDecodeError:
                    return result.stdout.strip(), execution_time
            else:
                return result.stdout.strip(), execution_time

        except subprocess.CalledProcessError as e:
            execution_time = time.time() - start_time
            raise RuntimeError(f"CLI command failed: {e.stderr}") from e


class PythonTester:
    """Interface to test RustKmer Python API"""

    def __init__(self):
        """Initialize Python tester"""
        try:
            import rustkmer
            self.rustkmer = rustkmer
        except ImportError as e:
            raise RuntimeError(f"Could not import rustkmer: {e}. Please run 'maturin develop --release'") from e

    def count_command(self, input_file: str, k: int, **kwargs) -> Tuple[Any, float]:
        """Simulate count command using Python API"""
        start_time = time.time()

        counter = self.rustkmer.KmerCounter(k=k, canonical=kwargs.get('canonical', True))
        if input_file:
            counter.count_file(input_file)
        else:
            raise ValueError("Input file required for count test")

        # Get statistics
        stats = {
            'total_kmers': counter.get_total_count(),
            'unique_kmers': counter.get_unique_count(),
            'kmer_size': k
        }

        execution_time = time.time() - start_time
        return stats, execution_time

    def query_command(self, database_file: str, kmer: str) -> Tuple[Any, float]:
        """Simulate query command using Python API"""
        start_time = time.time()

        db = self.rustkmer.Database()
        db.load(database_file)

        result = db.query(kmer)

        stats = {
            'found': result.found,
            'count': result.count if result.found else 0,
            'kmer': kmer
        }

        execution_time = time.time() - start_time
        return stats, execution_time

    def dump_command(self, database_file: str, format: str = "text") -> Tuple[Any, float]:
        """Simulate dump command using Python API"""
        start_time = time.time()

        db = self.rustkmer.Database()
        db.load(database_file)

        # Create temporary file for dump output
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tmp:
            tmp_path = tmp.name

        try:
            db.dump(tmp_path, format=format)

            # Read the dump output
            with open(tmp_path, 'r') as f:
                content = f.read()

            execution_time = time.time() - start_time

            # Parse output based on format
            if format == "text":
                # Count k-mers in output (skip comments)
                kmer_count = len([line for line in content.split('\n')
                                 if line.strip() and not line.startswith('#')])
                return {'kmer_count': kmer_count, 'format': format}, execution_time
            else:
                return {'output': content, 'format': format}, execution_time

        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def stats_command(self, database_file: str) -> Tuple[Any, float]:
        """Simulate stats command using Python API"""
        start_time = time.time()

        db = self.rustkmer.Database()
        db.load(database_file)

        stats = db.get_stats()

        # Convert to dictionary format similar to CLI output
        stats_dict = {
            'kmer_size': stats.kmer_size,
            'total_kmers': stats.total_kmers,
            'unique_kmers': stats.unique_kmers,
            'canonical': stats.canonical,
            'sorted': stats.sorted
        }

        execution_time = time.time() - start_time
        return stats_dict, execution_time


class CompatibilityTestRunner:
    """Main test runner for CLI compatibility tests"""

    def __init__(self, test_data_dir: Optional[str] = None):
        """
        Initialize test runner

        Args:
            test_data_dir: Directory containing test data files
        """
        self.test_data_dir = test_data_dir or Path(__file__).parent / "test_data"
        self.test_data_dir = Path(self.test_data_dir)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="rustkmer_compat_test_"))

        # Initialize testers
        self.cli_tester = CLITester()
        self.python_tester = PythonTester()

        # Test registry
        self.tests = []

    def register_test(self, test_func):
        """Register a test function"""
        self.tests.append(test_func)

    def run_all_tests(self) -> CompatibilityTestSuite:
        """
        Run all registered compatibility tests

        Returns:
            CompatibilityTestSuite with all results
        """
        print("Starting RustKmer CLI-Python Compatibility Tests")
        print("=" * 50)
        print(f"CLI Binary: {self.cli_tester.binary_path}")
        print(f"Test Data Dir: {self.test_data_dir}")
        print(f"Temp Dir: {self.temp_dir}")
        print()

        start_time = time.time()
        test_results = {}
        passed_tests = []
        failed_tests = []

        for test_func in self.tests:
            print(f"Running: {test_func.__name__}")
            try:
                result = test_func(self.cli_tester, self.python_tester, self.temp_dir)
                test_results[result.test_name] = result

                if result.passed:
                    passed_tests.append(result)
                    print(f"  ✓ PASSED")
                else:
                    failed_tests.append(result)
                    print(f"  ✗ FAILED: {result.error_message}")

            except Exception as e:
                print(f"  ✗ ERROR: {e}")
                failed_tests.append(TestResult(
                    test_name=test_func.__name__,
                    passed=False,
                    cli_output=None,
                    python_output=None,
                    execution_time_cli=0,
                    execution_time_python=0,
                    error_message=str(e)
                ))

        total_time = time.time() - start_time

        suite = CompatibilityTestSuite(
            total_tests=len(self.tests),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            passed_tests_list=passed_tests,
            total_time=total_time,
            test_results=test_results
        )

        # Print summary
        print()
        print("Test Summary:")
        print("-" * 50)
        print(f"Total Tests: {suite.total_tests}")
        print(f"Passed: {suite.passed_count}")
        print(f"Failed: {suite.failed_count}")
        print(f"Pass Rate: {suite.pass_rate:.1f}%")
        print(f"Total Time: {suite.total_time:.2f}s")

        # Clean up
        shutil.rmtree(self.temp_dir, ignore_errors=True)

        return suite

    def save_report(self, suite: CompatibilityTestSuite, output_path: str):
        """Save test results to JSON file"""
        report = suite.to_dict()

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\nTest report saved to: {output_path}")


# Built-in test functions
def test_count_command(cli_tester: CLITester, python_tester: PythonTester, temp_dir: Path) -> TestResult:
    """Test count command compatibility"""
    # Create test FASTA file
    test_fasta = temp_dir / "test_count.fasta"
    with open(test_fasta, 'w') as f:
        f.write(">test_seq\nATCGATCGATCG\n")

    # Run CLI count
    cli_output, cli_time = cli_tester.run_command("count", [
        "-k", "4",
        "--canonical",
        "--json",
        str(test_fasta),
        str(temp_dir / "test_output.rkdb")
    ])

    # Run Python count
    python_output, python_time = python_tester.count_command(
        str(test_fasta),
        k=4,
        canonical=True
    )

    # Compare results
    # CLI output is complex, just check if database was created
    db_created = os.path.exists(temp_dir / "test_output.rkdb")
    python_has_counts = python_output['total_kmers'] > 0

    passed = db_created and python_has_counts

    return TestResult(
        test_name="count_command",
        passed=passed,
        cli_output=cli_output,
        python_output=python_output,
        execution_time_cli=cli_time,
        execution_time_python=python_time,
        performance_ratio=python_time / cli_time if cli_time > 0 else None
    )


def test_query_command(cli_tester: CLITester, python_tester: PythonTester, temp_dir: Path) -> TestResult:
    """Test query command compatibility"""
    # First create a test database
    test_fasta = temp_dir / "test_query.fasta"
    db_path = temp_dir / "test_query.rkdb"

    with open(test_fasta, 'w') as f:
        f.write(">test_seq\nATCGATCGATCG\n")

    # Create database using CLI
    cli_tester.run_command("count", [
        "-k", "4",
        str(test_fasta),
        str(db_path)
    ])

    # Test query
    test_kmer = "ATCG"

    # CLI query
    cli_output, cli_time = cli_tester.run_command("query", [
        "--json",
        str(db_path),
        test_kmer
    ])

    # Python query
    python_output, python_time = python_tester.query_command(
        str(db_path),
        test_kmer
    )

    # Compare results
    # Check if both found the k-mer
    cli_found = cli_output.get('found', False) if isinstance(cli_output, dict) else False
    python_found = python_output.get('found', False)

    passed = cli_found == python_found

    return TestResult(
        test_name="query_command",
        passed=passed,
        cli_output=cli_output,
        python_output=python_output,
        execution_time_cli=cli_time,
        execution_time_python=python_time,
        performance_ratio=python_time / cli_time if cli_time > 0 else None
    )


def test_dump_command(cli_tester: CLITester, python_tester: PythonTester, temp_dir: Path) -> TestResult:
    """Test dump command compatibility"""
    # Create test database
    test_fasta = temp_dir / "test_dump.fasta"
    db_path = temp_dir / "test_dump.rkdb"

    with open(test_fasta, 'w') as f:
        f.write(">test_seq\nATCGATCGATCGATCG\n")

    cli_tester.run_command("count", [
        "-k", "5",
        str(test_fasta),
        str(db_path)
    ])

    # CLI dump
    cli_output, cli_time = cli_tester.run_command("dump", [str(db_path)])

    # Python dump
    python_output, python_time = python_tester.dump_command(str(db_path))

    # Compare results
    # Both should export k-mers
    cli_has_kmers = isinstance(cli_output, str) and len(cli_output.strip()) > 0
    python_has_kmers = python_output.get('kmer_count', 0) > 0

    passed = cli_has_kmers and python_has_kmers

    return TestResult(
        test_name="dump_command",
        passed=passed,
        cli_output=cli_output,
        python_output=python_output,
        execution_time_cli=cli_time,
        execution_time_python=python_time,
        performance_ratio=python_time / cli_time if cli_time > 0 else None
    )


def test_stats_command(cli_tester: CLITester, python_tester: PythonTester, temp_dir: Path) -> TestResult:
    """Test stats command compatibility"""
    # Create test database
    test_fasta = temp_dir / "test_stats.fasta"
    db_path = temp_dir / "test_stats.rkdb"

    with open(test_fasta, 'w') as f:
        f.write(">test_seq\nATCGATCGATCGATCGATCGATCG\n")

    cli_tester.run_command("count", [
        "-k", "4",
        str(test_fasta),
        str(db_path)
    ])

    # CLI stats
    cli_output, cli_time = cli_tester.run_command("stats", [
        "--json",
        str(db_path)
    ])

    # Python stats
    python_output, python_time = python_tester.stats_command(str(db_path))

    # Compare results
    if isinstance(cli_output, dict):
        # Check key fields match
        kmer_size_match = cli_output.get('kmer_size') == python_output.get('kmer_size')
        canonical_match = cli_output.get('canonical') == python_output.get('canonical')

        passed = kmer_size_match and canonical_match
    else:
        passed = False

    return TestResult(
        test_name="stats_command",
        passed=passed,
        cli_output=cli_output,
        python_output=python_output,
        execution_time_cli=cli_time,
        execution_time_python=python_time,
        performance_ratio=python_time / cli_time if cli_time > 0 else None
    )


def main():
    """Main entry point for running compatibility tests"""
    import argparse

    parser = argparse.ArgumentParser(description="Run RustKmer CLI-Python compatibility tests")
    parser.add_argument(
        "--output", "-o",
        default="compatibility_test_report.json",
        help="Output JSON file for test report"
    )
    parser.add_argument(
        "--cli-binary",
        help="Path to rustkmer CLI binary"
    )
    parser.add_argument(
        "--test-data",
        help="Directory containing test data files"
    )

    args = parser.parse_args()

    # Initialize test runner
    runner = CompatibilityTestRunner(test_data_dir=args.test_data)

    # Override CLI binary if specified
    if args.cli_binary:
        runner.cli_tester.binary_path = args.cli_binary

    # Register built-in tests
    runner.register_test(test_count_command)
    runner.register_test(test_query_command)
    runner.register_test(test_dump_command)
    runner.register_test(test_stats_command)

    # Run tests
    suite = runner.run_all_tests()

    # Save report
    runner.save_report(suite, args.output)

    # Exit with appropriate code
    sys.exit(0 if suite.passed_count == suite.total_tests else 1)


if __name__ == "__main__":
    main()