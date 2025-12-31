#!/usr/bin/env python3
"""
Quick Real Data Fuzzy Query Test

This is a quick test to compare a few fuzzy query results between CLI and PyO3.
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


def run_cli_fuzzy_query(db_path, pattern, mutations=0, max_variants=1000):
    """Run rustkmer CLI fuzzy query and parse results."""
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
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return {
                "success": True,
                "total_matches": data.get("total_count", 0),
                "variants_generated": data.get("query_metadata", {}).get(
                    "variants_generated", 0
                ),
                "query_time_ms": data.get("query_metadata", {}).get("query_time_ms", 0),
            }
        else:
            return {"success": False, "error": f"CLI failed: {result.stderr}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "CLI query timed out"}
    except Exception as e:
        return {"success": False, "error": f"CLI error: {str(e)}"}


def run_pyo3_fuzzy_query(db_path, pattern, mutations=0, max_variants=1000):
    """Run PyO3 fuzzy query."""
    try:
        with Database(db_path) as db:
            result = db.fuzzy_query(
                pattern, mutations=mutations, max_variants=max_variants
            )
            return {
                "success": True,
                "total_matches": result.total_matches,
                "has_exact_match": result.has_exact_match,
                "fuzzy_match_count": len(result.fuzzy_matches),
            }
    except Exception as e:
        return {"success": False, "error": f"PyO3 error: {str(e)}"}


def main():
    """Main test function."""
    # Real database path
    db_path = "/Users/forrest/Data/data/kmer/K19/R1_001.rkdb"

    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return

    print(f"🧬 Quick Real Data Fuzzy Query Test")
    print(f"📊 Database: {db_path}")
    print(f"📁 Database size: {os.path.getsize(db_path) / (1024 * 1024 * 1024):.1f} GB")
    print("=" * 60)

    # Test patterns
    test_patterns = [
        ("AAAAAAAAAAAAAAAAAAA", 0),  # All A, no mutations
        ("ATCGATCGATCGATCGAT", 0),  # Repeating pattern, no mutations
        ("ATCGATCGATCGATCGAT", 1),  # Same with 1 mutation
        ("ATCNATCNATCNATCNAT", 0),  # With N wildcard
        ("AAAAAAAAAAAAAAAAAN", 0),  # N at end
    ]

    print("🔍 Testing individual patterns...")

    for i, (pattern, mutations) in enumerate(test_patterns):
        print(f"\n📝 Test {i + 1}: Pattern='{pattern}', mutations={mutations}")

        # CLI query
        print("   🖥️  Running CLI query...")
        start_time = time.time()
        cli_result = run_cli_fuzzy_query(db_path, pattern, mutations)
        cli_time = time.time() - start_time

        if cli_result["success"]:
            print(
                f"   ✅ CLI: {cli_result['total_matches']} matches ({cli_result['variants_generated']} variants, {cli_result['query_time_ms']}ms)"
            )
        else:
            print(f"   ❌ CLI: {cli_result['error']}")
            continue

        # PyO3 query
        print("   🐍 Running PyO3 query...")
        start_time = time.time()
        pyo3_result = run_pyo3_fuzzy_query(db_path, pattern, mutations)
        pyo3_time = time.time() - start_time

        if pyo3_result["success"]:
            print(
                f"   ✅ PyO3: {pyo3_result['total_matches']} matches (exact={pyo3_result['has_exact_match']}, fuzzy={pyo3_result['fuzzy_match_count']})"
            )
        else:
            print(f"   ❌ PyO3: {pyo3_result['error']}")
            continue

        # Compare results
        if cli_result["success"] and pyo3_result["success"]:
            if cli_result["total_matches"] == pyo3_result["total_matches"]:
                print(f"   🎉 MATCH! Results are consistent.")
            else:
                print(
                    f"   🚨 MISMATCH! CLI={cli_result['total_matches']}, PyO3={pyo3_result['total_matches']}"
                )
                print(f"      This indicates a bug in PyO3 implementation.")

        print(f"   ⏱️  Times: CLI={cli_time:.2f}s, PyO3={pyo3_time:.2f}s")

    print(f"\n✅ Quick test completed!")


if __name__ == "__main__":
    main()
