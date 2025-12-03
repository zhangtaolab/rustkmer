#!/usr/bin/env python3
"""
Fuzzy Query Comparator for CLI vs Python API Compatibility Testing

This framework tests wildcard patterns ('N') and mutation tolerance (Hamming distance)
to ensure that the Python API fuzzy query produces identical results to the CLI.
"""

import os
import sys
import subprocess
import json
import time
import tempfile
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
class FuzzyQueryTestCase:
    """Represents a single fuzzy query test case."""
    query: str
    kmer_size: int
    mutation_tolerance: int = 0
    max_variants: int = 10000
    description: str = ""
    category: str = "basic"
    expected_variants: Optional[int] = None  # Expected number of variants to generate


@dataclass
class FuzzyQueryResult:
    """Represents a fuzzy query result from either CLI or Python API."""
    query: str
    kmer_size: int
    mutation_tolerance: int
    total_matches: int
    total_variants: int
    matches: List[Dict[str, Any]]  # List of match results
    duration: float = 0.0
    source: str = ""  # "cli" or "python"
    error: Optional[str] = None


@dataclass
class FuzzyValidationResult:
    """Represents validation result for a fuzzy query test."""
    test_case: FuzzyQueryTestCase
    cli_result: Optional[FuzzyQueryResult] = None
    python_result: Optional[FuzzyQueryResult] = None
    match: bool = False
    error: Optional[str] = None


