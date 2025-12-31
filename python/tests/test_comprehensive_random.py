#!/usr/bin/env python3
"""
Comprehensive Random Test for Fuzzy Query Fix

Generate 100 random 19-mers with N wildcards and test consistency
between CLI and PyO3 fuzzy query results.
"""

import os
import sys
import subprocess
import json
import random
import time
from pathlib import Path

# Add the parent directory to path to import rustkmer modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from rustkmer import Database
from rustkmer.fuzzy_fix import FixedFuzzyQuery


class ComprehensiveRandomTest:
    """Comprehensive random test for fuzzy query consistency."""

    def __init__(self, db_path):
        self.db_path = db_path
        self.results = []

    def generate_random_kmers_with_n(self, count=100, kmer_size=19, n_probability=0.1):
        """Generate random k-mers with N wildcards."""
        nucleotides = ["A", "T", "C", "G"]
        random_kmers = []

        for _ in range(count):
            kmer = []
            for _ in range(kmer_size):
                if random.random() < n_probability:
                    kmer.append("N")
                else:
                    kmer.append(random.choice(nucleotides))
            random_kmers.append("".join(kmer))

        return random_kmers

    def run_cli_fuzzy_query(self, pattern, mutations=0, max_variants=1000):
        """Run rustkmer CLI fuzzy query."""
        cmd = [
            "rustkmer",
            "fuzzy-query",
            self.db_path,
            pattern,
            "--mutations",
            str(mutations),
            "--max-variants",
            str(max_variants),
            "--format",
            "json",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return {
                    "success": True,
                    "total_matches": data.get("total_count", 0),
                    "variants_generated": data.get("query_metadata", {}).get(
                        "variants_generated", 0
                    ),
                }
            else:
                # Check if it's a combinatorial explosion error
                if "Too many variants generated" in result.stderr:
                    return {
                        "success": False,
                        "error": "combinatorial_explosion",
                        "error_details": result.stderr.strip(),
                    }
                else:
                    return {
                        "success": False,
                        "error": "cli_failed",
                        "error_details": result.stderr.strip(),
                    }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "timeout",
                "error_details": "CLI query timed out",
            }
        except Exception as e:
            return {"success": False, "error": "exception", "error_details": str(e)}

    def run_pyo3_fuzzy_query(self, pattern, mutations=0, max_variants=1000):
        """Run PyO3 fuzzy query using fixed implementation."""
        try:
            fixed_db = FixedFuzzyQuery(self.db_path)
            result = fixed_db.fuzzy_query(
                pattern, mutations=mutations, max_variants=max_variants
            )
            return {
                "success": True,
                "total_matches": result.total_matches,
                "match_count": result.match_count,
                "consistent": result.total_matches == result.match_count,
            }
        except Exception as e:
            return {"success": False, "error": "pyo3_failed", "error_details": str(e)}

    def test_single_pattern(self, pattern, mutations=0, max_variants=1000):
        """Test a single pattern."""
        # CLI query
        cli_result = self.run_cli_fuzzy_query(pattern, mutations, max_variants)

        # PyO3 query
        pyo3_result = self.run_pyo3_fuzzy_query(pattern, mutations, max_variants)

        # Compare results
        comparison = {
            "pattern": pattern,
            "mutations": mutations,
            "cli_result": cli_result,
            "pyo3_result": pyo3_result,
            "consistent": False,
            "error_type": None,
        }

        # Determine consistency
        if cli_result["success"] and pyo3_result["success"]:
            # Both succeeded - compare counts
            if cli_result["total_matches"] == pyo3_result["total_matches"]:
                comparison["consistent"] = True
            else:
                comparison["error_type"] = "count_mismatch"
        elif not cli_result["success"] and not pyo3_result["success"]:
            # Both failed - check if it's the same reason
            if (
                cli_result["error"] == "combinatorial_explosion"
                and pyo3_result["error"] == "pyo3_failed"
                and "variants" in pyo3_result["error_details"]
            ):
                # Both hit combinatorial explosion - this is consistent
                comparison["consistent"] = True
            else:
                comparison["error_type"] = "failure_mismatch"
        else:
            # One succeeded, one failed - inconsistent
            comparison["error_type"] = "success_mismatch"

        return comparison

    def run_comprehensive_test(self, test_count=100, mutations_list=[0, 1]):
        """Run comprehensive random test."""
        print(f"🧬 Comprehensive Random Fuzzy Query Test")
        print(f"📊 Database: {self.db_path}")
        print(f"🎲 Generating {test_count} random 19-mers with N wildcards...")

        # Generate test k-mers
        test_kmers = self.generate_random_kmers_with_n(test_count)
        print(f"✅ Generated {len(test_kmers)} test k-mers")

        # Sample a few for display
        print("📝 Sample test k-mers:")
        for i, kmer in enumerate(test_kmers[:5]):
            print(f"   {i + 1}. {kmer}")
        print()

        all_tests = []
        total_queries = len(test_kmers) * len(mutations_list)
        completed_queries = 0

        start_time = time.time()

        for i, kmer in enumerate(test_kmers):
            print(f"📊 Processing k-mer {i + 1}/{len(test_kmers)}: {kmer}")

            for mutations in mutations_list:
                completed_queries += 1
                print(
                    f"   🔍 Mutations={mutations} ({completed_queries}/{total_queries})"
                )

                # Test the pattern
                comparison = self.test_single_pattern(kmer, mutations)
                all_tests.append(comparison)

                # Report progress and any inconsistencies
                if comparison["consistent"]:
                    print(f"   ✅ Consistent result")
                else:
                    print(f"   ❌ Inconsistent:")
                    if comparison["error_type"] == "count_mismatch":
                        cli_count = comparison["cli_result"]["total_matches"]
                        pyo3_count = comparison["pyo3_result"]["total_matches"]
                        print(
                            f"      Count mismatch: CLI={cli_count}, PyO3={pyo3_count}"
                        )
                    elif comparison["error_type"] == "success_mismatch":
                        print(
                            f"      Success mismatch: CLI={'success' if comparison['cli_result']['success'] else 'failed'}, PyO3={'success' if comparison['pyo3_result']['success'] else 'failed'}"
                        )
                    else:
                        print(f"      Other inconsistency: {comparison['error_type']}")

                # Progress update every 10 queries
                if completed_queries % 10 == 0:
                    elapsed = time.time() - start_time
                    eta = (elapsed / completed_queries) * (
                        total_queries - completed_queries
                    )
                    print(
                        f"   ⏱️  Progress: {completed_queries}/{total_queries} ({completed_queries / total_queries * 100:.1f}%)"
                    )
                    print(f"   ⏰ ETA: {eta / 60:.1f} minutes")

        # Generate summary report
        self.generate_summary_report(all_tests)
        return all_tests

    def generate_summary_report(self, all_tests):
        """Generate comprehensive summary report."""
        total_tests = len(all_tests)
        consistent_tests = sum(1 for t in all_tests if t["consistent"])
        inconsistent_tests = total_tests - consistent_tests

        print("\n" + "=" * 70)
        print("📋 COMPREHENSIVE TEST SUMMARY REPORT")
        print("=" * 70)
        print(f"📊 Total tests: {total_tests}")
        print(f"✅ Consistent results: {consistent_tests}")
        print(f"❌ Inconsistent results: {inconsistent_tests}")
        print(f"📈 Consistency rate: {consistent_tests / total_tests * 100:.2f}%")

        # Analyze error types
        error_types = {}
        for test in all_tests:
            if not test["consistent"]:
                error_type = test["error_type"]
                error_types[error_type] = error_types.get(error_type, 0) + 1

        if error_types:
            print(f"\n🚨 INCONSISTENCY ANALYSIS:")
            for error_type, count in sorted(
                error_types.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"   - {error_type}: {count} occurrences")

        if consistent_tests == total_tests:
            print(f"\n🎉 ALL TESTS PASSED!")
            print(f"   PyO3 fuzzy query implementation is fully consistent with CLI.")
            print(f"   The fix successfully resolves all consistency issues.")
        elif consistent_tests > total_tests * 0.9:
            print(f"\n✅ MOSTLY CONSISTENT!")
            print(
                f"   {consistent_tests}/{total_tests} tests passed ({consistent_tests / total_tests * 100:.1f}%)"
            )
            print(f"   This indicates the fix is working well with minor issues.")
        else:
            print(f"\n🚨 SIGNIFICANT INCONSISTENCIES DETECTED!")
            print(
                f"   Only {consistent_tests}/{total_tests} tests passed ({consistent_tests / total_tests * 100:.1f}%)"
            )
            print(f"   Further investigation and fixes may be needed.")

        # Save detailed report
        report_path = Path(__file__).parent / "comprehensive_fuzzy_test_report.json"
        with open(report_path, "w") as f:
            json.dump(all_tests, f, indent=2)
        print(f"\n💾 Detailed report saved to: {report_path}")


def main():
    """Main test function."""
    # Real database path
    db_path = "/Users/forrest/Data/data/kmer/K19/R1_001.rkdb"

    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return False

    # Initialize tester
    tester = ComprehensiveRandomTest(db_path)

    # Run comprehensive test with smaller count for initial testing
    test_count = 20  # Start with 20 for quick verification
    mutations_list = [0, 1]  # Test with 0 and 1 mutations

    tests = tester.run_comprehensive_test(test_count, mutations_list)

    # Count consistent tests
    consistent_count = sum(1 for t in tests if t["consistent"])
    success_rate = consistent_count / len(tests) * 100

    print(f"\n✅ COMPREHENSIVE TEST COMPLETED!")
    print(f"   Consistency rate: {success_rate:.1f}%")

    if success_rate >= 90:
        print(f"   The fix is working well! ✅")
        return True
    else:
        print(f"   There are still issues to resolve. ❌")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
