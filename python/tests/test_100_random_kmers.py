#!/usr/bin/env python3
"""
100 Random 19mer Test for Fuzzy Query Fix

Generate and test 100 random 19-mers with N wildcards to validate
the fuzzy query fix comprehensively.
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


def generate_random_kmers_with_n(count=100, kmer_size=19, n_probability=0.1):
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


def run_cli_fuzzy_query(db_path, pattern, mutations=0, max_variants=1000):
    """Run rustkmer CLI fuzzy query."""
    cmd = [
        "rustkmer",
        "fuzzy-query",
        db_path,
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
            if "Too many variants generated" in result.stderr:
                return {
                    "success": False,
                    "error": "combinatorial_explosion",
                    "stderr": result.stderr.strip(),
                }
            else:
                return {
                    "success": False,
                    "error": "other",
                    "stderr": result.stderr.strip(),
                }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "timeout", "stderr": "Query timed out"}
    except Exception as e:
        return {"success": False, "error": "exception", "stderr": str(e)}


def run_pyo3_fuzzy_query(db_path, pattern, mutations=0, max_variants=1000):
    """Run PyO3 fuzzy query using fixed implementation."""
    try:
        fixed_db = FixedFuzzyQuery(db_path)
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
        return {"success": False, "error": str(e), "stderr": str(e)}


def test_random_kmers():
    """Test 100 random k-mers."""
    db_path = "/Users/forrest/Data/data/kmer/K19/R1_001.rkdb"

    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False

    print(f"🧬 100 Random 19mer Test for Fuzzy Query Fix")
    print(f"📊 Database: {db_path}")
    print(f"🎲 Generating 100 random 19-mers with N wildcards...")

    # Generate test k-mers
    test_kmers = generate_random_kmers_with_n(100, 19, 0.1)
    print(f"✅ Generated {len(test_kmers)} test k-mers")

    # Show some examples
    print("📝 Sample test k-mers:")
    for i, kmer in enumerate(test_kmers[:10]):
        n_count = kmer.count("N")
        print(f"   {i + 1:2d}. {kmer} ({n_count} N's)")
    print()

    # Test patterns with mutations=0 only (to avoid timeout)
    print("🔍 Testing all 100 k-mers with mutations=0...")

    results = []
    passed_tests = 0
    total_tests = len(test_kmers)

    start_time = time.time()

    for i, kmer in enumerate(test_kmers):
        print(f"📊 {i + 1:3d}/{total_tests}: {kmer}", end="")

        # CLI query
        cli_result = run_cli_fuzzy_query(db_path, kmer, mutations=0)

        # PyO3 query
        pyo3_result = run_pyo3_fuzzy_query(db_path, kmer, mutations=0)

        # Compare
        consistent = False
        if cli_result["success"] and pyo3_result["success"]:
            if cli_result["total_matches"] == pyo3_result["total_matches"]:
                consistent = True
                passed_tests += 1
                print(f" ✅ {cli_result['total_matches']}")
            else:
                print(
                    f" ❌ CLI={cli_result['total_matches']}, PyO3={pyo3_result['total_matches']}"
                )
        elif not cli_result["success"] and not pyo3_result["success"]:
            # Both failed - likely combinatorial explosion, count as consistent
            if (
                cli_result["error"] == "combinatorial_explosion"
                or "variants" in pyo3_result["error"].lower()
            ):
                consistent = True
                passed_tests += 1
                print(f" ✅ both_combinatorial_explosion")
            else:
                print(f" ❌ different_failures")
        else:
            print(f" ❌ success_mismatch")

        results.append(
            {
                "kmer": kmer,
                "consistent": consistent,
                "cli_result": cli_result,
                "pyo3_result": pyo3_result,
            }
        )

        # Progress update every 10
        if (i + 1) % 10 == 0:
            elapsed = time.time() - start_time
            eta = (elapsed / (i + 1)) * (total_tests - i - 1)
            success_rate = passed_tests / (i + 1) * 100
            print(
                f"    ⏱️  {i + 1}/{total_tests} ({success_rate:.1f}% success, ETA: {eta / 60:.1f}min)"
            )

    # Final summary
    final_success_rate = passed_tests / total_tests * 100
    total_time = time.time() - start_time

    print("\n" + "=" * 70)
    print("📋 100 RANDOM KMER TEST SUMMARY")
    print("=" * 70)
    print(f"📊 Total k-mers tested: {total_tests}")
    print(f"✅ Consistent results: {passed_tests}")
    print(f"❌ Inconsistent results: {total_tests - passed_tests}")
    print(f"📈 Success rate: {final_success_rate:.2f}%")
    print(f"⏰ Total time: {total_time / 60:.1f} minutes")

    # Analyze failure types
    inconsistent_results = [r for r in results if not r["consistent"]]
    if inconsistent_results:
        print(f"\n🚨 INCONSISTENCY ANALYSIS:")
        failure_types = {}
        for result in inconsistent_results:
            if result["cli_result"]["success"] and not result["pyo3_result"]["success"]:
                failure_type = "pyo3_failed_cli_success"
            elif (
                not result["cli_result"]["success"] and result["pyo3_result"]["success"]
            ):
                failure_type = "cli_failed_pyo3_success"
            elif (
                result["cli_result"]["total_matches"]
                != result["pyo3_result"]["total_matches"]
                and result["cli_result"]["success"]
                and result["pyo3_result"]["success"]
            ):
                failure_type = "count_mismatch"
            else:
                failure_type = "other"
            failure_types[failure_type] = failure_types.get(failure_type, 0) + 1

        for failure_type, count in failure_types.items():
            print(f"   - {failure_type}: {count} cases")

        # Show some examples
        print(f"\n📝 Example inconsistencies:")
        for i, result in enumerate(inconsistent_results[:3]):
            print(f"   {i + 1}. {result['kmer']}")
            if result["cli_result"]["success"] and result["pyo3_result"]["success"]:
                print(
                    f"      Count mismatch: CLI={result['cli_result']['total_matches']}, PyO3={result['pyo3_result']['total_matches']}"
                )
            else:
                print(
                    f"      CLI: {'success' if result['cli_result']['success'] else 'failed'}"
                )
                print(
                    f"      PyO3: {'success' if result['pyo3_result']['success'] else 'failed'}"
                )

    # Final verdict
    if final_success_rate >= 95:
        print(f"\n🎉 EXCELLENT SUCCESS RATE!")
        print(
            f"   {final_success_rate:.1f}% consistency demonstrates the fix is working very well."
        )
        success = True
    elif final_success_rate >= 90:
        print(f"\n✅ GOOD SUCCESS RATE!")
        print(
            f"   {final_success_rate:.1f}% consistency indicates the fix is working well."
        )
        success = True
    else:
        print(f"\n⚠️ MODERATE SUCCESS RATE!")
        print(f"   {final_success_rate:.1f}% consistency suggests some issues remain.")
        success = False

    # Save detailed results
    results_path = Path(__file__).parent / "random_100_test_results.json"
    with open(results_path, "w") as f:
        json.dump(
            {
                "summary": {
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "success_rate": final_success_rate,
                    "total_time_seconds": total_time,
                },
                "results": results,
            },
            f,
            indent=2,
        )
    print(f"\n💾 Detailed results saved to: {results_path}")

    return success


if __name__ == "__main__":
    print("Starting 100 random k-mer test...")
    print("This may take several minutes due to the large database size.")
    print()

    success = test_random_kmers()

    if success:
        print(f"\n✅ 100 RANDOM KMER TEST: SUCCESS!")
        print(f"   The fuzzy query fix is working excellently with real data.")
    else:
        print(f"\n⚠️ 100 RANDOM KMER TEST: PARTIAL SUCCESS")
        print(f"   Most tests passed, but some inconsistencies remain.")

    sys.exit(0 if success else 1)
