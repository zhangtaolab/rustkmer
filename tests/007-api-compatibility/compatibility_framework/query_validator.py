#!/usr/bin/env python3
"""
T026: Cross-platform query result validation framework.
Comprehensive testing to validate 100% query result consistency between CLI and Python API.
"""

import os
import sys
import subprocess
import json
import tempfile
import time
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from pathlib import Path

# Add Python API to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src', 'python'))

try:
    import rustkmer
except ImportError as e:
    print(f"Warning: rustkmer Python module not available: {e}")
    rustkmer = None


@dataclass
class QueryTestCase:
    """Represents a single query test case."""
    kmer: str
    expected_count: Optional[int] = None
    description: str = ""
    category: str = "basic"


@dataclass
class QueryResult:
    """Represents a query result from either CLI or Python API."""
    kmer: str
    count: int
    found: bool
    duration: float = 0.0
    source: str = ""  # "cli" or "python"


@dataclass
class ValidationResult:
    """Represents validation result for a query test."""
    test_case: QueryTestCase
    cli_result: Optional[QueryResult] = None
    python_result: Optional[QueryResult] = None
    match: bool = False
    error: Optional[str] = None


class CrossPlatformQueryValidator:
    """Comprehensive cross-platform query result validator."""

    def __init__(self, cli_path: str = None):
        """
        Initialize the validator.

        Args:
            cli_path: Path to the rustkmer CLI binary
        """
        self.cli_path = cli_path or self._find_cli_binary()
        self.test_results: List[ValidationResult] = []

    def _find_cli_binary(self) -> str:
        """Find the rustkmer CLI binary."""
        # Try common locations
        candidates = [
            "./target/release/rustkmer",
            "./target/debug/rustkmer",
            "rustkmer",
            "/usr/local/bin/rustkmer"
        ]

        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate

        raise FileNotFoundError("RustKmer CLI binary not found")

    def _run_cli_query(self, database_path: str, kmer: str) -> Tuple[Optional[QueryResult], Optional[str]]:
        """Run a single CLI query."""
        try:
            start_time = time.time()
            cmd = [self.cli_path, "query", database_path, kmer]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            duration = time.time() - start_time

            if result.returncode == 0:
                # Parse CLI output (assuming format: "KMER COUNT")
                output = result.stdout.strip()
                if output:
                    parts = output.split()
                    if len(parts) >= 2:
                        count = int(parts[1])
                        return QueryResult(
                            kmer=kmer.upper(),
                            count=count,
                            found=count > 0,
                            duration=duration,
                            source="cli"
                        )

                return QueryResult(kmer=kmer.upper(), count=0, found=False, duration=duration, source="cli")
            else:
                return None, f"CLI error: {result.stderr}"

        except subprocess.TimeoutExpired:
            return None, "CLI query timeout"
        except Exception as e:
            return None, f"CLI exception: {str(e)}"

    def _run_python_query(self, database_path: str, kmer: str) -> Tuple[Optional[QueryResult], Optional[str]]:
        """Run a single Python API query."""
        if rustkmer is None:
            return None, "Python rustkmer module not available"

        try:
            start_time = time.time()

            # Use Python API to query
            db = rustkmer.Database(database_path)
            result = db.query(kmer)

            duration = time.time() - start_time

            return QueryResult(
                kmer=result.kmer,
                count=result.count,
                found=result.found,
                duration=duration,
                source="python"
            )

        except Exception as e:
            return None, f"Python API exception: {str(e)}"

    def _run_python_batch_query(self, database_path: str, kmers: List[str]) -> Tuple[List[QueryResult], Optional[str]]:
        """Run batch queries using Python API."""
        if rustkmer is None:
            return [], "Python rustkmer module not available"

        try:
            start_time = time.time()

            db = rustkmer.Database(database_path)
            results = db.query_multiple(kmers)

            duration = time.time() - start_time

            query_results = []
            for result in results:
                query_results.append(QueryResult(
                    kmer=result.kmer,
                    count=result.count,
                    found=result.found,
                    duration=duration / len(results),  # Approximate per-query time
                    source="python"
                ))

            return query_results, None

        except Exception as e:
            return [], f"Python API batch query exception: {str(e)}"

    def create_test_cases(self, kmer_size: int = 13) -> List[QueryTestCase]:
        """Create comprehensive test cases for given k-mer size."""
        test_cases = []

        # Basic valid k-mers
        valid_kmers = [
            "ACGTACGTACGTAC",  # Perfect alternating
            "AAAAAAAAAAAAAA",  # All A's
            "CCCCCCCCCCCCCC",  # All C's
            "GGGGGGGGGGGGGG",  # All G's
            "TTTTTTTTTTTTTT",  # All T's
            "ACGTACGTACGTA",   # One shorter
            "ACGTACGTACGTACG", # One longer
        ]

        for kmer in valid_kmers:
            if len(kmer) == kmer_size:
                test_cases.append(QueryTestCase(
                    kmer=kmer,
                    description=f"Valid {kmer_size}-mer: {kmer[:8]}...",
                    category="valid"
                ))

        # Edge cases
        test_cases.extend([
            QueryTestCase(kmer="N" * kmer_size, description="All N's", category="edge"),
            QueryTestCase(kmer="A" * (kmer_size - 1), description="Too short", category="edge"),
            QueryTestCase(kmer="A" * (kmer_size + 1), description="Too long", category="edge"),
            QueryTestCase(kmer="ACGTACGTACGTX", description="Invalid character X", category="edge"),
            QueryTestCase(kmer="acgtacgtacgtac", description="Lower case", category="edge"),
        ])

        # Canonical cases (if kmer_size is reasonable)
        if kmer_size <= 21:
            canonical_pairs = [
                ("ACGTACGTACGTAC", "GTGTACGTACGTAC"),  # Different forms
                ("AAAAAAAAAAAAAA", "TTTTTTTTTTTTTT"),  # Reverse complement
            ]

            for kmer1, kmer2 in canonical_pairs:
                if len(kmer1) == kmer_size and len(kmer2) == kmer_size:
                    test_cases.append(QueryTestCase(
                        kmer=kmer1,
                        description=f"Canonical pair with {kmer2[:8]}...",
                        category="canonical"
                    ))

        return test_cases

    def validate_database_compatibility(self, database_path: str, test_cases: List[QueryTestCase] = None) -> Dict[str, Any]:
        """
        Validate query compatibility for a database.

        Args:
            database_path: Path to the database file
            test_cases: Optional custom test cases

        Returns:
            Validation results dictionary
        """
        if test_cases is None:
            # Auto-detect k-mer size and create test cases
            try:
                if rustkmer is not None:
                    db = rustkmer.Database(database_path)
                    kmer_size = db.get_kmer_size()
                else:
                    # Use CLI to get k-mer size (would need implementation)
                    kmer_size = 13  # Default fallback
                test_cases = self.create_test_cases(kmer_size)
            except Exception as e:
                return {"error": f"Failed to determine k-mer size: {str(e)}"}

        validation_results = []

        print(f"Testing database: {database_path}")
        print(f"Running {len(test_cases)} query validation tests...")

        for i, test_case in enumerate(test_cases, 1):
            print(f"  Test {i}/{len(test_cases)}: {test_case.description}")

            result = ValidationResult(test_case=test_case)

            # Run CLI query
            cli_result, cli_error = self._run_cli_query(database_path, test_case.kmer)
            if cli_error:
                result.error = f"CLI error: {cli_error}"
            else:
                result.cli_result = cli_result

            # Run Python API query
            python_result, python_error = self._run_python_query(database_path, test_case.kmer)
            if python_error:
                if result.error:
                    result.error += f"; Python error: {python_error}"
                else:
                    result.error = f"Python error: {python_error}"
            else:
                result.python_result = python_result

            # Check for match
            if cli_result and python_result:
                result.match = (
                    cli_result.count == python_result.count and
                    cli_result.found == python_result.found and
                    cli_result.kmer == python_result.kmer
                )

            validation_results.append(result)

            # Print result
            if result.match:
                print(f"    ✅ MATCH: count={cli_result.count if cli_result else 'N/A'}")
            else:
                print(f"    ❌ MISMATCH: CLI={cli_result.count if cli_result else 'ERROR'}, Python={python_result.count if python_result else 'ERROR'}")

        self.test_results.extend(validation_results)

        return self._generate_validation_report(validation_results)

    def validate_batch_queries(self, database_path: str, batch_sizes: List[int] = [10, 100, 1000]) -> Dict[str, Any]:
        """Validate batch query compatibility."""
        if rustkmer is None:
            return {"error": "Python rustkmer module not available"}

        batch_results = {}

        # Get k-mer size
        try:
            db = rustkmer.Database(database_path)
            kmer_size = db.get_kmer_size()
        except Exception as e:
            return {"error": f"Failed to determine k-mer size: {str(e)}"}

        # Generate test k-mers
        base_kmers = self.create_test_cases(kmer_size)
        base_kmers = [tc.kmer for tc in base_kmers if tc.category == "valid"]

        for batch_size in batch_sizes:
            print(f"Testing batch size: {batch_size}")

            # Repeat k-mers if needed
            test_kmers = (base_kmers * ((batch_size // len(base_kmers)) + 1))[:batch_size]

            try:
                # Run Python batch query
                python_results, python_error = self._run_python_batch_query(database_path, test_kmers)

                if python_error:
                    batch_results[batch_size] = {"error": python_error}
                    continue

                # Run individual CLI queries for comparison
                cli_results = []
                cli_errors = []

                for kmer in test_kmers:
                    cli_result, cli_error = self._run_cli_query(database_path, kmer)
                    if cli_error:
                        cli_errors.append(cli_error)
                        cli_results.append(None)
                    else:
                        cli_results.append(cli_result)

                # Compare results
                matches = 0
                total = len(test_kmers)

                for i, (python_result, cli_result) in enumerate(zip(python_results, cli_results)):
                    if cli_result and python_result:
                        if (cli_result.count == python_result.count and
                            cli_result.found == python_result.found):
                            matches += 1

                accuracy = (matches / total) * 100 if total > 0 else 0

                batch_results[batch_size] = {
                    "total_queries": total,
                    "matching_queries": matches,
                    "accuracy_percent": accuracy,
                    "cli_errors": len(cli_errors),
                    "python_duration": sum(r.duration for r in python_results),
                    "cli_duration": sum(r.duration for r in cli_results if r)
                }

                print(f"  Batch {batch_size}: {accuracy:.1f}% accuracy ({matches}/{total})")

            except Exception as e:
                batch_results[batch_size] = {"error": str(e)}
                print(f"  Batch {batch_size}: ERROR - {e}")

        return {
            "database_path": database_path,
            "batch_validation": batch_results,
            "summary": self._generate_batch_summary(batch_results)
        }

    def _generate_validation_report(self, validation_results: List[ValidationResult]) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        total_tests = len(validation_results)
        successful_tests = sum(1 for r in validation_results if r.match)
        failed_tests = total_tests - successful_tests

        # Categorize results
        categories = {}
        for result in validation_results:
            category = result.test_case.category
            if category not in categories:
                categories[category] = {"total": 0, "passed": 0, "failed": 0}

            categories[category]["total"] += 1
            if result.match:
                categories[category]["passed"] += 1
            else:
                categories[category]["failed"] += 1

        # Performance analysis
        cli_times = [r.cli_result.duration for r in validation_results if r.cli_result]
        python_times = [r.python_result.duration for r in validation_results if r.python_result]

        avg_cli_time = sum(cli_times) / len(cli_times) if cli_times else 0
        avg_python_time = sum(python_times) / len(python_times) if python_times else 0

        overhead = (avg_python_time / avg_cli_time) if avg_cli_time > 0.001 else 0

        return {
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": failed_tests,
                "success_rate_percent": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
                "overall_status": "PASSED" if failed_tests == 0 else "FAILED"
            },
            "categories": categories,
            "performance": {
                "avg_cli_time_ms": avg_cli_time * 1000,
                "avg_python_time_ms": avg_python_time * 1000,
                "overhead_factor": overhead,
                "performance_target_met": overhead < 10.0  # <10x overhead
            },
            "detailed_results": [
                {
                    "kmer": r.test_case.kmer,
                    "description": r.test_case.description,
                    "category": r.test_case.category,
                    "match": r.match,
                    "cli_count": r.cli_result.count if r.cli_result else None,
                    "python_count": r.python_result.count if r.python_result else None,
                    "error": r.error
                }
                for r in validation_results
            ]
        }

    def _generate_batch_summary(self, batch_results: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        """Generate batch validation summary."""
        successful_batches = 0
        total_batches = len(batch_results)
        accuracies = []

        for batch_size, result in batch_results.items():
            if "error" not in result:
                successful_batches += 1
                accuracies.append(result["accuracy_percent"])

        return {
            "total_batches_tested": total_batches,
            "successful_batches": successful_batches,
            "average_accuracy_percent": sum(accuracies) / len(accuracies) if accuracies else 0,
            "batch_sizes_tested": list(batch_results.keys()),
            "overall_batch_status": "PASSED" if successful_batches == total_batches and all(acc == 100.0 for acc in accuracies) else "FAILED"
        }

    def save_validation_report(self, report: Dict[str, Any], output_path: str = None):
        """Save validation report to file."""
        if output_path is None:
            timestamp = int(time.time())
            output_path = f"tests/007-api-compatibility/test_reports/t026_query_validation_report_{timestamp}.json"

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Validation report saved to: {output_path}")
        return output_path


def main():
    """Main function for standalone testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Cross-platform query validator")
    parser.add_argument("database", help="Database file to test")
    parser.add_argument("--cli-path", help="Path to rustkmer CLI binary")
    parser.add_argument("--output", help="Output report path")
    parser.add_argument("--batch", action="store_true", help="Run batch query tests")

    args = parser.parse_args()

    validator = CrossPlatformQueryValidator(args.cli_path)

    # Run individual query validation
    report = validator.validate_database_compatibility(args.database)

    # Run batch validation if requested
    if args.batch:
        batch_report = validator.validate_batch_queries(args.database)
        report["batch_validation"] = batch_report

    # Save report
    output_path = validator.save_validation_report(report, args.output)

    # Print summary
    summary = report["summary"]
    print(f"\n📊 Validation Summary:")
    print(f"  Total tests: {summary['total_tests']}")
    print(f"  Successful: {summary['successful_tests']}")
    print(f"  Failed: {summary['failed_tests']}")
    print(f"  Success rate: {summary['success_rate_percent']:.1f}%")
    print(f"  Overall status: {summary['overall_status']}")

    if "performance" in report:
        perf = report["performance"]
        print(f"\n⚡ Performance:")
        print(f"  Avg CLI time: {perf['avg_cli_time_ms']:.3f}ms")
        print(f"  Avg Python time: {perf['avg_python_time_ms']:.3f}ms")
        print(f"  Overhead: {perf['overhead_factor']:.1f}x")
        print(f"  Performance target: {'✅ MET' if perf['performance_target_met'] else '❌ NOT MET'}")

    return summary["overall_status"] == "PASSED"


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)