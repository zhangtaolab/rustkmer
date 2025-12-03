#!/usr/bin/env python3
"""
Query comparison utilities for CLI vs Python API compatibility testing.
"""

import os
import subprocess
import json
from typing import Dict, List, Any, Tuple
import tempfile

class QueryComparator:
    """Compare query results between CLI and Python API."""

    def __init__(self, cli_path: str = "rustkmer"):
        self.cli_path = cli_path
        self.query_results = []

    def query_database_cli(
        self,
        database_path: str,
        kmer: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Query database using Rust CLI."""
        cmd = [
            self.cli_path, "query",
            "-d", database_path,
            kmer
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=60  # 1 minute timeout
            )

            # Parse CLI output (expecting format: kmer count)
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 1:
                line = lines[0].strip()
                if '\t' in line:
                    kmer_out, count = line.split('\t', 1)
                    try:
                        count = int(count)
                        return True, {"kmer": kmer_out, "count": count, "found": True}
                    except ValueError:
                        return False, {"error": f"Invalid count format: {count}"}
                else:
                    return True, {"kmer": line, "count": 0, "found": False}

            return False, {"error": "No output from CLI"}

        except subprocess.CalledProcessError as e:
            return False, {"error": f"CLI Error: {e.stderr}"}
        except subprocess.TimeoutExpired:
            return False, {"error": "CLI Error: Timeout exceeded"}

    def query_database_python(
        self,
        database_path: str,
        kmer: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Query database using Python API."""
        try:
            # Import rustkmer Python API
            import rustkmer
            from rustkmer import Database

            # Open database
            db = Database(database_path)
            result = db.query(kmer)

            return True, {
                "kmer": kmer,
                "found": result.found,
                "count": result.count if result.found else 0
            }

        except ImportError as e:
            return False, {"error": f"Python API Error: Module not found - {e}"}
        except Exception as e:
            return False, {"error": f"Python API Error: {e}"}

    def run_query_compatibility_test(
        self,
        database_path: str,
        test_kmers: List[str]
    ) -> Dict[str, Any]:
        """Run query compatibility test between CLI and Python API."""
        results = {
            "database_path": database_path,
            "test_kmers": test_kmers,
            "individual_results": [],
            "summary": None
        }

        matching_results = 0
        total_tests = len(test_kmers)

        for kmer in test_kmers:
            # Query with CLI
            cli_success, cli_result = self.query_database_cli(database_path, kmer)

            # Query with Python API
            python_success, python_result = self.query_database_python(database_path, kmer)

            # Compare results
            comparison = self._compare_query_results(cli_result, python_result, cli_success, python_success)

            test_result = {
                "kmer": kmer,
                "cli_success": cli_success,
                "python_success": python_success,
                "cli_result": cli_result,
                "python_result": python_result,
                "comparison": comparison
            }

            results["individual_results"].append(test_result)

            if comparison["identical"]:
                matching_results += 1

        # Generate summary
        results["summary"] = {
            "total_queries": total_tests,
            "matching_results": matching_results,
            "accuracy_rate": (matching_results / total_tests) * 100 if total_tests > 0 else 0,
            "all_identical": matching_results == total_tests
        }

        self.query_results.append(results)
        return results

    def _compare_query_results(
        self,
        cli_result: Dict[str, Any],
        python_result: Dict[str, Any],
        cli_success: bool,
        python_success: bool
    ) -> Dict[str, Any]:
        """Compare query results between CLI and Python API."""

        if not cli_success or not python_success:
            return {
                "identical": False,
                "reason": f"Query failed - CLI: {cli_success}, Python: {python_success}",
                "cli_error": cli_result.get("error"),
                "python_error": python_result.get("error")
            }

        # Check if both found the kmer
        cli_found = cli_result.get("found", False)
        python_found = python_result.get("found", False)

        if cli_found != python_found:
            return {
                "identical": False,
                "reason": f"Found status mismatch - CLI: {cli_found}, Python: {python_found}",
                "cli_found": cli_found,
                "python_found": python_found
            }

        # Check counts
        cli_count = cli_result.get("count", 0)
        python_count = python_result.get("count", 0)

        if cli_count != python_count:
            return {
                "identical": False,
                "reason": f"Count mismatch - CLI: {cli_count}, Python: {python_count}",
                "cli_count": cli_count,
                "python_count": python_count
            }

        # Check kmer values (case-sensitive comparison)
        cli_kmer = cli_result.get("kmer", "")
        python_kmer = python_result.get("kmer", "")

        if cli_kmer.upper() != python_kmer.upper():
            return {
                "identical": False,
                "reason": f"Kmer mismatch - CLI: {cli_kmer}, Python: {python_kmer}",
                "cli_kmer": cli_kmer,
                "python_kmer": python_kmer
            }

        return {
            "identical": True,
            "found": cli_found,
            "count": cli_count,
            "kmer": cli_kmer
        }

    def get_query_test_summary(self) -> Dict[str, Any]:
        """Get summary of all query compatibility tests."""
        if not self.query_results:
            return {"total_test_suites": 0, "average_accuracy": 0, "perfect_suites": 0}

        total_suites = len(self.query_results)
        perfect_suites = sum(1 for result in self.query_results
                           if result.get("summary", {}).get("all_identical", False))
        avg_accuracy = sum(result.get("summary", {}).get("accuracy_rate", 0)
                         for result in self.query_results) / total_suites

        return {
            "total_test_suites": total_suites,
            "perfect_suites": perfect_suites,
            "average_accuracy": avg_accuracy,
            "perfect_suite_rate": (perfect_suites / total_suites) * 100 if total_suites > 0 else 0
        }


# Example usage
if __name__ == "__main__":
    comparator = QueryComparator()

    # Example test with sample k-mers
    test_kmers = [
        "ACGTACGTACGTACGTACGT",
        "TGCATGCATGCATGCATGCA",
        "AAAAAAAAAAAAAAAAAAAA",  # Likely not found
        "CCCCCCCCCCCCCCCCCCCC"   # Likely not found
    ]

    # Test with a sample database if available
    sample_db = "test_databases/sample_database.rkdb"
    if os.path.exists(sample_db):
        print(f"Testing query compatibility with {sample_db}")
        result = comparator.run_query_compatibility_test(sample_db, test_kmers)
        print(f"Results: {result['summary']}")
    else:
        print(f"Sample database not found: {sample_db}")

    summary = comparator.get_query_test_summary()
    print(f"Query Test Summary: {summary}")