#!/usr/bin/env python3
"""
Real Data Fuzzy Query Consistency Test

This test compares fuzzy query results between rustkmer CLI and fixed PyO3 binding
using real genomic database to ensure consistency.
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path

# Add the parent directory to path to import rustkmer modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from rustkmer import Database
from rustkmer.fuzzy_fix import FixedFuzzyQuery


class RealDataConsistencyTest:
    """Test consistency between CLI and PyO3 fuzzy query results."""

    def __init__(self, db_path):
        self.db_path = db_path

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
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return {
                    "success": True,
                    "total_matches": data.get("total_count", 0),
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
                "has_exact_match": result.has_exact_match,
                "fuzzy_match_count": len(result.fuzzy_matches),
            }
        except Exception as e:
            return {"success": False, "error": f"PyO3 error: {str(e)}"}

    def run_comprehensive_test(self, test_patterns):
        """Run comprehensive consistency test."""
        print(f"🧬 Real Data Fuzzy Query Consistency Test")
        print(f"📊 Database: {self.db_path}")
        print(
            f"📁 Database size: {os.path.getsize(self.db_path) / (1024 * 1024 * 1024):.1f} GB"
        )
        print(f"🧪 Test patterns: {len(test_patterns)}")
        print("=" * 70)

        all_tests_passed = True
        total_tests = len(test_patterns)
        passed_tests = 0

        for i, (pattern, mutations) in enumerate(test_patterns):
            print(
                f"\n📝 Test {i + 1}/{total_tests}: Pattern='{pattern}', mutations={mutations}"
            )

            # CLI query
            print("   🖥️  Running CLI query...")
            cli_result = self.run_cli_fuzzy_query(pattern, mutations)

            if not cli_result["success"]:
                print(f"   ❌ CLI failed: {cli_result['error']}")
                all_tests_passed = False
                continue

            print(
                f"   ✅ CLI: {cli_result['total_matches']} matches ({cli_result['variants_generated']} variants)"
            )

            # PyO3 query
            print("   🐍 Running PyO3 query...")
            pyo3_result = self.run_pyo3_fuzzy_query(pattern, mutations)

            if not pyo3_result["success"]:
                print(f"   ❌ PyO3 failed: {pyo3_result['error']}")
                all_tests_passed = False
                continue

            print(f"   ✅ PyO3: {pyo3_result['total_matches']} matches (fixed)")

            # Compare results
            if cli_result["success"] and pyo3_result["success"]:
                if cli_result["total_matches"] == pyo3_result["total_matches"]:
                    print(f"   🎉 CONSISTENT! CLI and PyO3 results match.")
                    passed_tests += 1
                else:
                    print(
                        f"   🚨 INCONSISTENT! CLI={cli_result['total_matches']}, PyO3={pyo3_result['total_matches']}"
                    )
                    print(f"      This indicates the fix may not be working correctly.")
                    all_tests_passed = False

        # Summary
        print("\n" + "=" * 70)
        print("📋 CONSISTENCY TEST SUMMARY")
        print("=" * 70)
        print(f"📊 Total tests: {total_tests}")
        print(f"✅ Consistent results: {passed_tests}")
        print(f"❌ Inconsistent results: {total_tests - passed_tests}")
        print(f"📈 Consistency rate: {passed_tests / total_tests * 100:.2f}%")

        if all_tests_passed:
            print(f"\n🎉 ALL TESTS PASSED!")
            print(f"   PyO3 fuzzy query implementation is now consistent with CLI.")
            print(f"   The fix successfully resolves the total_matches issue.")
        else:
            print(f"\n🚨 SOME TESTS FAILED!")
            print(f"   There may be remaining inconsistencies between CLI and PyO3.")

        return all_tests_passed


def main():
    """Main test function."""
    # Real database path
    db_path = "/Users/forrest/Data/data/kmer/K19/R1_001.rkdb"

    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        print("Please ensure the real database file exists.")
        return

    # Test patterns for comprehensive testing
    test_patterns = [
        # Basic patterns without N
        ("AAAAAAAAAAAAAAAAAAA", 0),  # All A, no mutations
        ("ATCGATCGATCGATCGAT", 0),  # Repeating pattern, no mutations
        ("ATCGATCGATCGATCGAT", 1),  # Same with 1 mutation
        # Patterns with N wildcards (limit max_variants to avoid explosion)
        ("ATCNATCNATCNATCNAT", 0),  # With N wildcard
        ("AAAAAAAAAAAAAAAAAN", 0),  # N at end
        ("NATAAAAAAAAAAAAAAA", 0),  # N at start
        ("AAAANAAAAAAAAAAAAA", 0),  # N in middle
        # Complex patterns with mutations
        ("ATCGATCGATCGATCGAT", 2),  # Multiple mutations
    ]

    # Initialize tester
    tester = RealDataConsistencyTest(db_path)

    # Run comprehensive test
    success = tester.run_comprehensive_test(test_patterns)

    if success:
        print(f"\n✅ REAL DATA CONSISTENCY TEST PASSED!")
        print(f"   The PyO3 fuzzy query fix is working correctly.")
    else:
        print(f"\n❌ REAL DATA CONSISTENCY TEST FAILED!")
        print(f"   Please review the inconsistencies above.")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