class FuzzyQueryComparator:
    """Comprehensive fuzzy query compatibility validator between CLI and Python API."""

    def __init__(self, cli_path: str = None):
        """
        Initialize the fuzzy query comparator.

        Args:
            cli_path: Path to the rustkmer CLI binary
        """
        self.cli_path = cli_path or self._find_cli_binary()
        self.test_results: List[FuzzyValidationResult] = []

    def _find_cli_binary(self) -> str:
        """Find the rustkmer CLI binary."""
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

    def _run_cli_fuzzy_query(self, database_path: str, query: str, kmer_size: int,
                           mutation_tolerance: int = 0, max_variants: int = 10000) -> Tuple[Optional[FuzzyQueryResult], Optional[str]]:
        """Run a fuzzy query using CLI."""
        try:
            start_time = time.time()

            # Build CLI command
            cmd = [
                self.cli_path, "fuzzy-query",
                database_path, query,
                "--mutations", str(mutation_tolerance),
                "--max-variants", str(max_variants),
                "--format", "json",
                "--quiet"  # Suppress non-error output
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout for fuzzy queries
            )

            duration = time.time() - start_time

            if result.returncode == 0:
                # Parse JSON output
                try:
                    output_data = json.loads(result.stdout.strip())

                    # Extract match information from CLI output
                    matches = []
                    if "matches" in output_data:
                        for match in output_data["matches"]:
                            matches.append({
                                "sequence": match.get("sequence", ""),
                                "count": match.get("count", 0),
                                "distance": match.get("distance", 0),
                                "type": match.get("type", "unknown")
                            })

                    return FuzzyQueryResult(
                        query=query,
                        kmer_size=kmer_size,
                        mutation_tolerance=mutation_tolerance,
                        total_matches=output_data.get("total_matches", 0),
                        total_variants=output_data.get("variants_generated", 0),
                        matches=matches,
                        duration=duration,
                        source="cli"
                    ), None

                except json.JSONDecodeError as e:
                    # Fallback: parse text output if JSON parsing fails
                    return self._parse_cli_text_output(result.stdout, query, kmer_size, mutation_tolerance, duration), None

            else:
                return None, f"CLI error: {result.stderr}"

        except subprocess.TimeoutExpired:
            return None, "CLI fuzzy query timeout"
        except Exception as e:
            return None, f"CLI exception: {str(e)}"

    def _parse_cli_text_output(self, output: str, query: str, kmer_size: int,
                             mutation_tolerance: int, duration: float) -> FuzzyQueryResult:
        """Parse CLI text output as fallback when JSON parsing fails."""
        lines = output.strip().split('\n')

        # Extract basic information from text output
        total_matches = 0
        total_variants = 0
        matches = []

        for line in lines:
            if "Total Matches:" in line:
                total_matches = int(line.split(":")[-1].strip())
            elif "Variants Generated:" in line:
                total_variants = int(line.split(":")[-1].strip())
            elif line.strip() and not line.startswith("Query:") and not line.startswith("Mutations:") and not line.startswith("┌"):
                # Try to parse match line
                parts = line.split()
                if len(parts) >= 2 and parts[0].replace('-', '').replace('│', '').strip():
                    sequence = parts[0].replace('│', '').strip()
                    try:
                        count = int(parts[1].replace('│', '').strip())
                        matches.append({
                            "sequence": sequence,
                            "count": count,
                            "distance": 0,
                            "type": "exact"
                        })
                    except ValueError:
                        continue

        return FuzzyQueryResult(
            query=query,
            kmer_size=kmer_size,
            mutation_tolerance=mutation_tolerance,
            total_matches=total_matches,
            total_variants=total_variants,
            matches=matches,
            duration=duration,
            source="cli"
        )

    def _run_python_fuzzy_query(self, database_path: str, query: str, kmer_size: int,
                              mutation_tolerance: int = 0, max_variants: int = 10000) -> Tuple[Optional[FuzzyQueryResult], Optional[str]]:
        """Run a fuzzy query using Python API."""
        if rustkmer is None:
            return None, "Python rustkmer module not available"

        try:
            start_time = time.time()

            # Use Python API for fuzzy query
            fuzzy_query = rustkmer.FuzzyQuery(
                query_string=query,
                kmer_size=kmer_size,
                mutation_tolerance=mutation_tolerance,
                max_variants=max_variants
            )

            results = fuzzy_query.execute(database_path)
            duration = time.time() - start_time

            # Convert Python results to our format
            matches = []
            for result in results:
                matches.append({
                    "sequence": result.kmer,
                    "count": result.count,
                    "distance": result.distance,
                    "type": "fuzzy" if result.distance > 0 else "exact"
                })

            return FuzzyQueryResult(
                query=query,
                kmer_size=kmer_size,
                mutation_tolerance=mutation_tolerance,
                total_matches=len(results),
                total_variants=fuzzy_query.get_variant_count(),
                matches=matches,
                duration=duration,
                source="python"
            ), None

        except Exception as e:
            return None, f"Python API exception: {str(e)}"

    def create_test_cases(self, kmer_size: int = 13) -> List[FuzzyQueryTestCase]:
        """Create comprehensive fuzzy query test cases for given k-mer size."""
        test_cases = []

        # Basic exact matches (no wildcards, no mutations)
        exact_matches = [
            "ACGTACGTACGTAC",
            "AAAAAAAAAAAAAA",
            "CCCCCCCCCCCCCC",
            "GGGGGGGGGGGGGG",
            "TTTTTTTTTTTTTT"
        ]

        for query in exact_matches:
            if len(query) == kmer_size:
                test_cases.append(FuzzyQueryTestCase(
                    query=query,
                    kmer_size=kmer_size,
                    description=f"Exact match: {query[:8]}...",
                    category="exact",
                    expected_variants=1
                ))

        # Single wildcard tests
        single_wildcard_patterns = [
            f"ACGTACGTACGT{'N'}",
            f"{'N'}CGTACGTACGTAC",
            f"ACGTACGT{'N'}GTAC",
        ]

        for query in single_wildcard_patterns:
            if len(query) == kmer_size:
                test_cases.append(FuzzyQueryTestCase(
                    query=query,
                    kmer_size=kmer_size,
                    description=f"Single wildcard: {query}",
                    category="wildcard_1",
                    expected_variants=4  # N -> A,C,G,T
                ))

        # Multiple wildcard tests
        multi_wildcard_patterns = [
            f"ACGTACGT{'N'}{'N'}AC",
            f"{'N'}CGT{'N'}CGTACGTAC",
            f"ACGT{'N'}GT{'N'}GTAC",
        ]

        for query in multi_wildcard_patterns:
            if len(query) == kmer_size:
                n_count = query.count('N')
                expected_variants = min(4 ** n_count, 10000)  # Cap at max_variants
                test_cases.append(FuzzyQueryTestCase(
                    query=query,
                    kmer_size=kmer_size,
                    description=f"Multiple wildcards ({n_count} N's): {query}",
                    category="wildcard_multi",
                    expected_variants=expected_variants
                ))

        # Mutation tolerance tests (no wildcards, but allow mutations)
        mutation_test_queries = [
            "ACGTACGTACGTAC",
            "CCCCCCCCCCCCCC",
        ]

        for query in mutation_test_queries:
            if len(query) == kmer_size:
                for mutation_tolerance in [1, 2, 3]:
                    test_cases.append(FuzzyQueryTestCase(
                        query=query,
                        kmer_size=kmer_size,
                        mutation_tolerance=mutation_tolerance,
                        description=f"Mutation tolerance {mutation_tolerance}: {query[:8]}...",
                        category="mutation",
                        expected_variants=None  # Harder to predict
                    ))

        # Mixed wildcard and mutation tests
        mixed_tests = [
            ("ACGTACGTACGTNG", 1),
            ("ACGTNGTACGTAC", 2),
        ]

        for query, mutations in mixed_tests:
            if len(query) == kmer_size:
                test_cases.append(FuzzyQueryTestCase(
                    query=query,
                    kmer_size=kmer_size,
                    mutation_tolerance=mutations,
                    description=f"Mixed wildcard + mutation {mutations}: {query}",
                    category="mixed",
                    expected_variants=None
                ))

        # Edge cases
        edge_cases = [
            FuzzyQueryTestCase(
                query="N" * kmer_size,
                kmer_size=kmer_size,
                description="All wildcards",
                category="edge",
                expected_variants=min(4 ** kmer_size, 10000)
            ),
            FuzzyQueryTestCase(
                query="ACGTACGTACGTAC"[:kmer_size-2] + "NN",
                kmer_size=kmer_size,
                description="Trailing wildcards",
                category="edge",
                expected_variants=16
            ),
        ]

        test_cases.extend(edge_cases)

        return test_cases

    def validate_fuzzy_query_compatibility(self, database_path: str,
                                         test_cases: List[FuzzyQueryTestCase] = None) -> Dict[str, Any]:
        """
        Validate fuzzy query compatibility for a database.

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
                    kmer_size = 13  # Default fallback
                test_cases = self.create_test_cases(kmer_size)
            except Exception as e:
                return {"error": f"Failed to determine k-mer size: {str(e)}"}

        validation_results = []

        print(f"Testing fuzzy queries on database: {database_path}")
        print(f"Running {len(test_cases)} fuzzy query validation tests...")

        for i, test_case in enumerate(test_cases, 1):
            print(f"  Test {i}/{len(test_cases)}: {test_case.description}")

            result = FuzzyValidationResult(test_case=test_case)

            # Run CLI fuzzy query
            cli_result, cli_error = self._run_cli_fuzzy_query(
                database_path, test_case.query, test_case.kmer_size,
                test_case.mutation_tolerance, test_case.max_variants
            )

            if cli_error:
                result.error = f"CLI error: {cli_error}"
            else:
                result.cli_result = cli_result

            # Run Python API fuzzy query
            python_result, python_error = self._run_python_fuzzy_query(
                database_path, test_case.query, test_case.kmer_size,
                test_case.mutation_tolerance, test_case.max_variants
            )

            if python_error:
                if result.error:
                    result.error += f"; Python error: {python_error}"
                else:
                    result.error = f"Python error: {python_error}"
            else:
                result.python_result = python_result

            # Check for match
            if cli_result and python_result:
                result.match = self._compare_fuzzy_results(cli_result, python_result)

            validation_results.append(result)

            # Print result
            if result.match:
                print(f"    ✅ MATCH: variants={cli_result.total_variants if cli_result else 'N/A'}, matches={cli_result.total_matches if cli_result else 'N/A'}")
            else:
                cli_info = f"variants={cli_result.total_variants}, matches={cli_result.total_matches}" if cli_result else "ERROR"
                python_info = f"variants={python_result.total_variants}, matches={python_result.total_matches}" if python_result else "ERROR"
                print(f"    ❌ MISMATCH: CLI={cli_info}, Python={python_info}")

        self.test_results.extend(validation_results)

        return self._generate_validation_report(validation_results)

    def _compare_fuzzy_results(self, cli_result: FuzzyQueryResult, python_result: FuzzyQueryResult) -> bool:
        """Compare two fuzzy query results for equality."""
        # Check basic metrics
        if cli_result.total_matches != python_result.total_matches:
            return False

        if cli_result.total_variants != python_result.total_variants:
            return False

        # Check individual matches
        if len(cli_result.matches) != len(python_result.matches):
            return False

        # Sort matches by sequence for comparison
        cli_matches = sorted(cli_result.matches, key=lambda x: x["sequence"])
        python_matches = sorted(python_result.matches, key=lambda x: x["sequence"])

        for cli_match, python_match in zip(cli_matches, python_matches):
            if (cli_match["sequence"] != python_match["sequence"] or
                cli_match["count"] != python_match["count"] or
                cli_match["distance"] != python_match["distance"]):
                return False

        return True

    def _generate_validation_report(self, validation_results: List[FuzzyValidationResult]) -> Dict[str, Any]:
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
                "performance_target_met": overhead < 20.0  # <20x overhead for fuzzy queries
            },
            "detailed_results": [
                {
                    "query": r.test_case.query,
                    "kmer_size": r.test_case.kmer_size,
                    "mutation_tolerance": r.test_case.mutation_tolerance,
                    "description": r.test_case.description,
                    "category": r.test_case.category,
                    "expected_variants": r.test_case.expected_variants,
                    "match": r.match,
                    "cli_variants": r.cli_result.total_variants if r.cli_result else None,
                    "python_variants": r.python_result.total_variants if r.python_result else None,
                    "cli_matches": r.cli_result.total_matches if r.cli_result else None,
                    "python_matches": r.python_result.total_matches if r.python_result else None,
                    "error": r.error
                }
                for r in validation_results
            ]
        }

    def save_validation_report(self, report: Dict[str, Any], output_path: str = None):
        """Save validation report to file."""
        if output_path is None:
            timestamp = int(time.time())
            output_path = f"tests/007-api-compatibility/test_reports/fuzzy_query_validation_report_{timestamp}.json"

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Fuzzy query validation report saved to: {output_path}")
        return output_path


def main():
    """Main function for standalone testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Fuzzy query compatibility validator")
    parser.add_argument("database", help="Database file to test")
    parser.add_argument("--cli-path", help="Path to rustkmer CLI binary")
    parser.add_argument("--output", help="Output report path")
    parser.add_argument("--kmer-size", type=int, default=13, help="K-mer size for test cases")

    args = parser.parse_args()

    comparator = FuzzyQueryComparator(args.cli_path)

    # Run fuzzy query validation
    report = comparator.validate_fuzzy_query_compatibility(args.database)

    # Save report
    output_path = comparator.save_validation_report(report, args.output)

    # Print summary
    summary = report["summary"]
    print(f"\n📊 Fuzzy Query Validation Summary:")
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