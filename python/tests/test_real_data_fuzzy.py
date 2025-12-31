#!/usr/bin/env python3
"""
Real Data Fuzzy Query Test

This test compares fuzzy query results between rustkmer CLI and PyO3 binding
using real genomic database to ensure consistency.
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


class FuzzyQueryComparer:
    """Compare fuzzy query results between CLI and PyO3 binding."""

    def __init__(self, db_path):
        self.db_path = db_path
        self.cli_results = {}
        self.pyo3_results = {}

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
        """Run rustkmer CLI fuzzy query and parse results."""
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
                # Parse JSON output
                data = json.loads(result.stdout)
                return {
                    "success": True,
                    "total_matches": data.get("total_count", 0),
                    "matches": data.get("individual_matches", []),
                    "variants_generated": data.get("query_metadata", {}).get(
                        "variants_generated", 0
                    ),
                    "query_time_ms": data.get("query_metadata", {}).get(
                        "query_time_ms", 0
                    ),
                }
            else:
                return {"success": False, "error": f"CLI failed: {result.stderr}"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "CLI query timed out"}
        except Exception as e:
            return {"success": False, "error": f"CLI error: {str(e)}"}

    def run_pyo3_fuzzy_query(self, pattern, mutations=0, max_variants=1000):
        """Run PyO3 fuzzy query."""
        try:
            with Database(self.db_path) as db:
                result = db.fuzzy_query(
                    pattern, mutations=mutations, max_variants=max_variants
                )
                return {
                    "success": True,
                    "total_matches": result.total_matches,
                    "matches": [
                        {"sequence": m.kmer, "count": m.count, "distance": m.distance}
                        for m in result.matches
                    ],
                    "has_exact_match": result.has_exact_match,
                    "exact_match": {
                        "sequence": result.exact_match.kmer,
                        "count": result.exact_match.count,
                        "distance": result.exact_match.distance,
                    }
                    if result.exact_match
                    else None,
                }
        except Exception as e:
            return {"success": False, "error": f"PyO3 error: {str(e)}"}

    def compare_results(self, cli_result, pyo3_result, pattern, mutations):
        """Compare CLI and PyO3 results."""
        comparison = {
            "pattern": pattern,
            "mutations": mutations,
            "cli_success": cli_result["success"],
            "pyo3_success": pyo3_result["success"],
            "results_match": False,
            "differences": [],
        }

        # Check if both succeeded or both failed
        if cli_result["success"] != pyo3_result["success"]:
            comparison["differences"].append(
                f"Success status mismatch: CLI={cli_result['success']}, PyO3={pyo3_result['success']}"
            )
            if cli_result["success"]:
                comparison["differences"].append(
                    f"CLI error: {cli_result.get('error', 'Unknown')}"
                )
            if pyo3_result["success"]:
                comparison["differences"].append(
                    f"PyO3 error: {pyo3_result.get('error', 'Unknown')}"
                )
            return comparison

        # If both failed, compare error messages
        if not cli_result["success"]:
            comparison["results_match"] = cli_result.get(
                "error", ""
            ) == pyo3_result.get("error", "")
            if not comparison["results_match"]:
                comparison["differences"].append(
                    f"Error mismatch: CLI='{cli_result.get('error', '')}', PyO3='{pyo3_result.get('error', '')}'"
                )
            return comparison

        # Both succeeded - compare results
        cli_total = cli_result["total_matches"]
        pyo3_total = pyo3_result["total_matches"]

        if cli_total != pyo3_total:
            comparison["differences"].append(
                f"Total matches mismatch: CLI={cli_total}, PyO3={pyo3_total}"
            )

        # Compare individual matches (if counts match)
        if cli_total == pyo3_total and cli_total > 0:
            cli_matches = {(m["sequence"], m["count"]) for m in cli_result["matches"]}
            pyo3_matches = {(m["sequence"], m["count"]) for m in pyo3_result["matches"]}

            if cli_matches != pyo3_matches:
                comparison["differences"].append("Individual matches differ")
                comparison["differences"].append(f"CLI matches: {len(cli_matches)}")
                comparison["differences"].append(f"PyO3 matches: {len(pyo3_matches)}")

        comparison["results_match"] = len(comparison["differences"]) == 0
        return comparison

    def run_comprehensive_test(self, test_count=100, mutations_list=[0, 1, 2]):
        """Run comprehensive comparison test."""
        print(f"🧬 Starting Real Data Fuzzy Query Test")
        print(f"📊 Database: {self.db_path}")
        print(f"🔢 Test count: {test_count}")
        print(f"🧮 Mutation tolerances: {mutations_list}")
        print("=" * 60)

        # Generate test k-mers
        print("🎲 Generating random 19-mers with N wildcards...")
        test_kmers = self.generate_random_kmers_with_n(test_count)
        print(f"✅ Generated {len(test_kmers)} test k-mers")

        # Sample a few for display
        print("📝 Sample test k-mers:")
        for i, kmer in enumerate(test_kmers[:5]):
            print(f"   {i + 1}. {kmer}")
        print()

        all_comparisons = []
        total_tests = len(test_kmers) * len(mutations_list)
        completed_tests = 0

        start_time = time.time()

        for i, kmer in enumerate(test_kmers):
            print(f"📊 Processing k-mer {i + 1}/{len(test_kmers)}: {kmer}")

            for mutations in mutations_list:
                completed_tests += 1
                print(f"   🔍 Mutations={mutations} ({completed_tests}/{total_tests})")

                # Run CLI query
                cli_result = self.run_cli_fuzzy_query(kmer, mutations)

                # Run PyO3 query
                pyo3_result = self.run_pyo3_fuzzy_query(kmer, mutations)

                # Compare results
                comparison = self.compare_results(
                    cli_result, pyo3_result, kmer, mutations
                )
                all_comparisons.append(comparison)

                # Report differences immediately
                if not comparison["results_match"]:
                    print(f"   ❌ MISMATCH DETECTED:")
                    for diff in comparison["differences"]:
                        print(f"      - {diff}")
                else:
                    print(f"   ✅ Results match")

                # Progress update every 10 tests
                if completed_tests % 10 == 0:
                    elapsed = time.time() - start_time
                    eta = (elapsed / completed_tests) * (total_tests - completed_tests)
                    print(
                        f"   ⏱️  Progress: {completed_tests}/{total_tests} ({completed_tests / total_tests * 100:.1f}%)"
                    )
                    print(f"   ⏰ ETA: {eta / 60:.1f} minutes")

                # Small delay to avoid overwhelming the system
                time.sleep(0.1)

        # Summary
        self.generate_summary_report(all_comparisons)
        return all_comparisons

    def generate_summary_report(self, comparisons):
        """Generate comprehensive summary report."""
        total_tests = len(comparisons)
        matching_tests = sum(1 for c in comparisons if c["results_match"])
        mismatched_tests = total_tests - matching_tests

        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY REPORT")
        print("=" * 60)
        print(f"📊 Total tests: {total_tests}")
        print(f"✅ Matching results: {matching_tests}")
        print(f"❌ Mismatched results: {mismatched_tests}")
        print(f"📈 Success rate: {matching_tests / total_tests * 100:.2f}%")

        if mismatched_tests > 0:
            print(f"\n🚨 MISMATCH ANALYSIS:")

            # Analyze mismatch types
            mismatch_types = {}
            for comp in comparisons:
                if not comp["results_match"]:
                    for diff in comp["differences"]:
                        mismatch_type = diff.split(":")[0] if ":" in diff else diff
                        mismatch_types[mismatch_type] = (
                            mismatch_types.get(mismatch_type, 0) + 1
                        )

            for mismatch_type, count in sorted(
                mismatch_types.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"   - {mismatch_type}: {count} occurrences")

            # Show some examples
            print(f"\n📝 MISMATCH EXAMPLES:")
            examples_shown = 0
            for comp in comparisons:
                if not comp["results_match"] and examples_shown < 5:
                    print(
                        f"   Pattern: {comp['pattern']} (mutations={comp['mutations']})"
                    )
                    for diff in comp["differences"]:
                        print(f"      - {diff}")
                    examples_shown += 1

            print(f"\n🔧 ACTION REQUIRED:")
            print(
                f"   PyO3 fuzzy query implementation needs to be fixed to match CLI behavior."
            )
        else:
            print(f"\n🎉 ALL TESTS PASSED!")
            print(f"   PyO3 fuzzy query implementation is consistent with CLI.")

        # Save detailed report
        report_path = Path(__file__).parent / "fuzzy_query_comparison_report.json"
        with open(report_path, "w") as f:
            json.dump(comparisons, f, indent=2)
        print(f"\n💾 Detailed report saved to: {report_path}")


def main():
    """Main test function."""
    # Real database path
    db_path = "/Users/forrest/Data/data/kmer/K19/R1_001.rkdb"

    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        print("Please ensure the real database file exists.")
        return

    # Initialize comparer
    comparer = FuzzyQueryComparer(db_path)

    # Run comprehensive test (using smaller sample for initial testing)
    # Using 20 k-mers and 2 mutation levels for quick verification
    comparisons = comparer.run_comprehensive_test(test_count=20, mutations_list=[0, 1])

    # Additional verification with known patterns
    print(f"\n🎯 ADDITIONAL VERIFICATION TESTS")
    print("=" * 40)

    known_patterns = [
        "AAAAAAAAAAAAAAAAAAA",  # All A
        "ATCGATCGATCGATCGAT",  # Repeating pattern
        "ANNNNNNNNNNNNNNNNNN",  # Many N's
        "ATCNATCNATCNATCNAT",  # N in middle
    ]

    for pattern in known_patterns:
        print(f"🧪 Testing pattern: {pattern}")
        cli_result = comparer.run_cli_fuzzy_query(pattern, mutations=0)
        pyo3_result = comparer.run_pyo3_fuzzy_query(pattern, mutations=0)
        comparison = comparer.compare_results(cli_result, pyo3_result, pattern, 0)

        if comparison["results_match"]:
            print(f"   ✅ Results match ({cli_result['total_matches']} matches)")
        else:
            print(f"   ❌ Results differ:")
            for diff in comparison["differences"]:
                print(f"      - {diff}")

    print(f"\n✅ Real data fuzzy query test completed!")


if __name__ == "__main__":
    main()
