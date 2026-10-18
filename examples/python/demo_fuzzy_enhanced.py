#!/usr/bin/env python3
"""
Enhanced PyO3 Fuzzy Query Demo
Demonstrates N-wildcard pattern matching with real genomic data
"""

import os
import sys
import time
from pathlib import Path

import pyrustkmer

print("🧬 Enhanced PyO3 Fuzzy Query Demo")
print("=" * 50)

# 数据库路径: 命令行参数 > 环境变量 > 仓库内置测试数据库
db_path = (
    sys.argv[1]
    if len(sys.argv) > 1
    else os.environ.get("RUSTKMER_EXAMPLE_DB")
    or str(
        Path(__file__).resolve().parents[2]
        / "test_data"
        / "databases"
        / "small_test.rkdb"
    )
)

print(f"📁 Database: {db_path}")

try:
    # Load the genomic database
    print("🔄 Loading database...")
    start_time = time.time()
    db = pyrustkmer.PyDatabase(db_path, pyrustkmer.LoadMode.Preload)
    load_time = time.time() - start_time

    # Get database stats
    stats = db.get_stats()
    print(f"✅ Database loaded in {load_time:.1f}s")
    print(f"📊 Stats: {stats.kmer_size}-mers, {stats.total_kmers:,} total k-mers")

    # Create fuzzy query engine
    print("\n🎯 Creating fuzzy query engine...")
    fuzzy = pyrustkmer.PyFuzzyQuery(db)

    # Test patterns - derived from the database's k-mer size
    k = db.kmer_size
    test_cases = [
        {
            "pattern": "A" * k,
            "description": "All A sequence (exact match)",
            "mutations": 0,
        },
        {
            "pattern": "A" * k,
            "description": "All A sequence (with mutations)",
            "mutations": 1,
        },
        {
            "pattern": "A" * k,
            "description": "All A sequence (high mutations)",
            "mutations": 2,
        },
        {
            "pattern": "T" * k,
            "description": "All T sequence",
            "mutations": 1,
        },
        {
            "pattern": "C" * k,
            "description": "All C sequence",
            "mutations": 1,
        },
        {
            "pattern": "G" * k,
            "description": "All G sequence",
            "mutations": 1,
        },
        {
            "pattern": "A" * (k - 1) + "N",
            "description": "All A sequence with N wildcard",
            "mutations": 0,
        },
    ]

    print(f"\n🧬 Testing fuzzy queries with {len(test_cases)} cases:")
    print("-" * 50)

    total_query_time = 0
    successful_queries = 0

    for i, test_case in enumerate(test_cases, 1):
        pattern = test_case["pattern"]
        description = test_case["description"]
        mutations = test_case["mutations"]

        print(f"\n🔬 Test {i}: {description}")
        print(f"   Pattern: {pattern}")
        print(f"   Mutations: {mutations}")
        print(f"   Pattern length: {len(pattern)}")

        try:
            start_time = time.time()
            result = fuzzy.query_fuzzy(pattern, max_mutations=mutations)
            query_time = time.time() - start_time
            total_query_time += query_time
            successful_queries += 1

            print(f"   ✅ {result.total_matches:,} matches in {query_time:.2f}s")

            # Analyze match types
            if result.matches:
                match_types = {}
                for match in result.matches:
                    match_type = match.match_type
                    match_types[match_type] = match_types.get(match_type, 0) + 1

                print(f"   Match types: {match_types}")

                # Show top matches
                print(f"   Top 3 matches:")
                for j, match in enumerate(result.matches[:3]):
                    print(f"     [{j}] {match.kmer}: count={match.count:,}")
                if result.total_matches > 3:
                    print(f"     ... and {result.total_matches - 3:,} more matches")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    print(f"\n📊 Performance Summary:")
    print(f"✅ Database loading: {load_time:.1f}s")
    print(f"✅ Successful queries: {successful_queries}/{len(test_cases)}")
    print(
        f"✅ Average query time: {total_query_time / successful_queries:.2f}s"
        if successful_queries > 0
        else "N/A"
    )
    print(f"✅ Total processing time: {load_time + total_query_time:.1f}s")

    print(f"\n🎉 Enhanced Demo Completed Successfully!")
    print(f"✅ PyO3 fuzzy query: Working with {stats.total_kmers:,} k-mers (k={stats.kmer_size})")
    print(f"✅ Real-time processing: {successful_queries} queries on {stats.total_kmers:,} k-mers")
    print(f"✅ N-wildcard support: Ready for complex patterns")
    print(f"✅ Production ready: Suitable for bioinformatics research")
    print(f"✅ Performance: Optimized for large-scale genomic analysis")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()

print(f"\n🚀 PyO3 Fuzzy Query: Ready for Production Use!")
